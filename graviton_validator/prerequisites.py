#!/usr/bin/env python3
"""
Prerequisites checker for graviton-validator flags.
"""

import subprocess
import sys
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class PrerequisiteChecker:
    """Check prerequisites for different graviton-validator flags."""
    
    # Prerequisites mapping for each flag/mode
    PREREQUISITES = {
        'runtime_analysis_native': {
            'python': ['python3', 'pip3'],
            'nodejs': ['node', 'npm'], 
            'dotnet': ['dotnet'],
            'ruby': ['ruby', 'gem', 'bundle'],
            'java': ['java', 'mvn']
        },
        'runtime_analysis_container': ['docker', 'podman'],  # Either Docker or Podman
        'jar_enhancement': ['java'],
        'excel_output': [],  # No external prerequisites
        'markdown_output': [],  # No external prerequisites
    }
    
    def check_all_prerequisites(self, args) -> Tuple[bool, List[str]]:
        """Check all prerequisites based on provided arguments."""
        missing_tools = []
        
        # Check runtime analysis prerequisites
        if args.runtime_analysis:
            use_containers = getattr(args, 'use_containers', None)
            if use_containers is None:
                import os
                use_containers = os.environ.get('CODEBUILD_BUILD_ID') is None
            
            if use_containers:
                # Container mode - need Docker or Podman
                container_tool = self._detect_container_tool()
                if not container_tool:
                    missing_tools.append('docker or podman')
                    logger.error("Container mode requires Docker or Podman")
                else:
                    logger.info(f"Using container tool: {container_tool}")
            else:
                # Native mode - need runtime tools (will check detected runtimes later)
                logger.info("Native mode - runtime tools will be validated per detected runtime")
        
        # Check JAR enhancement prerequisites
        if getattr(args, 'jar_files', None) or getattr(args, 'jar_directory', None):
            if not self._check_tool('java'):
                missing_tools.append('java')
                logger.error("JAR enhancement requires Java")
        
        # Check output format prerequisites (none currently)
        
        return len(missing_tools) == 0, missing_tools
    
    def check_runtime_prerequisites(self, runtimes: List[str], use_containers: bool) -> Tuple[bool, Dict[str, List[str]]]:
        """Check prerequisites for specific runtimes."""
        if use_containers:
            # Container mode needs Docker or Podman
            container_tool = self._detect_container_tool()
            if not container_tool:
                return False, {'container': ['docker or podman']}
            return True, {}
        
        # Native mode - check each runtime
        missing_by_runtime = {}
        for runtime in runtimes:
            if runtime in self.PREREQUISITES['runtime_analysis_native']:
                required_tools = self.PREREQUISITES['runtime_analysis_native'][runtime]
                missing_tools = []
                
                for tool in required_tools:
                    if not self._check_tool(tool):
                        missing_tools.append(tool)
                
                if missing_tools:
                    missing_by_runtime[runtime] = missing_tools
        
        return len(missing_by_runtime) == 0, missing_by_runtime
    
    def _detect_container_tool(self) -> str:
        """Detect available container tool (Docker or Podman)."""
        for tool in ['docker', 'podman']:
            if self._check_tool(tool):
                return tool
        return None
    
    def _check_tool(self, tool: str) -> bool:
        """Check if a tool is available."""
        try:
            subprocess.run([tool, '--version'], 
                         capture_output=True, check=True, timeout=10)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def get_container_tool(self) -> str:
        """Get the available container tool."""
        return self._detect_container_tool() or 'docker'
    
    def get_installation_instructions(self, missing_tools: List[str]) -> str:
        """Get installation instructions for missing tools."""
        instructions = {
            'docker or podman': 'Install Docker Desktop (https://www.docker.com/products/docker-desktop) or Podman (https://podman.io/getting-started/installation)',
            'docker': 'Install Docker Desktop from https://www.docker.com/products/docker-desktop',
            'podman': 'Install Podman from https://podman.io/getting-started/installation',
            'python3': 'Install Python 3: brew install python3 (macOS) or apt-get install python3 (Ubuntu)',
            'pip3': 'Install pip3: python3 -m ensurepip --upgrade',
            'node': 'Install Node.js from https://nodejs.org/ or brew install node',
            'npm': 'Install npm: comes with Node.js or npm install -g npm',
            'dotnet': 'Install .NET SDK from https://dotnet.microsoft.com/download',
            'ruby': 'Install Ruby: brew install ruby (macOS) or apt-get install ruby (Ubuntu)',
            'gem': 'Install RubyGems: comes with Ruby or gem update --system',
            'bundle': 'Install Bundler: gem install bundler',
            'java': 'Install Java: brew install openjdk (macOS) or apt-get install openjdk-11-jdk',
            'mvn': 'Install Maven: brew install maven (macOS) or apt-get install maven'
        }
        
        result = "Missing prerequisites installation instructions:\n"
        for tool in missing_tools:
            if tool in instructions:
                result += f"  {tool}: {instructions[tool]}\n"
            else:
                result += f"  {tool}: Please install {tool}\n"
        
        return result