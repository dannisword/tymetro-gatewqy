from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.sensor_model import Sensor
from app.repositories.base_repository import BaseRepository

class SensorRepository(BaseRepository[Sensor]):
    def __init__(self, db: Session):
        super().__init__(Sensor, db)

    def get_by_code(self, sensor_code: str) -> List[Sensor]:
        return self.db.query(self.model).filter(self.model.sensorCode == sensor_code).all()

    def get_by_equipment_id(self, equipment_id: int) -> List[Sensor]:
        return self.db.query(self.model).filter(self.model.equipmentId == equipment_id).all()

    def get_by_car_id(self, car_id: int) -> List[Sensor]:
        return self.db.query(self.model).filter(self.model.carId == car_id).all()
