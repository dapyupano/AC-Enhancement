"""
Flask REST API for "Enhancing Aho-Corasick Algorithm with Context-Aware and
Approximate Matching for Medical Term Extraction from Handwritten Prescriptions".

Endpoints
---------
GET  /                       -> serves the frontend (index.html)
POST /api/ocr                -> multipart image upload -> {"text": "..."}
POST /api/analyze            -> {"text": "...", "mode": "original"|"enhanced"}
                                 -> matched medical terms

Run with:
    cd backend
    python app.py
Then open http://127.0.0.1:5000 in a browser.
"""

import os
import re
from flask import Flask, request, jsonify, send_from_directory

from algorithms.original_aho_corasick import OriginalAhoCorasick, load_patterns_from_csv
from algorithms.enhanced_aho_corasick import EnhancedAhoCorasick, load_dictionary
from data.context_data import (
    AMBIGUOUS_TERMS, NEGATIVE_CONTEXT, POSITIVE_CONTEXT,
    AMBIGUOUS_MEANINGS, HOT_STATE_THRESHOLD, CONTEXT_WINDOW_K,
    COMMON_ENGLISH_WORDS,
)
from data.ocr_corrections import apply_ocr_corrections, hardcoded_cleanup
from ac_compare import (
    OriginalAC as BenchOriginalAC,
    EnhancedAC as BenchEnhancedAC,
    PATTERNS as BENCH_PATTERNS,
    normalize_text as bench_normalize_text,
)
from memory_layout import get_run_memory_layout

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "data", "medical_dictionary.csv")
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")

# ---------------------------------------------------------------------------
# Build BOTH automatons once at startup and keep them resident in memory
# (per the thesis: "the skip table is loaded in the Flask app for it to stay
# in the memory and doesn't need to be rebuilt for every new search").
# ---------------------------------------------------------------------------
print("Building ORIGINAL Aho-Corasick automaton...")
_original_patterns = load_patterns_from_csv(CSV_PATH)
original_engine = OriginalAhoCorasick(_original_patterns)

print("Building ENHANCED Aho-Corasick automaton...")
_enhanced_patterns, _meaning_dict = load_dictionary(CSV_PATH)
enhanced_engine = EnhancedAhoCorasick(
    _enhanced_patterns,
    dictionary_meaning=_meaning_dict,
    ambiguous_terms=AMBIGUOUS_TERMS,
    negative_context=NEGATIVE_CONTEXT,
    positive_context=POSITIVE_CONTEXT,
    ambiguous_meanings=AMBIGUOUS_MEANINGS,
    hot_threshold=HOT_STATE_THRESHOLD,
    context_window_k=CONTEXT_WINDOW_K,
    common_words=COMMON_ENGLISH_WORDS,
)
print("Both automatons ready.")

# ---------------------------------------------------------------------------
# SOP 1 benchmark engines (ac_compare.py) — separate, lightweight pair used
# only to demonstrate failure-link traversal vs. precomputed skip table
# timing on the SOP 1 visualizer page. Built once at startup like the main
# engines above.
# ---------------------------------------------------------------------------
print("Building SOP 1 benchmark automatons (ac_compare.py)...")
bench_original = BenchOriginalAC(BENCH_PATTERNS)
bench_enhanced = BenchEnhancedAC(BENCH_PATTERNS)
print("SOP 1 benchmark automatons ready.")


# ------------------------------- routes -----------------------------------
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/api/ocr", methods=["POST"])
def ocr():
    if "image" not in request.files:
        return jsonify({"error": "No image file uploaded. Expected field name 'image'."}), 400

    file = request.files["image"]
    image_bytes = file.read()
    if not image_bytes:
        return jsonify({"error": "Uploaded image is empty."}), 400

    try:
        from ocr.trocr_engine import extract_text
        raw_text = extract_text(image_bytes)
    except Exception as exc:  # noqa: BLE001
        return jsonify({
            "error": "OCR failed. Make sure TrOCR dependencies (torch, "
                     "transformers, opencv-python, pillow) are installed and "
                     "that the model has been downloaded at least once "
                     "(requires internet access).",
            "detail": str(exc),
        }), 500

    # Clean up common OCR misreads before handing the text back to the
    # frontend / Aho-Corasick search (see data/ocr_corrections.py).
    text = apply_ocr_corrections(raw_text)
    text = hardcoded_cleanup(text)

    return jsonify({"text": text, "raw_text": raw_text})


@app.route("/api/analyze", methods=["POST"])
def analyze():
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")
    mode = payload.get("mode", "original")
    debug_memory = bool(payload.get("debug_memory"))

    if not text.strip():
        return jsonify({"error": "No text provided to analyze."}), 400

    if mode == "enhanced":
        hits = enhanced_engine.search(text)
        original_hits = original_engine.search(text)
        raw_matches = [{
            "term": h.get("matched", h["term"]),
            "category": h.get("category", ""),
            "meaning": h.get("meaning", "—"),
            "start": h["start"],
            "end": h["end"],
            "confidence": h.get("match_type", "exact"),
            "score": round(h.get("priority_score", 0), 2),
            "matched_dictionary_term": h.get("matched", h["term"]),
            "canonical_term": h["term"],
        } for h in hits]
        matches = []
        seen_matches = set()
        for match in raw_matches:
            key = (match["matched_dictionary_term"].upper(), match["category"])
            if key in seen_matches:
                continue
            seen_matches.add(key)
            matches.append(match)

        baseline_terms = {}
        for hit in original_hits:
            term = hit["term"].upper()
            if term in baseline_terms:
                continue
            score, context_valid = enhanced_engine.score_external_hit(hit, text)
            baseline_terms[term] = {
                "term": hit["term"],
                "start": hit["start"],
                "end": hit["end"],
                "score": round(score, 2),
                "context_valid": context_valid,
            }
        matches = [match for match in matches if not (
            match["matched_dictionary_term"].upper() in AMBIGUOUS_TERMS
            or match["canonical_term"].upper() in AMBIGUOUS_TERMS
        )]
        for match in matches:
            baseline_terms.pop(match["matched_dictionary_term"].upper(), None)
            baseline_terms.pop(match["canonical_term"].upper(), None)

        kept_spans = [
            (match["start"], match["end"])
            for match in matches
            if match["start"] < match["end"]
        ]

        def dropped_reason(item):
            span = (item["start"], item["end"])
            term = item["term"].upper()
            category = enhanced_engine.term_category.get(term, "")
            source_text = text.upper()
            left_ok = item["start"] == 0 or not source_text[item["start"] - 1].isalnum()
            right_ok = item["end"] >= len(source_text) or not source_text[item["end"]].isalnum()
            overlaps_kept = any(
                span[0] < kept_end and span[1] > kept_start
                for kept_start, kept_end in kept_spans
                if (kept_start, kept_end) != span
            )

            dosage_components = {"TAB", "TABS", "CAP", "CAPS", "VIAL", "AMPULE"}
            if overlaps_kept and (category in {"Dosage", "Symbol"} or term in dosage_components):
                return "overlapping"
            if not (left_ok and right_ok):
                return "false positive"
            if overlaps_kept:
                return "overlapping"

            if term in AMBIGUOUS_TERMS:
                return "ambiguous term"
            return "not retained by enhanced extraction"

        dropped_matches = [{
            "term": item["term"],
            "category": enhanced_engine.term_category.get(item["term"].upper(), ""),
            "meaning": "—",
            "start": item["start"],
            "end": item["end"],
            "confidence": "exact",
            "score": item["score"],
            "matched_dictionary_term": item["term"],
            "canonical_term": item["term"],
            "dropped": True,
            "drop_reason": dropped_reason(item),
        } for item in baseline_terms.values()]
        matches.extend(dropped_matches)

        abbreviations = [
            {"term": m["matched_dictionary_term"], "meaning": m["meaning"]}
            for m in matches if m["meaning"] != "—"
        ]
        # Keep component abbreviations visible even when a composite dosage
        # term wins overlap resolution in the identified terms list.
        for match in matches:
            if match["category"] not in {"Dosage", "Frequency"}:
                continue
            components = re.findall(r"(?i)(mg|mcg|ug|ml|g|tab|tabs|cap|caps)\b", match["term"])
            if match["category"] == "Frequency":
                components.extend(re.findall(r"(?i)\b(?:2x|3x)\b", match["term"]))
            for component in components:
                component = component.upper()
                meaning = enhanced_engine.term_meaning.get(component)
                if meaning:
                    abbreviations.append({"term": component, "meaning": meaning})
        # de-duplicate abbreviations panel
        seen = set()
        dedup_abbrev = []
        for a in abbreviations:
            if a["term"] not in seen:
                seen.add(a["term"])
                dedup_abbrev.append(a)

        detected_terms = sorted({m["matched_dictionary_term"] for m in matches})
        memory_layout = get_run_memory_layout(detected_terms)

        return jsonify({
            "mode": "enhanced",
            "matches": matches,
            "dropped_matches": dropped_matches,
            "abbreviations": dedup_abbrev,
            "memory_layout": memory_layout,
        })

    # ---- original / baseline algorithm: exact matches only, no meanings,
    #      no scoring, no context validation, no fuzzy matching ----
    hits = original_engine.search(text)
    hits.sort(key=lambda h: h["start"])
    raw_matches = [{
        "term": h["term"],
        "start": h["start"],
        "end": h["end"],
    } for h in hits]
    matches = []
    seen_matches = set()
    for match in raw_matches:
        key = match["term"].upper()
        if key in seen_matches:
            continue
        seen_matches.add(key)
        matches.append(match)

    return jsonify({
        "mode": "original",
        "matches": matches,
    })


@app.route("/api/benchmark", methods=["POST"])
def benchmark():
    """
    Runs ac_compare.py's OriginalAC vs EnhancedAC (precomputed skip table)
    on the server and returns real Python-side timing numbers, for the
    SOP 1 "Run Python Backend Benchmark" button.

    Body: { "text": "...", "iterations": 3000 }
    """
    import time as _time

    payload = request.get_json(silent=True) or {}
    raw_text = payload.get("text", "")
    iterations = int(payload.get("iterations", 3000))
    iterations = max(100, min(iterations, 200000))  # keep requests reasonable

    if not raw_text.strip():
        return jsonify({"error": "No text provided to benchmark."}), 400

    norm_text = bench_normalize_text(raw_text)

    orig_hits, orig_hops = bench_original.search(norm_text)
    enh_hits = bench_enhanced.search(norm_text)

    NUM_TRIALS = 5

    def time_it(fn, label):
        # Pooled mean across all trials (thesis formula):
        #
        #   x̄_f = (1 / n_f) * Σ_{i=1..n} [1_{f_i = f} * x_i]
        #
        # Each trial's `diff` IS the partial sum Σ x_i for that trial,
        # since every one of the `iterations` runs inside it belongs to
        # the same program f (indicator = 1 for all of them). Summing
        # the 5 trial diffs together gives the full numerator; dividing
        # by n_f = NUM_TRIALS * iterations (the *total* individual runs
        # across all trials, not just one trial) gives the true average
        # time per run - not a "best of 5" minimum.
        trial_diffs = []
        for trial in range(NUM_TRIALS):
            t0 = _time.perf_counter()
            for _ in range(iterations):
                fn(norm_text)
            t1 = _time.perf_counter()
            diff = t1 - t0
            print(f"{label} trial {trial}: t0={t0}, t1={t1}, diff={diff}, ")
            trial_diffs.append(diff)

        n_f = NUM_TRIALS * iterations                # e.g. 5 * 50,000 = 250,000
        diff_sum = sum(trial_diffs)                   # Σ 1_{f_i=f} x_i, e.g. 1.4845760998
        avg_seconds = diff_sum / n_f                  # x̄_f = (1/n_f) * diff_sum
        avg_us = avg_seconds * 1_000_000              # convert to microseconds
        print(
            f"{label.capitalize()} pooled average: n_f={n_f}, "
            f"sum_diff={diff_sum}, avg={round(avg_us, 3)} us\n"
        )
        return avg_seconds, trial_diffs, n_f

    t_orig, orig_trial_diffs, orig_n_f = time_it(lambda t: bench_original.search(t), "baseline")  # T(s)
    t_enh, enh_trial_diffs, enh_n_f = time_it(lambda t: bench_enhanced.search(t), "enhanced")     # T(o)
    speedup = (t_orig / t_enh) if t_enh > 0 else None

    return jsonify({
        "normalized_text": norm_text,
        "iterations": iterations,
        "pattern_count": len(BENCH_PATTERNS),
        "original": {
            "nodes": len(bench_original.nodes),
            "build_time_ms": round(bench_original.build_time * 1000, 3),
            "avg_time_us": round(t_orig * 1_000_000, 3),
            "failure_hops": orig_hops,
            "n_f": orig_n_f,
            "trial_diffs": [round(d, 10) for d in orig_trial_diffs],
            "hits": [{"term": p, "start": s, "end": e} for p, s, e in sorted(orig_hits, key=lambda h: h[1])],
        },
        "enhanced": {
            "nodes": len(bench_enhanced.nodes),
            "build_time_ms": round(bench_enhanced.build_time * 1000, 3),
            "avg_time_us": round(t_enh * 1_000_000, 3),
            "failure_hops": 0,
            "n_f": enh_n_f,
            "trial_diffs": [round(d, 10) for d in enh_trial_diffs],
            "hits": [{"term": p, "start": s, "end": e} for p, s, e in sorted(enh_hits, key=lambda h: h[1])],
        },
        "speedup": round(speedup, 3) if speedup else None,
    })


if __name__ == "__main__":
    app.run(debug=False, port=5050)