
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
    # ===== 503 / 容量高峰应对参数（本次新增，仅服务于 AI 分析环节）=====
    MAX_TRIES_PER_BATCH = 3              # 每个批次主模型最多重试次数
    FALLBACK_MODEL = "gemini-2.5-flash"  # 主模型连续失败后降级的兜底模型
    # 分钟级退避基数（秒），配合随机抖动，专门对付 503“分钟级才恢复”的特性
    MINUTE_BACKOFF_BASE = [60, 120, 180]

    def _minute_backoff(self, attempt):
        # 第 attempt 次失败后的分钟级退避时长（基数 + 随机抖动）
        base = self.MINUTE_BACKOFF_BASE[min(attempt - 1, len(self.MINUTE_BACKOFF_BASE) - 1)]
        return base + random.uniform(0, 30)

    def _call_analyze(self, analyzer, batch, model=None):
        # 安全调用 analyzer.analyze：优先用 model= 关键字（模型降级链前提）；
        # 不支持该关键字则临时改 self.model 属性；异常统一按失败(None)返回交上层判定。
        try:
            if model is not None:
                try:
                    return analyzer.analyze(batch, model=model)
                except TypeError:
                    if hasattr(analyzer, "model"):
                        _orig = analyzer.model
                        try:
                            analyzer.model = model
                            return analyzer.analyze(batch)
                        finally:
                            analyzer.model = _orig
                return analyzer.analyze(batch)
            return analyzer.analyze(batch)
        except Exception as e:
            print(f"  [AI 呼叫異常] {type(e).__name__}: {e}")
            return None

    def _analyze_batch_with_retry(self, analyzer, batch, batch_index, primary_model):
        # 单批次 503 单层重试策略：主模型最多 3 次(分钟级退避+抖动)，
        # 全挂后降级 gemini-2.5-flash 再打 1 次，仍挂则硬停本轮。
        # 返回 (results, hard_stop)；results 非 None=本批成功，hard_stop=True=结束本轮剩余批次
        for attempt in range(1, self.MAX_TRIES_PER_BATCH + 1):
            results = self._call_analyze(analyzer, batch, model=primary_model)
            if results is not None:
                return results, False
            if attempt < self.MAX_TRIES_PER_BATCH:
                wait = self._minute_backoff(attempt)
                print(f"  [批次 {batch_index}] 第 {attempt}/{self.MAX_TRIES_PER_BATCH} 次分析失敗"
                      f"(疑似 503/容量高峰)，分鐘級退避 {wait:.0f}s 後重試...")
                time.sleep(wait)

        # 主模型连续 3 次失败 -> 降级 gemini-2.5-flash 再打 1 次（切换容量池，最有效）
        print(f"  [批次 {batch_index}] 主模型連續 {self.MAX_TRIES_PER_BATCH} 次失敗，"
              f"降級至 {self.FALLBACK_MODEL} 再試 1 次...")
        time.sleep(self._minute_backoff(self.MAX_TRIES_PER_BATCH))
        results = self._call_analyze(analyzer, batch, model=self.FALLBACK_MODEL)
        if results is not None:
            print(f"  [批次 {batch_index}] 降級模型分析成功。")
            return results, False

        # 降级仍失败 -> 判定进入容量高峰，硬停本轮，剩余批次留待下轮
        print(f"  [批次 {batch_index}] 降級模型仍失敗，判定進入容量高峰，"
              f"結束本輪剩餘批次分析，留待下輪排程重試。")
        return None, True

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
        elif (hour == 10 and minute >= 30) or (11 <= hour <= 14) or (hour == 15 and minute < 30):
            end = now.replace(hour=15, minute=30, second=0, microsecond=0)
            return "盤中 (10:30-15:30)", end
        return "自訂/測試時段", now + timedelta(minutes=60)

    def run(self):
        session_name, end_time = self._get_window()
        print(f"🌟 啟動時段：【{session_name}】，預計運行至 HKT: {end_time.strftime('%H:%M:%S')}")

        initial_sleep = random.randint(0, 5 * 60)
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

            raw_news = scraper.fetch_all()

            if raw_news:
                filtered_news = news_filter.apply(raw_news)

                final_news = []
                if filtered_news:
                    for news in filtered_news:
                        url = news.get("link")
                        title = news.get("title", "無標題")

                        if state_mgr.is_url_scanned(url):
                            print(f"  ⏭️ [重複攔截] 標題: {title[:40]}... | 網址: {url}")
                            continue

                        # 先不要在这里執行 add_record！只把它加進清單。
                        final_news.append(news)

                if final_news:
                    analyzed_news = []
                    batch_size = 20
                    primary_model = getattr(analyzer, "model", "gemini-3.5-flash-lite")

                    for batch_index, i in enumerate(range(0, len(final_news), batch_size), start=1):
                        batch = final_news[i:i + batch_size]
                        print(f"🧠 開始將第 {i + 1} 至 {min(i + batch_size, len(final_news))} 條新聞送入 AI 分析...")

                        # 503 单层重试：主模型 3 次(分钟级退避+抖动) -> 降级 gemini-2.5-flash 1 次 -> 仍失败硬停本轮
                        batch_results, hard_stop = self._analyze_batch_with_retry(
                            analyzer, batch, batch_index, primary_model
                        )

                        # 判斷 AI 是否成功分析 (回傳不是 None)
                        if batch_results is not None:
                            # 既然 AI 成功看過了 (不管有沒有達標)，這批新聞才正式寫入記憶體
                            for news in batch:
                                state_mgr.add_record(news.get("link"), event="已完成AI判斷")

                            if batch_results:
                                analyzed_news.extend(batch_results)

                        # 降级模型仍失败 -> 结束本轮剩余批次，留待下轮
                        if hard_stop:
                            print(f"⛔ 本輪提前結束剩餘批次分析（共 {len(final_news)} 條，已處理至第 {batch_index} 批）。")
                            break

                    if analyzed_news:
                        push_time = datetime.now(HKT).strftime('%Y-%m-%d %H:%M:%S')
                        print(f"🚀 AI 共篩選出 {len(analyzed_news)} 條達標訊號，準備合併推送...")
                        push_payload = {"push_time": push_time, "news_list": analyzed_news}
                        notifier.push(push_payload)
                    else:
                        print("✨ AI 深度分析完成，本次無達標重磅訊號！")
                else:
                    print("🤷‍♂️ 本次抓取沒有符合 [港股+利好] 條件的【全新】資訊，跳過 AI 分析。")

            state_mgr.save()

            now = datetime.now(HKT)
            if now >= end_time:
                break

            sleep_seconds = random.randint(7 * 60, 12 * 60)
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
