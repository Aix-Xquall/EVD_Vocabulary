import csv
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


HOLIDAY_DIR = Path(__file__).resolve().parent / "holidays"
TAIPEI_TIME_ZONE = timezone(timedelta(hours=8))


def today_in_taipei(now: datetime | None = None) -> date:
    return (now or datetime.now(TAIPEI_TIME_ZONE)).astimezone(TAIPEI_TIME_ZONE).date()


def is_study_day(target_date: date) -> bool:
    """Use Taiwan's government office calendar; weekends are always rest days."""
    if target_date.weekday() >= 5:
        return False

    calendar_path = HOLIDAY_DIR / f"taiwan_{target_date.year}.csv"
    if not calendar_path.exists():
        raise FileNotFoundError(
            f"Missing Taiwan holiday calendar for {target_date.year}: {calendar_path}"
        )

    with calendar_path.open(encoding="utf-8-sig", newline="") as stream:
        rows = csv.DictReader(stream)
        if rows.fieldnames != ["date", "name"]:
            raise ValueError(f"Invalid Taiwan holiday calendar header: {calendar_path}")
        holidays = set()
        for row in rows:
            holiday = date.fromisoformat(row["date"])
            if holiday.year != target_date.year:
                raise ValueError(f"Holiday outside calendar year: {holiday}")
            holidays.add(holiday)
    return target_date not in holidays
