# Graviton Validator Core Package

Core Python package for the Graviton Compatibility Validator tool. This package provides SBOM parsing, compatibility analysis, runtime testing, and multi-format reporting capabilities.

## Package Structure

### Core Modules

- **`models.py`** - Data models (SoftwareComponent, CompatibilityResult, AnalysisResult)
- **`config.py`** - Configuration management and YAML settings
- **`exceptions.py`** - Custom exception classes
- **`logging_config.py`** - Logging configuration
- **`pattern_validator.py`** - Regex pattern validation utilities
- **`jar_analysis_engine.py`** - JAR/WAR/EAR file analysis
- **`prerequisites.py`** - Runtime prerequisite checking (Docker, package managers)
- **`runtime_configs.py`** - Runtime version configurations
- **`version.py`** - Package version information

### Subpackages

#### `analysis/`
Compatibility analysis and runtime testing:

**Core Analysis:**
- `compatibility_analyzer.py` - Main SBOM compatibility analysis engine
- `filters.py` - Component filtering and system package detection
- `sbom_filters.py` - SBOM-specific filtering logic
- `runtime_detection.py` - Multi-runtime detection from SBOM components

**Runtime Analyzers** (Phase 1: Runtime KB → Phase 2: API → Phase 3: Cache):
- `python_runtime_analyzer.py` - Python/PyPI analysis
- `nodejs_runtime_analyzer.py` - Node.js/NPM analysis
- `java_runtime_analyzer.py` - Java/Maven analysis
- `dotnet_runtime_analyzer.py` - .NET/NuGet analysis
- `ruby_runtime_analyzer.py` - Ruby/RubyGems analysis
- `runtime_analyzer.py` - Base runtime analyzer interface
- `cache_manager.py` - API response caching (.cache/ directory)

**Package Installers** (for `--test` mode):
- `python_package_installer.py` - Python package installation testing
- `nodejs_package_installer.py` - Node.js package installation testing
- `java_package_installer.py` - Java package installation testing
- `dotnet_package_installer.py` - .NET package installation testing
- `ruby_package_installer.py` - Ruby package installation testing

**Utilities:**
- `manifest_generators.py` - Runtime manifest generation and management
- `execution_environment.py` - Container and native execution environments
- `sbom_jar_enhancer.py` - JAR file SBOM enhancement
- `sbom_runtime_merger.py` - Merge SBOM and runtime analysis results
- `runtime_config.py` - Runtime configuration management
- `config.py` - Analysis configuration
- `base.py` - Abstract base classes

#### `knowledge_base/`
Knowledge base management and matching:

**Core:**
- `data_structures.py` - JSON knowledge base implementation
- `loader.py` - Knowledge base loading and validation
- `intelligent_matcher.py` - Fuzzy matching and alias resolution
- `version_comparator.py` - Semantic version comparison
- `base.py` - Abstract base classes

**Runtime Knowledge Bases** (fast-path for common packages):
- `runtime_loader.py` - Runtime KB loader
- `python_runtime_dependencies.json` - 10 common PyPI packages
- `nodejs_runtime_dependencies.json` - 13 common NPM packages
- `java_runtime_dependencies.json` - 13 common Maven packages
- `dotnet_runtime_dependencies.json` - 15 common NuGet packages
- `ruby_runtime_dependencies.json` - 4 common RubyGems

**Note:** Runtime KBs are optional fast-path optimizations. Package registry APIs (PyPI, NPM, Maven, NuGet, RubyGems) are the authoritative source for compatibility data.

#### `parsers/`
SBOM format parsers:
- `cyclonedx.py` - CycloneDX format parser
- `spdx.py` - SPDX format parser
- `syft.py` - Syft/app_identifier format parser
- `factory.py` - Parser factory and format detection
- `base.py` - Abstract parser base class

#### `reporting/`
Multi-format report generation:
- `json_reporter.py` - JSON format reports
- `text_reporter.py` - Human-readable text reports with color coding
- `markdown_reporter.py` - Markdown documentation reports
- `excel_reporter.py` - Excel spreadsheet reports with charts
- `base.py` - Abstract reporter base class

#### `os_detection/`
Operating system detection:
- `detector.py` - OS detection from SBOM metadata
- `os_configs.py` - OS compatibility configurations

#### `deny_list/`
Package deny list management:
- `loader.py` - Deny list loading and processing
- `models.py` - Deny list data structures

#### `validation/`
Result validation:
- `runtime_result_validator.py` - Runtime analysis result validation

## Key Features

### Multi-Format SBOM Support
- **CycloneDX** - Industry standard SBOM format
- **SPDX** - Software Package Data Exchange format
- **Syft** - Syft/app_identifier custom format

### Hybrid Compatibility Analysis

**SBOM Analysis (Static):**
- Knowledge base matching with fuzzy name resolution
- Version range validation
- Deny list checking
- OS-aware compatibility assessment

**Runtime Analysis (Dynamic):**
```
Phase 1: Runtime KB Check (10-15 common packages)
         ↓ (if not found)
Phase 2: Package Registry API Query (PyPI/NPM/Maven/NuGet/RubyGems)
         ↓
Phase 3: Cache Results (.cache/ directory)
```

**Runtime Testing (Optional `--test`):**
- Actual package installation verification
- Native code compilation testing
- Containerized testing (Docker/Podman)
- ARM64 wheel/binary availability checking

### Comprehensive Reporting
- **JSON** - Structured data for automation
- **Text** - Color-coded console output
- **Markdown** - Documentation-friendly format
- **Excel** - Multi-sheet spreadsheets with charts and statistics

### Extensible Architecture
- Plugin-based parsers for new SBOM formats
- Configurable component filters
- Modular reporter system
- JSON-based knowledge bases

## Usage Examples

### Basic SBOM Analysis
```python
from graviton_validator.parsers.factory import SBOMParserFactory
from graviton_validator.analysis.compatibility_analyzer import GravitonCompatibilityAnalyzer
from graviton_validator.knowledge_base.loader import KnowledgeBaseLoader

# Parse SBOM
parser = SBOMParserFactory.get_parser('sbom.json')
components = parser.parse('sbom.json')

# Load knowledge base
kb_loader = KnowledgeBaseLoader()
kb = kb_loader.load_multiple(['knowledge_bases/custom_kb.json'])

# Analyze compatibility
analyzer = GravitonCompatibilityAnalyzer(knowledge_base=kb)
results = analyzer.analyze_components(components)
```

### Runtime Analysis
```python
from graviton_validator.analysis.python_runtime_analyzer import PythonRuntimeAnalyzer

# Create analyzer with config
config = {'metadata_lookup': {'python': True}, 'offline_mode': False}
analyzer = PythonRuntimeAnalyzer(config=config)

# Analyze component (checks runtime KB → PyPI API → cache)
result = analyzer.analyze_component(component)
print(f"{component.name}: {result.compatibility.status}")
```

### Generate Reports
```python
from graviton_validator.reporting.json_reporter import JSONReporter
from graviton_validator.reporting.excel_reporter import ExcelReporter

# JSON report
json_reporter = JSONReporter()
json_report = json_reporter.generate_report(results)

# Excel report with charts
excel_reporter = ExcelReporter()
excel_reporter.generate_report(results, 'report.xlsx')
```

## Configuration

### Environment Variables
- `GRAVITON_VALIDATOR_CONFIG` - Default configuration file path
- `GRAVITON_VALIDATOR_KB` - Default knowledge base directory
- `GRAVITON_VALIDATOR_LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)

### Configuration Files
YAML-based configuration (`config.yaml`):
- Knowledge base paths
- Output format preferences
- Matching algorithm settings (fuzzy matching thresholds)
- Filtering patterns (system packages, test dependencies)
- Runtime analysis settings (metadata lookup, offline mode)
- Logging configuration

## Development

### Adding New SBOM Parsers
1. Inherit from `parsers.base.SBOMParser`
2. Implement `parse()` and `supports_format()` methods
3. Register in `parsers.factory.SBOMParserFactory`
4. Add tests in `tests/test_parsers.py`

### Adding New Runtime Analyzers
1. Inherit from `analysis.runtime_analyzer.RuntimeCompatibilityAnalyzer`
2. Implement 3-phase analysis: Runtime KB → API → Cache
3. Add package installer for `--test` mode
4. Create runtime KB JSON file (optional, for common packages)
5. Add tests in `tests/test_*_runtime_analyzer.py`

### Creating New Report Formats
1. Inherit from `reporting.base.ReportGenerator`
2. Implement `generate_report()` method
3. Handle file I/O and formatting
4. Add tests in `tests/test_reporters.py`

## Testing

Run tests with pytest:
```bash
# All tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=graviton_validator --cov-report=html

# Specific test file
python -m pytest tests/test_python_runtime_analyzer.py -v
```

## Dependencies

### Core Dependencies
- **requests** - HTTP client for API calls
- **pyyaml** - YAML configuration parsing
- **packaging** - Version parsing and comparison

### Optional Dependencies
- **openpyxl** - Excel report generation
- **docker** - Container-based testing
- **Levenshtein** - Enhanced fuzzy matching performance

### Development Dependencies
- **pytest** - Testing framework
- **pytest-cov** - Coverage reporting
- **black** - Code formatting
- **flake8** - Linting

## Architecture Principles

### Modularity
- Clear separation: parsing → analysis → reporting
- Plugin-based extensibility
- Minimal coupling between components

### Performance
- Lazy loading of knowledge bases
- API response caching
- Efficient memory usage for large SBOMs
- Fast-path runtime KB for common packages

### Reliability
- Comprehensive error handling
- Input validation and sanitization
- Graceful degradation for missing dependencies
- Retry logic for API calls

## See Also

- [Main Documentation](../docs/README.md) - User guides and references
- [Knowledge Base Guide](../docs/KNOWLEDGE_BASE_GUIDE.md) - KB structure and maintenance
- [Architecture Documentation](../docs/ARCHITECTURE_AND_WORKFLOWS.md) - System architecture
- [CLI Reference](../docs/CLI_REFERENCE.md) - Command-line usage
