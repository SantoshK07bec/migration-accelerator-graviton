#!/bin/bash
# Script to dump OS packages from Graviton instances
# Run this on each Graviton-compatible OS to generate package databases

set -e

OS_NAME=""
OUTPUT_DIR="./os_packages"
ARCH=$(uname -m)

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    case "$ID" in
        "amzn")
            OS_NAME="amazon-linux-${VERSION_ID}"
            ;;
        "ubuntu")
            OS_NAME="ubuntu-${VERSION_ID}"
            ;;
        "rhel"|"centos"|"almalinux"|"rocky")
            OS_NAME="${ID}-${VERSION_ID}"
            ;;
        *)
            OS_NAME="${ID}-${VERSION_ID}"
            ;;
    esac
else
    echo "Cannot detect OS"
    exit 1
fi

echo "Detected OS: $OS_NAME on $ARCH"
mkdir -p "$OUTPUT_DIR"

# RPM-based systems (YUM/DNF)
if command -v yum >/dev/null 2>&1; then
    echo "Refreshing YUM metadata..."
    yum makecache --quiet
    echo "Dumping available YUM packages..."
    # Use yum with better formatting to avoid multi-line issues
    yum list available --quiet | tr -s ' ' | awk '
    BEGIN { pkg=""; ver=""; repo="" }
    /^[a-zA-Z0-9]/ && NF>=3 {
        n=split($1,a,"."); arch=a[n]; gsub(/\.[^.]*$/,"",$1)
        print "{\"name\":\""$1"\",\"version\":\""$2"\",\"arch\":\""arch"\",\"repo\":\""$3"\"}"
        next
    }
    /^[a-zA-Z0-9]/ && NF==1 { pkg=$1; getline; ver=$1; getline; repo=$1
        if(pkg && ver && repo) {
            n=split(pkg,a,"."); arch=a[n]; gsub(/\.[^.]*$/,"",pkg)
            print "{\"name\":\""pkg"\",\"version\":\""ver"\",\"arch\":\""arch"\",\"repo\":\""repo"\"}"
        }
        pkg=""; ver=""; repo=""
    }' > "$OUTPUT_DIR/${OS_NAME}-yum-available.jsonl"
elif command -v dnf >/dev/null 2>&1; then
    echo "Refreshing DNF metadata..."
    dnf makecache --quiet
    echo "Dumping available DNF packages..."
    # Use dnf with better formatting to avoid multi-line issues
    dnf list available --quiet | tr -s ' ' | awk '
    BEGIN { pkg=""; ver=""; repo="" }
    /^[a-zA-Z0-9]/ && NF>=3 {
        n=split($1,a,"."); arch=a[n]; gsub(/\.[^.]*$/,"",$1)
        print "{\"name\":\""$1"\",\"version\":\""$2"\",\"arch\":\""arch"\",\"repo\":\""$3"\"}"
        next
    }
    /^[a-zA-Z0-9]/ && NF==1 { pkg=$1; getline; ver=$1; getline; repo=$1
        if(pkg && ver && repo) {
            n=split(pkg,a,"."); arch=a[n]; gsub(/\.[^.]*$/,"",pkg)
            print "{\"name\":\""pkg"\",\"version\":\""ver"\",\"arch\":\""arch"\",\"repo\":\""repo"\"}"
        }
        pkg=""; ver=""; repo=""
    }' > "$OUTPUT_DIR/${OS_NAME}-dnf-available.jsonl"
fi

# DEB-based systems (APT)
if command -v apt-cache >/dev/null 2>&1; then
    echo "Refreshing APT metadata..."
    apt-get update -qq
    echo "Dumping available APT packages..."
    apt-cache dumpavail | awk '/^Package:/ {name=$2} /^Version:/ {version=$2} /^Architecture:/ {arch=$2} /^Description:/ {desc=$0; gsub(/^Description: /, "", desc)} /^$/ && name {print "{\"name\":\""name"\",\"version\":\""version"\",\"arch\":\""arch"\",\"description\":\""desc"\"}"; name=""}' > "$OUTPUT_DIR/${OS_NAME}-apt-available.jsonl"
fi

# APK-based systems (Alpine)
if command -v apk >/dev/null 2>&1; then
    echo "Refreshing APK metadata..."
    apk update
    echo "Dumping available APK packages..."
    apk search -v | awk '{split($1,a,"-"); name=a[1]; for(i=2;i<length(a)-1;i++) name=name"-"a[i]; version=a[length(a)]; print "{\"name\":\""name"\",\"version\":\""version"\",\"arch\":\"'$ARCH'\"}"}' > "$OUTPUT_DIR/${OS_NAME}-apk-available.jsonl"
fi

echo "Package dump completed: $OUTPUT_DIR/${OS_NAME}-*-available.jsonl"
echo "Architecture: $ARCH"
echo "Kernel: $(uname -r)"