"""
Deny list loader for loading and managing denied packages.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from .models import DenyListEntry

logger = logging.getLogger(__name__)


class DenyListLoader:
    """Loads and manages deny list entries."""
    
    def __init__(self):
        self.deny_entries: Dict[str, DenyListEntry] = {}
        self.aliases: Dict[str, str] = {}  # alias -> canonical name
    
    def load_from_file(self, file_path: str) -> None:
        """
        Load deny list from JSON file.
        
        Args:
            file_path: Path to deny list JSON file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._validate_deny_list(data)
            entries_before = len(self.deny_entries)
            self._load_deny_entries(data)
            entries_added = len(self.deny_entries) - entries_before
            
            logger.info(f"Loaded {entries_added} deny list entries from {file_path}")
            
        except FileNotFoundError:
            logger.warning(f"Deny list file not found: {file_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in deny list file {file_path}: {e}")
            raise ValueError(f"Invalid JSON format in {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error loading deny list from {file_path}: {e}")
            raise
    
    def load_from_multiple_files(self, file_paths: List[str]) -> None:
        """
        Load deny lists from multiple JSON files.
        
        Args:
            file_paths: List of paths to deny list JSON files
        """
        total_loaded = 0
        for file_path in file_paths:
            entries_before = len(self.deny_entries)
            self.load_from_file(file_path)
            total_loaded += len(self.deny_entries) - entries_before
        
        logger.info(f"Loaded total of {len(self.deny_entries)} deny list entries from {len(file_paths)} files")
    
    def load_from_directory(self, directory_path: str) -> None:
        """
        Load all JSON files from a directory as deny lists.
        
        Args:
            directory_path: Path to directory containing deny list JSON files
        """
        directory = Path(directory_path)
        if not directory.exists() or not directory.is_dir():
            logger.warning(f"Deny list directory not found: {directory_path}")
            return
        
        json_files = list(directory.glob('*.json'))
        if not json_files:
            logger.info(f"No JSON files found in deny list directory: {directory_path}")
            return
        
        logger.info(f"Found {len(json_files)} deny list files in {directory_path}")
        self.load_from_multiple_files([str(f) for f in json_files])
    
    def _validate_deny_list(self, data: dict) -> None:
        """Validate deny list structure."""
        if not isinstance(data, dict):
            raise ValueError("Deny list must be a JSON object")
        
        if "deny_list" not in data:
            raise ValueError("Missing 'deny_list' key")
        
        if not isinstance(data["deny_list"], list):
            raise ValueError("'deny_list' must be an array")
    
    def _load_deny_entries(self, data: dict) -> None:
        """Load deny entries from parsed JSON."""
        for entry_data in data["deny_list"]:
            entry = DenyListEntry(
                name=entry_data["name"].lower(),
                reason=entry_data["reason"],
                aliases=entry_data.get("aliases", []),
                minimum_supported_version=entry_data.get("minimum_supported_version"),
                recommended_alternative=entry_data.get("recommended_alternative")
            )
            
            self.deny_entries[entry.name] = entry
            
            # Register aliases
            for alias in entry.aliases:
                self.aliases[alias.lower()] = entry.name
    
    def is_denied(self, package_name: str) -> bool:
        """
        Check if a package is in the deny list.
        
        Args:
            package_name: Package name to check
            
        Returns:
            True if package is denied
        """
        normalized_name = package_name.lower()
        
        # Check direct match
        if normalized_name in self.deny_entries:
            return True
        
        # Check aliases
        canonical_name = self.aliases.get(normalized_name)
        if canonical_name is not None:
            return True
        
        # Check if any denied term appears as substring in package name
        for deny_name in self.deny_entries.keys():
            if deny_name in normalized_name:
                return True
        
        # Check aliases as substrings
        for alias in self.aliases.keys():
            if alias in normalized_name:
                return True
        
        return False
    
    def get_deny_entry(self, package_name: str) -> Optional[DenyListEntry]:
        """
        Get deny entry for a package.
        
        Args:
            package_name: Package name to look up
            
        Returns:
            DenyListEntry if found, None otherwise
        """
        normalized_name = package_name.lower()
        
        # Check direct match
        if normalized_name in self.deny_entries:
            return self.deny_entries[normalized_name]
        
        # Check aliases
        canonical_name = self.aliases.get(normalized_name)
        if canonical_name:
            return self.deny_entries[canonical_name]
        
        # Check if any denied term appears as substring
        for deny_name, entry in self.deny_entries.items():
            if deny_name in normalized_name:
                return entry
        
        # Check aliases as substrings
        for alias, canonical_name in self.aliases.items():
            if alias in normalized_name:
                return self.deny_entries[canonical_name]
        
        return None