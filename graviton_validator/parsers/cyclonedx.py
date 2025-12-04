"""
CycloneDX SBOM parser implementation with OS detection capabilities.
"""

from typing import Dict, List, Optional, Tuple

from .base import SBOMParser
from ..models import SoftwareComponent
from ..os_detection.os_configs import OSConfigManager


class CycloneDXParser(SBOMParser):
    """Parser for CycloneDX format SBOMs with OS detection capabilities."""
    
    def __init__(self, os_config_manager: Optional[OSConfigManager] = None):
        """Initialize CycloneDX parser with OS detection capabilities."""
        super().__init__()
        self.os_config_manager = os_config_manager or OSConfigManager()
    
    def _get_supported_formats(self) -> List[str]:
        """Get list of supported SBOM formats for this parser."""
        return ["CycloneDX"]
    
    def is_supported_format(self, sbom_data: dict) -> bool:
        """
        Check if the SBOM data is in CycloneDX format.
        
        Args:
            sbom_data: Parsed JSON data from SBOM file
            
        Returns:
            True if format is CycloneDX, False otherwise
        """
        # Check for explicit CycloneDX format marker
        if sbom_data.get("bomFormat") == "CycloneDX":
            return True
        
        # Check for CycloneDX structure (components + metadata)
        if "components" in sbom_data and "metadata" in sbom_data:
            return True
        
        return False
    
    def _parse_components(self, sbom_data: dict, source_file: str) -> List[SoftwareComponent]:
        """
        Parse components from CycloneDX SBOM data with hierarchical support.
        
        Args:
            sbom_data: Parsed JSON data from SBOM file
            source_file: Path to the source SBOM file
            
        Returns:
            List of SoftwareComponent objects with hierarchical relationships
        """
        components = []
        
        # Detect OS from SBOM metadata
        detected_os = self.os_config_manager.detect_os_from_sbom_data(sbom_data)
        
        # Parse components hierarchically
        for component_data in sbom_data.get("components", []):
            parsed_components = self._parse_component_hierarchy(component_data, source_file, detected_os)
            components.extend(parsed_components)
        
        return components
    
    def _parse_component_hierarchy(self, component_data: dict, source_file: str, detected_os: Optional[str] = None, parent_name: Optional[str] = None) -> List[SoftwareComponent]:
        """
        Parse a component and its children hierarchically.
        
        Args:
            component_data: Component data from SBOM
            source_file: Path to the source SBOM file
            detected_os: Detected OS name
            parent_name: Name of parent component (for child components)
            
        Returns:
            List of SoftwareComponent objects (parent + children)
        """
        components = []
        
        # Parse the main component
        main_component = self._parse_single_component(component_data, source_file, detected_os, parent_name)
        if not main_component:
            return components
        
        components.append(main_component)
        
        # Parse child components if they exist
        child_components_data = component_data.get("components", [])
        if child_components_data:
            for child_data in child_components_data:
                child_components = self._parse_component_hierarchy(
                    child_data, source_file, detected_os, main_component.name
                )
                components.extend(child_components)
                
                # Add child names to parent's child_components list
                for child_comp in child_components:
                    if child_comp.name not in main_component.child_components:
                        main_component.child_components.append(child_comp.name)
        
        return components
    
    def _parse_single_component(self, component_data: dict, source_file: str, detected_os: Optional[str] = None, parent_name: Optional[str] = None) -> Optional[SoftwareComponent]:
        """
        Parse a single component from CycloneDX data.
        
        Args:
            component_data: Component data from SBOM
            source_file: Path to the source SBOM file
            detected_os: Detected OS name
            parent_name: Name of parent component (for child components)
            
        Returns:
            SoftwareComponent object or None if parsing fails
        """
        try:
            name = component_data.get("name")
            if not name:
                return None
            
            # Extract version from direct field or properties
            version = component_data.get("version")
            if not version:
                # Check properties for unresolved_version (CycloneDX spec: properties is always a list)
                properties_list = component_data.get("properties", [])
                for prop in properties_list:
                    if isinstance(prop, dict) and "unresolved_version" in prop.get("name", ""):
                        version = prop.get("value")
                        break
            
            version = self._extract_version(version)
            component_type = component_data.get("type", "library")
            
            # Extract properties
            properties = {}
            
            # Extract properties (important for kernel modules and system packages)
            if "properties" in component_data:
                # CycloneDX spec: properties is always a list of {name, value} objects
                for prop in component_data["properties"]:
                    if isinstance(prop, dict) and "name" in prop and "value" in prop:
                        prop_name = prop["name"]
                        prop_value = prop["value"]
                        properties[prop_name] = prop_value
                        
                        # Special handling for package type - look for 'package:type' in the name
                        if "package:type" in prop_name:
                            properties["package:type"] = prop_value
            
            # For CycloneDX, use package:type from properties if available for better reporting
            for prop_name, prop_value in properties.items():
                if "package:type" in prop_name and prop_value:
                    component_type = prop_value
                    break
            
            # Add PURL if available
            if "purl" in component_data:
                properties["purl"] = component_data["purl"]
            
            # Add licenses if available
            if "licenses" in component_data:
                licenses = []
                for license_info in component_data["licenses"]:
                    if "license" in license_info:
                        license_data = license_info["license"]
                        if "name" in license_data:
                            licenses.append(license_data["name"])
                        elif "id" in license_data:
                            licenses.append(license_data["id"])
                if licenses:
                    properties["licenses"] = ",".join(licenses)
            
            # Add publisher/supplier if available
            if "publisher" in component_data:
                properties["publisher"] = component_data["publisher"]
            elif "supplier" in component_data and "name" in component_data["supplier"]:
                properties["supplier"] = component_data["supplier"]["name"]
            
            # Add description if available
            if "description" in component_data:
                properties["description"] = component_data["description"]
            
            # Extract source package from purl for Debian/Ubuntu packages
            source_package = self._extract_source_package_from_purl(properties.get("purl", ""))
            
            component = SoftwareComponent(
                name=name,
                version=version,
                component_type=component_type,
                source_sbom=source_file,
                properties=properties,
                parent_component=parent_name,
                source_package=source_package
            )
            
            # Enhance component with OS-specific information
            if detected_os:
                component = self._enhance_component_with_os_info(component, component_data, detected_os)
            
            return component
        
        except Exception:
            # Skip components that can't be parsed
            return None
    
    def _extract_source_package_from_purl(self, purl: str) -> Optional[str]:
        """
        Extract source package name from purl for Debian/Ubuntu packages.
        
        Args:
            purl: Package URL string
            
        Returns:
            Source package name or None if not found
        """
        if not purl or "source=" not in purl:
            return None
        
        try:
            # Extract source parameter from purl
            # Example: pkg:deb/debian/bsdutils@2.36.1-8%2Bdeb11u1?arch=amd64&distro=bullseye&epoch=0&source=util-linux
            parts = purl.split("source=")
            if len(parts) > 1:
                source_part = parts[1].split("&")[0]  # Get everything before next parameter
                return source_part if source_part else None
        except Exception:
            pass
        
        return None
    

    
    def _enhance_component_with_os_info(self, component: SoftwareComponent, component_data: dict, detected_os: Optional[str]) -> SoftwareComponent:
        """
        Enhance component with OS-specific information.
        
        Args:
            component: Base SoftwareComponent
            component_data: Original component data from SBOM
            detected_os: Detected OS name
            
        Returns:
            Enhanced SoftwareComponent
        """
        if not detected_os:
            return component
        
        # Add OS information to properties
        component.properties["detected_os"] = detected_os
        
        # Check if this is a system package for the detected OS
        os_patterns = self.os_config_manager.get_detection_patterns(detected_os)
        
        # Check version patterns
        if component.version:
            for pattern in os_patterns.get("package_patterns", []):
                if pattern.lower() in component.version.lower():
                    component.properties["os_system_package"] = "true"
                    component.properties["system_package_os"] = detected_os
                    break
        
        # Check PURL for OS-specific information
        purl = component.properties.get("purl", "")
        if purl:
            purl_detected_os = self.os_config_manager.detect_os_from_purl(purl)
            if purl_detected_os == detected_os:
                component.properties["os_system_package"] = "true"
                component.properties["system_package_os"] = detected_os
                component.properties["system_package_source"] = "purl"
        
        # Check component type against OS package types
        os_info = self.os_config_manager.get_os_info(detected_os)
        if os_info and component.component_type in os_info.get("package_types", []):
            component.properties["os_system_package"] = "true"
            component.properties["system_package_os"] = detected_os
            component.properties["system_package_source"] = "component_type"
        
        # Check publisher/supplier patterns
        publisher = component_data.get("publisher", "")
        supplier_info = component_data.get("supplier", {})
        supplier_name = supplier_info.get("name", "") if isinstance(supplier_info, dict) else ""
        
        for vendor_text in [publisher, supplier_name]:
            if vendor_text:
                for vendor_pattern in os_patterns.get("vendor_names", []):
                    if vendor_pattern.lower() in vendor_text.lower():
                        component.properties["os_system_package"] = "true"
                        component.properties["system_package_os"] = detected_os
                        component.properties["system_package_vendor"] = vendor_text
                        break
        
        # Add OS compatibility information
        is_compatible = self.os_config_manager.is_os_graviton_compatible(detected_os)
        component.properties["os_graviton_compatible"] = str(is_compatible).lower()
        
        return component
    
    def get_detected_os(self, sbom_data: dict) -> Optional[str]:
        """
        Public method to get detected OS from SBOM data.
        
        Args:
            sbom_data: Parsed CycloneDX SBOM data
            
        Returns:
            Detected OS name or None
        """
        return self.os_config_manager.detect_os_from_sbom_data(sbom_data)
    
    def parse_with_os_detection(self, sbom_data: dict, source_file: str) -> Tuple[List[SoftwareComponent], Optional[str]]:
        """
        Parse SBOM with OS detection, returning both components and detected OS.
        
        Args:
            sbom_data: Parsed CycloneDX SBOM data
            source_file: Path to source SBOM file
            
        Returns:
            Tuple of (components, detected_os)
        """
        detected_os = self.os_config_manager.detect_os_from_sbom_data(sbom_data)
        components = self._parse_components(sbom_data, source_file)
        return components, detected_os