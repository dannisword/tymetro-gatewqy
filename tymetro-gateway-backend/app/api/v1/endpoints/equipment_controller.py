from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import Optional, List
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
from app.services.plc_command_service import PlcCommandService
from app.schemas.plc_command_schema import PlcCommandRequest
from app.api.v1.endpoints.plc_control_controller import _client_ip
from app.core.enums import SettingType
from app.models.user_model import User
from app.models.equipment_model import Equipment
from app.models.car_model import Car
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

@router.post("/set-temperature", response_model=ResponseBase[TemperatureSetResult], summary="設定單端點目標溫度 (與 PLC 控制指令共用 PlcCommandService)")
async def set_temperature(
    request: TemperatureSetRequest,
    req: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    對指定車廂端點發送設定溫度：與其他 PLC 設定指令走同一套流程 (設定紀錄、稽核紀錄、以 D40201 確認 PLC 已套用)。
    """
    try:
        operator_name: str = str(current_user.userName or current_user.account) if current_user else "system"

        resp = await PlcCommandService(db).execute(
            PlcCommandRequest(
                command=SettingType.TEMPERATURE.value,
                carNo=request.carNo,
                endPos=request.endPos,
                trainCode=request.trainCode or "101",
                value=request.targetTemperature,
            ),
            operator=operator_name,
            ip_address=_client_ip(req),
        )

        success = resp.confirmed is True
        result = TemperatureSetResult(
            success=success,
            message=resp.confirmMessage or "",
            targetTemperature=request.targetTemperature,
            confirmedCount=1 if success else 0,
            failedTargets=[] if success else [f"{resp.carNo}-{resp.endPos}端"],
        )

        if not success:
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


@router.post("/batch-set-temperature", response_model=ResponseBase[TemperatureSetResult], summary="批次設定目標溫度 (與 PLC 控制指令共用 PlcCommandService)")
async def batch_set_temperature(
    request: TemperatureBatchSetRequest,
    req: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    對多端點 (預設 8 端點) 發送設定溫度：一次發出、逐台以 D40201 確認 PLC 已套用，並各自留下設定紀錄。
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
                targets.append({"carNo": car_no_val, "endPos": eq.endPos})

        results = await PlcCommandService(db).execute_batch(
            command=SettingType.TEMPERATURE.value,
            value=request.targetTemperature,
            targets=targets,
            operator=operator_name,
            ip_address=_client_ip(req),
            train_code=str(current_train_no),
        )

        failed_names = [r.name for r in results if not r.ok]
        success = not failed_names
        confirmed_count = len(results) - len(failed_names)
        result = TemperatureSetResult(
            success=success,
            message=(
                f"批次溫度設定{'全數成功' if success else '未完全成功'}: 車組={current_train_no}, "
                f"目標={request.targetTemperature}°C, 成功={confirmed_count}/{len(results)}"
                + (f", 失敗端點={', '.join(failed_names)}" if failed_names else "")
            ),
            targetTemperature=request.targetTemperature,
            confirmedCount=confirmed_count,
            failedTargets=failed_names,
        )

        if not success:
            return ResponseUtil.error(
                message=f"批次設定溫度未全數成功: {len(failed_names)} 台設備逾時未確認 ({', '.join(failed_names)})"
            )

        return ResponseUtil.success(
            data=result,
            message=f"{len(results)} 個端點溫度設定成功！目標溫度：{request.targetTemperature}°C (全數 PLC 已確認)"
        )
    except Exception as e:
        logger.error(f"[batch_set_temperature] Exception: {e}", exc_info=True)
        return ResponseUtil.error(message=f"批次設定溫度失敗: {str(e)}")
