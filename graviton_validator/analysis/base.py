"""
Abstract base classes for analysis functionality.
"""

from abc import ABC, abstractmethod
from typing import List

from ..models import AnalysisResult, ComponentResult, SoftwareComponent


class CompatibilityAnalyzer(ABC):
    """Abstract base class for compatibility analysis."""
    
    @abstractmethod
    def analyze_components(self, components: List[SoftwareComponent]) -> AnalysisResult:
        """
        Analyze a list of software components for Graviton compatibility.
        
        Args:
            components: List of SoftwareComponent objects to analyze
            
        Returns:
            AnalysisResult containing the complete analysis
        """
        pass
    
    @abstractmethod
    def check_single_component(self, component: SoftwareComponent) -> ComponentResult:
        """
        Check compatibility for a single software component.
        
        Args:
            component: SoftwareComponent to analyze
            
        Returns:
            ComponentResult containing the analysis for this component
        """
        pass


class RecommendationGenerator(ABC):
    """Abstract base class for generating upgrade recommendations."""
    
    @abstractmethod
    def generate_recommendations(self, component_result: ComponentResult) -> ComponentResult:
        """
        Generate upgrade recommendations for a component analysis result.
        
        Args:
            component_result: ComponentResult to generate recommendations for
            
        Returns:
            Updated ComponentResult with recommendations
        """
        pass