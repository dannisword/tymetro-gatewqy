import os
import json
import asyncio
import time
from typing import Dict, Any, Callable, Optional
from app.core.logger import logger
from app.core.config_yaml import yaml_settings

class IPCServer:
    def __init__(self, socket_path: Optional[str] = None, handler_func: Optional[Callable] = None):
        self.socket_path = socket_path or yaml_settings.network.ipc_socket_path
        self.handler_func = handler_func
        self.server: Optional[asyncio.AbstractServer] = None

    async def start(self):
        """啟動 Unix Domain Socket IPC 伺服器"""
        if os.path.exists(self.socket_path):
            try:
                os.remove(self.socket_path)
            except OSError as e:
                logger.error(f"Failed to remove stale IPC socket {self.socket_path}: {e}")

        self.server = await asyncio.start_unix_server(self._handle_client, path=self.socket_path)
        logger.info(f"IPC Server listening on Unix Domain Socket: {self.socket_path}")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """處理來自 API Service 的 JSON-RPC 請求"""
        try:
            while not reader.at_eof():
                line = await reader.readline()
                if not line:
                    break
                request_str = line.decode('utf-8').strip()
                if not request_str:
                    continue
                try:
                    req = json.loads(request_str)
                    resp = await self._process_request(req)
                except Exception as e:
                    resp = {
                        "id": None,
                        "code": 400,
                        "msg": f"Bad Request: {str(e)}",
                        "data": None
                    }
                writer.write((json.dumps(resp) + "\n").encode('utf-8'))
                await writer.drain()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"IPC Client handling error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def _process_request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        req_id = req.get("id")
        cmd = req.get("cmd")
        params = req.get("params", {})

        if self.handler_func:
            return await self.handler_func(req_id, cmd, params)

        # 預設範例回應
        return {
            "id": req_id,
            "code": 200,
            "msg": "OK",
            "data": {
                "cmd": cmd,
                "status": "ready",
                "timestamp": time.time()
            }
        }

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            if os.path.exists(self.socket_path):
                os.remove(self.socket_path)
            logger.info("IPC Server stopped and socket removed.")
