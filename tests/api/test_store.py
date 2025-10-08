from typing import Dict, List
from unittest.mock import mock_open, patch

import pandas as pd
import pytest

from api.store import get_data


@pytest.fixture
def mock_json_data() -> List[Dict[str, str]]:
    """Fixture to provide sample media data"""
    return [
        {
            "Name": "Test News",
            "X": "@testnews",
            "Youtube": "@testnews",
            "Substack": "testnews",
            "Website": "https://test.news",
            "About": "Test news organization",
            "TrustFactors": "High quality reporting",
            "Topics": "Politics, Technology",
        }
    ]


class TestStore:
    """Tests for store.py functionality"""

    def test_get_data(
        self,
        mock_json_data: List[Dict[str, str]],
    ) -> None:
        """Test get_data function"""
        df = pd.DataFrame(mock_json_data)
        with patch("pandas.read_csv", return_value=df):
            data = get_data()
            assert len(data) == 1
            assert isinstance(data, list)
            assert isinstance(data[0], dict)
            assert data[0].get("Name") == "Test News"
            assert data[0].get("Youtube") == "@testnews"
            assert data[0].get("Substack") == "testnews"
