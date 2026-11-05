from datetime import timedelta
from sqlalchemy import text
from app.models.plc_command_task_model import PlcCommandTask
from app.database.session import SessionLocal
from app.core.logger import logger
from app.utils.datetime_util import get_local_now


class PlcCommandTaskRepository:
    def delete_records_older_than(self, days: int) -> int:
        """刪除超過指定天數且已結束 (非 PENDING) 的 PLC 重試佇列紀錄 (plc_command_tasks)"""
        # createdAt 以本地時間寫入 (見 PlcCommandService._enqueue_unconfirmed)
        cutoff_date = get_local_now() - timedelta(days=days)
        db = SessionLocal()
        try:
            num_deleted = (
                db.query(PlcCommandTask)
                .filter(PlcCommandTask.createdAt < cutoff_date, PlcCommandTask.status != "PENDING")
                .delete(synchronize_session=False)
            )
            db.commit()
            if num_deleted > 0:
                logger.info(f"[PlcCommandTaskRepository] Cleaned up {num_deleted} expired plc command tasks older than {days} days.")
                db.execute(text("PRAGMA optimize;"))
            return num_deleted
        except Exception as e:
            db.rollback()
            logger.error(f"[PlcCommandTaskRepository] Error cleaning up expired plc command tasks: {e}")
            return 0
        finally:
            db.close()

plc_command_task_repo = PlcCommandTaskRepository()
