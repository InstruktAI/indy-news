"""
Unit tests for X/Twitter business logic.
Tests actual algorithmic functions, not twikit library.
"""
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from api.x import _filter_users, _max_per_user


class TestFilterUsers:
    """Test user handle filtering logic"""

    def test_filters_valid_users(self):
        """Test returns only users present in source data"""
        mock_data = [
            {"X": "user1"},
            {"X": "user2"},
            {"X": "user3"},
        ]
        with patch("api.x.get_data", return_value=mock_data):
            result = _filter_users(["user1", "user2", "unknown"])
            assert len(result) == 2
            assert "user1" in result
            assert "user2" in result
            assert "unknown" not in result

    def test_excludes_na_values(self):
        """Test filters out 'n/a' values from source data"""
        mock_data = [
            {"X": "user1"},
            {"X": "n/a"},
            {"X": "user2"},
        ]
        with patch("api.x.get_data", return_value=mock_data):
            result = _filter_users(["user1", "n/a", "user2"])
            assert len(result) == 2
            assert "user1" in result
            assert "user2" in result
            assert "n/a" not in result

    def test_empty_input(self):
        """Test with empty user list"""
        mock_data = [{"X": "user1"}]
        with patch("api.x.get_data", return_value=mock_data):
            result = _filter_users([])
            assert result == []

    def test_no_matches(self):
        """Test when no users match source data"""
        mock_data = [{"X": "user1"}, {"X": "user2"}]
        with patch("api.x.get_data", return_value=mock_data):
            result = _filter_users(["user3", "user4"])
            assert result == []


class TestMaxPerUser:
    """Test per-user tweet limiting logic"""

    def test_limits_tweets_per_user(self):
        """Test enforces max tweets per user"""
        tweets = []
        # Create 10 tweets from user1, 5 from user2
        for i in range(10):
            tweet = MagicMock()
            tweet.user = MagicMock()
            tweet.user.id = "user1"
            tweets.append(tweet)
        for i in range(5):
            tweet = MagicMock()
            tweet.user = MagicMock()
            tweet.user.id = "user2"
            tweets.append(tweet)

        result = _max_per_user(tweets, max_tweets_per_user=3)

        # Should have 3 from user1, 3 from user2
        assert len(result) == 6
        user1_count = sum(1 for t in result if t.user.id == "user1")
        user2_count = sum(1 for t in result if t.user.id == "user2")
        assert user1_count == 3
        assert user2_count == 3

    def test_preserves_order(self):
        """Test that limiting preserves original tweet order"""
        tweets = []
        for i in range(5):
            tweet = MagicMock()
            tweet.user = MagicMock()
            tweet.user.id = "user1"
            tweet.id = f"tweet_{i}"
            tweets.append(tweet)

        result = _max_per_user(tweets, max_tweets_per_user=3)

        # First 3 should be preserved in order
        assert result[0].id == "tweet_0"
        assert result[1].id == "tweet_1"
        assert result[2].id == "tweet_2"

    def test_empty_list(self):
        """Test with empty tweet list"""
        result = _max_per_user([], max_tweets_per_user=5)
        assert result == []

    def test_under_limit(self):
        """Test when all users have fewer tweets than limit"""
        tweets = []
        for i in range(2):
            tweet = MagicMock()
            tweet.user = MagicMock()
            tweet.user.id = f"user{i}"
            tweets.append(tweet)

        result = _max_per_user(tweets, max_tweets_per_user=5)
        assert len(result) == 2

    def test_single_user(self):
        """Test with tweets from single user"""
        tweets = []
        for i in range(10):
            tweet = MagicMock()
            tweet.user = MagicMock()
            tweet.user.id = "user1"
            tweets.append(tweet)

        result = _max_per_user(tweets, max_tweets_per_user=4)
        assert len(result) == 4
        assert all(t.user.id == "user1" for t in result)

    def test_multiple_users_uneven_distribution(self):
        """Test with uneven tweet distribution across users"""
        tweets = []
        # user1: 8 tweets
        for i in range(8):
            tweet = MagicMock()
            tweet.user = MagicMock()
            tweet.user.id = "user1"
            tweets.append(tweet)
        # user2: 2 tweets
        for i in range(2):
            tweet = MagicMock()
            tweet.user = MagicMock()
            tweet.user.id = "user2"
            tweets.append(tweet)
        # user3: 5 tweets
        for i in range(5):
            tweet = MagicMock()
            tweet.user = MagicMock()
            tweet.user.id = "user3"
            tweets.append(tweet)

        result = _max_per_user(tweets, max_tweets_per_user=3)

        # Should have 3+2+3 = 8 total (user2 had only 2)
        assert len(result) == 8
        user1_count = sum(1 for t in result if t.user.id == "user1")
        user2_count = sum(1 for t in result if t.user.id == "user2")
        user3_count = sum(1 for t in result if t.user.id == "user3")
        assert user1_count == 3
        assert user2_count == 2
        assert user3_count == 3
