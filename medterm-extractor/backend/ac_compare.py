#!/usr/bin/env python3
import re
import time
from collections import deque

SIGMA = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,-/%()+:")
CHAR_INDEX = {c: i for i, c in enumerate(SIGMA)}
ASCII_INDEX = [-1] * 128
for _i, _c in enumerate(SIGMA):
    code = ord(_c)
    if code < 128:
        ASCII_INDEX[code] = _i

PATTERNS = [
    "BIOGESIC", "PARACETAMOL", "IBUPROFEN", "MEFENAMIC ACID", "AMOXICILLIN",
    "CEFALEXIN", "ASPIRIN", "METFORMIN", "LOSARTAN", "OMEPRAZOLE",
    "CETIRIZINE", "SALBUTAMOL", "BIOFLU", "NEOZEP", "DECOLGEN", "MEDICOL",
    "ALAXAN", "SOLMUX", "KREMIL-S", "BUSCOPAN",
    "BID", "TID", "OD", "PRN", "TAB", "CAP", "MG", "ML",
    "FEVER", "COUGH", "COLD", "COLD COMPRESS",
]

RE_STRAY = re.compile(r"[^A-Z0-9 .,\-/%()+:]")
RE_SPACES = re.compile(r"\s+")

def normalize_text(text):
    text = text.upper()
    text = RE_STRAY.sub(" ", text)
    return RE_SPACES.sub(" ", text).strip()

class Node:
    __slots__ = ("children", "fail", "output", "node_id")

    def __init__(self, node_id):
        self.children = {}
        self.fail = None
        self.output = set()
        self.node_id = node_id

def build_trie(patterns):
    root = Node(0)
    nodes = [root]
    next_id = 1
    for pat in patterns:
        cur = root
        for ch in pat:
            nxt = cur.children.get(ch)
            if nxt is None:
                nxt = Node(next_id)
                next_id += 1
                cur.children[ch] = nxt
                nodes.append(nxt)
            cur = nxt
        cur.output.add(pat)
    return root, nodes

def build_failure_links(root):
    q = deque()
    for child in root.children.values():
        child.fail = root
        q.append(child)

    while q:
        v = q.popleft()
        for ch, u in v.children.items():
            x = v.fail
            while x is not root and ch not in x.children:
                x = x.fail
            u.fail = x.children[ch] if ch in x.children else root
            u.output |= u.fail.output
            q.append(u)
    root.fail = root


class OriginalAC:
    def __init__(self, patterns):
        t0 = time.perf_counter()
        self.root, self.nodes = build_trie(patterns)
        build_failure_links(self.root)
        self.build_time = time.perf_counter() - t0

    def search(self, text):
        root = self.root
        state = root
        hits = []
        hops = 0
        for i, ch in enumerate(text):
            while ch not in state.children and state is not root:
                state = state.fail
                hops += 1
            state = state.children.get(ch, root)
            if state.output:
                for pat in state.output:
                    hits.append((pat, i - len(pat) + 1, i))
        return hits, hops


class EnhancedAC:
    """Enhanced only by precomputing skip table transitions."""

    def __init__(self, patterns):
        t0 = time.perf_counter()
        self.root, self.nodes = build_trie(patterns)
        build_failure_links(self.root)

        n = len(self.nodes)
        m = len(SIGMA)
        self.skip = [[0] * m for _ in range(n)]
        self.outputs = [()] * n

        root = self.root
        for v in self.nodes:
            vid = v.node_id
            self.outputs[vid] = tuple(v.output) if v.output else ()
            for a in SIGMA:
                direct = v.children.get(a)
                if direct is not None:
                    self.skip[vid][CHAR_INDEX[a]] = direct.node_id
                    continue

                x = v.fail
                while x is not root and a not in x.children:
                    x = x.fail
                target = x.children[a] if a in x.children else root
                self.skip[vid][CHAR_INDEX[a]] = target.node_id

        self.build_time = time.perf_counter() - t0

    def search(self, text):
        skip = self.skip
        outputs = self.outputs
        ascii_index = ASCII_INDEX
        state = 0
        hits = []
        append_hit = hits.append

        for i, ch in enumerate(text):
            oc = ord(ch)
            idx = ascii_index[oc] if oc < 128 else -1
            if idx < 0:
                state = 0
                continue
            state = skip[state][idx]
            out = outputs[state]
            if out:
                for pat in out:
                    append_hit((pat, i - len(pat) + 1, i))
        return hits
