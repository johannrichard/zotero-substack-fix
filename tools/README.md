# Development Tools

This directory contains utility tools for development and testing.

## discover_substack_urls.py

A tool to automatically discover public Substack posts and notes for use in testing.

### Features

- **Discovers regular posts** from Substack subdomains (e.g., `example.substack.com/p/article`)
- **Discovers notes** using `/@username/note/` pattern search
- **Discovers chat/comment URLs** including `/chat/` threads and post comment sections
- **Uses verified starting URLs** for better discovery results
- **Rate limiting** to be respectful to Substack servers
- **Multiple output formats** (JSON, Python test data)

### Usage

Basic usage to discover URLs:

```bash
pipenv run python tools/discover_substack_urls.py
```

This will search for:

- 3 Substack domains
- 2 posts per domain
- 3 notes
- 2 chat URLs

**Recommended**: Use the `--use-defaults` flag to start from verified URLs:

```bash
pipenv run python tools/discover_substack_urls.py --use-defaults
```

This uses known good starting points:
- Notes from @contraptions and @uncertaintymindset
- Chat threads from verified discussions

### Advanced Options

```bash
# Use default starting URLs (recommended)
pipenv run python tools/discover_substack_urls.py --use-defaults

# Customize discovery limits
pipenv run python tools/discover_substack_urls.py --domains 5 --posts 3 --notes 5 --chats 3

# Save results to JSON file
pipenv run python tools/discover_substack_urls.py --output discovered_urls.json

# Generate Python test data
pipenv run python tools/discover_substack_urls.py --test-output tests/discovered_urls.py

# Adjust delay between requests (in seconds)
pipenv run python tools/discover_substack_urls.py --delay 2.0
```

### Command Line Options

- `--domains N` - Number of Substack domains to explore (default: 3)
- `--posts N` - Number of posts per domain (default: 2)
- `--notes N` - Number of notes to find (default: 3)
- `--chats N` - Number of chat URLs to find (default: 2)
- `--output FILE` - Save discovered URLs to JSON file
- `--test-output FILE` - Save as Python test data
- `--delay SECONDS` - Delay between requests (default: 1.0)
- `--use-defaults` - Use verified starting URLs (recommended)

### Default Starting URLs

When using `--use-defaults`, the tool starts from these verified URLs:

**Notes:**
- `https://substack.com/@contraptions/note/c-191022428`
- `https://substack.com/@uncertaintymindset/note/c-190184676`

**Chats:**
- `https://substack.com/chat/9973/post/64cc3fbb-ef7b-44a8-b8a9-9e336cc7e71b`

These URLs are guaranteed to resolve and can help discover related content from active Substack users.

### How It Works

1. **Starting URLs (optional)**: If `--use-defaults` is used, starts with verified URLs
2. **Domain Discovery**: Explores known popular Substacks and optionally searches Substack's browse page
3. **Post Discovery**: Visits archive pages of discovered domains and extracts `/p/` URLs
4. **Note Discovery**: Searches Substack's notes feed for `/@username/note/` patterns
5. **Chat Discovery**: Searches for `/chat/` thread URLs and post comment sections

### Example Output

JSON format:

```json
{
  "posts": [
    "https://astralcodexten.substack.com/p/some-article",
    "https://platformer.news/p/another-article"
  ],
  "notes": [
    "https://substack.com/@username/note/p-12345"
  ],
  "chats": [
    "https://astralcodexten.substack.com/p/some-article/comments"
  ]
}
```

Python test data format:

```python
# Test cases format (ready for test_real_urls.py)
DISCOVERED_TEST_CASES = [
    (
        "https://astralcodexten.substack.com/p/some-article",
        None,
        "Discovered regular post",
    ),
    (
        "https://substack.com/@username/note/p-12345",
        "note",
        "Discovered note",
    ),
    (
        "https://substack.com/chat/123/post/uuid",
        "chat",
        "Discovered chat",
    ),
]

# Raw URLs by type (for compatibility)
DISCOVERED_TEST_URLS = {
    "posts": [
        "https://astralcodexten.substack.com/p/some-article",
    ],
    "notes": [
        "https://substack.com/@username/note/p-12345",
    ],
    "chats": [
        "https://substack.com/chat/123/post/uuid",
    ],
}
```

### Integrating with Tests

The discovery tool generates test cases in a format that `test_real_urls.py` can directly import and use.

**Step 1: Generate test data**

```bash
# Recommended: use verified starting URLs
pipenv run python tools/discover_substack_urls.py --use-defaults --test-output tests/discovered_test_urls.py
```

**Step 2: Use in test_real_urls.py**

Open `tests/test_real_urls.py` and uncomment the import:

```python
# Uncomment these lines:
try:
    from discovered_test_urls import DISCOVERED_TEST_CASES
    USE_DISCOVERED = True
except ImportError:
    DISCOVERED_TEST_CASES = []
    USE_DISCOVERED = False
```

And uncomment the code that adds discovered test cases:

```python
# Uncomment this block:
if USE_DISCOVERED:
    print(f"\nAdding {len(DISCOVERED_TEST_CASES)} auto-discovered test cases")
    test_cases.extend(DISCOVERED_TEST_CASES)
```

**Step 3: Run tests**

```bash
pipenv run python tests/test_real_urls.py
```

The tests will now include both the manually defined test cases and the auto-discovered ones.

### Example Workflow

Complete workflow to discover and test URLs:

```bash
# 1. Discover URLs from verified starting points
pipenv run python tools/discover_substack_urls.py --use-defaults --test-output tests/discovered_test_urls.py

# 2. Edit tests/test_real_urls.py to uncomment the import section

# 3. Run tests with discovered URLs
pipenv run python tests/test_real_urls.py

# Output will show:
# - 11 manually defined test cases
# - N auto-discovered test cases
# - Total: 11+N test cases
```

### Notes

- **Rate Limiting**: The tool includes a configurable delay between requests to avoid overwhelming servers
- **Best Effort**: Some URLs may not be accessible or may return errors - this is normal
- **Dynamic Content**: Substack's structure may change over time, so the tool may need updates
- **Respectful Usage**: Please use reasonable limits and delays when running this tool
