"""
BNG AI Dock Widget - Dockable panel for BNG AI plugin functionality
"""
from qgis.PyQt.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QTabWidget, 
                               QLabel, QPushButton, QMessageBox)
from qgis.PyQt.QtCore import Qt, pyqtSignal, QSettings, QSize
from qgis.core import QgsMessageLog

from ..auth.auth_manager import AuthManager
from .login_tab import LoginTab
from .projects.projects_tab import ProjectsTab

class BngAiDockWidget(QDockWidget):
    """
    Main dockable widget for the BNG AI plugin
    """
    closingPlugin = pyqtSignal()
    
    def __init__(self, auth_manager, iface=None, parent=None):
        """Initialize the dock widget"""
        super(BngAiDockWidget, self).__init__(parent)
        
        # Set window title and properties
        self.setWindowTitle("BNG AI")
        self.setMinimumWidth(250)
        
        # Store reference to QGIS interface
        self.iface = iface
        
        # Store authentication manager
        self.auth_manager = auth_manager
        
        # Create main widget and layout
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.login_tab = LoginTab(self.auth_manager)
        self.projects_tab = ProjectsTab(self.auth_manager)
        
        # Set the QGIS interface for the projects tab
        if self.iface and hasattr(self.projects_tab, 'set_iface'):
            self.projects_tab.set_iface(self.iface)
        
        # Add tabs to the tab widget
        self.tab_widget.addTab(self.login_tab, "Login")
        self.tab_widget.addTab(self.projects_tab, "BNG Planning")
        
        # Add tab widget to main layout
        self.main_layout.addWidget(self.tab_widget)
        
        # Set the widget as the dockable widget
        self.setWidget(self.main_widget)
        
        # Connect signals
        self.connect_signals()
        
    @property
    def default_dock_area(self):
        """Get the default dock area"""
        return Qt.RightDockWidgetArea
    
    def on_user_logged_in(self, user_info):
        """Handle user login event"""
        # Update UI state
        self.update_ui_state(is_logged_in=True)
        
        # Set API client for the BNG Planning tab
        if hasattr(self, 'projects_tab') and self.projects_tab:
            api_client = self.auth_manager.get_api_client()
            if api_client:
                self.projects_tab.set_api_client(api_client)
        
        # Log the event
        username = user_info.get('name', 'Unknown User')
        QgsMessageLog.logMessage(f"User logged in: {username}", "BNGAI Plugin", level=0)
        
        # Switch to the BNG Planning tab after successful login
        self.tab_widget.setCurrentIndex(1)
        
    def on_user_logged_out(self):
        """Handle user logout event"""
        # Update UI state
        self.update_ui_state(is_logged_in=False)
        
        # Log the event
        QgsMessageLog.logMessage("User logged out", "BNGAI Plugin", level=0)
        
        # Switch back to the login tab
        self.tab_widget.setCurrentIndex(0)
        
    def update_ui_state(self, is_logged_in=False):
        """Update UI based on login state"""
        # Enable/disable tabs based on login state
        if hasattr(self, 'projects_tab') and self.projects_tab:
            self.projects_tab.setEnabled(is_logged_in)
        
    def closeEvent(self, event):
        """Handle close event"""
        # Emit signal to clean up resources if needed
        self.closingPlugin.emit()
        event.accept() 

    def connect_signals(self):
        """Connect signals for the dock widget"""
        self.login_tab.logged_in.connect(self.on_user_logged_in)
        self.login_tab.logged_out.connect(self.on_user_logged_out) 