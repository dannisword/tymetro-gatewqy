from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from app.api.deps import get_schedule_service, get_current_user
from app.services.schedule_service import ScheduleService
from app.schemas.schedule_schema import ScheduleCreate, ScheduleUpdate, ScheduleResponse
from app.schemas.response_schema import ResponseBase, ResponseList
from app.utils.response_util import ResponseUtil
from app.models.user_model import User
from app.scheduler.engine import scheduler_engine
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.car_model import Car
from app.core.config import settings
from app.core.logger import logger
from app.utils.http_util import HttpUtil

router = APIRouter()

class ScheduleSwitch(BaseModel):
    enabled: bool

def _sync_cars_schedule_enabled(db: Session, enabled: bool) -> dict:
    """呼叫中心端 PUT /api/v1/cars/{id}，將本機所有車廂的 isScheduleEnabled 更新為 enabled；失敗不丟例外，回傳結果摘要"""
    token = HttpUtil.get_central_backend_token()
    if not token:
        return {"synced": 0, "failed": [], "error": "無法登入中心後端取得 Token"}
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    base = settings.TYMETRO_BACKEND_URL.rstrip("/")
    synced, failed = 0, []
    for (car_id,) in db.query(Car.id).all():
        resp = HttpUtil.put(f"{base}/api/v1/cars/{car_id}", data={"isScheduleEnabled": enabled}, headers=headers)
        if resp.get("success"):
            synced += 1
        else:
            failed.append({"carId": car_id, "message": resp.get("message")})
    return {"synced": synced, "failed": failed}

async def _sync_and_log(db: Session, enabled: bool) -> dict:
    # HttpUtil 為同步阻塞呼叫，放到 thread 執行避免卡住 event loop
    result = await run_in_threadpool(_sync_cars_schedule_enabled, db, enabled)
    if result.get("error") or result["failed"]:
        logger.warning(f"[schedules] 同步中心端 cars.isScheduleEnabled 未完全成功: {result}")
    return result

@router.post("/cloud-sync", response_model=ResponseBase, summary="同步中心端 cars.isScheduleEnabled (排程啟用/停止狀態)")
async def sync_schedule_enabled(request: ScheduleSwitch, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await _sync_and_log(db, request.enabled)
    return ResponseUtil.success(data={"enabled": request.enabled, "centralSync": result}, message="已同步中心端排程狀態")

@router.post("", response_model=ResponseBase[ScheduleResponse], summary="新增排程")
def create_schedule(
    request: ScheduleCreate, 
    service: ScheduleService = Depends(get_schedule_service),
    current_user: User = Depends(get_current_user)
):
    try:
        schedule = service.create(request)
        scheduler_engine.reload_schedule(int(schedule.id))  # type: ignore
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
    service: ScheduleService = Depends(get_schedule_service)
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
async def update_schedule(
    schedule_id: int, 
    request: ScheduleUpdate, 
    service: ScheduleService = Depends(get_schedule_service),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    schedule = service.update(schedule_id, request)
    scheduler_engine.reload_schedule(schedule_id)
    refreshed = service.get_by_id(schedule_id)
    if request.isActive is not None:
        # 啟用/停止排程時，同步中心端 cars.isScheduleEnabled
        await _sync_and_log(db, request.isActive)
    return ResponseUtil.success(data=refreshed, message="Schedule updated successfully")

@router.delete("/{schedule_id}", response_model=ResponseBase, summary="刪除排程")
def delete_schedule(
    schedule_id: int, 
    service: ScheduleService = Depends(get_schedule_service),
    current_user: User = Depends(get_current_user)
):
    service.delete(schedule_id)
    scheduler_engine.reload_schedule(schedule_id)
    return ResponseUtil.success(message="Schedule deleted successfully")

