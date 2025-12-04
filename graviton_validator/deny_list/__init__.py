"""
Deny list functionality for explicitly marking packages as unsupported.
"""

from .loader import DenyListLoader
from .models import DenyListEntry

__all__ = ['DenyListLoader', 'DenyListEntry']