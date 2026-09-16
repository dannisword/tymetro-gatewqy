from datetime import datetime, timezone, timedelta
from typing import Optional

# 預設台灣/台北時區 UTC+8
LOCAL_TZ = timezone(timedelta(hours=8))

def get_local_now() -> datetime:
    """取得當前本地當地時間 (naive datetime)"""
    return datetime.now(LOCAL_TZ).replace(tzinfo=None)

def get_active_season_by_date(dt: datetime) -> str:
    """
    根據給定的日期 (月份與天數) 自動判斷並回傳對應的季節模式代碼。
    
    季節模式定義：
    - 春1 (spring1): 03/01 ~ 04/15
    - 春2 (spring2): 04/16 ~ 05/31
    - 夏1 (summer1): 06/01 ~ 07/15
    - 夏2 (summer2): 07/16 ~ 08/31
    - 秋1 (autumn1): 09/01 ~ 10/15
    - 秋2 (autumn2): 10/16 ~ 11/30
    - 冬1 (winter1): 12/01 ~ 01/15
    - 冬2 (winter2): 01/16 ~ 02/28 或 02/29
    """
    month = dt.month
    day = dt.day

    if month in [3, 4]:
        return "spring1" if (month == 3 or day <= 15) else "spring2"
    elif month == 5:
        return "spring2"
    elif month in [6, 7]:
        return "summer1" if (month == 6 or day <= 15) else "summer2"
    elif month == 8:
        return "summer2"
    elif month in [9, 10]:
        return "autumn1" if (month == 9 or day <= 15) else "autumn2"
    elif month == 11:
        return "autumn2"
    elif month in [12, 1]:
        return "winter1" if (month == 12 or day <= 15) else "winter2"
    elif month == 2:
        return "winter2"
    else:
        return "spring1"
