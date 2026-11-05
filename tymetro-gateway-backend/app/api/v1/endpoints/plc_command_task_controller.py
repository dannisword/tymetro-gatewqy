from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user_model import User
from app.schemas.response_schema import ResponseList
from app.services.plc_command_task_service import PlcCommandTaskService
from app.utils.response_util import ResponseUtil

router = APIRouter()


@router.get("", response_model=ResponseList, summary="查詢 PLC 設定重試佇列 (plc_command_tasks)")
def get_plc_command_tasks(
    command: Optional[str] = Query(None, description="設定類型 (如 TEMPERATURE)"),
    carNo: Optional[int] = Query(None, description="車號"),
    endPos: Optional[int] = Query(None, description="端點位置 (1端或2端)"),
    status: Optional[str] = Query(None, description="PENDING / SUCCESS / FAILED / SUPERSEDED / EXPIRED"),
    startTime: Optional[datetime] = Query(None, description="建立時間起"),
    endTime: Optional[datetime] = Query(None, description="建立時間迄"),
    pageIndex: int = Query(0, ge=0),
    pageSize: int = Query(50, ge=1, le=500),
    order: str = Query("DESC", description="依建立時間排序 ASC / DESC"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = PlcCommandTaskService(db).query_tasks(
        command=command, carNo=carNo, endPos=endPos, status=status,
        startTime=startTime, endTime=endTime,
        pageIndex=pageIndex, pageSize=pageSize, order=order,
    )
    return ResponseUtil.list_success(data=items, total=total, pageIndex=pageIndex, pageSize=pageSize)
