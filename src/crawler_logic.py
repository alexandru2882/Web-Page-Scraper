import cloudscraper
from bs4 import BeautifulSoup
from collections import deque
import time
from .url_utils import normalize_url, is_internal, is_blocked, is_allowed_external, get_root_domain
from .file_manager import match_file_type, save_content, WEB_EXTENSIONS
import os

class CrawlManager:
    def __init__(self, config, export_dir, report_generator=None):
        self.config = config
        self.export_dir = export_dir
        self.report = report_generator
        
        self.start_url = config["start_url"]
        self.root_domain = get_root_domain(self.start_url)
        self.max_depth = config["max_depth"]
        self.blocked_paths = config.get("blocked_paths", [])
        self.allowed_external = config.get("allowed_external_domains", [])
        self.allowed_url_prefixes = config.get("allowed_url_prefixes", [])
        self.file_types = config["file_types"]
        self.run_mode = config["run_mode"]
        
        self.queue = deque([(self.start_url, 0)])
        self.visited = set()
        
        # Use cloudscraper to bypass Cloudflare
        self.session = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'darwin',
                'desktop': True
            }
        )

    def _is_in_scope(self, url):
        """Check if a URL is within the allowed scope.
        
        If allowed_url_prefixes is set, the URL must match at least one prefix.
        Otherwise, fall back to the default internal domain check.
        """
        if self.allowed_url_prefixes:
            return any(url.startswith(prefix) for prefix in self.allowed_url_prefixes)
        # Default: internal domain check
        return is_internal(url, self.root_domain)

    def run(self):
        print(f"Starting crawl at {self.start_url} (Max Depth: {self.max_depth})")
        print(f"Root Domain: {self.root_domain}")
        print(f"Mode: {self.run_mode}")
        if self.allowed_url_prefixes:
            print(f"Scope restricted to URL prefixes:")
            for p in self.allowed_url_prefixes:
                print(f"  - {p}")
        
        while self.queue:
            current_url, depth = self.queue.popleft()
            
            if current_url in self.visited:
                continue
            
            # Guard: Blocked paths
            if is_blocked(current_url, self.blocked_paths):
                continue
            
            # Guard: Must be in scope
            if not self._is_in_scope(current_url):
                continue
                
            self.visited.add(current_url)
            
            try:
                # Fetch
                response = self.session.get(current_url, timeout=15)
                response.raise_for_status()
                content_type = response.headers.get('Content-Type', '').lower()
                
                # Determine type for logging/logic
                is_html = 'text/html' in content_type
                
                # --- PROCESS CONTENT ---
                if self.run_mode.startswith("dry_run"):
                    type_label = "Page" if is_html else "File"
                    if self.report:
                        self.report.log_target(current_url, type_label, depth, "N/A")
                    
                elif self.run_mode == "full_run":
                    # Check if we should save this file
                    if match_file_type(current_url, self.file_types):
                        saved_name = save_content(response.content, current_url, self.export_dir)
                        print(f"[Saved] {saved_name}")
                        
                # --- EXPAND / RECURSE ---
                if is_html and depth < self.max_depth:
                    self._expand(response.text, current_url, depth)
                    
            except Exception as e:
                if self.run_mode == "dry_run_errors" and self.report:
                     self.report.log_target(current_url, f"Error: {str(e)}", depth, "N/A")
                else:
                    print(f"Error processing {current_url}: {e}")

    def _expand(self, html_content, base_url, current_depth):
        soup = BeautifulSoup(html_content, 'html.parser')
        
        for link in soup.find_all('a', href=True):
            raw_url = link['href']
            url = normalize_url(base_url, raw_url)
            
            if not url: 
                continue
            
            # Filter Logic
            # 1. Blocked
            if is_blocked(url, self.blocked_paths):
                continue
            
            # 2. Scope Check — use prefix-based scoping if configured
            if self._is_in_scope(url):
                if url not in self.visited:
                    self.queue.append((url, current_depth + 1))
            elif is_allowed_external(url, self.allowed_external):
                # External Allowed -> Enqueue as terminal (won't pass scope check next pass)
                if url not in self.visited:
                    self.queue.append((url, current_depth + 1))
            # Else: Out of scope -> Ignore
