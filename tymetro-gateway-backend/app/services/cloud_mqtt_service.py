import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import aiomqtt
from app.core.logger import logger
from app.core.config_yaml import yaml_settings
from app.database.db_config_repo import db_config_repo
from app.utils.datetime_util import get_local_now

class CloudMQTTService:
    """
    桃捷雲 Cloud MQTT Forwarder Service:
    - 專責連線至「桃捷雲」 Cloud MQTT Broker
    - 接收內存 Queue 佇列中由 PFC200 送進來的 telemetry 數據，並拋轉 (Publish) 至桃捷雲 Topic

    上行 (Gateway -> Cloud):
    - push_telemetry() 將資料放入 asyncio.Queue，由 _publish_loop 內的 send_worker 逐筆發送
    - 佇列滿 (max_queue_size) 時丟棄最舊資料；封包排隊超過 max_ttl_seconds 亦直接丟棄，只保留最新狀態
    - 發送失敗 (MqttError) 時，未過期且佇列未滿的封包會放回佇列，並觸發重連
    - Topic = {cloud_topic_prefix}/{topic_suffix}；未指定 suffix 則使用 prefix

    下行 (Cloud -> Gateway):
    - 訂閱 {cloud_topic_prefix}/+/+，只處理最後一層以 'R' 結尾的控制指令 (如 '1R')，其餘忽略
    - 指令會先寫入 SettingLog (operator='Cloud')，再轉換 Topic 後轉發至本地 MQTT：
      雲端 MQT/TRA/OTR/TRC/102/1102/1R -> 本地 TYMC/AIR/SET/102/1102/1
    - 僅寫入單一暫存器、且為 PlcCommandService.COMMANDS 已定義的指令 (溫度、擋板、重置、強制開啟等)，改走 PlcCommandService.execute：
      驗證設定值、完成暫存器確認 (設定值型比對寫入值並可重發，觸發型等待旗標為 1；逾時回報 FAILED)、
      SettingLog / AuditLog 格式皆與 Gateway 前端相同，operator='Cloud'，SettingLog 由該流程寫入
    - 其餘指令 (多暫存器、未定義暫存器) 維持原樣轉發至本地 MQTT
    - 5 秒內相同 (topic, payload) 視為重複並略過，避免 Local 與 Cloud 為同一 Broker 時的 Echo 無窮迴圈

    指令結果回報 (Gateway -> Cloud)，僅 payload 帶 commandId 的指令：
    - 收到即回報 ACKED，轉發至本地 MQTT 後依完成暫存器確認，再回報 SUCCESS / FAILED
      回報 Topic：將指令 Topic 最後一層的 'R' 改為 'A' (如 .../1102/1R -> .../1102/1A)，QoS 至少 1
      內容：{commandId, status, error, registers, confirmed, message, ts}，格式見 tymetro-backend/doc/plc_command_protocol.md
    - commandId 於轉發至本地前移除 (PLC 端不需要)；同一 commandId 10 分鐘內重送視為重複並略過
    - 沒有 commandId 的指令維持原行為，不回報

    連線與設定:
    - 設定來自 DB (cloud_mqtt.*)，reload_config() 重新讀取；restart() = stop + start，套用新設定
    - 斷線或例外時，等待 reconnect_delay_sec 秒後自動重連
    - is_connected 反映目前與雲端 Broker 的連線狀態
    - 全域單例：cloud_mqtt_service
    """
    def __init__(self):
        self._max_queue_size = 50
        self._max_ttl_seconds = 30.0
        self.reload_config()

        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self.is_connected = False
        self._worker_task: Optional[asyncio.Task] = None
        self._sent_commands_cache: Dict[tuple, float] = {}
        self._processed_command_ids: Dict[str, float] = {}
        self._command_tasks: set = set()

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
        
        # 佇列大小與過期時間設定 (避免斷線或延遲造成舊封包大量積壓)
        self._max_queue_size = int(db_config_repo.get_system_config("cloud_mqtt.max_queue_size") or 50)
        self._max_ttl_seconds = float(db_config_repo.get_system_config("cloud_mqtt.max_ttl_seconds") or 30.0)

        db_clean = db_config_repo.get_system_config("cloud_mqtt.clean_session")
        if db_clean is not None:
            self.clean_session = str(db_clean).lower() in ("true", "1")
        else:
            self.clean_session = True

        logger.info(f"[CloudMQTTService] Config reloaded: Host={self.cloud_host}:{self.cloud_port}, Topic='{self.cloud_topic_prefix}', ClientID='{self.client_id}', MaxQueue={self._max_queue_size}, MaxTTL={self._max_ttl_seconds}s, Keepalive={self.keepalive}, CleanSession={self.clean_session}")

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
        self.is_connected = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        # 停止時清空佇列殘留
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except (asyncio.QueueEmpty, ValueError):
                break
        logger.info("[CloudMQTTService] Cloud MQTT Forwarder stopped.")

    async def restart(self):
        """重載設定並重新連線 Cloud MQTT 拋轉"""
        logger.info("[CloudMQTTService] Restarting Cloud MQTT Service with updated configuration...")
        await self.stop()
        await self.start()

    async def push_telemetry(self, payload: Dict[str, Any], topic_suffix: Optional[str] = None):
        """
        將 PFC200 點位資料寫入佇列準備拋轉至桃捷雲
        - 佇列滿時自動丟棄最舊資料 (Drop Oldest)，確保永遠只轉發最新狀態
        :param payload: JSON 點位封包
        :param topic_suffix: 子 Topic 訊息，如 'MQT/TRA/OTR/TRC/102/1102'
        """
        if not self._running:
            return

        # 佇列已滿時丟棄最舊的資料 (Drop Oldest)，防止記憶體膨脹與歷史封包塞車
        while self._queue.qsize() >= self._max_queue_size:
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except (asyncio.QueueEmpty, ValueError):
                break

        await self._queue.put({
            "payload": payload,
            "topic_suffix": topic_suffix,
            "enqueued_at": time.time()
        })

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
                    self.is_connected = True
                    logger.info(f"[CloudMQTTService] Successfully connected to Cloud MQTT Broker ({self.cloud_host}:{self.cloud_port})!")
                    
                    sub_topic = f"{self.cloud_topic_prefix}/+/+"
                    await client.subscribe(sub_topic)
                    logger.info(f"[CloudMQTTService] Subscribed to cloud command topic: '{sub_topic}'")

                    # gateway 發送任務
                    async def send_worker():
                        while self._running:
                            item = await self._queue.get()
                            try:
                                now = time.time()
                                enqueued_at = item.get("enqueued_at", now)

                                # 檢查封包是否過期 (超過 max_ttl_seconds 則丟棄，優先發送最新即時數據)
                                if (now - enqueued_at) > self._max_ttl_seconds:
                                    logger.warning(
                                        f"[CloudMQTTService] Dropping stale telemetry for cloud (queued {now - enqueued_at:.1f}s ago > TTL {self._max_ttl_seconds}s)"
                                    )
                                    continue

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
                                # 若尚未過期且佇列未滿，才放回佇列
                                if (time.time() - item.get("enqueued_at", 0)) <= self._max_ttl_seconds:
                                    if self._queue.qsize() < self._max_queue_size:
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
            finally:
                self.is_connected = False

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
                        
                        command = self._parse_tracked_command(payload_str)
                        if command and self._is_duplicate_command_id(command["commandId"]):
                            logger.warning(f"[CloudMQTTService] Duplicate commandId ignored: {command['commandId']}")
                            continue

                        # PlcCommandService 已定義的設定指令 (含溫度)，與 Gateway 前端共用同一套流程
                        setting_cmd = self._parse_setting_command(payload_str, parts)

                        # 1. 儲存設定紀錄至資料庫 (共用流程自行寫入設定紀錄)
                        if setting_cmd is None:
                            self._save_setting_log(topic, payload_str, command["commandId"] if command else None)

                        if setting_cmd:
                            task = asyncio.create_task(self._run_setting_command(client, topic, command, setting_cmd))
                            self._command_tasks.add(task)
                            task.add_done_callback(self._command_tasks.discard)
                        elif command:
                            # 帶 commandId 的指令：背景執行 ACK -> 轉發 -> 確認 -> 回報，不阻塞後續訊息
                            task = asyncio.create_task(self._run_tracked_command(client, topic, parts, command))
                            self._command_tasks.add(task)
                            task.add_done_callback(self._command_tasks.discard)
                        else:
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

    def _save_setting_log(self, topic: str, payload_str: str, command_id: Optional[str] = None):
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
                    recordedAt=get_local_now(),
                    topic=topic,
                    payload=payload_str,
                    commandId=command_id,
                    status="ACKED" if command_id else None,
                    ackedAt=datetime.now(timezone.utc).replace(tzinfo=None) if command_id else None,
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

    @staticmethod
    def _parse_tracked_command(payload_str: str) -> Optional[Dict[str, Any]]:
        """payload 帶 commandId 時回傳 {commandId, data}，否則回傳 None (舊版指令不回報)"""
        try:
            data = json.loads(payload_str)
        except ValueError:
            return None
        if isinstance(data, dict) and isinstance(data.get("commandId"), str) and data["commandId"]:
            return {"commandId": data["commandId"], "data": data}
        return None

    @staticmethod
    def _parse_single_register_command(payload_str: str, parts: list) -> Optional[Dict[str, Any]]:
        """只寫入單一暫存器的指令回傳 {register, raw, trainCode, carNo, endPos, event}，否則回傳 None (車組/車廂/端點取自 Topic)"""
        try:
            data = json.loads(payload_str)
        except ValueError:
            return None
        if not isinstance(data, dict) or len(parts) < 7:
            return None
        regs = data.get("register")
        if not isinstance(regs, dict) or len(regs) != 1:
            return None
        register, raw = next(iter(regs.items()))
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            return None
        end_pos = parts[6].rstrip("R")
        if not (parts[5].isdigit() and end_pos.isdigit()):
            return None
        event = data.get("events")
        return {
            "register": register,
            "raw": raw,
            "trainCode": parts[4],
            "carNo": int(parts[5]),
            "endPos": int(end_pos),
            "event": event if isinstance(event, str) and event else None,
        }

    @classmethod
    def _parse_setting_command(cls, payload_str: str, parts: list) -> Optional[Dict[str, Any]]:
        """
        PlcCommandService.COMMANDS 已定義的單一暫存器設定指令 (溫度、擋板、重置、強制開啟等)，
        回傳 {command, value, register, raw, trainCode, carNo, endPos, event}，否則回傳 None
        """
        from app.services.plc_command_service import COMMAND_BY_REGISTER, COMMANDS

        cmd = cls._parse_single_register_command(payload_str, parts)
        if cmd is None or cmd["register"] not in COMMAND_BY_REGISTER:
            return None
        command = COMMAND_BY_REGISTER[cmd["register"]]
        return {**cmd, "command": command, "value": COMMANDS[command].from_register_value(cmd["raw"])}

    def _is_duplicate_command_id(self, command_id: str) -> bool:
        now = time.time()
        self._processed_command_ids = {k: v for k, v in self._processed_command_ids.items() if now - v < 600}
        if command_id in self._processed_command_ids:
            return True
        self._processed_command_ids[command_id] = now
        return False

    def _update_setting_log_status(self, command_id: str, status: str, error: Optional[str]):
        """依回報結果更新本地設定紀錄 (終態不再變更)"""
        try:
            from app.database.session import SessionLocal
            from app.models.setting_log_model import SettingLog

            db = SessionLocal()
            try:
                db.query(SettingLog).filter(
                    SettingLog.commandId == command_id,
                    SettingLog.status.notin_(("SUCCESS", "FAILED")),
                ).update({
                    SettingLog.status: status,
                    SettingLog.errorMessage: error[:500] if error else None,
                    SettingLog.finishedAt: datetime.now(timezone.utc).replace(tzinfo=None),
                }, synchronize_session=False)
                db.commit()
            except Exception as db_err:
                db.rollback()
                logger.error(f"[CloudMQTTService] Error updating setting log status: {db_err}")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"[CloudMQTTService] General error updating setting log status: {e}")

    async def _report_command(
        self,
        client: aiomqtt.Client,
        topic: str,
        command_id: str,
        status: str,
        registers: Dict[str, Any],
        error: Optional[str] = None,
        confirmed: Optional[bool] = None,
        message: Optional[str] = None,
        plc: Optional[Dict[str, Any]] = None,
    ):
        """將指令狀態回報至雲端 (指令 Topic 的 R 改為 A)"""
        if status in ("SUCCESS", "FAILED"):
            self._update_setting_log_status(command_id, status, error)
        result_topic = f"{topic[:-1]}A"
        body = {
            "commandId": command_id,
            "status": status,
            "error": error,
            "registers": registers,
            "confirmed": confirmed,
            "message": message,
            "plc": plc,
            "ts": int(time.time()),
        }
        try:
            await client.publish(result_topic, json.dumps(body, ensure_ascii=False), qos=max(self.qos, 1))
            logger.info(f"[CloudMQTTService] Reported command {command_id} -> {status} on '{result_topic}'")
        except Exception as e:
            logger.error(f"[CloudMQTTService] Failed to report command {command_id} ({status}): {e}")

    async def _run_tracked_command(self, client: aiomqtt.Client, topic: str, parts: list, command: Dict[str, Any]):
        """帶 commandId 的雲端指令：回報 ACKED -> 轉發至本地 -> 以完成暫存器確認 -> 回報結果"""
        command_id: str = command["commandId"]
        data: Dict[str, Any] = command["data"]
        registers = data.get("register") if isinstance(data.get("register"), dict) else {}

        await self._report_command(client, topic, command_id, "ACKED", registers)

        confirmation = None
        db = None
        try:
            from app.database.session import SessionLocal
            from app.services.plc_command_service import PlcCommandService

            db = SessionLocal()
            service = PlcCommandService(db)
            first_register = next(iter(registers), None)
            end_pos = data.get("endPos")
            if first_register and isinstance(end_pos, int):
                # 須在發送前取得完成暫存器基準值，避免把舊的完成狀態當成本次結果
                confirmation = service.prepare_cloud_confirmation(data.get("carNo"), end_pos, first_register)

            local_payload = json.dumps({k: v for k, v in data.items() if k != "commandId"}, ensure_ascii=False)
            if not await self._forward_to_local_mqtt(topic, local_payload, parts):
                await self._report_command(client, topic, command_id, "FAILED", registers, error="轉發至本地 MQTT 失敗")
                return

            if confirmation is None:
                await self._report_command(
                    client, topic, command_id, "SUCCESS", registers,
                    confirmed=False, message="已轉發至本地 MQTT，此指令無完成暫存器可確認",
                )
                return

            ok, message = await service.wait_cloud_confirmation(confirmation)
            await self._report_command(
                client, topic, command_id, "SUCCESS" if ok else "FAILED", registers,
                error=None if ok else message, confirmed=ok, message=message, plc=service.last_plc_values,
            )
        except Exception as e:
            logger.error(f"[CloudMQTTService] Tracked command {command_id} failed: {e}")
            await self._report_command(client, topic, command_id, "FAILED", registers, error=f"Gateway 處理失敗: {e}")
        finally:
            if db is not None:
                db.close()

    async def _run_setting_command(
        self, client: aiomqtt.Client, topic: str, command: Optional[Dict[str, Any]], cmd: Dict[str, Any]
    ):
        """共用流程的設定指令：有 commandId 時回報 ACKED -> SUCCESS / FAILED，沒有則只執行不回報"""
        command_id: Optional[str] = command["commandId"] if command else None
        registers = {cmd["register"]: cmd["raw"]}

        if command_id:
            await self._report_command(client, topic, command_id, "ACKED", registers)

        db = None
        try:
            from app.database.session import SessionLocal

            db = SessionLocal()
            ok, confirmed, message, plc = await self._execute_setting_command(db, cmd, command_id)
        except Exception as e:
            logger.error(f"[CloudMQTTService] Setting command {command_id or topic} failed: {e}")
            ok, confirmed, message, plc = False, None, f"Gateway 處理失敗: {e}", None
        finally:
            if db is not None:
                db.close()

        if command_id:
            await self._report_command(
                client, topic, command_id, "SUCCESS" if ok else "FAILED", registers,
                error=None if ok else message, confirmed=confirmed, message=message, plc=plc,
            )
        elif not ok:
            logger.error(f"[CloudMQTTService] Setting command {topic} failed: {message}")

    @staticmethod
    async def _execute_setting_command(db, cmd: Dict[str, Any], command_id: Optional[str]) -> tuple:
        """透過 PlcCommandService 執行 (與 Gateway 前端共用)，回傳 (是否成功, 是否經 PLC 確認, 訊息, PLC 點位值)"""
        from app.schemas.plc_command_schema import PlcCommandRequest
        from app.services.plc_command_service import PlcCommandError, PlcCommandService

        try:
            result = await PlcCommandService(db).execute(
                PlcCommandRequest(
                    command=cmd["command"],
                    carNo=cmd["carNo"],
                    endPos=cmd["endPos"],
                    trainCode=cmd["trainCode"],
                    value=cmd["value"],
                ),
                operator="Cloud",
                ip_address=None,
                command_id=command_id,
                event=cmd["event"],
            )
        except PlcCommandError as e:
            return False, None, str(e), None
        if result.confirmed is False:
            return False, False, result.confirmMessage, result.plcValues
        return (
            True, result.confirmed is True,
            result.confirmMessage or "已轉發至本地 MQTT，此指令無完成暫存器可確認", result.plcValues,
        )

    async def _forward_to_local_mqtt(self, topic: str, payload_str: str, parts: list) -> bool:
        """將雲端指令轉換主題格式並發送至 Gateway 本地 MQTT，回傳是否成功發布"""
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
            else:
                logger.error(f"[CloudMQTTService] Unexpected cloud command topic format: '{topic}'")
                return False

            await gateway_mqtt_service.publish_message(gateway_topic, payload_str, raise_on_error=True)
            return True
        except Exception as e:
            logger.error(f"[CloudMQTTService] Error forwarding message to local MQTT: {e}")
            return False

cloud_mqtt_service = CloudMQTTService()
