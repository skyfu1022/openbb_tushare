"""Unit tests for Tushare equity historical adjustment feature."""

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd

from openbb_tushare.models.equity_historical import (
    TushareEquityHistoricalQueryParams,
    TushareEquityHistoricalFetcher,
)
from openbb_tushare.utils.ts_equity_historical import (
    get_from_cache,
    get_one,
    check_cache,
    EQUITY_HISTORY_SCHEMA,
)
from mysharelib.table_cache import TableCache
from mysharelib.tools import normalize_symbol


class TestTushareEquityHistoricalQueryParams:
    """Tests for TushareEquityHistoricalQueryParams."""

    def test_adjustment_default_is_none(self):
        """Test that adjustment defaults to None."""
        q = TushareEquityHistoricalQueryParams(symbol="600036.SH")
        assert q.adjustment is None

    def test_adjustment_accepts_qfq(self):
        """Test that adjustment accepts 'qfq' value."""
        q = TushareEquityHistoricalQueryParams(symbol="600036.SH", adjustment="qfq")
        assert q.adjustment == "qfq"

    def test_adjustment_accepts_hfq(self):
        """Test that adjustment accepts 'hfq' value."""
        q = TushareEquityHistoricalQueryParams(symbol="600036.SH", adjustment="hfq")
        assert q.adjustment == "hfq"

    def test_adjustment_rejects_invalid_value(self):
        """Test that adjustment rejects invalid values."""
        with pytest.raises(Exception):
            TushareEquityHistoricalQueryParams(symbol="600036.SH", adjustment="invalid")

    def test_adjustment_description_exists(self):
        """Test that adjustment parameter has proper description."""
        field_info = TushareEquityHistoricalQueryParams.model_fields["adjustment"]
        assert "forward-adjusted" in field_info.description
        assert "backward-adjusted" in field_info.description


class TestCacheTableName:
    """Tests for cache table name generation based on adjustment type."""

    def test_table_name_without_adjustment(self):
        """Test table name without adjustment."""
        symbol_b, symbol_f, market = normalize_symbol("600036.SH")
        table_name = f"{market}{symbol_b}"
        assert table_name == "SH600036"

    def test_table_name_with_qfq_adjustment(self):
        """Test table name with qfq adjustment."""
        symbol_b, symbol_f, market = normalize_symbol("600036.SH")
        table_name = f"{market}{symbol_b}_qfq"
        assert table_name == "SH600036_qfq"

    def test_table_name_with_hfq_adjustment(self):
        """Test table name with hfq adjustment."""
        symbol_b, symbol_f, market = normalize_symbol("600036.SH")
        table_name = f"{market}{symbol_b}_hfq"
        assert table_name == "SH600036_hfq"

    def test_hk_table_name_with_adjustment(self):
        """Test table name for Hong Kong stocks with adjustment."""
        symbol_b, symbol_f, market = normalize_symbol("00700.HK")
        table_name = f"{market}{symbol_b}_qfq"
        assert table_name == "HK00700_qfq"


class TestGetOneApiSelection:
    """Tests for API selection logic in get_one function."""

    @patch("openbb_tushare.utils.ts_equity_historical.ts")
    @patch("openbb_tushare.utils.ts_equity_historical.get_api_key")
    def test_a_share_no_adjustment_uses_pro_daily(self, mock_get_api_key, mock_ts):
        """Test A-share without adjustment uses pro.daily()."""
        mock_get_api_key.return_value = "test_key"
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_pro.daily.return_value = pd.DataFrame()

        get_one("600036.SH", start_date=pd.to_datetime("2024-01-01").date(), 
                end_date=pd.to_datetime("2024-01-10").date(), adjust="")

        mock_pro.daily.assert_called_once()
        mock_pro.hk_daily.assert_not_called()
        mock_ts.pro_bar.assert_not_called()
        mock_pro.hk_daily_adj.assert_not_called()

    @patch("openbb_tushare.utils.ts_equity_historical.ts")
    @patch("openbb_tushare.utils.ts_equity_historical.get_api_key")
    def test_a_share_qfq_adjustment_uses_pro_bar(self, mock_get_api_key, mock_ts):
        """Test A-share with qfq adjustment uses ts.pro_bar()."""
        mock_get_api_key.return_value = "test_key"
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_ts.pro_bar.return_value = pd.DataFrame()

        get_one("600036.SH", start_date=pd.to_datetime("2024-01-01").date(), 
                end_date=pd.to_datetime("2024-01-10").date(), adjust="qfq")

        mock_ts.pro_bar.assert_called_once_with(
            ts_code="600036.SH",
            start_date="20240101",
            end_date="20240110",
            freq="D",
            adj="qfq"
        )

    @patch("openbb_tushare.utils.ts_equity_historical.ts")
    @patch("openbb_tushare.utils.ts_equity_historical.get_api_key")
    def test_a_share_hfq_adjustment_uses_pro_bar(self, mock_get_api_key, mock_ts):
        """Test A-share with hfq adjustment uses ts.pro_bar()."""
        mock_get_api_key.return_value = "test_key"
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_ts.pro_bar.return_value = pd.DataFrame()

        get_one("600036.SH", start_date=pd.to_datetime("2024-01-01").date(), 
                end_date=pd.to_datetime("2024-01-10").date(), adjust="hfq")

        mock_ts.pro_bar.assert_called_once_with(
            ts_code="600036.SH",
            start_date="20240101",
            end_date="20240110",
            freq="D",
            adj="hfq"
        )

    @patch("openbb_tushare.utils.ts_equity_historical.ts")
    @patch("openbb_tushare.utils.ts_equity_historical.get_api_key")
    def test_hk_share_no_adjustment_uses_hk_daily(self, mock_get_api_key, mock_ts):
        """Test Hong Kong stock without adjustment uses pro.hk_daily()."""
        mock_get_api_key.return_value = "test_key"
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_pro.hk_daily.return_value = pd.DataFrame()

        get_one("00700.HK", start_date=pd.to_datetime("2024-01-01").date(), 
                end_date=pd.to_datetime("2024-01-10").date(), adjust="")

        mock_pro.hk_daily.assert_called_once()
        mock_pro.daily.assert_not_called()
        mock_ts.pro_bar.assert_not_called()
        mock_pro.hk_daily_adj.assert_not_called()

    @patch("openbb_tushare.utils.ts_equity_historical.ts")
    @patch("openbb_tushare.utils.ts_equity_historical.get_api_key")
    def test_hk_share_adjustment_uses_hk_daily_adj(self, mock_get_api_key, mock_ts):
        """Test Hong Kong stock with adjustment uses pro.hk_daily_adj()."""
        mock_get_api_key.return_value = "test_key"
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_pro.hk_daily_adj.return_value = pd.DataFrame()

        get_one("00700.HK", start_date=pd.to_datetime("2024-01-01").date(), 
                end_date=pd.to_datetime("2024-01-10").date(), adjust="qfq")

        mock_pro.hk_daily_adj.assert_called_once()

    @patch("openbb_tushare.utils.ts_equity_historical.ts")
    @patch("openbb_tushare.utils.ts_equity_historical.get_api_key")
    def test_a_share_weekly_period_uses_correct_freq(self, mock_get_api_key, mock_ts):
        """Test A-share weekly period uses correct frequency parameter."""
        mock_get_api_key.return_value = "test_key"
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_ts.pro_bar.return_value = pd.DataFrame()

        get_one("600036.SH", start_date=pd.to_datetime("2024-01-01").date(), 
                end_date=pd.to_datetime("2024-01-10").date(), period="weekly", adjust="qfq")

        mock_ts.pro_bar.assert_called_once_with(
            ts_code="600036.SH",
            start_date="20240101",
            end_date="20240110",
            freq="W",
            adj="qfq"
        )

    @patch("openbb_tushare.utils.ts_equity_historical.ts")
    @patch("openbb_tushare.utils.ts_equity_historical.get_api_key")
    def test_a_share_monthly_period_uses_correct_freq(self, mock_get_api_key, mock_ts):
        """Test A-share monthly period uses correct frequency parameter."""
        mock_get_api_key.return_value = "test_key"
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_ts.pro_bar.return_value = pd.DataFrame()

        get_one("600036.SH", start_date=pd.to_datetime("2024-01-01").date(), 
                end_date=pd.to_datetime("2024-01-10").date(), period="monthly", adjust="qfq")

        mock_ts.pro_bar.assert_called_once_with(
            ts_code="600036.SH",
            start_date="20240101",
            end_date="20240110",
            freq="M",
            adj="qfq"
        )


class TestDataFrameColumnRenaming:
    """Tests for DataFrame column renaming in get_one function."""

    @patch("openbb_tushare.utils.ts_equity_historical.ts")
    @patch("openbb_tushare.utils.ts_equity_historical.get_api_key")
    def test_columns_are_renamed_correctly(self, mock_get_api_key, mock_ts):
        """Test that columns are renamed to standard names."""
        mock_get_api_key.return_value = "test_key"
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        
        # Create mock data with Tushare column names
        mock_df = pd.DataFrame({
            'trade_date': ['20240101', '20240102'],
            'open': [10.0, 10.1],
            'high': [10.5, 10.6],
            'low': [9.9, 10.0],
            'close': [10.2, 10.3],
            'vol': [1000, 2000],
            'pct_chg': [1.5, 0.8],
            'ts_code': ['600036.SH', '600036.SH']
        })
        mock_pro.daily.return_value = mock_df

        result = get_one("600036.SH", start_date=pd.to_datetime("2024-01-01").date(), 
                        end_date=pd.to_datetime("2024-01-02").date(), adjust="")

        # Check that columns are renamed
        assert 'date' in result.columns
        assert 'volume' in result.columns
        assert 'change_percent' in result.columns
        assert 'trade_date' not in result.columns
        assert 'vol' not in result.columns
        assert 'pct_chg' not in result.columns
        assert 'ts_code' not in result.columns


class TestExtractDataWithAdjustment:
    """Tests for extract_data method with adjustment parameter."""

    @patch("openbb_tushare.utils.ts_equity_historical.get_from_cache")
    def test_extract_data_passes_adjustment_none(self, mock_get_from_cache):
        """Test extract_data passes empty string when adjustment is None."""
        mock_get_from_cache.return_value = pd.DataFrame()
        
        fetcher = TushareEquityHistoricalFetcher()
        query = TushareEquityHistoricalQueryParams(
            symbol="600036.SH",
            adjustment=None
        )
        
        try:
            fetcher.extract_data(query, {})
        except Exception:
            pass  # Expected EmptyDataError
        
        mock_get_from_cache.assert_called_once()
        call_kwargs = mock_get_from_cache.call_args[1]
        assert call_kwargs['adjust'] == ""

    @patch("openbb_tushare.utils.ts_equity_historical.get_from_cache")
    def test_extract_data_passes_adjustment_qfq(self, mock_get_from_cache):
        """Test extract_data passes 'qfq' when adjustment is 'qfq'."""
        mock_get_from_cache.return_value = pd.DataFrame()
        
        fetcher = TushareEquityHistoricalFetcher()
        query = TushareEquityHistoricalQueryParams(
            symbol="600036.SH",
            adjustment="qfq"
        )
        
        try:
            fetcher.extract_data(query, {})
        except Exception:
            pass  # Expected EmptyDataError
        
        mock_get_from_cache.assert_called_once()
        call_kwargs = mock_get_from_cache.call_args[1]
        assert call_kwargs['adjust'] == "qfq"

    @patch("openbb_tushare.utils.ts_equity_historical.get_from_cache")
    def test_extract_data_passes_adjustment_hfq(self, mock_get_from_cache):
        """Test extract_data passes 'hfq' when adjustment is 'hfq'."""
        mock_get_from_cache.return_value = pd.DataFrame()
        
        fetcher = TushareEquityHistoricalFetcher()
        query = TushareEquityHistoricalQueryParams(
            symbol="600036.SH",
            adjustment="hfq"
        )
        
        try:
            fetcher.extract_data(query, {})
        except Exception:
            pass  # Expected EmptyDataError
        
        mock_get_from_cache.assert_called_once()
        call_kwargs = mock_get_from_cache.call_args[1]
        assert call_kwargs['adjust'] == "hfq"
