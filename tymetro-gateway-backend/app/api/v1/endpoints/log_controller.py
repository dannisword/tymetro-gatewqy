from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.core.logger import get_recent_logs
from app.models.user_model import User
from app.utils.response_util import ResponseUtil

router = APIRouter()


@router.get("", summary="取得即時系統 logs (記憶體緩衝，輪詢用)")
def get_logs(
    after: int = Query(0, ge=0, description="只回傳 seq 大於此值的 log；首次請帶 0"),
    level: str = Query("", description="最低等級 DEBUG/INFO/WARNING/ERROR"),
    keyword: str = Query("", description="關鍵字過濾"),
    limit: int = Query(500, ge=1, le=2000),
    current_user: User = Depends(get_current_user),
):
    items, latest = get_recent_logs(after=after, level=level, keyword=keyword, limit=limit)
    return ResponseUtil.success(data={"items": items, "latest": latest})
