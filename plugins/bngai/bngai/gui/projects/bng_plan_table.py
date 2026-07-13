"""
BNG Plan Table - Table view for displaying BNG plans with pagination
"""
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTableWidget, QTableWidgetItem, QLabel, QSpinBox)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.core import QgsMessageLog

class BNGPlanDropdownManager:
    """
    Helper class to populate a QComboBox with BNG plans using the existing API logic.
    """
    def __init__(self, api_client, combo_box):
        """Initialize the dropdown manager"""
        self.api_client = api_client
        self.combo_box = combo_box

    def load_plans(self, site_id, org_id, limit=1000, offset=0):
        """
        Fetch BNG plans for the given site and populate the combo box.
        
        Args:
            site_id (str): Site ID to fetch plans for
            org_id (str): Organization ID
            limit (int): Maximum number of plans to fetch
            offset (int): Offset for pagination
        """
        self.combo_box.clear()
        result = self.api_client.get_bng_plans(site_id, org_id)
        
        if result and "rows" in result:
            for plan in result["rows"]:
                name = plan.get("title") or plan.get("planId", "")
                plan_id = plan.get("planId", "")
                if name and plan_id:
                    self.combo_box.addItem(name, plan_id)
                    QgsMessageLog.logMessage(f"Added BNG plan: {name} (ID: {plan_id})", "BNGAI Plugin", level=0)
        else:
            QgsMessageLog.logMessage("No BNG plans found or invalid response format", "BNGAI Plugin", level=2) 