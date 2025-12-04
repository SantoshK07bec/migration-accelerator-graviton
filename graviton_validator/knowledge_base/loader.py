"""
Knowledge Base Loader

Provides a simple interface for loading knowledge base files.
"""

from typing import List, Optional
from .data_structures import JSONKnowledgeBase


class KnowledgeBaseLoader:
    """Simple loader for knowledge base files."""
    
    def __init__(self):
        self.knowledge_base = None
    
    def load_multiple(self, file_paths: List[str]) -> JSONKnowledgeBase:
        """
        Load multiple knowledge base files.
        
        Args:
            file_paths: List of paths to knowledge base files
            
        Returns:
            JSONKnowledgeBase instance with loaded data
        """
        self.knowledge_base = JSONKnowledgeBase()
        self.knowledge_base.load_from_files(file_paths)
        return self.knowledge_base
    
    def load_single(self, file_path: str) -> JSONKnowledgeBase:
        """
        Load a single knowledge base file.
        
        Args:
            file_path: Path to knowledge base file
            
        Returns:
            JSONKnowledgeBase instance with loaded data
        """
        return self.load_multiple([file_path])