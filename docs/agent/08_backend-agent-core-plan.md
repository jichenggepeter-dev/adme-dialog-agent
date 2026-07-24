# ADME Conversational Agent — Backend Core Implementation Plan

Implementation status: completed on 2026-07-12 and awaiting human review. Frontend work has not started.

## 0. Phase 1 审查结论

Phase 1 通过，可以进入后端 Agent 核心实施。

已验证：

- `OpenAIResponsesModel` 可连接 `http://127.0.0.1:18080/v1`
- 显式模型 `gpt-5.4` 可用
- strict function tool、JSON arguments、tool continuation、tool error continuation、多轮和 timeout mapping 均通过
- OpenAI-hosted tracing 已关闭，本地 audit logging 保留
- Python 3.11.14 与 3.13.5 SDK smoke 通过
- Backend `48 passed, 1 skipped`
- Frontend lint、typecheck、17 tests 通过

进入下一阶段前，必须修正文档中的陈旧信息：

- 当前 `.venv` 已是 Python 3.11.14
- `openai` 与 `openai-agents` 已安装并固定版本
- SDK-level compatibility 已确认，不再是 blocker
- `admet-ai` 若仍未安装，应继续标为真实模型未验证
- `AGENT_LLM_MODEL` 必须显式配置，不允许代码内隐藏 fallback

## 1. 后端核心目标

完成前端 Assistant 之前所需的全部后端能力：

1. 中立预测服务
2. 输入质量检查
3. 严格 Agent contracts
4. SQLite 会话与业务状态
5. Confirmation state machine
6. Resource store
7. Typed scientific tools
8. Guardrails
9. 单 Agent runtime
10. 非流式 `/agent/*` API
11. 本地 audit logging 与 redaction
12. 后端测试和文档

不包括：前端 Assistant、SSE streaming、Multi-Agent、MCP、Shell/File/Web tools、部署。

## 2. 推荐模块结构

```text
app/
├── agent.py                         # 旧规则式 handler，保留
├── agent_runtime/
│   ├── provider.py
│   ├── contracts.py
│   ├── errors.py
│   ├── instructions.py
│   ├── runtime.py
│   ├── tools.py
│   ├── guardrails.py
│   ├── state.py
│   ├── repositories.py
│   ├── confirmations.py
│   ├── resources.py
│   ├── audit.py
│   └── routes.py
└── services/
    ├── prediction.py
    ├── input_quality.py
    └── comparison.py
```

不得删除或重命名 `app/agent.py`。

## 3. Milestone A — 基线和回滚

- 修正文档中的 Phase 1 陈旧信息
- 记录 Python、SDK、ADMET-AI、feature flag 状态
- 建立 Git baseline commit；若不初始化 Git，则创建项目外部时间戳备份
- 重跑 backend、frontend lint、typecheck、tests

验收：文档一致、基线记录完整、有回滚点、无行为变化。

## 4. Milestone B — 中立确定性服务

### 4.1 `app/services/prediction.py`

职责：

- 接收 canonical SMILES 或内部 confirmed compound reference
- 复用现有 validator、predictor、formatter、endpoint enrichment
- 保留 raw output、model metadata、mock/real、warnings、disclaimer
- 返回 typed result 和 stable errors
- 不包含 chat 文案或 LLM 逻辑

旧 `/predict`、旧 `/chat` 和未来 Agent Tool 都应调用该 service，外部 contract 保持兼容。

### 4.2 `app/services/input_quality.py`

使用 RDKit 确定性计算：

- parse status
- fragment count
- heavy atom count
- molecular weight
- total formal charge
- metal presence
- unusual elements
- disconnected-component/mixture warning
- configured size warning

明确：这不是统计学 applicability-domain score；模型能输出数值不代表可靠。

### 4.3 `app/services/comparison.py`

- 只比较相同 raw endpoint
- 保留 output type、unit、metadata status
- Registry 未验证方向时不解释好坏
- 不排名、不选 winner、不做 composite score

## 5. Milestone C — Contracts 与错误模型

严格 Pydantic contracts：

- `AgentSession`
- `AgentMessage`
- `AgentChatRequest/Response`
- `SinglePageContext`
- `BatchPageContext`
- `AboutPageContext`
- `CompoundConfirmation`
- `PendingAction`
- `ToolResultEnvelope`
- Structured payload union
- UIAction discriminated union
- Resource contracts

稳定错误至少包括：

- `AGENT_NOT_CONFIGURED`
- `AGENT_PROVIDER_UNAVAILABLE`
- `AGENT_PROVIDER_INCOMPATIBLE`
- `AGENT_TIMEOUT`
- `SESSION_NOT_FOUND`
- `SESSION_EXPIRED`
- `CONFIRMATION_REQUIRED`
- `CONFIRMATION_EXPIRED`
- `CONFIRMATION_REPLAYED`
- `ACTION_NOT_ALLOWED`
- `ACTION_STALE`
- `RESOURCE_NOT_FOUND`
- `TOOL_FAILED`
- `TOOL_RESULT_INVALID`
- `SCIENTIFIC_POLICY_VIOLATION`
- `INTERNAL_ERROR`

不得暴露 traceback。

## 6. Milestone D — SQLite 状态、确认与资源

建议表：

- `agent_sessions`
- `agent_messages`
- `agent_business_state`
- `agent_confirmations`
- `agent_pending_actions`
- `agent_resources`
- `agent_audit_events`

业务状态与聊天历史分离，保存：

- current page
- current/confirmed compound references
- latest prediction resource
- current batch job
- selected endpoint/compounds
- pending confirmation/action
- state version

Confirmation 状态机：

```text
proposed
→ awaiting_confirmation
→ approved
→ executing
→ succeeded | failed

terminal:
rejected | expired | superseded
```

要求：单次使用、expiry、payload hash 绑定、canonical SMILES 匹配、optimistic version、replay protection、cross-session rejection。

Resource store：类型、owner session、hash、size limit、TTL、bounded retrieval。不得变成通用文件接口。

## 7. Milestone E — Typed Agent Tools

初始工具：

- `resolve_compound`
- `get_compound_context`
- `get_input_quality_assessment`
- `predict_single_compound`
- `get_prediction_results`
- `explain_endpoint`
- `get_model_information`
- `get_batch_job_status`
- `get_batch_errors`
- `summarize_batch_results`
- `compare_compounds`

规则：

- 仅做确定性 service 的薄包装
- strict inputs
- compact JSON-safe outputs
- 大结果用 resource ID
- 保留 provenance 和 metadata status
- confirmed compound 才能预测
- compare 仅 2–5 个
- 不排名、不自动 winner
- 不提供 Shell/File/Web/MCP/Code tools
- 不修改 Registry
- 初始阶段不暴露 run/cancel batch 和外部 export

## 8. Milestone F — Instructions 与 Guardrails

Agent 必须：

- 只通过工具获得应用事实
- 不计算或编造 ADMET 值
- 不编造单位、阈值、positive class、directionality
- 不把预测称为测量
- 不给临床、剂量、患者或监管结论
- 不绕过结构确认
- 不自动排名最佳分子
- 明确 mock mode
- Registry 未验证时诚实说明

Guardrails 覆盖：

- 临床请求
- Prompt injection
- Shell/File/Network 请求
- Registry mutation
- Skip-confirmation
- Tool result poisoning
- Mock/Real 混淆
- 未验证概率语言

不能只靠字符串黑名单，应结合结构化事实与最终输出校验。

## 9. Milestone G — 单 Agent Runtime

- 一个 Agent
- 无 handoff
- 无 agents-as-tools
- 无 MCP/hosted tools
- 非流式
- 限制 max turns/tool calls
- provider timeout/error mapping
- hosted tracing off
- local audit logging on
- 普通测试使用 fake provider/model

关键流程：

```text
用户要求预测
→ resolve_compound
→ 创建 pending structure confirmation
→ 返回 confirmation payload
→ 停止

用户确认
→ 校验 confirmation
→ predict_single_compound
→ 保存 prediction resource
→ 返回 summary
```

禁止在未确认的同一轮直接预测。

## 10. Milestone H — 非流式 Agent API

新增：

```http
POST /agent/sessions
GET  /agent/sessions/{session_id}
GET  /agent/sessions/{session_id}/messages
POST /agent/chat
POST /agent/confirm
GET  /agent/resources/{resource_id}
```

要求：

- `AGENT_ENABLED=false` 时现有应用正常启动
- 旧 `/chat` 保留
- Agent route 返回稳定 disabled/not-configured error
- typed page context 与 expected state version
- response 包含 text、structured payload、pending confirmation、tool activity、UI action proposals、warnings、state version
- confirmation replay 明确拒绝或按 contract 幂等处理
- 不增加 streaming route

## 11. Milestone I — 测试与文档

必须测试：

- name/CID/SMILES 均停在 confirmation
- valid SMILES 仍需 confirmation
- confirmed compound 才能预测
- rejected/expired/replayed confirmation 不得预测
- unknown endpoint metadata 中性解释
- mock mode 明确标识
- tool error 不产生幻觉事实
- clinical request 保持 out of scope
- Shell/File prompt injection 无法获得工具
- compare 1 个或 6 个被拒绝
- provider outage 返回稳定错误
- Agent disabled 不影响现有 API
- 现有科学输出无 regression

文档：

- `backend-core-architecture.md`
- `backend-api.md`
- `session-and-confirmation.md`
- `tool-reference.md`
- `safety-and-audit.md`
- `backend-core-test-report.md`

## 12. 总体验收

后端核心完成时必须满足：

- 中立 prediction service 完成
- 旧 `/predict`、`/chat` contract 保持
- input quality helper 为确定性规则
- contracts 严格
- SQLite conversation/business state 分离
- confirmation 原子、过期、单次、可防重放
- resource storage bounded
- typed allowlisted tools 完成
- 未确认不得预测
- Registry 驱动 endpoint explanation
- 单 Agent runtime 可用
- 本地 `gpt-5.4` opt-in integration 通过
- 非流式 `/agent/*` API 可用
- Agent disabled 不影响现有产品
- Guardrails 与 redaction 通过
- Backend tests 全部通过
- 现有 frontend lint/typecheck/tests 不受影响
- 不实现前端 Assistant
- 不实现 streaming
- 不部署
