import time
import requests
import tempfile
import subprocess
import concurrent.futures
import os
import re
import shutil
from fake_useragent import UserAgent
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils.logs_handler import create_logger
from utils.signature_loader import load_signatures_from_directory
from utils.config_loader import ConfigLoader

logger = create_logger(__name__, remote_logging=False, log_level="INFO")

class ServiceDetection:
    def __init__(self, config_path="config.yaml"):
        # Load configuration
        self.config_loader = ConfigLoader(config_path)
        request_config = self.config_loader.get_request_config()
        
        self.user_agent = UserAgent()
        self.crawled_data_cache = {}
        self.custom_signatures = load_signatures_from_directory(os.path.join(os.path.dirname(__file__), '..', 'signatures'))
        
        # Check if ripgrep is available
        self.ripgrep_available = self._check_ripgrep_availability()
        
        # Get configuration values
        self.timeout = request_config.get('timeout', 15)
        self.max_retries = request_config.get('max_retries', 3)
        self.follow_redirects = request_config.get('follow_redirects', True)
        self.verify_ssl = request_config.get('verify_ssl', False)
        
        # Configure session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        logger.info(f"ServiceDetection initialized with timeout={self.timeout}s, max_retries={self.max_retries}")
        if self.ripgrep_available:
            logger.info("Ripgrep detected and will be used for pattern matching")
        else:
            logger.warning("Ripgrep not found, using fallback regex matcher")

    def _check_ripgrep_availability(self):
        """Check if ripgrep is available on the system."""
        try:
            result = subprocess.run(['rg', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logger.info(f"Ripgrep detected: {result.stdout.strip()}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return False

    def _read_file_content(self, file_path):
        """Read content from a file path, handling both file paths and direct content."""
        if os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                return ""
        return file_path  # If it's not a file path, return as-is

    def _cleanup_temp_files(self, source_content):
        """Clean up temporary files created during crawling."""
        if isinstance(source_content, dict):
            for key, file_path in source_content.items():
                if isinstance(file_path, str) and os.path.isfile(file_path):
                    try:
                        os.unlink(file_path)
                        logger.debug(f"Cleaned up temp file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up temp file {file_path}: {e}")

    def crawlUrl(self, baseUrl, rule):
        url = f"{baseUrl.rstrip('/')}{rule.get('path')}"
        
        try:
            headers = {
                'User-Agent': self.user_agent.random  
            }

            # Check if the crawled data for this URL is already in the cache
            if url in self.crawled_data_cache:
                rule["sourceContent"] = self.crawled_data_cache[url]
                return rule
                        
            # Use session with retry strategy and configurable timeout
            response = self.session.get(
                url, 
                headers=headers, 
                timeout=self.timeout, 
                verify=self.verify_ssl,
                allow_redirects=self.follow_redirects
            )
            
            # Check if response is successful
            response.raise_for_status()
            
            content = response.text
            cookies = response.cookies
            header = response.headers

            # Store content directly instead of in temp files for better performance
            rule["sourceContent"] = {
                "content": content,
                "cookies": str(cookies),
                "header": str(header)
            }
            
            self.crawled_data_cache[url] = rule["sourceContent"]  # Store the crawled data in the cache
            logger.debug(f"Successfully crawled URL: {url}")
            
        except requests.exceptions.Timeout as err:
            logger.warning(f"Timeout crawling URL '{url}' after {self.timeout}s: {str(err)}")
            rule["sourceContent"] = {
                "content": "",
                "cookies": "",
                "header": ""
            }
        except requests.exceptions.ConnectionError as err:
            logger.warning(f"Connection error crawling URL '{url}': {str(err)}")
            rule["sourceContent"] = {
                "content": "",
                "cookies": "",
                "header": ""
            }
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 404:
                logger.debug(f"404 Not Found for URL '{url}' - this is expected for some paths")
            else:
                logger.warning(f"HTTP error crawling URL '{url}': {err.response.status_code} {str(err)}")
            rule["sourceContent"] = {
                "content": "",
                "cookies": "",
                "header": ""
            }
        except requests.exceptions.RequestException as err:
            logger.error(f"Request error crawling URL '{url}': {str(err)}")
            rule["sourceContent"] = {
                "content": "",
                "cookies": "",
                "header": ""
            }
        except Exception as err:
            logger.error(f"Unexpected error in crawlUrl for '{url}': {str(err)}", exc_info=True)
            rule["sourceContent"] = {
                "content": "",
                "cookies": "",
                "header": ""
            }
        
        return rule


    def _fallback_regex_search(self, pattern, content):
        """Fallback regex search when ripgrep is not available."""
        try:
            # Use case-insensitive search by default
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            if matches:
                # Return the first match, handling both string and tuple results
                if isinstance(matches[0], tuple):
                    return matches[0][0] if matches[0][0] else matches[0]
                return matches[0]
            return ""
        except re.error as e:
            logger.error(f"Regex error with pattern '{pattern}': {e}")
            return ""

    def _fallback_regex_search_groups(self, pattern, content):
        """Fallback regex search with group extraction for version detection."""
        try:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                # Return the first captured group, or the full match if no groups
                return match.group(1) if match.groups() else match.group(0)
            return ""
        except re.error as e:
            logger.error(f"Regex error with pattern '{pattern}': {e}")
            return ""

    def runRipGrep(self, pattern, sourceContent):
        """Run pattern matching using ripgrep or fallback to regex."""
        if not sourceContent:
            return ""
            
        # Read content if it's a file path
        content = self._read_file_content(sourceContent)
        
        if self.ripgrep_available:
            try:
                # Create a temporary file for ripgrep
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt", encoding='utf-8') as temp_file:
                    temp_file.write(content)
                    temp_file_path = temp_file.name
                
                ripgrep_cmd = [
                    "rg",
                    "--no-line-number",  
                    "-i", 
                    pattern,
                    temp_file_path,
                    "-o"
                ]
                process = subprocess.Popen(ripgrep_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                ripgrepResult, error = process.communicate(timeout=10)
                
                # Clean up temp file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                
                if process.returncode == 0:
                    matchedSignature = ripgrepResult.decode("utf-8").strip().split("\n")[0]
                    return matchedSignature
                else:
                    logger.debug(f"Ripgrep found no matches for pattern: {pattern}")
                    return ""
            except subprocess.TimeoutExpired:
                logger.warning(f"Ripgrep timeout for pattern: {pattern}")
                process.kill()
                return self._fallback_regex_search(pattern, content)
            except Exception as e:
                logger.error(f"Error running ripgrep: {e}")
                return self._fallback_regex_search(pattern, content)
        else:
            return self._fallback_regex_search(pattern, content)

    def runRipGrepWithGroups(self, pattern, sourceContent):
        """Run pattern matching with group extraction using ripgrep or fallback to regex."""
        if not sourceContent:
            return ""
            
        # Read content if it's a file path
        content = self._read_file_content(sourceContent)
        
        if self.ripgrep_available:
            try:
                # Create a temporary file for ripgrep
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt", encoding='utf-8') as temp_file:
                    temp_file.write(content)
                    temp_file_path = temp_file.name
                
                ripgrep_cmd = [
                    "rg",
                    "--no-line-number",  
                    "-i", 
                    pattern,
                    temp_file_path,
                    "-o"
                ]
                process = subprocess.Popen(ripgrep_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                ripgrepResult, error = process.communicate(timeout=10)
                
                # Clean up temp file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                
                if process.returncode == 0:
                    matchedSignature = ripgrepResult.decode("utf-8").strip().split("\n")[0]
                    # Try to extract version from the matched string
                    version_match = re.search(r'(\d+\.\d+(?:\.\d+)*)', matchedSignature)
                    if version_match:
                        return version_match.group(1)
                    return matchedSignature
                else:
                    logger.debug(f"Ripgrep found no matches for pattern: {pattern}")
                    return ""
            except subprocess.TimeoutExpired:
                logger.warning(f"Ripgrep timeout for pattern: {pattern}")
                process.kill()
                return self._fallback_regex_search_groups(pattern, content)
            except Exception as e:
                logger.error(f"Error running ripgrep: {e}")
                return self._fallback_regex_search_groups(pattern, content)
        else:
            return self._fallback_regex_search_groups(pattern, content)


    def parseSignatures(self, techRegex, VersionRegex, sourceContent):
        techMatcher = ''
        detectedVersions = ''

        if techRegex:
            techMatcher = self.runRipGrep(techRegex, sourceContent)

            if techMatcher and VersionRegex:
                detectedVersions = self.runRipGrepWithGroups(VersionRegex, sourceContent)

        return techMatcher, detectedVersions


    def processResult(self, baseUrl):
        try:
            final_results = []

            for signature in self.custom_signatures:
                discoveryRules = signature.get("discoveryRules", [])
                techName = signature.get("techName")

                # Expand rules with path arrays into individual rules
                expanded_rules = []
                for rule in discoveryRules:
                    paths = rule.get("path", [])
                    if isinstance(paths, list):
                        for path in paths:
                            expanded_rule = rule.copy()
                            expanded_rule["path"] = path
                            expanded_rules.append(expanded_rule)
                    else:
                        # If path is already a string, use as-is
                        expanded_rules.append(rule)

                # Get threading configuration
                threading_config = self.config_loader.get_threading_config()
                max_workers = threading_config.get('max_workers', 10)
                
                sourceCrawled = list()
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    saveRequests = {executor.submit(self.crawlUrl, baseUrl, rule.copy()): rule for rule in expanded_rules}
                    for future in concurrent.futures.as_completed(saveRequests):
                        result = future.result()
                        if result:
                            sourceCrawled.append(result)

                techVersionDetected = False
                detectedVersionSource = None
                detectedPath = ""

                for sourceData in sourceCrawled:
                    sourceType = sourceData['type']
                    sourcePath = sourceData['sourceContent'].get(sourceType, "")

                    techMatcher, detectedVersions = self.parseSignatures(sourceData['techRegex'], sourceData['versionRegex'], sourcePath)

                    if techMatcher:
                        techVersionDetected = True
                        detectedPath = sourceData['path']
                        detectedVersionSource = sourceType

                        result_entry = {
                            "url": baseUrl,
                            "techname": {
                                techName: detectedVersions if detectedVersions else ""
                            },
                            "path": detectedPath if techVersionDetected else "",
                            "type": detectedVersionSource if techVersionDetected else ""
                        }

                        final_results.append(result_entry)

            return final_results

        except Exception as e:
            logger.error(f"Error processing result: {e}")
            return []


