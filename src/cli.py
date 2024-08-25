import argparse
from service_detection import ServiceDetection
import json
import time
from art import text2art
from colorama import Fore, Style, init
from utils.logs_handler import create_logger
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = create_logger(__name__, remote_logging=False)

def colorize_json(json_obj):
    """Colorize JSON output."""
    json_str = json.dumps(json_obj, indent=4)
    json_str = json_str.replace('"url":', f'{Fore.CYAN}"url":{Style.RESET_ALL}')
    json_str = json_str.replace('"techname":', f'{Fore.GREEN}"techname":{Style.RESET_ALL}')
    json_str = json_str.replace('"path":', f'{Fore.YELLOW}"path":{Style.RESET_ALL}')
    json_str = json_str.replace('"source":', f'{Fore.MAGENTA}"source":{Style.RESET_ALL}')
    return json_str

def main():
    init(autoreset=True)

    ascii_art = text2art("Ashwatthama  v1.0", font='small')
    print(Fore.RED + ascii_art + Style.RESET_ALL)

    parser = argparse.ArgumentParser(description="Service Detection Tool")
    parser.add_argument("--url", help="URL to scan")
    parser.add_argument("--url-list", help="Path to a file containing list of URLs to scan")
    args = parser.parse_args()

    service_detection = ServiceDetection()

    logger.info(f"[*] Scan started to detect version and technology")

    start_time = time.time()
    if args.url:
        results = service_detection.processResult(args.url)
        colored_results = colorize_json(results)
        print(colored_results)

    elif args.url_list:
        with open(args.url_list, 'r') as file:
            urls = [line.strip() for line in file if line.strip()]
        
        all_results = []
        for url in urls:
            results = service_detection.processResult(url)
            all_results.append(results)

        colored_results = colorize_json(all_results)
        print(colored_results)

    else:
        print("Please provide a URL with --url or a file containing URLs with --url-list")
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.info(f"[*] Total time consumed to detect version and technology: {elapsed_time}")

if __name__ == "__main__":
    main()
