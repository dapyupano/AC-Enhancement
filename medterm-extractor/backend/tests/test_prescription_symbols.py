import os

from algorithms.enhanced_aho_corasick import EnhancedAhoCorasick, load_dictionary
from data.context_data import (
    AMBIGUOUS_TERMS,
    NEGATIVE_CONTEXT,
    POSITIVE_CONTEXT,
    AMBIGUOUS_MEANINGS,
    HOT_STATE_THRESHOLD,
    CONTEXT_WINDOW_K,
)


def build_engine():
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
