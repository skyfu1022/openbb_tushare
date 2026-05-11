"""Tushare Index Constituents Model."""

from typing import Any, Dict, List, Optional

from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.index_constituents import (
    IndexConstituentsData,
    IndexConstituentsQueryParams,
)
from pydantic import Field


class TushareIndexConstituentsQueryParams(IndexConstituentsQueryParams):
    """Tushare Index Constituents Query.

    Source: https://tushare.pro/document/2?doc_id=96
    """

    use_cache: bool = Field(
        default=True,
        description="Whether to use a cached request.",
    )


class TushareIndexConstituentsData(IndexConstituentsData):
    """Tushare Index Constituents Data."""


class TushareIndexConstituentsFetcher(
    Fetcher[
        TushareIndexConstituentsQueryParams,
        List[TushareIndexConstituentsData],
    ]
):
    """Transform the query, extract and transform the data from the Tushare endpoints."""

    @staticmethod
    def transform_query(params: Dict[str, Any]) -> TushareIndexConstituentsQueryParams:
        return TushareIndexConstituentsQueryParams(**params)

    @staticmethod
    def extract_data(
        query: TushareIndexConstituentsQueryParams,
        credentials: Optional[Dict[str, str]],
        **kwargs: Any,
    ) -> List[Dict]:
        from openbb_tushare.utils.ts_index_constituents import get_index_constituents

        api_key = credentials.get("tushare_api_key") if credentials else ""
        data = get_index_constituents(
            symbol=query.symbol,
            api_key=api_key,
        )

        if data.empty:
            return []

        return data.to_dict(orient="records")

    @staticmethod
    def transform_data(
        query: TushareIndexConstituentsQueryParams, data: List[Dict], **kwargs: Any
    ) -> List[TushareIndexConstituentsData]:
        return [TushareIndexConstituentsData.model_validate(d) for d in data]
