"""Opt-in HTTP evidence capture; capture does not imply factual verification."""
from datetime import datetime, timezone
import hashlib
import ipaddress
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

COLLECTOR_VERSION = "1.0.0"
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


def collect_url(url, publisher, source_id, evidence_id, source_type="OTHER",
                title=None, source_published_at=None, timeout=10,
                max_bytes=DEFAULT_MAX_BYTES, opener=None):
    """Capture a public URL into Source and Evidence envelopes.

    The caller supplies the original publication timestamp when known; HTTP
    Last-Modified is retained as transport metadata, not misrepresented as the
    publication timestamp. Content is hashed and not persisted automatically.
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
    # Decode for analyst preview only; preserve exact bytes through the digest.
    charset = "utf-8"
    if headers and headers.get_content_charset():
        charset = headers.get_content_charset()
    try:
        preview = body.decode(charset, errors="replace")[:4000]
    except LookupError:
        preview = body.decode("utf-8", errors="replace")[:4000]
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
            "reliability_assessment": None, "access_method": "HTTP GET",
            "notes": notes,
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
            "records": [source, evidence], "preview": preview}
