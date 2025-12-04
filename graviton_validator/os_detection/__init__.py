"""
OS Detection module for identifying operating systems from SBOM data.
"""

from .detector import OSDetector
from .os_configs import OSConfigManager

__all__ = ['OSDetector', 'OSConfigManager']