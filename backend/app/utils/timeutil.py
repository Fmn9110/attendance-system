from datetime import datetime


def format_duration(started_at: datetime | None, finished_at: datetime | None) -> str:
    if not started_at or not finished_at:
        return ""
    secs = int((finished_at - started_at).total_seconds())
    if secs < 0:
        secs = 0
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def duration_human_cn(started_at: datetime | None, finished_at: datetime | None) -> str:
    if not started_at or not finished_at:
        return ""
    secs = int((finished_at - started_at).total_seconds())
    if secs < 0:
        secs = 0
    d, rem = divmod(secs, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if d:
        parts.append(f"{d}天")
    if h:
        parts.append(f"{h}小时")
    if m:
        parts.append(f"{m}分")
    if s and not h:
        parts.append(f"{s}秒")
    if not parts:
        return "0秒"
    return "".join(parts)


def cn_date(dt: datetime) -> str:
    return f"{dt.month}月{dt.day}日"


def cn_time(dt: datetime) -> str:
    return f"{dt.hour}点{dt.minute:02d}分"
