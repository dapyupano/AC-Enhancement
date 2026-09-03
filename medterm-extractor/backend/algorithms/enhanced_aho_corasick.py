"""
ENHANCED AHO-CORASICK ALGORITHM
================================
Implements ENHANCED_AC_BUILD(P) and ENHANCED_AC_SEARCH(T) exactly as
specified in Chapter 3.2.1 ("Proposed Algorithm") of the thesis:

    Phase 1: standard trie construction
    Phase 2 (Objective 2): Two-Pass BFS memory layout
    Phase 3 (Objective 3): Tiered Hot/Cold classification
    Phase 4: failure links (standard AC BFS on compacted nodes)
    Phase 5 (Objective 1): precompute Skip Table

    Search:
      - Text normalization (uppercase, punctuation strip, whitespace
        normalization, common-noise expansion)
      - Tokenization
      - O(1) skip-table traversal (no failure-link loop at search time)
      - Context-aware validation (Ambiguous/Negative/Positive context sets)
      - Priority-weighted scoring (length, boundary, known-term, context bonus)
      - Overlap resolution (keep highest-scoring non-overlapping hits)
      - Meaning lookup for abbreviated terms (dictionary D)
      - Phase 7: Fuzzy matching over unmatched tokens (edit distance)
"""

import re
from collections import deque


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
                 context_window_k=3):
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
        self.theta = hot_threshold
        self.context_window_k = context_window_k

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

        self._root_ref = root

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
                if window & neg:
                    continue  # e.g. "cold compress" -> skip
                if pos and not (window & pos):
                    continue  # no clinical signal nearby -> skip
                hit["context_valid"] = True
            else:
                hit["context_valid"] = False
            validated.append(hit)

        # ---- Priority-weighted scoring ----
        for hit in validated:
            score = 0.0
            score += self._length_bonus(hit["term"])
            score += self._boundary_bonus(hit, T)
            score += self._known_term_bonus(hit["term"])
            score += self._context_bonus(hit["context_valid"])
            hit["priority_score"] = min(score / 4.0, 1.0)  # normalize to [0,1]

        # ---- Overlap resolution: keep highest-scoring non-overlapping hits ----
        validated.sort(key=lambda h: (-h["priority_score"], -len(h["term"])))
        output = []
        occupied = []  # list of (start, end) already accepted
        for hit in validated:
            overlap = any(not (hit["end"] <= s or hit["start"] >= e) for s, e in occupied)
            if not overlap:
                output.append(hit)
                occupied.append((hit["start"], hit["end"]))

        # ---- Meaning for abbreviated terms ----
        for hit in output:
            lookup_term = hit["term"]
            if lookup_term.startswith("-"):
                lookup_term = "-"
            elif lookup_term.startswith("#") or lookup_term.endswith("#"):
                lookup_term = "#"
            hit["category"] = self.term_category.get(lookup_term, "")
            hit["meaning"] = self.term_meaning.get(lookup_term, "—")
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
            if tok_upper in {"CUP", "MIX"}:
                continue
            # Avoid rewriting normal 3-letter words like "day" into a valid
            # abbreviation such as "daw". Real OCR corruption cases like
            # "moflox" are longer and remain eligible for fuzzy correction.
            if len(tok) == 3:
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
                "priority_score": 0.72,
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
                "meaning": self.term_meaning.get(token, "—"),
                "priority_score": 0.72,
                "match_type": "exact",
            })
            seen_exact.add((token, tstart, tend))

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
        return min(len(term) / 12.0, 1.0)  # longer = more specific

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
