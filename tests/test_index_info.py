"""Unit tests for IndexInfo model."""

import pytest

from openbb_tushare.models.index_info import (
    TushareIndexInfoQueryParams,
    TushareIndexInfoData,
    TushareIndexInfoFetcher,
)


class TestTushareIndexInfoQueryParams:
    """Tests for query params."""

    def test_use_cache_default_is_true(self):
        q = TushareIndexInfoQueryParams(symbol="000001.SH")
        assert q.use_cache is True

    def test_symbol_param(self):
        q = TushareIndexInfoQueryParams(symbol="000001.SH")
        assert q.symbol == "000001.SH"


class TestTushareIndexInfoData:
    """Tests for data model with alias mapping."""

    def test_ts_code_mapped_to_symbol(self):
        data = {
            "ts_code": "000001.SH",
            "name": "上证指数",
            "fullname": "上海证券综合指数",
        }
        result = TushareIndexInfoData.model_validate(data)
        assert result.symbol == "000001.SH"
        assert result.name == "上证指数"


class TestTushareIndexInfoFetcherTransformData:
    """Tests for transform_data filtering logic."""

    def test_filters_by_symbol(self):
        query = TushareIndexInfoQueryParams(symbol="000001.SH")
        data = [
            {"ts_code": "000001.SH", "name": "上证指数"},
            {"ts_code": "399001.SZ", "name": "深证成指"},
        ]
        result = TushareIndexInfoFetcher.transform_data(query, data)
        assert len(result) == 1
        assert result[0].symbol == "000001.SH"

    def test_returns_all_when_symbol_does_not_filter(self):
        query = TushareIndexInfoQueryParams(symbol="000001.SH")
        data = [
            {"ts_code": "000001.SH", "name": "上证指数"},
            {"ts_code": "399001.SZ", "name": "深证成指"},
        ]
        result = TushareIndexInfoFetcher.transform_data(query, data)
        assert len(result) == 1
        assert result[0].symbol == "000001.SH"

    def test_filter_case_insensitive(self):
        query = TushareIndexInfoQueryParams(symbol="000001.sh")
        data = [
            {"ts_code": "000001.SH", "name": "上证指数"},
        ]
        result = TushareIndexInfoFetcher.transform_data(query, data)
        assert len(result) == 1

    def test_empty_data_returns_empty(self):
        query = TushareIndexInfoQueryParams(symbol="000001.SH")
        result = TushareIndexInfoFetcher.transform_data(query, [])
        assert result == []
