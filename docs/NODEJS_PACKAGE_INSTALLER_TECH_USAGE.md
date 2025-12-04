# Node.js Package Installer - Technical & Usage Documentation

## Overview

The `nodejs_package_installer.py` script is an enhanced Node.js package compatibility analyzer that tests individual packages for ARM64/Graviton compatibility. It provides comprehensive analysis including installation testing, test execution, native build detection, and detailed error reporting. The script is implemented in Python and outputs results using the ComponentResult schema from models.py.

## Features

- **Individual Package Testing**: Tests each package separately with version fallback
- **Test Suite Execution**: Runs `npm test` when available and captures output
- **Native Build Detection**: Detects native modules via npm output and file system scanning
- **Enhanced Error Reporting**: Classifies errors and provides detailed troubleshooting information
- **Configurable Logging**: INFO level by default, DEBUG level for troubleshooting
- **Duplicate Handling**: Automatically removes duplicate package entries
- **Alternative File Detection**: Supports `package.json`, `*_package.json`, and `*-package.json` files

## Prerequisites

### System Requirements

- **Python**: Version 3.7 or higher
- **Node.js**: Version 12.0 or higher
- **npm**: Version 6.0 or higher (typically bundled with Node.js)
- **Operating System**: Linux, macOS, or Windows with WSL
- **Network Access**: Internet connectivity to npm registry (registry.npmjs.org)
- **Disk Space**: Sufficient space for temporary package installations in `node_modules/`
- **Permissions**: Write access to current directory for `node_modules/` creation

### Required Tools

- **npm CLI**: Must be available in PATH for package installation
- **Build Tools** (for native packages): 
  - Linux (Ubuntu/Debian): `build-essential`, `python3`
  - Linux (Fedora/RHEL/CentOS): `gcc`, `gcc-c++`, `make`, `python3`
  - Linux (Arch): `base-devel`, `python`
  - macOS: Xcode Command Line Tools
  - Windows: Visual Studio Build Tools or Windows Build Tools

**Why Python is needed**: Many Node.js packages with native components use `node-gyp` for compilation, which requires Python to run build scripts and configure the compilation process. Python is used to parse `binding.gyp` files and generate appropriate Makefiles for the target platform.

### Environment Setup

```bash
# Verify Python installation
python3 --version  # Should be >= 3.7

# Verify Node.js installation
node --version  # Should be >= 12.0
npm --version   # Should be >= 6.0

# Ensure npm registry access
npm ping        # Should return "Ping success"

# Install build tools (choose based on your Linux distribution)
# Ubuntu/Debian:
sudo apt-get update && sudo apt-get install build-essential python3

# Fedora/RHEL/CentOS:
sudo dnf install gcc gcc-c++ make python3
# OR for older versions: sudo yum install gcc gcc-c++ make python3

# Arch Linux:
sudo pacman -S base-devel python

# macOS:
xcode-select --install

# Check build tools (for native packages)
npm config get python  # Should show Python path (required by node-gyp)
which gcc g++ make     # Should show compiler paths
python3 --version      # Should be Python 2.7 or 3.x
```

## Assumptions

### Input File Assumptions

1. **Valid JSON Format**: Input file must be valid JSON with proper syntax
2. **Dependencies Structure**: Expects standard `package.json` format with `dependencies` object
3. **Version Specifications**: Supports npm semver format (^1.0.0, ~2.1.0, >=3.0.0, etc.)
4. **File Accessibility**: Input file must be readable by the script process
5. **Alternative Naming**: Supports `package.json`, `*_package.json`, and `*-package.json` patterns

### Package Testing Assumptions

1. **npm Registry Access**: Assumes packages are available on public npm registry
2. **Package Availability**: Does not handle private registries or scoped private packages
3. **Installation Permissions**: Assumes write permissions to create `node_modules/` directory
4. **Temporary Installation**: Packages are installed temporarily and may affect local environment
5. **Test Script Format**: Assumes standard npm test script format in `package.json`

### Network and Security Assumptions

1. **Internet Connectivity**: Requires stable internet connection for package downloads
2. **Registry Trust**: Trusts npm registry and downloaded packages (no malware scanning)
3. **Firewall Configuration**: Assumes npm registry URLs are not blocked
4. **Proxy Support**: Uses npm's configured proxy settings if any
5. **Rate Limiting**: May be subject to npm registry rate limits

### System Environment Assumptions

1. **Working Directory**: Script runs in directory where `node_modules/` can be created
2. **Process Permissions**: Sufficient permissions to spawn child processes (npm, node)
3. **Timeout Handling**: npm operations complete within configured timeouts (60s for tests, 120s for installs)
4. **Resource Availability**: Sufficient memory and CPU for package compilation
5. **Clean State**: No conflicting `node_modules/` or `package-lock.json` files

### Output and Logging Assumptions

1. **JSON Output**: Consumers expect valid JSON array output on stdout
2. **Log Separation**: Logs go to stderr, JSON results to stdout
3. **Character Encoding**: All output uses UTF-8 encoding
4. **Error Handling**: Script continues processing even if individual packages fail
5. **Deterministic Results**: Same input should produce consistent results (barring registry changes)

### Native Build Assumptions

1. **Build Tool Availability**: Native packages assume presence of compilers and build tools
2. **Python for node-gyp**: Many native packages use `node-gyp` which requires Python (2.7 or 3.x) to parse `binding.gyp` files and generate build configurations
3. **Platform Detection**: Assumes standard file extensions and build patterns
4. **File System Access**: Can read installed package files for native detection
5. **Architecture Compatibility**: Tests on current system architecture (may not reflect target ARM64)
6. **Build Dependencies**: Native packages have all required system dependencies

## Usage

### Recommended Environment

**⚠️ Important**: For accurate ARM64/Graviton compatibility results, it is **strongly recommended** to run this script on an ARM64/Graviton system. Running on x86_64 systems may produce false positives or miss architecture-specific compatibility issues.

```bash
# Check current architecture
uname -m  # Should show 'aarch64' for ARM64/Graviton systems
```

### Basic Usage

```bash
# Basic usage
python3 nodejs_package_installer.py package.json

# Enable debug logging
NODE_LOG_LEVEL=DEBUG python3 nodejs_package_installer.py package.json
```

### Cleanup Behavior

**✅ Automatic Cleanup**: The script **automatically cleans up** temporary files and installed packages after analysis completion. The following files are removed:

- `node_modules/` directory (recursively)
- `package-lock.json` file

**Cleanup Process**:
- Runs after all package testing is completed
- Runs even if the script encounters errors during testing
- Logs cleanup progress (visible with debug logging)
- Continues execution even if cleanup partially fails

**Manual Cleanup** (if needed):
```bash
# If automatic cleanup fails, manually remove:
rm -rf node_modules/
rm -f package-lock.json
```

## Output Schema

The script outputs a JSON array using the ComponentResult schema from models.py. Each result contains a component and compatibility analysis:

```json
[
  {
    "component": {
      "name": "package-name",
      "version": "1.0.0",
      "component_type": "nodejs",
      "source_sbom": "runtime_analysis",
      "properties": {
        "environment": "native_nodejs_v16.17.1_amazon-linux-2023",
        "native_build_detected": "Yes|No",
        "install_status": "Success|Failed",
        "fallback_used": "true|false",
        "original_version": "requested version",
        "test_output": "npm install output",
        "test_execution_output": "npm test output or N/A - No test script",
        "error_details": "Detailed error information",
        "error_type": "network|native_build|permissions|dependency|unknown",
        "timestamp": "2025-10-08T07:18:39.478Z",
        "runtime_analysis": "true"
      },
      "parent_component": null,
      "child_components": [],
      "source_package": null
    },
    "compatibility": {
      "status": "compatible|incompatible|needs_upgrade|needs_verification",
      "current_version_supported": true|false,
      "minimum_supported_version": "1.0.0",
      "recommended_version": null,
      "notes": "Detailed analysis message",
      "confidence_level": 0.9
    },
    "matched_name": null
  }
]
```

## Field Descriptions

### ComponentResult Structure

| Field | Type | Description | How It's Determined |
|-------|------|-------------|-------------------|
| `component` | SoftwareComponent | Package information | Extracted from package.json dependencies |
| `compatibility` | CompatibilityResult | Analysis results | Based on installation success and native build detection |
| `matched_name` | string | Intelligent matching | Always null for runtime analysis |

### SoftwareComponent Fields

| Field | Type | Description | How It's Determined |
|-------|------|-------------|-------------------|
| `name` | string | Package name | Extracted from package.json dependencies |
| `version` | string | Tested version | Version from package.json or fallback version |
| `component_type` | string | Runtime type | Always "nodejs" |
| `source_sbom` | string | Analysis source | Always "runtime_analysis" |
| `properties` | dict | Runtime metadata | Detailed analysis information |

### CompatibilityResult Fields

| Field | Type | Description | How It's Determined |
|-------|------|-------------|-------------------|
| `status` | enum | Compatibility status | Based on installation success and native build detection |
| `current_version_supported` | bool | Version support | True if requested version works |
| `minimum_supported_version` | string | Minimum version | Working version or fallback version |
| `recommended_version` | string | Recommended version | Set for upgrades, null otherwise |
| `notes` | string | Human-readable analysis | Combines installation result, test result, and error details |
| `confidence_level` | float | Analysis confidence | 0.9 for successful tests, 0.85 for fallbacks |

### Installation Fields

| Field | Type | Description | How It's Determined |
|-------|------|-------------|-------------------|
| `install_status` | enum | Installation result | "Success" if npm install exit code = 0, "Failed" otherwise |
| `test_output` | string | npm install output | Raw stdout from npm install command |
| `fallback_used` | boolean | Whether fallback was used | True if specific version failed but latest succeeded |
| `original_version` | string | Originally requested version | Version from package.json dependencies |

### Test Execution Fields

| Field | Type | Description | How It's Determined |
|-------|------|-------------|-------------------|
| `test_execution_output` | string | Test execution result | npm test stdout/stderr or "N/A - No test script" |

### Native Build Detection

| Field | Type | Description | How It's Determined |
|-------|------|-------------|-------------------|
| `native_build_detected` | enum | Native build presence | "Yes" if npm output contains native indicators OR native files found in node_modules |

**Native Indicators in npm output:**
- `node-gyp`, `binding.gyp`, `gyp info`
- `node-pre-gyp`, `prebuild-install`
- `make:`, `gcc`, `g++`, `clang`
- `compiled successfully`

**Native Files in file system:**
- Build files: `binding.gyp`, `wscript`, `Makefile`, `CMakeLists.txt`
- Config files: `configure`, `configure.ac`, `configure.in`
- Binary files: `.so`, `.dylib`, `.dll`, `.node`

### Error Analysis Fields

| Field | Type | Description | How It's Determined |
|-------|------|-------------|-------------------|
| `error_details` | string | Extracted error information | **Specialized head/tail extraction** (see below) |
| `error_type` | enum | Error classification | Pattern matching on error messages |

#### Specialized Error Handling

The script implements **advanced error extraction** similar to the original bash script:

**Short Errors (≤40 lines)**: Returns complete error output

**Long Errors (>40 lines)**: Uses **head/tail extraction**:
- **Head**: First 20 lines, filtered for error keywords
- **Separator**: `...` to indicate truncation
- **Tail**: Last 20 lines, filtered for error keywords
- **Fallback**: If no error keywords found, uses first 5 + last 5 lines
- **Length Limit**: Truncated to 2000 characters maximum

**Error Keywords**: `error`, `failed`, `enoent`, `permission denied`, `network`, `timeout`, `enotfound`

**Example Error Extraction**:
```
# Input: 50-line npm install error
# Output:
npm ERR! code E404
npm ERR! 404 Not Found - GET https://registry.npmjs.org/package
npm ERR! 404 'package' is not in the npm registry
...
npm ERR! A complete log of this run can be found in:
npm ERR!     /home/user/.npm/_logs/2025-10-09T14_30_00_000Z-debug.log
```

**Error Classification Logic:**
- `network`: Contains "enotfound", "network", "timeout", "404", "not found", "registry"
- `native_build`: Contains "gyp", "make", "compile"
- `permissions`: Contains "permission", "eacces"
- `dependency`: Contains "dependency", "peer dep"
- `unknown`: Default when no patterns match

### Status Determination Logic

| Status | Conditions |
|--------|------------|
| `compatible` | Installation successful AND no native build detected |
| `needs_verification` | Installation successful AND native build detected |
| `needs_upgrade` | Specific version failed BUT latest version succeeded AND no native build |
| `incompatible` | All versions (including latest) failed to install |

## Logging System

### Log Levels

- **ERROR**: Critical failures only
- **WARN**: Warning conditions
- **INFO**: Essential progress information (default)
- **DEBUG**: Detailed troubleshooting information

### Log Format

```
[2025-10-08T07:24:15.997Z] INFO: Testing package: lodash (1 version)
[2025-10-08T07:24:15.997Z] DEBUG: Versions to test: ^4.17.21
```

### Debug Information Captured

- Package discovery and file resolution
- Dependency grouping and deduplication
- Installation command execution and results
- Test script detection and execution
- Native build detection process
- Error classification decisions
- Performance and completion tracking

## Processing Flow

### 1. Package Discovery
```
Input: package.json path
↓
Check if file exists
↓
If not found: Search for *_package.json, *-package.json
↓
Parse JSON and extract dependencies
```

### 2. Package Grouping
```
Dependencies object
↓
Group by package name (handle scoped packages)
↓
Remove duplicates using Set
↓
Sort versions for consistent processing
```

### 3. Version Testing Strategy
```
For each package:
  Test specific version first
  ↓
  If successful: Run tests, detect native builds
  ↓
  If failed: Try latest version as fallback
  ↓
  If fallback succeeds: Mark as needs_upgrade
  ↓
  If all fail: Mark as incompatible
```

### 4. Test Execution
```
Check if package.json has test script
↓
If yes: Run npm test, capture output
↓
If no: Set test_execution_output to "N/A - No test script"
↓
Update notes based on test success/failure
```

### 5. Native Build Detection
```
Check npm install output for native indicators
↓
If found: Return "Yes"
↓
If not found: Scan node_modules for native files
↓
Return "Yes" if native files found, "No" otherwise
```

## Example Outputs

### Successful Pure JavaScript Package
```json
{
  "component": {
    "name": "lodash",
    "version": "^4.17.21",
    "component_type": "nodejs",
    "source_sbom": "runtime_analysis",
    "properties": {
      "environment": "native_nodejs_v16.17.1_amazon-linux-2023",
      "native_build_detected": "No",
      "install_status": "Success",
      "fallback_used": "false",
      "original_version": "^4.17.21",
      "test_output": "up to date, audited 2 packages in 412ms\nfound 0 vulnerabilities",
      "test_execution_output": "N/A - No test script",
      "error_details": "",
      "error_type": "unknown",
      "timestamp": "2025-10-08T07:18:39.478Z",
      "runtime_analysis": "true"
    },
    "parent_component": null,
    "child_components": [],
    "source_package": null
  },
  "compatibility": {
    "status": "compatible",
    "current_version_supported": true,
    "minimum_supported_version": "^4.17.21",
    "recommended_version": null,
    "notes": "Successfully installed lodash@^4.17.21 Tests passed.",
    "confidence_level": 0.9
  },
  "matched_name": null
}
```

### Failed Package with Network Error
```json
{
  "component": {
    "name": "nonexistent-package",
    "version": "^1.0.0",
    "component_type": "nodejs",
    "source_sbom": "runtime_analysis",
    "properties": {
      "environment": "native_nodejs_v16.17.1_amazon-linux-2023",
      "native_build_detected": "No",
      "install_status": "Failed",
      "fallback_used": "true",
      "original_version": "^1.0.0",
      "test_output": "npm ERR! 404 Not Found - GET https://registry.npmjs.org/nonexistent-package",
      "test_execution_output": "",
      "error_details": "npm ERR! code E404; npm ERR! 404 Not Found - GET https://registry.npmjs.org/nonexistent-package",
      "error_type": "network",
      "timestamp": "2025-10-08T07:20:15.123Z",
      "runtime_analysis": "true"
    },
    "parent_component": null,
    "child_components": [],
    "source_package": null
  },
  "compatibility": {
    "status": "incompatible",
    "current_version_supported": false,
    "minimum_supported_version": null,
    "recommended_version": null,
    "notes": "All versions including latest failed to install: npm ERR! code E404",
    "confidence_level": 0.9
  },
  "matched_name": null
}
```

### Package with Native Build
```json
{
  "component": {
    "name": "bcrypt",
    "version": "^5.1.0",
    "component_type": "nodejs",
    "source_sbom": "runtime_analysis",
    "properties": {
      "environment": "native_nodejs_v16.17.1_amazon-linux-2023",
      "native_build_detected": "Yes",
      "install_status": "Success",
      "fallback_used": "false",
      "original_version": "^5.1.0",
      "test_output": "node-gyp rebuild\ngyp info it worked if it ends with ok",
      "test_execution_output": "✓ should hash password correctly",
      "error_details": "",
      "error_type": "unknown",
      "timestamp": "2025-10-08T07:22:30.456Z",
      "runtime_analysis": "true"
    },
    "parent_component": null,
    "child_components": [],
    "source_package": null
  },
  "compatibility": {
    "status": "needs_verification",
    "current_version_supported": true,
    "minimum_supported_version": "^5.1.0",
    "recommended_version": null,
    "notes": "Successfully installed bcrypt@^5.1.0 Tests passed.",
    "confidence_level": 0.9
  },
  "matched_name": null
}
```

### Version Fallback Scenario
```json
{
  "component": {
    "name": "old-package",
    "version": "1.0.0",
    "component_type": "nodejs",
    "source_sbom": "runtime_analysis",
    "properties": {
      "environment": "native_nodejs_v16.17.1_amazon-linux-2023",
      "native_build_detected": "No",
      "install_status": "Success",
      "fallback_used": "true",
      "original_version": "1.0.0",
      "test_output": "up to date, audited 1 package in 234ms",
      "test_execution_output": "N/A - No test script",
      "error_details": "npm ERR! deprecated",
      "error_type": "dependency",
      "timestamp": "2025-10-08T07:25:45.789Z",
      "runtime_analysis": "true"
    },
    "parent_component": null,
    "child_components": [],
    "source_package": null
  },
  "compatibility": {
    "status": "needs_upgrade",
    "current_version_supported": false,
    "minimum_supported_version": "2.1.0",
    "recommended_version": "2.1.0",
    "notes": "Version 1.0.0 failed (npm ERR! deprecated), but latest version 2.1.0 works",
    "confidence_level": 0.85
  },
  "matched_name": null
}
```

## Limitations and Considerations

### Testing Limitations

1. **Architecture Testing**: **CRITICAL** - For accurate results, run on ARM64/Graviton systems
2. **Automatic Cleanup**: Script automatically removes `node_modules/` and temporary files after testing
3. **Shallow Installation**: Uses `--no-save` flag, doesn't install peer dependencies
4. **Version Fallback**: Only tries specific version then latest, not all other intermediate versions
5. **Registry Scope**: Only tests packages from public npm registry
6. **Build Environment**: Native builds tested with current system's build tools

### Performance Considerations

1. **Sequential Processing**: Tests packages one at a time (not parallel)
2. **Network Dependent**: Performance limited by npm registry response times
3. **Disk I/O**: Uses shared `node_modules/` directory, accumulates packages during testing
4. **Memory Usage**: May accumulate memory during large package testing
5. **Timeout Constraints**: npm install (2 minutes), npm test (1 minute) - long-running builds may hit these limits

### Accuracy Limitations

1. **False Positives**: Package may work on ARM64 even if marked as incompatible
2. **False Negatives**: Package may fail on ARM64 even if marked as compatible. This can be minimized by testing on Graviton/arm64 system.
3. **Version Drift**: Registry changes between testing and actual deployment
4. **Environment Differences**: Production environment may differ from test environment
5. **Dependency Reporting**: Only reports on direct dependencies, not individual transitive dependencies

### Security Considerations

1. **Code Execution**: Downloads and potentially executes package code during testing
2. **Network Requests**: Makes requests to npm registry and package repositories
3. **File System Access**: Creates files and directories in current working directory
4. **Process Spawning**: Spawns npm and node processes with system permissions
5. **No Sandboxing**: No isolation from host system during package testing

## Troubleshooting

### Enable Debug Logging
```bash
NODE_LOG_LEVEL=DEBUG python3 nodejs_package_installer.py package.json
```

### Common Issues

1. **Package not found**: Check `error_type: "network"` and `error_details` for registry issues
2. **Native build failures**: Look for `native_build_detected: "Yes"` and `error_type: "native_build"`
3. **Permission errors**: Check `error_type: "permissions"` and ensure proper npm permissions
4. **Test failures**: Review `test_execution_output` for specific test error details
5. **Build tool missing**: Ensure native build tools are installed for packages requiring compilation
6. **Network timeouts**: Check internet connectivity and npm registry accessibility

### Debug Log Analysis

Debug logs provide step-by-step execution details:
- File discovery process
- Package grouping and deduplication
- Installation attempts and results
- Native build detection process
- Error classification decisions

### Environment Troubleshooting

```bash
# Check current architecture (should be aarch64 for ARM64)
uname -m

# Check Node.js and npm versions
node --version && npm --version

# Verify npm registry connectivity
npm ping

# Check npm configuration
npm config list

# Test basic package installation
npm install lodash --no-save

# Check build tools (Linux/macOS)
which gcc g++ make python3

# Check build tools (Windows)
npm config get msvs_version

# Test Python script syntax
python3 -m py_compile nodejs_package_installer.py

# Clean up after testing (manual cleanup required)
rm -rf node_modules/
rm -f package-lock.json
```
