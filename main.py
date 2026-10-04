import sys
from scrapling import Fetcher

def scrape_stock_news():
    url = "https://finance.yahoo.com/topic/stock-market-news/"
    
    # 初始化 Fetcher
    fetcher = Fetcher()
    
    print(f"[*] 正在獲取最新股市新聞：{url}")
    try:
        page = fetcher.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=25
        )
    except Exception as e:
        print(f"[!] 請求失敗: {e}")
        sys.exit(1)

    # 提取新聞文章節點
    articles = page.css("section article, li.stream-item, div.content")
    news_list = []

    for article in articles:
        # 提取標題與相對/絕對連結
        title_el = article.css("h3::text").first
        link_el = article.css("a::attr(href)").first
        
        if title_el and title_el.text:
            title = title_el.text.strip()
            link = link_el.text.strip() if link_el else ""
            
            # 若為相對路徑則補全網址
            if link.startswith("/"):
                link = f"https://finance.yahoo.com{link}"
                
            if title and not any(item['title'] == title for item in news_list):
                news_list.append({"title": title, "link": link})

    # 若特定容器選擇器未配對成功，啟動備用標題抓取機制
    if not news_list:
        raw_titles = page.css("h3::text").get_all()
        for t in raw_titles:
            clean_title = t.strip()
            if len(clean_title) > 10 and clean_title not in [x['title'] for x in news_list]:
                news_list.append({"title": clean_title, "link": url})

    print(f"\n[+] 成功解析 {len(news_list)} 條即時新聞：\n" + "="*50)
    for idx, item in enumerate(news_list[:10], start=1):
        print(f"{idx}. {item['title']}")
        if item['link'] != url:
            print(f"   連結: {item['link']}")
    print("="*50)

if __name__ == "__main__":
    scrape_stock_news()
