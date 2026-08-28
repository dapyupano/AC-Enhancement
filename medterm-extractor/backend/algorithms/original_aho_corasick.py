"""
ORIGINAL / BASELINE AHO-CORASICK ALGORITHM
===========================================
Implements the "Existing Algorithm" exactly as it is presented in the thesis
(Chapter 1, "Existing Algorithm" pseudocode):

    Input:
        P = {p1, p2, ..., pn}
        T = t1...tm

    AC-Build(P):
        create root q0
        for each pattern p in P:
            insert p into trie via goto transitions delta(q, a)
            mark terminal state with O(q) <- O(q) U {p}
        ... standard BFS failure-link construction ...
        return automaton (Q, Sigma, delta, q0, F, f, O)

    AC-Search(T):
        state <- q0
        for each symbol a in T:
            while delta(state, a) undefined and state != q0:
                state <- f(state)
            if delta(state, a) defined:
                state <- delta(state, a)
            else:
                state <- q0
            if O(state) != empty:
                report all patterns in O(state) ending at current index

This module intentionally implements NOTHING beyond the above:
    - No precomputed skip table (Objective 1 is an enhancement).
    - No two-pass BFS memory layout (Objective 2 is an enhancement).
    - No tiered hot/cold transition storage (Objective 3 is an enhancement).
    - No context-aware validation, no priority-weighted scoring,
      no abbreviation-meaning lookup, no fuzzy matching.

Matching is exact-string only, case-sensitive after a simple uppercase pass,
identical to how the thesis illustrates the baseline automaton
(patterns like {cora, ora, ras, or, sick, ick, corasick}).
"""

from collections import deque


class TrieNode:
    """A single trie state q. Uses a plain dict for goto transitions delta(q, a),
    exactly like the classical construction -- no hot/cold storage tiers."""

    __slots__ = ("goto", "fail", "output")

    def __init__(self):
        self.goto = {}          # delta(q, a) -> child TrieNode
        self.fail = None        # f(q)
        self.output = set()     # O(q)


class OriginalAhoCorasick:
    """Baseline Aho-Corasick automaton. No performance enhancements."""

    def __init__(self, patterns):
        """
        patterns: iterable of (term, category, meaning) tuples, OR plain strings.
        Only `term` is used for matching -- category/meaning are stored purely
        for display purposes and are NOT looked up during search (the original
        algorithm has no meaning-lookup phase).
        """
        self.term_lookup = {}   # term -> (category, meaning), display-only
        self._patterns = []
        for p in patterns:
            if isinstance(p, tuple):
                term, category, meaning = p
            else:
                term, category, meaning = p, "", ""
            term = term.upper()
            self._patterns.append(term)
            self.term_lookup[term] = (category, meaning)

        self.root = TrieNode()
        self._build(self._patterns)

    # ---- AC-Build(P) -----------------------------------------------------
    def _build(self, P):
        # create root q0
        root = self.root

        # for each pattern p in P: insert p into trie via goto transitions delta(q, a)
        for p in P:
            node = root
            for ch in p:
                if ch not in node.goto:
                    node.goto[ch] = TrieNode()
                node = node.goto[ch]
            node.output.add(p)  # mark terminal state with O(q) <- O(q) U {p}

        # standard AC BFS to build failure links f and inherit outputs
        queue = deque()
        for a, child in root.goto.items():
            child.fail = root
            queue.append(child)
        # for each a with delta(q0, a) undefined: delta(q0, a) <- q0 (root self-loop)
        # (handled lazily in search via .get(a, None) + fallback to root)

        while queue:
            v = queue.popleft()
            for a, u in v.goto.items():
                x = v.fail
                while x is not None and a not in x.goto:
                    x = x.fail
                u.fail = x.goto[a] if (x is not None and a in x.goto) else root
                u.output |= u.fail.output  # O(u) <- O(u) U O(f(u))
                queue.append(u)

    # ---- AC-Search(T) ------------------------------------------------------
    def search(self, text):
        """
        Exact multi-pattern search, following failure links one-by-one on
        every mismatch exactly as in the classical algorithm (no skip table).
        Returns a list of hits: {term, category, meaning, start, end}
        in the order they are found, WITHOUT any overlap resolution,
        scoring, or context filtering (those are enhancements).
        """
        T = text.upper()
        state = self.root
        hits = []

        for i, a in enumerate(T):
            # while delta(state, a) undefined and state != q0: state <- f(state)
            while a not in state.goto and state is not self.root:
                state = state.fail
            # if delta(state, a) defined: state <- delta(state, a) else state <- q0
            state = state.goto.get(a, self.root)

            if state.output:
                for p in state.output:
                    start = i - len(p) + 1
                    category, meaning = self.term_lookup.get(p, ("", ""))
                    hits.append({
                        "term": p,
                        "category": category,
                        "start": start,
                        "end": i + 1,
                    })

        return hits


def load_patterns_from_csv(csv_path):
    """Loads (term, category, meaning) tuples from the medical_dictionary.csv."""
    import csv
    patterns = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            patterns.append((row["term"].strip(), row["category"].strip(), row.get("meaning", "").strip()))
    return patterns
