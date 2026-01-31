#!/usr/bin/env python3
"""
Substack URL Discovery Tool

This tool discovers public Substack posts and notes to use in testing.
It searches both substack.com and subdomain sites for various content types.
It can also extract metadata during discovery to generate test cases with
expected values for validation.

Usage:
    python tools/discover_substack_urls.py [--limit N] [--output FILE] [--with-metadata]
"""

import argparse
import json
import re
import sys
import time
from typing import List, Dict, Set, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Try to import metadata extraction functions if available
try:
    sys.path.insert(0, "./src")
    from main import extract_metadata, get_substack_content_type, check_if_substack
    METADATA_AVAILABLE = True
except ImportError:
    METADATA_AVAILABLE = False
    print("Warning: Metadata extraction not available. Install dependencies or run from repo root.", file=sys.stderr)


class SubstackDiscovery:
    """Discovers Substack URLs for testing"""

    def __init__(self, delay: float = 1.0, extract_metadata: bool = False):
        self.delay = delay
        self.extract_metadata = extract_metadata
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
        self.discovered_urls: Dict[str, List[Dict]] = {
            "posts": [],
            "notes": [],
            "chats": [],
        }

    def fetch_url(self, url: str) -> str:
        """Fetch URL with rate limiting"""
        time.sleep(self.delay)
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching {url}: {e}", file=sys.stderr)
            return ""
    
    def extract_url_metadata(self, url: str, html: str) -> Optional[Dict]:
        """Extract metadata from URL if metadata extraction is enabled"""
        if not self.extract_metadata or not METADATA_AVAILABLE:
            return None
        
        try:
            metadata = extract_metadata(html, url)
            # Check if title has ellipsis
            title = metadata.get("title", "")
            has_ellipsis = title.endswith("...")
            
            return {
                "title": title,
                "author": metadata.get("author", ""),
                "publisher": metadata.get("publisher", ""),
                "has_ellipsis": has_ellipsis,
                "content_type": metadata.get("content_type"),
            }
        except Exception as e:
            print(f"  Warning: Could not extract metadata: {e}", file=sys.stderr)
            return None

    def discover_substack_subdomains(self, limit: int = 5) -> List[str]:
        """
        Discover popular Substack subdomain publications
        
        This searches for well-known Substacks to use as test sources.
        """
        # Some well-known Substack publications
        known_substacks = [
            "astralcodexten.substack.com",
            "platformer.news",
            "stratechery.com",
            "themargins.substack.com",
            "tedgioia.substack.com",
        ]
        
        discovered = []
        
        # Try to find more from Substack's explore page
        try:
            html = self.fetch_url("https://substack.com/browse/top")
            if html:
                soup = BeautifulSoup(html, "html.parser")
                
                # Look for publication links
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    if ".substack.com" in href:
                        parsed = urlparse(href)
                        domain = parsed.netloc
                        if domain and domain not in discovered:
                            discovered.append(domain)
                            if len(discovered) >= limit:
                                break
        except Exception as e:
            print(f"Error discovering substacks: {e}", file=sys.stderr)
        
        # Combine known + discovered
        result = list(set(known_substacks + discovered))[:limit]
        print(f"Found {len(result)} Substack domains to explore")
        return result

    def discover_posts(self, subdomain: str, limit: int = 3) -> List[Dict]:
        """
        Discover regular posts from a Substack subdomain
        
        Looks for URLs matching /p/article-name pattern
        Returns list of dicts with url and optional metadata
        """
        posts = []
        
        # Construct the base URL
        if not subdomain.startswith("http"):
            base_url = f"https://{subdomain}"
        else:
            base_url = subdomain
        
        print(f"Searching for posts on {base_url}")
        
        # Try the archive page
        archive_url = urljoin(base_url, "/archive")
        html = self.fetch_url(archive_url)
        
        if html:
            soup = BeautifulSoup(html, "html.parser")
            
            # Look for post links
            for link in soup.find_all("a", href=True):
                href = link["href"]
                
                # Match /p/ pattern
                if re.search(r"/p/[\w-]+/?$", href):
                    full_url = urljoin(base_url, href)
                    if any(p["url"] == full_url for p in posts):
                        continue
                    
                    # Extract metadata if requested
                    metadata = None
                    if self.extract_metadata:
                        print(f"  Extracting metadata from: {full_url}")
                        post_html = self.fetch_url(full_url)
                        if post_html:
                            metadata = self.extract_url_metadata(full_url, post_html)
                    
                    post_data = {"url": full_url}
                    if metadata:
                        post_data["metadata"] = metadata
                    
                    posts.append(post_data)
                    print(f"  Found post: {full_url}")
                    if len(posts) >= limit:
                            break
        
        return posts

    def discover_notes(self, limit: int = 3, starting_urls: List[str] = None) -> List[str]:
        """
        Discover Substack notes
        
        Looks for URLs matching /@username/note/ or /notes/ patterns
        
        Args:
            limit: Maximum number of notes to discover
            starting_urls: Optional list of known note URLs to start from
        """
        notes = []
        
        # Add any starting URLs first
        if starting_urls:
            for url in starting_urls:
                if url not in notes:
                    notes.append(url)
                    print(f"  Starting with note: {url}")
                    if len(notes) >= limit:
                        return notes
        
        # Try the main Substack notes feed
        print("Searching for notes on substack.com")
        
        # Try various note discovery endpoints
        note_urls = [
            "https://substack.com/notes",
            "https://substack.com/browse/notes",
        ]
        
        for notes_url in note_urls:
            html = self.fetch_url(notes_url)
            
            if html:
                soup = BeautifulSoup(html, "html.parser")
                
                # Look for note links
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    
                    # Match note patterns
                    if re.search(r"/@[\w-]+/note/", href) or re.search(r"/notes/p-", href):
                        full_url = href if href.startswith("http") else f"https://substack.com{href}"
                        if full_url not in notes:
                            notes.append(full_url)
                            print(f"  Found note: {full_url}")
                            if len(notes) >= limit:
                                return notes
        
        return notes

    def discover_chats(self, subdomain: str = None, limit: int = 2, starting_urls: List[str] = None) -> List[str]:
        """
        Discover chat/comment URLs
        
        Looks for comment sections on posts and chat threads
        
        Args:
            subdomain: Optional subdomain to search for post comments
            limit: Maximum number of chat URLs to discover
            starting_urls: Optional list of known chat URLs to start from
        """
        chats = []
        
        # Add any starting URLs first
        if starting_urls:
            for url in starting_urls:
                if url not in chats:
                    chats.append(url)
                    print(f"  Starting with chat: {url}")
                    if len(chats) >= limit:
                        return chats
        
        # Try to find chat threads on substack.com
        print("Searching for chats on substack.com")
        chat_urls = [
            "https://substack.com/chat",
        ]
        
        for chat_url in chat_urls:
            html = self.fetch_url(chat_url)
            
            if html:
                soup = BeautifulSoup(html, "html.parser")
                
                # Look for chat thread links
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    
                    # Match chat patterns
                    if re.search(r"/chat/\d+/post/", href):
                        full_url = href if href.startswith("http") else f"https://substack.com{href}"
                        if full_url not in chats:
                            chats.append(full_url)
                            print(f"  Found chat: {full_url}")
                            if len(chats) >= limit:
                                return chats
        
        # If we still need more and have a subdomain, look for post comments
        if subdomain and len(chats) < limit:
            print(f"Searching for post comments on {subdomain}")
            posts = self.discover_posts(subdomain, limit=3)
            
            for post_url in posts[:limit - len(chats)]:
                # Try the comments section
                comments_url = post_url.rstrip("/") + "/comments"
                
                # Verify it exists
                html = self.fetch_url(comments_url)
                if html and "comment" in html.lower():
                    chats.append(comments_url)
                    print(f"  Found chat: {comments_url}")
                    if len(chats) >= limit:
                        break
        
        return chats

    def run_discovery(
        self, 
        num_domains: int = 3, 
        posts_per_domain: int = 2,
        num_notes: int = 3,
        num_chats: int = 2,
        starting_notes: List[str] = None,
        starting_chats: List[str] = None
    ) -> Dict[str, List[str]]:
        """
        Run full discovery process
        
        Args:
            num_domains: Number of Substack domains to explore
            posts_per_domain: Number of posts to find per domain
            num_notes: Number of notes to find
            num_chats: Number of chat URLs to find
            starting_notes: Optional list of known note URLs to start from
            starting_chats: Optional list of known chat URLs to start from
        """
        print("=" * 80)
        print("Starting Substack URL Discovery")
        print("=" * 80)
        
        # Discover Substack domains
        domains = self.discover_substack_subdomains(num_domains)
        
        # Discover posts from each domain
        for domain in domains:
            posts = self.discover_posts(domain, posts_per_domain)
            self.discovered_urls["posts"].extend(posts)
        
        # Discover notes
        notes = self.discover_notes(num_notes, starting_urls=starting_notes)
        self.discovered_urls["notes"].extend(notes)
        
        # Discover chats
        chats = self.discover_chats(
            subdomain=domains[0] if domains else None, 
            limit=num_chats,
            starting_urls=starting_chats
        )
        self.discovered_urls["chats"].extend(chats)
        
        print("\n" + "=" * 80)
        print("Discovery Complete")
        print("=" * 80)
        print(f"Posts found: {len(self.discovered_urls['posts'])}")
        print(f"Notes found: {len(self.discovered_urls['notes'])}")
        print(f"Chats found: {len(self.discovered_urls['chats'])}")
        
        return self.discovered_urls

    def generate_test_data(self) -> str:
        """Generate Python test data from discovered URLs"""
        lines = [
            "# Auto-discovered Substack URLs for testing",
            "# Generated by tools/discover_substack_urls.py",
            "#",
            "# Import in test_real_urls.py with:",
            "#   from discovered_test_urls import DISCOVERED_TEST_CASES",
            "#",
            "# Each test case can be a tuple (for basic tests) or a dict (with metadata validation):",
            "# Tuple format: (url, expected_type, description)",
            "# Dict format: {",
            "#   'url': 'https://...',",
            "#   'expected_type': 'note'/'chat'/None,",
            "#   'description': '...',",
            "#   'expected_metadata': {  # Optional, for validation",
            "#       'title': 'Expected Title',  # Can include '...' if Substack adds it",
            "#       'author': 'Expected Author',",
            "#       'should_not_add_ellipsis': True,  # Verify we don't add extra ...",
            "#   }",
            "# }",
            "",
            "DISCOVERED_TEST_CASES = [",
        ]
        
        # Generate test cases for posts
        for post in self.discovered_urls.get("posts", []):
            if isinstance(post, dict):
                url = post["url"]
                metadata = post.get("metadata", {})
                if metadata:
                    # Generate dict format with metadata
                    lines.append("    {")
                    lines.append(f'        "url": "{url}",')
                    lines.append('        "expected_type": None,')
                    lines.append('        "description": "Discovered regular post",')
                    lines.append('        "expected_metadata": {')
                    if metadata.get("title"):
                        # Escape quotes in title
                        title = metadata["title"].replace('"', '\\"')
                        lines.append(f'            "title": "{title}",')
                    if metadata.get("author"):
                        author = metadata["author"].replace('"', '\\"')
                        lines.append(f'            "author": "{author}",')
                    # Flag if title already has ellipsis from Substack
                    if metadata.get("has_ellipsis"):
                        lines.append('            "title_has_ellipsis": True,  # From Substack JSON-LD')
                    lines.append('        },')
                    lines.append("    },")
                else:
                    # Generate tuple format
                    lines.append("    (")
                    lines.append(f'        "{url}",')
                    lines.append('        None,')
                    lines.append('        "Discovered regular post",')
                    lines.append("    ),")
            else:
                # Old format - just URL string
                lines.append("    (")
                lines.append(f'        "{post}",')
                lines.append('        None,')
                lines.append('        "Discovered regular post",')
                lines.append("    ),")
        
        # Generate test cases for notes
        for note in self.discovered_urls.get("notes", []):
            if isinstance(note, dict):
                url = note["url"]
                metadata = note.get("metadata", {})
                if metadata:
                    lines.append("    {")
                    lines.append(f'        "url": "{url}",')
                    lines.append('        "expected_type": "note",')
                    lines.append('        "description": "Discovered note",')
                    lines.append('        "expected_metadata": {')
                    if metadata.get("title"):
                        title = metadata["title"].replace('"', '\\"')
                        lines.append(f'            "title": "{title}",')
                        # For notes, we generate titles, so check if we added ellipsis
                        if metadata.get("has_ellipsis"):
                            lines.append('            "should_have_ellipsis": True,  # Content was truncated')
                    lines.append('        },')
                    lines.append("    },")
                else:
                    lines.append("    (")
                    lines.append(f'        "{url}",')
                    lines.append('        "note",')
                    lines.append('        "Discovered note",')
                    lines.append("    ),")
            else:
                lines.append("    (")
                lines.append(f'        "{note}",')
                lines.append('        "note",')
                lines.append('        "Discovered note",')
                lines.append("    ),")
        
        # Generate test cases for chats
        for chat in self.discovered_urls.get("chats", []):
            if isinstance(chat, dict):
                url = chat["url"]
                metadata = chat.get("metadata", {})
                if metadata:
                    lines.append("    {")
                    lines.append(f'        "url": "{url}",')
                    lines.append('        "expected_type": "chat",')
                    lines.append('        "description": "Discovered chat",')
                    lines.append('        "expected_metadata": {')
                    if metadata.get("title"):
                        title = metadata["title"].replace('"', '\\"')
                        lines.append(f'            "title": "{title}",')
                    lines.append('        },')
                    lines.append("    },")
                else:
                    lines.append("    (")
                    lines.append(f'        "{url}",')
                    lines.append('        "chat",')
                    lines.append('        "Discovered chat",')
                    lines.append("    ),")
            else:
                lines.append("    (")
                lines.append(f'        "{chat}",')
                lines.append('        "chat",')
                lines.append('        "Discovered chat",')
                lines.append("    ),")
        
        lines.append("]")
        lines.append("")
        
        # Also generate backward-compatible format
        lines.append("# Raw URLs by type (for compatibility)")
        lines.append("DISCOVERED_TEST_URLS = {")
        
        for content_type, items in self.discovered_urls.items():
            lines.append(f'    "{content_type}": [')
            for item in items:
                url = item["url"] if isinstance(item, dict) else item
                lines.append(f'        "{url}",')
            lines.append("    ],")
        
        lines.append("}")
        lines.append("")
        
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Discover Substack URLs for testing"
    )
    parser.add_argument(
        "--domains",
        type=int,
        default=3,
        help="Number of Substack domains to explore (default: 3)",
    )
    parser.add_argument(
        "--posts",
        type=int,
        default=2,
        help="Number of posts per domain (default: 2)",
    )
    parser.add_argument(
        "--notes",
        type=int,
        default=3,
        help="Number of notes to find (default: 3)",
    )
    parser.add_argument(
        "--chats",
        type=int,
        default=2,
        help="Number of chat URLs to find (default: 2)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for discovered URLs (JSON format)",
    )
    parser.add_argument(
        "--test-output",
        type=str,
        help="Output file for Python test data",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--use-defaults",
        action="store_true",
        help="Use default starting URLs (recommended)",
    )
    parser.add_argument(
        "--with-metadata",
        action="store_true",
        help="Extract metadata from discovered URLs (requires main.py dependencies)",
    )
    
    args = parser.parse_args()
    
    # Default starting URLs (known good examples)
    starting_notes = None
    starting_chats = None
    
    if args.use_defaults:
        starting_notes = [
            "https://substack.com/@contraptions/note/c-191022428",
            "https://substack.com/@uncertaintymindset/note/c-190184676",
        ]
        starting_chats = [
            "https://substack.com/chat/9973/post/64cc3fbb-ef7b-44a8-b8a9-9e336cc7e71b",
            "https://open.substack.com/chat/posts/64cc3fbb-ef7b-44a8-b8a9-9e336cc7e71b",
        ]
    
    # Run discovery
    discovery = SubstackDiscovery(
        delay=args.delay,
        extract_metadata=args.with_metadata
    )
    results = discovery.run_discovery(
        num_domains=args.domains,
        posts_per_domain=args.posts,
        num_notes=args.notes,
        num_chats=args.chats,
        starting_notes=starting_notes,
        starting_chats=starting_chats,
    )
    
    # Output JSON if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nSaved JSON to: {args.output}")
    
    # Output Python test data if requested
    if args.test_output:
        test_data = discovery.generate_test_data()
        with open(args.test_output, "w") as f:
            f.write(test_data)
        print(f"Saved Python test data to: {args.test_output}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("Discovered URLs:")
    print("=" * 80)
    
    for content_type, urls in results.items():
        print(f"\n{content_type.upper()}:")
        for url in urls:
            print(f"  - {url}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
