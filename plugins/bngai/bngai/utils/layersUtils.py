from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsMessageLog, QgsField, QgsProject, QgsCoordinateReferenceSystem, QgsJsonUtils
from qgis.PyQt.QtCore import QVariant
import json
import os

class LayersUtils:
  

    @staticmethod
    def create_vector_layer_from_geojson(geojson_data, name="GeoJSON Layer", crs="EPSG:4326"):
        """Create a vector layer from GeoJSON data
        
        :param geojson_data: GeoJSON data (dictionary or string)
        :type geojson_data: dict or str
        :param name: Layer name
        :type name: str
        :param crs: CRS string (e.g. "EPSG:4326")
        :type crs: str
        
        :returns: Vector layer
        :rtype: QgsVectorLayer
        """
        try:
            # Convert geojson_data to string if it's a dictionary
            if isinstance(geojson_data, dict):
                geojson_str = json.dumps(geojson_data)
            else:
                geojson_str = geojson_data
            
            QgsMessageLog.logMessage(f"Creating layer '{name}' from GeoJSON", "BNGAI Plugin", level=0)
            
            # Save GeoJSON to a temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.geojson', delete=False) as f:
                f.write(geojson_str)
                temp_file = f.name
                
            QgsMessageLog.logMessage(f"Saved GeoJSON to temporary file: {temp_file}", "BNGAI Plugin", level=0)
            
            # Create a new vector layer directly from the GeoJSON file using OGR
            # This handles mixed geometry types automatically
            layer = QgsVectorLayer(temp_file, name, "ogr")
            
            if not layer.isValid():
                QgsMessageLog.logMessage(f"Error creating layer from GeoJSON file", "BNGAI Plugin", level=2)
                # Try alternative approach with memory layer if OGR approach fails
                layer = QgsVectorLayer("None", name, "memory")
                layer.setCrs(QgsCoordinateReferenceSystem(crs))
                
                # Load features from temporary GeoJSON
                source_layer = QgsVectorLayer(temp_file, "temp", "ogr")
                if source_layer.isValid():
                    # Add all fields from source layer
                    provider = layer.dataProvider()
                    attrs = source_layer.fields().toList()
                    provider.addAttributes(attrs)
                    layer.updateFields()
                    
                    # Add all features
                    features = []
                    for feature in source_layer.getFeatures():
                        features.append(feature)
                    
                    provider.addFeatures(features)
                    layer.updateExtents()
                else:
                    QgsMessageLog.logMessage("Failed to create source layer from GeoJSON file", "BNGAI Plugin", level=2)
                    os.unlink(temp_file)
                    return None
            else:
                # Set the CRS explicitly
                layer.setCrs(QgsCoordinateReferenceSystem(crs))
            
            # Delete temporary file
            os.unlink(temp_file)
            
            QgsMessageLog.logMessage(f"Successfully created layer with {layer.featureCount()} features", "BNGAI Plugin", level=0)
            return layer
            
        except Exception as e:
            import traceback
            QgsMessageLog.logMessage(f"Error creating vector layer from GeoJSON: {str(e)}", "BNGAI Plugin", level=2)
            QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            return None

    @staticmethod
    def add_geojson_to_map(geojson_data, name="GeoJSON Layer", crs="EPSG:4326"):
        """Add GeoJSON data to the map as separate vector layers for each geometry type
        
        :param geojson_data: GeoJSON data (dictionary or string)
        :type geojson_data: dict or str
        :param name: Layer name
        :type name: str
        :param crs: CRS string (e.g. "EPSG:4326")
        :type crs: str
        
        :returns: List of added layers
        :rtype: list
        """
        try:
            QgsMessageLog.logMessage(f"Adding GeoJSON layer '{name}' to map", "BNGAI Plugin", level=0)
            
            # Convert geojson_data to string if it's a dictionary
            if isinstance(geojson_data, dict):
                geojson_str = json.dumps(geojson_data)
                parsed_json = geojson_data
            else:
                geojson_str = geojson_data
                parsed_json = json.loads(geojson_str)
            
            # Validate the GeoJSON structure
            if 'type' not in parsed_json or parsed_json['type'] != 'FeatureCollection' or 'features' not in parsed_json:
                QgsMessageLog.logMessage("Invalid GeoJSON structure: missing required fields", "BNGAI Plugin", level=2)
                # Try to fix the structure if possible
                if 'features' not in parsed_json and 'type' in parsed_json and 'coordinates' in parsed_json:
                    # This appears to be a single geometry, wrap it as a feature
                    parsed_json = {
                        "type": "FeatureCollection",
                        "features": [{
                            "type": "Feature",
                            "geometry": parsed_json,
                            "properties": {}
                        }]
                    }
                    geojson_str = json.dumps(parsed_json)
                    QgsMessageLog.logMessage("Fixed GeoJSON: wrapped single geometry as feature", "BNGAI Plugin", level=0)
            
            # Check if features array exists and is not empty
            if 'features' not in parsed_json or not parsed_json['features']:
                QgsMessageLog.logMessage("GeoJSON has no features", "BNGAI Plugin", level=2)
                return []
            
            # Log the number of features
            feature_count = len(parsed_json['features'])
            QgsMessageLog.logMessage(f"GeoJSON contains {feature_count} features", "BNGAI Plugin", level=0)
            
            # Save the GeoJSON to a file for debugging and as fallback
            import tempfile
            import os
            temp_dir = tempfile.gettempdir()
            debug_file = os.path.join(temp_dir, f"bngai_debug_{name.replace(' ', '_')}.geojson")
            
            with open(debug_file, 'w') as f:
                f.write(geojson_str)
                
            QgsMessageLog.logMessage(f"Saved GeoJSON to file for debugging: {debug_file}", "BNGAI Plugin", level=0)
            
            # Create a backup HTML file for manual viewing if needed
            html_file = os.path.join(temp_dir, f"bngai_map_{name.replace(' ', '_')}.html")
            with open(html_file, 'w') as f:
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>BNG AI GeoJSON Viewer</title>
                    <meta charset="utf-8" />
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
                    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
                    <style>
                        #map {{height: 600px;}}
                        body {{padding: 0; margin: 0;}}
                    </style>
                </head>
                <body>
                    <div id="map"></div>
                    <script>
                        var map = L.map('map');
                        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                            maxZoom: 19,
                            attribution: '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap contributors</a>'
                        }}).addTo(map);
                        
                        var geojsonData = {geojson_str};
                        var geojsonLayer = L.geoJSON(geojsonData, {{
                            style: function(feature) {{
                                return {{color: "#ff0000", weight: 3, opacity: 1, fillColor: "#00ff00", fillOpacity: 0.5}};
                            }},
                            pointToLayer: function(feature, latlng) {{
                                return L.circleMarker(latlng, {{
                                    radius: 8,
                                    fillColor: "#ff0000",
                                    color: "#000",
                                    weight: 1,
                                    opacity: 1,
                                    fillOpacity: 0.8
                                }});
                            }}
                        }}).addTo(map);
                        
                        map.fitBounds(geojsonLayer.getBounds());
                    </script>
                </body>
                </html>
                """
                f.write(html_content)
                
            QgsMessageLog.logMessage(f"Created HTML map viewer for backup: {html_file}", "BNGAI Plugin", level=0)
            QgsMessageLog.logMessage(f"If QGIS fails to display layers, open this HTML file in a browser", "BNGAI Plugin", level=0)
            
            # Group features by geometry type
            point_features = []
            line_features = []
            polygon_features = []
            
            for feature in parsed_json['features']:
                if 'geometry' in feature and feature['geometry'] and 'type' in feature['geometry']:
                    geom_type = feature['geometry']['type']
                    if geom_type == 'Point' or geom_type == 'MultiPoint':
                        point_features.append(feature)
                    elif geom_type == 'LineString' or geom_type == 'MultiLineString':
                        line_features.append(feature)
                    elif geom_type == 'Polygon' or geom_type == 'MultiPolygon':
                        polygon_features.append(feature)
            
            QgsMessageLog.logMessage(f"Grouped features: {len(point_features)} points, {len(line_features)} lines, {len(polygon_features)} polygons", "BNGAI Plugin", level=0)
            
            added_layers = []
            
            # Always create separate layers for each geometry type
            if point_features:
                point_layer = LayersUtils._create_layer_for_features(point_features, f"{name} - Points", "Point", crs)
                if point_layer:
                    added_layers.append(point_layer)
                    QgsMessageLog.logMessage(f"Added point layer with {point_layer.featureCount()} features", "BNGAI Plugin", level=0)
            
            if line_features:
                line_layer = LayersUtils._create_layer_for_features(line_features, f"{name} - Lines", "LineString", crs)
                if line_layer:
                    added_layers.append(line_layer)
                    QgsMessageLog.logMessage(f"Added line layer with {line_layer.featureCount()} features", "BNGAI Plugin", level=0)
            
            if polygon_features:
                polygon_layer = LayersUtils._create_layer_for_features(polygon_features, f"{name} - Polygons", "Polygon", crs)
                if polygon_layer:
                    added_layers.append(polygon_layer)
                    QgsMessageLog.logMessage(f"Added polygon layer with {polygon_layer.featureCount()} features", "BNGAI Plugin", level=0)
            
            if not added_layers:
                QgsMessageLog.logMessage("Failed to create any valid layers", "BNGAI Plugin", level=2)
                QgsMessageLog.logMessage(f"GeoJSON file is available at: {debug_file}", "BNGAI Plugin", level=0)
                QgsMessageLog.logMessage("Please manually import using Layer > Add Layer > Add Vector Layer", "BNGAI Plugin", level=0)
                return []
            
            # Force canvas refresh
            try:
                from qgis.utils import iface
                if iface:
                    iface.mapCanvas().refresh()
                    
                    # Try to zoom to all layers
                    extent = None
                    for layer in added_layers:
                        if layer.featureCount() > 0:
                            if extent is None:
                                extent = layer.extent()
                            else:
                                extent.combineExtentWith(layer.extent())
                    
                    if extent:
                        iface.mapCanvas().setExtent(extent)
                        iface.mapCanvas().refresh()
                        QgsMessageLog.logMessage(f"Zoomed to combined layer extent", "BNGAI Plugin", level=0)
            except Exception as e:
                QgsMessageLog.logMessage(f"Error refreshing canvas: {e}", "BNGAI Plugin", level=1)
            
            total_features = sum(layer.featureCount() for layer in added_layers)
            QgsMessageLog.logMessage(f"Successfully added {len(added_layers)} layers with {total_features} total features to map", "BNGAI Plugin", level=0)
            return added_layers
            
        except Exception as e:
            import traceback
            QgsMessageLog.logMessage(f"Error adding GeoJSON layer to map: {str(e)}", "BNGAI Plugin", level=2)
            QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            return []

    @staticmethod
    def _create_layer_for_features(features, name, geometry_type, crs="EPSG:4326"):
        """Create a layer for specific geometry type features
        
        :param features: List of GeoJSON features
        :type features: list
        :param name: Layer name
        :type name: str
        :param geometry_type: Geometry type (Point, LineString, Polygon)
        :type geometry_type: str
        :param crs: CRS string
        :type crs: str
        
        :returns: The created layer or None
        :rtype: QgsVectorLayer or None
        """
        if not features:
            return None
            
        QgsMessageLog.logMessage(f"Creating {geometry_type} layer '{name}' with {len(features)} features", "BNGAI Plugin", level=0)
        
        # Create a temporary GeoJSON file
        import tempfile
        import os
        import json
        
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"bngai_{geometry_type.lower()}_{name.replace(' ', '_')}.geojson")
        
        # Create GeoJSON with only these features
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        with open(temp_file, 'w') as f:
            json.dump(geojson, f)
            
        # Try OGR approach first which usually produces selectable features
        layer = None
        QgsMessageLog.logMessage(f"Attempting to create layer using OGR provider from file: {temp_file}", "BNGAI Plugin", level=0)
        
        # Create vector layer using OGR provider
        ogr_uri = f"{temp_file}|layername=ogr_layer"
        layer = QgsVectorLayer(ogr_uri, name, "ogr")
        
        if not layer or not layer.isValid():
            QgsMessageLog.logMessage(f"OGR provider failed, trying direct file path", "BNGAI Plugin", level=1)
            # Try direct file path
            layer = QgsVectorLayer(temp_file, name, "ogr")
            
        if not layer or not layer.isValid():
            QgsMessageLog.logMessage(f"File-based approaches failed, trying memory provider", "BNGAI Plugin", level=1)
            
            # Fall back to memory provider
            geom_type_str = geometry_type
            if geometry_type == "LineString":
                geom_type_str = "LineString"
            elif geometry_type == "Polygon":
                geom_type_str = "Polygon"
            elif geometry_type == "Point":
                geom_type_str = "Point"
                
            layer = QgsVectorLayer(f"{geom_type_str}?crs={crs}", name, "memory")
            if not layer.isValid():
                QgsMessageLog.logMessage(f"Failed to create memory {geometry_type} layer", "BNGAI Plugin", level=2)
                return None
                
            # Set up fields from all features
            provider = layer.dataProvider()
            field_names = set()
            
            # Collect all field names
            for feature in features:
                if 'properties' in feature and feature['properties']:
                    for field_name in feature['properties'].keys():
                        field_names.add(field_name)
            
            # Add fields to the layer
            fields = []
            for field_name in field_names:
                field = QgsField(field_name, QVariant.String)
                fields.append(field)
                
            if fields:
                provider.addAttributes(fields)
                layer.updateFields()
                
                # Create features
                qgis_features = []
                for feature in features:
                    if 'geometry' not in feature or not feature['geometry']:
                        continue
                        
                    qgis_feature = QgsFeature()
                    
                    # Extract geometry info
                    geom_data = feature['geometry']
                    geom_type = geom_data.get('type')
                    coords = geom_data.get('coordinates')
                    
                    # Convert GeoJSON geometry to WKT
                    wkt = LayersUtils._geojson_to_wkt(geom_type, coords)
                    if not wkt:
                        continue
                    
                    # Create geometry from WKT
                    geometry = QgsGeometry.fromWkt(wkt)
                    if not geometry or not geometry.isGeosValid():
                        continue
                        
                    qgis_feature.setGeometry(geometry)
                    
                    # Set attributes
                    attrs = [None] * len(fields)
                    if 'properties' in feature and feature['properties']:
                        field_indexes = {}
                        for i, field in enumerate(provider.fields()):
                            field_indexes[field.name()] = i
                            
                        for field_name, value in feature['properties'].items():
                            if field_name in field_indexes:
                                attrs[field_indexes[field_name]] = str(value) if value is not None else ""
                                
                    qgis_feature.setAttributes(attrs)
                    qgis_features.append(qgis_feature)
                
                # Add features
                if qgis_features:
                    provider.addFeatures(qgis_features)
                    layer.updateExtents()
                    
                    QgsMessageLog.logMessage(f"Added {len(qgis_features)} features to {geometry_type} layer", "BNGAI Plugin", level=0)
                else:
                    QgsMessageLog.logMessage(f"No features added to {geometry_type} layer", "BNGAI Plugin", level=2)
                    return None
        
        # Set CRS
        layer.setCrs(QgsCoordinateReferenceSystem(crs))
        
        # Explicitly make features selectable
        try:
            from qgis.core import QgsVectorLayer, QgsMapLayerProxyModel
            
            # Ensure the layer is selectable
            layer.setFlags(QgsVectorLayer.LayerFlag.AllFlags)
            
            # Enable selection capability
            if hasattr(layer, 'selectByIds'):
                # Get first feature to test selection
                from qgis.core import QgsFeatureRequest
                first_feature = next(layer.getFeatures(QgsFeatureRequest().setLimit(1)), None)
                if first_feature:
                    layer.selectByIds([first_feature.id()])
                    layer.removeSelection()
                    QgsMessageLog.logMessage("Selection capability tested successfully", "BNGAI Plugin", level=0)
        except Exception as e:
            QgsMessageLog.logMessage(f"Error setting selection capability: {str(e)}", "BNGAI Plugin", level=1)
            
        # Add to project
        QgsProject.instance().addMapLayer(layer)
        
        # Apply extreme styling based on geometry type to ensure visibility
        try:
            from qgis.core import QgsSimpleLineSymbolLayer, QgsSimpleFillSymbolLayer, QgsMarkerSymbol, QgsLineSymbol, QgsFillSymbol
            from qgis.core import QgsUnitTypes, QgsSymbol, QgsWkbTypes, QgsRenderContext, QgsRuleBasedRenderer
            
            if geometry_type == "Point":
                # Create an extra large, highly visible point symbol
                symbol = QgsMarkerSymbol.createSimple({
                    'name': 'circle',
                    'color': '255,0,0,255',  # Pure red
                    'outline_color': '255,255,255,255',  # White outline for contrast
                    'size': '8',  # Very large size
                    'outline_width': '1'
                })
                layer.renderer().setSymbol(symbol)
                
            elif geometry_type == "LineString":
                # Create an extra thick, highly visible line symbol
                symbol = QgsLineSymbol.createSimple({
                    'color': '0,0,255,255',  # Pure blue
                    'width': '2.5',  # Very thick line
                    'line_style': 'solid',
                    'capstyle': 'square'  # Square caps for better visibility
                })
                layer.renderer().setSymbol(symbol)
                
            elif geometry_type == "Polygon":
                # Create a highly visible polygon symbol
                symbol = QgsFillSymbol.createSimple({
                    'color': '0,255,0,150',  # Brighter green with medium transparency
                    'outline_color': '255,0,0,255',  # Red outline for high contrast
                    'outline_width': '1.0',
                    'style': 'solid'
                })
                layer.renderer().setSymbol(symbol)
            
            # Force layer symbols to use map units instead of millimeters if possible
            try:
                renderer = layer.renderer()
                if hasattr(renderer, 'symbol'):
                    symbol = renderer.symbol()
                    if symbol:
                        # Try to set symbol size unit to map units for better visibility
                        if hasattr(symbol, 'setSizeUnit'):
                            symbol.setSizeUnit(QgsUnitTypes.RenderMapUnits)
                        elif hasattr(symbol, 'setWidthUnit'):
                            symbol.setWidthUnit(QgsUnitTypes.RenderMapUnits)
            except Exception as e:
                QgsMessageLog.logMessage(f"Error setting symbol units: {str(e)}", "BNGAI Plugin", level=1)
                
            QgsMessageLog.logMessage(f"Applied extreme styling to {geometry_type} layer", "BNGAI Plugin", level=0)
        except Exception as e:
            QgsMessageLog.logMessage(f"Error applying styling: {str(e)}", "BNGAI Plugin", level=1)
        
        # Ensure layer is completely visible
        layer.setOpacity(1.0)
        
        # Double check renderer is enabled
        layer.setRenderer(layer.renderer())
        
        # Make sure the layer is editable and selectable
        try:
            # Enable editing capability (though we're not actually editing)
            layer.startEditing()
            layer.commitChanges()
            
            # Enable all flags for the layer
            if hasattr(layer, 'setFlags'):
                layer.setFlags(layer.flags() | QgsVectorLayer.LayerFlag.AllFlags)
            
            # Set layer to be selectable in the canvas
            try:
                from qgis.utils import iface
                if iface and iface.layerTreeView():
                    # Try to make layer selectable in the layer tree
                    model = iface.layerTreeView().model()
                    if model:
                        for i in range(model.rowCount()):
                            index = model.index(i, 0)
                            if model.data(index) == name:
                                model.setData(index, Qt.Checked, Qt.CheckStateRole)
                                break
            except Exception as e:
                QgsMessageLog.logMessage(f"Error making layer selectable in UI: {str(e)}", "BNGAI Plugin", level=1)
                
        except Exception as e:
            QgsMessageLog.logMessage(f"Error enabling editing/selection: {str(e)}", "BNGAI Plugin", level=1)
        
        # Ensure layer is enabled in legend
        root = QgsProject.instance().layerTreeRoot()
        tree_layer = root.findLayer(layer.id())
        if tree_layer:
            tree_layer.setItemVisibilityChecked(True)
            QgsMessageLog.logMessage(f"Layer visibility checked in legend", "BNGAI Plugin", level=0)
        
        # Force layer to repaint
        layer.triggerRepaint()
        
        # Try to force canvas to update for this layer
        try:
            from qgis.utils import iface
            if iface and iface.mapCanvas():
                # Try to zoom to layer
                if layer.featureCount() > 0:
                    iface.mapCanvas().zoomToFeatureExtent(layer.extent())
                    QgsMessageLog.logMessage(f"Zoomed to layer extent", "BNGAI Plugin", level=0)
                
                # Set current layer for selection
                iface.setActiveLayer(layer)
                
                # Refresh canvas
                iface.mapCanvas().refresh()
                iface.layerTreeView().refreshLayerSymbology(layer.id())
                
                # Try to flash features to make them more visible
                LayersUtils._flash_layer_features(layer)
                
                QgsMessageLog.logMessage(f"Canvas refreshed and layer flashed", "BNGAI Plugin", level=0)
            else:
                QgsMessageLog.logMessage("iface or mapCanvas not available", "BNGAI Plugin", level=1)
        except Exception as e:
            QgsMessageLog.logMessage(f"Error refreshing layer in canvas: {str(e)}", "BNGAI Plugin", level=1)
        
        return layer

    @staticmethod
    def _flash_layer_features(layer):
        """Flash features to help identify them on map
        
        :param layer: The layer containing features to flash
        :type layer: QgsVectorLayer
        """
        try:
            from qgis.utils import iface
            if not iface or not iface.mapCanvas():
                return
                
            from qgis.core import QgsFeatureRequest
            
            # Get up to 10 features for flashing (to avoid performance issues)
            features = list(layer.getFeatures(QgsFeatureRequest().setLimit(10)))
            if not features:
                return
                
            # Flash features if the method is available
            if hasattr(iface.mapCanvas(), 'flashFeatureIds'):
                feature_ids = [f.id() for f in features]
                iface.mapCanvas().flashFeatureIds(layer, feature_ids)
                QgsMessageLog.logMessage(f"Flashed {len(feature_ids)} features on map", "BNGAI Plugin", level=0)
                
        except Exception as e:
            QgsMessageLog.logMessage(f"Error flashing features: {str(e)}", "BNGAI Plugin", level=1)
            
    @staticmethod
    def create_memory_layer_from_features(features, name="GeoJSON Layer", crs="EPSG:4326"):
        """Create a memory layer from GeoJSON features by manually adding each feature
        
        :param features: List of GeoJSON feature dictionaries
        :type features: list
        :param name: Layer name
        :type name: str
        :param crs: CRS string (e.g. "EPSG:4326")
        :type crs: str
        
        :returns: Vector layer
        :rtype: QgsVectorLayer
        """
        try:
            QgsMessageLog.logMessage(f"Creating memory layer '{name}' directly from {len(features)} features", "BNGAI Plugin", level=0)
            
            # Count features by geometry type for logging
            point_count = 0
            line_count = 0
            polygon_count = 0
            other_count = 0
            
            for feature in features:
                if 'geometry' in feature and feature['geometry'] and 'type' in feature['geometry']:
                    geom_type = feature['geometry']['type']
                    if geom_type == 'Point' or geom_type == 'MultiPoint':
                        point_count += 1
                    elif geom_type == 'LineString' or geom_type == 'MultiLineString':
                        line_count += 1
                    elif geom_type == 'Polygon' or geom_type == 'MultiPolygon':
                        polygon_count += 1
                    else:
                        other_count += 1
            
            QgsMessageLog.logMessage(f"Feature counts: Points={point_count}, Lines={line_count}, Polygons={polygon_count}, Other={other_count}", "BNGAI Plugin", level=0)
            
            if (point_count + line_count + polygon_count + other_count) == 0:
                QgsMessageLog.logMessage("No valid features found", "BNGAI Plugin", level=2)
                return None
                
            # Create a generic layer that can handle multiple geometry types
            layer = QgsVectorLayer("MultiGeometry?crs=" + crs, name, "memory")
            if not layer.isValid():
                QgsMessageLog.logMessage("Failed to create memory layer with MultiGeometry type, trying NoGeometry", "BNGAI Plugin", level=1)
                # Fallback to NoGeometry if MultiGeometry doesn't work
                layer = QgsVectorLayer("NoGeometry?crs=" + crs, name, "memory")
                if not layer.isValid():
                    QgsMessageLog.logMessage("Failed to create memory layer", "BNGAI Plugin", level=2)
                    return None
            
            QgsMessageLog.logMessage(f"Creating mixed geometry layer with {len(features)} total features", "BNGAI Plugin", level=0)
                
            # Set up fields from all features' properties
            provider = layer.dataProvider()
            field_names = set()
            
            # Collect all field names from all features
            for feature in features:
                if 'properties' in feature and feature['properties']:
                    for field_name in feature['properties'].keys():
                        field_names.add(field_name)
            
            # Add fields to the layer
            fields = []
            for field_name in field_names:
                field = QgsField(field_name, QVariant.String)
                fields.append(field)
                
            if fields:
                provider.addAttributes(fields)
                layer.updateFields()
                
                # Build a map of field indexes
                field_indexes = {}
                for i, field in enumerate(provider.fields()):
                    field_indexes[field.name()] = i
                
                # Now add each feature regardless of geometry type
                qgis_features = []
                
                for json_feature in features:
                    if 'geometry' not in json_feature or not json_feature['geometry']:
                        continue
                        
                    # Create a new feature
                    qgis_feature = QgsFeature()
                    
                    # Extract geometry info
                    geom_data = json_feature['geometry']
                    geom_type = geom_data.get('type')
                    coords = geom_data.get('coordinates')
                    
                    # Convert GeoJSON geometry to WKT
                    wkt = LayersUtils._geojson_to_wkt(geom_type, coords)
                    if not wkt:
                        QgsMessageLog.logMessage(f"Failed to convert geometry to WKT for type {geom_type}", "BNGAI Plugin", level=2)
                        continue
                    
                    # Create geometry from WKT
                    geometry = QgsGeometry.fromWkt(wkt)
                    if not geometry or not geometry.isGeosValid():
                        QgsMessageLog.logMessage(f"Invalid geometry from WKT: {wkt[:100]}...", "BNGAI Plugin", level=2)
                        continue
                        
                    qgis_feature.setGeometry(geometry)
                    
                    # Set attributes
                    attrs = [None] * len(fields)
                    if 'properties' in json_feature and json_feature['properties']:
                        for field_name, value in json_feature['properties'].items():
                            if field_name in field_indexes:
                                attrs[field_indexes[field_name]] = str(value) if value is not None else ""
                                
                    qgis_feature.setAttributes(attrs)
                    qgis_features.append(qgis_feature)
                
                # Add all features at once for better performance
                if qgis_features:
                    provider.addFeatures(qgis_features)
                    layer.updateExtents()
                    QgsMessageLog.logMessage(f"Added {len(qgis_features)} features to layer", "BNGAI Plugin", level=0)
                else:
                    QgsMessageLog.logMessage("No features added to layer", "BNGAI Plugin", level=2)
                    return None
            else:
                QgsMessageLog.logMessage("No fields found in features", "BNGAI Plugin", level=2)
                return None
            
            return layer
            
        except Exception as e:
            import traceback
            QgsMessageLog.logMessage(f"Error creating memory layer: {str(e)}", "BNGAI Plugin", level=2)
            QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            return None

    @staticmethod
    def _geojson_to_wkt(geom_type, coords):
        """Convert GeoJSON geometry to WKT format
        
        :param geom_type: GeoJSON geometry type (Point, LineString, Polygon, etc.)
        :type geom_type: str
        :param coords: GeoJSON coordinates
        :type coords: list
        
        :returns: WKT string
        :rtype: str
        """
        try:
            if geom_type == 'Point':
                return f"POINT({coords[0]} {coords[1]})"
                
            elif geom_type == 'LineString':
                points = [f"{p[0]} {p[1]}" for p in coords]
                return f"LINESTRING({', '.join(points)})"
                
            elif geom_type == 'Polygon':
                rings = []
                for ring in coords:
                    points = [f"{p[0]} {p[1]}" for p in ring]
                    rings.append(f"({', '.join(points)})")
                return f"POLYGON({', '.join(rings)})"
                
            elif geom_type == 'MultiPoint':
                points = [f"({p[0]} {p[1]})" for p in coords]
                return f"MULTIPOINT({', '.join(points)})"
                
            elif geom_type == 'MultiLineString':
                lines = []
                for line in coords:
                    points = [f"{p[0]} {p[1]}" for p in line]
                    lines.append(f"({', '.join(points)})")
                return f"MULTILINESTRING({', '.join(lines)})"
                
            elif geom_type == 'MultiPolygon':
                polygons = []
                for poly in coords:
                    rings = []
                    for ring in poly:
                        points = [f"{p[0]} {p[1]}" for p in ring]
                        rings.append(f"({', '.join(points)})")
                    polygons.append(f"({', '.join(rings)})")
                return f"MULTIPOLYGON({', '.join(polygons)})"
                
            else:
                QgsMessageLog.logMessage(f"Unsupported geometry type: {geom_type}", "BNGAI Plugin", level=2)
                return None
                
        except Exception as e:
            QgsMessageLog.logMessage(f"Error converting GeoJSON to WKT: {str(e)}", "BNGAI Plugin", level=2)
            return None

    @staticmethod
    def create_line_layer_from_geojson(geojson_data, name="Lines Layer", crs="EPSG:4326"):
        """Create a memory layer specifically for line geometries from GeoJSON data
        
        :param geojson_data: GeoJSON data (dictionary or string)
        :type geojson_data: dict or str
        :param name: Layer name
        :type name: str
        :param crs: CRS string (e.g. "EPSG:4326")
        :type crs: str
        
        :returns: Line vector layer
        :rtype: QgsVectorLayer
        """
        try:
            QgsMessageLog.logMessage(f"Creating line layer '{name}' from GeoJSON", "BNGAI Plugin", level=0)
            
            # Convert geojson_data to dictionary if it's a string
            if isinstance(geojson_data, str):
                geojson_dict = json.loads(geojson_data)
            else:
                geojson_dict = geojson_data
            
            # Extract line features only
            line_features = []
            if 'type' in geojson_dict and geojson_dict['type'] == 'FeatureCollection' and 'features' in geojson_dict:
                for feature in geojson_dict['features']:
                    if 'geometry' in feature and 'type' in feature['geometry']:
                        if feature['geometry']['type'] in ['LineString', 'MultiLineString']:
                            line_features.append(feature)
            
            if not line_features:
                QgsMessageLog.logMessage("No line features found in GeoJSON", "BNGAI Plugin", level=1)
                return None
                
            QgsMessageLog.logMessage(f"Found {len(line_features)} line features", "BNGAI Plugin", level=0)
            
            # Create a memory layer for lines
            layer = QgsVectorLayer("LineString?crs=" + crs, name, "memory")
            
            if not layer.isValid():
                QgsMessageLog.logMessage("Failed to create memory layer", "BNGAI Plugin", level=2)
                return None
                
            # Add fields from the first feature with properties
            provider = layer.dataProvider()
            fields_added = False
            field_names = []
            
            for feature in line_features:
                if 'properties' in feature and feature['properties']:
                    fields = []
                    for name, value in feature['properties'].items():
                        fields.append(QgsField(name, QVariant.String))
                        field_names.append(name)
                        
                    provider.addAttributes(fields)
                    layer.updateFields()
                    fields_added = True
                    break
                    
            if not fields_added:
                QgsMessageLog.logMessage("No properties found in features, creating layer without attributes", "BNGAI Plugin", level=1)
            
            # Add features to the layer
            features_added = 0
            for feature_json in line_features:
                if 'geometry' not in feature_json or not feature_json['geometry']:
                    continue
                    
                # Create a new feature
                feature = QgsFeature()
                
                # Convert geometry from GeoJSON to WKT
                geom_type = feature_json['geometry']['type']
                coords = feature_json['geometry']['coordinates']
                wkt = LayersUtils._geojson_to_wkt(geom_type, coords)
                
                if not wkt:
                    continue
                    
                # Create geometry from WKT
                geometry = QgsGeometry.fromWkt(wkt)
                
                if not geometry or not geometry.isGeosValid():
                    continue
                    
                feature.setGeometry(geometry)
                
                # Set attributes if we have fields
                if fields_added and 'properties' in feature_json and feature_json['properties']:
                    attrs = [None] * len(field_names)
                    
                    for i, name in enumerate(field_names):
                        if name in feature_json['properties']:
                            attrs[i] = str(feature_json['properties'][name])
                            
                    feature.setAttributes(attrs)
                
                # Add feature to layer
                provider.addFeature(feature)
                features_added += 1
                
            if features_added > 0:
                # Update the layer's extent
                layer.updateExtents()
                
                # Apply distinctive styling to lines
                from qgis.core import QgsLineSymbol
                symbol = QgsLineSymbol.createSimple({
                    'color': '0,0,255,255',  # Blue
                    'width': '1.5',  # Thicker line
                    'line_style': 'solid'
                })
                layer.renderer().setSymbol(symbol)
                
                QgsMessageLog.logMessage(f"Successfully created line layer with {features_added} features", "BNGAI Plugin", level=0)
                return layer
            else:
                QgsMessageLog.logMessage("No features added to layer", "BNGAI Plugin", level=2)
                return None
                
        except Exception as e:
            import traceback
            QgsMessageLog.logMessage(f"Error creating line layer from GeoJSON: {str(e)}", "BNGAI Plugin", level=2)
            QgsMessageLog.logMessage(f"Traceback: {traceback.format_exc()}", "BNGAI Plugin", level=2)
            return None

    @staticmethod
    def geojson_to_wkt(geojson_data):
        """
        Convert GeoJSON geometry to WKT format.
        
        Args:
            geojson_data (dict): GeoJSON geometry object
            
        Returns:
            str: WKT representation of the geometry or None if conversion fails
        """
        try:
            if not geojson_data:
                return None
                
            geom_type = geojson_data.get('type', '').upper()
            coordinates = geojson_data.get('coordinates', [])
            
            if not geom_type or not coordinates:
                return None
            
            if geom_type == 'POINT':
                return f"POINT({coordinates[0]} {coordinates[1]})"
                
            elif geom_type == 'LINESTRING':
                points = [f"{x} {y}" for x, y in coordinates]
                return f"LINESTRING({', '.join(points)})"
                
            elif geom_type == 'POLYGON':
                rings = []
                for ring in coordinates:
                    points = [f"{x} {y}" for x, y in ring]
                    rings.append(f"({', '.join(points)})")
                return f"POLYGON({', '.join(rings)})"
                
            elif geom_type == 'MULTIPOLYGON':
                polygons = []
                for polygon in coordinates:
                    rings = []
                    for ring in polygon:
                        points = [f"{x} {y}" for x, y in ring]
                        rings.append(f"({', '.join(points)})")
                    polygons.append(f"({', '.join(rings)})")
                return f"MULTIPOLYGON({', '.join(polygons)})"
                
            else:
                QgsMessageLog.logMessage(f"Unsupported geometry type: {geom_type}", "BNGAI Plugin", level=2)
                return None
                
        except Exception as e:
            QgsMessageLog.logMessage(f"Error converting GeoJSON to WKT: {str(e)}", "BNGAI Plugin", level=2)
            return None
