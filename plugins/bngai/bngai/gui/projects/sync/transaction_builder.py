"""
TransactionBuilder - Builds WFS transaction payloads from change sets.

Single Responsibility: Only handles building transaction payloads.
"""
from typing import Dict, List, Optional, Any
import json

from .models import ChangeSet, FeatureChange, TransactionPayload
from .utils import safe_get_attribute, determine_activity_type, safe_lower, log_error
from ....utils.habitat_mappings import (
    CONDITION_MAP,
    STRATEGIC_SIGNIFICANCE_MAP,
    WATERCOURSE_ENCROACHMENT_MAP,
    RIPARIAN_ENCROACHMENT_MAP,
    map_value
)


class TransactionBuilder:
    """
    Builds WFS transaction payloads from detected changes.
    
    Responsibilities:
    - Convert FeatureChange objects to GeoJSON features
    - Build insert/update/delete payloads
    - Map attribute values using habitat mappings
    """
    
    def __init__(self):
        """Initialize the builder"""
        self._client_id_mapping: Dict[str, Any] = {}
    
    @property
    def client_id_mapping(self) -> Dict[str, Any]:
        """
        Get mapping from clientId to local feature.
        
        Used by TransactionProcessor to update local features after insert.
        """
        return self._client_id_mapping
    
    def build_from_changes(self, changes: ChangeSet) -> TransactionPayload:
        """
        Build transaction payload from a ChangeSet.
        
        Args:
            changes: ChangeSet containing inserts, updates, deletes
            
        Returns:
            TransactionPayload ready for API
        """
        self._client_id_mapping.clear()
        payload = TransactionPayload()
        
        # Build insert features
        for change in changes.inserts:
            feature = self._build_insert_feature(change)
            if feature:
                payload.insert.append(feature)
                # Track clientId mapping
                client_id = feature.get('properties', {}).get('clientId')
                if client_id and change.local_feature:
                    self._client_id_mapping[client_id] = change.local_feature
        
        # Build update features
        for change in changes.updates:
            feature = self._build_update_feature(change)
            if feature:
                payload.update.append(feature)
        
        # Build delete entries
        for change in changes.deletes:
            payload.delete.append({'id': change.feature_id})
        
        return payload
    
    def build_from_legacy_changes(self, changes: Dict[str, List]) -> TransactionPayload:
        """
        Build transaction payload from legacy changes format.
        
        Args:
            changes: Legacy format {'new': [...], 'updated': [...], 'deleted': [...]}
            
        Returns:
            TransactionPayload ready for API
        """
        self._client_id_mapping.clear()
        payload = TransactionPayload()
        
        # Build insert features
        for change in changes.get('new', []):
            feature_data = change.get('data', {})
            local_feature = feature_data.get('feature')
            if not local_feature:
                continue
            
            geojson = self._feature_to_geojson(local_feature, is_new=True)
            if geojson:
                payload.insert.append(geojson)
                client_id = geojson.get('properties', {}).get('clientId')
                if client_id:
                    self._client_id_mapping[client_id] = local_feature
        
        # Build update features
        for change in changes.get('updated', []):
            feature_id = change.get('id')
            feature_data = change.get('data', {})
            local_feature = feature_data.get('feature')
            if not local_feature:
                continue
            
            geojson = self._feature_to_geojson(local_feature, is_new=False, server_id=feature_id)
            if geojson:
                payload.update.append(geojson)
        
        # Build delete entries
        for change in changes.get('deleted', []):
            payload.delete.append({'id': change.get('id')})
        
        return payload
    
    def _build_insert_feature(self, change: FeatureChange) -> Optional[Dict]:
        """
        Build GeoJSON feature for insert operation.
        
        Args:
            change: FeatureChange for insert
            
        Returns:
            GeoJSON feature dict or None
        """
        if not change.local_feature:
            return None
        return self._feature_to_geojson(change.local_feature, is_new=True)
    
    def _build_update_feature(self, change: FeatureChange) -> Optional[Dict]:
        """
        Build GeoJSON feature for update operation.
        
        Args:
            change: FeatureChange for update
            
        Returns:
            GeoJSON feature dict or None
        """
        if not change.local_feature:
            return None
        return self._feature_to_geojson(
            change.local_feature, 
            is_new=False, 
            server_id=change.feature_id
        )
    
    def _feature_to_geojson(self, feature, is_new: bool = True, 
                            server_id: Optional[str] = None) -> Optional[Dict]:
        """
        Convert QgsFeature to GeoJSON for WFS transaction.
        
        Args:
            feature: QgsFeature to convert
            is_new: True for insert, False for update
            server_id: Server ID (required for updates)
            
        Returns:
            GeoJSON feature dict or None on error
        """
        try:
            # Get geometry
            geometry = json.loads(feature.geometry().asJson())
            geometry_type = geometry.get('type', '')
            
            # Build properties
            properties = self._build_properties(feature, geometry_type)
            
            # Build GeoJSON feature
            geojson = {
                'type': 'Feature',
                'geometry': geometry,
                'properties': properties
            }
            
            # Add server ID for updates
            if not is_new and server_id:
                geojson['id'] = server_id
            
            return geojson
            
        except Exception as e:
            log_error(f"Error converting feature to GeoJSON: {str(e)}")
            return None
    
    def _build_properties(self, feature, geometry_type: str) -> Dict:
        """
        Build properties object for WFS transaction.
        
        Args:
            feature: QgsFeature to extract properties from
            geometry_type: GeoJSON geometry type
            
        Returns:
            Properties dictionary
        """
        # Determine activity type based on geometry type
        existing_type = safe_get_attribute(feature, 'activityType')
        activity_type = determine_activity_type(geometry_type, existing_type)
        
        properties = {
            'activityType': activity_type,
            'clientId': safe_get_attribute(feature, 'clientId'),
        }
        
        # Add aiDash code
        aidash_code = safe_get_attribute(feature, 'aiDashCode')
        if aidash_code:
            properties['planHabitatAidashCode'] = safe_lower(aidash_code)
        
        # Add condition code
        condition = safe_get_attribute(feature, 'condition')
        if condition:
            mapped = map_value(condition, CONDITION_MAP)
            if mapped:
                properties['conditionCode'] = mapped
        
        # Add strategic significance
        strategic = safe_get_attribute(feature, 'strategicSignificance')
        if strategic:
            mapped = map_value(strategic, STRATEGIC_SIGNIFICANCE_MAP)
            if mapped:
                properties['strategicSignificanceCode'] = mapped
        
        # Add tree size (points)
        tree_size = safe_get_attribute(feature, 'treeSize')
        if tree_size:
            properties['treeSizeCode'] = safe_lower(tree_size)
        
        # Add watercourse encroachment (lines)
        watercourse = safe_get_attribute(feature, 'watercourseEncroachment')
        if watercourse:
            mapped = map_value(watercourse, WATERCOURSE_ENCROACHMENT_MAP)
            if mapped:
                properties['watercourseEncroachmentCode'] = mapped
        
        # Add riparian encroachment (lines)
        riparian = safe_get_attribute(feature, 'riparianEncroachment')
        if riparian:
            mapped = map_value(riparian, RIPARIAN_ENCROACHMENT_MAP)
            if mapped:
                properties['riparianEncroachmentCode'] = mapped
        
        return properties

