# Development Tools

This directory contains utility tools for development and testing.

## discover_substack_urls.py

A tool to automatically discover public Substack posts and notes for use in testing.

### Features

- **Discovers regular posts** from Substack subdomains (e.g., `example.substack.com/p/article`)
- **Discovers notes** using `/@username/note/` pattern search
- **Discovers chat/comment URLs** from post comment sections
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

### Advanced Options

```bash
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

### How It Works

1. **Domain Discovery**: Starts with known popular Substacks and optionally searches Substack's browse page
2. **Post Discovery**: Visits archive pages of discovered domains and extracts `/p/` URLs
3. **Note Discovery**: Searches Substack's notes feed for `/@username/note/` patterns
4. **Chat Discovery**: Visits post URLs and checks for `/comments` sections

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
DISCOVERED_TEST_URLS = {
    "posts": [
        "https://astralcodexten.substack.com/p/some-article",
    ],
    "notes": [
        "https://substack.com/@username/note/p-12345",
    ],
    "chats": [
        "https://astralcodexten.substack.com/p/some-article/comments",
    ],
}
```

### Integrating with Tests

To use discovered URLs in your tests:

```bash
# Generate test data
pipenv run python tools/discover_substack_urls.py --test-output tests/discovered_urls.py

# Import in your tests
from discovered_urls import DISCOVERED_TEST_URLS

# Use in test cases
for url in DISCOVERED_TEST_URLS["posts"]:
    test_post_detection(url)
```

### Notes

- **Rate Limiting**: The tool includes a configurable delay between requests to avoid overwhelming servers
- **Best Effort**: Some URLs may not be accessible or may return errors - this is normal
- **Dynamic Content**: Substack's structure may change over time, so the tool may need updates
- **Respectful Usage**: Please use reasonable limits and delays when running this tool
