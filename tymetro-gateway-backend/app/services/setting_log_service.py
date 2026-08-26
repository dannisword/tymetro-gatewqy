from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.setting_log_model import SettingLog
from app.schemas.setting_log_schema import SettingLogCreate, SettingLogUpdate
from app.repositories.setting_log_repository import SettingLogRepository
from app.services.base_service import BaseService

class SettingLogService(BaseService[SettingLog, SettingLogCreate, SettingLogUpdate]):
    repo: SettingLogRepository

    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = SettingLogRepository(db)

    def get_setting_logs(
        self,
        settingType: Optional[str] = None,
        operator: Optional[str] = None,
        isNotified: Optional[bool] = None,
        startTime: Optional[datetime] = None,
        endTime: Optional[datetime] = None,
        pageIndex: int = 0,
        pageSize: int = 50,
        propertyName: str = "id",
        order: str = "DESC"
    ):
        """根據參數過濾設定紀錄列表 (含總數)"""
        expressions = []
        if settingType:
            expressions.append(lambda x: x.settingType.like(f"%{settingType}%"))
        if operator:
            expressions.append(lambda x: x.operator.like(f"%{operator}%"))
        if isNotified is not None:
            expressions.append(lambda x: x.isNotified == isNotified)
        if startTime:
            expressions.append(lambda x: x.recordedAt >= startTime)
        if endTime:
            expressions.append(lambda x: x.recordedAt <= endTime)

        records, total = self.filter_with_pageable(
            *expressions,
            pageIndex=pageIndex,
            pageSize=pageSize,
            propertyName=propertyName,
            order=order
        )

        return records, total
