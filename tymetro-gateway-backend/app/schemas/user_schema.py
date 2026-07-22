from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.schemas.base import AuditBase

class UserBase(BaseModel):
    account: str
    userName: Optional[str] = None
    orgId: int
    orgCode: Optional[str] = None
    orgName: Optional[str] = None
    roleIds: Optional[List[int]] = None
    roleNames: Optional[List[str]] = None
    isMobile: Optional[bool] = False
    isActive: Optional[bool] = True
    
    model_config = ConfigDict(from_attributes=True)

class UserCreate(UserBase):
    password: Optional[str] = None

class UserUpdate(BaseModel):
    userName: Optional[str] = None
    password: Optional[str] = None
    roleIds: Optional[List[int]] = None
    enableAt: Optional[datetime] = None
    disableAt: Optional[datetime] = None
    isMobile: Optional[bool] = None
    isActive: Optional[bool] = None
    
    model_config = ConfigDict(from_attributes=True)

class UserResponse(UserBase, AuditBase):
    id: int
    enableAt: Optional[datetime] = None
    disableAt: Optional[datetime] = None
    lastLoginAt: Optional[datetime] = None
    isAccountValid: bool = True
    
    model_config = ConfigDict(from_attributes=True)

class UserLoginRequest(BaseModel):
    account: str
    password: str
