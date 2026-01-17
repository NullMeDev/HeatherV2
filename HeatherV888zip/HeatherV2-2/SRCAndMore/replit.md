# Mady Bot (Codename: Heather) - Telegram Payment Gateway Bot

## Overview
Mady is a high-performance Telegram bot for card validation and payment gateway testing. Version 6.2.1. Built in Python, it supports 70 payment gateway modules including PayPal, Stripe, Braintree, Shopify, and WooCommerce integrations.

## Project Structure
```
/
├── transferto.py          # Main bot entry point (~7,300 lines)
├── config.py              # Configuration loader (reads from environment)
├── response_formatter*.py # Response formatting utilities
├── metrics_collector.py   # Bot analytics and metrics
├── dashboard.py           # Analytics dashboard
├── gates/                 # Payment gateway modules (70 files)
│   ├── stripe*.py        # Stripe gateway variants
│   ├── paypal*.py        # PayPal integration
│   ├── braintree*.py     # Braintree gateways
│   ├── shopify*.py       # Shopify checkout
│   ├── woostripe*.py     # WooCommerce Stripe
│   └── ...               # Other gateways
├── tools/                 # Utility tools
│   ├── shopify_db.py     # Shopify database management
│   ├── shopify_scraper.py # Store product scraper
│   ├── stripe_db.py      # Stripe key database
│   ├── stripe_scraper.py # Stripe key finder
│   ├── niche_scraper.py  # CLI tool for finding Stripe/WooCommerce sites
│   └── card_generator.py # Card generation tools
└── logs/                  # Log files directory
```

## Required Secrets
- `BOT_TOKEN` - Telegram bot token from @BotFather (required)
- `PROXY_HTTP` - HTTP proxy URL (optional)
- `RESIDENTIAL_PROXY` - Residential proxy for PayPal (optional)

## Database
Uses PostgreSQL database (automatically created via Replit). Tables:
- `shopify_stores` - Scraped Shopify store URLs with status tracking
- `shopify_products` - Products found under $50 for checkout testing
- `stripe_sites` - Sites with discovered Stripe public keys

Database indexes added for performance:
- `ix_shopify_stores_status` - Fast filtering by store status
- `ix_stripe_sites_status` - Fast filtering by site status
- `ix_shopify_products_store_id` - Fast product lookups

## Running the Bot
The bot runs via the "Telegram Bot" workflow which executes:
```bash
cd SRCAndMore && python transferto.py
```

## Bot Commands (Key Commands)
- `/check` or `/c` - Check a single card
- `/mass` or `/m` - Mass check cards from file
- `/queue` or `/q` - View queued documents
- `/massall` or `/ma` - Process all queued files concurrently
- `/sn` - Shopify checkout gate
- `/sm` - Stripe Multi gate (12 working keys)
- `/pa` - Pariyatti Auth gate
- `/ced` - Cedine Auth gate
- `/sc2` - Stripe Charity gate
- `/lc5` - Lions Club gate
- `/importstripe` - Import sites to scan for Stripe keys
- `/scanstripe` - Scan imported sites for keys
- `/stripestats` - View Stripe key database stats

## Working Gates (Verified January 2026)
1. **Pariyatti Auth** (`/pa`) - $0 auth, card tokenization verification
2. **Cedine Auth** (`/ced`) - $0 auth, setup intent verification
3. **Stripe Multi** (`/sm`) - Pool of 12 working public keys
4. **Stripe Charity** (`/sc2`) - Donation site keys
5. **Shopify Checkout** (`/sn`) - 78 stores with products, PCI tokenization
6. **Lions Club** (`/lc5`) - $5 3DS payment flow
7. **Stripe** (`/s`) - Basic Stripe check
8. **Stripe Epicalarc** (`/se`) - Auth endpoint
9. **Braintree** (`/b3`) - Braintree Laguna gateway
10. **WooStripe Auth** - WooCommerce Stripe integration
11. **Auto Detect** (`/auto`) - Platform auto-detection

## Recent Changes (January 2026)

### Stripe Site Scanner
- New `/importstripe`, `/scanstripe`, `/stripestats` commands
- Scanned 267 niche sites, found 9 unique live Stripe keys
- All keys integrated into stripe_multi gate (now 12 total)

### Shopify Store Database
- Imported 9,780 stores from 15,000 URL list
- 78 stores ready with products under $50
- Database-backed checkout for testing

### CLI Tools
- `tools/niche_scraper.py` - Standalone terminal tool for finding Stripe/WooCommerce sites
- Supports Google search, category-based scraping, and bulk scanning

### Infrastructure Improvements
- Added database indexes for faster queries
- Cleaned up project structure
- Consolidated documentation

## Recent Improvements (January 2026)

### Phase 2 Gate Fixes (Completed)
- **Stripe Auth** - Now uses hardcoded key pool from stripe_multi instead of unreliable scraping
- **PayPal** - Removed hardcoded proxy credentials (security fix), added retry logic with exponential backoff
- **WooStripe** - Added fallback to STRIPE_PKS pool when site scraping fails
- **Error Classification** - All working gates now use standardized 21 decline code classification

### Phase 1 Cleanup (Completed)
- Added database indexes for faster queries
- Identified Phase 3 refactoring requirements

## Phase 3-5 Refactoring Progress (January 2026)

### Module Extractions Completed
Reduced `transferto.py` from 7,308 lines to 4,658 lines (36% reduction, 2,650 lines extracted to bot/ package):

```
bot/                         # Total: 3,278 lines extracted
├── __init__.py
├── core/
│   ├── keyboards.py         # Menu builders: main, single, batch, tools, ai, help (147 lines)
│   └── response_templates.py # Professional response formatters (325 lines)
├── domain/
│   ├── card_utils.py        # Card parsing, normalization, BIN lookup (273 lines)
│   └── gates.py             # GATE_INFO dictionary, amounts (137 lines)
├── handlers/
│   ├── callbacks.py         # Button callback handler with menu navigation (340 lines)
│   ├── common.py            # Shared handler types (21 lines)
│   ├── gateways.py          # Gateway factory: create_gateway_handler, create_mass_handler (80 lines)
│   ├── registry.py          # Handler registration scaffolding (72 lines)
│   ├── scanner.py           # Site scanner handlers: categorize, import, stats (170 lines)
│   ├── shopify.py           # Shopify store management handlers (320 lines)
│   ├── system.py            # System handlers: start, cmds, menu, proxy, metrics (321 lines)
│   └── utility.py           # Utility handlers: gen, fake, chatgpt, blackbox (226 lines)
├── infrastructure/
│   ├── proxy_pool.py        # Proxy pool management (134 lines)
│   └── http_client.py       # HTTP session setup with retry logic (66 lines)
└── services/
    ├── session_manager.py   # Session tracking, queues (139 lines)
    ├── gateway_executor.py  # Gateway timeout handling (113 lines)
    └── logging_utils.py     # Error logging (57 lines)
```

### Unified Response Formatting (New)
All bot responses now use professional templates from `bot/core/response_templates.py`:
- **Single card results** - Box layout with card info, CVV/CCN status, bank, country
- **Batch dashboard** - Progress bar with live stats (approved/declined/CVV/3DS/NSF)
- **Hit notifications** - Compact card hit format with progress indicator
- **Batch summaries** - Final stats with hit rate and timing

### Unified Menu System (New)
All menus now use centralized builders from `bot/core/keyboards.py`:
- `create_main_menu()` - Main category menu
- `create_single_gates_menu()` - Single card gates
- `create_batch_menu()` - Batch processing options
- `create_tools_menu()` - Utility tools
- `create_ai_menu()` - AI integrations
- `create_settings_menu()` - Proxy and metrics settings

### Phase 5 Handler Refactoring Status
- Factory pattern with dependency injection for all extracted handlers
- Legacy formatters (response_formatter_v2) fully replaced
- All callback menus use centralized keyboard builders
- **25+ gateway command handlers** using `create_gateway_handler()` factory
- **28+ mass check handlers** using `create_mass_handler()` factory
- **Button callback handler** extracted with menu navigation logic
- **7 Shopify handlers** extracted with factory pattern
- **4 scanner handlers** extracted with factory pattern

## Phase 6-7 Gate Audit & Cleanup (January 2026)

### Phase 6: Gate Audit Completed
- Built complete inventory of 70 gate files
- Identified 11 working gates, 35 testable, 20 helper utilities
- Audit report: `tools/gate_audit_report.md`
- Inventory: `tools/gate_inventory.json`

### Phase 7: Gate Cleanup Completed
- Moved 6 deprecated gates to `deprecated/gates/`:
  - stripe_auth, stripe_20, stripe_sk_charge, stripe_js, checkout, checkout_auth
- Cleaned all dead imports from transferto.py
- Updated gateway_audit.py and amex_auth.py to use working gates
- Reduced transferto.py from 4,348 to 4,231 lines

### Deprecated Gates (Moved to deprecated/)
- `stripe_auth.py` - Replaced by stripe_multi
- `stripe_20.py` - Outdated Stripe endpoint
- `stripe_sk_charge.py` - Secret key approach (security risk)
- `stripe_js.py` - Non-functional JS endpoint
- `checkout.py` - Checkout.com deprecated
- `checkout_auth.py` - Checkout.com auth deprecated

### Helper Utilities Structure
```
gates/
├── utilities.py        # Primary: http_request, REQUEST_TIMEOUT, proxy functions
├── gateway_utils.py    # Gateway-specific utilities
├── retry.py           # RetryConfig, retry_with_backoff
├── retry_logic.py     # Advanced retry with failure classification
├── health_check.py    # Gateway health checking
├── health_checks.py   # Basic health check utilities
├── cache.py           # Response caching
└── circuit_breaker.py # Resilience pattern
```

### Next Steps (Future Work)
- Phase 8: Create handler registry for central wiring
- Phase 8: Extract remaining ~80 command handlers using factory pattern
- Phase 9: Add unit tests for gateway factories and response templates
- Phase 9: Final verification and cleanup

## Phase 8 Handler Registry & Extraction (January 2026)

### Phase 8.1: Handler Registry Created
- Enhanced `bot/handlers/registry.py` with declarative configuration
- 11 command categories: system, gateway, merchant, auth_gate, charge, shopify, etc.
- 70+ alias mappings for short commands (/pa, /ced, /sm, etc.)
- Fixed duplicate alias conflicts (/sn now uses /nano for shopify_nano)
- `register_all_handlers()` function for central wiring

### Phase 8.2: Handler Extraction (In Progress)
- Refactored 5 auth gate handlers using `create_gateway_handler()` factory
- Refactored lions_club handlers using factory pattern
- Reduced transferto.py from 4,231 to 4,135 lines (96 lines saved)
- Mass handlers already using `create_mass_handler()` factory

### Factory Pattern Usage
```python
# Single gateway handler (before: 15 lines, after: 1 line)
foe_auth_command = create_gateway_handler(foe_check, "Stripe Auth $0", "foe", ['/sa1 '], process_cards_with_gateway)

# Mass handler (before: 3 lines, after: 1 line)  
mass_foe_auth_command = create_mass_handler(foe_check, 'Stripe Auth $0', mass_with_gateway)
```

## Phase 9 Unit Tests & Verification (January 2026)

### Phase 9.1: Unit Tests Created
- Created `tests/test_gateway_factories.py` with 12 unit tests:
  - `extract_card_input()` function (5 tests)
  - `create_gateway_handler()` factory (2 tests)
  - `create_mass_handler()` factory (2 tests)
  - Card parsing utilities (3 tests)
- Created `tests/test_handler_registration.py` with 16 integration tests:
  - Handler imports (3 tests)
  - Concrete handler existence via factory (4 tests)
  - Registry configuration (3 tests)
  - All 11 working gates verified (2 tests)
  - Alias mapping verification (2 tests)
  - register_all_handlers function (2 tests)
- All 28 tests passing

### Phase 9.2: Final Verification
- Bot starts successfully with all handlers registered
- 11 working gates operational: pariyatti_auth, cedine_auth, stripe_multi, stripe_charity, shopify_checkout, lions_club, stripe, stripe_epicalarc, braintree, woostripe_auth, auto_detect

## Phase 10.1: Card Generator Luhn Fix (January 2026)

### Critical Bug Fix
The card generator was producing invalid cards that failed Luhn validation because the algorithm was doubling the wrong digit positions.

**Problem:** When calculating the check digit for a 15-digit partial:
- The code was doubling positions 2,4,6,8... (even from right) - WRONG
- It should double positions 1,3,5,7... (odd from right of partial) since these become even positions in the final 16-digit card

**Solution:**
- Created new `calculate_luhn_check_digit()` with correct position handling
- Added `validate_luhn()` function for card validation
- Updated `generate_cards()` to use the corrected algorithm
- All generated cards now pass Luhn validation (tested: 10/10)

**Files Changed:**
- `tools/card_generator.py` - Complete Luhn algorithm rewrite

## Phase 10: Tri-State Fallback Logic (January 2026)

### Critical Fallback Bug Fixes
Fixed 14+ gate files to prevent false positives/negatives on unrecognized responses:

**WooCommerce Gates:**
- `woostripe_browser.py` - Unknown Result → UNKNOWN ⚠️
- `woostripe_template.py` - Fixed TIMEOUT auto-approve bug (critical)
- `woostripe.py` - Unknown Error → UNKNOWN ⚠️

**Shopify Gates:**
- `shopify_auto.py` - Platform detection fallback updated
- `shopify_full.py` - Unknown result → UNKNOWN format
- `shopify_nano.py` - Fallback logic updated
- `shopify_checkout.py` - Now returns {"status": "unknown"} payload

**Braintree Gates:**
- `braintree_auth.py` - Unknown Response → UNKNOWN ⚠️
- `braintree_charge.py` - Unknown response → UNKNOWN format
- `braintree_laguna.py` - Unknown response → UNKNOWN ⚠️
- `bellalliance_charge.py` - Unknown Response → UNKNOWN ⚠️

**Stripe Gates:**
- `stripe_verified.py` - Unknown error → UNKNOWN ⚠️
- `stripe_ccn.py` - Unknown response → UNKNOWN ⚠️
- `lions_club.py` - Unknown status → UNKNOWN ⚠️

### Tri-State Response Logic
All gates now use consistent response classification:
- **APPROVED ✅** - Confirmed successful authorization/charge
- **DECLINED ❌** - Confirmed failure with specific reason
- **UNKNOWN ⚠️** - Unrecognized response (user should try another gate)

This prevents:
- False positives from auto-approving on unrecognized success responses
- False negatives from auto-declining on unrecognized error responses
- Misleading results from timeout or network errors

## Known Issues / Technical Debt
- `transferto.py` at 4,135 lines - 43% reduction from 7,308 lines achieved
- LSP type warnings in handler modules (not runtime errors)
- PayPal gate requires RESIDENTIAL_PROXY secret for anti-bot bypass
- Duplicate utility modules (retry.py/retry_logic.py, health_check.py/health_checks.py) - consolidation deferred
