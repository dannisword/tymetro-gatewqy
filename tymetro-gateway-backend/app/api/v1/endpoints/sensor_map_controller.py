from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from app.database.session import get_db
from app.api.deps import get_config_service, get_current_user
from app.services.config_service import ConfigService
from app.schemas.response_schema import ResponseBase
from app.utils.response_util import ResponseUtil
from app.models.user_model import User
from app.schemas.config_schema import ConfigCreate, ConfigUpdate
from app.core.config import settings
from app.core.logger import logger
from app.utils.http_util import HttpUtil
from pydantic import BaseModel

router = APIRouter()

class SensorMapMarker(BaseModel):
    templateCode: str
    sensorCode: str
    bitIndex: Optional[int] = None
    x: float
    y: float
    markerType: str
    color: str
    label: Optional[str] = None
    isActive: bool

@router.get("/template/{template_code}", response_model=ResponseBase[List[SensorMapMarker]], summary="根據模板編號獲取感測器圖配置")
def get_sensor_map_template(
    template_code: str,
    service: ConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user)
):
    try:
        config_type = f"SENSOR_MAP_{template_code}"
        config_item = service.get_by_config_type(config_type)
        if not config_item or not config_item.configContent:
            return ResponseUtil.success(data=[], message="No configuration found for this template")
        
        data = json.loads(str(config_item.configContent))
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(message=f"Failed to fetch sensor map template: {str(e)}")

@router.post("/batch/{template_code}", response_model=ResponseBase, summary="批量儲存感測器圖配置")
def save_sensor_map_batch(
    template_code: str,
    request: List[SensorMapMarker],
    service: ConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user)
):
    try:
        config_type = f"SENSOR_MAP_{template_code}"
        content_str = json.dumps([item.model_dump() for item in request], ensure_ascii=False)
        
        config_item = service.get_by_config_type(config_type)
        if config_item:
            # Update existing
            service.update(config_item.id, ConfigUpdate(configContent=content_str))
        else:
            # Create new
            service.create(ConfigCreate(configType=config_type, configContent=content_str))
            
        return ResponseUtil.success(message="Sensor map configurations saved successfully")
    except Exception as e:
        return ResponseUtil.error(message=f"Failed to save sensor map template: {str(e)}")

@router.post("/download/{template_code}", response_model=ResponseBase, summary="自中心端下載感測器圖配置並儲存至本機")
@router.get("/download/{template_code}", response_model=ResponseBase, summary="自中心端下載感測器圖配置並儲存至本機 (GET)")
def download_sensor_map_template(
    template_code: str,
    service: ConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user)
):
    """
    從中央後端 (tymetro-backend) 下載特定 template_code 的感測器地圖配置，
    並直接儲存至本機 SQLite 的 config 資料表中。
    """
    try:
        token = HttpUtil.get_central_backend_token()
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        target_url = f"{settings.TYMETRO_BACKEND_URL.rstrip('/')}/api/v1/sensor-maps/template/{template_code}"
        logger.info(f"Proxying sensor-maps download request to central backend: {target_url}")

        resp_data = HttpUtil.get(target_url, headers=headers, timeout=10)
        if not resp_data or not resp_data.get("success"):
            error_msg = resp_data.get("message") if resp_data else "無法連線至中心端後端"
            return ResponseUtil.error(message=f"自中心端下載感測器地圖失敗: {error_msg}")

        raw_list = resp_data.get("data") or []
        markers = []
        for item in raw_list:
            if isinstance(item, dict):
                markers.append({
                    "templateCode": template_code,
                    "sensorCode": item.get("sensorCode", ""),
                    "bitIndex": item.get("bitIndex"),
                    "x": float(item.get("x", 0.0)),
                    "y": float(item.get("y", 0.0)),
                    "markerType": item.get("markerType", "rect"),
                    "color": item.get("color", "#3b82f6"),
                    "label": item.get("label"),
                    "isActive": bool(item.get("isActive", True))
                })

        config_type = f"SENSOR_MAP_{template_code}"
        content_str = json.dumps(markers, ensure_ascii=False)

        config_item = service.get_by_config_type(config_type)
        if config_item:
            service.update(config_item.id, ConfigUpdate(configContent=content_str))
        else:
            service.create(ConfigCreate(configType=config_type, configContent=content_str))

        return ResponseUtil.success(
            data=markers,
            message=f"成功自中心端下載並套用樣板 [{template_code}] 共 {len(markers)} 筆感測器圖面配置"
        )
    except Exception as e:
        logger.error(f"Failed to download sensor map template {template_code}: {e}", exc_info=True)
        return ResponseUtil.error(message=f"下載感測器圖配置發生例外: {str(e)}")

