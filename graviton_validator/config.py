"""
Configuration management for the Graviton Compatibility Validator.
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .exceptions import ConfigurationError
from .logging_config import get_logger

logger = get_logger('config')


@dataclass
class MatchingConfig:
    """Configuration for intelligent matching."""
    intelligent_matching: bool = True
    similarity_threshold: float = 0.8
    enable_fuzzy_matching: bool = True
    enable_alias_matching: bool = True
    custom_aliases: Dict[str, str] = field(default_factory=dict)
    name_mappings: Dict[str, str] = field(default_factory=dict)  # Additional name mappings
    
    # Extensible matching algorithm framework
    matching_strategies: List[str] = field(default_factory=lambda: ['fuzzy', 'alias', 'substring'])
    strategy_weights: Dict[str, float] = field(default_factory=lambda: {
        'levenshtein': 0.3,
        'jaro_winkler': 0.3,
        'substring': 0.2,
        'normalized': 0.2
    })
    
    # Advanced matching options
    enable_substring_matching: bool = True
    enable_normalized_matching: bool = True
    max_matches: int = 5
    min_confidence_threshold: float = 0.5


@dataclass
class FilteringConfig:
    """Configuration for component filtering."""
    exclude_system_packages: bool = True
    custom_kernel_patterns: List[str] = field(default_factory=list)
    custom_system_patterns: List[str] = field(default_factory=list)
    custom_exclusions: List[str] = field(default_factory=list)
    
    # OS/Kernel detection patterns
    kernel_module_patterns: List[str] = field(default_factory=lambda: [
        r'.*\.ko$',           # Kernel modules
        r'^kernel-.*',        # Kernel packages
        r'.*-kmod-.*',        # Kernel module packages
        r'.*-dkms$',          # Dynamic kernel module support
    ])
    
    system_library_patterns: List[str] = field(default_factory=lambda: [
        r'^glibc.*',          # GNU C Library
        r'^libc.*',           # C Library variants
        r'^systemd.*',        # systemd components
        r'^udev.*',           # Device manager
        r'^dbus.*',           # D-Bus system
        r'^pam.*',            # Pluggable Authentication Modules
    ])
    
    os_utility_patterns: List[str] = field(default_factory=lambda: [
        r'^(bash|sh|zsh|fish).*',     # Shells
        r'^coreutils.*',              # Core utilities
        r'^util-linux.*',             # Linux utilities
        r'^procps.*',                 # Process utilities
        r'^findutils.*',              # Find utilities
        r'^grep.*',                   # Text search utilities
        r'^sed.*',                    # Stream editor
        r'^awk.*',                    # Text processing
    ])
    
    # Environment-specific exclusion patterns
    development_patterns: List[str] = field(default_factory=lambda: [
        r'.*-dev$',           # Development packages
        r'.*-devel$',         # Development packages (RPM)
        r'.*-dbg$',           # Debug packages
        r'.*-debug$',         # Debug packages
        r'.*-doc$',           # Documentation packages
        r'.*-docs$',          # Documentation packages
    ])
    
    test_patterns: List[str] = field(default_factory=lambda: [
        r'^test-.*',          # Test packages
        r'.*-test$',          # Test packages
        r'.*-tests$',         # Test packages
        r'^mock-.*',          # Mock packages
        r'.*-mock$',          # Mock packages
    ])
    
    # Pattern validation settings
    validate_patterns: bool = True
    pattern_validation_timeout: float = 1.0  # seconds


@dataclass
class OutputConfig:
    """Configuration for output formatting."""
    default_format: str = "text"
    include_system_packages: bool = False
    show_confidence_scores: bool = False


@dataclass
class CacheConfig:
    """Configuration for caching system."""
    enabled: bool = True
    cache_dir: str = ".cache"
    max_age_days: int = 30
    rate_limiting: bool = True
    
    # Rate limiting per runtime
    rate_limits: Dict[str, Dict[str, int]] = field(default_factory=lambda: {
        'nuget': {'requests_per_minute': 60, 'burst_limit': 10},
        'pypi': {'requests_per_minute': 60, 'burst_limit': 10},
        'npm': {'requests_per_minute': 60, 'burst_limit': 10},
        'maven': {'requests_per_minute': 60, 'burst_limit': 10},
        'rubygems': {'requests_per_minute': 300, 'burst_limit': 20}  # RubyGems.org allows higher rate
    })


@dataclass
class KnowledgeBaseConfig:
    """Configuration for knowledge base."""
    default_files: List[str] = field(default_factory=list)
    cache_enabled: bool = True
    auto_update: bool = False


@dataclass
class LoggingConfig:
    """Configuration for logging."""
    level: str = "INFO"
    log_file: Optional[str] = None
    verbose: bool = False


@dataclass
class Config:
    """Main configuration class."""
    knowledge_base: KnowledgeBaseConfig = field(default_factory=KnowledgeBaseConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    matching: MatchingConfig = field(default_factory=MatchingConfig)
    filtering: FilteringConfig = field(default_factory=FilteringConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from file or use defaults.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        Config object with loaded settings
        
    Raises:
        ConfigurationError: If configuration file is invalid
    """
    config = Config()
    
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            if config_data:
                # Update configuration with loaded data
                _update_config_from_dict(config, config_data)
                logger.info(f"Loaded configuration from {config_path}")
        
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in configuration file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading configuration file: {e}")
    
    elif config_path:
        logger.warning(f"Configuration file not found: {config_path}")
    
    # Validate filtering patterns if enabled
    if config.filtering.validate_patterns:
        try:
            from .pattern_validator import validate_filtering_config
            validation_errors = validate_filtering_config(config.filtering)
            if validation_errors:
                error_msg = "Pattern validation failed:\n" + "\n".join(validation_errors)
                raise ConfigurationError(error_msg)
        except ImportError:
            logger.warning("Pattern validator not available, skipping pattern validation")
    
    return config


def _update_config_from_dict(config: Config, config_data: Dict) -> None:
    """
    Update configuration object from dictionary data.
    
    Args:
        config: Config object to update
        config_data: Dictionary with configuration data
    """
    if 'knowledge_base' in config_data:
        kb_data = config_data['knowledge_base']
        if 'default_files' in kb_data:
            config.knowledge_base.default_files = kb_data['default_files']
        if 'cache_enabled' in kb_data:
            config.knowledge_base.cache_enabled = kb_data['cache_enabled']
        if 'auto_update' in kb_data:
            config.knowledge_base.auto_update = kb_data['auto_update']
    
    if 'output' in config_data:
        output_data = config_data['output']
        if 'default_format' in output_data:
            config.output.default_format = output_data['default_format']
        if 'include_system_packages' in output_data:
            config.output.include_system_packages = output_data['include_system_packages']
        if 'show_confidence_scores' in output_data:
            config.output.show_confidence_scores = output_data['show_confidence_scores']
    
    if 'matching' in config_data:
        matching_data = config_data['matching']
        if 'intelligent_matching' in matching_data:
            config.matching.intelligent_matching = matching_data['intelligent_matching']
        if 'similarity_threshold' in matching_data:
            config.matching.similarity_threshold = matching_data['similarity_threshold']
        if 'enable_fuzzy_matching' in matching_data:
            config.matching.enable_fuzzy_matching = matching_data['enable_fuzzy_matching']
        if 'enable_alias_matching' in matching_data:
            config.matching.enable_alias_matching = matching_data['enable_alias_matching']
        if 'custom_aliases' in matching_data:
            config.matching.custom_aliases = matching_data['custom_aliases']
        if 'name_mappings' in matching_data:
            config.matching.name_mappings = matching_data['name_mappings']
        if 'matching_strategies' in matching_data:
            config.matching.matching_strategies = matching_data['matching_strategies']
        if 'strategy_weights' in matching_data:
            config.matching.strategy_weights = matching_data['strategy_weights']
        if 'enable_substring_matching' in matching_data:
            config.matching.enable_substring_matching = matching_data['enable_substring_matching']
        if 'enable_normalized_matching' in matching_data:
            config.matching.enable_normalized_matching = matching_data['enable_normalized_matching']
        if 'max_matches' in matching_data:
            config.matching.max_matches = matching_data['max_matches']
        if 'min_confidence_threshold' in matching_data:
            config.matching.min_confidence_threshold = matching_data['min_confidence_threshold']
        if 'custom_aliases' in matching_data:
            config.matching.custom_aliases = matching_data['custom_aliases']
        if 'name_mappings' in matching_data:
            config.matching.name_mappings = matching_data['name_mappings']
    
    if 'filtering' in config_data:
        filtering_data = config_data['filtering']
        if 'exclude_system_packages' in filtering_data:
            config.filtering.exclude_system_packages = filtering_data['exclude_system_packages']
        if 'custom_kernel_patterns' in filtering_data:
            config.filtering.custom_kernel_patterns = filtering_data['custom_kernel_patterns']
        if 'custom_system_patterns' in filtering_data:
            config.filtering.custom_system_patterns = filtering_data['custom_system_patterns']
        if 'custom_exclusions' in filtering_data:
            config.filtering.custom_exclusions = filtering_data['custom_exclusions']
        if 'kernel_module_patterns' in filtering_data:
            config.filtering.kernel_module_patterns = filtering_data['kernel_module_patterns']
        if 'system_library_patterns' in filtering_data:
            config.filtering.system_library_patterns = filtering_data['system_library_patterns']
        if 'os_utility_patterns' in filtering_data:
            config.filtering.os_utility_patterns = filtering_data['os_utility_patterns']
        if 'development_patterns' in filtering_data:
            config.filtering.development_patterns = filtering_data['development_patterns']
        if 'test_patterns' in filtering_data:
            config.filtering.test_patterns = filtering_data['test_patterns']
        if 'validate_patterns' in filtering_data:
            config.filtering.validate_patterns = filtering_data['validate_patterns']
        if 'pattern_validation_timeout' in filtering_data:
            config.filtering.pattern_validation_timeout = filtering_data['pattern_validation_timeout']
    
    if 'logging' in config_data:
        logging_data = config_data['logging']
        if 'level' in logging_data:
            config.logging.level = logging_data['level']
        if 'log_file' in logging_data:
            config.logging.log_file = logging_data['log_file']
        if 'verbose' in logging_data:
            config.logging.verbose = logging_data['verbose']


def get_default_config_path() -> Optional[str]:
    """
    Get the default configuration file path.
    
    Returns:
        Path to default config file if it exists, None otherwise
    """
    possible_paths = [
        'graviton_validator.yaml',
        'graviton_validator.yml',
        os.path.expanduser('~/.graviton_validator.yaml'),
        os.path.expanduser('~/.graviton_validator.yml'),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None