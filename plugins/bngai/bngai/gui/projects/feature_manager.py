"""
Feature management functionality for the projects tab.
"""
from qgis.core import (QgsMessageLog, QgsFeature, QgsGeometry)
from qgis.PyQt.QtCore import  QTimer, QObject
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QDialogButtonBox
from ...layers.layer_manager import LayerManager
import json

class FeatureManager(QObject):
    """Manages feature operations for the BNG AI plugin"""
    
    def __init__(self, api_client, layer_manager=None):
        """
        Initialize the FeatureManager.
        
        Args:
            api_client (BngPlanHabitatApi): The API client for habitat data
            layer_manager (LayerManager, optional): The layer manager instance to use.
                                                  If None, a new instance will be created.
        """
        super().__init__()  # Initialize QObject
        self.api_client = api_client
        self.layer_manager = layer_manager if layer_manager is not None else LayerManager()
        
        # Initialize state
        self.current_layer = None
        self.current_feature = None
        self._last_edit_stop = None  # Track last edit stop to prevent duplicates
        self._is_fixing_duplicates = False  # Flag to prevent recursive editing
        self._last_feature_count = {}  # Track feature counts to detect splits/merges
        
        # Connect to layer manager signals
        QgsMessageLog.logMessage("Connecting FeatureManager to LayerManager signals...", "BNGAI Plugin", level=0)
        try:
            self.layer_manager.selection_changed.connect(self._handle_selection_changed)
            self.layer_manager.editing_stopped.connect(self._handle_editing_stopped)
            self.layer_manager.feature_added.connect(self._handle_feature_added)
            QgsMessageLog.logMessage("Successfully connected to LayerManager signals", "BNGAI Plugin", level=0)
        except Exception as e:
            QgsMessageLog.logMessage(f"Error connecting to LayerManager signals: {str(e)}", "BNGAI Plugin", level=2)
            
        # Connect to existing layers only if we created our own LayerManager
        if layer_manager is None:
            self.layer_manager.connect_to_existing_layers()

    def _handle_editing_stopped(self, layer):
        """
        Handle when editing is stopped on a layer.
        Logs the current state of features in the layer and handles duplicate IDs.
        Also sets ID to null for new features and split features.
        
        Args:
            layer (QgsMapLayer): The layer where editing was stopped
        """
        try:
            # Skip if we're in the middle of fixing duplicates
            if self._is_fixing_duplicates:
                QgsMessageLog.logMessage("Skipping duplicate check - already fixing duplicates", "BNGAI Plugin", level=0)
                return
                
            # Get layer identifier
            layer_id = layer.id()
            bngai_id = layer.customProperty('bngai_id', '<no bngai_id>')
            
            # Create unique identifier for this edit stop event
            current_stop = f"{layer_id}_{bngai_id}"
            
            # Check if this is a duplicate signal
            if self._last_edit_stop == current_stop:
                return
                
            self._last_edit_stop = current_stop
            
            QgsMessageLog.logMessage(
                f"Editing stopped in layer: {layer} "
                f"(Layer ID: {layer_id}, BNGAI ID: {bngai_id})", 
                "BNGAI Plugin", level=0
            )
            
            # Only process BNG plan layers
            if bngai_id == '<no bngai_id>':
                QgsMessageLog.logMessage("Not a BNG plan layer, skipping ID checks", "BNGAI Plugin", level=0)
                return
                
            # Get all features and their details
            features = list(layer.getFeatures())
            current_feature_count = len(features)
            
            # Check if this might be a split operation
            last_count = self._last_feature_count.get(layer_id, current_feature_count)
            is_potential_split = current_feature_count > last_count
            
            # Update the feature count for next time
            self._last_feature_count[layer_id] = current_feature_count
            
            # Track IDs and their occurrences
            id_occurrences = {}
            features_by_id = {}
            features_to_update = []
            
            # First pass: count occurrences of each ID and identify features needing updates
            for feature in features:
                if feature.fieldNameIndex('id') >= 0:
                    feature_id = feature.attribute('id')
                    # Handle empty or invalid IDs
                    if not feature_id or str(feature_id).lower() in ['none', 'null', '', '0']:
                        features_to_update.append(feature)
                    elif feature_id:  # Only track non-null IDs
                        if feature_id not in id_occurrences:
                            id_occurrences[feature_id] = []
                        id_occurrences[feature_id].append(feature.id())
                        features_by_id[feature.id()] = feature
            
            # Find duplicate IDs
            duplicate_ids = {id_val: fids for id_val, fids in id_occurrences.items() if len(fids) > 1}
            
            # If we have features to update or duplicates to fix
            if features_to_update or duplicate_ids or is_potential_split:
                QgsMessageLog.logMessage(
                    f"Found {len(features_to_update)} features needing ID update and {len(duplicate_ids)} duplicate IDs", 
                    "BNGAI Plugin", level=0
                )
                
                # Set flag to prevent recursive editing
                self._is_fixing_duplicates = True
                
                try:
                    # Start editing to fix IDs
                    if not layer.isEditable():
                        if not layer.startEditing():
                            QgsMessageLog.logMessage("Failed to start editing layer", "BNGAI Plugin", level=2)
                            self._is_fixing_duplicates = False
                            return
                    
                    # Update features needing ID set to null
                    for feature in features_to_update:
                        if not feature.isValid():
                            continue
                        # Set ID to null
                        feature.setAttribute('id', None)
                        # Update the feature
                        if not layer.updateFeature(feature):
                            QgsMessageLog.logMessage(f"Failed to update feature {feature.id()}", "BNGAI Plugin", level=2)
                            continue
                        QgsMessageLog.logMessage(f"Set ID to null for feature FID {feature.id()}", "BNGAI Plugin", level=0)
                    
                    # For each set of duplicates, keep the first occurrence and null out the rest
                    for id_val, fids in duplicate_ids.items():
                        # Skip first FID (keep original)
                        for fid in fids[1:]:
                            feature = features_by_id[fid]
                            if not feature.isValid():
                                continue
                            # Set ID to null
                            feature.setAttribute('id', None)
                            # Update the feature
                            if not layer.updateFeature(feature):
                                QgsMessageLog.logMessage(f"Failed to update feature {fid}", "BNGAI Plugin", level=2)
                                continue
                            QgsMessageLog.logMessage(f"Nulled ID for feature FID {fid} (was {id_val})", "BNGAI Plugin", level=0)
                    
                    # If this was a split operation, ensure all new features have null IDs
                    if is_potential_split:
                        QgsMessageLog.logMessage(
                            f"Potential split detected (feature count increased from {last_count} to {current_feature_count})", 
                            "BNGAI Plugin", level=0
                        )
                        # Any feature with an ID that appears more than once is likely from a split
                        for id_val, fids in id_occurrences.items():
                            if len(fids) > 1:
                                # Null out all instances as they're all new split features
                                for fid in fids:
                                    feature = features_by_id[fid]
                                    if not feature.isValid():
                                        continue
                                    # Set ID to null
                                    feature.setAttribute('id', None)
                                    # Update the feature
                                    if not layer.updateFeature(feature):
                                        QgsMessageLog.logMessage(f"Failed to update split feature {fid}", "BNGAI Plugin", level=2)
                                        continue
                                    QgsMessageLog.logMessage(f"Nulled ID for split feature FID {fid} (was {id_val})", "BNGAI Plugin", level=0)
            
                    # Commit the changes
                    if layer.commitChanges():
                        QgsMessageLog.logMessage("Successfully fixed feature IDs", "BNGAI Plugin", level=0)
                    else:
                        QgsMessageLog.logMessage(f"Failed to commit changes: {layer.commitErrors()}", "BNGAI Plugin", level=2)
                        layer.rollBack()
                except Exception as e:
                    QgsMessageLog.logMessage(f"Error fixing feature IDs: {str(e)}", "BNGAI Plugin", level=2)
                    if layer.isEditable():
                        layer.rollBack()
                finally:
                    # Always reset the flag, even if an error occurs
                    self._is_fixing_duplicates = False
            
            # Clear the last edit stop after a short delay
            QTimer.singleShot(100, lambda: setattr(self, '_last_edit_stop', None))
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error handling editing stopped: {str(e)}", "BNGAI Plugin", level=2)
            if layer.isEditable():
                layer.rollBack()
            # Make sure to reset the flag on error
            self._is_fixing_duplicates = False
            # Clear the last edit stop
            self._last_edit_stop = None

    def _handle_selection_changed(self):
        """
        Handle when the selection changes in the current layer.
        Updates the current feature and layer state.
        """
        QgsMessageLog.logMessage("Selection changed in layer", "BNGAI Plugin", level=0)
        
        # Get current selection from layer manager
        layer, feature = self.layer_manager.get_current_selection()
        
        # Update current state
        self.current_layer = layer
        self.current_feature = feature
        
        if layer and feature:
            QgsMessageLog.logMessage(f"Selected feature {feature.id()} in layer {layer.name()}", "BNGAI Plugin", level=0)
        else:
            QgsMessageLog.logMessage("No feature selected", "BNGAI Plugin", level=0)

    def _handle_feature_added(self, layer, feature_id):
        """
        Handle when a new feature is added to a layer.
        Sets the ID to null for the new feature.
        
        Args:
            layer (QgsMapLayer): The layer where the feature was added
            feature_id (int): The ID of the added feature
        """
        try:
            QgsMessageLog.logMessage(f"Feature added: {feature_id}", "BNGAI Plugin", level=0)
            # Skip if we're in the middle of fixing duplicates
            if self._is_fixing_duplicates:
                QgsMessageLog.logMessage("Skipping feature added handling - already fixing duplicates", "BNGAI Plugin", level=0)
                return

            # Only process BNG plan layers
            bngai_id = layer.customProperty('bngai_id', '<no bngai_id>')
            if bngai_id == '<no bngai_id>':
                QgsMessageLog.logMessage("Not a BNG plan layer, skipping ID check", "BNGAI Plugin", level=0)
                return

            # Get the feature by ID
            feature = None
            for f in layer.getFeatures():
                if f.id() == feature_id:
                    feature = f
                    break

            if not feature:
                QgsMessageLog.logMessage(f"Could not find feature with ID {feature_id}", "BNGAI Plugin", level=2)
                return

            # Set flag to prevent recursive editing
            self._is_fixing_duplicates = True

            try:
                # Start editing if not already editing
                was_editing = layer.isEditable()
                if not was_editing:
                    if not layer.startEditing():
                        QgsMessageLog.logMessage("Failed to start editing layer", "BNGAI Plugin", level=2)
                        self._is_fixing_duplicates = False
                        return

                # Set ID to null
                feature.setAttribute('id', None)

                # Update the feature
                if not layer.updateFeature(feature):
                    QgsMessageLog.logMessage(f"Failed to update feature {feature_id}", "BNGAI Plugin", level=2)
                    if not was_editing:
                        layer.rollBack()
                    return

                # Commit changes if we started editing
                if not was_editing:
                    if not layer.commitChanges():
                        QgsMessageLog.logMessage(f"Failed to commit changes: {layer.commitErrors()}", "BNGAI Plugin", level=2)
                        layer.rollBack()
                        return

                QgsMessageLog.logMessage(f"Set ID to null for new feature FID {feature_id}", "BNGAI Plugin", level=0)

            finally:
                # Always reset the flag
                self._is_fixing_duplicates = False

        except Exception as e:
            QgsMessageLog.logMessage(f"Error handling feature added: {str(e)}", "BNGAI Plugin", level=2)
            if layer.isEditable():
                layer.rollBack()
            self._is_fixing_duplicates = False

    def cleanup(self):
        """Clean up resources and disconnect signals."""
        try:
            self.layer_manager.selection_changed.disconnect(self._handle_selection_changed)
            self.layer_manager.editing_stopped.disconnect(self._handle_editing_stopped)
            self.layer_manager.feature_added.disconnect(self._handle_feature_added)
        except:
            pass

    def merge_selected_features(self, layer):
        """
        Merge selected features in the layer into a single feature.
        
        Args:
            layer (QgsVectorLayer): The layer containing selected features
            
        Returns:
            tuple: (success: bool, merged_feature: QgsFeature or None, message: str)
        """
        try:
            if not layer or not layer.isValid():
                return False, None, "Invalid layer"
                
            selected_features = list(layer.selectedFeatures())
            if len(selected_features) < 2:
                return False, None, "Select at least 2 features to merge"
                
            # Show dialog to select which feature's attributes to keep
            dialog = AttributeSelectionDialog(selected_features)
            if not dialog.exec_():
                return False, None, "Merge cancelled"
                
            source_feature = dialog.get_selected_feature()
            if not source_feature:
                return False, None, "No source feature selected"
                
            # Start editing
            if not layer.isEditable():
                layer.startEditing()
                
            # Create merged geometry
            merged_geometry = None
            for feature in selected_features:
                if merged_geometry is None:
                    merged_geometry = feature.geometry()
                else:
                    merged_geometry = merged_geometry.combine(feature.geometry())
                    
            if not merged_geometry or not merged_geometry.isGeosValid():
                return False, None, "Failed to create valid merged geometry"
                
            # Create new feature with source feature's attributes
            merged_feature = QgsFeature(layer.fields())
            merged_feature.setGeometry(merged_geometry)
            
            # Copy attributes from source feature
            for field in layer.fields():
                merged_feature[field.name()] = source_feature[field.name()]
                
            # Generate new ID for merged feature
            merged_feature['id'] = None  # Clear ID to get new one from server
            
            # Collect all IDs to be merged, including existing mergedIds
            merged_ids = set()  # Use set to avoid duplicates
            for feature in selected_features:
                # Add the feature's own ID if it exists
                feature_id = feature.attribute('id')
                if feature_id and str(feature_id).lower() not in ['none', 'null', '']:
                    merged_ids.add(feature_id)
                
                # Add any existing merged IDs
                existing_merged = feature.attribute('mergedIds')
                if existing_merged and str(existing_merged).lower() not in ['none', 'null', '']:
                    # Split existing comma-separated IDs and add them
                    merged_ids.update([id.strip() for id in existing_merged.split(',') if id.strip()])
            
            # Store merged IDs as comma-separated string
            if merged_ids:
                merged_feature['mergedIds'] = ','.join(sorted(merged_ids))  # Sort for consistency
                
            # Add merged feature and delete old features
            layer.addFeature(merged_feature)
            layer.deleteSelectedFeatures()
            
            # Commit changes
            if layer.commitChanges():
                # Select the new feature
                layer.selectByIds([merged_feature.id()])
                return True, merged_feature, "Successfully merged features"
            else:
                layer.rollBack()
                return False, None, "Failed to commit changes"
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error merging features: {str(e)}", "BNGAI Plugin", level=2)
            if layer.isEditable():
                layer.rollBack()
            return False, None, f"Error merging features: {str(e)}"

class AttributeSelectionDialog(QDialog):
    """Dialog for selecting which feature's attributes to keep after merge"""
    def __init__(self, features, parent=None):
        super(AttributeSelectionDialog, self).__init__(parent)
        self.features = features
        self.selected_feature = None
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI"""
        self.setWindowTitle("Select Source Feature")
        layout = QVBoxLayout(self)
        
        # Add explanation label
        label = QLabel("Select which feature's attributes to keep:")
        layout.addWidget(label)
        
        # Create combo box for feature selection
        self.combo = QComboBox()
        for i, feature in enumerate(self.features):
            # Try to get meaningful attributes to display
            feature_desc = f"Feature {i+1}"
            if feature.fieldNameIndex("aiDashCode") >= 0:
                code = feature.attribute("aiDashCode")
                if code:
                    feature_desc += f" (Code: {code})"
            if feature.fieldNameIndex("aiDashLabel") >= 0:
                label = feature.attribute("aiDashLabel")
                if label:
                    feature_desc += f" - {label}"
            self.combo.addItem(feature_desc, i)
        layout.addWidget(self.combo)
        
        # Add OK/Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_selected_feature(self):
        """Get the selected feature"""
        selected_index = self.combo.currentData()
        return self.features[selected_index] if selected_index is not None else None 