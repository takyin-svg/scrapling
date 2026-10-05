import json
import re
import time
from urllib.parse import urljoin

from scrapling.fetchers import Fetcher, StealthyFetcher

# ==================== 源配置 ====================
SOURCES = [
    {
        "name": "Yahoo財經(大盤)",
        "url": "https://hk.finance.yahoo.com/",
        "fetcher": "stealth",
        "timeout_sec": 30,
    },
    {
        "name": "东方财富",
        "url": (
            "https://api.eastmoney.com/dataapi/xinwen/list?"
            "type=100&pageIndex=1&pageSize=50&keyword=%E6%B8%AF%E8%82%A1"
        ),
        "fetcher": "fetcher",  # 東財維持純 HTTP，若被擋則自動優雅跳過
        "timeout_sec": 15,
    },
    {
        "name": "新浪港股",
        "url": "https://finance.sina.com.cn/stock/hkstock/",
        "fetcher": "stealth",
        "timeout_sec": 45,
    },
    {
        "name": "智通財經",
        "url": "https://www.zhitongcaijing.com/",
        "fetcher": "stealth",
        "timeout_sec": 60,
    },
    {
        "name": "格隆匯",
        "url": "https://www.gelonghui.com/",
        "fetcher": "stealth",
        "timeout_sec": 45,
    },
    {
        "name": "金十數據",
        "url": "https://www.jin10.com/",
        "fetcher": "stealth",
        "timeout_sec": 45,
    }
]

# ==================== 防禦式工具 ====================
def get_status(page):
    return getattr(page, "status", None)

def get_body(page):
    b = getattr(page, "body", b"")
    if isinstance(b, bytes):
        return b.decode("utf-8", "ignore")
    return b or ""

def get_page_url(page):
    return getattr(page, "url", "") or ""

def all_css(el, sel):
    try:
        return list(el.css(sel))
    except Exception:
        return []

def text_of(el):
    if el is None:
        return ""
    try:
        return (el.text or "").strip()
    except Exception:
        return ""

def href_of(el):
    if el is None:
        return ""
    try:
        return (el.attrib.get("href", "") or "").strip()
    except Exception:
        return ""

# ==================== 解析器 ====================
def parse_eastmoney(page):
    items = []
    body = get_body(page).strip()
    if not body:
        return items
    
    # 防禦 WAF 阻擋：如果回傳的是 HTML(CSS) 而不是 JSON，直接放棄
    if not (body.startswith("{") or body.startswith("[")):
        m = re.search(r"\{.*\}", body, re.DOTALL)
        body = m.group(0) if m else body
    
    try:
        data = json.loads(body)
    except Exception:
        return items

    records = (
        (data.get("data") or {}).get("diff")
        or data.get("result")
        or data.get("data")
        or []
    )
    if isinstance(records, dict):
        records = records.get("data") or []

    for r in records:
        t = r.get("title") or r.get("news_title") or ""
        u = r.get("url") or r.get("news_url") or r.get("link") or ""
        if t and u:
            items.append({
                "title": t,
                "link": u,
                "source": "东方财富"
            })
    return items

def parse_by_href(page, name, *href_substrings, clean_prefix=False):
    items, seen = [], set()
    page_url = get_page_url(page)
    
    for a in all_css(page, "a"):
        href = href_of(a)
        # 若有指定特徵字串，則必須包含
        if href_substrings and not any(s in href for s in href_substrings):
            continue
            
        t = text_of(a)
        if not t or len(t) < 8:
            continue
        if href in seen:
            continue
        seen.add(href)
        
        if clean_prefix:
            t = re.sub(r"^\s*格隆汇\d+月\d+日[|｜:：]\s*", "", t)
            
        full = urljoin(page_url, href) if not href.startswith("http") else href
        items.append({
            "title": t,
            "link": full,
            "source": name
        })
    return items

def parse_yahoo(page):
    """專門解析 Yahoo 大盤首頁新聞"""
    items, seen = [], set()
    page_url = get_page_url(page)
    
    # Yahoo 財經首頁核心新聞通常在 h3 標籤內
    for a in all_css(page, "h3 a"):
        href = href_of(a)
        t = text_of(a)
        if not t or not href or len(t) < 8:
            continue
        if "/video/" in href or "login" in href:
            continue
        if href in seen:
            continue
        seen.add(href)
        
        full = urljoin(page_url, href) if not href.startswith("http") else href
        items.append({
            "title": t,
            "link": full,
            "source": "Yahoo財經(大盤)"
        })
    return items

def parse_sina(page):
    items = parse_by_href(page, "新浪港股", "sina.com.cn", "/hkstock", "/doc-")
    if not items:
        items = parse_by_href(page, "新浪港股", "finance.sina.com.cn")
    return items


# ==================== 抓取核心 ====================
def fetch_page(cfg):
    url = cfg["url"]
    timeout_sec = cfg.get("timeout_sec", 30)
    fetcher_type = cfg.get("fetcher", "stealth")
    name = cfg.get("name", "unknown")

    for attempt in (1, 2):
        try:
            if fetcher_type == "fetcher":
                page = Fetcher.get(url, timeout=timeout_sec)
            else:
                page = StealthyFetcher.fetch(
                    url,
                    headless=True,
                    network_idle=True,
                    timeout=timeout_sec * 1000,
                )
            if page and get_status(page) == 200:
                return page
            print(f"    ⚠️️ [{name}] 非200: status={get_status(page)}")
        except Exception as e:
            print(f"    ⚠️ [{name}] 第{attempt}次失敗: {type(e).__name__} ({str(e)[:50]})")
            if attempt < 2:
                time.sleep(2)
    return None

def run_scraper() -> list[dict]:
    total = []

    for src in SOURCES:
        name = src["name"]
        page = fetch_page(src)
        if not page:
            continue

        if name == "东方财富":
            items = parse_eastmoney(page)
        elif name == "Yahoo財經(大盤)":
            items = parse_yahoo(page)
        elif name == "新浪港股":
            items = parse_sina(page)
        elif name == "智通財經":
            items = parse_by_href(page, "智通財經", "/content/detail/")
        elif name == "格隆匯":
            items = parse_by_href(page, "格隆匯", "/live/", "/p/", clean_prefix=True)
        elif name == "金十數據":
            items = parse_by_href(page, "金十數據", "/flash/", "/detail/", "jin10.com/flash")
        else:
            items = []

        print(f"  ✅ [{name}] 成功抓取 {len(items)} 條")
        total.extend(items)

    print(f"📥 總計：全網共抓取到 {len(total)} 條原始資訊")
    return total

# ==================== V2.0 系統整合介面 ====================
class HKStockScraper:
    def fetch_all(self) -> list[dict]:
        """
        對接 V2.0 Orchestrator 的標準接口。
        """
        return run_scraper()
