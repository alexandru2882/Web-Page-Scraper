# Configurable Web Crawler

A Python-based recursive web crawler for downloading pages and files with strict domain scoping.

## Features

-   **Recursion Control**: Crawl up to a specified depth (Max 10).
-   **Smart Scoping**:
    -   **Internal**: Crawls pages sharing the root domain.
    -   **Blocked**: Skips URLs provided in the blocklist.
    -   **External Allowed**: Downloads specific external pages (leaf nodes) but does *not* crawl them further.
-   **File Filtering**:
    -   `"web"`: HTML/PHP/ASP pages.
    -   `"all"`: Everything.
    -   Custom list: e.g., `pdf, docx`.
-   **Modes**:
    -   `dry_run`: Generates a Markdown report of what *would* be saved.
    -   `dry_run_errors`: Same as dry_run, but also logs URLs that failed to download/crawl directly in the tree structure.
    -   `full_run`: Downloads files to a flat, timestamped folder in `Export/`.
-   **CLI Overrides**: Command-line arguments take precedence over `config.json`.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

**1. Using Config File (`config.json`)**
Edit `config.json` and run:
```bash
python main.py
```

**2. Using CLI Arguments (Overrides Config)**

*Dry run analysis:*
```bash
python main.py --start_url "https://example.com" --run_mode "dry_run" --max_depth 2
```

*Download specific files:*
```bash
python main.py --start_url "https://example.com" --file_types "pdf, docx" --run_mode "full_run"
```

*Block specific paths:*
```bash
python main.py --blocked_paths "https://example.com/blog, https://google.com"
```
