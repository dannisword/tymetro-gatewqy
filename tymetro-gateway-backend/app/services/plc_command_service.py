import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.enums import AuditCategory, PlcEvent, SettingType
from app.core.logger import logger
from app.database.db_config_repo import db_config_repo
from app.models.car_model import Car
from app.models.equipment_model import Equipment
from app.models.sensor_model import Sensor
from app.schemas.plc_command_schema import PlcCommandRequest, PlcCommandResponse
from app.models.setting_log_model import SettingLog
from app.services.audit_log_service import AuditLogService
from app.services.gateway_mqtt_service import gateway_mqtt_service
from app.utils.datetime_util import get_local_now


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
    # 完成確認方式：flag = 完成暫存器變為 1 (觸發型)；match = 完成暫存器回傳與寫入值相同 (設定值型，可安全重發)
    done_mode: str = "flag"
    # match 型最多發送次數 (每次發送後等待完成)；flag 型為一次性動作，重發等於重複觸發，固定為 1
    retries: int = 1
    # 雲端 payload 的暫存器值轉回 PlcCommandRequest.value (如 D40200 為 x10)
    from_register_value: Callable[[float], float] = lambda raw: raw


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


def _temperature(value: Optional[float]) -> int:
    # 暫存器值為 x10 (23.0°C -> 230)
    return int(round(_require(value) * 10))


def _trigger(register: str, name: str, done_register: Optional[str] = None) -> PlcCommandSpec:
    """觸發型暫存器：寫入 1 觸發，PLC 完成後由「完成」暫存器回報"""
    return PlcCommandSpec(
        event=PlcEvent.WRITE_REGISTER.value,
        register=register,
        to_register_value=lambda v: 1,
        to_log_value=lambda v, reg: f"{name}觸發 ({register}: {reg})",
        done_register=done_register,
    )


# 要新增可執行的設定，在此加入一筆 (並於 core/enums.py 的 SettingType 補上對應類型)
# 多端點批次設定見 PlcCommandService.execute_batch
COMMANDS: Dict[str, PlcCommandSpec] = {
    SettingType.TEMPERATURE.value: PlcCommandSpec(
        event=PlcEvent.SET_VALUE.value,
        register="D40200",
        to_register_value=_temperature,
        to_log_value=lambda v, reg: f"{reg / 10:g}°C",
        done_register="D40201",
        done_mode="match",
        retries=3,
        from_register_value=lambda raw: raw / 10.0,
    ),
    SettingType.FRESH_AIR_DAMPER.value: PlcCommandSpec(
        event=PlcEvent.SET_VALUE.value,
        register="D40212",
        to_register_value=_fresh_air,
        to_log_value=lambda v, reg: "關閉" if reg == 0 else f"{reg}%",
        done_register="D40213",
        done_mode="match",
        retries=3,
    ),
    SettingType.EMERGENCY_AIR_SUPPLY.value: PlcCommandSpec(
        event=PlcEvent.SET_VALUE.value,
        register="D40214",
        to_register_value=_emergency_air,
        to_log_value=lambda v, reg: str(reg),
        done_register="D40215",
        done_mode="match",
        retries=3,
    ),
    SettingType.RESET_ALL.value: _trigger("D40130", "重置復歸", done_register="D40131"),
    SettingType.INITIAL_VALUE.value: _trigger("D40216", "初始值", done_register="D40217"),
    SettingType.MANUAL_START_AC.value: _trigger("D40218", "手動開啟空調系統", done_register="D40219"),
    SettingType.FORCE_EMERGENCY_DAMPER.value: _trigger("D40220", "強制開啟緊急供氣擋板", done_register="D40221"),
    SettingType.FORCE_EXCHANGER.value: _trigger("D40222", "強制開啟換流器", done_register="D40223"),
    SettingType.CLEAR_COMP1_HOURS.value: _trigger("D40224", "清除壓縮機1運轉時數", done_register="D40225"),
    SettingType.CLEAR_COMP2_HOURS.value: _trigger("D40226", "清除壓縮機2運轉時數", done_register="D40227"),
    SettingType.CLEAR_AC_HOURS.value: _trigger("D40228", "清除空調運轉時數", done_register="D40229"),
}


# 完成確認：每秒查詢一次 sensors，逾時視為未完成
CONFIRM_TIMEOUT_SEC = 10
CONFIRM_INTERVAL_SEC = 1.0


@dataclass(frozen=True)
class CloudConfirmation:
    """雲端指令的完成確認所需資訊 (發送前先取得完成暫存器的基準值)"""
    car: Car
    equipment: Equipment
    done_register: str
    baseline: Optional[float]


# 以寫入暫存器反查設定類型 (雲端指令只帶暫存器位址，不帶設定類型)
COMMAND_BY_REGISTER: Dict[str, str] = {spec.register: command for command, spec in COMMANDS.items()}


# 以寫入暫存器反查完成暫存器 (雲端指令只帶暫存器位址，不帶設定類型)
DONE_REGISTER_BY_REGISTER: Dict[str, str] = {
    spec.register: spec.done_register for spec in COMMANDS.values() if spec.done_register and spec.done_mode == "flag"
}


def _fmt(value: Optional[float]) -> str:
    return "無資料" if value is None else f"{value:g}"


@dataclass
class _DoneWatcher:
    """單一目標的完成確認狀態 (execute 與 execute_batch 共用)"""
    car: Car
    equipment: Equipment
    done_register: str
    baseline: Optional[float]
    mode: str = "flag"
    expected: Optional[float] = None
    trigger_register: Optional[str] = None
    seen_reset: bool = field(init=False)
    done_value: Optional[float] = None
    trigger_value: Optional[float] = None
    filled: bool = False

    def __post_init__(self):
        self.seen_reset = self.baseline != 1


@dataclass
class BatchTargetResult:
    carNo: Optional[int]
    endPos: int
    confirmed: Optional[bool] = None
    message: Optional[str] = None
    plcValues: Optional[Dict[str, Optional[float]]] = None
    error: Optional[str] = None
    settingLogId: Optional[int] = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.confirmed is not False

    @property
    def name(self) -> str:
        return f"{self.carNo}-{self.endPos}端"


class PlcCommandService:
    def __init__(self, db: Session):
        self.db = db
        # 最近一次 _wait_done 結束時的點位值 (觸發點位、完成點位)
        self.last_plc_values: Optional[Dict[str, Optional[float]]] = None
        self.audit_log_service = AuditLogService(db)

    def _resolve_target(self, req: PlcCommandRequest) -> tuple[Car, Equipment]:
        logger.debug(f"_resolve_target: {req}")
        return self._find_target(req.carNo, req.endPos)

    def _find_target(self, car_no: Any, end_pos: int) -> tuple[Car, Equipment]:
        record = (
            self.db.query(Car, Equipment)
            .join(Equipment, Equipment.carId == Car.id)
            .filter(
                (Car.carVin == str(car_no)) | (Car.carNo == car_no),
                Equipment.endPos == end_pos,
                Equipment.isActive == True,
                Car.isActive == True,
            )
            .first()
        )
        if not record:
            raise PlcCommandError(f"找不到車廂 {car_no} 的 {end_pos} 端設備")
        car, equipment = record
        return car, equipment

    async def execute(
        self,
        req: PlcCommandRequest,
        operator: str,
        ip_address: Optional[str],
        command_id: Optional[str] = None,
        event: Optional[str] = None,
    ) -> PlcCommandResponse:
        """
        :param command_id: 雲端指令 ID。有值時設定紀錄於發送後、等待完成前以 ACKED 寫入 (之後由雲端回報流程更新狀態)，
                           無論成功或失敗都會留下紀錄
        :param event: 下發的 events 欄位；未指定時使用該指令預設值 (雲端指令沿用雲端帶入的值)
        """
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
        reg_value: Optional[int] = None

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
                "events": event or spec.event,
                "trainCode": train_code,
                "carNo": car_no,
                "endPos": req.endPos,
                "register": {spec.register: reg_value},
            }
            await self._publish(topic, payload)
        except PlcCommandError as e:
            error = str(e)
        except Exception as e:
            logger.error(f"[PlcCommand] 執行失敗: {e}")
            error = f"MQTT 指令發布失敗: {e}"

        setting_log_id: Optional[int] = None
        if command_id:
            setting_log_id = self._write_setting_log(
                req.command, operator, log_value or error, topic, payload, command_id=command_id
            )

        confirmed: Optional[bool] = None
        confirm_message: Optional[str] = None
        if not error and spec.done_register and car is not None and equipment is not None:
            attempts = max(1, spec.retries) if spec.done_mode == "match" else 1
            for attempt in range(1, attempts + 1):
                if attempt > 1:
                    try:
                        await self._publish(topic, payload)
                    except Exception as e:
                        logger.error(f"[PlcCommand] 重發失敗: {e}")
                        break
                confirmed, confirm_message = await self._wait_done(
                    car, equipment, spec.done_register, baseline_done,
                    mode=spec.done_mode, expected=reg_value, timeout=CONFIRM_TIMEOUT_SEC / attempts,
                    trigger_register=spec.register,
                )
                if confirmed:
                    break
                logger.warning(f"[PlcCommand] {req.command} 第 {attempt}/{attempts} 次未確認: {confirm_message}")
            log_value = f"{log_value} | {confirm_message}"

        if not command_id:
            failure = error or (confirm_message if confirmed is False else None)
            setting_log_id = self._write_setting_log(
                req.command, operator, log_value or error, topic, payload,
                status="FAILED" if failure else "SUCCESS", error_message=failure,
            )

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
            settingLogId=setting_log_id,
            confirmed=confirmed,
            confirmMessage=confirm_message,
            plcValues=self.last_plc_values if confirmed is not None else None,
        )

    @staticmethod
    async def _publish(topic: str, payload: Dict[str, Any]) -> None:
        # 不可 retain，避免 PLC 重新連線時被重複觸發
        await gateway_mqtt_service.publish_message(
            topic, json.dumps(payload, ensure_ascii=False), qos=1, retain=False, raise_on_error=True
        )

    def prepare_cloud_confirmation(self, car_no: Any, end_pos: int, register: str) -> Optional[CloudConfirmation]:
        """雲端指令發送前呼叫：找出設備並記錄完成暫存器目前值；此暫存器沒有完成回報或找不到設備時回傳 None"""
        done_register = DONE_REGISTER_BY_REGISTER.get(register)
        if not done_register:
            return None
        try:
            car, equipment = self._find_target(car_no, end_pos)
        except PlcCommandError as e:
            logger.warning(f"[PlcCommand] 雲端指令無法確認完成: {e}")
            return None
        return CloudConfirmation(car, equipment, done_register, self._read_sensor_value(car, equipment, done_register))

    async def wait_cloud_confirmation(self, confirmation: CloudConfirmation) -> tuple[bool, str]:
        return await self._wait_done(
            confirmation.car, confirmation.equipment, confirmation.done_register, confirmation.baseline
        )

    def _read_sensor_value(self, car: Car, equipment: Equipment, code: Optional[str]) -> Optional[float]:
        if not code:
            return None
        # 優先讀 MQTT 剛收到的記憶體最新值 (DB 為批次寫入，會延遲數秒)
        live = db_config_repo.get_live_sensor_value(equipment.id, code)
        if live is not None:
            return live
        # 結束目前交易以讀到 MQTT 寫入的最新值
        self.db.rollback()
        value = (
            self.db.query(Sensor.sensorValue)
            .filter(Sensor.carId == car.id, Sensor.equipmentId == equipment.id, Sensor.sensorCode == code)
            .scalar()
        )
        return None if value is None else float(value)

    def _poll_done(self, w: _DoneWatcher) -> bool:
        """
        PC 寫入觸發點位後，PLC 完成時會「清空觸發點位」並「回填完成點位」，兩者皆成立才視為完成：
        - flag：完成點位為 1；發送前已為 1 時，須先看到歸零再回到 1，避免把舊值當成完成
        - match：完成點位與寫入值 (expected) 相同 (設定同一個值為冪等，不需歸零)
        - 有 trigger_register 時，另需其值為 0 (讀不到該點位時不阻擋)
        """
        w.done_value = self._read_sensor_value(w.car, w.equipment, w.done_register)
        w.trigger_value = self._read_sensor_value(w.car, w.equipment, w.trigger_register)
        if w.mode == "match":
            w.filled = w.done_value is not None and w.expected is not None and abs(w.done_value - w.expected) < 0.1
        elif w.done_value != 1:
            w.seen_reset = True
            w.filled = False
        else:
            w.filled = w.seen_reset
        if not w.filled:
            return False
        return w.trigger_value is None or w.trigger_value == 0

    @staticmethod
    def _done_message(w: _DoneWatcher, ok: bool, timeout: float) -> str:
        values = f"{w.done_register}={_fmt(w.done_value)}"
        if w.trigger_register:
            values += f", {w.trigger_register}={_fmt(w.trigger_value)}"
        if ok:
            return f"PLC 已完成 ({values})"
        if w.filled and w.trigger_register:
            return f"PLC 已回填 {w.done_register} 但 {w.trigger_register} 未在時限內清空 ({values})"
        return f"PLC 未在時限內回報完成 ({values})"

    @staticmethod
    def _plc_values(w: _DoneWatcher) -> Dict[str, Optional[float]]:
        values: Dict[str, Optional[float]] = {}
        if w.trigger_register:
            values[w.trigger_register] = w.trigger_value
        values[w.done_register] = w.done_value
        return values

    async def _wait_done(
        self,
        car: Car,
        equipment: Equipment,
        done_register: str,
        baseline: Optional[float],
        mode: str = "flag",
        expected: Optional[float] = None,
        timeout: Optional[float] = None,
        trigger_register: Optional[str] = None,
    ) -> tuple[bool, str]:
        timeout = CONFIRM_TIMEOUT_SEC if timeout is None else timeout
        watcher = _DoneWatcher(car, equipment, done_register, baseline, mode, expected, trigger_register)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            await asyncio.sleep(CONFIRM_INTERVAL_SEC)
            if self._poll_done(watcher):
                self.last_plc_values = self._plc_values(watcher)
                return True, self._done_message(watcher, True, timeout)
        self.last_plc_values = self._plc_values(watcher)
        return False, self._done_message(watcher, False, timeout)

    async def execute_batch(
        self,
        command: str,
        value: Optional[float],
        targets: List[Dict[str, Any]],
        operator: str,
        ip_address: Optional[str],
        train_code: Optional[str] = None,
        event: Optional[str] = None,
    ) -> List[BatchTargetResult]:
        """
        對多個端點下同一個設定 (如 8 端點批次設定溫度)：一次發出所有指令，再於同一個迴圈輪流確認各端點，
        確認方式與單端點 execute 相同 (設定值型最多重發給尚未完成者)；每個端點各寫一筆設定紀錄，另寫一筆彙總稽核紀錄。
        :param targets: [{"carNo": 1101, "endPos": 1}, ...]
        :raises PlcCommandError: 指令不支援、設定值不合法，或沒有任何有效目標
        """
        started = time.perf_counter()
        spec = COMMANDS.get(command)
        if spec is None:
            raise PlcCommandError(f"不支援的設定類型: {command}")
        label = SettingType(command).label
        reg_value = spec.to_register_value(value)
        log_value = spec.to_log_value(value, reg_value)

        results: List[BatchTargetResult] = []
        watchers: Dict[int, _DoneWatcher] = {}
        messages: Dict[int, Dict[str, Any]] = {}
        for t in targets:
            car_val = t.get("carNo") or t.get("car_no") or t.get("carVin")
            end_pos = t.get("endPos") or t.get("end_pos")
            if not car_val or not end_pos:
                continue
            result = BatchTargetResult(carNo=None, endPos=int(end_pos))
            results.append(result)
            idx = len(results) - 1
            try:
                car, equipment = self._find_target(int(car_val), int(end_pos))
                code = train_code or str(car.trainCode or "").strip()
                if not train_code and code.upper().startswith("P"):
                    code = code[1:]
                car_vin = str(car.carVin or "")
                result.carNo = int(car_vin) if car_vin.isdigit() else int(str(car.carNo or car_val))
                payload = {
                    "events": event or spec.event,
                    "trainCode": code,
                    "carNo": result.carNo,
                    "endPos": result.endPos,
                    "register": {spec.register: reg_value},
                }
                messages[idx] = {
                    "topic": f"TYMC/AIR/SET/{code}/{result.carNo}/{result.endPos}",
                    "payload": json.dumps(payload, ensure_ascii=False),
                    "qos": 1,
                    "retain": False,
                    "_payload": payload,
                }
                if spec.done_register:
                    watchers[idx] = _DoneWatcher(
                        car, equipment, spec.done_register,
                        self._read_sensor_value(car, equipment, spec.done_register),
                        spec.done_mode, reg_value, spec.register,
                    )
            except PlcCommandError as e:
                result.carNo = int(car_val)
                result.error = str(e)
        if not messages:
            raise PlcCommandError("未找到任何有效之目標設備以執行設定")

        await gateway_mqtt_service.publish_messages(list(messages.values()))

        pending = [i for i in messages if i in watchers]
        attempts = max(1, spec.retries) if spec.done_mode == "match" else 1
        attempt_timeout = CONFIRM_TIMEOUT_SEC / attempts
        # 等待期間請求被中斷 (連線斷開、服務重載) 時，仍要把設定紀錄寫入後再往上拋出
        interrupted: Optional[BaseException] = None
        try:
            for attempt in range(1, attempts + 1):
                if attempt > 1:
                    await gateway_mqtt_service.publish_messages([messages[i] for i in pending])
                deadline = time.monotonic() + attempt_timeout
                while pending and time.monotonic() < deadline:
                    await asyncio.sleep(CONFIRM_INTERVAL_SEC)
                    pending = [i for i in pending if not self._poll_done(watchers[i])]
                if not pending:
                    break
                logger.warning(f"[PlcCommand] 批次 {command} 第 {attempt}/{attempts} 次仍有 {len(pending)} 台未確認")
        except BaseException as e:
            interrupted = e
            logger.warning(f"[PlcCommand] 批次 {command} 等待確認時被中斷 ({type(e).__name__})，先寫入設定紀錄")

        for i, w in watchers.items():
            is_confirmed = i not in pending
            results[i].confirmed = is_confirmed
            results[i].plcValues = self._plc_values(w)
            results[i].message = self._done_message(w, is_confirmed, attempt_timeout)

        log_rows: Dict[int, Dict[str, Any]] = {}
        for i, result in enumerate(results):
            failure = result.error or (result.message if result.confirmed is False else None)
            if i in messages:
                value_text = f"{log_value} | {result.message}" if result.message else log_value
                log_rows[i] = dict(
                    command=command, operator=operator, log_value=value_text,
                    topic=messages[i]["topic"], payload=messages[i]["_payload"],
                    status="FAILED" if failure else "SUCCESS", error_message=failure,
                )
        for i, log_id in self._write_setting_logs(log_rows).items():
            results[i].settingLogId = log_id

        failed = [r for r in results if not r.ok]
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        detail = (
            f"{label} 批次設定{'全數成功' if not failed else '未完全成功'}: 值={log_value}, "
            f"成功={len(results) - len(failed)}/{len(results)}"
            + (f", 失敗端點={', '.join(r.name for r in failed)}" if failed else "")
            + f" | {elapsed_ms}ms"
        )
        try:
            self.audit_log_service.log(
                auditCategory=AuditCategory.SETTING.value,
                action=f"plc_batch_{command.lower()}",
                status="fail" if failed else "success",
                operator=operator,
                ipAddress=ip_address,
                detail=detail[:1000],
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"[PlcCommand] 寫入稽核紀錄失敗: {e}")
        if interrupted is not None:
            raise interrupted
        return results

    def _build_setting_log(
        self,
        command: str,
        operator: str,
        log_value: Optional[str],
        topic: str,
        payload: Dict[str, Any],
        command_id: Optional[str] = None,
        status: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> SettingLog:
        now = get_local_now()
        return SettingLog(
            settingType=command,
            value=log_value,
            operator=operator,
            isNotified=True,
            recordedAt=now,
            topic=topic,
            payload=json.dumps(payload, ensure_ascii=False),
            commandId=command_id,
            status="ACKED" if command_id else status,
            errorMessage=error_message[:500] if error_message else None,
            ackedAt=now if command_id else None,
            finishedAt=now if status and not command_id else None,
        )

    def _write_setting_logs(self, rows: Dict[int, Dict[str, Any]]) -> Dict[int, Optional[int]]:
        """批次寫入多筆設定紀錄 (單一 commit)；回傳 {索引: 紀錄 id}，失敗時全部為 None"""
        if not rows:
            return {}
        try:
            logs = {i: self._build_setting_log(**kw) for i, kw in rows.items()}
            self.db.add_all(logs.values())
            self.db.commit()
            return {i: int(log.id) for i, log in logs.items()}  # type: ignore[arg-type]
        except Exception as e:
            self.db.rollback()
            logger.error(f"[PlcCommand] 批次寫入設定紀錄失敗: {e}")
            return {i: None for i in rows}

    def _write_setting_log(
        self,
        command: str,
        operator: str,
        log_value: Optional[str],
        topic: str,
        payload: Dict[str, Any],
        command_id: Optional[str] = None,
        status: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[int]:
        """command_id 有值 (雲端指令) 時以 ACKED 起始，結果由雲端回報流程更新；否則直接寫入最終 status"""
        try:
            now = get_local_now()
            log = SettingLog(
                settingType=command,
                value=log_value,
                operator=operator,
                isNotified=True,
                recordedAt=now,
                topic=topic,
                payload=json.dumps(payload, ensure_ascii=False),
                commandId=command_id,
                status="ACKED" if command_id else status,
                errorMessage=error_message[:500] if error_message else None,
                ackedAt=now if command_id else None,
                finishedAt=now if status and not command_id else None,
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
