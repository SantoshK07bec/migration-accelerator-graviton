import re
import json
import requests
from datetime import datetime

"""
Scrapes isv.md file from Graviton Getting Started Guide
https://github.com/aws/aws-graviton-getting-started/blob/main/isv.md
"""

def parse_isv_markdown():
    """Parse ISV markdown file and convert to knowledge base format"""
    
    try:
        # Fetch the ISV markdown file from GitHub
        url = "https://raw.githubusercontent.com/aws/aws-graviton-getting-started/refs/heads/main/isv.md"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        content = response.text
        
        # Find the table section
        table_match = re.search(r'\| Category \| ISV \| Product \| Resources \|(.*?)(?=\n\n|\Z)', content, re.DOTALL)
        if not table_match:
            print("No table found in markdown file")
            return
        
        table_content = table_match.group(1)
        
        # Parse table rows
        rows = []
        for line in table_content.strip().split('\n'):
            line = line.strip()
            if line.startswith('|') and '---' not in line:
                # Split by | and clean up
                parts = [part.strip() for part in line.split('|')[1:-1]]  # Remove empty first/last
                if len(parts) >= 4:
                    rows.append(parts)
        
        software_compatibility = []
        
        for row in rows:
            category, isv, product, resources = row[0], row[1], row[2], row[3]
            
            # Clean up ISV name (remove markdown links)
            isv_clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', isv)
            
            # Clean up product name (remove markdown links)
            product_clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', product)
            
            # Extract URLs from resources
            urls = re.findall(r'https?://[^\s<>,]+', resources)
            
            # Create knowledge base entry
            software_entry = {
                "name": product_clean.lower(),
                "aliases": [isv_clean.lower()] if isv_clean.lower() != product_clean.lower() else [],
                "description": f"{product_clean} by {isv_clean} - ISV product with Graviton support",
                "compatibility": {
                    "supported_versions": [
                        {
                            "version_range": "",
                            "status": "compatible",
                            "notes": f"ISV product in {category} category with official Graviton support"
                        }
                    ],
                    "minimum_supported_version": None,
                    "recommended_version": None,
                    "documentation_links": urls[:3] if urls else []  # Limit to first 3 URLs
                }
            }
            
            software_compatibility.append(software_entry)
        
        # Create knowledge base structure
        knowledge_base = {
            "$schema": "./knowledge_base_schema.json",
            "metadata": {
                "version": "1.0",
                "description": "ISV products with official Graviton support",
                "created_date": datetime.now().strftime("%Y-%m-%d"),
                "maintainer": "ISV Markdown Scraper",
                "notes": "Auto-generated from ISV markdown file"
            },
            "software_compatibility": software_compatibility
        }
        
        # Save to JSON file
        json_file = '../knowledge_bases/isv_graviton_packages.json'
        with open(json_file, 'w', encoding='utf-8') as jsonfile:
            json.dump(knowledge_base, jsonfile, indent=2, ensure_ascii=False)
        
        print(f"Successfully parsed {len(software_compatibility)} ISV entries and saved to {json_file}")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    parse_isv_markdown()