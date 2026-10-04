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
        first_run_time = datetime.now(HKT) + timedelta(seconds=initial_sleep)
        print(f"🎲 [首次排程] 第一波隨機爬取時間定於 HKT: {first_run_time.strftime('%H:%M:%S')}")
        print(f"💤 [狀態] 系統正在 Sleep 待機中... (預計等待 {initial_sleep} 秒 / 約 {initial_sleep // 60} 分鐘)")
        time.sleep(initial_sleep)

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
            print(f"⏰ [{now.strftime('%H:%M:%S')} HKT] 開始執行隨機抽樣爬取！")
            print(f"==================================================")
            
            # Step 1: 抓取
            raw_news = scraper.fetch_all()
            
            # Step 2: 過濾
            if raw_news:
                filtered_news = news_filter.apply(raw_news)
                # Step 3 & 4: 分析與推送
                if filtered_news:
                    analyzed_news = analyzer.analyze(filtered_news)
                    notifier.push(analyzed_news)
                else:
                    print("🤷‍♂️ 本次抓取沒有符合 [港股+利好] 條件的新鮮資訊，跳過 AI 分析。")
            
            # 保存歷史紀錄
            state_mgr.save()
            
            # 計算下一次排程
            now = datetime.now(HKT)
            if now >= end_time:
                break
                
            sleep_seconds = random.randint(5 * 60, 10 * 60)
            if now + timedelta(seconds=sleep_seconds) > end_time:
                remaining = (end_time - now).total_seconds()
                if remaining > 300:
                    next_run_time = now + timedelta(seconds=remaining)
                    print(f"🎲 [末次排程] 本時段即將結束，最後一次動作時間定於 HKT: {next_run_time.strftime('%H:%M:%S')}")
                    print(f"💤 [狀態] 系統正在 Sleep 待機中... (休眠剩餘 {int(remaining)} 秒至時段結束)")
                    time.sleep(remaining)
                break
                
            next_run_time = now + timedelta(seconds=sleep_seconds)
            print(f"\n🎲 [下一輪排程] 隨機執行時間定於 HKT: {next_run_time.strftime('%H:%M:%S')}")
            print(f"💤 [狀態] 系統正在 Sleep 待機中... (等待 {sleep_seconds} 秒 / 約 {sleep_seconds // 60} 分鐘)")
            time.sleep(sleep_seconds)
            
        print("🏁 當前排程時段結束，程式平穩退出。")
