"""
State management functionality for the projects tab.
"""
from qgis.PyQt.QtCore import QSettings

class StateManager:
    """Handles state management and persistence."""
    
    def __init__(self):
        """Initialize the state manager."""
        self.settings_prefix = "BNGAI/ProjectsTab/"
        self.settings_org_id_key = f"{self.settings_prefix}last_organization_id"
        self.settings_org_name_key = f"{self.settings_prefix}last_organization_name"
        self.settings_project_id_key = f"{self.settings_prefix}last_project_id"
        self.settings_project_name_key = f"{self.settings_prefix}last_project_name"
        self.settings_plan_id_key = f"{self.settings_prefix}last_plan_id"
        self.settings_plan_name_key = f"{self.settings_prefix}last_plan_name"
    
    def save_organization(self, org_id, org_name):
        """Save organization selection to settings."""
        settings = QSettings()
        settings.setValue(self.settings_org_id_key, org_id)
        settings.setValue(self.settings_org_name_key, org_name)
    
    def get_organization(self):
        """Get saved organization from settings."""
        settings = QSettings()
        org_id = settings.value(self.settings_org_id_key, "")
        org_name = settings.value(self.settings_org_name_key, "")
        return org_id, org_name
    
    def save_project(self, project_id, project_name):
        """Save project selection to settings."""
        settings = QSettings()
        settings.setValue(self.settings_project_id_key, project_id)
        settings.setValue(self.settings_project_name_key, project_name)
    
    def get_project(self):
        """Get saved project from settings."""
        settings = QSettings()
        project_id = settings.value(self.settings_project_id_key, "")
        project_name = settings.value(self.settings_project_name_key, "")
        return project_id, project_name
    
    def save_plan(self, plan_id, plan_name):
        """Save BNG plan selection to settings."""
        settings = QSettings()
        settings.setValue(self.settings_plan_id_key, plan_id)
        settings.setValue(self.settings_plan_name_key, plan_name)
    
    def get_plan(self):
        """Get saved BNG plan from settings."""
        settings = QSettings()
        plan_id = settings.value(self.settings_plan_id_key, "")
        plan_name = settings.value(self.settings_plan_name_key, "")
        return plan_id, plan_name
    
    def clear_all(self):
        """Clear all saved state."""
        settings = QSettings()
        settings.remove(self.settings_org_id_key)
        settings.remove(self.settings_org_name_key)
        settings.remove(self.settings_project_id_key)
        settings.remove(self.settings_project_name_key)
        settings.remove(self.settings_plan_id_key)
        settings.remove(self.settings_plan_name_key) 