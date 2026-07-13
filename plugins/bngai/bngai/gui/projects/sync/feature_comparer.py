"""
FeatureComparer - Compares local and server features to detect changes.

Single Responsibility: Only handles feature comparison logic.
"""
from typing import Dict, Set, Tuple, Optional, Any
from qgis.core import QgsVectorLayer, QgsGeometry
import json
import os

from .models import ChangeSet, FeatureChange, OperationType
from .utils import normalize_for_compare, safe_get_attribute, log_info, log_error, filter_features_by_geometry_type
from ....utils.layersUtils import LayersUtils

# Load allowed attributes config
_ALLOWED_ATTRIBUTES_CONFIG = None

def _load_allowed_attributes_config() -> Dict:
    """Load the DEFRA_BIDV3 allowed attributes config"""
    global _ALLOWED_ATTRIBUTES_CONFIG
    if _ALLOWED_ATTRIBUTES_CONFIG is None:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            'utils', 'DEFRA_BIDV3_ALLOWED_ATTRIBUTES_PER_AIDASH_CODE.json'
        )
        try:
            with open(config_path, 'r') as f:
                _ALLOWED_ATTRIBUTES_CONFIG = json.load(f)
        except Exception as e:
            log_error(f"Failed to load allowed attributes config: {e}")
            _ALLOWED_ATTRIBUTES_CONFIG = {}
    return _ALLOWED_ATTRIBUTES_CONFIG

# Mapping from local field names to config keys
FIELD_TO_CONFIG_KEY = {
    'condition': 'condition',
    'strategicSignificance': 'strategic_significance',
    'treeSize': 'tree_size',
    'watercourseEncroachment': 'watercourse_encroachment',
    'riparianEncroachment': 'riparian_encroachment'
}


class FeatureComparer:
    """
    Compares local layer features with server features to identify changes.
    
    Responsibilities:
    - Extract features from local layers
    - Fetch features from server via API
    - Compare features and detect inserts, updates, deletes
    """
    
    # Attributes to ignore during comparison
    IGNORED_ATTRIBUTES = frozenset({
        'sourceId', 'activityType', 'aiDashLabel', 
        'mergedIds', 'referenceId', 'clientId'
    })
    
    # Geometry comparison tolerances
    AREA_TOLERANCE = 0.001  # 0.1%
    LENGTH_TOLERANCE = 0.001  # 0.1%
    
    def __init__(self, api_client):
        """
        Initialize the comparer.
        
        Args:
            api_client: API client for fetching server data
        """
        self.api_client = api_client
    
    def compare_layer(self, layer: QgsVectorLayer, server_features: Dict[str, Dict]) -> ChangeSet:
        """
        Compare a single layer with server features.
        
        Args:
            layer: QGIS vector layer to compare
            server_features: Server features dictionary
            
        Returns:
            ChangeSet with detected changes
        """
        # Get local features
        local_features, deleted_ids = self._extract_local_features(layer)
        
        # Get feature type from layer
        feature_type = self._get_layer_feature_type(layer)
        
        # Filter server features for this geometry type
        filtered_server = filter_features_by_geometry_type(server_features, feature_type)
        
        # Compute changes
        return self._compute_changes(local_features, filtered_server, deleted_ids)
    
    def get_server_features(self, plan_id: str, org_id: str) -> Tuple[Dict[str, Dict], Optional[str]]:
        """
        Fetch all features from server for a plan.
        
        Args:
            plan_id: BNG Plan ID
            org_id: Organization ID
            
        Returns:
            Tuple of (features dict, error message or None)
        """
        geojson_data = self.api_client.get_bng_plan_habitats(plan_id, org_id)
        
        if not geojson_data or geojson_data.get("type") != "FeatureCollection":
            return {}, "No BNG Plan habitats found in the response"
        
        features = geojson_data.get("features", [])
        server_features = {}
        
        for feature in features:
            if feature.get("type") != "Feature":
                continue
            
            geometry = feature.get("geometry")
            if not geometry:
                continue
            
            feature_id = feature.get("id")
            properties = feature.get("properties", {})
            
            # Build habitat data structure
            habitat = self._build_habitat_data(feature_id, geometry, properties)
            
            server_features[feature_id] = {
                'id': feature_id,
                'geometry': geometry,
                'data': habitat
            }
        
        return server_features, None
    
    def _extract_local_features(self, layer: QgsVectorLayer) -> Tuple[Dict[str, Dict], Set[str]]:
        """
        Extract features from local layer.
        
        Args:
            layer: QGIS vector layer
            
        Returns:
            Tuple of (features dict, deleted feature IDs set)
        """
        current_features = {}
        deleted_feature_ids = set()
        field_names = [field.name() for field in layer.fields()]
        
        for feature in layer.getFeatures():
            feature_id = feature.attribute('id')
            source_id = feature.attribute('sourceId') if 'sourceId' in field_names else None
            merged_ids = feature.attribute('mergedIds') if 'mergedIds' in field_names else None
            
            
            
            # Handle null IDs with sourceId
            if self._is_null_id(feature_id) and source_id:
                deleted_feature_ids.add(source_id)
            
            # Handle mergedIds
            if merged_ids:
                self._process_merged_ids(merged_ids, feature_id, deleted_feature_ids)
            
            # Use fallback key if id is None/empty
            key = feature_id if not self._is_null_id(feature_id) else f"local_{feature.id()}"
            
            
            current_features[key] = {
                'id': feature.attribute('id'),
                'geometry': feature.geometry().asWkt(),
                'feature': feature
            }
        
        # Remove IDs that exist in current features from deleted set
        deleted_feature_ids -= set(current_features.keys())
        
        return current_features, deleted_feature_ids
    
    def _compute_changes(self, local: Dict, server: Dict, deleted_ids: Set[str]) -> ChangeSet:
        """
        Compute differences between local and server features.
        
        Args:
            local: Local features dictionary
            server: Server features dictionary
            deleted_ids: Set of explicitly deleted feature IDs
            
        Returns:
            ChangeSet with detected changes
        """
        changes = ChangeSet()
        
        log_info(f"Computing changes: {len(local)} local features, {len(server)} server features")
        
        # Find new and updated features
        for feature_id, feature_data in local.items():
            is_local_prefix = feature_id.startswith('local_')
            not_in_server = feature_id not in server
            local_feature = feature_data.get('feature')
            
            if is_local_prefix or not_in_server:
                # New feature - log details
                self._log_insert_details(feature_id, local_feature, is_local_prefix, not_in_server)
                changes.inserts.append(FeatureChange(
                    feature_id=feature_id,
                    operation=OperationType.INSERT,
                    local_feature=local_feature,
                    client_id=safe_get_attribute(local_feature, 'clientId')
                ))
            elif not self._features_match(feature_data, server[feature_id], feature_id):
                # Updated feature - details logged in _features_match
                changes.updates.append(FeatureChange(
                    feature_id=feature_id,
                    operation=OperationType.UPDATE,
                    local_feature=local_feature,
                    server_data=server[feature_id]
                ))
            else:
                log_info(f"NO CHANGE: feature_id='{feature_id}' matches server")
        
        # Find deleted features
        for feature_id in server:
            if feature_id not in local or feature_id in deleted_ids:
                self._log_delete_details(feature_id, server[feature_id], feature_id not in local, feature_id in deleted_ids)
                changes.deletes.append(FeatureChange(
                    feature_id=feature_id,
                    operation=OperationType.DELETE,
                    server_data=server[feature_id]
                ))
        
        return changes
    
    def _log_insert_details(self, feature_id: str, feature: Any, is_local_prefix: bool, not_in_server: bool) -> None:
        """Log detailed information about a new feature being inserted."""
        log_info(f"INSERT detected: feature_id='{feature_id}' (local_prefix={is_local_prefix}, not_in_server={not_in_server})")
        if feature:
            aidash_code = safe_get_attribute(feature, 'aiDashCode')
            client_id = safe_get_attribute(feature, 'clientId')
            condition = safe_get_attribute(feature, 'condition')
            strategic_significance = safe_get_attribute(feature, 'strategicSignificance')
            activity_type = safe_get_attribute(feature, 'activityType')
            log_info(f"  INSERT details: aiDashCode='{aidash_code}', clientId='{client_id}', "
                    f"condition='{condition}', strategicSignificance='{strategic_significance}', "
                    f"activityType='{activity_type}'")
    
    def _log_delete_details(self, feature_id: str, server_data: Dict, not_in_local: bool, in_deleted: bool) -> None:
        """Log detailed information about a feature being deleted."""
        log_info(f"DELETE detected: feature_id='{feature_id}' (not_in_local={not_in_local}, in_deleted={in_deleted})")
        if server_data:
            data = server_data.get('data', {})
            aidash_code = data.get('aiDashCode')
            reference_id = data.get('referenceId')
            log_info(f"  DELETE details: aiDashCode='{aidash_code}', referenceId='{reference_id}'")
    
    def _features_match(self, local_data: Dict, server_data: Dict, feature_id: str = "") -> bool:
        """
        Compare two features to check if they match.
        
        Args:
            local_data: Local feature data
            server_data: Server feature data
            feature_id: Feature ID for logging
            
        Returns:
            True if features match
        """
        try:
            geometry_changed = False
            attributes_changed = False
            
            # Compare geometries
            if not self._geometries_match(local_data['geometry'], server_data['geometry'], feature_id):
                geometry_changed = True
            
            # Compare attributes
            if not self._attributes_match(local_data, server_data, feature_id):
                attributes_changed = True
            
            # Log UPDATE details if anything changed
            if geometry_changed or attributes_changed:
                change_types = []
                if geometry_changed:
                    change_types.append("GEOMETRY")
                if attributes_changed:
                    change_types.append("ATTRIBUTES")
                log_info(f"UPDATE detected: feature_id='{feature_id}' - Changes: {', '.join(change_types)}")
                return False
            
            return True
            
        except Exception as e:
            log_error(f"Error comparing features: {str(e)}")
            return False
    
    # Centroid tolerance in degrees (approx 1 meter at equator)
    CENTROID_TOLERANCE = 0.00001
    
    def _geometries_match(self, geom1_data: Any, geom2_data: Any, feature_id: str = "") -> bool:
        """
        Compare two geometries.
        
        Checks for both shape changes (area/length) AND position changes (centroid).
        
        Args:
            geom1_data: First geometry (WKT string or GeoJSON dict)
            geom2_data: Second geometry (WKT string or GeoJSON dict)
            feature_id: Feature ID for logging
            
        Returns:
            True if geometries match within tolerance
        """
        # Convert to WKT
        wkt1 = LayersUtils.geojson_to_wkt(geom1_data) if isinstance(geom1_data, dict) else geom1_data
        wkt2 = LayersUtils.geojson_to_wkt(geom2_data) if isinstance(geom2_data, dict) else geom2_data
        
        # Get geometry types
        geom_type1 = geom1_data.get('type', '').lower() if isinstance(geom1_data, dict) else ''
        geom_type2 = geom2_data.get('type', '').lower() if isinstance(geom2_data, dict) else ''
        
        # Create QgsGeometry objects
        geom1 = QgsGeometry.fromWkt(wkt1) if wkt1 else None
        geom2 = QgsGeometry.fromWkt(wkt2) if wkt2 else None
        
        if not geom1 or not geom2:
            return False
        
        # Determine geometry category
        is_polygon = 'polygon' in geom_type1 or 'polygon' in geom_type2
        is_line = 'linestring' in geom_type1 or 'linestring' in geom_type2
        is_point = 'point' in geom_type1 or 'point' in geom_type2
        
        # Compare based on geometry type
        if is_polygon:
            # Check shape change (area and perimeter)
            area_diff = self._relative_diff(geom1.area(), geom2.area())
            length_diff = self._relative_diff(geom1.length(), geom2.length())
            shape_matches = area_diff <= self.AREA_TOLERANCE and length_diff <= self.LENGTH_TOLERANCE
            
            # Check position change (centroid)
            position_matches = self._centroids_match(geom1, geom2)
            
            if not shape_matches or not position_matches:
                changes = []
                if not shape_matches:
                    changes.append(f"SHAPE (area_diff={area_diff:.4f}, length_diff={length_diff:.4f})")
                if not position_matches:
                    changes.append("POSITION (centroid moved)")
                log_info(f"  GEOMETRY change for '{feature_id}': {', '.join(changes)}")
            
            return shape_matches and position_matches
            
        elif is_line:
            # Check length change
            length_diff = self._relative_diff(geom1.length(), geom2.length())
            length_matches = length_diff <= self.LENGTH_TOLERANCE
            
            # Check position change (centroid)
            position_matches = self._centroids_match(geom1, geom2)
            
            if not length_matches or not position_matches:
                changes = []
                if not length_matches:
                    changes.append(f"LENGTH (diff={length_diff:.4f})")
                if not position_matches:
                    changes.append("POSITION (centroid moved)")
                log_info(f"  GEOMETRY change for '{feature_id}': {', '.join(changes)}")
            
            return length_matches and position_matches
            
        elif is_point:
            matches = geom1.equals(geom2)
            if not matches:
                log_info(f"  GEOMETRY change for '{feature_id}': POINT position changed")
            return matches
        else:
            matches = geom1.equals(geom2)
            if not matches:
                log_info(f"  GEOMETRY change for '{feature_id}': geometry differs")
            return matches
    
    def _centroids_match(self, geom1: QgsGeometry, geom2: QgsGeometry) -> bool:
        """
        Compare centroids of two geometries to detect position changes.
        
        Args:
            geom1: First QgsGeometry
            geom2: Second QgsGeometry
            
        Returns:
            True if centroids are within tolerance
        """
        centroid1 = geom1.centroid()
        centroid2 = geom2.centroid()
        
        if not centroid1 or not centroid2:
            return False
        
        pt1 = centroid1.asPoint()
        pt2 = centroid2.asPoint()
        
        x_diff = abs(pt1.x() - pt2.x())
        y_diff = abs(pt1.y() - pt2.y())
        
        return x_diff <= self.CENTROID_TOLERANCE and y_diff <= self.CENTROID_TOLERANCE
    
    def _attributes_match(self, local_data: Dict, server_data: Dict, feature_id: str = "") -> bool:
        """
        Compare feature attributes based on aiDashCode config.
        
        Only compares attributes that are relevant for the feature's aiDashCode
        (i.e., attributes with non-empty allowed values in the config).
        
        Args:
            local_data: Local feature data containing 'feature' key
            server_data: Server data containing 'data' key
            feature_id: Feature ID for logging
            
        Returns:
            True if attributes match
        """
        local_feature = local_data.get('feature')
        server_attrs = server_data.get('data', {})
        
        if not local_feature:
            return False
        
        # Get aiDashCode to determine which attributes are relevant
        aidash_code = safe_get_attribute(local_feature, 'aiDashCode')
        if aidash_code:
            aidash_code = str(aidash_code).lower()
        
        # Get relevant attributes for this aiDashCode
        relevant_fields = self._get_relevant_fields(aidash_code)
        
        # Get all fields, filtering by relevance and ignored list
        all_fields = [f.name() for f in local_feature.fields() if f.name() not in self.IGNORED_ATTRIBUTES]
        
        mismatches = []
        for field_name in all_fields:
            # Skip fields that aren't relevant for this aiDashCode
            if field_name in FIELD_TO_CONFIG_KEY and field_name not in relevant_fields:
                continue
            
            local_val = normalize_for_compare(local_feature[field_name])
            server_val = normalize_for_compare(server_attrs.get(field_name))
            
            if local_val != server_val:
                mismatches.append(f"{field_name}: local='{local_val}' vs server='{server_val}'")
        
        if mismatches:
            log_info(f"Feature '{feature_id}' (aiDashCode={aidash_code}) ATTRIBUTE mismatches: {mismatches}")
            return False
        
        return True
    
    def _get_relevant_fields(self, aidash_code: str) -> Set[str]:
        """
        Get the set of relevant field names for a given aiDashCode.
        
        A field is relevant if it has non-empty allowed values in the config.
        
        Args:
            aidash_code: The aiDashCode (lowercase)
            
        Returns:
            Set of relevant field names
        """
        config = _load_allowed_attributes_config()
        relevant = set()
        
        if not aidash_code or aidash_code not in config:
            # If no config found, compare all fields
            return set(FIELD_TO_CONFIG_KEY.keys())
        
        code_config = config.get(aidash_code, {})
        
        for field_name, config_key in FIELD_TO_CONFIG_KEY.items():
            allowed_values = code_config.get(config_key, [])
            if allowed_values:  # Has allowed values, so field is relevant
                relevant.add(field_name)
        
        log_info(f"Relevant fields for aiDashCode '{aidash_code}': {relevant}")
        return relevant
    
    def _build_habitat_data(self, feature_id: str, geometry: Dict, properties: Dict) -> Dict:
        """
        Build habitat data structure from API response.
        
        Args:
            feature_id: Feature ID
            geometry: GeoJSON geometry
            properties: Feature properties
            
        Returns:
            Habitat data dictionary
        """
        # Debug: log raw properties keys for the first few features
        
        
        habitat = {
            'id': feature_id,
            'geometry': geometry,
            'activityType': properties.get('activityType'),
            'treeSize': properties.get('treeSizeCode'),
            'condition': properties.get('conditionCode'),
            'distinctiveness': properties.get('distinctiveness'),
            'strategicSignificance': properties.get('strategicSignificanceCode'),
            'riparianEncroachment': properties.get('riparianEncroachmentCode'),
            'watercourseEncroachment': properties.get('watercourseEncroachmentCode'),
            'watercourseAndRiparianEncroachment': properties.get('watercourseAndRiparianEncroachmentCode'),
            'referenceId': properties.get('referenceId') or properties.get('habitatReferenceId'),
            'area': properties.get('area'),
        }
        
        # Normalize aiDash code
        plan_habitat_code = properties.get("planHabitatAidashCode")
        if plan_habitat_code:
            habitat['aiDashCode'] = str(plan_habitat_code).strip().lower()
        
        return habitat
    
    def _get_layer_feature_type(self, layer: QgsVectorLayer) -> str:
        """
        Get feature type from layer custom property.
        
        Args:
            layer: QGIS vector layer
            
        Returns:
            Feature type: 'point', 'line', or 'polygon'
        """
        bngai_id = layer.customProperty('bngai_id', '')
        try:
            return bngai_id.split('_')[2]
        except (IndexError, AttributeError):
            return 'unknown'
    
    @staticmethod
    def _is_null_id(feature_id: Any) -> bool:
        """Check if feature ID is null or empty"""
        if not feature_id:
            return True
        return str(feature_id).lower() in ['none', 'null', '']
    
    @staticmethod
    def _relative_diff(val1: float, val2: float) -> float:
        """Calculate relative difference between two values"""
        max_val = max(abs(val1), abs(val2))
        if max_val == 0:
            return 0
        return abs(val1 - val2) / max_val
    
    def _process_merged_ids(self, merged_ids: Any, feature_id: str, deleted_set: Set[str]) -> None:
        """Process merged IDs and add to deleted set"""
        try:
            id_list = json.loads(merged_ids) if isinstance(merged_ids, str) else merged_ids
            if isinstance(id_list, list):
                deleted_set.update([mid for mid in id_list if mid != feature_id])
        except Exception as e:
            log_error(f"Error processing mergedIds: {str(e)}")

