"""
UI package for BNG AI QGIS Plugin.

This package contains all user interface components including:
- Dock widget (main plugin UI)
- Tabs (Projects, Login, Map)
- Dialogs (Config, Sync Results)
- Reusable components

Usage:
    from bngai.ui.styles import STYLES, apply_style
    from bngai.ui.dock.widget import BngAiDockWidget
"""

from .styles import STYLES, COLORS

__all__ = ['STYLES', 'COLORS']

