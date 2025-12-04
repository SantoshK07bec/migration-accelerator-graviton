"""
Data models for deny list functionality.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DenyListEntry:
    """Represents a package that is explicitly denied/unsupported."""
    name: str
    reason: str
    aliases: List[str] = None
    minimum_supported_version: Optional[str] = None
    recommended_alternative: Optional[str] = None
    
    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []