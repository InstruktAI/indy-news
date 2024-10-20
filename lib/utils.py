from datetime import datetime, timedelta
from typing import List


def get_since_date(period_days: int = 3, since_str: str = None) -> List[int]:
    since_date: datetime
    if since_str:
        since_date = datetime.strptime(since_str, "%Y-%m-%d")
    else:
        since_date = datetime.today()
    since: datetime = since_date - timedelta(days=period_days)
    return [since.year, since.month, since.day]
