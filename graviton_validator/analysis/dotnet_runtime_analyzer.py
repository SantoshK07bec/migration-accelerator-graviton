"""
.NET Runtime Compatibility Analyzer

Analyzes .NET packages for Graviton compatibility using NuGet API metadata
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


class DotNetRuntimeAnalyzer(RuntimeCompatibilityAnalyzer):
    """.NET runtime compatibility analyzer with NuGet API metadata analysis."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize .NET runtime analyzer.
        
        Args:
            config: Configuration dictionary with metadata lookup settings
        """
        self.config = config or {}
        self.metadata_lookup_enabled = self.config.get('metadata_lookup', {}).get('dotnet', True)
        self.offline_mode = self.config.get('offline_mode', False)
        self.nuget_api_url = "https://api.nuget.org/v3-flatcontainer"
        self.nuget_search_url = "https://azuresearch-usnc.nuget.org/query"
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'graviton-validator/1.0'})
        
        # Initialize cache manager
        self.cache_manager = get_cache_manager()
        
        # Load .NET runtime knowledge base
        self.kb_loader = RuntimeKnowledgeBaseLoader()
        self.runtime_kb = self.kb_loader.load_dotnet_knowledge_base()
        
        # ARM64 runtime identifiers
        self.arm64_rids = {
            'linux-arm64',
            'osx-arm64',
            'win-arm64',
            'any'
        }
        
        # .NET target frameworks that support ARM64
        self.arm64_frameworks = {
            'net5.0', 'net6.0', 'net7.0', 'net8.0',
            'netcoreapp3.0', 'netcoreapp3.1',
            'netstandard2.0', 'netstandard2.1'
        }
        
    def analyze_component(self, component: SoftwareComponent) -> ComponentResult:
        """Analyze .NET component for Graviton compatibility.
        
        Args:
            component: .NET component to analyze
            
        Returns:
            ComponentResult with compatibility analysis
        """
        logger.debug(f"Analyzing .NET component: {component.name}@{component.version}")
        
        # Phase 1: Knowledge Base Analysis (Primary)
        kb_result = self._analyze_with_knowledge_base(component)
        if kb_result.compatibility.status != CompatibilityStatus.UNKNOWN:
            logger.debug(f"Knowledge base analysis complete for {component.name}")
            return kb_result
        else:
            logger.debug(f"Knowledge base analysis returned UNKNOWN for {component.name}: {kb_result.compatibility.notes}")
        
        # Check if KB had meaningful information even with UNKNOWN status
        kb_has_info = (kb_result.compatibility.notes and 
                      kb_result.compatibility.notes != "Package not found in knowledge base")
        
        # Phase 2: Metadata Analysis (Secondary)
        if self.metadata_lookup_enabled and not self.offline_mode and not kb_has_info:
            logger.debug(f"Starting NuGet metadata analysis for {component.name}")
            metadata_result = self._analyze_with_nuget_metadata(component)
            if metadata_result.compatibility.status != CompatibilityStatus.UNKNOWN:
                logger.debug(f"Metadata analysis complete for {component.name}")
                return metadata_result
            else:
                logger.debug(f"NuGet metadata analysis returned UNKNOWN for {component.name}: {metadata_result.compatibility.notes}")
        else:
            logger.debug(f"NuGet metadata lookup disabled for {component.name} (metadata_lookup_enabled={self.metadata_lookup_enabled}, offline_mode={self.offline_mode}, kb_has_info={kb_has_info})")
        
        # Phase 3: Return KB result if it has meaningful info, otherwise default unknown
        if kb_has_info:
            logger.debug(f"Knowledge base analysis complete for {component.name} (with UNKNOWN status but meaningful notes)")
            return kb_result
        
        logger.debug(f"No compatibility information found for {component.name} after all analysis phases")
        
        # Add analysis details for the fallback case
        analysis_details = f".NET analysis: kb_lookup=not_found, nuget_lookup={'disabled' if not self.metadata_lookup_enabled or self.offline_mode else 'failed'}, metadata_available=False"
        
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
        package_info = self.runtime_kb.get(component.name) or self.runtime_kb.get(component.name.lower())
        if not package_info:
            logger.debug(f"Package {component.name} not found in .NET knowledge base (searched for: {component.name}, {component.name.lower()})")
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
            logger.debug(f"Found {component.name} in .NET knowledge base with status: {package_info.get('default_status', 'unknown')}")
        
        # Check for invalid/placeholder versions
        version = component.version
        if version and version.lower() in ['unknown', 'vunknown', 'n/a', 'na', 'null', 'none', 'all', '*', '']:
            version = None  # Treat as no version
        
        # Check version compatibility
        version_info = self._check_version_compatibility(version, package_info)
        if version_info:
            # Ensure status is a CompatibilityStatus enum
            status = version_info['status']
            if isinstance(status, str):
                try:
                    status = CompatibilityStatus(status)
                except ValueError:
                    logger.warning(f"Invalid status string '{status}' for {component.name}, defaulting to UNKNOWN")
                    status = CompatibilityStatus.UNKNOWN
            
            return ComponentResult(
                component=component,
                compatibility=CompatibilityResult(
                    status=status,
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
        default_status = package_info.get('default_status', CompatibilityStatus.UNKNOWN)
        if isinstance(default_status, str):
            try:
                default_status = CompatibilityStatus(default_status)
            except ValueError:
                logger.warning(f"Invalid default status string '{default_status}' for {component.name}, using UNKNOWN")
                default_status = CompatibilityStatus.UNKNOWN
        
        return ComponentResult(
            component=component,
            compatibility=CompatibilityResult(
                status=default_status,
                current_version_supported=True,
                minimum_supported_version=None,
                recommended_version=None,
                notes=package_info.get('notes', '')
            )
        )
    
    def _analyze_with_nuget_metadata(self, component: SoftwareComponent) -> ComponentResult:
        """Analyze component using NuGet API metadata with caching.
        
        Args:
            component: Component to analyze
            
        Returns:
            ComponentResult from metadata analysis
        """
        try:
            # Check cache first
            cached_result = self.cache_manager.get_cached('nuget', component.name, component.version)
            if cached_result is not None:
                logger.debug(f"Using cached NuGet result for {component.name}@{component.version}")
                return self._create_result_from_cached_data(component, cached_result)
            
            logger.debug(f"Fetching NuGet metadata for {component.name}@{component.version}")
            # Get package metadata from NuGet API
            package_data = self._fetch_nuget_metadata_with_cache(component.name, component.version)
            
            if not package_data:
                logger.debug(f"No package data returned for {component.name}")
                # Log API call details for debugging
                logger.info(f"DEBUG: NuGet API call failed for {component.name}@{component.version}")
                logger.info(f"DEBUG: NuGet URLs attempted: {self.nuget_api_url}/{component.name.lower()}/index.json")
                
                result = ComponentResult(
                    component=component,
                    compatibility=CompatibilityResult(
                        status=CompatibilityStatus.UNKNOWN,
                        current_version_supported=False,
                        minimum_supported_version=None,
                        recommended_version=None,
                        notes="Package metadata not available from NuGet API"
                    )
                )
                # Cache negative result with 24h TTL
                self.cache_manager.set_cached('nuget', component.name, {
                    'status': 'unknown',
                    'notes': 'Package not found on NuGet'
                }, component.version, ttl_hours=24)
                return result
            
            logger.debug(f"Analyzing ARM64 compatibility for {component.name}")
            # Analyze ARM64 compatibility
            compatibility_result = self._analyze_arm64_compatibility(package_data, component)
            
            # Cache result based on status
            cache_data = {
                'status': compatibility_result.compatibility.status.value,
                'current_version_supported': compatibility_result.compatibility.current_version_supported,
                'notes': compatibility_result.compatibility.notes,
                'package_data': package_data
            }
            
            # Use 24h TTL for non-compatible/non-upgrade results
            ttl_hours = None
            if compatibility_result.compatibility.status in [CompatibilityStatus.UNKNOWN, CompatibilityStatus.NEEDS_VERIFICATION]:
                ttl_hours = 24
            
            self.cache_manager.set_cached('nuget', component.name, cache_data, component.version, ttl_hours=ttl_hours)
            logger.debug(f"Cached NuGet result for {component.name}@{component.version}" + (f" (TTL: {ttl_hours}h)" if ttl_hours else ""))
            
            return compatibility_result
            
        except Exception as e:
            logger.error(f"NuGet metadata analysis failed for {component.name}: {e}", exc_info=True)
            self.cache_manager.record_request('nuget', success=False)
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
            self.cache_manager.set_cached('nuget', component.name, {
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
    
    def _fetch_nuget_metadata_with_cache(self, package_name: str, version: Optional[str] = None) -> Optional[Dict]:
        """Fetch NuGet metadata with rate limiting and exponential backoff."""
        # Wait for any active backoff period or rate limit window
        wait_time = self.cache_manager.wait_for_rate_limit('nuget')
        if wait_time > 0:
            logger.info(f"Waited {wait_time:.1f}s for NuGet rate limit backoff")
        
        # Check if we can make the request after waiting
        if not self.cache_manager.can_make_request('nuget'):
            logger.warning(f"Rate limit still exceeded for NuGet API after waiting, skipping {package_name}")
            return None
        
        try:
            result = self._fetch_nuget_metadata(package_name, version)
            self.cache_manager.record_request('nuget', success=result is not None)
            return result
        except Exception as e:
            self.cache_manager.record_request('nuget', success=False)
            raise e
    
    def _fetch_nuget_metadata(self, package_name: str, version: Optional[str] = None) -> Optional[Dict]:
        """Fetch package metadata from NuGet API.
        
        Args:
            package_name: Name of the package
            version: Specific version to fetch (optional)
            
        Returns:
            Package metadata dictionary or None if not found
        """
        try:
            logger.debug(f"Fetching versions for {package_name} from NuGet API")
            # First try to get package versions
            versions_url = f"{self.nuget_api_url}/{package_name.lower()}/index.json"
            response = self.session.get(versions_url, timeout=10)
            
            logger.debug(f"NuGet versions API response for {package_name}: status={response.status_code}")
            
            if response.status_code != 200:
                logger.debug(f"Package {package_name} not found on NuGet (status: {response.status_code})")
                logger.debug(f"Response content: {response.text[:200]}")
                return None
            
            try:
                versions_data = response.json()
                logger.debug(f"Versions data type for {package_name}: {type(versions_data)}")
            except Exception as json_error:
                logger.error(f"Failed to parse JSON response for {package_name}: {json_error}")
                logger.debug(f"Raw response: {response.text[:500]}")
                return None
            
            available_versions = versions_data.get('versions', [])
            logger.debug(f"Available versions for {package_name}: {len(available_versions)} versions")
            
            if not available_versions:
                logger.debug(f"No versions found for {package_name}")
                return None
            
            # Use specified version or latest
            target_version = version if version in available_versions else available_versions[-1]
            logger.debug(f"Using version {target_version} for {package_name}")
            
            # Get package manifest (.nuspec)
            logger.debug(f"Fetching manifest for {package_name}@{target_version}")
            manifest_url = f"{self.nuget_api_url}/{package_name.lower()}/{target_version}/{package_name.lower()}.nuspec"
            manifest_response = self.session.get(manifest_url, timeout=10)
            
            if manifest_response.status_code == 200:
                return {
                    'versions': available_versions,
                    'target_version': target_version,
                    'manifest': manifest_response.text,
                    'package_name': package_name
                }
            
            # Fallback to search API for basic metadata
            return self._fetch_nuget_search_metadata(package_name)
                
        except requests.RequestException as e:
            logger.error(f"Request failed for NuGet metadata {package_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching NuGet metadata for {package_name}: {e}", exc_info=True)
            return None
    
    def _fetch_nuget_search_metadata(self, package_name: str) -> Optional[Dict]:
        """Fetch package metadata from NuGet search API.
        
        Args:
            package_name: Name of the package
            
        Returns:
            Package metadata from search API
        """
        try:
            params = {
                'q': f'packageid:{package_name}',
                'take': 1
            }
            response = self.session.get(self.nuget_search_url, params=params, timeout=10)
            
            if response.status_code == 200:
                search_data = response.json()
                data = search_data.get('data', [])
                if data:
                    return data[0]
            
            return None
            
        except requests.RequestException as e:
            logger.warning(f"Failed to fetch NuGet search metadata for {package_name}: {e}")
            return None
    
    def _analyze_arm64_compatibility(self, package_data: Dict, component: SoftwareComponent) -> ComponentResult:
        """Analyze ARM64 compatibility from package metadata.
        
        Args:
            package_data: Package metadata from NuGet
            component: Component being analyzed
            
        Returns:
            ComponentResult with compatibility analysis
        """
        # Validate package_data is a dictionary
        if not isinstance(package_data, dict):
            logger.warning(f"Invalid package data type for {component.name}: expected dict, got {type(package_data)}")
            return ComponentResult(
                component=component,
                compatibility=CompatibilityResult(
                    status=CompatibilityStatus.UNKNOWN,
                    current_version_supported=False,
                    minimum_supported_version=None,
                    recommended_version=None,
                    notes="Invalid metadata format from NuGet API"
                )
            )
        
        # Check target frameworks
        framework_support = self._check_framework_support(package_data)
        if framework_support['has_arm64_frameworks']:
            return ComponentResult(
                component=component,
                compatibility=CompatibilityResult(
                    status=CompatibilityStatus.COMPATIBLE,
                    current_version_supported=True,
                    minimum_supported_version=None,
                    recommended_version=None,
                    notes=f"Supports ARM64-compatible frameworks: {', '.join(framework_support['arm64_frameworks'])}"
                )
            )
        
        # Check runtime identifiers in manifest
        rid_support = self._check_runtime_identifiers(package_data)
        if rid_support['has_arm64_rids']:
            return ComponentResult(
                component=component,
                compatibility=CompatibilityResult(
                    status=CompatibilityStatus.COMPATIBLE,
                    current_version_supported=True,
                    minimum_supported_version=None,
                    recommended_version=None,
                    notes=f"Explicit ARM64 runtime identifiers: {', '.join(rid_support['arm64_rids'])}"
                )
            )
        
        # Check for native dependencies
        native_deps = self._check_native_dependencies(package_data)
        if native_deps['has_native_deps']:
            indicators_text = "; ".join(native_deps['native_indicators']) if native_deps['native_indicators'] else "detected"
            return ComponentResult(
                component=component,
                compatibility=CompatibilityResult(
                    status=CompatibilityStatus.NEEDS_VERIFICATION,
                    current_version_supported=False,
                    minimum_supported_version=None,
                    recommended_version=None,
                    notes=f"Package has native dependencies - ARM64 support depends on native library availability. Native module detection: {indicators_text}. NuGet analysis: native_deps=True, indicators={native_deps['native_indicators']}"
                )
            )
        
        # Check if it's a pure managed assembly
        if self._is_pure_managed(package_data):
            return ComponentResult(
                component=component,
                compatibility=CompatibilityResult(
                    status=CompatibilityStatus.COMPATIBLE,
                    current_version_supported=True,
                    minimum_supported_version=None,
                    recommended_version=None,
                    notes="Pure managed .NET assembly - should be compatible with ARM64"
                )
            )
        
        # Log detailed analysis for unknown status debugging
        logger.debug(f"NuGet analysis for {component.name}@{component.version} resulted in UNKNOWN status")
        logger.debug(f"Package data available: {bool(package_data)}")
        
        framework_info = self._check_framework_support(package_data) if package_data else {}
        rid_info = self._check_runtime_identifiers(package_data) if package_data else {}
        native_info = self._check_native_dependencies(package_data) if package_data else {}
        
        if package_data:
            logger.debug(f"Package data keys: {list(package_data.keys())}")
            logger.debug(f"Available versions: {len(package_data.get('versions', []))} versions")
            logger.debug(f"Target version: {package_data.get('target_version', 'unknown')}")
            logger.debug(f"Framework analysis: {framework_info}")
            logger.debug(f"Runtime ID analysis: {rid_info}")
            logger.debug(f"Native dependency analysis: {native_info}")
        
        analysis_details = f"NuGet analysis: arm64_frameworks={framework_info.get('has_arm64_frameworks', False)}, arm64_rids={rid_info.get('has_arm64_rids', False)}, native_deps={native_info.get('has_native_deps', False)}, pure_managed={self._is_pure_managed(package_data) if package_data else False}"
        
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
    
    def _check_framework_support(self, package_data: Dict) -> Dict[str, any]:
        """Check target framework support for ARM64.
        
        Args:
            package_data: Package metadata
            
        Returns:
            Dictionary with framework support analysis
        """
        result = {
            'has_arm64_frameworks': False,
            'arm64_frameworks': [],
            'all_frameworks': []
        }
        
        # Validate input
        if not isinstance(package_data, dict):
            return result
        
        # Extract frameworks from search API data
        if 'versions' in package_data and isinstance(package_data['versions'], list):
            for version_info in package_data['versions']:
                # Handle case where version_info might be a string instead of dict
                if not isinstance(version_info, dict):
                    logger.debug(f"Skipping non-dict version_info: {type(version_info)} - {version_info}")
                    continue
                    
                frameworks = version_info.get('frameworks', [])
                for framework in frameworks:
                    if isinstance(framework, dict):
                        framework_name = framework.get('framework', '').lower()
                    else:
                        framework_name = str(framework).lower()
                    result['all_frameworks'].append(framework_name)
                    
                    if any(arm64_fw in framework_name for arm64_fw in self.arm64_frameworks):
                        result['has_arm64_frameworks'] = True
                        result['arm64_frameworks'].append(framework_name)
        
        # Also check direct frameworks field
        frameworks = package_data.get('frameworks', [])
        if isinstance(frameworks, list):
            for framework in frameworks:
                if isinstance(framework, dict):
                    framework_name = framework.get('framework', '').lower()
                else:
                    framework_name = str(framework).lower()
                result['all_frameworks'].append(framework_name)
                
                if any(arm64_fw in framework_name for arm64_fw in self.arm64_frameworks):
                    result['has_arm64_frameworks'] = True
                    result['arm64_frameworks'].append(framework_name)
        
        # Remove duplicates
        result['arm64_frameworks'] = list(set(result['arm64_frameworks']))
        result['all_frameworks'] = list(set(result['all_frameworks']))
        
        return result
    
    def _check_runtime_identifiers(self, package_data: Dict) -> Dict[str, any]:
        """Check runtime identifiers for ARM64 support.
        
        Args:
            package_data: Package metadata
            
        Returns:
            Dictionary with RID support analysis
        """
        result = {
            'has_arm64_rids': False,
            'arm64_rids': [],
            'all_rids': []
        }
        
        # Validate input
        if not isinstance(package_data, dict):
            return result
        
        # Parse manifest XML for runtime identifiers (simplified)
        manifest = package_data.get('manifest', '')
        if manifest:
            # Look for runtime identifiers in manifest
            import re
            rid_pattern = r'<RuntimeIdentifiers?>(.*?)</RuntimeIdentifiers?>'
            rid_matches = re.findall(rid_pattern, manifest, re.IGNORECASE | re.DOTALL)
            
            for match in rid_matches:
                rids = [rid.strip() for rid in match.split(';') if rid.strip()]
                result['all_rids'].extend(rids)
                
                for rid in rids:
                    if any(arm64_rid in rid.lower() for arm64_rid in self.arm64_rids):
                        result['has_arm64_rids'] = True
                        result['arm64_rids'].append(rid)
        
        # Remove duplicates
        result['arm64_rids'] = list(set(result['arm64_rids']))
        result['all_rids'] = list(set(result['all_rids']))
        
        return result
    
    def _check_native_dependencies(self, package_data: Dict) -> Dict[str, any]:
        """Check for native dependencies.
        
        Args:
            package_data: Package metadata
            
        Returns:
            Dictionary with native dependency analysis
        """
        result = {
            'has_native_deps': False,
            'native_indicators': []
        }
        
        # Validate input
        if not isinstance(package_data, dict):
            return result
        
        # Check package tags for native indicators
        tags = package_data.get('tags', [])
        if isinstance(tags, list):
            native_tags = ['native', 'pinvoke', 'interop', 'unmanaged']
            for tag in tags:
                if any(native_tag in tag.lower() for native_tag in native_tags):
                    result['has_native_deps'] = True
                    result['native_indicators'].append(f"tag: {tag}")
        
        # Check description for native indicators
        description = package_data.get('description', '').lower()
        native_keywords = ['native', 'p/invoke', 'interop', 'unmanaged', 'dll']
        for keyword in native_keywords:
            if keyword in description:
                result['has_native_deps'] = True
                result['native_indicators'].append(f"description: {keyword}")
                break
        
        return result
    
    def _is_pure_managed(self, package_data: Dict) -> bool:
        """Check if package is pure managed code.
        
        Args:
            package_data: Package metadata
            
        Returns:
            True if package appears to be pure managed code
        """
        # Validate input
        if not isinstance(package_data, dict):
            return True  # Default to managed if invalid data
        
        # Check for absence of native dependencies
        native_deps = self._check_native_dependencies(package_data)
        if native_deps['has_native_deps']:
            return False
        
        # Check target frameworks - modern frameworks are good indicators
        framework_support = self._check_framework_support(package_data)
        if framework_support['has_arm64_frameworks']:
            return True
        
        # Check for managed code indicators
        tags = package_data.get('tags', [])
        if isinstance(tags, list):
            managed_tags = ['managed', 'dotnet', 'csharp', 'vb.net']
            if any(tag.lower() in managed_tags for tag in tags):
                return True
        
        return True  # Default to managed if no native indicators
    
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
        # Simplified version matching for .NET versions
        if not version_range or version_range == '*':
            return True
        
        # If no version provided, can't match any range
        if not version:
            return False
        
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
        """Simple version comparison for .NET versions.
        
        Args:
            v1: First version
            v2: Second version
            
        Returns:
            -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
        """
        # Handle .NET version formats (e.g., 1.0.0, 2.1.3-preview)
        def parse_version(v):
            # Remove pre-release suffixes
            v = v.split('-')[0]
            return [int(x) for x in v.split('.') if x.isdigit()]
        
        parts1 = parse_version(v1)
        parts2 = parse_version(v2)
        
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
        return 'dotnet'
    
    def get_supported_purls(self) -> List[str]:
        """Return list of PURL prefixes this analyzer supports."""
        return ['pkg:nuget/']
    
    def analyze_components_batch(self, components: List[SoftwareComponent]) -> List[ComponentResult]:
        """Analyze multiple components with batch optimization.
        
        Args:
            components: List of components to analyze
            
        Returns:
            List of ComponentResults
        """
        results = []
        
        # Separate components by analysis method needed
        kb_components = []
        api_components = []
        
        for component in components:
            # Check knowledge base first
            kb_result = self._analyze_with_knowledge_base(component)
            if kb_result.compatibility.status != CompatibilityStatus.UNKNOWN:
                results.append(kb_result)
            else:
                # Check if KB had meaningful info
                kb_has_info = (kb_result.compatibility.notes and 
                             kb_result.compatibility.notes != "Package not found in knowledge base")
                
                if kb_has_info:
                    results.append(kb_result)
                elif self.metadata_lookup_enabled and not self.offline_mode:
                    api_components.append(component)
                else:
                    results.append(kb_result)
        
        # Process API components in batches
        if api_components:
            logger.info(f"Processing {len(api_components)} components via NuGet API")
            
            # Get components that need API lookup (not cached)
            package_names = [comp.name for comp in api_components]
            uncached_packages = self.cache_manager.get_batch_candidates('nuget', package_names)
            
            if uncached_packages:
                logger.info(f"Fetching metadata for {len(uncached_packages)} uncached packages")
            
            # Process each component (cache will handle duplicates)
            for component in api_components:
                result = self._analyze_with_nuget_metadata(component)
                results.append(result)
        
        return results
    
    def get_analyzer_info(self) -> Dict[str, any]:
        """Get analyzer configuration and status information."""
        cache_stats = self.cache_manager.get_cache_stats()
        return {
            'runtime_type': self.get_runtime_type(),
            'metadata_lookup_enabled': self.metadata_lookup_enabled,
            'offline_mode': self.offline_mode,
            'nuget_api_url': self.nuget_api_url,
            'knowledge_base_entries': len(self.runtime_kb) if self.runtime_kb else 0,
            'cache_stats': cache_stats
        }