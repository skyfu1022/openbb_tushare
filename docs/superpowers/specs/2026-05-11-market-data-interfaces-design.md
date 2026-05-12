# 行情接口完善设计文档

## 背景

openbb_tushare 是 OpenBB 平台的 Tushare 数据源扩展，为中国 A 股/港股市场提供数据。当前已实现 10 个接口（股票行情、财报、搜索等），但缺乏指数行情、成分股、ETF 行情等因子挖掘必需的数据。

## 目标

新增 5 个行情接口，覆盖指数和 ETF 的历史行情、成分股、搜索和基本信息，为因子挖掘智能体提供完整的市场数据基础。

## 新增接口

### 1. IndexHistorical — 指数历史行情

- **OpenBB 标准模型**: `IndexHistoricalQueryParams` / `IndexHistoricalData`
- **Tushare API**: `index_daily(ts_code, start_date, end_date)`
- **字段映射**: `trade_date → date`, `vol → volume`
- **扩展参数**: `use_cache`（缓存控制）
- **文件**: `models/index_historical.py` + `utils/ts_index_historical.py`
- **缓存策略**: 复用 `TableCache`，表名 `idx_{指数代码}`

### 2. IndexConstituents — 指数成分股

- **OpenBB 标准模型**: `IndexConstituentsQueryParams` / `IndexConstituentsData`
- **Tushare API**: `index_weight(index_code, start_date, end_date)`，取最新日期数据
- **字段映射**: `con_code → symbol`, `stock_name → name`
- **扩展参数**: `use_cache`（缓存控制）
- **文件**: `models/index_constituents.py` + `utils/ts_index_constituents.py`
- **注意事项**: 需将 Tushare 的 `000001.SH` 格式转为 `000001.SS`；取最新交易日的权重数据

### 3. IndexSearch — 指数搜索

- **OpenBB 标准模型**: `IndexSearchQueryParams` / `IndexSearchData`
- **数据来源**: 复用 `ts_available_indices.py` 的 `get_available_indices()`，在内存中过滤
- **字段映射**: `ts_code → symbol`
- **扩展参数**: `use_cache`
- **文件**: `models/index_search.py`（无需新 utils）
- **搜索逻辑**: 支持 `query` 模糊匹配名称/代码，`is_symbol=True` 时仅匹配代码

### 4. IndexInfo — 指数基本信息

- **OpenBB 标准模型**: `IndexInfoQueryParams` / `IndexInfoData`
- **数据来源**: 复用 `ts_available_indices.py`，按 symbol 过滤
- **字段映射**: `ts_code → symbol`, `fullname → name`, 基期/基点等信息
- **扩展参数**: `use_cache`
- **文件**: `models/index_info.py`（无需新 utils）

### 5. ETFHistorical — ETF 历史行情

- **OpenBB 标准模型**: `EtfHistoricalQueryParams` / `EtfHistoricalData`
- **Tushare API**: `fund_daily(ts_code, start_date, end_date)`
- **字段映射**: `trade_date → date`, `vol → volume`
- **扩展参数**: `use_cache`
- **文件**: `models/etf_historical.py` + `utils/ts_etf_historical.py`
- **缓存策略**: 复用 `TableCache`，表名 `etf_{基金代码}`

## 实现模式

所有接口遵循现有项目模式：

```
model 文件:
  TushareXxxQueryParams  → 继承标准 QueryParams，添加 use_cache 参数
  TushareXxxData         → 继承标准 Data，用 __alias_dict__ 映射字段
  TushareXxxFetcher      → transform_query → extract_data → transform_data

utils helper（新接口需要）:
  get_from_cache()       → 缓存检查 + Tushare API 调用
  使用 TableCache        → 本地 SQLite 缓存
  使用 get_api_key()     → 统一 API key 管理
```

## 注册变更

`provider.py` 新增 5 个 fetcher：

```python
"IndexHistorical": TushareIndexHistoricalFetcher,
"IndexConstituents": TushareIndexConstituentsFetcher,
"IndexSearch": TushareIndexSearchFetcher,
"IndexInfo": TushareIndexInfoFetcher,
"EtfHistorical": TushareEtfHistoricalFetcher,
```

## 不做的事情

- 不实现指数的实时快照（IndexSnapshots），Tushare 需要更高权限
- 不实现 ETF 的持仓/NAV 等接口，留到基本面阶段
- 不修改已有的 10 个接口
- 不修改 router.py（路由通过 fetcher_dict 自动注册）
