---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: L13
topic: Join Algorithms — Nested Loop, Sort-Merge, Hash Join
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 数据库
  - 连接算法
  - 嵌套循环连接
  - 排序归并连接
  - 哈希连接
  - GRACE Hash Join
---

# 15-445 L13：连接算法（Join Algorithms）

> 上一讲讲的两个算子（排序、聚合）都是**单表**操作。本讲进入关系数据库最核心、也最昂贵的算子：**连接（join）**。规范化（normalization）把信息拆到多张表以避免冗余，连接再把它们拼回来——**没有连接就没有关系模型**。连接也是查询优化器花最多时间的地方：同一句 SQL 可以有五种执行算法，代价相差**四个数量级**（本讲例题里朴素嵌套循环 1.3 小时 vs 哈希连接 0.45 秒）。

## 1. 本节学习目标

学完本讲，你应该能够：

1. 说明为什么必须连接（规范化与信息重构），以及为什么本讲只讨论**二元内等值连接（binary inner equijoin）**。
2. 区分连接的两种输出方式——**早物化（early materialization）** 与**晚物化（late materialization）**，并说明各自适合行存还是列存。
3. 写出五种连接算法的 I/O 代价公式，并说明每个公式中每一项的来源。
4. 推导 **block nested loop join** 的 `M + (⌈M/(B-2)⌉ × N)`，解释为什么是 `B-2` 而不是 `B`。
5. 说明 **index nested loop join** 的 `M + (m × C)` 在什么条件下优于 block nested loop join，什么条件下反而更差。
6. 推导 **sort-merge join** 的总代价（两个排序 + 一次归并），并说明它的最坏情况（连接键全部相同）为什么是 `M × N`。
7. 推导 **Grace/partitioned hash join** 的 `3(M+N)`，并说明 `2(M+N)` 与 `M+N` 各自的来源。
8. 说明 **recursive partitioning** 的必要性与「必须换哈希函数」的原因。
9. 说明 **probe filter（布隆过滤器）** 如何减少探测开销，以及它为什么叫 **sideways information passing**。
10. 说明 **hybrid hash join** 的优化思路与它在实践中「很少实现」的原因。
11. 手算讲义例题（`M=1000, m=100000, N=500, n=40000, B=100, 0.1ms/IO`）中五种算法的耗时，并排序。
12. 给出「哈希 vs 排序」的选择准则（至少三条）。

## 2. 前置知识

- **外部归并排序**：见 [[15-445-11-Sorting-and-Aggregation]]；sort-merge join 的排序阶段直接调用它，`2M × (1 + ⌈log_{B-1}⌈M/B⌉⌉)` 就是那里的公式。
- **哈希表**：见 [[15-445-07-Hash-Tables]]；哈希连接的 build 阶段就是建哈希表，讲义明确说「实践中线性探查最好」。
- **布隆过滤器**：见 [[15-445-09-Indexes-and-Filters-II]]；probe filter 就是它，假阳性可以接受、假阴性绝不允许。
- **B+ 树与聚簇索引**：见 [[15-445-08-Indexes-and-Filters-I]]；index NLJ 依赖索引，sort-merge 可以复用聚簇索引的有序性。
- **缓冲池与替换策略**：见 [[15-445-04-Memory-Management]]；所有 `B` 都指分给该算子的缓冲页数，Grace hash join 的动机就是「不让缓冲池随机换出哈希表页」。
- **查询计划与算子树**：见 [[15-445-11-Sorting-and-Aggregation]] 第 5.14 节。
- **页与记录 id**：见 [[15-445-03-Database-Storage-I]]；晚物化输出的就是 record id。

## 3. 核心概念

### 3.1 Join（连接）

把两张表中满足连接谓词（join predicate）的元组配对，并把它们**拼接（concatenate）** 成新的输出元组。本讲聚焦**二元内等值连接（binary inner equijoin）**：只有两张表、只保留匹配的行、谓词是等号。

### 3.2 Outer Table / Inner Table（外表 / 内表）

嵌套循环中的外层循环遍历的表叫**外表（outer table）**，内层循环遍历的叫**内表（inner table）**。讲义的经验法则：**让较小的表当外表**（一般按**页数**衡量，有时也按元组数）。查询优化器在生成物理计划时会尝试决定这个顺序。

### 3.3 Early Materialization（早物化）

连接算子把外表与内表匹配元组的**所有属性值**复制进一个新的输出元组。优点是后续算子不必回基表取数据；缺点是物化整行的内存开销大。适合**行存（row store）**——反正整行都要读进内存。

### 3.4 Late Materialization（晚物化）

连接算子只复制**连接键**与匹配元组的 **record id**。优点是避免把查询不需要的列带进内存，适合**列存（column store）**；缺点是后续算子要按 record id 回表。

### 3.5 Cost Metric（代价度量）

本讲用**磁盘 I/O 次数**作为代价度量。忽略计算与网络开销（磁盘导向 DBMS 中 I/O 占主导），也**忽略输出结果的 I/O**（因为输出量取决于数据，对所有算法都一样）。

### 3.6 Naïve Nested Loop Join（朴素嵌套循环连接）

两层 `for` 循环，外层遍历 R 的每个**元组**，内层遍历 S 的每个**元组**，逐对比较。对 R 的每个元组都要**完整扫描一遍 S**，没有任何缓存或访问局部性。讲义标注 **"Don't Do This!"**。

### 3.7 Block Nested Loop Join（块嵌套循环连接）

外层按**页（block）** 遍历 R，对 R 的每一页完整扫描一遍 S，页内所有元组两两比较。因为「按页扫描」而不是「按元组扫描」，磁盘访问次数大幅下降。

### 3.8 Index Nested Loop Join（索引嵌套循环连接）

外表顺序扫描，内表**用索引探测（index probe）** 代替顺序扫描。索引可以是已有的，也可以为本次连接临时建。

### 3.9 Sort-Merge Join（排序归并连接）

先把两张表按连接键排序，然后用两个游标同步推进、输出匹配元组（类似归并排序的 merge 阶段）。当连接键有重复时，需要**回溯游标（backtrack）**。

### 3.10 Hash Join（哈希连接）

用哈希表按连接属性把元组分到桶里，使 R 的桶 `ri` 只需与 S 的桶 `si` 比较，从而把比较次数从 `m × n` 降到接近 `m + n`。**只能用于完整连接键上的等值连接**。

### 3.11 Build Phase / Probe Phase（构建阶段 / 探测阶段）

哈希连接的两阶段：**Build** 扫描外表建哈希表；**Probe** 扫描内表，用同一个哈希函数跳到哈希表对应位置找匹配。

### 3.12 Probe Filter（探测过滤器）

在 build 阶段顺便建一个**布隆过滤器**，probe 阶段先查过滤器再查哈希表。过滤器小到能放进 CPU cache，所以比查哈希表快；它回答「这个键**肯定不在**」或「**可能在**」。

### 3.13 Sideways Information Passing（侧向信息传递）

通过**额外的元数据**（如布隆过滤器）把一个算子的信息传给另一个算子，以减少不必要的数据读取。probe filter 是它的一个实例。

### 3.14 Grace Hash Join / Partitioned Hash Join（GRACE 哈希连接 / 分区哈希连接）

哈希表装不进内存时的哈希连接。**Partition 阶段**：用同一个哈希函数 `h1` 把两张表都分到 `k` 个磁盘桶；**Probe 阶段**：逐对读入对应桶，在内存里做哈希连接。名字来自 1980 年代日本东京大学的 **GRACE 数据库机**。

### 3.15 Recursive Partitioning（递归分区）

若某个桶分区后仍装不进内存，就用**另一个**哈希函数 `h2`（`h2 ≠ h1`）对它再分区，可反复递归直到能装下。

### 3.16 Hybrid Hash Join（混合哈希连接）

若缓冲池比分区数 `k` 大，就把多出来的页用于**第一个分区的内存连接**，其余分区照常落盘。相当于「基本哈希连接」与「GRACE 哈希连接」的自适应混合。

## 4. 通俗理解

- **连接 = 把拆散的档案重新配对**。图书馆为了不重复记录，把「读者信息」和「借阅记录」分两张表存（规范化）。要查「谁借了哪本书」，就得按读者 ID 把两张表配对——这就是连接。
- **朴素嵌套循环 = 用最笨的办法查字典**。对名单上的每个人，你从词典第一页翻到最后一页找一个名字。100 个人就要翻 100 遍词典。**块嵌套循环 = 一次记住一页词典**：翻词典时把整页记住，一页上的 20 个名字一起查完再翻下一页。**索引嵌套循环 = 直接用拼音索引**：不翻页，直接跳到那个词。
- **排序归并 = 两副已排好的扑克牌对着走**。两副牌都从小到大排好，各拿一张比大小：小的往前走，相等就配对输出。若同一数值有多张（重复键），就得**退回去**再配一遍——这就是 backtrack。
- **哈希连接 = 按区号分信件**。要配对「寄件人」和「收件人」，先按区号把所有信分到不同格子（build），然后对每个收件人也算出区号、直接去那个格子找（probe）。不必两两比对全部信件。
- **GRACE 哈希连接 = 格子装不下就先分箱**。信件太多，桌子放不下所有格子，那就先按区号把信装进不同的箱子堆到地上（partition 落盘），然后一次只拿一个箱子到桌上处理（probe）。每个箱子内部再做一次精细分格。
- **Probe filter = 门口先看名单**。查哈希表要翻页（cache miss），但门口贴一张小纸条（布隆过滤器，能放进 cache）写着「这些人肯定不在」。先看纸条，能挡掉大部分白跑一趟的人。
- **Hybrid = 把最常用的那个箱子留在桌上**。既然桌子（缓冲池）还有空位，就把最大的那个箱子（第一个分区）直接留在桌上处理完，其他箱子再堆到地上。

具体数字（讲义例题，`M=1000, m=100000, N=500, n=40000, B=100`，每次 I/O 0.1 ms，4 KB 页 → R 约 6 MB）：

| 算法 | I/O 次数 | 耗时 |
|---|---|---|
| 朴素嵌套循环 | `1000 + 100000×500 = 50,001,000` | **1.3 小时** |
| 块嵌套循环（`B=102`） | `1000 + 10×500 = 6,000` | 0.6 秒 |
| 排序归并 | `4000 + 2000 + 1500 = 7,500` | 0.75 秒 |
| 哈希连接 | `3×(1000+500) = 4,500` | **0.45 秒** |

**最笨与最快的差距是 10,000 倍以上。**

## 5. 原理与推导

### 5.1 为什么必须连接：规范化与信息重构

讲义第 5 页：

```
We normalize tables in a relational database to avoid unnecessary
repetition of information.
We then use the join operator to reconstruct the original tuples without
any information loss.
```

**逻辑链条**：

```
1. 好的数据库设计要求「最小化不必要的信息重复」（normalization theory）
2. 因此表被拆分（decomposed）到多张表中
3. 拆分后，单表查询无法回答跨表问题
4. 必须用 join 把原始元组无信息损失地重构（reconstruct）
```

**推论**：**连接是规范化的代价**。规范化省了存储与更新异常，代价是查询时要付连接开销。这就是为什么「反规范化（denormalization）」在某些 OLAP 场景仍然流行——用冗余换掉连接。

### 5.2 本讲的范围：二元内等值连接

讲义第 6 页：

```
We will focus on performing binary joins (two tables) using inner
equijoin algorithms.
  → These algorithms can be tweaked to support other joins.
  → Multi-way joins exist primarily in research literature
    (e.g., worst-case optimal joins).
```

**三个限定词**：

| 限定 | 含义 | 为什么这样限定 |
|---|---|---|
| **binary（二元）** | 只连两张表 | 多表连接可以分解成一系列二元连接（左深树 / 浓密树），所以二元算法是基础 |
| **inner（内）** | 只输出匹配的行 | 外连接（LEFT/RIGHT/FULL）可以看作「内连接 + 补上未匹配行」，后者用同样的算法加一个标记位 |
| **equijoin（等值）** | 谓词是 `=` | 只有等值连接才能用哈希；非等值（`<`、`>`）只能靠嵌套循环或排序归并 |

**多路连接**：讲义说主要存在于研究文献，例如 **worst-case optimal joins**（Ngo、Ré、Rudra 等人 2018 年的工作），对三角形查询这类多路连接能证明比二元分解更优。工业界主流仍是二元分解。

**外表选择**：讲义明确「一般希望较小的表总是查询计划中的**左表（外表）**」，由优化器决定。

### 5.3 输出设计：早物化 vs 晚物化

讲义第 9–19 页。给定 `r ∈ R` 与 `s ∈ S` 在连接属性上匹配，连接算子把 `r` 与 `s` **拼接**成新元组。输出内容有三种依赖：**处理模型（processing model）**、**存储模型（storage model）**、**查询本身的数据需求**。

**方式一：早物化（Data / Early Materialization）**

```
Copy the values for the attributes in outer and inner tuples into a new
output tuple.
Subsequent operators in the query plan never need to go back to the base
tables to get more data.
```

```
R(id,name)          S(id,value,cdate)
  abc                123  1000  10/19/26
                     123  2000  10/19/26

        连接输出（早物化）:
        R.id | R.name | S.id | S.value | S.cdate
        abc  |  abc   | 123  |  1000   | 10/19/26
        abc  |  abc   | 123  |  2000   | 10/19/26
```

- **优点**：后续算子（filter、project、aggregate）不需要回基表，**零额外 I/O**。
- **缺点**：物化整行的内存开销大；对宽表尤其浪费（查询只要两列却复制了全部）。
- **适合**：**行存**——反正整行都要读进内存，复制整行不额外增加 I/O。
- **进一步优化**：DBMS 可以**省略后续不再需要的属性**，只复制查询真正用到的列。

**方式二：晚物化（Record IDs / Late Materialization）**

```
Only copy the join keys along with the Record IDs of the matching tuples.
Ideal for column stores because the DBMS does not copy data that is not
needed for the query.
```

```
        连接输出（晚物化）:
        R.id | R.RID | S.id | S.RID
        abc  |  ###  | 123  |  ###
        abc  |  ###  | 123  |  ###
              ↑ 只存 record id，不复制值
```

- **优点**：连接算子只搬运键与 id，数据量极小；**列存**下尤其划算（不把无关列读进内存）。
- **缺点**：后续算子要按 record id **回表**，产生随机 I/O。
- **适合**：**列存** + 查询只需要少数列。

**实践**：讲义 notes 强调「真实系统中 DBMS 常常**混合使用**两种方式」，取决于元组数、列数与后续算子。例如：连接输出只带键 + id（晚物化），但若下一层是聚合且只需要键，就完全不用回表。

**与第 11 讲排序的对照**：那里「早/晚物化」指 run 里存整行还是存键 + id；这里指连接输出存整行还是存键 + id。**同一权衡、同一命名**——都是「尽早丢弃不需要的数据，把回表推到最后一刻」。

### 5.4 代价模型：为什么只算 I/O

讲义第 20 页：

```
Given a query that joins table R with table S, assume the DBMS has the
following information those tables:
  → M pages in table R, m tuples in R
  → N pages in table S, n tuples in S

Cost Metric: # of I/Os to compute join
  → Ignore result output costs because it depends on the data and is the
    same for all algorithms.
  → Ignore computation / network costs (for now).
```

**约定**（后续所有公式都用这套符号）：

| 符号 | 含义 |
|---|---|
| `M` | 外表 R 的**页数** |
| `m` | 外表 R 的**元组数** |
| `N` | 内表 S 的**页数** |
| `n` | 内表 S 的**元组数** |
| `B` | 分给该连接算子的**缓冲页数** |
| `C` | 一次索引探测的代价（以 I/O 计，通常是树高） |

**为什么忽略输出代价**：输出行数取决于数据分布（连接的选择性），对五种算法**完全一样**，所以在比较算法时可以约掉。这是代价模型设计的常见手法：**只保留区分度高的项**。

**为什么忽略 CPU**：磁盘导向 DBMS 中一次 I/O（0.1 ms 到 10 ms）比一次比较（纳秒级）贵 5–8 个数量级。所以 I/O 主导。**但这个假设在内存数据库里失效**——那时 CPU 成为瓶颈，算法选择会反过来（见第 5.12 节的讨论）。

### 5.5 连接 vs 笛卡尔积

讲义第 21 页：

```
R⨝S is the most common operation and thus must be carefully optimized.
R×S followed by a selection is inefficient because the cross-product is
large.
  → These types of joins are rare and there is no magic algorithm to make
    this go faster.
There are many algorithms for reducing join cost, but no algorithm works
well in all scenarios.
```

**定量**：`m = 100,000`、`n = 40,000` 时，笛卡尔积有 `4 × 10⁹` 行。若每行 100 字节 → **400 GB**。然后再用选择把 99.99% 丢掉——**这是纯粹的浪费**。

**推论**：连接算法的全部智慧都在于「**避免产生不匹配的配对**」。五种算法的区别就是**用什么手段提前排除不可能匹配的组合**：

| 算法 | 排除手段 |
|---|---|
| 朴素嵌套循环 | 无（最笨） |
| 块嵌套循环 | 用页缓存减少重复 I/O（但仍比较全部配对） |
| 索引嵌套循环 | 用索引直接跳到匹配位置 |
| 排序归并 | 用有序性提前终止（`cursorR < cursorS` 就推进 `cursorR`） |
| 哈希连接 | 用哈希分桶，只比较同桶 |

**「no algorithm works well in all scenarios」** 是本讲的中心思想——所以好的 DBMS 实现全部五种，由优化器选。

### 5.6 朴素嵌套循环连接：`M + (m × N)`

讲义第 23–32 页。伪代码：

```
for tuple r ∈ R:
  for tuple s ∈ S:
    if r and s match: emit
```

**代价推导**：

```
外层扫描 R 一遍:              M 次 I/O
对 R 的每一个元组（共 m 个）:
    完整扫描 S 一遍:          N 次 I/O
内层总 I/O:                   m × N

总 I/O = M + (m × N)
```

**为什么是 `M + m×N` 而不是 `(M×N)`**：外层只扫一遍 R（M 页），但内层要扫 m 遍 S（每遍 N 页）。

**讲义例题**：

```
Table R: M = 1000, m = 100,000
Table S: N = 500,  n = 40,000

以 R 为外表:
  M + (m × N) = 1000 + (100000 × 500) = 50,001,000 次 I/O
  0.1 ms/IO → 约 1.3 小时

以 S 为外表（换小表当外表）:
  N + (n × M) = 500 + (40000 × 1000) = 40,000,500 次 I/O
  0.1 ms/IO → 约 1.1 小时
```

**换外表只从 1.3 小时降到 1.1 小时**——因为 `m×N` 与 `n×M` 量级相同（都约等于 `m×N`，当 `m/N ≈ n/M` 即两表元组密度相近时）。这说明**朴素嵌套循环的根本问题不是外表选错，而是「每个元组扫一遍内表」这个结构本身**。

讲义第 32 页标注「4 KB pages → 6 MB」：R 有 1000 页 × 4 KB = 4 MB，S 有 500 页 × 4 KB = 2 MB，合计 6 MB——**两张表总共只有 6 MB，却要跑 1.3 小时**。这是最刺眼的反差：数据量极小，代价极大，纯粹因为算法结构。

### 5.7 块嵌套循环连接：`M + (M × N)` 与 `M + (⌈M/(B-2)⌉ × N)`

**基本版**（第 33–35 页）：

```
for page pR ∈ R:
  for page pS ∈ S:
    for tuple r ∈ pR:
      for tuple s ∈ pS:
        if r and s match: emit
```

```
This algorithm performs fewer disk accesses.
  → For every block in R, it scans S once.
Cost: M + (M × N)
```

**代价变化**：`m × N` → `M × N`。因为内层循环从「每个**元组**扫一遍 S」变成「每个**页**扫一遍 S」。

**定量收益**：若每页装 `m/M = 100` 个元组，则内层 I/O 从 `100,000 × 500` 降到 `1000 × 500`——**减少 100 倍**。

**外表选择的关键变化**（第 35 页）：

```
The smaller table should be the outer table.
We determine size based on the number of pages, not the number of tuples.
```

**为什么按页数而不按元组数**：代价公式是 `M + (M × N)`，`M` 出现两次（一次作为外层扫描、一次作为内层重复次数），所以**外表页数越小越好**。若两表页数与元组数的相对大小不一致（例如 R 页少但元组多，因为元组小），按元组数选会选错。

**用满缓冲池的版本**（第 36–40 页）：

```
If we have B buffers available:
  → Use B-2 buffers for each block of the outer table.
  → Use one buffer for the inner table, one buffer for output.
```

```
for B-2 pages pR ∈ R:
  for page pS ∈ S:
    for tuple r ∈ B-2 pages:
      for tuple s ∈ pS:
        if r and s match: emit
```

```
Cost: M + (⌈M / (B-2)⌉ × N)
```

**为什么是 `B-2`**：

```
B 个缓冲页
  - 1 页：内表 S 的当前扫描页（每轮都要换）
  - 1 页：输出缓冲（攒满再写）
  ─────
  = B-2 页：可以一次装下外表的 B-2 页作为一个「大块」
```

于是外层不再「一页一页」扫，而是「一次 `B-2` 页」，外层块数变成 `⌈M/(B-2)⌉`，内层扫描次数随之降到 `⌈M/(B-2)⌉`。

**两个极端情形**：

```
情形 1：外表完全装进内存（M < B-2）
  → 外层只需读一遍，内层也只需读一遍
  → Cost = M + N = 1000 + 500 = 1500 次 I/O
  → 0.1 ms/IO → 约 0.15 秒

情形 2：B = 102（即 B-2 = 100）
  → Cost = 1000 + ⌈1000/100⌉ × 500 = 1000 + 10 × 500 = 6000 次 I/O
  → 若换内外表: 500 + ⌈500/100⌉ × 1000 = 500 + 5 × 1000 = 5500 次 I/O
```

**注意情形 2 的细节**：`B=102` 时 `⌈M/(B-2)⌉ = ⌈1000/100⌉ = 10`；换成 S 当外表则是 `⌈500/100⌉ = 5`。**这次换外表确实省了 500 次 I/O**（6000 → 5500），因为 `⌈M/(B-2)⌉` 与 `⌈N/(B-2)⌉` 的比值不再是 1。

**从 1.3 小时到 0.15 秒**：`M < B-2` 时块嵌套循环只需 1500 次 I/O，比朴素版快 **33,000 倍**。这就是「按页循环」的威力——**同一个算法思想，粒度差 100 倍，结果差 4 个数量级**。

### 5.8 索引嵌套循环连接：`M + (m × C)`

**动机**（第 41–42 页）：

```
Why is the basic nested loop join so bad?
  → For each tuple in the outer table, we must do a sequential scan to
    check for a match in the inner table.
We can avoid sequential scans by using an index to find inner table matches.
  → Use an existing index for the join.
```

**关键洞察**：块嵌套循环虽然减少了 I/O，但**仍然要比较全部配对**（`m × n` 次比较）。索引嵌套循环则**从根本上消除了「扫描」这个动作**——直接跳到匹配位置。

```
for tuple r ∈ R:
  for tuple s ∈ Index(ri = sj):
    if r and s match: emit
```

```
Assume the cost of each index probe is some constant C per tuple in the
outer table.
Cost: M + (m × C)
```

**`C` 的含义**：一次索引探测的 I/O 次数，通常等于**B+ 树的树高**（3–4 层）。若索引是聚簇的且数据在缓存里，`C` 可以低到 1；若索引非聚簇且数据冷，`C` 可能是 4 次 I/O（3 层树 + 1 次回表）。

**内表必须是带索引的那张**（讲义明确）：因为「每个外表元组探一次索引」，索引必须建在**内表**的连接键上。若索引在外表上，应该交换内外表。

**索引来源**：可以是**已有索引**，也可以是**为本次连接临时建的索引**（建索引的代价要计入，但如果连接要重复执行或外表很大，摊销后仍划算）。

**什么时候最优**：

```
Index NLJ 代价:        M + (m × C)
Block NLJ 代价:        M + (⌈M/(B-2)⌉ × N)

Index 更优 ⟺ m × C < ⌈M/(B-2)⌉ × N
```

**例题**（`M=1000, m=100000, N=500, B=102`）：

```
Block NLJ:  1000 + 10 × 500 = 6,000
Index NLJ:  1000 + 100000 × C
  → 要优于 block NLJ 需 C < 0.05
  → 但 C 至少是 1（一次探测至少一次 I/O）
  → 所以此例中 index NLJ 反而更差: 1000 + 100000 × 1 = 101,000
```

**这个反直觉的结果非常重要**：index NLJ **不是总更快**。它的优势场景是：

| 场景 | 为什么 index NLJ 好 |
|---|---|
| 外表**元组数很少**（如 `m = 100`） | `m × C` 很小 |
| 内表**很大**且索引选择性高 | block NLJ 的 `N` 很大 |
| 索引**完全在缓存里**（`C ≈ 0`） | 探测几乎无 I/O |
| 内表有**聚簇索引**且匹配行相邻 | 一次探测取回多行，摊薄 `C` |

**劣势场景**：

| 场景 | 为什么差 |
|---|---|
| 外表元组数巨大（`m` 大） | `m × C` 线性增长 |
| 索引非聚簇、匹配行稀疏 | 每次探测都是随机 I/O |
| 索引不存在且内表小 | 建索引的代价超过收益 |
| 连接键选择性差（大量重复） | 一次探测返回大量行，接近全表扫描 |

### 5.9 排序归并连接：两阶段与回溯

**Phase #1：Sort**（第 46 页）：

```
Sort both tables on the join key(s).
  → You can use any appropriate sort algorithm
  → These phases are distinct from the sort/merge phases of an external
    merge sort, from the previous class
```

**注意讲义的这个澄清**：sort-merge join 的「Sort 阶段 / Merge 阶段」与外部归并排序的「Phase #1 Sorting / Phase #2 Merging」**是两回事**。前者是「先排两张表、再归并连接」；后者是「先排成 run、再归并 run」。名字撞车但语义不同。

**Phase #2：Merge**（第 46–47 页）：

```
Step through the two sorted tables with cursors and emit matching tuples.
  → May need to backtrack depending on the join type.
```

```
sort R,S on join keys
cursorR ← Rsorted, cursorS ← Ssorted
while cursorR and cursorS:
  if cursorR > cursorS:
    increment cursorS
  if cursorR < cursorS:
    increment cursorR
  backtrack cursors (if necessary)
  elif cursorR and cursorS match:
    emit
  increment cursorS
```

**逐句解释**：

- `cursorR > cursorS`：R 的当前键更大，说明 S 落后了 → 推进 S。
- `cursorR < cursorS`：R 落后 → 推进 R。
- **`backtrack cursors (if necessary)`**：这是与普通归并排序**唯一的本质区别**。归并排序的输入是两个已排序序列，每个元素只需输出一次；而连接中**键可以重复**，一个 R 元组可能匹配**多个** S 元组。所以当 `cursorS` 前进到不匹配时，若 `cursorR` 还有同键的元组，就要把 `cursorS` **退回到该键的第一个 S 元组**重新扫描。
- `emit` 后 `increment cursorS`：继续找 R 当前键的下一个匹配。

**讲义的完整示例**（第 48–73 页）：

```
排序后的 R:             排序后的 S:
  id   name               id   value  cdate
  100  Andy               100  2222   10/19/26
  200  GZA                100  9999   10/19/26
  200  GZA                200  8888   10/19/26
  400  ODB                400  6666   10/19/26
  500  Raekwon            500  7777   10/19/26
  500  RZA
  500  MethodMan
  500  Ghostface
```

执行轨迹（讲义用 `Last Value:` 标注状态）：

```
Last Value: ---
  比较 R(100, Andy) vs S(100, 2222) → 匹配 → emit (Andy, 2222)
  比较 R(100, Andy) vs S(100, 9999) → 匹配 → emit (Andy, 9999)
Last Value: 100

  cursorS 越过 100，到 S(200, 8888)
  R 推进到 R(200, GZA)
  匹配 → emit (GZA, 8888)
Last Value: 200
  R 还有第二个 (200, GZA) → **backtrack cursorS 回到 S(200, 8888)**
  匹配 → emit (GZA, 8888)   ← 同一个 S 元组被输出两次
Last Value: 200

  R 推进到 R(400, ODB)，S 推进到 S(400, 6666)
  匹配 → emit (Raekwon 200, 6666)  ← 讲义此处标注略有错位，见下方待核实
Last Value: 400

  R 推进到 R(500, Raekwon)，S 推进到 S(500, 7777)
  匹配 → emit (RZA, 7777)
Last Value: 500
```

**backtrack 的必要性定量**：R 中 `id=200` 有 2 个元组、S 中 `id=200` 有 1 个 → 输出 2 行；R 中 `id=500` 有 4 个元组、S 中 `id=500` 有 1 个 → 输出 4 行。若不 backtrack，每个 S 元组只能与 R 的第一个同键元组配对，**漏掉其余匹配**。

**代价公式**（第 74–76 页）：

```
Sort Cost (R): 2M ∙ (1 + ⌈ log_{B-1} ⌈M / B⌉ ⌉)
Sort Cost (S): 2N ∙ (1 + ⌈ log_{B-1} ⌈N / B⌉ ⌉)
Merge Cost: (M + N)
Total Cost: Sort + Merge
```

**三项的来源**：

1. **`2M × (1 + ⌈log_{B-1}⌈M/B⌉⌉)`**：R 的外部归并排序代价（第 11 讲公式），`2M` 是「每趟读写全表」。
2. **`2N × (...)`**：S 的外部归并排序代价。
3. **`M + N`**：归并阶段各扫一遍两张表。

**最坏情况**（第 76 页）：

```
The worst case for the merging phase is when the join attribute of all
the tuples in both relations contains the same value.
Cost: (M ∙ N) + (sort cost)
```

**为什么是 `M × N`**：若两表所有元组的连接键**完全相同**，则每个 R 元组都要与**全部** S 元组配对。backtrack 会把 `cursorS` 反复退回起点，归并退化成嵌套循环。

**但这个最坏情况「very unlikely to happen in real databases」**（notes 原文）。实际中连接键大多近似唯一，所以归并代价可以近似为 `M + N`。

**讲义例题**（第 75 页，`B=100`）：

```
Sort Cost (R) = 2 × 1000 × (1 + ⌈log₉₉⌈1000/100⌉⌉)
             = 2000 × (1 + ⌈log₉₉ 10⌉)
             = 2000 × (1 + 1) = 4000 次 I/O

Sort Cost (S) = 2 × 500 × (1 + ⌈log₉₉⌈500/100⌉⌉)
             = 1000 × (1 + ⌈log₉₉ 5⌉)
             = 1000 × (1 + 1) = 2000 次 I/O

Merge Cost   = 1000 + 500 = 1500 次 I/O

Total = 4000 + 2000 + 1500 = 7500 次 I/O
      = 0.75 秒（0.1 ms/IO）
```

**注意 `⌈log₉₉ 10⌉ = 1`**：`log₉₉ 10 ≈ 0.5`，向上取整为 1。所以 R 的排序只需 **2 个 pass**（Pass #0 产出 `⌈1000/100⌉ = 10` 个 run，Pass #1 一次 99 路归并就够了）。这是 `B=100` 巨大的缓冲带来的好处——**两表都只需两趟排序**。

**什么时候优选 sort-merge**（第 77 页）：

```
Sort-Merge Join is preferable when one of the following conditions are met:
  → One or both tables are already sorted on join key.
  → Output must be sorted on join key.
The input relations may be sorted either by an explicit sort operator, or
by scanning the relation using an index on the join key.
```

**两个条件各自的收益**：

| 条件 | 收益 |
|---|---|
| 一张或两张表**已按连接键有序** | 省掉对应的 `2M × passes` 或 `2N × passes` |
| **输出必须按连接键有序** | 省掉后续的 `ORDER BY` 算子（否则哈希连接后还要再排一次） |

**「已排序」的来源**：显式排序算子，或**用连接键上的索引扫描**（聚簇索引直接给有序数据）。后者让 sort-merge 与 index NLJ 产生协同——**索引既提供了有序输入，又可能是聚簇的**。

### 5.10 哈希连接：Build 与 Probe

**核心洞察**（第 78 页）：

```
If tuple r ∈ R and tuple s ∈ S satisfy the join condition, then they have
the same value for the join attributes.
If that value is hashed to some partition i, the R tuple must be in ri and
the S tuple in si.
Therefore, R tuples in ri need only to be compared with S tuples in si.
```

**逻辑推导**：

```
1. r 与 s 匹配 ⟹ r.key = s.key                （等值连接的定义）
2. 哈希函数是确定性的 ⟹ h1(r.key) = h1(s.key)  （同一输入同一输出）
3. 若 h1(r.key) = i，则 h1(s.key) = i          （由 1、2）
4. 所以匹配的 (r, s) 必然落在同一个桶 i
5. 因此只需比较同桶内的元组，跨桶的配对可以完全跳过
```

**这是哈希连接的正确性证明**，也是它只能用于**等值连接**的原因：第 1 步要求 `r.key = s.key`；若谓词是 `r.key < s.key`，就无法从「同哈希值」推出「满足谓词」。

**基本版**（第 79–85 页）：

```
Phase #1: Build
  → Scan the outer relation and populate a hash table using the hash
    function h1 on the join attributes.
  → We can use any hash table that we discussed before but in practice
    linear probing works the best.
Phase #2: Probe
  → Scan the inner relation and use h1 on each tuple to jump to a location
    in the hash table and find a matching tuple.
```

```
for tuple r ∈ R:
  insert h1(r) into hash table HTR
for tuple s ∈ S:
  if h1(s) ∈ HTR: emit
```

**为什么「实践中线性探查最好」**：第 7 讲讲过线性探查有主聚集（primary clustering）问题，但哈希连接里它反而最优，原因：

1. **顺序访问模式**：线性探查在数组中顺序前进，对 CPU cache 极友好；链地址法要追指针（每次都是潜在 cache miss）。
2. **无额外内存分配**：不需要为每个桶分配链表节点。
3. **可向量化**：SIMD 可以一次比较多个槽。
4. **build 阶段键唯一性**：连接键通常近似唯一，装载因子可以控制得较低，主聚集不严重。

**哈希表的值存什么**（关键设计选择）：讲义 notes 明确「value 取决于实现，可以是**完整元组**或 **record ID**」——这就是**早物化 vs 晚物化**在哈希连接里的体现。若存完整元组，probe 时直接输出；若存 record id，probe 命中后要回表。

**静态 vs 动态哈希表**（notes 原文）：

```
If the DBMS knows the size of the outer table, the join can use a static
hash table. If it does not know the size, the join must use a dynamic hash
table or allow for overflow pages.
```

- **静态**：预先知道外表大小 → 一次分配足够大的表 → 无 rehash、无溢出页。
- **动态**：不知道大小 → 用可扩展哈希/线性哈希，或用溢出页。

**Probe Filter 优化**（第 86–93 页）：

```
Create a probe filter (Bloom Filter) as the DBMS constructs the hash table
on the "build" table in the first phase.
  → Always check the filter before probing the hash table.
  → Faster than probing hash table because the filter fits in CPU cache.
This technique is sometimes called sideways information passing.
```

**为什么有效**（定量）：

```
哈希表大小:    几 MB 到几 GB  → 探测几乎必然 cache miss（~100 ns）
布隆过滤器:    几 KB 到几百 KB → 完全放进 L2/L3 cache（~5 ns）

若过滤器假阳性率 1%:
  99% 的不匹配键被过滤器挡掉，省下一次 cache miss
  1% 的键误入哈希表探测，浪费一次（无害，只是慢）
```

**「假阴性绝不允许」**：若过滤器说「不在」而实际在，就会**漏掉匹配行 → 结果错误**。布隆过滤器天然满足（位为 0 则元素一定不在）。这是它与「假阳性可以接受」的不对称性。

**Sideways Information Passing（侧向信息传递）** 的含义：正常的数据流是「自叶向根」的，而过滤器让 build 阶段的信息**横向**传给 probe 阶段（甚至是传给相邻的另一个算子）。这是查询执行中的一类通用优化：**用廉价的元数据提前排除不可能的工作**。

### 5.11 GRACE 哈希连接：`3(M + N)`

**动机**（第 94 页）：

```
What happens if we do not have enough memory to fit the entire hash table?
We do not want to let the buffer pool manager swap out the hash table
pages at random.
```

**为什么「随机换出」是灾难**：哈希表的访问模式是随机的（每次探测跳到一个哈希位置）。若哈希表大于内存，缓冲池会**持续抖动（thrashing）**：每次探测都缺页，换入一页又立刻被换出。这比顺序扫描慢几个数量级。

**解法**（第 95–110 页）：

```
Partition Phase: Hash both tables on the join attribute into partitioned
buckets that the DBMS writes out to disk.
Probe Phase: Build a hash table one-at-a-time per bucket and compares
tuples in corresponding partitions for each table.
Sometimes called GRACE Hash Join.
  → Named after the GRACE database machine from Japan in the 1980s.
```

```
Partition Phase:
  Hash R into k buckets.
  Hash S into k buckets with same hash function.    ← 必须是同一个 h1
  Write buckets to disk when they get full.

Probe Phase:
  Read the corresponding buckets into memory one partition at a time and
  then perform a hash join on their contents.
```

**为什么两张表必须用同一个 `h1`**：若 R 用 `h1`、S 用 `h1'`，则匹配的 `(r, s)` 可能落到不同的桶，probe 阶段就找不到彼此。**同一个哈希函数保证「同键同桶」**——这是整个算法的正确性基础。

**与外部哈希聚合（第 11 讲）的同构性**：

| | 外部哈希聚合 | GRACE 哈希连接 |
|---|---|---|
| Partition 用什么 | `h1` 按分组键 | `h1` 按连接键 |
| 分区数 | `B-1` | `k`（通常 `≈ √(M+N)` 或按内存定） |
| Probe/ReHash 用什么 | `h2 ≠ h1` | `h2`（桶内建表，也需不同） |
| 为什么能独立处理 | 同组必同分区 | 同键必同分区 |

**代价推导**（第 122 页）：

```
If we do not need recursive partitioning:
  Cost: 3(M + N)

Partition phase:
  → Read+write both input tables.
  → 2(M+N) I/Os

Probe phase:
  → Read both tables' buckets one partition at a time.
  → M+N I/Os
```

**逐项来源**：

```
Partition 阶段:
  读 R 一遍        M
  写 R 的分区      M
  读 S 一遍        N
  写 S 的分区      N
  ────────────────
  小计            2(M + N)

Probe 阶段:
  读 R 的分区      M
  读 S 的分区      N
  ────────────────
  小计            M + N

总计             3(M + N)
```

**注意**：Probe 阶段的「写」不计入，因为连接结果不算代价（约定见第 5.4 节）；哈希表本身在内存里，不产生 I/O。

**讲义例题**（第 123 页）：

```
M = 1000, m = 100,000
N = 500,  n = 40,000

Cost = 3 × (1000 + 500) = 4,500 次 I/O
     = 0.45 秒（0.1 ms/IO）
```

**这是五种算法里最快的**。

### 5.12 递归分区与边界情况

**递归分区**（第 111–121 页）：

```
If a partition still does not fit in memory after the first phase,
recursively partition it again with a different hash function
  → Repeat as needed
  → Eventually hash join the corresponding (sub-)partitions
```

```
        h1 分区后
  ┌────┬────┬────┬─────┬────┐
  │ P1 │ P2 │ P3 │ ... │ Pk │
  └─┬──┴────┴────┴─────┴────┘
    │ P1 太大
    ↓ h2 再分区
  ┌────┬─────┬──────┐
  │1'  │1''  │1'''  │
  └────┴─────┴──────┘
```

**为什么必须换哈希函数**：与第 11 讲外部哈希聚合完全同构——若用 `h1` 再分，P1 内的所有键已经满足 `h1(key) % k = 1`，再按 `h1` 分只会得到退化分布。

**边界情况 1：单个连接键匹配行过多**（第 111 页）：

```
If a single join key has too many matching records that do not fit in
memory, use a block nested loop join just for that key.
  → Avoids random I/O in exchange for sequential I/O.
```

**这是什么情况**：例如连接键是 `status`，90% 的行都是 `'active'`。即使分区再细，那个「active」桶仍然巨大。此时对**这一个键**改用块嵌套循环——因为它只需要**顺序扫描**，而哈希探测是随机的。

**为什么「用顺序 I/O 换随机 I/O」是好事**：HDD 上随机 I/O 比顺序慢 100 倍，SSD 上慢 10 倍。宁可多读几倍的页，也不要随机跳。

**边界情况 2：probe 表的大小**（第 133 页）：

```
The probe table can be any size.
  → Only the build table (or its partitions) need to fit in memory
If the probe table entirely fits in memory, then simply build the hash
table on the probe side and scan the build side probing the hash table
(no partitioning needed).
If we do not know the size, then we must use a dynamic hash table or
allow for overflow pages.
```

**关键的不对称性**：

| | Build 表 | Probe 表 |
|---|---|---|
| 大小限制 | **必须装进内存**（或其分区） | **任意大小**（流式扫描） |
| 为什么 | 要建哈希表 | 只需逐条探测，读完即可丢弃 |

**推论**：**应该把较小的表作为 build 表**（这与嵌套循环「小表当外表」的直觉一致，但理由不同——那里是为了减少外层重复扫描，这里是为了让哈希表装得下）。

**「若 probe 表完全装进内存，就在 probe 侧建表」**：如果内表反而更小、能全放进内存，就把角色对调——在它上面建哈希表，然后流式扫描外表去探测。这等价于交换 build/probe 的角色。

### 5.13 混合哈希连接

**优化思路**（第 124–132 页）：

```
If the buffer pool is larger than k, then use additional pages to perform
an in-memory join in the first phase for the first partition. All other
partitions are spilled to disk as in the original partitioned hash join
algorithm.
```

```
缓冲池 B > k（分区数）时:

  分区 0:  直接留在内存里 → 立即完成连接（不落盘！）
  分区 1..k-1: 照常落盘 → probe 阶段处理
```

**收益**：分区 0 省掉了「写一次 + 读一次」= `2 × (|R₀| + |S₀|)` 次 I/O。若分区 0 占总量的 `1/k`，则省下约 `2(M+N)/k`。

**但讲义 notes 的评语很关键**：

```
Difficult to implement correctly and rarely done in practice.
```

**为什么难实现**：

1. **需要运行时知道缓冲池实际可用页数**，而这是动态的（其他算子可能正在用）。
2. **分区 0 的大小不可控**：若哈希分布不均，分区 0 可能大到装不下，退化为普通 GRACE。
3. **与递归分区的交互复杂**：分区 0 若溢出，是递归分区还是回退到落盘？
4. **收益有限**：只省 `2(M+N)/k`，而 `k` 通常不大（几十到几百），收益是总量的百分之几。

**这是「理论优雅但工程不划算」的典型例子**——与第 11 讲 Bε-tree、第 4 讲 ARC 的部分优化类似：**优化必须值得它带来的复杂度**。

### 5.14 五种算法的完整对比

讲义第 134 页的总结表（附 notes 的差异，见第 8 节待核实）：

| 算法 | I/O 代价 | 例题耗时（`M=1000, m=100000, N=500, n=40000, B=100, 0.1ms/IO`） |
|---|---|---|
| Naïve Nested Loop Join | `M + (m · N)` | **1.3 小时**（notes 作 1.4 小时） |
| Block Nested Loop Join | `M + (⌈M/(B-2)⌉ · N)` | **0.55 秒**（notes 作 0.65 秒） |
| Index Nested Loop Join | `M + (m · C)` | **Varies（可变）** |
| Sort-Merge Join | `M + N + (sort cost)` | **0.75 秒** |
| Hash Join | `3 · (M + N)` | **0.45 秒** |

**排序（从快到慢）**：Hash (0.45s) < Block NLJ (0.55s) < Sort-Merge (0.75s) << Naïve (1.3h)。

**注意 Block NLJ 在这个例题里竟然接近 Hash Join**——因为 `B=100` 且 `M=1000` 相对 `N=500` 不大，`⌈1000/98⌉ = 11`，所以只需 11 次内表扫描。**若 `M` 是 `100,000` 页，Block NLJ 就完全不行了**（`⌈100000/98⌉ ≈ 1021` 次内表扫描）。

**各算法的适用条件汇总**：

| 算法 | 最适合 | 最不适合 |
|---|---|---|
| Naïve NLJ | 教学反例 | 一切实际场景 |
| Block NLJ | 无索引、两表都不太大、`B` 充足 | 外表页数远大于 `B-2` |
| Index NLJ | 外表元组少、内表有高选择性索引 | 外表元组多、索引非聚簇 |
| Sort-Merge | 输入已有序、输出需有序、非等值连接 | 两表都无序且输出无序 |
| Hash | 等值连接、build 表能装进内存 | 非等值连接、严重数据倾斜 |

### 5.15 结论：哈希 vs 排序

**notes 的结论**（第 5 页）：

```
Hash joins are almost always better than sort-based join algorithms, but
there are cases in which sort-based joins would be preferred.
This includes queries on non-uniform data, when the data is already sorted
on the join key, or when the result needs to be sorted.
Good DBMSs will use either or both.
```

**slides 的结论**（第 135 页）：

```
Hashing is almost always better than sorting for operator execution.
Caveats:
  → Sorting is better on non-uniform data.
  → Sorting is better when result needs to be sorted.
Good DBMSs use either (or both).
```

**三条 caveat 的机理**：

1. **非均匀数据（non-uniform data / 数据倾斜）**：哈希连接的分区大小取决于键的分布。若某个键占 90%，它的分区会爆炸，导致递归分区甚至失败。排序的 run 大小只取决于页数，**天然均匀**。
2. **数据已按连接键有序**：sort-merge 可以跳过排序阶段，代价降到 `M + N`——比哈希的 `3(M+N)` 还低。
3. **结果需要有序**：sort-merge 的输出天然有序，省掉后续 `ORDER BY`；哈希连接的输出无序，还要再排一次。

**「Good DBMSs use either or both」** 的实践含义：PostgreSQL、SQL Server、Oracle、DuckDB 都同时实现 sort-merge join 与 hash join，由优化器按代价模型与统计信息选择；执行期还会**自适应切换**（例如哈希连接发现分区过大，运行时改为 sort-merge）。

**内存数据库的反转**：本讲全部结论建立在「I/O 主导」上。在内存数据库中（如 HyPer、DuckDB 的内存模式），CPU 成为瓶颈，此时：

- 哈希连接的随机访问成为 cache miss 的主要来源。
- **sort-merge join 反而可能更快**（顺序访问、可向量化、可 SIMD）。
- 学术界对此有大量实测（Balkesen 等人 VLDB 2013 的 *Multi-Core, Main-Memory Joins: Sort vs. Hash Revisited* 是经典）。

> 待核实：本讲未涉及内存数据库场景，上述反转是补充背景，非讲义内容。

## 6. 代码示例

### 6.1 讲义原文示例

**为什么需要连接**（`12-joins.pdf` 第 5 页）：

```
We normalize tables in a relational database to avoid unnecessary
repetition of information.
We then use the join operator to reconstruct the original tuples without
any information loss.
```

**本讲范围**（第 6 页）：

```
We will focus on performing binary joins (two tables) using inner
equijoin algorithms.
  → These algorithms can be tweaked to support other joins.
  → Multi-way joins exist primarily in research literature
    (e.g., worst-case optimal joins).
In general, we want the smaller table to always be the left table
("outer table") in the query plan.
  → The optimizer will (try to) figure this out when generating the
    physical plan.
```

**两个设计决策**（第 8 页）：

```
Decision #1: Output
  → What data does the join operator emit to its parent operator in the
    query plan tree?
Decision #2: Cost Analysis Criteria
  → How do we determine whether one join algorithm is better than another?
```

**早物化**（第 10 页）：

```
Early Materialization:
  → Copy the values for the attributes in outer and inner tuples into a
    new output tuple.
  Subsequent operators in the query plan never need to go back to the base
  tables to get more data.
```

**晚物化**（第 15 页）：

```
Late Materialization:
  → Only copy the joins keys along with the Record IDs of the matching
    tuples.
  Ideal for column stores because the DBMS does not copy data that is not
  needed for the query.
```

**代价度量**（第 20 页）：

```
Given a query that joins table R with table S, assume the DBMS has the
following information those tables:
  → M pages in table R, m tuples in R
  → N pages in table S, n tuples in S

Cost Metric: # of I/Os to compute join
  → Ignore result output costs because it depends on the data and is the
    same for all algorithms.
  → Ignore computation / network costs (for now).
```

**连接 vs 笛卡尔积**（第 21 页）：

```
R⨝S is the most common operation and thus must be carefully optimized.
R×S followed by a selection is inefficient because the cross-product is
large.
  → These types of joins are rare and there is no magic algorithm to make
    this go faster.
There are many algorithms for reducing join cost, but no algorithm works
well in all scenarios.
```

**朴素嵌套循环**（第 24、27 页）：

```
for tuple r ∈ R:
  for tuple s ∈ S:
    if r and s match: emit
```

```
Why is this algorithm bad?
  → For every tuple in R, it scans S once
Cost: M + (m ∙ N)
```

页面标注 **"Don't Do This!"**（第 26 页）。

**朴素版的例题与换外表**（第 29 页）：

```
Example database:
  → Table R: M = 1000, m = 100,000
  → Table S: N = 500,  n = 40,000

Cost Analysis:
  → M + (m ∙ N) = 1000 + (100000 ∙ 500) = 50,001,000 IOs
  → At 0.1 ms/IO, Total time ≈ 1.3 hours

What if smaller table (S) is used as the outer table?
  → N + (n ∙ M) = 500 + (40000 ∙ 1000) = 40,000,500 IOs
  → At 0.1 ms/IO, Total time ≈ 1.1 hours
```

第 32 页补注：`4 KB pages → 6 MB`。

**块嵌套循环**（第 33–35 页）：

```
for page pR ∈ R:
  for page pS ∈ S:
    for tuple r ∈ pR:
      for tuple s ∈ ps:
        if r and s match: emit
```

```
This algorithm performs fewer disk accesses.
  → For every block in R, it scans S once.
Cost: M + (M ∙ N)
```

```
The smaller table should be the outer table.
We determine size based on the number of pages, not the number of tuples.
```

**用满缓冲池的块嵌套循环**（第 36–38 页）：

```
If we have B buffers available:
  → Use B-2 buffers for each block of the outer table.
  → Use one buffer for the inner table, one buffer for output.
```

```
for B - 2 pages pR ∈ R:
  for page pS ∈ S:
    for tuple r ∈ B - 2 pages:
      for tuple s ∈ pS:
        if r and s match: emit
```

```
This algorithm uses B-2 buffers for scanning R.
Cost: M + (⌈M / (B-2)⌉ ∙ N)

If the outer relation fits in memory (M < B-2):
  → Cost: M + N = 1000 + 500 = 1500 I/Os
  → At 0.1ms per I/O, Total time ≈ 0.15 seconds

If we have B=102 buffer pages:
  → Cost: M + (⌈M / (B-2)⌉ ∙ N) = 1000 + 10∙500 = 6000 I/Os
  → Or switch inner/outer relations: 500 + 5∙1000 = 5500 I/Os
```

**索引嵌套循环**（第 43 页）：

```
Assume the cost of each index probe is some constant C per tuple in the
outer table.
Cost: M + (m ∙ C)
```

```
for tuple r ∈ R:
  for tuple s ∈ Index(ri = sj):
    if r and s match: emit
```

**嵌套循环总结**（第 45 页）：

```
Key Takeaways
  → Pick the smaller table as the outer table, when possible.
  → Buffer as much of the outer table in memory as possible.
  → Loop over the inner table (or use an index).
Algorithms
  → Naïve
  → Block
  → Index
```

**排序归并的两阶段**（第 46–47 页）：

```
Phase #1: Sort
  → Sort both tables on the join key(s).
  → You can use any appropriate sort algorithm
  → These phases are distinct from the sort/merge phases of an external
    merge sort, from the previous class
Phase #2: Merge
  → Step through the two sorted tables with cursors and emit matching
    tuples.
  → May need to backtrack depending on the join type.
```

```
sort R,S on join keys
cursorR ← Rsorted, cursorS ← Ssorted
while cursorR and cursorS:
  if cursorR > cursorS:
    increment cursorS
  if cursorR < cursorS:
    increment cursorR
  backtrack cursors (if necessary)
  elif cursorR and cursorS match:
    emit
  increment cursorS
```

**排序归并的代价**（第 74、76 页）：

```
Sort Cost (R): 2M ∙ (1 + ⌈ log_{B-1} ⌈M / B⌉ ⌉)
Sort Cost (S): 2N ∙ (1 + ⌈ log_{B-1} ⌈N / B⌉ ⌉)
Merge Cost: (M + N)
Total Cost: Sort + Merge
```

```
The worst case for the merging phase is when the join attribute of all
the tuples in both relations contains the same value.
Cost: (M ∙ N) + (sort cost)
```

**排序归并的例题**（第 75 页）：

```
Example database:
  → Table R: M = 1000, m = 100,000
  → Table S: N = 500,  n = 40,000

With B=100 buffer pages, both R and S can be sorted in two passes:
  → Sort Cost (R) = 2000 ∙ (1 + ⌈log₉₉ 1000/100⌉) = 4000 I/Os
  → Sort Cost (S) = 1000 ∙ (1 + ⌈log₉₉ 500/100⌉) = 2000 I/Os
  → Merge Cost = (1000 + 500) = 1500 I/Os
  → Total Cost = 4000 + 2000 + 1500 = 7500 I/Os
  → At 0.1 ms/IO, Total time ≈ 0.75 seconds
```

**排序归并的适用条件**（第 77 页）：

```
Sort-Merge Join is preferable when one of the following conditions are met:
  → One or both tables are already sorted on join key.
  → Output must be sorted on join key.
The input relations may be sorted either by an explicit sort operator, or
by scanning the relation using an index on the join key.
```

**哈希连接的正确性论证**（第 78 页）：

```
If tuple r ∈ R and tuple s ∈ S satisfy the join condition, then they have
the same value for the join attributes.
If that value is hashed to some partition i, the R tuple must be in ri and
the S tuple in si.
Therefore, R tuples in ri need only to be compared with S tuples in si.
```

**基本哈希连接**（第 79–80 页）：

```
Phase #1: Build
  → Scan the outer relation and populate a hash table using the hash
    function h1 on the join attributes.
  → We can use any hash table that we discussed before but in practice
    linear probing works the best.
Phase #2: Probe
  → Scan the inner relation and use h1 on each tuple to jump to a location
    in the hash table and find a matching tuple.
```

```
for tuple r ∈ R:
  insert h1(r) into hash table HTR
for tuple s ∈ S:
  if h1(s) ∈ HTR: emit
```

**Probe Filter**（第 86 页）：

```
Create a probe filter (Bloom Filter) as the DBMS constructs the hash table
on the "build" table in the first phase.
  → Always check the filter before probing the hash table.
  → Faster than probing hash table because the filter fits in CPU cache.
This technique is sometimes called sideways information passing.
```

**GRACE 哈希连接**（第 95 页）：

```
Partition Phase: Hash both tables on the join attribute into partitioned
buckets that the DBMS writes out to disk.
Probe Phase: Build a hash table one-at-a-time per bucket and compares
tuples in corresponding partitions for each table.
Sometimes called GRACE Hash Join.
  → Named after the GRACE database machine from Japan in the 1980s.
```

**分区阶段**（第 100 页）：

```
Hash R into k buckets.
Hash S into k buckets with same hash function.
Write buckets to disk when they get full.
```

**探测阶段**（第 103 页）：

```
Read corresponding the buckets into memory one partition at a time and
then perform a hash join their contents.
```

**边界情况**（第 111 页）：

```
If a partition still does not fit in memory after the first phase,
recursively partition it again with a different hash function
  → Repeat as needed
  → Eventually hash join the corresponding (sub-)partitions

If a single join key has too many matching records that do not fit in
memory, use a block nested loop join just for that key.
  → Avoids random I/O in exchange for sequential I/O.
```

**GRACE 的代价**（第 122 页）：

```
If we do not need recursive partitioning:
  Cost: 3(M + N)

Partition phase:
  → Read+write both input tables.
  → 2(M+N) I/Os

Probe phase:
  → Read both tables' buckets one partition at a time.
  → M+N I/Os
```

**混合哈希连接**（第 124 页）：

```
If the buffer pool is larger than k, then use additional pages to perform
an in-memory join in the first phase for the first partition. All other
partitions are spilled to disk as in the original partitioned hash join
algorithm.
```

**哈希连接的性质**（第 133 页）：

```
The probe table can be any size.
  → Only the build table (or its partitions) need to fit in memory
If the probe table entirely fits in memory, then simply build the hash
table on the probe side and scan the build side probing the hash table
(no partitioning needed).
If we do not know the size, then we must use a dynamic hash table or
allow for overflow pages.
```

**总结表**（第 134 页）：

```
Algorithm               | IO Cost                  | Example
Naïve Nested Loop Join  | M + (m ∙ N)              | 1.3 hours
Block Nested Loop Join  | M + (⌈M/(B-2)⌉ ∙ N)      | 0.55 seconds
Index Nested Loop Join  | M + (m ∙ C)              | Variable
Sort-Merge Join         | M + N + (sort cost)      | 0.75 seconds
Hash Join               | 3 ∙ (M + N)              | 0.45 seconds
```

**结论**（第 135 页）：

```
Hashing is almost always better than sorting for operator execution.
Caveats:
  → Sorting is better on non-uniform data.
  → Sorting is better when result needs to be sorted.
Good DBMSs use either (or both).
```

### 6.2 补充示例（非官方，仅用于说明概念）

**五种算法的代价计算器**：

```python
import math

M, m = 1000, 100_000      # R: 页数, 元组数
N, n = 500, 40_000        # S: 页数, 元组数
B = 100                   # 缓冲页
MS_PER_IO = 0.1

def naive_loop(M, m, N, n):
    return M + m * N

def block_loop(M, m, N, n, B):
    # 外表完全装进内存时，内表只需扫一遍
    if M <= B - 2:
        return M + N
    return M + math.ceil(M / (B - 2)) * N

def index_loop(M, m, N, n, C):
    return M + m * C

def sort_merge(M, m, N, n, B):
    def sort_cost(pages):
        passes = 1 + math.ceil(math.log(math.ceil(pages / B), B - 1)) if pages > B else 1
        return 2 * pages * passes
    return sort_cost(M) + sort_cost(N) + (M + N)

def grace_hash(M, m, N, n):
    return 3 * (M + N)

for name, cost in [
    ("Naive NLJ",  naive_loop(M, m, N, n)),
    ("Block NLJ",  block_loop(M, m, N, n, B)),
    ("Index NLJ (C=1)", index_loop(M, m, N, n, 1)),
    ("Sort-Merge", sort_merge(M, m, N, n, B)),
    ("Grace Hash", grace_hash(M, m, N, n)),
]:
    ms = cost * MS_PER_IO
    unit = f"{ms/3_600_000:.2f} 小时" if ms > 3_600_000 else f"{ms/1000:.2f} 秒"
    print(f"{name:18s} {cost:>12,} I/O  {unit:>12s}")
```

**朴素嵌套循环的「换外表」分析**：

```python
def compare_outer(M, m, N, n):
    a = M + m * N      # R 当外表
    b = N + n * M      # S 当外表
    print(f"R 当外表: {a:,}   S 当外表: {b:,}   比值 {a/b:.2f}")
    # 两表元组密度相同（m/M == n/N）时，a ≈ b
    print(f"元组密度: R={m/M:.0f} 元组/页, S={n/N:.0f} 元组/页")

compare_outer(1000, 100_000, 500, 40_000)
# R 当外表: 50,001,000   S 当外表: 40,000,500   比值 1.25
# 元组密度: R=100 元组/页, S=80 元组/页
# → 密度接近时换外表只省 25%，因为 m×N ≈ n×M
```

**这个分析说明**：朴素嵌套循环的根本问题不是外表选错，而是「每个元组扫一遍内表」。**当 `m/N ≈ n/M` 时，`m×N ≈ n×M`，换外表几乎无用**。

**块嵌套循环的外表选择（按页数）**：

```python
def block_outer_choice(M, N, B):
    a = M + math.ceil(M / (B - 2)) * N
    b = N + math.ceil(N / (B - 2)) * M
    print(f"R 外表: {a:,}   S 外表: {b:,}   → 选 {'R' if a < b else 'S'}")
    # 注意：不是简单选页数小的，要看 ⌈M/(B-2)⌉ × N 与 ⌈N/(B-2)⌉ × M

block_outer_choice(1000, 500, 102)
# R 外表: 6,000   S 外表: 5,500   → 选 S
```

**排序归并的 backtrack 逻辑**：

```python
def sort_merge_join(R, S, key=lambda t: t[0]):
    """R、S 为已按 key 排序的列表。返回匹配对。"""
    i = j = 0
    out = []
    while i < len(R) and j < len(S):
        kr, ks = key(R[i]), key(S[j])
        if kr < ks:
            i += 1
        elif kr > ks:
            j += 1
        else:
            # 找到一组同键元组：收集 R 中所有同键、S 中所有同键
            i2, j2 = i, j
            while i2 < len(R) and key(R[i2]) == kr:
                i2 += 1
            while j2 < len(S) and key(S[j2]) == ks:
                j2 += 1
            # 笛卡尔积（这就是 backtrack 的语义）
            for a in range(i, i2):
                for b in range(j, j2):
                    out.append((R[a], S[b]))
            i, j = i2, j2
    return out
```

**注意 `for a ... for b ...` 的双重循环**——这就是**最坏情况 `M × N` 的来源**：若两表所有键相同，`i2 - i = m`、`j2 - j = n`，输出 `m × n` 对。讲义说这「very unlikely」，因为真实数据的连接键大多近似唯一。

**哈希连接（内存版）**：

```python
def hash_join(R, S, key=lambda t: t[0]):
    """Build on R, probe with S。"""
    table = {}
    for r in R:                              # Phase #1: Build
        table.setdefault(key(r), []).append(r)
    out = []
    for s in S:                              # Phase #2: Probe
        for r in table.get(key(s), ()):
            out.append((r, s))
    return out
```

**注意 `table.setdefault(key(r), []).append(r)`**：这处理了**重复键**——同一个键可能对应多个 R 元组，所以桶里是列表。这是哈希连接与「哈希去重」的关键区别：**连接不能丢重复**。

**GRACE 哈希连接（模拟落盘）**：

```python
def grace_hash_join(R, S, key, n_parts, h1, memory_rows):
    # Partition Phase: 两表用同一个 h1 分到 n_parts 个桶
    r_parts = [[] for _ in range(n_parts)]
    s_parts = [[] for _ in range(n_parts)]
    for r in R:
        r_parts[h1(key(r)) % n_parts].append(r)
    for s in S:
        s_parts[h1(key(s)) % n_parts].append(s)

    # Probe Phase: 逐对桶做内存哈希连接
    out = []
    for p in range(n_parts):
        if len(r_parts[p]) + len(s_parts[p]) > memory_rows:
            # 边界情况：桶太大 → 对该桶改用块嵌套循环
            out.extend(block_nested_loop(r_parts[p], s_parts[p], key))
        else:
            out.extend(hash_join(r_parts[p], s_parts[p], key))
    return out

def block_nested_loop(R, S, key):
    return [(r, s) for r in R for s in S if key(r) == key(s)]
```

**注意 `h1` 对两表是同一个**——若用不同的哈希函数，匹配的 `(r, s)` 会落到不同桶，probe 阶段永远找不到彼此。

**Probe filter 的效果模拟**：

```python
import random

def hash_join_with_filter(R, S, key, fpr=0.01):
    table = {key(r): r for r in R}
    # 用一个集合模拟「完美布隆过滤器」，再按 fpr 注入假阳性
    bloom = set(table)
    stats = {"filter_reject": 0, "probe": 0, "false_positive": 0}
    out = []
    for s in S:
        k = key(s)
        if k not in bloom:
            # 过滤器说不存在 → 一定不存在（无假阴性）
            if random.random() < fpr:          # 模拟假阳性
                stats["false_positive"] += 1
                stats["probe"] += 1            # 白跑一次
            else:
                stats["filter_reject"] += 1
            continue
        stats["probe"] += 1
        if k in table:
            out.append((table[k], s))
    return out, stats
```

**关键不对称性**：过滤器「说不在」时**必须真的不在**（否则漏结果）；「说在」时可以错（只是白跑一次）。所以布隆过滤器只允许假阳性。

## 7. 容易混淆的概念

| 概念对 | 区别 | 记忆要点 |
|---|---|---|
| 外表 vs 内表 | 外层循环遍历的是外表，内层是内表 | 嵌套循环里「小的当外表」；哈希连接里「小的当 build 表」 |
| 早物化 vs 晚物化（连接） | 前者复制全部属性值；后者只复制键 + record id | 行存用早，列存用晚 |
| 块嵌套循环 `M×N` vs `⌈M/(B-2)⌉×N` | 前者一页一块；后者一次 `B-2` 页一块 | 用满缓冲池能再降 `B-2` 倍 |
| `B-2` vs `B-1`（排序的） | 连接留 1 页给内表 + 1 页输出；排序留 1 页输出 | 连接比排序多占一页 |
| 索引 NLJ vs 块 NLJ | 前者 `m×C`（按元组探索引）；后者 `⌈M/(B-2)⌉×N`（按块扫内表） | 外表元组少才用索引 |
| 排序归并的 Sort/Merge vs 外部排序的 Phase#1/#2 | 前者「排两张表 + 归并连接」；后者「排成 run + 归并 run」 | 讲义明确说这两组阶段「distinct」 |
| 排序归并的 `M+N` vs 最坏 `M×N` | 前者键近似唯一；后者所有键相同（backtrack 反复回退） | 真实数据近似唯一 |
| 哈希连接的 build vs probe | build 表**必须装进内存**；probe 表**任意大小** | 小的当 build |
| 基本哈希连接 vs GRACE | 前者哈希表装内存；后者分区落盘 | 一个 `M+N`，一个 `3(M+N)` |
| GRACE 的 `h1` vs 桶内的 `h2` | `h1` 分磁盘桶（两表必须相同）；`h2` 桶内建表（必须不同） | 同一个函数会让桶内退化 |
| 递归分区 vs 混合哈希 | 前者「装不下就再分」；后者「装得下就留内存」 | 一个向下拆，一个向上留 |
| Probe filter vs 哈希表 | 过滤器小到进 cache、允许假阳性；哈希表精确但会 cache miss | 门口名单 vs 进屋翻档案 |
| 哈希 vs 排序（连接） | 哈希 `3(M+N)` 通常更快；排序在倾斜/已有序/需有序时更优 | 哈希怕倾斜，排序怕无序 |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Slides | `90-原始PDF/15-445/slides/12-joins.pdf` | 135 | 1（标题，讲师 Jignesh Patel，标注 Lecture #12）、2（Project #2 due Sunday Oct 25th 2026 11:59pm；期中成绩已发布，中位数 62/90、标准差 8.77；补分找 OH）、3（DB Talks：Snowflake DB Lunch 周二 Oct 23rd noon ET NSH 4305；Floe DB Seminar 周一 Oct 19th 4:30pm ET Zoom）、4（上讲回顾：Divide-and-Conquer、Sorting/Hashing 两种策略）、5（为什么需要连接：规范化 + 重构）、6（二元内等值连接、多路连接在研究文献、小表当外表）、7（查询计划算子树）、8（两个设计决策：Output 与 Cost Analysis）、9（算子输出：拼接 r 与 s）、10–14（早物化：复制全部属性值）、15–19（晚物化：只复制连接键 + record id）、20（代价度量：`M/m/N/n` 定义、只算 I/O、忽略输出与计算）、21（连接 vs 笛卡尔积）、22（算法清单：Nested Loop Naïve/Block/Index、Sort-Merge、Hash Simple/Partitioned/Hybrid）、23–32（朴素嵌套循环：伪代码、`M+(m·N)`、例题 50,001,000 I/O ≈ 1.3 小时、换外表 40,000,500 ≈ 1.1 小时、`4 KB pages → 6 MB`）、33–35（块嵌套循环：`M+(M·N)`、按页数选外表）、36–40（用满缓冲池：`B-2` 页给外表、`M+(⌈M/(B-2)⌉·N)`、`M<B-2` 时 `M+N=1500` ≈ 0.15 秒、`B=102` 时 6000 与换表 5500）、41–42（嵌套循环为何差：每元组顺序扫内表）、43–44（索引嵌套循环：`M+(m·C)`）、45（嵌套循环总结三条）、46–47（排序归并两阶段与游标伪代码、backtrack）、48–73（完整示例：R 8 行 / S 5 行、`Last Value` 状态推进、GZA 重复键 backtrack）、74（代价公式：两个 sort cost + `M+N`）、75（例题：4000+2000+1500=7500 ≈ 0.75 秒）、76（最坏情况 `M·N` + sort cost）、77（何时优选：已有序 / 输出需有序）、78（哈希连接正确性论证）、79–85（基本哈希连接 Build/Probe、线性探查最好、`for r insert h1(r)`）、86–93（Probe Filter / 布隆过滤器 / sideways information passing）、94（哈希表装不下时不能让缓冲池随机换出）、95–99（GRACE：Partition/Probe、命名自 1980s 日本东京大学 GRACE 数据库机）、100–110（分区阶段 `k` 桶、同一 `h1`、探测阶段逐桶建表）、111（边界：递归分区换哈希函数、单键过多改用块嵌套循环）、112–121（递归分区图示 `1' 1'' 1'''`）、122（代价 `3(M+N)`：分区 `2(M+N)` + 探测 `M+N`）、123（例题 4500 ≈ 0.45 秒）、124–132（混合哈希连接：缓冲池 > k 时第一分区留内存）、133（probe 表任意大小、只有 build 侧需装内存、大小未知用动态哈希表或溢出页）、134（五算法总结表）、135（结论：哈希几乎总是更好，三条 caveat） |
| Notes | `90-原始PDF/15-445/notes/12-joins.pdf` | 5 | 第 1 页（Introduction：规范化与重构、二元内等值连接、多路连接、小表当外表；Join Operators：算子输出、早物化与晚物化的优缺点、真实系统混用）、第 2 页（Cost Analysis：`M/m/N/n` 与只算 I/O 的理由；Nested Loop Join：Naïve `M+(m·N)`、Block `M+(M·N)`、缓冲池版 `M+(⌈M/(B-2)⌉·N)` 与 `B-2` 的分配）、第 3 页（Index NLJ `M+(m·C)`、内表需索引；Sort-Merge Join 两阶段、适用条件、最坏 `M·N`、`B` 缓冲下的排序与归并代价；Hash Join 的正确性论证、Basic Hash Join 的 Build/Probe、build 侧需装内存）、第 4 页（Probe Filter 布隆过滤器与 sideways information passing、静态 vs 动态哈希表；Grace/Partitioned Hash Join 的两阶段、`h1 ≠ h2` 的递归分区、`3(M+N)`、单键过多改用 block NLJ、hybrid hash join「难以正确实现且实践中很少做」；Conclusion 总结表）、第 5 页（结论：哈希几乎总是优于排序，除非常规数据、已按连接键排序、或结果需排序；好的 DBMS 两者都用） |

原始 URL：

- Slides：`https://15445.courses.cs.cmu.edu/fall2026/slides/12-joins.pdf`
- Notes：`https://15445.courses.cs.cmu.edu/fall2026/notes/12-joins.pdf`

> 待核实：本 PDF 文件名与内部编号均为 **#12 / Lecture #12**，但按 2026 秋季课表本讲是**第 13 讲**（课表 #12 为 DRC 无课）。这是「PDF 编号比课表讲次少 1」的直接体现，引用页码时以 PDF 为准、引用讲次时以课表为准。
> 待核实：讲义 notes 第 4 页总结表写 **Block Nested Loop Join = 0.65 秒**、**Naïve Nested Loop Join = 1.4 小时**，而 slides 第 134 页写 **0.55 秒**与 **1.3 小时**。两处不一致，本笔记表格同时标注两者；建议以 slides 例题（第 38 页 `6000 I/O`、第 29 页 `50,001,000 I/O`）自行核算：`6000 × 0.1ms = 0.6 秒`、`50,001,000 × 0.1ms ≈ 1.39 小时`，故 notes 的 0.65 秒 / 1.4 小时更接近手算结果。
> 待核实：slides 第 67 页的示例输出中 `Raekwon 200 | 6666` 一行，`id=200` 对应 S 元组 `(200, 8888)` 而非 `(400, 6666)`；疑为动画帧拼接时的错位。按语义，`(400, ODB)` 应与 `(400, 6666)` 配对、`(200, Raekwon)` 应与 `(200, 8888)` 配对，请以 PDF 原图为准。
> 待核实：slides 第 2 页 admin 信息提到「期中成绩已发布，中位数 62/90」，而第 11 讲 slides 写「期中在 Oct 7」，两讲时间线相隔约两周，逻辑一致；但 Project #2 截止日在本讲写作 **Oct 25th, 2026**，与第 11 讲提到的「Project #2 due Sunday March 15th」矛盾，进一步印证第 11 讲那处是春季版残留。
> 待核实：讲义称 GRACE 数据库机为「Japan in the 1980s / University of Tokyo」，具体年份与项目归属（东京大学理学部还是某实验室）讲义未给，建议人工核对原始文献（Fushimi et al., *An Overview of the System Software of a Parallel Relational Database Machine GRACE*, VLDB 1986）。

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内，本讲内容对应 2025 年第 12 讲）

- 标题：Join Algorithms — Nested Loop Join, Sort-Merge Join, Hash Join（2025 年第 12 讲）
- URL：`https://www.youtube.com/watch?v=YIdIaPopfpk&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 年份：2025
- 时间戳：未核实，故不标注。

## 10. 本节复习

- 能说明「规范化省存储、连接付代价」这条权衡链，并解释为什么反规范化在 OLAP 中仍有人用。
- 能说出本讲三个限定词（binary / inner / equijoin）各自的含义与放宽方式。
- 能对比早物化与晚物化的内存开销与回表代价，并指出各自适合行存还是列存。
- 能默写五种连接算法的 I/O 代价公式，并说明每一项的来源。
- 能解释块嵌套循环里 `B-2` 的分配（1 页内表 + 1 页输出），并与排序的 `B-1` 对照。
- 能说明 index NLJ 在什么条件下反而比 block NLJ 更差，并举出例题中的反直觉结果。
- 能说明排序归并的 `backtrack` 为什么必要，以及最坏情况 `M×N` 的成因。
- 能完整推导 `B=100` 时排序归并的 7500 次 I/O（4000 + 2000 + 1500）。
- 能证明哈希连接的正确性（三步推导），并解释它为什么只能用于等值连接。
- 能说明为什么哈希连接里「线性探查在实践中最好」。
- 能解释 probe filter 为什么能加速（cache 大小差异），以及为什么绝不允许假阴性。
- 能推导 GRACE 的 `3(M+N)`（分区 `2(M+N)` + 探测 `M+N`）。
- 能说明递归分区为什么必须换哈希函数，以及与外部哈希聚合的同构性。
- 能列出哈希连接在哪些情况下劣于排序归并（倾斜、已有序、需有序）。

## 11. 自我检查

**Q1.** 块嵌套循环连接的代价是 `M + (⌈M/(B-2)⌉ × N)`。请说明为什么是 `B-2` 而不是 `B` 或 `B-1`，并计算 `M=1000, N=500, B=102` 时两种内外表顺序的代价。若 `B` 增大到 `1002`，代价如何变化？

<details><summary>参考答案</summary>

**为什么是 `B-2`**：

```
B 个缓冲页的分配：
  - 1 页：内表 S 的当前扫描页（内层循环每轮都要换页）
  - 1 页：输出缓冲（攒满一批再写回，避免每行一次 I/O）
  ─────────
  = B - 2 页：可用于一次性装下外表的「一个大块」
```

**为什么不能是 `B`**：内层扫描必须有一页放 S 的当前页，否则无法比较；输出也必须有一页缓冲，否则每产生一个结果元组就要写一次磁盘（可能几百万次 I/O）。

**为什么不能是 `B-1`**：那意味着不给输出留缓冲。虽然理论上可以「直接写」，但代价是结果元组的每次输出都变成一次 I/O——若输出 100 万行就是 100 万次 I/O，完全抵消了优化收益。

**对照第 11 讲的排序**：外部排序用 `B-1`（`B-1` 路归并 + 1 页输出），因为归并的**输入**只需要每个 run 一页，而**不需要额外的「内表扫描页」**。连接比排序多一个「内层循环的当前页」需求，所以是 `B-2`。**这个差异是两种算子数据流结构不同的直接结果。**

**`M=1000, N=500, B=102` 的计算**：

```
B - 2 = 100

以 R 为外表（M=1000）:
  Cost = M + ⌈M/(B-2)⌉ × N
       = 1000 + ⌈1000/100⌉ × 500
       = 1000 + 10 × 500
       = 6,000 次 I/O

以 S 为外表（N=500）:
  Cost = N + ⌈N/(B-2)⌉ × M
       = 500 + ⌈500/100⌉ × 1000
       = 500 + 5 × 1000
       = 5,500 次 I/O
```

**结论：应选 S 当外表**（5500 < 6000），省 500 次 I/O。

**注意这不是简单的「选页数小的」**：`⌈1000/100⌉ = 10` 与 `⌈500/100⌉ = 5` 恰好成比例，所以按页数选也对。但如果 `M=1001, N=999, B=102`：`⌈1001/100⌉ = 11`、`⌈999/100⌉ = 10`，代价 `1001 + 11×999 = 11,990` vs `999 + 10×1001 = 11,009`——仍选 N。**一般情况下按页数选是好的启发式，但严格判断要看 `⌈M/(B-2)⌉ × N` 与 `⌈N/(B-2)⌉ × M` 的比较。**

**`B` 增大到 `1002` 时的变化**：

```
B - 2 = 1000

以 R 为外表:
  Cost = 1000 + ⌈1000/1000⌉ × 500 = 1000 + 1 × 500 = 1,500 次 I/O

以 S 为外表:
  Cost = 500 + ⌈500/1000⌉ × 1000 = 500 + 1 × 1000 = 1,500 次 I/O
```

**两个关键观察**：

1. **代价降到 `M + N = 1500`**——这正是「外表完全装进内存」的情形（`M = 1000 ≤ B-2 = 1000`）。此时内表只需扫一遍，达到**理论下界**（每张表至少读一次）。
2. **两种顺序代价相同**——因为无论谁当外表，都是「外表读一遍 + 内表读一遍」。**当缓冲池足够大时，内外表的选择不再重要**。

**代价随 B 的变化曲线**（`M=1000, N=500`）：

| B | `B-2` | 以 R 为外表 | 以 S 为外表 | 最优 |
|---|---|---|---|---|
| 3 | 1 | `1000 + 1000×500 = 501,000` | `500 + 500×1000 = 500,500` | S |
| 12 | 10 | `1000 + 100×500 = 51,000` | `500 + 50×1000 = 50,500` | S |
| 102 | 100 | `1000 + 10×500 = 6,000` | `500 + 5×1000 = 5,500` | S |
| 502 | 500 | `1000 + 2×500 = 2,000` | `500 + 1×1000 = 1,500` | S |
| 1002 | 1000 | `1000 + 1×500 = 1,500` | `500 + 1×1000 = 1,500` | 相同 |

**曲线形状是 `1/B` 的双曲线**：`B` 从 3 增到 12（4 倍）省了 10 倍 I/O；从 102 增到 1002（10 倍）只省了 4 倍。**边际收益递减，但在小 B 区间极其陡峭**——这与第 11 讲外部排序「`log_{B-1}` 在小 B 时最陡」的结论同源：**缓冲页是查询执行最稀缺、也最有价值的资源**。

**实践含义**：这就是第 4 讲「Multiple Buffer Pools」要为连接单独划池的原因——若连接算子只分到 3 个缓冲页，块嵌套循环退化成接近朴素版；给它 100 页就能快 100 倍。**查询优化器在估算代价时必须知道实际能分到多少页**，否则代价模型完全失真。

</details>

**Q2.** 哈希连接的正确性依赖哪三个前提？为什么它不能用于非等值连接（如 `R.id < S.id`）？GRACE 哈希连接里为什么两张表必须用同一个哈希函数 `h1`，而桶内建表又必须换用 `h2`？

<details><summary>参考答案</summary>

**正确性的三个前提**：

```
1. 等值谓词：r 与 s 匹配 ⟺ r.key = s.key
2. 哈希函数确定性：同一个键必然算出同一个哈希值，h(x) 与调用时机、
   调用者、表无关
3. 哈希函数在两张表上一致：R 与 S 用同一个 h1（GRACE 场景下尤其关键）
```

**三步推导**：

```
设 r ∈ R、s ∈ S 满足 r.key = s.key = k
由 (1)(2)：h1(r.key) = h1(k) = h1(s.key)
∴ r 与 s 落在同一个桶 i = h1(k)
∴ 只需比较同桶内的元组，跨桶配对可以完全跳过   ← 剪枝的正确性
```

**为什么不能用于非等值连接**：

设谓词是 `r.id < s.id`。取 `r.id = 5`、`s.id = 7`，满足 `5 < 7`。但：

```
h1(5) 与 h1(7) 毫无关系
→ 它们可能落在完全不同的桶
→ 若只比较同桶元组，就会漏掉这个匹配
→ 结果错误
```

**根本原因**：哈希只保留「**相等性**」这一种信息（同键同哈希），**丢弃了顺序信息**。而 `<`、`>`、`BETWEEN` 都需要顺序信息。所以：

| 谓词类型 | 可用算法 |
|---|---|
| `=`（等值） | 全部五种，含哈希 |
| `<`、`>`、`<=`、`>=` | 嵌套循环、排序归并（**不能用哈希**） |
| `!=`、`NOT IN` | 嵌套循环（哈希只能用来**排除**，不能直接产出） |
| 复合谓词 `a=b AND c<d` | 用哈希处理 `a=b` 部分，再用其他方式处理 `c<d` |

**补充**：讲义强调哈希连接只能用于「**完整连接键**（complete join key）上的等值连接」。若连接键是复合的 `(a, b)`，必须对 `(a, b)` 整体哈希，不能只哈希 `a`——否则同 `a` 不同 `b` 的元组会混在一个桶里，虽然不影响正确性但会丧失剪枝效果。

**GRACE 里为什么两表必须用同一个 `h1`**：

```
若 R 用 h1、S 用 h1'（h1 ≠ h1'）:
  r.key = s.key = k
  → r 落在桶 h1(k) % k_parts
  → s 落在桶 h1'(k) % k_parts
  → 两个桶号大概率不同
  → Probe 阶段读「对应的」桶（第 i 个 R 桶 + 第 i 个 S 桶）
  → 但匹配的 r 和 s 根本不在同一对桶里
  → 永远找不到彼此 → 结果错误
```

**这就是「分区」与「桶内建表」的本质区别**：

| 阶段 | 哈希函数 | 目的 | 一致性要求 |
|---|---|---|---|
| **Partition**（跨表） | `h1` | 把**两张表**切成对应的 `k` 份 | **两表必须相同**——否则对应桶不匹配 |
| **桶内建表**（单表内） | `h2` | 在**一个桶内部**再分散 | **必须与 `h1` 不同**——否则退化 |

**为什么桶内必须换 `h2`**：

桶 `i` 里的所有元组都满足 `h1(key) % k = i`。若桶内建表仍用 `h1`：

```
bucket = h1(key) % table_size
对桶 i 内所有元组：h1(key) % k 都等于 i
→ 若 table_size 是 k 的倍数，所有键算出同一个 bucket
→ 哈希表退化成一条长度为 |桶 i| 的链表
→ 探测变成 O(|桶 i|)，整个连接退化为嵌套循环
```

即使 `table_size` 不是 `k` 的倍数，`h1` 的输出在「模 `k` 固定」的约束下也高度相关，分布远不如独立哈希均匀。**必须用统计独立的 `h2`**（不同算法，或同算法不同种子）。

**这个「同一个跨表、不同个桶内」的规则与第 11 讲外部哈希聚合完全同构**：

| | 外部哈希聚合 | GRACE 哈希连接 |
|---|---|---|
| 跨分区 | `h1`，**同表内自洽** | `h1`，**两表必须相同** |
| 分区内 | `h2 ≠ h1` | `h2 ≠ h1` |

**差异点**：聚合只处理一张表，所以 `h1` 只需自洽；连接处理两张表，所以 `h1` 还必须**跨表一致**。这是连接比聚合多出来的一条约束。

**递归分区时同理**：若桶 `i` 仍太大，用 `h2` 把它再分成 `i'`、`i''`、`i'''`——**两张表必须用同一个 `h2`**，否则子桶又对不上。讲义第 116–121 页的图示正是这个结构。

</details>

**Q3.** 排序归并连接的最坏情况代价是 `M × N + sort cost`。请构造一个具体例子说明为什么，并说明真实系统中为什么很少遇到。若确实遇到（例如连接键是低基数的 `status` 列），有什么补救办法？

<details><summary>参考答案</summary>

**最坏情况的构造**：

讲义原文：「The worst case for the merging phase is when the join attribute of all the tuples in both relations contains the same value.」

```
R: 1000 页, 100,000 个元组，全部 status = 'active'
S:  500 页,  40,000 个元组，全部 status = 'active'
```

排序后（全同键，排序不改变任何东西）：

```
cursorR 指向 R 的第 1 个元组
cursorS 指向 S 的第 1 个元组
→ 匹配 → emit
→ increment cursorS（S 还有 39,999 个同键元组）
→ 匹配 → emit
→ ... 重复 40,000 次
→ cursorS 耗尽，backtrack 回 S 的第 1 个元组
→ increment cursorR（R 还有 99,999 个）
→ 重复上面 40,000 次
→ ...
```

**总输出 = 100,000 × 40,000 = 4 × 10⁹ 行**。

**归并阶段的 I/O**：

```
对 R 的每个元组，都要把 S 完整扫一遍（因为要 backtrack）
→ 归并 I/O ≈ m/M × ... 实际是 M × N（按页算）
→ 1000 × 500 = 500,000 次 I/O
```

**注意这里的关键**：即使 S 只有 500 页，反复 backtrack 会让它被读 `M = 1000` 遍。**归并退化成嵌套循环**。

**总代价**：

```
Total = M × N + sort cost
      = 500,000 + 7,500  （sort cost 见例题）
      = 507,500 次 I/O
      ≈ 50.75 秒（0.1 ms/IO）
```

**对比正常情况**：

```
正常（键近似唯一）:  M + N + sort = 1500 + 7500 = 9,000 次 I/O ≈ 0.9 秒
最坏（全同键）:      507,500 次 I/O ≈ 50.75 秒
放大倍数:            56 倍
```

**真实系统为什么很少遇到**：

1. **连接键通常是主键/外键**：主键唯一，外键的选择性也高（如 `sid`、`order_id`）。所以「所有元组同键」几乎不可能。
2. **规范化设计的自然结果**：连接键通常是实体标识符（entity identifier），按定义就是高基数的。
3. **即使有重复，重复度也有限**：例如「一个学生选 5 门课」，重复度 5，归并只需多扫 5 遍，代价 `5 × N` 而非 `M × N`。

**一般化的代价**（设 R 中每个键平均重复 `d_R` 次，S 中 `d_S` 次）：

```
归并 I/O ≈ M + N + (重复带来的额外回溯)
若最坏单键重复 d_R = m、d_S = n → M × N
若平均重复较小 → 接近 M + N
```

**补救办法（低基数连接键，如 `status`）**：

**方案 1：改用哈希连接**（最优）

```
status 只有 3 个值 → 哈希表只有 3 个桶
build 阶段：把 R 按 status 分到 3 个桶
probe 阶段：S 的每个元组只与同 status 的桶比较
代价：3(M + N) = 4,500 次 I/O ≈ 0.45 秒
```

**但要注意**：若 90% 的行都是 `'active'`，那一个桶仍然巨大 → 触发 GRACE 的「单键过多」边界情况 → 对该键改用块嵌套循环。**哈希连接也有倾斜问题，只是形式不同。**

**方案 2：GRACE 的「单键专用块嵌套循环」**

讲义第 111 页的原话：

```
If a single join key has too many matching records that do not fit in
memory, use a block nested loop join just for that key.
  → Avoids random I/O in exchange for sequential I/O.
```

即：把热点键（`'active'`）单独拿出来做块嵌套循环（顺序扫描），其余键走哈希。**用顺序 I/O 换随机 I/O**。

**方案 3：位图连接（bitmap join）**

若一个表的连接键基数极低（如 `status`），可以给每个取值建一个**位图**：

```
status='active'   → 位图 1101110010...
status='inactive' → 位图 0010001101...
```

连接变成**位图 AND 运算**（CPU 一条指令处理 64 位）。这是数据仓库的经典优化，PostgreSQL、Oracle 都支持。

> 待核实：位图连接讲义未涉及，属补充背景。

**方案 4：广播连接（broadcast join）**

若一张表极小（如 `status` 的维表只有 3 行），直接把它**复制到每个节点/每个线程**，然后在另一张表上做过滤式扫描。分布式系统（Spark、Presto）的标准优化。

**方案 5：接受它，改用排序聚合的思路**

若查询其实是 `SELECT status, COUNT(*) FROM R JOIN S ... GROUP BY status`，那么**根本不需要物化 4×10⁹ 行**——可以在归并过程中**边扫边累加**。这是「聚合下推」的思想：把 `COUNT/SUM` 推到连接内部，避免物化中间结果。

**这是最重要的补救思路**：**最坏情况的「4×10⁹ 行输出」往往根本不需要产生**。查询优化器若能识别「连接后立即聚合」，就可以把代价从 `O(m×n)` 降到 `O(m+n)`。

**总结判断**：

| 情形 | 选择 |
|---|---|
| 连接键近似唯一 | 排序归并或哈希都行 |
| 连接键低基数、分布均匀 | **哈希连接**（桶均匀） |
| 连接键低基数、严重倾斜 | 哈希 + 热点键块嵌套循环，或位图连接 |
| 连接后立即聚合 | 把聚合下推到连接，避免物化 |

</details>

**Q4.** 请完整推导 GRACE 哈希连接的 `3(M + N)`，说明每一项的 I/O 来源。若发生一次递归分区（某个桶装不下），代价会变成多少？为什么 hybrid hash join 在实践中很少用？

<details><summary>参考答案</summary>

**`3(M + N)` 的逐项推导**：

**Partition 阶段**：

```
对表 R（M 页）:
  读一遍 R                    → M 次 I/O
  把 R 的元组按 h1 写到 k 个桶  → 每个元组写一次，共 M 页 → M 次 I/O
  小计                        → 2M

对表 S（N 页）:
  读一遍 S                    → N 次 I/O
  写到 k 个桶                  → N 次 I/O
  小计                        → 2N

Partition 阶段合计 = 2M + 2N = 2(M + N)
```

**Probe 阶段**：

```
逐对读入对应的桶（R 的第 i 桶 + S 的第 i 桶）:
  读 R 的所有桶（总共 M 页）    → M 次 I/O
  读 S 的所有桶（总共 N 页）    → N 次 I/O
  在内存里建哈希表并连接        → 0 次 I/O（哈希表在内存）
  输出结果                     → 不计（约定见第 5.4 节）

Probe 阶段合计 = M + N
```

**总计**：

```
3(M + N)
```

**注意几个容易算错的地方**：

1. **Partition 阶段为什么是 `2(M+N)` 而不是 `(M+N)`**：既要**读**原表，又要**写**分区文件。每个元组被读写各一次。
2. **Probe 阶段为什么没有「写」**：哈希表建在内存里，不落盘。连接结果不计入代价。
3. **为什么不是 `2(M+N) + 2(M+N)`**：Probe 阶段不重写分区文件——它是**读**分区、建内存表、输出结果，不产生新的磁盘写（除输出外）。
4. **哈希表本身的 I/O 为 0 的前提**：每个分区（R 的第 i 桶 + S 的第 i 桶）必须**能装进内存**。这正是「无递归分区」的前提条件。

**例题验证**：

```
M = 1000, N = 500
3 × (1000 + 500) = 4,500 次 I/O
4,500 × 0.1 ms = 450 ms = 0.45 秒  ✓
```

**发生一次递归分区后的代价**：

设桶 `P1` 装不下，需要对它再分区。设 `P1` 占 R 的 `α` 比例、S 的 `β` 比例（通常 `α ≈ β ≈ 1/k`）。

```
额外的递归分区 I/O:
  读 P1 的 R 部分 + 写子桶   → 2αM
  读 P1 的 S 部分 + 写子桶   → 2βN

额外 I/O = 2(αM + βN)

若 α = β = 1/k:
额外 I/O = 2(M + N)/k
```

**新的总代价**：

```
Total = 3(M + N) + 2(M + N)/k
      = (3 + 2/k)(M + N)
```

**定量**（`k = 16`，`M+N = 1500`）：

```
无递归:  3 × 1500 = 4,500
一次递归: (3 + 2/16) × 1500 = 3.125 × 1500 = 4,687.5
增加:    187.5 次 I/O，约 4.2%
```

**关键洞察：一次递归分区的代价增量很小**（约 `2/k` 倍）。这是因为递归只作用于**一个桶**（总量的 `1/k`），而不是整张表。**只有当几乎所有桶都需要递归时，代价才会显著上升**——那时说明 `k` 选得太小，应该一开始就用更大的 `k`。

**多次递归的极端情况**：若分区严重倾斜，某个桶递归 `d` 层：

```
Total ≈ 3(M+N) + 2(M+N)/k + 2(M+N)/k² + ...
      ≈ 3(M+N) × (1 + 1/(k-1))
```

对 `k = 16`，最坏约 `3 × 1.067 = 3.2` 倍——**仍然可控**。这就是 GRACE 的鲁棒性：**递归分区的代价是对数级增长，不是指数级**。

**但真正的危险不是 I/O，是「递归无法终止」**：若单个键的匹配行数就超过内存（如 90% 的行同键），递归多少层都没用——那个桶永远装不下。这时必须回退到块嵌套循环（讲义第 111 页的边界情况）。

**hybrid hash join 为什么实践中很少用**：

讲义 notes 原话：「**Difficult to implement correctly and rarely done in practice.**」

**四个原因**：

1. **缓冲池大小是运行时才知道的、且会变**
   ```
   Hybrid 的前提是「B > k」，即缓冲池页数大于分区数。
   但 B 是动态的：
     - 其他算子可能正在占用缓冲池
     - 缓冲池替换策略可能驱逐本算子的页
     - 并行执行时每个 worker 分到的页数不确定
   → 无法在分区阶段可靠判断「能否把分区 0 留在内存」
   ```

2. **分区 0 的大小不可控**
   ```
   若哈希分布不均，分区 0 可能远大于 1/k
   → 留它进内存会挤占其他分区
   → 或者装不下，中途被迫落盘（此时已浪费了内存驻留的时间）
   → 需要复杂的「先试后弃」逻辑
   ```

3. **与递归分区的交互复杂**
   ```
   分区 0 溢出时怎么办？
     - 递归分区？但它已经在内存里了
     - 回退到落盘？那前面的内存连接白做了
     - 部分落盘？需要跟踪哪些元组已连接、哪些没有
   → 状态机爆炸
   ```

4. **收益有限**
   ```
   只省分区 0 的「写一次 + 读一次」= 2(|R₀| + |S₀|) ≈ 2(M+N)/k
   对 k = 16: 省 12.5% 的 I/O
   而 GRACE 本身已是 3(M+N)，省 12.5% → 2.75(M+N)
   → 从 0.45 秒降到 0.41 秒
   ```

**「9% 的性能提升换一个状态机爆炸的实现」——工程上不划算。**

**这与本课程反复出现的主题一致**：优化必须值得它带来的复杂度。对照：

| 优化 | 收益 | 复杂度 | 工业采用 |
|---|---|---|---|
| Probe filter（布隆） | 大（省大量 cache miss） | 低（一个位数组） | **广泛** |
| 递归分区 | 必需（否则装不下） | 中 | **广泛** |
| Hybrid hash join | 小（~12%） | 高（状态机） | **罕见** |
| Bε-tree | 中 | 高 | 少数（Tokutek/TokuDB） |
| ARC 替换策略 | 中 | 中 | 少数（DB2/PG/ZFS） |

**替代方案**：现代系统更倾向于**运行时自适应**——先按 GRACE 分区，若发现分区 0 恰好能装进内存，就在 probe 阶段直接跳过落盘（这不需要在分区阶段做决定，只需在 probe 时检查）。**把「决策」推迟到信息最充分的时刻**，比在分区阶段猜测更简单也更可靠。

</details>

**Q5.** 讲义结论说「hashing is almost always better than sorting for operator execution」，但列了三条 caveat。请逐条说明其机理，并给出一个「排序确实更优」的具体查询例子。若在内存数据库中（数据全在 RAM），结论会如何变化？

<details><summary>参考答案</summary>

**三条 caveat 的机理**：

**Caveat 1：非均匀数据（non-uniform data / 数据倾斜）**

```
哈希连接的代价取决于「最大的分区有多大」
  → 若某键占 90%，它的分区是平均值的 9k 倍
  → 该分区装不进内存 → 递归分区
  → 若单键匹配行数就超内存 → 递归也无法解决 → 回退块嵌套循环

排序的代价只取决于「数据总页数」
  → run 大小 = B 页，与键分布完全无关
  → 归并的每一路都是均匀的
  → 倾斜不影响 I/O
```

**定量对比**（`M=1000, N=500`，一个键占 R 的 90%）：

```
哈希连接: 90% 的数据落在一个分区 → 该分区无法装内存
         → 递归分区无效（单键）→ 回退块嵌套循环处理该键
         → 代价 ≈ 3(M+N) + 块嵌套循环的热点部分
         ≈ 4,500 + (0.9M × 0.9N 的扫描) 可能远超 3(M+N)

排序归并: 排序代价与分布无关 = 7,500
        归并阶段：该键有 0.9m × 0.9n 个匹配 → 输出爆炸
        但若只算 I/O 不算输出：归并仍约 M+N（除非单键全同）
```

**结论**：倾斜严重时排序更**可预测**，而哈希可能退化成嵌套循环。

**Caveat 2：数据已按连接键有序**

```
Sort-Merge 的排序阶段可以完全跳过:
  代价 = M + N（只剩归并）
  = 1,500 次 I/O

Hash 的代价 = 3(M + N) = 4,500 次 I/O
```

**排序归并快 3 倍**。有序性的来源：

- **聚簇索引**：沿叶子链表扫描直接得到有序数据。
- **上游算子已经排过序**：如前面的 `ORDER BY` 或另一个 sort-merge join 的输出。
- **表本身按该键物理有序**（如按时间追加的日志表）。

**Caveat 3：结果需要有序**

```sql
SELECT * FROM R JOIN S ON R.id = S.id ORDER BY R.id;
```

```
Hash:        3(M+N) + 后续 ORDER BY 的排序代价 2×(结果页数)×passes
Sort-Merge:  M+N + sort cost，输出天然有序，无需额外排序
```

**关键**：哈希连接的输出**无序**，必须再排一次。而结果集可能很大（`m × n` 最坏），二次排序的代价可能超过哈希省下的部分。

**一个「排序确实更优」的具体例子**：

```sql
-- 场景：R 按 id 聚簇（主键），S 按 rid 有聚簇索引
-- 查询需要按 id 有序输出，且两表都很大
SELECT R.id, R.name, S.value
FROM R JOIN S ON R.id = S.rid
WHERE R.id BETWEEN 1000 AND 2000
ORDER BY R.id;

代价分析（设 R、S 各 10,000 页）:

Hash 连接:
  build R 的 1000 行（假设过滤后很少）→ 但 S 要全表扫描
  = 3 × (10,000 + 10,000) = 60,000 次 I/O
  + 输出排序（若结果大）→ 更多

Sort-Merge:
  R 用聚簇索引范围扫描 → 只需读 100 页（范围小）
  S 已按 rid 聚簇 → 沿索引走，只需读匹配部分
  = 100 + (匹配的 S 页) ≈ 几百次 I/O
  + 输出天然有序，零排序成本
```

**这个例子里 sort-merge 快 100 倍以上**——因为**聚簇索引同时解决了「有序输入」和「范围裁剪」两个问题**，而哈希连接必须全表扫描。

**另一个例子：非等值连接**

```sql
SELECT * FROM orders o JOIN shipments s
ON o.order_date <= s.ship_date
AND o.order_date >= s.ship_date - INTERVAL '7 days';
```

**哈希连接完全不可用**（非等值）。只能：

- 排序归并（按日期排序后区间扫描）——**高效**
- 嵌套循环——**慢**

这是 sort-merge 的**独占领域**。

**内存数据库中的结论反转**：

本讲全部结论建立在「**I/O 主导**」上（`0.1 ms` 一次 I/O vs 纳秒级比较，差 5–6 个数量级）。在内存数据库中：

```
1. 没有磁盘 I/O → 代价模型变成「CPU cycles + cache miss」
2. 哈希连接的随机探测 = 每次一次 cache miss（~100 ns）
   哈希表大小几 MB 到几 GB → 几乎必然 miss
3. 排序归并的顺序扫描 = 预取友好、可 SIMD 向量化
   → 每次比较 ~1 ns（若数据在 L1/L2）
```

**具体反转**：

| 维度 | 磁盘导向 | 内存导向 |
|---|---|---|
| 瓶颈 | I/O 次数 | CPU cache miss |
| 哈希连接 | 优（`3(M+N)` I/O） | 随机访问导致大量 cache miss |
| 排序归并 | 差（排序要多次读写） | **优**（顺序访问、可向量化） |
| 赢家 | **哈希** | **常是排序归并**（或 radix join） |

**学术界的实测**：Balkesen、Alonso、Teletia、Kossmann，*Multi-Core, Main-Memory Joins: Sort vs. Hash Revisited*（VLDB 2013）的结论是：在内存多核场景下，**精心实现的 radix hash join 与 sort-merge join 性能接近**，哈希略优但优势远没有磁盘时代那么大；而**朴素的哈希实现会被排序归并打败**。

**现代系统的实际做法**：

- **DuckDB**：内存执行，但用**向量化 + radix partitioning**，哈希连接仍是默认。
- **HyPer**：主张**编译执行（code generation）**，把连接逻辑编译成机器码，两种算法都能高度优化。
- **SQL Server**：同时实现 hash join、merge join、nested loop，优化器按统计信息选。
- **PostgreSQL**：同样三种都有，且支持并行哈希连接。

**本讲的结论要这样理解**：

```
「hashing is almost always better」的完整表述是：
  「在磁盘导向的 DBMS 中，以 I/O 次数为代价度量时，
    哈希连接几乎总是优于排序归并」

三个限定条件缺一不可：
  ① 磁盘导向
  ② I/O 为代价度量
  ③ 二元内等值连接
```

**这也解释了为什么讲义最后说「Good DBMSs use either (or both)」**——真正的工程答案是**都实现、让优化器按实际代价选**，而不是硬编码某一种。

</details>

## 12. 进一步学习

- 上一讲：[[15-445-11-Sorting-and-Aggregation]] —— 外部归并排序（sort-merge join 的排序阶段直接复用它）、Top-N 堆、哈希聚合。
- 下一讲：[[15-445-14-Query-Execution-I]] —— 查询执行的处理模型（迭代器模型 / 物化模型 / 向量化模型）与数据在算子间如何流动。
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]、[[40-CMU-15-445/04-学习进度|CMU 15-445 - 学习进度]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：Graefe, *Query Evaluation Techniques for Large Databases*, ACM Computing Surveys 1993 —— 连接算法的权威综述，五种算法的代价分析讲得最系统。
- 延伸阅读：Mishra & Eich, *Join Processing in Relational Databases*, ACM Computing Surveys 1992 —— 连接算法的经典分类学。
- 延伸阅读：Fushimi et al., *An Overview of the System Software of a Parallel Relational Database Machine GRACE*, VLDB 1986 —— GRACE 哈希连接的原始文献。
- 延伸阅读：DeWitt et al., *Implementation Techniques for Main Memory Database Systems*, SIGMOD 1984 —— 内存数据库中连接算法的早期分析（哈希 vs 排序的第一次大讨论）。
- 延伸阅读：Balkesen et al., *Multi-Core, Main-Memory Joins: Sort vs. Hash Revisited*, VLDB 2013 —— 内存多核时代「排序 vs 哈希」的实测结论。
- 延伸阅读：Ngo, Ré, Rudra, *Worst-Case Optimal Join Algorithms*, JACM 2018 —— 讲义提到的「多路连接主要在研究文献」的具体内容。
- 延伸阅读：Blanas et al., *Design and Evaluation of Main Memory Hash Join Algorithms for Multi-core CPUs*, SIGMOD 2011 —— 无分区哈希连接 vs 分区哈希连接的实测对比。
- 动手建议：用 Python 实现五种连接算法，在同一份数据上跑一遍，统计**实际 I/O 次数**（用一个带计数器的「假磁盘」模拟），验证本讲的所有公式。重点验证两件事：① 块嵌套循环在 `M ≤ B-2` 时降到 `M+N`；② 排序归并在所有键相同时退化成 `M×N`。再画一张「代价 vs B」的曲线，观察双曲线的陡峭区间。
