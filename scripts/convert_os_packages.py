#!/usr/bin/env python3
"""
Convert OS package dumps to knowledge base format
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def convert_jsonl_to_kb(jsonl_file: Path, os_name: str) -> dict:
    """Convert JSONL package dump to knowledge base format"""
    
    packages = []
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    pkg = json.loads(line.strip())
                    # Debug: Print first few packages to see the data structure
                    if len(packages) < 3:
                        print(f"Debug - Package data: {pkg}", file=sys.stderr)
                    packages.append({
                        "name": pkg["name"],
                        "aliases": [],
                        "compatibility": {
                            "supported_versions": [
                                {
                                    "version_range": ">0.0.0",
                                    "status": "compatible",
                                    "notes": f"Available in {os_name} repository"
                                }
                            ],
                            "minimum_supported_version": None,
                            "recommended_version": pkg["version"]
                        },
                        "metadata": {
                            "package_type": "repository",
                            "os_native": True,
                            "architecture": pkg.get("arch", "unknown"),
                            "repository": pkg.get("repo", ""),
                            "description": pkg.get("description", "")
                        }
                    })
                except json.JSONDecodeError:
                    continue
    
    return {
        "$schema": "../schemas/knowledge_base_schema.json",
        "metadata": {
            "name": f"{os_name} Native Packages",
            "description": f"Available packages from {os_name} repositories on Graviton",
            "version": "1.0",
            "created_date": datetime.now().isoformat(),
            "source": "graviton_instance_dump"
        },
        "software_compatibility": packages
    }

def main():
    if len(sys.argv) != 3:
        print("Usage: python convert_os_packages.py <jsonl_file> <os_name>")
        sys.exit(1)
    
    jsonl_file = Path(sys.argv[1])
    os_name = sys.argv[2]
    
    if not jsonl_file.exists():
        print(f"File not found: {jsonl_file}")
        sys.exit(1)
    
    kb_data = convert_jsonl_to_kb(jsonl_file, os_name)
    
    output_file = jsonl_file.with_suffix('.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(kb_data, f, indent=2)
    
    print(f"Converted {len(kb_data['software_compatibility'])} packages")
    print(f"Output: {output_file}")

if __name__ == "__main__":
    main()