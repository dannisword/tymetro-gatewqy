import asyncio
import json
import time
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
        self.keepalive = int(db_config_repo.get_system_config("cloud_mqtt.keepalive") or yaml_settings.network.cloud_mqtt.keepalive)

        db_clean = db_config_repo.get_system_config("cloud_mqtt.clean_session")
        if db_clean is not None:
            self.clean_session = str(db_clean).lower() in ("true", "1")
        else:
            self.clean_session = yaml_settings.network.cloud_mqtt.clean_session

        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._sent_commands_cache: Dict[tuple, float] = {}

    def reload_config(self):
        """重新讀取 DB / yaml_settings 最新 Cloud MQTT 設定"""
        self.host = db_config_repo.get_system_config("cloud_mqtt.broker_host") or yaml_settings.network.cloud_mqtt.broker_host
        self.port = int(db_config_repo.get_system_config("cloud_mqtt.broker_port") or yaml_settings.network.cloud_mqtt.broker_port)
        self.username = db_config_repo.get_system_config("cloud_mqtt.username") or yaml_settings.network.cloud_mqtt.username or None
        self.password = db_config_repo.get_system_config("cloud_mqtt.password") or yaml_settings.network.cloud_mqtt.password or None
        self.client_id = db_config_repo.get_system_config("cloud_mqtt.client_id") or yaml_settings.network.cloud_mqtt.client_id or "GW-TAU-01-CLOUD"
        self.publish_topic_prefix = db_config_repo.get_system_config("cloud_mqtt.publish_topic_prefix") or yaml_settings.network.cloud_mqtt.publish_topic_prefix
        self.qos = int(db_config_repo.get_system_config("cloud_mqtt.qos") or yaml_settings.network.cloud_mqtt.qos)
        self.reconnect_delay_sec = int(db_config_repo.get_system_config("cloud_mqtt.reconnect_delay_sec") or yaml_settings.network.cloud_mqtt.reconnect_delay_sec)
        self.keepalive = int(db_config_repo.get_system_config("cloud_mqtt.keepalive") or yaml_settings.network.cloud_mqtt.keepalive)
        
        db_clean = db_config_repo.get_system_config("cloud_mqtt.clean_session")
        if db_clean is not None:
            self.clean_session = str(db_clean).lower() in ("true", "1")
        else:
            self.clean_session = yaml_settings.network.cloud_mqtt.clean_session

        logger.info(f"[CloudMQTTService] Config reloaded: Host={self.host}:{self.port}, Topic='{self.publish_topic_prefix}', ClientID='{self.client_id}', Keepalive={self.keepalive}, CleanSession={self.clean_session}")

    async def start(self):
        """啟動桃捷雲 MQTT 拋轉任務"""
        self.reload_config()
        self._running = True
        self._worker_task = asyncio.create_task(self._publish_loop())
        logger.info(
            f"[CloudMQTTService] Cloud MQTT Forwarder started. "
            f"Target Cloud Broker: {self.host}:{self.port}, Topic Prefix: '{self.publish_topic_prefix}', CleanSession: {self.clean_session}"
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

    async def restart(self):
        """重載設定並重新連線 Cloud MQTT 拋轉"""
        logger.info("[CloudMQTTService] Restarting Cloud MQTT Service with updated configuration...")
        await self.stop()
        await self.start()

    async def push_telemetry(self, payload: Dict[str, Any], topic_suffix: Optional[str] = None):
        """
        將 PFC200 點位資料寫入佇列準備拋轉至桃捷雲
        :param payload: JSON 點位封包
        :param topic_suffix: 子 Topic 訊息，如 'MQT/TRA/OTR/TRC/102/1102'
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
                    "identifier": self.client_id,
                    "keepalive": self.keepalive,
                    "clean_session": self.clean_session
                }
                if self.username:
                    client_kwargs["username"] = self.username
                if self.password:
                    client_kwargs["password"] = self.password

                async with aiomqtt.Client(**client_kwargs) as client:
                    logger.info(f"[CloudMQTTService] Successfully connected to Cloud MQTT Broker ({self.host}:{self.port})!")
                    
                    # 訂閱雲端控制指令主題: [publish_topic_prefix]/+/+
                    sub_topic = f"{self.publish_topic_prefix}/+/+"
                    await client.subscribe(sub_topic)
                    logger.info(f"[CloudMQTTService] Subscribed to cloud command topic: '{sub_topic}'")

                    # 啟動背景監聽任務
                    listener_task = asyncio.create_task(self._listen_cloud_messages(client))
                    # 啟動批次拋轉任務
                    try:
                        while self._running:
                            get_task = asyncio.create_task(self._queue.get())
                            done, pending = await asyncio.wait(
                                [listener_task, get_task],
                                return_when=asyncio.FIRST_COMPLETED
                            )

                            if get_task not in done:
                                get_task.cancel()
                                try:
                                    await get_task
                                except asyncio.CancelledError:
                                    pass

                            if listener_task.done():
                                exc = listener_task.exception()
                                if exc:
                                    raise exc
                                else:
                                    raise aiomqtt.MqttError("Cloud message listener stopped unexpectedly")

                            if get_task in done and not get_task.cancelled():
                                item = get_task.result()
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
                                except aiomqtt.MqttError as mqtt_err:
                                    logger.error(f"[CloudMQTTService] Connection lost while publishing to Cloud MQTT: {mqtt_err}")
                                    await self._queue.put(item)
                                    raise mqtt_err
                                except Exception as pub_err:
                                    logger.error(f"[CloudMQTTService] Error publishing to Cloud MQTT: {pub_err}")
                                finally:
                                    self._queue.task_done()
                    finally:
                        listener_task.cancel()
                        try:
                            await listener_task
                        except asyncio.CancelledError:
                            pass

            except asyncio.CancelledError:
                break
            except aiomqtt.MqttError as err:
                logger.warning(f"[CloudMQTTService] Cloud MQTT Connection error: {err}. Reconnecting in {self.reconnect_delay_sec}s...")
                await asyncio.sleep(self.reconnect_delay_sec)
            except Exception as e:
                logger.error(f"[CloudMQTTService] Unexpected error in Cloud MQTT loop: {e}. Reconnecting in {self.reconnect_delay_sec}s...")
                await asyncio.sleep(self.reconnect_delay_sec)

    async def _listen_cloud_messages(self, client: aiomqtt.Client):
        """監聽從雲端 MQTT Broker 傳入的訊息"""
        try:
            async for message in client.messages:
                if not self._running:
                    break
                await self._handle_cloud_message(message)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[CloudMQTTService] Error in cloud message listener: {e}")
            raise

    async def _handle_cloud_message(self, message: aiomqtt.Message):
        """處理雲端傳入的訊息並判斷是否需要轉發"""
        try:
            topic = str(message.topic)
           
            payload_str = message.payload.decode("utf-8")
            
            # 檢查重複指令 (防止當 Local Broker 與 Cloud Broker 為同一個時造成的無窮迴圈/Echo)
            now = time.time()
            self._sent_commands_cache = {k: v for k, v in self._sent_commands_cache.items() if now - v < 5.0}
            cache_key = (topic, payload_str)
            if cache_key in self._sent_commands_cache:
                return
            self._sent_commands_cache[cache_key] = now
            
            # 檢查主題格式是否符合控制指令 (最後一層是否以 R 結尾，例如 1R)
            parts = topic.split("/")
            if len(parts) >= 2 and parts[-1].endswith("R"):
                logger.debug(f"[CloudMQTTService] Received cloud command on topic '{topic}': {payload_str}")
                
                # 新增到 setting logs
                try:
                    from app.database.session import SessionLocal
                    from app.models.setting_log_model import SettingLog
                    from app.models.sensor_model import Sensor
                    
                    setting_type = "雲端控制"
                    val_str = payload_str
                    operator = "Cloud"
                    
                    try:
                        payload_data = json.loads(payload_str)
                        regs = {}
                        if isinstance(payload_data, dict):
                            if "register" in payload_data and isinstance(payload_data["register"], dict):
                                regs = payload_data["register"]
                            else:
                                regs = {k: v for k, v in payload_data.items() if k.startswith("D")}
                                if not regs:
                                    regs = payload_data
                        
                        if regs:
                            first_code = list(regs.keys())[0]
                            first_val = regs[first_code]
                            val_str = str(first_val)
                            
                            db = SessionLocal()
                            try:
                                sensor = db.query(Sensor).filter(Sensor.sensorCode == first_code).first()
                                if sensor and sensor.sensorName:
                                    setting_type = sensor.sensorName
                                else:
                                    setting_type = f"設定 {first_code}"
                            finally:
                                db.close()
                    except Exception as json_err:
                        logger.debug(f"[CloudMQTTService] Payload not parsed as json or register dict: {json_err}")
                    
                    db = SessionLocal()
                    try:
                        log_entry = SettingLog(
                            settingType=setting_type,
                            value=val_str,
                            operator=operator,
                            isNotified=False,
                            topic=topic,
                            payload=payload_str
                        )
                        db.add(log_entry)
                        db.commit()
                        logger.info(f"[CloudMQTTService] Saved setting log: type={setting_type}, value={val_str}")
                    except Exception as db_err:
                        db.rollback()
                        logger.error(f"[CloudMQTTService] Error saving setting log: {db_err}")
                    finally:
                        db.close()
                except Exception as log_err:
                    logger.error(f"[CloudMQTTService] General error writing setting log: {log_err}")

                # 動態導入以防循環參照
                from app.services.mqtt_service import mqtt_service
                await mqtt_service.publish_message(topic, payload_str)
            else:
                # 忽略非指令主題
                pass
        except Exception as e:
            logger.error(f"[CloudMQTTService] Error handling cloud message: {e}")

cloud_mqtt_service = CloudMQTTService()
