from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class AuditBase(BaseModel):
    createdAt: Optional[datetime] = None
    createdBy: Optional[int] = None
    updatedAt: Optional[datetime] = None
    updatedBy: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)
