"""Unit tests for IndexConstituents model and utils."""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from openbb_tushare.models.index_constituents import (
    TushareIndexConstituentsQueryParams,
    TushareIndexConstituentsData,
    TushareIndexConstituentsFetcher,
)
from openbb_tushare.utils.ts_index_constituents import get_index_constituents


class TestTushareIndexConstituentsQueryParams:
    """Tests for query params."""

    def test_use_cache_default_is_true(self):
        q = TushareIndexConstituentsQueryParams(symbol="000300.SH")
        assert q.use_cache is True

    def test_use_cache_can_be_false(self):
        q = TushareIndexConstituentsQueryParams(symbol="000300.SH", use_cache=False)
        assert q.use_cache is False


class TestTushareIndexConstituentsData:
    """Tests for data model."""

    def test_data_model_with_symbol(self):
        data = {"symbol": "600036.SH"}
        result = TushareIndexConstituentsData.model_validate(data)
        assert result.symbol == "600036.SH"


class TestTushareIndexConstituentsFetcher:
    """Tests for fetcher."""

    def test_transform_query(self):
        params = {"symbol": "000300.SH"}
        result = TushareIndexConstituentsFetcher.transform_query(params)
        assert result.symbol == "000300.SH"

    def test_transform_data_with_data(self):
        query = TushareIndexConstituentsQueryParams(symbol="000300.SH")
        data = [{"symbol": "600036.SH"}, {"symbol": "000001.SZ"}]
        result = TushareIndexConstituentsFetcher.transform_data(query, data)
        assert len(result) == 2
        assert result[0].symbol == "600036.SH"

    def test_transform_data_with_empty(self):
        query = TushareIndexConstituentsQueryParams(symbol="000300.SH")
        result = TushareIndexConstituentsFetcher.transform_data(query, [])
        assert result == []


class TestGetIndexConstituents:
    """Tests for utils helper."""

    @patch("openbb_tushare.utils.ts_index_constituents.ts")
    @patch("openbb_tushare.utils.ts_index_constituents.get_api_key")
    def test_returns_latest_constituents(self, mock_get_api_key, mock_ts):
        mock_get_api_key.return_value = "test_key"
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro

        mock_df = pd.DataFrame({
            "trade_date": ["20240101", "20240101", "20231201"],
            "con_code": ["600036.SH", "000001.SZ", "600036.SH"],
            "weight": [5.0, 3.0, 5.0],
        })
        mock_pro.index_weight.return_value = mock_df

        result = get_index_constituents("000300.SH")
        assert len(result) == 2
        assert "symbol" in result.columns
        assert "600036.SH" in result["symbol"].values

    @patch("openbb_tushare.utils.ts_index_constituents.ts")
    @patch("openbb_tushare.utils.ts_index_constituents.get_api_key")
    def test_returns_empty_on_empty_response(self, mock_get_api_key, mock_ts):
        mock_get_api_key.return_value = "test_key"
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_pro.index_weight.return_value = pd.DataFrame()

        result = get_index_constituents("000300.SH")
        assert result.empty

    @patch("openbb_tushare.utils.ts_index_constituents.ts")
    @patch("openbb_tushare.utils.ts_index_constituents.get_api_key")
    def test_only_returns_symbol_column(self, mock_get_api_key, mock_ts):
        mock_get_api_key.return_value = "test_key"
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro

        mock_df = pd.DataFrame({
            "trade_date": ["20240101"],
            "con_code": ["600036.SH"],
            "weight": [5.0],
        })
        mock_pro.index_weight.return_value = mock_df

        result = get_index_constituents("000300.SH")
        assert list(result.columns) == ["symbol"]
