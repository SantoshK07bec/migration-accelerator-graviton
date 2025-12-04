#!/usr/bin/env python3
"""
SBOM Runtime Merger - Merges SBOM analysis with runtime analysis results

This module provides functionality to combine SBOM-based compatibility analysis
with runtime package testing results, with runtime results taking precedence
for duplicate components.
"""

import logging
import json
from typing import List, Dict, Any
from pathlib import Path

from ..models import ComponentResult, SoftwareComponent, CompatibilityResult, CompatibilityStatus, AnalysisResult
from ..reporting.json_reporter import JSONReporter

logger = logging.getLogger(__name__)

def analyze_with_runtime_integration(components: List, detected_os: str, sbom_file: str,
                                   sbom_data: Dict[str, Any], analyzer, runtime_analyzer_manager,
                                   output_dir: str, **runtime_kwargs) -> AnalysisResult:
    """
    Single function to handle SBOM + runtime analysis integration.
    Replaces the complex 200+ line conversion logic in main script.
    """
    logger.info(f"Starting integrated analysis for {len(components)} components")
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Step 1: SBOM Analysis
    sbom_result = analyzer.analyze_components(components, detected_os, sbom_file)
    logger.debug(f"SBOM analysis: {len(sbom_result.components)} components")
    
    # Write SBOM analysis result to disk
    sbom_filename = Path(sbom_file).stem if sbom_file else "sbom_analysis"
    sbom_json_path = Path(output_dir) / f"{sbom_filename}_sbom_analysis.json"
    _write_analysis_result_to_file(sbom_result, sbom_json_path)
    logger.info(f"SBOM analysis saved to: {sbom_json_path}")
    
    # Step 2: Runtime Analysis
    runtime_components = []
    if runtime_analyzer_manager:
        try:
            # Pass detected_os to runtime analyzer so it uses same OS detection as SBOM analyzer
            runtime_kwargs['detected_os'] = detected_os
            logger.info(f"Passing detected OS to runtime analyzer: {detected_os}")
            
            runtime_results = runtime_analyzer_manager.analyze_components_by_runtime(
                components, output_dir, sbom_data=sbom_data, **runtime_kwargs
            )
            runtime_components = _load_runtime_components(runtime_results, output_dir, detected_os)
            logger.debug(f"Runtime analysis: {len(runtime_components)} components")
        except Exception as e:
            logger.error(f"Runtime analysis failed: {e}")
    
    # Step 3: Combine components (change function name below to switch behavior)
    merged_components = _merge_components(sbom_result.components, runtime_components)
    # To use append instead: merged_components = _append_components(sbom_result.components, runtime_components)
    logger.info(f"Merged result: {len(merged_components)} total components")
    
    # Step 4: Create merged result
    merged_result = _create_merged_result(sbom_result, merged_components)
    
    # Write merged analysis result to disk
    merged_json_path = Path(output_dir) / f"{sbom_filename}_merged_analysis.json"
    _write_analysis_result_to_file(merged_result, merged_json_path)
    logger.info(f"Merged analysis saved to: {merged_json_path}")
    
    return merged_result

# Reuse the existing working function from manifest_generators.py
# This is the same function that works in native/container mode
from .manifest_generators import RuntimeAnalyzerManager

def _load_runtime_components(runtime_results: Dict[str, Any], output_dir: str, detected_os: str = None) -> List[ComponentResult]:
    """Load ComponentResult objects from runtime analysis files - reuses working implementation."""
    # Handle case where no runtime analyzers were found
    if isinstance(runtime_results, str) or 'message' in runtime_results:
        logger.debug("No runtime results to load (no applicable analyzers found)")
        return []
    
    # Create a temporary RuntimeAnalyzerManager to access its _load_results_from_file method
    temp_manager = RuntimeAnalyzerManager(use_containers=False)
    components = []
    
    logger.debug(f"Loading runtime components from {len(runtime_results)} runtime results")
    
    for runtime_type, result in runtime_results.items():
        logger.debug(f"Processing runtime {runtime_type}")
        
        if 'error' in result:
            logger.warning(f"{runtime_type} has error, skipping: {result['error']}")
            continue
            
        # Get result file path with fallback
        result_file_path = result.get('result_file') or result.get('result_path')
        if not result_file_path:
            logger.warning(f"{runtime_type} missing result file path")
            continue
            
        result_file = Path(result_file_path)
        if not result_file.exists():
            # Fallback: check for *_<runtime>_analysis.json in root directory
            output_path = Path(output_dir)
            fallback_files = list(output_path.glob(f"*_{runtime_type}_analysis.json"))
            if fallback_files:
                result_file = fallback_files[0]
                logger.debug(f"Using fallback file for {runtime_type}: {result_file}")
            else:
                logger.warning(f"{runtime_type} result file not found: {result_file}")
                continue
        
        # Load and process components using the working method from RuntimeAnalyzer
        try:
            
            logger.debug(f"{runtime_type} reading file: {result_file}")
            logger.debug(f"{runtime_type} file size: {result_file.stat().st_size} bytes")
            
            with open(result_file, 'r') as f:
                data = json.load(f)
            
            # Handle both dict format ({'components': [...]}) and direct list format ([{...}, {...}])
            components_data = []
            if isinstance(data, dict) and 'components' in data:
                # Dict format with 'components' key
                components_data = data['components']
                logger.debug(f"{runtime_type} found {len(components_data)} components in dict format")
            elif isinstance(data, list):
                # Direct list format
                components_data = data
                logger.debug(f"{runtime_type} found {len(components_data)} components in list format")
            else:
                logger.warning(f"{runtime_type} unexpected data format: {type(data)}")
                continue
            
            # Process each component
            processed_count = 0
            for item in components_data:
                if isinstance(item, dict) and 'name' in item and 'compatibility' in item:
                    # Valid component format
                    properties = item.get('properties', {})
                    # Ensure runtime components have detected OS information
                    if detected_os and 'detected_os' not in properties:
                        properties['detected_os'] = detected_os
                    
                    component = SoftwareComponent(
                        name=item['name'],
                        version=item.get('version', 'unknown'),
                        component_type=item.get('type', 'unknown'),
                        source_sbom='runtime_analysis',
                        properties=properties,
                        parent_component=item.get('parent_component'),
                        child_components=item.get('child_components', []),
                        source_package=item.get('source_package')
                    )
                    
                    compatibility = CompatibilityResult(
                        status=CompatibilityStatus(item['compatibility']['status']),
                        current_version_supported=item['compatibility'].get('current_version_supported', False),
                        minimum_supported_version=item['compatibility'].get('minimum_supported_version'),
                        recommended_version=item['compatibility'].get('recommended_version'),
                        notes=item['compatibility'].get('notes', ''),
                        confidence_level=item['compatibility'].get('confidence_level', 0.9)
                    )
                    
                    components.append(ComponentResult(component=component, compatibility=compatibility))
                    processed_count += 1
                else:
                    if processed_count < 3:  # Only log first few invalid items
                        logger.warning(f"{runtime_type} invalid component format: {type(item)} - keys: {list(item.keys()) if isinstance(item, dict) else 'not dict'}")
            
            logger.debug(f"{runtime_type} successfully processed {processed_count}/{len(components_data)} components")
                
        except Exception as e:
            logger.error(f"Failed to load {runtime_type} results from {result_file}: {e}")
            import traceback
            logger.debug(f"{runtime_type} full traceback: {traceback.format_exc()}")
    
    total_loaded = len(components)
    logger.debug(f"Total runtime components loaded: {total_loaded} from {len(runtime_results)} runtime files")
    if total_loaded == 0:
        logger.debug(f"No runtime components loaded - this is normal when no applicable runtime analyzers are found")
    return components

def _append_components(sbom_components: List[ComponentResult], 
                      runtime_components: List[ComponentResult]) -> List[ComponentResult]:
    """Append SBOM and runtime components without merging duplicates."""
    logger.debug(f"Appending {len(sbom_components)} SBOM + {len(runtime_components)} runtime components")
    combined = list(sbom_components)
    combined.extend(runtime_components)
    logger.debug(f"Combined result: {len(combined)} total components")
    return combined

def _merge_components(sbom_components: List[ComponentResult], 
                     runtime_components: List[ComponentResult]) -> List[ComponentResult]:
    """Merge components with runtime taking precedence over SBOM for duplicates."""
    if not runtime_components:
        return sbom_components
    
    # Create lookup for runtime components
    runtime_lookup = {f"{c.component.name}:{c.component.version}": c for c in runtime_components}
    
    # Start with runtime components
    merged = list(runtime_components)
    
    # Add SBOM components that don't have runtime equivalents
    for sbom_comp in sbom_components:
        key = f"{sbom_comp.component.name}:{sbom_comp.component.version}"
        if key not in runtime_lookup:
            merged.append(sbom_comp)
    
    return merged

def _create_merged_result(sbom_result: AnalysisResult, merged_components: List[ComponentResult]) -> AnalysisResult:
    """Create merged AnalysisResult with recalculated counts."""
    compatible = sum(1 for c in merged_components if c.compatibility.status == CompatibilityStatus.COMPATIBLE)
    incompatible = sum(1 for c in merged_components if c.compatibility.status == CompatibilityStatus.INCOMPATIBLE)
    needs_upgrade = sum(1 for c in merged_components if c.compatibility.status == CompatibilityStatus.NEEDS_UPGRADE)
    needs_verification = sum(1 for c in merged_components if c.compatibility.status == CompatibilityStatus.NEEDS_VERIFICATION)
    needs_version_verification = sum(1 for c in merged_components if c.compatibility.status == CompatibilityStatus.NEEDS_VERSION_VERIFICATION)
    unknown = sum(1 for c in merged_components if c.compatibility.status == CompatibilityStatus.UNKNOWN)
    
    return AnalysisResult(
        components=merged_components,
        total_components=len(merged_components),
        compatible_count=compatible,
        incompatible_count=incompatible,
        needs_upgrade_count=needs_upgrade,
        needs_verification_count=needs_verification,
        needs_version_verification_count=needs_version_verification,
        unknown_count=unknown,
        errors=sbom_result.errors,
        processing_time=sbom_result.processing_time,
        detected_os=sbom_result.detected_os,
        sbom_file=sbom_result.sbom_file
    )

def _write_analysis_result_to_file(analysis_result: AnalysisResult, file_path: Path):
    """Write AnalysisResult to JSON file using JSONReporter."""
    try:
        json_reporter = JSONReporter(include_metadata=True)
        structured_data = json_reporter.get_structured_data(analysis_result)
        
        with open(file_path, 'w') as f:
            json.dump(structured_data, f, indent=2)
        
        logger.debug(f"Analysis result written to: {file_path}")
    except Exception as e:
        logger.error(f"Failed to write analysis result to {file_path}: {e}")

