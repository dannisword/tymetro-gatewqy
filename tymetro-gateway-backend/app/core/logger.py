import os
import sys
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

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

    # 控制台輸出
    logger.add(sys.stderr, format=console_format, level="INFO", enqueue=True)

    # 檔案輸出
    log_file_format = os.path.join(log_dir, "gateway_{time:YYYY-MM-DD}.log")
    logger.add(
        log_file_format,
        rotation="10 MB",
        retention="10 days",
        compression="zip",
        encoding="utf-8",
        enqueue=True,
        format=file_format,
        level="INFO"
    )

    return logger

logger = setup_logger()
