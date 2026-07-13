"""
Geometry validation functionality for the projects tab.
"""
from qgis.core import QgsGeometry, QgsMessageLog, QgsWkbTypes
from qgis.PyQt.QtWidgets import QMessageBox

class GeometryValidator:
    """Handles geometry validation operations."""
    
    @staticmethod
    def validate_polygon_boundary(feature_geom, boundary_geom):
        """
        Validate if a polygon feature is within the boundary.
        
        Args:
            feature_geom (QgsGeometry): The feature geometry to validate
            boundary_geom (QgsGeometry): The boundary geometry to check against
            
        Returns:
            tuple: (bool, QgsGeometry, str) - (is_valid, clipped_geometry, message)
                  is_valid: True if geometry is valid or can be fixed
                  clipped_geometry: The clipped geometry if available, None otherwise
                  message: Description of the validation result
        """
        try:
            if not feature_geom or not boundary_geom:
                QgsMessageLog.logMessage("Invalid geometry provided", "BNGAI Plugin", level=2)
                return False, None, "Invalid geometry"
            
            # Log geometry types
            QgsMessageLog.logMessage(f"Validating geometries - Feature: {feature_geom.wkbType()}, Boundary: {boundary_geom.wkbType()}", "BNGAI Plugin", level=0)
            
            # Ensure geometries are valid
            if not feature_geom.isGeosValid():
                QgsMessageLog.logMessage("Feature geometry is not valid", "BNGAI Plugin", level=2)
                return False, None, "Feature geometry is not valid"
                
            if not boundary_geom.isGeosValid():
                QgsMessageLog.logMessage("Boundary geometry is not valid", "BNGAI Plugin", level=2)
                return False, None, "Boundary geometry is not valid"
                
            # Check if feature intersects with boundary
            if not feature_geom.intersects(boundary_geom):
                QgsMessageLog.logMessage("Feature is completely outside the boundary", "BNGAI Plugin", level=0)
                return False, None, "Feature is completely outside the boundary"
                
            # Check if feature is within boundary
            if feature_geom.within(boundary_geom):
                QgsMessageLog.logMessage("Feature is completely within boundary", "BNGAI Plugin", level=0)
                return True, feature_geom, "Feature is within boundary"
                
            # Feature overlaps boundary, calculate intersection
            QgsMessageLog.logMessage("Feature overlaps boundary, calculating intersection", "BNGAI Plugin", level=0)
            intersection = feature_geom.intersection(boundary_geom)
            
            if not intersection or intersection.isEmpty():
                QgsMessageLog.logMessage("Failed to calculate intersection", "BNGAI Plugin", level=2)
                return False, None, "Failed to calculate intersection"
                
            # Ensure the intersection is a valid polygon
            if not QgsWkbTypes.isPolygon(intersection.wkbType()):
                QgsMessageLog.logMessage(f"Intersection result is not a polygon: {intersection.wkbType()}", "BNGAI Plugin", level=2)
                return False, None, "Clipped geometry is not a valid polygon"
                
            QgsMessageLog.logMessage("Successfully calculated intersection", "BNGAI Plugin", level=0)
            return True, intersection, "Feature has been clipped to boundary"
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error validating geometry: {str(e)}", "BNGAI Plugin", level=2)
            import traceback
            QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            return False, None, f"Error validating geometry: {str(e)}"
    
    @staticmethod
    def show_validation_dialog(message):
        """
        Show a validation dialog with options to handle invalid geometry.
        
        Args:
            message (str): The validation message to display
            
        Returns:
            str: The user's choice ('clip', 'discard', or None if cancelled)
        """
        try:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("Geometry Validation")
            msg_box.setText("The feature extends outside the site boundary.")
            msg_box.setInformativeText(f"{message}\n\nHow would you like to proceed?")
            
            # Add custom buttons
            clip_button = msg_box.addButton("Clip to Boundary", QMessageBox.ActionRole)
            discard_button = msg_box.addButton("Discard Changes", QMessageBox.ActionRole)
            msg_box.addButton(QMessageBox.Cancel)
            
            msg_box.exec_()
            clicked_button = msg_box.clickedButton()
            
            QgsMessageLog.logMessage(f"Dialog result: {clicked_button}", "BNGAI Plugin", level=0)
            
            if clicked_button == clip_button:
                return 'clip'
            elif clicked_button == discard_button:
                return 'discard'
            return None
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error showing validation dialog: {str(e)}", "BNGAI Plugin", level=2)
            return None 