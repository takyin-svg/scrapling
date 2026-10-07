def push(self, payload: dict):
        push_time = payload.get("push_time")
        news_list = payload.get("news_list", [])
        
        if not news_list:
            return

        # 組合所有新聞內容為一個大型文本 (Markdown 格式)
        combined_text = f"⏰ **推送時間 (HKT):** {push_time}\n"
        combined_text += f"📊 **本次共捕獲 {len(news_list)} 條重磅訊號**\n\n"
        
        for idx, news in enumerate(news_list, 1):
            stock_code = news.get('stock_code', '無')
            stock_name = news.get('stock_name', '無')
            score = news.get('score', 0)
            
            # 獲取新聞發布時間 (相容各種爬蟲可能的 key 命名)
            publish_time = news.get('time', news.get('publish_time', news.get('pubDate', '未知時間')))
            
            combined_text += f"**【{idx}】{stock_name} ({stock_code})** - 評分: {score}\n"
            combined_text += f"🕒 **發布時間:** {publish_time}\n"
            combined_text += f"📌 **事件:** {news.get('core_event', '無')}\n"
            combined_text += f"💡 **理由:** {news.get('reason', '無')}\n"
            combined_text += f"🔗 [點擊查看原文]({news.get('url', '')})\n\n"
            
        # 這裡執行你原本發送 Request 到飛書 Webhook 的代碼
        # 例如飛書的富文本/卡片消息格式：
        # card_payload = {
        #     "msg_type": "interactive",
        #     "card": {
        #         "elements": [{"tag": "markdown", "content": combined_text}]
        #     }
        # }
        # requests.post(FEISHU_WEBHOOK, json=card_payload)
