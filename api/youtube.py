import asyncio
import json
import time
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Union

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


class Transcript(BaseModel):
    """Transcript model"""

    text: str
    start: int
    duration: int


class VideoTranscript(BaseModel):
    """Video transcript model"""

    id: str
    text: str


class Video(BaseModel):
    """Video model"""

    id: str
    # thumbnails: List[str]
    title: str
    short_desc: str
    channel: str
    duration: str
    views: str
    publish_time: str
    url_suffix: str
    long_desc: Optional[str] = None
    transcript: Optional[str] = None


def _parse_html_list(html: str, max_results: int) -> List[Video]:
    results: List[Video] = []
    if not "ytInitialData" in html:
        return []
    start = html.index("ytInitialData") + len("ytInitialData") + 3
    end = html.index("};", start) + 1
    json_str = html[start:end]
    data = json.loads(json_str)
    if not "twoColumnBrowseResultsRenderer" in data["contents"]:
        return []
    tab = None
    for tab in data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"]:
        if "expandableTabRenderer" in tab.keys():
            break
    if tab is None:
        return []
    for contents in tab["expandableTabRenderer"]["content"]["sectionListRenderer"][
        "contents"
    ]:
        if "itemSectionRenderer" in contents:
            for video in contents["itemSectionRenderer"]["contents"]:
                if not "videoRenderer" in video.keys():
                    continue

                res: Dict[str, Union[str, List[str], int, None]] = {}
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
                    "simpleText", ""
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


def _parse_html_video(html: str) -> Dict[str, str]:
    result: Dict[str, str] = {"long_desc": None}
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
    except:
        pass
    return result


# cache results for one hour
@async_threadsafe_ttl_cache(ttl=3600)
async def youtube_search(
    channels: str,
    end_date: str,
    query: Optional[str] = None,
    period_days: int = 3,
    max_videos_per_channel: int = 3,
    get_descriptions: bool = False,
    get_transcripts: bool = True,
    char_cap: Optional[int] = None,
) -> List[Video]:
    channels_arr = _fix_channels(
        ["@" + channel.replace("@", "") for channel in channels.lower().split(",")]
    )
    [year, month, day] = get_since_date(period_days, end_date)
    query_str = f"{query} " if query else ""
    before = f'{" " if query else ""}before:{end_date} ' if end_date else ""
    encoded_search = urllib.parse.quote_plus(
        f"{query_str}{before}after:{year}-{month}-{day}"
    )
    tasks = []
    if len(channels_arr) == 0:
        return []
    try:
        for channel in channels_arr:
            if channel == "n/a":
                continue
            url = (
                f"https://www.youtube.com/{channel}/search?hl=en&query={encoded_search}"
            )
            tasks.append(
                _get_channel_videos(
                    channel=channel,
                    url=url,
                    max_videos_per_channel=max_videos_per_channel,
                    get_descriptions=get_descriptions,
                    get_transcripts=get_transcripts,
                )
            )
        results = await asyncio.gather(*tasks)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise e

    res: List[Video] = []
    for videos in results:
        # a given query results in relevance sort, which is nice, but if no query was given we sort by publish time
        if not query:
            videos.sort(key=sort_by_publish_time)
            videos = videos[::-1]
        res.extend(videos)
    print("Number of videos found: " + str(len(res)))
    if char_cap:
        res = filter_by_char_cap(res, char_cap)
    return res


def filter_by_char_cap(videos: List[Video], char_cap: int) -> List[Video]:
    while len(json.dumps([vid.model_dump_json() for vid in videos])) > char_cap:
        transcript_lengths = [len(video.transcript) for video in videos]
        max_index = transcript_lengths.index(max(transcript_lengths))
        videos.pop(max_index)
    return videos


def sort_by_publish_time(video: Video) -> float:
    now = datetime.now()
    d = dateparser.parse(
        video.publish_time.replace("Streamed ", ""), settings={"RELATIVE_BASE": now}
    )
    return time.mktime(d.timetuple())


@cache(ttl=3600)
def youtube_transcripts(
    ids: str,
) -> List[VideoTranscript]:
    """
    Extract transcripts from a list of Youtube video ids
    """
    results: List[VideoTranscript] = []
    for video_id in ids.split(","):
        transcript = _get_video_transcript(video_id, strip_timestamps=True)
        results.append(VideoTranscript(id=video_id, text=transcript))
    return results


def _fix_channels(channels: List[str]) -> List[str]:
    data = get_data()
    fixed_channels = []
    for channel_raw in channels:
        channel = channel_raw.replace("@", "")
        # look up as partial match in our db
        found = next((item for item in data if channel in item["Youtube"]), None)
        if found:
            fixed_channels.append(found["Youtube"])
        # we always append, even if we did not correct it (which might throw a 400 later)
        else:
            fixed_channels.append(channel_raw)
    return fixed_channels


async def _get_channel_videos(
    channel: str,
    url: str,
    max_videos_per_channel: int,
    get_descriptions: bool,
    get_transcripts: bool,
) -> List[Video]:
    # cookie to bypass consent, as found here:
    # https://stackoverflow.com/questions/74127649/is-there-a-way-to-skip-youtubes-before-you-continue-to-youtube-cookies-messag
    async with ClientSession() as session:
        response = await session.get(
            url, headers={"Cookie": "SOCS=CAESEwgDEgk0ODE3Nzk3MjQaAmVuIAEaBgiA_LyaBg"}
        )
        if response.status != 200:
            raise HTTPException(
                status_code=400,
                detail=f'Failed to fetch videos for channel "{channel}. The handle is probably incorrect."',
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


async def _get_video_info(session: ClientSession, video_id: str) -> Dict[str, str]:
    url = f"https://www.youtube.com/watch?v={video_id}"
    response = await session.get(
        url, headers={"Cookie": "SOCS=CAESEwgDEgk0ODE3Nzk3MjQaAmVuIAEaBgiA_LyaBg"}
    )
    html = await response.text()
    result = _parse_html_video(html)
    return result


def _get_video_transcript(video_id: str, strip_timestamps: bool = False) -> str:
    try:
        transcripts = YouTubeTranscriptApi.get_transcript(
            video_id, preserve_formatting=True
        )
        transcript = " ".join(
            [
                (
                    str(t["start"]).split(".")[0] + "s" + ": " + t["text"]
                    if not strip_timestamps
                    else t["text"]
                )
                for t in transcripts
            ]
        )
        return transcript
    except:
        return ""
