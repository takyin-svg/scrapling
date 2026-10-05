import json
import time
from google import genai
from google.genai import types
from src.config import GEMINI_API_KEY, AI_MODEL

class GeminiAnalyzer:
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY 未設定")
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def analyze(self, news_list: list[dict]) -> list[dict]:
        if not news_list:
            return []

        prompt = """
        你是港股事件驅動對沖基金經理，專門從新聞中篩選未來48小時-2周可能引發股價大幅上漲的重大催化劑。
        
        【判斷標準】
        1. 事件已正式落實，實質改變公司盈利或估值。
        2. 評分 (score): 95-100(極重大)；85-94(明確重大利好)；<85(忽略，設為 is_major_bullish: false)。
        3. 置信度 (confidence): 95=官方；90=權威媒體；60=市場消息。
        4. 風險排查 (risk_warning): 偵測暗藏利空(配股/供股/立案/盈警/減持)，若有以「🔴」開頭；輕微利空以「🟡」開頭；若無填「近期未見明顯利空」。
        
        返回嚴格的 JSON 陣列格式：
        [
          {
            "title": "原新聞標題", "url": "原新聞連結", "source": "原來源",
            "stock_code": "代號", "stock_name": "個股中文", "core_event": "核心事件限10字",
            "is_major_bullish": true/false, "score": 88, "confidence": 90,
            "category": "利好分類", "urgency": "Immediate/1-3 Days/Long Term",
            "reason": "80字以內點評", "risk_warning": "風險提示"
          }
        ]
        """
        
        print(f"🧠 開始將 {len(news_list)} 條新聞送入 Gemini ({AI_MODEL}) 進行基金經理級深度分析...")
        analyzed_results = []
        
        # 每 15 條為一個批次
        for i in range(0, len(news_list), 15):
            batch = news_list[i:i+15]
            max_retries = 3
            
            # 🛡️ 核心避震器：應付 503 塞車的重試機制
            for attempt in range(1, max_retries + 1):
                try:
                    res = self.client.models.generate_content(
                        model=AI_MODEL,  # 如果 src.config 沒設定 AI_MODEL，也可以直接寫 'gemini-3.8-flash'
                        contents=prompt + "\n資料:\n" + json.dumps(batch, ensure_ascii=False),
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.1 # 極低隨機性，維持基金經理的冷靜判斷
                        )
                    )
                    
                    # 成功解析，加入結果清單
                    analyzed_results.extend(json.loads(res.text))
                    break  # 成功就跳出重試迴圈，處理下一批
                    
                except Exception as e:
                    error_msg = str(e)
                    # 捕捉 API 塞車或限流錯誤
                    if "503" in error_msg or "429" in error_msg:
                        print(f"  ⏳ Google API 塞車中 (503/429)，等待 5 秒後進行第 {attempt}/{max_retries} 次重試...")
                        time.sleep(5)
                    else:
                        print(f"  ❌ AI 批次分析出錯: {error_msg}")
                        break # 如果是其他嚴重錯誤(如 JSON 解析失敗)，放棄這批，繼續往下執行
            
            # 批次之間稍作暫停，避免密集連線被 API 封鎖
            time.sleep(2)
                
        return analyzed_results
