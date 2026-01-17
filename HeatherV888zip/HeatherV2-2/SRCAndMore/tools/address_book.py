"""
Multi-Country Address Book for Checkout Operations
Supports 10+ countries with auto-detection based on URL TLD and currency.
"""

from urllib.parse import urlparse
from typing import Optional
import random
import string

CURRENCY_TO_COUNTRY = {
    "USD": "US",
    "CAD": "CA",
    "INR": "IN",
    "AED": "AE",
    "HKD": "HK",
    "GBP": "GB",
    "CHF": "CH",
    "AUD": "AU",
    "EUR": "DE",
    "NZD": "NZ",
    "SGD": "SG",
    "JPY": "JP",
    "CNY": "CN",
    "MXN": "MX",
    "BRL": "BR",
}

ADDRESS_BOOK = {
    "US": {
        "address1": "123 Main Street",
        "address2": "",
        "city": "New York",
        "postalCode": "10001",
        "zoneCode": "NY",
        "countryCode": "US",
        "country": "United States",
        "phone": "2125551234",
        "currencyCode": "USD",
        "first_name": "John",
        "last_name": "Smith",
    },
    "CA": {
        "address1": "88 Queen Street West",
        "address2": "",
        "city": "Toronto",
        "postalCode": "M5H 2M5",
        "zoneCode": "ON",
        "countryCode": "CA",
        "country": "Canada",
        "phone": "4165550198",
        "currencyCode": "CAD",
        "first_name": "Michael",
        "last_name": "Brown",
    },
    "GB": {
        "address1": "221B Baker Street",
        "address2": "",
        "city": "London",
        "postalCode": "NW1 6XE",
        "zoneCode": "LND",
        "countryCode": "GB",
        "country": "United Kingdom",
        "phone": "2079460123",
        "currencyCode": "GBP",
        "first_name": "James",
        "last_name": "Wilson",
    },
    "IN": {
        "address1": "221B MG Road",
        "address2": "",
        "city": "Mumbai",
        "postalCode": "400001",
        "zoneCode": "MH",
        "countryCode": "IN",
        "country": "India",
        "phone": "9876543210",
        "currencyCode": "INR",
        "first_name": "Raj",
        "last_name": "Sharma",
    },
    "AE": {
        "address1": "Burj Tower, Sheikh Zayed Road",
        "address2": "",
        "city": "Dubai",
        "postalCode": "00000",
        "zoneCode": "DU",
        "countryCode": "AE",
        "country": "United Arab Emirates",
        "phone": "501234567",
        "currencyCode": "AED",
        "first_name": "Ahmed",
        "last_name": "Al Maktoum",
    },
    "HK": {
        "address1": "88 Nathan Road",
        "address2": "",
        "city": "Kowloon",
        "postalCode": "000000",
        "zoneCode": "KL",
        "countryCode": "HK",
        "country": "Hong Kong",
        "phone": "55555555",
        "currencyCode": "HKD",
        "first_name": "Wei",
        "last_name": "Chan",
    },
    "CN": {
        "address1": "8 Zhongguancun Street",
        "address2": "",
        "city": "Beijing",
        "postalCode": "100080",
        "zoneCode": "BJ",
        "countryCode": "CN",
        "country": "China",
        "phone": "1062512345",
        "currencyCode": "CNY",
        "first_name": "Li",
        "last_name": "Wang",
    },
    "CH": {
        "address1": "Gotthardstrasse 17",
        "address2": "",
        "city": "Zurich",
        "postalCode": "8002",
        "zoneCode": "ZH",
        "countryCode": "CH",
        "country": "Switzerland",
        "phone": "445512345",
        "currencyCode": "CHF",
        "first_name": "Hans",
        "last_name": "Muller",
    },
    "AU": {
        "address1": "1 Martin Place",
        "address2": "",
        "city": "Sydney",
        "postalCode": "2000",
        "zoneCode": "NSW",
        "countryCode": "AU",
        "country": "Australia",
        "phone": "291234567",
        "currencyCode": "AUD",
        "first_name": "Jack",
        "last_name": "Thompson",
    },
    "DE": {
        "address1": "Friedrichstrasse 123",
        "address2": "",
        "city": "Berlin",
        "postalCode": "10117",
        "zoneCode": "BE",
        "countryCode": "DE",
        "country": "Germany",
        "phone": "301234567",
        "currencyCode": "EUR",
        "first_name": "Max",
        "last_name": "Schmidt",
    },
    "FR": {
        "address1": "15 Rue de Rivoli",
        "address2": "",
        "city": "Paris",
        "postalCode": "75001",
        "zoneCode": "IDF",
        "countryCode": "FR",
        "country": "France",
        "phone": "142345678",
        "currencyCode": "EUR",
        "first_name": "Pierre",
        "last_name": "Dubois",
    },
    "NZ": {
        "address1": "123 Queen Street",
        "address2": "",
        "city": "Auckland",
        "postalCode": "1010",
        "zoneCode": "AUK",
        "countryCode": "NZ",
        "country": "New Zealand",
        "phone": "93001234",
        "currencyCode": "NZD",
        "first_name": "Tom",
        "last_name": "Williams",
    },
    "SG": {
        "address1": "1 Raffles Place",
        "address2": "",
        "city": "Singapore",
        "postalCode": "048616",
        "zoneCode": "SG",
        "countryCode": "SG",
        "country": "Singapore",
        "phone": "61234567",
        "currencyCode": "SGD",
        "first_name": "David",
        "last_name": "Tan",
    },
    "JP": {
        "address1": "1-1-1 Shibuya",
        "address2": "",
        "city": "Tokyo",
        "postalCode": "150-0002",
        "zoneCode": "TK",
        "countryCode": "JP",
        "country": "Japan",
        "phone": "312345678",
        "currencyCode": "JPY",
        "first_name": "Yuki",
        "last_name": "Tanaka",
    },
    "MX": {
        "address1": "Av. Paseo de la Reforma 505",
        "address2": "",
        "city": "Mexico City",
        "postalCode": "06500",
        "zoneCode": "CMX",
        "countryCode": "MX",
        "country": "Mexico",
        "phone": "5512345678",
        "currencyCode": "MXN",
        "first_name": "Carlos",
        "last_name": "Garcia",
    },
    "BR": {
        "address1": "Av. Paulista 1000",
        "address2": "",
        "city": "Sao Paulo",
        "postalCode": "01310-100",
        "zoneCode": "SP",
        "countryCode": "BR",
        "country": "Brazil",
        "phone": "11987654321",
        "currencyCode": "BRL",
        "first_name": "Pedro",
        "last_name": "Silva",
    },
}

TLD_TO_COUNTRY = {
    "com": "US",
    "us": "US",
    "ca": "CA",
    "uk": "GB",
    "co.uk": "GB",
    "in": "IN",
    "ae": "AE",
    "hk": "HK",
    "cn": "CN",
    "ch": "CH",
    "au": "AU",
    "com.au": "AU",
    "de": "DE",
    "fr": "FR",
    "nz": "NZ",
    "sg": "SG",
    "jp": "JP",
    "mx": "MX",
    "br": "BR",
    "com.br": "BR",
}


def get_country_from_url(url: str) -> str:
    """
    Extract country code from URL TLD.
    Returns 'US' as default if not detected.
    """
    try:
        domain = urlparse(url).netloc.lower()
        parts = domain.split(".")
        
        if len(parts) >= 2:
            tld = parts[-1]
            compound_tld = ".".join(parts[-2:])
            
            if compound_tld in TLD_TO_COUNTRY:
                return TLD_TO_COUNTRY[compound_tld]
            if tld in TLD_TO_COUNTRY:
                return TLD_TO_COUNTRY[tld]
    except Exception:
        pass
    
    return "US"


def get_country_from_currency(currency_code: str) -> str:
    """
    Get country code from currency.
    """
    if not currency_code:
        return "US"
    return CURRENCY_TO_COUNTRY.get(currency_code.upper(), "US")


def pick_address(url: Optional[str] = None, currency_code: Optional[str] = None, country_code: Optional[str] = None) -> dict:
    """
    Pick the best address for a checkout based on URL, currency, or explicit country.
    
    Priority:
    1. Explicit country_code parameter
    2. Match currency to country
    3. Match URL TLD to country
    4. Default to US
    
    Args:
        url: Store URL (optional)
        currency_code: Currency code like USD, GBP (optional)
        country_code: Explicit country code like US, GB (optional)
    
    Returns:
        Address dict with all required fields
    """
    detected_country = "US"
    
    if country_code and country_code.upper() in ADDRESS_BOOK:
        detected_country = country_code.upper()
    elif currency_code:
        currency_country = get_country_from_currency(currency_code)
        if currency_country in ADDRESS_BOOK:
            detected_country = currency_country
    elif url:
        url_country = get_country_from_url(url)
        if url_country in ADDRESS_BOOK:
            detected_country = url_country
    
    address = ADDRESS_BOOK.get(detected_country, ADDRESS_BOOK["US"]).copy()
    address["detected_country"] = detected_country
    
    return address


def get_random_email(domain: str = "gmail.com") -> str:
    """
    Generate a random email address.
    """
    rand_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"user{rand_suffix}@{domain}"


def get_buyer_info(url: Optional[str] = None, currency_code: Optional[str] = None, country_code: Optional[str] = None) -> dict:
    """
    Get complete buyer info for checkout including address and personal details.
    
    Returns a dict compatible with Shopify checkout forms.
    """
    addr = pick_address(url, currency_code, country_code)
    
    return {
        "email": get_random_email(),
        "first_name": addr["first_name"],
        "last_name": addr["last_name"],
        "address1": addr["address1"],
        "address2": addr.get("address2", ""),
        "city": addr["city"],
        "province": addr["zoneCode"],
        "country": addr["country"],
        "country_code": addr["countryCode"],
        "zip": addr["postalCode"],
        "phone": addr["phone"],
        "currency": addr["currencyCode"],
    }


def get_supported_countries() -> list:
    """
    Get list of supported country codes.
    """
    return list(ADDRESS_BOOK.keys())
