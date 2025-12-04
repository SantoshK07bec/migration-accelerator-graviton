#!/usr/bin/env python3
"""
Runtime configuration management for multi-runtime dependency analysis.
Handles OS and runtime version detection and overrides.
"""

import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional


class RuntimeConfig:
    """Manages runtime configuration with SBOM-specific overrides."""
    
    DEFAULT_VERSIONS = {
        'os_version': 'amazon-linux-2023',
        'python': '3.11',
        'nodejs': '20.10.0',
        'dotnet': '8.0',
        'ruby': '3.2',
        'java': '17'
    }
    
    COMPATIBLE_VERSIONS = {
        'python': ['3.8', '3.9', '3.10', '3.11', '3.12'],
        'nodejs': ['16', '18', '20', '21'],
        'dotnet': ['6.0', '7.0', '8.0'],
        'ruby': ['3.0', '3.1', '3.2', '3.3'],
        'java': ['11', '17', '21']
    }
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.config_data = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        if not self.config_file or not Path(self.config_file).exists():
            return {
                'default_versions': self.DEFAULT_VERSIONS.copy(),
                'sbom_overrides': {}
            }
        
        try:
            with open(self.config_file, 'r') as f:
                if self.config_file.endswith('.yaml') or self.config_file.endswith('.yml'):
                    config = yaml.safe_load(f)
                else:
                    config = json.load(f)
            
            # Merge with defaults
            merged_config = {
                'default_versions': {**self.DEFAULT_VERSIONS, **config.get('default_versions', {})},
                'sbom_overrides': config.get('sbom_overrides', {})
            }
            return merged_config
            
        except Exception as e:
            print(f"Warning: Failed to load config file {self.config_file}: {e}")
            return {
                'default_versions': self.DEFAULT_VERSIONS.copy(),
                'sbom_overrides': {}
            }
    
    def get_runtime_version(self, runtime: str, sbom_name: Optional[str] = None, 
                          detected_version: Optional[str] = None, supported_versions: Optional[list] = None) -> str:
        """Get runtime version with override priority."""
        # Priority: Override config → SBOM detected (if supported) → Default config → Latest stable
        
        # Check SBOM-specific override
        if sbom_name and sbom_name in self.config_data['sbom_overrides']:
            sbom_config = self.config_data['sbom_overrides'][sbom_name]
            if 'runtimes' in sbom_config and runtime in sbom_config['runtimes']:
                return sbom_config['runtimes'][runtime]
        
        # Use detected version if available and supported
        if detected_version and detected_version not in ['unknown', '', 'not_detected']:
            # Check against provided supported versions first, then fallback to compatibility check
            if supported_versions:
                is_supported = any(detected_version.startswith(v) for v in supported_versions)
            else:
                is_supported = self._is_graviton_compatible_version(runtime, detected_version)
            
            if is_supported:
                return detected_version
        
        # Use default config version
        return self.config_data['default_versions'].get(runtime, self.DEFAULT_VERSIONS.get(runtime, 'latest'))
    
    def get_os_version(self, sbom_name: Optional[str] = None, 
                      detected_os: Optional[str] = None) -> str:
        """Get OS version with override priority."""
        # Check SBOM-specific override
        if sbom_name and sbom_name in self.config_data['sbom_overrides']:
            sbom_config = self.config_data['sbom_overrides'][sbom_name]
            if 'os_version' in sbom_config:
                return sbom_config['os_version']
        
        # Use detected OS if available and compatible
        if detected_os and self._is_graviton_compatible_os(detected_os):
            return detected_os
        
        # Use default config version
        return self.config_data['default_versions']['os_version']
    
    def _is_graviton_compatible_version(self, runtime: str, version: str) -> bool:
        """Check if runtime version is Graviton compatible."""
        if runtime not in self.COMPATIBLE_VERSIONS:
            return True  # Assume compatible if not in list
        
        # Check if version starts with any compatible version
        return any(version.startswith(v) for v in self.COMPATIBLE_VERSIONS[runtime])
    
    def _is_graviton_compatible_os(self, os_version: str) -> bool:
        """Check if OS version is Graviton compatible."""
        compatible_os = [
            'amazon-linux', 'ubuntu', 'debian', 'rhel', 'centos', 'fedora'
        ]
        return any(os_name in os_version.lower() for os_name in compatible_os)
    
    def detect_versions_from_sbom(self, sbom_data: Dict[str, Any]) -> Dict[str, str]:
        """Detect runtime and OS versions from SBOM metadata."""
        detected = {}
        
        # Look for runtime versions in SBOM metadata
        metadata = sbom_data.get('metadata', {})
        
        # Check component properties for runtime versions
        components = sbom_data.get('components', [])
        for component in components:
            purl = component.get('purl', '')
            
            # Extract runtime versions from PURLs
            if purl.startswith('pkg:pypi/'):
                # Python version might be in component properties
                if 'python' not in detected:
                    detected['python'] = self._extract_python_version(component)
            elif purl.startswith('pkg:npm/'):
                if 'nodejs' not in detected:
                    detected['nodejs'] = self._extract_nodejs_version(component)
            elif purl.startswith('pkg:nuget/'):
                if 'dotnet' not in detected:
                    detected['dotnet'] = self._extract_dotnet_version(component)
            elif purl.startswith('pkg:gem/'):
                if 'ruby' not in detected:
                    detected['ruby'] = self._extract_ruby_version(component)
            elif purl.startswith('pkg:maven/'):
                if 'java' not in detected:
                    detected['java'] = self._extract_java_version(component)
        
        # Extract OS version from metadata
        os_version = self._extract_os_version(sbom_data)
        if os_version:
            detected['os_version'] = os_version
        
        return detected
    
    def _extract_python_version(self, component: Dict[str, Any]) -> Optional[str]:
        """Extract Python version from component."""
        # Look in component properties for Python version indicators
        properties = component.get('properties', {})
        if isinstance(properties, dict):
            for key, value in properties.items():
                if 'python' in key.lower() and any(c.isdigit() for c in str(value)):
                    return str(value)
        return None
    
    def _extract_nodejs_version(self, component: Dict[str, Any]) -> Optional[str]:
        """Extract Node.js version from component."""
        properties = component.get('properties', {})
        if isinstance(properties, dict):
            for key, value in properties.items():
                if 'node' in key.lower() and any(c.isdigit() for c in str(value)):
                    return str(value)
        return None
    
    def _extract_dotnet_version(self, component: Dict[str, Any]) -> Optional[str]:
        """Extract .NET version from component."""
        properties = component.get('properties', {})
        if isinstance(properties, dict):
            for key, value in properties.items():
                if any(framework in key.lower() for framework in ['net', 'dotnet', 'framework']) and any(c.isdigit() for c in str(value)):
                    return str(value)
        return None
    
    def _extract_ruby_version(self, component: Dict[str, Any]) -> Optional[str]:
        """Extract Ruby version from component."""
        properties = component.get('properties', {})
        if isinstance(properties, dict):
            for key, value in properties.items():
                if 'ruby' in key.lower() and any(c.isdigit() for c in str(value)):
                    return str(value)
        return None
    
    def _extract_java_version(self, component: Dict[str, Any]) -> Optional[str]:
        """Extract Java version from component."""
        properties = component.get('properties', {})
        if isinstance(properties, dict):
            for key, value in properties.items():
                if 'java' in key.lower() and any(c.isdigit() for c in str(value)):
                    return str(value)
        return None
    
    def _extract_os_version(self, sbom_data: Dict[str, Any]) -> Optional[str]:
        """Extract OS version from SBOM metadata."""
        metadata = sbom_data.get('metadata', {})
        
        # Look for OS information in metadata
        os_name = metadata.get('os_name')
        os_version = metadata.get('os_version')
        
        if os_name and os_version:
            return f"{os_name}:{os_version}"
        elif os_name:
            return os_name
        elif os_version:
            return os_version
        
        return None
    
    def create_sample_config(self, output_path: str):
        """Create a sample configuration file."""
        sample_config = {
            'default_versions': self.DEFAULT_VERSIONS.copy(),
            'sbom_overrides': {
                'my-app-sbom.json': {
                    'os_version': 'ubuntu-20.04',
                    'runtimes': {
                        'python': '3.9',
                        'nodejs': '18.17.0',
                        'dotnet': '6.0',
                        'ruby': '3.1'
                    }
                }
            }
        }
        
        with open(output_path, 'w') as f:
            if output_path.endswith('.yaml') or output_path.endswith('.yml'):
                yaml.dump(sample_config, f, default_flow_style=False, indent=2)
            else:
                json.dump(sample_config, f, indent=2)