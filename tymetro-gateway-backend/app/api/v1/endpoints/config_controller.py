from fastapi import APIRouter, Depends, Query
from datetime import datetime, date
from sqlalchemy.orm import Session
from typing import Optional, Any
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
from app.models.sensor_value_label_model import SensorValueLabel
from app.models.event_template_model import EventTemplate
from app.core.config import settings
from app.utils.http_util import HttpUtil

from app.database.init_db import sync_yaml_to_db
from app.core.config_yaml import reload_gateway_yaml_config
from app.services.gateway_mqtt_service import gateway_mqtt_service
from app.services.cloud_mqtt_service import cloud_mqtt_service, is_cloud_mqtt_enabled, set_cloud_mqtt_enabled
from pydantic import BaseModel
from app.core.enums import get_all_enums
from app.services.equipment_event_service import equipment_event_service

router = APIRouter()

@router.get("/enums", response_model=ResponseBase, summary="取得系統列舉選項")
def get_enums():
    """回傳前端所需的各類列舉選項 (label/value 列表)"""
    return ResponseUtil.success(data=get_all_enums())

class CloudMqttSwitch(BaseModel):
    enabled: bool

@router.get("/cloud-mqtt", response_model=ResponseBase, summary="取得 Cloud MQTT 開關狀態")
def get_cloud_mqtt_switch():
    return ResponseUtil.success(data={"enabled": is_cloud_mqtt_enabled(), "connected": cloud_mqtt_service.is_connected})

@router.post("/cloud-mqtt", response_model=ResponseBase, summary="開啟/關閉 Cloud MQTT (全域開關)")
async def set_cloud_mqtt_switch(request: CloudMqttSwitch, current_user: User = Depends(get_current_user)):
    try:
        set_cloud_mqtt_enabled(request.enabled)
        if request.enabled:
            await cloud_mqtt_service.restart()
        else:
            await cloud_mqtt_service.stop()
        return ResponseUtil.success(
            data={"enabled": is_cloud_mqtt_enabled(), "connected": cloud_mqtt_service.is_connected},
            message="Cloud MQTT 已開啟" if request.enabled else "Cloud MQTT 已關閉"
        )
    except Exception as e:
        return ResponseUtil.error(message=f"切換 Cloud MQTT 失敗: {e}")

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
        equipment_event_service.reload_templates()
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

    # 4. 取得數值對照文字 (3D 圖/儀表板顯示用)
    labels_url = f"{settings.TYMETRO_BACKEND_URL.rstrip('/')}/api/v1/sensor-bit-labels/values"
    labels_resp = HttpUtil.get(labels_url, headers=headers)
    labels_ok = bool(labels_resp.get("success"))
    if not labels_ok:
        # 數值對照僅影響顯示文字，失敗時不中斷 cars/equipments/sensors 的同步，並保留本機既有對照資料
        print(f"Download value labels failed, keeping local copy: {labels_resp.get('message')}")
    labels_data = (labels_resp.get("data") if labels_ok else None) or []
    labels_list = labels_data.get("source", []) if isinstance(labels_data, dict) else (labels_data if isinstance(labels_data, list) else [])

    # 4.1 取得 PLC 事件樣板 (D40016/D40017 位元定義，後端單頁上限 200 筆)
    tmpl_url = f"{settings.TYMETRO_BACKEND_URL.rstrip('/')}/api/v1/event-templates"
    tmpl_resp = HttpUtil.get(tmpl_url, params={"pageSize": 200, "isActive": True}, headers=headers)
    tmpl_ok = bool(tmpl_resp.get("success"))
    if not tmpl_ok:
        print(f"Download event templates failed, keeping local copy: {tmpl_resp.get('message')}")
    tmpl_data = (tmpl_resp.get("data") if tmpl_ok else None) or []
    tmpl_list = tmpl_data.get("source", []) if isinstance(tmpl_data, dict) else (tmpl_data if isinstance(tmpl_data, list) else [])
    tmpl_ok = tmpl_ok and bool(tmpl_list)

    # 5. 取得使用者資料
    users_url = f"{settings.TYMETRO_BACKEND_URL.rstrip('/')}/api/v1/users"
    users_params = {"pageSize": 1000}
    users_resp = HttpUtil.get(users_url, params=users_params, headers=headers)
    users_ok = bool(users_resp.get("success"))
    if not users_ok:
        print(f"Download users failed, keeping local users: {users_resp.get('message')}")
    users_data = (users_resp.get("data") if users_ok else None) or {}
    users_list = users_data.get("source", []) if isinstance(users_data, dict) else (users_data if isinstance(users_data, list) else [])

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
        if labels_ok:
            db.query(SensorValueLabel).delete()
        if tmpl_ok:
            db.query(EventTemplate).delete()
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
                saveHistory=s.get("saveHistory") if s.get("saveHistory") is not None else True,
                limitMode=s.get("limitMode") or "NONE",
                minLimit=s.get("minLimit"),
                maxLimit=s.get("maxLimit"),
                scale=s.get("scale") if s.get("scale") is not None else 1.0,
                dataType=s.get("dataType") or "int16",
                defaultValue=s.get("defaultValue") if s.get("defaultValue") is not None else 0.0
            ))
        
        # 插入數值對照文字 (下載失敗時略過，保留舊資料)
        for v in (labels_list if labels_ok else []):
            db.add(SensorValueLabel(
                sensorCode=v.get("sensorCode"),
                bitMask=v.get("bitMask"),
                matchValue=v.get("matchValue"),
                text=v.get("text"),
                label=v.get("label"),
                description=v.get("description")
            ))

        # 插入事件樣板 (下載失敗時略過，保留舊資料)
        for t in (tmpl_list if tmpl_ok else []):
            db.add(EventTemplate(
                templateCode=t.get("templateCode") or "HVAC_PLC_STANDARD",
                registerCode=str(t.get("registerCode", "")).upper(),
                bitIndex=t.get("bitIndex"),
                tagName=t.get("tagName"),
                tagDesc=t.get("tagDesc") or t.get("tagName"),
                eventType=t.get("eventType") or "ALARM",
                severity=t.get("severity") or "ERROR",
                isActive=t.get("isActive") if t.get("isActive") is not None else True,
                needConfirm=bool(t.get("needConfirm"))
            ))

        # 同步更新使用者資料 (若有下載到使用者清單，採 upsert 避免覆蓋密碼，若為新增則預設 admin123)
        synced_users_count = 0
        if users_ok and users_list:
            for u in users_list:
                account = u.get("account")
                if not account:
                    continue
                local_user = db.query(User).filter(User.account == account).first()
                if local_user:
                    update_fields: dict[str, Any] = {}
                    if u.get("userName"):
                        update_fields["userName"] = u.get("userName")
                    if u.get("email"):
                        update_fields["email"] = u.get("email")
                    if u.get("orgId"):
                        update_fields["orgId"] = u.get("orgId")
                    if u.get("orgCode"):
                        update_fields["orgCode"] = u.get("orgCode")
                    if u.get("isActive") is not None:
                        update_fields["isActive"] = u.get("isActive")
                    if u.get("isMobile") is not None:
                        update_fields["isMobile"] = u.get("isMobile")
                    parsed_enable_at = parse_datetime(u.get("enableAt"))
                    if parsed_enable_at is not None:
                        update_fields["enableAt"] = parsed_enable_at
                    parsed_disable_at = parse_datetime(u.get("disableAt"))
                    if parsed_disable_at is not None:
                        update_fields["disableAt"] = parsed_disable_at

                    for k, val in update_fields.items():
                        setattr(local_user, k, val)
                else:
                    from app.core.security import get_password_hash
                    db.add(User(
                        account=account,
                        userName=u.get("userName"),
                        email=u.get("email"),
                        orgId=u.get("orgId") or 1,
                        orgCode=u.get("orgCode") or "HQ",
                        password=get_password_hash("admin123"),
                        isActive=u.get("isActive") if u.get("isActive") is not None else True,
                        isMobile=u.get("isMobile") if u.get("isMobile") is not None else False,
                        enableAt=parse_datetime(u.get("enableAt")),
                        disableAt=parse_datetime(u.get("disableAt"))
                    ))
                synced_users_count += 1

        db.commit()

        # 清空快取並重新預熱設備點位資料
        db_config_repo.clear_cache()
        db_config_repo.get_all_equipments()

        print("Metadata download and sync completed successfully.")
        detail_msg = f"成功下載並同步 {len(cars_list)} 筆車廂、{len(eq_list)} 筆設備、{len(sensors_list)} 筆感測器"
        if labels_ok:
            detail_msg += f"、{len(labels_list)} 筆數值對照資料"
        if tmpl_ok:
            detail_msg += f"、{len(tmpl_list)} 筆事件樣板"
        if users_ok:
            detail_msg += f"及 {synced_users_count} 筆使用者資料。"
        else:
            detail_msg += "；使用者資料下載失敗，已保留本機既有帳號。"
        return ResponseUtil.success(message=detail_msg)

    except Exception as e:
        db.rollback()
        print(f"Error saving downloaded metadata to DB: {e}")
        return ResponseUtil.error(f"寫入本地資料庫失敗: {str(e)}")


@router.post("/publish-initial-values", response_model=ResponseBase, summary="透過 MQTT 發送初始值暫存器至 8 台 PLC")
async def publish_initial_values(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    將資料庫中 sensorType 為 INITIAL 的初始值暫存器，
    透過 MQTT 發布至所有啟用的設備 (8 台 PLC)。
    Topic 格式：TYMC/AIR/INI/{trainNo}/{carVin}/{endPos}
    """
    try:
        result = await gateway_mqtt_service.publish_initial_values(db)
        return ResponseUtil.success(
            data=result,
            message=f"已成功將初始值暫存器發布至 {result.get('count', 0)} 台 PLC (MQTT)"
        )
    except Exception as e:
        return ResponseUtil.error(message=f"發布初始值至 PLC 失敗: {str(e)}")

