import json
from google import genai
from google.genai import types
from src.config import GEMINI_API_KEY

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
        
        analyzed_results = []
        for i in range(0, len(news_list), 15):
            batch = news_list[i:i+15]
            try:
                res = self.client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt + "\n資料:\n" + json.dumps(batch, ensure_ascii=False),
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )
                analyzed_results.extend(json.loads(res.text))
            except Exception as e:
                print(f"  ❌ AI 批次分析出錯: {e}")
                
        return analyzed_results
