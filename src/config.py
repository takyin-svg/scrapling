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
    "派息", "中標", "突破", "超預期", "扭虧", "激勵"
]

# --- 抓取源設定 (純淨版 CSS 選擇器) ---
NEWS_SOURCES = [
    {"name": "Yahoo 財經", "url": "https://hk.finance.yahoo.com/", "item": "h3", "title": "a", "link": "a"},
    {"name": "Sina 新浪港股", "url": "https://finance.sina.com.cn/stock/hkstock/", "item": "ul.list_009 li", "title": "a", "link": "a"},
    {"name": "東方財富港股", "url": "https://finance.eastmoney.com/a/chgsh.html", "item": "div.newsList ul li", "title": "a", "link": "a"},
    {"name": "21世紀經濟報道", "url": "https://www.21jingji.com/", "item": "div.news_list li", "title": "a", "link": "a"},
    {"name": "金吾財訊", "url": "https://www.jwview.com/", "item": "div.news-item", "title": "a.title", "link": "a.title"},
    {"name": "Reuters 路透社", "url": "https://www.reuters.com/markets/asia/", "item": "li.story-collection__story", "title": "a[data-testid='Heading']", "link": "a[data-testid='Heading']"},
    {"name": "RTHK 財經", "url": "https://news.rthk.hk/rthk/ch/finance", "item": "div.ns2-inner", "title": "div.ns2-title a", "link": "div.ns2-title a"}
]
