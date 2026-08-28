"""
Context-awareness reference data for the ENHANCED Aho-Corasick pipeline only.

Per the thesis (Chapter 3, "Context-Aware Validation"), some dictionary terms
are lexically ambiguous: the same string can be a clinical symptom/drug term
in one context and an ordinary, non-clinical word in another
(e.g. "cold" as an illness vs. "cold compress").

AMBIGUOUS_TERMS   - terms that require a surrounding-token check before being
                     accepted as a valid clinical match.
NEGATIVE_CONTEXT  - tokens that, if found in the ±k window around a hit,
                     suggest the term is NOT being used clinically -> reject.
POSITIVE_CONTEXT  - tokens that, if found in the ±k window, confirm clinical
                     usage -> accept.
CONTEXT_WINDOW_K  - how many tokens to the left/right of a hit are inspected.

None of this is used by the original/baseline algorithm, which performs
exact matching only, exactly as specified in the paper's "Existing Algorithm".
"""

# Hot/cold classification threshold (theta) used by ENHANCED_AC_BUILD Phase 3.
# A state with >= HOT_STATE_THRESHOLD outgoing transitions is stored as a
# flat array ("hot"); otherwise it is stored as a hash map ("cold").
HOT_STATE_THRESHOLD = 4

# Number of tokens to inspect on each side of a candidate match.
CONTEXT_WINDOW_K = 3

AMBIGUOUS_TERMS = {
    "COLD",
    "PAIN",
    "TAB",
    "IV",
}

NEGATIVE_CONTEXT = {
    "COLD": {"COMPRESS", "WATER", "DRINK", "PACK", "TOWEL", "WEATHER"},
    "PAIN": {"PAINTING", "PAINT"},
    "TAB": {"KEYBOARD", "BROWSER"},
    "IV": {"ROMAN", "NUMERAL", "CHAPTER"},
}

POSITIVE_CONTEXT = {
    "COLD": {"FEVER", "COUGH", "MEDICINE", "SYMPTOMS", "FLU", "SORE", "THROAT", "MG", "MCG", "UG"},
    "PAIN": {"RELIEVER", "MEDICINE", "MILD", "SEVERE", "TAKE", "MG", "MCG", "UG", "TAB", "TABS"},
    "TAB": {"MG", "MCG", "UG", "ML", "TAKE", "ONCE", "TWICE", "OD", "BID", "TID", "PO"},
    "IV": {"FLUID", "DRIP", "LINE", "INFUSION", "PUSH"},
}
