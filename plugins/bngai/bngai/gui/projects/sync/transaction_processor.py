"""
TransactionProcessor - Processes WFS transaction results.

Single Responsibility: Only handles processing transaction responses 
and updating local features.
"""
from typing import Dict, List, Any, Optional
from qgis.core import QgsVectorLayer

from .models import (
    TransactionResult, OperationResult, TransactionPayload,
    SyncStatus
)
from .utils import log_info, log_error
from ....utils.sync_tracker import SyncTracker


class TransactionProcessor:
    """
    Processes WFS transaction results and updates local features.
    
    Responsibilities:
    - Parse transaction response
    - Update local features with server IDs (for inserts)
    - Track operation results for reporting
    """
    
    def __init__(self, sync_tracker: Optional[SyncTracker] = None):
        """
        Initialize the processor.
        
        Args:
            sync_tracker: Optional tracker for recording operations
        """
        self.sync_tracker = sync_tracker or SyncTracker()
    
    def process(self, layer: QgsVectorLayer, 
                result: TransactionResult,
                client_id_mapping: Dict[str, Any],
                payload: TransactionPayload) -> bool:
        """
        Process transaction results and update local layer.
        
        Args:
            layer: QGIS layer to update
            result: TransactionResult from API
            client_id_mapping: Map from clientId to local feature
            payload: Original transaction payload (for error tracking)
            
        Returns:
            True if all operations succeeded
        """
        # Extract layer info for tracking
        layer_name = layer.name() if layer else "Unknown"
        layer_type = self._get_layer_type(layer)
        
        if not result.success and result.error_message:
            self._track_bulk_failure(payload, result.error_message, layer_name, layer_type)
            return False
        
        success = True
        
        # Process insert results - also track missing inserts as failures
        success &= self._process_inserts(layer, result.insert_results, client_id_mapping, payload, layer_name, layer_type)
        
        # Process update results - also track missing updates as failures
        success &= self._process_updates(result.update_results, payload, layer_name, layer_type)
        
        # Process delete results - also track missing deletes as failures
        success &= self._process_deletes(result.delete_results, payload, layer_name, layer_type)
        
        # Log summary
        log_info(
            f"Transaction summary: {result.total_inserted} inserted, "
            f"{result.total_updated} updated, {result.total_deleted} deleted"
        )
        
        return success
    
    def _get_layer_type(self, layer: QgsVectorLayer) -> str:
        """Get layer type from custom property or geometry type"""
        if not layer:
            return "unknown"
        
        bngai_id = layer.customProperty('bngai_id', '')
        try:
            # Extract type from bngai_id like "planId_plan_polygon"
            parts = bngai_id.split('_')
            if len(parts) >= 2:
                return '_'.join(parts[1:])  # e.g., "plan_polygon"
        except (IndexError, AttributeError):
            pass
        
        # Fallback to geometry type
        from qgis.core import QgsWkbTypes
        geom_type = layer.geometryType()
        if geom_type == QgsWkbTypes.PointGeometry:
            return "point"
        elif geom_type == QgsWkbTypes.LineGeometry:
            return "line"
        elif geom_type == QgsWkbTypes.PolygonGeometry:
            return "polygon"
        
        return "unknown"
    
    def _process_inserts(self, layer: QgsVectorLayer,
                         results: List[OperationResult],
                         client_id_mapping: Dict[str, Any],
                         payload: TransactionPayload = None,
                         layer_name: str = "",
                         layer_type: str = "") -> bool:
        """
        Process insert results and update local features with server IDs.
        Also tracks inserts that were sent but not returned as failures.
        
        Args:
            layer: QGIS layer to update
            results: List of insert operation results
            client_id_mapping: Map from clientId to local feature
            payload: Original transaction payload (to detect missing results)
            layer_name: Name of the layer for tracking
            layer_type: Type of the layer for tracking
            
        Returns:
            True if all inserts succeeded
        """
        success = True
        
        # Track which clientIds we got results for
        processed_client_ids = set()
        
        for result in results:
            if result.client_id:
                processed_client_ids.add(result.client_id)
            
            if result.status == SyncStatus.SUCCESS and result.client_id and result.server_id:
                # Update local feature with server ID
                success &= self._update_local_feature(
                    layer, result, client_id_mapping
                )
                
                # Track success
                self._track_operation(
                    operation_type="INSERT",
                    feature_id=result.server_id,
                    success=True,
                    additional_data={
                        "clientId": result.client_id, 
                        "status": "SUCCESS",
                        "layerName": layer_name,
                        "layerType": layer_type
                    }
                )
                
                log_info(f"Insert SUCCESS: clientId={result.client_id} -> serverId={result.server_id}")
            else:
                # Track failure with detailed error info
                error_msg = self._build_error_message(result, "New Habitat")
                log_error(error_msg)
                
                self._track_operation(
                    operation_type="INSERT",
                    feature_id=result.client_id or "unknown",
                    success=False,
                    error_message=error_msg,
                    additional_data={
                        "clientId": result.client_id,
                        "status": str(result.status.value),
                        "errorCode": result.error_code,
                        "errorField": result.error_field,
                        "layerName": layer_name,
                        "layerType": layer_type
                    }
                )
                success = False
        
        # Track inserts that were sent but server returned no results for (silent failures)
        if payload and payload.insert:
            for feature in payload.insert:
                client_id = feature.get('properties', {}).get('clientId')
                if client_id and client_id not in processed_client_ids:
                    error_msg = f"New Habitat FAIL: clientId={client_id} - Server returned no result"
                    log_error(error_msg)
                    
                    self._track_operation(
                        operation_type="INSERT",
                        feature_id=client_id,
                        success=False,
                        error_message="Server returned no result (silent failure)",
                        additional_data={
                            "clientId": client_id,
                            "status": "NO_RESPONSE",
                            "aiDashCode": feature.get('properties', {}).get('planHabitatAidashCode'),
                            "layerName": layer_name,
                            "layerType": layer_type
                        }
                    )
                    success = False
        
        return success
    
    def _process_updates(self, results: List[OperationResult],
                         payload: TransactionPayload = None,
                         layer_name: str = "",
                         layer_type: str = "") -> bool:
        """
        Process update results. Also tracks updates that were sent but not returned as failures.
        
        Args:
            results: List of update operation results
            payload: Original transaction payload (to detect missing results)
            layer_name: Name of the layer for tracking
            layer_type: Type of the layer for tracking
            
        Returns:
            True if all updates succeeded
        """
        success = True
        
        # Track which feature IDs we got results for
        processed_ids = set()
        
        for result in results:
            if result.feature_id:
                processed_ids.add(result.feature_id)
            
            is_success = result.status == SyncStatus.SUCCESS
            
            if is_success:
                log_info(f"Update SUCCESS: id={result.feature_id}")
            else:
                error_msg = self._build_error_message(result, "Update")
                log_error(error_msg)
                success = False
            
            self._track_operation(
                operation_type="UPDATE",
                feature_id=result.feature_id,
                success=is_success,
                error_message=None if is_success else self._build_error_message(result, "Update"),
                additional_data={
                    "status": result.status.value,
                    "errorCode": result.error_code,
                    "errorField": result.error_field,
                    "layerName": layer_name,
                    "layerType": layer_type
                }
            )
        
        # Track updates that were sent but server returned no results for (silent failures)
        if payload and payload.update:
            for feature in payload.update:
                feature_id = feature.get('id')
                if feature_id and feature_id not in processed_ids:
                    error_msg = f"Update FAIL: id={feature_id} - Server returned no result"
                    log_error(error_msg)
                    
                    self._track_operation(
                        operation_type="UPDATE",
                        feature_id=feature_id,
                        success=False,
                        error_message="Server returned no result (silent failure)",
                        additional_data={
                            "status": "NO_RESPONSE",
                            "layerName": layer_name,
                            "layerType": layer_type
                        }
                    )
                    success = False
        
        return success
    
    def _process_deletes(self, results: List[OperationResult],
                         payload: TransactionPayload = None,
                         layer_name: str = "",
                         layer_type: str = "") -> bool:
        """
        Process delete results. Also tracks deletes that were sent but not returned as failures.
        
        Args:
            results: List of delete operation results
            payload: Original transaction payload (to detect missing results)
            layer_name: Name of the layer for tracking
            layer_type: Type of the layer for tracking
            
        Returns:
            True if all deletes succeeded
        """
        success = True
        
        # Track which feature IDs we got results for
        processed_ids = set()
        
        for result in results:
            if result.feature_id:
                processed_ids.add(result.feature_id)
            
            is_success = result.status == SyncStatus.SUCCESS
            
            if is_success:
                log_info(f"Delete SUCCESS: id={result.feature_id}")
            else:
                error_msg = self._build_error_message(result, "Delete")
                log_error(error_msg)
                success = False
            
            self._track_operation(
                operation_type="DELETE",
                feature_id=result.feature_id,
                success=is_success,
                error_message=None if is_success else self._build_error_message(result, "Delete"),
                additional_data={
                    "status": result.status.value,
                    "errorCode": result.error_code,
                    "errorField": result.error_field,
                    "layerName": layer_name,
                    "layerType": layer_type
                }
            )
        
        # Track deletes that were sent but server returned no results for (silent failures)
        if payload and payload.delete:
            for entry in payload.delete:
                feature_id = entry.get('id')
                if feature_id and feature_id not in processed_ids:
                    error_msg = f"Delete FAIL: id={feature_id} - Server returned no result"
                    log_error(error_msg)
                    
                    self._track_operation(
                        operation_type="DELETE",
                        feature_id=feature_id,
                        success=False,
                        error_message="Server returned no result (silent failure)",
                        additional_data={
                            "status": "NO_RESPONSE",
                            "layerName": layer_name,
                            "layerType": layer_type
                        }
                    )
                    success = False
        
        return success
    
    def _update_local_feature(self, layer: QgsVectorLayer,
                               result: OperationResult,
                               client_id_mapping: Dict[str, Any]) -> bool:
        """
        Update local feature with server ID after insert.
        
        Args:
            layer: QGIS layer
            result: Insert operation result
            client_id_mapping: Map from clientId to local feature
            
        Returns:
            True if update succeeded
        """
        local_feature = client_id_mapping.get(result.client_id)
        if not local_feature:
            log_error(f"No local feature found for clientId: {result.client_id}")
            return True  # Not a failure, just no feature to update
        
        try:
            fid = local_feature.id()
            old_id = local_feature.attribute('id')
            log_info(f"Updating feature FID={fid}, old id='{old_id}' -> new id='{result.server_id}'")
            
            layer.startEditing()
            
            # Get fresh feature from layer by FID to ensure we're updating the right one
            fresh_feature = layer.getFeature(fid)
            if not fresh_feature.isValid():
                log_error(f"Could not get fresh feature for FID={fid}")
                layer.rollBack()
                return False
            
            # Update id attribute
            id_field_idx = layer.fields().indexOf('id')
            if id_field_idx >= 0:
                layer.changeAttributeValue(fid, id_field_idx, result.server_id)
                log_info(f"Changed 'id' attribute at field index {id_field_idx}")
            else:
                log_error("'id' field not found in layer")
            
            # Copy server ID to sourceId
            source_id_field_idx = layer.fields().indexOf('sourceId')
            if source_id_field_idx >= 0:
                layer.changeAttributeValue(fid, source_id_field_idx, result.server_id)
                log_info(f"Copied server ID to 'sourceId' at field index {source_id_field_idx}")
            
            # Update activityType from response if available
            if result.properties and result.properties.get('activityType'):
                activity_type_idx = layer.fields().indexOf('activityType')
                if activity_type_idx >= 0:
                    layer.changeAttributeValue(fid, activity_type_idx, result.properties.get('activityType'))
            
            success = layer.commitChanges()
            if success:
                log_info(f"Successfully committed feature update for FID={fid}")
                # Verify the update
                verify_feature = layer.getFeature(fid)
                verify_id = verify_feature.attribute('id')
                log_info(f"Verification: FID={fid} now has id='{verify_id}'")
            else:
                log_error(f"Failed to commit changes: {layer.commitErrors()}")
                layer.rollBack()
                return False
            
            return True
            
        except Exception as e:
            log_error(f"Error updating local feature: {str(e)}")
            if layer.isEditable():
                layer.rollBack()
            return False
    
    def _build_error_message(self, result: OperationResult, operation: str) -> str:
        """Build descriptive error message from status object"""
        msg = f"{operation} FAIL"
        
        if result.client_id:
            msg += f": clientId={result.client_id}"
        if result.feature_id:
            msg += f", id={result.feature_id}"
        
        # Include error details from status object
        if result.error_code:
            msg += f", errorCode={result.error_code}"
        if result.error_field:
            msg += f", field={result.error_field}"
        if result.error_message:
            msg += f", reason={result.error_message}"
        
        return msg
    
    def _track_operation(self, operation_type: str, feature_id: str,
                         success: bool, error_message: Optional[str] = None,
                         additional_data: Optional[Dict] = None) -> None:
        """Track operation in sync tracker"""
        if self.sync_tracker:
            self.sync_tracker.add_operation(
                operation_type=operation_type,
                feature_id=feature_id,
                api_name="wfs_transaction",
                success=success,
                error_message=error_message,
                additional_data=additional_data or {}
            )
    
    def _track_bulk_failure(self, payload: TransactionPayload, error_msg: str,
                            layer_name: str = "", layer_type: str = "") -> None:
        """Track failure when entire bulk operation fails"""
        # Track insert failures
        for feature in payload.insert:
            client_id = feature.get('properties', {}).get('clientId', 'unknown')
            self._track_operation(
                operation_type="INSERT",
                feature_id=client_id,
                success=False,
                error_message=error_msg,
                additional_data={
                    "layerName": layer_name,
                    "layerType": layer_type
                }
            )
        
        # Track update failures
        for feature in payload.update:
            self._track_operation(
                operation_type="UPDATE",
                feature_id=feature.get('id', 'unknown'),
                success=False,
                error_message=error_msg,
                additional_data={
                    "layerName": layer_name,
                    "layerType": layer_type
                }
            )
        
        # Track delete failures
        for entry in payload.delete:
            self._track_operation(
                operation_type="DELETE",
                feature_id=entry.get('id', 'unknown'),
                success=False,
                error_message=error_msg,
                additional_data={
                    "layerName": layer_name,
                    "layerType": layer_type
                }
            )

