"""
Reporting Module

Contains report generators for different output formats (JSON, Markdown, Excel, text).
"""

from .base import ReportGenerator
from .json_reporter import JSONReporter

__all__ = ['ReportGenerator', 'JSONReporter']