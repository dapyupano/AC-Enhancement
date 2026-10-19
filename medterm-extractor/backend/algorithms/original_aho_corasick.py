from collections import deque

class TrieNode:

    __slots__ = ("goto", "fail", "output")

    def __init__(self):
        self.goto = {}          # delta(q, a) -> child TrieNode
        self.fail = None        # f(q)
        self.output = set()     # O(q)


class OriginalAhoCorasick:
    """Baseline Aho-Corasick automaton. No performance enhancements."""

    def __init__(self, patterns):
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
                    hits.append({
                        "term": p,
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
