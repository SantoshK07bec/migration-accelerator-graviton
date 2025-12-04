# CLI Reference Guide

Complete command-line reference for the Graviton Compatibility Validator.

## Table of Contents
- [Basic Usage](#basic-usage)
- [Input Options](#input-options)
- [Execution Modes](#execution-modes)
- [Analysis Features](#analysis-features)
- [Output Options](#output-options)
- [Configuration](#configuration)
- [Logging & Debugging](#logging--debugging)
- [Expert Options](#expert-options)
- [Exit Codes](#exit-codes)
- [Examples by Use Case](#examples-by-use-case)

## Basic Usage

```bash
python graviton_validator.py [OPTIONS] [SBOM_FILES...]
```

**Minimum Required**: One of the following
- SBOM file(s) as positional arguments
- `--directory` for batch processing
- `--merge` for combining reports
- `--sbom-only` for manifest generation
- `--runtime-only` for runtime analysis

## Input Options

### Positional Arguments

#### `sbom_files`
**Type**: File path(s)  
**Required**: Unless using alternative input mode  
**Description**: One or more SBOM files to analyze

```bash
# Single file
python graviton_validator.py app.sbom.json

# Multiple files
python graviton_validator.py app1.sbom.json app2.sbom.json app3.sbom.json
```

**Supported Formats**:
- CycloneDX (JSON)
- SPDX (JSON)

### Directory Input

#### `-d, --directory DIR`
**Type**: Directory path  
**Default**: None  
**Description**: Analyze all `*.json` files in directory

```bash
# Analyze all SBOMs in directory
python graviton_validator.py -d ./sbom-files/

# With runtime testing
python graviton_validator.py -d ./sbom-files/ --runtime --test --containers
```

**Behavior**:
- Recursively finds all `.json` files
- Processes each file independently
- Generates separate json reports for each
- Can combine with `--merge` for unified final report

## Execution Modes

### Standard Analysis (Default)

```bash
python graviton_validator.py sbom.json
```

**What it does**:
- Parses SBOM file
- Matches components against knowledge base
- Checks deny lists
- Generates compatibility report

**Does NOT**:
- Install any packages
- Check package registries
- Require network access

### Runtime Analysis Mode

#### `--runtime`
**Type**: Flag  
**Default**: False  
**Description**: Enable runtime analysis (checks package availability)

```bash
python graviton_validator.py sbom.json --runtime
```

**What it does**:
- Extracts dependency manifests from SBOM
- Checks package registry availability (network access required)
- Detects native code dependencies
- **Does NOT install packages** (read-only checks)

**Supported Runtimes**:
- Python (pip)
- Node.js (npm)
- Java (Maven)
- .NET (NuGet)
- Ruby (bundler)

### Runtime Testing Mode

#### `--test`
**Type**: Flag  
**Default**: False  
**Requires**: `--runtime`  
**Description**: Actually install packages to verify compatibility

```bash
python graviton_validator.py sbom.json --runtime --test
```

**⚠️ WARNING**: Installs packages on your local machine
- Runs `pip install`, `npm install`, `mvn`, `dotnet restore`, `bundle install`
- May execute package setup scripts
- Can modify Python/Node.js/Ruby environments
- **Use `--containers` for safety**

### Containerized Testing Mode

#### `--containers`
**Type**: Flag  
**Default**: False  
**Requires**: `--runtime --test`  
**Description**: Run tests in isolated Docker containers

```bash
python graviton_validator.py sbom.json --runtime --test --containers
```

**✅ RECOMMENDED** for production use

**Requirements**:
- Docker or Podman installed
- Docker daemon running
- Sufficient disk space

**Benefits**:
- Isolated from host system
- Safe for production
- Automatic cleanup
- Reproducible results

### Multi-Stage Build Modes

#### `--sbom-only`
**Type**: Flag  
**Default**: False  
**Description**: Generate dependency manifests only (Stage 1)

```bash
python graviton_validator.py --sbom-only -d ./sboms/
```

**Output**: Manifests saved to `output_files/`
- `<name>_requirements.txt` (Python)
- `<name>_package.json` (Node.js)
- `<name>_pom.xml` (Java)
- `<name>_test.csproj` (.NET)
- `<name>_Gemfile` (Ruby)

**Use Case**: Parallel runtime testing on different machines

#### `--runtime-only [RUNTIME]`
**Type**: Choice  
**Choices**: `auto`, `python`, `nodejs`, `java`, `dotnet`, `ruby`  
**Default**: `auto` (if flag used without value)  
**Description**: Analyze runtime dependencies only (Stage 2)

```bash
# Auto-detect runtimes
python graviton_validator.py --runtime-only auto

# Specific runtime
python graviton_validator.py --runtime-only python --test --containers

# With custom input file
python graviton_validator.py --runtime-only python --input-file requirements.txt --test
```

**Behavior**:
- Reads manifests from `--input-dir` (default: `output_files/`)
- No SBOM parsing
- Can specify custom manifest with `--input-file`

#### `--input-file FILE`
**Type**: File path  
**Default**: None  
**Requires**: `--runtime-only`  
**Description**: Specific manifest file to analyze

```bash
# Analyze specific manifest
python graviton_validator.py --runtime-only python --input-file requirements.txt --test --containers

# Java POM file
python graviton_validator.py --runtime-only java --input-file pom.xml --test --containers
```

#### `--input-dir DIR`
**Type**: Directory path  
**Default**: `output_files`  
**Requires**: `--runtime-only`  
**Description**: Directory containing manifests from `--sbom-only`

```bash
python graviton_validator.py --runtime-only auto --input-dir ./manifests/ --test --containers
```

### Report Merging Modes

#### `--merge [FILES...]`
**Type**: File path(s)  
**Default**: None  
**Description**: Merge multiple JSON analysis reports

```bash
# Merge specific reports
python graviton_validator.py --merge report1.json report2.json report3.json -f excel

# Merge all reports in directory
python graviton_validator.py --merge ./results/*.json -f excel -o combined.xlsx
```

**Behavior**:
- Combines component lists
- Deduplicates components
- Aggregates statistics
- Generates unified report

#### `--merge-runtime [DIR]`
**Type**: Directory path  
**Default**: `output_files` (if flag used without value)  
**Description**: Merge SBOM and runtime analysis results (Stage 3)

```bash
# Use default directory
python graviton_validator.py --merge-runtime

# Specify directory
python graviton_validator.py --merge-runtime ./analysis-results/ -f excel
```

**Behavior**:
- Finds SBOM analysis files (`*_sbom_analysis.json`)
- Finds runtime analysis files (`*_<runtime>_analysis.json`)
- Matches by filename pattern
- Merges compatibility data
- Generates unified report

## Analysis Features

### JAR Analysis

#### `--jars [FILES...]`
**Type**: File path(s)  
**Default**: None  
**Description**: Additional JAR/WAR/EAR files to analyze

```bash
# Single JAR
python graviton_validator.py sbom.json --jars app.jar

# Multiple JARs
python graviton_validator.py sbom.json --jars lib1.jar lib2.jar lib3.jar

# Wildcard
python graviton_validator.py sbom.json --jars ./libs/*.jar
```

**What it analyzes**:
- Dependencies from MANIFEST.MF
- Native libraries (.so, .dll, .dylib)
- Bytecode compatibility
- Platform-specific code

#### `--jar-dir DIR`
**Type**: Directory path  
**Default**: None  
**Description**: Directory containing JAR/WAR/EAR files

```bash
python graviton_validator.py sbom.json --jar-dir ./application-libs/
```

### Filtering

#### `--no-system`
**Type**: Flag  
**Default**: False  
**Description**: Exclude system packages from analysis

```bash
python graviton_validator.py sbom.json --no-system
```

**Use Case**: Focus on application dependencies only
**Applies to**: SBOMs generated by app_identifier tool

## Output Options

### Output Format

#### `-f, --format FORMAT`
**Type**: Choice  
**Choices**: `text`, `json`, `excel`, `markdown`  
**Default**: `text`  
**Description**: Report output format

```bash
# Text (console output)
python graviton_validator.py sbom.json -f text

# JSON (machine-readable)
python graviton_validator.py sbom.json -f json -o report.json

# Excel (spreadsheet)
python graviton_validator.py sbom.json -f excel -o report.xlsx

# Markdown (documentation)
python graviton_validator.py sbom.json -f markdown -o report.md
```

**Format Details**:

| Format | Extension | Use Case | Features |
|--------|-----------|----------|----------|
| `text` | `.txt` | Console, CI/CD | Summary, component list, recommendations |
| `json` | `.json` | Automation, merging | Complete data, machine-readable |
| `excel` | `.xlsx` | Stakeholder reports | Multi-sheet, charts, filtering |
| `markdown` | `.md` | Documentation | GitHub/GitLab compatible, formatted |

### Output Filename

#### `-o, --output FILE`
**Type**: File path  
**Default**: Auto-generated  
**Description**: Custom output filename

```bash
# Custom filename
python graviton_validator.py sbom.json -f excel -o my-report.xlsx

# Auto-generated (based on input)
python graviton_validator.py app.sbom.json -f excel
# Creates: app.xlsx
```

**Auto-generation Rules**:
- Single input: `<input_stem>.<ext>`
- Multiple inputs: `graviton_compatibility_report.<ext>`

### Output Directory

#### `--output-dir DIR`
**Type**: Directory path  
**Default**: `output_files`  
**Description**: Directory for all output files

```bash
python graviton_validator.py sbom.json --output-dir ./results/
```

**Created automatically** if doesn't exist

**Contains**:
- Analysis reports
- Extracted manifests (if `--sbom-only`)
- Runtime results (if `--runtime`)
- Logs (if `--log-file` without path)

### Detailed Output

#### `--detailed`
**Type**: Flag  
**Default**: False  
**Description**: Include detailed component information in text reports

```bash
python graviton_validator.py sbom.json --detailed
```

**Adds**:
- Full component metadata
- Version information
- All aliases
- Migration notes
- Recommendations

## Configuration

### Knowledge Base

#### `-k, --knowledge-base FILE`
**Type**: File path  
**Default**: Built-in knowledge bases  
**Repeatable**: Yes  
**Description**: Custom knowledge base file

```bash
# Single custom KB
python graviton_validator.py sbom.json -k custom_kb.json

# Multiple KBs (merged)
python graviton_validator.py sbom.json -k kb1.json -k kb2.json -k kb3.json
```

**Behavior**:
- Supplements default knowledge base
- Does not replace default
- Later files override earlier ones
- Supports version ranges and aliases

### Deny List

#### `--deny-list FILE`
**Type**: File path  
**Default**: Built-in deny lists  
**Description**: Custom deny list file

```bash
python graviton_validator.py sbom.json --deny-list custom_deny.json
```

**Behavior**:
- Supplements default deny lists
- Marks packages as incompatible
- Overrides knowledge base entries

### Configuration File

#### `-c, --config FILE`
**Type**: File path  
**Default**: `~/.graviton_validator/config.yaml`  
**Description**: Configuration file for advanced settings

```bash
python graviton_validator.py sbom.json --config custom_config.yaml
```

**Override Priority**:
1. Command-line arguments (highest)
2. Custom config file
3. Default config file
4. Built-in defaults (lowest)

## Logging & Debugging

### Verbosity

#### `-v, --verbose`
**Type**: Flag  
**Default**: False  
**Description**: Show detailed progress information

```bash
python graviton_validator.py sbom.json -v
```

**Shows**:
- Component processing details
- Runtime analysis progress
- Package installation status
- Detailed error messages

#### `--debug`
**Type**: Flag  
**Default**: False  
**Description**: Enable DEBUG level logging

```bash
python graviton_validator.py sbom.json --debug
```

**Shows**:
- Internal logic details
- Function calls
- Data transformations
- Performance metrics

#### `--quiet`
**Type**: Flag  
**Default**: False  
**Description**: Show only errors

```bash
python graviton_validator.py sbom.json --quiet
```

**Use Case**: CI/CD pipelines, automated scripts

### Log Level

#### `--log-level LEVEL`
**Type**: Choice  
**Choices**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`  
**Default**: `INFO`  
**Description**: Set logging level explicitly

```bash
python graviton_validator.py sbom.json --log-level DEBUG
```

**Levels**:
- `DEBUG`: Everything (most verbose)
- `INFO`: Normal operations
- `WARNING`: Potential issues
- `ERROR`: Errors only
- `CRITICAL`: Critical failures only

### Log File

#### `--log-file FILE`
**Type**: File path  
**Default**: None (console only)  
**Description**: Save logs to file

```bash
# Specific file
python graviton_validator.py sbom.json --log-file analysis.log

# With debug level
python graviton_validator.py sbom.json --debug --log-file debug.log
```

**Behavior**:
- Logs still appear on console
- File contains complete log
- Useful for troubleshooting

## Expert Options

### Runtime Configuration

#### `--runtime-config FILE`
**Type**: File path  
**Default**: None  
**Description**: Runtime configuration file (YAML/JSON)

```bash
python graviton_validator.py sbom.json --runtime --runtime-config custom_runtime.yaml
```

**Use Case**: Override runtime versions, timeouts, container settings

### Cleanup Control

#### `--no-cleanup`
**Type**: Flag  
**Default**: False  
**Description**: Keep temporary files for debugging

```bash
python graviton_validator.py sbom.json --runtime --test --no-cleanup
```

**Keeps**:
- Temporary directories
- Downloaded packages
- Container artifacts
- Intermediate files

**Use Case**: Debugging failed analyses

## Exit Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `0` | Success | Analysis completed successfully |
| `1` | Error | General error (invalid input, analysis failure) |
| `130` | Interrupted | User cancelled with Ctrl+C |

**Usage in Scripts**:
```bash
python graviton_validator.py sbom.json
if [ $? -eq 0 ]; then
    echo "Analysis successful"
else
    echo "Analysis failed"
    exit 1
fi
```

## Examples by Use Case

### Quick Analysis
```bash
# Fastest - knowledge base only
python graviton_validator.py app.sbom.json
```

### Comprehensive Analysis
```bash
# Recommended - full testing in containers
python graviton_validator.py app.sbom.json --runtime --test --containers -f excel
```

### CI/CD Pipeline
```bash
# Quiet mode with JSON output
python graviton_validator.py app.sbom.json --runtime --test --containers -f json --quiet
```

### Enterprise Portfolio
```bash
# Batch analysis with Excel reports
python graviton_validator.py -d ./enterprise-sboms/ --runtime --test --containers -f excel --output-dir ./reports/
```

### Multi-Stage Build
```bash
# Stage 1: Generate manifests
python graviton_validator.py --sbom-only -d ./sboms/

# Stage 2: Test runtimes (can run in parallel)
python graviton_validator.py --runtime-only python --test --containers
python graviton_validator.py --runtime-only nodejs --test --containers
python graviton_validator.py --runtime-only java --test --containers

# Stage 3: Merge results
python graviton_validator.py --merge-runtime -f excel -o final-report.xlsx
```

### Debugging Failed Analysis
```bash
# Maximum verbosity with log file
python graviton_validator.py app.sbom.json --debug -v --log-file debug.log --no-cleanup
```

### Custom Knowledge Base
```bash
# Organization-specific compatibility data
python graviton_validator.py app.sbom.json -k company_kb.json -k team_kb.json --runtime --test
```

## Common Option Combinations

### Safe Production Testing
```bash
--runtime --test --containers
```

### Detailed Reporting
```bash
-f excel --detailed -o detailed-report.xlsx
```

### Silent Automation
```bash
-f json --quiet --log-file analysis.log
```

### Debug Mode
```bash
--debug -v --log-file debug.log --no-cleanup
```

### Batch Processing
```bash
-d ./sboms/ --runtime --test --containers --output-dir ./results/
```

## Tips & Best Practices

1. **Always use `--containers` with `--test`** for safety
2. **Use `-f excel` for stakeholder reports** - easier to read
3. **Use `-f json` for automation** - machine-readable
4. **Enable `--verbose` when troubleshooting** - see what's happening
5. **Use `--sbom-only` for large portfolios** - parallel processing
6. **Keep logs with `--log-file`** - helpful for debugging
7. **Use `--detailed` for deep dives** - complete information
8. **Combine `--merge` with `-f excel`** - unified portfolio view

## Runtime Testing Guide

### Overview

Runtime testing verifies actual package installation and ARM64 compatibility for 5 languages:
- Python (pip/PyPI)
- Node.js (npm)
- Java (Maven)
- .NET (NuGet)
- Ruby (bundler/RubyGems)

### When to Use Each Mode

| Mode | Command | Speed | Accuracy | Safety | Use Case |
|------|---------|-------|----------|--------|----------|
| Standard | `sbom.json` | Fast | Medium | Safe | Quick check, CI/CD |
| Runtime | `--runtime` | Medium | High | Safe | Verify availability |
| Testing | `--runtime --test` | Slow | Highest | ⚠️ Unsafe | Full verification |
| Containers | `--runtime --test --containers` | Slow | Highest | ✅ Safe | Production testing |

### Multi-Stage Workflow

For large portfolios (100+ applications), use multi-stage builds:

**Stage 1: Generate Manifests**
```bash
python graviton_validator.py --sbom-only -d ./sboms/
```
Output: Manifests saved to `output_files/`
- `<name>_requirements.txt` (Python)
- `<name>_package.json` (Node.js)
- `<name>_pom.xml` (Java)
- `<name>_test.csproj` (.NET)
- `<name>_Gemfile` (Ruby)

**Stage 2: Test Runtimes (Parallel)**
```bash
# Run on different machines/containers
python graviton_validator.py --runtime-only python --test --containers
python graviton_validator.py --runtime-only nodejs --test --containers
python graviton_validator.py --runtime-only java --test --containers
python graviton_validator.py --runtime-only dotnet --test --containers
python graviton_validator.py --runtime-only ruby --test --containers
```

**Stage 3: Merge Results**
```bash
python graviton_validator.py --merge-runtime ./output_files/ -f excel -o final-report.xlsx
```

### Configuration

Control runtime analysis via config file (`~/.graviton_validator/config.yaml`):

```yaml
runtime_analysis:
  # Enable/disable metadata lookup per runtime
  metadata_lookup:
    python: true
    nodejs: true
    java: true
    dotnet: true
    ruby: true
  
  # Disable all network calls
  offline_mode: false
  
  # API timeouts and retries
  api_timeout: 10
  max_retries: 3
```

### Runtime-Specific Configuration

File: `runtime_config.yaml` (use with `--runtime-config`)

```yaml
python:
  pip_index_url: "https://pypi.org/simple"
  timeout: 30

nodejs:
  npm_registry: "https://registry.npmjs.org"
  timeout: 30

java:
  maven_central_url: "https://repo1.maven.org/maven2"
  timeout: 30

dotnet:
  nuget_source: "https://api.nuget.org/v3/index.json"
  timeout: 30

ruby:
  rubygems_url: "https://rubygems.org"
  timeout: 30
```

### What Each Runtime Detects

**Python**:
- ARM64 wheels (`linux_aarch64`)
- Universal wheels
- Native extensions (C/C++)
- Source distributions

**Node.js**:
- Native modules (node-gyp)
- Prebuilt binaries
- CPU architecture support
- Build requirements

**Java**:
- ARM64 classifiers (`linux-aarch64`)
- Native libraries (JNI)
- Platform-specific JARs
- MANIFEST.MF dependencies

**.NET**:
- Runtime Identifiers (`linux-arm64`)
- Platform-specific packages
- Native dependencies (P/Invoke)
- Framework compatibility

**Ruby**:
- Native extensions (C)
- Platform-specific gems
- Compilation requirements
- Precompiled binaries

### Troubleshooting Runtime Testing

**Network Issues**:
```bash
# Check if offline mode is enabled
grep offline_mode ~/.graviton_validator/config.yaml

# Test with verbose logging
python graviton_validator.py sbom.json --runtime -v
```

**Package Installation Failures**:
```bash
# Use containers for isolation
python graviton_validator.py sbom.json --runtime --test --containers

# Keep temp files for debugging
python graviton_validator.py sbom.json --runtime --test --no-cleanup

# Check logs
python graviton_validator.py sbom.json --runtime --test --log-file debug.log
```

**API Rate Limiting**:
```yaml
# Adjust in config.yaml
runtime_analysis:
  api_timeout: 30
  max_retries: 5
```

### Technical Implementation Details

For developers interested in how runtime analyzers work internally:
- [Python Analyzer](PYTHON_PACKAGE_INSTALLER_TECH_USAGE.md)
- [Node.js Analyzer](NODEJS_PACKAGE_INSTALLER_TECH_USAGE.md)
- [Java Analyzer](JAVA_PACKAGE_INSTALLER_TECH_USAGE.md)
- [.NET Analyzer](DOTNET_PACKAGE_INSTALLER_TECH_USAGE.md)
- [Ruby Analyzer](RUBY_PACKAGE_INSTALLER_TECH_USAGE.md)

## Getting Help

```bash
# Show help message
python graviton_validator.py --help

# Show version
python graviton_validator.py --version
```

## See Also

- [Quick Start Guide](QUICK_START.md) - Get started in 5 minutes
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions
- [Architecture and Workflows](ARCHITECTURE_AND_WORKFLOWS.md) - Technical details
