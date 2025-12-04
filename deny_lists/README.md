# Deny Lists

This directory contains JSON files that define packages explicitly unsupported on AWS Graviton processors.

## Automatic Loading

All JSON files in this directory are automatically loaded when the Graviton Compatibility Validator runs. No additional configuration is required.

## Current Deny Lists

### `proprietary_packages.json`
- **Microsoft SQL Server**: Database server without ARM64 support (Linux x86_64 only)
- **Recommended alternatives**: PostgreSQL, MySQL, Amazon RDS

### `x86_specific_packages.json`
- **Intel MKL**: Math Kernel Library optimized for x86 processors
- **Recommended alternative**: OpenBLAS

## Adding New Deny Lists

1. Create a new JSON file following the schema in `../schemas/deny_list_schema.json`
2. Use descriptive filenames (e.g., `database_specific.json`, `legacy_libraries.json`)
3. Include clear reasons and recommended alternatives
4. Test with `jsonschema -i your_file.json ../schemas/deny_list_schema.json`

## Schema Reference

```json
{
  "$schema": "../schemas/deny_list_schema.json",
  "deny_list": [
    {
      "name": "package-name",
      "aliases": ["alternative-name"],
      "reason": "Why this package is unsupported",
      "minimum_supported_version": "1.0.0",
      "recommended_alternative": "suggested-package"
    }
  ]
}
```

## Guidelines

- **Be specific**: Clearly explain why a package is denied
- **Provide alternatives**: Always suggest Graviton-compatible replacements when possible
- **Use aliases**: Include common alternative names for better detection
- **Categorize**: Group related packages in themed files
- **Validate**: Ensure JSON follows the schema before committing