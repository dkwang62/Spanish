# app.py (v5)
# Grid tiles sorted by SUBTLEX rank.
# Click once: sidebar preview.
# Click same tile again: open detail (replaces grid).
# Back button returns to grid.
# No wordfreq. No personal rating/notes.

import streamlit as st

from spanish_core import (
    load_jehle_db, load_overrides, save_overrides,
    load_frequency_map, sorted_infinitives, search_verbs,
    get_verb_record, merge_usage, TEMPLATES, render_prompt
)
from spanish_state import PAGE_CONFIG, ensure_state, click_tile, back_to_grid
from spanish_ui import apply_styles, conjugations_to_table, build_verb_card_html, render_prompt_box, render_breadcrumb

DB_JSON = "jehle_verb_database.json"
LOOKUP_JSON = "jehle_verb_lookup_index.json"
FREQ_JSON = "verb_frequency_rank.json"   # your SUBTLEX-derived file
OVERRIDES_JSON = "verb_overrides.json"

st.set_page_config(**PAGE_CONFIG)
apply_styles()
ensure_state()

verbs, lookup = load_jehle_db(DB_JSON, LOOKUP_JSON)
rank_map = load_frequency_map(FREQ_JSON)
overrides = load_overrides(OVERRIDES_JSON)

st.title("Spanish Verb Lab")

# ---------- Sidebar: search + preview card ----------
with st.sidebar:

    st.header("Verbs")

    if "search_query" not in st.session_state:
        st.session_state["search_query"] = ""

    if "search_input" not in st.session_state:
        st.session_state["search_input"] = ""

    search_cols = st.columns([0.85, 0.15])

    with search_cols[0]:
        search_text = st.text_input(
            "Search (Spanish or English)",
            value=st.session_state["search_input"],
            placeholder="hablar / to speak / speak",
            label_visibility="collapsed",
        )

    with search_cols[1]:
        if st.button("🔍", help="Search", use_container_width=True):
            st.session_state["search_query"] = search_text.strip()
            st.session_state["search_input"] = ""
            st.rerun()


    # keep input synced
    st.session_state["search_input"] = search_text

    if st.button("Clear search", use_container_width=True):
        st.session_state["search_query"] = ""
        st.rerun()






    preview_inf = st.session_state.get("preview")
    selected_inf = st.session_state.get("selected")
    mode = st.session_state.get("mode", "grid")

    active_inf = selected_inf if mode == "detail" else preview_inf

    if active_inf:
        v = get_verb_record(verbs, lookup, active_inf)
        if v:
            v = merge_usage(v, overrides)
            rank = rank_map.get(active_inf.lower())
            st.markdown(build_verb_card_html(v, rating=None, freq_rank=rank), unsafe_allow_html=True)
    else:
        st.caption("Click a verb tile to preview here.")






    sort_mode = st.selectbox(
        "Sort grid",
        options=[
            "1) Ranking",
            "2) -ar / -er / -ir then ranking",
            "3) Alphabetical (no ranking)",
        ],
        index=0,
    )





# ---------- Main: grid OR detail ----------
mode = st.session_state.get("mode", "grid")
preview_inf = st.session_state.get("preview")
selected_inf = st.session_state.get("selected")

# Build list (sorted by rank) and optionally filter by search

def _rank(inf: str) -> int:
    return rank_map.get(inf.lower(), 10_000_000)


def build_list() -> list[str]:
    q = st.session_state.get("search_query", "")

    if q.strip():
        results = search_verbs(verbs, q, limit=5000)
        base = [r["infinitive"] for r in results if r.get("infinitive")]
    else:
        base = [v["infinitive"] for v in verbs if v.get("infinitive")]

    # de-duplicate while preserving order
    base = list(dict.fromkeys(base))

    # alphabetical (no ranking)
    if sort_mode.startswith("3)"):
        return sorted(base, key=lambda x: x.lower())

    # ranking-based (mode 1 and 2)
    base.sort(key=lambda inf: (_rank(inf), inf))
    return base



base_list = build_list()




def render_tiles(infs: list[str], show_rank: bool, per_row: int = 6, max_items: int = 240):
    infs = infs[:max_items]
    for i in range(0, len(infs), per_row):
        row = infs[i:i+per_row]
        cols = st.columns(per_row)
        for j, inf in enumerate(row):
            r = rank_map.get(inf.lower())
            label = f"{inf} ({r})" if (show_rank and r is not None) else f"{inf}"
            btn_type = "primary" if st.session_state.get("preview") == inf else "secondary"
            cols[j].button(
                label,
                key=f"tile_{inf}",
                use_container_width=True,
                type=btn_type,
                on_click=click_tile,
                args=(inf,),
            )

if mode == "grid":
    show_rank = not sort_mode.startswith("3)")

    if sort_mode.startswith("2)"):
        # IMPORTANT: split FROM base_list (already rank-sorted)
        ar = [inf for inf in base_list if inf.lower().endswith("ar")]
        er = [inf for inf in base_list if inf.lower().endswith("er")]
        ir = [inf for inf in base_list if inf.lower().endswith("ir")]
        other = [inf for inf in base_list if not inf.lower().endswith(("ar", "er", "ir"))]

        st.subheader("-ar verbs")
        render_tiles(ar, show_rank=True)

        st.divider()
        st.subheader("-er verbs")
        render_tiles(er, show_rank=True)

        st.divider()
        st.subheader("-ir verbs")
        render_tiles(ir, show_rank=True)

        if other:
            st.divider()
            st.subheader("Other")
            render_tiles(other, show_rank=True)

    else:
        # Mode 1 (ranking) or Mode 3 (alphabetical)
        render_tiles(base_list, show_rank=show_rank, max_items=600)

    st.stop()

else:
    # detail view (replaces grid)
    if not selected_inf:
        st.warning("No verb selected.")
        st.stop()

    v = get_verb_record(verbs, lookup, selected_inf)
    if not v:
        st.error("Verb not found.")
        st.stop()

    v = merge_usage(v, overrides)
    render_breadcrumb("detail", selected_inf)

    st.button("← Back to verb grid", on_click=back_to_grid, type="primary")

    tabs = st.tabs(["Conjugations", "Prompt generator"])
    with tabs[0]:
        df = conjugations_to_table(v.get("conjugations", []))
        st.dataframe(df, use_container_width=True, height=640)

    with tabs[1]:
        template_id = st.selectbox(
            "Template",
            options=list(TEMPLATES.keys()),
            format_func=lambda k: f"{TEMPLATES[k]['name']} ({k})"
        )
        prompt = render_prompt(template_id, v)

        st.subheader("Generated AI Prompt")

        st.code(
            prompt,
            language="text",
        )

