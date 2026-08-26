from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime
from app.api.deps import get_setting_log_service, get_current_user
from app.services.setting_log_service import SettingLogService
from app.schemas.setting_log_schema import SettingLogCreate, SettingLogResponse
from app.schemas.response_schema import ResponseBase, ResponseList
from app.utils.response_util import ResponseUtil
from app.models.user_model import User

router = APIRouter()

@router.post("", response_model=ResponseBase[SettingLogResponse], summary="新增設定紀錄")
def create_setting_log(
    request: SettingLogCreate,
    service: SettingLogService = Depends(get_setting_log_service),
    current_user: User = Depends(get_current_user)
):
    try:
        # 如果 request 中未提供操作人員，則自動帶入當前登入者名稱或帳號
        if not request.operator and current_user:
            request.operator = str(current_user.userName) if current_user.userName else str(current_user.account)
            
        record = service.create(request)
        return ResponseUtil.success(data=record, message="Setting log created successfully")
    except Exception as e:
        return ResponseUtil.error(message=str(e))

@router.get("", response_model=ResponseList[SettingLogResponse], summary="查詢設定紀錄 (支援分頁與多條件篩選)")
def get_setting_logs(
    pageIndex: int = Query(0, description="頁碼索引 (0 開始)"),
    pageSize: int = Query(50, description="每頁筆數"),
    propertyName: str = Query("id", description="排序欄位"),
    order: str = Query("DESC", description="排序順序 (ASC/DESC)"),
    settingType: Optional[str] = Query(None, description="設定類型"),
    operator: Optional[str] = Query(None, description="操作人員"),
    isNotified: Optional[bool] = Query(None, description="是否已通知"),
    startTime: Optional[datetime] = Query(None, description="開始時間"),
    endTime: Optional[datetime] = Query(None, description="結束時間"),
    service: SettingLogService = Depends(get_setting_log_service),
    current_user: User = Depends(get_current_user)
):
    records, total = service.get_setting_logs(
        settingType=settingType,
        operator=operator,
        isNotified=isNotified,
        startTime=startTime,
        endTime=endTime,
        pageIndex=pageIndex,
        pageSize=pageSize,
        propertyName=propertyName,
        order=order
    )
    return ResponseUtil.list_success(
        data=records,
        total=total,
        pageIndex=pageIndex,
        pageSize=pageSize
    )
