"""
DrawingHandler - Module for handling drawing events and popups in QGIS
"""
from qgis.core import (QgsProject, QgsVectorLayer, QgsGeometry, 
                      QgsMessageLog, QgsWkbTypes, QgsFeature)
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.PyQt.QtCore import QObject

class DrawingHandler(QObject):
    """Handles drawing events for shapes"""
    
    def __init__(self, layer):
        """
        Initialize the drawing handler
        
        Args:
            layer (QgsVectorLayer): The target layer for drawn features
        """
        super().__init__()
        self.layer = layer
        
        # Connect to layer signals
        if self.layer and self.layer.isValid():
            QgsMessageLog.logMessage(f"Connecting to layer: {layer.name()}", "BNGAI Plugin", level=0)
            self.layer.featureAdded.connect(self.on_feature_added)
            self.layer.committedFeaturesAdded.connect(self.on_features_committed)
    
    def on_feature_added(self, fid):
        """
        Handle feature added event
        
        Args:
            fid (int): Feature ID of the added feature
        """
        QgsMessageLog.logMessage(f"New feature detected with ID: {fid}", "BNGAI Plugin", level=0)
        
        # Show simple completion message
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Drawing Completed")
        msg.setText("New feature has been added successfully!")
        msg.exec_()
    
    def on_features_committed(self, layer_id, features):
        """
        Handle committed features event
        
        Args:
            layer_id (str): ID of the layer where features were committed
            features (list): List of added features
        """
        QgsMessageLog.logMessage(f"Features committed to layer {layer_id}: {len(features)} features", "BNGAI Plugin", level=0)
        
        # Show simple completion message
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Drawing Completed")
        msg.setText("New feature has been committed successfully!")
        msg.exec_()
    
    def cleanup(self):
        """Cleanup connections"""
        if self.layer:
            try:
                self.layer.featureAdded.disconnect(self.on_feature_added)
                self.layer.committedFeaturesAdded.disconnect(self.on_features_committed)
            except:
                pass 