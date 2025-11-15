from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from .config import AppConfig
from .guidelines_loader import read_guidelines_text
from .word_io import read_docx_text, write_docx_with_replacements
from .analyzers import Suggestion, heuristic_checks, llm_checks


def run_cli() -> None:
    parser = argparse.ArgumentParser(description="明細書チェックくん: 明細書案を自動レビュー")
    parser.add_argument("input", type=Path, help="入力 .docx ファイル")
    parser.add_argument("--guidelines-dir", type=Path, default=None, help="審査基準/特許法の参照フォルダ")
    parser.add_argument("--out-dir", type=Path, default=Path("reports"), help="レポート/修正版の出力先")
    parser.add_argument("--no-llm", action="store_true", help="LLMを使わずヒューリスティックのみ実行")
    args = parser.parse_args()

    cfg = AppConfig.load()
    gdir = args.guidelines_dir or cfg.guidelines_dir
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # 入力を読み込み
    in_path: Path = args.input
    if not in_path.exists():
        raise FileNotFoundError(in_path)
    text = read_docx_text(in_path)
    lines: List[str] = text.splitlines()

    # ガイドライン読み込み
    gtext = read_guidelines_text(gdir)

    # 解析
    suggestions: List[Suggestion] = []
    suggestions += heuristic_checks(lines)
    if not args.no_llm:
        suggestions += llm_checks(
            text=text,
            guidelines_text=gtext,
            model=cfg.openai_model,
            api_key=cfg.openai_api_key,
            base_url=cfg.openai_base_url,
        )

    # レポート出力
    report = [s.to_dict() for s in suggestions]
    report_path = out_dir / f"{in_path.stem}_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # 簡易自動修正（autofix=true のみ）
    replacements = {}
    for s in suggestions:
        if s.autofix and s.suggested_fix:
            # 簡易化のため message から置換前語を抽出するのではなく、適用は別UIで高度化を想定
            pass

    # 現時点では自動置換を行わず、原文をコピー保存しておく（将来UIで選択適用）
    fixed_path = out_dir / f"{in_path.stem}_fixed.docx"
    write_docx_with_replacements(in_path, fixed_path, replacements)

    print("解析完了:")
    print("- レポート:", report_path)
    print("- 修正版(現状は原文コピー):", fixed_path)


if __name__ == "__main__":
    run_cli()

