"""Tushare Index Search Model."""

from typing import Any, Dict, List, Optional

from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.index_search import (
    IndexSearchData,
    IndexSearchQueryParams,
)
from pydantic import Field


class TushareIndexSearchQueryParams(IndexSearchQueryParams):
    """Tushare Index Search Query.

    Source: https://tushare.pro/document/2?doc_id=94
    """

    use_cache: bool = Field(
        default=True,
        description="Whether to use a cached request.",
    )


class TushareIndexSearchData(IndexSearchData):
    """Tushare Index Search Data."""

    __alias_dict__ = {
        "symbol": "ts_code",
    }


class TushareIndexSearchFetcher(
    Fetcher[
        TushareIndexSearchQueryParams,
        List[TushareIndexSearchData],
    ]
):
    """Transform the query, extract and transform the data from the Tushare endpoints."""

    @staticmethod
    def transform_query(params: Dict[str, Any]) -> TushareIndexSearchQueryParams:
        return TushareIndexSearchQueryParams(**params)

    @staticmethod
    def extract_data(
        query: TushareIndexSearchQueryParams,
        credentials: Optional[Dict[str, str]],
        **kwargs: Any,
    ) -> List[Dict]:
        from openbb_tushare.utils.ts_available_indices import get_available_indices

        api_key = credentials.get("tushare_api_key") if credentials else ""
        data = get_available_indices(query.use_cache, api_key=api_key)

        if data.empty:
            return []

        return data.to_dict(orient="records")

    @staticmethod
    def transform_data(
        query: TushareIndexSearchQueryParams, data: List[Dict], **kwargs: Any
    ) -> List[TushareIndexSearchData]:
        if query.query:
            if query.is_symbol:
                data = [
                    d for d in data if query.query.upper() in d.get("ts_code", "").upper()
                ]
            else:
                data = [
                    d
                    for d in data
                    if query.query.upper() in d.get("name", "").upper()
                    or query.query.upper() in d.get("ts_code", "").upper()
                ]

        return [TushareIndexSearchData.model_validate(d) for d in data]
