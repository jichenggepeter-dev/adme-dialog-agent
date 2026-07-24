# ADME Discovery Workspace — Conversational Agent 产品规格

## 1. 项目背景

现有产品包含：

- `/single`：单分子解析、结构确认、预测和导出
- `/batch`：数据集上传、校验、批量预测、筛选和比较
- `/about`：模型信息、Endpoint Registry、来源与限制

当前交互主要是固定工作流：

```text
用户操作页面控件
→ 前端调用固定 API
→ 后端执行确定性服务
→ 页面展示结果
```

这已经是较完整的科学工作台，但还缺少自然语言意图理解、动态工具选择、多轮上下文、跨页面会话、Human-in-the-loop、Guardrails 和 Tracing。

## 2. 产品目标

新增嵌入三页工作台的 **ADME Assistant**，使其能够：

1. 理解用户的自然语言目标
2. 读取当前页面的精简上下文
3. 调用现有确定性工具
4. 记住当前分子、预测、Endpoint 和 Batch Job
5. 支持跨页面连续会话
6. 在关键操作前要求确认
7. 解释模型结果但不越过科学边界
8. 通过受限 UI Action 改变页面状态
9. 保留工具调用和回答的可追溯记录

## 3. 产品定位

ADME Assistant 是现有科学工作台的自然语言操作层、解释层和工具编排层。

它不是：

- 通用聊天机器人
- 医疗诊断系统
- 临床或监管决策系统
- 自动药物设计平台

## 4. 目标用户与场景

### Medicinal Chemist

- 帮我预测 aspirin 的 ADME
- 只看它的代谢结果
- 再和 ibuprofen 比较

### Computational Chemist

- 这个 endpoint 是 regression 还是 classification probability
- 哪些字段 metadata 未验证
- 当前是不是 mock

### DMPK Scientist

- clearance 的单位是否验证
- 哪些值不能直接解释成概率
- 输入是否存在 applicability warning

### 项目负责人

- 当前 batch 有多少失败
- 比较当前选中的两个分子
- 总结 batch，但不要自动排名

## 5. 核心流程

### 名称预测

```text
用户：帮我预测 aspirin 的 ADME
→ Agent 调用 resolve_compound
→ 展示结构确认卡
→ 用户确认
→ Agent 调用 predict_single_compound
→ 返回结果摘要
```

### 多轮追问

```text
用户：只看它的 toxicity
→ Agent 从业务状态识别“它”指 aspirin
→ 调用 get_prediction_results
```

### Batch 查询

```text
用户：刚才那个 batch 哪些行失败
→ Agent 从会话找到 job_id
→ 调用 get_batch_errors
```

## 6. 已确认的产品决策

### 跨页面统一会话

必须支持。切换 `/single`、`/batch`、`/about` 后，Assistant 保留同一会话和业务状态。

### 结构确认

必须确认。名称、CID、歧义结果、多 fragment 和盐结构不得直接预测。

### Assistant 改变页面状态

允许，但只能通过白名单 UI Action Schema。

可直接执行的可逆动作：

- 导航
- 打开详情
- 选择 endpoint
- 填充输入
- 应用筛选
- 聚焦结果区域

有副作用动作必须确认：

- 启动真实预测
- 启动或取消 batch
- 覆盖文件
- 清空会话
- 删除本地任务数据

## 7. 前端形态

三个页面右下角统一提供 `ADME Assistant`。

桌面端：400–460px 右侧面板。  
移动端：全屏或接近全屏 sheet。

页面继续负责表单、上传、表格、结构、筛选和导出；Assistant 负责理解、工具调用、解释、多轮上下文和页面联动。

## 8. 第一版支持的意图

- `resolve_compound`
- `predict_single`
- `explain_current_prediction`
- `explain_endpoint`
- `compare_compounds`
- `get_batch_status`
- `summarize_batch`
- `list_batch_errors`
- `explain_model`
- `explain_prediction_mode`
- `export_guidance`
- `general_help`
- `out_of_scope`

## 9. 非目标

第一版不做：

- 分子生成、Docking、靶点预测、合成路线
- Multi-Agent
- 自动修改 Endpoint Registry
- 自动科学阈值和最佳候选排名
- 临床建议
- 公网部署、账号和权限
- 任意 Shell 或文件访问
- Agent 自我修改科学规则

## 10. 验收标准

- 三页均有 Assistant
- 会话跨页面保持
- 结构确认不可绕过
- 能调用 Single、Batch、Endpoint 和 Model 工具
- 能记住当前分子和 job
- 能解释选中 endpoint
- 能列出 batch 错误
- 能比较 2–5 个已预测分子
- UI Actions 白名单化
- 不编造单位、概率、方向或临床结论
- 工具调用可追踪
- 核心 E2E 通过
