#!/usr/bin/env python3
# Copyright (c) 2025 Johann Richard. All rights reserved.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import os
import re
import argparse
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

# Constants
TITLE_FALLBACK_WORD_LIMIT = 20  # APA citation style: first 20 words for posts/comments

# Statistics for reporting
stats = {
    "total": 0,
    "processed": 0,
    "substackFound": 0,
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
        print(f"Warning: Could not clean URL '{url}': {str(e)}")
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
    print(f"Connecting to Zotero API with key: {mask_key(config.api_key)}")
    print(f"Library type: {config.library_type}, Library ID: {config.library_id}")

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
        print(f"Failed to download {url}: {str(e)}")
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
                        and publisher["identifier"].startswith("pub:"),
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

        # Priority Search: 1. Comments, 2. Articles/Posts
        target_item = None
        for item in json_ld:
            if item.get("@type") == "Comment":
                target_item = item
                break

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
                    "headline", target_item.get("name", "")
                )
            else:
                # Fallback for Posts/Comments (APA Style)
                full_text = target_item.get("text", target_item.get("articleBody", ""))
                words = full_text.split()
                metadata["title"] = " ".join(words[:TITLE_FALLBACK_WORD_LIMIT])
                if len(words) > TITLE_FALLBACK_WORD_LIMIT:
                    metadata["title"] += " ..."

            # 3. Date & Publisher
            metadata["date"] = target_item.get("datePublished", "")
            publisher = target_item.get("publisher", {})
            metadata["publisher"] = (
                publisher.get("name", "") if isinstance(publisher, dict) else ""
            )

    except Exception as e:
        print(f"Extraction Error: {e}")

    return metadata


def prepare_item_update(item: Dict, metadata: Dict[str, str]) -> Dict:
    """
    Prepare an updated Zotero item with extracted metadata
    """
    # Create a copy of the item data
    updated_data = dict(item["data"])

    # Update item type
    updated_data["itemType"] = "blogPost"
    updated_data["websiteType"] = "Substack Newsletter"

    # Update blog title
    if metadata["publisher"]:
        updated_data["blogTitle"] = metadata["publisher"]

    # Handle date parsing and updates
    if metadata["date"]:
        try:
            # Parse metadata date
            meta_date = date_parser.parse(metadata["date"])
            meta_date_str = meta_date.strftime("%Y-%m-%d")
            print(f"Parsed metadata date: {metadata['date']} → {meta_date_str}")

            # Parse current date if it exists
            current_date_str = updated_data.get("date", "").strip()
            if current_date_str:
                try:
                    current_date = date_parser.parse(current_date_str)
                    current_date_str = current_date.strftime("%Y-%m-%d")
                    print(
                        f"Parsed current date: {updated_data['date']} → {current_date_str}"
                    )
                except Exception as e:
                    print(
                        f"Warning: Could not parse existing date '{current_date_str}': {str(e)}"
                    )
                    current_date_str = ""

            # Update if no date exists or dates are different
            if not current_date_str or current_date_str != meta_date_str:
                print(
                    f"Date will be updated: {current_date_str or 'Not set'} → {meta_date_str}"
                )
                updated_data["date"] = meta_date_str
            else:
                print(f"Dates match, no update needed: {current_date_str}")

        except Exception as e:
            print(
                f"Warning: Could not parse metadata date '{metadata['date']}': {str(e)}"
            )
            # If parsing fails, use the original date string only if no date exists
            if not updated_data.get("date"):
                updated_data["date"] = metadata["date"]
                print(f"Using original metadata date string: {metadata['date']}")

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

    return updated_data


def process_item(item: Dict) -> Optional[Dict]:
    """
    Process a single Zotero item, cleaning URL and checking for Substack metadata

    Args:
        item: Zotero item to process

    Returns:
        Updated item data if changes needed, None otherwise
    """
    url = item["data"].get("url")
    if not url:
        return None

    title = item["data"].get("title", "")
    print(f"\nProcessing {title[:50]}... ({url})")

    # Create a copy of the item data for potential updates
    updated_data = dict(item["data"])
    needs_update = False

    # Clean URL first

    cleaned_url = clean_url(url)
    if cleaned_url != url:
        updated_data["url"] = cleaned_url
        needs_update = True
        print(f"Cleaned URL: {url} → {cleaned_url}")

    # Download and check for Substack only if we haven't already categorized it
    if not (
        any(tag["tag"] == "zotero:processed" for tag in item["data"].get("tags", []))
    ):

        html = download_page(cleaned_url)
        if html and check_if_substack(html, cleaned_url):
            print(f"✓ Substack detected for: {title[:50]}...")
            global stats
            stats["substackFound"] += 1

            # Extract and update Substack metadata
            metadata = extract_metadata(html, url)
            updated_data = prepare_item_update(item, metadata)

            # Clean URL
            updated_data["url"] = cleaned_url
            needs_update = True

            # Log metadata changes
            print("\nMetadata updates:")
            print("----------------")

            # Add URL changes to logging
            old_url = item["data"].get("url", "")
            new_url = updated_data.get("url", "")
            if old_url != new_url:
                print(f"URL: {old_url} → {new_url}")

            if metadata["date"]:
                print(
                    f"Date: {item['data'].get('date', 'Not set')} → {updated_data.get('date', 'Not set')}"
                )
            if metadata["publisher"]:
                print(
                    f"Website/Blog: {item['data'].get('blogTitle', 'Not set')} → {updated_data.get('blogTitle', 'Not set')}"
                )
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
                    print(f"Authors: {old_authors or 'Not set'} → {new_authors}")
            print("----------------")
        else:
            print(f"✗ Not a Substack site: {title[:50]}...")
    else:
        print(f"✓ Already categorized as Substack: {title[:50]}...")

    if needs_update:
        # Add a tag to indicate processing
        if "tags" not in updated_data:
            updated_data["tags"] = []
        updated_data["tags"].append({"tag": "zotero:processed"})
        print("✓ Tag added: zotero:processed")

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
    config: ZoteroConfig, dry_run: bool = False, report_file: Optional[str] = None
) -> None:
    """Main function to analyze Zotero library via API"""
    # Create Pyzotero client
    zot = get_zotero_client(config)

    # Get all web items
    print("Retrieving webpage and blogPost items from Zotero...")
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

    # Filter for items with URLs
    web_items = [item for item in web_items if item["data"].get("url")]

    # Initialize counters
    global stats
    stats.update({"urls_cleaned": 0, "substackFound": 0, "updated": 0, "errors": 0})

    print(f"Found {len(web_items)} web items to process.")

    # Modify the confirmation message for dry run
    action_msg = "analyze" if dry_run else "process and update"
    if not confirm_action(
        f"{action_msg.capitalize()} {len(web_items)} items? "
        f"{'(Dry run, no changes will be made)' if dry_run else '(This will update your Zotero database directly)'} (y/n): "
    ):
        print("Operation cancelled by user.")
        return

    # Process items
    for item in web_items:
        try:
            if updated_data := process_item(item):
                updates.append(updated_data)  # Keep all updates for report

                # Track URL cleaning separately
                if updated_data.get("url") != item["data"].get("url"):
                    stats["urls_cleaned"] += 1

                if not dry_run:
                    batch_updates.append(updated_data)
                    stats["updated"] += 1

                    # Perform batch update every 50 items or at the end
                    if len(batch_updates) >= 50 or item == web_items[-1]:
                        print(f"\nBatch updating {len(batch_updates)} items...")
                        try:
                            zot.update_items(batch_updates)
                            print(f"✓ Successfully updated {len(batch_updates)} items")
                            batch_updates = []
                        except Exception as e:
                            print(f"Error during batch update: {str(e)}")
                            stats["errors"] += len(batch_updates)
                            batch_updates = []

        except Exception as e:
            print(f"Error processing item {item.get('key')}: {str(e)}")
            stats["errors"] += 1

        # Update progress with URL cleaning stats
        stats["processed"] += 1
        if stats["processed"] % 5 == 0 or stats["processed"] == stats["total"]:
            print(
                f"Processed {stats['processed']}/{stats['total']} items. "
                f"Cleaned {stats['urls_cleaned']} URLs. "
                f"Found {stats['substackFound']} Substack posts. "
                f"Updated {stats['updated']} items."
            )

    # Generate report if there are any updates
    if updates:
        generate_markdown_report(updates, report_file)

    # Update final statistics output
    print("\nAnalysis complete!")
    if dry_run:
        print("DRY RUN - No changes were made to Zotero library")
    print(f"Total items processed: {stats['processed']}")
    print(f"URLs cleaned: {stats['urls_cleaned']}")
    print(f"Substack posts identified: {stats['substackFound']}")
    if not dry_run:
        print(f"Items updated in Zotero: {stats['updated']}")
    print(f"Errors encountered: {stats['errors']}")


def run_yaml_tests(yaml_path: str = "tests/data.yaml"):
    """
    Offline-first Test Mode. Uses local fixtures if they exist.
    """
    if not os.path.exists(yaml_path):
        print(f"Error: YAML test data not found at {yaml_path}")
        return

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    cases = data.get("test_cases", {}).get("substack", []) + data.get(
        "test_cases", {}
    ).get("linkedin", [])

    passed = 0
    print(f"--- Running Tests (YAML: {yaml_path}) ---")

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

        extracted = extract_metadata(html, url)

        # Validation
        author_ok = extracted["author"] == expected["author"]
        title_ok = expected["title"].strip(" .") in extracted["title"]

        if author_ok and title_ok:
            print(f"✅ {source} {url[:50]}...")
            passed += 1
        else:
            print(f"❌ {source} {url}")
            # Show the JSON-LD type and what Zotero entry type would be created
            if extracted["type"]:
                print(f"    Type: {extracted['type']} → Zotero: blogPost")
            if not author_ok:
                print(
                    f"    Expected Author: {expected['author']} | Got: {extracted['author']}"
                )
            if not title_ok:
                print(
                    f"    Expected Title: {expected['title']} | Got: {extracted['title']}"
                )

    print(f"\nResult: {passed}/{len(cases)} tests passed.")


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

    # Separate URL cleaning and Substack updates
    url_updates = []
    substack_updates = defaultdict(list)

    for item in updates:
        data = item.get("data", item)  # Handle both raw data and Zotero item format

        # Check if this is a Substack post
        if data.get("websiteType") == "Substack Newsletter":
            blog_title = data.get("blogTitle", "Unknown Blog")
            substack_updates[blog_title].append(data)
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
    print(f"\nReport generated: {filename}")


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
        print("Starting Substack Analyzer...")
        args = parse_args()

        if args.test_yaml:
            run_yaml_tests(args.test_yaml)
        else:
            # Load configuration from environment
            config = ZoteroConfig.from_env(args.env)

            if args.stream:
                print("Running in streaming mode...")
                asyncio.run(run_streaming_mode(config))
            else:
                print("Running in batch mode...")
                analyze_zotero_library(
                    config, dry_run=args.dry_run, report_file=args.report
                )
    except Exception as e:
        print(f"Error running analysis: {str(e)}")
        exit(1)
