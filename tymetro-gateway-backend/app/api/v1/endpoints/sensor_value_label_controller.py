from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.sensor_value_label_model import SensorValueLabel
from app.models.user_model import User
from app.schemas.response_schema import ResponseBase
from app.utils.response_util import ResponseUtil

router = APIRouter()

@router.get("", response_model=ResponseBase, summary="獲取本機數值對照文字 (自中心端下載)")
def get_value_labels(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rows = db.query(SensorValueLabel).order_by(SensorValueLabel.sensorCode, SensorValueLabel.bitMask).all()
    data = [
        {
            "sensorCode": r.sensorCode,
            "bitMask": r.bitMask,
            "matchValue": r.matchValue,
            "text": r.text,
            "label": r.label,
            "description": r.description,
        }
        for r in rows
    ]
    return ResponseUtil.success(data=data)
