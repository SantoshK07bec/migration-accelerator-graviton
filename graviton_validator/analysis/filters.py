"""
Component filtering system for excluding system packages and OS/kernel components.
"""

import re
from typing import Dict, List, Optional, Tuple
from enum import Enum

from ..models import SoftwareComponent
from .config import FilterConfig
from ..os_detection import OSDetector
from ..os_detection.os_configs import OSConfigManager


class ComponentCategory(Enum):
    """Component categorization for OS-aware filtering."""
    SYSTEM_COMPATIBLE = "system_compatible"
    SYSTEM_UNKNOWN = "system_unknown"
    APPLICATION = "application"
    KERNEL_MODULE = "kernel_module"


class ComponentFilter:
    """Component filtering logic for excluding system packages and OS/kernel components."""
    
    def __init__(self, os_kernel_detector: Optional['OSKernelDetector'] = None, 
                 config_file: Optional[str] = None,
                 os_detector: Optional[OSDetector] = None,
                 os_config_manager: Optional[OSConfigManager] = None,
                 sbom_format: Optional[str] = None):
        """
        Initialize the component filter.
        
        Args:
            os_kernel_detector: Optional OSKernelDetector instance. If None, creates default.
            config_file: Optional path to configuration file for custom patterns.
            os_detector: Optional OSDetector for OS identification.
            os_config_manager: Optional OSConfigManager for OS compatibility data.
            sbom_format: Optional SBOM format ("CycloneDX", "SPDX", "app_identifier")
        """
        if os_kernel_detector is None:
            config = FilterConfig(config_file) if config_file else None
            os_kernel_detector = OSKernelDetector(config=config, os_config_manager=os_config_manager)
        self.os_kernel_detector = os_kernel_detector
        
        # OS-aware components
        self.os_config_manager = os_config_manager or OSConfigManager()
        self.sbom_format = sbom_format
    
    def should_exclude_component(self, component: Dict, sbom_source: str, detected_os: Optional[str] = None) -> bool:
        """
        Determine if a component should be excluded from analysis.
        
        Args:
            component: Component data from SBOM
            sbom_source: Source of the SBOM (e.g., "app_identifier", "third_party")
            detected_os: Optional detected OS name for OS-aware filtering
            
        Returns:
            True if component should be excluded, False otherwise
        """
        # For app_identifier SBOMs: exclude both system packages and OS/kernel components
        if sbom_source == "app_identifier":
            if self.is_system_package(component) or self.is_os_kernel_component(component):
                return True
        
        # For third-party SBOMs: only exclude OS/kernel components that are NOT system packages
        elif sbom_source == "third_party":
            # If it's explicitly marked as a system package, don't exclude it
            if self.is_system_package(component):
                return False
            # Otherwise, exclude if it's an OS/kernel component
            if self.is_os_kernel_component(component):
                return True
        
        # For other SBOM sources: only exclude OS/kernel components
        else:
            if self.is_os_kernel_component(component):
                return True
        
        return False
    
    def filter_components(self, components: List[SoftwareComponent], sbom_source: str, detected_os: Optional[str] = None) -> List[SoftwareComponent]:
        """
        Filter a list of components, excluding system packages and OS/kernel components.
        
        Args:
            components: List of SoftwareComponent objects
            sbom_source: Source of the SBOM (e.g., "app_identifier", "third_party")
            detected_os: Optional detected OS name for OS-aware filtering
            
        Returns:
            Filtered list of SoftwareComponent objects
        """
        filtered_components = []
        
        for component in components:
            # Convert SoftwareComponent to dict for compatibility with existing methods
            component_dict = {
                "name": component.name,
                "version": component.version,
                "type": component.component_type,
                "properties": component.properties
            }
            
            if not self.should_exclude_component(component_dict, sbom_source, detected_os):
                filtered_components.append(component)
        
        return filtered_components
    
    def is_system_package(self, component: Dict) -> bool:
        """
        Check if a component is a system package.
        
        This method specifically detects app_identifier.sh system packages and other
        system package indicators.
        
        Args:
            component: Component data from SBOM
            
        Returns:
            True if component is a system package, False otherwise
        """
        # Primary check: app_identifier.sh system package marker
        if isinstance(component.get("properties"), dict):
            package_type = component["properties"].get("package:type")
            if package_type == "system-package":
                return True
            
            # Additional property checks for system packages
            package_source = component["properties"].get("package:source", "").lower()
            if package_source in ["system", "os", "kernel"]:
                return True
        
        # Check component type for system indicators
        component_type = (component.get("type") or "").lower()
        if component_type in ["system-package", "os-package", "system"]:
            return True
        
        # Check for system package name patterns from JSON configuration
        component_name = (component.get("name") or "").lower()
        
        # Get system package name patterns from OS config
        detection_rules = self.os_kernel_detector.os_config_manager.get_all_detection_rules()
        system_patterns = detection_rules.get("system_package_patterns", {})
        system_package_patterns = system_patterns.get("system_package_names", [])
        
        for pattern in system_package_patterns:
            if re.match(pattern, component_name, re.IGNORECASE):
                return True
        
        return False
    
    def is_os_kernel_component(self, component: Dict) -> bool:
        """
        Check if a component is an OS or kernel component using SBOM-format-aware logic.
        
        Args:
            component: Component data from SBOM
            
        Returns:
            True if component is OS/kernel related, False otherwise
        """
        return self._is_kernel_module_by_format(component) or self._is_system_library_or_utility(component)
    
    def _is_kernel_module_by_format(self, component: Dict) -> bool:
        """
        Check if component is a kernel module based on SBOM format.
        
        Args:
            component: Component data from SBOM
            
        Returns:
            True if component is a kernel module
        """
        component_name = component.get("name", "")
        component_type = component.get("type", "")
        properties = component.get("properties", {})
        
        # CycloneDX format: check syft:package:type property
        if self.sbom_format == "CycloneDX":
            syft_package_type = properties.get("syft:package:type", "")
            if syft_package_type.lower() == "linux-kernel-module":
                return True
        
        # app_identifier format: check package:type property
        elif self.sbom_format == "app_identifier":
            package_type = properties.get("package:type", "")
            if package_type.lower() in ["linux-kernel-module", "kernel-module"]:
                return True
        
        # SPDX or unknown format: check main component type
        else:
            if component_type.lower() in ["linux-kernel-module", "kernel-module", "driver"]:
                return True
        
        # Fallback: check name patterns for all formats
        return self.os_kernel_detector.is_kernel_module_by_name(component_name)
    
    def _is_system_library_or_utility(self, component: Dict) -> bool:
        """
        Check if component is a system library or OS utility.
        
        Args:
            component: Component data from SBOM
            
        Returns:
            True if component is a system library or OS utility
        """
        component_name = component.get("name", "")
        return (
            self.os_kernel_detector.is_system_library(component_name) or
            self.os_kernel_detector.is_os_utility(component_name)
        )
    
    def is_system_package_by_os(self, component: Dict, detected_os: str, os_knowledge_base=None) -> bool:
        """
        Check if component is a system package based on detected OS using knowledge base.
        
        Args:
            component: Component data from SBOM
            detected_os: Detected operating system name
            os_knowledge_base: Optional OS-specific knowledge base
            
        Returns:
            True if component is a system package for the detected OS
        """
        if not detected_os:
            return self.is_system_package(component)
        
        component_name = component.get("name", "")
        
        # First check if component exists in OS-specific knowledge base
        if os_knowledge_base and hasattr(os_knowledge_base, 'find_software'):
            software_entry = os_knowledge_base.find_software(component_name)
            if software_entry:
                # Check if it's marked as OS native in metadata
                metadata = software_entry.metadata or {}
                if isinstance(metadata, dict) and metadata.get('os_native', False):
                    return True
        
        # Fallback to pattern-based detection for backward compatibility
        patterns = self.os_config_manager.get_detection_patterns(detected_os)
        
        # Check version patterns
        version = component.get("version", "")
        if version:
            for pattern in patterns.get("package_patterns", []):
                if pattern.lower() in version.lower():
                    return True
        
        # Check component type against OS package types
        component_type = component.get("type", "")
        os_info = self.os_config_manager.get_os_info(detected_os)
        if os_info and component_type in os_info.get("package_types", []):
            return True
        
        # Fallback to general system package detection
        return self.is_system_package(component)
    
    def is_graviton_compatible_os(self, os_name: str, os_version: Optional[str] = None) -> bool:
        """
        Check if OS and version are Graviton compatible.
        
        Args:
            os_name: Operating system name
            os_version: Optional OS version
            
        Returns:
            True if OS is Graviton compatible
        """
        return self.os_config_manager.is_os_graviton_compatible(os_name, os_version)
    
    def detect_runtime_type(self, component_dict: Dict) -> Optional[str]:
        """
        Detect runtime type using dedicated runtime detection service.
        
        Args:
            component_dict: Component data from SBOM
            
        Returns:
            Runtime type string ('java', 'python', 'nodejs') or None
        """
        # Use dedicated runtime detection service to keep this method clean
        if not hasattr(self, '_runtime_detector'):
            from .runtime_detection import RuntimeDetectionService
            self._runtime_detector = RuntimeDetectionService()
        
        return self._runtime_detector.detect_runtime_type(component_dict)
    
    def categorize_component(self, component: Dict, detected_os: Optional[str] = None, os_knowledge_base=None) -> ComponentCategory:
        """
        Categorize component based on OS compatibility using knowledge base.
        
        Args:
            component: Component data from SBOM
            detected_os: Optional detected OS name
            os_knowledge_base: Optional OS-specific knowledge base
            
        Returns:
            ComponentCategory enum value
        """
        component_type = component.get("type", "") or ""
        component_name = component.get("name", "")
        
        # Kernel modules are always compatible if OS is compatible
        if component_type.lower() in ["linux-kernel-module", "kernel-module"]:
            if detected_os and self.is_graviton_compatible_os(detected_os):
                return ComponentCategory.SYSTEM_COMPATIBLE
            else:
                return ComponentCategory.SYSTEM_UNKNOWN
        
        # Check if component exists in OS-specific knowledge base
        if detected_os and os_knowledge_base and hasattr(os_knowledge_base, 'find_software'):
            software_entry = os_knowledge_base.find_software(component_name)
            if software_entry:
                # Check if it's marked as OS native
                metadata = software_entry.metadata or {}
                if isinstance(metadata, dict) and metadata.get('os_native', False):
                    if self.is_graviton_compatible_os(detected_os):
                        return ComponentCategory.SYSTEM_COMPATIBLE
                    else:
                        return ComponentCategory.SYSTEM_UNKNOWN
        
        # Fallback to pattern-based detection
        if detected_os:
            is_system = self.is_system_package_by_os(component, detected_os, os_knowledge_base)
            if is_system:
                if self.is_graviton_compatible_os(detected_os):
                    return ComponentCategory.SYSTEM_COMPATIBLE
                else:
                    return ComponentCategory.SYSTEM_UNKNOWN
        else:
            # No OS detected, check general system package patterns
            if self.is_system_package(component) or self.is_os_kernel_component(component):
                return ComponentCategory.SYSTEM_UNKNOWN
        
        # Default to application package
        return ComponentCategory.APPLICATION
    
    def get_os_package_types(self, os_name: str) -> List[str]:
        """
        Get supported package types for specific OS.
        
        Args:
            os_name: Operating system name
            
        Returns:
            List of supported package types
        """
        os_info = self.os_config_manager.get_os_info(os_name)
        if os_info:
            return os_info.get("package_types", [])
        return []


class OSKernelDetector:
    """Intelligent detection of OS and kernel-specific components with configurable patterns."""
    
    def __init__(self, custom_patterns: Optional[Dict[str, List[str]]] = None, config: Optional[FilterConfig] = None, os_config_manager=None):
        """
        Initialize with detection patterns.
        
        Args:
            custom_patterns: Optional dict with custom patterns for different component types.
                           Keys: 'kernel', 'system_library', 'os_utility'
            config: Optional FilterConfig instance for loading patterns from configuration files.
            os_config_manager: Optional OSConfigManager for loading patterns from OS compatibility JSON.
        """
        # Initialize OS config manager
        if os_config_manager is None:
            self.os_config_manager = OSConfigManager()
        else:
            self.os_config_manager = os_config_manager
        
        # Load patterns from OS compatibility JSON
        detection_rules = self.os_config_manager.get_all_detection_rules()
        system_patterns = detection_rules.get("system_package_patterns", {})
        
        # Load patterns from config file if provided, otherwise use patterns from JSON
        if config:
            self.kernel_patterns = config.get_patterns('kernel')
            self.system_library_patterns = config.get_patterns('system_library')
            self.os_utility_patterns = config.get_patterns('os_utility')
            self.system_package_name_patterns = config.get_patterns('system_package_names') if hasattr(config, 'get_patterns') else []
        else:
            self.kernel_patterns = system_patterns.get("kernel", [])
            self.system_library_patterns = system_patterns.get("system_library", [])
            self.os_utility_patterns = system_patterns.get("os_utility", [])
            self.system_package_name_patterns = system_patterns.get("system_package_names", [])
        
        self.kernel_module_types = [
            "linux-kernel-module",
            "kernel-module",
            "driver"
        ]
        
        # Apply custom patterns if provided
        if custom_patterns:
            if 'kernel' in custom_patterns:
                self.kernel_patterns.extend(custom_patterns['kernel'])
            if 'system_library' in custom_patterns:
                self.system_library_patterns.extend(custom_patterns['system_library'])
            if 'os_utility' in custom_patterns:
                self.os_utility_patterns.extend(custom_patterns['os_utility'])
    
    def is_os_kernel_component(self, component_name: str, component_type: str, properties: Optional[Dict] = None) -> bool:
        """
        Check if a component is OS or kernel related.
        
        Args:
            component_name: Name of the component
            component_type: Type of the component
            properties: Optional component properties dict
            
        Returns:
            True if component is OS/kernel related, False otherwise
        """
        return (
            self.is_kernel_module(component_name, component_type, properties) or
            self.is_system_library(component_name) or
            self.is_os_utility(component_name)
        )
    
    def is_kernel_module(self, component_name: str, component_type: str, properties: Optional[Dict] = None) -> bool:
        """
        Check if a component is a kernel module.
        
        Args:
            component_name: Name of the component
            component_type: Type of the component
            properties: Optional component properties dict
            
        Returns:
            True if component is a kernel module, False otherwise
        """
        # Check component type first
        if component_type.lower() in [t.lower() for t in self.kernel_module_types]:
            return True
        
        # Check properties for syft:package:type (CycloneDX SBOMs)
        if properties:
            syft_package_type = properties.get("syft:package:type", "")
            if syft_package_type.lower() in [t.lower() for t in self.kernel_module_types]:
                return True
        
        # Check name patterns
        return self.is_kernel_module_by_name(component_name)
    
    def is_kernel_module_by_name(self, component_name: str) -> bool:
        """
        Check if a component is a kernel module based on name patterns only.
        
        Args:
            component_name: Name of the component
            
        Returns:
            True if component name matches kernel module patterns
        """
        for pattern in self.kernel_patterns:
            if re.match(pattern, component_name, re.IGNORECASE):
                return True
        return False
    
    def is_system_library(self, component_name: str) -> bool:
        """
        Check if a component is a system library.
        
        Args:
            component_name: Name of the component
            
        Returns:
            True if component is a system library, False otherwise
        """
        for pattern in self.system_library_patterns:
            if re.match(pattern, component_name, re.IGNORECASE):
                return True
        
        return False
    
    def is_os_utility(self, component_name: str) -> bool:
        """
        Check if a component is an OS utility.
        
        Args:
            component_name: Name of the component
            
        Returns:
            True if component is an OS utility, False otherwise
        """
        for pattern in self.os_utility_patterns:
            if re.match(pattern, component_name, re.IGNORECASE):
                return True
        
        return False
    
    def add_custom_patterns(self, pattern_type: str, patterns: List[str]) -> None:
        """
        Add custom detection patterns.
        
        Args:
            pattern_type: Type of patterns ('kernel', 'system_library', 'os_utility')
            patterns: List of regex patterns to add
        """
        if pattern_type == 'kernel':
            self.kernel_patterns.extend(patterns)
        elif pattern_type == 'system_library':
            self.system_library_patterns.extend(patterns)
        elif pattern_type == 'os_utility':
            self.os_utility_patterns.extend(patterns)
        else:
            raise ValueError(f"Unknown pattern type: {pattern_type}")
    
    def load_patterns_from_config(self, config_file: str) -> None:
        """
        Load additional patterns from a configuration file.
        
        Args:
            config_file: Path to configuration file
        """
        config = FilterConfig(config_file)
        
        # Extend existing patterns with those from config
        self.kernel_patterns.extend(config.get_patterns('kernel'))
        self.system_library_patterns.extend(config.get_patterns('system_library'))
        self.os_utility_patterns.extend(config.get_patterns('os_utility'))


def filter_system_packages(components: List[SoftwareComponent], detected_os: Optional[str] = None, os_knowledge_base=None) -> Tuple[List[SoftwareComponent], List[SoftwareComponent]]:
    """
    Utility function to separate system packages from application packages.
    
    Args:
        components: List of SoftwareComponent objects
        detected_os: Optional detected OS name
        os_knowledge_base: Optional OS-specific knowledge base
        
    Returns:
        Tuple of (application_components, system_components)
    """
    component_filter = ComponentFilter()
    application_components = []
    system_components = []
    
    for component in components:
        component_dict = {
            "name": component.name,
            "version": component.version,
            "type": component.component_type,
            "properties": component.properties
        }
        
        category = component_filter.categorize_component(component_dict, detected_os, os_knowledge_base)
        
        if category in [ComponentCategory.SYSTEM_COMPATIBLE, ComponentCategory.SYSTEM_UNKNOWN, ComponentCategory.KERNEL_MODULE]:
            system_components.append(component)
        else:
            application_components.append(component)
    
    return application_components, system_components