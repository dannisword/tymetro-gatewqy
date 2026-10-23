import time
from datetime import datetime
from typing import Any, Dict, List, Optional, cast
from app.core.logger import logger
from app.database.session import SessionLocal
from app.models.equipment_event_model import EquipmentEvent
from app.models.event_template_model import EventTemplate
from app.utils.plc_decoder import DEFAULT_PLC_BIT_TEMPLATES, detect_word_bit_changes

class EquipmentEventService:
    """
    PLC Word 位元變動偵測：
    - 以記憶體快取前次 Word 值 (old ^ new)，僅對變動 Bit 產生事件
    - 事件寫入 equipment_events 表，並回傳事件清單供即時推播
    """
    def __init__(self):
        # "car_vin:end_pos:register" -> last word
        self._last_words: Dict[str, int] = {}
        self._templates: Dict[str, Dict[int, Dict[str, Any]]] = {}
        self._templates_loaded_at: float = 0.0

    def reload_templates(self):
        """清除樣板快取，下次偵測時自 SQLite event_templates 重新載入"""
        self._templates_loaded_at = 0.0

    def get_templates_map(self) -> Dict[str, Dict[int, Dict[str, Any]]]:
        """取得啟用中的樣板 (快取 60 秒)；DB 無資料時退回內建預設樣板"""
        now = time.time()
        if self._templates and now - self._templates_loaded_at < 60:
            return self._templates
        db = SessionLocal()
        try:
            rows = db.query(EventTemplate).filter(EventTemplate.isActive == True).all()
            tmap: Dict[str, Dict[int, Dict[str, Any]]] = {}
            for t in rows:
                tmap.setdefault(str(t.registerCode).upper(), {})[int(cast(Any, t.bitIndex))] = {
                    "tag": t.tagName, "desc": t.tagDesc, "type": t.eventType,
                    "severity": t.severity, "needConfirm": bool(t.needConfirm),
                }
            self._templates = tmap or DEFAULT_PLC_BIT_TEMPLATES
        except Exception as e:
            logger.warning(f"[EquipmentEventService] 載入樣板失敗，使用預設樣板: {e}")
            self._templates = self._templates or DEFAULT_PLC_BIT_TEMPLATES
        finally:
            db.close()
        self._templates_loaded_at = now
        return self._templates

    def process_registers(
        self,
        car_vin: Optional[str],
        end_pos: Optional[int],
        register_dict: Dict[str, Any],
        timestamp: float,
    ) -> List[Dict[str, Any]]:
        car_no = int(car_vin[1]) if car_vin and len(car_vin) >= 2 and car_vin[1].isdigit() else None
        event_time = datetime.fromtimestamp(timestamp)
        events: List[Dict[str, Any]] = []
        templates = self.get_templates_map()

        for code, raw_val in register_dict.items():
            code = str(code).upper()
            bit_map = templates.get(code)
            if bit_map is None:
                continue
            try:
                new_word = int(float(raw_val))
            except (ValueError, TypeError):
                continue

            key = f"{car_vin}:{end_pos}:{code}"
            old_word = self._last_words.get(key)
            self._last_words[key] = new_word
            if old_word is None:
                # 首次接收：視舊值為 0，已為 1 的 bit 一律記錄一筆事件
                old_word = 0
            if old_word == new_word:
                continue

            for chg in detect_word_bit_changes(old_word, new_word, bit_map):
                events.append({
                    "carVin": car_vin,
                    "carNo": car_no,
                    "endPos": end_pos,
                    "registerCode": code,
                    "bitIndex": chg["bitIndex"],
                    "tagName": chg["tagName"],
                    "tagDesc": chg["tagDesc"],
                    "eventType": chg["eventType"],
                    "prevValue": chg["prevValue"],
                    "newValue": chg["newValue"],
                    "action": chg["action"],
                    "isConfirmed": False,
                    "triggeredAt": event_time,
                })
        return events

    def save_events(self, events: List[Dict[str, Any]]) -> int:
        """批次寫入 equipment_events 表 (同步，供 run_in_executor 呼叫)"""
        if not events:
            return 0
        db = SessionLocal()
        try:
            db.bulk_insert_mappings(cast(Any, EquipmentEvent), events)
            db.commit()
            return len(events)
        except Exception as e:
            db.rollback()
            logger.error(f"[EquipmentEventService] 批次寫入事件記錄失敗: {e}")
            return 0
        finally:
            db.close()

equipment_event_service = EquipmentEventService()
