"""
Habitat Sync Manager - Backward compatibility wrapper.

This module re-exports from the refactored sync package for backward compatibility.
All new code should import directly from gui.projects.sync.

The sync package follows SOLID principles:
- Single Responsibility: Each class has one focused purpose
- Open/Closed: Components can be extended without modification
- Dependency Inversion: High-level modules depend on abstractions

New Structure:
- sync/sync_manager.py: Main orchestrator (HabitatSyncManager)
- sync/feature_comparer.py: Feature comparison logic
- sync/transaction_builder.py: WFS transaction payload builder
- sync/transaction_processor.py: Transaction result processor
- sync/models.py: Data classes (SyncResult, FeatureChange, etc.)
- sync/utils.py: Shared utility functions
"""

# Re-export main class for backward compatibility
from .sync import HabitatSyncManager

# Re-export utility function for any code using it directly
from .sync.utils import normalize_for_compare as _normalize_for_compare

# Alias for backward compatibility
def _normalize_for_compare(v):
    """Legacy alias for normalize_for_compare"""
    from .sync.utils import normalize_for_compare
    return normalize_for_compare(v)

__all__ = ['HabitatSyncManager', '_normalize_for_compare']
