# Persistent SBOM Component Name Aliases

## Overview

The Graviton Validator uses a persistent alias system to handle cases where SBOM component names don't exactly match OS knowledge base package names. This system survives OS knowledge base regeneration.

## How It Works

1. **Persistent Storage**: Aliases are stored in `knowledge_bases/os_knowledge_bases/common_aliases.json`
2. **Automatic Loading**: Aliases are loaded automatically when any knowledge base is initialized
3. **Regeneration Safe**: The alias file is separate from generated OS knowledge bases

## Common Use Cases

### Truncated Names
SBOMs often truncate long package names:
- `node_exporter` → `prometheus-node-exporter`
- `networkd-dispat` → `networkd-dispatcher`
- `unattended-upgr` → `unattended-upgrades`

### Alternative Names
Different tools may use different names:
- `docker` → `docker.io`
- `nginx` → `nginx-core`
- `mysql` → `mysql-server`

## Managing Aliases

### Using the Management Script

```bash
# List all current aliases
python scripts/manage_aliases.py list

# Add a new alias
python scripts/manage_aliases.py add sbom_name target_name

# Remove an alias
python scripts/manage_aliases.py remove sbom_name
```

### Examples

```bash
# Add alias for truncated name
python scripts/manage_aliases.py add "prometheus-exp" "prometheus-exporter"

# Add alias for alternative name
python scripts/manage_aliases.py add "httpd" "apache2"

# Remove an alias
python scripts/manage_aliases.py remove "old_alias"
```

### Manual Editing

You can also edit `knowledge_bases/os_knowledge_bases/common_aliases.json` directly:

```json
{
  "metadata": {
    "name": "Common SBOM Name Aliases",
    "description": "Persistent aliases for truncated or variant component names",
    "version": "1.0"
  },
  "aliases": {
    "sbom_component_name": "os_package_name",
    "node_exporter": "prometheus-node-exporter"
  }
}
```

## Best Practices

### When to Add Aliases

1. **Truncated Names**: When SBOMs consistently truncate package names
2. **Tool Variations**: When different SBOM tools use different names
3. **Common Alternatives**: When packages have well-known alternative names

### Naming Guidelines

1. **Use lowercase**: All aliases should be lowercase
2. **Match SBOM exactly**: Alias should match exactly what appears in SBOMs
3. **Target real packages**: Target should be actual package name in OS KB

### Maintenance

1. **Regular Review**: Periodically review aliases for relevance
2. **Documentation**: Document why specific aliases were added
3. **Testing**: Test aliases after OS KB regeneration

## Integration with OS KB Regeneration

### Workflow

1. **Regenerate OS KB**: Update OS knowledge base files as needed
2. **Aliases Preserved**: Common aliases remain intact in separate file
3. **Automatic Loading**: Next tool run automatically loads persistent aliases
4. **No Manual Steps**: No need to re-add aliases after regeneration

### Validation

After OS KB regeneration, validate aliases still work:

```bash
# Test specific aliases
python -c "
from graviton_validator.knowledge_base.data_structures import JSONKnowledgeBase
kb = JSONKnowledgeBase()
kb.load_from_files(['knowledge_bases/os_knowledge_bases/ubuntu-20.04-graviton-packages.json'])
print('node_exporter:', kb.get_compatibility('node_exporter', '1.0.0').status)
"
```

## Troubleshooting

### Alias Not Working

1. **Check File**: Verify `common_aliases.json` exists and is valid JSON
2. **Check Loading**: Look for "Loaded X persistent aliases" in logs
3. **Check Spelling**: Ensure alias matches SBOM name exactly
4. **Check Target**: Verify target package exists in OS knowledge base

### Performance Impact

- **Minimal**: Aliases are loaded once at startup
- **Memory**: Small memory footprint (typically <1KB)
- **Speed**: No impact on analysis performance

## Schema Validation

The alias file follows a JSON schema at `knowledge_bases/schemas/common_aliases_schema.json`:

```bash
# Validate alias file
jsonschema -i knowledge_bases/os_knowledge_bases/common_aliases.json \
           knowledge_bases/schemas/common_aliases_schema.json
```