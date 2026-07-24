import asyncio
import json
from typing import Dict, Any, Optional
import aiomqtt
from app.core.logger import logger
from app.core.config_yaml import yaml_settings
from app.database.db_config_repo import db_config_repo

class CloudMQTTService:
    """
    桃捷雲 Cloud MQTT Forwarder Service:
    - 專責連線至「桃捷雲」 Cloud MQTT Broker
    - 接收內存 Queue 佇列中由 PFC200 送進來的 telemetry 數據，並拋轉 (Publish) 至桃捷雲 Topic
    """
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        publish_topic_prefix: Optional[str] = None
    ):
        self.host = host or db_config_repo.get_system_config("cloud_mqtt.broker_host") or yaml_settings.network.cloud_mqtt.broker_host
        self.port = int(port or db_config_repo.get_system_config("cloud_mqtt.broker_port") or yaml_settings.network.cloud_mqtt.broker_port)
        self.username = db_config_repo.get_system_config("cloud_mqtt.username") or yaml_settings.network.cloud_mqtt.username or None
        self.password = db_config_repo.get_system_config("cloud_mqtt.password") or yaml_settings.network.cloud_mqtt.password or None
        self.client_id = db_config_repo.get_system_config("cloud_mqtt.client_id") or yaml_settings.network.cloud_mqtt.client_id or "GW-TAU-01-CLOUD"
        self.publish_topic_prefix = publish_topic_prefix or db_config_repo.get_system_config("cloud_mqtt.publish_topic_prefix") or yaml_settings.network.cloud_mqtt.publish_topic_prefix
        self.qos = int(db_config_repo.get_system_config("cloud_mqtt.qos") or yaml_settings.network.cloud_mqtt.qos)
        self.reconnect_delay_sec = int(db_config_repo.get_system_config("cloud_mqtt.reconnect_delay_sec") or yaml_settings.network.cloud_mqtt.reconnect_delay_sec)

        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None

    async def start(self):
        """啟動桃捷雲 MQTT 拋轉任務"""
        self._running = True
        self._worker_task = asyncio.create_task(self._publish_loop())
        logger.info(
            f"[CloudMQTTService] Cloud MQTT Forwarder started. "
            f"Target Cloud Broker: {self.host}:{self.port}, Topic Prefix: '{self.publish_topic_prefix}'"
        )

    async def stop(self):
        """停止桃捷雲 MQTT 拋轉"""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("[CloudMQTTService] Cloud MQTT Forwarder stopped.")

    async def push_telemetry(self, payload: Dict[str, Any], topic_suffix: Optional[str] = None):
        """
        將 PFC200 點位資料寫入佇列準備拋轉至桃捷雲
        :param payload: JSON 點位封包
        :param topic_suffix: 子 Topic 訊息，如 'car1102/pos1' 或 '101/data'
        """
        if not self._running:
            return
        await self._queue.put({"payload": payload, "topic_suffix": topic_suffix})

    async def _publish_loop(self):
        """Cloud MQTT 連線與批次拋轉 Loop (含自動重連)"""
        while self._running:
            try:
                logger.info(f"[CloudMQTTService] Connecting to Cloud MQTT Broker at {self.host}:{self.port}...")
                
                client_kwargs: Dict[str, Any] = {
                    "hostname": self.host,
                    "port": self.port,
                    "identifier": self.client_id
                }
                if self.username:
                    client_kwargs["username"] = self.username
                if self.password:
                    client_kwargs["password"] = self.password

                async with aiomqtt.Client(**client_kwargs) as client:
                    logger.info(f"[CloudMQTTService] Successfully connected to Cloud MQTT Broker ({self.host}:{self.port})!")
                    
                    while self._running:
                        item = await self._queue.get()
                        try:
                            payload = item["payload"]
                            suffix = item.get("topic_suffix")
                            
                            if suffix:
                                topic = f"{self.publish_topic_prefix}/{suffix}".strip("/")
                            else:
                                topic = self.publish_topic_prefix

                            payload_str = json.dumps(payload, ensure_ascii=False)
                            await client.publish(topic, payload_str, qos=self.qos)
                            # logger.info(f"[CloudMQTTService] Forwarded data to 桃捷雲 topic '{topic}' successfully.")
                        except Exception as pub_err:
                            logger.error(f"[CloudMQTTService] Error publishing to Cloud MQTT: {pub_err}")
                        finally:
                            self._queue.task_done()

            except asyncio.CancelledError:
                break
            except aiomqtt.MqttError as err:
                logger.warning(f"[CloudMQTTService] Cloud MQTT Connection error: {err}. Reconnecting in {self.reconnect_delay_sec}s...")
                await asyncio.sleep(self.reconnect_delay_sec)
            except Exception as e:
                logger.error(f"[CloudMQTTService] Unexpected error in Cloud MQTT loop: {e}. Reconnecting in {self.reconnect_delay_sec}s...")
                await asyncio.sleep(self.reconnect_delay_sec)

cloud_mqtt_service = CloudMQTTService()
