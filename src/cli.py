import argparse
import sys
import os
import json
import time
import urllib3
from urllib.parse import urlparse
from art import text2art
from colorama import Fore, Style, init

# Add the src directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from service_detection import ServiceDetection
from utils.logs_handler import create_logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = create_logger(__name__, remote_logging=False)

def validate_url(url):
    """Validate URL format."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def colorize_json(json_obj):
    """Colorize JSON output."""
    json_str = json.dumps(json_obj, indent=4)
    json_str = json_str.replace('"url":', f'{Fore.CYAN}"url":{Style.RESET_ALL}')
    json_str = json_str.replace('"techname":', f'{Fore.GREEN}"techname":{Style.RESET_ALL}')
    json_str = json_str.replace('"path":', f'{Fore.YELLOW}"path":{Style.RESET_ALL}')
    json_str = json_str.replace('"type":', f'{Fore.MAGENTA}"type":{Style.RESET_ALL}')
    return json_str

def save_results_to_file(results, output_file):
    """Save results to a file."""
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=4)
        logger.info(f"Results saved to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save results to file: {e}")

def print_progress(current, total, url):
    """Print progress indicator."""
    percentage = (current / total) * 100
    print(f"\r{Fore.YELLOW}[{current}/{total}] ({percentage:.1f}%) Processing: {url}{Style.RESET_ALL}", end="", flush=True)

def main():
    parser = argparse.ArgumentParser(
        description="Advanced Service Detection Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 src/cli.py --url https://example.com
  python3 src/cli.py --url-list urls.txt
  python3 src/cli.py --url https://example.com --output results.json
  python3 src/cli.py --url https://example.com --threads 5
        """
    )
    
    parser.add_argument("--url", help="Single URL to scan")
    parser.add_argument("--url-list", help="Path to a file containing list of URLs to scan")
    parser.add_argument("--output", "-o", help="Output file to save results (JSON format)")
    parser.add_argument("--threads", "-t", type=int, default=10, help="Number of threads for concurrent processing (default: 10)")
    parser.add_argument("--timeout", type=int, default=15, help="Request timeout in seconds (default: 15)")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    
    args = parser.parse_args()

    # Initialize colorama after parsing arguments
    if args.no_color:
        # Disable colorama
        init(autoreset=False)
        Fore.CYAN = Fore.GREEN = Fore.YELLOW = Fore.MAGENTA = Fore.RED = ""
        Style.RESET_ALL = ""
    else:
        init(autoreset=True)

    ascii_art = text2art("Ashwatthama  v1.1", font='small')
    if args.no_color:
        print(ascii_art)
    else:
        print(Fore.RED + ascii_art + Style.RESET_ALL)

    if not args.url and not args.url_list:
        print(f"{Fore.RED}Error: Please provide either --url or --url-list{Style.RESET_ALL}")
        parser.print_help()
        sys.exit(1)

    # Create ServiceDetection with CLI overrides
    service_detection = ServiceDetection()
    
    # Override timeout if provided via CLI
    if args.timeout:
        service_detection.timeout = args.timeout
        # Update the session timeout as well
        for adapter in service_detection.session.adapters.values():
            if hasattr(adapter, 'config'):
                adapter.config['timeout'] = args.timeout
    
    # Override threading if provided via CLI
    if args.threads:
        # Update the config loader's threading config
        service_detection.config_loader.config['threading']['max_workers'] = args.threads
        logger.info(f"CLI override: Using {args.threads} threads")
    
    if args.timeout:
        logger.info(f"CLI override: Using {args.timeout}s timeout")

    logger.info(f"[*] Scan started to detect version and technology")

    start_time = time.time()
    
    try:
        if args.url:
            if not validate_url(args.url):
                print(f"{Fore.RED}Error: Invalid URL format: {args.url}{Style.RESET_ALL}")
                sys.exit(1)
                
            print(f"{Fore.CYAN}[*] Scanning: {args.url}{Style.RESET_ALL}")
            results = service_detection.processResult(args.url)
            
            if results:
                colored_results = colorize_json(results)
                print(f"\n{colored_results}")
            else:
                print(f"{Fore.YELLOW}No technologies detected{Style.RESET_ALL}")
                
            if args.output:
                save_results_to_file(results, args.output)

        elif args.url_list:
            if not os.path.exists(args.url_list):
                print(f"{Fore.RED}Error: File not found: {args.url_list}{Style.RESET_ALL}")
                sys.exit(1)
                
            with open(args.url_list, 'r') as file:
                urls = [line.strip() for line in file if line.strip() and validate_url(line.strip())]
            
            if not urls:
                print(f"{Fore.RED}Error: No valid URLs found in {args.url_list}{Style.RESET_ALL}")
                sys.exit(1)
            
            print(f"{Fore.CYAN}[*] Found {len(urls)} valid URLs to scan{Style.RESET_ALL}")
            
            all_results = []
            for i, url in enumerate(urls, 1):
                if not args.no_color:
                    print_progress(i, len(urls), url)
                else:
                    print(f"[{i}/{len(urls)}] Processing: {url}")
                
                results = service_detection.processResult(url)
                if results:
                    all_results.append(results)
            
            print(f"\n{Fore.GREEN}[*] Scan completed{Style.RESET_ALL}")
            
            if all_results:
                colored_results = colorize_json(all_results)
                print(f"\n{colored_results}")
            else:
                print(f"{Fore.YELLOW}No technologies detected across all URLs{Style.RESET_ALL}")
                
            if args.output:
                save_results_to_file(all_results, args.output)

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[*] Scan interrupted by user{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        sys.exit(1)
    finally:
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"[*] Total time consumed: {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    main()
