"""
Pattern validation utilities for configurable detection patterns.
"""

import re
import signal
import time
from typing import List, Dict, Tuple, Optional
from contextlib import contextmanager

from .exceptions import ConfigurationError
from .logging_config import get_logger

logger = get_logger('pattern_validator')


class PatternValidationError(ConfigurationError):
    """Exception raised when pattern validation fails."""
    pass


class PatternValidator:
    """Validator for regex patterns used in component detection."""
    
    def __init__(self, validation_timeout: float = 1.0):
        """
        Initialize the pattern validator.
        
        Args:
            validation_timeout: Maximum time to spend validating each pattern
        """
        self.validation_timeout = validation_timeout
    
    @contextmanager
    def _timeout_context(self, timeout: float):
        """Context manager for pattern validation timeout."""
        def timeout_handler(signum, frame):
            raise TimeoutError("Pattern validation timed out")
        
        # Set up the timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout))
        
        try:
            yield
        finally:
            # Clean up
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    
    def validate_pattern(self, pattern: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a single regex pattern.
        
        Args:
            pattern: Regex pattern to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not pattern:
            return False, "Pattern cannot be empty"
        
        try:
            with self._timeout_context(self.validation_timeout):
                # Try to compile the pattern
                compiled_pattern = re.compile(pattern)
                
                # Test the pattern with some sample strings
                test_strings = [
                    "test-package",
                    "libtest.so.1",
                    "kernel-module.ko",
                    "system-util-1.0",
                    "app-dev",
                    "test-suite"
                ]
                
                for test_string in test_strings:
                    try:
                        compiled_pattern.match(test_string)
                    except Exception as e:
                        return False, f"Pattern failed on test string '{test_string}': {e}"
                
                return True, None
                
        except re.error as e:
            return False, f"Invalid regex pattern: {e}"
        except TimeoutError:
            return False, f"Pattern validation timed out after {self.validation_timeout} seconds"
        except Exception as e:
            return False, f"Unexpected error during pattern validation: {e}"
    
    def validate_patterns(self, patterns: List[str]) -> Dict[str, Optional[str]]:
        """
        Validate a list of regex patterns.
        
        Args:
            patterns: List of regex patterns to validate
            
        Returns:
            Dictionary mapping pattern to error message (None if valid)
        """
        results = {}
        
        for pattern in patterns:
            is_valid, error_message = self.validate_pattern(pattern)
            results[pattern] = error_message
            
            if not is_valid:
                logger.warning(f"Invalid pattern '{pattern}': {error_message}")
        
        return results
    
    def validate_pattern_effectiveness(self, pattern: str, test_cases: List[Tuple[str, bool]]) -> Tuple[bool, str]:
        """
        Validate that a pattern works as expected with test cases.
        
        Args:
            pattern: Regex pattern to test
            test_cases: List of (test_string, should_match) tuples
            
        Returns:
            Tuple of (is_effective, report)
        """
        try:
            compiled_pattern = re.compile(pattern)
        except re.error as e:
            return False, f"Invalid regex pattern: {e}"
        
        failures = []
        successes = 0
        
        for test_string, should_match in test_cases:
            try:
                matches = bool(compiled_pattern.match(test_string))
                if matches == should_match:
                    successes += 1
                else:
                    expected = "match" if should_match else "not match"
                    actual = "matched" if matches else "did not match"
                    failures.append(f"'{test_string}' should {expected} but {actual}")
            except Exception as e:
                failures.append(f"Error testing '{test_string}': {e}")
        
        total_tests = len(test_cases)
        success_rate = successes / total_tests if total_tests > 0 else 0
        
        if failures:
            report = f"Pattern effectiveness: {successes}/{total_tests} tests passed ({success_rate:.1%})\n"
            report += "Failures:\n" + "\n".join(f"  - {failure}" for failure in failures)
            return success_rate >= 0.8, report  # 80% success rate threshold
        else:
            report = f"Pattern effectiveness: {successes}/{total_tests} tests passed (100%)"
            return True, report
    
    def get_pattern_statistics(self, patterns: List[str]) -> Dict[str, any]:
        """
        Get statistics about a list of patterns.
        
        Args:
            patterns: List of regex patterns
            
        Returns:
            Dictionary with pattern statistics
        """
        stats = {
            'total_patterns': len(patterns),
            'valid_patterns': 0,
            'invalid_patterns': 0,
            'empty_patterns': 0,
            'complex_patterns': 0,  # Patterns with special regex features
            'validation_errors': []
        }
        
        for pattern in patterns:
            if not pattern:
                stats['empty_patterns'] += 1
                continue
            
            is_valid, error_message = self.validate_pattern(pattern)
            
            if is_valid:
                stats['valid_patterns'] += 1
                
                # Check for complexity indicators
                if any(char in pattern for char in ['(', ')', '[', ']', '{', '}', '|', '?', '*', '+']):
                    stats['complex_patterns'] += 1
            else:
                stats['invalid_patterns'] += 1
                stats['validation_errors'].append({
                    'pattern': pattern,
                    'error': error_message
                })
        
        return stats


def validate_filtering_config(filtering_config) -> List[str]:
    """
    Validate all patterns in a filtering configuration.
    
    Args:
        filtering_config: FilteringConfig object to validate
        
    Returns:
        List of validation error messages
    """
    if not filtering_config.validate_patterns:
        return []
    
    validator = PatternValidator(filtering_config.pattern_validation_timeout)
    errors = []
    
    # Validate all pattern lists
    pattern_groups = {
        'custom_kernel_patterns': filtering_config.custom_kernel_patterns,
        'custom_system_patterns': filtering_config.custom_system_patterns,
        'custom_exclusions': filtering_config.custom_exclusions,
        'kernel_module_patterns': filtering_config.kernel_module_patterns,
        'system_library_patterns': filtering_config.system_library_patterns,
        'os_utility_patterns': filtering_config.os_utility_patterns,
        'development_patterns': filtering_config.development_patterns,
        'test_patterns': filtering_config.test_patterns,
    }
    
    for group_name, patterns in pattern_groups.items():
        if not patterns:
            continue
            
        validation_results = validator.validate_patterns(patterns)
        
        for pattern, error_message in validation_results.items():
            if error_message:
                errors.append(f"{group_name}: {error_message}")
    
    return errors


def validate_pattern_effectiveness():
    """Test the effectiveness of default patterns with known test cases."""
    validator = PatternValidator()
    
    # Test cases for different pattern types
    test_cases = {
        'kernel_module_patterns': [
            (r'.*\.ko$', [
                ('module.ko', True),
                ('driver.ko', True),
                ('libtest.so', False),
                ('kernel-module', False),
            ]),
            (r'^kernel-.*', [
                ('kernel-headers', True),
                ('kernel-devel', True),
                ('my-kernel', False),
                ('userspace-app', False),
            ]),
        ],
        'system_library_patterns': [
            (r'^glibc.*', [
                ('glibc', True),
                ('glibc-common', True),
                ('libglibc', False),
                ('application', False),
            ]),
            (r'^systemd.*', [
                ('systemd', True),
                ('systemd-units', True),
                ('libsystemd', False),
                ('user-app', False),
            ]),
        ],
        'development_patterns': [
            (r'.*-dev$', [
                ('libssl-dev', True),
                ('python3-dev', True),
                ('libssl', False),
                ('development-tools', False),
            ]),
        ],
    }
    
    results = {}
    
    for category, pattern_tests in test_cases.items():
        results[category] = {}
        
        for pattern, test_data in pattern_tests:
            is_effective, report = validator.validate_pattern_effectiveness(pattern, test_data)
            results[category][pattern] = {
                'effective': is_effective,
                'report': report
            }
    
    return results


if __name__ == '__main__':
    # Run pattern effectiveness tests
    print("Testing pattern effectiveness...")
    results = validate_pattern_effectiveness()
    
    for category, patterns in results.items():
        print(f"\n{category}:")
        for pattern, result in patterns.items():
            status = "✓" if result['effective'] else "✗"
            print(f"  {status} {pattern}")
            if not result['effective']:
                print(f"    {result['report']}")