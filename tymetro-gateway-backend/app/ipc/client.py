import json
import asyncio
from typing import Dict, Any, Optional
from app.core.logger import logger
from app.core.config_yaml import yaml_settings

class IPCClient:
    def __init__(self, socket_path: Optional[str] = None):
        self.socket_path = socket_path or yaml_settings.network.ipc_socket_path

    async def send_command(self, cmd: str, params: Optional[Dict[str, Any]] = None, timeout: float = 1.0) -> Dict[str, Any]:
        """透過 Unix Domain Socket 傳送 JSON-RPC 報文給 Polling Service"""
        req_id = int(asyncio.get_event_loop().time() * 1000)
        request_data = {
            "id": req_id,
            "cmd": cmd,
            "params": params or {}
        }
        
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_unix_connection(self.socket_path),
                timeout=timeout
            )
            
            payload = json.dumps(request_data) + "\n"
            writer.write(payload.encode('utf-8'))
            await writer.drain()

            line = await asyncio.wait_for(reader.readline(), timeout=timeout)
            writer.close()
            await writer.wait_closed()

            if not line:
                return {"id": req_id, "code": 500, "msg": "Empty IPC response", "data": None}

            return json.loads(line.decode('utf-8').strip())
        except Exception as e:
            logger.error(f"IPC request failed [{cmd}]: {e}")
            return {"id": req_id, "code": 503, "msg": f"IPC Connection Error: {str(e)}", "data": None}

ipc_client = IPCClient()
