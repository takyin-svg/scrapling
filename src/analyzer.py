import json
import time
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
        5. 股票代號 (stock_code): 必須提取具體的港股代號 (如 0700.HK)。若是宏觀大盤、行業泛指而無具體個股，請填寫「無」。
        
        返回嚴格的 JSON 陣列格式：
        [
          {
            "title": "原新聞標題", "url": "原新聞連結", "source": "原來源",
            "stock_code": "代號或無", "stock_name": "個股中文", "core_event": "核心事件限10字",
            "is_major_bullish": true/false, "score": 88, "confidence": 90,
            "category": "利好分類", "urgency": "Immediate/1-3 Days/Long Term",
            "reason": "80字以內點評", "risk_warning": "風險提示"
          }
        ]
        """
        
        model_name = "gemini-3.5-flash-lite"
        print(f"🧠 開始將 {len(news_list)} 條新聞送入 Gemini ({model_name}) 進行基金經理級深度分析...")
        analyzed_results = []
        
        for i in range(0, len(news_list), 15):
            batch = news_list[i:i+15]
            max_retries = 3
            wait_times = [30, 60, 120] 
            
            for attempt in range(1, max_retries + 1):
                try:
                    res = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt + "\n資料:\n" + json.dumps(batch, ensure_ascii=False),
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.1 
                        )
                    )
                    
                    batch_results = json.loads(res.text)
                    
                    # 🚨 這裡加入決策日誌：把 AI 的大腦思考過程印出來！
                    for item in batch_results:
                        title_preview = item.get("title", "")[:15].replace("\n", "")
                        stock = item.get("stock_code", "")
                        is_bullish = item.get("is_major_bullish", False)
                        score = item.get("score", 0)
                        reason = item.get("reason", "無詳細理由")
                        
                        # 判斷淘汰原因
                        if not stock or stock == "無":
                            print(f"  ❌ [淘汰] 代號: 無 | 評分: {score} | 標題: {title_preview}... | 原因: 無具體受惠個股 ({reason})")
                        elif not is_bullish or score < 85:
                            print(f"  ❌ [淘汰] 代號: {stock} | 評分: {score} | 標題: {title_preview}... | 原因: 利好程度不足 ({reason})")
                        else:
                            print(f"  ✅ [達標] 代號: {stock} | 評分: {score} | 標題: {title_preview}... | 理由: {reason}")
                            analyzed_results.append(item)
                            
                    break  # 成功就跳出重試迴圈
                    
                except Exception as e:
                    error_msg = str(e)
                    if "503" in error_msg or "429" in error_msg:
                        wait_time = wait_times[attempt - 1]
                        print(f"  ⏳ Google API 請求頻繁 (503/429)，冷卻 {wait_time} 秒後進行第 {attempt}/{max_retries} 次重試...")
                        time.sleep(wait_time)
                    else:
                        print(f"  ❌ AI 批次分析出錯: {error_msg}")
                        break 
            
            time.sleep(3)
                
        return analyzed_results
