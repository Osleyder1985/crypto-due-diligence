"""Tests for HTTP evidence capture without live network dependencies."""
import unittest
from email.message import Message
from unittest.mock import patch

from evidence_collector import CollectionError, collect_url


class FakeResponse:
    status = 200
    def __init__(self, body=b"synthetic response"):
        self.body = body
        self.headers = Message()
        self.headers["Content-Type"] = "text/plain; charset=utf-8"
        self.headers["Last-Modified"] = "Wed, 01 Jan 2025 00:00:00 GMT"
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, size=-1): return self.body[:size]
    def geturl(self): return "https://example.org/final"


class EvidenceCollectorTests(unittest.TestCase):
    def test_returns_source_and_unverified_evidence_with_hash(self):
        result = collect_url(
            "https://example.org/source", "Synthetic Publisher", "src_test", "evd_test",
            source_type="NEWS_MEDIA", source_published_at="2025-01-01T00:00:00Z",
            opener=lambda request, timeout: FakeResponse(),
        )
        source, evidence = result["records"]
        self.assertEqual("Source", source["record_type"])
        self.assertEqual("Evidence", evidence["record_type"])
        self.assertTrue(result["content_hash"].startswith("sha256:"))
        self.assertEqual("UNVERIFIED", evidence["record"]["verification_status"])
        self.assertEqual("https://example.org/source", source["record"]["url"])
        self.assertIn("last_modified=", source["record"]["notes"])

    def test_rejects_localhost(self):
        with self.assertRaises(CollectionError):
            collect_url("http://localhost/private", "x", "src_x", "evd_x")

    def test_rejects_unsupported_scheme(self):
        with self.assertRaises(CollectionError):
            collect_url("file:///etc/passwd", "x", "src_x", "evd_x")

    def test_rejects_oversized_response(self):
        with self.assertRaises(CollectionError):
            collect_url("https://example.org/source", "x", "src_x", "evd_x",
                        max_bytes=4, opener=lambda request, timeout: FakeResponse(b"too long"))


if __name__ == "__main__":
    unittest.main()
