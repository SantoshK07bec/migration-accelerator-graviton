"""
Concrete implementations of knowledge base data structures.
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from ..models import CompatibilityResult, CompatibilityStatus, VersionInfo
from .base import KnowledgeBase

logger = logging.getLogger(__name__)


@dataclass
class CompatibilityRecord:
    """Represents a compatibility record for a software component."""
    name: str
    supported_versions: List[Dict[str, Any]]
    minimum_supported_version: Optional[str]
    recommended_version: Optional[str]
    migration_notes: Optional[str] = None
    aliases: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class JSONKnowledgeBase(KnowledgeBase):
    """JSON-based knowledge base implementation."""
    
    def __init__(self):
        self.compatibility_records: Dict[str, CompatibilityRecord] = {}
        self.software_aliases: Dict[str, str] = {}  # alias -> canonical name
        self._loaded_files: List[str] = []
        self._compatibility_cache: Dict[str, CompatibilityResult] = {}  # Cache for get_compatibility results
        self._intelligent_match_cache: Dict[str, List[str]] = {}  # Cache for intelligent matching results
    
    def load_from_files(self, file_paths: List[str]) -> None:
        """
        Load knowledge base data from JSON files.
        
        Args:
            file_paths: List of paths to knowledge base JSON files
            
        Raises:
            FileNotFoundError: If any file doesn't exist
            ValueError: If file format is invalid
        """
        self.compatibility_records.clear()
        self.software_aliases.clear()
        self._loaded_files.clear()
        
        # Load persistent aliases first (global only at this stage)
        self._load_persistent_aliases()
        
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self._validate_knowledge_base_format(data, file_path)
                self._load_compatibility_data(data)
                self._loaded_files.append(file_path)
                
                logger.info(f"Successfully loaded knowledge base from {file_path}")
                
            except FileNotFoundError:
                logger.error(f"Knowledge base file not found: {file_path}")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in knowledge base file {file_path}: {e}")
                raise ValueError(f"Invalid JSON format in {file_path}: {e}")
            except Exception as e:
                logger.error(f"Error loading knowledge base from {file_path}: {e}")
                raise ValueError(f"Error loading knowledge base from {file_path}: {e}")
    
    def _validate_knowledge_base_format(self, data: Dict[str, Any], file_path: str) -> None:
        """Validate the structure of knowledge base data."""
        if not isinstance(data, dict):
            raise ValueError(f"Knowledge base must be a JSON object in {file_path}")
        
        if "software_compatibility" not in data:
            raise ValueError(f"Missing 'software_compatibility' key in {file_path}")
        
        if not isinstance(data["software_compatibility"], list):
            raise ValueError(f"'software_compatibility' must be a list in {file_path}")
        
        for i, software in enumerate(data["software_compatibility"]):
            if not isinstance(software, dict):
                raise ValueError(f"Software entry {i} must be an object in {file_path}")
            
            if "name" not in software:
                raise ValueError(f"Software entry {i} missing 'name' field in {file_path}")
            
            if "compatibility" not in software:
                raise ValueError(f"Software entry {i} missing 'compatibility' field in {file_path}")
    
    def _load_compatibility_data(self, data: Dict[str, Any]) -> None:
        """Load compatibility data from parsed JSON."""
        for software in data["software_compatibility"]:
            name = software["name"].lower()  # Normalize to lowercase
            compatibility = software["compatibility"]
            
            # Create compatibility record
            record = CompatibilityRecord(
                name=name,
                supported_versions=compatibility.get("supported_versions", []),
                minimum_supported_version=compatibility.get("minimum_supported_version"),
                recommended_version=compatibility.get("recommended_version"),
                migration_notes=compatibility.get("migration_notes"),
                aliases=software.get("aliases", []),
                metadata=software.get("metadata", {})
            )
            
            self.compatibility_records[name] = record
            
            # Register aliases
            for alias in record.aliases or []:
                self.software_aliases[alias.lower()] = name
    
    def get_compatibility(self, software_name: str, version: str) -> CompatibilityResult:
        """
        Get compatibility information for a software component.
        
        Args:
            software_name: Name of the software
            version: Version of the software
            
        Returns:
            CompatibilityResult object
        """
        # Check cache first
        cache_key = f"{software_name.lower()}:{version}"
        if cache_key in self._compatibility_cache:
            return self._compatibility_cache[cache_key]
        
        # Normalize software name
        normalized_name = software_name.lower()
        
        # Check for direct match first
        record = self.compatibility_records.get(normalized_name)
        
        # If not found, check aliases
        if not record:
            canonical_name = self.software_aliases.get(normalized_name)
            if canonical_name:
                logger.debug(f"Using alias: {software_name} -> {canonical_name}")
                record = self.compatibility_records.get(canonical_name)
        
        if not record:
            return CompatibilityResult(
                status=CompatibilityStatus.UNKNOWN,
                current_version_supported=False,
                minimum_supported_version=None,
                recommended_version=None,
                notes=f"No compatibility information found for {software_name}"
            )
        
        # Check version compatibility
        current_version_supported = False
        status = CompatibilityStatus.UNKNOWN
        notes = None
        
        # Check for invalid/placeholder versions
        if version and version.lower() in ['unknown', 'vunknown', 'n/a', 'na', 'null', 'none', 'all', '*', '']:
            version = None  # Treat as no version
        
        if version and record.supported_versions:
            from .version_comparator import SemanticVersionComparator
            comparator = SemanticVersionComparator()
            
            # Check against version specifications
            version_matched = False
            for version_spec in record.supported_versions:
                version_range = version_spec.get("version_range", "")
                # Empty version range matches any version
                if not version_range or comparator.version_matches_range(version, version_range):
                    version_matched = True
                    spec_status = version_spec.get("status", "unknown")
                    if spec_status == "compatible":
                        status = CompatibilityStatus.COMPATIBLE
                        current_version_supported = True
                        notes = version_spec.get("notes")
                    elif spec_status == "compatible_with_notes":
                        status = CompatibilityStatus.COMPATIBLE
                        current_version_supported = True
                        notes = version_spec.get("notes")
                    elif spec_status == "incompatible":
                        status = CompatibilityStatus.INCOMPATIBLE
                        current_version_supported = False
                        notes = version_spec.get("notes")
                    break
            
            # If no version range matched but we have minimum version, check if upgrade needed
            if not version_matched and record.minimum_supported_version:
                try:
                    if comparator.compare_versions(version, record.minimum_supported_version) < 0:
                        status = CompatibilityStatus.NEEDS_UPGRADE
                        current_version_supported = False
                        notes = f"ARM64 support available in version {record.minimum_supported_version} and later. Current version {version} requires upgrade."
                    else:
                        # Version is >= minimum but no specific range matched - assume compatible
                        status = CompatibilityStatus.COMPATIBLE
                        current_version_supported = True
                        notes = f"Version {version} meets minimum requirement ({record.minimum_supported_version})"
                except Exception as e:
                    logger.warning(f"Error comparing versions {version} and {record.minimum_supported_version}: {e}")
                    # Fallback to unknown for version comparison failures
                    status = CompatibilityStatus.UNKNOWN
                    current_version_supported = False
                    notes = f"Version comparison failed for {version} vs {record.minimum_supported_version}. Due to version parsing issues, cannot determine Graviton compatibility. However, recent versions of this software are supported on Graviton (minimum supported version: {record.minimum_supported_version})."
        elif not version or not version.strip():
            # No version provided - check if KB has version requirements
            if record.minimum_supported_version or any(v.get("version_range") for v in record.supported_versions):
                # KB has version info but SBOM doesn't - return needs version verification
                status = CompatibilityStatus.NEEDS_VERSION_VERIFICATION
                current_version_supported = False
                if record.minimum_supported_version and record.recommended_version:
                    notes = f"Version verification needed - software is Graviton-compatible (min: v{record.minimum_supported_version}, recommended: v{record.recommended_version}). Verify your version meets requirements."
                elif record.minimum_supported_version:
                    notes = f"Version verification needed - software is Graviton-compatible (min: v{record.minimum_supported_version}). Verify your version meets requirements."
                else:
                    notes = "Version verification needed - software is Graviton-compatible. Verify your version meets requirements."
            else:
                # KB has no version requirements - still unknown due to missing version
                status = CompatibilityStatus.UNKNOWN
                current_version_supported = False
                notes = "No version information available. Manual testing required before migration."
        
        # Handle cases where version couldn't be processed but component is in KB
        if status == CompatibilityStatus.UNKNOWN and version:
            # For cases where version format couldn't be processed
            if record.minimum_supported_version:
                status = CompatibilityStatus.NEEDS_VERSION_VERIFICATION
                notes = f"Version '{version}' format not recognized - software is Graviton-compatible (min: v{record.minimum_supported_version}). Verify your version meets requirements."
            else:
                notes = f"Version '{version}' format not recognized. Manual testing required before migration."
        
        result = CompatibilityResult(
            status=status,
            current_version_supported=current_version_supported,
            minimum_supported_version=record.minimum_supported_version,
            recommended_version=record.recommended_version,
            notes=notes or record.migration_notes
        )
        
        # Cache the result
        self._compatibility_cache[cache_key] = result
        return result
    
    def find_compatible_versions(self, software_name: str) -> List[VersionInfo]:
        """
        Find all compatible versions for a software component.
        
        Args:
            software_name: Name of the software
            
        Returns:
            List of VersionInfo objects
        """
        normalized_name = software_name.lower()
        
        # Check for direct match first
        record = self.compatibility_records.get(normalized_name)
        
        # If not found, check aliases
        if not record:
            canonical_name = self.software_aliases.get(normalized_name)
            if canonical_name:
                record = self.compatibility_records.get(canonical_name)
        
        if not record:
            return []
        
        version_infos = []
        for version_spec in record.supported_versions:
            spec_status = version_spec.get("status", "unknown")
            if spec_status in ["compatible", "compatible_with_notes"]:
                # Extract version from range (simplified - just take the range as version info)
                version_range = version_spec.get("version_range", "")
                status = CompatibilityStatus.COMPATIBLE
                notes = version_spec.get("notes")
                
                version_infos.append(VersionInfo(
                    version=version_range,
                    status=status,
                    notes=notes
                ))
        
        return version_infos
    
    def intelligent_match(self, software_name: str, matching_config=None) -> List[str]:
        """
        Perform intelligent/fuzzy matching for software names.
        
        Args:
            software_name: Name to match against
            matching_config: Optional matching configuration
            
        Returns:
            List of potential matches from knowledge base
        """
        # Check cache first
        if software_name in self._intelligent_match_cache:
            return self._intelligent_match_cache[software_name]
        
        # Quick exact match check first
        normalized_name = software_name.lower()
        if normalized_name in self.compatibility_records or normalized_name in self.software_aliases:
            result = [normalized_name]
            self._intelligent_match_cache[software_name] = result
            return result
        
        # Performance optimization: limit candidates and use faster matching
        candidates = list(self.compatibility_records.keys()) + list(self.software_aliases.keys())
        
        # Limit candidates for performance (top 100 most common packages)
        if len(candidates) > 100:
            candidates = candidates[:100]
        
        try:
            from .intelligent_matcher import FuzzyMatcher
            
            # Create matcher with performance-optimized configuration
            if matching_config:
                # Override some settings for performance
                matcher = FuzzyMatcher(
                    similarity_threshold=max(0.7, getattr(matching_config, 'similarity_threshold', 0.7)),  # Higher threshold
                    max_matches=min(3, getattr(matching_config, 'max_matches', 3)),  # Fewer matches
                    min_confidence_threshold=max(0.6, getattr(matching_config, 'min_confidence_threshold', 0.6))
                )
            else:
                matcher = FuzzyMatcher(
                    similarity_threshold=0.7,  # Higher threshold for performance
                    max_matches=3,  # Limit matches
                    min_confidence_threshold=0.6
                )
            
            # Find best matches using the configured matcher
            matches = matcher.find_multiple_matches(software_name, candidates)
            result = [match[0] for match in matches]
            
            # Cache the result
            self._intelligent_match_cache[software_name] = result
            return result
            
        except ImportError:
            # Fallback to simple string matching if intelligent matcher not available
            logger.warning("Intelligent matcher not available, using simple matching")
            candidates = list(self.compatibility_records.keys()) + list(self.software_aliases.keys())
            matches = []
            
            query_lower = software_name.lower()
            for candidate in candidates:
                candidate_lower = candidate.lower()
                similarity = self._simple_similarity(query_lower, candidate_lower)
                
                # Simple substring and case-insensitive matching
                if (query_lower in candidate_lower or 
                    candidate_lower in query_lower or 
                    query_lower == candidate_lower or
                    similarity > 0.6):  # Use 0.6 threshold to match nginx-server
                    matches.append(candidate)
            
            result = matches[:3]  # Limit to 3 matches for performance
            
            # Cache the result
            self._intelligent_match_cache[software_name] = result
            return result
    
    def _simple_similarity(self, s1: str, s2: str) -> float:
        """Simple similarity calculation for fallback matching."""
        if s1 == s2:
            return 1.0
        if not s1 or not s2:
            return 0.0
        
        # Check for substring matches
        if s1 in s2 or s2 in s1:
            shorter = min(len(s1), len(s2))
            longer = max(len(s1), len(s2))
            return shorter / longer
        
        # Check for word-based matching (split by common separators)
        s1_words = set(word for word in re.split(r'[-_\s]+', s1.lower()) if word)
        s2_words = set(word for word in re.split(r'[-_\s]+', s2.lower()) if word)
        
        if s1_words & s2_words:  # If there's any word overlap
            overlap = len(s1_words & s2_words)
            total = len(s1_words | s2_words)
            word_similarity = overlap / total if total > 0 else 0.0
            
            # Boost score if main word matches (first word typically most important)
            s1_main = list(s1_words)[0] if s1_words else ""
            s2_main = list(s2_words)[0] if s2_words else ""
            if s1_main and s2_main and (s1_main in s2_main or s2_main in s1_main):
                word_similarity = min(1.0, word_similarity + 0.3)
            
            return word_similarity
        
        # Simple character overlap as fallback
        s1_chars = set(s1)
        s2_chars = set(s2)
        overlap = len(s1_chars & s2_chars)
        total = len(s1_chars | s2_chars)
        
        return overlap / total if total > 0 else 0.0
    
    def get_all_software_names(self) -> List[str]:
        """Get all software names in the knowledge base."""
        return list(self.compatibility_records.keys())
    
    def get_loaded_files(self) -> List[str]:
        """Get list of successfully loaded knowledge base files."""
        return self._loaded_files.copy()
    
    def find_software(self, software_name: str) -> Optional[CompatibilityRecord]:
        """Find software entry by name or alias."""
        normalized_name = software_name.lower()
        
        # Check for direct match first
        record = self.compatibility_records.get(normalized_name)
        
        # If not found, check aliases
        if not record:
            canonical_name = self.software_aliases.get(normalized_name)
            if canonical_name:
                record = self.compatibility_records.get(canonical_name)
        
        return record
    
    def _load_persistent_aliases(self, detected_os=None):
        """Load persistent aliases from common_aliases.json file."""
        import os
        
        # Try to find common_aliases.json in knowledge_bases directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        aliases_file = os.path.join(project_root, "knowledge_bases", "os_knowledge_bases", "common_aliases.json")
        
        if os.path.exists(aliases_file):
            try:
                with open(aliases_file, 'r', encoding='utf-8') as f:
                    aliases_data = json.load(f)
                
                # Load global aliases first
                global_aliases = aliases_data.get("aliases", {})
                for alias, target in global_aliases.items():
                    self.software_aliases[alias.lower()] = target.lower()
                
                # Load OS-specific aliases if available and detected_os is provided
                if detected_os and "os_specific_aliases" in aliases_data:
                    os_aliases = aliases_data.get("os_specific_aliases", {}).get(detected_os, {})
                    for alias, target in os_aliases.items():
                        self.software_aliases[alias.lower()] = target.lower()  # OS-specific overrides global
                    
                    if os_aliases:
                        logger.info(f"Loaded {len(os_aliases)} OS-specific aliases for {detected_os}")
                
                logger.info(f"Loaded {len(global_aliases)} global persistent aliases")
                logger.debug(f"Persistent aliases: {list(global_aliases.keys())}")
                
            except Exception as e:
                logger.warning(f"Failed to load persistent aliases: {e}")
        else:
            logger.debug(f"No persistent aliases file found at {aliases_file}")
    
    @property
    def software_entries(self) -> List[CompatibilityRecord]:
        """Get all software entries for compatibility with main application."""
        return list(self.compatibility_records.values())


def create_knowledge_base_template() -> Dict[str, Any]:
    """
    Create a template structure for knowledge base JSON files.
    
    Returns:
        Dictionary representing the knowledge base template
    """
    template = {
        "software_compatibility": [
            {
                "name": "nginx",
                "aliases": ["nginx-server", "nginx-web-server"],
                "compatibility": {
                    "supported_versions": [
                        {
                            "version_range": ">=1.18.0",
                            "status": "compatible",
                            "notes": "Full Graviton support with optimizations"
                        },
                        {
                            "version_range": ">=1.14.0,<1.18.0",
                            "status": "compatible_with_notes",
                            "notes": "Compatible but performance optimizations available in newer versions"
                        },
                        {
                            "version_range": "<1.14.0",
                            "status": "incompatible",
                            "notes": "Requires upgrade for Graviton compatibility"
                        }
                    ],
                    "minimum_supported_version": "1.14.0",
                    "recommended_version": "1.20.2",
                    "migration_notes": "Consider enabling specific Graviton optimizations in configuration"
                }
            },
            {
                "name": "python",
                "aliases": ["python3", "python-interpreter"],
                "compatibility": {
                    "supported_versions": [
                        {
                            "version_range": ">=3.8.0",
                            "status": "compatible",
                            "notes": "Full Graviton support"
                        },
                        {
                            "version_range": ">=3.6.0,<3.8.0",
                            "status": "compatible_with_notes",
                            "notes": "Compatible but newer versions have better performance"
                        },
                        {
                            "version_range": "<3.6.0",
                            "status": "incompatible",
                            "notes": "Upgrade required for Graviton support"
                        }
                    ],
                    "minimum_supported_version": "3.6.0",
                    "recommended_version": "3.11.0",
                    "migration_notes": "Ensure all Python packages are also Graviton-compatible"
                }
            }
        ]
    }
    
    return template