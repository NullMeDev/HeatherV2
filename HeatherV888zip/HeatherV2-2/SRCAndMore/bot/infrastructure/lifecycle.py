"""
Bot Lifecycle Management Module

Handles graceful shutdown, signal handlers, and cleanup operations.

Phase 11.5: Extracted from main transferto.py to centralize lifecycle management.
Phase 12.1: Added session pool cleanup on shutdown.
Phase 12.2: Added async proxy pool cleanup on shutdown.
"""

import os
import sys
import signal
import asyncio
from typing import Dict, Any


async def cleanup_resources(
    ongoing_checks: Dict[int, Any],
    stop_requested: Dict[int, bool],
    uploaded_files: Dict[int, str],
):
    """
    Cleanup all bot resources asynchronously.
    
    Args:
        ongoing_checks: Dictionary of user checks to clear
        stop_requested: Dictionary of stop flags to clear
        uploaded_files: Dictionary of uploaded file paths to clean up
    """
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
    
    # Cleanup session pool (Phase 12.1)
    try:
        from bot.infrastructure.session_pool import cleanup_session_pool
        await cleanup_session_pool()
        print("[✓] Session pool cleaned up")
    except Exception as e:
        print(f"[!] Error cleaning up session pool: {e}")
    
    # Cleanup async proxy pool (Phase 12.2)
    try:
        from bot.infrastructure.proxy_pool import get_proxy_pool
        pool = get_proxy_pool()
        if pool:
            await pool.stop()
            print("[✓] Async proxy pool cleaned up")
    except Exception as e:
        print(f"[!] Error cleaning up proxy pool: {e}")


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
    
    # Run async cleanup
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, schedule cleanup as a task
            asyncio.create_task(cleanup_resources(ongoing_checks, stop_requested, uploaded_files))
        else:
            # If loop is not running, run cleanup synchronously
            loop.run_until_complete(cleanup_resources(ongoing_checks, stop_requested, uploaded_files))
    except Exception as e:
        print(f"[!] Error during async cleanup: {e}")
        # Fallback to synchronous cleanup
        for user_id in list(ongoing_checks.keys()):
            try:
                del ongoing_checks[user_id]
            except KeyError:
                pass
        for user_id in list(stop_requested.keys()):
            try:
                del stop_requested[user_id]
            except KeyError:
                pass
    
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
