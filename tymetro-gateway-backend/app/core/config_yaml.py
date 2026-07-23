import os
import yaml
from typing import List, Optional
from pydantic import BaseModel, Field
from app.core.logger import logger

class RegisterConfig(BaseModel):
    code: Optional[str] = None
    name: str
    address: int
    type: str = "INT16"
    scale: float = 1.0
    unit: str = ""
    sensor_type: Optional[str] = "REAL_TIME"

class EquipmentConfig(BaseModel):
    id: str
    name: str
    protocol: Optional[str] = "MQTT"
    mqtt_topic: Optional[str] = None
    ip: Optional[str] = "127.0.0.1"
    port: Optional[int] = 502
    slave_id: Optional[int] = 1
    registers: List[RegisterConfig] = []

class CentralServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 9001
    tls_enabled: bool = False
    reconnect_delay_sec: int = 5

class MQTTYamlConfig(BaseModel):
    enabled: bool = True
    broker_host: str = "127.0.0.1"
    broker_port: int = 1883
    topic_prefix: str = "PFC200/+/data"

class NetworkConfig(BaseModel):
    mqtt: MQTTYamlConfig = MQTTYamlConfig()
    central_server: CentralServerConfig = CentralServerConfig()
    ipc_socket_path: str = "/tmp/hvac_ipc.sock"

class DatabaseConfig(BaseModel):
    db_path: str = "gateway.db"
    batch_flush_sec: int = 10

class GatewayInfoConfig(BaseModel):
    id: str = "GW-TAU-01"
    name: str = "桃園捷運 冰水機房 Gateway"
    location: str = "桃機 T2 冰水主機房"
    poll_interval_ms: int = 1000

class AppYamlConfig(BaseModel):
    gateway: GatewayInfoConfig = GatewayInfoConfig()
    network: NetworkConfig = NetworkConfig()
    database: DatabaseConfig = DatabaseConfig()
    equipments: List[EquipmentConfig] = Field(default=[], alias="equipments")

def load_gateway_config(config_path: str = "gateway.yaml") -> AppYamlConfig:
    if not os.path.exists(config_path):
        logger.warning(f"Config file {config_path} not found. Using default empty settings.")
        return AppYamlConfig()
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return AppYamlConfig(**data)
    except Exception as e:
        logger.error(f"Error loading {config_path}: {e}")
        return AppYamlConfig()


yaml_settings = load_gateway_config()
