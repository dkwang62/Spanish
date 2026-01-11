# app.py (v6.6)
# Updates:
# 1. Sort options changed to: "Alphabetical", "ar/er/ir/se", "Popularity".
# 2. Default sort is now "Alphabetical".

import streamlit as st

from spanish_core import (
    load_jehle_db, load_overrides, save_overrides,
    load_frequency_map, sorted_infinitives, search_verbs,
    get_verb_record, merge_usage, TEMPLATES, render_prompt
)
from spanish_state import PAGE_CONFIG, ensure_state, click_tile, back_to_grid
from spanish_ui import apply_styles, build_verb_card_html

DB_JSON = "jehle_verb_database.json"
LOOKUP_JSON = "jehle_verb_lookup_index.json"
FREQ_JSON = "verb_frequency_rank.json" 
OVERRIDES_JSON = "verb_overrides.json"

st.set_page_config(**PAGE_CONFIG)
apply_styles()
ensure_state()

verbs, lookup = load_jehle_db(DB_JSON, LOOKUP_JSON)
rank_map = load_frequency_map(FREQ_JSON)
overrides = load_overrides(OVERRIDES_JSON)

# Fetch state vars
mode = st.session_state.get("mode", "grid")
preview_inf = st.session_state.get("preview")
selected_inf = st.session_state.get("selected")

st.title("Spanish Verb Lab")

# ==========================================
# 🛑 SIDEBAR: NAVIGATION & CONTROLS
# ==========================================
with st.sidebar:
    
    # --- 1. NAVIGATION GROUP ---
    st.header("Navigation")
    
    if mode == "grid":
        st.markdown("📍 **Home / Grid**")
    else:
        st.markdown(f"📍 Home › **{selected_inf}**")

    # Action Buttons Logic
    if mode == "grid":
        if preview_inf:
            if st.button(f"Open '{preview_inf}' Details ➡", use_container_width=True, type="primary"):
                st.session_state["selected"] = preview_inf
                st.session_state["mode"] = "detail"
                st.rerun()
        else:
            st.button("Select a verb to preview...", disabled=True, use_container_width=True)
            
    elif mode == "detail":
        if st.button("⬅ Back to Verb Grid", use_container_width=True, type="primary"):
            back_to_grid()
            st.rerun()

    st.divider()

    # --- 2. SEARCH ---
    st.subheader("Search")

    if "search_query" not in st.session_state:
        st.session_state["search_query"] = ""
    if "search_input" not in st.session_state:
        st.session_state["search_input"] = ""

    search_cols = st.columns([0.85, 0.15])
    with search_cols[0]:
        search_text = st.text_input(
            "Search",
            value=st.session_state["search_input"],
            placeholder="hablar / speak",
            label_visibility="collapsed",
        )
    with search_cols[1]:
        if st.button("🔍", help="Search", use_container_width=True):
            st.session_state["search_query"] = search_text.strip()
            st.session_state["search_input"] = ""
            st.rerun()

    st.session_state["search_input"] = search_text

    if st.button("Clear search", use_container_width=True):
        st.session_state["search_query"] = ""
        st.rerun()

    st.divider()

    # --- 3. PREVIEW CARD (Grid Only) ---
    if mode == "grid":
        st.subheader("Preview")
        if preview_inf:
            v = get_verb_record(verbs, lookup, preview_inf)
            if v:
                v = merge_usage(v, overrides)
                rank = rank_map.get(preview_inf.lower())
                st.markdown(build_verb_card_html(v, rating=None, freq_rank=rank), unsafe_allow_html=True)
        else:
            st.caption("Click a tile to preview.")
        st.divider()

    # --- 4. SETTINGS ---
    st.subheader("Display Settings")
    show_vos = st.checkbox("Show 'vos' (voseo)", value=True)
    show_vosotros = st.checkbox("Show 'vosotros'", value=True)


# ==========================================
# 🛑 MAIN AREA
# ==========================================

if mode == "grid":
    # Instruction Tip
    st.info("👆 **Tip:** Click a tile to **preview** in the sidebar. Click the **same tile again** (or the sidebar button) to open details.", icon="ℹ️")

    # --- TOP CONTROLS (Sort) ---
    sort_option = st.radio(
        "Sort Order",
        options=["Alphabetical", "ar/er/ir/se", "Popularity"],
        index=0, # Default: Alphabetical
        horizontal=True,
        label_visibility="collapsed"
    )

    # --- List Building Logic ---
    def _rank(inf: str) -> int:
        return rank_map.get(inf.lower(), 10_000_000)

    def build_list() -> list[str]:
        q = st.session_state.get("search_query", "")
        if q.strip():
            results = search_verbs(verbs, q, limit=5000)
            base = [r["infinitive"] for r in results if r.get("infinitive")]
        else:
            base = [v["infinitive"] for v in verbs if v.get("infinitive")]
        
        base = list(dict.fromkeys(base))

        # "Popularity" sorts by Rank
        if sort_option == "Popularity":
            base.sort(key=lambda inf: (_rank(inf), inf))
            return base
        
        # "Alphabetical" and "ar/er/ir/se" (group basis) sort A-Z
        return sorted(base, key=lambda x: x.lower())

    base_list = build_list()

    def render_tiles(infs: list[str], per_row: int = 6, max_items: int = 240):
        infs = infs[:max_items]
        for i in range(0, len(infs), per_row):
            row = infs[i:i+per_row]
            cols = st.columns(per_row)
            for j, inf in enumerate(row):
                label = f"{inf}"
                
                # Check active state
                is_preview = (st.session_state.get("preview") == inf)
                btn_type = "primary" if is_preview else "secondary"
                
                cols[j].button(
                    label,
                    key=f"tile_{inf}",
                    use_container_width=True,
                    type=btn_type,
                    on_click=click_tile,
                    args=(inf,),
                )

    if sort_option == "ar/er/ir/se":
        # Grouped View (A-Z within groups)
        ar = sorted([inf for inf in base_list if inf.lower().endswith("ar")], key=lambda x: x.lower())
        er = sorted([inf for inf in base_list if inf.lower().endswith("er")], key=lambda x: x.lower())
        
        # Match both "ir" and "ír"
        ir = sorted([inf for inf in base_list if inf.lower().endswith(("ir", "ír"))], key=lambda x: x.lower())
        
        # Exclude all endings
        other = sorted([inf for inf in base_list if not inf.lower().endswith(("ar", "er", "ir", "ír"))], key=lambda x: x.lower())

        st.subheader("-ar verbs")
        render_tiles(ar)
        st.divider()
        st.subheader("-er verbs")
        render_tiles(er)
        st.divider()
        st.subheader("-ir verbs")
        render_tiles(ir)
        
        if other:
            st.divider()
            st.subheader("Other")
            render_tiles(other)

    else:
        # "Alphabetical" or "Popularity" (Flat list)
        render_tiles(base_list, max_items=600)

else:
    # --- DETAIL VIEW ---
    if not selected_inf:
        st.warning("No verb selected.")
        st.stop()

    v = get_verb_record(verbs, lookup, selected_inf)
    if not v:
        st.error("Verb not found.")
        st.stop()

    v = merge_usage(v, overrides)

    tabs = st.tabs(["Conjugations", "Prompt generator"])
    with tabs[0]:
        from spanish_ui import render_conjugation_dashboard
        render_conjugation_dashboard(v, show_vos=show_vos, show_vosotros=show_vosotros)

    with tabs[1]:
        template_id = st.selectbox(
            "Template",
            options=list(TEMPLATES.keys()),
            format_func=lambda k: f"{TEMPLATES[k]['name']} ({k})"
        )
        prompt = render_prompt(template_id, v)

        st.subheader("Generated AI Prompt")
        st.code(prompt, language="text")
