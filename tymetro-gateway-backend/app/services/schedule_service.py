from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.schedule_model import Schedule
from app.schemas.schedule_schema import ScheduleCreate, ScheduleUpdate
from app.repositories.schedule_repository import ScheduleRepository
from app.services.base_service import BaseService

class ScheduleService(BaseService[Schedule, ScheduleCreate, ScheduleUpdate]):
    repo: ScheduleRepository

    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = ScheduleRepository(db)

    def get_schedules(
        self, 
        scheduleType: Optional[str] = None,
        isActive: Optional[bool] = None,
        pageIndex: int = 0, 
        pageSize: int = 50, 
        propertyName: str = "id",
        order: str = "DESC"
    ):
        """根據參數過濾排程列表 (含總數)"""
        expressions = []
        if scheduleType:
            expressions.append(lambda x: x.scheduleType == scheduleType)
        if isActive is not None:
            expressions.append(lambda x: x.isActive == isActive)
            
        schedules, total = self.filter_with_pageable(
            *expressions,
            pageIndex=pageIndex,
            pageSize=pageSize,
            propertyName=propertyName,
            order=order
        )
            
        return schedules, total
