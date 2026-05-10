"""Playwright-based Instagram login — real browser, real fingerprint.

Flow
────
1. Launch headless Chromium (with optional proxy)
2. Navigate to instagram.com/accounts/login/
3. Fill username + password with human-like typing delays
4. Handle optional 2FA code injection
5. Wait for successful redirect to home feed
6. Extract cookies → pass sessionid to instagrapi login_by_sessionid()
7. Return instagrapi session settings dict for storage

Why Playwright?
───────────────
instagrapi talks directly to Instagram's private API, which means the
request lacks a real browser fingerprint (Canvas, WebGL, HTTP/2 headers,
Sec-CH-UA, etc.).  Playwright uses a real Chromium engine so Instagram sees
a genuine browser session — dramatically reducing the chance of challenge /
ban on login.
"""

from __future__ import annotations

import asyncio
import logging
import random

import os

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    async_playwright,
)

logger = logging.getLogger(__name__)

_IG_LOGIN_URL = "https://www.instagram.com/accounts/login/"
_IG_HOME_URL  = "https://www.instagram.com/"

# On Replit / NixOS the Playwright-bundled headless-shell is missing system libs.
# The nix store ships a fully-linked Chromium that works out of the box.
_NIX_CHROMIUM = (
    "/nix/store/0n9rl5l9syy808xi9bk4f6dhnfrvhkww-playwright-browsers-chromium"
    "/chromium-1080/chrome-linux/chrome"
)


def _chromium_executable() -> str | None:
    """Return the best available Chromium executable path."""
    # Prefer explicit override from environment
    env_path = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path
    # Fall back to the nix-store bundled version (works on Replit)
    if os.path.isfile(_NIX_CHROMIUM):
        return _NIX_CHROMIUM
    # Let Playwright find it automatically (works on standard Linux VPS)
    return None


# Realistic mobile user-agent (iPhone 15 / iOS 17)
_MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Mobile/15E148 Safari/604.1"
)


class PWLoginError(Exception):
    """Raised when Playwright-based login fails."""


class PWChallengeRequired(PWLoginError):
    pass


class PW2FARequired(PWLoginError):
    pass


# ─── typing helpers ───────────────────────────────────────────────────────────

async def _human_type(page: Page, selector: str, text: str) -> None:
    """Click a field then type character-by-character with random delays."""
    await page.click(selector)
    await asyncio.sleep(random.uniform(0.3, 0.7))
    for ch in text:
        await page.keyboard.type(ch)
        await asyncio.sleep(random.uniform(0.05, 0.18))


async def _random_sleep(mn: float = 0.8, mx: float = 2.0) -> None:
    await asyncio.sleep(random.uniform(mn, mx))


# ─── cookie extraction ────────────────────────────────────────────────────────

async def _extract_sessionid(context: BrowserContext) -> str | None:
    cookies = await context.cookies("https://www.instagram.com")
    for c in cookies:
        if c["name"] == "sessionid":
            return c["value"]
    return None


async def _extract_all_cookies(context: BrowserContext) -> list[dict]:
    return await context.cookies("https://www.instagram.com")


# ─── main login coroutine ─────────────────────────────────────────────────────

async def _do_login(
    username: str,
    password: str,
    proxy: str | None,
    verification_code: str | None,
    timeout_ms: int,
) -> dict:
    """Run the full Playwright login flow. Returns cookies list."""
    proxy_settings = None
    if proxy:
        proxy_settings = {"server": proxy}

    async with async_playwright() as pw:
        exe = _chromium_executable()
        launch_kwargs: dict = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
            "proxy": proxy_settings,
        }
        if exe:
            launch_kwargs["executable_path"] = exe
            logger.info("[pw_login] Using Chromium at: %s", exe)

        browser: Browser = await pw.chromium.launch(**launch_kwargs)

        context: BrowserContext = await browser.new_context(
            viewport={"width": 390, "height": 844},   # iPhone 14 Pro
            user_agent=_MOBILE_UA,
            locale="ar-SA",
            timezone_id="Asia/Riyadh",
            color_scheme="dark",
            # Mask automation signals
            extra_http_headers={
                "Accept-Language": "ar-SA,ar;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        )

        # Hide navigator.webdriver
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['ar-SA', 'ar', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
        """)

        page: Page = await context.new_page()

        try:
            logger.info("[pw_login] Navigating to Instagram login page")
            await page.goto(_IG_LOGIN_URL, wait_until="domcontentloaded", timeout=timeout_ms)
            await _random_sleep(1.5, 3.0)

            # Accept cookies popup if present
            try:
                accept_btn = page.locator("text=Allow all cookies").first
                if await accept_btn.is_visible(timeout=3000):
                    await accept_btn.click()
                    await _random_sleep(0.5, 1.2)
            except Exception:
                pass

            # Wait for username field
            try:
                await page.wait_for_selector('input[name="username"]', timeout=15000)
            except Exception as exc:
                raise PWLoginError("تعذّر تحميل صفحة تسجيل الدخول") from exc

            await _random_sleep(0.8, 1.5)
            logger.info("[pw_login] Typing username")
            await _human_type(page, 'input[name="username"]', username)

            await _random_sleep(0.4, 0.9)
            logger.info("[pw_login] Typing password")
            await _human_type(page, 'input[name="password"]', password)

            await _random_sleep(0.6, 1.2)

            # Click login button
            login_btn = page.locator('button[type="submit"]').first
            await login_btn.click()
            logger.info("[pw_login] Clicked login button — waiting for response")

            # Wait for redirect or 2FA prompt
            try:
                await page.wait_for_url(
                    lambda url: (
                        "instagram.com" in url
                        and "/accounts/login/" not in url
                    ),
                    timeout=20000,
                )
            except Exception:
                current_url = page.url
                logger.warning("[pw_login] No redirect after login. Current URL: %s", current_url)

            await _random_sleep(1.0, 2.5)
            current_url = page.url

            # ── Detect 2FA prompt ──────────────────────────────────────────
            two_fa_selectors = [
                'input[name="verificationCode"]',
                'input[aria-label*="Security Code"]',
                'input[aria-label*="رمز"]',
                'input[placeholder*="code"]',
            ]
            is_2fa = False
            for sel in two_fa_selectors:
                try:
                    if await page.locator(sel).is_visible(timeout=2000):
                        is_2fa = True
                        break
                except Exception:
                    pass

            if is_2fa:
                if not verification_code:
                    logger.info("[pw_login] 2FA required but no code provided")
                    raise PW2FARequired("يتطلب رمز التحقق الثنائي (2FA)")

                logger.info("[pw_login] Entering 2FA code")
                for sel in two_fa_selectors:
                    try:
                        if await page.locator(sel).is_visible(timeout=1000):
                            await _human_type(page, sel, verification_code)
                            break
                    except Exception:
                        pass

                await _random_sleep(0.5, 1.0)
                confirm_selectors = [
                    'button:has-text("Confirm")',
                    'button:has-text("Verify")',
                    'button[type="submit"]',
                ]
                clicked = False
                for sel in confirm_selectors:
                    try:
                        btn = page.locator(sel).first
                        if await btn.is_visible(timeout=1500):
                            await btn.click()
                            clicked = True
                            break
                    except Exception:
                        pass
                if not clicked:
                    await page.keyboard.press("Enter")

                try:
                    await page.wait_for_url(
                        lambda url: (
                            "instagram.com" in url
                            and "/accounts/login/" not in url
                            and "two_factor" not in url
                        ),
                        timeout=20000,
                    )
                except Exception as exc:
                    raise PWLoginError("فشل التحقق بخطوتين") from exc

                await _random_sleep(1.0, 2.0)

            # ── Detect challenge / suspicious login ────────────────────────
            current_url = page.url
            if "challenge" in current_url or "checkpoint" in current_url:
                raise PWChallengeRequired(
                    "Instagram طلب تحقق إضافي (Challenge). افتح الحساب يدوياً في المتصفح أولاً."
                )

            # ── Check successful login ─────────────────────────────────────
            sessionid = await _extract_sessionid(context)
            if not sessionid:
                raise PWLoginError(
                    "لم يتم تسجيل الدخول بنجاح — تحقق من اسم المستخدم وكلمة المرور"
                )

            all_cookies = await _extract_all_cookies(context)
            logger.info("[pw_login] Login successful — sessionid extracted")

            # Dismiss "Save login info" popup if it appears
            try:
                not_now = page.locator("text=Not Now").first
                if await not_now.is_visible(timeout=3000):
                    await not_now.click()
            except Exception:
                pass

            await browser.close()

            # Return cookie list (compatible with our existing cookies login)
            return {
                "cookies": all_cookies,
                "sessionid": sessionid,
            }

        except (PWLoginError, PWChallengeRequired, PW2FARequired):
            await browser.close()
            raise
        except Exception as exc:
            await browser.close()
            raise PWLoginError(f"خطأ في تشغيل المتصفح: {exc}") from exc


# ─── public sync wrapper (called from FastAPI sync route via thread pool) ────

def login_with_playwright(
    username: str,
    password: str,
    proxy: str | None = None,
    verification_code: str | None = None,
    timeout_ms: int = 60_000,
) -> dict:
    """Synchronous wrapper around the async Playwright login.

    Returns a dict with keys:
        cookies   — list of raw cookie dicts
        sessionid — the Instagram sessionid value
    """
    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(
            _do_login(username, password, proxy, verification_code, timeout_ms)
        )
        loop.close()
        return result
    except (PWLoginError, PWChallengeRequired, PW2FARequired):
        raise
    except Exception as exc:
        raise PWLoginError(f"Playwright error: {exc}") from exc
