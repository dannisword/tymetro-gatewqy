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
    def __init__(self):
        self.reload_config()

        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._sent_commands_cache: Dict[tuple, float] = {}

    def reload_config(self):
        """重新讀取 DB 最新 Cloud MQTT 設定"""
        self.cloud_host = db_config_repo.get_system_config("cloud_mqtt.broker_host") or "127.0.0.1"
        self.cloud_port = int(db_config_repo.get_system_config("cloud_mqtt.broker_port") or 1883)
        self.username = db_config_repo.get_system_config("cloud_mqtt.username") or None
        self.password = db_config_repo.get_system_config("cloud_mqtt.password") or None
        self.client_id = db_config_repo.get_system_config("cloud_mqtt.client_id") or "GW-TAU-01-CLOUD"
        self.cloud_topic_prefix = db_config_repo.get_system_config("cloud_mqtt.cloud_topic_prefix") or "TYMC/CLOUD/101"
        self.qos = int(db_config_repo.get_system_config("cloud_mqtt.qos") or 0)
        self.reconnect_delay_sec = int(db_config_repo.get_system_config("cloud_mqtt.reconnect_delay_sec") or 5)
        self.keepalive = int(db_config_repo.get_system_config("cloud_mqtt.keepalive") or 20)
        
        db_clean = db_config_repo.get_system_config("cloud_mqtt.clean_session")
        if db_clean is not None:
            self.clean_session = str(db_clean).lower() in ("true", "1")
        else:
            self.clean_session = True

        logger.info(f"[CloudMQTTService] Config reloaded: Host={self.cloud_host}:{self.cloud_port}, Topic='{self.cloud_topic_prefix}', ClientID='{self.client_id}', Keepalive={self.keepalive}, CleanSession={self.clean_session}")

    async def start(self):
        """啟動桃捷雲 MQTT 拋轉任務"""
        self.reload_config()
        self._running = True
        self._worker_task = asyncio.create_task(self._publish_loop())
        logger.info(
            f"[CloudMQTTService] Cloud MQTT Forwarder started. "
            f"Target Cloud Broker: {self.cloud_host}:{self.cloud_port}, Topic Prefix: '{self.cloud_topic_prefix}', CleanSession: {self.clean_session}"
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
                logger.info(f"[CloudMQTTService] Connecting to Cloud MQTT Broker at {self.cloud_host}:{self.cloud_port}...")
                
                client_kwargs: Dict[str, Any] = {
                    "hostname": self.cloud_host,
                    "port": self.cloud_port,
                    "identifier": self.client_id,
                    "keepalive": self.keepalive,
                    "clean_session": self.clean_session
                }
                if self.username:
                    client_kwargs["username"] = self.username
                if self.password:
                    client_kwargs["password"] = self.password
 
                async with aiomqtt.Client(**client_kwargs) as client:
                    logger.info(f"[CloudMQTTService] Successfully connected to Cloud MQTT Broker ({self.cloud_host}:{self.cloud_port})!")
                    
                    sub_topic = f"{self.cloud_topic_prefix}/+/+"
                    await client.subscribe(sub_topic)
                    logger.info(f"[CloudMQTTService] Subscribed to cloud command topic: '{sub_topic}'")

                    # gateway 發送任務
                    async def send_worker():
                        while self._running:
                            item = await self._queue.get()
                            try:
                                payload = item["payload"]
                                suffix = item.get("topic_suffix")
                                if suffix:
                                    topic = f"{self.cloud_topic_prefix}/{suffix}".strip("/")
                                else:
                                    topic = self.cloud_topic_prefix

                                payload_str = json.dumps(payload, ensure_ascii=False)
                                await client.publish(topic, payload_str, qos=self.qos)
                            except aiomqtt.MqttError as mqtt_err:
                                logger.error(f"[CloudMQTTService] Connection lost while publishing to Cloud MQTT: {mqtt_err}")
                                await self._queue.put(item)
                                raise mqtt_err
                            except Exception as pub_err:
                                logger.error(f"[CloudMQTTService] Error publishing to Cloud MQTT: {pub_err}")
                            finally:
                                self._queue.task_done()

                    # 同時執行監聽與發送，任一者拋出異常即中斷並重連
                    await asyncio.gather(
                        self._listen_cloud_messages(client),
                        send_worker()
                    )

            except asyncio.CancelledError:
                break
            except aiomqtt.MqttError as err:
                logger.warning(f"[CloudMQTTService] Cloud MQTT Connection error: {err}. Reconnecting in {self.reconnect_delay_sec}s...")
                await asyncio.sleep(self.reconnect_delay_sec)
            except Exception as e:
                logger.error(f"[CloudMQTTService] Unexpected error in Cloud MQTT loop: {e}. Reconnecting in {self.reconnect_delay_sec}s...")
                await asyncio.sleep(self.reconnect_delay_sec)

    async def _listen_cloud_messages(self, client: aiomqtt.Client):
        """監聽並處理從雲端 MQTT Broker 傳入的訊息"""
        try:
            async for message in client.messages:
                if not self._running:
                    break
                try:
                    topic = str(message.topic)
                    payload_str = message.payload.decode("utf-8")
                    
                    # 檢查重複指令 (防止當 Local Broker 與 Cloud Broker 為同一個時造成的無窮迴圈/Echo)
                    now = time.time()
                    self._sent_commands_cache = {k: v for k, v in self._sent_commands_cache.items() if now - v < 5.0}
                    cache_key = (topic, payload_str)
                    if cache_key in self._sent_commands_cache:
                        continue
                    self._sent_commands_cache[cache_key] = now
                    
                    # 檢查主題格式是否符合控制指令 (最後一層是否以 R 結尾，例如 1R)
                    parts = topic.split("/")
                    if len(parts) >= 2 and parts[-1].endswith("R"):
                        logger.debug(f"[CloudMQTTService] Received cloud command on topic '{topic}': {payload_str}")
                        
                        # 1. 儲存設定紀錄至資料庫
                        self._save_setting_log(topic, payload_str)

                        # 2. 轉發至本地 MQTT
                        await self._forward_to_local_mqtt(topic, payload_str, parts)
                    else:
                        # 忽略非指令主題
                        pass
                except Exception as msg_err:
                    logger.error(f"[CloudMQTTService] Error processing message: {msg_err}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[CloudMQTTService] Error in cloud message listener: {e}")
            raise

    def _save_setting_log(self, topic: str, payload_str: str):
        """解析雲端指令 payload 並儲存設定紀錄至資料庫"""
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

    async def _forward_to_local_mqtt(self, topic: str, payload_str: str, parts: list):
        """將雲端指令轉換主題格式並發送至 Gateway 本地 MQTT"""
        try:
            # 動態導入以防循環參照
            from app.services.gateway_mqtt_service import gateway_mqtt_service
            
            # 重新映射 Topic 格式
            # 雲端格式: MQT/TRA/OTR/TRC/102/1102/1R -> 提取 '102', '1102' 和 '1' (從 '1R' 去掉 'R')
            # 轉發本地格式: TYMC/AIR/SET/102/1102/1
            gateway_topic = ''
            if len(parts) >= 7:
                trainNo = parts[4]       # 102 車組
                carVin = parts[5]        # 1102 車廂
                endPos = parts[6].strip('R')        # 1 端點
                gateway_topic = f"TYMC/AIR/SET/{trainNo}/{carVin}/{endPos}"
                logger.debug(f"[CloudMQTTService] Routing cloud command to local topic: '{gateway_topic}' (original: '{topic}')")
            
            await gateway_mqtt_service.publish_message(gateway_topic, payload_str)
        except Exception as e:
            logger.error(f"[CloudMQTTService] Error forwarding message to local MQTT: {e}")

cloud_mqtt_service = CloudMQTTService()
