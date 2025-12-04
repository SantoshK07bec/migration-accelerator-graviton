# Troubleshooting Guide

This guide helps resolve common issues when using the Graviton Compatibility Validator.

## Common Error Messages

### SBOM Parsing Errors

#### Error: "Unable to parse SBOM file"

```
Error: Unable to parse SBOM file 'my_sbom.json': Invalid JSON format
```

**Causes:**
- Malformed JSON syntax
- File corruption
- Unsupported SBOM format

**Solutions:**
1. Validate JSON syntax:
   ```bash
   python -m json.tool my_sbom.json
   ```

2. Check file encoding (should be UTF-8):
   ```bash
   file my_sbom.json
   ```

3. Verify SBOM format is supported (CycloneDX, SPDX, or app_identifier.sh):
   ```bash
   head -20 my_sbom.json
   ```

#### Error: "No components found in SBOM"

```
Warning: No components found in SBOM file 'my_sbom.json'
```

**Causes:**
- Empty SBOM file
- Components in unexpected JSON structure
- SBOM format not recognized

**Solutions:**
1. Check SBOM structure:
   ```bash
   jq '.components | length' my_sbom.json  # CycloneDX
   jq '.packages | length' my_sbom.json    # SPDX
   ```

2. Verify component format matches expected structure
3. Enable verbose logging to see parsing details:
   ```bash
   python graviton_validator.py -v -k kb.json my_sbom.json
   ```

### Knowledge Base Errors

#### Error: "Knowledge base validation failed"

```
Error: Knowledge base validation failed: 'name' is a required property
```

**Causes:**
- Missing required fields in knowledge base
- Invalid JSON schema
- Incorrect version range syntax

**Solutions:**
1. Validate against schema:
   ```bash
   jsonschema -i my_kb.json schemas/knowledge_base_schema.json
   ```

2. Check required fields are present:
   ```json
   {
     "software_compatibility": [
       {
         "name": "required_field",
         "compatibility": {
           "supported_versions": []
         }
       }
     ]
   }
   ```

3. Verify version range syntax:
   ```json
   {
     "version_range": ">=1.0.0,<2.0.0"
   }
   ```

#### Error: "Knowledge base file not found"

```
Error: Knowledge base file not found: 'missing_kb.json'
```

**Solutions:**
1. Check file path and permissions:
   ```bash
   ls -la missing_kb.json
   ```

2. Use absolute paths if needed:
   ```bash
   python graviton_validator.py -k /full/path/to/kb.json sbom.json
   ```

3. Verify file exists and is readable:
   ```bash
   test -r missing_kb.json && echo "File is readable" || echo "File not readable"
   ```

### Matching and Analysis Errors

#### Warning: "No compatibility information found"

```
Warning: No compatibility information found for 'my-software-1.0.0'
```

**Causes:**
- Software not in knowledge base
- Name mismatch between SBOM and knowledge base
- Intelligent matching disabled or threshold too high

**Solutions:**
1. Check software name in knowledge base:
   ```bash
   jq '.software_compatibility[].name' knowledge_base.json | grep -i "my-software"
   ```

2. Add aliases to knowledge base:
   ```json
   {
     "name": "my-software",
     "aliases": ["my-software-alt", "mysoftware", "my_software"]
   }
   ```

3. Enable intelligent matching:
   ```bash
   python graviton_validator.py -k kb.json sbom.json
   ```

4. Lower similarity threshold in config:
   ```yaml
   matching:
     similarity_threshold: 0.6
   ```

#### Info: "Unknown compatibility" with guidance

```
Status: Unknown - Version not specified in SBOM. Due to unknown version, cannot determine Graviton compatibility. However, recent versions of this software are supported on Graviton (minimum supported version: 2.0.0).
```

**This is normal behavior when:**
- SBOM doesn't include version information
- Version format cannot be parsed
- Software is in knowledge base but version is unclear

**The tool now provides helpful guidance:**
- Indicates that recent versions are typically supported
- Shows minimum supported version when available
- Provides recommended version for upgrades
- Explains why compatibility cannot be determined

**No action needed** - this is informative messaging to help with migration planning.

#### Error: "Version comparison failed"

```
Error: Version comparison failed for 'software-1.0.0-beta': Invalid version format
```

**Causes:**
- Non-standard version format
- Missing version information
- Unsupported version syntax

**Solutions:**
1. Check version format in SBOM:
   ```bash
   jq '.components[].version' my_sbom.json | sort | uniq
   ```

2. The tool now handles this gracefully with informative messages:
   ```
   Version '1.0.0-beta' format not recognized. Due to unknown version, cannot determine Graviton compatibility. However, recent versions of this software are supported on Graviton (minimum supported version: 2.0.0).
   ```

3. Update knowledge base with flexible version ranges:
   ```json
   {
     "version_range": ">=1.0.0",
     "status": "compatible"
   }
   ```

4. For complex version formats, use empty version ranges:
   ```json
   {
     "version_range": "",
     "status": "compatible",
     "notes": "All versions supported"
   }
   ```

### Output and Reporting Errors

#### Error: "Permission denied writing output file"

```
Error: Permission denied: '/protected/path/report.json'
```

**Solutions:**
1. Check directory permissions:
   ```bash
   ls -ld /protected/path/
   ```

2. Use writable directory:
   ```bash
   python graviton_validator.py -o ~/reports/report.json -k kb.json sbom.json
   ```

3. Create output directory:
   ```bash
   mkdir -p reports
   python graviton_validator.py -o reports/report.json -k kb.json sbom.json
   ```

#### Error: "Excel report generation failed"

```
Error: Excel report generation failed: No module named 'openpyxl'
```

**Solutions:**
1. Install required dependencies:
   ```bash
   pip install openpyxl
   ```

2. Reinstall all requirements:
   ```bash
   pip install -r requirements.txt
   ```

3. Use alternative output format:
   ```bash
   python graviton_validator.py -f json -k kb.json sbom.json
   ```

## Performance Issues

### Slow Analysis with Large SBOM Files

**Symptoms:**
- Analysis takes several minutes
- High memory usage
- System becomes unresponsive

**Solutions:**

1. **Enable system package filtering:**
   ```bash
   python graviton_validator.py --exclude-system -k kb.json large_sbom.json
   ```

2. **Split large SBOM files:**
   ```python
   import json
   
   # Split SBOM into smaller chunks
   with open('large_sbom.json') as f:
       sbom = json.load(f)
   
   components = sbom.get('components', [])
   chunk_size = 1000
   
   for i in range(0, len(components), chunk_size):
       chunk = components[i:i+chunk_size]
       chunk_sbom = sbom.copy()
       chunk_sbom['components'] = chunk
       
       with open(f'sbom_chunk_{i//chunk_size}.json', 'w') as f:
           json.dump(chunk_sbom, f)
   ```

3. **Optimize knowledge base:**
   ```bash
   # Remove unused entries
   jq '.software_compatibility |= map(select(.name | test("relevant_pattern")))' kb.json > optimized_kb.json
   ```

4. **Increase system resources:**
   - Add more RAM
   - Use faster storage (SSD)
   - Run on more powerful hardware

### High Memory Usage

**Solutions:**

1. **Monitor memory usage:**
   ```bash
   /usr/bin/time -v python graviton_validator.py -k kb.json sbom.json
   ```

2. **Process files individually:**
   ```bash
   for sbom in *.json; do
       python graviton_validator.py -k kb.json "$sbom"
   done
   ```

3. **Use streaming processing (if available):**
   ```bash
   python graviton_validator.py --stream -k kb.json large_sbom.json
   ```

## Configuration Issues

### Configuration File Not Loaded

**Symptoms:**
- Default settings used instead of config file
- Config file settings ignored

**Solutions:**

1. **Verify config file path:**
   ```bash
   python graviton_validator.py -c config.yaml -v sbom.json
   ```

2. **Check YAML syntax:**
   ```bash
   python -c "import yaml; yaml.safe_load(open('config.yaml'))"
   ```

3. **Use absolute path:**
   ```bash
   python graviton_validator.py -c /full/path/to/config.yaml sbom.json
   ```

4. **Validate config structure:**
   ```yaml
   knowledge_base:
     default_files:
       - "kb.json"
   output:
     default_format: "text"
   ```

### Environment Variables Not Working

**Solutions:**

1. **Check environment variable names:**
   ```bash
   export GRAVITON_VALIDATOR_CONFIG="/path/to/config.yaml"
   export GRAVITON_VALIDATOR_KB="/path/to/kb.json"
   ```

2. **Verify variables are set:**
   ```bash
   env | grep GRAVITON_VALIDATOR
   ```

3. **Use explicit command-line options:**
   ```bash
   python graviton_validator.py -c config.yaml -k kb.json sbom.json
   ```

## Integration Issues

### CI/CD Pipeline Failures

#### Exit Code Issues

**Problem:** Pipeline fails even when analysis completes successfully

**Solutions:**

1. **Check exit codes:**
   ```bash
   python graviton_validator.py -k kb.json sbom.json
   echo "Exit code: $?"
   ```

2. **Handle different exit codes in pipeline:**
   ```bash
   # In CI script
   python graviton_validator.py -k kb.json sbom.json
   EXIT_CODE=$?
   
   case $EXIT_CODE in
       0) echo "All components compatible" ;;
       1) echo "Some incompatible components found" ;;
       2) echo "Critical error occurred"; exit 1 ;;
   esac
   ```

3. **Use JSON output for programmatic handling:**
   ```bash
   python graviton_validator.py -k kb.json -f json sbom.json > results.json
   COMPATIBLE=$(jq '.summary.compatible' results.json)
   TOTAL=$(jq '.summary | add' results.json)
   ```

#### Docker Integration Issues

**Problem:** Tool doesn't work correctly in Docker container

**Solutions:**

1. **Check file permissions:**
   ```dockerfile
   RUN chmod +x graviton_validator.py
   ```

2. **Mount volumes correctly:**
   ```bash
   docker run -v $(pwd):/workspace graviton-validator -k /workspace/kb.json /workspace/sbom.json
   ```

3. **Use proper base image:**
   ```dockerfile
   FROM python:3.9-slim
   # Install required system packages
   RUN apt-get update && apt-get install -y curl
   ```

### GitHub Actions Issues

**Problem:** Action fails with permission or dependency errors

**Solutions:**

1. **Install dependencies correctly:**
   ```yaml
   - name: Install dependencies
     run: |
       python -m pip install --upgrade pip
       pip install -r requirements.txt
   ```

2. **Set proper permissions:**
   ```yaml
   - name: Set permissions
     run: chmod +x graviton_validator.py
   ```

3. **Use artifacts correctly:**
   ```yaml
   - name: Upload results
     uses: actions/upload-artifact@v3
     with:
       name: graviton-report
       path: |
         *.json
         *.md
   ```

## Debugging Techniques

### Enable Verbose Logging

```bash
# Maximum verbosity
python graviton_validator.py -v -k kb.json sbom.json

# With log file
python graviton_validator.py -v -k kb.json sbom.json 2> debug.log
```

### Inspect Intermediate Data

```python
# Add debug prints to see parsed data
import json

# In your debugging session
with open('sbom.json') as f:
    sbom_data = json.load(f)

print("SBOM structure:")
print(json.dumps(sbom_data, indent=2)[:500])

# Check components
if 'components' in sbom_data:
    print(f"Found {len(sbom_data['components'])} components")
    for comp in sbom_data['components'][:5]:
        print(f"  - {comp.get('name', 'unknown')} {comp.get('version', 'no-version')}")
```

### Test Individual Components

```bash
# Create minimal test SBOM
cat > test_sbom.json << EOF
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.4",
  "components": [
    {
      "type": "library",
      "name": "nginx",
      "version": "1.20.2"
    }
  ]
}
EOF

# Test with this minimal SBOM
python graviton_validator.py -v -k kb.json test_sbom.json
```

### Validate Knowledge Base Entries

```python
# Test specific knowledge base entries
import json

with open('knowledge_base.json') as f:
    kb = json.load(f)

for software in kb['software_compatibility']:
    name = software['name']
    versions = software['compatibility']['supported_versions']
    
    print(f"Software: {name}")
    for version_info in versions:
        print(f"  Range: {version_info['version_range']}")
        print(f"  Status: {version_info['status']}")
```

## Getting Help

### Log Analysis

When reporting issues, include:

1. **Command used:**
   ```bash
   python graviton_validator.py -v -k kb.json sbom.json
   ```

2. **Error output:**
   ```bash
   python graviton_validator.py -k kb.json sbom.json 2> error.log
   ```

3. **System information:**
   ```bash
   python --version
   pip list | grep -E "(jsonschema|openpyxl|Levenshtein|yaml)"
   ```

4. **Sample files (if possible):**
   - Minimal SBOM that reproduces the issue
   - Relevant knowledge base entries
   - Configuration file (if used)

### Creating Minimal Reproducible Examples

```bash
# Create minimal test case
cat > minimal_sbom.json << EOF
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.4",
  "components": [
    {
      "type": "library",
      "name": "problematic-software",
      "version": "1.0.0"
    }
  ]
}
EOF

cat > minimal_kb.json << EOF
{
  "software_compatibility": [
    {
      "name": "problematic-software",
      "compatibility": {
        "supported_versions": [
          {
            "version_range": ">=1.0.0",
            "status": "compatible"
          }
        ]
      }
    }
  ]
}
EOF

# Test minimal case
python graviton_validator.py -v -k minimal_kb.json minimal_sbom.json
```

### Community Resources

- Check existing issues in the project repository
- Review documentation for similar use cases
- Test with provided sample files
- Validate JSON files with online tools
- Use schema validators for knowledge base files

Remember to sanitize any sensitive information before sharing files or logs for troubleshooting.