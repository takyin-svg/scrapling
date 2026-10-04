import os
import pytz

# --- 基礎設定 ---
HKT = pytz.timezone('Asia/Hong_Kong')
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")
HISTORY_FILE = "data/history.json"

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
    "派息", "中標", "突破", "超预", "扭虧", "激勵"
]

# --- 抓取源設定 (【GitHub Actions 美國 IP 專屬白名單】) ---
# 這些網站對海外 IP 極度友善，不會跳轉或封鎖，確保雲端掛機 100% 成功
NEWS_SOURCES = [
    {
        "name": "Yahoo 財經", 
        "url": "https://hk.finance.yahoo.com/", 
        "item": "h3", 
        "title": "a::text", 
        "link": "a::attr(href)"
    },
    {
        "name": "Reuters 路透社", 
        "url": "https://www.reuters.com/markets/asia/", 
        "item": "li.story-collection__story", 
        "title": "a[data-testid='Heading']::text", 
        "link": "a[data-testid='Heading']::attr(href)"
    },
    {
        "name": "Investing.com HK", 
        "url": "https://hk.investing.com/news/stock-market-news", 
        "item": "article", 
        "title": "a.title::text", 
        "link": "a.title::attr(href)"
    },
    {
        "name": "格隆匯 (7x24快訊)", 
        "url": "https://www.gelonghui.com/live", 
        "item": "div.live-item", 
        "title": "div.content::text", 
        "link": "a::attr(href)"
    }
]
