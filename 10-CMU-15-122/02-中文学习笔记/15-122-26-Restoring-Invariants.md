---
course: CMU 15-122
course_name: Imperative Computation
semester: Fall 2026
lecture_id: L26
topic: Restoring Invariants
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-122
  - 标准C
  - 堆
  - 优先队列
  - 不变量
  - 循环不变式
---

# 第 26 讲：恢复不变量（Restoring Invariants）

## 1. 本节学习目标

学完本讲后，你应该能够：

1. 用**标准 C**（不是 C0）写出一个完整的、有界的最小堆（min-heap），包括 `struct heap_header` 的变长数组成员 `elem[] data`。
2. 说明「部分不变式」（partial invariant）的含义，并写出 `is_heap_except_up` / `is_heap_except_down` 这两个谓词。
3. **解释为什么「除 x 外所有父子对都有序」这个朴素的部分不变式不够强**——并给出反例，说明交换后无法证明 `b ≤ c₁`、`b ≤ c₂`。
4. 写出**加强后的不变式** `grandparent_check`（祖父母检查），并说明它如何补上缺口。
5. 完整推导 `pq_add`（sift up）与 `pq_rem`（sift down）的正确性证明，包括循环不变式与退出时的论证。
6. 说明「临时违反不变式 → 局部修复」这一通用模式，并指出它在哪些其他算法中出现。
7. 分析 heapsort 的复杂度，并说明为什么它的辅助空间可以做到 O(1)。

## 2. 前置知识

- 上一讲：[[15-122-25-Priority-Queues]] —— 优先队列接口、堆的两条不变式、sift up / sift down 的直觉。
- [[15-122-17-Introduction-to-C]] —— 从 C0 转到标准 C 的分界点；`lib/contracts.h` 的 ASSERT/REQUIRES/ENSURES；`xmalloc`/`xcalloc`。
- [[15-122-18-C-Memory-Model]] —— 五段内存布局、`sizeof`、指针算术。
- [[15-122-19-Types-in-C]] —— `size_t`、有符号/无符号、`int_max()`。
- [[15-122-01-Contracts]] —— 契约、前置/后置条件、循环不变式的基本写法。
- 课程入口：[[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]]、[[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。

> **语言提醒**：本讲是**标准 C**，不是 C0。三处具体差异必须注意：
> 1. **契约只是注释**。`/*@requires ... @*/` 在标准 C 里不会被检查，必须靠 `lib/contracts.h` 的 `REQUIRES(...)` / `ENSURES(...)` / `ASSERT(...)` 宏（编译时加 `-DDEBUG`）才真正生效。
> 2. **变长数组成员** `elem[] data` 是 C99 的灵活数组成员（flexible array member），C0 不支持。
> 3. **内存管理**：`xmalloc` / `xcalloc` / `free`，并用 valgrind 检查泄漏。C0 有垃圾回收，C 没有。

## 3. 核心概念

**Partial Invariant（部分不变式）**：一个比完整不变式**弱**的谓词，它允许「某个特定位置」违反不变式，其余位置都满足。

**`is_heap_except_up(H, x)`**：除「`x` 与其父」这一对之外，所有父子对都满足有序不变式。

**`is_heap_except_down(H, x)`**：除「`x` 与其孩子」这些对之外，所有父子对都满足有序不变式。

**`grandparent_check(H, i)`**：`i` 的两个孩子（如果存在）的优先级都不低于 `i` 的父。**这是补强部分不变式的关键条件。**

**Restoring an Invariant（恢复不变量）**：先**故意**破坏不变式（例如把新元素放到末尾、把末尾元素提到根），然后用一个**只沿一条路径**的局部操作（sift up / sift down）把不变式修回来。

**Flexible Array Member（灵活数组成员）**：`struct` 的最后一个成员写成 `elem data[]`，长度在运行时决定，随 `xmalloc` 的字节数一起分配。

**Heapsort（堆排序）**：把所有元素插入堆，再逐个删除最小，得到升序序列。O(n log n)。

## 4. 通俗理解

**「恢复不变量」= 先把书架上的一本书抽出来，再插回正确的位置。**

你不可能「一边保持整齐一边插书」——插书这个动作本身就要求你先把书拿在手里（此时书架不整齐），插好之后才恢复整齐。**关键是：不整齐的状态只持续一瞬间，而且只影响一个位置。**

**部分不变式的价值 = 精确描述「哪儿乱了」。**

如果只说「书架乱了」，你没法证明「插回去之后会整齐」。你必须说清楚：「**除了第 3 层第 5 本，其他都是有序的**」。这样你才能论证：「我把这本插到第 3 层第 2 本的位置，交换之后，第 3 层第 5 本也归位了，于是全部有序」。

**本讲最精彩的部分 = 发现「除 x 外都整齐」这句话不够精确。**

假设书架除了第 5 本之外都整齐。你把第 5 本和第 2 本（它的父位置）交换。交换之后，第 2 本位置上是原来的第 5 本（更小），第 5 本位置上是原来的第 2 本（更大）。

**问题**：第 5 本位置上的书（原来的第 2 本）比它**下面**的两本书（第 10、11 本）小吗？

原来的不变式只说「第 2 本 ≤ 第 5 本」和「第 2 本 ≤ 第 6 本」，**没说「第 2 本 ≤ 第 10、11 本」**。所以交换后无法证明第 5 本位置上的书 ≤ 它下面的书。

**解决方式**：**加强假设**。除了「除第 5 本外都整齐」，还要加上「**第 5 本下面的两本书，都不小于第 2 本**」。这个额外条件就是 `grandparent_check`——**祖父母检查**：孩子 ≥ 父的父。

**加上这条之后，交换就能证明正确了**：原来的第 2 本 ≤ 第 10、11 本（由新假设），所以交换后第 5 本位置上的书 ≤ 它下面的书 ✓。

**这个「发现假设不够强、然后加强它」的过程，是形式化验证中最有教育意义的时刻。** 讲义第 7–9 页专门用了一整节讲这个。

## 5. 原理与推导

### 5.1 堆的数据结构（标准 C）

讲义第 2 页：

```c
struct heap_header {
  int limit;                        /* limit = capacity + 1 */
  int next;                         /* 1 <= next && next <= limit */
  elem[] data;                      /* \length(data) == limit */
  has_higher_priority_fn *prior;    /* != NULL */
};
```

**四个字段逐一解释**：

- **`limit`**：数组的总长度，等于 `capacity + 1`。**为什么 +1**：下标 0 不用（第 25 讲），所以 `capacity` 个元素需要 `capacity + 1` 格。
- **`next`**：**下一个空位**的下标。有效元素在 `data[1 … next−1]`，共 `next − 1` 个。`next == 1` 表示空堆，`next == limit` 表示满堆。
- **`elem[] data`**：**灵活数组成员**。它必须是 `struct` 的**最后一个**成员，且不写长度。分配时用 `xmalloc(sizeof(struct heap_header) + limit * sizeof(elem))`，一次分配把 header 和数组连在一起。
- **`prior`**：比较函数指针（第 25 讲的 `has_higher_priority_fn`）。**必须非 NULL**——否则 `pq_add` 会解引用空指针。

**为什么用灵活数组成员而不是 `elem *data`**：

| 方案 | 分配次数 | 释放次数 | 缓存局部性 |
|---|---|---|---|
| `elem *data`（分开分配） | 2 次 `xmalloc` | 2 次 `free` | 差（两块内存可能相距很远） |
| `elem[] data`（灵活数组） | **1 次 `xmalloc`** | **1 次 `free`** | **好**（header 与数据连续） |

**代价**：`sizeof(struct heap_header)` 不包含数组部分，所以**必须手动算总字节数**：

```c
heap pq_new(int capacity, has_higher_priority_fn *prior) {
  heap H = xmalloc(sizeof(struct heap_header) + (capacity + 1) * sizeof(elem));
  H->limit = capacity + 1;
  H->next  = 1;
  H->prior = prior;
  return H;
}
```

**这是标准 C 的惯用法，也是本讲相对第 25 讲的第一个实质升级。**

### 5.2 `is_heap_safe`：安全检查

讲义第 3 页：

```c
bool is_heap_safe(heap H) {
  return H != NULL
      && (1 < H->limit && H->limit <= int_max() / 2)
      && is_array_expected_length(H->data, H->limit)
      && (1 <= H->next && H->next <= H->limit)
      && H->prior != NULL;
}
```

**五个条件逐一解释**：

1. **`H != NULL`**：不能是空指针。
2. **`1 < H->limit`**：`limit = capacity + 1`，所以 `limit > 1` 意味着 `capacity > 0`。**空容量的堆没有意义**（连一个元素都放不下）。
3. **`H->limit <= int_max() / 2`**：防止 `(capacity + 1) * sizeof(elem)` 溢出 `int`。`int_max()` 是 `lib/contracts.h` 提供的 `INT_MAX` 包装。**除以 2 是保守估计**——如果 `elem` 是 `void*`（8 字节），`limit * 8` 在 `limit > INT_MAX/8` 时就会溢出。讲义用 `/2` 是一个简单但足够安全的上界。
4. **`is_array_expected_length(H->data, H->limit)`**：数组的实际长度确实是 `limit`。这个谓词在 `lib/contracts.h` 里，通过 `malloc_usable_size` 之类的机制检查。
5. **`1 <= H->next && H->next <= H->limit`**：`next` 在合法范围内。`next == 1` 空堆，`next == limit` 满堆。
6. **`H->prior != NULL`**：比较函数存在。

**为什么叫 `safe` 而不是 `is_heap`**：它只检查「**结构上不会崩溃**」，不检查「有序性」。**这是两件事**——`safe` 是「能安全访问」，`ordered` 是「语义正确」。分开写让检查更模块化，也让「部分不变式」的表述更精确。

### 5.3 有序不变式与 `ok_above`

讲义第 4 页：

```c
/* ok_above(H, i1, i2): data[i1] 的优先级不低于 data[i2] */
bool ok_above(heap H, int i1, int i2) {
  elem e1 = H->data[i1];
  elem e2 = H->data[i2];
  return !(*H->prior)(e2, e1);
}
```

**为什么是 `!prior(e2, e1)` 而不是 `prior(e1, e2)`**：

`prior(e2, e1)` 问「`e2` 是否**严格**高于 `e1`」。

- 若为真：`e2` 严格高于 `e1`，即 `e1` 的优先级**低于** `e2`。所以 `ok_above` 返回 `false` ✓。
- 若为假：`e2` 不严格高于 `e1`，即 `e1` 的优先级 **≥** `e2`。所以 `ok_above` 返回 `true` ✓。

**`ok_above` 是「非严格」的**（`≥`），而 `prior` 是「严格」的（`>`）。**这个非严格性正是 sift up / sift down 终止的原因**——相等元素之间不交换。

**`is_heap_ordered`**：

```c
bool is_heap_ordered(heap H) {
  for (int child = 2; child < H->next; child++) {
    if (!ok_above(H, child / 2, child)) return false;
  }
  return true;
}
```

**从 `child = 2` 开始**：位置 1 是根，没有父。位置 2 是第一个有父的节点。

**循环到 `child < H->next`**：有效元素下标最大是 `next − 1`，所以 `child` 最大取 `next − 1`。

**复杂度 O(n)**：遍历所有非根节点，每个 O(1)。

**完整不变式**：

```c
bool is_heap(heap H) {
  return is_heap_safe(H) && is_heap_ordered(H);
}
```

### 5.4 空堆与满堆

讲义第 4–5 页：

```c
bool pq_empty(heap H) { return H->next == 1; }
bool pq_full(heap H)  { return H->next == H->limit; }
```

**`pq_empty`**：`next == 1` 表示没有元素（有效范围 `data[1 … 0]` 是空的）。

**`pq_full`**：`next == limit` 表示下一个空位已经越界。**注意 `limit = capacity + 1`**，所以 `next == limit` 时有效元素有 `limit − 1 = capacity` 个——**正好装满**。

**这两个谓词的简洁性来自「`next` 始终指向下一个空位」这个约定**。如果 `next` 指向最后一个元素（而不是下一个空位），公式就要写成 `next == 0` 和 `next == capacity`，边界判断容易出错。**「指向下一个空位」是一个好的表示选择。**

### 5.5 `pq_add` 与 sift up

讲义第 5–11 页。核心循环：

```c
void pq_add(heap H, elem e)
/*@requires is_heap(H) && !pq_full(H); @*/
/*@ensures is_heap(H); @*/
{
  int i = H->next - 1;
  while (i > 1 && !ok_above(H, i / 2, i))
  /*@loop_invariant 1 <= i && i < H->next; @*/
  /*@loop_invariant is_heap_except_up(H, i); @*/
  /*@loop_invariant grandparent_check(H, i); @*/
  {
    swap_up(H, i);
    i = i / 2;
  }
}
```

**等一下——这里 `i = H->next - 1` 看起来不对。** 让我仔细看讲义的写法。

**讲义第 5–6 页的 `pq_add`**：先 `H->data[H->next] = e;`（把元素放到下一个空位），然后 `H->next++`（空位前移），然后 sift up。所以 sift up 时新元素在位置 `H->next - 1`（因为 `next` 已经加过了）。

**这个顺序很重要**：

```
1. 检查 !pq_full(H)
2. H->data[H->next] = e;      // 放到空位
3. H->next++;                 // 空位前移
4. sift up 位置 H->next - 1   // 就是刚放元素的位置
```

**这样写的好处**：sift up 期间 `H->next` 已经包含了新元素，所以 `is_heap_except_up` 检查的范围是对的（`1 <= j < H->next`）。

**`swap_up`**：

```c
void swap_up(heap H, int child)
/*@requires 2 <= child && child < H->next; @*/
/*@requires !ok_above(H, child / 2, child); @*/
/*@ensures ok_above(H, child / 2, child); @*/
{
  elem tmp = H->data[child];
  H->data[child] = H->data[child / 2];
  H->data[child / 2] = tmp;
}
```

**前置条件三条**：

- `2 <= child`：不是根（有父）。
- `child < H->next`：在有效范围内。
- `!ok_above(H, child/2, child)`：**当前违反不变式**（孩子的优先级严格更高）。

**后置条件**：交换后，父（新的是原来的孩子）的优先级不低于孩子（新的是原来的父）✓。

**注意 `swap_up` 的前置条件里就有「违反」**——这看起来奇怪，但正是「恢复不变量」模式的体现：**这个函数专门用来修一个已知的违规**。如果前置条件不满足（已经有序），调用它就是逻辑错误。

### 5.6 朴素的部分不变式：`is_heap_except_up`

讲义第 7 页：

```c
bool is_heap_except_up(heap H, int x) {
  for (int child = 2; child < H->next; child++) {
    if (!(child == x || ok_above(H, child / 2, child)))
      return false;
  }
  return true;
}
```

**读法**：对每个非根节点 `child`，**要么** `child == x`（豁免），**要么** 它满足父子序。

**注意 `is_heap_except_up(H, 1) ≡ is_heap(H)`**：`x = 1` 时没有任何 `child` 等于 1（因为 `child >= 2`），所以所有 `child` 都必须满足父子序。**这个等式在正确性证明的收尾时用到**——如果 sift up 一路走到根（`i == 1`），那么 `is_heap_except_up(H, 1)` 直接就是 `is_heap(H)`。

**为什么这个不变式「不够强」——完整推导**

讲义第 7–9 页的核心论证。假设我们在位置 `x` 有一个违规，现在把 `x` 与它的父 `p = x/2` 交换。交换后需要证明：

- **(A)** 位置 `p` 上的新元素（原来的 `data[x]`）满足「≤ 它的两个孩子」。
- **(B)** 位置 `x` 上的新元素（原来的 `data[p]`）满足「≤ 它的两个孩子」。

**（A）的证明**：位置 `p` 的新元素是 `data[x]`，它的孩子是原来的 `2p` 和 `2p+1`。需要 `data[x] ≤ data[2p]` 和 `data[x] ≤ data[2p+1]`。

`data[x]` 的优先级高于 `data[p]`（这是交换的前提，因为 `!ok_above(H, p, x)`）。而由不变式（`2p`、`2p+1` 都不等于 `x`，所以它们满足父子序），`data[p] ≤ data[2p]`、`data[p] ≤ data[2p+1]`。由传递性 `data[x] < data[p] ≤ data[2p]` ✓。

**等等——这里 `data[x]` 是 `p` 的孩子吗？** 是的，`x = 2p` 或 `x = 2p+1`。所以 `2p` 和 `2p+1` 中**有一个就是 `x` 自己**。

**这是一个关键细节**：如果 `x = 2p`（左孩子），那么 `2p = x`，位置 `p` 的新元素是 `data[x]`，它的左孩子位置 `2p` 上现在是**原来的 `data[p]`**（交换后）。所以需要 `data[x] ≤ data[p]`——这正是交换的前提 ✓。右孩子 `2p+1` 上还是原来的元素，需要 `data[x] ≤ data[2p+1]`。由 `data[x] < data[p] ≤ data[2p+1]` ✓。

**（B）的证明**：位置 `x` 的新元素是 `data[p]`（原来的父）。它的孩子是 `2x` 和 `2x+1`。需要 `data[p] ≤ data[2x]` 和 `data[p] ≤ data[2x+1]`。

**但不变式只告诉我们**：`data[x] ≤ data[2x]`、`data[x] ≤ data[2x+1]`（因为 `2x`、`2x+1` 不等于 `x`，它们满足父子序）。

**而我们只知道 `data[p] > data[x]`**（交换前提）。

**从 `data[p] > data[x]` 和 `data[x] ≤ data[2x]`，推不出 `data[p] ≤ data[2x]`！**

**这就是缺口。** 反例：`data[p] = 10`、`data[x] = 3`、`data[2x] = 5`。交换前提 `10 > 3` ✓，`data[x] ≤ data[2x]` 即 `3 ≤ 5` ✓。但 `data[p] = 10 ≤ data[2x] = 5`？**假！**

**所以朴素的部分不变式确实不够强。** 交换后位置 `x` 上的 10 比它的孩子 5 大——**不变式仍然被违反，而且这次是在一个新的位置**。

### 5.7 加强：`grandparent_check`

讲义第 7–9 页的解法：**在循环不变式里额外要求「`x` 的孩子 ≥ `x` 的父」**。

```c
bool grandparent_check(heap H, int i) {
  int left = 2 * i;
  int right = left + 1;
  int grandparent = i / 2;

  if (i == 1) return true;                      /* 根没有父 */
  if (left >= H->next) return true;             /* 没有孩子 */
  if (right == H->next)                         /* 只有左孩子 */
    return ok_above(H, grandparent, left);
  /*@assert right < H->next; @*/
  return ok_above(H, grandparent, left) && ok_above(H, grandparent, right);
}
```

**逐行解释**：

- **`i == 1`**：根没有父，`grandparent = 0` 是无效下标。平凡满足。
- **`left >= H->next`**：`i` 是叶子（没有孩子）。平凡满足。
- **`right == H->next`**：只有左孩子（`right` 越界但 `left` 有效）。只需检查左孩子。
- **否则**：两个孩子都存在，都要检查。

**语义**：`i` 的每个孩子（如果存在）的优先级都不低于 `i` 的父。

**为什么这一条能补上缺口**：回到上面的反例。加强后的假设是 `data[p] ≤ data[2x]`（祖父母检查，因为 `p = x/2` 是 `2x` 的祖父）。那么（B）直接成立 ✓。

**加强后的完整证明表**（讲义第 9 页）：

| 假设（编号） | 内容 |
|---|---|
| (1) | `a ≤ b`（`a` 是 `x` 的父，`b` 是 `x`） |
| (2) | `b ≤ c`（`c` 是 `b` 的孩子） |
| (3) | `x ≤ c₁`（`c₁` 是 `x` 的左孩子） |
| (4) | `x ≤ c₂`（`c₂` 是 `x` 的右孩子） |
| (5) | `b > x`（交换前提：`x` 严格高于 `b`） |
| (6) | `b ≤ c₁`（祖父母检查） |
| (7) | `b ≤ c₂`（祖父母检查） |

**要证的结论**（交换后）：

| 结论 | 依据 |
|---|---|
| `a ? x`（允许例外，`x` 是新的违规位置） | 循环不变式允许 |
| `a ≤ c`（`a` 是 `x` 的父位置的新元素 `x`，`c` 是……） | 由 (1)(2) 传递 |
| `a ≤ b` | 由 (1) |
| `x ≤ c` | 由 (5)(2)：`x < b ≤ c` |
| `x ≤ b` | 由 (5) |
| `b ≤ c₁` | 由 (6) |
| `b ≤ c₂` | 由 (7) |

**这张表就是证明的核心。** 注意 (6)(7) 是**新加的假设**，没有它们，`b ≤ c₁`、`b ≤ c₂` 无法证明——这正是 5.6 节的缺口。

**注意这里的记号**：`a` 是 `x` 的祖父（`x/2/2`？不对）。让我重新梳理：

- `x` 是当前违规位置。
- `p = x/2` 是 `x` 的父。
- 交换后，`p` 位置上是 `x` 的原元素，`x` 位置上是 `p` 的原元素。
- `c₁ = 2x`、`c₂ = 2x+1` 是 `x` 的孩子（交换后它们仍是位置 `2x`、`2x+1` 上的元素，不变）。
- `a` 是 `p` 的父（即 `x` 的祖父），`b` 是 `p` 位置上的元素（交换前是 `p` 的原元素，交换后是 `x` 的原元素）。

**这个记号有点绕。** 用具体的数值更清楚：设 `x = 6`，则 `p = 3`，`a = 1`（根），`c₁ = 12`、`c₂ = 13`。

交换前：位置 3 上是 `data[3]`，位置 6 上是 `data[6]`，且 `data[6]` 严格高于 `data[3]`（违规）。

交换后：位置 3 上是 `data[6]`，位置 6 上是 `data[3]`。

**需要证明**：

- 位置 3 上的 `data[6]` ≤ 位置 6 和 7 上的元素。位置 6 上现在是 `data[3]`，需要 `data[6] ≤ data[3]` ✓（交换前提）。位置 7 上是 `data[7]`，需要 `data[6] ≤ data[7]`——由 `data[6] < data[3] ≤ data[7]` ✓（后者是原来的父子序，因为 7 ≠ 6）。
- 位置 6 上的 `data[3]` ≤ 位置 12、13 上的元素。需要 `data[3] ≤ data[12]`、`data[3] ≤ data[13]`——**这正是 `grandparent_check(H, 6)` 的内容** ✓。
- 位置 3 与它的父（位置 1）的关系：需要 `data[1] ≤ data[6]`。**这个可能不成立**——如果 `data[6]` 比 `data[1]` 还小，那么新的违规位置变成 3。**这正是循环继续的原因**，也是 `is_heap_except_up(H, 3)` 允许的例外。

**所以不变式 `is_heap_except_up(H, i) ∧ grandparent_check(H, i)` 在 `i ← i/2` 后仍然成立。** 这是循环保持的关键。

### 5.8 `pq_add` 的收尾论证

讲义第 10 页。循环退出时有两个条件：

1. `!(i > 1 && !ok_above(H, i/2, i))`，即 `i <= 1 || ok_above(H, i/2, i)`。
2. 循环不变式：`1 <= i && i < H->next`、`is_heap_except_up(H, i)`、`grandparent_check(H, i)`。

**分两种情形**：

**情形 1：`i <= 1`。** 由 `1 <= i`，得 `i == 1`。此时 `is_heap_except_up(H, 1) ≡ is_heap_ordered(H)`（5.6 节）。加上 `is_heap_safe(H)`（未被修改），得 `is_heap(H)` ✓。

**情形 2：`ok_above(H, i/2, i)`。** 此时唯一的例外位置 `i` 也满足了父子序。所以所有 `child` 都满足 `ok_above(H, child/2, child)`，即 `is_heap_ordered(H)` ✓。

**两种情形都得到 `is_heap(H)`，后置条件成立。** 证毕。

**这个收尾非常干净**——因为部分不变式被设计成「退出条件恰好补上最后一个例外」。

### 5.9 `pq_rem` 与 sift down

讲义第 11 页：

```c
elem pq_rem(heap H)
/*@requires is_heap(H) && !pq_empty(H); @*/
/*@ensures is_heap(H); @*/
{
  elem min = H->data[1];
  (H->next)--;
  if (H->next > 1) {
    H->data[1] = H->data[H->next];
    sift_down(H);
  }
  return min;
}
```

**逐步解释**：

1. **`min = H->data[1]`**：根是最小元（第 25 讲的不变式推论）。
2. **`(H->next)--`**：空位前移，逻辑上删除了最后一个元素。
3. **`if (H->next > 1)`**：如果删除后还有元素，需要修复。
4. **`H->data[1] = H->data[H->next]`**：把**原来的最后一个元素**（现在是 `data[next]`，因为 `next` 已经减过）移到根。
5. **`sift_down(H)`**：下滤修复。

**为什么 `if (H->next > 1)` 不能省**：如果原来只有 1 个元素，`next` 从 2 减到 1。此时 `data[1]` 是要删除的元素，**不应该**把它复制到根（那等于没删）。而且 `H->data[H->next] = H->data[1]` 会把 `min` 又写回根——**逻辑错误**。

**`is_heap_except_down`**：

```c
bool is_heap_except_down(heap H, int x) {
  for (int child = 2; child < H->next; child++) {
    if (!(child / 2 == x || ok_above(H, child / 2, child)))
      return false;
  }
  return true;
}
```

**读法**：对每个非根节点 `child`，**要么** 它的父是 `x`（豁免），**要么** 它满足父子序。

**与 `is_heap_except_up` 的区别**：`except_up` 豁免「`child == x`」（`x` 作为孩子的那一对）；`except_down` 豁免「`child/2 == x`」（`x` 作为父的那些对）。

**为什么 `sift_down` 要豁免「`x` 作为父」的所有对**：因为 `x` 有两个孩子，两个对都可能违规。而 `sift_up` 里 `x` 只有一个父，所以只豁免一对。

### 5.10 `sift_down` 的实现

讲义第 13 页：

```c
void sift_down(heap H)
/*@requires is_heap_except_down(H, 1); @*/
/*@ensures is_heap(H); @*/
{
  int i = 1;
  while (2 * i < H->next)
  /*@loop_invariant 1 <= i && i < H->next; @*/
  /*@loop_invariant is_heap_except_down(H, i); @*/
  /*@loop_invariant grandparent_check(H, i); @*/
  {
    if (done_sifting_down(H, i)) return;
    int p = child_to_swap_up(H, i);
    swap_up(H, p);
    i = p;
  }
  /*@assert i < H->next && 2 * i >= H->next; @*/
}
```

**辅助函数一：`done_sifting_down`**

```c
bool done_sifting_down(heap H, int i) {
  int left = 2 * i;
  int right = left + 1;
  return ok_above(H, i, left)
      && (right >= H->next || ok_above(H, i, right));
}
```

**语义**：`i` 已经满足与它所有孩子的不变式。**前置隐含 `left < H->next`**（由 while 条件 `2*i < H->next`）。

**辅助函数二：`child_to_swap_up`**

```c
int child_to_swap_up(heap H, int i)
/*@requires 2 * i < H->next; @*/
/*@ensures \result / 2 == i; @*/
{
  int left = 2 * i;
  int right = left + 1;
  if (right >= H->next || ok_above(H, left, right))
    return left;
  /*@assert right < H->next; @*/
  /*@assert ok_above(H, right, left); @*/
  return right;
}
```

**语义**：返回「优先级更高的那个孩子」的下标。

- **只有左孩子**（`right >= H->next`）：返回 `left`。
- **两个孩子都有，且左孩子不低于右孩子**（`ok_above(H, left, right)`）：返回 `left`。
- **否则**：右孩子严格更高，返回 `right`。

**后置 `\result / 2 == i`**：返回值确实是 `i` 的孩子。

**为什么叫 `child_to_swap_up`**：从孩子的角度，它要「上移」到父的位置。**这个命名提醒我们「交换」是双向的**——同一个操作，从父看是「下滤」，从孩子看是「上滤」。

**循环终止的论证**：每次 `i = p`，其中 `p` 是 `i` 的孩子，所以 `p > i`。而 `p < H->next`（`child_to_swap_up` 的返回值在有效范围内）。所以 `i` **严格递增**且**有上界** `H->next − 1`。**必然终止**。

**复杂度**：每次下降一层，最多 `⌊log₂ n⌋` 层。每层 O(1)（两次比较）。**O(log n)**。

**循环退出后的断言 `2*i >= H->next`**：`i` 是叶子（或只有一个不存在的左孩子）。此时 `is_heap_except_down(H, i)` 中 `i` 作为父的对**都不存在**（没有孩子），所以 `is_heap_except_down(H, i) ≡ is_heap_ordered(H)` ✓。

**但如果从 `return` 退出**（`done_sifting_down` 为真），那么 `i` 与它的所有孩子都满足不变式，其他位置由循环不变式保证。也是 `is_heap_ordered(H)` ✓。

**两条退出路径都得到后置条件。**

### 5.11 sift down 的证明表

讲义第 13–14 页。设 `i` 位置上的元素是 `x`，它的左孩子是 `b`、右孩子是 `c`（假设 `c` 优先级更高，所以要交换 `x` 与 `c`）。

**假设**：

| 编号 | 内容 |
|---|---|
| (1) | `a ≤ x`（`a` 是 `x` 的父） |
| (2) | `x ≤ b`（左孩子） |
| (3) | `x > c`（右孩子优先级更高，这是交换前提） |
| (4) | `c ≤ c₁`（`c` 的左孩子） |
| (5) | `c ≤ c₂`（`c` 的右孩子） |
| (6) | `a ≤ b`（祖父母检查：`b` 是 `x` 的孩子，`a` 是 `x` 的父） |
| (7) | `a ≤ c`（祖父母检查） |

**要证**（交换 `x` 与 `c` 后）：

| 结论 | 依据 |
|---|---|
| `a ≤ c` | 由 (7) |
| `c ≤ b` | 由 (3)(2)：`c < x ≤ b` |
| `c ≤ x` | 由 (3) |
| `x ? c₁` | 允许例外（新的违规位置是 `c` 的位置） |
| `x ? c₂` | 允许例外 |
| `c ≤ c₁` | 由 (4) |
| `c ≤ c₂` | 由 (5) |

**注意 `x ? c₁`、`x ? c₂` 是「允许例外」**——因为交换后 `x` 到了 `c` 的位置，它可能与 `c` 的孩子（`c₁`、`c₂`）违规。**这正是 `is_heap_except_down(H, c)` 允许的例外。**

**对比 sift up 的表**（5.7 节）：结构完全对称，只是「一个父、两个孩子」与「一个孩子、两个孙子」的角色互换。**这个对称性是「堆的两条不变式互为镜像」的体现。**

### 5.12 Heapsort

讲义第 15–16 页：

```c
void heapsort(elem *A, int n, has_higher_priority_fn *prior) {
  heap H = pq_new(n, prior);
  for (int i = 0; i < n; i++) pq_add(H, A[i]);
  for (int i = 0; i < n; i++) A[i] = pq_rem(H);
  pq_free(H);
}
```

**复杂度**：

- `n` 次 `pq_add`，每次 O(log n) ⇒ **O(n log n)**。
- `n` 次 `pq_rem`，每次 O(log n) ⇒ **O(n log n)**。
- 总计 **O(n log n)**。

**与归并排序同级**，与快排的期望同级（但快排最坏 O(n²)）。

**空间**：`pq_new(n, prior)` 分配 `n + 1` 个 `elem` 的空间 ⇒ **O(n) 辅助空间**。

**讲义提到的改进**：可以做到**原地**（O(1) 辅助空间）。思路是：

1. 直接在输入数组 `A` 上建堆（把 `A` 当作 `data[0 … n−1]`，用 0 基下标）。
2. 每次 `rem` 时，把根与最后一个元素交换，堆大小减 1，然后 sift down。被换出的最小元就落在了数组末尾的正确位置。

**这就是经典的 in-place heapsort**。讲义说「可以改」，但**没有给出完整代码**——这是一个值得自己实现的练习。

**建堆可以做到 O(n)**（而不是 O(n log n)）：从最后一个非叶节点（下标 `n/2`）开始，倒序对每个节点 `sift_down`。这个算法的复杂度分析是 `Σ (每层节点数 × 该层高度) = O(n)`，因为大部分节点在底层且高度很小。**这叫 Floyd 建堆法。**

**讲义第 15–16 页的实验代码**：

```c
int main() {
  int n = (1 << 9) - 1;         /* 511 */
  int num_tests = 10;
  srand(0xc0c0ffee);
  ...
  assert(is_sorted(A, 0, n));
}
```

**`n = 511`**：完全二叉树满 9 层（`2^9 − 1 = 511`），形状完美。**这个选择让「形状不变式」在测试中始终成立**，避免边界情形干扰。

**`seed = 0xc0c0ffee`**：一个固定的随机种子，保证测试可重现。**`0xc0c0ffee` 是 CMU 15-122 的传统彩蛋**——`C0` 是课程语言，`c0c0ffee` 读作「coco coffee」。

### 5.13 三条总结

讲义第 16 页给出三条总结，**这是全讲的纲领**：

**（1）清楚理解「为什么必须临时违反不变式」以及「如何恢复它」。**

这是「恢复不变量」模式的本质：**有些操作无法在不破坏不变式的情况下完成**。`pq_add` 必须先放元素再修；`pq_rem` 必须先把末尾元素提到根再修。**关键是让破坏「局部化」且「可修复」。**

**（2）在接口处只传递满足完整不变式的实例。**

`pq_add` 的前置是 `is_heap(H) && !pq_full(H)`；`pq_rem` 的前置是 `is_heap(H) && !pq_empty(H)`。**部分不变式只在内部使用**，不暴露给调用者。这保证了「抽象屏障」——调用者不需要知道 sift up / sift down 的存在。

**（3）写出检查「部分不变式」的谓词，用作恢复函数的 pre 与 loop invariant。**

`is_heap_except_up` / `is_heap_except_down` / `grandparent_check` 就是这样的谓词。**它们是「不变量工程」的核心工具**——把「哪儿乱了」写成可检查的代码，然后用它做契约。

**这三条可以推广到所有「修复型算法」**：

- **AVL 插入**（第 16 讲）：插入后某个节点高度差变成 2，用旋转修复。
- **红黑树插入/删除**：颜色违规，用旋转 + 重着色修复。
- **并查集路径压缩**（第 24 讲）：压缩后高度信息不再精确，但仍是上界——不变式被「放松」而非「恢复」。
- **数据库事务**：临时违反一致性约束，提交时检查。

**「恢复不变量」是算法设计中最通用的模式之一。**

## 6. 代码示例

### 6.1 官方课程代码

以下内容出自 `26-heap.pdf`，页码为该 PDF 的页码。

**（1）堆的结构定义**（第 2 页）

```c
struct heap_header {
  int limit;      /* limit = capacity+1 */
  int next;       /* 1 <= next && next <= limit */
  elem[] data;    /* \length(data) == limit */
  has_higher_priority_fn *prior;  /* != NULL */
};
```

**（2）`is_heap_safe`**（第 3 页）

五个条件：`H != NULL`、`1 < H->limit && H->limit <= int_max()/2`、`is_array_expected_length(H->data, H->limit)`、`1 <= H->next && H->next <= H->limit`、`H->prior != NULL`。

**（3）`ok_above`**（第 4 页）

`return !(*H->prior)(e2, e1);` —— `e1` 优先级 ≥ `e2`（非严格）。

**（4）`is_heap_ordered`**（第 4 页）

`for (int child = 2; child < H->next; child++)` 逐个比较父子。

**（5）`is_heap`**（第 4 页）

`is_heap_safe(H) && is_heap_ordered(H)`。

**（6）`pq_empty` / `pq_full`**（第 4–5 页）

`H->next == 1` / `H->next == H->limit`。

**（7）`pq_new`**（第 4–5 页）

`limit = capacity + 1`、`next = 1`、`data = alloc_array(...)`、`data[0]` 不用。

**（8）`swap_up` 的前后置**（第 5–6 页）

前置 `2 <= child && child < H->next && !ok_above(H, child/2, child)`；后置 `ok_above(H, child/2, child)`。

**（9）`pq_add` 的循环与三条循环不变式**（第 6–10 页）

`1 <= i && i < H->next`、`is_heap_except_up(H, i)`、`grandparent_check(H, i)`。

**（10）`is_heap_except_up`**（第 7 页）

`if (!(child == x || ok_above(H, child/2, child))) return false;`；注意 `is_heap_except_up(H,1) ≡ is_heap(H)`。

**（11）「朴素部分不变式不够强」的论证与加强**（第 7–9 页）

反例 + 证明表；`grandparent_check(H, i)` 的完整实现（含 `i == 1`、`left >= H->next`、`right == H->next` 三个边界）。

**（12）`pq_add` 的后置证明**（第 10 页）

循环退出两种情形（`i <= 1` / `ok_above(H, i/2, i)`）分别推出 `is_heap(H)`。

**（13）`pq_rem`**（第 11 页）

保存 `min`、`(H->next)--`、`if (H->next > 1)` 才搬移与 sift down。

**（14）`is_heap_except_down`**（第 11 页）

`if (!(parent == x || ok_above(H, parent, child))) return false;`

**（15）`sift_down`**（第 13 页）

while 条件 `2*i < H->next`；三条循环不变式；退出断言 `i < H->next && 2*i >= H->next`。

**（16）`done_sifting_down` / `child_to_swap_up`**（第 13 页）

后者后置 `\result/2 == i`；两个孩子都有时用 `ok_above(H, left, right)` 选较小的。

**（17）sift down 的证明表**（第 13–14 页）

七条假设 → 七条结论。

**（18）Heapsort**（第 15–16 页）

`n = (1<<9)-1 = 511`、`num_tests = 10`、`seed = 0xc0c0ffee`、`assert(is_sorted(A, 0, n))`。

**（19）三条总结**（第 16 页）

临时违反的自觉、接口处传完整不变式、部分不变式谓词用作 pre 与 loop invariant。

**（20）习题与答案**（第 17 页题目，第 18–24 页答案）

Ex2 合法堆 `[X, 3, 8, 4, 9]`（既非升序也非降序）；Ex3 递归版 `is_heap_ordered_helper(H, child)`；Ex4 抽出 `sift_up(heap* H)`；Ex5 `pq_bump`；Ex6 sift down 的图证明。

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念

**示例一：用灵活数组成员实现的完整最小堆（标准 C）。**

```c
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <assert.h>
#include "lib/xalloc.h"

typedef void* elem;
typedef bool has_higher_priority_fn(elem e1, elem e2);

typedef struct heap_header {
  int limit;                       /* capacity + 1 */
  int next;                        /* 1 <= next <= limit */
  has_higher_priority_fn *prior;
  elem data[];                     /* 灵活数组成员，长度 limit */
} *heap;

/* ---------- 构造与销毁 ---------- */

heap pq_new(int capacity, has_higher_priority_fn *prior) {
  assert(capacity > 0);
  assert(prior != NULL);
  int limit = capacity + 1;
  heap H = xmalloc(sizeof(struct heap_header) + limit * sizeof(elem));
  H->limit = limit;
  H->next  = 1;
  H->prior = prior;
  return H;
}

void pq_free(heap H) {
  if (H == NULL) return;
  free(H);                          /* 一次 free 搞定（灵活数组与 header 连续） */
}

/* ---------- 不变式检查 ---------- */

bool pq_empty(heap H) { return H->next == 1; }
bool pq_full(heap H)  { return H->next == H->limit; }

static bool ok_above(heap H, int i1, int i2) {
  elem e1 = H->data[i1];
  elem e2 = H->data[i2];
  return !(*H->prior)(e2, e1);      /* e1 的优先级不低于 e2 */
}

static bool is_heap_ordered(heap H) {
  for (int child = 2; child < H->next; child++)
    if (!ok_above(H, child / 2, child)) return false;
  return true;
}

static bool is_heap_safe(heap H) {
  return H != NULL
      && 1 < H->limit
      && 1 <= H->next && H->next <= H->limit
      && H->prior != NULL;
}

bool is_heap(heap H) { return is_heap_safe(H) && is_heap_ordered(H); }

/* ---------- 部分不变式 ---------- */

static bool is_heap_except_up(heap H, int x) {
  for (int child = 2; child < H->next; child++)
    if (!(child == x || ok_above(H, child / 2, child))) return false;
  return true;
}

static bool is_heap_except_down(heap H, int x) {
  for (int child = 2; child < H->next; child++)
    if (!(child / 2 == x || ok_above(H, child / 2, child))) return false;
  return true;
}

static bool grandparent_check(heap H, int i) {
  int left  = 2 * i;
  int right = left + 1;
  int gp    = i / 2;
  if (i == 1) return true;
  if (left >= H->next) return true;
  if (right >= H->next) return ok_above(H, gp, left);
  return ok_above(H, gp, left) && ok_above(H, gp, right);
}

/* ---------- 基本操作 ---------- */

static void swap(heap H, int i, int j) {
  elem tmp = H->data[i];
  H->data[i] = H->data[j];
  H->data[j] = tmp;
}

void pq_add(heap H, elem e) {
  assert(is_heap(H));
  assert(!pq_full(H));

  H->data[H->next] = e;
  (H->next)++;

  int i = H->next - 1;
  while (i > 1 && !ok_above(H, i / 2, i)) {
    assert(is_heap_except_up(H, i));
    assert(grandparent_check(H, i));
    swap(H, i, i / 2);
    i = i / 2;
  }
  assert(is_heap(H));
}

elem pq_peek(heap H) {
  assert(is_heap(H));
  assert(!pq_empty(H));
  return H->data[1];
}

elem pq_rem(heap H) {
  assert(is_heap(H));
  assert(!pq_empty(H));

  elem min = H->data[1];
  (H->next)--;
  if (H->next > 1) {
    H->data[1] = H->data[H->next];
    /* sift down */
    int i = 1;
    while (2 * i < H->next) {
      int left  = 2 * i;
      int right = left + 1;
      int child = left;
      if (right < H->next && ok_above(H, right, left)) child = right;
      if (ok_above(H, i, child)) break;
      swap(H, i, child);
      i = child;
    }
  }
  assert(is_heap(H));
  return min;
}
```

**三个关键点**：

1. **`free(H)` 一次就够**。因为 `data[]` 是灵活数组成员，它与 `struct heap_header` 在同一块 `xmalloc` 分配的内存里。**这是灵活数组相对 `elem *data` 的最大优势**——少一次分配、少一次 free、少一类泄漏。

2. **`assert(is_heap_except_up(H, i))` 放在循环体内**。注意位置：**在交换之前**。这检查的是「进入这一轮时，除了 `i` 之外都整齐」。如果把 assert 放在 `swap` 之后，语义就变了（那时 `i` 已经换了，例外位置也变了）。

3. **`pq_rem` 里的 `break` 而非 `return`**。因为 `min` 还没返回，必须走到最后的 `return min`。**如果在这里写 `return`，就会漏掉 `assert(is_heap(H))`**（虽然功能上没问题，但调试时少了验证）。

**示例二：故意写一个「朴素部分不变式」的版本，观察它在哪里失败。**

```c
/* 错误版本：只用 is_heap_except_up，没有 grandparent_check */
void pq_add_naive(heap H, elem e) {
  H->data[H->next] = e;
  (H->next)++;
  int i = H->next - 1;
  while (i > 1 && !ok_above(H, i / 2, i)) {
    /*@loop_invariant is_heap_except_up(H, i); @*/   /* 只有这一条！ */
    swap(H, i, i / 2);
    i = i / 2;
  }
}
```

**这个版本「看起来」能工作**——事实上它能正确地把元素上滤到位，最终结果是正确的堆。**但「能工作」和「能证明」是两件事。**

**为什么「能工作」**：`swap(H, i, i/2)` 确实把更小的元素往上送，最终结果正确。

**为什么「不能证明」**：循环不变式 `is_heap_except_up(H, i)` 在 `i ← i/2` 后**不能保持**。具体地，交换后位置 `i` 上的元素（原来的父）可能与它的孩子违规（5.6 节的反例：`data[p]=10`、`data[x]=3`、`data[2x]=5`）。

**构造一个具体反例**：

考虑堆（数组 `[_, 1, 5, 2, 7, 9, 3]`，`next = 7`）：

```
        1
      /   \
     5     2
    / \   /
   7   9 3
```

不变式：`1≤5`、`1≤2`、`5≤7`、`5≤9`、`2≤3` ✓。

现在 `pq_add(0)`：

- `data[7] = 0`，`next = 8`。位置 7 是位置 3（值 2）的右孩子。
- `i = 7`：`ok_above(3, 7)`？`data[3]=2`、`data[7]=0`。`0` 严格高于 `2`，所以 `!ok_above` 为真，进入循环。
  - `is_heap_except_up(H, 7)`？检查所有 `child ∈ [2,7]` 除了 7：`1≤5`✓、`1≤2`✓、`5≤7`✓、`5≤9`✓、`2≤3`✓。成立 ✓。
  - 交换 7 与 3：`[_, 1, 5, 0, 7, 9, 3, 2]`，`i = 3`。
- `i = 3`：`ok_above(1, 3)`？`data[1]=1`、`data[3]=0`。`0` 严格高于 `1`，进入循环。
  - **`is_heap_except_up(H, 3)`？** 检查除 3 外的所有：`1≤5`✓、`5≤7`✓、`5≤9`✓、`2≤3`✓、`3≤2`？`data[3]=0`、`data[7]=2`，`0 ≤ 2` ✓。
  - **但位置 7 现在是 2**（原来是 3 的位置上的元素被换下来了）……等等。

**让我重新算。** 交换 7 与 3 后：

- 位置 3 上：`0`（新元素）
- 位置 7 上：`2`（原来的 `data[3]`）

**现在检查位置 7 与它的父（位置 3）**：`ok_above(3, 7)` = `0 ≤ 2` ✓。

**但位置 7 有孩子吗**？`2·7 = 14 ≥ next = 8`，没有。所以位置 7 作为父的对都平凡满足。

**继续**：`i = 3`，交换 3 与 1：`[_, 0, 5, 1, 7, 9, 3, 2]`，`i = 1`。

- `i = 1`：循环条件 `i > 1` 为假，退出。

**最终数组**：`[_, 0, 5, 1, 7, 9, 3, 2]`。

```
        0
      /   \
     5     1
    / \   / \
   7   9 3   2
```

**检查不变式**：`0≤5`✓、`0≤1`✓、`5≤7`✓、`5≤9`✓、`1≤3`✓、`1≤2`✓。**完全正确！**

**所以这个例子没有暴露问题。** 需要构造一个「交换后位置 `i` 的元素比它的孩子大」的情形。

**构造**：需要 `data[p]` 比 `data[2x]` 大，其中 `p = x/2`。

设 `x = 4`（`p = 2`，`2x = 8`、`2x+1 = 9`）。需要：

- `data[4] < data[2]`（违规，触发交换）
- `data[2] > data[8]` 或 `data[2] > data[9]`（交换后 `data[2]` 到位置 4，位置 4 的孩子是 8、9）

设 `data[2] = 10`、`data[4] = 3`、`data[8] = 5`。

**但等等**：`data[4]` 的孩子是 `8`、`9`，所以 `data[4] ≤ data[8]` 必须成立（不变式）。`3 ≤ 5` ✓。

**构造完整堆**：

```
位置:  1   2   3   4   5   6   7   8   9
值:    1  10   2   3  11  12  13   5   6
```

检查不变式：`1≤10`✓、`1≤2`✓、`10≤3`？**✗ 违反！**

**所以 `data[2]=10` 与 `data[4]=3` 本身就不满足不变式。** 这说明我的构造不对——因为 `data[4]` 是 `data[2]` 的孩子，`data[2] ≤ data[4]` 必须成立。而交换前提是 `data[4] < data[2]`——**矛盾**。

**啊，这就是关键！** `x` 是 `p` 的孩子，所以 `data[p] ≤ data[x]` 是原来的不变式（除了 `x` 这个例外）。交换前提 `data[x] < data[p]` 说明 `x` 正是那个例外。

**交换后**：`data[p]` 到了位置 `x`。需要 `data[p] ≤ data[2x]`。而原来的不变式说 `data[x] ≤ data[2x]`（因为 `2x ≠ x`，它不豁免）。

**从 `data[p] > data[x]` 和 `data[x] ≤ data[2x]`，推不出 `data[p] ≤ data[2x]`。**

**具体构造**：`data[p] = 10`、`data[x] = 3`、`data[2x] = 5`。

**但 `data[p] = 10` 是 `data[x] = 3` 的父**，原来 `10 ≤ 3` 违反——**这正是那个例外** ✓。

**完整堆**：设 `x = 4`，`p = 2`。

```
位置:  1    2    3    4    5    6    7    8    9   10
值:    0   10    1    3    2   20   30    5    6    ...
```

检查：

- `1 ≤ 2`：`0 ≤ 10` ✓
- `1 ≤ 3`：`0 ≤ 1` ✓
- `2 ≤ 4`：`10 ≤ 3` **✗ 违反**（这是我们的例外 `x=4`）
- `2 ≤ 5`：`10 ≤ 2` **✗ 也违反！**

**问题**：`x = 4` 只豁免一对，但 `data[5] = 2 < data[2] = 10` 也违规。**所以这个配置不是「只有一个例外」的合法部分不变式状态。**

**必须让 `data[5] ≥ data[2]`**。设 `data[5] = 15`：

```
位置:  1    2    3    4    5    6    7    8    9   10
值:    0   10    1    3   15   20   30    5    6   40
```

检查：

- `1 ≤ 2`：`0 ≤ 10` ✓
- `1 ≤ 3`：`0 ≤ 1` ✓
- `2 ≤ 4`：`10 ≤ 3` ✗（例外 `x=4`）
- `2 ≤ 5`：`10 ≤ 15` ✓
- `4 ≤ 8`：`3 ≤ 5` ✓
- `4 ≤ 9`：`3 ≤ 6` ✓
- `5 ≤ 10`：`15 ≤ 40` ✓

**`is_heap_except_up(H, 4)` 成立** ✓。

**`grandparent_check(H, 4)`**：`gp = 2`，`left = 8`、`right = 9`。需要 `ok_above(2, 8)` 即 `10 ≤ 5`——**✗ 不成立！**

**所以这个状态违反了 `grandparent_check`。** 而这正是我们要说明的：**如果 `grandparent_check` 不成立，交换后就会出错。**

**执行 sift up**：交换位置 4 与 2：

```
位置:  1    2    3    4    5    6    7    8    9   10
值:    0    3    1   10   15   20   30    5    6   40
```

**检查位置 4 与它的孩子（8、9）**：`10 ≤ 5`？**✗ 违反！**

**所以朴素版本在这个状态下会「修好一处、弄坏另一处」**——它把一个违规从位置 4 搬到了位置 4（但方向反了：从「比父小」变成「比孩子大」）。

**继续 sift up**：`i = 2`，`ok_above(1, 2)`？`0 ≤ 3` ✓，退出。

**最终堆**：

```
位置:  1    2    3    4    5    6    7    8    9   10
值:    0    3    1   10   15   20   30    5    6   40
```

`4 ≤ 8`：`10 ≤ 5` **✗**。**不是合法的堆！**

**这就是「朴素部分不变式不够强」的具体后果**——不是「证明不了」，而是**算法真的会出错**（在这个状态下）。

**注意**：这个状态**在实际的 `pq_add` 中不会出现**，因为真实的不变式（`grandparent_check`）会阻止它。**但如果我们只用朴素不变式做验证，就会接受这个非法状态，然后算法出错。**

**这正是「加强不变式」的意义**：不只是让证明通过，而是**排除了算法会出错的状态**。

**示例三：原地 heapsort（O(1) 辅助空间）。**

```c
/* 0 基下标的原地 heapsort（升序） */
static void sift_down_arr(int *A, int n, int i) {
  while (2 * i + 1 < n) {                 /* 有左孩子 */
    int left  = 2 * i + 1;
    int right = left + 1;
    int child = left;
    if (right < n && A[right] > A[left]) child = right;   /* 选较大的（大顶堆） */
    if (A[i] >= A[child]) break;
    int t = A[i]; A[i] = A[child]; A[child] = t;
    i = child;
  }
}

void heapsort_inplace(int *A, int n) {
  /* 阶段 1：建大顶堆（Floyd 建堆，O(n)） */
  for (int i = n / 2 - 1; i >= 0; i--)
    sift_down_arr(A, n, i);

  /* 阶段 2：反复把堆顶（最大）换到末尾，堆缩小 */
  for (int end = n - 1; end > 0; end--) {
    int t = A[0]; A[0] = A[end]; A[end] = t;
    sift_down_arr(A, end, 0);             /* 注意：传 end 而不是 n */
  }
}
```

**三个关键点**：

1. **0 基下标**：左孩子 `2i+1`、右孩子 `2i+2`、父 `(i−1)/2`（第 25 讲答 5 的公式）。**原地版本用 0 基更自然**，因为输入数组本来就是 0 基。

2. **用大顶堆而非小顶堆**：升序排序要反复把**最大**元素换到末尾。所以建**大顶堆**（父 ≥ 子）。**这与第 25–26 讲的「最小堆」方向相反**——注意不要混。

3. **`sift_down_arr(A, end, 0)` 的第二个参数是 `end` 而不是 `n`**。因为「已排序的尾部」不再属于堆。**这是原地 heapsort 最容易写错的地方**——如果传 `n`，会把已排序的部分又搅乱。

**复杂度**：

- 建堆：O(n)（Floyd 法）。
- 排序：`n−1` 次 `sift_down`，每次 O(log n) ⇒ O(n log n)。
- 总计 **O(n log n)**，辅助空间 **O(1)**。

**为什么建堆是 O(n)**：第 `k` 层（从根数，根是第 0 层）有 `2^k` 个节点，每个的 sift down 代价是 `O(h − k)`，其中 `h = log₂ n`。总和 `Σ_{k=0}^{h} 2^k (h−k) = O(n)`。**直觉**：大部分节点在底层，而底层节点的 sift down 代价很小（几乎不用动）。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键区别 | 记忆点 |
|---|---|---|---|
| 完整不变式 `is_heap` | 部分不变式 `is_heap_except_up/down` | 前者在接口处用；后者在修复函数内部用 | 一个对外，一个对内 |
| `is_heap_safe` | `is_heap_ordered` | 前者管「能安全访问」；后者管「语义正确」 | 一个防崩溃，一个防逻辑错 |
| `is_heap_except_up` | `is_heap_except_down` | 前者豁免「`x` 作为孩子」；后者豁免「`x` 作为父」 | 一个向上，一个向下 |
| 朴素部分不变式 | 加强版（+`grandparent_check`） | 后者能证明交换后不变式保持；前者不能 | 少了它算法真会出错 |
| sift up 与父交换 | sift down 与较小的孩子交换 | 前者只有一个候选；后者要在两个中选 | 一个无需选择 |
| `next` 指向下一个空位 | `next` 指向最后一个元素 | 前者的空/满判断是 `next==1` / `next==limit` | 空位语义更简洁 |
| `elem[] data`（灵活数组） | `elem *data`（分开分配） | 前者一次分配一次 free；后者两次 | 灵活数组更省 |
| `pq_rem` 的 `if (H->next > 1)` | 省略这个判断 | 后者会把 `min` 写回根 | 边界必须判 |
| 原地 heapsort（大顶堆） | 本讲 heapsort（小顶堆） | 前者升序用大顶堆；后者用最小堆 | 方向相反 |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-122/lectures/26-heap.pdf`
- **总页数**：24 页
- **本节重点页码**（PDF 页码，即提取文本中 `=== [page N] ===` 的 N）：
  - 第 2 页：`struct heap_header`（`limit` / `next` / `elem[] data` / `prior`）
  - 第 2–3 页：最小堆不变式概述
  - 第 3 页：`is_heap_safe` 五个条件
  - 第 4 页：`ok_above`（`!(*H->prior)(e2, e1)`）、`is_heap_ordered`、`is_heap`
  - 第 4–5 页：`pq_empty` / `pq_full` / `pq_new`
  - 第 5–6 页：`swap_up` 的前后置条件
  - 第 5–11 页：`pq_add` 与 sift up 的完整循环
  - 第 7 页：`is_heap_except_up`
  - 第 7–9 页：**朴素部分不变式不够强的论证**、`grandparent_check`、加强后的证明表
  - 第 10 页：`pq_add` 后置证明（循环退出两情形）
  - 第 11 页：`pq_rem`、`is_heap_except_down`
  - 第 11–14 页：`sift_down` 与 `done_sifting_down` / `child_to_swap_up`
  - 第 13–14 页：sift down 的证明表
  - 第 15–16 页：Heapsort（`n = 511`、`seed = 0xc0c0ffee`）与三条总结
  - 第 17 页：习题；第 18–24 页：习题答案（Ex2 合法堆、Ex3 递归 `is_heap_ordered`、Ex4 抽出 `sift_up`、Ex5 `pq_bump`、Ex6 sift down 图证明）
- **原始网页链接**：`https://www.cs.cmu.edu/~15122-archive/f26/handouts/lectures/26-heap.pdf`
- **配套代码包**：`90-原始PDF/15-122/code/26-heap.tgz`

## 9. 对应视频

未找到官方公开录像。本讲是「形式化验证」味道最重的一讲，建议配合 6.2 节的示例二——**亲手跑一遍那个反例**（`data = [_, 0, 10, 1, 3, 15, 20, 30, 5, 6, 40]`，`x = 4`），你会看到朴素版本如何把一个违规「搬」成另一个违规。这比读十遍证明表更有用。

## 10. 本节复习

1. `struct heap_header` 四字段：`limit = capacity + 1`、`next`（下一个空位，`1 ≤ next ≤ limit`）、`elem[] data`（灵活数组成员，必须是最后一个）、`prior`（非 NULL）。
2. `is_heap_safe`（能安全访问）与 `is_heap_ordered`（语义正确）分开写；`is_heap = safe && ordered`。
3. `ok_above(H, i1, i2)` 是**非严格**的：`!(*H->prior)(e2, e1)`，即 `e1 ≥ e2`。
4. `is_heap_except_up(H, x)` 豁免「`child == x`」；`is_heap_except_down(H, x)` 豁免「`child/2 == x`」。**`is_heap_except_up(H, 1) ≡ is_heap(H)`。**
5. **朴素部分不变式不够强**：交换 `x` 与 `x/2` 后，位置 `x` 上的新元素（原来的父）可能与它的孩子违规。**反例：`data[p]=10`、`data[x]=3`、`data[2x]=5`。**
6. **加强：`grandparent_check(H, i)`**——`i` 的孩子 ≥ `i` 的父。加上它，证明表才能闭合。
7. `pq_add` 收尾：循环退出时 `i <= 1` 或 `ok_above(H, i/2, i)`，两种情形都推出 `is_heap(H)`。
8. `pq_rem`：`min = data[1]`、`next--`、`if (next > 1)` 才搬移末尾元素到根并 sift down。**这个 `if` 不能省。**
9. `sift_down` 每次 `i = child_to_swap_up(H, i)`，`i` 严格递增有上界，**必然终止**；O(log n)。
10. Heapsort O(n log n)；原地版本用**大顶堆** + Floyd 建堆 O(n)，辅助空间 O(1)。

## 11. 自我检查

**题 1.** 设堆数组为 `[_, 0, 10, 1, 3, 15, 20, 30, 5, 6, 40]`（`next = 11`）。验证 `is_heap_except_up(H, 4)` 成立、`grandparent_check(H, 4)` 不成立。然后执行一次「交换位置 4 与位置 2」，说明为什么结果**不是**合法堆。

**题 2.** 为什么 `pq_rem` 里的 `if (H->next > 1)` 不能省略？如果堆里只有 1 个元素，省略会发生什么？请写出具体的错误结果。

**题 3.** 用灵活数组成员 `elem[] data` 与用指针 `elem *data` 相比，各有什么优缺点？如果 `pq_new` 需要「动态扩容」（容量不够时重新分配），哪种写法更容易实现？

**题 4.** 设 `n = 1000` 的堆。`pq_add` 最坏要做多少次 `swap_up`？`pq_rem` 最坏要做多少次 `swap`？各自的比较次数是多少？（注意 `pq_rem` 每层要比较两次。）

**题 5.** 证明 Floyd 建堆是 O(n)。提示：第 `k` 层有 `2^k` 个节点，每个的 sift down 代价是 `O(h − k)`，求和 `Σ_{k=0}^{h} 2^k (h−k)`。

<details>
<summary>参考答案</summary>

**答 1.**
数组 `[_, 0, 10, 1, 3, 15, 20, 30, 5, 6, 40]`，`next = 11`，有效下标 `1 … 10`。

**树形**：

```
              0 (1)
           /         \
       10 (2)        1 (3)
       /    \        /    \
   3 (4)  15 (5)  20 (6)  30 (7)
   /  \    /
5 (8) 6(9) 40(10)
```

**验证 `is_heap_except_up(H, 4)`**：检查所有 `child ∈ [2, 10]` 除 `4`：

| child | 父 | 父值 | 子值 | `父 ≤ 子`？ |
|---|---|---|---|---|
| 2 | 1 | 0 | 10 | ✓ |
| 3 | 1 | 0 | 1 | ✓ |
| 4 | 2 | 10 | 3 | **跳过（例外）** |
| 5 | 2 | 10 | 15 | ✓ |
| 6 | 3 | 1 | 20 | ✓ |
| 7 | 3 | 1 | 30 | ✓ |
| 8 | 4 | 3 | 5 | ✓ |
| 9 | 4 | 3 | 6 | ✓ |
| 10 | 5 | 15 | 40 | ✓ |

全部满足（除例外 4）⇒ **`is_heap_except_up(H, 4)` 成立** ✓。

**验证 `grandparent_check(H, 4)`**：`i = 4`，`gp = 4/2 = 2`，`left = 8`、`right = 9`。两个孩子都存在（`9 < 11`）。需要：

- `ok_above(H, 2, 8)`：`data[2] = 10 ≤ data[8] = 5`？**✗ 不成立。**
- `ok_above(H, 2, 9)`：`10 ≤ 6`？**✗ 不成立。**

⇒ **`grandparent_check(H, 4)` 不成立** ✓。

**交换位置 4 与位置 2**：

数组变成 `[_, 0, 3, 1, 10, 15, 20, 30, 5, 6, 40]`。

**树形**：

```
              0 (1)
           /         \
       3 (2)         1 (3)
       /    \        /    \
  10 (4)  15 (5)  20 (6)  30 (7)
   /  \    /
5 (8) 6(9) 40(10)
```

**检查位置 4 与它的孩子**：

- `ok_above(H, 4, 8)`：`data[4] = 10 ≤ data[8] = 5`？**✗ 违反！**
- `ok_above(H, 4, 9)`：`10 ≤ 6`？**✗ 违反！**

**所以结果不是合法堆** ✓。

**这正是「朴素部分不变式不够强」的后果**：交换修好了「位置 4 比父小」这个违规，但制造了「位置 4 比孩子大」这个新违规。**因为原来的不变式只保证 `data[4] ≤ data[8]`（即 `3 ≤ 5`），没有保证 `data[2] ≤ data[8]`（即 `10 ≤ 5`，不成立）。**

**加上 `grandparent_check` 后**：这个状态会被拒绝（`grandparent_check(H, 4)` 为假），所以 `pq_add` 的循环不变式保证它**不会出现**。**真实运行中，`data[2] ≤ data[8]` 总是成立**（因为位置 8 不是例外，它满足父子序；而位置 2 是位置 4 的父，如果位置 2 也违规，那就不是「只有一个例外」了）。

**答 2.**
假设堆里只有 1 个元素，值为 `X`：`data = [_, X]`、`next = 2`。

**执行 `pq_rem`**：

```c
elem min = H->data[1];       /* min = X */
(H->next)--;                 /* next = 1 */
/* 若无 if 判断： */
H->data[1] = H->data[H->next];   /* data[1] = data[1] = X —— 把 X 写回根！ */
sift_down(H);                     /* 无孩子，什么也不做 */
return min;                       /* 返回 X */
```

**结果**：`next = 1`（逻辑上堆为空），但 `data[1]` 仍然是 `X`。

**这看起来「无害」**——因为 `next = 1` 意味着 `pq_empty` 为真，后续 `pq_add` 会从位置 1 开始写，`data[1]` 的旧值会被覆盖。

**但有两个真实问题**：

1. **`sift_down(H)` 的前置是 `is_heap_except_down(H, 1)`**。当 `next = 1` 时，`is_heap_except_down` 的循环 `for (child = 2; child < 1; ...)` **一次都不执行**，返回 `true`——所以前置成立，无害。

2. **真正的问题在 `data[H->next]` 的读取**。当 `next = 1` 时，`H->data[1]` 是**刚被删除的元素**。虽然读它不会越界，但如果 `elem` 是一个**需要释放的对象**（例如 `pq_rem` 的调用者期望「取出的元素」与「堆里不再有它」），那么把 `min` 又写回 `data[1]` 会造成**悬空引用**——调用者 `free(min)` 之后，`data[1]` 就成了悬空指针。虽然 `next = 1` 使这个位置不可达，但**valgrind 不会报错，问题会潜伏**。

**更严重的情形**：如果 `next` 减到 1 之前是 2，而 `limit` 也是 2（`capacity = 1`），那么 `data[1]` 是唯一元素。**省略 `if` 后，`data[1] = data[1]` 是无操作**——功能上确实无害。

**所以严格说，省略 `if` 在「功能」上不会出错，但**：

- **违反了「删除后不再引用」的原则**（第 17 讲 `free` 的两条限制之一）。
- **如果 `elem` 是拥有资源的对象，会造成逻辑上的「复活」**。
- **讲义的写法更清晰**：`if (H->next > 1)` 明确表达「删除后还有元素才需要修复」。

**结论**：`if` 不能省，主要理由是**语义清晰 + 避免悬空引用**，而非「必然崩溃」。

**答 3.**

| 维度 | `elem[] data`（灵活数组） | `elem *data`（指针） |
|---|---|---|
| 分配次数 | 1 次 | 2 次 |
| free 次数 | 1 次 | 2 次 |
| 泄漏风险 | 低（一次 free） | 高（忘记 free `data` 就泄漏） |
| 缓存局部性 | 好（header 与数据连续） | 差（两块内存分离） |
| `sizeof` 语义 | 不含数组（要手动算） | 含指针本身 |
| 动态扩容 | **困难** | **容易** |
| 拷贝/移动 | 需要 memcpy 整个块 | 只需复制指针 |

**动态扩容的对比**：

**用指针时**，扩容只需：

```c
H->data = xrealloc(H->data, new_limit * sizeof(elem));
H->limit = new_limit;
```

**用灵活数组时**，扩容必须：

```c
heap H2 = xmalloc(sizeof(struct heap_header) + new_limit * sizeof(elem));
H2->limit = new_limit;
H2->next  = H->next;
H2->prior = H->prior;
memcpy(H2->data, H->data, H->next * sizeof(elem));   /* 复制有效元素 */
free(H);
return H2;    /* 注意：调用者的 H 指针失效！ */
```

**问题**：`pq_add` 的签名是 `void pq_add(heap H, elem e)`，**无法返回新指针**。所以灵活数组版本**不能透明地扩容**——必须改成 `heap pq_add(heap H, elem e)`（返回可能的新指针），或者要求调用者预先给足容量。

**这就是讲义选择「有界」的原因**（第 25 讲）：`pq_new(capacity, prior)` 明确容量，`pq_add` 前置 `!pq_full(H)`，**从根本上避免了扩容问题**。

**如果必须无界**：用 `elem *data` + `xrealloc` 更简单。**代价是两次分配/两次 free。**

**结论**：**有界 + 灵活数组**是讲义的选择（简单、安全、缓存友好）；**无界 + 指针**是另一种合理选择（灵活但多一次分配）。**没有绝对优劣，取决于需求。**

**答 4.**
`n = 1000`。堆高度 `h = ⌊log₂ 1000⌋ + 1 = 9 + 1 = 10`。

**`pq_add` 最坏情况**：新元素从叶子（第 10 层）一路升到根（第 1 层），需要 `10 − 1 = 9` 次 `swap_up`。

**每次 `swap_up` 的比较次数**：循环条件 `i > 1 && !ok_above(H, i/2, i)` 里，`ok_above` 调用一次 `prior`。所以**每次迭代 1 次比较**。

**总计**：`9` 次 `swap_up`，`9` 次比较（加上最后退出时的那次失败比较，共 **10** 次 `prior` 调用）。

**`pq_rem` 最坏情况**：sift down 从根到叶子，`9` 层。

**每次迭代的比较次数**：

1. `child_to_swap_up`：若有两个孩子，比较 `ok_above(H, left, right)` —— **1 次**。
2. `done_sifting_down`：比较 `ok_above(H, i, left)` 和 `ok_above(H, i, right)` —— **2 次**（若 `done_sifting_down` 在 `child_to_swap_up` 之前调用，如讲义第 13 页的写法）。

**讲义的 `sift_down` 顺序**：

```c
if (done_sifting_down(H, i)) return;      /* 最多 2 次比较 */
int p = child_to_swap_up(H, i);           /* 最多 1 次比较 */
swap_up(H, p);                            /* 0 次比较 */
i = p;
```

**每层最多 3 次比较**。

**总计**：`9` 层 × 3 = **27** 次 `prior` 调用（最坏）。

**注意**：`swap` 本身不比较。所以「`swap` 次数」是 `9` 次，「比较次数」是 `27` 次。**这两个数字不同，题目问的是两个不同的量。**

**简化版实现**（6.2 节示例一的写法，把「选孩子」与「判断是否停止」合并）：

```c
while (2*i < H->next) {
  int child = left;
  if (right < H->next && ok_above(H, right, left)) child = right;  /* 1 次 */
  if (ok_above(H, i, child)) break;                                /* 1 次 */
  swap(H, i, child);
  i = child;
}
```

**每层 2 次比较**，总计 `9 × 2 = 18` 次。**比讲义的写法少 9 次**——因为讲义的 `done_sifting_down` 和 `child_to_swap_up` 有重复判断。

**这是「可读性 vs 效率」的取舍**：讲义为了证明清晰把逻辑拆成两个谓词（每个都是独立可验证的），代价是少量重复比较。**在形式化验证的语境下，这个代价值得付。**

**答 5.**
设堆有 `n` 个节点，高度 `h = ⌊log₂ n⌋`（从 0 数，叶子在第 `h` 层）。

**第 `k` 层**（`0 ≤ k ≤ h`）有 `2^k` 个节点（最后一层可能不满，但**上界**是 `2^k`）。

**第 `k` 层节点的 sift down 代价**：从第 `k` 层下降到第 `h` 层，最多 `h − k` 层，每层 O(1)。所以代价是 `O(h − k)`。

**总代价**：

```
T(n) = Σ_{k=0}^{h} 2^k · (h − k)
```

**换元**：令 `j = h − k`，则 `k = h − j`，`j` 从 `h` 到 `0`：

```
T(n) = Σ_{j=0}^{h} 2^(h−j) · j = 2^h · Σ_{j=0}^{h} j / 2^j
```

**已知级数**：`Σ_{j=0}^{∞} j / 2^j = 2`（这是一个标准结果，可由 `Σ j x^j = x/(1−x)²` 在 `x = 1/2` 处取值得到：`(1/2)/(1/2)² = 2`）。

**所以**：

```
T(n) ≤ 2^h · 2 = 2^(h+1)
```

**而 `2^h ≤ n`**（第 `h` 层最多 `2^h` 个节点，总节点数 `n ≥ 2^h`……严格说 `n ≥ 2^h` 因为前 `h` 层全满有 `2^h − 1` 个，加上第 `h` 层至少 1 个，所以 `n ≥ 2^h`）。

**因此**：

```
T(n) ≤ 2 · 2^h ≤ 2n = O(n)
```

**证毕** ✓。

**直觉解释**：**大部分节点在底层，而底层节点的 sift down 几乎不用动。**

- 第 `h` 层：约 `n/2` 个节点，每个代价 0（叶子，不用 sift）。
- 第 `h−1` 层：约 `n/4` 个节点，每个代价 1。
- 第 `h−2` 层：约 `n/8` 个节点，每个代价 2。
- ……

**总代价** `≈ n/4 · 1 + n/8 · 2 + n/16 · 3 + … = n · Σ k/2^(k+1) = n · 1 = O(n)`。

**对比「逐个插入建堆」**：`n` 次 `pq_add`，每次 O(log n)，总计 **O(n log n)**。**Floyd 法快了一个 log 因子。**

**为什么逐个插入慢**：它从「空堆」开始，每次插入的元素都要从**底部**上滤到可能很高的位置。而 Floyd 法从**底部**开始，大量元素根本不需要动。

**注意**：Floyd 建堆**只能建堆**，不能用来「动态维护堆」——因为它是批量的、一次性的。如果需要「边插入边取最小」（例如优先队列的常规用法），还是得用 `pq_add`。

</details>

## 12. 进一步学习

- 上一讲：[[15-122-25-Priority-Queues]] —— 优先队列接口与堆的两条不变式；本讲是它的「标准 C 实现 + 完整验证」版本。
- 回顾：[[15-122-24-Union-Find]] —— 另一个「用不变式论证复杂度」的数据结构（高度引理 + 路径压缩）。
- 回顾：[[15-122-23-Spanning-Trees]] —— Prim 算法需要优先队列；本讲的堆是它的高效实现。
- 回顾：[[15-122-22-Graph-Search]] —— DFS 的三条正确性不变式，与本讲的「部分不变式」是同一种论证风格。
- 回顾：[[15-122-16-AVL-Trees]] —— 另一个「临时违反 → 旋转修复」的例子；对比 sift up/down 与 rotate_left/right。
- 回顾：[[15-122-17-Introduction-to-C]] —— 标准 C 的起点；`lib/contracts.h`、`xmalloc`、valgrind。
- 回顾：[[15-122-18-C-Memory-Model]] —— 灵活数组成员与 `sizeof` 的关系。
- 回顾：[[15-122-01-Contracts]] —— 契约与循环不变式的基础。
- 课程入口：[[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]]、[[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 术语查询：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Heap、Invariant、Loop Invariant、Sift Up/Down、Flexible Array Member 等条目）。
