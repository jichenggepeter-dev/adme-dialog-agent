# ADME Discovery Workspace — Agent Implementation Roadmap

## Phase 0：仓库审查

Codex 先完成：

- 读取全部 Agent 文档
- 审查 FastAPI、Single、Batch、About
- 审查 Endpoint Registry、Batch Job 和现有 Natural Language 接口
- 审查前端 root layout、测试和 Makefile
- 探测本地 LLM API

输出：

```text
docs/agent/agent-implementation-plan.md
```

不得立即实现。

## Phase 1：本地 LLM Compatibility Smoke Test

验证：

- `/v1/models`
- 普通聊天
- 单 Tool Call
- Tool Result 后继续回答
- 多工具串联
- JSON Arguments
- Multi-turn
- Streaming
- Timeout

创建：

```text
scripts/smoke_test_agent_llm.py
docs/agent/local-llm-compatibility.md
```

Tool Calling 不兼容时必须明确记录 blocker。

## Phase 2：Agent 后端基础

完成：

- OpenAI Agents SDK
- model provider
- instructions
- session store
- business state
- `/agent/sessions`
- `/agent/chat`
- 非流式回复
- tracing
- 基础测试

## Phase 3：核心 Tools

接入：

- resolve_compound
- get_compound_context
- predict_single_compound
- get_prediction_results
- explain_endpoint
- get_model_information
- get_input_quality_assessment

## Phase 4：Human-in-the-loop

完成：

- structure confirmation
- ambiguous compound
- multi-fragment warning
- confirm API
- confirmation state 和 expiry
- frontend payload schema

## Phase 5：Batch Tools

接入：

- get_batch_job_status
- summarize_batch_results
- get_batch_errors
- compare_compounds

## Phase 6：前端 Assistant

完成：

- launcher
- panel
- session
- message list
- composer
- tool activity
- confirmation card
- structured cards
- error states
- responsive

## Phase 7：跨页面 Context

完成 Single、Batch、About context，以及 root provider 和跨页面 session persistence。

## Phase 8：UI Actions

完成：

- action schema
- dispatcher
- direct reversible actions
- confirmation-required actions
- trace logging
- error handling

## Phase 9：Guardrails

完成：

- input guardrail
- tool guardrail
- output guardrail
- mock mode language
- scientific language gating
- forbidden phrase checks

## Phase 10：Tracing and Observability

完成：

- trace schema
- redaction
- large-result summarization
- tool latency
- token usage
- error categories
- activity view

## Phase 11：Evaluation

完成：

- eval cases
- tool selection tests
- multi-turn tests
- confirmation tests
- scientific integrity tests
- error recovery
- frontend E2E
- cross-page E2E

## Phase 12：文档与交付

更新：

- README
- `.env.example`
- testing guide
- Agent architecture
- Tool reference
- Safety reference
- Local LLM troubleshooting

## 总体验收

- 本地 LLM Tool Calling 兼容性有明确结论
- 三页 Assistant 可用
- 跨页面会话保持
- 名称解析后必须确认
- 现有确定性服务被复用
- Tool 调用正确
- UI Actions 白名单化
- 科学 Guardrails 生效
- Mock / Real 不混淆
- Tracing 可用
- 后端测试通过
- 前端 lint、typecheck、test、build 通过
- 核心 E2E 通过
- 不部署
