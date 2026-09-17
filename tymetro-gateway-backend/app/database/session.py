from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# 資料庫連線配置
SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL

# 根據資料庫類型調整引擎參數
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    from sqlalchemy import event

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"check_same_thread": False, "timeout": 30}
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        # 1. 啟用 WAL 模式 (Write-Ahead Logging)：大幅改善並行性，背景採集寫入時不再阻塞讀取
        cursor.execute("PRAGMA journal_mode = WAL;")
        # 2. 同步級別改為 NORMAL：在 WAL 模式下安全且顯著減少對 Flash/SD 卡的 fsync 次數
        cursor.execute("PRAGMA synchronous = NORMAL;")
        # 3. 記憶體快取大小：設為 16MB (負數代表 KB，-16000 約 16MB，適合 PFC200 記憶體限制)
        cursor.execute("PRAGMA cache_size = -16000;")
        # 4. 排序與暫存表置於記憶體，減少對 SD 卡的讀寫
        cursor.execute("PRAGMA temp_store = MEMORY;")
        # 5. 開啟 64MB 記憶體映射 I/O，加速唯讀查詢
        cursor.execute("PRAGMA mmap_size = 67108864;")
        # 6. 設定鎖定等待時間 (5秒)，防止 database is locked 拋出異常
        cursor.execute("PRAGMA busy_timeout = 5000;")
        cursor.close()
else:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
