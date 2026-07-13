"""
API client for the projects tab.
"""
import requests
import json
from qgis.core import QgsMessageLog
from ...utils.api_config import ApiConfig

class ProjectsApiClient:
    """Handles all API interactions for the projects tab."""
    
    def __init__(self, auth_manager):
        """Initialize the API client."""
        self.auth_manager = auth_manager
        self.api_url = ApiConfig.get_api_base_url()
        self.legacy_backend_url = ApiConfig.get_legacy_backend_url()
    
    def _get_graphql_url(self):
        """Get the GraphQL API URL"""
        return ApiConfig.get_graphql_url()
        
    def _get_habitat_api_url(self):
        """Get Habitat API URL from API config"""
        return ApiConfig.get_habitat_api_url()
    
    def _get_legacy_backend_url(self):
        """Get Legacy Backend URL from API config"""
        return self.legacy_backend_url

    def _get_api_headers(self, token, org_id):
        """Get API headers"""
        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "authorization": token,
            "content-type": "application/json",
            "organization-id": org_id,
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site"
        }
        return headers

    def get_retained_layers(self, plan_id):
        """
        Fetch retained habitats (retained layers) for a given plan from legacy backend.
        Endpoint: GET {legacy_backend}/api/v1/plan/retainedHabitats?planId=<plan_id>
        
        Args:
            plan_id (str): BNG Plan ID
        
        Returns:
            list | None: List of retained habitat objects or None if failed
        """
        if not self.auth_manager or not self.auth_manager.is_logged_in():
            QgsMessageLog.logMessage("Cannot fetch retained layers: Not logged in", "BNGAI Plugin", level=2)
            return None
        try:
            token = self.auth_manager.get_token()
            if not token:
                QgsMessageLog.logMessage("Cannot fetch retained layers: No token", "BNGAI Plugin", level=2)
                return None
            # Build URL and headers
            base_url = getattr(self, "legacy_backend_url", ApiConfig.get_legacy_backend_url())
            url = f"{base_url}/api/v1/plan/retainedHabitats"
            # No Organization-Id header needed for this endpoint
            headers = {
                "accept": "application/json",
                "authorization": token,
                "origin": ApiConfig.get_header_origin(),
                "referer": ApiConfig.get_header_referer(),
            }
            params = {"planId": plan_id}
            resp = requests.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                QgsMessageLog.logMessage(f"Retained layers request failed: {resp.status_code} {resp.text}", "BNGAI Plugin", level=2)
                return None
            try:
                data = resp.json()
            except Exception:
                QgsMessageLog.logMessage("Failed to parse JSON from retained layers response", "BNGAI Plugin", level=2)
                return None
            if isinstance(data, list):
                QgsMessageLog.logMessage(f"Fetched retained layers: count={len(data)}", "BNGAI Plugin", level=0)
                return data
            QgsMessageLog.logMessage(f"Unexpected retained layers response format: {data}", "BNGAI Plugin", level=1)
            return None
        except Exception as e:
            QgsMessageLog.logMessage(f"Error fetching retained layers: {str(e)}", "BNGAI Plugin", level=2)
            try:
                import traceback
                QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            except Exception:
                pass
            return None
    
    def get_retained_habitats(self, plan_id, org_id=None):
        """
        Compatibility wrapper: retained habitats are fetched from legacy backend.
        Delegates to get_retained_layers(plan_id).
        """
        try:
            return self.get_retained_layers(plan_id)
        except Exception as e:
            QgsMessageLog.logMessage(f"Error in get_retained_habitats: {str(e)}", "BNGAI Plugin", level=2)
            return None

    def _get_api_headers_without_org(self, token):
        """Get API headers without Organization-Id"""
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Authorization": token,
            "Content-Type": "application/json",
            "Origin": ApiConfig.get_header_origin(),
            "Referer": ApiConfig.get_header_referer()
        }
        return headers

    def get_organizations(self):
        """Fetch organizations from the API."""
        if not self.auth_manager.is_logged_in():
            QgsMessageLog.logMessage("Cannot fetch organizations: Not logged in", "BNGAI Plugin", level=2)
            return []

        try:
            token = self.auth_manager.get_token()
            if not token:
                return []

            # Get organizations from auth manager
            organizations = self.auth_manager.get_organizations()
            return organizations if organizations is not None else []
        except Exception as e:
            QgsMessageLog.logMessage(f"Error fetching organizations: {str(e)}", "BNGAI Plugin", level=2)
            return []

    # GraphQL for assigned-projects table (requires viewMode and full input shape)
    _GET_ASSIGNED_PROJECTS_QUERY = """
    query (
      $applicationComponent: ApplicationComponent!,
      $paginationInput: PaginationInput,
      $sortInput: SortInput,
      $habitatMetricTableFilters: HabitatMetricTableFilters,
      $siteManagementTableFilters: SiteManagementTableFilters,
      $bngProjectOverviewTableFilters: BNGProjectOverviewTableFilters,
      $bngReportTableFilters: BngReportTableFilters,
      $bngDevelopmentPlanTableFilters: BNGDevelopmentPlanTableFilters,
      $bngPlanTableFilters: BNGPlanTableFilters,
      $bngApprovedDevelopmentPlanTableFilters: BNGApprovedDevelopmentPlanTableFilters,
      $bngPlanAttachmentsTableFilters: BNGPlanAttachmentsTableFilters,
      $appliedFilters: AppliedFilters,
      $viewMode: ViewMode,
      $projectGroupFilter: ProjectGroupFilter
    ) {
      getTableData(
        input: {
          applicationComponent: $applicationComponent,
          paginationInput: $paginationInput,
          sortInput: $sortInput,
          habitatMetricTableFilters: $habitatMetricTableFilters,
          siteManagementTableFilters: $siteManagementTableFilters,
          bngProjectOverviewTableFilters: $bngProjectOverviewTableFilters,
          bngReportTableFilters: $bngReportTableFilters,
          bngDevelopmentPlanTableFilters: $bngDevelopmentPlanTableFilters,
          bngPlanTableFilters: $bngPlanTableFilters,
          bngApprovedDevelopmentPlanTableFilters: $bngApprovedDevelopmentPlanTableFilters,
          bngPlanAttachmentsTableFilters: $bngPlanAttachmentsTableFilters,
          appliedFilters: $appliedFilters,
          viewMode: $viewMode,
          projectGroupFilter: $projectGroupFilter
        }
      ) {
        rows
        totalCount
        __typename
      }
    }
    """

    def get_projects(self, org_id, category="my"):
        """Fetch projects from the API.

        Args:
            org_id: Organization UUID.
            category: "my" for the user's BNG projects listing (default).
                "assigned" for projects from the assigned-projects table API.
        """
        if not self.auth_manager.is_logged_in():
            QgsMessageLog.logMessage("Cannot fetch projects: Not logged in", "BNGAI Plugin", level=2)
            return None

        try:
            token = self.auth_manager.get_token()
            if not token:
                return None

            url = self._get_graphql_url()
            headers = self._get_api_headers(token, org_id)

            if category == "assigned":
                query = self._GET_ASSIGNED_PROJECTS_QUERY
                variables = {
                    "applicationComponent": "BNG_ASSIGNED_PROJECTS_LISTING_TABLE",
                    "paginationInput": {
                        "limit": 100,
                        "offset": 0,
                    },
                    "viewMode": "ALL",
                }
            else:
                query = """
                query ($applicationComponent: ApplicationComponent!, $paginationInput: PaginationInput, $appliedFilters: AppliedFilters) {
                  getTableData(
                    input: {applicationComponent: $applicationComponent, paginationInput: $paginationInput, appliedFilters: $appliedFilters}
                  ) {
                    rows
                    totalCount
                    __typename
                  }
                }
                """
                variables = {
                    "applicationComponent": "BNG_PROJECTS_LISTING_TABLE",
                    "paginationInput": {
                        "limit": 100,
                        "offset": 0
                    },
                    "appliedFilters": {
                        "filters": [
                            {
                                "key": "projectLifecycleStatus",
                                "values": ["Project in Progress", "Submission Ready"],
                                "type": "MULTI_SELECT_SERVER"
                            },
                        ]
                    }
                }

            payload = {
                "query": query,
                "variables": variables
            }
            QgsMessageLog.logMessage(f"Payload: {payload}", "BNGAI Plugin", level=0)

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                data = response.json()
                if data.get("errors"):
                    QgsMessageLog.logMessage(
                        f"GraphQL errors fetching projects: {data['errors']}",
                        "BNGAI Plugin",
                        level=2,
                    )
                if "data" in data and data["data"] and "getTableData" in data["data"]:
                    return data["data"]["getTableData"]
            else:
                QgsMessageLog.logMessage(
                    f"Projects request failed: {response.status_code} {response.text[:500]}",
                    "BNGAI Plugin",
                    level=2,
                )

            return None
        except Exception as e:
            QgsMessageLog.logMessage(f"Error fetching projects: {str(e)}", "BNGAI Plugin", level=2)
            return None

    def get_project_details(self, project_id, org_id):
        """Fetch project details from the API."""
        if not self.auth_manager.is_logged_in():
            return None

        try:
            token = self.auth_manager.get_token()
            if not token:
                return None

            url = self._get_graphql_url()
            headers = self._get_api_headers(token, org_id)

            query = """
            query getProjectDetail($id: UUID!) {
              projectDetail(input: {id: $id}) {
                name
                siteId
                siteRevisionId
                createdBy
                siteTypeCode
                currentUserAccess
                status
                projectType
                isDemo
                allowedClassificationSelection
                bngaiCashUsageStatus
                __typename
              }
            }
            """

            variables = {
                "id": project_id
            }

            payload = {
                "query": query,
                "variables": variables
            }

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                data = response.json()
                if "data" in data and "projectDetail" in data["data"]:
                    return data["data"]["projectDetail"]

            return None
        except Exception as e:
            QgsMessageLog.logMessage(f"Error fetching project details: {str(e)}", "BNGAI Plugin", level=2)
            return None

    def get_bng_plans(self, site_id, org_id):
        """Fetch BNG plans from the API."""
        if not self.auth_manager.is_logged_in():
            QgsMessageLog.logMessage("Cannot fetch BNG plans: Not logged in", "BNGAI Plugin", level=2)
            return None

        try:
            token = self.auth_manager.get_token()
            if not token:
                QgsMessageLog.logMessage("Cannot fetch BNG plans: No token available", "BNGAI Plugin", level=2)
                return None

            url = f"{self._get_legacy_backend_url()}/api/v1/plan/table/{site_id}"
            headers = self._get_api_headers(token, org_id)
            headers["Accept"] = "application/json"
            headers["Content-Type"] = "application/json"
            QgsMessageLog.logMessage(f"URL: {url}", "BNGAI Plugin", level=0)
            QgsMessageLog.logMessage(f"Fetching BNG plans via REST for site: {site_id}", "BNGAI Plugin", level=0)
            response = requests.get(url, headers=headers)
            QgsMessageLog.logMessage(f"Response status code: {response.status_code}", "BNGAI Plugin", level=0)

            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception:
                    QgsMessageLog.logMessage("Failed to parse JSON from BNG plans response", "BNGAI Plugin", level=2)
                    return None

                plans = self._extract_bng_plan_items(data)
                QgsMessageLog.logMessage(f"Successfully fetched BNG plans. Count: {len(plans)}", "BNGAI Plugin", level=0)
                return {
                    "rows": plans,
                    "totalCount": len(plans)
                }

            QgsMessageLog.logMessage(f"Failed to fetch BNG plans. Status code: {response.status_code}", "BNGAI Plugin", level=2)
            QgsMessageLog.logMessage(f"Response text: {response.text}", "BNGAI Plugin", level=2)
            return None
        except Exception as e:
            QgsMessageLog.logMessage(f"Error fetching BNG plans: {str(e)}", "BNGAI Plugin", level=2)
            import traceback
            QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            return None

    def get_habitat_geometry(self, site_revision_id, org_id):
        """Fetch habitat geometry from the API."""
        if not self.auth_manager.is_logged_in():
            return None

        try:
            token = self.auth_manager.get_token()
            if not token:
                return None

            url = self._get_graphql_url()
            headers = self._get_api_headers(token, org_id)

            query = """
            query ($siteRevisionId: UUID!, $applicationComponent: ApplicationComponent!) {
              getHabitatGeometry(
                input: {siteRevisionId: $siteRevisionId, applicationComponent: $applicationComponent}
              ) {
                site {
                    boundaryGeometry
                    centroidGeometry
                    __typename
                }
                habitats {
                  id
                  habitatReferenceID
                  shapeAttributes {
                    area
                    length
                    centroid
                    }
                    biodiversityAttributes {
                        condition
                        treeSize
                        isIrreplaceableHabitat
                        distinctiveness
                        strategy
                    }
                    habitatClassification {
                        aiDash {
                        code
                        label
                        }
                        custom {
                        code
                        label
                        group
                        shapeType
                        }
                    }
                  geometry
                }
              }
            }
            """

            variables = {
                "siteRevisionId": site_revision_id,
                "applicationComponent": "BNG_PROJECT_OVERVIEW_MAP"
            }

            payload = {
                "query": query,
                "variables": variables
            }

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                data = response.json()
                if "data" in data and "getHabitatGeometry" in data["data"]:
                    return data["data"]["getHabitatGeometry"]

            return None
        except Exception as e:
            QgsMessageLog.logMessage(f"Error fetching habitat geometry: {str(e)}", "BNGAI Plugin", level=2)
            return None

    def get_site_boundary(self, site_revision_id, org_id):
        """
        Fetch site boundary (Red Line Boundary) from the API.
        
        Args:
            site_revision_id (str): Site revision ID
            org_id (str): Organization ID
            
        Returns:
            dict: GeoJSON geometry of the site boundary or None if failed
        """
        if not self.auth_manager.is_logged_in():
            return None

        try:
            token = self.auth_manager.get_token()
            if not token:
                return None

            url = self._get_graphql_url()
            headers = self._get_api_headers(token, org_id)

            query = """
            query ($siteRevisionId: UUID!, $applicationComponent: ApplicationComponent!) {
              getHabitatGeometry(
                input: {siteRevisionId: $siteRevisionId, applicationComponent: $applicationComponent}
              ) {
                site {
                  boundaryGeometry
                }
              }
            }
            """

            variables = {
                "siteRevisionId": site_revision_id,
                "applicationComponent": "BNG_PROJECT_OVERVIEW_MAP"
            }

            payload = {
                "query": query,
                "variables": variables
            }

            QgsMessageLog.logMessage(f"Fetching site boundary for siteRevisionId: {site_revision_id}", "BNGAI Plugin", level=0)
            response = requests.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                data = response.json()
                if "data" in data and "getHabitatGeometry" in data["data"]:
                    habitat_geometry = data["data"]["getHabitatGeometry"]
                    if habitat_geometry and "site" in habitat_geometry:
                        boundary_geometry = habitat_geometry["site"].get("boundaryGeometry")
                        if boundary_geometry:
                            QgsMessageLog.logMessage("Successfully fetched site boundary geometry", "BNGAI Plugin", level=0)
                            return boundary_geometry
                        
            QgsMessageLog.logMessage(f"Failed to fetch site boundary. Status: {response.status_code}", "BNGAI Plugin", level=1)
            return None
        except Exception as e:
            QgsMessageLog.logMessage(f"Error fetching site boundary: {str(e)}", "BNGAI Plugin", level=2)
            return None

    def update_habitat(self, formatted_feature, old_ids, org_id):
        """Update habitat via the API."""
        if not self.auth_manager.is_logged_in():
            return False

        try:
            token = self.auth_manager.get_token()
            if not token:
                return False

            url = self._get_habitat_api_url()
            headers = self._get_api_headers_without_org(token)

            payload = {
                "oldIds": old_ids or [],
                "newHabitats": [formatted_feature],
            }
            QgsMessageLog.logMessage(f"Sending update request to {url} with payload: {json.dumps(payload)}", "BNGAI Plugin", level=0)
            response = requests.post(url, headers=headers, json=payload)
            QgsMessageLog.logMessage(f"Update request response status: {response}", "BNGAI Plugin", level=0)

            return response.status_code in [200, 201, 204]
        except Exception as e:
            QgsMessageLog.logMessage(f"Error updating habitat: {str(e)}", "BNGAI Plugin", level=2)
            import traceback
            QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            return False

    def delete_habitat(self, habitat_id, org_id):
        """Delete habitat via the API."""
        if not self.auth_manager.is_logged_in():
            QgsMessageLog.logMessage("Cannot delete habitat: Not logged in", "BNGAI Plugin", level=2)
            return False

        try:
            token = self.auth_manager.get_token()
            if not token:
                QgsMessageLog.logMessage("Cannot delete habitat: No token available", "BNGAI Plugin", level=2)
                return False

            url = self._get_habitat_api_url()
            headers = self._get_api_headers_without_org(token)

            payload = {
                "oldIds": [habitat_id],
                "newHabitats": [],
            }

            QgsMessageLog.logMessage(f"Sending delete request to {url} with payload: {json.dumps(payload)}", "BNGAI Plugin", level=0)
            
            response = requests.post(url, headers=headers, json=payload)
            
            QgsMessageLog.logMessage(f"Delete request response status: {response.status_code}", "BNGAI Plugin", level=0)
            if response.status_code not in [200, 201, 204]:
                QgsMessageLog.logMessage(f"Delete request failed with response: {response.text}", "BNGAI Plugin", level=2)

            return response.status_code in [200, 201, 204]
        except Exception as e:
            QgsMessageLog.logMessage(f"Error deleting habitat: {str(e)}", "BNGAI Plugin", level=2)
            import traceback
            QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            return False

    def get_ground_survey_details(self, ids):
        """Get ground survey details for a list of IDs."""
        try:
            token = self.auth_manager.get_token()
            if not token:
                return None

            url = f"{self._get_legacy_backend_url()}/habitat/groundSurvey/details"
            headers = self._get_api_headers_without_org(token)

            response = requests.post(url, headers=headers, json={"ids": ids})
            QgsMessageLog.logMessage(f"Ground survey details response: {response.json()}", "BNGAI Plugin", level=0)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            QgsMessageLog.logMessage(f"Error getting ground survey details: {str(e)}", "BNGAI Plugin", level=2)
            return None

    def get_condition_assessment_details(self, ids):
        """Get condition assessment details for a list of IDs."""
        try:
            token = self.auth_manager.get_token()
            if not token:
                return None

            url = f"{self._get_legacy_backend_url()}/habitat/conditionAssessment/details"
            headers = self._get_api_headers_without_org(token)

            response = requests.post(url, headers=headers, json={"ids": ids})

            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            QgsMessageLog.logMessage(f"Error getting condition assessment details: {str(e)}", "BNGAI Plugin", level=2)
            return None

    def get_encroachment_assessment_details(self, ids):
        """Get encroachment assessment details for a list of IDs."""
        try:
            token = self.auth_manager.get_token()
            if not token:
                return None

            url = f"{self._get_legacy_backend_url()}/habitat/encroachmentAssessment/details"
            headers = self._get_api_headers_without_org(token)

            response = requests.post(url, headers=headers, json={"ids": ids})

            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            QgsMessageLog.logMessage(f"Error getting encroachment assessment details: {str(e)}", "BNGAI Plugin", level=2)
            return None

    def get_justification_details(self, ids):
        """Get justification details for a list of IDs."""
        try:
            token = self.auth_manager.get_token()
            if not token:
                return None

            url = f"{self._get_legacy_backend_url()}/habitat/justification/details"
            headers = self._get_api_headers_without_org(token)

            response = requests.post(url, headers=headers, json={"ids": ids})

            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            QgsMessageLog.logMessage(f"Error getting justification details: {str(e)}", "BNGAI Plugin", level=2)
            return None

    def get_tree_size_assessment_details(self, ids, org_id):
        """Get tree size assessment details for a list of IDs."""
        try:
            token = self.auth_manager.get_token()
            if not token:
                return None

            url = f"{self._get_legacy_backend_url()}/habitat/tree-size-assessment/details"
            headers = self._get_api_headers(token, org_id)

            response = requests.post(url, headers=headers, json={"ids": ids})

            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            QgsMessageLog.logMessage(f"Error getting tree size assessment details: {str(e)}", "BNGAI Plugin", level=2)
            return None

    def _extract_bng_plan_items(self, payload):
        """
        Flatten the REST response into a list of plan entries.
        Each item captures planId and title from template[i].props.items.list[j].
        """
        plans = []
        try:
            templates = payload.get("template", [])
            if isinstance(templates, list):
                for template in templates:
                    props = template.get("props", {})
                    items = props.get("items", {})
                    plan_list = items.get("list", [])
                    if not isinstance(plan_list, list):
                        continue
                    for item in plan_list:
                        plan_id = item.get("planId")
                        title = item.get("title", "")
                        if plan_id:
                            plans.append({
                                "planId": plan_id,
                                "title": title,
                                "raw": item
                            })
        except Exception as e:
            QgsMessageLog.logMessage(f"Error parsing BNG plans response: {str(e)}", "BNGAI Plugin", level=2)
        return plans

    def fetch_features(self, plan_id=None, org_id=None, site_revision_id=None, geometry_type=None, layer_type=None):
        """
        Fetch plan features (plan/base/retained) via WFS endpoint.
        Args:
            plan_id (str|None): Plan ID (optional for base layer)
            org_id (str): Organization ID
            site_revision_id (str|None): Optional site revision ID
            geometry_type (str|None): Optional geometry type filter
            layer_type (str|None): One of plan, retained, base (optional)
        Returns:
            dict | None: GeoJSON FeatureCollection or None on failure
        """
        if not self.auth_manager.is_logged_in():
            QgsMessageLog.logMessage("Cannot fetch plan features: Not logged in", "BNGAI Plugin", level=2)
            return None

        try:
            token = self.auth_manager.get_token()
            if not token:
                return None

            legacy_backend_url = self._get_legacy_backend_url()
            url = f"{legacy_backend_url}/api/v1/wfs/features"
            headers = self._get_api_headers(token, org_id)

            params = {}
            if plan_id:
                params["planId"] = plan_id
            if site_revision_id:
                params["siteRevisionId"] = site_revision_id
            if geometry_type:
                params["geometryType"] = geometry_type
            if layer_type:
                params["layerType"] = layer_type

            QgsMessageLog.logMessage(f"Fetching plan features: site_revision_id={site_revision_id}, planId={plan_id}, layerType={layer_type}, geometryType={geometry_type}", "BNGAI Plugin", level=0)
            QgsMessageLog.logMessage(f"URL: {url}", "BNGAI Plugin", level=0)
            QgsMessageLog.logMessage(f"Headers: {headers}", "BNGAI Plugin", level=0)
            QgsMessageLog.logMessage(f"Params: {params}", "BNGAI Plugin", level=0)
            response = requests.get(url, headers=headers, params=params)

            if response.status_code != 200:
                QgsMessageLog.logMessage(
                    f"Failed to fetch plan features. Status code: {response.status_code}, body: {response.text}",
                    "BNGAI Plugin",
                    level=2,
                )
                return None

            data = response.json()
            if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
                QgsMessageLog.logMessage(f"Invalid FeatureCollection response: {data}", "BNGAI Plugin", level=2)
                return None

            features_count = len(data.get("features", []))
            QgsMessageLog.logMessage(f"Fetched {features_count} features from WFS endpoint", "BNGAI Plugin", level=0)
            return data
        except Exception as e:
            QgsMessageLog.logMessage(f"Error fetching plan features: {str(e)}", "BNGAI Plugin", level=2)
            import traceback
            QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            return None

    def get_bng_plan_habitats(self, bng_plan_id, org_id, site_revision_id=None, geometry_type=None):
        """
        Fetch retained BNG plan habitats using the reusable WFS plan features endpoint.
        """
        return self.fetch_features(
            plan_id=bng_plan_id,
            org_id=org_id,
            site_revision_id=site_revision_id,
            geometry_type=geometry_type,
            layer_type="plan",
        )

    def get_retained_features(self, plan_id, org_id, site_revision_id=None, geometry_type=None):
        """
        Fetch retained habitat features using the WFS endpoint.
        """
        return self.fetch_features(
            plan_id=plan_id,
            org_id=org_id,
            site_revision_id=site_revision_id,
            geometry_type=geometry_type,
            layer_type="retained",
        )

    def get_base_features(self, plan_id=None, org_id=None, site_revision_id=None, geometry_type=None):
        """
        Fetch base habitat features using the WFS endpoint.
        plan_id is optional for base layer.
        """
        return self.fetch_features(
            plan_id=plan_id,
            org_id=org_id,
            site_revision_id=site_revision_id,
            geometry_type=geometry_type,
            layer_type="base",
        )

    def wfs_transaction(self, plan_id, org_id, insert=None, update=None, delete=None):
        """
        Execute a bulk WFS transaction for insert/update/delete operations.
        
        Args:
            plan_id (str): The BNG plan ID
            org_id (str): Organization ID
            insert (list|None): List of GeoJSON features to insert
            update (list|None): List of GeoJSON features to update
            delete (list|None): List of dicts with 'id' key for features to delete
            
        Returns:
            dict | None: Transaction response containing:
                - transactionSummary: {totalInserted, totalUpdated, totalDeleted}
                - insertResults: array of created features with server IDs
                - updateResults: array of updated features
                - deleteResults: array of delete results
            Returns None on failure.
        """
        if not self.auth_manager.is_logged_in():
            QgsMessageLog.logMessage("Cannot execute WFS transaction: Not logged in", "BNGAI Plugin", level=2)
            return None

        try:
            token = self.auth_manager.get_token()
            if not token:
                return None

            legacy_backend_url = self._get_legacy_backend_url()
            url = f"{legacy_backend_url}/api/v1/wfs/transaction"
            headers = self._get_api_headers(token, org_id)

            params = {
                "layerType": "plan",
                "planId": plan_id
            }

            # Build transaction payload
            payload = {
                "version": "2.0.0",
                "insert": insert or [],
                "update": update or [],
                "delete": delete or []
            }

            QgsMessageLog.logMessage(f"Executing WFS transaction for plan: {plan_id}", "BNGAI Plugin", level=0)
            QgsMessageLog.logMessage(f"Insert count: {len(payload['insert'])}, Update count: {len(payload['update'])}, Delete count: {len(payload['delete'])}", "BNGAI Plugin", level=0)
            
            # Log insert payload details for debugging
            if payload['insert']:
                for i, feat in enumerate(payload['insert']):
                    props = feat.get('properties', {})
                    geom_type = feat.get('geometry', {}).get('type', 'unknown')
                    QgsMessageLog.logMessage(
                        f"Insert[{i}]: clientId={props.get('clientId')}, "
                        f"activityType={props.get('activityType')}, "
                        f"aiDashCode={props.get('planHabitatAidashCode')}, "
                        f"geomType={geom_type}",
                        "BNGAI Plugin", level=0
                    )

            response = requests.post(url, headers=headers, params=params, json=payload)

            if response.status_code != 200:
                QgsMessageLog.logMessage(
                    f"WFS transaction failed. Status code: {response.status_code}, body: {response.text}",
                    "BNGAI Plugin",
                    level=2,
                )
                return None

            data = response.json()
            
            # Log transaction summary
            summary = data.get("transactionSummary", {})
            QgsMessageLog.logMessage(
                f"WFS transaction completed: {summary.get('totalInserted', 0)} inserted, "
                f"{summary.get('totalUpdated', 0)} updated, {summary.get('totalDeleted', 0)} deleted",
                "BNGAI Plugin",
                level=0
            )
            
            # Log any insert results with errors
            insert_results = data.get("insertResults", [])
            if insert_results:
                for i, result in enumerate(insert_results):
                    props = result.get('properties', {})
                    status = props.get('status', 'unknown')
                    error = props.get('error') or props.get('message') or props.get('errorMessage')
                    QgsMessageLog.logMessage(
                        f"InsertResult[{i}]: id={result.get('id')}, status={status}, error={error}",
                        "BNGAI Plugin", level=0 if status == 'SUCCESS' else 2
                    )
            elif payload['insert'] and summary.get('totalInserted', 0) == 0:
                # No insert results but we sent inserts - log full response for debugging
                import json
                QgsMessageLog.logMessage(
                    f"WARNING: Sent {len(payload['insert'])} inserts but got 0 results. Full response: {json.dumps(data, indent=2)[:2000]}",
                    "BNGAI Plugin", level=1
                )
            
            return data

        except Exception as e:
            QgsMessageLog.logMessage(f"Error executing WFS transaction: {str(e)}", "BNGAI Plugin", level=2)
            import traceback
            QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            return None

    def create_bng_plan_habitat(self, bng_plan_id, geometry, activity_type, org_id):
        """
        Create a new BNG plan habitat using GraphQL API.
        
        Args:
            bng_plan_id (str): The BNG plan ID
            geometry (dict): GeoJSON geometry object
            activity_type (str): Activity type for the habitat
            org_id (str): Organization ID
            
        Returns:
            dict: Response containing the created habitat data, or None if failed
        """
        if not self.auth_manager.is_logged_in():
            QgsMessageLog.logMessage("Cannot create BNG plan habitat: Not logged in", "BNGAI Plugin", level=2)
            return None

        try:
            token = self.auth_manager.get_token()
            if not token:
                return None

            url = self._get_graphql_url()
            headers = self._get_api_headers(token, org_id)

            query = """
            mutation ($input: CreateBngPlanHabitatInput!) {
              createBngPlanHabitat(input: $input) {
                planHabitatId
                errorMessage
                __typename
              }
            }
            """

            variables = {
                "input": {
                    "bngPlanId": bng_plan_id,
                    "geometry": geometry,
                    "activityType": activity_type
                }
            }

            payload = {
                "query": query,
                "variables": variables
            }

            QgsMessageLog.logMessage(f"Creating BNG plan habitat for plan: {bng_plan_id}", "BNGAI Plugin", level=0)
            response = self._make_request("POST", url, headers=headers, json=payload)
            
            if response and "data" in response:
                result = response["data"].get("createBngPlanHabitat")
                if result:
                    QgsMessageLog.logMessage(f"Successfully created habitat with ID: {result.get('planHabitatId')}", "BNGAI Plugin", level=0)
                    return result
                    
            QgsMessageLog.logMessage("Failed to create BNG plan habitat", "BNGAI Plugin", level=2)
            return None
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error creating BNG plan habitat: {str(e)}", "BNGAI Plugin", level=2)
            return None
    def _get_api_headers(self, token, org_id):
        """Get standardized API headers"""
        return {
            "Accept": "application/json, text/plain, */*",
            "Authorization": token,
            "Content-Type": "application/json",
            "Organization-Id": org_id,
            "Origin": ApiConfig.get_header_origin(),
            "Referer": ApiConfig.get_header_referer()
        }
    
    def create_habitats(self, plan_id, geometries, org_id):
        """
        Create new habitats with geometries
        
        Args:
            plan_id (str): BNG Plan ID
            geometries (list): List of GeoJSON geometries
            org_id (str): Organization ID
        
        Returns:
            list: List of created habitat IDs
        """
        if not self.auth_manager.is_logged_in():
            QgsMessageLog.logMessage("Cannot create habitats: Not logged in", "BNGAI Plugin", level=2)
            return None
        
        try:
            token = self.auth_manager.get_token()
            if not token:
                return None
            
            headers = self._get_api_headers(token, org_id)
            
            # GraphQL mutation to create habitats
            mutation = """
            mutation createBNGPlanHabitats($input: CreateBNGPlanHabitatsInput!) {
                createBNGPlanHabitats(input: $input) {
                    bngPlanHabitats {
                        id
                        geometry
                    }
                }
            }
            """
            
            variables = {
                "input": {
                    "bngPlanId": plan_id,
                    "geometries": geometries
                }
            }
            
            payload = {
                "query": mutation,
                "variables": variables
            }
            
            response = requests.post(self.graphql_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data and "createBNGPlanHabitats" in data["data"]:
                    created_habitats = data["data"]["createBNGPlanHabitats"]["bngPlanHabitats"]
                    return [habitat["id"] for habitat in created_habitats]
            
            return None
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error creating habitats: {str(e)}", "BNGAI Plugin", level=2)
            return None
    
    def update_habitats(self, habitat_ids, attributes, org_id):
        """
        Update habitat attributes
        
        Args:
            habitat_ids (list): List of habitat IDs to update
            attributes (dict): Habitat attributes to update
            org_id (str): Organization ID
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.auth_manager.is_logged_in():
            QgsMessageLog.logMessage("Cannot update habitats: Not logged in", "BNGAI Plugin", level=2)
            return False
        
        try:
            token = self.auth_manager.get_token()
            if not token:
                return False
            
            headers = self._get_api_headers(token, org_id)
            
            # GraphQL mutation to update habitats
            mutation = """
            mutation updateBNGPlanHabitats($input: UpdateBNGPlanHabitatsInput!) {
                updateBNGPlanHabitats(input: $input) {
                    bngPlanHabitats {
                        id
                    }
                }
            }
            """
            
            variables = {
                "input": {
                    "habitatIds": habitat_ids,
                    "attributes": attributes
                }
            }
            
            payload = {
                "query": mutation,
                "variables": variables
            }
            
            response = requests.post(self.graphql_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                return "data" in data and "updateBNGPlanHabitats" in data["data"]
            
            return False
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error updating habitats: {str(e)}", "BNGAI Plugin", level=2)
            return False

        if not self.auth_manager.is_logged_in():
            QgsMessageLog.logMessage("Cannot validate habitat: Not logged in", "BNGAI Plugin", level=2)
            return None

        try:
            token = self.auth_manager.get_token()
            if not token:
                return None

            org_id = self.auth_manager.get_current_organization().get("id")
            if not org_id:
                QgsMessageLog.logMessage("Cannot validate habitat: No organization selected", "BNGAI Plugin", level=2)
                return None

            headers = self._get_api_headers(token, org_id)
            
            query = """
            query ($planHabitatId: UUID, $bngPlanId: UUID!, $geometry: JSON!) {
                verifyIfValidUpdateBngPlanHabitat(
                    input: {
                        bngPlanId: $bngPlanId,
                        geometry: $geometry,
                        planHabitatId: $planHabitatId
                    }
                ) {
                    warningMsg
                    warningTitle
                    hasWarning
                }
            }
            """
            
            variables = {
                "bngPlanId": bng_plan_id,
                "geometry": geometry,
                "planHabitatId": plan_habitat_id
            }
            
            payload = {
                "query": query,
                "variables": variables
            }

            QgsMessageLog.logMessage(f"Validating habitat geometry for plan: {bng_plan_id}", "BNGAI Plugin", level=0)
            response = requests.post(self.graphql_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data and "verifyIfValidUpdateBngPlanHabitat" in data["data"]:
                    QgsMessageLog.logMessage("Successfully validated habitat geometry", "BNGAI Plugin", level=0)
                    return data["data"]["verifyIfValidUpdateBngPlanHabitat"]
                else:
                    QgsMessageLog.logMessage(f"Invalid response format: {data}", "BNGAI Plugin", level=2)
            else:
                QgsMessageLog.logMessage(f"Failed to validate habitat geometry. Status code: {response.status_code}", "BNGAI Plugin", level=2)
                QgsMessageLog.logMessage(f"Response text: {response.text}", "BNGAI Plugin", level=2)

            return None
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error validating habitat geometry: {str(e)}", "BNGAI Plugin", level=2)
            import traceback
            QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            return None 

    def get_plan_layers_post_intervention(self, bng_plan_id: str, site_revision_id: str, org_id: str):
        """
        Fetch base and BNG plan layers via REST API.
        Endpoint: GET /plan/layer/post-intervention?bngPlanId=...&siteRevisionId=...

        Args:
            bng_plan_id (str): BNG Plan ID
            site_revision_id (str): Site Revision ID
            org_id (str): Organization ID

        Returns:
            dict | None: Parsed JSON on success, None otherwise
        """
        if not self.auth_manager or not self.auth_manager.is_logged_in():
            QgsMessageLog.logMessage("Cannot fetch plan layers: Not logged in", "BNGAI Plugin", level=2)
            return None

        try:
            token = self.auth_manager.get_token()
            if not token:
                QgsMessageLog.logMessage("Cannot fetch plan layers: No token", "BNGAI Plugin", level=2)
                return None

            url = f"{self.api_url}/plan/layer/post-intervention"
            headers = self._get_api_headers(token, org_id)
            params = {
                "bngPlanId": bng_plan_id,
                "siteRevisionId": site_revision_id,
            }

            QgsMessageLog.logMessage(
                f"Fetching plan layers (post-intervention) for plan={bng_plan_id}, siteRevision={site_revision_id}",
                "BNGAI Plugin", level=0
            )
            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception:
                    QgsMessageLog.logMessage("Failed to parse JSON from plan layers response", "BNGAI Plugin", level=2)
                    return None
                QgsMessageLog.logMessage("Successfully fetched plan layers (post-intervention)", "BNGAI Plugin", level=0)
                return data

            QgsMessageLog.logMessage(
                f"Failed to fetch plan layers. Status code: {response.status_code}",
                "BNGAI Plugin", level=2
            )
            QgsMessageLog.logMessage(f"Response text: {response.text}", "BNGAI Plugin", level=2)
            return None
        except Exception as e:
            QgsMessageLog.logMessage(f"Error fetching plan layers: {str(e)}", "BNGAI Plugin", level=2)
            import traceback
            QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            return None