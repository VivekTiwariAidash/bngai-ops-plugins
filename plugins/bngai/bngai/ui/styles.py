"""
Centralized Qt stylesheets for BNG AI QGIS Plugin.

This module provides consistent styling across all UI components.
All colors, styles, and themes are defined here for easy maintenance.

Usage:
    from ..ui.styles import STYLES, COLORS, apply_style
    
    widget.setStyleSheet(STYLES['dropdown'])
    button.setStyleSheet(STYLES['button_primary'])
"""

# =============================================================================
# COLOR PALETTE
# =============================================================================

COLORS = {
    # Primary colors
    'primary': '#4CAF50',
    'primary_hover': '#45A049',
    'primary_dark': '#388E3C',
    
    # Secondary colors
    'secondary': '#2196F3',
    'secondary_hover': '#1976D2',
    
    # Status colors
    'success': '#4CAF50',
    'warning': '#FF9800',
    'error': '#F44336',
    'info': '#2196F3',
    
    # Neutral colors
    'background': '#F5F5F5',
    'background_dark': '#E8E8E8',
    'background_white': '#FFFFFF',
    'border': '#E0E0E0',
    'border_dark': '#BDBDBD',
    
    # Text colors
    'text_primary': '#333333',
    'text_secondary': '#666666',
    'text_disabled': '#999999',
    'text_white': '#FFFFFF',
    
    # Accent colors
    'accent_green': '#00A300',
    'accent_green_hover': '#008000',
    'accent_red': '#FF0000',
}


# =============================================================================
# COMPONENT STYLES
# =============================================================================

# Dropdown/ComboBox styles
DROPDOWN = f"""
    QComboBox {{
        padding: 8px;
        background: {COLORS['background']};
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        min-height: 16px;
        color: {COLORS['text_primary']};
    }}
    QComboBox:hover {{
        border-color: {COLORS['border_dark']};
    }}
    QComboBox:focus {{
        border-color: {COLORS['primary']};
    }}
    QComboBox:disabled {{
        background: {COLORS['background_dark']};
        color: {COLORS['text_disabled']};
    }}
    QComboBox::drop-down {{
        border: none;
        padding-right: 10px;
    }}
    QComboBox::down-arrow {{
        image: url(:/images/themes/default/mActionArrowDown.svg);
        width: 12px;
        height: 12px;
    }}
    QComboBox QAbstractItemView {{
        background: {COLORS['background_white']};
        border: 1px solid {COLORS['border']};
        selection-background-color: {COLORS['background']};
        selection-color: {COLORS['text_primary']};
    }}
    QComboBox QAbstractItemView::item {{
        padding: 6px;
        min-height: 24px;
    }}
    QComboBox QAbstractItemView::item:hover {{
        background: {COLORS['background']};
        color: {COLORS['text_primary']};
        font-weight: bold;
    }}
    QComboBox QAbstractItemView::item:selected {{
        background: {COLORS['background_dark']};
        color: {COLORS['text_primary']};
        font-weight: bold;
    }}
"""

# Primary button (green, prominent action)
BUTTON_PRIMARY = f"""
    QPushButton {{
        padding: 8px 16px;
        background: {COLORS['primary']};
        color: {COLORS['text_white']};
        border: none;
        border-radius: 4px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background: {COLORS['primary_hover']};
    }}
    QPushButton:pressed {{
        background: {COLORS['primary_dark']};
    }}
    QPushButton:disabled {{
        background: {COLORS['background_dark']};
        color: {COLORS['text_disabled']};
    }}
"""

# Secondary button (outlined, less prominent)
BUTTON_SECONDARY = f"""
    QPushButton {{
        padding: 8px 16px;
        background: {COLORS['background']};
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        color: {COLORS['text_primary']};
    }}
    QPushButton:hover {{
        background: {COLORS['background_dark']};
    }}
    QPushButton:pressed {{
        background: {COLORS['border']};
    }}
    QPushButton:disabled {{
        background: {COLORS['background']};
        color: {COLORS['text_disabled']};
    }}
"""

# Danger button (red, destructive action)
BUTTON_DANGER = f"""
    QPushButton {{
        padding: 8px 16px;
        background: {COLORS['error']};
        color: {COLORS['text_white']};
        border: none;
        border-radius: 4px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background: #D32F2F;
    }}
    QPushButton:pressed {{
        background: #B71C1C;
    }}
    QPushButton:disabled {{
        background: {COLORS['background_dark']};
        color: {COLORS['text_disabled']};
    }}
"""

# Refresh button (icon button, transparent background)
BUTTON_REFRESH = f"""
    QPushButton {{
        border: none;
        padding: 5px;
        color: {COLORS['accent_green']};
        text-align: right;
        background: transparent;
    }}
    QPushButton:hover {{
        color: {COLORS['accent_green_hover']};
    }}
    QPushButton:disabled {{
        color: {COLORS['text_disabled']};
    }}
"""

# Icon button (minimal, just icon)
BUTTON_ICON = f"""
    QPushButton {{
        border: none;
        padding: 4px;
        background: transparent;
    }}
    QPushButton:hover {{
        background: {COLORS['background']};
        border-radius: 4px;
    }}
    QPushButton:pressed {{
        background: {COLORS['background_dark']};
    }}
"""

# Status label
LABEL_STATUS = f"""
    QLabel {{
        color: {COLORS['text_primary']};
        font-weight: bold;
        padding: 5px;
        margin-bottom: 10px;
    }}
"""

LABEL_STATUS_ERROR = f"""
    QLabel {{
        color: {COLORS['error']};
        font-weight: bold;
        padding: 5px;
        margin-bottom: 10px;
    }}
"""

LABEL_STATUS_SUCCESS = f"""
    QLabel {{
        color: {COLORS['success']};
        font-weight: bold;
        padding: 5px;
        margin-bottom: 10px;
    }}
"""

# Section header label
LABEL_SECTION = f"""
    QLabel {{
        font-size: 14px;
        font-weight: bold;
        color: {COLORS['text_primary']};
    }}
"""

# Group box
GROUP_BOX = f"""
    QGroupBox {{
        font-weight: bold;
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        margin-top: 12px;
        padding-top: 12px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        color: {COLORS['text_primary']};
    }}
"""

# Text input
TEXT_INPUT = f"""
    QLineEdit {{
        padding: 8px;
        background: {COLORS['background_white']};
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        color: {COLORS['text_primary']};
    }}
    QLineEdit:hover {{
        border-color: {COLORS['border_dark']};
    }}
    QLineEdit:focus {{
        border-color: {COLORS['primary']};
    }}
    QLineEdit:disabled {{
        background: {COLORS['background']};
        color: {COLORS['text_disabled']};
    }}
"""

# Text area
TEXT_AREA = f"""
    QTextEdit {{
        padding: 8px;
        background: {COLORS['background_white']};
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        color: {COLORS['text_primary']};
    }}
    QTextEdit:focus {{
        border-color: {COLORS['primary']};
    }}
"""

# Progress bar
PROGRESS_BAR = f"""
    QProgressBar {{
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        background: {COLORS['background']};
        text-align: center;
    }}
    QProgressBar::chunk {{
        background: {COLORS['primary']};
        border-radius: 3px;
    }}
"""

# Tab widget
TAB_WIDGET = f"""
    QTabWidget::pane {{
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        background: {COLORS['background_white']};
    }}
    QTabBar::tab {{
        padding: 8px 16px;
        background: {COLORS['background']};
        border: 1px solid {COLORS['border']};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }}
    QTabBar::tab:selected {{
        background: {COLORS['background_white']};
        border-bottom: 1px solid {COLORS['background_white']};
    }}
    QTabBar::tab:hover {{
        background: {COLORS['background_dark']};
    }}
"""

# Scrollbar
SCROLLBAR = f"""
    QScrollBar:vertical {{
        border: none;
        background: {COLORS['background']};
        width: 10px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {COLORS['border_dark']};
        min-height: 20px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {COLORS['text_secondary']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
"""


# =============================================================================
# STYLES DICTIONARY
# =============================================================================
# Unified access to all styles

STYLES = {
    # Dropdowns
    'dropdown': DROPDOWN,
    'combobox': DROPDOWN,
    
    # Buttons
    'button_primary': BUTTON_PRIMARY,
    'button_secondary': BUTTON_SECONDARY,
    'button_danger': BUTTON_DANGER,
    'button_refresh': BUTTON_REFRESH,
    'button_icon': BUTTON_ICON,
    
    # Labels
    'label_status': LABEL_STATUS,
    'label_status_error': LABEL_STATUS_ERROR,
    'label_status_success': LABEL_STATUS_SUCCESS,
    'label_section': LABEL_SECTION,
    
    # Containers
    'group_box': GROUP_BOX,
    'tab_widget': TAB_WIDGET,
    
    # Inputs
    'text_input': TEXT_INPUT,
    'text_area': TEXT_AREA,
    
    # Progress
    'progress_bar': PROGRESS_BAR,
    
    # Scrollbar
    'scrollbar': SCROLLBAR,
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def apply_style(widget, style_name: str) -> None:
    """
    Apply a named style to a widget.
    
    Args:
        widget: Qt widget to style
        style_name: Name of style from STYLES dict
    """
    if style_name in STYLES:
        widget.setStyleSheet(STYLES[style_name])


def get_status_style(is_error: bool = False, is_success: bool = False) -> str:
    """
    Get appropriate status label style.
    
    Args:
        is_error: If True, return error style
        is_success: If True, return success style
        
    Returns:
        Style string
    """
    if is_error:
        return LABEL_STATUS_ERROR
    if is_success:
        return LABEL_STATUS_SUCCESS
    return LABEL_STATUS


def combine_styles(*style_names: str) -> str:
    """
    Combine multiple styles into one.
    
    Args:
        *style_names: Names of styles to combine
        
    Returns:
        Combined style string
    """
    styles = []
    for name in style_names:
        if name in STYLES:
            styles.append(STYLES[name])
    return '\n'.join(styles)

