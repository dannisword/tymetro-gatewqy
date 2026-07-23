import json
import os
import yaml
from sqlalchemy.orm import Session
from app.models.user_model import User
from app.models.config_model import Config, SystemConfig, DeviceConfigModel, RegisterConfigModel
from app.core.logger import logger
from datetime import datetime, timezone
from app.core.security import get_password_hash

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
            central_cfg = network_cfg.get("central_server", {})
            for k, v in central_cfg.items():
                db.add(SystemConfig(category="network", key=f"central_server.{k}", value=str(v)))
            db.add(SystemConfig(category="network", key="ipc_socket_path", value=network_cfg.get("ipc_socket_path", "/tmp/hvac_ipc.sock")))

            db.commit()
            logger.info("SystemConfigs synced from YAML successfully.")

        # 2. 檢查是否已有 DeviceConfig 資料
        if db.query(DeviceConfigModel).count() == 0:
            logger.info(f"DeviceConfigs table is empty. Syncing devices from {yaml_path}...")
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            devices_list = data.get("devices", [])
            for dev in devices_list:
                dev_model = DeviceConfigModel(
                    device_id=dev.get("id"),
                    name=dev.get("name"),
                    ip=dev.get("ip"),
                    port=dev.get("port", 502),
                    slave_id=dev.get("slave_id", 1),
                    is_active=True
                )
                db.add(dev_model)
                db.flush()

                for reg in dev.get("registers", []):
                    reg_model = RegisterConfigModel(
                        device_id=dev.get("id"),
                        name=reg.get("name"),
                        address=reg.get("address"),
                        data_type=reg.get("type", "INT16"),
                        scale=float(reg.get("scale", 1.0)),
                        unit=reg.get("unit", "")
                    )
                    db.add(reg_model)
            
            db.commit()
            logger.info(f"Synced {len(devices_list)} devices from YAML to SQLite successfully.")

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
