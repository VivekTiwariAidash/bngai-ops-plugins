"""
Centralized logging for BNG AI QGIS Plugin.

This module provides a consistent logging interface across the plugin,
wrapping QGIS message logging with convenience functions.

Usage:
    from ..utils.logging import log_info, log_warn, log_error, logged
    
    log_info("Starting sync operation")
    log_error("Failed to connect", exc=e)
    
    @logged("sync habitats")
    def sync_habitats(self, ...):
        ...
"""
import traceback
from functools import wraps
from typing import Optional, Callable, Any

from qgis.core import QgsMessageLog, Qgis


# Plugin log tag - single source of truth
LOG_TAG = "BNGAI Plugin"


def log_info(message: str) -> None:
    """
    Log an info message.
    
    Args:
        message: Message to log
    """
    QgsMessageLog.logMessage(str(message), LOG_TAG, Qgis.Info)


def log_warn(message: str) -> None:
    """
    Log a warning message.
    
    Args:
        message: Message to log
    """
    QgsMessageLog.logMessage(str(message), LOG_TAG, Qgis.Warning)


def log_error(message: str, exc: Optional[Exception] = None) -> None:
    """
    Log an error message with optional exception details.
    
    Args:
        message: Error message
        exc: Optional exception to include traceback
    """
    full_message = str(message)
    if exc:
        full_message += f"\n{traceback.format_exc()}"
    QgsMessageLog.logMessage(full_message, LOG_TAG, Qgis.Critical)


def log_debug(message: str) -> None:
    """
    Log a debug message (uses Info level in QGIS).
    
    Args:
        message: Debug message
    """
    QgsMessageLog.logMessage(f"[DEBUG] {message}", LOG_TAG, Qgis.Info)


def logged(operation: str) -> Callable:
    """
    Decorator to log function entry/exit and handle errors.
    
    Args:
        operation: Description of the operation being performed
        
    Returns:
        Decorated function
        
    Usage:
        @logged("sync habitats")
        def sync_habitats(self, layers, plan_id):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            log_info(f"Starting: {operation}")
            try:
                result = func(*args, **kwargs)
                log_info(f"Completed: {operation}")
                return result
            except Exception as e:
                log_error(f"Failed: {operation}", exc=e)
                raise
        return wrapper
    return decorator


class LogContext:
    """
    Context manager for logging operation blocks.
    
    Usage:
        with LogContext("loading layers"):
            # operations here
            pass
    """
    
    def __init__(self, operation: str):
        self.operation = operation
    
    def __enter__(self):
        log_info(f"Starting: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            log_error(f"Failed: {self.operation}", exc=exc_val)
            return False  # Re-raise exception
        log_info(f"Completed: {self.operation}")
        return False


# Aliases for compatibility with existing code
info = log_info
warn = log_warn
error = log_error
debug = log_debug

