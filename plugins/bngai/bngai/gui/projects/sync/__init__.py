"""
Sync module - Handles synchronization of habitat features between QGIS and server.

This module follows SOLID principles:
- Single Responsibility: Each class has one focused purpose
- Open/Closed: Components can be extended without modification
- Dependency Inversion: High-level modules depend on abstractions

Components:
- HabitatSyncManager: Main facade that orchestrates sync operations
- FeatureComparer: Compares local and server features
- TransactionBuilder: Builds WFS transaction payloads
- TransactionProcessor: Processes transaction results
"""

from .sync_manager import HabitatSyncManager
from .feature_comparer import FeatureComparer
from .transaction_builder import TransactionBuilder
from .transaction_processor import TransactionProcessor
from .models import SyncResult, FeatureChange, TransactionPayload

__all__ = [
    'HabitatSyncManager',
    'FeatureComparer', 
    'TransactionBuilder',
    'TransactionProcessor',
    'SyncResult',
    'FeatureChange',
    'TransactionPayload'
]

