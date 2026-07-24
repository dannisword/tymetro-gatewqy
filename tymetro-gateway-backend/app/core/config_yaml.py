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

class MQTTYamlConfig(BaseModel):
    enabled: bool = True
    broker_host: str = Field(default_factory=lambda: os.getenv("MQTT_BROKER_HOST", "127.0.0.1"))
    broker_port: int = Field(default_factory=lambda: int(os.getenv("MQTT_BROKER_PORT", "1883")))
    topic_prefix: str = Field(default_factory=lambda: os.getenv("MQTT_TOPIC_PREFIX", "PFC200/+/data"))

class CloudMQTTYamlConfig(BaseModel):
    enabled: bool = True
    broker_host: str = Field(default_factory=lambda: os.getenv("CLOUD_MQTT_HOST", "127.0.0.1"))
    broker_port: int = Field(default_factory=lambda: int(os.getenv("CLOUD_MQTT_PORT", "1883")))
    username: Optional[str] = Field(default_factory=lambda: os.getenv("CLOUD_MQTT_USER", None))
    password: Optional[str] = Field(default_factory=lambda: os.getenv("CLOUD_MQTT_PASS", None))
    client_id: Optional[str] = Field(default_factory=lambda: os.getenv("CLOUD_MQTT_CLIENT_ID", "GW-TAU-01-CLOUD"))
    publish_topic_prefix: str = Field(default_factory=lambda: os.getenv("CLOUD_MQTT_TOPIC", "TYMC/CLOUD/101"))
    qos: int = 0
    reconnect_delay_sec: int = 5

class NetworkConfig(BaseModel):
    mqtt: MQTTYamlConfig = MQTTYamlConfig()
    cloud_mqtt: CloudMQTTYamlConfig = CloudMQTTYamlConfig()
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


def reload_gateway_yaml_config(config_path: str = "gateway.yaml") -> AppYamlConfig:
    global yaml_settings
    yaml_settings = load_gateway_config(config_path)
    logger.info("[ConfigYAML] gateway.yaml reloaded into memory.")
    return yaml_settings

yaml_settings = load_gateway_config()
