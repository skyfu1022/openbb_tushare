import logging
import pandas as pd
import tushare as ts
from mysharelib.tools import setup_logger
from openbb_tushare.utils.helpers import get_api_key
from openbb_tushare import project_name

setup_logger(project_name)
logger = logging.getLogger(__name__)


def get_index_constituents(
    symbol: str,
    api_key: str = "",
) -> pd.DataFrame:
    tushare_api_key = get_api_key(api_key)

    pro = ts.pro_api(tushare_api_key)

    df = pro.index_weight(index_code=symbol, start_date="20200101")

    if df.empty:
        return pd.DataFrame()

    latest_date = df["trade_date"].max()
    df_latest = df[df["trade_date"] == latest_date].copy()

    logger.info(
        f"Got {len(df_latest)} constituents for {symbol} on {latest_date}."
    )

    df_latest = df_latest.rename(columns={"con_code": "symbol"})
    df_latest = df_latest[["symbol"]]

    return df_latest
