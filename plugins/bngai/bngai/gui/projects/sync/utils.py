"""
Utility functions for sync operations.

These are stateless helper functions used across the sync module.
"""
from typing import Any, Optional, Dict

# Import centralized logging
from ....utils.logging import log_info, log_warn, log_error


def normalize_for_compare(value: Any) -> str:
    """
    Normalize values for comparison.
    
    Treats None, empty strings, and sentinel strings ('NULL', 'None') as equal.
    
    Args:
        value: Any value to normalize
        
    Returns:
        str: Normalized string value
    """
    try:
        from PyQt5.QtCore import QVariant
    except ImportError:
        QVariant = None
    
    if QVariant is not None and isinstance(value, QVariant):
        if value.isNull():
            return ''
        value = value.value()
    
    if value is None:
        return ''
    
    if isinstance(value, str):
        s = value.strip()
        if s.lower() in ('', 'null', 'none'):
            return ''
        return s
    
    return str(value).strip()


def safe_get_attribute(feature, field_name: str) -> Optional[Any]:
    """
    Safely get attribute value from a feature.
    
    Args:
        feature: QgsFeature to get attribute from
        field_name: Name of the field
        
    Returns:
        Attribute value or None if not found
    """
    try:
        field_idx = feature.fieldNameIndex(field_name)
        if field_idx >= 0:
            value = feature.attribute(field_name)
            return value if value else None
    except Exception:
        pass
    return None


def safe_lower(value: Any) -> Optional[str]:
    """
    Safely convert value to lowercase string.
    
    Args:
        value: Value to convert
        
    Returns:
        Lowercase string or None
    """
    return str(value).lower() if value is not None else None


# Re-export logging functions for backward compatibility
# These are now imported from utils.logging at the top


def get_geometry_type_category(geom_type: str) -> str:
    """
    Get category of geometry type.
    
    Args:
        geom_type: GeoJSON geometry type
        
    Returns:
        Category: 'point', 'line', or 'polygon'
    """
    geom_type_lower = geom_type.lower()
    if 'point' in geom_type_lower:
        return 'point'
    elif 'line' in geom_type_lower:
        return 'line'
    elif 'polygon' in geom_type_lower:
        return 'polygon'
    return 'unknown'


def determine_activity_type(geometry_type: str, existing_type: Optional[str] = None) -> str:
    """
    Determine the activity type based on geometry.
    
    Args:
        geometry_type: GeoJSON geometry type
        existing_type: Existing activity type (if any)
        
    Returns:
        Activity type: 'CREATE' or 'CONVERT'
    """
    if existing_type and isinstance(existing_type, str) and existing_type.strip():
        return existing_type
    
    if geometry_type in ['Point', 'LineString', 'MultiPoint', 'MultiLineString']:
        return 'CREATE'
    return 'CONVERT'


def filter_features_by_geometry_type(features: Dict[str, Dict], feature_type: str) -> Dict[str, Dict]:
    """
    Filter features by geometry type.
    
    Args:
        features: Dictionary of features keyed by ID
        feature_type: Type to filter ('point', 'line', 'polygon')
        
    Returns:
        Filtered features dictionary
    """
    filtered = {}
    
    type_mapping = {
        'point': ['Point', 'MultiPoint'],
        'line': ['LineString', 'MultiLineString'],
        'polygon': ['Polygon', 'MultiPolygon']
    }
    
    allowed_types = type_mapping.get(feature_type, [])
    
    for feature_id, feature_data in features.items():
        geom_type = feature_data.get('geometry', {}).get('type', '')
        if geom_type in allowed_types:
            filtered[feature_id] = feature_data
    
    return filtered

