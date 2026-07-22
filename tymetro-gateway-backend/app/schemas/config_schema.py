from pydantic import BaseModel, ConfigDict
from typing import Optional
from app.schemas.base import AuditBase

class ConfigBase(BaseModel):
    configType: str
    configContent: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class ConfigCreate(ConfigBase):
    pass

class ConfigUpdate(BaseModel):
    configType: Optional[str] = None
    configContent: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class ConfigResponse(ConfigBase, AuditBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)
