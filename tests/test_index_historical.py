"""Unit tests for IndexHistorical model and utils."""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from datetime import date

from openbb_tushare.models.index_historical import (
    TushareIndexHistoricalQueryParams,
    TushareIndexHistoricalData,
    TushareIndexHistoricalFetcher,
)
from openbb_tushare.utils.ts_index_historical import (
    get_index_from_cache,
    INDEX_HISTORY_SCHEMA,
)


class TestTushareIndexHistoricalQueryParams:
    """Tests for query params validation."""

    def test_use_cache_default_is_true(self):
        q = TushareIndexHistoricalQueryParams(symbol="000001.SH")
        assert q.use_cache is True

    def test_use_cache_can_be_false(self):
        q = TushareIndexHistoricalQueryParams(symbol="000001.SH", use_cache=False)
        assert q.use_cache is False

    def test_validates_start_date_iso_format(self):
        q = TushareIndexHistoricalQueryParams(
            symbol="000001.SH",
            start_date="2024-01-01",
            end_date="2024-06-01",
        )
        assert q.start_date is not None

    def test_rejects_invalid_start_date_format(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            TushareIndexHistoricalQueryParams(
                symbol="000001.SH",
                start_date="20240101",
                end_date="2024-06-01",
            )

    def test_rejects_invalid_end_date_format(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            TushareIndexHistoricalQueryParams(
                symbol="000001.SH",
                start_date="2024-01-01",
                end_date="2024/06/01",
            )


class TestTushareIndexHistoricalData:
    """Tests for data model."""

    def test_data_model_with_amount(self):
        data = {
            "date": "2024-01-02",
            "open": 2960.0,
            "high": 2980.0,
            "low": 2950.0,
            "close": 2970.0,
            "volume": 1000000.0,
            "amount": 5000000.0,
        }
        result = TushareIndexHistoricalData.model_validate(data)
        assert result.close == 2970.0
        assert result.amount == 5000000.0

    def test_data_model_amount_optional(self):
        data = {
            "date": "2024-01-02",
            "open": 2960.0,
            "high": 2980.0,
            "low": 2950.0,
            "close": 2970.0,
            "volume": 1000000.0,
        }
        result = TushareIndexHistoricalData.model_validate(data)
        assert result.amount is None


class TestTushareIndexHistoricalFetcherTransformQuery:
    """Tests for transform_query."""

    def test_transform_query_sets_default_dates(self):
        params = {"symbol": "000001.SH"}
        result = TushareIndexHistoricalFetcher.transform_query(params)
        assert result.start_date is not None
        assert result.end_date is not None
        assert result.symbol == "000001.SH"

    def test_transform_query_preserves_explicit_dates(self):
        params = {
            "symbol": "000001.SH",
            "start_date": "2024-01-01",
            "end_date": "2024-06-01",
        }
        result = TushareIndexHistoricalFetcher.transform_query(params)
        assert result.symbol == "000001.SH"


class TestGetIndexFromCache:
    """Tests for utils helper."""

    def test_schema_has_required_columns(self):
        required = {"date", "open", "high", "low", "close", "volume", "amount"}
        assert required == set(INDEX_HISTORY_SCHEMA.keys())

    @patch("openbb_tushare.utils.ts_index_historical.ts")
    @patch("openbb_tushare.utils.ts_index_historical.get_api_key")
    @patch("openbb_tushare.utils.ts_index_historical.TableCache")
    def test_calls_index_daily_api(self, mock_cache_cls, mock_get_api_key, mock_ts):
        mock_get_api_key.return_value = "test_key"
        mock_cache = MagicMock()
        mock_cache.fetch_date_range.return_value = pd.DataFrame()
        mock_cache_cls.return_value = mock_cache

        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_pro.index_daily.return_value = pd.DataFrame()

        get_index_from_cache("000001.SH", "20240101", "20240601", use_cache=False)

        mock_pro.index_daily.assert_called_once_with(
            ts_code="000001.SH", start_date="20240101", end_date="20240601"
        )

    @patch("openbb_tushare.utils.ts_index_historical.ts")
    @patch("openbb_tushare.utils.ts_index_historical.get_api_key")
    @patch("openbb_tushare.utils.ts_index_historical.TableCache")
    def test_renames_columns(self, mock_cache_cls, mock_get_api_key, mock_ts):
        mock_get_api_key.return_value = "test_key"
        mock_cache = MagicMock()
        mock_cache.fetch_date_range.return_value = pd.DataFrame()
        mock_cache_cls.return_value = mock_cache

        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_df = pd.DataFrame({
            "trade_date": ["20240101"],
            "open": [10.0],
            "high": [11.0],
            "low": [9.0],
            "close": [10.5],
            "vol": [1000.0],
            "amount": [5000.0],
            "ts_code": ["000001.SH"],
            "pct_chg": [1.0],
            "pre_close": [10.0],
            "change": [0.5],
        })
        mock_pro.index_daily.return_value = mock_df

        get_index_from_cache("000001.SH", "20240101", "20240101", use_cache=False)

        written_df = mock_cache.write_dataframe.call_args[0][0]
        assert "date" in written_df.columns
        assert "volume" in written_df.columns
        assert "trade_date" not in written_df.columns
        assert "vol" not in written_df.columns
        assert "ts_code" not in written_df.columns
        assert "pct_chg" not in written_df.columns

    @patch("openbb_tushare.utils.ts_index_historical.ts")
    @patch("openbb_tushare.utils.ts_index_historical.get_api_key")
    @patch("openbb_tushare.utils.ts_index_historical.TableCache")
    def test_returns_empty_on_empty_api_response(self, mock_cache_cls, mock_get_api_key, mock_ts):
        mock_get_api_key.return_value = "test_key"
        mock_cache = MagicMock()
        mock_cache.fetch_date_range.return_value = pd.DataFrame()
        mock_cache_cls.return_value = mock_cache

        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_pro.index_daily.return_value = pd.DataFrame()

        result = get_index_from_cache("000001.SH", "20240101", "20240601", use_cache=False)
        assert result.empty

    @patch("openbb_tushare.utils.ts_index_historical.get_api_key")
    @patch("openbb_tushare.utils.ts_index_historical.TableCache")
    def test_returns_cached_data_when_available(self, mock_cache_cls, mock_get_api_key):
        mock_get_api_key.return_value = "test_key"
        cached_df = pd.DataFrame({"date": ["20240101"], "close": [3000.0]})
        mock_cache = MagicMock()
        mock_cache.fetch_date_range.return_value = cached_df
        mock_cache_cls.return_value = mock_cache

        result = get_index_from_cache("000001.SH", "20240101", "20240101", use_cache=True)
        assert not result.empty
        assert result.equals(cached_df)

    @patch("openbb_tushare.utils.ts_index_historical.ts")
    @patch("openbb_tushare.utils.ts_index_historical.get_api_key")
    @patch("openbb_tushare.utils.ts_index_historical.TableCache")
    def test_converts_date_object_to_string(self, mock_cache_cls, mock_get_api_key, mock_ts):
        mock_get_api_key.return_value = "test_key"
        mock_cache = MagicMock()
        mock_cache.fetch_date_range.return_value = pd.DataFrame()
        mock_cache_cls.return_value = mock_cache

        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_pro.index_daily.return_value = pd.DataFrame()

        get_index_from_cache("000001.SH", date(2024, 1, 1), date(2024, 6, 1), use_cache=False)

        mock_pro.index_daily.assert_called_once_with(
            ts_code="000001.SH", start_date="20240101", end_date="20240601"
        )
