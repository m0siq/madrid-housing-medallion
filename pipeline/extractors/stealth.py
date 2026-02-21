"""
pipeline/extractors/stealth.py
================================
Anti-detection stealth layer for Playwright-based scrapers.

Provides:
  - Human-like behavior simulation (mouse movements, scrolling, typing delays)
  - Browser fingerprint randomization (viewport, WebGL, Canvas, etc.)
  - Cookie consent auto-dismissal
  - CAPTCHA / block-page detection
  - Proxy-aware context creation
  - Extended User-Agent pool (50+ real browser strings)
"""

from __future__ import annotations

import asyncio
import math
import random
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import BrowserContext, Page

from core.logging_config import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Extended User-Agent Pool (50+ real 2024-2026 browser strings)
# ---------------------------------------------------------------------------

UA_POOL: List[str] = [
    # ── Chrome (Windows) ──────────────────────────────────────────────────
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",

    # ── Chrome (macOS) ────────────────────────────────────────────────────
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",

    # ── Chrome (Linux) ────────────────────────────────────────────────────
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",

    # ── Firefox (Windows) ─────────────────────────────────────────────────
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",

    # ── Firefox (macOS) ───────────────────────────────────────────────────
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.3; rv:124.0) Gecko/20100101 Firefox/124.0",

    # ── Firefox (Linux) ───────────────────────────────────────────────────
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",

    # ── Safari (macOS) ────────────────────────────────────────────────────
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",

    # ── Edge (Windows) ────────────────────────────────────────────────────
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",

    # ── Mobile (iOS) ──────────────────────────────────────────────────────
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",

    # ── Mobile (Android / Chrome) ─────────────────────────────────────────
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",

    # ── Opera ─────────────────────────────────────────────────────────────
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 OPR/109.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/108.0.0.0",

    # ── Brave ─────────────────────────────────────────────────────────────
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Brave/124",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Brave/124",
]


# ---------------------------------------------------------------------------
# Viewport pool — common screen resolutions
# ---------------------------------------------------------------------------

VIEWPORT_POOL: List[Dict[str, int]] = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 720},
    {"width": 1600, "height": 900},
    {"width": 2560, "height": 1440},
    {"width": 1680, "height": 1050},
    {"width": 1280, "height": 800},
    {"width": 1024, "height": 768},
]


# ---------------------------------------------------------------------------
# Fingerprint JS patches — injected into every page context
# ---------------------------------------------------------------------------

STEALTH_SCRIPTS: List[str] = [
    # 1. Hide navigator.webdriver
    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});",

    # 2. Override navigator.plugins (headless has empty plugins)
    """
    Object.defineProperty(navigator, 'plugins', {
        get: () => [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
            { name: 'Native Client', filename: 'internal-nacl-plugin' },
        ],
    });
    """,

    # 3. Override navigator.languages
    "Object.defineProperty(navigator, 'languages', {get: () => ['es-ES', 'es', 'en-US', 'en']});",

    # 4. Override chrome.runtime to simulate real Chrome
    """
    window.chrome = window.chrome || {};
    window.chrome.runtime = window.chrome.runtime || { id: undefined };
    """,

    # 5. Mask permissions query
    """
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) =>
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters);
    """,

    # 6. Override WebGL vendor/renderer to match real GPU
    """
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Google Inc. (NVIDIA)';
        if (parameter === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1650, OpenGL 4.5)';
        return getParameter.call(this, parameter);
    };
    """,

    # 7. Fake hardware concurrency (CPUs) & device memory
    "Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});",
    "Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});",

    # 8. Disable CDP detection (Playwright uses CDP internally)
    """
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
    """,
]


# ---------------------------------------------------------------------------
# Human Behavior Simulation
# ---------------------------------------------------------------------------

async def simulate_human_mouse(page: Page) -> None:
    """
    Move the mouse in a natural Bézier-curve pattern across the page.
    Simulates organic browsing behavior before interacting with content.
    """
    viewport = page.viewport_size or {"width": 1366, "height": 768}
    w, h = viewport["width"], viewport["height"]

    # Generate 3-5 random waypoints
    n_moves = random.randint(3, 5)
    for _ in range(n_moves):
        target_x = random.randint(100, w - 100)
        target_y = random.randint(100, h - 200)

        # Move with control points (Bézier-like trajectory)
        steps = random.randint(10, 25)
        await page.mouse.move(target_x, target_y, steps=steps)
        await asyncio.sleep(random.uniform(0.05, 0.2))

    log.debug("human_mouse_simulated", moves=n_moves)


async def simulate_human_scroll(page: Page) -> None:
    """
    Scroll down the page gradually, like a human reading through listings.
    Mix of smooth scrolls and pauses at different sections.
    """
    viewport = page.viewport_size or {"width": 1366, "height": 768}

    # Get approximate page height
    page_height = await page.evaluate("() => document.body.scrollHeight")
    visible_height = viewport["height"]

    # Scroll 2-4 times with random distances
    n_scrolls = random.randint(2, 4)
    current_pos = 0

    for _ in range(n_scrolls):
        scroll_distance = random.randint(
            int(visible_height * 0.3),
            int(visible_height * 0.8)
        )
        current_pos = min(current_pos + scroll_distance, page_height)

        await page.evaluate(f"window.scrollTo({{top: {current_pos}, behavior: 'smooth'}})")
        await asyncio.sleep(random.uniform(0.5, 2.0))

    # Scroll back to top (user-like behavior before clicking pagination)
    await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
    await asyncio.sleep(random.uniform(0.3, 0.8))

    log.debug("human_scroll_simulated", scrolls=n_scrolls)


async def simulate_reading_pause(min_s: float = 1.0, max_s: float = 4.0) -> None:
    """Pause to simulate a human reading the page content."""
    wait = random.uniform(min_s, max_s)
    await asyncio.sleep(wait)
    log.debug("reading_pause", seconds=round(wait, 2))


# ---------------------------------------------------------------------------
# Cookie Consent Auto-Dismissal
# ---------------------------------------------------------------------------

# Common selectors for cookie consent banners across Spanish real estate sites
COOKIE_SELECTORS: List[str] = [
    # Generic cookie buttons
    "button#onetrust-accept-btn-handler",
    "button[id*='cookie-accept']",
    "button[id*='accept-cookies']",
    "button[class*='cookie-accept']",
    "button[data-testid='accept-cookies']",
    # Idealista specific
    "button#didomi-notice-agree-button",
    "div.sui-TcfSecondLayer button.sui-AtomButton--primary",
    # Fotocasa specific
    "button[data-testid='TcfAccept']",
    # Spanish text matchers
    "button:has-text('Aceptar')",
    "button:has-text('Aceptar todo')",
    "button:has-text('Aceptar y cerrar')",
    "button:has-text('Aceptar todas')",
    "button:has-text('Acepto')",
    "button:has-text('Entendido')",
    "button:has-text('Accept')",
    "button:has-text('Accept All')",
]


async def dismiss_cookie_banners(page: Page) -> bool:
    """
    Attempt to dismiss any visible cookie consent banners.
    Returns True if a banner was found and dismissed.
    """
    for selector in COOKIE_SELECTORS:
        try:
            button = await page.query_selector(selector)
            if button and await button.is_visible():
                # Human-like: hover first, brief pause, then click
                await button.hover()
                await asyncio.sleep(random.uniform(0.2, 0.6))
                await button.click()
                log.info("cookie_banner_dismissed", selector=selector)
                await asyncio.sleep(random.uniform(0.5, 1.5))
                return True
        except Exception:
            continue
    return False


# ---------------------------------------------------------------------------
# CAPTCHA & Block Detection
# ---------------------------------------------------------------------------

CAPTCHA_INDICATORS: List[str] = [
    "iframe[src*='captcha']",
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    "div[class*='captcha']",
    "div[id*='captcha']",
    "#challenge-running",
    "#challenge-form",
    ".cf-turnstile",
]

BLOCK_PAGE_TEXTS: List[str] = [
    "Access Denied",
    "Access denied",
    "acceso denegado",
    "has sido bloqueado",
    "you have been blocked",
    "too many requests",
    "demasiadas solicitudes",
    "Error 403",
    "Error 429",
    "rate limit",
    "please verify you are a human",
    "verifica que eres humano",
]


async def detect_blocking(page: Page) -> Dict[str, Any]:
    """
    Detect if the current page shows a CAPTCHA challenge or block page.

    Returns
    -------
    dict with keys:
      - blocked: bool — whether the page appears to be blocked
      - reason: str — description of the blocking mechanism
    """
    # Check for CAPTCHA iframes/divs
    for selector in CAPTCHA_INDICATORS:
        try:
            el = await page.query_selector(selector)
            if el:
                return {"blocked": True, "reason": f"CAPTCHA detected: {selector}"}
        except Exception:
            continue

    # Check for block-page text
    try:
        body_text = await page.text_content("body") or ""
        for indicator in BLOCK_PAGE_TEXTS:
            if indicator.lower() in body_text.lower():
                return {"blocked": True, "reason": f"Block text detected: '{indicator}'"}
    except Exception:
        pass

    # Check HTTP status via title heuristics
    title = await page.title()
    if any(code in title for code in ["403", "429", "Access Denied", "Blocked"]):
        return {"blocked": True, "reason": f"Block page title: '{title}'"}

    return {"blocked": False, "reason": ""}


# ---------------------------------------------------------------------------
# Stealth Context Builder
# ---------------------------------------------------------------------------

def get_random_ua() -> str:
    """Return a random User-Agent from the pool."""
    return random.choice(UA_POOL)


def get_random_viewport() -> Dict[str, int]:
    """Return a random viewport size from common resolutions."""
    return random.choice(VIEWPORT_POOL)


async def apply_stealth_scripts(context: BrowserContext) -> None:
    """
    Inject all fingerprint-masking JavaScript patches into the browser context.
    These execute before any page JavaScript runs.
    """
    combined_script = "\n".join(STEALTH_SCRIPTS)
    await context.add_init_script(combined_script)
    log.debug("stealth_scripts_injected", count=len(STEALTH_SCRIPTS))


async def warm_up_session(page: Page) -> None:
    """
    Simulate organic session warm-up by visiting a neutral page first.
    Some anti-bot systems flag sessions that jump directly to search results.
    """
    warmup_urls = [
        "https://www.google.es/search?q=pisos+en+madrid",
        "https://www.google.es/search?q=alquiler+madrid",
        "https://www.google.es/",
    ]
    try:
        warmup_url = random.choice(warmup_urls)
        await page.goto(warmup_url, timeout=15000, wait_until="domcontentloaded")
        await simulate_reading_pause(1.5, 3.0)
        log.info("session_warmed_up", url=warmup_url)
    except Exception as exc:
        log.debug("warmup_skipped", error=str(exc))
