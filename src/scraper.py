import random
import time
from scrapling import Fetcher
from src.config import NEWS_SOURCES

class HKStockScraper:
    def __init__(self):
        # 【破甲升級】：注入香港語系與本地 Referer，降低美國 IP 被秒殺的機率
        self.headers = {
            "Accept-Language": "zh-HK,zh-TW;q=0.9,zh-CN;q=0.8,zh;q=0.7,en-US;q=0.6",
            "Referer": "https://www.google.com.hk/"
        }
        self.fetcher = Fetcher(impersonate="chrome", headers=self.headers)

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
                        t = it.css(src["title"]).get()
                        l = it.css(src["link"]).get()
                        
                        if t and str(t).strip():
                            t = str(t).strip()
                            l = str(l).strip() if l and str(l).startswith("http") else src["url"].rstrip('/') + '/' + str(l).strip().lstrip('/')
                            raw_news.append({"title": t, "link": l, "source": src["name"]})
                            extracted_count += 1
                                
                    if extracted_count > 0:
                        success = True
                        print(f"  ✅ 成功從 [{src['name']}] 抓取 {extracted_count} 條資訊")
                        break
                    else:
                        # 🚨 網頁標題探測器：看穿美國 IP 到底收到了什麼畫面
                        page_title = page.css("title::text").get() or "無標題 (可能被強制阻斷)"
                        raise Exception(f"未找到新聞區塊。網頁標題顯示為: 【{page_title}】 (高度疑似 GitHub 美國 IP 遭封鎖)")

                except Exception as e:
                    print(f"  ⚠️ [{src['name']}] 第 {attempt} 次抓取失敗: {str(e)[:150]}")
                    time.sleep(2)
                    
            if not success:
                print(f"  ❌ [{src['name']}] 重試 3 次皆失敗，已自動跳過")
                
        print(f"📥 總計：全網共抓取到 {len(raw_news)} 條原始資訊")
        return raw_news
