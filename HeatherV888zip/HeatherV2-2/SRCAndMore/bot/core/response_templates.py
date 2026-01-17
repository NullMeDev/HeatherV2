"""
Unified Professional Response Formatting Module
Provides consistent, professional formatting for all bot responses.
"""
from typing import Optional, Dict

COUNTRY_FLAGS = {
    "US": "🇺🇸", "USA": "🇺🇸", "CA": "🇨🇦", "GB": "🇬🇧", "UK": "🇬🇧",
    "DE": "🇩🇪", "FR": "🇫🇷", "IT": "🇮🇹", "ES": "🇪🇸", "AU": "🇦🇺",
    "JP": "🇯🇵", "CN": "🇨🇳", "IN": "🇮🇳", "BR": "🇧🇷", "MX": "🇲🇽",
    "RU": "🇷🇺", "KR": "🇰🇷", "NL": "🇳🇱", "SE": "🇸🇪", "CH": "🇨🇭",
    "NO": "🇳🇴", "DK": "🇩🇰", "FI": "🇫🇮", "PL": "🇵🇱", "BE": "🇧🇪",
    "AT": "🇦🇹", "IE": "🇮🇪", "PT": "🇵🇹", "NZ": "🇳🇿", "SG": "🇸🇬",
    "HK": "🇭🇰", "AE": "🇦🇪", "SA": "🇸🇦", "ZA": "🇿🇦", "IL": "🇮🇱",
    "TR": "🇹🇷", "TH": "🇹🇭", "MY": "🇲🇾", "PH": "🇵🇭", "ID": "🇮🇩",
    "VN": "🇻🇳", "AR": "🇦🇷", "CL": "🇨🇱", "CO": "🇨🇴", "PE": "🇵🇪",
}


def get_card_brand(card_number: str) -> str:
    """Returns card brand based on BIN prefix."""
    if not card_number or len(card_number) < 1:
        return "UNKNOWN"
    
    card = card_number.replace(" ", "").replace("-", "")
    
    if card.startswith("4"):
        return "VISA"
    elif card.startswith(("51", "52", "53", "54", "55")):
        return "MASTERCARD"
    elif card.startswith(("2221", "2222", "2223", "2224", "2225", "2226", "2227", "2228", "2229",
                          "223", "224", "225", "226", "227", "228", "229", "23", "24", "25", "26",
                          "270", "271", "2720")):
        return "MASTERCARD"
    elif card.startswith(("34", "37")):
        return "AMEX"
    elif card.startswith(("6011", "644", "645", "646", "647", "648", "649", "65")):
        return "DISCOVER"
    elif card.startswith("36"):
        return "DINERS"
    elif card.startswith(("3528", "3529", "353", "354", "355", "356", "357", "358")):
        return "JCB"
    elif card[0] == "5":
        return "MASTERCARD"
    elif card[0] == "6":
        return "DISCOVER"
    else:
        return "UNKNOWN"


def get_country_flag(country_code: str) -> str:
    """Returns emoji flag for country code."""
    if not country_code:
        return "🌍"
    return COUNTRY_FLAGS.get(country_code.upper(), "🌍")


def mask_card(card_number: str) -> str:
    """Returns masked card format: 411111...1111"""
    if not card_number:
        return "••••...••••"
    
    card = card_number.replace(" ", "").replace("-", "")
    if len(card) < 10:
        return card
    
    return f"{card[:6]}...{card[-4:]}"


def format_single_card_result(
    card_input: str,
    status: str,
    card_brand: str = "",
    card_type: str = "CREDIT",
    bank_name: str = "Unknown",
    country: str = "US",
    cvv_match: bool = True,
    ccn_live: bool = True,
    gateway: str = "Stripe Auth",
    amount: str = "$0.50 USD",
    elapsed_sec: float = 0.0,
    proxy_alive: bool = True,
    vbv_status: str = "Unknown",
    country_emoji: str = ""
) -> str:
    """
    Format single card check result - instant popup format.
    Clean, compact format with all key info.
    """
    card_parts = card_input.split("|")
    card_number = card_parts[0] if card_parts else ""
    
    if not card_brand:
        card_brand = get_card_brand(card_number)
    
    flag = get_country_flag(country)
    
    status_upper = status.upper()
    if status_upper in ("APPROVED", "LIVE", "SUCCESS", "HIT"):
        status_emoji = "✅"
        status_text = "APPROVED"
    elif status_upper in ("CVV", "CVV_MISMATCH", "CVV_ISSUE"):
        status_emoji = "⚠️"
        status_text = "CVV MISMATCH"
    elif status_upper in ("3DS", "FRAUD", "FRAUD_CHECK"):
        status_emoji = "🔐"
        status_text = "3DS REQUIRED"
    elif status_upper in ("NSF", "INSUFFICIENT", "INSUFFICIENT_FUNDS"):
        status_emoji = "💰"
        status_text = "INSUFFICIENT FUNDS"
    elif status_upper in ("EXPIRED",):
        status_emoji = "📅"
        status_text = "EXPIRED"
    else:
        status_emoji = "❌"
        status_text = "DECLINED"
    
    cvv_icon = "✓" if cvv_match else "✗"
    ccn_icon = "✓" if ccn_live else "✗"
    
    flag_display = country_emoji if country_emoji else flag
    
    response = f"""{status_emoji} <b>{status_text}</b>

<code>{card_input}</code>

<b>CVV:</b> {cvv_icon} {"Match" if cvv_match else "Mismatch"}
<b>CCN:</b> {ccn_icon} {"Live" if ccn_live else "Dead"}
<b>VBV:</b> {vbv_status}

💳 {card_brand} {card_type}
🏦 {bank_name}
{flag_display} {country}

⚡ {gateway} | {amount}"""
    
    return response


def format_batch_dashboard(
    gateway_name: str,
    current: int,
    total: int,
    approved: int = 0,
    declined: int = 0,
    cvv: int = 0,
    three_ds: int = 0,
    nsf: int = 0,
    last_card: str = "",
    last_status: str = "Waiting",
    is_paused: bool = False
) -> str:
    """
    Format batch progress dashboard with real-time stats.
    
    Args:
        gateway_name: Gateway being used
        current: Current card number
        total: Total cards
        approved: Approved count
        declined: Declined count
        cvv: CVV mismatch count
        three_ds: 3DS required count
        nsf: Insufficient funds count
        last_card: Last card checked
        last_status: Status of last card
        is_paused: Whether batch is paused
    """
    percent = (current / total * 100) if total > 0 else 0
    bar_len = 14
    filled = int(bar_len * current / total) if total > 0 else 0
    bar = "▓" * filled + "░" * (bar_len - filled)
    
    status_icon = "⏸" if is_paused else "⚡"
    status_text = "Paused" if is_paused else "Processing"
    
    masked = mask_card(last_card) if last_card else "..."
    
    response = f"""{status_icon} <b>{gateway_name.upper()}</b> • {status_text}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[{bar}] {current}/{total} ({percent:.0f}%)

✅ {approved}  │  ❌ {declined}  │  CVV {cvv}  │  3DS {three_ds}  │  NSF {nsf}

Last: {masked} → {last_status}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    return response


def format_batch_hit(
    card_input: str,
    card_brand: str = "",
    card_type: str = "CREDIT",
    country: str = "US",
    bank_name: str = "Unknown",
    gateway: str = "Stripe Auth",
    amount: str = "$1.00 USD",
    elapsed_sec: float = 0.0,
    current: int = 0,
    total: int = 0
) -> str:
    """
    Format batch hit notification.
    
    Args:
        card_input: Card in format CARD|MM|YY|CVV
        card_brand: VISA, MASTERCARD, etc.
        card_type: CREDIT, DEBIT, PREPAID
        country: Country code
        bank_name: Issuing bank
        gateway: Gateway name
        amount: Amount charged
        elapsed_sec: Time taken
        current: Current position in batch
        total: Total cards in batch
    """
    card_parts = card_input.split("|")
    card_number = card_parts[0] if card_parts else ""
    
    if not card_brand:
        card_brand = get_card_brand(card_number)
    
    flag = get_country_flag(country)
    percent = (current / total * 100) if total > 0 else 0
    
    response = f"""✅ <b>HIT FOUND</b>

<code>{card_input}</code>
{card_brand} {card_type} • {country} {flag} • {bank_name}

Gateway: {gateway}
Amount: {amount}
Time: {elapsed_sec:.2f}s

[{current}/{total}] {percent:.0f}%"""
    
    return response


def format_batch_complete(
    gateway_name: str,
    total: int,
    approved: int = 0,
    declined: int = 0,
    cvv: int = 0,
    three_ds: int = 0,
    nsf: int = 0,
    elapsed_sec: float = 0.0,
    was_stopped: bool = False
) -> str:
    """
    Format batch complete summary.
    
    Args:
        gateway_name: Gateway used
        total: Total cards checked
        approved: Hits count
        declined: Dead cards count
        cvv: CVV mismatch count
        three_ds: 3DS required count
        nsf: Insufficient funds count
        elapsed_sec: Total time
        was_stopped: Whether batch was manually stopped
    """
    hit_rate = (approved / total * 100) if total > 0 else 0
    avg_time = elapsed_sec / total if total > 0 else 0
    
    status = "⏹ BATCH STOPPED" if was_stopped else "✅ BATCH COMPLETE"
    
    response = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{status}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Gateway: {gateway_name}
Cards: {total}

📊 Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Hits: {approved} ({hit_rate:.0f}%)
❌ Dead: {declined}
CVV: {cvv} │ 3DS: {three_ds} │ NSF: {nsf}

⏱ Time: {elapsed_sec:.1f}s ({avg_time:.1f}s/card)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    return response


def format_error(error_type: str, message: str, gateway: str = "") -> str:
    """Format error message."""
    gateway_line = f"\nGateway: {gateway}" if gateway else ""
    return f"""❌ <b>ERROR: {error_type}</b>{gateway_line}

{message}"""


def format_start_batch(gateway_name: str, total: int, proxy_alive: bool = True) -> str:
    """Format batch start message."""
    proxy_icon = "🟢" if proxy_alive else "🔴"
    return f"""🚀 <b>Starting Batch Check</b>

Gateway: {gateway_name}
Total Cards: {total}
Proxy: {proxy_icon}

Processing..."""


def format_progress(current: int, total: int) -> str:
    """
    Format simple progress update for mass checks.
    Returns: "[▓▓▓░░░] 15/25 (60%)"
    """
    percent = (current / total * 100) if total > 0 else 0
    bar_len = 14
    filled = int(bar_len * current / total) if total > 0 else 0
    bar = "▓" * filled + "░" * (bar_len - filled)
    return f"<b>Progress:</b> [{bar}] {current}/{total} ({percent:.0f}%)"
