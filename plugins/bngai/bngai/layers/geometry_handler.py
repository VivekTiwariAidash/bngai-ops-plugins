"""
GeometryHandler - Module for processing and filtering geometry data for BNG AI plugin
"""
from qgis.core import QgsMessageLog, QgsGeometry, QgsPointXY, QgsFeature, QgsFields, QgsField, QgsWkbTypes
import json
import uuid

class GeometryHandler:
    """
    Handles the processing and filtering of geometry data from API responses
    for use with the layer management classes
    """
    
    def __init__(self):
        """Initialize the geometry handler"""
        QgsMessageLog.logMessage("GeometryHandler initialized", "BNGAI Plugin", level=0)
    
    def _geom_log(self, label, geom):
        """Lightweight geometry diagnostics for debugging."""
        try:
            if not geom:
                QgsMessageLog.logMessage(f"{label}: <None>", "BNGAI Plugin", level=0)
                return
            empty = False
            try:
                empty = geom.isEmpty()
            except Exception:
                empty = True
            wkb_name = None
            try:
                wkb_name = QgsWkbTypes.displayString(geom.wkbType())
            except Exception:
                wkb_name = "<unk>"
            area = None
            try:
                area = geom.area()
            except Exception:
                area = None
            QgsMessageLog.logMessage(f"{label}: type={wkb_name}, empty={empty}, area={area}", "BNGAI Plugin", level=0)
        except Exception:
            pass
    
    def fix_polygon_geometry(self, geom: QgsGeometry, feature_id: str = None) -> QgsGeometry:
        """
        Make a polygon geometry valid and coerce it to Polygon/MultiPolygon.
        - Runs makeValid()
        - If GeometryCollection, extracts polygonal parts and merges them
        - Returns None if no polygonal content remains
        """
        try:
            fid = f"[fid={feature_id}]" if feature_id is not None else ""
            self._geom_log(f"fix_polygon_geometry.before{fid}", geom)
            if not geom or geom.isEmpty():
                QgsMessageLog.logMessage(f"fix_polygon_geometry: empty geometry skipped {fid}", "BNGAI Plugin", level=1)
                return None
            valid = None
            try:
                valid = geom.makeValid()
            except Exception as e:
                QgsMessageLog.logMessage(f"fix_polygon_geometry: makeValid error {fid}: {str(e)}", "BNGAI Plugin", level=1)
                valid = geom  # fall back to original geometry
            if not valid or valid.isEmpty():
                QgsMessageLog.logMessage(f"fix_polygon_geometry: valid is empty -> skip {fid}", "BNGAI Plugin", level=1)
                return None
            self._geom_log(f"fix_polygon_geometry.after_makeValid{fid}", valid)
            try:
                wkb = valid.wkbType()
            except Exception:
                wkb = None
            try:
                is_collection = False
                try:
                    if wkb is not None:
                        is_collection = QgsWkbTypes.flatType(wkb) == QgsWkbTypes.GeometryCollection
                except Exception:
                    is_collection = False
                    try:
                        # Fallback probe
                        _probe = valid.asGeometryCollection()
                        is_collection = _probe is not None
                    except Exception:
                        is_collection = False
                if is_collection:
                    parts = valid.asGeometryCollection()
                    polygon_parts = []
                    for p in parts or []:
                        try:
                            if QgsWkbTypes.geometryType(p.wkbType()) == QgsWkbTypes.PolygonGeometry and not p.isEmpty():
                                polygon_parts.append(p)
                        except Exception:
                            continue
                    QgsMessageLog.logMessage(f"fix_polygon_geometry: collection parts={len(parts or [])}, polygon_parts={len(polygon_parts)} {fid}", "BNGAI Plugin", level=0)
                    if not polygon_parts:
                        QgsMessageLog.logMessage(f"fix_polygon_geometry: no polygonal parts -> skip {fid}", "BNGAI Plugin", level=1)
                        return None
                    merged = None
                    try:
                        merged = QgsGeometry.unaryUnion(polygon_parts)
                    except Exception:
                        merged = None
                    if not merged or merged.isEmpty():
                        try:
                            merged = QgsGeometry.collectGeometry(polygon_parts)
                        except Exception:
                            merged = None
                    if not merged or merged.isEmpty():
                        QgsMessageLog.logMessage(f"fix_polygon_geometry: merge failed -> skip {fid}", "BNGAI Plugin", level=1)
                        return None
                    self._geom_log(f"fix_polygon_geometry.after_merge{fid}", merged)
                    valid = merged
                # Ensure final is polygonal
                if QgsWkbTypes.geometryType(valid.wkbType()) != QgsWkbTypes.PolygonGeometry:
                    QgsMessageLog.logMessage(f"fix_polygon_geometry: final non-polygon type -> skip {fid}", "BNGAI Plugin", level=1)
                    return None
            except Exception as e:
                QgsMessageLog.logMessage(f"fix_polygon_geometry: post-process error {fid}: {str(e)}", "BNGAI Plugin", level=1)
                try:
                    if QgsWkbTypes.geometryType(valid.wkbType()) == QgsWkbTypes.PolygonGeometry:
                        return valid
                except Exception:
                    return None
            QgsMessageLog.logMessage(f"fix_polygon_geometry: success {fid}", "BNGAI Plugin", level=0)
            return valid
        except Exception as e:
            QgsMessageLog.logMessage(f"fix_polygon_geometry: unexpected error: {str(e)}", "BNGAI Plugin", level=2)
            return None
    
    def process_geometries(self, geojson_data):
        """
        Process GeoJSON data and separate geometries by type
        
        Args:
            geojson_data (dict/str): GeoJSON data as dict or JSON string
            
        Returns:
            dict: Dictionary containing separated geometries by type:
                 {'points': [...], 'lines': [...], 'polygons': [...]}
        """
        try:
            # Convert string to dict if needed
            if isinstance(geojson_data, str):
                geojson_data = json.loads(geojson_data)
            
            # Initialize containers for each geometry type
            points = []
            lines = []
            polygons = []
            
            # Check if we have a FeatureCollection or just one Feature
            if 'type' in geojson_data:
                if geojson_data['type'] == 'FeatureCollection' and 'features' in geojson_data:
                    features = geojson_data['features']
                elif geojson_data['type'] == 'Feature' and 'geometry' in geojson_data:
                    features = [geojson_data]
                else:
                    # Maybe just a geometry object
                    features = [{'geometry': geojson_data}]
            else:
                # Assume it's a list of features or geometries
                features = geojson_data if isinstance(geojson_data, list) else [geojson_data]
            
            # Process each feature
            for feature in features:
                if 'geometry' not in feature:
                    QgsMessageLog.logMessage("Feature missing geometry", "BNGAI Plugin", level=1)
                    continue
                
                geometry = feature['geometry']
                properties = feature.get('properties', {})
                
                if 'type' not in geometry:
                    QgsMessageLog.logMessage("Geometry missing type", "BNGAI Plugin", level=1)
                    continue
                
                # Categorize by geometry type
                if geometry['type'] == 'Point' or geometry['type'] == 'MultiPoint':
                    points.append({'geometry': geometry, 'properties': properties})
                elif geometry['type'] == 'LineString' or geometry['type'] == 'MultiLineString':
                    lines.append({'geometry': geometry, 'properties': properties})
                elif geometry['type'] == 'Polygon' or geometry['type'] == 'MultiPolygon':
                    polygons.append({'geometry': geometry, 'properties': properties})
                else:
                    QgsMessageLog.logMessage(f"Unsupported geometry type: {geometry['type']}", "BNGAI Plugin", level=1)
            
            QgsMessageLog.logMessage(
                f"Processed geometries: {len(points)} points, {len(lines)} lines, {len(polygons)} polygons", 
                "BNGAI Plugin", 
                level=0
            )
            
            return {
                'points': points,
                'lines': lines,
                'polygons': polygons
            }
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error processing geometries: {str(e)}", "BNGAI Plugin", level=2)
            return {'points': [], 'lines': [], 'polygons': []}
    
    def create_geojson_from_filtered(self, filtered_geometries, geometry_type):
        """
        Create a GeoJSON FeatureCollection from filtered geometries
        
        Args:
            filtered_geometries (list): List of geometry objects of the same type
            geometry_type (str): Type of geometry ('points', 'lines', or 'polygons')
            
        Returns:
            dict: GeoJSON FeatureCollection
        """
        try:
            features = []
            
            for item in filtered_geometries:
                feature = {
                    'type': 'Feature',
                    'geometry': item['geometry'],
                    'properties': item['properties']
                }
                features.append(feature)
            
            geojson = {
                'type': 'FeatureCollection',
                'features': features
            }
            
            return geojson
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error creating GeoJSON from {geometry_type}: {str(e)}", "BNGAI Plugin", level=2)
            return {'type': 'FeatureCollection', 'features': []}
    
    def prepare_features_for_layer(self, filtered_geometries, attributes=None, geometry_type=None):
        """
        Prepare QGIS features from filtered geometry objects for direct addition to a layer
        
        Args:
            filtered_geometries (list): List of geometry objects
            attributes (list): List of attribute definitions [(name, type), ...]
            geometry_type (str): Type of geometry ('points', 'lines', or 'polygons')
            
        Returns:
            list: List of QgsFeature objects ready to add to a layer
        """
        try:
            features = []
            
            # Create fields based on provided attribute definitions
            fields = QgsFields()
            if attributes:
                for attr_name, attr_type in attributes:
                    fields.append(QgsField(attr_name, attr_type))
            
            # Process each geometry
            processed_count = 0
            added_count = 0
            skipped_count = 0
            for item in filtered_geometries:
                processed_count += 1
                qgs_feature = QgsFeature(fields)
                geometry = item['geometry']
                properties = item['properties']
                # Try to determine a feature identifier for logging
                feature_id = None
                try:
                    fid_val = properties.get('id')
                    feature_id = str(fid_val) if fid_val is not None else None
                except Exception:
                    feature_id = None
                
                # Create QgsGeometry based on geometry type
                qgs_geometry = None
                
                if geometry['type'] == 'Point':
                    coords = geometry['coordinates']
                    point = QgsPointXY(coords[0], coords[1])
                    qgs_geometry = QgsGeometry.fromPointXY(point)
                    
                elif geometry['type'] == 'MultiPoint':
                    points = []
                    for coord in geometry['coordinates']:
                        points.append(QgsPointXY(coord[0], coord[1]))
                    qgs_geometry = QgsGeometry.fromMultiPointXY(points)
                    
                elif geometry['type'] == 'LineString':
                    points = []
                    for coord in geometry['coordinates']:
                        points.append(QgsPointXY(coord[0], coord[1]))
                    qgs_geometry = QgsGeometry.fromPolylineXY(points)
                    
                elif geometry['type'] == 'MultiLineString':
                    lines = []
                    for line_coords in geometry['coordinates']:
                        points = []
                        for coord in line_coords:
                            points.append(QgsPointXY(coord[0], coord[1]))
                        lines.append(points)
                    qgs_geometry = QgsGeometry.fromMultiPolylineXY(lines)
                    
                elif geometry['type'] == 'Polygon':
                    rings = []
                    for ring_coords in geometry['coordinates']:
                        ring_points = []
                        for coord in ring_coords:
                            ring_points.append(QgsPointXY(coord[0], coord[1]))
                        rings.append(ring_points)
                    qgs_geometry = QgsGeometry.fromPolygonXY(rings)
                    
                elif geometry['type'] == 'MultiPolygon':
                    polygons = []
                    for polygon_coords in geometry['coordinates']:
                        rings = []
                        for ring_coords in polygon_coords:
                            ring_points = []
                            for coord in ring_coords:
                                ring_points.append(QgsPointXY(coord[0], coord[1]))
                            rings.append(ring_points)
                        polygons.append(rings)
                    qgs_geometry = QgsGeometry.fromMultiPolygonXY(polygons)
                
                if qgs_geometry:
                    # Ensure polygon geometries are valid to avoid downstream split/edit errors
                    if geometry_type == 'polygons':
                        fixed = self.fix_polygon_geometry(qgs_geometry, feature_id=feature_id)
                        if not fixed:
                            skipped_count += 1
                            try:
                                QgsMessageLog.logMessage(f"prepare_features_for_layer: skipped polygon feature (invalid after fix) fid={feature_id}", "BNGAI Plugin", level=1)
                            except Exception:
                                pass
                            continue
                        qgs_geometry = fixed
                    try:
                        self._geom_log("polygon_final_setGeometry", qgs_geometry)
                    except Exception:
                        pass
                    qgs_feature.setGeometry(qgs_geometry)
                    
                    # Set attributes from properties if they match our field definitions
                    if attributes:
                        for attr_name, _ in attributes:
                            if attr_name == 'clientId':
                                # Auto-generate clientId if not provided or empty
                                existing_client_id = properties.get('clientId')
                                if existing_client_id:
                                    qgs_feature[attr_name] = existing_client_id
                                else:
                                    qgs_feature[attr_name] = str(uuid.uuid4())
                            elif attr_name in properties:
                                value = properties[attr_name]
                                qgs_feature[attr_name] = value
                            else:
                                QgsMessageLog.logMessage(
                                    f"Field: {attr_name} not found in properties for feature: {feature_id} and layer: {geometry_type}", 
                                    "BNGAI Plugin", 
                                    level=1
                                )
                    
                    features.append(qgs_feature)
                    added_count += 1
                else:
                    skipped_count += 1
                    try:
                        QgsMessageLog.logMessage("prepare_features_for_layer: skipped feature due to null geometry", "BNGAI Plugin", level=1)
                    except Exception:
                        pass
            
            try:
                QgsMessageLog.logMessage(
                    f"prepare_features_for_layer: processed={processed_count}, added={added_count}, skipped={skipped_count}",
                    "BNGAI Plugin",
                    level=0
                )
            except Exception:
                pass
            QgsMessageLog.logMessage(f"Prepared {len(features)} features for layer", "BNGAI Plugin", level=0)
            return features
            
        except Exception as e:
            import traceback
            QgsMessageLog.logMessage(f"Error preparing features: {str(e)}", "BNGAI Plugin", level=2)
            QgsMessageLog.logMessage(f"Error traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            return [] 