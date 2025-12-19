# Quick Start Guide

Get started with Migration Accelerator for Graviton in 5 minutes.

## Choose Your Approach

### 🚀 Option 1: AWS Hosted (Recommended)
**Fully managed analysis with automatic processing**

### 💻 Option 2: Local Analysis
**Run analysis directly on your machine**

---

## 🚀 AWS Hosted Solution

### Step 1: Deploy Infrastructure (One-time setup)

```bash
# Clone the repository
git clone https://github.com/awslabs/migration-accelerator-graviton
cd migration-accelerator-graviton

# Deploy AWS infrastructure using deploy script (recommended)
./deploy.sh

# The deploy script automatically:
# - Creates/manages Terraform state bucket
# - Deploys Terraform infrastructure
# - Enables S3 EventBridge notifications
# - Verifies deployment
# - Shows usage instructions

# Alternative: Use existing state bucket
./deploy.sh deploy --state-bucket my-existing-bucket

# Manual deployment (requires state bucket)
cd terraform
terraform init \
  -backend-config="bucket=my-terraform-state-bucket" \
  -backend-config="region=us-east-1"
terraform apply
cd ..
```

### Step 2: Upload Your Files

```bash
# Get your S3 bucket name
BUCKET_NAME=$(cd terraform && terraform output -raw s3_bucket_name)
echo "Your bucket: $BUCKET_NAME"

# Individual mode: Upload SBOM files to trigger EventBridge → Lambda → Batch Job
aws s3 cp my-app-sbom.json s3://$BUCKET_NAME/input/individual/

# Batch mode: Upload multiple SBOMs and manifest file
aws s3 sync ./my-sbom-files/ s3://$BUCKET_NAME/input/batch/my-project/
cat > batch-manifest.txt <<EOF
app1.sbom.json
app2.sbom.json
app3.sbom.json
EOF
aws s3 cp batch-manifest.txt s3://$BUCKET_NAME/input/batch/my-project/
```

### Step 3: Monitor Analysis

```bash
# Get queue name from Terraform output
QUEUE_NAME=$(cd terraform && terraform output -raw batch_job_queue_name)

# Watch Batch job execution
aws batch list-jobs --job-queue $QUEUE_NAME --job-status RUNNING

# Monitor logs
aws logs tail /aws/batch/graviton-validator --follow

# View CloudWatch dashboard
echo "Dashboard: $(cd terraform && terraform output -raw dashboard_url)"
```

### Step 4: Download Results

```bash
# List available results
aws s3 ls s3://$BUCKET_NAME/output/individual/ --recursive

# Download all reports for a specific SBOM
aws s3 sync s3://$BUCKET_NAME/output/individual/<sbom-name>/ ./results/

# Download batch project results
aws s3 sync s3://$BUCKET_NAME/output/batch/my-project/ ./results/

# Download specific report formats
aws s3 cp s3://$BUCKET_NAME/output/individual/<sbom-name>/<sbom-name>.xlsx ./
aws s3 cp s3://$BUCKET_NAME/output/individual/<sbom-name>/<sbom-name>_analysis.json ./
```

**Your results include:**
- 📊 **Excel Report**: `*.xlsx` - Detailed compatibility analysis
- 📄 **JSON Report**: `*_analysis.json` - Machine-readable results
- 📝 **Markdown Report**: `*_analysis.md` - Human-readable summary

---

## 💻 Local Analysis

### Step 1: Install Requirements

```bash
# Clone repository
git clone <repository-url>
cd migration-accelerator-graviton

# Install Python dependencies
pip install -r requirements.txt
```

### Step 2: Basic Analysis

```bash
# Analyze SBOM file (knowledge base only)
python graviton_validator.py examples/sample_cyclonedx.json

# Analyze multiple SBOM files
python graviton_validator.py sbom1.json sbom2.json

# Analyze directory of SBOM files
python graviton_validator.py -d ./sbom-files/
```

### Step 3: Enhanced Analysis (Recommended)

```bash
# With runtime testing (actually tests package installation)
python graviton_validator.py my-app-sbom.json --runtime --test --containers

# Generate Excel report
python graviton_validator.py my-app-sbom.json --runtime --test --containers -f excel -o report.xlsx

# Multi-stage analysis for large applications
python graviton_validator.py --sbom-only my-app-sbom.json
python graviton_validator.py --runtime-only auto --test --containers
python graviton_validator.py --merge-runtime ./output_files/ -f excel
```

### Step 4: Advanced Features

```bash
# Batch analysis with runtime testing
python graviton_validator.py -d ./sbom-files/ --runtime --test --containers -f excel

# Include JAR analysis
python graviton_validator.py my-app-sbom.json --runtime --test --jars examples/JARs/*.jar -f excel

# Custom knowledge base
python graviton_validator.py my-app-sbom.json -k custom_kb.json --runtime --test
```

---

## 📊 Understanding Results

### Compatibility Status

| Status | Icon | Meaning | Action |
|--------|------|---------|--------|
| **Compatible** | ✅ | Ready for Graviton | Migrate with confidence |
| **Needs Upgrade** | ⚠️ | Newer version supports ARM64 | Update to recommended version |
| **Incompatible** | ❌ | No ARM64 support available | Find alternatives |
| **Needs Testing** | 🔍 | Requires manual verification | Test on Graviton instances |
| **Unknown** | ❓ | No compatibility data | Research and test |

### Sample Output

```
Graviton Compatibility Analysis Report
=====================================

📊 Summary:
  Total Components: 150
  ✅ Compatible: 120 (80.0%)
  ⚠️ Needs Upgrade: 20 (13.3%)
  ❌ Incompatible: 5 (3.3%)
  🔍 Needs Testing: 3 (2.0%)
  ❓ Unknown: 2 (1.3%)

🎯 Migration Readiness: 80% - Good for Graviton migration

⚠️ Components Requiring Attention:
  • numpy 1.19.0 → Upgrade to 1.21.0+ for ARM64 support
  • tensorflow 2.4.0 → No ARM64 wheels available, consider alternatives
  • bcrypt 3.2.0 → Native code requires ARM64 testing

💡 Next Steps:
  1. Update 20 components to newer versions
  2. Find alternatives for 5 incompatible components
  3. Test 3 components on Graviton instances
  4. 120 components are ready to migrate!
```

---

## 🔧 Common Scenarios

### Java Applications

```bash
# Analyze Java SBOM with runtime testing
python graviton_validator.py java-app-sbom.json --runtime --test --containers

# Include additional JAR files
python graviton_validator.py java-app-sbom.json --jars examples/JARs/*.jar --runtime --test

# Generate detailed Excel report
python graviton_validator.py java-app-sbom.json --runtime --test --containers -f excel -o java-compatibility.xlsx
```

### Python Applications

```bash
# Analyze Python SBOM with pip testing
python graviton_validator.py python-app-sbom.json --runtime --test --containers

# With custom knowledge base
python graviton_validator.py python-app-sbom.json -k knowledge_bases/python_runtime_dependencies.json --runtime --test

# Multi-stage for large Python applications
python graviton_validator.py --sbom-only python-app-sbom.json
python graviton_validator.py --runtime-only python --test --containers
```

### Node.js Applications

```bash
# Analyze Node.js SBOM with npm testing
python graviton_validator.py nodejs-app-sbom.json --runtime --test --containers

# Focus on native modules (critical for ARM64)
python graviton_validator.py nodejs-app-sbom.json --runtime --test --containers --detailed
```

### .NET Applications

```bash
# Analyze .NET SBOM with NuGet testing
python graviton_validator.py dotnet-app-sbom.json --runtime --test --containers

# Batch analysis for multiple .NET applications
python graviton_validator.py -d ./dotnet-sboms/ --runtime --test --containers -f excel
```

### Multi-Runtime Applications

```bash
# Analyze SBOM with multiple runtimes detected
python graviton_validator.py mixed-app-sbom.json --runtime --test --containers -f excel

# Multi-stage analysis for optimal performance
python graviton_validator.py --sbom-only mixed-app-sbom.json
python graviton_validator.py --runtime-only auto --test --containers
python graviton_validator.py --merge-runtime ./output_files/ -f excel -o final-report.xlsx

# Selective runtime analysis
python graviton_validator.py --runtime-only python --input-dir ./output_files/ --test --containers
python graviton_validator.py --runtime-only java --input-dir ./output_files/ --test --containers
```

### Enterprise Portfolio Analysis

```bash
# Analyze entire application portfolio
python graviton_validator.py -d ./enterprise-sboms/ --runtime --test --containers --output-dir ./portfolio-results/

# Generate consolidated portfolio report
python graviton_validator.py --merge ./portfolio-results/*.json -f excel -o portfolio-compatibility.xlsx

# Focus on specific technology stacks
python graviton_validator.py -d ./java-sboms/ --runtime --test --containers -f excel -o java-portfolio.xlsx
python graviton_validator.py -d ./python-sboms/ --runtime --test --containers -f excel -o python-portfolio.xlsx
```

---

## 🚨 Troubleshooting

### Common Issues

#### "No SBOM files found"
```bash
# Make sure file exists and has .json extension
ls -la *.json

# Use full path
python graviton_validator.py /full/path/to/sbom.json
```

#### "Missing prerequisites"
```bash
# Install missing tools
# For Java: Install Maven
# For Python: Install pip
# For Node.js: Install npm
# For .NET: Install dotnet CLI

# Or use container mode to avoid local dependencies
python graviton_validator.py sbom.json --runtime --test --containers
```

#### "Permission denied" (AWS)
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify S3 bucket access
aws s3 ls s3://your-bucket-name/
```

#### "Analysis failed"
```bash
# Enable debug logging
python graviton_validator.py sbom.json --debug -v

# Check log file and keep temp files
python graviton_validator.py sbom.json --log-file analysis.log --no-cleanup

# Test with example files
python graviton_validator.py examples/sample_cyclonedx.json -v
```

### Getting Help

- 📖 **[Technical Documentation](../TECHNICAL_README.md)** - Advanced configuration
- 🐛 **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Detailed problem solving
- 💡 **[CLI Reference](CLI_REFERENCE.md)** - Complete command-line reference

---

## 🎯 Next Steps

### After Analysis

1. **Review Results**: Check compatibility status for each component
2. **Plan Updates**: Identify components that need version upgrades
3. **Find Alternatives**: Research replacements for incompatible components
4. **Test Critical Components**: Verify "Needs Testing" components on Graviton
5. **Start Migration**: Begin with highly compatible applications

### Advanced Usage

- **CI/CD Integration**: Add compatibility checks to your pipeline
- **Portfolio Analysis**: Analyze multiple applications for migration planning
- **Custom Knowledge Base**: Add your own compatibility data (see [Knowledge Base Guide](KNOWLEDGE_BASE_GUIDE.md))
- **Update Knowledge Bases**: Refresh OS packages and ISV data using [helper scripts](../scripts/README.md)
- **Automated Reporting**: Set up scheduled analysis and reporting

### Migration Planning

1. **Start with Compatible Apps**: Migrate applications with 90%+ compatibility first
2. **Batch Similar Apps**: Group applications by technology stack
3. **Plan Upgrade Windows**: Schedule component updates before migration
4. **Test Thoroughly**: Use Graviton instances for final validation
5. **Monitor Performance**: Compare performance after migration

---

**Ready to analyze your first application?** 

Choose your preferred method above and start your Graviton migration journey! 🚀