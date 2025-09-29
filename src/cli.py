import argparse
import sys
import os
import json
import time
import urllib3
from urllib.parse import urlparse
from art import text2art
from colorama import Fore, Style, init

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from service_detection import ServiceDetection
from utils.logs_handler import createLogger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = createLogger(__name__, remoteLogging=False)

def validateUrl(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def colorizeJson(jsonObj):
    jsonStr = json.dumps(jsonObj, indent=4)
    jsonStr = jsonStr.replace('"url":', f'{Fore.CYAN}"url":{Style.RESET_ALL}')
    jsonStr = jsonStr.replace('"techname":', f'{Fore.GREEN}"techname":{Style.RESET_ALL}')
    jsonStr = jsonStr.replace('"path":', f'{Fore.YELLOW}"path":{Style.RESET_ALL}')
    jsonStr = jsonStr.replace('"type":', f'{Fore.MAGENTA}"type":{Style.RESET_ALL}')
    return jsonStr

def saveResultsToFile(results, outputFile):
    try:
        with open(outputFile, 'w') as f:
            json.dump(results, f, indent=4)
        logger.info(f"Results saved to {outputFile}")
    except Exception as e:
        logger.error(f"Failed to save results to file: {e}")

def printProgress(current, total, url):
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

    if args.no_color:
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

    serviceDetection = ServiceDetection()
    
    if args.timeout:
        serviceDetection.timeout = args.timeout
        for adapter in serviceDetection.session.adapters.values():
            if hasattr(adapter, 'config'):
                adapter.config['timeout'] = args.timeout
    
    if args.threads:
        serviceDetection.configLoader.config['threading']['max_workers'] = args.threads
        logger.info(f"CLI override: Using {args.threads} threads")
    
    if args.timeout:
        logger.info(f"CLI override: Using {args.timeout}s timeout")

    logger.info(f"[*] Scan started to detect version and technology")

    start_time = time.time()
    
    try:
        if args.url:
            if not validateUrl(args.url):
                print(f"{Fore.RED}Error: Invalid URL format: {args.url}{Style.RESET_ALL}")
                sys.exit(1)
                
            print(f"{Fore.CYAN}[*] Scanning: {args.url}{Style.RESET_ALL}")
            results = serviceDetection.processResult(args.url)
            
            if results:
                coloredResults = colorizeJson(results)
                print(f"\n{coloredResults}")
            else:
                print(f"{Fore.YELLOW}No technologies detected{Style.RESET_ALL}")
                
            if args.output:
                saveResultsToFile(results, args.output)

        elif args.url_list:
            if not os.path.exists(args.url_list):
                print(f"{Fore.RED}Error: File not found: {args.url_list}{Style.RESET_ALL}")
                sys.exit(1)
                
            with open(args.url_list, 'r') as file:
                urls = [line.strip() for line in file if line.strip() and validateUrl(line.strip())]
            
            if not urls:
                print(f"{Fore.RED}Error: No valid URLs found in {args.url_list}{Style.RESET_ALL}")
                sys.exit(1)
            
            print(f"{Fore.CYAN}[*] Found {len(urls)} valid URLs to scan{Style.RESET_ALL}")
            
            allResults = []
            for i, url in enumerate(urls, 1):
                if not args.no_color:
                    printProgress(i, len(urls), url)
                else:
                    print(f"[{i}/{len(urls)}] Processing: {url}")
                
                results = serviceDetection.processResult(url)
                if results:
                    allResults.append(results)
            
            print(f"\n{Fore.GREEN}[*] Scan completed{Style.RESET_ALL}")
            
            if allResults:
                coloredResults = colorizeJson(allResults)
                print(f"\n{coloredResults}")
            else:
                print(f"{Fore.YELLOW}No technologies detected across all URLs{Style.RESET_ALL}")
                
            if args.output:
                saveResultsToFile(allResults, args.output)

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
