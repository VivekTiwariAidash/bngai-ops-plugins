"""
Plan layer handling functionality.
"""
from qgis.core import QgsMessageLog, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QObject, pyqtSignal
from ..gui.projects.geometry_validator import GeometryValidator
from .layer_types import LayerType, generate_layer_id

class PlanLayerHandler(QObject):
    """Handles plan layer operations and validation."""
    
    # Define signals
    feature_validated = pyqtSignal(bool, str)  # (success, message)
    
    def __init__(self):
        """Initialize the plan layer handler."""
        super(PlanLayerHandler, self).__init__()
        self.geometry_validator = GeometryValidator()
        self.current_project_id = None
        
    def set_project_id(self, project_id):
        """
        Set the current project ID for layer management.
        
        Args:
            project_id (str): The project ID to use
        """
        self.current_project_id = project_id
        QgsMessageLog.logMessage(f"Set current project ID: {project_id}", "BNGAI Plugin", level=0)
        
    def get_rlb_layer(self):
        """
        Find the Red Line Boundary layer in the project.
        
        Returns:
            QgsVectorLayer: The RLB layer or None if not found
        """
        # Get all layers in the project
        layers = QgsProject.instance().mapLayers().values()
        
        # Find the RLB layer by checking custom properties
        for layer in layers:
            if (layer.customProperty("bngai_layer_type") == LayerType.RLB.value and 
                isinstance(layer, QgsVectorLayer) and 
                layer.isValid()):
                return layer
        
        return None
        
    def get_rlb_geometry(self):
        """
        Get the geometry of the Red Line Boundary.
        
        Returns:
            QgsGeometry: The RLB geometry or None if not found
        """
        rlb_layer = self.get_rlb_layer()
        if not rlb_layer or rlb_layer.featureCount() == 0:
            QgsMessageLog.logMessage("No RLB layer or features found", "BNGAI Plugin", level=0)
            return None
            
        # Get the first (and should be only) RLB feature
        feature = next(rlb_layer.getFeatures())
        return feature.geometry()
        
    def create_rlb_layer(self, geometry, name="Red Line Boundary"):
        """
        Create a Red Line Boundary layer with special styling
        
        Args:
            geometry (QgsGeometry): The boundary geometry
            name (str): Name for the layer
            
        Returns:
            QgsVectorLayer: Created layer or None if failed
        """
        try:
            if not self.current_project_id:
                QgsMessageLog.logMessage("No project ID set for RLB layer creation", "BNGAI Plugin", level=2)
                return None

            # Generate layer ID
            layer_id = generate_layer_id(self.current_project_id, LayerType.RLB)
            
            # Create a new vector layer
            layer = QgsVectorLayer("Polygon?crs=EPSG:4326", name, "memory")
            
            if not layer.isValid():
                QgsMessageLog.logMessage("Failed to create valid vector layer", "BNGAI Plugin", level=2)
                return None
            
            # Set custom properties
            layer.setCustomProperty("bngai_layer_type", LayerType.RLB.value)
            layer.setCustomProperty("bngai_project_id", self.current_project_id)
            layer.setCustomProperty("bngai_layer_id", layer_id)
            
            # Add the geometry as a feature
            feature = QgsFeature()
            feature.setGeometry(geometry)
            
            # Add feature to layer
            layer.dataProvider().addFeatures([feature])
            layer.updateExtents()
            
            # Apply RLB styling
            self._apply_rlb_style(layer)
            
            QgsMessageLog.logMessage(f"Created RLB layer with ID: {layer_id}", "BNGAI Plugin", level=0)
            return layer
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error creating RLB layer: {str(e)}", "BNGAI Plugin", level=2)
            return None
            
    def _apply_rlb_style(self, layer):
        """
        Apply Red Line Boundary styling to a layer
        
        Args:
            layer (QgsVectorLayer): The layer to style
        """
        # Apply RLB styling here
        pass
    
    def validate_plan_feature(self, feature_geometry):
        """
        Validate a plan feature against the RLB.
        
        Args:
            feature_geometry (QgsGeometry): The geometry to validate
            
        Returns:
            tuple: (bool, QgsGeometry, str) - (success, validated_geometry, message)
        """
        try:
            # Get RLB geometry
            rlb_geometry = self.get_rlb_geometry()
            if not rlb_geometry:
                # If no RLB exists, allow the feature without validation
                message = "No Red Line Boundary found. Feature added without validation."
                QgsMessageLog.logMessage(message, "BNGAI Plugin", level=0)
                self.feature_validated.emit(True, message)
                return True, feature_geometry, message
            
            # Validate the geometry
            is_valid, clipped_geom, message = self.geometry_validator.validate_polygon_boundary(
                feature_geometry, rlb_geometry
            )
            
            # Emit validation result
            self.feature_validated.emit(is_valid, message)
            
            return is_valid, clipped_geom, message
            
        except Exception as e:
            message = f"Error validating plan feature: {str(e)}"
            QgsMessageLog.logMessage(message, "BNGAI Plugin", level=2)
            self.feature_validated.emit(False, message)
            return False, None, message 