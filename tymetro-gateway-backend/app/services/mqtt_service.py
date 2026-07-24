import asyncio
import json
import time
from typing import Dict, Any, Optional, List
import aiomqtt
from app.core.logger import logger
from app.services.equipment_manager import equipment_manager
from app.services.sqlite_writer import sqlite_writer
from app.services.cloud_mqtt_service import cloud_mqtt_service
from app.database.db_config_repo import db_config_repo

from app.core.config_yaml import yaml_settings

class MQTTService:
    """
    MQTT Subscriber Service:
    - 專責連線 Mosquitto / Local MQTT Broker (1883)
    - 訂閱 PFC200 設備的主題 (設定於 gateway.yaml)
    - 將收到的 Telemetry JSON 資料發送給 DeviceManager 更新心跳
    - 將數據推入 sqlite_writer 的 asyncio.Queue 記憶體佇列
    """
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        topic_prefix: Optional[str] = None
    ):
        self.host = host or db_config_repo.get_system_config("mqtt.broker_host") or yaml_settings.network.mqtt.broker_host
        self.port = int(port or db_config_repo.get_system_config("mqtt.broker_port") or yaml_settings.network.mqtt.broker_port)
        self.topic_prefix = topic_prefix or db_config_repo.get_system_config("mqtt.topic_prefix") or yaml_settings.network.mqtt.topic_prefix
        self._running = False
        self._listener_task: Optional[asyncio.Task] = None
        # 異動存記憶體快取 (Delta Saving Cache): "eq_id:sensor_code" -> last_value
        self._last_sensor_values: Dict[str, float] = {}

    async def start(self):
        """啟動 MQTT 監聽任務"""
        self._running = True
        self._listener_task = asyncio.create_task(self._listen_loop())
        logger.info(f"[MQTTService] MQTT Service started. Targeting Broker {self.host}:{self.port}, Topic: '{self.topic_prefix}'")

    async def stop(self):
        """停止 MQTT 監聽"""
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        logger.info("[MQTTService] MQTT Service stopped.")

    async def _listen_loop(self):
        """MQTT 非同步監聽與自動斷線重連 Loop"""
        reconnect_interval = 5
        while self._running:
            try:
                logger.info(f"[MQTTService] Connecting to MQTT Broker at {self.host}:{self.port}...")
                async with aiomqtt.Client(self.host, port=self.port) as client:
                    logger.info(f"[MQTTService] Successfully connected to MQTT Broker! Subscribing to '{self.topic_prefix}'...")
                    await client.subscribe(self.topic_prefix)

                    async for message in client.messages:
                        if not self._running:
                            break
                        await self._handle_message(message)

            except asyncio.CancelledError:
                break
            except aiomqtt.MqttError as err:
                logger.warning(f"[MQTTService] MQTT Connection error: {err}. Reconnecting in {reconnect_interval}s...")
                await asyncio.sleep(reconnect_interval)
            except Exception as e:
                logger.error(f"[MQTTService] Unexpected error in MQTT loop: {e}. Reconnecting in {reconnect_interval}s...")
                await asyncio.sleep(reconnect_interval)

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
            eq_info = db_config_repo.get_equipment_by_vin_and_pos(car_vin, end_pos)
            eq_id = eq_info["eq_id"]
            equipment_name = eq_info["equipment_name"]

            # 4. 提取 WAGO 標準暫存器點位字典 ("register": {"D40001": "2", ...})
            register_dict = data.get("register") or {}

            sensor_values: Dict[str, Any] = {}
            history_items: List[Dict[str, Any]] = []

            for code, raw_val in register_dict.items():
                try:
                    val = float(raw_val)
                    # 處理 INT16 Signed 補碼 (若 > 32767 轉為負數)
                    if val > 32767:
                        val -= 65536
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
                db_config_repo.update_sensor_values(sensor_values)

            if history_items:
                await sqlite_writer.push_many(history_items)

            # 7. 拋轉 (Forward) 資料至桃捷雲 Cloud MQTT Broker
            if yaml_settings.network.cloud_mqtt.enabled:
                topic_suffix = f"{car_vin}/{end_pos}" if car_vin and end_pos is not None else str(eq_id)
                await cloud_mqtt_service.push_telemetry(data, topic_suffix=topic_suffix)

            #logger.info(f"[MQTTService] Received WAGO MQTT ({eq_id} | carVin:{car_vin} | endPos:{end_pos}): Queued {len(history_items)} registers.")

        except json.JSONDecodeError:
            logger.warning(f"[MQTTService] Non-JSON payload received on topic {message.topic}: {message.payload}")
        except Exception as e:
            logger.error(f"[MQTTService] Error processing MQTT payload: {e}")

mqtt_service = MQTTService()
