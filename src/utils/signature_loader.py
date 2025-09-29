import os
import yaml
import json
import logging

logger = logging.getLogger(__name__)

def load_signatures_from_directory(directory_path):
    """Load signatures from JSON and YAML files in the specified directory."""
    signatures = []
    
    if not os.path.exists(directory_path):
        logger.error(f"Signatures directory not found: {directory_path}")
        return signatures
    
    try:
        for file_name in sorted(os.listdir(directory_path)):
            if file_name.endswith((".yaml", ".yml", ".json")):
                file_path = os.path.join(directory_path, file_name)
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        if file_name.endswith((".yaml", ".yml")):
                            signature = yaml.safe_load(file)
                        elif file_name.endswith(".json"):
                            signature = json.load(file)
                        
                        if signature and isinstance(signature, dict):
                            # Validate signature structure
                            is_valid, error_msg = validate_signature_structure(signature)
                            if is_valid:
                                signatures.append(signature)
                                logger.debug(f"Loaded signature from {file_name}")
                            else:
                                logger.warning(f"Invalid signature structure in {file_name}: {error_msg}")
                        else:
                            logger.warning(f"Invalid signature format in {file_name}")
                            
                except yaml.YAMLError as e:
                    logger.error(f"Error parsing YAML file {file_name}: {e}")
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing JSON file {file_name}: {e}")
                except Exception as e:
                    logger.error(f"Error loading signature file {file_name}: {e}")
    
    except Exception as e:
        logger.error(f"Error accessing signatures directory {directory_path}: {e}")
    
    logger.info(f"Loaded {len(signatures)} valid signatures from {directory_path}")
    return signatures

def validate_signature_structure(signature):
    """Validate the structure of a signature."""
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
        
        required_fields = ["type", "path", "techRegex"]
        for field in required_fields:
            if field not in rule:
                return False, f"Rule {i} missing required field: {field}"
        
        if rule["type"] not in ["content", "header", "cookies"]:
            return False, f"Rule {i} has invalid type: {rule['type']}"
    
    return True, "Valid signature"
