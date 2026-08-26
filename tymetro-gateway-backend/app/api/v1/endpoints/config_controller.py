from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from app.database.session import get_db
from app.schemas.response_schema import ResponseBase, ResponseList
from app.utils.response_util import ResponseUtil
from app.database.db_config_repo import db_config_repo
from app.models.config_model import SystemConfig
from app.models.user_model import User
from app.api.deps import get_config_service, get_current_user
from app.services.config_service import ConfigService
from app.schemas.config_schema import ConfigCreate, ConfigUpdate, ConfigResponse

from app.database.init_db import sync_yaml_to_db
from app.core.config_yaml import reload_gateway_yaml_config
from app.services.gateway_mqtt_service import gateway_mqtt_service
from app.services.cloud_mqtt_service import cloud_mqtt_service

router = APIRouter()

@router.post("/reload", response_model=ResponseBase, summary="觸發熱重載內存快取與 gateway.yaml 設定並同步資料庫與 MQTT 服務")
async def reload_config(db: Session = Depends(get_db)):
    """重新自硬碟載入 gateway.yaml、同步覆蓋至 DB、重啟 MQTT 連線並清空 RAM 快取"""
    try:
        # 1. 先將最新 YAML 同步覆蓋入 SQLite 資料庫 (system_configs)
        sync_yaml_to_db(db, force=True)
        # 2. 重新讀取 gateway.yaml 至 Python 記憶體 (yaml_settings)
        reload_gateway_yaml_config()
        # 3. 清空並立即預熱 (Pre-warm) 最新 RAM 快取
        db_config_repo.clear_cache()
        db_config_repo.get_all_equipments()
        # 4. 熱重載並重連 MQTT Subscriber 與 Publisher (Cloud MQTT)
        await gateway_mqtt_service.restart()
        await cloud_mqtt_service.restart()
        return ResponseUtil.success(message="gateway.yaml reloaded, synced to DB, MQTT services restarted, and RAM cache pre-warmed successfully.")
    except Exception as e:
        return ResponseUtil.error(message=f"Failed to reload config: {e}")

@router.post("/sync", response_model=ResponseBase, summary="從 gateway.yaml 重置並同步設定至資料庫與 MQTT 服務")
async def sync_yaml_configs(db: Session = Depends(get_db)):
    """清空現有 system_configs 並從 gateway.yaml 重新匯入、重啟 MQTT 連線與預熱快取"""
    try:
        # 1. 先將 gateway.yaml 同步覆蓋至 SQLite 資料庫
        sync_yaml_to_db(db, force=True)
        # 2. 再重載 YAML 至 Python 記憶體全域變數 (yaml_settings)
        reload_gateway_yaml_config()
        # 3. 清空舊的 RAM 快取
        db_config_repo.clear_cache()
        # 4. 重新自 DB 讀取並預熱最新快取
        db_config_repo.get_all_equipments()
        # 5. 熱重載並重連 MQTT Subscriber 與 Publisher (Cloud MQTT)
        await gateway_mqtt_service.restart()
        await cloud_mqtt_service.restart()
        return ResponseUtil.success(message="Successfully re-synced system configs from gateway.yaml to DB, restarted MQTT services, and pre-warmed RAM cache.")
    except Exception as e:
        return ResponseUtil.error(message=f"Failed to sync configs from YAML: {e}")

@router.delete("", response_model=ResponseBase, summary="清空所有系統設定 (Clear System Configs)")
def clear_system_configs(db: Session = Depends(get_db)):
    """清空 system_configs 資料表中所有系統設定紀錄並重置 RAM 快取"""
    try:
        num_deleted = db.query(SystemConfig).delete()
        db.commit()
        db_config_repo.clear_cache()
        db_config_repo.get_all_equipments()
        return ResponseUtil.success(
            data={"cleared_count": num_deleted},
            message=f"Successfully cleared {num_deleted} system config records and re-initialized RAM cache."
        )
    except Exception as e:
        db.rollback()
        return ResponseUtil.error(message=f"Failed to clear system configs: {e}")

@router.get("", response_model=ResponseList[ConfigResponse], summary="獲取設定清單")
def get_configs(
    pageIndex: int = 0,
    pageSize: int = 50,
    propertyName: str = "id",
    order: str = "DESC",
    configType: Optional[str] = None,
    service: ConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user)
):
    items, total = service.get_configs(
        configType=configType,
        pageIndex=pageIndex,
        pageSize=pageSize,
        propertyName=propertyName,
        order=order
    )
    return ResponseUtil.list_success(
        data=items,
        total=total,
        pageIndex=pageIndex,
        pageSize=pageSize
    )

@router.get("/type/{config_type}", response_model=ResponseBase[ConfigResponse], summary="根據類型獲取設定資訊")
def get_config_by_type(
    config_type: str,
    service: ConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user)
):
    item = service.get_by_config_type(config_type)
    if not item:
        return ResponseUtil.not_found("Config not found")
    return ResponseUtil.success(data=item)

@router.put("/{config_id}", response_model=ResponseBase[ConfigResponse], summary="更新設定資訊")
def update_config(
    config_id: int,
    request: ConfigUpdate,
    service: ConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user)
):
    try:
        item = service.update(config_id, request)
        return ResponseUtil.success(data=item, message="Config updated successfully")
    except Exception as e:
        return ResponseUtil.error(message=str(e))

@router.post("/upsert", response_model=ResponseBase[ConfigResponse], summary="新增或更新設定")
def upsert_config(
    request: ConfigCreate,
    service: ConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user)
):
    try:
        item = service.get_by_config_type(request.configType)
        if item:
            item = service.update(item.id, ConfigUpdate(configContent=request.configContent))
            return ResponseUtil.success(data=item, message="Config updated successfully")
        else:
            item = service.create(request)
            return ResponseUtil.success(data=item, message="Config created successfully")
    except Exception as e:
        return ResponseUtil.error(message=str(e))
