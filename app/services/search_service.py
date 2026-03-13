from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.config import Config
from app.services.login_state_service import LoginStateService
from app.services.part_filter_service import reject_reason

API_URL_PATTERN = "h5api.m.goofish.com/h5/mtop.taobao.idlemtopsearch.pc.search"
RISK_SELECTORS = ["div.baxia-dialog-mask", "div.J_MIDDLEWARE_FRAME_WIDGET"]
LOGIN_MARKERS = ["passport.goofish.com", "mini_login"]
PRICE_RE = re.compile(r"(\d+(?:\.\d+)?)")


class SearchError(Exception):
    pass


class LoginRequiredError(SearchError):
    pass


class RiskControlError(SearchError):
    pass


class SearchService:
    def __init__(self, cfg: Config, state_service: LoginStateService):
        self.cfg = cfg
        self.state_service = state_service

    async def search(self, keyword: str, category: str, limit: int, strategy: Optional[str], account_state_file: Optional[str]) -> Dict[str, Any]:
        if not keyword.strip():
            raise ValueError("keyword must not be empty")
        state_file = self.state_service.resolve_state_file(strategy, account_state_file)
        result = await self._search_with_state(keyword.strip(), category.strip(), max(1, limit), state_file)
        result["state_file"] = state_file.name
        return result

    async def validate_state(self, strategy: Optional[str], account_state_file: Optional[str]) -> Dict[str, Any]:
        state_file = self.state_service.resolve_state_file(strategy, account_state_file)
        result = await self._search_with_state(self.cfg.validation_keyword, "", 1, state_file)
        return {
            "valid": True,
            "state_file": state_file.name,
            "keyword": self.cfg.validation_keyword,
            "sample_count": result.get("sample_count", 0),
            "page_url": result.get("page_url"),
        }

    async def _search_with_state(self, keyword: str, category: str, limit: int, state_file) -> Dict[str, Any]:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=self.cfg.run_headless,
                channel=None if self.cfg.browser_channel == "chromium" else self.cfg.browser_channel,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ],
            )
            try:
                context = await browser.new_context(storage_state=str(state_file))
                page = await context.new_page()
                await page.goto("https://www.goofish.com/", wait_until="domcontentloaded", timeout=self.cfg.search_timeout_ms)
                search_url = "https://www.goofish.com/search?" + urlencode({"q": keyword})
                async with page.expect_response(lambda resp: API_URL_PATTERN in resp.url, timeout=self.cfg.search_timeout_ms) as response_info:
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=self.cfg.search_timeout_ms)
                if self._is_login_url(page.url):
                    raise LoginRequiredError("goofish search requires a valid login state")
                await self._check_risk(page)
                response = await response_info.value
                payload = await response.json()
                items = self._parse_search_payload(payload, keyword, category, limit)
                return {
                    "keyword": keyword,
                    "category": category,
                    "limit": limit,
                    "page_url": page.url,
                    "products": items,
                    "sample_count": len(items),
                }
            finally:
                await browser.close()

    async def _check_risk(self, page) -> None:
        for selector in RISK_SELECTORS:
            try:
                await page.locator(selector).first.wait_for(state="visible", timeout=1500)
                raise RiskControlError(f"goofish risk control detected: {selector}")
            except PlaywrightTimeoutError:
                continue

    @staticmethod
    def _is_login_url(url: str) -> bool:
        lowered = (url or "").lower()
        return any(marker in lowered for marker in LOGIN_MARKERS)

    def _parse_search_payload(self, payload: Dict[str, Any], keyword: str, category: str, limit: int) -> List[Dict[str, Any]]:
        items = (((payload or {}).get("data") or {}).get("resultList") or [])
        parsed: List[Dict[str, Any]] = []
        for raw in items:
            parsed_item = self._parse_item(raw, keyword, category)
            if parsed_item is None:
                continue
            parsed.append(parsed_item)
            if len(parsed) >= limit:
                break
        return parsed

    def _parse_item(self, raw: Dict[str, Any], keyword: str, category: str) -> Optional[Dict[str, Any]]:
        item = (((raw or {}).get("data") or {}).get("item") or {})
        main = ((((item.get("main") or {}).get("exContent")) or {}))
        click_args = ((((item.get("main") or {}).get("clickParam") or {}).get("args")) or {})
        title = str(main.get("title") or "").strip()
        if not title:
            return None
        reject = reject_reason(title, category)
        if reject is not None:
            return None
        price = self._parse_price(main.get("price"))
        if price is None:
            return None
        target_url = str(((item.get("main") or {}).get("targetUrl")) or "").replace("fleamarket://", "https://www.goofish.com/")
        return {
            "source_platform": "goofish",
            "keyword": keyword,
            "category": category,
            "item_id": str(main.get("itemId") or ""),
            "title": title,
            "price": price,
            "currency": "CNY",
            "seller": str(main.get("userNickName") or ""),
            "area": str(main.get("area") or ""),
            "url": target_url,
            "image_url": str(main.get("picUrl") or ""),
            "published_at": self._parse_publish_time(click_args.get("publishTime")),
            "tags": self._extract_tags(main, click_args),
            "raw_payload": raw,
        }

    @staticmethod
    def _parse_price(price_parts: Any) -> Optional[float]:
        if isinstance(price_parts, list):
            text = "".join(str(part.get("text", "")) for part in price_parts if isinstance(part, dict))
        else:
            text = str(price_parts or "")
        text = text.replace("当前价", "").replace("¥", "").strip()
        if not text:
            return None
        if "万" in text:
            try:
                return round(float(text.replace("万", "")) * 10000, 2)
            except ValueError:
                return None
        match = PRICE_RE.search(text)
        if not match:
            return None
        try:
            return round(float(match.group(1)), 2)
        except ValueError:
            return None

    @staticmethod
    def _parse_publish_time(timestamp: Any) -> Optional[str]:
        if timestamp is None:
            return None
        text = str(timestamp)
        if not text.isdigit():
            return None
        if len(text) >= 13:
            text = text[:13]
        return text

    @staticmethod
    def _extract_tags(main: Dict[str, Any], click_args: Dict[str, Any]) -> List[str]:
        tags: List[str] = []
        if click_args.get("tag") == "freeship":
            tags.append("包邮")
        for tag_item in ((((main.get("fishTags") or {}).get("r1")) or {}).get("tagList") or []):
            content = (((tag_item or {}).get("data") or {}).get("content")) or ""
            if content:
                tags.append(str(content))
        return tags
