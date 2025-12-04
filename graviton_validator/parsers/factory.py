"""
SBOM Parser Factory

Automatically detects SBOM format and returns the appropriate parser.
"""

import json
import os
from typing import List, Optional

from .base import SBOMParser
from .cyclonedx import CycloneDXParser
from .spdx import SPDXParser
from .syft import SyftParser
from ..exceptions import SBOMParseError
from ..models import SoftwareComponent


class SBOMParserFactory:
    """Factory class for creating appropriate SBOM parsers."""
    
    def __init__(self):
        """Initialize the factory with available parsers."""
        self.parsers = [
            CycloneDXParser(),
            SPDXParser(),
            SyftParser()
        ]
    
    def get_parser(self, file_path: str) -> SBOMParser:
        """
        Get the appropriate parser for an SBOM file.
        
        Args:
            file_path: Path to the SBOM file
            
        Returns:
            SBOMParser instance that can handle the file format
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            SBOMParseError: If no suitable parser is found
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
        
        # Try each parser to see which one supports the format
        for parser in self.parsers:
            if parser.is_supported_format(sbom_data):
                return parser
        
        # If no parser supports the format, raise an error
        detected_format = SBOMParser.detect_sbom_format(sbom_data)
        supported_formats = []
        for parser in self.parsers:
            supported_formats.extend(parser.supported_formats)
        
        raise SBOMParseError(
            f"No suitable parser found for SBOM file {file_path}. "
            f"Detected format: {detected_format}, "
            f"Supported formats: {', '.join(set(supported_formats))}"
        )
    
    def parse_file(self, file_path: str) -> List[SoftwareComponent]:
        """
        Parse an SBOM file using the appropriate parser.
        
        Args:
            file_path: Path to the SBOM file
            
        Returns:
            List of SoftwareComponent objects
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            SBOMParseError: If parsing fails
        """
        parser = self.get_parser(file_path)
        return parser.parse(file_path)
    
    def get_supported_formats(self) -> List[str]:
        """
        Get list of all supported SBOM formats.
        
        Returns:
            List of supported format names
        """
        formats = []
        for parser in self.parsers:
            formats.extend(parser.supported_formats)
        return list(set(formats))  # Remove duplicates
    
    def detect_format(self, file_path: str) -> str:
        """
        Detect the format of an SBOM file without parsing it.
        
        Args:
            file_path: Path to the SBOM file
            
        Returns:
            String identifier for the detected format
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            SBOMParseError: If the file can't be read
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
        
        return SBOMParser.detect_sbom_format(sbom_data)