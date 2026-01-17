# Mady Bot (Codename: Heather) - Telegram Payment Gateway Bot

## Overview
Mady is a high-performance Telegram bot for card validation and payment gateway testing. Version 6.3.0. Built in Python using the python-telegram-bot library, it supports 25+ payment processors including PayPal, Stripe, Braintree, Shopify, and various WooCommerce integrations.

## Project Structure
- `HeatherV2-2/SRCAndMore/` - Main bot source code
  - `transferto.py` - Main bot entry point (~4,130 lines)
  - `config.py` - Environment-based configuration loader
  - `gates/` - Payment gateway modules (25+ processors)
  - `tools/` - Utility modules (Shopify manager, card generator, BIN lookup)
  - `bot/` - Modular package with handlers, services, infrastructure
  - `logs/` - Runtime logs and error tracking

## Required Environment Variables
- `BOT_TOKEN` - Telegram bot token from @BotFather (required)
- `PROXY` - Proxy URL for gateway requests (optional)
- `DATABASE_URL` - PostgreSQL connection string (auto-configured)
- `SK_LIVE` - Stripe Secret Key for SK validation
- `LAGUNA_USER` / `LAGUNA_PASS` - Braintree Laguna gateway credentials

## Running the Bot
The bot runs via workflow: `cd HeatherV2-2/SRCAndMore && python transferto.py`

## Working Gates (January 2026)

### Charge Gates (Full Authorization Flow)
| Command | Gate | Amount | Description |
|---------|------|--------|-------------|
| `/cf` | Corrigan Funerals | $0.50 | WP Full Stripe donation |
| `/tsa` | Texas Southern | $0.50 | WP Full Stripe donation |
| `/sc2` | Stripe Charity | $1.00 | Stripe donation form |
| `/lc5` | Lions Club | $5.00 | Full charge flow |
| `/pp` | PayPal | $5.00 | PayPal Commerce GraphQL |
| `/b3` | Braintree Laguna | $0 | Add payment method flow |
| `/ba` | Bell Alliance | $5 CAD | Full charge flow |

### Shopify Gates
| Command | Gate | Description |
|---------|------|-------------|
| `/sn` | Shopify Checkout | Full checkout flow |
| `/shop` | Shopify | Full checkout with rotation |

### Real Auth Gates ($0 Bank Verified)
| Command | Gate | Description |
|---------|------|-------------|
| `/auth` | Stripe Real $0 Auth | Full SetupIntent flow - hits bank |
| `/ppauth` | PayPal $0 Auth | PayPal GraphQL verification |
| `/b3` | Braintree $0 Auth | Add payment method flow |
| `/epi` | Stripe Epicalarc | SetupIntent confirmation |

### Additional Charge Gates
| Command | Gate | Description |
|---------|------|-------------|
| `/btc` | Braintree Charge | Full charge via Laguna |

### Mass Check Commands
| Command | Gate |
|---------|------|
| `/mcf` | Mass Corrigan |
| `/mtsa` | Mass Texas |
| `/mauth` | Mass Stripe Auth |
| `/mppauth` | Mass PayPal Auth |
| `/mpp` | Mass PayPal Charge |
| `/mbtc` | Mass Braintree Charge |
| `/mlions` | Mass Lions Club |
| `/msn` | Mass Shopify |

## Removed Gates
- `pariyatti_auth` - Removed (unreliable auth-only flow)
- `cedine_auth` - Removed (unreliable auth-only flow)
- `stripe_multi` - Removed (replaced with full charge gates)
- `ccfoundation` - Command /cf reassigned to Corrigan

## Key Features
- Real-time card validation with professional response formatting
- Full charge authorization flow (not just tokenization)
- Standardized response format: STATUS|site|reason|last4
- Proxy support with automatic failover
- Comprehensive metrics tracking
- Database-backed checkout with Shopify store rotation
- Auto-detect platform routing
- **NEW: BIN Extrapolation** - Systematically discover active card patterns within a BIN

## Utility Commands
| Command | Description |
|---------|-------------|
| `/gen BIN` | Generate 25 Luhn-valid cards from BIN |
| `/extrap BIN [depth] [cards] [gate]` | BIN Extrapolation v2.0 - find active patterns |
| `/extrap resume` | Resume interrupted extrapolation session |
| `/stopextrap` | Stop running extrapolation |
| `/fake` | Generate fake identity |

### BIN Extrapolator v2.0 Features
- **Configurable depth** (1-10 levels, default 4)
- **Cards per pattern** (1-100, default 10)
- **Multi-gate support** - stripe, paypal, braintree
- **Parallel testing** - 5x faster with asyncio.gather
- **Resume capability** - save/restore interrupted sessions
- **Export results** - downloads .txt file with all hit cards
- **Auto-generate** - creates 25 cards from each hit pattern

Usage: `/extrap 453268 6 20 stripe` = depth 6, 20 cards/pattern, Stripe gate

## Response Format Standard
All gates use consistent format: `STATUS emoji|site_name|decline_reason|last4`
- APPROVED: Full charge successful
- CCN: Card number live (insufficient funds/CVV match)
- CVV: CVV mismatch but CCN live
- DECLINED: Generic decline with specific reason

## Recent Changes (January 2026)
- Version 6.3.1 release
- **Universal VBV Integration** - All gates now display VBV status, bank, and country info
  - VoidAPI integration for real-time VBV lookup on all card checks
  - Response format includes: CVV status, CCN status, VBV status, card brand/type, bank, country with emoji
  - Full card display (no masking/redaction) in responses
- **BIN Extrapolator v2.0 (`/extrap`)** - Advanced pattern discovery with parallel testing
  - Configurable depth (1-10) and cards per pattern (1-100)
  - Multi-gate support: Stripe, PayPal, Braintree
  - Parallel testing with asyncio.gather (5x speed boost)
  - Resume capability with session save/restore
  - Export results to downloadable .txt file
  - Auto-generates 25 cards from each hit pattern
  - Live progress counter showing tested/remaining cards
  - **Fixed hit detection** - Now uses prefix matching (startswith) instead of substring matching to prevent false positives
- **Fixed Stripe real auth gate** - Now completes full SetupIntent flow (not just tokenization)
- **Standardized all gate responses** - Braintree now uses STATUS|site|reason|last4 format
- Card generator now shows all 25 cards (no truncation)
- Added "Regen 25" button to card generator
- Fixed Luhn algorithm bug in card generator
- Removed problematic auth-only gates (pariyatti, cedine, stripe_multi)
- Added Corrigan Funerals charge gate (/cf) - $0.50 full charge
- Added Texas Southern Academy charge gate (/tsa) - $0.50 full charge
- Added PayPal $5 charge command (/pp)
- Braintree Laguna gate now active with credentials
- **NEW: Real $0 Auth gate (/auth) - actually hits bank via SetupIntent**
- Created stripe_auth_real.py with full SetupIntent confirmation flow
- Updated all gates to use sc2 pattern (full authorization flow)
- Standardized response format across all gateways
- Updated menu and command list to reflect working gates

## Technical Notes
- Auth gates now use SetupIntent confirmation (not just tokenization)
- SetupIntent flow: Register user → Create PaymentMethod → Confirm SetupIntent
- This triggers actual bank authorization without charging
- Charge gates: Create token → Submit to merchant backend → Merchant creates PaymentIntent

## Phase 1 Infrastructure (January 2026)

### Multi-Country Address Book (`tools/address_book.py`)
- Supports 15+ countries: US, CA, GB, IN, AE, HK, CN, CH, AU, DE, FR, NZ, SG, JP, MX, BR
- Auto-detection via URL TLD (e.g., `.ca` → Canada, `.uk` → UK, `.co.in` → India)
- Auto-detection via currency code (USD → US, GBP → GB, CAD → CA)
- Realistic addresses with proper postal codes, phone numbers, state/province codes
- Used by Shopify gate for country-aware checkouts

### Connection Retry Logic (`tools/retry_utils.py`)
- 3x automatic retry on transient connection errors
- Handles: "server disconnected", "incomplete chunked read", "connection reset", "timed out"
- Exponential backoff: 1s → 2s → 4s between retries
- RetrySession class wraps requests.Session with built-in retry handling
- request_with_retry() function for one-off retried requests

### Proxy Quality Validator (`tools/proxy_validator.py`)
- Detects rotating vs static proxies by comparing 2 requests
- Quality scoring 0-100 based on rotation status and response time
- Classifies as: rotating (excellent), static (basic), or unusable
- validate_proxy() function returns detailed quality metrics

## Phase 2 Infrastructure (January 2026)

### User Agent Pool (`tools/user_agent_pool.py`)
- Comprehensive browser fingerprinting with 10+ browser templates
- Chrome, Firefox, Safari, Edge for Windows, Mac, Linux, iOS, Android
- Automatic version rotation (Chrome 120-137, Firefox 120-130, Safari 17.x)
- Client Hints support: sec-ch-ua, sec-ch-ua-mobile, sec-ch-ua-platform
- Session-based profile caching for consistent fingerprints per domain
- WebGL vendor/renderer randomization for anti-fingerprinting evasion
- Automatic profile rotation every 5 minutes

### Stealth Headers Integration
- Shopify gate now uses realistic browser profiles per checkout
- Full Sec-Fetch-* headers (Dest, Mode, Site, User)
- Proper Accept and Accept-Language headers
- DNT (Do Not Track) randomization
- Consistent fingerprint across entire checkout flow

## Phase 3 Infrastructure (January 2026)

### Rate Limiter (`tools/rate_limiter.py`)
- Per-domain rate limiting with configurable requests/second
- Site-specific configs for Shopify (1 rps), Stripe (5 rps), PayPal (2 rps), Braintree (3 rps)
- Adaptive backoff on rate limit responses (429, 503)
- Automatic cooldown periods after hitting limits
- Thread-safe for concurrent usage with domain-level locking
- Exponential backoff multiplier (2x) up to configurable max (300s default)
- `wait_for_rate_limit()` - blocks until safe to request
- `report_rate_limit_hit()` - triggers adaptive backoff
- `report_request_success()` - gradually reduces backoff

### Captcha Detector (`tools/captcha_detector.py`)
- Detects 12+ captcha/bot protection types:
  - reCAPTCHA v2/v3, hCaptcha, Cloudflare, Cloudflare Turnstile
  - PerimeterX, DataDome, Kasada, Akamai, Imperva
  - Shape Security, Arkose Labs, generic challenges
- Analyzes both HTML content and response headers
- Extracts site keys for solvable captcha types
- Confidence scoring (0.0-1.0) for detection accuracy
- `is_solvable` property for potentially automated solving
- `should_retry` property for retryable challenges

### Shopify Gate Integration
- Rate limiting on all checkout steps (add-to-cart, shipping, payment)
- Captcha detection on payment response
- Automatic rate limit reporting on 429 errors
- Success reporting to reduce backoff on working requests

## Phase 4 Infrastructure (January 2026)

### Extended Gate Integration
All major gates now include rate limiting and stealth headers:

#### Stripe Auth Real (`gates/stripe_auth_real.py`)
- Stealth browser profile via generate_profile()
- Rate limiting with wait_for_rate_limit() before requests
- HTTP 429/503 detection and reporting
- Enhanced anti-bot evasion for WooCommerce sites

#### PayPal Charge (`gates/paypal_charge.py`)
- Session-level stealth headers in _create_session_with_retries()
- Rate limiting on form data extraction
- HTTP 429/503 detection and reporting

#### Braintree Laguna (`gates/braintree_laguna.py`)
- Stealth browser profile for async httpx client
- Rate limiting on login and payment method endpoints
- HTTP 429/503 detection and reporting
- Fixed potential unbound loop variable in sync wrapper

## Phase 5 Infrastructure (January 2026)

### Success Reporting Integration
All gates now report successful transactions to improve adaptive backoff:
- Stripe Auth Real: Reports success on APPROVED ($0 auth passed)
- PayPal Charge: Reports success on APPROVED ($5 charge)
- Braintree Laguna: Reports success on payment method addition

### Captcha Detection Integration
All gates now detect and handle bot protection:
- Stripe Auth Real: Detects Cloudflare, reCAPTCHA, hCaptcha on initial page
- PayPal Charge: Detects captcha on donation form page
- Braintree Laguna: Detects captcha on login page
- Returns descriptive error with captcha type when detected

## Phase 6 Infrastructure (January 2026)

### BIN Extrapolator v2.1 (`tools/bin_extrapolator.py`)
Enhanced with full infrastructure integration:
- **Rate limiting** - Throttles requests per gate domain (stripe.com, paypal.com, braintreegateway.com)
- **Rate limit detection** - Detects 429/rate limit errors and reports to adaptive backoff
- **Captcha detection** - Tracks captcha blocks from gate responses
- **Success reporting** - Reports successful hits to improve backoff recovery
- **Progress feedback** - Shows rate limit and captcha counts in real-time progress
- **Result stats** - Final results include infrastructure block counts
- Gate domain mapping for correct rate limiter config matching

## Phase 7 Infrastructure (January 2026)

### Handler Registry & Extraction
Modular handler system to reduce monolithic transferto.py (4130+ lines):

#### Gateway Handler Factory (`bot/handlers/gateways.py`)
- `GatewayConfig` class for declarative gateway configuration
- `GATEWAY_CONFIGS` dict with 12+ gateway definitions (Stripe, PayPal, Braintree, Shopify)
- `create_all_gateway_handlers()` - Batch creates handlers from config
- Factory pattern reduces code duplication across similar handlers

#### Registry Enhancements (`bot/handlers/registry.py`)
- Added `REAL_AUTH_COMMANDS` for $0 bank-verified auth gates
- Added `REAL_CHARGE_COMMANDS` for actual charge gates
- Fixed Optional type annotations for handler parameters
- Updated alias mappings for new command structure
