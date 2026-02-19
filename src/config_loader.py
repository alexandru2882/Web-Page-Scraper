import json
import argparse
import os
import sys

def load_config(config_path="config.json"):
    """Loads configuration from a JSON file."""
    if not os.path.exists(config_path):
        print(f"Error: Configuration file '{config_path}' not found.")
        return {} # Should probably raise or exit, but let's handle in merge
    
    with open(config_path, 'r') as f:
        content = f.read()
        
        # Remove C-style comments (/* ... */) and C++-style comments (// ...)
        import re
        # Regex to remove comments: //... or /*...*/
        # It handles cases where // or /* is inside a string
        pattern = r'//.*?$|/\*.*?\*/'
        # Simple regex for config files (assuming no complex urls with // inside strings breaking this simple approach)
        # Better approach for URLs: match strings OR comments, capture strings, ignore comments.
        
        # Robust pattern:
        # Group 1: Strings (double quoted)
        # Group 2: Comment //
        # Group 3: Comment /* */
        pattern = r'("(?:\\.|[^"\\])*")|//.*?$|/\*.*?\*/'
        
        def replace(match):
            if match.group(1):
                return match.group(1) # Keep strings
            return "" # Remove comments
            
        content = re.sub(pattern, replace, content, flags=re.MULTILINE | re.DOTALL)
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Error parsing config.json: {e}")
            sys.exit(1)

def parse_arguments():
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(description="Configurable Web Crawler")
    
    parser.add_argument("--start_url", type=str, help="Starting URL for the crawler")
    parser.add_argument("--max_depth", type=int, help="Maximum recursion depth (Max 10)")
    parser.add_argument("--file_types", type=str, help="Comma-separated list of file extensions or keywords 'all', 'web'")
    parser.add_argument("--blocked_paths", type=str, help="Comma-separated list of blocked URL paths/domains")
    parser.add_argument("--allowed_external", type=str, help="Comma-separated list of allowed external domains")
    parser.add_argument("--run_mode", type=str, choices=["dry_run", "full_run", "dry_run_errors"], help="Execution mode")
    parser.add_argument("--allowed_url_prefixes", type=str, help="Comma-separated list of URL prefixes to restrict crawling scope")
    
    return parser.parse_args()

def merge_config(json_config, args):
    """Merges CLI arguments into JSON config (CLI takes precedence)."""
    config = json_config.copy()
    
    if args.start_url:
        config["start_url"] = args.start_url
    
    if args.max_depth is not None:
        config["max_depth"] = args.max_depth
        
    if args.file_types:
        # Convert comma-separated string to list if it looks like a list, 
        # but 'web' and 'all' are strings.
        # The plan says "String or List".
        # If the user passes "pdf, docx", we make it a list.
        # If "web", keep as string.
        ft = args.file_types.strip()
        if "," in ft:
            config["file_types"] = [x.strip() for x in ft.split(",")]
        else:
            config["file_types"] = ft
            
    if args.blocked_paths:
        config["blocked_paths"] = [x.strip() for x in args.blocked_paths.split(",")]
        
    if args.allowed_external:
        config["allowed_external_domains"] = [x.strip() for x in args.allowed_external.split(",")]

    if args.allowed_url_prefixes:
        config["allowed_url_prefixes"] = [x.strip() for x in args.allowed_url_prefixes.split(",")]
        
    if args.run_mode:
        config["run_mode"] = args.run_mode
        
    # Validate run mode, support partial config match
    # Wait, the choices in parser only enforce CLI args.
    # We should validate final config here or in validate_config.
        
    return config

def validate_config(config):
    """Validates the configuration rules."""
    # Start URL
    if not config.get("start_url"):
        print("Error: start_url is required.")
        sys.exit(1)
        
    # Max Depth
    max_depth = config.get("max_depth", 0)
    if not isinstance(max_depth, int):
        print("Error: max_depth must be an integer.")
        sys.exit(1)
    
    if max_depth > 10:
        print("Warning: max_depth > 10. Clamping to 10 as per specification.")
        config["max_depth"] = 10
        
    return config

def get_final_config():
    args = parse_arguments()
    json_config = load_config()
    merged = merge_config(json_config, args)
    return validate_config(merged)
