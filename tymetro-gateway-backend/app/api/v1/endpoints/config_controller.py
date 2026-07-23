from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.equipment_model import Equipment
from app.schemas.response_schema import ResponseBase
from app.utils.response_util import ResponseUtil
from app.ipc.client import ipc_client

router = APIRouter()

@router.post("/reload", response_model=ResponseBase, summary="觸發 Polling Service 熱重載內存快取")
async def reload_config():
    """發送 IPC RELOAD_CONFIG 指令通知 Polling Service 重新自 DB 載入設備配置"""
    try:
        res = await ipc_client.send_command("RELOAD_CONFIG")
        return ResponseUtil.success(data=res, message="Config reload signal sent successfully.")
    except Exception as e:
        return ResponseUtil.error(message=f"Failed to send reload signal: {e}")
