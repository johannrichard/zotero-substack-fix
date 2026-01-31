# Testing Guide: Substack Notes, Posts, and Chats

## Overview

This guide explains how to test the Substack content detection and metadata extraction features, including the new support for notes and chats.

## Quick Start

### Run All Tests

```bash
cd /path/to/zotero-substack-fix
python tests/test_real_urls.py
```

This will run:
1. URL pattern detection tests (11 test cases)
2. Domain validation tests (6 test cases) 
3. Title extraction tests (7 test cases)
4. Real URL tests (with discovered URLs if available)

## Generating Test Cases with Metadata

### Basic Discovery (No Metadata)

```bash
python tools/discover_substack_urls.py \
  --use-defaults \
  --test-output tests/discovered_test_urls.py
```

This generates simple test cases in tuple format:
```python
DISCOVERED_TEST_CASES = [
    ("https://example.substack.com/p/post", None, "Discovered regular post"),
    ("https://substack.com/@user/note/123", "note", "Discovered note"),
]
```

### Discovery with Metadata Validation

```bash
python tools/discover_substack_urls.py \
  --use-defaults \
  --with-metadata \
  --test-output tests/discovered_test_urls.py
```

This generates rich test cases with expected metadata:
```python
DISCOVERED_TEST_CASES = [
    {
        "url": "https://example.substack.com/p/post",
        "expected_type": None,
        "description": "Discovered regular post",
        "expected_metadata": {
            "title": "The Actual Title...",  # From Substack JSON-LD
            "author": "Author Name",
            "title_has_ellipsis": True,  # Substack added ellipsis
        }
    },
    {
        "url": "https://substack.com/@user/note/123",
        "expected_type": "note",
        "description": "Discovered note",
        "expected_metadata": {
            "title": "First twenty words of the note content...",
            "should_have_ellipsis": True,  # We truncated to 20 words
        }
    },
]
```

## Understanding Ellipsis Validation

### Ellipsis from Substack

Regular blog posts often have titles ending in "..." in Substack's JSON-LD metadata. This is **expected behavior** from Substack:

```
Title: "AI Sleeper Agents..."
```

Test flag: `"title_has_ellipsis": True`

### Ellipsis from Our Code

When generating titles for notes/chats, we add "..." only when content exceeds 20 words:

```python
# Content with 25 words
"word1 word2 word3 ... word20..."  # We added ellipsis

# Content with 15 words
"word1 word2 word3 ... word15"  # NO ellipsis
```

Test flag: `"should_have_ellipsis": True/False`

## Test Validation

### URL Pattern Detection

Tests verify that URLs are correctly categorized:
- Regular posts: `None` (default type)
- Notes: `"note"`
- Chats: `"chat"`

Patterns tested:
```python
# Posts
"https://example.substack.com/p/article"         → None
"https://custom-domain.com/p/article"            → None

# Notes  
"https://substack.com/@user/note/c-123"          → "note"
"https://substack.com/notes/post-123"            → "note"

# Chats
"https://substack.com/chat/9973/post/uuid"       → "chat"
"https://open.substack.com/chat/posts/uuid"      → "chat"
"https://example.substack.com/p/post/comment/1"  → "chat"
```

### Metadata Validation

When test cases include `expected_metadata`, tests validate:

1. **Title Matching**: Actual title matches expected
2. **Ellipsis Correctness**:
   - `title_has_ellipsis`: Verifies Substack provided ellipsis
   - `should_have_ellipsis`: Verifies we added/didn't add ellipsis correctly
3. **Author Attribution**: Checks author extraction

Example output:
```
✓ Title matches
✓ Title has ellipsis from Substack (expected)
✓ Ellipsis absent as expected
```

## Discovery Tool Options

### Full Command Reference

```bash
python tools/discover_substack_urls.py \
  --domains 3 \           # Number of Substack domains to explore
  --posts 2 \             # Posts per domain
  --notes 3 \             # Number of notes to find
  --chats 2 \             # Number of chat URLs to find
  --delay 1.0 \           # Delay between requests (seconds)
  --use-defaults \        # Use known good starting URLs
  --with-metadata \       # Extract metadata (requires dependencies)
  --test-output FILE \    # Output Python test file
  --output FILE           # Output JSON file
```

### Starting URLs

When using `--use-defaults`, the tool starts from known good URLs:

**Notes:**
- `https://substack.com/@contraptions/note/c-191022428`
- `https://substack.com/@uncertaintymindset/note/c-190184676`

**Chats:**
- `https://substack.com/chat/9973/post/64cc3fbb-ef7b-44a8-b8a9-9e336cc7e71b`
- `https://open.substack.com/chat/posts/64cc3fbb-ef7b-44a8-b8a9-9e336cc7e71b`

## Test File Integration

### Enable Discovered Tests

In `tests/test_real_urls.py`, the discovered tests are imported:

```python
try:
    from discovered_test_urls import DISCOVERED_TEST_CASES
    USE_DISCOVERED = True
except ImportError:
    DISCOVERED_TEST_CASES = []
    USE_DISCOVERED = False
```

Tests automatically include discovered URLs when `USE_DISCOVERED=True`.

### Test Format Compatibility

The test suite handles both formats automatically:

```python
# Tuple format (backward compatible)
for url, expected, description in test_cases:
    ...

# Dict format (with metadata)
if isinstance(test_case, dict):
    url = test_case["url"]
    expected_metadata = test_case.get("expected_metadata", {})
    ...
```

## Troubleshooting

### Chat URLs Not Detected

If chat URLs like `https://open.substack.com/chat/posts/...` aren't detected:

1. Check pattern in `src/main.py`:
   ```python
   chat_patterns = [
       r"/chat/\d+/post/",  # Numeric ID
       r"/chat/posts/",     # Plural posts
       r"/p/[^/]+/comment/",
       r"/p/[^/]+/comments",
   ]
   ```

2. Verify domain validation:
   ```python
   is_substack_domain(url)  # Must return True
   ```

### Metadata Extraction Fails

If metadata extraction fails during discovery:

1. Ensure dependencies are installed:
   ```bash
   pip install beautifulsoup4 extruct w3lib
   ```

2. Check `METADATA_AVAILABLE` flag:
   ```python
   try:
       from main import extract_metadata
       METADATA_AVAILABLE = True
   except ImportError:
       METADATA_AVAILABLE = False
   ```

3. Run from repo root or add src to path

### Test Failures

If tests fail unexpectedly:

1. **Check internet connection**: Real URL tests require network access
2. **Substack changes**: Substack may update their HTML/metadata structure
3. **Rate limiting**: Add `--delay 2.0` for slower requests
4. **Metadata mismatches**: Substack may update post titles/authors

## Best Practices

### 1. Generate Fresh Test Cases

Regenerate discovered tests periodically:
```bash
python tools/discover_substack_urls.py --use-defaults --with-metadata --test-output tests/discovered_test_urls.py
```

### 2. Use Metadata Validation for Critical Tests

For important test cases, use dict format with metadata:
```python
{
    "url": "https://...",
    "expected_metadata": {
        "title": "Expected Title",
        "should_have_ellipsis": False,  # Validate ellipsis logic
    }
}
```

### 3. Test Both Patterns

Always test both chat URL patterns:
- `/chat/\d+/post/` (with numeric ID)
- `/chat/posts/` (without ID)

### 4. Validate Ellipsis Logic

Include tests that verify:
- Short content (≤20 words) → NO ellipsis
- Long content (>20 words) → ellipsis added
- Substack's ellipsis preserved

## Example Workflow

### Complete Testing Cycle

```bash
# 1. Generate test cases with metadata
python tools/discover_substack_urls.py \
  --use-defaults \
  --with-metadata \
  --test-output tests/discovered_test_urls.py

# 2. Run all tests
python tests/test_real_urls.py

# 3. Review output
# - Check pattern detection (should be 100%)
# - Verify metadata matches expectations
# - Ensure no extra ellipsis added

# 4. If tests fail, investigate
# - Check Substack URLs directly in browser
# - Verify metadata extraction logic
# - Update expected values if Substack changed
```

## Summary

- ✅ Use `--with-metadata` for rich test cases with validation
- ✅ Tests handle both tuple and dict formats
- ✅ Ellipsis validation distinguishes Substack's vs ours
- ✅ All discovered URLs tested automatically
- ✅ Detailed output helps debug failures
