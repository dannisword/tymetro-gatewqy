from fastapi import APIRouter
from app.schemas.response_schema import ResponseBase
from app.utils.response_util import ResponseUtil
from app.core.enums import get_all_enums

router = APIRouter()


@router.get("", response_model=ResponseBase, summary="取得系統所有選項與列舉")
@router.get("/enums", response_model=ResponseBase, summary="取得系統列舉選項")
def get_options():
    """回傳前端所需的各類列舉選項 (label/value 列表)"""
    return ResponseUtil.success(data=get_all_enums())
