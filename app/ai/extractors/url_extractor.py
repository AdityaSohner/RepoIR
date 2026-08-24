import asyncio
import os


class LinkExtractor:
    """
    URL content extractor using Playwright (full JS rendering) + trafilatura (clean text).
    Falls back to a lightweight requests-based extraction if Playwright fails.
    """

    def extract(self, url: str, **kwargs) -> dict:
        """
        Synchronous entry point called by the ingestion pipeline.
        Runs the async Playwright extraction in a dedicated event loop.
        """
        try:
            # asyncio.run() creates a fresh loop — safe since ingestion runs in a thread
            raw_text, title = asyncio.run(self._playwright_extract(url))
        except Exception as e:
            print(f"[URL] Playwright extraction failed, trying requests fallback: {e}")
            raw_text, title = self._requests_fallback(url)

        if not raw_text.strip():
            print(f"[URL] No content extracted from: {url}")

        return {
            "raw_text": raw_text,
            "metadata": {
                "file_type": "url",
                "title": title or url,
                "extraction_status": "success" if raw_text.strip() else "empty"
            }
        }

    async def _playwright_extract(self, url: str) -> tuple[str, str]:
        """
        Load the page with Playwright (Chromium, headless), wait for network idle
        so JS-rendered content is fully in the DOM, then extract clean text via trafilatura.
        """
        from playwright.async_api import async_playwright
        import trafilatura

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                locale="en-US",
                viewport={"width": 1280, "height": 800},
            )
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
            except Exception:
                # Some sites never reach networkidle — fall back to domcontentloaded
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)

            html = await page.content()
            title = await page.title()
            await browser.close()

        # trafilatura strips boilerplate, ads, nav, and returns clean article text
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
        ) or ""

        return text.strip(), title.strip()

    def _requests_fallback(self, url: str) -> tuple[str, str]:
        """
        Lightweight fallback: plain HTTP GET + trafilatura.
        Works for simple static sites; fails on JS-heavy pages.
        """
        try:
            import requests
            import trafilatura

            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            html = response.text
            text = trafilatura.extract(html, include_tables=True, no_fallback=False) or ""
            # Try to parse title from <title> tag
            import re
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else url
            return text.strip(), title
        except Exception as e:
            print(f"[URL] Requests fallback also failed: {e}")
            return "", ""
