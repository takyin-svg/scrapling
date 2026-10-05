import re
import time
from urllib.parse import urljoin

from scrapling.fetchers import StealthyFetcher, Fetcher

# ==================== 源配置 ====================

SOURCES = [
    # ---------- 大盤首頁類 (HTML 動態渲染) ----------
    {
        "name": "Yahoo財經(大盤)",
        "url": "https://hk.finance.yahoo.com/",
        "kind": "html",
        "fetcher": "stealth",
        "timeout": 30,
    },
    # ---------- JSON API 類 ----------
    {
        "name": "东方财富港股",
        "url": (
            "https://api.eastmoney.com/dataapi/xinwen/list?"
            "type=100&pageIndex=1&pageSize=50&keyword=%E6%B8%AF%E8%82%A1"
        ),
        "kind": "json",
        "fetcher": "fetcher",
        "timeout": 15,
    },
    # ---------- HTML 類（需瀏覽器渲染） ----------
    {
        "name": "新浪港股",
        "url": "https://finance.sina.com.cn/stock/hkstock/",
        "kind": "html",
        "fetcher": "stealth",
        "timeout": 30,
    },
    {
        "name": "智通财经",
        "url": "https://www.zhitongcaijing.com/",
        "kind": "html",
        "fetcher": "stealth",
        "timeout": 45,
    },
    {
        "name": "格隆汇",
        "url": "https://www.gelonghui.com/",
        "kind": "html",
        "fetcher": "stealth",
        "timeout": 30,
    },
    {
        "name": "金十数据",
        "url": "https://www.jin10.com/",
        "kind": "html",
        "fetcher": "stealth",
        "timeout": 30,
    },
]

# 進程內暫時去重
_seen_urls: set[str] = set()

def _normalize_url(url: str) -> str:
    url = url.strip().rstrip("/")
    for prefix in ("utm_", "ref", "from"):
        url = re.sub(rf"[&?]{prefix}=\w+", "", url)
    return url

def _is_duplicate(url: str) -> bool:
    norm = _normalize_url(url)
    if norm in _seen_urls:
        return True
    _seen_urls.add(norm)
    return False


# ==================== 解析器 ====================

def parse_eastmoney_json(page) -> list[dict]:
    import json
    items = []
    try:
        data = json.loads(page.body)
    except Exception:
        return items

    records = []
    if isinstance(data, dict):
        records = (data.get("data") or {}).get("diff") or []
        if not records:
            records = data.get("result") or data.get("data") or []
            if isinstance(records, dict):
                records = records.get("data") or []

    for rec in records:
        title = rec.get("title") or rec.get("news_title") or ""
        url = rec.get("url") or rec.get("news_url") or rec.get("link") or ""
        pub_date = rec.get("show_time") or rec.get("publish_time") or rec.get("date") or ""
        snippet = rec.get("digest") or rec.get("summary") or ""
        if title and url:
            items.append({
                "title": title,
                "url": url,
                "pub_date": str(pub_date),
                "source": "东方财富",
                "snippet": snippet,
            })
    return items

def _generic_list_parse(
    page, source_name: str,
    card_selector: str = "article, .news-item, .feed-item, .article-item",
    link_selector: str = "a",
    time_selector: str = "time, .time, .date, .publish-time",
) -> list[dict]:
    items = []
    seen_local = set()
    for card in page.css(card_selector):
        a = card.css_first(link_selector)
        if not a:
            continue
        title = (a.text or "").strip()
        href = a.attrib.get("href", "")
        if not title or not href or len(title) < 8:
            continue
        if href in seen_local:
            continue
        seen_local.add(href)

        skip = any(k in href for k in (
            "login", "register", "about", "contact",
            "download", "app", "search", "tag", "javascript:",
        ))
        if skip:
            continue

        pub_date = ""
        t_el = card.css_first(time_selector) if time_selector else None
        if t_el:
            pub_date = (t_el.text or "").strip()

        full_url = urljoin(page.url, href) if not href.startswith("http") else href
        items.append({
            "title": title,
            "url": full_url,
            "pub_date": pub_date,
            "source": source_name,
            "snippet": "",
        })
    return items

def parse_yahoo_hk(page) -> list[dict]:
    """專門解析 Yahoo 香港財經首頁的抓取器"""
    items = []
    seen_local = set()
    # Yahoo 財經首頁的主要新聞標題都放在 h3 裡面的 a 標籤
    for a in page.css("h3 a"):
        title = (a.text or "").strip()
        href = a.attrib.get("href", "")
        if not title or not href or len(title) < 8:
            continue
        if href in seen_local:
            continue
        seen_local.add(href)
        
        # 排除首頁的導覽列與影音連結
        if "/video/" in href or "login" in href:
            continue

        full_url = urljoin(page.url, href) if not href.startswith("http") else href
        items.append({
            "title": title,
            "url": full_url,
            "pub_date": "",
            "source": "Yahoo財經(大盤)",
            "snippet": "",
        })
    
    # 防呆機制：若 h3 抓不到，嘗試用更廣泛的列表抓取
    if not items:
        items = _generic_list_parse(page, "Yahoo財經(大盤)", card_selector="li.js-stream-content", link_selector="a")
    return items

def parse_sina_hk(page) -> list[dict]:
    items = page.css("ul.list li, .newslist li, .blk01 li")
    result = []
    for li in items:
        a = li.css_first("a")
        if not a:
            continue
        title = (a.text or "").strip()
        href = a.attrib.get("href", "")
        if not title or not href or len(title) < 8:
            continue
        time_el = li.css_first("span, em, time")
        pub_date = (time_el.text or "").strip() if time_el else ""
        full_url = urljoin(page.url, href) if not href.startswith("http") else href
        result.append({
            "title": title, "url": full_url,
            "pub_date": pub_date, "source": "新浪港股", "snippet": "",
        })
    if not result:
        result = _generic_list_parse(page, "新浪港股", "ul.list li, .newslist li, .blk01 li")
    return result

def parse_zhitong(page) -> list[dict]:
    return _generic_list_parse(page, "智通财经", card_selector="article, .news-item, .feed-item, .article-item")

def parse_gelonghui(page) -> list[dict]:
    return _generic_list_parse(page, "格隆汇", card_selector="article, .article-item, .news-item, .feed-card, .home-feed-item")

def parse_jin10(page) -> list[dict]:
    return _generic_list_parse(page, "金十数据", card_selector=".jin-flash, .flash-item, .news-flash, .jin10-item, article", link_selector=".title, .content, .text, p, a")


# ==================== 抓取核心 ====================

PARSERS = {
    "Yahoo財經(大盤)": parse_yahoo_hk,  # 對接新的 Yahoo 解析器
    "新浪港股": parse_sina_hk,
    "东方财富港股": parse_eastmoney_json,
    "智通财经": parse_zhitong,
    "格隆汇": parse_gelonghui,
    "金十数据": parse_jin10,
}

def fetch_page(source_cfg: dict, url: str):
    fetcher_type = source_cfg.get("fetcher", "stealth")
    timeout_sec = source_cfg.get("timeout", 30)  # 取得設定的秒數
    max_retries = 2
    name = source_cfg.get("name", "unknown")

    for attempt in range(1, max_retries + 1):
        try:
            if fetcher_type == "fetcher":
                # 一般 HTTP 請求，timeout 單位是秒
                page = Fetcher.get(url, timeout=timeout_sec)
            else:
                # 🚨 Playwright 渲染引擎，timeout 單位必須轉換為毫秒 (* 1000)
                page = StealthyFetcher.fetch(url, headless=True, network_idle=True, timeout=timeout_sec * 1000)
                
            if page and getattr(page, 'status', 200) == 200:
                return page
        except Exception as e:
            print(f"    ⚠️ 第 {attempt} 次失敗: {type(e).__name__}: {str(e)[:150]}")
            if attempt < max_retries:
                time.sleep(2)

    print(f"  ❌ [{name}] 抓取失敗，跳過")
    return None

def fetch_source(source_cfg: dict) -> list[dict]:
    name = source_cfg["name"]
    url = source_cfg["url"]
    kind = source_cfg.get("kind", "html")

    page = fetch_page(source_cfg, url)
    if not page:
        return []

    if kind == "json":
        items = parse_eastmoney_json(page)
    else:
        parser = PARSERS.get(name)
        if not parser:
            print(f"  ⚠️ 找不到 [{name}] 的解析器")
            return []
        items = parser(page)

    print(f"  ✅ [{name}] 成功抓取 {len(items)} 條")
    return items

def run_scraper() -> list[dict]:
    all_raw: list[dict] = []
    _seen_urls.clear()  # 確保每次排程啟動時清空本輪紀錄
    
    for src in SOURCES:
        items = fetch_source(src)
        for item in items:
            url = item.get("url", "")
            if url and not _is_duplicate(url):
                all_raw.append(item)
            elif not url:
                all_raw.append(item)

    print(f"📥 總計：全網共抓取到 {len(all_raw)} 條未處理原始資訊")
    return all_raw


# ==================== V2.0 系統整合介面 ====================

class HKStockScraper:
    def fetch_all(self) -> list[dict]:
        """
        對接 V2.0 Orchestrator 的標準接口。
        將多源爬蟲資料格式化為系統預期的結構。
        """
        raw_news = run_scraper()
        
        formatted_news = []
        for item in raw_news:
            formatted_news.append({
                "title": item.get("title", ""),
                "link": item.get("url", ""),     # V2.0 的 filters 預期欄位是 link
                "source": item.get("source", "")
            })
            
        return formatted_news
