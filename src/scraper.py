import random
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from src.config import NEWS_SOURCES

class HKStockScraper:
    def fetch_all(self) -> list[dict]:
        valid_sources = [s for s in NEWS_SOURCES if s["url"]]
        selected_sources = random.sample(valid_sources, min(random.randint(3, 5), len(valid_sources)))
        print(f"🎲 本輪隨機抽取抓取源：{[s['name'] for s in selected_sources]}")

        raw_news = []
        
        # 啟動微軟最強無頭瀏覽器 Playwright，完美降維打擊所有 JS 動態網頁
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # 偽裝成真實 Mac 用戶，並設定螢幕尺寸
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()

            for src in selected_sources:
                success = False
                for attempt in range(1, 4):
                    try:
                        # 訪問網頁，wait_until="networkidle" 確保所有 JS 數據都加載完畢才放行
                        page.goto(src["url"], wait_until="networkidle", timeout=30000)
                        
                        # 額外等待 2 秒，對付有延遲加載 (Lazy Load) 的網站
                        page.wait_for_timeout(2000)
                        
                        # 取出經過 JS 渲染後的「完整 HTML」
                        html_content = page.content()
                        
                        # 交給老牌且最穩定的 BeautifulSoup 解析
                        soup = BeautifulSoup(html_content, "html.parser")
                        items = soup.select(src["item"])
                        
                        if not items:
                            raise Exception("JS 渲染後仍找不到區塊 (可能網頁改版或擋IP)")
                        
                        extracted_count = 0
                        for it in items[:30]:
                            title_els = it.select(src["title"])
                            link_els = it.select(src["link"])
                            
                            # 提取純文字並清除空白
                            t = title_els[0].get_text(strip=True) if title_els else it.get_text(strip=True)
                            
                            # 提取網址
                            l = ""
                            if link_els and link_els[0].has_attr('href'):
                                l = link_els[0]['href']
                            elif it.has_attr('href'):
                                l = it['href']
                            
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
            
            # 關閉瀏覽器釋放資源
            browser.close()
            
        print(f"📥 總計：全網共抓取到 {len(raw_news)} 條原始資訊")
        return raw_news
