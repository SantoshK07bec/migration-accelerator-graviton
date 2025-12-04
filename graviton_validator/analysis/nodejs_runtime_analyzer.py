"""
NodeJS Runtime Compatibility Analyzer

Analyzes NodeJS packages for Graviton compatibility using NPM registry metadata API
and hybrid analysis approach with configurable metadata lookup.
"""

import json
import logging
import requests
from typing import Dict, List, Optional, Set
from urllib.parse import quote

from .runtime_analyzer import RuntimeCompatibilityAnalyzer
from .cache_manager import get_cache_manager
from ..models import SoftwareComponent, ComponentResult, CompatibilityResult, CompatibilityStatus
from ..knowledge_base.runtime_loader import RuntimeKnowledgeBaseLoader
from ..validation.runtime_result_validator import RuntimeResultValidator

logger = logging.getLogger(__name__)


class NodeJSRuntimeAnalyzer(RuntimeCompatibilityAnalyzer):
    """NodeJS runtime compatibility analyzer with NPM registry metadata analysis."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize NodeJS runtime analyzer.
        
        Args:
            config: Configuration dictionary with metadata lookup settings
        """
        self.config = config or {}
        self.metadata_lookup_enabled = self.config.get('metadata_lookup', {}).get('nodejs', True)
        self.offline_mode = self.config.get('offline_mode', False)
        self.npm_registry_url = "https://registry.npmjs.org"
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'graviton-validator/1.0'})
        
        # Initialize cache manager and validator
        self.cache_manager = get_cache_manager()
        self.validator = RuntimeResultValidator()
        
        # Load NodeJS runtime knowledge base
        self.kb_loader = RuntimeKnowledgeBaseLoader()
        self.runtime_kb = self.kb_loader.load_nodejs_knowledge_base()
        
        # Native module indicators
        self.native_module_indicators = {
            'binding.gyp',
            'wscript',
            '.cc',
            '.cpp',
            '.c',
            'node-gyp',
            'prebuild'
        }
        
    def analyze_component(self, component: SoftwareComponent) -> ComponentResult:
        """Analyze NodeJS component for Graviton compatibility.
        
        Args:
            component: NodeJS component to analyze
            
        Returns:
            ComponentResult with compatibility analysis
        """
        logger.debug(f"Analyzing NodeJS component: {component.name}@{component.version}")
        
        # Phase 1: Knowledge Base Analysis (Primary)
        kb_result = self._analyze_with_knowledge_base(component)
        if kb_result.compatibility.status != CompatibilityStatus.UNKNOWN:
            logger.debug(f"Knowledge base analysis complete for {component.name}")
            return kb_result
        else:
            logger.debug(f"Knowledge base analysis returned UNKNOWN for {component.name}: {kb_result.compatibility.notes}")
        
        # Phase 2: Metadata Analysis (Secondary)
        if self.metadata_lookup_enabled and not self.offline_mode:
            logger.debug(f"Starting NPM metadata analysis for {component.name}")
            metadata_result = self._analyze_with_npm_metadata(component)
            if metadata_result.compatibility.status != CompatibilityStatus.UNKNOWN:
                logger.debug(f"Metadata analysis complete for {component.name}")
                return metadata_result
            else:
                logger.debug(f"NPM metadata analysis returned UNKNOWN for {component.name}: {metadata_result.compatibility.notes}")
        else:
            logger.debug(f"NPM metadata lookup disabled for {component.name} (metadata_lookup_enabled={self.metadata_lookup_enabled}, offline_mode={self.offline_mode})")
        
        # Phase 3: Unknown status with recommendation and analysis details
        logger.debug(f"No compatibility information found for {component.name} after all analysis phases")
        
        # Add analysis details for the fallback case
        analysis_details = f"NodeJS analysis: kb_lookup=not_found, npm_lookup={'disabled' if not self.metadata_lookup_enabled or self.offline_mode else 'failed'}, metadata_available=False"
        
        return ComponentResult(
            component=component,
            compatibility=CompatibilityResult(
                status=CompatibilityStatus.UNKNOWN,
                current_version_supported=False,
                minimum_supported_version=None,
                recommended_version=None,
                notes=f"No compatibility information available. Consider testing in ARM64 environment. {analysis_details}"
            )
        )
    
    def _analyze_with_knowledge_base(self, component: SoftwareComponent) -> ComponentResult:
        """Analyze component using runtime knowledge base.
        
        Args:
            component: Component to analyze
            
        Returns:
            ComponentResult from knowledge base analysis
        """
        package_info = self.runtime_kb.get(component.name.lower())
        if not package_info:
            logger.debug(f"Package {component.name} not found in NodeJS knowledge base (searched for: {component.name.lower()})")
            logger.debug(f"Available packages in knowledge base: {list(self.runtime_kb.keys())[:10]}..." if self.runtime_kb else "Knowledge base is empty")
            return ComponentResult(
                component=component,
                compatibility=CompatibilityResult(
                    status=CompatibilityStatus.UNKNOWN,
                    current_version_supported=False,
                    minimum_supported_version=None,
                    recommended_version=None,
                    notes="Package not found in knowledge base"
                )
            )
        else:
            logger.debug(f"Found {component.name} in NodeJS knowledge base with status: {package_info.get('default_status', 'unknown')}")
        
        # Check for invalid/placeholder versions
        version = component.version
        if version and version.lower() in ['unknown', 'vunknown', 'n/a', 'na', 'null', 'none', 'all', '*', '']:
            version = None  # Treat as no version
        
        # Check version compatibility
        version_info = self._check_version_compatibility(version, package_info)
        if version_info:
            return ComponentResult(
                component=component,
                compatibility=CompatibilityResult(
                    status=version_info['status'],
                    current_version_supported=True,
                    minimum_supported_version=None,
                    recommended_version=None,
                    notes=version_info.get('notes', '')
                )
            )
        
        # Check if package has version requirements but no version provided
        if not version or not version.strip():
            has_version_ranges = bool(package_info.get('version_ranges', []))
            min_version = package_info.get('minimum_supported_version')
            
            if has_version_ranges or min_version:
                # Package has version requirements but no version provided
                if min_version:
                    notes = f"Version verification needed - software is Graviton-compatible (min: v{min_version}). Verify your version meets requirements."
                else:
                    notes = "Version verification needed - software is Graviton-compatible. Verify your version meets requirements."
                
                return ComponentResult(
                    component=component,
                    compatibility=CompatibilityResult(
                        status=CompatibilityStatus.NEEDS_VERSION_VERIFICATION,
                        current_version_supported=False,
                        minimum_supported_version=min_version,
                        recommended_version=package_info.get('recommended_version'),
                        notes=notes
                    )
                )
        
        # Handle cases where version couldn't be processed but component is in KB
        if version and package_info.get('minimum_supported_version'):
            # Version format couldn't be processed but we have minimum version info
            min_version = package_info.get('minimum_supported_version')
            return ComponentResult(
                component=component,
                compatibility=CompatibilityResult(
                    status=CompatibilityStatus.NEEDS_VERSION_VERIFICATION,
                    current_version_supported=False,
                    minimum_supported_version=min_version,
                    recommended_version=package_info.get('recommended_version'),
                    notes=f"Version '{version}' format not recognized - software is Graviton-compatible (min: v{min_version}). Verify your version meets requirements."
                )
            )
        
        # Default to package-level compatibility
        return ComponentResult(
            component=component,
            compatibility=CompatibilityResult(
                status=package_info.get('default_status', CompatibilityStatus.UNKNOWN),
                current_version_supported=True,
                minimum_supported_version=None,
                recommended_version=None,
                notes=package_info.get('notes', '')
            )
        )
    
    def _analyze_with_npm_metadata(self, component: SoftwareComponent) -> ComponentResult:
        """Analyze component using NPM registry metadata API with caching.
        
        Args:
            component: Component to analyze
            
        Returns:
            ComponentResult from metadata analysis
        """
        try:
            # Check cache first
            cached_result = self.cache_manager.get_cached('npm', component.name, component.version)
            if cached_result is not None:
                logger.debug(f"Using cached NPM result for {component.name}@{component.version}")
                return self._create_result_from_cached_data(component, cached_result)
            
            # Get package metadata from NPM registry
            logger.debug(f"Fetching NPM metadata for {component.name}")
            package_data = self._fetch_npm_metadata_with_cache(component.name)
            if not package_data:
                # Log API call details for debugging
                logger.debug(f"NPM API call failed for {component.name}@{component.version}")
                logger.debug(f"NPM URL attempted: {self.npm_registry_url}/{quote(component.name)}")
                
                result = ComponentResult(
                    component=component,
                    compatibility=CompatibilityResult(
                        status=CompatibilityStatus.UNKNOWN,
                        current_version_supported=False,
                        minimum_supported_version=None,
                        recommended_version=None,
                        notes="Package metadata not available from NPM registry"
                    )
                )
                # Cache with 24h TTL
                self.cache_manager.set_cached('npm', component.name, {
                    'status': 'unknown',
                    'notes': result.compatibility.notes
                }, component.version, ttl_hours=24)
                return result
            
            # Get specific version metadata
            version_data = None
            if component.version and component.version in package_data.get('versions', {}):
                version_data = package_data['versions'][component.version]
            else:
                # Use latest version if specific version not found
                latest_version = package_data.get('dist-tags', {}).get('latest')
                if latest_version:
                    version_data = package_data.get('versions', {}).get(latest_version)
            
            if not version_data:
                # Log API call details for debugging
                logger.info(f"DEBUG: NPM version data not found for {component.name}@{component.version}")
                logger.info(f"DEBUG: Package has {len(package_data.get('versions', {}))} total versions")
                logger.info(f"DEBUG: Requested version '{component.version}' available: {component.version in package_data.get('versions', {})}")
                
                result = ComponentResult(
                    component=component,
                    compatibility=CompatibilityResult(
                        status=CompatibilityStatus.UNKNOWN,
                        current_version_supported=False,
                        minimum_supported_version=None,
                        recommended_version=None,
                        notes="Version metadata not available"
                    )
                )
                # Cache with 24h TTL
                self.cache_manager.set_cached('npm', component.name, {
                    'status': 'unknown',
                    'notes': result.compatibility.notes
                }, component.version, ttl_hours=24)
                return result
            
            # Check if newer version has ARM64 support
            upgrade_info = self._find_arm64_upgrade_version(package_data, component.version)
            if upgrade_info['has_upgrade']:
                result = ComponentResult(
                    component=component,
                    compatibility=CompatibilityResult(
                        status=CompatibilityStatus.NEEDS_UPGRADE,
                        current_version_supported=False,
                        minimum_supported_version=upgrade_info['min_version'],
                        recommended_version=upgrade_info['recommended_version'],
                        notes=f"ARM64 support available in version {upgrade_info['min_version']} and later. Current version {component.version} requires upgrade."
                    )
                )
                # Cache upgrade result (permanent)
                cache_data = {
                    'status': 'needs_upgrade',
                    'current_version_supported': False,
                    'minimum_supported_version': upgrade_info['min_version'],
                    'recommended_version': upgrade_info['recommended_version'],
                    'notes': result.compatibility.notes
                }
                self.cache_manager.set_cached('npm', component.name, cache_data, component.version)
                return result
            
            # Analyze ARM64 compatibility
            compatibility_result = self._analyze_arm64_compatibility(version_data, component, package_data)
            
            # Cache result based on status
            cache_data = {
                'status': compatibility_result.compatibility.status.value,
                'current_version_supported': compatibility_result.compatibility.current_version_supported,
                'notes': compatibility_result.compatibility.notes
            }
            
            # Use 24h TTL for non-compatible/non-upgrade results
            ttl_hours = None
            if compatibility_result.compatibility.status in [CompatibilityStatus.UNKNOWN]:
                ttl_hours = 24
            
            self.cache_manager.set_cached('npm', component.name, cache_data, component.version, ttl_hours=ttl_hours)
            logger.debug(f"Cached NPM result for {component.name}@{component.version}" + (f" (TTL: {ttl_hours}h)" if ttl_hours else ""))
            
            return compatibility_result
            
        except Exception as e:
            logger.warning(f"NPM metadata analysis failed for {component.name}: {e}")
            result = ComponentResult(
                component=component,
                compatibility=CompatibilityResult(
                    status=CompatibilityStatus.UNKNOWN,
                    current_version_supported=False,
                    minimum_supported_version=None,
                    recommended_version=None,
                    notes=f"Metadata analysis failed: {str(e)}"
                )
            )
            # Cache error result with 24h TTL
            self.cache_manager.set_cached('npm', component.name, {
                'status': 'unknown',
                'notes': result.compatibility.notes
            }, component.version, ttl_hours=24)
            return result
    
    def _create_result_from_cached_data(self, component: SoftwareComponent, cached_data: Dict) -> ComponentResult:
        """Create ComponentResult from cached data."""
        try:
            status = CompatibilityStatus(cached_data['status'])
        except (ValueError, KeyError):
            status = CompatibilityStatus.UNKNOWN
        
        return ComponentResult(
            component=component,
            compatibility=CompatibilityResult(
                status=status,
                current_version_supported=cached_data.get('current_version_supported', False),
                minimum_supported_version=cached_data.get('minimum_supported_version'),
                recommended_version=cached_data.get('recommended_version'),
                notes=cached_data.get('notes', 'From cache')
            )
        )
    
    def _fetch_npm_metadata_with_cache(self, package_name: str) -> Optional[Dict]:
        """Fetch NPM metadata with rate limiting and exponential backoff."""
        # Wait for any active backoff period
        wait_time = self.cache_manager.wait_for_rate_limit('npm')
        if wait_time > 0:
            logger.info(f"Waited {wait_time:.1f}s for NPM rate limit backoff")
        
        # Check if we can make the request after waiting
        if not self.cache_manager.can_make_request('npm'):
            logger.warning(f"Rate limit still exceeded for NPM API after backoff, skipping {package_name}")
            return None
        
        try:
            result = self._fetch_npm_metadata(package_name)
            self.cache_manager.record_request('npm', success=result is not None)
            return result
        except Exception as e:
            self.cache_manager.record_request('npm', success=False)
            raise e
    
    def _fetch_npm_metadata(self, package_name: str) -> Optional[Dict]:
        """Fetch package metadata from NPM registry API.
        
        Args:
            package_name: Name of the package
            
        Returns:
            Package metadata dictionary or None if not found
        """
        try:
            url = f"{self.npm_registry_url}/{quote(package_name)}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.debug(f"Package {package_name} not found on NPM registry")
                return None
            else:
                logger.warning(f"NPM registry returned status {response.status_code} for {package_name}")
                return None
                
        except requests.RequestException as e:
            logger.warning(f"Failed to fetch NPM metadata for {package_name}: {e}")
            return None
    
    def _analyze_arm64_compatibility(self, version_data: Dict, component: SoftwareComponent, package_data: Optional[Dict] = None) -> ComponentResult:
        """Analyze ARM64 compatibility from version metadata.
        
        Args:
            version_data: Version-specific metadata from NPM
            component: Component being analyzed
            
        Returns:
            ComponentResult with compatibility analysis
        """
        # Check CPU architecture support
        cpu_support = self._check_cpu_support(version_data)
        if cpu_support['explicit_arm64_support']:
            return ComponentResult(
                component=component,
                compatibility=CompatibilityResult(
                    status=CompatibilityStatus.COMPATIBLE,
                    current_version_supported=True,
                    minimum_supported_version=None,
                    recommended_version=None,
                    notes="Explicit ARM64 support declared in package metadata"
                )
            )
        
        # Check for native modules
        native_module_info = self._check_native_modules(version_data)
        if native_module_info['has_native_modules']:
            indicators_text = "; ".join(native_module_info['indicators']) if native_module_info['indicators'] else "detected"
            if native_module_info['prebuilt_binaries']:
                return ComponentResult(
                    component=component,
                    compatibility=CompatibilityResult(
                        status=CompatibilityStatus.UNKNOWN,
                        current_version_supported=False,
                        minimum_supported_version=None,
                        recommended_version=None,
                        notes=f"Package has native modules with prebuilt binaries - ARM64 support depends on binary availability. Native module detection: {indicators_text}. NPM analysis: native_modules=True, prebuilt_binaries=True, indicators={native_module_info['indicators']}"
                    )
                )
            else:
                return ComponentResult(
                    component=component,
                    compatibility=CompatibilityResult(
                        status=CompatibilityStatus.UNKNOWN,
                        current_version_supported=False,
                        minimum_supported_version=None,
                        recommended_version=None,
                        notes=f"Package has native modules requiring compilation. Native module detection: {indicators_text}. NPM analysis: native_modules=True, prebuilt_binaries=False, indicators={native_module_info['indicators']}"
                    )
                )
        
        # Pure JavaScript packages are generally compatible
        if self._is_pure_javascript(version_data):
            return ComponentResult(
                component=component,
                compatibility=CompatibilityResult(
                    status=CompatibilityStatus.COMPATIBLE,
                    current_version_supported=True,
                    minimum_supported_version=None,
                    recommended_version=None,
                    notes="Pure JavaScript package - should be compatible with ARM64"
                )
            )
        
        # Log detailed analysis for unknown status debugging
        logger.debug(f"NPM analysis for {component.name}@{component.version} resulted in UNKNOWN status")
        logger.debug(f"Version data available: {bool(version_data)}")
        
        native_info = self._check_native_modules(version_data) if version_data else {}
        cpu_info = self._check_cpu_support(version_data) if version_data else {}
        
        if version_data:
            logger.debug(f"Version data keys: {list(version_data.keys())}")
            logger.debug(f"Dependencies: {list(version_data.get('dependencies', {}).keys())[:5]}")
            logger.debug(f"Scripts: {list(version_data.get('scripts', {}).keys())}")
            logger.debug(f"Native module analysis: {native_info}")
            logger.debug(f"CPU support analysis: {cpu_info}")
        
        analysis_details = f"NPM analysis: native_modules={native_info.get('has_native_modules', False)}, prebuilt_binaries={native_info.get('prebuilt_binaries', False)}, explicit_arm64={cpu_info.get('explicit_arm64_support', False)}, pure_js={self._is_pure_javascript(version_data) if version_data else False}"
        
        return ComponentResult(
            component=component,
            compatibility=CompatibilityResult(
                status=CompatibilityStatus.UNKNOWN,
                current_version_supported=False,
                minimum_supported_version=None,
                recommended_version=None,
                notes=f"Unable to determine ARM64 compatibility from metadata. {analysis_details}"
            )
        )
    
    def _check_cpu_support(self, version_data: Dict) -> Dict[str, any]:
        """Check CPU architecture support from package metadata.
        
        Args:
            version_data: Version metadata
            
        Returns:
            Dictionary with CPU support analysis
        """
        result = {
            'explicit_arm64_support': False,
            'supported_cpus': []
        }
        
        # Check engines.cpu field
        engines = version_data.get('engines', {})
        cpu_field = engines.get('cpu')
        
        if cpu_field:
            if isinstance(cpu_field, list):
                result['supported_cpus'] = cpu_field
                result['explicit_arm64_support'] = any(
                    cpu.lower() in ['arm64', 'aarch64'] for cpu in cpu_field
                )
            elif isinstance(cpu_field, str):
                result['supported_cpus'] = [cpu_field]
                result['explicit_arm64_support'] = cpu_field.lower() in ['arm64', 'aarch64']
        
        # Check os field for additional context
        os_field = engines.get('os')
        if os_field and isinstance(os_field, list):
            # Linux support is a good indicator for potential ARM64 compatibility
            if 'linux' in [os.lower() for os in os_field]:
                result['linux_support'] = True
        
        return result
    
    def _check_native_modules(self, version_data: Dict) -> Dict[str, any]:
        """Check for native module indicators.
        
        Args:
            version_data: Version metadata
            
        Returns:
            Dictionary with native module analysis
        """
        result = {
            'has_native_modules': False,
            'prebuilt_binaries': False,
            'indicators': []
        }
        
        # Check dependencies for native module indicators
        dependencies = version_data.get('dependencies', {})
        dev_dependencies = version_data.get('devDependencies', {})
        all_deps = {**dependencies, **dev_dependencies}
        
        # Check for common native module dependencies
        native_deps = ['node-gyp', 'prebuild', 'prebuild-install', 'node-pre-gyp']
        for dep in native_deps:
            if dep in all_deps:
                result['has_native_modules'] = True
                result['indicators'].append(f"dependency: {dep}")
                if dep in ['prebuild', 'prebuild-install', 'node-pre-gyp']:
                    result['prebuilt_binaries'] = True
        
        # Check scripts for build indicators
        scripts = version_data.get('scripts', {})
        for script_name, script_content in scripts.items():
            if any(indicator in script_content.lower() for indicator in self.native_module_indicators):
                result['has_native_modules'] = True
                result['indicators'].append(f"script: {script_name}")
        
        return result
    
    def _is_pure_javascript(self, version_data: Dict) -> bool:
        """Check if package is pure JavaScript.
        
        Args:
            version_data: Version metadata
            
        Returns:
            True if package appears to be pure JavaScript
        """
        # Check for absence of native module indicators
        native_info = self._check_native_modules(version_data)
        if native_info['has_native_modules']:
            return False
        
        # Check main field points to .js file
        main_file = version_data.get('main', '')
        if main_file and main_file.endswith('.js'):
            return True
        
        # Check for common pure JS indicators
        keywords = version_data.get('keywords', [])
        if isinstance(keywords, list):
            pure_js_keywords = ['javascript', 'js', 'pure', 'browser']
            if any(keyword.lower() in pure_js_keywords for keyword in keywords):
                return True
        
        return True  # Default to pure JS if no native indicators found
    
    def _check_version_compatibility(self, version: str, package_info: Dict) -> Optional[Dict]:
        """Check version-specific compatibility information.
        
        Args:
            version: Package version to check
            package_info: Package information from knowledge base
            
        Returns:
            Version compatibility information or None
        """
        version_ranges = package_info.get('version_ranges', [])
        
        for version_range in version_ranges:
            if self._version_matches_range(version, version_range.get('range', '')):
                return {
                    'status': CompatibilityStatus(version_range.get('status', 'unknown')),
                    'notes': version_range.get('notes', ''),
                    'recommendations': version_range.get('recommendations', [])
                }
        
        return None
    
    def _version_matches_range(self, version: str, version_range: str) -> bool:
        """Check if version matches the specified range.
        
        Args:
            version: Version to check
            version_range: Version range specification (semver)
            
        Returns:
            True if version matches range
        """
        # Simplified version matching - can be enhanced with proper semver
        if not version_range or version_range == '*':
            return True
        
        # If no version provided, can't match any range
        if not version:
            return False
        
        # Handle semver ranges (simplified)
        if version_range.startswith('>='):
            min_version = version_range[2:].strip()
            return self._compare_versions(version, min_version) >= 0
        elif version_range.startswith('>'):
            min_version = version_range[1:].strip()
            return self._compare_versions(version, min_version) > 0
        elif version_range.startswith('<='):
            max_version = version_range[2:].strip()
            return self._compare_versions(version, max_version) <= 0
        elif version_range.startswith('<'):
            max_version = version_range[1:].strip()
            return self._compare_versions(version, max_version) < 0
        elif version_range.startswith('==') or version_range.startswith('='):
            exact_version = version_range.lstrip('=').strip()
            return version == exact_version
        else:
            return version == version_range
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """Simple version comparison.
        
        Args:
            v1: First version
            v2: Second version
            
        Returns:
            -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
        """
        # Remove 'v' prefix if present
        v1 = v1.lstrip('v')
        v2 = v2.lstrip('v')
        
        # Split versions into parts
        parts1 = [int(x) for x in v1.split('.') if x.isdigit()]
        parts2 = [int(x) for x in v2.split('.') if x.isdigit()]
        
        # Pad shorter version with zeros
        max_len = max(len(parts1), len(parts2))
        parts1.extend([0] * (max_len - len(parts1)))
        parts2.extend([0] * (max_len - len(parts2)))
        
        # Compare parts
        for p1, p2 in zip(parts1, parts2):
            if p1 < p2:
                return -1
            elif p1 > p2:
                return 1
        
        return 0
    
    def get_runtime_type(self) -> str:
        """Return the runtime type this analyzer handles."""
        return 'nodejs'
    
    def get_supported_purls(self) -> List[str]:
        """Return list of PURL prefixes this analyzer supports."""
        return ['pkg:npm/']
    
    def _find_arm64_upgrade_version(self, package_data: Dict, current_version: str) -> Dict[str, any]:
        """Find the minimum version that has ARM64 support.
        
        Args:
            package_data: Full package data from NPM
            current_version: Current version being analyzed
            
        Returns:
            Dictionary with upgrade information
        """
        result = {
            'has_upgrade': False,
            'min_version': None,
            'recommended_version': None
        }
        
        if not package_data or 'versions' not in package_data:
            return result
        
        versions = package_data['versions']
        # Sort versions (simple string sort, could be improved with proper semver)
        sorted_versions = sorted(versions.keys())
        
        # Find first version with ARM64 support
        for version in sorted_versions:
            if self._compare_versions(version, current_version) <= 0:
                continue
                
            version_data = versions[version]
            
            # Check CPU architecture support
            cpu_support = self._check_cpu_support(version_data)
            if cpu_support['explicit_arm64_support']:
                result['has_upgrade'] = True
                result['min_version'] = version
                result['recommended_version'] = sorted_versions[-1] if sorted_versions else version
                break
            
            # Check if it's pure JavaScript (also compatible)
            if self._is_pure_javascript(version_data):
                result['has_upgrade'] = True
                result['min_version'] = version
                result['recommended_version'] = sorted_versions[-1] if sorted_versions else version
                break
        
        return result
    
    def get_analyzer_info(self) -> Dict[str, any]:
        """Get analyzer configuration and status information."""
        cache_stats = self.cache_manager.get_cache_stats()
        return {
            'runtime_type': self.get_runtime_type(),
            'metadata_lookup_enabled': self.metadata_lookup_enabled,
            'offline_mode': self.offline_mode,
            'npm_registry_url': self.npm_registry_url,
            'knowledge_base_entries': len(self.runtime_kb) if self.runtime_kb else 0,
            'cache_stats': cache_stats
        }