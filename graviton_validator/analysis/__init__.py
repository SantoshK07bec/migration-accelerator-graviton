"""
Analysis Module

Contains compatibility analysis engine and recommendation generation logic.
"""

from .base import CompatibilityAnalyzer, RecommendationGenerator
from .compatibility_analyzer import (
    GravitonCompatibilityAnalyzer,
    DefaultRecommendationGenerator,
    create_analyzer
)
# from .recommendation_system import (
#     AdvancedRecommendationGenerator,
#     RecommendationCategory,
#     UpgradePriority,
#     RecommendationAction,
#     UpgradeRecommendation,
#     categorize_component_compatibility,
#     create_recommendation_generator
# )

__all__ = [
    # Base classes
    'CompatibilityAnalyzer',
    'RecommendationGenerator',
    
    # Compatibility analyzer implementations
    'GravitonCompatibilityAnalyzer',
    'DefaultRecommendationGenerator',
    'create_analyzer',
    
    # Advanced recommendation system (commented out - module moved)
    # 'AdvancedRecommendationGenerator',
    # 'RecommendationCategory',
    # 'UpgradePriority',
    # 'RecommendationAction',
    # 'UpgradeRecommendation',
    # 'categorize_component_compatibility',
    # 'create_recommendation_generator',
]