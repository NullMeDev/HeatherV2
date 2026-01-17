"""
Gate Wrapper - Enhances gate responses with VBV lookup
Adds VBV status, bank info, and country to all gate responses
"""
import asyncio
from tools.vbv_api import get_vbv_for_card


async def enhance_gate_response(gate_response: str, cc: str, mes: str, exp: str, cvv: str) -> str:
    """
    Enhance a gate response with VBV lookup info
    
    Args:
        gate_response: Original gate response (STATUS emoji|site|reason|last4)
        cc: Card number
        mes: Month
        exp: Year
        cvv: CVV
    
    Returns:
        Enhanced formatted response with VBV info
    """
    vbv_info = await get_vbv_for_card(cc, mes, exp, cvv)
    
    vbv_status = vbv_info.get("vbv_status", "Unknown")
    bank = vbv_info.get("bank", "Unknown")
    country = vbv_info.get("country", "Unknown")
    country_emoji = vbv_info.get("country_emoji", "")
    card_type = vbv_info.get("card_type", "Unknown")
    scheme = vbv_info.get("scheme", "Unknown")
    
    parts = gate_response.split("|")
    if len(parts) >= 4:
        status = parts[0]
        site = parts[1]
        reason = parts[2]
        last4 = parts[3]
    else:
        status = gate_response.split()[0] if gate_response else "UNKNOWN"
        site = "unknown"
        reason = gate_response
        last4 = cc[-4:] if len(cc) >= 4 else "----"
    
    full_card = f"{cc}|{mes}|{exp}|{cvv}"
    bin_num = cc[:6] if len(cc) >= 6 else "------"
    
    if "APPROVED" in status.upper():
        cvv_stat = "✅ Match"
        ccn_stat = "✅ Live"
    elif "CVV" in status.upper():
        cvv_stat = "❌ Mismatch"
        ccn_stat = "✅ Live"
    elif "CCN" in status.upper() or "NSF" in reason.upper() or "INSUFFICIENT" in reason.upper():
        cvv_stat = "✅ Match"
        ccn_stat = "✅ Live (NSF)"
    elif "3DS" in status.upper() or "3D" in reason.upper():
        cvv_stat = "⚠️ Unknown"
        ccn_stat = "✅ Live (3DS)"
    else:
        cvv_stat = "❌ N/A"
        ccn_stat = "❌ Dead"
    
    return f"""<b>{status}</b>

<code>{full_card}</code>

<b>CVV:</b> {cvv_stat}
<b>CCN:</b> {ccn_stat}
<b>VBV:</b> {vbv_status}

<b>BIN:</b> {bin_num}
<b>Brand:</b> {scheme}
<b>Type:</b> {card_type}
<b>Bank:</b> {bank}
<b>Country:</b> {country_emoji} {country}

<b>Gateway:</b> {site}
<b>Response:</b> {reason}"""


def enhance_gate_response_sync(gate_response: str, cc: str, mes: str, exp: str, cvv: str) -> str:
    """Sync wrapper for enhance_gate_response"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    enhance_gate_response(gate_response, cc, mes, exp, cvv)
                )
                return future.result(timeout=20)
        else:
            return loop.run_until_complete(enhance_gate_response(gate_response, cc, mes, exp, cvv))
    except Exception as e:
        return gate_response
