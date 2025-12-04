"""
OS Detection module - all functionality moved to OSConfigManager.
This module is deprecated - use OSConfigManager directly.
"""

# Re-export OSConfigManager for backward compatibility
from .os_configs import OSConfigManager as OSDetector

