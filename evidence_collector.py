"""Opt-in HTTP evidence capture; capture does not imply factual verification."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import ipaddress
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

COLLECTOR_VERSION = "1.1.0"
DEFAULT_MAX_BYTES = 1_000_000
ALLOWED_SOURCE_TYPES = {
    "OFFICIAL_ANNOUNCEMENT", "REGULATORY_FILING", "NEWS_MEDIA",
    "EXCHANGE_DATA", "ONCHAIN_DATA", "SOCIAL_MEDIA", "RESEARCH_REPORT", "OTHER",
}


class CollectionError(RuntimeError):
    """Raised when a source cannot be captured safely or completely."""


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _validate_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise CollectionError("only absolute HTTP(S) URLs are supported")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".localhost"):
        raise CollectionError("localhost URLs are not allowed")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise CollectionError("non-public IP addresses are not allowed")
    return parsed


def _local_name(tag):
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(element, names):
    for child in list(element):
        if _local_name(child.tag) in names:
            text = "".join(child.itertext()).strip()
            if text:
                return text
    return None


def _entry_link(element, feed_url):
    for child in list(element):
        if _local_name(child.tag) != "link":
            continue
        href = child.attrib.get("href")
        rel = child.attrib.get("rel", "alternate")
        if href and rel in {"alternate", ""}:
            return urljoin(feed_url, href)
        text = (child.text or "").strip()
        if text:
            return urljoin(feed_url, text)
    return None


def _publication_timestamp(raw_value):
    """Normalize known RSS/Atom dates to UTC; unknown/unparseable values stay null."""
    if not raw_value:
        return None
    try:
        value = datetime.fromisoformat(raw_value.strip().replace("Z", "+00:00"))
    except ValueError:
        try:
            value = parsedate_to_datetime(raw_value.strip())
        except (TypeError, ValueError, OverflowError):
            return None
    if value.tzinfo is None:
        return None
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_feed(xml_text, feed_url, publisher, source_id, evidence_id, captured_at=None):
    """Parse RSS 2.0 or Atom XML into Source/Evidence envelopes without network access."""
    _validate_url(feed_url)
    if not publisher.strip() or not source_id.strip() or not evidence_id.strip():
        raise CollectionError("publisher, source_id and evidence_id are required")
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise CollectionError(f"malformed feed XML: {exc}") from exc

    root_name = _local_name(root.tag)
    if root_name == "rss":
        channel = next((child for child in list(root) if _local_name(child.tag) == "channel"), None)
        if channel is None:
            raise CollectionError("RSS feed is missing its channel element")
        entries = [child for child in list(channel) if _local_name(child.tag) == "item"]
        feed_title = _child_text(channel, {"title"})
    elif root_name == "feed":
        entries = [child for child in list(root) if _local_name(child.tag) == "entry"]
        feed_title = _child_text(root, {"title"})
    else:
        raise CollectionError("unsupported feed format: expected RSS 2.0 <rss> or Atom <feed>")

    captured_at = captured_at or _utc_now()
    records = []
    for index, entry in enumerate(entries, start=1):
        title = _child_text(entry, {"title"}) or f"Untitled feed entry {index}"
        link = _entry_link(entry, feed_url)
        original_id = _child_text(entry, {"guid", "id"})
        published_raw = _child_text(entry, {"pubdate", "published", "updated", "date"})
        published_at = _publication_timestamp(published_raw)
        summary = _child_text(entry, {"description", "summary", "content", "encoded"}) or ""
        # Hash the parsed entry bytes, not a normalized summary, for stable audit comparisons.
        entry_bytes = ET.tostring(entry, encoding="utf-8")
        digest = hashlib.sha256(entry_bytes).hexdigest()
        suffix = f"{index:04d}"
        item_source_id = f"{source_id}_{suffix}"
        item_evidence_id = f"{evidence_id}_{suffix}"
        item_url = link or feed_url
        # Aggregator feeds (for example Google News) may identify the original
        # publisher on each RSS item. Preserve it instead of labeling every
        # article with the collector/feed name.
        item_publisher = _child_text(entry, {"source"}) or publisher
        provenance = (
            f"feed_url={feed_url}; feed_title={feed_title or ''}; feed_publisher={publisher}; "
            f"item_publisher={item_publisher}; entry_id={original_id or ''}; "
            f"original_published_value={published_raw or ''}; collector_version={COLLECTOR_VERSION}; "
            "Feed metadata is not independent verification of authorship or truth."
        )
        records.append({
            "schema_version": "1.0.0", "record_type": "Source",
            "record": {
                "source_id": item_source_id, "source_type": "NEWS_MEDIA",
                "publisher": item_publisher, "title": title, "url": item_url,
                "published_at": published_at, "retrieved_at": captured_at,
                "content_hash": f"sha256:{digest}", "reliability_assessment": None,
                "access_method": "RSS/Atom feed", "notes": provenance,
            },
        })
        excerpt = summary[:3000] if summary else None
        records.append({
            "schema_version": "1.0.0", "record_type": "Evidence",
            "record": {
                "evidence_id": item_evidence_id, "source_id": item_source_id,
                "claim": "Feed entry metadata and supplied summary were captured for analyst review; no factual claim is asserted by ingestion alone.",
                "evidence_role": "CONTEXTUALIZES", "excerpt_or_locator": excerpt or item_url,
                "captured_at": captured_at, "content_hash": f"sha256:{digest}",
                "verification_method": "RSS/Atom XML parsing with SHA-256 digest; content requires independent review.",
                "verification_status": "UNVERIFIED",
                "limitations": "Feed metadata may be incomplete, altered, duplicated or inaccurate; ingestion does not verify the publisher, entry URL, summary or causal relevance.",
            },
        })
    return {"collector_version": COLLECTOR_VERSION, "captured_at": captured_at,
            "feed_url": feed_url, "feed_title": feed_title or None,
            "entry_count": len(entries), "records": records}


def collect_url(url, publisher, source_id, evidence_id, source_type="OTHER",
                title=None, source_published_at=None, timeout=10,
                max_bytes=DEFAULT_MAX_BYTES, opener=None):
    """Capture a public URL into Source and Evidence envelopes.

    The caller supplies the original publication timestamp when known; HTTP
    Last-Modified is retained as transport metadata, not misrepresented as the
    publication timestamp. The response body is returned as text for opt-in
    feed parsing; callers should respect the configured max_bytes limit.
    """
    _validate_url(url)
    if source_type not in ALLOWED_SOURCE_TYPES:
        raise CollectionError(f"unsupported source_type: {source_type}")
    if not publisher.strip() or not source_id.strip() or not evidence_id.strip():
        raise CollectionError("publisher, source_id and evidence_id are required")
    if timeout <= 0 or max_bytes <= 0:
        raise CollectionError("timeout and max_bytes must be positive")
    request = Request(url, headers={"User-Agent": "CryptoDueDiligence/1.0 (+evidence capture)", "Accept": "*/*"})
    open_url = opener or urlopen
    try:
        with open_url(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            final_url = response.geturl() if hasattr(response, "geturl") else url
            headers = response.headers
            body = response.read(max_bytes + 1)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise CollectionError(f"source capture failed: {exc}") from exc
    if status < 200 or status >= 300:
        raise CollectionError(f"source returned HTTP status {status}")
    if len(body) > max_bytes:
        raise CollectionError(f"response exceeds max_bytes={max_bytes}; capture rejected")
    digest = hashlib.sha256(body).hexdigest()
    captured_at = _utc_now()
    last_modified = headers.get("Last-Modified") if headers else None
    content_type = headers.get("Content-Type", "unknown") if headers else "unknown"
    charset = headers.get_content_charset() if headers else None
    try:
        body_text = body.decode(charset or "utf-8", errors="replace")
    except LookupError:
        body_text = body.decode("utf-8", errors="replace")
    preview = body_text[:4000]
    notes = (
        f"collector_version={COLLECTOR_VERSION}; requested_url={url}; final_url={final_url}; "
        f"http_status={status}; content_type={content_type}; last_modified={last_modified}; "
        "Last-Modified is transport metadata and is not treated as original publication time."
    )
    source = {
        "schema_version": "1.0.0", "record_type": "Source",
        "record": {
            "source_id": source_id, "source_type": source_type, "publisher": publisher,
            "title": title, "url": url, "published_at": source_published_at,
            "retrieved_at": captured_at, "content_hash": f"sha256:{digest}",
            "reliability_assessment": None, "access_method": "HTTP GET", "notes": notes,
        },
    }
    evidence = {
        "schema_version": "1.0.0", "record_type": "Evidence",
        "record": {
            "evidence_id": evidence_id, "source_id": source_id,
            "claim": "Captured source content is available for analyst review; no factual claim is asserted by capture alone.",
            "evidence_role": "CONTEXTUALIZES", "excerpt_or_locator": f"content preview: {preview}",
            "captured_at": captured_at, "content_hash": f"sha256:{digest}",
            "verification_method": "HTTP retrieval with SHA-256 digest; content requires independent review.",
            "verification_status": "UNVERIFIED",
            "limitations": "Capture proves only which bytes were retrieved at capture time, not authorship, truth, completeness or causal relevance.",
        },
    }
    return {"collector_version": COLLECTOR_VERSION, "captured_at": captured_at,
            "content_hash": f"sha256:{digest}", "byte_length": len(body),
            "records": [source, evidence], "preview": preview, "body_text": body_text}


def collect_feed(url, publisher, source_id, evidence_id, timeout=10,
                 max_bytes=DEFAULT_MAX_BYTES, opener=None):
    """Fetch and parse an explicitly supplied RSS 2.0 or Atom feed URL.

    The response size and HTTP(S) URL checks are shared with collect_url. Entry
    publication dates are normalized to UTC when parseable; their original
    text, entry IDs and feed URL are retained in provenance notes.
    """
    capture = collect_url(
        url, publisher, f"{source_id}_capture", f"{evidence_id}_capture",
        source_type="OTHER", title="Feed capture", timeout=timeout,
        max_bytes=max_bytes, opener=opener,
    )
    parsed = parse_feed(
        capture["body_text"], url, publisher, source_id, evidence_id,
        captured_at=capture["captured_at"],
    )
    return {
        "collector_version": COLLECTOR_VERSION, "captured_at": capture["captured_at"],
        "feed_url": url, "feed_title": parsed["feed_title"],
        "entry_count": parsed["entry_count"],
        "content_hash": capture["content_hash"], "byte_length": capture["byte_length"],
        "records": capture["records"] + parsed["records"],
    }
