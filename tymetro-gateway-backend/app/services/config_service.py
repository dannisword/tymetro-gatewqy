from typing import List, Optional, cast
from sqlalchemy.orm import Session
from app.models.config_model import Config
from app.schemas.config_schema import ConfigCreate, ConfigUpdate
from app.repositories.config_repository import ConfigRepository
from app.services.base_service import BaseService

class ConfigService(BaseService[Config, ConfigCreate, ConfigUpdate]):
    repo: ConfigRepository

    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = ConfigRepository(db)

    def get_configs(
        self, 
        configType: Optional[str] = None,
        pageIndex: int = 0, 
        pageSize: int = 50, 
        propertyName: str = "id",
        order: str = "DESC"
    ):
        """根據參數過濾設定列表 (含總數)"""
        expressions = []
        if configType:
            expressions.append(lambda x: x.configType == configType)
            
        configs, total = self.filter_with_pageable(
            *expressions,
            pageIndex=pageIndex,
            pageSize=pageSize,
            propertyName=propertyName,
            order=order
        )
            
        return configs, total

    def get_by_config_type(self, configType: str) -> Optional[Config]:
        """根據設定類型取得單筆設定"""
        return self.repo.get_by(lambda x: x.configType == configType)
