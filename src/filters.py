from src.config import HK_KEYWORDS, BASIC_BULLISH

class NewsFilter:
    def __init__(self, state_manager):
        self.state_manager = state_manager

    def apply(self, raw_news: list[dict]) -> list[dict]:
        filtered = []
        for news in raw_news:
            title = news["title"]
            url = news["link"]
            
            # 第一重：URL 去重
            if self.state_manager.is_url_scanned(url):
                continue
            
            # 必須把準備分析的標記為已看過，防止後續重複抓取浪費 AI Token
            self.state_manager.add_record(url=url)
            
            # 第二重：關鍵字初篩 (剔除無關/垃圾新聞)
            is_hk_related = any(kw in title for kw in HK_KEYWORDS)
            has_bullish_hint = any(kw in title for kw in BASIC_BULLISH)
            
            if is_hk_related and has_bullish_hint:
                filtered.append(news)
                
        print(f"🧹 本地初篩過濾完成：從 {len(raw_news)} 條提煉出 {len(filtered)} 條高潛力新聞")
        return filtered
