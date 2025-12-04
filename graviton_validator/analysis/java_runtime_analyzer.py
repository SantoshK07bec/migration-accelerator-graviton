"""
Java-specific compatibility analyzer for Graviton processors.

This module implements Java runtime dependency analysis by checking
Maven components against known problematic libraries and patterns.
"""

import re
import logging
from typing import Optional, Dict, List, Tuple
from .runtime_analyzer import RuntimeCompatibilityAnalyzer
from ..models import SoftwareComponent, ComponentResult, CompatibilityResult, CompatibilityStatus

logger = logging.getLogger(__name__)


class JavaRuntimeCompatibilityAnalyzer(RuntimeCompatibilityAnalyzer):
    """Java-specific compatibility analyzer for Graviton processors."""
    
    def __init__(self, knowledge_base=None):
        """
        Initialize Java runtime analyzer.
        
        Args:
            knowledge_base: KnowledgeBase instance with runtime_dependencies section
        """
        self.knowledge_base = knowledge_base
        self.maven_purl_pattern = re.compile(r'^pkg:maven/([^/]+)/([^@]+)@(.+)$')
        self.compatibility_cache = {}
    
    def get_runtime_type(self) -> str:
        """Return runtime type."""
        return 'java'
    
    def get_supported_purls(self) -> List[str]:
        """Return supported PURL prefixes."""
        return ['pkg:maven/']
    
    def is_applicable(self, component: SoftwareComponent) -> bool:
        """Check if this analyzer can handle the component."""
        purl = component.properties.get('purl', '') if component.properties else ''
        return any(purl.startswith(prefix) for prefix in self.get_supported_purls())
    
    def analyze_component(self, component: SoftwareComponent) -> ComponentResult:
        """
        Analyze Java component for ARM compatibility.
        
        Args:
            component: Java component to analyze
            
        Returns:
            ComponentResult with compatibility analysis
        """
        logger.debug(f"Analyzing Java component: {component.name}@{component.version}")
        
        try:
            # Extract Maven coordinates
            group_id, artifact_id, version = self._parse_maven_coordinates(component)
            maven_key = f"{group_id}:{artifact_id}"
            logger.debug(f"Parsed Maven coordinates: {maven_key}@{version}")
            
            # Check cache first
            cache_key = f"{maven_key}:{version}"
            if cache_key in self.compatibility_cache:
                logger.debug(f"Using cached result for {cache_key}")
                return self.compatibility_cache[cache_key]
            
            # Analyze compatibility
            logger.debug(f"Starting Java compatibility analysis for {maven_key}")
            compatibility_result = self._analyze_maven_component(maven_key, version, component)
            logger.debug(f"Java analysis result for {maven_key}: {compatibility_result.status}")
            
            result = ComponentResult(
                component=component,
                compatibility=compatibility_result
            )
            
            # Cache result
            self.compatibility_cache[cache_key] = result
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing Java component {component.name}: {e}")
            return self._create_error_result(component, str(e))
    
    def _parse_maven_coordinates(self, component: SoftwareComponent) -> Tuple[str, str, str]:
        """
        Extract groupId, artifactId, version from component.
        
        Args:
            component: SoftwareComponent to parse
            
        Returns:
            Tuple of (group_id, artifact_id, version)
            
        Raises:
            ValueError: If Maven coordinates cannot be parsed
        """
        purl = component.properties.get('purl', '') if component.properties else ''
        match = self.maven_purl_pattern.match(purl)
        
        if match:
            group_id, artifact_id, version = match.groups()
            return group_id, artifact_id, version
        
        # Fallback: try to parse from component name
        if ':' in component.name:
            parts = component.name.split(':')
            if len(parts) >= 2:
                return parts[0], parts[1], component.version or 'unknown'
        
        raise ValueError(f"Cannot parse Maven coordinates from {component.name}")
    
    def _analyze_maven_component(self, maven_key: str, version: str, component: SoftwareComponent) -> CompatibilityResult:
        """
        Analyze Maven component using complete logic from java_arm_compatibility.py.
        
        Args:
            maven_key: Maven coordinates (groupId:artifactId)
            version: Component version
            component: Original component
            
        Returns:
            CompatibilityResult with comprehensive analysis
        """
        # Check for ARM-specific classifier first
        classifier = component.properties.get('classifier', '') if component.properties else ''
        if classifier and any(arm_arch in classifier.lower() for arm_arch in 
                             ['arm64', 'aarch64', 'arm', 'aarch32', 'armv7', 'armv8']):
            return CompatibilityResult(
                status=CompatibilityStatus.COMPATIBLE,
                current_version_supported=True,
                minimum_supported_version=None,
                recommended_version=None,
                notes=f"Using ARM-specific classifier '{classifier}' - no action needed",
                confidence_level=0.95
            )
        
        # Check known problematic libraries from knowledge base
        java_deps = self._get_java_dependencies_from_kb()
        logger.debug(f"Java knowledge base has {len(java_deps)} entries")
        
        if maven_key in java_deps:
            logger.debug(f"Found {maven_key} in Java knowledge base")
            return self._analyze_problematic_library(maven_key, version, java_deps[maven_key])
        else:
            logger.debug(f"Maven component {maven_key} not found in Java knowledge base")
        
        # Check native code patterns from knowledge base
        has_native = self._has_native_code_patterns(maven_key)
        logger.debug(f"Native code patterns check for {maven_key}: {has_native}")
        
        if has_native:
            return self._analyze_native_code_component(maven_key, version)
        
        # Check for endianness issues from knowledge base
        endianness_issues = self._check_endianness_issues(maven_key)
        logger.debug(f"Endianness issues check for {maven_key}: {endianness_issues}")
        
        # Check for memory alignment issues from knowledge base
        alignment_issues = self._check_memory_alignment_issues(maven_key)
        logger.debug(f"Memory alignment issues check for {maven_key}: {alignment_issues}")
        
        # Check for available ARM classifiers from knowledge base
        arm_classifier_suggestion = self._check_arm_classifiers(maven_key, classifier)
        logger.debug(f"ARM classifier suggestion for {maven_key}: {arm_classifier_suggestion}")
        
        # Build comprehensive result
        issues = []
        recommendations = []
        
        if endianness_issues:
            issues.append("Potential endianness issues on ARM")
            recommendations.append("Test byte order handling on ARM")
        
        if alignment_issues:
            issues.append("Potential memory alignment issues on ARM")
            recommendations.append("Test memory access patterns on ARM")
        
        if arm_classifier_suggestion:
            recommendations.append(arm_classifier_suggestion)
        
        # Determine overall status
        if issues:
            status = CompatibilityStatus.UNKNOWN
            confidence = 0.6
        else:
            status = CompatibilityStatus.COMPATIBLE
            confidence = 0.7
        
        logger.debug(f"Final Java analysis for {maven_key}: status={status}, issues={issues}, recommendations={recommendations}")
        
        notes_parts = [f"Java library {maven_key}"]
        if issues:
            notes_parts.append(". ".join(issues))
        else:
            notes_parts.append("no known ARM compatibility issues")
        
        if recommendations:
            notes_parts.append(". ".join(recommendations))
        
        # Add Java analysis details for UNKNOWN status
        if status == CompatibilityStatus.UNKNOWN:
            analysis_details = f"Java analysis: kb_lookup={'found' if maven_key in java_deps else 'not_found'}, native_code={has_native}, endianness_issues={endianness_issues}, alignment_issues={alignment_issues}, arm_classifier_available={bool(arm_classifier_suggestion)}"
            notes_parts.append(analysis_details)
        
        return CompatibilityResult(
            status=status,
            current_version_supported=True,
            minimum_supported_version=None,
            recommended_version=None,
            notes=". ".join(notes_parts),
            confidence_level=confidence
        )
    
    def _analyze_problematic_library(self, maven_key: str, version: str, lib_info: Dict) -> CompatibilityResult:
        """
        Analyze known problematic library using knowledge base data.
        
        Args:
            maven_key: Maven coordinates
            version: Component version
            lib_info: Library information from knowledge base
            
        Returns:
            CompatibilityResult based on version comparison
        """
        fixed_version = lib_info.get('minimum_supported_version')
        
        # Check for invalid/placeholder versions
        if version and version.lower() in ['unknown', 'vunknown', 'n/a', 'na', 'null', 'none', 'all', '*', '']:
            version = None  # Treat as no version
        
        # Handle missing or invalid version when we have version requirements
        if not version or not version.strip():
            if fixed_version:
                notes = f"Version verification needed - software is Graviton-compatible (min: v{fixed_version}). Verify your version meets requirements."
                return CompatibilityResult(
                    status=CompatibilityStatus.NEEDS_VERSION_VERIFICATION,
                    current_version_supported=False,
                    minimum_supported_version=fixed_version,
                    recommended_version=lib_info.get('recommended_version', fixed_version),
                    notes=notes,
                    confidence_level=0.9
                )
        
        if fixed_version and self._compare_versions(version, fixed_version) < 0:
            return CompatibilityResult(
                status=CompatibilityStatus.INCOMPATIBLE,
                current_version_supported=False,
                minimum_supported_version=fixed_version,
                recommended_version=lib_info.get('recommended_version', fixed_version),
                notes=f"{lib_info.get('issue_description', 'Known compatibility issue')}. {lib_info.get('upgrade_notes', '')}",
                confidence_level=0.9
            )
        else:
            # Build notes with additional warnings for endianness/alignment issues
            notes_parts = [f"Version {version} includes ARM compatibility fixes"]
            
            if lib_info.get('endianness_sensitive', False):
                notes_parts.append("Potential endianness issues on ARM - test byte order handling")
            
            if lib_info.get('memory_alignment_sensitive', False):
                notes_parts.append("Potential memory alignment issues on ARM - test memory access patterns")
            
            return CompatibilityResult(
                status=CompatibilityStatus.COMPATIBLE,
                current_version_supported=True,
                minimum_supported_version=fixed_version,
                recommended_version=lib_info.get('recommended_version', fixed_version),
                notes=". ".join(notes_parts),
                confidence_level=0.9
            )
    
    def _analyze_native_code_component(self, maven_key: str, version: str) -> CompatibilityResult:
        """
        Analyze component with potential native code.
        
        Args:
            maven_key: Maven coordinates
            version: Component version
            
        Returns:
            CompatibilityResult for native code component
        """
        analysis_details = f"Java analysis: native_code=True, requires_testing=True"
        return CompatibilityResult(
            status=CompatibilityStatus.UNKNOWN,
            current_version_supported=False,
            minimum_supported_version=None,
            recommended_version=None,
            notes=f"Library {maven_key} may contain native code - requires testing on ARM. {analysis_details}",
            confidence_level=0.6
        )
    
    def _has_native_code_patterns(self, maven_key: str) -> bool:
        """
        Check if component matches native code patterns from knowledge base.
        
        Args:
            maven_key: Maven coordinates to check
            
        Returns:
            True if component likely contains native code
        """
        java_deps = self._get_java_dependencies_from_kb()
        
        # Check if any dependency entry indicates native code
        for dep_key, dep_info in java_deps.items():
            if dep_key in maven_key and dep_info.get('native_code', False):
                return True
        
        # Check for common native code patterns in group/artifact names
        native_patterns = ['lwjgl', 'native', 'jni', 'jna', 'netty-transport-native']
        maven_lower = maven_key.lower()
        
        return any(pattern in maven_lower for pattern in native_patterns)
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """
        Compare two version strings.
        
        Args:
            version1: First version
            version2: Second version
            
        Returns:
            -1 if version1 < version2, 0 if equal, 1 if version1 > version2
        """
        def normalize(v):
            if not v:
                return '0'
            v = str(v).strip().lower()
            if 'final' in v:
                v = v.replace('final', '')
            if 'release' in v:
                v = v.replace('release', '')
            return v.strip()
        
        parts1 = [normalize(p) for p in re.split(r'[\.\-]', version1) if normalize(p)]
        parts2 = [normalize(p) for p in re.split(r'[\.\-]', version2) if normalize(p)]
        
        for i in range(max(len(parts1), len(parts2))):
            if i >= len(parts1):
                return -1
            if i >= len(parts2):
                return 1
            
            try:
                v1 = int(parts1[i])
                v2 = int(parts2[i])
                if v1 != v2:
                    return v1 - v2
            except ValueError:
                if parts1[i] != parts2[i]:
                    return -1 if parts1[i] < parts2[i] else 1
        
        return 0
    
    def _create_error_result(self, component: SoftwareComponent, error_msg: str) -> ComponentResult:
        """
        Create error result for failed analysis.
        
        Args:
            component: Component that failed analysis
            error_msg: Error message
            
        Returns:
            ComponentResult with error status
        """
        return ComponentResult(
            component=component,
            compatibility=CompatibilityResult(
                status=CompatibilityStatus.UNKNOWN,
                current_version_supported=False,
                minimum_supported_version=None,
                recommended_version=None,
                notes=f"Analysis failed: {error_msg}",
                confidence_level=0.0
            )
        )
    
    def _get_java_dependencies_from_kb(self) -> Dict:
        """
        Get Java dependencies from knowledge base or load from separate file.
        
        Returns:
            Dictionary with Java dependency compatibility data
        """
        if not self.knowledge_base:
            return self._load_java_dependencies_from_file()
        
        # Try to get runtime dependencies from knowledge base
        try:
            runtime_deps = getattr(self.knowledge_base, 'runtime_dependencies', {})
            if isinstance(runtime_deps, dict):
                java_deps = runtime_deps.get('java', {})
                if java_deps:
                    return java_deps
            
            # Fallback: check if knowledge base has a method to get runtime deps
            if hasattr(self.knowledge_base, 'get_runtime_dependencies'):
                runtime_deps = self.knowledge_base.get_runtime_dependencies()
                java_deps = runtime_deps.get('java', {})
                if java_deps:
                    return java_deps
            
        except Exception as e:
            logger.warning(f"Could not load Java dependencies from knowledge base: {e}")
        
        # Fallback to loading from separate file
        return self._load_java_dependencies_from_file()
    
    def _load_java_dependencies_from_file(self) -> Dict:
        """
        Load Java dependencies from separate JSON file using loader utility.
        
        Returns:
            Dictionary with Java dependency compatibility data
        """
        try:
            from ..knowledge_base.runtime_loader import RuntimeKnowledgeBaseLoader
            loader = RuntimeKnowledgeBaseLoader()
            return loader.load_java_knowledge_base()
        except Exception as e:
            logger.error(f"Error loading Java dependencies from file: {e}")
            return {}

    
    def _check_endianness_issues(self, maven_key: str) -> bool:
        """
        Check if component has potential endianness issues from knowledge base.
        
        Args:
            maven_key: Maven coordinates to check
            
        Returns:
            True if component may have endianness issues
        """
        java_deps = self._get_java_dependencies_from_kb()
        
        # Check if any dependency entry indicates endianness sensitivity
        for dep_key, dep_info in java_deps.items():
            if dep_key == maven_key and dep_info.get('endianness_sensitive', False):
                return True
        
        return False
    
    def _check_memory_alignment_issues(self, maven_key: str) -> bool:
        """
        Check if component has potential memory alignment issues from knowledge base.
        
        Args:
            maven_key: Maven coordinates to check
            
        Returns:
            True if component may have memory alignment issues
        """
        java_deps = self._get_java_dependencies_from_kb()
        
        # Check if any dependency entry indicates memory alignment sensitivity
        for dep_key, dep_info in java_deps.items():
            if dep_key == maven_key and dep_info.get('memory_alignment_sensitive', False):
                return True
        
        return False
    
    def _check_arm_classifiers(self, maven_key: str, current_classifier: str) -> Optional[str]:
        """
        Check if ARM-specific classifiers are available from knowledge base.
        
        Args:
            maven_key: Maven coordinates
            current_classifier: Current classifier (if any)
            
        Returns:
            Suggestion string if ARM classifiers are available
        """
        java_deps = self._get_java_dependencies_from_kb()
        
        if maven_key in java_deps:
            dep_info = java_deps[maven_key]
            available_classifiers = dep_info.get('arm_classifiers', [])
            
            if available_classifiers and (not current_classifier or 
                                        not any(arm_classifier in current_classifier 
                                               for arm_classifier in available_classifiers)):
                return f"Consider using ARM-specific classifier: {', '.join(available_classifiers)}"
        
        return None