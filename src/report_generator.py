import os

class ReportGenerator:
    def __init__(self, export_dir, timestamp):
        self.export_dir = export_dir
        self.timestamp = timestamp
        self.stats = {
            "total_pages": 0,
            "total_files": 0,
            "total_errors": 0,
            "file_types_found": {}
        }
        
        self.report_path = os.path.join(self.export_dir, f"dry_run_{self.timestamp}.md")
        # Open file immediately with line buffering
        self.f = open(self.report_path, "w", encoding="utf-8", buffering=1)
        
        self._write_header()
        
    def _write_header(self):
        self.f.write(f"# Dry Run Report - {self.timestamp}\n\n")
        self.f.write("## Real-time Crawl Log\n")
        self.f.write("```text\n")

    def log_target(self, url, type_label, depth, source_url):
        """Logs a discovered target to file immediately."""
        # Update stats
        if type_label == "Page":
            self.stats["total_pages"] += 1
        elif type_label.startswith("Error:"):
            self.stats["total_errors"] += 1
        else:
            self.stats["total_files"] += 1
            _, ext = os.path.splitext(url)
            if ext:
                ext = ext.lower()
                self.stats["file_types_found"][ext] = self.stats["file_types_found"].get(ext, 0) + 1
        
        # Write to file
        indent = "  " * depth
        self.f.write(f"{indent}- {url} [{type_label}]\n")

    def finalize(self):
        """Writes final stats and closes the file."""
        self.f.write("```\n\n")
        
        self.f.write("## Final Statistics\n")
        self.f.write(f"- Total Pages Found: {self.stats['total_pages']}\n")
        self.f.write(f"- Total Files Found: {self.stats['total_files']}\n")
        self.f.write(f"- Total Errors: {self.stats['total_errors']}\n")
        
        if self.stats["file_types_found"]:
            self.f.write("- File Types:\n")
            for ext, count in self.stats["file_types_found"].items():
                self.f.write(f"  - {ext}: {count}\n")
                
        self.f.close()
        return self.report_path
