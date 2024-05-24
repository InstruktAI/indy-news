from typing import Annotated, Dict, List, Optional, Union

from fastapi import Depends, FastAPI, HTTPException, Query

from api.store import Media, query_allsides, query_media, query_mediabiasfactcheck
from api.youtube import Video, VideoTranscript, youtube_search, youtube_transcripts
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
    query: Annotated[
        str,
        Query(
            title="Query string",
            description="Query string used to match independent news channels and do a youtube search with in those channels.",
            min_length=3,
            example="israel",
        ),
    ] = None,
    channels: Annotated[
        str,
        Query(
            title="Channels to search in",
            description="A string of comma-separated Youtube channels to search in.",
            example="@aljazeeraenglish,@DemocracyNow",
        ),
    ] = None,
    period_days: Annotated[
        int,
        Query(
            title="Period in days",
            description="The period in days since now that we want to search videos for.",
        ),
    ] = 3,
    max_channels: Annotated[
        int,
        Query(
            title="Max channels",
            description="Maximum number of channels that we want to match. Needed when no channels were provided.",
        ),
    ] = 12,
    max_videos_per_channel: Annotated[
        int,
        Query(
            title="Max videos per channel",
            description="The maximum number of videos per channel that we want from each channel search.",
        ),
    ] = 3,
    get_descriptions: Annotated[
        bool,
        Query(
            title="Get descriptions",
            description="Get the long descriptions for the videos.",
        ),
    ] = False,
    get_transcripts: Annotated[
        bool,
        Query(
            title="Get transcripts",
            description="Get the transcripts for the videos.",
        ),
    ] = True,
    _: None = Depends(verify_apikey),
) -> List[Video]:
    """
    Get the details of matching videos by either providing Youtube channels, a query, or both
    """
    if not (channels or query):
        raise HTTPException(
            status_code=400,
            detail='Either one of "query" or "channels" must be provided!',
        )
    if not channels:
        if not max_channels:
            raise HTTPException(
                status_code=400,
                detail='"max_channels" must be provided when no "channels" are set!',
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


@app.get("/youtube-transcripts", response_model=List[VideoTranscript])
async def get_youtube_transcripts(
    ids: str,
    _: None = Depends(verify_apikey),
) -> Dict[str, str]:
    """
    Extract transcripts from a list of Youtube video ids
    """
    return youtube_transcripts(ids)


@app.get("/privacy")
async def read_privacy() -> str:
    return "You are ok"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8088)
