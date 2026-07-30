from typing import Any, Dict, List, Optional
import json
import os
import yaml
from sqlalchemy.orm import Session
from app.models.user_model import User
from app.models.config_model import Config, SystemConfig
from app.models.equipment_model import Equipment
from app.models.sensor_model import Sensor
from app.core.logger import logger
from datetime import datetime, timezone
from app.core.security import get_password_hash
from app.database.session import engine, Base

def create_tables():
    """初始化建立所有 SQLAlchemy ORM 資料表 (若尚不存在)"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created successfully via ORM Metadata.")

def sync_yaml_to_db(db: Session, yaml_path: str = "gateway.yaml", force: bool = False):
    """
    Auto Sync 機制：自動讀取 gateway.yaml 並更新/同步至 SQLite 資料庫 (SystemConfig, Equipments, Sensors)
    """
    if not os.path.exists(yaml_path):
        logger.warning(f"YAML config file {yaml_path} not found. Skipping auto-sync.")
        return

    try:
        logger.info(f"Syncing system configs from {yaml_path} to DB...")
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        def upsert_config(category: str, key: str, value: Any):
            val_str = str(value) if value is not None else ""
            item = db.query(SystemConfig).filter(SystemConfig.key == key).first()
            if item:
                item.value = val_str
                item.category = category
            else:
                db.add(SystemConfig(category=category, key=key, value=val_str))

        gateway_cfg = data.get("gateway", {}) or {}
        for k, v in gateway_cfg.items():
            upsert_config("gateway", f"gateway.{k}", v)

        network_cfg = data.get("network", {}) or {}
        broker_mqtt_cfg = network_cfg.get("broker_mqtt", {}) or network_cfg.get("mqtt", {}) or {}
        for k, v in broker_mqtt_cfg.items():
            upsert_config("network", f"broker_mqtt.{k}", v)

        cloud_mqtt_cfg = network_cfg.get("cloud_mqtt", {}) or {}
        for k, v in cloud_mqtt_cfg.items():
            upsert_config("network", f"cloud_mqtt.{k}", v)

        upsert_config("network", "ipc_socket_path", network_cfg.get("ipc_socket_path", "/tmp/hvac_ipc.sock"))

        database_cfg = data.get("database", {}) or {}
        for k, v in database_cfg.items():
            upsert_config("database", f"database.{k}", v)

        # 同步 equipments 與 registers (感測器點位) 到 SQLite 的 equipments 與 sensors 資料表
        equipments_cfg = data.get("equipments", []) or []
        for eq_item in equipments_cfg:
            eq_id_str = str(eq_item.get("id", ""))
            eq_name = eq_item.get("name", "")
            eq_ip = eq_item.get("ip", "")

            # 嘗試更新 Equipment 表
            eq_rec = None
            if eq_id_str.isdigit():
                eq_rec = db.query(Equipment).filter(Equipment.id == int(eq_id_str)).first()
            if not eq_rec and eq_name:
                eq_rec = db.query(Equipment).filter(Equipment.equipmentName == eq_name).first()

            if eq_rec:
                if eq_name:
                    eq_rec.equipmentName = eq_name
                if eq_ip:
                    eq_rec.ipAddress = eq_ip

            # 同步 registers 到 Sensors 表
            for reg in eq_item.get("registers", []):
                code = reg.get("code")
                if not code:
                    continue
                s_name = reg.get("name")
                s_unit = reg.get("unit", "")
                s_type = reg.get("sensor_type", "REAL_TIME")

                sensor_rec = db.query(Sensor).filter(Sensor.sensorCode == code).first()
                if sensor_rec:
                    if s_name:
                        sensor_rec.sensorName = s_name
                    if s_unit is not None:
                        sensor_rec.sensorUnit = str(s_unit)
                    if s_type:
                        sensor_rec.sensorType = s_type

        db.commit()
        logger.info("SystemConfigs, Equipments, and Sensors synced from YAML to DB successfully.")

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
