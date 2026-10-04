import os
import sys
import json
import time
import random
import requests
from datetime import datetime, timedelta
import pytz

from google import genai
from google.genai import types
from scrapling import Fetcher

# --- 1. 設定香港時區 ---
HKT = pytz.timezone('Asia/Hong_Kong')

# --- 2. 計算當前時段與結束時間 ---
def get_session_window():
    now = datetime.now(HKT)
    hour = now.hour
    minute = now.minute

    if hour >= 22 or hour < 2:
        end_time = now.replace(hour=2, minute=0, second=0, microsecond=0)
        if hour >= 22: end_time += timedelta(days=1)
        return "夜間 (昨收16:00後至此刻)", end_time
    elif 5 <= hour < 10:
        end_time = now.replace(hour=10, minute=0, second=0, microsecond=0)
        return "早盤前 (橫跨週末/昨夜至今日開盤)", end_time
    elif (hour == 10 and minute >= 20) or (11 <= hour < 14):
        end_time = now.replace(hour=14, minute=0, second=0, microsecond=0)
        return "盤中 (10:30-14:00)", end_time
    else:
        return "自訂/測試時段", now + timedelta(minutes=60)


# --- 3. 核心執行邏輯 ---
def execute_single_scrape(time_range_msg):
    now_str = datetime.now(HKT).strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n" + "="*50)
    print(f"⏰ [{now_str} HKT] 開始執行隨機抽樣爬取！")
    print(f"📊 掃描時段範圍：{time_range_msg}")
    print("="*50)

    history_file = "history.json"
    history_records = []
    
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history_records = json.load(f)
        except Exception:
            history_records = []
            
    history_urls = [record.get("url") for record in history_records if "url" in record]

    # --- 【修改點 1】更新 10 大財經新聞源，修復 404 失效網址 ---
    sources = [
        {"name": "Yahoo 財經", "url": "https://hk.finance.yahoo.com/", "item": "h3", "title": "a::text", "link": "a::attr(href)"}, # 改抓首頁新聞模塊
        {"name": "Sina 新浪港股", "url": "https://finance.sina.com.cn/stock/hkstock/", "item": "ul.list_009 li", "title": "a::text", "link": "a::attr(href)"},
        {"name": "智通財經", "url": "https://www.zhitongcaijing.com/hknews.html", "item": "div.news-list-item", "title": "h2.title::text", "link": "a::attr(href)"},
        {"name": "格隆匯", "url": "https://www.gelonghui.com/live", "item": "div.live-item", "title": "div.content::text", "link": "a::attr(href)"}, # 強制 HTTPS
        {"name": "東方財富港股", "url": "https://finance.eastmoney.com/a/chgsh.html", "item": "div.newsList ul li", "title": "a::text", "link": "a::attr(href)"}, # 更新為有效的港股路由
        {"name": "財聯社", "url": "https://www.cls.cn/telegraph", "item": "div.telegraph-list", "title": "span.telegraph-content::text", "link": "a::attr(href)"},
        {"name": "金十數據", "url": "https://www.jin10.com/", "item": "div.jin10-news-item", "title": "div.jin10-news-text::text", "link": "a::attr(href)"},
        {"name": "21世紀經濟報道", "url": "https://www.21jingji.com/", "item": "div.news_list li", "title": "a::text", "link": "a::attr(href)"},
        {"name": "金吾財訊", "url": "https://www.jwview.com/", "item": "div.news-item", "title": "a.title::text", "link": "a.title::attr(href)"},
        {"name": "Reuters 路透社", "url": "https://www.reuters.com/markets/asia/", "item": "li.story-collection__story", "title": "a[data-testid='Heading']::text", "link": "a[data-testid='Heading']::attr(href)"}
    ]

    valid_sources = [s for s in sources if s["url"]]
    selected_count = min(random.randint(3, 5), len(valid_sources))
    selected_sources = random.sample(valid_sources, selected_count)
    print(f"🎲 本輪隨機抽出來源：{[s['name'] for s in selected_sources]}")

    # --- 【修改點 2】啟用 Chrome 指紋偽裝，解決 400/401 反爬蟲，並修正 Timeout 語法 ---
    fetcher = Fetcher(impersonate="chrome")
    fetcher.configure(timeout=25) 
    
    raw_news = []

    for src in selected_sources:
        success = False
        for attempt in range(1, 4):
            try:
                # 這裡去掉了已棄用的 timeout=20，交由 configure 統一管理
                page = fetcher.get(src["url"]) 
                items = page.css(src["item"])
                
                for it in items[:15]:
                    # 有些網址的標題不在 a 標籤內，做個防呆備援
                    t = it.css(src["title"]).get() or it.text
                    l = it.css(src["link"]).get() or src["url"]
                    
                    if t:
                        t = t.strip()
                        l = l.strip() if l.startswith("http") else src["url"].rstrip('/') + '/' + l.strip().lstrip('/')
                        
                        if l not in history_urls or l == src["url"]: 
                            raw_news.append({"title": t, "link": l, "source": src["name"]})
                            
                success = True
                print(f"  ✅ 成功從 {src['name']} 爬取數據")
                break
            except Exception as e:
                print(f"  ⚠️ {src['name']} 第 {attempt} 次失敗: {e}")
                time.sleep(2)
                
        if not success:
            print(f"  ❌ {src['name']} 重試 3 次皆失敗，已跳過")

    print(f"📥 共抓取到 {len(raw_news)} 條未處理的潛在新資訊")
    if not raw_news:
        print("本輪無新資訊需要處理。")
        return

    # --- 呼叫 Gemini 2.5 Flash AI 分析 ---
    api_key = os.getenv("GEMINI_API_KEY")
    keywords = os.getenv("BULLISH_KEYWORDS", "利好, 增長, 大行唱好")
    
    if not api_key:
        print("⚠️ 尚未設定 GEMINI_API_KEY，略過 AI 分析。")
        return

    client = genai.Client(api_key=api_key)

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
    for i in range(0, len(raw_news), 10):
        batch = raw_news[i:i+10]
        try:
            res = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=ai_prompt + "\n資料:\n" + json.dumps(batch, ensure_ascii=False),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                )
            )
            batch_result = json.loads(res.text)
            ai_results.extend(batch_result)
        except Exception as e:
            print(f"  ❌ AI 分析出錯: {e}")

    print(f"✨ AI (Gemini 2.5 Flash) 篩選出 {len(ai_results)} 條利好消息")

    # --- 飛書推送與跨來源事件去重 ---
    webhook = os.getenv("FEISHU_WEBHOOK")
    if not webhook:
        print("⚠ 尚未設定 FEISHU_WEBHOOK，略過發送。")
        return

    pushed_count = 0
    for item in ai_results:
        stock = item.get('stock_code', '')
        event = item.get('core_event', '')
        
        is_duplicate_event = any(
            (r.get("stock") == stock and r.get("event") == event) 
            for r in history_records
        )
        
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

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history_records[-500:], f, ensure_ascii=False)

def main():
    session_name, end_time = get_session_window()
    print(f"🌟 啟動時段：【{session_name}】，預計運行至 HKT: {end_time.strftime('%H:%M:%S')}")

    while True:
        now = datetime.now(HKT)
        if now >= end_time:
            print(f"🏁 當前時間 {now.strftime('%H:%M:%S')} 已到達或超過時段結束點，程式平穩退出。")
            break

        execute_single_scrape(session_name)

        now = datetime.now(HKT)
        if now >= end_time:
            break

        sleep_seconds = random.randint(22 * 60, 32 * 60)
        
        if now + timedelta(seconds=sleep_seconds) > end_time:
            remaining = (end_time - now).total_seconds()
            if remaining > 600:
                print(f"💤 本時段即將結束，休眠剩餘 {int(remaining)} 秒至結束...")
                time.sleep(remaining)
            break

        next_run_time = now + timedelta(seconds=sleep_seconds)
        print(f"💤 進入休眠，下一次隨機執行時間為 HKT: {next_run_time.strftime('%H:%M:%S')} (等待約 {sleep_seconds // 60} 分鐘)...")
        time.sleep(sleep_seconds)

if __name__ == "__main__":
    main()
