import json
import asyncio
import ssl
from typing import Optional, Dict, Any
from app.core.logger import logger
from app.core.config_yaml import yaml_settings
from app.repositories.outbox_repository import outbox_repo


class CentralTcpClient:
    """負責連線至中央 Linux Server (TLS/JSON Lines over TCP) 並維護 Store & Forward 補傳"""
    def __init__(self):
        self.config = yaml_settings.network.central_server
        self.is_connected = False
        self.writer: Optional[asyncio.StreamWriter] = None
        self.reader: Optional[asyncio.StreamReader] = None
        self._running = False

    async def start_loop(self):
        """啟動與中央伺服器的持久連線與 outbox 補傳 Task"""
        self._running = True
        asyncio.create_task(self._maintain_connection_and_flush())

    async def _maintain_connection_and_flush(self):
        while self._running:
            if not self.is_connected:
                await self._connect()
            
            if self.is_connected:
                # 嘗試發送 Outbox 暫存資料
                await self._flush_outbox()

            await asyncio.sleep(self.config.reconnect_delay_sec)

    async def _connect(self):
        try:
            ssl_ctx = None
            if self.config.tls_enabled:
                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE

            logger.info(f"Connecting to Central Server {self.config.host}:{self.config.port} (TLS: {self.config.tls_enabled})...")
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(
                    host=self.config.host,
                    port=self.config.port,
                    ssl=ssl_ctx
                ),
                timeout=5.0
            )
            self.is_connected = True
            logger.info("Successfully connected to Central Server.")
        except Exception as e:
            self.is_connected = False
            logger.warning(f"Central Server connection failed: {e}. Will retry in {self.config.reconnect_delay_sec}s.")

    async def send_payload(self, payload: Dict[str, Any]) -> bool:
        """主動發送報文，若中斷自動寫入 outbox (Store)"""
        if not self.is_connected or not self.writer:
            outbox_repo.push(payload)
            return False

        try:
            line = json.dumps(payload) + "\n"
            self.writer.write(line.encode('utf-8'))
            await self.writer.drain()
            return True
        except Exception as e:
            logger.error(f"Failed to send payload to Central Server: {e}. Saving to outbox.")
            self.is_connected = False
            outbox_repo.push(payload)
            return False

    async def _flush_outbox(self):
        """復連後批次補傳 Outbox 資料 (Forward)"""
        batch = outbox_repo.fetch_batch(limit=30)
        if not batch:
            return

        logger.info(f"Flushing {len(batch)} items from Outbox to Central Server...")
        success_ids = []
        for item in batch:
            sent = await self.send_payload(item["payload"])
            if sent:
                success_ids.append(item["id"])
            else:
                break

        if success_ids:
            outbox_repo.delete_batch(success_ids)

    async def stop(self):
        self._running = False
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.is_connected = False
        logger.info("Central TCP Client stopped.")

central_tcp_client = CentralTcpClient()
