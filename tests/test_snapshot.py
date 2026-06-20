#!/usr/bin/env python3
"""
Unit tests for get_snapshot_html – snapshot attachment retrieval.
All tests use mocks so no live Zotero connection is required.
"""

import io
import sys
import os
import zipfile
from unittest.mock import MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import get_snapshot_html  # noqa: E402


def _make_zip(html_content: str, filename: str = "index.html") -> bytes:
    """Return bytes of a zip archive containing one HTML file."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(filename, html_content)
    return buf.getvalue()


def _mock_zot(children, file_content=None):
    """Build a minimal mock Pyzotero client."""
    zot = MagicMock()
    zot.children.return_value = children
    if file_content is not None:
        zot.file.return_value = file_content
    return zot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_HTML = "<html><head></head><body><p>Hello snapshot</p></body></html>"

SNAPSHOT_CHILD = {
    "key": "SNAP0001",
    "data": {
        "itemType": "attachment",
        "contentType": "text/html",
        "linkMode": "imported_url",
    },
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_html_from_zip_snapshot():
    """HTML is extracted from a zip-based snapshot attachment."""
    zip_bytes = _make_zip(SAMPLE_HTML)
    zot = _mock_zot([SNAPSHOT_CHILD], file_content=zip_bytes)

    result = get_snapshot_html(zot, "ITEM0001")

    assert SAMPLE_HTML in result
    zot.children.assert_called_once_with("ITEM0001")
    zot.file.assert_called_once_with("SNAP0001")
    print("✅ HTML extracted from zip snapshot")


def test_returns_raw_html_when_not_zip():
    """Raw HTML bytes (not zipped) are decoded and returned."""
    zot = _mock_zot([SNAPSHOT_CHILD], file_content=SAMPLE_HTML.encode("utf-8"))

    result = get_snapshot_html(zot, "ITEM0001")

    assert SAMPLE_HTML in result
    print("✅ Raw HTML bytes decoded and returned")


def test_returns_empty_when_no_snapshot_attachment():
    """Items with no HTML snapshot attachment yield an empty string."""
    non_snapshot = {
        "key": "PDF0001",
        "data": {
            "itemType": "attachment",
            "contentType": "application/pdf",
            "linkMode": "imported_file",
        },
    }
    zot = _mock_zot([non_snapshot])

    result = get_snapshot_html(zot, "ITEM0001")

    assert result == ""
    zot.file.assert_not_called()
    print("✅ Non-HTML attachment is ignored")


def test_returns_empty_when_no_children():
    """Items with no children yield an empty string."""
    zot = _mock_zot([])

    result = get_snapshot_html(zot, "ITEM0001")

    assert result == ""
    print("✅ Empty children list handled gracefully")


def test_skips_linked_url_attachment():
    """Attachments with linkMode 'linked_url' (not a stored snapshot) are skipped."""
    linked_child = {
        "key": "LINK0001",
        "data": {
            "itemType": "attachment",
            "contentType": "text/html",
            "linkMode": "linked_url",
        },
    }
    zot = _mock_zot([linked_child])

    result = get_snapshot_html(zot, "ITEM0001")

    assert result == ""
    zot.file.assert_not_called()
    print("✅ linked_url attachment correctly skipped")


def test_skips_failed_download_and_continues():
    """A failed file download is logged and the function returns empty string."""
    zot = _mock_zot([SNAPSHOT_CHILD])
    zot.file.side_effect = Exception("Network error")

    result = get_snapshot_html(zot, "ITEM0001")

    assert result == ""
    print("✅ Download failure handled gracefully")


def test_children_api_error_returns_empty():
    """An error from zot.children() is handled and returns empty string."""
    zot = MagicMock()
    zot.children.side_effect = Exception("API error")

    result = get_snapshot_html(zot, "ITEM0001")

    assert result == ""
    print("✅ children() API error handled gracefully")


def test_zip_with_nested_html_uses_root_file():
    """When the zip has both a root and nested HTML file, the root one is preferred."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("index.html", SAMPLE_HTML)
        zf.writestr("subdir/other.html", "<html>nested</html>")
    zip_bytes = buf.getvalue()

    zot = _mock_zot([SNAPSHOT_CHILD], file_content=zip_bytes)
    result = get_snapshot_html(zot, "ITEM0001")

    assert SAMPLE_HTML in result
    print("✅ Root-level HTML file preferred over nested one")


def test_imported_file_link_mode_also_supported():
    """Snapshots stored with linkMode 'imported_file' are also retrieved."""
    child = {
        "key": "SNAP0002",
        "data": {
            "itemType": "attachment",
            "contentType": "text/html",
            "linkMode": "imported_file",
        },
    }
    zip_bytes = _make_zip(SAMPLE_HTML)
    zot = _mock_zot([child], file_content=zip_bytes)

    result = get_snapshot_html(zot, "ITEM0001")

    assert SAMPLE_HTML in result
    print("✅ imported_file linkMode is supported")


if __name__ == "__main__":
    print("Running snapshot retrieval tests...\n")
    test_returns_html_from_zip_snapshot()
    test_returns_raw_html_when_not_zip()
    test_returns_empty_when_no_snapshot_attachment()
    test_returns_empty_when_no_children()
    test_skips_linked_url_attachment()
    test_skips_failed_download_and_continues()
    test_children_api_error_returns_empty()
    test_zip_with_nested_html_uses_root_file()
    test_imported_file_link_mode_also_supported()
    print("\n✨ All snapshot tests passed!")
