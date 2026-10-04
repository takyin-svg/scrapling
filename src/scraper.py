import random
import time
from scrapling import Fetcher
from src.config import NEWS_SOURCES

class HKStockScraper:
    def __init__(self):
        # 底層套用 Chrome 指紋，突破 WAF 防火牆
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
                    page = self.fetcher.get(src["url"]) 
                    items = page.css(src["item"])
                    
                    # 擴大至前 30 條，防止被美股/宏觀新聞洗版
                    for it in items[:30]:
                        t = it.css(src["title"]).get() or it.text
                        l = it.css(src["link"]).get() or src["url"]
                        if t:
                            t = t.strip()
                            l = l.strip() if l.startswith("http") else src["url"].rstrip('/') + '/' + l.strip().lstrip('/')
                            raw_news.append({"title": t, "link": l, "source": src["name"]})
                                
                    success = True
                    print(f"  ✅ 成功從 [{src['name']}] 爬取數據")
                    break
                except Exception as e:
                    print(f"  ⚠️ [{src['name']}] 第 {attempt} 次抓取失敗")
                    time.sleep(2)
                    
            if not success:
                print(f"  ❌ [{src['name']}] 重試 3 次皆失敗，已自動跳過")
                
        print(f"📥 總計：共抓取到 {len(raw_news)} 條原始資訊")
        return raw_news
