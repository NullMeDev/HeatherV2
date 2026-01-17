import aiohttp
import asyncio
import os

VBV_API_KEY = os.getenv("VBV_API_KEY", "VDX-SHA2X-NZ0RS-O7HAM")
VBV_API_URL = "https://api.voidapi.xyz/v2/vbv"

async def lookup_vbv_async(card: str) -> dict:
    """
    Lookup VBV/3DS status for a card using VoidAPI
    
    Args:
        card: Card string in format "4242424242424242|12|2030|123"
    
    Returns:
        dict with VBV data or error
    """
    url = f"{VBV_API_URL}?key={VBV_API_KEY}&card={card}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                data = await resp.json()
                if data.get("success"):
                    return {"success": True, "data": data.get("data", {})}
                else:
                    return {"success": False, "error": data.get("error", "Unknown error")}
    except asyncio.TimeoutError:
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def parse_vbv_status(status: str) -> str:
    """
    Convert VoidAPI status to human-readable VBV status
    """
    status_map = {
        "authenticate_successful": "3DS Required (Enrolled)",
        "authenticate_frictionless_failed": "3DS Failed",
        "authenticate_failed": "3DS Failed",
        "authenticate_attempted": "3DS Attempted",
        "not_enrolled": "No 3DS (2D)",
        "not_supported": "No 3DS (2D)",
        "unavailable": "VBV Unknown",
        "error": "VBV Error"
    }
    return status_map.get(status, status.replace("_", " ").title())


def format_vbv_info(data: dict) -> dict:
    """
    Format VBV API response into structured info
    
    Returns dict with:
        - vbv_status: Human readable VBV status
        - bank: Bank name
        - country: Country code
        - country_emoji: Country flag emoji
        - card_type: CREDIT/DEBIT
        - card_level: CLASSIC/GOLD/PLATINUM etc
        - scheme: Visa/Mastercard etc
    """
    if not data:
        return {
            "vbv_status": "Unknown",
            "bank": "Unknown",
            "country": "Unknown",
            "country_emoji": "",
            "card_type": "Unknown",
            "card_level": "Unknown",
            "scheme": "Unknown"
        }
    
    raw_status = data.get("status", "unavailable")
    
    return {
        "vbv_status": parse_vbv_status(raw_status),
        "bank": data.get("bank", "Unknown"),
        "country": data.get("country", "Unknown"),
        "country_emoji": data.get("emoji", ""),
        "card_type": data.get("type", "Unknown"),
        "card_level": data.get("level", "Unknown"),
        "scheme": data.get("scheme", "Unknown")
    }


async def get_vbv_for_card(cc: str, mes: str, exp: str, cvv: str) -> dict:
    """
    Get VBV info for a card (convenience function)
    
    Args:
        cc: Card number
        mes: Month
        exp: Year (2 or 4 digit)
        cvv: CVV
    
    Returns:
        Formatted VBV info dict
    """
    year = f"20{exp}" if len(exp) == 2 else exp
    card_string = f"{cc}|{mes}|{year}|{cvv}"
    
    result = await lookup_vbv_async(card_string)
    
    if result.get("success"):
        return format_vbv_info(result.get("data", {}))
    else:
        return {
            "vbv_status": "Lookup Failed",
            "bank": "Unknown",
            "country": "Unknown", 
            "country_emoji": "",
            "card_type": "Unknown",
            "card_level": "Unknown",
            "scheme": "Unknown"
        }
