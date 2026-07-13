"""
RLB Spatial Validator - Validates that features are within the Red Line Boundary.

This module checks if plan features (polygon, line, point) are within or intersect
the Red Line Boundary (RLB). Features outside the RLB are flagged as invalid.
"""
from typing import List, Optional
from dataclasses import dataclass, field
from qgis.core import (
    QgsMessageLog, QgsProject, QgsVectorLayer, 
    QgsFeature, QgsGeometry, QgsWkbTypes
)


@dataclass
class SpatialValidationError:
    """Represents a spatial validation error for a feature outside RLB"""
    feature_id: str
    error_type: str = "outside_rlb"  # 'outside_rlb', 'partially_outside', 'no_geometry'
    feature_name: Optional[str] = None
    client_id: Optional[str] = None
    percentage_outside: float = 0.0  # For partially outside features
    
    def __str__(self):
        id_str = self.client_id or self.feature_id
        if self.error_type == "outside_rlb":
            return f"Feature {id_str}: Completely outside Red Line Boundary"
        elif self.error_type == "partially_outside":
            return f"Feature {id_str}: {self.percentage_outside:.1f}% outside Red Line Boundary"
        elif self.error_type == "no_geometry":
            return f"Feature {id_str}: No geometry found"
        return f"Feature {id_str}: Spatial validation error"
    
    def to_reason(self) -> str:
        """Get a short reason string for display"""
        if self.error_type == "outside_rlb":
            return "outside RLB"
        elif self.error_type == "partially_outside":
            return f"{self.percentage_outside:.0f}% outside RLB"
        elif self.error_type == "no_geometry":
            return "no geometry"
        return "spatial error"


@dataclass 
class SpatialValidationResult:
    """Spatial validation result for a single feature"""
    feature_id: str
    is_within_rlb: bool
    error: Optional[SpatialValidationError] = None
    client_id: Optional[str] = None
    
    @property
    def display_id(self) -> str:
        return self.client_id or self.feature_id


@dataclass
class LayerSpatialValidationResult:
    """Spatial validation results for a layer"""
    layer_name: str
    total_features: int = 0
    features_within_rlb: int = 0
    features_outside_rlb: int = 0
    errors: List[SpatialValidationError] = field(default_factory=list)
    
    def add_result(self, result: SpatialValidationResult):
        """Add a feature validation result"""
        self.total_features += 1
        if result.is_within_rlb:
            self.features_within_rlb += 1
        else:
            self.features_outside_rlb += 1
            if result.error:
                self.errors.append(result.error)


class RLBSpatialValidator:
    """
    Validates that features are within the Red Line Boundary.
    """
    
    # Tolerance for intersection checks (in map units, e.g., degrees for EPSG:4326)
    INTERSECTION_TOLERANCE = 0.0001
    
    def __init__(self):
        self.project = QgsProject.instance()
        self.rlb_geometry: Optional[QgsGeometry] = None
        self.rlb_layer: Optional[QgsVectorLayer] = None
    
    def find_rlb_layer(self) -> Optional[QgsVectorLayer]:
        """
        Find the Red Line Boundary layer in the project.
        
        Looks for layers with:
        - Custom property 'bngai_layer_type' == 'rlb'
        - Or layer name containing 'Red Line Boundary' or 'RLB'
        
        Returns:
            QgsVectorLayer or None if not found
        """
        for layer in self.project.mapLayers().values():
            if not isinstance(layer, QgsVectorLayer):
                continue
            
            # Check custom property first
            layer_type = layer.customProperty("bngai_layer_type")
            if layer_type == "rlb":
                QgsMessageLog.logMessage(f"Found RLB layer by property: {layer.name()}", "BNGAI Plugin", level=0)
                return layer
            
            # Check layer name
            layer_name_lower = layer.name().lower()
            if "red line boundary" in layer_name_lower or "rlb" in layer_name_lower:
                QgsMessageLog.logMessage(f"Found RLB layer by name: {layer.name()}", "BNGAI Plugin", level=0)
                return layer
        
        QgsMessageLog.logMessage("RLB layer not found in project", "BNGAI Plugin", level=1)
        return None
    
    def get_rlb_geometry(self) -> Optional[QgsGeometry]:
        """
        Get the combined geometry of all features in the RLB layer.
        
        Returns:
            QgsGeometry or None if RLB layer not found or empty
        """
        if self.rlb_geometry is not None:
            return self.rlb_geometry
        
        self.rlb_layer = self.find_rlb_layer()
        if not self.rlb_layer:
            return None
        
        # Combine all RLB features into a single geometry
        combined_geom = QgsGeometry()
        for feature in self.rlb_layer.getFeatures():
            geom = feature.geometry()
            if geom and not geom.isEmpty():
                if combined_geom.isEmpty():
                    combined_geom = geom
                else:
                    combined_geom = combined_geom.combine(geom)
        
        if combined_geom.isEmpty():
            QgsMessageLog.logMessage("RLB layer has no valid geometry", "BNGAI Plugin", level=1)
            return None
        
        self.rlb_geometry = combined_geom
        QgsMessageLog.logMessage(f"RLB geometry loaded, area: {combined_geom.area()}", "BNGAI Plugin", level=0)
        return self.rlb_geometry
    
    def validate_feature(self, feature: QgsFeature, feature_id: str = None, 
                        client_id: str = None) -> SpatialValidationResult:
        """
        Validate that a feature is within the RLB.
        
        Args:
            feature: QgsFeature to validate
            feature_id: Optional feature ID for reporting
            client_id: Optional client ID for reporting
            
        Returns:
            SpatialValidationResult
        """
        fid = feature_id or str(feature.id())
        
        # Get feature geometry
        feature_geom = feature.geometry()
        if not feature_geom or feature_geom.isEmpty():
            return SpatialValidationResult(
                feature_id=fid,
                is_within_rlb=False,
                client_id=client_id,
                error=SpatialValidationError(
                    feature_id=fid,
                    error_type="no_geometry",
                    client_id=client_id
                )
            )
        
        # Get RLB geometry
        rlb_geom = self.get_rlb_geometry()
        if not rlb_geom:
            # If no RLB, skip spatial validation (consider valid)
            QgsMessageLog.logMessage("Skipping spatial validation - no RLB geometry available", "BNGAI Plugin", level=1)
            return SpatialValidationResult(
                feature_id=fid,
                is_within_rlb=True,
                client_id=client_id
            )
        
        # Check if feature is within RLB
        return self._check_spatial_relationship(feature_geom, rlb_geom, fid, client_id)
    
    def _check_spatial_relationship(self, feature_geom: QgsGeometry, rlb_geom: QgsGeometry,
                                   feature_id: str, client_id: str = None) -> SpatialValidationResult:
        """
        Check the spatial relationship between feature and RLB.
        
        Args:
            feature_geom: Feature geometry
            rlb_geom: RLB geometry
            feature_id: Feature ID for reporting
            client_id: Client ID for reporting
            
        Returns:
            SpatialValidationResult
        """
        # For points: check if within RLB (with small buffer for tolerance)
        if feature_geom.type() == QgsWkbTypes.PointGeometry:
            # Buffer point slightly for tolerance
            buffered_rlb = rlb_geom.buffer(self.INTERSECTION_TOLERANCE, 5)
            if buffered_rlb.contains(feature_geom):
                return SpatialValidationResult(
                    feature_id=feature_id,
                    is_within_rlb=True,
                    client_id=client_id
                )
            else:
                return SpatialValidationResult(
                    feature_id=feature_id,
                    is_within_rlb=False,
                    client_id=client_id,
                    error=SpatialValidationError(
                        feature_id=feature_id,
                        error_type="outside_rlb",
                        client_id=client_id
                    )
                )
        
        # For lines and polygons: check intersection
        if not feature_geom.intersects(rlb_geom):
            # Completely outside
            return SpatialValidationResult(
                feature_id=feature_id,
                is_within_rlb=False,
                client_id=client_id,
                error=SpatialValidationError(
                    feature_id=feature_id,
                    error_type="outside_rlb",
                    client_id=client_id
                )
            )
        
        # Check if completely within (with tolerance)
        buffered_rlb = rlb_geom.buffer(self.INTERSECTION_TOLERANCE, 5)
        if buffered_rlb.contains(feature_geom):
            return SpatialValidationResult(
                feature_id=feature_id,
                is_within_rlb=True,
                client_id=client_id
            )
        
        # Partially outside - calculate percentage
        intersection = feature_geom.intersection(rlb_geom)
        if intersection.isEmpty():
            return SpatialValidationResult(
                feature_id=feature_id,
                is_within_rlb=False,
                client_id=client_id,
                error=SpatialValidationError(
                    feature_id=feature_id,
                    error_type="outside_rlb",
                    client_id=client_id
                )
            )
        
        # Calculate percentage outside
        if feature_geom.type() == QgsWkbTypes.LineGeometry:
            total_length = feature_geom.length()
            inside_length = intersection.length()
            percentage_outside = ((total_length - inside_length) / total_length * 100) if total_length > 0 else 0
        else:  # Polygon
            total_area = feature_geom.area()
            inside_area = intersection.area()
            percentage_outside = ((total_area - inside_area) / total_area * 100) if total_area > 0 else 0
        
        # If more than 1% outside, flag as partially outside
        if percentage_outside > 1.0:
            return SpatialValidationResult(
                feature_id=feature_id,
                is_within_rlb=False,
                client_id=client_id,
                error=SpatialValidationError(
                    feature_id=feature_id,
                    error_type="partially_outside",
                    client_id=client_id,
                    percentage_outside=percentage_outside
                )
            )
        
        # Within tolerance, consider valid
        return SpatialValidationResult(
            feature_id=feature_id,
            is_within_rlb=True,
            client_id=client_id
        )
    
    def validate_layer_features(self, layer: QgsVectorLayer, 
                                feature_ids: List[str] = None) -> LayerSpatialValidationResult:
        """
        Validate all features in a layer against the RLB.
        
        Args:
            layer: QgsVectorLayer to validate
            feature_ids: Optional list of specific feature IDs to validate
            
        Returns:
            LayerSpatialValidationResult
        """
        result = LayerSpatialValidationResult(layer_name=layer.name())
        
        for feature in layer.getFeatures():
            # Get feature ID
            feature_id = str(feature.attribute('id') or feature.id())
            
            # Skip if we have a specific list and this feature is not in it
            if feature_ids and feature_id not in feature_ids:
                continue
            
            # Get client ID if available
            client_id = None
            try:
                client_id = feature.attribute('clientId')
            except Exception:
                pass
            
            # Validate
            validation = self.validate_feature(feature, feature_id, client_id)
            result.add_result(validation)
        
        return result
    
    def reset(self):
        """Reset cached RLB geometry"""
        self.rlb_geometry = None
        self.rlb_layer = None


def create_spatial_validation_html(results: List[LayerSpatialValidationResult], 
                                   title: str = "Spatial Validation") -> str:
    """
    Create HTML summary of spatial validation results.
    
    Args:
        results: List of LayerSpatialValidationResult
        title: Title for the summary section
        
    Returns:
        HTML string
    """
    # Count totals
    total_errors = sum(len(r.errors) for r in results)
    
    if total_errors == 0:
        return ""
    
    html = f"""
    <h3 style="color: #C62828;">{title}</h3>
    <p style="color: #666;">The following features are outside the Red Line Boundary:</p>
    <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%;">
        <tr style="background: #ffebee;">
            <th>Layer</th>
            <th>Feature ID</th>
            <th>Issue</th>
        </tr>
    """
    
    for result in results:
        for error in result.errors:
            feature_id = error.client_id or error.feature_id
            # Truncate long IDs
            display_id = feature_id[:12] + '...' if len(str(feature_id)) > 15 else feature_id
            
            html += f"""
        <tr>
            <td>{result.layer_name}</td>
            <td title="{feature_id}">{display_id}</td>
            <td style="color: #C62828;">{error.to_reason()}</td>
        </tr>
            """
    
    html += "</table>"
    return html
