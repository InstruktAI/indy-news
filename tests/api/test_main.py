"""
Integration tests for API endpoints.
These tests exercise the full request/response cycle, mocking only external dependencies.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> TestClient:
    """Fixture to provide a test client"""
    return TestClient(app)


@pytest.fixture
def api_key() -> str:
    """Fixture to provide test API key"""
    return "test_api_key_12345"


@pytest.fixture(autouse=True)
def setup_api_key(api_key: str):
    """Automatically set up API key for all tests"""
    os.environ["API_KEY"] = api_key


@pytest.fixture
def mock_csv_data() -> str:
    """Mock CSV data for testing"""
    return """Name,X,Youtube,Substack,Website,About,TrustFactors,Topics
Al Jazeera,@ajenglish,@aljazeeraenglish,n/a,https://aljazeera.com,International news,Independent,Politics
Democracy Now,@democracynow,@democracynow,democracynow,https://democracynow.org,Independent news,Grassroots,Politics"""


class TestAuthentication:
    """Test API authentication enforcement"""

    def test_endpoint_requires_auth(self, client: TestClient):
        """Endpoints should reject requests without API key"""
        response = client.get("/sources")
        assert response.status_code == 401

    def test_invalid_api_key(self, client: TestClient):
        """Endpoints should reject invalid API keys"""
        response = client.get("/sources?apikey=wrong_key")
        assert response.status_code == 401

    def test_valid_api_key_query_param(self, client: TestClient, api_key: str):
        """Endpoints should accept valid API key in query param"""
        with patch("api.store.get_data", return_value=[]):
            response = client.get(f"/sources?apikey={api_key}")
            assert response.status_code == 200

    def test_valid_api_key_header(self, client: TestClient, api_key: str):
        """Endpoints should accept valid API key in header"""
        with patch("api.store.get_data", return_value=[]):
            response = client.get("/sources", headers={"X-API-KEY": api_key})
            assert response.status_code == 200


class TestDataEndpoints:
    """Test data query endpoints - these test actual business logic"""

    def test_sources_endpoint_returns_minimal_fields(
        self, client: TestClient, api_key: str, mock_csv_data: str
    ):
        """Test /sources returns only Name, About, Topics"""
        with patch("builtins.open", mock_open(read_data=mock_csv_data)):
            response = client.get(f"/sources?apikey={api_key}")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            # Verify only minimal fields returned
            assert set(data[0].keys()) == {"Name", "About", "Topics"}
            assert data[0]["Name"] == "Al Jazeera"

    def test_source_media_filters_na_values(
        self, client: TestClient, api_key: str, mock_csv_data: str
    ) -> None:
        """Test /source-media converts 'n/a' to None"""
        with patch("builtins.open", mock_open(read_data=mock_csv_data)):
            response = client.get(f"/source-media?sources=Al Jazeera&apikey={api_key}")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["Substack"] is None  # Was "n/a" in CSV
            assert data[0]["Youtube"] == "@aljazeeraenglish"

    def test_media_search_exact_match_only(
        self, client: TestClient, api_key: str, mock_csv_data: str
    ) -> None:
        """Test /media requires exact name match"""
        with patch("builtins.open", mock_open(read_data=mock_csv_data)):
            # Exact match should work
            response = client.get(f"/media?names=Al Jazeera&apikey={api_key}")
            assert response.status_code == 200
            assert len(response.json()) == 1

            # Partial match should NOT work
            response = client.get(f"/media?names=Al&apikey={api_key}")
            assert response.status_code == 200
            assert len(response.json()) == 0


class TestContentEndpointValidation:
    """Test parameter validation for content endpoints"""

    def test_youtube_requires_query_or_channels(
        self, client: TestClient, api_key: str
    ) -> None:
        """Test /youtube rejects requests with neither query nor channels"""
        response = client.get(f"/youtube?apikey={api_key}")
        assert response.status_code == 400
        assert "Either one of" in response.json()["detail"]

    def test_x_requires_query_or_users(
        self, client: TestClient, api_key: str
    ) -> None:
        """Test /x rejects requests with neither query nor users"""
        response = client.get(f"/x?apikey={api_key}")
        assert response.status_code == 400
        assert "Either one of" in response.json()["detail"]

    def test_substack_requires_query_or_publications(
        self, client: TestClient, api_key: str
    ) -> None:
        """Test /substack rejects requests with neither query nor publications"""
        response = client.get(f"/substack?apikey={api_key}")
        assert response.status_code == 400
        assert "Either one of" in response.json()["detail"]

    def test_news_requires_channels_or_users(
        self, client: TestClient, api_key: str
    ) -> None:
        """Test /news rejects requests with neither channels nor users"""
        response = client.get(f"/news?apikey={api_key}")
        assert response.status_code == 400
        assert "Either one of" in response.json()["detail"]


class TestWebhookEndpoint:
    """Test webhook endpoint for cookie updates"""

    def test_webhook_accepts_valid_cookies(
        self, client: TestClient, api_key: str
    ) -> None:
        """Test webhook successfully saves valid cookies"""
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("os.getenv", return_value=tmpdir),
        ):
            payload = {
                "success": True,
                "cookies": "cookie1=value1; cookie2=value2",
            }
            response = client.post(f"/webhook/cookies?apikey={api_key}", json=payload)
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

            # Verify cookie file was written
            cookie_file = Path(tmpdir) / "cookies.txt"
            assert cookie_file.exists()
            assert "cookie1=value1" in cookie_file.read_text()

    def test_webhook_rejects_failed_refresh(
        self, client: TestClient, api_key: str
    ) -> None:
        """Test webhook rejects failed cookie refresh"""
        payload = {
            "success": False,
            "cookies": None,
            "error": "Login failed",
        }
        response = client.post(f"/webhook/cookies?apikey={api_key}", json=payload)
        assert response.status_code == 400
        assert "Cookie refresh failed" in response.json()["detail"]

    def test_webhook_rejects_success_without_cookies(
        self, client: TestClient, api_key: str
    ) -> None:
        """Test webhook rejects success=true but no cookies"""
        payload = {
            "success": True,
            "cookies": None,
        }
        response = client.post(f"/webhook/cookies?apikey={api_key}", json=payload)
        assert response.status_code == 400


class TestHealthEndpoint:
    """Test health/privacy endpoints"""

    def test_privacy_endpoint(self, client: TestClient) -> None:
        """Test /privacy returns success (no auth required)"""
        response = client.get("/privacy")
        assert response.status_code == 200
        assert response.json() == "You are ok"
