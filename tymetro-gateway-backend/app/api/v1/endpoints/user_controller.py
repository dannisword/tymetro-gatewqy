from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Optional
from app.api.deps import get_user_service, get_current_user
from app.services.user_service import UserService
from app.schemas.user_schema import UserCreate, UserUpdate, UserResponse, UserLoginRequest
from app.schemas.response_schema import ResponseBase, ResponseList
from app.utils.response_util import ResponseUtil
from app.core.security import create_access_token
from app.models.user_model import User

router = APIRouter()

@router.post("/register", response_model=ResponseBase[UserResponse], summary="註冊新用戶")
def register_user(
    request: UserCreate, 
    service: UserService = Depends(get_user_service)
):
    try:
        user = service.register_user(request)
        return ResponseUtil.success(data=user, message="User registered successfully")
    except Exception as e:
        return ResponseUtil.error(message=str(e))

@router.post("/login", summary="用戶登入 (JSON)")
def login(
    request: UserLoginRequest,
    service: UserService = Depends(get_user_service)
):
    user = service.authenticate(request.account, request.password)
    if not user:
        return ResponseUtil.unauthorized("帳號或密碼錯誤")
    
    access_token = create_access_token(subject=user.id)
    
    return ResponseUtil.success(
        data={
            "accessToken": access_token,
            "tokenType": "bearer",
            "userId": user.id,
            "account": user.account,
            "userName": user.userName
        },
        message="Login successful"
    )

@router.post("/login/access-token", summary="專供 Swagger 使用的 Token 接口")
def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: UserService = Depends(get_user_service)
):
    user = service.authenticate(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號或密碼錯誤",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(subject=user.id)
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=ResponseBase[UserResponse], summary="獲取當前用戶資訊")
def get_me(current_user: User = Depends(get_current_user)):
    return ResponseUtil.success(data=current_user)

@router.get("", response_model=ResponseList[UserResponse], summary="獲取所有用戶清單")
def get_users(
    pageIndex: int = 0, 
    pageSize: int = 50, 
    propertyName: str = "id",
    order: str = "DESC",
    account: Optional[str] = None,
    userName: Optional[str] = None,
    orgId: Optional[int] = None,
    isActive: Optional[bool] = None,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
):
    users, total = service.get_users(
        account=account, 
        userName=userName,
        orgId=orgId,
        isActive=isActive,
        pageIndex=pageIndex, 
        pageSize=pageSize,
        propertyName=propertyName,
        order=order
    )
    return ResponseUtil.list_success(
        data=users, 
        total=total,
        pageIndex=pageIndex,
        pageSize=pageSize
    )

@router.get("/{user_id}", response_model=ResponseBase[UserResponse], summary="獲取用戶詳細資訊")
def get_user(
    user_id: int, 
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
):
    user = service.get_user(user_id)
    return ResponseUtil.success(data=user)

@router.put("/{user_id}", response_model=ResponseBase[UserResponse], summary="更新用戶資訊")
def update_user(
    user_id: int, 
    request: UserUpdate, 
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
):
    user = service.update_user(user_id, request)
    return ResponseUtil.success(data=user, message="User updated successfully")

@router.delete("/{user_id}", response_model=ResponseBase, summary="刪除用戶")
def delete_user(
    user_id: int, 
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
):
    service.delete(user_id)
    return ResponseUtil.success(message="User deleted successfully")
