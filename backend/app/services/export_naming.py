from datetime import datetime
from typing import Optional
from ..utils.timeutil import cn_date, cn_time


def single_filename(class_name: str, started_at: Optional[datetime]) -> str:
    if started_at:
        return f"{class_name}{cn_date(started_at)}{cn_time(started_at)}点名情况.xlsx"
    return f"{class_name}点名情况.xlsx"


def batch_filename(class_name: str, date_from: Optional[datetime], date_to: Optional[datetime]) -> str:
    if date_from and date_to:
        if date_from.date() == date_to.date():
            return f"{class_name}{cn_date(date_from)}的到课情况.xlsx"
        return f"{class_name}{cn_date(date_from)}到{cn_date(date_to)}的到课情况.xlsx"
    return f"{class_name}到课情况.xlsx"
