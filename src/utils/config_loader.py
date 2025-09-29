import os
import yaml
import logging

logger = logging.getLogger(__name__)

class ConfigLoader:
    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration from YAML file."""
        default_config = {
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
        
        if not os.path.exists(self.config_path):
            logger.warning(f"Config file {self.config_path} not found, using defaults")
            return default_config
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                user_config = yaml.safe_load(file) or {}
            
            # Merge user config with defaults
            config = self._merge_configs(default_config, user_config)
            logger.info(f"Configuration loaded from {self.config_path}")
            return config
            
        except yaml.YAMLError as e:
            logger.error(f"Error parsing config file: {e}")
            return default_config
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            return default_config
    
    def _merge_configs(self, default, user):
        """Recursively merge user config with defaults."""
        result = default.copy()
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get(self, key_path, default=None):
        """Get configuration value using dot notation (e.g., 'request.timeout')."""
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_request_config(self):
        """Get request configuration."""
        return self.config.get("request", {})
    
    def get_threading_config(self):
        """Get threading configuration."""
        return self.config.get("threading", {})
    
    def get_output_config(self):
        """Get output configuration."""
        return self.config.get("output", {})
    
    def get_signatures_config(self):
        """Get signatures configuration."""
        return self.config.get("signatures", {})
    
    def get_logging_config(self):
        """Get logging configuration."""
        return self.config.get("logging", {})
