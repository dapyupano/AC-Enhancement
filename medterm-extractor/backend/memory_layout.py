"""
memory_layout.py

Prints, to the Python terminal running app.py, the real memory addresses
of trie nodes for the patterns detected in ONE prescription run:

  BASELINE       -- OriginalAhoCorasick built from just the patterns
                     found in this prescription. Each node is a separate
                     heap allocation created during insertion, so
                     addresses come out scattered (Figure 3.4 style).

  TWO-PASS BFS   -- EnhancedAhoCorasick built the same way. Phase 2 in
                     algorithms/enhanced_aho_corasick.py already assigns
                     bfs_rank (Pass 1) and stores nodes in BFS order in
                     self.nodes (Pass 2). This packs those pointers into
                     one contiguous ctypes buffer and prints each slot's
                     address -- a fixed stride, evenly spaced, matching
                     Figure 4.8.

Called from app.py's /api/analyze route (SOP 2 "Run" button only), the
same way /api/benchmark prints SOP 1's trial timings.
"""

import ctypes
from collections import deque

from algorithms.original_aho_corasick import OriginalAhoCorasick
from algorithms.enhanced_aho_corasick import EnhancedAhoCorasick


def _bfs_walk_original(root):
    order = []
    seen = {id(root)}
    q = deque([root])
    while q:
        v = q.popleft()
        order.append(v)
        for ch in sorted(v.goto.keys()):
            child = v.goto[ch]
            if id(child) not in seen:
                seen.add(id(child))
                q.append(child)
    return order


def _char_labels(root):
    """Map id(node) -> the single character consumed to reach that node
    (the trie edge label), so printing shows 'm', 'o', 'n', ... instead
    of '(internal)'. The root itself is labeled 'root'."""
    labels = {id(root): "root"}
    seen = {id(root)}
    q = deque([root])
    while q:
        v = q.popleft()
        for ch in sorted(v.goto.keys()):
            child = v.goto[ch]
            if id(child) not in seen:
                seen.add(id(child))
                labels[id(child)] = ch
                q.append(child)
    return labels


def _depths(root):
    """Map id(node) -> its depth in the trie (root = 0). BFS naturally
    visits nodes in non-decreasing depth order, so printing this next to
    each address makes the 'why does the letter order look scrambled'
    question visible instead of confusing."""
    depths = {id(root): 0}
    seen = {id(root)}
    q = deque([root])
    while q:
        v = q.popleft()
        for ch in sorted(v.goto.keys()):
            child = v.goto[ch]
            if id(child) not in seen:
                seen.add(id(child))
                depths[id(child)] = depths[id(v)] + 1
                q.append(child)
    return depths


def print_run_memory_layout(detected_terms, max_print=40):
    """
    detected_terms: list[str] of the pattern terms matched in this
    prescription (same list SOP 2's frontend uses to draw the node graph).

    Prints BASELINE and TWO-PASS BFS side by side in two columns, since
    both are built from the identical pattern set with the identical
    sorted-key BFS shape -- row i on the left and row i on the right are
    always the same logical trie node (same depth, same character),
    only their addresses differ.
    """
    if not detected_terms:
        print("\n[SOP 2] No patterns detected in this prescription -- skipping memory layout dump.\n")
        return

    patterns = [(t, "", "") for t in detected_terms]
    baseline = OriginalAhoCorasick(patterns)
    enhanced = EnhancedAhoCorasick(patterns)

    print(f"\n[SOP 2] Two-Pass BFS memory layout for this run "
          f"-- {len(detected_terms)} pattern(s): {detected_terms}")

    # ---- BASELINE: scattered heap addresses ----
    b_nodes = _bfs_walk_original(baseline.root)
    b_labels = _char_labels(baseline.root)
    b_depths = _depths(baseline.root)

    # ---- TWO-PASS BFS: contiguous, fixed-stride addresses ----
    e_nodes = enhanced.nodes  # already Phase-2 bfs_order (Pass 1 + Pass 2)
    e_labels = _char_labels(enhanced._root_ref)
    buf = (ctypes.c_void_p * len(e_nodes))(*(id(n) for n in e_nodes))
    base_addr = ctypes.addressof(buf)
    stride = ctypes.sizeof(ctypes.c_void_p)

    COL = 42
    n = min(len(b_nodes), len(e_nodes), max_print)

    left_header = f"BASELINE -- {len(b_nodes)} nodes (scattered)"
    right_header = f"TWO-PASS BFS -- {len(e_nodes)} nodes (contiguous)"
    print(f"{left_header:<{COL}} | {right_header}")
    print(f"{'-' * COL}-+-{'-' * COL}")

    last_depth = None
    for i in range(n):
        bn, en = b_nodes[i], e_nodes[i]
        depth = b_depths[id(bn)]
        if depth != last_depth:
            marker = f"-- depth {depth} --"
            print(f"{marker:<{COL}} | {marker}")
            last_depth = depth

        left = f"{id(bn):#012x} -> {b_labels.get(id(bn), '?')}"
        slot_addr = base_addr + i * stride
        right = f"{slot_addr:#012x} -> rank={en.bfs_rank:<3}{e_labels.get(id(en), '?')}"
        print(f"{left:<{COL}} | {right}")

    if len(b_nodes) > max_print or len(e_nodes) > max_print:
        remaining = max(len(b_nodes), len(e_nodes)) - max_print
        print(f"... ({remaining} more nodes not shown)")

    print(f"\nStride between TWO-PASS BFS slots: {stride} bytes -> fully contiguous\n")