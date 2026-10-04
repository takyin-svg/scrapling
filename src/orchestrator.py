import time
import random
from datetime import datetime, timedelta
from src.config import HKT
from src.state_manager import StateManager
from src.scraper import HKStockScraper
from src.filters import NewsFilter
from src.analyzer import GeminiAnalyzer
from src.feishu_notifier import FeishuNotifier

class Orchestrator:
    def _get_window(self):
        now = datetime.now(HKT)
        hour, minute = now.hour, now.minute
        if hour >= 22 or hour < 2:
            end = now.replace(hour=2, minute=0, second=0, microsecond=0)
            if hour >= 22: end += timedelta(days=1)
            return "夜間 (昨收16:00後至此刻)", end
        elif 5 <= hour < 10:
            end = now.replace(hour=10, minute=0, second=0, microsecond=0)
            return "早盤前 (橫跨週末/昨夜至今日開盤)", end
        elif (hour == 10 and minute >= 20) or (11 <= hour < 14):
            end = now.replace(hour=14, minute=0, second=0, microsecond=0)
            return "盤中 (10:30-14:00)", end
        return "自訂/測試時段", now + timedelta(minutes=60)

    def run(self):
        session_name, end_time = self._get_window()
        print(f"🌟 啟動時段：【{session_name}】，預計運行至 HKT: {end_time.strftime('%H:%M:%S')}")

        initial_sleep = random.randint(0, 15 * 60)
        print(f"🎲 [隨機喚醒] 系統將在 {initial_sleep // 60} 分鐘後開始第一波掃描...")
        time.sleep(initial_sleep)

        # 初始化模組
        state_mgr = StateManager()
        scraper = HKStockScraper()
        news_filter = NewsFilter(state_mgr)
        analyzer = GeminiAnalyzer()
        notifier = FeishuNotifier(state_mgr)

        while True:
            now = datetime.now(HKT)
            if now >= end_time:
                break
                
            print(f"\n==================================================")
            print(f"⏰ [{now.strftime('%H:%M:%S')} HKT] 啟動抓取循環")
            
            # Step 1: 隱形抓取
            raw_news = scraper.fetch_all()
            
            # Step 2: 本地初篩 (零成本)
            filtered_news = news_filter.apply(raw_news)
            
            # Step 3: AI 深度分析
            if filtered_news:
                analyzed_news = analyzer.analyze(filtered_news)
                # Step 4: 飛書推送
                notifier.push(analyzed_news)
            
            # 保存狀態
            state_mgr.save()
            
            # 計算下一次隨機休眠
            now = datetime.now(HKT)
            if now >= end_time:
                break
                
            sleep_seconds = random.randint(22 * 60, 32 * 60)
            if now + timedelta(seconds=sleep_seconds) > end_time:
                remaining = (end_time - now).total_seconds()
                if remaining > 300:
                    print(f"💤 接近時段尾聲，休眠剩餘 {int(remaining)} 秒...")
                    time.sleep(remaining)
                break
                
            print(f"💤 [進入休眠] 等待約 {sleep_seconds // 60} 分鐘...")
            time.sleep(sleep_seconds)
            
        print("🏁 當前排程時段結束，程式平穩退出。")
