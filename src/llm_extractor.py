#!/usr/bin/env python3
# Copyright (c) 2025 Johann Richard. All rights reserved.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""
LLM-powered metadata extraction fallback.

When regular JSON-LD / extruct extraction yields incomplete metadata (missing
title or author), this module fetches a fully-rendered copy of the page using
a headless Playwright/Chromium browser and asks an LLM to extract structured
metadata from the visible text.

The returned dict has the same shape as the one produced by
``extract_metadata`` in main.py:

    {
        "title":     str,
        "author":    str,
        "date":      str,   # ISO-8601 or empty
        "publisher": str,
        "type":      str,   # JSON-LD @type hint, or empty
    }

Configuration (all via environment variables):

    LLM_ENABLED   – set to "true" to activate the fallback (default: false)
    LLM_PROVIDER  – "openai" | "anthropic" | "gemini"  (default: "openai")
    LLM_MODEL     – model name, e.g. "gpt-4o-mini"     (default: "gpt-4o-mini")
    LLM_API_KEY   – provider API key
    LLM_MAX_CHARS – max characters of page text to send to the LLM (default: 12000)
"""

import json
import logging
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# How much rendered page text (characters) to feed to the LLM.
# Keeps the prompt within a safe token budget for most models.
DEFAULT_MAX_CHARS = 12_000

_SYSTEM_PROMPT = """\
You are a metadata extraction assistant. Given the visible text of a web page,
extract the following fields and return ONLY a JSON object — no explanation,
no markdown fences.

Required JSON keys (use empty string "" when a value cannot be determined):
  title       – the main title or headline of the article / post / note
  author      – the human author's full name (NOT a platform or company name)
  date        – publication date in ISO-8601 format (YYYY-MM-DD), or ""
  publisher   – the name of the publication, newsletter, or platform
  type        – one of: "NewsArticle", "BlogPosting", "SocialMediaPosting",
                "DiscussionForumPosting", "Comment", "Article", or ""

Rules:
- "author" must be a real person's name. If only an organisation name is
  present, set author to "".
- Do not invent or guess values; use "" for genuinely unknown fields.
- Return valid JSON only.
"""

_EMPTY: Dict[str, str] = {
    "title": "",
    "author": "",
    "date": "",
    "publisher": "",
    "type": "",
}


def is_llm_enabled() -> bool:
    """Return True when the LLM fallback is enabled via environment."""
    return os.getenv("LLM_ENABLED", "false").lower() in ("1", "true", "yes")


def _fetch_rendered_text(url: str, max_chars: int) -> Optional[str]:
    """
    Fetch a page using headless Chromium (Playwright) and return its
    visible text content, truncated to *max_chars*.

    Returns None when Playwright is unavailable or the fetch fails.
    """
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        logger.warning(
            "LLM fallback: playwright is not installed. "
            "Run 'pip install playwright && playwright install chromium' to enable it."
        )
        return None

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=20_000)
            text = page.inner_text("body")
            browser.close()
        return text[:max_chars] if text else None
    except Exception as exc:
        logger.warning(f"LLM fallback: Playwright fetch failed for {url}: {exc}")
        return None


def _call_openai(text: str, model: str, api_key: str) -> Dict[str, str]:
    """Call OpenAI chat completions and return extracted metadata."""
    from openai import OpenAI  # type: ignore

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0,
    )
    raw = response.choices[0].message.content or "{}"
    return json.loads(raw)


def _call_anthropic(text: str, model: str, api_key: str) -> Dict[str, str]:
    """Call Anthropic Messages API and return extracted metadata."""
    import anthropic  # type: ignore

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=512,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    raw = message.content[0].text if message.content else "{}"
    # Strip accidental markdown fences
    raw = (
        raw.strip()
        .removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )
    return json.loads(raw)


def _call_gemini(text: str, model: str, api_key: str) -> Dict[str, str]:
    """Call Google Gemini API and return extracted metadata."""
    import google.generativeai as genai  # type: ignore

    genai.configure(api_key=api_key)
    gemini_model = genai.GenerativeModel(
        model_name=model,
        system_instruction=_SYSTEM_PROMPT,
        generation_config={"response_mime_type": "application/json"},
    )
    response = gemini_model.generate_content(text)
    raw = response.text or "{}"
    return json.loads(raw)


def _normalise(raw: Dict) -> Dict[str, str]:
    """Coerce the LLM response into the expected flat string dict."""
    result = dict(_EMPTY)
    for key in _EMPTY:
        val = raw.get(key, "")
        result[key] = str(val).strip() if val else ""
    return result


def extract_metadata_with_llm(url: str) -> Dict[str, str]:
    """
    Fetch *url* with a headless browser and extract metadata using an LLM.

    Returns a metadata dict in the same shape as ``extract_metadata`` in
    main.py.  On any failure returns a dict of empty strings so the caller
    can safely merge the result.
    """
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    api_key = os.getenv("LLM_API_KEY", "")
    max_chars = int(os.getenv("LLM_MAX_CHARS", str(DEFAULT_MAX_CHARS)))

    if not api_key:
        logger.warning("LLM fallback: LLM_API_KEY is not set — skipping.")
        return dict(_EMPTY)

    logger.info(f"LLM fallback: fetching rendered page for {url}")
    text = _fetch_rendered_text(url, max_chars)
    if not text:
        logger.warning("LLM fallback: no page text retrieved — skipping.")
        return dict(_EMPTY)

    logger.info(f"LLM fallback: calling {provider} ({model}) for metadata extraction")
    try:
        if provider == "openai":
            raw = _call_openai(text, model, api_key)
        elif provider == "anthropic":
            raw = _call_anthropic(text, model, api_key)
        elif provider == "gemini":
            raw = _call_gemini(text, model, api_key)
        else:
            logger.warning(f"LLM fallback: unknown provider '{provider}' — skipping.")
            return dict(_EMPTY)

        metadata = _normalise(raw)
        logger.info(
            f"LLM fallback: extracted title='{metadata['title'][:60]}' "
            f"author='{metadata['author']}'"
        )
        return metadata

    except Exception as exc:
        logger.warning(f"LLM fallback: extraction failed: {exc}")
        return dict(_EMPTY)
