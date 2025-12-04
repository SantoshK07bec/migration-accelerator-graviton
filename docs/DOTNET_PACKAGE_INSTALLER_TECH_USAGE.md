# .NET Package Installer - Technical & Usage Documentation

## Overview

The `dotnet_package_installer.py` script is a Python-based .NET package compatibility tester designed for ARM64/Graviton compatibility analysis. It performs real package restore testing with intelligent error classification and comprehensive status determination using the standardized ComponentResult schema from models.py.

## Prerequisites

### System Requirements

- **.NET SDK**: Version 8.0 or higher
- **Operating System**: Windows, Linux, or macOS
- **Network Access**: Internet connectivity to NuGet registry (nuget.org)
- **Disk Space**: Sufficient space for temporary project creation and package downloads
- **Permissions**: Write access to temporary directory

### Required Tools

- **dotnet CLI**: Must be available in PATH for package operations
- **.NET Runtime**: ARM64 runtime support for accurate testing
- **NuGet**: Package manager (bundled with .NET SDK)

### Environment Setup

```bash
# Verify .NET SDK
dotnet --version  # Should be >= 8.0

# Verify NuGet connectivity
dotnet nuget list source

# Test ARM64 runtime support
dotnet --list-runtimes | grep linux-arm64

# Check temporary directory access
echo $TMPDIR || echo %TEMP%
```

## Assumptions

### Input File Assumptions

1. **Valid .csproj Format**: Input file follows standard MSBuild project format
2. **PackageReference Elements**: Uses `<PackageReference Include="Name" Version="X.Y.Z" />` format
3. **File Accessibility**: Project file is readable by the script process
4. **Character Encoding**: Input file uses UTF-8 encoding
5. **Well-formed XML**: Project file is valid XML structure

### Package Testing Assumptions

1. **NuGet Registry Access**: Assumes packages are available on public NuGet registry
2. **ARM64 Runtime Testing**: Tests compatibility with `linux-arm64` runtime identifier
3. **Temporary Project Creation**: Can create temporary projects in system temp directory
4. **Network Reliability**: Stable internet connection for package downloads
5. **Clean Environment**: No conflicting package locks or corrupted NuGet cache

### System Environment Assumptions

1. **Working Directory**: Script runs in directory with write permissions
2. **Process Permissions**: Can spawn child processes (dotnet restore)
3. **Timeout Handling**: Package operations complete within reasonable time
4. **Resource Availability**: Sufficient memory and CPU for package restoration
5. **Clean State**: No conflicting .NET processes or locks

## Technical Architecture

### Design Principles
- **Standalone Execution**: Runs independently without external dependencies
- **Individual Package Testing**: Tests each package separately for clear attribution
- **Smart Error Classification**: Categorizes errors for intelligent status determination
- **Comprehensive Reporting**: Outputs standardized JSON matching runtime analysis schema
- **Per-Package Cleanup**: Removes temporary files after each individual package test for resource efficiency

### Core Components

```csharp
// Main Functions
ExtractPackageReferences(projectFile)        // Parse .csproj for PackageReference elements
TestPackageCompatibility(name, version)      // Individual package compatibility test
RunDotNetCommand(arguments, workingDir)      // Execute dotnet CLI commands
DetermineCompatibilityStatus(exitCode, output, error)  // Intelligent status logic
ClassifyError(error)                         // Error type classification
ExtractRelevantError(error)                  // Smart error detail extraction
GenerateNotes(exitCode, output, error, name, version)  // Human-readable explanations
```

## Usage

### Command Line Interface

```bash
# Basic usage
python -m graviton_validator.analysis.dotnet_package_installer <project_file>

# Enable debug logging for troubleshooting
DEBUG=1 python -m graviton_validator.analysis.dotnet_package_installer project.csproj

# Verbose output with summary
python -m graviton_validator.analysis.dotnet_package_installer project.csproj -v

# Save output to file
python -m graviton_validator.analysis.dotnet_package_installer project.csproj -o results.json

# Container execution (recommended for ARM64 testing)
docker run --rm -v $(pwd):/workspace -w /workspace python:3.10 \
  python -m graviton_validator.analysis.dotnet_package_installer project.csproj

# Container execution with debug logging
docker run --rm -v $(pwd):/workspace -w /workspace -e DEBUG=1 python:3.10 \
  python -m graviton_validator.analysis.dotnet_package_installer project.csproj
```

### Input Format

**Project File** (`project.csproj`):
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
    <PackageReference Include="Microsoft.Extensions.Logging" Version="8.0.0" />
    <PackageReference Include="System.Text.Json" Version="8.0.0" />
  </ItemGroup>
</Project>
```

### Output Format

**JSON Array** with ComponentResult schema from models.py:
```json
[
  {
    "component": {
      "name": "Newtonsoft.Json",
      "version": "13.0.3",
      "component_type": "dotnet-8.0",
      "source_sbom": "runtime_analysis",
      "properties": {
        "environment": "native_dotnet_8.0_amazon-linux-2023",
        "native_build_detected": "No",
        "install_status": "Success",
        "fallback_used": "false",
        "original_version": "13.0.3",
        "test_output": "Restoring packages for test.csproj...\nRestored test.csproj (in 2.1 sec).",
        "test_execution_output": "N/A - No test script available",
        "error_details": "",
        "error_type": "unknown",
        "timestamp": "2025-10-08T15:30:45Z",
        "runtime_analysis": "true"
      },
      "parent_component": null,
      "child_components": [],
      "source_package": null
    },
    "compatibility": {
      "status": "compatible",
      "current_version_supported": true,
      "minimum_supported_version": null,
      "recommended_version": null,
      "notes": "Successfully restored Newtonsoft.Json==13.0.3 for ARM64",
      "confidence_level": 0.9
    },
    "matched_name": null
  }
]
```

## Testing Strategy

### Package Compatibility Testing

```
For each PackageReference:
  1. Create temporary test project with single package (unique GUID directory)
  2. Execute: dotnet restore --runtime linux-arm64
  3. Analyze exit code, stdout, and stderr
  4. Classify error type and determine status
  5. Generate human-readable notes
  6. Clean up temporary files immediately (per-package cleanup)
```

**Cleanup Strategy**: Each package test creates and destroys its own temporary directory, ensuring:
- **Resource Efficiency**: No accumulation of temporary files
- **Test Isolation**: Each package test is completely independent
- **Container Friendly**: Works well in resource-constrained environments

### Status Decision Logic

```csharp
// Pseudo-code for status determination
if (exitCode == 0):
    status = "compatible"  // Package restored successfully
else:
    if (network_error):
        status = "unknown"  // Cannot determine due to connectivity
    elif (package_not_found):
        status = "incompatible"  // Package doesn't exist
    elif (version_not_found):
        status = "needs_upgrade"  // Specific version missing
    elif (runtime_incompatible):
        status = "incompatible"  // No ARM64 support
    else:
        status = "unknown"  // Unclear failure reason
```

### Error Classification System

| Error Type | Indicators | Description |
|------------|------------|-------------|
| `network` | "service index", "timeout", "connection" | Network/connectivity issues |
| `dependency` | "not found", "version", "constraint" | Package or version resolution issues |
| `permissions` | "permission", "access" | File system permission errors |
| `unknown` | Default | Unclassified or unclear errors |

## Field Descriptions

### ComponentResult Schema Fields

#### Component Object

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `name` | string | Package name | "Newtonsoft.Json" |
| `version` | string | Tested version | "13.0.3" |
| `component_type` | string | Runtime type | "dotnet-8.0" |
| `source_sbom` | string | Analysis source | "runtime_analysis" |
| `properties` | object | Runtime-specific metadata | See properties table below |
| `parent_component` | string/null | Parent component name | null |
| `child_components` | array | Child component names | [] |
| `source_package` | string/null | Source package name | null |

#### Compatibility Object

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `status` | enum | Compatibility result | "compatible" |
| `current_version_supported` | boolean | Current version works | true |
| `minimum_supported_version` | string/null | Minimum working version | null |
| `recommended_version` | string/null | Recommended version | null |
| `notes` | string | Human-readable summary | "Successfully restored for ARM64" |
| `confidence_level` | float | Analysis confidence | 0.9 |

#### Properties Object

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `environment` | string | Runtime environment | "native_dotnet_8.0_amazon-linux-2023" |
| `native_build_detected` | string | Native compilation detected (always "No" for .NET) | "No" |
| `install_status` | string | Package restore result | "Success" or "Failed" |
| `fallback_used` | string | Version fallback used (always "false") | "false" |
| `original_version` | string | Requested version | "13.0.3" |
| `test_output` | string | Complete dotnet command output | "Restoring packages..." |
| `test_execution_output` | string | Test suite output (always "N/A - No test script available") | "N/A - No test script available" |
| `error_details` | string | Extracted error info (empty on success) | "error NU1101: Unable to find package..." |
| `error_type` | string | Error classification ("unknown" on success) | "dependency", "network", "unknown" |
| `timestamp` | string | ISO timestamp | "2025-10-08T15:30:45Z" |
| `runtime_analysis` | string | Runtime analysis flag (always "true") | "true" |

## Status Categories

| Status | Meaning | Conditions |
|--------|---------|------------|
| `compatible` | Package works on ARM64 | **Package restore successful** (dotnet restore exits with code 0) |
| `incompatible` | Package fails on ARM64 | **Package doesn't exist** OR **no ARM64 support** OR **runtime incompatible** |
| `needs_upgrade` | Specific version fails, newer available | **Version not found** but package exists (version constraint errors) |
| `unknown` | Cannot determine compatibility | **Network issues** OR **unclear errors** OR **ambiguous failures** |
| `needs_verification` | Manual verification required | **Not used in .NET script** (no native build detection implemented) |

### Status Logic Examples

#### `compatible` Status
- **Successful Restore**: `dotnet restore` completes without errors
- **ARM64 Support**: Package has ARM64-compatible binaries or is platform-agnostic
- **Example**: Pure .NET libraries, cross-platform packages

#### `incompatible` Status  
- **Package Not Found**: `error NU1101: Unable to find package PackageName`
- **Runtime Incompatible**: `error NU1202: Package is not compatible with linux-arm64`
- **Example**: Windows-specific packages, x86-only native libraries

#### `needs_upgrade` Status
- **Version Not Found**: `error NU1102: Unable to find package PackageName with version (>= X.Y.Z)`
- **Constraint Conflicts**: Version exists but conflicts with other dependencies
- **Example**: Deprecated versions, version range mismatches

#### `unknown` Status
- **Network Issues**: `error NU1301: Unable to load the service index`
- **Timeout Errors**: Connection timeouts to NuGet registry
- **Unclear Failures**: Ambiguous error messages or unexpected exceptions

## Error Handling

### Network Error Detection
```csharp
if (errorLower.Contains("unable to load the service index") ||
    errorLower.Contains("timeout") ||
    errorLower.Contains("connection"))
    return "unknown";  // Cannot determine compatibility
```

### Package Resolution Errors
```csharp
if (errorLower.Contains("unable to find package") && 
    errorLower.Contains("no packages exist"))
    return "incompatible";  // Package doesn't exist

if (errorLower.Contains("unable to find package") && 
    errorLower.Contains("version"))
    return "needs_upgrade";  // Version not found
```

### Runtime Compatibility Errors
```csharp
if (errorLower.Contains("not compatible with") ||
    errorLower.Contains("linux-arm64"))
    return "incompatible";  // No ARM64 support
```

## Performance Characteristics

### Timing
- **Individual Testing**: Each package tested separately
- **Sequential Processing**: One package at a time
- **Clean Environment**: Temporary project per package

### Resource Usage
- **Memory**: Minimal, temporary projects only
- **Disk**: Temporary project files and package downloads
- **Network**: NuGet package downloads only

## Container Integration

### ARM64 Testing
```bash
# Test on ARM64 system for accurate results
docker run --platform linux/arm64 mcr.microsoft.com/dotnet/sdk:8.0 \
  dotnet run dotnet_package_installer.cs project.csproj
```

## Limitations

### Testing Scope
- **No Test Execution**: Doesn't run package unit tests
- **Restore Only**: Only tests package restoration, not runtime behavior
- **Individual Package Projects**: Tests each package in separate temporary projects, but includes full dependency trees

### Architecture Accuracy
- **Host Dependent**: Results depend on execution architecture
- **ARM64 Recommended**: Run on Graviton systems for accurate results
- **Container Preferred**: Use ARM64 containers for consistent testing

### Error Handling
- **No Retry Logic**: Single attempt per package
- **Network Dependent**: Requires NuGet connectivity
- **Limited Fallback**: No automatic version fallback testing
- **No Version Grouping**: Tests each package version separately (future optimization: group multiple versions of same package for efficiency)

## Best Practices

### For Accurate Results
1. **Run on ARM64**: Execute on Graviton instances or ARM64 containers
2. **Clean Environment**: Use fresh containers for each test run
3. **Network Stability**: Ensure reliable NuGet connectivity
4. **Valid Input**: Verify .csproj file format before testing

## Integration with Graviton Validator

### Runtime Analysis Flow
```
SBOM Analysis → .csproj Generation → Container Execution → Result Collection
```

### Schema Compliance
- Outputs match `runtime_analysis_result_schema.json`
- Compatible with multi-runtime analysis pipeline
- Consistent field naming across all runtime analyzers

## Troubleshooting

### Common Issues

| Issue | Symptoms | Solution |
|-------|----------|----------|
| **Missing .NET SDK** | "dotnet: command not found" | Install .NET 8.0 SDK |
| **Invalid .csproj** | XML parsing errors | Validate project file format |
| **Network Issues** | Service index errors | Check internet connectivity and NuGet sources |
| **Permission Errors** | Temp directory access denied | Ensure write permissions to temp directory |
| **ARM64 Runtime Missing** | Runtime not found warnings | Install ARM64 runtime or use ARM64 container |

### Debug Commands

```bash
# Verify .NET installation
dotnet --info

# Check NuGet sources
dotnet nuget list source

# Test package manually
dotnet add package PackageName --version X.Y.Z
dotnet restore --runtime linux-arm64

# Clear NuGet cache
dotnet nuget locals all --clear
```

## Understanding `dotnet restore --runtime linux-arm64`

The core testing command `dotnet restore --runtime linux-arm64` asks: *"Can this package and all its dependencies be downloaded and used on an ARM64 Linux system?"* - which is exactly what we need for Graviton compatibility assessment.

### What the Command Does:
1. **Runtime-Specific Resolution**: Looks for packages compatible with `linux-arm64` runtime identifier
2. **Asset Selection**: Selects ARM64-specific binaries when available
3. **Dependency Chain Validation**: Ensures all transitive dependencies support ARM64
4. **Native Binary Check**: Packages with native code must have ARM64 binaries
5. **Compatibility Verification**: Only succeeds if entire dependency graph supports ARM64

### What It Tests vs. Doesn't Test:
- ✅ **Tests**: Package availability and ARM64 asset compatibility
- ❌ **Doesn't Test**: Runtime behavior, performance, or native code correctness

This comprehensive documentation provides complete guidance for the .NET package installer with intelligent error handling and ARM64 compatibility detection.
