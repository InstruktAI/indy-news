"""
Unit tests for YouTube business logic.
Tests actual algorithmic functions, not YouTube API or BeautifulSoup.
"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from api.youtube import Video, _filter_by_char_cap, _sort_by_publish_time


class TestSortByPublishTime:
    """Test publish time parsing logic - converts relative times to timestamps"""

    def test_hours_ago(self):
        """Test parsing 'X hours ago'"""
        video = Video(
            id="1",
            title="Test",
            short_desc="Test",
            channel="Test",
            duration="10:00",
            views="100",
            publish_time="2 hours ago",
            url_suffix="/watch?v=1",
        )
        timestamp = _sort_by_publish_time(video)
        # Should be approximately 2 hours ago
        expected = (datetime.now() - timedelta(hours=2)).timestamp()
        assert abs(timestamp - expected) < 3600  # Within 1 hour tolerance

    def test_days_ago(self):
        """Test parsing 'X days ago'"""
        video = Video(
            id="1",
            title="Test",
            short_desc="Test",
            channel="Test",
            duration="10:00",
            views="100",
            publish_time="5 days ago",
            url_suffix="/watch?v=1",
        )
        timestamp = _sort_by_publish_time(video)
        expected = (datetime.now() - timedelta(days=5)).timestamp()
        assert abs(timestamp - expected) < 86400  # Within 1 day tolerance

    def test_weeks_ago(self):
        """Test parsing 'X weeks ago'"""
        video = Video(
            id="1",
            title="Test",
            short_desc="Test",
            channel="Test",
            duration="10:00",
            views="100",
            publish_time="3 weeks ago",
            url_suffix="/watch?v=1",
        )
        timestamp = _sort_by_publish_time(video)
        expected = (datetime.now() - timedelta(weeks=3)).timestamp()
        assert abs(timestamp - expected) < 86400 * 2  # Within 2 days tolerance

    def test_months_ago(self):
        """Test parsing 'X months ago'"""
        video = Video(
            id="1",
            title="Test",
            short_desc="Test",
            channel="Test",
            duration="10:00",
            views="100",
            publish_time="2 months ago",
            url_suffix="/watch?v=1",
        )
        timestamp = _sort_by_publish_time(video)
        expected = (datetime.now() - timedelta(days=60)).timestamp()
        # Months are approximate, allow larger tolerance
        assert abs(timestamp - expected) < 86400 * 7  # Within 1 week

    def test_sorting_order(self):
        """Test that more recent videos have higher timestamps"""
        recent = Video(
            id="1",
            title="Test",
            short_desc="Test",
            channel="Test",
            duration="10:00",
            views="100",
            publish_time="1 day ago",
            url_suffix="/watch?v=1",
        )
        older = Video(
            id="2",
            title="Test",
            short_desc="Test",
            channel="Test",
            duration="10:00",
            views="100",
            publish_time="5 days ago",
            url_suffix="/watch?v=2",
        )
        assert _sort_by_publish_time(recent) > _sort_by_publish_time(older)


class TestFilterByCharCap:
    """Test character cap logic - truncates results to fit within char limit"""

    def test_empty_list(self):
        """Test with empty video list"""
        result = _filter_by_char_cap([], 1000)
        assert result == []

    def test_no_cap(self):
        """Test with None cap returns all videos"""
        videos = [
            Video(
                id="1",
                title="Test",
                short_desc="Test",
                channel="Test",
                duration="10:00",
                views="100",
                publish_time="1 day ago",
                url_suffix="/watch?v=1",
                transcript="Short transcript",
            )
        ]
        result = _filter_by_char_cap(videos, None)
        assert len(result) == 1

    def test_under_cap(self):
        """Test all videos fit under cap"""
        videos = [
            Video(
                id="1",
                title="Test",
                short_desc="Desc",
                channel="Ch",
                duration="10:00",
                views="100",
                publish_time="1 day ago",
                url_suffix="/watch?v=1",
                transcript="Short",
            ),
            Video(
                id="2",
                title="Test2",
                short_desc="Desc2",
                channel="Ch",
                duration="10:00",
                views="100",
                publish_time="1 day ago",
                url_suffix="/watch?v=2",
                transcript="Short",
            ),
        ]
        result = _filter_by_char_cap(videos, 10000)
        assert len(result) == 2

    def test_truncates_to_fit(self):
        """Test truncation when videos exceed cap"""
        videos = [
            Video(
                id="1",
                title="Test",
                short_desc="Desc",
                channel="Ch",
                duration="10:00",
                views="100",
                publish_time="1 day ago",
                url_suffix="/watch?v=1",
                transcript="x" * 500,  # 500 chars
            ),
            Video(
                id="2",
                title="Test2",
                short_desc="Desc2",
                channel="Ch",
                duration="10:00",
                views="100",
                publish_time="1 day ago",
                url_suffix="/watch?v=2",
                transcript="y" * 500,  # 500 chars
            ),
            Video(
                id="3",
                title="Test3",
                short_desc="Desc3",
                channel="Ch",
                duration="10:00",
                views="100",
                publish_time="1 day ago",
                url_suffix="/watch?v=3",
                transcript="z" * 500,  # 500 chars
            ),
        ]
        # Cap allows roughly 2 videos
        result = _filter_by_char_cap(videos, 1200)
        # Should truncate to fit within cap
        assert len(result) < 3
        assert len(result) >= 1

    def test_character_counting(self):
        """Test that character counting includes all fields"""
        video = Video(
            id="123",
            title="Title",
            short_desc="Description",
            channel="Channel",
            duration="10:00",
            views="1000",
            publish_time="1 day ago",
            url_suffix="/watch?v=123",
            transcript="Transcript text",
        )
        videos = [video]
        # Tight cap should exclude the video
        result = _filter_by_char_cap(videos, 10)
        assert len(result) == 0

    def test_preserves_order(self):
        """Test that filtering preserves original order"""
        videos = [
            Video(
                id=str(i),
                title=f"Test{i}",
                short_desc="Desc",
                channel="Ch",
                duration="10:00",
                views="100",
                publish_time="1 day ago",
                url_suffix=f"/watch?v={i}",
                transcript="x" * 100,
            )
            for i in range(5)
        ]
        result = _filter_by_char_cap(videos, 1000)
        # Check IDs are in order
        for i in range(len(result) - 1):
            assert int(result[i].id) < int(result[i + 1].id)
