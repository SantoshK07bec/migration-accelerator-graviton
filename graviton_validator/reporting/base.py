"""
Abstract base classes for report generation.
"""

from abc import ABC, abstractmethod
from typing import Optional

from ..models import AnalysisResult


class ReportGenerator(ABC):
    """Abstract base class for report generators."""
    
    @abstractmethod
    def generate_report(self, analysis_result: AnalysisResult, output_path: Optional[str] = None) -> str:
        """
        Generate a report from analysis results.
        
        Args:
            analysis_result: AnalysisResult to generate report from
            output_path: Optional path to write report to file
            
        Returns:
            Report content as string
        """
        pass
    
    @abstractmethod
    def get_format_name(self) -> str:
        """
        Get the name of the report format.
        
        Returns:
            String identifier for the report format (e.g., "json", "markdown")
        """
        pass