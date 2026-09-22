from pathlib import Path
from io import BytesIO
from email.message import Message
from unittest.mock import Mock, patch
from urllib.request import Request, HTTPHandler, HTTPSHandler, ProxyHandler, build_opener
from urllib.response import addinfourl
import hashlib
import json
import os
import socket
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills/research-lookup-enhanced/scripts"))
from rle import public_http
from rle.extraction import MinerUParser, WebExtractor
from rle.http_client import HttpClient, urllib_transport


class MinerUCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "paper.pdf"
        self.source.write_bytes(b"%PDF-1.4\nsynthetic old input\n")
        self.original_hash = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.output = self.root / "parsed"
        self.output.mkdir()
        (self.output / "full.md").write_text("synthetic old parse", encoding="utf-8")
        self.manifest = self.output / "manifest.json"
        self.manifest.write_text(json.dumps({"source": {"input_sha256": self.original_hash}}))
        self.wrapper = self.root / "wrapper.py"
        self.wrapper.write_text("raise AssertionError('No remote execution expected')")
        self.parser = MinerUParser(allow_remote=True, is_open_access=True,
                                  python_executable=sys.executable, wrapper_path=str(self.wrapper))

    def tearDown(self):
        self.temp.cleanup()

    def parse(self):
        with patch.dict(os.environ, {"MINERU_API_KEY": "synthetic-only"}), \
             patch("rle.extraction.subprocess.run", side_effect=AssertionError("No upload")):
            return self.parser.parse(self.source, output_dir=self.output)

    def test_matching_hash_reuses_without_upload(self):
        result = self.parse()
        self.assertEqual(result.source_file_hash, self.original_hash)
        self.assertTrue(result.parser_provenance[0]["input_hash_verified"])
        self.assertEqual(result.parser_provenance[0]["status"], "reused")

    def test_source_replacement_preserves_cache_and_rejects_old_parse(self):
        before = {p.name: p.read_bytes() for p in self.output.iterdir()}
        self.source.write_bytes(b"%PDF-1.4\nsynthetic replacement\n")
        with self.assertRaisesRegex(RuntimeError, "input hash"):
            self.parse()
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.output.iterdir()})

    def test_missing_malformed_hashes_do_not_borrow_current_hash(self):
        for digest in (None, "", "old-source-hash", "0" * 64):
            with self.subTest(digest=digest):
                self.manifest.write_text(json.dumps({"source": {"input_sha256": digest}}))
                with self.assertRaisesRegex(RuntimeError, "input hash"):
                    self.parse()


def address(ip, port=443):
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    sockaddr = (ip, port, 0, 0) if family == socket.AF_INET6 else (ip, port)
    return (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr)


class PublicHTTPTests(unittest.TestCase):
    def test_literals_and_non_http_schemes_block_without_dns(self):
        urls = ("http://127.0.0.1/", "http://169.254.169.254/", "http://[::1]/",
                "http://[::ffff:127.0.0.1]/", "http://224.0.0.1/",
                "file:///etc/passwd", "ftp://example.org/", "http://user:secret@example.org/",
                "http://localhost./", "http://example.org\\@127.0.0.1/")
        with patch.object(public_http.socket, "getaddrinfo", side_effect=AssertionError("No DNS")):
            for url in urls:
                with self.subTest(url=url), self.assertRaises(ValueError):
                    public_http.validate_public_url(url)

    def test_private_or_mixed_dns_is_blocked_before_socket(self):
        for records in ([address("127.0.0.1")],
                        [address("93.184.216.34"), address("10.0.0.1")]):
            with self.subTest(records=records), \
                 patch.object(public_http.socket, "getaddrinfo", return_value=records), \
                 patch.object(public_http.socket, "socket", side_effect=AssertionError("No socket")):
                with self.assertRaisesRegex(ValueError, "DNS resolves"):
                    public_http._connection_factory(Request("https://example.org/article"), True)

    def test_direct_connection_pins_checked_dns_answer(self):
        fake_socket = Mock()
        with patch.object(public_http.socket, "getaddrinfo", return_value=[address("93.184.216.34")]) as dns, \
             patch.object(public_http.socket, "socket", return_value=fake_socket):
            factory = public_http._connection_factory(Request("https://example.org/a"), True)
            connection = factory("example.org", timeout=2)
            with patch.object(public_http.socket, "getaddrinfo", side_effect=AssertionError("No second DNS")):
                result = connection._create_connection(("example.org", 443), 2)
            self.assertIs(result, fake_socket)
            fake_socket.connect.assert_called_once_with(("93.184.216.34", 443))
            dns.assert_called_once()
            connection.close()

    def test_proxy_uses_checked_ip_and_original_host(self):
        for scheme in ("http", "https"):
            with self.subTest(scheme=scheme):
                request = Request(f"{scheme}://example.org/article")
                request.set_proxy("127.0.0.1:8080", "http")
                with patch.object(public_http.socket, "getaddrinfo", return_value=[address("93.184.216.34")]):
                    factory = public_http._connection_factory(request, scheme == "https")
                self.assertEqual(request.get_header("Host"), "example.org")
                connection = factory("127.0.0.1:8080", timeout=2)
                if scheme == "https":
                    self.assertEqual(request._tunnel_host, "93.184.216.34:443")
                    self.assertEqual(connection._public_server_hostname, "example.org")
                else:
                    self.assertEqual(request.selector, "http://93.184.216.34:80/article")
                connection.close()

    def test_redirect_removes_cross_origin_credentials_and_rejects_body(self):
        handler = public_http._PublicRedirectHandler()
        request = Request("https://a.example/a", headers={"Authorization": "synthetic",
                          "X-Api-Key": "synthetic", "Cookie": "synthetic", "User-Agent": "audit"})
        redirected = handler.redirect_request(request, None, 302, "Found", {}, "https://b.example/b")
        self.assertEqual({k.lower() for k in redirected.headers}, {"user-agent"})
        same = handler.redirect_request(request, None, 302, "Found", {}, "https://a.example/b")
        self.assertTrue(same.has_header("Authorization"))
        with self.assertRaisesRegex(ValueError, "request body"):
            handler.redirect_request(Request("https://a.example", data=b"synthetic"), None,
                                     307, "Temporary", {}, "https://b.example")

    def test_real_redirect_handler_blocks_private_before_following(self):
        calls = []
        def respond(request):
            calls.append(request.full_url)
            self.assertNotIn("127.0.0.1", request.full_url)
            headers = Message()
            headers["Location"] = "http://127.0.0.1/private"
            response = addinfourl(BytesIO(b""), headers, request.full_url, 302)
            response.msg = "Found"
            return response
        class FakeHTTP(HTTPHandler):
            def http_open(self, request):
                return respond(request)
        class FakeHTTPS(HTTPSHandler):
            def https_open(self, request):
                return respond(request)
        opener = build_opener(ProxyHandler({}), FakeHTTP(), FakeHTTPS(),
                              public_http._PublicRedirectHandler())
        with patch.object(public_http, "build_opener", return_value=opener), \
             patch.object(socket, "create_connection", side_effect=AssertionError("No real network")):
            with self.assertRaisesRegex(ValueError, "non-public"):
                urllib_transport("GET", "https://public.example/a", {}, None, 1)
        self.assertEqual(calls, ["https://public.example/a"])

    def test_public_redirect_runs_through_checked_sockets_and_strips_credentials(self):
        first, second = Mock(), Mock()
        first.makefile.return_value = BytesIO(
            b"HTTP/1.1 302 Found\r\nLocation: http://second.example/b\r\nContent-Length: 0\r\n\r\n")
        second.makefile.return_value = BytesIO(
            b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\nok")
        with patch("urllib.request.getproxies", return_value={}), \
             patch.object(public_http.socket, "getaddrinfo", side_effect=[
                 [address("93.184.216.34", 80)], [address("93.184.216.35", 80)]]), \
             patch.object(public_http.socket, "socket", side_effect=[first, second]):
            result = urllib_transport("GET", "http://first.example/a",
                                      {"Authorization": "synthetic-only"}, None, 1)
        self.assertEqual(result.body, b"ok")
        self.assertEqual(result.url, "http://second.example/b")
        first.connect.assert_called_once_with(("93.184.216.34", 80))
        second.connect.assert_called_once_with(("93.184.216.35", 80))
        self.assertIn(b"Authorization: synthetic-only", first.sendall.call_args.args[0])
        self.assertNotIn(b"synthetic-only", second.sendall.call_args.args[0])

    def test_tunnel_tls_checks_original_hostname(self):
        request = Request("https://example.org/article")
        request.set_proxy("127.0.0.1:8080", "http")
        with patch.object(public_http.socket, "getaddrinfo", return_value=[address("93.184.216.34")]):
            factory = public_http._connection_factory(request, True)
        connection = factory("127.0.0.1:8080")
        connection.set_tunnel(request._tunnel_host)
        raw_socket = Mock()
        connection._context = Mock()
        def connect_tunnel(instance):
            instance.sock = raw_socket
        with patch("http.client.HTTPConnection.connect", connect_tunnel):
            connection.connect()
        connection._context.wrap_socket.assert_called_once_with(raw_socket, server_hostname="example.org")
        self.assertEqual(connection._tunnel_host, "93.184.216.34")
        self.assertEqual(connection._tunnel_port, 443)
        connection.close()

    def test_robots_private_redirect_blocks_article_request(self):
        # The robots path uses the same protected transport. Policy errors are
        # ValueError, not a transient HttpRequestError that robots may ignore.
        calls = []
        def respond(request):
            calls.append(request.full_url)
            headers = Message()
            headers["Location"] = "http://127.0.0.1/private"
            response = addinfourl(BytesIO(b""), headers, request.full_url, 302)
            response.msg = "Found"
            return response
        class FakeHTTPS(HTTPSHandler):
            def https_open(self, request): return respond(request)
        opener = build_opener(ProxyHandler({}), FakeHTTPS(), public_http._PublicRedirectHandler())
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(public_http, "build_opener", return_value=opener), \
             patch.object(socket, "create_connection", side_effect=AssertionError("No real network")):
            extractor = WebExtractor(cache_dir=tmp, client=HttpClient("test", cache_dir=tmp))
            with self.assertRaises(ValueError):
                extractor.extract_url("https://public.example/article")
        self.assertEqual(calls, ["https://public.example/robots.txt"])


if __name__ == "__main__":
    unittest.main()
