"""
Abstract base classes for SBOM parsers.
"""

import json
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from ..models import SoftwareComponent
from ..exceptions import SBOMParseError


class SBOMParser(ABC):
    """Abstract base class for SBOM parsers."""
    
    def __init__(self):
        """Initialize the parser."""
        self.supported_formats = self._get_supported_formats()
    
    @abstractmethod
    def _get_supported_formats(self) -> List[str]:
        """
        Get list of supported SBOM formats for this parser.
        
        Returns:
            List of format identifiers (e.g., ["CycloneDX", "Syft"])
        """
        pass
    
    def parse(self, file_path: str) -> List[SoftwareComponent]:
        """
        Parse an SBOM file and extract software components.
        
        Args:
            file_path: Path to the SBOM file
            
        Returns:
            List of SoftwareComponent objects
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            SBOMParseError: If the file format is invalid or parsing fails
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"SBOM file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                sbom_data = json.load(f)
        except json.JSONDecodeError as e:
            raise SBOMParseError(f"Invalid JSON in SBOM file {file_path}: {e}")
        except Exception as e:
            raise SBOMParseError(f"Error reading SBOM file {file_path}: {e}")
        
        if not self.is_supported_format(sbom_data):
            detected_format = self.detect_sbom_format(sbom_data)
            raise SBOMParseError(
                f"Unsupported SBOM format in {file_path}. "
                f"Detected: {detected_format}, Supported: {self.supported_formats}"
            )
        
        return self._parse_components(sbom_data, file_path)
    
    @abstractmethod
    def _parse_components(self, sbom_data: dict, source_file: str) -> List[SoftwareComponent]:
        """
        Parse components from SBOM data.
        
        Args:
            sbom_data: Parsed JSON data from SBOM file
            source_file: Path to the source SBOM file
            
        Returns:
            List of SoftwareComponent objects
        """
        pass
    
    @abstractmethod
    def is_supported_format(self, sbom_data: dict) -> bool:
        """
        Check if the SBOM data is in a supported format.
        
        Args:
            sbom_data: Parsed JSON data from SBOM file
            
        Returns:
            True if format is supported, False otherwise
        """
        pass
    
    @staticmethod
    def detect_sbom_format(sbom_data: dict) -> str:
        """
        Detect the SBOM format from parsed data.
        
        Args:
            sbom_data: Parsed JSON data from SBOM file
            
        Returns:
            String identifier for the SBOM format
        """
        if not isinstance(sbom_data, dict):
            return "unknown"
        
        # Check for CycloneDX format
        if "bomFormat" in sbom_data and sbom_data.get("bomFormat") == "CycloneDX":
            return "CycloneDX"
        
        # Check for SPDX format
        if "spdxVersion" in sbom_data or "SPDXID" in sbom_data:
            return "SPDX"
        
        # Check for Syft format (app_identifier.sh generated)
        if "artifacts" in sbom_data and isinstance(sbom_data["artifacts"], list):
            return "Syft"
        
        # Check for other CycloneDX indicators
        if "components" in sbom_data and "metadata" in sbom_data:
            return "CycloneDX"
        
        # Check for other SPDX indicators
        if "packages" in sbom_data or "documentNamespace" in sbom_data:
            return "SPDX"
        
        return "unknown"
    
    def _extract_version(self, version_str: Optional[str]) -> Optional[str]:
        """
        Extract and normalize version information.
        
        Args:
            version_str: Raw version string
            
        Returns:
            Normalized version string or None if invalid/missing
        """
        if not version_str or version_str.strip() == "":
            return None
        
        # Clean up common version string issues
        version = version_str.strip()
        
        # Remove common prefixes
        if version.startswith("v"):
            version = version[1:]
        
        return version if version else None


# Removed duplicate ComponentFilter and OSKernelDetector classes
# These are now imported from analysis.filters module