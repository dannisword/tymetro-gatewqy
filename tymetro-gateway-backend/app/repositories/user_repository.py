from sqlalchemy.orm import Session
from app.models.user_model import User
from app.repositories.base_repository import BaseRepository

class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_account(self, account: str):
        return self.db.query(self.model).filter(self.model.account == account).first()
