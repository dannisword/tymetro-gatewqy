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

class GatewayMQTTConfig(BaseModel):
    enabled: bool = True
    broker_host: str = "127.0.0.1"
    broker_port: int = 1883
    topic_prefix: str = "MQT/TRA/OTR/TRC/+/+"
    clean_session: bool = True

class CloudMQTTYamlConfig(BaseModel):
    enabled: bool = True
    broker_host: str = "127.0.0.1"
    broker_port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: Optional[str] = "GW-TAU-01-CLOUD"
    publish_topic_prefix: str = "TYMC/CLOUD/101"
    qos: int = 0
    reconnect_delay_sec: int = 5
    keepalive: int = 20
    clean_session: bool = True

class NetworkConfig(BaseModel):
    gateway_mqtt: GatewayMQTTConfig = Field(default_factory=GatewayMQTTConfig)
    cloud_mqtt: CloudMQTTYamlConfig = CloudMQTTYamlConfig()
    ipc_socket_path: str = "/tmp/hvac_ipc.sock"

    @property
    def mqtt(self) -> GatewayMQTTConfig:
        return self.gateway_mqtt

class DatabaseConfig(BaseModel):
    db_path: str = "gateway.db"
    batch_flush_sec: int = 10

class GatewayInfoConfig(BaseModel):
    id: str = "Gateway"
    name: str = "Gateway"
    location: str = ""
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


def reload_gateway_yaml_config(config_path: str = "gateway.yaml") -> AppYamlConfig:
    global yaml_settings
    new_config = load_gateway_config(config_path)
    for key, value in new_config.__dict__.items():
        setattr(yaml_settings, key, value)
    logger.info("[ConfigYAML] gateway.yaml reloaded in-place into memory.")
    return yaml_settings

yaml_settings = load_gateway_config()
