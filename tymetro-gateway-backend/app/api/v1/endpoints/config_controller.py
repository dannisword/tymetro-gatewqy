from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.response_schema import ResponseBase
from app.utils.response_util import ResponseUtil
from app.database.db_config_repo import db_config_repo
from app.models.config_model import SystemConfig

router = APIRouter()

@router.post("/reload", response_model=ResponseBase, summary="觸發熱重載內存快取")
async def reload_config():
    """重新自 DB 載入設備配置快取"""
    try:
        db_config_repo.clear_cache()
        return ResponseUtil.success(message="Config cache reloaded successfully.")
    except Exception as e:
        return ResponseUtil.error(message=f"Failed to reload config: {e}")

@router.delete("", response_model=ResponseBase, summary="清空所有系統設定 (Clear System Configs)")
def clear_system_configs(db: Session = Depends(get_db)):
    """清空 system_configs 資料表中所有系統設定紀錄"""
    try:
        num_deleted = db.query(SystemConfig).delete()
        db.commit()
        db_config_repo.clear_cache()
        return ResponseUtil.success(
            data={"cleared_count": num_deleted},
            message=f"Successfully cleared {num_deleted} system config records."
        )
    except Exception as e:
        db.rollback()
        return ResponseUtil.error(message=f"Failed to clear system configs: {e}")
