import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.api.deps import get_equipment_service, get_current_user, get_db
from app.services.equipment_service import EquipmentService
from app.schemas.equipment_schema import (
    EquipmentCreate,
    EquipmentUpdate,
    EquipmentResponse,
    TemperatureSetRequest,
    TemperatureBatchSetRequest,
    TemperatureSetResult
)
from app.schemas.response_schema import ResponseBase, ResponseList
from app.utils.response_util import ResponseUtil
from app.services.equipment_manager import equipment_manager
from app.services.gateway_mqtt_service import gateway_mqtt_service
from app.services.audit_log_service import AuditLogService
from app.models.user_model import User
from app.models.equipment_model import Equipment
from app.models.car_model import Car
from app.models.setting_log_model import SettingLog
from app.core.enums import PlcEvent, PlcRegister, SettingTypeEnum
from app.core.logger import logger

router = APIRouter()

@router.get("/states/live", summary="獲取 8 台 (及所有) PFC200 設備實時心跳與連線狀態")
def get_live_equipment_states():
    states = equipment_manager.get_all_equipment_states()
    return ResponseUtil.success(data=states, message="Equipment live states retrieved successfully")

@router.get("", response_model=ResponseList[EquipmentResponse], summary="獲取設備清單")
def get_equipments(
    pageIndex: int = 0,
    pageSize: int = 50,
    propertyName: str = "id",
    order: str = "ASC",
    carId: Optional[int] = None,
    equipmentName: Optional[str] = None,
    equipmentStatus: Optional[str] = None,
    isActive: Optional[bool] = None,
    service: EquipmentService = Depends(get_equipment_service),
    current_user: User = Depends(get_current_user)
):
    items, total = service.get_equipments(
        carId=carId,
        equipmentName=equipmentName,
        equipmentStatus=equipmentStatus,
        isActive=isActive,
        pageIndex=pageIndex,
        pageSize=pageSize,
        propertyName=propertyName,
        order=order
    )
    return ResponseUtil.list_success(
        data=items,
        total=total,
        pageIndex=pageIndex,
        pageSize=pageSize
    )

@router.get("/{equipment_id}", response_model=ResponseBase[EquipmentResponse], summary="獲取單一設備詳細資訊")
def get_equipment(
    equipment_id: int,
    service: EquipmentService = Depends(get_equipment_service),
    current_user: User = Depends(get_current_user)
):
    item = service.get_equipment(equipment_id)
    if not item:
        return ResponseUtil.not_found("Equipment not found")
    return ResponseUtil.success(data=item)

@router.post("", response_model=ResponseBase[EquipmentResponse], summary="建立新設備")
def create_equipment(
    request: EquipmentCreate,
    service: EquipmentService = Depends(get_equipment_service),
    current_user: User = Depends(get_current_user)
):
    try:
        item = service.create_equipment(request)
        return ResponseUtil.success(data=item, message="Equipment created successfully")
    except Exception as e:
        return ResponseUtil.error(message=str(e))

@router.put("/{equipment_id}", response_model=ResponseBase[EquipmentResponse], summary="更新設備資訊")
def update_equipment(
    equipment_id: int,
    request: EquipmentUpdate,
    service: EquipmentService = Depends(get_equipment_service),
    current_user: User = Depends(get_current_user)
):
    try:
        item = service.update_equipment(equipment_id, request)
        return ResponseUtil.success(data=item, message="Equipment updated successfully")
    except Exception as e:
        return ResponseUtil.error(message=str(e))

@router.delete("/{equipment_id}", response_model=ResponseBase, summary="刪除設備")
def delete_equipment(
    equipment_id: int,
    service: EquipmentService = Depends(get_equipment_service),
    current_user: User = Depends(get_current_user)
):
    try:
        service.delete(equipment_id)
        return ResponseUtil.success(message="Equipment deleted successfully")
    except Exception as e:
        return ResponseUtil.error(message=str(e))

async def execute_temperature_setting(
    db: Session,
    train_code: str,
    target_val: float,
    targets: List[Dict[str, Any]],
    operator_name: str = "system",
    is_batch: bool = False
) -> TemperatureSetResult:
    """
    整合獨立的溫度設定核心邏輯 (支援單端點與多端點批次)：
    1. 解析與對齊目標設備 (車號 carVin, 端點 endPos, eq_id)
    2. 記錄 SettingLog
    3. 多端點同時下發 MQTT 指令 (TYMC/AIR/SET/...)
    4. 閉環驗證與重試機制 (檢查 D40200 清零 / D40201 反饋 / D40121 顯示值)
    5. 記錄 AuditLog 並回傳 TemperatureSetResult
    """
    scaled_temp = int(round(target_val * 10))

    # 1. 解析目標設備清單與 DB 對齊
    pending_targets = []
    for t in targets:
        car_val = t.get("carNo") or t.get("car_no") or t.get("carVin")
        ep_val = t.get("endPos") or t.get("end_pos")
        eq_id = t.get("eq_id")

        if not car_val or not ep_val:
            continue

        car_val = int(car_val)
        ep_val = int(ep_val)
        car_str = str(car_val)

        eq_record = (
            db.query(Equipment, Car)
            .join(Car, Equipment.carId == Car.id)
            .filter(
                (Car.carNo == car_val) | (Car.carVin == car_str),
                Equipment.endPos == ep_val,
                Equipment.isActive == True
            )
            .first()
        )
        if eq_record:
            found_eq, found_car = eq_record
            eq_id = str(found_eq.id)
            resolved_car_no = int(found_car.carVin) if found_car.carVin and found_car.carVin.isdigit() else found_car.carNo
        else:
            eq_id = eq_id or f"{car_val}_{ep_val}"
            resolved_car_no = car_val

        pending_targets.append({
            "carNo": resolved_car_no,
            "endPos": ep_val,
            "eq_id": eq_id
        })

    if not pending_targets:
        raise ValueError("未找到任何有效之目標設備以執行設定")

    # 2. 寫入 SettingLog
    log_title = f"{'8端點批次' if is_batch else '單端點'}設定溫度: {target_val}°C (D40200: {scaled_temp})"
    log_topic = f"TYMC/AIR/SET/{train_code}/+/+" if is_batch else f"TYMC/AIR/SET/{train_code}/{pending_targets[0]['carNo']}/{pending_targets[0]['endPos']}"
    try:
        log_entry = SettingLog(
            settingType=SettingTypeEnum.TEMPERATURE.value if hasattr(SettingTypeEnum, "TEMPERATURE") else "TEMPERATURE",
            train=str(train_code),
            carNo=pending_targets[0]["carNo"],
            value=log_title,
            operator=operator_name,
            isNotified=True,
            topic=log_topic,
            payload=json.dumps({
                "targetTemperature": target_val,
                "scaledTemp": scaled_temp,
                "targetsCount": len(pending_targets),
                "targets": [{"carNo": p["carNo"], "endPos": p["endPos"]} for p in pending_targets]
            }, ensure_ascii=False)
        )
        db.add(log_entry)
        db.commit()
    except Exception as log_err:
        logger.warning(f"[execute_temperature_setting] Failed to write setting log: {log_err}")

    # 3. 閉環驗證與重試
    max_retries = 3
    retry_interval = 2.0 if not is_batch else 2.5
    waiting_targets = list(pending_targets)

    for attempt in range(1, max_retries + 1):
        mqtt_messages = []
        for item in waiting_targets:
            topic = f"TYMC/AIR/SET/{train_code}/{item['carNo']}/{item['endPos']}"
            payload = {
                "events": PlcEvent.SET_VALUE.value,
                "trainCode": str(train_code),
                "carNo": item["carNo"],
                "endPos": item["endPos"],
                "register": {
                    PlcRegister.TEMP_SETTING_CMD.value: scaled_temp
                }
            }
            mqtt_messages.append({
                "topic": topic,
                "payload": json.dumps(payload, ensure_ascii=False),
                "qos": 1,
                "retain": True
            })

        if len(mqtt_messages) == 1:
            await gateway_mqtt_service.publish_message(mqtt_messages[0]["topic"], mqtt_messages[0]["payload"])
        else:
            await gateway_mqtt_service.publish_messages(mqtt_messages)

        logger.info(
            f"[execute_temperature_setting] Attempt {attempt}/{max_retries}: Dispatched {target_val}°C to {len(waiting_targets)} PLC(s)."
        )

        await asyncio.sleep(retry_interval)

        still_pending = []
        for item in waiting_targets:
            eq_state = (
                equipment_manager.get_equipment_state(item["eq_id"]) or
                equipment_manager.get_equipment_state(f"{item['carNo']}_{item['endPos']}")
            )
            sensors = eq_state.get("sensors", {}) if eq_state else {}
            d40200_val = sensors.get(PlcRegister.TEMP_SETTING_CMD.value)
            d40201_val = sensors.get(PlcRegister.TEMP_SETTING_FEEDBACK.value)

            # 判定條件：
            # 1. D40200 PLC 設定完成會回傳 0(代表完成)
            # 2. 或 D40201 反饋吻合
            d40201_matched = False
            if d40201_val is not None:
                try:
                    f_val = float(d40201_val)
                    if abs(f_val - scaled_temp) < 0.1 or abs((f_val / 10.0) - target_val) < 0.1 or abs(f_val - target_val) < 0.1:
                        d40201_matched = True
                except (ValueError, TypeError):
                    pass

            is_completed = (
                (d40200_val == 0 or d40200_val == 0.0) or
                d40201_matched
            )

            if not is_completed:
                still_pending.append(item)

        waiting_targets = still_pending
        if not waiting_targets:
            logger.info(f"[execute_temperature_setting] All {len(pending_targets)} PLC(s) verified at attempt {attempt}!")
            break

    confirmed_count = len(pending_targets) - len(waiting_targets)
    failed_names = [f"{p['carNo']}-{p['endPos']}端" for p in waiting_targets]
    all_success = (len(waiting_targets) == 0)

    # 4. 記錄 AuditLog
    audit_service = AuditLogService(db)
    action_name = "batch_set_temperature" if is_batch else "set_temperature"
    detail_msg = (
        f"{'批次' if is_batch else '單端點'}溫度設定{'全數成功' if all_success else '未完全成功'}: "
        f"車組={train_code}, 目標={target_val}°C, 成功={confirmed_count}/{len(pending_targets)}"
        + (f", 失敗端點={', '.join(failed_names)}" if failed_names else "")
    )
    audit_service.log(
        auditCategory="system",
        action=action_name,
        status="success" if all_success else "failure",
        operator=operator_name,
        detail=detail_msg
    )

    return TemperatureSetResult(
        success=all_success,
        message=detail_msg,
        targetTemperature=target_val,
        confirmedCount=confirmed_count,
        failedTargets=failed_names
    )


@router.post("/set-temperature", response_model=ResponseBase[TemperatureSetResult], summary="設定單端點目標溫度 (整合獨立執行)")
async def set_temperature(
    request: TemperatureSetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    對指定車廂端點發送設定溫度 (調用整合獨立核心邏輯)。
    """
    try:
        operator_name: str = str(current_user.userName or current_user.account) if current_user else "system"
        train_code = request.trainCode or "101"
        targets = [{"carNo": request.carNo, "endPos": request.endPos}]

        result = await execute_temperature_setting(
            db=db,
            train_code=train_code,
            target_val=request.targetTemperature,
            targets=targets,
            operator_name=operator_name,
            is_batch=False
        )

        if not result.success:
            return ResponseUtil.error(
                message=f"溫度設定指令已送出，但 PLC 逾時未確認 (目標溫度: {request.targetTemperature}°C)"
            )

        return ResponseUtil.success(
            data=result,
            message="溫度設定成功！PLC 已確認"
        )
    except Exception as e:
        logger.error(f"[set_temperature] Exception: {e}", exc_info=True)
        return ResponseUtil.error(message=f"設定溫度失敗: {str(e)}")


@router.post("/batch-set-temperature", response_model=ResponseBase[TemperatureSetResult], summary="批次設定目標溫度 (調用整合獨立邏輯)")
async def batch_set_temperature(
    request: TemperatureBatchSetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    對多端點 (預設 8 端點) 發送設定溫度 (調用整合獨立核心邏輯)。
    """
    try:
        current_train_no = request.trainCode or "101"
        operator_name: str = str(current_user.userName or current_user.account) if current_user else "system"

        # 整理目標清單：若前端未傳 targets，自動從資料庫抓取全部 8 台 active 設備
        targets = []
        if request.targets and len(request.targets) > 0:
            targets = request.targets
        else:
            active_equipments = (
                db.query(Equipment, Car)
                .join(Car, Equipment.carId == Car.id)
                .filter(Equipment.isActive == True, Car.isActive == True)
                .order_by(Car.carNo, Equipment.endPos)
                .all()
            )
            for eq, car in active_equipments:
                car_no_val = int(car.carVin) if car.carVin and car.carVin.isdigit() else (car.carNo or 0)
                targets.append({"carNo": car_no_val, "endPos": eq.endPos, "eq_id": str(eq.id)})

        result = await execute_temperature_setting(
            db=db,
            train_code=str(current_train_no),
            target_val=request.targetTemperature,
            targets=targets,
            operator_name=operator_name,
            is_batch=True
        )

        if not result.success:
            return ResponseUtil.error(
                message=f"批次設定溫度未全數成功: {len(result.failedTargets)} 台設備逾時未確認 ({', '.join(result.failedTargets)})"
            )

        return ResponseUtil.success(
            data=result,
            message=f"8 個端點溫度設定成功！全數 PLC 已確認"
        )
    except Exception as e:
        logger.error(f"[batch_set_temperature] Exception: {e}", exc_info=True)
        return ResponseUtil.error(message=f"批次設定溫度失敗: {str(e)}")
