"""
Base interface for runtime-specific compatibility analyzers.

This module provides the abstract base class that all runtime analyzers
(Java, Python, NodeJS, etc.) must implement for consistent integration
with the migration-accelerator-graviton framework.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from ..models import SoftwareComponent, ComponentResult


class RuntimeCompatibilityAnalyzer(ABC):
    """Base interface for all runtime-specific compatibility analyzers."""
    
    @abstractmethod
    def analyze_component(self, component: SoftwareComponent) -> ComponentResult:
        """
        Analyze a component for runtime-specific compatibility issues.
        
        Args:
            component: SoftwareComponent to analyze
            
        Returns:
            ComponentResult with compatibility analysis
        """
        pass
    
    @abstractmethod
    def get_runtime_type(self) -> str:
        """
        Return the runtime type this analyzer handles.
        
        Returns:
            Runtime type string (e.g., 'java', 'python', 'nodejs')
        """
        pass
    
    @abstractmethod
    def get_supported_purls(self) -> List[str]:
        """
        Return list of PURL prefixes this analyzer supports.
        
        Returns:
            List of PURL prefixes (e.g., ['pkg:maven/', 'pkg:pypi/'])
        """
        pass
    
    def is_applicable(self, component: SoftwareComponent) -> bool:
        """
        Check if this analyzer can handle the given component.
        
        Args:
            component: SoftwareComponent to check
            
        Returns:
            True if this analyzer can handle the component
        """
        if not hasattr(component, 'properties') or not component.properties:
            return False
        
        purl = component.properties.get('purl', '')
        if not purl:
            return False
        
        return any(purl.startswith(prefix) for prefix in self.get_supported_purls())