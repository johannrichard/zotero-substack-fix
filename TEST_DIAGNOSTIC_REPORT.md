# TEST FAILURE DIAGNOSTIC REPORT
**Date:** 2026-02-01  
**Test Suite Status:** 11/16 tests passing (5 failures)

---

## EXECUTIVE SUMMARY

All 5 test failures are related to **title extraction mismatches** between expected values in `tests/data.yaml` and actual JSON-LD content in HTML fixtures. The failures stem from three distinct issues:

1. **LinkedIn Articles** (2 failures): Code extracts wrong JSON-LD field
2. **LinkedIn SocialMediaPosting** (2 failures): Test expectations don't match fixture content
3. **Substack Note** (1 failure): Fixture updated with additional content (URL)

---

## FAILURE ANALYSIS

### FAILURE #1 & #2: LinkedIn Articles - Field Selection Bug

**Affected Tests:**
- `linkedin_pulseeu_space_top_5_priorities_2024_beyond_thierry_breton_dmkhe`
- `linkedin_pulsebusiness_development_issues_space_industry_satsearch_03mae`

**Problem:**
LinkedIn Article JSON-LD contains TWO title-like fields:
- `name`: The actual article title (e.g., "EU Space: the Top 5 Priorities for 2024 and beyond")
- `headline`: The article's opening paragraph text

**Current Code Logic (lines 294-297):**
```python
if target_item.get("@type") in ["NewsArticle", "BlogPosting", "Article"]:
    metadata["title"] = target_item.get("headline", target_item.get("name", ""))
```

**What happens:** Code prioritizes `headline` over `name`, extracting the opening paragraph instead of the actual title.

**Example - EU Space Article:**
```
Expected (from test):  "EU Space: the Top 5 Priorities for 2024 and beyond"
What's in 'name':      "EU Space: the Top 5 Priorities for 2024 and beyond" ✓
What's in 'headline':  "Over the past four years of this mandate, we have achieved..." ✗
Code extracts:         "Over the past four years of this mandate..." (headline) ✗
```

**Root Cause:** For LinkedIn Articles, `headline` contains body text, not the title. The code should use `name` instead.

**Fix Required:** Change the field extraction order for Article type to prefer `name` over `headline`.

---

### FAILURE #3 & #4: LinkedIn SocialMediaPosting - Test Expectations Don't Match Fixtures

**Affected Tests:**
- `linkedin_postschaveso_chevy_cook_cynical_on_sinek...`
- `linkedin_postssimonwardley_when_people_say_chinas_deepseek...`

**Problem:**
Test expectations specify titles that **do not appear anywhere in the JSON-LD** of the actual fixtures.

**Example - Chaveso Cook Post:**
```
Expected (from test):  "Cynical on Sinek: Why Simon Sinek's Works Fall Short for Leaders"
What's in fixture:
  - headline:     "Here's a why to start with… why do so many people listen to Simon Sinek??"
  - articleBody:  "Here's a why to start with… why do so many people listen to Simon Sinek?? ..."
  - No field contains the expected title!
```

**Current Code Behavior:**
For SocialMediaPosting, code uses `text` or `articleBody` with 20-word truncation:
```python
full_text = target_item.get("text", target_item.get("articleBody", ""))
words = full_text.split()
metadata["title"] = " ".join(words[:TITLE_FALLBACK_WORD_LIMIT])
if len(words) > TITLE_FALLBACK_WORD_LIMIT:
    metadata["title"] += " ..."
```

**What it extracts:** "Here's a why to start with… why do so many people listen to Simon Sinek?? Another: Why do we value ..."

**Root Cause:** 
- The fixtures appear to be recently re-downloaded/updated
- The test expectations are based on old fixture data or manually specified expected values
- The actual JSON-LD in current fixtures doesn't contain the expected titles

**Fix Options:**
1. Update test expectations to match actual fixture content
2. Re-download fixtures to match test expectations (if expectations are correct)
3. Use `headline` field for SocialMediaPosting when available (consider code change)

---

### FAILURE #5: Substack Note - Fixture Contains Additional Content

**Affected Test:**
- `substack_contraptionsnotec_138536158`

**Problem:**
The fixture text includes a URL that wasn't in the test expectation.

```
Expected (from test):
"Haven't thought about my piece cited here (the GUTs thing from 2018) 
in a long time. I think what Ben"

Actual in fixture:
"Haven't thought about my piece cited here (the GUTs thing from 2018, 
https://contraptions.venkateshrao.com/p/guts-the-grand-unified-theory-of) 
in a long time. I think what @Ben Reinhardt..."
```

**Root Cause:** Fixture was updated with more complete/current content from Substack, which now includes the URL inline.

**Fix Required:** Update test expectation to match the current fixture content.

---

## DETAILED FIELD STRUCTURE ANALYSIS

### LinkedIn Article JSON-LD Structure:
```json
{
  "@type": "Article",
  "name": "EU Space: the Top 5 Priorities for 2024 and beyond",  ← ACTUAL TITLE
  "headline": "Over the past four years of this mandate...",      ← OPENING TEXT
  "author": {...}
}
```

### LinkedIn SocialMediaPosting JSON-LD Structure:
```json
{
  "@type": "SocialMediaPosting",
  "headline": "Here's a why to start with…",      ← Post opening
  "articleBody": "Here's a why to start with…",   ← Full text (used by code)
  "author": {...}
}
```

### Substack Note JSON-LD Structure:
```json
{
  "@type": "SocialMediaPosting",
  "text": "Haven't thought about my piece cited here (the GUTs thing from 2018, https://...) ...",
  "author": {...}
}
```

---

## RECOMMENDED FIXES

### Priority 1: LinkedIn Articles (HIGH IMPACT - Code Fix)
**Change:** Modify extraction logic to prefer `name` over `headline` for Article type.

**Current code (line 294-297):**
```python
if target_item.get("@type") in ["NewsArticle", "BlogPosting", "Article"]:
    metadata["title"] = target_item.get("headline", target_item.get("name", ""))
```

**Suggested fix:**
```python
if target_item.get("@type") in ["NewsArticle", "BlogPosting", "Article"]:
    metadata["title"] = target_item.get("name", target_item.get("headline", ""))
```

**Impact:** Will fix 2 LinkedIn Article tests immediately.

---

### Priority 2: LinkedIn SocialMediaPosting (Test Data Fix)
**Change:** Update test expectations in `tests/data.yaml` to match actual fixture content.

**For Chaveso Cook post:**
```yaml
# Current (wrong):
title: "Cynical on Sinek: Why Simon Sinek's Works Fall Short for Leaders"

# Update to (matches fixture):
title: "Here's a why to start with… why do so many people listen to Simon Sinek??"
```

**For Simon Wardley post:**
```yaml
# Current (wrong):
title: "When people say China's DeepSeek bombshell"

# Update to (matches fixture):
title: "When people say \"China's DeepSeek Bombshell\" - https://lnkd.in/eUnYsTvq what they really mean is China's obvious and well signalled move towards ..."
```

**Impact:** Will fix 2 SocialMediaPosting tests.

---

### Priority 3: Substack Note (Test Data Fix)
**Change:** Update test expectation to include the URL.

```yaml
# Current (missing URL):
title: "Haven't thought about my piece cited here (the GUTs thing from 2018) in a long time. I think what Ben"

# Update to (includes URL):
title: "Haven't thought about my piece cited here (the GUTs thing from 2018, https://contraptions.venkateshrao.com/p/guts-the-grand-unified-theory-of) in a long time. I think what ..."
```

**Impact:** Will fix 1 Substack test.

---

## IMPLEMENTATION CHECKLIST

- [ ] Fix code: Change Article field priority from `headline` to `name`
- [ ] Update test: Chaveso Cook SocialMediaPosting title expectation
- [ ] Update test: Simon Wardley SocialMediaPosting title expectation  
- [ ] Update test: Substack note c-138536158 title expectation (add URL)
- [ ] Run full test suite to verify all 16 tests pass

---

## ADDITIONAL NOTES

### Why SocialMediaPosting Tests Failed
The fixtures appear to have been updated/re-downloaded recently, but the test expectations weren't updated accordingly. This suggests:
1. Fixtures may have been regenerated from live URLs
2. LinkedIn may have changed how they structure their JSON-LD
3. Test expectations may have been manually created rather than extracted from fixtures

### Code vs Test Data Issues
- **Code issues:** 1 (LinkedIn Article field selection)
- **Test data issues:** 4 (3 LinkedIn posts + 1 Substack note with outdated expectations)

### Alternative Approach for SocialMediaPosting
Consider modifying the code to check for and use `headline` field first for SocialMediaPosting:
```python
else:  # For SocialMediaPosting, Comments, etc.
    # Try headline first for SocialMediaPosting
    if target_item.get("@type") == "SocialMediaPosting" and target_item.get("headline"):
        metadata["title"] = target_item.get("headline")
    else:
        # Fallback to 20-word truncation
        full_text = target_item.get("text", target_item.get("articleBody", ""))
        words = full_text.split()
        metadata["title"] = " ".join(words[:TITLE_FALLBACK_WORD_LIMIT])
        if len(words) > TITLE_FALLBACK_WORD_LIMIT:
            metadata["title"] += " ..."
```

This would better match the LinkedIn SocialMediaPosting structure.

---

## CONCLUSION

**Root causes:**
1. Code bug: Wrong field extraction for LinkedIn Articles
2. Stale test data: Test expectations don't match updated fixtures

**Recommended approach:**
1. Fix the code bug (Article field priority)
2. Update test expectations to match current fixtures
3. Optionally: Improve SocialMediaPosting handling to use headline when available

**Expected outcome:** All 16 tests passing after fixes applied.

