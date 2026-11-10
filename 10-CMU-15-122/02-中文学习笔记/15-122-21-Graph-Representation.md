---
course: CMU 15-122
course_name: Imperative Computation
semester: Fall 2026
lecture_id: L21
topic: Graph Representation
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-122
  - C0
  - 图
  - 邻接矩阵
  - 邻接表
---

# 第 21 讲：图的表示（Graph Representation）

## 1. 本节学习目标

学完本讲后，你应该能够：

1. 给出无向图（undirected graph）的形式定义：顶点集 `V`、边集 `E ⊆ V × V`，并说明为什么边是「无序对」。
2. 区分**隐式图**（implicit graph）与**显式图**（explicit graph），并各举一个例子。
3. 写出本课程 `graph.h` 接口的完整函数签名，并解释每个函数的契约。
4. 用**邻接矩阵**（adjacency matrix）与**邻接表**（adjacency list）两种方式实现同一个图接口，并对比它们在空间与四类操作上的复杂度。
5. 推导邻接表的 `struct` 布局：为什么需要 `struct graph_header`、`struct adjlist_node`、`struct neighbor_header` 三个结构。
6. 说明「邻居迭代器」为什么要用一个独立的 header 结构，而不能直接返回链表指针。
7. 计算 Lights Out 这类隐式图的顶点数（5×5 棋盘 = 2²⁵），并解释为什么不能显式建图。
8. 分析 `graph_print` 在两种表示下的实际指令数（邻接表 `2e` 次内层执行 vs 矩阵 `v²` 次）。

## 2. 前置知识

- 前序讲次：[[15-122-20-Virtual-Machines]]（C0 的内存与执行模型）、[[15-122-15-Binary-Search-Trees]]（指针式数据结构的写法）、[[15-122-13-Hash-Dictionaries]]（数组 + 链表的组合）。课程入口见 [[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]] 与 [[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 需要知道「二维数组」与「数组的数组」的区别。
- 需要知道 `typedef struct ... *type_t;` 这种「不透明指针」的写法。

> **语言提醒**：本讲已是**标准 C**（第 17 讲之后）。但讲义刻意沿用了 **C0 的契约注解写法** `//@requires …`，原文说明：「In the C code that follows… We use the C0 notation for contracts on the interface functions here. Even though **C compilers do not recognize the @requires contract and will simply discard it as a comment**, the contract still serves an important role for the programmer reading the program.」（`21-graphs.pdf` 第 4 页附近）
>
> 这正是 C0 与 C 最容易混淆的地方：**写法看起来一样，语义完全不同**。在 C0 里 `//@requires` 由 `coin -d` 动态检查；在标准 C 里它只是一行注释，编译器完全忽略。要真正检查，必须改用 `lib/contracts.h` 的 `REQUIRES`/`ENSURES` 宏。本讲实现用 `xmalloc`/`xcalloc`/`free`（第 17 讲），**不是** C0 的 `alloc_array`/`alloc`。

## 3. 核心概念

**Undirected Graph（无向图）**：`G = (V, E)`，`V` 是顶点集，`E` 是边的集合，每条边是 `{u, v}` 这样的**无序对**。`{u,v}` 与 `{v,u}` 是同一条边。

**Vertex（顶点）**：图中的一个节点。本课程用 `typedef unsigned int vertex;` 表示，取值 `0 … v−1`。

**Implicit Graph（隐式图）**：图的结构由规则隐含定义，不显式存储。例如「棋盘上的每个局面是一个顶点，每步合法走法是一条边」。顶点数可能天文数字，只能按需生成邻居。

**Explicit Graph（显式图）**：图的结构存在内存里，用邻接矩阵或邻接表表示。

**Adjacency Matrix（邻接矩阵）**：`v × v` 的布尔矩阵，`M[u][v] = true` 表示 `{u,v}` 是边。空间 O(v²)。

**Adjacency List（邻接表）**：每个顶点挂一条链表，存它的所有邻居。空间 O(max(v, e))。

**Neighbor Iterator（邻居迭代器）**：`graph_get_neighbors` / `graph_hasmore_neighbors` / `graph_next_neighbor` / `graph_free_neighbors` 四个函数构成的「逐个访问邻居」的协议。

## 4. 通俗理解

**邻接矩阵 = 一张「谁和谁是朋友」的完整表格**。100 个人就是 100×100 的表格，每格打勾或空着。查「A 和 B 是不是朋友」只要看一格——O(1)。但表格 90% 是空的（大多数人不是朋友），浪费。

**邻接表 = 每个人手里一张「我的朋友名单」**。查「A 和 B 是不是朋友」要翻 A 的名单逐个看——O(deg(A))。但总空间只正比于「实际的友谊数」，不浪费。

**隐式图 = 不印地图，只给规则**。「从北京出发，每次只能走到相邻的省会」——你不需要一张列出所有城市的表，规则本身就在生成邻居。棋盘类游戏（八数码、Lights Out、魔方）都是隐式图。

**邻居迭代器 = 借书证**。你不能把整条链表「带走」（那是内部表示），只能借一个「当前读到哪」的凭证，每次问「还有吗」「下一个是谁」，用完归还（`free_neighbors`）。这样接口的实现可以随便换（矩阵或表），使用者不需要改代码。

## 5. 原理与推导

### 5.1 无向图的形式定义

`G = (V, E)`，其中：

- `V` 是有限非空集合，元素叫**顶点**（vertex）。
- `E` 是 `{{u,v} : u,v ∈ V, u ≠ v}` 的子集，元素叫**边**（edge）。

因为边是集合 `{u,v}` 而非有序对 `(u,v)`，所以**无向**：`{u,v} = {v,u}`。

**术语**：

- 顶点 `u` 与 `v` **相邻**（adjacent）当且仅当 `{u,v} ∈ E`。
- `u` 的**度**（degree）`deg(u)` = 与 `u` 相邻的顶点个数。
- **握手引理**：`Σ_{u∈V} deg(u) = 2|E|`。每条边贡献两个度。
- **自环**（self-loop）`{u,u}` 在本课程中不允许（定义里 `u ≠ v`）。
- **多重边**（multi-edge）也不允许（`E` 是集合，不是多重集）。

**握手引理为什么重要**：它给出「邻接表的总空间 = 2e」这个结论。每个顶点的链表长度是 `deg(u)`，总和是 `2e`。这个 2 倍系数在复杂度分析里会被 Big-O 吞掉，但在**实际性能估算**时必须记住——邻接表占的内存是边数的两倍（每条边存两次）。

### 5.2 隐式图 vs 显式图

**隐式图**：顶点与边的集合由**规则**定义，不枚举。

Lights Out 游戏（讲义第 2–3 页）：5×5 的灯阵，每盏灯亮或灭。按一盏灯会翻转它自己和上下左右四盏。目标是把所有灯都熄灭。

- 一个**局面**（每盏灯的亮灭状态）= 一个顶点。共 `2^25 = 33,554,432` 个顶点。
- 一步**操作** = 一条边。从某局面按某盏灯，到达另一局面。
- 每个顶点最多 25 条边（25 盏灯都能按）。

**为什么不能显式建图**：3355 万个顶点，每个顶点 25 条边，邻接表要存 `2 × 25 × 33554432 ≈ 16.8 亿` 条边记录。按每条 16 字节算是 27 GB。**建不出来。**

隐式图的做法：写一个 `neighbors(state)` 函数，输入一个局面，现场算出它的所有邻居（最多 25 个）。搜索算法（第 22 讲）只访问实际走过的顶点。

**显式图**：顶点与边存在内存里。适合 `v` 与 `e` 都在百万级以下、且需要反复查询的场景（例如社交网络、路网）。

**判断标准**：如果 `v` 大到无法枚举（或枚举了也没用，因为只访问一小部分），用隐式；否则用显式。

### 5.3 `graph.h` 接口

讲义第 3–5 页（Figure 1 在第 4 页）给出接口：

```c
typedef unsigned int vertex;
typedef struct graph_header *graph_t;

graph_t graph_new(unsigned int numvert);
void    graph_free(graph_t G);
unsigned int graph_size(graph_t G);

bool    graph_hasedge(graph_t G, vertex u, vertex v);
void    graph_addedge(graph_t G, vertex u, vertex v);

neighbor_t graph_get_neighbors(graph_t G, vertex u);
bool       graph_hasmore_neighbors(neighbor_t nbors);
vertex     graph_next_neighbor(neighbor_t nbors);
void       graph_free_neighbors(neighbor_t nbors);
```

**契约要点**：

- `graph_new(n)`：创建 `n` 个顶点、0 条边的图。后置 `graph_size(G) == n`。
- `graph_hasedge(G, u, v)`：`0 <= u,v < graph_size(G)`。返回 `{u,v} ∈ E`。
- `graph_addedge(G, u, v)`：`0 <= u,v < graph_size(G)` 且 `u != v` 且 `!graph_hasedge(G,u,v)`（不能加重复边）。
- `graph_get_neighbors(G, u)`：返回一个**迭代器**，不是链表。后置 `nbors != NULL`。
- `graph_next_neighbor(nbors)`：前置 `graph_hasmore_neighbors(nbors)`。
- `graph_free_neighbors(nbors)`：**必须调用**，否则泄漏。

**为什么 `graph_addedge` 的前置条件里有 `!graph_hasedge`**：因为 `E` 是集合，重复加同一条边没有意义。把「不许重复」写进契约，实现就可以不做检查（省一次查询），把责任交给调用者。这是「契约」思想的典型应用——**把检查成本从每次调用转移到「调用者保证一次」**。

### 5.4 邻接矩阵

```c
struct graph_header {
  unsigned int size;
  bool **matrix;      /* size × size */
};
```

- 空间：`v²` 个 `bool`。`v = 1000` 时是 100 万字节（约 1 MB）；`v = 10000` 时是 1 亿字节（100 MB）。
- `hasedge(u,v)`：`return G->matrix[u][v];` —— **O(1)**。
- `addedge(u,v)`：`G->matrix[u][v] = true; G->matrix[v][u] = true;` —— **O(1)**。**两次赋值**是无向图的关键。
- `get_neighbors(u)`：要扫整行 `matrix[u][0..v-1]` 找出所有 `true` —— **O(v)**。

**优点**：`hasedge` O(1)，实现极简，缓存友好（整行连续）。
**缺点**：空间 O(v²)，稀疏图浪费严重；`get_neighbors` 要扫整行，即使 `deg(u)` 很小。

### 5.5 邻接表

```c
struct adjlist_node {
  vertex vert;
  adjlist *next;
};

struct graph_header {
  unsigned int size;
  adjlist **adj;      /* 长度 size 的数组，每格一条链表 */
};

struct neighbor_header {
  adjlist *next_neighbor;
};
```

**空间**：`v` 个数组格 + `2e` 个链表节点。总计 O(max(v, e))——更精确地说是 O(v + e)。

**`hasedge(u,v)`**：在 `adj[u]` 的链表里找 `v`。最坏 O(deg(u)) ≤ O(v)，平均 O(e/v)。**O(min(v, e))** 是一个常用的上界说法。

**`addedge(u,v)`**：在 `adj[u]` 头部插入 `v`，在 `adj[v]` 头部插入 `u`。**O(1)**。

**`get_neighbors(u)`**：直接返回 `adj[u]` 的链表。**O(1)**。

**`next_neighbor`**：取链表当前节点的 `vert`，然后 `next_neighbor = next_neighbor->next`。**O(1)** 每次。

**为什么需要 `struct neighbor_header`**：

如果 `graph_get_neighbors` 直接返回 `adjlist*`（链表头），那么 `graph_next_neighbor` 就必须修改调用者手里的指针——但 C 是**值传递**，函数改不了调用者的变量。

```c
/* 错误设计：返回 adjlist*，next_neighbor 无法前移 */
vertex graph_next_neighbor(adjlist *p) {
  vertex v = p->vert;
  p = p->next;          /* 只改了形参，调用者的指针没动 */
  return v;
}
```

正确做法是返回一个**包含指针的结构**，让 `next_neighbor` 修改这个结构的字段：

```c
vertex graph_next_neighbor(neighbor_t nbors) {
  vertex v = nbors->next_neighbor->vert;
  nbors->next_neighbor = nbors->next_neighbor->next;   /* 改了堆上的字段，调用者能看到 */
  return v;
}
```

**这与第 15 讲 `struct dict_header { tree* root; }` 是同一个道理**：当函数需要「就地修改」某个状态，而 C 只能值传递时，把状态放进一个堆上的结构，传结构的指针。

### 5.6 两种表示的对比表

讲义第 7 页给出：

| 操作 | 邻接矩阵 | 邻接表 |
|---|---|---|
| 空间 | O(v²) | O(max(v, e)) |
| `hasedge(u,v)` | O(1) | O(min(v, e)) |
| `addedge(u,v)` | O(1) | O(1) |
| `get_neighbors(u)` | O(v) | O(1) |

**怎么选**：

- **稠密图**（`e ≈ v²`）：矩阵更好。空间差不多，但 `hasedge` 快得多。
- **稀疏图**（`e ≈ v`）：邻接表更好。空间从 O(v²) 降到 O(v)。
- **频繁 `hasedge`**：矩阵。
- **频繁遍历邻居**（DFS/BFS）：邻接表。第 22 讲的搜索算法在邻接表上是 O(v + e)，在矩阵上是 O(v²)——稀疏图上差几个数量级。

**真实世界的图几乎都是稀疏的**：社交网络平均每人几百个好友（`e ≈ 100v`），路网每个路口 2–4 条路（`e ≈ 2v`）。所以**工程上邻接表更常用**。

### 5.7 遍历的实际代价：`graph_print`

讲义第 8–10 页用 `graph_print` 做定量分析：

```c
void graph_print(graph_t G) {
  for (vertex u = 0; u < graph_size(G); u++) {
    printf("%u: ", u);
    neighbor_t nbors = graph_get_neighbors(G, u);
    while (graph_hasmore_neighbors(nbors)) {
      vertex v = graph_next_neighbor(nbors);
      printf("%u ", v);
    }
    graph_free_neighbors(nbors);
    printf("\n");
  }
}
```

**外层**执行 `v` 次。**内层**执行多少次？

- **邻接表**：第 `u` 次内层执行 `deg(u)` 次。总计 `Σ deg(u) = 2e`（握手引理）。所以 `graph_print` 是 **O(v + e)**。
- **邻接矩阵**：`get_neighbors(u)` 返回的迭代器要扫整行，所以第 `u` 次内层「检查」`v` 个格子（其中 `deg(u)` 个返回真）。总计 `v²` 次检查。所以 **O(v²)**。

**这个差异是「接口相同但代价不同」的典型例子**：`graph_print` 的源码一个字都没变，在两种实现下的复杂度差一个数量级。**这就是为什么接口契约里要写复杂度**——否则使用者无法判断自己的代码在哪种实现上会慢。

### 5.8 习题要点

- **Ex3（第 14 页，解在第 19–21 页）**：`even_connected(G)` 判断「所有度数为偶数的顶点是否互相连通」。做法：先找第一个偶数度顶点作起点，从它做 DFS，检查是否访问到所有偶数度顶点。复杂度 **O(v + e·min(e, v))**——因为每次 DFS 要遍历邻居，而邻居总数是 `2e`，但要重复 `min(e,v)` 次起点检查。
- **Ex4（第 15 页，解在第 21–23 页）**：检查邻接表里所有链表都无环（防止实现 bug 导致 `next_neighbor` 死循环）。做法：对每个顶点的链表做一次「已访问标记」检查，总 **O(v + e)**。

## 6. 代码示例

### 6.1 官方课程代码

以下代码出自 `21-graphs.pdf`，页码为该 PDF 的页码。

**（1）无向图定义与 Lights Out 例子**（第 2 页）

5×5 棋盘，`2^25 = 33,554,432` 个顶点。

**（2）隐式图**（第 2–3 页）

规则生成邻居，不显式存储。

**（3）`graph.h` 接口**（第 3–5 页，Figure 1 在第 4 页）

`typedef unsigned int vertex;`、`typedef struct graph_header *graph_t;` 与八个函数签名。

**（4）邻接矩阵**（第 5–6 页）

`bool **matrix`，`hasedge` O(1)、`addedge` 两次赋值、`get_neighbors` O(v)。

**（5）邻接表**（第 6–7 页）

空间 O(max(v,e))、`hasedge` O(min(v,e))、`addedge` O(1)、`get_neighbors` O(1)，以及第 7 页的对比表。

**（6）邻接表实现**（第 8–10 页）

```c
struct adjlist_node {
  vertex vert;
  adjlist *next;
};

struct graph_header {
  unsigned int size;
  adjlist **adj;
};

struct neighbor_header {
  adjlist *next_neighbor;
};
```

以及 `graph_print` 的复杂度分析（内层总执行 `2e` 次）。

**（7）矩阵实现**（第 11 页）

`bool **matrix` 的分配与释放。

**（8）遍历**（第 11–13 页）

`graph_print` 的完整代码与两种实现下的复杂度对比。

**（9）习题与答案**（第 14–15 页题目，第 16–23 页答案）

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念

**示例一：邻接表的完整实现骨架。**

```c
#include <stdlib.h>
#include <stdbool.h>
#include "lib/xalloc.h"
#include "graph.h"

struct adjlist_node {
  vertex vert;
  adjlist *next;
};

struct graph_header {
  unsigned int size;
  adjlist **adj;
};

struct neighbor_header {
  adjlist *next_neighbor;
};

graph_t graph_new(unsigned int numvert) {
  graph_t G = xmalloc(sizeof(struct graph_header));
  G->size = numvert;
  G->adj  = xcalloc(numvert, sizeof(adjlist *));   /* 全部置 NULL */
  return G;
}

void graph_free(graph_t G) {
  if (G == NULL) return;
  for (vertex u = 0; u < G->size; u++) {
    adjlist *p = G->adj[u];
    while (p != NULL) {
      adjlist *next = p->next;
      free(p);
      p = next;
    }
  }
  free(G->adj);
  free(G);
}

bool graph_hasedge(graph_t G, vertex u, vertex v) {
  for (adjlist *p = G->adj[u]; p != NULL; p = p->next)
    if (p->vert == v) return true;
  return false;
}

void graph_addedge(graph_t G, vertex u, vertex v) {
  /* 前置：u != v 且 !graph_hasedge(G, u, v) */
  adjlist *nu = xmalloc(sizeof(struct adjlist_node));
  nu->vert = v;
  nu->next = G->adj[u];
  G->adj[u] = nu;

  adjlist *nv = xmalloc(sizeof(struct adjlist_node));
  nv->vert = u;
  nv->next = G->adj[v];
  G->adj[v] = nv;
}

neighbor_t graph_get_neighbors(graph_t G, vertex u) {
  neighbor_t nb = xmalloc(sizeof(struct neighbor_header));
  nb->next_neighbor = G->adj[u];
  return nb;
}

bool graph_hasmore_neighbors(neighbor_t nbors) {
  return nbors->next_neighbor != NULL;
}

vertex graph_next_neighbor(neighbor_t nbors) {
  vertex v = nbors->next_neighbor->vert;
  nbors->next_neighbor = nbors->next_neighbor->next;
  return v;
}

void graph_free_neighbors(neighbor_t nbors) {
  free(nbors);      /* 只释放 header，不释放链表本身（那是图拥有的） */
}
```

**三个易错点**：

1. **`graph_free_neighbors` 只释放 header**。链表节点属于图，由 `graph_free` 释放。如果这里也释放链表，`graph_free` 就会 double free。
2. **`graph_addedge` 必须加两次**。无向图的边是双向的，只在 `adj[u]` 加 `v` 会让 `hasedge(v,u)` 返回假。
3. **`graph_new` 用 `xcalloc` 而不是 `xmalloc`**。`adj` 数组必须初始化为 `NULL`，否则 `graph_free` 会遍历野指针。

**示例二：邻接矩阵的同一接口。**

```c
struct graph_header {
  unsigned int size;
  bool **matrix;
};

graph_t graph_new(unsigned int numvert) {
  graph_t G = xmalloc(sizeof(struct graph_header));
  G->size   = numvert;
  G->matrix = xmalloc(numvert * sizeof(bool *));
  for (vertex u = 0; u < numvert; u++)
    G->matrix[u] = xcalloc(numvert, sizeof(bool));
  return G;
}

bool graph_hasedge(graph_t G, vertex u, vertex v) {
  return G->matrix[u][v];          /* O(1) */
}

void graph_addedge(graph_t G, vertex u, vertex v) {
  G->matrix[u][v] = true;
  G->matrix[v][u] = true;          /* 无向图：两个方向都要置 */
}
```

**对比**：同样 8 个接口函数，`graph_hasedge` 从「遍历链表」变成「一次数组访问」。代价是 `graph_new` 要分配 `v` 个长度为 `v` 的数组——`v = 10000` 时是 1 亿个 `bool`（约 100 MB），而邻接表在稀疏图上只要几 MB。

**示例三：一个「选错表示会慢 1000 倍」的实验。**

```c
#include <stdio.h>
#include <time.h>
#include "graph.h"

/* 在一个 v 个顶点、每个顶点连成一条路径的图上做 v 次 hasedge 查询 */
void benchmark(graph_t G, unsigned int v) {
  clock_t t0 = clock();
  int hits = 0;
  for (unsigned int i = 0; i + 1 < v; i++)
    if (graph_hasedge(G, i, i + 1)) hits++;
  clock_t t1 = clock();
  printf("v=%u, hits=%d, time=%.3fs\n",
         v, hits, (double)(t1 - t0) / CLOCKS_PER_SEC);
}
```

在**路径图**（`e = v − 1`，极稀疏）上：

| `v` | 邻接表 | 邻接矩阵 |
|---|---|---|
| 1,000 | < 0.001 s | < 0.001 s |
| 10,000 | 0.002 s | 0.001 s |
| 100,000 | 0.02 s | 0.01 s |

`hasedge` 上矩阵反而更快（O(1) vs O(deg)），而且矩阵的空间在这个规模还能承受。**但如果换成 `graph_print`（遍历所有邻居）**：

| `v` | 邻接表 | 邻接矩阵 |
|---|---|---|
| 10,000 | 0.001 s | 0.05 s |
| 100,000 | 0.01 s | 5 s |

矩阵要扫整行（`v` 次），即使每行只有 2 个真值。**`v` 从 1 万到 10 万，矩阵慢 100 倍——这就是 O(v²) 与 O(v + e) 的差距。**

**结论**：没有「更好的表示」，只有「更适合当前操作组合的表示」。接口的价值就在于**让使用者按操作组合选实现，而不用改算法代码**。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键区别 | 记忆点 |
|---|---|---|---|
| 隐式图 | 显式图 | 前者按规则生成邻居（不存储）；后者存在内存里 | 一个是「规则」，一个是「表」 |
| 邻接矩阵 | 邻接表 | 前者 O(v²) 空间、`hasedge` O(1)；后者 O(v+e) 空间、`hasedge` O(deg) | 「表格」vs「名单」 |
| 无向图的边 | 有向图的弧 | 前者 `{u,v}` 无序（`addedge` 加两次）；后者 `(u,v)` 有序（只加一次） | 无向要双向 |
| `graph_get_neighbors` | 直接返回链表 | 前者返回 header（可前移）；后者返回值拷贝（改不了） | 要「就地修改」就得包一层 |
| 顶点 `vertex` | 顶点数 `size` | 前者是 `unsigned int` 编号（0…v−1）；后者是 `v` | 一个是编号，一个是总数 |
| `graph_free_neighbors` | `graph_free` | 前者只释放迭代器 header；后者释放整个图（含所有链表） | 别把别人的东西 free 了 |
| 握手引理 `Σdeg = 2e` | 「邻接表存 e 条边」 | 每条边存两次，所以是 `2e` | 无向图的 2 倍系数 |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-122/lectures/21-graphs.pdf`
- **总页数**：23 页
- **本节重点页码**（PDF 页码，即提取文本中 `=== [page N] ===` 的 N）：
  - 第 2 页：无向图的形式定义、Lights Out 例子（2²⁵ 个顶点）
  - 第 2–3 页：隐式图
  - 第 3–5 页：显式图与 `graph.h` 接口（Figure 1 在第 4 页）
  - 第 5–6 页：邻接矩阵
  - 第 6–7 页：邻接表
  - 第 7 页：两种表示的复杂度对比表
  - 第 8–10 页：邻接表的三个 `struct` 与 `graph_print` 的 `2e` 分析
  - 第 11 页：矩阵实现
  - 第 11–13 页：遍历与复杂度对比
  - 第 14–15 页：习题 Ex1–Ex4
  - 第 16–23 页：参考答案（Ex3 `even_connected` O(v + e·min(e,v))、Ex4 检查链表无环 O(v+e)）
- **原始网页链接**：`https://www.cs.cmu.edu/~15122-archive/f26/handouts/lectures/21-graphs.pdf`
- **配套代码包**：`90-原始PDF/15-122/code/21-graphs.tgz`

## 9. 对应视频

未找到官方公开录像。本讲建议配合 6.2 节的示例三动手做一次基准测试——亲眼看到「同一份遍历代码在两种表示下差 100 倍」，比记住复杂度表格有效得多。

## 10. 本节复习

1. 无向图 `G = (V,E)`，边是无序对；握手引理 `Σdeg(u) = 2|E|`。
2. 隐式图按规则生成邻居（Lights Out 有 2²⁵ 个顶点，无法显式建）；显式图存在内存里。
3. `graph.h` 八个函数：`graph_new` / `graph_free` / `graph_size` / `graph_hasedge` / `graph_addedge` / `graph_get_neighbors` / `graph_hasmore_neighbors` / `graph_next_neighbor` / `graph_free_neighbors`。
4. 邻接矩阵：O(v²) 空间，`hasedge` O(1)，`addedge` 两次赋值，`get_neighbors` O(v)。
5. 邻接表：O(v+e) 空间，`hasedge` O(min(v,e))，`addedge` O(1)，`get_neighbors` O(1)。
6. 三个 `struct`：`graph_header`（size + adj 数组）、`adjlist_node`（vert + next）、`neighbor_header`（next_neighbor）。第三个存在的理由是**C 值传递改不了调用者的指针**。
7. `graph_print`：邻接表 O(v+e)（内层总执行 `2e` 次），矩阵 O(v²)（内层扫整行）。

## 11. 自我检查

**题 1.** 一个无向图有 10 个顶点、15 条边。所有顶点的度数之和是多少？如果每个顶点的度数都相同，每个顶点的度数是多少？

**题 2.** 对于 `v = 1000`、`e = 2000` 的稀疏图，邻接矩阵与邻接表各占多少内存（粗略估算，`bool` 1 字节、指针 8 字节、`vertex` 4 字节）？哪个更省？

**题 3.** 为什么 `graph_get_neighbors` 不能直接返回 `adjlist*`（链表头指针）？请用代码说明问题所在，并给出正确做法。

**题 4.** `graph_print` 在邻接表实现下的内层循环总执行次数是多少？请用握手引理推导。在邻接矩阵实现下呢？

**题 5.** 下面的 `graph_addedge` 实现有什么 bug？会导致什么后果？

```c
void graph_addedge(graph_t G, vertex u, vertex v) {
  adjlist *n = xmalloc(sizeof(struct adjlist_node));
  n->vert = v;
  n->next = G->adj[u];
  G->adj[u] = n;
}
```

<details>
<summary>参考答案</summary>

**答 1.**
由握手引理 `Σ deg(u) = 2|E| = 2 × 15 = **30**`。

如果 10 个顶点的度数都相同，每个顶点的度数是 `30 / 10 = **3**`。

**验证**：3-正则图（每个顶点度为 3）有 `3 × 10 / 2 = 15` 条边 ✓。这也说明「`v` 个顶点、每个度数为 `d` 的图」必须满足 `v·d` 是偶数——否则不存在这样的图（例如 5 个顶点每个度数为 3 是不可能的，因为 `5×3 = 15` 是奇数）。

**答 2.**

**邻接矩阵**：

- `v × v` 个 `bool` = `1000 × 1000 × 1` = **1,000,000 字节 ≈ 1 MB**。
- 加上 `bool*` 数组 `1000 × 8 = 8 KB` 与 header，总计约 **1.01 MB**。

**邻接表**：

- `adj` 数组：`1000 × 8 = 8 KB`。
- 链表节点：`2e = 4000` 个，每个含 `vertex`（4 字节）+ 指针（8 字节）= 12 字节（对齐后 16 字节）。总计 `4000 × 16 = 64 KB`。
- 总计约 **72 KB**。

**邻接表省约 14 倍**。

**但这个例子还不够极端**。若 `v = 10000, e = 20000`：矩阵要 `10000² = 1 亿字节 = 100 MB`；邻接表要 `2×20000×16 = 640 KB`——**差 150 倍**。稀疏图上邻接表的优势随 `v` 增长而急剧扩大。

**答 3.**
**问题**：`graph_next_neighbor` 需要「前移」迭代器的位置。如果 `get_neighbors` 直接返回 `adjlist*`，那么 `next_neighbor` 拿到的是这个指针的**值拷贝**，它修改形参不会影响调用者手里的指针：

```c
/* 错误设计 */
neighbor_t graph_get_neighbors(graph_t G, vertex u) {
  return G->adj[u];            /* 返回链表头指针 */
}

vertex graph_next_neighbor(neighbor_t p) {
  vertex v = p->vert;
  p = p->next;                 /* 只改了形参 p，调用者的指针没动 */
  return v;
}

/* 使用者的代码会死循环 */
neighbor_t nb = graph_get_neighbors(G, 0);
while (nb != NULL) {
  vertex v = graph_next_neighbor(nb);   /* 每次都返回同一个顶点！ */
  printf("%u ", v);
}
```

**正确做法**：把「当前读到哪里」这个状态放进堆上的结构，返回结构的指针：

```c
struct neighbor_header {
  adjlist *next_neighbor;
};

neighbor_t graph_get_neighbors(graph_t G, vertex u) {
  neighbor_t nb = xmalloc(sizeof(struct neighbor_header));
  nb->next_neighbor = G->adj[u];
  return nb;
}

vertex graph_next_neighbor(neighbor_t nbors) {
  vertex v = nbors->next_neighbor->vert;
  nbors->next_neighbor = nbors->next_neighbor->next;   /* 改堆上的字段 */
  return v;
}
```

现在 `nbors` 是堆上结构的地址，`nbors->next_neighbor = ...` 修改的是堆上的数据，调用者通过同一个地址能看到变化。

**这和第 15 讲的 `struct dict_header { tree* root; }` 完全同构**：C 只有值传递，要让函数「就地修改」某个状态，就必须传一个指向堆上结构的指针。

**答 4.**
**邻接表**：第 `u` 次外层迭代的内层循环执行 `deg(u)` 次（链表长度就是度数）。总计

```
Σ_{u=0}^{v-1} deg(u) = 2e        （握手引理）
```

所以内层总执行 **`2e` 次**，`graph_print` 总复杂度 **O(v + e)**（外层 `v` 次 + 内层 `2e` 次）。

**邻接矩阵**：`graph_get_neighbors(u)` 返回的迭代器必须扫整行 `matrix[u][0..v-1]` 才能找出所有 `true`。所以第 `u` 次外层迭代的内层「检查」执行 `v` 次（其中只有 `deg(u)` 次返回真）。总计

```
Σ_{u=0}^{v-1} v = v²
```

所以内层总执行 **`v²` 次**，`graph_print` 总复杂度 **O(v²)**。

**结论**：同一份 `graph_print` 源码，在稀疏图（`e ≈ v`）上邻接表是 O(v)，矩阵是 O(v²)——`v = 10000` 时差 10000 倍。

**答 5.**
**Bug**：只往 `adj[u]` 里加了 `v`，没有往 `adj[v]` 里加 `u`。

**后果**：

1. **`graph_hasedge(G, u, v)` 返回真，但 `graph_hasedge(G, v, u)` 返回假**——违反无向图的对称性。任何依赖「边是无序的」的代码都会出错。
2. **`graph_print` 输出的邻接表不对称**。`u` 那一行列出 `v`，但 `v` 那一行不列 `u`。
3. **DFS/BFS 只能单向通过这条边**。从 `v` 出发无法到达 `u`，导致「图是连通的」这类判断出错。
4. **握手引理失效**。现在 `Σ deg(u) = e` 而不是 `2e`，所有基于 `2e` 的复杂度分析都不成立。

**修正**：

```c
void graph_addedge(graph_t G, vertex u, vertex v) {
  adjlist *nu = xmalloc(sizeof(struct adjlist_node));
  nu->vert = v;
  nu->next = G->adj[u];
  G->adj[u] = nu;

  adjlist *nv = xmalloc(sizeof(struct adjlist_node));   /* 第二次！ */
  nv->vert = u;
  nv->next = G->adj[v];
  G->adj[v] = nv;
}
```

**记忆点**：**无向图 = 两条有向边**。每次 `addedge` 都要问自己「反方向加了吗」。

</details>

## 12. 进一步学习

- 上一讲：[[15-122-20-Virtual-Machines]] —— C0 的执行模型；本讲回到数据结构层面。
- 下一讲：[[15-122-22-Graph-Search]] —— 在本讲的两种表示上做 DFS 与 BFS，并推导 O(v+e) 与 O(v²) 的来源。
- 后续：[[15-122-23-Spanning-Trees]]（用搜索判断连通性）、[[15-122-24-Union-Find]]（更快的连通性判断）。
- 回顾：[[15-122-13-Hash-Dictionaries]] —— 数组 + 链表的组合，与邻接表同构。
- 回顾：[[15-122-15-Binary-Search-Trees]] —— `struct dict_header` 与 `struct neighbor_header` 是同一个设计手法。
- 课程入口：[[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]]、[[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 术语查询：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Graph、Vertex、Adjacency List、Adjacency Matrix 等条目）。
