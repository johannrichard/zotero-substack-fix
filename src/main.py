#!/usr/bin/env python3
# Copyright (c) 2025 Johann Richard. All rights reserved.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import os
import re
import argparse
import logging
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import extruct
from w3lib.html import get_base_url
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from pyzotero import zotero
from dateutil import parser as date_parser
import asyncio
import yaml
from streaming import ZoteroStreamHandler
from dataclasses import dataclass

# Setup logging (initial level, will be reconfigured based on debug flag)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def setup_logging(debug: bool = False) -> None:
    """Configure logging level based on debug flag."""
    log_level = logging.DEBUG if debug else logging.INFO
    if debug:
        log_format = "%(asctime)s [%(levelname)-8s] %(name)s:%(lineno)d | %(message)s"
        date_format = "%H:%M:%S"
    else:
        log_format = "%(asctime)s [%(levelname)-8s] %(message)s"
        date_format = "%H:%M:%S"

    formatter = logging.Formatter(log_format, datefmt=date_format)
    for handler in logging.root.handlers:
        handler.setFormatter(formatter)

    logger.setLevel(log_level)
    # Also update the root logger
    logging.getLogger().setLevel(log_level)


# Constants
TITLE_FALLBACK_WORD_LIMIT = 20  # APA citation style: first 20 words for posts/comments

# Statistics for reporting
stats = {
    "processed": 0,
    "substackFound": 0,
    "linkedinFound": 0,
    "updated": 0,
    "errors": 0,
    "urls_cleaned": 0,
}


def clean_url(url: str) -> str:
    """
    Clean URL by removing tracking parameters

    Args:
        url: URL to clean

    Returns:
        Cleaned URL string
    """
    try:
        # Parse URL
        parsed = urlparse(url)

        # Get query parameters
        params = parse_qs(parsed.query, keep_blank_values=True)

        # List of parameters to remove
        remove_params = [
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "source",
            "ref",
            "referral",
            "eType",
            "mc_cid",
            "mc_eid",
            "fbclid",
            "ref_src",
            "ref_url",
            "_hsenc",
            "_hsmi",
            "hs_preview",
            "preview",
            "r",
            "s",
            "gclid",
            "ocid",
            "msclkid",
            "dclid",
            "igshid",
        ]

        # Remove tracking parameters
        cleaned_params = {
            k: v for k, v in params.items() if k.lower() not in remove_params
        }

        # Reconstruct URL
        cleaned = parsed._replace(query=urlencode(cleaned_params, doseq=True))
        cleaned_url = urlunparse(cleaned)

        # Remove trailing '?' if no parameters left
        if cleaned_url.endswith("?"):
            cleaned_url = cleaned_url[:-1]

        return cleaned_url

    except Exception as e:
        logger.warning(f"Warning: Could not clean URL '{url}': {str(e)}")
        return url


def mask_key(key: str) -> str:
    """Simple function to mask API key for display purposes."""
    if not key or len(key) < 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"


@dataclass
class ZoteroConfig:
    """Zotero API configuration"""

    api_key: str
    library_id: str
    library_type: str = "user"

    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "ZoteroConfig":
        """Load configuration from environment variables"""
        if env_file:
            load_dotenv(env_file)

        api_key = os.getenv("ZOTERO_API_KEY")
        library_id = os.getenv("ZOTERO_LIBRARY_ID")
        library_type = os.getenv("ZOTERO_LIBRARY_TYPE", "user")

        if not api_key:
            raise ValueError("ZOTERO_API_KEY is not set in environment")
        if not library_id:
            raise ValueError("ZOTERO_LIBRARY_ID is not set in environment")

        return cls(api_key=api_key, library_id=library_id, library_type=library_type)


def get_zotero_client(config: ZoteroConfig) -> zotero.Zotero:
    """Create and return a Pyzotero client instance."""
    logger.info(f"Connecting to Zotero API with key: {mask_key(config.api_key)}")
    logger.info(f"Library type: {config.library_type}, Library ID: {config.library_id}")

    return zotero.Zotero(config.library_id, config.library_type, config.api_key)


def download_page(url: str) -> str:
    """
    Download HTML content from a URL

    Args:
        url: URL to download

    Returns:
        HTML content as string
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to download {url}: {str(e)}")
        return ""


def is_substack_note_url(url: str) -> bool:
    """
    Check if URL is a Substack note/forum post

    Args:
        url: URL to check

    Returns:
        Boolean indicating if it's a note/forum post
    """
    note_patterns = [
        r"substack\.com/@[\w-]+/note/",
        r"substack\.com/notes/",
        r"substack\.com/@[\w-]+/p/comments/",
        r"substack\.com/profile/\d+-[\w-]+/note/",
    ]
    return any(re.search(pattern, url, re.IGNORECASE) for pattern in note_patterns)


def check_if_substack(html: str, url: str) -> bool:
    """
    Check if the HTML content is from a Substack site using LD+JSON metadata

    Args:
        html: HTML content to check
        url: Original URL

    Returns:
        Boolean indicating if it's a Substack site
    """
    if not html or is_substack_note_url(url):
        return False

    # Extract JSON-LD data
    metadata = extruct.extract(
        html, base_url=get_base_url(html, url), syntaxes=["json-ld"]
    )

    # Look for Substack-specific patterns in JSON-LD
    if metadata.get("json-ld"):
        for item in metadata["json-ld"]:
            # Check for NewsArticle type
            if item.get("@type") == "NewsArticle":
                # Check for Substack-specific patterns in publisher or URLs
                publisher = item.get("publisher", {})
                if any(
                    [
                        "substack.com" in str(item.get("url", "")),
                        "substackcdn.com" in str(item.get("image", "")),
                        publisher.get("url", "").endswith("substack.com"),
                        isinstance(publisher.get("identifier", ""), str)
                        and publisher.get("identifier", "").startswith("pub:"),
                    ]
                ):
                    return True

    return False


def extract_metadata(html: str, url: str) -> Dict[str, str]:
    """
    Extracts metadata from JSON-LD. Handles Articles, Posts, and Comments.
    Maintains full author names as found in the source.
    """
    metadata = {"title": "", "author": "", "date": "", "publisher": "", "type": ""}
    if not html:
        return metadata

    try:
        data = extruct.extract(
            html, base_url=get_base_url(html, url), syntaxes=["json-ld"]
        )
        json_ld = data.get("json-ld", [])

        # Check if this is a LinkedIn URL
        is_linkedin = "linkedin.com" in url.lower()
        # LinkedIn comment URLs use /feed/update/ pattern
        is_linkedin_feed_update = is_linkedin and "/feed/update/" in url

        # Priority Search: 1. Comments (including nested), 2. Articles/Posts
        target_item = None

        # For LinkedIn /feed/update/ pages, check if there are nested comments
        # If comments exist in the JSON-LD, it IS a comment page
        if is_linkedin_feed_update:
            for item in json_ld:
                if item.get("@type") == "SocialMediaPosting" and "comment" in item:
                    comments = item.get("comment", [])
                    if comments and len(comments) > 0:
                        # Extract the first comment from the nested array
                        target_item = comments[0]
                        break

        # If no nested comment found, search at top level for Comment
        if not target_item:
            for item in json_ld:
                if item.get("@type") == "Comment":
                    target_item = item
                    break

        # If still no comment, look for articles/posts
        if not target_item:
            for item in json_ld:
                if item.get("@type") in [
                    "NewsArticle",
                    "BlogPosting",
                    "SocialMediaPosting",
                    "DiscussionForumPosting",
                    "Article",
                ]:
                    target_item = item
                    break

        if target_item:
            # Store the @type for reference
            metadata["type"] = target_item.get("@type", "")

            # 1. Author (Exact string preservation)
            author_field = target_item.get("author")
            if isinstance(author_field, list) and author_field:
                metadata["author"] = author_field[0].get("name", "")
            elif isinstance(author_field, dict):
                metadata["author"] = author_field.get("name", "")
            else:
                metadata["author"] = str(author_field) if author_field else ""

            # 2. Title Logic (Headline vs. 20-word Text fallback)
            if target_item.get("@type") in ["NewsArticle", "BlogPosting", "Article"]:
                metadata["title"] = target_item.get(
                    "name", target_item.get("headline", "")
                )
            else:
                # Fallback for Posts/Comments (APA Style)
                full_text = target_item.get("text", target_item.get("articleBody", ""))
                words = full_text.split()
                metadata["title"] = " ".join(words[:TITLE_FALLBACK_WORD_LIMIT])
                if len(words) > TITLE_FALLBACK_WORD_LIMIT:
                    metadata["title"] += " ..."

            # 3. Date & Publisher
            metadata["date"] = (
                target_item.get("datePublished")
                or target_item.get("dateCreated")
                or target_item.get("dateModified")
                or ""
            )
            publisher = target_item.get("publisher", {})
            metadata["publisher"] = (
                publisher.get("name", "") if isinstance(publisher, dict) else ""
            )

    except Exception as e:
        logger.warning(f"Extraction Error: {e}")

    return metadata


def validate_item_fields(item_data: Dict) -> Dict:
    """
    Validate and clean item fields based on item type to prevent sending
    invalid fields to Zotero API.

    Based on Zotero API v3 schema documentation:
    - forumPost item type has valid field: forumTitle
      (https://www.zotero.org/support/dev/web_api/v3/types_and_fields)
    - blogPost item type has valid field: blogTitle
    - Sending incompatible fields will cause API validation errors

    Args:
        item_data: Dictionary containing item data with itemType and other fields

    Returns:
        Cleaned item data with only valid fields for the item type

    References:
        Zotero Schema: https://github.com/zotero/zotero-schema
        API Docs: https://www.zotero.org/support/dev/web_api/v3/types_and_fields
    """
    item_type = item_data.get("itemType")

    # Create a copy to avoid modifying the original
    validated_data = dict(item_data)

    # Remove incompatible fields based on item type per Zotero schema
    if item_type == "forumPost":
        # Per Zotero schema: forumPost uses forumTitle, not blogTitle
        # Valid fields include: forumTitle, postType, title, creators, etc.
        if "blogTitle" in validated_data:
            del validated_data["blogTitle"]
    elif item_type == "blogPost":
        # Per Zotero schema: blogPost uses blogTitle, not forumTitle
        # Valid fields include: blogTitle, websiteType, title, creators, etc.
        if "forumTitle" in validated_data:
            del validated_data["forumTitle"]

    return validated_data


def prepare_substack_item_update(item: Dict, metadata: Dict[str, str]) -> Dict:
    """
    Prepare an updated Zotero item with extracted metadata
    """
    # Create a copy of the item data
    updated_data = dict(item["data"])

    # Update item type (use forumPost for comments/notes/social media posts)
    if metadata.get("type") in [
        "Comment",
        "DiscussionForumPosting",
        "SocialMediaPosting",
    ]:
        updated_data["itemType"] = "forumPost"
    else:
        updated_data["itemType"] = "blogPost"
    updated_data["websiteType"] = "Substack Newsletter"

    if metadata["title"]:
        updated_data["title"] = metadata["title"]

    # Update blog/forum title based on item type per Zotero schema
    # Per Zotero API: forumPost uses 'forumTitle', blogPost uses 'blogTitle'
    # Reference: https://www.zotero.org/support/dev/web_api/v3/types_and_fields
    if metadata["publisher"]:
        if updated_data["itemType"] == "forumPost":
            updated_data["forumTitle"] = metadata["publisher"]
        else:
            updated_data["blogTitle"] = metadata["publisher"]

    # Handle date parsing and updates
    if metadata["date"]:
        try:
            # Parse metadata date
            meta_date = date_parser.parse(metadata["date"])
            meta_date_str = meta_date.strftime("%Y-%m-%d")
            logger.debug(f"Parsed metadata date: {metadata['date']} → {meta_date_str}")

            # Parse current date if it exists
            current_date_str = updated_data.get("date", "").strip()
            if current_date_str:
                try:
                    current_date = date_parser.parse(current_date_str)
                    current_date_str = current_date.strftime("%Y-%m-%d")
                    logger.debug(
                        f"Parsed current date: {updated_data['date']} → {current_date_str}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Warning: Could not parse existing date '{current_date_str}': {str(e)}"
                    )
                    current_date_str = ""

            # Update if no date exists or dates are different
            if not current_date_str or current_date_str != meta_date_str:
                logger.debug(
                    f"Date will be updated: {current_date_str or 'Not set'} → {meta_date_str}"
                )
                updated_data["date"] = meta_date_str
            else:
                logger.debug(f"Dates match, no update needed: {current_date_str}")

        except Exception as e:
            logger.warning(
                f"Warning: Could not parse metadata date '{metadata['date']}': {str(e)}"
            )
            # If parsing fails, use the original date string only if no date exists
            if not updated_data.get("date"):
                updated_data["date"] = metadata["date"]
                logger.debug(f"Using original metadata date string: {metadata['date']}")

    # Update creators if author is available and no creators exist
    if metadata["author"] and (
        not updated_data.get("creators") or len(updated_data["creators"]) == 0
    ):
        name_parts = metadata["author"].split()
        if name_parts:
            last_name = name_parts[-1]
            first_name = " ".join(name_parts[:-1])

            updated_data["creators"] = [
                {
                    "firstName": first_name,
                    "lastName": last_name,
                    "creatorType": "author",
                }
            ]

    # Add a tag for Substack if not already present
    if "tags" not in updated_data:
        updated_data["tags"] = []

    if not any(tag["tag"] == "Substack" for tag in updated_data["tags"]):
        updated_data["tags"].append({"tag": "Substack"})

    # Validate fields before returning
    return validate_item_fields(updated_data)


def prepare_linkedin_item_update(item: Dict, metadata: Dict[str, str]) -> Dict:
    """
    Prepare an updated Zotero item with extracted LinkedIn metadata

    Args:
        item: Original Zotero item
        metadata: Extracted metadata dictionary from LinkedIn page
    """
    updated_data = dict(item["data"])

    if metadata.get("type") in [
        "Comment",
        "DiscussionForumPosting",
        "SocialMediaPosting",
    ]:
        updated_data["itemType"] = "forumPost"
    else:
        updated_data["itemType"] = "blogPost"
    updated_data["websiteType"] = "LinkedIn"

    if metadata["title"]:
        updated_data["title"] = metadata["title"]

    # Update blog/forum title based on item type per Zotero schema
    # Per Zotero API: forumPost uses 'forumTitle', blogPost uses 'blogTitle'
    # Reference: https://www.zotero.org/support/dev/web_api/v3/types_and_fields
    if metadata["publisher"]:
        if updated_data["itemType"] == "forumPost":
            updated_data["forumTitle"] = metadata["publisher"]
        else:
            updated_data["blogTitle"] = metadata["publisher"]

    if metadata["date"]:
        try:
            meta_date = date_parser.parse(metadata["date"])
            meta_date_str = meta_date.strftime("%Y-%m-%d")
            logger.debug(f"Parsed metadata date: {metadata['date']} → {meta_date_str}")

            current_date_str = updated_data.get("date", "").strip()
            if current_date_str:
                try:
                    current_date = date_parser.parse(current_date_str)
                    current_date_str = current_date.strftime("%Y-%m-%d")
                    logger.debug(
                        f"Parsed current date: {updated_data['date']} → {current_date_str}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Warning: Could not parse existing date '{current_date_str}': {str(e)}"
                    )
                    current_date_str = ""

            if not current_date_str or current_date_str != meta_date_str:
                logger.debug(
                    f"Date will be updated: {current_date_str or 'Not set'} → {meta_date_str}"
                )
                updated_data["date"] = meta_date_str
            else:
                logger.debug(f"Dates match, no update needed: {current_date_str}")

        except Exception as e:
            logger.warning(
                f"Warning: Could not parse metadata date '{metadata['date']}': {str(e)}"
            )
            if not updated_data.get("date"):
                updated_data["date"] = metadata["date"]
                logger.debug(f"Using original metadata date string: {metadata['date']}")

    if metadata["author"] and (
        not updated_data.get("creators") or len(updated_data["creators"]) == 0
    ):
        name_parts = metadata["author"].split()
        if name_parts:
            last_name = name_parts[-1]
            first_name = " ".join(name_parts[:-1])

            updated_data["creators"] = [
                {
                    "firstName": first_name,
                    "lastName": last_name,
                    "creatorType": "author",
                }
            ]

    if "tags" not in updated_data:
        updated_data["tags"] = []

    if not any(tag["tag"] == "LinkedIn" for tag in updated_data["tags"]):
        updated_data["tags"].append({"tag": "LinkedIn"})

    # Validate fields before returning
    return validate_item_fields(updated_data)


def process_item(
    item: Dict,
    exclude_substack: bool = False,
    exclude_linkedin: bool = False,
    force: bool = False,
) -> Optional[Dict]:
    """
    Process a single Zotero item, cleaning URL and checking for Substack/LinkedIn metadata

    Args:
        item: Zotero item to process

    Returns:
        Updated item data if changes needed, None otherwise
    """
    url = item["data"].get("url")
    if not url:
        return None

    title = item["data"].get("title", "")
    logger.debug(f"\nProcessing {title[:50]}... ({url})")

    # Create a copy of the item data for potential updates
    updated_data = dict(item["data"])
    needs_update = False

    # Clean URL first

    cleaned_url = clean_url(url)
    if cleaned_url != url:
        updated_data["url"] = cleaned_url
        needs_update = True
        logger.debug(f"Cleaned URL: {url} → {cleaned_url}")

    # Download and check for Substack/LinkedIn only if we haven't already categorized it
    if force or not (
        any(tag["tag"] == "zotero:processed" for tag in item["data"].get("tags", []))
    ):
        is_linkedin = "linkedin.com" in url.lower()

        if exclude_linkedin and is_linkedin:
            logger.debug(f"- Skipping LinkedIn post (excluded): {title[:50]}...")
            return updated_data if needs_update else None

        if exclude_substack and not exclude_linkedin and not is_linkedin:
            logger.debug(
                f"- Skipping non-LinkedIn item (Substack excluded): {title[:50]}..."
            )
            return updated_data if needs_update else None

        html = download_page(cleaned_url)

        is_substack = html and (
            check_if_substack(html, url) or is_substack_note_url(url)
        )
        metadata = extract_metadata(html, url) if html else {}

        if html and (is_substack or is_linkedin):
            global stats
            if is_substack:
                logger.info(f"✓ Substack detected for: {title[:50]}...")
                stats["substackFound"] += 1
            else:
                logger.info(f"✓ LinkedIn detected for: {title[:50]}...")
                stats["linkedinFound"] += 1
            if is_substack:
                updated_data = prepare_substack_item_update(item, metadata)
            else:
                updated_data = prepare_linkedin_item_update(item, metadata)

            updated_data["url"] = cleaned_url
            needs_update = True

            logger.info("Metadata updates:")
            logger.info("----------------")

            # Type
            old_type = item["data"].get("itemType", "Not set")
            new_type = updated_data.get("itemType", "Not set")
            if old_type != new_type:
                logger.info(f"Type: {old_type} → {new_type}")

            # Title
            old_title = item["data"].get("title", "Not set")
            new_title = updated_data.get("title", "Not set")
            if old_title != new_title:
                logger.info(f"Title: {old_title[:60]}... → {new_title[:60]}...")

            # Date
            if metadata["date"]:
                logger.info(
                    f"Date: {item['data'].get('date', 'Not set')} → {updated_data.get('date', 'Not set')}"
                )

            # Author
            if metadata["author"]:
                old_authors = ", ".join(
                    f"{c.get('firstName', '')} {c.get('lastName', '')}"
                    for c in item["data"].get("creators", [])
                )
                new_authors = ", ".join(
                    f"{c.get('firstName', '')} {c.get('lastName', '')}"
                    for c in updated_data.get("creators", [])
                )
                if old_authors != new_authors:
                    logger.info(f"Author: {old_authors or 'Not set'} → {new_authors}")

            # Website/Blog/Forum
            if metadata["publisher"]:
                # Get old and new titles based on item type
                old_title = item["data"].get("forumTitle") or item["data"].get(
                    "blogTitle", "Not set"
                )
                new_title = updated_data.get("forumTitle") or updated_data.get(
                    "blogTitle", "Not set"
                )
                logger.info(f"Website/Blog/Forum: {old_title} → {new_title}")

            logger.info("----------------")
        else:
            logger.debug(f"✗ Not a Substack or LinkedIn site: {title[:50]}...")
    else:
        logger.warning(f"✓ Already processed: {title[:50]}...")

    if needs_update:
        # Add a tag to indicate processing
        if "tags" not in updated_data:
            updated_data["tags"] = []
        updated_data["tags"].append({"tag": "zotero:processed"})
        logger.debug("✓ Tag added: zotero:processed")

    return updated_data if needs_update else None


def confirm_action(question: str) -> bool:
    """
    Prompt the user for confirmation

    Args:
        question: Question to ask the user

    Returns:
        Boolean indicating user's response
    """
    response = input(question).lower()
    return response in ["y", "yes"]


def analyze_zotero_library(
    config: ZoteroConfig,
    dry_run: bool = False,
    report_file: Optional[str] = None,
    confirm: bool = False,
    exclude_substack: bool = False,
    exclude_linkedin: bool = False,
    force: bool = False,
) -> None:
    """Main function to analyze Zotero library via API"""
    # Create Pyzotero client
    zot = get_zotero_client(config)

    # Get all web items
    logger.debug("Retrieving webpage and blogPost items from Zotero...")
    web_items = []
    updates = []  # New list to collect all updates (not just batch)
    batch_updates = []  # List for batch processing

    # Get items in batches to handle large libraries
    start = 0
    limit = 100

    # First get webpage items
    while True:
        items = zot.items(itemType="webpage", start=start, limit=limit)
        if not items:
            break
        web_items.extend(items)
        start += len(items)
        if len(items) < limit:
            break

    # Reset start for blogPost items
    start = 0

    # Then get blogPost items
    while True:
        items = zot.items(itemType="blogPost", start=start, limit=limit)
        if not items:
            break
        web_items.extend(items)
        start += len(items)
        if len(items) < limit:
            break

    # Then get blogPost items
    while True:
        items = zot.items(itemType="forumPost", start=start, limit=limit)
        if not items:
            break
        web_items.extend(items)
        start += len(items)
        if len(items) < limit:
            break

    # Filter for items with URLs
    web_items = [item for item in web_items if item["data"].get("url")]

    # Initialize counters
    total = len(web_items)
    global stats
    stats.update(
        {
            "urls_cleaned": 0,
            "substackFound": 0,
            "linkedinFound": 0,
            "updated": 0,
            "errors": 0,
        }
    )

    logger.info(f"Found {total} web items to process.")

    # Modify the confirmation message for dry run
    action_msg = "analyze" if dry_run else "process and update"
    if not confirm and not confirm_action(
        f"{action_msg.capitalize()} {total} items? "
        f"{'(Dry run, no changes will be made)' if dry_run else '(This will update your Zotero database directly)'} (y/n): "
    ):
        logger.warning("Operation cancelled by user.")
        return

    # Process items
    for item in web_items:
        updated_data = None
        try:
            updated_data = process_item(
                item,
                exclude_substack=exclude_substack,
                exclude_linkedin=exclude_linkedin,
                force=force,
            )
        except Exception as e:
            logger.error(f"Error processing item {item.get('key')}: {str(e)}")
            stats["errors"] += 1

        if updated_data:
            updates.append(updated_data)  # Keep all updates for report

            # Track URL cleaning separately
            if updated_data.get("url") != item["data"].get("url"):
                stats["urls_cleaned"] += 1

            if not dry_run:
                batch_updates.append(updated_data)
                stats["updated"] += 1

        if not dry_run:
            # Perform batch update every 50 items or at the end
            if len(batch_updates) >= 50 or item == web_items[-1]:
                logger.info(f"\nBatch updating {len(batch_updates)} items...")
                try:
                    logger.info(f"Batch update data: {batch_updates}")
                    zot.update_items(batch_updates)
                    logger.info(f"✓ Successfully updated {len(batch_updates)} items")
                    batch_updates = []
                except Exception as e:
                    logger.error(f"Error during batch update: {str(e)}")
                    stats["errors"] += len(batch_updates)
                    batch_updates = []

        # Update progress with URL cleaning stats
        stats["processed"] += 1
        if stats["processed"] % 5 == 0 or stats["processed"] == total:
            logger.debug(
                f"Processed {stats['processed']}/{total} items. "
                f"Cleaned {stats['urls_cleaned']} URLs. "
                f"Found {stats['substackFound']} Substack posts. "
                f"Found {stats['linkedinFound']} LinkedIn posts. "
                f"Updating {stats['updated']} items."
            )

    # Generate report if there are any updates
    if updates:
        generate_markdown_report(updates, report_file)

    # Update final statistics output
    logger.info("\nAnalysis complete!")
    if dry_run:
        logger.info("DRY RUN - No changes were made to Zotero library")
    logger.info(f"Total items processed: {stats['processed']}")
    logger.info(f"URLs cleaned: {stats['urls_cleaned']}")
    logger.info(f"Substack posts identified: {stats['substackFound']}")
    logger.info(f"LinkedIn posts identified: {stats['linkedinFound']}")
    if not dry_run:
        logger.info(f"Items updated in Zotero: {stats['updated']}")
    logger.info(f"Errors encountered: {stats['errors']}")


def _to_date_string(date_obj) -> str:
    """Convert date object to ISO string or empty string."""
    if date_obj is None or date_obj == "":
        return ""
    if hasattr(date_obj, "isoformat"):
        return date_obj.isoformat()
    return str(date_obj)


def run_yaml_tests(yaml_path: str = "tests/data.yaml"):
    """
    Offline-first Test Mode. Uses local fixtures if they exist.
    Validates the full pipeline: detection → extraction → item preparation
    """
    if not os.path.exists(yaml_path):
        logger.error(f"Error: YAML test data not found at {yaml_path}")
        return

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    cases = data.get("test_cases", {}).get("substack", []) + data.get(
        "test_cases", {}
    ).get("linkedin", [])

    passed = 0
    logger.info(f"--- Running Tests (YAML: {yaml_path}) ---")

    for case in cases:
        url = case["url"]
        expected = case["metadata"]
        fixture_path = case.get("fixture_path")

        html = ""
        # Try loading from local repository first
        if fixture_path and os.path.exists(fixture_path):
            with open(fixture_path, "r", encoding="utf-8") as f:
                html = f.read()
            source = "[LOCAL]"
        else:
            html = download_page(url)
            source = "[LIVE] "

        # Full pipeline: detect site and extract metadata

        is_substack = html and (
            check_if_substack(html, url) or is_substack_note_url(url)
        )
        # Check if this is a LinkedIn URL
        is_linkedin = "linkedin.com" in url.lower()
        extracted = extract_metadata(html, url) if html else {}
        # Create a minimal mock Zotero item for preparation testing
        mock_item = {"data": {"creators": [], "tags": [], "url": url}}

        # Prepare the item update based on detected site
        updated_item = None
        if is_substack and extracted:
            updated_item = prepare_substack_item_update(mock_item, extracted)
        elif is_linkedin and extracted:
            updated_item = prepare_linkedin_item_update(mock_item, extracted)

        # Validation
        author_ok = extracted["author"] == expected["author"]
        title_ok = expected["title"].strip(" .") in extracted["title"]
        expected_date = expected.get("date")
        extracted_date = extracted.get("date", "")
        expected_date_value = _to_date_string(expected_date)
        extracted_date_value = _to_date_string(extracted_date)
        expected_date_only = (
            expected_date_value.split("T")[0].split(" ")[0]
            if expected_date_value
            else ""
        )
        extracted_date_only = (
            extracted_date_value.split("T")[0].split(" ")[0]
            if extracted_date_value
            else ""
        )
        date_ok = (
            True
            if not expected_date_only
            else extracted_date_only == expected_date_only
        )

        # Additional validation for item structure if prepared
        item_type_ok = True
        has_website_type = False
        has_creators = False
        if updated_item:
            item_type_ok = updated_item.get("itemType") == expected.get("type")
            has_website_type = updated_item.get("websiteType") in [
                "Substack Newsletter",
                "LinkedIn",
            ]
            has_creators = (
                len(updated_item.get("creators", [])) > 0
                if extracted["author"]
                else True
            )

        if (
            author_ok
            and title_ok
            and item_type_ok
            and has_website_type
            and has_creators
            and date_ok
        ):
            logger.info(f"✅ {source} {url[:50]}...")
            passed += 1
        else:
            logger.info(f"❌ {source} {url}")
            # Show the JSON-LD type and what Zotero entry type would be created
            if extracted["type"]:
                expected_type = expected.get("type", "N/A")
                actual_type = (
                    updated_item.get("itemType", "N/A") if updated_item else "N/A"
                )
                logger.info(
                    f"    Type Mismatch: Extracted JSON-LD: {extracted['type']} | Expected itemType: {expected_type} | Got itemType: {actual_type}"
                )
            if not author_ok:
                logger.info(
                    f"    Expected Author: {expected['author']} | Got: {extracted['author']}"
                )
            if not title_ok:
                logger.info(
                    f"    Expected Title: {expected['title']} | Got: {extracted['title']}"
                )
            if not date_ok:
                logger.info(
                    f"    Expected Date: {expected_date_only} | Got: {extracted_date_only}"
                )
            if not item_type_ok and updated_item:
                logger.info(
                    f"    Item Type Issue: Expected {expected.get('type', 'N/A')}, got {updated_item.get('itemType', 'Missing')}"
                )
            if not has_website_type and updated_item:
                logger.info(
                    f"    Website Type Issue: {updated_item.get('websiteType', 'Missing')}"
                )
            if not has_creators and extracted["author"] and updated_item:
                logger.info(f"    Authors Issue: {updated_item.get('creators', [])}")

    logger.info(f"\nResult: {passed}/{len(cases)} tests passed.")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze and update Substack posts in Zotero library"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate updates without modifying Zotero library",
    )
    parser.add_argument(
        "--report",
        nargs="?",
        const=None,
        metavar="FILE",
        help="Generate a Markdown report of changes. If FILE is not provided, uses Changes_YYYYMMDD.md",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Run in streaming mode to process updates in real-time",
    )
    parser.add_argument(
        "--test-yaml",
        nargs="?",
        const="tests/data.yaml",
        type=str,
        help="Path to YAML test file to run offline tests (default: tests/data.yaml)",
    )
    parser.add_argument(
        "-e", "--env", type=str, help="Path to custom .env file", default=".env"
    )
    exclude_group = parser.add_mutually_exclusive_group()
    exclude_group.add_argument(
        "--no-substack",
        action="store_true",
        help="Exclude Substack posts from processing",
    )
    exclude_group.add_argument(
        "--no-linkedin",
        action="store_true",
        help="Exclude LinkedIn posts from processing",
    )
    parser.add_argument(
        "-y",
        "--confirm",
        action="store_true",
        help="Auto-confirm prompts for non-interactive use",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging for detailed output",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Process items even if already tagged as zotero:processed",
    )
    return parser.parse_args()


def generate_markdown_report(
    updates: List[Dict], filename: Optional[str] = None
) -> None:
    """
    Generate a Markdown report of updates grouped by blog/update type

    Args:
        updates: List of updated Zotero items
        filename: Optional custom filename for the report
    """
    if not filename:
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"Changes_{date_str}.md"

    # Separate URL cleaning, Substack updates, and LinkedIn updates
    url_updates = []
    substack_updates = defaultdict(list)
    linkedin_updates = []

    for item in updates:
        data = item.get("data", item)  # Handle both raw data and Zotero item format

        # Check if this is a Substack or LinkedIn post
        if data.get("websiteType") == "Substack Newsletter":
            # Get title from either forumTitle or blogTitle
            blog_title = data.get("forumTitle") or data.get("blogTitle", "Unknown Blog")
            substack_updates[blog_title].append(data)
        elif data.get("websiteType") == "LinkedIn":
            linkedin_updates.append(data)
        else:
            url_updates.append(data)

    # Generate markdown content
    md_content = ["# Zotero Updates Report\n"]
    md_content.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Report URL cleaning updates
    if url_updates:
        md_content.append("\n## URL Cleaning Updates")
        for item in sorted(url_updates, key=lambda x: x.get("title", "")):
            md_content.append(f"\n### {item.get('title', 'Untitled')}")
            md_content.append(f"- Original URL: {item.get('original_url', 'No URL')}")
            md_content.append(f"- Cleaned URL: {item.get('url', 'No URL')}")
            md_content.append("")

    # Report Substack updates
    if substack_updates:
        md_content.append("\n## Substack Updates")
        for blog, items in sorted(substack_updates.items()):
            md_content.append(f"\n### {blog}")
            for item in sorted(items, key=lambda x: x.get("title", "")):
                md_content.append(f"\n#### {item.get('title', 'Untitled')}")
                md_content.append(f"- Type: {item.get('itemType', 'N/A')}")
                md_content.append(f"- URL: {item.get('url', 'No URL')}")
                if item.get("date"):
                    md_content.append(f"- Date: {item['date']}")
                if item.get("creators"):
                    authors = ", ".join(
                        f"{c.get('firstName', '')} {c.get('lastName', '')}"
                        for c in item["creators"]
                    )
                    md_content.append(f"- Author(s): {authors}")
                md_content.append("")

    # Report LinkedIn updates
    if linkedin_updates:
        md_content.append("\n## LinkedIn Updates")
        for item in sorted(linkedin_updates, key=lambda x: x.get("title", "")):
            md_content.append(f"\n### {item.get('title', 'Untitled')}")
            md_content.append(f"- Type: {item.get('itemType', 'N/A')}")
            md_content.append(f"- URL: {item.get('url', 'No URL')}")
            if item.get("date"):
                md_content.append(f"- Date: {item['date']}")
            if item.get("creators"):
                authors = ", ".join(
                    f"{c.get('firstName', '')} {c.get('lastName', '')}"
                    for c in item["creators"]
                )
                md_content.append(f"- Author(s): {authors}")
            md_content.append("")

    # Write to file
    Path(filename).write_text("\n".join(md_content))
    logger.info(f"\nReport generated: {filename}")


async def run_streaming_mode(config: ZoteroConfig):
    """Run the script in streaming mode"""
    zot = get_zotero_client(config)
    handler = ZoteroStreamHandler(zot, config.api_key)
    await handler.run()


def load_environment(env_file: str = ".env") -> None:
    """
    Load environment variables from specified .env file

    Args:
        env_file: Path to .env file
    """
    if not os.path.exists(env_file):
        raise FileNotFoundError(f"Environment file not found: {env_file}")

    load_dotenv(env_file)

    # Validate required variables
    if not os.getenv("ZOTERO_API_KEY"):
        raise ValueError("ZOTERO_API_KEY is not set in environment file")
    if not os.getenv("ZOTERO_LIBRARY_ID"):
        raise ValueError("ZOTERO_LIBRARY_ID is not set in environment file")


if __name__ == "__main__":
    try:
        args = parse_args()
        setup_logging(debug=args.debug)
        logger.info("Starting Substack Analyzer...")

        if args.test_yaml:
            run_yaml_tests(args.test_yaml)
        else:
            # Load configuration from environment
            config = ZoteroConfig.from_env(args.env)

            if args.stream:
                logger.info("Running in streaming mode...")
                asyncio.run(run_streaming_mode(config))
            else:
                logger.info("Running in batch mode...")
                if args.confirm:
                    logger.debug("Auto-confirm enabled: prompts will be bypassed.")
                if args.force:
                    logger.warning(
                        "Force processing enabled: all items will be re-processed."
                    )
                analyze_zotero_library(
                    config,
                    dry_run=args.dry_run,
                    report_file=args.report,
                    confirm=args.confirm,
                    exclude_substack=args.no_substack,
                    exclude_linkedin=args.no_linkedin,
                    force=args.force,
                )
    except Exception as e:
        logger.error(f"Error running analysis: {str(e)}")
        exit(1)
