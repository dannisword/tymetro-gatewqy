from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class AuditLogBase(BaseModel):
    auditCategory: str
    action: str
    status: Optional[str] = "success"
    operator: Optional[str] = None
    ipAddress: Optional[str] = None
    detail: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class AuditLogCreate(AuditLogBase):
    pass

class AuditLogUpdate(BaseModel):
    auditCategory: Optional[str] = None
    action: Optional[str] = None
    status: Optional[str] = None
    operator: Optional[str] = None
    ipAddress: Optional[str] = None
    detail: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class AuditLogResponse(AuditLogBase):
    id: int
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)
