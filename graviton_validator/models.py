"""
Core data models for the Graviton Compatibility Validator.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class CompatibilityStatus(Enum):
    """Enumeration of possible compatibility statuses."""
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    NEEDS_UPGRADE = "needs_upgrade"
    NEEDS_VERIFICATION = "needs_verification"
    NEEDS_VERSION_VERIFICATION = "needs_version_verification"
    UNKNOWN = "unknown"


@dataclass
class SoftwareComponent:
    """Represents a software component extracted from an SBOM."""
    name: str
    version: Optional[str]
    component_type: str  # library, application, etc.
    source_sbom: str     # file path of source SBOM
    properties: Dict[str, str]
    parent_component: Optional[str] = None  # Name of parent/source component
    child_components: List[str] = None  # Names of child components
    source_package: Optional[str] = None  # Source package name for Debian/Ubuntu
    
    def __post_init__(self):
        """Initialize child_components as empty list if None."""
        if self.child_components is None:
            self.child_components = []


@dataclass
class VersionInfo:
    """Represents version information for a software component."""
    version: str
    status: CompatibilityStatus
    notes: Optional[str] = None


@dataclass
class CompatibilityResult:
    """Result of compatibility analysis for a software component."""
    status: CompatibilityStatus
    current_version_supported: bool
    minimum_supported_version: Optional[str]
    recommended_version: Optional[str]
    notes: Optional[str]
    confidence_level: float = 1.0  # For intelligent matching


@dataclass
class ComponentResult:
    """Analysis result for a single component."""
    component: SoftwareComponent
    compatibility: CompatibilityResult
    matched_name: Optional[str] = None  # For intelligent matching


@dataclass
class AnalysisResult:
    """Complete analysis result for all components."""
    components: List[ComponentResult]
    total_components: int
    compatible_count: int
    incompatible_count: int
    needs_upgrade_count: int
    needs_verification_count: int
    needs_version_verification_count: int
    unknown_count: int
    errors: List[str]
    processing_time: float
    detected_os: Optional[str] = None
    sbom_file: Optional[str] = None