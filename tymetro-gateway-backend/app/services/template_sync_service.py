import json
import urllib.parse
from app.core.config import settings
from app.core.logger import logger
from app.database.session import SessionLocal
from app.models.car_model import Car
from app.models.config_model import Config
from app.utils.http_util import HttpUtil


def sync_schedule_template() -> None:
    """
    開機時同步後端時段樣板 (同步阻塞，請以 thread 執行)。
    條件：本機 configs (SCHEDULE) 的 code 有值，且中心端同 code 的 version 與本機不同時才覆蓋。
    任何失敗僅記錄 log，不影響開機。
    """
    db = SessionLocal()
    try:
        config = db.query(Config).filter(Config.configType == "SCHEDULE").first()
        if not config or not config.code:
            logger.info("[TemplateSync] 本機無 SCHEDULE 樣板 code，略過同步。")
            return
        code = str(config.code)
        local_version = str(config.version or "")

        car = db.query(Car).first()
        train_code = car.trainCode if car else ""
        if not train_code:
            logger.info("[TemplateSync] 本機無車組編號，略過同步。")
            return

        token = HttpUtil.get_central_backend_token()
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        base = settings.TYMETRO_BACKEND_URL.rstrip("/")
        url = f"{base}/api/v1/time-period-templates/download-by-train/{urllib.parse.quote(str(train_code), safe='')}/{urllib.parse.quote(code, safe='')}"

        resp = HttpUtil.get(url, headers=headers, timeout=10)
        data = resp.get("data") if resp.get("success") else None
        if not data or not data.get("payload"):
            logger.warning(f"[TemplateSync] 下載樣板 {code} 失敗或無資料: {resp.get('message')}")
            return

        remote_version = str(data.get("version") or "")
        if not remote_version or remote_version == local_version:
            logger.info(f"[TemplateSync] 樣板 {code} 版本相同 ({local_version})，無需更新。")
            return

        name = data.get("name") or config.name or ""
        config.configContent = json.dumps({**data["payload"], "templateName": name}, ensure_ascii=False)  # type: ignore[assignment]
        config.version = remote_version  # type: ignore[assignment]
        config.name = name  # type: ignore[assignment]
        db.commit()
        logger.info(f"[TemplateSync] 樣板 {code} 已更新：{local_version} -> {remote_version}")
    except Exception as e:
        db.rollback()
        logger.error(f"[TemplateSync] 開機同步時段樣板失敗: {e}")
    finally:
        db.close()
