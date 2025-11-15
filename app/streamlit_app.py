from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from meisai_checker.config import AppConfig
from meisai_checker.guidelines_loader import read_guidelines_text
from meisai_checker.word_io import read_docx_text, write_docx_with_replacements
from meisai_checker.analyzers import heuristic_checks, llm_checks


st.set_page_config(page_title="明細書チェックくん", layout="wide")
st.title("明細書チェックくん (MVP)")

cfg = AppConfig.load()

uploaded = st.file_uploader(".docx をアップロード", type=["docx"])
guidelines_dir = st.text_input("guidelines ディレクトリ", str(cfg.guidelines_dir))
use_llm = st.checkbox("LLM を使う（OpenAI）", value=True)

if uploaded is not None:
    tmp_in = Path(".tmp_input.docx")
    tmp_in.write_bytes(uploaded.read())

    text = read_docx_text(tmp_in)
    lines = text.splitlines()
    gtext = read_guidelines_text(Path(guidelines_dir))

    suggestions = heuristic_checks(lines)
    if use_llm:
        suggestions += llm_checks(text, gtext, cfg.openai_model, cfg.openai_api_key, cfg.openai_base_url)

    st.subheader("指摘一覧")
    chosen_ids = []
    for s in suggestions:
        with st.expander(f"[{s.severity}] {s.category} - {s.message}"):
            st.json(s.to_dict(), expanded=False)
            if st.checkbox("この修正案を適用する", key=s.id, value=False):
                chosen_ids.append(s.id)

    if st.button("修正版を生成"):
        # 本MVPでは自動置換は未実装（UI設計と差分作成のため）
        out_dir = Path("reports")
        out_dir.mkdir(exist_ok=True)
        fixed = out_dir / f"{tmp_in.stem}_fixed.docx"
        write_docx_with_replacements(tmp_in, fixed, {})
        rep = out_dir / f"{tmp_in.stem}_report.json"
        rep.write_text(json.dumps([s.to_dict() for s in suggestions], ensure_ascii=False, indent=2), encoding="utf-8")
        st.success("生成しました。")
        st.write("レポート:", rep)
        st.write("修正版:", fixed)

