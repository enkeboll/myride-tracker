from datetime import datetime
from zoneinfo import ZoneInfo
from scheduler import is_bus_active_time, get_active_window_info

ET = ZoneInfo("America/New_York")

def test_active_window_during_school_bus_hours():
    # Monday 8:15 AM ET -> Active
    mon_815 = datetime(2026, 9, 14, 8, 15, tzinfo=ET)
    assert is_bus_active_time(mon_815, ignore_schedule=False) is True

    # Monday 7:45 AM ET -> Active
    mon_745 = datetime(2026, 9, 14, 7, 45, tzinfo=ET)
    assert is_bus_active_time(mon_745, ignore_schedule=False) is True

    # Monday 8:50 AM ET -> Active
    mon_850 = datetime(2026, 9, 14, 8, 50, tzinfo=ET)
    assert is_bus_active_time(mon_850, ignore_schedule=False) is True

def test_inactive_window_outside_bus_hours():
    # Monday 7:30 AM ET -> Inactive
    mon_730 = datetime(2026, 9, 14, 7, 30, tzinfo=ET)
    assert is_bus_active_time(mon_730, ignore_schedule=False) is False

    # Monday 9:00 AM ET -> Inactive
    mon_900 = datetime(2026, 9, 14, 9, 0, tzinfo=ET)
    assert is_bus_active_time(mon_900, ignore_schedule=False) is False

    # Saturday 8:15 AM ET -> Inactive
    sat_815 = datetime(2026, 9, 19, 8, 15, tzinfo=ET)
    assert is_bus_active_time(sat_815, ignore_schedule=False) is False

def test_ignore_schedule_override():
    mon_730 = datetime(2026, 9, 14, 7, 30, tzinfo=ET)
    assert is_bus_active_time(mon_730, ignore_schedule=True) is True

def test_get_active_window_info():
    mon_815 = datetime(2026, 9, 14, 8, 15, tzinfo=ET)
    is_active, time_str, msg = get_active_window_info(mon_815)
    assert is_active is True
    assert "Active window" in msg
