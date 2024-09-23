from datetime import datetime, timedelta
from typing import List


def get_since_date(period_days: int = 3) -> List[int]:
    today = datetime.today()
    since = today - timedelta(days=period_days)
    return [since.year, since.month, since.day]
