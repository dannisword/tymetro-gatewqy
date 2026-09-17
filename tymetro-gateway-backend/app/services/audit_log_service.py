from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.audit_log_model import AuditLog
from app.schemas.audit_log_schema import AuditLogCreate, AuditLogUpdate
from app.repositories.audit_log_repository import AuditLogRepository
from app.services.base_service import BaseService

class AuditLogService(BaseService[AuditLog, AuditLogCreate, AuditLogUpdate]):
    repo: AuditLogRepository

    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = AuditLogRepository(db)

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
        expressions = []
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

    def log(
        self,
        auditCategory: str,
        action: str,
        status: str = "success",
        operator: Optional[str] = None,
        ipAddress: Optional[str] = None,
        detail: Optional[str] = None
    ) -> AuditLog:
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
