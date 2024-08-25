import os
import yaml
import json

def load_signatures_from_directory(directory_path):
    signatures = []
    for file_name in os.listdir(directory_path):
        if file_name.endswith(".yaml") or file_name.endswith(".json"):
            file_path = os.path.join(directory_path, file_name)
            with open(file_path, 'r') as file:
                if file_name.endswith(".yaml"):
                    signatures.append(yaml.safe_load(file))
                elif file_name.endswith(".json"):
                    signatures.append(json.load(file))
    return signatures
