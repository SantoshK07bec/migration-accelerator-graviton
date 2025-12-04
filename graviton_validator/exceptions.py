"""
Custom exceptions for the Graviton Compatibility Validator.
"""


class GravitonValidatorError(Exception):
    """Base exception class for all Graviton Validator errors."""
    pass


class SBOMParseError(GravitonValidatorError):
    """Raised when SBOM parsing fails."""
    
    def __init__(self, message: str, file_path: str = None, line_number: int = None):
        self.file_path = file_path
        self.line_number = line_number
        
        if file_path:
            message = f"Error parsing SBOM file '{file_path}': {message}"
            if line_number:
                message += f" (line {line_number})"
        
        super().__init__(message)


class KnowledgeBaseError(GravitonValidatorError):
    """Raised when knowledge base operations fail."""
    
    def __init__(self, message: str, file_path: str = None):
        self.file_path = file_path
        
        if file_path:
            message = f"Knowledge base error in '{file_path}': {message}"
        
        super().__init__(message)


class VersionComparisonError(GravitonValidatorError):
    """Raised when version comparison fails."""
    
    def __init__(self, message: str, version1: str = None, version2: str = None):
        self.version1 = version1
        self.version2 = version2
        
        if version1 and version2:
            message = f"Version comparison error between '{version1}' and '{version2}': {message}"
        elif version1:
            message = f"Version error with '{version1}': {message}"
        
        super().__init__(message)


class ConfigurationError(GravitonValidatorError):
    """Raised when configuration is invalid."""
    pass


class ReportGenerationError(GravitonValidatorError):
    """Raised when report generation fails."""
    
    def __init__(self, message: str, format_name: str = None, output_path: str = None):
        self.format_name = format_name
        self.output_path = output_path
        
        if format_name:
            message = f"Report generation error for format '{format_name}': {message}"
            if output_path:
                message += f" (output: {output_path})"
        
        super().__init__(message)