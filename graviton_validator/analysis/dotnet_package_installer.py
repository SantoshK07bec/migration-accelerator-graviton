#!/usr/bin/env python3
"""
.NET Package Installer for ARM64 Compatibility Analysis
Rewritten to use models.py schema with ComponentResult structure
"""

import os
import sys
import json
import subprocess
import tempfile
import argparse
import time
import logging
import shutil
import defusedxml.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))  # Add graviton_validator/
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # Add project root

# Import models from the main validator
try:
    from graviton_validator.models import (
        SoftwareComponent, CompatibilityResult, ComponentResult, 
        CompatibilityStatus
    )
except ImportError:
    # Fallback for standalone execution
    try:
        from models import (
            SoftwareComponent, CompatibilityResult, ComponentResult, 
            CompatibilityStatus
        )
    except ImportError:
        # Final fallback - direct path
        from graviton_validator.models import (
            SoftwareComponent, CompatibilityResult, ComponentResult, 
            CompatibilityStatus
        )

# Initialize logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stderr)
formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG if os.environ.get('DEBUG') else logging.INFO)

def debug(msg): logger.debug(msg)
def info(msg): logger.info(msg)
def warn(msg): logger.warning(msg)
def error(msg): logger.error(msg)


class DotNetCompatibilityAnalyzer:
    """Main analyzer for .NET package ARM64 compatibility."""
    
    def __init__(self):
        self.is_arm = self._detect_architecture()
    
    def _detect_architecture(self) -> bool:
        """Detect if running on ARM architecture."""
        try:
            arch = subprocess.run(['uname', '-m'], capture_output=True, text=True).stdout.strip()
            return arch in ['aarch64', 'arm64']
        except:
            return False
    
    def analyze_package(self, package_name: str, version: str) -> ComponentResult:
        """Analyze single package for ARM64 compatibility."""
        debug(f"[DOTNET_ANALYZE_START] Starting analysis for package: {package_name}@{version}")
        
        # Create SoftwareComponent
        component = SoftwareComponent(
            name=package_name,
            version=version,
            component_type="dotnet-8.0",
            source_sbom="runtime_analysis",
            properties={
                'environment': 'native_dotnet_8.0_amazon-linux-2023',
                'runtime_analysis': 'true',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'original_version': version
            }
        )
        
        # Initialize compatibility result
        compatibility = CompatibilityResult(
            status=CompatibilityStatus.UNKNOWN,
            current_version_supported=False,
            minimum_supported_version=None,
            recommended_version=None,
            notes="",
            confidence_level=0.9
        )
        
        try:
            debug(f"[DOTNET_ANALYZE_TEST] Starting package restore test for {package_name}@{version}")
            test_result = self._test_package_restore(package_name, version, component)
            
            # Determine compatibility based on test results
            self._determine_compatibility(test_result, component, compatibility)
            
        except Exception as e:
            error(f"[DOTNET_ANALYZE_ERROR] Analysis failed for {package_name}@{version}: {str(e)}")
            compatibility.status = CompatibilityStatus.UNKNOWN
            compatibility.notes = f"Analysis failed: {str(e)}"
            component.properties['error_details'] = str(e)
            component.properties['error_type'] = 'unknown'
            component.properties['install_status'] = 'Failed'
        
        debug(f"[DOTNET_ANALYZE_COMPLETE] Final result for {package_name}@{version}: status={compatibility.status.value}")
        return ComponentResult(component=component, compatibility=compatibility, matched_name=None)
    
    def _test_package_restore(self, package_name: str, version: str, component: SoftwareComponent) -> Dict[str, Any]:
        """Test package restore with ARM64 runtime."""
        temp_dir = tempfile.mkdtemp(prefix=f"dotnet_test_{uuid.uuid4().hex[:8]}_")
        debug(f"[DOTNET_TEST_TEMP] Using temporary directory: {temp_dir}")
        
        try:
            # Create test project
            test_project = self._create_test_project(temp_dir, package_name, version)
            debug(f"[DOTNET_TEST_PROJECT] Created test project: {test_project}")
            
            # Run dotnet restore with ARM64 runtime
            debug(f"[DOTNET_TEST_RESTORE] Starting dotnet restore for {package_name}@{version}")
            result = self._run_dotnet_command(f"restore {test_project} --runtime linux-arm64", temp_dir)
            
            debug(f"[DOTNET_TEST_RESTORE_RESULT] Restore completed: exit_code={result['exit_code']}")
            
            # Store test outputs in component properties
            component.properties['test_output'] = result['output']
            component.properties['test_execution_output'] = result['error'] if result['error'] else 'N/A - No test script available'
            component.properties['install_status'] = 'Success' if result['exit_code'] == 0 else 'Failed'
            
            return result
            
        finally:
            debug(f"[DOTNET_TEST_CLEANUP] Starting cleanup for {package_name}@{version}")
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    debug(f"[DOTNET_TEST_CLEANUP] Cleanup completed successfully")
            except Exception as cleanup_ex:
                debug(f"[DOTNET_TEST_CLEANUP] Cleanup failed (ignoring): {cleanup_ex}")
    
    def _create_test_project(self, temp_dir: str, package_name: str, version: str) -> str:
        """Create temporary test project."""
        project_content = f'''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="{package_name}" Version="{version}" />
  </ItemGroup>
</Project>'''
        
        test_project = os.path.join(temp_dir, "test.csproj")
        with open(test_project, 'w') as f:
            f.write(project_content)
        
        debug(f"[DOTNET_TEST_PROJECT_CONTENT] Project content written to {test_project}")
        return test_project
    
    def _run_dotnet_command(self, arguments: str, working_dir: str) -> Dict[str, Any]:
        """Execute dotnet command and return results."""
        debug(f"[DOTNET_COMMAND_START] Executing: dotnet {arguments}")
        debug(f"[DOTNET_COMMAND_DIR] Working directory: {working_dir}")
        
        try:
            start_time = time.time()
            # Split arguments safely - arguments are internally controlled, not user input
            import shlex
            cmd_list = ["dotnet"] + shlex.split(arguments)
            
            process = subprocess.run(
                cmd_list,
                shell=False,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            duration = time.time() - start_time
            
            debug(f"[DOTNET_COMMAND_COMPLETE] Command completed in {duration:.2f}s with exit code: {process.returncode}")
            debug(f"[DOTNET_COMMAND_OUTPUT] STDOUT ({len(process.stdout)} chars): {process.stdout[:200]}{'...' if len(process.stdout) > 200 else ''}")
            debug(f"[DOTNET_COMMAND_ERROR] STDERR ({len(process.stderr)} chars): {process.stderr[:200]}{'...' if len(process.stderr) > 200 else ''}")
            
            return {
                'exit_code': process.returncode,
                'output': process.stdout,
                'error': process.stderr
            }
            
        except subprocess.TimeoutExpired:
            error(f"[DOTNET_COMMAND_TIMEOUT] Command timed out after 120s")
            return {
                'exit_code': -1,
                'output': '',
                'error': 'Command timed out after 120 seconds'
            }
        except Exception as e:
            error(f"[DOTNET_COMMAND_EXCEPTION] Command execution failed: {str(e)}")
            return {
                'exit_code': -1,
                'output': '',
                'error': str(e)
            }
    
    def _determine_compatibility(self, test_result: Dict[str, Any], component: SoftwareComponent, compatibility: CompatibilityResult):
        """Determine compatibility status based on test results."""
        exit_code = test_result['exit_code']
        output = test_result['output']
        error = test_result['error']
        
        debug(f"[DOTNET_COMPAT_DETERMINE] Determining compatibility: exit_code={exit_code}")
        
        # Set default properties
        component.properties['native_build_detected'] = 'No'  # .NET packages are typically managed code
        component.properties['fallback_used'] = 'false'
        
        if exit_code == 0:
            debug(f"[DOTNET_COMPAT_SUCCESS] Package restore successful")
            compatibility.status = CompatibilityStatus.COMPATIBLE
            compatibility.current_version_supported = True
            compatibility.notes = f"Successfully restored {component.name}=={component.version} for ARM64"
            return
        
        # Analyze error for specific failure types
        error_lower = error.lower() if error else ""
        debug(f"[DOTNET_COMPAT_ERROR_ANALYSIS] Analyzing error content for status determination")
        
        # Classify error type
        error_type = self._classify_error(error)
        component.properties['error_type'] = error_type
        
        # Extract relevant error details
        error_details = self._extract_relevant_error(error)
        component.properties['error_details'] = error_details
        
        # Determine status based on error patterns
        if self._is_network_error(error_lower):
            debug(f"[DOTNET_COMPAT_NETWORK] Network error detected")
            compatibility.status = CompatibilityStatus.UNKNOWN
            compatibility.notes = "Network connectivity issue - unable to reach NuGet registry"
        elif self._is_package_not_found(error_lower):
            debug(f"[DOTNET_COMPAT_NOT_FOUND] Package not found error detected")
            compatibility.status = CompatibilityStatus.INCOMPATIBLE
            compatibility.notes = f"Package {component.name} does not exist on NuGet"
        elif self._is_version_not_found(error_lower):
            debug(f"[DOTNET_COMPAT_VERSION_NOT_FOUND] Version not found error detected")
            compatibility.status = CompatibilityStatus.NEEDS_UPGRADE
            compatibility.notes = f"Version {component.version} of {component.name} not found - try latest version"
        elif self._is_runtime_incompatible(error_lower):
            debug(f"[DOTNET_COMPAT_RUNTIME_INCOMPATIBLE] Runtime incompatibility detected")
            compatibility.status = CompatibilityStatus.INCOMPATIBLE
            compatibility.notes = f"Package {component.name}=={component.version} is not compatible with ARM64 architecture"
        else:
            debug(f"[DOTNET_COMPAT_UNKNOWN] Unknown error pattern")
            compatibility.status = CompatibilityStatus.UNKNOWN
            compatibility.notes = f"Package {component.name}=={component.version} failed to restore"
    
    def _classify_error(self, error: str) -> str:
        """Classify error type."""
        if not error:
            return "unknown"
        
        error_lower = error.lower()
        
        if any(keyword in error_lower for keyword in ["network", "timed out", "timeout", "connection", "service index"]):
            return "network"
        elif any(keyword in error_lower for keyword in ["unable to find package", "not found", "404"]):
            return "dependency"
        elif any(keyword in error_lower for keyword in ["version", "constraint"]):
            return "dependency"
        elif any(keyword in error_lower for keyword in ["permission", "access"]):
            return "permissions"
        else:
            return "unknown"
    
    def _extract_relevant_error(self, error: str) -> str:
        """Extract relevant error information."""
        if not error:
            return ""
        
        lines = error.split('\n')
        relevant_lines = [
            line for line in lines 
            if any(keyword in line.lower() for keyword in ["error", "failed", "not found", "unable"])
        ][:3]  # Take first 3 relevant lines
        
        result = "; ".join(relevant_lines)
        return result
    
    def _is_network_error(self, error_lower: str) -> bool:
        """Check if error is network-related."""
        return any(pattern in error_lower for pattern in [
            "unable to load the service index",
            "timeout",
            "network",
            "connection"
        ])
    
    def _is_package_not_found(self, error_lower: str) -> bool:
        """Check if package doesn't exist."""
        return ("unable to find package" in error_lower and 
                "no packages exist with this id" in error_lower)
    
    def _is_version_not_found(self, error_lower: str) -> bool:
        """Check if specific version not found."""
        return ("unable to find package" in error_lower and 
                "version" in error_lower and
                "no packages exist with this id" not in error_lower)
    
    def _is_runtime_incompatible(self, error_lower: str) -> bool:
        """Check if runtime incompatible."""
        return any(pattern in error_lower for pattern in [
            "not compatible with",
            "linux-arm64"
        ])


class ProjectFileParser:
    """Parser for .NET project files."""
    
    def parse(self, project_file: str) -> List[Dict[str, str]]:
        """Parse project file and extract package references."""
        debug(f"[DOTNET_PARSE_START] Parsing project file: {project_file}")
        packages = []
        
        try:
            tree = ET.parse(project_file)
            root = tree.getroot()
            
            # Find all PackageReference elements
            package_refs = root.findall('.//PackageReference')
            debug(f"[DOTNET_PARSE_FOUND] Found {len(package_refs)} PackageReference elements")
            
            for i, package_ref in enumerate(package_refs, 1):
                name = package_ref.get('Include')
                version = package_ref.get('Version', 'latest')
                
                debug(f"[DOTNET_PARSE_PACKAGE] Package {i}: Include='{name}', Version='{version}'")
                
                if name:
                    packages.append({
                        'name': name,
                        'version': version
                    })
                    debug(f"[DOTNET_PARSE_ADDED] Added package: {name}@{version}")
                else:
                    debug(f"[DOTNET_PARSE_SKIP] Skipping PackageReference {i}: missing Include attribute")
            
            debug(f"[DOTNET_PARSE_COMPLETE] Parsing complete. Found {len(packages)} valid package references")
            
        except Exception as e:
            error(f"[DOTNET_PARSE_ERROR] Failed to parse project file: {str(e)}")
            raise Exception(f"Failed to parse project file: {str(e)}")
        
        return packages


def analyze_project_file(project_file: str) -> List[ComponentResult]:
    """Analyze .NET project file for ARM64 compatibility."""
    debug(f"[DOTNET_PROJECT_START] Starting project file analysis: {project_file}")
    info(f"Starting .NET package analysis for: {project_file}")
    
    if not os.path.exists(project_file):
        error(f"[DOTNET_PROJECT_ERROR] Project file not found: {project_file}")
        raise FileNotFoundError(f"Project file not found: {project_file}")
    
    # Parse project file
    parser = ProjectFileParser()
    packages = parser.parse(project_file)
    
    if not packages:
        debug(f"[DOTNET_PROJECT_NO_PACKAGES] No packages found in project file")
        info("No packages found in project file")
        return []
    
    # Analyze each package
    analyzer = DotNetCompatibilityAnalyzer()
    results = []
    
    debug(f"[DOTNET_PROJECT_ANALYZE] Starting analysis of {len(packages)} packages")
    
    for i, package in enumerate(packages, 1):
        debug(f"[DOTNET_PROJECT_PACKAGE] Analyzing package {i}/{len(packages)}: {package['name']}@{package['version']}")
        result = analyzer.analyze_package(package['name'], package['version'])
        results.append(result)
        debug(f"[DOTNET_PROJECT_PACKAGE_RESULT] Package {package['name']} analysis complete: {result.compatibility.status.value}")
    
    debug(f"[DOTNET_PROJECT_COMPLETE] Project analysis complete. Generated {len(results)} results")
    info(f"Analysis complete. Generated {len(results)} results")
    
    return results


def show_help():
    """Display help information for .NET package installer."""
    help_text = """
.NET Package Installer - ARM64 Compatibility Analyzer

USAGE:
    python dotnet_package_installer.py <project_file> [OPTIONS]

ARGUMENTS:
    project_file        Path to .csproj or project file to analyze

OPTIONS:
    -v, --verbose      Enable verbose output with detailed logging
    -o, --output FILE  Save analysis results to specified JSON file
    -h, --help         Show this help message and exit

DESCRIPTION:
    Analyzes .NET project files for ARM64/Graviton compatibility by testing
    package restoration with ARM64 runtime. Generates detailed compatibility
    reports with installation status and native build detection.

EXAMPLES:
    python dotnet_package_installer.py MyProject.csproj
    python dotnet_package_installer.py MyProject.csproj -v -o results.json

OUTPUT:
    JSON format with compatibility status, installation results, and
    recommendations for each package dependency.
    """
    print(help_text)

def main():
    """Main function for .NET package installer."""
    debug(f"[DOTNET_MAIN_START] .NET Package Installer starting with args: {sys.argv[1:]}")
    
    parser = argparse.ArgumentParser(description='Analyze .NET packages for ARM compatibility', add_help=False)
    parser.add_argument('project_file', nargs='?', help='Path to .csproj or project file')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-o', '--output', help='Output JSON file path')
    parser.add_argument('-h', '--help', action='store_true', help='Show help message')
    
    args = parser.parse_args()
    
    if args.help or not args.project_file:
        show_help()
        if not args.project_file:
            print("\nError: project_file is required.", file=sys.stderr)
            return 1
        return 0
    
    debug(f"[DOTNET_MAIN_ARGS] Parsed arguments: project_file='{args.project_file}', verbose={args.verbose}, output='{args.output}'")
    
    if args.verbose or os.environ.get('DEBUG'):
        debug(f"[DOTNET_MAIN_LOGGING] Enabling DEBUG logging level")
        logger.setLevel(logging.DEBUG)
    else:
        debug(f"[DOTNET_MAIN_LOGGING] Using INFO logging level")
    
    project_file = os.path.abspath(args.project_file)
    debug(f"[DOTNET_MAIN_INPUT] Resolved project file path: {project_file}")
    
    if not os.path.exists(project_file):
        error(f"[DOTNET_MAIN_ERROR] Project file not found: {project_file}")
        print(f"Error: Project file not found: {project_file}", file=sys.stderr)
        print("Use -h or --help for usage information.", file=sys.stderr)
        return 1
    
    try:
        debug(f"[DOTNET_MAIN_ANALYSIS] Starting project file analysis")
        results = analyze_project_file(project_file)
        debug(f"[DOTNET_MAIN_RESULTS] Analysis produced {len(results)} results")
        
        if not results:
            debug(f"[DOTNET_MAIN_NO_RESULTS] No packages found to analyze")
            info("No packages found to analyze")
            return 0
        
        # Convert ComponentResult objects to flattened JSON format (matching SBOM structure)
        debug(f"[DOTNET_MAIN_JSON] Converting {len(results)} ComponentResult objects to flattened JSON format")
        results_json = []
        for i, result in enumerate(results):
            if i < 3:  # Log details for first 3 results
                debug(f"[DOTNET_MAIN_JSON] Converting result {i+1}: {result.component.name}:{result.component.version} -> {result.compatibility.status.value}")
            
            # Flattened structure matching SBOM format but preserving all fields
            result_dict = {
                "name": result.component.name,
                "version": result.component.version,
                "type": result.component.component_type,
                "source_sbom": result.component.source_sbom,
                "compatibility": {
                    "status": result.compatibility.status.value,
                    "current_version_supported": result.compatibility.current_version_supported,
                    "minimum_supported_version": result.compatibility.minimum_supported_version,
                    "recommended_version": result.compatibility.recommended_version,
                    "notes": result.compatibility.notes,
                    "confidence_level": result.compatibility.confidence_level
                },
                "parent_component": result.component.parent_component,
                "child_components": result.component.child_components,
                "source_package": result.component.source_package
            }
            
            # Add matched name if available
            if result.matched_name:
                result_dict["matched_name"] = result.matched_name
            
            # Add properties if available
            if result.component.properties:
                result_dict["properties"] = result.component.properties
            
            results_json.append(result_dict)
        
        debug(f"[DOTNET_MAIN_JSON_COMPLETE] Successfully converted all results to JSON format")
        
        # Output results
        debug(f"[DOTNET_MAIN_OUTPUT] Generating JSON output")
        output_json = json.dumps(results_json, indent=2)
        debug(f"[DOTNET_MAIN_OUTPUT] JSON output size: {len(output_json)} characters")
        
        if args.output:
            debug(f"[DOTNET_MAIN_OUTPUT_FILE] Writing results to file: {args.output}")
            with open(args.output, 'w') as f:
                f.write(output_json)
            debug(f"[DOTNET_MAIN_OUTPUT_FILE_COMPLETE] Results written to file successfully")
            if args.verbose:
                info(f"Analysis results saved to: {args.output}")
        else:
            debug(f"[DOTNET_MAIN_OUTPUT_STDOUT] Writing results to stdout")
            print(output_json)
        
        # Summary
        if args.verbose and results_json:
            debug(f"[DOTNET_MAIN_SUMMARY] Generating analysis summary")
            total = len(results_json)
            compatible = sum(1 for r in results_json if r['compatibility']['status'] == 'compatible')
            incompatible = sum(1 for r in results_json if r['compatibility']['status'] == 'incompatible')
            needs_verification = sum(1 for r in results_json if r['compatibility']['status'] == 'needs_verification')
            needs_upgrade = sum(1 for r in results_json if r['compatibility']['status'] == 'needs_upgrade')
            unknown = sum(1 for r in results_json if r['compatibility']['status'] == 'unknown')
            
            debug(f"[DOTNET_MAIN_SUMMARY_STATS] total={total}, compatible={compatible}, incompatible={incompatible}, needs_upgrade={needs_upgrade}, needs_verification={needs_verification}, unknown={unknown}")
            
            info(f"Analysis Summary:")
            info(f"  Total components: {total}")
            info(f"  Compatible: {compatible}")
            info(f"  Incompatible: {incompatible}")
            info(f"  Needs upgrade: {needs_upgrade}")
            info(f"  Needs verification: {needs_verification}")
            info(f"  Unknown: {unknown}")
        
        # Return appropriate exit code
        if results_json:
            incompatible_count = sum(1 for r in results_json if r['compatibility']['status'] == 'incompatible')
            debug(f"[DOTNET_MAIN_EXIT_CODE] Found {incompatible_count} incompatible components")
            if incompatible_count > 0:
                debug(f"[DOTNET_MAIN_EXIT_CODE] Returning exit code 2 due to incompatible components")
                return 2
            else:
                debug(f"[DOTNET_MAIN_EXIT_CODE] Returning exit code 0 (success)")
                return 0
        else:
            debug(f"[DOTNET_MAIN_EXIT_CODE] No results, returning exit code 0")
            return 0
    
    except Exception as e:
        error(f"[DOTNET_MAIN_ERROR] .NET Package Installer failed: {e}")
        debug(f"[DOTNET_MAIN_ERROR_DETAILS] Exception type: {type(e).__name__}")
        import traceback
        debug(f"[DOTNET_MAIN_ERROR_TRACEBACK] {traceback.format_exc()}")
        return 1


if __name__ == '__main__':
    start_time = time.time()
    debug(f"[DOTNET_MAIN_ENTRY] .NET Package Installer starting at {datetime.utcnow().isoformat()}Z")
    debug(f"[DOTNET_MAIN_ENTRY] Python version: {sys.version}")
    debug(f"[DOTNET_MAIN_ENTRY] Working directory: {os.getcwd()}")
    debug(f"[DOTNET_MAIN_ENTRY] Environment DEBUG: {os.environ.get('DEBUG', 'not set')}")
    
    try:
        exit_code = main()
        duration = time.time() - start_time
        debug(f"[DOTNET_MAIN_EXIT] Execution completed in {duration:.2f}s with exit code {exit_code}")
        info(f".NET Package Installer finished in {duration:.2f}s with exit code {exit_code}")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        duration = time.time() - start_time
        debug(f"[DOTNET_MAIN_INTERRUPT] Execution interrupted after {duration:.2f}s")
        info(f".NET Package Installer interrupted after {duration:.2f}s")
        sys.exit(130)
    except Exception as e:
        duration = time.time() - start_time
        error(f"[DOTNET_MAIN_EXCEPTION] Unhandled exception after {duration:.2f}s: {e}")
        import traceback
        debug(f"[DOTNET_MAIN_EXCEPTION_TRACEBACK] {traceback.format_exc()}")
        sys.exit(1)