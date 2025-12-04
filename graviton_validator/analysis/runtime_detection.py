"""
Runtime Detection Service

Detects runtime types (Python, NodeJS, .NET, Java) from SBOM component data.
"""

import logging
from typing import Dict, Optional, Set

logger = logging.getLogger(__name__)


class RuntimeDetectionService:
    """Service for detecting runtime types from component data."""
    
    def __init__(self):
        """Initialize runtime detection patterns."""
        # PURL-based detection (most reliable)
        self.purl_patterns = {
            'python': ['pkg:pypi/'],
            'nodejs': ['pkg:npm/'],
            'dotnet': ['pkg:nuget/'],
            'java': ['pkg:maven/', 'pkg:gradle/'],
            'ruby': ['pkg:gem/', 'pkg:rubygems/']
        }
        
        # Component type patterns
        self.type_patterns = {
            'python': ['python', 'pypi', 'pip'],
            'nodejs': ['npm', 'node', 'javascript'],
            'dotnet': ['nuget', 'dotnet', 'csharp', 'vb.net'],
            'java': ['maven', 'gradle', 'jar', 'java'],
            'ruby': ['gem', 'ruby', 'rubygems']
        }
        
        # File extension patterns
        self.extension_patterns = {
            'python': ['.py', '.pyx', '.pyo', '.pyc', '.whl'],
            'nodejs': ['.js', '.mjs', '.cjs', '.ts', '.tsx'],
            'dotnet': ['.dll', '.exe', '.nupkg'],
            'java': ['.jar', '.war', '.ear', '.class'],
            'ruby': ['.rb', '.gem', '.gemspec']
        }
        
        # Package name patterns (common runtime packages)
        self.package_patterns = {
            'python': {
                'pip', 'setuptools', 'wheel', 'virtualenv', 'conda',
                'numpy', 'pandas', 'django', 'flask', 'requests',
                'pytest', 'sphinx', 'pillow', 'matplotlib'
            },
            'nodejs': {
                'npm', 'node', 'express', 'react', 'angular', 'vue',
                'lodash', 'axios', 'webpack', 'babel', 'typescript',
                'jest', 'mocha', 'eslint', 'prettier'
            },
            'dotnet': {
                'microsoft.netcore.app', 'microsoft.aspnetcore.app',
                'newtonsoft.json', 'system.text.json', 'entityframework',
                'microsoft.entityframeworkcore', 'serilog', 'automapper',
                'fluentvalidation', 'xunit', 'nunit'
            },
            'java': {
                'spring-boot', 'spring-core', 'hibernate', 'jackson',
                'junit', 'mockito', 'slf4j', 'logback', 'apache-commons',
                'guava', 'gson', 'maven', 'gradle'
            },
            'ruby': {
                'rails', 'railties', 'activerecord', 'actionpack', 'activesupport',
                'nokogiri', 'puma', 'unicorn', 'sidekiq', 'devise', 'rspec',
                'bundler', 'rake', 'ffi', 'pg', 'mysql2', 'redis', 'sassc',
                'bootsnap', 'capistrano', 'factory_bot', 'faker'
            }
        }
    
    def detect_runtime_type(self, component_dict: Dict) -> Optional[str]:
        """
        Detect runtime type from component data.
        
        Args:
            component_dict: Component data with name, version, type, properties
            
        Returns:
            Runtime type string or None if not detected
        """
        # Phase 1: PURL-based detection (highest confidence)
        purl_runtime = self._detect_by_purl(component_dict)
        if purl_runtime:
            logger.debug(f"Detected {purl_runtime} runtime via PURL for {component_dict.get('name')}")
            return purl_runtime
        
        # Phase 2: Component type detection
        type_runtime = self._detect_by_type(component_dict)
        if type_runtime:
            logger.debug(f"Detected {type_runtime} runtime via type for {component_dict.get('name')}")
            return type_runtime
        
        # Phase 3: Package name pattern detection
        name_runtime = self._detect_by_name_patterns(component_dict)
        if name_runtime:
            logger.debug(f"Detected {name_runtime} runtime via name pattern for {component_dict.get('name')}")
            return name_runtime
        
        # Phase 4: File extension detection (lowest confidence)
        extension_runtime = self._detect_by_extensions(component_dict)
        if extension_runtime:
            logger.debug(f"Detected {extension_runtime} runtime via extension for {component_dict.get('name')}")
            return extension_runtime
        
        return None
    
    def _detect_by_purl(self, component_dict: Dict) -> Optional[str]:
        """Detect runtime by PURL (Package URL)."""
        properties = component_dict.get('properties', {})
        purl = properties.get('purl', '') or component_dict.get('purl', '')
        
        if not purl:
            return None
        
        purl_lower = purl.lower()
        for runtime, patterns in self.purl_patterns.items():
            if any(pattern in purl_lower for pattern in patterns):
                return runtime
        
        return None
    
    def _detect_by_type(self, component_dict: Dict) -> Optional[str]:
        """Detect runtime by component type."""
        component_type = component_dict.get('type', '').lower()
        if not component_type:
            return None
        
        for runtime, patterns in self.type_patterns.items():
            if any(pattern in component_type for pattern in patterns):
                return runtime
        
        return None
    
    def _detect_by_name_patterns(self, component_dict: Dict) -> Optional[str]:
        """Detect runtime by package name patterns."""
        component_name = component_dict.get('name', '').lower()
        if not component_name:
            return None
        
        # Direct name matching
        for runtime, package_set in self.package_patterns.items():
            if component_name in package_set:
                return runtime
        
        # Partial name matching for common prefixes/suffixes
        for runtime, package_set in self.package_patterns.items():
            for package in package_set:
                if (component_name.startswith(package) or 
                    component_name.endswith(package) or
                    package in component_name):
                    return runtime
        
        return None
    
    def _detect_by_extensions(self, component_dict: Dict) -> Optional[str]:
        """Detect runtime by file extensions in component name."""
        component_name = component_dict.get('name', '').lower()
        if not component_name:
            return None
        
        for runtime, extensions in self.extension_patterns.items():
            if any(component_name.endswith(ext) for ext in extensions):
                return runtime
        
        return None
    
    def get_supported_runtimes(self) -> Set[str]:
        """Get set of supported runtime types."""
        return set(self.purl_patterns.keys())
    
    def add_custom_patterns(self, runtime: str, patterns: Dict[str, any]) -> None:
        """
        Add custom detection patterns for a runtime.
        
        Args:
            runtime: Runtime type name
            patterns: Dictionary with pattern types and values
        """
        if 'purl' in patterns:
            if runtime not in self.purl_patterns:
                self.purl_patterns[runtime] = []
            self.purl_patterns[runtime].extend(patterns['purl'])
        
        if 'type' in patterns:
            if runtime not in self.type_patterns:
                self.type_patterns[runtime] = []
            self.type_patterns[runtime].extend(patterns['type'])
        
        if 'extensions' in patterns:
            if runtime not in self.extension_patterns:
                self.extension_patterns[runtime] = []
            self.extension_patterns[runtime].extend(patterns['extensions'])
        
        if 'packages' in patterns:
            if runtime not in self.package_patterns:
                self.package_patterns[runtime] = set()
            self.package_patterns[runtime].update(patterns['packages'])