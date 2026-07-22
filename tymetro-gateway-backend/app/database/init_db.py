import json
from sqlalchemy.orm import Session
from app.models.user_model import User
from app.models.config_model import Config
from app.core.logger import logger
from datetime import datetime, timezone
from app.core.security import get_password_hash

def init_mock_data(db: Session):
    """初始化預設資料：若 users 表為空，則插入預設 admin 帳號；若 configs 表無 MTR_PARAMS，則插入預設參數"""
    try:
        admin_user = db.query(User).filter(User.account == "admin").first()
        if not admin_user:
            logger.info("Creating default admin user in SQLite...")
            admin_user = User(
                orgId=1,
                orgCode="HQ",
                account="admin",
                userName="系統管理員",
                password=get_password_hash("admin123"),
                isActive=True,
                enableAt=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            db.add(admin_user)
            db.commit()
            logger.info("Default admin user created successfully.")
        else:
            logger.debug("Default admin user already exists.")
            if admin_user.password == "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW":
                logger.info("Updating default admin user password to valid bcrypt hash...")
                admin_user.password = get_password_hash("admin123")
                db.commit()

        # 初始化捷運參數預設值
        if not db.query(Config).filter(Config.configType == "MTR_PARAMS").first():
            logger.info("Creating default MTR_PARAMS config in gateway...")
            mtr_params = {
                "leftItems": [
                    {
                        "name": "車組/車廂資料維護",
                        "route": "/mtr/vehicle-data",
                        "isOpen": False,
                        "fields": [
                            {"label": "車組代碼", "key": "trainCode", "type": "text", "placeholder": "請輸入車組代碼"},
                            {"label": "車廂代碼", "key": "carVin", "type": "text", "placeholder": "請輸入車廂代碼"},
                            {"label": "車廂序", "key": "carSeq", "type": "number", "placeholder": "請輸入車廂序"},
                            {"label": "端點位置", "key": "endpointPos", "type": "text", "placeholder": "0"}
                        ],
                        "formData": {
                            "trainCode": "T101",
                            "carVin": "1101",
                            "carSeq": "1",
                            "endpointPos": "1"
                        }
                    },
                    {
                        "name": "PLC 設備資料維護",
                        "route": "/mtr/plc-data",
                        "isOpen": False,
                        "fields": [
                            {"label": "IPAddress", "key": "ipAddress", "type": "text", "placeholder": "192.168.1.1"},
                            {"label": "Modbus Port", "key": "port", "type": "text", "placeholder": "502"}
                        ],
                        "formData": {
                            "ipAddress": "192.168.1.1",
                            "port": "502"
                        }
                    },
                    {
                        "name": "啟動延時參數",
                        "route": "/mtr/startup-params",
                        "isOpen": False,
                        "fields": [
                            {"label": "1/4車系統啟動延時(秒)", "key": "startDelay14", "type": "number", "placeholder": "預設: 35"},
                            {"label": "2/3車系統啟動延時(秒)", "key": "startDelay23", "type": "number", "placeholder": "預設: 40"},
                            {"label": "風門 -> 送風機啟動延時(秒)", "key": "damperFanDelay", "type": "number", "placeholder": "預設: 30"},
                            {"label": "送風機 -> 冷凝風扇啟動延時(秒)", "key": "fanCondDelay", "type": "number", "placeholder": "預設: 10"},
                            {"label": "冷凝風扇 -> 壓縮機啟動延時(秒)", "key": "condCompDelay", "type": "number", "placeholder": "預設: 1"},
                            {"label": "壓縮機 -> 壓縮機啟動延時(秒)", "key": "compCompDelay", "type": "number", "placeholder": "預設: 10"},
                            {"label": "壓縮機 -> 壓縮機關閉延時(秒)", "key": "compUnloadDelay", "type": "number", "placeholder": "預設: 5"},
                            {"label": "壓縮機最短運轉時間(秒)", "key": "minRunTime", "type": "number", "placeholder": "預設: 180"},
                            {"label": "壓縮機最短再啟動週期(秒)", "key": "minCycleTime", "type": "number", "placeholder": "預設: 360"},
                            {"label": "壓縮機最短停機時間(秒)", "key": "minStopTime", "type": "number", "placeholder": "預設: 30"},
                            {"label": "冷凝風扇初始高通風時間(秒)", "key": "initHighSpeed", "type": "number", "placeholder": "預設: 10"},
                            {"label": "強制全載測試最大時間(秒)", "key": "maxFullLoad", "type": "number", "placeholder": "預設: 1200"},
                            {"label": "SIV 動作多久進通風模式(秒)", "key": "sivFaultDelay", "type": "number", "placeholder": "預設: 15"}
                        ],
                        "formData": {
                            "startDelay14": 35,
                            "startDelay23": 40,
                            "damperFanDelay": 30,
                            "fanCondDelay": 10,
                            "condCompDelay": 1,
                            "compCompDelay": 10,
                            "compUnloadDelay": 5,
                            "minRunTime": 180,
                            "minCycleTime": 360,
                            "minStopTime": 30,
                            "initHighSpeed": 10,
                            "maxFullLoad": 1200,
                            "sivFaultDelay": 15
                        }
                    }
                ],
                "rightItems": [
                    {
                        "name": "壓力閾值與泵集控制",
                        "route": "/mtr/pressure-pump-params",
                        "isOpen": False,
                        "fields": [
                            {"label": "高速風扇壓力值(kPa)", "key": "highSpeedPress", "type": "number", "placeholder": "預設: 2300"},
                            {"label": "低速風扇壓力值(kPa)", "key": "lowSpeedPress", "type": "number", "placeholder": "預設: 1800"},
                            {"label": "泵集完成低壓值(kPa)", "key": "pumpDownPress", "type": "number", "placeholder": "預設: 250"},
                            {"label": "泵集最大時間(sec)", "key": "maxPumpTime", "type": "number", "placeholder": "預設: 30"},
                            {"label": "高壓過高跳脫值(kPa)", "key": "highPressTrip", "type": "number", "placeholder": "預設: 2760"},
                            {"label": "高壓警報復歸值(kPa)", "key": "highPressReset", "type": "number", "placeholder": "預設: 2070"},
                            {"label": "低壓過低跳脫值(kPa)", "key": "lowPressTrip", "type": "number", "placeholder": "預設: 276"},
                            {"label": "低壓警報復歸值(kPa)", "key": "lowPressReset", "type": "number", "placeholder": "預設: 410"},
                            {"label": "高低壓差過低跳脫值(kPa)", "key": "diffPressTrip", "type": "number", "placeholder": "預設: 1000"}
                        ],
                        "formData": {
                            "highSpeedPress": 2300,
                            "lowSpeedPress": 1800,
                            "pumpDownPress": 250,
                            "maxPumpTime": 30,
                            "highPressTrip": 2760,
                            "highPressReset": 2070,
                            "lowPressTrip": 276,
                            "lowPressReset": 410,
                            "diffPressTrip": 1000
                        }
                    },
                    {
                        "name": "警報延時、計數與校正值",
                        "route": "/mtr/alarm-delay-params",
                        "isOpen": False,
                        "fields": [
                            {"label": "高壓警報延時(sec)", "key": "highPressAlarmDly", "type": "number", "placeholder": "預設: 1"},
                            {"label": "低壓警報延時(sec)", "key": "lowPressAlarmDly", "type": "number", "placeholder": "預設: 5"},
                            {"label": "回風高溫警報值(0.1°C)", "key": "highTempAlarm", "type": "number", "placeholder": "預設: 330"},
                            {"label": "PLC WD 重置允許次數", "key": "plcWdResetLimit", "type": "number", "placeholder": "預設: 3"},
                            {"label": "高壓跳脫允許次數", "key": "highPressTryLimit", "type": "number", "placeholder": "預設: 3"},
                            {"label": "回風溫度校正(0.1°C)", "key": "tempCalibration", "type": "number", "placeholder": "預設: 0"},
                            {"label": "高壓 1 讀值校正(kPa)", "key": "hp1Calibration", "type": "number", "placeholder": "預設: 0"},
                            {"label": "低壓 1 讀值校正(kPa)", "key": "lp1Calibration", "type": "number", "placeholder": "預設: 0"},
                            {"label": "高壓 2 讀值校正(kPa)", "key": "hp2Calibration", "type": "number", "placeholder": "預設: 0"},
                            {"label": "低壓 2 讀值校正(kPa)", "key": "lp2Calibration", "type": "number", "placeholder": "預設: 0"}
                        ],
                        "formData": {
                            "highPressAlarmDly": 1,
                            "lowPressAlarmDly": 5,
                            "highTempAlarm": 330,
                            "plcWdResetLimit": 3,
                            "highPressTryLimit": 3,
                            "tempCalibration": 0,
                            "hp1Calibration": 0,
                            "lp1Calibration": 0,
                            "hp2Calibration": 0,
                            "lp2Calibration": 0
                        }
                    }
                ]
            }
            cfg = Config(
                configType="MTR_PARAMS",
                configContent=json.dumps(mtr_params, ensure_ascii=False)
            )
            db.add(cfg)
            db.commit()
            logger.info("Default MTR_PARAMS config created successfully in gateway.")

        # 初始化時段表設定預設值 (單一筆 row 整合所有模式，使用標準英文代號)
        old_schedules = db.query(Config).filter(Config.configType == "SCHEDULE").all()
        if not old_schedules or len(old_schedules) > 1:
            if len(old_schedules) > 1:
                logger.info("Removing 8 separate SCHEDULE configs to consolidate into a single row...")
                for item in old_schedules:
                    db.delete(item)
                db.commit()

            logger.info("Creating default SCHEDULE config (single row with English codes) in gateway...")
            mode_codes = [
                'spring1', 'spring2',
                'summer1', 'summer2',
                'autumn1', 'autumn2',
                'winter1', 'winter2'
            ]
            
            def create_default_matrix():
                matrix = []
                for h in range(24):
                    row = []
                    for d in range(7):
                        if d == 0 or d == 6:
                            val = 24.5 if h == 0 else 0.0
                        elif 7 <= h <= 19:
                            val = 23.5 if h in [7, 8, 17, 18, 19] else 24.5
                        else:
                            val = 24.5
                        row.append(val)
                    matrix.append(row)
                return matrix

            all_schedules_dict = {code: create_default_matrix() for code in mode_codes}
            cfg_item = Config(
                configType="SCHEDULE",
                configContent=json.dumps(all_schedules_dict, ensure_ascii=False)
            )
            db.add(cfg_item)
            db.commit()
            logger.info("Default consolidated SCHEDULE config created successfully in gateway.")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to initialize mock data: {e}")
