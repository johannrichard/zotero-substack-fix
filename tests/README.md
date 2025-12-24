# Manual Verification Tests

This directory contains manual verification tests for the Substack URL detection and metadata extraction functionality.

## Test Files

### `test_real_urls.py`

Comprehensive manual tests that verify:

1. **URL Pattern Detection**: Tests various Substack URL formats including:
   - Regular posts (`/p/article-name`)
   - Notes (`/@username/note/`, `/notes/`)
   - Chats/Comments (`/p/article/comment/`, `/p/article/comments`)
   - Security: Validates rejection of malicious domains like `evilsubstack.com`

2. **Domain Validation**: Security tests ensuring:
   - Proper Substack domains are accepted (`substack.com`, `*.substack.com`)
   - Malicious domains are rejected
   - Similar but wrong domains are rejected

3. **Title Extraction**: Tests HTML parsing for note titles:
   - First sentence extraction (if 10-100 chars)
   - Fallback to first 20 words
   - Various HTML structures

4. **Real URL Test** (optional, requires internet):
   - Downloads an actual Substack page
   - Verifies detection and metadata extraction
   - Validates author, title, date extraction

## Running the Tests

### Basic Tests (no internet required)
```bash
pipenv run python tests/test_real_urls.py
```

When prompted, type 'n' to skip the real URL test.

### Full Tests (requires internet)
```bash
pipenv run python tests/test_real_urls.py
```

When prompted, type 'y' to run the real URL test.

### Non-interactive Mode
```bash
echo "n" | pipenv run python tests/test_real_urls.py
```

## Expected Output

The tests will show:
- ✓ for passing tests
- ✗ for failing tests
- Summary of passed/failed tests
- Detailed output for each test case

## Test Coverage

These tests validate:
- URL pattern matching for all content types
- Security of domain validation
- Title extraction from various HTML structures
- Integration with real Substack pages (optional)
- Metadata extraction from JSON-LD and HTML

## Adding New Tests

To add new test cases:
1. Add to the appropriate test function in `test_real_urls.py`
2. Follow the existing pattern: `(url, expected_result, description)`
3. Run tests to verify
