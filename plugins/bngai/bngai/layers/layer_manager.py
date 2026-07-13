"""
LayerManager - Module for manipulating QGIS layers for the BNG AI plugin
"""
from qgis.core import (QgsProject, QgsRasterLayer, QgsVectorLayer, 
                      QgsLayerTreeGroup, QgsCoordinateReferenceSystem, 
                      QgsCoordinateTransform, QgsMessageLog, QgsApplication,
                      QgsDataSourceUri, QgsWkbTypes, QgsMapLayer, QgsFeature, 
                      QgsGeometry, QgsField)
from qgis.PyQt.QtCore import QObject, pyqtSignal, QVariant, QUrl
from qgis.PyQt.QtXml import QDomDocument
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QComboBox, QPushButton, QLabel
import os
import time
import sip
import uuid


class LayerManager(QObject):
    """
    Manages layer interactions and selection state.
    """
    # Define signals
    selection_changed = pyqtSignal()
    editing_stopped = pyqtSignal(QgsMapLayer)  # layer
    feature_added = pyqtSignal(QgsMapLayer, int)  # layer, feature_id
    features_deleted = pyqtSignal(QgsMapLayer, list)  # layer, feature_ids
    features_committed = pyqtSignal(QgsMapLayer, list)  # layer, feature_ids
    
    def __init__(self):
        """Initialize the layer manager"""
        super().__init__()
        QgsMessageLog.logMessage("Initializing LayerManager", "BNGAI Plugin", level=0)
        
        # Core properties
        self.project = QgsProject.instance()
        self.root = self.project.layerTreeRoot()
        self.bng_group = None
        
        # Selection tracking properties
        self.layer_connections = {}  # Track layer signal connections
        self.current_layer = None  # Track the current layer with selection
        self.current_feature = None  # Track the current selected feature
        
        # Track pending features per layer
        self.pending_features = {}  # {layer_id: {'added': set(), 'deleted': set()}}
        
        # Ensure the BNG group exists
        self._ensure_bng_group()
        QgsMessageLog.logMessage("LayerManager initialized", "BNGAI Plugin", level=0)
    
    def _ensure_bng_group(self):
        """
        Ensure that the BNG AI group exists in the layer tree.
        Creates it if it doesn't exist.
        """
        # Look for existing BNG AI group
        self.bng_group = self.root.findGroup("BNG AI")
        
        # Create group if it doesn't exist
        if not self.bng_group:
            self.bng_group = self.root.addGroup("BNG AI")
            QgsMessageLog.logMessage("Created BNG AI layer group", "BNGAI Plugin", level=0)
    
    def _init_layer_tracking(self, layer):
        """Initialize feature tracking for a layer"""
        layer_id = layer.id()
        if layer_id not in self.pending_features:
            self.pending_features[layer_id] = {
                'added': set(),
                'deleted': set()
            }
            
    def on_layer_deleted(self, layer):
        """
        Handle layer deletion signal
        
        Args:
            layer: The layer being deleted
        """
        try:
            # Get layer ID before the layer is deleted
            layer_id = None
            try:
                if layer and not sip.isdeleted(layer):
                    layer_id = layer.id()
            except:
                pass
            
            # If we couldn't get the layer ID, try to find it in our connections
            if not layer_id:
                # Find the layer ID in our connections that matches this layer object
                for lid, callbacks in self.layer_connections.items():
                    if callbacks.get('layer_ref') == layer:
                        layer_id = lid
                        break
            
            # If we found the layer ID, clean up its connections
            if layer_id and layer_id in self.layer_connections:
                # Get callbacks before removing from tracking dict
                callbacks = self.layer_connections[layer_id]
                
                # Remove from tracking dict first
                del self.layer_connections[layer_id]
                
                # Try to safely disconnect signals if the layer is still valid
                try:
                    if layer and not sip.isdeleted(layer) and layer.isValid():
                        if hasattr(layer, 'selectionChanged'):
                            layer.selectionChanged.disconnect(callbacks['selection_changed'])
                        if hasattr(layer, 'editingStopped'):
                            layer.editingStopped.disconnect(callbacks['editing_stopped'])
                        if hasattr(layer, 'featureAdded'):
                            layer.featureAdded.disconnect(callbacks['feature_added'])
                except:
                    pass  # Ignore any disconnection errors
                
                QgsMessageLog.logMessage(f"Cleaned up deleted layer (ID: {layer_id})", "BNGAI Plugin", level=0)
                
                # Clear current selection if this was the current layer
                if self.current_layer and hasattr(self.current_layer, 'id'):
                    try:
                        if self.current_layer.id() == layer_id:
                            self.current_layer = None
                            self.current_feature = None
                            self.selection_changed.emit()
                    except:
                        # If we can't access the current layer's ID, just reset everything
                        self.current_layer = None
                        self.current_feature = None
                        self.selection_changed.emit()
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error handling layer deletion: {str(e)}", "BNGAI Plugin", level=2)
            # Try to clean up as much as possible
            try:
                if layer_id and layer_id in self.layer_connections:
                    del self.layer_connections[layer_id]
            except:
                pass
            # Reset current layer and feature
            self.current_layer = None
            self.current_feature = None
            self.selection_changed.emit()

    def connect_layer(self, layer):
        """
        Connect to layer signals
        
        Args:
            layer (QgsMapLayer): The layer to connect to
        """
        if not layer or not layer.isValid():
            return
            
        try:
            layer_id = layer.id()
        except:
            QgsMessageLog.logMessage("Could not get layer ID", "BNGAI Plugin", level=2)
            return
        
        # Already connected?
        if layer_id in self.layer_connections:
            QgsMessageLog.logMessage(f"Layer {layer.name()} already connected to LayerManager", "BNGAI Plugin", level=0)
            return
            
        QgsMessageLog.logMessage(f"LayerManager connecting to layer: {layer.name()} (ID: {layer_id})", "BNGAI Plugin", level=0)
        
        # Store weak reference to layer to avoid circular references
        import weakref
        layer_ref = None
        try:
            layer_ref = weakref.proxy(layer)
        except:
            layer_ref = layer  # Fallback to normal reference if weak reference fails
        
        # Define the callbacks with safe layer access
        def on_selection_changed():
            try:
                if not sip.isdeleted(layer):
                    self.handle_selection_changed(layer)
            except:
                pass
            
        def on_editing_stopped():
            try:
                if not sip.isdeleted(layer):
                    self.handle_editing_stopped(layer)
            except:
                pass

        def on_feature_added(feature_id):
            try:
                if not sip.isdeleted(layer):
                    self.handle_feature_added(layer, feature_id)
            except:
                pass
            
        # Store the callbacks and a reference to the layer
        self.layer_connections[layer_id] = {
            'selection_changed': on_selection_changed,
            'editing_stopped': on_editing_stopped,
            'feature_added': on_feature_added,
            'layer_ref': layer_ref  # Store reference to help with cleanup
        }
        
        # Connect the signals
        try:
            layer.selectionChanged.connect(on_selection_changed)
            layer.editingStopped.connect(on_editing_stopped)
            layer.featureAdded.connect(on_feature_added)
            QgsMessageLog.logMessage(f"Successfully connected all signals for layer: {layer.name()}", "BNGAI Plugin", level=0)
            # Enable 'Show Feature Count' in layer tree for this layer
            try:
                layer_node = self.root.findLayer(layer_id)
                if layer_node:
                    layer_node.setCustomProperty("showFeatureCount", True)
                    QgsMessageLog.logMessage(f"Enabled feature count for layer: {layer.name()}", "BNGAI Plugin", level=0)
            except Exception:
                pass
        except Exception as e:
            QgsMessageLog.logMessage(f"Error connecting to layer {layer.name()}: {str(e)}", "BNGAI Plugin", level=2)
            # Clean up partial connections
            if layer_id in self.layer_connections:
                del self.layer_connections[layer_id]

    def disconnect_layer(self, layer):
        """
        Disconnect from layer signals.
        
        Args:
            layer (QgsMapLayer): The layer to disconnect from
        """
        try:
            # Check if layer is already deleted
            if not layer or sip.isdeleted(layer):
                return
                
            layer_id = layer.id()
            if layer_id not in self.layer_connections:
                return
                
            callbacks = self.layer_connections[layer_id]
            
            # Only try to disconnect if layer is still valid
            if layer.isValid():
                try:
                    layer.selectionChanged.disconnect(callbacks['selection_changed'])
                    layer.editingStopped.disconnect(callbacks['editing_stopped'])
                    layer.featureAdded.disconnect(callbacks['feature_added'])
                except:
                    pass  # Ignore disconnection errors
            
            # Remove from tracking dict
            del self.layer_connections[layer_id]
            QgsMessageLog.logMessage(f"LayerManager disconnected all signals for layer: {layer.name()}", "BNGAI Plugin", level=0)
            
            # Clear current selection if this was the current layer
            if self.current_layer and hasattr(self.current_layer, 'id'):
                try:
                    if self.current_layer.id() == layer_id:
                        self.current_layer = None
                        self.current_feature = None
                        self.selection_changed.emit()
                except:
                    # Reset everything if we can't access the ID
                    self.current_layer = None
                    self.current_feature = None
                    self.selection_changed.emit()
                
        except Exception as e:
            QgsMessageLog.logMessage(f"Error disconnecting layer: {str(e)}", "BNGAI Plugin", level=2)
            # Still try to remove from tracking dict if we have the layer_id
            try:
                if layer and not sip.isdeleted(layer):
                    layer_id = layer.id()
                    if layer_id in self.layer_connections:
                        del self.layer_connections[layer_id]
            except:
                pass

    def handle_selection_changed(self, layer):
        """
        Handle feature selection changes.
        
        Args:
            layer (QgsMapLayer): The layer where selection changed
        """
        try:
            # First check if layer still exists and is valid
            if not layer or not layer.isValid():
                QgsMessageLog.logMessage(f"Invalid layer in handle_selection_changed", "BNGAI Plugin", level=2)
                self.current_layer = None
                self.current_feature = None
                self.selection_changed.emit()
                return
                
            # Check if layer is still in project
            if not self.project.mapLayer(layer.id()):
                QgsMessageLog.logMessage(f"Layer no longer in project", "BNGAI Plugin", level=2)
                self.current_layer = None
                self.current_feature = None
                self.selection_changed.emit()
                return
                
            selected_features = layer.selectedFeatures()
            
            if not selected_features:
                self.current_layer = None
                self.current_feature = None
                self.selection_changed.emit()
                return
            
            # Get the first selected feature
            feature = selected_features[0]
            QgsMessageLog.logMessage(f"First selected feature ID: {feature.id()} in layer {layer.name()}", "BNGAI Plugin", level=0)
            
            # Store the current layer and feature
            self.current_layer = layer
            self.current_feature = feature
            
            # Emit signal
            self.selection_changed.emit()
            
        except RuntimeError as e:
            QgsMessageLog.logMessage(f"Layer was deleted during selection handling: {str(e)}", "BNGAI Plugin", level=2)
            self.current_layer = None
            self.current_feature = None
            self.selection_changed.emit()
        except Exception as e:
            QgsMessageLog.logMessage(f"Error handling selection change: {str(e)}", "BNGAI Plugin", level=2)
            self.current_layer = None
            self.current_feature = None
            self.selection_changed.emit()

    def handle_editing_stopped(self, layer):
        """
        Handle the editing stopped signal from a layer.
        
        Args:
            layer (QgsMapLayer): The layer where editing was stopped
        """
        if not layer or not layer.isValid():
            QgsMessageLog.logMessage("Invalid layer in handle_editing_stopped", "BNGAI Plugin", level=2)
            return
            
        try:
            # Get layer identifiers
            layer_id = layer.id()
            bngai_id = layer.customProperty('bngai_id', '<no bngai_id>')
            
            # Verify layer is still in project
            if not self.project.mapLayer(layer_id):
                QgsMessageLog.logMessage("Layer no longer in project", "BNGAI Plugin", level=2)
                return
                
           
            # Emit the signal with verified layer
            self.editing_stopped.emit(layer)
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error in handle_editing_stopped: {str(e)}", "BNGAI Plugin", level=2)

    def handle_feature_added(self, layer, feature_id):
        """
        Handle the feature added signal from a layer.
        Auto-generates a clientId UUID for new features in BNG Plan layers.
        
        IMPORTANT: Always generates a NEW clientId for newly added features,
        even if the feature already has one (e.g., from copy/paste).
        This ensures each feature has a unique clientId.
        
        Args:
            layer (QgsMapLayer): The layer where the feature was added
            feature_id (int): The ID of the added feature (may be negative for new features)
        """
        QgsMessageLog.logMessage(f"Feature added to layer: {layer.name()} - Feature ID: {feature_id}", "BNGAI Plugin", level=0)
        
        # Auto-generate clientId for BNG Plan layer features if clientId field exists
        try:
            if layer and layer.isValid() and layer.isEditable():
                field_index = layer.fields().indexFromName('clientId')
                if field_index >= 0:
                    # For new features (negative IDs), access via edit buffer
                    edit_buffer = layer.editBuffer()
                    if edit_buffer:
                        # Check if this is a newly added feature
                        added_features = edit_buffer.addedFeatures()
                        if feature_id in added_features:
                            # ALWAYS generate a new clientId for newly added features
                            # This handles both new creations AND pasted features
                            new_client_id = str(uuid.uuid4())
                            layer.changeAttributeValue(feature_id, field_index, new_client_id)
                            QgsMessageLog.logMessage(f"Generated clientId for new feature {feature_id}: {new_client_id}", "BNGAI Plugin", level=0)
                        else:
                            # For existing features (not newly added), only set if empty
                            feature = layer.getFeature(feature_id)
                            if feature.isValid():
                                current_client_id = feature.attribute('clientId')
                                if not current_client_id:
                                    new_client_id = str(uuid.uuid4())
                                    layer.changeAttributeValue(feature_id, field_index, new_client_id)
                                    QgsMessageLog.logMessage(f"Generated clientId for feature {feature_id}: {new_client_id}", "BNGAI Plugin", level=0)
        except Exception as e:
            QgsMessageLog.logMessage(f"Error setting clientId for feature {feature_id}: {str(e)}", "BNGAI Plugin", level=2)
            import traceback
            QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
        
        self.feature_added.emit(layer, feature_id)
        
    def handle_features_deleted(self, layer, feature_ids):
        """
        Handle the features deleted signal from a layer.
        
        Args:
            layer (QgsMapLayer): The layer where features were deleted
            feature_ids (list): List of IDs of the deleted features
        """
        QgsMessageLog.logMessage(f"Features deleted from layer: {layer.name()} - Feature IDs: {feature_ids}", "BNGAI Plugin", level=0)
        self.features_deleted.emit(layer, feature_ids)

    def handle_features_committed(self, layer):
        """
        Handle the features committed signal from a layer.
        
        Args:
            layer (QgsMapLayer): The layer where features were committed
        """
        layer_id = layer.id()
        if layer_id not in self.pending_features:
            return
            
        try:
            # Get the tracked features for this layer
            added_features = list(self.pending_features[layer_id]['added'])
            deleted_features = list(self.pending_features[layer_id]['deleted'])
            
            QgsMessageLog.logMessage(
                f"Processing committed changes for layer {layer.name()}:\n" +
                f"Added features: {added_features}\n" +
                f"Deleted features: {deleted_features}",
                "BNGAI Plugin", level=0
            )
            
            # Emit signal with added features (these are the ones we care about)
            if added_features:
                self.features_committed.emit(layer, added_features)
            
            # Clear the tracking sets for this layer
            self.pending_features[layer_id]['added'].clear()
            self.pending_features[layer_id]['deleted'].clear()
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error processing committed features: {str(e)}", "BNGAI Plugin", level=2)
            # If processing fails, clear the tracking sets to avoid stale data
            if layer_id in self.pending_features:
                self.pending_features[layer_id]['added'].clear()
                self.pending_features[layer_id]['deleted'].clear()

    def get_current_selection(self):
        """
        Get the currently selected layer and feature.
        
        Returns:
            tuple: (QgsMapLayer, QgsFeature) or (None, None) if no selection
        """
        try:
            if self.current_layer and not self.current_layer.isValid():
                QgsMessageLog.logMessage("Current layer is no longer valid", "BNGAI Plugin", level=0)
                self.current_layer = None
                self.current_feature = None
                
            if self.current_layer and not self.project.mapLayer(self.current_layer.id()):
                QgsMessageLog.logMessage("Current layer is no longer in project", "BNGAI Plugin", level=0)
                self.current_layer = None
                self.current_feature = None
                
        except RuntimeError:
            QgsMessageLog.logMessage("Layer was deleted, clearing selection", "BNGAI Plugin", level=0)
            self.current_layer = None
            self.current_feature = None
            
        return self.current_layer, self.current_feature

    # Layer Operations
    def add_wms_layer(self, layer_name, url, layers, format="image/png", crs="EPSG:4326", styles=""):
        """
        Add a WMS layer to the BNG AI group
        
        Args:
            layer_name (str): Display name for the layer
            url (str): WMS service URL
            layers (str): Layer names to request from WMS service
            format (str): Image format (default: "image/png")
            crs (str): Coordinate reference system (default: "EPSG:4326")
            styles (str): WMS styles (default: "")
            
        Returns:
            QgsRasterLayer: The created raster layer or None if failed
        """
        # Make sure the BNG group exists
        self._ensure_bng_group()
        
        # Build the URI for the WMS
        uri = f"crs={crs}&format={format}&layers={layers}&styles={styles}&url={url}"
        
        # Create the raster layer
        wms_layer = QgsRasterLayer(uri, layer_name, "wms")
        
        if not wms_layer.isValid():
            QgsMessageLog.logMessage(f"Failed to create WMS layer: {layer_name}", "BNGAI Plugin", level=2)
            return None
        
        # Add to the project
        self.project.addMapLayer(wms_layer, False)
        self.bng_group.addLayer(wms_layer)
        
        QgsMessageLog.logMessage(f"Added WMS layer: {layer_name}", "BNGAI Plugin", level=0)
        return wms_layer
    
    def add_vector_layer(self, layer_name, uri, provider="ogr"):
        """
        Add a vector layer to the BNG AI group
        
        Args:
            layer_name (str): Display name for the layer
            uri (str): Data source URI
            provider (str): Data provider name (default: "ogr")
            
        Returns:
            QgsVectorLayer: The created vector layer or None if failed
        """
        # Make sure the BNG group exists
        self._ensure_bng_group()
        
        # Create the vector layer
        vector_layer = QgsVectorLayer(uri, layer_name, provider)
        
        if not vector_layer.isValid():
            QgsMessageLog.logMessage(f"Failed to create vector layer: {layer_name}", "BNGAI Plugin", level=2)
            return None
        
        # Add to the project
        self.project.addMapLayer(vector_layer, False)
        self.bng_group.addLayer(vector_layer)
        
        # Connect to layer signals if it's a vector layer
        self.connect_layer(vector_layer)
        
        QgsMessageLog.logMessage(f"Added vector layer: {layer_name}", "BNGAI Plugin", level=0)
        return vector_layer
    
    def create_memory_layer(self, layer_name, geometry_type, crs="EPSG:4326", attributes=None, add_to_group=True):
        """
        Create a memory layer, optionally adding it to the BNG AI group.
        
        Args:
            layer_name (str): Display name for the layer
            geometry_type (str): Geometry type ('Point', 'LineString', 'Polygon')
            crs (str): Coordinate reference system (default: "EPSG:4326")
            attributes (list): List of attribute definitions [('name', type), ...] 
                              where type is QVariant.Int, QVariant.Double, etc.
            add_to_group (bool): If True, add to BNG AI group. If False, just add to project
                                without any group (caller can move to their own group).
            
        Returns:
            QgsVectorLayer: The created memory layer or None if failed
        """
        # Map geometry type to WKB type
        geom_types = {
            'Point': 'Point',
            'LineString': 'LineString',
            'Polygon': 'Polygon',
            'MultiPoint': 'MultiPoint',
            'MultiLineString': 'MultiLineString',
            'MultiPolygon': 'MultiPolygon'
        }
        
        if geometry_type not in geom_types:
            QgsMessageLog.logMessage(f"Invalid geometry type: {geometry_type}", "BNGAI Plugin", level=2)
            return None
        
        # Create the URI for the memory layer
        uri = f"{geom_types[geometry_type]}?crs={crs}"
        
        # Add attribute fields if provided
        if attributes:
            for attr_name, attr_type in attributes:
                uri += f"&field={attr_name}:{attr_type}"
        
        # Create the memory layer
        memory_layer = QgsVectorLayer(uri, layer_name, "memory")
        
        if not memory_layer.isValid():
            QgsMessageLog.logMessage(f"Failed to create memory layer: {layer_name}", "BNGAI Plugin", level=2)
            return None
        
        # Add to the project
        if add_to_group:
            # Add to BNG AI group
            self._ensure_bng_group()
            self.project.addMapLayer(memory_layer, False)
            self.bng_group.addLayer(memory_layer)
        else:
            # Just add to project without any group (caller will handle grouping)
            self.project.addMapLayer(memory_layer, True)
        
        # Connect to layer signals
        self.connect_layer(memory_layer)
        
        QgsMessageLog.logMessage(f"Created memory layer: {layer_name}", "BNGAI Plugin", level=0)
        return memory_layer
    
    # BNG Plan Layer Management
    def get_bng_plan_layers(self):
        """
        Get all BNG Plan layers from the project
            
        Returns:
            list: List of layer IDs that are BNG Plan layers
        """
        bng_plan_layers = []
        
        # Get all layers in the project
        layers = self.project.mapLayers()
        
        for layer_id, layer in layers.items():
            if layer and layer.isValid():
                # Check if layer has bngai_id custom property
                bngai_id = layer.customProperty('bngai_id')
                if bngai_id:
                    bng_plan_layers.append(layer_id)
        
        return bng_plan_layers
        
    def remove_bng_plan_layers(self):
        """
        Remove all BNG Plan layers from the project
        """
        # Get BNG Plan layer IDs
        layer_ids = self.get_bng_plan_layers()
        
        # Remove the layers
        if layer_ids:
            self.project.removeMapLayers(layer_ids)
            QgsMessageLog.logMessage(f"Removed {len(layer_ids)} BNG Plan layers", "BNGAI Plugin", level=0)

    # Layer Styling and View Operations
    def style_layer(self, layer, style_file=None, style_xml=None):
        """
        Apply a style to a layer
        
        Args:
            layer (QgsMapLayer): Layer to style
            style_file (str): Path to QML style file (optional)
            style_xml (str): QML style as XML string (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not layer:
            QgsMessageLog.logMessage("Cannot style null layer", "BNGAI Plugin", level=2)
            return False
        
        try:
            if style_file and os.path.exists(style_file):
                # Load style from file
                result = layer.loadNamedStyle(style_file)
                if not result[0]:
                    QgsMessageLog.logMessage(f"Failed to load style: {result[1]}", "BNGAI Plugin", level=2)
                    return False
                    
            elif style_xml:
                # Load style from XML string
                doc = QDomDocument()
                if not doc.setContent(style_xml):
                    QgsMessageLog.logMessage("Failed to parse style XML", "BNGAI Plugin", level=2)
                    return False
                    
                result = layer.importNamedStyle(doc)
                if not result[0]:
                    QgsMessageLog.logMessage(f"Failed to import style: {result[1]}", "BNGAI Plugin", level=2)
                    return False
            else:
                QgsMessageLog.logMessage("No style provided", "BNGAI Plugin", level=1)
                return False
            
            # Refresh the layer
            layer.triggerRepaint()
            
            # Update the legend
            if self.bng_group:
                layer_node = self.bng_group.findLayer(layer.id())
                if layer_node:
                    layer_node.setItemVisibilityChecked(True)
            
            QgsMessageLog.logMessage(f"Applied style to layer: {layer.name()}", "BNGAI Plugin", level=0)
            return True
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error applying style: {str(e)}", "BNGAI Plugin", level=2)
            return False
    
    def zoom_to_layer(self, layer):
        """
        Zoom the map canvas to a layer's extent
        
        Args:
            layer (QgsMapLayer): Layer to zoom to
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not layer:
            QgsMessageLog.logMessage("Cannot zoom to null layer", "BNGAI Plugin", level=2)
            return False
        
        try:
            # Get the map canvas
            from qgis.utils import iface
            canvas = iface.mapCanvas() if iface else None
            
            if not canvas:
                QgsMessageLog.logMessage("Failed to get map canvas", "BNGAI Plugin", level=2)
                return False
            
            # Get the layer extent in the project CRS
            extent = layer.extent()
            
            if layer.crs() != self.project.crs():
                transform = QgsCoordinateTransform(layer.crs(), self.project.crs(), self.project)
                extent = transform.transformBoundingBox(extent)
            
            # Add a buffer around the extent (10%)
            buffer = extent.width() * 0.1
            extent.grow(buffer)
            
            # Set the extent on the canvas
            canvas.setExtent(extent)
            canvas.refresh()
            
            QgsMessageLog.logMessage(f"Zoomed to layer: {layer.name()}", "BNGAI Plugin", level=0)
            return True
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error zooming to layer: {str(e)}", "BNGAI Plugin", level=2)
            return False
    
    def on_layers_added(self, layers):
        """
        Handle layers being added to the project
        
        Args:
            layers (list): List of QgsMapLayer objects that were added
        """
        QgsMessageLog.logMessage(f"LayerManager: Layers added to project: {len(layers)}", "BNGAI Plugin", level=0)
        for layer in layers:
            if layer and layer.isValid() and isinstance(layer, QgsVectorLayer):
                self.connect_layer(layer)

    def on_layers_removed(self, layer_ids):
        """
        Handle layers being removed from the project
        
        Args:
            layer_ids (list): List of layer IDs that were removed
        """
        QgsMessageLog.logMessage(f"LayerManager: Layers removed from project: {len(layer_ids)}", "BNGAI Plugin", level=0)
        for layer_id in layer_ids:
            if layer_id in self.layer_connections:
                layer = QgsProject.instance().mapLayer(layer_id)
                if layer:
                    self.disconnect_layer(layer)

    def connect_to_existing_layers(self):
        """
        Connect to all existing vector layers in the project.
        This is typically called when the plugin is loaded or when a tab is shown.
        """
        QgsMessageLog.logMessage("LayerManager connecting to existing layers...", "BNGAI Plugin", level=0)
        
        # Get all layers in the project
        layers = QgsProject.instance().mapLayers().values()
        
        # Connect to each vector layer
        for layer in layers:
            if layer and layer.isValid() and isinstance(layer, QgsVectorLayer):
                self.connect_layer(layer)

    def disconnect_all_layers(self):
        """
        Disconnect from all layers.
        This is typically called when the plugin is unloaded or when a tab is hidden.
        """
        QgsMessageLog.logMessage("LayerManager disconnecting from all layers...", "BNGAI Plugin", level=0)
        
        # Create a copy of the keys since we'll be modifying the dictionary
        layer_ids = list(self.layer_connections.keys())
        
        # Disconnect each layer
        for layer_id in layer_ids:
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer:
                self.disconnect_layer(layer)
        
        # Clear all tracking
        self.layer_connections.clear()
        self.current_layer = None
        self.current_feature = None
        self.selection_changed.emit() 