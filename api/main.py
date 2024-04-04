import os
from typing import Dict, List

from fastapi import Depends, FastAPI

from api.store import Media, query_allsides, query_media, query_mediabiasfactcheck
from api.tools.youtube import Video, search_youtube_channel
from lib.auth import verify_apikey

app = FastAPI()


@app.get("/allsides", response_model=List[Dict[str, str]])
def search_allsides(
    name: str,
    limit: int = 5,
    offset: int = 0,
    _: None = Depends(verify_apikey),
) -> List[Dict[str, str]]:
    results = query_allsides(name, limit, offset)
    return results[offset:]


@app.get("/mediabiasfactcheck", response_model=List[Dict[str, str]])
def search_mediabiasfactcheck(
    name: str,
    limit: int = 5,
    offset: int = 0,
    _: None = Depends(verify_apikey),
) -> List[Dict[str, str]]:
    results = query_mediabiasfactcheck(name, limit, offset)
    return results[offset:]


@app.get("/media", response_model=List[Media])
async def search_media(
    query: str,
    limit: int = 5,
    offset: int = 0,
    _: None = Depends(verify_apikey),
) -> List[Media]:
    results = await query_media(query, top_k=limit + offset)
    return results[offset:]


@app.get("/youtube", response_model=List[Video])
async def search_youtube(
    query: str,
    period_days: int = 1,
    max_channels: int = 8,
    max_videos_per_channel: int = 3,
    _: None = Depends(verify_apikey),
) -> List[Video]:
    media = await query_media(query, top_k=max_channels * 2)
    tmp = {}
    for item in media:
        if not "Youtube" in item or item["Youtube"] == "n/a":
            continue
        ret = search_youtube_channel(
            item["Youtube"], query, period_days, max_videos_per_channel
        )
        if len(ret) > 0:
            tmp[item["Name"]] = ret
        if len(tmp.keys()) >= max_channels:
            break
    ret = []
    for item in tmp.values():
        ret.extend(item)
    print("Number of videos found: " + str(len(ret)))
    return ret


@app.get("/privacy")
async def read_privacy() -> str:
    return "You are ok"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8088)
