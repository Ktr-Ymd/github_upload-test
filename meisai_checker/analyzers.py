from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Suggestion:
    id: str
    category: str
    severity: str
    message: str
    location: Dict[str, int]  # {paragraph_index, start, end}
    suggested_fix: Optional[str] = None
    evidence: Optional[str] = None
    autofix: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "location": self.location,
            "suggested_fix": self.suggested_fix,
            "evidence": self.evidence,
            "autofix": self.autofix,
        }


def heuristic_checks(lines: List[str]) -> List[Suggestion]:
    suggestions: List[Suggestion] = []
    sid = 1

    # 1) 連続句読点
    patt = re.compile(r"[。、]{2,}")
    for i, line in enumerate(lines):
        for m in patt.finditer(line):
            s = Suggestion(
                id=f"H-{sid:04d}",
                category="typo",
                severity="low",
                message="句読点が連続しています",
                location={"paragraph_index": i, "start": m.start(), "end": m.end()},
                suggested_fix=re.sub(r"[。、]{2,}", lambda _: _.group(0)[0], m.group(0)),
                autofix=False,
            )
            suggestions.append(s)
            sid += 1

    # 2) 括弧不一致（簡易）
    pairs = {"(": ")", "（": "）", "[": "]", "「": "」"}
    for i, line in enumerate(lines):
        for op, cl in pairs.items():
            if line.count(op) != line.count(cl):
                suggestions.append(
                    Suggestion(
                        id=f"H-{sid:04d}",
                        category="style",
                        severity="medium",
                        message=f"括弧の数が一致しません: {op}{cl}",
                        location={"paragraph_index": i, "start": 0, "end": max(0, len(line) - 1)},
                    )
                )
                sid += 1

    # 3) 余分な空白（全角直後の半角スペースなど）
    extra_space = re.compile(r"([ぁ-んァ-ヶ一-龥））」》】・])\s+([ぁ-んァ-ヶ一-龥（「《【・])")
    for i, line in enumerate(lines):
        for m in extra_space.finditer(line):
            suggestions.append(
                Suggestion(
                    id=f"H-{sid:04d}",
                    category="style",
                    severity="low",
                    message="日本語間の不自然な空白",
                    location={"paragraph_index": i, "start": m.start(), "end": m.end()},
                )
            )
            sid += 1

    return suggestions


def llm_checks(text: str, guidelines_text: str, model: str, api_key: Optional[str], base_url: Optional[str]) -> List[Suggestion]:
    """Call OpenAI for enablement/support/clarity checks.
    Returns empty list when API key is missing.
    """
    if not api_key:
        return []

    from openai import OpenAI  # type: ignore

    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)

    system = (
        "あなたは日本の特許実務に精通した品質管理アシスタントです。\n"
        "ユーザーの明細書草案を、審査基準・特許法（実施可能要件・サポート要件・明確性等）\n"
        "に照らしてレビューし、条文等の根拠とともに具体的な修正案をJSONで返してください。\n"
        "必ず日本語で、locationは段落推定で十分です。"
    )

    prompt = (
        "【参照資料（抜粋可）】\n" + guidelines_text[:4000] + "\n\n"  # limit prompt size for safety
        "【明細書（抜粋可）】\n" + text[:8000] + "\n\n"
        "次のJSONスキーマの配列で返答してください。\n"
        "[{id, category, severity, message, evidence, location:{paragraph_index,start,end}, suggested_fix, autofix}]\n"
        "categoryは support|enablement|clarity|consistency 等を使用。"
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    content = resp.choices[0].message.content or "[]"
    items = _safe_json_list(content)
    out: List[Suggestion] = []
    sid = 1
    for it in items:
        try:
            out.append(
                Suggestion(
                    id=str(it.get("id") or f"L-{sid:04d}"),
                    category=str(it.get("category") or "other"),
                    severity=str(it.get("severity") or "medium"),
                    message=str(it.get("message") or ""),
                    evidence=it.get("evidence"),
                    location=dict(it.get("location") or {"paragraph_index": 0, "start": 0, "end": 0}),
                    suggested_fix=it.get("suggested_fix"),
                    autofix=bool(it.get("autofix", False)),
                )
            )
            sid += 1
        except Exception:
            continue
    return out


def _safe_json_list(s: str) -> List[Dict[str, Any]]:
    try:
        data = json.loads(s)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
    except Exception:
        pass
    return []

