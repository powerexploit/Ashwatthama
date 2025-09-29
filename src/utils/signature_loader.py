import os
import yaml
import json
import logging

logger = logging.getLogger(__name__)

def loadSignaturesFromDirectory(directoryPath):
    signatures = []
    
    if not os.path.exists(directoryPath):
        logger.error(f"Signatures directory not found: {directoryPath}")
        return signatures
    
    try:
        for fileName in sorted(os.listdir(directoryPath)):
            if fileName.endswith((".yaml", ".yml", ".json")):
                filePath = os.path.join(directoryPath, fileName)
                try:
                    with open(filePath, 'r', encoding='utf-8') as file:
                        if fileName.endswith((".yaml", ".yml")):
                            signature = yaml.safe_load(file)
                        elif fileName.endswith(".json"):
                            signature = json.load(file)
                        
                        if signature and isinstance(signature, dict):
                            isValid, errorMsg = validateSignatureStructure(signature)
                            if isValid:
                                signatures.append(signature)
                                logger.debug(f"Loaded signature from {fileName}")
                            else:
                                logger.warning(f"Invalid signature structure in {fileName}: {errorMsg}")
                        else:
                            logger.warning(f"Invalid signature format in {fileName}")
                            
                except yaml.YAMLError as e:
                    logger.error(f"Error parsing YAML file {fileName}: {e}")
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing JSON file {fileName}: {e}")
                except Exception as e:
                    logger.error(f"Error loading signature file {fileName}: {e}")
    
    except Exception as e:
        logger.error(f"Error accessing signatures directory {directoryPath}: {e}")
    
    logger.info(f"Loaded {len(signatures)} valid signatures from {directoryPath}")
    return signatures

def validateSignatureStructure(signature):
    if not isinstance(signature, dict):
        return False, "Signature must be a dictionary"
    
    if "techName" not in signature:
        return False, "Missing 'techName' field"
    
    if "discoveryRules" not in signature:
        return False, "Missing 'discoveryRules' field"
    
    if not isinstance(signature["discoveryRules"], list):
        return False, "'discoveryRules' must be a list"
    
    for i, rule in enumerate(signature["discoveryRules"]):
        if not isinstance(rule, dict):
            return False, f"Rule {i} must be a dictionary"
        
        requiredFields = ["type", "path", "techRegex"]
        for field in requiredFields:
            if field not in rule:
                return False, f"Rule {i} missing required field: {field}"
        
        if rule["type"] not in ["content", "header", "cookies"]:
            return False, f"Rule {i} has invalid type: {rule['type']}"
    
    return True, "Valid signature"
