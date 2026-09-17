from sqlalchemy.orm import Session
from app.repositories.base_repository import BaseRepository
from app.models.audit_log_model import AuditLog

class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, db: Session):
        super().__init__(AuditLog, db)
