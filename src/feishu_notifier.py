import requests
import json
from src.config import FEISHU_WEBHOOK

class FeishuNotifier:
    def __init__(self, state_manager=None):
        # 兼容 orchestrator 傳入的 state_mgr
        self.state_manager = state_manager

    def push(self, payload: dict):
        push_time = payload.get("push_time")
        news_list = payload.get("news_list", [])
        
        if not news_list:
            return

        if not FEISHU_WEBHOOK:
            print("⚠️ 未設定 FEISHU_WEBHOOK，跳過飛書推送。")
            return

        # 組合所有新聞內容為一個大型文本 (Markdown 格式)
        combined_text = f"⏰ **推送時間 (HKT):** {push_time}\n"
        combined_text += f"📊 **本次共捕獲 {len(news_list)} 條重磅訊號**\n\n"
        
        for idx, news in enumerate(news_list, 1):
            stock_code = news.get('stock_code', '無')
            stock_name = news.get('stock_name', '無')
            score = news.get('score', 0)
            original_title = news.get('title', '無標題')  # 提取原文標題
            
            # 獲取新聞發布時間 (相容各種爬蟲可能的 key 命名)
            publish_time = news.get('time', news.get('publish_time', news.get('pubDate', '未知時間')))
            
            combined_text += f"**【{idx}】{stock_name} ({stock_code})** - 評分: {score}\n"
            combined_text += f"🕒 **發布時間:** {publish_time}\n"
            combined_text += f"📰 **原文標題:** {original_title}\n"  # 增加原文標題顯示
            combined_text += f"📌 **事件:** {news.get('core_event', '無')}\n"
            combined_text += f"💡 **理由:** {news.get('reason', '無')}\n"
            combined_text += f"🔗 [點擊查看原文]({news.get('url', '')})\n\n"
            
        # 封裝飛書富文本 (Interactive 卡片) 格式
        card_payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": "🚀 港股量化監控：重磅利好信號"
                    },
                    "template": "red"
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": combined_text
                    }
                ]
            }
        }
        
        # 發送 Request 到飛書 Webhook
        try:
            response = requests.post(FEISHU_WEBHOOK, json=card_payload)
            if response.status_code == 200:
                print(f"✅ 成功發送 {len(news_list)} 條合併訊號至飛書！")
            else:
                print(f"❌ 飛書發送失敗，狀態碼: {response.status_code}, 回應: {response.text}")
        except Exception as e:
            print(f"❌ 飛書請求發生異常: {str(e)}")
