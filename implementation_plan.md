# Web Crawler Specification

## Goal Description
Create a configurable web crawler in Python that recursively downloads web pages and specific file types (e.g., PDF, DOCX) starting from a given URL. The software must enforce strict domain boundaries (subdomains allowed, external domains blocked), support configurable recursion depth, and allow precise filtering of file types to download. All output must be saved in a **single flat timestamped directory**, allowing for easy bulk access.

## Configuration
The software reads input parameters from a user-defined file named `config.json`. This file acts as the central control for the crawler.

### Configuration Parameters
The following structure outlines all available options.

1.  `start_url` (String): The entry point for the crawler.
2.  `max_depth` (Integer): The maximum recursive depth to traverse. **(Maximum allowed: 10)**.
3.  `file_types` (String or List): Specifies which file extensions to download.
    -   **Built-in Keywords**:
        -   `"all"`: Downloads ALL files found, regardless of extension.
        -   `"web"`: Smart preset that downloads standard web pages only (`.html`, `.htm`, `.php`, `.asp`, `.jsp`, `.aspx`, and URLs with no extension).
    -   **Custom Extensions**: Provide a comma-separated string or list (e.g., `"pdf, docx, png"`).
4.  `blocked_paths` (List of Strings): A list of URL prefixes to strictly exclude.
5.  `allowed_external_domains` (List of Strings): A whitelist of external domains to download (non-recursively).
6.  `run_mode` (String): Execution mode.
    -   `"dry_run"`: Analysis only (no downloads), generates report.
    -   `"full_run"`: Downloads content to disk.

### Sample `config.json`
```json
{
  "start_url": "https://example.com",
  "max_depth": 3,
  "file_types": "web",  // Options: "all", "web", or ["pdf", "docx"]
  "blocked_paths": [
    "https://example.com/blog",
    "https://google.com"
  ],
  "allowed_external_domains": [
    "https://external-partner.com"
  ],
  "run_mode": "full_run" // Options: "dry_run", "full_run"
}
```
*Note: Standard JSON does not support comments (`//`). The actual config file will be pure JSON. The comments above are for documentation.*

#### Command Line Arguments (Priority Override)
The application must accept CLI arguments that correspond to the configuration parameters.
-   **Precedence**: CLI Arguments > `config.json` > Defaults.
-   **Behavior**:
    -   If an argument is provided (e.g., `--start_url`), it **overrides** the value in `config.json`.
    -   If an argument is missing, the value from `config.json` is used.
    -   If all arguments are provided, `config.json` is effectively ignored.
-   **Arguments**:
    -   `--start_url`: Overrides `start_url`.
    -   `--max_depth`: Overrides `max_depth`.
    -   `--file_types`: Overrides `file_types` (accepts comma-separated string).
    -   `--blocked_paths`: Overrides `blocked_paths` (accepts comma-separated string).
    -   `--allowed_external`: Overrides `allowed_external_domains` (accepts comma-separated string).
    -   `--run_mode`: Overrides `run_mode`.

## Core Logic & Rules

### 1. Scope & Filtering
-   **Domain Matching & Scope**:
    1.  **Blocklist Check (Highest Priority)**: If URL matches `blocked_paths`, SKIP immediately.
    2.  **Internal Check**: If URL matches `root_domain` (including subdomains) -> **Allowed & Expandable** (subject to `max_depth`).
    3.  **External Whitelist Check**: If URL matches `allowed_external_domains` -> **Allowed but Terminal** (Download yes, Expand no).
    4.  **Default**: If none of above matches -> **Blocked**.

### 2. Crawl Depth Logic
-   **Depth 0**: The `start_url` page itself.
-   **Depth 1**: All valid links found on the Depth 0 page.
-   **Depth 2**: All valid links found on Depth 1 pages.
-   **Depth N**: Continue until `N == max_depth` **(Limit: 10)**.
-   **Recursion Note**: The crawler must **always** fetch and parse HTML pages to discover new links, even if HTML files are not configured to be saved/downloaded.
-   **Constraint**: Do not expand (crawl for more links) pages found at `depth == max_depth`. Non-web files (like PDF, DOCX) found at any depth are **downloaded but never expanded**.

### 3. Execution Flow
1.  **Startup & Configuration**:
    -   **Load Config**: Read `config.json`.
    -   **Apply Overrides**: Parse CLI arguments; overwrite config values where arguments exist.
    -   **Validate**: Ensure `max_depth <= 10`.
    -   **Setup Output**:
        -   Create `Export/<timestamp>/` directory.
        -   If `run_mode` is "dry_run", initialize the report file.

2.  **Initialization**:
    -   Parse `start_url` to extract the `root_domain`.
    -   Initialize `visited` set to track processed URLs.
    -   Initialize `queue` with tuple: `(start_url, depth=0)`.

3.  **Crawl Loop** (While Queue is not empty):
    -   **Dequeue**: Get `(current_url, current_depth)`.
    -   **Guards**:
        -   If `current_url` in `visited` $\rightarrow$ Skip.
        -   If `current_url` matches `blocked_paths` $\rightarrow$ Skip.
    -   **Mark Visited**: Add `current_url` to `visited`.
    -   **Fetch**: Perform HTTP GET request.
    -   **Process Content**:
        -   Determine if resource is a file (matches `file_types`) or HTML page.
        -   **Mode Check**:
            -   **Dry Run**: Log stats (URL, type), do NOT save file.
            -   **Full Run**:
                -   If matches `file_types`: Generate safe filename $\rightarrow$ Save to `Export/<timestamp>/` flat folder.
    -   **Expand/Recurse**:
        -   **Condition**: Resource is HTML **AND** `current_depth < max_depth`.
        -   **Action**:
            -   Parse HTML for links (`<a href>`).
            -   For each unique link found:
                -   Normalize URL.
                -   **Scope Check**:
                    -   If matches `blocked_paths` $\rightarrow$ Ignore.
                    -   If **Internal** (same root domain) $\rightarrow$ **Enqueue** `(link, current_depth + 1)`.
                    -   If **Allowed External** $\rightarrow$ **Enqueue** `(link, current_depth + 1)` (treated as terminal in next pass).
                    -   Else $\rightarrow$ Ignore.

### 4. Output & Directory Structure

#### Output per Mode
-   **`full_run`**: Follows the **Download Storage** rules below.
-   **`dry_run`**:
    -   Generates a single report file: `Export/dry_run_<timestamp>.md` (or `.html`).
    -   **Content**:
        -   **Statistics**: Total Pages found, Total Files found (by type).
        -   **Tree Structure**: A visual hierarchy of the crawl path (e.g., showing which page linked to which file).
        -   **List of Targets**: A complete list of all URLs that *would* be downloaded in a full run.

#### Download Storage (for `full_run`)
-   **Per-Run Isolation**: For each execution, create a new subfolder inside `Export/` named with the current timestamp (e.g., `Export/2023-10-27_10-30-00/`).
-   **Flat Structure**: Save ALL downloaded files directly into this timestamped folder. **Do not create subdirectories**.
-   **Filename Generation**:
    -   Convert the URL path into a safe filename to avoid collisions and preserve context (e.g., convert `/` to `_`).
    -   Example: `https://site.com/a/b/page.html` -> `site.com_a_b_page.html`.
    -   Handle duplicates: If a filename already exists, append a unique counter (e.g., `name_1.html`).

## Technical Recommendations (for LLM Builder)
-   **Language**: Python.
-   **Libraries**:
    -   `requests`: For HTTP fetching.
    -   `beautifulsoup4`: For HTML parsing and link extraction.
    -   `tldextract`: For robust domain/subdomain matching (e.g., handling `.co.uk` correctly).
    -   `urllib.parse`: For URL joining and parsing.
