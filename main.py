from scrapling import Fetcher

def run():
    url = "https://finance.yahoo.com/topic/stock-market-news/"
    fetcher = Fetcher()
    page = fetcher.get(url)

    # 抓取新聞標題
    titles = page.css("h3::text").get_all()
    print(f"--- 今日股票新聞共 {len(titles)} 則 ---")
    for t in titles[:8]:
        if t.strip():
            print(f"• {t.strip()}")

if __name__ == "__main__":
    run()
