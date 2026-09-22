"""Small standard-library HTTP client with cache, rate limiting, and retries."""

from __future__ import annotations

import base64
import binascii
from contextlib import nullcontext
import hashlib
import json
import random
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


RETRYABLE_STATUS = {429, 500, 502, 503, 504}
SECRET_QUERY_KEYS = {
    "api_key",
    "apikey",
    "key",
    "secret",
    "secretkey",
    "token",
    "email",
    "mailto",
}


def redact_url(url: str) -> str:
    parts = urlsplit(url)
    query = [
        (key, "***" if key.casefold() in SECRET_QUERY_KEYS else value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def redact_detail(text: str, url: str) -> str:
    redacted = text
    for key, value in parse_qsl(urlsplit(url).query, keep_blank_values=True):
        if key.casefold() in SECRET_QUERY_KEYS and value:
            redacted = redacted.replace(value, "***")
    return redacted


@dataclass(slots=True)
class TransportResponse:
    status: int
    url: str
    headers: dict[str, str]
    body: bytes


@dataclass(slots=True)
class HttpResult:
    status: int
    url: str
    headers: dict[str, str]
    body: bytes
    cache_path: str = ""
    from_cache: bool = False
    retrieved_at: str = ""

    @property
    def content_type(self) -> str:
        return self.headers.get("content-type", "").split(";", 1)[0].strip().lower()

    def text(self) -> str:
        charset = "utf-8"
        content_type = self.headers.get("content-type", "")
        if "charset=" in content_type:
            charset = content_type.rsplit("charset=", 1)[-1].split(";", 1)[0].strip()
        elif self.body.startswith((b"\xff\xfe", b"\xfe\xff")):
            charset = "utf-16"
        elif self.body.startswith(b"\xef\xbb\xbf"):
            charset = "utf-8-sig"
        else:
            head = self.body[:4096].decode("ascii", errors="ignore")
            match = re.search(
                r"(?:charset\s*=\s*|encoding\s*=\s*)[\"']?([A-Za-z0-9._-]+)",
                head,
                flags=re.I,
            )
            if match:
                charset = match.group(1)
        return self.body.decode(charset or "utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.text())


class HttpRequestError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, url: str = ""):
        super().__init__(message)
        self.status = status
        self.url = redact_url(url)


class RateLimiter:
    def __init__(
        self,
        min_interval: float,
        *,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.min_interval = max(0.0, min_interval)
        self.sleeper = sleeper
        self.clock = clock
        self._last_request = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = self.clock()
            remaining = self.min_interval - (now - self._last_request)
            if self._last_request and remaining > 0:
                self.sleeper(remaining)
            self._last_request = self.clock()


Transport = Callable[[str, str, Mapping[str, str], bytes | None, float], TransportResponse]

_SHARED_CONTROL_LOCK = threading.Lock()
_SHARED_REQUEST_LOCKS: dict[str, threading.Lock] = {}
_SHARED_RATE_LIMITERS: dict[str, RateLimiter] = {}


def _shared_request_controls(
    key: str,
    *,
    min_interval: float,
    sleeper: Callable[[float], None],
    clock: Callable[[], float],
) -> tuple[threading.Lock, RateLimiter]:
    with _SHARED_CONTROL_LOCK:
        request_lock = _SHARED_REQUEST_LOCKS.setdefault(key, threading.Lock())
        limiter = _SHARED_RATE_LIMITERS.get(key)
        if limiter is None:
            limiter = RateLimiter(
                min_interval,
                sleeper=sleeper,
                clock=clock,
            )
            _SHARED_RATE_LIMITERS[key] = limiter
        else:
            limiter.min_interval = max(limiter.min_interval, min_interval)
        return request_lock, limiter


def urllib_transport(
    method: str,
    url: str,
    headers: Mapping[str, str],
    body: bytes | None,
    timeout: float,
) -> TransportResponse:
    request = Request(url, data=body, headers=dict(headers), method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            return TransportResponse(
                status=int(response.status),
                url=str(response.geturl()),
                headers={key.lower(): value for key, value in response.headers.items()},
                body=response.read(),
            )
    except HTTPError as exc:
        return TransportResponse(
            status=int(exc.code),
            url=str(exc.geturl() or url),
            headers={key.lower(): value for key, value in exc.headers.items()},
            body=exc.read(),
        )
    except URLError as exc:
        raise HttpRequestError(
            f"Network request failed for {redact_url(url)}: {exc.reason}", url=url
        ) from exc
    except (OSError, TimeoutError) as exc:
        raise HttpRequestError(
            f"Network request failed for {redact_url(url)}: {exc}", url=url
        ) from exc


class HttpClient:
    def __init__(
        self,
        provider: str,
        *,
        cache_dir: str | Path,
        min_interval: float = 0.0,
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        user_agent: str = "research-lookup-enhanced/0.1",
        transport: Transport = urllib_transport,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        random_fn: Callable[[], float] = random.random,
        serialize_requests: bool = False,
        serialization_key: str | None = None,
    ) -> None:
        self.provider = provider
        self.cache_dir = Path(cache_dir) / provider
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.backoff_base = max(0.0, backoff_base)
        self.user_agent = user_agent
        self.transport = transport
        self.sleeper = sleeper
        self.random_fn = random_fn
        self.serialize_requests = bool(serialize_requests)
        self.serialization_key = (
            str(serialization_key or provider).casefold()
            if self.serialize_requests
            else ""
        )
        if self.serialization_key:
            self._request_lock, self.rate_limiter = _shared_request_controls(
                self.serialization_key,
                min_interval=min_interval,
                sleeper=sleeper,
                clock=clock,
            )
        else:
            self._request_lock = threading.Lock()
            self.rate_limiter = RateLimiter(
                min_interval, sleeper=sleeper, clock=clock
            )

    @staticmethod
    def _build_url(url: str, params: Mapping[str, Any] | None) -> str:
        if not params:
            return url
        parts = urlsplit(url)
        existing = parse_qsl(parts.query, keep_blank_values=True)
        added: list[tuple[str, Any]] = []
        for key, value in params.items():
            if value is None or value == "":
                continue
            if isinstance(value, (list, tuple)):
                added.extend((key, item) for item in value)
            else:
                added.append((key, value))
        query = urlencode([*existing, *added], doseq=True)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))

    @staticmethod
    def _cache_key(method: str, url: str, body: bytes | None) -> str:
        payload = method.encode() + b"\0" + url.encode() + b"\0" + (body or b"")
        return hashlib.sha256(payload).hexdigest()

    def _read_cache(self, path: Path) -> HttpResult | None:
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return HttpResult(
                status=int(payload["status"]),
                url=str(payload["url"]),
                headers={str(k): str(v) for k, v in payload.get("headers", {}).items()},
                body=base64.b64decode(payload["body_base64"], validate=True),
                cache_path=str(path),
                from_cache=True,
                retrieved_at=str(payload.get("retrieved_at") or ""),
            )
        except (OSError, KeyError, TypeError, ValueError, binascii.Error):
            return None

    def _write_cache(
        self, path: Path, result: TransportResponse, *, retrieved_at: str
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "status": result.status,
            "url": redact_url(result.url),
            "headers": result.headers,
            "body_base64": base64.b64encode(result.body).decode("ascii"),
            "retrieved_at": retrieved_at,
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        json_body: Any = None,
        use_cache: bool = True,
        cache_post: bool = False,
    ) -> HttpResult:
        method = method.upper()
        request_url = self._build_url(url, params)
        body = None
        request_headers = {
            "accept": "application/json, application/xml, text/html;q=0.9, */*;q=0.8",
            "user-agent": self.user_agent,
            **{key.lower(): value for key, value in (headers or {}).items()},
        }
        if json_body is not None:
            body = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            request_headers["content-type"] = "application/json"
        cache_path = self.cache_dir / f"{self._cache_key(method, request_url, body)}.json"
        cacheable = use_cache and (method == "GET" or (method == "POST" and cache_post))
        if cacheable:
            cached = self._read_cache(cache_path)
            if cached:
                return cached

        last: TransportResponse | None = None
        last_error: HttpRequestError | None = None
        for attempt in range(self.max_retries + 1):
            try:
                guard = self._request_lock if self.serialize_requests else nullcontext()
                with guard:
                    self.rate_limiter.wait()
                    last = self.transport(
                        method, request_url, request_headers, body, self.timeout
                    )
                last_error = None
            except HttpRequestError as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    raise
                delay = min(
                    60.0,
                    self.backoff_base * (2**attempt) + self.random_fn() * 0.25,
                )
                self.sleeper(delay)
                continue
            if last.status not in RETRYABLE_STATUS:
                break
            if attempt >= self.max_retries:
                break
            retry_after = last.headers.get("retry-after", "")
            try:
                delay = min(60.0, max(0.0, float(retry_after)))
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(retry_after)
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=timezone.utc)
                    delay = min(
                        60.0,
                        max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds()),
                    )
                except (TypeError, ValueError, OverflowError):
                    delay = 0.0
            if not delay:
                delay = min(
                    60.0,
                    self.backoff_base * (2**attempt) + self.random_fn() * 0.25,
                )
            self.sleeper(delay)

        if last is None:
            assert last_error is not None
            raise last_error
        if not 200 <= last.status < 300:
            detail = redact_detail(
                last.body.decode("utf-8", errors="replace")[:500], request_url
            )
            raise HttpRequestError(
                f"{self.provider} returned HTTP {last.status} for "
                f"{redact_url(request_url)}: {detail}",
                status=last.status,
                url=request_url,
            )
        retrieved_at = datetime.now(timezone.utc).isoformat()
        if cacheable:
            self._write_cache(cache_path, last, retrieved_at=retrieved_at)
        return HttpResult(
            status=last.status,
            url=redact_url(last.url),
            headers=last.headers,
            body=last.body,
            cache_path=str(cache_path) if cacheable else "",
            retrieved_at=retrieved_at,
        )

    def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        use_cache: bool = True,
    ) -> tuple[Any, HttpResult]:
        result = self.request(
            "GET", url, params=params, headers=headers, use_cache=use_cache
        )
        try:
            return result.json(), result
        except json.JSONDecodeError as exc:
            raise HttpRequestError(
                f"{self.provider} returned invalid JSON for {result.url}",
                status=result.status,
                url=result.url,
            ) from exc

    def get_text(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        use_cache: bool = True,
    ) -> tuple[str, HttpResult]:
        result = self.request(
            "GET", url, params=params, headers=headers, use_cache=use_cache
        )
        return result.text(), result

    def post_json(
        self,
        url: str,
        *,
        json_body: Any,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        use_cache: bool = True,
    ) -> tuple[Any, HttpResult]:
        """POST to an idempotent retrieval endpoint and cache by URL plus body."""
        result = self.request(
            "POST",
            url,
            params=params,
            headers=headers,
            json_body=json_body,
            use_cache=use_cache,
            cache_post=True,
        )
        try:
            return result.json(), result
        except json.JSONDecodeError as exc:
            raise HttpRequestError(
                f"{self.provider} returned invalid JSON for {result.url}",
                status=result.status,
                url=result.url,
            ) from exc
