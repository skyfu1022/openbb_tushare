"""Unit tests for ETFHistorical model and utils."""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from datetime import date

from openbb_tushare.models.etf_historical import (
    TushareEtfHistoricalQueryParams,
    TushareEtfHistoricalData,
    TushareEtfHistoricalFetcher,
)
from openbb_tushare.utils.ts_etf_historical import (
    get_etf_from_cache,
    ETF_HISTORY_SCHEMA,
)


class TestTushareEtfHistoricalQueryParams:
    """Tests for query params validation."""

    def test_use_cache_default_is_true(self):
        q = TushareEtfHistoricalQueryParams(symbol="510300.SH")
        assert q.use_cache is True

    def test_use_cache_can_be_false(self):
        q = TushareEtfHistoricalQueryParams(symbol="510300.SH", use_cache=False)
        assert q.use_cache is False

    def test_validates_start_date_iso_format(self):
        q = TushareEtfHistoricalQueryParams(
            symbol="510300.SH",
            start_date="2024-01-01",
            end_date="2024-06-01",
        )
        assert q.start_date is not None

    def test_rejects_invalid_start_date_format(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            TushareEtfHistoricalQueryParams(
                symbol="510300.SH",
                start_date="20240101",
                end_date="2024-06-01",
            )

    def test_rejects_invalid_end_date_format(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            TushareEtfHistoricalQueryParams(
                symbol="510300.SH",
                start_date="2024-01-01",
                end_date="2024/06/01",
            )


class TestTushareEtfHistoricalData:
    """Tests for data model."""

    def test_data_model_with_amount(self):
        data = {
            "date": "2024-01-02",
            "open": 4.0,
            "high": 4.1,
            "low": 3.9,
            "close": 4.05,
            "volume": 50000.0,
            "amount": 200000.0,
        }
        result = TushareEtfHistoricalData.model_validate(data)
        assert result.close == 4.05
        assert result.amount == 200000.0

    def test_data_model_amount_optional(self):
        data = {
            "date": "2024-01-02",
            "open": 4.0,
            "high": 4.1,
            "low": 3.9,
            "close": 4.05,
            "volume": 50000.0,
        }
        result = TushareEtfHistoricalData.model_validate(data)
        assert result.amount is None


class TestTushareEtfHistoricalFetcherTransformQuery:
    """Tests for transform_query."""

    def test_transform_query_sets_default_dates(self):
        params = {"symbol": "510300.SH"}
        result = TushareEtfHistoricalFetcher.transform_query(params)
        assert result.start_date is not None
        assert result.end_date is not None
        assert result.symbol == "510300.SH"


class TestGetEtfFromCache:
    """Tests for utils helper."""

    def test_schema_has_required_columns(self):
        required = {"date", "open", "high", "low", "close", "volume", "amount"}
        assert required == set(ETF_HISTORY_SCHEMA.keys())

    @patch("openbb_tushare.utils.ts_etf_historical.ts")
    @patch("openbb_tushare.utils.ts_etf_historical.get_api_key")
    @patch("openbb_tushare.utils.ts_etf_historical.TableCache")
    def test_calls_fund_daily_api(self, mock_cache_cls, mock_get_api_key, mock_ts):
        mock_get_api_key.return_value = "test_key"
        mock_cache = MagicMock()
        mock_cache.fetch_date_range.return_value = pd.DataFrame()
        mock_cache_cls.return_value = mock_cache

        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_pro.fund_daily.return_value = pd.DataFrame()

        get_etf_from_cache("510300.SH", "20240101", "20240601", use_cache=False)

        mock_pro.fund_daily.assert_called_once_with(
            ts_code="510300.SH", start_date="20240101", end_date="20240601"
        )

    @patch("openbb_tushare.utils.ts_etf_historical.ts")
    @patch("openbb_tushare.utils.ts_etf_historical.get_api_key")
    @patch("openbb_tushare.utils.ts_etf_historical.TableCache")
    def test_renames_columns(self, mock_cache_cls, mock_get_api_key, mock_ts):
        mock_get_api_key.return_value = "test_key"
        mock_cache = MagicMock()
        mock_cache.fetch_date_range.return_value = pd.DataFrame()
        mock_cache_cls.return_value = mock_cache

        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_df = pd.DataFrame({
            "trade_date": ["20240101"],
            "open": [4.0],
            "high": [4.1],
            "low": [3.9],
            "close": [4.05],
            "vol": [50000.0],
            "amount": [200000.0],
            "ts_code": ["510300.SH"],
            "pct_chg": [1.0],
            "pre_close": [4.0],
            "change": [0.05],
        })
        mock_pro.fund_daily.return_value = mock_df

        get_etf_from_cache("510300.SH", "20240101", "20240101", use_cache=False)

        written_df = mock_cache.write_dataframe.call_args[0][0]
        assert "date" in written_df.columns
        assert "volume" in written_df.columns
        assert "trade_date" not in written_df.columns
        assert "vol" not in written_df.columns
        assert "ts_code" not in written_df.columns

    @patch("openbb_tushare.utils.ts_etf_historical.get_api_key")
    @patch("openbb_tushare.utils.ts_etf_historical.TableCache")
    def test_returns_cached_data_when_available(self, mock_cache_cls, mock_get_api_key):
        mock_get_api_key.return_value = "test_key"
        cached_df = pd.DataFrame({"date": ["20240101"], "close": [4.05]})
        mock_cache = MagicMock()
        mock_cache.fetch_date_range.return_value = cached_df
        mock_cache_cls.return_value = mock_cache

        result = get_etf_from_cache("510300.SH", "20240101", "20240101", use_cache=True)
        assert not result.empty
        assert result.equals(cached_df)

    @patch("openbb_tushare.utils.ts_etf_historical.ts")
    @patch("openbb_tushare.utils.ts_etf_historical.get_api_key")
    @patch("openbb_tushare.utils.ts_etf_historical.TableCache")
    def test_returns_empty_on_empty_api_response(self, mock_cache_cls, mock_get_api_key, mock_ts):
        mock_get_api_key.return_value = "test_key"
        mock_cache = MagicMock()
        mock_cache.fetch_date_range.return_value = pd.DataFrame()
        mock_cache_cls.return_value = mock_cache

        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_pro.fund_daily.return_value = pd.DataFrame()

        result = get_etf_from_cache("510300.SH", "20240101", "20240601", use_cache=False)
        assert result.empty

    @patch("openbb_tushare.utils.ts_etf_historical.ts")
    @patch("openbb_tushare.utils.ts_etf_historical.get_api_key")
    @patch("openbb_tushare.utils.ts_etf_historical.TableCache")
    def test_converts_date_object_to_string(self, mock_cache_cls, mock_get_api_key, mock_ts):
        mock_get_api_key.return_value = "test_key"
        mock_cache = MagicMock()
        mock_cache.fetch_date_range.return_value = pd.DataFrame()
        mock_cache_cls.return_value = mock_cache

        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_pro.fund_daily.return_value = pd.DataFrame()

        get_etf_from_cache("510300.SH", date(2024, 1, 1), date(2024, 6, 1), use_cache=False)

        mock_pro.fund_daily.assert_called_once_with(
            ts_code="510300.SH", start_date="20240101", end_date="20240601"
        )
