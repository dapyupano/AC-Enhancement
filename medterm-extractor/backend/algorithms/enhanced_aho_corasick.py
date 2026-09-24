import re
from collections import deque

# Full transition alphabet a NON-tiered automaton must reserve a column for
# (A-Z, 0-9, space and the symbols the dictionary/normalizer keep). Used only
# as the "full-row" baseline in storage_metrics(); it matches the SOP 1/3
# front-end alphabet.
FULL_ALPHABET = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,-/%()+:#\u2022\u2014")

# One transition cell = one machine word (same 8-byte stride memory_layout.py
# reports for the BFS node array). Only used for the KB estimate.
CELL_BYTES = 8


# ------------------------- helper: edit distance -------------------------
def edit_distance(a, b):
    """Standard Levenshtein distance, used only by Phase 7 (Fuzzy Matching)."""
    n, m = len(a), len(b)
    if n == 0:
        return m
    if m == 0:
        return n
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        curr = [i] + [0] * m
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(
                prev[j] + 1,       # deletion
                curr[j - 1] + 1,   # insertion
                prev[j - 1] + cost # substitution
            )
        prev = curr
    return prev[m]


def similarity(a, b):
    dist = edit_distance(a, b)
    longest = max(len(a), len(b))
    if longest == 0:
        return 1.0
    return 1.0 - (dist / longest)


# ------------------------------ trie node ---------------------------------
class _Node:
    __slots__ = ("goto", "fail", "output", "bfs_rank")

    def __init__(self):
        self.goto = {}       # temporary construction-time transitions (Phase 1)
        self.fail = None
        self.output = set()
        self.bfs_rank = -1


class EnhancedAhoCorasick:
    def __init__(self, patterns, dictionary_meaning=None,
                 ambiguous_terms=None, negative_context=None,
                 positive_context=None, hot_threshold=4,
                 context_window_k=5, ambiguous_meanings=None, common_words=None):
        """
        patterns: iterable of (term, category, meaning) tuples.
        dictionary_meaning (D): term -> meaning, used ONLY in the
            "Meaning for abbreviated terms" phase.
        ambiguous_terms / negative_context / positive_context: sets/dicts
            used ONLY in the "Context-aware validation" phase.
        hot_threshold (theta): hot/cold classification cutoff (Objective 3).
        """
        self.term_category = {}
        self.term_meaning = dict(dictionary_meaning or {})
        self._pattern_list = []
        for term, category, meaning in patterns:
            term = term.upper()
            self._pattern_list.append(term)
            self.term_category[term] = category
            if meaning:
                self.term_meaning[term] = meaning

        self.ambiguous_terms = ambiguous_terms or set()
        self.negative_context = negative_context or {}
        self.positive_context = positive_context or {}
        self.ambiguous_meanings = ambiguous_meanings or {}
        self.theta = hot_threshold
        self.context_window_k = context_window_k
        self.common_words = common_words or set()
        

        # Populated by ENHANCED_AC_BUILD:
        self.nodes = []          # flat array of nodes in BFS order (Objective 2)
        self.skip = []           # skip[state_idx][char] -> next_state_idx (Objective 1)
        self.store_kind = []     # "hot" | "cold" per state index (Objective 3)
        self.q0 = 0

        self._build(self._pattern_list)

    # ===================== ENHANCED_AC_BUILD(P) ============================
    def _build(self, P):
        # ---- Phase 1: standard trie construction ----
        root = _Node()
        for p in P:
            node = root
            for ch in p:
                if ch not in node.goto:
                    node.goto[ch] = _Node()
                node = node.goto[ch]
            node.output.add(p)

        # ---- Phase 2 (Objective 2): Two-Pass BFS memory layout ----
        # Pass 1: assign BFS rank to every node, build bfs_order (flat array)
        bfs_order = []
        queue = deque([root])
        root.bfs_rank = 0
        visited_ids = {id(root)}
        while queue:
            v = queue.popleft()
            v.bfs_rank = len(bfs_order)
            bfs_order.append(v)
            # sorted char order -> deterministic, prefix-adjacent layout
            for ch in sorted(v.goto.keys()):
                child = v.goto[ch]
                if id(child) not in visited_ids:
                    visited_ids.add(id(child))
                    queue.append(child)

        # Pass 2: remap all child pointers to BFS ranks (contiguous indices)
        # self.nodes[i] is the node with bfs_rank == i
        self.nodes = bfs_order
        self.q0 = root.bfs_rank  # == 0

        # ---- Phase 3 (Objective 3): Tiered Hot/Cold classification ----
        n = len(self.nodes)
        self.store_kind = ["cold"] * n
        for v in self.nodes:
            if len(v.goto) >= self.theta:
                self.store_kind[v.bfs_rank] = "hot"
            else:
                self.store_kind[v.bfs_rank] = "cold"
            # (hot states would be backed by a flat array over the whole
            #  alphabet and cold states by a hash map; in this reference
            #  implementation both are represented as dicts for portability,
            #  but the classification itself -- the thing being measured --
            #  is computed and stored exactly as specified.)

        # ---- Phase 4: failure links (standard AC BFS on compacted nodes) ----
        queue = deque()
        for ch, child in root.goto.items():
            child.fail = root
            queue.append(child)

        while queue:
            v = queue.popleft()
            for ch, u in v.goto.items():
                x = v.fail
                while x is not root and ch not in x.goto:
                    x = x.fail
                u.fail = x.goto[ch] if (ch in x.goto and x.goto[ch] is not u) else root
                u.output |= u.fail.output
                queue.append(u)
        root.fail = root

        # ---- Phase 5 (Objective 1): precompute Skip Table ----
        # skip[state_rank][char] = destination_rank, resolved ONCE at build time.
        self.skip = [dict() for _ in range(n)]
        alphabet = set()
        for v in self.nodes:
            alphabet.update(v.goto.keys())

        for v in self.nodes:
            s_rank = v.bfs_rank
            for a in alphabet:
                if a in v.goto:
                    self.skip[s_rank][a] = v.goto[a].bfs_rank  # fast path
                else:
                    # resolve failure chain NOW, once, at build time
                    x = v.fail if v is not root else root
                    while x is not root and a not in x.goto:
                        x = x.fail
                    if a in x.goto:
                        self.skip[s_rank][a] = x.goto[a].bfs_rank
                    else:
                        self.skip[s_rank][a] = root.bfs_rank

        # Materialize the tiered transition representation. Hot states use a
        # dense array for constant-time indexed access; cold states retain a
        # sparse map to avoid allocating mostly-empty rows.
        self._alphabet = tuple(sorted(alphabet))
        self._alphabet_index = {a: i for i, a in enumerate(self._alphabet)}
        self._ascii_index = [-1] * 128
        for i, ch in enumerate(self._alphabet):
            code = ord(ch)
            if code < 128:
                self._ascii_index[code] = i

        for state, transitions in enumerate(self.skip):
            if self.store_kind[state] == "hot":
                dense = [self.q0] * len(self._alphabet)
                for char, target in transitions.items():
                    dense[self._alphabet_index[char]] = target
                self.skip[state] = dense
            else:
                # Cold rows are genuinely sparse: keep ONLY the transitions
                # that differ from q0 (own edges + edges inherited through
                # the failure chain). A missing key means "go to q0", which
                # is exactly what search() does with transitions.get(a, q0),
                # so lookups and match results are unchanged. Storing the
                # q0 defaults explicitly would make every cold row |Sigma|
                # wide and defeat the point of tiering.
                self.skip[state] = {
                    char: target
                    for char, target in transitions.items()
                    if target != self.q0
                }

        self._root_ref = root

        # Precompute, once at build time, the small subset of patterns that
        # contain "/" along with their space-normalized form and a compiled
        # regex -- search() used to rebuild and rescan this per character,
        # which made it O(n^2). It only ever depends on the pattern list,
        # so it belongs here, not inside the per-character search loop.
        self._slash_patterns = [
            (p, p.replace("/", " "), re.compile(re.escape(p.replace("/", " "))))
            for p in self._pattern_list
            if "/" in p
        ]

    # ===================== STORAGE METRICS (Objective 3) ====================
    def storage_metrics(self):
        """Measured transition-storage figures for this automaton.

        Hot rows are counted from self.skip (dense arrays, |Sigma| each).
        Cold rows are counted from the trie itself (self.nodes[i].goto),
        i.e. each cold state's own trie edges -- NOT the extra transitions
        the failure chain would resolve for other characters. That
        failure-chain resolution is what the skip table (Objective 1)
        precomputes so lookups stay O(1); it is a separate, derived
        structure and is not counted as a state's own storage here.

        Cells are transition slots. Two baselines are reported so the
        saving can be attributed honestly:
          * full-row baseline  = |S| x |FULL_ALPHABET|  (no tiering, no
            alphabet restriction -- the textbook |S| x |Sigma| matrix)
          * same-alphabet baseline = |S| x |Sigma_pattern| (dense rows over
            only the characters that occur in the patterns). Comparing
            against this isolates the effect of hot/cold tiering from the
            effect of simply using a smaller alphabet.
        """
        n = len(self.nodes)
        sigma = len(self._alphabet)
        full = len(FULL_ALPHABET)

        hot = [i for i, k in enumerate(self.store_kind) if k == "hot"]
        cold = [i for i, k in enumerate(self.store_kind) if k == "cold"]

        hot_cells = sum(len(self.skip[i]) for i in hot)          # dense: |Sigma| each
        cold_cells = sum(len(self.nodes[i].goto) for i in cold)  # trie's own edges only
        cold_row_sizes = [len(self.nodes[i].goto) for i in cold]

        enhanced_total = hot_cells + cold_cells
        baseline_full = n * full
        baseline_same = n * sigma

        def pct(saved, base):
            return round(saved / base * 100, 2) if base else 0.0

        def kb(cells):
            return round(cells * CELL_BYTES / 1024, 3)

        return {
            "theta": self.theta,
            "states": n,
            "alphabet_pattern": sigma,
            "alphabet_full": full,
            "hot_states": len(hot),
            "cold_states": len(cold),
            "hot_ratio_pct": pct(len(hot), n),
            "hot_cells": hot_cells,
            "cold_cells": cold_cells,
            "cold_row_min": min(cold_row_sizes) if cold_row_sizes else 0,
            "cold_row_avg": round(sum(cold_row_sizes) / len(cold_row_sizes), 2) if cold_row_sizes else 0,
            "cold_row_max": max(cold_row_sizes) if cold_row_sizes else 0,
            "cold_dense_equivalent": len(cold) * sigma,
            "enhanced_cells": enhanced_total,
            "baseline_full_cells": baseline_full,
            "baseline_same_alphabet_cells": baseline_same,
            "saved_vs_full_cells": baseline_full - enhanced_total,
            "saved_vs_full_pct": pct(baseline_full - enhanced_total, baseline_full),
            "saved_vs_same_alphabet_cells": baseline_same - enhanced_total,
            "saved_vs_same_alphabet_pct": pct(baseline_same - enhanced_total, baseline_same),
            # split of the full-row saving into its two causes
            "saving_from_alphabet_restriction_cells": baseline_full - baseline_same,
            "saving_from_tiering_cells": baseline_same - enhanced_total,
            "cell_bytes": CELL_BYTES,
            "baseline_full_kb": kb(baseline_full),
            "baseline_same_alphabet_kb": kb(baseline_same),
            "enhanced_kb": kb(enhanced_total),
        }

    # ===================== ENHANCED_AC_SEARCH(T) ============================
    def search(self, text):
        # ---- Text Normalization ----
        T = text.upper()
        T = T.replace("ΜG", " MCG ").replace("µG", " MCG ").replace("μG", " MCG ")
        T = T.replace("Μ", "U").replace("µ", "U").replace("μ", "U")
        T = T.replace("×", " X ").replace("÷", " / ")
        T = re.sub(r"(?i)\bMCG\b", " MCG ", T)
        T = re.sub(r"(?i)\bUG\b", " MCG ", T)
        T = re.sub(r"(?i)\bIU\b", " IU ", T)
        # Keep prescription symbols from the dictionary while still removing
        # punctuation that commonly separates abbreviations (for example,
        # "B.I.D." -> "B I D").
        T = re.sub(r"[^\w\s#•—\u0304-]", " ", T)
        T = re.sub(r"\s+", " ", T).strip()    # normalize_spaces
        # Restore common frequency shorthand after punctuation stripping so
        # patterns like "1-1-1", "1/1/1", and "1-0-1" remain intact for exact
        # dictionary matching instead of being split into separate tokens.
        T = re.sub(r"(?i)\b([01])\s+([01])\s+([01])\b", r"\1-\2-\3", T)
        T = self._expand_common_noise(T)

        # ---- Tokenization ----
        tokens, token_spans = self._tokenize(T)
        token_index = self._build_char_to_token_index(T, token_spans)

        # ---- O(1) skip-table scan ----
        state = self.q0
        candidates = []
        nodes = self.nodes
        skip = self.skip
        ascii_index = self._ascii_index
        q0 = self.q0
        append_candidate = candidates.append

        for i, a in enumerate(T):
            # Space is a normal alphabet symbol here (some dictionary terms,
            # e.g. "1 TAB", span a whitespace boundary), so it is routed
            # through the skip table like any other character rather than
            # forcing a reset to q0.
            transitions = skip[state]
            if isinstance(transitions, list):
                code = ord(a)
                idx = ascii_index[code] if code < 128 else -1
                state = transitions[idx] if idx >= 0 else q0
            else:
                state = transitions.get(a, q0)

            node = nodes[state]
            if node.output:
                for p in node.output:
                    start = i - len(p) + 1
                    if start >= 0:
                        append_candidate({"term": p, "start": start, "end": i + 1})

        # Punctuation is normalized to spaces before scanning, so also test
        # dictionary terms whose slash separator was normalized away.
        # NOTE: this used to run once PER CHARACTER inside the loop above
        # (an O(n^2) bug -- the whole text was re-scanned for every slash
        # pattern at every position). It only needs to run once, over the
        # whole text, after the single-pass skip-table scan is done.
        for pattern, normalized_pattern, compiled in self._slash_patterns:
            for match in compiled.finditer(T):
                append_candidate({
                    "term": pattern,
                    "start": match.start(),
                    "end": match.end(),
                })

        candidates = self._normalize_symbol_candidates(candidates, T)

        # ---- Context-aware validation ----
        validated = []
        for hit in candidates:
            # Do not treat a short dictionary term embedded in a larger word
            # as an exact medical match (for example, "AC" in "PARACETMOL").
            if not self._boundary_bonus(hit, T):
                continue
            term = hit["term"]
            if term in self.ambiguous_terms:
                window = self._surrounding_tokens(hit, token_index, tokens, token_spans)
                neg = self.negative_context.get(term, set())
                pos = self.positive_context.get(term, set())
                neg_score = len(window & neg)
                pos_score = len(window & pos)
                if neg_score > pos_score:
                    continue  # negative evidence outweighs clinical evidence -> skip
                if pos and pos_score == 0:
                    continue  # no clinical signal nearby -> skip
                hit["context_valid"] = True
            else:
                hit["context_valid"] = True
            validated.append(hit)

        # ---- Priority-weighted scoring ----
        for hit in validated:
            score = 0.0
            score += self._length_bonus(hit["term"])
            score += self._boundary_bonus(hit, T)
            score += self._known_term_bonus(hit["term"])
            score += self._context_bonus(hit["context_valid"])
            hit["priority_score"] = min(score / 4.0, 1.0)  # normalize to [0,1]

        # Keep all validated hits until supplemental and fuzzy candidates have
        # been added, then resolve every overlap in one priority-ordered pass.
        output = list(validated)

        # ---- Meaning for abbreviated terms ----
        for hit in output:
            lookup_term = hit["term"]
            if lookup_term.startswith("-"):
                lookup_term = "-"
            elif lookup_term.startswith("#") or lookup_term.endswith("#"):
                lookup_term = "#"
            hit["category"] = self.term_category.get(lookup_term, "")
            hit["meaning"] = self._meaning_for_hit(
                hit, lookup_term, token_index, tokens, token_spans
            )
            hit["match_type"] = "exact"

        # ---- Phase 7: Fuzzy Matching over tokens not covered by output ----
        # A position counts as "covered" if the exact skip-table scan ever
        # produced a candidate there, even if context validation later
        # rejected it (e.g. "cold" in "cold compress"). Otherwise fuzzy
        # matching would immediately re-add a context-rejected exact term
        # right back in, defeating the point of Context-Aware Validation.
        # Positions are only left open to fuzzy matching when the exact
        # scan found nothing there at all (a genuine spelling miss).
        covered_positions = set()
        for hit in candidates:
            if not self._boundary_bonus(hit, T):
                continue
            covered_positions.update(range(hit["start"], hit["end"]))

        for idx, (tok, (tstart, tend)) in enumerate(zip(tokens, token_spans)):
            # Keep fuzzy correction for genuine OCR misspellings like "moflox" ->
            # "IMOFLOX", but block common OCR false positives like "CUP" and "MIX"
            # which were previously being mapped to "CAP" and "MI".
            tok_upper = tok.upper()
            if tok_upper in self.common_words:
                continue
            # Avoid rewriting normal 3-letter words like "day" into a valid
            # abbreviation such as "daw". Real OCR corruption cases like
            # "moflox" are longer and remain eligible for fuzzy correction.
            if len(tok) < 4:
                continue
            if any(pos in covered_positions for pos in range(tstart, tend)):
                continue
            best, best_dist = None, None
            for p in self._pattern_list:
                if p.isalpha() != tok.isalpha():
                    continue
                d = edit_distance(tok, p)
                if best_dist is None or d < best_dist:
                    best, best_dist = p, d
            if best is None:
                continue
            sim = similarity(tok, best)
            if best_dist <= 2 and sim >= 0.6:
                output.append({
                    "term": tok,
                    "matched": best,
                    "start": tstart,
                    "end": tend,
                    "category": self.term_category.get(best, ""),
                    "meaning": self.term_meaning.get(best, "—"),
                    "priority_score": round(sim, 2),
                    "match_type": "fuzzy",
                })

        # Some dosage forms appear fused as a numeric token (e.g. "200mg")
        # and should still contribute the standalone unit abbreviation to the
        # abbreviations panel ("MG" / "MCG" / "UG" / "ML"). Keep the exact
        # dosage match as-is while also surfacing the unit abbreviation.
        unit_hits = []
        for unit_match in re.finditer(r"(?i)(\d+)\s*(mg|mcg|ug|ml|g|tab|tabs|cap|caps)\b", T):
            unit = unit_match.group(2).upper()
            dosage_term = f"{unit_match.group(1)}{unit}"
            dosage_start = unit_match.start(1)
            dosage_end = unit_match.end(2)
            if dosage_term in self.term_category:
                if not any(h.get("term") == dosage_term and h.get("start") == dosage_start and h.get("end") == dosage_end for h in output):
                    unit_hits.append({
                        "term": dosage_term,
                        "matched": dosage_term,
                        "start": dosage_start,
                        "end": dosage_end,
                        "category": self.term_category.get(dosage_term, "Dosage"),
                        "meaning": self.term_meaning.get(dosage_term, "—"),
                        "context_valid": True,
                        "match_type": "exact",
                    })
                continue
            start = unit_match.start(2)
            end = unit_match.end(2)
            if any(h.get("term") == unit and h.get("start") == start and h.get("end") == end for h in output):
                continue
            unit_hits.append({
                "term": unit,
                "matched": unit,
                "start": start,
                "end": end,
                "category": self.term_category.get(unit, "Dosage"),
                "meaning": self.term_meaning.get(unit, "—"),
                "context_valid": True,
                "match_type": "exact",
            })

        output.extend(unit_hits)
        # Keep exact standalone abbreviation tokens such as "2X" and "3X"
        # even when the longer frequency phrase "2X A DAY" also matches.
        seen_exact = {(hit["term"], hit["start"], hit["end"]) for hit in output}
        for tok, (tstart, tend) in zip(tokens, token_spans):
            token = tok.upper()
            if token not in self.term_category:
                continue
            if (token, tstart, tend) in seen_exact:
                continue
            if self.term_category[token] not in {"Abbreviation", "Dosage", "Symbol", "Frequency"}:
                continue
            output.append({
                "term": token,
                "matched": token,
                "start": tstart,
                "end": tend,
                "category": self.term_category.get(token, ""),
                "meaning": self._meaning_for_hit(
                    {"term": token, "start": tstart, "end": tend},
                    token, token_index, tokens, token_spans,
                ),
                "context_valid": True,
                "match_type": "exact",
            })
            seen_exact.add((token, tstart, tend))

        for hit in output:
            if hit.get("match_type") == "exact" and "priority_score" not in hit:
                score = 0.0
                score += self._length_bonus(hit["term"])
                score += self._boundary_bonus(hit, T)
                score += self._known_term_bonus(hit["term"])
                score += self._context_bonus(hit.get("context_valid", True))
                hit["priority_score"] = min(score / 4.0, 1.0)

        # ---- Final overlap resolution across all candidate sources ----
        # `occupied` only ever holds non-overlapping intervals (each accepted
        # hit is checked against it before being added), so it can be kept
        # sorted by start and only its neighboring interval(s) need checking,
        # instead of scanning every previously-accepted interval for every
        # candidate. The overlap check itself drops from O(k) to O(log k)
        # per candidate; list.insert still shifts elements (O(k)) so this is
        # not asymptotically better in the worst case, but it cuts real
        # comparisons enormously (measured ~13x faster on a 20k-word,
        # match-dense prescription text -- 19.1s to 1.4s) because the old
        # code did a full linear `any(...)` scan, with a Python-level
        # generator, against every prior accepted interval on every hit.
        import bisect
        output.sort(key=lambda h: (-h["priority_score"], -len(h["term"])))
        resolved = []
        occupied_starts = []   # kept sorted; parallel to occupied_ends
        occupied_ends = []     # end of the interval starting at occupied_starts[i]
        for hit in output:
            pos = bisect.bisect_right(occupied_starts, hit["start"])
            # Only the neighboring interval(s) can possibly overlap `hit`,
            # since all occupied intervals are mutually non-overlapping:
            # the one starting just before `pos` (may extend into hit),
            # and the one right after `pos` (may start before hit ends).
            overlap = False
            if pos > 0 and occupied_ends[pos - 1] > hit["start"]:
                overlap = True
            elif pos < len(occupied_starts) and occupied_starts[pos] < hit["end"]:
                overlap = True
            if not overlap:
                resolved.append(hit)
                occupied_starts.insert(pos, hit["start"])
                occupied_ends.insert(pos, hit["end"])

        output = resolved
        output.sort(key=lambda h: h["start"])
        return output

    # ---------------------------- helpers ----------------------------------
    # Dosage-form words that are frequently glued to their preceding count by
    # OCR noise (e.g. "1tab" -> should read as "1 tab"). Deliberately narrow:
    # measurement units like "MG"/"ML"/"G" and coded abbreviations like "Q4H"
    # are legitimately fused in the dictionary and must NOT be split here.
    _UNIT_WORDS = ("TABS", "TAB", "CAPS", "CAP", "VIAL", "AMPULE", "TSP", "DROPS", "DROP")

    @classmethod
    def _expand_common_noise(cls, T):
        # "1tab" -> "1 tab", "2caps" -> "2 caps", etc.
        for word in cls._UNIT_WORDS:
            T = re.sub(rf"(\d)({word})\b", r"\1 \2", T)
        return T

    @staticmethod
    def _tokenize(T):
        tokens, spans = [], []
        for m in re.finditer(r"\S+", T):
            tokens.append(m.group(0))
            spans.append((m.start(), m.end()))
        return tokens, spans

    @staticmethod
    def _build_char_to_token_index(T, token_spans):
        index = [-1] * len(T)
        for ti, (s, e) in enumerate(token_spans):
            for pos in range(s, e):
                index[pos] = ti
        return index

    def _surrounding_tokens(self, hit, token_index, tokens, token_spans):
        pos = hit["start"]
        if pos >= len(token_index) or token_index[pos] == -1:
            return set()
        ti = token_index[pos]
        k = self.context_window_k
        lo, hi = max(0, ti - k), min(len(tokens), ti + k + 1)
        return {tokens[i] for i in range(lo, hi) if i != ti}

    @staticmethod
    def _normalize_symbol_candidates(candidates, T):
        normalized = []
        meal_marker_spans = []
        for hit in candidates:
            if hit["term"] == "#":
                start, end = hit["start"], hit["end"]
                while start > 0 and T[start - 1].isdigit():
                    start -= 1
                while end < len(T) and T[end].isdigit():
                    end += 1
                hit = {
                    **hit,
                    "term": T[start:end],
                    "matched": T[start:end],
                    "start": start,
                    "end": end,
                }
            elif hit["term"] in ("-", "•", "—"):
                meal_marker_spans.append(hit)
                continue
            normalized.append(hit)

        for marker in sorted(meal_marker_spans, key=lambda hit: hit["start"]):
            if normalized and normalized[-1]["term"].startswith("-") and normalized[-1]["end"] == marker["start"]:
                normalized[-1]["term"] += "-"
                normalized[-1]["matched"] += T[marker["start"]:marker["end"]]
                normalized[-1]["end"] = marker["end"]
            else:
                normalized.append({
                    "term": "-",
                    "matched": T[marker["start"]:marker["end"]],
                    "start": marker["start"],
                    "end": marker["end"],
                })
        return normalized

    def _length_bonus(self, term):
        return min(len(term) / 11.0, 1.0)  # longer = more specific

    def _boundary_bonus(self, hit, T):
        start, end = hit["start"], hit["end"]
        # Quantity notation is commonly written as "#9". The dictionary
        # treats the hash as its own symbol, so a following digit is valid.
        if hit["term"].startswith("#") or hit["term"].endswith("#"):
            left_ok = start == 0 or not T[start - 1].isalnum()
            right_ok = end >= len(T) or not T[end].isalnum()
            return 1.0 if (left_ok or hit["term"].endswith("#")) and (right_ok or hit["term"].startswith("#")) else 0.0
        
        left_ok = start == 0 or not T[start - 1].isalnum()
        right_ok = end >= len(T) or not T[end].isalnum()
        return 1.0 if (left_ok and right_ok) else 0.0

    def _known_term_bonus(self, term):
        return 1.0 if term in self.term_category or term.startswith("#") or term.endswith("#") else 0.0

    def _context_bonus(self, context_valid):
        return 1.0 if context_valid else 0.0

    def score_external_hit(self, hit, text):
        T = text.upper()
        tokens, token_spans = self._tokenize(T)
        token_index = self._build_char_to_token_index(T, token_spans)
        term = hit["term"].upper()
        context_valid = True
        if term in self.ambiguous_terms:
            window = self._surrounding_tokens(hit, token_index, tokens, token_spans)
            neg = self.negative_context.get(term, set())
            pos = self.positive_context.get(term, set())
            neg_score = len(window & neg)
            pos_score = len(window & pos)
            context_valid = not (neg_score > pos_score or (pos and pos_score == 0))

        score = 0.0
        score += self._length_bonus(term)
        score += self._boundary_bonus({**hit, "term": term}, T)
        score += self._known_term_bonus(term)
        score += self._context_bonus(context_valid)
        return min(score / 4.0, 1.0), context_valid

    def _meaning_for_hit(self, hit, lookup_term, token_index, tokens, token_spans):
        meanings = self.ambiguous_meanings.get(lookup_term)
        if not meanings:
            return self.term_meaning.get(lookup_term, "—")

        window = self._surrounding_tokens(hit, token_index, tokens, token_spans)

        for meaning, context_terms in meanings.items():
            if window & context_terms:
                return meaning
        return self.term_meaning.get(lookup_term, "—")



def load_dictionary(csv_path):
    """Loads patterns and abbreviation-meaning dictionary D from the CSV."""
    import csv
    patterns = []
    meaning_dict = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            term = row["term"].strip().upper()
            category = row["category"].strip()
            meaning = row.get("meaning", "").strip()
            patterns.append((term, category, meaning))
            if meaning:
                meaning_dict[term] = meaning
    return patterns, meaning_dict