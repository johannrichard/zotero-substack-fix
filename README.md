# Zotero Substack Fixer

Zotero (both the Web Scraper and the Apps) currently fail to properly identify Substack Posts hosted outside of a `substack.com` subdomain (i.e. on third-party domain). This script will iterate through Websites and will update their Metadata if they turn out to be Substack posts. It will also at the same go clean up the URL's in your library and remove tracking links.

## Features

- Identifies Substack posts hosted on custom domains
- Updates metadata for Substack posts (dates, authors, etc.)
- Properly distinguishes between item types (forum posts, blog posts, articles)
- Sets correct field types: `forumTitle` for forum posts, `blogTitle` for blog posts
- Cleans URLs by removing tracking parameters
- Adds appropriate tags for categorisation
- Generates detailed reports of changes
- Supports both personal and group libraries
- Batch processing to handle large libraries efficiently
- Real-time processing via Zotero's Streaming API
- Supports both batch and streaming modes
- Validates item fields to prevent invalid Zotero API requests
- **LLM fallback** — when JSON-LD extraction yields no title or author, a headless browser fetches the rendered page and an LLM extracts the missing fields (opt-in, see below)

## Prerequisites

- Python 3.11 or higher
- `pipenv` for dependency management (install with `pip install pipenv` if not already installed)
- A Zotero account with API access
- Your Zotero API key (get it from [Zotero Settings](https://www.zotero.org/settings/keys))

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/johannrichard/zotero-substack-fix.git
   cd zotero-substack-fix
   ```

2. Install dependencies using pipenv:

   ```bash
   make install
   ```

3. Create a `.env` file with your Zotero credentials (copy `.env.example` as a starting point):

   ```bash
   cp .env.example .env
   # then edit .env with your actual values
   ```

   Minimum required values:

   ```bash
   cat > .env << EOF
   ZOTERO_API_KEY=your_api_key_here
   ZOTERO_LIBRARY_ID=your_library_id_here
   ZOTERO_LIBRARY_TYPE=user  # or 'group'
   EOF
   ```

## Usage

The script can be run in two modes: batch processing or streaming. Batch mode is best suited to fix an existing library, whereas streaming mode can be used to keep your library updated, effortlessly. Just keep adding those Substack posts to your Library and they will end up neatly.

### Batch Processing

#### Using Make Commands

- Run with default settings:

  ```bash
  make run
  ```

- Perform a dry run (no changes made):

  ```bash
  make dry-run
  ```

- Run with a custom report file:

  ```bash
  make run ARGS="--report custom_report.md"
  ```

#### Direct Python Execution

- Basic run:

  ```bash
  pipenv run python src/main.py
  ```

- Dry run:

  ```bash
  pipenv run python src/main.py --dry-run
  ```

- Generate report:

  ```bash
  pipenv run python src/main.py --report
  ```

### Streaming Mode

The streaming mode listens to Zotero's WebSocket API for real-time updates and processes new or modified items as they come in.

- Run in streaming mode:

  ```bash
  make stream
  ```

- Direct execution:

  ```bash
  pipenv run python src/main.py --stream
  ```

In streaming mode, the script will:

- Connect to Zotero's WebSocket API
- Listen for library changes in real-time
- Process new or modified items automatically
- Reconnect automatically if the connection drops
- Use exponential backoff for connection retries

### Available Options

- `--dry-run`: Simulate updates without modifying your library
- `--report [FILE]`: Generate a Markdown report of changes (default: `Changes_YYYYMMDD.md`)
- `--stream`: Run in streaming mode to process updates in real-time

## LLM Fallback Mode

When regular JSON-LD metadata extraction yields no title or author for a detected Substack or LinkedIn item, the script can fall back to fetching a fully-rendered copy of the page using a headless Chromium browser (Playwright) and asking an LLM to extract the missing fields.

This is **opt-in** and disabled by default.

### Setup

1. Add the following variables to your `.env` file:

   ```bash
   LLM_ENABLED=true
   LLM_PROVIDER=openai          # openai | anthropic | gemini
   LLM_MODEL=gpt-4o-mini        # model name for your chosen provider
   LLM_API_KEY=sk-...           # your provider API key
   # LLM_MAX_CHARS=12000        # optional: limit page text sent to the LLM
   ```

2. Install the Playwright browser once:

   ```bash
   make setup-playwright
   ```

### How it works

The fallback fires only when all three conditions are true:

1. The item was identified as Substack or LinkedIn.
2. Regular JSON-LD extraction left the title **or** author empty.
3. `LLM_ENABLED=true` is set in your `.env`.

The visible page text (truncated to `LLM_MAX_CHARS` characters, default 12 000) is sent to the LLM with a strict JSON schema prompt. The LLM response is merged back — it fills only the fields that JSON-LD left empty, so existing values are never overwritten.

### Supported providers

| Provider | `LLM_PROVIDER` value | Example model |
|---|---|---|
| OpenAI | `openai` | `gpt-4o-mini` |
| Anthropic | `anthropic` | `claude-3-5-haiku-20241022` |
| Google Gemini | `gemini` | `gemini-2.0-flash` |

> **Note** — `anthropic` requires `pip install anthropic`; `gemini` requires
> `pip install google-generativeai`. The `openai` SDK is installed by default.

- Format code:

  ```bash
  make format
  ```

- Run linting:

  ```bash
  make lint
  ```

- Clean build artifacts:

  ```bash
  make clean
  ```

## Output

The script provides:

- Progress updates during processing
- Summary of changes made
- Optional detailed Markdown report
- Clear error messages if issues occur

### Report Format

The generated report includes:

- URL cleaning updates
- Substack metadata changes
- Items grouped by blog/publisher
- Timestamps and detailed modifications

## Item Type Handling

The script intelligently categorizes content based on JSON-LD metadata:

### Forum Posts

Content types mapped to `forumPost` in Zotero:
- Comments
- Discussion forum postings
- Social media postings (e.g., Substack Notes, LinkedIn posts)

Forum posts use the `forumTitle` field to store the publisher/platform name.

### Blog Posts

Content types mapped to `blogPost` in Zotero:
- Articles
- Blog postings
- News articles
- LinkedIn Articles

Blog posts use the `blogTitle` field to store the blog/publication name.

### Field Validation

The script validates all fields before sending to Zotero's API to ensure:
- `forumPost` items only have `forumTitle` (not `blogTitle`)
- `blogPost` items only have `blogTitle` (not `forumTitle`)
- Invalid field combinations are automatically cleaned up

This prevents API errors and ensures proper metadata organization in your Zotero library.

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
