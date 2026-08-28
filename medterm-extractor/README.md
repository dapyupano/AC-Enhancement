# Medical Term Extractor — Original vs. Enhanced Aho-Corasick

A web system that extracts medical terms from handwritten doctor's
prescriptions using TrOCR, then locates drug names, dosages, frequencies,
abbreviations, and treatments using **two selectable algorithms**:

- **Original** — the classical/baseline Aho-Corasick algorithm exactly as
  presented in Chapter 1 of the thesis ("Existing Algorithm"): exact
  multi-pattern matching only, no skip table, no context awareness, no
  fuzzy matching, no abbreviation-meaning lookup.
- **Enhanced** — the proposed algorithm from Chapter 3 ("Proposed
  Algorithm"): precomputed skip table (Objective 1), two-pass BFS memory
  layout (Objective 2), tiered hot/cold transition storage (Objective 3),
  context-aware validation, priority-weighted scoring, abbreviation-meaning
  lookup, and fuzzy (edit-distance) matching.

A navigation bar at the top lets you switch between the two modes at any
time; the same uploaded/typed text can be re-evaluated under either
algorithm so you can directly compare their behavior (e.g. try
`"...take with cold compress"` and see the Original algorithm falsely tag
"cold" as an illness, while the Enhanced algorithm suppresses it).

## Project layout

```
medterm-extractor/
├── backend/
│   ├── app.py                          Flask REST API + static file server
│   ├── requirements.txt
│   ├── algorithms/
│   │   ├── original_aho_corasick.py    Baseline AC-Build / AC-Search
│   │   └── enhanced_aho_corasick.py    Enhanced 5-phase build + 7-phase search
│   ├── ocr/
│   │   └── trocr_engine.py             TrOCR + OpenCV/Pillow preprocessing
│   └── data/
│       ├── medical_dictionary.csv      Drug/Dosage/Frequency/Abbreviation/Treatment
│       └── context_data.py             Ambiguous terms + pos/neg context sets
└── frontend/
    ├── index.html
    ├── style.css
    └── script.js
```

## Setup (VS Code)

1. Open the `medterm-extractor` folder in VS Code.
2. Create and activate a virtual environment:
   ```bash
   cd backend
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   > `torch` and `transformers` are needed only for the OCR (`Scan & Extract`)
   > feature. The first OCR request downloads `microsoft/trocr-large-handwritten`
   > from Hugging Face (a few hundred MB) — this requires an internet
   > connection once; afterwards it's cached locally.
4. Run the server:
   ```bash
   python app.py
   ```
5. Open **http://127.0.0.1:5050** in your browser. The Flask app also
   serves the `frontend/` folder directly, so no separate frontend server
   is needed.

## Using the app

1. Pick **Original Algorithm** or **Enhanced Algorithm** from the nav bar.
2. Either:
   - Upload a prescription image and click **Scan & Extract** (runs TrOCR,
     fills the text box, and automatically runs the selected algorithm), or
   - Type/paste prescription text directly into the text box.
3. Click **Re-evaluate** any time (e.g. after editing the extracted text,
   or after switching modes) to re-run the currently selected algorithm.
4. Results show:
   - The extracted text with color-coded highlights by category.
   - A table of identified terms (Enhanced mode adds a confidence
     column — Exact/Fuzzy — and a normalized priority score).
   - An **Abbreviations Panel** mapping shorthand to full meanings
     (Enhanced mode only — the original algorithm has no meaning-lookup
     phase).

## Extending the medical dictionary

Add rows to `backend/data/medical_dictionary.csv` using the schema:

```
term,category,meaning
AMOXICILLIN,Drug,
BID,Abbreviation,Twice a day
```

`category` must be one of `Drug`, `Dosage`, `Frequency`, `Abbreviation`,
`Treatment` (used for color-coding and the results table). `meaning` is
only used for `Abbreviation` rows and only affects the Enhanced algorithm.
Restart the Flask app after editing the CSV so both automatons rebuild.

## Tuning the enhanced algorithm

`backend/data/context_data.py` exposes the tunable parameters described in
the thesis:

- `HOT_STATE_THRESHOLD` (θ) — hot/cold classification cutoff (Objective 3).
- `CONTEXT_WINDOW_K` — ±k token window for context-aware validation.
- `AMBIGUOUS_TERMS`, `NEGATIVE_CONTEXT`, `POSITIVE_CONTEXT` — the
  disambiguation rules (e.g. "cold" as a symptom vs. "cold compress").

The SOP 1 benchmark measures the automaton search structures only: classical
failure-link traversal versus the enhanced precomputed skip table. It does
not include OCR, context validation, scoring, or fuzzy matching, which are
measured by the main extraction API.
