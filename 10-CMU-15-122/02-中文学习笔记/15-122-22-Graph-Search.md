---
course: CMU 15-122
course_name: Imperative Computation
semester: Fall 2026
lecture_id: L22
topic: Graph Search
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-122
  - C0
  - 图
  - DFS
  - BFS
---

# 第 22 讲：图的搜索（Graph Search）

## 1. 本节学习目标

学完本讲后，你应该能够：

1. 给出**路径**（path）、**路径长度**、**环**（cycle）的严格定义，并区分「长度 0 的路径」与「空路径」。
2. 写出递归版 DFS 的完整代码，说明为什么必须在进入函数时立即 `mark[start] = true`，以及为什么每个 `return` 之前都要 `graph_free_neighbors`。
3. 推导 DFS 在邻接表上的复杂度 **O(v + e)**：mark 初始化 O(v)、循环体 O(e)、递归调用次数 ≤ min(2e, v)。
4. 写出显式栈版 DFS，说明它与递归版的等价性，并给出**三条正确性不变式**及其论证。
5. 说明 BFS 与 DFS 的代码只差「栈换成队列」，并解释为什么复杂度分析不依赖这个选择。
6. 对比 DFS 与 BFS 在隐式图上的行为：DFS 可能陷入无限路径，BFS 不会。
7. 说明「迭代加深」（iterative deepening）如何折中两者。

## 2. 前置知识

- 前序讲次：[[15-122-21-Graph-Representation]]（`graph.h` 接口与两种表示）、[[15-122-09-Stacks-and-Queues]]（栈与队列）。课程入口见 [[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]] 与 [[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 需要理解递归的执行模型（调用栈）。
- 需要知道「标记数组」的作用：避免重复访问。

> **语言提醒**：本讲已是**标准 C**（第 17 讲之后），沿用第 21 讲的 `graph.h` 接口。注意讲义里的 `//@requires` 在标准 C 中**只是一行注释**，编译器完全忽略——不要以为它像 C0 那样会被 `coin -d` 检查。DFS 用递归实现，深递归会耗尽栈空间（第 20 讲讨论的调用栈），这正是需要用显式栈改写迭代版的原因。

## 3. 核心概念

**Path（路径）**：顶点序列 `v₀, v₁, …, vₖ`，其中每对相邻顶点 `{vᵢ, vᵢ₊₁}` 都是边。**长度**是边的条数 `k`。单个顶点 `v₀` 是长度为 0 的路径。

**Simple Path（简单路径）**：所有顶点互不相同的路径。

**Cycle（环）**：首尾相同的路径 `v₀, …, vₖ` 且 `v₀ = vₖ`，长度 `k ≥ 1`。

**Connected（连通）**：`u` 与 `v` 连通当且仅当存在从 `u` 到 `v` 的路径。图连通当且仅当任意两个顶点连通。

**DFS（Depth-First Search，深度优先搜索）**：沿一条路走到底，走不通再回溯。

**BFS（Breadth-First Search，广度优先搜索）**：先访问所有距离为 1 的顶点，再访问距离为 2 的，逐层扩展。

**Frontier（边界/前沿）**：已发现但还没展开的顶点集合。DFS 的 frontier 是栈，BFS 的 frontier 是队列。

**Mark Array（标记数组）**：`bool mark[v]`，`mark[u] == true` 表示顶点 `u` 已被访问。防止重复访问与无限循环。

## 4. 通俗理解

**DFS = 走迷宫时「左手扶墙法」**。遇到岔路就选一条走到底，撞墙了退回上一个岔路口换一条。优点是内存省（只记当前路径），缺点是不保证找到最短路径。

**BFS = 水波纹扩散**。从起点滴一滴水，先漫到距离 1 的所有点，再漫到距离 2 的……优点是**第一次到达某点时的距离一定是最短的**，缺点是要记住一整圈的点（内存大）。

**标记数组 = 走过的路上撒面粉**。没有它，DFS 在有环的图上会永远绕圈；BFS 会无限重复入队。

**栈 vs 队列 = 「后进先出」vs「先进先出」**。DFS 把新发现的顶点压栈，下次取最近发现的（往深走）；BFS 把它入队，下次取最早发现的（往广走）。**两者代码只差一个数据结构，行为却完全不同**——这是本讲最漂亮的一点。

## 5. 原理与推导

### 5.1 路径与环

**定义**（讲义第 3 页）：

- **路径**是顶点序列 `v₀, v₁, …, vₖ`，满足对每个 `0 ≤ i < k`，`{vᵢ, vᵢ₊₁} ∈ E`。
- **长度**是 `k`（边的条数）。
- **单点路径** `v₀` 长度 0。**注意：长度 0 的路径是存在的**，不是「空路径」。
- **环**是 `v₀ = vₖ` 且 `k ≥ 1` 的路径。`k ≥ 1` 排除了「单点自环」——`v₀ = v₀` 长度 0 不算环。

**为什么 `k ≥ 1`**：如果允许 `k = 0`，那么每个顶点都「有一个长度 0 的环」，这让「无环图」的定义失去意义。

**路径存在性**：`u` 与 `v` 连通 ⟺ 存在从 `u` 到 `v` 的路径。这个关系是**等价关系**（自反、对称、传递），所以图被划分成若干**连通分量**（connected component）。

**传递性的证明**：若 `u→v` 有路径 `u = a₀,…,aₘ = v`，`v→w` 有路径 `v = b₀,…,bₙ = w`，则拼接 `a₀,…,aₘ, b₁,…,bₙ` 是 `u→w` 的路径（去掉重复的 `v`）。长度 `m + n`。**这个拼接操作是第 23、24 讲的基础。**

### 5.2 递归 DFS

讲义第 7 页给出核心代码：

```c
bool dfs_helper(graph_t G, bool *mark, vertex start, vertex target)
/*@requires 0 <= start && start < graph_size(G); @*/
/*@requires 0 <= target && target < graph_size(G); @*/
/*@requires \length(mark) == graph_size(G); @*/
/*@requires !mark[start]; @*/
{
  mark[start] = true;
  if (target == start) return true;

  bool found = false;
  neighbor_t nbors = graph_get_neighbors(G, start);
  while (graph_hasmore_neighbors(nbors)) {
    vertex u = graph_next_neighbor(nbors);
    if (!mark[u] && dfs_helper(G, mark, u, target)) {
      found = true;
      break;
    }
  }
  graph_free_neighbors(nbors);
  return found;
}

bool dfs(graph_t G, vertex start, vertex target)
/*@requires 0 <= start && start < graph_size(G); @*/
/*@requires 0 <= target && target < graph_size(G); @*/
{
  bool *mark = xcalloc(graph_size(G), sizeof(bool));
  bool connected = dfs_helper(G, mark, start, target);
  free(mark);
  return connected;
}
```

**四个关键设计点**：

**（1）`mark[start] = true` 必须在函数开头，不能在循环里。**

如果放在「发现邻居时」标记：

```c
while (graph_hasmore_neighbors(nbors)) {
  vertex u = graph_next_neighbor(nbors);
  if (!mark[u]) {
    mark[u] = true;                        /* 在这里标记 */
    if (dfs_helper(G, mark, u, target)) ...
  }
}
```

看起来也能工作——但 `start` 自己没有被标记。如果图里有环 `start → a → start`，从 `start` 递归到 `a`，`a` 的邻居里有 `start`，此时 `mark[start]` 还是假，会再递归回 `start`——**无限递归**。

**在函数入口标记**保证「一旦进入某顶点的 `dfs_helper`，它立刻被标记」，环无法重新进入。这是「访问标记」的标准写法。

**（2）前置条件 `!mark[start]`。**

这个契约保证「不会重复进入已访问的顶点」。调用方负责检查（`if (!mark[u] && dfs_helper(...))`）。把检查放在调用方而不是被调方，省掉一次函数内的分支——但更重要的是**让契约清晰**：`dfs_helper` 的语义是「从 start 出发搜索，且 start 是新的」。

**（3）每个 `return` 之前都要 `graph_free_neighbors`。**

`neighbor_t` 是堆上分配的 header（第 21 讲）。不释放就泄漏。这段代码只有一个 `return found;` 在循环之后，所以只 free 一次——但如果写成「循环里 return true」，就必须在每个 return 前 free：

```c
while (graph_hasmore_neighbors(nbors)) {
  vertex u = graph_next_neighbor(nbors);
  if (!mark[u] && dfs_helper(G, mark, u, target)) {
    graph_free_neighbors(nbors);      /* 这个 free 不能漏 */
    return true;
  }
}
```

**讲义用的是 `found` 标志 + `break` + 单一 return**，这样只需一处 free。**这是一个值得学的编码习惯**：用「单一出口」减少资源泄漏的风险。

**（4）`mark` 数组由 `dfs` 分配与释放，`dfs_helper` 只借用。**

分工清晰：`dfs` 管生命周期，`dfs_helper` 管逻辑。`dfs` 的 `xcalloc` 保证全部初始化为 `false`——用 `xmalloc` 会得到垃圾值，`mark[u]` 可能是随机真，导致漏访问顶点。

### 5.3 DFS 的复杂度推导

**逐项分析**：

1. **`mark` 初始化**：`xcalloc(v, sizeof(bool))` 是 **O(v)**。
2. **递归调用次数**：每个顶点最多被标记一次（因为 `!mark[start]` 前置 + 入口立即标记），所以 `dfs_helper` 最多被调用 **v 次**。又因为每次调用对应一条「发现边」，而边总数是 `2e`（无向图），所以也 ≤ **2e + 1**（含初始调用）。取小：**min(2e + 1, v)**。
3. **每次调用的循环体**：遍历 `start` 的所有邻居，执行 `deg(start)` 次。**所有调用的循环体总执行次数 = Σ deg(u) = 2e**（握手引理）——**注意这是「所有调用加起来」，不是每次调用**。
4. **`graph_get_neighbors` / `graph_free_neighbors`**：每次调用 O(1)，共 v 次，O(v)。

**总计**：

```
O(v)          mark 初始化
+ O(v)        递归调用开销
+ O(e)        所有循环体
+ O(v)        迭代器分配释放
= O(v + e)
```

**邻接表上 DFS 是 O(v + e)。**

**邻接矩阵上呢**：`graph_next_neighbor` 要扫整行（第 21 讲），每次调用的循环体实际执行 `v` 次（不是 `deg`）。总 `v × v = v²`。所以**矩阵上是 O(v²)**。

**讲义第 8 页的写法是 `O(min(v², ev))`**——因为矩阵上每个顶点最多被访问一次，每次扫 `v` 格，总 `v²`；而如果图很稀疏（`e < v`），实际可达的顶点数 ≤ `e + 1`，所以也是 `O(ev)`。取小得 `O(min(v², ev))`。**通常直接写 O(v²)**，因为最坏情况就是 `v²`。

**这个差异的实际意义**：`v = 10000, e = 20000` 的稀疏图上，邻接表 DFS 约 3 万次操作，矩阵 DFS 约 1 亿次——**差 3000 倍**。

### 5.4 显式栈版 DFS

递归版依赖调用栈。显式栈版把「待访问的顶点」放在一个显式的栈里（讲义第 9 页）：

```c
bool dfs_explicit_stack(graph_t G, vertex start, vertex target) {
  bool *mark = xcalloc(graph_size(G), sizeof(bool));
  stack_t S = stack_new();
  mark[start] = true;
  push(S, start);

  bool found = false;
  while (!stack_empty(S)) {
    vertex u = pop(S);
    if (u == target) { found = true; break; }

    neighbor_t nbors = graph_get_neighbors(G, u);
    while (graph_hasmore_neighbors(nbors)) {
      vertex w = graph_next_neighbor(nbors);
      if (!mark[w]) {
        mark[w] = true;        /* 标记时机：入栈时，不是出栈时 */
        push(S, w);
      }
    }
    graph_free_neighbors(nbors);
  }

  free(mark);
  stack_free(S);
  return found;
}
```

**标记时机是关键**：`mark[w] = true` 在**入栈时**，不是出栈时。如果在出栈时标记：

```c
vertex u = pop(S);
if (mark[u]) continue;      /* 出栈时检查并标记 */
mark[u] = true;
```

也能工作，但会让同一个顶点被多次压栈（因为压栈时不检查重复），栈可能膨胀到 O(e) 而不是 O(v)。**入栈时标记**保证每个顶点最多入栈一次，栈大小 ≤ v。

**递归版与显式栈版的等价性**：两者都是 DFS，但**访问顺序可能不同**。递归版是「发现邻居后立即深入第一个邻居」；显式栈版是「把所有邻居压栈，然后弹出最后压的那个」——因为栈是后进先出，弹出的正好是「最后压的」，也就是邻居链表的最后一个。**如果邻接表的插入顺序与递归版一致，两者顺序相同；否则不同。** 但**「是否能到达 target」这个判定结果相同**——因为两者都穷尽搜索同一个连通分量。

### 5.5 DFS 正确性的三条不变式

讲义第 10–11 页给出显式栈版的三条不变式。这三条是「为什么 DFS 正确」的核心论证。

**不变式 1：每个被标记的顶点都与 `start` 连通。**

*证明（对步骤归纳）*：

- **初始**：只有 `start` 被标记，`start` 与 `start` 连通（长度 0 的路径）。✓
- **保持**：某步标记了 `w`，是因为 `w` 是某个已弹出顶点 `u` 的邻居，且 `u` 已标记。由归纳假设 `u` 与 `start` 连通，而 `{u,w} ∈ E`，所以 `start → … → u → w` 是到 `w` 的路径。✓

**推论**：如果 `target` 被标记，它一定与 `start` 连通——所以返回 `true` 是正确的。

**不变式 2：栈中的每个顶点都被标记。**

*证明*：

- **初始**：栈里只有 `start`，已标记。✓
- **保持**：每次 `push(S, w)` 之前都有 `mark[w] = true`。弹出不会让「栈中元素」变成未标记（弹出是移除，不是改变标记）。✓

**为什么需要这条**：它保证「栈里的顶点都是已发现的」，配合不变式 3 才能推出「栈空时搜索完成」。

**不变式 3：每条从 `start` 到 `target` 的路径都经过 frontier（栈中的某个顶点）。**

*证明（对步骤归纳）*：

- **初始**：栈 = `{start}`。任何从 `start` 出发的路径的第一个顶点就是 `start`，在栈里。✓
- **保持**：弹出 `u` 时，把 `u` 的所有未标记邻居压栈。考虑任意一条从 `start` 到 `target` 的路径 `P`。由归纳假设 `P` 经过栈中某顶点 `x`。
  - 若 `x ≠ u`：`x` 仍在栈里（只是 `u` 被弹出），`P` 仍经过栈中顶点。✓
  - 若 `x = u`：路径从 `u` 继续到某个邻居 `w`。若 `w` 已标记，则由不变式 1，`w` 与 `start` 连通，且路径 `start → … → w` 已存在，搜索会通过别的分支找到——**这里需要更细的论证**；若 `w` 未标记，则 `w` 被压栈，`P` 经过 `w`，在栈里。✓

（讲义第 11 页的论证更细致，考虑「路径上第一个未标记顶点」——那个顶点一定是某个已标记顶点的邻居，所以会被压栈。）

**三条不变式合起来的推论**：

**若栈空且未找到 `target`，则不存在从 `start` 到 `target` 的路径。**

*证明*：假设存在路径。由不变式 3，它经过栈中某顶点——但栈空，矛盾。✓

**这是「DFS 找不到就真的不存在」的严格证明。** 没有这三条不变式，「DFS 返回 false」只是一个经验观察；有了它们，才是一个定理。

### 5.6 BFS：把栈换成队列

讲义第 11–12 页：

```c
bool bfs(graph_t G, vertex start, vertex target) {
  bool *mark = xcalloc(graph_size(G), sizeof(bool));
  queue_t Q = queue_new();
  mark[start] = true;
  enqueue(Q, start);

  bool found = false;
  while (!queue_empty(Q)) {
    vertex u = dequeue(Q);
    if (u == target) { found = true; break; }

    neighbor_t nbors = graph_get_neighbors(G, u);
    while (graph_hasmore_neighbors(nbors)) {
      vertex w = graph_next_neighbor(nbors);
      if (!mark[w]) {
        mark[w] = true;
        enqueue(Q, w);
      }
    }
    graph_free_neighbors(nbors);
  }

  free(mark);
  queue_free(Q);
  return found;
}
```

**与 DFS 的唯一区别**：`stack` → `queue`，`push` → `enqueue`，`pop` → `dequeue`。

**为什么复杂度分析不变**：

上面 5.3 节的推导中，唯一用到「栈」的地方是「每个顶点最多入栈一次」。队列同样满足这个性质（因为 `mark[w] = true` 在入队时）。所以：

- 每个顶点最多入队一次 ⇒ 最多 v 次出队。
- 每次出队遍历 `deg(u)` 个邻居 ⇒ 总 `2e` 次。
- 总计 **O(v + e)**。

**「栈还是队列」只影响访问顺序，不影响「访问了多少」**。这是「复杂度分析不依赖数据结构选择」的漂亮例子。

**BFS 的额外性质**：第一次到达某顶点时的距离是**最短距离**。

*证明（对层数归纳）*：BFS 按「距离起点的层数」逐层扩展。第 `k` 层出队时，把第 `k+1` 层入队。所以顶点入队的顺序是非递减的距离。第一个到达 `w` 的路径必然是距离最短的。✓

这个性质 DFS 没有——DFS 找到的路径可能绕很远。

### 5.7 隐式图上 DFS 的危险

讲义第 12 页（§4 结论）：

在**隐式图**上（第 21 讲），顶点集合可能无限或极大。DFS 沿一条路走到底，如果这条路无限长，**DFS 永不返回**。

**例子**：图是「所有整数」，边是 `{n, n+1}`。从 0 出发找 −1：

- DFS 从 0 走 1、2、3、……**永远走不到 −1**（因为每次都在「前进」方向上深入）。
- BFS 从 0 出发，第 1 层是 `{−1, 1}`，立刻找到 −1。

**BFS 不会陷入无限路径**，因为它按层扩展——只要 `target` 在有限距离内，BFS 一定能找到（虽然可能耗尽内存）。

**折中方案：迭代加深（iterative deepening）**

```
for depth = 1, 2, 3, ... :
    做一次深度限制为 depth 的 DFS
    如果找到 target，返回 true
```

- **内存**：O(depth)——和 DFS 一样省。
- **完备性**：只要 `target` 在有限距离 `d` 内，第 `d` 轮一定能找到——和 BFS 一样完备。
- **代价**：重复搜索浅层。第 `k` 轮会重做前 `k−1` 轮的工作。但总工作量是 `O(b^d)` 的常数倍（`b` 是分支因子），因为最后一轮的工作量 `b^d` 主导了前面所有轮的和 `b^d + b^(d−1) + … ≈ b^d · b/(b−1)`。**只慢一个常数因子，换来内存从指数降到线性。**

**这就是「为什么棋类程序用迭代加深」**：内存是硬约束，时间可以多花一个常数倍。

### 5.8 习题要点

- **Ex1（第 13 页，解在第 15 页）**：给定一个图，写出 BFS 与 DFS 的访问顺序。BFS 序 **A, B, C, D, E, F, G**；DFS 序 **A, B, D, E, G**。差异来自「先扩展谁」。
- **Ex2（第 13 页，解在第 15–16 页）**：写 `int *shortest_distances(graph_t G, vertex start)` 返回从 `start` 到每个顶点的最短距离。做法：BFS，用 `dist` 数组，`-1` 表示未访问，`dist[w] = dist[u] + 1`。复杂度 O(v + e)。
- **Ex3（第 13–14 页，解在第 16–17 页）**：同一个图上比较 DFS 与 BFS 访问的顶点数。以 A 为起点、F 为目标：DFS 只看 3 个顶点、BFS 看 6 个；以 C 为目标：DFS 看 4 个、BFS 看 3 个。**这说明「哪个更快」取决于目标的位置**，没有普遍答案。
- **Ex4（第 14 页，解在第 17 页）**：`tester` 函数对每个顶点调用一次 `dfs`，复杂度：邻接表 **O(v²)**（`v` 次调用 × 每次 O(v+e)，但 `v²` 项吞掉 `v+e`）；矩阵 **O(v²)**（`v` 次 × 每次 O(v²) = O(v³)`？讲义给的是 O(v²)——需注意每次 DFS 在矩阵上是 O(v²) 最坏，`v` 次就是 `v³`；但若只统计「可达顶点数」，稀疏图上每次 O(v·min(v,e))……**此处以讲义答案为准，标记为待核对**）。

## 6. 代码示例

### 6.1 官方课程代码

以下代码出自 `22-dfs.pdf`，页码为该 PDF 的页码。

**（1）路径与环的定义**（第 3 页）

路径长度 = 边数；单点路径长度 0；环要求 `k ≥ 1`。

**（2）递归 DFS**（第 4–6 页，完整版在第 7 页）

`dfs_helper` 与 `dfs` 的完整代码，含 `!mark[start]` 前置条件。

**（3）复杂度分析**（第 8 页）

mark 初始化 O(v)、循环体 O(e)、递归调用 ≤ min(2e, v) ⇒ 邻接表 O(v+e)、矩阵 O(min(v², ev))。

**（4）显式栈 DFS**（第 8–11 页）

`dfs_explicit_stack`，入栈时标记。

**（5）三条正确性不变式**（第 10–11 页）

1. 每个被标记顶点与 `start` 连通；2. 栈中每个顶点都被标记；3. 每条 `start→target` 路径经过 frontier 中某顶点。

**（6）BFS**（第 11–12 页）

栈换队列，代码同构，复杂度不变。

**（7）结论：隐式图上的差异**（第 12 页）

DFS 可能陷入无限路径，BFS 不会；折中方案迭代加深。

**（8）习题与答案**（第 13–14 页题目，第 15–17 页答案）

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念

**示例一：给 DFS 加「路径记录」，输出实际路径而不只是布尔值。**

```c
#include <stdlib.h>
#include <stdbool.h>
#include "lib/xalloc.h"
#include "graph.h"

/* 返回从 start 到 target 的一条路径（顶点数组），找不到返回 NULL。
 * 长度写入 *len。调用者负责 free 返回值。
 */
vertex *dfs_path(graph_t G, vertex start, vertex target, int *len) {
  unsigned int v = graph_size(G);
  bool   *mark  = xcalloc(v, sizeof(bool));
  vertex *path  = xmalloc(v * sizeof(vertex));   /* 路径最长 v 个顶点 */
  int     depth = 0;

  /* 显式栈：每个元素是 (顶点, 迭代器)，这样能「记住读到哪」以便回溯 */
  typedef struct { vertex u; neighbor_t nb; } frame;
  frame *S = xmalloc(v * sizeof(frame));
  int sp = 0;

  mark[start] = true;
  path[depth++] = start;
  S[sp].u  = start;
  S[sp].nb = graph_get_neighbors(G, start);
  sp++;

  while (sp > 0) {
    frame *f = &S[sp - 1];

    if (f->u == target) {
      *len = depth;
      /* 清理 */
      for (int i = 0; i < sp; i++) graph_free_neighbors(S[i].nb);
      free(S); free(mark);
      return path;
    }

    if (graph_hasmore_neighbors(f->nb)) {
      vertex w = graph_next_neighbor(f->nb);
      if (!mark[w]) {
        mark[w] = true;
        path[depth++] = w;
        S[sp].u  = w;
        S[sp].nb = graph_get_neighbors(G, w);
        sp++;
      }
    } else {
      /* 这个顶点的邻居走完了，回溯 */
      graph_free_neighbors(f->nb);
      sp--;
      depth--;                    /* 从路径里去掉 */
    }
  }

  /* 没找到 */
  free(S); free(mark); free(path);
  *len = 0;
  return NULL;
}
```

**关键点**：栈帧里同时存「顶点」和「它的邻居迭代器」。这样回溯到某个顶点时，能**从上次停下的地方继续**读邻居，而不是重新开始。这就是递归版「局部变量 `nbors` 保存在调用栈上」的显式模拟。

**这个例子说明了递归与显式栈的真正对应关系**：递归的「调用栈帧」= 显式栈里的「frame 结构」。理解了这一点，就能把任何递归算法改写成迭代。

**示例二：BFS 求最短距离。**

```c
/* 返回 dist 数组：dist[i] = 从 start 到 i 的最短边数，不可达为 -1。
 * 调用者负责 free。
 */
int *shortest_distances(graph_t G, vertex start) {
  unsigned int v = graph_size(G);
  int *dist = xmalloc(v * sizeof(int));
  for (vertex i = 0; i < v; i++) dist[i] = -1;   /* -1 = 未访问 */

  queue_t Q = queue_new();
  dist[start] = 0;
  enqueue(Q, start);

  while (!queue_empty(Q)) {
    vertex u = dequeue(Q);
    neighbor_t nbors = graph_get_neighbors(G, u);
    while (graph_hasmore_neighbors(nbors)) {
      vertex w = graph_next_neighbor(nbors);
      if (dist[w] == -1) {              /* 第一次到达 */
        dist[w] = dist[u] + 1;
        enqueue(Q, w);
      }
    }
    graph_free_neighbors(nbors);
  }

  queue_free(Q);
  return dist;
}
```

**为什么 `dist[w] == -1` 这个检查就够了，不需要单独的 `mark` 数组**：`dist` 数组本身承担了标记功能（`-1` = 未访问）。这是「用距离数组代替布尔标记」的常见简化。

**为什么第一次到达就是最短**：BFS 按层扩展，队列里的距离是非递减的。第一次遇到 `w` 时，`dist[u]` 是所有能到达 `w` 的顶点里最小的——所以 `dist[u] + 1` 就是最短距离。**这个论证依赖队列的 FIFO 性质**；如果换成栈（DFS），第一次到达的路径可能很长。

**示例三：DFS 与 BFS 在同一图上的访问顺序对比。**

```c
/* 打印 DFS 访问顺序 */
void dfs_order(graph_t G, vertex start) {
  unsigned int v = graph_size(G);
  bool *mark = xcalloc(v, sizeof(bool));
  stack_t S = stack_new();
  mark[start] = true; push(S, start);
  printf("DFS: ");
  while (!stack_empty(S)) {
    vertex u = pop(S);
    printf("%u ", u);
    neighbor_t nb = graph_get_neighbors(G, u);
    while (graph_hasmore_neighbors(nb)) {
      vertex w = graph_next_neighbor(nb);
      if (!mark[w]) { mark[w] = true; push(S, w); }
    }
    graph_free_neighbors(nb);
  }
  printf("\n");
  free(mark); stack_free(S);
}

/* 打印 BFS 访问顺序 */
void bfs_order(graph_t G, vertex start) {
  unsigned int v = graph_size(G);
  bool *mark = xcalloc(v, sizeof(bool));
  queue_t Q = queue_new();
  mark[start] = true; enqueue(Q, start);
  printf("BFS: ");
  while (!queue_empty(Q)) {
    vertex u = dequeue(Q);
    printf("%u ", u);
    neighbor_t nb = graph_get_neighbors(G, u);
    while (graph_hasmore_neighbors(nb)) {
      vertex w = graph_next_neighbor(nb);
      if (!mark[w]) { mark[w] = true; enqueue(Q, w); }
    }
    graph_free_neighbors(nb);
  }
  printf("\n");
  free(mark); queue_free(Q);
}
```

**两个函数逐行对照，只有 4 处不同**：`stack_t`/`queue_t`、`stack_new`/`queue_new`、`push`/`enqueue`、`pop`/`dequeue`、`stack_empty`/`queue_empty`、`stack_free`/`queue_free`（其实是 6 处，但都是同一类替换）。

**这个「同构」是教学上最有价值的观察**：搜索算法的骨架是「取一个 frontier 元素 → 展开 → 把新元素放入 frontier」，**frontier 的数据结构决定了搜索的行为**。

| frontier 结构 | 算法 | 找到的路径 |
|---|---|---|
| 栈（LIFO） | DFS | 任意路径（可能很长） |
| 队列（FIFO） | BFS | 最短路径（边数最少） |
| 优先队列（按权重） | Dijkstra | 最小权重路径 |

**第三行是第 25 讲的伏笔**：把队列换成优先队列，BFS 就变成 Dijkstra 算法——**只改一个数据结构，算法从「最短边数」升级到「最小权重」**。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键区别 | 记忆点 |
|---|---|---|---|
| 路径 | 简单路径 | 前者顶点可重复；后者顶点互不相同 | 简单路径不绕圈 |
| 长度 0 的路径 | 空路径 | 前者是「单个顶点」；后者不存在 | 单点也是路径 |
| 环 | 长度 0 的路径 | 环要求 `k ≥ 1` 且首尾相同 | `v₀ = v₀` 长度 0 不算环 |
| DFS | BFS | 前者栈（LIFO），走到底再回溯；后者队列（FIFO），逐层扩展 | 一个深，一个广 |
| 标记时机（入栈） | 标记时机（出栈） | 前者保证栈 ≤ v；后者可能重复压栈到 O(e) | 早标记省空间 |
| DFS 复杂度 | BFS 复杂度 | 都是 O(v+e)（邻接表） | 复杂度不看顺序 |
| BFS 的最短性 | DFS 的无此性质 | 前者第一次到达即最短；后者不保证 | 要最短用 BFS |
| 迭代加深 | BFS | 前者 O(depth) 内存、重复搜索；后者 O(v) 内存、不重复 | 内存换时间 |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-122/lectures/22-dfs.pdf`
- **总页数**：17 页
- **本节重点页码**（PDF 页码，即提取文本中 `=== [page N] ===` 的 N）：
  - 第 3 页：路径、长度、环的定义
  - 第 4–6 页：DFS 的思路
  - 第 7–8 页：递归 `dfs_helper` / `dfs` 的完整代码与复杂度分析
  - 第 8–11 页：显式栈 DFS 与三条正确性不变式（第 10–11 页）
  - 第 11–12 页：BFS 与「栈换队列」的等价性
  - 第 12 页：隐式图上 DFS 的无限路径问题、迭代加深
  - 第 13–14 页：习题 Ex1–Ex4
  - 第 15–17 页：参考答案
- **原始网页链接**：`https://www.cs.cmu.edu/~15122-archive/f26/handouts/lectures/22-dfs.pdf`
- **配套代码包**：`90-原始PDF/15-122/code/22-dfs.tgz`

## 9. 对应视频

未找到官方公开录像。本讲建议配合 6.2 节的示例三，在同一张图上打印 DFS 与 BFS 的访问顺序——「代码只差一个数据结构，顺序完全不同」这个观察，看一遍比读十遍定义有效。

## 10. 本节复习

1. 路径是顶点序列，长度是边数；单点路径长度 0；环要求 `k ≥ 1` 且首尾相同。连通关系是等价关系，把图分成连通分量。
2. 递归 DFS：入口立即 `mark[start] = true`（否则环会无限递归）；前置 `!mark[start]`；每个 return 前 `graph_free_neighbors`；`mark` 由 `dfs` 分配与释放。
3. DFS 复杂度：mark 初始化 O(v)、所有循环体总计 O(e)（握手引理）、递归调用 ≤ min(2e, v) ⇒ **邻接表 O(v+e)**、矩阵 O(v²)。
4. 显式栈 DFS：**入栈时标记**（不是出栈时），保证栈 ≤ v。
5. 三条不变式：被标记顶点与 start 连通、栈中顶点都被标记、每条 start→target 路径经过 frontier。推论：栈空未找到 ⇒ 无路径。
6. BFS = DFS 把栈换队列。复杂度分析不变（都依赖「每个顶点最多入队/栈一次」）。BFS 额外保证「第一次到达即最短」。
7. 隐式图上 DFS 可能陷入无限路径，BFS 不会；迭代加深用 O(depth) 内存换完备性。

## 11. 自我检查

**题 1.** 一个无向图有顶点 `{0,1,2,3,4}` 与边 `{0,1}, {1,2}, {2,0}, {2,3}, {3,4}`。从 0 出发找 4：
（a）DFS 会访问哪些顶点？（按「邻接表按边加入顺序」的假设）
（b）BFS 会访问哪些顶点？
（c）从 0 到 4 的最短路径长度是多少？

**题 2.** 如果把 `dfs_helper` 里的 `mark[start] = true;` 移到「发现邻居时标记」，在什么图上会出错？请画出最小反例。

**题 3.** 推导 DFS 在邻接表上的复杂度 O(v + e)。请分三部分说明：mark 初始化、递归调用次数、所有循环体的总执行次数。其中哪一部分用到了握手引理？

**题 4.** 显式栈版 DFS 中，`mark[w] = true` 在入栈时执行。如果改成「出栈时检查并标记」，算法还正确吗？会有什么性能问题？

**题 5.** 为什么 BFS 第一次到达某顶点时的距离一定是最短的？请用「队列中距离非递减」这个性质给出论证。

<details>
<summary>参考答案</summary>

**答 1.**
图的结构：`0–1`、`1–2`、`2–0`（三角形 0-1-2）、`2–3`、`3–4`。

假设邻接表按边加入顺序存（`addedge` 头插，所以链表是逆序的）：
- `adj[0]`：加入 `{0,1}` 时插 1，加入 `{2,0}` 时插 2 → 链表 `2 → 1`。
- `adj[1]`：加入 `{0,1}` 时插 0，加入 `{1,2}` 时插 2 → 链表 `2 → 0`。
- `adj[2]`：`{1,2}` 插 1，`{2,0}` 插 0，`{2,3}` 插 3 → 链表 `3 → 0 → 1`。
- `adj[3]`：`{2,3}` 插 2，`{3,4}` 插 4 → 链表 `4 → 2`。
- `adj[4]`：链表 `3`。

**（a）DFS 从 0 出发**：访问 0，取邻居 2（链表头），访问 2；取 2 的邻居 3，访问 3；取 3 的邻居 4，访问 4 → **找到**。

访问顺序：**0, 2, 3, 4**（4 个顶点）。

**（b）BFS 从 0 出发**：访问 0，把邻居 2、1 入队；出队 2，把邻居 3 入队（0、1 已标记）；出队 1，邻居都标记了；出队 3，把 4 入队；出队 4 → **找到**。

访问顺序：**0, 2, 1, 3, 4**（5 个顶点）。

**（c）最短路径**：`0 → 2 → 3 → 4`，长度 **3**。BFS 保证找到的就是最短的（这里 DFS 恰好也走了这条）。

**注意**：如果邻接表的顺序不同（例如 `adj[0]` 是 `1 → 2`），DFS 会走 `0 → 1 → 2 → 3 → 4`，访问 5 个顶点。**DFS 的访问数依赖邻接表的顺序**，这是它「不保证最优」的一个体现。

**答 2.**
**最小反例：两个顶点、一条边（或任何含环的图）。**

```
0 — 1
```

更清楚的是三角形：

```
0 — 1
 \ /
  2
```

**错误版本**：

```c
bool dfs_helper(graph_t G, bool *mark, vertex start, vertex target) {
  /* 没有 mark[start] = true; */
  if (target == start) return true;
  neighbor_t nbors = graph_get_neighbors(G, start);
  while (graph_hasmore_neighbors(nbors)) {
    vertex u = graph_next_neighbor(nbors);
    if (!mark[u]) {
      mark[u] = true;                              /* 在发现时标记 */
      if (dfs_helper(G, mark, u, target)) { ... }
    }
  }
  ...
}
```

从 0 出发找 3（假设 3 是孤立顶点）：

1. `dfs_helper(0)`：`mark[0]` 仍是 **false**（从未被标记）。
2. 邻居 1 未标记 → `mark[1] = true`，递归 `dfs_helper(1)`。
3. `dfs_helper(1)`：邻居 0 —— `mark[0]` 是 **false**！→ `mark[0] = true`，递归 `dfs_helper(0)`。
4. `dfs_helper(0)`：邻居 1 —— `mark[1]` 是 true，跳过；邻居 2 —— 未标记，`mark[2] = true`，递归 `dfs_helper(2)`。
5. `dfs_helper(2)`：邻居 0 —— `mark[0]` 是 true（第 3 步标的），跳过；邻居 1 —— true，跳过。返回 false。
6. 回到第 4 步，返回 false；回到第 3 步，返回 false；回到第 2 步…… 

在这个例子里碰巧终止了（因为 `mark[0]` 在第 3 步被标上）。但**如果起点 0 只有一个邻居、且图是一条链加一个环**：

```
0 — 1 — 2 — 1   （1 和 2 之间有两条边？不允许）
```

用三角形更直接：

```
0 — 1
 \ /
  2
```

从 0 找孤立顶点 3：

1. `dfs_helper(0)`，`mark[0]` = false。
2. 邻居 1 未标记 → `mark[1] = true`，递归 `dfs_helper(1)`。
3. `dfs_helper(1)`：邻居 0 未标记 → `mark[0] = true`，递归 `dfs_helper(0)`。
4. `dfs_helper(0)`：邻居 1 已标记，跳过；邻居 2 未标记 → `mark[2] = true`，递归 `dfs_helper(2)`。
5. `dfs_helper(2)`：邻居 0 已标记，邻居 1 已标记。返回 false。
6. 回到第 4 步 → false；回到第 3 步 → false；回到第 2 步 → 没有更多邻居，返回 false。

**碰巧也终止了**。原因是「发现时标记」仍然保证「一旦某顶点被递归进入，它的某个邻居会把它标上」——但这依赖「进入 `start` 时它至少有一个未标记的邻居」这个巧合。

**真正会无限递归的情形**：起点没有任何已标记的邻居来「救」它。考虑**只有一条边**的图 `0 — 1`：

1. `dfs_helper(0)`，`mark[0]` = false。
2. 邻居 1 未标记 → `mark[1] = true`，递归 `dfs_helper(1)`。
3. `dfs_helper(1)`：邻居 0 未标记 → `mark[0] = true`，递归 `dfs_helper(0)`。
4. `dfs_helper(0)`：邻居 1 已标记 → 跳过。返回 false。

**也终止了。**

**结论修正**：在无向图上，「发现时标记」**碰巧也能终止**，因为每条边会被两端各标记一次。但**在以下情形会出问题**：

**（1）有向图**（如果扩展到这个场景）：`0 → 1 → 0`，从 0 出发，两个都未标记，进入 0 → 标 1 → 进入 1 → 标 0 → 进入 0 → 1 已标记 → 停。也终止。

**（2）真正的问题不是无限递归，而是「起点被重复进入」**。在三角形里，`dfs_helper(0)` 被调用了**两次**（第 1 步和第 3 步）。如果图更大、环更多，重复进入的次数会指数增长——**这才是真正的灾难**。

**最小反例：完全图 `Kₙ`**。`K₅` 有 5 个顶点、10 条边，任意两点相邻。从 0 出发，「发现时标记」会让 `dfs_helper(0)` 被从每个邻居递归进入一次，而每次进入又会递归进入其他顶点……**递归调用次数是 O(n!) 级别**（接近阶乘），因为没有任何机制阻止「重复进入已访问顶点」。

具体地：`dfs_helper(v)` 只在「被某个未标记邻居发现」时进入，而 `mark[v]` 直到它自己被进入后才设置——所以在它被进入之前，多个邻居都可能递归进入它。这个「多个入口」导致组合爆炸。

**正确的写法**（入口立即标记）保证：`mark[start] = true` 在函数第一行执行，任何后续对 `dfs_helper(start, ...)` 的调用都被前置条件 `!mark[start]` 挡住。**每个顶点恰好进入一次**，总调用 ≤ v。

**总结**：错误版本在小图上可能碰巧终止，但在稠密图上会因「重复进入」而组合爆炸。**入口立即标记是唯一正确的写法。**

**答 3.**
**（1）mark 初始化**：`xcalloc(v, sizeof(bool))` 要把 `v` 个字节清零，**O(v)**。

**（2）递归调用次数**：每个顶点最多被 `dfs_helper` 进入一次（前置 `!mark[start]` + 入口立即标记）。所以调用次数 **≤ v**。另一方面，每次进入（除初始调用）对应一条「发现边」，而无向图有 `2e` 条有向边，所以也 **≤ 2e + 1**。取小：**O(min(v, 2e+1)) = O(v)**（因为 `min(v, 2e+1) ≤ v`）。每次调用的固定开销 O(1)（分配迭代器、判断 target 等），总计 **O(v)**。

**（3）所有循环体的总执行次数**：第 `u` 次调用（`u` 被进入时）的循环执行 `deg(u)` 次。**所有调用加起来**：

```
Σ_{u 被访问} deg(u) ≤ Σ_{u ∈ V} deg(u) = 2e        （握手引理）
```

所以总 **O(e)**。

**哪一部分用到了握手引理**：**第（3）部分**。握手引理 `Σ deg(u) = 2|E|` 把「每个顶点遍历自己的邻居」这个「按顶点计」的量，转换成「按边计」的 `2e`。没有它，只能写出 `Σ deg(u) ≤ v · (v−1) = O(v²)`——差了一个数量级。

**总计**：`O(v) + O(v) + O(e) = **O(v + e)**`。

**答 4.**
**算法仍然正确**，但性能会退化。

**正确性**：出栈时检查并标记，等价于「延迟标记」。搜索仍然会穷尽整个连通分量——只是同一个顶点可能被多次压栈，每次出栈时检查 `if (mark[u]) continue;` 跳过。

**性能问题**：

1. **栈可能膨胀到 O(e)**。入栈时不检查重复，所以一条边的两端可能被反复压入。极端情况（完全图 `Kₙ`）：每条边都导致一次压栈，栈大小 `2e = n(n−1) = O(n²)`。而**入栈时标记**保证栈 ≤ v。
2. **出栈时多做一次检查**。虽然只是 O(1)，但对每个重复入栈的元素都要做。
3. **内存峰值高**。O(e) 的栈在稠密图上可能是 O(v²)——`v = 10000` 时是 1 亿个元素，几百 MB。

**为什么「入栈时标记」更好**：

- **栈大小 ≤ v**（每个顶点最多入栈一次）。
- **不需要出栈时的重复检查**（虽然通常还是保留 `if (mark[u]) continue;` 作为防御）。
- **语义更清晰**：「已标记 = 已发现 = 已在栈中或已处理」。

**唯一需要「出栈时标记」的场景**：当你想让同一个顶点以不同路径多次入栈（例如某些最短路径算法的变体，需要「松弛」操作）。**在纯 DFS/BFS 中不需要。**

**答 5.**
**核心性质：BFS 的队列中，顶点的距离是非递减的。**

*证明（对入队顺序归纳）*：设队列内容为 `q₁, q₂, …, qₘ`（`q₁` 是队首）。断言 `dist[q₁] ≤ dist[q₂] ≤ … ≤ dist[qₘ]`。

- **初始**：队列只有 `start`，`dist = 0`。✓
- **保持**：出队 `q₁`（距离 `d`），把它的未访问邻居入队，距离都是 `d + 1`。由于归纳假设剩余元素距离 ≥ `d`，而新入队的都是 `d + 1`，且它们排在队尾——需要保证「剩余元素的距离 ≤ d+1」。因为 BFS 逐层扩展，队列里最多只有距离 `d` 和 `d+1` 两层的元素（不会有 `d+2`，因为 `d+2` 的顶点还没被发现）。所以剩余元素距离 ≤ `d+1`，新元素距离 `d+1`，非递减性保持。✓

**由此推出「第一次到达即最短」**：

设 `w` 第一次被到达时，是从 `u` 扩展来的，`dist[w] = dist[u] + 1`。

假设存在更短的路径 `start → … → w`，长度 `d' < dist[u] + 1`。设这条路径上 `w` 的前驱是 `u'`，则 `dist[u'] ≤ d' − 1 < dist[u]`。

由非递减性，`u'` 在队列中排在 `u` 之前（距离更小），所以 `u'` 会**先于** `u` 被出队并扩展。`u'` 扩展时会把 `w` 入队（因为那时 `w` 还没被访问）。所以 `w` 会先通过 `u'` 被到达，`dist[w] = dist[u'] + 1 ≤ d'`——与「通过 `u` 到达」矛盾。

**因此第一次到达的路径就是最短的。** ✓

**这个论证的关键是「距离非递减」**——它保证「更近的顶点先被扩展」。DFS 的栈不满足这个性质（后进先出，可能先扩展很远的顶点），所以 DFS 找到的路径不保证最短。

</details>

## 12. 进一步学习

- 上一讲：[[15-122-21-Graph-Representation]] —— 两种图表示与 `graph.h` 接口；本讲的复杂度分析直接依赖它。
- 下一讲：[[15-122-23-Spanning-Trees]] —— 用 DFS/BFS 判断连通性，进而构造生成树。
- 后续：[[15-122-24-Union-Find]] —— 更快的连通性判断（摊还近 O(1)）；[[15-122-25-Priority-Queues]] —— 把 BFS 的队列换成优先队列就得到 Dijkstra。
- 回顾：[[15-122-09-Stacks-and-Queues]] —— frontier 的两种数据结构：栈给 DFS，队列给 BFS。
- 课程入口：[[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]]、[[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 术语查询：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（DFS、BFS、Path、Cycle、Frontier 等条目）。
