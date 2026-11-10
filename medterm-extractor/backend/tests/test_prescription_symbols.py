import os

from algorithms.enhanced_aho_corasick import EnhancedAhoCorasick, load_dictionary
from data.context_data import (
    AMBIGUOUS_TERMS,
    NEGATIVE_CONTEXT,
    POSITIVE_CONTEXT,
    AMBIGUOUS_MEANINGS,
    HOT_STATE_THRESHOLD,
    CONTEXT_WINDOW_K,
    COMMON_ENGLISH_WORDS,
)


def build_engine(common_words=None):
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "medical_dictionary.csv")
    patterns, meanings = load_dictionary(csv_path)
    return EnhancedAhoCorasick(
        patterns,
        dictionary_meaning=meanings,
        ambiguous_terms=AMBIGUOUS_TERMS,
        negative_context=NEGATIVE_CONTEXT,
        positive_context=POSITIVE_CONTEXT,
        ambiguous_meanings=AMBIGUOUS_MEANINGS,
        hot_threshold=HOT_STATE_THRESHOLD,
        context_window_k=CONTEXT_WINDOW_K,
        common_words=common_words,
    )


def test_microgram_symbols_are_recognized_in_prescription_notes():
    engine = build_engine()
    hits = engine.search("Take 500 µg BID")
    terms = {hit["term"] for hit in hits}
    assert "MCG" in terms
    assert "BID" in terms


def test_frequency_symbol_is_recognized_in_enhanced_matching():
    engine = build_engine()
    hits = engine.search("5 days (1-1-1)")
    terms = {hit["term"] for hit in hits}
    assert "1-1-1" in terms
    assert any(hit["category"] == "Symbol" for hit in hits if hit["term"] == "1-1-1")


def test_all_three_time_slot_combinations_are_recognized_in_enhanced_matching():
    engine = build_engine()
    schedules = [f"{morning}-{afternoon}-{night}"
                 for morning in (0, 1)
                 for afternoon in (0, 1)
                 for night in (0, 1)]

    hits = engine.search(" ".join(schedules))
    assert {hit["term"] for hit in hits} >= set(schedules)


def test_hash_symbol_is_recognized_in_enhanced_matching():
    engine = build_engine()

    hits = engine.search("Dolcet tablet #9")

    hash_hits = [hit for hit in hits if hit["term"] == "#9"]
    assert len(hash_hits) == 1
    assert hash_hits[0]["category"] == "Symbol"


def test_hash_symbol_absorbs_adjacent_quantity_in_either_order():
    engine = build_engine()

    assert {hit["term"] for hit in engine.search("#9 9#")} >= {"#9", "9#"}


def test_mg_unit_is_detected_as_an_abbreviation_from_dosage_tokens():
    engine = build_engine()

    hits = engine.search("Imoflox 200mg tablet #19")
    terms = {hit["term"] for hit in hits}

    assert "200MG" in terms
    assert "MG" in terms


def test_decimal_dosage_preserves_the_full_strength():
    engine = build_engine()

    hits = engine.search("carvedilol 6.25mg")
    dosage_terms = {
        hit["term"] for hit in hits
        if hit["category"] == "Dosage"
    }

    assert "6.25MG" in dosage_terms
    assert "25MG" not in dosage_terms


def test_ocr_typo_is_detected_as_a_fuzzy_match():
    engine = build_engine()

    fuzzy_hits = [hit for hit in engine.search("moflox") if hit["match_type"] == "fuzzy"]

    assert any(hit["matched"] == "IMOFLOX" for hit in fuzzy_hits)


def test_prescription_instruction_words_are_not_fuzzy_drugs():
    engine = build_engine()

    hits = engine.search("NASOFLO NASAL SPRAY #1 SIG 2 SPRAYS PER NOSTRIL")

    assert not any(hit.get("matched") == "SUPRAX" for hit in hits)


def test_contextual_abbreviations_are_detected_without_roman_text_false_positive():
    engine = build_engine()

    historical = engine.search("Chapter IV discusses the roman numeral century in old manuscripts")
    clinical_or = engine.search("Patient transferred to OR for emergency surgical procedure under anesthesia")
    clinical_ra = engine.search("History of RA, rheumatoid autoimmune disease confirmed by recent lab tests")

    assert not any(hit.get("matched") == "RIOPAN" for hit in historical)
    assert any(hit["term"] == "OR" for hit in clinical_or)
    assert any(hit["term"] == "RA" for hit in clinical_ra)


def test_supplemental_ambiguous_abbreviations_require_context():
    engine = build_engine()

    for term in ("IV", "IM", "OR"):
        assert not any(hit["term"] == term for hit in engine.search(term))

    assert any(hit["term"] == "IV" for hit in engine.search("IV fluid"))
    assert any(hit["term"] == "IM" for hit in engine.search("IM injection"))
    assert any(hit["term"] == "OR" for hit in engine.search("OR surgery"))
    assert any(hit["term"] == "AC" for hit in engine.search("AC"))
    assert any(hit["term"] == "ET" for hit in engine.search("ET"))


def test_clinical_narrative_words_are_not_fuzzy_drugs_or_treatments():
    engine = build_engine()

    hits = engine.search("Patient placed on RA, oxygen saturation stable via nasal cannula")
    hits += engine.search("The odds ratio OR reported in the regression analysis, 95 percent CI")

    assert not any(hit.get("matched") == "KLACID" for hit in hits)
    assert not any(hit.get("matched") == "DIALYSIS" for hit in hits)


def test_typo_in_multi_word_term_keeps_the_full_medical_term():
    engine = build_engine()

    hits = engine.search("METFORMIN HYDROCLORIDE")

    phrase_hits = [hit for hit in hits if hit["match_type"] == "fuzzy"]
    assert any(
        hit["matched"] == "METFORMIN HYDROCHLORIDE"
        and hit["term"] == "METFORMIN HYDROCLORIDE"
        for hit in phrase_hits
    )
    assert not any(hit["term"] == "METFORMIN" for hit in hits)


def test_meal_marker_glyphs_become_one_ascii_marker_group():
    engine = build_engine()

    hits = engine.search("•-- —-")
    marker_hits = [hit for hit in hits if hit["category"] == "Symbol"]

    assert {hit["term"] for hit in marker_hits} >= {"---", "--"}
    assert all(hit["meaning"] == "Take 1 tablet before/after meal/s" for hit in marker_hits)


def test_bullet_is_matched_directly_before_marker_normalization():
    engine = build_engine()

    hits = engine.search("•")

    bullet_hits = [hit for hit in hits if hit["term"] == "-"]
    assert len(bullet_hits) == 1
    assert bullet_hits[0]["matched"] == "•"


def test_bullet_symbol_remains_in_the_csv_dictionary():
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "medical_dictionary.csv")
    patterns, _ = load_dictionary(csv_path)

    assert any(term == "•" and category == "Symbol" for term, category, _ in patterns)
    assert any(term == "—" and category == "Symbol" for term, category, _ in patterns)


def test_platexan_correction_is_detected_as_a_drug():
    from data.ocr_corrections import apply_ocr_corrections

    text = apply_ocr_corrections("Clopidogrel 75mg\nPlateson #60\n1 - 0 - 0")
    engine = build_engine()

    assert "Platexan" in text
    assert any(
        hit["term"] == "PLATEXAN" and hit["category"] == "Drug"
        for hit in engine.search(text)
    )


def test_before_breakfast_and_supper_is_one_frequency():
    engine = build_engine(common_words=COMMON_ENGLISH_WORDS)

    hits = engine.search("10u - 6u\nbefore breakfast & supper")
    meal_frequency = [
        hit for hit in hits
        if hit["term"] == "BEFORE BREAKFAST & SUPPER"
    ]

    assert len(meal_frequency) == 1
    assert meal_frequency[0]["category"] == "Frequency"
    assert not any(hit.get("matched") == "SUPP" for hit in hits)


def test_analyze_reports_supp_and_single_hyphen_as_dropped_false_positives():
    from app import app as flask_app

    response = flask_app.test_client().post(
        "/api/analyze",
        json={
            "mode": "enhanced",
            "text": "Humulin 70/30 or Insuget 70/30 #2\n"
                    "10u - 6u\n10u \u2014 6u\nbefore breakfast & supper",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    dropped = {
        match["term"]: match
        for match in payload["dropped_matches"]
    }

    assert dropped["SUPP"]["drop_reason"] == "false positive"
    assert dropped["-"]["drop_reason"] == "false positive"
    assert dropped["\u2014"]["drop_reason"] == "false positive"
    assert any(
        match["term"] == "BEFORE BREAKFAST & SUPPER"
        and match["category"] == "Frequency"
        for match in payload["matches"]
    )


def test_analyze_reports_fuzzy_nebule_match_as_dropped():
    from app import app as flask_app

    text = (
        "Humulin 70/30\n"
        "or Insuget\n"
        "#1\n"
        "10u—0—10u\n\n"
        "Insulin syringe\n"
        "BD G#31 short needle\n"
        "#50\n\n"
        "OR\n\n"
        "Novomix\n"
        "#10\n"
        "10u—0—10u\n\n"
        "BD pen needle 4mm\n"
        "#50"
    )
    response = flask_app.test_client().post(
        "/api/analyze",
        json={"mode": "enhanced", "text": text},
    )

    assert response.status_code == 200
    payload = response.get_json()
    nebule_matches = [
        match for match in payload["dropped_matches"]
        if match["term"] == "NEBULE"
    ]

    assert len(nebule_matches) == 2
    assert all(match["confidence"] == "fuzzy" for match in nebule_matches)
    assert all(match["drop_reason"] == "fuzzy match" for match in nebule_matches)
    assert not any(
        match["matched_dictionary_term"] == "NEBULE" and not match.get("dropped")
        for match in payload["matches"]
    )


def test_analyze_keeps_fuzzy_drugs_in_identified_terms():
    from app import app as flask_app

    response = flask_app.test_client().post(
        "/api/analyze",
        json={
            "mode": "enhanced",
            "text": "Mupirocin\n+ Bethamethason\n(Foskina-B)\n"
                    "S Apply 2x/day x 7 days",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    identified_drugs = {
        match["matched_dictionary_term"]: match
        for match in payload["matches"]
        if match["category"] == "Drug" and not match.get("dropped")
    }

    assert identified_drugs["BETAMETHASONE"]["confidence"] == "fuzzy"
    assert identified_drugs["FOSKINA-B"]["confidence"] == "exact"
    assert not any(
        match["matched_dictionary_term"] in {"BETAMETHASONE", "FOSKINA-B"}
        for match in payload["dropped_matches"]
    )


def test_analyze_keeps_higher_scoring_overlapping_dosage_term():
    from app import app as flask_app

    text = (
        "Dibencozide 3mg\n"
        "(Heraclene forte cap)\n"
        "#30\n"
        "S 1 cap once daily\n\n"
        "Ibuprofen 200 mg/tab\n"
        "S 1 q 6 hrs"
    )
    response = flask_app.test_client().post(
        "/api/analyze",
        json={"mode": "enhanced", "text": text},
    )

    assert response.status_code == 200
    payload = response.get_json()
    identified_one_cap = next(
        match for match in payload["matches"]
        if match["matched_dictionary_term"] == "1 CAP"
    )
    dropped_cap = next(
        match for match in payload["dropped_matches"]
        if match["matched_dictionary_term"] == "CAP"
    )

    assert identified_one_cap["score"] > dropped_cap["score"]
    assert dropped_cap["drop_reason"] == "overlapping"


def test_six_hours_q_and_sodium_symbol_are_recognized():
    engine = build_engine()

    six_hours = engine.search("q 6 hrs")
    sodium = engine.search("Na hyaluronate")

    assert any(hit["term"] == "6 HRS" and hit["category"] == "Frequency" for hit in six_hours)
    assert any(
        hit["term"] == "Q"
        and hit["category"] == "Symbol"
        and hit["meaning"] == "Every or each"
        for hit in six_hours
    )
    assert any(
        hit["term"] == "NA"
        and hit["category"] == "Symbol"
        and hit["meaning"] == "Sodium"
        for hit in sodium
    )


def test_prescription_17_frequency_phrases_are_recognized():
    from app import app as flask_app

    response = flask_app.test_client().post(
        "/api/analyze",
        json={
            "mode": "enhanced",
            "text": "Salbutamol nebule\nS 1 nebule every 8 hrs for 3-5 days",
        },
    )

    assert response.status_code == 200
    frequencies = {
        match["term"]
        for match in response.get_json()["matches"]
        if match["category"] == "Frequency" and not match.get("dropped")
    }
    assert "EVERY 8 HRS" in frequencies
    assert "3-5 DAYS" in frequencies


def test_priority_score_uses_all_four_requested_components():
    engine = build_engine()

    hits = engine.search("MONTELUKAST 10MG/TAB #14 SIG 1 TAB AT BEDTIME")
    scores = {hit["term"]: hit["priority_score"] for hit in hits}

    expected_scores = {
        "MONTELUKAST": 1.0,
        "AT BEDTIME": (10 / 11 + 3) / 4.0,
        "10MG/TAB": (8 / 11 + 3) / 4.0,
        "1 TAB": (5 / 11 + 3) / 4.0,
        "SIG": (3 / 11 + 3) / 4.0,
        "#14": (3 / 11 + 3) / 4.0,
    }
    assert set(scores) == set(expected_scores)
    assert all(abs(scores[term] - expected) < 1e-12
               for term, expected in expected_scores.items())
