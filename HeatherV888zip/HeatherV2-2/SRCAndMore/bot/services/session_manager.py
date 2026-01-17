"""
Session management module for batch processing and check tracking.
Extracted from transferto.py for modular organization.
"""
import time

__all__ = [
    'check_numbers',
    'check_status',
    'ongoing_checks',
    'stop_requested',
    'document_queue',
    'concurrent_doc_sessions',
    'batch_sessions',
    'MAX_CONCURRENT_DOCS',
    'get_next_check_number',
    'register_check',
    'unregister_check',
    'is_check_active',
    'request_stop',
    'should_stop',
    'queue_document',
    'get_queued_documents',
    'clear_document_queue',
    'get_active_doc_sessions',
    'count_active_sessions',
    'prune_completed_sessions',
    'remove_processed_docs',
]

check_numbers = {}
check_status = {}
ongoing_checks = {}
stop_requested = {}
document_queue = {}
concurrent_doc_sessions = {}
batch_sessions = {}
MAX_CONCURRENT_DOCS = 5


def get_next_check_number(user_id: int) -> int:
    """Get next check number for user"""
    if user_id not in check_numbers:
        check_numbers[user_id] = 1
    else:
        check_numbers[user_id] += 1
    return check_numbers[user_id]


def register_check(user_id: int, check_num: int):
    """Register a new ongoing check"""
    if user_id not in ongoing_checks:
        ongoing_checks[user_id] = {}
    ongoing_checks[user_id][check_num] = True
    
    if user_id not in stop_requested:
        stop_requested[user_id] = {}
    stop_requested[user_id][check_num] = False


def unregister_check(user_id: int, check_num: int):
    """Unregister a check"""
    if user_id in ongoing_checks and check_num in ongoing_checks[user_id]:
        del ongoing_checks[user_id][check_num]
    if user_id in stop_requested and check_num in stop_requested[user_id]:
        del stop_requested[user_id][check_num]


def is_check_active(user_id: int, check_num: int) -> bool:
    """Check if a specific check is active"""
    return user_id in ongoing_checks and ongoing_checks[user_id].get(check_num, False)


def request_stop(user_id: int, check_num: int):
    """Request stop for a specific check"""
    if user_id in stop_requested:
        stop_requested[user_id][check_num] = True


def should_stop(user_id: int, check_num: int) -> bool:
    """Check if stop was requested for a specific check"""
    return user_id in stop_requested and stop_requested[user_id].get(check_num, False)


def queue_document(user_id: int, file_path: str, filename: str, gate: str = "paypal") -> int:
    """Add a document to the user's processing queue. Returns queue position."""
    if user_id not in document_queue:
        document_queue[user_id] = []
    
    doc_entry = {
        "path": file_path,
        "filename": filename,
        "gate": gate,
        "queued_at": time.time(),
        "status": "queued"
    }
    document_queue[user_id].append(doc_entry)
    return len(document_queue[user_id])


def get_queued_documents(user_id: int) -> list:
    """Get all queued documents for a user"""
    return document_queue.get(user_id, [])


def clear_document_queue(user_id: int):
    """Clear all queued documents for a user"""
    if user_id in document_queue:
        document_queue[user_id] = []


def get_active_doc_sessions(user_id: int) -> list:
    """Get all active document processing sessions for a user"""
    return [
        session for session_id, session in concurrent_doc_sessions.items()
        if session.get("user_id") == user_id and not session.get("completed", False)
    ]


def count_active_sessions(user_id: int) -> int:
    """Count active processing sessions for a user"""
    return len(get_active_doc_sessions(user_id))


def prune_completed_sessions():
    """Remove completed sessions from concurrent_doc_sessions to free up slots"""
    completed_ids = [
        session_id for session_id, session in concurrent_doc_sessions.items()
        if session.get("completed", False)
    ]
    for session_id in completed_ids:
        del concurrent_doc_sessions[session_id]
    return len(completed_ids)


def remove_processed_docs(user_id: int, processed_count: int):
    """Remove only the processed documents from the queue, keep the rest"""
    if user_id in document_queue:
        document_queue[user_id] = document_queue[user_id][processed_count:]
