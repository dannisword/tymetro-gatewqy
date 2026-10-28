from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.setting_log_model import SettingLog
from app.schemas.audit_log_schema import AuditLogCreate, AuditLogUpdate
from app.repositories.setting_log_repository import SettingLogRepository
from app.services.base_service import BaseService
from app.utils.datetime_util import get_local_now

class AuditLogService(BaseService[SettingLog, AuditLogCreate, AuditLogUpdate]):
    """審計日誌服務：審計紀錄寫入 setting_logs (auditCategory 不為 NULL 者即為審計紀錄)"""
    repo: SettingLogRepository

    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = SettingLogRepository(db)

    def get_audit_logs(
        self, 
        auditCategory: Optional[str] = None,
        status: Optional[str] = None,
        operator: Optional[str] = None,
        pageIndex: int = 0, 
        pageSize: int = 50, 
        propertyName: str = "timestamp",
        order: str = "DESC"
    ):
        """根據參數過濾審計日誌列表 (含總數)"""
        expressions = [lambda x: x.auditCategory.isnot(None)]
        if auditCategory:
            expressions.append(lambda x: x.auditCategory == auditCategory)
        if status:
            expressions.append(lambda x: x.status == status)
        if operator:
            expressions.append(lambda x: x.operator.like(f"%{operator}%"))
            
        logs, total = self.filter_with_pageable(
            *expressions,
            pageIndex=pageIndex,
            pageSize=pageSize,
            propertyName=propertyName,
            order=order
        )
            
        return logs, total

    def create(self, obj_in: AuditLogCreate) -> SettingLog:  # type: ignore[override]
        """新增審計紀錄 (寫入 setting_logs，設定類型沿用 action)"""
        entry = SettingLog(
            settingType=obj_in.action[:50],
            auditCategory=obj_in.auditCategory,
            action=obj_in.action,
            status=obj_in.status,
            operator=obj_in.operator,
            ipAddress=obj_in.ipAddress,
            detail=obj_in.detail,
            isNotified=False,
            recordedAt=get_local_now(),
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def log(
        self,
        auditCategory: str,
        action: str,
        status: str = "success",
        operator: Optional[str] = None,
        ipAddress: Optional[str] = None,
        detail: Optional[str] = None
    ) -> SettingLog:
        """快速記錄審計日誌"""
        log_data = AuditLogCreate(
            auditCategory=auditCategory,
            action=action,
            status=status,
            operator=operator,
            ipAddress=ipAddress,
            detail=detail
        )
        return self.create(log_data)
