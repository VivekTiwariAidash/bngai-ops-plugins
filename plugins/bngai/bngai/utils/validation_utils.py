"""
Validation utilities for BNG attributes - Single source of truth for feature validation.

This module handles:
- Mandatory field validation based on aiDashCode
- Value validation against DEFRA_BIDV3_ALLOWED_ATTRIBUTES_PER_AIDASH_CODE.json
- Validation summary and reporting
"""
from qgis.core import QgsMessageLog, QgsWkbTypes
import json
import os
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field
from .habitat_mappings import (
    CONDITION_MAP,
    STRATEGIC_SIGNIFICANCE_MAP,
    WATERCOURSE_ENCROACHMENT_MAP,
    RIPARIAN_ENCROACHMENT_MAP,
    map_value
)


@dataclass
class ValidationError:
    """Represents a single validation error"""
    feature_id: str
    field_name: str
    error_type: str  # 'missing' or 'invalid'
    current_value: Optional[str] = None
    allowed_values: List[str] = field(default_factory=list)
    client_id: Optional[str] = None

    def __str__(self):
        id_str = self.client_id or self.feature_id
        if self.error_type == 'missing':
            return f"Feature {id_str}: Missing required field '{self.field_name}'"
        return f"Feature {id_str}: Invalid {self.field_name} value '{self.current_value}'"

    def to_reason(self) -> str:
        """Get a short reason string for display"""
        if self.error_type == 'missing':
            return f"missing {self.field_name}"
        return f"{self.field_name}='{self.current_value}' (invalid)"

    def to_detailed_reason(self) -> str:
        """Get detailed reason string including allowed values"""
        if self.error_type == 'missing':
            if self.allowed_values:
                return f"missing {self.field_name}. Allowed: {', '.join(self.allowed_values)}"
            return f"missing {self.field_name}"
        if self.allowed_values:
            return f"{self.field_name}='{self.current_value}' (invalid). Allowed: {', '.join(self.allowed_values)}"
        return f"{self.field_name}='{self.current_value}' (invalid)"


@dataclass
class FeatureValidationResult:
    """Validation result for a single feature"""
    feature_id: str
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    client_id: Optional[str] = None

    @property
    def display_id(self) -> str:
        """Get the best ID to display (clientId preferred over feature_id)"""
        return self.client_id or self.feature_id

    def get_reason(self, include_allowed: bool = False) -> str:
        """
        Get combined reason string for all errors.
        
        Args:
            include_allowed: If True, include allowed values in the reason
        """
        if not self.errors:
            return ""
        
        if include_allowed:
            # Use detailed format with allowed values
            return "; ".join([e.to_detailed_reason() for e in self.errors])
        
        # Simple format
        missing = [e.field_name for e in self.errors if e.error_type == 'missing']
        invalid = [f"{e.field_name}='{e.current_value}'" for e in self.errors if e.error_type == 'invalid']
        parts = []
        if missing:
            parts.append(f"missing: {', '.join(missing)}")
        if invalid:
            parts.append(f"invalid: {', '.join(invalid)}")
        return "; ".join(parts)


@dataclass
class LayerValidationResult:
    """Validation result for a layer"""
    layer_name: str
    total_features: int = 0
    valid_features: int = 0
    invalid_features: int = 0
    feature_results: List[FeatureValidationResult] = field(default_factory=list)

    def add_result(self, result: FeatureValidationResult):
        self.feature_results.append(result)
        self.total_features += 1
        if result.is_valid:
            self.valid_features += 1
        else:
            self.invalid_features += 1

    def get_invalid_details(self) -> List[Tuple[str, str]]:
        """Get list of (display_id, reason) for invalid features. Uses clientId if available."""
        return [
            (r.display_id, r.get_reason())
            for r in self.feature_results if not r.is_valid
        ]


class FeatureValidator:
    """
    Validates features against DEFRA BNG rules.
    
    Handles:
    - Mandatory field validation based on aiDashCode
    - Value validation against allowed values per aiDashCode
    """
    
    # Field name mappings from JSON keys to feature attribute names
    JSON_TO_FIELD = {
        'condition': 'condition',
        'strategic_significance': 'strategicSignificance',
        'tree_size': 'treeSize',
        'watercourse_encroachment': 'watercourseEncroachment',
        'riparian_encroachment': 'riparianEncroachment',
    }
    
    # Field name to mapping dict for value normalization
    FIELD_MAPPINGS = {
        'condition': CONDITION_MAP,
        'strategicSignificance': STRATEGIC_SIGNIFICANCE_MAP,
        'watercourseEncroachment': WATERCOURSE_ENCROACHMENT_MAP,
        'riparianEncroachment': RIPARIAN_ENCROACHMENT_MAP,
    }

    def __init__(self):
        """Initialize validator with allowed attributes from JSON"""
        self.allowed_by_code = self._load_allowed_attributes()

    def _load_allowed_attributes(self) -> Dict:
        """Load allowed attributes from JSON file"""
        try:
            json_path = os.path.join(
                os.path.dirname(__file__), 
                'DEFRA_BIDV3_ALLOWED_ATTRIBUTES_PER_AIDASH_CODE.json'
            )
            with open(json_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error loading allowed attributes: {str(e)}", 
                "BNGAI Plugin", level=2
            )
            return {}

    @staticmethod
    def get_layer_type(layer) -> str:
        """Get geometry type string from layer"""
        if not layer:
            return ''
        if layer.geometryType() == QgsWkbTypes.PointGeometry:
            return 'point'
        if layer.geometryType() == QgsWkbTypes.LineGeometry:
            return 'line'
        if layer.geometryType() == QgsWkbTypes.PolygonGeometry:
            return 'polygon'
        return ''

    @staticmethod
    def is_value_missing(value: Any) -> bool:
        """Check if a value is considered missing/empty"""
        if value is None:
            return True
        s = str(value).strip()
        return s == '' or s.lower() in ('null', 'none')

    def _normalize_value(self, field_name: str, value: Any) -> Any:
        """Normalize a field value to its canonical code"""
        if value is None:
            return None
        mapping = self.FIELD_MAPPINGS.get(field_name)
        if mapping:
            return map_value(value, mapping)
        if field_name == 'treeSize':
            return str(value).strip().lower()
        return value

    def _get_required_fields(self, aidash_code: str, layer_type: str) -> List[str]:
        """
        Get list of required field names for an aiDashCode and layer type.
        
        A field is required if it has non-empty allowed values in the JSON.
        Line-specific fields (watercourse/riparian encroachment) only required for lines.
        """
        required = []
        attrs = self.allowed_by_code.get(aidash_code or '', {})
        
        for json_key, allowed_values in attrs.items():
            # Skip if no allowed values defined
            if not isinstance(allowed_values, list) or len(allowed_values) == 0:
                continue
            # Skip line-specific fields for non-line layers
            if json_key in ('watercourse_encroachment', 'riparian_encroachment'):
                if layer_type != 'line':
                    continue
            field_name = self.JSON_TO_FIELD.get(json_key)
            if field_name:
                required.append(field_name)
        
        return required

    def _get_allowed_values(self, aidash_code: str, json_key: str) -> List[str]:
        """Get allowed values for a field from the JSON config"""
        attrs = self.allowed_by_code.get(aidash_code or '', {})
        return attrs.get(json_key, [])

    def _extract_feature_ids(self, feature) -> Tuple[str, Optional[str]]:
        """Extract feature_id and client_id from a feature"""
        feature_id = str(feature.attribute('id') or f"fid_{feature.id()}")
        client_id = feature.attribute('clientId') if 'clientId' in [f.name() for f in feature.fields()] else None
        client_id = str(client_id) if client_id and not self.is_value_missing(client_id) else None
        return feature_id, client_id

    def _validate_field(self, feature, field_name: str, allowed_attrs: Dict, 
                        feature_id: str, client_id: Optional[str]) -> Optional[ValidationError]:
        """Validate a single field and return error if invalid"""
        value = feature.attribute(field_name)
        
        # Get allowed values for this field
        json_key = next((k for k, v in self.JSON_TO_FIELD.items() if v == field_name), None)
        allowed_values = allowed_attrs.get(json_key, []) if json_key else []
        
        # Check if missing
        if self.is_value_missing(value):
            return ValidationError(
                feature_id=feature_id, field_name=field_name, error_type='missing',
                allowed_values=allowed_values, client_id=client_id
            )
        
        # Check if value is valid
        if allowed_values:
            normalized = self._normalize_value(field_name, value)
            if normalized not in allowed_values:
                return ValidationError(
                    feature_id=feature_id, field_name=field_name, error_type='invalid',
                    current_value=str(value), allowed_values=allowed_values, client_id=client_id
                )
        return None

    def validate_feature(self, feature, layer_type: str) -> FeatureValidationResult:
        """
        Validate a single feature.
        
        Args:
            feature: QgsFeature to validate
            layer_type: 'point', 'line', or 'polygon'
            
        Returns:
            FeatureValidationResult with validation status and any errors
        """
        if not feature:
            return FeatureValidationResult(
                feature_id="unknown", is_valid=False,
                errors=[ValidationError(feature_id="unknown", field_name='feature', error_type='missing')]
            )
        
        feature_id, client_id = self._extract_feature_ids(feature)
        
        # Check aiDashCode - required for all features
        aidash_code = feature.attribute('aiDashCode')
        if self.is_value_missing(aidash_code):
            return FeatureValidationResult(
                feature_id=feature_id, is_valid=False, client_id=client_id,
                errors=[ValidationError(
                    feature_id=feature_id, field_name='aiDashCode', 
                    error_type='missing', client_id=client_id
                )]
            )
        
        # Validate required fields
        required_fields = self._get_required_fields(aidash_code, layer_type)
        allowed_attrs = self.allowed_by_code.get(aidash_code, {})
        
        errors = []
        for field_name in required_fields:
            error = self._validate_field(feature, field_name, allowed_attrs, feature_id, client_id)
            if error:
                errors.append(error)
        
        return FeatureValidationResult(
            feature_id=feature_id, is_valid=len(errors) == 0, 
            errors=errors, client_id=client_id
        )

    def validate_feature_by_id(self, layer, layer_type: str, feature_id: str) -> FeatureValidationResult:
        """Validate a feature by its ID attribute"""
        feature = next(layer.getFeatures(f"id = '{feature_id}'"), None)
        if not feature:
            return FeatureValidationResult(
                feature_id=feature_id,
                is_valid=False,
                errors=[ValidationError(
                    feature_id=feature_id,
                    field_name='feature',
                    error_type='missing'
                )]
            )
        return self.validate_feature(feature, layer_type)

    def validate_feature_by_fid(self, layer, layer_type: str, fid: int) -> Tuple[FeatureValidationResult, Any]:
        """
        Validate a feature by its internal FID.
        
        Returns:
            Tuple of (FeatureValidationResult, QgsFeature or None)
        """
        feature = layer.getFeature(fid)
        if not feature or not feature.isValid():
            return FeatureValidationResult(
                feature_id=f"local_{fid}",
                is_valid=False,
                errors=[ValidationError(
                    feature_id=f"local_{fid}",
                    field_name='feature',
                    error_type='missing'
                )]
            ), None
        result = self.validate_feature(feature, layer_type)
        # Override feature_id to use local_ prefix for new features (keep clientId)
        result.feature_id = f"local_{fid}"
        return result, feature

    def validate_layer_features(self, layer, features: List[Any] = None) -> LayerValidationResult:
        """
        Validate all features in a layer or a subset of features.
        
        Args:
            layer: QgsVectorLayer to validate
            features: Optional list of features to validate (defaults to all)
            
        Returns:
            LayerValidationResult with validation stats and details
        """
        layer_type = self.get_layer_type(layer)
        result = LayerValidationResult(layer_name=layer.name())
        
        if features is None:
            features = list(layer.getFeatures())
        
        for feature in features:
            feature_result = self.validate_feature(feature, layer_type)
            result.add_result(feature_result)
        
        return result

    def get_allowed_values_for_field(self, aidash_code: str, field_name: str) -> List[str]:
        """Get allowed values for a specific field and aiDashCode"""
        json_key = next(
            (k for k, v in self.JSON_TO_FIELD.items() if v == field_name), 
            None
        )
        if json_key:
            return self._get_allowed_values(aidash_code, json_key)
        return []


def _format_allowed_values(allowed_values: List[str]) -> str:
    """Format allowed values for HTML display"""
    if not allowed_values:
        return "<span style='color:#666'>N/A</span>"
    allowed = ", ".join(allowed_values[:10])
    if len(allowed_values) > 10:
        allowed += f" ... (+{len(allowed_values) - 10} more)"
    return f"<span style='color:#2E7D32;font-size:0.9em'>{allowed}</span>"


def _format_error_issue(error: ValidationError) -> str:
    """Format the issue cell for an error"""
    if error.error_type == 'missing':
        return "<span style='color:#b71c1c'>Missing</span>"
    return f"<span style='color:#b71c1c'>{error.current_value}</span>"


def _format_feature_id(feat_result: FeatureValidationResult) -> str:
    """Format the feature ID cell"""
    if feat_result.client_id and feat_result.feature_id != feat_result.client_id:
        return f"{feat_result.client_id}<br/><small style='color:#666'>({feat_result.feature_id})</small>"
    return feat_result.display_id


def _build_error_rows(feat_result: FeatureValidationResult) -> List[str]:
    """Build HTML table rows for a feature's errors"""
    rows = []
    id_cell = _format_feature_id(feat_result)
    
    for error in feat_result.errors:
        issue = _format_error_issue(error)
        allowed_cell = _format_allowed_values(error.allowed_values)
        rows.append(
            f"<tr><td style='padding:4px 8px'>{id_cell}</td>"
            f"<td style='padding:4px 8px'>{error.field_name}</td>"
            f"<td style='padding:4px 8px'>{issue}</td>"
            f"<td style='padding:4px 8px;max-width:300px;word-wrap:break-word'>{allowed_cell}</td></tr>"
        )
        id_cell = ""  # Only show ID for first row
    return rows


def _build_layer_section(result: LayerValidationResult) -> str:
    """Build HTML section for a single layer"""
    header = f"<h4>{result.layer_name}</h4>"
    header += f"<p><b>Valid</b>: {result.valid_features}/{result.total_features}</p>"
    
    invalid_features = [r for r in result.feature_results if not r.is_valid]
    if not invalid_features:
        return header
    
    rows = []
    for feat_result in invalid_features:
        rows.extend(_build_error_rows(feat_result))
    
    table = (
        "<table border='1' cellspacing='0' cellpadding='2' style='border-collapse:collapse;width:100%'>"
        "<thead><tr style='background:#f5f5f5'>"
        "<th style='text-align:left;padding:4px 8px'>Feature ID</th>"
        "<th style='text-align:left;padding:4px 8px'>Field</th>"
        "<th style='text-align:left;padding:4px 8px'>Current Value</th>"
        "<th style='text-align:left;padding:4px 8px'>Allowed Values</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )
    return header + table


def create_validation_html_summary(
    layer_results: List[LayerValidationResult],
    title: str = "Validation Results",
    note: str = ""
) -> str:
    """
    Create an HTML summary of validation results.
    
    Args:
        layer_results: List of LayerValidationResult objects
        title: Title for the summary
        note: Optional note to display
        
    Returns:
        HTML string
    """
    sections = [_build_layer_section(result) for result in layer_results]
    note_html = f"<p>{note}</p>" if note else ""
    
    return (
        f"<div style='font-family:Sans-Serif'><h3>{title}</h3>"
        f"{note_html}{''.join(sections)}</div>"
    )
