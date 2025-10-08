import pandas as pd
from pydantic import BaseModel


class SourceMedia(BaseModel):
    """Source minimal model."""

    Name: str
    Youtube: str | None
    """Youtube channel"""
    X: str | None
    """X (formerly Twitter) handle"""
    Substack: str | None
    """Substack handle"""


class Source(BaseModel):
    """Media model."""

    Name: str
    X: str
    Youtube: str
    Substack: str | None
    Website: str
    About: str
    TrustFactors: str
    Topics: str


class SourceMinimal(BaseModel):
    """Source model."""

    Name: str
    About: str
    Topics: str


def get_data(force: bool = False) -> list[dict[str, str]]:
    csv_file = "data/sources.csv"
    df = pd.read_csv(csv_file, na_filter=False)
    return df.to_dict(orient="records")
