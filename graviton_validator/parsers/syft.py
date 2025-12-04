"""
Syft SBOM parser implementation for app_identifier.sh generated SBOMs.
"""

from typing import Dict, List, Optional, TYPE_CHECKING

from .base import SBOMParser
from ..models import SoftwareComponent

if TYPE_CHECKING:
    from ..os_detection.os_configs import OSConfigManager


class SyftParser(SBOMParser):
    """Parser for Syft format SBOMs (app_identifier.sh generated)."""
    
    def __init__(self, os_config_manager=None):
        """Initialize the Syft parser with OS detector."""
        super().__init__()
        from ..os_detection.os_configs import OSConfigManager
        self.os_config_manager = os_config_manager or OSConfigManager()
    
    def _get_supported_formats(self) -> List[str]:
        """Get list of supported SBOM formats for this parser."""
        return ["Syft"]
    
    def is_supported_format(self, sbom_data: dict) -> bool:
        """
        Check if the SBOM data is in Syft format.
        
        Args:
            sbom_data: Parsed JSON data from SBOM file
            
        Returns:
            True if format is Syft, False otherwise
        """
        # Check for Syft structure (artifacts array)
        if "artifacts" in sbom_data and isinstance(sbom_data["artifacts"], list):
            return True
        
        return False
    
    def _parse_components(self, sbom_data: dict, source_file: str) -> List[SoftwareComponent]:
        """
        Parse components from Syft SBOM data.
        
        Args:
            sbom_data: Parsed JSON data from SBOM file
            source_file: Path to the source SBOM file
            
        Returns:
            List of SoftwareComponent objects
        """
        components = []
        
        # Parse artifacts from the artifacts array
        for artifact_data in sbom_data.get("artifacts", []):
            component = self._parse_single_artifact(artifact_data, source_file)
            if component:
                components.append(component)
        
        return components
    
    def _parse_single_artifact(self, artifact_data: dict, source_file: str) -> Optional[SoftwareComponent]:
        """
        Parse a single artifact from Syft data.
        
        Args:
            artifact_data: Artifact data from SBOM
            source_file: Path to the source SBOM file
            
        Returns:
            SoftwareComponent object or None if parsing fails
        """
        try:
            name = artifact_data.get("name")
            if not name:
                return None
            
            version = self._extract_version(artifact_data.get("version"))
            component_type = artifact_data.get("type", "unknown")
            
            # Extract properties
            properties = {}
            
            # Add PURL if available
            if "purl" in artifact_data:
                properties["purl"] = artifact_data["purl"]
            
            # Add language if available
            if "language" in artifact_data and artifact_data["language"]:
                properties["language"] = artifact_data["language"]
            
            # Add foundBy (cataloger information)
            if "foundBy" in artifact_data:
                properties["found_by"] = artifact_data["foundBy"]
            
            # Add licenses if available
            if "licenses" in artifact_data:
                licenses = []
                for license_info in artifact_data["licenses"]:
                    if "value" in license_info:
                        licenses.append(license_info["value"])
                    elif "spdxExpression" in license_info and license_info["spdxExpression"]:
                        licenses.append(license_info["spdxExpression"])
                if licenses:
                    properties["licenses"] = ",".join(licenses)
            
            # Add metadata if available
            metadata = artifact_data.get("metadata", {})
            if isinstance(metadata, dict):
                # Add specific metadata fields
                for key in ["author", "authorEmail", "description", "homepage", "platform"]:
                    if key in metadata and metadata[key]:
                        properties[key] = metadata[key]
                
                # For kernel modules, add kernel-specific info
                if component_type == "linux-kernel-module":
                    for key in ["kernelVersion", "versionMagic", "sourceVersion"]:
                        if key in metadata and metadata[key]:
                            properties[key] = metadata[key]
                
                # For Python packages, add Python-specific info
                if component_type == "python":
                    if "sitePackagesRootPath" in metadata:
                        properties["site_packages_path"] = metadata["sitePackagesRootPath"]
                
                # For RPM packages, add RPM-specific info
                if component_type == "rpm":
                    for key in ["architecture", "release", "sourceRpm", "vendor"]:
                        if key in metadata and metadata[key]:
                            properties[key] = metadata[key]
            
            # Add locations if available
            locations = artifact_data.get("locations", [])
            if locations:
                paths = [loc.get("path", "") for loc in locations if loc.get("path")]
                if paths:
                    properties["locations"] = ",".join(paths[:3])  # Limit to first 3 paths
            
            # Add CPEs if available
            cpes = artifact_data.get("cpes", [])
            if cpes:
                cpe_values = [cpe.get("cpe", "") for cpe in cpes if cpe.get("cpe")]
                if cpe_values:
                    properties["cpes"] = ",".join(cpe_values[:2])  # Limit to first 2 CPEs
            
            return SoftwareComponent(
                name=name,
                version=version,
                component_type=component_type,
                source_sbom=source_file,
                properties=properties
            )
        
        except Exception:
            # Skip artifacts that can't be parsed
            return None
    
    def get_detected_os(self, sbom_data: dict) -> Optional[str]:
        """
        Detect operating system from Syft SBOM data.
        
        Args:
            sbom_data: Parsed JSON data from SBOM file
            
        Returns:
            Detected OS name or None if not detected
        """
        return self.os_config_manager.detect_os_from_sbom_data(sbom_data)