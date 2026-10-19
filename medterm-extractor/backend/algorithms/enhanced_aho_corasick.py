import re
import unicodedata
from collections import deque

# Shared storage constants.
# Full transition alphabet.
FULL_ALPHABET = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,-/%()+:#\u2022\u2014")

# Used for storage estimates.
CELL_BYTES = 8


# Fuzzy matching helpers.
def edit_distance(a, b):
    """Return the Levenshtein distance between two strings."""
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
                prev[j] + 1,
                curr[j - 1] + 1,
                prev[j - 1] + cost
            )
        prev = curr
    return prev[m]


def similarity(a, b):
    dist = edit_distance(a, b)
    longest = max(len(a), len(b))
    if longest == 0:
        return 1.0
    return 1.0 - (dist / longest)


class _Node:
    """Trie node used while building the automaton."""

    __slots__ = ("goto", "fail", "output", "bfs_rank")

    def __init__(self):
        self.goto = {}
        self.fail = None
        self.output = set()
        self.bfs_rank = -1


class EnhancedAhoCorasick:
    """Aho-Corasick search with validation, scoring, and fuzzy matching."""

    def __init__(self, patterns, dictionary_meaning=None,
                 ambiguous_terms=None, negative_context=None,
                 positive_context=None, hot_threshold=4,
                 context_window_k=5, ambiguous_meanings=None, common_words=None):
        """Build an enhanced Aho-Corasick automaton."""
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
        

        self.nodes = []
        self.skip = []
        self.store_kind = []
        self.q0 = 0

        self._build(self._pattern_list)

    def _build(self, P):
        # Build the trie.
        root = _Node()
        for p in P:
            node = root
            for ch in p:
                if ch not in node.goto:
                    node.goto[ch] = _Node()
                node = node.goto[ch]
            node.output.add(p)

        # Assign BFS ranks for compact storage. obj 2
        bfs_order = []
        queue = deque([root])
        root.bfs_rank = 0
        visited_ids = {id(root)}
        while queue:
            v = queue.popleft()
            v.bfs_rank = len(bfs_order)
            bfs_order.append(v)
            for ch in sorted(v.goto.keys()):
                child = v.goto[ch]
                if id(child) not in visited_ids:
                    visited_ids.add(id(child))
                    queue.append(child)

        self.nodes = bfs_order
        self.q0 = root.bfs_rank

        # Classify states by transition count. obj 3
        n = len(self.nodes)
        self.store_kind = ["cold"] * n
        for v in self.nodes:
            if len(v.goto) >= self.theta:
                self.store_kind[v.bfs_rank] = "hot"
            else:
                self.store_kind[v.bfs_rank] = "cold"

        # Build failure links for fallback matching.
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

        # Precompute skip transitions for constant-time scanning. obj 1 
        self.skip = [dict() for _ in range(n)]
        alphabet = set()
        for v in self.nodes:
            alphabet.update(v.goto.keys())

        for v in self.nodes:
            s_rank = v.bfs_rank
            for a in alphabet:
                if a in v.goto:
                    self.skip[s_rank][a] = v.goto[a].bfs_rank
                else:
                    x = v.fail if v is not root else root
                    while x is not root and a not in x.goto:
                        x = x.fail
                    if a in x.goto:
                        self.skip[s_rank][a] = x.goto[a].bfs_rank
                    else:
                        self.skip[s_rank][a] = root.bfs_rank

        # Store hot states densely and cold states sparsely.
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
                # Missing cold transitions go to q0.
                self.skip[state] = {
                    char: target
                    for char, target in transitions.items()
                    if target != self.q0
                }

        self._root_ref = root

        # Precompile slash-separated patterns after normalization.
        self._slash_patterns = [
            (p, p.replace("/", " "), re.compile(re.escape(p.replace("/", " "))))
            for p in self._pattern_list
            if "/" in p
        ]

    def storage_metrics(self):
        # Report memory usage for the transition tables.
        """Return transition-storage metrics."""
        n = len(self.nodes)
        sigma = len(self._alphabet)
        full = len(FULL_ALPHABET)

        hot = [i for i, k in enumerate(self.store_kind) if k == "hot"]
        cold = [i for i, k in enumerate(self.store_kind) if k == "cold"]

        hot_cells = sum(len(self.skip[i]) for i in hot)
        cold_cells = sum(len(self.nodes[i].goto) for i in cold)
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
            "saving_from_alphabet_restriction_cells": baseline_full - baseline_same,
            "saving_from_tiering_cells": baseline_same - enhanced_total,
            "cell_bytes": CELL_BYTES,
            "baseline_full_kb": kb(baseline_full),
            "baseline_same_alphabet_kb": kb(baseline_same),
            "enhanced_kb": kb(enhanced_total),
        }

    def search(self, text):
        # Normalize input before matching.
        T = unicodedata.normalize("NFC", text.upper())
        T = T.replace("ΜG", " MCG ").replace("µG", " MCG ").replace("μG", " MCG ")
        T = T.replace("Μ", "U").replace("µ", "U").replace("μ", "U")
        T = re.sub(r"(?i)\bMCG\b", " MCG ", T)
        T = re.sub(r"(?i)\bUG\b", " MCG ", T)
        T = re.sub(r"(?i)\bIU\b", " IU ", T)
        # Normalize OCR macron artifacts.
        has_separate_macron = "─" in T
        T = re.sub(r"([A-Z])─", lambda match: f"{match.group(1)}\u0304", T)
        if has_separate_macron:
            T = re.sub(r"\bA\b", "Ā", T)
        # Keep dictionary symbols and abbreviation separators.
        T = re.sub(r"[^\w\s#•—\u0304-]", " ", T)
        T = re.sub(r"\s+", " ", T).strip()
        # Restore three-part frequency shorthand.
        T = re.sub(r"(?i)\b([01])\s+([01])\s+([01])\b", r"\1-\2-\3", T)
        T = self._expand_common_noise(T)

        # Tokenize input for context checks and fuzzy matching.
        tokens, token_spans = self._tokenize(T)
        token_index = self._build_char_to_token_index(T, token_spans)

        # Find exact candidates with the skip table.
        state = self.q0
        candidates = []
        nodes = self.nodes
        skip = self.skip
        ascii_index = self._ascii_index
        q0 = self.q0
        append_candidate = candidates.append

        for i, a in enumerate(T):
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

        # Match slash patterns after punctuation normalization.
        for pattern, normalized_pattern, compiled in self._slash_patterns:
            for match in compiled.finditer(T):
                append_candidate({
                    "term": pattern,
                    "start": match.start(),
                    "end": match.end(),
                })

        # Normalize symbol candidates such as "#9" and meal markers.
        candidates = self._normalize_symbol_candidates(candidates, T)

        # Reject invalid boundaries and ambiguous contexts.
        validated = []
        for hit in candidates:
            # Do not treat a short dictionary term embedded in a larger word
            # as an exact medical match (for example, "AC" in "PARACETMOL").
            if not self._boundary_bonus(hit, T):
                continue
            if not self._context_is_valid(hit, token_index, tokens, token_spans):
                continue
            validated.append(hit)

        # Score validated exact matches.
        for hit in validated:
            score = 0.0
            score += self._length_bonus(hit["term"])
            score += self._boundary_bonus(hit, T)
            score += self._known_term_bonus(hit["term"])
            score += self._context_bonus(hit["context_valid"])
            hit["priority_score"] = min(score / 4.0, 1.0)  # normalize to [0,1]

        # Add meanings and categories to exact matches.
        output = list(validated)

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

        # Reserve exact-match positions from fuzzy matching.
        covered_positions = set()
        for hit in candidates:
            if not self._boundary_bonus(hit, T):
                continue
            covered_positions.update(range(hit["start"], hit["end"]))

        # Match misspelled multi-word terms first.
        phrase_patterns = [
            pattern for pattern in self._pattern_list
            if len(pattern.split()) > 1
        ]
        for pattern in phrase_patterns:
            pattern_words = pattern.split()
            word_count = len(pattern_words)
            if word_count > len(tokens):
                continue
            for idx in range(len(tokens) - word_count + 1):
                window = tokens[idx:idx + word_count]
                if any(word.upper() in self.common_words for word in window):
                    continue
                distances = [
                    edit_distance(token.upper(), pattern_word)
                    for token, pattern_word in zip(window, pattern_words)
                ]
                if all(
                    distance <= 2 and similarity(token.upper(), pattern_word) >= 0.6
                    for token, pattern_word, distance in zip(window, pattern_words, distances)
                ) and any(distance > 0 for distance in distances):
                    start = token_spans[idx][0]
                    end = token_spans[idx + word_count - 1][1]
                    phrase_similarity = sum(
                        similarity(token.upper(), pattern_word)
                        for token, pattern_word in zip(window, pattern_words)
                    ) / word_count
                    output.append({
                        "term": T[start:end],
                        "matched": pattern,
                        "start": start,
                        "end": end,
                        "category": self.term_category.get(pattern, ""),
                        "meaning": self.term_meaning.get(pattern, "—"),
                        "priority_score": min(round(phrase_similarity + 0.1, 2), 1.0),
                        "match_type": "fuzzy",
                    })

        # Match remaining misspelled single tokens.
        for idx, (tok, (tstart, tend)) in enumerate(zip(tokens, token_spans)):
            tok_upper = tok.upper()
            if tok_upper in self.common_words:
                continue
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

        # Add units found inside fused dosage tokens.
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
        # Keep standalone abbreviations inside longer frequency phrases.
        seen_exact = {(hit["term"], hit["start"], hit["end"]) for hit in output}
        for tok, (tstart, tend) in zip(tokens, token_spans):
            token = tok.upper()
            if token not in self.term_category:
                continue
            if (token, tstart, tend) in seen_exact:
                continue
            if self.term_category[token] not in {"Abbreviation", "Dosage", "Symbol", "Frequency"}:
                continue
            token_hit = {"term": token, "start": tstart, "end": tend}
            if not self._context_is_valid(token_hit, token_index, tokens, token_spans):
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
                "context_valid": token_hit["context_valid"],
                "match_type": "exact",
            })
            seen_exact.add((token, tstart, tend))

        # Score supplemental exact matches.
        for hit in output:
            if hit.get("match_type") == "exact" and "priority_score" not in hit:
                score = 0.0
                score += self._length_bonus(hit["term"])
                score += self._boundary_bonus(hit, T)
                score += self._known_term_bonus(hit["term"])
                score += self._context_bonus(hit.get("context_valid", True))
                hit["priority_score"] = min(score / 4.0, 1.0)

        # Keep the highest-priority non-overlapping matches.
        import bisect
        output.sort(key=lambda h: (-h["priority_score"], -len(h["term"])))
        resolved = []
        occupied_starts = []
        occupied_ends = []
        for hit in output:
            pos = bisect.bisect_right(occupied_starts, hit["start"])
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

    # Input normalization helpers.
    # Dosage words commonly fused with a preceding number by OCR.
    _UNIT_WORDS = ("TABS", "TAB", "CAPS", "CAP", "VIAL", "AMPULE", "TSP", "DROPS", "DROP")

    @classmethod
    def _expand_common_noise(cls, T):
        for word in cls._UNIT_WORDS:
            T = re.sub(rf"(\d)({word})\b", r"\1 \2", T)
        return T

    # Token and span helpers.
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

    # Context validation helpers.
    def _surrounding_tokens(self, hit, token_index, tokens, token_spans):
        pos = hit["start"]
        if pos >= len(token_index) or token_index[pos] == -1:
            return set()
        ti = token_index[pos]
        k = self.context_window_k
        lo, hi = max(0, ti - k), min(len(tokens), ti + k + 1)
        return {tokens[i] for i in range(lo, hi) if i != ti}

    def _context_is_valid(self, hit, token_index, tokens, token_spans):
        """Validate an ambiguous term against nearby tokens."""
        term = hit["term"]
        if term not in self.ambiguous_terms:
            hit["context_valid"] = True
            return True

        window = self._surrounding_tokens(hit, token_index, tokens, token_spans)
        neg = self.negative_context.get(term, set())
        pos = self.positive_context.get(term, set())
        neg_score = len(window & neg)
        pos_score = len(window & pos)
        context_valid = not (neg_score > pos_score or (pos and pos_score == 0))
        hit["context_valid"] = context_valid
        return context_valid

    # Symbol and boundary helpers.
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

    # Match scoring helpers.
    def _length_bonus(self, term):
        return min(len(term) / 11.0, 1.0)

    def _boundary_bonus(self, hit, T):
        start, end = hit["start"], hit["end"]
        # Allow percent notation after a number.
        if hit["term"] == "%" and start > 0 and T[start - 1].isdigit():
            return 1.0
        # Allow quantity notation such as "#9".
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
        hit = {**hit, "term": term}
        context_valid = self._context_is_valid(hit, token_index, tokens, token_spans)

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



# Dictionary loading.
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