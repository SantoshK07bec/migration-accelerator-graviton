import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

url = "https://www.arm.com/developer-hub/ecosystem-dashboard/"

try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find all table rows with package data
    package_rows = soup.find_all('tr', class_='c-table-row main-sw-row')
    
    # Fallback to broader selector if specific one doesn't work
    if len(package_rows) == 0:
        package_rows = soup.find_all('tr', class_='c-table-row')

    software_compatibility = []
    for row in package_rows:
        # Extract package name
        name_elem = row.find('span', class_='package-name')
        if not name_elem:
            continue
        name = name_elem.text.strip()
        
        # Extract supported since date
        date_elem = row.find('div', class_='date-supported')
        supported_since = None
        if date_elem:
            long_date = date_elem.find('span', class_='long-date')
            if long_date:
                supported_since = long_date.text.strip()
        
        # Extract version information from the expanded content
        version = None
        recommended_version = None
        next_row = row.find_next_sibling('tr')
        if next_row and next_row.get('hidden') is not None:
            # Look for version numbers in the expanded content
            version_spans = next_row.find_all('span', class_='version-number')
            if version_spans:
                # First version is usually the minimum supported
                first_version = version_spans[0].text.strip()
                version = re.sub(r'(?i)version\s*', '', first_version).strip()
                
                # Look for recommended version if there are multiple versions
                if len(version_spans) > 1:
                    rec_version = version_spans[1].text.strip()
                    recommended_version = re.sub(r'(?i)version\s*', '', rec_version).strip()
        
        # Extract license type
        license_type = "open-source"
        if 'tag-license-commercial' in row.get('class', []):
            license_type = "commercial"
        
        # Create knowledge base entry
        software_entry = {
            "name": name.lower(),
            "description": f"Software package from ARM ecosystem dashboard - {license_type} license",
            "compatibility": {
                "supported_versions": [
                    {
                        "version_range": f">={version}" if version else "",
                        "status": "compatible",
                        "notes": f"Listed on ARM ecosystem dashboard as Graviton compatible since {supported_since}" if supported_since else "Listed on ARM ecosystem dashboard as Graviton compatible"
                    }
                ],
                "minimum_supported_version": version,
                "recommended_version": recommended_version or version
            }
        }
        
        software_compatibility.append(software_entry)

    # Create knowledge base structure
    knowledge_base = {
        "$schema": "./knowledge_base_schema.json",
        "metadata": {
            "version": "1.0",
            "description": "ARM Ecosystem Dashboard packages compatible with Graviton",
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "maintainer": "ARM Ecosystem Dashboard Scraper",
            "notes": "Auto-generated from ARM ecosystem dashboard"
        },
        "software_compatibility": software_compatibility
    }
    
    json_file = '../knowledge_bases/arm_ecosystem_packages.json'
    with open(json_file, 'w', encoding='utf-8') as jsonfile:
        json.dump(knowledge_base, jsonfile, indent=2, ensure_ascii=False)

    print(f"Successfully scraped {len(software_compatibility)} entries and saved to {json_file}")
    print(f"Number of packages with missing versions: {sum(1 for item in software_compatibility if item['compatibility']['minimum_supported_version'] is None)}")

except requests.exceptions.RequestException as e:
    print(f"Error fetching the URL: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
