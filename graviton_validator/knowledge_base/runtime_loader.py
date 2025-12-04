"""
Runtime Knowledge Base Loader

Loads runtime-specific knowledge bases for Python, NodeJS, and .NET analyzers.
"""

import json
import logging
import os
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class RuntimeKnowledgeBaseLoader:
    """Loader for runtime-specific knowledge bases."""
    
    def __init__(self):
        """Initialize the runtime knowledge base loader."""
        self.kb_dir = Path(__file__).parent
        
    def load_python_knowledge_base(self) -> Dict:
        """Load Python runtime knowledge base.
        
        Returns:
            Dictionary with Python package compatibility information
        """
        return self._load_knowledge_base('python_runtime_dependencies.json')
    
    def load_nodejs_knowledge_base(self) -> Dict:
        """Load NodeJS runtime knowledge base.
        
        Returns:
            Dictionary with NodeJS package compatibility information
        """
        return self._load_knowledge_base('nodejs_runtime_dependencies.json')
    
    def load_dotnet_knowledge_base(self) -> Dict:
        """Load .NET runtime knowledge base.
        
        Returns:
            Dictionary with .NET package compatibility information
        """
        return self._load_knowledge_base('dotnet_runtime_dependencies.json')
    
    def load_java_knowledge_base(self) -> Dict:
        """Load Java runtime knowledge base.
        
        Returns:
            Dictionary with Java package compatibility information
        """
        return self._load_knowledge_base('java_runtime_dependencies.json')
    
    def load_ruby_knowledge_base(self) -> Dict:
        """Load Ruby runtime knowledge base.
        
        Returns:
            Dictionary with Ruby gem compatibility information
        """
        return self._load_knowledge_base('ruby_runtime_dependencies.json')
    
    def _load_knowledge_base(self, filename: str) -> Dict:
        """Load knowledge base from JSON file.
        
        Args:
            filename: Name of the knowledge base file
            
        Returns:
            Dictionary with package compatibility information
        """
        kb_path = self.kb_dir / filename
        
        try:
            if kb_path.exists():
                with open(kb_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.debug(f"Loaded {len(data)} entries from {filename}")
                    return data
            else:
                logger.warning(f"Knowledge base file not found: {kb_path}")
                return {}
                
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load knowledge base {filename}: {e}")
            return {}
    
    def get_all_runtime_knowledge_bases(self) -> Dict[str, Dict]:
        """Load all runtime knowledge bases.
        
        Returns:
            Dictionary mapping runtime types to their knowledge bases
        """
        return {
            'python': self.load_python_knowledge_base(),
            'nodejs': self.load_nodejs_knowledge_base(),
            'dotnet': self.load_dotnet_knowledge_base(),
            'java': self.load_java_knowledge_base(),
            'ruby': self.load_ruby_knowledge_base()
        }