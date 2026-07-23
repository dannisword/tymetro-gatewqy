from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.equipment_model import Equipment
from app.schemas.equipment_schema import EquipmentCreate, EquipmentUpdate
from app.repositories.equipment_repository import EquipmentRepository
from app.services.base_service import BaseService

class EquipmentService(BaseService[Equipment, EquipmentCreate, EquipmentUpdate]):
    repo: EquipmentRepository

    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = EquipmentRepository(db)

    def get_equipment(self, id: int) -> Optional[Equipment]:
        return super().get_by_id(id)

    def get_equipments(
        self,
        carId: Optional[int] = None,
        equipmentName: Optional[str] = None,
        equipmentStatus: Optional[str] = None,
        isActive: Optional[bool] = None,
        pageIndex: int = 0,
        pageSize: int = 50,
        propertyName: str = "id",
        order: str = "ASC"
    ) -> Tuple[List[Equipment], int]:
        expressions = []
        if carId is not None:
            expressions.append(lambda x: x.carId == carId)
        if equipmentName:
            expressions.append(lambda x: x.equipmentName.like(f"%{equipmentName}%"))
        if equipmentStatus:
            expressions.append(lambda x: x.equipmentStatus == equipmentStatus)
        if isActive is not None:
            expressions.append(lambda x: x.isActive == isActive)

        return self.filter_with_pageable(
            *expressions,
            pageIndex=pageIndex,
            pageSize=pageSize,
            propertyName=propertyName,
            order=order
        )

    def create_equipment(self, schema: EquipmentCreate) -> Equipment:
        return super().create(schema)

    def update_equipment(self, id: int, schema: EquipmentUpdate) -> Equipment:
        return super().update(id, schema)
