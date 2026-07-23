from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from app.api.deps import get_sensor_service, get_current_user
from app.services.sensor_service import SensorService
from app.schemas.sensor_schema import SensorCreate, SensorUpdate, SensorResponse
from app.schemas.response_schema import ResponseBase, ResponseList
from app.utils.response_util import ResponseUtil
from app.models.user_model import User

router = APIRouter()

@router.get("", response_model=ResponseList[SensorResponse], summary="獲取感測器清單")
def get_sensors(
    pageIndex: int = 0,
    pageSize: int = 50,
    propertyName: str = "id",
    order: str = "ASC",
    carId: Optional[int] = None,
    equipmentId: Optional[int] = None,
    sensorType: Optional[str] = None,
    sensorCode: Optional[str] = None,
    sensorName: Optional[str] = None,
    sensorStatus: Optional[str] = None,
    showOnDashboard: Optional[bool] = None,
    isActive: Optional[bool] = None,
    service: SensorService = Depends(get_sensor_service),
    current_user: User = Depends(get_current_user)
):
    items, total = service.get_sensors(
        carId=carId,
        equipmentId=equipmentId,
        sensorType=sensorType,
        sensorCode=sensorCode,
        sensorName=sensorName,
        sensorStatus=sensorStatus,
        showOnDashboard=showOnDashboard,
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

@router.get("/{sensor_id}", response_model=ResponseBase[SensorResponse], summary="獲取單一感測器詳細資訊")
def get_sensor(
    sensor_id: int,
    service: SensorService = Depends(get_sensor_service),
    current_user: User = Depends(get_current_user)
):
    item = service.get_sensor(sensor_id)
    if not item:
        return ResponseUtil.not_found("Sensor not found")
    return ResponseUtil.success(data=item)

@router.post("", response_model=ResponseBase[SensorResponse], summary="建立新感測器")
def create_sensor(
    request: SensorCreate,
    service: SensorService = Depends(get_sensor_service),
    current_user: User = Depends(get_current_user)
):
    try:
        item = service.create_sensor(request)
        return ResponseUtil.success(data=item, message="Sensor created successfully")
    except Exception as e:
        return ResponseUtil.error(message=str(e))

@router.put("/{sensor_id}", response_model=ResponseBase[SensorResponse], summary="更新感測器資訊")
def update_sensor(
    sensor_id: int,
    request: SensorUpdate,
    service: SensorService = Depends(get_sensor_service),
    current_user: User = Depends(get_current_user)
):
    try:
        item = service.update_sensor(sensor_id, request)
        return ResponseUtil.success(data=item, message="Sensor updated successfully")
    except Exception as e:
        return ResponseUtil.error(message=str(e))

@router.delete("/{sensor_id}", response_model=ResponseBase, summary="刪除感測器")
def delete_sensor(
    sensor_id: int,
    service: SensorService = Depends(get_sensor_service),
    current_user: User = Depends(get_current_user)
):
    try:
        service.delete(sensor_id)
        return ResponseUtil.success(message="Sensor deleted successfully")
    except Exception as e:
        return ResponseUtil.error(message=str(e))
