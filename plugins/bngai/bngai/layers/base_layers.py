"""
BaseLayersManager - Module for managing base layers (trees, watercourse/hedgerow, plan) in QGIS
"""
from qgis.core import QgsProject
from qgis.PyQt.QtGui import QColor, QFont
import os

from .layer_manager import LayerManager
from .drawing_handler import DrawingHandler
from ..utils.logging import log_info, log_error
from ..utils.constants import TREE_ATTRIBUTES, WATERCOURSE_ATTRIBUTES, POLYGON_ATTRIBUTES, DEFAULT_CRS

class BaseLayersManager:
    """
    Manages base layers within QGIS for the BNG AI plugin.
    Base layers include trees, watercourse/hedgerow, and plan layers.
    """
    
    def __init__(self):
        """Initialize the base layers manager"""
        self.layer_manager = LayerManager()
        # Connect to existing layers to track selection
        self.layer_manager.connect_to_existing_layers()
        log_info("Initialized BaseLayers")
        self.project = QgsProject.instance()
        self.root = self.project.layerTreeRoot()
        self.base_group = None
        self.drawing_handler = None
        
        # Ensure the Base Layers group exists
        self._ensure_base_group()
        
        # Use centralized attribute schemas from constants
        self.tree_attributes = TREE_ATTRIBUTES
        self.watercourse_attributes = WATERCOURSE_ATTRIBUTES
        self.plan_attributes = POLYGON_ATTRIBUTES
    
    def _ensure_base_group(self):
        """
        Ensure that the Base Layers group exists in the layer tree.
        Creates it if it doesn't exist.
        """
        # Look for existing Base Layers group
        self.base_group = self.root.findGroup("Base Layers")
        
        # Create group if it doesn't exist
        if not self.base_group:
            self.base_group = self.root.addGroup("Base Layers")
            log_info("Created Base Layers group")

    # Tree layer methods
    def create_tree_layer(self, name="Base Trees"):
        """
        Create a layer for tree mapping
        
        Args:
            name (str): Name for the layer
            
        Returns:
            QgsVectorLayer: The created vector layer or None if failed
        """
        try:
            # Create a new memory layer with tree attributes
            layer = self.layer_manager.create_memory_layer(
                name,
                'Point',
                crs=DEFAULT_CRS,
                attributes=self.tree_attributes
            )
            
            if not layer:
                return None
            
            # Move from default BNG AI group to Base Layers group
            self._move_to_base_group(layer)
            
            # Apply a default style for trees
            self._apply_tree_style(layer)
            
            log_info(f"Created tree layer: {name}")
            return layer
            
        except Exception as e:
            log_error(f"Error creating tree layer: {str(e)}")
            return None
    
    # Watercourse/Hedgerow layer methods
    def create_watercourse_layer(self, name="Base Watercourse/Hedgerow"):
        """
        Create a layer for watercourse and hedgerow mapping
        
        Args:
            name (str): Name for the layer
            
        Returns:
            QgsVectorLayer: The created vector layer or None if failed
        """
        log_info(f"Creating Base watercourse/hedgerow layer: {name}")
        try:
            # Create a new memory layer with watercourse attributes
            layer = self.layer_manager.create_memory_layer(
                name,
                'LineString',
                crs=DEFAULT_CRS,
                attributes=self.watercourse_attributes
            )
            
            if not layer:
                return None
            
            # Move from default BNG AI group to Base Layers group
            self._move_to_base_group(layer)
            
            # Apply a default style for watercourse/hedgerow
            self._apply_watercourse_style(layer)
            
            log_info(f"Created watercourse/hedgerow layer: {name}")
            return layer
            
        except Exception as e:
            log_error(f"Error creating watercourse/hedgerow layer: {str(e)}")
            return None
    
    # Plan layer methods
    def create_plan_layer(self, name="Base Plan"):
        """
        Create a layer for plan boundary mapping
        
        Args:
            name (str): Name for the layer
            
        Returns:
            QgsVectorLayer: The created vector layer or None if failed
        """
        try:
            # Create a new memory layer with plan attributes
            layer = self.layer_manager.create_memory_layer(
                name,
                'Polygon',
                crs=DEFAULT_CRS,
                attributes=self.plan_attributes
            )
            
            if not layer:
                return None
            
            # Move from default BNG AI group to Base Layers group
            self._move_to_base_group(layer)
            
            # Apply a default style for plans
            self._apply_plan_style(layer)
            
            log_info(f"Created plan layer: {name}")
            return layer
            
        except Exception as e:
            log_error(f"Error creating plan layer: {str(e)}")
            return None
    
    def _move_to_base_group(self, layer):
        """
        Move a layer from its current group to the Base Layers group
        
        Args:
            layer (QgsMapLayer): The layer to move
        """
        if not layer or not self.base_group:
            return
        
        # Find the layer in the layer tree
        layer_id = layer.id()
        layer_node = self.root.findLayer(layer_id)
        
        if layer_node:
            # Get the parent group
            parent = layer_node.parent()
            
            # Clone the layer node to the base group
            self.base_group.addLayer(layer)
            
            # Remove the layer from its original parent
            if parent:
                parent.removeChildNode(layer_node)
    
    def import_geojson(self, file_path, layer_type, name=None):
        """
        Import GeoJSON data into appropriate base layer
        
        Args:
            file_path (str): Path to GeoJSON file
            layer_type (str): Type of layer ('tree', 'watercourse', 'plan')
            name (str): Optional name for the layer (default: derived from layer_type)
            
        Returns:
            QgsVectorLayer: The imported layer or None if failed
        """
        try:
            if not os.path.exists(file_path):
                log_error(f"GeoJSON file not found: {file_path}")
                return None
            
            # Determine layer name and type
            if not name:
                base_name = {
                    'tree': 'Base Trees',
                    'watercourse': 'Base Watercourse/Hedgerow',
                    'plan': 'Base Plan'
                }.get(layer_type, 'Base Layer')
                name = f"Imported {base_name}"
            
            # Load the GeoJSON
            layer = self.layer_manager.add_vector_layer(name, file_path, "ogr")
            
            if not layer:
                return None
            
            # Move to base group
            self._move_to_base_group(layer)
            
            # Apply appropriate style
            if layer_type == 'tree':
                self._apply_tree_style(layer)
            elif layer_type == 'watercourse':
                self._apply_watercourse_style(layer)
            elif layer_type == 'plan':
                self._apply_plan_style(layer)
            
            log_info(f"Imported {layer_type} data from GeoJSON")
            return layer
            
        except Exception as e:
            log_error(f"Error importing GeoJSON: {str(e)}")
            return None
    
    def _apply_tree_style(self, layer):
        """
        Apply QML style to a tree layer
        
        Args:
            layer (QgsVectorLayer): Layer to style
        """
        if not layer:
            return
            
        # Get the path to the QML file from Base symbology
        qml_path = os.path.join(os.path.dirname(__file__), 'symbology', 'Base', 'BaseTree.qml')
        
        if os.path.exists(qml_path):
            # Load and apply the style
            layer.loadNamedStyle(qml_path)
            layer.triggerRepaint()
            log_info(f"Applied tree style from {qml_path}")
        else:
            log_error(f"Style file not found: {qml_path}")
        # Apply QML and enforce label field
        self._apply_label_style(layer, 'retainedId')
    
    def _apply_watercourse_style(self, layer):
        """
        Apply QML style to a watercourse/hedgerow layer
        
        Args:
            layer (QgsVectorLayer): Layer to style
        """
        if not layer:
            return
            
        # Use Base symbology for Watercourse/Hedgerow
        qml_path = os.path.join(os.path.dirname(__file__), 'symbology', 'Base', 'BaseWatercourseHedgerowHabitats.qml')
        
        if os.path.exists(qml_path):
            # Load and apply the style
            layer.loadNamedStyle(qml_path)
            layer.triggerRepaint()
            log_info(f"Applied watercourse/hedgerow style from {qml_path}")
        else:
            log_error(f"Style file not found: {qml_path}")
        # Apply QML and enforce label field
        self._apply_label_style(layer, 'retainedId')
    
    def _apply_plan_style(self, layer):
        """
        Apply QML style to a plan layer
        
        Args:
            layer (QgsVectorLayer): Layer to style
        """
        if not layer:
            return
            
        # Get the path to the QML file from Base symbology
        qml_path = os.path.join(os.path.dirname(__file__), 'symbology', 'Base', 'BasePolygon.qml')
        
        if os.path.exists(qml_path):
            # Load and apply the style
            layer.loadNamedStyle(qml_path)
            layer.triggerRepaint()
            log_info(f"Applied plan style from {qml_path}")
        else:
            log_error(f"Style file not found: {qml_path}")
        # Apply QML and enforce label field
        self._apply_label_style(layer, 'retainedId')

    def _enable_label_by_field(self, layer, field_name: str):
        """Enable labeling for a given field, with geometry-aware placement."""
        try:
            from qgis.core import (
                QgsPalLayerSettings,
                QgsVectorLayerSimpleLabeling,
                QgsTextFormat,
                QgsWkbTypes,
            )
            text_format = QgsTextFormat()
            # Font styling
            font = QFont()
            font.setBold(True)
            font.setPointSize(14)
            text_format.setFont(font)
            text_format.setSize(14)
            pal = QgsPalLayerSettings()
            pal.enabled = True
            pal.fieldName = field_name
            # Choose placement based on geometry type
            try:
                if layer.geometryType() == QgsWkbTypes.LineGeometry:
                    pal.placement = QgsPalLayerSettings.Line
                elif layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                    pal.placement = QgsPalLayerSettings.OverPolygon
                else:
                    pal.placement = QgsPalLayerSettings.OverPoint
            except Exception:
                pal.placement = QgsPalLayerSettings.OverPoint
            # Colors: default black text with white 2px buffer; invert for polygons
            is_polygon = False
            try:
                from qgis.core import QgsWkbTypes as _Wkb
                is_polygon = layer.geometryType() == _Wkb.PolygonGeometry
            except Exception:
                is_polygon = False
            if is_polygon:
                text_format.setColor(QColor('white'))
                text_format.setBufferEnabled(True)
                text_format.setBufferColor(QColor('black'))
                text_format.setBufferSize(2)
                text_format.setBufferOpacity(1.0)
            else:
                text_format.setColor(QColor('black'))
                text_format.setBufferEnabled(True)
                text_format.setBufferColor(QColor('white'))
                text_format.setBufferSize(2)
                text_format.setBufferOpacity(1.0)
            pal.setFormat(text_format)
            labeling = QgsVectorLayerSimpleLabeling(pal)
            layer.setLabeling(labeling)
            layer.setLabelsEnabled(True)
            layer.triggerRepaint()
        except Exception:
            pass

    def _apply_label_style(self, layer, label_field='retainedId'):
        """Apply QML style and then force label field to label_field, preserving QML format/placement."""
        try:
            qml_path = os.path.join(os.path.dirname(__file__), 'labelStyles', 'BaseLableStyle.qml')
            if os.path.exists(qml_path):
                layer.loadNamedStyle(qml_path)
            from qgis.core import (
                QgsVectorLayerSimpleLabeling,
                QgsRuleBasedLabeling,
            )
            labeling = layer.labeling()
            if isinstance(labeling, QgsVectorLayerSimpleLabeling):
                s = labeling.settings()
                s.fieldName = label_field
                layer.setLabeling(QgsVectorLayerSimpleLabeling(s))
            elif isinstance(labeling, QgsRuleBasedLabeling):
                root = labeling.rootRule()
                for rule in root.children():
                    try:
                        rs = rule.settings()
                        rs.fieldName = label_field
                        rule.setSettings(rs)
                    except Exception:
                        continue
                layer.setLabeling(QgsRuleBasedLabeling(root))
            layer.setLabelsEnabled(True)
            layer.triggerRepaint()
        except Exception as e:
            log_error(f"Label style apply failed: {str(e)}")
    
    def clear_all_base_layers(self):
        """
        Remove all layers in the Base Layers group
        
        Returns:
            bool: True if successful, False otherwise
        """
        # Make sure the Base Layers group exists
        self._ensure_base_group()
        
        try:
            # Get all layers in the Base Layers group
            layer_ids = [node.layerId() for node in self.base_group.findLayers()]
            
            # Remove all layers
            self.project.removeMapLayers(layer_ids)
            
            log_info("Removed all Base Layers")
            return True
            
        except Exception as e:
            log_error(f"Error removing Base Layers: {str(e)}")
            return False
    
    def start_drawing(self, layer):
        """
        Start drawing mode for a layer
        
        Args:
            layer (QgsVectorLayer): The layer to draw on
        """
        if not layer or not layer.isValid():
            log_error("Invalid layer for drawing")
            return
        
        # Stop any existing drawing
        self.stop_drawing()
        
        # Create new drawing handler
        self.drawing_handler = DrawingHandler(layer)
        
        # Connect to drawing handler signals
        self.drawing_handler.drawing_completed.connect(self._on_drawing_completed)
        self.drawing_handler.drawing_cancelled.connect(self._on_drawing_cancelled)
        
        self.drawing_handler.start_drawing()
        log_info(f"Started drawing mode for layer: {layer.name()}")
    
    def stop_drawing(self):
        """Stop any active drawing"""
        if self.drawing_handler:
            # Disconnect signals
            try:
                self.drawing_handler.drawing_completed.disconnect(self._on_drawing_completed)
                self.drawing_handler.drawing_cancelled.disconnect(self._on_drawing_cancelled)
            except Exception:
                pass
            
            self.drawing_handler.stop_drawing()
            self.drawing_handler = None
            log_info("Stopped drawing mode")
    
    def _on_drawing_completed(self, geometry):
        """
        Handle drawing completion
        
        Args:
            geometry (QgsGeometry): The completed geometry
        """
        log_info(f"Drawing completed with area: {geometry.area():.2f} m²")
        
        # Here you can add any additional processing needed when drawing completes
        # For example, update UI elements, trigger analysis, etc.
    
    def _on_drawing_cancelled(self):
        """Handle drawing cancellation"""
        log_info("Drawing was cancelled")
        
        # Here you can add any cleanup or UI updates needed when drawing is cancelled 