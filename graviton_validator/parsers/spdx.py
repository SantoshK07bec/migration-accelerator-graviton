"""
SPDX SBOM parser implementation with OS detection capabilities.
"""

from typing import Dict, List, Optional, Tuple

from .base import SBOMParser
from ..models import SoftwareComponent
from ..os_detection.os_configs import OSConfigManager


class SPDXParser(SBOMParser):
    """Parser for SPDX format SBOMs with OS detection capabilities."""
    
    def __init__(self, os_config_manager: Optional[OSConfigManager] = None):
        """Initialize SPDX parser with OS detection capabilities."""
        super().__init__()
        self.os_config_manager = os_config_manager or OSConfigManager()
    
    def _get_supported_formats(self) -> List[str]:
        """Get list of supported SBOM formats for this parser."""
        return ["SPDX"]
    
    def is_supported_format(self, sbom_data: dict) -> bool:
        """
        Check if the SBOM data is in SPDX format.
        
        Args:
            sbom_data: Parsed JSON data from SBOM file
            
        Returns:
            True if format is SPDX, False otherwise
        """
        # Check for SPDX version marker
        if "spdxVersion" in sbom_data:
            return True
        
        # Check for SPDX ID marker
        if "SPDXID" in sbom_data:
            return True
        
        # Check for SPDX structure (packages or documentNamespace)
        if "packages" in sbom_data or "documentNamespace" in sbom_data:
            return True
        
        return False
    
    def _parse_components(self, sbom_data: dict, source_file: str) -> List[SoftwareComponent]:
        """
        Parse components from SPDX SBOM data with OS detection.
        
        Args:
            sbom_data: Parsed JSON data from SBOM file
            source_file: Path to the source SBOM file
            
        Returns:
            List of SoftwareComponent objects
        """
        components = []
        
        # Detect OS from SBOM metadata
        detected_os = self.os_config_manager.detect_os_from_sbom_data(sbom_data)
        
        # Parse packages from the packages array
        for package_data in sbom_data.get("packages", []):
            component = self._parse_single_package(package_data, source_file, detected_os)
            if component:
                components.append(component)
        
        return components
    
    def _parse_single_package(self, package_data: dict, source_file: str, detected_os: Optional[str] = None) -> Optional[SoftwareComponent]:
        """
        Parse a single package from SPDX data.
        
        Args:
            package_data: Package data from SBOM
            source_file: Path to the source SBOM file
            
        Returns:
            SoftwareComponent object or None if parsing fails
        """
        try:
            name = package_data.get("name")
            if not name:
                return None
            
            # Skip the document package (root package)
            if name == "." or package_data.get("SPDXID") == "SPDXRef-DOCUMENT":
                return None
            
            version = self._extract_version(package_data.get("versionInfo"))
            
            # Determine component type from available information
            component_type = "library"  # Default
            
            # Try to infer type from download location or other fields
            download_location = package_data.get("downloadLocation", "")
            if "github.com" in download_location or "gitlab.com" in download_location:
                component_type = "application"
            
            # Extract properties
            properties = {}
            
            # Add SPDX ID
            if "SPDXID" in package_data:
                properties["spdx_id"] = package_data["SPDXID"]
            
            # Add download location
            if download_location and download_location != "NOASSERTION":
                properties["download_location"] = download_location
            
            # Add homepage
            if "homepage" in package_data and package_data["homepage"] != "NOASSERTION":
                properties["homepage"] = package_data["homepage"]
            
            # Add supplier
            if "supplier" in package_data and package_data["supplier"] != "NOASSERTION":
                properties["supplier"] = package_data["supplier"]
            
            # Add originator
            if "originator" in package_data and package_data["originator"] != "NOASSERTION":
                properties["originator"] = package_data["originator"]
            
            # Add copyright text
            if "copyrightText" in package_data and package_data["copyrightText"] != "NOASSERTION":
                properties["copyright"] = package_data["copyrightText"]
            
            # Add license information
            licenses = []
            if "licenseConcluded" in package_data and package_data["licenseConcluded"] != "NOASSERTION":
                licenses.append(package_data["licenseConcluded"])
            if "licenseDeclared" in package_data and package_data["licenseDeclared"] != "NOASSERTION":
                licenses.append(package_data["licenseDeclared"])
            
            if licenses:
                properties["licenses"] = ",".join(set(licenses))  # Remove duplicates
            
            # Add description/summary
            if "description" in package_data:
                properties["description"] = package_data["description"]
            elif "summary" in package_data:
                properties["description"] = package_data["summary"]
            
            # Add external references
            external_refs = package_data.get("externalRefs", [])
            for ref in external_refs:
                ref_type = ref.get("referenceType", "")
                ref_locator = ref.get("referenceLocator", "")
                if ref_type and ref_locator:
                    properties[f"external_ref_{ref_type.lower()}"] = ref_locator
            
            component = SoftwareComponent(
                name=name,
                version=version,
                component_type=component_type,
                source_sbom=source_file,
                properties=properties
            )
            
            # Enhance component with OS-specific information
            if detected_os:
                component = self._enhance_component_with_os_info(component, package_data, detected_os)
            
            return component
        
        except Exception:
            # Skip packages that can't be parsed
            return None
    

    
    def _enhance_component_with_os_info(self, component: SoftwareComponent, package_data: dict, detected_os: Optional[str]) -> SoftwareComponent:
        """
        Enhance component with OS-specific information.
        
        Args:
            component: Base SoftwareComponent
            package_data: Original package data from SBOM
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
        
        # Check vendor patterns
        supplier = package_data.get("supplier", "")
        originator = package_data.get("originator", "")
        
        for vendor_text in [supplier, originator]:
            if vendor_text and vendor_text != "NOASSERTION":
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
            sbom_data: Parsed SPDX SBOM data
            
        Returns:
            Detected OS name or None
        """
        return self.os_config_manager.detect_os_from_sbom_data(sbom_data)
    
    def parse_with_os_detection(self, sbom_data: dict, source_file: str) -> Tuple[List[SoftwareComponent], Optional[str]]:
        """
        Parse SBOM with OS detection, returning both components and detected OS.
        
        Args:
            sbom_data: Parsed SPDX SBOM data
            source_file: Path to source SBOM file
            
        Returns:
            Tuple of (components, detected_os)
        """
        detected_os = self.os_config_manager.detect_os_from_sbom_data(sbom_data)
        components = self._parse_components(sbom_data, source_file)
        return components, detected_os