import asyncio
import json
import time
import urllib.parse
from collections import namedtuple
from typing import Dict, List, Union

import requests
from aiohttp import ClientSession
from fastapi import HTTPException
from munch import munchify
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromiumService
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager, DriverManager
from webdriver_manager.core.os_manager import ChromeType
from youtube_transcript_api import YouTubeTranscriptApi

from api.store import get_data, query_media
from lib.cache import async_threadsafe_ttl_cache
from lib.cache import sync_threadsafe_ttl_cache as cache

options: Options = Options()
options.add_argument("--headless")


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
    short_desc: Union[str, None] = None
    channel: str
    channel_url: Union[str, None] = None
    duration: Union[str, int]
    views: Union[str, int]
    publish_time: Union[str, int]
    url_suffix: str
    long_desc: Union[str, None] = None
    transcript: Union[str, None] = None


def _parse_html_list(html: str, max_results: int) -> List[Video]:
    results: List[Video] = []
    start = html.index("ytInitialData") + len("ytInitialData") + 3
    end = html.index("};", start) + 1
    json_str = html[start:end]
    data = json.loads(json_str)
    tab = None
    for tab in data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"]:
        if "expandableTabRenderer" in tab.keys():
            break
    if tab is None:
        return results
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
                    video_data.get("title", {}).get("runs", [[{}]])[0].get("text", None)
                )
                res["short_desc"] = (
                    video_data.get("descriptionSnippet", {})
                    .get("runs", [{}])[0]
                    .get("text", None)
                )
                res["channel"] = (
                    video_data.get("longBylineText", {})
                    .get("runs", [[{}]])[0]
                    .get("text", None)
                )
                res["duration"] = video_data.get("lengthText", {}).get("simpleText", 0)
                res["views"] = video_data.get("viewCountText", {}).get("simpleText", 0)
                res["publish_time"] = video_data.get("publishedTimeText", {}).get(
                    "simpleText", 0
                )
                res["url_suffix"] = (
                    video_data.get("navigationEndpoint", {})
                    .get("commandMetadata", {})
                    .get("webCommandMetadata", {})
                    .get("url", None)
                )
                results.append(Video(**res))
                if len(results) >= int(max_results):
                    break
        if len(results) >= int(max_results):
            break

    return results


def _parse_html_video(html: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    start = html.index("ytInitialData") + len("ytInitialData") + 3
    end = html.index("};", start) + 1
    json_str = html[start:end]
    data = json.loads(json_str)
    obj = munchify(data)
    result["long_desc"] = (
        obj.contents.twoColumnWatchNextResults.results.results.contents[
            1
        ].videoSecondaryInfoRenderer.attributedDescription.content
    )
    return result


# @async_threadsafe_ttl_cache(ttl=3600)
async def youtube_search(
    channels: str,
    period_days: int,
    max_channels: int,
    max_videos_per_channel: int,
    query: str = "",
    get_descriptions: bool = False,
    get_transcripts: bool = False,
) -> List[Video]:
    if channels:
        channels_arr = channels.lower().split(",")
        media = [
            item
            for item in get_data()
            if item["Youtube"].lower().replace("https://www.youtube.com/", "")
            in channels_arr
        ]
    else:
        media = await query_media(query, top_k=max_channels * 2)

    # calculate day and month from today minus period_days:
    today = time.time()
    period = int(period_days) * 24 * 3600
    start = today - period
    day = time.strftime("%d", time.localtime(start)).zfill(2)
    month = time.strftime("%m", time.localtime(start)).zfill(2)
    year = time.strftime("%Y", time.localtime(start))
    encoded_search = urllib.parse.quote_plus(f"{query} after:{year}-{month}-{day}")
    tasks = []
    for item in media:
        channel_url = item["Youtube"]
        if channel_url == "n/a":
            continue
        url = f"{channel_url}/search?hl=en&query={encoded_search}"
        tasks.append(
            _get_channel_videos(
                url,
                max_videos_per_channel,
                channel_url,
                get_descriptions,
                get_transcripts,
            )
        )
    results = await asyncio.gather(*tasks)
    res: List[Video] = []
    for videos in results:
        res.extend(videos)
    print("Number of videos found: " + str(len(res)))
    return res


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


async def _get_channel_videos(
    url: str,
    max_videos_per_channel: int,
    channel: str,
    get_descriptions: bool,
    get_transcripts: bool,
) -> List[Video]:
    # cookie to bypass consent, as found here:
    # https://stackoverflow.com/questions/74127649/is-there-a-way-to-skip-youtubes-before-you-continue-to-youtube-cookies-messag
    async with ClientSession() as session:
        response = await session.get(
            url, headers={"Cookie": "SOCS=CAESEwgDEgk0ODE3Nzk3MjQaAmVuIAEaBgiA_LyaBg"}
        )
        html = await response.text()
        videos = _parse_html_list(html, max_results=max_videos_per_channel)
        channel_url = f"https://www.youtube.com/{channel}"
        for video in videos:
            video.channel_url = channel_url
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
