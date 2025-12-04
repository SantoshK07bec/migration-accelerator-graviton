"""
Intelligent matching system for fuzzy software name matching.
"""

import re
import logging
from typing import List, Optional, Tuple, Dict

from .base import IntelligentMatcher

logger = logging.getLogger(__name__)


class FuzzyMatcher(IntelligentMatcher):
    """Fuzzy matcher using multiple similarity algorithms."""
    
    def __init__(self, 
                 similarity_threshold: float = 0.7,
                 enable_fuzzy_matching: bool = True,
                 enable_alias_matching: bool = True,
                 custom_aliases: Optional[Dict[str, str]] = None,
                 matching_strategies: Optional[List[str]] = None,
                 strategy_weights: Optional[Dict[str, float]] = None,
                 enable_substring_matching: bool = True,
                 enable_normalized_matching: bool = True,
                 max_matches: int = 5,
                 min_confidence_threshold: float = 0.5):
        """
        Initialize the fuzzy matcher.
        
        Args:
            similarity_threshold: Minimum similarity score for matches
            enable_fuzzy_matching: Whether to enable fuzzy string matching
            enable_alias_matching: Whether to enable alias-based matching
            custom_aliases: Additional custom aliases to use
            matching_strategies: List of enabled matching strategies
            strategy_weights: Weights for different similarity algorithms
            enable_substring_matching: Whether to enable substring matching
            enable_normalized_matching: Whether to enable normalized matching
            max_matches: Maximum number of matches to return
            min_confidence_threshold: Minimum confidence threshold for matches
        """
        # Validate parameters
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("Similarity threshold must be between 0.0 and 1.0")
        if not 0.0 <= min_confidence_threshold <= 1.0:
            raise ValueError("Min confidence threshold must be between 0.0 and 1.0")
        if max_matches < 1:
            raise ValueError("Max matches must be at least 1")
            
        self.similarity_threshold = similarity_threshold
        self.enable_fuzzy_matching = enable_fuzzy_matching
        self.enable_alias_matching = enable_alias_matching
        self.enable_substring_matching = enable_substring_matching
        self.enable_normalized_matching = enable_normalized_matching
        self.max_matches = max_matches
        self.min_confidence_threshold = min_confidence_threshold
        
        # Set up matching strategies
        self.matching_strategies = matching_strategies or ['fuzzy', 'alias', 'substring']
        
        # Set up strategy weights
        self.strategy_weights = strategy_weights or {
            'levenshtein': 0.3,
            'jaro_winkler': 0.3,
            'substring': 0.2,
            'normalized': 0.2
        }
        
        # Common software aliases and variations
        self.common_aliases = {
            'httpd': 'apache',
            'apache2': 'apache',
            'apache-httpd': 'apache',
            'nodejs': 'node',
            'node.js': 'node',
            'python3': 'python',
            'python2': 'python',
            'py': 'python',
            'java-jdk': 'java',
            'openjdk': 'java',
            'oracle-java': 'java',
            'mysql-server': 'mysql',
            'mariadb': 'mysql',
            'postgresql': 'postgres',
            'postgres-server': 'postgres',
            'nginx-server': 'nginx',
            'redis-server': 'redis',
            'mongodb': 'mongo',
            'mongo-db': 'mongo',
        }
        
        # Add custom aliases if provided
        if custom_aliases:
            self.common_aliases.update(custom_aliases)
        
        # Patterns for normalizing package names
        self.normalization_patterns = [
            (r'-dev$', ''),           # Remove -dev suffix
            (r'-devel$', ''),         # Remove -devel suffix
            (r'-server$', ''),        # Remove -server suffix
            (r'-client$', ''),        # Remove -client suffix
            (r'-common$', ''),        # Remove -common suffix
            (r'-core$', ''),          # Remove -core suffix
            (r'-base$', ''),          # Remove -base suffix
            (r'^lib', ''),            # Remove lib prefix
            (r'[_-]', ''),            # Remove underscores and hyphens
        ]
    
    def normalize_name(self, name: str) -> str:
        """
        Normalize a software name for better matching.
        
        Args:
            name: Software name to normalize
            
        Returns:
            Normalized name
        """
        normalized = name.lower().strip()
        
        # Apply normalization patterns
        for pattern, replacement in self.normalization_patterns:
            normalized = re.sub(pattern, replacement, normalized)
        
        return normalized
    
    def find_best_match(self, query: str, candidates: List[str]) -> Optional[str]:
        """
        Find the best match for a query string from a list of candidates.
        
        Args:
            query: String to match
            candidates: List of candidate strings
            
        Returns:
            Best matching candidate or None if no good match found
        """
        if not query or not candidates:
            return None
        
        # Check for exact match first
        query_lower = query.lower()
        for candidate in candidates:
            if candidate.lower() == query_lower:
                return candidate
        
        # Check for alias match if enabled
        if self.enable_alias_matching:
            normalized_query = self.normalize_name(query)
            query_lower = query.lower()
            
            # Check both normalized and original query in aliases
            if normalized_query in self.common_aliases:
                canonical_name = self.common_aliases[normalized_query]
                for candidate in candidates:
                    if self.normalize_name(candidate) == canonical_name or candidate.lower() == canonical_name.lower():
                        return candidate
            
            if query_lower in self.common_aliases:
                canonical_name = self.common_aliases[query_lower]
                for candidate in candidates:
                    if self.normalize_name(candidate) == canonical_name or candidate.lower() == canonical_name.lower():
                        return candidate
        
        # Find best fuzzy match if enabled
        if self.enable_fuzzy_matching:
            best_match = None
            best_score = 0.0
            
            for candidate in candidates:
                score = self.calculate_similarity(query, candidate)
                if score > best_score and score >= self.similarity_threshold:
                    best_score = score
                    best_match = candidate
            
            if best_match:
                logger.debug(f"Fuzzy match: '{query}' -> '{best_match}' (score: {best_score:.3f})")
            
            return best_match
        
        return None
    
    def calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity score between two strings using multiple algorithms.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not str1 or not str2:
            return 0.0
        
        # Normalize strings
        s1 = str1.lower().strip()
        s2 = str2.lower().strip()
        
        # Exact match
        if s1 == s2:
            return 1.0
        
        # Calculate different similarity scores based on enabled strategies
        scores = {}
        
        # Calculate substring matches if enabled
        if self.enable_substring_matching and 'substring' in self.strategy_weights:
            scores['substring'] = self._calculate_substring_score(s1, s2)
        
        # Calculate Levenshtein similarity
        if 'levenshtein' in self.strategy_weights:
            scores['levenshtein'] = self._levenshtein_similarity(s1, s2)
        
        # Calculate Jaro-Winkler similarity
        if 'jaro_winkler' in self.strategy_weights:
            scores['jaro_winkler'] = self._jaro_winkler_similarity(s1, s2)
        
        # Calculate normalized similarity if enabled
        if self.enable_normalized_matching and 'normalized' in self.strategy_weights:
            normalized_s1 = self.normalize_name(s1)
            normalized_s2 = self.normalize_name(s2)
            scores['normalized'] = self._levenshtein_similarity(normalized_s1, normalized_s2)
        
        # Weighted combination of scores using configured weights
        final_score = 0.0
        total_weight = 0.0
        
        for strategy, score in scores.items():
            if strategy in self.strategy_weights:
                weight = self.strategy_weights[strategy]
                final_score += score * weight
                total_weight += weight
        
        # Normalize by total weight to ensure score is between 0 and 1
        if total_weight > 0:
            final_score = final_score / total_weight
        else:
            # Fallback to simple average if no weights match
            if scores:
                final_score = sum(scores.values()) / len(scores)
        
        return min(final_score, 1.0)
    
    def _calculate_substring_score(self, s1: str, s2: str) -> float:
        """Calculate score based on substring matches."""
        if s1 in s2 or s2 in s1:
            shorter = min(len(s1), len(s2))
            longer = max(len(s1), len(s2))
            return shorter / longer
        return 0.0
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _levenshtein_similarity(self, s1: str, s2: str) -> float:
        """Calculate Levenshtein similarity (1 - normalized distance)."""
        distance = self._levenshtein_distance(s1, s2)
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 1.0
        return 1.0 - (distance / max_len)
    
    def _jaro_similarity(self, s1: str, s2: str) -> float:
        """Calculate Jaro similarity."""
        if s1 == s2:
            return 1.0
        
        len1, len2 = len(s1), len(s2)
        if len1 == 0 or len2 == 0:
            return 0.0
        
        # Calculate the match window
        match_window = max(len1, len2) // 2 - 1
        match_window = max(0, match_window)
        
        s1_matches = [False] * len1
        s2_matches = [False] * len2
        
        matches = 0
        transpositions = 0
        
        # Find matches
        for i in range(len1):
            start = max(0, i - match_window)
            end = min(i + match_window + 1, len2)
            
            for j in range(start, end):
                if s2_matches[j] or s1[i] != s2[j]:
                    continue
                s1_matches[i] = s2_matches[j] = True
                matches += 1
                break
        
        if matches == 0:
            return 0.0
        
        # Count transpositions
        k = 0
        for i in range(len1):
            if not s1_matches[i]:
                continue
            while not s2_matches[k]:
                k += 1
            if s1[i] != s2[k]:
                transpositions += 1
            k += 1
        
        jaro = (matches / len1 + matches / len2 + (matches - transpositions / 2) / matches) / 3
        return jaro
    
    def _jaro_winkler_similarity(self, s1: str, s2: str) -> float:
        """Calculate Jaro-Winkler similarity."""
        jaro = self._jaro_similarity(s1, s2)
        
        if jaro < 0.7:
            return jaro
        
        # Calculate common prefix length (up to 4 characters)
        prefix_len = 0
        for i in range(min(len(s1), len(s2), 4)):
            if s1[i] == s2[i]:
                prefix_len += 1
            else:
                break
        
        return jaro + (0.1 * prefix_len * (1 - jaro))
    
    def get_match_confidence(self, similarity_score: float) -> str:
        """
        Get confidence level based on similarity score.
        
        Args:
            similarity_score: Similarity score between 0.0 and 1.0
            
        Returns:
            Confidence level string
        """
        if similarity_score >= 0.9:
            return "high"
        elif similarity_score >= 0.7:
            return "medium"
        elif similarity_score >= 0.5:
            return "low"
        else:
            return "very_low"
    
    def find_multiple_matches(self, query: str, candidates: List[str], max_matches: Optional[int] = None) -> List[Tuple[str, float]]:
        """
        Find multiple potential matches with their similarity scores.
        
        Args:
            query: String to match
            candidates: List of candidate strings
            max_matches: Maximum number of matches to return (uses configured default if None)
            
        Returns:
            List of (candidate, similarity_score) tuples, sorted by score
        """
        if max_matches is None:
            max_matches = self.max_matches
            
        matches = []
        
        for candidate in candidates:
            score = self.calculate_similarity(query, candidate)
            if score >= self.similarity_threshold:
                matches.append((candidate, score))
        
        # Sort by similarity score (descending)
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return matches[:max_matches]
    
    def add_custom_aliases(self, aliases: Dict[str, str]) -> None:
        """
        Add custom aliases to the matcher.
        
        Args:
            aliases: Dictionary of alias -> canonical name mappings
        """
        self.common_aliases.update(aliases)
        logger.debug(f"Added {len(aliases)} custom aliases")
    
    def set_similarity_threshold(self, threshold: float) -> None:
        """
        Set the similarity threshold for matching.
        
        Args:
            threshold: New similarity threshold (0.0 to 1.0)
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Similarity threshold must be between 0.0 and 1.0")
        
        self.similarity_threshold = threshold
        logger.debug(f"Set similarity threshold to {threshold}")
    
    def enable_matching_strategy(self, strategy: str, enabled: bool) -> None:
        """
        Enable or disable a specific matching strategy.
        
        Args:
            strategy: Strategy name ('fuzzy' or 'alias')
            enabled: Whether to enable the strategy
        """
        if strategy == 'fuzzy':
            self.enable_fuzzy_matching = enabled
        elif strategy == 'alias':
            self.enable_alias_matching = enabled
        else:
            raise ValueError(f"Unknown matching strategy: {strategy}")
        
        logger.debug(f"{'Enabled' if enabled else 'Disabled'} {strategy} matching")
    
    def set_strategy_weights(self, weights: Dict[str, float]) -> None:
        """
        Set weights for different similarity strategies.
        
        Args:
            weights: Dictionary of strategy -> weight mappings
        """
        # Validate weights
        for strategy, weight in weights.items():
            if not 0.0 <= weight <= 1.0:
                raise ValueError(f"Weight for {strategy} must be between 0.0 and 1.0")
        
        self.strategy_weights.update(weights)
        logger.debug(f"Updated strategy weights: {weights}")
    
    def set_matching_strategies(self, strategies: List[str]) -> None:
        """
        Set enabled matching strategies.
        
        Args:
            strategies: List of strategy names to enable
        """
        valid_strategies = ['fuzzy', 'alias', 'substring', 'normalized']
        for strategy in strategies:
            if strategy not in valid_strategies:
                raise ValueError(f"Unknown strategy: {strategy}. Valid strategies: {valid_strategies}")
        
        self.matching_strategies = strategies
        logger.debug(f"Set matching strategies: {strategies}")
    
    def configure_advanced_options(self, 
                                 enable_substring_matching: Optional[bool] = None,
                                 enable_normalized_matching: Optional[bool] = None,
                                 max_matches: Optional[int] = None,
                                 min_confidence_threshold: Optional[float] = None) -> None:
        """
        Configure advanced matching options.
        
        Args:
            enable_substring_matching: Whether to enable substring matching
            enable_normalized_matching: Whether to enable normalized matching
            max_matches: Maximum number of matches to return
            min_confidence_threshold: Minimum confidence threshold
        """
        if enable_substring_matching is not None:
            self.enable_substring_matching = enable_substring_matching
        if enable_normalized_matching is not None:
            self.enable_normalized_matching = enable_normalized_matching
        if max_matches is not None:
            if max_matches < 1:
                raise ValueError("max_matches must be at least 1")
            self.max_matches = max_matches
        if min_confidence_threshold is not None:
            if not 0.0 <= min_confidence_threshold <= 1.0:
                raise ValueError("min_confidence_threshold must be between 0.0 and 1.0")
            self.min_confidence_threshold = min_confidence_threshold
        
        logger.debug("Updated advanced matching options")
    
    def get_configuration(self) -> Dict[str, any]:
        """
        Get current matcher configuration.
        
        Returns:
            Dictionary with current configuration settings
        """
        return {
            'similarity_threshold': self.similarity_threshold,
            'enable_fuzzy_matching': self.enable_fuzzy_matching,
            'enable_alias_matching': self.enable_alias_matching,
            'enable_substring_matching': self.enable_substring_matching,
            'enable_normalized_matching': self.enable_normalized_matching,
            'custom_aliases_count': len(self.common_aliases),
            'matching_strategies': self.matching_strategies,
            'strategy_weights': self.strategy_weights,
            'max_matches': self.max_matches,
            'min_confidence_threshold': self.min_confidence_threshold
        }