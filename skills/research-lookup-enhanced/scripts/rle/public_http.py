"""Public HTTP(S) transport boundaries for lookup and extraction.

Direct connections use the DNS addresses that were checked, without a second
resolution. Existing urllib proxy configuration remains supported: a configured
proxy is trusted transport, but receives the checked destination IP, while Host
and TLS SNI/certificate verification retain the original public hostname.
"""
from __future__ import annotations

import http.client
import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPHandler, HTTPSHandler, HTTPRedirectHandler, build_opener


def _public_address(value: str) -> bool:
    address = ipaddress.ip_address(value)
    return (address.is_global and not address.is_multicast
            and not address.is_reserved and not address.is_unspecified)


def validate_public_url(url: str):
    if "\\" in url or any(ord(c) < 32 or ord(c) == 127 for c in url):
        raise ValueError("Control characters and backslashes are not allowed in public URLs.")
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("Only absolute HTTP(S) URLs are supported.")
    if parts.username is not None or parts.password is not None:
        raise ValueError("Credentials in public URLs are not supported.")
    hostname = parts.hostname.rstrip(".").casefold()
    if "%" in hostname or hostname == "localhost" or hostname.endswith(".localhost") or hostname == "localhost.localdomain":
        raise ValueError("Local or scoped hostnames are disabled.")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        pass  # DNS is checked by the connection handler before any socket opens.
    else:
        if not _public_address(str(address)):
            raise ValueError("Private or non-public IP URLs are disabled.")
    port = parts.port if parts.port is not None else (443 if parts.scheme == "https" else 80)
    if not 1 <= port <= 65535:
        raise ValueError("Invalid public URL port.")
    return parts


def public_addresses(url: str):
    parts = validate_public_url(url)
    port = parts.port if parts.port is not None else (443 if parts.scheme == "https" else 80)
    records = socket.getaddrinfo(parts.hostname, port, type=socket.SOCK_STREAM)
    if not records or any(not _public_address(record[4][0]) for record in records):
        raise ValueError("DNS resolves to a private or non-public address; request blocked.")
    return records


def _connect_checked(records, timeout, source_address=None):
    last_error = None
    for family, socktype, proto, _canonname, sockaddr in records:
        sock = socket.socket(family, socktype, proto)
        try:
            if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sockaddr)
            return sock
        except OSError as exc:
            last_error = exc
            sock.close()
    if last_error is not None:
        raise last_error
    raise OSError("No public address is available.")


def _authority(hostname: str, port: int) -> str:
    host = f"[{hostname}]" if ":" in hostname else hostname
    return f"{host}:{port}"


class _TunnelTLSConnection(http.client.HTTPSConnection):
    def __init__(self, *args, server_hostname: str, **kwargs):
        self._public_server_hostname = server_hostname
        super().__init__(*args, **kwargs)

    def connect(self):
        # HTTPConnection performs CONNECT to the checked IP. Verify the TLS
        # certificate for the public source hostname, not that numeric address.
        http.client.HTTPConnection.connect(self)
        self.sock = self._context.wrap_socket(
            self.sock, server_hostname=self._public_server_hostname)


def _connection_factory(request, secure: bool):
    parts = validate_public_url(request.full_url)
    records = public_addresses(request.full_url)
    port = parts.port if parts.port is not None else (443 if secure else 80)
    proxied = bool(request.has_proxy() or getattr(request, "_tunnel_host", None))
    if proxied:
        # Prefer IPv4 when both families exist, for compatibility with HTTP
        # proxies which do not accept IPv6 CONNECT destinations.
        record = next((r for r in records if r[0] == socket.AF_INET), records[0])
        destination = _authority(record[4][0], port)
        request.add_unredirected_header("Host", parts.netloc)
        if secure:
            request._tunnel_host = destination
        else:
            request.selector = urlunsplit(parts._replace(netloc=destination, fragment=""))

    def factory(host, **kwargs):
        if proxied and secure:
            return _TunnelTLSConnection(host, server_hostname=parts.hostname, **kwargs)
        cls = http.client.HTTPSConnection if secure else http.client.HTTPConnection
        connection = cls(host, **kwargs)
        if not proxied:
            # Do not change global socket/DNS functions: other threads may be
            # using unrelated clients. Ignore the original hostname here.
            connection._create_connection = (
                lambda address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None:
                _connect_checked(records, timeout, source_address))
        return connection
    return factory


class _PublicHTTPHandler(HTTPHandler):
    def http_open(self, request):
        return self.do_open(_connection_factory(request, False), request)


class _PublicHTTPSHandler(HTTPSHandler):
    def https_open(self, request):
        return self.do_open(_connection_factory(request, True), request,
                            context=self._context)


class _PublicRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        try:
            old, new = validate_public_url(request.full_url), validate_public_url(newurl)
            old_origin = (old.scheme, old.hostname, old.port or (443 if old.scheme == "https" else 80))
            new_origin = (new.scheme, new.hostname, new.port or (443 if new.scheme == "https" else 80))
            if old_origin != new_origin and request.data:
                raise ValueError("Cross-origin redirects with a request body require a separate request.")
            redirected = super().redirect_request(request, fp, code, message, headers, newurl)
            if redirected is not None and old_origin != new_origin:
                allowed = {"accept", "accept-language", "user-agent", "range",
                           "content-type", "content-length"}
                for mapping in (redirected.headers, redirected.unredirected_hdrs):
                    for key in list(mapping):
                        if key.lower() not in allowed:
                            del mapping[key]
            return redirected
        except Exception:
            if fp is not None:
                fp.close()
            raise


def public_urlopen(request, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
    validate_public_url(request.full_url)
    # A fresh local opener preserves urllib's proxy/no_proxy handling without
    # installing a process-global handler or changing application TLS settings.
    opener = build_opener(_PublicHTTPHandler(), _PublicHTTPSHandler(), _PublicRedirectHandler())
    return opener.open(request, timeout=timeout)
