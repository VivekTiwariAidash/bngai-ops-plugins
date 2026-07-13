"""
BNG AI Sync Module - Synchronizes habitat data with server.

This module provides a clean, top-level interface for habitat synchronization.
It follows clean architecture principles with clear separation of concerns:

- models.py: Data structures (dataclasses, enums)
- manager.py: Orchestration facade
- comparer.py: Change detection
- builder.py: Transaction payload construction
- processor.py: Result processing

Usage:
    from bngai.sync import HabitatSyncManager, SyncResult
    
    manager = HabitatSyncManager(api_client)
    success, msg, html, csv = manager.sync_habitats(layers, plan_id, org_id)

Or import specific models:
    from bngai.sync import ChangeSet, FeatureChange, OperationType
"""

# Re-export from gui/projects/sync for backward compatibility
# This allows cleaner imports while keeping code in original location

from .manager import HabitatSyncManager
from .models import (
    # Enums
    OperationType,
    SyncStatus,
    # Data classes
    FeatureChange,
    ChangeSet,
    TransactionPayload,
    OperationResult,
    TransactionResult,
    SyncResult,
)
from .comparer import FeatureComparer
from .builder import TransactionBuilder
from .processor import TransactionProcessor

__all__ = [
    # Main facade
    'HabitatSyncManager',
    
    # Enums
    'OperationType',
    'SyncStatus',
    
    # Data classes
    'FeatureChange',
    'ChangeSet',
    'TransactionPayload',
    'OperationResult',
    'TransactionResult',
    'SyncResult',
    
    # Components (for advanced usage)
    'FeatureComparer',
    'TransactionBuilder',
    'TransactionProcessor',
]

