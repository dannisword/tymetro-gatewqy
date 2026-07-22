from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from app.api.deps import get_config_service, get_current_user
from app.services.config_service import ConfigService
from app.schemas.config_schema import ConfigCreate, ConfigUpdate, ConfigResponse
from app.schemas.response_schema import ResponseBase, ResponseList
from app.utils.response_util import ResponseUtil
from app.models.user_model import User

router = APIRouter()

@router.post("", response_model=ResponseBase[ConfigResponse], summary="新增設定")
def create_config(
    request: ConfigCreate, 
    service: ConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user)
):
    try:
        config = service.create(request)
        return ResponseUtil.success(data=config, message="Config created successfully")
    except Exception as e:
        return ResponseUtil.error(message=str(e))

@router.get("", response_model=ResponseList[ConfigResponse], summary="獲取所有設定清單")
def get_configs(
    pageIndex: int = 0, 
    pageSize: int = 50, 
    propertyName: str = "id",
    order: str = "DESC",
    configType: Optional[str] = None,
    service: ConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user)
):
    configs, total = service.get_configs(
        configType=configType, 
        pageIndex=pageIndex, 
        pageSize=pageSize,
        propertyName=propertyName,
        order=order
    )
    return ResponseUtil.list_success(
        data=configs, 
        total=total,
        pageIndex=pageIndex,
        pageSize=pageSize
    )

@router.get("/type/{config_type}", response_model=ResponseBase[ConfigResponse], summary="根據類型獲取設定")
def get_config_by_type(
    config_type: str, 
    service: ConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user)
):
    config = service.get_by_config_type(config_type)
    if not config:
        return ResponseUtil.error(message="Config not found")
    return ResponseUtil.success(data=config)

@router.get("/{config_id}", response_model=ResponseBase[ConfigResponse], summary="獲取設定詳細資訊")
def get_config(
    config_id: int, 
    service: ConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user)
):
    config = service.get_by_id(config_id)
    return ResponseUtil.success(data=config)

@router.put("/{config_id}", response_model=ResponseBase[ConfigResponse], summary="更新設定資訊")
def update_config(
    config_id: int, 
    request: ConfigUpdate, 
    service: ConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user)
):
    config = service.update(config_id, request)
    return ResponseUtil.success(data=config, message="Config updated successfully")

@router.delete("/{config_id}", response_model=ResponseBase, summary="刪除設定")
def delete_config(
    config_id: int, 
    service: ConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user)
):
    service.delete(config_id)
    return ResponseUtil.success(message="Config deleted successfully")
