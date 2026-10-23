from fastapi import APIRouter, Query, Depends
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.user_model import User
from app.models.equipment_event_model import EquipmentEvent
from app.schemas.response_schema import ResponseList
from app.utils.response_util import ResponseUtil

router = APIRouter()

@router.get("", response_model=ResponseList, summary="查詢設備狀態/警報變動事件紀錄")
def get_equipment_events(
    carVin: Optional[str] = Query(None, description="車廂唯一代碼 (如 1101)"),
    endPos: Optional[int] = Query(None, description="端點位置 (1端或2端)"),
    registerCode: Optional[str] = Query(None, description="暫存器代碼 (如 D40016)"),
    tagName: Optional[str] = Query(None, description="點位標籤 (如 CMB1_FAULT)"),
    eventType: Optional[str] = Query(None, description="事件類別 (ALARM / STATUS ...)"),
    action: Optional[str] = Query(None, description="動作 (TRIGGERED / CLEARED / CHANGED / RESTORED)"),
    startTime: Optional[datetime] = Query(None, description="開始時間"),
    endTime: Optional[datetime] = Query(None, description="結束時間"),
    pageIndex: int = Query(0, ge=0),
    pageSize: int = Query(50, ge=1, le=500),
    order: str = Query("DESC", description="依發生時間排序 ASC / DESC"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(EquipmentEvent)
    if carVin:
        query = query.filter(EquipmentEvent.carVin == carVin)
    if endPos is not None:
        query = query.filter(EquipmentEvent.endPos == endPos)
    if registerCode:
        query = query.filter(EquipmentEvent.registerCode == registerCode.upper())
    if tagName:
        query = query.filter(EquipmentEvent.tagName == tagName)
    if eventType:
        query = query.filter(EquipmentEvent.eventType == eventType)
    if action:
        query = query.filter(EquipmentEvent.action == action)
    if startTime:
        query = query.filter(EquipmentEvent.triggeredAt >= startTime)
    if endTime:
        query = query.filter(EquipmentEvent.triggeredAt <= endTime)

    total = query.count()
    ordering = EquipmentEvent.triggeredAt.asc() if order.upper() == "ASC" else EquipmentEvent.triggeredAt.desc()
    rows = query.order_by(ordering, EquipmentEvent.id.desc()).offset(pageIndex * pageSize).limit(pageSize).all()

    items = [{
        "id": r.id,
        "carVin": r.carVin,
        "carNo": r.carNo,
        "endPos": r.endPos,
        "registerCode": r.registerCode,
        "bitIndex": r.bitIndex,
        "tagName": r.tagName,
        "tagDesc": r.tagDesc,
        "eventType": r.eventType,
        "prevValue": r.prevValue,
        "newValue": r.newValue,
        "action": r.action,
        "isConfirmed": r.isConfirmed,
        "triggeredAt": r.triggeredAt.isoformat() if r.triggeredAt else None,
    } for r in rows]

    return ResponseUtil.list_success(data=items, total=total, pageIndex=pageIndex, pageSize=pageSize)
