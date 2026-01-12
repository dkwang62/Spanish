# spanish_core.py (v6.0)
# Core: Jehle DB + SUBTLEX rank file + Pronominal JSON + Prompts
# Updated: Loads verb seeds from external JSON to reduce code bloat

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import streamlit as st

VERBS_CAT_JSON = "verbs_categorized.json"

@st.cache_data(show_spinner=False)
def load_jehle_db(db_json_path: str, lookup_json_path: str) -> Tuple[List[dict], Dict[str, int]]:
    with open(db_json_path, "r", encoding="utf-8") as f:
        verbs = json.load(f)
    with open(lookup_json_path, "r", encoding="utf-8") as f:
        lookup = json.load(f)
    lookup = {k.lower(): int(v) for k, v in lookup.items()}
    return verbs, lookup

@st.cache_data(show_spinner=False)
def load_verb_seeds(json_path: str = VERBS_CAT_JSON) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Parses the categorized JSON into flat lookup dicts for 'Reflexive' and 'Pronominal' seeds.
    Returns: (reflexive_flat, pronominal_flat)
    """
    p = Path(json_path)
    if not p.exists():
        return {}, {}
        
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        taxonomy = data.get("verb_taxonomy", {})
        
        # Helper to flatten categories
        def _flatten_categories(root_key: str) -> Dict[str, str]:
            flat_map = {}
            cats = taxonomy.get(root_key, {}).get("categories", {})
            for cat_name, content in cats.items():
                for base, pron in content.get("verbs", {}).items():
                    flat_map[base.lower()] = pron
            return flat_map

        reflexive_flat = _flatten_categories("reflexive")
        pronominal_flat = _flatten_categories("pronominal")
        
        return reflexive_flat, pronominal_flat
    
    except Exception:
        return {}, {}


def _starter_overrides() -> Dict[str, dict]:
    # Expanded overrides with more nuance, preserved as fallback logic
    return {
        "lavar": {"is_pronominal": True, "pronominal_infinitive": "lavarse", "se_type": "reflexive", "meaning_shift": "subject washes self"},
        "ir": {"is_pronominal": True, "pronominal_infinitive": "irse", "se_type": "pronominal", "meaning_shift": "departure / leaving"},
        "dormir": {"is_pronominal": True, "pronominal_infinitive": "dormirse", "se_type": "pronominal", "meaning_shift": "fall asleep"},
        "poner": {"is_pronominal": True, "pronominal_infinitive": "ponerse", "se_type": "pronominal", "meaning_shift": "become / put on (clothes)"},
        "quedar": {"is_pronominal": True, "pronominal_infinitive": "quedarse", "se_type": "pronominal", "meaning_shift": "remain / stay"},
        "volver": {"is_pronominal": True, "pronominal_infinitive": "volverse", "se_type": "pronominal", "meaning_shift": "become (permanent change)"},
        "dar": {"is_pronominal": True, "pronominal_infinitive": "darse cuenta", "se_type": "pronominal_phrase", "meaning_shift": "realize"},
    }


def load_overrides(overrides_path: str) -> Dict[str, dict]:
    starter = _starter_overrides()
    p = Path(overrides_path)
    if not p.exists():
        return starter
    try:
        with open(p, "r", encoding="utf-8") as f:
            user_overrides = json.load(f)
        if not isinstance(user_overrides, dict):
            return starter
        merged = dict(starter)
        for k, v in user_overrides.items():
            merged[str(k).lower()] = v
        return merged
    except Exception:
        return starter


def save_overrides(overrides_path: str, merged_overrides: Dict[str, dict]) -> None:
    starter_keys = set(_starter_overrides().keys())
    user_only = {k: v for k, v in merged_overrides.items() if k not in starter_keys}
    with open(overrides_path, "w", encoding="utf-8") as f:
        json.dump(user_only, f, ensure_ascii=False, indent=2)


@st.cache_data(show_spinner=False)
def load_frequency_map(freq_path: str) -> Dict[str, int]:
    p = Path(freq_path)
    if not p.exists():
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            m = json.load(f)
        if not isinstance(m, dict):
            return {}
        out = {}
        for k, v in m.items():
            try:
                out[str(k).lower()] = int(v)
            except Exception:
                continue
        return out
    except Exception:
        return {}


# --- TEMPLATES (Spanish Radix v1) ---
TEMPLATES: Dict[str, dict] = {
    "REFLEXIVE_PLACEMENT_CORE": {
        "name": "Reflexive / se placement drill",
        "prompt": """You are the 'Spanish Radix' engine (v1). Execute the following task strictly.

**Global Constraints & Safety Rules:**
1. **Consistency:** Use the SAME subject and SAME non-verb vocabulary across all sentences in Sections A-D. Vary only the verb tense/mood.
2. **Highlighting:** Highlight the CLITIC + VERB in **ALL CAPS** (e.g., "ME LAVO", "LAVARME").
3. **Time/Tense Agreement:** Ensure time expressions (hoy, ayer, mañana) match the verb tense.
4. **Subjunctive Licensing:** For Section E, ONLY use subjunctive with valid triggers.

**Task:** REFLEXIVE_PLACEMENT_CORE
**Target Verb:** {infinitive}
**Pronominal Form:** {pronominal_infinitive}
**Meaning Shift:** {meaning_shift}

**Step 1: Explain Rules**
Briefly explain clitic placement for: Conjugated verbs, Infinitives, Gerunds, Imperatives.

**Step 2: Generate Sections (5 sentences each)**
* **Section A:** Indicative (Clitic before conjugated verb)
* **Section B:** Infinitive (Attached clitic)
* **Section C:** Gerund (Attached clitic)
* **Section D:** Imperatives (Positive attached, Negative before)
* **Section E:** Subjunctive (Trigger + que + subject + clitic + verb)

**Step 3: Drill**
Provide 10 fill-in-the-blank sentences mixing all structures above with an Answer Key.
"""
    },
    "PRONOMINAL_CONTRAST_PAIR": {
        "name": "Base vs pronominal contrast",
        "prompt": """You are the 'Spanish Radix' engine (v1). Execute the following task strictly.

**Global Constraints:**
1. **Highlighting:** Highlight the target VERB in **ALL CAPS**.
2. **Clarity:** Ensure the English translation clearly reflects the specific meaning difference.

**Task:** PRONOMINAL_CONTRAST_PAIR
**Base Verb:** {infinitive}
**Pronominal Form:** {pronominal_infinitive}
**Meaning Shift:** {meaning_shift}

**Step 1: Explanation**
Explain the semantic contrast in 4–5 lines.

**Step 2: Contrast Pairs (12 Total)**
* **Sentence A:** Base Verb ({infinitive}).
* **Sentence B:** Pronominal Verb ({pronominal_infinitive}).
* Both sentences should share context.

**Distribution:**
* **6 Pairs:** Present Tense
* **3 Pairs:** Past Tense
* **3 Pairs:** Future or "Ir a + inf"

**Step 3: Decision Drill**
Create 10 short scenarios where the user decides between Base or Pronominal forms.
"""
    },
}


def get_verb_record(verbs: List[dict], lookup: Dict[str, int], infinitive: str) -> Optional[dict]:
    idx = lookup.get(infinitive.lower())
    return verbs[idx] if idx is not None else None


def merge_usage(verb: dict, overrides: Dict[str, dict]) -> dict:
    base = (verb.get("infinitive") or "").lower()

    # 1) start from overrides
    o = overrides.get(base, {})

    # 2) Load Seeds dynamically (Cached)
    ref_seed, pron_seed = load_verb_seeds(VERBS_CAT_JSON)
    
    seed_pron = pron_seed.get(base)
    seed_refl = ref_seed.get(base)

    is_pronominal = bool(o.get("is_pronominal", False))
    pronominal_inf = o.get("pronominal_infinitive")
    se_type = o.get("se_type")
    meaning_shift = o.get("meaning_shift")

    if not o:
        if seed_pron:
            is_pronominal = True
            pronominal_inf = seed_pron
            se_type = "pronominal"
            meaning_shift = "meaning shift (see category in json)"
        elif seed_refl:
            is_pronominal = True
            pronominal_inf = seed_refl
            se_type = "reflexive"
            meaning_shift = "reflexive (self-directed)"

    usage = {
        "is_pronominal": is_pronominal,
        "pronominal_infinitive": pronominal_inf,
        "se_type": se_type,
        "meaning_shift": meaning_shift,
        "notes": o.get("notes", "")
    }

    verb2 = dict(verb)
    verb2["usage"] = usage
    if "infinitive_english" in verb2 and "gloss_en" not in verb2:
        verb2["gloss_en"] = verb2.get("infinitive_english")
    return verb2


def render_prompt(template_id: str, verb: dict) -> str:
    t = TEMPLATES.get(template_id)
    if not t:
        return ""
    usage = verb.get("usage", {}) or {}
    
    infinitive = verb.get("infinitive", "VERB")
    pronominal = usage.get("pronominal_infinitive") or f"{infinitive}se"
    shift = usage.get("meaning_shift") or "Standard usage"

    return t["prompt"].format(
        infinitive=infinitive,
        pronominal_infinitive=pronominal,
        meaning_shift=shift,
    )


def _matches_english(v: dict, q: str) -> bool:
    gloss = (v.get("infinitive_english") or v.get("gloss_en") or "")
    if gloss and q in gloss.lower():
        return True
    for c in (v.get("conjugations") or []):
        ve = (c.get("verb_english") or "")
        if ve and q in ve.lower():
            return True
    return False


def search_verbs(verbs: List[dict], query: str, limit: int = 2000) -> List[dict]:
    q = (query or "").strip().lower()
    if not q:
        return []
    out = []
    for v in verbs:
        inf = (v.get("infinitive") or "")
        if inf.lower().startswith(q) or _matches_english(v, q):
            out.append(v)
        if len(out) >= limit:
            break
    return out


def sorted_infinitives(verbs: List[dict], rank_map: Dict[str, int]) -> List[str]:
    infinitives = [v.get("infinitive") for v in verbs if v.get("infinitive")]
    infinitives.sort(key=lambda inf: (rank_map.get(inf.lower(), 10_000_000), inf))
    return infinitives