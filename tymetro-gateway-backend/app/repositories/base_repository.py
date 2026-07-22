from typing import TypeVar, Generic, Type, List, Optional, Any, cast
from sqlalchemy.orm import Session
from sqlalchemy import delete, ColumnElement
from datetime import datetime, timezone
from app.core.logger import logger

ModelType = TypeVar("ModelType", bound=Any)

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: Session):
        """
        :param model: SQLAlchemy 模型類別
        :param db: SQLAlchemy Session 實例
        """
        self.model = model
        self.db = db

    def get(self, id: Any) -> Optional[ModelType]:
        """透過 ID 取得單筆資料"""
        return self.db.query(self.model).filter(cast(ColumnElement[bool], getattr(self.model, "id") == id)).first()

    def filter(self, *expressions, skip: int = 0, limit: int = 100, **kwargs) -> List[ModelType]:
        """列表查詢與過濾 (自動跳過值為 None 的條件)"""
        query = self.db.query(self.model)
        
        if expressions:
            for expr in expressions:
                query = query.filter(cast(ColumnElement[bool], expr(self.model) if callable(expr) else expr))
        
        if kwargs:
            # 只保留值不為 None 的過濾條件
            valid_filters = {k: v for k, v in kwargs.items() if v is not None}
            if valid_filters:
                query = query.filter_by(**valid_filters)
        
        return query.offset(skip).limit(limit).all()

    def filter_with_pageable(
        self, 
        *expressions, 
        pageIndex: int = 0, 
        pageSize: int = 50, 
        propertyName: str = "id",
        order: str = "DESC",
        **kwargs
    ) -> tuple[List[ModelType], int]:
        """列表查詢與過濾，並回傳總筆數 (Pageable)"""
        query = self.db.query(self.model)
        
        if expressions:
            for expr in expressions:
                query = query.filter(cast(ColumnElement[bool], expr(self.model) if callable(expr) else expr))
        
        if kwargs:
            valid_filters = {k: v for k, v in kwargs.items() if v is not None}
            if valid_filters:
                query = query.filter_by(**valid_filters)
        
        # 1. 計算總數
        total = query.count()
        
        # 2. 處理排序
        if propertyName and hasattr(self.model, propertyName):
            col = getattr(self.model, propertyName)
            logger.info(f"propertyName: {propertyName}, order: {order}")
            if order.upper() == "ASC":
                query = query.order_by(col.asc())
            else:
                query = query.order_by(col.desc())
        else:
            # 預設排序
            query = query.order_by(getattr(self.model, "id").desc())
 
        # 3. 分頁
        skip = pageIndex * pageSize
        items = query.offset(skip).limit(pageSize).all()
        
        return items, total
        
    def get_by(self, *expressions, **kwargs) -> Optional[ModelType]:
        """單筆查詢"""
        query = self.db.query(self.model)

        for expr in expressions:
            query = query.filter(cast(ColumnElement[bool], expr(self.model) if callable(expr) else expr))

        for key, value in kwargs.items():
            if hasattr(self.model, key):
                query = query.filter(cast(ColumnElement[bool], getattr(self.model, key) == value))

        return query.first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """取得所有資料"""
        return self.db.query(self.model).offset(skip).limit(limit).all()
    
    def get_all_with_pageable(self, skip: int = 0, limit: int = 100) -> tuple[List[ModelType], int]:
        """取得所有資料與總數 (Pageable)"""
        query = self.db.query(self.model)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total
    
    def create(self, obj_in: dict) -> ModelType:
        """新增資料"""
        if "createdAt" not in obj_in:
            obj_in["createdAt"] = datetime.now(timezone.utc)

        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        return db_obj
    
    def update(self, id: Any, obj_in: dict) -> Optional[ModelType]:
        """更新資料"""
        db_obj = self.db.query(self.model).get(id)
        if not db_obj:
            return None
        
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        if hasattr(db_obj, "updatedAt"):
            db_obj.updatedAt = datetime.now(timezone.utc)

        self.db.add(db_obj)
        return db_obj
    
    def delete(self, id: Any) -> bool:
        """刪除資料"""
        obj = self.db.query(self.model).get(id)
        if obj:
            self.db.delete(obj)
            return True
        return False

    def create_many(self, objs_in: List[dict]) -> List[ModelType]:
        """批次新增"""
        if not objs_in:
            return []

        now = datetime.now(timezone.utc)
        has_created = hasattr(self.model, "createdAt")
        has_updated = hasattr(self.model, "updatedAt")
        
        db_objs = []
        for obj in objs_in:
            if has_created and "createdAt" not in obj:
                obj["createdAt"] = now
            if has_updated and "updatedAt" not in obj:
                obj["updatedAt"] = now
            db_objs.append(self.model(**obj))

        self.db.add_all(db_objs)
        return db_objs
    
    def update_many(self, data_list: List[dict]) -> int:
        """批次更新"""
        if not data_list:
            return 0
        
        now = datetime.now(timezone.utc)
        for item in data_list:
            if "updatedAt" not in item:
                item["updatedAt"] = now

        self.db.bulk_update_mappings(cast(Any, self.model), data_list)
        return len(data_list)
    
    def update_many_by_filter(self, criteria: dict, update_data: dict) -> int:
        """根據條件批次更新"""
        if "updatedAt" not in update_data:
            update_data["updatedAt"] = datetime.now(timezone.utc)

        query = self.db.query(self.model)
        for key, value in criteria.items():
            query = query.filter(cast(ColumnElement[bool], getattr(self.model, key) == value))
            
        rows_affected = query.update(update_data, synchronize_session=False)
        return rows_affected
    
    def delete_many(self, ids: List[Any]) -> int:
        """批次刪除"""
        if not ids:
            return 0

        stmt = delete(self.model).where(getattr(self.model, "id").in_(ids))
        result = self.db.execute(stmt)
        return cast(Any, result).rowcount
