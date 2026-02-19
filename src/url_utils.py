import tldextract
from urllib.parse import urlparse, urljoin, urldefrag

def get_root_domain(url):
    """Extracts the root domain (eTLD+1) from a URL."""
    extracted = tldextract.extract(url)
    return f"{extracted.domain}.{extracted.suffix}"

def normalize_url(base_url, link):
    """Joins relative links and removes fragments."""
    joined = urljoin(base_url, link)
    defragged, _ = urldefrag(joined)
    return defragged

def is_blocked(url, blocked_paths):
    """Checks if the URL starts with any of the blocked paths."""
    if not blocked_paths:
        return False
    for path in blocked_paths:
        if url.startswith(path):
            return True
    return False

def is_internal(url, root_domain):
    """Checks if the URL shares the same root domain."""
    url_domain = get_root_domain(url)
    return url_domain == root_domain

def is_allowed_external(url, allowed_domains):
    """Checks if the URL matches any of the allowed external domains."""
    if not allowed_domains:
        return False
    # Check if the URL starts with any of the allowed domains
    # Or strict domain matching? Plan said "matches allowed_external_domains".
    # Assuming the config provides full domains or prefixes logic similar to blocked.
    # But usually external whitelist is domain based.
    # Let's check if the root domain of the URL is in the allowed list
    # OR if the user provided specific URLs (prefixes).
    # The plan says "Whitelisted external domains/subdomains".
    # Let's assume prefix matching for flexibility, consistent with blocked_paths logic.
    for allowed in allowed_domains:
         if url.startswith(allowed):
             return True
    return False
