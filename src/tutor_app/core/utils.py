# src/tutor_app/core/utils.py
import datetime
import pytz

def convert_to_beijing_time(utc_dt: datetime.datetime) -> datetime.datetime:
    """将UTC时间转换为北京时间"""
    if utc_dt is None:
        return None
    beijing_tz = pytz.timezone("Asia/Shanghai")
    # 首先将天真的datetime对象（无时区信息）设置为UTC时区
    # 然后再转换为北京时区
    return utc_dt.replace(tzinfo=pytz.utc).astimezone(beijing_tz)