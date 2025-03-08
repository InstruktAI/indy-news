from typing import Dict, List
from unittest.mock import mock_open, patch

import pandas as pd
import pytest

from api.store import get_data, query_allsides, query_mediabiasfactcheck


@pytest.fixture
def mock_json_data() -> List[Dict[str, str]]:
    """Fixture to provide sample media data"""
    return [
        {
            "Name": "Test News",
            "Website": "https://test.news",
            "Youtube": "@testnews",
            "About": "Test news organization",
            "TrustFactors": "High quality reporting",
            "Topics": "Politics, Technology",
            "Wikipedia": "https://wikipedia.org/wiki/Test_News",
            "X": "@testnews",
        }
    ]


@pytest.fixture
def mock_allsides_data() -> List[Dict[str, str]]:
    """Fixture to provide sample AllSides data"""
    return [{"name": "Test News", "bias": "Center", "url": "https://test.news"}]


@pytest.fixture
def mock_mediabiasfactcheck_data() -> List[Dict[str, str]]:
    """Fixture to provide sample MediaBiasFactCheck data"""
    return [
        {
            "name": "Test News",
            "bias": "Least Biased",
            "factual": "High",
            "credibility": "high credibility",
            "profile": "Test profile",
            "url": "https://test.news",
        }
    ]


class TestStore:
    """Tests for store.py functionality"""

    def test_get_data(
        self,
        mock_json_data: List[Dict[str, str]],
        mock_mediabiasfactcheck_data: List[Dict[str, str]],
    ) -> None:
        """Test get_data function"""
        mock_csv = "Name,Website,Youtube,About,TrustFactors,Topics,Wikipedia,X\nTest News,https://test.news,@testnews,Test news organization,High quality reporting,Politics Technology,https://wikipedia.org/wiki/Test_News,@testnews"
        df = pd.DataFrame(mock_json_data)
        with (
            patch("builtins.open", mock_open(read_data=mock_csv)),
            patch("json.load", return_value=mock_mediabiasfactcheck_data),
            patch("pandas.read_csv", return_value=df),
            patch("os.path.exists", return_value=True),
        ):
            data = get_data(force=True)
            assert len(data) == 1
            assert isinstance(data, list)
            assert isinstance(data[0], dict)
            assert data[0].get("Name") == "Test News"
            assert data[0].get("Youtube") == "@testnews"

    def test_get_data_file_not_found(
        self,
        mock_json_data: List[Dict[str, str]],
        mock_mediabiasfactcheck_data: List[Dict[str, str]],
    ) -> None:
        """Test get_data function when file not found"""
        mock_csv = "Name,Website,Youtube,About,TrustFactors,Topics,Wikipedia,X\nTest News,https://test.news,@testnews,Test news organization,High quality reporting,Politics Technology,https://wikipedia.org/wiki/Test_News,@testnews"
        with (
            patch("os.path.exists", return_value=False),
            patch("pandas.read_csv", return_value=pd.DataFrame(mock_json_data)),
            patch("builtins.open", mock_open(read_data=mock_csv)),
            patch("json.load", return_value=mock_mediabiasfactcheck_data),
        ):
            data = get_data()
            assert len(data) == 1
            assert data[0]["Name"] == "Test News"
            assert data[0]["Youtube"] == "@testnews"
            assert data[0]["Bias"] == "Least Biased"
            assert data[0]["Factual"] == "High"

    def test_get_data_json_error(self) -> None:
        """Test get_data function when JSON parsing fails"""
        with (
            patch("builtins.open", mock_open(read_data="invalid json")),
            patch("json.load", side_effect=ValueError),
        ):
            # should throw ValueError on JSON parsing error
            with pytest.raises(ValueError):
                get_data()

    def test_query_allsides(self, mock_allsides_data: List[Dict[str, str]]) -> None:
        """Test query_allsides function"""
        with (
            patch("builtins.open", mock_open()),
            patch("json.load", return_value=mock_allsides_data),
        ):
            results = query_allsides("Test", 5, 0)
            assert len(results) == 1
            assert results[0]["bias"] == "Center"

    def test_query_allsides_no_matches(
        self, mock_allsides_data: List[Dict[str, str]]
    ) -> None:
        """Test query_allsides function with no matching results"""
        with (
            patch("builtins.open", mock_open()),
            patch("json.load", return_value=mock_allsides_data),
        ):
            results = query_allsides("NonExistent", 5, 0)
            assert len(results) == 0

    def test_query_allsides_case_insensitive(
        self, mock_allsides_data: List[Dict[str, str]]
    ) -> None:
        """Test query_allsides function is case-insensitive"""
        with (
            patch("builtins.open", mock_open()),
            patch("json.load", return_value=mock_allsides_data),
        ):
            results = query_allsides("test", 5, 0)  # lowercase query
            assert len(results) == 1
            assert results[0]["bias"] == "Center"

    def test_query_allsides_limit_and_offset(self) -> None:
        """Test query_allsides function respects limit and offset"""
        mock_data = [
            {"name": "Test News 1", "bias": "Center", "url": "https://test1.news"},
            {"name": "Test News 2", "bias": "Left", "url": "https://test2.news"},
            {"name": "Test News 3", "bias": "Right", "url": "https://test3.news"},
        ]
        with (
            patch("builtins.open", mock_open()),
            patch("json.load", return_value=mock_data),
        ):
            # Test limit
            results = query_allsides("Test", 2, 0)
            assert len(results) == 2

            # Test offset
            results = query_allsides("Test", 2, 1)
            assert len(results) == 2
            # The first result should be the second item from the original data
            assert results[0]["url"] == "https://test2.news"

    def test_query_mediabiasfactcheck(
        self, mock_mediabiasfactcheck_data: List[Dict[str, str]]
    ) -> None:
        """Test query_mediabiasfactcheck function"""
        with (
            patch("builtins.open", mock_open()),
            patch("json.load", return_value=mock_mediabiasfactcheck_data),
        ):
            results = query_mediabiasfactcheck("Test", 5, 0)
            assert len(results) == 1
            assert results[0]["bias"] == "Least Biased"
            assert results[0]["factual"] == "High"

    def test_query_mediabiasfactcheck_no_matches(
        self, mock_mediabiasfactcheck_data: List[Dict[str, str]]
    ) -> None:
        """Test query_mediabiasfactcheck function with no matching results"""
        with (
            patch("builtins.open", mock_open()),
            patch("json.load", return_value=mock_mediabiasfactcheck_data),
        ):
            results = query_mediabiasfactcheck("NonExistent", 5, 0)
            assert len(results) == 0

    def test_query_mediabiasfactcheck_case_insensitive(
        self, mock_mediabiasfactcheck_data: List[Dict[str, str]]
    ) -> None:
        """Test query_mediabiasfactcheck function is case-insensitive"""
        with (
            patch("builtins.open", mock_open()),
            patch("json.load", return_value=mock_mediabiasfactcheck_data),
        ):
            results = query_mediabiasfactcheck("test", 5, 0)  # lowercase query
            assert len(results) == 1
            assert results[0]["bias"] == "Least Biased"

    def test_query_mediabiasfactcheck_limit_and_offset(self) -> None:
        """Test query_mediabiasfactcheck function respects limit and offset"""
        mock_data = [
            {
                "name": "Test News 1",
                "bias": "Least Biased",
                "factual": "High",
                "credibility": "high credibility",
                "url": "https://test1.news",
            },
            {
                "name": "Test News 2",
                "bias": "Left Bias",
                "factual": "Mixed",
                "credibility": "medium credibility",
                "url": "https://test2.news",
            },
            {
                "name": "Test News 3",
                "bias": "Right Bias",
                "factual": "High",
                "credibility": "high credibility",
                "url": "https://test3.news",
            },
        ]
        with (
            patch("builtins.open", mock_open()),
            patch("json.load", return_value=mock_data),
        ):
            # Test limit
            results = query_mediabiasfactcheck("Test", 2, 0)
            assert len(results) == 2

            # Test offset
            results = query_mediabiasfactcheck("Test", 2, 1)
            assert len(results) == 2
            # The first result should be the second item from the original data
            assert results[0]["url"] == "https://test2.news"
