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
CONTEXT_WINDOW_K = 5

AMBIGUOUS_TERMS = {
    "COLD",
    "PAIN",
    "TAB",
    "IV",
    "PT",
    "ER",
    "OR",
    "RA",
    "MS",
    "MI",
    "PE",
    "PP",
    "PS",
    "OD",
    "ID",
    "IM",
    "DC",
    "DO",
    "DX",
    "HX",
    "SX",
    "CT",
    "US",
    "XR",
    "PTT",
}

NEGATIVE_CONTEXT = {
    "COLD": {"WATER", "DRINK", "PACK", "TOWEL", "WEATHER", "ATTITUDE"},
    "PAIN": {"PAINTING", "PAINT"},
    "TAB": {"KEYBOARD", "BROWSER", "TABULATOR", "WEBSITE", "WINDOW"},
    "IV": {"ROMAN", "NUMERAL", "CHAPTER", "CENTURY", "VOLUME"},
    "PT": {"ADMITTED", "AGE", "BLEEDING", "BP", "CLOTTING", "COAGULATION", "DIAGNOSIS", "DISCHARGED", "FEMALE", "FOLLOWUP", "GESTATION", "HCG", "HISTORY", "HR", "INR", "LMP", "MALE", "MEDICATION", "PATIENT", "PATIENTS", "PREGNANCY", "PREGNANT", "SYMPTOMS", "TEMP", "TRIMESTER", "URINE", "VISIT", "WARFARIN", "WEIGHT"},
    "ER": {"ENGINEER", "TEACHER", "WORKER"},
    "OR": {"CHOICE", "EITHER", "OPTION"},
    "RA": {"ANCIENT", "ROMAN"},
    "MS": {"EXCEL", "MICROSOFT", "WINDOWS", "WORD"},
    "MI": {"MICHIGAN", "STATE"},
    "PE": {"CLASS", "EDUCATION", "SCHOOL", "SPORT"},
    "PP": {"POWERPOINT", "PRESENTATION", "SLIDE"},
    "PS": {"CONSOLE", "GAME", "PLAYSTATION"},
    "OD": {"DISK", "DRIVE", "OPTICAL"},
    "ID": {"ACCOUNT", "IDENTITY", "USERNAME"},
    "IM": {"CHAT", "INSTANT", "MESSAGE"},
    "DC": {"COMIC", "COMICS", "WASHINGTON"},
    "CT": {"CONNECTICUT", "STATE"},
    "US": {"AMERICA", "STATES", "UNITED"},
    "XR": {"ERROR", "UNKNOWN"},
}

POSITIVE_CONTEXT = {
    "COLD": {"FEVER", "COUGH", "MEDICINE", "SYMPTOMS", "FLU", "SORE", "THROAT", "MG", "MCG", "UG", "COMPRESS", "TAB", "TABS"},
    "PAIN": {"RELIEVER", "MEDICINE", "MILD", "SEVERE", "TAKE", "MG", "MCG", "UG", "TAB", "TABS"},
    "TAB": {"MG", "MCG", "UG", "ML", "TAKE", "ONCE", "TWICE", "OD", "BID", "TID", "PO"},
    "IV": {"FLUID", "DRIP", "LINE", "INFUSION", "PUSH", "INTRAVENOUS", "SALINE"},
    "PT": {"ADMITTED", "AGE", "BLEEDING", "BP", "CLOTTING", "COAGULATION", "DIAGNOSIS", "DISCHARGED", "FEMALE", "FOLLOWUP", "GESTATION", "HCG", "HISTORY", "HR", "INR", "LMP", "MALE", "MEDICATION", "PATIENT", "PATIENTS", "PREGNANCY", "PREGNANT", "SYMPTOMS", "TEMP", "TRIMESTER", "URINE", "VISIT", "WARFARIN", "WEIGHT"},
    "ER": {"ADMISSION", "AMBULANCE", "DEPARTMENT", "EMERGENCY", "ROOM", "TRAUMA"},
    "OR": {"ANESTHESIA", "ODDS", "OPERATING", "PROCEDURE", "RATIO", "REGRESSION", "STATISTICS", "SURGERY", "SURGICAL", "THEATER", "THEATRE"},
    "RA": {"ARTHRITIS", "AUTOIMMUNE", "INFLAMMATION", "JOINT", "LITER", "NASAL", "OXYGEN", "RESPIRATORY", "RHEUMATOID", "SATURATION"},
    "MS": {"CARDIAC", "MITRAL", "MORPHINE", "MULTIPLE", "MURMUR", "SCLEROSIS", "STENOSIS", "SULFATE", "VALVE"},
    "MI": {"CARDIAC", "CHEST", "ECG", "INFARCTION", "MYOCARDIAL", "NSTEMI", "STEMI"},
    "PE": {"CHEST", "CLOT", "DVT", "DYSPNEA", "EMBOLISM", "PULMONARY", "THROMBUS"},
    "PP": {"BLEEDING", "DELIVERY", "POSTPARTUM", "PRESSURE", "PULSE"},
    "PS": {"CARDIOLOGY", "PRESSURE", "PULMONARY", "STENOSIS", "SUPPORT", "VENTILATION"},
    "OD": {"CAPSULE", "DAILY", "DOSE", "EYE", "MEDICATION", "OCULAR", "RIGHT", "TABLET", "TAKE"},
    "ID": {"IMMUNIZATION", "INJECTION", "INTRADERMAL", "SKIN", "VACCINE"},
    "IM": {"DELTOID", "INJECTION", "INTRAMUSCULAR", "MUSCLE", "VACCINE"},
    "DC": {"DISCHARGE", "DISCHARGED", "DISCONTINUE", "DISCONTINUED", "MEDICATION", "PATIENT", "THERAPY"},
    "DO": {"DATE", "DOCTOR", "DOSE", "MEDICATION", "ONSET", "ORDER"},
    "DX": {"ASSESSMENT", "DIAGNOSED", "DIAGNOSIS", "MEDICAL", "PATIENT", "SYMPTOMS"},
    "HX": {"FAMILY", "HISTORY", "MEDICAL", "PAST", "PATIENT", "SURGICAL"},
    "SX": {"CLINICAL", "PATIENT", "PRESENTING", "SYMPTOM", "SYMPTOMS"},
    "CT": {"ABDOMEN", "BRAIN", "CHEST", "CONTRAST", "HEAD", "IMAGING", "SCAN", "TOMOGRAPHY"},
    "US": {"FETAL", "GESTATION", "IMAGING", "PREGNANCY", "SONOGRAPHY", "ULTRASOUND", "UTERUS"},
    "XR": {"BONE", "CHEST", "FRACTURE", "IMAGING", "RADIOGRAPH", "X-RAY", "XRAY"},
    "PTT": {"APTT", "CLOTTING", "COAGULATION", "PARTIAL", "THROMBOPLASTIN", "TIME"},
}


# Optional meaning-level context for ambiguous clinical abbreviations.
AMBIGUOUS_MEANINGS = {
    "PT": {
        "Patient": {"HISTORY", "AGE", "MALE", "FEMALE", "DIAGNOSIS", "SYMPTOMS", "VISIT", "ADMITTED", "REPORTS", "ABDOMINAL", "PAIN", "NAUSEA"},
        "Pregnancy Test": {"PREGNANCY", "PREGNANT", "HCG", "LMP", "GESTATION", "URINE", "TRIMESTER", "POSITIVE", "NEGATIVE", "OB"},
        "PROTHROMBIN_TIME": {"INR", "COAGULATION", "CLOTTING", "BLEEDING", "WARFARIN", "PTT"},
    },
    "IV": {
        "INTRAVENOUS": {"FLUID", "DRIP", "INFUSION", "LINE", "PUSH", "SALINE"},
        "ROMAN_NUMERAL": {"ROMAN", "NUMERAL", "CHAPTER", "VOLUME", "CENTURY"},
    },
    "OD": {
        "ONCE_DAILY": {"DOSE", "DAILY", "MEDICATION", "TABLET", "TAKE"},
        "RIGHT_EYE": {"EYE", "OCULAR", "VISION", "OPHTHALMIC", "RETINA"},
    },
    "OR": {
        "OPERATING_ROOM": {"SURGERY", "SURGICAL", "OPERATING", "ANESTHESIA", "PROCEDURE"},
        "ODDS_RATIO": {"STATISTICS", "ODDS", "RATIO", "REGRESSION", "CI", "CONFIDENCE"},
    },
    "RA": {
        "RHEUMATOID_ARTHRITIS": {"RHEUMATOID", "ARTHRITIS", "JOINT", "AUTOIMMUNE"},
        "ROOM_AIR": {"OXYGEN", "SATURATION", "RESPIRATORY", "LITER", "NASAL"},
    },
    "MS": {
        "MULTIPLE_SCLEROSIS": {"NEUROLOGY", "SCLEROSIS", "RELAPSE", "LESION"},
        "MORPHINE_SULFATE": {"MORPHINE", "SULFATE", "OPIOID", "MG", "INJECTION"},
        "MITRAL_STENOSIS": {"MITRAL", "VALVE", "MURMUR", "CARDIAC", "ECHOCARDIOGRAM"},
    },
}
