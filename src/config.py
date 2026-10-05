import os
import pytz

# --- 基礎設定 ---
HKT = pytz.timezone('Asia/Hong_Kong')
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")
HISTORY_FILE = "data/history.json"

# --- AI 模型設定 ---
# 🚨 記得配合修改 analyzer.py 使用這個新變數，解決 404 錯誤
AI_MODEL = "gemini-3.8-flash"

# --- AI 與推送門檻 ---
MIN_SCORE = 85           
MIN_CONFIDENCE = 70      

# --- 本地初篩過濾器 ---
HK_KEYWORDS = [
    "港股", "恆指", "科指", "騰訊", "阿里", "美團", "匯豐", "平保", 
    "中移動", "大行", "目標價", ".HK", "港交所", "中海油", "比亞迪"
]
BASIC_BULLISH = [
    "升", "漲", "高", "盈", "利", "好", "增", "回購", 
    "派息", "中標", "突破", "超預期", "扭虧", "激勵"
]

# ==================== 抓取源設定 (專屬解析器對接版) ====================

# Yahoo RSS 監聽的股票池
YAHOO_STOCKS = [
    "0700.HK", "1810.HK", "1211.HK", "0388.HK", "0005.HK", "3690.HK", "%5EHSI"
]

# 這裡的格式完全對齊你 scraper.py 的邏輯 (包含 kind, fetcher, timeout)
NEWS_SOURCES = [
    # ---------- RSS 類 ----------
    {
        "name": "Yahoo财经",
        "kind": "yahoo_rss",
        "stocks": YAHOO_STOCKS,
        "fetcher": "fetcher",
        "timeout": 15,
    },
    # ---------- JSON API 類 ----------
    {
        "name": "东方财富港股",
        "url": "https://api.eastmoney.com/dataapi/xinwen/list?type=100&pageIndex=1&pageSize=50&keyword=%E6%B8%AF%E8%82%A1",
        "kind": "json",
        "fetcher": "fetcher",
        "timeout": 15,
    },
    # ---------- HTML 類 (使用 StealthyFetcher 渲染) ----------
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
