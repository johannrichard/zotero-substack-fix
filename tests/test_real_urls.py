#!/usr/bin/env python3
"""
Manual verification tests for Substack URL detection and metadata extraction.
Tests with real Substack URLs to validate the implementation.

Usage:
    pipenv run python tests/test_real_urls.py
    
To use auto-discovered test cases:
    1. Run: pipenv run python tools/discover_substack_urls.py --use-defaults --test-output tests/discovered_test_urls.py
    2. Uncomment the import below to include discovered URLs in tests
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


try:
    from discovered_test_urls import DISCOVERED_TEST_CASES
    USE_DISCOVERED = True
except ImportError:
    DISCOVERED_TEST_CASES = []
    USE_DISCOVERED = False

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
            "Chat thread URL with numeric ID",
        ),
        (
            "https://open.substack.com/chat/posts/64cc3fbb-ef7b-44a8-b8a9-9e336cc7e71b",
            "chat",
            "Chat posts URL (plural)",
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
    
    # Add discovered test cases if available
    if USE_DISCOVERED:
        print(f"\nAdding {len(DISCOVERED_TEST_CASES)} auto-discovered test cases")
        for discovered in DISCOVERED_TEST_CASES:
            # Handle both tuple and dict formats
            if isinstance(discovered, dict):
                # Dict format with metadata
                url = discovered["url"]
                expected = discovered["expected_type"]
                description = discovered["description"]
            else:
                # Tuple format
                url, expected, description = discovered
            test_cases.append((url, expected, description))

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
    """Test with real Substack URLs (requires internet)"""
    print("\n" + "=" * 80)
    print("Testing Real URL Detection (requires internet)")
    print("=" * 80)

    # Collect URLs to test  
    test_urls = [{"url": "https://astralcodexten.substack.com/p/ai-sleeper-agents"}]
    
    # Add discovered URLs if available
    if USE_DISCOVERED:
        print(f"\nAdding {len(DISCOVERED_TEST_CASES)} discovered URLs to real URL tests")
        
        for discovered in DISCOVERED_TEST_CASES:
            # Handle both tuple and dict formats
            if isinstance(discovered, dict):
                test_urls.append(discovered)
            else:
                # Tuple format - convert to dict
                url, expected_type, description = discovered
                test_urls.append({"url": url, "expected_type": expected_type, "description": description})
    
    passed = 0
    failed = 0
    
    for test in test_urls:
        test_url = test["url"]
        expected_metadata = test.get("expected_metadata", {})
        
        print(f"\n{'-' * 80}")
        print(f"Testing URL: {test_url}")
        print("Downloading page...")

        try:
            html = download_page(test_url)
            if not html:
                print("✗ Failed to download page")
                failed += 1
                continue

            print(f"✓ Downloaded {len(html)} bytes")

            # Test if it's detected as Substack
            is_substack = check_if_substack(html, test_url)
            print(f"Is Substack: {is_substack}")

            if not is_substack:
                print("✗ Failed to detect as Substack")
                failed += 1
                continue

            # Extract metadata
            print("Extracting metadata...")
            metadata = extract_metadata(html, test_url)

            print("\nExtracted metadata:")
            print(f"  Title: {metadata.get('title', 'N/A')}")
            print(f"  Author: {metadata.get('author', 'N/A')}")
            print(f"  Date: {metadata.get('date', 'N/A')}")
            print(f"  Publisher: {metadata.get('publisher', 'N/A')}")
            print(f"  Content Type: {metadata.get('content_type', 'N/A')}")

            # Validate metadata if expectations provided
            validation_passed = True
            if expected_metadata:
                print("\nValidating against expected metadata:")
                
                if "title" in expected_metadata:
                    expected_title = expected_metadata["title"]
                    actual_title = metadata.get("title", "")
                    if expected_title == actual_title:
                        print(f"  ✓ Title matches")
                    else:
                        print(f"  ℹ Title differs (may be due to Substack updates):")
                        print(f"    Expected: {expected_title}")
                        print(f"    Got: {actual_title}")
                
                if "title_has_ellipsis" in expected_metadata:
                    # This means Substack's JSON-LD includes ellipsis (expected)
                    has_ellipsis = metadata.get("title", "").endswith("...")
                    if has_ellipsis:
                        print(f"  ✓ Title has ellipsis from Substack (expected)")
                
                if "should_have_ellipsis" in expected_metadata:
                    # This means we generated the title and should have added ellipsis
                    should_have = expected_metadata["should_have_ellipsis"]
                    has_ellipsis = metadata.get("title", "").endswith("...")
                    if should_have == has_ellipsis:
                        print(f"  ✓ Ellipsis {'present' if has_ellipsis else 'absent'} as expected")
                    else:
                        print(f"  ✗ Ellipsis validation failed:")
                        print(f"    Should have ellipsis: {should_have}")
                        print(f"    Actually has ellipsis: {has_ellipsis}")
                        validation_passed = False

            # Verify we got some metadata
            if metadata.get("title") and (metadata.get("author") or metadata.get("content_type") in ["note", "chat"]):
                if validation_passed:
                    print("✓ Successfully extracted metadata")
                    passed += 1
                else:
                    print("✗ Metadata validation failed")
                    failed += 1
            else:
                print("✗ Metadata extraction incomplete")
                failed += 1

        except Exception as e:
            print(f"✗ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'=' * 80}")
    print(f"Results: {passed} passed, {failed} failed out of {len(test_urls)} URLs")
    
    print(f"\n{'=' * 80}")
    return failed == 0


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
            "This is a test note with enough words to demonstrate the title extraction",
            False,  # Should NOT have ellipsis
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
            "This is another sentence that is longer and should be used",
            False,  # Should NOT have ellipsis
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
            "A medium length sentence that should work fine as a title for this note",
            False,  # Should NOT have ellipsis
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
            "20-word extraction with ellipsis (25 words total)",
            "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12 word13 word14 word15 word16 word17 word18 word19 word20",
            True,  # SHOULD have ellipsis (more than 20 words)
        ),
        (
            """
            <html>
            <body>
                <div class="markup">
                    This has exactly fifteen words so it should not add any ellipsis at all.
                </div>
            </body>
            </html>
            """,
            "Short content (15 words) - NO ellipsis",
            "This has exactly fifteen words so it should not add any ellipsis at all",
            False,  # Should NOT have ellipsis (only 15 words, less than 20)
        ),
        (
            """
            <html>
            <body>
                <div class="markup">
                    Five words only here.
                </div>
            </body>
            </html>
            """,
            "Very short content (5 words) - NO ellipsis",
            "Five words only here",
            False,  # Should NOT have ellipsis (only 5 words)
        ),
        (
            """
            <html>
            <body>
                <div class="markup">
                    This sentence has exactly twenty words which is the threshold for word extraction so no ellipsis should be added here.
                </div>
            </body>
            </html>
            """,
            "Exactly 20 words - NO ellipsis",
            "This sentence has exactly twenty words which is the threshold for word extraction so no ellipsis should be added here",
            False,  # Should NOT have ellipsis (exactly 20 words)
        ),
    ]

    passed = 0
    failed = 0

    for html, description, expected_text, should_have_ellipsis in test_cases:
        title = extract_note_title(html)
        has_ellipsis = title.endswith("...")
        
        # Check if ellipsis presence matches expectation
        ellipsis_correct = has_ellipsis == should_have_ellipsis
        
        # Check if the text content (without ellipsis) matches expected
        title_text = title.rstrip(".")
        expected_clean = expected_text.rstrip(".")
        text_matches = title_text == expected_clean or title_text == expected_clean + "..."
        
        if ellipsis_correct and text_matches:
            status = "✓"
            passed += 1
        else:
            status = "✗"
            failed += 1
            
        print(f"\n{status} {description}")
        print(f"  Extracted: '{title}'")
        print(f"  Length: {len(title)} chars, Words: {len(title.replace('...', '').split())}")
        print(f"  Has ellipsis: {has_ellipsis} (expected: {should_have_ellipsis})")
        
        if not ellipsis_correct:
            print(f"  ⚠️  ELLIPSIS MISMATCH!")
        if not text_matches:
            print(f"  ⚠️  TEXT MISMATCH!")
            print(f"  Expected: '{expected_text}'")

    print(f"\n{'=' * 80}")
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


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
