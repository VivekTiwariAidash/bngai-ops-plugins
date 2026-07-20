import os
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from .spike_checker_dialog import SpikeCheckerDialog


class SpikeCheckerPlugin:
    def __init__(self, iface):
        self.iface  = iface
        self.dialog = None
        self.action = None

    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        self.action = QAction(
            QIcon(icon_path),
            "Spike Error Checker",
            self.iface.mainWindow()
        )
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToVectorMenu("&Spike Error Checker", self.action)

    def unload(self):
        self.iface.removePluginVectorMenu("&Spike Error Checker", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        if self.dialog is None:
            self.dialog = SpikeCheckerDialog(self.iface)
        self.dialog.show()
        self.dialog.raise_()
