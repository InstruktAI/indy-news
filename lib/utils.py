from datetime import datetime, timedelta
from typing import List


def get_since_date(period_days: int = 3, end_date: str = None) -> List[int]:
    end_date_obj: datetime
    if end_date:
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        end_date_obj = datetime.today()
    since: datetime = end_date_obj - timedelta(days=period_days)
    return [since.year, since.month, since.day]
