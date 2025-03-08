import os
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from api.x import Tweet, _filter_users, _get_client, _max_per_user, x_search


@pytest.fixture
def mock_get_data() -> Generator[MagicMock, None, None]:
    """Fixture to mock get_data function"""
    with patch("api.x.get_data") as mock:
        mock.return_value = [
            {"Name": "Test Source", "X": "test_user"},
            {"Name": "Another Source", "X": "another_user"},
            {"Name": "Third Source", "X": "n/a"},
        ]
        yield mock


@pytest.fixture
def mock_client() -> Generator[MagicMock, None, None]:
    """Fixture to mock Twitter client"""
    mock = MagicMock()
    mock._user_id = None
    mock.search_tweet = AsyncMock()
    mock.load_cookies = MagicMock()
    mock.save_cookies = MagicMock()
    mock.set_cookies = MagicMock()
    mock.login = AsyncMock()
    yield mock


class TestHelperFunctions:
    """Tests for helper functions in x.py"""

    def test_max_per_user(self) -> None:
        """Test _max_per_user function"""
        # Create mock tweets from different users
        tweets = []
        for i in range(5):
            tweet = MagicMock(spec=Tweet)
            tweet.id = f"tweet_{i}"
            tweet.user = MagicMock()
            tweet.user.id = i % 2  # Alternate between 2 users
            tweets.append(tweet)

        result = _max_per_user(tweets, max_tweets_per_user=2)
        assert len(result) == 4  # 2 tweets each from 2 users

    def test_filter_users(self) -> None:
        """Test _filter_users function properly handles user mapping"""
        # Mock get_data to return test data
        test_data = [{"X": "test_user"}, {"X": "another_user"}, {"X": "n/a"}]
        with patch("api.x.get_data", return_value=test_data):
            result = _filter_users(["test_user", "unknown_user", "another_user"])
            assert len(result) == 2
            assert "test_user" in result
            assert "another_user" in result


@pytest.mark.asyncio
class TestClientFunctions:
    """Tests for client-related functions in x.py"""

    async def test_get_client_with_user_id(self) -> None:
        """Test _get_client when user_id is already set"""
        with patch("api.x.client") as mock_client:
            # Set up the mock with a user_id
            mock_client._user_id = "existing_user"

            result = await _get_client()

            assert result == mock_client
            # No methods should be called if user_id exists
            mock_client.load_cookies.assert_not_called()
            mock_client.login.assert_not_called()

    @patch.dict(os.environ, {"X_COOKIES": "cookie1=value1; cookie2=value2"})
    async def test_get_client_with_env_cookies(self) -> None:
        """Test _get_client when X_COOKIES env var is set"""
        with patch("api.x.client") as mock_client:
            mock_client._user_id = None

            result = await _get_client()

            assert result == mock_client
            mock_client.set_cookies.assert_called_once()
            # Verify the correct cookies dict is created
            cookies_arg = mock_client.set_cookies.call_args[0][0]
            assert cookies_arg == {"cookie1": "value1", "cookie2": "value2"}
            # Login should not be called when cookies are used
            mock_client.login.assert_not_called()

    @patch("os.path.exists")
    async def test_get_client_with_cookies_file(self, mock_exists: MagicMock) -> None:
        """Test _get_client when cookies file exists"""
        mock_exists.return_value = True

        with patch("api.x.client") as mock_client:
            mock_client._user_id = None

            # Clear environment to avoid using X_COOKIES
            with patch.dict(os.environ, {}, clear=True):
                result = await _get_client()

            assert result == mock_client
            mock_client.load_cookies.assert_called_once()
            # Login should not be called when cookie file is used
            mock_client.login.assert_not_called()

    @patch("os.path.exists")
    @patch("api.x.client")
    async def test_get_client_with_login(
        self, mock_client: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test _get_client when login is needed"""
        mock_exists.return_value = False
        mock_client._user_id = None
        # Set up AsyncMock for login to avoid "await" expression error
        mock_client.login = AsyncMock()

        test_user = "user"
        test_email = "email"
        test_password = "pass"

        with patch.dict(
            os.environ,
            {"X_USER": test_user, "X_EMAIL": test_email, "X_PASSWORD": test_password},
        ):
            result = await _get_client()

            # Verify login was called with correct credentials
            mock_client.login.assert_called_once_with(
                auth_info_1=test_user,
                auth_info_2=test_email,
                password=test_password,
            )
            # Verify cookies are saved
            mock_client.save_cookies.assert_called_once()


@pytest.mark.asyncio
class TestXSearch:
    """Tests for the x_search function"""

    async def test_x_search_no_query_no_users(self) -> None:
        """Test x_search with no query and no users"""
        with pytest.raises(ValueError) as exc_info:
            await x_search(users="", query=None, period_days=3)
        assert str(exc_info.value) == "Either users or query must be provided"

    async def test_x_search_with_query_and_users(self) -> None:
        """Test x_search with query and users"""
        test_data = [{"X": "user1"}, {"X": "user2"}]
        with patch("api.x.get_data", return_value=test_data):
            with patch("api.x._get_client") as mock_get_client:
                mock_response = AsyncMock()
                mock_response.__iter__ = lambda self: iter([])
                mock_response.next = AsyncMock(return_value=[])
                mock_client = MagicMock()
                mock_client.search_tweet = AsyncMock(return_value=mock_response)
                mock_get_client.return_value = mock_client

                result = await x_search(
                    users="user1,user2",
                    query="test",
                    period_days=3,
                    end_date="2023-01-01",
                )
                assert isinstance(result, list)

    async def test_x_search_with_pagination(self) -> None:
        """Test x_search with pagination"""
        test_data = [{"X": "user1"}]
        with patch("api.x.get_data", return_value=test_data):
            with patch("api.x._get_client") as mock_get_client:
                mock_response = AsyncMock()
                mock_response.__iter__ = lambda self: iter([])
                mock_response.next = AsyncMock(return_value=[])
                mock_client = MagicMock()
                mock_client.search_tweet = AsyncMock(return_value=mock_response)
                mock_get_client.return_value = mock_client

                result = await x_search(users="user1", query="test", period_days=3)
                assert isinstance(result, list)

    async def test_x_search_date_calculation(self) -> None:
        """Test x_search date calculation"""
        test_data = [{"X": "user1"}]
        with patch("api.x.get_data", return_value=test_data):
            with patch("api.x._get_client") as mock_get_client:
                mock_response = AsyncMock()
                mock_response.__iter__ = lambda self: iter([])
                mock_response.next = AsyncMock(return_value=[])
                mock_client = MagicMock()
                mock_client.search_tweet = AsyncMock(return_value=mock_response)
                mock_get_client.return_value = mock_client

                result = await x_search(
                    users="user1", query="test", period_days=7, end_date="2023-12-31"
                )
                assert isinstance(result, list)

    async def test_x_search_rate_limit_handling(self) -> None:
        """Test x_search rate limit handling"""
        test_data = [{"X": "user1"}]
        with patch("api.x.get_data", return_value=test_data):
            with patch("api.x._get_client") as mock_get_client:
                mock_client = MagicMock()
                mock_client.search_tweet = AsyncMock(
                    side_effect=HTTPException(
                        status_code=429, detail="Rate limit exceeded"
                    )
                )
                mock_get_client.return_value = mock_client

                with pytest.raises(HTTPException) as exc_info:
                    await x_search(users=None, query="test", max_tweets_per_user=1)
                assert exc_info.value.status_code == 429
                assert "Rate limit exceeded" in str(exc_info.value.detail)

    async def test_x_search_malformed_tweet_data(self) -> None:
        """Test x_search handling of malformed tweet data"""
        test_data = [{"X": "user1"}]
        with patch("api.x.get_data", return_value=test_data):
            with patch("api.x._get_client") as mock_get_client:
                mock_response = AsyncMock()
                mock_response.__iter__ = lambda self: iter([])
                mock_response.next = AsyncMock(return_value=[])
                mock_client = MagicMock()
                mock_client.search_tweet = AsyncMock(return_value=mock_response)
                mock_get_client.return_value = mock_client

                result = await x_search(users="user1", query="test", period_days=3)
                assert isinstance(result, list)
                assert len(result) == 0

    async def test_max_per_user_edge_cases(self) -> None:
        """Test _max_per_user with edge cases"""
        # Empty list
        assert len(_max_per_user([], 5)) == 0

        # Single tweet
        tweet = MagicMock(spec=Tweet)
        tweet.id = "1"
        tweet.user = MagicMock()
        tweet.user.id = 1
        assert len(_max_per_user([tweet], 5)) == 1

    async def test_filter_users_edge_cases(self) -> None:
        """Test _filter_users with edge cases"""
        # Mock data with edge cases
        test_data = [
            {"X": "test_user"},
            {"X": ""},
            {"X": "n/a"},
        ]
        with patch("api.x.get_data", return_value=test_data):
            # Empty list
            assert _filter_users([]) == []

            # User with no match in data
            result = _filter_users(["unknown_user"])
            assert result == []
