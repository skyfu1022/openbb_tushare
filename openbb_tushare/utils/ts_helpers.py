"""
Helper functions using Tushare API.
"""
import logging

import tushare as ts
from mysharelib.tools import normalize_symbol
from openbb_tushare.utils.helpers import get_api_key

logger = logging.getLogger(__name__)


def get_list_date(ts_code: str, api_key: str = "") -> str:
    """查询 A 股/港股的上市日期，返回 YYYYMMDD 字符串。"""
    tushare_api_key = get_api_key(api_key)
    pro = ts.pro_api(tushare_api_key)

    _, _, market = normalize_symbol(ts_code)

    if market == "HK":
        df = pro.hk_stock_basic(ts_code=ts_code, fields="ts_code,name,list_date")
    else:
        df = pro.stock_basic(ts_code=ts_code, fields="ts_code,name,list_date")

    if df.empty:
        logger.warning(f"No list_date found for {ts_code}, falling back to 19900101")
        return "19900101"

    return str(df.iloc[0]["list_date"])