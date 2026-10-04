import random
import time
from scrapling import Fetcher
from src.config import NEWS_SOURCES

class HKStockScraper:
    def __init__(self):
        self.fetcher = Fetcher(impersonate="chrome")

    def fetch_all(self) -> list[dict]:
        valid_sources = [s for s in NEWS_SOURCES if s["url"]]
        selected_sources = random.sample(valid_sources, min(random.randint(3, 5), len(valid_sources)))
        print(f"🎲 本輪隨機抽取抓取源：{[s['name'] for s in selected_sources]}")

        raw_news = []
        for src in selected_sources:
            success = False
            for attempt in range(1, 4):
                try:
                    # 獲取網頁
                    page = self.fetcher.get(src["url"]) 
                    items = page.css(src["item"])
                    
                    extracted_count = 0
                    for it in items[:30]:
                        t = it.css(src["title"]).get() or getattr(it, 'text', '')
                        l = it.css(src["link"]).get() or src["url"]
                        
                        if t:
                            t = str(t).strip()
                            l = str(l).strip() if l and str(l).startswith("http") else src["url"].rstrip('/') + '/' + str(l).strip().lstrip('/')
                            raw_news.append({"title": t, "link": l, "source": src["name"]})
                            extracted_count += 1
                                
                    if extracted_count > 0:
                        success = True
                        print(f"  ✅ 成功從 [{src['name']}] 抓取 {extracted_count} 條資訊")
                        break
                    else:
                        # 🚨 終極偵錯核心：印出 HTTP 狀態碼與網頁真實 HTML 前 200 字
                        status = page.status_code if hasattr(page, 'status_code') else 'Unknown'
                        preview = page.text[:200].replace('\n', ' ') if hasattr(page, 'text') else "無內容"
                        raise Exception(f"HTTP {status} | HTML預覽: {preview}")

                except Exception as e:
                    # 把錯誤訊息印長一點，讓我們看清楚 HTML
                    print(f"  ⚠️ [{src['name']}] 第 {attempt} 次抓取失敗: {str(e)[:250]}")
                    time.sleep(2)
                    
            if not success:
                print(f"  ❌ [{src['name']}] 重試 3 次皆失敗，已自動跳過")
                
        print(f"📥 總計：全網共抓取到 {len(raw_news)} 條原始資訊")
        return raw_news
