import os
import shutil
import re
from pathlib import Path
from bs4 import BeautifulSoup, Comment
from markdownify import markdownify as md


import datetime
import difflib

from collections import defaultdict

# Configuration
DEFAULT_SOURCE_DIR = Path("source")
EXPORT_DIR = Path("Eport")
SOURCE_PATH_FILE = DEFAULT_SOURCE_DIR / "source_path.txt"

# Tags to ALWAYS remove (Technical noise, scripts, etc.)
TAGS_ALWAYS_REMOVE = [
    # Scripts and styles
    "script", "style", "noscript",
    # Metadata
    "meta", "link", 
    # Media (non-text content)
    "img", "picture", "video", "audio", "source", "track",
    "canvas", "iframe", "embed", "object", "param",
    # SVG/Graphics
    "svg", "path", "circle", "rect", "line", "polygon", "polyline", "ellipse", "g", "defs", "use", "symbol", "clipPath", "mask",
    # Interactive elements (forms handled separately as boilerplate)
    "button", "input", "select", "textarea", "option", "optgroup", "datalist", "output",
    # Misc non-content
    "template", "slot", "portal",
]

# Boilerplate tags (Navigation, Menus, Footers, Forms)
# These are kept for the FIRST file in a directory, but removed for the rest.
TAGS_BOILERPLATE = [
    "header", "footer", "nav", "form", "aside", "menu", "menuitem"
]

# Classes/IDs that indicate boilerplate elements (partial matching)
BOILERPLATE_PATTERNS = [
    # Navigation
    "nav", "menu", "navigation", "navbar", "topbar", "sidebar", "breadcrumb",
    # Headers/Footers
    "header", "footer", "foot", "masthead",
    # Popups/Modals
    "modal", "popup", "poptin", "overlay", "lightbox", "dialog",
    # Cookie/Consent
    "cookie", "consent", "gdpr", "privacy-banner", "cookiebot",
    # Chat widgets
    "chat", "chatbot", "messenger", "intercom", "drift", "crisp", "zendesk", "hubspot",
    "magicform", "widget",  # From the example page
    # Ads/Tracking
    "ad-", "ads-", "advertisement", "banner", "promo", "sponsor",
    "tracking", "analytics", "gtm", "google-tag",
    # Social
    "social", "share", "follow-us",
    # Language selectors
    "lang-", "language", "locale", "wpml", "dropdown",
    # Forms/CTAs that are not main content
    "newsletter", "subscribe", "signup", "login", "signin",
    # Misc boilerplate
    "skip-link", "sr-only", "visually-hidden", "hidden",
    "back-to-top", "scroll-top",
]

# Attributes to keep (everything else is stripped to reduce noise)
ATTRIBUTES_TO_KEEP = ["href", "alt", "title"]

def remove_empty_tags(soup):
    """
    Recursively removes tags that have no content (no text, no children)
    or contain only whitespace.
    """
    # List of tags that are "void" and should not be removed even if empty
    VOID_TAGS = ['img', 'br', 'hr', 'input', 'meta', 'link']
    
    # We iterate in reverse to handle nested empty tags correctly
    for tag in reversed(list(soup.find_all(True))):
        if tag.name in VOID_TAGS:
            continue
            
        # If tag has no text (or only whitespace) and no children, remove it
        if not tag.get_text(strip=True) and not tag.contents:
             tag.decompose()
        # Also remove if it has children but they are all empty strings/whitespace
        # (BeautifulSoup sometimes leaves empty NavigableStrings)
        elif all(isinstance(c, str) and not c.strip() for c in tag.contents):
            tag.decompose()

def unwrap_useless_divs(soup):
    """
    Unwraps div and span tags that have no attributes.
    Replaces <div>...</div> with ...
    Note: We already strip attributes before this step, so most divs 
    will be attribute-less unless they kept one of the ATTRIBUTES_TO_KEEP (unlikely for divs).
    """
    # Find all divs and spans
    for tag in soup.find_all(["div", "span"]):
        # We only keep attributes in ATTRIBUTES_TO_KEEP. 
        # If a tag has attributes left (like 'title'), we might want to keep it.
        # But our current config only keeps href/alt/title. Divs/spans usually don't have these.
        # So check if attrs is empty.
        if not tag.attrs:
            tag.unwrap()


def remove_comments(soup):
    """
    Removes all HTML comments from the soup.
    """
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()


def is_boilerplate_element(tag):
    """
    Checks if a tag is a boilerplate element based on class/ID patterns.
    """
    if not tag.attrs:
        return False
    
    # Get class list and id
    classes = tag.get("class", [])
    if isinstance(classes, str):
        classes = [classes]
    tag_id = tag.get("id", "")
    
    # Combine into searchable string
    attr_string = " ".join(classes).lower() + " " + tag_id.lower()
    
    for pattern in BOILERPLATE_PATTERNS:
        if pattern in attr_string:
            return True
    
    return False


def remove_boilerplate_by_patterns(soup):
    """
    Removes elements that match boilerplate class/ID patterns.
    """
    # Find all elements and check if they're boilerplate
    # Process in reverse to handle nested elements
    for tag in reversed(list(soup.find_all(True))):
        if is_boilerplate_element(tag):
            tag.decompose()


def clean_html_structure(html_content, remove_boilerplate=False):
    """
    Performs the structural cleaning: removing unwanted tags, 
    unwrapping divs, removing empty tags/attributes.
    Returns the BeautifulSoup object for further processing.
    
    Args:
        html_content: Raw HTML string
        remove_boilerplate: If True, also removes boilerplate elements (header, footer, nav, etc.)
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # 0. Remove HTML comments first
    remove_comments(soup)

    # 1. Remove ALWAYS tags
    for tag in TAGS_ALWAYS_REMOVE:
        for element in soup.find_all(tag):
            element.decompose()

    # 2. Remove boilerplate by tag name if requested
    if remove_boilerplate:
        for tag_name in TAGS_BOILERPLATE:
            for element in soup.find_all(tag_name):
                element.decompose()
        
        # Also remove by class/ID patterns
        remove_boilerplate_by_patterns(soup)

    # 3. Clean Attributes (do this BEFORE checking for empty divs)
    for tag in soup.find_all(True):
        new_attrs = {k: v for k, v in tag.attrs.items() if k in ATTRIBUTES_TO_KEEP}
        tag.attrs = new_attrs

    # 4. Recursive Cleaning
    remove_empty_tags(soup)
    unwrap_useless_divs(soup)
    remove_empty_tags(soup) # Second pass

    return soup

def finalize_html(soup, compact=True):
    """
    Converts soup to string and normalizes whitespace.
    
    Args:
        soup: BeautifulSoup object or Tag
        compact: If True, compress to fewer lines (better for AI ingestion)
                If False, keep more structure for readability
    """
    # Get clean HTML
    cleaned_html = str(soup)
    
    if compact:
        # Normalize whitespace within the HTML
        # Replace multiple whitespace with single space
        cleaned_html = re.sub(r'\s+', ' ', cleaned_html)
        
        # Add line breaks after major block elements for some readability
        block_elements = ['</section>', '</article>', '</main>', '</body>', '</html>', 
                          '</h1>', '</h2>', '</h3>', '</h4>', '</h5>', '</h6>',
                          '</p>', '</div>', '</li>', '</tr>']
        for elem in block_elements:
            cleaned_html = cleaned_html.replace(elem, elem + '\n')
        
        # Clean up any resulting double newlines
        cleaned_html = re.sub(r'\n\s*\n', '\n', cleaned_html)
        
        # Final strip of each line
        lines = [line.strip() for line in cleaned_html.splitlines() if line.strip()]
        return '\n'.join(lines)
    else:
        # Just remove empty lines
        lines = [line.rstrip() for line in cleaned_html.splitlines() if line.strip()]
        return '\n'.join(lines)

def get_source_directory():
    """
    Determines the source directory to read files from.
    Checks source/source_path.txt for a valid path.
    Returns a tuple: (Path object, is_external_source_boolean)
    """
    if SOURCE_PATH_FILE.exists():
        try:
            with open(SOURCE_PATH_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    content = content.strip('"\'')
                    path = Path(content)
                    if path.exists():
                        print(f"Using source path from file: {path}")
                        return path, True
                    else:
                        print(f"Warning: Path in {SOURCE_PATH_FILE.name} does not exist: {path}")
        except Exception as e:
            print(f"Error reading {SOURCE_PATH_FILE.name}: {e}")
    
    print(f"Using default source directory: {DEFAULT_SOURCE_DIR}")
    return DEFAULT_SOURCE_DIR, False

def process_files():
    """
    Iterates through source directory and cleans files.
    Groups files by directory to handle boilerplate retention logic.
    
    LOGIC:
    - First file in each directory: Keep full cleaned structure (header, footer, nav, menus)
    - Subsequent files: Extract ONLY <main> content (or body minus boilerplate if no <main>)
    """
    source_dir, is_external = get_source_directory()

    if not source_dir.exists():
        print(f"Error: Source directory '{source_dir}' does not exist.")
        return

    # Determine export subdirectory name
    if is_external:
        export_subdir_name = source_dir.name
    else:
        export_subdir_name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    current_export_dir = EXPORT_DIR / export_subdir_name
    
    # Handle directory collision (increment name if exists)
    if current_export_dir.exists():
        counter = 2
        while True:
            new_dir = EXPORT_DIR / f"{export_subdir_name}_{counter}"
            if not new_dir.exists():
                current_export_dir = new_dir
                break
            counter += 1
            
    current_export_dir.mkdir(parents=True)
    print(f"Created export directory '{current_export_dir}'.")

    # Recursive search for .html files
    # Sort them to ensure deterministic processing order
    files = sorted(list(source_dir.rglob("*.html")))
    if not files:
        print(f"No .html files found in '{source_dir}' (recursively).")
        return

    print(f"Found {len(files)} files to process...")

    # Group files by their parent directory
    files_by_dir = defaultdict(list)
    for f in files:
        files_by_dir[f.parent].append(f)

    processed_count = 0
    
    # Process each directory group
    for directory, dir_files in files_by_dir.items():
        # dir_files is already sorted because 'files' was sorted
        
        for i, file_path in enumerate(dir_files):
            is_first_file = (i == 0)
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Step 1: Base Cleaning with boilerplate removal
                # For first file: keep structure but remove class-based boilerplate (popups, chat, etc.)
                # For subsequent files: remove ALL boilerplate
                soup = clean_html_structure(content, remove_boilerplate=(not is_first_file))
                
                # Step 2: Additional boilerplate handling for subsequent files
                if is_first_file:
                    # FIRST FILE: Keep structure, but still remove class-based boilerplate
                    print(f"[{file_path.name}] First file - keeping structure, removing widgets/popups")
                    
                    # Still remove boilerplate by class/ID patterns (popups, chat widgets, etc.)
                    remove_boilerplate_by_patterns(soup)
                    remove_empty_tags(soup)  # Clean up after removal
                    
                    final_content = finalize_html(soup)
                else:
                    # SUBSEQUENT FILES: Extract ONLY main content
                    print(f"[{file_path.name}] Subsequent file - extracting main content only")
                    
                    # Strategy 1: Try to find <main> tag
                    main_tag = soup.find("main")
                    
                    if main_tag:
                        # Found <main> - it's already clean from boilerplate
                        final_content = finalize_html(main_tag)
                    else:
                        # Strategy 2: No <main> tag - use body
                        root = soup.body if soup.body else soup
                        
                        # Remove top-level <ul> elements (likely navigation menus)
                        # Only remove if they are direct children of body
                        for ul in list(root.find_all("ul", recursive=False)):
                            # Check if this looks like a menu (has links)
                            links = ul.find_all("a")
                            if len(links) > 3:  # Likely a navigation menu
                                ul.decompose()
                        
                        # Clean up after additional removal
                        remove_empty_tags(root)
                        final_content = finalize_html(root)

                # Output
                output_filename = file_path.name 
                output_path = current_export_dir / output_filename
                
                counter = 1
                while output_path.exists():
                    output_path = current_export_dir / f"{file_path.stem}_{counter}{file_path.suffix}"
                    counter += 1

                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(final_content)
                
                processed_count += 1
                
            except Exception as e:
                print(f"Failed to process {file_path.name}: {e}")

    print(f"Processing complete. {processed_count} files saved to: {current_export_dir}")

if __name__ == "__main__":
    process_files()
