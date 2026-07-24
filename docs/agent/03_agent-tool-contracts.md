# ADME Discovery Workspace — Agent Tool Contracts

## 1. 总则

Agent Tool 必须是现有确定性服务的薄包装层：

```text
Agent Tool
→ Existing Service
→ PubChem / RDKit / ADMET-AI / Batch Storage
```

禁止：

- 在 Tool 中复制已有业务逻辑
- 让 LLM 直接计算 ADMET
- 让 LLM 自己猜 SMILES
- 访问任意本地路径
- 修改 Endpoint Registry
- 隐藏失败或 unknown metadata

每个 Tool 必须：

- 输入 Schema 明确
- 输出 JSON 稳定
- 错误码稳定
- 保留 Resource ID
- 不暴露 traceback
- 支持 tracing
- 保留 prediction mode 和 model metadata

## 2. `resolve_compound`

输入：

```json
{"query": "aspirin"}
```

输出：

```json
{
  "resolution_status": "resolved",
  "input": "aspirin",
  "input_type": "name",
  "compound_id": "compound_123",
  "preferred_name": "Aspirin",
  "pubchem_cid": 2244,
  "canonical_smiles": "...",
  "isomeric_smiles": "...",
  "molecular_formula": "C9H8O4",
  "molecular_weight": 180.16,
  "fragment_count": 1,
  "warnings": [],
  "requires_confirmation": true
}
```

错误码：

- `COMPOUND_NOT_FOUND`
- `COMPOUND_AMBIGUOUS`
- `PUBCHEM_UNAVAILABLE`
- `INVALID_CID`
- `INVALID_SMILES`
- `COMPOUND_RESOLUTION_FAILED`

规则：

- 名称和 CID 必须确认
- 多 fragment 必须警告
- 不自动猜盐型或异构体
- 不调用 ADMET-AI

## 3. `get_compound_context`

根据 `compound_id` 获取：

- 名称
- CID
- SMILES
- formula
- molecular weight
- depiction resource
- warnings
- confirmation status

## 4. `predict_single_compound`

输入：

```json
{
  "compound_id": "compound_123",
  "confirmed": true
}
```

输出：

```json
{
  "prediction_id": "pred_123",
  "compound_id": "compound_123",
  "status": "completed",
  "prediction_mode": "real",
  "model_name": "ADMET-AI",
  "model_version": "...",
  "raw_predictions_resource_id": "resource_123",
  "grouped_results": {},
  "warnings": [],
  "disclaimer": "..."
}
```

错误码：

- `CONFIRMATION_REQUIRED`
- `MODEL_NOT_AVAILABLE`
- `MODEL_LOAD_FAILED`
- `PREDICTION_FAILED`
- `INVALID_SMILES`
- `INPUT_OUTSIDE_SUPPORTED_SCOPE`

规则：

- 未确认结构不能调用
- 不在 Tool 内生成科学解释
- 保留 raw output
- 标注 mock / real

## 5. `get_prediction_results`

输入：

```json
{
  "prediction_id": "pred_123",
  "categories": ["toxicity"],
  "endpoints": []
}
```

返回 enriched endpoint results、grouped results、warnings 和 metadata coverage。

规则：

- metadata 未验证则保留 unverified
- 不自动把 0–1 解释成概率

## 6. `explain_endpoint`

输入：

```json
{"endpoint_name": "DILI"}
```

输出：

```json
{
  "raw_name": "DILI",
  "display_name": "Drug-induced liver injury",
  "category": "toxicity",
  "output_type": "unknown",
  "prediction_task": null,
  "positive_class": null,
  "unit": null,
  "metadata_status": "unverified",
  "description": null,
  "interpretation_note": "Exact semantics are not verified.",
  "source": null,
  "supports_probability_language": false,
  "supports_directional_language": false
}
```

规则：

- 不用模型常识替代 Registry
- 未验证就明确说未验证
- 不编造单位、概率或方向

## 7. `compare_compounds`

输入：

```json
{
  "prediction_ids": ["pred_123", "pred_456"],
  "categories": ["absorption"],
  "endpoints": []
}
```

约束：

- 至少 2 个、最多 5 个
- 必须完成预测
- 不输出 best compound
- 不输出 safe / unsafe
- 只在 unit 和 output type 可比时比较

## 8. `get_batch_job_status`

输入：

```json
{"job_id": "job_123"}
```

输出：

```json
{
  "job_id": "job_123",
  "status": "completed_with_errors",
  "prediction_mode": "real",
  "total_rows": 100,
  "valid_rows": 92,
  "unique_valid_molecules": 89,
  "completed_count": 87,
  "failed_count": 2,
  "progress": 0.9775
}
```

## 9. `summarize_batch_results`

输入：

```json
{
  "job_id": "job_123",
  "scope": "overview",
  "selected_compound_ids": [],
  "selected_endpoints": []
}
```

scope：

- `overview`
- `errors`
- `selected_compounds`
- `selected_endpoints`

规则：

- 不自动排名
- 不给最佳候选
- 不隐藏无效行
- 不把数值方向解释成好坏

## 10. `get_batch_errors`

返回：

- row number
- compound ID
- name
- input SMILES
- error code
- error message
- retry eligibility

## 11. `get_model_information`

返回：

- prediction mode
- backend version
- model name / version
- model loaded
- registry schema version
- registry coverage
- scientific limitations
- data source responsibilities

## 12. `get_input_quality_assessment`

目的：处理“怪 SMILES”的输入质量问题，而不是让 Registry 处理输入适用性。

输入：

```json
{"compound_id": "compound_123"}
```

输出：

- parse status
- fragment count
- heavy atom count
- molecular weight
- metal presence
- charge
- unusual element warnings
- size warnings
- mixture warning
- applicability warning

规则：

- “可以计算”不等于“可靠”
- 只给 input quality warning
- 不伪造统计置信区间

## 13. 大结果控制

大型 batch rows 和 raw prediction 不全部进入 Agent 上下文。

应返回：

- resource ID
- count
- selected subset
- summary
- pagination cursor
