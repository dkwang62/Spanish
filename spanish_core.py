# spanish_core.py (v7.1)
# Core: Jehle DB + Pronominal JSON + Prompts + Se Classification
# Updated: Added STANDARD_VERB_DRILL as a fallback for non-pronominal verbs

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

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
def load_se_catalog(path: str = VERBS_CAT_JSON) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

@st.cache_data(show_spinner=False)
def load_verb_seeds(json_path: str = VERBS_CAT_JSON) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Parses the categorized JSON into flat lookup dicts for 'Reflexive' and 'Pronominal' seeds.
    Returns: (reflexive_flat, pronominal_flat)
    """
    data = load_se_catalog(json_path)
    taxonomy = data.get("verb_taxonomy", {})
    
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


def classify_se_type(infinitive: str, pronominal_infinitive: str | None, se_catalog: dict) -> str | None:
    """
    Returns one of: 'reflexive', 'pronominal', 'accidental_dative', or None.
    """
    if not se_catalog or not pronominal_infinitive:
        return None

    pro = pronominal_infinitive.lower()
    taxonomy = se_catalog.get("verb_taxonomy", {})

    def _get_set(root_key):
        s = set()
        cats = taxonomy.get(root_key, {}).get("categories", {})
        for _, content in cats.items():
            s.update([v.lower() for v in content.get("verbs", {}).values()])
        return s

    ref_all = _get_set("reflexive")
    pro_all = _get_set("pronominal")
    acc_all = _get_set("accidental_dative")

    if pro in acc_all:
        return "accidental_dative"
    if pro in ref_all:
        return "reflexive"
    if pro in pro_all:
        return "pronominal"
    
    return None


def _starter_overrides() -> Dict[str, dict]:
    return {
        "lavar": {"is_pronominal": True, "pronominal_infinitive": "lavarse", "se_type": "reflexive", "meaning_shift": "subject washes self"},
        "ir": {"is_pronominal": True, "pronominal_infinitive": "irse", "se_type": "pronominal", "meaning_shift": "departure / leaving"},
        "caer": {"is_pronominal": True, "pronominal_infinitive": "caerse", "se_type": "accidental_dative", "meaning_shift": "fall/drop accidentally"},
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


# --- TEMPLATES ---
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
    "ACCIDENTAL_DATIVE_SE_CORE": {
        "name": "Accidental / dative se drill",
        "prompt": """You are the 'Spanish Radix' engine (v1). Execute the following task strictly.

**Target pattern:** accidental/dative SE
**Target verb:** {pronominal_infinitive}
**Base verb:** {infinitive}
**Level:** A2–B1

**Step 1: Explain the pattern briefly**
- Structure: SE + IO clitic (me/te/le/nos/os/les) + 3rd-person verb
- Meaning: unintended event affecting someone, lack of control.

**Step 2: Generate 20 short sentences (Spanish + English)**
- Use only one IO clitic per sentence (rotate me/te/le/nos/os/les).
- **Global Constraint:** Highlight SE + IO CLITIC + VERB in **ALL CAPS** (e.g. "SE ME CAYÓ").
- Keep vocabulary simple and relevant to the verb's meaning ({meaning_shift}).

**Step 3: Drill**
- 10 fill-in-the-blank sentences (focus on the 'se + io' cluster).
- Provide answer key.
"""
    },
    "ACCIDENTAL_VS_INTENTIONAL_CONTRAST": {
        "name": "Accidental (se me...) vs intentional",
        "prompt": """You are the 'Spanish Radix' engine (v1). Execute the following task strictly.

**Teach the contrast:**
A) Intentional action (Base verb: {infinitive})
B) Accidental outcome (Accidental Se: {pronominal_infinitive})

**Step 1: Explain the meaning difference**
Explain in 4–5 simple lines how the syntax changes the meaning from "I did X" to "X happened to me".

**Step 2: Provide 12 contrast pairs**
- Share the object/context where possible.
- **Sentence A:** Intentional (Active voice, normal subject).
- **Sentence B:** Accidental (Se + IO construction).
- Format: Spanish + English.
- **Highlight the verb phrase in ALL CAPS**.

**Step 3: Decision Drill**
- 10 situations where the user must choose between the intentional or accidental construction.
- Provide answers + one-line explanation.
"""
    },
    # NEW: Fallback for all verbs
    "STANDARD_VERB_DRILL": {
        "name": "Standard conjugation & usage",
        "prompt": """You are the 'Spanish Radix' engine (v1).

**Global Constraints:**
1. **Highlighting:** Highlight the target VERB in **ALL CAPS**.
2. **Accuracy:** Ensure strict tense agreement and correct conjugations.

**Task:** STANDARD_VERB_DRILL
**Target Verb:** {infinitive}
**Meaning:** {meaning_shift}

**Step 1: Conjugation Overview**
List the Present, Preterite, and Imperfect forms for 'Yo', 'Tú', and 'Nosotros'.
Mark any irregularities clearly.

**Step 2: Sentence Generation (10 total)**
Generate 10 sentences across different tenses (Indicative & Subjunctive).
* Contextualize the meaning clearly.
* Spanish + English translation.

**Step 3: Drill**
Provide 5 fill-in-the-blank exercises focusing on correct conjugation choice.
"""
    }
}


def get_verb_record(verbs: List[dict], lookup: Dict[str, int], infinitive: str) -> Optional[dict]:
    idx = lookup.get(infinitive.lower())
    return verbs[idx] if idx is not None else None


def merge_usage(verb: dict, overrides: Dict[str, dict]) -> dict:
    base = (verb.get("infinitive") or "").lower()

    # 1) start from overrides
    o = overrides.get(base, {})

    # 2) Load Seeds dynamically
    ref_seed, pron_seed = load_verb_seeds(VERBS_CAT_JSON)
    se_catalog = load_se_catalog(VERBS_CAT_JSON)
    
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
            # Default meaning shift if not in overrides
            meaning_shift = "meaning shift (see category in json)"
        elif seed_refl:
            is_pronominal = True
            pronominal_inf = seed_refl
            meaning_shift = "reflexive (self-directed)"
    
    # 3) CLASSIFY SE TYPE (Reflexive vs Pronominal vs Accidental)
    if is_pronominal and pronominal_inf:
        computed_type = classify_se_type(base, pronominal_inf, se_catalog)
        if computed_type:
            se_type = computed_type 

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