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

# --- 本地初篩過濾器 (Zero-Cost Filter) ---
HK_KEYWORDS = [
    "港股", "恆指", "科指", "騰訊", "阿里", "美團", "匯豐", "平保", 
    "中移動", "大行", "目標價", ".HK", "港交所", "中海油", "比亞迪"
]
BASIC_BULLISH = [
    "升", "漲", "高", "盈", "利", "好", "增", "回購", 
    "派息", "中標", "突破", "超預期", "扭虧", "激勵"
]

# --- 抓取源設定 (【修復重點】：移除 ::text 和 ::attr，改為純淨 CSS 標籤) ---
NEWS_SOURCES = [
    {"name": "Yahoo 財經", "url": "https://hk.finance.yahoo.com/", "item": "h3", "title": "a", "link": "a"},
    {"name": "Sina 新浪港股", "url": "https://finance.sina.com.cn/stock/hkstock/", "item": "ul.list_009 li", "title": "a", "link": "a"},
    {"name": "智通財經", "url": "https://www.zhitongcaijing.com/hknews.html", "item": "div.news-list-item", "title": "h2.title", "link": "a"},
    {"name": "格隆匯", "url": "https://www.gelonghui.com/live", "item": "div.live-item", "title": "div.content", "link": "a"},
    {"name": "東方財富港股", "url": "https://finance.eastmoney.com/a/chgsh.html", "item": "div.newsList ul li", "title": "a", "link": "a"},
    {"name": "財聯社", "url": "https://www.cls.cn/telegraph", "item": "div.telegraph-list", "title": "span.telegraph-content", "link": "a"},
    {"name": "金十數據", "url": "https://www.jin10.com/", "item": "div.jin10-news-item", "title": "div.jin10-news-text", "link": "a"},
    {"name": "Reuters 路透社", "url": "https://www.reuters.com/markets/asia/", "item": "li.story-collection__story", "title": "a[data-testid='Heading']", "link": "a[data-testid='Heading']"}
]
