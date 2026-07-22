from fastapi import APIRouter
from app.api.v1.endpoints import health_controller, user_controller, config_controller

api_router = APIRouter()

# 系統與健康檢查路由
api_router.include_router(health_controller.router, prefix="/health", tags=["健康檢查 (Health Check)"])
api_router.include_router(user_controller.router, prefix="/users", tags=["用戶管理 (Users)"])
api_router.include_router(config_controller.router, prefix="/configs", tags=["系統設定 (Configs)"])
