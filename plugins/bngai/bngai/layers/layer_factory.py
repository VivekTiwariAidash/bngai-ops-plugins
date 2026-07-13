"""
LayerFactory - Module for creating layers from API geometry data
"""
from qgis.core import (QgsMessageLog, QgsVectorLayer, QgsSymbol,
                      QgsSimpleLineSymbolLayer, QgsSimpleFillSymbolLayer,
                      QgsField, QgsProject)
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import Qt, QVariant
import json
from .geometry_handler import GeometryHandler
from .base_layers import BaseLayersManager
from .bng_plan_layers import BNGPlanLayersManager

class LayerFactory:
    """
    Factory class for creating QGIS layers from API geometry data
    """
    
    def __init__(self, is_baseline=True, is_boundary=False, project_id=None, plan_id=None):
        """
        Initialize the layer factory
        
        Args:
            is_baseline (bool): Whether to create baseline layers (True) or BNG Plan layers (False)
            is_boundary (bool): Whether this is a boundary layer factory
            project_id (str): Project ID for baseline layers
            plan_id (str): Plan ID for BNG plan layers
        """
        self.geometry_handler = GeometryHandler()
        self.is_baseline = is_baseline
        self.is_boundary = is_boundary
        self.project_id = project_id
        self.plan_id = plan_id
        
        QgsMessageLog.logMessage(
            f"Initialized LayerFactory with: is_baseline={is_baseline}, is_boundary={is_boundary}, "
            f"project_id={project_id}, plan_id={plan_id}", 
            "BNGAI Plugin", 
            level=0
        )
        
        # Create appropriate layer manager based on type
        if is_baseline:
            self.layer_manager = BaseLayersManager()
        else:
            self.layer_manager = BNGPlanLayersManager()

    def create_layers_from_api_data(self, geojson_data, tree_layer_name=None, watercourse_layer_name=None, plan_layer_name=None):
        """
        Create layers from API GeoJSON data
        
        Args:
            geojson_data (dict/str): GeoJSON data from API
            tree_layer_name (str): Optional custom name for tree layer
            watercourse_layer_name (str): Optional custom name for watercourse layer
            plan_layer_name (str): Optional custom name for plan layer
            
        Returns:
            dict: Dictionary of created layers {'trees': layer, 'watercourses': layer, 'plans': layer}
        """
        try:
            # Process geometries and filter by type
            filtered_geometries = self.geometry_handler.process_geometries(geojson_data)
            
            created_layers = {}
            
            # Create tree layer if we have points
            if filtered_geometries['points']:
                tree_layer = self._create_tree_layer(filtered_geometries['points'], tree_layer_name)
                if tree_layer:
                    created_layers['trees'] = tree_layer
            
            # Create watercourse layer if we have lines
            if filtered_geometries['lines']:
                watercourse_layer = self._create_watercourse_layer(filtered_geometries['lines'], watercourse_layer_name)
                if watercourse_layer:
                    created_layers['watercourses'] = watercourse_layer
            
            # Create plan layer if we have polygons
            if filtered_geometries['polygons']:
                plan_layer = self._create_plan_layer(filtered_geometries['polygons'], plan_layer_name)
                if plan_layer:
                    created_layers['plans'] = plan_layer
            
            QgsMessageLog.logMessage(
                f"Created {len(created_layers)} layers from API data", 
                "BNGAI Plugin", 
                level=0
            )
            
            return created_layers
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error creating layers from API data: {str(e)}", "BNGAI Plugin", level=2)
            return {}
    
    def _create_tree_layer(self, point_geometries, layer_name=None):
        """
        Create tree layer from point geometries
        
        Args:
            point_geometries (list): List of point geometry objects
            layer_name (str): Optional custom name for the layer
            
        Returns:
            QgsVectorLayer: Created layer or None if failed
        """
        try:
            # Use default layer name if none provided
            if not layer_name:
                layer_name = "Base Tree" if self.is_baseline else "Plan Tree"
            
            # Create the layer
            if self.is_baseline:
                layer = self.layer_manager.create_tree_layer(name=layer_name)
            else:
                layer = self.layer_manager.create_tree_layer(name=layer_name)
            
            if not layer:
                return None
            
            # Get the appropriate attributes
            attributes = self.layer_manager.tree_attributes
            
            # Prepare features for the layer
            features = self.geometry_handler.prepare_features_for_layer(
                point_geometries, 
                attributes=attributes,
                geometry_type='points'
            )
            
            # Add features to the layer
            if features:
                data_provider = layer.dataProvider()
                data_provider.addFeatures(features)
                layer.updateExtents()
                
                # Add custom properties
                self._set_layer_variables(layer, 'point')
                
                # Make sure the layer is added to the project
                if not QgsProject.instance().mapLayer(layer.id()):
                    QgsProject.instance().addMapLayer(layer)
                
                # Ensure the layer is visible
                root = QgsProject.instance().layerTreeRoot()
                tree_layer = root.findLayer(layer.id())
                if tree_layer:
                    tree_layer.setItemVisibilityChecked(True)
                    # Collapse legend/styling by default
                    try:
                        tree_layer.setExpanded(False)
                    except Exception:
                        pass
                    # Enable feature count in legend
                    try:
                        layer.setCustomProperty("showFeatureCount", True)
                    except Exception:
                        pass
                    try:
                        tree_layer.setCustomProperty("showFeatureCount", True)
                    except Exception:
                        pass
                
                layer.triggerRepaint()
            
            QgsMessageLog.logMessage(f"Added {len(features)} trees to layer", "BNGAI Plugin", level=0)
            return layer
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error creating tree layer: {str(e)}", "BNGAI Plugin", level=2)
            return None
    
    def _create_watercourse_layer(self, line_geometries, layer_name=None):
        """
        Create watercourse layer from line geometries
        
        Args:
            line_geometries (list): List of line geometry objects
            layer_name (str): Optional custom name for the layer
            
        Returns:
            QgsVectorLayer: Created layer or None if failed
        """
        try:
            # Use default layer name if none provided
            if not layer_name:
                layer_name = "Base Watercourse/Hedgerow" if self.is_baseline else "BNG Plan Watercourse/Hedgerow"
            
            # Create the layer
            if self.is_baseline:
                layer = self.layer_manager.create_watercourse_layer(name=layer_name)
            else:
                layer = self.layer_manager.create_watercourse_layer(name=layer_name)
            
            if not layer:
                return None
            
            # Get the appropriate attributes
            attributes = self.layer_manager.watercourse_attributes
            
            # Prepare features for the layer
            features = self.geometry_handler.prepare_features_for_layer(
                line_geometries, 
                attributes=attributes,
                geometry_type='lines'
            )
            
            # Add features to the layer
            if features:
                data_provider = layer.dataProvider()
                data_provider.addFeatures(features)
                layer.updateExtents()
                
                # Add custom properties
                self._set_layer_variables(layer, 'line')
                
                # Make sure the layer is added to the project
                if not QgsProject.instance().mapLayer(layer.id()):
                    QgsProject.instance().addMapLayer(layer)
                
                # Ensure the layer is visible
                root = QgsProject.instance().layerTreeRoot()
                tree_layer = root.findLayer(layer.id())
                if tree_layer:
                    tree_layer.setItemVisibilityChecked(True)
                    # Enable feature count in legend
                    try:
                        layer.setCustomProperty("showFeatureCount", True)
                    except Exception:
                        pass
                    try:
                        tree_layer.setCustomProperty("showFeatureCount", True)
                    except Exception:
                        pass
                
                layer.triggerRepaint()
            
            QgsMessageLog.logMessage(f"Added {len(features)} watercourses to layer", "BNGAI Plugin", level=0)
            return layer
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error creating watercourse layer: {str(e)}", "BNGAI Plugin", level=2)
            return None
    
    def _create_plan_layer(self, polygon_geometries, layer_name=None):
        """
        Create plan layer from polygon geometries
        
        Args:
            polygon_geometries (list): List of polygon geometry objects
            layer_name (str): Optional custom name for the layer
            
        Returns:
            QgsVectorLayer: Created layer or None if failed
        """
        try:
            # Use default layer name if none provided
            if not layer_name:
                layer_name = "Base Polygon" if self.is_baseline else "Plan Polygon"
            
            # Create the layer
            if self.is_baseline:
                layer = self.layer_manager.create_plan_layer(name=layer_name)
            else:
                layer = self.layer_manager.create_plan_layer(name=layer_name)
            
            if not layer:
                return None
            
            # Get the appropriate attributes
            attributes = self.layer_manager.plan_attributes
            
            # Prepare features for the layer
            features = self.geometry_handler.prepare_features_for_layer(
                polygon_geometries, 
                attributes=attributes,
                geometry_type='polygons'
            )
            
            # Add features to the layer
            if features:
                data_provider = layer.dataProvider()
                data_provider.addFeatures(features)
                layer.updateExtents()
                
                # Add custom properties
                self._set_layer_variables(layer, 'polygon')
                
                # Re-apply editor widgets to ensure dropdowns on plan fields
                if not self.is_baseline:
                    try:
                        layer.startEditing()
                        self.layer_manager._configure_field_value_maps(layer)
                        layer.commitChanges()
                    except Exception:
                        pass
                
                # Make sure the layer is added to the project
                if not QgsProject.instance().mapLayer(layer.id()):
                    QgsProject.instance().addMapLayer(layer)
                
                # Ensure the layer is visible
                root = QgsProject.instance().layerTreeRoot()
                tree_layer = root.findLayer(layer.id())
                if tree_layer:
                    tree_layer.setItemVisibilityChecked(True)
                    # Enable feature count in legend
                    try:
                        layer.setCustomProperty("showFeatureCount", True)
                    except Exception:
                        pass
                    try:
                        tree_layer.setCustomProperty("showFeatureCount", True)
                    except Exception:
                        pass
                
                layer.triggerRepaint()
            
            QgsMessageLog.logMessage(f"Added {len(features)} polygons to layer", "BNGAI Plugin", level=0)
            return layer
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error creating plan layer: {str(e)}", "BNGAI Plugin", level=2)
            return None
    
    def _create_boundary_layer(self, geometry, layer_name="Red Line Boundary"):
        """
        Create a Red Line Boundary layer with special styling
        
        Args:
            geometry (dict): GeoJSON geometry object
            layer_name (str): Name for the layer
            
        Returns:
            QgsVectorLayer: Created layer or None if failed
        """
        try:
            # Log incoming geometry
            QgsMessageLog.logMessage(f"Creating boundary layer with geometry: {json.dumps(geometry)}", "BNGAI Plugin", level=0)
            
            # Always use canonical RLB layer name expected by spatial validation
            # See utils/plan_spatial_validation.py (_find_rlb_layer)
            canonical_name = "Red Line Boundary"
            # Create a new vector layer
            layer = QgsVectorLayer("Polygon?crs=EPSG:4326", canonical_name, "memory")
            
            if not layer.isValid():
                QgsMessageLog.logMessage("Failed to create valid vector layer", "BNGAI Plugin", level=2)
                return None
            
            # Define attributes with proper types
            attributes = [
                ("type", QVariant.String),
                ("name", QVariant.String)
            ]
            
            # Add fields for properties
            provider = layer.dataProvider()
            provider.addAttributes([
                QgsField(name, field_type) 
                for name, field_type in attributes
            ])
            layer.updateFields()
            
            # Create a feature collection with the boundary geometry
            boundary_feature = {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "type": "RLB",
                    "name": "Red Line Boundary"
                }
            }
            
            QgsMessageLog.logMessage(f"Created boundary feature: {json.dumps(boundary_feature)}", "BNGAI Plugin", level=0)
            
            # Prepare features for the layer using geometry handler
            features = self.geometry_handler.prepare_features_for_layer(
                [boundary_feature],
                attributes=attributes,
                geometry_type='polygons'
            )
            
            QgsMessageLog.logMessage(f"Prepared {len(features) if features else 0} features", "BNGAI Plugin", level=0)
            
            # Add features to the layer
            if features:
                provider.addFeatures(features)
                layer.updateExtents()
            else:
                QgsMessageLog.logMessage("No features were created", "BNGAI Plugin", level=2)
                return None
            
            # Set layer style
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            
            # Create fill symbol layer (transparent fill)
            fill_layer = QgsSimpleFillSymbolLayer()
            fill_layer.setColor(QColor(255, 0, 0, 30))  # Semi-transparent red
            fill_layer.setStrokeStyle(Qt.NoPen)  # No stroke for fill
            
            # Create line symbol layer for the boundary
            line_layer = QgsSimpleLineSymbolLayer()
            line_layer.setColor(QColor(255, 0, 0))  # Red color
            line_layer.setWidth(3)  # Increased line width for better visibility
            line_layer.setPenStyle(Qt.SolidLine)
            
            # Create the symbol and add layers
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            symbol.deleteSymbolLayer(0)  # Remove default symbol layer
            symbol.appendSymbolLayer(fill_layer)
            symbol.appendSymbolLayer(line_layer)
            
            # Apply symbol to layer
            layer.renderer().setSymbol(symbol)
            
            # Set layer properties
            layer.setOpacity(1.0)  # Ensure full opacity
            # Mark layer for discoverability if naming ever changes
            layer.setCustomProperty("bngai_is_rlb", True)
            layer.triggerRepaint()
            
            QgsMessageLog.logMessage("Created Red Line Boundary layer successfully", "BNGAI Plugin", level=0)
            return layer
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error creating boundary layer: {str(e)}", "BNGAI Plugin", level=2)
            import traceback
            QgsMessageLog.logMessage(f"Error traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            return None

    def process_api_response(self, api_response):
        """
        Process an API response and create layers
        
        Args:
            api_response (dict/str): API response containing geometry data
            
        Returns:
            dict: Dictionary of created layers
        """
        try:
            if isinstance(api_response, str):
                api_response = json.loads(api_response)
            
            if not isinstance(api_response, dict):
                QgsMessageLog.logMessage("Invalid API response format", "BNGAI Plugin", level=2)
                return {}
            
            # If this is a boundary layer factory, create boundary layer
            if self.is_boundary and "features" in api_response:
                QgsMessageLog.logMessage(f"Processing boundary layer with {len(api_response['features'])} features", "BNGAI Plugin", level=0)
                
                for feature in api_response["features"]:
                    QgsMessageLog.logMessage(f"Processing feature with properties: {json.dumps(feature.get('properties', {}))}", "BNGAI Plugin", level=0)
                    
                    if feature.get("properties", {}).get("type") == "RLB":
                        QgsMessageLog.logMessage("Found RLB feature, creating boundary layer", "BNGAI Plugin", level=0)
                        boundary_layer = self._create_boundary_layer(feature["geometry"])
                        
                        if boundary_layer and boundary_layer.isValid():
                            QgsMessageLog.logMessage("Successfully created boundary layer", "BNGAI Plugin", level=0)
                            # Add layer to QGIS project
                            QgsProject.instance().addMapLayer(boundary_layer)
                            return {"Red Line Boundary": boundary_layer}
                        else:
                            QgsMessageLog.logMessage("Failed to create valid boundary layer", "BNGAI Plugin", level=2)
                
                QgsMessageLog.logMessage("No valid RLB features found", "BNGAI Plugin", level=2)
                return {}
            
            # Otherwise create normal layers
            return self.create_layers_from_api_data(api_response)
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error processing API response: {str(e)}", "BNGAI Plugin", level=2)
            import traceback
            QgsMessageLog.logMessage(f"Error traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            return {}

    def _set_layer_variables(self, layer, geometry_type):
        """
        Set custom variables for the layer
        
        Args:
            layer (QgsVectorLayer): Layer to set variables for
            geometry_type (str): Type of geometry ('tree', 'line', 'polygon')
        """
        if layer:
            prefix = "base" if self.is_baseline else "plan"
            if self.is_baseline:
                id_value = f"{self.project_id}_{prefix}_{geometry_type}"
            else:
                id_value = f"{self.plan_id}_{prefix}_{geometry_type}"
            
            # Use setCustomProperty instead of setLayerVariable
            layer.setCustomProperty("bngai_id", id_value)
            layer.setCustomProperty("bngai_type", prefix)
            layer.setCustomProperty("is_baseline", self.is_baseline)  # Add is_baseline property
            QgsMessageLog.logMessage(f"Set layer custom properties - bngai_id: {id_value}, bngai_type: {prefix}, is_baseline: {self.is_baseline}", "BNGAI Plugin", level=0) 