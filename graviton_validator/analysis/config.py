"""
Configuration management for component filtering patterns.
"""

import json
import os
from typing import Dict, List, Optional


class FilterConfig:
    """Configuration loader for component filtering patterns."""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration loader.
        
        Args:
            config_file: Optional path to configuration file. If None, uses default patterns.
        """
        self.config_file = config_file
        self.patterns = self._load_patterns()
    
    def _load_patterns(self) -> Dict[str, List[str]]:
        """
        Load detection patterns from configuration file or use defaults.
        
        Returns:
            Dictionary with pattern lists for different component types
        """
        if self.config_file and os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    return config_data.get('patterns', {})
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config file {self.config_file}: {e}")
                print("Using default patterns.")
        
        return self._get_default_patterns()
    
    def _get_default_patterns(self) -> Dict[str, List[str]]:
        """
        Get default detection patterns.
        
        Returns:
            Dictionary with default pattern lists
        """
        return {
            'kernel': [
                r'.*\.ko$',  # Kernel modules
                r'^kernel-.*',
                r'.*-kernel-.*',
                r'^linux-.*',
                r'^.*-driver$',
                r'^.*-drivers$'
            ],
            'system_library': [
                r'^lib(c|ssl|crypto|z|m|dl|pthread|rt).*',
                r'^glibc.*',
                r'^systemd$',
                r'^systemd-.*',
                r'^libc6.*',
                r'^libssl.*',
                r'^libcrypto.*',
                r'^zlib.*'
            ],
            'os_utility': [
                r'^(bash|sh|coreutils|util-linux|procps|findutils).*',
                r'^(grep|sed|awk|tar|gzip|gunzip|bzip2|xz).*',
                r'^(mount|umount|fdisk|parted).*',
                r'^(systemctl|service|init).*',
                r'^(ps|top|htop|kill|killall).*'
            ]
        }
    
    def get_patterns(self, pattern_type: str) -> List[str]:
        """
        Get patterns for a specific component type.
        
        Args:
            pattern_type: Type of patterns ('kernel', 'system_library', 'os_utility')
            
        Returns:
            List of regex patterns for the specified type
        """
        return self.patterns.get(pattern_type, [])
    
    def add_patterns(self, pattern_type: str, patterns: List[str]) -> None:
        """
        Add additional patterns for a component type.
        
        Args:
            pattern_type: Type of patterns ('kernel', 'system_library', 'os_utility')
            patterns: List of regex patterns to add
        """
        if pattern_type not in self.patterns:
            self.patterns[pattern_type] = []
        self.patterns[pattern_type].extend(patterns)
    
    def save_config(self, output_file: str) -> None:
        """
        Save current patterns to a configuration file.
        
        Args:
            output_file: Path to output configuration file
        """
        config_data = {
            'patterns': self.patterns,
            'description': 'Component filtering patterns for Graviton Compatibility Validator'
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)


def create_default_config_file(output_file: str) -> None:
    """
    Create a default configuration file with example patterns.
    
    Args:
        output_file: Path to output configuration file
    """
    config = FilterConfig()
    
    # Add some example custom patterns
    config.add_patterns('kernel', [
        r'^custom-kernel-.*',
        r'.*-kmod$'
    ])
    
    config.add_patterns('system_library', [
        r'^myorg-system-.*',
        r'^enterprise-lib-.*'
    ])
    
    config.add_patterns('os_utility', [
        r'^internal-tool-.*',
        r'^admin-util-.*'
    ])
    
    config.save_config(output_file)