import json
import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError
from typing import Any, Dict, Optional
import time
from datetime import datetime, timedelta, timezone
from jose import jwt
from app.core.config import settings
from app.core.logger import logger

class HttpUtil:
    # Memory cache for the central JWT Token
    _token_cache: Dict[str, Any] = {
        "token": None,
        "expiry": 0
    }

    @staticmethod
    def get_central_backend_token() -> Optional[str]:
        """
        取得呼叫中央後端 (tymetro-backend) 的 JWT Token。
        支援 2 種驗證方式：
        1. password: 向中央後端發送帳號密碼登入 (POST /api/v1/users/login/access-token) 換取 Token
        2. secret_key: 使用固定 SECRET_KEY 直接在本地簽發合法 JWT Token（免去網路登入請求，安全穩定）
        """
        now = time.time()
        if HttpUtil._token_cache["token"] and HttpUtil._token_cache["expiry"] > now + 60:
            return HttpUtil._token_cache["token"]

        auth_type = getattr(settings, "TYMETRO_BACKEND_AUTH_TYPE", "secret_key").lower()

        # 方式 2: 固定 SECRET_KEY 驗證
        if auth_type in ("secret_key", "secret", "token"):
            secret = getattr(settings, "TYMETRO_BACKEND_SECRET_KEY", "") or settings.SECRET_KEY
            try:
                expire = datetime.now(timezone.utc) + timedelta(days=7)
                payload = {
                    "sub": "1",
                    "exp": expire,
                    "type": "gateway_service"
                }
                token = jwt.encode(payload, secret, algorithm=settings.ALGORITHM)
                HttpUtil._token_cache["token"] = token
                HttpUtil._token_cache["expiry"] = now + 3600 * 24
                logger.info("[HttpUtil] Generated central backend token using fixed SECRET_KEY successfully.")
                return token
            except Exception as e:
                logger.error(f"[HttpUtil] Failed to generate token with SECRET_KEY: {e}")
                return None

        # 方式 1: 帳號密碼登入驗證
        login_url = f"{settings.TYMETRO_BACKEND_URL.rstrip('/')}/api/v1/users/login/access-token"
        data = urllib.parse.urlencode({
            "username": settings.TYMETRO_BACKEND_USERNAME,
            "password": settings.TYMETRO_BACKEND_PASSWORD
        })

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        logger.info(f"Attempting login to central backend: {login_url}")
        resp_data = HttpUtil.post(login_url, data=data, headers=headers, timeout=5)

        if resp_data.get("access_token"):
            token = resp_data["access_token"]
            HttpUtil._token_cache["token"] = token
            HttpUtil._token_cache["expiry"] = now + 3600
            logger.info("Successfully fetched and cached central backend access token.")
            return token
        else:
            logger.error(f"Failed to fetch token from central backend: {resp_data.get('message', 'Unknown error')}")
            # 若帳密登入失敗，自動 fallback 至固定 SECRET_KEY 簽發
            logger.warning("[HttpUtil] Fallback to generating token using fixed SECRET_KEY.")
            secret = getattr(settings, "TYMETRO_BACKEND_SECRET_KEY", "") or settings.SECRET_KEY
            try:
                expire = datetime.now(timezone.utc) + timedelta(days=7)
                payload = {"sub": "1", "exp": expire, "type": "gateway_service"}
                token = jwt.encode(payload, secret, algorithm=settings.ALGORITHM)
                HttpUtil._token_cache["token"] = token
                HttpUtil._token_cache["expiry"] = now + 3600 * 24
                return token
            except Exception as e:
                logger.error(f"[HttpUtil] Fallback token generation also failed: {e}")
                return None

    @staticmethod
    def request(
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 5
    ) -> Dict[str, Any]:
        """
        發送 HTTP 請求並返回解析後的 JSON 結果或錯誤資訊。
        """
        method = method.upper()
        if headers is None:
            headers = {}
        
        # 處理 Query parameters
        if params:
            query_str = urllib.parse.urlencode(params)
            url = f"{url}?{query_str}" if "?" not in url else f"{url}&{query_str}"

        # 處理 Body payload
        req_data = None
        if data is not None:
            if isinstance(data, (dict, list)):
                req_data = json.dumps(data).encode("utf-8")
                if "Content-Type" not in headers:
                    headers["Content-Type"] = "application/json"
            elif isinstance(data, str):
                req_data = data.encode("utf-8")
            else:
                req_data = data

        req = urllib.request.Request(
            url,
            data=req_data,
            headers=headers,
            method=method
        )

        try:
            logger.debug(f"[HttpUtil] Sending {method} to {url}")
            with urllib.request.urlopen(req, timeout=timeout) as response:
                resp_bytes = response.read()
                if not resp_bytes:
                    return {"success": True, "message": "No Content", "data": None}
                
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return json.loads(resp_bytes.decode("utf-8"))
                else:
                    return {"success": True, "message": "Success", "data": resp_bytes.decode("utf-8")}
                    
        except HTTPError as e:
            logger.error(f"[HttpUtil] HTTP Error {e.code} for {method} {url}: {e.reason}")
            try:
                # 試圖讀取遠端伺服器返回的錯誤 JSON 訊息
                err_bytes = e.read()
                if err_bytes:
                    return json.loads(err_bytes.decode("utf-8"))
            except Exception:
                pass
            return {"success": False, "message": f"HTTP Error: {e.code} - {e.reason}", "data": None}
        except URLError as e:
            logger.error(f"[HttpUtil] Network Error for {method} {url}: {e.reason}")
            return {"success": False, "message": f"Network Error: {str(e.reason)}", "data": None}
        except Exception as e:
            logger.error(f"[HttpUtil] Unexpected Error for {method} {url}: {str(e)}")
            return {"success": False, "message": f"System Error: {str(e)}", "data": None}

    @staticmethod
    def get(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: int = 5) -> Dict[str, Any]:
        return HttpUtil.request("GET", url, params=params, headers=headers, timeout=timeout)

    @staticmethod
    def post(url: str, data: Optional[Any] = None, headers: Optional[Dict[str, str]] = None, timeout: int = 5) -> Dict[str, Any]:
        return HttpUtil.request("POST", url, data=data, headers=headers, timeout=timeout)

    @staticmethod
    def put(url: str, data: Optional[Any] = None, headers: Optional[Dict[str, str]] = None, timeout: int = 5) -> Dict[str, Any]:
        return HttpUtil.request("PUT", url, data=data, headers=headers, timeout=timeout)

    @staticmethod
    def delete(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: int = 5) -> Dict[str, Any]:
        return HttpUtil.request("DELETE", url, params=params, headers=headers, timeout=timeout)
