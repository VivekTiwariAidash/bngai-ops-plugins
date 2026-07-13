"""
Data models for sync operations.

These dataclasses provide type-safe containers for sync data,
improving code readability and reducing errors.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class OperationType(Enum):
    """Types of sync operations"""
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class SyncStatus(Enum):
    """Status of sync operations"""
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"
    PENDING = "PENDING"


@dataclass
class FeatureChange:
    """Represents a single feature change detected during sync"""
    feature_id: str
    operation: OperationType
    local_feature: Optional[Any] = None  # QgsFeature
    server_data: Optional[Dict] = None
    client_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging/serialization"""
        return {
            'feature_id': self.feature_id,
            'operation': self.operation.value,
            'client_id': self.client_id
        }


@dataclass
class ChangeSet:
    """Collection of all changes for a layer"""
    inserts: List[FeatureChange] = field(default_factory=list)
    updates: List[FeatureChange] = field(default_factory=list)
    deletes: List[FeatureChange] = field(default_factory=list)
    
    @property
    def total_count(self) -> int:
        """Total number of changes"""
        return len(self.inserts) + len(self.updates) + len(self.deletes)
    
    @property
    def is_empty(self) -> bool:
        """Check if there are no changes"""
        return self.total_count == 0
    
    def to_legacy_format(self) -> Dict[str, List]:
        """Convert to legacy format for backward compatibility"""
        return {
            'new': [{'id': c.feature_id, 'data': {'feature': c.local_feature}} for c in self.inserts],
            'updated': [{'id': c.feature_id, 'data': {'feature': c.local_feature}, 'old_data': c.server_data} for c in self.updates],
            'deleted': [{'id': c.feature_id, 'data': c.server_data} for c in self.deletes]
        }


@dataclass
class TransactionPayload:
    """WFS Transaction request payload"""
    version: str = "2.0.0"
    insert: List[Dict] = field(default_factory=list)
    update: List[Dict] = field(default_factory=list)
    delete: List[Dict] = field(default_factory=list)
    
    @property
    def is_empty(self) -> bool:
        """Check if payload has no operations"""
        return not self.insert and not self.update and not self.delete
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API request"""
        return {
            'version': self.version,
            'insert': self.insert,
            'update': self.update,
            'delete': self.delete
        }
    
    @property
    def summary(self) -> str:
        """Get summary string of operations"""
        return f"{len(self.insert)} inserts, {len(self.update)} updates, {len(self.delete)} deletes"


@dataclass
class OperationResult:
    """Result of a single operation from transaction response"""
    feature_id: str
    client_id: Optional[str]
    status: SyncStatus
    operation: OperationType
    server_id: Optional[str] = None  # New server ID for inserts
    error_message: Optional[str] = None  # reason from status object
    error_code: Optional[str] = None  # errorCode from status object
    error_field: Optional[str] = None  # field from status object
    properties: Optional[Dict] = None


@dataclass
class TransactionResult:
    """Complete result of a WFS transaction"""
    success: bool
    total_inserted: int = 0
    total_updated: int = 0
    total_deleted: int = 0
    insert_results: List[OperationResult] = field(default_factory=list)
    update_results: List[OperationResult] = field(default_factory=list)
    delete_results: List[OperationResult] = field(default_factory=list)
    error_message: Optional[str] = None
    
    @classmethod
    def _parse_status(cls, item: Dict) -> tuple:
        """
        Parse status object from feature response.
        
        Status can be at item level or inside properties:
        - item.status (legacy)
        - item.properties.status (new format)
        
        Status object format:
        "status": {
            "code": "SUCCESS" or "FAILED",
            "success": true/false,
            "failed": true/false,
            "reason": "Error reason",
            "errorCode": "ERROR_CODE",
            "field": "field_name"
        }
        
        Returns:
            Tuple of (SyncStatus, error_message, error_code, error_field)
        """
        # Look for status in properties first, then at item level
        props = item.get('properties', {})
        status_obj = props.get('status') or item.get('status', {})
        
        # Handle status object format
        if isinstance(status_obj, dict):
            # Check 'code' first, then 'success' boolean
            code = str(status_obj.get('code', '')).upper()
            if code == 'SUCCESS' or status_obj.get('success') is True:
                status = SyncStatus.SUCCESS
            else:
                status = SyncStatus.FAIL
            error_message = status_obj.get('reason')
            error_code = status_obj.get('errorCode')
            error_field = status_obj.get('field')
        else:
            # Fallback for legacy string format
            status_str = str(status_obj).upper() if status_obj else ''
            status = SyncStatus.SUCCESS if status_str == 'SUCCESS' else SyncStatus.FAIL
            error_message = None
            error_code = None
            error_field = None
        
        return status, error_message, error_code, error_field
    
    @classmethod
    def from_api_response(cls, response: Optional[Dict]) -> 'TransactionResult':
        """Create TransactionResult from API response"""
        if not response:
            return cls(success=False, error_message="No response from API")
        
        summary = response.get('transactionSummary', {})
        
        result = cls(
            success=True,
            total_inserted=summary.get('totalInserted', 0),
            total_updated=summary.get('totalUpdated', 0),
            total_deleted=summary.get('totalDeleted', 0)
        )
        
        # Parse insert results
        for item in response.get('insertResults', []):
            props = item.get('properties', {})
            status, error_msg, error_code, error_field = cls._parse_status(item)
            
            result.insert_results.append(OperationResult(
                feature_id=item.get('id', ''),
                client_id=props.get('clientId'),
                status=status,
                operation=OperationType.INSERT,
                server_id=item.get('id'),
                error_message=error_msg,
                error_code=error_code,
                error_field=error_field,
                properties=props
            ))
            
            if status == SyncStatus.FAIL:
                result.success = False
        
        # Parse update results
        for item in response.get('updateResults', []):
            props = item.get('properties', {})
            status, error_msg, error_code, error_field = cls._parse_status(item)
            
            result.update_results.append(OperationResult(
                feature_id=item.get('id', ''),
                client_id=props.get('clientId'),
                status=status,
                operation=OperationType.UPDATE,
                error_message=error_msg,
                error_code=error_code,
                error_field=error_field,
                properties=props
            ))
            
            if status == SyncStatus.FAIL:
                result.success = False
        
        # Parse delete results
        for item in response.get('deleteResults', []):
            props = item.get('properties', {})
            status, error_msg, error_code, error_field = cls._parse_status(item)
            
            result.delete_results.append(OperationResult(
                feature_id=item.get('id', ''),
                client_id=props.get('clientId'),
                status=status,
                operation=OperationType.DELETE,
                error_message=error_msg,
                error_code=error_code,
                error_field=error_field,
                properties=props
            ))
            
            if status == SyncStatus.FAIL:
                result.success = False
        
        return result


@dataclass
class SyncResult:
    """Final result of the sync operation"""
    success: bool
    message: str
    html_summary: str = ""
    csv_path: str = ""
    changes_summary: Optional[Dict] = None
    
    @classmethod
    def error(cls, message: str) -> 'SyncResult':
        """Create an error result"""
        return cls(success=False, message=message)
    
    @classmethod
    def no_changes(cls) -> 'SyncResult':
        """Create a 'no changes' result"""
        html = """
        <div style='text-align: center; padding: 20px;'>
            <h3 style='color: #2E7D32;'>✓ All Features are in Sync</h3>
            <p style='color: #555;'>No changes were detected between local and server data.</p>
        </div>
        """
        return cls(success=True, message="No changes to sync", html_summary=html)

