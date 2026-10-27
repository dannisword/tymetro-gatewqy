import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from sqlalchemy.orm import Session

from app.core.enums import AuditCategory, PlcEvent, SettingType
from app.core.logger import logger
from app.models.car_model import Car
from app.models.equipment_model import Equipment
from app.models.sensor_model import Sensor
from app.models.setting_log_model import SettingLog
from app.schemas.plc_command_schema import PlcCommandRequest, PlcCommandResponse
from app.services.audit_log_service import AuditLogService
from app.services.gateway_mqtt_service import gateway_mqtt_service


class PlcCommandError(Exception):
    """設定指令驗證或發送失敗"""


@dataclass(frozen=True)
class PlcCommandSpec:
    event: str
    register: str
    # 驗證並轉為寫入暫存器的整數值
    to_register_value: Callable[[Optional[float]], int]
    # 設定紀錄顯示文字
    to_log_value: Callable[[Optional[float], int], str]
    # PLC 完成回報暫存器 (值為 1 表示完成)，由後端查 sensors 資料表確認
    done_register: Optional[str] = None


def _require(value: Optional[float]) -> float:
    if value is None:
        raise PlcCommandError("缺少設定值 value")
    return value


def _fresh_air(value: Optional[float]) -> int:
    v = _require(value)
    if v not in (0, 25, 50, 75, 100):
        raise PlcCommandError("新鮮空氣擋板開度須為 0 / 25 / 50 / 75 / 100")
    return int(v)


def _emergency_air(value: Optional[float]) -> int:
    v = _require(value)
    if v not in (1, 2):
        raise PlcCommandError("緊急供氣擋板值須為 1 (關閉) 或 2 (開啟)")
    return int(v)


def _trigger(register: str, name: str, done_register: Optional[str] = None) -> PlcCommandSpec:
    """觸發型暫存器：寫入 1 觸發，PLC 完成後由「完成」暫存器回報"""
    return PlcCommandSpec(
        event=PlcEvent.WRITE_REGISTER.value,
        register=register,
        to_register_value=lambda v: 1,
        to_log_value=lambda v, reg: f"{name}觸發 ({register}: {reg})",
        done_register=done_register,
    )


# 設定溫度已由 /equipments/set-temperature 處理 (含 PLC 閉環確認)，不在此重複
# 要新增可執行的設定，在此加入一筆 (並於 core/enums.py 的 SettingType 補上對應類型)
COMMANDS: Dict[str, PlcCommandSpec] = {
    SettingType.FRESH_AIR_DAMPER.value: PlcCommandSpec(
        event=PlcEvent.SET_VALUE.value,
        register="D40212",
        to_register_value=_fresh_air,
        to_log_value=lambda v, reg: "關閉" if reg == 0 else f"{reg}%",
    ),
    SettingType.EMERGENCY_AIR_SUPPLY.value: PlcCommandSpec(
        event=PlcEvent.SET_VALUE.value,
        register="D40214",
        to_register_value=_emergency_air,
        to_log_value=lambda v, reg: str(reg),
    ),
    SettingType.RESET_ALL.value: _trigger("D40130", "重置復歸"),
    SettingType.INITIAL_VALUE.value: _trigger("D40216", "初始值"),
    SettingType.MANUAL_START_AC.value: _trigger("D40218", "手動開啟空調系統", done_register="D40219"),
    SettingType.FORCE_EMERGENCY_DAMPER.value: _trigger("D40220", "強制開啟緊急供氣擋板", done_register="D40221"),
    SettingType.FORCE_EXCHANGER.value: _trigger("D40222", "強制開啟換流器", done_register="D40223"),
    SettingType.CLEAR_COMP1_HOURS.value: _trigger("D40224", "清除壓縮機1運轉時數"),
    SettingType.CLEAR_COMP2_HOURS.value: _trigger("D40226", "清除壓縮機2運轉時數"),
    SettingType.CLEAR_AC_HOURS.value: _trigger("D40228", "清除空調運轉時數"),
}


# 完成確認：每秒查詢一次 sensors，逾時視為未完成
CONFIRM_TIMEOUT_SEC = 10
CONFIRM_INTERVAL_SEC = 1.0


class PlcCommandService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_log_service = AuditLogService(db)

    def _resolve_target(self, req: PlcCommandRequest) -> tuple[Car, Equipment]:
        logger.debug(f"_resolve_target: {req}")
        record = (
            self.db.query(Car, Equipment)
            .join(Equipment, Equipment.carId == Car.id)
            .filter(
                (Car.carVin == str(req.carNo)) | (Car.carNo == req.carNo),
                Equipment.endPos == req.endPos,
                Equipment.isActive == True,
                Car.isActive == True,
            )
            .first()
        )
        if not record:
            raise PlcCommandError(f"找不到車廂 {req.carNo} 的 {req.endPos} 端設備")
        car, equipment = record
        return car, equipment

    async def execute(self, req: PlcCommandRequest, operator: str, ip_address: Optional[str]) -> PlcCommandResponse:
        started = time.perf_counter()
        spec = COMMANDS.get(req.command)
        if spec is None:
            raise PlcCommandError(f"不支援的設定類型: {req.command}")

        label = SettingType(req.command).label
        topic = ""
        payload: Dict[str, Any] = {}
        log_value: Optional[str] = None
        error: Optional[str] = None
        train_code = req.trainCode or ""
        car: Optional[Car] = None
        equipment: Optional[Equipment] = None
        baseline_done: Optional[float] = None

        try:
            car, equipment = self._resolve_target(req)
            if not train_code:
                train_code = str(car.trainCode or "").strip()
                if train_code.upper().startswith("P"):
                    train_code = train_code[1:]
            car_vin = str(car.carVin or "")
            car_no = int(car_vin) if car_vin.isdigit() else int(str(car.carNo or req.carNo))

            baseline_done = self._read_sensor_value(car, equipment, spec.done_register)
            reg_value = spec.to_register_value(req.value)
            log_value = spec.to_log_value(req.value, reg_value)
            topic = f"TYMC/AIR/SET/{train_code}/{car_no}/{req.endPos}"
            payload = {
                "events": spec.event,
                "trainCode": train_code,
                "carNo": car_no,
                "endPos": req.endPos,
                "register": {spec.register: reg_value},
            }
            # 觸發型暫存器不可 retain，避免 PLC 重新連線時被重複觸發
            await gateway_mqtt_service.publish_message(
                topic, json.dumps(payload, ensure_ascii=False), qos=1, retain=False, raise_on_error=True
            )
        except PlcCommandError as e:
            error = str(e)
        except Exception as e:
            logger.error(f"[PlcCommand] 執行失敗: {e}")
            error = f"MQTT 指令發布失敗: {e}"

        confirmed: Optional[bool] = None
        confirm_message: Optional[str] = None
        if not error and spec.done_register and car is not None and equipment is not None:
            confirmed, confirm_message = await self._wait_done(car, equipment, spec.done_register, baseline_done)
            log_value = f"{log_value} | {confirm_message}"

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        self._write_audit(req, operator, ip_address, label, log_value, topic, payload, error, elapsed_ms)

        if error:
            raise PlcCommandError(error)

        return PlcCommandResponse(
            command=req.command,
            commandName=label,
            trainCode=train_code,
            carNo=payload["carNo"],
            endPos=req.endPos,
            topic=topic,
            registers=payload["register"],
            settingLogId=self._write_setting_log(req, operator, log_value, topic, payload),
            confirmed=confirmed,
            confirmMessage=confirm_message,
        )

    def _read_sensor_value(self, car: Car, equipment: Equipment, code: Optional[str]) -> Optional[float]:
        if not code:
            return None
        # 結束目前交易以讀到 MQTT 寫入的最新值
        self.db.rollback()
        value = (
            self.db.query(Sensor.sensorValue)
            .filter(Sensor.carId == car.id, Sensor.equipmentId == equipment.id, Sensor.sensorCode == code)
            .scalar()
        )
        return None if value is None else float(value)

    async def _wait_done(
        self, car: Car, equipment: Equipment, done_register: str, baseline: Optional[float]
    ) -> tuple[bool, str]:
        """輪詢完成暫存器是否為 1。發送前已為 1 時，須先看到歸零再回到 1，避免把舊值當成完成"""
        seen_reset = baseline != 1
        deadline = time.monotonic() + CONFIRM_TIMEOUT_SEC
        while time.monotonic() < deadline:
            await asyncio.sleep(CONFIRM_INTERVAL_SEC)
            value = self._read_sensor_value(car, equipment, done_register)
            if value != 1:
                seen_reset = True
            elif seen_reset:
                return True, f"PLC 已完成 ({done_register}=1)"
        return False, f"PLC 未於 {CONFIRM_TIMEOUT_SEC} 秒內回報完成 ({done_register})"

    def _write_setting_log(
        self, req: PlcCommandRequest, operator: str, log_value: Optional[str], topic: str, payload: Dict[str, Any]
    ) -> Optional[int]:
        try:
            log = SettingLog(
                settingType=req.command,
                value=log_value,
                operator=operator,
                isNotified=True,
                topic=topic,
                payload=json.dumps(payload, ensure_ascii=False),
            )
            self.db.add(log)
            self.db.commit()
            self.db.refresh(log)
            return int(log.id)  # type: ignore[arg-type]
        except Exception as e:
            # 指令已送出，設定紀錄失敗不應回報整體失敗
            self.db.rollback()
            logger.error(f"[PlcCommand] 寫入設定紀錄失敗: {e}")
            return None

    def _write_audit(
        self,
        req: PlcCommandRequest,
        operator: str,
        ip_address: Optional[str],
        label: str,
        log_value: Optional[str],
        topic: str,
        payload: Dict[str, Any],
        error: Optional[str],
        elapsed_ms: int,
    ) -> None:
        target = f"{req.carNo}車 {req.endPos}端"
        if error:
            detail = f"{label} ({target}) 失敗: {error}"
        else:
            detail = f"{label} ({target}) = {log_value} | topic={topic} | payload={json.dumps(payload, ensure_ascii=False)} | {elapsed_ms}ms"
        try:
            self.audit_log_service.log(
                auditCategory=AuditCategory.SETTING.value,
                action=f"plc_{req.command.lower()}",
                status="fail" if error else "success",
                operator=operator,
                ipAddress=ip_address,
                detail=detail[:1000],
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"[PlcCommand] 寫入稽核紀錄失敗: {e}")
