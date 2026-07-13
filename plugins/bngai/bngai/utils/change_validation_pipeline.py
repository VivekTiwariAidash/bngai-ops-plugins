"""
ChangeValidationPipeline - Validates pending changes (NEW and UPDATED features) before sync.

Uses FeatureValidator from validation_utils for actual validation logic.
Uses RLBSpatialValidator for checking features are within Red Line Boundary.
Handles UI confirmation dialog and BLOCKS sync if any validation fails.
No partial sync allowed - user must fix all errors before syncing.
"""
from typing import Dict, List, Tuple, Any
from qgis.core import QgsMessageLog
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox, QTextBrowser
from qgis.PyQt.QtCore import Qt

from .validation_utils import (
    FeatureValidator,
    LayerValidationResult,
    create_validation_html_summary
)
from .rlb_spatial_validator import (
    RLBSpatialValidator,
    LayerSpatialValidationResult,
    create_spatial_validation_html
)


class ChangeValidationPipeline:
    """
    Validates changes before sync and shows confirmation dialog.
    
    Validates NEW and UPDATED features:
    - If ANY validation fails (attribute or spatial), sync is BLOCKED.
    - No partial sync allowed - user must fix all errors before syncing.
    
    Also validates that features are within the Red Line Boundary (RLB).
    """
    
    def __init__(self):
        self.validator = FeatureValidator()
        self.spatial_validator = RLBSpatialValidator()

    def validate_changes_and_confirm(
        self, 
        _layers: List[Any],  # Kept for backward compatibility
        all_changes: Dict[str, Dict]
    ) -> Tuple[bool, Dict[str, Dict], str]:
        """
        Validate all changes (NEW and UPDATED features) and get user confirmation.
        
        Performs both:
        1. Attribute validation (required fields, valid values)
        2. Spatial validation (features within RLB)
        
        If ANY validation fails, sync is BLOCKED - no partial sync allowed.
        
        Args:
            layers: List of QgsVectorLayer objects
            all_changes: Dict mapping layer_id to {'layer': layer, 'changes': {...}}
                        where changes has 'new', 'updated', 'deleted' lists
        
        Returns:
            Tuple of (proceed, all_changes, html_summary)
            - proceed: True if sync should continue (all valid)
            - all_changes: Original changes dict (unchanged since no partial sync)
            - html_summary: HTML string summarizing validation results
        """
        layer_results: List[LayerValidationResult] = []
        spatial_results: List[LayerSpatialValidationResult] = []
        any_attribute_invalid = False
        any_spatial_invalid = False
        
        # Reset spatial validator cache
        self.spatial_validator.reset()

        for layer_id, bundle in all_changes.items():
            layer = bundle['layer']
            changes = bundle['changes']
            layer_type = self.validator.get_layer_type(layer)
            
            # Validate changes for this layer (attribute validation)
            result = self._validate_layer_changes(layer, layer_type, changes)
            layer_results.append(result)
            
            if result.invalid_features > 0:
                any_attribute_invalid = True
            
            # Spatial validation (check features within RLB)
            spatial_result = self._validate_spatial(layer, changes)
            if spatial_result and spatial_result.features_outside_rlb > 0:
                spatial_results.append(spatial_result)
                any_spatial_invalid = True

        # If all valid (both attribute and spatial), proceed without dialog
        if not any_attribute_invalid and not any_spatial_invalid:
            html = self._create_success_html(layer_results)
            return True, all_changes, html

        # Show error dialog - sync is BLOCKED
        return self._show_validation_error_dialog(
            layer_results, spatial_results, all_changes,
            any_attribute_invalid, any_spatial_invalid
        )
    
    def _validate_spatial(self, layer, changes: Dict) -> LayerSpatialValidationResult:
        """
        Validate that new and updated features are within the RLB.
        
        Args:
            layer: QgsVectorLayer
            changes: Dict with 'new', 'updated', 'deleted' lists
            
        Returns:
            LayerSpatialValidationResult
        """
        result = LayerSpatialValidationResult(layer_name=layer.name())
        
        # Collect feature IDs to validate (new and updated)
        features_to_validate = []
        
        # Add new features
        for item in (changes.get('new') or []):
            fid_str = str(item.get('id') or "")
            if fid_str.startswith("local_"):
                try:
                    fid = int(fid_str.split("_", 1)[1])
                    feature = layer.getFeature(fid)
                    if feature and feature.isValid():
                        client_id = None
                        try:
                            client_id = feature.attribute('clientId')
                        except Exception:
                            pass
                        features_to_validate.append((feature, fid_str, client_id))
                except Exception as e:
                    QgsMessageLog.logMessage(
                        f"Error getting feature {fid_str}: {e}", "BNGAI Plugin", level=1
                    )
        
        # Add updated features
        for item in (changes.get('updated') or []):
            feature_id = item.get('id')
            if feature_id:
                # Find feature by ID attribute
                for feature in layer.getFeatures():
                    if str(feature.attribute('id')) == str(feature_id):
                        client_id = None
                        try:
                            client_id = feature.attribute('clientId')
                        except Exception:
                            pass
                        features_to_validate.append((feature, feature_id, client_id))
                        break
        
        # Validate each feature
        for feature, feature_id, client_id in features_to_validate:
            validation = self.spatial_validator.validate_feature(feature, feature_id, client_id)
            result.add_result(validation)
        
        return result
    
    def _create_success_html(self, layer_results: List[LayerValidationResult]) -> str:
        """Create HTML for successful validation."""
        return create_validation_html_summary(
            layer_results,
            title="Pre-Sync Validation",
            note="All habitats validated successfully. Proceeding with sync..."
        )
    
    def _create_combined_validation_html(
        self, 
        layer_results: List[LayerValidationResult],
        spatial_results: List[LayerSpatialValidationResult],
        has_attribute_errors: bool,
        has_spatial_errors: bool
    ) -> str:
        """Create combined HTML for both attribute and spatial validation."""
        
        html = ""
        
        # Add attribute validation results if there are errors
        if has_attribute_errors:
            html += create_validation_html_summary(
                layer_results,
                title="Attribute Validation Errors",
                note=""
            )
        
        # Add spatial validation results if any
        if has_spatial_errors:
            html += create_spatial_validation_html(
                spatial_results,
                title="Features Outside Red Line Boundary"
            )
        
        return html

    def _validate_layer_changes(
        self, 
        layer, 
        layer_type: str, 
        changes: Dict
    ) -> LayerValidationResult:
        """
        Validate changes for a single layer.
        
        Args:
            layer: QgsVectorLayer
            layer_type: 'point', 'line', or 'polygon'
            changes: Dict with 'new', 'updated', 'deleted' lists
            
        Returns:
            LayerValidationResult
        """
        result = LayerValidationResult(layer_name=layer.name())
        
        # Validate UPDATED features
        for item in (changes.get('updated') or []):
            feature_id = item.get('id')
            validation = self.validator.validate_feature_by_id(layer, layer_type, feature_id)
            result.add_result(validation)
        
        # Validate NEW features
        for item in (changes.get('new') or []):
            validation, _ = self._validate_new_item(layer, layer_type, item)
            result.add_result(validation)
        
        return result

    def _validate_new_item(
        self, 
        layer, 
        layer_type: str, 
        item: Dict
    ) -> Tuple[Any, Any]:
        """
        Validate a NEW feature item.
        
        Tries to get feature from:
        1. item['data']['feature'] - embedded feature reference
        2. layer.getFeature(fid) - resolved from 'local_<fid>' id
        
        Args:
            layer: QgsVectorLayer
            layer_type: 'point', 'line', or 'polygon'
            item: Dict with 'id' and optionally 'data.feature'
            
        Returns:
            Tuple of (FeatureValidationResult, QgsFeature or None)
        """
        # Try to get embedded feature reference
        feature = None
        try:
            data = item.get('data') or {}
            feature = data.get('feature')
        except Exception:
            pass
        
        # If no embedded feature, try to resolve from layer by FID
        if feature is None:
            fid_str = str(item.get('id') or "")
            if fid_str.startswith("local_"):
                try:
                    fid = int(fid_str.split("_", 1)[1])
                    validation, feature = self.validator.validate_feature_by_fid(
                        layer, layer_type, fid
                    )
                    return validation, feature
                except Exception as e:
                    QgsMessageLog.logMessage(
                        f"Failed to resolve feature {fid_str}: {str(e)}", 
                        "BNGAI Plugin", level=1
                    )
        
        # Validate the feature we have (or report missing)
        if feature:
            validation = self.validator.validate_feature(feature, layer_type)
            # Use original item id for reporting
            validation.feature_id = str(item.get('id'))
            return validation, feature
        
        # Feature not found
        from .validation_utils import FeatureValidationResult, ValidationError
        return FeatureValidationResult(
            feature_id=str(item.get('id')),
            is_valid=False,
            errors=[ValidationError(
                feature_id=str(item.get('id')),
                field_name='feature',
                error_type='missing'
            )]
        ), None

    def _show_validation_error_dialog(
        self, 
        layer_results: List[LayerValidationResult],
        spatial_results: List[LayerSpatialValidationResult],
        all_changes: Dict[str, Dict],
        has_attribute_errors: bool,
        has_spatial_errors: bool
    ) -> Tuple[bool, Dict[str, Dict], str]:
        """
        Show validation error dialog. Sync is BLOCKED if any validation fails.
        No partial sync allowed - user must fix all errors before syncing.
        
        Args:
            layer_results: Attribute validation results per layer
            spatial_results: Spatial validation results per layer
            all_changes: Original changes dict (returned unchanged)
            has_attribute_errors: True if there are attribute validation errors
            has_spatial_errors: True if there are features outside RLB
            
        Returns:
            Tuple of (proceed=False, all_changes, html_summary)
        """
        # Build error summary header
        html = """
        <div style='padding: 10px; margin-bottom: 15px; background: #ffebee; 
             border-radius: 5px; border-left: 4px solid #C62828;'>
            <h2 style='color: #C62828; margin: 0;'>Validation Failed - Sync Blocked</h2>
            <p style='margin: 5px 0 0 0; color: #666;'>
                Please fix all validation errors before syncing.
            </p>
        </div>
        """
        
        # Add attribute validation results
        if has_attribute_errors:
            html += create_validation_html_summary(
                layer_results,
                title="Attribute Validation Errors",
                note=""
            )
        
        # Add spatial errors section
        if has_spatial_errors:
            html += create_spatial_validation_html(
                spatial_results,
                title="Features Outside Red Line Boundary"
            )
        
        # Add instructions
        html += """
        <div style='margin-top: 15px; padding: 10px; background: #fff3e0; border-radius: 5px;'>
            <p style='margin: 0; color: #E65100;'>
                <strong>To fix:</strong><br>
                - For attribute errors: Edit features and fill in required fields<br>
                - For spatial errors: Move or delete features outside the Red Line Boundary
            </p>
        </div>
        """
        
        dlg = QDialog()
        dlg.setWindowTitle("Validation Failed - Cannot Sync")
        dlg.resize(900, 650)
        
        layout = QVBoxLayout(dlg)
        
        browser = QTextBrowser()
        browser.setHtml(html)
        layout.addWidget(browser)
        
        buttons = QDialogButtonBox(Qt.Horizontal)
        buttons.addButton("OK - I'll Fix the Errors", QDialogButtonBox.AcceptRole)
        buttons.accepted.connect(dlg.accept)
        layout.addWidget(buttons)
        
        dlg.exec_()
        
        # Always return False - sync is blocked
        return False, all_changes, html
