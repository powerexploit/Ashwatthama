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
from utils.logs_handler import createLogger
from utils.signature_loader import loadSignaturesFromDirectory
from utils.config_loader import ConfigLoader

logger = createLogger(__name__, remoteLogging=False, logLevel="INFO")

class ServiceDetection:
    def __init__(self, configPath="config.yaml"):
        self.configLoader = ConfigLoader(configPath)
        requestConfig = self.configLoader.getRequestConfig()
        
        self.user_agent = UserAgent()
        self.crawledDataCache = {}
        self.customSignatures = loadSignaturesFromDirectory(os.path.join(os.path.dirname(__file__), '..', 'signatures'))
        
        self.ripgrep_available = self._checkRipgrepAvailability()
        
        self.timeout = requestConfig.get('timeout', 15)
        self.maxRetries = requestConfig.get('max_retries', 3)
        self.followRedirects = requestConfig.get('follow_redirects', True)
        self.verifySsl = requestConfig.get('verify_ssl', False)
        
        self.session = requests.Session()
        retryStrategy = Retry(
            total=self.maxRetries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retryStrategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        logger.info(f"ServiceDetection initialized with timeout={self.timeout}s, maxRetries={self.maxRetries}")
        if self.ripgrep_available:
            logger.info("Ripgrep detected and will be used for pattern matching")
        else:
            logger.warning("Ripgrep not found, using fallback regex matcher")

    def _checkRipgrepAvailability(self):
        try:
            result = subprocess.run(['rg', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logger.info(f"Ripgrep detected: {result.stdout.strip()}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return False

    def _readFileContent(self, filePath):
        if os.path.isfile(filePath):
            try:
                with open(filePath, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Error reading file {filePath}: {e}")
                return ""
        return filePath

    def _cleanupTempFiles(self, sourceContent):
        if isinstance(sourceContent, dict):
            for key, filePath in sourceContent.items():
                if isinstance(filePath, str) and os.path.isfile(filePath):
                    try:
                        os.unlink(filePath)
                        logger.debug(f"Cleaned up temp file: {filePath}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up temp file {filePath}: {e}")

    def crawlUrl(self, baseUrl, rule):
        url = f"{baseUrl.rstrip('/')}{rule.get('path')}"
        
        try:
            headers = {
                'User-Agent': self.user_agent.random  
            }

            if url in self.crawledDataCache:
                rule["sourceContent"] = self.crawledDataCache[url]
                return rule
                        
            response = self.session.get(
                url, 
                headers=headers, 
                timeout=self.timeout, 
                verify=self.verifySsl,
                allow_redirects=self.followRedirects
            )
            
            response.raise_for_status()
            
            content = response.text
            cookies = response.cookies
            header = response.headers

            rule["sourceContent"] = {
                "content": content,
                "cookies": str(cookies),
                "header": str(header)
            }
            
            self.crawledDataCache[url] = rule["sourceContent"]
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


    def _fallbackRegexSearch(self, pattern, content):
        try:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            if matches:
                if isinstance(matches[0], tuple):
                    return matches[0][0] if matches[0][0] else matches[0]
                return matches[0]
            return ""
        except re.error as e:
            logger.error(f"Regex error with pattern '{pattern}': {e}")
            return ""

    def _fallbackRegexSearchGroups(self, pattern, content):
        try:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1) if match.groups() else match.group(0)
            return ""
        except re.error as e:
            logger.error(f"Regex error with pattern '{pattern}': {e}")
            return ""

    def runRipGrep(self, pattern, sourceContent):
        if not sourceContent:
            return ""
            
        content = self._readFileContent(sourceContent)
        
        if self.ripgrep_available:
            try:
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
                return self._fallbackRegexSearch(pattern, content)
        else:
            return self._fallbackRegexSearch(pattern, content)

    def runRipGrepWithGroups(self, pattern, sourceContent):
        if not sourceContent:
            return ""
            
        content = self._readFileContent(sourceContent)
        
        if self.ripgrep_available:
            try:
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
                
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                
                if process.returncode == 0:
                    matchedSignature = ripgrepResult.decode("utf-8").strip().split("\n")[0]
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
                return self._fallbackRegexSearchGroups(pattern, content)
        else:
            return self._fallbackRegexSearchGroups(pattern, content)


    def parseSignatures(self, techRegex, versionRegex, sourceContent):
        techMatcher = ''
        detectedVersions = ''

        if techRegex:
            techMatcher = self.runRipGrep(techRegex, sourceContent)

            if techMatcher and versionRegex:
                detectedVersions = self.runRipGrepWithGroups(versionRegex, sourceContent)

        return techMatcher, detectedVersions


    def processResult(self, baseUrl):
        try:
            final_results = []

            for signature in self.customSignatures:
                discoveryRules = signature.get("discoveryRules", [])
                techName = signature.get("techName")

                expanded_rules = []
                for rule in discoveryRules:
                    paths = rule.get("path", [])
                    if isinstance(paths, list):
                        for path in paths:
                            expanded_rule = rule.copy()
                            expanded_rule["path"] = path
                            expanded_rules.append(expanded_rule)
                    else:
                        expanded_rules.append(rule)

                threadingConfig = self.configLoader.getThreadingConfig()
                maxWorkers = threadingConfig.get('max_workers', 10)
                
                sourceCrawled = list()
                with concurrent.futures.ThreadPoolExecutor(max_workers=maxWorkers) as executor:
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


