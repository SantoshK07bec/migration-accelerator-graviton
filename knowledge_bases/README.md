# Knowledge Bases

Compatibility databases for AWS Graviton processors used during SBOM analysis. These files are automatically loaded by the validator and can be updated using [helper scripts](../scripts/README.md).

## Directory Structure

```
knowledge_bases/
├── arm_ecosystem_packages.json      # ARM ecosystem software (auto-updated)
├── isv_graviton_packages.json       # ISV commercial software (auto-updated)
├── custom_kb.json                   # Application-level software (manual)
├── custom_system_kb.json            # Custom system packages (manual)
├── os_knowledge_bases/              # OS package databases (auto-updated)
│   ├── amazon-linux-2-graviton-packages.json
│   ├── amazon-linux-2023-graviton-packages.json
│   ├── ubuntu-18.04-graviton-packages.json
│   ├── ubuntu-20.04-graviton-packages.json
│   ├── ubuntu-22.04-graviton-packages.json
│   ├── ubuntu-24.04-graviton-packages.json
│   ├── debian-10-graviton-packages.json
│   ├── debian-11-graviton-packages.json
│   ├── debian-12-graviton-packages.json
│   ├── centos-8-graviton-packages.json
│   ├── alpine-3.17.10-graviton-packages.json
│   ├── alpine-3.18.12-graviton-packages.json
│   └── common_aliases.json          # Package name aliases (managed by scripts/manage_aliases.py)
└── schemas/
    └── common_aliases_schema.json   # Alias validation schema
```

## Knowledge Base Files

### Auto-Updated Files

#### `arm_ecosystem_packages.json`
ARM ecosystem software packages with verified Graviton compatibility.

**Content:** Native ARM64 packages, cross-platform libraries, performance-optimized versions

**Updated by:** `scripts/arm_ecosystem_scraper.py` (scrapes [Arm Developer Hub](https://www.arm.com/developer-hub/ecosystem-dashboard/))

**Update frequency:** Monthly or as needed

#### `isv_graviton_packages.json`
Independent Software Vendor (ISV) packages with official Graviton support.

**Content:** Commercial software, databases, development tools, monitoring solutions

**Updated by:** `scripts/isv_scraper.py` (scrapes [AWS Graviton Getting Started](https://github.com/aws/aws-graviton-getting-started/blob/main/isv.md))

**Update frequency:** Monthly or as needed

#### `os_knowledge_bases/*.json`
Operating system package databases with ARM64-compatible packages.

**Content:** All available packages for each OS version, guaranteed Graviton-compatible

**Updated by:** `scripts/generate_all_os_kb.sh` or `scripts/generate_docker_kb.sh`

**Update frequency:** Quarterly or when new OS versions are released

**Supported OS:**
- Amazon Linux 2, 2023
- Ubuntu 18.04, 20.04, 22.04, 24.04 LTS
- Debian 10, 11, 12
- CentOS 8
- Alpine 3.17, 3.18

#### `os_knowledge_bases/common_aliases.json`
Persistent package name alias mappings for improved matching.

**Content:** Global aliases, OS-specific aliases, truncated names, legacy mappings

**Updated by:** `scripts/manage_aliases.py`

**Usage:**
```bash
# Add alias
./scripts/manage_aliases.py add "node.js" "nodejs"

# Remove alias
./scripts/manage_aliases.py remove "node.js"

# List all aliases
./scripts/manage_aliases.py list
```

### Manual Files

#### `custom_kb.json`
Application-level software compatibility database (template for customization).

**Content:** Java, Tomcat, MySQL, PostgreSQL, Redis, Nginx, Apache, etc.

**Maintenance:** Manual updates based on testing and vendor documentation

**Use case:** Organization-specific software compatibility tracking

#### `custom_system_kb.json`
Custom system package compatibility database.

**Content:** System-level packages not covered by OS knowledge bases

**Maintenance:** Manual updates

**Use case:** Special system packages or custom builds

## Usage

### Automatic Loading (Default)

All `*.json` files in `knowledge_bases/` directory are loaded automatically:

```bash
# Uses all knowledge bases in knowledge_bases/ directory
python graviton_validator.py sbom.json
```

### Explicit Knowledge Base Selection

```bash
# Use specific knowledge base
python graviton_validator.py -k knowledge_bases/isv_graviton_packages.json sbom.json

# Use multiple knowledge bases
python graviton_validator.py \
  -k knowledge_bases/isv_graviton_packages.json \
  -k knowledge_bases/os_knowledge_bases/ubuntu-22.04-graviton-packages.json \
  sbom.json

# Use custom knowledge base
python graviton_validator.py -k my_custom_kb.json sbom.json
```

### OS-Specific Analysis

```bash
# Analyze with specific OS knowledge base
python graviton_validator.py \
  -k knowledge_bases/os_knowledge_bases/amazon-linux-2023-graviton-packages.json \
  sbom.json
```

## Updating Knowledge Bases

### Update All Auto-Generated Files

```bash
# Update OS package databases
cd scripts
./generate_all_os_kb.sh

# Update ISV database
python isv_scraper.py

# Update ARM ecosystem database
python arm_ecosystem_scraper.py
```

### Update Specific OS

```bash
cd scripts
./generate_docker_kb.sh ubuntu 22.04
./generate_docker_kb.sh amazonlinux 2023
```

### Manage Aliases

```bash
cd scripts
./manage_aliases.py add "python3" "python"
./manage_aliases.py add "nodejs" "node"
./manage_aliases.py list
```

See [scripts/README.md](../scripts/README.md) for detailed script documentation.

## Creating Custom Knowledge Bases

### Basic Structure

```json
{
  "$schema": "./schemas/knowledge_base_schema.json",
  "metadata": {
    "version": "1.0",
    "description": "Custom organization knowledge base",
    "maintainer": "Your Organization"
  },
  "software_compatibility": [
    {
      "name": "your-software",
      "aliases": ["your-app", "yourapp"],
      "compatibility": {
        "supported_versions": [
          {
            "version_range": ">=2.0.0",
            "status": "compatible",
            "notes": "Full Graviton support"
          }
        ],
        "minimum_supported_version": "2.0.0",
        "recommended_version": "2.5.0"
      }
    }
  ]
}
```

### Version Range Syntax

| Operator | Description | Example |
|----------|-------------|---------|
| `>=` | Greater than or equal | `>=1.0.0` |
| `<=` | Less than or equal | `<=2.0.0` |
| `>` | Greater than | `>1.0.0` |
| `<` | Less than | `<2.0.0` |
| `==` | Exactly equal | `==1.0.0` |
| `~` | Patch compatible | `~1.0.0` (>=1.0.0, <1.1.0) |
| `^` | Minor compatible | `^1.0.0` (>=1.0.0, <2.0.0) |
| `,` | Combine ranges | `>=1.0.0,<2.0.0` |

### Compatibility Status Values

| Status | Meaning | When to Use |
|--------|---------|-------------|
| `compatible` | Full Graviton support | Native ARM64 builds, no issues |
| `compatible_with_notes` | Works with limitations | Minor issues, workarounds available |
| `incompatible` | Does not work on Graviton | No ARM64 support, critical bugs |
| `unknown` | Status not determined | Not tested, no information available |

### Example: Complete Entry

```json
{
  "name": "nginx",
  "aliases": ["nginx-core", "nginx-full"],
  "description": "High-performance HTTP server",
  "compatibility": {
    "supported_versions": [
      {
        "version_range": ">=1.18.0",
        "status": "compatible",
        "notes": "Full Graviton support with optimized performance"
      },
      {
        "version_range": ">=1.14.0,<1.18.0",
        "status": "compatible_with_notes",
        "notes": "Works but upgrade recommended for better performance"
      },
      {
        "version_range": "<1.14.0",
        "status": "incompatible",
        "notes": "Upgrade required for ARM64 support"
      }
    ],
    "minimum_supported_version": "1.14.0",
    "recommended_version": "1.20.2",
    "migration_notes": "Consider enabling Graviton optimizations",
    "documentation_links": [
      "https://nginx.org/en/docs/arm64.html"
    ],
    "alternatives": [
      {
        "name": "apache2",
        "description": "Alternative web server with ARM64 support"
      }
    ]
  }
}
```

## Knowledge Base Features

### Intelligent Matching
- **Fuzzy name matching** - Handles package name variations
- **Alias resolution** - Maps alternative names to canonical packages
- **Version normalization** - Standardizes version formats
- **Confidence scoring** - Reliability indicators for matches

### Automatic OS Detection
- Detects OS from SBOM metadata
- Selects appropriate OS knowledge bases
- Handles multi-OS SBOMs

### Multi-Source Integration
- Combines multiple knowledge bases
- Resolves conflicts (deny lists take precedence)
- Provides comprehensive coverage

## Best Practices

### Knowledge Base Design
1. **Use canonical names** - Consistent software naming (lowercase, no special chars)
2. **Include comprehensive aliases** - Cover common name variations
3. **Provide clear notes** - Explain compatibility issues and solutions
4. **Document version ranges** - Be specific about supported versions
5. **Regular updates** - Keep information current

### Maintenance
1. **Test thoroughly** - Validate all compatibility claims on Graviton
2. **Schema validation** - Always validate against JSON schema
3. **Version control** - Track changes to knowledge bases
4. **Peer review** - Have others review compatibility information
5. **Documentation** - Maintain clear update logs

### Performance
1. **Limit size** - Include only relevant software
2. **Optimize aliases** - Remove unused aliases
3. **Use specific ranges** - Avoid overly broad version ranges

## Troubleshooting

### Knowledge Base Not Loading

```bash
# Check file exists
ls -la knowledge_bases/your_kb.json

# Validate JSON syntax
python -m json.tool knowledge_bases/your_kb.json

# Check file permissions
chmod 644 knowledge_bases/your_kb.json
```

### Software Not Matched

```bash
# Enable verbose logging
python graviton_validator.py -v sbom.json

# Check software names in knowledge base
jq '.software_compatibility[].name' knowledge_bases/custom_kb.json

# Add aliases for better matching
./scripts/manage_aliases.py add "alternative-name" "canonical-name"
```

### Update Scripts Failing

```bash
# Check Docker is running (for OS KB generation)
docker ps

# Check network connectivity (for scrapers)
curl -I https://github.com/aws/aws-graviton-getting-started

# Check Python dependencies
pip install -r requirements.txt
```

## See Also

- [Knowledge Base Guide](../docs/KNOWLEDGE_BASE_GUIDE.md) - Detailed KB creation guide
- [Scripts README](../scripts/README.md) - Update script documentation
- [Architecture Documentation](../docs/ARCHITECTURE_AND_WORKFLOWS.md) - How KBs are used
- [CLI Reference](../docs/CLI_REFERENCE.md) - Command-line usage with `-k` flag
