# 实现复权处理功能 Spec

## Why

目前 openbb_tushare 数据提供者在获取股票历史价格时，没有处理复权的情况。这导致用户在使用该数据源时，无法获取经过前复权或后复权处理的价格数据，影响了技术分析和量化回测的准确性。

复权处理对于股票价格数据的连续性至关重要，特别是在处理分红、送股、配股等权益事件时。不进行复权处理会导致价格序列出现不连续的跳空，影响技术指标计算和收益率分析。

## What Changes

- 在 `TushareEquityHistoricalQueryParams` 中添加 `adjustment` 参数，支持 `qfq`（前复权）和 `hfq`（后复权）选项
- 修改 `get_from_cache` 函数，支持传递复权参数
- 修改 `get_one` 函数，根据复权类型选择不同的 Tushare API：
  - 不复权：A股使用 `pro.daily()`，港股使用 `pro.hk_daily()`
  - 复权：A股使用 `ts.pro_bar()`，港股使用 `pro.hk_daily_adj()`
- 更新缓存逻辑，为不同的复权类型创建独立的缓存表
- 添加单元测试，验证复权功能的正确性

## Impact

- **Affected specs**: 股票历史价格数据获取功能
- **Affected code**:
  - `openbb_tushare/models/equity_historical.py` - 添加 adjustment 参数
  - `openbb_tushare/utils/ts_equity_historical.py` - 修改数据获取逻辑
  - `tests/test_equity_historical.py` - 添加复权测试用例

## ADDED Requirements

### Requirement: 复权参数支持

系统 SHALL 在获取股票历史价格时支持复权参数。

#### Scenario: 前复权数据获取
- **WHEN** 用户指定 `adjustment="qfq"` 参数
- **THEN** 系统返回前复权处理后的历史价格数据

#### Scenario: 后复权数据获取
- **WHEN** 用户指定 `adjustment="hfq"` 参数
- **THEN** 系统返回后复权处理后的历史价格数据

#### Scenario: 不复权数据获取
- **WHEN** 用户不指定 adjustment 参数或指定为 None
- **THEN** 系统返回未复权的原始价格数据

### Requirement: 复权参数定义

系统 SHALL 使用以下参数定义：

```python
adjustment: Optional[Literal["qfq", "hfq"]] = Field(
    default=None,
    description="Adjustment type for historical prices. 'qfq' for forward-adjusted (前复权), 'hfq' for backward-adjusted (后复权). None means no adjustment.",
)
```

### Requirement: Tushare API 集成

系统 SHALL 根据复权类型选择不同的 Tushare API：

#### 不复权数据获取
- **A股**: 使用 `pro.daily()` 接口
- **港股**: 使用 `pro.hk_daily()` 接口

#### 复权数据获取
- **A股**: 使用 `ts.pro_bar()` 接口，设置 `adj` 参数
  - 前复权: `adj='qfq'`
  - 后复权: `adj='hfq'`
- **港股**: 使用 `pro.hk_daily_adj()` 接口

### Requirement: 港股复权数据处理

港股复权返回的数据包含 `adj_factor`（复权因子），复权逻辑为：
- 复权价格 = 价格 × 复权因子

因此对于港股复权数据，需要在返回前计算实际的复权价格。

### Requirement: 缓存策略

系统 SHALL 为不同的复权类型创建独立的缓存表：

- 不复权数据：使用表名 `{market}{symbol}`
- 前复权数据：使用表名 `{market}{symbol}_qfq`
- 后复权数据：使用表名 `{market}{symbol}_hfq`

### Requirement: 市场支持

系统 SHALL 对 A 股和港股市场都提供复权功能：

- A股（SH、SZ市场）：
  - 不复权：使用 `pro.daily()` 接口
  - 复权：使用 `ts.pro_bar()` 接口，设置 `adj` 参数
- 港股（HK市场）：
  - 不复权：使用 `pro.hk_daily()` 接口
  - 复权：使用 `pro.hk_daily_adj()` 接口

## MODIFIED Requirements

### Requirement: 数据获取接口

原有的 `get_from_cache` 和 `get_one` 函数 SHALL 新增 `adjust` 参数：

```python
def get_from_cache(
    ts_code: str,
    start_date: Union[dateType, str],
    end_date: Union[dateType, str],
    api_key: str = "",
    period: str = "daily",
    use_cache: bool = True,
    adjust: str = ""  # 新增参数
) -> pd.DataFrame:
```

## REMOVED Requirements

无移除的需求。

## Technical Implementation Details

### 1. 参数传递流程

```
用户请求 (adjustment="qfq")
  ↓
TushareEquityHistoricalFetcher.extract_data()
  ↓
get_from_cache(adjust="qfq")
  ↓
get_one(adjust="qfq")
  ↓
ts.pro_bar(adj="qfq")
```

### 2. Tushare API 使用

#### A股不复权
```python
# 使用 pro.daily()
df = pro.daily(ts_code='000001.SZ', start_date='20180101', end_date='20181011')
```

#### A股复权
```python
# 使用 ts.pro_bar()
# 前复权
df = ts.pro_bar(ts_code='000001.SZ', adj='qfq', start_date='20180101', end_date='20181011')
# 后复权
df = ts.pro_bar(ts_code='000001.SZ', adj='hfq', start_date='20180101', end_date='20181011')
```

#### 港股不复权
```python
# 使用 pro.hk_daily()
df = pro.hk_daily(ts_code='00001.HK', start_date='20240101', end_date='20240722')
```

#### 港股复权
```python
# 使用 pro.hk_daily_adj()
df = pro.hk_daily_adj(ts_code='00001.HK', start_date='20240101', end_date='20240722')
# 返回数据包含 adj_factor 字段，需要计算复权价格
```

### 3. 复权算法说明

#### A股复权（根据 Tushare 文档）

- **前复权**: 当日收盘价 × 当日复权因子 / 最新复权因子
- **后复权**: 当日收盘价 × 当日复权因子

#### 港股复权

- 复权价格 = 价格 × 复权因子
- `pro.hk_daily_adj()` 接口已经返回了调整后的价格（通过 `adj_factor` 计算）
- 需要注意：返回数据中 `close` 字段已经是复权后的价格

### 4. 兼容性考虑

- 保持向后兼容：不指定 adjustment 参数时，行为与之前一致
- 缓存表名需要包含复权类型，避免数据混淆

## Dependencies

- Tushare Python SDK >= 1.2.26（支持复权功能）
- 现有的 `mysharelib.table_cache` 模块
- 现有的 `mysharelib.tools.normalize_symbol` 工具函数

## References

1. Tushare A股复权文档: https://tushare.pro/document/2?doc_id=146
2. Tushare 港股复权文档: https://tushare.pro/document/2?doc_id=339
3. OpenBB 官方文档: https://docs.openbb.co/odp/python/reference/equity/price/historical
4. openbb_akshare 实现参考: `/home/sgye/s/finanalyzer/openbb_akshare/openbb_akshare/models/equity_historical.py`
5. 复权处理技能文档: `/home/sgye/s/finanalyzer/openbb_tdx/.trae/skills/openbb-data-provider/SKILL.md#L298-446`
