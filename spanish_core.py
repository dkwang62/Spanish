# spanish_core.py (v8.0)
# Core: Jehle DB + Pronominal JSON + Prompts + Se Classification
# Updated: Added Psychological/Experiencer verb support (gustar-like)

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
def load_verb_seeds(json_path: str = VERBS_CAT_JSON) -> Tuple[Dict[str, str], Dict[str, str], List[str]]:
    """
    Parses the categorized JSON into lookup structures.
    Returns: (reflexive_flat, pronominal_flat, experiencer_list)
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
    
    # Experiencer list (just a set of infinitives, e.g., 'gustar', 'doler')
    experiencer_set = set()
    exp_cats = taxonomy.get("experiencer", {}).get("categories", {})
    for _, content in exp_cats.items():
        for base in content.get("verbs", {}).keys():
            experiencer_set.add(base.lower())
    
    return reflexive_flat, pronominal_flat, list(experiencer_set)


def classify_se_type(infinitive: str, pronominal_infinitive: str | None, se_catalog: dict) -> str | None:
    """
    Returns one of: 'reflexive', 'pronominal', 'accidental_dative', 'experiencer', or None.
    """
    inf = infinitive.lower()
    
    # 1. Check Experiencer (Base Infinitive Lookup)
    # Because 'gustar' is the dictionary entry, not 'gustarse' in this context.
    taxonomy = se_catalog.get("verb_taxonomy", {})
    
    def _get_set(root_key, use_values=True):
        s = set()
        cats = taxonomy.get(root_key, {}).get("categories", {})
        for _, content in cats.items():
            # For reflexive/pronominal, we often look at the 'values' (pron form).
            # For experiencer, we look at the 'keys' (base form).
            target_dict = content.get("verbs", {})
            iterator = target_dict.values() if use_values else target_dict.keys()
            s.update([v.lower() for v in iterator])
        return s

    exp_all = _get_set("experiencer", use_values=False) # Check base keys: gustar, doler
    if inf in exp_all:
        return "experiencer"

    # 2. Check Pronominal forms (if provided)
    if not pronominal_infinitive:
        return None

    pro = pronominal_infinitive.lower()
    acc_all = _get_set("accidental_dative", use_values=True)
    ref_all = _get_set("reflexive", use_values=True)
    pro_all = _get_set("pronominal", use_values=True)

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
        "gustar": {"is_pronominal": False, "se_type": "experiencer", "meaning_shift": "pleases (inverted subject)"}
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
    # 1. Reflexive (Updated w/ Semantic Check)
    "REFLEXIVE_PLACEMENT_CORE": {
        "name": "Reflexive / se placement drill",
        "prompt": """You are the 'Spanish Radix' engine (v1). Execute the following task strictly.

**Global Constraints & Safety Rules:**
1. **Consistency (A–D):** Use the SAME subject and SAME non-verb vocabulary across all sentences in Sections A–D. Vary ONLY the verb tense/mood and clitic placement rules required by the structure.
2. **Highlighting:** Highlight the CLITIC + VERB in **ALL CAPS** in ALL sections (e.g., "SE HACE", "HACERSE", "HACIÉNDOSE", "HÁZTE", "NO TE HAGAS").
3. **Time/Tense Agreement:** If you use time expressions (hoy/ayer/mañana), they must match the verb tense (present/past/future).
4. **Subjunctive Licensing:** For Section E, use subjunctive ONLY with valid triggers (querer que, dudar que, es posible que, recomendar que, etc.).
5. **Semantic Validity (Critical):** Avoid sentences that are morphologically correct but conceptually unnatural in Spanish. In particular:
   - Do NOT pair time expressions with situations that imply an unrealistic instantaneous change (e.g., becoming an expert “ayer” without a plausible frame).
   - If the target meaning typically implies a gradual process, prefer neutral time frames (hoy/mañana) or choose a complement/context that makes the change plausible.
   - Ensure number/person agreement and conceptual naturalness for imperatives (e.g., avoid “nosotros” + singular predicate that sounds unnatural; if needed, choose vocabulary that works for all required persons).

**Task:** REFLEXIVE_PLACEMENT_CORE
**Target Verb:** {infinitive}
**Pronominal Form:** {pronominal_infinitive}
**Meaning Shift:** {meaning_shift}

**Step 1: Explain Rules**
Briefly explain clitic placement for:
- Conjugated verbs (finite): clitic BEFORE the verb.
- Infinitives: clitic ATTACHED to the infinitive (and mention the alternative of pre-verbal placement only if structure permits).
- Gerunds: clitic ATTACHED to the gerund (and mention the alternative of pre-verbal placement only if structure permits).
- Imperatives: Positive = attached; Negative = before the verb.

**Step 2: Generate Sections (5 sentences each)**

* **Section A: Indicative (Clitic before conjugated verb)**
  - Vary tenses (Present, Preterite, Future, etc.).
  - Format: Spanish (English)

* **Section B: Infinitive (Attached clitic)**
  - Structure: conjugated verb + infinitive WITH clitic attached.

* **Section C: Gerund (Attached clitic)**
  - Structure: estar + gerund WITH clitic attached.

* **Section D: Imperatives**
  - Mix Positive (attached) and Negative (clitic before verb).
  - Keep vocabulary consistent; ensure agreement and naturalness.

* **Section E: Subjunctive**
  - Structure: [Trigger] + que + [Different Subject] + [Clitic] + [Subjunctive Verb].
  - Note: Subject must change from trigger to clause.
  - Only use licensed subjunctive triggers.

**Step 3: Drill**
Provide 10 fill-in-the-blank sentences mixing all structures above + Answer Key.
- Apply the SAME highlighting rule.
- Strictly avoid semantically unnatural items (even if grammatically correct).
- Do not include “edge-case” drills that require extra context to sound natural.
"""
    },
    # 2. Pronominal
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
Explain the semantic contrast in 4–5 lines. Focus on the shift in meaning or nuance caused by the clitic.

**Step 2: Contrast Pairs (12 Total)**
Generate 12 pairs of sentences. In each pair:
* **Sentence A:** Uses the Base Verb ({infinitive}).
* **Sentence B:** Uses the Pronominal Verb ({pronominal_infinitive}).
* Both sentences should share context where possible to highlight the difference.

**Distribution Requirements:**
* **6 Pairs:** Present Tense
* **3 Pairs:** Past Tense (Preterite vs Imperfect where natural)
* **3 Pairs:** Future or "Ir a + inf"

**Step 3: Decision Drill**
Create 10 short scenarios/sentences with a blank.
* The user must decide between the Base or Pronominal form.
* Provide the Answer Key with a one-line explanation for each.
"""
    },
    # 3. Accidental Core
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
    # 4. Accidental Contrast
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
    # 5. NEW: Psychological / Experiencer Drill
    "GUSTAR_EXPERIENCER_DRILL": {
        "name": "Gustar-like (Experiencer) drill",
        "prompt": """You are the 'Spanish Radix' engine (v1).

**Target Pattern:** Psychological/Experiencer Verbs (Verbs like Gustar)
**Target Verb:** {infinitive}
**Pattern:** Indirect Object (Experiencer) + Verb (3rd Person) + Subject (Theme).

**Step 1: Explanation**
Explain that in this structure, the "subject" (grammatically) is what pleases/bores/hurts, and the person feeling it is marked by an Indirect Object pronoun (me/te/le/nos/os/les).

**Step 2: Conjugation Table (Specific)**
Show a grid for the PRESENT tense of {infinitive} in this structure:
- A mí me ...
- A ti te ...
- A él/ella le ...
- A nosotros nos ...
- A vosotros os ...
- A ellos les ...
*(Include singular and plural verb forms: e.g., 'gusta' vs 'gustan')*

**Step 3: Sentence Generation (12 sentences)**
Generate sentences mixing different tenses (Present, Preterite, Imperfect, Conditional).
- Rotate the experiencer (Me, Te, Le, Nos, Les).
- **Constraint:** Highlight the IO PRONOUN + VERB in **ALL CAPS** (e.g., "ME GUSTA", "LE DOLÍA").
- Include questions (e.g., "¿Te interesa...?").

**Step 4: Drill**
Provide 10 fill-in-the-blank items where the user must supply the correct Indirect Object Pronoun and/or the correct Verb Form based on the subject.
"""
    },
    # 6. Standard Fallback
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
    ref_seed, pron_seed, exp_seed_list = load_verb_seeds(VERBS_CAT_JSON)
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
    
    # 3) CLASSIFY SE TYPE (Reflexive vs Pronominal vs Accidental vs Experiencer)
    
    # A) Check if it is explicitly an Experiencer verb (base form)
    # This overrides regular classification because 'gustar' is not pronominal
    computed_type = classify_se_type(base, pronominal_inf, se_catalog)
    
    if computed_type:
        se_type = computed_type 
        if se_type == "experiencer":
            meaning_shift = "Psychological/Experiencer (IO construction)"

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