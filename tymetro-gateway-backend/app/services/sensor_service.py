from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.sensor_model import Sensor
from app.schemas.sensor_schema import SensorCreate, SensorUpdate
from app.repositories.sensor_repository import SensorRepository
from app.services.base_service import BaseService

class SensorService(BaseService[Sensor, SensorCreate, SensorUpdate]):
    repo: SensorRepository

    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = SensorRepository(db)

    def get_sensor(self, id: int) -> Optional[Sensor]:
        return super().get_by_id(id)

    def get_sensors(
        self,
        carId: Optional[int] = None,
        equipmentId: Optional[int] = None,
        sensorType: Optional[str] = None,
        sensorCode: Optional[str] = None,
        sensorName: Optional[str] = None,
        sensorStatus: Optional[str] = None,
        showOnDashboard: Optional[bool] = None,
        isActive: Optional[bool] = None,
        pageIndex: int = 0,
        pageSize: int = 50,
        propertyName: str = "id",
        order: str = "ASC"
    ) -> Tuple[List[Sensor], int]:
        expressions = []
        if carId is not None:
            expressions.append(lambda x: x.carId == carId)
        if equipmentId is not None:
            expressions.append(lambda x: x.equipmentId == equipmentId)
        if sensorType:
            expressions.append(lambda x: x.sensorType == sensorType)
        if sensorCode:
            expressions.append(lambda x: x.sensorCode.like(f"%{sensorCode}%"))
        if sensorName:
            expressions.append(lambda x: x.sensorName.like(f"%{sensorName}%"))
        if sensorStatus:
            expressions.append(lambda x: x.sensorStatus == sensorStatus)
        if showOnDashboard is not None:
            expressions.append(lambda x: x.showOnDashboard == showOnDashboard)
        if isActive is not None:
            expressions.append(lambda x: x.isActive == isActive)

        return self.filter_with_pageable(
            *expressions,
            pageIndex=pageIndex,
            pageSize=pageSize,
            propertyName=propertyName,
            order=order
        )

    def create_sensor(self, schema: SensorCreate) -> Sensor:
        return super().create(schema)

    def update_sensor(self, id: int, schema: SensorUpdate) -> Sensor:
        return super().update(id, schema)
