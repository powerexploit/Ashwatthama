import os
import yaml
import logging

logger = logging.getLogger(__name__)

class ConfigLoader:
    def __init__(self, configPath="config.yaml"):
        self.configPath = configPath
        self.config = self.loadConfig()
    
    def loadConfig(self):
        defaultConfig = {
            "request": {
                "timeout": 15,
                "max_retries": 3,
                "user_agent_rotation": True,
                "follow_redirects": True,
                "verify_ssl": False
            },
            "threading": {
                "max_workers": 10,
                "thread_timeout": 30
            },
            "output": {
                "default_format": "json",
                "colorize": True,
                "verbose": False,
                "save_logs": True
            },
            "signatures": {
                "auto_reload": False,
                "validation": True,
                "cache_enabled": True
            },
            "logging": {
                "level": "INFO",
                "file_rotation": True,
                "max_file_size_mb": 10,
                "backup_count": 5
            }
        }
        
        if not os.path.exists(self.configPath):
            logger.warning(f"Config file {self.configPath} not found, using defaults")
            return defaultConfig
        
        try:
            with open(self.configPath, 'r', encoding='utf-8') as file:
                userConfig = yaml.safe_load(file) or {}
            
            config = self._mergeConfigs(defaultConfig, userConfig)
            logger.info(f"Configuration loaded from {self.configPath}")
            return config
            
        except yaml.YAMLError as e:
            logger.error(f"Error parsing config file: {e}")
            return defaultConfig
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            return defaultConfig
    
    def _mergeConfigs(self, default, user):
        result = default.copy()
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._mergeConfigs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get(self, keyPath, default=None):
        keys = keyPath.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def getRequestConfig(self):
        return self.config.get("request", {})
    
    def getThreadingConfig(self):
        return self.config.get("threading", {})
    
    def getOutputConfig(self):
        return self.config.get("output", {})
    
    def getSignaturesConfig(self):
        return self.config.get("signatures", {})
    
    def getLoggingConfig(self):
        return self.config.get("logging", {})
