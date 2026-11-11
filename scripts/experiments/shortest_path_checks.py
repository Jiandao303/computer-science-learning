#!/usr/bin/env python3
"""最短路笔记里四个「可复现实验」的实现。

对应 docs/30-数据结构与算法/07-最短路算法.md 中的数字：
1. Dijkstra 懒惰删除的三种检查组合 vs 两个检查都删掉
2. 无 S 的 Dijkstra 遇到负环不会终止
3. Floyd-Warshall 六种循环顺序的错误率
4. 0-1 BFS 带不带 S 是否影响正确性

运行：python scripts/experiments/shortest_path_checks.py
只用标准库，结果确定（固定随机种子）。
"""

from __future__ import annotations

import heapq
import random
from collections import deque

INF = float("inf")


def exp1_dijkstra_checks(seed: int = 20261111, v_count: int = 60, e_count: int = 690) -> dict:
    """返回四种检查组合的 (push, pop, 边扫描) 计数。"""
    rnd = random.Random(seed)
    edges = set()
    while len(edges) < e_count:
        u, v = rnd.randrange(v_count), rnd.randrange(v_count)
        if u != v:
            edges.add((u, v))
    adj = [[] for _ in range(v_count)]
    for u, v in edges:
        adj[u].append((v, rnd.randint(1, 100)))

    def run(use_s: bool, use_stale: bool) -> tuple[int, int, int]:
        dist = [INF] * v_count
        dist[0] = 0
        heap = [(0, 0)]
        settled = set()
        push, pop, scans = 1, 0, 0
        while heap:
            d, u = heapq.heappop(heap)
            pop += 1
            if use_s and u in settled:
                continue
            if use_stale and d != dist[u]:
                continue
            if use_s:
                settled.add(u)
            for nxt, w in adj[u]:
                scans += 1
                if use_s and nxt in settled:
                    continue
                nd = d + w
                if nd < dist[nxt]:
                    dist[nxt] = nd
                    heapq.heappush(heap, (nd, nxt))
                    push += 1
        return push, pop, scans

    return {
        "S+stale": run(True, True),
        "S only": run(True, False),
        "stale only": run(False, True),
        "neither": run(False, False),
    }


def exp2_negative_cycle(iter_cap: int = 5000) -> tuple[int, list]:
    """无 S 的懒惰删除 Dijkstra 在负环图上不终止；返回迭代次数与 dist。"""
    v_count = 5
    edges = [(0, 1, 1), (1, 2, 1), (2, 3, 1), (3, 4, 1), (4, 0, -9)]
    dist = [INF] * v_count
    dist[0] = 0
    heap = [(0, 0)]
    it = 0
    while heap and it < iter_cap:
        d, u = heapq.heappop(heap)
        it += 1
        for a, b, w in edges:
            if a == u and d + w < dist[b]:
                dist[b] = d + w
                heapq.heappush(heap, (dist[b], b))
    return it, [None if x == INF else x for x in dist]


def _floyd(matrix, v_count: int, order: str):
    d = [row[:] for row in matrix]
    for a in range(v_count):
        for b in range(v_count):
            for c in range(v_count):
                pos = {order[0]: a, order[1]: b, order[2]: c}
                i, j, k = pos["i"], pos["j"], pos["k"]
                if d[i][k] + d[k][j] < d[i][j]:
                    d[i][j] = d[i][k] + d[k][j]
    return d


def exp3_floyd_orders(n: int = 20000, seed: int = 7, v_count: int = 4) -> dict:
    """六种循环顺序相对「k 在最外层」标准实现的错误次数。"""
    rnd = random.Random(seed)
    orders = ["ijk", "ikj", "jik", "jki", "kij", "kji"]
    errors = {o: 0 for o in orders}
    for _ in range(n):
        w = [[INF] * v_count for _ in range(v_count)]
        for i in range(v_count):
            w[i][i] = 0
        for i in range(v_count):
            for j in range(v_count):
                if i != j and rnd.random() < 0.5:
                    w[i][j] = rnd.randint(1, 9)
        ref = _floyd(w, v_count, "kij")
        for order in orders:
            if _floyd(w, v_count, order) != ref:
                errors[order] += 1
    return errors


def _dijkstra_01(adj, v_count: int, source: int = 0):
    dist = [INF] * v_count
    dist[source] = 0
    heap = [(0, source)]
    while heap:
        d, u = heapq.heappop(heap)
        if d != dist[u]:
            continue
        for nxt, w in adj[u]:
            if d + w < dist[nxt]:
                dist[nxt] = d + w
                heapq.heappush(heap, (dist[nxt], nxt))
    return dist


def _zero_one_bfs(adj, v_count: int, use_s: bool, source: int = 0):
    dist = [INF] * v_count
    dist[source] = 0
    queue = deque([(0, source)])
    settled = set()
    while queue:
        d, u = queue.popleft()
        if use_s and u in settled:
            continue
        if d != dist[u]:
            continue
        if use_s:
            settled.add(u)
        for nxt, w in adj[u]:
            if use_s and nxt in settled:
                continue
            if d + w < dist[nxt]:
                dist[nxt] = d + w
                (queue.appendleft if w == 0 else queue.append)((dist[nxt], nxt))
    return dist


def exp4_zero_one_bfs(n: int = 20000, seed: int = 11, v_count: int = 8) -> dict:
    """带 S / 不带 S 的 0-1 BFS 相对 Dijkstra 的错误次数。"""
    rnd = random.Random(seed)
    bad = {True: 0, False: 0}
    for _ in range(n):
        adj = [[] for _ in range(v_count)]
        for u in range(v_count):
            for v in range(v_count):
                if u != v and rnd.random() < 0.3:
                    adj[u].append((v, rnd.randint(0, 1)))
        ref = _dijkstra_01(adj, v_count)
        for use_s in (True, False):
            if _zero_one_bfs(adj, v_count, use_s) != ref:
                bad[use_s] += 1
    return bad


def main() -> None:
    print("EXP1 Dijkstra 检查组合（60 顶点 / 690 边 / seed=20261111）")
    for name, counts in exp1_dijkstra_checks().items():
        print(f"  {name:10s} push={counts[0]} pop={counts[1]} scans={counts[2]}")

    it, dist = exp2_negative_cycle()
    print(f"EXP2 负环 + 无 S：迭代 {it} 次仍未终止，dist={dist}")

    errors = exp3_floyd_orders()
    print("EXP3 Floyd 六种循环顺序（2 万图 / seed=7）")
    for order, count in errors.items():
        print(f"  for {order}: {count} errors ({count / 20000:.1%})")

    bad = exp4_zero_one_bfs()
    print("EXP4 0-1 BFS（2 万图 / seed=11）")
    for use_s, count in bad.items():
        print(f"  use_S={use_s}: {count} errors")


if __name__ == "__main__":
    main()
