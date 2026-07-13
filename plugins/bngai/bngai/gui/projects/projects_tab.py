"""
BNG Planning Tab - Tab for displaying and interacting with BNG Planning projects
"""
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QComboBox, QMessageBox, QDialog, QTextEdit)
from qgis.PyQt.QtCore import Qt, pyqtSignal, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsMessageLog, QgsProject, QgsGeometry, QgsVectorLayer
try:
    from qgis.PyQt import sip
except ImportError:
    import sip
from ...layers.layer_manager import LayerManager
from .api_client import ProjectsApiClient
from .feature_manager import FeatureManager
from .state_manager import StateManager
from .bng_plan_table import BNGPlanDropdownManager
from .habitat_sync_manager import HabitatSyncManager
from ...layers import LayerFactory
from ...layers.retained_habitat_layers import RetainedHabitatLayersManager
from ...layers.boundary_layers import BoundaryLayersManager

class ProjectsTab(QWidget):
    """
    Tab for displaying and interacting with BNG Planning projects
    """
    # Define signals
    project_selected = pyqtSignal(dict)
    
    def __init__(self, auth_manager, parent=None):
        """Initialize the BNG Planning tab"""
        super(ProjectsTab, self).__init__(parent)
        
        # Initialize managers
        self.auth_manager = auth_manager
        self.api_client = ProjectsApiClient(auth_manager)
        self.layer_manager = LayerManager()  # Create LayerManager first
        self.feature_manager = FeatureManager(self.api_client, layer_manager=self.layer_manager)
        self.state_manager = StateManager()
        self.habitat_sync_manager = HabitatSyncManager(self.api_client)
        
        # Initialize properties
        self.iface = None  # Will be set by the plugin
        self.is_loading = False  # Flag to prevent recursive calls
        
        # Set up the UI
        self.setup_ui()
        
        # Initialize managers after UI setup
        self.bng_plan_dropdown_manager = BNGPlanDropdownManager(self.api_client, self.bng_plan_dropdown)
        
        # Connect signals
        self.connect_signals()
        
        # Disable tab initially (until user is logged in)
        self.setEnabled(False)
    
    def _is_widget_valid(self) -> bool:
        """Check if the widget and its children are still valid (not deleted)."""
        try:
            # Check if this widget has been deleted
            if sip.isdeleted(self):
                return False
            # Check critical child widgets
            if hasattr(self, 'org_dropdown') and sip.isdeleted(self.org_dropdown):
                return False
            if hasattr(self, 'sync_status_text') and sip.isdeleted(self.sync_status_text):
                return False
            return True
        except Exception:
            return False
    
    def setup_ui(self):
        """Set up the UI elements"""
        # Get the path to the refresh icon using Qt's resource system
        refresh_icon_path = ":/plugins/bngai/refresh.png"
        refresh_icon = QIcon(refresh_icon_path)
        if refresh_icon.isNull():
            refresh_icon = QIcon(":/images/themes/default/mActionRefresh.svg")

        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # Add status label at the top
        self.status_label = QLabel()
        self.status_label.setStyleSheet("""
            QLabel {
                color: #333333;
                font-weight: bold;
                padding: 5px;
                margin-bottom: 10px;
            }
        """)
        self.main_layout.addWidget(self.status_label)

        # Common styles
        dropdown_style = """
            QComboBox {
                padding: 8px;
                background: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                min-height: 16px;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            QComboBox::down-arrow {
                image: url(:/images/themes/default/mActionArrowDown.svg);
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background: white;
                border: 1px solid #E0E0E0;
                selection-background-color: #F5F5F5;
                selection-color: black;
            }
            QComboBox QAbstractItemView::item {
                padding: 6px;
                min-height: 24px;
            }
            QComboBox QAbstractItemView::item:hover {
                background: #F5F5F5;
                color: black;
                font-weight: bold;
            }
            QComboBox QAbstractItemView::item:selected {
                background: #E8E8E8;
                color: black;
                font-weight: bold;
            }
        """
        
        refresh_button_style = """
            QPushButton {
                border: none;
                padding: 5px;
                color: #00A300;
                text-align: right;
                background: transparent;
            }
            QPushButton:hover {
                color: #008000;
            }
        """

        action_button_style = """
            QPushButton {
                padding: 8px 16px;
                background: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                color: #333333;
            }
            QPushButton:hover {
                background: #E8E8E8;
            }
            QPushButton:disabled {
                background: #F5F5F5;
                color: #999999;
            }
        """

        # Organization Section
        org_section = QHBoxLayout()
        org_label = QLabel("Organisation")
        org_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        org_section.addWidget(org_label)
        
        org_section.addStretch()
        
        self.refresh_orgs_button = QPushButton("Refresh")
        self.refresh_orgs_button.setIcon(refresh_icon)
        self.refresh_orgs_button.setLayoutDirection(Qt.RightToLeft)
        self.refresh_orgs_button.setStyleSheet(refresh_button_style)
        org_section.addWidget(self.refresh_orgs_button)
        
        self.main_layout.addLayout(org_section)
        
        self.org_dropdown = QComboBox()
        self.org_dropdown.setStyleSheet(dropdown_style)
        self.org_dropdown.setPlaceholderText("Select organization")
        self.main_layout.addWidget(self.org_dropdown)

        # Project category (My Projects vs Assigned projects)
        category_section = QHBoxLayout()
        category_label = QLabel("Project category")
        category_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        category_section.addWidget(category_label)
        category_section.addStretch()
        self.main_layout.addLayout(category_section)

        self.project_category_dropdown = QComboBox()
        self.project_category_dropdown.setStyleSheet(dropdown_style)
        self.project_category_dropdown.addItem("My Projects", "my")
        self.project_category_dropdown.addItem("Assigned projects", "assigned")
        self.main_layout.addWidget(self.project_category_dropdown)

        # Project Section
        project_section = QHBoxLayout()
        project_label = QLabel("Project")
        project_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        project_section.addWidget(project_label)
        
        project_section.addStretch()
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setIcon(refresh_icon)
        self.refresh_button.setLayoutDirection(Qt.RightToLeft)
        self.refresh_button.setStyleSheet(refresh_button_style)
        project_section.addWidget(self.refresh_button)
        
        self.main_layout.addLayout(project_section)
        
        self.project_dropdown = QComboBox()
        self.project_dropdown.setStyleSheet(dropdown_style)
        self.project_dropdown.setPlaceholderText("Select project")
        self.main_layout.addWidget(self.project_dropdown)

        # Plan Section
        plan_label = QLabel("Plan")
        plan_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.main_layout.addWidget(plan_label)
        
        self.bng_plan_dropdown = QComboBox()
        self.bng_plan_dropdown.setStyleSheet(dropdown_style)
        self.bng_plan_dropdown.setEnabled(False)
        self.main_layout.addWidget(self.bng_plan_dropdown)

        # Load Baseline and BNG Plan buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.load_baseline_button = QPushButton("Load Baseline")
        self.load_baseline_button.setStyleSheet(action_button_style)
        self.load_baseline_button.setEnabled(False)
        button_layout.addWidget(self.load_baseline_button)
        
        button_layout.addSpacing(10)  # Add spacing between buttons
        
        self.load_bng_plan_button = QPushButton("Load BNG Plan")
        self.load_bng_plan_button.setStyleSheet(action_button_style)
        self.load_bng_plan_button.setEnabled(False)
        button_layout.addWidget(self.load_bng_plan_button)
        
        button_layout.addSpacing(10)
        
        self.main_layout.addLayout(button_layout)

        # Sync Status Section
        sync_section = QHBoxLayout()
        sync_label = QLabel("Sync Status")
        sync_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        sync_section.addWidget(sync_label)
        
        sync_section.addStretch()
        
        # Add Sync Habitats button
        self.sync_habitats_button = QPushButton("Sync Habitats")
        self.sync_habitats_button.setStyleSheet(action_button_style + """
            QPushButton:disabled {
                background: #F5F5F5;
                color: #999999;
                border: 1px solid #E0E0E0;
            }
        """)
        self.sync_habitats_button.setEnabled(False)  # Initially disabled
        sync_section.addWidget(self.sync_habitats_button)
        
        sync_section.addSpacing(10)  # Add spacing between buttons
        
        self.sync_refresh_button = QPushButton("Refresh")
        self.sync_refresh_button.setIcon(refresh_icon)
        self.sync_refresh_button.setLayoutDirection(Qt.RightToLeft)
        self.sync_refresh_button.setStyleSheet(refresh_button_style)
        sync_section.addWidget(self.sync_refresh_button)
        
        self.main_layout.addLayout(sync_section)
        
        # Sync Status Text Area
        self.sync_status_text = QTextEdit()
        self.sync_status_text.setReadOnly(True)
        self.sync_status_text.setMinimumHeight(100)  # Set minimum height for better visibility
        self.sync_status_text.setStyleSheet("""
            QTextEdit {
                background: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 6px 10px;
                font-family: system-ui, -apple-system, sans-serif;
            }
        """)
        self.main_layout.addWidget(self.sync_status_text)

        # Habitat ID Section
        habitat_id_layout = QHBoxLayout()
        habitat_id_layout.setContentsMargins(0, 5, 0, 5)
        habitat_id_label = QLabel("Habitat ID:")
        habitat_id_label.setStyleSheet("font-weight: bold;")
        self.feature_id_label = QLabel("None")
        habitat_id_layout.addWidget(habitat_id_label)
        habitat_id_layout.addWidget(self.feature_id_label)
        habitat_id_layout.addStretch()
        self.main_layout.addLayout(habitat_id_layout)

        # Feature Management Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Merge Button
        self.merge_button = QPushButton("Merge")
        self.merge_button.setEnabled(False)
        self.merge_button.setStyleSheet(action_button_style)
        button_layout.addWidget(self.merge_button)

        self.main_layout.addLayout(button_layout)

        # Add stretch at the bottom to push everything up
        self.main_layout.addStretch()

        # Create the dropdown manager
        self.bng_plan_dropdown_manager = BNGPlanDropdownManager(self.api_client, self.bng_plan_dropdown)
    
    def connect_signals(self):
        """Connect Qt signals and slots"""
        # Connect refresh buttons
        self.refresh_button.clicked.connect(self.fetch_projects)
        self.refresh_orgs_button.clicked.connect(self.fetch_organizations)
        self.sync_refresh_button.clicked.connect(self.fetch_sync_status)
        self.sync_habitats_button.clicked.connect(self.sync_habitats)
        
        # Connect load buttons
        self.load_baseline_button.clicked.connect(self.load_baseline_layers)
        self.load_bng_plan_button.clicked.connect(self.load_bng_plan)
        # Removed: load_retained_layers_button
        
        # Connect dropdowns
        self.org_dropdown.currentIndexChanged.connect(self.on_organization_changed)
        self.project_category_dropdown.currentIndexChanged.connect(
            self.on_project_category_changed
        )
        self.project_dropdown.currentIndexChanged.connect(self.on_project_changed)
        
        # Connect to QGIS project signals
        QgsProject.instance().layersAdded.connect(self.layer_manager.on_layers_added)
        QgsProject.instance().layersRemoved.connect(self.layer_manager.on_layers_removed)
        
        # Connect to selection changes in QGIS
        if self.iface:
            self.iface.currentLayerChanged.connect(self.on_current_layer_changed)
            # Also connect to selection changes on the active layer
            active_layer = self.iface.activeLayer()
            if active_layer and isinstance(active_layer, QgsVectorLayer):
                active_layer.selectionChanged.connect(self.update_button_states)
        
        # Try to connect to existing layers
        self.layer_manager.connect_to_existing_layers()
        
        # Connect the dropdown signal
        self.bng_plan_dropdown.currentIndexChanged.connect(self.on_plan_selected)
        self.merge_button.clicked.connect(self.on_merge_clicked)
        # Connect LayerManager selection_changed signal to update_button_states
        self.layer_manager.selection_changed.connect(self.update_button_states)
    
    def set_iface(self, iface):
        """Set the QGIS interface"""
        self.iface = iface
        
        # Connect to QGIS project signals
        QgsProject.instance().layersAdded.connect(self.layer_manager.on_layers_added)
        QgsProject.instance().layersRemoved.connect(self.layer_manager.on_layers_removed)
        
        # Connect to selection changes on the active layer
        if self.iface:
            self.iface.currentLayerChanged.connect(self.on_current_layer_changed)
            active_layer = self.iface.activeLayer()
            if active_layer and isinstance(active_layer, QgsVectorLayer):
                active_layer.selectionChanged.connect(self.update_button_states)
        
        # Connect to existing layers
        self.layer_manager.connect_to_existing_layers()
        
    def on_current_layer_changed(self, layer):
        """Handle current layer change"""
        try:
            # Disconnect from old layer's selection signal
            old_layer = self.current_layer if hasattr(self, 'current_layer') else None
            if old_layer and isinstance(old_layer, QgsVectorLayer):
                try:
                    old_layer.selectionChanged.disconnect(self.update_button_states)
                except (TypeError, RuntimeError):
                    # Handle case where layer is already deleted
                    pass
            
            # Store and connect to new layer
            self.current_layer = layer
            if layer is not None:  # Check if layer exists
                if isinstance(layer, QgsVectorLayer):
                    try:
                        layer.selectionChanged.connect(self.update_button_states)
                    except (TypeError, RuntimeError):
                        # Handle case where layer is being deleted
                        pass
            
            # Update button states for new layer
            self.update_button_states()
            
        except Exception as e:
            # Log any unexpected errors
            QgsMessageLog.logMessage(f"Error in on_current_layer_changed: {str(e)}", "BNGAI Plugin", level=2)
            # Continue gracefully
            self.update_button_states()
    
    def set_api_client(self, api_client):
        """Set the API client for this tab"""
        # Create a new ProjectsApiClient if we didn't get one
        if not isinstance(api_client, ProjectsApiClient):
            QgsMessageLog.logMessage("Converting generic API client to ProjectsApiClient", "BNGAI Plugin", level=0)
            api_client = ProjectsApiClient(self.auth_manager)
            
        self.api_client = api_client
        self.feature_manager = FeatureManager(api_client, layer_manager=self.layer_manager)
        self.habitat_sync_manager = HabitatSyncManager(self.api_client)
        
        if api_client and self._is_widget_valid():
            self.setEnabled(True)
            # Populate organization dropdown
            self.fetch_organizations()
    
    def hideEvent(self, event):
        """Handle hide event"""
        # Disconnect from layers when hidden to prevent callbacks to hidden widgets
        self.layer_manager.disconnect_all_layers()
        super(ProjectsTab, self).hideEvent(event)
        
    def showEvent(self, event):
        """Handle show event"""
        # Reconnect to layers when shown
        self.layer_manager.connect_to_existing_layers()
        
        # Check if user is logged in before restoring state
        if self.auth_manager.is_logged_in():
            # Restore selections from settings if needed
            org_id, _ = self.state_manager.get_organization()
            project_id, _ = self.state_manager.get_project()
            plan_id, _ = self.state_manager.get_plan()
            
            # If organization dropdown is empty but we have a saved organization,
            # trigger the organization fetch which will restore the selection
            if self.org_dropdown.count() == 0 and org_id:
                QgsMessageLog.logMessage("Restoring organization from settings", "BNGAI Plugin", level=0)
                self.fetch_organizations()
            
            # If project dropdown is empty but we have a saved project,
            # trigger the project fetch which will restore the selection
            if self.project_dropdown.count() == 0 and project_id and self.org_dropdown.currentIndex() >= 0:
                QgsMessageLog.logMessage("Restoring project from settings", "BNGAI Plugin", level=0)
                self.fetch_projects()
            
            # If BNG plan dropdown is empty but we have a saved plan,
            # the plan will be restored after project selection via on_project_changed
            if self.bng_plan_dropdown.count() == 0 and plan_id:
                QgsMessageLog.logMessage("BNG plan will be restored after project selection", "BNGAI Plugin", level=0)
        
        super(ProjectsTab, self).showEvent(event) 

    def set_sync_status(self, message):
        """Set sync status text and log it"""
        # Log the message
        QgsMessageLog.logMessage(f"Sync Status Update: {message}", "BNGAI Plugin", level=0)
        # Update the UI only if widget is still valid
        if self._is_widget_valid():
            self.sync_status_text.setText(message)
            # Scroll to the top to ensure latest message is visible
            self.sync_status_text.verticalScrollBar().setValue(0)

    def fetch_organizations(self):
        """Fetch organizations for the logged-in user"""
        # Check if widget is still valid
        if not self._is_widget_valid():
            QgsMessageLog.logMessage("Widget deleted, skipping fetch_organizations", "BNGAI Plugin", level=1)
            return
            
        if not self.auth_manager.is_logged_in():
            self.set_sync_status("Please log in to fetch organizations")
            self._show_login_required_message()
            return
            
        try:
            # Show loading status
            self.set_sync_status("Fetching organizations...")
            self.refresh_orgs_button.setEnabled(False)
            QCoreApplication.processEvents()  # Update UI
            
            # Clear previous items
            self.org_dropdown.clear()
            
            # Fetch organizations
            organizations = self.api_client.get_organizations()
            
            # Reset button state
            self.refresh_orgs_button.setEnabled(True)
            
            if not organizations:
                self.set_sync_status("No organizations found")
                return
                
            # Get previously selected organization
            saved_org_id, saved_org_name = self.state_manager.get_organization()
            
            # Add organizations to dropdown
            found_index = -1
            for i, org in enumerate(organizations):
                if "id" in org and "name" in org:
                    self.org_dropdown.addItem(org['name'], org['id'])
                    
                    # Check if this is the previously selected org
                    if saved_org_id and org['id'] == saved_org_id:
                        found_index = i
            
            # If we have organizations
            if self.org_dropdown.count() > 0:
                # Show success message
                self.set_sync_status(f"Found {self.org_dropdown.count()} organizations")
                
                # Select previously chosen org if found, otherwise select first
                if found_index >= 0:
                    self.org_dropdown.setCurrentIndex(found_index)
                else:
                    self.org_dropdown.setCurrentIndex(0)
            else:
                self.set_sync_status("No valid organizations found")
                
        except Exception as e:
            QgsMessageLog.logMessage(f"Error fetching organizations: {str(e)}", "BNGAI Plugin", level=2)
            QgsMessageLog.logMessage(f"Error type: {type(e)}", "BNGAI Plugin", level=2)
            import traceback
            QgsMessageLog.logMessage(f"Error traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            self.set_sync_status(f"Error: {str(e)}")
            self.refresh_orgs_button.setEnabled(True)
    
    def _reset_bng_plan_dropdown(self):
        """Clear the BNG plan list and disable plan actions until plans are loaded again."""
        self.bng_plan_dropdown.blockSignals(True)
        self.bng_plan_dropdown.clear()
        self.bng_plan_dropdown.setEnabled(False)
        self.bng_plan_dropdown.blockSignals(False)
        self.load_bng_plan_button.setEnabled(False)
        self.load_baseline_button.setEnabled(False)

    def fetch_projects(self):
        """Fetch BNG Planning projects from the API"""
        if not self.auth_manager.is_logged_in():
            self.set_sync_status("Error: Not logged in")
            return
            
        # Set the loading flag to prevent recursive calls
        self.is_loading = True
        
        try:
            category = self.project_category_dropdown.currentData() or "my"
            if category == "assigned":
                self.set_sync_status("Fetching assigned projects...")
            else:
                self.set_sync_status("Fetching BNG Planning projects...")
            self.refresh_button.setEnabled(False)
            QCoreApplication.processEvents()  # Update UI
            
            # Get the current organization
            org_id = self.org_dropdown.currentData()
            if not org_id:
                self.set_sync_status("Please select an organization first")
                self.refresh_button.setEnabled(True)
                return

            # Clear plans immediately; project list will change (category/org/refresh).
            self._reset_bng_plan_dropdown()
            
            # Fetch projects
            result = self.api_client.get_projects(org_id, category=category)
            
            # Reset button state
            self.refresh_button.setEnabled(True)

            self.project_dropdown.blockSignals(True)
            try:
                if not result:
                    self.project_dropdown.clear()
                    self.set_sync_status("No projects found or invalid response format")
                else:
                    rows = result.get("rows", [])
                    self.project_dropdown.clear()
                    saved_project_id, _ = self.state_manager.get_project()
                    found_index = -1
                    for i, project in enumerate(rows):
                        if "projectId" in project and "projectName" in project:
                            project_id = project["projectId"]
                            project_name = project["projectName"]
                            self.project_dropdown.addItem(project_name, project_id)
                            if saved_project_id and project_id == saved_project_id:
                                found_index = i

                    if category == "assigned":
                        self.set_sync_status(
                            f"Found {self.project_dropdown.count()} assigned projects"
                        )
                    else:
                        self.set_sync_status(
                            f"Found {self.project_dropdown.count()} BNG Planning projects"
                        )

                    if found_index >= 0 and self.project_dropdown.count() > 0:
                        self.project_dropdown.setCurrentIndex(found_index)
                    elif self.project_dropdown.count() > 0:
                        self.project_dropdown.setCurrentIndex(0)
            finally:
                self.project_dropdown.blockSignals(False)

            # QComboBox may auto-select index 0 as items are added, so setCurrentIndex(0)
            # can be a no-op and never emit currentIndexChanged — always reload plans here.
            if result and self.project_dropdown.count() > 0:
                self.on_project_changed(self.project_dropdown.currentIndex())

            self.update_button_states()
            
        except Exception as e:
            self.set_sync_status(f"Error: {str(e)}")
            self.refresh_button.setEnabled(True)
            self.project_dropdown.clear()
            self._reset_bng_plan_dropdown()
            self.update_button_states()
        finally:
            self.is_loading = False
    
    def load_baseline_layers(self):
        """Load baseline geometries from the API and create QGIS layers"""
        if not self.auth_manager.is_logged_in():
            self.set_sync_status("Error: Not logged in")
            self._show_login_required_message()
            return
            
        # Get the selected project
        if self.project_dropdown.count() == 0 or self.project_dropdown.currentIndex() < 0:
            self.set_sync_status("Error: No project selected")
            return
            
        project_id = self.project_dropdown.currentData()
        project_name = self.project_dropdown.currentText()
        org_id = self.org_dropdown.currentData()
        
        if not project_id or not org_id:
            self.set_sync_status("Error: Invalid project or organization ID")
            return
        
        # Show loading status
        self.set_sync_status(f"Loading baseline layers for project: {project_name}...")
        self.load_baseline_button.setEnabled(False)
        self.load_baseline_button.setText("Loading...")
        QCoreApplication.processEvents()  # Update UI
        
        try:
            # Get project details to get the site revision ID
            project_details = self.api_client.get_project_details(project_id, org_id)
            
            if not project_details or "siteRevisionId" not in project_details:
                self.set_sync_status("Failed to fetch project details or no site revision ID")
                return
                
            site_revision_id = project_details["siteRevisionId"]

            # Get plan_id if a plan is selected (required for new base features API)
            plan_id = None
            if self.bng_plan_dropdown and self.bng_plan_dropdown.count() > 0 and self.bng_plan_dropdown.currentIndex() >= 0:
                plan_id = self.bng_plan_dropdown.currentData()
            
            # Fetch base habitat features using the new WFS endpoint
            habitat_data = self.api_client.get_base_features(
                plan_id=plan_id,
                org_id=org_id,
                site_revision_id=site_revision_id
            )
            
            if not habitat_data or habitat_data.get("type") != "FeatureCollection":
                self.set_sync_status("No habitat geometries found in the response")
                return
                
            features = habitat_data.get("features", [])
            
            if not features:
                self.set_sync_status("No habitat features found")
                return
            
            # Process habitat geometries
            habitat_geometries = {
                'points': [],
                'lines': [],
                'polygons': []
            }
            
            for feature in features:
                if feature.get("type") != "Feature":
                    continue
                    
                geometry = feature.get("geometry")
                if not geometry:
                    continue
                
                props = feature.get("properties", {})
                feature_id = feature.get("id")
                
                # Create property object with all the required properties
                properties = {
                    "id": feature_id or "",
                    "habitatReferenceID": props.get("retainedHabitatId", ""),
                    "sourceId": feature_id or "",  # Set sourceId same as id for baseline features
                    "retainedId": props.get("habitatReferenceID", ""),
                }
                
                
                # Add area and length directly from properties
                if props.get("area") is not None:
                    properties["area"] = props.get("area")
                if props.get("length") is not None:
                    properties["length"] = props.get("length")
                
                # Add biodiversity attributes
                bio_attrs = props.get("biodiversityAttributes", {})
                if bio_attrs:
                    for key in ["condition", "treeSize", "isIrreplaceableHabitat", "distinctiveness", "strategy", "isGreenWall"]:
                        if bio_attrs.get(key) is not None:
                            properties[key] = bio_attrs[key]
                
                # Add habitat classification
                habitat_class = props.get("habitatClassification", {})
                if habitat_class:
                    # Add aiDash classification
                    ai_dash = habitat_class.get("aiDash", {})
                    if ai_dash:
                        if ai_dash.get("code"):
                            properties["aiDashCode"] = ai_dash["code"]
                        if ai_dash.get("label"):
                            properties["aiDashLabel"] = ai_dash["label"]
                    
                    # Add custom classification
                    custom = habitat_class.get("custom", {})
                    if custom:
                        for key in ["code", "label", "group", "shapeType"]:
                            if custom.get(key) is not None:
                                properties[f"custom{key.capitalize()}"] = custom[key]
                
                # Create a GeoJSON feature
                processed_feature = {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": properties
                }
                
                # Add to appropriate list based on geometry type
                geom_type = geometry.get("type")
                if geom_type in ("Point", "MultiPoint"):
                    habitat_geometries['points'].append(processed_feature)
                elif geom_type in ("LineString", "MultiLineString"):
                    habitat_geometries['lines'].append(processed_feature)
                elif geom_type in ("Polygon", "MultiPolygon"):
                    habitat_geometries['polygons'].append(processed_feature)
            
            # Create feature collections for each geometry type
            created_layers = {}
            QgsMessageLog.logMessage(f"Creating baseline layers with project_id: {project_id}", "BNGAI Plugin", level=0)
            layer_factory = LayerFactory(is_baseline=True, project_id=project_id)
            
            # Create point layer if we have points
            if habitat_geometries['points']:
                point_collection = {
                    "type": "FeatureCollection",
                    "features": habitat_geometries['points']
                }
                point_layers = layer_factory.create_layers_from_api_data(point_collection)
                if point_layers:
                    created_layers.update(point_layers)
            
            # Create line layer if we have lines
            if habitat_geometries['lines']:
                line_collection = {
                    "type": "FeatureCollection",
                    "features": habitat_geometries['lines']
                }
                line_layers = layer_factory.create_layers_from_api_data(line_collection)
                if line_layers:
                    created_layers.update(line_layers)
            
            # Create polygon layer if we have polygons
            if habitat_geometries['polygons']:
                polygon_collection = {
                    "type": "FeatureCollection",
                    "features": habitat_geometries['polygons']
                }
                polygon_layers = layer_factory.create_layers_from_api_data(polygon_collection)
                if polygon_layers:
                    created_layers.update(polygon_layers)
            
            # Note: Red Line Boundary is not returned by the new WFS base features endpoint.
            # If boundary geometry is needed, a separate API call would be required.
            
            # Check if any layers were created
            if not created_layers:
                self.set_sync_status("No layers could be created from the geometry data")
                return
            
            # Count created layers
            layer_count = len(created_layers)
            layer_names = ", ".join(created_layers.keys())
            
            # Update status
            self.set_sync_status(f"Created {layer_count} baseline layers: {layer_names}")
            
            # Verify layer properties
            self.verify_layer_properties()
            
           
            
        except Exception as e:
            self.set_sync_status(f"Error: {str(e)}")
        finally:
            self.load_baseline_button.setEnabled(True)
            self.load_baseline_button.setText("Load Baseline Layers")
    
    def update_button_states(self):
        """Update button states based on selection"""
        try:
            # Get current layer
            layer = None
            if self.iface:
                layer = self.iface.activeLayer()
            
            # Initialize selected_count to 0
            selected_count = 0
            
            if layer and layer.isValid():
                # Check if this is a vector layer
                if isinstance(layer, QgsVectorLayer):
                    # Get selected feature count
                    selected_count = layer.selectedFeatureCount()
                    
                    # Check if this is a BNG Plan layer
                    bngai_id = layer.customProperty('bngai_id')
                    is_plan_layer = bngai_id is not None and not layer.customProperty('is_baseline', False)
                    
                    if is_plan_layer:
                        # Enable sync button for plan layers
                        self.sync_habitats_button.setEnabled(True)
                        if selected_count > 0:
                            self.sync_habitats_button.setText(f"Sync Selected Habitats ({selected_count})")
                        else:
                            self.sync_habitats_button.setText("Sync All Habitats")
                        
                        # Enable merge button if 2 or more features are selected
                        self.merge_button.setEnabled(selected_count >= 2)
                    else:
                        self.sync_habitats_button.setEnabled(False)
                        self.sync_habitats_button.setText("Sync Habitats")
                        self.merge_button.setEnabled(False)
                    
                    # Update feature ID label
                    if selected_count > 0:
                        feature = next(layer.getSelectedFeatures(), None)
                        if feature:
                            feature_id = feature.attribute("id") if feature.fieldNameIndex("id") >= 0 else None
                            self.feature_id_label.setText(str(feature_id) if feature_id else "None")
                    else:
                        self.feature_id_label.setText("None")
                else:
                    # Not a vector layer - disable all selection-dependent buttons
                    self.sync_habitats_button.setEnabled(False)
                    self.sync_habitats_button.setText("Sync Habitats")
                    self.feature_id_label.setText("None")
                    self.merge_button.setEnabled(False)
            else:
                # No valid layer
                self.sync_habitats_button.setEnabled(False)
                self.sync_habitats_button.setText("Sync Habitats")
                self.feature_id_label.setText("None")
                self.merge_button.setEnabled(False)
                
        except Exception as e:
            # Log any unexpected errors
            QgsMessageLog.logMessage(f"Error in update_button_states: {str(e)}", "BNGAI Plugin", level=2)
            # Set safe default states
            self.sync_habitats_button.setEnabled(False)
            self.sync_habitats_button.setText("Sync Habitats")
            self.feature_id_label.setText("None")
            self.merge_button.setEnabled(False)
    
    def _show_login_required_message(self):
        """Show a message box informing the user they need to log in again"""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Session Expired")
        msg_box.setText("Your session has expired.")
        msg_box.setInformativeText("Please switch to the Login tab and log in again to continue.")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_() 

    def on_project_category_changed(self, index):
        """Reload project list when switching between My Projects and Assigned projects."""
        if self.is_loading:
            return
        if index < 0:
            return
        if self.org_dropdown.currentIndex() < 0 or not self.org_dropdown.currentData():
            return
        self.fetch_projects()

    def on_organization_changed(self, index):
        """Handle organization selection change"""
        # Skip if we're already loading
        if self.is_loading:
            return
            
        if index < 0 or self.org_dropdown.count() == 0:
            return
            
        org_id = self.org_dropdown.itemData(index)
        org_name = self.org_dropdown.itemText(index)
        
        # Skip if either value is None
        if not org_id or not org_name:
            return
            
        # Save selected organization
        self.auth_manager.set_current_organization(org_id, org_name)
        self.state_manager.save_organization(org_id, org_name)
        
        # Update UI
        self.status_label.setText(f"Organization: {org_name}")
        
        # Clear both dropdowns
        self.project_dropdown.clear()
        self.update_button_states()
        
        # Fetch projects for the selected organization
        self.fetch_projects()
    
    def on_project_changed(self, index):
        """Handle project selection from the dropdown"""
        if index < 0:
            return
            
        # Get project ID and name
        project_id = self.project_dropdown.itemData(index)
        project_name = self.project_dropdown.itemText(index)
        
        # Save the selected project
        self.state_manager.save_project(project_id, project_name)
        
        # Get organization ID
        org_id = self.org_dropdown.currentData()
        if not org_id:
            self.set_sync_status("Error: No organization selected")
            return
        
        # Fetch project details and BNG plans
        try:
            self.set_sync_status("Fetching BNG plans...")
            QCoreApplication.processEvents()  # Update UI
            
            self.bng_plan_dropdown_manager.load_plans(project_id, org_id)
            
            # Enable dropdown if plans were loaded
            plan_count = self.bng_plan_dropdown.count()
            if plan_count > 0:
                self.bng_plan_dropdown.setEnabled(True)
                self.load_bng_plan_button.setEnabled(True)
                self.set_sync_status(f"Found {plan_count} BNG plans")
                
                # Get saved BNG plan selection
                saved_plan_id, _ = self.state_manager.get_plan()
                if saved_plan_id:
                    # Find the saved plan in the dropdown
                    for i in range(self.bng_plan_dropdown.count()):
                        if self.bng_plan_dropdown.itemData(i) == saved_plan_id:
                            self.bng_plan_dropdown.setCurrentIndex(i)
                            break
                else:
                    self.set_sync_status("No BNG plans found for this project")
                
            # Emit project selection
            project_info = {
                'id': project_id,
                'name': project_name,
                'planId': None,  # No plan selected yet
                'planName': None  # No plan selected yet
            }
            self.project_selected.emit(project_info)
            
        except Exception as e:
            self.set_sync_status(f"Error: {str(e)}")
            QgsMessageLog.logMessage(f"Error loading project details: {str(e)}", "BNGAI Plugin", level=2)
    
    def get_selected_project(self):
        """Get the currently selected project"""
        # Check if project is selected
        if self.project_dropdown.count() == 0 or self.project_dropdown.currentIndex() < 0:
            return None
        
        # Get the project ID and name from the project dropdown
        project_id = self.project_dropdown.currentData()
        project_name = self.project_dropdown.currentText()
        
        # Create a project-only object for deletion purposes
        return {
            'id': project_id,
            'name': project_name,
            'planId': None,  # No plan selected
            'planName': None  # No plan selected
        }
    
    def update_ui_state(self, is_logged_in=False):
        """Update UI based on login state"""
        # Enable/disable tabs based on login state
        if hasattr(self, 'projects_tab') and self.projects_tab:
            self.projects_tab.setEnabled(is_logged_in)
            
        # Clear plan table when logged out
        if not is_logged_in:
            self.bng_plan_dropdown.clear()
            self.bng_plan_dropdown.setEnabled(False)
    
    def on_plan_selected(self, index):
        """Handle BNG plan selection from the dropdown"""
        if index < 0:
            return
        plan_id = self.bng_plan_dropdown.itemData(index)
        plan_name = self.bng_plan_dropdown.itemText(index)
        
        # Save the selected plan
        self.state_manager.save_plan(plan_id, plan_name)
        
        # Log selection
        QgsMessageLog.logMessage(f"Selected BNG plan: {plan_name} (ID: {plan_id})", "BNGAI Plugin", level=0)
        
        # Enable both load buttons when a plan is selected
        self.load_bng_plan_button.setEnabled(True)
        self.load_baseline_button.setEnabled(True)
    
    def load_bng_plan(self):
        """Load BNG Plan habitats from the API and create QGIS layers"""
        if not self.auth_manager.is_logged_in():
            self.set_sync_status("Error: Not logged in")
            self._show_login_required_message()
            return
            
        # Get the selected plan from the dropdown
        current_index = self.bng_plan_dropdown.currentIndex()
        if current_index < 0:
            self.set_sync_status("Error: No BNG Plan selected")
            return
            
        # Get plan ID and name from the current selection
        plan_id = self.bng_plan_dropdown.currentData()  # Get plan ID from user data
        plan_name = self.bng_plan_dropdown.currentText()  # Get plan name
        
        if not plan_id:
            self.set_sync_status("Error: Invalid plan ID")
            return
        
        # Get organization ID
        org_id = self.org_dropdown.currentData()
        if not org_id:
            self.set_sync_status("Error: No organization selected")
            return
        
        # Show loading status
        self.set_sync_status(f"Loading BNG Plan habitats for plan: {plan_name}...")
        self.load_bng_plan_button.setEnabled(False)
        self.load_bng_plan_button.setText("Loading...")
        QCoreApplication.processEvents()  # Update UI
        
        try:
            # Fetch BNG Plan habitats data (returns GeoJSON FeatureCollection)
            geojson_data = self.api_client.get_bng_plan_habitats(plan_id, org_id)

            # Check if GeoJSON data is valid
            if not geojson_data or geojson_data.get("type") != "FeatureCollection":
                self.set_sync_status("No BNG Plan habitats found in the response")
                return
            
            features = geojson_data.get("features", [])
            
            # Check if features are empty
            if not features:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Information)
                msg_box.setWindowTitle("Empty BNG Plan")
                msg_box.setText(f"The BNG Plan '{plan_name}' is empty.")
                msg_box.setInformativeText("There are no habitats in this BNG Plan.")
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.exec_()
                self.set_sync_status(f"BNG Plan '{plan_name}' is empty")
                return
            
            # Process habitat geometries
            habitat_geometries = {
                'points': [],
                'lines': [],
                'polygons': []
            }
            QgsMessageLog.logMessage(f"BNG Plan habitats data: {len(features)} features", "BNGAI Plugin", level=0)
            
            for feature in features:
                if feature.get("type") != "Feature":
                    continue
                    
                geometry = feature.get("geometry")
                properties = feature.get("properties", {})
                feature_id = feature.get("id")
                
                if not geometry:
                    continue
                
                # Skip DELETE activityType entries
                activity_type_val = (properties.get("activityType") or "").strip().upper()
                if activity_type_val == "DELETE":
                    continue

                # Create property object with all the required properties
                feature_properties = {
                    "id": feature_id,
                    "sourceId": feature_id,
                    "treeSize": properties.get("treeSizeCode", ""),
                    "activityType": properties.get("activityType", ""),
                    "mergedIds": None,
                }
                
                # Add habitat classification from GeoJSON properties
                plan_habitat_code = properties.get("planHabitatAidashCode")
                plan_habitat_group = properties.get("planHabitatGroupName")
                
                if plan_habitat_code or plan_habitat_group:
                    feature_properties["aiDashCode"] = plan_habitat_code or ""
                    feature_properties["aiDashLabel"] = plan_habitat_group or "Unclassified"
                    feature_properties["customCode"] = plan_habitat_code or ""
                    feature_properties["customLabel"] = plan_habitat_group or "Unclassified"
                    feature_properties["customGroup"] = plan_habitat_group or ""
                    feature_properties["customShapeType"] = geometry.get("type") if geometry else None
                else:
                    # Set default values when habitat classification is missing
                    feature_properties.update({
                        "aiDashCode": "",
                        "aiDashLabel": "Unclassified",
                    })
                
                # Add other properties from GeoJSON
                if properties.get("conditionCode"):
                    feature_properties["condition"] = properties.get("conditionCode")
                if properties.get("distinctiveness"):
                    feature_properties["distinctiveness"] = properties.get("distinctiveness")
                if properties.get("strategicSignificanceCode"):
                    feature_properties["strategicSignificance"] = properties.get("strategicSignificanceCode")
                if properties.get("riparianEncroachmentCode"):
                    feature_properties["riparianEncroachment"] = properties.get("riparianEncroachmentCode")
                if properties.get("watercourseEncroachmentCode"):
                    feature_properties["watercourseEncroachment"] = properties.get("watercourseEncroachmentCode")
                if properties.get("watercourseAndRiparianEncroachmentCode"):
                    feature_properties["watercourseAndRiparianEncroachment"] = properties.get("watercourseAndRiparianEncroachmentCode")
                
                # Get referenceId directly from feature properties
                if properties.get("referenceId"):
                    feature_properties['referenceId'] = properties.get("referenceId")
                
                # Get area from feature propertiesr
                if properties.get("area") is not None:
                    feature_properties['area'] = properties.get("area")

                # Create a GeoJSON feature
                geojson_feature = {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": feature_properties
                }
                
                # Add to appropriate list based on geometry type
                geom_type = geometry.get("type")
                if geom_type == "Point" or geom_type == "MultiPoint":
                    habitat_geometries['points'].append(geojson_feature)
                elif geom_type == "LineString" or geom_type == "MultiLineString":
                    habitat_geometries['lines'].append(geojson_feature)
                elif geom_type == "Polygon" or geom_type == "MultiPolygon":
                    habitat_geometries['polygons'].append(geojson_feature)
            
            # Create feature collections for each geometry type
            created_layers = {}
            QgsMessageLog.logMessage(f"Creating BNG Plan layers with plan_id: {plan_id}", "BNGAI Plugin", level=0)
            layer_factory = LayerFactory(is_baseline=False, plan_id=plan_id)  # Set is_baseline to False for BNG Plan layers
            
            # Create point layer if we have points
            if habitat_geometries['points']:
                point_collection = {
                    "type": "FeatureCollection",
                    "features": habitat_geometries['points']
                }
                point_layers = layer_factory.create_layers_from_api_data(point_collection)
                if point_layers:
                    created_layers.update(point_layers)
            
            # Create line layer if we have lines
            if habitat_geometries['lines']:
                line_collection = {
                    "type": "FeatureCollection",
                    "features": habitat_geometries['lines']
                }
                line_layers = layer_factory.create_layers_from_api_data(line_collection)
                if line_layers:
                    created_layers.update(line_layers)
            
            # Create polygon layer if we have polygons
            if habitat_geometries['polygons']:
                polygon_collection = {
                    "type": "FeatureCollection",
                    "features": habitat_geometries['polygons']
                }
                polygon_layers = layer_factory.create_layers_from_api_data(polygon_collection)
                if polygon_layers:
                    created_layers.update(polygon_layers)
            
            # Check if any layers were created
            if not created_layers:
                self.set_sync_status("No layers could be created from the BNG Plan data")
                return
            
            # Count created layers
            layer_count = len(created_layers)
            layer_names = ", ".join(created_layers.keys())
            
            # Update status
            self.set_sync_status(f"Created {layer_count} BNG Plan layers: {layer_names}")
            
            # Verify layer properties
            self.verify_layer_properties()

            # Load Red Line Boundary (RLB) 
            self._load_red_line_boundary(plan_id, org_id)

            self.load_retained_layers()
            
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.set_sync_status(f"Error: {str(e)}")
            QgsMessageLog.logMessage(f"Error loading BNG Plan: {str(e)}", "BNGAI Plugin", level=2)
        finally:
            self.load_bng_plan_button.setEnabled(True)
            self.load_bng_plan_button.setText("Load BNG Plan") 
    
    def _load_red_line_boundary(self, plan_id, org_id):
        """
        Load Red Line Boundary (RLB) for the current plan.
        
        Args:
            plan_id (str): BNG Plan ID
            org_id (str): Organization ID
        """
        try:
            # Get project_id from the project dropdown
            project_id = self.project_dropdown.currentData()
            if not project_id:
                QgsMessageLog.logMessage("Cannot load RLB: No project selected", "BNGAI Plugin", level=1)
                return
            
            # Get project details to retrieve siteRevisionId
            project_details = self.api_client.get_project_details(project_id, org_id)
            
            if not project_details or "siteRevisionId" not in project_details:
                QgsMessageLog.logMessage("Cannot load RLB: No siteRevisionId in project details", "BNGAI Plugin", level=1)
                return
            
            site_revision_id = project_details["siteRevisionId"]
            QgsMessageLog.logMessage(f"Fetching RLB for siteRevisionId: {site_revision_id}", "BNGAI Plugin", level=0)
            
            # Fetch site boundary geometry
            boundary_geometry = self.api_client.get_site_boundary(site_revision_id, org_id)
            
            if not boundary_geometry:
                QgsMessageLog.logMessage("No site boundary geometry returned from API", "BNGAI Plugin", level=1)
                return
            
            # Create and load RLB layer
            boundary_manager = BoundaryLayersManager()
            rlb_layer = boundary_manager.load_rlb_from_geometry(
                boundary_geometry,
                plan_id=plan_id,
                name="Red Line Boundary"
            )
            
            if rlb_layer:
                QgsMessageLog.logMessage(f"Successfully loaded RLB layer for plan: {plan_id}", "BNGAI Plugin", level=0)
                
                # Zoom to RLB extent if it's the first layer
                if rlb_layer.featureCount() > 0:
                    self._zoom_to_layer_extent(rlb_layer)
            else:
                QgsMessageLog.logMessage("Failed to create RLB layer", "BNGAI Plugin", level=1)
                
        except Exception as e:
            QgsMessageLog.logMessage(f"Error loading RLB: {str(e)}", "BNGAI Plugin", level=2)
            import traceback
            QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
    
    def _zoom_to_layer_extent(self, layer):
        """
        Zoom the map canvas to the extent of a layer.
        
        Args:
            layer (QgsVectorLayer): Layer to zoom to
        """
        try:
            if self.iface and layer and layer.extent() and not layer.extent().isEmpty():
                # Add a small buffer around the extent
                extent = layer.extent()
                extent.grow(extent.width() * 0.1)  # 10% buffer
                self.iface.mapCanvas().setExtent(extent)
                self.iface.mapCanvas().refresh()
        except Exception as e:
            QgsMessageLog.logMessage(f"Error zooming to layer: {str(e)}", "BNGAI Plugin", level=1)
    
    def load_retained_layers(self):
        """Load Retained Habitats as a separate action."""
        if not self.auth_manager.is_logged_in():
            self.set_sync_status("Error: Not logged in")
            self._show_login_required_message()
            return
        
        # Ensure a plan is selected
        current_index = self.bng_plan_dropdown.currentIndex()
        if current_index < 0:
            self.set_sync_status("Error: No BNG Plan selected")
            return
        
        plan_id = self.bng_plan_dropdown.currentData()
        org_id = self.org_dropdown.currentData()
        if not plan_id or not org_id:
            self.set_sync_status("Error: Invalid plan or organization")
            return
        
        # Show loading status
        try:
            self.set_sync_status("Loading Retained Habitats...")
            QCoreApplication.processEvents()
        except Exception:
            pass
        
        # After loading BNG Plan layers, also load Retained Habitats layer
        try:
            retained_manager = RetainedHabitatLayersManager()
            retained_layer = retained_manager.import_from_api(
                plan_id=plan_id,
                api_client=self.api_client,
                org_id=org_id,
                name="Retained Habitats"
            )
            if retained_layer:
                QgsMessageLog.logMessage("Loaded Retained Habitats layer via button.", "BNGAI Plugin", level=0)
                self.set_sync_status("Retained Habitats loaded")
            else:
                QgsMessageLog.logMessage("No Retained Habitats layer created (no data or error).", "BNGAI Plugin", level=1)
                self.set_sync_status("No Retained Habitats to load")
        except Exception as err:
            QgsMessageLog.logMessage(f"Error creating Retained Habitats layer: {str(err)}", "BNGAI Plugin", level=2)
            self.set_sync_status(f"Error loading Retained Habitats: {str(err)}")
        finally:
            pass
    
    def fetch_sync_status(self):
        """Fetch and update the sync status"""
        if not self.auth_manager.is_logged_in():
            self.set_sync_status("Please log in to view sync status")
            return
            
        try:
            # Get the current organization and project
            org_id = self.org_dropdown.currentData()
            project_id = self.project_dropdown.currentData()
            
            if not org_id or not project_id:
                self.set_sync_status("Please select an organization and project to view sync status")
                return
            
            # TODO: Implement actual sync status fetch from API
            # For now, just show a placeholder message
            self.set_sync_status("Sync status: Up to date\nLast synced: Just now")
            
        except Exception as e:
            self.set_sync_status(f"Error fetching sync status: {str(e)}")
            QgsMessageLog.logMessage(f"Error fetching sync status: {str(e)}", "BNGAI Plugin", level=2) 

    def sync_habitats(self):
        """Synchronize habitats with the server"""
        if not self.auth_manager.is_logged_in():
            self.set_sync_status("Please log in to sync habitats")
            self._show_login_required_message()
            return
            
        # Get the current organization and project
        org_id = self.org_dropdown.currentData()
        project_id = self.project_dropdown.currentData()
        
        if not org_id or not project_id:
            self.set_sync_status("Please select an organization and project to sync habitats")
            return

        # Get all BNG Plan layers
        bng_plan_layers = []
        current_plan_id = None
        
        # If there are selected features in the active layer, only sync that layer
        active_layer = self.iface.activeLayer() if self.iface else None
        if active_layer and active_layer.selectedFeatureCount() > 0:
            bngai_id = active_layer.customProperty('bngai_id')
            if bngai_id and '_plan_' in bngai_id:  # Only consider plan layers
                try:
                    parts = bngai_id.split('_')
                    if len(parts) == 3:
                        current_plan_id = parts[0]
                        bng_plan_layers.append(active_layer)
                except Exception as e:
                    QgsMessageLog.logMessage(f"Error parsing active layer ID: {str(e)}", "BNGAI Plugin", level=2)
        else:
            # Get all layers from the project
            for layer in QgsProject.instance().mapLayers().values():
                if not layer.isValid():
                    continue
                    
                bngai_id = layer.customProperty('bngai_id')
                if not bngai_id or '_plan_' not in bngai_id:  # Only consider plan layers
                    continue
                    
                try:
                    parts = bngai_id.split('_')
                    if len(parts) == 3:
                        plan_id = parts[0]
                        # If we haven't found a plan ID yet, use this one
                        if not current_plan_id:
                            current_plan_id = plan_id
                        # Only include layers from the same plan
                        if plan_id == current_plan_id:
                            bng_plan_layers.append(layer)
                except Exception as e:
                    QgsMessageLog.logMessage(f"Error parsing layer ID: {str(e)}", "BNGAI Plugin", level=2)
                    continue

        if not bng_plan_layers:
            self.set_sync_status("No valid BNG Plan layers found")
            return
            
        if not current_plan_id:
            self.set_sync_status("Could not determine BNG Plan ID")
            return

        # Log what we're about to sync
        QgsMessageLog.logMessage(f"Syncing {len(bng_plan_layers)} layers for plan {current_plan_id}", "BNGAI Plugin", level=0)
        for layer in bng_plan_layers:
            QgsMessageLog.logMessage(f"Layer to sync: {layer.name()} ({layer.customProperty('bngai_id')})", "BNGAI Plugin", level=0)
            
        # Disable sync button while processing
        self.sync_habitats_button.setEnabled(False)
        self.sync_habitats_button.setText("Syncing...")
        QCoreApplication.processEvents()  # Update UI
        
        try:
            # Use the habitat sync manager to handle the sync
            success, message, html_summary, csv_path = self.habitat_sync_manager.sync_habitats(bng_plan_layers, current_plan_id, org_id)
            
            # Create a custom dialog to show the results
            dialog = QDialog(self)
            dialog.setWindowTitle("Sync Results")
            dialog.setMinimumWidth(600)
            dialog.setMinimumHeight(400)
            
            # Create layout
            layout = QVBoxLayout(dialog)
            
            # Add HTML summary in a QTextEdit
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setHtml(html_summary)
            layout.addWidget(text_edit)
            
            # Add buttons
            button_layout = QHBoxLayout()
            
            # Add Open CSV button if we have a CSV file
            if csv_path:
                open_csv_button = QPushButton("Open CSV")
                open_csv_button.clicked.connect(lambda: self._open_csv(csv_path))
                button_layout.addWidget(open_csv_button)
            
            # Add Close button
            close_button = QPushButton("Close")
            close_button.clicked.connect(dialog.accept)
            button_layout.addWidget(close_button)
            
            layout.addLayout(button_layout)
            
            # Show the dialog
            dialog.exec_()
            
            # Update status text
            self.set_sync_status(message)
                
        except Exception as e:
            error_msg = str(e)
            self.set_sync_status(f"Error syncing habitats: {error_msg}")
            QgsMessageLog.logMessage(f"Error syncing habitats: {error_msg}", "BNGAI Plugin", level=2)
            
            # Show error dialog
            error_box = QMessageBox()
            error_box.setIcon(QMessageBox.Critical)
            error_box.setWindowTitle("Sync Error")
            error_box.setText("Failed to sync habitats")
            error_box.setDetailedText(error_msg)
            error_box.setStandardButtons(QMessageBox.Ok)
            error_box.exec_()
            
        finally:
            self.sync_habitats_button.setEnabled(True)
            self.sync_habitats_button.setText("Sync Habitats")
            
    def _open_csv(self, csv_path):
        """Open the CSV file with the default application"""
        import subprocess
        import platform
        
        try:
            if platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', csv_path])
            elif platform.system() == 'Windows':
                subprocess.run(['start', csv_path], shell=True)
            else:  # Linux
                subprocess.run(['xdg-open', csv_path])
        except Exception as e:
            QgsMessageLog.logMessage(f"Error opening CSV file: {str(e)}", "BNGAI Plugin", level=2)
            QMessageBox.warning(self, "Error", f"Could not open CSV file: {str(e)}")
    
    def verify_layer_properties(self):
        """Verify custom properties of all layers in the project"""
        layers = QgsProject.instance().mapLayers().values()
        
        QgsMessageLog.logMessage("Verifying layer custom properties:", "BNGAI Plugin", level=0)
        for layer in layers:
            if not layer.isValid():
                continue
                
            bngai_id = layer.customProperty('bngai_id')
            if bngai_id:
                QgsMessageLog.logMessage(f"Layer '{layer.name()}' has bngai_id: {bngai_id}", "BNGAI Plugin", level=0)
            else:
                QgsMessageLog.logMessage(f"Layer '{layer.name()}' has no bngai_id property", "BNGAI Plugin", level=0)
                
    def _update_feature_with_server_data(self, feature, server_data):
        """Update a feature with data from the server"""
        try:
            # Convert GeoJSON geometry to WKT
            wkt_geometry = LayersUtils.geojson_to_wkt(server_data.get('geometry'))
            if not wkt_geometry:
                QgsMessageLog.logMessage("Failed to convert geometry to WKT", "BNGAI Plugin", level=2)
                return False
                
            # Create new geometry from WKT
            new_geometry = QgsGeometry.fromWkt(wkt_geometry)
            if not new_geometry or not new_geometry.isGeosValid():
                QgsMessageLog.logMessage("Invalid geometry from server", "BNGAI Plugin", level=2)
                return False

            # Update feature geometry
            feature.setGeometry(new_geometry)
            
            # Update feature attributes if they exist in server data
            if 'habitatClassification' in server_data:
                habitat_class = server_data['habitatClassification']
                
                # Update aiDash classification
                if 'aiDash' in habitat_class and habitat_class['aiDash']:
                    ai_dash = habitat_class['aiDash']
                    if 'code' in ai_dash:
                        feature['aiDashCode'] = ai_dash['code']
                    if 'label' in ai_dash:
                        feature['aiDashLabel'] = ai_dash['label']
                
                # Update custom classification
                if 'custom' in habitat_class and habitat_class['custom']:
                    custom = habitat_class['custom']
                    if 'code' in custom:
                        feature['customCode'] = custom['code']
                    if 'label' in custom:
                        feature['customLabel'] = custom['label']
                    if 'group' in custom:
                        feature['customGroup'] = custom['group']
                    if 'shapeType' in custom:
                        feature['customShapeType'] = custom['shapeType']
            
            # Update other attributes
            if 'treeSize' in server_data:
                feature['treeSize'] = server_data['treeSize']
            if 'activityType' in server_data:
                feature['activityType'] = server_data['activityType']
            
            QgsMessageLog.logMessage(f"Successfully updated feature {feature.id()} with server data", "BNGAI Plugin", level=0)
            return True
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error updating feature with server data: {str(e)}", "BNGAI Plugin", level=2)
            return False
                
    def on_merge_clicked(self):
        """Handle merge button click: call merge_selected_features and show result."""
        layer = None
        if self.iface:
            layer = self.iface.activeLayer()
        if not layer or not layer.isValid():
            QMessageBox.warning(self, "Merge Features", "No valid layer selected.")
            return
        result, merged_feature, message = self.feature_manager.merge_selected_features(layer)
        if result:
            QMessageBox.information(self, "Merge Features", "Successfully merged features.")
        else:
            QMessageBox.critical(self, "Merge Features", f"Failed to merge features: {message}")
                