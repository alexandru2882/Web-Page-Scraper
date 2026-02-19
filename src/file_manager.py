import os
import re
from urllib.parse import urlparse

WEB_EXTENSIONS = {'.html', '.htm', '.php', '.asp', '.jsp', '.aspx'}

def setup_export_dir(timestamp_str):
    """Creates the timestamped export directory."""
    dir_path = os.path.join("Export", timestamp_str)
    os.makedirs(dir_path, exist_ok=True)
    return dir_path

def generate_safe_filename(url):
    """Generates a filesystem-safe filename from a URL (flat structure)."""
    parsed = urlparse(url)
    # Combine netloc and path
    path = parsed.netloc + parsed.path
    
    # If path ends with /, append index.html ?? Or just let it be.
    # The plan says: "Convert / to _"
    if path.endswith('/'):
        path += "index.html"
    
    safe_name = re.sub(r'[^a-zA-Z0-9.\-_]', '_', path)
    
    # Ensure it's not too long
    if len(safe_name) > 200:
        safe_name = safe_name[-200:]
        
    return safe_name

def get_unique_filename(directory, filename):
    """Handles duplicates by appending a counter."""
    base, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    while os.path.exists(os.path.join(directory, new_filename)):
        new_filename = f"{base}_{counter}{ext}"
        counter += 1
    return new_filename

def match_file_type(url, file_types_config):
    """Checks if the URL matches the requested file types."""
    parsed = urlparse(url)
    path = parsed.path
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    
    if isinstance(file_types_config, str):
        if file_types_config == "all":
            return True
        if file_types_config == "web":
            # Match standard web extensions OR no extension
            if not ext or ext in WEB_EXTENSIONS:
                return True
            return False
            
    # List or comma-string handling (handled in config_loader already to be list or str)
    # If it is a list of specific extensions
    if isinstance(file_types_config, list):
        # clean extensions in config (remove dots usually, but user might say "pdf")
        allowed = [x.lower().lstrip('.') for x in file_types_config]
        current_ext = ext.lstrip('.')
        return current_ext in allowed
        
    return False

def save_content(content, url, export_dir):
    """Saves raw content bytes to the export directory."""
    raw_name = generate_safe_filename(url)
    final_name = get_unique_filename(export_dir, raw_name)
    file_path = os.path.join(export_dir, final_name)
    
    with open(file_path, 'wb') as f:
        f.write(content)
        
    return final_name
