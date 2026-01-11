# spanish_ui.py (v3)
# UI helpers (Radix-like cards + breadcrumb)

from __future__ import annotations

from typing import List, Optional
import pandas as pd
import streamlit as st

PERSON_ORDER = ["yo", "tú", "él/ella/usted", "nosotros/nosotras", "vosotros/vosotras", "ellos/ellas/ustedes"]


def apply_styles() -> None:
    st.markdown("""
    <style>
    .main .block-container {padding-top: 1.3rem; padding-bottom: 3rem;}

    .crumb {font-size: 0.85rem; color: #6c757d; font-weight: 700; margin-bottom: 6px;}
    .crumb b {color:#212529;}

    .verb-card {
      background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
      padding: 18px 18px;
      border-radius: 14px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.06);
      border: 1px solid #e9ecef;
      margin-bottom: 14px;
    }
    .verb-title {font-size: 1.6rem; font-weight: 800; margin: 0; line-height: 1.2;}
    .verb-gloss {color: #444; font-size: 1.05rem; font-weight: 600; margin-top: 6px;}
    .meta-row {display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-top: 10px;}
    .meta-tag {
      background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
      padding: 4px 10px; border-radius: 8px;
      font-size: 0.85rem; color: #495057; font-weight: 700;
      display:inline-block;
    }
    .meta-tag-accent {background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%); color: #856404; border: 1px solid #ffd54f;}
    .hint {font-size: 0.78rem; color: #6c757d; font-weight: 700; margin-top: 6px;}
    </style>
    """, unsafe_allow_html=True)


def conjugations_to_table(conjugations: List[dict]) -> pd.DataFrame:
    rows = []
    for c in conjugations:
        mood = c.get("mood")
        tense = c.get("tense")
        forms = c.get("forms") or {}
        row = {"mood": mood, "tense": tense}
        for p in PERSON_ORDER:
            row[p] = forms.get(p)
        rows.append(row)
    return pd.DataFrame(rows)


def render_breadcrumb(mode: str, infinitive: str) -> None:
    if mode == "detail":
        html = f"<div class='crumb'>Verbs › <b>{infinitive}</b> › Detail</div>"
    else:
        html = f"<div class='crumb'>Verbs › <b>{infinitive}</b></div>"
    st.markdown(html, unsafe_allow_html=True)


def build_verb_card_html(verb: dict, rating: Optional[int] = None, freq_rank: Optional[int] = None) -> str:
    inf = verb.get("infinitive", "")
    gloss = verb.get("gloss_en") or verb.get("infinitive_english") or ""
    usage = verb.get("usage", {}) or {}
    pro = usage.get("pronominal_infinitive")
    se_type = usage.get("se_type")
    shift = usage.get("meaning_shift")

    tags = []
    if freq_rank is not None:
        tags.append(f"<span class='meta-tag meta-tag-accent'>Rank #{freq_rank}</span>")
    if rating is not None:
        tags.append(f"<span class='meta-tag'>Your rating: {rating}/5</span>")
    if usage.get("is_pronominal") and pro:
        tags.append(f"<span class='meta-tag'>Pronominal: {pro}</span>")
        if se_type:
            tags.append(f"<span class='meta-tag'>se-type: {se_type}</span>")

    nf = verb.get("nonfinite") or {}
    if nf.get("gerund"):
        tags.append(f"<span class='meta-tag'>Gerund: {nf.get('gerund')}</span>")
    if nf.get("past_participle"):
        tags.append(f"<span class='meta-tag'>PP: {nf.get('past_participle')}</span>")

    meta_html = f"<div class='meta-row'>{''.join(tags)}</div>" if tags else ""
    shift_html = f"<div class='hint'>Meaning shift: {shift}</div>" if shift else ""

    return f"""
    <div class='verb-card'>
      <div class='verb-title'>{inf}</div>
      <div class='verb-gloss'>{gloss}</div>
      {meta_html}
      {shift_html}
    </div>
    """


def render_prompt_box(prompt: str) -> None:
    st.text_area("Generated prompt (paste into ChatGPT)", value=prompt, height=420)

import streamlit as st
import pandas as pd

PERSON_ORDER = [
    "yo", "tú", "vos", "él/ella/usted",
    "nosotros/nosotras", "vosotros/vosotras",
    "ellos/ellas/ustedes"
]

MOOD_ORDER = [
    "Indicative",
    "Subjunctive",
    "Imperative",
]


def render_periphrastic(verb: dict) -> None:
    infinitive = verb.get("infinitive", "")
    nf = verb.get("nonfinite", {}) or {}
    gerund = nf.get("gerund", "")
    past_part = nf.get("past_participle", "")

    st.markdown("## 🟪 PROGRESSIVE (estar + gerund)")
    st.table(pd.DataFrame([
        ["yo", f"estoy {gerund}"],
        ["tú", f"estás {gerund}"],
        ["vos", f"estás {gerund}"],
        ["él / ella / Ud.", f"está {gerund}"],
        ["nosotros", f"estamos {gerund}"],
        ["vosotros", f"estáis {gerund}"],
        ["ellos", f"están {gerund}"],
    ], columns=["Pronoun", "Form"]))

    st.markdown("## 🟥 PERFECT (haber + participle)")
    st.table(pd.DataFrame([
        ["yo", f"he {past_part}"],
        ["tú", f"has {past_part}"],
        ["vos", f"has {past_part}"],
        ["él / ella / Ud.", f"ha {past_part}"],
        ["nosotros", f"hemos {past_part}"],
        ["vosotros", f"habéis {past_part}"],
        ["ellos", f"han {past_part}"],
    ], columns=["Pronoun", "Form"]))

    st.markdown("## 🟧 INFORMAL FUTURE (ir a)")
    st.table(pd.DataFrame([
        ["yo", f"voy a {infinitive}"],
        ["tú", f"vas a {infinitive}"],
        ["vos", f"vas a {infinitive}"],
        ["él / ella / Ud.", f"va a {infinitive}"],
        ["nosotros", f"vamos a {infinitive}"],
        ["vosotros", f"vais a {infinitive}"],
        ["ellos", f"van a {infinitive}"],
    ], columns=["Pronoun", "Form"]))






def render_conjugation_dashboard(verb: dict):
    st.markdown(f"## 🔹 Verb: **{verb['infinitive'].upper()}**")
    st.markdown("### Practice Conjugation Dashboard")

    # ---- Participles ----
    nf = verb.get("nonfinite", {})
    st.markdown("### 🧩 Participles")
    st.table(pd.DataFrame(
        [
            ["Present participle", nf.get("gerund")],
            ["Past participle", nf.get("past_participle")],
        ],
        columns=["Type", "Form"]
    ))

    # ---- Group conjugations ----
    grouped = {}
    for c in verb.get("conjugations", []):
        mood = c["mood"]
        tense = c["tense"]
        grouped.setdefault(mood, {}).setdefault(tense, []).append(c)

    # ---- INDICATIVE / SUBJUNCTIVE / IMPERATIVE ----
    for mood in MOOD_ORDER:
        if mood not in grouped:
            continue

        icon = {
            "Indicative": "🟦",
            "Subjunctive": "🟩",
            "Imperative": "🟨",
        }.get(mood, "🔹")

        st.markdown(f"## {icon} {mood.upper()}")

        for tense, entries in grouped[mood].items():
            st.markdown(f"### {tense}")

            rows = []
            forms = entries[0]["forms"]
            for p in PERSON_ORDER:
                if p in forms and forms[p]:
                    rows.append([p, forms[p]])

            st.table(pd.DataFrame(rows, columns=["Pronoun", "Form"]))

    # ---- PERIPHRASTIC FORMS ----
    render_periphrastic(verb)
