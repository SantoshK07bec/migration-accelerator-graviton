"""
Python Runtime Compatibility Analyzer

Analyzes Python packages for Graviton compatibility using PyPI metadata API
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

logger = logging.getLogger(__name__)


class PythonRuntimeAnalyzer(RuntimeCompatibilityAnalyzer):
    """Python runtime compatibility analyzer with PyPI metadata analysis."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize Python runtime analyzer.
        
        Args:
            config: Configuration dictionary with metadata lookup settings
        """
        self.config = config or {}
        self.metadata_lookup_enabled = self.config.get('metadata_lookup', {}).get('python', True)
        self.offline_mode = self.config.get('offline_mode', False)
        self.pypi_base_url = "https://pypi.org/pypi"
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'graviton-validator/1.0'})
        
        # Initialize cache manager
        self.cache_manager = get_cache_manager()
        
        # Load Python runtime knowledge base
        self.kb_loader = RuntimeKnowledgeBaseLoader()
        self.runtime_kb = self.kb_loader.load_python_knowledge_base()
        
        # ARM64 wheel indicators
        self.arm64_wheel_patterns = {
            'linux_aarch64',
            'aarch64',
            'arm64'
        }
        
    def analyze_component(self, component: SoftwareComponent) -> ComponentResult:
        """Analyze Python component for Graviton compatibility.
        
        Args:
            component: Python component to analyze
            
        Returns:
            ComponentResult with compatibility analysis
        """
        logger.debug(f"Analyzing Python component: {component.name}@{component.version}")
        
        # Phase 1: Knowledge Base Analysis (Primary)
        kb_result = self._analyze_with_knowledge_base(component)
        if kb_result.compatibility.status != CompatibilityStatus.UNKNOWN:
            logger.debug(f"Knowledge base analysis complete for {component.name}")
            return kb_result
        else:
            logger.debug(f"Knowledge base analysis returned UNKNOWN for {component.name}: {kb_result.compatibility.notes}")
        
        # Phase 2: Metadata Analysis (Secondary)
        if self.metadata_lookup_enabled and not self.offline_mode:
            logger.debug(f"Starting PyPI metadata analysis for {component.name}")
            metadata_result = self._analyze_with_pypi_metadata(component)
            if metadata_result.compatibility.status != CompatibilityStatus.UNKNOWN:
                logger.debug(f"Metadata analysis complete for {component.name}")
                return metadata_result
            else:
                logger.debug(f"PyPI metadata analysis returned UNKNOWN for {component.name}: {metadata_result.compatibility.notes}")
        else:
            logger.debug(f"PyPI metadata lookup disabled for {component.name} (metadata_lookup_enabled={self.metadata_lookup_enabled}, offline_mode={self.offline_mode})")
        
        # Phase 3: Unknown status with recommendation and analysis details
        logger.debug(f"No compatibility information found for {component.name} after all analysis phases")
        
        # Add analysis details for the fallback case
        analysis_details = f"Python analysis: kb_lookup=not_found, pypi_lookup={'disabled' if not self.metadata_lookup_enabled or self.offline_mode else 'failed'}, metadata_available=False"
        
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
            logger.debug(f"Package {component.name} not found in Python knowledge base (searched for: {component.name.lower()})")
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
            logger.debug(f"Found {component.name} in Python knowledge base with status: {package_info.get('default_status', 'unknown')}")
        
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
    
    def _analyze_with_pypi_metadata(self, component: SoftwareComponent) -> ComponentResult:
        """Analyze component using PyPI metadata API with caching.
        
        Args:
            component: Component to analyze
            
        Returns:
            ComponentResult from metadata analysis
        """
        try:
            # Check cache first
            cached_result = self.cache_manager.get_cached('pypi', component.name, component.version)
            if cached_result is not None:
                logger.debug(f"Using cached PyPI result for {component.name}@{component.version}")
                return self._create_result_from_cached_data(component, cached_result)
            
            # Get package metadata from PyPI
            logger.debug(f"Fetching PyPI metadata for {component.name}")
            package_data = self._fetch_pypi_metadata_with_cache(component.name)
            if not package_data:
                # Log API call details for debugging
                logger.debug(f"PyPI API call failed for {component.name}@{component.version}")
                logger.debug(f"PyPI URL attempted: {self.pypi_base_url}/{quote(component.name)}/json")
                
                result = ComponentResult(
                    component=component,
                    compatibility=CompatibilityResult(
                        status=CompatibilityStatus.UNKNOWN,
                        current_version_supported=False,
                        minimum_supported_version=None,
                        recommended_version=None,
                        notes="Package metadata not available from PyPI"
                    )
                )
                # Cache with 24h TTL
                cache_data = {
                    'status': 'unknown',
                    'current_version_supported': False,
                    'notes': result.compatibility.notes
                }
                self.cache_manager.set_cached('pypi', component.name, cache_data, component.version, ttl_hours=24)
                return result
            
            # Check specific version if available
            version_data = None
            releases = package_data.get('releases', {})
            logger.debug(f"PyPI package {component.name} has {len(releases)} releases")
            
            if component.version and component.version in releases:
                version_data = releases[component.version]
                logger.debug(f"Found version {component.version} with {len(version_data)} files")
            else:
                logger.debug(f"Version {component.version} not found in releases. Available versions: {list(releases.keys())[:5]}...")
            
            # Analyze wheel availability for current version
            arm64_support = self._check_arm64_wheel_support(version_data or [])
            logger.debug(f"ARM64 support analysis for {component.name}@{component.version}: {arm64_support}")
            
            if arm64_support['has_arm64_wheels']:
                result = ComponentResult(
                    component=component,
                    compatibility=CompatibilityResult(
                        status=CompatibilityStatus.COMPATIBLE,
                        current_version_supported=True,
                        minimum_supported_version=None,
                        recommended_version=None,
                        notes=f"ARM64 wheels available: {', '.join(arm64_support['wheel_types'])}"
                    )
                )
                # Cache successful result (permanent)
                cache_data = {
                    'status': 'compatible',
                    'current_version_supported': True,
                    'notes': result.compatibility.notes
                }
                self.cache_manager.set_cached('pypi', component.name, cache_data, component.version)
                logger.debug(f"Cached PyPI result for {component.name}@{component.version}")
                return result
            elif arm64_support['has_universal_wheels']:
                result = ComponentResult(
                    component=component,
                    compatibility=CompatibilityResult(
                        status=CompatibilityStatus.COMPATIBLE,
                        current_version_supported=True,
                        minimum_supported_version=None,
                        recommended_version=None,
                        notes="Universal wheels available (compatible with ARM64)"
                    )
                )
                # Cache successful result (permanent)
                cache_data = {
                    'status': 'compatible',
                    'current_version_supported': True,
                    'notes': result.compatibility.notes
                }
                self.cache_manager.set_cached('pypi', component.name, cache_data, component.version)
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
                self.cache_manager.set_cached('pypi', component.name, cache_data, component.version)
                return result
            
            # Handle other cases with 24h TTL
            if arm64_support['has_wheels'] and not arm64_support['has_arm64_wheels']:
                analysis_details = f"ARM64 analysis: has_arm64_wheels={arm64_support['has_arm64_wheels']}, has_universal_wheels={arm64_support['has_universal_wheels']}, has_wheels={arm64_support['has_wheels']}, source_only={arm64_support['source_only']}, wheel_types={arm64_support['wheel_types']}"
                result = ComponentResult(
                    component=component,
                    compatibility=CompatibilityResult(
                        status=CompatibilityStatus.UNKNOWN,
                        current_version_supported=False,
                        minimum_supported_version=None,
                        recommended_version=None,
                        notes=f"Package has wheels but no ARM64-specific wheels. Native module detection: platform-specific wheels detected. Verify ARM64 wheel availability or test compilation. {analysis_details}"
                    )
                )
                # Cache with 24h TTL
                cache_data = {
                    'status': 'unknown',
                    'current_version_supported': False,
                    'notes': result.compatibility.notes
                }
                self.cache_manager.set_cached('pypi', component.name, cache_data, component.version, ttl_hours=24)
                return result
            elif arm64_support['source_only']:
                analysis_details = f"ARM64 analysis: has_arm64_wheels={arm64_support['has_arm64_wheels']}, has_universal_wheels={arm64_support['has_universal_wheels']}, has_wheels={arm64_support['has_wheels']}, source_only={arm64_support['source_only']}, wheel_types={arm64_support['wheel_types']}"
                result = ComponentResult(
                    component=component,
                    compatibility=CompatibilityResult(
                        status=CompatibilityStatus.UNKNOWN,
                        current_version_supported=False,
                        minimum_supported_version=None,
                        recommended_version=None,
                        notes=f"Source distribution only - requires compilation. Native module detection: source-only package. Test compilation on ARM64 environment. {analysis_details}"
                    )
                )
                # Cache with 24h TTL
                cache_data = {
                    'status': 'unknown',
                    'current_version_supported': False,
                    'notes': result.compatibility.notes
                }
                self.cache_manager.set_cached('pypi', component.name, cache_data, component.version, ttl_hours=24)
                return result
            
            # Log detailed analysis for unknown status debugging
            logger.debug(f"PyPI analysis for {component.name}@{component.version} resulted in UNKNOWN status")
            logger.debug(f"Package data available: {bool(package_data)}")
            if package_data:
                logger.debug(f"Package data keys: {list(package_data.keys())}")
                if 'releases' in package_data:
                    releases = package_data['releases']
                    logger.debug(f"Total releases available: {len(releases)}")
                    if component.version in releases:
                        files = releases[component.version]
                        logger.debug(f"Version {component.version} has {len(files)} files")
                        for i, file_info in enumerate(files[:3]):  # Log first 3 files
                            logger.debug(f"File {i+1}: {file_info.get('filename', 'unknown')} (type: {file_info.get('packagetype', 'unknown')})")
                    else:
                        logger.debug(f"Version {component.version} not in releases. Available: {sorted(list(releases.keys()))[:10]}")
            logger.debug(f"Final ARM64 support decision: {arm64_support}")
            
            analysis_details = f"ARM64 analysis: has_arm64_wheels={arm64_support['has_arm64_wheels']}, has_universal_wheels={arm64_support['has_universal_wheels']}, has_wheels={arm64_support['has_wheels']}, source_only={arm64_support['source_only']}, wheel_types={arm64_support['wheel_types']}"
            result = ComponentResult(
                component=component,
                compatibility=CompatibilityResult(
                    status=CompatibilityStatus.UNKNOWN,
                    current_version_supported=False,
                    minimum_supported_version=None,
                    recommended_version=None,
                    notes=f"Unable to determine ARM64 compatibility from metadata. {analysis_details}"
                )
            )
            # Cache with 24h TTL
            cache_data = {
                'status': 'unknown',
                'current_version_supported': False,
                'notes': result.compatibility.notes
            }
            self.cache_manager.set_cached('pypi', component.name, cache_data, component.version, ttl_hours=24)
            return result
            
        except Exception as e:
            logger.warning(f"PyPI metadata analysis failed for {component.name}: {e}")
            return ComponentResult(
                component=component,
                compatibility=CompatibilityResult(
                    status=CompatibilityStatus.UNKNOWN,
                    current_version_supported=False,
                    minimum_supported_version=None,
                    recommended_version=None,
                    notes=f"Metadata analysis failed: {str(e)}"
                )
            )
    
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
    
    def _fetch_pypi_metadata_with_cache(self, package_name: str) -> Optional[Dict]:
        """Fetch PyPI metadata with rate limiting and exponential backoff."""
        # Wait for any active backoff period
        wait_time = self.cache_manager.wait_for_rate_limit('pypi')
        if wait_time > 0:
            logger.debug(f"Waited {wait_time:.1f}s for PyPI rate limit backoff")
        
        # Check if we can make the request after waiting
        if not self.cache_manager.can_make_request('pypi'):
            logger.debug(f"Rate limit exceeded for PyPI API, skipping {package_name}")
            return None
        
        try:
            result = self._fetch_pypi_metadata(package_name)
            self.cache_manager.record_request('pypi', success=result is not None)
            return result
        except Exception as e:
            self.cache_manager.record_request('pypi', success=False)
            raise e
    
    def _fetch_pypi_metadata(self, package_name: str) -> Optional[Dict]:
        """Fetch package metadata from PyPI API.
        
        Args:
            package_name: Name of the package
            
        Returns:
            Package metadata dictionary or None if not found
        """
        try:
            url = f"{self.pypi_base_url}/{quote(package_name)}/json"
            logger.debug(f"Making PyPI API call: {url}")
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                logger.debug(f"PyPI API success for {package_name}: {len(data.get('releases', {}))} releases found")
                return data
            elif response.status_code == 404:
                logger.debug(f"Package {package_name} not found on PyPI (404)")
                return None
            else:
                logger.debug(f"PyPI API returned status {response.status_code} for {package_name}")
                return None
                
        except requests.RequestException as e:
            logger.debug(f"PyPI API request failed for {package_name}: {e}")
            return None
    
    def _check_arm64_wheel_support(self, release_files: List[Dict]) -> Dict[str, any]:
        """Check ARM64 wheel support from release files.
        
        Args:
            release_files: List of release file metadata
            
        Returns:
            Dictionary with ARM64 support analysis
        """
        result = {
            'has_arm64_wheels': False,
            'has_universal_wheels': False,
            'has_wheels': False,
            'source_only': False,
            'wheel_types': set(),
            'file_analysis': []  # For debugging
        }
        
        if not release_files:
            logger.debug("No release files to analyze for ARM64 support")
            return result
        
        logger.debug(f"Analyzing {len(release_files)} release files for ARM64 support")
        
        for file_info in release_files:
            filename = file_info.get('filename', '')
            packagetype = file_info.get('packagetype', '')
            
            file_analysis = {
                'filename': filename,
                'packagetype': packagetype,
                'is_arm64': False,
                'is_universal': False
            }
            
            if packagetype == 'bdist_wheel':
                # Check for ARM64-specific wheels
                arm64_match = any(pattern in filename.lower() for pattern in self.arm64_wheel_patterns)
                if arm64_match:
                    result['has_arm64_wheels'] = True
                    result['wheel_types'].add('arm64')
                    file_analysis['is_arm64'] = True
                    logger.debug(f"Found ARM64 wheel: {filename}")
                
                # Check for universal wheels (any-any or pure Python)
                universal_patterns = ['py2.py3-none-any', 'py3-none-any', 'py2-none-any', '-none-any']
                universal_match = any(pattern in filename for pattern in universal_patterns)
                if universal_match:
                    result['has_universal_wheels'] = True
                    result['wheel_types'].add('universal')
                    file_analysis['is_universal'] = True
                    logger.debug(f"Found universal wheel: {filename}")
                
                # Track that we have some wheels (even if not ARM64-specific)
                result['has_wheels'] = True
                logger.debug(f"Found wheel: {filename}")
                    
            elif packagetype == 'sdist':
                result['source_only'] = True
                logger.debug(f"Found source distribution: {filename}")
            
            result['file_analysis'].append(file_analysis)
        
        # Convert set to list for JSON serialization
        result['wheel_types'] = list(result['wheel_types'])
        
        logger.debug(f"ARM64 analysis complete: arm64_wheels={result['has_arm64_wheels']}, universal_wheels={result['has_universal_wheels']}, has_wheels={result['has_wheels']}, source_only={result['source_only']}")
        
        return result
    
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
            version_range: Version range specification
            
        Returns:
            True if version matches range
        """
        # Simplified version matching - can be enhanced with proper semver
        if not version_range or version_range == '*':
            return True
        
        # If no version provided, can't match any range
        if not version:
            return False
        
        if version_range.startswith('>='):
            min_version = version_range[2:].strip()
            return version >= min_version
        elif version_range.startswith('>'):
            min_version = version_range[1:].strip()
            return version > min_version
        elif version_range.startswith('<='):
            max_version = version_range[2:].strip()
            return version <= max_version
        elif version_range.startswith('<'):
            max_version = version_range[1:].strip()
            return version < max_version
        elif version_range.startswith('=='):
            exact_version = version_range[2:].strip()
            return version == exact_version
        else:
            return version == version_range
    
    def get_runtime_type(self) -> str:
        """Return the runtime type this analyzer handles."""
        return 'python'
    
    def get_supported_purls(self) -> List[str]:
        """Return list of PURL prefixes this analyzer supports."""
        return ['pkg:pypi/']
    
    def _find_arm64_upgrade_version(self, package_data: Dict, current_version: str) -> Dict[str, any]:
        """Find the minimum version that has ARM64 support.
        
        Args:
            package_data: Full package data from PyPI
            current_version: Current version being analyzed
            
        Returns:
            Dictionary with upgrade information
        """
        result = {
            'has_upgrade': False,
            'min_version': None,
            'recommended_version': None
        }
        
        releases = package_data.get('releases', {})
        if not releases:
            return result
        
        # Sort versions (simple string sort, could be improved with proper semver)
        sorted_versions = sorted(releases.keys())
        
        # Find first version with ARM64 support
        for version in sorted_versions:
            if version <= current_version:
                continue
                
            version_files = releases[version]
            arm64_support = self._check_arm64_wheel_support(version_files)
            
            if arm64_support['has_arm64_wheels'] or arm64_support['has_universal_wheels']:
                result['has_upgrade'] = True
                result['min_version'] = version
                # Use latest version as recommended
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
            'pypi_base_url': self.pypi_base_url,
            'knowledge_base_entries': len(self.runtime_kb) if self.runtime_kb else 0,
            'cache_stats': cache_stats
        }