from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Tuple
from config import settings

ET_TIMEZONE = ZoneInfo("America/New_York")

def is_bus_active_time(dt: datetime = None, ignore_schedule: bool = None) -> bool:
    """
    Checks if the current time (or given datetime) falls within the active bus tracking window:
    Monday through Friday, 7:45 AM to 8:50 AM Eastern Time (ET).
    """
    if ignore_schedule is None:
        ignore_schedule = settings.myride_ignore_schedule

    if ignore_schedule:
        return True

    now = dt or datetime.now(ET_TIMEZONE)
    if now.tzinfo is None:
        now = now.replace(tzinfo=ET_TIMEZONE)
    else:
        now = now.astimezone(ET_TIMEZONE)

    # Saturday (5) or Sunday (6)
    if now.weekday() > 4:
        return False

    current_minutes = now.hour * 60 + now.minute
    start_minutes = 7 * 60 + 45   # 7:45 AM
    end_minutes = 8 * 60 + 50     # 8:50 AM

    return start_minutes <= current_minutes <= end_minutes

def get_active_window_info(dt: datetime = None) -> Tuple[bool, str, str]:
    """
    Returns (is_active, current_time_formatted, status_message)
    """
    now = dt or datetime.now(ET_TIMEZONE)
    if now.tzinfo is None:
        now = now.replace(tzinfo=ET_TIMEZONE)
    else:
        now = now.astimezone(ET_TIMEZONE)

    time_str = now.strftime("%Y-%m-%d %I:%M:%S %p ET (%a)")
    is_active = is_bus_active_time(now)

    if is_active:
        msg = "Active window (Mon-Fri 7:45 AM - 8:50 AM ET)"
    elif now.weekday() > 4:
        msg = "Off-hours (Weekend - Bus inactive)"
    else:
        msg = "Off-hours (Mon-Fri active window is 7:45 AM - 8:50 AM ET)"

    return is_active, time_str, msg
