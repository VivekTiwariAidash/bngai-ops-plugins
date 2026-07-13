"""
BNG AI QGIS Plugin - Main plugin class
"""
import os
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt, QSettings, QCoreApplication, QTimer, QTranslator
from qgis.core import QgsMessageLog

from .gui.dock_widget import BngAiDockWidget
from .gui.config_dialog import ConfigDialog
from .auth.auth_manager import AuthManager
from .utils.apiclient import ApiClient

class BngAiPlugin:
    """Main plugin class for BNG AI QGIS integration"""
    
    def __init__(self, iface):
        """Constructor.
        
        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        
        # Initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        
        # Initialize locale
        locale = str(QSettings().value('locale/userLocale', 'en_US', type=str))[:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'BngAi_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)
        
        # Initialize settings
        self.settings = {}
        
        # Declare instance attributes
        self.actions = []
        self.menu = 'BNG AI'  # Changed from self.tr(u'&BNG AI') to a simple string
        self.toolbar = self.iface.addToolBar('BNG AI')
        self.toolbar.setObjectName('BngAiToolbar')
        
        # Initialize the dock widget to None
        self.dock_widget = None
        
        # Initialize auth manager
        self.auth_manager = None
        
        # Initialize API client
        self.api_client = None
    
    def tr(self, message):
        """Get the translation for a string using Qt translation API.
        
        We implement this ourselves since we do not inherit QObject.
        
        :param message: String for translation.
        :type message: str, QString
        
        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('BngAiPlugin', message)
    
    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.
        
        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str
        
        :param text: Text that should be shown in menu items for this action.
        :type text: str
        
        :param callback: Function to be called when the action is triggered.
        :type callback: function
        
        :param enabled: A boolean flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled: bool
        
        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool
        
        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool
        
        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str
        
        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.
        :type whats_this: str
        
        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget
        
        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled)
        
        if status_tip is not None:
            action.setStatusTip(status_tip)
        
        if whats_this is not None:
            action.setWhatsThis(whats_this)
        
        if add_to_toolbar:
            self.toolbar.addAction(action)
        
        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)
        
        self.actions.append(action)
        
        return action
    
    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        # Create action that will start plugin configuration
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        self.add_action(
            icon_path,
            text='BNG AI',
            callback=self.run,
            parent=self.iface.mainWindow())
            
        # Add settings action
        settings_icon = ':/images/themes/default/mActionOptions.svg'
        self.add_action(
            settings_icon,
            text="Configure BNG AI",
            callback=self.show_settings,
            parent=self.iface.mainWindow(),
            status_tip="Configure BNG AI Plugin")
            
        # Initialize AuthManager
        self.auth_manager = AuthManager()
        
        # Initialize API client with auth_manager
        self.api_client = ApiClient(self.auth_manager)
        
        # Automatically show the dock widget when the plugin loads
        QTimer.singleShot(0, self.run)
    
    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""
        # Disconnect signals
        if self.dock_widget:
            self.dock_widget.closingPlugin.disconnect(self.onClosePlugin)
        
        # Remove dock widget
        if self.dock_widget:
            self.dock_widget.setParent(None)
            self.dock_widget = None
    
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        # Remove dock widget if it exists
        if self.dock_widget:
            self.dock_widget.setParent(None)
            self.dock_widget = None
        
        # Remove actions
        for action in self.actions:
            self.iface.removePluginMenu(
                self.menu,
                action)
            self.iface.removeToolBarIcon(action)
        
        # Remove toolbar
        del self.toolbar
    
    def run(self):
        """Run method that loads and starts the plugin"""
        if not self.dock_widget:
            # Create the dockable widget
            self.dock_widget = BngAiDockWidget(self.auth_manager, self.iface, self.iface.mainWindow())
            
            # Connect signals from dock widget
            self.dock_widget.closingPlugin.connect(self.onClosePlugin)
            
            # Connect API client to the dock widget
            projects_tab = self.dock_widget.projects_tab
            if projects_tab:
                projects_tab.set_api_client(self.api_client)
                
            # Add the dockable widget to the QGIS interface
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)
        
        # Show the dock widget if it's hidden
        self.dock_widget.show()
    
    def show_settings(self):
        """Show the settings dialog"""
        dialog = ConfigDialog(self.iface.mainWindow())
        result = dialog.exec_()
        
        if result:
            # Update auth manager and API client with new settings if needed
            settings = dialog.settings
            auth_url = settings.value("BNGAI/settings/auth_url")
            api_base_url = settings.value("BNGAI/settings/api_base_url")
            
            # Update auth manager if URL changed
            if auth_url:
                self.auth_manager.auth_url = auth_url
            
            # Update API client if URL changed
            if api_base_url:
                self.api_client.base_url = api_base_url
                
            QgsMessageLog.logMessage("Plugin settings updated", "BNGAI Plugin", level=0) 