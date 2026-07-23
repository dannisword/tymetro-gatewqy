from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.config_model import DeviceConfigModel, RegisterConfigModel
from app.schemas.response_schema import ResponseBase
from app.utils.response_util import ResponseUtil
from app.ipc.client import ipc_client

router = APIRouter()

class RegisterSchema(BaseModel):
    name: str
    address: int
    data_type: str = "INT16"
    scale: float = 1.0
    unit: str = ""

class DeviceCreateSchema(BaseModel):
    device_id: str
    name: str
    ip: str
    port: int = 502
    slave_id: int = 1
    registers: List[RegisterSchema] = []

@router.get("/devices", response_model=ResponseBase, summary="查詢所有 PFC 控制器與 Modbus 點位 (自 DB 讀取)")
def get_devices(db: Session = Depends(get_db)):
    devices = db.query(DeviceConfigModel).all()
    result = []
    for dev in devices:
        regs = [{"name": r.name, "address": r.address, "type": r.data_type, "scale": r.scale, "unit": r.unit} for r in dev.registers]
        result.append({
            "id": dev.device_id,
            "name": dev.name,
            "ip": dev.ip,
            "port": dev.port,
            "slave_id": dev.slave_id,
            "is_active": dev.is_active,
            "registers": regs
        })
    return ResponseUtil.success(data=result)

@router.post("/devices", response_model=ResponseBase, summary="動態新增/修改 PFC 設備並觸發 Hot Reload")
async def create_or_update_device(request: DeviceCreateSchema, db: Session = Depends(get_db)):
    dev = db.query(DeviceConfigModel).filter(DeviceConfigModel.device_id == request.device_id).first()
    if not dev:
        dev = DeviceConfigModel(
            device_id=request.device_id,
            name=request.name,
            ip=request.ip,
            port=request.port,
            slave_id=request.slave_id
        )
        db.add(dev)
    else:
        dev.name = request.name
        dev.ip = request.ip
        dev.port = request.port
        dev.slave_id = request.slave_id
        # 刪除舊暫存器
        db.query(RegisterConfigModel).filter(RegisterConfigModel.device_id == dev.device_id).delete()

    db.flush()

    for r in request.registers:
        reg = RegisterConfigModel(
            device_id=dev.device_id,
            name=r.name,
            address=r.address,
            data_type=r.data_type,
            scale=r.scale,
            unit=r.unit
        )
        db.add(reg)

    db.commit()

    # 發送 IPC RELOAD_CONFIG 指令通知 Polling Service 熱重載內存快取
    await ipc_client.send_command("RELOAD_CONFIG")

    return ResponseUtil.success(message=f"Device {request.device_id} saved and Polling Service hot-reloaded successfully.")
