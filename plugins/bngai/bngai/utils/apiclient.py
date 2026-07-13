"""
API Client for making requests to the BNG AI service.
"""
import os
import json
import requests
import tempfile
from pathlib import Path

from qgis.core import (QgsVectorLayer, QgsProject, QgsMessageLog, 
                      QgsFeature, QgsGeometry, QgsPoint, QgsLineString,
                      QgsSymbol, QgsSimpleLineSymbolLayer, QgsSimpleFillSymbolLayer,
                      QgsLineSymbol, QgsMarkerSymbol, QgsMarkerLineSymbolLayer, 
                      QgsSimpleMarkerSymbolLayer, QgsUnitTypes, QgsTask, QgsWkbTypes,
                      QgsField, QgsPointXY, QgsCoordinateReferenceSystem)
from qgis.PyQt.QtCore import Qt, QVariant
from qgis.PyQt.QtGui import QColor

from .api_config import ApiConfig

try:
    import fiona
    HAS_FIONA = True
except ImportError:
    HAS_FIONA = False

def create_line_vector_layer(features, name="Line Layer"):
    """Create a memory vector layer for line features
    
    :param features: List of GeoJSON feature dictionaries
    :type features: list
    :param name: Name for the layer
    :type name: str
    
    :returns: QgsVectorLayer or None if creation fails
    :rtype: QgsVectorLayer or None
    """
    try:
        QgsMessageLog.logMessage(f"Creating in-memory line vector layer '{name}'", "BNGAI Plugin", level=0)
        
        # Import all necessary QGIS classes
        from qgis.core import (
            QgsSingleSymbolRenderer, QgsMarkerSymbol, QgsLineSymbol,
            QgsMapUnitScale, QgsUnitTypes, QgsSimpleLineSymbolLayer,
            QgsMarkerLineSymbolLayer, QgsCoordinateReferenceSystem,
            QgsCoordinateTransform, QgsProject
        )
        from qgis.PyQt.QtGui import QColor
        
        # Filter for line features only
        line_features = []
        for feature in features:
            if 'geometry' in feature and feature['geometry'] and 'type' in feature['geometry']:
                if feature['geometry']['type'] == 'LineString':
                    line_features.append(feature)
        
        if not line_features:
            QgsMessageLog.logMessage("No line features found", "BNGAI Plugin", level=1)
            return None
        
        QgsMessageLog.logMessage(f"Found {len(line_features)} line features", "BNGAI Plugin", level=0)
        
        # Try using both British National Grid and WGS84
        for crs_epsg in ['EPSG:4326', 'EPSG:27700']:
            # Create a memory vector layer with the specific CRS
            layer = QgsVectorLayer(f"LineString?crs={crs_epsg}", f"{name} ({crs_epsg})", "memory")
            
            if not layer.isValid():
                QgsMessageLog.logMessage(f"Failed to create memory vector layer with {crs_epsg}", "BNGAI Plugin", level=2)
                continue
            
            # Set up fields based on feature properties
            provider = layer.dataProvider()
            field_names = set()
            
            # Collect all unique field names from all features
            for feature in line_features:
                if 'properties' in feature and feature['properties']:
                    for field_name in feature['properties'].keys():
                        field_names.add(field_name)
            
            # Add fields to the layer
            fields = []
            for field_name in field_names:
                field = QgsField(field_name, QVariant.String)
                fields.append(field)
            
            if fields:
                provider.addAttributes(fields)
                layer.updateFields()
            
            # Add features to the layer
            qgis_features = []
            for feature_json in line_features:
                qgis_feature = QgsFeature()
                
                # Get coordinates
                coords = feature_json['geometry']['coordinates']
                
                # Log the coordinates for debugging
                QgsMessageLog.logMessage(f"Line coordinates: {coords}", "BNGAI Plugin", level=0)
                
                # Create geometry
                points = []
                for point in coords:
                    x, y = point[0], point[1]
                    points.append(QgsPointXY(x, y))
                
                # Create line geometry
                geometry = QgsGeometry.fromPolylineXY(points)
                
                if not geometry or geometry.isEmpty():
                    QgsMessageLog.logMessage("Failed to create geometry or geometry is empty", "BNGAI Plugin", level=2)
                    continue
                
                qgis_feature.setGeometry(geometry)
                
                # Set attributes
                attrs = []
                for field in layer.fields():
                    field_name = field.name()
                    if 'properties' in feature_json and field_name in feature_json['properties']:
                        value = feature_json['properties'][field_name]
                        attrs.append(str(value) if value is not None else "")
                    else:
                        attrs.append(None)
                
                qgis_feature.setAttributes(attrs)
                qgis_features.append(qgis_feature)
            
            # Add all features at once
            if provider.addFeatures(qgis_features):
                QgsMessageLog.logMessage(f"Added {len(qgis_features)} features to layer", "BNGAI Plugin", level=0)
            else:
                QgsMessageLog.logMessage("Failed to add features to layer", "BNGAI Plugin", level=2)
            
            # Update layer's extent
            layer.updateExtents()
            
            # Create a specialized symbol for high visibility
            # Use a marker line symbol layer for better visibility
            marker_line = QgsMarkerLineSymbolLayer()
            marker_line.setPlacement(QgsMarkerLineSymbolLayer.Interval)
            marker_line.setInterval(10)  # Place markers every 10 map units
            
            # Create a marker symbol for the line
            marker = QgsMarkerSymbol.createSimple({
                'name': 'circle',
                'color': '255,0,0,255',
                'size': '4',
                'outline_color': '0,0,0,255',
                'outline_width': '0.5'
            })
            marker_line.setSubSymbol(marker)
            
            # Create a regular line symbol as base
            line_symbol = QgsLineSymbol()
            line_symbol.changeSymbolLayer(0, QgsSimpleLineSymbolLayer.create({
                'color': '255,0,0,255',
                'width': '2',
                'line_style': 'solid',
                'capstyle': 'square'
            }))
            
            # Add the marker line as an additional symbol layer
            line_symbol.appendSymbolLayer(marker_line)
            
            # Apply the symbol to the layer
            renderer = QgsSingleSymbolRenderer(line_symbol)
            layer.setRenderer(renderer)
            
            # Force repaint
            layer.triggerRepaint()
            
            QgsMessageLog.logMessage(f"Successfully created line layer with {len(qgis_features)} features using {crs_epsg}", "BNGAI Plugin", level=0)
            
            # Add layer to project
            QgsProject.instance().addMapLayer(layer)
            
            # Try to add a separate helper layer with big points at each vertex
            try:
                # Create a point layer for vertices
                point_layer = QgsVectorLayer(f"Point?crs={crs_epsg}", f"{name} Vertices ({crs_epsg})", "memory")
                
                if point_layer.isValid():
                    point_provider = point_layer.dataProvider()
                    
                    # Add vertex features
                    vertex_features = []
                    
                    for feature_json in line_features:
                        coords = feature_json['geometry']['coordinates']
                        for i, point in enumerate(coords):
                            pt_feature = QgsFeature()
                            pt_feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(point[0], point[1])))
                            vertex_features.append(pt_feature)
                    
                    point_provider.addFeatures(vertex_features)
                    point_layer.updateExtents()
                    
                    # Style the points to be large and visible
                    point_symbol = QgsMarkerSymbol.createSimple({
                        'name': 'circle',
                        'color': '0,0,255,255',  # Blue
                        'size': '8',  # Big points
                        'outline_color': '255,255,255,255',
                        'outline_width': '1'
                    })
                    
                    point_layer.renderer().setSymbol(point_symbol)
                    point_layer.triggerRepaint()
                    
                    # Add to project
                    QgsProject.instance().addMapLayer(point_layer)
                    QgsMessageLog.logMessage(f"Added vertex helper layer with {len(vertex_features)} points", "BNGAI Plugin", level=0)
            except Exception as e:
                QgsMessageLog.logMessage(f"Error creating vertex layer: {str(e)}", "BNGAI Plugin", level=1)
            
            return layer
        
        # If we got here, both CRS attempts failed
        QgsMessageLog.logMessage("Failed to create layer with any CRS", "BNGAI Plugin", level=2)
        return None
        
    except Exception as e:
        import traceback
        QgsMessageLog.logMessage(f"Error creating line vector layer: {str(e)}", "BNGAI Plugin", level=2)
        QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
        return None

class ApiClient:
    """
    API Client for the BNG AI web service
    """
    
    def __init__(self, auth_manager=None):
        """Initialize the API client"""
        self.base_url = ApiConfig.get_api_base_url()
        self.auth_manager = auth_manager
        self.logger = QgsMessageLog
        
        # Log the API configuration being used
        env = ApiConfig.get_active_environment()
        self.logger.logMessage(
            f"ApiClient initialized using {ApiConfig.ENVIRONMENTS[env]['name']} environment",
            "BNGAI Plugin", level=0
        )
    
    def get_auth_headers(self):
        """Get authorization headers for API requests"""
        headers = {'Content-Type': 'application/json'}
        
        # First check if we have a directly set token
        if hasattr(self, 'auth_token') and self.auth_token:
            headers['Authorization'] = self.auth_token
            return headers
            
        # Otherwise try to get from auth manager
        if self.auth_manager and self.auth_manager.is_logged_in():
            token = self.auth_manager.get_token()
            if token:
                headers['Authorization'] = token
                
        return headers
    
    def set_auth_token(self, token):
        """Set the authentication token directly
        
        :param token: The authentication token to use
        :type token: str
        """
        self.auth_token = token
        self.logger.logMessage("API client token set", "BNGAI Plugin", level=0)
    
    def get_authenticated_user(self):
        """Get the authenticated user"""
        if not self.auth_manager or not self.auth_manager.is_logged_in():
            return None
            
        return self.auth_manager.get_user_info()
        
    def get_projects(self):
        """Get all available projects"""
        if not self.auth_manager or not self.auth_manager.is_logged_in():
            self.logger.logMessage("Cannot fetch projects: Not logged in", "BNGAI Plugin", level=2)
            return []
            
        try:
            url = f"{self.base_url}/bng/projects"
            headers = self.get_auth_headers()
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data and isinstance(data["data"], list):
                    return data["data"]
                else:
                    return []
            else:
                self.logger.logMessage(f"Failed to fetch projects: {response.status_code}", "BNGAI Plugin", level=2)
                return []
        except Exception as e:
            self.logger.logMessage(f"Error fetching projects: {str(e)}", "BNGAI Plugin", level=2)
            return []
    
    def get_plans(self, project_id=None):
        """Get plans for a project"""
        if not self.auth_manager or not self.auth_manager.is_logged_in():
            self.logger.logMessage("Cannot fetch plans: Not logged in", "BNGAI Plugin", level=2)
            return []
            
        try:
            url = f"{self.base_url}/bng/plans"
            if project_id:
                url = f"{url}?projectId={project_id}"
                
            headers = self.get_auth_headers()
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data and isinstance(data["data"], list):
                    return data["data"]
                else:
                    return []
            else:
                self.logger.logMessage(f"Failed to fetch plans: {response.status_code}", "BNGAI Plugin", level=2)
                return []
        except Exception as e:
            self.logger.logMessage(f"Error fetching plans: {str(e)}", "BNGAI Plugin", level=2)
            return []
    
    def get_plan_details(self, plan_id):
        """Get details for a specific plan"""
        if not self.auth_manager or not self.auth_manager.is_logged_in():
            self.logger.logMessage("Cannot fetch plan details: Not logged in", "BNGAI Plugin", level=2)
            return None
            
        try:
            url = f"{self.base_url}/bng/plans/{plan_id}"
            headers = self.get_auth_headers()
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data:
                    return data["data"]
                else:
                    return None
            else:
                self.logger.logMessage(f"Failed to fetch plan details: {response.status_code}", "BNGAI Plugin", level=2)
                return None
        except Exception as e:
            self.logger.logMessage(f"Error fetching plan details: {str(e)}", "BNGAI Plugin", level=2)
            return None

class GraphQLClient:
    @staticmethod
    def get_default_headers(authorization=None, organization_id=None):
        """Get default headers for GraphQL requests"""
        headers = {
            'content-type': 'application/json',
            'client-code': 'bngai-web-client',
            'origin': ApiConfig.get_header_origin(),
            'referer': ApiConfig.get_header_referer(),
        }
        
        if authorization:
            headers['authorization'] = authorization
            
        if organization_id:
            headers['organization'] = organization_id
            
        return headers

    @staticmethod
    def getHabitatGeometry():
        """Return GraphQL query for habitat geometry"""
        return """
            query GetHabitatGeometry($siteRevisionId: String!, $applicationComponent: String!) {
                getHabitatGeometry(siteRevisionId: $siteRevisionId, applicationComponent: $applicationComponent) {
                    site {
                        boundaryGeometry {
                            type
                            coordinates
                        }
                        habitats {
                            name
                            habitatCode
                            habitatVariants {
                                name
                                habitatVariantCode
                                geometry {
                                    type
                                    coordinates
                                }
                            }
                        }
                    }
                }
            }
        """
    
    @staticmethod
    def getBngPlanDetail():
        """Return GraphQL query for BNG plan details"""
        return """
            query ($bngPlanId: UUID!) {
              bngPlanDetail(input: {bngPlanId: $bngPlanId}) {
                name
                status
                createdBy
                isPlanSubmittable
                developmentPlan {
                  id
                  name
                  __typename
                }
                bngPlanHabitats {
                  id
                  geometry
                  habitatClassification {
                    aiDash {
                      code
                      label
                      __typename
                    }
                    custom {
                      code
                      label
                      group
                      shapeType
                      __typename
                    }
                    __typename
                  }
                  treeSize
                  activityType
                  __typename
                }
                bngPlanChanges {
                  code
                  activityType
                  changeScenario
                  baseHabitatData {
                    baseHabitatId
                    habitatReferenceId
                    habitatClassification {
                      aiDash {
                        code
                        label
                        __typename
                      }
                      custom {
                        code
                        label
                        group
                        shapeType
                        __typename
                      }
                      __typename
                    }
                    area
                    length
                    condition
                    distinctiveness
                    strategicSignificance
                    riparianEncroachment
                    watercourseEncroachment
                    watercourseAndRiparianEncroachment
                    __typename
                  }
                  planHabitatData {
                    planHabitatId
                    habitatClassification {
                      aiDash {
                        code
                        label
                        __typename
                      }
                      custom {
                        code
                        label
                        group
                        shapeType
                        __typename
                      }
                      __typename
                    }
                    area
                    length
                    condition
                    distinctiveness
                    strategicSignificance
                    riparianEncroachment
                    watercourseEncroachment
                    watercourseAndRiparianEncroachment
                    __typename
                  }
                  tenure {
                    numberOfYears
                    tenureRange
                    __typename
                  }
                  biodiversityUnitChange
                  assessorComment
                  __typename
                }
                __typename
              }
            }
        """
    
    @staticmethod
    def get_default_variables(site_revision_id=None, application_component=None):
        """Return default variables for GraphQL query"""
        return {
            "siteRevisionId": site_revision_id or "9113d037-9577-40b7-bd66-e9738536d99e",
            "applicationComponent": application_component or "BNG_PROJECT_OVERVIEW_MAP"
        }
    
    @staticmethod
    def get_bng_plan_variables(bng_plan_id):
        """Return variables for BNG plan query
        
        :param bng_plan_id: BNG plan ID (UUID format)
        :type bng_plan_id: str
        
        :returns: Dictionary of variables
        :rtype: dict
        """
        # Make sure bng_plan_id is a string
        if not isinstance(bng_plan_id, str):
            bng_plan_id = str(bng_plan_id)
            
        # Remove any surrounding quotes if present
        bng_plan_id = bng_plan_id.strip('"\'')
        
        return {
            "bngPlanId": bng_plan_id  # Should be a valid UUID string
        }

class GraphQLTask(QgsTask):
    """Task for asynchronous GraphQL queries"""
    
    def __init__(self, description, url, query, variables, headers, plugin_instance):
        super().__init__(description, QgsTask.CanCancel)
        self.url = url
        self.query = query
        self.variables = variables
        self.headers = headers
        self.data = None
        self.error = None
        self.progress = 0
        self.completed = False
        self.plugin_instance = plugin_instance
    
    def extract_geometry_data(self, data):
        """Extract geometry data from the response
        
        :param data: The response data dictionary
        :type data: dict
        
        :returns: Tuple of (success, coordinates, error_message)
        :rtype: tuple
        """
        try:
            if 'data' in data:
                if 'getHabitatGeometry' in data['data']:
                    if 'site' in data['data']['getHabitatGeometry']:
                        if 'boundaryGeometry' in data['data']['getHabitatGeometry']['site']:
                            geometry_data = data['data']['getHabitatGeometry']['site']['boundaryGeometry']
                            if 'coordinates' in geometry_data:
                                coords = geometry_data['coordinates']
                                if coords:
                                    return True, coords, None
                                else:
                                    return False, None, "No coordinates found in geometry data"
                            else:
                                return False, None, "No coordinates field in boundary geometry"
                        else:
                            return False, None, "boundaryGeometry not found in site"
                    else:
                        return False, None, "site not found in getHabitatGeometry"
                else:
                    return False, None, "getHabitatGeometry not found in data"
            else:
                return False, None, "No 'data' field in response"
        except Exception as e:
            return False, None, f"Error extracting geometry data: {str(e)}"
    
    def run(self):
        """Run the GraphQL task"""
        try:
            self.setProgress(10)
            QgsMessageLog.logMessage("Starting GraphQL data fetch", "BNGAI Plugin", level=0)
            
            self.setProgress(20)
            QgsMessageLog.logMessage(f"Making request to: {self.url}", "BNGAI Plugin", level=0)
            
            # Log the request details (excluding sensitive headers)
            safe_headers = self.headers.copy()
            if 'authorization' in safe_headers:
                safe_headers['authorization'] = 'Bearer [REDACTED]'
            QgsMessageLog.logMessage(f"Request headers: {json.dumps(safe_headers, indent=2)}", "BNGAI Plugin", level=0)
            QgsMessageLog.logMessage(f"Request variables: {json.dumps(self.variables, indent=2)}", "BNGAI Plugin", level=0)
            
            self.setProgress(30)
            QgsMessageLog.logMessage("Sending POST request...", "BNGAI Plugin", level=0)
            
            # Add timeout to the request
            query_payload = {
                'query': self.query,
                'variables': self.variables
            }
            
            # Log the exact query being sent
            
            
            response = requests.post(
                self.url,
                json=query_payload,
                headers=self.headers,
                timeout=30  # 30 second timeout
            )
            
            self.setProgress(60)
            QgsMessageLog.logMessage(f"Response status code: {response.status_code}", "BNGAI Plugin", level=0)
            
            if response.status_code == 200:
                self.setProgress(80)
                QgsMessageLog.logMessage("Parsing response JSON...", "BNGAI Plugin", level=0)
                self.data = response.json()
                
                # Extract geometry data
                success, coords, error = self.extract_geometry_data(self.data)
                if success:
                    QgsMessageLog.logMessage("Boundary Geometry Coordinates:", "BNGAI Plugin", level=0)
                    QgsMessageLog.logMessage(json.dumps(coords, indent=2), "BNGAI Plugin", level=0)
                    
                    # Create GeoJSON structure
                    geojson_data = {
                        "type": "Polygon",
                        "coordinates": coords
                    }
                    
                    # Create vector layer from GeoJSON using the plugin instance
                    layer = self.plugin_instance.create_vector_layer_from_geojson(geojson_data)
                    if layer:
                        # Add layer to the project
                        QgsProject.instance().addMapLayer(layer)
                        QgsMessageLog.logMessage("Vector layer created and added to map", "BNGAI Plugin", level=0)
                    else:
                        QgsMessageLog.logMessage("Failed to create vector layer", "BNGAI Plugin", level=2)
                else:
                    QgsMessageLog.logMessage(error, "BNGAI Plugin", level=2)
                
                QgsMessageLog.logMessage("Successfully fetched and parsed data", "BNGAI Plugin", level=0)
                self.setProgress(100)
                self.completed = True
                return True
            else:
                self.error = f"Failed to fetch data. Status code: {response.status_code}\nResponse: {response.text}"
                QgsMessageLog.logMessage(self.error, "BNGAI Plugin", level=2)
                self.setProgress(100)
                return False
                
        except requests.Timeout:
            self.error = "Request timed out after 30 seconds"
            QgsMessageLog.logMessage(self.error, "BNGAI Plugin", level=2)
            self.setProgress(100)
            return False
        except requests.ConnectionError:
            self.error = "Connection error occurred"
            QgsMessageLog.logMessage(self.error, "BNGAI Plugin", level=2)
            self.setProgress(100)
            return False
        except Exception as e:
            self.error = f"An error occurred: {str(e)}"
            QgsMessageLog.logMessage(self.error, "BNGAI Plugin", level=2)
            self.setProgress(100)
            return False

    def finished(self, result):
        """Called when the task is finished"""
        if result:
            QgsMessageLog.logMessage("Task completed successfully", "BNGAI Plugin", level=0)
        else:
            QgsMessageLog.logMessage(f"Task failed: {self.error}", "BNGAI Plugin", level=2)

class BngPlanGraphQLTask(QgsTask):
    """Task for asynchronous BNG Plan GraphQL queries"""
    
    def __init__(self, description, url, query, variables, headers, plugin_instance):
        super().__init__(description, QgsTask.CanCancel)
        self.url = url
        self.query = query
        self.variables = variables
        self.headers = headers
        self.data = None
        self.error = None
        self.progress = 0
        self.completed = False
        self.plugin_instance = plugin_instance
        # Initialize KML attributes
        self.kml_path = None
        self.kml_name = None
        # Initialize GeoJSON attributes
        self.geojson_path = None
        self.geojson_name = None
    
    def extract_bng_plan_data(self, data):
        """Extract BNG plan data from the response and format as GeoJSON
        
        :param data: The response data dictionary
        :type data: dict
        
        :returns: Tuple of (success, bng_plan_data, geojson_features, error_message)
        :rtype: tuple
        """
        
        try:
            if not data:
                return False, None, [], "Response data is empty"
                
            if 'data' not in data:
                return False, None, [], "No 'data' field in response"
                
            if 'bngPlanDetail' not in data['data']:
                # Log the actual response data to see what we got
                QgsMessageLog.logMessage(f"Response data structure: {json.dumps(data, indent=2)}", "BNGAI Plugin", level=2)
                return False, None, [], "bngPlanDetail not found in data"
                
            bng_plan = data['data']['bngPlanDetail']
            if not bng_plan:
                return False, None, [], "BNG plan not found"
            
            # Log the bng_plan structure for debugging
            
            
            # Extract all habitat geometries and format as GeoJSON features
            geojson_features = []
            
            # Check if bngPlanHabitats exists and is not None
            if 'bngPlanHabitats' not in bng_plan:
                QgsMessageLog.logMessage("bngPlanHabitats field is missing in the response", "BNGAI Plugin", level=1)
                return True, bng_plan, [], None
            
            if bng_plan['bngPlanHabitats'] is None:
                QgsMessageLog.logMessage("bngPlanHabitats field is null in the response", "BNGAI Plugin", level=1)
                return True, bng_plan, [], None
                
            # Check if bngPlanHabitats is an empty array
            if len(bng_plan['bngPlanHabitats']) == 0:
                QgsMessageLog.logMessage("bngPlanHabitats is an empty array", "BNGAI Plugin", level=1)
                return True, bng_plan, [], None
                
            # Log habitat count
            QgsMessageLog.logMessage(f"Found {len(bng_plan['bngPlanHabitats'])} habitats in BNG plan", "BNGAI Plugin", level=0)
            
            # Log first habitat for debugging
            
            
            # Now iterate over the habitats safely
            for i, habitat in enumerate(bng_plan['bngPlanHabitats']):
                if not habitat:
                    QgsMessageLog.logMessage(f"Habitat {i} is null, skipping", "BNGAI Plugin", level=1)
                    continue
                    
                # Log habitat structure for debugging
                
                
                if 'geometry' not in habitat:
                    QgsMessageLog.logMessage(f"Habitat {i} has no geometry field, skipping", "BNGAI Plugin", level=1)
                    continue
                    
                if not habitat['geometry']:
                    QgsMessageLog.logMessage(f"Habitat {i} has null geometry, skipping", "BNGAI Plugin", level=1)
                    continue
                
                # Log the actual geometry type
                
                    
                try:
                    # Handle geometry data that could be a string or a dictionary
                    geometry_data = habitat['geometry']
                    
                    # If geometry is a string, try to parse it as JSON
                    if isinstance(geometry_data, str):
                        try:
                            geometry_data = json.loads(geometry_data)
                            QgsMessageLog.logMessage(f"Parsed geometry from JSON string for habitat {i}", "BNGAI Plugin", level=0)
                        except json.JSONDecodeError as e:
                            QgsMessageLog.logMessage(f"Failed to parse geometry JSON for habitat {i}: {str(e)}", "BNGAI Plugin", level=2)
                            continue
                    
                    # Log geometry type for debugging
                    
                    
                    # Ensure the geometry has the required structure for GeoJSON
                    if 'type' not in geometry_data or 'coordinates' not in geometry_data:
                        QgsMessageLog.logMessage(f"Habitat {i} geometry missing required fields (type or coordinates)", "BNGAI Plugin", level=1)
                        continue
                    
                    # Skip empty coordinates
                    if not geometry_data['coordinates']:
                        QgsMessageLog.logMessage(f"Habitat {i} has empty coordinates, skipping", "BNGAI Plugin", level=1)
                        continue
                    
                    # Verify coordinates structure based on geometry type
                    geom_type = geometry_data['type']
                    coords = geometry_data['coordinates']
                    
                    # Validate coordinate structure based on geometry type
                    try:
                        if geom_type == 'Point':
                            # Point coordinates should be [x, y]
                            if not isinstance(coords, list) or len(coords) < 2:
                                QgsMessageLog.logMessage(f"Invalid Point coordinates: {coords}", "BNGAI Plugin", level=2)
                                continue
                        elif geom_type == 'LineString':
                            # LineString coordinates should be array of points [[x1,y1], [x2,y2], ...]
                            if not isinstance(coords, list) or len(coords) < 2:
                                QgsMessageLog.logMessage(f"Invalid LineString coordinates - not enough points", "BNGAI Plugin", level=2)
                                continue
                            for point in coords:
                                if not isinstance(point, list) or len(point) < 2:
                                    QgsMessageLog.logMessage(f"Invalid LineString point: {point}", "BNGAI Plugin", level=2)
                                    continue
                        elif geom_type == 'Polygon':
                            # Polygon coordinates should be array of rings [[[x1,y1], [x2,y2], ...], [...]]
                            if not isinstance(coords, list) or len(coords) < 1:
                                QgsMessageLog.logMessage(f"Invalid Polygon coordinates - missing rings", "BNGAI Plugin", level=2)
                                continue
                            for ring in coords:
                                if not isinstance(ring, list) or len(ring) < 4:  # Polygons need at least 4 points (closed ring)
                                    QgsMessageLog.logMessage(f"Invalid Polygon ring - not enough points", "BNGAI Plugin", level=2)
                                    continue
                    except Exception as e:
                        QgsMessageLog.logMessage(f"Error validating coordinates for {geom_type}: {str(e)}", "BNGAI Plugin", level=2)
                        continue
                    
                    # Get habitat classification label if available
                    layer_name = f"BNG Habitat {i+1}"
                    
                    # Safely check for habitat classification
                    if habitat.get('habitatClassification'):
                        habitat_class = habitat['habitatClassification']
                        
                        # Check for custom classification
                        if habitat_class.get('custom') and habitat_class['custom'].get('label'):
                            label = habitat_class['custom']['label']
                            layer_name = f"BNG Habitat - {label}"
                        # Check for aiDash classification
                        elif habitat_class.get('aiDash') and habitat_class['aiDash'].get('label'):
                            label = habitat_class['aiDash']['label']
                            layer_name = f"BNG Habitat - {label}"
                    
                    # Ensure all property values are strings to avoid type issues
                    props = {
                        "id": str(habitat.get('id', '')),
                        "name": layer_name,
                        "treeSize": str(habitat.get('treeSize', '')) if habitat.get('treeSize') is not None else '',
                        "activityType": str(habitat.get('activityType', '')) if habitat.get('activityType') is not None else ''
                    }
                    
                    # Create a Feature GeoJSON with properties
                    feature_geojson = {
                        "type": "Feature",
                        "geometry": geometry_data,
                        "properties": props
                    }
                    
                   
                    
                    geojson_features.append(feature_geojson)
                    
                except Exception as e:
                    import traceback
                    QgsMessageLog.logMessage(f"Error processing habitat {i} geometry: {str(e)}", "BNGAI Plugin", level=2)
                    QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
                    continue
            
            if not geojson_features:
                QgsMessageLog.logMessage("No valid geometries found in any of the habitats", "BNGAI Plugin", level=1)
            else:
                QgsMessageLog.logMessage(f"Successfully created {len(geojson_features)} valid GeoJSON features", "BNGAI Plugin", level=0)
            
            return True, bng_plan, geojson_features, None
            
        except Exception as e:
            import traceback
            QgsMessageLog.logMessage(f"Error extracting BNG plan data: {str(e)}", "BNGAI Plugin", level=2)
            QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            return False, None, [], f"Error extracting BNG plan data: {str(e)}"
    
    def run(self):
        """Run the BNG Plan GraphQL task"""
        try:
            self.setProgress(10)
            QgsMessageLog.logMessage("Starting BNG Plan data fetch", "BNGAI Plugin", level=0)
            
            self.setProgress(20)
            QgsMessageLog.logMessage(f"Making request to: {self.url}", "BNGAI Plugin", level=0)
            
            # Log the request details (excluding sensitive headers)
            safe_headers = self.headers.copy()
            if 'authorization' in safe_headers:
                safe_headers['authorization'] = 'Bearer [REDACTED]'
            # Use json module directly to avoid naming conflict
            import json as json_module
            QgsMessageLog.logMessage(f"Request variables: {json_module.dumps(self.variables, indent=2)}", "BNGAI Plugin", level=0)
            
            self.setProgress(30)
            QgsMessageLog.logMessage("Sending POST request...", "BNGAI Plugin", level=0)
            
            # Add timeout to the request
            query_payload = {
                'query': self.query,
                'variables': self.variables
            }
            
            # Log the exact query being sent
            QgsMessageLog.logMessage(f"Query: {self.query}", "BNGAI Plugin", level=0)
            QgsMessageLog.logMessage(f"Variables: {json_module.dumps(self.variables)}", "BNGAI Plugin", level=0)
            
            response = requests.post(
                self.url,
                json=query_payload,
                headers=self.headers,
                timeout=30  # 30 second timeout
            )
            
            self.setProgress(60)
            QgsMessageLog.logMessage(f"Response status code: {response.status_code}", "BNGAI Plugin", level=0)
            
            if response.status_code == 200:
                self.setProgress(80)
                QgsMessageLog.logMessage("Parsing response JSON...", "BNGAI Plugin", level=0)
                self.data = response.json()
                
                # Extract BNG plan data
                success, bng_plan, geojson_features, error = self.extract_bng_plan_data(self.data)
                if success:
                    QgsMessageLog.logMessage("BNG Plan Data:", "BNGAI Plugin", level=0)
                    QgsMessageLog.logMessage(f"Found {len(geojson_features)} valid BNG plan habitat features", "BNGAI Plugin", level=0)
                    
                    # Process habitat geometries if available
                    if geojson_features and len(geojson_features) > 0:
                        # Import LayersUtils
                        from .layersUtils import LayersUtils
                        
                        # Create a descriptive layer name
                        layer_name = f"BNG Plan - {bng_plan.get('name', 'Unknown')}"
                        
                        # Create a feature collection with all habitats
                        feature_collection = {
                            "type": "FeatureCollection",
                            "features": geojson_features
                        }
                        
                        # Log how many features we're trying to add
                        QgsMessageLog.logMessage(f"Creating layer '{layer_name}' with {len(geojson_features)} features", "BNGAI Plugin", level=0)
                        
                        # Count geometry types for informational purposes
                        point_count = len([f for f in geojson_features if f.get('geometry', {}).get('type') == 'Point'])
                        line_count = len([f for f in geojson_features if f.get('geometry', {}).get('type') == 'LineString'])
                        polygon_count = len([f for f in geojson_features if f.get('geometry', {}).get('type') == 'Polygon'])
                        QgsMessageLog.logMessage(f"Feature counts: Points={point_count}, Lines={line_count}, Polygons={polygon_count}", "BNGAI Plugin", level=0)
                        
                        # Direct approach - create a simple GeoJSON file and load it with OGR
                        try:
                            import tempfile
                            import os
                            import json
                            
                            # Create a GeoJSON file
                            geojson_collection = {
                                "type": "FeatureCollection",
                                "features": geojson_features
                            }
                            
                            # Create a temporary file for GeoJSON
                            geojson_fd, geojson_path = tempfile.mkstemp(suffix=".geojson")
                            os.close(geojson_fd)
                            
                            # Write GeoJSON to file
                            with open(geojson_path, 'w') as f:
                                json.dump(geojson_collection, f)
                            
                            QgsMessageLog.logMessage(f"Created direct GeoJSON file at {geojson_path}", "BNGAI Plugin", level=0)
                            self.geojson_path = geojson_path
                            self.geojson_name = f"{layer_name} - Direct"
                            
                        except Exception as e:
                            QgsMessageLog.logMessage(f"Failed to create direct GeoJSON file: {str(e)}", "BNGAI Plugin", level=1)
                            self.geojson_path = None
                            self.geojson_name = None
                        
                        # Create line layer (using memory approach) as a fallback
                        line_layer = None
                        if line_count > 0:
                            line_layer = create_line_vector_layer(geojson_features, f"{layer_name} - Lines")
                        
                        # Skip KML approach as it requires additional libraries and can cause issues
                        self.kml_path = None
                        self.kml_name = None
                        
                        if line_layer and line_layer.isValid():
                            # Try to refresh canvas and zoom to layer
                            try:
                                from qgis.utils import iface
                                if iface and iface.mapCanvas():
                                    # Set the line layer as the active layer
                                    iface.setActiveLayer(line_layer)
                                    
                                    # Force the layer to repaint
                                    line_layer.triggerRepaint()
                                    
                                    # Make sure the layer is visible in legend
                                    root = QgsProject.instance().layerTreeRoot()
                                    layer_node = root.findLayer(line_layer.id())
                                    if layer_node:
                                        layer_node.setItemVisibilityChecked(True)
                                    
                                    # Explicitly zoom out a bit to see context
                                    if line_layer.featureCount() > 0:
                                        extent = line_layer.extent()
                                        # Expand the extent by 50% to provide context
                                        extent.grow(0.5)  
                                        iface.mapCanvas().setExtent(extent)
                                        QgsMessageLog.logMessage("Zoomed to line layer extent with context", "BNGAI Plugin", level=0)
                                    
                                    # Refresh canvas multiple times to ensure rendering
                                    iface.mapCanvas().refresh()
                                    iface.mapCanvas().refreshAllLayers()
                                    
                                    # Flash features to help user locate them
                                    if line_layer.featureCount() > 0:
                                        features = list(line_layer.getFeatures())
                                        if features and hasattr(iface.mapCanvas(), 'flashFeatureIds'):
                                            feature_ids = [f.id() for f in features]
                                            iface.mapCanvas().flashFeatureIds(line_layer, feature_ids)
                                            QgsMessageLog.logMessage("Flashed features to highlight them", "BNGAI Plugin", level=0)
                            except Exception as e:
                                # Just log and continue
                                QgsMessageLog.logMessage(f"Canvas refresh error: {str(e)}", "BNGAI Plugin", level=1)
                        else:
                            QgsMessageLog.logMessage("Failed to create line layer or no line features found", "BNGAI Plugin", level=1)
                    else:
                        QgsMessageLog.logMessage("No habitat features found in the BNG plan data", "BNGAI Plugin", level=1)
                else:
                    QgsMessageLog.logMessage(error, "BNGAI Plugin", level=2)
                
                QgsMessageLog.logMessage("Successfully fetched and parsed BNG Plan data", "BNGAI Plugin", level=0)
                self.setProgress(100)
                self.completed = True
                return True
            else:
                self.error = f"Failed to fetch data. Status code: {response.status_code}\nResponse: {response.text}"
                QgsMessageLog.logMessage(self.error, "BNGAI Plugin", level=2)
                self.setProgress(100)
                return False
                
        except requests.Timeout:
            self.error = "Request timed out after 30 seconds"
            QgsMessageLog.logMessage(self.error, "BNGAI Plugin", level=2)
            self.setProgress(100)
            return False
        except requests.ConnectionError:
            self.error = "Connection error occurred"
            QgsMessageLog.logMessage(self.error, "BNGAI Plugin", level=2)
            self.setProgress(100)
            return False
        except Exception as e:
            import traceback
            self.error = f"An error occurred: {str(e)}"
            QgsMessageLog.logMessage(self.error, "BNGAI Plugin", level=2)
            QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            self.setProgress(100)
            return False

    def finished(self, result):
        """Called when the task is finished"""
        if result:
            QgsMessageLog.logMessage("BNG Plan task completed successfully", "BNGAI Plugin", level=0)
            
            # Always print raw coordinates for diagnostic purposes
            if self.geojson_path and os.path.exists(self.geojson_path):
                self._log_raw_coordinates(self.geojson_path)
            
            # Try to load the direct GeoJSON 
            if self.geojson_path and os.path.exists(self.geojson_path):
                try:
                    from qgis.utils import iface
                    
                    # First try using a shapefile approach
                    shapefile_path = self._create_shapefile_from_geojson(self.geojson_path)
                    if shapefile_path:
                        QgsMessageLog.logMessage(f"Adding shapefile layer from {shapefile_path}", "BNGAI Plugin", level=0)
                        shapefile_layer = iface.addVectorLayer(shapefile_path, f"{self.geojson_name or 'BNG Features'} (Shapefile)", "ogr")
                        if shapefile_layer and shapefile_layer.isValid():
                            QgsMessageLog.logMessage("Successfully added shapefile layer", "BNGAI Plugin", level=0)
                            
                            # Set style for the layer to make features more visible
                            if shapefile_layer.geometryType() == QgsWkbTypes.LineGeometry:
                                self._set_line_style(shapefile_layer)
                            elif shapefile_layer.geometryType() == QgsWkbTypes.PointGeometry:
                                self._set_point_style(shapefile_layer)
                            elif shapefile_layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                                self._set_polygon_style(shapefile_layer)
                            
                            # Refresh and zoom to layer
                            if iface.mapCanvas():
                                shapefile_layer.triggerRepaint()
                                iface.mapCanvas().refreshAllLayers()
                                iface.setActiveLayer(shapefile_layer)
                                if shapefile_layer.featureCount() > 0:
                                    iface.zoomToActiveLayer()
                            
                            # Also create endpoint markers
                            self._create_endpoint_marker_layer(self.geojson_path)
                            return
                    
                    # If shapefile approach failed, try the GeoJSON approach
                    QgsMessageLog.logMessage(f"Adding GeoJSON layer from {self.geojson_path}", "BNGAI Plugin", level=0)
                    vector_layer = iface.addVectorLayer(self.geojson_path, f"{self.geojson_name or 'BNG Features'}", "ogr")
                    if vector_layer and vector_layer.isValid():
                        QgsMessageLog.logMessage("Successfully added GeoJSON layer directly", "BNGAI Plugin", level=0)
                        
                        # Set style for the layer to make features more visible
                        if vector_layer.geometryType() == QgsWkbTypes.LineGeometry:
                            self._set_line_style(vector_layer)
                        elif vector_layer.geometryType() == QgsWkbTypes.PointGeometry:
                            self._set_point_style(vector_layer)
                        elif vector_layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                            self._set_polygon_style(vector_layer)
                        
                        # Refresh and zoom to layer
                        if iface.mapCanvas():
                            vector_layer.triggerRepaint()
                            iface.mapCanvas().refreshAllLayers()
                            iface.setActiveLayer(vector_layer)
                            if vector_layer.featureCount() > 0:
                                iface.zoomToActiveLayer()
                        
                        # Now try to create a simple POINT helper layer to mark endpoints of lines
                        self._create_endpoint_marker_layer(self.geojson_path)
                    else:
                        QgsMessageLog.logMessage("Failed to add GeoJSON layer directly", "BNGAI Plugin", level=1)
                        # Try the fallback approach with endpoint markers
                        self._create_endpoint_marker_layer(self.geojson_path)
                except Exception as e:
                    QgsMessageLog.logMessage(f"Error adding layer: {str(e)}", "BNGAI Plugin", level=1)
                    # Try the fallback approach with endpoint markers
                    self._create_endpoint_marker_layer(self.geojson_path)
        else:
            QgsMessageLog.logMessage(f"BNG Plan task failed: {self.error}", "BNGAI Plugin", level=2)
    
    def _create_endpoint_marker_layer(self, geojson_path):
        """Create a special layer with large markers at line endpoints
        
        This is a fallback approach that should always work even if line rendering fails
        """
        try:
            import json
            from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsMarkerSymbol
            from qgis.utils import iface
            
            # Read the GeoJSON file
            with open(geojson_path, 'r') as f:
                geojson_data = json.load(f)
            
            if 'features' not in geojson_data:
                QgsMessageLog.logMessage("Invalid GeoJSON - no features found", "BNGAI Plugin", level=1)
                return
            
            # Try a direct approach by creating a manual line layer too
            self._create_direct_manual_line_layer(geojson_data)
                
            # Create a memory point layer
            point_layer = QgsVectorLayer("Point?crs=EPSG:4326", "Endpoints (Highly Visible)", "memory")
            
            if not point_layer.isValid():
                QgsMessageLog.logMessage("Failed to create endpoint marker layer", "BNGAI Plugin", level=1)
                return
                
            provider = point_layer.dataProvider()
            point_layer.startEditing()
            
            # Extract line endpoints
            found_points = 0
            for feature in geojson_data['features']:
                if feature.get('geometry', {}).get('type') == 'LineString':
                    coordinates = feature.get('geometry', {}).get('coordinates', [])
                    
                    if not coordinates or len(coordinates) < 2:
                        continue
                        
                    # Add start and end points (first and last coordinates)
                    for point_idx, point in enumerate([coordinates[0], coordinates[-1]]):
                        if len(point) >= 2:
                            qgs_feature = QgsFeature()
                            qgs_feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(point[0], point[1])))
                            provider.addFeatures([qgs_feature])
                            found_points += 1
                            
                            # Log the point coordinates
                            QgsMessageLog.logMessage(f"Added endpoint: {point[0]}, {point[1]}", "BNGAI Plugin", level=0)
            
            point_layer.commitChanges()
            
            if found_points == 0:
                QgsMessageLog.logMessage("No valid endpoints found in GeoJSON", "BNGAI Plugin", level=1)
                return
                
            # Set a very visible style for markers - LARGE red circles
            marker = QgsMarkerSymbol.createSimple({
                'name': 'circle',
                'color': 'red',
                'size': '10',  # Very large
                'outline_color': 'yellow',
                'outline_width': '1'
            })
            point_layer.renderer().setSymbol(marker)
            
            # Add layer to project
            QgsProject.instance().addMapLayer(point_layer)
            QgsMessageLog.logMessage(f"Added {found_points} marker points to highlight features", "BNGAI Plugin", level=0)
            
            # Zoom to this layer
            if found_points > 0 and iface and iface.mapCanvas():
                point_layer.triggerRepaint()
                iface.setActiveLayer(point_layer)
                iface.zoomToActiveLayer()
                
        except Exception as e:
            import traceback
            QgsMessageLog.logMessage(f"Error creating endpoint markers: {str(e)}", "BNGAI Plugin", level=2)
            QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
    
    def _create_direct_manual_line_layer(self, geojson_data):
        """Create a direct manual line layer with the simplest possible approach
        
        This should be the most reliable method with the least dependencies.
        """
        try:
            from qgis.core import QgsVectorLayer, QgsProject, QgsFeature, QgsGeometry, QgsPointXY, QgsLineSymbol, QgsSingleSymbolRenderer
            from qgis.PyQt.QtGui import QColor
            
            # Create a new memory layer
            layer = QgsVectorLayer("LineString?crs=EPSG:4326", "Direct Manual Lines", "memory")
            
            if not layer.isValid():
                QgsMessageLog.logMessage("Failed to create direct manual line layer", "BNGAI Plugin", level=1)
                return
                
            provider = layer.dataProvider()
            
            # Find all LineString features
            features_added = 0
            for feature in geojson_data['features']:
                if feature.get('geometry', {}).get('type') == 'LineString':
                    coordinates = feature.get('geometry', {}).get('coordinates', [])
                    
                    if not coordinates or len(coordinates) < 2:
                        QgsMessageLog.logMessage("Skipping line with insufficient points", "BNGAI Plugin", level=1)
                        continue
                    
                    # Create a line feature
                    qgs_feature = QgsFeature()
                    
                    # Create points from coordinates
                    points = []
                    for coord in coordinates:
                        if len(coord) >= 2:
                            x, y = coord[0], coord[1]
                            point = QgsPointXY(x, y)
                            points.append(point)
                    
                    if len(points) < 2:
                        QgsMessageLog.logMessage("Not enough valid points for line", "BNGAI Plugin", level=1)
                        continue
                        
                    # Create geometry and set it
                    line_geom = QgsGeometry.fromPolylineXY(points)
                    qgs_feature.setGeometry(line_geom)
                    
                    # Add the feature
                    provider.addFeature(qgs_feature)
                    features_added += 1
                    
                    QgsMessageLog.logMessage(f"Added manual line with {len(points)} points", "BNGAI Plugin", level=0)
            
            if features_added == 0:
                QgsMessageLog.logMessage("No lines added to manual layer", "BNGAI Plugin", level=1)
                return
                
            # Create a very visible style
            symbol = QgsLineSymbol.createSimple({
                'color': 'red',
                'width': '2.5',
                'line_style': 'solid',
                'capstyle': 'square'
            })
            renderer = QgsSingleSymbolRenderer(symbol)
            layer.setRenderer(renderer)
            
            # Add layer to project
            QgsProject.instance().addMapLayer(layer)
            
            # Force repaint
            layer.triggerRepaint()
            
            QgsMessageLog.logMessage(f"Successfully created direct manual line layer with {features_added} features", "BNGAI Plugin", level=0)
            
            return layer
                
        except Exception as e:
            import traceback
            QgsMessageLog.logMessage(f"Error creating direct manual line layer: {str(e)}", "BNGAI Plugin", level=2)
            QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            return None

    def _set_line_style(self, layer):
        """Set a high-visibility style for line layers"""
        try:
            from qgis.core import QgsSingleSymbolRenderer, QgsLineSymbol
            symbol = QgsLineSymbol.createSimple({
                'color': 'red',
                'width': '2',
                'line_style': 'solid'
            })
            renderer = QgsSingleSymbolRenderer(symbol)
            layer.setRenderer(renderer)
        except Exception as e:
            QgsMessageLog.logMessage(f"Error setting line style: {str(e)}", "BNGAI Plugin", level=1)
            
    def _set_point_style(self, layer):
        """Set a high-visibility style for point layers"""
        try:
            from qgis.core import QgsSingleSymbolRenderer, QgsMarkerSymbol
            symbol = QgsMarkerSymbol.createSimple({
                'name': 'circle',
                'color': 'blue',
                'size': '4',
                'outline_color': 'black',
                'outline_width': '0.5'
            })
            renderer = QgsSingleSymbolRenderer(symbol)
            layer.setRenderer(renderer)
        except Exception as e:
            QgsMessageLog.logMessage(f"Error setting point style: {str(e)}", "BNGAI Plugin", level=1)
            
    def _set_polygon_style(self, layer):
        """Set a high-visibility style for polygon layers"""
        try:
            from qgis.core import QgsSingleSymbolRenderer, QgsFillSymbol
            symbol = QgsFillSymbol.createSimple({
                'color': 'rgba(255,0,0,50)',
                'outline_color': 'red',
                'outline_width': '1'
            })
            renderer = QgsSingleSymbolRenderer(symbol)
            layer.setRenderer(renderer)
        except Exception as e:
            QgsMessageLog.logMessage(f"Error setting polygon style: {str(e)}", "BNGAI Plugin", level=1)

    def _log_raw_coordinates(self, geojson_path):
        """Output raw coordinates to log for diagnostic purposes"""
        try:
            import json
            
            # Read the GeoJSON file
            with open(geojson_path, 'r') as f:
                geojson_data = json.load(f)
            
            if 'features' not in geojson_data:
                QgsMessageLog.logMessage("Invalid GeoJSON - no features found", "BNGAI Plugin", level=1)
                return
                
            QgsMessageLog.logMessage("=== RAW FEATURE COORDINATES FOR MANUAL ENTRY ===", "BNGAI Plugin", level=0)
            
            feature_count = len(geojson_data['features'])
            QgsMessageLog.logMessage(f"Total features: {feature_count}", "BNGAI Plugin", level=0)
            
            line_count = 0
            point_count = 0
            polygon_count = 0
            
            for i, feature in enumerate(geojson_data['features']):
                geom_type = feature.get('geometry', {}).get('type')
                coords = feature.get('geometry', {}).get('coordinates', [])
                
                if geom_type == 'LineString':
                    line_count += 1
                    QgsMessageLog.logMessage(f"LINE {line_count} - {len(coords)} points:", "BNGAI Plugin", level=0)
                    for j, point in enumerate(coords):
                        if len(point) >= 2:
                            QgsMessageLog.logMessage(f"  Point {j+1}: X={point[0]}, Y={point[1]}", "BNGAI Plugin", level=0)
                
                elif geom_type == 'Point':
                    point_count += 1
                    if len(coords) >= 2:
                        QgsMessageLog.logMessage(f"POINT {point_count}: X={coords[0]}, Y={coords[1]}", "BNGAI Plugin", level=0)
                
                elif geom_type == 'Polygon':
                    polygon_count += 1
                    if coords and len(coords) > 0:
                        outer_ring = coords[0]
                        QgsMessageLog.logMessage(f"POLYGON {polygon_count} - {len(outer_ring)} vertices:", "BNGAI Plugin", level=0)
                        for j, point in enumerate(outer_ring):
                            if len(point) >= 2:
                                QgsMessageLog.logMessage(f"  Vertex {j+1}: X={point[0]}, Y={point[1]}", "BNGAI Plugin", level=0)
            
            QgsMessageLog.logMessage(f"Summary: {line_count} lines, {point_count} points, {polygon_count} polygons", "BNGAI Plugin", level=0)
            QgsMessageLog.logMessage("=== END OF RAW COORDINATES ===", "BNGAI Plugin", level=0)
            
        except Exception as e:
            import traceback
            QgsMessageLog.logMessage(f"Error logging coordinates: {str(e)}", "BNGAI Plugin", level=2)
            QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)

    def _create_shapefile_from_geojson(self, geojson_path):
        """Create a shapefile from GeoJSON for better QGIS compatibility
        
        Returns the path to the shapefile if successful, None otherwise
        """
        try:
            import tempfile
            import os
            import json
            
            # First check if fiona is available (it should be with QGIS)
            try:
                import fiona
                from fiona.crs import from_epsg
            except ImportError:
                QgsMessageLog.logMessage("Fiona not available, skipping shapefile creation", "BNGAI Plugin", level=1)
                return None
                
            # Read the GeoJSON file
            with open(geojson_path, 'r') as f:
                geojson_data = json.load(f)
                
            if 'features' not in geojson_data or not geojson_data['features']:
                QgsMessageLog.logMessage("No features in GeoJSON", "BNGAI Plugin", level=1)
                return None
                
            # Get first feature to determine schema
            features = geojson_data['features']
            
            # Group features by geometry type
            point_features = []
            line_features = []
            polygon_features = []
            
            for feature in features:
                geom_type = feature.get('geometry', {}).get('type')
                if geom_type == 'Point':
                    point_features.append(feature)
                elif geom_type == 'LineString':
                    line_features.append(feature)
                elif geom_type == 'Polygon':
                    polygon_features.append(feature)
            
            # Process each geometry type separately
            for geom_type, feature_list, type_name in [
                ('Point', point_features, 'points'),
                ('LineString', line_features, 'lines'),
                ('Polygon', polygon_features, 'polygons')
            ]:
                if not feature_list:
                    continue
                    
                # Create temp directory for shapefile
                temp_dir = tempfile.mkdtemp()
                shapefile_path = os.path.join(temp_dir, f"bng_{type_name}.shp")
                
                # Create schema from first feature
                first_feature = feature_list[0]
                properties = first_feature.get('properties', {})
                
                schema = {
                    'geometry': geom_type,
                    'properties': {k: 'str' for k in properties.keys()}
                }
                
                # Create the shapefile
                with fiona.open(
                    shapefile_path, 'w',
                    driver='ESRI Shapefile',
                    crs=from_epsg(4326),
                    schema=schema
                ) as shp:
                    # Write features to shapefile
                    for feature in feature_list:
                        shp.write(feature)
                
                QgsMessageLog.logMessage(f"Created shapefile at {shapefile_path} with {len(feature_list)} features", "BNGAI Plugin", level=0)
                return shapefile_path
                
            # If no shapefiles were created
            return None
                
        except Exception as e:
            import traceback
            QgsMessageLog.logMessage(f"Error creating shapefile: {str(e)}", "BNGAI Plugin", level=2)
            QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            return None

def export_features_to_kml(features, name_prefix="BNG_Features"):
    """Export features to KML format for debugging
    
    This function creates a KML file from GeoJSON features, which can be opened
    in Google Earth or any GIS software. It's particularly useful for debugging
    issues with QGIS rendering.
    
    :param features: List of GeoJSON feature dictionaries
    :type features: list
    :param name_prefix: Prefix for the output file name
    :type name_prefix: str
    
    :returns: Tuple of (success, file_path)
    :rtype: tuple
    """
    try:
        import os
        import tempfile
        
        # Validate input
        if not features or not isinstance(features, list):
            QgsMessageLog.logMessage("No features provided or invalid format", "BNGAI Plugin", level=1)
            return False, None
        
        # Try importing simplekml
        try:
            import simplekml
        except ImportError:
            # simplekml not available, just log and return
            QgsMessageLog.logMessage("simplekml package not available, skipping KML export", "BNGAI Plugin", level=1)
            QgsMessageLog.logMessage("You can manually install it using: pip install simplekml", "BNGAI Plugin", level=1)
            return False, None
            
        # Count how many features of each type we have
        line_features = []
        polygon_features = []
        point_features = []
        
        for f in features:
            if not isinstance(f, dict) or 'geometry' not in f:
                continue
                
            geom = f.get('geometry', {})
            if not isinstance(geom, dict) or 'type' not in geom or 'coordinates' not in geom:
                continue
                
            geom_type = geom.get('type')
            coords = geom.get('coordinates')
            
            if not coords:
                continue
                
            if geom_type == 'LineString':
                line_features.append(f)
            elif geom_type == 'Polygon':
                polygon_features.append(f)
            elif geom_type == 'Point':
                point_features.append(f)
        
        QgsMessageLog.logMessage(f"Exporting features to KML: {len(line_features)} lines, {len(polygon_features)} polygons, {len(point_features)} points", 
                                "BNGAI Plugin", level=0)
        
        if not line_features and not polygon_features and not point_features:
            QgsMessageLog.logMessage("No valid features found for KML export", "BNGAI Plugin", level=1)
            return False, None
        
        # Create a unique base filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{name_prefix}_{timestamp}"
        temp_dir = tempfile.gettempdir()
        
        # Create KML file
        kml_path = os.path.join(temp_dir, f"{base_name}.kml")
        kml = simplekml.Kml()
        
        # Add each feature to KML
        feature_count = 0
        
        # Process line features
        for i, feature in enumerate(line_features):
            try:
                coords = feature.get('geometry', {}).get('coordinates', [])
                if not coords or not isinstance(coords, list):
                    continue
                
                # Add a line
                line = kml.newlinestring(name=f"Line {i+1}")
                
                # Add coordinates
                kml_coords = []
                for point in coords:
                    if not point or len(point) < 2:
                        continue
                    # KML uses long, lat order
                    kml_coords.append((point[0], point[1]))
                
                if len(kml_coords) < 2:
                    continue
                    
                line.coords = kml_coords
                
                # Set style
                line.style.linestyle.color = simplekml.Color.red
                line.style.linestyle.width = 5
                
                # Add point placemarks at vertices
                for j, point in enumerate(coords):
                    if not point or len(point) < 2:
                        continue
                    pt = kml.newpoint(name=f"Line {i+1} Vertex {j+1}")
                    pt.coords = [(point[0], point[1])]
                    pt.style.iconstyle.color = simplekml.Color.blue
                    pt.style.iconstyle.scale = 1.0
                
                feature_count += 1
            except Exception as e:
                QgsMessageLog.logMessage(f"Error processing line feature {i+1}: {str(e)}", "BNGAI Plugin", level=1)
                continue
        
        # Process polygon features
        for i, feature in enumerate(polygon_features):
            try:
                coords = feature.get('geometry', {}).get('coordinates', [])
                if not coords:
                    continue
                    
                # Add a polygon
                poly = kml.newpolygon(name=f"Polygon {i+1}")
                
                # For polygons, coordinates can be nested (outer ring + holes)
                outer_ring = coords[0] if isinstance(coords[0][0], list) else coords
                
                # Add coordinates
                kml_coords = []
                for point in outer_ring:
                    if not point or len(point) < 2:
                        continue
                    kml_coords.append((point[0], point[1]))
                
                if len(kml_coords) < 3:
                    continue
                    
                poly.outerboundaryis = kml_coords
                
                # Set style
                poly.style.linestyle.color = simplekml.Color.yellow
                poly.style.linestyle.width = 3
                poly.style.polystyle.color = simplekml.Color.changealphaint(100, simplekml.Color.green)
                
                feature_count += 1
            except Exception as e:
                QgsMessageLog.logMessage(f"Error processing polygon feature {i+1}: {str(e)}", "BNGAI Plugin", level=1)
                continue
        
        # Process point features
        for i, feature in enumerate(point_features):
            try:
                coords = feature.get('geometry', {}).get('coordinates', [])
                if not coords or len(coords) < 2:
                    continue
                
                pt = kml.newpoint(name=f"Point {i+1}")
                pt.coords = [(coords[0], coords[1])]
                pt.style.iconstyle.color = simplekml.Color.yellow
                pt.style.iconstyle.scale = 1.2
                
                feature_count += 1
            except Exception as e:
                QgsMessageLog.logMessage(f"Error processing point feature {i+1}: {str(e)}", "BNGAI Plugin", level=1)
                continue
        
        # Save KML
        kml.save(kml_path)
        QgsMessageLog.logMessage(f"Saved KML file with {feature_count} features to: {kml_path}", "BNGAI Plugin", level=0)
        
        return True, kml_path
    
    except Exception as e:
        import traceback
        QgsMessageLog.logMessage(f"Error exporting features to KML: {str(e)}", "BNGAI Plugin", level=2)
        QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
        return False, None