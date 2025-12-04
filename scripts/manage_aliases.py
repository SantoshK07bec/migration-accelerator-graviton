#!/usr/bin/env python3
"""
Script to manage persistent SBOM component name aliases.
"""

import json
import os
import sys
from pathlib import Path

def get_aliases_file():
    """Get path to common_aliases.json file."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    return project_root / "knowledge_bases" / "os_knowledge_bases" / "common_aliases.json"

def load_aliases():
    """Load existing aliases."""
    aliases_file = get_aliases_file()
    if aliases_file.exists():
        with open(aliases_file, 'r') as f:
            return json.load(f)
    return {"metadata": {"name": "Common SBOM Name Aliases", "version": "1.0"}, "aliases": {}}

def save_aliases(data):
    """Save aliases to file."""
    aliases_file = get_aliases_file()
    with open(aliases_file, 'w') as f:
        json.dump(data, f, indent=2)

def add_alias(sbom_name, target_name):
    """Add a new alias mapping."""
    data = load_aliases()
    data["aliases"][sbom_name] = target_name
    save_aliases(data)
    print(f"✅ Added alias: {sbom_name} → {target_name}")

def remove_alias(sbom_name):
    """Remove an alias mapping."""
    data = load_aliases()
    if sbom_name in data["aliases"]:
        del data["aliases"][sbom_name]
        save_aliases(data)
        print(f"✅ Removed alias: {sbom_name}")
    else:
        print(f"❌ Alias not found: {sbom_name}")

def list_aliases():
    """List all current aliases."""
    data = load_aliases()
    aliases = data.get("aliases", {})
    
    if not aliases:
        print("No aliases defined.")
        return
    
    print(f"Current aliases ({len(aliases)}):")
    for sbom_name, target_name in sorted(aliases.items()):
        print(f"  {sbom_name} → {target_name}")

def show_help():
    """Display help information."""
    print("Graviton Validator - Alias Management Tool")
    print("==========================================")
    print()
    print("USAGE:")
    print("  python manage_aliases.py <command> [arguments]")
    print()
    print("COMMANDS:")
    print("  list                     List all current aliases")
    print("  add <sbom_name> <target> Add new alias mapping")
    print("  remove <sbom_name>       Remove existing alias")
    print("  help                     Show this help message")
    print()
    print("EXAMPLES:")
    print("  python manage_aliases.py list")
    print("  python manage_aliases.py add redis-server redis6")
    print("  python manage_aliases.py add chronyd chrony")
    print("  python manage_aliases.py remove old-alias")
    print()
    print("DESCRIPTION:")
    print("  Manages persistent aliases for SBOM component names that don't")
    print("  exactly match OS knowledge base package names. These aliases")
    print("  survive OS knowledge base regeneration.")
    print()
    print("  - sbom_name: Component name as it appears in SBOM files")
    print("  - target:    Actual package name in OS knowledge base")

def main():
    if len(sys.argv) < 2:
        show_help()
        return 1
    
    command = sys.argv[1]
    
    if command == "help" or command == "-h" or command == "--help":
        show_help()
    elif command == "list":
        list_aliases()
    elif command == "add" and len(sys.argv) == 4:
        add_alias(sys.argv[2], sys.argv[3])
    elif command == "remove" and len(sys.argv) == 3:
        remove_alias(sys.argv[2])
    else:
        print("❌ Invalid command or arguments")
        print()
        show_help()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())