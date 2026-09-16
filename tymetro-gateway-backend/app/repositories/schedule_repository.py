from sqlalchemy.orm import Session
from app.repositories.base_repository import BaseRepository
from app.models.schedule_model import Schedule

class ScheduleRepository(BaseRepository[Schedule]):
    def __init__(self, db: Session):
        super().__init__(Schedule, db)
