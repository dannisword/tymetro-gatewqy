from typing import Any, Dict, List, Optional
import json
import os
import yaml
from sqlalchemy.orm import Session
from app.models.user_model import User
from app.models.config_model import Config, SystemConfig
from app.models.equipment_model import Equipment
from app.models.sensor_model import Sensor
from app.models.setting_log_model import SettingLog
from app.models.schedule_model import Schedule
from app.models.sensor_history_model import SensorHistory
from app.models.sensor_value_label_model import SensorValueLabel
from app.models.event_template_model import EventTemplate
from app.models.equipment_event_model import EquipmentEvent

from app.core.logger import logger
from datetime import datetime, timezone
from app.core.security import get_password_hash
from app.database.session import engine, Base
from app.core.config_yaml import parse_yaml_with_env

def create_tables():
    """初始化建立所有 SQLAlchemy ORM 資料表 (若尚不存在)"""
    Base.metadata.create_all(bind=engine)
    
    from sqlalchemy import inspect, text
    inspector = inspect(engine)

    # 檢查並動態遷移 configs.version 欄位 (防止舊有 SQLite 資料庫因為缺少此欄位出錯)
    if "configs" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("configs")]
        if "version" not in columns:
            logger.info("Adding missing column 'version' to 'configs' table...")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE configs ADD COLUMN version VARCHAR(50) DEFAULT '1.0.0'"))

    # 檢查並動態遷移 sensors 新增欄位 (與雲端 PostgreSQL sensors 結構一致)
    if "sensors" in inspector.get_table_names():
        sensor_cols = [col["name"] for col in inspector.get_columns("sensors")]
        new_sensor_cols = {
            "limit_mode": "VARCHAR(20) DEFAULT 'NONE'",
            "min_limit": "NUMERIC(10,2) DEFAULT NULL",
            "max_limit": "NUMERIC(10,2) DEFAULT NULL",
            "scale": "NUMERIC(6,4) NOT NULL DEFAULT 1.0",
            "data_type": "VARCHAR(50) NOT NULL DEFAULT 'int16'",
            "default_value": "NUMERIC(10,2) DEFAULT 0.00",
        }
        for col_name, col_def in new_sensor_cols.items():
            if col_name not in sensor_cols:
                logger.info(f"Adding missing column '{col_name}' to 'sensors' table...")
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE sensors ADD COLUMN {col_name} {col_def}"))

    # 檢查並動態遷移 users.email 欄位 (與雲端 PostgreSQL users 結構一致)
    if "users" in inspector.get_table_names():
        user_cols = [col["name"] for col in inspector.get_columns("users")]
        if "email" not in user_cols:
            logger.info("Adding missing column 'email' to 'users' table...")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(100)"))

    # 檢查並動態遷移 setting_logs 指令追蹤欄位 (command_id / status 等，與雲端 setting_logs 對應)
    if "setting_logs" in inspector.get_table_names():
        log_cols = [col["name"] for col in inspector.get_columns("setting_logs")]
        new_log_cols = {
            "topic": "VARCHAR(255) DEFAULT NULL",
            "payload": "TEXT DEFAULT NULL",
            "command_id": "VARCHAR(36) DEFAULT NULL",
            "status": "VARCHAR(20) DEFAULT NULL",
            "error_message": "VARCHAR(500) DEFAULT NULL",
            "acked_at": "DATETIME DEFAULT NULL",
            "finished_at": "DATETIME DEFAULT NULL",
        }
        for col_name, col_def in new_log_cols.items():
            if col_name not in log_cols:
                logger.info(f"Adding missing column '{col_name}' to 'setting_logs' table...")
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE setting_logs ADD COLUMN {col_name} {col_def}"))
        with engine.begin() as conn:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_setting_logs_command_id ON setting_logs (command_id)"))

    # 檢查並動態遷移 setting_logs 審計欄位，並將舊 audit_logs 資料併入後移除該表
    if "setting_logs" in inspector.get_table_names():
        log_cols = [col["name"] for col in inspector.get_columns("setting_logs")]
        new_audit_cols = {
            "audit_category": "VARCHAR(50) DEFAULT NULL",
            "action": "VARCHAR(100) DEFAULT NULL",
            "ip_address": "VARCHAR(50) DEFAULT NULL",
            "detail": "VARCHAR(1000) DEFAULT NULL",
        }
        for col_name, col_def in new_audit_cols.items():
            if col_name not in log_cols:
                logger.info(f"Adding missing column '{col_name}' to 'setting_logs' table...")
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE setting_logs ADD COLUMN {col_name} {col_def}"))
        with engine.begin() as conn:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_setting_logs_audit_category ON setting_logs (audit_category)"))

        if "audit_logs" in inspector.get_table_names():
            logger.info("Merging legacy 'audit_logs' into 'setting_logs'...")
            with engine.begin() as conn:
                conn.execute(text(
                    "INSERT INTO setting_logs (setting_type, audit_category, action, status, operator, ip_address, detail, is_notified, recorded_at) "
                    "SELECT SUBSTR(action, 1, 50), audit_category, action, status, operator, ip_address, detail, 0, timestamp FROM audit_logs"
                ))
                conn.execute(text("DROP TABLE audit_logs"))

    # 建立/確保感測器歷史紀錄之複合降序索引存在 (顯著加速 PFC200 查詢)
    if "sensor_histories" in inspector.get_table_names():
        with engine.begin() as conn:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sensor_histories_recorded_at_desc ON sensor_histories (recorded_at DESC)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sensor_histories_code_time ON sensor_histories (sensor_code, recorded_at DESC)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sensor_histories_code_car_time ON sensor_histories (sensor_code, car_vin, recorded_at DESC)"))
            conn.execute(text("DROP INDEX IF EXISTS ix_sensor_histories_recorded_at"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sensor_histories_car_time ON sensor_histories (car_vin, recorded_at DESC)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sensor_histories_equip_time ON sensor_histories (equipment_name, recorded_at DESC)"))
                
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
            data = parse_yaml_with_env(f.read())

        def upsert_config(category: str, key: str, value: Any):
            val_str = str(value) if value is not None else ""
            query = db.query(SystemConfig).filter(SystemConfig.key == key)
            if query.first():
                query.update({SystemConfig.value: val_str, SystemConfig.category: category})
            else:
                db.add(SystemConfig(category=category, key=key, value=val_str))

        gateway_cfg = data.get("gateway", {}) or {}
        for k, v in gateway_cfg.items():
            upsert_config("gateway", f"gateway.{k}", v)

        network_cfg = data.get("network", {}) or {}
        gateway_mqtt_cfg = network_cfg.get("gateway_mqtt", {}) or network_cfg.get("broker_mqtt", {}) or network_cfg.get("mqtt", {}) or {}
        for k, v in gateway_mqtt_cfg.items():
            upsert_config("network", f"gateway_mqtt.{k}", v)

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
                eq_values: Dict[Any, Any] = {}
                if eq_name:
                    eq_values[Equipment.equipmentName] = eq_name
                if eq_ip:
                    eq_values[Equipment.ipAddress] = eq_ip
                if eq_values:
                    db.query(Equipment).filter(Equipment.id == eq_rec.id).update(eq_values)

            # 同步 registers 到 Sensors 表
            for reg in eq_item.get("registers", []):
                code = reg.get("code")
                if not code:
                    continue
                s_name = reg.get("name")
                s_unit = reg.get("unit", "")
                s_type = reg.get("sensor_type", "REAL_TIME")

                sensor_query = db.query(Sensor).filter(Sensor.sensorCode == code)
                if sensor_query.first():
                    sensor_values: Dict[Any, Any] = {}
                    if s_name:
                        sensor_values[Sensor.sensorName] = s_name
                    if s_unit is not None:
                        sensor_values[Sensor.sensorUnit] = str(s_unit)
                    if s_type:
                        sensor_values[Sensor.sensorType] = s_type
                    if sensor_values:
                        sensor_query.update(sensor_values)

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

        # 初始化預設排程 (Schedule)
        if not db.query(Schedule).first():
            logger.info("Creating default schedules in SQLite...")
            default_schedules = [
                Schedule(
                    name="每小時同步資料",
                    scheduleType="hourly",
                    taskCode="SYNC_SCHEDULE_CONFIG",
                    minuteOfHour=0,
                    isActive=False,
                    description="同步時段溫度設定"
                )
            ]
            db.add_all(default_schedules)
            db.commit()
            logger.info("Default schedules created successfully.")

        # 自動進行 YAML -> DB 同步 (Option B)
        sync_yaml_to_db(db)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to initialize database: {e}")
