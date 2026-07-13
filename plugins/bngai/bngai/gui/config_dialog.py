"""
Configuration Dialog - Allows users to configure plugin settings
"""
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QDialogButtonBox, 
                               QFormLayout, QGroupBox, QCheckBox)
from qgis.PyQt.QtCore import Qt, QSettings
from qgis.core import QgsMessageLog

class ConfigDialog(QDialog):
    """
    Dialog for configuring plugin settings
    """
    
    def __init__(self, parent=None):
        """Initialize the configuration dialog"""
        super(ConfigDialog, self).__init__(parent)
        
        # Set window properties
        self.setWindowTitle("BNG AI Plugin Configuration")
        self.resize(500, 300)
        
        # Settings
        self.settings = QSettings()
        self.settings_prefix = "BNGAI/settings/"
        
        # Set up the UI
        self.setup_ui()
        
        # Load saved settings
        self.load_settings()
    
    def setup_ui(self):
        """Set up the UI elements"""
        # Main layout
        self.main_layout = QVBoxLayout(self)
        
        # API settings group
        self.api_group = QGroupBox("API Settings")
        self.api_layout = QFormLayout()
        
        # API base URL
        self.api_base_url = QLineEdit()
        self.api_base_url.setPlaceholderText("https://api.example.com/v1")
        self.api_layout.addRow(QLabel("API Base URL:"), self.api_base_url)
        
        # Set layout for API group
        self.api_group.setLayout(self.api_layout)
        self.main_layout.addWidget(self.api_group)
        
        # Auth0 settings group
        self.auth0_group = QGroupBox("Auth0 Settings")
        self.auth0_layout = QFormLayout()
        
        # Auth0 Domain
        self.auth0_domain = QLineEdit()
        self.auth0_domain.setPlaceholderText("dev-im8kscqw.eu.auth0.com")
        self.auth0_layout.addRow(QLabel("Auth0 Domain:"), self.auth0_domain)
        
        # Auth0 Client ID
        self.auth0_client_id = QLineEdit()
        self.auth0_client_id.setPlaceholderText("ww2XuC8nzbS4wLNGLcYzHUlcAyMlZb2n")
        self.auth0_layout.addRow(QLabel("Auth0 Client ID:"), self.auth0_client_id)
        
        # Auth0 Audience
        self.auth0_audience = QLineEdit()
        self.auth0_audience.setPlaceholderText("https://dev-im8kscqw.eu.auth0.com/api/v2/")
        self.auth0_layout.addRow(QLabel("Auth0 Audience:"), self.auth0_audience)
        
        # Set layout for Auth0 group
        self.auth0_group.setLayout(self.auth0_layout)
        self.main_layout.addWidget(self.auth0_group)
        
        # Display settings group
        self.display_group = QGroupBox("Display Settings")
        self.display_layout = QFormLayout()
        
        # Automatically refresh projects
        self.auto_refresh = QCheckBox()
        self.auto_refresh.setChecked(True)
        self.display_layout.addRow(QLabel("Auto-refresh projects:"), self.auto_refresh)
        
        # Automatically load project data
        self.auto_load = QCheckBox()
        self.auto_load.setChecked(False)
        self.display_layout.addRow(QLabel("Auto-load project data:"), self.auto_load)
        
        # Set layout for display group
        self.display_group.setLayout(self.display_layout)
        self.main_layout.addWidget(self.display_group)
        
        # Auth settings group
        self.auth_group = QGroupBox("Authentication Settings")
        self.auth_layout = QFormLayout()
        
        # Remember login
        self.remember_login = QCheckBox()
        self.remember_login.setChecked(True)
        self.auth_layout.addRow(QLabel("Remember login:"), self.remember_login)
        
        # Clear credentials button
        self.clear_button = QPushButton("Clear Saved Credentials")
        self.clear_button.clicked.connect(self.clear_credentials)
        self.auth_layout.addRow("", self.clear_button)
        
        # Set layout for auth group
        self.auth_group.setLayout(self.auth_layout)
        self.main_layout.addWidget(self.auth_group)
        
        # Add buttons at the bottom
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.main_layout.addWidget(self.button_box)
    
    def load_settings(self):
        """Load settings from QSettings"""
        # API settings
        self.api_base_url.setText(self.settings.value(f"{self.settings_prefix}api_base_url", ""))
        
        # Auth0 settings
        self.auth0_domain.setText(self.settings.value(f"{self.settings_prefix}auth0_domain", ""))
        self.auth0_client_id.setText(self.settings.value(f"{self.settings_prefix}auth0_client_id", ""))
        self.auth0_audience.setText(self.settings.value(f"{self.settings_prefix}auth0_audience", ""))
        
        # Display settings
        self.auto_refresh.setChecked(self.settings.value(f"{self.settings_prefix}auto_refresh", True, type=bool))
        self.auto_load.setChecked(self.settings.value(f"{self.settings_prefix}auto_load", False, type=bool))
        
        # Auth settings
        self.remember_login.setChecked(self.settings.value(f"{self.settings_prefix}remember_login", True, type=bool))
    
    def save_settings(self):
        """Save settings to QSettings"""
        # API settings
        self.settings.setValue(f"{self.settings_prefix}api_base_url", self.api_base_url.text())
        
        # Auth0 settings
        self.settings.setValue(f"{self.settings_prefix}auth0_domain", self.auth0_domain.text())
        self.settings.setValue(f"{self.settings_prefix}auth0_client_id", self.auth0_client_id.text())
        self.settings.setValue(f"{self.settings_prefix}auth0_audience", self.auth0_audience.text())
        
        # Display settings
        self.settings.setValue(f"{self.settings_prefix}auto_refresh", self.auto_refresh.isChecked())
        self.settings.setValue(f"{self.settings_prefix}auto_load", self.auto_load.isChecked())
        
        # Auth settings
        self.settings.setValue(f"{self.settings_prefix}remember_login", self.remember_login.isChecked())
        
        QgsMessageLog.logMessage("Plugin settings saved", "BNGAI Plugin", level=0)
    
    def clear_credentials(self):
        """Clear saved credentials"""
        self.settings.remove("BNGAI/auth/token")
        self.settings.remove("BNGAI/auth/user_info")
        self.settings.remove("BNGAI/auth/current_org_id")
        self.settings.remove("BNGAI/auth/current_org_name")
        
        QgsMessageLog.logMessage("Cleared saved credentials", "BNGAI Plugin", level=0)
    
    def accept(self):
        """Handle dialog acceptance"""
        self.save_settings()
        super(ConfigDialog, self).accept() 