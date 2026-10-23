import asyncio
import json
import time
from typing import Dict, Any, Optional, List
import aiomqtt
from app.core.logger import logger
from app.services.equipment_manager import equipment_manager
from app.services.sqlite_writer import sqlite_writer
from app.services.cloud_mqtt_service import cloud_mqtt_service
from app.services.equipment_event_service import equipment_event_service
from app.database.db_config_repo import db_config_repo

from app.core.config_yaml import yaml_settings

class GatewayMQTTService:
    """
    MQTT Subscriber Service:
    - 專責連線 Mosquitto / Local MQTT Broker (1883)
    - 訂閱 PFC200 設備的主題 (設定於 gateway.yaml)
    - 將收到的 Telemetry JSON 資料發送給 DeviceManager 更新心跳
    - 將數據推入 sqlite_writer 的 asyncio.Queue 記憶體佇列
    """
    def __init__(self):
        self.reload_config()

        self._running = False
        self.is_connected = False
        self._listener_task: Optional[asyncio.Task] = None
        # 異動存記憶體快取 (Delta Saving Cache): "eq_id:sensor_code" -> last_value
        self._last_sensor_values: Dict[str, float] = {}

    def reload_config(self):
        """重新讀取 DB 最新 MQTT 設定"""
        db_host = db_config_repo.get_system_config("gateway_mqtt.broker_host") or db_config_repo.get_system_config("broker_mqtt.broker_host")
        self.host = db_host or "127.0.0.1"

        db_port = db_config_repo.get_system_config("gateway_mqtt.broker_port") or db_config_repo.get_system_config("broker_mqtt.broker_port")
        self.port = int(db_port or 1883)

        db_topic = db_config_repo.get_system_config("gateway_mqtt.topic_prefix") or db_config_repo.get_system_config("broker_mqtt.topic_prefix")
        self.topic_prefix = db_topic or "MQT/TRA/OTR/TRC/+/+"
        
        db_clean = db_config_repo.get_system_config("gateway_mqtt.clean_session") or db_config_repo.get_system_config("broker_mqtt.clean_session")
        if db_clean is not None:
            self.clean_session = str(db_clean).lower() in ("true", "1")
        else:
            self.clean_session = True

        logger.info(f"[GatewayMQTTService] Config reloaded: Host={self.host}:{self.port}, Topic='{self.topic_prefix}', CleanSession={self.clean_session}")

    async def start(self):
        """啟動 MQTT 監聽任務"""
        self.reload_config()
        self._running = True
        self._listener_task = asyncio.create_task(self._listen_loop())
        logger.info(f"[GatewayMQTTService] MQTT Service started. Targeting Broker {self.host}:{self.port}, Topic: '{self.topic_prefix}', CleanSession: {self.clean_session}")

    async def stop(self):
        """停止 MQTT 監聽"""
        self._running = False
        self.is_connected = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        logger.info("[GatewayMQTTService] MQTT Service stopped.")

    async def restart(self):
        """重載設定並重新連線 MQTT 監聽」"""
        logger.info("[GatewayMQTTService] Restarting MQTT Service with updated configuration...")
        await self.stop()
        await self.start()

    async def _listen_loop(self):
        """MQTT 非同步監聽與自動斷線重連 Loop"""
        reconnect_interval = 5
        while self._running:
            try:
                logger.info(f"[GatewayMQTTService] Connecting to MQTT Broker at {self.host}:{self.port}...")
                async with aiomqtt.Client(self.host, port=self.port, clean_session=self.clean_session) as client:
                    self.is_connected = True
                    logger.info(f"[GatewayMQTTService] Successfully connected to MQTT Broker! Subscribing to '{self.topic_prefix}'...")
                    await client.subscribe(self.topic_prefix)
 
                    async for message in client.messages:
                        if not self._running:
                            break
                        await self._handle_message(message)
 
            except asyncio.CancelledError:
                break
            except aiomqtt.MqttError as err:
                logger.warning(f"[GatewayMQTTService] MQTT Connection error: {err}. Reconnecting in {reconnect_interval}s...")
                await asyncio.sleep(reconnect_interval)
            except Exception as e:
                logger.error(f"[GatewayMQTTService] Unexpected error in MQTT loop: {e}. Reconnecting in {reconnect_interval}s...")
                await asyncio.sleep(reconnect_interval)
            finally:
                self.is_connected = False

    async def _handle_message(self, message: aiomqtt.Message):
        """解析 MQTT 接收到的 WAGO 標準 JSON 封包並發送至 Queue 與 DeviceManager"""
        try:
            topic_str = str(message.topic)
            payload_str = message.payload.decode("utf-8")
            data = json.loads(payload_str)

            # 1. 提取時間戳記 (支援 Unix Timestamp 字串 "1784802488" 或 數值)
            raw_ts = data.get("timestamp")
            if isinstance(raw_ts, str) and raw_ts.replace('.', '', 1).isdigit():
                timestamp = float(raw_ts)
            elif isinstance(raw_ts, (int, float)):
                timestamp = float(raw_ts)
            else:
                timestamp = time.time()

            # 2. 從 Topic 或 Payload 解出階層與車輛資訊
            parts = topic_str.split("/")
            topic_train_no = parts[2] if len(parts) >= 5 else None
            topic_car_vin = parts[3] if len(parts) >= 5 else None
            topic_end_pos = parts[4] if len(parts) >= 5 else None

            train_no = data.get("trainNo") or topic_train_no
            car_vin = data.get("carVin") or topic_car_vin

            end_pos_str = data.get("endPos") or topic_end_pos
            end_pos = int(end_pos_str) if end_pos_str is not None and str(end_pos_str).isdigit() else None

            # 3. 直接自 SQLite 資料庫對照查詢對應的 eq_id 與 equipment_name (完全由 SQLite DB 設定控制)
            loop = asyncio.get_running_loop()
            eq_info = await loop.run_in_executor(
                None, db_config_repo.get_equipment_by_vin_and_pos, car_vin, end_pos
            )
            eq_id = eq_info["eq_id"]
            equipment_name = eq_info["equipment_name"]

            # 4. 提取 WAGO 標準暫存器點位字典 ("register": {"D40001": "2", ...})
            register_dict = data.get("register") or {}

            sensor_values: Dict[str, Any] = {}
            history_items: List[Dict[str, Any]] = []

            for code, raw_val in register_dict.items():
                try:
                    val = float(raw_val)
                except (ValueError, TypeError):
                    val = 0.0

                # 1. 保持即時狀態記憶體 100% 刷新 (給 Web UI / REST API 秒級顯示)
                sensor_values[code] = val

                # 2. 異動存檢查 (Delta Saving Check)：僅當數值有變化時才寫入 SQLite 歷史庫 (sensor_histories)
                sensor_key = f"{eq_id}:{code}"
                last_val = self._last_sensor_values.get(sensor_key)

                if last_val is None or abs(val - last_val) >= 0.0001:
                    self._last_sensor_values[sensor_key] = val
                    history_items.append({
                        "car_vin": car_vin,
                        "car_no": int(car_vin[1]) if car_vin and len(car_vin) >= 2 and car_vin[1].isdigit() else None,
                        "end_pos": end_pos,
                        "sensor_code": code,
                        "sensor_value": val,
                        "recorded_at": timestamp,
                        "sensor_name": None,
                        "sensor_unit": None,
                        "equipment_name": equipment_name
                    })

            # 5. 更新 EquipmentManager 心跳與狀態
            equipment_manager.update_telemetry(eq_id, {
                "equipment_id": eq_id,
                "equipment_name": equipment_name,
                "train_no": str(train_no) if train_no else None,
                "car_vin": car_vin,
                "end_pos": end_pos,
                "sensors": sensor_values,
                "timestamp": timestamp
            })

            # 6. 更新 SQLite 即時點位與寫入 Queue 佇列
            if sensor_values:
                await loop.run_in_executor(None, db_config_repo.update_sensor_values, sensor_values)

            if history_items:
                await sqlite_writer.push_many(history_items)

            # 6.1 處理 PLC Word 變動事件 (寫入 SQLite equipment_events 表)
            events = equipment_event_service.process_registers(car_vin, end_pos, register_dict, timestamp)
            if events:
                event_count = await loop.run_in_executor(None, equipment_event_service.save_events, events)
                if event_count > 0:
                    logger.info(f"[GatewayMQTTService] 成功記錄 {event_count} 筆設備狀態/警報變動事件 ({car_vin}/{end_pos})")

            # 7. 拋轉 (Forward) 資料至桃捷雲 Cloud MQTT Broker
            if yaml_settings.network.cloud_mqtt.enabled:
                topic_suffix = f"{car_vin}/{end_pos}" if car_vin and end_pos is not None else str(eq_id)
                await cloud_mqtt_service.push_telemetry(data, topic_suffix=topic_suffix)

            logger.debug(f"[GatewayMQTTService] Received WAGO MQTT ({eq_id} | carVin:{car_vin} | endPos:{end_pos}): Queued {len(history_items)} registers.")

        except json.JSONDecodeError:
            logger.warning(f"[GatewayMQTTService] Non-JSON payload received on topic {message.topic}: {message.payload}")
        except Exception as e:
            logger.error(f"[GatewayMQTTService] Error processing MQTT payload: {e}")

    async def publish_message(self, topic: str, payload: str, qos: int = 0, retain: bool = False):
        """將訊息發布至 Local MQTT Broker"""
        try:
            async with aiomqtt.Client(self.host, port=self.port) as client:
                await client.publish(topic, payload, qos=qos, retain=retain)
                logger.info(f"[GatewayMQTTService] Successfully published message to Local Broker on topic '{topic}'")
        except Exception as e:
            logger.error(f"[GatewayMQTTService] Failed to publish message to Local Broker on topic '{topic}': {e}")

    async def publish_messages(self, messages: List[Dict[str, Any]], delay_sec: float = 0.05):
        """批次將多筆訊息發布至 Local MQTT Broker (共用單一連線，每筆間隔微延遲避免塞車)"""
        if not messages:
            return
        try:
            async with aiomqtt.Client(self.host, port=self.port) as client:
                for idx, msg in enumerate(messages):
                    topic = msg.get("topic")
                    payload = msg.get("payload")
                    qos = msg.get("qos", 0)
                    retain = msg.get("retain", False)
                    if topic and payload is not None:
                        await client.publish(topic, payload, qos=qos, retain=retain)
                        logger.info(f"[GatewayMQTTService] Successfully published message to Local Broker on topic '{topic}'")
                    if delay_sec > 0 and idx < len(messages) - 1:
                        await asyncio.sleep(delay_sec)
        except Exception as e:
            logger.error(f"[GatewayMQTTService] Failed to batch publish messages to Local Broker: {e}")

    async def publish_initial_values(self, db: Optional[Any] = None) -> Dict[str, Any]:
        """
        將資料庫中 sensorType 為 INITIAL 的初始值暫存器，
        透過 MQTT 發布至所有啟用的設備 (8 台 PLC)。
        Topic 格式：TYMC/AIR/INI/{trainNo}/{carVin}/{endPos}
        """
        from collections import defaultdict
        from app.database.session import SessionLocal
        from app.models.car_model import Car
        from app.models.equipment_model import Equipment
        from app.models.sensor_model import Sensor

        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        try:
            # 1. 查詢所有啟用車廂與設備
            equipments = (
                db.query(Equipment, Car)
                .join(Car, Equipment.carId == Car.id)
                .filter(Equipment.isActive == True, Car.isActive == True)
                .all()
            )

            if not equipments:
                logger.warning("[GatewayMQTTService] No active equipments found to publish initial values.")
                return {"count": 0, "targets": []}

            # 2. 查詢所有 INITIAL 感測器
            initial_sensors = (
                db.query(Sensor)
                .filter(Sensor.sensorType == "INITIAL", Sensor.isActive == True)
                .all()
            )

            # 依 equipmentId 分組暫存器
            eq_sensor_map = defaultdict(dict)
            for s in initial_sensors:
                val: Any = s.sensorValue or 0
                if isinstance(val, float) and val.is_integer():
                    val = int(val)
                eq_sensor_map[s.equipmentId][s.sensorCode] = val

            mqtt_messages = []
            published_targets = []
            current_timestamp = int(time.time())

            for eq, car in equipments:
                train_no = str(car.trainCode or "109").strip()
                if train_no.upper().startswith("P"):
                    train_no = train_no[1:]

                car_vin = str(car.carVin or car.carNo or "")
                end_pos = eq.endPos
                car_no_val = int(car.carVin) if car.carVin and str(car.carVin).isdigit() else (car.carNo or 0)

                topic = f"TYMC/AIR/INI/{train_no}/{car_vin}/{end_pos}"
                registers = eq_sensor_map.get(eq.id, {})

                payload = {
                    "events": "set_value",
                    "timestamp": current_timestamp,
                    "trainCode": train_no,
                    "carNo": car_no_val,
                    "endPos": end_pos,
                    "register": registers
                }

                mqtt_messages.append({
                    "topic": topic,
                    "payload": json.dumps(payload, ensure_ascii=False),
                    "qos": 1,
                    "retain": True
                })
                published_targets.append(topic)

            await self.publish_messages(mqtt_messages)
            logger.info(f"[GatewayMQTTService] Successfully published initial values to {len(mqtt_messages)} PLC(s).")
            return {"count": len(mqtt_messages), "targets": published_targets}
        except Exception as e:
            logger.error(f"[GatewayMQTTService] Failed to publish initial values: {e}")
            raise e
        finally:
            if close_db:
                db.close()

gateway_mqtt_service = GatewayMQTTService()

