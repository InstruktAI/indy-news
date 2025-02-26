import json
import os
from typing import Dict, List, Union

import pandas as pd
from pydantic import BaseModel

allsides_file = "./data/allsides.com.json"
mbfc_file = "./data/mediabiasfactcheck.com.json"
csv_file = "./data/all.csv"


class SourceMedia(BaseModel):
    """Source minimal model"""

    Name: str
    Youtube: Union[str, None]
    """Youtube channel"""
    X: Union[str, None]
    """X (formerly Twitter) handle"""


class Source(BaseModel):
    """Media model"""

    Name: str
    Website: str
    Youtube: str
    About: str
    TrustFactors: str
    Topics: str
    Wikipedia: str
    X: str
    Bias: Union[str, None]
    Profile: Union[str, None]
    Factual: Union[str, None]
    Credibility: Union[str, None]


class SourceMinimal(BaseModel):
    """Source model"""

    Name: str
    About: str
    Topics: str


def _merge_facts(df: pd.DataFrame, facts: Dict[str, Dict[str, str]]) -> pd.DataFrame:
    def merge_fact(row: pd.Series) -> pd.Series:
        name = row["Name"].lower()
        if name in facts:
            fact = facts[name]
            row["Bias"] = fact["bias"]
            row["Profile"] = fact["profile"]
            row["Factual"] = fact["factual"]
            row["Credibility"] = fact["credibility"]
        else:
            print(f"Facts not found for {name}")
        return row

    return df.apply(merge_fact, axis=1)


def get_data(force: bool = False) -> List[Dict[str, str]]:
    combined = "data/combined.json"
    if not force and os.path.exists(combined):
        with open(combined, encoding="utf-8") as f:
            return json.load(f)
    else:
        # combine the data
        raw = pd.read_csv(csv_file, na_filter=False)
        with open(mbfc_file, encoding="utf-8") as f:
            fact_list = json.load(f)
        facts = {item["name"].lower(): item for item in fact_list}
        df = _merge_facts(raw, facts)
        data = df.where(pd.notnull(df), None).to_dict(orient="records")
        # write json to file:
        with open(combined, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return data


def query_allsides(query: str, limit: int = 5, offset: int = 0) -> List[Dict[str, str]]:
    with open(allsides_file, encoding="utf-8") as f:
        fact_list = json.load(f)
    results = []
    for item in fact_list:
        if query.lower() in item["name"].lower():
            results.append(item)
    return results[offset : offset + limit]


def query_mediabiasfactcheck(
    query: str, limit: int = 5, offset: int = 0
) -> List[Dict[str, str]]:
    with open(mbfc_file, encoding="utf-8") as f:
        fact_list = json.load(f)
    results = []
    for item in fact_list:
        if query.lower() in item["name"].lower():
            if item["credibility"] in [
                "medium credibility",
                "high credibility",
            ] or item["factual"] in ["factual", "mostly", "mixed"]:
                results.append(item)
    return results[offset : offset + limit]
