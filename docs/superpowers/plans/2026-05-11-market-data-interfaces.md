# 行情接口完善实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 openbb_tushare 新增 5 个行情接口（IndexHistorical、IndexConstituents、IndexSearch、IndexInfo、ETFHistorical），覆盖指数和 ETF 的历史行情、成分股、搜索和基本信息。

**Architecture:** 所有接口遵循现有 Fetcher 三步模式（transform_query → extract_data → transform_data）。需要新 utils helper 的接口（IndexHistorical、IndexConstituents、ETFHistorical）复用 TableCache 缓存机制。IndexSearch 和 IndexInfo 复用已有的 `ts_available_indices.py`。

**Tech Stack:** OpenBB Provider SDK (openbb-core), Tushare Python SDK, mysharelib TableCache, Pydantic

---

## File Structure

| 文件 | 操作 | 职责 |
|------|------|------|
| `openbb_tushare/utils/ts_index_historical.py` | 新建 | 指数历史行情缓存 + Tushare API 调用 |
| `openbb_tushare/utils/ts_index_constituents.py` | 新建 | 指数成分股获取 + Tushare API 调用 |
| `openbb_tushare/utils/ts_etf_historical.py` | 新建 | ETF 历史行情缓存 + Tushare API 调用 |
| `openbb_tushare/models/index_historical.py` | 新建 | IndexHistorical Fetcher 模型 |
| `openbb_tushare/models/index_constituents.py` | 新建 | IndexConstituents Fetcher 模型 |
| `openbb_tushare/models/index_search.py` | 新建 | IndexSearch Fetcher 模型 |
| `openbb_tushare/models/index_info.py` | 新建 | IndexInfo Fetcher 模型 |
| `openbb_tushare/models/etf_historical.py` | 新建 | ETFHistorical Fetcher 模型 |
| `openbb_tushare/provider.py` | 修改 | 注册 5 个新 Fetcher |

---

### Task 1: IndexHistorical — utils helper

**Files:**
- Create: `openbb_tushare/utils/ts_index_historical.py`

- [ ] **Step 1: 创建 utils helper**

参考 `ts_equity_historical.py` 的模式，创建 `ts_index_historical.py`。Tushare API 为 `pro.index_daily(ts_code, start_date, end_date)`。

```python
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

INDEX_HISTORY_SCHEMA = {
    "date": "TEXT PRIMARY KEY",
    "open": "REAL",
    "high": "REAL",
    "low": "REAL",
    "close": "REAL",
    "volume": "REAL",
    "amount": "REAL",
}


def get_index_from_cache(
    ts_code: str,
    start_date: Union[dateType, str],
    end_date: Union[dateType, str],
    api_key: str = "",
    use_cache: bool = True,
) -> pd.DataFrame:
    tushare_api_key = get_api_key(api_key)

    cache = TableCache(
        INDEX_HISTORY_SCHEMA,
        project=project_name,
        table_name=f"idx_{ts_code.replace('.', '_')}",
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
            logger.info(f"Getting index {ts_code} historical data from cache...")
            return data_from_cache

    pro = ts.pro_api(tushare_api_key)
    df_data = pro.index_daily(
        ts_code=ts_code, start_date=start, end_date=end
    )

    if df_data.empty:
        return pd.DataFrame()

    logger.info(
        f"Downloaded index {ts_code}: {len(df_data)} rows from {start} to {end}."
    )

    rename_map = {
        "trade_date": "date",
        "vol": "volume",
    }
    df_data = df_data.rename(columns=lambda col: rename_map.get(col, col))

    cols_to_drop = [c for c in ["ts_code", "pct_chg", "pre_close", "change"] if c in df_data.columns]
    if cols_to_drop:
        df_data.drop(columns=cols_to_drop, inplace=True)

    cache.write_dataframe(df_data)
    return cache.fetch_date_range(start, end)
```

- [ ] **Step 2: 验证文件语法**

Run: `cd /Users/skyfu/Projects/QuantProjects/falpha/openbb_tushare && python -c "from openbb_tushare.utils.ts_index_historical import get_index_from_cache; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add openbb_tushare/utils/ts_index_historical.py
git commit -m "feat: add index historical utils helper with TableCache"
```

---

### Task 2: IndexHistorical — Fetcher 模型

**Files:**
- Create: `openbb_tushare/models/index_historical.py`

- [ ] **Step 1: 创建 Fetcher 模型**

参考 `equity_historical.py` 的模式。OpenBB 标准模型 `IndexHistoricalData` 字段：date, open, high, low, close, volume。Tushare `index_daily` 返回字段：trade_date, open, high, low, close, vol, amount。通过 `__alias_dict__` 不需要，因为 utils 已经做了 rename。

```python
"""Tushare Index Historical Price Model."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from dateutil.relativedelta import relativedelta
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.index_historical import (
    IndexHistoricalData,
    IndexHistoricalQueryParams,
)
from openbb_core.provider.utils.descriptions import QUERY_DESCRIPTIONS
from openbb_core.provider.utils.errors import EmptyDataError
from pydantic import Field

from openbb_tushare.utils.tools import validate_iso_yyyy_mm_dd
from pydantic import ValidationInfo, field_validator


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
```

- [ ] **Step 2: 验证文件语法**

Run: `cd /Users/skyfu/Projects/QuantProjects/falpha/openbb_tushare && python -c "from openbb_tushare.models.index_historical import TushareIndexHistoricalFetcher; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add openbb_tushare/models/index_historical.py
git commit -m "feat: add IndexHistorical fetcher model"
```

---

### Task 3: IndexConstituents — utils helper

**Files:**
- Create: `openbb_tushare/utils/ts_index_constituents.py`

- [ ] **Step 1: 创建 utils helper**

Tushare API 为 `pro.index_weight(index_code, start_date, end_date)`。取最新交易日的权重数据。注意 `con_code` 格式为 `000001.SZ`，OpenBB 标准要求 `symbol` 字段。

```python
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
```

- [ ] **Step 2: 验证文件语法**

Run: `cd /Users/skyfu/Projects/QuantProjects/falpha/openbb_tushare && python -c "from openbb_tushare.utils.ts_index_constituents import get_index_constituents; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add openbb_tushare/utils/ts_index_constituents.py
git commit -m "feat: add index constituents utils helper"
```

---

### Task 4: IndexConstituents — Fetcher 模型

**Files:**
- Create: `openbb_tushare/models/index_constituents.py`

- [ ] **Step 1: 创建 Fetcher 模型**

OpenBB 标准 `IndexConstituentsData` 字段：symbol, name。Tushare `index_weight` 返回 `con_code`，需要映射为 `symbol`。名称需要通过 `stock_basic` 补充（或直接返回无 name 的数据，因为 OpenBB 标准 name 是 Optional）。

```python
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
```

- [ ] **Step 2: 验证文件语法**

Run: `cd /Users/skyfu/Projects/QuantProjects/falpha/openbb_tushare && python -c "from openbb_tushare.models.index_constituents import TushareIndexConstituentsFetcher; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add openbb_tushare/models/index_constituents.py
git commit -m "feat: add IndexConstituents fetcher model"
```

---

### Task 5: IndexSearch — Fetcher 模型（无新 utils）

**Files:**
- Create: `openbb_tushare/models/index_search.py`

- [ ] **Step 1: 创建 Fetcher 模型**

复用 `ts_available_indices.py` 的 `get_available_indices()`，在 `transform_data` 中过滤。OpenBB 标准 `IndexSearchData` 字段：symbol, name。`get_available_indices()` 返回含 `ts_code` 和 `name` 的 DataFrame，需要用 `__alias_dict__` 映射。

```python
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
```

- [ ] **Step 2: 验证文件语法**

Run: `cd /Users/skyfu/Projects/QuantProjects/falpha/openbb_tushare && python -c "from openbb_tushare.models.index_search import TushareIndexSearchFetcher; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add openbb_tushare/models/index_search.py
git commit -m "feat: add IndexSearch fetcher model"
```

---

### Task 6: IndexInfo — Fetcher 模型（无新 utils）

**Files:**
- Create: `openbb_tushare/models/index_info.py`

- [ ] **Step 1: 创建 Fetcher 模型**

复用 `ts_available_indices.py`，按 symbol 过滤。OpenBB 标准 `IndexInfoData` 字段：symbol, name, description, methodology, factsheet, num_constituents。`get_available_indices()` 返回 `ts_code`, `name`, `fullname`, `base_date`, `base_point` 等。`methodology`、`factsheet`、`num_constituents` 在 Tushare 中无对应字段，返回 None（OpenBB 标准这些字段本身就是 Optional）。

```python
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
```

- [ ] **Step 2: 验证文件语法**

Run: `cd /Users/skyfu/Projects/QuantProjects/falpha/openbb_tushare && python -c "from openbb_tushare.models.index_info import TushareIndexInfoFetcher; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add openbb_tushare/models/index_info.py
git commit -m "feat: add IndexInfo fetcher model"
```

---

### Task 7: ETFHistorical — utils helper

**Files:**
- Create: `openbb_tushare/utils/ts_etf_historical.py`

- [ ] **Step 1: 创建 utils helper**

Tushare API 为 `pro.fund_daily(ts_code, start_date, end_date)`。模式与 `ts_index_historical.py` 一致。

```python
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

    cache.write_dataframe(df_data)
    return cache.fetch_date_range(start, end)
```

- [ ] **Step 2: 验证文件语法**

Run: `cd /Users/skyfu/Projects/QuantProjects/falpha/openbb_tushare && python -c "from openbb_tushare.utils.ts_etf_historical import get_etf_from_cache; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add openbb_tushare/utils/ts_etf_historical.py
git commit -m "feat: add ETF historical utils helper with TableCache"
```

---

### Task 8: ETFHistorical — Fetcher 模型

**Files:**
- Create: `openbb_tushare/models/etf_historical.py`

- [ ] **Step 1: 创建 Fetcher 模型**

OpenBB 标准 `EtfHistoricalData` 字段：date, open, high, low, close, volume。模式与 `index_historical.py` 一致。

```python
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
from pydantic import Field

from openbb_tushare.utils.tools import validate_iso_yyyy_mm_dd
from pydantic import ValidationInfo, field_validator


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
```

- [ ] **Step 2: 验证文件语法**

Run: `cd /Users/skyfu/Projects/QuantProjects/falpha/openbb_tushare && python -c "from openbb_tushare.models.etf_historical import TushareEtfHistoricalFetcher; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add openbb_tushare/models/etf_historical.py
git commit -m "feat: add ETFHistorical fetcher model"
```

---

### Task 9: 注册所有新 Fetcher 到 provider.py

**Files:**
- Modify: `openbb_tushare/provider.py`

- [ ] **Step 1: 添加 import 和注册**

在 `provider.py` 中添加 5 个新 import 和 fetcher_dict 条目：

在 import 区域（第 13 行 `from openbb_tushare.models.income_statement` 之后）添加：

```python
from openbb_tushare.models.etf_historical import TushareEtfHistoricalFetcher
from openbb_tushare.models.index_constituents import TushareIndexConstituentsFetcher
from openbb_tushare.models.index_historical import TushareIndexHistoricalFetcher
from openbb_tushare.models.index_info import TushareIndexInfoFetcher
from openbb_tushare.models.index_search import TushareIndexSearchFetcher
```

在 `fetcher_dict` 中（`"IncomeStatement"` 行之后）添加：

```python
        "EtfHistorical": TushareEtfHistoricalFetcher,
        "IndexConstituents": TushareIndexConstituentsFetcher,
        "IndexHistorical": TushareIndexHistoricalFetcher,
        "IndexInfo": TushareIndexInfoFetcher,
        "IndexSearch": TushareIndexSearchFetcher,
```

- [ ] **Step 2: 验证 provider 能正常加载**

Run: `cd /Users/skyfu/Projects/QuantProjects/falpha/openbb_tushare && python -c "from openbb_tushare.provider import provider; print(sorted(provider.fetcher_dict.keys()))"`
Expected: 包含 `'EtfHistorical', 'IndexConstituents', 'IndexHistorical', 'IndexInfo', 'IndexSearch'` 的列表，总共 15 个 fetcher。

- [ ] **Step 3: Commit**

```bash
git add openbb_tushare/provider.py
git commit -m "feat: register 5 new market data fetchers in provider"
```

---

### Task 10: 构建验证

**Files:**
- All created files

- [ ] **Step 1: 运行 Python 导入检查**

验证所有新模块能被正确导入：

Run: `cd /Users/skyfu/Projects/QuantProjects/falpha/openbb_tushare && python -c "
from openbb_tushare.provider import provider
fetchers = sorted(provider.fetcher_dict.keys())
print(f'Total fetchers: {len(fetchers)}')
for f in fetchers:
    print(f'  {f}')
"`
Expected: 15 个 fetcher，包含所有新增的 5 个。

- [ ] **Step 2: 最终 commit（如有未提交的变更）**

```bash
git status
git add -A
git commit -m "feat: complete market data interfaces - IndexHistorical, IndexConstituents, IndexSearch, IndexInfo, ETFHistorical"
```
