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
