"""Offline regressions for public capture headers and failure reasons."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kraken_prop.kraken_prop_c6_public_capture_v1 import (  # noqa: E402
    TRANSPORT_FAILED,
    capture_public,
    persisted_failure_reason,
)
from kraken_prop.kraken_prop_c6_public_http_v1 import (  # noqa: E402
    HEADERS_REJECTED,
    PublicHttpError,
    collect_response_headers,
    parse_public_response,
)


PUBLIC_URL = "https://futures.kraken.com/derivatives/api/v3/tickers/PF_XBTUSD"
FIRST_COOKIE = "facade-lang=en-us; Path=/; Domain=kraken.com; Secure"
SECOND_COOKIE = "public-bm=synthetic; HttpOnly; Secure; Path=/"


def _http(status: int, fields: list[tuple[str, str]], body: bytes) -> bytes:
    lines = [f"HTTP/1.1 {status} OK"]
    lines.extend(f"{name}: {value}" for name, value in fields)
    return ("\r\n".join(lines) + "\r\n\r\n").encode("ascii") + body


def _fail(exc: BaseException):
    def fetch(_url: str) -> bytes:
        raise exc

    return fetch


def _ticker_response() -> bytes:
    return _http(
        200,
        [
            ("Content-Type", "application/json"),
            ("Cache-Control", "private, no-store"),
            ("Set-Cookie", FIRST_COOKIE),
            ("set-cookie", SECOND_COOKIE),
        ],
        b'{"result":"success","ticker":{"symbol":"PF_XBTUSD"}}',
    )


class PublicHeaderTests(unittest.TestCase):
    def test_repeated_set_cookie_is_kept_on_a_valid_public_response(self):
        response = parse_public_response(_ticker_response())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.values("set-cookie"), (FIRST_COOKIE, SECOND_COOKIE))
        self.assertEqual(response.values("content-type"), ("application/json",))

    def test_repeated_safe_response_header_is_kept(self):
        headers = collect_response_headers(
            [
                ("Link", '</a>; rel="next"'),
                ("Cache-Control", "private"),
                ("Cache-Control", "no-store"),
                ("Link", '</b>; rel="prev"'),
            ]
        )

        self.assertEqual(
            tuple(value for name, value in headers if name == "Link"),
            ('</a>; rel="next"', '</b>; rel="prev"'),
        )
        self.assertEqual(
            tuple(value for name, value in headers if name == "Cache-Control"),
            ("private", "no-store"),
        )

    def test_repeated_set_cookie_capture_succeeds(self):
        stored: list[dict[str, object]] = []
        result = capture_public(
            PUBLIC_URL,
            fetch=lambda _url: _ticker_response(),
            persist=stored.append,
        )

        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["reason"], "")
        self.assertEqual(result["http_status"], 200)
        self.assertEqual(result["set_cookie"], [FIRST_COOKIE, SECOND_COOKIE])
        self.assertEqual(stored, [result])
        self.assertIsInstance(result["elapsed_ms"], int)

    def test_repeated_unsafe_header_is_rejected(self):
        raw = _http(
            200,
            [("Content-Length", "4"), ("Content-Length", "5")],
            b"abcd",
        )

        with self.assertRaises(PublicHttpError) as caught:
            parse_public_response(raw)

        self.assertEqual(caught.exception.code, HEADERS_REJECTED)


class FailureReasonTests(unittest.TestCase):
    def test_header_rejection_is_persisted_as_the_inner_code(self):
        raw = _http(
            200,
            [("Content-Length", "4"), ("Content-Length", "9")],
            b"abcd",
        )
        stored: list[dict[str, object]] = []
        result = capture_public(PUBLIC_URL, fetch=lambda _url: raw, persist=stored.append)

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["reason"], HEADERS_REJECTED)
        self.assertNotEqual(result["reason"], TRANSPORT_FAILED)
        self.assertEqual(stored[0]["reason"], HEADERS_REJECTED)
        self.assertEqual(result["set_cookie"], [])

    def test_wrapped_transport_failed_keeps_the_inner_code(self):
        def fetch(_url: str) -> bytes:
            try:
                raise PublicHttpError(HEADERS_REJECTED, "set-cookie")
            except PublicHttpError as exc:
                wrapper = RuntimeError(TRANSPORT_FAILED)
                wrapper.code = TRANSPORT_FAILED
                raise wrapper from exc

        result = capture_public(PUBLIC_URL, fetch=fetch)

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["reason"], HEADERS_REJECTED)

    def test_exact_inner_message_code_is_persisted(self):
        result = capture_public(PUBLIC_URL, fetch=_fail(RuntimeError("READ_TIMEOUT")))

        self.assertEqual(result["reason"], "READ_TIMEOUT")
        self.assertEqual(persisted_failure_reason(RuntimeError("READ_TIMEOUT")), "READ_TIMEOUT")

    def test_bare_transport_error_stays_transport_failed(self):
        result = capture_public(PUBLIC_URL, fetch=_fail(TimeoutError("timed out")))

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["reason"], TRANSPORT_FAILED)
        self.assertEqual(
            persisted_failure_reason(TimeoutError("timed out")),
            TRANSPORT_FAILED,
        )


if __name__ == "__main__":
    unittest.main()
