"""Integration tests for market data interfaces — hits real Tushare API.

Run with: uv run pytest tests/test_market_data_integration.py -v -m integration
Requires TUSHARE_API_KEY in environment or .env file.
"""

import os
import asyncio

import pytest
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


def _get_credentials():
    api_key = os.environ.get("TUSHARE_API_KEY", "")
    if not api_key:
        pytest.skip("TUSHARE_API_KEY not set, skipping integration test")
    return {"tushare_api_key": api_key}


# ── IndexHistorical ──────────────────────────────────────────────────────


@pytest.mark.integration
def test_index_historical_real_api():
    """Test real Tushare index_daily API call."""
    from openbb_tushare.utils.ts_index_historical import get_index_from_cache

    creds = _get_credentials()
    df = get_index_from_cache(
        ts_code="000001.SH",
        start_date="20240101",
        end_date="20240131",
        api_key=creds["tushare_api_key"],
        use_cache=False,
    )

    assert not df.empty
    assert "date" in df.columns
    assert "open" in df.columns
    assert "close" in df.columns
    assert "volume" in df.columns
    assert "amount" in df.columns
    assert "trade_date" not in df.columns
    assert "ts_code" not in df.columns


@pytest.mark.integration
def test_index_historical_fetcher_real():
    """Test IndexHistorical fetcher end-to-end."""
    from openbb_tushare.models.index_historical import TushareIndexHistoricalFetcher

    creds = _get_credentials()
    params = {
        "symbol": "000001.SH",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "use_cache": False,
    }

    query = TushareIndexHistoricalFetcher.transform_query(params)
    data = TushareIndexHistoricalFetcher.extract_data(query, creds)
    assert isinstance(data, list)
    assert len(data) > 0

    result = TushareIndexHistoricalFetcher.transform_data(query, data)
    assert len(result) > 0
    assert result[0].close > 0
    assert result[0].volume > 0


# ── IndexConstituents ────────────────────────────────────────────────────


@pytest.mark.integration
def test_index_constituents_real_api():
    """Test real Tushare index_weight API call."""
    from openbb_tushare.utils.ts_index_constituents import get_index_constituents

    creds = _get_credentials()
    df = get_index_constituents(
        symbol="000300.SH",
        api_key=creds["tushare_api_key"],
    )

    assert not df.empty
    assert "symbol" in df.columns
    assert list(df.columns) == ["symbol"]
    # 沪深300应有不少成分股
    assert len(df) > 100


@pytest.mark.integration
def test_index_constituents_fetcher_real():
    """Test IndexConstituents fetcher end-to-end."""
    from openbb_tushare.models.index_constituents import TushareIndexConstituentsFetcher

    creds = _get_credentials()
    params = {"symbol": "000300.SH", "use_cache": False}

    query = TushareIndexConstituentsFetcher.transform_query(params)
    data = TushareIndexConstituentsFetcher.extract_data(query, creds)
    assert isinstance(data, list)
    assert len(data) > 100

    result = TushareIndexConstituentsFetcher.transform_data(query, data)
    assert len(result) > 100
    assert result[0].symbol.endswith(".SH") or result[0].symbol.endswith(".SZ")


# ── IndexSearch ──────────────────────────────────────────────────────────


@pytest.mark.integration
def test_index_search_real_api():
    """Test real Tushare index_basic API call for search."""
    from openbb_tushare.utils.ts_available_indices import get_available_indices

    creds = _get_credentials()
    df = get_available_indices(use_cache=False, api_key=creds["tushare_api_key"])

    assert not df.empty
    assert "ts_code" in df.columns
    assert "name" in df.columns


@pytest.mark.integration
def test_index_search_fetcher_real():
    """Test IndexSearch fetcher end-to-end with query filter."""
    from openbb_tushare.models.index_search import TushareIndexSearchFetcher

    creds = _get_credentials()
    params = {"query": "沪深300", "use_cache": False}

    query = TushareIndexSearchFetcher.transform_query(params)
    data = TushareIndexSearchFetcher.extract_data(query, creds)
    assert isinstance(data, list)
    assert len(data) > 0

    result = TushareIndexSearchFetcher.transform_data(query, data)
    assert len(result) > 0
    # 结果应包含"沪深300"
    names = [r.name for r in result]
    assert any("沪深300" in n for n in names)


@pytest.mark.integration
def test_index_search_fetcher_by_symbol_real():
    """Test IndexSearch with is_symbol=True."""
    from openbb_tushare.models.index_search import TushareIndexSearchFetcher

    creds = _get_credentials()
    params = {"query": "000001", "is_symbol": True, "use_cache": False}

    query = TushareIndexSearchFetcher.transform_query(params)
    data = TushareIndexSearchFetcher.extract_data(query, creds)
    assert isinstance(data, list)

    result = TushareIndexSearchFetcher.transform_data(query, data)
    assert len(result) > 0
    assert any("000001" in r.symbol for r in result)


# ── IndexInfo ────────────────────────────────────────────────────────────


@pytest.mark.integration
def test_index_info_fetcher_real():
    """Test IndexInfo fetcher end-to-end."""
    from openbb_tushare.models.index_info import TushareIndexInfoFetcher

    creds = _get_credentials()
    params = {"symbol": "000001.SH", "use_cache": False}

    query = TushareIndexInfoFetcher.transform_query(params)
    data = TushareIndexInfoFetcher.extract_data(query, creds)
    assert isinstance(data, list)
    assert len(data) > 0

    result = TushareIndexInfoFetcher.transform_data(query, data)
    assert len(result) == 1
    assert result[0].symbol == "000001.SH"
    assert result[0].name == "上证指数"


# ── ETFHistorical ────────────────────────────────────────────────────────


@pytest.mark.integration
def test_etf_historical_real_api():
    """Test real Tushare fund_daily API call."""
    from openbb_tushare.utils.ts_etf_historical import get_etf_from_cache

    creds = _get_credentials()
    df = get_etf_from_cache(
        ts_code="510300.SH",
        start_date="20240101",
        end_date="20240131",
        api_key=creds["tushare_api_key"],
        use_cache=False,
    )

    assert not df.empty
    assert "date" in df.columns
    assert "open" in df.columns
    assert "close" in df.columns
    assert "volume" in df.columns
    assert "amount" in df.columns
    assert "trade_date" not in df.columns
    assert "ts_code" not in df.columns


@pytest.mark.integration
def test_etf_historical_fetcher_real():
    """Test ETFHistorical fetcher end-to-end."""
    from openbb_tushare.models.etf_historical import TushareEtfHistoricalFetcher

    creds = _get_credentials()
    params = {
        "symbol": "510300.SH",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "use_cache": False,
    }

    query = TushareEtfHistoricalFetcher.transform_query(params)
    data = TushareEtfHistoricalFetcher.extract_data(query, creds)
    assert isinstance(data, list)
    assert len(data) > 0

    result = TushareEtfHistoricalFetcher.transform_data(query, data)
    assert len(result) > 0
    assert result[0].close > 0
    assert result[0].volume > 0


# ── Provider Registration ────────────────────────────────────────────────


@pytest.mark.integration
def test_all_new_fetchers_registered():
    """Verify all 5 new fetchers are in provider.fetcher_dict."""
    from openbb_tushare.provider import provider

    expected = [
        "EtfHistorical",
        "IndexConstituents",
        "IndexHistorical",
        "IndexInfo",
        "IndexSearch",
    ]
    for name in expected:
        assert name in provider.fetcher_dict, f"{name} not registered in provider"
    assert len(provider.fetcher_dict) >= 15
