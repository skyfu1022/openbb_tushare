"""Tushare ETF Historical Price Model."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from dateutil.relativedelta import relativedelta
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.etf_historical import (
    EtfHistoricalData,
    EtfHistoricalQueryParams,
)
from openbb_core.provider.utils.errors import EmptyDataError
from pydantic import Field, ValidationInfo, field_validator

from openbb_tushare.utils.tools import validate_iso_yyyy_mm_dd


class TushareEtfHistoricalQueryParams(EtfHistoricalQueryParams):
    """Tushare ETF Historical Price Query.

    Source: https://tushare.pro/document/2?doc_id=19
    """

    use_cache: bool = Field(
        default=True,
        description="Whether to use a cached request.",
    )

    @field_validator("start_date", "end_date", mode="before", check_fields=False)
    @classmethod
    def _validate_dates(cls, v: object, info: ValidationInfo) -> object:
        return validate_iso_yyyy_mm_dd(v, info.field_name)


class TushareEtfHistoricalData(EtfHistoricalData):
    """Tushare ETF Historical Price Data."""

    amount: Optional[float] = Field(
        default=None,
        description="Amount.",
    )


class TushareEtfHistoricalFetcher(
    Fetcher[
        TushareEtfHistoricalQueryParams,
        List[TushareEtfHistoricalData],
    ]
):
    """Transform the query, extract and transform the data from the Tushare endpoints."""

    @staticmethod
    def transform_query(params: Dict[str, Any]) -> TushareEtfHistoricalQueryParams:
        transformed_params = params

        now = datetime.now().date()
        if params.get("start_date") is None:
            transformed_params["start_date"] = now - relativedelta(years=1)

        if params.get("end_date") is None:
            transformed_params["end_date"] = now

        return TushareEtfHistoricalQueryParams(**transformed_params)

    @staticmethod
    def extract_data(
        query: TushareEtfHistoricalQueryParams,
        credentials: Optional[Dict[str, str]],
        **kwargs: Any,
    ) -> List[Dict]:
        from openbb_tushare.utils.ts_etf_historical import get_etf_from_cache

        api_key = credentials.get("tushare_api_key") if credentials else ""
        data = get_etf_from_cache(
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
        query: TushareEtfHistoricalQueryParams, data: List[Dict], **kwargs: Any
    ) -> List[TushareEtfHistoricalData]:
        return [TushareEtfHistoricalData.model_validate(d) for d in data]
