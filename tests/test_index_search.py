"""Unit tests for IndexSearch model."""

import pytest

from openbb_tushare.models.index_search import (
    TushareIndexSearchQueryParams,
    TushareIndexSearchData,
    TushareIndexSearchFetcher,
)


class TestTushareIndexSearchQueryParams:
    """Tests for query params."""

    def test_use_cache_default_is_true(self):
        q = TushareIndexSearchQueryParams()
        assert q.use_cache is True

    def test_query_param(self):
        q = TushareIndexSearchQueryParams(query="上证", use_cache=False)
        assert q.query == "上证"


class TestTushareIndexSearchData:
    """Tests for data model with alias mapping."""

    def test_ts_code_mapped_to_symbol(self):
        data = {"ts_code": "000001.SH", "name": "上证指数"}
        result = TushareIndexSearchData.model_validate(data)
        assert result.symbol == "000001.SH"
        assert result.name == "上证指数"

    def test_accepts_symbol_directly(self):
        data = {"symbol": "000001.SH", "name": "上证指数"}
        result = TushareIndexSearchData.model_validate(data)
        assert result.symbol == "000001.SH"


class TestTushareIndexSearchFetcherTransformData:
    """Tests for transform_data filtering logic."""

    def _make_query(self, query=None, is_symbol=False):
        params = {}
        if query is not None:
            params["query"] = query
            params["is_symbol"] = is_symbol
        return TushareIndexSearchQueryParams(**params)

    def test_no_query_returns_all(self):
        query = self._make_query()
        data = [
            {"ts_code": "000001.SH", "name": "上证指数"},
            {"ts_code": "399001.SZ", "name": "深证成指"},
        ]
        result = TushareIndexSearchFetcher.transform_data(query, data)
        assert len(result) == 2

    def test_filters_by_name(self):
        query = self._make_query(query="上证", is_symbol=False)
        data = [
            {"ts_code": "000001.SH", "name": "上证指数"},
            {"ts_code": "399001.SZ", "name": "深证成指"},
        ]
        result = TushareIndexSearchFetcher.transform_data(query, data)
        assert len(result) == 1
        assert result[0].name == "上证指数"

    def test_filters_by_ts_code_when_is_symbol(self):
        query = self._make_query(query="000001", is_symbol=True)
        data = [
            {"ts_code": "000001.SH", "name": "上证指数"},
            {"ts_code": "399001.SZ", "name": "深证成指"},
        ]
        result = TushareIndexSearchFetcher.transform_data(query, data)
        assert len(result) == 1
        assert result[0].symbol == "000001.SH"

    def test_filters_case_insensitive(self):
        query = self._make_query(query="sz", is_symbol=False)
        data = [
            {"ts_code": "399001.SZ", "name": "深证成指"},
            {"ts_code": "000001.SH", "name": "上证指数"},
        ]
        result = TushareIndexSearchFetcher.transform_data(query, data)
        assert len(result) == 1
        assert result[0].name == "深证成指"

    def test_empty_data_returns_empty(self):
        query = self._make_query()
        result = TushareIndexSearchFetcher.transform_data(query, [])
        assert result == []
