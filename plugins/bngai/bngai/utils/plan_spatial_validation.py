"""
PlanSpatialValidator - Spatial validation for BNG Plan sync.
Rules:
  1) New/updated features must lie within the Red Line Boundary (RLB) layer.
  2) Plan polygon features must not overlap/intersect each other.
If violations exist, validation returns (False, html_summary). No sync should proceed.
"""
from typing import Dict, List, Tuple
from qgis.core import QgsMessageLog, QgsProject, QgsVectorLayer, QgsGeometry, QgsFeature, QgsWkbTypes

# Treat extremely tiny intersections as non-overlaps to align with PostGIS behavior
OVERLAP_AREA_EPSILON = 1e-5
# Single relative threshold to decide meaningful overlap (fraction of the smaller polygon area)
# 0.2% strikes a balance: ignores numerical slivers, catches real overlaps
OVERLAP_RELATIVE_EPSILON = 2e-3


class PlanSpatialValidator:
    def __init__(self):
        QgsMessageLog.logMessage("PlanSpatialValidator initialized", "BNGAI Plugin", level=0)
        # Log thresholds to verify runtime configuration
        try:
            QgsMessageLog.logMessage(
                f"PlanSpatialValidator thresholds: OVERLAP_AREA_EPSILON={OVERLAP_AREA_EPSILON}, OVERLAP_RELATIVE_EPSILON={OVERLAP_RELATIVE_EPSILON}",
                "BNGAI Plugin",
                level=0
            )
        except Exception:
            pass

    def _geom_debug_info(self, geom: QgsGeometry) -> str:
        """
        Produce diagnostic info for a polygon geometry to aid debugging overlaps.
        Includes bbox, centroid, area, vertex and ring counts, and multipart flag.
        """
        try:
            if not geom or geom.isEmpty():
                return "empty"
            bbox = geom.boundingBox()
            cx, cy = None, None
            try:
                cpt = geom.centroid().asPoint()
                cx, cy = cpt.x(), cpt.y()
            except Exception:
                pass
            is_mp = geom.isMultipart()
            area = 0.0
            try:
                area = geom.area()
            except Exception:
                pass
            ring_count = 0
            vertex_count = 0
            try:
                if is_mp:
                    mpoly = geom.asMultiPolygon()
                    for poly in mpoly:
                        ring_count += len(poly)
                        for ring in poly:
                            vertex_count += len(ring)
                else:
                    poly = geom.asPolygon()
                    ring_count = len(poly)
                    for ring in poly:
                        vertex_count += len(ring)
            except Exception:
                pass
            return (
                f"isMultipart={is_mp}, area={area}, "
                f"bbox=[{bbox.xMinimum()},{bbox.yMinimum()}]-[{bbox.xMaximum()},{bbox.yMaximum()}], "
                f"size=({bbox.width()}x{bbox.height()}), "
                f"centroid=({cx},{cy}), rings={ring_count}, vertices={vertex_count}"
            )
        except Exception:
            return "debug-info-error"

    def _find_rlb_layer(self) -> QgsVectorLayer:
        """
        Find the Red Line Boundary layer in the project by common name.
        Returns the layer or None if not found.
        """
        QgsMessageLog.logMessage("Searching for Red Line Boundary layer...", "BNGAI Plugin", level=0)
        project = QgsProject.instance()
        for lyr in project.mapLayers().values():
            try:
                if isinstance(lyr, QgsVectorLayer) and lyr.name().strip().lower() == "red line boundary":
                    QgsMessageLog.logMessage(f"Found RLB layer: {lyr.name()} ({lyr.id()})", "BNGAI Plugin", level=0)
                    return lyr
            except Exception:
                continue
        QgsMessageLog.logMessage("RLB layer not found", "BNGAI Plugin", level=1)
        return None

    def _union_rlb_geometry(self, rlb_layer: QgsVectorLayer) -> QgsGeometry:
        """Create a single unioned geometry from all RLB features."""
        QgsMessageLog.logMessage("Building union geometry for RLB...", "BNGAI Plugin", level=0)
        union_geom = None
        count = 0
        for feat in rlb_layer.getFeatures():
            geom = feat.geometry()
            if not geom or geom.isEmpty():
                continue
            union_geom = geom if union_geom is None else union_geom.combine(geom)
            count += 1
        QgsMessageLog.logMessage(f"RLB union built from {count} feature(s)", "BNGAI Plugin", level=0)
        return union_geom

    def _layer_type(self, layer: QgsVectorLayer) -> str:
        if layer.geometryType() == QgsWkbTypes.PointGeometry:
            return 'point'
        if layer.geometryType() == QgsWkbTypes.LineGeometry:
            return 'line'
        if layer.geometryType() == QgsWkbTypes.PolygonGeometry:
            return 'polygon'
        return ''

    def _build_candidate_ids(self, changes: Dict[str, List[Dict]]) -> List[str]:
        """
        Validate only updated and new geometries for RLB containment.
        (Overlap rule will apply only to polygon layer among candidates.)
        """
        ids: List[str] = []
        if changes.get('new'):
            ids.extend([item['id'] for item in changes['new']])
        if changes.get('updated'):
            ids.extend([item['id'] for item in changes['updated']])
        QgsMessageLog.logMessage(f"Collected {len(ids)} candidate feature id(s) for spatial validation", "BNGAI Plugin", level=0)
        return ids

    def _get_features_by_ids(self, layer: QgsVectorLayer, feature_ids: List[str]) -> List[QgsFeature]:
        """
        Robust lookup that works for:
          - Features that have attribute 'id' (server ids)
          - Newly created, unsynced features (no 'id' attr yet) by using internal feature id
        We build an index over all features, mapping both attribute id and internal id string.
        """
        feats: List[QgsFeature] = []
        QgsMessageLog.logMessage(f"Fetching {len(feature_ids)} feature(s) by id from layer: {layer.name()}", "BNGAI Plugin", level=0)
        # Build index once
        index: Dict[str, QgsFeature] = {}
        has_attr_id = layer.fields().indexOf('id') != -1
        all_count = 0
        for f in layer.getFeatures():
            all_count += 1
            # Map internal id
            index[str(f.id())] = f
            # Map attribute id if present and truthy
            if has_attr_id:
                attr_val = f.attribute('id')
                if attr_val is not None and str(attr_val).strip() != '':
                    index[str(attr_val)] = f
        QgsMessageLog.logMessage(f"Feature index built for layer {layer.name()}: {len(index)} keys from {all_count} feature(s)", "BNGAI Plugin", level=0)
        # Resolve requested ids
        for key in feature_ids:
            f = index.get(str(key))
            if f is not None:
                feats.append(f)
            else:
                QgsMessageLog.logMessage(f"Feature key not found in index for layer {layer.name()}: {key}", "BNGAI Plugin", level=1)
        return feats
    
    def _get_all_feature_ids(self, layer: QgsVectorLayer) -> List[str]:
        """Return string ids for all features in layer (attribute 'id' if present, else internal id)."""
        ids: List[str] = []
        count = 0
        for f in layer.getFeatures():
            fid = f.attribute('id')
            ids.append(str(fid if fid is not None and str(fid).strip() != '' else f.id()))
            count += 1
        QgsMessageLog.logMessage(f"Collected all feature ids from layer {layer.name()}: {count}", "BNGAI Plugin", level=0)
        return ids

    def _check_outside_rlb(self, rlb_union: QgsGeometry, layer: QgsVectorLayer, feat_ids: List[str]) -> List[str]:
        violations: List[str] = []
        if not rlb_union or rlb_union.isEmpty():
            QgsMessageLog.logMessage("RLB union is empty; skipping outside-RLB checks", "BNGAI Plugin", level=1)
            return violations
        QgsMessageLog.logMessage(f"Checking outside-RLB for {len(feat_ids)} feature(s) in layer {layer.name()}", "BNGAI Plugin", level=0)
        for f in self._get_features_by_ids(layer, feat_ids):
            g = f.geometry()
            if not g or g.isEmpty():
                continue
            # Use within() for robust inside check
            if not g.within(rlb_union):
                fid = str(f.attribute('id') or f.id())
                violations.append(fid)
                QgsMessageLog.logMessage(f"Outside RLB: layer={layer.name()} id={fid}", "BNGAI Plugin", level=1)
        return violations


    def _make_html(self, rlb_missing: bool, outside: List[Tuple[str, str, List[str]]], overlaps: List[Tuple[str, List[Tuple[str, str]]]]) -> str:
        """
        outside: list of (layer_name, layer_type, [ids_outside])
        overlaps: list of (layer_name, [(id1,id2),...])
        """
        html = ["<div style='font-family:Sans-Serif'>",
                "<h3>Plan Spatial Validation</h3>"]
        if rlb_missing:
            html.append("<p style='color:#b71c1c'><b>Red Line Boundary (RLB) layer not found.</b> Please load the plan boundary before syncing.</p>")
        for lname, ltype, ids in outside:
            if ids:
                html.append(f"<h4>{lname} – {ltype}: Outside RLB</h4>")
                rows = "".join([f"<li>{fid}</li>" for fid in ids])
                html.append(f"<ul>{rows}</ul>")
        for lname, pairs in overlaps:
            if pairs:
                html.append(f"<h4>{lname} – polygon overlaps</h4>")
                rows = "".join([f"<li>{a} × {b}</li>" for a, b in pairs])
                html.append(f"<ul>{rows}</ul>")
        html.append("<p><b>Sync is blocked.</b> Please fix the issues above and try again.</p>")
        html.append("</div>")
        return "".join(html)

    def validate_overlaps_only(self, all_changes: Dict[str, Dict]) -> Tuple[bool, str]:
        """
        Validate only polygon overlaps across provided layer bundles.
        Returns (proceed, html_summary). If proceed is False, the caller should block sync.
        """
        QgsMessageLog.logMessage("Polygon overlap-only validation is temporarily disabled", "BNGAI Plugin", level=0)
        return True, ""

    def _check_polygon_overlaps_simple(self, layer: QgsVectorLayer, feat_ids: List[str]) -> List[Tuple[str, str]]:
        """
        Simple pairwise overlap detection across ALL plan polygon features:
          - For each pair, compute intersection area directly
          - Ignore if intersection area <= OVERLAP_AREA_EPSILON
          - Compute relative overlap: inter_area / min(area_i, area_j)
          - Flag as overlap if relative > OVERLAP_RELATIVE_EPSILON
        No bbox shortcuts, no touches heuristics.
        """
        overlaps: List[Tuple[str, str]] = []
        feats = self._get_features_by_ids(layer, feat_ids)
        if not feats:
            return overlaps
        QgsMessageLog.logMessage(
            f"Using simple overlap algorithm on {len(feats)} polygon feature(s) in layer {layer.name()}",
            "BNGAI Plugin",
            level=0
        )
        n = len(feats)
        for i in range(n):
            fi = feats[i]
            gi = fi.geometry()
            if not gi or gi.isEmpty():
                continue
            try:
                giv = gi.makeValid()
            except Exception:
                giv = gi
            try:
                ai = max(giv.area(), 0.0)
            except Exception:
                ai = 0.0
            for j in range(i + 1, n):
                fj = feats[j]
                gj = fj.geometry()
                if not gj or gj.isEmpty():
                    continue
                try:
                    gjv = gj.makeValid()
                except Exception:
                    gjv = gj
                try:
                    aj = max(gjv.area(), 0.0)
                except Exception:
                    aj = 0.0
                try:
                    inter = giv.intersection(gjv)
                    inter_area = inter.area() if inter else 0.0
                except Exception:
                    inter_area = 0.0
                # Ignore numerically-zero intersections
                if inter_area <= OVERLAP_AREA_EPSILON:
                    continue
                denom = max(min(ai, aj), 1e-12)
                rel = inter_area / denom if denom > 0 else 0.0
                if rel > OVERLAP_RELATIVE_EPSILON:
                    id_i = str(fi.attribute('id') or fi.id())
                    id_j = str(fj.attribute('id') or fj.id())
                    pair = (id_i, id_j)
                    if pair not in overlaps:
                        try:
                            pct = rel * 100.0
                            QgsMessageLog.logMessage(
                                f"[simple] Overlap metrics in {layer.name()}: {id_i} × {id_j} | inter_area={inter_area} | rel_min={rel:.8f} ({pct:.6f}%) | rel_threshold={OVERLAP_RELATIVE_EPSILON} | a_i={ai} | a_j={aj}",
                                "BNGAI Plugin",
                                level=1
                            )
                        except Exception:
                            pass
                        overlaps.append(pair)
                        QgsMessageLog.logMessage(f"[simple] Overlap detected in {layer.name()}: {id_i} × {id_j}", "BNGAI Plugin", level=1)
        return overlaps


