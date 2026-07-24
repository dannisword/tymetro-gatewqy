import json
import os
import yaml
from sqlalchemy.orm import Session
from app.models.user_model import User
from app.models.config_model import Config, SystemConfig
from app.core.logger import logger
from datetime import datetime, timezone
from app.core.security import get_password_hash
from app.database.session import engine, Base

def create_tables():
    """初始化建立所有 SQLAlchemy ORM 資料表 (若尚不存在)"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created successfully via ORM Metadata.")

def sync_yaml_to_db(db: Session, yaml_path: str = "gateway.yaml"):
    """
    Auto Sync 機制：若 DB 為空，自動讀取 gateway.yaml 並匯入 SQLite 資料庫
    """
    if not os.path.exists(yaml_path):
        logger.warning(f"YAML config file {yaml_path} not found. Skipping auto-sync.")
        return

    try:
        # 1. 檢查是否已有 SystemConfig 資料
        if db.query(SystemConfig).count() == 0:
            logger.info(f"SystemConfigs table is empty. Syncing from {yaml_path}...")
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            gateway_cfg = data.get("gateway", {})
            for k, v in gateway_cfg.items():
                db.add(SystemConfig(category="gateway", key=f"gateway.{k}", value=str(v)))

            network_cfg = data.get("network", {})
            mqtt_cfg = network_cfg.get("mqtt", {})
            for k, v in mqtt_cfg.items():
                db.add(SystemConfig(category="network", key=f"mqtt.{k}", value=str(v)))

            cloud_mqtt_cfg = network_cfg.get("cloud_mqtt", {})
            for k, v in cloud_mqtt_cfg.items():
                db.add(SystemConfig(category="network", key=f"cloud_mqtt.{k}", value=str(v)))

            db.add(SystemConfig(category="network", key="ipc_socket_path", value=network_cfg.get("ipc_socket_path", "/tmp/hvac_ipc.sock")))

            db.commit()
            logger.info("SystemConfigs synced from YAML successfully.")

    except Exception as e:
        db.rollback()
        logger.error(f"Error syncing YAML to DB: {e}")

def init_mock_data(db: Session):
    """初始化預設資料與 YAML 自動備份同步"""
    try:
        admin_user = db.query(User).filter(User.account == "admin").first()
        if not admin_user:
            logger.info("Creating default admin user in SQLite...")
            admin_user = User(
                orgId=1,
                orgCode="HQ",
                account="admin",
                userName="系統管理員",
                password=get_password_hash("admin123"),
                isActive=True,
                enableAt=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            db.add(admin_user)
            db.commit()
            logger.info("Default admin user created successfully.")

        # 自動進行 YAML -> DB 同步 (Option B)
        sync_yaml_to_db(db)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to initialize database: {e}")
