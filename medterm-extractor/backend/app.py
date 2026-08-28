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
from flask import Flask, request, jsonify, send_from_directory

from algorithms.original_aho_corasick import OriginalAhoCorasick, load_patterns_from_csv
from algorithms.enhanced_aho_corasick import EnhancedAhoCorasick, load_dictionary
from data.context_data import (
    AMBIGUOUS_TERMS, NEGATIVE_CONTEXT, POSITIVE_CONTEXT,
    HOT_STATE_THRESHOLD, CONTEXT_WINDOW_K,
)
from data.ocr_corrections import apply_ocr_corrections, hardcoded_cleanup
from ac_compare import (
    OriginalAC as BenchOriginalAC,
    EnhancedAC as BenchEnhancedAC,
    PATTERNS as BENCH_PATTERNS,
    normalize_text as bench_normalize_text,
)

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
    hot_threshold=HOT_STATE_THRESHOLD,
    context_window_k=CONTEXT_WINDOW_K,
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

    if not text.strip():
        return jsonify({"error": "No text provided to analyze."}), 400

    if mode == "enhanced":
        hits = enhanced_engine.search(text)
        matches = [{
            "term": h["term"],
            "category": h.get("category", ""),
            "meaning": h.get("meaning", "—"),
            "start": h["start"],
            "end": h["end"],
            "confidence": h.get("match_type", "exact"),
            "score": round(h.get("priority_score", 0), 2),
            "matched_dictionary_term": h.get("matched", h["term"]),
        } for h in hits]

        abbreviations = [
            {"term": m["matched_dictionary_term"], "meaning": m["meaning"]}
            for m in matches if m["meaning"] != "—"
        ]
        # de-duplicate abbreviations panel
        seen = set()
        dedup_abbrev = []
        for a in abbreviations:
            if a["term"] not in seen:
                seen.add(a["term"])
                dedup_abbrev.append(a)

        return jsonify({
            "mode": "enhanced",
            "matches": matches,
            "abbreviations": dedup_abbrev,
        })

    # ---- original / baseline algorithm: exact matches only, no meanings,
    #      no scoring, no context validation, no fuzzy matching ----
    hits = original_engine.search(text)
    hits = [h for h in hits if h.get("category") != "Symbol"]
    hits.sort(key=lambda h: h["start"])
    matches = [{
        "term": h["term"],
        "category": h.get("category", ""),
        "start": h["start"],
        "end": h["end"],
    } for h in hits]

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

    def time_it(fn):
        best = None
        for _ in range(5):  # 5 trials, take the best (min) like main.py
            t0 = _time.perf_counter()
            for _ in range(iterations):
                fn(norm_text)
            t1 = _time.perf_counter()
            avg = (t1 - t0) / iterations
            if best is None or avg < best:
                best = avg
        return best

    t_orig = time_it(lambda t: bench_original.search(t))
    t_enh = time_it(lambda t: bench_enhanced.search(t))
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
            "hits": [{"term": p, "start": s, "end": e} for p, s, e in sorted(orig_hits, key=lambda h: h[1])],
        },
        "enhanced": {
            "nodes": len(bench_enhanced.nodes),
            "build_time_ms": round(bench_enhanced.build_time * 1000, 3),
            "avg_time_us": round(t_enh * 1_000_000, 3),
            "failure_hops": 0,
            "hits": [{"term": p, "start": s, "end": e} for p, s, e in sorted(enh_hits, key=lambda h: h[1])],
        },
        "speedup": round(speedup, 3) if speedup else None,
    })


if __name__ == "__main__":
    app.run(debug=False, port=5050)
