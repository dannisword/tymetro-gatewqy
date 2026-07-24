from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.response_schema import ResponseBase
from app.utils.response_util import ResponseUtil
from app.database.db_config_repo import db_config_repo
from app.models.config_model import SystemConfig

from app.database.init_db import sync_yaml_to_db
from app.core.config_yaml import reload_gateway_yaml_config

router = APIRouter()

@router.post("/reload", response_model=ResponseBase, summary="觸發熱重載內存快取與 gateway.yaml 設定並同步資料庫")
def reload_config(db: Session = Depends(get_db)):
    """重新自硬碟載入 gateway.yaml、同步覆蓋至 DB 並清空 RAM 快取"""
    try:
        # 1. 重新讀取 gateway.yaml 至記憶體
        reload_gateway_yaml_config()
        # 2. 將最新 YAML 同步覆蓋入 SQLite 資料庫 (system_configs)
        sync_yaml_to_db(db, force=True)
        # 3. 清空並立即預熱 (Pre-warm) 最新 RAM 快取
        db_config_repo.clear_cache()
        db_config_repo.get_all_equipments()
        return ResponseUtil.success(message="gateway.yaml reloaded, synced to DB, and RAM cache pre-warmed successfully.")
    except Exception as e:
        return ResponseUtil.error(message=f"Failed to reload config: {e}")

@router.post("/sync", response_model=ResponseBase, summary="從 gateway.yaml 重置並同步設定至資料庫")
def sync_yaml_configs(db: Session = Depends(get_db)):
    """清空現有 system_configs 並從 gateway.yaml 重新匯入與預熱快取"""
    try:
        sync_yaml_to_db(db, force=True)
        db_config_repo.clear_cache()
        db_config_repo.get_all_equipments()
        return ResponseUtil.success(message="Successfully re-synced system configs from gateway.yaml to DB and pre-warmed RAM cache.")
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
