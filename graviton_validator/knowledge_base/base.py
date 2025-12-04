"""
Abstract base classes for knowledge base functionality.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..models import CompatibilityResult, VersionInfo


class KnowledgeBase(ABC):
    """Abstract base class for knowledge base implementations."""
    
    @abstractmethod
    def load_from_files(self, file_paths: List[str]) -> None:
        """
        Load knowledge base data from files.
        
        Args:
            file_paths: List of paths to knowledge base files
            
        Raises:
            FileNotFoundError: If any file doesn't exist
            ValueError: If file format is invalid
        """
        pass
    
    @abstractmethod
    def get_compatibility(self, software_name: str, version: str) -> CompatibilityResult:
        """
        Get compatibility information for a software component.
        
        Args:
            software_name: Name of the software
            version: Version of the software
            
        Returns:
            CompatibilityResult object
        """
        pass
    
    @abstractmethod
    def find_compatible_versions(self, software_name: str) -> List[VersionInfo]:
        """
        Find all compatible versions for a software component.
        
        Args:
            software_name: Name of the software
            
        Returns:
            List of VersionInfo objects
        """
        pass
    
    @abstractmethod
    def intelligent_match(self, software_name: str) -> List[str]:
        """
        Perform intelligent/fuzzy matching for software names.
        
        Args:
            software_name: Name to match against
            
        Returns:
            List of potential matches from knowledge base
        """
        pass
    
    def get_runtime_dependencies(self, runtime_type: str = None) -> dict:
        """
        Get runtime-specific dependency data from knowledge base.
        
        Args:
            runtime_type: Optional runtime type filter ('java', 'python', 'nodejs')
            
        Returns:
            Dictionary with runtime dependency data
        """
        # Default implementation returns empty dict
        # Concrete implementations should override this
        return {}


class VersionComparator(ABC):
    """Abstract base class for version comparison logic."""
    
    @abstractmethod
    def compare_versions(self, version1: str, version2: str) -> int:
        """
        Compare two version strings.
        
        Args:
            version1: First version string
            version2: Second version string
            
        Returns:
            -1 if version1 < version2, 0 if equal, 1 if version1 > version2
        """
        pass
    
    @abstractmethod
    def version_matches_range(self, version: str, version_range: str) -> bool:
        """
        Check if a version matches a version range specification.
        
        Args:
            version: Version string to check
            version_range: Version range specification (e.g., ">=2.1.0,<3.0.0")
            
        Returns:
            True if version matches range, False otherwise
        """
        pass


class IntelligentMatcher(ABC):
    """Abstract base class for intelligent software name matching."""
    
    @abstractmethod
    def find_best_match(self, query: str, candidates: List[str]) -> Optional[str]:
        """
        Find the best match for a query string from a list of candidates.
        
        Args:
            query: String to match
            candidates: List of candidate strings
            
        Returns:
            Best matching candidate or None if no good match found
        """
        pass
    
    @abstractmethod
    def calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity score between two strings.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        pass