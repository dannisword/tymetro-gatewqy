from fastapi import APIRouter, Query, status
from typing import Optional, List, Dict, Any
from app.repositories.sensor_history_repository import sensor_history_repo
from app.utils.response_util import ResponseUtil

router = APIRouter()

@router.get("", summary="查詢感測器歷史數據 (支援條件篩選與分頁)")
def get_sensor_histories(
    sensor_code: Optional[str] = Query(None, description="感測器代碼 (如 D40001)"),
    car_vin: Optional[str] = Query(None, description="車廂唯一代碼 (如 1101)"),
    equipment_name: Optional[str] = Query(None, description="設備名稱 (如 PFC11011)"),
    limit: int = Query(100, ge=1, le=1000, description="每頁筆數"),
    offset: int = Query(0, ge=0, description="偏移量 (頁碼索引)")
):
    records = sensor_history_repo.get_history(
        sensor_code=sensor_code,
        car_vin=car_vin,
        equipment_name=equipment_name,
        limit=limit,
        offset=offset
    )
    result = []
    for r in records:
        result.append({
            "id": r.id,
            "car_vin": r.carVin,
            "car_no": r.carNo,
            "end_pos": r.endPos,
            "sensor_code": r.sensorCode,
            "sensor_value": r.sensorValue,
            "recorded_at": r.recordedAt.isoformat() if r.recordedAt else None,
            "sensor_name": r.sensorName,
            "sensor_unit": r.sensorUnit,
            "equipment_name": r.equipmentName
        })
    return ResponseUtil.success(data=result, message=f"Retrieved {len(result)} sensor history records.")

@router.delete("/clear-all", summary="清空所有感測器歷史紀錄 (Clear All Sensor Histories)")
@router.delete("", summary="清空所有感測器歷史紀錄 (Clear All Sensor Histories)")
def clear_all_sensor_histories():
    num_deleted = sensor_history_repo.clear_all()
    return ResponseUtil.success(
        data={"cleared_count": num_deleted},
        message=f"Successfully cleared all {num_deleted} sensor history records."
    )
