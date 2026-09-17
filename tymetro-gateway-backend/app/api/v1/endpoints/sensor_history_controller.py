from fastapi import APIRouter, Query, status, Depends
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.user_model import User
from app.schemas.response_schema import ResponseBase, ResponseList
from app.schemas.sensor_history_schema import SensorHistoryResponse
from app.repositories.sensor_history_repository import sensor_history_repo
from app.utils.response_util import ResponseUtil

router = APIRouter()

@router.get("/trend", response_model=ResponseBase, summary="查詢感測器歷史趨勢數據 (Trend)")
def get_sensor_trend(
    sensor_code: str = Query(..., alias="sensorCode", description="感測器代碼 (如 D40001)"),
    carVin: str = Query(..., description="車廂唯一代碼 (如 1101)"),
    endPos: Optional[int] = Query(None, description="端點位置 (1端或2端)"),
    startTime: Optional[datetime] = Query(None, description="開始時間"),
    endTime: Optional[datetime] = Query(None, description="結束時間"),
    limit: int = Query(2000, description="限制筆數"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.models.sensor_history_model import SensorHistory

    # 1. 查詢歷史數據
    query = db.query(SensorHistory).filter(
        SensorHistory.sensorCode == sensor_code,
        SensorHistory.carVin == carVin
    )
    if endPos is not None:
        query = query.filter(SensorHistory.endPos == endPos)

    if startTime:
        query = query.filter(SensorHistory.recordedAt >= startTime)
    if endTime:
        query = query.filter(SensorHistory.recordedAt <= endTime)

    # 取最新的 limit 筆，所以照 recordedAt.desc() 取，之後再反轉
    records = query.order_by(SensorHistory.recordedAt.desc()).limit(limit).all()
    records = list(reversed(records))

    result = {
        "sensor_code": sensor_code,
        "car_vin": carVin,
        "end_pos": endPos,
        "points": [
            {
                "timestamp": r.recordedAt.isoformat() + "Z" if r.recordedAt else None,
                "value": r.sensorValue
            } for r in records
        ]
    }
    return ResponseUtil.success(data=result)


@router.get("", response_model=ResponseList[SensorHistoryResponse], summary="查詢感測器歷史數據 (支援條件篩選與分頁)")
def get_sensor_histories(
    pageIndex: int = Query(0, ge=0, description="頁碼索引 (0 開始)"),
    pageSize: int = Query(50, ge=1, le=1000, description="每頁筆數"),
    propertyName: str = Query("recordedAt", description="排序欄位"),
    order: str = Query("DESC", description="排序順序 (ASC/DESC)"),
    sensorCode: Optional[str] = Query(None, description="感測器代碼 (如 D40001)"),
    sensor_code: Optional[str] = Query(None, description="感測器代碼 (相容舊參數)"),
    carVin: Optional[str] = Query(None, description="車廂唯一代碼 (如 1101)"),
    car_vin: Optional[str] = Query(None, description="車廂唯一代碼 (相容舊參數)"),
    equipmentName: Optional[str] = Query(None, description="設備名稱 (如 PFC11011)"),
    equipment_name: Optional[str] = Query(None, description="設備名稱 (相容舊參數)"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="每頁筆數 (相容舊版參數)"),
    offset: Optional[int] = Query(None, ge=0, description="偏移量 (相容舊版參數)"),
    db: Session = Depends(get_db)
):
    target_sensor_code = sensorCode or sensor_code
    target_car_vin = carVin or car_vin
    target_equipment_name = equipmentName or equipment_name

    actual_page_size = limit if limit is not None else pageSize
    actual_page_index = (offset // actual_page_size) if offset is not None else pageIndex

    records, total = sensor_history_repo.get_history(
        sensor_code=target_sensor_code,
        car_vin=target_car_vin,
        equipment_name=target_equipment_name,
        page_index=actual_page_index,
        page_size=actual_page_size,
        property_name=propertyName,
        order=order,
        limit=limit,
        offset=offset,
        db_session=db
    )

    items = [SensorHistoryResponse.model_validate(r) for r in records]
    return ResponseUtil.list_success(
        data=items,
        total=total,
        pageIndex=actual_page_index,
        pageSize=actual_page_size
    )

@router.delete("/clear-all", summary="清空所有感測器歷史紀錄 (Clear All Sensor Histories)")
@router.delete("", summary="清空所有感測器歷史紀錄 (Clear All Sensor Histories)")
def clear_all_sensor_histories():
    num_deleted = sensor_history_repo.clear_all()
    return ResponseUtil.success(
        data={"cleared_count": num_deleted},
        message=f"Successfully cleared all {num_deleted} sensor history records."
    )
