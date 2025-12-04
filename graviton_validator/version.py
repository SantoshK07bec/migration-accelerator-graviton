"""
Version management for Graviton Compatibility Validator.

This module provides centralized version information to avoid hardcoding
version numbers throughout the codebase.
"""

from . import __version__


def get_version() -> str:
    """
    Get the current version of the Graviton Compatibility Validator.
    
    Returns:
        Version string (e.g., "0.0.1")
    """
    return __version__


def get_version_info() -> dict:
    """
    Get detailed version information.
    
    Returns:
        Dictionary with version details
    """
    version_parts = __version__.split('.')
    
    return {
        "version": __version__,
        "major": int(version_parts[0]) if len(version_parts) > 0 else 0,
        "minor": int(version_parts[1]) if len(version_parts) > 1 else 0,
        "patch": int(version_parts[2]) if len(version_parts) > 2 else 0,
        "is_alpha": __version__.startswith("0.0."),
        "is_beta": __version__.startswith("0.") and not __version__.startswith("0.0."),
        "is_stable": not __version__.startswith("0.")
    }


def get_full_name_with_version() -> str:
    """
    Get the full tool name with version.
    
    Returns:
        Full name string (e.g., "Graviton Compatibility Validator v0.0.1")
    """
    return f"Graviton Compatibility Validator v{__version__}"