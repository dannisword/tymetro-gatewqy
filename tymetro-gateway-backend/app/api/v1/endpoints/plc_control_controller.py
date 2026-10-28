from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user_model import User
from app.models.car_model import Car
from app.models.equipment_model import Equipment
from app.schemas.plc_command_schema import (
    PlcBatchCommandRequest,
    PlcBatchCommandResponse,
    PlcCommandRequest,
    PlcCommandResponse,
)
from app.schemas.response_schema import ResponseBase
from app.services.plc_command_service import PlcCommandError, PlcCommandService
from app.utils.response_util import ResponseUtil

router = APIRouter()


def _client_ip(req: Request) -> Optional[str]:
    forwarded = req.headers.get("x-real-ip") or req.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return req.client.host if req.client else None


@router.post("/execute", response_model=ResponseBase[PlcCommandResponse], summary="執行 PLC 設定 (發布 MQTT 並記錄稽核)")
async def execute_plc_command(
    request: PlcCommandRequest,
    req: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    operator = str(current_user.userName or current_user.account) if current_user else "system"
    try:
        result = await PlcCommandService(db).execute(request, operator=operator, ip_address=_client_ip(req))
    except PlcCommandError as e:
        return ResponseUtil.error(message=str(e))
    return ResponseUtil.success(data=result, message="設定指令已送出")


@router.post("/batch-execute", response_model=ResponseBase[PlcBatchCommandResponse], summary="批次執行 PLC 設定 (多端點，逾時重發，逐台留設定紀錄)")
async def batch_execute_plc_command(
    request: PlcBatchCommandRequest,
    req: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    operator = str(current_user.userName or current_user.account) if current_user else "system"
    targets = request.targets
    if not targets:
        rows = (
            db.query(Equipment, Car)
            .join(Car, Equipment.carId == Car.id)
            .filter(Equipment.isActive == True, Car.isActive == True)
            .order_by(Car.carNo, Equipment.endPos)
            .all()
        )
        targets = [
            {"carNo": int(car.carVin) if car.carVin and car.carVin.isdigit() else (car.carNo or 0), "endPos": eq.endPos}
            for eq, car in rows
        ]
    try:
        results = await PlcCommandService(db).execute_batch(
            command=request.command,
            value=request.value,
            targets=targets,
            operator=operator,
            ip_address=_client_ip(req),
            train_code=request.trainCode,
        )
    except PlcCommandError as e:
        return ResponseUtil.error(message=str(e))

    failed = [r.name for r in results if not r.ok]
    data = PlcBatchCommandResponse(
        command=request.command,
        success=not failed,
        message="全數 PLC 已確認" if not failed else f"{len(failed)} 個端點逾時未確認: {', '.join(failed)}",
        total=len(results),
        confirmedCount=len(results) - len(failed),
        failedTargets=failed,
    )
    if failed:
        return ResponseUtil.error(message=data.message)
    return ResponseUtil.success(data=data, message=data.message)
