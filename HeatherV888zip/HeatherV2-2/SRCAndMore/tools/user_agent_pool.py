"""
User Agent Pool - Centralized browser fingerprinting and header generation
Provides realistic User-Agent rotation, Client Hints, and stealth headers for gateway requests.
"""

import random
import hashlib
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

CHROME_VERSIONS = ["120", "121", "122", "123", "124", "125", "126", "127", "128", "129", "130", "131", "132", "133", "134", "135", "136", "137"]
FIREFOX_VERSIONS = ["120", "121", "122", "123", "124", "125", "126", "127", "128", "129", "130"]
SAFARI_VERSIONS = ["17.0", "17.1", "17.2", "17.3", "17.4", "17.5"]
EDGE_VERSIONS = ["120", "121", "122", "123", "124", "125", "126"]

BROWSER_TEMPLATES = {
    "chrome_windows": {
        "template": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36",
        "versions": CHROME_VERSIONS,
        "platform": "Windows",
        "mobile": False,
        "webgl_vendor": "Google Inc. (NVIDIA)",
        "webgl_renderers": [
            "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0)",
        ],
    },
    "chrome_mac": {
        "template": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36",
        "versions": CHROME_VERSIONS,
        "platform": "macOS",
        "mobile": False,
        "webgl_vendor": "Google Inc. (Apple)",
        "webgl_renderers": [
            "ANGLE (Apple, Apple M1 Pro, OpenGL 4.1)",
            "ANGLE (Apple, Apple M2, OpenGL 4.1)",
            "ANGLE (Apple, Apple M3, OpenGL 4.1)",
            "ANGLE (Apple, Apple M1 Max, OpenGL 4.1)",
        ],
    },
    "chrome_linux": {
        "template": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36",
        "versions": CHROME_VERSIONS,
        "platform": "Linux",
        "mobile": False,
        "webgl_vendor": "Google Inc. (Mesa)",
        "webgl_renderers": [
            "ANGLE (Intel, Mesa Intel(R) UHD Graphics 630)",
            "ANGLE (AMD, AMD Radeon RX 580)",
        ],
    },
    "firefox_windows": {
        "template": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}.0) Gecko/20100101 Firefox/{version}.0",
        "versions": FIREFOX_VERSIONS,
        "platform": "Windows",
        "mobile": False,
        "webgl_vendor": "Mozilla",
        "webgl_renderers": ["NVIDIA GeForce GTX 1660 SUPER", "Intel UHD Graphics 630"],
    },
    "firefox_mac": {
        "template": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:{version}.0) Gecko/20100101 Firefox/{version}.0",
        "versions": FIREFOX_VERSIONS,
        "platform": "macOS",
        "mobile": False,
        "webgl_vendor": "Mozilla",
        "webgl_renderers": ["Apple M1 Pro", "Apple M2"],
    },
    "safari_mac": {
        "template": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version} Safari/605.1.15",
        "versions": SAFARI_VERSIONS,
        "platform": "macOS",
        "mobile": False,
        "webgl_vendor": "Apple Inc.",
        "webgl_renderers": ["Apple M1 Pro", "Apple M2", "Apple M3"],
    },
    "edge_windows": {
        "template": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36 Edg/{version}.0.0.0",
        "versions": EDGE_VERSIONS,
        "platform": "Windows",
        "mobile": False,
        "webgl_vendor": "Google Inc. (NVIDIA)",
        "webgl_renderers": ["ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER)"],
    },
    "chrome_android": {
        "template": "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Mobile Safari/537.36",
        "versions": CHROME_VERSIONS,
        "platform": "Android",
        "mobile": True,
        "webgl_vendor": "Qualcomm",
        "webgl_renderers": ["Adreno (TM) 740", "Adreno (TM) 730"],
    },
    "chrome_iphone": {
        "template": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/{version}.0.0.0 Mobile/15E148 Safari/604.1",
        "versions": CHROME_VERSIONS,
        "platform": "iOS",
        "mobile": True,
        "webgl_vendor": "Apple Inc.",
        "webgl_renderers": ["Apple GPU"],
    },
    "safari_iphone": {
        "template": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version} Mobile/15E148 Safari/604.1",
        "versions": SAFARI_VERSIONS,
        "platform": "iOS",
        "mobile": True,
        "webgl_vendor": "Apple Inc.",
        "webgl_renderers": ["Apple GPU"],
    },
}

SCREEN_RESOLUTIONS = {
    "desktop": [(1920, 1080), (2560, 1440), (1366, 768), (1536, 864), (1440, 900), (3840, 2160)],
    "mobile": [(390, 844), (393, 873), (412, 915), (360, 780), (414, 896)],
}

ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en-US,en;q=0.9,es;q=0.8",
    "en-CA,en;q=0.9,fr;q=0.8",
    "en-AU,en;q=0.9",
    "en-US,en;q=0.9,de;q=0.8",
]

TIMEZONES = [-480, -420, -360, -300, -240, -180, 0, 60, 120, 180, 330, 480, 540]


@dataclass
class BrowserProfile:
    """Complete browser fingerprint profile"""
    user_agent: str
    platform: str
    browser_name: str
    browser_version: str
    is_mobile: bool
    screen_width: int
    screen_height: int
    color_depth: int
    timezone_offset: int
    language: str
    accept_language: str
    webgl_vendor: str
    webgl_renderer: str
    hardware_concurrency: int
    device_memory: int
    canvas_hash: str
    do_not_track: Optional[str]
    
    def get_sec_ch_ua(self) -> str:
        """Generate sec-ch-ua header"""
        if "Chrome" in self.user_agent and "Edg" not in self.user_agent:
            return f'"Chromium";v="{self.browser_version}", "Google Chrome";v="{self.browser_version}", "Not-A.Brand";v="99"'
        elif "Edg" in self.user_agent:
            return f'"Chromium";v="{self.browser_version}", "Microsoft Edge";v="{self.browser_version}", "Not-A.Brand";v="99"'
        elif "Firefox" in self.user_agent:
            return f'"Firefox";v="{self.browser_version}"'
        elif "Safari" in self.user_agent:
            return f'"Safari";v="{self.browser_version.split(".")[0]}"'
        return '"Not-A.Brand";v="99"'
    
    def get_client_hints(self) -> Dict[str, str]:
        """Get Sec-CH-* client hints headers"""
        hints = {
            "sec-ch-ua": self.get_sec_ch_ua(),
            "sec-ch-ua-mobile": "?1" if self.is_mobile else "?0",
            "sec-ch-ua-platform": f'"{self.platform}"',
        }
        
        if "Chrome" in self.user_agent or "Edg" in self.user_agent:
            hints["sec-ch-ua-platform-version"] = f'"{random.randint(10, 14)}.0.0"'
            hints["sec-ch-ua-full-version-list"] = self.get_sec_ch_ua()
            hints["sec-ch-ua-arch"] = '"x86"' if not self.is_mobile else '""'
            hints["sec-ch-ua-bitness"] = '"64"' if not self.is_mobile else '""'
        
        return hints
    
    def get_page_headers(self, referer: Optional[str] = None) -> Dict[str, str]:
        """Generate realistic HTTP headers for page navigation"""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": self.accept_language,
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none" if not referer else "same-origin",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        
        headers.update(self.get_client_hints())
        
        if referer:
            headers["Referer"] = referer
        
        if self.do_not_track:
            headers["DNT"] = self.do_not_track
        
        return headers
    
    def get_api_headers(self, referer: Optional[str] = None, origin: Optional[str] = None) -> Dict[str, str]:
        """Generate headers for API/XHR requests"""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": self.accept_language,
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin" if not origin else "cross-site",
        }
        
        headers.update(self.get_client_hints())
        
        if referer:
            headers["Referer"] = referer
        if origin:
            headers["Origin"] = origin
        
        if self.do_not_track:
            headers["DNT"] = self.do_not_track
        
        return headers
    
    def get_form_headers(self, referer: Optional[str] = None, origin: Optional[str] = None) -> Dict[str, str]:
        """Generate headers for form submissions"""
        headers = self.get_api_headers(referer, origin)
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        headers["Sec-Fetch-Site"] = "same-origin"
        return headers


_profile_cache: Dict[str, BrowserProfile] = {}
_last_rotation: float = 0
_rotation_interval: float = 300.0


def generate_profile(
    session_id: Optional[str] = None,
    prefer_mobile: bool = False,
    browser_type: Optional[str] = None
) -> BrowserProfile:
    """
    Generate a realistic browser fingerprint profile.
    
    Args:
        session_id: Optional ID to cache/retrieve consistent profile for a session
        prefer_mobile: If True, prefer mobile browser profiles
        browser_type: Optional specific browser type (e.g., "chrome_windows", "safari_mac")
    
    Returns:
        BrowserProfile with complete fingerprint data
    """
    global _last_rotation, _profile_cache
    
    current_time = time.time()
    if current_time - _last_rotation > _rotation_interval:
        _profile_cache.clear()
        _last_rotation = current_time
    
    if session_id and session_id in _profile_cache:
        return _profile_cache[session_id]
    
    if browser_type and browser_type in BROWSER_TEMPLATES:
        template_key = browser_type
    elif prefer_mobile:
        template_key = random.choice(["chrome_android", "chrome_iphone", "safari_iphone"])
    else:
        template_key = random.choice([
            "chrome_windows", "chrome_windows", "chrome_windows",
            "chrome_mac", "chrome_mac",
            "firefox_windows", "firefox_mac",
            "safari_mac",
            "edge_windows",
        ])
    
    template = BROWSER_TEMPLATES[template_key]
    version = random.choice(template["versions"])
    user_agent = template["template"].format(version=version)
    
    screen_type = "mobile" if template["mobile"] else "desktop"
    screen = random.choice(SCREEN_RESOLUTIONS[screen_type])
    
    canvas_seed = f"{user_agent}{random.randint(1, 10000)}{time.time()}"
    canvas_hash = hashlib.md5(canvas_seed.encode()).hexdigest()[:16]
    
    profile = BrowserProfile(
        user_agent=user_agent,
        platform=template["platform"],
        browser_name=template_key.split("_")[0].capitalize(),
        browser_version=version,
        is_mobile=template["mobile"],
        screen_width=screen[0],
        screen_height=screen[1],
        color_depth=random.choice([24, 32]),
        timezone_offset=random.choice(TIMEZONES),
        language="en-US",
        accept_language=random.choice(ACCEPT_LANGUAGES),
        webgl_vendor=template["webgl_vendor"],
        webgl_renderer=random.choice(template["webgl_renderers"]),
        hardware_concurrency=random.choice([4, 8, 12, 16]) if not template["mobile"] else random.choice([4, 8]),
        device_memory=random.choice([4, 8, 16]) if not template["mobile"] else random.choice([4, 6, 8]),
        canvas_hash=canvas_hash,
        do_not_track=random.choice([None, "1", None, None, None]),
    )
    
    if session_id:
        _profile_cache[session_id] = profile
    
    return profile


def get_random_user_agent(prefer_mobile: bool = False) -> str:
    """Get a random user agent string"""
    return generate_profile(prefer_mobile=prefer_mobile).user_agent


def get_random_headers(
    referer: Optional[str] = None,
    origin: Optional[str] = None,
    api_mode: bool = False,
    session_id: Optional[str] = None
) -> Dict[str, str]:
    """
    Get random realistic headers for a request.
    
    Args:
        referer: Optional referer URL
        origin: Optional origin URL (for CORS)
        api_mode: If True, use API/XHR headers instead of page headers
        session_id: Optional session ID for consistent profile
    
    Returns:
        Dict of HTTP headers
    """
    profile = generate_profile(session_id=session_id)
    
    if api_mode:
        return profile.get_api_headers(referer=referer, origin=origin)
    else:
        return profile.get_page_headers(referer=referer)


def get_stealth_headers_for_site(site_url: str, api_mode: bool = False) -> Dict[str, str]:
    """
    Get stealth headers optimized for a specific site.
    Uses site URL as session ID for consistent fingerprinting per domain.
    
    Args:
        site_url: The target site URL
        api_mode: If True, use API headers
    
    Returns:
        Dict of HTTP headers
    """
    from urllib.parse import urlparse
    domain = urlparse(site_url).netloc
    
    return get_random_headers(
        referer=site_url,
        origin=site_url if api_mode else None,
        api_mode=api_mode,
        session_id=domain
    )


def rotate_all_profiles() -> None:
    """Force rotation of all cached profiles"""
    global _profile_cache, _last_rotation
    _profile_cache.clear()
    _last_rotation = time.time()


def get_profile_count() -> int:
    """Get number of cached profiles"""
    return len(_profile_cache)


def list_available_browsers() -> List[str]:
    """List all available browser types"""
    return list(BROWSER_TEMPLATES.keys())
