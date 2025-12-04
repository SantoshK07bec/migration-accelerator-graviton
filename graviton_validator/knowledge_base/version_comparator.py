"""
Version comparison logic for semantic versioning.
"""

import re
import logging
from typing import List, Tuple, Optional

from .base import VersionComparator

logger = logging.getLogger(__name__)


class SemanticVersionComparator(VersionComparator):
    """Semantic version comparator supporting version ranges."""
    
    def __init__(self):
        # Regex pattern for semantic version parsing
        self.version_pattern = re.compile(
            r'^(?P<major>\d+)(?:\.(?P<minor>\d+))?(?:\.(?P<patch>\d+))?'
            r'(?:-(?P<prerelease>[0-9A-Za-z]+(?:\.[0-9A-Za-z]+)*))?'
            r'(?:\+(?P<build>[0-9A-Za-z]+(?:\.[0-9A-Za-z]+)*))?$'
        )
        
        # Regex pattern for version range parsing
        self.range_pattern = re.compile(
            r'(?P<operator>>=|<=|==|>|<|=|~|\^)?\s*v?(?P<version>[0-9]+(?:\.[0-9]+)*(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?)'
        )
        
        # Cache for parsed versions
        self._version_cache = {}
    
    def parse_version(self, version: str) -> Tuple[int, int, int, str, str]:
        """
        Parse a version string into components.
        
        Args:
            version: Version string to parse
            
        Returns:
            Tuple of (major, minor, patch, prerelease, build)
            
        Raises:
            ValueError: If version format is invalid
        """
        if not version:
            raise ValueError("Version string cannot be empty")
        
        # Check cache first
        if version in self._version_cache:
            return self._version_cache[version]
        
        # Clean version string
        original_version = version
        version = version.strip().lstrip('v')
        
        # Handle Debian epoch format (e.g., "5:1.2.3" -> "1.2.3")
        if ':' in version and version.split(':', 1)[0].isdigit():
            version = version.split(':', 1)[1]
        
        # Only normalize complex versions if they don't look like semantic versions
        # Semantic versions have + for build metadata, don't normalize those
        if not ('+' in version and re.match(r'^\d+(?:\.\d+)*(?:-[0-9A-Za-z]+(?:\.[0-9A-Za-z]+)*)?\+', version)):
            # Handle complex package versions like "1.14-18.amzn2.1"
            version = self._normalize_complex_version(version)
        
        # Handle 4-part versions by truncating to 3 parts with warning
        parts = version.split('.')
        if len(parts) == 4 and all(part.isdigit() for part in parts):
            truncated_version = '.'.join(parts[:3])
            logger.warning(f"4-part version '{version}' truncated to '{truncated_version}' for comparison")
            version = truncated_version
        
        match = self.version_pattern.match(version)
        if not match:
            # Try to handle simple numeric versions like "1.2" or "1"
            if len(parts) <= 3 and all(part.isdigit() for part in parts):
                major = int(parts[0])
                minor = int(parts[1]) if len(parts) > 1 else 0
                patch = int(parts[2]) if len(parts) > 2 else 0
                return (major, minor, patch, "", "")
            else:
                raise ValueError(f"Invalid version format: {version}")
        
        groups = match.groupdict()
        major = int(groups['major'])
        minor = int(groups['minor']) if groups['minor'] else 0
        patch = int(groups['patch']) if groups['patch'] else 0
        prerelease = groups['prerelease'] or ""
        build = groups['build'] or ""
        
        result = (major, minor, patch, prerelease, build)
        self._version_cache[original_version] = result
        return result
    
    def compare_versions(self, version1: str, version2: str) -> int:
        """
        Compare two version strings.
        
        Args:
            version1: First version string
            version2: Second version string
            
        Returns:
            -1 if version1 < version2, 0 if equal, 1 if version1 > version2
        """
        try:
            v1_parts = self.parse_version(version1)
            v2_parts = self.parse_version(version2)
            
            # Compare major, minor, patch
            for i in range(3):
                if v1_parts[i] < v2_parts[i]:
                    return -1
                elif v1_parts[i] > v2_parts[i]:
                    return 1
            
            # Compare prerelease (empty prerelease > non-empty prerelease)
            v1_pre, v2_pre = v1_parts[3], v2_parts[3]
            
            if not v1_pre and not v2_pre:
                return 0
            elif not v1_pre and v2_pre:
                return 1  # 1.0.0 > 1.0.0-alpha
            elif v1_pre and not v2_pre:
                return -1  # 1.0.0-alpha < 1.0.0
            else:
                # Both have prerelease, compare lexicographically
                if v1_pre < v2_pre:
                    return -1
                elif v1_pre > v2_pre:
                    return 1
                else:
                    return 0
                    
        except ValueError as e:
            # Only log warning for unexpected errors, not non-semantic versions
            if not (self._is_non_semantic_version(version1) or self._is_non_semantic_version(version2)):
                logger.warning(f"Error comparing versions '{version1}' and '{version2}': {e}")
            else:
                logger.debug(f"Skipping comparison of non-semantic versions '{version1}' and '{version2}'")
            
            # Fallback to string comparison
            if version1 < version2:
                return -1
            elif version1 > version2:
                return 1
            else:
                return 0
    
    def version_matches_range(self, version: str, version_range: str) -> bool:
        """
        Check if a version matches a version range specification.
        
        Args:
            version: Version string to check
            version_range: Version range specification (e.g., ">=2.1.0,<3.0.0", "*", "all")
            
        Returns:
            True if version matches range, False otherwise
        """
        if not version_range or version_range == "*" or version_range.lower() == "all":
            return True
        
        try:
            # Split range by comma for multiple constraints
            constraints = [c.strip() for c in version_range.split(',')]
            
            for constraint in constraints:
                constraint = constraint.strip()
                if not self._check_single_constraint(version, constraint):
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Error checking version range '{version}' against '{version_range}': {e}")
            return False
    
    def _check_single_constraint(self, version: str, constraint: str) -> bool:
        """Check a single version constraint."""
        constraint = constraint.strip()
        
        # Handle non-semantic version formats gracefully
        if self._is_non_semantic_version(constraint):
            logger.debug(f"Skipping non-semantic version constraint: {constraint}")
            return True  # Assume compatible for non-semantic versions
        
        match = self.range_pattern.match(constraint)
        if not match:
            # If no operator, assume exact match
            try:
                return self.compare_versions(version, constraint) == 0
            except ValueError:
                logger.debug(f"Cannot compare versions '{version}' and '{constraint}' - assuming compatible")
                return True
        
        operator = match.group('operator') or '='
        constraint_version = match.group('version').strip()
        
        # Skip non-semantic constraint versions
        if self._is_non_semantic_version(constraint_version):
            logger.debug(f"Skipping non-semantic constraint version: {constraint_version}")
            return True
        
        try:
            comparison = self.compare_versions(version, constraint_version)
        except ValueError:
            logger.debug(f"Cannot compare versions '{version}' and '{constraint_version}' - assuming compatible")
            return True
        
        if operator == '=' or operator == '==':
            return comparison == 0
        elif operator == '>':
            return comparison > 0
        elif operator == '>=':
            return comparison >= 0
        elif operator == '<':
            return comparison < 0
        elif operator == '<=':
            return comparison <= 0
        elif operator == '~':
            # Tilde range: ~1.2.3 := >=1.2.3 <1.(2+1).0
            return self._check_tilde_range(version, constraint_version)
        elif operator == '^':
            # Caret range: ^1.2.3 := >=1.2.3 <2.0.0
            return self._check_caret_range(version, constraint_version)
        else:
            logger.warning(f"Unknown version operator: {operator}")
            return False
    
    def _check_tilde_range(self, version: str, constraint_version: str) -> bool:
        """Check tilde range constraint (~1.2.3 := >=1.2.3 <1.3.0)."""
        try:
            v_parts = self.parse_version(version)
            c_parts = self.parse_version(constraint_version)
            
            # Must be >= constraint version
            if self.compare_versions(version, constraint_version) < 0:
                return False
            
            # Must have same major and minor version
            return v_parts[0] == c_parts[0] and v_parts[1] == c_parts[1]
            
        except ValueError:
            return False
    
    def _check_caret_range(self, version: str, constraint_version: str) -> bool:
        """Check caret range constraint (^1.2.3 := >=1.2.3 <2.0.0)."""
        try:
            v_parts = self.parse_version(version)
            c_parts = self.parse_version(constraint_version)
            
            # Must be >= constraint version
            if self.compare_versions(version, constraint_version) < 0:
                return False
            
            # Must have same major version
            return v_parts[0] == c_parts[0]
            
        except ValueError:
            return False
    
    def get_latest_version(self, versions: List[str]) -> Optional[str]:
        """
        Get the latest version from a list of version strings.
        
        Args:
            versions: List of version strings
            
        Returns:
            Latest version string or None if list is empty
        """
        if not versions:
            return None
        
        valid_versions = []
        for version in versions:
            try:
                self.parse_version(version)
                valid_versions.append(version)
            except ValueError:
                logger.warning(f"Skipping invalid version: {version}")
        
        if not valid_versions:
            return None
        
        latest = valid_versions[0]
        for version in valid_versions[1:]:
            if self.compare_versions(version, latest) > 0:
                latest = version
        
        return latest
    
    def _normalize_complex_version(self, version: str) -> str:
        """
        Normalize complex version formats like "1.14-18.amzn2.1" to semantic versions.
        
        Args:
            version: Original version string
            
        Returns:
            Normalized version string
        """
        # Handle formats like "1.14-18.amzn2.1", "2.4.6-1ubuntu1", "1.2.3-4.el8"
        # Pattern: base_version-release_info
        if '-' in version:
            parts = version.split('-', 1)
            base_version = parts[0]
            release_info = parts[1]
            
            # Extract numeric parts from base version
            base_parts = base_version.split('.')
            
            # Handle very complex versions like kernel versions (5.10.239-236.958.amzn2.x86_64)
            # Take only first 3 numeric parts
            numeric_parts = []
            for part in base_parts:
                if part.isdigit():
                    numeric_parts.append(part)
                if len(numeric_parts) >= 3:
                    break
            
            # Pad with zeros if needed
            while len(numeric_parts) < 3:
                numeric_parts.append('0')
            
            # Extract first numeric part from release info as patch increment
            release_match = re.match(r'^(\d+)', release_info)
            if release_match:
                release_num = int(release_match.group(1))
                # Add release number to patch version (but keep it reasonable)
                if len(numeric_parts) >= 3:
                    current_patch = int(numeric_parts[2])
                    # Limit the addition to prevent overflow
                    numeric_parts[2] = str(min(current_patch + release_num, 9999))
            
            # Return normalized version with distribution info as prerelease
            normalized = '.'.join(numeric_parts[:3])
            
            # Add distribution info as prerelease if present
            dist_info = re.sub(r'^\d+\.?', '', release_info)
            if dist_info:
                # Clean up distribution info to be valid prerelease
                dist_info = re.sub(r'[^a-zA-Z0-9.-]', '', dist_info)
                if dist_info:
                    normalized += f"-{dist_info}"
            
            return normalized
        
        return version
    
    def _is_non_semantic_version(self, version: str) -> bool:
        """
        Check if a version string is a non-semantic format that should be skipped.
        
        Args:
            version: Version string to check
            
        Returns:
            True if version is non-semantic format
        """
        if not version:
            return True
        
        # Clean the version string
        clean_version = version.strip().lstrip('>=<~^=').lstrip('v')
        
        # Check for non-semantic patterns
        non_semantic_patterns = [
            r'^[A-Z_]+$',  # All caps like "OPENLDAP_REL_ENG_2_4_50"
            r'^[A-Z]+_\d+',  # Pattern like "V_8_2_P1"
            r'^r\d+$',  # Pattern like "r116"
            r'[A-Z]{3,}',  # Contains 3+ consecutive uppercase letters
            r'^[A-Z]+_[A-Z]+_',  # Pattern like "OPENLDAP_REL_"
        ]
        
        for pattern in non_semantic_patterns:
            if re.search(pattern, clean_version):
                return True
        
        # Additional check: if it contains mostly non-numeric characters after cleaning
        if clean_version and not re.search(r'\d', clean_version):
            return True
        
        return False
    
    def is_valid_version(self, version: str) -> bool:
        """
        Check if a version string is valid.
        
        Args:
            version: Version string to validate
            
        Returns:
            True if version is valid, False otherwise
        """
        try:
            self.parse_version(version)
            return True
        except ValueError:
            return False