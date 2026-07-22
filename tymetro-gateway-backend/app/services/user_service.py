from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.logger import logger
from app.models.user_model import User
from app.schemas.user_schema import UserCreate, UserUpdate
from app.repositories.user_repository import UserRepository
from app.services.base_service import BaseService
from app.core.security import get_password_hash, verify_password

class UserService(BaseService[User, UserCreate, UserUpdate]):
    repo: UserRepository

    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = UserRepository(db)

    def get_by_account(self, account: str) -> Optional[User]:
        return self.repo.get_by_account(account)

    def get_user(self, id: int) -> Optional[User]:
        return super().get_by_id(id)

    def get_users(
        self, 
        account: Optional[str] = None,
        userName: Optional[str] = None,
        orgId: Optional[int] = None,
        isActive: Optional[bool] = None,
        pageIndex: int = 0, 
        pageSize: int = 50, 
        propertyName: str = "id",
        order: str = "DESC"
    ):
        """根據參數過濾用戶列表 (含總數)"""
        expressions = []
        if account:
            expressions.append(lambda x: x.account.like(f"%{account}%"))
        if userName:
            expressions.append(lambda x: x.userName.like(f"%{userName}%"))
        if orgId:
            expressions.append(lambda x: x.orgId == orgId)
        if isActive is not None:
            expressions.append(lambda x: x.isActive == isActive)
            
        users, total = self.filter_with_pageable(
            *expressions,
            pageIndex=pageIndex,
            pageSize=pageSize,
            propertyName=propertyName,
            order=order
        )
            
        return users, total

    def register_user(self, schema: UserCreate) -> User:
        """新增帳號"""
        obj_in = schema.model_dump()
        obj_in.pop("roleIds", None)
        obj_in.pop("orgName", None)
        obj_in.pop("roleNames", None)
        
        # 設定預設密碼 (若未提供)
        if not obj_in.get("password"):
            obj_in["password"] = "admin123"
            
        obj_in["password"] = get_password_hash(obj_in["password"])
        user = super().create(obj_in)            
        return user

    def update_user(self, id: int, schema: UserUpdate) -> User:
        """更新帳號"""
        obj_in = schema.model_dump(exclude_unset=True)
        obj_in.pop("roleIds", None)
        obj_in.pop("orgName", None)
        obj_in.pop("roleNames", None)

        if "password" in obj_in and obj_in["password"]:
            obj_in["password"] = get_password_hash(obj_in["password"])

        user = super().update(id, obj_in)            
        return user

    def authenticate(self, account: str, password: str) -> Optional[User]:
        """驗證帳號密碼，回傳 User 物件 (包含日期檢查)"""
        user = self.get_by_account(account)
        if not user:
            return None
        
        # 1. 檢查密碼
        if not verify_password(password, str(user.password)):
            return None
            
        # 2. 檢查 isActive 標記
        if not user.isActive:
            return None
            
        # 3. 檢查日期範圍
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        
        if user.enableAt and user.enableAt > now:
            return None
            
        if user.disableAt and user.disableAt < now:
            return None
            
        return user
