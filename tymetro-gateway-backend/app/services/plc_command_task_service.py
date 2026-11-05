from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.enums import get_setting_type_label
from app.models.plc_command_task_model import PlcCommandTask


def _iso(dt: Any) -> Optional[str]:
    """ORM 欄位 (Column[datetime]) 型別在靜態檢查下不是 datetime，故參數用 Any"""
    return dt.isoformat() if dt else None


class PlcCommandTaskService:
    """PLC 設定重試佇列 (plc_command_tasks) 查詢服務"""

    def __init__(self, db: Session):
        self.db = db

    def query_tasks(
        self,
        command: Optional[str] = None,
        carNo: Optional[int] = None,
        endPos: Optional[int] = None,
        status: Optional[str] = None,
        startTime: Optional[datetime] = None,
        endTime: Optional[datetime] = None,
        pageIndex: int = 0,
        pageSize: int = 50,
        order: str = "DESC",
    ) -> Tuple[List[Dict[str, Any]], int]:
        """依條件分頁查詢，回傳 (items, total)"""
        query = self.db.query(PlcCommandTask)
        if command:
            query = query.filter(PlcCommandTask.command == command)
        if carNo is not None:
            query = query.filter(PlcCommandTask.carNo == carNo)
        if endPos is not None:
            query = query.filter(PlcCommandTask.endPos == endPos)
        if status:
            query = query.filter(PlcCommandTask.status == status.upper())
        if startTime:
            query = query.filter(PlcCommandTask.createdAt >= startTime)
        if endTime:
            query = query.filter(PlcCommandTask.createdAt <= endTime)

        total = query.count()
        ordering = PlcCommandTask.createdAt.asc() if order.upper() == "ASC" else PlcCommandTask.createdAt.desc()
        rows = query.order_by(ordering, PlcCommandTask.id.desc()).offset(pageIndex * pageSize).limit(pageSize).all()

        return [self._to_dict(r) for r in rows], total

    @staticmethod
    def _to_dict(r: PlcCommandTask) -> Dict[str, Any]:
        return {
            "id": r.id,
            "command": r.command,
            "commandName": get_setting_type_label(str(r.command)),
            "value": r.value,
            "carNo": r.carNo,
            "endPos": r.endPos,
            "trainCode": r.trainCode,
            "event": r.event,
            "operator": r.operator,
            "status": r.status,
            "attemptCount": r.attemptCount,
            "maxAttempts": r.maxAttempts,
            "lastError": r.lastError,
            "createdAt": _iso(r.createdAt),
            "updatedAt": _iso(r.updatedAt),
        }
