"""
Login Tab - Tab for user authentication and organization selection
"""
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QComboBox, QFormLayout, QGroupBox, 
                               QMessageBox, QFrame, QSizePolicy)
from qgis.PyQt.QtCore import Qt, pyqtSignal, QSettings, QCoreApplication
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.core import QgsMessageLog

class LoginTab(QWidget):
    """
    Tab for user authentication and organization selection
    """
    # Define signals
    logged_in = pyqtSignal(dict)  # Emitted when user logs in successfully, passes user info
    logged_out = pyqtSignal()     # Emitted when user logs out
    
    def __init__(self, auth_manager, parent=None):
        """Initialize the login tab"""
        super(LoginTab, self).__init__(parent)
        self.auth_manager = auth_manager
        
        # Set up the UI
        self.setup_ui()
        
        # Connect signals
        self.connect_signals()
        
        # Initialize state
        self.update_ui_state()
    
    def setup_ui(self):
        """Set up the UI elements"""
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Logo section
        self.logo_layout = QHBoxLayout()
        self.logo_label = QLabel("BNG AI Authentication")
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.logo_layout.addWidget(self.logo_label)
        self.main_layout.addLayout(self.logo_layout)
        
        # Add a separator line
        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setFrameShadow(QFrame.Sunken)
        self.main_layout.addWidget(self.separator)
        
        # Login section
        self.login_group = QGroupBox("Authentication")
        self.login_layout = QVBoxLayout()
        
        # Login info label with more detailed instructions
        self.login_info = QLabel(
            "<p>To use the BNG AI Plugin, you need to authenticate using your Auth0 account.</p>"
            "<p><b>Authentication Process:</b></p>"
            "<ol>"
            "<li>Click the <b>Login with Auth0</b> button below</li>"
            "<li>A web browser will open automatically</li>"
            "<li>Enter your credentials in the login form on the Auth0 page</li>"
            "<li>After successful authentication, the browser will redirect to a success page</li>"
            "<li>You can then close the browser and return to this plugin</li>"
            "</ol>"
            "<p><b>Important:</b> Do not close the waiting dialog until authentication is complete or you cancel login.</p>"
            "<p>The plugin uses secure OAuth 2.0 authentication with PKCE to protect your credentials.</p>"
            "<p>If you have trouble with the login process, contact your system administrator.</p>"
        )
        self.login_info.setWordWrap(True)
        self.login_info.setTextFormat(Qt.RichText)
        self.login_layout.addWidget(self.login_info)
        
        # Login status
        self.login_status = QLabel("Not logged in")
        self.login_status.setStyleSheet("font-style: italic;")
        self.login_layout.addWidget(self.login_status)
        
        # Login button layout
        self.button_layout = QHBoxLayout()
        
        # Login button
        self.login_button = QPushButton("Login with Auth0")
        self.login_button.setMinimumHeight(40)
        self.button_layout.addWidget(self.login_button)
        
        # Logout button
        self.logout_button = QPushButton("Logout")
        self.logout_button.setMinimumHeight(40)
        self.button_layout.addWidget(self.logout_button)
        
        # Add button layout
        self.login_layout.addLayout(self.button_layout)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.login_layout.addWidget(self.status_label)
        
        # Set layout for login group
        self.login_group.setLayout(self.login_layout)
        self.main_layout.addWidget(self.login_group)
    
    def connect_signals(self):
        """Connect UI signals to slots"""
        self.login_button.clicked.connect(self.login)
        self.logout_button.clicked.connect(self.logout)
        
        # Connect to auth_manager signals
        self.auth_manager.auth_changed.connect(self.on_auth_changed)
    
    def on_auth_changed(self, is_authenticated):
        """Handle authentication state changes from auth manager"""
        self.update_ui_state()
    
    def login(self):
        """Handle login button click"""
        # Update status to indicate login attempt
        self.status_label.setText("Starting Auth0 authentication...")
        self.login_status.setText("Authentication in progress...")
        QgsMessageLog.logMessage("Starting Auth0 login process", "BNGAI Plugin", level=0)
        
        # Try to log in
        try:
            # Disable login button while authenticating
            self.login_button.setEnabled(False)
            self.login_button.setText("Authenticating...")
            self.logout_button.setEnabled(False)
            
            # Process events to update UI
            QCoreApplication.processEvents()
            
            # Call Auth0 login
            self.status_label.setText("Opening authentication window...")
            success = self.auth_manager.login()
            
            # Re-enable login button
            self.login_button.setEnabled(True)
            self.login_button.setText("Login with Auth0")
            self.logout_button.setEnabled(True)
            
            if success:
                QgsMessageLog.logMessage("Auth0 login successful", "BNGAI Plugin", level=0)
                self.update_ui_state()
                
                # Show success message
                user_name = self.auth_manager.get_user_info().get('name', 'User')
                self.status_label.setText(f"Login successful! Welcome, {user_name}")
                
                # Show a brief success message (optional)
                QMessageBox.information(
                    self,
                    "Login Successful",
                    f"You have successfully logged in as {user_name}.\n\n"
                    f"You can now use the BNG AI Plugin features."
                )
                
                self.logged_in.emit(self.auth_manager.get_user_info())
            else:
                self.status_label.setText("Authentication failed or was canceled")
                self.login_status.setText("Not logged in")
                
                # Only show error message if not canceled by user
                if not self.auth_manager.login_canceled:
                    QMessageBox.warning(
                        self, 
                        "Auth0 Login Failed", 
                        "Authentication failed.\n\n"
                        "Possible reasons:\n"
                        "- Your credentials were incorrect\n"
                        "- Network connectivity issues\n"
                        "- Authentication server issues\n\n"
                        "Please try again or contact your administrator for assistance."
                    )
        except Exception as e:
            self.login_button.setEnabled(True)
            self.login_button.setText("Login with Auth0")
            self.logout_button.setEnabled(True)
            self.status_label.setText(f"Error: {str(e)}")
            self.login_status.setText("Authentication error")
            QgsMessageLog.logMessage(f"Auth0 login error: {str(e)}", "BNGAI Plugin", level=2)
            
            # Show detailed error message
            error_message = f"An error occurred during authentication:\n\n{str(e)}\n\n"
            error_message += "Troubleshooting steps:\n"
            error_message += "1. Check your internet connection\n"
            error_message += "2. Ensure the Auth0 settings are correct\n"
            error_message += "3. Try clearing your browser cookies/cache\n"
            error_message += "4. Contact your administrator if the issue persists"
            
            QMessageBox.critical(self, "Auth0 Login Error", error_message)
    
    def logout(self):
        """Handle logout button click"""
        try:
            self.auth_manager.logout()
            self.update_ui_state()
            self.logged_out.emit()
        except Exception as e:
            QgsMessageLog.logMessage(f"Logout error: {str(e)}", "BNGAI Plugin", level=2)
            QMessageBox.critical(self, "Logout Error", f"An error occurred: {str(e)}")
    
    def update_ui_state(self):
        """Update UI based on login state"""
        is_logged_in = self.auth_manager.is_logged_in()
        
        # Update button states
        self.login_button.setEnabled(not is_logged_in)
        self.logout_button.setEnabled(is_logged_in)
        
        # Update login info text
        if is_logged_in:
            self.login_info.setText("You are currently logged in. Use the logout button to sign out.")
            user_info = self.auth_manager.get_user_info()
            user_name = user_info.get('name', user_info.get('email', 'User'))
            self.login_status.setText(f"Logged in as: {user_name}")
            
            # Show saved organization if any
            current_org = self.auth_manager.get_current_organization()
            if current_org.get("name"):
                org_name = current_org.get("name")
                self.status_label.setText(f"Organization: {org_name}")
        else:
            self.login_info.setText(
                "<p>To use the BNG AI Plugin, you need to authenticate using your Auth0 account.</p>"
                "<p><b>Authentication Process:</b></p>"
                "<ol>"
                "<li>Click the <b>Login with Auth0</b> button below</li>"
                "<li>A web browser will open automatically</li>"
                "<li>Enter your credentials in the login form on the Auth0 page</li>"
                "<li>After successful authentication, the browser will redirect to a success page</li>"
                "<li>You can then close the browser and return to this plugin</li>"
                "</ol>"
                "<p><b>Important:</b> Do not close the waiting dialog until authentication is complete or you cancel login.</p>"
                "<p>The plugin uses secure OAuth 2.0 authentication with PKCE to protect your credentials.</p>"
                "<p>If you have trouble with the login process, contact your system administrator.</p>"
            )
            self.login_status.setText("Not logged in")
            self.status_label.setText("Not logged in") 