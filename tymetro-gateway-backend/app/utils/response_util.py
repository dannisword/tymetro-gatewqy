from typing import Any, List
from fastapi import HTTPException, status
from app.schemas.response_schema import ResponseBase, ResponseList

class ResponseUtil:
    @staticmethod
    def success(data: Any = None, message: str = "操作成功") -> ResponseBase:
        return ResponseBase(
            success=True,
            message=message,
            data=data
        )

    @staticmethod
    def list_success(
        data: List[Any], 
        total: int, 
        pageIndex: int = 0, 
        pageSize: int = 100, 
        message: str = "查詢成功"
    ) -> ResponseList:
        from app.schemas.response_schema import PageData
        
        page_data = PageData(
            source=data,
            pageIndex=pageIndex,
            pageSize=pageSize,
            total=total
        )
        
        return ResponseList(
            success=True,
            message=message,
            data=page_data
        )

    @staticmethod
    def error(message: str = "操作失敗", status_code: int = status.HTTP_400_BAD_REQUEST):
        raise HTTPException(
            status_code=status_code,
            detail=message
        )

    @staticmethod
    def not_found(message: str = "找不到相關資料"):
        return ResponseUtil.error(message, status_code=status.HTTP_404_NOT_FOUND)

    @staticmethod
    def unauthorized(message: str = "未經授權或憑證已過期"):
        return ResponseUtil.error(message, status_code=status.HTTP_401_UNAUTHORIZED)

    @staticmethod
    def forbidden(message: str = "權限不足，拒絕存取"):
        return ResponseUtil.error(message, status_code=status.HTTP_403_FORBIDDEN)
