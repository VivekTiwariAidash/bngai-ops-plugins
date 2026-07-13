"""
HabitatSyncManager - Orchestrates synchronization of habitat features.

This is a Facade that coordinates the sync process using specialized components:
- FeatureComparer: Compares local and server features
- TransactionBuilder: Builds WFS transaction payloads
- TransactionProcessor: Processes transaction results

Single Responsibility: Orchestration only - delegates to specialized components.
Open/Closed: New operations can be added without modifying this class.
Dependency Inversion: Depends on abstractions (components), not concrete implementations.
"""
from typing import List, Tuple, Dict, Optional
import os
import json
import traceback

from qgis.core import QgsVectorLayer
from PyQt5.QtCore import QObject, pyqtSignal

from .models import SyncResult, TransactionResult
from .feature_comparer import FeatureComparer
from .transaction_builder import TransactionBuilder
from .transaction_processor import TransactionProcessor
from .utils import log_info, log_error

from ....utils.sync_tracker import SyncTracker
from ....utils.validation_utils import (
    FeatureValidator, 
    LayerValidationResult, 
    create_validation_html_summary
)
from ....utils.change_validation_pipeline import ChangeValidationPipeline
from ....utils.plan_spatial_validation import PlanSpatialValidator


class HabitatSyncManager(QObject):
    """
    Orchestrates synchronization of habitat data between QGIS and the BNG API.
    
    This class acts as a Facade, providing a simple interface while coordinating
    multiple specialized components behind the scenes.
    
    Usage:
        manager = HabitatSyncManager(api_client)
        result = manager.sync_habitats(layers, plan_id, org_id)
    """
    
    # Signal emitted when sync state changes
    state_changed = pyqtSignal()
    
    def __init__(self, api_client):
        """
        Initialize the sync manager with required dependencies.
        
        Args:
            api_client: API client for server communication
        """
        super().__init__()
        
        self.api_client = api_client
        self.auth_manager = api_client.auth_manager if api_client else None
        
        # Initialize components
        self.sync_tracker = SyncTracker()
        self.comparer = FeatureComparer(api_client)
        self.builder = TransactionBuilder()
        self.processor = TransactionProcessor(self.sync_tracker)
    
    def sync_habitats(self, layers: List[QgsVectorLayer], 
                      bng_plan_id: str, org_id: str) -> Tuple[bool, str, str, str]:
        """
        Synchronize local layers with server data.
        
        This is the main entry point for sync operations. It:
        1. Validates features
        2. Compares with server data
        3. Executes bulk transaction
        4. Returns results
        
        Args:
            layers: List of QGIS layers to sync
            bng_plan_id: BNG Plan ID
            org_id: Organization ID
            
        Returns:
            Tuple of (success, message, html_summary, csv_path)
        """
        self.sync_tracker.reset()
        
        try:
            # Step 1: Validate features
            validation_result = self._validate_layers(layers)
            if validation_result:
                return validation_result
            
            # Step 2: Fetch server features
            server_features, error = self.comparer.get_server_features(bng_plan_id, org_id)
            if error:
                return False, error, "", ""
            
            # Step 3: Compare and collect changes for all layers
            all_changes, total_count = self._collect_all_changes(layers, server_features)
            
            # Step 4: Handle no changes case
            if total_count == 0:
                result = SyncResult.no_changes()
                return result.success, result.message, result.html_summary, ""
            
            # Step 5: Spatial validation
            spatial_result = self._validate_spatial(all_changes)
            if spatial_result:
                return spatial_result
            
            # Step 6: User confirmation and filtering
            all_changes, validation_snippet = self._confirm_changes(layers, all_changes)
            if all_changes is None:
                return False, "Sync cancelled by user", validation_snippet, ""
            
            # Step 7: Process changes for each layer
            overall_success = self._process_all_layers(all_changes, bng_plan_id, org_id)
            
            # Step 8: Refresh synced features from server to get updated attributes
            if overall_success:
                self._refresh_synced_features(all_changes, bng_plan_id, org_id)
            
            # Step 9: Generate results
            return self._generate_results(all_changes, overall_success, validation_snippet)
            
        except Exception as e:
            error_msg = f"Error during sync: {str(e)}\n{traceback.format_exc()}"
            log_error(error_msg)
            return False, error_msg, "", ""
    
    def _validate_layers(self, layers: List[QgsVectorLayer]) -> Optional[Tuple[bool, str, str, str]]:
        """
        Validate all features in layers.
        
        Returns:
            Tuple result if validation fails, None if validation passes
        """
        validator = FeatureValidator()
        layer_results = []
        has_errors = False
        
        for layer in layers:
            if not layer or not layer.isValid():
                continue
            
            layer_type = validator.get_layer_type(layer)
            if not layer_type:
                continue
            
            # Create result for this layer
            result = LayerValidationResult(layer_name=layer.name())
            
            # Validate each feature
            for feature in layer.getFeatures():
                validation = validator.validate_feature(feature, layer_type)
                result.add_result(validation)
            
            layer_results.append(result)
            
            if result.invalid_features > 0:
                has_errors = True
        
        if has_errors:
            html = create_validation_html_summary(
                layer_results,
                title="Validation Errors",
                note="Please fix the errors below before syncing."
            )
            return False, "Validation errors found", html, ""
        
        return None
    
    def _collect_all_changes(self, layers: List[QgsVectorLayer], 
                             server_features: Dict) -> Tuple[Dict, int]:
        """
        Collect changes from all layers.
        
        Returns:
            Tuple of (all_changes dict, total change count)
        """
        all_changes = {}
        total_count = 0
        
        for layer in layers:
            if not layer or not layer.isValid():
                continue
            
            # Compare layer with server data
            changes = self.comparer.compare_layer(layer, server_features)
            
            # Store changes
            all_changes[layer.id()] = {
                'layer': layer,
                'changes': changes,
                'legacy_changes': changes.to_legacy_format()  # For backward compatibility
            }
            
            total_count += changes.total_count
            
            # Log changes
            log_info(f"Layer {layer.name()}: {len(changes.inserts)} new, "
                    f"{len(changes.updates)} updated, {len(changes.deletes)} deleted")
        
        return all_changes, total_count
    
    def _validate_spatial(self, all_changes: Dict) -> Optional[Tuple[bool, str, str, str]]:
        """
        Run spatial validation on changes.
        
        Returns:
            Tuple result if validation fails, None if passes
        """
        try:
            validator = PlanSpatialValidator()
            # Convert to legacy format for validator
            legacy_changes = {
                lid: {'layer': data['layer'], 'changes': data['legacy_changes']}
                for lid, data in all_changes.items()
            }
            ok, html = validator.validate_overlaps_only(legacy_changes)
            if not ok:
                return False, "Spatial validation failed", html, ""
        except Exception:
            pass  # Fail-safe: continue if validation errors
        
        return None
    
    def _confirm_changes(self, layers: List[QgsVectorLayer], 
                         all_changes: Dict) -> Tuple[Optional[Dict], str]:
        """
        Get user confirmation for changes.
        
        Returns:
            Tuple of (filtered_changes or None if cancelled, validation_snippet)
        """
        try:
            pipeline = ChangeValidationPipeline()
            # Convert to legacy format
            legacy_changes = {
                lid: {'layer': data['layer'], 'changes': data['legacy_changes']}
                for lid, data in all_changes.items()
            }
            
            proceed, filtered, snippet = pipeline.validate_changes_and_confirm(
                [data['layer'] for data in all_changes.values()],
                legacy_changes
            )
            
            if not proceed:
                return None, snippet
            
            # Update all_changes with filtered data
            for lid, data in all_changes.items():
                if lid in filtered:
                    data['legacy_changes'] = filtered[lid]['changes']
            
            return all_changes, snippet
            
        except Exception:
            return all_changes, ""
    
    def _process_all_layers(self, all_changes: Dict, 
                            bng_plan_id: str, org_id: str) -> bool:
        """
        Process changes for all layers using bulk transaction.
        
        Returns:
            True if all operations succeeded
        """
        overall_success = True
        
        for data in all_changes.values():
            layer = data['layer']
            legacy_changes = data['legacy_changes']
            
            success = self._process_layer_changes(layer, legacy_changes, bng_plan_id, org_id)
            if not success:
                overall_success = False
        
        return overall_success
    
    def _process_layer_changes(self, layer: QgsVectorLayer, 
                               changes: Dict, bng_plan_id: str, org_id: str) -> bool:
        """
        Process changes for a single layer.
        
        Args:
            layer: QGIS layer
            changes: Legacy format changes dict
            bng_plan_id: Plan ID
            org_id: Organization ID
            
        Returns:
            True if successful
        """
        # Build transaction payload
        payload = self.builder.build_from_legacy_changes(changes)
        
        if payload.is_empty:
            log_info("No changes to process")
            return True
        
        log_info(f"Processing: {payload.summary}")
        
        # Log the payload for debugging
        log_info(f"WFS Transaction Payload: {json.dumps(payload.to_dict(), indent=2)}")
        
        # Execute transaction
        response = self.api_client.wfs_transaction(
            plan_id=bng_plan_id,
            org_id=org_id,
            insert=payload.insert,
            update=payload.update,
            delete=payload.delete
        )
        
        # Parse response
        result = TransactionResult.from_api_response(response)
        
        if not response:
            log_error("WFS transaction failed - no response")
            self.processor._track_bulk_failure(payload, "Transaction failed")
            return False
        
        # Process results
        return self.processor.process(
            layer, result, self.builder.client_id_mapping, payload
        )
    
    def _generate_results(self, all_changes: Dict, success: bool, 
                          validation_snippet: str) -> Tuple[bool, str, str, str]:
        """
        Generate final sync results.
        
        Returns:
            Tuple of (success, message, html_summary, csv_path)
        """
        # Create summary message
        summary = self._create_summary(all_changes)
        
        # Get HTML summary and export CSV
        html_summary = self.sync_tracker.get_html_summary()
        
        if validation_snippet:
            html_summary += validation_snippet
        
        output_dir = os.path.join(os.path.expanduser('~'), 'BNGAISync')
        csv_path = self.sync_tracker.export_to_csv(output_dir)
        
        return success, summary, html_summary, csv_path
    
    def _create_summary(self, all_changes: Dict) -> str:
        """Create human-readable summary of changes"""
        total_new = 0
        total_updated = 0
        total_deleted = 0
        layer_summaries = []
        
        for data in all_changes.values():
            layer = data['layer']
            changes = data['legacy_changes']
            
            new_count = len(changes.get('new', []))
            updated_count = len(changes.get('updated', []))
            deleted_count = len(changes.get('deleted', []))
            
            total_new += new_count
            total_updated += updated_count
            total_deleted += deleted_count
            
            layer_summaries.append(
                f"{layer.name()}: {new_count} new, {updated_count} updated, {deleted_count} deleted"
            )
        
        summary = "Changes Summary:\n"
        summary += f"Total: {total_new} new, {total_updated} updated, {total_deleted} deleted\n\n"
        summary += "By Layer:\n" + "\n".join(layer_summaries)
        
        return summary
    
    def _get_feature_type(self, layer: QgsVectorLayer) -> Optional[str]:
        """Get feature type from layer custom property"""
        bngai_id = layer.customProperty('bngai_id', '')
        try:
            return bngai_id.split('_')[2]
        except (IndexError, AttributeError):
            return None
    
    def _refresh_synced_features(self, all_changes: Dict, bng_plan_id: str, org_id: str) -> None:
        """
        Refresh local features with updated values from server after successful sync.
        
        This ensures all attributes (including server-calculated ones like distinctiveness)
        are updated from the server response - similar to initial layer load.
        Only features that were successfully synced are refreshed.
        
        Args:
            all_changes: Dict of all changes by layer
            bng_plan_id: BNG Plan ID
            org_id: Organization ID
        """
        try:
            log_info("Refreshing synced features from server...")
            
            # Collect IDs of successfully synced features from sync tracker
            synced_ids = self._get_successfully_synced_ids()
            if not synced_ids:
                log_info("No successfully synced features to refresh")
                return
            
            log_info(f"Will refresh {len(synced_ids)} successfully synced features")
            
            # Fetch fresh features from server
            server_features, error = self.comparer.get_server_features(bng_plan_id, org_id)
            if error or not server_features:
                log_error(f"Failed to refresh features from server: {error}")
                return
            
            # Build server feature lookup by ID
            # server_features is a dict keyed by feature_id already
            server_lookup = {}
            for feature_id, feature_data in server_features.items():
                # feature_data has 'id', 'geometry', 'data' structure
                # We need to restructure it to have 'properties' for the update method
                server_lookup[feature_id] = {
                    'properties': feature_data.get('data', {})
                }
            
            log_info(f"Fetched {len(server_lookup)} server features for refresh")
            
            # Update each layer with only successfully synced features
            for data in all_changes.values():
                layer = data['layer']
                self._update_layer_from_server(layer, server_lookup, synced_ids)
            
            # Refresh layer views
            for data in all_changes.values():
                layer = data['layer']
                if layer and layer.isValid():
                    layer.triggerRepaint()
                
        except Exception as e:
            log_error(f"Error refreshing synced features: {str(e)}")
            log_error(traceback.format_exc())
    
    def _get_successfully_synced_ids(self) -> set:
        """
        Get IDs of features that were successfully synced.
        
        Returns:
            Set of feature IDs that were successfully inserted or updated
        """
        return {
            op.get('feature_id')
            for op in self.sync_tracker.operations
            if op.get('success') and op.get('feature_id') and op.get('feature_id') != 'unknown'
        }
    
    # Map server property keys to local field names
    # This mirrors how features are loaded initially
    # Some fields have multiple possible server keys (list of alternatives)
    SERVER_TO_LOCAL_MAPPING = {
        'condition': ['conditionCode', 'condition'],
        'distinctiveness': ['distinctiveness'],
        'strategicSignificance': ['strategicSignificanceCode', 'strategicSignificance'],
        'treeSize': ['treeSizeCode', 'treeSize'],
        'riparianEncroachment': ['riparianEncroachmentCode', 'riparianEncroachment'],
        'watercourseEncroachment': ['watercourseEncroachmentCode', 'watercourseEncroachment'],
        'activityType': ['activityType'],
        'aiDashCode': ['planHabitatAidashCode', 'aiDashCode'],
        'referenceId': ['referenceId', 'habitatReferenceId', 'habitatReferenceID'],
        'area': ['area'],
    }
    
    def _update_layer_from_server(self, layer: QgsVectorLayer, server_lookup: Dict,
                                    synced_ids: set = None) -> None:
        """
        Update layer features with values from server response.
        Similar to initial layer load - updates all relevant attributes.
        
        Args:
            layer: QGIS layer to update
            server_lookup: Dict mapping feature ID to server feature data
            synced_ids: Optional set of feature IDs that were successfully synced
                       If None, updates all features found in server_lookup
        """
        if not layer or not layer.isValid():
            return
        
        field_names = {f.name() for f in layer.fields()}
        updated_count = 0
        features_updated = 0
        layer.startEditing()
        
        try:
            for feature in layer.getFeatures():
                feature_id = feature.attribute('id')
                if not self._should_update_feature(feature_id, server_lookup, synced_ids):
                    continue
                
                server_props = server_lookup[feature_id].get('properties', {})
                attr_updates = self._update_feature_attributes(
                    layer, feature, server_props, field_names
                )
                updated_count += attr_updates
                if attr_updates > 0:
                    features_updated += 1
            
            layer.commitChanges()
            if features_updated > 0:
                log_info(f"Refreshed {features_updated} feature(s) ({updated_count} attribute(s)) in layer '{layer.name()}'")
                
        except Exception as e:
            layer.rollBack()
            log_error(f"Error updating layer '{layer.name()}' from server: {str(e)}")
    
    def _should_update_feature(self, feature_id: str, server_lookup: Dict, 
                                synced_ids: set = None) -> bool:
        """Check if feature should be updated from server."""
        if not feature_id or feature_id not in server_lookup:
            return False
        if synced_ids and feature_id not in synced_ids:
            return False
        return True
    
    def _update_feature_attributes(self, layer: QgsVectorLayer, feature, 
                                    server_props: Dict, field_names: set) -> int:
        """Update a single feature's attributes from server. Returns count of updates."""
        update_count = 0
        feature_id = feature.attribute('id')
        
        # Debug: log server props for this feature
        log_info(f"Refresh feature '{feature_id}': server_props keys = {list(server_props.keys())}")
        
        for local_field, server_keys in self.SERVER_TO_LOCAL_MAPPING.items():
            if local_field not in field_names:
                continue
            
            # Try each possible server key until we find a value
            server_value = None
            used_key = None
            for server_key in server_keys:
                server_value = server_props.get(server_key)
                if server_value is not None:
                    used_key = server_key
                    break
            
            if server_value is None:
                continue
            
            # Normalize aiDashCode
            if used_key == 'planHabitatAidashCode':
                server_value = str(server_value).strip().lower()
            
            field_idx = layer.fields().indexOf(local_field)
            current_value = feature.attribute(local_field)
            if field_idx >= 0 and current_value != server_value:
                layer.changeAttributeValue(feature.id(), field_idx, server_value)
                log_info(f"  Updated '{local_field}': '{current_value}' -> '{server_value}' (from key '{used_key}')")
                update_count += 1
        
        return update_count
    
    def get_sync_results(self) -> Tuple[str, str]:
        """
        Get sync results summary and CSV file path.
        
        Returns:
            Tuple of (html_summary, csv_path)
        """
        html_summary = self.sync_tracker.get_html_summary()
        output_dir = os.path.join(os.path.expanduser('~'), 'BNGAISync')
        csv_path = self.sync_tracker.export_to_csv(output_dir)
        return html_summary, csv_path

