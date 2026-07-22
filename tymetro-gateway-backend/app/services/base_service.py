from typing import TypeVar, Generic, Type, Any, List, Optional, Union, Dict
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.repositories.base_repository import BaseRepository
from app.core.logger import logger

# 定義泛型變數
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    repo: Any

    def __init__(self, db: Session, model: Optional[Type[ModelType]] = None):
        """
        :param db: 資料庫 Session
        :param model: 選項，如果傳入 model，則會自動建立基礎 repo
        """
        self.db = db
        if model:
            self.repo = BaseRepository(model, db)
        else:
            self.repo = None  # 子類別應該自行初始化 repo
            
        self.logger = logger
         
    def get_by_id(self, id: Any) -> ModelType:
        """取得單筆資料，若不存在則拋出 404"""
        obj = self.repo.get(id)
        if not obj:
            raise HTTPException(status_code=404, detail="Item not found")
        return obj

    def get_by(self, *expressions, **kwargs) -> Optional[ModelType]:
        """單筆查詢"""
        return self.repo.get_by(*expressions, **kwargs)

    def filter(self, *expressions, **kwargs) -> List[ModelType]:
        """多筆查詢"""
        return self.repo.filter(*expressions, **kwargs)

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
        return self.repo.filter_with_pageable(
            *expressions, 
            pageIndex=pageIndex, 
            pageSize=pageSize, 
            propertyName=propertyName,
            order=order,
            **kwargs
        )

    def get_list_by(
        self, 
        *expressions, 
        skip: int = 0, 
        limit: int = 100, 
        **kwargs
    ) -> List[ModelType]:
        """多筆查詢 支援條件過濾與分頁"""
        return self.repo.filter(*expressions, skip=skip, limit=limit, **kwargs)
    
    def get_list(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """取得列表 (通用版)"""
        return self.repo.get_all(skip=skip, limit=limit)

    def get_list_with_pageable(self, skip: int = 0, limit: int = 100) -> tuple[List[ModelType], int]:
        """取得列表與總筆數 (Pageable)"""
        return self.repo.get_all_with_pageable(skip=skip, limit=limit)

    def create(self, schema: Union[CreateSchemaType, Dict[str, Any]]) -> ModelType:
        """支援傳入 Schema 或 Dict"""
        if isinstance(schema, dict):
            obj_in = schema
        else:
            obj_in = schema.model_dump(exclude_unset=True)
        
        try:
            db_obj = self.repo.create(obj_in)
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"新增失敗: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Create failed: {str(e)}")

    def update(self, id: Any, schema: Union[UpdateSchemaType, Dict[str, Any]]) -> ModelType:
        self.get_by_id(id)
        if isinstance(schema, dict):
            obj_in = schema
        else:
            obj_in = schema.model_dump(exclude_unset=True)
            
        try:
            result = self.repo.update(id, obj_in)
            self.db.commit()
            self.db.refresh(result)
            self.logger.info(f"更新成功 | ID: {id}")
            return result
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"更新失敗 | ID: {id} | 錯誤: {str(e)}")
            raise HTTPException(status_code=400, detail="Update failed")   

    def delete(self, id: Any) -> ModelType:
        """標準刪除邏輯"""
        db_obj = self.get_by_id(id)  # 檢查是否存在
        try:
            self.repo.delete(id)
            self.db.commit()
            return db_obj
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"刪除失敗: {str(e)}")
            raise HTTPException(status_code=400, detail="Delete failed")

    def create_many(self, schemas: List[Union[CreateSchemaType, Dict[str, Any]]]) -> List[ModelType]:
        """批次新增"""
        if not schemas:
            return []
            
        objs_in = []
        for schema in schemas:
            try:
                if isinstance(schema, dict):
                    objs_in.append(schema)
                elif hasattr(schema, 'model_dump'):
                    objs_in.append(schema.model_dump(exclude_unset=True))
                else:
                    self.logger.warning(f"create_many 收到不支援的資料型態: {type(schema)}")
                    continue
            except Exception as e:
                self.logger.error(f"資料轉換失敗，跳過此筆: {e}")
                continue
        
        if not objs_in:
            return []

        try:
            db_objs = self.repo.create_many(objs_in)
            self.db.commit()
            for obj in db_objs:
                self.db.refresh(obj)
            return db_objs
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"批次新增失敗: {str(e)}")
            raise HTTPException(status_code=400, detail="Bulk create failed")

    def update_many(self, schemas: List[Union[UpdateSchemaType, Dict[str, Any]]]) -> int:
        """批次更新"""
        if not schemas:
            return 0
            
        objs_in = []
        for schema in schemas:
            try:
                if isinstance(schema, dict):
                    objs_in.append(schema)
                elif hasattr(schema, 'model_dump'):
                    objs_in.append(schema.model_dump(exclude_unset=True))
            except Exception as e:
                self.logger.error(f"資料轉換失敗，跳過此筆: {e}")
                continue
        
        if not objs_in:
            return 0
            
        return self.repo.update_many(objs_in)

    def delete_many(self, ids: List[Any]) -> int:
        if not ids:
            return 0
        return self.repo.delete_many(ids)
