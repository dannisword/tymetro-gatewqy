from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.equipment_model import Equipment
from app.repositories.base_repository import BaseRepository

class EquipmentRepository(BaseRepository[Equipment]):
    def __init__(self, db: Session):
        super().__init__(Equipment, db)

    def get_active_equipments(self) -> List[Equipment]:
        return self.db.query(self.model).filter(self.model.isActive == True).all()

    def get_by_name(self, equipment_name: str) -> Optional[Equipment]:
        return self.db.query(self.model).filter(self.model.equipmentName == equipment_name).first()

    def get_by_car_id(self, car_id: int) -> List[Equipment]:
        return self.db.query(self.model).filter(self.model.carId == car_id).all()
