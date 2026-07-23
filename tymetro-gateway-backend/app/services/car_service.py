from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.car_model import Car
from app.schemas.car_schema import CarCreate, CarUpdate
from app.repositories.car_repository import CarRepository
from app.services.base_service import BaseService

class CarService(BaseService[Car, CarCreate, CarUpdate]):
    repo: CarRepository

    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = CarRepository(db)

    def get_car(self, id: int) -> Optional[Car]:
        return super().get_by_id(id)

    def get_cars(
        self,
        trainCode: Optional[str] = None,
        carNo: Optional[int] = None,
        carVin: Optional[str] = None,
        carType: Optional[str] = None,
        carStatus: Optional[str] = None,
        isActive: Optional[bool] = None,
        pageIndex: int = 0,
        pageSize: int = 50,
        propertyName: str = "id",
        order: str = "ASC"
    ) -> Tuple[List[Car], int]:
        expressions = []
        if trainCode:
            expressions.append(lambda x: x.trainCode.like(f"%{trainCode}%"))
        if carNo is not None:
            expressions.append(lambda x: x.carNo == carNo)
        if carVin:
            expressions.append(lambda x: x.carVin.like(f"%{carVin}%"))
        if carType:
            expressions.append(lambda x: x.carType == carType)
        if carStatus:
            expressions.append(lambda x: x.carStatus == carStatus)
        if isActive is not None:
            expressions.append(lambda x: x.isActive == isActive)

        return self.filter_with_pageable(
            *expressions,
            pageIndex=pageIndex,
            pageSize=pageSize,
            propertyName=propertyName,
            order=order
        )

    def create_car(self, schema: CarCreate) -> Car:
        return super().create(schema)

    def update_car(self, id: int, schema: CarUpdate) -> Car:
        return super().update(id, schema)
