import logging
import pandas as pd
import tushare as ts
from datetime import (
    date as dateType,
    datetime,
)
from typing import Optional, Union
from mysharelib.tools import setup_logger
from openbb_tushare.utils.helpers import get_api_key
from mysharelib.tools import normalize_symbol
from mysharelib.table_cache import TableCache
from openbb_tushare import project_name

setup_logger(project_name)

logger = logging.getLogger(__name__)

EQUITY_HISTORY_SCHEMA = {
    "date": "TEXT PRIMARY KEY",
    "open": "REAL",
    "high": "REAL",
    "low": "REAL",
    "close": "REAL",
    "volume": "REAL",
    "vwap": "REAL",
    "change": "REAL",
    "change_percent": "REAL",
    "amount": "REAL",
    "adj_factor": "REAL",
}

def get_from_cache(
        ts_code: str,
        start_date: Union[dateType, str],
        end_date: Union[dateType, str],
        api_key: str = "",
        period: str = "daily",
        use_cache: bool = True,
        adjust: str = ""
    ) -> pd.DataFrame:
    """
    Retrieves historical equity data from a cache or downloads it from a remote source.
    
    Parameters:
        ts_code (str): Stock symbol to fetch data for.
        start_date (Union[dateType, str]): Start date for fetching data.
        end_date (Union[dateType, str]): End date for fetching data.
        api_key (str): Tushare API key.
        period (str): Data frequency, e.g., "daily", "weekly", "monthly".
        use_cache (bool): Whether to use cached data.
        adjust (str): Adjustment type, e.g., "qfq" for forward-adjusted, "hfq" for backward-adjusted.

    Returns:
        DataFrame: DataFrame containing historical equity data.
    """
    from mysharelib.tools import get_valid_date

    # Retrieve data from cache first
    symbol_b, symbol_f, market = normalize_symbol(ts_code)
    
    # Generate cache table name based on adjustment type
    table_name = f"{market}{symbol_b}"
    if adjust:
        table_name = f"{table_name}_{adjust}"
    
    cache = TableCache(EQUITY_HISTORY_SCHEMA, project=project_name, table_name=table_name, primary_key="date")
    
    start_dt = get_valid_date(start_date)
    end_dt = get_valid_date(end_date)

    start = start_dt.strftime("%Y%m%d")
    end = end_dt.strftime("%Y%m%d")
    if use_cache:
        check_cache(symbol=ts_code, cache=cache, api_key=api_key, period=period, adjust=adjust)
        data_from_cache = cache.fetch_date_range(start, end)
        if not data_from_cache.empty:
            logger.info(f"Getting equity {ts_code} historical data from cache...")
            return data_from_cache

    # If not in cache, download data from Tushare API
    data_util_today_df = get_one(ts_code, period=period, api_key=api_key, start_date=start_dt, end_date=end_dt, adjust=adjust)
    cache.write_dataframe(data_util_today_df)
    
    return cache.fetch_date_range(start, end)

def get_one(
        ts_code: str,
        start_date: dateType,
        end_date: dateType,
        period: str = "daily",
        api_key: str = "",
        adjust: str = ""
    ) -> pd.DataFrame:
    """
    Fetch historical equity data from Tushare API.
    
    Parameters:
        ts_code (str): Stock symbol to fetch data for.
        start_date (dateType): Start date for fetching data.
        end_date (dateType): End date for fetching data.
        period (str): Data frequency, e.g., "daily", "weekly", "monthly".
        api_key (str): Tushare API key.
        adjust (str): Adjustment type, "qfq" for forward-adjusted, "hfq" for backward-adjusted.

    Returns:
        DataFrame: DataFrame containing historical equity data.
    """
    tushare_api_key = get_api_key(api_key)

    pro = ts.pro_api(tushare_api_key)
    _, normalized_ts_code, market = normalize_symbol(ts_code)
    
    # Convert dates to tushare format (YYYYMMDD)
    if isinstance(start_date, dateType):
        start_date_str = start_date.strftime("%Y%m%d")
    else:
        start_date_str = start_date
    
    if isinstance(end_date, dateType):
        end_date_str = end_date.strftime("%Y%m%d")
    else:
        end_date_str = end_date
    
    df_data = pd.DataFrame()
    
    if market == 'HK':
        if adjust:
            # Hong Kong stock with adjustment - use hk_daily_adj
            df_data = pro.hk_daily_adj(
                ts_code=normalized_ts_code,
                start_date=start_date_str,
                end_date=end_date_str
            )
            logger.info(f"Downloaded adjusted historical data (HK) {normalized_ts_code}: {len(df_data)} rows from {start_date_str} to {end_date_str}.")
        else:
            # Hong Kong stock without adjustment - use hk_daily
            df_data = pro.hk_daily(
                ts_code=normalized_ts_code,
                start_date=start_date_str,
                end_date=end_date_str
            )
            logger.info(f"Downloaded historical data (HK) {normalized_ts_code}: {len(df_data)} rows from {start_date_str} to {end_date_str}.")
    else:
        if adjust:
            # A-share with adjustment - use pro_bar
            freq = 'D' if period == 'daily' else 'W' if period == 'weekly' else 'M'
            ts.set_token(tushare_api_key)
            df_data = ts.pro_bar(
                ts_code=normalized_ts_code,
                start_date=start_date_str,
                end_date=end_date_str,
                freq=freq,
                adj=adjust
            )
            logger.info(f"Downloaded {adjust} adjusted historical data {normalized_ts_code}: {len(df_data)} rows from {start_date_str} to {end_date_str}.")
        else:
            # A-share without adjustment - use pro_bar to get adj_factor
            freq = 'D' if period == 'daily' else 'W' if period == 'weekly' else 'M'
            ts.set_token(tushare_api_key)
            df_data = ts.pro_bar(
                ts_code=normalized_ts_code,
                start_date=start_date_str,
                end_date=end_date_str,
                freq=freq,
            )
            logger.info(f"Downloaded historical data {normalized_ts_code}: {len(df_data)} rows from {start_date_str} to {end_date_str}.")

    # Rename columns to standard names
    rename_map = {
        'trade_date': 'date',
        'vol': 'volume',
        'pct_chg': 'change_percent',
        'pre_close': 'previous_close'
    }
    df_data = df_data.rename(columns=lambda col: rename_map.get(col, col))
    
    # Drop unnecessary columns
    if 'ts_code' in df_data.columns:
        df_data.drop(columns=['ts_code'], inplace=True)
    
    return df_data

def check_cache(
        symbol: str,
        cache: TableCache,
        api_key: str = "",
        period: str = "daily",
        adjust: str = ""
    ) -> bool:
    """
    Check if the cache contains the latest data for the given symbol.
    
    Parameters:
        symbol (str): Stock symbol to check cache for.
        cache (TableCache): Cache instance.
        api_key (str): Tushare API key.
        period (str): Data frequency.
        adjust (str): Adjustment type, e.g., "qfq", "hfq".

    Returns:
        bool: True if cache is valid, False otherwise.
    """
    from openbb_tushare.utils.ts_helpers import get_list_date
    from mysharelib.tools import last_closing_day

    start_str = get_list_date(symbol, api_key=api_key)
    from datetime import datetime as dt
    start = dt.strptime(start_str, "%Y%m%d").date()
    end = last_closing_day()
    cache_df = cache.fetch_date_range(start.strftime("%Y%m%d"), end.strftime("%Y%m%d"))
    
    if cache_df.empty:
        logger.warning(f"Cache for {symbol} is empty.")
        data_util_today_df = get_one(symbol, period=period, api_key=api_key, start_date=start, end_date=end, adjust=adjust)
        cache.write_dataframe(data_util_today_df)
        return False
    
    cache_df = cache_df.set_index('date')
    cache_df.index = pd.to_datetime(cache_df.index)
    is_cache_valid = cache_df.index.max().date() == last_closing_day()
    
    if not is_cache_valid:
        logger.warning(f"Cache for {symbol} is not up-to-date. Last date in cache: {cache_df.index.max().date()}, expected: {last_closing_day()}.")
        data_util_today_df = get_one(symbol, period=period, api_key=api_key, start_date=start, end_date=end, adjust=adjust)
        cache.write_dataframe(data_util_today_df)
    
    return is_cache_valid