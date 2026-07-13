"""
Constants and attribute schemas for BNG AI QGIS Plugin.

This module centralizes all constant values, attribute schemas,
and mappings used throughout the plugin.

Usage:
    from ..utils.constants import ATTRIBUTE_SCHEMAS, STYLE_FILES
    
    attrs = ATTRIBUTE_SCHEMAS['tree']
    style = STYLE_FILES['base_tree']
"""
from qgis.PyQt.QtCore import QVariant


# =============================================================================
# ATTRIBUTE SCHEMAS
# =============================================================================
# Define field schemas for different layer types
# Format: List of (field_name, QVariant type)

TREE_ATTRIBUTES = [
    ('id', QVariant.String),
    ('habitatReferenceID', QVariant.String),
    ('retainedId', QVariant.String),
    ('sourceId', QVariant.String),
    ('treeId', QVariant.String),
    ('species', QVariant.String),
    ('height', QVariant.Double),
    ('diameter', QVariant.Double),
    ('aiDashCode', QVariant.String),
    ('aiDashLabel', QVariant.String),
    ('condition', QVariant.String),
    ('treeSize', QVariant.String),
    ('strategicSignificance', QVariant.String),
    ('activityType', QVariant.String),
    ('clientId', QVariant.String),
    ('notes', QVariant.String),
]

WATERCOURSE_ATTRIBUTES = [
    ('id', QVariant.String),
    ('habitatReferenceID', QVariant.String),
    ('retainedId', QVariant.String),
    ('sourceId', QVariant.String),
    ('type', QVariant.String),
    ('length', QVariant.Double),
    ('width', QVariant.Double),
    ('condition', QVariant.String),
    ('distinctiveness', QVariant.String),  # Read-only, populated from server
    ('strategicSignificance', QVariant.String),
    ('aiDashCode', QVariant.String),
    ('aiDashLabel', QVariant.String),
    ('watercourseEncroachment', QVariant.String),
    ('riparianEncroachment', QVariant.String),
    ('activityType', QVariant.String),
    ('clientId', QVariant.String),
    ('notes', QVariant.String),
]

POLYGON_ATTRIBUTES = [
    ('id', QVariant.String),
    ('habitatReferenceID', QVariant.String),
    ('retainedId', QVariant.String),
    ('sourceId', QVariant.String),
    ('area', QVariant.Double),
    ('length', QVariant.Double),
    ('condition', QVariant.String),
    ('distinctiveness', QVariant.String),  # Read-only, populated from server
    ('strategicSignificance', QVariant.String),
    ('aiDashCode', QVariant.String),
    ('aiDashLabel', QVariant.String),
    ('activityType', QVariant.String),
    ('clientId', QVariant.String),
    ('notes', QVariant.String),
]

PLAN_POLYGON_ATTRIBUTES = [
    ('id', QVariant.String),
    ('habitatReferenceID', QVariant.String),
    ('retainedId', QVariant.String),
    ('sourceId', QVariant.String),
    ('area', QVariant.Double),
    ('length', QVariant.Double),
    ('condition', QVariant.String),
    ('treeSize', QVariant.String),
    ('isIrreplaceableHabitat', QVariant.Bool),
    ('distinctiveness', QVariant.String),  # Read-only, populated from server
    ('strategy', QVariant.String),
    ('strategicSignificance', QVariant.String),
    ('aiDashCode', QVariant.String),
    ('aiDashLabel', QVariant.String),
    ('customCode', QVariant.String),
    ('customLabel', QVariant.String),
    ('customGroup', QVariant.String),
    ('customShapeType', QVariant.String),
    ('activityType', QVariant.String),
    ('clientId', QVariant.String),
    ('description', QVariant.String),
]

BOUNDARY_ATTRIBUTES = [
    ('type', QVariant.String),
    ('name', QVariant.String),
]

# Unified schema lookup
ATTRIBUTE_SCHEMAS = {
    'tree': TREE_ATTRIBUTES,
    'point': TREE_ATTRIBUTES,  # Alias
    'watercourse': WATERCOURSE_ATTRIBUTES,
    'hedgerow': WATERCOURSE_ATTRIBUTES,  # Alias
    'line': WATERCOURSE_ATTRIBUTES,  # Alias
    'polygon': POLYGON_ATTRIBUTES,
    'plan_polygon': PLAN_POLYGON_ATTRIBUTES,
    'boundary': BOUNDARY_ATTRIBUTES,
}


# =============================================================================
# STYLE FILE MAPPINGS
# =============================================================================
# Map style names to QML file paths (relative to layers/symbology/)

STYLE_FILES = {
    # Base layer styles
    'base_tree': 'Base/BaseTree.qml',
    'base_watercourse': 'Base/BaseWatercourseHedgerowHabitats.qml',
    'base_polygon': 'Base/BasePolygon.qml',
    'base_boundary': 'Base/SiteBoundary.qml',
    
    # Plan layer styles
    'plan_tree': 'Plan/PlanTree.qml',
    'plan_watercourse': 'Plan/PlanWatercourseHedgerow.qml',
    'plan_polygon': 'Plan/PlanPolygon.qml',
    'plan_boundary': 'Plan/SiteBoundary.qml',
}

LABEL_STYLE_FILE = 'labelStyles/BaseLableStyle.qml'


# =============================================================================
# LAYER GROUP NAMES
# =============================================================================

LAYER_GROUPS = {
    'root': 'BNG AI',
    'baseline': 'Base Layers',
    'plan': 'BNG Plan Layers',
    'retained': 'Retained Habitat Layers',
}


# =============================================================================
# GEOMETRY TYPE MAPPINGS
# =============================================================================

GEOMETRY_TYPES = {
    'point': 'Point',
    'line': 'LineString',
    'polygon': 'Polygon',
    'multipoint': 'MultiPoint',
    'multiline': 'MultiLineString',
    'multipolygon': 'MultiPolygon',
}

# Map GeoJSON types to categories
GEOMETRY_CATEGORY_MAP = {
    'Point': 'point',
    'MultiPoint': 'point',
    'LineString': 'line',
    'MultiLineString': 'line',
    'Polygon': 'polygon',
    'MultiPolygon': 'polygon',
}


# =============================================================================
# API CONSTANTS
# =============================================================================

# Default CRS for layers
DEFAULT_CRS = 'EPSG:4326'

# Comparison tolerances
AREA_TOLERANCE = 0.001  # 0.1%
LENGTH_TOLERANCE = 0.001  # 0.1%

# Attributes to ignore during feature comparison
COMPARISON_IGNORED_ATTRIBUTES = frozenset({
    'sourceId',
    'activityType', 
    'aiDashLabel',
    'mergedIds',
    'referenceId',
    'clientId',
})


# =============================================================================
# ACTIVITY TYPES
# =============================================================================

ACTIVITY_TYPES = {
    'CREATE': 'CREATE',
    'CONVERT': 'CONVERT',
    'ENHANCE': 'ENHANCE',
    'RETAIN': 'RETAIN',
}

# Default activity type by geometry
DEFAULT_ACTIVITY_BY_GEOMETRY = {
    'Point': 'CREATE',
    'LineString': 'CREATE',
    'Polygon': 'CONVERT',
    'MultiPoint': 'CREATE',
    'MultiLineString': 'CREATE',
    'MultiPolygon': 'CONVERT',
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_attributes_for_type(layer_type: str) -> list:
    """
    Get attribute schema for a layer type.
    
    Args:
        layer_type: Type of layer ('tree', 'watercourse', 'polygon', etc.)
        
    Returns:
        List of (field_name, QVariant type) tuples
    """
    return ATTRIBUTE_SCHEMAS.get(layer_type.lower(), POLYGON_ATTRIBUTES)


def get_style_path(style_name: str) -> str:
    """
    Get style file path for a style name.
    
    Args:
        style_name: Name of the style
        
    Returns:
        Relative path to QML file
    """
    return STYLE_FILES.get(style_name, '')


def get_geometry_category(geom_type: str) -> str:
    """
    Get geometry category from GeoJSON type.
    
    Args:
        geom_type: GeoJSON geometry type
        
    Returns:
        Category: 'point', 'line', or 'polygon'
    """
    return GEOMETRY_CATEGORY_MAP.get(geom_type, 'polygon')

