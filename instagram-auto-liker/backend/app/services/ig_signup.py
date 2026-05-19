"""Playwright-based Instagram signup flow.

Drives a real Chromium browser through Instagram's email-signup form, fills
the fields, awaits the email OTP from Mailgun, and (if required) requests a
phone number from the SMS provider and submits the SMS OTP.

This is a best-effort implementation. Instagram frequently changes the signup
flow and deploys CAPTCHA / behavioural challenges; expect partial failures.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any, Callable

from . import mailgun, sms_provider as sms_svc
from .pw_login import ensure_chromium_installed

logger = logging.getLogger(__name__)

LogCb = Callable[[str], Any]
PhoneCb = Callable[[str], Any]


def _slow_type(locator, text: str) -> None:
    for ch in text:
        locator.type(ch, delay=random.randint(50, 130))


def perform_signup(
    *,
    email: str,
    full_name: str,
    username: str,
    password: str,
    proxy: str | None,
    mailgun_domain: str,
    mailgun_api_key: str,
    sms_provider_type: str | None,
    sms_api_key: str | None,
    sms_country: str,
    on_log: LogCb,
    on_phone_assigned: PhoneCb,
) -> dict[str, Any]:
    try:
        ensure_chromium_installed()
    except Exception as exc:
        return {"success": False, "error": f"Chromium not available: {exc}"}

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return {"success": False, "error": f"Playwright import failed: {exc}"}

    activation_id: str | None = None
    try:
        with sync_playwright() as p:
            launch_kwargs: dict[str, Any] = {"headless": True}
            if proxy:
                launch_kwargs["proxy"] = {"server": proxy}
            browser = p.chromium.launch(**launch_kwargs)
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
                locale="en-US",
            )
            page = ctx.new_page()
            on_log("Opening Instagram signup page")
            page.goto("https://www.instagram.com/accounts/emailsignup/", timeout=45_000)
            page.wait_for_load_state("networkidle", timeout=30_000)
            time.sleep(random.uniform(1.5, 3.0))

            try:
                page.get_by_role("button", name="Allow all cookies").click(timeout=4_000)
            except Exception:
                pass

            on_log("Filling signup form")
            try:
                _slow_type(page.locator('input[name="emailOrPhone"]'), email)
                _slow_type(page.locator('input[name="fullName"]'), full_name)
                _slow_type(page.locator('input[name="username"]'), username)
                _slow_type(page.locator('input[name="password"]'), password)
            except Exception as exc:
                browser.close()
                return {"success": False, "error": f"Form fill failed: {exc}"}

            time.sleep(random.uniform(0.8, 1.6))
            try:
                page.get_by_role("button", name="Sign up").click(timeout=10_000)
            except Exception:
                try:
                    page.locator('button[type="submit"]').first.click(timeout=10_000)
                except Exception as exc:
                    browser.close()
                    return {"success": False, "error": f"Submit failed: {exc}"}

            page.wait_for_load_state("networkidle", timeout=30_000)
            time.sleep(random.uniform(1.0, 2.5))

            # ---- Birthday step ----
            on_log("Handling birthday step")
            try:
                page.select_option('select[title="Month:"]', str(random.randint(1, 12)))
                page.select_option('select[title="Day:"]', str(random.randint(1, 28)))
                page.select_option('select[title="Year:"]', str(random.randint(1990, 2002)))
                time.sleep(random.uniform(0.5, 1.2))
                page.get_by_role("button", name="Next").click(timeout=10_000)
                page.wait_for_load_state("networkidle", timeout=30_000)
            except Exception:
                on_log("Birthday step not present or skipped")

            # ---- Email OTP ----
            on_log(f"Waiting for email OTP at {email} (up to 180s)")
            otp = mailgun.wait_for_otp(
                mailgun_domain=mailgun_domain,
                api_key=mailgun_api_key,
                recipient=email,
                timeout_seconds=180,
            )
            if not otp:
                browser.close()
                return {"success": False, "error": "Email OTP did not arrive within 180s"}

            on_log(f"OTP received: {otp[:2]}****")
            try:
                conf = page.locator('input[name="email_confirmation_code"]').first
                _slow_type(conf, otp)
                time.sleep(random.uniform(0.4, 1.0))
                page.get_by_role("button", name="Next").click(timeout=10_000)
                page.wait_for_load_state("networkidle", timeout=30_000)
            except Exception as exc:
                on_log(f"Email-OTP submission UI not detected: {exc}")

            # ---- Phone challenge (optional) ----
            phone_input_visible = False
            try:
                phone_input_visible = page.locator(
                    'input[name="phone_number"], input[name="phoneNumber"]'
                ).first.is_visible(timeout=3_000)
            except Exception:
                phone_input_visible = False

            if phone_input_visible:
                if not (sms_provider_type and sms_api_key):
                    browser.close()
                    return {
                        "success": False,
                        "error": "Instagram requested phone verification but no SMS provider configured",
                    }
                on_log(f"Requesting phone number from {sms_provider_type}")
                try:
                    phone, activation_id = sms_svc.get_number(
                        sms_provider_type, sms_api_key, sms_country
                    )
                except Exception as exc:
                    browser.close()
                    return {"success": False, "error": f"SMS provider getNumber failed: {exc}"}

                on_phone_assigned(phone)
                on_log(f"Assigned phone {phone}")
                try:
                    sel = page.locator('input[name="phone_number"], input[name="phoneNumber"]').first
                    _slow_type(sel, phone)
                    page.get_by_role("button", name="Next").click(timeout=10_000)
                    page.wait_for_load_state("networkidle", timeout=30_000)
                except Exception as exc:
                    sms_svc.finish(sms_provider_type, sms_api_key, activation_id, False)
                    browser.close()
                    return {"success": False, "error": f"Phone submit failed: {exc}"}

                on_log("Waiting for SMS code (up to 300s)")
                sms_code = sms_svc.get_code(
                    sms_provider_type, sms_api_key, activation_id, timeout=300
                )
                if not sms_code:
                    sms_svc.finish(sms_provider_type, sms_api_key, activation_id, False)
                    browser.close()
                    return {"success": False, "error": "SMS code did not arrive in time"}
                try:
                    sms_input = page.locator(
                        'input[name="confirmation_code"], input[name="phone_confirmation_code"]'
                    ).first
                    _slow_type(sms_input, sms_code)
                    page.get_by_role("button", name="Next").click(timeout=10_000)
                    page.wait_for_load_state("networkidle", timeout=30_000)
                    sms_svc.finish(sms_provider_type, sms_api_key, activation_id, True)
                except Exception as exc:
                    sms_svc.finish(sms_provider_type, sms_api_key, activation_id, False)
                    browser.close()
                    return {"success": False, "error": f"SMS submit failed: {exc}"}

            # ---- Persist session cookies ----
            try:
                cookies = ctx.cookies()
            except Exception:
                cookies = []
            browser.close()

            session_blob = {"cookies": cookies, "user_agent": "Mozilla/5.0", "username": username}
            on_log("Signup completed; cookies captured")
            return {"success": True, "session": session_blob}
    except Exception as exc:
        logger.exception("[ig_signup] unexpected error")
        if activation_id and sms_provider_type and sms_api_key:
            sms_svc.finish(sms_provider_type, sms_api_key, activation_id, False)
        return {"success": False, "error": f"Unexpected: {exc}"}
