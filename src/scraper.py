#!/usr/bin/env python3
"""
港股量化新聞爬蟲模組 (HK Stock News Polite Scraper) - V2.1 終極防線版
特色：
- 嚴格遵守禮貌爬取 (3~7 秒隨機延遲)
- 403/429/50X 錯誤優雅降級
- 新增「泛用型 <a> 標籤」終極備用防線，無懼網站改版
- 完美對接 Gemini Analyzer
"""

import json
import logging
import random
import time
from typing import Any, Dict, List
from urllib.parse import urljoin

from scrapling.fetchers import StealthyFetcher

# 設置日誌格式
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("HKStockScraper")

# 8 大精選源頭配置 (移除強力封鎖的 Bloomberg)
SOURCE_CONFIGS = [
    {
        "id": "sina_hk",
        "name": "新浪港股",
        "url": "https://finance.sina.com.cn/stock/hkstock/",
        "selectors": ["ul.list_009 li a", ".news-list li a", "div.feed-card-item h2 a"],
    },
    {
        "id": "gelonghui",
        "name": "格隆匯",
        "url": "https://www.gelonghui.com/",
        "selectors": ["section.article-item h2 a", ".article-content a", ".news-item a"],
    },
    {
        "id": "hkej",
        "name": "信報財經",
        "url": "https://www.hkej.com/instantnews/hongkong",
        "selectors": ["div.allNewsList h3 a", ".listing h3 a", "h3.subhead a"],
    },
    {
        "id": "cnbc_asia",
        "name": "CNBC Asia",
        "url": "https://www.cnbc.com/markets/asia-markets/",
        "selectors": ["a.Card-title", ".RiverHeadline-headline a"],
    },
    {
        "id": "marketwatch_asia",
        "name": "MarketWatch Asia",
        "url": "https://www.marketwatch.com/markets/asia",
        "selectors": ["h3.article__headline a", "div.article__content a.link"],
    },
    {
        "id": "nikkei_asia",
        "name": "Nikkei Asia",
        "url": "https://asia.nikkei.com/business/markets",
        "selectors": ["article.article h2 a", "h2.headline a", ".article-title a"],
    },
    {
        "id": "zhitong",
        "name": "智通財經",
        "url": "https://www.zhitongcaijing.com/",
        "selectors": ["div.res-list a", ".news-item a", "div.content-box a"],
    },
    {
        "id": "hstong",
        "name": "華盛通資訊",
        "url": "https://www.hstong.com/news",
        "selectors": ["div.news-item a", "div.article-item a", "h3 a"],
    },
]


class HKStockScraper:
    def __init__(self, timeout_ms: int = 45000):
        self.timeout_ms = timeout_ms

    def _safe_get_text(self, element: Any) -> str:
        if element is None:
            return ""
        try:
            text = element.css("::text").get()
            if text and text.strip():
                return text.strip()
        except Exception:
            pass
        if hasattr(element, "text") and isinstance(element.text, str):
            return element.text.strip()
        return ""

    def _safe_get_href(self, element: Any) -> str:
        if element is None:
            return ""
        try:
            href = element.css("::attr(href)").get()
            if href and href.strip():
                return href.strip()
        except Exception:
            pass
        if hasattr(element, "attrib") and isinstance(element.attrib, dict):
            return element.attrib.get("href", "").strip()
        return ""

    def _parse_elements(self, page_adaptor: Any, base_url: str, selectors: List[str], source_name: str) -> List[Dict[str, str]]:
        items = []
        seen_links = set()

        # 🚨 核心改動：將泛用的 "a" 標籤作為終極備用防線，無懼網站改版
        active_selectors = selectors + ["a"]

        for sel in active_selectors:
            try:
                elements = page_adaptor.css(sel)
                if not elements:
                    continue

                for el in elements:
                    title = self._safe_get_text(el)
                    raw_href = self._safe_get_href(el)

                    # 標題太短 (少於 8 個字) 或無效連結直接濾除
                    if not title or len(title) < 8 or not raw_href or raw_href.startswith("javascript:"):
                        continue
                    
                    # 排除網站導覽列與雜訊按鈕
                    skip_words = ["登入", "登錄", "login", "register", "首頁", "下載", "app", "about", "忘記密碼"]
                    if any(w in title.lower() for w in skip_words):
                        continue

                    full_url = urljoin(base_url, raw_href)
                    if full_url in seen_links:
                        continue

                    seen_links.add(full_url)
                    items.append({
                        "source": source_name,
                        "title": title,
                        "link": full_url,
                    })

                # 如果成功抓到 3 條以上，代表這個選擇器是精準有效的，立刻跳出迴圈
                if len(items) >= 3:
                    break
            except Exception as e:
                logger.debug(f"選擇器 '{sel}' 解析失敗: {e}")
                continue

        return items

    def fetch_source(self, config: Dict[str, Any]) -> List[Dict[str, str]]:
        name = config["name"]
        url = config["url"]
        logger.info(f"開始抓取: {name} ({url})")

        try:
            response = StealthyFetcher.fetch(url, timeout=self.timeout_ms, headless=True)
            status = getattr(response, "status", 200)

            if status in (401, 403, 429):
                logger.warning(f"⚠️ [{name}] 遭遇存取限制 (HTTP {status})，已優雅跳過該源頭。")
                return []
            if status >= 500:
                logger.warning(f"⚠️ [{name}] 目標伺服器內部異常 (HTTP {status})，已優雅跳過該源頭。")
                return []

            news_list = self._parse_elements(
                page_adaptor=response,
                base_url=url,
                selectors=config["selectors"],
                source_name=name,
            )

            logger.info(f"✅ [{name}] 成功取得 {len(news_list)} 則新聞標題。")
            return news_list

        except Exception as e:
            err_msg = str(e).split("\n")[0]
            logger.error(f"❌ [{name}] 抓取異常，已跳過: {err_msg[:80]}")
            return []

    def fetch_all(self) -> List[Dict[str, str]]:
        all_news: List[Dict[str, str]] = []
        total = len(SOURCE_CONFIGS)

        logger.info(f"啟動港股量化新聞抓取任務，共計 {total} 個精選源頭。")

        for idx, config in enumerate(SOURCE_CONFIGS, 1):
            source_news = self.fetch_source(config)
            all_news.extend(source_news)

            if idx < total:
                delay = round(random.uniform(3.0, 7.0), 2)
                logger.info(f"[友善延遲] 休眠 {delay} 秒以保護目標伺服器...")
                time.sleep(delay)

        logger.info(f"任務完成！總計自 {total} 個源頭抓取到 {len(all_news)} 則新聞。")
        return all_news
