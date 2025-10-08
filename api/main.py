import logging
import os
from os import getenv
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel

from api.store import (
    Source,
    SourceMedia,
    SourceMinimal,
    get_data,
)
from api.substack import SubstackPost, substack_search
from api.x import Tweet, x_search
from api.youtube import Video, VideoTranscript, youtube_search, youtube_transcripts
from lib.auth import verify_apikey

logging.basicConfig(level=getenv("LOG_LEVEL", "INFO").upper())

app = FastAPI()


class WebhookPayload(BaseModel):
    """Payload sent to webhook URL upon completion."""

    success: bool
    cookies: str | None = None
    error: str | None = None
    iterations: int | None = None
    request_id: str | None = None


@app.get("/media")
def search_media(
    names: str,
    _: Annotated[None, Depends(verify_apikey)],
) -> list[Source]:
    """Search the curated independent media sources database for a partial name."""
    data = get_data()
    results = []
    for name in names.split(","):
        for item in data:
            if name == item["Name"]:
                results.append(Source(**item))
    return results


@app.get("/sources")
def get_all_sources(
    _: Annotated[None, Depends(verify_apikey)],
) -> list[SourceMinimal]:
    """Returns a list of all sources.

    Used as input for AI to determine which sources to select for certain topics.
    """
    data = get_data()
    sources: list[SourceMinimal] = []
    for _i, item in enumerate(data):
        sources.append(
            SourceMinimal(
                Name=item["Name"],
                About=item["About"],
                Topics=item["Topics"],
            ),
        )
    return sources


@app.get("/source-media")
def get_source_media(
    sources: Annotated[
        str | None,
        Query(
            title="Comma separated list of source names",
            description="Source names to get Youtube channel and X handles for",
            min_length=1,
            examples=["Al Jazeera,Democracy Now"],
        ),
    ] = None,
    _: None = Depends(verify_apikey),
) -> list[SourceMedia]:
    """Returns a list of sources' Youtube channel and X handles. Used as input for AI to query for videos and tweets."""
    data = get_data()
    selected_sources: list[SourceMedia] = []
    for _i, item in enumerate(data):
        if sources and item["Name"] not in sources:
            continue
        selected_sources.append(
            SourceMedia(
                Name=item["Name"],
                Youtube=item["Youtube"] if item["Youtube"] != "n/a" else None,
                X=item["X"] if item["X"] != "n/a" else None,
                Substack=item["Substack"] if item["Substack"] != "n/a" else None,
            ),
        )
    return selected_sources


def get_column_values(
    name: Annotated[
        str | None,
        Query(
            title="Name of column",
            min_length=3,
            examples=["Youtube"],
        ),
    ] = None,
    _: None = Depends(verify_apikey),
) -> list[str]:
    """Returns a list of sources' Youtube channel and X handles. Used as input for AI to query for videos and tweets."""
    data = get_data()
    values = []
    for _i, item in enumerate(data):
        for key, value in item.items():
            if key.lower() == name.lower():
                values.append(value)
    return values


@app.get("/source-names")
def get_source_names(
    _: Annotated[None, Depends(verify_apikey)],
) -> list[str]:
    """Returns a list of source names."""
    return get_column_values("Name")


@app.get("/youtube-channels")
def get_youtube_channels(
    _: Annotated[None, Depends(verify_apikey)],
) -> list[str]:
    """Returns a list of sources' Youtube channels."""
    return get_column_values("Youtube")


@app.get("/x-users")
def get_x_users(
    _: Annotated[None, Depends(verify_apikey)],
) -> list[str]:
    """Returns a list of sources' X user handles."""
    return get_column_values("X")


@app.get("/substack-publications")
def get_substack_publications(
    _: Annotated[None, Depends(verify_apikey)],
) -> list[str]:
    """Returns a list of sources' Substack publication names."""
    return get_column_values("Substack")


@app.get("/youtube")
async def get_youtube_search(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    query: Annotated[
        str | None,
        Query(
            title="Query string",
            description="Search query to match independent news channels",
            min_length=3,
            examples=["israel"],
        ),
    ] = None,
    channels: Annotated[
        str | None,
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
        str | None,
        Query(
            title="End date",
            description="End date in Y-m-d format (subtracts period_days from this)",
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
        int | None,
        Query(
            title="Max chars in the response",
            description="The maximum number of characters for the response.",
        ),
    ] = None,
    _: None = Depends(verify_apikey),
) -> list[Video]:
    """Find Youtube videos by either providing channels, a query, or both."""
    if not (channels or query):
        raise HTTPException(
            status_code=400,
            detail='Either one of "query" or "channels" must be provided!',
        )
    return await youtube_search(
        channels=channels,
        query=query,
        period_days=period_days,
        end_date=end_date,
        max_videos_per_channel=max_videos_per_channel,
        get_descriptions=get_descriptions,
        get_transcripts=get_transcripts,
        char_cap=char_cap,
    )


@app.get("/x")
async def get_x_search(
    query: Annotated[
        str | None,
        Query(
            title="Query string",
            description="Query string used to match independent news users and do an X tweet search.",
            min_length=3,
            examples=["israel"],
        ),
    ] = None,
    users: Annotated[
        str | None,
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
        str | None,
        Query(
            title="End date",
            description="End date in Y-m-d format (subtracts period_days from this)",
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
) -> list[Tweet]:
    """Find tweets on X by either providing users, a query, or both."""
    if not (users or query):
        raise HTTPException(
            status_code=400,
            detail='Either one of "query" or "users" must be provided!',
        )
    return await x_search(
        query=query,
        users=users,
        period_days=period_days,
        end_date=end_date,
        max_tweets_per_user=max_tweets_per_user,
    )


@app.get("/substack")
async def get_substack_search(
    query: Annotated[
        str | None,
        Query(
            title="Query string",
            description="Query string used to search Substack publications.",
            min_length=3,
            examples=["ukraine"],
        ),
    ] = None,
    publications: Annotated[
        str | None,
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
) -> list[SubstackPost]:
    """Find free posts on Substack by either providing publications, a query, or both.
    Returns posts with plain text content (converted from HTML).
    """
    if not (publications or query):
        raise HTTPException(
            status_code=400,
            detail='Either one of "query" or "publications" must be provided!',
        )
    return await substack_search(
        publications=publications,
        query=query,
        max_posts_per_publication=max_posts_per_publication,
        get_content=get_content,
    )


@app.get("/news", response_model=list[Video | Tweet])
async def get_news_search(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    query: Annotated[
        str | None,
        Query(
            title="Query string",
            description="Search query to match independent news channels",
            min_length=3,
            examples=["israel"],
        ),
    ] = None,
    channels: Annotated[
        str | None,
        Query(
            title="Channels to search in",
            description="A string of comma-separated Youtube channels to search in.",
            examples=["@aljazeeraenglish,@DemocracyNow"],
        ),
    ] = None,
    users: Annotated[
        str | None,
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
        str | None,
        Query(
            title="End date",
            description="End date in Y-m-d format (subtracts period_days from this)",
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
        int | None,
        Query(
            title="Max chars in the response",
            description="The maximum number of characters for the response.",
        ),
    ] = None,
    _: None = Depends(verify_apikey),
) -> list[Video | Tweet]:
    """Find both Youtube videos and X tweets by either providing channels or users, and potentially a query."""
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


@app.get("/youtube-transcripts")
def get_youtube_transcripts(
    ids: str,
    _: Annotated[None, Depends(verify_apikey)],
) -> list[VideoTranscript]:
    """Extract transcripts from a list of Youtube video ids."""
    return youtube_transcripts(ids)


@app.post("/webhook/cookies")
async def receive_cookies(
    payload: WebhookPayload,
    _: Annotated[None, Depends(verify_apikey)],
) -> dict[str, str]:
    """Webhook endpoint to receive cookie updates from external playwright service.
    Creates a new timestamped cookie file and removes previous ones.
    """
    if not payload.success or not payload.cookies:
        raise HTTPException(
            status_code=400,
            detail=f"Cookie refresh failed: {payload.error}",
        )

    cookies_dir = Path(os.getenv("CACHE", "cache"))
    cookies_file = cookies_dir / "cookies.txt"

    with open(cookies_file, "w", encoding="utf-8") as f:
        f.write(payload.cookies)

    return {"status": "ok"}


@app.get("/privacy")
async def read_privacy() -> str:
    return "You are ok"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8088)
