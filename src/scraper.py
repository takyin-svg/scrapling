import random
import time
from scrapling import Fetcher
from src.config import NEWS_SOURCES

class HKStockScraper:
    def __init__(self):
        # 找回你早上測試成功的輕量級引擎！速度極快且自帶反爬偽裝
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
                    
                    extracted_count = 0
                    for it in items[:30]:
                        # 完全採用你早上測試成功的選擇器邏輯
                        t = it.css(src["title"]).get() or it.text
                        l = it.css(src["link"]).get() or src["url"]
                        
                        if t:
                            t = t.strip()
                            l = l.strip() if l.startswith("http") else src["url"].rstrip('/') + '/' + l.strip().lstrip('/')
                            raw_news.append({"title": t, "link": l, "source": src["name"]})
                            extracted_count += 1
                                
                    if extracted_count > 0:
                        success = True
                        print(f"  ✅ 成功從 [{src['name']}] 抓取 {extracted_count} 條資訊")
                        break
                    else:
                        raise Exception("成功連線，但未解析到新聞 (可能遇到JS動態渲染或選擇器失效)")

                except Exception as e:
                    print(f"  ⚠️ [{src['name']}] 第 {attempt} 次抓取失敗: {str(e)[:40]}")
                    time.sleep(2)
                    
            if not success:
                print(f"  ❌ [{src['name']}] 重試 3 次皆失敗，已自動跳過")
                
        print(f"📥 總計：全網共抓取到 {len(raw_news)} 條原始資訊")
        return raw_news
