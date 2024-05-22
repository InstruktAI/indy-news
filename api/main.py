from typing import Dict, List

from fastapi import Depends, FastAPI, HTTPException

from api.store import (
    Media,
    get_data,
    query_allsides,
    query_media,
    query_mediabiasfactcheck,
)
from api.tools.youtube import Video, youtube_search, youtube_transcripts
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


@app.get("/media-videos", response_model=List[Video])
async def get_youtube_search(
    channels: str = None,
    query: str = None,
    period_days: int = 3,
    max_channels: int = 8,
    max_videos_per_channel: int = 3,
    get_descriptions: bool = False,
    get_transcripts: bool = False,
    _: None = Depends(verify_apikey),
) -> List[Video]:
    if not (channels or query):
        raise HTTPException(
            status_code=400, detail="No query given when no channels are provided!"
        )
    return await youtube_search(
        channels=channels,
        query=query,
        period_days=period_days,
        max_channels=max_channels,
        max_videos_per_channel=max_videos_per_channel,
        get_descriptions=get_descriptions,
        get_transcripts=get_transcripts,
    )


@app.get("/youtube-transcripts", response_model=Dict[str, str])
async def get_youtube_transcripts(
    ids: str,
    _: None = Depends(verify_apikey),
) -> Dict[str, str]:
    return youtube_transcripts(ids)


@app.get("/privacy")
async def read_privacy() -> str:
    return "You are ok"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8088)
