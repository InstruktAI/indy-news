import logging
from os import getenv
from typing import Annotated, Dict, List

from fastapi import Depends, FastAPI, HTTPException, Query

from api.store import (
    Source,
    SourceMedia,
    SourceMinimal,
    get_data,
    query_allsides,
    query_mediabiasfactcheck,
)
from api.substack import SubstackPost, substack_search
from api.x import Tweet, x_search
from api.youtube import Video, VideoTranscript, youtube_search, youtube_transcripts
from lib.auth import verify_apikey

logging.basicConfig(level=getenv("LOG_LEVEL", "INFO").upper())

app = FastAPI()


@app.get("/allsides", response_model=List[Dict[str, str]])
def search_allsides(
    name: str,
    limit: int = 5,
    offset: int = 0,
    _: None = Depends(verify_apikey),
) -> List[Dict[str, str]]:
    """Search the AllSides database for a partial name"""
    results = query_allsides(name, limit, offset)
    return results[offset:]


@app.get("/mediabiasfactcheck", response_model=List[Dict[str, str]])
def search_mediabiasfactcheck(
    name: str,
    limit: int = 5,
    offset: int = 0,
    _: None = Depends(verify_apikey),
) -> List[Dict[str, str]]:
    """Search the MediaBiasFactCheck database for a partial name"""
    results = query_mediabiasfactcheck(name, limit, offset)
    return results[offset:]


@app.get("/media", response_model=List[Source])
def search_media(
    names: str,
    _: None = Depends(verify_apikey),
) -> List[Source]:
    """Search the curated independent media sources database for a partial name"""
    data = get_data()
    results = []
    for name in names.split(","):
        for item in data:
            if name == item["Name"]:
                results.append(Source(**item))
    return results


@app.get("/sources", response_model=List[SourceMinimal])
def get_all_sources(
    _: None = Depends(verify_apikey),
) -> List[SourceMinimal]:
    """Returns a list of all sources. Used as input for AI to determine which sources to select for certain topics (it knows these names and what topics those sources report on)."""
    data = get_data()
    sources: List[SourceMinimal] = []
    for _i, item in enumerate(data):
        sources.append(
            SourceMinimal(
                Name=item["Name"],
                About=item["About"],
                Topics=item["Topics"],
            )
        )
    return sources


@app.get("/source-media", response_model=List[SourceMedia])
def get_source_media(
    sources: Annotated[
        str,
        Query(
            title="Comma separated list of source names",
            description="Comma separated list of source names to get Youtube channel and X handles for",
            min_length=1,
            examples=["Al Jazeera,Democracy Now"],
        ),
    ] = None,
    _: None = Depends(verify_apikey),
) -> List[SourceMedia]:
    """Returns a list of sources' Youtube channel and X handles. Used as input for AI to query for videos and tweets."""
    data = get_data()
    selected_sources: List[SourceMedia] = []
    for _i, item in enumerate(data):
        if sources and item["Name"] not in sources:
            continue
        selected_sources.append(
            SourceMedia(
                Name=item["Name"],
                Youtube=item["Youtube"] if item["Youtube"] != "n/a" else None,
                X=item["X"] if item["X"] != "n/a" else None,
                Substack=item["Substack"] if item["Substack"] != "n/a" else None,
            )
        )
    return selected_sources


def get_column_values(
    name: Annotated[
        str,
        Query(
            title="Name of column",
            min_length=3,
            examples=["Youtube"],
        ),
    ] = None,
    _: None = Depends(verify_apikey),
) -> List[str]:
    """Returns a list of sources' Youtube channel and X handles. Used as input for AI to query for videos and tweets."""
    data = get_data()
    values = []
    for _i, item in enumerate(data):
        for key, value in item.items():
            if key.lower() == name.lower():
                values.append(value)
    return values


@app.get("/source-names", response_model=List[str])
def get_source_names(
    _: None = Depends(verify_apikey),
) -> List[str]:
    """Returns a list of source names."""
    return get_column_values("Name")


@app.get("/youtube-channels", response_model=List[str])
def get_youtube_channels(
    _: None = Depends(verify_apikey),
) -> List[str]:
    """Returns a list of sources' Youtube channels."""
    return get_column_values("Youtube")


@app.get("/youtube", response_model=List[Video])
async def get_youtube_search(
    query: Annotated[
        str,
        Query(
            title="Query string",
            description="Query string used to match independent news channels and do a youtube search with in those channels.",
            min_length=3,
            examples=["israel"],
        ),
    ] = None,
    channels: Annotated[
        str,
        Query(
            title="Channels to search in",
            description="A string of comma-separated Youtube channels to search in.",
            examples=["@aljazeeraenglish,@DemocracyNow"],
        ),
    ] = None,
    period_days: Annotated[
        int,
        Query(
            title="Period in days",
            description="The period in days before (now|end_date) that we want to search videos for.",
        ),
    ] = 3,
    end_date: Annotated[
        str,
        Query(
            title="End date",
            description="The end day in Y-m-d format. Subtracts the period_days to determine the period that we want to search videos for.",
        ),
    ] = None,
    max_videos_per_channel: Annotated[
        int,
        Query(
            title="Max videos per channel",
            description="The maximum number of videos per channel that we want from each channel search.",
        ),
    ] = 2,
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
    char_cap: Annotated[
        int,
        Query(
            title="Max chars in the response",
            description="The maximum number of characters for the response.",
        ),
    ] = None,
    _: None = Depends(verify_apikey),
) -> List[Video]:
    """
    Find Youtube videos by either providing channels, a query, or both
    """
    if not (channels or query):
        raise HTTPException(
            status_code=400,
            detail='Either one of "query" or "channels" must be provided!',
        )
    results = await youtube_search(
        channels=channels,
        query=query,
        period_days=period_days,
        end_date=end_date,
        max_videos_per_channel=max_videos_per_channel,
        get_descriptions=get_descriptions,
        get_transcripts=get_transcripts,
        char_cap=char_cap,
    )
    return results


@app.get("/x", response_model=List[Tweet])
async def get_x_search(
    query: Annotated[
        str,
        Query(
            title="Query string",
            description="Query string used to match independent news users and do an X tweet search.",
            min_length=3,
            examples=["israel"],
        ),
    ] = None,
    users: Annotated[
        str,
        Query(
            title="Users to search in",
            description="A string of comma-separated X users to search in.",
            examples=["AJenglish,democracynow"],
        ),
    ] = None,
    period_days: Annotated[
        int,
        Query(
            title="Period in days",
            description="The period in days since now that we want to search tweets for.",
        ),
    ] = 3,
    end_date: Annotated[
        str,
        Query(
            title="End date",
            description="The end day in Y-m-d format. Subtracts the period_days to determine the period that we want to search videos for.",
        ),
    ] = None,
    max_tweets_per_user: Annotated[
        int,
        Query(
            title="Max tweets per user",
            description="The maximum number of tweets per user that we want from the search.",
        ),
    ] = 20,
    _: None = Depends(verify_apikey),
) -> List[Tweet]:
    """
    Find tweets on X by either providing users, a query, or both
    """
    if not (users or query):
        raise HTTPException(
            status_code=400,
            detail='Either one of "query" or "users" must be provided!',
        )
    results = await x_search(
        query=query,
        users=users,
        period_days=period_days,
        end_date=end_date,
        max_tweets_per_user=max_tweets_per_user,
    )
    return results


@app.get("/substack", response_model=List[SubstackPost])
async def get_substack_search(
    query: Annotated[
        str,
        Query(
            title="Query string",
            description="Query string used to search Substack publications.",
            min_length=3,
            examples=["ukraine"],
        ),
    ] = None,
    publications: Annotated[
        str,
        Query(
            title="Publications to search in",
            description="A string of comma-separated Substack publication names to search in.",
            examples=["greenwald,taibbi,matgyver"],
        ),
    ] = None,
    max_posts_per_publication: Annotated[
        int,
        Query(
            title="Max posts per publication",
            description="The maximum number of posts per publication that we want from the search.",
        ),
    ] = 10,
    get_content: Annotated[
        bool,
        Query(
            title="Get content",
            description="Whether to fetch the full content of posts as plain text (slower but includes body text).",
        ),
    ] = True,
    _: None = Depends(verify_apikey),
) -> List[SubstackPost]:
    """
    Find free posts on Substack by either providing publications, a query, or both.
    Returns posts with plain text content (converted from HTML).
    """
    if not (publications or query):
        raise HTTPException(
            status_code=400,
            detail='Either one of "query" or "publications" must be provided!',
        )
    results = await substack_search(
        publications=publications,
        query=query,
        max_posts_per_publication=max_posts_per_publication,
        get_content=get_content,
    )
    return results


@app.get("/news", response_model=List[Video | Tweet])
async def get_news_search(
    query: Annotated[
        str,
        Query(
            title="Query string",
            description="Query string used to match independent news channels and do a youtube search with in those channels.",
            min_length=3,
            examples=["israel"],
        ),
    ] = None,
    channels: Annotated[
        str,
        Query(
            title="Channels to search in",
            description="A string of comma-separated Youtube channels to search in.",
            examples=["@aljazeeraenglish,@DemocracyNow"],
        ),
    ] = None,
    users: Annotated[
        str,
        Query(
            title="Users to search in",
            description="A string of comma-separated X users to search in.",
            examples=["AJenglish,democracynow"],
        ),
    ] = None,
    period_days: Annotated[
        int,
        Query(
            title="Period in days",
            description="The period in days before (now|end_date) that we want to search videos for.",
        ),
    ] = 7,
    end_date: Annotated[
        str,
        Query(
            title="End date",
            description="The end day in Y-m-d format. Subtracts the period_days to determine the period that we want to search videos for.",
        ),
    ] = None,
    max_videos_per_channel: Annotated[
        int,
        Query(
            title="Max videos per channel",
            description="The maximum number of videos per channel that we want from each channel search.",
        ),
    ] = 2,
    max_tweets_per_user: Annotated[
        int,
        Query(
            title="Max tweets per user",
            description="The maximum number of tweets per user that we want from the search.",
        ),
    ] = 20,
    char_cap: Annotated[
        int,
        Query(
            title="Max chars in the response",
            description="The maximum number of characters for the response.",
        ),
    ] = None,
    _: None = Depends(verify_apikey),
) -> List[Video | Tweet]:
    """
    Find both Youtube videos and X tweets by either providing channels or users, and potentially a query.
    """
    if not (channels or users):
        raise HTTPException(
            status_code=400,
            detail='Either one of "channels" or "users" must be provided!',
        )
    tweets = (
        await x_search(
            query=query,
            users=users,
            period_days=period_days,
            end_date=end_date,
            max_tweets_per_user=max_tweets_per_user,
        )
        if (users)
        else []
    )
    if tweets and char_cap is not None:
        char_cap -= len((",").join([f"{tweet}" for tweet in tweets]))
    videos = (
        await youtube_search(
            channels=channels,
            query=query,
            period_days=period_days,
            end_date=end_date,
            max_videos_per_channel=max_videos_per_channel,
            get_descriptions=False,
            get_transcripts=False,
            char_cap=char_cap,
        )
        if (channels)
        else []
    )

    return tweets + videos


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8088)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8088)
