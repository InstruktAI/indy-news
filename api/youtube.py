import asyncio
import json
import logging
import time
import urllib.parse
from collections.abc import Coroutine
from datetime import datetime
from typing import Any

import dateparser
from aiohttp import ClientSession
from fastapi import HTTPException
from munch import munchify
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi

from api.store import get_data
from lib.cache import async_threadsafe_ttl_cache
from lib.cache import sync_threadsafe_ttl_cache as cache
from lib.utils import get_since_date

logger = logging.getLogger(__name__)


class Transcript(BaseModel):
    """Transcript model."""

    text: str
    start: int
    duration: int


class VideoTranscript(BaseModel):
    """Video transcript model."""

    id: str
    text: str


class Video(BaseModel):
    """Video model."""

    id: str
    # thumbnails: List[str]
    title: str
    short_desc: str
    channel: str
    duration: str
    views: str
    publish_time: str
    url_suffix: str
    long_desc: str | None = None
    transcript: str | None = None


def _parse_html_list(html: str, max_results: int) -> list[Video]:
    results: list[Video] = []
    if "ytInitialData" not in html:
        return []
    start = html.index("ytInitialData") + len("ytInitialData") + 3
    end = html.index("};", start) + 1
    json_str = html[start:end]
    data = json.loads(json_str)
    if "twoColumnBrowseResultsRenderer" not in data["contents"]:
        return []
    tab = None
    for tab in data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"]:
        if "expandableTabRenderer" in tab:
            break
    if tab is None:
        return []
    for contents in tab["expandableTabRenderer"]["content"]["sectionListRenderer"][
        "contents"
    ]:
        if "itemSectionRenderer" in contents:
            for video in contents["itemSectionRenderer"]["contents"]:
                if "videoRenderer" not in video:
                    continue

                res: dict[str, str | list[str] | int | None] = {}
                video_data = video.get("videoRenderer", {})
                res["id"] = video_data.get("videoId", None)
                # res["thumbnails"] = [
                #     thumb.get("url", None)
                #     for thumb in video_data.get("thumbnail", {}).get("thumbnails", [{}])
                # ]
                res["title"] = (
                    video_data.get("title", {}).get("runs", [[{}]])[0].get("text", "")
                )
                res["short_desc"] = (
                    video_data.get("descriptionSnippet", {})
                    .get("runs", [{}])[0]
                    .get("text", "")
                )
                res["channel"] = (
                    video_data.get("longBylineText", {})
                    .get("runs", [[{}]])[0]
                    .get("text", None)
                )
                res["duration"] = video_data.get("lengthText", {}).get("simpleText", "")
                res["views"] = video_data.get("viewCountText", {}).get("simpleText", "")
                res["publish_time"] = video_data.get("publishedTimeText", {}).get(
                    "simpleText",
                    "",
                )
                res["url_suffix"] = (
                    video_data.get("navigationEndpoint", {})
                    .get("commandMetadata", {})
                    .get("webCommandMetadata", {})
                    .get("url", "")
                )
                results.append(Video(**res))
                if len(results) >= int(max_results):
                    break
        if len(results) >= int(max_results):
            break

    return results


def _parse_html_video(html: str) -> dict[str, str]:
    result: dict[str, str] = {"long_desc": None}
    start = html.index("ytInitialData") + len("ytInitialData") + 3
    end = html.index("};", start) + 1
    json_str = html[start:end]
    data = json.loads(json_str)
    obj = munchify(data)
    try:
        result["long_desc"] = (
            obj.contents.twoColumnWatchNextResults.results.results.contents[
                1
            ].videoSecondaryInfoRenderer.attributedDescription.content
        )
    except (AttributeError, KeyError, IndexError, TypeError):
        logger.warning(
            "YouTube HTML structure changed, could not extract long description"
        )
    return result


def _build_youtube_search_url(
    query: str | None, period_days: int, end_date: str
) -> str:
    """Build YouTube search query URL."""
    [year, month, day] = get_since_date(period_days, end_date)
    query_str = f"{query} " if query else ""
    before = f"{' ' if query else ''}before:{end_date} " if end_date else ""
    return urllib.parse.quote_plus(f"{query_str}{before}after:{year}-{month}-{day}")


def _create_channel_tasks(
    channels_arr: list[str],
    encoded_search: str,
    max_videos_per_channel: int,
    get_descriptions: bool,
    get_transcripts: bool,
) -> list[Coroutine[Any, Any, list[Video]]]:
    """Create async tasks for fetching videos from each channel."""
    tasks = []
    for channel in channels_arr:
        if channel == "n/a":
            continue
        url = f"https://www.youtube.com/{channel}/search?hl=en&query={encoded_search}"
        tasks.append(
            _get_channel_videos(
                channel=channel,
                url=url,
                max_videos_per_channel=max_videos_per_channel,
                get_descriptions=get_descriptions,
                get_transcripts=get_transcripts,
            )
        )
    return tasks


def _process_video_results(
    results: list[list[Video]], query: str | None, char_cap: int | None
) -> list[Video]:
    """Process and sort video results."""
    res: list[Video] = []
    for videos in results:
        if not query:
            videos.sort(key=_sort_by_publish_time)
            videos = videos[::-1]
        res.extend(videos)
    if char_cap:
        res = _filter_by_char_cap(res, char_cap)
    return res


# cache results for one hour
@async_threadsafe_ttl_cache(ttl=3600)
async def youtube_search(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    channels: str,
    end_date: str,
    query: str | None = None,
    period_days: int = 3,
    max_videos_per_channel: int = 3,
    get_descriptions: bool = False,
    get_transcripts: bool = True,
    char_cap: int | None = None,
) -> list[Video]:
    if not channels:
        raise ValueError("No channels specified")

    channels_arr = _filter_channels(
        ["@" + channel.replace("@", "") for channel in channels.lower().split(",")]
    )
    if len(channels_arr) == 0:
        return []

    logger.debug(
        f"Searching for videos on channels: {channels_arr}, query: {query}, "
        f"period_days: {period_days}, end_date: {end_date}, "
        f"max_videos_per_channel: {max_videos_per_channel}, "
        f"get_descriptions: {get_descriptions}, get_transcripts: {get_transcripts}, char_cap: {char_cap}"
    )

    encoded_search = _build_youtube_search_url(query, period_days, end_date)
    tasks = _create_channel_tasks(
        channels_arr,
        encoded_search,
        max_videos_per_channel,
        get_descriptions,
        get_transcripts,
    )

    try:
        results = await asyncio.gather(*tasks)
    except HTTPException as e:
        logger.exception(e)
        raise
    except Exception as e:
        logger.exception(e)
        raise

    return _process_video_results(results, query, char_cap)


def _filter_by_char_cap(videos: list[Video], char_cap: int) -> list[Video]:
    if char_cap is None:
        return videos
    while len(json.dumps([vid.model_dump_json() for vid in videos])) > char_cap:
        transcript_lengths = [len(video.transcript) for video in videos]
        max_index = transcript_lengths.index(max(transcript_lengths))
        videos.pop(max_index)
    return videos


def _sort_by_publish_time(video: Video) -> float:
    now = datetime.now()
    d = dateparser.parse(
        video.publish_time.replace("Streamed ", ""),
        settings={"RELATIVE_BASE": now},
    )
    return time.mktime(d.timetuple())


@cache(ttl=3600)
def youtube_transcripts(
    ids: str,
) -> list[VideoTranscript]:
    """Extract transcripts from a list of Youtube video ids."""
    results: list[VideoTranscript] = []
    for video_id in ids.split(","):
        transcript = _get_video_transcript(video_id)
        results.append(VideoTranscript(id=video_id, text=transcript))
    return results


def _filter_channels(channels: list[str]) -> list[str]:
    data = get_data()
    fixed_channels = []
    for channel_raw in channels:
        channel = channel_raw.replace("@", "")
        # look up as partial match in our db
        found = next((item for item in data if channel in item["Youtube"]), None)
        if found and found["Youtube"] and found["Youtube"].lower() != "n/a":
            fixed_channels.append(found["Youtube"])
    return fixed_channels


async def _get_channel_videos(
    channel: str,
    url: str,
    max_videos_per_channel: int,
    get_descriptions: bool,
    get_transcripts: bool,
) -> list[Video]:
    # cookie to bypass consent, as found here:
    # https://stackoverflow.com/questions/74127649/is-there-a-way-to-skip-youtubes-before-you-continue-to-youtube-cookies-messag
    async with ClientSession() as session:
        response = await session.get(
            url,
            headers={"Cookie": "SOCS=CAESEwgDEgk0ODE3Nzk3MjQaAmVuIAEaBgiA_LyaBg"},
        )
        if response.status != 200:
            raise HTTPException(
                status_code=400,
                detail=f'Failed to fetch videos for channel "{channel}". The handle is probably incorrect.',
            )
        html = await response.text()
        videos = _parse_html_list(html, max_results=max_videos_per_channel)
        for video in videos:
            if get_descriptions:
                video_info = await _get_video_info(session, video.id)
                video.long_desc = video_info.get("long_desc")
            if get_transcripts:
                transcript = _get_video_transcript(video.id)
                video.transcript = transcript
        return videos


async def _get_video_info(session: ClientSession, video_id: str) -> dict[str, str]:
    url = f"https://www.youtube.com/watch?v={video_id}"
    response = await session.get(
        url,
        headers={"Cookie": "SOCS=CAESEwgDEgk0ODE3Nzk3MjQaAmVuIAEaBgiA_LyaBg"},
    )
    html = await response.text()
    return _parse_html_video(html)


def _get_video_transcript(video_id: str, strip_timestamps: bool = False) -> str:
    ytt_api = YouTubeTranscriptApi()
    try:
        transcripts = ytt_api.fetch(video_id, preserve_formatting=True)
        return " ".join(
            [
                (
                    "[" + str(t["start"]).split(".", maxsplit=1)[0] + "s] " + t["text"]
                    if not strip_timestamps
                    else t["text"]
                )
                for t in transcripts.to_raw_data()
            ],
        )
    except (KeyError, AttributeError, ValueError, ConnectionError, TimeoutError):
        return ""
