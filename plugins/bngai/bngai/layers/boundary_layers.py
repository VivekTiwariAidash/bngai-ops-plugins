"""
BoundaryLayersManager - Module for managing boundary layers in QGIS
"""
from qgis.core import (QgsProject, QgsMessageLog, QgsFeature, QgsGeometry,
                      QgsSymbol, QgsSimpleLineSymbolLayer, QgsSimpleFillSymbolLayer)
from qgis.PyQt.QtCore import QVariant, Qt
from qgis.PyQt.QtGui import QColor
from .layer_manager import LayerManager
from .layer_types import LayerType, generate_layer_id
import os

class BoundaryLayersManager:
    """
    Manages boundary layers within QGIS for the BNG AI plugin.
    Handles Red Line Boundary (RLB) and other boundary types.
    """
    
    def __init__(self):
        """Initialize the boundary layers manager"""
        self.layer_manager = LayerManager()
        # Connect to existing layers to track selection
        self.layer_manager.connect_to_existing_layers()
        QgsMessageLog.logMessage("Initialized BoundaryLayers", "BNGAI Plugin", level=0)
        self.project = QgsProject.instance()
        self.root = self.project.layerTreeRoot()
        self.boundary_group = None
        
        # Ensure the Boundary Layers group exists
        self._ensure_boundary_group()
        
        # Define standard attributes for boundary layers
        self.boundary_attributes = [
            ('id', QVariant.String),
            ('type', QVariant.String),  # 'rlb', 'site_boundary', etc.
            ('area', QVariant.Double),
            ('perimeter', QVariant.Double),
            ('description', QVariant.String),
            ('notes', QVariant.String)
        ]
    
    def _ensure_boundary_group(self):
        """
        Ensure that the Boundary Layers group exists in the layer tree.
        Creates it if it doesn't exist.
        """
        self.boundary_group = self.root.findGroup("Boundary Layers")
        
        if not self.boundary_group:
            self.boundary_group = self.root.addGroup("Boundary Layers")
            QgsMessageLog.logMessage("Created Boundary Layers group", "BNGAI Plugin", level=0)
    
    def create_rlb_layer(self, project_id, layer_id=None):
        """
        Create a Red Line Boundary (RLB) layer
        
        Args:
            project_id (str): Project ID for layer identification
            layer_id (str, optional): Specific layer ID to use. If None, one will be generated.
            
        Returns:
            QgsVectorLayer: The created vector layer or None if failed
        """
        try:
            # Use provided layer_id if available, otherwise generate one
            layer_id = layer_id or generate_layer_id(project_id, LayerType.RLB)
            layer_name = f"RLB_{project_id}"
            
            layer = self.layer_manager.create_memory_layer(
                layer_name,
                'Polygon',
                crs="EPSG:4326",
                attributes=self.boundary_attributes,
                add_to_group=False  # Don't add to BNG AI group, will be moved to Boundary Layers
            )
            
            if not layer:
                return None
            
            # Set layer ID and other properties
            layer.setCustomProperty("bngai_layer_id", layer_id)
            layer.setCustomProperty("bngai_layer_type", LayerType.RLB.value)
            layer.setCustomProperty("bngai_project_id", project_id)
            
            # Move to boundary group
            self._move_to_boundary_group(layer)
            
            # Apply RLB style
            self._apply_rlb_style(layer)
            
            QgsMessageLog.logMessage(f"Created RLB layer for project: {project_id} with ID: {layer_id}", "BNGAI Plugin", level=0)
            return layer
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error creating RLB layer: {str(e)}", "BNGAI Plugin", level=2)
            return None
    
    def _move_to_boundary_group(self, layer):
        """
        Move a layer from its current group to the Boundary Layers group
        
        Args:
            layer (QgsMapLayer): The layer to move
        """
        if not layer or not self.boundary_group:
            return
        
        layer_id = layer.id()
        layer_node = self.root.findLayer(layer_id)
        
        if layer_node:
            parent = layer_node.parent()
            self.boundary_group.addLayer(layer)
            if parent:
                parent.removeChildNode(layer_node)
                # Clean up empty parent group (e.g., "BNG AI")
                self._cleanup_empty_group(parent)
    
    def _cleanup_empty_group(self, group):
        """
        Remove a layer group if it's empty.
        
        Args:
            group: QgsLayerTreeGroup to check and potentially remove
        """
        if not group:
            return
        
        # Don't remove the root or the Boundary Layers group
        if group == self.root or group == self.boundary_group:
            return
        
        # Check if group is empty (no child layers or groups)
        if len(group.children()) == 0:
            group_name = group.name()
            parent = group.parent()
            if parent:
                parent.removeChildNode(group)
                QgsMessageLog.logMessage(f"Removed empty layer group: {group_name}", "BNGAI Plugin", level=0)
    
    def _apply_rlb_style(self, layer):
        """
        Apply the standard RLB style (red outline)
        
        Args:
            layer (QgsVectorLayer): Layer to style
        """
        if not layer:
            return
        
        # Define RLB style with red outline
        style = {
            'line_color': '#ff0000',  # Red
            'line_width': '2',        # 2 pixels
            'line_style': 'solid',
            'fill_color': '#00000000' # Transparent fill
        }
        
        # Create symbol layers
        outline = QgsSimpleLineSymbolLayer()
        outline.setColor(QColor(style['line_color']))
        outline.setWidth(float(style['line_width']))
        outline.setPenStyle(Qt.SolidLine)
        
        fill = QgsSimpleFillSymbolLayer()
        fill.setColor(QColor(style['fill_color']))
        fill.setStrokeStyle(Qt.NoPen)
        
        # Apply style to layer
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        symbol.changeSymbolLayer(0, fill)
        symbol.appendSymbolLayer(outline)
        
        layer.renderer().setSymbol(symbol)
        layer.triggerRepaint()
    
    def _apply_boundary_style(self, layer):
        """
        Apply QML style to a boundary layer
        
        Args:
            layer (QgsVectorLayer): Layer to style
        """
        if not layer:
            return
            
        # Get the path to the QML file from Plan symbology
        qml_path = os.path.join(os.path.dirname(__file__), 'symbology', 'Plan', 'SiteBoundary.qml')
        
        if os.path.exists(qml_path):
            # Load and apply the style
            layer.loadNamedStyle(qml_path)
            layer.triggerRepaint()
            QgsMessageLog.logMessage(f"Applied boundary style from {qml_path}", "BNGAI Plugin", level=0)
        else:
            QgsMessageLog.logMessage(f"Style file not found: {qml_path}", "BNGAI Plugin", level=2)
    
    def create_boundary_layer(self, name="Site Boundary"):
        """
        Create a layer for site boundary
        
        Args:
            name (str): Name for the layer
            
        Returns:
            QgsVectorLayer: The created vector layer or None if failed
        """
        try:
            # Create a new memory layer with boundary attributes
            layer = self.layer_manager.create_memory_layer(
                name,
                'LineString',
                crs="EPSG:4326",
                attributes=self.boundary_attributes,
                add_to_group=False  # Don't add to BNG AI group, will be moved to Boundary Layers
            )
            
            if not layer:
                return None
            
            # Move to Boundary Layers group
            self._move_to_boundary_group(layer)
            
            # Apply the boundary style
            self._apply_boundary_style(layer)
            
            QgsMessageLog.logMessage(f"Created boundary layer: {name}", "BNGAI Plugin", level=0)
            return layer
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error creating boundary layer: {str(e)}", "BNGAI Plugin", level=2)
            return None
    
    def clear_all_boundary_layers(self):
        """
        Remove all layers in the Boundary Layers group
        
        Returns:
            bool: True if successful, False otherwise
        """
        self._ensure_boundary_group()
        
        try:
            layer_ids = [node.layerId() for node in self.boundary_group.findLayers()]
            self.project.removeMapLayers(layer_ids)
            
            QgsMessageLog.logMessage("Removed all Boundary Layers", "BNGAI Plugin", level=0)
            return True
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error removing Boundary Layers: {str(e)}", "BNGAI Plugin", level=2)
            return False
    
    def import_boundary(self, file_path, name=None):
        """
        Import boundary data from GeoJSON
        
        Args:
            file_path (str): Path to GeoJSON file
            name (str): Optional name for the layer (default: "Imported Site Boundary")
            
        Returns:
            QgsVectorLayer: The imported layer or None if failed
        """
        try:
            if not os.path.exists(file_path):
                QgsMessageLog.logMessage(f"GeoJSON file not found: {file_path}", "BNGAI Plugin", level=2)
                return None
            
            # Use default name if none provided
            if not name:
                name = "Imported Site Boundary"
            
            # Load the GeoJSON
            layer = self.layer_manager.add_vector_layer(name, file_path, "ogr")
            
            if not layer:
                return None
            
            # Move to boundary group
            self._move_to_boundary_group(layer)
            
            # Apply boundary style
            self._apply_boundary_style(layer)
            
            QgsMessageLog.logMessage("Imported boundary data from GeoJSON", "BNGAI Plugin", level=0)
            return layer
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error importing boundary: {str(e)}", "BNGAI Plugin", level=2)
            return None
    
    def load_rlb_from_geometry(self, boundary_geometry, plan_id=None, name="Red Line Boundary"):
        """
        Load Red Line Boundary (RLB) layer from GeoJSON geometry.
        
        Args:
            boundary_geometry (dict): GeoJSON geometry object with 'type' and 'coordinates'
            plan_id (str, optional): Plan ID for layer identification
            name (str): Name for the layer (default: "Red Line Boundary")
            
        Returns:
            QgsVectorLayer: The created layer or None if failed
        """
        try:
            if not boundary_geometry:
                QgsMessageLog.logMessage("No boundary geometry provided", "BNGAI Plugin", level=1)
                return None
            
            # Validate geometry structure
            geom_type = boundary_geometry.get("type")
            coordinates = boundary_geometry.get("coordinates")
            
            if not geom_type or not coordinates:
                QgsMessageLog.logMessage("Invalid boundary geometry: missing type or coordinates", "BNGAI Plugin", level=2)
                return None
            
            QgsMessageLog.logMessage(f"Loading RLB from {geom_type} geometry", "BNGAI Plugin", level=0)
            
            # Generate layer ID if plan_id is provided
            layer_id = None
            if plan_id:
                layer_id = generate_layer_id(plan_id, LayerType.RLB)
            
            # Check if RLB layer already exists for this plan
            if layer_id:
                existing_layer = self._find_existing_rlb_layer(layer_id)
                if existing_layer:
                    QgsMessageLog.logMessage(f"RLB layer already exists for plan: {plan_id}", "BNGAI Plugin", level=0)
                    return existing_layer
            
            # Create memory layer for the boundary
            layer = self.layer_manager.create_memory_layer(
                name,
                'Polygon',
                crs="EPSG:4326",
                attributes=self.boundary_attributes,
                add_to_group=False  # Don't add to BNG AI group, will be moved to Boundary Layers
            )
            
            if not layer:
                QgsMessageLog.logMessage("Failed to create RLB memory layer", "BNGAI Plugin", level=2)
                return None
            
            # Create feature from geometry
            feature = QgsFeature()
            
            # Convert GeoJSON geometry to QgsGeometry
            qgs_geometry = QgsGeometry.fromWkt(self._geojson_to_wkt(boundary_geometry))
            
            if not qgs_geometry or qgs_geometry.isEmpty():
                # Try alternative approach using fromPolygonXY
                qgs_geometry = self._create_geometry_from_geojson(boundary_geometry)
            
            if not qgs_geometry or qgs_geometry.isEmpty():
                QgsMessageLog.logMessage("Failed to create geometry from boundary data", "BNGAI Plugin", level=2)
                return None
            
            feature.setGeometry(qgs_geometry)
            
            # Set attributes
            attrs = [
                plan_id or "",  # id
                "rlb",          # type
                qgs_geometry.area() if qgs_geometry else 0,  # area
                qgs_geometry.length() if qgs_geometry else 0,  # perimeter
                "Red Line Boundary",  # description
                ""  # notes
            ]
            feature.setAttributes(attrs)
            
            # Add feature to layer
            provider = layer.dataProvider()
            provider.addFeatures([feature])
            layer.updateExtents()
            
            # Set layer properties
            if plan_id:
                layer.setCustomProperty("bngai_layer_id", layer_id)
                layer.setCustomProperty("bngai_layer_type", LayerType.RLB.value)
                layer.setCustomProperty("bngai_plan_id", plan_id)
            
            # Move to boundary group
            self._move_to_boundary_group(layer)
            
            # Apply RLB style
            self._apply_rlb_style(layer)
            
            QgsMessageLog.logMessage(f"Successfully loaded RLB layer with {layer.featureCount()} features", "BNGAI Plugin", level=0)
            return layer
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error loading RLB from geometry: {str(e)}", "BNGAI Plugin", level=2)
            import traceback
            QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            return None
    
    def _find_existing_rlb_layer(self, layer_id):
        """
        Find an existing RLB layer by layer ID.
        
        Args:
            layer_id (str): The layer ID to search for
            
        Returns:
            QgsVectorLayer or None
        """
        for layer in self.project.mapLayers().values():
            if layer.customProperty("bngai_layer_id") == layer_id:
                return layer
        return None
    
    def _geojson_to_wkt(self, geojson_geom):
        """
        Convert GeoJSON geometry to WKT string.
        
        Args:
            geojson_geom (dict): GeoJSON geometry object
            
        Returns:
            str: WKT string
        """
        geom_type = geojson_geom.get("type", "")
        coords = geojson_geom.get("coordinates", [])
        
        if geom_type == "Polygon":
            rings = []
            for ring in coords:
                points = ", ".join([f"{c[0]} {c[1]}" for c in ring])
                rings.append(f"({points})")
            return f"POLYGON({', '.join(rings)})"
        elif geom_type == "MultiPolygon":
            polygons = []
            for polygon in coords:
                rings = []
                for ring in polygon:
                    points = ", ".join([f"{c[0]} {c[1]}" for c in ring])
                    rings.append(f"({points})")
                polygons.append(f"({', '.join(rings)})")
            return f"MULTIPOLYGON({', '.join(polygons)})"
        
        return ""
    
    def _create_geometry_from_geojson(self, geojson_geom):
        """
        Create QgsGeometry from GeoJSON geometry using coordinate parsing.
        
        Args:
            geojson_geom (dict): GeoJSON geometry object
            
        Returns:
            QgsGeometry
        """
        from qgis.core import QgsPointXY
        
        geom_type = geojson_geom.get("type", "")
        coords = geojson_geom.get("coordinates", [])
        
        try:
            if geom_type == "Polygon":
                # Create polygon from coordinates
                rings = []
                for ring_coords in coords:
                    points = [QgsPointXY(c[0], c[1]) for c in ring_coords]
                    rings.append(points)
                
                if rings:
                    return QgsGeometry.fromPolygonXY(rings)
                    
            elif geom_type == "MultiPolygon":
                # Create multipolygon from coordinates
                polygons = []
                for polygon_coords in coords:
                    rings = []
                    for ring_coords in polygon_coords:
                        points = [QgsPointXY(c[0], c[1]) for c in ring_coords]
                        rings.append(points)
                    polygons.append(rings)
                
                if polygons:
                    return QgsGeometry.fromMultiPolygonXY(polygons)
        except Exception as e:
            QgsMessageLog.logMessage(f"Error creating geometry: {str(e)}", "BNGAI Plugin", level=2)
        
        return None