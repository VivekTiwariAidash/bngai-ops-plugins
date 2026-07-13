"""
DrawingWidget - Widget for handling drawing functionality in the BNG AI plugin
"""
from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QLabel
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsMessageLog, QgsProject
from qgis.utils import iface
from ..layers.drawing_handler import DrawingHandler

class DrawingWidget(QWidget):
    """Widget for managing drawing operations"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.drawing_handler = None
        self.setup_ui()
        
        # Connect to layer changes
        QgsProject.instance().layersAdded.connect(self.on_layers_changed)
        QgsProject.instance().layersRemoved.connect(self.on_layers_changed)
        
    def setup_ui(self):
        """Setup the widget UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        # Instructions section
        instructions = QLabel(
            "<b>Drawing Instructions:</b><br>"
            "1. Use QGIS's native drawing tools from the toolbar<br>"
            "2. Select the appropriate drawing tool (point, line, or polygon)<br>"
            "3. Draw your feature on the map<br>"
            "4. A confirmation message will appear when done"
        )
        instructions.setAlignment(Qt.AlignLeft)
        instructions.setWordWrap(True)
        instructions.setStyleSheet("padding: 5px; background-color: #f0f0f0; border-radius: 3px;")
        layout.addWidget(instructions)
        
        # Status label
        self.status_label = QLabel("No active layer")
        self.status_label.setAlignment(Qt.AlignLeft)
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        # Initialize UI state
        self.update_ui_state()
    
    def on_layers_changed(self):
        """Handle changes in the layer list"""
        try:
            # Get the active layer
            active_layer = iface.activeLayer()
            
            # Clean up existing handler
            if self.drawing_handler:
                self.drawing_handler.cleanup()
                self.drawing_handler = None
            
            # Set up new handler if we have a valid layer
            if active_layer and active_layer.isValid():
                QgsMessageLog.logMessage(f"Active layer: {active_layer.name()}", "BNGAI Plugin", level=0)
                self.drawing_handler = DrawingHandler(active_layer)
                self.status_label.setText(f"Active layer: {active_layer.name()}")
            else:
                QgsMessageLog.logMessage("No active layer", "BNGAI Plugin", level=0)
                self.status_label.setText("No active layer")
            
            # Update UI state
            self.update_ui_state()
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error in on_layers_changed: {str(e)}", "BNGAI Plugin", level=2)
            self.status_label.setText("Error updating layer state")
    
    def update_ui_state(self):
        """Update the UI state based on current conditions"""
        try:
            active_layer = iface.activeLayer()
            if active_layer and active_layer.isValid():
                self.setEnabled(True)
            else:
                self.setEnabled(False)
        except Exception as e:
            QgsMessageLog.logMessage(f"Error in update_ui_state: {str(e)}", "BNGAI Plugin", level=2)
            self.setEnabled(False)
    
    def cleanup(self):
        """Cleanup resources"""
        if self.drawing_handler:
            self.drawing_handler.cleanup()
            self.drawing_handler = None
            
        # Disconnect signals
        try:
            QgsProject.instance().layersAdded.disconnect(self.on_layers_changed)
            QgsProject.instance().layersRemoved.disconnect(self.on_layers_changed)
        except:
            pass 