from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from app.api.deps import get_car_service, get_current_user
from app.services.car_service import CarService
from app.schemas.car_schema import CarCreate, CarUpdate, CarResponse
from app.schemas.response_schema import ResponseBase, ResponseList
from app.utils.response_util import ResponseUtil
from app.models.user_model import User

router = APIRouter()

@router.get("", response_model=ResponseList[CarResponse], summary="獲取車廂清單")
def get_cars(
    pageIndex: int = 0,
    pageSize: int = 50,
    propertyName: str = "id",
    order: str = "ASC",
    trainCode: Optional[str] = None,
    carNo: Optional[int] = None,
    carVin: Optional[str] = None,
    carType: Optional[str] = None,
    carStatus: Optional[str] = None,
    isActive: Optional[bool] = None,
    service: CarService = Depends(get_car_service),
    current_user: User = Depends(get_current_user)
):
    items, total = service.get_cars(
        trainCode=trainCode,
        carNo=carNo,
        carVin=carVin,
        carType=carType,
        carStatus=carStatus,
        isActive=isActive,
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

@router.get("/{car_id}", response_model=ResponseBase[CarResponse], summary="獲取單一車廂詳細資訊")
def get_car(
    car_id: int,
    service: CarService = Depends(get_car_service),
    current_user: User = Depends(get_current_user)
):
    item = service.get_car(car_id)
    if not item:
        return ResponseUtil.not_found("Car not found")
    return ResponseUtil.success(data=item)

@router.post("", response_model=ResponseBase[CarResponse], summary="建立新車廂")
def create_car(
    request: CarCreate,
    service: CarService = Depends(get_car_service),
    current_user: User = Depends(get_current_user)
):
    try:
        item = service.create_car(request)
        return ResponseUtil.success(data=item, message="Car created successfully")
    except Exception as e:
        return ResponseUtil.error(message=str(e))

@router.put("/{car_id}", response_model=ResponseBase[CarResponse], summary="更新車廂資訊")
def update_car(
    car_id: int,
    request: CarUpdate,
    service: CarService = Depends(get_car_service),
    current_user: User = Depends(get_current_user)
):
    try:
        item = service.update_car(car_id, request)
        return ResponseUtil.success(data=item, message="Car updated successfully")
    except Exception as e:
        return ResponseUtil.error(message=str(e))

@router.delete("/{car_id}", response_model=ResponseBase, summary="刪除車廂")
def delete_car(
    car_id: int,
    service: CarService = Depends(get_car_service),
    current_user: User = Depends(get_current_user)
):
    try:
        service.delete(car_id)
        return ResponseUtil.success(message="Car deleted successfully")
    except Exception as e:
        return ResponseUtil.error(message=str(e))
