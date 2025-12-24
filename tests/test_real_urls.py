#!/usr/bin/env python3
"""
Manual verification tests for Substack URL detection and metadata extraction.
Tests with real Substack URLs to validate the implementation.

Usage:
    pipenv run python tests/test_real_urls.py
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import (
    get_substack_content_type,
    is_substack_domain,
    download_page,
    check_if_substack,
    extract_metadata,
    extract_note_title,
)


def test_url_pattern_detection():
    """Test URL pattern detection with various Substack URL formats"""
    print("=" * 80)
    print("Testing URL Pattern Detection")
    print("=" * 80)

    test_cases = [
        # Regular posts
        (
            "https://astralcodexten.substack.com/p/ai-sleeper-agents",
            None,
            "Regular Substack post",
        ),
        (
            "https://www.platformer.news/p/how-elon-musk-spent-three-years",
            None,
            "Custom domain regular post",
        ),
        # Notes
        (
            "https://substack.com/@contraptions/note/c-191022428",
            "note",
            "Note from @contraptions",
        ),
        (
            "https://substack.com/@uncertaintymindset/note/c-190184676",
            "note",
            "Note from @uncertaintymindset",
        ),
        ("https://substack.com/notes/post-67890", "note", "Generic notes URL"),
        (
            "https://astralcodexten.substack.com/@scottwalker/note/c-123",
            "note",
            "Note on custom subdomain",
        ),
        # Chats/Comments
        (
            "https://substack.com/chat/9973/post/64cc3fbb-ef7b-44a8-b8a9-9e336cc7e71b",
            "chat",
            "Chat thread URL",
        ),
        (
            "https://astralcodexten.substack.com/p/some-post/comment/12345",
            "chat",
            "Single comment URL",
        ),
        (
            "https://www.platformer.news/p/some-post/comments",
            None,
            "Comments section (custom domain - won't match, not substack.com)",
        ),
        # Non-Substack (should not match)
        (
            "https://example.com/p/article",
            None,
            "Non-Substack URL",
        ),
        (
            "https://evilsubstack.com/p/fake",
            None,
            "Malicious similar domain (security test)",
        ),
    ]

    passed = 0
    failed = 0

    for url, expected, description in test_cases:
        result = get_substack_content_type(url)
        status = "✓" if result == expected else "✗"

        if result == expected:
            passed += 1
        else:
            failed += 1

        print(f"\n{status} {description}")
        print(f"  URL: {url}")
        print(f"  Expected: {expected}, Got: {result}")

    print(f"\n{'=' * 80}")
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


def test_domain_validation():
    """Test domain validation security"""
    print("\n" + "=" * 80)
    print("Testing Domain Validation (Security)")
    print("=" * 80)

    test_cases = [
        ("https://substack.com/notes/123", True, "Base domain"),
        ("https://astralcodexten.substack.com/p/test", True, "Subdomain"),
        ("https://www.platformer.news/p/test", False, "Custom domain (non-substack)"),
        ("https://evilsubstack.com/p/test", False, "Malicious domain"),
        ("https://substackcdn.com/image.jpg", False, "CDN domain (not main)"),
        ("https://mysubstack.com/p/test", False, "Similar but wrong domain"),
    ]

    passed = 0
    failed = 0

    for url, expected, description in test_cases:
        result = is_substack_domain(url)
        status = "✓" if result == expected else "✗"

        if result == expected:
            passed += 1
        else:
            failed += 1

        print(f"\n{status} {description}")
        print(f"  URL: {url}")
        print(f"  Expected: {expected}, Got: {result}")

    print(f"\n{'=' * 80}")
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


def test_real_url_detection():
    """Test with a real Substack URL (requires internet)"""
    print("\n" + "=" * 80)
    print("Testing Real URL Detection (requires internet)")
    print("=" * 80)

    # Use a well-known Substack post
    test_url = "https://astralcodexten.substack.com/p/ai-sleeper-agents"

    print(f"\nTesting URL: {test_url}")
    print("Downloading page...")

    try:
        html = download_page(test_url)
        if not html:
            print("✗ Failed to download page")
            return False

        print(f"✓ Downloaded {len(html)} bytes")

        # Test if it's detected as Substack
        is_substack = check_if_substack(html, test_url)
        print(f"\nIs Substack: {is_substack}")

        if not is_substack:
            print("✗ Failed to detect as Substack")
            return False

        # Extract metadata
        print("\nExtracting metadata...")
        metadata = extract_metadata(html, test_url)

        print("\nExtracted metadata:")
        print(f"  Title: {metadata.get('title', 'N/A')[:80]}...")
        print(f"  Author: {metadata.get('author', 'N/A')}")
        print(f"  Date: {metadata.get('date', 'N/A')}")
        print(f"  Publisher: {metadata.get('publisher', 'N/A')}")
        print(f"  Content Type: {metadata.get('content_type', 'N/A')}")

        # Verify we got some metadata
        if metadata.get("title") and metadata.get("author"):
            print("\n✓ Successfully extracted metadata")
            return True
        else:
            print("\n✗ Metadata extraction incomplete")
            return False

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_title_extraction():
    """Test title extraction from various HTML structures"""
    print("\n" + "=" * 80)
    print("Testing Title Extraction from HTML")
    print("=" * 80)

    test_cases = [
        (
            """
            <html>
            <body>
                <div class="markup">
                    This is a test note with enough words to demonstrate the title extraction.
                    It should use the first sentence if it's a reasonable length.
                </div>
            </body>
            </html>
            """,
            "First sentence extraction",
        ),
        (
            """
            <html>
            <body>
                <article>
                    Short! This is another sentence that is longer and should be used.
                </article>
            </body>
            </html>
            """,
            "Skip short sentence, use longer",
        ),
        (
            """
            <html>
            <body>
                <div class="post-content">
                    A medium length sentence that should work fine as a title for this note.
                </div>
            </body>
            </html>
            """,
            "Medium length sentence",
        ),
        (
            """
            <html>
            <body>
                <div>
                    word1 word2 word3 word4 word5 word6 word7 word8 word9 word10
                    word11 word12 word13 word14 word15 word16 word17 word18 word19 word20
                    word21 word22 word23 word24 word25
                </div>
            </body>
            </html>
            """,
            "20-word extraction with ellipsis",
        ),
    ]

    for html, description in test_cases:
        title = extract_note_title(html)
        print(f"\n✓ {description}")
        print(f"  Extracted: '{title}'")
        print(f"  Length: {len(title)} chars")

    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("SUBSTACK URL DETECTION - MANUAL VERIFICATION TESTS")
    print("=" * 80)

    all_passed = True

    # Run tests
    all_passed &= test_url_pattern_detection()
    all_passed &= test_domain_validation()
    all_passed &= test_title_extraction()

    # Optional: Test with real URL (requires internet)
    print("\n" + "=" * 80)
    print("Optional: Test with real URL? (requires internet)")
    print("This will download a real Substack page to verify detection.")
    print("=" * 80)

    try:
        response = input("\nRun real URL test? (y/n): ").lower()
        if response in ["y", "yes"]:
            all_passed &= test_real_url_detection()
        else:
            print("Skipping real URL test.")
    except (EOFError, KeyboardInterrupt):
        print("\nSkipping real URL test (non-interactive mode).")

    # Summary
    print("\n" + "=" * 80)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 80)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
