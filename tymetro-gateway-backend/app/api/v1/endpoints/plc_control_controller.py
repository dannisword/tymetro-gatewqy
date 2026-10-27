from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user_model import User
from app.schemas.plc_command_schema import PlcCommandRequest, PlcCommandResponse
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
