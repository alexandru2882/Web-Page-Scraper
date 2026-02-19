import datetime
from src.config_loader import get_final_config
from src.crawler_logic import CrawlManager
from src.file_manager import setup_export_dir
from src.report_generator import ReportGenerator

def main():
    # 1. Configuration
    config = get_final_config()
    
    # 2. Setup Output
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    export_dir = setup_export_dir(timestamp)
    print(f"Output Directory: {export_dir}")
    
    # 3. Report Init (if dry run)
    report_gen = None
    if config["run_mode"].startswith("dry_run"):
        report_gen = ReportGenerator(export_dir, timestamp)
        
    # 4. Initialize Crawler
    crawler = CrawlManager(config, export_dir, report_generator=report_gen)
    
    # 5. Run
    try:
        crawler.run()
    except KeyboardInterrupt:
        print("\nCrawl interrupted by user.")
    finally:
        # 6. Finalize Report
        if config["run_mode"].startswith("dry_run") and report_gen:
            path = report_gen.finalize()
            print(f"Dry Run Report saved to: {path}")

if __name__ == "__main__":
    main()
