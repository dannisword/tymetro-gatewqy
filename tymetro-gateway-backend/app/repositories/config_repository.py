from sqlalchemy.orm import Session
from app.repositories.base_repository import BaseRepository
from app.models.config_model import Config

class ConfigRepository(BaseRepository[Config]):
    def __init__(self, db: Session):
        super().__init__(Config, db)
