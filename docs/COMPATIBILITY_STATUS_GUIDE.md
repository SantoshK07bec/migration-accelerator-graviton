# Compatibility Status Guide

This guide explains the compatibility status values used throughout the Graviton Compatibility Validator and their meanings.

## Status Values

The tool uses six distinct compatibility status values defined in the `CompatibilityStatus` enum:

### 1. `compatible`
**Meaning**: Component is confirmed to work with AWS Graviton processors (ARM64 architecture)

**When assigned**:
- ARM64-specific wheels/binaries are available
- Package explicitly declares ARM64 support
- Pure managed code (.NET) or pure JavaScript (NodeJS)
- ARM64 runtime identifiers found in metadata
- Knowledge base confirms compatibility

**Examples**:
- Python package with `linux_aarch64` wheels
- .NET package with `linux-arm64` runtime identifier
- NodeJS package with explicit ARM64 CPU support
- Java library with ARM64 classifier

### 2. `incompatible`
**Meaning**: Component is confirmed to NOT work with Graviton processors

**When assigned**:
- Package version is below minimum supported version for known problematic libraries
- Explicitly listed in deny lists (e.g., Intel-specific libraries)
- Known architecture-specific dependencies that don't support ARM64

**Examples**:
- Intel MKL (Math Kernel Library) - x86-specific
- Old versions of libraries with known ARM64 issues
- Proprietary software without ARM64 builds

### 3. `unknown`
**Meaning**: Compatibility status cannot be determined from available information

**When assigned**:
- No information available in knowledge base
- Package metadata doesn't indicate architecture support
- API calls failed or returned insufficient data
- Source-only distributions requiring compilation

**Examples**:
- Python packages with only source distributions
- Packages not found in repository APIs
- Custom or internal packages
- Packages with insufficient metadata

### 4. `needs_upgrade`
**Meaning**: Component is not compatible in current version but has compatible versions available

**When assigned**:
- Current version lacks ARM64 support but newer versions have it
- Package version is below minimum supported version for ARM64
- Upgrade path to compatible version is available
- Knowledge base indicates version-specific compatibility

**Examples**:
- Python package with ARM64 wheels in newer versions
- Java library with ARM64 support added in later releases
- .NET package with ARM64 runtime support in updated versions
- NodeJS package with native module fixes for ARM64

### 5. `needs_verification`
**Meaning**: Component may work but requires manual testing and verification

**When assigned**:
- Native modules or compiled components detected
- Prebuilt binaries available but ARM64 support unclear
- Packages with potential architecture-specific behavior
- Components requiring compilation from source

**Examples**:
- NodeJS packages with native modules
- .NET packages with native dependencies
- Python packages requiring C extensions
- Java libraries with JNI components

### 6. `needs_version_verification`
**Meaning**: Software is known to be Graviton-compatible but version information is missing or unrecognized

**When assigned**:
- Component found in knowledge base but SBOM lacks version information
- Version format is unrecognized but software is known to support Graviton
- Knowledge base has version requirements but current version is unknown

**Examples**:
- SBOM entries without version fields
- Version strings in non-standard formats
- Components with minimum version requirements but unknown current version

## Status Assignment Logic

### Analysis Priority Order
1. **Knowledge Base** (Primary): Direct compatibility information
2. **Repository Metadata** (Secondary): API-based analysis
3. **Fallback**: Default to `unknown` with guidance

### Runtime-Specific Behavior

#### Python (PyPI)
- `compatible`: ARM64 wheels or universal wheels available
- `needs_upgrade`: Current version lacks ARM64 wheels but newer versions have them
- `unknown`: Source distribution only or no wheels
- `needs_verification`: Not used (treated as `unknown`)

#### NodeJS (NPM)
- `compatible`: Explicit ARM64 support or pure JavaScript
- `needs_upgrade`: Current version incompatible but newer versions support ARM64
- `needs_verification`: Native modules detected
- `unknown`: Cannot determine from metadata

#### .NET (NuGet)
- `compatible`: ARM64 frameworks, runtime identifiers, or pure managed code
- `needs_upgrade`: Current version lacks ARM64 support but newer versions have it
- `needs_verification`: Native dependencies detected
- `unknown`: Insufficient metadata or API failures

#### Java (Maven)
- `compatible`: ARM64 classifier or version includes fixes
- `incompatible`: Below minimum version for known issues
- `needs_upgrade`: Current version incompatible but upgrade path available
- `unknown`: Native code patterns or insufficient data

## Report Formatting

### Excel Reports
Status values appear in the "Status" column with color coding:
- `compatible` → Green background
- `incompatible` → Red background
- `needs_upgrade` → Light orange background
- `needs_verification` → Yellow background
- `needs_version_verification` → Light lavender background
- `unknown` → Yellow background

### Text Reports
Status values are displayed with symbols:
- `compatible` → ✅ (green)
- `incompatible` → ❌ (red)
- `needs_upgrade` → 🔄 (orange)
- `needs_verification` → ⚠️ (yellow)
- `needs_version_verification` → 🔍 (purple)
- `unknown` → ❓ (yellow)

### JSON Reports
Status values are included as lowercase strings in the `status` field:
```json
{
  "compatibility": {
    "status": "compatible",
    "current_version_supported": true,
    "notes": "ARM64 wheels available"
  }
}
```

## Migration Recommendations

### By Status Priority

#### High Priority: `incompatible`
- **Action**: Immediate upgrade or replacement required
- **Steps**: 
  1. Check recommended version
  2. Test upgrade path
  3. Find alternatives if no upgrade available

#### High Priority: `needs_upgrade`
- **Action**: Upgrade to compatible version
- **Steps**:
  1. Review minimum and recommended versions
  2. Plan upgrade timeline and testing
  3. Update dependency management files
  4. Test upgraded version thoroughly

#### Medium Priority: `needs_verification`
- **Action**: Test in ARM64 environment
- **Steps**:
  1. Deploy to Graviton test environment
  2. Run comprehensive functionality tests
  3. Monitor performance and stability

#### Medium Priority: `needs_version_verification`
- **Action**: Verify version meets requirements
- **Steps**:
  1. Check current installed version
  2. Compare against minimum supported version
  3. Upgrade if necessary before migration
  4. Update SBOM with correct version information

#### Low Priority: `unknown`
- **Action**: Research and test when possible
- **Steps**:
  1. Check vendor documentation
  2. Contact vendor for ARM64 support status
  3. Test in development environment

#### No Action: `compatible`
- **Action**: No changes required
- **Note**: Monitor for any runtime issues during migration

## Best Practices

### For Development Teams
1. **Prioritize by status**: Focus on `incompatible` components first
2. **Test verification items**: Always test `needs_verification` components
3. **Document findings**: Update knowledge base with test results
4. **Monitor unknowns**: Keep track of `unknown` components for future research

### For Operations Teams
1. **Plan migration phases**: Group components by status for staged rollouts
2. **Prepare rollback plans**: Especially for `needs_verification` components
3. **Monitor performance**: Watch for issues with `unknown` components
4. **Update documentation**: Record actual compatibility findings

### For Security Teams
1. **Review incompatible alternatives**: Ensure replacements meet security requirements
2. **Validate verification results**: Confirm `needs_verification` components are secure
3. **Track unknown risks**: Monitor `unknown` components for security implications

## Confidence Levels

Status assignments include confidence levels (0.0-1.0):

- **0.9-1.0**: High confidence (knowledge base match, explicit metadata)
- **0.6-0.8**: Medium confidence (inferred from patterns, API metadata)
- **0.0-0.5**: Low confidence (fallback logic, insufficient data)

Higher confidence levels indicate more reliable status assignments.

## Troubleshooting Status Issues

### Unexpected `unknown` Status
- Check if package exists in repository APIs
- Verify package name spelling and aliases
- Review knowledge base entries
- Enable verbose logging for detailed analysis

### Missing `compatible` Status
- Verify ARM64 wheels/binaries are actually available
- Check if metadata lookup is enabled for the runtime
- Review API response data in debug logs
- Consider adding to knowledge base

### False `incompatible` Status
- Check deny list entries
- Review knowledge base version ranges
- Verify component version parsing
- Update knowledge base if needed

## Contributing Status Information

To improve status accuracy:

1. **Update Knowledge Base**: Add confirmed compatibility information
2. **Report Issues**: Submit corrections for incorrect status assignments
3. **Share Test Results**: Contribute findings from ARM64 testing
4. **Enhance Metadata**: Improve repository metadata analysis logic

See [KNOWLEDGE_BASE_GUIDE.md](KNOWLEDGE_BASE_GUIDE.md) for detailed contribution guidelines.