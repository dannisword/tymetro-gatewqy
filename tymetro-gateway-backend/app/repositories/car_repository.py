from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.car_model import Car
from app.repositories.base_repository import BaseRepository

class CarRepository(BaseRepository[Car]):
    def __init__(self, db: Session):
        super().__init__(Car, db)

    def get_by_vin(self, car_vin: str) -> Optional[Car]:
        return self.db.query(self.model).filter(self.model.carVin == car_vin).first()

    def get_by_train_code(self, train_code: str) -> List[Car]:
        return self.db.query(self.model).filter(self.model.trainCode == train_code).all()
