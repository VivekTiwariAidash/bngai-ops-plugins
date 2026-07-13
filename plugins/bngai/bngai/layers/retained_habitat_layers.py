"""
RetainedHabitatLayersManager - Manage Retained Habitat polygon layer
"""
from qgis.core import (QgsProject, QgsMessageLog)
from qgis.PyQt.QtCore import QVariant
import os
from .layer_manager import LayerManager
from .geometry_handler import GeometryHandler


class RetainedHabitatLayersManager:
    """
    Manages a single Retained Habitat polygon layer.
    """
    def __init__(self):
        self.layer_manager = LayerManager()
        self.layer_manager.connect_to_existing_layers()
        QgsMessageLog.logMessage("Initialized RetainedHabitatLayersManager", "BNGAI Plugin", level=0)
        self.project = QgsProject.instance()
        self.root = self.project.layerTreeRoot()
        self.group = None
        self._ensure_group()
        # Attributes based on provided sample
        self.attributes = [
            ('id', QVariant.String),
            ('planRevisionId', QVariant.String),
            ('baseHabitat', QVariant.String),
            ('sizeValue', QVariant.Double),
            ('sizeUnit', QVariant.String),
            ('activityType', QVariant.String),
            ('activityId', QVariant.String),
            ('aidashCode', QVariant.String)
            
        ]
        self.geometry_handler = GeometryHandler()

    def _ensure_group(self):
        """
        Ensure the Retained Habitat group exists.
        """
        self.group = self.root.findGroup("Retained Habitat Layers")
        if not self.group:
            self.group = self.root.addGroup("Retained Habitat Layers")
            QgsMessageLog.logMessage("Created Retained Habitat Layers group", "BNGAI Plugin", level=0)

    def _move_to_group(self, layer):
        """
        Move a layer under the Retained Habitat Layers group.
        """
        if not layer or not self.group:
            return
        layer_node = self.root.findLayer(layer.id())
        if layer_node:
            parent = layer_node.parent()
            self.group.addLayer(layer)
            if parent:
                parent.removeChildNode(layer_node)

    def _apply_polygon_style(self, layer):
        """
        Apply Plan polygon symbology as default style.
        """
        if not layer:
            return
        try:
            qml_path = os.path.join(os.path.dirname(__file__), 'symbology', 'Plan', 'PlanPolygon.qml')
            if os.path.exists(qml_path):
                layer.loadNamedStyle(qml_path)
                layer.triggerRepaint()
                QgsMessageLog.logMessage(f"Applied retained habitat style from {qml_path}", "BNGAI Plugin", level=0)
        except Exception:
            pass
    
    def _apply_line_style(self, layer):
        """Apply Plan watercourse/hedgerow symbology."""
        if not layer:
            return
        try:
            qml_path = os.path.join(os.path.dirname(__file__), 'symbology', 'Plan', 'PlanWatercourseHedgerow.qml')
            if os.path.exists(qml_path):
                layer.loadNamedStyle(qml_path)
                layer.triggerRepaint()
                QgsMessageLog.logMessage(f"Applied retained watercourse/hedgerow style from {qml_path}", "BNGAI Plugin", level=0)
        except Exception:
            pass
    
    def _apply_point_style(self, layer):
        """Apply Plan tree symbology."""
        if not layer:
            return
        try:
            qml_path = os.path.join(os.path.dirname(__file__), 'symbology', 'Plan', 'PlanTree.qml')
            if os.path.exists(qml_path):
                layer.loadNamedStyle(qml_path)
                layer.triggerRepaint()
                QgsMessageLog.logMessage(f"Applied retained tree style from {qml_path}", "BNGAI Plugin", level=0)
        except Exception:
            pass

    def create_layer(self, name="Retained Habitats"):
        """
        Create an empty retained habitat polygon layer.
        """
        layer = self.layer_manager.create_memory_layer(
            name,
            'Polygon',
            crs="EPSG:4326",
            attributes=self.attributes
        )
        if not layer:
            return None
        self._move_to_group(layer)
        self._apply_polygon_style(layer)
        # Enable feature count
        try:
            layer.setCustomProperty("showFeatureCount", True)
            node = self.root.findLayer(layer.id())
            if node:
                node.setCustomProperty("showFeatureCount", True)
        except Exception:
            pass
        return layer
    
    def create_line_layer(self, name="Retained Watercourse/Hedgerow"):
        """Create an empty retained habitat line layer (MultiLineString)."""
        layer = self.layer_manager.create_memory_layer(
            name,
            'MultiLineString',
            crs="EPSG:4326",
            attributes=self.attributes
        )
        if not layer:
            return None
        self._move_to_group(layer)
        self._apply_line_style(layer)
        try:
            layer.setCustomProperty("showFeatureCount", True)
            node = self.root.findLayer(layer.id())
            if node:
                node.setCustomProperty("showFeatureCount", True)
        except Exception:
            pass
        return layer
    
    def create_point_layer(self, name="Retained Tree"):
        """Create an empty retained habitat point layer (MultiPoint)."""
        layer = self.layer_manager.create_memory_layer(
            name,
            'MultiPoint',
            crs="EPSG:4326",
            attributes=self.attributes
        )
        if not layer:
            return None
        self._move_to_group(layer)
        self._apply_point_style(layer)
        try:
            layer.setCustomProperty("showFeatureCount", True)
            node = self.root.findLayer(layer.id())
            if node:
                node.setCustomProperty("showFeatureCount", True)
                # Collapse legend/symbology by default and ensure visibility
                try:
                    node.setExpanded(False)
                except Exception:
                    pass
                try:
                    node.setItemVisibilityChecked(True)
                except Exception:
                    pass
        except Exception:
            pass
        return layer

    def import_from_api(self, plan_id, api_client, org_id, name="Retained Habitats"):
        """
        Fetch retained habitats and populate into point/line/polygon layers.
        Uses the new WFS get_retained_features endpoint which returns GeoJSON FeatureCollection.
        """
        try:
            data = api_client.get_retained_features(plan_id, org_id)
            if not data or data.get("type") != "FeatureCollection":
                QgsMessageLog.logMessage("No retained habitats returned from API", "BNGAI Plugin", level=1)
                return None
            
            features = data.get("features", [])
            if not features:
                QgsMessageLog.logMessage("No retained habitat features in response", "BNGAI Plugin", level=1)
                return None
            
            # Transform GeoJSON FeatureCollection into filtered geometries format for GeometryHandler
            filtered_points = []
            filtered_lines = []
            filtered_polygons = []
            for feature in features:
                if feature.get("type") != "Feature":
                    continue
                geom = feature.get("geometry")
                if not geom or not isinstance(geom, dict) or not geom.get("type"):
                    continue
                
                feat_props = feature.get("properties", {})
                metadata = feat_props.get("metadata", {})
                props = {
                    'id': feature.get('id') or feat_props.get('retainedHabitatId'),
                    'planRevisionId': feat_props.get('planRevisionId'),
                    'baseHabitat': metadata.get('baseHabitat'),
                    'sizeValue': feat_props.get('sizeValue'),
                    'sizeUnit': feat_props.get('sizeUnit'),
                    'activityType': feat_props.get('activityType'),
                    'activityId': feat_props.get('activityId'),
                    'retainedHabitatId': feat_props.get('retainedHabitatId'),
                    'aidashCode': feat_props.get('aidashCode'),
                }
                gtype = geom.get('type')
                rec = {'geometry': geom, 'properties': props}
                if gtype in ('Point', 'MultiPoint'):
                    filtered_points.append(rec)
                elif gtype in ('LineString', 'MultiLineString'):
                    filtered_lines.append(rec)
                elif gtype in ('Polygon', 'MultiPolygon'):
                    filtered_polygons.append(rec)
            
            created = []
            # Points
            if filtered_points:
                point_features = self.geometry_handler.prepare_features_for_layer(
                    filtered_geometries=filtered_points,
                    attributes=self.attributes,
                    geometry_type='points'
                )
                if point_features:
                    pt_layer = self.create_point_layer(name="Retained Tree")
                    if pt_layer:
                        pt_layer.dataProvider().addFeatures(point_features)
                        pt_layer.updateExtents()
                        pt_layer.triggerRepaint()
                        created.append(pt_layer)
                        QgsMessageLog.logMessage(f"Loaded {len(point_features)} retained point features", "BNGAI Plugin", level=0)
            # Lines
            if filtered_lines:
                line_features = self.geometry_handler.prepare_features_for_layer(
                    filtered_geometries=filtered_lines,
                    attributes=self.attributes,
                    geometry_type='lines'
                )
                if line_features:
                    ln_layer = self.create_line_layer(name="Retained Watercourse/Hedgerow")
                    if ln_layer:
                        ln_layer.dataProvider().addFeatures(line_features)
                        ln_layer.updateExtents()
                        ln_layer.triggerRepaint()
                        created.append(ln_layer)
                        QgsMessageLog.logMessage(f"Loaded {len(line_features)} retained line features", "BNGAI Plugin", level=0)
            # Polygons
            if filtered_polygons:
                poly_features = self.geometry_handler.prepare_features_for_layer(
                    filtered_geometries=filtered_polygons,
                    attributes=self.attributes,
                    geometry_type='polygons'
                )
                if poly_features:
                    poly_layer = self.create_layer(name=name)
                    if poly_layer:
                        poly_layer.dataProvider().addFeatures(poly_features)
                        poly_layer.updateExtents()
                        poly_layer.triggerRepaint()
                        created.append(poly_layer)
                        QgsMessageLog.logMessage(f"Loaded {len(poly_features)} retained polygon features", "BNGAI Plugin", level=0)
            
            if not created:
                QgsMessageLog.logMessage("No valid retained habitat features to add", "BNGAI Plugin", level=1)
                return None
            # Return the last created layer (polygon preferred) for backward compatibility
            return created[-1]
        except Exception as e:
            QgsMessageLog.logMessage(f"Error importing retained habitats: {str(e)}", "BNGAI Plugin", level=2)
            return None

