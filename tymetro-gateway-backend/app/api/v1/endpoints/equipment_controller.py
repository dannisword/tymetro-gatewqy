from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from app.api.deps import get_equipment_service, get_current_user
from app.services.equipment_service import EquipmentService
from app.schemas.equipment_schema import EquipmentCreate, EquipmentUpdate, EquipmentResponse
from app.schemas.response_schema import ResponseBase, ResponseList
from app.utils.response_util import ResponseUtil
from app.services.equipment_manager import equipment_manager
from app.models.user_model import User

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
