import time
import requests
import tempfile
import subprocess
import concurrent.futures
import os
from fake_useragent import UserAgent
from utils.logs_handler import create_logger
from utils.signature_loader import load_signatures_from_directory

logger = create_logger(__name__, remote_logging=False)

class ServiceDetection:
    def __init__(self):
        self.user_agent = UserAgent()
        self.crawled_data_cache = {}
        self.custom_signatures = load_signatures_from_directory(os.path.join(os.path.dirname(__file__), '..', 'signatures'))


    def crawlUrl(self, baseUrl, rule):
        try:
            headers = {
                'User-Agent': self.user_agent.random  
            }
            
            url = f"{baseUrl.rstrip('/')}{rule.get('path')}"

            # Check if the crawled data for this URL is already in the cache
            if url in self.crawled_data_cache:
                rule["sourceContent"] = self.crawled_data_cache[url]
                return rule
                        
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            
            content = response.text
            cookies = response.cookies
            header = response.headers

            # Save content, cookies, and headers to temporary files
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt", encoding='utf-8') as content_file:
                content_file.write(str(content))
                content_path = content_file.name

            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt", encoding='utf-8') as cookies_file:
                cookies_file.write(str(cookies))
                cookies_path = cookies_file.name

            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt", encoding='utf-8') as headers_file:
                headers_file.write(str(header))
                headers_path = headers_file.name

            rule["sourceContent"] = {
                "content": content_path,
                "cookies": cookies_path,
                "header": headers_path
            }
            
            self.crawled_data_cache[url] = rule["sourceContent"]  # Store the crawled data in the cache
            
        except requests.exceptions.RequestException as err:
            logger.error(f"Error crawling URL '{baseUrl}': {str(err)}")
            rule["sourceContent"] = {
                "content": "",
                "cookies": "",
                "header": ""
            }
        
        return rule


    def runRipGrep(self, pattern, sourceContent):
        ripgrep_cmd = [
                "rg",
                "--no-line-number",  
                "-i", 
                pattern,
                sourceContent,
                "-o"
            ]
        process = subprocess.Popen(ripgrep_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ripgrepResult, error = process.communicate()
        matchedSignature = ripgrepResult.decode("utf-8").strip().split("\n")[0]
        
        return matchedSignature


    def parseSignatures(self, techRegex, VersionRegex, sourceContent):
        techMatcher = ''
        detectedVersions = ''

        if techRegex:
            techMatcher = self.runRipGrep(techRegex, sourceContent)

            if techMatcher and VersionRegex:
                detectedVersions = self.runRipGrep(VersionRegex, sourceContent)

        return techMatcher, detectedVersions


    def processResult(self, baseUrl):
        try:
            final_results = []

            for signature in self.custom_signatures:
                discoveryRules = signature.get("discoveryRules", [])
                techName = signature.get("techName")

                sourceCrawled = list()
                with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                    saveRequests = {executor.submit(self.crawlUrl, baseUrl, rule.copy()): rule for rule in discoveryRules}
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


