import os
import sys
import json
import time
import random
import requests
from datetime import datetime, timedelta
import pytz
import google.generativeai as genai
from scrapling import Fetcher

# --- 1. 設定香港時區 ---
HKT = pytz.timezone('Asia/Hong_Kong')

# --- 2. 計算當前時段與結束時間 ---
def get_session_window():
    now = datetime.now(HKT)
    hour = now.hour
    minute = now.minute

    # 夜間時段: 23:00 - 02:00 (隔天)
    if hour >= 22 or hour < 2:
        end_time = now.replace(hour=2, minute=0, second=0, microsecond=0)
        if hour >= 22:
            end_time += timedelta(days=1)
        return "夜間 (昨收16:00後至此刻)", end_time

    # 早盤前: 06:00 - 10:00
    elif 5 <= hour < 10:
        end_time = now.replace(hour=10, minute=0, second=0, microsecond=0)
        return "早盤前 (橫跨週末/昨夜至今日開盤)", end_time

    # 盤中: 10:30 - 14:00
    elif (hour == 10 and minute >= 20) or (11 <= hour < 14):
        end_time = now.replace(hour=14, minute=0, second=0, microsecond=0)
        return "盤中 (10:30-14:00)", end_time

    # 若為手動觸發測試，預設運行 60 分鐘
    else:
        return "自訂/測試時段", now + timedelta(minutes=60)


# --- 3. 核心執行邏輯 (爬取 -> AI分析 -> 去重 -> 飛書發送) ---
def execute_single_scrape(time_range_msg):
    now_str = datetime.now(HKT).strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n" + "="*50)
    print(f"⏰ [{now_str} HKT] 開始執行隨機抽樣爬取！")
    print(f"📊 掃描時段範圍：{time_range_msg}")
    print("="*50)

    history_file = "history.json"
    history_records = []
    
    # 讀取歷史紀錄 (包含 URL、股票代號、核心事件)
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history_records = json.load(f)
        except Exception:
            history_records = []
            
    # 提取已經爬過的 URL (避免浪費 AI 算力)
    history_urls = [record.get("url") for record in history_records if "url" in record]

    # 10 個源頭清單 (目前預設 3 個真實源頭，其餘留白供後續填寫)
    sources = [
        {"name": "Yahoo 財經 (港股)", "url": "https://hk.finance.yahoo.com/topic/hk-stock-news/", "item": "li.stream-item", "title": "h3::text", "link": "a::attr(href)"},
        {"name": "AASTOCKS 阿思達克", "url": "http://www.aastocks.com/tc/stocks/news/aafn/latest-news", "item": "div.news-list", "title": "div.news-title::text", "link": "a::attr(href)"},
        {"name": "Sina 新浪港股", "url": "https://finance.sina.com.cn/stock/hkstock/", "item": "ul.list_009 li", "title": "a::text", "link": "a::attr(href)"},
    ]

    # 過濾出有填寫 URL 的源頭，並隨機抽取 3 到 5 個
    valid_sources = [s for s in sources if s["url"]]
    selected_count = min(random.randint(3, 5), len(valid_sources))
    selected_sources = random.sample(valid_sources, selected_count)
    print(f"🎲 本輪隨機抽出來源：{[s['name'] for s in selected_sources]}")

    fetcher = Fetcher()
    raw_news = []

    # 爬取與重試邏輯
    for src in selected_sources:
        success = False
        for attempt in range(1, 4):
            try:
                page = fetcher.get(src["url"], timeout=20)
                items = page.css(src["item"])
                
                # 每個源頭抓最新 15 篇
                for it in items[:15]:
                    t = it.css(src["title"]).get()
                    l = it.css(src["link"]).get()
                    if t and l:
                        t = t.strip()
                        l = l.strip() if l.startswith("http") else src["url"] + l.strip()
                        
                        # 第一層去重：網址是否抓過
                        if l not in history_urls:
                            raw_news.append({"title": t, "link": l, "source": src["name"]})
                            
                success = True
                print(f"  ✅ 成功從 {src['name']} 爬取數據")
                break
            except Exception as e:
                print(f"  ⚠️ {src['name']} 第 {attempt} 次失敗: {e}")
                time.sleep(2)
                
        if not success:
            print(f"  ❌ {src['name']} 重試 3 次皆失敗，已跳過")

    print(f"📥 共抓取到 {len(raw_news)} 條未處理的新新聞")
    if not raw_news:
        print("本輪無新資訊需要處理。")
        return

    # --- 呼叫 Gemini AI 分析與提取事件指紋 ---
    api_key = os.getenv("GEMINI_API_KEY")
    keywords = os.getenv("BULLISH_KEYWORDS", "利好, 增長, 大行唱好")
    
    if not api_key:
        print("⚠️ 尚未設定 GEMINI_API_KEY，略過 AI 分析。")
        return

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})

    ai_prompt = f"""
    你是一個專業的港股分析師。請分析以下 JSON 格式的新聞標題與連結。
    判斷標準：
    1. 必須符合這些「利好關鍵詞」或其語義：{keywords}
    2. 判斷該消息是否屬於「24小時內且未被市場完全消化」的潛在利多。
    3. 如果這批新聞中，有多條(不同來源)報導「同一家公司的同一個利好事件」，請將它們合併為一條，來源可以寫多個。

    請將合格的新聞格式化為以下 JSON 陣列結構返回（若無利好則返回 []）：
    [
      {{
        "title": "新聞標題",
        "stock_code": "對應的港股中文名稱及代號 (如: 匯豐控股 00005.HK，若無特定個股填 '大盤/板塊')",
        "core_event": "提煉該新聞的最核心事件（限10個字以內，例如：發布Q3財報、大行上調目標價、中標重大項目）",
        "publish_time": "發佈時間 (格式 YYYY-MM-DD HH:MM)",
        "source": "來源網站",
        "url": "新聞連結",
        "summary": "1-3句的精煉利好摘要，說明為何看好"
      }}
    ]
    """

    ai_results = []
    # 批次傳送，每次 10 條
    for i in range(0, len(raw_news), 10):
        batch = raw_news[i:i+10]
        try:
            res = model.generate_content(ai_prompt + "\n資料:\n" + json.dumps(batch, ensure_ascii=False))
            batch_result = json.loads(res.text)
            ai_results.extend(batch_result)
        except Exception as e:
            print(f"  ❌ AI 分析出錯: {e}")

    print(f"✨ AI 篩選出 {len(ai_results)} 條利好消息")

    # --- 飛書推送與跨來源事件去重 ---
    webhook = os.getenv("FEISHU_WEBHOOK")
    if not webhook:
        print("⚠️ 尚未設定 FEISHU_WEBHOOK，略過發送。")
        return

    pushed_count = 0
    for item in ai_results:
        stock = item.get('stock_code', '')
        event = item.get('core_event', '')
        
        # 第二層去重：檢查歷史紀錄中，是否已經發送過「同公司」的「同事件」
        is_duplicate_event = any(
            (r.get("stock") == stock and r.get("event") == event) 
            for r in history_records
        )
        
        # 若大盤新聞無法歸類個股，則略過事件去重
        if is_duplicate_event and stock != '大盤/板塊':
            print(f"  ⏭️ 攔截重複事件: {stock} - {event} (已在歷史紀錄中，不重複發送)")
            continue

        msg = {
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"tag": "plain_text", "content": "📈 港股利好速報"}, "template": "green"},
                "elements": [
                    {"tag": "markdown", "content": f"**新聞標題：** {item.get('title')}"},
                    {"tag": "markdown", "content": f"**股票：** {stock}"},
                    {"tag": "markdown", "content": f"**核心事件：** {event}"},
                    {"tag": "markdown", "content": f"**發佈時間：** {item.get('publish_time')}"},
                    {"tag": "markdown", "content": f"**來源：** {item.get('source')}"},
                    {"tag": "markdown", "content": f"**連結：** [點擊查看]({item.get('url')})"},
                    {"tag": "hr"},
                    {"tag": "markdown", "content": f"**利好摘要：**\n{item.get('summary')}"}
                ]
            }
        }
        
        try:
            r = requests.post(webhook, json=msg)
            if r.status_code == 200:
                pushed_count += 1
                history_records.append({
                    "url": item.get('url'),
                    "stock": stock,
                    "event": event,
                    "timestamp": datetime.now(HKT).strftime('%Y-%m-%d %H:%M')
                })
        except Exception as e:
            print(f"  ❌ 飛書發送失敗: {e}")

    print(f"🚀 飛書成功發送 {pushed_count} 條不重複的利好消息")

    # 寫入歷史檔案 (保留最近 500 條紀錄)
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history_records[-500:], f, ensure_ascii=False)


# --- 4. 主循環調度器 (隨機休眠機制) ---
def main():
    session_name, end_time = get_session_window()
    print(f"🌟 啟動時段：【{session_name}】，預計運行至 HKT: {end_time.strftime('%H:%M:%S')}")

    while True:
        now = datetime.now(HKT)
        if now >= end_time:
            print(f"🏁 當前時間 {now.strftime('%H:%M:%S')} 已到達或超過時段結束點，程式平穩退出。")
            break

        # 立即執行一次爬取與分析
        execute_single_scrape(session_name)

        # 檢查爬完後是否已經超時
        now = datetime.now(HKT)
        if now >= end_time:
            break

        # 計算下一次執行的間隔：隨機 22 到 32 分鐘
        sleep_seconds = random.randint(22 * 60, 32 * 60)
        
        # 若下次執行時間會超過時段結束點，調整等待時間或直接結束
        if now + timedelta(seconds=sleep_seconds) > end_time:
            remaining = (end_time - now).total_seconds()
            if remaining > 600: # 如果還剩超過 10 分鐘，休眠到最後一刻再結束
                print(f"💤 本時段即將結束，休眠剩餘 {int(remaining)} 秒至結束...")
                time.sleep(remaining)
            break

        next_run_time = now + timedelta(seconds=sleep_seconds)
        print(f"💤 進入休眠，下一次隨機執行時間為 HKT: {next_run_time.strftime('%H:%M:%S')} (等待約 {sleep_seconds // 60} 分鐘)...")
        time.sleep(sleep_seconds)

if __name__ == "__main__":
    main()
