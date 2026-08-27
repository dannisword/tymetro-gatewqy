from fastapi import APIRouter, Depends, Query
from datetime import datetime, date
from sqlalchemy.orm import Session
from typing import Optional
from app.database.session import get_db
from app.schemas.response_schema import ResponseBase, ResponseList
from app.utils.response_util import ResponseUtil
from app.database.db_config_repo import db_config_repo
from app.models.config_model import SystemConfig
from app.models.user_model import User
from app.api.deps import get_config_service, get_current_user
from app.services.config_service import ConfigService
from app.schemas.config_schema import ConfigCreate, ConfigUpdate, ConfigResponse

from app.models.car_model import Car
from app.models.equipment_model import Equipment
from app.models.sensor_model import Sensor
from app.core.config import settings
from app.utils.http_util import HttpUtil

from app.database.init_db import sync_yaml_to_db
from app.core.config_yaml import reload_gateway_yaml_config
from app.services.gateway_mqtt_service import gateway_mqtt_service
from app.services.cloud_mqtt_service import cloud_mqtt_service

router = APIRouter()

@router.post("/reload", response_model=ResponseBase, summary="觸發熱重載內存快取與 gateway.yaml 設定並同步資料庫與 MQTT 服務")
async def reload_config(db: Session = Depends(get_db)):
    """重新自硬碟載入 gateway.yaml、同步覆蓋至 DB、重啟 MQTT 連線並清空 RAM 快取"""
    try:
        # 1. 先將最新 YAML 同步覆蓋入 SQLite 資料庫 (system_configs)
        sync_yaml_to_db(db, force=True)
        # 2. 重新讀取 gateway.yaml 至 Python 記憶體 (yaml_settings)
        reload_gateway_yaml_config()
        # 3. 清空並立即預熱 (Pre-warm) 最新 RAM 快取
        db_config_repo.clear_cache()
        db_config_repo.get_all_equipments()
        # 4. 熱重載並重連 MQTT Subscriber 與 Publisher (Cloud MQTT)
        await gateway_mqtt_service.restart()
        await cloud_mqtt_service.restart()
        return ResponseUtil.success(message="gateway.yaml reloaded, synced to DB, MQTT services restarted, and RAM cache pre-warmed successfully.")
    except Exception as e:
        return ResponseUtil.error(message=f"Failed to reload config: {e}")

@router.post("/sync", response_model=ResponseBase, summary="從 gateway.yaml 重置並同步設定至資料庫與 MQTT 服務")
async def sync_yaml_configs(db: Session = Depends(get_db)):
    """清空現有 system_configs 並從 gateway.yaml 重新匯入、重啟 MQTT 連線與預熱快取"""
    try:
        # 1. 先將 gateway.yaml 同步覆蓋至 SQLite 資料庫
        sync_yaml_to_db(db, force=True)
        # 2. 再重載 YAML 至 Python 記憶體全域變數 (yaml_settings)
        reload_gateway_yaml_config()
        # 3. 清空舊的 RAM 快取
        db_config_repo.clear_cache()
        # 4. 重新自 DB 讀取並預熱最新快取
        db_config_repo.get_all_equipments()
        # 5. 熱重載並重連 MQTT Subscriber 與 Publisher (Cloud MQTT)
        await gateway_mqtt_service.restart()
        await cloud_mqtt_service.restart()
        return ResponseUtil.success(message="Successfully re-synced system configs from gateway.yaml to DB, restarted MQTT services, and pre-warmed RAM cache.")
    except Exception as e:
        return ResponseUtil.error(message=f"Failed to sync configs from YAML: {e}")

@router.delete("", response_model=ResponseBase, summary="清空所有系統設定 (Clear System Configs)")
def clear_system_configs(db: Session = Depends(get_db)):
    """清空 system_configs 資料表中所有系統設定紀錄並重置 RAM 快取"""
    try:
        num_deleted = db.query(SystemConfig).delete()
        db.commit()
        db_config_repo.clear_cache()
        db_config_repo.get_all_equipments()
        return ResponseUtil.success(
            data={"cleared_count": num_deleted},
            message=f"Successfully cleared {num_deleted} system config records and re-initialized RAM cache."
        )
    except Exception as e:
        db.rollback()
        return ResponseUtil.error(message=f"Failed to clear system configs: {e}")

@router.get("", response_model=ResponseList[ConfigResponse], summary="獲取設定清單")
def get_configs(
    pageIndex: int = 0,
    pageSize: int = 50,
    propertyName: str = "id",
    order: str = "DESC",
    configType: Optional[str] = None,
    service: ConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user)
):
    items, total = service.get_configs(
        configType=configType,
        pageIndex=pageIndex,
        pageSize=pageSize,
        propertyName=propertyName,
        order=order
    )
    return ResponseUtil.list_success(
        data=items,
        total=total,
        pageIndex=pageIndex,
        pageSize=pageSize
    )

@router.get("/type/{config_type}", response_model=ResponseBase[ConfigResponse], summary="根據類型獲取設定資訊")
def get_config_by_type(
    config_type: str,
    service: ConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user)
):
    item = service.get_by_config_type(config_type)
    if not item:
        return ResponseUtil.not_found("Config not found")
    return ResponseUtil.success(data=item)

@router.put("/{config_id}", response_model=ResponseBase[ConfigResponse], summary="更新設定資訊")
def update_config(
    config_id: int,
    request: ConfigUpdate,
    service: ConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user)
):
    try:
        item = service.update(config_id, request)
        return ResponseUtil.success(data=item, message="Config updated successfully")
    except Exception as e:
        return ResponseUtil.error(message=str(e))

@router.post("/upsert", response_model=ResponseBase[ConfigResponse], summary="新增或更新設定")
def upsert_config(
    request: ConfigCreate,
    service: ConfigService = Depends(get_config_service),
    current_user: User = Depends(get_current_user)
):
    try:
        item = service.get_by_config_type(request.configType)
        if item:
            item = service.update(item.id, ConfigUpdate(configContent=request.configContent, version=request.version))
            return ResponseUtil.success(data=item, message="Config updated successfully")
        else:
            item = service.create(request)
            return ResponseUtil.success(data=item, message="Config created successfully")
    except Exception as e:
        return ResponseUtil.error(message=str(e))


@router.post("/download-metadata", response_model=ResponseBase, summary="從中心端下載並同步車廂、設備與感測器資料")
def download_metadata(
    trainCode: Optional[str] = Query(None, description="車組編號"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    自中心端 (tymetro-backend) 取得最新的車廂 (cars)、設備 (equipments) 與感測器 (sensors) 資料，
    並同步更新本機 SQLite 資料庫，最後清空快取並重載預熱。
    """
    token = HttpUtil.get_central_backend_token()
    if not token:
        return ResponseUtil.error("無法登入中心後端取得 Token")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    # 1. 取得車廂資料
    cars_url = f"{settings.TYMETRO_BACKEND_URL.rstrip('/')}/api/v1/cars"
    cars_params = {"pageSize": 1000, "trainCode": trainCode} if trainCode else {"pageSize": 1000}
    cars_resp = HttpUtil.get(cars_url, params=cars_params, headers=headers)
    if not cars_resp.get("success"):
        return ResponseUtil.error(f"下載車廂資料失敗: {cars_resp.get('message')}")
    cars_data = cars_resp.get("data") or {}
    cars_list = cars_data.get("source", []) if isinstance(cars_data, dict) else (cars_data if isinstance(cars_data, list) else [])

    if trainCode:
        # 本地過濾，確保資料精確度
        cars_list = [c for c in cars_list if c.get("trainCode") == trainCode]
        if not cars_list:
            return ResponseUtil.error(f"在中心端找不到車組編號為 '{trainCode}' 的車廂資料。")

    # 2. 取得設備資料
    eq_url = f"{settings.TYMETRO_BACKEND_URL.rstrip('/')}/api/v1/equipments"
    eq_params = {"pageSize": 1000, "trainCode": trainCode} if trainCode else {"pageSize": 1000}
    eq_resp = HttpUtil.get(eq_url, params=eq_params, headers=headers)
    if not eq_resp.get("success"):
        return ResponseUtil.error(f"下載設備資料失敗: {eq_resp.get('message')}")
    eq_data = eq_resp.get("data") or {}
    eq_list = eq_data.get("source", []) if isinstance(eq_data, dict) else (eq_data if isinstance(eq_data, list) else [])

    # 3. 取得感測器資料
    sensors_url = f"{settings.TYMETRO_BACKEND_URL.rstrip('/')}/api/v1/sensors"
    sensors_params = {"pageSize": 10000, "trainCode": trainCode} if trainCode else {"pageSize": 10000}
    sensors_resp = HttpUtil.get(sensors_url, params=sensors_params, headers=headers)
    if not sensors_resp.get("success"):
        return ResponseUtil.error(f"下載感測器資料失敗: {sensors_resp.get('message')}")
    sensors_data = sensors_resp.get("data") or {}
    sensors_list = sensors_data.get("source", []) if isinstance(sensors_data, dict) else (sensors_data if isinstance(sensors_data, list) else [])

    if trainCode:
        # 篩選屬於該車組的車廂 ID 集合，並僅保留相關設備與感測器
        target_car_ids = {c.get("id") for c in cars_list if c.get("id") is not None}
        eq_list = [eq for eq in eq_list if eq.get("carId") in target_car_ids]
        sensors_list = [s for s in sensors_list if s.get("carId") in target_car_ids]

    # Helper 解析函數
    def parse_date(val: Optional[str]) -> Optional[date]:
        if not val:
            return None
        try:
            return date.fromisoformat(val[:10])
        except Exception:
            return None

    def parse_datetime(val: Optional[str]) -> Optional[datetime]:
        if not val:
            return None
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            return None

    try:
        # 永遠清空所有舊資料 (依外鍵依賴反向刪除)
        db.query(Sensor).delete()
        db.query(Equipment).delete()
        db.query(Car).delete()
        
        # 先提交清除資料的變更，確保資料完全清空，避免 Unique 鍵衝突
        db.commit()

        # 插入車廂
        for c in cars_list:
            db.add(Car(
                id=c.get("id"),
                trainCode=c.get("trainCode"),
                carNo=c.get("carNo"),
                carVin=c.get("carVin"),
                carType=c.get("carType"),
                carTag=c.get("carTag"),
                carStatus=c.get("carStatus"),
                isActive=c.get("isActive") if c.get("isActive") is not None else True,
                lastSeenAt=parse_datetime(c.get("lastSeenAt"))
            ))
        db.flush()

        # 插入設備
        for eq in eq_list:
            db.add(Equipment(
                id=eq.get("id"),
                carId=eq.get("carId"),
                endPos=eq.get("endPos"),
                equipmentName=eq.get("equipmentName"),
                equipmentStatus=eq.get("equipmentStatus") or "OPERATING",
                ipAddress=eq.get("ipAddress"),
                brandModel=eq.get("brandModel"),
                installDate=parse_date(eq.get("installDate")),
                accumulatedHours=eq.get("accumulatedHours") or 0,
                isActive=eq.get("isActive") if eq.get("isActive") is not None else True,
                lastSeenAt=parse_datetime(eq.get("lastSeenAt"))
            ))
        db.flush()

        # 插入感測器
        for s in sensors_list:
            db.add(Sensor(
                id=s.get("id"),
                carId=s.get("carId"),
                equipmentId=s.get("equipmentId"),
                sensorType=s.get("sensorType"),
                sensorCode=s.get("sensorCode"),
                sensorName=s.get("sensorName"),
                sensorValue=s.get("sensorValue") or 0.0,
                sensorUnit=s.get("sensorUnit"),
                sensorStatus=s.get("sensorStatus") or "OPERATING",
                calibrationOffset=s.get("calibrationOffset") or 0.0,
                lastCalibrationDate=parse_date(s.get("lastCalibrationDate")),
                showOnDashboard=s.get("showOnDashboard") if s.get("showOnDashboard") is not None else True,
                isActive=s.get("isActive") if s.get("isActive") is not None else True,
                saveHistory=s.get("saveHistory") if s.get("saveHistory") is not None else True
            ))
        
        db.commit()

        # 清空快取並重新預熱設備點位資料
        db_config_repo.clear_cache()
        db_config_repo.get_all_equipments()

        print("Metadata download and sync completed successfully.")
        return ResponseUtil.success(message=f"成功下載並同步 {len(cars_list)} 筆車廂、{len(eq_list)} 筆設備及 {len(sensors_list)} 筆感測器資料。")

    except Exception as e:
        db.rollback()
        print(f"Error saving downloaded metadata to DB: {e}")
        return ResponseUtil.error(f"寫入本地資料庫失敗: {str(e)}")
