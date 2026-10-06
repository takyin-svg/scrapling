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
    "港股", "恆指", "恒指", "科指", "國指", "騰訊", "阿里", "美團", "匯豐", "平保", 
    "中移動", "大行", "目標價", ".HK", "港交所", "中海油", "比亞迪", "港股通", "新股"
]

# 根據 10 大重磅利好條件擴充的關鍵字庫 (覆蓋繁簡體與常見財經縮寫)
BASIC_BULLISH = [
    # 1. 業績爆發
    "盈喜", "扭虧", "超預期", "增長", "盈利", "淨利", "業績",
    # 2. 機構評級
    "上調", "買入", "看好", "增持評級", "首予",
    # 3. 資金面動作
    "回購", "增持", "大手",
    # 4. 業務突破
    "突破", "獲批", "新藥", "上市", "中標", "訂單", "授權", "BD", "收購", "併購",
    # 5. 政策與出海
    "受惠", "扶持", "補貼", "出海",
    # 6. 資本架構事件
    "分拆", "納入", "剔除", # 剔除通常伴隨納入其他股，可保留作觸發詞交由 AI 判斷
    # 7. 重大基本面
    "重組", "戰略", "激勵",
    # 8. 股息
    "派息", "股息", "特別息",
    # 9. 私有化
    "私有化", "要約",
    # 10. 新股 IPO
    "超購", "超額認購", "暗盤", "IPO",
    # 基礎通用利好字眼
    "升", "漲", "高", "利好", "大升", "飆", "反彈"
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
