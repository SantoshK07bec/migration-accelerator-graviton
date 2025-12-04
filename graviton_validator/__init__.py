"""
Graviton Compatibility Validator

A Python tool for analyzing Software Bill of Materials (SBOM) files to determine
compatibility with AWS Graviton processors.
"""

__version__ = "0.0.4"
__author__ = "Graviton Compatibility Team"

# Make version easily importable
def get_version():
    """Get the current version of the Graviton Compatibility Validator."""
    return __version__

__all__ = ['get_version']