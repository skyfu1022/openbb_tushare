"""Tushare Index Historical Price Model."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from dateutil.relativedelta import relativedelta
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.index_historical import (
    IndexHistoricalData,
    IndexHistoricalQueryParams,
)
from openbb_core.provider.utils.errors import EmptyDataError
from pydantic import Field, ValidationInfo, field_validator

from openbb_tushare.utils.tools import validate_iso_yyyy_mm_dd


class TushareIndexHistoricalQueryParams(IndexHistoricalQueryParams):
    """Tushare Index Historical Price Query.

    Source: https://tushare.pro/document/2?doc_id=173
    """

    use_cache: bool = Field(
        default=True,
        description="Whether to use a cached request.",
    )

    @field_validator("start_date", "end_date", mode="before", check_fields=False)
    @classmethod
    def _validate_dates(cls, v: object, info: ValidationInfo) -> object:
        return validate_iso_yyyy_mm_dd(v, info.field_name)


class TushareIndexHistoricalData(IndexHistoricalData):
    """Tushare Index Historical Price Data."""

    amount: Optional[float] = Field(
        default=None,
        description="Amount.",
    )


class TushareIndexHistoricalFetcher(
    Fetcher[
        TushareIndexHistoricalQueryParams,
        List[TushareIndexHistoricalData],
    ]
):
    """Transform the query, extract and transform the data from the Tushare endpoints."""

    @staticmethod
    def transform_query(params: Dict[str, Any]) -> TushareIndexHistoricalQueryParams:
        transformed_params = params

        now = datetime.now().date()
        if params.get("start_date") is None:
            transformed_params["start_date"] = now - relativedelta(years=1)

        if params.get("end_date") is None:
            transformed_params["end_date"] = now

        return TushareIndexHistoricalQueryParams(**transformed_params)

    @staticmethod
    def extract_data(
        query: TushareIndexHistoricalQueryParams,
        credentials: Optional[Dict[str, str]],
        **kwargs: Any,
    ) -> List[Dict]:
        from openbb_tushare.utils.ts_index_historical import get_index_from_cache

        api_key = credentials.get("tushare_api_key") if credentials else ""
        data = get_index_from_cache(
            ts_code=query.symbol,
            start_date=query.start_date,
            end_date=query.end_date,
            api_key=api_key,
            use_cache=query.use_cache,
        )

        if data.empty:
            raise EmptyDataError()

        return data.to_dict(orient="records")

    @staticmethod
    def transform_data(
        query: TushareIndexHistoricalQueryParams, data: List[Dict], **kwargs: Any
    ) -> List[TushareIndexHistoricalData]:
        return [TushareIndexHistoricalData.model_validate(d) for d in data]
