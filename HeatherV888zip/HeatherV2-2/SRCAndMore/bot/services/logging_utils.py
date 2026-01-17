"""
Logging Utilities Module

Provides structured logging for gateway errors and metrics.
"""

import os
import json
from datetime import datetime

__all__ = [
    'log_gateway_error',
    'log_error_metric',
]


def log_gateway_error(gateway_name: str, card_bin: str, error_type: str, error_msg: str, user_id: int = None, elapsed_ms: int = None):
    """Log gateway errors to file for debugging"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_path = "logs/gateway_errors.log"
    
    log_entry = f"[{timestamp}] GATEWAY: {gateway_name}\n"
    log_entry += f"  BIN: {card_bin}\n"
    log_entry += f"  ERROR TYPE: {error_type}\n"
    log_entry += f"  MESSAGE: {error_msg}\n"
    if user_id:
        log_entry += f"  USER: {user_id}\n"
    if elapsed_ms:
        log_entry += f"  ELAPSED: {elapsed_ms}ms\n"
    log_entry += "-" * 60 + "\n"
    
    try:
        os.makedirs("logs", exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"[!] Failed to log gateway error: {e}")


def log_error_metric(gateway_name: str, error_type: str, card_bin: str = None):
    """Log error metrics for aggregation and analysis"""
    log_path = "logs/error_metrics.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    metric = {
        'timestamp': timestamp,
        'gateway': gateway_name,
        'error_type': error_type,
        'card_bin': card_bin or 'unknown'
    }
    
    try:
        os.makedirs("logs", exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(metric) + "\n")
    except Exception as e:
        print(f"[!] Failed to log error metric: {e}")
