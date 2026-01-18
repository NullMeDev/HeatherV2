"""
Mass Check Service Module

Phase 12.6: Mass File Processing with Concurrency Control
Extracted from transferto.py to reduce monolithic structure.

Manages:
- File-based batch card checking
- Concurrent processing with semaphores
- Check session tracking (pause/stop/resume)
- Progress reporting
- Per-check statistics

Integrates with Phase 12.3 concurrent batch processing.
"""

import os
import time
import uuid
import random
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from telegram import Update
from telegram.ext import ContextTypes
from response_formatter import ApprovalStatus
from bot.services.gateway_executor import call_gateway_with_timeout, validate_proxy_before_request
from bot.domain.card_utils import lookup_bin_info, detect_security_type
from bot.core.response_templates import format_batch_complete
from config import PROXY

__all__ = [
    'MassCheckService',
    'init_mass_checker',
    'get_mass_checker',
]


@dataclass
class CheckSession:
    """Represents an active mass check session"""
    user_id: int
    check_num: int
    chat_id: int
    session_id: str
    paused: bool = False
    stopped: bool = False
    gateway_name: str = ""
    total_cards: int = 0
    processed: int = 0


@dataclass
class DocumentInfo:
    """Cached document information"""
    path: str
    filename: str
    file_obj: Any
    chat_id: int
    message_id: int
    chat_type: str


class MassCheckService:
    """
    Service for managing mass file-based card checking.
    
    Phase 12.6: Encapsulates all mass check state and logic.
    """
    
    def __init__(
        self,
        file_concurrency: int = 10,
        card_concurrency: int = 10
    ):
        """
        Initialize mass check service.
        
        Args:
            file_concurrency: Max concurrent file checks (default 10)
            card_concurrency: Max concurrent card checks per file (default 10)
        """
        # Concurrency control
        self.file_semaphore = asyncio.Semaphore(file_concurrency)
        self.card_semaphore = asyncio.Semaphore(card_concurrency)
        
        # State tracking
        self.last_documents: Dict[int, DocumentInfo] = {}
        self.uploaded_files: Dict[int, str] = {}
        self.check_status: Dict[str, Any] = {}  # {f"{user_id}_{check_num}": message}
        self.file_stats: Dict[str, Dict] = {}
        self.batch_sessions: Dict[str, CheckSession] = {}
        
        # Check numbering
        self.check_counter = 0
        self._check_lock = asyncio.Lock()
        
        # Registry of active checks per user
        self.active_checks: Dict[int, set] = {}  # {user_id: {check_num1, check_num2}}
        
        print(f"[✓] Mass check service initialized: {file_concurrency} files, {card_concurrency} cards")
    
    async def get_next_check_number(self, user_id: int) -> int:
        """Get next check number for user (thread-safe)"""
        async with self._check_lock:
            self.check_counter += 1
            return self.check_counter
    
    def register_check(self, user_id: int, check_num: int):
        """Register an active check"""
        if user_id not in self.active_checks:
            self.active_checks[user_id] = set()
        self.active_checks[user_id].add(check_num)
    
    def unregister_check(self, user_id: int, check_num: int):
        """Unregister a completed check"""
        if user_id in self.active_checks:
            self.active_checks[user_id].discard(check_num)
            if not self.active_checks[user_id]:
                del self.active_checks[user_id]
    
    def should_stop(self, user_id: int, check_num: int) -> bool:
        """Check if stop was requested for this check"""
        return check_num not in self.active_checks.get(user_id, set())
    
    def store_document(self, user_id: int, doc_info: DocumentInfo):
        """Store document reference for reuse"""
        self.last_documents[user_id] = doc_info
        self.uploaded_files[user_id] = doc_info.path
    
    async def process_mass_file(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        gateway_fn: Callable,
        gateway_name: str
    ):
        """
        Main entry point for mass file processing.
        
        Spawns background task for non-blocking operation.
        """
        user_id = update.message.from_user.id
        chat_id = update.message.chat_id
        
        async def run_mass_check_background():
            """Background task wrapper"""
            async with self.file_semaphore:
                try:
                    await self._process_mass_file_impl(
                        update, context, gateway_fn, gateway_name, user_id, chat_id
                    )
                except Exception as e:
                    print(f"[ERROR] Mass check failed: {e}")
                    try:
                        await update.message.reply_text(f"❌ Mass check failed: {str(e)[:100]}")
                    except:
                        pass
        
        context.application.create_task(run_mass_check_background())
    
    async def _process_mass_file_impl(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        gateway_fn: Callable,
        gateway_name: str,
        user_id: int,
        chat_id: int
    ):
        """Implementation of mass file processing"""
        
        # Get unique check number
        check_num = await self.get_next_check_number(user_id)
        self.register_check(user_id, check_num)
        
        # Determine file path
        file_path, filename = await self._get_file_path(update, user_id, chat_id)
        
        if not file_path or not os.path.exists(file_path):
            self.unregister_check(user_id, check_num)
            await update.message.reply_text(
                "❌ No document to check or file missing. Upload a file and reply with this command."
            )
            return
        
        # Parse cards from file
        cards = await self._parse_cards_from_file(file_path)
        
        if not cards:
            self.unregister_check(user_id, check_num)
            await update.message.reply_text("❌ No valid cards found in file!")
            return
        
        # Send initial status message
        status_msg = await update.message.reply_text(
            f"<b>🚀 Mass Check #{check_num} Started</b>\n\n"
            f"<b>Gateway:</b> {gateway_name}\n"
            f"<b>File:</b> {filename}\n"
            f"<b>Total Cards:</b> {len(cards)}\n"
            f"<b>Stop Command:</b> <code>/stop{check_num}</code>",
            parse_mode='HTML'
        )
        
        # Check proxy health
        proxy_healthy = await asyncio.to_thread(validate_proxy_before_request)
        if not proxy_healthy:
            await status_msg.reply_text(
                "⚠️ Warning: Proxy is not responding. Continuing anyway...",
                parse_mode='HTML'
            )
        
        # Setup check session
        session_id = str(uuid.uuid4())[:8]
        session = CheckSession(
            user_id=user_id,
            check_num=check_num,
            chat_id=chat_id,
            session_id=session_id,
            gateway_name=gateway_name,
            total_cards=len(cards)
        )
        self.batch_sessions[session_id] = session
        self.check_status[f"{user_id}_{check_num}"] = status_msg
        
        # Track stats
        check_key = f"{user_id}_{check_num}"
        self.file_stats[check_key] = {
            "approved": 0,
            "failed": 0,
            "status_msg": status_msg,
            "cards_processed": 0,
            "gateway": gateway_name
        }
        
        # Process cards
        batch_start_time = time.time()
        results = await self._process_cards_batch(
            cards, gateway_fn, gateway_name, session, status_msg, user_id, check_num
        )
        
        # Generate summary
        await self._send_completion_summary(
            results, status_msg, gateway_name, filename, cards, 
            batch_start_time, user_id, check_num
        )
        
        # Cleanup
        self.unregister_check(user_id, check_num)
        if session_id in self.batch_sessions:
            del self.batch_sessions[session_id]
        if check_key in self.file_stats:
            del self.file_stats[check_key]
    
    async def _get_file_path(
        self, update: Update, user_id: int, chat_id: int
    ) -> tuple[Optional[str], Optional[str]]:
        """Get file path from message or cache"""
        file_path = None
        filename = None
        
        # Check if replying to document
        if update.message.reply_to_message and update.message.reply_to_message.document:
            replied_msg = update.message.reply_to_message
            file_obj = replied_msg.document
            filename = file_obj.file_name or f"cards_{file_obj.file_id}.txt"
            
            file = await file_obj.get_file()
            os.makedirs("uploaded_files", exist_ok=True)
            file_path = f"uploaded_files/user_{user_id}_{filename}"
            await file.download_to_drive(file_path)
            
            # Store for reuse
            doc_info = DocumentInfo(
                path=file_path,
                filename=filename,
                file_obj=file_obj,
                chat_id=chat_id,
                message_id=replied_msg.message_id,
                chat_type=update.message.chat.type
            )
            self.store_document(user_id, doc_info)
        
        # Try cached document
        if not file_path and user_id in self.last_documents:
            doc = self.last_documents[user_id]
            file_path = doc.path
            filename = doc.filename
        
        if not file_path and user_id in self.uploaded_files:
            file_path = self.uploaded_files[user_id]
            filename = file_path.split('/')[-1]
        
        return file_path, filename
    
    async def _parse_cards_from_file(self, file_path: str) -> List[Dict[str, str]]:
        """Parse cards from file"""
        cards = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line or '|' not in line:
                        continue
                    
                    parts = line.split('|')
                    if len(parts) == 4:
                        card_num = parts[0].strip()
                        if card_num.isdigit() and len(card_num) >= 13:
                            year_val = parts[2].strip()
                            card_yer = f"20{year_val.zfill(2)}" if len(year_val) <= 2 else year_val[-4:]
                            
                            cards.append({
                                'num': card_num,
                                'mon': parts[1].strip(),
                                'yer': card_yer,
                                'cvc': parts[3].strip()
                            })
        except Exception as e:
            print(f"[ERROR] Failed to parse cards: {e}")
        
        return cards
    
    async def _process_cards_batch(
        self,
        cards: List[Dict],
        gateway_fn: Callable,
        gateway_name: str,
        session: CheckSession,
        status_msg: Any,
        user_id: int,
        check_num: int
    ) -> Dict[str, List]:
        """Process batch of cards with concurrency control"""
        
        approved = []
        failed = []
        cvv_count = 0
        nsf_count = 0
        three_ds_count = 0
        
        async def check_single_card(idx: int, card: Dict) -> Optional[int]:
            """Process single card with semaphore"""
            nonlocal cvv_count, nsf_count, three_ds_count
            
            async with self.card_semaphore:
                # Check stop conditions
                if self.should_stop(user_id, check_num):
                    return None
                
                if self.batch_sessions.get(session.session_id, CheckSession(0, 0, 0, "")).stopped:
                    return None
                
                # Wait while paused
                while self.batch_sessions.get(session.session_id, CheckSession(0, 0, 0, "")).paused:
                    await asyncio.sleep(0.5)
                
                # Execute gateway call
                start_time = time.time()
                res, proxy_ok = await call_gateway_with_timeout(
                    gateway_fn, card['num'], card['mon'], card['yer'], card['cvc'],
                    timeout=22, proxy=PROXY
                )
                elapsed_sec = round(time.time() - start_time, 2)
                
                # Determine status
                status = ApprovalStatus.DECLINED
                if res and "Error" not in res:
                    res_lower = res.lower()
                    if any(kw in res_lower for kw in ["charged", "approved", "success", "accesstoken", "cartid", "ccn", "live"]):
                        status = ApprovalStatus.APPROVED
                    elif "cvv" in res_lower:
                        status = ApprovalStatus.CVV_ISSUE
                        cvv_count += 1
                    elif "insufficient" in res_lower:
                        status = ApprovalStatus.INSUFFICIENT_FUNDS
                        nsf_count += 1
                    elif "3ds" in res_lower or "authentication" in res_lower:
                        three_ds_count += 1
                
                card_full = f"{card['num']}|{card['mon']}|{card['yer']}|{card['cvc']}"
                
                # Store results
                if status in [ApprovalStatus.APPROVED, ApprovalStatus.CVV_ISSUE, ApprovalStatus.INSUFFICIENT_FUNDS]:
                    approved.append(card_full)
                    
                    # Post individual hit
                    bank_name, country = lookup_bin_info(card['num'])
                    try:
                        hit_msg = (
                            f"✅ <b>APPROVED</b> - {gateway_name}\n\n"
                            f"<b>Card:</b> <code>{card_full}</code>\n"
                            f"<b>Bank:</b> {bank_name}\n"
                            f"<b>Country:</b> {country}\n"
                            f"<b>Time:</b> {elapsed_sec}s\n"
                            f"<b>Response:</b> {res[:100]}"
                        )
                        await status_msg.reply_text(hit_msg, parse_mode='HTML')
                    except Exception as e:
                        print(f"[ERROR] Failed to post hit: {e}")
                else:
                    failed.append(card_full)
                
                # Delay between cards
                await asyncio.sleep(random.randint(3, 6))
                return idx
        
        # Process all cards concurrently
        tasks = [check_single_card(idx, card) for idx, card in enumerate(cards, 1)]
        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            "approved": approved,
            "failed": failed,
            "cvv_count": cvv_count,
            "nsf_count": nsf_count,
            "three_ds_count": three_ds_count,
            "stopped": None in task_results
        }
    
    async def _send_completion_summary(
        self,
        results: Dict,
        status_msg: Any,
        gateway_name: str,
        filename: str,
        cards: List,
        batch_start_time: float,
        user_id: int,
        check_num: int
    ):
        """Send completion summary message"""
        
        if results["stopped"]:
            stop_msg = (
                f"⏹️ <b>Mass Check #{check_num} Stopped</b>\n\n"
                f"<b>Status:</b> Cancellation requested by user\n"
                f"<b>Gateway:</b> {gateway_name}\n"
                f"<b>File:</b> {filename}\n\n"
                f"<i>Check stopped gracefully.</i>"
            )
            await status_msg.reply_text(stop_msg, parse_mode='HTML')
        else:
            # Build completion summary
            total_elapsed = round(time.time() - batch_start_time, 2)
            summary = format_batch_complete(
                gateway_name=gateway_name,
                total=len(cards),
                approved=len(results["approved"]),
                declined=len(results["failed"]),
                cvv=results["cvv_count"],
                three_ds=results["three_ds_count"],
                nsf=results["nsf_count"],
                elapsed_sec=total_elapsed,
                was_stopped=False
            )
            
            # Add approved cards list
            if results["approved"]:
                summary += "\n\n<b>💳 Approved Cards:</b>\n"
                for idx, card in enumerate(results["approved"][:15], 1):
                    summary += f"{idx}. <code>{card}</code>\n"
                if len(results["approved"]) > 15:
                    summary += f"<i>... and {len(results['approved']) - 15} more</i>\n"
            
            try:
                await status_msg.edit_text(summary, parse_mode='HTML')
            except Exception as e:
                print(f"[ERROR] Failed to update summary: {e}")


# Global mass checker instance
_mass_checker: Optional[MassCheckService] = None


async def init_mass_checker(file_concurrency: int = 10, card_concurrency: int = 10) -> MassCheckService:
    """
    Initialize global mass check service.
    
    Phase 12.6: Call during bot startup.
    """
    global _mass_checker
    _mass_checker = MassCheckService(
        file_concurrency=file_concurrency,
        card_concurrency=card_concurrency
    )
    return _mass_checker


def get_mass_checker() -> Optional[MassCheckService]:
    """Get global mass check service"""
    return _mass_checker
