"""
MapDataFetcher - Module for handling API calls to fetch map data and create layers
"""
from qgis.core import QgsMessageLog
from qgis.PyQt.QtCore import QObject, pyqtSignal, pyqtSlot
import requests
import json
from ..layers import LayerFactory, GeometryHandler, BaseLayersManager, BNGPlanLayersManager

class MapDataFetcher(QObject):
    """
    Handles API calls to fetch map data and manages layer creation
    """
    
    # Define signals for async operations
    fetch_completed = pyqtSignal(dict)  # Emits created layers
    fetch_error = pyqtSignal(str)       # Emits error message
    fetch_started = pyqtSignal()        # Emits when fetch starts
    
    def __init__(self, api_client=None):
        """
        Initialize the map data fetcher
        
        Args:
            api_client: Optional API client instance
        """
        super().__init__()
        self.api_client = api_client
        self.baseline_layer_factory = LayerFactory(is_baseline=True)
        self.bng_plan_layer_factory = LayerFactory(is_baseline=False)
    
    @pyqtSlot(str, str, str)
    def fetch_baseline_data(self, plan_id, token, org_id=None):
        """
        Fetch baseline data for a plan and create layers
        
        Args:
            plan_id (str): Plan ID to fetch data for
            token (str): Authentication token
            org_id (str): Optional organization ID
        """
        self.fetch_started.emit()
        
        try:
            # Endpoint for baseline data
            url = f"plans/{plan_id}/baseline"
            
            # Prepare headers
            headers = {
                "Accept": "application/json",
                "Authorization": token
            }
            
            if org_id:
                headers["Organization-Id"] = org_id
            
            QgsMessageLog.logMessage(f"Fetching baseline data for plan: {plan_id}", "BNGAI Plugin", level=0)
            
            # Use API client if available, otherwise use requests
            if self.api_client:
                response = self.api_client.get(url, headers=headers)
            else:
                # Construct full URL - update this with your actual API base URL
                full_url = f"https://api-uat.bng.ai/bngai-web-service/v1/{url}"
                response = requests.get(full_url, headers=headers)
                
                # Convert requests response to dict
                if isinstance(response, requests.Response):
                    if response.status_code == 200:
                        response = response.json()
                    else:
                        self.fetch_error.emit(f"API error: {response.status_code} - {response.text}")
                        return
            
            # Create layers from API response
            layers = self.baseline_layer_factory.process_api_response(response)
            
            # Emit signal with created layers
            self.fetch_completed.emit(layers)
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error fetching baseline data: {str(e)}", "BNGAI Plugin", level=2)
            self.fetch_error.emit(f"Error fetching baseline data: {str(e)}")
    
    @pyqtSlot(str, str, str)
    def fetch_bng_plan_data(self, plan_id, token, org_id=None):
        """
        Fetch BNG plan data for a plan and create layers
        
        Args:
            plan_id (str): Plan ID to fetch data for
            token (str): Authentication token
            org_id (str): Optional organization ID
        """
        self.fetch_started.emit()
        
        try:
            # Endpoint for BNG plan data
            url = f"plans/{plan_id}/bngplan"
            
            # Prepare headers
            headers = {
                "Accept": "application/json",
                "Authorization": token
            }
            
            if org_id:
                headers["Organization-Id"] = org_id
            
            QgsMessageLog.logMessage(f"Fetching BNG plan data for plan: {plan_id}", "BNGAI Plugin", level=0)
            
            # Use API client if available, otherwise use requests
            if self.api_client:
                response = self.api_client.get(url, headers=headers)
            else:
                # Construct full URL - update this with your actual API base URL
                full_url = f"https://api-uat.bng.ai/bngai-web-service/v1/{url}"
                response = requests.get(full_url, headers=headers)
                
                # Convert requests response to dict
                if isinstance(response, requests.Response):
                    if response.status_code == 200:
                        response = response.json()
                    else:
                        self.fetch_error.emit(f"API error: {response.status_code} - {response.text}")
                        return
            
            # Create layers from API response
            layers = self.bng_plan_layer_factory.process_api_response(response)
            
            # Emit signal with created layers
            self.fetch_completed.emit(layers)
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error fetching BNG plan data: {str(e)}", "BNGAI Plugin", level=2)
            self.fetch_error.emit(f"Error fetching BNG plan data: {str(e)}")
    
    def calculate_net_gain(self, baseline_layers, bng_plan_layers):
        """
        Calculate net gain between baseline and BNG plan layers
        
        Args:
            baseline_layers (dict): Dictionary of baseline layers
            bng_plan_layers (dict): Dictionary of BNG plan layers
            
        Returns:
            dict: Dictionary of net gain results
        """
        try:
            results = {}
            
            # Get instances of layer managers
            base_manager = BaseLayersManager()
            bng_plan_manager = BNGPlanLayersManager()
            
            # Calculate net gain for trees if both layers exist
            if 'trees' in baseline_layers and 'trees' in bng_plan_layers:
                tree_success = bng_plan_manager.calculate_net_gain(
                    baseline_layers['trees'],
                    bng_plan_layers['trees'],
                    target_field="netGain"
                )
                results['trees'] = tree_success
            
            # Calculate net gain for watercourses if both layers exist
            if 'watercourses' in baseline_layers and 'watercourses' in bng_plan_layers:
                watercourse_success = bng_plan_manager.calculate_net_gain(
                    baseline_layers['watercourses'],
                    bng_plan_layers['watercourses'],
                    target_field="netGain"
                )
                results['watercourses'] = watercourse_success
            
            # Calculate net gain for plans if both layers exist
            if 'plans' in baseline_layers and 'plans' in bng_plan_layers:
                plan_success = bng_plan_manager.calculate_net_gain(
                    baseline_layers['plans'],
                    bng_plan_layers['plans'],
                    target_field="netGain"
                )
                results['plans'] = plan_success
            
            return results
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error calculating net gain: {str(e)}", "BNGAI Plugin", level=2)
            return {} 