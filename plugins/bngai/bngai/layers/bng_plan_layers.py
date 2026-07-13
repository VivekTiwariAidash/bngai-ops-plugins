"""
BNGPlanLayersManager - Module for managing BNG Plan layers (trees, watercourse/hedgerow, plan) in QGIS
"""
from qgis.core import (QgsProject, 
                      QgsMessageLog, QgsField,
                      QgsEditorWidgetSetup, QgsWkbTypes)
from qgis.PyQt.QtCore import QVariant
import os
import uuid
from .layer_manager import LayerManager
from ..utils.habitat_mappings import (CONDITION_MAP, STRATEGIC_SIGNIFICANCE_MAP,
                                    WATERCOURSE_ENCROACHMENT_MAP, RIPARIAN_ENCROACHMENT_MAP,
                                    TREE_SIZE_MAP, TREE_AIDASHCODE_MAP, 
                                    PLANAR_AIDASHCODE_MAP, WATERCOURSE_HEDGEROW_AIDASHCODE_MAP,
                                    AIDASH_CODE_TO_NAME)

class BNGPlanLayersManager:
    """
    Manages BNG Plan layers within QGIS for the BNG AI plugin.
    BNG Plan layers include trees, watercourse/hedgerow, and plan layers with biodiversity attributes.
    """
    
    def __init__(self):
        """Initialize the BNG plan layers manager"""
        self.layer_manager = LayerManager()
        # Connect to existing layers to track selection
        self.layer_manager.connect_to_existing_layers()
        QgsMessageLog.logMessage("Initialized BNGPlanLayers", "BNGAI Plugin", level=0)
        self.project = QgsProject.instance()
        self.root = self.project.layerTreeRoot()
        self.bng_plan_group = None
        
        # Ensure the BNG Plan Layers group exists
        self._ensure_bng_plan_group()
        
        # Define standard attributes for different layer types
        self.tree_attributes = [
            ('id', QVariant.String),
            ('clientId', QVariant.String),  # Unique UUID generated on feature creation (readonly)
            ('referenceId', QVariant.String),
            ('sourceId', QVariant.String),
            ('treeSize', QVariant.String),
            ('activityType', QVariant.String),
            ('aiDashCode', QVariant.String),
            ('aiDashLabel', QVariant.String),
            ('mergedIds', QVariant.Double),
            ('condition', QVariant.String),
            ('distinctiveness', QVariant.String),  # Read-only, populated from server
            ('strategicSignificance', QVariant.String),
        ]
        
        self.watercourse_attributes = [
            ('id', QVariant.String),
            ('clientId', QVariant.String),  # Unique UUID generated on feature creation (readonly)
            ('referenceId', QVariant.String),
            ('sourceId', QVariant.String),
            ('activityType', QVariant.String),
            ('aiDashCode', QVariant.String),
            ('aiDashLabel', QVariant.String),
            ('mergedIds', QVariant.Double),
            ('condition', QVariant.String),
            ('distinctiveness', QVariant.String),  # Read-only, populated from server
            ('strategicSignificance', QVariant.String),
            ('riparianEncroachment', QVariant.String),
            ('watercourseEncroachment', QVariant.String),
        ]
        
        self.plan_attributes = [
            ('id', QVariant.String),
            ('clientId', QVariant.String),  # Unique UUID generated on feature creation (readonly)
            ('referenceId', QVariant.String),
            ('sourceId', QVariant.String),
            ('activityType', QVariant.String),
            ('aiDashCode', QVariant.String),
            ('aiDashLabel', QVariant.String),
            ('area', QVariant.Double),
            ('description', QVariant.String),
            ('mergedIds', QVariant.Double),
            ('condition', QVariant.String),
            ('distinctiveness', QVariant.String),  # Read-only, populated from server
            ('strategicSignificance', QVariant.String),
        ]
    
    def _ensure_bng_plan_group(self):
        """
        Ensure that the BNG Plan Layers group exists in the layer tree.
        Creates it if it doesn't exist.
        """
        # Look for existing BNG Plan Layers group
        self.bng_plan_group = self.root.findGroup("BNG Plan Layers")
        
        # Create group if it doesn't exist
        if not self.bng_plan_group:
            self.bng_plan_group = self.root.addGroup("BNG Plan Layers")
            QgsMessageLog.logMessage("Created BNG Plan Layers group", "BNGAI Plugin", level=0)
    
    def _build_aidash_value_map(self, code_map):
        """
        Build a value map for aiDashCode field.
        Shows habitat names with codes in dropdown, stores codes.
        
        Args:
            code_map (dict): Map of code -> code (e.g., PLANAR_AIDASHCODE_MAP)
            
        Returns:
            dict: Value map with {display_label: code} entries
        """
        value_map = {}
        for code in code_map.values():
            name = AIDASH_CODE_TO_NAME.get(code)
            if name:
                # Format: "Name (code)" for clarity in dropdown
                display_label = f"{name} ({code})"
                value_map[display_label] = code
            else:
                # Fallback: just show code if no name found
                value_map[code] = code
        return value_map
    
    def _get_common_value_maps(self):
        """
        Get common value maps used across all geometry types
        
        Returns:
            dict: Common value maps configuration
        """
        return {
            'condition': {
                # Labels map to stored codes
                'map': CONDITION_MAP
            },
            'strategicSignificance': {
                # Labels map to stored codes
                'map': STRATEGIC_SIGNIFICANCE_MAP
            },
            'aiDashCode': {
                # Names shown in dropdown, codes stored; also accepts direct code entry
                'map': self._build_aidash_value_map(PLANAR_AIDASHCODE_MAP)
            }
        }
    
    def _get_line_specific_value_maps(self):
        """
        Get value maps specific to line geometry (watercourse/hedgerow)
        
        Returns:
            dict: Line-specific value maps configuration
        """
        return {
            'riparianEncroachment': {
                # Labels map to stored codes
                'map': RIPARIAN_ENCROACHMENT_MAP
            },
            'watercourseEncroachment': {
                # Labels map to stored codes
                'map': WATERCOURSE_ENCROACHMENT_MAP
            },
            'aiDashCode': {
                # Names shown in dropdown, codes stored; also accepts direct code entry
                'map': self._build_aidash_value_map(WATERCOURSE_HEDGEROW_AIDASHCODE_MAP)
            }
        }
    
    def _get_point_specific_value_maps(self):
        """
        Get value maps specific to point geometry (trees)
        
        Returns:
            dict: Point-specific value maps configuration
        """
        return {
            'treeSize': {
                # Labels map to stored codes (codes already in values)
                'map': TREE_SIZE_MAP
            },
            'aiDashCode': {
                # Names shown in dropdown, codes stored; also accepts direct code entry
                'map': self._build_aidash_value_map(TREE_AIDASHCODE_MAP)
            }
        }
    
    def _apply_value_map(self, layer, field_name, config):
        """
        Apply value map configuration to a specific field
        
        Args:
            layer (QgsVectorLayer): Layer to configure
            field_name (str): Name of the field to configure
            config (dict): Value map configuration
        """
        field_index = layer.fields().indexFromName(field_name)
        if field_index >= 0:
            try:
                setup = QgsEditorWidgetSetup('ValueMap', config)
                layer.setEditorWidgetSetup(field_index, setup)
            except Exception as e:
                QgsMessageLog.logMessage(
                    f"Error setting up value map for field {field_name}: {str(e)}", 
                    "BNGAI Plugin", 
                    level=2
                )
    
    def _configure_field_value_maps(self, layer):
        """
        Configure value maps (dropdowns) for specific fields in the layer
        
        Args:
            layer (QgsVectorLayer): The layer to configure
        """
        # Get common value maps
        value_maps = self._get_common_value_maps()
        
        # Add line-specific value maps if needed
        if layer.geometryType() == QgsWkbTypes.LineGeometry:
            value_maps.update(self._get_line_specific_value_maps())
        # Add point-specific value maps if needed
        if layer.geometryType() == QgsWkbTypes.PointGeometry:
            value_maps.update(self._get_point_specific_value_maps())
        
        # Apply value maps to fields
        for field_name, config in value_maps.items():
            self._apply_value_map(layer, field_name, config)
        
        # Configure clientId as readonly (Hidden widget type)
        self._configure_readonly_field(layer, 'clientId')
        
        # Configure distinctiveness as readonly text field for watercourse (line) and point (tree) layers
        if layer.geometryType() in (QgsWkbTypes.LineGeometry, QgsWkbTypes.PointGeometry):
            self._configure_readonly_text_field(layer, 'distinctiveness')
    
    def _configure_readonly_field(self, layer, field_name):
        """
        Configure a field as readonly using the Hidden widget type
        
        Args:
            layer (QgsVectorLayer): Layer to configure
            field_name (str): Name of the field to make readonly
        """
        field_index = layer.fields().indexFromName(field_name)
        if field_index >= 0:
            try:
                # Use 'Hidden' widget type to make the field readonly in forms
                setup = QgsEditorWidgetSetup('Hidden', {})
                layer.setEditorWidgetSetup(field_index, setup)
                QgsMessageLog.logMessage(f"Configured field '{field_name}' as readonly (Hidden)", "BNGAI Plugin", level=0)
            except Exception as e:
                QgsMessageLog.logMessage(
                    f"Error configuring readonly field {field_name}: {str(e)}", 
                    "BNGAI Plugin", 
                    level=2
                )
    
    def _configure_readonly_text_field(self, layer, field_name):
        """
        Configure a field as a readonly text field (visible but not editable)
        
        Args:
            layer (QgsVectorLayer): Layer to configure
            field_name (str): Name of the field to make readonly
        """
        field_index = layer.fields().indexFromName(field_name)
        if field_index >= 0:
            try:
                # Use 'TextEdit' widget type with readonly config
                setup = QgsEditorWidgetSetup('TextEdit', {
                    'IsMultiline': False,
                    'UseHtml': False
                })
                layer.setEditorWidgetSetup(field_index, setup)
                # Set field to not editable via form config
                form_config = layer.editFormConfig()
                form_config.setReadOnly(field_index, True)
                layer.setEditFormConfig(form_config)
                QgsMessageLog.logMessage(f"Configured field '{field_name}' as readonly text field", "BNGAI Plugin", level=0)
            except Exception as e:
                QgsMessageLog.logMessage(
                    f"Error configuring readonly text field {field_name}: {str(e)}", 
                    "BNGAI Plugin", 
                    level=2
                )
    
    def generate_client_id(self):
        """
        Generate a unique client ID (UUID) for a new habitat feature.
        
        Returns:
            str: A new UUID string
        """
        return str(uuid.uuid4())
    
    def _apply_label_style(self, layer, label_field='referenceId'):
        """Apply QML style and then force label field to label_field, preserving QML format/placement."""
        try:
            qml_path = os.path.join(os.path.dirname(__file__), 'labelStyles', 'PlanLayerLabel.qml')
            if os.path.exists(qml_path):
                layer.loadNamedStyle(qml_path)
            # Try to preserve existing labeling and only switch field
            from qgis.core import (
                QgsVectorLayerSimpleLabeling,
                QgsRuleBasedLabeling,
            )
            labeling = layer.labeling()
            if isinstance(labeling, QgsVectorLayerSimpleLabeling):
                s = labeling.settings()
                s.fieldName = label_field
                layer.setLabeling(QgsVectorLayerSimpleLabeling(s))
            elif isinstance(labeling, QgsRuleBasedLabeling):
                root = labeling.rootRule()
                for rule in root.children():
                    try:
                        rs = rule.settings()
                        rs.fieldName = label_field
                        rule.setSettings(rs)
                    except Exception:
                        continue
                layer.setLabeling(QgsRuleBasedLabeling(root))
            layer.setLabelsEnabled(True)
            layer.triggerRepaint()
        except Exception as e:
            QgsMessageLog.logMessage(f"Label style apply failed: {str(e)}", "BNGAI Plugin", level=2)
    
    # Tree layer methods
    def create_tree_layer(self, name="BNG Plan Trees"):
        """
        Create a layer for tree planning with biodiversity attributes
        
        Args:
            name (str): Name for the layer
            
        Returns:
            QgsVectorLayer: The created vector layer or None if failed
        """
        try:
            # Create a new memory layer with tree attributes
            layer = self.layer_manager.create_memory_layer(
                name,
                'Point',
                crs="EPSG:4326",
                attributes=self.tree_attributes
            )
            
            if not layer:
                return None
            
            # Move from default BNG AI group to BNG Plan Layers group
            self._move_to_bng_plan_group(layer)
            
            # Apply a default style for BNG plan trees
            self._apply_tree_style(layer)
            
            # Start editing to ensure widget setup is applied
            layer.startEditing()
            
            # Configure value maps for dropdown fields
            self._configure_field_value_maps(layer)
            
            # Save changes and refresh
            layer.commitChanges()
            layer.updateFields()
            
            # Apply QML and enforce label field
            self._apply_label_style(layer, 'referenceId')
            
            QgsMessageLog.logMessage(f"Created BNG Plan tree layer: {name}", "BNGAI Plugin", level=0)
            return layer
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error creating BNG Plan tree layer: {str(e)}", "BNGAI Plugin", level=2)
            return None
    
    # Watercourse/Hedgerow layer methods
    def create_watercourse_layer(self, name="BNG Plan Watercourse/Hedgerow"):
        """
        Create a layer for watercourse and hedgerow planning with biodiversity attributes
        
        Args:
            name (str): Name for the layer
            
        Returns:
            QgsVectorLayer: The created vector layer or None if failed
        """
        try:
            # Create a new memory layer with watercourse attributes
            layer = self.layer_manager.create_memory_layer(
                name,
                'LineString',
                crs="EPSG:4326",
                attributes=self.watercourse_attributes
            )
            
            if not layer:
                return None
            
            # Move from default BNG AI group to BNG Plan Layers group
            self._move_to_bng_plan_group(layer)
            
            # Apply a default style for BNG plan watercourse/hedgerow
            self._apply_watercourse_style(layer)
            
            # Start editing to ensure widget setup is applied
            layer.startEditing()
            
            # Configure value maps for dropdown fields
            self._configure_field_value_maps(layer)
            
            # Save changes and refresh
            layer.commitChanges()
            layer.updateFields()
            
            # Apply QML and enforce label field
            self._apply_label_style(layer, 'referenceId')
            
            QgsMessageLog.logMessage(f"Created BNG Plan watercourse/hedgerow layer: {name}", "BNGAI Plugin", level=0)
            return layer
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error creating BNG Plan watercourse/hedgerow layer: {str(e)}", "BNGAI Plugin", level=2)
            return None
    
    # Plan layer methods
    def create_plan_layer(self, name="BNG Plan Boundary"):
        """
        Create a layer for BNG plan boundary with biodiversity metrics
        
        Args:
            name (str): Name for the layer
            
        Returns:
            QgsVectorLayer: The created vector layer or None if failed
        """
        try:
            # Create a new memory layer with plan attributes
            layer = self.layer_manager.create_memory_layer(
                name,
                'Polygon',
                crs="EPSG:4326",
                attributes=self.plan_attributes
            )
            
            if not layer:
                return None
            
            # Move from default BNG AI group to BNG Plan Layers group
            self._move_to_bng_plan_group(layer)
            
            # Apply a default style for BNG plans
            self._apply_plan_style(layer)
            
            # Start editing to ensure widget setup is applied
            layer.startEditing()
            
            # Configure value maps for dropdown fields
            self._configure_field_value_maps(layer)
            
            # Save changes and refresh
            layer.commitChanges()
            layer.updateFields()

            # Apply QML and enforce label field
            self._apply_label_style(layer, 'referenceId')
            
            QgsMessageLog.logMessage(f"Created BNG Plan boundary layer: {name}", "BNGAI Plugin", level=0)
            return layer
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error creating BNG Plan boundary layer: {str(e)}", "BNGAI Plugin", level=2)
            return None
    
    def _move_to_bng_plan_group(self, layer):
        """
        Move a layer from its current group to the BNG Plan Layers group
        
        Args:
            layer (QgsMapLayer): The layer to move
        """
        if not layer or not self.bng_plan_group:
            return
        
        # Find the layer in the layer tree
        layer_id = layer.id()
        layer_node = self.root.findLayer(layer_id)
        
        if layer_node:
            # Get the parent group
            parent = layer_node.parent()
            
            # Clone the layer node to the BNG Plan group
            self.bng_plan_group.addLayer(layer)
            
            # Remove the layer from its original parent
            if parent:
                parent.removeChildNode(layer_node)
    
    def import_from_api(self, plan_id, api_client, token):
        """
        Import BNG Plan layers from API data
        
        Args:
            plan_id (str): BNG Plan ID to retrieve data for
            api_client: API client instance for making requests
            token (str): Authentication token
            
        Returns:
            dict: Dictionary of created layers or None if failed
        """
        try:
            # Call API to get plan data
            QgsMessageLog.logMessage(f"Fetching BNG Plan data for plan ID: {plan_id}", "BNGAI Plugin", level=0)
            
            # Example API endpoint structure - adjust as needed for your API
            url = f"plans/{plan_id}/layers"
            response = api_client.get(url, headers={"Authorization": token})
            
            if not response or "data" not in response:
                QgsMessageLog.logMessage("Failed to retrieve BNG Plan data from API", "BNGAI Plugin", level=2)
                return None
            
            data = response["data"]
            layers_created = {}
            
            # Process tree data if available
            if "trees" in data and data["trees"]:
                tree_layer = self.layer_manager.load_geojson(
                    "BNG Plan Trees",
                    data["trees"],
                    crs="EPSG:4326"
                )
                
                if tree_layer:
                    self._move_to_bng_plan_group(tree_layer)
                    self._apply_tree_style(tree_layer)
                    layers_created["trees"] = tree_layer
            
            # Process watercourse data if available
            if "watercourses" in data and data["watercourses"]:
                watercourse_layer = self.layer_manager.load_geojson(
                    "BNG Plan Watercourse/Hedgerow",
                    data["watercourses"],
                    crs="EPSG:4326"
                )
                
                if watercourse_layer:
                    self._move_to_bng_plan_group(watercourse_layer)
                    self._apply_watercourse_style(watercourse_layer)
                    layers_created["watercourses"] = watercourse_layer
            
            # Process plan boundary data if available
            if "boundary" in data and data["boundary"]:
                plan_layer = self.layer_manager.load_geojson(
                    "BNG Plan Boundary",
                    data["boundary"],
                    crs="EPSG:4326"
                )
                
                if plan_layer:
                    self._move_to_bng_plan_group(plan_layer)
                    self._apply_plan_style(plan_layer)
                    layers_created["boundary"] = plan_layer
            
            QgsMessageLog.logMessage(f"Imported BNG Plan layers for plan ID: {plan_id}", "BNGAI Plugin", level=0)
            return layers_created
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error importing BNG Plan from API: {str(e)}", "BNGAI Plugin", level=2)
            return None
    
    def calculate_net_gain(self, baseline_layer, bng_plan_layer, target_field="netGain"):
        """
        Calculate net biodiversity gain between baseline and BNG plan layer
        
        Args:
            baseline_layer (QgsVectorLayer): Baseline layer for comparison
            bng_plan_layer (QgsVectorLayer): BNG Plan layer
            target_field (str): Field to store net gain value
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not baseline_layer or not baseline_layer.isValid():
                QgsMessageLog.logMessage("Invalid baseline layer for net gain calculation", "BNGAI Plugin", level=2)
                return False
                
            if not bng_plan_layer or not bng_plan_layer.isValid():
                QgsMessageLog.logMessage("Invalid BNG Plan layer for net gain calculation", "BNGAI Plugin", level=2)
                return False
            
            # Check if target field exists, create it if not
            field_index = bng_plan_layer.fields().indexFromName(target_field)
            if field_index == -1:
                bng_plan_layer.dataProvider().addAttributes([QgsField(target_field, QVariant.Double)])
                bng_plan_layer.updateFields()
                field_index = bng_plan_layer.fields().indexFromName(target_field)
            
            # Start editing
            bng_plan_layer.startEditing()
            
            # Get total biodiversity value from baseline
            baseline_value = 0
            for feature in baseline_layer.getFeatures():
                if feature.fieldNameIndex('biodiversityValue') >= 0:
                    value = feature.attribute('biodiversityValue')
                    if value is not None:
                        baseline_value += float(value)
            
            # Get total biodiversity value from BNG plan
            bng_value = 0
            for feature in bng_plan_layer.getFeatures():
                if feature.fieldNameIndex('biodiversityValue') >= 0:
                    value = feature.attribute('biodiversityValue')
                    if value is not None:
                        bng_value += float(value)
            
            # Calculate net gain
            net_gain = bng_value - baseline_value
            
            # Update features with net gain
            for feature in bng_plan_layer.getFeatures():
                bng_plan_layer.changeAttributeValue(feature.id(), field_index, net_gain)
            
            # Commit changes
            bng_plan_layer.commitChanges()
            
            QgsMessageLog.logMessage(
                f"Calculated net gain ({net_gain}) between baseline and BNG Plan", 
                "BNGAI Plugin", 
                level=0
            )
            return True
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error calculating net gain: {str(e)}", "BNGAI Plugin", level=2)
            if bng_plan_layer and bng_plan_layer.isEditable():
                bng_plan_layer.rollBack()
            return False
    
    def _apply_tree_style(self, layer):
        """
        Apply QML style to a BNG Plan tree layer
        
        Args:
            layer (QgsVectorLayer): Layer to style
        """
        if not layer:
            return
            
        # Get the path to the QML file from Plan symbology
        qml_path = os.path.join(os.path.dirname(__file__), 'symbology', 'Plan', 'PlanTree.qml')
        
        if os.path.exists(qml_path):
            # Load and apply the style
            layer.loadNamedStyle(qml_path)
            layer.triggerRepaint()
            QgsMessageLog.logMessage(f"Applied tree style from {qml_path}", "BNGAI Plugin", level=0)
        else:
            QgsMessageLog.logMessage(f"Style file not found: {qml_path}", "BNGAI Plugin", level=2)
    
    def _apply_watercourse_style(self, layer):
        """
        Apply QML style to a BNG Plan watercourse/hedgerow layer
        
        Args:
            layer (QgsVectorLayer): Layer to style
        """
        if not layer:
            return
            
        # Use Plan symbology for Watercourse/Hedgerow
        qml_path = os.path.join(os.path.dirname(__file__), 'symbology', 'Plan', 'PlanWatercourseHedgerow.qml')
        
        if os.path.exists(qml_path):
            # Load and apply the style
            layer.loadNamedStyle(qml_path)
            layer.triggerRepaint()
            QgsMessageLog.logMessage(f"Applied watercourse/hedgerow style from {qml_path}", "BNGAI Plugin", level=0)
        else:
            QgsMessageLog.logMessage(f"Style file not found: {qml_path}", "BNGAI Plugin", level=2)
    
    def _apply_plan_style(self, layer):
        """
        Apply QML style to a BNG Plan boundary layer
        
        Args:
            layer (QgsVectorLayer): Layer to style
        """
        if not layer:
            return
            
        # Get the path to the QML file from Plan symbology
        qml_path = os.path.join(os.path.dirname(__file__), 'symbology', 'Plan', 'PlanPolygon.qml')
        
        if os.path.exists(qml_path):
            # Load and apply the style
            layer.loadNamedStyle(qml_path)
            layer.triggerRepaint()
            QgsMessageLog.logMessage(f"Applied plan style from {qml_path}", "BNGAI Plugin", level=0)
        else:
            QgsMessageLog.logMessage(f"Style file not found: {qml_path}", "BNGAI Plugin", level=2)
    
    def clear_all_bng_plan_layers(self):
        """
        Remove all layers in the BNG Plan Layers group
        
        Returns:
            bool: True if successful, False otherwise
        """
        # Make sure the BNG Plan Layers group exists
        self._ensure_bng_plan_group()
        
        try:
            # Get all layers in the BNG Plan Layers group
            layer_ids = [node.layerId() for node in self.bng_plan_group.findLayers()]
            
            # Remove all layers
            self.project.removeMapLayers(layer_ids)
            
            QgsMessageLog.logMessage("Removed all BNG Plan Layers", "BNGAI Plugin", level=0)
            return True
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error removing BNG Plan Layers: {str(e)}", "BNGAI Plugin", level=2)
            return False 