"""
Configuration Management Utility

Centralized configuration management for the IoT sensor system with
environment variable support, validation, and hot-reloading capabilities.
"""

import os
import json
import yaml
import configparser
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
import logging


@dataclass
class SensorConfig:
    """Configuration for individual sensors."""
    enabled: bool = True
    timeout_seconds: int = 30
    retry_attempts: int = 3
    sampling_rate_hz: float = 1.0
    health_check_interval: int = 300


@dataclass
class NetworkConfig:
    """Network configuration settings."""
    connection_timeout: int = 10
    read_timeout: int = 30
    max_retries: int = 3
    mqtt_keepalive: int = 60
    thingsboard_url: str = ""
    jwt_token: str = ""


@dataclass
class LoggingConfig:
    """Logging configuration settings."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    max_file_size: str = "10MB"
    backup_count: int = 5
    log_directory: str = "./logs"


@dataclass
class SystemConfig:
    """System-wide configuration."""
    device_id: str = ""
    device_name: str = ""
    location: Dict[str, float] = None
    environment: str = "production"
    debug_mode: bool = False


class ConfigManager:
    """
    Production-grade configuration manager with support for multiple formats,
    environment variables, validation, and hot-reloading.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.config_path = Path(config_path) if config_path else Path("config.yaml")
        self.config_data = {}
        self._watchers = []
        
        # Initialize default configurations
        self.sensor_config = SensorConfig()
        self.network_config = NetworkConfig()
        self.logging_config = LoggingConfig()
        self.system_config = SystemConfig()
        
        # Load configuration
        self.load_config()
        self._apply_environment_overrides()
        self._validate_config()
    
    def load_config(self) -> None:
        """Load configuration from file with format auto-detection."""
        try:
            if not self.config_path.exists():
                self.logger.warning(f"Config file {self.config_path} not found, using defaults")
                self._create_default_config()
                return
            
            # Determine file format and load accordingly
            if self.config_path.suffix.lower() in ['.yaml', '.yml']:
                self._load_yaml_config()
            elif self.config_path.suffix.lower() == '.json':
                self._load_json_config()
            elif self.config_path.suffix.lower() in ['.ini', '.properties']:
                self._load_ini_config()
            else:
                raise ValueError(f"Unsupported config format: {self.config_path.suffix}")
            
            self.logger.info(f"Configuration loaded from {self.config_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            self._create_default_config()
    
    def _load_yaml_config(self) -> None:
        """Load YAML configuration file."""
        with open(self.config_path, 'r') as f:
            self.config_data = yaml.safe_load(f) or {}
    
    def _load_json_config(self) -> None:
        """Load JSON configuration file."""
        with open(self.config_path, 'r') as f:
            self.config_data = json.load(f)
    
    def _load_ini_config(self) -> None:
        """Load INI/Properties configuration file."""
        config = configparser.ConfigParser()
        config.read(self.config_path)
        
        # Convert ConfigParser to dict
        self.config_data = {}
        for section in config.sections():
            self.config_data[section] = dict(config[section])
    
    def _create_default_config(self) -> None:
        """Create default configuration."""
        self.config_data = {
            'sensors': asdict(self.sensor_config),
            'network': asdict(self.network_config),
            'logging': asdict(self.logging_config),
            'system': asdict(self.system_config)
        }
        
        # Save default config to file
        self.save_config()
    
    def _apply_environment_overrides(self) -> None:
        """Apply environment variable overrides."""
        env_mappings = {
            'IOT_DEVICE_ID': ('system', 'device_id'),
            'IOT_DEVICE_NAME': ('system', 'device_name'),
            'IOT_ENVIRONMENT': ('system', 'environment'),
            'IOT_DEBUG_MODE': ('system', 'debug_mode'),
            'IOT_LOG_LEVEL': ('logging', 'level'),
            'IOT_LOG_DIR': ('logging', 'log_directory'),
            'THINGSBOARD_URL': ('network', 'thingsboard_url'),
            'JWT_TOKEN': ('network', 'jwt_token'),
        }
        
        for env_var, (section, key) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                if section not in self.config_data:
                    self.config_data[section] = {}
                
                # Type conversion for boolean values
                if key in ['debug_mode'] and value.lower() in ['true', 'false']:
                    value = value.lower() == 'true'
                
                self.config_data[section][key] = value
                self.logger.debug(f"Applied environment override: {env_var} -> {section}.{key}")
    
    def _validate_config(self) -> None:
        """Validate configuration values."""
        try:
            # Update dataclass instances with loaded config
            if 'sensors' in self.config_data:
                self.sensor_config = SensorConfig(**self.config_data['sensors'])
            
            if 'network' in self.config_data:
                self.network_config = NetworkConfig(**self.config_data['network'])
            
            if 'logging' in self.config_data:
                self.logging_config = LoggingConfig(**self.config_data['logging'])
            
            if 'system' in self.config_data:
                # Handle location field specially
                system_data = self.config_data['system'].copy()
                if 'location' not in system_data:
                    system_data['location'] = {'latitude': 0.0, 'longitude': 0.0}
                self.system_config = SystemConfig(**system_data)
            
            self.logger.info("Configuration validation successful")
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            raise ValueError(f"Invalid configuration: {e}")
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get configuration value with dot notation support."""
        try:
            if section in self.config_data and key in self.config_data[section]:
                return self.config_data[section][key]
            return default
        except Exception:
            return default
    
    def set(self, section: str, key: str, value: Any) -> None:
        """Set configuration value."""
        if section not in self.config_data:
            self.config_data[section] = {}
        
        self.config_data[section][key] = value
        self.logger.debug(f"Configuration updated: {section}.{key} = {value}")
    
    def get_sensor_config(self) -> SensorConfig:
        """Get sensor configuration."""
        return self.sensor_config
    
    def get_network_config(self) -> NetworkConfig:
        """Get network configuration."""
        return self.network_config
    
    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration."""
        return self.logging_config
    
    def get_system_config(self) -> SystemConfig:
        """Get system configuration."""
        return self.system_config
    
    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save based on file extension
            if self.config_path.suffix.lower() in ['.yaml', '.yml']:
                with open(self.config_path, 'w') as f:
                    yaml.dump(self.config_data, f, default_flow_style=False, indent=2)
            elif self.config_path.suffix.lower() == '.json':
                with open(self.config_path, 'w') as f:
                    json.dump(self.config_data, f, indent=2)
            
            self.logger.info(f"Configuration saved to {self.config_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            raise
    
    def reload_config(self) -> None:
        """Reload configuration from file."""
        self.logger.info("Reloading configuration...")
        self.load_config()
        self._apply_environment_overrides()
        self._validate_config()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.config_data.copy()
    
    def __str__(self) -> str:
        """String representation of configuration."""
        return json.dumps(self.config_data, indent=2, default=str)