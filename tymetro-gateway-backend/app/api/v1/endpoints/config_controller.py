from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.response_schema import ResponseBase
from app.utils.response_util import ResponseUtil
from app.database.db_config_repo import db_config_repo
from app.models.config_model import SystemConfig

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
