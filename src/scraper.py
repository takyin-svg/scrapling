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
                    page = self.fetcher.get(src["url"]) 
                    items = page.css(src["item"])
                    
                    extracted_count = 0
                    for it in items[:30]:
                        title_els = it.css(src["title"])
                        link_els = it.css(src["link"])
                        
                        # 正確使用 Python 物件來提取文字
                        t = title_els[0].text if title_els else it.text
                        
                        # 正確提取超連結屬性
                        l = ""
                        if link_els and hasattr(link_els[0], 'attrib') and 'href' in link_els[0].attrib:
                            l = link_els[0].attrib['href']
                        elif hasattr(it, 'attrib') and 'href' in it.attrib:
                            l = it.attrib['href']
                        
                        if t and t.strip():
                            t = t.strip()
                            l = l.strip() if l and l.startswith("http") else src["url"].rstrip('/') + '/' + (l.strip().lstrip('/') if l else '')
                            raw_news.append({"title": t, "link": l, "source": src["name"]})
                            extracted_count += 1
                                
                    if extracted_count > 0:
                        success = True
                        print(f"  ✅ 成功從 [{src['name']}] 抓取 {extracted_count} 條資訊")
                        break
                    else:
                        # 終極偵錯：印出網頁真實 HTML，看是不是遇到 Cloudflare 驗證碼
                        preview = page.text[:150].replace('\n', ' ') if hasattr(page, 'text') else "無內容"
                        raise Exception(f"未匹配到新聞。HTML預覽: {preview}")

                except Exception as e:
                    print(f"  ⚠️ [{src['name']}] 第 {attempt} 次抓取失敗: {str(e)[:120]}")
                    time.sleep(2)
                    
            if not success:
                print(f"  ❌ [{src['name']}] 重試 3 次皆失敗，已自動跳過")
                
        print(f"📥 總計：全網共抓取到 {len(raw_news)} 條原始資訊")
        return raw_news
