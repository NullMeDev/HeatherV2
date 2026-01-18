"""
Card utility functions for card input normalization, country flags, and card type detection.
Extracted from transferto.py for better modularity.
"""
import re
import requests

__all__ = [
    'normalize_card_input',
    'COUNTRY_FLAGS',
    'get_country_flag',
    'get_card_type_from_bin',
    'lookup_bin_info',
    'format_bin_info_extended',
    'detect_security_type',
]

# ============================================================================
# COUNTRY FLAGS
# ============================================================================
COUNTRY_FLAGS = {
    "United States": "🇺🇸", "USA": "🇺🇸", "US": "🇺🇸",
    "United Kingdom": "🇬🇧", "UK": "🇬🇧", "GB": "🇬🇧",
    "Canada": "🇨🇦", "CA": "🇨🇦",
    "Australia": "🇦🇺", "AU": "🇦🇺",
    "Germany": "🇩🇪", "DE": "🇩🇪",
    "France": "🇫🇷", "FR": "🇫🇷",
    "Spain": "🇪🇸", "ES": "🇪🇸",
    "Italy": "🇮🇹", "IT": "🇮🇹",
    "Netherlands": "🇳🇱", "NL": "🇳🇱",
    "Brazil": "🇧🇷", "BR": "🇧🇷",
    "Mexico": "🇲🇽", "MX": "🇲🇽",
    "India": "🇮🇳", "IN": "🇮🇳",
    "China": "🇨🇳", "CN": "🇨🇳",
    "Japan": "🇯🇵", "JP": "🇯🇵",
    "South Korea": "🇰🇷", "KR": "🇰🇷",
    "Russia": "🇷🇺", "RU": "🇷🇺",
    "Poland": "🇵🇱", "PL": "🇵🇱",
    "Turkey": "🇹🇷", "TR": "🇹🇷",
    "Nigeria": "🇳🇬", "NG": "🇳🇬",
    "South Africa": "🇿🇦", "ZA": "🇿🇦",
    "Argentina": "🇦🇷", "AR": "🇦🇷",
    "Colombia": "🇨🇴", "CO": "🇨🇴",
    "Chile": "🇨🇱", "CL": "🇨🇱",
    "Indonesia": "🇮🇩", "ID": "🇮🇩",
    "Philippines": "🇵🇭", "PH": "🇵🇭",
    "Thailand": "🇹🇭", "TH": "🇹🇭",
    "Vietnam": "🇻🇳", "VN": "🇻🇳",
    "Malaysia": "🇲🇾", "MY": "🇲🇾",
    "Singapore": "🇸🇬", "SG": "🇸🇬",
    "UAE": "🇦🇪", "United Arab Emirates": "🇦🇪",
    "Saudi Arabia": "🇸🇦", "SA": "🇸🇦",
    "Israel": "🇮🇱", "IL": "🇮🇱",
    "Sweden": "🇸🇪", "SE": "🇸🇪",
    "Norway": "🇳🇴", "NO": "🇳🇴",
    "Denmark": "🇩🇰", "DK": "🇩🇰",
    "Finland": "🇫🇮", "FI": "🇫🇮",
    "Switzerland": "🇨🇭", "CH": "🇨🇭",
    "Austria": "🇦🇹", "AT": "🇦🇹",
    "Belgium": "🇧🇪", "BE": "🇧🇪",
    "Portugal": "🇵🇹", "PT": "🇵🇹",
    "Ireland": "🇮🇪", "IE": "🇮🇪",
    "New Zealand": "🇳🇿", "NZ": "🇳🇿",
    "Greece": "🇬🇷", "GR": "🇬🇷",
}


# ============================================================================
# CARD FORMAT AUTO-DETECTION & NORMALIZATION
# ============================================================================
def normalize_card_input(raw_input: str) -> list:
    """
    Normalize card input from various formats to standard CARD|MM|YY|CVV format.
    Returns list of normalized cards.
    
    Supported formats:
    - 4111111111111111|05|26|123 (standard)
    - 4111111111111111|05|2026|123 (4-digit year)
    - 4111 1111 1111 1111 05/26 123 (spaces and slashes)
    - 4111-1111-1111-1111/05/26/123 (dashes and slashes)
    - 4111111111111111 05 26 123 (space-separated)
    - 4111111111111111,05,26,123 (comma-separated)
    """
    cards = []
    lines = raw_input.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Already in correct format
        if '|' in line:
            parts = line.split('|')
            if len(parts) >= 4:
                card_num = re.sub(r'\D', '', parts[0])
                if len(card_num) >= 13:
                    mon = parts[1].strip().zfill(2)
                    year = parts[2].strip()
                    year = year[-2:] if len(year) == 4 else year.zfill(2)
                    cvv = parts[3].strip()
                    cards.append(f"{card_num}|{mon}|{year}|{cvv}")
            continue
        
        # Remove common separators and try to parse
        # Replace common delimiters with spaces
        normalized = re.sub(r'[-/,;:]', ' ', line)
        # Remove extra spaces
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Try to extract card number (13-19 digits)
        card_match = re.search(r'(\d[\d\s]{12,22}\d)', normalized)
        if card_match:
            card_num = re.sub(r'\D', '', card_match.group(1))
            remaining = normalized[card_match.end():].strip()
            
            # Extract remaining numbers (month, year, cvv)
            numbers = re.findall(r'\d+', remaining)
            
            if len(numbers) >= 3 and len(card_num) >= 13:
                mon = numbers[0].zfill(2)[-2:]
                year = numbers[1][-2:] if len(numbers[1]) >= 2 else numbers[1].zfill(2)
                cvv = numbers[2]
                
                # Validate
                if 1 <= int(mon) <= 12 and len(cvv) >= 3:
                    cards.append(f"{card_num}|{mon}|{year}|{cvv}")
    
    return cards


def get_country_flag(country: str) -> str:
    """Get flag emoji for country"""
    if not country or country == "Unknown":
        return "🌍"
    return COUNTRY_FLAGS.get(country, COUNTRY_FLAGS.get(country.upper(), "🌍"))


def get_card_type_from_bin(card_number: str) -> str:
    """Detect card type from BIN/first digit"""
    if not card_number or len(card_number) < 1:
        return "UNKNOWN"
    first_digit = card_number[0]
    if first_digit == '4':
        return "VISA"
    elif first_digit == '5':
        return "MASTERCARD"
    elif first_digit == '3':
        return "AMEX"
    elif first_digit == '6':
        return "DISCOVER"
    return "UNKNOWN"


def lookup_bin_info(bin_number: str, extended=False) -> tuple:
    """
    Lookup BIN information using drlab API with fallback to antipublic.
    Returns (bank_name, country) tuple, or extended info dict if extended=True.
    Falls back to antipublic API if drlab fails, then to "Unknown".
    
    Extended info includes: bank, country, card_type, card_level, prepaid, brand, flag
    """
    if not bin_number or len(bin_number) < 6:
        if extended:
            return {"bank": "Unknown", "country": "Unknown", "card_type": "Unknown", 
                    "card_level": "", "prepaid": False, "brand": "Unknown", "flag": "🌍"}
        return "Unknown", "Unknown"
    
    bin_6 = bin_number[:6]
    extended_info = {
        "bank": "Unknown",
        "country": "Unknown", 
        "card_type": "Unknown",
        "card_level": "",
        "prepaid": False,
        "brand": "Unknown",
        "flag": "🌍"
    }
    
    try:
        url = f"https://drlabapis.onrender.com/api/ccgenerator?bin={bin_6}&count=1"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, dict):
                extended_info["bank"] = data.get("bank", "Unknown")
                extended_info["country"] = data.get("country", "Unknown")
                extended_info["brand"] = data.get("brand", data.get("scheme", "Unknown"))
                extended_info["card_type"] = data.get("type", "Unknown")
                extended_info["card_level"] = data.get("level", data.get("card_level", ""))
                extended_info["prepaid"] = data.get("prepaid", False)
            elif isinstance(data, list) and len(data) > 0:
                first_item = data[0]
                if isinstance(first_item, dict):
                    extended_info["bank"] = first_item.get("bank", "Unknown")
                    extended_info["country"] = first_item.get("country", "Unknown")
                    extended_info["brand"] = first_item.get("brand", first_item.get("scheme", "Unknown"))
                    extended_info["card_type"] = first_item.get("type", "Unknown")
                    extended_info["card_level"] = first_item.get("level", first_item.get("card_level", ""))
                    extended_info["prepaid"] = first_item.get("prepaid", False)
            
            if extended_info["bank"] != "Unknown" or extended_info["country"] != "Unknown":
                extended_info["flag"] = get_country_flag(extended_info["country"])
                if extended:
                    return extended_info
                return extended_info["bank"], extended_info["country"]
    except (requests.RequestException, ValueError, KeyError) as e:
        pass
    
    try:
        url = f"https://bins.antipublic.cc/bins/{bin_6}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            extended_info["bank"] = data.get("bank", "Unknown")
            extended_info["country"] = data.get("country_name", data.get("country", "Unknown"))
            extended_info["brand"] = data.get("brand", data.get("scheme", "Unknown"))
            extended_info["card_type"] = data.get("type", "CREDIT")
            extended_info["card_level"] = data.get("level", "")
            extended_info["prepaid"] = str(data.get("prepaid", "")).lower() in ["true", "yes", "1"]
            
            if extended_info["bank"] != "Unknown" or extended_info["country"] != "Unknown":
                extended_info["flag"] = get_country_flag(extended_info["country"])
                if extended:
                    return extended_info
                return extended_info["bank"], extended_info["country"]
    except (requests.RequestException, ValueError) as e:
        pass
    
    if extended:
        return extended_info
    return "Unknown", "Unknown"


def format_bin_info_extended(bin_number: str) -> str:
    """Format extended BIN info for display in responses"""
    info = lookup_bin_info(bin_number, extended=True)
    
    parts = []
    if info["flag"] != "🌍":
        parts.append(info["flag"])
    if info["country"] != "Unknown":
        parts.append(info["country"])
    if info["brand"] != "Unknown":
        parts.append(info["brand"].upper())
    if info["card_level"]:
        parts.append(info["card_level"])
    if info["prepaid"]:
        parts.append("PREPAID")
    
    return " | ".join(parts) if parts else "Unknown"


async def lookup_bin_info_cached(bin_number: str, extended=False):
    """
    Phase 12.4: Async BIN lookup with caching.
    
    Uses cache to reduce API calls by ~20-30%.
    Falls back to sync lookup_bin_info if cache not initialized.
    
    Args:
        bin_number: First 6-8 digits of card
        extended: Return extended info dict if True
        
    Returns:
        (bank_name, country) tuple or extended info dict
    """
    try:
        from bot.infrastructure.cache import lookup_bin_cached, cache_bin_info, get_bin_cache
        
        cache = get_bin_cache()
        if cache is None:
            # Cache not initialized, fallback to sync
            return lookup_bin_info(bin_number, extended=extended)
        
        # Try cache first
        cached = await lookup_bin_cached(bin_number)
        if cached is not None:
            if extended:
                # For extended, we need to call API again (cache only stores basic info)
                # This is acceptable since extended=True is rare
                return lookup_bin_info(bin_number, extended=True)
            return cached
        
        # Cache miss - fetch and cache
        result = lookup_bin_info(bin_number, extended=extended)
        
        if extended:
            # Store basic info in cache
            bank = result.get("bank", "Unknown")
            country = result.get("country", "Unknown")
            await cache_bin_info(bin_number, bank, country)
            return result
        else:
            # Store tuple in cache
            bank, country = result
            await cache_bin_info(bin_number, bank, country)
            return bank, country
            
    except Exception as e:
        # Fallback to sync on any error
        return lookup_bin_info(bin_number, extended=extended)


