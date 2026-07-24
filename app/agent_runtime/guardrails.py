from __future__ import annotations

import re
from typing import Any
from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    code: str | None = None
    response: str | None = None


CAPABILITY_PATTERNS = {
    "clinical": [
        r"\b(patient|dose|dosage|prescrib|diagnos|treat(?:ment)?|can i take|safe for me)\b",
        r"患者|剂量|服用|治疗|诊断|临床建议",
    ],
    "arbitrary_execution": [
        r"\b(shell|terminal|bash|zsh|subprocess|read (?:my |the )?file|local file|filesystem)\b",
        r"任意.*(?:文件|shell|终端)|读取.*本地文件|执行命令",
    ],
    "registry_mutation": [
        r"\b(?:edit|modify|overwrite|delete|update)\b.{0,30}\bendpoint registry\b",
        r"修改.*(?:registry|端点注册表)|删除.*(?:registry|端点)",
    ],
    "prompt_injection": [
        r"\b(ignore|override|reveal)\b.{0,30}\b(previous|system|developer|instructions|prompt)\b",
        r"忽略.*(?:系统|之前).*指令|覆盖.*(?:系统|开发者).*指令",
    ],
}


def evaluate_input(message: str) -> PolicyDecision:
    normalized = " ".join(message.strip().lower().split())
    for capability, patterns in CAPABILITY_PATTERNS.items():
        if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in patterns):
            if capability == "clinical":
                return PolicyDecision(
                    False,
                    "OUT_OF_SCOPE",
                    "This workspace provides computational research predictions only and cannot provide patient, dosing, treatment, or clinical advice.",
                )
            return PolicyDecision(
                False,
                "ACTION_NOT_ALLOWED",
                "That request is outside the Agent's allowlisted scientific capabilities.",
            )
    return PolicyDecision(True)


FORBIDDEN_CLAIM_PATTERNS = [
    r"\bclinically proven\b",
    r"\bdefinitely toxic\b",
    r"\bguaranteed\b",
    r"\bno risk\b",
    r"\bbest compound\b",
    r"\bsuitable for patients\b",
    r"\b(?:safer|better|best|worst)\s+(?:compound|molecule|candidate|drug)\b",
    r"\b(?:compound|molecule|candidate|drug)\s+(?:is|appears|looks)\s+(?:safer|better|best|worst)\b",
    r"\b(?:experimental(?:ly)? (?:measured|confirmed)|clinical evidence)\b",
    r"\b(?:zero|no) (?:toxicity|hazard|risk)\b",
]


def validate_output(text: str) -> PolicyDecision:
    normalized = " ".join(text.lower().split())
    if any(re.search(pattern, normalized) for pattern in FORBIDDEN_CLAIM_PATTERNS):
        return PolicyDecision(
            False,
            "SCIENTIFIC_POLICY_VIOLATION",
            "The response was blocked because it exceeded the scientific interpretation policy.",
        )
    return PolicyDecision(True)


def validate_scientific_output(
    text: str, structured_payloads: list[dict[str, Any]]
) -> PolicyDecision:
    """Fail closed when prose claims more than sanitized tool facts support."""
    base = validate_output(text)
    if not base.allowed:
        return base
    normalized = " ".join(text.lower().split())
    facts = list(_scientific_facts(structured_payloads))
    modes = {str(item.get("prediction_mode", "")).lower() for item in facts}
    if "mock" in modes and re.search(r"\b(?:real admet-ai|real model|admet-ai output)\b", normalized):
        return _scientific_block()
    if re.search(r"\b(?:measured|observed|experimentally determined)\b", normalized):
        return _scientific_block()
    if re.search(r"\b\d+(?:\.\d+)?\s*%", normalized) and not any(
        item.get("supports_probability_language") for item in facts
    ):
        return _scientific_block()
    mentioned_units = re.findall(
        r"\b(?:mg/kg|ml/min/kg|l/kg|hours?|cm/s|mol/l|µm|um|nm)\b", normalized
    )
    verified_units = {
        str(item.get("unit", "")).lower()
        for item in facts
        if item.get("unit_verified") is True and item.get("unit")
    }
    if mentioned_units and any(
        not any(_unit_matches(unit, verified) for verified in verified_units)
        for unit in mentioned_units
    ):
        return _scientific_block()
    if re.search(r"\b(?:positive class|negative class) (?:means|indicates|is)\b", normalized):
        if not any(item.get("positive_class") for item in facts):
            return _scientific_block()
    return PolicyDecision(True)


def _unit_matches(mentioned: str, verified: str) -> bool:
    normalized_mentioned = mentioned.lower().replace("hours", "h").replace("hour", "h")
    normalized_verified = verified.lower().replace("hours", "h").replace("hour", "h")
    return (
        normalized_mentioned == normalized_verified
        or normalized_mentioned in normalized_verified
    )


def _scientific_facts(payloads: list[dict[str, Any]]):
    for payload in payloads:
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            continue
        yield data
        enriched = data.get("enriched_predictions") or {}
        if isinstance(enriched, dict):
            for entries in enriched.values():
                if isinstance(entries, list):
                    yield from (entry for entry in entries if isinstance(entry, dict))


def _scientific_block() -> PolicyDecision:
    return PolicyDecision(
        False,
        "SCIENTIFIC_POLICY_VIOLATION",
        "I could not safely present that interpretation. Review the structured computational predictions and verified endpoint metadata; experimental validation is required.",
    )
