#!/bin/bash
# Generate knowledge bases for all supported OS versions
# Usage: ./generate_all_os_kb.sh

set -e

# Define OS and versions to process
declare -a OS_LIST=(
    "amazonlinux 2"
    "amazonlinux 2023"
    "ubuntu 18.04"
    "ubuntu 20.04"
    "ubuntu 22.04"
    "ubuntu 24.04"
    "centos 8"
    "alpine 3.17"
    "alpine 3.18"
    "debian 10"
    "debian 11"
    "debian 12"
)

echo "Generating knowledge bases for ${#OS_LIST[@]} OS versions..."

# Process each OS
for os_version in "${OS_LIST[@]}"; do
    read -r os version <<< "$os_version"
    echo "Processing: $os $version"
    
    if ./generate_docker_kb.sh "$os" "$version"; then
        echo "✅ Success: $os $version"
    else
        echo "❌ Failed: $os $version"
    fi
    echo ""
done

echo "Generated files:"
ls -la os_packages/*.json 2>/dev/null || echo "No files generated"