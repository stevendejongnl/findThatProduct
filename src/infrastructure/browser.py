from __future__ import annotations
import logging
from typing import Any

from playwright.async_api import async_playwright, Browser, Playwright

logger = logging.getLogger(__name__)

_pw: Playwright | None = None
_browser: Browser | None = None


async def start_browser() -> None:
    global _pw, _browser
    _pw = await async_playwright().start()
    _browser = await _pw.chromium.launch(headless=True)
    logger.info("Playwright browser started")


async def stop_browser() -> None:
    global _pw, _browser
    if _browser:
        await _browser.close()
        _browser = None
    if _pw:
        await _pw.stop()
        _pw = None
    logger.info("Playwright browser stopped")


def get_browser() -> Browser:
    if _browser is None:
        raise RuntimeError("Browser not started — call start_browser() first")
    return _browser


async def fetch_with_browser(
    url: str,
    *,
    wait_for: str | None = None,
    timeout: int = 15_000,
    extra_headers: dict[str, str] | None = None,
) -> str:
    browser = get_browser()
    context = await browser.new_context(
        locale="nl-NL",
        extra_http_headers={
            "Accept-Language": "nl-NL,nl;q=0.9",
            **(extra_headers or {}),
        },
    )
    page = await context.new_page()
    try:
        await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        if wait_for:
            await page.wait_for_selector(wait_for, timeout=timeout)
        return await page.content()
    finally:
        await page.close()
        await context.close()
