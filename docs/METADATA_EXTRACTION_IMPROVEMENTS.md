# Metadata Extraction Improvements for Notes and Chats

## Overview

This document describes the improvements made to metadata extraction for Substack notes and chats based on real-world test cases.

## Problem Statement

The original implementation had limitations when extracting metadata from Substack notes and chats:

1. **Title truncation**: Notes were artificially truncated to ~20 words with ellipsis added
2. **Limited author extraction**: Only checked basic meta tags
3. **Mismatch with expectations**: Test cases showed the full content should be used as the title

## Solution

### 1. Enhanced Title Extraction

**For notes and chats, the content IS the title.** Substack notes are typically short-form content where the entire text serves as both the content and the title.

#### Changes to `extract_note_title()`:

**Before:**
```python
# Extracted first sentence (10-100 chars) or first 20 words + "..."
words = content.split()
title = " ".join(words[:NOTE_TITLE_WORD_COUNT])  # First 20 words
if len(words) > NOTE_TITLE_WORD_COUNT:
    title += "..."  # Added ellipsis if truncated
```

**After:**
```python
# Extract the FULL content as the title
content = re.sub(r"\s+", " ", content).strip()
return content if content else "Substack Note"
```

#### Improved Content Selectors

Added more specific CSS selectors for Substack's HTML structure:

```python
selectors = [
    'div.body',                           # Most common for notes
    'div[class*="note-content"]',
    'div[class*="post-body"]',
    'div[class*="post-content"]',
    'div[data-testid*="post-body"]',     # Testid attributes
    'div[data-testid*="note-body"]',
    "article p",                          # Paragraph-based content
    'div.markup',
    'div[class*="body"]',
    "article",
]
```

### 2. Enhanced Author Extraction

Implemented a **multi-strategy fallback approach** to find authors:

#### Strategy 1: Meta Tags
```python
# Look for standard author meta tags
author_meta = soup.find("meta", attrs={"name": "author"}) or \
              soup.find("meta", attrs={"property": "article:author"})
```

#### Strategy 2: OpenGraph and Twitter Cards
```python
# Check OpenGraph and Twitter card metadata
og_author = soup.find("meta", attrs={"property": "og:author"}) or \
           soup.find("meta", attrs={"property": "author"}) or \
           soup.find("meta", attrs={"name": "twitter:creator"})
```

#### Strategy 3: HTML Elements
```python
# Search in page elements
author_selectors = [
    'a[href*="/@"]',              # Substack profile links (/@username)
    'a[class*="author"]',
    'span[class*="author"]',
    'div[class*="byline"]',
    '[data-testid*="author"]',
]
```

**Special handling for Substack profile links:**
```python
# For links like /@username, extract the username
if '/@' in href:
    match = re.search(r'/@([^/]+)', href)
    if match:
        author_name = match.group(1)
```

#### Strategy 4: Embedded JSON-LD
```python
# Parse additional JSON-LD scripts that might contain author info
scripts = soup.find_all("script", type="application/ld+json")
for script in scripts:
    data = json.loads(script.string)
    if data.get("author"):
        # Extract from various formats (dict or string)
```

## Test Cases Validation

The improvements were validated against real test cases:

### Note 1: `/@contraptions/note/c-191022428`
```python
expected = {
    "title": "Leibnizian aesthetics: All is for the most beautiful in this most beautiful of all worlds",
    "author": "Venkatesh Rao",
    "should_not_add_ellipsis": True,
}
```
✅ **Result**: Full title extracted, author found in meta tag, no ellipsis

### Note 2: `/@uncertaintymindset/note/c-190184676`
```python
expected = {
    "title": "Those who manage to break the vicious cycle of avoiding discomfort and becoming less able to deal with discomfort eventually realize that productive discomfort is tolerable and can lead to great and unexpected things.",
    "author": "Vaughn Tan",
    "should_not_add_ellipsis": True,
}
```
✅ **Result**: Full 200+ character title extracted, no truncation

### Chat: `/chat/9973/post/...`
```python
expected = {
    "title": "Ok I'm convinced the divergence machine is alive and operational",
    "author": "PAtwater",
    "should_not_add_ellipsis": True,
}
```
✅ **Result**: Full chat message as title, author from OpenGraph meta

## Benefits

1. **Accurate Representation**: Notes and chats now preserve their full content as titles
2. **No Artificial Truncation**: Removed the 20-word limit and ellipsis for notes/chats
3. **Robust Author Attribution**: Multiple fallback strategies ensure authors are found
4. **Better User Experience**: Users see the actual note/chat content, not a truncated version
5. **Matches Substack Behavior**: Extraction matches how Substack presents this content

## Backward Compatibility

- Regular blog posts are **not affected** by these changes
- Changes only apply when `content_type in ["note", "chat"]`
- All existing functionality for regular posts is preserved

## Implementation Details

### Key Functions Modified

1. **`extract_note_title(html, soup)`**
   - Returns full content instead of truncating
   - Improved CSS selectors
   - Better whitespace normalization

2. **`extract_metadata(html, url)`**
   - Enhanced author extraction for notes/chats
   - Multi-strategy fallback approach
   - Special handling for Substack profile links

### Performance Considerations

- **Single HTML parse**: BeautifulSoup instance is reused
- **Early returns**: Strategies exit as soon as author is found
- **Efficient selectors**: Uses specific CSS selectors for targeted extraction

## Testing

### Unit Tests

Test the extraction functions with sample HTML:

```python
from main import extract_note_title, extract_metadata

# Test title extraction
html = '<div class="body">Full note content here</div>'
title = extract_note_title(html)
assert title == "Full note content here"

# Test author extraction
html_with_author = '''
<meta name="author" content="John Doe">
<div class="body">Content</div>
'''
metadata = extract_metadata(html_with_author, "https://substack.com/@user/note/123")
assert metadata["author"] == "John Doe"
```

### Integration Tests

The `discovered_test_urls.py` file contains real URLs with expected metadata for validation.

## Future Improvements

Potential areas for enhancement:

1. **Publisher extraction**: Extract publication name for notes/chats
2. **Date extraction**: Better date parsing for notes
3. **Hashtag extraction**: Parse hashtags from note content
4. **Thread support**: Handle threaded conversations in chats
5. **Media extraction**: Extract embedded images, videos from notes

## References

- Test cases: `tests/discovered_test_urls.py`
- Main implementation: `src/main.py`
- Testing guide: `docs/TESTING_GUIDE.md`
