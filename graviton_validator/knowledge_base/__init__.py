"""
Knowledge Base Module

Contains knowledge base loading, compatibility checking, and version comparison logic.
"""

from .loader import KnowledgeBaseLoader
from .data_structures import JSONKnowledgeBase

__all__ = ['KnowledgeBaseLoader', 'JSONKnowledgeBase']