# ADME Discovery Workspace — Conversational Agent 文档包

## 目标

本目录用于指导现有 ADME Discovery Workspace 从“科学工作台”升级为“具备多轮对话、工具调用、页面上下文和安全边界的 ADME 对话 Agent”。

当前产品已经包含：

- Single Molecule
- Batch Screening
- Model Information
- PubChem 化合物解析
- RDKit 结构校验、标准化与 2D depiction
- ADMET-AI 单分子与批量预测
- Endpoint Registry
- Mock / Real prediction mode
- Next.js 前端
- FastAPI 后端

本次升级新增：

- OpenAI Agents SDK 编排层
- 跨页面统一会话
- 结构化业务状态
- 工具调用
- Human-in-the-loop
- 右下角浮动 ADME Assistant
- 受限 UI Actions
- Guardrails
- Tracing
- Agent Evaluation

## 本地 LLM 配置

本地 OpenAI-compatible API：

```text
http://127.0.0.1:18080/v1
```

推荐环境变量：

```env
AGENT_LLM_BASE_URL=http://127.0.0.1:18080/v1
AGENT_LLM_API_KEY=local-dev-key
AGENT_LLM_MODEL=<served-codex-model-id>
```

不要在代码中硬编码 API key 或模型名。如本地服务支持 `GET /v1/models`，实施前先探测实际模型 ID。

## 文档列表

1. `01_conversational-agent-product-spec.md`：产品目标、用户、范围、交互和验收标准
2. `02_agent-architecture.md`：架构、状态、API、会话和 Tracing
3. `03_agent-tool-contracts.md`：Agent Tools 契约
4. `04_agent-safety-and-evaluation.md`：Guardrails、科学完整性与评估
5. `05_agent-frontend-assistant-spec.md`：浮动 Assistant 与 UI Actions
6. `06_agent-implementation-roadmap.md`：工程实施路线
7. `07_codex-execution-prompt.md`：交给 Codex 的执行 Prompt

## 推荐使用方式

第一步让 Codex 只审查、不实现，生成基于真实仓库的：

```text
docs/agent/agent-implementation-plan.md
```

第二步审核计划后，再按 Phase 分阶段实施。不建议第一次就要求 Codex 一次完成全部 Agent 功能。
