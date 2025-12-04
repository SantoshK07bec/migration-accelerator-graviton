"""
Enhanced JAR analysis integration for the main Graviton Validator.
Provides SBOM enhancement and gap detection capabilities.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..models import SoftwareComponent, ComponentResult, CompatibilityStatus, CompatibilityResult
from ..jar_analysis_engine import analyze_jar_files_simple

class JARAnalyzer:
    """Enhanced JAR analyzer that integrates with SBOM analysis."""
    
    def __init__(self, compatibility_analyzer=None):
        self.compatibility_analyzer = compatibility_analyzer
        # Initialize required components for tests - COMMENTED OUT (unused)
        # from .jar_enhancement import ArchiveInspector
        # self.archive_inspector = ArchiveInspector()
    
    def analyze_jars(self, jar_paths: List[str]) -> List[ComponentResult]:
        """Analyze JAR files and return ComponentResult objects."""
        # Use enhanced analysis
        jar_results = analyze_jar_files_simple(jar_paths)
        
        component_results = []
        for jar_result in jar_results:
            # Convert to ComponentResult
            component = SoftwareComponent(
                name=jar_result['library_name'],
                version=jar_result['version'],
                component_type='library',
                source_sbom='jar_analysis',
                properties={
                    'source': 'jar_analysis',
                    'jar_path': jar_result['path'],
                    'size_mb': str(jar_result['size_mb']),
                    'has_native_code': str(jar_result.get('has_native_code', False)),
                    'native_files': ','.join(jar_result.get('native_files', [])),
                    'group_id': jar_result.get('group_id', ''),
                    'confidence': jar_result.get('confidence', 'MEDIUM'),
                    'purl': self._generate_purl(jar_result)
                }
            )
            
            # Map compatibility status
            status_map = {
                'COMPATIBLE': CompatibilityStatus.COMPATIBLE,
                'NEEDS_VERIFICATION': CompatibilityStatus.NEEDS_VERIFICATION,
                'INCOMPATIBLE': CompatibilityStatus.INCOMPATIBLE,
                'ERROR': CompatibilityStatus.UNKNOWN
            }
            
            # Create compatibility result based on JAR analysis
            jar_status = status_map.get(jar_result['compatibility'], CompatibilityStatus.UNKNOWN)
            
            # Add JAR-specific notes
            notes = []
            if jar_result.get('issues'):
                notes.extend(jar_result['issues'])
            if jar_result.get('recommendations'):
                notes.extend([f"Recommendation: {rec}" for rec in jar_result['recommendations']])
            
            # Set confidence level
            confidence_map = {'HIGH': 1.0, 'MEDIUM': 0.7, 'LOW': 0.4}
            confidence_level = confidence_map.get(jar_result.get('confidence', 'MEDIUM'), 0.7)
            
            compatibility = CompatibilityResult(
                status=jar_status,
                current_version_supported=(jar_status == CompatibilityStatus.COMPATIBLE),
                minimum_supported_version=jar_result.get('version_info', {}).get('fixed_in'),
                recommended_version=None,
                notes='; '.join(notes) if notes else None,
                confidence_level=confidence_level
            )
            
            component_results.append(ComponentResult(
                component=component,
                compatibility=compatibility
            ))
        
        return component_results
    
    def enhance_sbom_with_jars(self, sbom_results: List[ComponentResult], 
                              jar_paths: List[str]) -> Dict[str, Any]:
        """Enhance SBOM analysis with JAR analysis results."""
        jar_results = self.analyze_jars(jar_paths)
        
        # Find gaps - components in JARs but not in SBOM
        sbom_components = {self._normalize_component_name(r.component): r for r in sbom_results}
        jar_components = {self._normalize_component_name(r.component): r for r in jar_results}
        
        gaps = []
        enhanced_components = list(sbom_results)  # Start with SBOM results
        
        for jar_name, jar_result in jar_components.items():
            if jar_name not in sbom_components:
                # This is a gap - component found in JAR but not in SBOM
                gaps.append(jar_result)
                enhanced_components.append(jar_result)
            else:
                # Component exists in both - enhance SBOM result with JAR info
                sbom_result = sbom_components[jar_name]
                self._enhance_component_with_jar_info(sbom_result, jar_result)
        
        return {
            'enhanced_components': enhanced_components,
            'gaps_found': gaps,
            'gap_count': len(gaps),
            'enhancement_summary': {
                'sbom_components': len(sbom_results),
                'jar_components': len(jar_results),
                'total_enhanced': len(enhanced_components),
                'gaps_detected': len(gaps)
            }
        }
    
    def _generate_purl(self, jar_result: Dict[str, Any]) -> str:
        """Generate package URL for JAR component."""
        group_id = jar_result.get('group_id', '')
        artifact_id = jar_result['library_name']
        version = jar_result['version']
        
        if group_id:
            return f"pkg:maven/{group_id}/{artifact_id}@{version}"
        else:
            return f"pkg:generic/{artifact_id}@{version}"
    
    def _normalize_component_name(self, component: SoftwareComponent) -> str:
        """Normalize component name for comparison."""
        # Use group:artifact format if available, otherwise just name
        group_id = component.properties.get('group_id', '')
        if group_id:
            return f"{group_id}:{component.name}"
        return component.name.lower()
    
    def _enhance_component_with_jar_info(self, sbom_result: ComponentResult, 
                                        jar_result: ComponentResult):
        """Enhance SBOM component result with JAR analysis information."""
        # Add JAR-specific properties
        sbom_result.component.properties.update({
            'jar_verified': True,
            'jar_path': jar_result.component.properties.get('jar_path'),
            'has_native_code': jar_result.component.properties.get('has_native_code', False),
            'native_files': jar_result.component.properties.get('native_files', []),
            'jar_confidence': jar_result.component.properties.get('confidence', 'MEDIUM')
        })
        
        # If JAR analysis found issues that SBOM didn't, update compatibility
        if (jar_result.compatibility.compatibility == CompatibilityStatus.INCOMPATIBLE and 
            sbom_result.compatibility.compatibility != CompatibilityStatus.INCOMPATIBLE):
            sbom_result.compatibility.compatibility = CompatibilityStatus.NEEDS_VERIFICATION
            sbom_result.compatibility.notes = (
                f"{sbom_result.compatibility.notes}; JAR analysis: {jar_result.compatibility.notes}"
                if sbom_result.compatibility.notes else f"JAR analysis: {jar_result.compatibility.notes}"
            )
        
        # Enhance confidence if JAR analysis provides higher confidence
        jar_confidence = jar_result.compatibility.confidence_level
        if jar_confidence == 'high' and sbom_result.compatibility.confidence_level != 'high':
            sbom_result.compatibility.confidence_level = 'high'
    
    def _convert_to_software_components(self, archive_components, source_jar):
        """Convert archive components to software components."""
        from ..models import SoftwareComponent
        
        software_components = []
        for comp in archive_components:
            # Extract name without extension for JAR components
            if comp.component_type == 'jar':
                name = comp.name.replace('.jar', '')
            else:
                name = comp.name
            
            software_comp = SoftwareComponent(
                name=name,
                version=comp.version,
                component_type='library' if comp.component_type != 'jar' else 'library',
                source_sbom=source_jar,
                properties={
                    'source': 'jar_analysis',
                    'component_type': comp.component_type,
                    'size': str(comp.size),
                    'checksum': comp.checksum or ''
                }
            )
            software_components.append(software_comp)
        
        return software_components