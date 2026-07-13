"""
MapTab - Tab for displaying map data and handling layer interactions
"""
from qgis.core import QgsMessageLog
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                                QLabel, QPushButton, QComboBox, 
                                QProgressBar, QGroupBox, QMessageBox)
from qgis.PyQt.QtCore import Qt, pyqtSlot
from .map_data_fetcher import MapDataFetcher
from ..utils.apiclient import ApiClient

class MapTab(QWidget):
    """
    Tab for displaying and interacting with map layers
    """
    
    def __init__(self, parent=None, auth_manager=None, api_client=None):
        """
        Initialize the map tab
        
        Args:
            parent: Parent widget
            auth_manager: Authentication manager instance
            api_client: API client instance
        """
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.api_client = api_client or ApiClient()
        
        # Initialize data fetcher
        self.data_fetcher = MapDataFetcher(api_client=self.api_client)
        
        # Store created layers
        self.baseline_layers = {}
        self.bng_plan_layers = {}
        
        # Setup UI
        self._setup_ui()
        
        # Connect signals
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup the user interface"""
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Plan selection section
        plan_group = QGroupBox("Plan Selection")
        plan_layout = QVBoxLayout()
        
        # Plan selector
        plan_selector_layout = QHBoxLayout()
        plan_selector_layout.addWidget(QLabel("Select Plan:"))
        self.plan_combo = QComboBox()
        self.plan_combo.setMinimumWidth(250)
        plan_selector_layout.addWidget(self.plan_combo)
        self.refresh_plans_btn = QPushButton("Refresh")
        plan_selector_layout.addWidget(self.refresh_plans_btn)
        plan_selector_layout.addStretch()
        plan_layout.addLayout(plan_selector_layout)
        
        plan_group.setLayout(plan_layout)
        main_layout.addWidget(plan_group)
        
        # Layer controls section
        layers_group = QGroupBox("Layer Controls")
        layers_layout = QVBoxLayout()
        
        # Baseline layers
        baseline_layout = QHBoxLayout()
        baseline_layout.addWidget(QLabel("Baseline Layers:"))
        self.load_baseline_btn = QPushButton("Load Baseline Layers")
        baseline_layout.addWidget(self.load_baseline_btn)
        self.clear_baseline_btn = QPushButton("Clear Baseline Layers")
        baseline_layout.addWidget(self.clear_baseline_btn)
        baseline_layout.addStretch()
        layers_layout.addLayout(baseline_layout)
        
        # BNG Plan layers
        bng_plan_layout = QHBoxLayout()
        bng_plan_layout.addWidget(QLabel("BNG Plan Layers:"))
        self.load_bng_plan_btn = QPushButton("Load BNG Plan Layers")
        bng_plan_layout.addWidget(self.load_bng_plan_btn)
        self.clear_bng_plan_btn = QPushButton("Clear BNG Plan Layers")
        bng_plan_layout.addWidget(self.clear_bng_plan_btn)
        bng_plan_layout.addStretch()
        layers_layout.addLayout(bng_plan_layout)
        
        # Net gain calculation
        net_gain_layout = QHBoxLayout()
        net_gain_layout.addWidget(QLabel("Net Gain Calculation:"))
        self.calc_net_gain_btn = QPushButton("Calculate Net Gain")
        net_gain_layout.addWidget(self.calc_net_gain_btn)
        net_gain_layout.addStretch()
        layers_layout.addLayout(net_gain_layout)
        
        # Progress bar
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        layers_layout.addLayout(progress_layout)
        
        layers_group.setLayout(layers_layout)
        main_layout.addWidget(layers_group)
        
        # Status section
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Status:"))
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        main_layout.addLayout(status_layout)
        
        # Add stretch to push everything to the top
        main_layout.addStretch()
        
        self.setLayout(main_layout)
    
    def _connect_signals(self):
        """Connect signals to slots"""
        # Button clicks
        self.refresh_plans_btn.clicked.connect(self.fetch_plans)
        self.load_baseline_btn.clicked.connect(self.load_baseline_layers)
        self.clear_baseline_btn.clicked.connect(self.clear_baseline_layers)
        self.load_bng_plan_btn.clicked.connect(self.load_bng_plan_layers)
        self.clear_bng_plan_btn.clicked.connect(self.clear_bng_plan_layers)
        self.calc_net_gain_btn.clicked.connect(self.calculate_net_gain)
        
        # Data fetcher signals
        self.data_fetcher.fetch_started.connect(self.on_fetch_started)
        self.data_fetcher.fetch_completed.connect(self.on_fetch_completed)
        self.data_fetcher.fetch_error.connect(self.on_fetch_error)
    
    @pyqtSlot()
    def fetch_plans(self):
        """Fetch available plans from API"""
        if not self.auth_manager or not self.auth_manager.is_logged_in():
            self.show_error("Please log in first")
            return
        
        self.status_label.setText("Fetching plans...")
        self.progress_bar.setVisible(True)
        
        # Get token and organization ID
        token = self.auth_manager.get_access_token()
        org_id = None
        if hasattr(self.auth_manager, 'get_current_organization'):
            org = self.auth_manager.get_current_organization()
            if org and 'id' in org:
                org_id = org['id']
        
        try:
            # Call API to get plans
            url = "plans"
            headers = {"Authorization": token}
            
            if org_id:
                headers["Organization-Id"] = org_id
            
            QgsMessageLog.logMessage("Fetching plans", "BNGAI Plugin", level=0)
            
            response = self.api_client.get(url, headers=headers)
            
            # Update plan dropdown
            self.plan_combo.clear()
            
            if response and 'data' in response and isinstance(response['data'], list):
                plans = response['data']
                for plan in plans:
                    if 'id' in plan and 'name' in plan:
                        # Store plan ID as user data
                        self.plan_combo.addItem(plan['name'], plan['id'])
            
            self.status_label.setText(f"Found {self.plan_combo.count()} plans")
            self.progress_bar.setVisible(False)
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error fetching plans: {str(e)}", "BNGAI Plugin", level=2)
            self.status_label.setText(f"Error: {str(e)}")
            self.progress_bar.setVisible(False)
    
    @pyqtSlot()
    def load_baseline_layers(self):
        """Load baseline layers for the selected plan"""
        if not self.auth_manager or not self.auth_manager.is_logged_in():
            self.show_error("Please log in first")
            return
        
        # Get selected plan ID
        if self.plan_combo.currentIndex() < 0:
            self.show_error("Please select a plan first")
            return
        
        plan_id = self.plan_combo.currentData()
        
        # Get token and organization ID
        token = self.auth_manager.get_access_token()
        org_id = None
        if hasattr(self.auth_manager, 'get_current_organization'):
            org = self.auth_manager.get_current_organization()
            if org and 'id' in org:
                org_id = org['id']
        
        # Start async data fetch
        self.data_fetcher.fetch_baseline_data(plan_id, token, org_id)
    
    @pyqtSlot()
    def load_bng_plan_layers(self):
        """Load BNG plan layers for the selected plan"""
        if not self.auth_manager or not self.auth_manager.is_logged_in():
            self.show_error("Please log in first")
            return
        
        # Get selected plan ID
        if self.plan_combo.currentIndex() < 0:
            self.show_error("Please select a plan first")
            return
        
        plan_id = self.plan_combo.currentData()
        
        # Get token and organization ID
        token = self.auth_manager.get_access_token()
        org_id = None
        if hasattr(self.auth_manager, 'get_current_organization'):
            org = self.auth_manager.get_current_organization()
            if org and 'id' in org:
                org_id = org['id']
        
        # Start async data fetch
        self.data_fetcher.fetch_bng_plan_data(plan_id, token, org_id)
    
    @pyqtSlot()
    def clear_baseline_layers(self):
        """Clear baseline layers"""
        from ..layers import BaseLayersManager
        
        manager = BaseLayersManager()
        if manager.clear_all_base_layers():
            self.baseline_layers = {}
            self.status_label.setText("Baseline layers cleared")
        else:
            self.status_label.setText("Error clearing baseline layers")
    
    @pyqtSlot()
    def clear_bng_plan_layers(self):
        """Clear BNG plan layers"""
        from ..layers import BNGPlanLayersManager
        
        manager = BNGPlanLayersManager()
        if manager.clear_all_bng_plan_layers():
            self.bng_plan_layers = {}
            self.status_label.setText("BNG Plan layers cleared")
        else:
            self.status_label.setText("Error clearing BNG Plan layers")
    
    @pyqtSlot()
    def calculate_net_gain(self):
        """Calculate net gain between baseline and BNG plan layers"""
        if not self.baseline_layers or not self.bng_plan_layers:
            self.show_error("Both baseline and BNG Plan layers must be loaded first")
            return
        
        results = self.data_fetcher.calculate_net_gain(self.baseline_layers, self.bng_plan_layers)
        
        if results:
            self.status_label.setText("Net gain calculation complete")
            
            # Prepare message with results
            message = "Net Gain Calculation Results:\n\n"
            
            if 'trees' in results:
                message += "Trees: "
                message += "Success\n" if results['trees'] else "Failed\n"
            
            if 'watercourses' in results:
                message += "Watercourses: "
                message += "Success\n" if results['watercourses'] else "Failed\n"
            
            if 'plans' in results:
                message += "Plans: "
                message += "Success\n" if results['plans'] else "Failed\n"
            
            # Show results
            QMessageBox.information(self, "Net Gain Results", message)
        else:
            self.status_label.setText("Error calculating net gain")
    
    @pyqtSlot()
    def on_fetch_started(self):
        """Handle fetch started signal"""
        self.progress_bar.setVisible(True)
        self.status_label.setText("Fetching data...")
    
    @pyqtSlot(dict)
    def on_fetch_completed(self, layers):
        """Handle fetch completed signal"""
        self.progress_bar.setVisible(False)
        
        # Determine if these are baseline or BNG plan layers
        # by checking which button is enabled/disabled
        if self.load_baseline_btn.isEnabled() and not self.load_bng_plan_btn.isEnabled():
            # BNG plan layers
            self.bng_plan_layers = layers
            self.load_bng_plan_btn.setEnabled(True)
            layer_type = "BNG Plan"
        else:
            # Baseline layers
            self.baseline_layers = layers
            self.load_baseline_btn.setEnabled(True)
            layer_type = "Baseline"
        
        # Update status
        num_layers = len(layers)
        layer_names = ", ".join(layers.keys())
        self.status_label.setText(f"Loaded {num_layers} {layer_type} layers: {layer_names}")
    
    @pyqtSlot(str)
    def on_fetch_error(self, error_message):
        """Handle fetch error signal"""
        self.progress_bar.setVisible(False)
        self.load_baseline_btn.setEnabled(True)
        self.load_bng_plan_btn.setEnabled(True)
        self.status_label.setText(f"Error: {error_message}")
        self.show_error(error_message)
    
    def show_error(self, message):
        """Show error message box"""
        QMessageBox.critical(self, "Error", message)
    
    def set_api_client(self, api_client):
        """
        Set the API client to use
        
        Args:
            api_client: API client instance
        """
        self.api_client = api_client
        self.data_fetcher.api_client = api_client
        
        # If authenticated, fetch plans
        if self.auth_manager and self.auth_manager.is_logged_in():
            self.fetch_plans()
    
    def update_ui_state(self):
        """Update UI state based on authentication status"""
        is_logged_in = self.auth_manager and self.auth_manager.is_logged_in()
        
        # Enable/disable controls based on login state
        self.plan_combo.setEnabled(is_logged_in)
        self.refresh_plans_btn.setEnabled(is_logged_in)
        self.load_baseline_btn.setEnabled(is_logged_in)
        self.load_bng_plan_btn.setEnabled(is_logged_in)
        self.calc_net_gain_btn.setEnabled(is_logged_in and bool(self.baseline_layers) and bool(self.bng_plan_layers))
        
        # Update status label
        if not is_logged_in:
            self.status_label.setText("Please log in to access map features")
            self.plan_combo.clear()
        else:
            self.status_label.setText("Ready")
            if self.plan_combo.count() == 0:
                # Fetch plans if authenticated but no plans loaded
                self.fetch_plans() 