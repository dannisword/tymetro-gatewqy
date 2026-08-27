from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import ColumnElement
from app.models.sensor_model import Sensor
from app.models.car_model import Car
from app.models.equipment_model import Equipment
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
        carVin: Optional[str] = None,
        equipmentId: Optional[int] = None,
        endPos: Optional[str] = None,
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
        need_car_join = carVin is not None
        need_equipment_join = endPos is not None

        if need_car_join or need_equipment_join:
            return self._get_sensors_with_join(
                carId=carId,
                carVin=carVin,
                equipmentId=equipmentId,
                endPos=endPos,
                sensorType=sensorType,
                sensorCode=sensorCode,
                sensorName=sensorName,
                sensorStatus=sensorStatus,
                showOnDashboard=showOnDashboard,
                isActive=isActive,
                pageIndex=pageIndex,
                pageSize=pageSize,
                propertyName=propertyName,
                order=order,
            )

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

        items, total = self.filter_with_pageable(
            *expressions,
            pageIndex=pageIndex,
            pageSize=pageSize,
            propertyName=propertyName,
            order=order
        )
        self._enrich_sensors(items)
        return items, total

    def _get_sensors_with_join(
        self,
        carId: Optional[int],
        carVin: Optional[str],
        equipmentId: Optional[int],
        endPos: Optional[str],
        sensorType: Optional[str],
        sensorCode: Optional[str],
        sensorName: Optional[str],
        sensorStatus: Optional[str],
        showOnDashboard: Optional[bool],
        isActive: Optional[bool],
        pageIndex: int,
        pageSize: int,
        propertyName: str,
        order: str,
    ) -> Tuple[List[Sensor], int]:
        query = self.db.query(Sensor)

        if carVin is not None:
            query = query.join(Car, Sensor.carId == Car.id).filter(Car.carVin == carVin)
        if endPos is not None:
            query = query.join(Equipment, Sensor.equipmentId == Equipment.id).filter(Equipment.endPos == endPos)

        if carId is not None:
            query = query.filter(Sensor.carId == carId)
        if equipmentId is not None:
            query = query.filter(Sensor.equipmentId == equipmentId)
        if sensorType:
            query = query.filter(Sensor.sensorType == sensorType)
        if sensorCode:
            query = query.filter(Sensor.sensorCode.like(f"%{sensorCode}%"))
        if sensorName:
            query = query.filter(Sensor.sensorName.like(f"%{sensorName}%"))
        if sensorStatus:
            query = query.filter(Sensor.sensorStatus == sensorStatus)
        if showOnDashboard is not None:
            query = query.filter(Sensor.showOnDashboard == showOnDashboard)
        if isActive is not None:
            query = query.filter(Sensor.isActive == isActive)

        total = query.count()

        if propertyName and hasattr(Sensor, propertyName):
            col = getattr(Sensor, propertyName)
            query = query.order_by(col.asc() if order.upper() == "ASC" else col.desc())
        else:
            query = query.order_by(Sensor.id.desc())

        skip = pageIndex * pageSize
        items = query.offset(skip).limit(pageSize).all()
        self._enrich_sensors(items)
        return items, total

    def _enrich_sensors(self, sensors: List[Sensor]) -> None:
        """批次查詢 carVin 與 endPos，回填至 Sensor 物件上。"""
        if not sensors:
            return

        # 收集所有 car_id / equipment_id
        car_ids = {s.carId for s in sensors if s.carId is not None}
        equipment_ids = {s.equipmentId for s in sensors if s.equipmentId is not None}

        # 批次查詢
        car_map: dict[int, str | None] = {}
        if car_ids:
            cars = self.db.query(Car.id, Car.carVin).filter(Car.id.in_(car_ids)).all()
            car_map = {c.id: c.carVin for c in cars}

        equipment_map: dict[int, int | None] = {}
        if equipment_ids:
            equips = self.db.query(Equipment.id, Equipment.endPos).filter(Equipment.id.in_(equipment_ids)).all()
            equipment_map = {e.id: e.endPos for e in equips}

        # 回填
        for s in sensors:
            s.carVin = car_map.get(s.carId)  # type: ignore[attr-defined]
            s.endPos = equipment_map.get(s.equipmentId) if s.equipmentId is not None else None  # type: ignore[attr-defined]

    def create_sensor(self, schema: SensorCreate) -> Sensor:
        return super().create(schema)

    def update_sensor(self, id: int, schema: SensorUpdate) -> Sensor:
        return super().update(id, schema)
