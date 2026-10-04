import random
import time
from scrapling import StealthyFetcher  # 👈 召喚 Scrapling 專治 JS 的隱形戰車！
from src.config import NEWS_SOURCES

class HKStockScraper:
    def fetch_all(self) -> list[dict]:
        valid_sources = [s for s in NEWS_SOURCES if s["url"]]
        selected_sources = random.sample(valid_sources, min(random.randint(3, 5), len(valid_sources)))
        print(f"🎲 本輪隨機抽取抓取源：{[s['name'] for s in selected_sources]}")

        raw_news = []
        
        # 使用 StealthyFetcher 啟動內建的無頭瀏覽器，它能自動渲染 JS 並維持極高的反爬偽裝！
        with StealthyFetcher(headless=True) as fetcher:
            for src in selected_sources:
                success = False
                for attempt in range(1, 4):
                    try:
                        # 讓 Scrapling 去抓取並渲染網頁
                        page = fetcher.get(src["url"])
                        
                        # 稍微等 2 秒，確保所有 Ajax 新聞列表都載入完畢
                        time.sleep(2)
                        
                        items = page.css(src["item"])
                        
                        if not items:
                            raise Exception("JS 渲染後仍找不到新聞區塊 (可能網頁改版)")
                        
                        extracted_count = 0
                        for it in items[:30]:
                            title_els = it.css(src["title"])
                            link_els = it.css(src["link"])
                            
                            # 使用 Scrapling 原生的節點屬性提取法 (避免 ::text 相容性問題)
                            t = title_els[0].text if title_els else it.text
                            
                            l = ""
                            if link_els and 'href' in link_els[0].attrib:
                                l = link_els[0].attrib['href']
                            elif 'href' in it.attrib:
                                l = it.attrib['href']
                            
                            l = l or src["url"]
                            
                            if t and t.strip():
                                t = t.strip()
                                l = l.strip() if l.startswith("http") else src["url"].rstrip('/') + '/' + l.strip().lstrip('/')
                                raw_news.append({"title": t, "link": l, "source": src["name"]})
                                extracted_count += 1
                                    
                        success = True
                        print(f"  ✅ 成功從 [{src['name']}] 抓取 {extracted_count} 條資訊")
                        break
                    except Exception as e:
                        print(f"  ⚠️ [{src['name']}] 第 {attempt} 次抓取失敗: {str(e)[:40]}")
                        time.sleep(2)
                        
                if not success:
                    print(f"  ❌ [{src['name']}] 重試 3 次皆失敗，已自動跳過")
                    
        print(f"📥 總計：全網共抓取到 {len(raw_news)} 條原始資訊")
        return raw_news
