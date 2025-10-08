from datetime import datetime, timedelta


def get_since_date(period_days: int = 3, end_date: str | None = None) -> list[int]:
    end_date_obj: datetime
    end_date_obj = (
        datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.today()
    )
    since: datetime = end_date_obj - timedelta(days=period_days)
    return [since.year, since.month, since.day]
