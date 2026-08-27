from typing import Optional
from fastapi import APIRouter, Depends
from app.core.config import settings
from app.core.logger import logger
from app.api.deps import get_current_user
from app.models.user_model import User
from app.utils.response_util import ResponseUtil
from app.utils.http_util import HttpUtil
from app.schemas.response_schema import ResponseBase

router = APIRouter()

@router.get("/options", response_model=ResponseBase, summary="獲取時段樣板選單選項列表 (中繼轉發)")
def get_template_options(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    token = HttpUtil.get_central_backend_token()
    if not token:
        logger.error("Failed to authenticate with central backend, returning fallback empty options.")
        return ResponseUtil.success(data=[], message="Failed to authenticate with central backend")

    params = {}
    if category:
        params["category"] = category
    params["pageSize"] = 1000

    target_url = f"{settings.TYMETRO_BACKEND_URL.rstrip('/')}/api/v1/time-period-templates/options"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    logger.info(f"Proxying request to central backend: {target_url}")
    resp_data = HttpUtil.get(target_url, params=params, headers=headers, timeout=5)
    return resp_data

@router.get("/download/{code}", response_model=ResponseBase, summary="下載特定代碼的時段樣板 (中繼轉發)")
def download_template_by_code(
    code: str,
    current_user: User = Depends(get_current_user)
):
    token = HttpUtil.get_central_backend_token()
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    target_url = f"{settings.TYMETRO_BACKEND_URL.rstrip('/')}/api/v1/time-period-templates/download/{code}"

    logger.info(f"Proxying download request to central backend: {target_url}")
    resp_data = HttpUtil.get(target_url, headers=headers, timeout=5)
    return resp_data



