from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.api.deps import get_audit_log_service, get_current_user
from app.services.audit_log_service import AuditLogService
from app.schemas.audit_log_schema import AuditLogCreate, AuditLogResponse
from app.schemas.response_schema import ResponseBase, ResponseList
from app.utils.response_util import ResponseUtil
from app.models.user_model import User

router = APIRouter()

@router.post("", response_model=ResponseBase[AuditLogResponse], summary="新增審計日誌")
def create_audit_log(
    request: AuditLogCreate,
    service: AuditLogService = Depends(get_audit_log_service),
    current_user: User = Depends(get_current_user)
):
    try:
        if not request.operator and current_user:
            request.operator = str(current_user.userName) if current_user.userName else str(current_user.account)
        log_entry = service.create(request)
        return ResponseUtil.success(data=log_entry, message="Audit log created successfully")
    except Exception as e:
        return ResponseUtil.error(message=str(e))

@router.get("", response_model=ResponseList[AuditLogResponse], summary="獲取審計日誌清單")
def get_audit_logs(
    pageIndex: int = Query(0, description="頁碼索引 (0 開始)"),
    pageSize: int = Query(50, description="每頁筆數"),
    propertyName: str = Query("timestamp", description="排序欄位"),
    order: str = Query("DESC", description="排序順序 (ASC/DESC)"),
    auditCategory: Optional[str] = Query(None, description="審計類別 (例如: auth, modbus, schedule, system)"),
    status: Optional[str] = Query(None, description="執行狀態 (success: 成功, fail: 失敗)"),
    operator: Optional[str] = Query(None, description="操作人員帳號/系統模組名稱"),
    service: AuditLogService = Depends(get_audit_log_service),
    current_user: User = Depends(get_current_user)
):
    logs, total = service.get_audit_logs(
        auditCategory=auditCategory,
        status=status,
        operator=operator,
        pageIndex=pageIndex,
        pageSize=pageSize,
        propertyName=propertyName,
        order=order
    )
    return ResponseUtil.list_success(
        data=logs,
        total=total,
        pageIndex=pageIndex,
        pageSize=pageSize
    )

@router.get("/{log_id}", response_model=ResponseBase[AuditLogResponse], summary="獲取單筆審計日誌")
def get_audit_log(
    log_id: int,
    service: AuditLogService = Depends(get_audit_log_service),
    current_user: User = Depends(get_current_user)
):
    log_entry = service.get_by_id(log_id)
    if not log_entry:
        return ResponseUtil.error(message="Audit log not found")
    return ResponseUtil.success(data=log_entry)
