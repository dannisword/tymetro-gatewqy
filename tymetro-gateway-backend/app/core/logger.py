import os
import sys
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

import logging

class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

def setup_logger():
    log_path_env = os.getenv("LOG_PATH", "logs/gateway.log")
    log_dir = os.path.dirname(log_path_env) or "logs"
    
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    logger.remove()

    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<magenta>{extra[service]}</magenta> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    file_format = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[service]} | {name}:{function}:{line} - {message}"

    logger.configure(extra={"service": "GATEWAY"}) 

    log_level_env = os.getenv("LOG_LEVEL", "INFO").upper()

    # 控制台輸出
    logger.add(sys.stderr, format=console_format, level=log_level_env, enqueue=True)

    # 檔案輸出
    log_file_format = os.path.join(log_dir, "gateway.log")
    
    import datetime
    try:
        if os.path.exists(log_file_format):
            mtime = os.path.getmtime(log_file_format)
            current_date = datetime.date.fromtimestamp(mtime)
        else:
            current_date = datetime.date.today()
    except Exception:
        current_date = datetime.date.today()

    def rotation_condition(message, file):
        nonlocal current_date
        # 1. 檢查大小是否超過 10 MB
        file.seek(0, 2)
        if file.tell() + len(message) > 10 * 1024 * 1024:
            return True
        # 2. 檢查是否跨天 (當前記錄的日期大於上次記錄/修改日期)
        msg_date = message.record["time"].date()
        if msg_date > current_date:
            current_date = msg_date
            return True
        return False

    logger.add(
        log_file_format,
        rotation=rotation_condition,
        retention="10 days",
        compression="zip",
        encoding="utf-8",
        enqueue=True,
        format=file_format,
        level=log_level_env
    )

    # 攔截並轉發標準 logging 日誌到 loguru (包含 uvicorn)
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        logging_logger = logging.getLogger(name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False

    return logger

logger = setup_logger()
