import glob
import io
import os
import re
import zipfile
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.logger import get_recent_logs, LOG_FILE_PATH
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
    items, latest, total = get_recent_logs(after=after, level=level, keyword=keyword, limit=limit)
    return ResponseUtil.success(data={"items": items, "latest": latest, "total": total})


DOWNLOAD_TICKET_TTL_SECONDS = 60


@router.post("/download-ticket", summary="取得 log 下載用短效票證 (60 秒內有效)")
def create_download_ticket(current_user: User = Depends(get_current_user)):
    ticket = jwt.encode(
        {
            "purpose": "log_download",
            "exp": datetime.now(timezone.utc) + timedelta(seconds=DOWNLOAD_TICKET_TTL_SECONDS),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return ResponseUtil.success(data={"ticket": ticket})


def _collect_day(day: str) -> bytes:
    """合併指定日期 (YYYY-MM-DD) 的 log：目前檔案 + 輪替壓縮檔，依時間排序。
    log 行以日期開頭；例外堆疊等續行跟隨前一個符合的行。"""
    log_dir = os.path.dirname(LOG_FILE_PATH) or "."
    base = os.path.basename(LOG_FILE_PATH)
    stem = base[:-4] if base.endswith(".log") else base  # gateway

    sources = []  # (sort_key, path, is_zip)
    for z in glob.glob(os.path.join(log_dir, f"{stem}.*.log.zip")):
        m = re.search(r"\.(\d{4}-\d{2}-\d{2})_", os.path.basename(z))
        # 檔名日期為輪替時間；當天內容只可能存在於輪替日 >= 當天的檔案
        if m and m.group(1) >= day:
            sources.append((os.path.basename(z), z, True))
    sources.sort(key=lambda x: x[0])
    if os.path.isfile(LOG_FILE_PATH):
        sources.append(("~current", LOG_FILE_PATH, False))

    out = io.BytesIO()
    prefix = day.encode()
    for _, path, is_zip in sources:
        try:
            if is_zip:
                with zipfile.ZipFile(path) as zf:
                    data = b"".join(zf.read(n) for n in zf.namelist())
            else:
                with open(path, "rb") as f:
                    data = f.read()
        except Exception:
            continue
        keep = False
        for line in data.splitlines(keepends=True):
            if re.match(rb"\d{4}-\d{2}-\d{2} ", line):
                keep = line.startswith(prefix)
            if keep:
                out.write(line)
    return out.getvalue()


@router.get("/download", summary="下載 log (可指定日期 date=YYYY-MM-DD 取整天；未指定則下載目前檔案)")
def download_log(
    ticket: str = Query(..., description="由 /logs/download-ticket 取得"),
    date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="日期 YYYY-MM-DD"),
):
    try:
        payload = jwt.decode(ticket, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired ticket")
    if payload.get("purpose") != "log_download":
        raise HTTPException(status_code=401, detail="Invalid ticket")

    if date:
        content = _collect_day(date)
        if not content:
            raise HTTPException(status_code=404, detail=f"No logs for {date}")
        filename = f"gateway_{date}.log"
    else:
        if not os.path.isfile(LOG_FILE_PATH):
            raise HTTPException(status_code=404, detail="Log file not found")
        # log 檔持續寫入中：先讀出當下快照再回傳，避免 Content-Length 與實際不符
        with open(LOG_FILE_PATH, "rb") as f:
            content = f.read()
        filename = "gateway.log"
    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
