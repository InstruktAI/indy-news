from typing import Dict, List

from fastapi import Depends, FastAPI, HTTPException

from api.store import (
    Media,
    get_data,
    query_allsides,
    query_media,
    query_mediabiasfactcheck,
)
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
    query: str = "",
    period_days: int = 3,
    max_channels: int = 8,
    max_videos_per_channel: int = 3,
    channels: str = None,
    get_descriptions: bool = False,
    get_transcripts: bool = False,
    _: None = Depends(verify_apikey),
) -> List[Video]:
    tmp: Dict[str, List[Video]] = {}
    if channels:
        channels_arr = channels.lower().split(",")
        media = [
            item
            for item in get_data()
            if item["Youtube"].lower().replace("https://www.youtube.com/", "")
            in channels_arr
        ]
    else:
        if query == "":
            raise HTTPException(
                status_code=400, detail="No query given when no channels are provided!"
            )
        media = await query_media(query, top_k=max_channels * 2)
    for item in media:
        if item["Youtube"] == "n/a":
            continue
        ret = search_youtube_channel(
            item["Youtube"],
            query,
            period_days,
            max_videos_per_channel,
            get_descriptions,
            get_transcripts,
        )
        if len(ret) > 0:
            if len(ret) > max_videos_per_channel:
                tmp[item["Name"]] = ret[:max_videos_per_channel]
            else:
                tmp[item["Name"]] = ret
        if len(tmp.keys()) >= max_channels:
            break
    res: List[Video] = []
    for videos in tmp.values():
        res.extend(videos)
    print("Number of videos found: " + str(len(res)))
    return res


@app.get("/privacy")
async def read_privacy() -> str:
    return "You are ok"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8088)
