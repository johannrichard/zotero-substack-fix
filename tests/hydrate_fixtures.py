#!/usr/bin/env python3
import os
import re
import yaml
import requests
from urllib.parse import urlparse

# Configuration - Relative to the script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
YAML_FILE = os.path.join(SCRIPT_DIR, "data.yaml")
FIXTURE_DIR = os.path.join(SCRIPT_DIR, "fixtures")

def slugify(url: str) -> str:
    """Creates a filesystem-friendly filename from a URL."""
    path = urlparse(url).path
    slug = re.sub(r'[^\w\s-]', '', path).strip().lower()
    slug = re.sub(r'[-\s]+', '_', slug)
    return slug[:100].strip('_')

def download_html(url: str) -> str:
    """Downloads HTML with a browser-like User Agent."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"  ⚠️  Failed to download {url}: {e}")
        return ""

def hydrate():
    """Main process to download and map fixtures."""
    if not os.path.exists(YAML_FILE):
        print(f"❌ Error: {YAML_FILE} not found in {SCRIPT_DIR}.")
        return

    with open(YAML_FILE, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    os.makedirs(FIXTURE_DIR, exist_ok=True)
    print(f"🚀 Hydrating fixtures into: {FIXTURE_DIR}\n")

    categories = data.get("test_cases", {})
    
    for category_name, cases in categories.items():
        print(f"--- {category_name.upper()} ---")
        for case in cases:
            url = case['url']
            
            # Generate filename and path
            name_seed = slugify(url)
            filename = f"{category_name}_{name_seed}.html"
            
            # We store the path relative to the PROJECT ROOT for main.py, 
            # or relative to tests/ for portability. 
            # Let's store it relative to the PROJECT ROOT: "tests/fixtures/..."
            relative_fixture_path = os.path.join("tests", "fixtures", filename)
            absolute_fixture_path = os.path.join(FIXTURE_DIR, filename)

            if os.path.exists(absolute_fixture_path):
                print(f"  ⏭️  Skipping: {filename}")
            else:
                print(f"  📥 Downloading: {url}")
                html = download_html(url)
                if html:
                    with open(absolute_fixture_path, "w", encoding="utf-8") as f:
                        f.write(html)
                    print(f"  ✅ Saved.")
                else:
                    continue

            # Update YAML with the path main.py will use
            case['fixture_path'] = relative_fixture_path

    # Save updated YAML
    with open(YAML_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True)

    print(f"\n✨ Done! Updated {YAML_FILE}")

if __name__ == "__main__":
    hydrate()