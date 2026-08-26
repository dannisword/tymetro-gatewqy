from sqlalchemy.orm import Session
from app.models.setting_log_model import SettingLog
from app.repositories.base_repository import BaseRepository

class SettingLogRepository(BaseRepository[SettingLog]):
    def __init__(self, db: Session):
        super().__init__(SettingLog, db)
