# Helper Scripts

Utility scripts for maintaining knowledge bases used by the Graviton Compatibility Validator.

## Scripts Overview

### OS Package Databases
- **`generate_all_os_kb.sh`** - Generate knowledge bases for all supported OS versions
- **`generate_docker_kb.sh`** - Generate knowledge base for specific OS version
- **`dump_os_packages.sh`** - Extract packages from running Graviton instance
- **`convert_os_packages.py`** - Convert package dumps to knowledge base JSON

### External Data Sources
- **`isv_scraper.py`** - Update ISV software database from AWS Graviton Getting Started
- **`arm_ecosystem_scraper.py`** - Update ARM ecosystem database from Arm Developer Hub

### Alias Management
- **`manage_aliases.py`** - Manage package name aliases for better matching

---

## OS Package Databases

### Generate All OS Knowledge Bases

```bash
cd scripts
./generate_all_os_kb.sh
```

**Generates knowledge bases for:**
- Amazon Linux 2, 2023
- Ubuntu 18.04, 20.04, 22.04, 24.04
- CentOS 8
- Alpine 3.17, 3.18
- Debian 11, 12

**Output:** `os_packages/{os}-{version}-graviton-packages.json`

### Generate Specific OS

```bash
cd scripts
./generate_docker_kb.sh ubuntu 22.04
./generate_docker_kb.sh amazonlinux 2023
./generate_docker_kb.sh alpine 3.18
```

**How it works:**
1. Builds ARM64 Docker container for specified OS
2. Installs package management tools
3. Dumps available packages
4. Converts to JSON format
5. Cleans up automatically

### Extract from Running Instance

```bash
# Run on a Graviton instance
cd scripts
./dump_os_packages.sh > packages.jsonl
python convert_os_packages.py packages.jsonl ../os_packages/custom-packages.json
```

---

## External Data Sources

### Update ISV Database

```bash
cd scripts
python isv_scraper.py
```

**Updates:** `knowledge_bases/isv_graviton_packages.json`

**Source:** [AWS Graviton Getting Started - ISV List](https://github.com/aws/aws-graviton-getting-started/blob/main/isv.md)

### Update ARM Ecosystem Database

```bash
cd scripts
python arm_ecosystem_scraper.py
```

**Updates:** `knowledge_bases/arm_ecosystem_packages.json`

**Source:** [Arm Developer Hub Ecosystem Dashboard](https://www.arm.com/developer-hub/ecosystem-dashboard/)

---

## Alias Management

### Manage Package Name Aliases

```bash
cd scripts

# Add alias
./manage_aliases.py add "node.js" "nodejs"

# Remove alias
./manage_aliases.py remove "node.js"

# List all aliases
./manage_aliases.py list

# Search aliases
./manage_aliases.py search "python"
```

**Updates:** `knowledge_bases/os_knowledge_bases/common_aliases.json`

**Purpose:** Maps alternative package names to canonical names for better SBOM matching

---

## Prerequisites

### Docker (for OS package scripts)
```bash
docker --version
docker run --rm --platform linux/arm64 ubuntu:22.04 uname -m
```

### Python Dependencies (for scrapers)
```bash
pip install requests beautifulsoup4
```

---

## Troubleshooting

### Docker not working
```bash
# Check Docker
docker info

# Enable ARM64 support in Docker Desktop settings
```

### Scripts not executable
```bash
chmod +x generate_all_os_kb.sh
chmod +x generate_docker_kb.sh
chmod +x dump_os_packages.sh
chmod +x manage_aliases.py
```

### Network connectivity
```bash
# Test GitHub access
curl -I https://github.com/aws/aws-graviton-getting-started

# Test Arm ecosystem access
curl -I https://www.arm.com/developer-hub/ecosystem-dashboard/
```

---

## See Also

- **[Knowledge Bases README](../knowledge_bases/README.md)** - KB directory structure and usage
- **[Knowledge Base Guide](../docs/KNOWLEDGE_BASE_GUIDE.md)** - Detailed KB creation guide
- **[Persistent Aliases](../docs/PERSISTENT_ALIASES.md)** - Alias management details
