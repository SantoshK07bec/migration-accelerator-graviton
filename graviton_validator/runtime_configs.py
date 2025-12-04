#!/usr/bin/env python3
"""
Centralized Runtime Configuration

Single source of truth for all runtime configurations used by both:
1. Container execution environment (--containers mode)
2. CodeBuild project generation

This ensures consistency between local development and CI/CD environments.
"""

from typing import Dict, List, Any

# Default runtime versions - matches existing DEFAULT_VERSIONS in ContainerExecutionEnvironment
DEFAULT_RUNTIME_VERSIONS = {
    'python': '3.11',
    'nodejs': '20',
    'dotnet': '8.0', 
    'ruby': '3.2',
    'java': '17'
}

# Script mappings - matches existing SCRIPT_MAP in execution environments
RUNTIME_SCRIPT_MAP = {
    'python': 'python_package_installer.py',
    'nodejs': 'nodejs_package_installer.py',
    'java': 'java_package_installer.py',
    'dotnet': 'dotnet_package_installer.py',
    'ruby': 'ruby_package_installer.py'
}

# Runtime execution configurations - matches existing RUNTIME_CONFIGS in NativeExecutionEnvironment
RUNTIME_EXECUTION_CONFIGS = {
    'python': {'timeout': 300, 'default_version': '3.11', 'env_var': 'DEBUG'},
    'nodejs': {'timeout': 300, 'default_version': '20', 'env_var': 'NODE_LOG_LEVEL'},
    'dotnet': {'timeout': 120, 'default_version': '8.0', 'env_var': 'DEBUG'},
    'ruby': {'timeout': 300, 'default_version': '3.2', 'env_var': 'DEBUG'},
    'java': {'timeout': 300, 'default_version': '17', 'env_var': 'DEBUG', 'success_codes': [0, 2]}
}

# Container image configurations - extracted from existing _generate_dockerfile logic
CONTAINER_RUNTIME_CONFIGS = {
    'python': {
        'base_images': {
            'amazon-linux': 'amazonlinux:2023',
            'amazon': 'amazonlinux:2023',
            'ubuntu': 'ubuntu:latest',
            'debian': 'debian:latest',
            'centos': 'centos:latest',
            'rhel': 'centos:latest',
            'fedora': 'fedora:latest'
        },
        'package_managers': {
            'rpm': {
                'update': 'yum update -y',
                'install': 'yum install -y',
                'packages': ['python3', 'python3-pip', 'gcc', 'gcc-c++', 'python3-devel', 'make']
            },
            'deb': {
                'update': 'apt-get update',
                'install': 'apt-get install -y',
                'packages': ['python3', 'python3-pip', 'gcc', 'g++', 'python3-dev', 'build-essential']
            }
        },
        'pip_packages': ['openpyxl', 'PyYAML', 'defusedxml', 'packaging', 'psutil', "'urllib3<2.0'"],
        'workdir': '/workspace'
    },
    
    'nodejs': {
        'base_image': 'node:{version}-alpine',
        'default_base': 'node:20-alpine',
        'package_manager': 'apk',
        'update_cmd': 'apk update',
        'install_cmd': 'apk add --no-cache',
        'packages': ['gcc', 'g++', 'make', 'musl-dev', 'python3-dev', 'python3', 'py3-pip', 'linux-headers', 'libffi-dev', 'openssl-dev', 'curl'],
        'pip_packages': ['PyYAML', 'defusedxml', 'packaging', 'psutil', 'openpyxl', "'urllib3<2.0'"],
        'pip_install_flags': '--break-system-packages',
        'workdir': '/workspace'
    },
    
    'dotnet': {
        'base_image': 'mcr.microsoft.com/dotnet/sdk:{version}',
        'default_base': 'mcr.microsoft.com/dotnet/sdk:8.0',
        'package_manager': 'apt',
        'update_cmd': 'apt-get update',
        'install_cmd': 'apt-get install -y',
        'packages': ['python3', 'python3-pip'],
        'pip_packages': ['PyYAML', 'defusedxml', 'packaging', 'psutil', 'openpyxl', "'urllib3<2.0'"],
        'pip_install_flags': '--break-system-packages',
        'environment_vars': {
            'DOTNET_CLI_TELEMETRY_OPTOUT': '1',
            'DOTNET_SKIP_FIRST_TIME_EXPERIENCE': '1'
        },
        'workdir': '/workspace'
    },
    
    'ruby': {
        'base_image': 'ruby:{version}-alpine',
        'default_base': 'ruby:3.2-alpine',
        'package_manager': 'apk',
        'update_cmd': 'apk update',
        'install_cmd': 'apk add --no-cache',
        'packages': ['gcc', 'g++', 'make', 'musl-dev', 'python3-dev', 'python3', 'py3-pip', 'linux-headers', 'libffi-dev', 'openssl-dev', 'curl'],
        'gem_packages': ['bundler'],
        'pip_packages': ['PyYAML', 'defusedxml', 'packaging', 'psutil', 'openpyxl', "'urllib3<2.0'"],
        'pip_install_flags': '--break-system-packages',
        'workdir': '/workspace'
    },
    
    'java': {
        'base_images': {
            'amazon-linux': 'amazonlinux:2023',
            'amazon': 'amazonlinux:2023',
            'ubuntu': 'ubuntu:latest',
            'debian': 'debian:latest',
            'centos': 'centos:latest',
            'rhel': 'centos:latest',
            'fedora': 'fedora:latest'
        },
        'package_managers': {
            'rpm': {
                'update': 'yum update -y',
                'install': 'yum install -y',
                'packages': ['java-{version}-amazon-corretto-devel', 'maven', 'python3', 'python3-pip']
            },
            'deb': {
                'update': 'apt-get update',
                'install': 'apt-get install -y',
                'packages': ['openjdk-{version}-jdk', 'maven', 'python3', 'python3-pip']
            }
        },
        'pip_packages': ['PyYAML', 'defusedxml', 'packaging', 'psutil', 'openpyxl', "'requests<2.29'", "'urllib3<2.0'"],
        'workdir': '/workspace'
    }
}

# OS to package manager mapping - extracted from existing _get_package_commands logic
OS_PACKAGE_MANAGER_MAP = {
    'ubuntu': 'deb',
    'debian': 'deb',
    'amazon-linux': 'rpm',
    'amazon': 'rpm',
    'centos': 'rpm',
    'rhel': 'rpm',
    'fedora': 'rpm'
}

def get_runtime_default_version(runtime: str) -> str:
    """Get default version for a runtime."""
    return DEFAULT_RUNTIME_VERSIONS.get(runtime, 'latest')

def get_runtime_script_name(runtime: str) -> str:
    """Get script name for a runtime."""
    return RUNTIME_SCRIPT_MAP.get(runtime, f'{runtime}_package_installer.py')

def get_runtime_execution_config(runtime: str) -> Dict[str, Any]:
    """Get execution configuration for a runtime."""
    return RUNTIME_EXECUTION_CONFIGS.get(runtime, {})

def get_container_config(runtime: str) -> Dict[str, Any]:
    """Get container configuration for a runtime."""
    return CONTAINER_RUNTIME_CONFIGS.get(runtime, {})

def get_base_image(runtime: str, os_name: str = 'amazon-linux', runtime_version: str = None) -> str:
    """Get base image for runtime and OS combination."""
    config = get_container_config(runtime)
    
    if not config:
        return 'amazonlinux:2023'  # fallback
    
    # Handle runtimes with single base image (nodejs, dotnet, ruby)
    if 'base_image' in config:
        if runtime_version and '{version}' in config['base_image']:
            return config['base_image'].format(version=runtime_version)
        return config.get('default_base', config['base_image'])
    
    # Handle runtimes with OS-specific base images (python, java)
    if 'base_images' in config:
        return config['base_images'].get(os_name, config['base_images'].get('amazon-linux', 'amazonlinux:2023'))
    
    return 'amazonlinux:2023'  # fallback

def get_package_manager_info(runtime: str, os_name: str) -> Dict[str, Any]:
    """Get package manager information for runtime and OS."""
    config = get_container_config(runtime)
    
    if not config:
        return {}
    
    # Handle runtimes with single package manager (nodejs, dotnet, ruby)
    if 'package_manager' in config:
        return {
            'type': config['package_manager'],
            'update': config.get('update_cmd', ''),
            'install': config.get('install_cmd', ''),
            'packages': config.get('packages', [])
        }
    
    # Handle runtimes with OS-specific package managers (python, java)
    if 'package_managers' in config:
        pm_type = OS_PACKAGE_MANAGER_MAP.get(os_name, 'deb')
        pm_config = config['package_managers'].get(pm_type, {})
        return {
            'type': pm_type,
            'update': pm_config.get('update', ''),
            'install': pm_config.get('install', ''),
            'packages': pm_config.get('packages', [])
        }
    
    return {}