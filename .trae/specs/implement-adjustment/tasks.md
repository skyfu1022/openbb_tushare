# Tasks

## 任务列表

- [ ] Task 1: 在 TushareEquityHistoricalQueryParams 中添加 adjustment 参数
  - [ ] SubTask 1.1: 在 `openbb_tushare/models/equity_historical.py` 中添加 adjustment 字段定义
  - [ ] SubTask 1.2: 验证参数定义符合用户要求（Literal["qfq", "hfq"]，默认 None）
  - [ ] SubTask 1.3: 添加字段描述文档

- [ ] Task 2: 修改 TushareEquityHistoricalFetcher.extract_data() 方法
  - [ ] SubTask 2.1: 在 extract_data 方法中获取 adjustment 参数
  - [ ] SubTask 2.2: 将 adjustment 参数传递给 get_from_cache 函数
  - [ ] SubTask 2.3: 处理参数转换（None → ""，"qfq" → "qfq"，"hfq" → "hfq"）

- [ ] Task 3: 修改 get_from_cache 函数支持复权参数
  - [ ] SubTask 3.1: 在函数签名中添加 adjust 参数
  - [ ] SubTask 3.2: 根据复权类型修改缓存表名（添加 _qfq 或 _hfq 后缀）
  - [ ] SubTask 3.3: 将 adjust 参数传递给 get_one 函数
  - [ ] SubTask 3.4: 更新函数文档字符串

- [ ] Task 4: 修改 get_one 函数根据复权类型选择不同 API
  - [ ] SubTask 4.1: 在函数签名中添加 adjust 参数
  - [ ] SubTask 4.2: 判断市场类型（A股 vs 港股）
  - [ ] SubTask 4.3: 判断复权类型（复权 vs 不复权）
  - [ ] SubTask 4.4: A股不复权：使用 `pro.daily()` 接口
  - [ ] SubTask 4.5: A股复权：使用 `ts.pro_bar()` 接口，设置 `adj` 参数
  - [ ] SubTask 4.6: 港股不复权：使用 `pro.hk_daily()` 接口
  - [ ] SubTask 4.7: 港股复权：使用 `pro.hk_daily_adj()` 接口
  - [ ] SubTask 4.8: 处理 `ts.pro_bar()` 和 `pro.hk_daily_adj()` 返回的数据格式，确保字段名称一致
  - [ ] SubTask 4.9: 更新函数文档字符串

- [ ] Task 5: 更新 check_cache 函数支持复权参数
  - [ ] SubTask 5.1: 在函数签名中添加 adjust 参数
  - [ ] SubTask 5.2: 根据复权类型修改缓存表名
  - [ ] SubTask 5.3: 将 adjust 参数传递给 get_one 函数

- [ ] Task 6: 编写单元测试
  - [ ] SubTask 6.1: 创建测试文件 `tests/test_equity_historical_adjustment.py`
  - [ ] SubTask 6.2: 测试 A 股前复权数据获取（adjustment="qfq"）
  - [ ] SubTask 6.3: 测试 A 股后复权数据获取（adjustment="hfq"）
  - [ ] SubTask 6.4: 测试 A 股不复权数据获取（adjustment=None）
  - [ ] SubTask 6.5: 测试港股前复权数据获取（adjustment="qfq"）
  - [ ] SubTask 6.6: 测试港股后复权数据获取（adjustment="hfq"）
  - [ ] SubTask 6.7: 测试港股不复权数据获取（adjustment=None）
  - [ ] SubTask 6.8: 测试缓存表名生成逻辑

- [ ] Task 7: 更新文档和注释
  - [ ] SubTask 7.1: 更新 `equity_historical.py` 的模块文档字符串
  - [ ] SubTask 7.2: 更新 README.md（如果存在）
  - [ ] SubTask 7.3: 添加使用示例到文档中

- [ ] Task 8: 验证和测试
  - [ ] SubTask 8.1: 运行所有现有测试，确保向后兼容性
  - [ ] SubTask 8.2: 手动测试 A 股复权功能（前复权和后复权）
  - [ ] SubTask 8.3: 手动测试港股复权功能（前复权和后复权）
  - [ ] SubTask 8.4: 手动测试 A 股不复权数据获取
  - [ ] SubTask 8.5: 手动测试港股不复权数据获取
  - [ ] SubTask 8.6: 验证缓存功能正常工作

## Task Dependencies

- Task 2 依赖于 Task 1（需要先定义参数）
- Task 3 依赖于 Task 2（extract_data 调用 get_from_cache）
- Task 4 依赖于 Task 3（get_from_cache 调用 get_one）
- Task 5 依赖于 Task 3（check_cache 被 get_from_cache 调用）
- Task 6 依赖于 Task 1-5（需要实现完成后才能测试）
- Task 7 可以与 Task 6 并行进行
- Task 8 依赖于所有其他任务完成

## Implementation Order

建议的实现顺序：

1. **Phase 1: 参数定义** (Task 1)
   - 添加 adjustment 参数到 QueryParams

2. **Phase 2: 核心功能实现** (Task 2, 3, 4, 5)
   - 修改数据获取流程，支持复权参数传递
   - 更新 API 调用逻辑

3. **Phase 3: 测试和验证** (Task 6, 8)
   - 编写单元测试
   - 运行集成测试
   - 验证功能正确性

4. **Phase 4: 文档更新** (Task 7)
   - 更新文档和注释
   - 添加使用示例

## Estimated Effort

- Task 1: 15 分钟
- Task 2: 20 分钟
- Task 3: 30 分钟
- Task 4: 45 分钟（核心任务，需要仔细处理）
- Task 5: 15 分钟
- Task 6: 60 分钟
- Task 7: 20 分钟
- Task 8: 30 分钟

**总计**: 约 4 小时

## Risk Assessment

### 高风险项
- Task 4: 修改核心数据获取逻辑，需要确保不影响现有功能
- Task 6: 测试覆盖率需要充分，特别是边界情况

### 中风险项
- Task 3: 缓存表名修改可能影响现有缓存数据

### 低风险项
- Task 1, 2, 5, 7: 相对简单的修改

## Success Criteria

- [ ] 所有单元测试通过
- [ ] 向后兼容性测试通过（不指定 adjustment 参数时行为不变）
- [ ] A 股复权功能正常工作（前复权和后复权）
- [ ] 港股复权功能正常工作（前复权和后复权）
- [ ] A 股不复权数据获取正常工作
- [ ] 港股不复权数据获取正常工作
- [ ] 缓存功能正常工作
- [ ] 代码符合项目规范（通过 lint 和 typecheck）
