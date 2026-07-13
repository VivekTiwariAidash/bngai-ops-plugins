"""
Authentication Manager - Handles user authentication and session management with Auth0
"""
import os
import json
import requests
import webbrowser
import base64
import hashlib
import secrets
import time
import threading
import socket
import http.server
import socketserver
from urllib.parse import urlencode, parse_qs, urlparse
from threading import Thread

from qgis.core import QgsMessageLog
from qgis.PyQt.QtCore import QObject, pyqtSignal, QSettings, QUrl, QEventLoop, QTimer, Qt
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                                QDialogButtonBox, QFrame, QInputDialog, QMessageBox, QLineEdit, QCheckBox,
                                QProgressBar)
from qgis.PyQt.QtGui import QDesktopServices
from ..utils.api_config import ApiConfig
import traceback

# Try to import WebKit components
try:
    from qgis.PyQt.QtWebKitWidgets import QWebView
    from qgis.PyQt.QtWebKit import QWebPage
    WEBKIT_AVAILABLE = True
except ImportError:
    WEBKIT_AVAILABLE = False
    QgsMessageLog.logMessage("QtWebKit not available, checking WebEngine", "BNGAI Plugin", level=1)

# Try to import WebEngine components as alternative
try:
    from qgis.PyQt.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
    from qgis.PyQt.QtWebEngineCore import QWebEngineUrlRequestInterceptor
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False
    QgsMessageLog.logMessage("QtWebEngine not available, will use fallback methods", "BNGAI Plugin", level=1)

# Global variable to store authorization code from callback
AUTH_CODE = None
AUTH_CODE_RECEIVED = False

# Simple HTTP server to handle the OAuth callback
class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to avoid printing logs to stderr
        QgsMessageLog.logMessage(f"CallbackHandler: {format % args}", "BNGAI Plugin", level=0)
        
    def do_GET(self):
        """Handle GET request to the callback URL"""
        global AUTH_CODE, AUTH_CODE_RECEIVED

        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        try:
            if path != "/login":
                self.send_response(204)
                self.end_headers()
                return

            if AUTH_CODE_RECEIVED:
                self._send_success_page()
                return

            query = parse_qs(parsed.query)

            if 'code' in query:
                AUTH_CODE = query['code'][0]
                AUTH_CODE_RECEIVED = True
                self._send_success_page()
                QgsMessageLog.logMessage(
                    f"Received authorization code: {AUTH_CODE[:5]}...",
                    "BNGAI Plugin", level=0,
                )
            else:
                self._send_waiting_page()
                QgsMessageLog.logMessage(
                    "Callback hit without authorization code — waiting for redirect",
                    "BNGAI Plugin", level=1,
                )

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(
                f"<h1>Server Error</h1><p>{e}</p>".encode('utf-8')
            )
            QgsMessageLog.logMessage(
                f"Error in callback handler: {e}", "BNGAI Plugin", level=2,
            )

    def _send_success_page(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"""
            <html><head><title>Authentication Successful</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 40px; }
                .success { color: #4CAF50; font-size: 24px; margin-bottom: 20px; }
                .info { margin-bottom: 30px; }
            </style></head><body>
                <h1 class="success">Authentication Successful!</h1>
                <p class="info">You can close this window and return to QGIS.</p>
                <script>setTimeout(function(){ window.close(); }, 3000);</script>
            </body></html>""")

    def _send_waiting_page(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"""
            <html><head><title>Waiting for authentication</title>
            <meta http-equiv="refresh" content="2">
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 40px; }
                .info { color: #0066cc; font-size: 20px; }
            </style></head><body>
                <h1 class="info">Waiting for authentication...</h1>
                <p>This page will refresh automatically. Please complete login in the Auth0 page.</p>
            </body></html>""")

# URL interceptor for WebEngine
if WEBENGINE_AVAILABLE:
    class URLInterceptor(QWebEngineUrlRequestInterceptor):
        def __init__(self, parent=None):
            super(URLInterceptor, self).__init__(parent)
            self.code = None
            self.code_received = False
            
        def interceptRequest(self, info):
            url = info.requestUrl().toString()
            if "code=" in url:
                QgsMessageLog.logMessage(f"Intercepted URL with code: {url}", "BNGAI Plugin", level=0)
                
                query = parse_qs(urlparse(url).query)
                if 'code' in query:
                    self.code = query['code'][0]
                    self.code_received = True

# Web view dialog for Auth0 login
class WebViewLoginDialog(QDialog):
    def __init__(self, auth_url, redirect_uri, parent=None):
        super(WebViewLoginDialog, self).__init__(parent)
        self.auth_url = auth_url
        self.redirect_uri = redirect_uri
        self.authorization_code = None
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Auth0 Login")
        self.resize(900, 700)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Info label
        info_label = QLabel(
            "<h3>Auth0 Authentication</h3>"
            "<p>Please log in with your Auth0 credentials in the window below.</p>"
            "<p>After successful authentication, the window will close automatically.</p>"
        )
        info_label.setWordWrap(True)
        info_label.setTextFormat(Qt.RichText)
        layout.addWidget(info_label)
        
        # Loading indicator
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate progress
        layout.addWidget(self.progress)
        
        # Status label
        self.status_label = QLabel("Loading login page...")
        layout.addWidget(self.status_label)
        
        # Create the web view based on available framework
        if WEBENGINE_AVAILABLE:
            self.web_view = QWebEngineView()
            self.url_interceptor = URLInterceptor()
            
            # Function to update status on loading
            def update_loading_status(loading):
                if loading:
                    self.status_label.setText("Loading page...")
                    self.progress.setRange(0, 0)
                else:
                    self.status_label.setText("Page loaded. Please log in.")
                    self.progress.setRange(0, 100)
                    self.progress.setValue(100)
            
            self.web_view.loadStarted.connect(lambda: update_loading_status(True))
            self.web_view.loadFinished.connect(lambda: update_loading_status(False))
            
            self.web_view.load(QUrl(self.auth_url))
        elif WEBKIT_AVAILABLE:
            self.web_view = QWebView()
            
            # Function to update status on loading
            def update_loading_status(loading):
                if loading:
                    self.status_label.setText("Loading page...")
                    self.progress.setRange(0, 0)
                else:
                    self.status_label.setText("Page loaded. Please log in.")
                    self.progress.setRange(0, 100)
                    self.progress.setValue(100)
            
            self.web_view.loadStarted.connect(lambda: update_loading_status(True))
            self.web_view.loadFinished.connect(lambda: update_loading_status(False))
            
            # Set up URL interception
            frame = self.web_view.page().mainFrame()
            
            def url_changed(url):
                url_str = url.toString()
                if "code=" in url_str:
                    QgsMessageLog.logMessage(f"Intercepted URL: {url_str}", "BNGAI Plugin", level=0)
                    query = parse_qs(urlparse(url_str).query)
                    if 'code' in query:
                        self.authorization_code = query['code'][0]
                        # Show success message
                        self.web_view.setHtml("""
                        <html>
                        <head>
                            <title>Authentication Successful</title>
                            <style>
                                body { font-family: Arial, sans-serif; text-align: center; padding: 40px; }
                                .success { color: #4CAF50; font-size: 24px; margin-bottom: 20px; }
                                .info { margin-bottom: 30px; }
                            </style>
                        </head>
                        <body>
                            <h1 class="success">Authentication Successful!</h1>
                            <p class="info">You have successfully authenticated with Auth0.</p>
                            <p class="info">This window will close automatically.</p>
                        </body>
                        </html>
                        """)
                        # After a short delay, accept the dialog to close it
                        QTimer.singleShot(2000, self.accept)
            
            self.web_view.urlChanged.connect(url_changed)
            self.web_view.load(QUrl(self.auth_url))
        else:
            # Fallback for when no web view is available
            self.web_view = QLabel("No web view available. Please authenticate in your browser.")
        
        # Add web view to layout
        layout.addWidget(self.web_view)
        
        # Cancel button
        button_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_authorization_code(self):
        if WEBENGINE_AVAILABLE:
            return self.url_interceptor.code
        else:
            return self.authorization_code


class AuthManager(QObject):
    """
    Manages user authentication and session for the BNG AI Plugin using Auth0
    """
    # Define signals
    auth_changed = pyqtSignal(bool)
    
    def __init__(self):
        """Initialize the authentication manager"""
        super(AuthManager, self).__init__()
        
        # Settings for storing configuration
        self.settings = QSettings()
        self.settings_prefix = "BNGAI/auth/"
        self.settings_config_prefix = "BNGAI/settings/"
        
        # Auth0 configuration sourced from ApiConfig
        self.domain = ApiConfig.get_auth0_domain()
        self.client_id = ApiConfig.get_auth0_client_id()
        self.audience = ApiConfig.get_auth0_audience()
        self.scope = "openid profile email offline_access"
        
        # Set localhost port for callback - use allowed ports from Auth0 config
        self.allowed_callback_ports = [5000, 8080, 5454, 3000, 5001]
        self.callback_port = self.allowed_callback_ports[0]  # Start with first port
        self.redirect_uri = f"http://localhost:{self.callback_port}/login"
        
        # User data
        self.user_token = None
        self.access_token = None
        self.id_token = None
        self.refresh_token = None
        self.user_info = None
        self.token_expiry = None
        self.current_org_id = None
        self.current_org_name = None
        self.login_canceled = False  # Flag to track if login was canceled by user
        
        # Try to load saved token
        self._load_saved_auth()
        
        QgsMessageLog.logMessage(f"Auth Manager initialized with domain: {self.domain}", "BNGAI Plugin", level=0)
        QgsMessageLog.logMessage(f"Using redirect URI: {self.redirect_uri}", "BNGAI Plugin", level=0)
        QgsMessageLog.logMessage(f"Allowed callback ports: {self.allowed_callback_ports}", "BNGAI Plugin", level=0)
    
    def login(self):
        """
        Authenticate user with Auth0 using Authorization Code flow with PKCE
        Returns True if login is successful, False otherwise
        """
        try:
            # Reset the login_canceled flag
            self.login_canceled = False
            
            QgsMessageLog.logMessage("Starting Auth0 authentication", "BNGAI Plugin", level=0)
            
            # Generate code verifier and challenge for PKCE
            code_verifier = secrets.token_urlsafe(64)
            code_verifier_bytes = code_verifier.encode('ascii')
            code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier_bytes).digest()).decode('ascii').rstrip('=')
            
            # Generate random state for CSRF protection
            state = secrets.token_urlsafe(32)
            
            # Create Auth0 authorization URL with the configured redirect URI
            auth_url = f"https://{self.domain}/authorize?"
            auth_params = {
                'response_type': 'code',
                'client_id': self.client_id,
                'redirect_uri': self.redirect_uri,
                'scope': self.scope,
                'state': state,
                'code_challenge': code_challenge,
                'code_challenge_method': 'S256',
                'audience': self.audience
            }
            
            auth_url += urlencode(auth_params)
            QgsMessageLog.logMessage(f"Auth URL: {auth_url}", "BNGAI Plugin", level=0)
            
            # Decide which authentication method to use
            auth_code = None
            
            if WEBENGINE_AVAILABLE or WEBKIT_AVAILABLE:
                # Use web view dialog
                QgsMessageLog.logMessage("Using WebView for authentication", "BNGAI Plugin", level=0)
                web_dialog = WebViewLoginDialog(auth_url, self.redirect_uri)
                result = web_dialog.exec_()
                
                if result == QDialog.Accepted and web_dialog.get_authorization_code():
                    auth_code = web_dialog.get_authorization_code()
                    QgsMessageLog.logMessage(f"Authentication successful, code received: {auth_code[:5]}...", "BNGAI Plugin", level=0)
                elif result == QDialog.Rejected:
                    QgsMessageLog.logMessage("Authentication canceled by user", "BNGAI Plugin", level=1)
                    self.login_canceled = True
                    return False
            else:
                # Use local HTTP server to handle callback
                QgsMessageLog.logMessage("Using local HTTP server for authentication callback", "BNGAI Plugin", level=0)
                
                # Reset global variables
                global AUTH_CODE, AUTH_CODE_RECEIVED
                AUTH_CODE = None
                AUTH_CODE_RECEIVED = False
                
                # Start local HTTP server to handle the callback
                try:
                    # Find an available port from our allowed list
                    port = None
                    httpd = None
                    
                    # Try each of our allowed ports
                    for attempt_port in self.allowed_callback_ports:
                        try:
                            QgsMessageLog.logMessage(f"Attempting to use port {attempt_port} for callback", "BNGAI Plugin", level=0)
                            httpd = socketserver.TCPServer(("localhost", attempt_port), CallbackHandler)
                            port = attempt_port
                            QgsMessageLog.logMessage(f"Successfully bound to port {port}", "BNGAI Plugin", level=0)
                            break
                        except OSError as e:
                            QgsMessageLog.logMessage(f"Port {attempt_port} unavailable: {str(e)}", "BNGAI Plugin", level=1)
                            continue
                    
                    if httpd is None:
                        raise RuntimeError("Could not find an available port for callback server from the allowed list")
                    
                    # Update redirect_uri with the actual port
                    if port != self.callback_port:
                        self.redirect_uri = f"http://localhost:{port}/login"
                        # Update auth URL with new redirect URI
                        auth_params['redirect_uri'] = self.redirect_uri
                        auth_url = f"https://{self.domain}/authorize?" + urlencode(auth_params)
                        QgsMessageLog.logMessage(f"Updated redirect URI to: {self.redirect_uri}", "BNGAI Plugin", level=0)
                    
                    # Start server in a separate thread
                    server_thread = Thread(target=httpd.serve_forever)
                    server_thread.daemon = True
                    server_thread.start()
                    
                    QgsMessageLog.logMessage(f"HTTP server started on port {port}", "BNGAI Plugin", level=0)
                    
                    # Open browser
                    QDesktopServices.openUrl(QUrl(auth_url))
                    
                    # Show a dialog to wait for authentication
                    wait_dialog = QDialog()
                    wait_dialog.setWindowTitle("Waiting for Authentication")
                    wait_dialog.setFixedSize(500, 250)
                    
                    wait_layout = QVBoxLayout(wait_dialog)
                    
                    # Improved wait message
                    wait_label = QLabel(
                        "<h3>Authentication in Progress</h3>"
                        "<p>A browser window has opened for you to log in with Auth0.</p>"
                        "<p><b>Please complete these steps:</b></p>"
                        "<ol>"
                        "<li>Enter your credentials in the browser</li>"
                        "<li>Authorize the application when prompted</li>"
                        "<li>Wait for the success page to appear</li>"
                        "</ol>"
                        "<p>This dialog will close automatically when authentication is complete.</p>"
                        "<p><b>Do not close this dialog</b> until you complete authentication or click Cancel.</p>"
                    )
                    wait_label.setWordWrap(True)
                    wait_label.setTextFormat(Qt.RichText)
                    wait_layout.addWidget(wait_label)
                    
                    # Status label to update during the process
                    status_label = QLabel("Waiting for authentication...")
                    status_label.setAlignment(Qt.AlignCenter)
                    status_label.setStyleSheet("color: #0066cc; font-weight: bold;")
                    wait_layout.addWidget(status_label)
                    
                    progress = QProgressBar()
                    progress.setRange(0, 0)  # Indeterminate progress
                    wait_layout.addWidget(progress)
                    
                    cancel_button = QPushButton("Cancel")
                    cancel_button.clicked.connect(wait_dialog.reject)
                    wait_layout.addWidget(cancel_button)
                    
                    # Function to check for auth code while dialog is open
                    def check_auth_code():
                        global AUTH_CODE_RECEIVED
                        if AUTH_CODE_RECEIVED:
                            status_label.setText("Authentication successful! Redirecting...")
                            status_label.setStyleSheet("color: green; font-weight: bold;")
                            QTimer.singleShot(1000, wait_dialog.accept)  # Give user time to see success message
                    
                    # Function to update status messages periodically
                    waiting_messages = [
                        "Waiting for authentication...",
                        "Please complete the login in your browser...",
                        "Enter your credentials in the Auth0 page...",
                        "Still waiting for authentication...",
                        "Please finish the login process in the browser...",
                        "Waiting for browser redirect..."
                    ]
                    message_index = 0
                    
                    def update_status():
                        nonlocal message_index
                        status_label.setText(waiting_messages[message_index % len(waiting_messages)])
                        message_index += 1
                    
                    # Set up timer to check for auth code
                    timer = QTimer()
                    timer.timeout.connect(check_auth_code)
                    timer.start(500)  # Check every 500ms
                    
                    # Set up timer for status updates
                    status_timer = QTimer()
                    status_timer.timeout.connect(update_status)
                    status_timer.start(3000)  # Update every 3 seconds
                    
                    # Set up timer to timeout if authentication takes too long
                    timeout_seconds = 300  # 5 minutes
                    elapsed_seconds = 0
                    
                    def check_timeout():
                        nonlocal elapsed_seconds
                        elapsed_seconds += 1
                        if elapsed_seconds >= timeout_seconds:
                            status_label.setText("Authentication timed out. Please try again.")
                            status_label.setStyleSheet("color: red; font-weight: bold;")
                            timer.stop()
                            status_timer.stop()
                            QTimer.singleShot(2000, wait_dialog.reject)  # Auto-close after timeout
                    
                    timeout_timer = QTimer()
                    timeout_timer.timeout.connect(check_timeout)
                    timeout_timer.start(1000)  # Check every second
                    
                    # Show dialog and wait for result
                    result = wait_dialog.exec_()
                    
                    # Stop all timers
                    timer.stop()
                    status_timer.stop()
                    timeout_timer.stop()
                    
                    # Shutdown server
                    httpd.shutdown()
                    server_thread.join(timeout=1.0)
                    
                    if result == QDialog.Accepted and AUTH_CODE_RECEIVED:
                        auth_code = AUTH_CODE
                        QgsMessageLog.logMessage(f"Authentication successful, code received: {auth_code[:5]}...", "BNGAI Plugin", level=0)
                    else:
                        QgsMessageLog.logMessage("Authentication canceled by user", "BNGAI Plugin", level=1)
                        self.login_canceled = True
                        return False
                        
                except Exception as server_error:
                    QgsMessageLog.logMessage(f"Error setting up HTTP server: {str(server_error)}", "BNGAI Plugin", level=2)
                    QMessageBox.critical(None, "Authentication Error", f"Could not set up authentication server: {str(server_error)}")
                    return False
            
            # If we don't have an auth code by now, authentication failed
            if not auth_code:
                QgsMessageLog.logMessage("No authorization code obtained", "BNGAI Plugin", level=2)
                return False
            
            # Exchange the authorization code for tokens
            token_url = f"https://{self.domain}/oauth/token"
            token_payload = {
                'grant_type': 'authorization_code',
                'client_id': self.client_id,
                'code_verifier': code_verifier,
                'code': auth_code,
                'redirect_uri': self.redirect_uri
            }
            
            QgsMessageLog.logMessage("Exchanging code for token", "BNGAI Plugin", level=0)
            token_headers = {'Content-Type': 'application/json'}
            token_response = requests.post(token_url, headers=token_headers, json=token_payload)
            
            if token_response.status_code == 200:
                token_data = token_response.json()
                
                # Store tokens
                self.access_token = token_data.get('access_token')
                self.id_token = token_data.get('id_token')
                self.refresh_token = token_data.get('refresh_token')
                self.token_expiry = time.time() + token_data.get('expires_in', 3600)
                self.user_token = self.access_token
                
                # Get user info
                self._fetch_user_info()
                
                # Save auth data
                self._save_auth()
                
                # Emit signal
                self.auth_changed.emit(True)
                
                QgsMessageLog.logMessage("Auth0 login successful", "BNGAI Plugin", level=0)
                return True
            else:
                error_msg = f"Failed to exchange code for token: {token_response.text}"
                QgsMessageLog.logMessage(error_msg, "BNGAI Plugin", level=2)
                QMessageBox.critical(None, "Auth0 Error", error_msg)
                return False
            
        except Exception as e:
            error_msg = f"Auth0 login error: {str(e)}\n{traceback.format_exc()}"
            QgsMessageLog.logMessage(error_msg, "BNGAI Plugin", level=2)
            QMessageBox.critical(None, "Auth0 Error", str(e))
            return False
    
    def _fetch_user_info(self):
        """Fetch user info from Auth0"""
        if not self.access_token:
            return
        
        try:
            # Call Auth0 userinfo endpoint
            response = requests.get(
                f"https://{self.domain}/userinfo",
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            
            if response.status_code == 200:
                self.user_info = response.json()
                QgsMessageLog.logMessage(f"User info retrieved: {self.user_info.get('name')}", "BNGAI Plugin", level=0)
            else:
                QgsMessageLog.logMessage(f"Failed to get user info: {response.text}", "BNGAI Plugin", level=2)
        except Exception as e:
            QgsMessageLog.logMessage(f"Error fetching user info: {str(e)}", "BNGAI Plugin", level=2)
    
    def logout(self):
        """Log out the current user"""
        # Clear tokens
        self.access_token = None
        self.id_token = None
        self.refresh_token = None
        self.token_expiry = None
        self.user_token = None
        self.user_info = None
        self.current_org_id = None
        self.current_org_name = None
        
        # Clear saved auth
        self._clear_saved_auth()
        
        # Emit signal
        self.auth_changed.emit(False)
        
        QgsMessageLog.logMessage("User logged out", "BNGAI Plugin", level=0)
        return True
    
    def is_logged_in(self):
        """Check if user is logged in"""
        # Try to refresh token if needed
        if self.access_token and self.token_expiry and time.time() > self.token_expiry:
            self._refresh_token()
        
        return self.access_token is not None
    
    def _refresh_token(self):
        """Refresh the access token"""
        if not self.refresh_token:
            return False
        
        try:
            token_url = f"https://{self.domain}/oauth/token"
            payload = {
                'grant_type': 'refresh_token',
                'client_id': self.client_id,
                'refresh_token': self.refresh_token
            }
            
            response = requests.post(token_url, json=payload)
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Update tokens
                self.access_token = token_data.get('access_token')
                if token_data.get('id_token'):
                    self.id_token = token_data.get('id_token')
                if token_data.get('refresh_token'):
                    self.refresh_token = token_data.get('refresh_token')
                
                self.token_expiry = time.time() + token_data.get('expires_in', 3600)
                self.user_token = self.access_token
                
                # Save updated tokens
                self._save_auth()
                
                QgsMessageLog.logMessage("Token refreshed successfully", "BNGAI Plugin", level=0)
                return True
            else:
                QgsMessageLog.logMessage(f"Failed to refresh token: {response.text}", "BNGAI Plugin", level=2)
                return False
        except Exception as e:
            QgsMessageLog.logMessage(f"Error refreshing token: {str(e)}", "BNGAI Plugin", level=2)
            return False
    
    def get_token(self):
        """Get the current access token (refreshing if needed)"""
        if self.is_logged_in():
            return self.access_token
        return None
    
    def get_user_info(self):
        """Get the current user's info"""
        return self.user_info or {}
    
    def force_token_refresh(self):
        """Force a token refresh regardless of expiration time
        
        Returns True if refresh was successful, False otherwise
        """
        if not self.refresh_token:
            QgsMessageLog.logMessage("Cannot refresh token: No refresh token available", "BNGAI Plugin", level=2)
            return False
            
        try:
            QgsMessageLog.logMessage("Forcing token refresh", "BNGAI Plugin", level=0)
            token_url = f"https://{self.domain}/oauth/token"
            payload = {
                'grant_type': 'refresh_token',
                'client_id': self.client_id,
                'refresh_token': self.refresh_token
            }
            
            response = requests.post(token_url, json=payload)
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Update tokens
                self.access_token = token_data.get('access_token')
                if token_data.get('id_token'):
                    self.id_token = token_data.get('id_token')
                if token_data.get('refresh_token'):
                    self.refresh_token = token_data.get('refresh_token')
                
                self.token_expiry = time.time() + token_data.get('expires_in', 3600)
                self.user_token = self.access_token
                
                # Save updated tokens
                self._save_auth()
                
                # Log preview of new token
                token_preview = self.access_token[:10] + "..." if self.access_token else "None"
                QgsMessageLog.logMessage(f"Token refreshed successfully. New token: {token_preview}", "BNGAI Plugin", level=0)
                return True
            else:
                QgsMessageLog.logMessage(f"Failed to refresh token: {response.text}", "BNGAI Plugin", level=2)
                return False
        except Exception as e:
            QgsMessageLog.logMessage(f"Error refreshing token: {str(e)}", "BNGAI Plugin", level=2)
            return False

    def get_organizations(self):
        """Get organizations for the current user"""
        if not self.is_logged_in():
            QgsMessageLog.logMessage("Cannot fetch organizations: Not logged in", "BNGAI Plugin", level=2)
            return []
            
        if not self.access_token:
            QgsMessageLog.logMessage("Cannot fetch organizations: No access token", "BNGAI Plugin", level=2)
            return []
            
        try:
            # Use the real API endpoint as shown in the curl command
            url = f"{ApiConfig.get_api_base_url()}/user/current"    
            
            # Set up headers similar to the curl command
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Authorization": self.access_token,
                "client-code": "bngai-web-client",
            }
            
            QgsMessageLog.logMessage(f"Fetching organizations from API: {url}", "BNGAI Plugin", level=0)
            
            # Make the API request
            response = requests.get(url, headers=headers)
            
            # Handle the response
            if response.status_code == 200:
                data = response.json()
                QgsMessageLog.logMessage(f"API response: {response.status_code}", "BNGAI Plugin", level=0)
                
                # Check if the response contains organizations
                if "organizations" in data:
                    orgs = data["organizations"]
                    QgsMessageLog.logMessage(f"Found {len(orgs)} organizations", "BNGAI Plugin", level=0)
                    
                    # Return a simplified list with just id and name
                    return [{"id": org["id"], "name": org["name"]} for org in orgs]
                else:
                    QgsMessageLog.logMessage("No organizations found in API response", "BNGAI Plugin", level=1)
                    return []
            else:
                QgsMessageLog.logMessage(f"Failed to fetch organizations: {response.status_code}", "BNGAI Plugin", level=2)
                
                # Try to get more error details
                try:
                    error_data = response.json()
                    QgsMessageLog.logMessage(f"API error details: {json.dumps(error_data)}", "BNGAI Plugin", level=2)
                except:
                    QgsMessageLog.logMessage(f"Raw API error response: {response.text}", "BNGAI Plugin", level=2)
                
                return []
        except Exception as e:
            QgsMessageLog.logMessage(f"Error fetching organizations: {str(e)}", "BNGAI Plugin", level=2)
            import traceback
            QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            return []
    
    def set_current_organization(self, org_id, org_name):
        """Set the current organization"""
        if not org_id or not org_name:
            return False
            
        # Store in memory
        self.current_org_id = org_id
        self.current_org_name = org_name
        
        # Save to settings for persistence
        self.settings.setValue(f"{self.settings_prefix}current_org_id", org_id)
        self.settings.setValue(f"{self.settings_prefix}current_org_name", org_name)
        
        QgsMessageLog.logMessage(f"Current organization set and saved to settings: {org_name} ({org_id})", "BNGAI Plugin", level=0)
        return True
        
    def get_current_organization(self):
        """Get the currently selected organization (id and name)"""
        # Check if we have in-memory values
        if not hasattr(self, 'current_org_id') or not self.current_org_id:
            # Try to load from settings
            self.current_org_id = self.settings.value(f"{self.settings_prefix}current_org_id", "")
            self.current_org_name = self.settings.value(f"{self.settings_prefix}current_org_name", "")
            
            if self.current_org_id:
                QgsMessageLog.logMessage(f"Loaded organization from settings: {self.current_org_name} ({self.current_org_id})", "BNGAI Plugin", level=0)
            
        # Return as dictionary for convenience
        return {
            "id": self.current_org_id or "",
            "name": self.current_org_name or ""
        }
    
    def get_api_client(self):
        """Get an API client instance configured with the current authentication"""
        if not self.is_logged_in():
            return None
            
        try:
            # Import here to avoid circular imports
            from ..gui.projects.api_client import ProjectsApiClient
            
            # Create and return a configured API client
            api_client = ProjectsApiClient(self)
            
            return api_client
        except Exception as e:
            QgsMessageLog.logMessage(f"Error creating API client: {str(e)}", "BNGAI Plugin", level=2)
            return None
    
    def _get_auth_headers(self):
        """Get the headers for authenticated API requests"""
        if self.access_token:
            return {
                "Authorization": f"Bearer {self.access_token}",  # Use correct Bearer format
                "Accept": "application/json"
            }
        return {}
    
    def _save_auth(self):
        """Save authentication data to settings"""
        self.settings.setValue(f"{self.settings_prefix}access_token", self.access_token)
        self.settings.setValue(f"{self.settings_prefix}id_token", self.id_token)
        self.settings.setValue(f"{self.settings_prefix}refresh_token", self.refresh_token)
        self.settings.setValue(f"{self.settings_prefix}token_expiry", self.token_expiry)
        
        # Save user info if available
        if self.user_info:
            self.settings.setValue(f"{self.settings_prefix}user_info", json.dumps(self.user_info))
    
    def _load_saved_auth(self):
        """Load authentication data from settings"""
        try:
            self.access_token = self.settings.value(f"{self.settings_prefix}access_token")
            self.id_token = self.settings.value(f"{self.settings_prefix}id_token")
            self.refresh_token = self.settings.value(f"{self.settings_prefix}refresh_token")
            self.token_expiry = self.settings.value(f"{self.settings_prefix}token_expiry")
            
            # Convert token_expiry to float if it's a string
            if isinstance(self.token_expiry, str):
                try:
                    self.token_expiry = float(self.token_expiry)
                except ValueError:
                    self.token_expiry = None
            
            # Set user_token to access_token
            if self.access_token:
                self.user_token = self.access_token
            
            # Load user info if available
            user_info_str = self.settings.value(f"{self.settings_prefix}user_info")
            if user_info_str:
                self.user_info = json.loads(user_info_str)
            
            # Load current organization
            self.current_org_id = self.settings.value(f"{self.settings_prefix}current_org_id")
            self.current_org_name = self.settings.value(f"{self.settings_prefix}current_org_name")
            
            # If token is expired, try to refresh it
            if self.token_expiry and time.time() > self.token_expiry:
                self._refresh_token()
            
            # If we have a valid token, emit auth_changed signal
            if self.access_token:
                self.auth_changed.emit(True)
                
            QgsMessageLog.logMessage("Loaded saved authentication data", "BNGAI Plugin", level=0)
        except Exception as e:
            QgsMessageLog.logMessage(f"Error loading saved auth: {str(e)}", "BNGAI Plugin", level=2)
    
    def _clear_saved_auth(self):
        """Clear saved authentication data from settings"""
        self.settings.remove(f"{self.settings_prefix}access_token")
        self.settings.remove(f"{self.settings_prefix}id_token")
        self.settings.remove(f"{self.settings_prefix}refresh_token")
        self.settings.remove(f"{self.settings_prefix}token_expiry")
        self.settings.remove(f"{self.settings_prefix}user_info")
        self.settings.remove(f"{self.settings_prefix}current_org_id")
        self.settings.remove(f"{self.settings_prefix}current_org_name") 