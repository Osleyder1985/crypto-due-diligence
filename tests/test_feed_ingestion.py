"""Offline tests for RSS/Atom evidence ingestion."""
import unittest
from email.message import Message

from evidence_collector import CollectionError, collect_feed, parse_feed


RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>Example Crypto News</title>
<item><title>Exchange announces listing</title><link>https://news.example/item/1</link>
<guid>item-1</guid><pubDate>Wed, 01 Jan 2025 12:30:00 +0000</pubDate>
<description>Exchange listing announcement.</description></item>
</channel></rss>"""

ATOM = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Example Atom</title>
<entry><title>Protocol update</title><id>tag:example.org,2025:item-2</id>
<link rel="alternate" href="/posts/2"/>
<published>2025-02-03T04:05:06+00:00</published>
<summary>Protocol release note.</summary></entry></feed>"""


class FakeResponse:
    status = 200

    def __init__(self, body):
        self.body = body.encode("utf-8")
        self.headers = Message()
        self.headers["Content-Type"] = "application/xml; charset=utf-8"
        self.headers["Last-Modified"] = "Wed, 01 Jan 2025 00:00:00 GMT"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size=-1):
        return self.body[:size]

    def geturl(self):
        return "https://feeds.example/final.xml"


class FeedIngestionTests(unittest.TestCase):
    def test_rss_entries_preserve_provenance_and_are_unverified(self):
        result = parse_feed(RSS, "https://feeds.example/rss.xml", "Publisher", "src", "evd",
                            captured_at="2025-01-02T00:00:00Z")
        self.assertEqual(1, result["entry_count"])
        source, evidence = result["records"]
        self.assertEqual("https://news.example/item/1", source["record"]["url"])
        self.assertEqual("2025-01-01T12:30:00Z", source["record"]["published_at"])
        self.assertIn("item-1", source["record"]["notes"])
        self.assertIn("https://feeds.example/rss.xml", source["record"]["notes"])
        self.assertEqual("UNVERIFIED", evidence["record"]["verification_status"])
        self.assertEqual("2025-01-02T00:00:00Z", evidence["record"]["captured_at"])

    def test_atom_relative_link_and_iso_date(self):
        result = parse_feed(ATOM, "https://feeds.example/atom.xml", "Publisher", "src", "evd")
        source = result["records"][0]["record"]
        self.assertEqual("https://feeds.example/posts/2", source["url"])
        self.assertEqual("2025-02-03T04:05:06Z", source["published_at"])
        self.assertEqual("Protocol update", source["title"])

    def test_unparseable_publication_date_remains_null_but_raw_value_is_kept(self):
        xml = RSS.replace("Wed, 01 Jan 2025 12:30:00 +0000", "date unknown")
        source = parse_feed(xml, "https://feeds.example/rss.xml", "Publisher", "src", "evd")["records"][0]["record"]
        self.assertIsNone(source["published_at"])
        self.assertIn("original_published_value=date unknown", source["notes"])

    def test_rejects_malformed_or_unsupported_xml(self):
        with self.assertRaises(CollectionError):
            parse_feed("<rss>", "https://feeds.example/rss.xml", "Publisher", "src", "evd")
        with self.assertRaises(CollectionError):
            parse_feed("<html/>", "https://feeds.example/rss.xml", "Publisher", "src", "evd")

    def test_collect_feed_uses_http_capture_limits_and_returns_feed_and_entry_records(self):
        result = collect_feed(
            "https://feeds.example/rss.xml", "Publisher", "src", "evd",
            opener=lambda request, timeout: FakeResponse(RSS),
        )
        self.assertEqual(1, result["entry_count"])
        self.assertEqual("https://feeds.example/rss.xml", result["feed_url"])
        self.assertEqual(["Source", "Evidence", "Source", "Evidence"],
                         [record["record_type"] for record in result["records"]])
        self.assertTrue(all(record.get("record", {}).get("verification_status", "UNVERIFIED") == "UNVERIFIED"
                            for record in result["records"] if record["record_type"] == "Evidence"))


if __name__ == "__main__":
    unittest.main()
