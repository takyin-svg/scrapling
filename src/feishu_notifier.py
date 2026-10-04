import requests
from src.config import FEISHU_WEBHOOK, MIN_SCORE, MIN_CONFIDENCE

class FeishuNotifier:
    def __init__(self, state_manager):
        self.state_manager = state_manager

    def push(self, analyzed_news: list[dict]):
        if not FEISHU_WEBHOOK:
            print("⚠️ 尚未設定 FEISHU_WEBHOOK，略過發送。")
            return
            
        valid_bullish = [
            item for item in analyzed_news 
            if item.get("is_major_bullish") 
            and item.get("score", 0) >= MIN_SCORE 
            and item.get("confidence", 0) >= MIN_CONFIDENCE
        ]
        valid_bullish.sort(key=lambda x: x.get("score", 0), reverse=True)
        print(f"✨ AI 深度分析完成，篩選出 {len(valid_bullish)} 條達標重磅訊號！")

        pushed_count = 0
        for item in valid_bullish:
            stock = item.get('stock_code', '')
            event = item.get('core_event', '')
            
            # 事件去重
            if self.state_manager.is_event_pushed(stock, event):
                print(f"  ⏭️ 攔截重複事件: {stock} - {event}")
                continue

            msg = {
                "msg_type": "interactive",
                "card": {
                    "header": {"title": {"tag": "plain_text", "content": f"🚀 量化利好觸發 | {item.get('stock_name')}"}, "template": "red"},
                    "elements": [
                        {"tag": "markdown", "content": f"**標題：** {item.get('title')}"},
                        {"tag": "markdown", "content": f"**標的：** {item.get('stock_name')} ({stock})\n**事件：** {event}"},
                        {"tag": "hr"},
                        {"tag": "markdown", "content": f"🔥 **評分：** {item.get('score')} 分 | 💎 **置信度：** {item.get('confidence')}%\n🏷️ **分類：** {item.get('category')} | ⚡ **緊急度：** {item.get('urgency')}"},
                        {"tag": "markdown", "content": f"📝 **經理點評：**\n{item.get('reason')}"},
                        {"tag": "markdown", "content": f"⚠️ **風險排查：**\n{item.get('risk_warning')}"},
                        {"tag": "hr"},
                        {"tag": "markdown", "content": f"🔗 [點擊閱讀原文]({item.get('url')}) *(來源: {item.get('source')})*"}
                    ]
                }
            }
            try:
                r = requests.post(FEISHU_WEBHOOK, json=msg)
                if r.status_code == 200:
                    pushed_count += 1
                    self.state_manager.add_record(url=item.get('url'), stock=stock, event=event)
            except Exception as e:
                print(f"  ❌ 飛書發送失敗: {e}")
                
        print(f"🚀 成功發送 {pushed_count} 條訊號至飛書")
