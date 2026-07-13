"""
Main dialog for the BNG AI plugin
"""
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QTabWidget
from .drawing_widget import DrawingWidget

class PluginDialog(QDialog):
    """Main dialog for the BNG AI plugin"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("BNG AI Plugin")
        
        # Create main layout
        layout = QVBoxLayout()
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # Add drawing widget as a tab
        drawing_widget = DrawingWidget()
        tab_widget.addTab(drawing_widget, "Drawing Tools")
        
        # Add other tabs as needed...
        
        layout.addWidget(tab_widget)
        self.setLayout(layout)
        
    def closeEvent(self, event):
        """Handle dialog close event"""
        # Clean up any active drawing operations
        drawing_widget = self.findChild(DrawingWidget)
        if drawing_widget:
            drawing_widget.stop_drawing()
        event.accept() 