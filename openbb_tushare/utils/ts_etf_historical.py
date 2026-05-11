import logging
import pandas as pd
import tushare as ts
from datetime import date as dateType
from typing import Union
from mysharelib.tools import setup_logger
from openbb_tushare.utils.helpers import get_api_key
from mysharelib.table_cache import TableCache
from openbb_tushare import project_name

setup_logger(project_name)
logger = logging.getLogger(__name__)

ETF_HISTORY_SCHEMA = {
    "date": "TEXT PRIMARY KEY",
    "open": "REAL",
    "high": "REAL",
    "low": "REAL",
    "close": "REAL",
    "volume": "REAL",
    "amount": "REAL",
}


def get_etf_from_cache(
    ts_code: str,
    start_date: Union[dateType, str],
    end_date: Union[dateType, str],
    api_key: str = "",
    use_cache: bool = True,
) -> pd.DataFrame:
    tushare_api_key = get_api_key(api_key)

    cache = TableCache(
        ETF_HISTORY_SCHEMA,
        project=project_name,
        table_name=f"etf_{ts_code.replace('.', '_')}",
        primary_key="date",
    )

    if isinstance(start_date, dateType):
        start = start_date.strftime("%Y%m%d")
    else:
        start = start_date

    if isinstance(end_date, dateType):
        end = end_date.strftime("%Y%m%d")
    else:
        end = end_date

    if use_cache:
        data_from_cache = cache.fetch_date_range(start, end)
        if not data_from_cache.empty:
            logger.info(f"Getting ETF {ts_code} historical data from cache...")
            return data_from_cache

    pro = ts.pro_api(tushare_api_key)
    df_data = pro.fund_daily(
        ts_code=ts_code, start_date=start, end_date=end
    )

    if df_data.empty:
        return pd.DataFrame()

    logger.info(
        f"Downloaded ETF {ts_code}: {len(df_data)} rows from {start} to {end}."
    )

    rename_map = {
        "trade_date": "date",
        "vol": "volume",
    }
    df_data = df_data.rename(columns=lambda col: rename_map.get(col, col))

    cols_to_drop = [c for c in ["ts_code", "pct_chg", "pre_close", "change"] if c in df_data.columns]
    if cols_to_drop:
        df_data.drop(columns=cols_to_drop, inplace=True)

    if "volume" in df_data.columns:
        df_data["volume"] = df_data["volume"].round().astype("Int64")

    cache.write_dataframe(df_data)
    return cache.fetch_date_range(start, end)
