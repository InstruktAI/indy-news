from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from api.youtube import (
    Video,
    _filter_by_char_cap,
    _filter_channels,
    _get_video_info,
    _get_video_transcript,
    _parse_html_list,
    _parse_html_video,
    _sort_by_publish_time,
    youtube_search,
    youtube_transcripts,
)


@pytest.fixture
def mock_video_html() -> str:
    """Fixture to provide sample video HTML"""
    return """
    {
        "contents": {
            "twoColumnBrowseResultsRenderer": {
                "tabs": [{
                    "expandableTabRenderer": {
                        "content": {
                            "sectionListRenderer": {
                                "contents": [{
                                    "itemSectionRenderer": {
                                        "contents": [{
                                            "videoRenderer": {
                                                "videoId": "test_id",
                                                "title": {"runs": [{"text": "Test Video"}]},
                                                "descriptionSnippet": {"runs": [{"text": "Test Description"}]},
                                                "longBylineText": {"runs": [{"text": "Test Channel"}]},
                                                "lengthText": {"simpleText": "10:00"},
                                                "viewCountText": {"simpleText": "1000 views"},
                                                "publishedTimeText": {"simpleText": "1 day ago"}
                                            }
                                        }]
                                    }
                                }]
                            }
                        }
                    }
                }]
            }
        }
    }
    """


@pytest.fixture
def mock_video_search_html() -> str:
    """Fixture to provide sample video search HTML"""
    return """<html><script>var ytInitialData = {
        "contents": {
            "twoColumnBrowseResultsRenderer": {
                "tabs": [{
                    "tabRenderer": {
                        "content": {
                            "sectionListRenderer": {
                                "contents": [{
                                    "itemSectionRenderer": {
                                        "contents": [{
                                            "videoRenderer": {
                                                "videoId": "test_id",
                                                "title": {"runs": [{"text": "Test Video"}]},
                                                "descriptionSnippet": {"runs": [{"text": "Test Description"}]},
                                                "longBylineText": {"runs": [{"text": "Test Channel"}]},
                                                "lengthText": {"simpleText": "10:00"},
                                                "viewCountText": {"simpleText": "1000 views"},
                                                "publishedTimeText": {"simpleText": "1 day ago"},
                                                "navigationEndpoint": {
                                                    "commandMetadata": {
                                                        "webCommandMetadata": {
                                                            "url": "/watch?v=test_id"
                                                        }
                                                    }
                                                }
                                            }
                                        }]
                                    }
                                }]
                            }
                        }
                    }
                }]
            }
        }
    };</script></html>"""


class TestParsingFunctions:
    """Tests for HTML parsing functions"""

    def test_parse_html_list(self) -> None:
        """Test _parse_html_list function"""
        mock_html = """<html><script>var ytInitialData = {
            "contents": {
                "twoColumnBrowseResultsRenderer": {
                    "tabs": [{
                        "expandableTabRenderer": {
                            "content": {
                                "sectionListRenderer": {
                                    "contents": [{
                                        "itemSectionRenderer": {
                                            "contents": [{
                                                "videoRenderer": {
                                                    "videoId": "test_id",
                                                    "title": {"runs": [{"text": "Test Video"}]},
                                                    "descriptionSnippet": {"runs": [{"text": "Test Description"}]},
                                                    "longBylineText": {"runs": [{"text": "Test Channel"}]},
                                                    "lengthText": {"simpleText": "10:00"},
                                                    "viewCountText": {"simpleText": "1000 views"},
                                                    "publishedTimeText": {"simpleText": "1 day ago"},
                                                    "navigationEndpoint": {
                                                        "commandMetadata": {
                                                            "webCommandMetadata": {
                                                                "url": "/watch?v=test_id"
                                                            }
                                                        }
                                                    }
                                                }
                                            }]
                                        }
                                    }]
                                }
                            }
                        }
                    }]
                }
            }
        };</script></html>"""
        videos = _parse_html_list(mock_html, 1)
        assert len(videos) == 1
        assert videos[0].id == "test_id"
        assert videos[0].title == "Test Video"

    def test_parse_html_video(self) -> None:
        """Test _parse_html_video function"""
        mock_html = """<html><script>var ytInitialData = {
            "contents": {
                "twoColumnWatchNextResults": {
                    "results": {
                        "results": {
                            "contents": [
                                {},
                                {
                                    "videoSecondaryInfoRenderer": {
                                        "attributedDescription": {
                                            "content": "Test long description"
                                        }
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        };</script></html>"""
        result = _parse_html_video(mock_html)
        assert result["long_desc"] == "Test long description"


@pytest.mark.asyncio
class TestYoutubeSearch:
    """Tests for YouTube search functionality"""

    @patch("api.youtube._parse_html_list")
    async def test_youtube_search_with_channels(self, mock_parse_html_list) -> None:
        """Test youtube_search when channels are provided"""
        # Mock the parser to return a video directly
        mock_video = Video(
            id="test_id",
            title="Test Video",
            short_desc="Test Description",
            channel="Test Channel",
            duration="10:00",
            views="1000 views",
            publish_time="1 day ago",
            url_suffix="/watch?v=test_id",
        )
        mock_parse_html_list.return_value = [mock_video]

        with patch("api.youtube._filter_channels", return_value=["@testchannel"]):
            with patch("aiohttp.ClientSession") as mock_session:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.text = AsyncMock(return_value="mock_html")
                mock_session.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_response
                )
                mock_session.return_value.__aexit__ = AsyncMock()

                result = await youtube_search(
                    channels="@testchannel",
                    query="test",
                    period_days=3,
                    end_date="2024-01-01",
                    max_videos_per_channel=2,
                    get_descriptions=False,
                    get_transcripts=False,
                )

                assert len(result) == 1
                assert result[0].id == "test_id"

    @patch("api.youtube._parse_html_list")
    async def test_youtube_search_with_end_date(self, mock_parse_html_list) -> None:
        """Test youtube_search with end_date parameter"""
        # Mock the parser to return a video directly
        mock_video = Video(
            id="test_id",
            title="Test Video",
            short_desc="Test Description",
            channel="Test Channel",
            duration="10:00",
            views="1000 views",
            publish_time="1 day ago",
            url_suffix="/watch?v=test_id",
        )
        mock_parse_html_list.return_value = [mock_video]

        with patch("api.youtube._filter_channels", return_value=["@testchannel"]):
            with patch("aiohttp.ClientSession") as mock_session:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.text = AsyncMock(return_value="mock_html")
                mock_session.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_response
                )
                mock_session.return_value.__aexit__ = AsyncMock()

                result = await youtube_search(
                    channels="@testchannel",
                    query="test",
                    period_days=3,
                    end_date="2024-01-01",
                    max_videos_per_channel=2,
                    get_descriptions=False,
                    get_transcripts=False,
                )

                assert len(result) == 1
                assert result[0].id == "test_id"

    @patch("api.youtube._parse_html_list")
    async def test_youtube_search_multiple_channels(self, mock_parse_html_list) -> None:
        """Test youtube_search with multiple channels"""
        # Mock the parser to return a video directly
        mock_video = Video(
            id="test_id",
            title="Test Video",
            short_desc="Test Description",
            channel="Test Channel",
            duration="10:00",
            views="1000 views",
            publish_time="1 day ago",
            url_suffix="/watch?v=test_id",
        )
        mock_parse_html_list.return_value = [mock_video]

        with patch(
            "api.youtube._filter_channels",
            return_value=["@testchannel1", "@testchannel2"],
        ):
            with patch("aiohttp.ClientSession") as mock_session:
                mock_response1 = AsyncMock()
                mock_response1.status = 200
                mock_response1.text = AsyncMock(return_value="mock_html")

                mock_response2 = AsyncMock()
                mock_response2.status = 200
                mock_response2.text = AsyncMock(return_value="mock_html")

                mock_session.return_value.__aenter__.return_value.get = AsyncMock(
                    side_effect=[mock_response1, mock_response2]
                )
                mock_session.return_value.__aexit__ = AsyncMock()

                result = await youtube_search(
                    channels="@testchannel1,@testchannel2",
                    end_date="2024-01-01",
                    query="test",
                    period_days=3,
                    max_videos_per_channel=1,
                    get_descriptions=False,
                    get_transcripts=False,
                )

                assert len(result) == 2  # One from each channel
                assert result[0].id == "test_id"
                assert result[1].id == "test_id"

    async def test_youtube_search_http_error(self) -> None:
        """Test youtube_search when HTTP request fails"""
        with patch("api.youtube._filter_channels", return_value=["@testchannel"]):
            with patch("aiohttp.ClientSession") as mock_session:
                mock_response = AsyncMock()
                mock_response.status = 404
                mock_session.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_response
                )
                mock_session.return_value.__aexit__ = AsyncMock()

                # Mock the HTTPException being raised
                with patch("api.youtube._get_channel_videos") as mock_get_videos:
                    mock_get_videos.side_effect = HTTPException(
                        status_code=400,
                        detail='Failed to fetch videos for channel "@testchannel". The handle is probably incorrect.',
                    )

                    with pytest.raises(HTTPException) as exc_info:
                        await youtube_search(
                            channels="@testchannel",
                            end_date="2024-01-01",
                            query="test",
                            period_days=3,
                            get_descriptions=False,
                            get_transcripts=False,
                        )

                    assert exc_info.value.status_code == 400
                    assert "Failed to fetch videos for channel" in str(
                        exc_info.value.detail
                    )

    async def test_video_transcript_retrieval(self) -> None:
        """Test video transcript retrieval"""
        with patch(
            "youtube_transcript_api.YouTubeTranscriptApi.get_transcript"
        ) as mock_get_transcript:
            mock_get_transcript.return_value = [
                {"text": "Test transcript", "start": 0.0, "duration": 5.0}
            ]
            transcript = _get_video_transcript("test_id")
            assert "Test transcript" in transcript

    async def test_filter_by_char_cap_edge_cases(self) -> None:
        """Test character cap filtering with edge cases"""
        # Empty list
        assert len(_filter_by_char_cap([], 100)) == 0

        # Single video under cap
        videos = [
            Video(
                id="1",
                title="Test",
                short_desc="Desc",
                channel="Channel",
                duration="1:00",
                views="100",
                publish_time="1 day ago",
                url_suffix="/watch?v=1",
                transcript="Short",
            )
        ]
        assert len(_filter_by_char_cap(videos, 1000)) == 1

    async def test_sort_by_publish_time_edge_cases(self) -> None:
        """Test publish time sorting with edge cases"""
        # Test with different time formats
        video1 = Video(
            id="1",
            title="Test",
            short_desc="Desc",
            channel="Channel",
            duration="1:00",
            views="100",
            publish_time="1 day ago",
            url_suffix="/watch?v=1",
        )
        video2 = Video(
            id="2",
            title="Test",
            short_desc="Desc",
            channel="Channel",
            duration="1:00",
            views="100",
            publish_time="2 days ago",
            url_suffix="/watch?v=2",
        )

        # More recent video should have a higher timestamp
        time1 = _sort_by_publish_time(video1)
        time2 = _sort_by_publish_time(video2)
        assert time1 > time2, "More recent video should have a higher timestamp"

    async def test_youtube_transcripts(self) -> None:
        """Test youtube_transcripts function for multiple videos"""
        with patch(
            "youtube_transcript_api.YouTubeTranscriptApi.get_transcript"
        ) as mock_get_transcript:
            mock_get_transcript.return_value = [
                {"text": "Test transcript", "start": 0.0, "duration": 5.0}
            ]
            results = youtube_transcripts("video1,video2")
            assert len(results) == 2
            assert results[0].id == "video1"
            assert results[1].id == "video2"
            assert "Test transcript" in results[0].text
            assert "Test transcript" in results[1].text

    async def test_filter_channels(self) -> None:
        """Test _filter_channels function"""
        with patch("api.youtube.get_data") as mock_get_data:
            mock_get_data.return_value = [
                {"Youtube": "@channel1"},
                {"Youtube": "@channel2"},
            ]
            channels = _filter_channels(["@channel1", "channel2"])
            assert len(channels) == 2
            assert "@channel1" in channels
            assert "@channel2" in channels

    async def test_get_video_transcript_error(self) -> None:
        """Test error handling in _get_video_transcript"""
        with patch(
            "youtube_transcript_api.YouTubeTranscriptApi.get_transcript",
            side_effect=Exception("Transcript not available"),
        ):
            transcript = _get_video_transcript("test_id")
            assert transcript == ""

    async def test_get_video_info(self) -> None:
        """Test _get_video_info function"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value="""
            <html><script>var ytInitialData = {
                "contents": {
                    "twoColumnWatchNextResults": {
                        "results": {
                            "results": {
                                "contents": [
                                    {},
                                    {
                                        "videoSecondaryInfoRenderer": {
                                            "attributedDescription": {
                                                "content": "Test video info"
                                            }
                                        }
                                    }
                                ]
                            }
                        }
                    }
                }
            };</script></html>
        """
        )

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response)

        result = await _get_video_info(mock_session, "test_id")
        assert result["long_desc"] == "Test video info"

    async def test_youtube_search_no_query(self) -> None:
        """Test youtube search when no query is provided (sort by publish time)"""
        with patch("api.youtube._filter_channels", return_value=["@testchannel"]):
            with patch("aiohttp.ClientSession") as mock_session:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.text = AsyncMock(return_value="mock_html")
                mock_session.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_response
                )
                mock_session.return_value.__aexit__ = AsyncMock()

                with patch("api.youtube._parse_html_list") as mock_parse:
                    mock_parse.return_value = [
                        Video(
                            id="1",
                            title="Old Video",
                            short_desc="Test",
                            channel="Test",
                            duration="10:00",
                            views="100",
                            publish_time="2 days ago",
                            url_suffix="/watch?v=1",
                        ),
                        Video(
                            id="2",
                            title="New Video",
                            short_desc="Test",
                            channel="Test",
                            duration="10:00",
                            views="100",
                            publish_time="1 day ago",
                            url_suffix="/watch?v=2",
                        ),
                    ]

                    result = await youtube_search(
                        channels="@testchannel",
                        end_date="2024-01-01",
                        query=None,
                        period_days=3,
                        max_videos_per_channel=2,
                        get_descriptions=False,
                        get_transcripts=False,
                    )

                    assert len(result) == 2
                    assert result[0].id == "2"  # Newer video should be first
                    assert result[1].id == "1"  # Older video should be second

    async def test_youtube_search_empty_channels(self) -> None:
        """Test youtube search with empty channels string"""
        with pytest.raises(ValueError) as exc_info:
            await youtube_search(
                channels="",
                end_date="2024-01-01",
                query="test",
                period_days=3,
                get_descriptions=False,
                get_transcripts=False,
            )
        assert str(exc_info.value) == "No channels specified"

    async def test_youtube_search_with_char_cap(self) -> None:
        """Test youtube search with character cap"""
        with patch("api.youtube._filter_channels", return_value=["@testchannel"]):
            with patch("aiohttp.ClientSession") as mock_session:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.text = AsyncMock(return_value="mock_html")
                mock_session.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_response
                )
                mock_session.return_value.__aexit__ = AsyncMock()

                with patch("api.youtube._parse_html_list") as mock_parse:
                    mock_parse.return_value = [
                        Video(
                            id="1",
                            title="Video 1",
                            short_desc="Test",
                            channel="Test",
                            duration="10:00",
                            views="100",
                            publish_time="1 day ago",
                            url_suffix="/watch?v=1",
                        ),
                        Video(
                            id="2",
                            title="Video 2",
                            short_desc="Test",
                            channel="Test",
                            duration="10:00",
                            views="100",
                            publish_time="1 day ago",
                            url_suffix="/watch?v=2",
                        ),
                    ]

                    with patch("api.youtube._get_video_transcript") as mock_transcript:
                        mock_transcript.side_effect = [
                            "Long transcript " * 100,  # First video - long transcript
                            "Short transcript",  # Second video - short transcript
                        ]

                        result = await youtube_search(
                            channels="@testchannel",
                            end_date="2024-01-01",
                            query="test",
                            period_days=3,
                            max_videos_per_channel=2,
                            get_descriptions=False,
                            get_transcripts=True,
                            char_cap=1000,
                        )

                        assert (
                            len(result) == 1
                        )  # Only the video with short transcript should remain
                        assert result[0].id == "2"
