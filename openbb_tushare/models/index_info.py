"""Tushare Index Info Model."""

from typing import Any, Dict, List, Optional

from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.index_info import (
    IndexInfoData,
    IndexInfoQueryParams,
)
from pydantic import Field


class TushareIndexInfoQueryParams(IndexInfoQueryParams):
    """Tushare Index Info Query.

    Source: https://tushare.pro/document/2?doc_id=94
    """

    use_cache: bool = Field(
        default=True,
        description="Whether to use a cached request.",
    )


class TushareIndexInfoData(IndexInfoData):
    """Tushare Index Info Data."""

    __alias_dict__ = {
        "symbol": "ts_code",
    }


class TushareIndexInfoFetcher(
    Fetcher[
        TushareIndexInfoQueryParams,
        List[TushareIndexInfoData],
    ]
):
    """Transform the query, extract and transform the data from the Tushare endpoints."""

    @staticmethod
    def transform_query(params: Dict[str, Any]) -> TushareIndexInfoQueryParams:
        return TushareIndexInfoQueryParams(**params)

    @staticmethod
    def extract_data(
        query: TushareIndexInfoQueryParams,
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
        query: TushareIndexInfoQueryParams, data: List[Dict], **kwargs: Any
    ) -> List[TushareIndexInfoData]:
        if query.symbol:
            data = [
                d for d in data if d.get("ts_code", "").upper() == query.symbol.upper()
            ]

        return [TushareIndexInfoData.model_validate(d) for d in data]
