# Zotero Substack Fixer

Zotero (both the Web Scraper and the Apps) currently fail to properly identify Substack Posts hosted outside of a `substack.com` subdomain (i.e. on third-party domain). This script will iterate through Websites and will update their Metadata if they turn out to be Substack posts. It will also at the same go clean up the URL's in your library and remove tracking links.

The script now supports **all types of Substack content**:
- **Regular posts** - Categorized as "Blog Post" items
- **Notes** - Categorized as "Forum Post" items with auto-generated titles from the first ~20 words or first sentence
- **Chats/Comments** - Categorized as "Forum Post" items

## Features

- Identifies Substack posts, notes, and chats hosted on custom domains
- Updates metadata for all Substack content types (dates, authors, etc.)
- Automatically generates titles for notes from content
- Properly categorizes content: posts as "Blog Post", notes/chats as "Forum Post"
- Cleans URLs by removing tracking parameters
- Adds appropriate tags for categorization
- Generates detailed reports of changes
- Supports both personal and group libraries
- Batch processing to handle large libraries efficiently
- Real-time processing via Zotero's Streaming API
- Supports both batch and streaming modes

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

3. Create a `.env` file with your Zotero credentials:

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

## Development

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

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
