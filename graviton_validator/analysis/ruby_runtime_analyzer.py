"""
Ruby Runtime Compatibility Analyzer

Analyzes Ruby gems for ARM64/Graviton compatibility by integrating with
RubyGems.org API and checking for native extensions, Ruby version requirements,
and platform compatibility.
"""

import re
import logging
from typing import Dict, List, Optional, Any
from packaging import version as pkg_version
import requests

from .runtime_analyzer import RuntimeCompatibilityAnalyzer
from .cache_manager import get_cache_manager
from ..models import SoftwareComponent, ComponentResult, CompatibilityResult, CompatibilityStatus
from ..knowledge_base.runtime_loader import RuntimeKnowledgeBaseLoader


class RubyRuntimeAnalyzer(RuntimeCompatibilityAnalyzer):
    """Ruby runtime compatibility analyzer."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Ruby runtime analyzer."""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Ruby-specific configuration
        self.api_base_url = self.config.get('api_base_url', 'https://rubygems.org/api/v1')
        self.api_timeout = self.config.get('api_timeout', 10)
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 1.0)
        self.minimum_recommended_version = self.config.get('minimum_recommended_version', '3.0.0')
        self.offline_mode = self.config.get('offline_mode', False)
        
        # Initialize cache manager
        self.cache_manager = get_cache_manager()
        
        # Load Ruby runtime knowledge base
        self.kb_loader = RuntimeKnowledgeBaseLoader()
        self.runtime_kb = self.kb_loader.load_ruby_knowledge_base()
        
        # Initialize session for API calls
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Graviton-Compatibility-Validator/1.0',
            'Accept': 'application/json'
        })
    
    def get_runtime_type(self) -> str:
        """Get the runtime type identifier."""
        return 'ruby'
    
    def get_supported_purls(self) -> List[str]:
        """Get list of supported PURL prefixes."""
        return ['pkg:gem/', 'pkg:rubygems/']
    
    def analyze_component(self, component: SoftwareComponent) -> ComponentResult:
        """Analyze a Ruby gem component for Graviton compatibility."""
        try:
            # Phase 1: Knowledge Base Analysis (Primary)
            kb_result = self._analyze_with_knowledge_base(component)
            if kb_result.compatibility.status != CompatibilityStatus.UNKNOWN:
                self.logger.debug(f"Knowledge base analysis complete for {component.name}")
                return kb_result
            else:
                self.logger.debug(f"Knowledge base analysis returned UNKNOWN for {component.name}: {kb_result.compatibility.notes}")
            
            # Phase 2: Metadata Analysis (Secondary)
            if not self.offline_mode:
                self.logger.debug(f"Starting RubyGems metadata analysis for {component.name}")
                metadata_result = self._analyze_with_rubygems_metadata(component)
                if metadata_result.compatibility.status != CompatibilityStatus.UNKNOWN:
                    self.logger.debug(f"Metadata analysis complete for {component.name}")
                    return metadata_result
                else:
                    self.logger.debug(f"RubyGems metadata analysis returned UNKNOWN for {component.name}: {metadata_result.compatibility.notes}")
            else:
                self.logger.debug(f"RubyGems metadata lookup disabled for {component.name} (offline_mode={self.offline_mode})")
            
            # Phase 3: Unknown status with recommendation and analysis details
            self.logger.debug(f"No compatibility information found for {component.name} after all analysis phases")
            
            # Add analysis details for the fallback case
            analysis_details = f"Ruby analysis: kb_lookup=not_found, rubygems_lookup={'disabled' if self.offline_mode else 'failed'}, metadata_available=False"
            
            compatibility = CompatibilityResult(
                status=CompatibilityStatus.UNKNOWN,
                current_version_supported=False,
                minimum_supported_version=None,
                recommended_version=None,
                notes=f"No compatibility information available. Consider testing in ARM64 environment. {analysis_details}",
                confidence_level=1.0
            )
            
            return ComponentResult(
                component=component,
                compatibility=compatibility
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing Ruby gem {component.name}: {e}")
            return ComponentResult(
                component=component,
                compatibility=CompatibilityResult(
                    status=CompatibilityStatus.UNKNOWN,
                    current_version_supported=False,
                    minimum_supported_version=None,
                    recommended_version=None,
                    notes=f"Analysis failed: {str(e)}",
                    confidence_level=0.0
                )
            )
    
    def _analyze_with_knowledge_base(self, component: SoftwareComponent) -> ComponentResult:
        """Analyze component using runtime knowledge base.
        
        Args:
            component: Component to analyze
            
        Returns:
            ComponentResult from knowledge base analysis
        """
        if not self.runtime_kb or 'software_compatibility' not in self.runtime_kb:
            return ComponentResult(
                component=component,
                compatibility=CompatibilityResult(
                    status=CompatibilityStatus.UNKNOWN,
                    current_version_supported=False,
                    minimum_supported_version=None,
                    recommended_version=None,
                    notes="Ruby knowledge base not available"
                )
            )
        
        # Check for invalid/placeholder versions
        version = component.version
        if version and version.lower() in ['unknown', 'vunknown', 'n/a', 'na', 'null', 'none', 'all', '*', '']:
            version = None  # Treat as no version
        
        # Look for gem in knowledge base
        for gem_info in self.runtime_kb['software_compatibility']:
            if gem_info['name'].lower() == component.name.lower():
                # Found gem in knowledge base
                compatibility_info = gem_info.get('compatibility', {})
                supported_versions = compatibility_info.get('supported_versions', [])
                min_version = compatibility_info.get('minimum_supported_version')
                
                # Check if package has version requirements but no version provided
                if not version or not version.strip():
                    if supported_versions or min_version:
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
                                recommended_version=compatibility_info.get('recommended_version'),
                                notes=notes
                            )
                        )
                
                # Check version compatibility - find the best matching range
                matching_versions = []
                for version_info in supported_versions:
                    if self._version_matches_range(version or '0.0.0', version_info.get('version_range', '')):
                        matching_versions.append(version_info)
                
                # Use the most specific match (prefer more restrictive ranges)
                if matching_versions:
                    # Sort by specificity - prefer ranges with < or exact matches over >= ranges
                    best_match = matching_versions[0]
                    for match in matching_versions:
                        version_range = match.get('version_range', '')
                        if '<' in version_range and '>=' not in version_range:
                            best_match = match
                            break
                    
                    status = CompatibilityStatus(best_match.get('status', 'unknown'))
                    return ComponentResult(
                        component=component,
                        compatibility=CompatibilityResult(
                            status=status,
                            current_version_supported=status == CompatibilityStatus.COMPATIBLE,
                            minimum_supported_version=compatibility_info.get('minimum_supported_version'),
                            recommended_version=compatibility_info.get('recommended_version'),
                            notes=best_match.get('notes', ''),
                            confidence_level=best_match.get('confidence_level', 0.9)
                        )
                    )
                
                # Handle cases where version couldn't be processed but component is in KB
                if version and min_version:
                    # Version format couldn't be processed but we have minimum version info
                    return ComponentResult(
                        component=component,
                        compatibility=CompatibilityResult(
                            status=CompatibilityStatus.NEEDS_VERSION_VERIFICATION,
                            current_version_supported=False,
                            minimum_supported_version=min_version,
                            recommended_version=compatibility_info.get('recommended_version'),
                            notes=f"Version '{version}' format not recognized - software is Graviton-compatible (min: v{min_version}). Verify your version meets requirements."
                        )
                    )
                
                # No specific version match, return general compatibility
                if supported_versions:
                    first_version = supported_versions[0]
                    status = CompatibilityStatus(first_version.get('status', 'unknown'))
                    return ComponentResult(
                        component=component,
                        compatibility=CompatibilityResult(
                            status=status,
                            current_version_supported=status == CompatibilityStatus.COMPATIBLE,
                            minimum_supported_version=compatibility_info.get('minimum_supported_version'),
                            recommended_version=compatibility_info.get('recommended_version'),
                            notes=first_version.get('notes', ''),
                            confidence_level=first_version.get('confidence_level', 0.9)
                        )
                    )
        
        # Not found in knowledge base
        self.logger.debug(f"Gem {component.name} not found in Ruby knowledge base")
        self.logger.debug(f"Available gems in knowledge base: {[gem['name'] for gem in self.runtime_kb.get('software_compatibility', [])][:10]}..." if self.runtime_kb and 'software_compatibility' in self.runtime_kb else "Knowledge base is empty")
        return ComponentResult(
            component=component,
            compatibility=CompatibilityResult(
                status=CompatibilityStatus.UNKNOWN,
                current_version_supported=False,
                minimum_supported_version=None,
                recommended_version=None,
                notes="Gem not found in knowledge base"
            )
        )
    
    def _analyze_with_rubygems_metadata(self, component: SoftwareComponent) -> ComponentResult:
        """Analyze component using RubyGems.org metadata API.
        
        Args:
            component: Component to analyze
            
        Returns:
            ComponentResult from metadata analysis
        """
        try:
            # Get gem metadata from RubyGems.org API
            self.logger.debug(f"Fetching RubyGems metadata for {component.name}")
            gem_metadata = self._get_rubygems_metadata(component.name)
            if not gem_metadata:
                self.logger.debug(f"RubyGems API call failed for {component.name}")
                self.logger.debug(f"RubyGems URL attempted: {self.api_base_url}/gems/{component.name}.json")
                return ComponentResult(
                    component=component,
                    compatibility=CompatibilityResult(
                        status=CompatibilityStatus.UNKNOWN,
                        current_version_supported=False,
                        minimum_supported_version=None,
                        recommended_version=None,
                        notes="Gem metadata not available from RubyGems.org"
                    )
                )
            
            # Determine compatibility based on metadata
            return self._determine_compatibility_from_metadata(component, gem_metadata)
            
        except Exception as e:
            self.logger.warning(f"RubyGems metadata analysis failed for {component.name}: {e}")
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
    
    def _get_rubygems_metadata(self, gem_name: str) -> Optional[Dict[str, Any]]:
        """Get gem metadata from RubyGems.org API with caching."""
        cache_key = f"rubygems_{gem_name}"
        
        # Check cache first (if available)
        if hasattr(self.cache_manager, 'get_cached'):
            cached_data = self.cache_manager.get_cached('rubygems', gem_name, None)
            if cached_data:
                return cached_data
        elif hasattr(self.cache_manager, 'get'):
            cached_data = self.cache_manager.get(cache_key)
            if cached_data:
                return cached_data
        
        try:
            url = f"{self.api_base_url}/gems/{gem_name}.json"
            self.logger.debug(f"Making RubyGems API call: {url}")
            response = self.session.get(url, timeout=self.api_timeout)
            
            if response.status_code == 200:
                gem_data = response.json()
                self.logger.debug(f"RubyGems API success for {gem_name}: version={gem_data.get('version', 'unknown')}, platform={gem_data.get('platform', 'ruby')}")
                # Cache for 24 hours
                if hasattr(self.cache_manager, 'set_cached'):
                    self.cache_manager.set_cached('rubygems', gem_name, gem_data, None, ttl_hours=24)
                elif hasattr(self.cache_manager, 'set'):
                    self.cache_manager.set(cache_key, gem_data, ttl=86400)
                return gem_data
            elif response.status_code == 404:
                self.logger.debug(f"Gem {gem_name} not found in RubyGems.org (404)")
                return None
            else:
                self.logger.debug(f"RubyGems API returned status {response.status_code} for {gem_name}")
                return None
                
        except requests.exceptions.Timeout:
            self.logger.warning(f"API timeout for {gem_name}, using knowledge base")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"API error for {gem_name}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error fetching {gem_name}: {e}")
            return None
    
    def _determine_compatibility_from_metadata(self, component: SoftwareComponent, gem_metadata: Dict[str, Any]) -> ComponentResult:
        """Determine compatibility from RubyGems metadata.
        
        Args:
            component: Component being analyzed
            gem_metadata: Metadata from RubyGems.org API
            
        Returns:
            ComponentResult with compatibility analysis
        """
        # Check for native extensions (but handle ARM64 platforms specially)
        platform = gem_metadata.get('platform', 'ruby')
        if self._has_native_extensions(gem_metadata):
            # If it's an ARM64 platform, it's actually compatible
            if 'arm64' in platform.lower() or 'aarch64' in platform.lower():
                return ComponentResult(
                    component=component,
                    compatibility=CompatibilityResult(
                        status=CompatibilityStatus.COMPATIBLE,
                        current_version_supported=True,
                        minimum_supported_version=None,
                        recommended_version=None,
                        notes=f"ARM64 platform gem - compatible with Graviton. RubyGems analysis: native_extensions=True, platform={platform}, arm64_specific=True",
                        confidence_level=1.0
                    )
                )
            else:
                return ComponentResult(
                    component=component,
                    compatibility=CompatibilityResult(
                        status=CompatibilityStatus.NEEDS_VERIFICATION,
                        current_version_supported=False,
                        minimum_supported_version=None,
                        recommended_version=None,
                        notes=f"Native extensions detected - requires testing on ARM64 environment. RubyGems analysis: native_extensions=True, platform={platform}",
                        confidence_level=0.8
                    )
                )
        
        # Check Ruby version requirements
        ruby_compat = self._check_ruby_version_compatibility(gem_metadata)
        if ruby_compat.status != CompatibilityStatus.COMPATIBLE:
            return ComponentResult(
                component=component,
                compatibility=ruby_compat
            )
        
        # Check platform compatibility
        platform_compat = self._check_platform_compatibility(gem_metadata)
        if platform_compat.status != CompatibilityStatus.COMPATIBLE:
            return ComponentResult(
                component=component,
                compatibility=platform_compat
            )
        
        # Check for Rails framework
        if self._is_rails_gem(component.name):
            rails_compat = self._analyze_rails_compatibility(gem_metadata)
            return ComponentResult(
                component=component,
                compatibility=rails_compat
            )
        
        # Log detailed analysis for pure Ruby gems
        self.logger.debug(f"RubyGems analysis for {component.name}@{component.version} resulted in COMPATIBLE status (pure Ruby)")
        
        native_extensions = self._has_native_extensions(gem_metadata)
        ruby_compat = self._check_ruby_version_compatibility(gem_metadata)
        platform_compat = self._check_platform_compatibility(gem_metadata)
        
        self.logger.debug(f"Native extensions: {native_extensions}")
        self.logger.debug(f"Ruby compatibility: {ruby_compat.status}")
        self.logger.debug(f"Platform compatibility: {platform_compat.status}")
        
        analysis_details = f"RubyGems analysis: native_extensions={native_extensions}, ruby_version_compat={ruby_compat.status.value}, platform_compat={platform_compat.status.value}, is_rails={self._is_rails_gem(component.name)}"
        
        # Pure Ruby gems are generally compatible
        return ComponentResult(
            component=component,
            compatibility=CompatibilityResult(
                status=CompatibilityStatus.COMPATIBLE,
                current_version_supported=True,
                minimum_supported_version=None,
                recommended_version=None,
                notes=f"Pure Ruby gem - generally compatible with ARM64. {analysis_details}",
                confidence_level=0.9
            )
        )
    

    
    def _has_native_extensions(self, gem_metadata: Dict[str, Any]) -> bool:
        """Detect if gem has native C extensions."""
        # Check extensions field
        extensions = gem_metadata.get('extensions', [])
        if extensions:
            return True
        
        # Check platform specificity (but not for ARM64 platforms)
        platform = gem_metadata.get('platform', 'ruby')
        if platform != 'ruby':
            # Don't flag ARM64 platforms as having native extensions
            if 'arm64' in platform.lower() or 'aarch64' in platform.lower():
                return False
            return True
        
        # Check for common native extension patterns in requirements
        requirements = gem_metadata.get('requirements', [])
        if requirements:
            requirements_text = ' '.join(str(req) for req in requirements)
            native_patterns = ['extconf.rb', 'Rakefile', 'make', 'gcc', 'native', 'extension']
            if any(pattern in requirements_text.lower() for pattern in native_patterns):
                return True
        
        # Check dependencies for native extension indicators
        dependencies = gem_metadata.get('dependencies', {})
        if isinstance(dependencies, dict):
            runtime_deps = dependencies.get('runtime', [])
            for dep in runtime_deps:
                if isinstance(dep, dict) and dep.get('name') in ['ffi', 'native-package-installer']:
                    return True
        
        return False
    
    def _check_ruby_version_compatibility(self, gem_metadata: Dict[str, Any]) -> CompatibilityResult:
        """Check Ruby version requirements against Graviton support."""
        ruby_version_req = gem_metadata.get('ruby_version', '')
        
        if not ruby_version_req:
            # No specific Ruby version requirement
            return CompatibilityResult(
                status=CompatibilityStatus.COMPATIBLE,
                current_version_supported=True,
                minimum_supported_version=None,
                recommended_version=None,
                notes="No specific Ruby version requirement",
                confidence_level=0.7
            )
        
        try:
            # Parse Ruby version requirement
            min_version = self._parse_ruby_version_requirement(ruby_version_req)
            
            if min_version:
                if pkg_version.parse(min_version) >= pkg_version.parse('3.0.0'):
                    return CompatibilityResult(
                        status=CompatibilityStatus.COMPATIBLE,
                        current_version_supported=True,
                        minimum_supported_version=None,
                        recommended_version=None,
                        notes="Ruby 3.0+ has excellent ARM64 support",
                        confidence_level=1.0
                    )
                elif pkg_version.parse(min_version) >= pkg_version.parse('2.7.0'):
                    return CompatibilityResult(
                        status=CompatibilityStatus.NEEDS_UPGRADE,
                        current_version_supported=True,
                        minimum_supported_version=min_version,
                        recommended_version="Ruby 3.0+",
                        notes="Consider upgrading to Ruby 3.0+ for optimal ARM64 support",
                        confidence_level=0.8
                    )
                else:
                    return CompatibilityResult(
                        status=CompatibilityStatus.NEEDS_VERIFICATION,
                        current_version_supported=False,
                        minimum_supported_version=min_version,
                        recommended_version="Ruby 3.0+",
                        notes="Ruby version < 2.7 may have ARM64 compatibility issues",
                        confidence_level=0.6
                    )
            
        except Exception as e:
            self.logger.warning(f"Error parsing Ruby version requirement '{ruby_version_req}': {e}")
        
        return CompatibilityResult(
            status=CompatibilityStatus.COMPATIBLE,
            current_version_supported=True,
            minimum_supported_version=None,
            recommended_version=None,
            notes="Unable to parse Ruby version requirement, assuming compatible",
            confidence_level=0.5
        )
    
    def _check_platform_compatibility(self, gem_metadata: Dict[str, Any]) -> CompatibilityResult:
        """Check platform compatibility."""
        platform = gem_metadata.get('platform', 'ruby')
        
        if platform == 'ruby':
            # Universal Ruby platform
            return CompatibilityResult(
                status=CompatibilityStatus.COMPATIBLE,
                current_version_supported=True,
                minimum_supported_version=None,
                recommended_version=None,
                notes="Universal Ruby platform - compatible with ARM64",
                confidence_level=0.9
            )
        elif 'arm64' in platform.lower() or 'aarch64' in platform.lower():
            # Explicit ARM64 support
            return CompatibilityResult(
                status=CompatibilityStatus.COMPATIBLE,
                current_version_supported=True,
                minimum_supported_version=None,
                recommended_version=None,
                notes="Explicit ARM64 platform support",
                confidence_level=1.0
            )
        elif any(arch in platform.lower() for arch in ['x86', 'x64', 'i386', 'i686']):
            # x86-specific platform
            return CompatibilityResult(
                status=CompatibilityStatus.NEEDS_VERIFICATION,
                current_version_supported=False,
                minimum_supported_version=None,
                recommended_version=None,
                notes=f"Platform-specific gem ({platform}) - requires ARM64 version",
                confidence_level=0.8
            )
        
        # Unknown platform
        return CompatibilityResult(
            status=CompatibilityStatus.UNKNOWN,
            current_version_supported=False,
            minimum_supported_version=None,
            recommended_version=None,
            notes=f"Unknown platform: {platform}",
            confidence_level=0.3
        )
    
    def _is_rails_gem(self, gem_name: str) -> bool:
        """Check if gem is part of Rails framework."""
        rails_gems = [
            'rails', 'railties', 'activerecord', 'actionpack', 'actionview',
            'actionmailer', 'activejob', 'actioncable', 'activestorage',
            'activesupport', 'actionmailbox', 'actiontext'
        ]
        return gem_name.lower() in rails_gems
    
    def _analyze_rails_compatibility(self, gem_metadata: Dict[str, Any]) -> CompatibilityResult:
        """Analyze Rails-specific compatibility."""
        gem_version = gem_metadata.get('version', '0.0.0')
        
        try:
            if pkg_version.parse(gem_version) >= pkg_version.parse('6.0.0'):
                return CompatibilityResult(
                    status=CompatibilityStatus.COMPATIBLE,
                    current_version_supported=True,
                    minimum_supported_version=None,
                    recommended_version=None,
                    notes="Rails 6.0+ has excellent ARM64 support",
                    confidence_level=1.0
                )
            elif pkg_version.parse(gem_version) >= pkg_version.parse('5.0.0'):
                return CompatibilityResult(
                    status=CompatibilityStatus.NEEDS_UPGRADE,
                    current_version_supported=True,
                    minimum_supported_version=None,
                    recommended_version="6.0+",
                    notes="Consider upgrading to Rails 6.0+ for better ARM64 support",
                    confidence_level=0.8
                )
            else:
                return CompatibilityResult(
                    status=CompatibilityStatus.NEEDS_VERIFICATION,
                    current_version_supported=False,
                    minimum_supported_version=None,
                    recommended_version="6.0+",
                    notes="Rails < 5.0 may have ARM64 compatibility issues",
                    confidence_level=0.6
                )
        except Exception as e:
            self.logger.warning(f"Error parsing Rails version {gem_version}: {e}")
            return CompatibilityResult(
                status=CompatibilityStatus.UNKNOWN,
                current_version_supported=False,
                minimum_supported_version=None,
                recommended_version=None,
                notes="Unable to determine Rails version compatibility",
                confidence_level=0.3
            )
    
    def _parse_ruby_version_requirement(self, requirement: str) -> Optional[str]:
        """Parse Ruby version requirement string."""
        if not requirement:
            return None
        
        # Handle common patterns like ">= 2.7.0", "~> 3.0", etc.
        patterns = [
            r'>= (\d+\.\d+(?:\.\d+)?)',  # >= 2.7.0
            r'> (\d+\.\d+(?:\.\d+)?)',   # > 2.7.0
            r'~> (\d+\.\d+)',            # ~> 3.0
            r'(\d+\.\d+(?:\.\d+)?)'      # 3.0.0
        ]
        
        for pattern in patterns:
            match = re.search(pattern, requirement)
            if match:
                return match.group(1)
        
        return None
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings."""
        try:
            v1 = pkg_version.parse(version1)
            v2 = pkg_version.parse(version2)
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
            else:
                return 0
        except Exception:
            return 0
    
    def get_analyzer_info(self) -> Dict[str, Any]:
        """Get analyzer configuration information."""
        return {
            'runtime_type': self.get_runtime_type(),
            'supported_purls': self.get_supported_purls(),
            'api_base_url': self.api_base_url,
            'metadata_lookup_enabled': not self.config.get('offline_mode', False),
            'cache_enabled': self.cache_manager is not None,
            'knowledge_base_entries': len(self.runtime_kb.get('software_compatibility', [])) if self.runtime_kb else 0,
            'minimum_recommended_ruby_version': self.minimum_recommended_version
        }
    
    def _version_matches_range(self, version: str, version_range: str, _recursion_depth: int = 0) -> bool:
        """Check if version matches the specified range.
        
        Args:
            version: Version to check
            version_range: Version range specification
            
        Returns:
            True if version matches range
        """
        if not version_range or version_range == '*':
            return True
        
        try:
            # Handle compound ranges first (before simple ranges)
            if ',' in version_range and _recursion_depth == 0:
                # Handle compound ranges like ">=5.0.0,<6.0.0" (only at top level to prevent recursion)
                parts = [part.strip() for part in version_range.split(',')]
                part_results = [self._version_matches_range(version, part, _recursion_depth + 1) for part in parts]
                result = all(part_results)
                self.logger.debug(f"Compound range {version_range} for {version}: parts={parts}, results={part_results}, final={result}")
                return result
            elif version_range.startswith('>='):
                min_version = version_range[2:].strip()
                result = pkg_version.parse(version) >= pkg_version.parse(min_version)
                return result
            elif version_range.startswith('>'):
                min_version = version_range[1:].strip()
                result = pkg_version.parse(version) > pkg_version.parse(min_version)
                return result
            elif version_range.startswith('<='):
                max_version = version_range[2:].strip()
                result = pkg_version.parse(version) <= pkg_version.parse(max_version)
                return result
            elif version_range.startswith('<'):
                max_version = version_range[1:].strip()
                result = pkg_version.parse(version) < pkg_version.parse(max_version)
                return result
            elif version_range.startswith('=='):
                exact_version = version_range[2:].strip()
                return version == exact_version
            else:
                return version == version_range
        except Exception as e:
            # If version parsing fails, assume it doesn't match
            self.logger.debug(f"Version parsing failed for {version} vs {version_range}: {e}")
            return False