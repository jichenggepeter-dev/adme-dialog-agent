# ADME Discovery Workspace — Frontend Assistant Specification

## 1. 产品形态

在 `/single`、`/batch`、`/about` 三页右下角提供统一的 `ADME Assistant` 入口。

不新增独立 Chat 页面作为主入口。

## 2. 收起状态

建议：

- 分子节点图标
- `ADME Assistant`
- 小型状态点
- 不使用普通客服聊天气泡
- 不遮挡主要页面操作

状态：

- Ready
- Thinking
- Tool running
- Confirmation needed
- Offline

## 3. 展开状态

### 桌面

- 右侧面板
- 400–460px
- 覆盖或轻微压缩页面
- 保持当前页面可见
- 支持关闭
- 支持 New Conversation
- 支持 View Activity

### 移动

- 全屏 sheet
- 保留返回页面按钮
- 输入框保持可用
- 消息卡片单列

## 4. 跨页面保持

Assistant Provider 放在根 layout。

切换路由时保留：

- session_id
- messages
- pending confirmation
- business state
- panel open/closed state

页面上下文随路由变化更新，但不清空会话。

## 5. 消息类型

### Text Message

用于解释、提问、错误和引导。

### Tool Activity

显示简化步骤：

```text
Resolving compound…
Checking structure…
Running ADMET prediction…
Loading endpoint metadata…
```

默认不展示 raw tool JSON，提供 `View Activity`。

### Compound Confirmation Card

包含：

- 2D structure
- name
- CID
- formula
- molecular weight
- canonical SMILES
- warnings
- Confirm / Change / Cancel

### Prediction Summary Card

包含：

- compound
- prediction mode
- model status
- grouped categories
- warnings
- Open in Single Molecule

### Endpoint Explanation Card

包含：

- raw endpoint
- display name
- category
- output type
- unit
- metadata status
- interpretation limitations
- Open in Model Information

### Batch Job Card

包含：

- job ID
- status
- progress
- valid / invalid / failed
- Open Batch Job

### Comparison Card

包含：

- selected compounds
- selected endpoints
- neutral differences
- Open Comparison

### Confirmation Card

适用于：

- run prediction
- run batch
- cancel batch
- clear session
- multi-fragment choice

## 6. Page Context Provider

每个页面只提供精简 context。不得把完整 raw result 或整张 batch 表直接塞入 message。

## 7. UI Action Dispatcher

Agent 返回：

```json
{
  "type": "select_endpoint",
  "payload": {
    "endpoint": "DILI"
  }
}
```

前端 dispatcher 只允许白名单动作。

可直接执行：

- navigate
- populate_single_input
- select_endpoint
- open_model_endpoint
- open_compound_detail
- open_batch_job
- select_compound
- set_batch_filter
- focus_result_section

需要确认：

- run_prediction
- run_batch
- cancel_batch
- clear_session
- replace_file

## 8. 主动改变页面状态

已确认允许，但必须满足：

- Action 来自白名单
- Payload 通过 Zod/TypeScript Schema 验证
- 无法识别的 action 忽略并记录
- 页面不存在目标对象时显示错误
- 有副作用 action 不得静默执行
- 每个 action 记录 trace

## 9. Composer

支持：

- Enter 发送
- Shift+Enter 换行
- Stop generation
- Retry
- 清晰 placeholder

建议：

```text
Ask about the current compound, endpoint, or batch job…
```

## 10. Empty State Suggestions

### Single

- Predict aspirin
- Explain the selected endpoint
- Show toxicity results
- Compare with ibuprofen

### Batch

- Summarize this batch
- List failed rows
- Compare selected compounds
- Explain the current filter

### About

- Explain this endpoint
- What does regression mean
- Which metadata is unverified
- Explain mock vs real mode

## 11. 可访问性

- Launcher 有 accessible name
- Panel 使用 dialog/region 语义
- Focus trap 合理
- ESC 关闭
- 打开后焦点进入输入框
- 关闭后焦点返回 launcher
- Tool 状态使用 aria-live
- Confirmation 可键盘操作
- 不用颜色单独表示状态
- 支持 reduced motion

## 12. 错误状态

- LLM unavailable
- Agent API unavailable
- Session expired
- Tool timeout
- Backend unavailable
- Confirmation expired
- Invalid UI Action

错误不得清空已有会话。

## 13. 性能

- Assistant 代码 lazy-load
- 不阻塞主页面
- 不重复拉取全量 batch
- Tool 大数据使用 resource ID
- 避免频繁 page context 更新
- Streaming 时避免过度重渲染
