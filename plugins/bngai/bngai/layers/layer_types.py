"""
Layer type definitions and ID generation functionality.
"""
from enum import Enum

class LayerType(Enum):
    """Enum defining different layer types in the BNG AI plugin."""
    TREE = "tree"
    WATERCOURSE = "watercourse"
    HEDGEROW = "hedgerow"
    PLAN = "plan"
    RLB = "rlb"  # Red Line Boundary

def generate_layer_id(project_id, layer_type):
    """
    Generate a layer ID using project ID and layer type.
    
    Args:
        project_id (str): The project ID
        layer_type (LayerType): The type of layer
        
    Returns:
        str: Generated layer ID in format 'project_id_layer_type'
    """
    return f"{project_id}_{layer_type.value}"

def get_layer_type(layer_id):
    """
    Extract layer type from a layer ID.
    
    Args:
        layer_id (str): The layer ID to parse
        
    Returns:
        LayerType: The layer type or None if invalid format
    """
    try:
        # Split ID into project_id and layer_type
        parts = layer_id.split('_')
        if len(parts) < 2:
            return None
            
        # Get the layer type part
        type_str = parts[-1]
        
        # Try to convert to LayerType
        return LayerType(type_str)
        
    except (ValueError, AttributeError):
        return None

def get_project_id(layer_id):
    """
    Extract project ID from a layer ID.
    
    Args:
        layer_id (str): The layer ID to parse
        
    Returns:
        str: The project ID or None if invalid format
    """
    try:
        # Split ID and get everything except the last part (layer type)
        parts = layer_id.split('_')
        if len(parts) < 2:
            return None
            
        # Join all parts except the last one (in case project_id contains underscores)
        return '_'.join(parts[:-1])
        
    except (ValueError, AttributeError):
        return None 