import time
from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. 紀錄請求開始時間
        start_time = time.perf_counter()
        
        # 2. 獲取請求基本資訊
        method = request.method
        path = request.url.path
        client_host = request.client.host if request.client else "unknown"
        
        # 綁定日誌上下文，標註這是來自 HTTP 的請求
        local_logger = logger.bind(service="HTTP", client=client_host)
        
        try:
            # 3. 執行後續的路由邏輯
            response = await call_next(request)
            
            # 4. 計算耗時 (秒轉毫秒)
            process_time = (time.perf_counter() - start_time) * 1000
            
            # 5. 根據狀態碼決定日誌等級
            status_code = response.status_code
            log_msg = f"{method} {path} | Status: {status_code} | Time: {process_time:.2f}ms"
            
            if 200 <= status_code < 400:
                local_logger.info(log_msg)
            else:
                local_logger.warning(log_msg)
                
            # 將處理時間放入 Response Header
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
            
            return response

        except Exception as e:
            # 捕捉未被處理的異常，紀錄錯誤並計算耗時
            process_time = (time.perf_counter() - start_time) * 1000
            local_logger.error(f"{method} {path} | FAILED | Time: {process_time:.2f}ms | Error: {str(e)}")
            raise e
