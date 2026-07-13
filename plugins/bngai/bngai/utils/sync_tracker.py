"""
Sync Tracker - Tracks API calls and their results during habitat synchronization
"""
import csv
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from qgis.core import QgsMessageLog

# Map internal operation types to user-friendly names
OPERATION_DISPLAY_NAMES = {
    'INSERT': 'New Habitat',
    'UPDATE': 'Update',
    'DELETE': 'Delete'
}

# Map layer type identifiers to user-friendly names
LAYER_DISPLAY_NAMES = {
    'polygon': 'Plan Habitat',
    'plan_polygon': 'Plan Habitat',
    'line': 'Watercourse/Hedgerow',
    'plan_line': 'Watercourse/Hedgerow',
    'point': 'Tree',
    'plan_point': 'Tree'
}


class SyncTracker:
    """
    Tracks API calls and their results during habitat synchronization.
    Provides functionality to export results to CSV.
    """
    
    def __init__(self):
        """Initialize the sync tracker"""
        self.reset()
    
    def reset(self):
        """Reset all tracking data"""
        self.operations = []
        self.start_time = datetime.now()
        
    def add_operation(self, operation_type: str, feature_id: str, api_name: str, 
                     success: bool, error_message: Optional[str] = None,
                     additional_data: Optional[Dict] = None):
        """
        Add an operation to the tracker
        
        Args:
            operation_type: Type of operation (INSERT, UPDATE, DELETE)
            feature_id: ID of the feature being operated on
            api_name: Name of the API endpoint called
            success: Whether the operation was successful
            error_message: Error message if operation failed
            additional_data: Any additional data to store (should include 'layerName' and 'layerType')
        """
        self.operations.append({
            'timestamp': datetime.now(),
            'operation_type': operation_type,
            'feature_id': feature_id,
            'api_name': api_name,
            'success': success,
            'error_message': error_message,
            'additional_data': additional_data or {}
        })
    
    def _get_display_operation(self, op_type: str) -> str:
        """Get user-friendly operation name"""
        return OPERATION_DISPLAY_NAMES.get(op_type, op_type)
    
    def _get_display_layer_type(self, layer_type: str) -> str:
        """Get user-friendly layer type name"""
        if layer_type:
            return LAYER_DISPLAY_NAMES.get(layer_type.lower(), layer_type)
        return 'Unknown'
        
    def get_html_summary(self) -> str:
        """
        Get HTML formatted summary of operations with detailed breakdown.
        
        Returns:
            str: HTML summary
        """
        if not self.operations:
            return "<p>No sync operations performed.</p>"
        
        # Calculate totals
        total_success = sum(1 for op in self.operations if op['success'])
        total_failed = sum(1 for op in self.operations if not op['success'])
        
        # Group by operation type and layer
        stats_by_op = {}  # {op_type: {layer_type: {success: [], failed: []}}}
        
        for op in self.operations:
            op_type = op['operation_type']
            layer_type = op['additional_data'].get('layerType', 'unknown')
            layer_name = op['additional_data'].get('layerName', '')
            
            if op_type not in stats_by_op:
                stats_by_op[op_type] = {}
            if layer_type not in stats_by_op[op_type]:
                stats_by_op[op_type][layer_type] = {
                    'success': [], 
                    'failed': [], 
                    'layer_name': layer_name
                }
            
            if op['success']:
                stats_by_op[op_type][layer_type]['success'].append(op)
            else:
                stats_by_op[op_type][layer_type]['failed'].append(op)
        
        # Build HTML
        html = self._build_summary_header(total_success, total_failed)
        html += self._build_operations_table(stats_by_op)
        html += self._build_details_section(stats_by_op)
        html += self._build_error_section(stats_by_op)
        
        return html
    
    def _build_summary_header(self, total_success: int, total_failed: int) -> str:
        """Build the summary header section"""
        status_color = '#2E7D32' if total_failed == 0 else '#C62828'
        status_icon = '✓' if total_failed == 0 else '⚠'
        status_text = 'Sync Completed Successfully' if total_failed == 0 else 'Sync Completed with Errors'
        
        return f"""
        <div style='padding: 10px; margin-bottom: 15px; background: #f5f5f5; border-radius: 5px;'>
            <h2 style='color: {status_color}; margin: 0;'>{status_icon} {status_text}</h2>
            <p style='margin: 5px 0 0 0; color: #666;'>
                Total: <strong style='color: #2E7D32;'>{total_success} succeeded</strong>
                {f", <strong style='color: #C62828;'>{total_failed} failed</strong>" if total_failed > 0 else ""}
            </p>
        </div>
        """
    
    def _build_operations_table(self, stats_by_op: Dict) -> str:
        """Build the operations summary table"""
        html = """
        <h3>Operations Summary</h3>
        <table border="1" cellpadding="8" style="border-collapse: collapse; width: 100%;">
            <tr style="background: #e0e0e0;">
                <th>Operation</th>
                <th>Layer Type</th>
                <th style="color: #2E7D32;">✓ Synced</th>
                <th style="color: #C62828;">✗ Failed</th>
            </tr>
        """
        
        # Order: New Habitat, Update, Delete
        op_order = ['INSERT', 'UPDATE', 'DELETE']
        
        for op_type in op_order:
            if op_type not in stats_by_op:
                continue
            
            layers = stats_by_op[op_type]
            op_display = self._get_display_operation(op_type)
            first_row = True
            
            for layer_type, data in layers.items():
                layer_display = self._get_display_layer_type(layer_type)
                success_count = len(data['success'])
                failed_count = len(data['failed'])
                
                # Style for success/failure counts
                success_style = "color: #2E7D32; font-weight: bold;" if success_count > 0 else "color: #999;"
                failed_style = "color: #C62828; font-weight: bold;" if failed_count > 0 else "color: #999;"
                
                html += f"""
            <tr>
                <td><strong>{op_display if first_row else ''}</strong></td>
                <td>{layer_display}</td>
                <td style="{success_style}">{success_count}</td>
                <td style="{failed_style}">{failed_count}</td>
            </tr>
                """
                first_row = False
        
        html += "</table>"
        return html
    
    def _build_details_section(self, stats_by_op: Dict) -> str:
        """Build the synced features details section"""
        # Check if there are any successful operations to show
        has_success = any(
            len(data['success']) > 0 
            for layers in stats_by_op.values() 
            for data in layers.values()
        )
        
        if not has_success:
            return ""
        
        html = """
        <h3>Synced Features</h3>
        <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%; font-size: 12px;">
            <tr style="background: #e8f5e9;">
                <th>Operation</th>
                <th>Layer Type</th>
                <th>Feature ID</th>
                <th>Details</th>
            </tr>
        """
        
        op_order = ['INSERT', 'UPDATE', 'DELETE']
        
        for op_type in op_order:
            if op_type not in stats_by_op:
                continue
            
            for layer_type, data in stats_by_op[op_type].items():
                op_display = self._get_display_operation(op_type)
                layer_display = self._get_display_layer_type(layer_type)
                
                for op in data['success']:
                    feature_id = op['feature_id']
                    # Truncate long IDs
                    display_id = feature_id[:12] + '...' if len(str(feature_id)) > 15 else feature_id
                    
                    # Get details from additional_data
                    aidash_code = op['additional_data'].get('aiDashCode', '')
                    details = f"Code: {aidash_code}" if aidash_code else ""
                    
                    html += f"""
            <tr>
                <td>{op_display}</td>
                <td>{layer_display}</td>
                <td title="{feature_id}">{display_id}</td>
                <td>{details}</td>
            </tr>
                    """
        
        html += "</table>"
        return html
    
    def _build_error_section(self, stats_by_op: Dict) -> str:
        """Build the error details section"""
        # Check if there are any errors
        has_errors = any(
            len(data['failed']) > 0 
            for layers in stats_by_op.values() 
            for data in layers.values()
        )
        
        if not has_errors:
            return ""
        
        html = """
        <h3 style="color: #C62828;">Failed Operations</h3>
        <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%; font-size: 12px;">
            <tr style="background: #ffebee;">
                <th>Operation</th>
                <th>Layer Type</th>
                <th>Feature ID</th>
                <th>Error</th>
            </tr>
        """
        
        op_order = ['INSERT', 'UPDATE', 'DELETE']
        
        for op_type in op_order:
            if op_type not in stats_by_op:
                continue
            
            for layer_type, data in stats_by_op[op_type].items():
                op_display = self._get_display_operation(op_type)
                layer_display = self._get_display_layer_type(layer_type)
                
                for op in data['failed']:
                    feature_id = op['feature_id']
                    display_id = feature_id[:12] + '...' if len(str(feature_id)) > 15 else feature_id
                    error_msg = op.get('error_message', 'Unknown error')
                    
                    html += f"""
            <tr>
                <td>{op_display}</td>
                <td>{layer_display}</td>
                <td title="{feature_id}">{display_id}</td>
                <td style="color: #C62828;">{error_msg}</td>
            </tr>
                    """
        
        html += "</table>"
        return html
        
    def export_to_csv(self, output_dir: str) -> str:
        """
        Export operations to CSV file
        
        Args:
            output_dir: Directory to save the CSV file
            
        Returns:
            str: Path to the created CSV file
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = self.start_time.strftime('%Y%m%d_%H%M%S')
        filename = f'sync_operations_{timestamp}.csv'
        filepath = os.path.join(output_dir, filename)
        
        # Write operations to CSV
        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = ['timestamp', 'operation_type', 'feature_id', 'api_name', 
                        'success', 'error_message', 'additional_data']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for op in self.operations:
                # Convert additional_data to string if present
                op_data = op.copy()
                if op_data['additional_data']:
                    op_data['additional_data'] = json.dumps(op_data['additional_data'])
                writer.writerow(op_data)
        
        return filepath 