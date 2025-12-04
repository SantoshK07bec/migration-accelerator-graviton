# Java Package Installer - Technical & Usage Documentation

## Overview

The `java_package_installer.py` script is a standalone Java package compatibility tester designed for ARM64/Graviton compatibility analysis. It has been rewritten to use the main script schema defined in `models.py`, outputting `ComponentResult` objects that are fully compatible with the main graviton validator pipeline.

## Schema Structure

The script now uses the main script schema with the following structure:

### ComponentResult
```python
ComponentResult:
  - component: SoftwareComponent     # What was tested
  - compatibility: CompatibilityResult  # Test results
  - matched_name: Optional[str]      # For intelligent matching
```

### SoftwareComponent
```python
SoftwareComponent:
  - name: str                       # Package name (artifactId)
  - version: str                    # Tested version  
  - component_type: str             # "java-17", "jar", etc.
  - source_sbom: str               # Always "runtime_analysis"
  - properties: Dict[str, str]      # Runtime-specific metadata
  - parent_component: Optional[str] # Parent component name
  - child_components: List[str]     # Child component names
  - source_package: Optional[str]   # Source package name
```

### CompatibilityResult
```python
CompatibilityResult:
  - status: CompatibilityStatus     # compatible/incompatible/etc.
  - current_version_supported: bool
  - minimum_supported_version: Optional[str]
  - recommended_version: Optional[str]
  - notes: str                      # Test details
  - confidence_level: float = 0.9  # High confidence for runtime testing
```

### CompatibilityStatus Enum
```python
CompatibilityStatus:
  - COMPATIBLE = "compatible"
  - INCOMPATIBLE = "incompatible"
  - NEEDS_UPGRADE = "needs_upgrade"
  - NEEDS_VERIFICATION = "needs_verification"
  - UNKNOWN = "unknown"
```

## Output Format

**JSON Array** with ComponentResult structure:
```json
[
  {
    "component": {
      "name": "junit",
      "version": "4.13.2",
      "component_type": "java-17",
      "source_sbom": "runtime_analysis",
      "properties": {
        "environment": "native_java_17_amazon-linux-2023",
        "native_build_detected": "No",
        "groupId": "junit",
        "artifactId": "junit",
        "runtime_analysis": "true",
        "timestamp": "2024-01-01T12:05:00Z"
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
      "notes": "Pure Java library - fully compatible with ARM64",
      "confidence_level": 0.9
    },
    "matched_name": null
  }
]
```

## Key Changes from Previous Version

### Schema Compliance
- **ComponentResult Structure**: Now returns proper `ComponentResult` objects instead of flat dictionaries
- **CompatibilityStatus Enum**: Uses enum values instead of string literals
- **SoftwareComponent Model**: Structured component information with proper typing
- **Properties Dictionary**: Runtime-specific metadata stored in component properties

### Preserved Functionality
- **Version Grouping**: Multi-version intelligence with inheritance logic
- **Deep Scanning**: JAR analysis for native code detection
- **Runtime Testing**: Actual dependency testing on ARM64
- **Knowledge Base**: Known problematic libraries database
- **Error Classification**: Comprehensive error handling and reporting
- **Maven Plugin Analysis**: ARM-specific plugin configuration detection
- **Dependency Management**: Analysis of dependencyManagement section

### Component Types
- **java-17**: For POM-based dependency analysis
- **jar**: For JAR directory analysis

## Usage

### Command Line Interface
```bash
# Basic POM analysis
python3 java_package_installer.py pom.xml

# JAR directory analysis
python3 java_package_installer.py /path/to/jars/

# Deep scanning with runtime testing
python3 java_package_installer.py pom.xml --deep-scan --runtime-test

# Additional JAR directory analysis
python3 java_package_installer.py pom.xml --jar-dir /path/to/additional/jars/

# Save output to file
python3 java_package_installer.py pom.xml -o results.json

# Verbose output with summary
python3 java_package_installer.py pom.xml -v

# Enable debug logging
DEBUG=1 python3 java_package_installer.py pom.xml
```

#### CLI Options
- `input_path`: Path to pom.xml, SBOM JSON file, or JAR directory
- `--jar-dir`: Additional JAR directory to analyze
- `-v, --verbose`: Verbose output with analysis summary
- `--deep-scan`: Perform deep scanning of JAR files
- `--runtime-test`: Perform runtime testing
- `-o, --output`: Output JSON file path

### Integration with Main Script
The output is now fully compatible with the main graviton validator:

```python
from graviton_validator.analysis.java_package_installer import analyze_pom_file
from graviton_validator.models import ComponentResult

# Returns List[ComponentResult]
results = analyze_pom_file('pom.xml', deep_scan=True, runtime_test=True)

# Each result is a ComponentResult object
for result in results:
    print(f"Component: {result.component.name}")
    print(f"Status: {result.compatibility.status.value}")
    print(f"Notes: {result.compatibility.notes}")
```

## New Features Added

### Maven Plugin ARM Configuration Analysis
The script now analyzes Maven plugins for ARM-specific configurations:

- **Spring Boot Maven Plugin**: Detects `imagePlatform` configurations for ARM64
- **Docker Maven Plugin**: Identifies platform-specific build configurations
- **Jib Maven Plugin**: Checks for ARM64 platform settings

Example detection:
```xml
<plugin>
    <artifactId>spring-boot-maven-plugin</artifactId>
    <configuration>
        <imagePlatform>linux/arm64</imagePlatform>
    </configuration>
</plugin>
```

### Dependency Management Section Analysis
Analyzes the `dependencyManagement` section to identify:

- Managed dependency versions that may affect ARM64 compatibility
- ARM-specific classifiers in managed dependencies
- Version constraints that could impact ARM64 migration

Example analysis:
```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>io.netty</groupId>
            <artifactId>netty-transport-native-epoll</artifactId>
            <version>4.1.50.Final</version>
            <classifier>linux-aarch64</classifier>
        </dependency>
    </dependencies>
</dependencyManagement>
```

### Maven Central Integration
The script now integrates with Maven Central API to enhance ARM64 compatibility analysis:

- **ARM Classifier Detection**: Queries Maven Central REST API (`https://search.maven.org/solrsearch/select`) for ARM-specific classifiers
- **Real-time Recommendations**: Provides suggestions when ARM classifiers are available but not used
- **Network Resilience**: Gracefully handles API failures without stopping analysis
- **Classifier Storage**: Stores available ARM classifiers in component properties for reporting

Example ARM classifiers detected:
- `linux-aarch64`, `linux-arm64` for native libraries
- `natives-linux-arm64`, `natives-linux-arm32` for LWJGL
- Platform-specific variants for Netty, RocksDB, etc.

### Enhanced JAR Analysis
The script provides comprehensive JAR file analysis for native code detection:

- **Platform-Specific Directories**: Detects directories like `linux-arm64`, `META-INF/native`, `natives-linux-arm64`, `lib/aarch64`
- **Native Library Loaders**: Identifies native library loading mechanisms (`native-lib-loader`, `nativelibraryloader`, `jniloader`)
- **JNI Method Detection**: Scans class files for JNI method signatures (simplified bytecode analysis)
- **Extended File Types**: Detects `.so`, `.dll`, `.dylib`, `.jnilib` native libraries
- **Architecture Classification**: Determines ARM64 vs x86_64 support from file paths and naming

Example platform directory patterns:
```
META-INF/native/linux-arm64/libnative.so
natives-linux-arm64/lwjgl.so
lib/aarch64/librocksdb.so
darwin-arm64/libnetty.dylib
```

### Dependency Installation Testing
The script pre-validates dependencies before compatibility analysis:

- **Maven Resolution Testing**: Creates minimal test projects to validate dependency resolution
- **Performance Optimization**: Tests first 5 dependencies to avoid long delays
- **Error Logging**: Generates detailed error logs for failed installations
- **Early Detection**: Identifies resolution issues before deep analysis
- **Timeout Protection**: 60-second timeout per dependency test

Installation test workflow:
1. Create temporary Maven project with single dependency
2. Execute `mvn dependency:resolve -q`
3. Log success/failure with detailed output
4. Store error information for reporting

### Cross-Platform Architecture Detection
The script provides robust architecture detection across platforms:

- **Linux/macOS Detection**: Uses `uname -m` command to detect `aarch64`/`arm64`
- **Windows Detection**: Falls back to `wmic os get OSArchitecture` for ARM detection
- **Warning System**: Issues warnings when not running on ARM architecture
- **Graceful Fallback**: Assumes x86 when detection fails
- **Test Accuracy Notices**: Informs users that results may be less accurate on non-ARM systems

Architecture detection flow:
1. Try `uname -m` (Linux/macOS)
2. If fails, try `wmic os get OSArchitecture` (Windows)
3. If both fail, assume x86 and warn user
4. Log detected architecture and issue warnings as needed

### Configuration Summary Component
When ARM plugin configurations or dependency management sections are found, the script adds a summary component with:

- Count of ARM plugin configurations detected
- Number of dependency management entries
- Overall assessment of POM ARM readiness

## Properties Dictionary

The `component.properties` dictionary contains runtime-specific metadata:

| Property | Description | Example |
|----------|-------------|---------|
| `environment` | Runtime environment identifier | `"native_java_17_amazon-linux-2023"` |
| `native_build_detected` | Native code detection result | `"Yes"`, `"No"` |
| `groupId` | Maven group ID | `"org.springframework"` |
| `artifactId` | Maven artifact ID | `"spring-core"` |
| `runtime_analysis` | Runtime analysis flag | `"true"` |
| `timestamp` | Analysis timestamp | `"2024-01-01T12:05:00Z"` |
| `test_output` | Maven command output | `"Downloaded junit-4.13.2.jar"` |
| `test_execution_output` | Runtime test output | `"Test execution successful"` |
| `error_details` | Error information | `"Could not resolve dependency"` |
| `error_type` | Error classification | `"network"`, `"dependency"`, etc. |
| `fallback_used` | Version fallback indicator | `"true"`, `"false"` |
| `arm_plugin_configs` | Number of ARM plugin configurations | `"2"` |
| `dependency_management_entries` | Number of managed dependencies | `"15"` |
| `available_arm_classifiers` | ARM classifiers from Maven Central | `"linux-aarch64,linux-arm64"` |
| `platform_dirs` | Platform-specific directories detected | `"linux-arm64,META-INF/native"` |
| `native_lib_loaders` | Native library loader detection | `"true"`, `"false"` |
| `has_jni` | JNI method detection result | `"true"`, `"false"` |

## Status Logic

### Compatible
- Pure Java libraries with no native dependencies
- Libraries with ARM64-specific classifiers
- Libraries that pass runtime testing on ARM64
- Known problematic libraries with fixed versions

### Needs Upgrade
- Older versions of known problematic libraries
- Failed versions when newer compatible version exists (inheritance logic)

### Needs Verification
- Libraries with native code requiring manual verification
- Libraries with x86-only native libraries
- Runtime test failures that aren't clearly incompatible

### Incompatible
- Libraries that fail dependency resolution
- Libraries with critical runtime failures
- Libraries with x86-only native code and no fallback

### Unknown
- Network issues preventing analysis
- Unclassified errors during analysis

## Version Inheritance Logic

The script implements intelligent version grouping:

1. **Group by Dependency**: Groups multiple versions of same `groupId:artifactId`
2. **Semantic Sorting**: Sorts versions from lowest to highest
3. **Sequential Testing**: Tests versions in order until compatible version found
4. **Inheritance**: When compatible version found:
   - Previous failed versions → `needs_upgrade`
   - Higher versions → `compatible` (inherited)
5. **Optimization**: Stops testing once compatible version found

## Error Handling

Errors are classified and stored in component properties:

- **network**: Connection/timeout issues, Maven Central API failures
- **dependency**: Dependency resolution failures, installation validation errors
- **native_build**: Native code compilation issues, JAR analysis failures
- **permissions**: File system permission errors
- **unknown**: Unclassified errors, architecture detection failures

### Enhanced Error Detection
- **Maven Central API Errors**: Network timeouts, invalid responses, rate limiting
- **Installation Validation Errors**: Dependency resolution failures, Maven command errors
- **JAR Analysis Errors**: Corrupted JAR files, ZIP format issues, permission errors
- **Architecture Detection Errors**: Command execution failures, platform detection issues

## Prerequisites

- **Java**: Version 8 or higher (Java 11+ recommended)
- **Maven**: Version 3.6 or higher
- **Python**: Version 3.6 or higher
- **Network Access**: Internet connectivity to Maven Central

## Limitations

- **Maven Central Only**: Limited to public Maven Central repository for classifier detection
- **ARM64 Accuracy**: Best results when run on ARM64 systems (warnings issued on x86)
- **Network Dependent**: Requires stable internet connectivity for Maven Central API and dependency resolution
- **Timeout Limits**: 60-second Maven resolution timeout per dependency, 10-second Maven Central API timeout
- **Installation Testing Scope**: Only tests first 5 dependencies for performance reasons
- **JNI Detection Accuracy**: Simplified bytecode analysis may miss complex JNI usage patterns
- **Platform Directory Detection**: Based on common naming patterns, may miss custom layouts

## Integration Benefits

- **Schema Compatibility**: Fully compatible with main graviton validator
- **Type Safety**: Proper typing with dataclasses and enums
- **Extensibility**: Easy to extend with additional analysis features
- **Consistency**: Consistent output format across all runtime analyzers
- **Maintainability**: Cleaner code structure with proper separation of concerns

This rewritten version maintains all the powerful analysis capabilities while providing a clean, type-safe interface that integrates seamlessly with the main graviton validator pipeline.