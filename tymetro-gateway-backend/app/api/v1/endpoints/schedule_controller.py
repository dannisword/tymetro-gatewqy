from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from app.api.deps import get_schedule_service, get_current_user
from app.services.schedule_service import ScheduleService
from app.schemas.schedule_schema import ScheduleCreate, ScheduleUpdate, ScheduleResponse
from app.schemas.response_schema import ResponseBase, ResponseList
from app.utils.response_util import ResponseUtil
from app.models.user_model import User

router = APIRouter()

@router.post("", response_model=ResponseBase[ScheduleResponse], summary="新增排程")
def create_schedule(
    request: ScheduleCreate, 
    service: ScheduleService = Depends(get_schedule_service),
    current_user: User = Depends(get_current_user)
):
    try:
        schedule = service.create(request)
        return ResponseUtil.success(data=schedule, message="Schedule created successfully")
    except Exception as e:
        return ResponseUtil.error(message=str(e))

@router.get("", response_model=ResponseList[ScheduleResponse], summary="獲取排程清單")
def get_schedules(
    pageIndex: int = 0, 
    pageSize: int = 50, 
    propertyName: str = "id",
    order: str = "DESC",
    scheduleType: Optional[str] = None,
    isActive: Optional[bool] = None,
    service: ScheduleService = Depends(get_schedule_service),
    current_user: User = Depends(get_current_user)
):
    schedules, total = service.get_schedules(
        scheduleType=scheduleType, 
        isActive=isActive,
        pageIndex=pageIndex, 
        pageSize=pageSize,
        propertyName=propertyName,
        order=order
    )
    return ResponseUtil.list_success(
        data=schedules, 
        total=total,
        pageIndex=pageIndex,
        pageSize=pageSize
    )

@router.get("/{schedule_id}", response_model=ResponseBase[ScheduleResponse], summary="獲取排程詳細資訊")
def get_schedule(
    schedule_id: int, 
    service: ScheduleService = Depends(get_schedule_service),
    current_user: User = Depends(get_current_user)
):
    schedule = service.get_by_id(schedule_id)
    return ResponseUtil.success(data=schedule)

@router.put("/{schedule_id}", response_model=ResponseBase[ScheduleResponse], summary="更新排程資訊")
def update_schedule(
    schedule_id: int, 
    request: ScheduleUpdate, 
    service: ScheduleService = Depends(get_schedule_service),
    current_user: User = Depends(get_current_user)
):
    schedule = service.update(schedule_id, request)
    return ResponseUtil.success(data=schedule, message="Schedule updated successfully")

@router.delete("/{schedule_id}", response_model=ResponseBase, summary="刪除排程")
def delete_schedule(
    schedule_id: int, 
    service: ScheduleService = Depends(get_schedule_service),
    current_user: User = Depends(get_current_user)
):
    service.delete(schedule_id)
    return ResponseUtil.success(message="Schedule deleted successfully")
