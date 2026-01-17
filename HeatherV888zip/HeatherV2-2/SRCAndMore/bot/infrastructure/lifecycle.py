"""
Bot Lifecycle Management Module

Handles graceful shutdown, signal handlers, and cleanup operations.

Phase 11.5: Extracted from main transferto.py to centralize lifecycle management.
"""

import os
import sys
import signal
from typing import Dict, Any


def handle_shutdown(
    ongoing_checks: Dict[int, Any],
    stop_requested: Dict[int, bool],
    uploaded_files: Dict[int, str],
):
    """
    Handle graceful shutdown on SIGTERM/SIGINT.
    
    Args:
        ongoing_checks: Dictionary of user checks to clear
        stop_requested: Dictionary of stop flags to clear
        uploaded_files: Dictionary of uploaded file paths to clean up
    """
    print("\n[*] Bot shutting down gracefully...")
    
    # Clear ongoing checks
    for user_id in list(ongoing_checks.keys()):
        try:
            del ongoing_checks[user_id]
        except KeyError:
            pass
    
    # Clear stop flags
    for user_id in list(stop_requested.keys()):
        try:
            del stop_requested[user_id]
        except KeyError:
            pass
    
    # Try to clean up temp files
    try:
        for user_id in list(uploaded_files.keys()):
            file_path = uploaded_files[user_id]
            if os.path.exists(file_path):
                os.remove(file_path)
    except Exception as e:
        print(f"[!] Error cleaning up files: {e}")
    
    print("[✓] Cleanup complete. Goodbye!")
    sys.exit(0)


def create_shutdown_handler(
    ongoing_checks: Dict[int, Any],
    stop_requested: Dict[int, bool],
    uploaded_files: Dict[int, str],
):
    """
    Create a shutdown handler closure with access to bot state.
    
    This allows the signal handler to access the necessary state
    for cleanup without using global variables.
    
    Args:
        ongoing_checks: Dictionary of user checks to clear
        stop_requested: Dictionary of stop flags to clear
        uploaded_files: Dictionary of uploaded file paths to clean up
        
    Returns:
        Signal handler function
    """
    def shutdown_handler(signum, frame):
        handle_shutdown(ongoing_checks, stop_requested, uploaded_files)
    
    return shutdown_handler


def register_signal_handlers(
    ongoing_checks: Dict[int, Any],
    stop_requested: Dict[int, bool],
    uploaded_files: Dict[int, str],
):
    """
    Register signal handlers for graceful shutdown.
    
    Handles SIGTERM and SIGINT (Ctrl+C) to ensure proper cleanup.
    
    Args:
        ongoing_checks: Dictionary of user checks to clear
        stop_requested: Dictionary of stop flags to clear
        uploaded_files: Dictionary of uploaded file paths to clean up
    """
    handler = create_shutdown_handler(ongoing_checks, stop_requested, uploaded_files)
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)
    print("[*] Signal handlers registered for graceful shutdown")


__all__ = [
    'handle_shutdown',
    'create_shutdown_handler',
    'register_signal_handlers',
]
