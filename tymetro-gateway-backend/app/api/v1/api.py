from fastapi import APIRouter
from app.api.v1.endpoints import (
    health_controller,
    user_controller,
    config_controller,
    equipment_controller,
    car_controller,
    sensor_controller,
    sensor_history_controller
)

api_router = APIRouter()

# 系統與健康檢查路由
api_router.include_router(health_controller.router, prefix="/health", tags=["健康檢查 (Health Check)"])
api_router.include_router(user_controller.router, prefix="/users", tags=["用戶管理 (Users)"])
api_router.include_router(config_controller.router, prefix="/configs", tags=["系統設定 (Configs)"])
api_router.include_router(equipment_controller.router, prefix="/equipments", tags=["設備管理 (Equipments)"])
api_router.include_router(car_controller.router, prefix="/cars", tags=["車廂管理 (Cars)"])
api_router.include_router(sensor_controller.router, prefix="/sensors", tags=["感測器管理 (Sensors)"])
api_router.include_router(sensor_history_controller.router, prefix="/sensor-histories", tags=["感測器歷史紀錄 (Sensor Histories)"])


