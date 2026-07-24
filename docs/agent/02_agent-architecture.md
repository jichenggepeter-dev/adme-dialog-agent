# ADME Discovery Workspace — Agent 技术架构

## 1. 总体架构

```text
Next.js Application
├── /single
├── /batch
├── /about
└── Global ADME Assistant Panel
            ↓
FastAPI Agent API
├── /agent/sessions
├── /agent/chat
├── /agent/confirm
└── /agent/sessions/{id}/messages
            ↓
OpenAI Agents SDK
├── Instructions
├── Function Tools
├── Sessions
├── Guardrails
├── Tracing
└── Human-in-the-loop
            ↓
Existing Deterministic Services
├── Compound Resolver / PubChem
├── RDKit Validation & Depiction
├── ADMET-AI Predictor
├── Endpoint Registry
├── Batch Job Service
├── Comparison Service
└── Export Service
```

## 2. 技术选择

### Agent Framework

使用 OpenAI Agents SDK。

原因：

- 现有 Python 后端已有成熟服务
- 适合单 Agent + Function Tools
- 支持 Sessions、Guardrails、Tracing 和 Human-in-the-loop
- 不需要引入复杂 Multi-Agent 系统

### LLM Provider

使用本地 OpenAI-compatible API：

```text
http://127.0.0.1:18080/v1
```

环境变量：

```env
AGENT_LLM_BASE_URL=http://127.0.0.1:18080/v1
AGENT_LLM_API_KEY=local-dev-key
AGENT_LLM_MODEL=<served-codex-model-id>
```

模型名必须通过配置提供，不能硬编码。

### Compatibility Smoke Test

实施前必须验证本地 API 是否支持：

- `/v1/models`
- Chat Completions 或 SDK 所需接口
- Function / Tool Calling
- 结构化 JSON arguments
- Tool Result 后继续回答
- 多轮对话
- 多工具串联
- Streaming
- Timeout 和 cancellation

如果 Responses API 不兼容，应使用 SDK 支持的 Chat Completions 路径或 provider adapter。

## 3. 建议后端结构

```text
app/
├── agent/
│   ├── __init__.py
│   ├── adme_agent.py
│   ├── instructions.py
│   ├── model_provider.py
│   ├── tools.py
│   ├── tool_schemas.py
│   ├── guardrails.py
│   ├── session_store.py
│   ├── business_state.py
│   ├── ui_actions.py
│   ├── tracing.py
│   └── errors.py
├── api/
│   └── agent_routes.py
└── services/
    └── existing deterministic services
```

## 4. 建议前端结构

```text
frontend/
├── components/assistant/
│   ├── assistant-launcher.tsx
│   ├── assistant-panel.tsx
│   ├── assistant-header.tsx
│   ├── assistant-message-list.tsx
│   ├── assistant-composer.tsx
│   ├── tool-activity.tsx
│   ├── confirmation-card.tsx
│   ├── compound-card.tsx
│   ├── prediction-card.tsx
│   ├── endpoint-card.tsx
│   ├── batch-card.tsx
│   └── comparison-card.tsx
├── contexts/
│   ├── assistant-context.tsx
│   └── page-context.tsx
└── lib/
    ├── agent-api.ts
    ├── agent-types.ts
    └── ui-action-dispatcher.ts
```

## 5. 会话模型

### Conversation History

保存：

- 用户消息
- Assistant 消息
- Tool Events
- Confirmation Events

### Business State

与聊天文本分开维护：

```json
{
  "session_id": "session_123",
  "current_page": "single",
  "current_compound_id": "compound_123",
  "resolved_compounds": ["compound_123"],
  "latest_prediction_id": "pred_123",
  "current_batch_job_id": null,
  "selected_endpoint": "DILI",
  "selected_compounds": [],
  "pending_confirmation": null
}
```

不能只依赖聊天历史推断当前对象。

## 6. Page Context

### Single

```json
{
  "page": "single",
  "current_compound": {
    "name": "Aspirin",
    "pubchem_cid": 2244,
    "canonical_smiles": "..."
  },
  "prediction_id": "pred_123",
  "selected_endpoint": "DILI"
}
```

### Batch

```json
{
  "page": "batch",
  "batch_job_id": "job_123",
  "selected_compounds": [
    {"row_id": 1, "compound_id": "CMPD-001", "name": "Aspirin"}
  ],
  "active_endpoints": ["DILI"],
  "active_filters": {}
}
```

### About

```json
{
  "page": "about",
  "selected_endpoint": "BBB_Martins",
  "active_category": "distribution"
}
```

原则：

- 只传 resource ID 和精简元数据
- 不把整张 batch 表塞给模型
- 不把完整 raw output 无条件塞给模型
- 需要详细数据时调用 Tool

## 7. Agent Loop

```text
接收用户消息
→ 合并 Session 与 Page Context
→ Agent 判断是否需要 Tool
→ Tool 执行确定性服务
→ Tool Result 返回
→ Agent 判断是否继续、确认或回答
→ Guardrails 检查
→ 返回文本、Structured Payload 和 UI Actions
```

## 8. Human-in-the-loop

需要确认：

- 名称或 CID 解析后的结构
- 名称歧义
- 多 fragment 或盐处理
- 启动真实预测
- 启动或取消 batch
- 清空会话
- 覆盖文件

确认对象：

```json
{
  "confirmation_id": "confirm_123",
  "type": "compound_structure",
  "payload": {
    "compound_id": "compound_123"
  },
  "expires_at": "..."
}
```

## 9. UI Actions

Agent 不直接操作 DOM，只返回白名单 action。

```json
{
  "ui_actions": [
    {
      "type": "open_model_endpoint",
      "payload": {
        "endpoint": "DILI"
      }
    }
  ]
}
```

可直接执行：

- `navigate`
- `populate_single_input`
- `select_endpoint`
- `open_model_endpoint`
- `open_compound_detail`
- `open_batch_job`
- `select_compound`
- `set_batch_filter`
- `focus_result_section`

必须确认：

- `run_prediction`
- `run_batch`
- `cancel_batch`
- `clear_session`
- `replace_file`

## 10. Agent API

### 创建会话

```http
POST /agent/sessions
```

### 发送消息

```http
POST /agent/chat
```

请求：

```json
{
  "session_id": "session_123",
  "message": "这个 DILI 值是什么意思？",
  "page_context": {
    "page": "single",
    "prediction_id": "pred_123",
    "selected_endpoint": "DILI"
  }
}
```

响应：

```json
{
  "message_id": "msg_123",
  "response": "...",
  "structured_payload": {
    "type": "endpoint_explanation",
    "data": {}
  },
  "pending_confirmation": null,
  "tool_events": [],
  "ui_actions": [],
  "warnings": []
}
```

### 确认

```http
POST /agent/confirm
```

### 会话历史

```http
GET /agent/sessions/{session_id}/messages
```

### 流式接口

后续支持：

```http
POST /agent/chat/stream
```

建议 SSE events：

- `assistant_started`
- `tool_call_started`
- `tool_call_completed`
- `confirmation_required`
- `assistant_delta`
- `ui_action`
- `assistant_completed`
- `error`

第一阶段可先做非流式。

## 11. Tracing

每次运行记录：

- session_id
- message_id
- model
- user_message
- page_context 摘要
- tool name 与 arguments
- tool result 摘要
- tool error
- guardrail result
- confirmation event
- final response
- latency
- token usage
- UI Actions

大型结果只记录 resource ID、hash、count 和 summary，不复制全量 batch 文件。

## 12. 稳定错误码

- `AGENT_MODEL_UNAVAILABLE`
- `AGENT_TOOL_CALL_INVALID`
- `AGENT_SESSION_NOT_FOUND`
- `AGENT_CONFIRMATION_REQUIRED`
- `AGENT_CONFIRMATION_EXPIRED`
- `TOOL_TIMEOUT`
- `TOOL_RESULT_INVALID`
- `BACKEND_UNAVAILABLE`
- `OUT_OF_SCOPE`
- `INTERNAL_ERROR`

不得向前端暴露 Python traceback。
