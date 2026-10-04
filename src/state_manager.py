import json
import os
from datetime import datetime, timedelta
from src.config import HISTORY_FILE, HKT

class StateManager:
    def __init__(self):
        self.records = []
        self.load()

    def load(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    self.records = json.load(f)
            except Exception:
                self.records = []
        self._clean_old_records()

    def _clean_old_records(self):
        """雙重清理機制：保留7天內，且最多保留最新1000筆"""
        valid_records = []
        cutoff_time = datetime.now(HKT) - timedelta(days=7)
        for r in self.records:
            try:
                dt = datetime.strptime(r["timestamp"], '%Y-%m-%d %H:%M')
                dt = HKT.localize(dt) if dt.tzinfo is None else dt
                if dt > cutoff_time:
                    valid_records.append(r)
            except Exception:
                pass
        self.records = valid_records[-1000:]

    def save(self):
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.records, f, ensure_ascii=False)

    def is_url_scanned(self, url: str) -> bool:
        return any(r.get("url") == url for r in self.records)

    def is_event_pushed(self, stock: str, event: str) -> bool:
        if not stock or stock == '大盤/板塊':
            return False
        return any(r.get("stock") == stock and r.get("event") == event for r in self.records)

    def add_record(self, url: str, stock: str = "", event: str = "已掃描"):
        self.records.append({
            "url": url,
            "stock": stock,
            "event": event,
            "timestamp": datetime.now(HKT).strftime('%Y-%m-%d %H:%M')
        })
