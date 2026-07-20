from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QFileDialog, QLabel, QComboBox, QCheckBox, \
    QMessageBox
from qgis.core import QgsVectorLayer, QgsProject, QgsVectorFileWriter, QgsWkbTypes
import os
import json
import glob

import geopandas as gpd
from rtree import index
import rasterio as rio
import fiona
import pandas as pd
import numpy as np
from rasterio.mask import mask
from rasterio.features import geometry_mask
import rasterio


def find_all_files_of_type(PATH, prefix="", type='tif'):
    """
    Find all files of a given type within a directory, optionally filtered by a prefix.

    Args:
        PATH (str): The directory path to search in.
        prefix (str, optional): The prefix to filter files. Defaults to "".
        type (str, optional): The file extension/type to search for. Defaults to 'tif'.

    Returns:
        list: A list of file paths matching the criteria.
    """
    result = [y for x in os.walk(PATH) for y in glob.glob(os.path.join(x[0], f'*{prefix}*.{type}'))]
    return result


class BNGAILabelling(QDialog):
    def __init__(self, iface):
        """
        Initialize the BNGAILabelling dialog with a QGIS interface reference.

        Args:
            iface: The QGIS interface instance.
        """
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.config = self.load_configuration()
        self.loaded_gdf = None

        # Set up the UI
        self.setWindowTitle("BNGAI Labelling")
        self.setMinimumSize(400, 400)

        layout = QVBoxLayout()
        self.setLayout(layout)
        # ── Plugin Logo ───────────────────────────────────────────────────────
        from qgis.PyQt.QtWidgets import QLabel
        from qgis.PyQt.QtGui import QPixmap
        from qgis.PyQt.QtCore import Qt
        self.logo_label = QLabel()
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(plugin_dir, "icon_large.png")
        pixmap = QPixmap(logo_path)
        self.logo_label.setPixmap(pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.logo_label)
        # ── End Logo ──────────────────────────────────────────────────────────


        # Job Type UI
        self.job_type_label = QLabel("Job Type:")
        self.job_type_combo_box = QComboBox()
        self.job_type_combo_box.addItems(["Convert shapes", "Habitat Labelling"])
        self.job_type_combo_box.setCurrentIndex(1)  # Set default to "Merge shapes"
        self.job_type_combo_box.currentTextChanged.connect(self.update_ui)

        # Conversion Type UI
        self.conversion_type_label = QLabel("Conversion Type:")
        self.conversion_type_combo_box = QComboBox()
        self.conversion_type_combo_box.addItems(["GeoPackage to Shapefile", "Shapefile to GeoPackage"])

        # Input file UI
        self.input_label = QLabel("RAW OS Folder:")
        self.input_line_edit = QLineEdit()
        self.input_line_edit.setPlaceholderText("Containing .gpkg")
        self.input_line_edit.setReadOnly(True)
        self.input_browse_button = QPushButton("Browse")
        self.input_browse_button.clicked.connect(self.select_input_folder)
        
        # Output folder UI
        self.image_label = QLabel("NIR Image Path:")
        self.image_line_edit = QLineEdit()
        self.image_line_edit.setPlaceholderText("path of NIR imagery(optional)")
        self.image_line_edit.setReadOnly(True)
        self.image_browse_button = QPushButton("Browse")
        self.image_browse_button.clicked.connect(self.select_image_folder)

        # Output folder UI
        self.output_label = QLabel("Output Folder:")
        self.output_line_edit = QLineEdit()
        self.output_line_edit.setReadOnly(True)
        self.output_browse_button = QPushButton("Browse")
        self.output_browse_button.clicked.connect(self.select_output_folder)
        
        # Merge specific UI
        # self.input_file_type_label = QLabel("Input File Type:")
        # self.input_file_type_combo_box = QComboBox()
        # self.input_file_type_combo_box.addItems(["gpkg", "shp"])
        #
        # self.output_file_type_label = QLabel("Output File Type:")
        # self.output_file_type_combo_box = QComboBox()
        # self.output_file_type_combo_box.addItems(["gpkg", "shp"])

        # Add Process Toggle Button
        # self.process_toggle_button = QCheckBox("Pre-label")
        # self.process_toggle_button.setToolTip("Toggle on to create processed output.")

        self.convert_button = QPushButton("Execute")
        self.convert_button.clicked.connect(self.execute_job)

        # Add widgets to layout
        layout.addWidget(self.job_type_label)
        layout.addWidget(self.job_type_combo_box)
        layout.addWidget(self.conversion_type_label)
        layout.addWidget(self.conversion_type_combo_box)
        layout.addWidget(self.input_label)
        layout.addWidget(self.input_line_edit)
        layout.addWidget(self.input_browse_button)
        layout.addWidget(self.image_label)
        layout.addWidget(self.image_line_edit)
        layout.addWidget(self.image_browse_button)
        layout.addWidget(self.output_label)
        layout.addWidget(self.output_line_edit)
        layout.addWidget(self.output_browse_button)
        # layout.addWidget(self.input_file_type_label)
        # layout.addWidget(self.input_file_type_combo_box)
        # layout.addWidget(self.output_file_type_label)
        # layout.addWidget(self.output_file_type_combo_box)
        # layout.addWidget(self.process_toggle_button)
        layout.addWidget(self.convert_button)

        # Initialize UI
        self.update_ui()  # Ensure the UI reflects the default selection

    def load_configuration(self):
        """
        Load configuration settings for processing.

        Returns:
            dict: A dictionary containing configuration settings.
        """
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(plugin_dir, 'config', 'rules.json')
        with open(config_path, 'r') as f:
            self.rules = json.load(f)
        return {
            "columns_to_combine": ["theme", "description", "	oslandcovertiera", "oslandcovertierb",
                                   "oslandusetiera"],
            "new_column_name": "habitat",
            "delimiter": ";",
            "dissolve_column": "habitat",
            "specific_dissolve_values": [
                'Transport;Central Reservation;Made;Made Sealed;Transport: Road, Track Or Path',
                'Transport;Made Surface;Made;Made Sealed;Transport: Rail',
                'Transport;Made Surface;Made;Made Unsealed;Transport: Rail',
                'Transport;Path And Steps;Made;Made Sealed;Transport: Road, Track Or Path',
                'Transport;Path;Made;Made Sealed;Transport: Road, Track Or Path',
                'Transport;Path;Made;Made Unknown;Transport: Road, Track Or Path',
                'Transport;Path;Made;Made Unsealed;Transport: Road, Track Or Path',
                'Transport;Pavement;Made;Made Sealed;Transport: Road, Track Or Path',
                'Transport;Road;Made;Made Sealed;Transport: Road, Track Or Path',
                'Transport;Road;Made;Made Unsealed;Transport: Road, Track Or Path',
                'Transport;Roofed Path;Constructed;Structure;Transport: Road, Track Or Path',
                'Transport;Track;Unmade;Unmade;Transport: Road, Track Or Path',
                'Transport;Traffic Calming;Made;Made Sealed;Transport: Road, Track Or Path',
                'Transport;Transport Curtilage;Open Vegetation;Bare Earth Or Grass;Transport: Rail',
                'Transport;Transport Curtilage;Open Vegetation;Bare Earth Or Grass;Transport: Road, Track Or Path',
                'Transport;Transport Curtilage;Trees;Non-Coniferous Trees,Scrub;Transport: Rail',
            ],
            "output_path": ""
        }

    def update_ui(self):
        """
        Update the UI elements based on the selected job type.
        """
        job_type = self.job_type_combo_box.currentText()
        if job_type == "Convert shapes":
            self.input_line_edit.setPlaceholderText("")
            self.conversion_type_label.setVisible(True)
            self.conversion_type_combo_box.setVisible(True)
            self.image_label.setVisible(False)
            self.image_line_edit.setVisible(False)
            self.image_browse_button.setVisible(False)
            # self.input_file_type_label.setVisible(False)
            # self.input_file_type_combo_box.setVisible(False)
            # self.output_file_type_label.setVisible(False)
            # self.output_file_type_combo_box.setVisible(False)
            # self.process_toggle_button.setVisible(False)
        elif job_type == "Habitat Labelling":
            self.input_line_edit.setPlaceholderText("Containing .gpkg")
            self.conversion_type_label.setVisible(False)
            self.conversion_type_combo_box.setVisible(False)
            self.image_label.setVisible(True)
            self.image_line_edit.setVisible(True)
            self.image_browse_button.setVisible(True)
            # self.input_file_type_label.setVisible(True)
            # self.input_file_type_combo_box.setVisible(True)
            # self.output_file_type_label.setVisible(True)
            # self.output_file_type_combo_box.setVisible(True)
            # self.process_toggle_button.setVisible(True)

    def select_input_folder(self):
        """
        Open a dialog to select the input folder and update the UI.
        """
        input_dir = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if input_dir:
            self.input_line_edit.setText(input_dir)
    
    def select_image_folder(self):
        """
        Open a dialog to select the image folder and update the UI.
        """
        image_dir = QFileDialog.getOpenFileName(self, "Select Image Folder")
        print("image_dir: ",image_dir)
        if image_dir:
            self.image_line_edit.setText(image_dir[0])

    @staticmethod
    def check_conditions(row, conditions):
        '''
        check a row againts a single rule condition which has
        AND operations
        '''
        for condition in conditions:
            column = condition['column'].lower()
            if isinstance(condition.get('value'), str):
                value = condition.get('value').lower()
            else:
                value = condition.get('value')
            operator = condition.get('operator', '==')

            if operator == '==':
                if row[column] != value:
                    return False
            elif operator == '!=':
                if row[column] == value:
                    return False
            elif operator == '<':
                if row[column] >= value:
                    return False
            elif operator == '>':
                if row[column] <= value:
                    return False
        return True  # All conditions are satisfied

    @staticmethod
    def habitat_labelling(row, rules):
        '''
        check a rule against all code condtions
        '''
        for code, condition_sets in rules.items():
            for condition_set in condition_sets:
                if BNGAILabelling.check_conditions(row, condition_set['conditions']):
                    return code
        return None

    @staticmethod
    def sealed_surface_present(row):
        if (row['theme'] == 'buildings') or (row['oslandcovertiera'] == 'made' and row['oslandcovertierb'] == 'made sealed'):
            return True
        return False

    @staticmethod
    def min_distance_to_subset_optimized(gdf, subset):
        """
        Optimized function to calculate the minimum distance from each row in `gdf`
        to the nearest centroid in `subset`.

        Parameters:
            gdf (GeoDataFrame): The main GeoDataFrame.
            subset (GeoDataFrame): The subset GeoDataFrame.

        Returns:
            Series: A Series containing the minimum distances.
        """
        # Precompute centroids for the subset
        subset_centroids = subset['centroid'].tolist()

        # Create a spatial index for the subset centroids
        idx = index.Index()
        for i, centroid in enumerate(subset_centroids):
            if centroid:
                idx.insert(i, centroid.bounds)

        # Function to calculate minimum distance for a single row
        def calculate_min_distance(row):
            if not row['centroid']: return -1
            if row['sealed_surface']: return 0
            # Find the nearest centroid using the spatial index
            nearest_indices = list(idx.nearest(row['centroid'].bounds, 1))
            if not nearest_indices:
                return -1
            nearest_centroid = subset_centroids[nearest_indices[0]]
            return round(row['centroid'].distance(nearest_centroid))

        # Apply the function to the entire GeoDataFrame
        return round(gdf.apply(calculate_min_distance, axis=1))


    def select_output_folder(self):
        """
        Open a dialog to select the output folder and update the UI.
        """
        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if output_dir:
            self.output_line_edit.setText(output_dir)

    def execute_job(self):
        """
        Execute the selected job (conversion or merging) and optionally process the data.
        """
        job_type = self.job_type_combo_box.currentText()
        if job_type == "Convert shapes":
            self.convert_files()
        elif job_type == "Habitat Labelling":
            self.merge_files()
            self.process_data()
            self.show_notification("habitat labelling done", "shape files are saved in the output folder")

    def convert_files(self):
        """
        Convert files between GeoPackage and Shapefile formats based on the selected conversion type.
        """
        input_dir = self.input_line_edit.text()
        output_dir = self.output_line_edit.text()
        conversion_type = self.conversion_type_combo_box.currentText()

        if not input_dir or not output_dir:
            return

        self.convert_folder(input_dir, output_dir, conversion_type)

    def convert_gpkg_to_shp(self, gpkg_file, output_dir):
        """
        Convert a GeoPackage file to separate Shapefile formats for the available geometries (polylines, polygons, and points).

        Args:
            gpkg_file (str): The path to the GeoPackage file.
            output_dir (str): The directory to save the converted Shapefiles.
        """
        # Load the GeoPackage file
        print("gpkg file name:",gpkg_file)
        layer_source = f"{gpkg_file}|layername="
        base_name = os.path.splitext(os.path.basename(gpkg_file))[0]
        # Remove unwanted substrings from base_name
        for unwanted in ['_point', '_polygon', '_polyline']:
            base_name = base_name.replace(unwanted, "")
        print("base name: ",base_name)

        # Open the GeoPackage to get the layers
        layers = QgsVectorLayer(gpkg_file, '', 'ogr')

        # Check if the layers are loaded
        if not layers.isValid():
            print(f"Failed to load {gpkg_file}")
            return

        # Initialize flags to track presence of each geometry type
        has_polygons = False
        has_polylines = False
        has_points = False

        # Iterate through each layer in the GeoPackage
        for layer_name in layers.dataProvider().subLayers():
            name = layer_name.split('!!::!!')[1]
            full_path = layer_source + name
            layer = QgsVectorLayer(full_path, name, "ogr")

            # Check layer validity
            if not layer.isValid():
                print(f"Layer {name} is not valid.")
                continue

            # Determine the geometry type and set flags
            geom_type = layer.geometryType()
            if geom_type == QgsWkbTypes.LineGeometry:
                geom_label = 'polyline'
                has_polylines = True
            elif geom_type == QgsWkbTypes.PolygonGeometry:
                geom_label = 'polygon'
                has_polygons = True
            elif geom_type == QgsWkbTypes.PointGeometry:
                geom_label = 'point'
                has_points = True
            else:
                # Skip any layer that is not a polygon, polyline, or point
                continue

            # Set unique output file name based on geometry type and layer name
            output_file = os.path.join(output_dir, f"{base_name}_{geom_label}.shp")

            # Write the layer to Shapefile
            QgsVectorFileWriter.writeAsVectorFormat(
                layer,
                output_file,
                "UTF-8",
                layer.crs(),
                "ESRI Shapefile"
            )

            # Load the converted layer into the QGIS project
            shp_layer = QgsVectorLayer(output_file, os.path.splitext(os.path.basename(output_file))[0], "ogr")
            QgsProject.instance().addMapLayer(shp_layer)
            print(f"Converted {name} to {output_file}")

        # Inform user about missing geometries (optional)
        if not has_polygons:
            print("No polygon layers found in the GeoPackage; no polygon Shapefile created.")
        if not has_polylines:
            print("No polyline layers found in the GeoPackage; no polyline Shapefile created.")
        if not has_points:
            print("No point layers found in the GeoPackage; no point Shapefile created.")

    def convert_shp_to_gpkg(self, shp_file, output_dir):
        """
        Convert a Shapefile to GeoPackage format.

        Args:
            shp_file (str): The path to the Shapefile.
            output_dir (str): The directory to save the converted GeoPackage.
        """
        shp_layer = QgsVectorLayer(shp_file, os.path.splitext(os.path.basename(shp_file))[0], "ogr")
        if not shp_layer.isValid():
            return
        input_crs = shp_layer.crs()
        output_file = os.path.join(output_dir, os.path.basename(shp_file).replace(".shp", ".gpkg"))
        QgsVectorFileWriter.writeAsVectorFormat(shp_layer, output_file, "UTF-8", input_crs, "GPKG")
        gpkg_layer = QgsVectorLayer(output_file, os.path.splitext(os.path.basename(output_file))[0], "ogr")
        QgsProject.instance().addMapLayer(gpkg_layer)

    def convert_folder(self, input_dir, output_dir, conversion_type):
        """
        Convert all files in a directory based on the selected conversion type.

        Args:
            input_dir (str): The directory containing the input files.
            output_dir (str): The directory to save the converted files.
            conversion_type (str): The type of conversion (GeoPackage to Shapefile or vice versa).
        """
        if conversion_type == "GeoPackage to Shapefile":
            files = find_all_files_of_type(input_dir, type='gpkg')
        elif conversion_type == "Shapefile to GeoPackage":
            files = find_all_files_of_type(input_dir, type='shp')

        for file in files:
            filename = os.path.basename(file)
            folder_name = os.path.dirname(file)
            folder_name = os.path.basename(folder_name)
            output_path = file.replace(input_dir, output_dir)
            output_path = output_path.replace(filename, '')
            os.makedirs(output_path, exist_ok=True)
            if conversion_type == "GeoPackage to Shapefile":
                self.convert_gpkg_to_shp(file, output_path)
            elif conversion_type == "Shapefile to GeoPackage":
                self.convert_shp_to_gpkg(file, output_path)

    def check_if_all_polygons(self, shp):
        """
        Check if all geometries in a shapefile are polygons.

        Args:
            shp (GeoDataFrame): The GeoDataFrame containing geometries.

        Returns:
            bool: True if all geometries are polygons, False otherwise.
        """
        return all(geom_type == 'Polygon' for geom_type in shp.geom_type)

    def check_if_all_polylines(self, shp):
        """
        Check if all geometries in a shapefile are polylines.

        Args:
            shp (GeoDataFrame): The GeoDataFrame containing geometries.

        Returns:
            bool: True if all geometries are polylines, False otherwise.
        """
        return all(geom_type == 'LineString' for geom_type in shp.geom_type)

    def check_if_included_file(self, filename, included_filenames):
        """
        Check if a filename contains any of the included filenames.

        Args:
            filename (str): The filename to check.
            included_filenames (list): A list of filenames to include.

        Returns:
            bool: True if the filename contains any included filenames, False otherwise.
        """
        return any(included_file in filename for included_file in included_filenames)

    def merge_files(self):
        """
        Merge files from the input directory and save them to the output directory.
        """
        input_dir = self.input_line_edit.text()
        output_dir = self.output_line_edit.text()
        # input_file_type = self.input_file_type_combo_box.currentText()
        input_file_type = "gpkg"
        # output_file_type = self.output_file_type_combo_box.currentText()
        output_file_type = "gpkg"

        if not input_dir or not output_dir:
            return

        self.merge_folder(input_dir, output_dir, input_file_type, output_file_type)

    def merge_folder(self, input_dir, output_dir, input_file_type, output_file_type):
        """
        Merge all files of a specific type from the input directory and save the merged output.

        Args:
            input_dir (str): The directory containing the input files.
            output_dir (str): The directory to save the merged files.
            input_file_type (str): The input file type (gpkg, shp, or gdb).
            output_file_type (str): The output file type (gpkg, shp, or gdb).
        """
        dir_name = os.path.basename(os.path.normpath(input_dir))
        base_output_filename = os.path.join(output_dir, f'{dir_name}_merged')

        files = find_all_files_of_type(input_dir, type=input_file_type)

        if not files:
            return

        lines = []
        polygons = []
        included_files = ['bld_fts_building', 'lnd_fts_land', 'trn_fts_rail', 'trn_fts_roadtrackorpath',
                          'wtr_ntwk_waterlink', 'wtr_fts_water', 'str_fts_structure']
        crs = None

        for file in files:
            if self.check_if_included_file(filename=file, included_filenames=included_files):
                if file.endswith('.shp') or file.endswith('.gpkg'):
                    gdf = gpd.read_file(file)
                    gdf = gdf.explode()
                    print("file: ", file)
                    print("gdf: ", gdf.shape)
                else:
                    continue

                self.process_geodataframe(gdf, crs, polygons, lines)
                print(len(polygons))
                print("*"*100)

        geom_type_labels = {
            'polygons': 'merged_polygon',
            'lines': 'merged_polyline'
        }
        print("polygon: ", len(polygons))
        print("polylines: ", len(lines))

        if len(polygons) != 0:
            merged_polygons = gpd.GeoDataFrame(pd.concat(polygons).drop_duplicates().reset_index(drop=True),
                                               geometry='geometry')
            self.save_merged_output(merged_polygons, base_output_filename, dir_name, geom_type_labels['polygons'],
                                    output_file_type)

        if len(lines) != 0:
            merged_lines = gpd.GeoDataFrame(pd.concat(lines).drop_duplicates().reset_index(drop=True),
                                            geometry='geometry')
            if merged_lines.shape[0] > 0:
                self.save_merged_output(merged_lines, base_output_filename, dir_name, geom_type_labels['lines'],
                                        output_file_type)

    def save_merged_output(self, gdf, base_filename, dir_name, layer_type, output_file_type):
        """
        Save the merged GeoDataFrame to the specified output file.

        Args:
            gdf (GeoDataFrame): The GeoDataFrame to save.
            base_filename (str): The base filename to save the output.
            dir_name (str): The directory name for the output.
            layer_type (str): The type of layer (polygon or polyline).
            output_file_type (str): The output file type (gpkg, shp, or gdb).
        """
        output_file_map = {
            'gpkg': {
                'driver': 'GPKG',
                'filename': f'{base_filename}.gpkg',
                'layer': f'{dir_name}_{layer_type}'
            },
            'shp': {
                'driver': 'ESRI Shapefile',
                'filename': f'{base_filename.rsplit("_", 1)[0]}_{layer_type}.shp',
                'layer': None  # Shapefiles do not support layers
            },
            'gdb': {
                'driver': 'FileGDB',
                'filename': f'{base_filename}.gdb',
                'layer': f'{dir_name}_{layer_type}'
            }
        }

        file_settings = output_file_map.get(output_file_type)

        if file_settings:
            if file_settings['layer']:
                gdf.to_file(file_settings['filename'], layer=file_settings['layer'], driver=file_settings['driver'])
            else:
                gdf.to_file(file_settings['filename'], driver=file_settings['driver'])
        else:
            raise ValueError(f"Unsupported output file type: {output_file_type}")

    def process_geodataframe(self, gdf, crs, polygons, lines):
        """
        Process a GeoDataFrame by checking its geometry type and appending it to the respective list.

        Args:
            gdf (GeoDataFrame): The GeoDataFrame to process.
            crs (CRS): The coordinate reference system to use.
            polygons (list): A list to store GeoDataFrames containing polygons.
            lines (list): A list to store GeoDataFrames containing polylines.
        """
        if crs is None:
            crs = gdf.crs
        gdf = gdf.to_crs(crs)

        if self.check_if_all_polygons(gdf):
            polygons.append(gdf)
        elif self.check_if_all_polylines(gdf):
            lines.append(gdf)
            
    def create_index_rasters(self):
        """
        Get the image indexes from the image path.
        """
        self.raster_paths = {
            'si': self.image_path.replace('.tif', '_si.tif'),
            'ndvi': self.image_path.replace('.tif', '_ndvi.tif'),
            'enh_ndvi': self.image_path.replace('.tif', '_enh_ndvi.tif')
        }
        with rasterio.open(self.image_path) as src:
            # Read all required bands
            blue = src.read(3).astype(float)
            green = src.read(2).astype(float)
            red = src.read(1).astype(float)
            nir = src.read(4).astype(float)
            
            # Normalize all bands to 0-1 range
            blue = blue / 255.0
            green = green / 255.0
            red = red / 255.0
            nir = nir / 255.0
            
            # Calculate indices
            indices = {
                'si': (1 - blue) * (1 - green) * (1 - red) , # Shadow Index,
                'ndvi': (nir - red) / (nir + red) # NDVI
            }
            
            # Copy the metadata from source
            metadata = src.meta.copy()
            metadata.update({
                'count': 1,  # Single band output
                'dtype': 'float32'
            })

            # Save each index as a separate raster
            for index_name, index_data in indices.items():
                output_path = self.raster_paths[index_name]              
                with rasterio.open(output_path, 'w', **metadata) as dst:
                    dst.write(index_data.astype('float32'), 1)
                    
                print(f"Saved {index_name} index to {output_path}")
        # modify ndvi to enhance vegetation
        with rasterio.open(self.raster_paths['ndvi']) as src1, rasterio.open(self.raster_paths['si']) as src2:
            # Read the data
            ndvi_data = src1.read(1)
            si_data = src2.read(1)
            
            # Create mask where raster2 meets threshold
            condition_mask = si_data >= 0.4
            
            # Create output array
            output_data = ndvi_data.copy()
            
            # Subtract value where condition is met
            output_data[condition_mask] -= 0.1
            
            # Create output raster with same metadata as input
            profile = src1.profile
            
            with rasterio.open(self.raster_paths['enh_ndvi'], 'w', **profile) as dst:
                dst.write(output_data, 1)
        return
    
    def check_nir_band(self):
        '''
        Check if the image has a NIR band
        '''
        src = rio.open(self.image_path)
        num_bands = src.count
        src.close()
        return True if num_bands == 4 else False
    
    def get_ndvi_stats(self, gdf, ndvi_threshold=0.1):
        """
        Calculate NDVI statistics for each geometry in the GeoDataFrame.
        """
        # Add imagery_present column if it doesn't exist
        if 'imagery_present' not in gdf.columns:
            gdf['imagery_present'] = 0
        print(self.image_path)
        if not os.path.exists(self.image_path):
            return gdf
        if "tif" not in self.image_path:
            self.show_notification("Error", "file is not a tif file")
            return gdf
        if not self.check_nir_band():
            self.show_notification("Error", "Image does not have a NIR band")
            return gdf
        self.ndvi_path = self.image_path.replace('.tif', '_ndvi.tif')
        self.create_index_rasters()
        with rasterio.open(self.raster_paths['enh_ndvi']) as src:
            for idx, row in gdf.iterrows():
                try:
                    # Create mask for the geometry
                    geom = row['geometry']
                    clipped, _ = mask(src, 
                                    [geom], 
                                    crop=True, 
                                    all_touched=False)
                    valid_data = clipped[0][clipped[0] != src.nodata]
                    total_points = len(valid_data)
                    
                    if len(valid_data) > 0:
                        # Calculate statistics
                        vegetation_points = np.sum(valid_data > ndvi_threshold)
                        gdf.at[idx, 'ndvi_vegetation_percent'] = round(float(vegetation_points / total_points * 100), 2)
                        gdf.at[idx, 'ndvi_mean'] = round(float(np.mean(valid_data)), 2)
                        gdf.at[idx, 'ndvi_median'] = round(float(np.median(valid_data)), 2)
                        gdf.at[idx, 'ndvi_std'] = round(float(np.std(valid_data)), 2)
                        zero_points = np.sum(valid_data == 0)
                        gdf.at[idx, 'ndvi_zero_percent'] = round(float(zero_points / total_points * 100), 2)
                        gdf.at[idx, 'imagery_present'] = 1
                except ValueError as e:
                    # Set default values for no overlap case
                    gdf.at[idx, 'ndvi_vegetation_percent'] = -1
                    gdf.at[idx, 'ndvi_mean'] = -1
                    gdf.at[idx, 'ndvi_median'] = -1
                    gdf.at[idx, 'ndvi_std'] = -1
                    gdf.at[idx, 'ndvi_zero_percent'] = -1
                    gdf.at[idx, 'imagery_present'] = 0
        for image in self.raster_paths.values():
            os.remove(image)
        return gdf

    def process_data(self):
        """
        Process the merged data, create a processed output, and save it.
        """
        self.output_dir = self.output_line_edit.text()
        self.image_path = self.image_line_edit.text()
        extensions = ('shp', 'gpkg')
        merged_output_filename = None
        found_extension = None

        # Find the merged file with either .shp or .gpkg extension
        for extension in extensions:
            files = find_all_files_of_type(self.output_dir, prefix='_merged', type=extension)
            if files:
                merged_output_filename = files[0]  # Use the first file found
                found_extension = extension
                break

        if not merged_output_filename:
            return  # No merged file found, so exit the function

        if found_extension == 'shp':
            # For .shp files, keep the specific type (polygon or polyline) in the filename
            base_name = os.path.basename(merged_output_filename).replace(f'_merged_polygon.{found_extension}',
                                                                         '').replace(
                f'_merged_polyline.{found_extension}', '')
            processed_polygon_filename = os.path.join(self.output_dir, f'{base_name}_processed_polygon.{found_extension}')
            processed_polyline_filename = os.path.join(self.output_dir, f'{base_name}_processed_polyline.{found_extension}')
        elif found_extension == 'gpkg':
            # For .gpkg files, handle layers differently
            base_name = os.path.basename(merged_output_filename).replace(f'_merged.{found_extension}', '')
            processed_polygon_filename = os.path.join(self.output_dir, f'{base_name}_processed.{found_extension}')
            processed_polyline_filename = os.path.join(self.output_dir, f'{base_name}_processed.{found_extension}')

        geom_type_labels = {
            'polygons': 'polygon',
            'lines': 'polyline'
        }

        # Process and save the polygon layer
        self.process_and_save_layer(merged_output_filename, geom_type_labels["polygons"], base_name,
                                    processed_polygon_filename, found_extension)

        # Process and save the polyline layer
        self.process_and_save_layer(merged_output_filename, geom_type_labels["lines"], base_name,
                                    processed_polyline_filename, found_extension)

    def process_and_save_layer(self, merged_output_filename, layer_type, base_name, processed_output_filename,
                               file_extension,
                               additional_columns=None, columns_to_keep=None, driver='GPKG'):
        """
        Process a specific layer (polygon or polyline) and save the processed output.

        Args:
            merged_output_filename (str): The filename of the merged GeoPackage or Shapefile.
            layer_type (str): The type of layer to process ('polygon' or 'polyline').
            base_name (str): The base name for constructing output filenames.
            processed_output_filename (str): The filename to save the processed output.
            file_extension (str): The extension of the input file (e.g., 'shp' or 'gpkg').
            additional_columns (dict, optional): A dictionary where keys are column names and values are default values for new columns. Defaults to None.
            columns_to_keep (list, optional): A list of columns to keep in the processed GeoDataFrame. Defaults to ['AiDashCode', 'strt_sig'].
            driver (str, optional): The file format driver to use when saving the file. Defaults to 'GPKG'.
        """
        if additional_columns is None:
            additional_columns = {'strat_sig': np.nan}

        if columns_to_keep is None:
            columns_to_keep = ['AiDashCode', 'strat_sig']

        # Determine if the file is a Shapefile or a GeoPackage
        if file_extension == 'gpkg':
            # For GeoPackage, use the layer name
            layers = fiona.listlayers(merged_output_filename)
            layer_name = f'{base_name}_merged_{layer_type}'
            if layer_name not in layers:
                return
            gdf = gpd.read_file(merged_output_filename, layer=layer_name)
        elif file_extension == 'shp':
            # For Shapefile, distinguish between the polygon and polyline files
            if layer_type == 'polygon' and 'polygon' in merged_output_filename:
                gdf = gpd.read_file(merged_output_filename)
            elif layer_type == 'polyline' and 'polyline' in merged_output_filename:
                gdf = gpd.read_file(merged_output_filename)
            else:
                return  # Skip if the layer type does not match the filename
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

        # Process the GeoDataFrame
        gdf = self.create_concatenated_column(gdf, self.config['columns_to_combine'], self.config['new_column_name'],
                                              self.config['delimiter'])
        gdf = self.dissolve_geometries(gdf, self.config['dissolve_column'], self.config['specific_dissolve_values'])
        gdf.columns = [col.strip() for col in gdf.columns]
        gdf['AiDashCode'] = ''
        gdf['ndvi_mean'] = np.nan
        gdf['ndvi_median'] = np.nan
        gdf['ndvi_std'] = np.nan
        gdf['ndvi_zero_percent'] = np.nan 
        gdf['ndvi_vegetation_percent'] = np.nan
        if layer_type == "polygon":
            gdf['area'] = gdf.geometry.area
            for col in gdf.columns:
                if gdf[col].dtype == 'object':
                    gdf[col] = gdf[col].str.lower()
            gdf = self.get_ndvi_stats(gdf)
            gdf['sealed_surface'] = gdf.apply(self.sealed_surface_present, axis=1)
            gdf.loc[:,'centroid'] = gdf.geometry.centroid
            sealed_surfaces = gdf[gdf.sealed_surface]
            gdf.loc[:,'min_distance_to_sealed'] = self.min_distance_to_subset_optimized(gdf, sealed_surfaces)
            gdf['AiDashCode'] = gdf.apply(self.habitat_labelling, rules=self.rules, axis=1)
            percentage_imagery_present = gdf['imagery_present'].value_counts() / len(gdf) * 100
            if os.path.exists(self.image_path) and 1 in percentage_imagery_present.index and percentage_imagery_present[1] < 90:
                self.show_notification("Warning", f"{round(percentage_imagery_present[1])}% polygons have imagery in the OS data")
        # gdf = self.map_aidash_code(gdf, self.config['habitat_to_aidash'])

        # Add additional columns with default values
        for column, value in additional_columns.items():
            gdf[column] = value

        # Ensure that AiDashCode and strat_sig columns are of string type
        gdf['AiDashCode'] = gdf['AiDashCode'].astype(pd.StringDtype())
        gdf['strat_sig'] = gdf['strat_sig'].astype(pd.StringDtype())
        
        

        # Create a new GeoDataFrame with the relevant columns
        # processed_gdf = gpd.GeoDataFrame(gdf[columns_to_keep], geometry=gdf.geometry)
        # ── Keep only AiDashCode and strat_sig in processed output ──────────
        cols_keep = ['AiDashCode', 'strat_sig']
        valid_cols = [c for c in cols_keep if c in gdf.columns]
        processed_gdf = gpd.GeoDataFrame(gdf[valid_cols], geometry=gdf.geometry)


        # Save the processed GeoDataFrame to the output file
        if file_extension == 'gpkg':
            processed_gdf.to_file(processed_output_filename, layer=f'{base_name}_processed_{layer_type}', driver=driver)
        elif file_extension == 'shp':
            processed_gdf.to_file(processed_output_filename, driver=driver)

    def create_concatenated_column(self, gdf, columns, new_column="habitat", delimiter=";"):
        """
        Create a new column in the GeoDataFrame by concatenating existing columns with a delimiter.

        Args:
            gdf (GeoDataFrame): The GeoDataFrame to process.
            columns (list): The columns to concatenate.
            new_column (str): The name of the new concatenated column.
            delimiter (str): The delimiter to use between concatenated values.

        Returns:
            GeoDataFrame: The processed GeoDataFrame with the new concatenated column.
        """
        # Ensure columns are stripped of any leading/trailing whitespace
        columns = [col.strip() for col in columns]

        # Ensure columns exist in the DataFrame
        valid_columns = [col for col in columns if col in gdf.columns]

        # Concatenate columns into the new column
        gdf[new_column] = gdf[valid_columns].fillna('').astype(str).agg(delimiter.join, axis=1)

        # Optionally, remove any leading or trailing delimiters
        gdf[new_column] = gdf[new_column].str.strip(delimiter)

        return gdf

    def dissolve_geometries(self, gdf, dissolve_column, specific_values):
        """
        Dissolve geometries in the GeoDataFrame based on a specific column and values.

        Args:
            gdf (GeoDataFrame): The GeoDataFrame to process.
            dissolve_column (str): The column to dissolve geometries by.
            specific_values (list): The specific values in the column to dissolve.

        Returns:
            GeoDataFrame: The processed GeoDataFrame with dissolved geometries.
        """
        dissolved_gdfs = []

        # Iterate over specific_values and dissolve each individually
        for value in specific_values:
            to_dissolve = gdf[gdf[dissolve_column] == value]
            if not to_dissolve.empty:
                dissolved_gdf = to_dissolve.dissolve(by=dissolve_column, as_index=False)
                dissolved_gdfs.append(dissolved_gdf)

        # Concatenate all individually dissolved GeoDataFrames
        dissolved_gdf = gpd.GeoDataFrame(pd.concat(dissolved_gdfs, ignore_index=True),
                                         geometry='geometry') if dissolved_gdfs else gpd.GeoDataFrame()

        # Select rows not to dissolve
        non_dissolved_gdf = gdf[~gdf[dissolve_column].isin(specific_values)]

        # Concatenate dissolved and non-dissolved GeoDataFrames
        result_gdf = gpd.GeoDataFrame(pd.concat([dissolved_gdf, non_dissolved_gdf], ignore_index=True),
                                      geometry='geometry')

        return result_gdf

    def map_aidash_code(self, gdf, mapping, source_column='habitat', target_column='AiDashCode'):
        """
        Map values from a source column to a target column using a provided mapping dictionary.

        Args:
            gdf (GeoDataFrame): The GeoDataFrame to process.
            mapping (dict): A dictionary mapping source column values to target column values.
            source_column (str): The column in the GeoDataFrame to map from. Defaults to 'habitat'.
            target_column (str): The column in the GeoDataFrame to map to. Defaults to 'AiDashCode'.

        Returns:
            GeoDataFrame: The processed GeoDataFrame with the mapped values in the target column.
        """
        if source_column not in gdf.columns:
            raise KeyError(f"Source column '{source_column}' not found in the GeoDataFrame.")

        # Perform the mapping, leaving unmapped values as NaN
        gdf[target_column] = gdf[source_column].map(mapping)

        return gdf

    def show_notification(self, title, message):
        """
        Show a notification dialog with the given title and message.

        Args:
            title (str): The title of the notification.
            message (str): The message to display in the notification.
        """
        QMessageBox.information(self, title, message)


def run_bngai_labelling():
    """
    Run the BNGAILabelling dialog within QGIS.
    """
    from qgis.utils import iface
    converter = BNGAILabelling(iface)
    converter.exec_()


if __name__ == "__console__":
    run_bngai_labelling()

