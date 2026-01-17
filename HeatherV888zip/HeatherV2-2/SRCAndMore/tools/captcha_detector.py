"""
Captcha Detection Module - Identify captcha challenges in responses.

Features:
- Detects multiple captcha types: reCAPTCHA, hCaptcha, Cloudflare, PerimeterX, etc.
- Analyzes both HTML content and response headers
- Provides captcha type identification for specialized handling
- Returns actionable status for retry logic
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CaptchaType(Enum):
    """Types of captcha/bot protection systems."""
    NONE = "none"
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    CLOUDFLARE = "cloudflare"
    CLOUDFLARE_TURNSTILE = "cloudflare_turnstile"
    PERIMETER_X = "perimeter_x"
    DATADOME = "datadome"
    KASADA = "kasada"
    AKAMAI = "akamai"
    IMPERVA = "imperva"
    SHAPE_SECURITY = "shape_security"
    ARKOSE_LABS = "arkose_labs"
    GENERIC_CHALLENGE = "generic_challenge"
    RATE_LIMITED = "rate_limited"


@dataclass
class CaptchaResult:
    """Result of captcha detection analysis."""
    detected: bool
    captcha_type: CaptchaType
    confidence: float
    site_key: Optional[str] = None
    challenge_url: Optional[str] = None
    details: Optional[str] = None
    
    @property
    def is_solvable(self) -> bool:
        """Whether this captcha type can potentially be solved automatically."""
        solvable_types = {
            CaptchaType.RECAPTCHA_V2,
            CaptchaType.RECAPTCHA_V3,
            CaptchaType.HCAPTCHA,
            CaptchaType.CLOUDFLARE_TURNSTILE,
        }
        return self.captcha_type in solvable_types
    
    @property
    def should_retry(self) -> bool:
        """Whether request should be retried (possibly with different fingerprint)."""
        retry_types = {
            CaptchaType.CLOUDFLARE,
            CaptchaType.RATE_LIMITED,
            CaptchaType.GENERIC_CHALLENGE,
        }
        return self.captcha_type in retry_types


class CaptchaDetector:
    """
    Detects captcha and bot protection challenges in HTTP responses.
    
    Usage:
        detector = CaptchaDetector()
        result = detector.analyze(response.text, response.headers, response.status_code)
        
        if result.detected:
            if result.captcha_type == CaptchaType.CLOUDFLARE:
                # Handle Cloudflare challenge
                pass
    """
    
    RECAPTCHA_PATTERNS = [
        (r'class=["\']g-recaptcha["\']', 0.9),
        (r'data-sitekey=["\']([^"\']+)["\']', 0.95),
        (r'google\.com/recaptcha', 0.85),
        (r'grecaptcha\.execute', 0.9),
        (r'recaptcha/api\.js', 0.9),
        (r'recaptcha-token', 0.8),
    ]
    
    HCAPTCHA_PATTERNS = [
        (r'class=["\']h-captcha["\']', 0.95),
        (r'hcaptcha\.com', 0.9),
        (r'data-hcaptcha-widget-id', 0.95),
        (r'hcaptcha-response', 0.85),
    ]
    
    CLOUDFLARE_PATTERNS = [
        (r'Attention Required! \| Cloudflare', 0.95),
        (r'cf-browser-verification', 0.9),
        (r'challenge-platform', 0.85),
        (r'cf_chl_opt', 0.9),
        (r'__cf_bm', 0.7),
        (r'cdn-cgi/challenge-platform', 0.95),
        (r'Just a moment\.\.\.', 0.8),
        (r'Checking your browser', 0.85),
    ]
    
    TURNSTILE_PATTERNS = [
        (r'cf-turnstile', 0.95),
        (r'challenges\.cloudflare\.com/turnstile', 0.95),
        (r'turnstile\.render', 0.9),
    ]
    
    PERIMETER_X_PATTERNS = [
        (r'px-captcha', 0.95),
        (r'_pxhd', 0.8),
        (r'perimeterx\.net', 0.9),
        (r'px-block', 0.85),
    ]
    
    DATADOME_PATTERNS = [
        (r'datadome\.co', 0.95),
        (r'dd_s', 0.7),
        (r'datadome-captcha', 0.95),
    ]
    
    KASADA_PATTERNS = [
        (r'kasada', 0.9),
        (r'cd-s\.kasada', 0.95),
    ]
    
    AKAMAI_PATTERNS = [
        (r'_abck', 0.7),
        (r'akamai', 0.6),
        (r'bm_sz', 0.7),
    ]
    
    IMPERVA_PATTERNS = [
        (r'incapsula', 0.9),
        (r'_incap_ses', 0.85),
        (r'visid_incap', 0.85),
    ]
    
    ARKOSE_PATTERNS = [
        (r'arkoselabs', 0.95),
        (r'funcaptcha', 0.9),
        (r'fc-token', 0.85),
    ]
    
    SHAPE_SECURITY_PATTERNS = [
        (r'shape\.com', 0.9),
        (r'_imp_apg_r_', 0.85),
        (r'f5-bot-defense', 0.9),
        (r'f5avraaasessionid', 0.85),
        (r'TS[a-f0-9]{8}', 0.7),
    ]
    
    RATE_LIMIT_PATTERNS = [
        (r'rate.?limit', 0.9),
        (r'too many requests', 0.95),
        (r'slow down', 0.7),
        (r'try again later', 0.6),
        (r'request limit exceeded', 0.9),
    ]
    
    GENERIC_CHALLENGE_PATTERNS = [
        (r'access.?denied', 0.7),
        (r'blocked', 0.5),
        (r'forbidden', 0.5),
        (r'bot.?detected', 0.9),
        (r'automated.?access', 0.85),
        (r'verify.?you.?are.?human', 0.9),
        (r'prove.?you.?are.?not.?a.?robot', 0.95),
    ]
    
    def __init__(self):
        self._pattern_cache: dict[str, re.Pattern] = {}
    
    def _compile_pattern(self, pattern: str) -> re.Pattern:
        """Compile and cache regex patterns."""
        if pattern not in self._pattern_cache:
            self._pattern_cache[pattern] = re.compile(pattern, re.IGNORECASE)
        return self._pattern_cache[pattern]
    
    def _check_patterns(self, content: str, patterns: list[tuple[str, float]]) -> tuple[bool, float, Optional[str]]:
        """Check content against a list of patterns."""
        max_confidence = 0.0
        matched_pattern = None
        
        for pattern, confidence in patterns:
            regex = self._compile_pattern(pattern)
            match = regex.search(content)
            if match:
                if confidence > max_confidence:
                    max_confidence = confidence
                    matched_pattern = pattern
        
        return max_confidence > 0, max_confidence, matched_pattern
    
    def _extract_site_key(self, content: str, captcha_type: CaptchaType) -> Optional[str]:
        """Extract captcha site key from content."""
        patterns = {
            CaptchaType.RECAPTCHA_V2: r'data-sitekey=["\']([^"\']+)["\']',
            CaptchaType.RECAPTCHA_V3: r'grecaptcha\.execute\(["\']([^"\']+)["\']',
            CaptchaType.HCAPTCHA: r'data-sitekey=["\']([^"\']+)["\']',
            CaptchaType.CLOUDFLARE_TURNSTILE: r'data-sitekey=["\']([^"\']+)["\']',
        }
        
        pattern = patterns.get(captcha_type)
        if pattern:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _check_headers(self, headers: dict) -> tuple[CaptchaType, float]:
        """Check response headers for bot protection indicators."""
        headers_lower = {k.lower(): v for k, v in headers.items()}
        
        if 'cf-ray' in headers_lower and 'cf-cache-status' not in headers_lower:
            return CaptchaType.CLOUDFLARE, 0.6
        
        if 'x-px-' in str(headers_lower):
            return CaptchaType.PERIMETER_X, 0.7
        
        if 'x-datadome' in headers_lower:
            return CaptchaType.DATADOME, 0.8
        
        server = headers_lower.get('server', '').lower()
        if 'cloudflare' in server:
            return CaptchaType.CLOUDFLARE, 0.4
        
        return CaptchaType.NONE, 0.0
    
    def analyze(
        self, 
        content: str, 
        headers: Optional[dict] = None, 
        status_code: int = 200
    ) -> CaptchaResult:
        """
        Analyze response for captcha or bot protection challenges.
        
        Args:
            content: Response body (HTML/text)
            headers: Response headers (optional)
            status_code: HTTP status code
            
        Returns:
            CaptchaResult with detection details
        """
        if status_code == 429:
            return CaptchaResult(
                detected=True,
                captcha_type=CaptchaType.RATE_LIMITED,
                confidence=1.0,
                details="HTTP 429 Too Many Requests"
            )
        
        if status_code == 403:
            pass
        
        if headers:
            header_type, header_conf = self._check_headers(headers)
            if header_conf >= 0.7:
                return CaptchaResult(
                    detected=True,
                    captcha_type=header_type,
                    confidence=header_conf,
                    details="Detected via response headers"
                )
        
        checks = [
            (self.TURNSTILE_PATTERNS, CaptchaType.CLOUDFLARE_TURNSTILE),
            (self.RECAPTCHA_PATTERNS, CaptchaType.RECAPTCHA_V2),
            (self.HCAPTCHA_PATTERNS, CaptchaType.HCAPTCHA),
            (self.CLOUDFLARE_PATTERNS, CaptchaType.CLOUDFLARE),
            (self.PERIMETER_X_PATTERNS, CaptchaType.PERIMETER_X),
            (self.DATADOME_PATTERNS, CaptchaType.DATADOME),
            (self.KASADA_PATTERNS, CaptchaType.KASADA),
            (self.AKAMAI_PATTERNS, CaptchaType.AKAMAI),
            (self.IMPERVA_PATTERNS, CaptchaType.IMPERVA),
            (self.ARKOSE_PATTERNS, CaptchaType.ARKOSE_LABS),
            (self.SHAPE_SECURITY_PATTERNS, CaptchaType.SHAPE_SECURITY),
            (self.RATE_LIMIT_PATTERNS, CaptchaType.RATE_LIMITED),
            (self.GENERIC_CHALLENGE_PATTERNS, CaptchaType.GENERIC_CHALLENGE),
        ]
        
        best_match: Optional[tuple[CaptchaType, float, Optional[str]]] = None
        
        for patterns, captcha_type in checks:
            detected, confidence, pattern = self._check_patterns(content, patterns)
            if detected:
                if best_match is None or confidence > best_match[1]:
                    best_match = (captcha_type, confidence, pattern)
        
        if best_match and best_match[1] >= 0.5:
            captcha_type, confidence, pattern = best_match
            
            if captcha_type == CaptchaType.RECAPTCHA_V2:
                if 'grecaptcha.execute' in content.lower():
                    captcha_type = CaptchaType.RECAPTCHA_V3
            
            site_key = self._extract_site_key(content, captcha_type)
            
            return CaptchaResult(
                detected=True,
                captcha_type=captcha_type,
                confidence=confidence,
                site_key=site_key,
                details=f"Matched pattern: {pattern}"
            )
        
        return CaptchaResult(
            detected=False,
            captcha_type=CaptchaType.NONE,
            confidence=0.0
        )


_global_detector: Optional[CaptchaDetector] = None


def get_captcha_detector() -> CaptchaDetector:
    """Get the global captcha detector instance."""
    global _global_detector
    if _global_detector is None:
        _global_detector = CaptchaDetector()
    return _global_detector


def detect_captcha(
    content: str, 
    headers: Optional[dict] = None, 
    status_code: int = 200
) -> CaptchaResult:
    """Convenience function to detect captcha using global detector."""
    return get_captcha_detector().analyze(content, headers, status_code)


def is_captcha_challenge(
    content: str, 
    headers: Optional[dict] = None, 
    status_code: int = 200
) -> bool:
    """Quick check if response contains a captcha challenge."""
    result = detect_captcha(content, headers, status_code)
    return result.detected
