"""
Utils package for BNG AI QGIS Plugin.

Contains utility modules and helper functions used across the plugin:
- logging: Centralized logging functions
- constants: Attribute schemas, mappings, and constants
- api_config: API endpoint configuration
- habitat_mappings: Habitat attribute mappings
- validation_utils: Validation utilities

Usage:
    from bngai.utils.logging import log_info, log_error
    from bngai.utils.constants import ATTRIBUTE_SCHEMAS
"""

from .logging import log_info, log_warn, log_error, log_debug, logged, LogContext
from .constants import (
    ATTRIBUTE_SCHEMAS,
    STYLE_FILES,
    LAYER_GROUPS,
    GEOMETRY_TYPES,
    DEFAULT_CRS,
    get_attributes_for_type,
    get_style_path,
    get_geometry_category,
)

__all__ = [
    # Logging
    'log_info', 'log_warn', 'log_error', 'log_debug', 'logged', 'LogContext',
    # Constants
    'ATTRIBUTE_SCHEMAS', 'STYLE_FILES', 'LAYER_GROUPS', 'GEOMETRY_TYPES',
    'DEFAULT_CRS', 'get_attributes_for_type', 'get_style_path', 'get_geometry_category',
] 