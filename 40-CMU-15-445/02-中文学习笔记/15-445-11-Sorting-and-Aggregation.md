---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: L11
topic: Sorting & Aggregation Algorithms — External Merge Sort, Top-N Heap, Hash Aggregation
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 数据库
  - 外部排序
  - 归并排序
  - 聚合
  - 哈希聚合
---

# 15-445 L11：排序与聚合算法（Sorting & Aggregation Algorithms）

> 前十讲都在讲**访问方法**（access methods）——数据怎么存、怎么找。从本讲开始进入**查询执行**（query execution）：SQL 被编译成算子树，每个算子要真正跑起来。两个最基础、也最常被复用的算子是**排序**与**聚合**：JOIN、DISTINCT、GROUP BY、窗口函数、B+ 树批量加载全都要用它们。核心约束只有一条——**数据可能装不进内存**，所以算法必须按「磁盘 I/O 次数」而不是「比较次数」来设计。

## 1. 本节学习目标

学完本讲，你应该能够：

1. 说明为什么关系模型本身无序，但 DBMS 仍然频繁需要排序（至少四个理由）。
2. 区分**早物化（early materialization）** 与**晚物化（late materialization）**，并说明各自在什么场景下更优。
3. 推导 **2-way external merge sort** 的 pass 数与 I/O 代价公式 `1 + ⌈log₂N⌉` 与 `2N × passes`。
4. 推导 **k-way（general）external merge sort** 的公式 `1 + ⌈log_{B-1}⌈N/B⌉⌉`，并手算 `N=108, B=5` 需要 4 个 pass。
5. 说明 **double buffering** 如何重叠 CPU 与 I/O，以及它为什么把可用缓冲页数减半。
6. 判断什么时候可以用 **B+ 树**代替外部排序，说明聚簇与非聚簇索引的差别（后者「几乎总是坏主意」，除 Top-N）。
7. 说明 **Top-N heap sort** 为什么只需扫一遍数据，以及 `WITH TIES` 如何扩展堆。
8. 解释 **collation（排序规则）** 为什么使字符串比较不通用，描述 ICU 的多级比较（primary/secondary/tertiary）与 sort key 预计算。
9. 说出三种比较优化（代码特化、后缀截断、键归一化）。
10. 对比**排序聚合**与**哈希聚合**，推导 **external hashing aggregate** 的两阶段（Partition + ReHash）与 `B-1` 个分区的来源。
11. 说明聚合的**运行值（running value）** 表示法，例如 `AVG → (COUNT, SUM)`。

## 2. 前置知识

- **缓冲池**：见 [[15-445-04-Memory-Management]]；外部排序的所有 I/O 都通过缓冲池，`B` 就是分到的缓冲页数。
- **B+ 树与聚簇索引**：见 [[15-445-08-Indexes-and-Filters-I]]；「用索引代替排序」的前提是理解聚簇与非聚簇。
- **哈希表与哈希函数**：见 [[15-445-07-Hash-Tables]]；哈希聚合与外部哈希聚合都建立在它之上。
- **页与记录 id**：见 [[15-445-03-Database-Storage-I]]；晚物化存的就是 record id。
- **早/晚物化与压缩**：见 [[15-445-06-Storage-Models-and-Compression]]；「延迟物化」在那里是压缩原则，在这里是排序/连接的设计选择。
- **SQL 的 ORDER BY / GROUP BY / DISTINCT**：见 [[15-445-02-Modern-SQL]]。

## 3. 核心概念

### 3.1 Query Plan（查询计划）

DBMS 把 SQL 编译成的**算子树（或 DAG）**。数据从叶子向上流向根，根的输出就是查询结果。例如 `SELECT R.id, S.cdate FROM R JOIN S ON R.id = S.id WHERE S.value > 100` 会被编译成「扫描 R、扫描 S → 连接 → 过滤 `value > 100` → 投影 `R.id, S.cdate`」的树。

### 3.2 Operator（算子）

查询计划中的一个执行单元，如 scan、filter、project、join、sort、aggregate。本讲讲 sort 与 aggregate 两个。

### 3.3 External Merge Sort（外部归并排序）

当数据大于内存时的标准排序算法。分治：先把数据切成能装进内存的块分别排序写成**归并段（run）**，再反复归并成更长的段。两个阶段：**Phase #1 Sorting**（排序并落盘）、**Phase #2 Merging**（归并）。

### 3.4 Run（归并段）

一次排序产生的一段**已有序**数据。Pass #0 产生的 run 长度为 B 页（B = 可用缓冲页数），之后每个 pass 把若干 run 合并成一个更长的 run。

### 3.5 Pass（趟）

一次「读遍全部数据、写遍全部数据」的过程。外部排序的代价用 **pass 数** 衡量，因为每趟对每一页都要读一次写一次。

### 3.6 Early / Late Materialization（早物化 / 晚物化）

排序时「值」存什么：

- **早物化**：run 里存**完整元组**。后续归并时不必回表，但 run 更大、I/O 更多。
- **晚物化**：run 里只存**键 + record id**。run 更小、排序更快，但最后要按 id 回表取元组（随机 I/O）。

### 3.7 Double Buffering（双缓冲）

在后台**预取**下一个 run 到第二组缓冲区，同时前台处理当前 run。让 CPU 计算与磁盘 I/O 重叠进行。代价：可用缓冲页数**减半**（一半给当前、一半给预取）。

### 3.8 Top-N Heap Sort（Top-N 堆排序）

当查询是 `ORDER BY ... LIMIT N` 时，只需**扫一遍**数据，用一个大小为 N 的**优先队列（堆）**维护「目前见过的最好的 N 个」。理想情况是 N 个元素能全部放进内存。

### 3.9 Collation（排序规则）

定义字符串如何比较与排序的规则集合：字符顺序、相等比较（`=`、`LIKE`）、大小写敏感性、重音敏感性、区域特定规则。**二进制排序最快，但不符合人类语言习惯**（ASCII 序 ≠ 语言序）。

### 3.10 Unicode Collation Algorithm（UCA，Unicode 排序算法）

ICU 库实现区域感知比较的算法。不直接比较 Unicode 码点，而是把字符串转成**多级排序元素（collation elements）**，再按级别逐级比较。

### 3.11 Sort Key（排序键 / 预计算比较键）

因为多级比较很贵，DBMS 会**预先算出**每个字符串的排序键（一串编码后的权重），之后比较两个排序键就是一次 `memcmp`。

### 3.12 Code Specialization（代码特化）

不为排序算法传入函数指针做比较，而是**为特定键类型生成硬编码的排序版本**（C++ 里是模板特化）。消除每次比较的间接调用。

### 3.13 Suffix Truncation（后缀截断）

比较长 `VARCHAR` 时，先比**二进制前缀**；前缀相等才回退到完整字符串比较。

### 3.14 Key Normalization（键归一化）

把变长属性转换成**定长、保序**的编码/填充字符串，使比较变成定长 `memcmp`。

### 3.15 Aggregation（聚合）

把多个元组的一个属性值**折叠成一个标量值**。两种实现：**排序**与**哈希**。

### 3.16 Running Value（运行值 / 中间状态）

聚合过程中为每个分组维护的部分结果。不同聚合函数的运行值不同：`AVG → (COUNT, SUM)`、`MIN → (MIN)`、`MAX → (MAX)`、`SUM → (SUM)`、`COUNT → (COUNT)`。

### 3.17 External Hashing Aggregate（外部哈希聚合）

哈希表装不进内存时的分治聚合。**Phase #1 Partition**：用 `h1` 把元组按分组键分到 `B-1` 个磁盘分区；**Phase #2 ReHash**：逐个分区读入内存，用**不同的** `h2` 建哈希表并计算聚合。

## 4. 通俗理解

- **外部归并排序 = 整理一整屋子的扑克牌**。桌子只能摊下 100 张（内存 = 缓冲池）。你先把牌分成一堆堆 100 张，每堆在桌上排好序、装盒贴标签（**Phase #1：生成 run**）。然后把若干盒倒出来，同时摊在桌上做「多路归并」——每次从各盒顶端挑最小的一张放到新盒（**Phase #2：merge**）。盒子越并越大，直到只剩一盒。
- **Double buffering = 一边炒菜一边让外卖小哥去取下一批食材**。灶台就那么大（缓冲池），但你可以让小哥在你炒当前这道菜时把下一批送到门口，而不是炒完了才让他出门。代价是灶台上要留一块地方放「已送到但还没用」的食材——可用空间少了一半。
- **Top-N = 只记前十名**。你不必把全年级的成绩单排序，只要拿一张纸记着「目前最好的 10 个分数」，每来一个人就比一下：比第 10 名高就挤掉他。一遍扫完就有答案。
- **Collation = 不同语言的字典顺序**。德语里 `Ä` 排在 `A` 附近（当作 `Ae`），ASCII 里 `Ä` 因为码点大而排在 `z` 后面。同一批名字，两本字典给出两种顺序——所以「字符串比较」没有唯一正确答案。
- **多级比较 = 先比姓氏再比名字再比大小写**。先看基字母（`a` vs `b`），相同再看重音（`e` vs `é`），再相同才看大小写（`a` vs `A`）。这就是 ICU 的 primary / secondary / tertiary。
- **哈希聚合 = 按分组直接扔进不同的桶**。要统计每个班的平均分，你不需要先按班级排序，只要准备一堆标着班号的桶，来人就往对应桶里扔，最后每个桶单独算。

具体数字：`N = 108` 页数据、`B = 5` 个缓冲页。Pass #0 产出 `⌈108/5⌉ = 22` 个 5 页的 run（最后一个只有 3 页）；Pass #1 每次合并 4 个 run，得到 `⌈22/4⌉ = 6` 个 run；Pass #2 得到 2 个 run（80 页 + 28 页）；Pass #3 得到完整的 108 页有序文件。**共 4 个 pass，总 I/O = 2 × 108 × 4 = 864 次页读写**。若只有 3 个缓冲页做 2-way，则需要 `1 + ⌈log₂108⌉ = 8` 个 pass，I/O 翻倍到 1728 次——**多用 2 个缓冲页就把 I/O 砍了一半**。

## 5. 原理与推导

### 5.1 为什么必须排序：四个理由

讲义第 6 页：

```
Relational model/SQL is unsorted.
Queries may request that tuples are sorted in a specific way (ORDER BY).
But even if a query does not specify an order, we may still want to sort
to do other things:
  → Duplicate elimination (DISTINCT).
  → Bulk loading sorted tuples into a B+Tree index is faster.
  → Aggregations (GROUP BY), Window Functions
```

**关系模型无序**是根本原因：SQL 表是**集合/包**，没有「第几行」的概念。所以任何「有序」的需求都必须由算子显式产生。

**四个隐含用途**：

1. **DISTINCT**：排序后相同值相邻，顺序扫一遍去重即可（`O(n)` 而非哈希的额外空间）。
2. **B+ 树批量加载**：按序插入可以总是填最右叶子，避免随机 I/O 与频繁分裂——比乱序插入快一个数量级。
3. **GROUP BY**：排序后同组相邻，顺序扫一遍累加运行值。
4. **窗口函数**：`ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)` 天然需要分组内有序。

### 5.2 排序算法的接口与两种物化

讲义第 7 页定义了排序算子的输入输出：

```
For a given input run (i.e., list of key/value pairs), sort it based on a
comparison function and sorting parameters.

Key:   The attribute(s) to compare to compute the sort order.
Value: Two choices
  → Tuple (early materialization)
  → Record ID (late materialization)
```

```
Early Materialization:          Late Materialization:
  K1 <Tuple Data>                 K1  Record ID / Offset
  K2 <Tuple Data>                 K2  Record ID / Offset
  ...                             ...
  Kn <Tuple Data>                 Kn  Record ID / Offset
```

**权衡**：

| | 早物化 | 晚物化 |
|---|---|---|
| run 的大小 | 大（含全部属性） | 小（只有键 + id） |
| 排序阶段的 I/O | 多 | **少** |
| 归并阶段的 I/O | 多（搬整行） | **少** |
| 最终取元组 | 无需回表 | 需按 id **随机**回表 |
| 适合 | 宽表但行数少；后续还要用多个属性 | 窄键 + 宽表；只需少量列 |

**为什么晚物化通常更优**：外部排序的代价是 I/O 次数，而 I/O 量与「每页能装多少条记录」直接相关。只存 8 字节键 + 8 字节 record id（16 字节）比存一整行（可能几百字节）能让每页装几十倍多的记录，pass 数因此大幅下降。代价是最后要回表——但那是**一次**随机读，而归并阶段省下的是**每趟**的顺序 I/O。

这与第 6 讲的「压缩必须尽可能推迟解压（late materialization）」是同一思想：**尽早丢弃不需要的信息，把昂贵的操作推到最后一刻**。

### 5.3 2-way external merge sort 的推导

**设定**：N = 数据总页数，B = 可用缓冲页数。最简单的版本只用 `B = 3`（2 个输入页 + 1 个输出页）。

**Pass #0（排序阶段）**：

```
读一页 → 在内存中排序 → 写回磁盘，成为一个 1 页的 run
重复，直到全表变成 N 个 1 页的 run
```

**Pass #1, 2, 3, …（归并阶段）**：

```
每次取两个 run，各用 1 个输入页，归并输出到 1 个输出页
输出页满了就写回磁盘，换一个空页
每趟把 run 的长度翻倍：1 → 2 → 4 → 8 → ...
```

**pass 数推导**：

```
Pass #0 之后有 N 个长度为 1 的 run
Pass #1 之后有 N/2 个长度为 2 的 run
Pass #2 之后有 N/4 个长度为 4 的 run
...
经过 k 趟归并后有 N/2^k 个 run
要只剩 1 个 run：N/2^k = 1 → k = log₂N

总 pass 数 = 1（排序）+ ⌈log₂N⌉（归并）
```

**I/O 代价**：

```
每一趟都要把每一页读一次、写一次 → 2N 次 I/O
总 I/O = 2N × (1 + ⌈log₂N⌉)
```

讲义第 13 页的图示正是这个链条：`1-Page Runs → 2-Page Runs → 4-Page Runs → 8-Page Runs`，对应 `Pass #0 → #1 → #2 → #3`。

**为什么 B = 3 不够好**（第 14 页）：

```
This algorithm only requires three buffer pool pages to perform the
sorting (B=3).
  → Two input pages, one output page
But even if we have more buffer space available (B>3), it does not
effectively utilize them if the worker must block on disk I/O…
```

即：有更多缓冲页却不用，等于浪费；而且单线程阻塞在 I/O 上时 CPU 闲置。

### 5.4 General (k-way) external merge sort 的推导

**改进**：把全部 B 个缓冲页都用上。

**Pass #0（排序阶段）**：

```
一次读入 B 页 → 在内存中排序 → 写回，成为一个 B 页的 run
产出 ⌈N / B⌉ 个 run
```

**Pass #1, 2, …（归并阶段）**：

```
用 B-1 个缓冲页做输入（每个 run 占 1 页），1 个缓冲页做输出
一次可归并 B-1 个 run（B-1 路归并）
每趟把 run 数除以 (B-1)
```

**为什么是 B-1 路而不是 B 路**：归并需要**同时**把每个输入 run 的当前页放在内存里，还要有一页放输出。所以输入缓冲 = `B - 1`，输出缓冲 = `1`。

**pass 数推导**：

```
Pass #0 后：⌈N/B⌉ 个 run
每趟除以 (B-1)：经过 k 趟后剩 ⌈N/B⌉ / (B-1)^k 个 run
要剩 1 个：k = ⌈log_{B-1}⌈N/B⌉⌉

总 pass 数 = 1 + ⌈log_{B-1}⌈N/B⌉⌉
总 I/O    = 2N × (1 + ⌈log_{B-1}⌈N/B⌉⌉)
```

**讲义例题完整推导**（第 16 页，`N = 108, B = 5`）：

```
Pass #0: ⌈N / B⌉   = ⌈108 / 5⌉ = 22 个 run，每个 5 页
                    （最后一个 run 只有 108 - 21×5 = 3 页）
Pass #1: ⌈N' / (B-1)⌉ = ⌈22 / 4⌉ = 6 个 run
                    前 5 个各含 4 个 run = 20 页，最后一个含 2 个 run = 8 页
Pass #2: ⌈N'' / (B-1)⌉ = ⌈6 / 4⌉ = 2 个 run
                    第一个 80 页（4 个 20 页 run），第二个 28 页
Pass #3: 1 个 run，108 页 → 排序完成

公式验证: 1 + ⌈log_{B-1}⌈N/B⌉⌉ = 1 + ⌈log₄ 22⌉ = 1 + ⌈2.229...⌉ = 4 ✓
总 I/O = 2 × 108 × 4 = 864
```

**对比 B=3 的 2-way**：

```
1 + ⌈log₂ 108⌉ = 1 + ⌈6.755⌉ = 8 个 pass
总 I/O = 2 × 108 × 8 = 1728
```

**多 2 个缓冲页，pass 数从 8 降到 4，I/O 减半。** 这是本讲最重要的定量结论：**外部排序的性能由 B 决定，而 B 由缓冲池分配策略决定**（见第 4 讲的 multiple buffer pools）。

### 5.5 Double buffering：用空间换重叠

**问题**：单缓冲时，CPU 在等 I/O 完成的整个过程中闲置。一次磁盘页读入约 100 µs（SSD）到 10 ms（HDD），而归并一页只需几微秒——**CPU 利用率不到 1%**。

**方案**（第 17 页）：

```
Prefetch next run in the background and store in a second buffer while
processing the current run.
  → Overlap CPU and I/O operations
  → Reduces effective buffers available by half
```

```
        前台（计算）              后台（预取）
   ┌────────────────┐      ┌────────────────┐
   │ Buffer 组 A    │      │ Buffer 组 B    │
   │  输入 run 1..k │      │  输入 run 1..k │  ← 下一批
   │  + 输出页      │      │  + 输出页      │
   └────────────────┘      └────────────────┘
         ↓ 处理完切换            ↑ 正在填充
```

**代价的定量**：若总缓冲为 B，双缓冲后**有效** B 减半 → `B_eff = B/2`。代入公式：

```
pass 数 = 1 + ⌈log_{B/2 - 1}⌈N / (B/2)⌉⌉
```

**收益 vs 代价的判断**：

- 若 I/O 是瓶颈（HDD、冷数据），重叠的收益远大于「B 减半导致多一个 pass」的损失。
- 若数据基本在缓存里（热数据、内存数据库），双缓冲无益，反而浪费缓冲。
- 讲义 notes 强调：**这个优化需要多线程**——预取必须与计算真正并行，否则只是把等待挪了个位置。

### 5.6 用 B+ 树代替排序：两种情形天差地别

**前提**：表上已有排序属性的 B+ 树索引，且 DBMS 支持**前缀键扫描（prefix key scan）**。

**Case #1：聚簇索引（clustered）**（第 19 页）：

```
Traverse to the left-most leaf page, then retrieve tuples from leaf pages.
This is always better than external sorting because there is no
computational cost, and all disk access is sequential.
```

**为什么总是更优**：

- **零计算成本**：不需要比较、不需要归并，树已经排好了。
- **全顺序 I/O**：聚簇意味着元组的物理顺序与索引顺序一致，沿叶子链表走就是顺序读。
- **无额外空间**：不需要临时文件。

**Case #2：非聚簇索引（unclustered）**（第 20 页）：

```
Chase each pointer to the page that contains the data.
This is almost always a bad idea except for Top-N queries where N is
small enough relative to total number of tuples in table.
  → In general, one I/O per data record.
```

**为什么几乎总是坏主意**：非聚簇索引的叶子只存 record id，取元组要**跳到一个任意页**。若每页只取到一条记录就被丢弃（因为下一页在别处），就是**每条记录一次随机 I/O**。

**定量对比**（设 100 万条记录、每页装 100 条 → 1 万页）：

```
非聚簇索引扫描:  1,000,000 次随机 I/O（最坏）
外部排序:        2 × 10,000 × passes ≈ 2 × 10,000 × 3 = 60,000 次顺序 I/O
```

差了一个数量级以上。**唯一例外是 Top-N**：`ORDER BY x LIMIT 10` 只需取前 10 条，非聚簇索引顺着走 10 步就够，此时它比排序整个表快得多。

### 5.7 Top-N heap sort：一遍扫描

**条件**（第 21 页）：查询含 `ORDER BY` + `LIMIT`（可选 `WITH TIES`）。

```sql
SELECT * FROM enrolled
ORDER BY sid ASC
FETCH FIRST 4 ROWS WITH TIES
```

**算法**：

```
维护一个大小为 N 的优先队列（堆），存「目前见过的最好的 N 个」
扫描数据：
  若堆未满 → 直接插入
  若堆已满 → 与堆顶（当前第 N 名）比较：
      更优 → 弹出堆顶、插入新元素
      不优 → Skip!（讲义标注）
扫描结束 → 堆中即为答案，按序输出
```

**为什么只需一遍**：Top-N 是**流式可计算**的——每个元素只需与「当前第 N 名」比较一次就能决定去留，不需要看到全部数据才能判断。这与「排序」有本质区别（排序必须看完全部数据）。

**`WITH TIES` 的处理**：若第 N 名有并列，堆要**按需扩展**以容纳所有并列者。

```sql
-- 若 sid 的前 4 名是 1,2,3,4，且还有多个 sid=4 的记录
-- 则输出会超过 4 行，包含所有 sid=4 的记录
```

实现上：堆先按 N 建；扫描结束时若堆顶与下一个候选相等，就继续插入，直到遇到严格更差的为止。

**理想情况**（讲义原文）：N 个元素能**全部放进内存**，整个堆常驻缓冲区。若 N 大到装不下（如 `LIMIT 10000000`），退化为需要外部排序。

**与 B+ 树的配合**：非聚簇索引 + Top-N 是唯一「非聚簇索引扫描」划算的场景——因为只取 N 条，随机 I/O 只有 N 次。

### 5.8 Collation：为什么字符串比较没有唯一答案

**问题**（第 22 页）：

```
A collation defines the rules for comparing and sorting character strings.
  → Character ordering (ORDER BY)
  → Equality comparison (=, LIKE)
  → Case sensitivity
  → Accent sensitivity
  → Locale-specific rules

Binary collations are the fastest, but string comparison is not universal
  → ASCII Order ≠ Human Linguistic Order
```

**讲义的三行例子**：

| id | name | ASCII 排序 | 德语排序 |
|---|---|---|---|
| 1 | banana | Apple | Ängel |
| 2 | Ängel | banana | Apple |
| 3 | zebra | zebra | banana |
| 4 | Apple | Ängel | zebra |

- **ASCII 排序**：`Ä` 的码点（U+00C4 = 196）大于 `z`（122），所以 `Ängel` 排**最后**。讲义标注 "Non-ASCII Sorted Last"。
- **德语排序**：`Ä` 被视为 `Ae`，所以 `Ängel` 排在 `Apple` 之前（`Ae` < `Ap`）。讲义标注 'Handle "Ä" Similar to "Ae"'。

**结论**：同一批数据，两种 collation 给出两种「正确」顺序。所以 DBMS 必须知道列的 collation，且**索引的排序只在同一 collation 下有效**。

### 5.9 UCA 多级比较与 sort key

**ICU 的做法**（第 23–24 页）：

```
Rather than comparing raw Unicode code points, ICU converts strings into
collation elements with multiple comparison levels and then compares those
elements lexicographically.
  → Each character is mapped to one or more collation elements.
```

| 级别 | 含义 | 例子 |
|---|---|---|
| **Primary** | 基字母差异 | `a` vs `b` |
| **Secondary** | 重音差异 | `e` vs `é` |
| **Tertiary** | 大小写差异 | `a` vs `A` |
| **Quaternary** | 标点 / 决胜（可选） | — |

**比较顺序**：

```
1. 先比 primary weights（基字母）
2. 相等 → 比 secondary weights（重音）
3. 相等 → 比 tertiary weights（大小写）
4. 相等 → 继续（quaternary）
```

**讲义的编码示例**：

```
a  → (P1, S0, T1)
A  → (P1, S0, T2)
á  → (P1, S1, T1)
```

三者 primary 都是 P1（同一个基字母 a），secondary 只有 `á` 是 S1（有重音），tertiary 只有 `A` 是 T2（大写）。所以排序为 `a < A < á`（按此编码规则）。

**性能问题与解法**（第 24 页）：

```
Since doing this multi-step comparison is expensive, the DBMS will
precompute sort keys.
```

**sort key** 是把多级权重**拼接成一串字节**，之后比较两个字符串就退化成一次 `memcmp`。这把「每次比较都要多级解码」变成「一次预计算 + 快速字节比较」——典型的**用空间换时间**，与第 8 讲的「键归一化」同源。

### 5.10 三种比较优化

**① Code Specialization（代码特化）**（第 25 页）：

```
Instead of providing a comparison function as a pointer to sorting
algorithm, create a hardcoded version of sort that is specific to a key type.
```

**为什么重要**：通用排序算法通过**函数指针**调用比较器，每次比较都有一次间接跳转，且无法内联。若为 `int`、`float`、`VARCHAR` 各生成一个特化版本，比较可以内联成一条指令。C++ 里就是**模板特化**：

```cpp
template <typename T> void Sort(T* data, size_t n);  // 编译器为每种 T 生成一份
```

代价是**代码膨胀**（每种类型一份机器码），但换来的是数倍的比较吞吐。

**② Suffix Truncation（后缀截断）**：

```
First compare a binary prefix of long VARCHAR keys instead of slower
string comparison. Fallback to slower version if prefixes are equal.
```

**原理**：长字符串通常前几个字节就不同（如 `abcdefghijk` vs `abcdefghijz` 前 10 字节相同，第 11 字节才不同）。先比前 N 字节的二进制前缀，相等才回退到完整比较。

**与第 8 讲 B+ 树的后缀截断是同一技术**——那里是截断索引键以省空间，这里是截断比较以省时间。

**③ Key Normalization（键归一化）**：

```
Transform variable-length attribute(s) into a single encoded/padded string
that preserves sort order.
```

**原理**：把变长键编码成**定长、保序**的字节串。例如：

- 整数 → 大端序字节（保序）+ 零填充。
- 字符串 → 定长填充（短串补 `\0`）。
- 复合键 → 各字段归一化后拼接。

**收益**：比较变成定长 `memcmp`，且可以用 SIMD 一次比 16/32 字节。这是列式存储（第 6 讲）里「保序编码」的同类技术。

### 5.11 聚合的两种实现：排序 vs 哈希

**定义**（第 26 页）：

```
Collapse values for a single attribute from multiple tuples into a single
scalar value.
The DBMS needs a way to quickly find tuples with the same distinguishing
attributes for grouping.
Two implementation choices:
  → Sorting
  → Hashing
```

**关键问题**：如何让「同组的元组」彼此靠近，从而一次扫描就能算出结果？

**排序聚合**（第 27–28 页）：

```
1. 按 GROUP BY 键排序（内存排序或外部归并排序）
2. 顺序扫描有序数据，相邻同组元组累加运行值
3. 组变化时输出结果
```

**讲义例子 1**（`SELECT DISTINCT cid FROM enrolled WHERE grade IN ('B','C') ORDER BY cid`）：

```
Filter（先过滤 grade）→ 去掉无关列 → Sort（按 cid）→ 消除重复 → 输出
```

**关键顺序**：讲义 notes 强调——**先过滤再排序**。若先排序 100 万行再过滤掉 99 万行，就浪费了 99 万行的排序成本。**尽早减小数据量**是查询优化的第一原则。

**讲义例子 2**（`SELECT cid, AVG(s.gpa) FROM student s, enrolled e WHERE s.sid = e.sid GROUP BY cid`）：

```
Join → 得到 (cid, s.gpa) 对
Sort → 按 cid 排序：
       15-445 3.62 | 15-445 3.7 | 15-721 3.33 | 15-826 2.89
运行值 → (1, 3.62) | (2, 7.32) | (1, 3.33) | (1, 2.89)
         ↑ 每个分组维护 (COUNT, SUM)
Previous: null → 15-445 → 15-721 → 15-826
最终 → 15-445 3.66 | 15-721 3.33 | 15-826 2.89
```

**运行值的含义**：

| 聚合函数 | 运行值 |
|---|---|
| `AVG(col)` | `(COUNT, SUM)` |
| `MIN(col)` | `MIN` |
| `MAX(col)` | `MAX` |
| `SUM(col)` | `SUM` |
| `COUNT(col)` | `COUNT` |

**为什么 AVG 要存两个数**：平均值不能增量更新——你不能从「目前的平均值」推出「加入新值后的平均值」，必须保留 `COUNT` 与 `SUM`，最后相除。这是一个常见的设计陷阱。

**排序聚合的输出特性**：输出**按分组键有序**。若查询后面还有 `ORDER BY` 同一个键，就省掉了第二次排序。

### 5.12 哈希聚合

**动机**（第 29 页）：

```
What if we do not need the data to be ordered?
  → Forming groups in GROUP BY (no ordering)
  → Removing duplicates in DISTINCT (no ordering)

Hashing is a better alternative in this scenario.
  → Only need to remove duplicates, no need for ordering.
  → Can be computationally cheaper than sorting.
```

**核心洞察**：排序是 `O(n log n)`，哈希是 `O(n)` 期望。若不需要有序输出，哈希严格更便宜。

**内存版**（第 30 页）：

```
Populate an ephemeral hash table as the DBMS scans the table.
For each record, check whether there is already an entry in the hash table:
  → DISTINCT: Discard duplicate
  → GROUP BY: Perform aggregate computation
```

**外部哈希聚合**（第 31–35 页）——哈希表装不进内存时：

**Phase #1 – Partition**（第 32 页）：

```
Use a hash function h1 to split tuples into partitions on disk.
  → A partition is one or more pages that contain the set of keys with
    the same hash value.
  → Partitions are "spilled" to disk via output buffers.

Assume that we have B buffers.
We will use B-1 buffers for the partitions and 1 buffer for the input data.
```

```
        ┌─────────────┐
输入页 →│  1 个缓冲页  │
        └──────┬──────┘
               ↓ h1(tuple)
    ┌──────┬──────┬──────┬─────┬──────┐
    │ P1   │ P2   │ P3   │ ... │ P(B-1)│   ← B-1 个输出缓冲页
    └──┬───┴──┬───┴──┬───┴─────┴──┬───┘
       ↓满则落盘 ↓      ↓            ↓
    ┌──────────────────────────────────┐
    │            磁盘分区文件           │
    └──────────────────────────────────┘
```

**为什么是 B-1 个分区**：与外部排序同构——1 页放输入、`B-1` 页放输出。**同一个键必然落到同一个分区**（因为 `h1` 是确定性的），所以同组元组一定在同一个分区里，可以独立聚合。

**Phase #2 – ReHash**（第 34 页）：

```
For each partition on disk:
  → Read it into memory and build an in-memory hash table based on a
    second hash function h2.
  → Then go through each bucket of this hash table to bring together
    matching tuples.

This assumes that each partition fits in memory.
```

**为什么必须换一个哈希函数 `h2 ≠ h1`**：若仍用 `h1`，同一个分区内的所有元组会算出**相同**的哈希值（因为它们就是按 `h1` 分到这里的），哈希表会退化成一条链表——所有键冲突。**必须用独立的 `h2` 才能在分区内部再次分散**。

**递归分区**：若某个分区仍然装不进内存，就对它**递归地**再用另一个哈希函数分区，直到能装下。

**哈希聚合的运行值**（第 36–37 页）：

```
During the rehash phase, store pairs of the form (GroupKey → RunningVal)
When we want to insert a new tuple into the hash table as we compute
the aggregate:
  → If we find a matching GroupKey, just update the RunningVal appropriately
  → Else insert a new GroupKey → RunningVal
```

**讲义例子**：

```
h2 分桶后建表：
  key       value
  15-445    (2, 7.32)      ← COUNT=2, SUM=7.32
  15-826    (1, 3.33)
  15-721    (1, 2.89)

最终：15-445 3.66 | 15-826 3.33 | 15-721 2.89
```

与排序聚合得到**相同结果**，但输出**无序**（这里是恰好有序，因为哈希分布巧合；一般无序）。

### 5.13 排序 vs 哈希：什么时候用哪个

讲义 notes 的结论（第 4 页）：

```
The choice between sorting and hashing aggregate is subtle and depends on
optimizations done in each case, but in general hashing is often more
efficient unless the data is already sorted beforehand or the output is
required to be sorted (e.g. following ORDER BY).
```

**判断表**：

| 情形 | 选择 | 理由 |
|---|---|---|
| 数据已按分组键有序 | **排序** | 省掉排序阶段，直接顺序扫描 |
| 输出需要按分组键有序（后面有 `ORDER BY` 同键） | **排序** | 哈希之后还要再排一次 |
| 数据无序、输出无序 | **哈希** | `O(n)` vs `O(n log n)` |
| 分组数极少（如 3 个） | **哈希** | 哈希表极小，全部常驻内存 |
| 分组数极多（几乎每行一组） | **排序**（或混合哈希） | 哈希表巨大，分区开销高 |
| 有 `DISTINCT` 且无 `ORDER BY` | **哈希** | 只需去重，无需顺序 |
| 内存极度受限 | **排序** | 外部排序的 I/O 模式更可预测；哈希分区有数据倾斜风险 |

**哈希的隐藏风险：数据倾斜（skew）**。若某个键出现频率极高（如 `NULL` 或默认值），它的分区会远大于其他分区，导致「一个分区装不进内存 → 递归分区 → 仍然倾斜」。排序没有这个问题（每个 run 大小均匀）。

**现代 DBMS 的实践**：多数系统（PostgreSQL、SQL Server、DuckDB）**两种都实现**，由**查询优化器**按代价模型与统计信息选择；执行时还会**自适应切换**（例如哈希聚合发现分区过大，运行时改为排序聚合）。这是第 16–17 讲（查询优化）的内容。

### 5.14 全景：这些算法在查询计划中的位置

```
                 ┌──────────────┐
                 │  Projection  │  ← 输出列
                 └──────┬───────┘
                 ┌──────┴───────┐
                 │  Sort/Top-N  │  ← 本讲
                 └──────┬───────┘
                 ┌──────┴───────┐
                 │  Aggregate   │  ← 本讲（排序或哈希）
                 └──────┬───────┘
                 ┌──────┴───────┐
                 │    Filter    │  ← 尽早减小数据量
                 └──────┬───────┘
                 ┌──────┴───────┐
                 │  Join / Scan │  ← 第 13 讲
                 └──────────────┘
```

**注意算子的顺序**：filter 应尽量下推（第 5.11 节强调），sort 与 aggregate 应尽量靠上。这就是「谓词下推（predicate pushdown）」的一个实例。

## 6. 代码示例

### 6.1 讲义原文示例

**查询计划的构成**（`11-sorting.pdf` 第 4 页）：

```sql
SELECT R.id, S.cdate
FROM R JOIN S
ON R.id = S.id
WHERE S.value > 100
```

```
        π (R.id, S.cdate)
              │
        σ (value > 100)
              │
            ⨝ (R.id = S.id)
           /            \
          R              S

The operators are arranged in a tree.
Data flows from the leaves of the tree up towards the root.
The output of the root node is the result of the query.
```

**磁盘导向 DBMS 的两条原则**（第 5 页）：

```
Just like it cannot assume that a table fits entirely in memory, a
disk-oriented DBMS cannot assume that query results fit in memory.

We will use the buffer pool to implement algorithms that need to spill
to disk.

We are also going to prefer algorithms that maximize the amount of
sequential I/O.
```

**为什么需要排序**（第 6 页）：

```
Relational model/SQL is unsorted.
Queries may request that tuples are sorted in a specific way (ORDER BY).
But even if a query does not specify an order, we may still want to sort
to do other things:
  → Duplicate elimination (DISTINCT).
  → Bulk loading sorted tuples into a B+Tree index is faster.
  → Aggregations (GROUP BY), Window Functions
```

**排序算子的接口与两种物化**（第 7 页）：

```
For a given input run (i.e., list of key/value pairs), sort it based on a
comparison function and sorting parameters.

Key: The attribute(s) to compare to compute the sort order.
Value: Two choices
  → Tuple (early materialization).
  → Record ID (late materialization).
```

**外部归并排序的两阶段**（第 10 页）：

```
Divide-and-conquer algorithm that splits data into separate runs, sorts
them individually, and then combines them into longer sorted runs.

Phase #1 – Sorting
  → Sort chunks of data that fit in memory and then write back the
    sorted chunks to a file on disk.
  → Pick your favorite in-memory sorting algorithm.
Phase #2 – Merging
  → Combine sorted runs into larger chunks.
```

**2-way 的 pass 与 I/O 公式**（第 12–13 页）：

```
Pass #0
  → Read one page of the table into memory
  → Sort page into a "run" and write it back to disk
  → Repeat until the whole table has been sorted into runs
Pass #1,2,3,…
  → Recursively merge pairs of runs into runs twice as long
  → Need at least 3 buffer pages (2 for input, 1 for output)

In each pass, the DBMS reads and writes every page in the file.

Number of passes   = 1 + ⌈ log₂ N ⌉
Total I/O cost     = 2N ∙ (# of passes)
```

**通用 k 路归并的公式**（第 15 页）：

```
Pass #0
  → Use B buffer pages
  → Produce ⌈N / B⌉ sorted runs of size B
Pass #1,2,3,…
  → Merge B-1 runs (i.e., M-way merge)

Number of passes = 1 + ⌈ log_{B-1} ⌈N / B⌉ ⌉
Total I/O Cost   = 2N ∙ (# of passes)
```

**双缓冲**（第 17 页）：

```
Prefetch next run in the background and store in a second buffer while
processing the current run.
  → Overlap CPU and I/O operations
  → Reduces effective buffers available by half
```

**B+ 树排序的两种情形**（第 18–20 页）：

```
If the table that must be sorted already has a B+Tree index on the sort
attribute(s), then we can use that to accelerate sorting.
  → Some DBMSs support prefix key scans for sorting.
Retrieve tuples in desired sort order by simply traversing the leaf pages
of the tree.
Cases to consider:
  → Clustered B+Tree
  → Unclustered B+Tree

Case #1: CLUSTERED B+TREE
  Traverse to the left-most leaf page, then retrieve tuples from leaf pages.
  This is always better than external sorting because there is no
  computational cost, and all disk access is sequential.

Case #2: UNCLUSTERED B+TREE
  Chase each pointer to the page that contains the data.
  This is almost always a bad idea except for Top-N queries where N is
  small enough relative to total number of tuples in table.
  → In general, one I/O per data record.
```

**Top-N 堆排序**（第 21 页）：

```sql
SELECT * FROM enrolled
ORDER BY sid ASC
FETCH FIRST 4 ROWS WITH TIES
```

```
If a query contains an ORDER BY with a LIMIT, then the DBMS only needs to
scan the data once to find the top-N elements.
Ideal scenario for HeapSort if the top-N elements fit in memory.
  → Scan data once, maintain an in-memory sorted priority queue.
```

页面上的三处标注：`Skip!`（当前元素比堆顶差，跳过）、`Skip and done!`（后续元素全部更差，可提前终止）。

**Collation 的三行例子**（第 22 页）：

```
A collation defines the rules for comparing and sorting character strings.
  → Character ordering (ORDER BY)
  → Equality comparison (=, LIKE)
  → Case sensitivity
  → Accent sensitivity
  → Locale-specific rules

Binary collations are the fastest, but string comparison is not universal
  → ASCII Order ≠ Human Linguistic Order

ASCII Collation:  Apple | banana | zebra | Ängel    (Non-ASCII Sorted Last)
German Collation: Ängel | Apple | banana | zebra    (Handle "Ä" Similar to "Ae")
```

**UCA 多级比较**（第 23–24 页）：

```
Locale-aware comparison in ICU is based on the Unicode Collation
Algorithm (UCA). Rather than comparing raw Unicode code points, ICU
converts strings into collation elements with multiple comparison levels
and then compares those elements lexicographically.
  → Each character is mapped to one or more collation elements.

Level      | Meaning                    | Example
Primary    | Base letter differences    | a vs. b
Secondary  | Accent differences         | e vs. é
Tertiary   | Case differences           | a vs. A
Quaternary | Punctuation / tie-breaking | Optional

Comparison proceeds lexicographically by level:
  → Compare primary weights (base letters).
  → If equal, compare secondary weights (accents).
  → If equal, compare tertiary weights (case).
  → Continue if needed.

Since doing this multi-step comparison is expensive, the DBMS will
precompute sort keys.

a → (P1,S0,T1)    A → (P1,S0,T2)    á → (P1,S1,T1)
```

**三种比较优化**（第 25 页）：

```
Approach #1: Code Specialization
  → Instead of providing a comparison function as a pointer to sorting
    algorithm, create a hardcoded version of sort that is specific to a
    key type.
Approach #2: Suffix Truncation
  → First compare a binary prefix of long VARCHAR keys instead of slower
    string comparison. Fallback to slower version if prefixes are equal.
Approach #3: Key Normalization
  → Transform variable-length attribute(s) into a single encoded/padded
    string that preserves sort order.
```

**聚合的定义与两种实现**（第 26 页）：

```
Collapse values for a single attribute from multiple tuples into a single
scalar value.
The DBMS needs a way to quickly find tuples with the same distinguishing
attributes for grouping.
Two implementation choices:
  → Sorting
  → Hashing
```

**排序聚合的完整流程**（第 27–28 页）：

```sql
SELECT DISTINCT cid FROM enrolled WHERE grade IN ('B','C') ORDER BY cid
-- 执行顺序：Filter → Remove Columns → Sort → Eliminate Duplicates

SELECT cid, AVG(s.gpa)
FROM student AS s, enrolled AS e
WHERE s.sid = e.sid
GROUP BY cid
-- 执行顺序：Join → Sort (by cid) → 逐组累加 Running Totals
```

**运行值表**（第 28、37 页）：

```
AVG(col)   → (COUNT, SUM)
MIN(col)   → (MIN)
MAX(col)   → (MAX)
SUM(col)   → (SUM)
COUNT(col) → (COUNT)
```

**外部哈希聚合的两阶段**（第 31–35 页）：

```
Divide-and-conquer approach to computing an aggregation when data does
not fit in memory.

Phase #1 – Partition
  → Split tuples into buckets based on hash key
  → Write them out to disk when they get full
Phase #2 – ReHash
  → Build in-memory hash table for each partition and compute the aggregation

Use a hash function h1 to split tuples into partitions on disk.
  → A partition is one or more pages that contain the set of keys with
    the same hash value.
  → Partitions are "spilled" to disk via output buffers.
Assume that we have B buffers.
We will use B-1 buffers for the partitions and 1 buffer for the input data.

For each partition on disk:
  → Read it into memory and build an in-memory hash table based on a
    second hash function h2.
  → Then go through each bucket of this hash table to bring together
    matching tuples.
This assumes that each partition fits in memory.
```

**哈希聚合的运行值更新**（第 36 页）：

```
During the rehash phase, store pairs of the form (GroupKey → RunningVal)
When we want to insert a new tuple into the hash table as we compute the
aggregate:
  → If we find a matching GroupKey, just update the RunningVal appropriately
  → Else insert a new GroupKey → RunningVal
```

**结论与下讲预告**（第 38–39 页）：

```
External merge-sort allows the DBMS to handle data sets larger than memory.
Choice of sorting vs. hashing is subtle and depends on optimizations done
in each case.

NEXT CLASS
  Nested Loop Join
  Sort-Merge Join
  Hash Join
```

### 6.2 补充示例（非官方，仅用于说明概念）

**外部归并排序的 pass 数计算器**：

```python
import math

def external_sort_passes(n_pages, b_buffers, k_way=None):
    """返回 (pass 数, 总 I/O 次数)。k_way 为 None 时用 B-1 路。"""
    k = k_way if k_way else b_buffers - 1
    runs = math.ceil(n_pages / b_buffers)        # Pass #0 后的 run 数
    merge_passes = 0
    while runs > 1:
        runs = math.ceil(runs / k)
        merge_passes += 1
    passes = 1 + merge_passes
    return passes, 2 * n_pages * passes

print(external_sort_passes(108, 5))   # (4, 864)
print(external_sort_passes(108, 3))   # (8, 1728)  ← 2-way
print(external_sort_passes(1000, 5))  # B=5: 1+ceil(log4(200))=1+4=5
```

**k 路归并的核心循环（用最小堆）**：

```python
import heapq

def k_way_merge(runs):
    """runs: 若干已排序的迭代器；用堆做 k 路归并，O(n log k)。"""
    heap = []
    for i, it in enumerate(runs):
        v = next(it, None)
        if v is not None:
            heapq.heappush(heap, (v, i, it))
    while heap:
        v, i, it = heapq.heappop(heap)
        yield v
        nxt = next(it, None)
        if nxt is not None:
            heapq.heappush(heap, (nxt, i, it))
```

堆的大小恒为 k（= B-1），所以每次选择最小值的代价是 `O(log k)`——**k 越大，每次比较越贵，但 pass 数越少**。这就是「多路归并的 trade-off」：`pass 数 = O(log_k N)`，而每趟的 CPU 代价 `= O(N log k)`，乘积为 `O(N log N)`，**与 k 无关**。所以从 CPU 角度 k 无所谓，但从 **I/O 角度 k 越大越好**——这就是为什么要把 B 用满。

**Top-N 堆的骨架**：

```python
import heapq

def top_n(stream, n, key=lambda x: x):
    """只需一遍扫描，内存 O(n)。"""
    heap = []                       # 小顶堆，堆顶是当前第 n 名
    for item in stream:
        k = key(item)
        if len(heap) < n:
            heapq.heappush(heap, (k, item))
        elif k > heap[0][0]:        # 比当前第 n 名更优
            heapq.heapreplace(heap, (k, item))
        # else: Skip!
    return [item for k, item in sorted(heap, key=lambda t: t[0], reverse=True)]
```

**WITH TIES 的扩展**：扫描结束后，若还有与堆顶相等的元素，继续插入直到遇到严格更差的。

**哈希聚合（内存版）**：

```python
def hash_aggregate(rows, group_key, init, update):
    table = {}                       # GroupKey -> RunningVal
    for r in rows:
        g = group_key(r)
        if g in table:
            table[g] = update(table[g], r)      # 更新 RunningVal
        else:
            table[g] = update(init(), r)        # 插入新分组
    return table

# AVG 的运行值是 (COUNT, SUM)
avg = hash_aggregate(
    rows,
    group_key=lambda r: r.cid,
    init=lambda: (0, 0.0),
    update=lambda acc, r: (acc[0] + 1, acc[1] + r.gpa),
)
result = {cid: s / c for cid, (c, s) in avg.items()}
```

注意 `init` 与 `update` 的分离——这正是「运行值」抽象的价值：**聚合函数的语义只体现在这两个函数里**，执行框架完全通用。这也是为什么 `AVG` 必须用 `(COUNT, SUM)` 而不是单个浮点数。

**外部哈希聚合的分区**：

```python
def partition(rows, n_parts, h1):
    """Phase #1：按键的哈希分到 B-1 个分区。同一键必进同一分区。"""
    parts = [[] for _ in range(n_parts)]
    for r in rows:
        parts[h1(r) % n_parts].append(r)
    return parts

def external_hash_aggregate(rows, n_parts, h1, h2, group_key, init, update):
    for part in partition(rows, n_parts, h1):        # 逐个分区
        # Phase #2：用不同的 h2 在分区内建表
        table = {}
        for r in part:
            g = group_key(r)
            if g in table:
                table[g] = update(table[g], r)
            else:
                table[g] = update(init(), r)
        yield from table.items()
```

`h1` 与 `h2` 必须是**不同**的函数——否则同一分区内所有键会算出相同哈希值，哈希表退化成链表。

## 7. 容易混淆的概念

| 概念对 | 区别 | 记忆要点 |
|---|---|---|
| 早物化 vs 晚物化 | 前者 run 存整行（无需回表但 I/O 多）；后者存键+id（I/O 少但要随机回表） | 一个宽而慢，一个窄而快 |
| 2-way vs k-way 归并 | 前者只需 3 个缓冲页、`1+⌈log₂N⌉` 趟；后者用满 B 页、`1+⌈log_{B-1}⌈N/B⌉⌉` 趟 | 一个省内存，一个省 I/O |
| pass 数 vs I/O 次数 | pass 数是「读写全表的遍数」；I/O 次数 = `2N × pass` | 一个遍数，一个页次数 |
| 双缓冲 vs 多缓冲池 | 前者用两组缓冲重叠 CPU/IO（有效 B 减半）；后者按对象分区减少 latch 争用 | 一个换重叠，一个换并发 |
| 聚簇 vs 非聚簇索引排序 | 前者全顺序 I/O、零计算，总是更优；后者每记录一次随机 I/O，几乎总是坏主意 | 一个顺藤摸瓜，一个满屋乱跳 |
| Top-N vs 全排序 | 前者一遍扫描、内存 O(N)；后者需看完全部数据 | 一个只记前十，一个全排 |
| 二进制 collation vs 语言 collation | 前者最快但 `Ä` 排最后；后者符合人类习惯但需多级比较 | 一个快而不像人，一个像人而慢 |
| sort key vs 键归一化 | 前者预计算多级权重拼接；后者把变长键转定长保序串 | 都是「预编码换快速比较」 |
| 排序聚合 vs 哈希聚合 | 前者输出有序、`O(n log n)`；后者输出无序、`O(n)` 期望 | 一个顺带排序，一个只管分组 |
| `h1` vs `h2`（外部哈希） | `h1` 分磁盘分区；`h2` 在分区内建表，**必须不同** | 同一个函数会让表退化成链 |
| 排序聚合的 `AVG` vs 哈希聚合的 `AVG` | 都用 `(COUNT, SUM)` 运行值 | 平均值不可增量更新 |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Slides | `90-原始PDF/15-445/slides/11-sorting.pdf` | 39 | 2（HW#3 due Oct 4、DRC #1 Oct 5 带 CMU ID、期中 Oct 7 覆盖 L01–11、study guide 见 Piazza @85）、3（课程位置图：Access Methods → Operator Execution → Query Planning）、4（查询计划示例与算子树）、5（磁盘导向 DBMS 的两条原则）、6（为什么排序：四个理由）、7（排序接口与早/晚物化）、8（今日议程 + DB Flash Talk: SingleStore）、9（内存够用 vs 不够用）、10（外部归并排序两阶段）、11–14（2-way 示例与 `1+⌈log₂N⌉`、`2N×passes`、B=3 的局限）、15（通用 k 路公式）、16（`N=108, B=5` 四趟完整推导）、17（双缓冲图与「有效缓冲减半」）、18–20（B+ 树排序：聚簇总是更优、非聚簇仅 Top-N 可用）、21（Top-N 堆排序与 `WITH TIES`）、22（Collation 三行例子：ASCII vs 德语）、23–24（UCA 四级比较与 `(P1,S0,T1)` 编码、sort key 预计算）、25（三种比较优化）、26（聚合定义与两种实现）、27（`DISTINCT cid` 的 Filter→Sort→Dedup 流程）、28（`AVG(gpa)` 的排序聚合与 Running Totals 表）、29（不需要有序时哈希更优）、30（内存哈希聚合）、31–35（外部哈希聚合：Partition 的 `B-1` 缓冲、ReHash 的 `h2`）、36–37（`GroupKey → RunningVal` 与哈希版 AVG）、38（结论）、39（下讲：Nested Loop / Sort-Merge / Hash Join） |
| Notes | `90-原始PDF/15-445/notes/11-sorting.pdf` | 4 | 第 1 页（查询计划与算子树、缓冲池与顺序 I/O 偏好、排序的动机、早/晚物化、Top-N Heap Sort、External Merge Sort 两阶段）、第 2 页（2-way 的 pass 与 I/O 公式、k 路的 `1+⌈log_{B-1}⌈N/B⌉⌉`、双缓冲、字符串比较与 collation 多级、三种比较优化）、第 3 页（用 B+ 树排序：聚簇 vs 非聚簇、聚合的两种实现、排序聚合与「先过滤再排序」、哈希聚合与外部哈希两阶段）、第 4 页（ReHash 阶段的 `(GroupKey→RunningValue)`、插入/更新的两条分支、排序 vs 哈希的选择结论） |

原始 URL：

- Slides：`https://15445.courses.cs.cmu.edu/fall2026/slides/11-sorting.pdf`
- Notes：`https://15445.courses.cs.cmu.edu/fall2026/notes/11-sorting.pdf`

> 待核实：本讲 slides 第 1 页的讲师署名为 **Yuchen Liang**（其余各讲为 Jignesh Patel），推测为客座讲授，建议人工核对课表。
> 待核实：slides 第 2 页写 "Project #2 is due Sunday **March 15th** @ 11:59pm"，与秋季学期时间线不符（其余 admin 信息均为 9–10 月），疑为沿用春季学期幻灯片未更新，实际截止日期请以课程官网 Project #2 页面为准。
> 待核实：notes 第 2 页称 2-way 归并「uses three buffer pages」，而 slides 第 12 页写「Need at least 3 buffer pages (2 for input, 1 for output)」——两处一致；但 notes 对 `N` 的定义（「total number of data pages」）与 `⌈log₂N⌉` 中的 N 是否含 Pass #0 后的取整差异，建议以 slides 第 16 页的具体例题为准。
> 待核实：讲义第 28 页的 `AVG` 示例中运行值序列 `(1, 3.62) (2, 7.32) (1, 3.33) (1, 2.89)` 与排序后的 `(cid, gpa)` 对一一对应，但最终 `15-445` 的结果 3.66 需 `7.32 / 2 = 3.66` 验证通过；`15-826` 的 3.33 与输入 2.89 不一致，疑为动画中间状态，需人工核对 PDF 原图。

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内，本讲内容对应 2025 年第 11 讲）

- 标题：Sorting & Aggregation Algorithms — External Merge Sort, Top-N Heap Sort, Hash Aggregation（2025 年第 11 讲）
- URL：`https://www.youtube.com/watch?v=LzyKTpeIgts&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 年份：2025
- 时间戳：未核实，故不标注。

## 10. 本节复习

- 能说出「关系模型无序」这一点如何推出「所有有序需求都必须由算子显式产生」。
- 能列出排序的四个隐含用途（DISTINCT、B+ 树批量加载、GROUP BY、窗口函数）。
- 能对比早物化与晚物化的 I/O 与回表代价，并说明为什么晚物化通常更优。
- 能默写 2-way 与 k 路归并的 pass 公式与 I/O 公式，并解释 `B-1` 的来源。
- 能手算 `N=108, B=5` 的四趟过程与总 I/O = 864。
- 能说明双缓冲如何重叠 CPU 与 I/O，以及为什么有效缓冲减半。
- 能判断聚簇/非聚簇 B+ 树排序何时可用，并解释非聚簇「每记录一次 I/O」的由来。
- 能说明 Top-N 为什么只需一遍扫描，以及 `WITH TIES` 如何扩展堆。
- 能举出 `Ä` 在 ASCII 与德语 collation 下的不同位置，说明字符串比较为何不通用。
- 能描述 UCA 的 primary/secondary/tertiary 三级比较与 sort key 预计算。
- 能说出三种比较优化（代码特化、后缀截断、键归一化）各自消除的开销。
- 能默写聚合的五种运行值，并解释 `AVG` 为什么必须用 `(COUNT, SUM)`。
- 能描述外部哈希聚合的两阶段，说明 `B-1` 个分区的来源与 `h1 ≠ h2` 的必要性。
- 能给出排序聚合与哈希聚合的选择准则（至少四条）。

## 11. 自我检查

**Q1.** 为什么 k 路归并的 pass 公式是 `1 + ⌈log_{B-1}⌈N/B⌉⌉` 而不是 `1 + ⌈log_B⌈N/B⌉⌉`？请用 `N=108, B=5` 完整推导，并与 B=3 的 2-way 对比 I/O 差异。

<details><summary>参考答案</summary>

**为什么是 B-1 而不是 B**：

归并阶段需要**同时**把每个输入 run 的当前页放在内存里，**还要有一页放输出**。所以：

```
输入缓冲页数 = B - 1   （每个 run 占 1 页）
输出缓冲页数 = 1
合计 = B
```

因此一次最多能归并 `B-1` 个 run，即 **B-1 路归并**。同理，Pass #0 的排序阶段可以一次读入 **B 页**（全部用于输入，排序在内存完成后再写回，不需要单独的输出缓冲），所以产出 `⌈N/B⌉` 个长度为 B 的 run。

**`N=108, B=5` 的完整推导**：

```
Pass #0（排序）:
  一次读 5 页，排序后写回
  run 数 = ⌈108 / 5⌉ = 22
  最后一个 run 只有 108 - 21×5 = 3 页

Pass #1（4 路归并）:
  run 数 = ⌈22 / 4⌉ = 6
  前 5 个 run 各合并 4 个 5 页 run = 20 页
  第 6 个 run 合并剩下的 2 个 run（5 页 + 3 页）= 8 页

Pass #2（4 路归并）:
  run 数 = ⌈6 / 4⌉ = 2
  第一个 run = 4 × 20 = 80 页
  第二个 run = 20 + 8 = 28 页（实际为 2 个 run 合并）

Pass #3（4 路归并）:
  run 数 = ⌈2 / 4⌉ = 1
  合并 80 + 28 = 108 页 → 完成

总 pass 数 = 4
公式验证: 1 + ⌈log₄ 22⌉ = 1 + ⌈2.229...⌉ = 1 + 3 = 4 ✓
```

**总 I/O**：每一趟都要把每一页读一次、写一次，所以

```
总 I/O = 2N × pass 数 = 2 × 108 × 4 = 864 次页 I/O
```

**与 B=3 的 2-way 对比**：

```
B=3 → 只能用 2 路归并（2 输入 + 1 输出）
Pass #0: ⌈108/3⌉ = 36 个 run（若按 B 页排序）
  注：讲义简化版是「1 页 1 个 run」，则 N=108 个 run
  按简化版：pass 数 = 1 + ⌈log₂ 108⌉ = 1 + ⌈6.755⌉ = 1 + 7 = 8
总 I/O = 2 × 108 × 8 = 1728
```

**结论**：多用 2 个缓冲页（B 从 3 到 5），pass 数从 8 降到 4，**I/O 减少 50%**。

**这个结论的实践含义**：

1. **B 是外部排序性能的唯一决定因素**（在 N 固定时）。所以查询执行器必须从缓冲池**争取足够多的页**——这正是第 4 讲「Multiple Buffer Pools」为排序/连接单独划池的原因。
2. **k 的收益是递减的**：`log_{B-1}` 意味着 B 从 5 增到 9（k 从 4 到 8）只省一趟，而 B 从 3 增到 5 省四趟。所以小 B 时增加缓冲的边际收益极高。
3. **CPU 代价与 k 无关**：k 路归并每次选最小值是 `O(log k)`，总 CPU 是 `O(N log N)`，与 k 无关。所以**从 CPU 角度 k 越大越好（免费），从内存角度 k 越大越贵**——权衡点在于「缓冲池能分多少页给排序」。

</details>

**Q2.** 什么时候可以用 B+ 树代替外部排序？为什么聚簇索引「总是更优」而非聚簇索引「几乎总是坏主意」？Top-N 为什么是例外？

<details><summary>参考答案</summary>

**前提条件**：表上已有排序属性的 B+ 树索引，且 DBMS 支持**前缀键扫描（prefix key scan）**——即能沿叶子链表按索引顺序取出元组。

**Case #1：聚簇索引 —— 总是更优**

```
Traverse to the left-most leaf page, then retrieve tuples from leaf pages.
```

三个理由：

1. **零计算成本**：树已经维护好了顺序，不需要比较、不需要归并、不需要临时文件。外部排序的 CPU 与 I/O 开销全部省掉。
2. **全顺序 I/O**：聚簇意味着**元组的物理存储顺序与索引顺序一致**。沿叶子链表走，读到的页就是磁盘上相邻的页 → 顺序读，每次 I/O 取一整页有用数据。
3. **无额外空间**：不需要 `2N` 的临时空间（外部排序每趟都要读写全表）。

所以聚簇索引扫描的代价约为 `N` 次顺序 I/O（N = 表页数），而外部排序至少 `2N × 2 = 4N`。**严格更优，没有例外**。

**Case #2：非聚簇索引 —— 几乎总是坏主意**

```
Chase each pointer to the page that contains the data.
  → In general, one I/O per data record.
```

**为什么是「每条记录一次 I/O」**：

非聚簇索引的叶子只存 record id（页号 + 槽号）。按索引顺序取元组时：

```
索引叶子: (key=1, rid=(页 500, 槽 3))
          (key=2, rid=(页 12,  槽 7))
          (key=3, rid=(页 890, 槽 1))
          ...
```

每个 rid 指向的页**在磁盘上毫无规律**。而缓冲池装不下整张表，所以每次跳转几乎都是**冷页** → 一次随机 I/O。更糟的是：**取完这一条记录，那一页剩下的 99 条记录可能永远不会被用到**（因为它们的键不相邻），于是这一页的读入完全是浪费。

**定量对比**（100 万条记录、每页 100 条 → 1 万页）：

```
非聚簇索引全表按序扫描:  1,000,000 次随机 I/O
外部排序:                2 × 10,000 × 3 ≈ 60,000 次顺序 I/O
比值:                    约 17 倍
```

而且随机 I/O 的单次延迟远高于顺序 I/O（HDD 上差 100 倍，SSD 上差 10 倍），**实际时间差距可能是几百倍**。

**Top-N 为什么是例外**：

```sql
SELECT * FROM t ORDER BY x LIMIT 10;
```

只需要**前 10 条**。非聚簇索引顺着叶子走 10 步，取 10 条记录 → **只有 10 次随机 I/O**。

对比两条路：

```
非聚簇索引 + Top-N:  10 次随机 I/O          ← 极快
外部排序全表:        2 × 10,000 × 3 = 60,000 次 I/O
```

**差距是三个数量级**。这就是讲义说「except for Top-N queries where N is small enough relative to total number of tuples」的确切含义。

**「small enough」的定量判据**：

```
非聚簇索引代价 ≈ N_top × (随机 I/O 延迟)
外部排序代价   ≈ 2N × passes × (顺序 I/O 延迟)

若 N_top × 100 × seq_latency < 2N × passes × seq_latency
（HDD 上随机约为顺序的 100 倍）
→ N_top < 2N × passes / 100
```

对 N = 10,000 页、passes = 3：`N_top < 600`。所以 HDD 上 Top-N 的 N 要小于几百条才划算。SSD 上随机/顺序比约 10 倍，阈值放宽到几千条。

**实践中的第三种选择**：若 N 较大（如 `LIMIT 10000`），优化器可能选择**先全表扫描 + Top-N 堆**（一遍顺序扫描，内存 O(N)），而不是走非聚簇索引。这就是第 5.7 节的算法——**它不依赖任何索引**。

**小结**：

| 情形 | 最佳方案 |
|---|---|
| 有聚簇索引 | 直接遍历索引叶子（总是最优） |
| 无索引、需完整排序 | 外部归并排序 |
| 无索引、Top-N 且 N 小 | Top-N 堆（一遍顺序扫描） |
| 非聚簇索引、Top-N 且 N 极小 | 走索引（少数随机 I/O） |
| 非聚簇索引、需完整排序 | **绝不要走索引**，改用外部排序 |

</details>

**Q3.** 外部哈希聚合为什么需要 `B-1` 个分区？为什么 ReHash 阶段必须用不同的哈希函数 `h2`？如果一个键出现频率极高（数据倾斜），会发生什么？

<details><summary>参考答案</summary>

**为什么是 B-1 个分区**：

与外部排序同构的缓冲分配：

```
Phase #1（Partition）:
  1 个缓冲页  ← 输入数据（从表里读元组）
  B-1 个缓冲页 ← 输出分区，每个分区一个缓冲页
  ─────────
  合计 B 页
```

每个元组按 `h1(分组键)` 决定进哪个分区，写入对应的输出缓冲页；该页满了就**落盘**（spill）并换一个空页。所以最多能同时维护 `B-1` 个分区。

**关键性质**：`h1` 是**确定性**的，同一个键必然算出同一个分区号 → **同组元组必然落在同一分区**。因此每个分区可以**独立聚合**，不需要跨分区通信。

**Phase #2（ReHash）**：逐个分区读入内存（此时 `B` 页全部可用于该分区），建内存哈希表。**前提是该分区能装进内存**——若装不下，就对该分区**递归地**用另一个哈希函数再分区。

**为什么必须 `h2 ≠ h1`**：

这是最容易搞错的一点。假设仍用 `h1`：

```
分区 P3 里的所有元组，都是因为 h1(key) % (B-1) == 3 才被分到这里的。
现在用 h1 建内存哈希表：
  bucket = h1(key) % table_size
  → 对 P3 里所有元组，h1(key) % (B-1) 都相同
  → 若 table_size 恰为 (B-1) 的倍数，所有键算出同一个 bucket
  → 哈希表退化成一条长度为 |P3| 的链表
  → 查找/插入变成 O(|P3|)，聚合退化为 O(n²)
```

即使 `table_size` 不是 `(B-1)` 的倍数，`h1` 的输出在「模 (B-1) 固定」这个约束下也**高度相关**，分布远不如独立哈希函数均匀。

**结论**：必须用一个**统计独立**的 `h2`（不同算法，或同一算法不同种子），才能在分区内部重新打散。

**数据倾斜（skew）的后果**：

假设 `cid` 列有 90% 的值是 `NULL`（或某个默认值 `'unknown'`）：

```
h1(NULL) → 固定落在某个分区，比如 P2
→ P2 装进了 90% 的数据，其他分区只有 10%
→ P2 装不进内存 → 递归分区
→ 递归时 NULL 仍然全落在同一个子分区 → 仍然倾斜
→ 递归 N 层也解决不了 → 无限递归 / 退化为排序
```

**三重后果**：

1. **内存耗尽**：P2 无法装进内存，递归分区也无法解决（因为倾斜是**键值层面**的，不是哈希函数层面的）。
2. **并行度崩塌**：其他分区早就处理完了，P2 还在慢慢做 → 整个算子的时间由最慢的分区决定。
3. **退化为嵌套循环**：若最终放弃哈希、改走「每个不同键扫一遍分区」，复杂度变成 `O(n × distinct_keys)`。

**工业界的应对**：

| 手段 | 做法 |
|---|---|
| **倾斜检测** | 运行时统计各分区大小，超过阈值（如平均值的 2 倍）就标记为倾斜 |
| **分裂热点键** | 把 `NULL` 这类热点键**单独**分到一个分区，其余正常哈希 |
| **自适应切换** | 发现倾斜就**改用排序聚合**（排序的 run 大小均匀，天然抗倾斜） |
| **两阶段聚合** | 先在每个分区内做**部分聚合**（`(COUNT, SUM)` 而非原始元组），大幅减小数据量后再合并 |
| **共享聚合** | 对 `COUNT`、`SUM` 这类可结合的聚合，分区内先算局部结果，最后合并局部结果 |

**为什么排序天然抗倾斜**：外部排序的 run 大小只取决于「每趟读入多少页」，与键的分布无关。所有 run 都是 B 页，归并的每一路都是均匀的。所以**倾斜严重时排序更稳健**——这也是讲义说「选择是微妙的（subtle）」的原因之一。

**实践建议**：

```
分组数少 + 分布均匀      → 哈希聚合（快）
分组数少 + 严重倾斜      → 排序聚合，或哈希 + 热点键单独处理
分组数极多（近唯一）      → 排序聚合（哈希表巨大，分区开销高）
输出需要有序             → 排序聚合（顺带省掉后续 ORDER BY）
```

</details>

**Q4.** `AVG` 的运行值为什么必须是 `(COUNT, SUM)` 而不能是单个「当前平均值」？请举一个具体的数字例子说明，并推广到「哪些聚合函数可以增量更新、哪些不行」。

<details><summary>参考答案</summary>

**为什么不能只存当前平均值**：

平均值**不是可结合（associative）的**运算——你不能从「前 n 个元素的平均值」和「第 n+1 个元素」直接算出「前 n+1 个元素的平均值」，除非你还知道 n。

**数学推导**：

```
avg_n     = S_n / n                    （S_n 是前 n 个元素的和）
avg_{n+1} = (S_n + x) / (n+1)
          = (avg_n × n + x) / (n+1)
```

要算 `avg_{n+1}`，必须知道 `n`。所以运行值里**必须**包含计数。

**具体数字例子**：

```
数据: 3.62, 3.70, 2.89

若只存当前平均值:
  处理 3.62 → avg = 3.62
  处理 3.70 → 若天真地算 (3.62 + 3.70)/2 = 3.66  ← 碰巧对（n=2）
  处理 2.89 → 若算 (3.66 + 2.89)/2 = 3.275     ← 错！
              正确答案是 (3.62 + 3.70 + 2.89)/3 = 3.4033...

  为什么错：第二次平均时权重错了。
  3.66 代表 2 个元素的平均，2.89 代表 1 个元素，
  应该算 (3.66×2 + 2.89×1)/3 = 3.4033，而不是 (3.66+2.89)/2。

若存 (COUNT, SUM):
  (1, 3.62) → (2, 7.32) → (3, 10.21)
  最终 avg = 10.21 / 3 = 3.4033  ✓
```

**根本原因**：`AVG` 是「两个可结合量的商」。`COUNT` 与 `SUM` 都是可结合的（可以任意分组、分别计算再合并），但它们的**商不是**。所以运行值必须保留那两个可结合量。

**可增量更新 vs 不可**：

| 聚合函数 | 运行值 | 为什么可/不可 |
|---|---|---|
| `SUM` | `SUM` | 可结合：`S(A∪B) = S(A) + S(B)` |
| `COUNT` | `COUNT` | 可结合：`C(A∪B) = C(A) + C(B)` |
| `MIN` | `MIN` | 可结合：`min(A∪B) = min(min(A), min(B))` |
| `MAX` | `MAX` | 可结合：`max(A∪B) = max(max(A), max(B))` |
| `AVG` | **`(COUNT, SUM)`** | 商不可结合，但分子分母各自可结合 |
| `STDDEV` / `VAR` | `(COUNT, SUM, SUM_OF_SQUARES)` | 方差的公式 `E[x²] - E[x]²` 需要二阶矩 |
| `MEDIAN` | **不可增量**（需全部值或近似结构） | 中位数依赖完整排序，不满足结合律 |
| `COUNT(DISTINCT)` | **不可增量**（需集合或 HyperLogLog） | 去重计数依赖完整集合 |
| `PERCENTILE` | 不可精确增量（可用 t-digest 近似） | 同 MEDIAN |

**推广出的三条规律**：

1. **可结合 + 可交换的聚合可以任意并行/分区**：`SUM`、`COUNT`、`MIN`、`MAX`。这是为什么 MapReduce / 分布式聚合能高效工作的基础。
2. **「两个可结合量的商」需要保留两个量**：`AVG = SUM/COUNT`、`STDDEV` 需要 `COUNT/SUM/SUMSQ`。这类聚合在并行时先各自算分子分母，最后合并再相除。
3. **依赖全局顺序或完整集合的聚合不可增量**：`MEDIAN`、`PERCENTILE`、`COUNT(DISTINCT)`。它们要么需要保留全部值（内存爆炸），要么用**近似算法**（HyperLogLog 估算 distinct、t-digest 估算分位数）。

**工程含义**：

- **运行值的类型必须由聚合函数决定**，执行框架不能假设「一个浮点数就够了」。这就是为什么所有 DBMS 的聚合算子都有 `init / update / combine / finalize` 四个钩子：

```cpp
struct AvgState { int64_t count = 0; double sum = 0; };

void init(AvgState& s)                        { s = {}; }
void update(AvgState& s, double v)            { s.count++; s.sum += v; }
void combine(AvgState& a, const AvgState& b)  { a.count += b.count; a.sum += b.sum; }
double finalize(const AvgState& s)            { return s.count ? s.sum / s.count : NAN; }
```

`combine` 的存在正是为了**并行聚合**（两个线程各算一半，最后合并）——它要求运行值本身可结合。`AVG` 的 `AvgState` 满足这一点，而「单个浮点数的平均值」不满足。

- **`COUNT(DISTINCT)` 在分布式下是著名的难题**：精确算法要传输全部去重值，网络开销爆炸；所以生产系统用 HyperLogLog（约 12 KB 估算任意基数，误差 ~2%）。

</details>

**Q5.** 假设你要实现一个 `ORDER BY x LIMIT 100` 的算子，表有 1 亿行、`x` 上有非聚簇索引、`x` 的取值高度重复（只有 1000 个不同值）。你会选哪种算法？如果 `x` 有 1 亿个不同值呢？请分别说明理由。

<details><summary>参考答案</summary>

**关键判断维度**：① 需要看多少数据才能确定答案；② I/O 是顺序还是随机；③ 内存能否容纳状态。

**情形 A：`x` 只有 1000 个不同值（高度重复）**

**不能直接用非聚簇索引**，原因很微妙：

```
ORDER BY x LIMIT 100
```

索引按 `x` 有序，所以顺着叶子走就能拿到最小的 `x`。但由于**高度重复**，最小的那个 `x` 值可能对应**几万条记录**。取前 100 条只需读 100 个 rid——**看似很快**。

**但问题在于**：`LIMIT 100` 只要 100 行，而同一个 `x` 值有 10 万行。走索引取 100 条 → 100 次随机 I/O，这确实很快。

所以这个情形下**走非聚簇索引是可行的**——只要 `LIMIT` 的 N 相对总行数极小。

**但若查询是 `ORDER BY x, y LIMIT 100`**（复合排序），或需要 `DISTINCT x`，情况就变了：

- 复合排序：索引只保证 `x` 有序，`x` 相同的组内 `y` 无序 → 索引不够用，必须取出**整个最小 `x` 组**（10 万行）再排序 → 10 万次随机 I/O，不可接受。
- `DISTINCT x`：只需 1000 个不同值，走索引要扫全部 1 亿条。

**推荐方案**：

| 查询 | 方案 | 理由 |
|---|---|---|
| `ORDER BY x LIMIT 100`（单键） | **非聚簇索引**，取前 100 条 | 100 次随机 I/O，极快 |
| `ORDER BY x, y LIMIT 100` | **全表顺序扫描 + Top-N 堆** | 堆大小 100，内存极小；一遍顺序 I/O ≈ 表页数 |
| `SELECT DISTINCT x` | **索引跳跃扫描（skip scan）** 或全表扫描 + 哈希去重 | 只有 1000 个值，skip scan 每段跳一次 |

**全表扫描 + Top-N 的代价**：1 亿行、每页 100 行 → 100 万页 → 100 万次顺序 I/O。虽然比 100 次随机 I/O 多，但**顺序 I/O 便宜**，且**结果一定正确**。对 HDD（顺序 ~100 MB/s）约 80 GB / 100 MB/s ≈ 800 秒；对 SSD 快得多。而走索引虽然只要 100 次 I/O，但复合排序下会退化成 10 万次随机 I/O（HDD 上 10 万 × 10 ms = 1000 秒）——**反而更慢**。

**情形 B：`x` 有 1 亿个不同值（近乎唯一）**

**这时非聚簇索引 + Top-N 是最优解**：

```
顺着索引叶子走，取前 100 条 rid → 100 次随机 I/O → 回表取 100 行 → 完成
```

因为 `x` 近乎唯一，最小的 100 个 `x` 就对应 100 条不同的记录，**不需要取出任何「同值组」**。100 次随机 I/O 是**下界**（你必须至少读这 100 行）。

对比全表扫描：100 万页顺序 I/O，慢几个数量级。

**推荐方案**：**非聚簇索引 + Top-N 堆**（或者更简单：直接走索引取前 100 条，连堆都不需要——因为索引顺序已经是答案顺序）。

**注意**：只有当 `LIMIT N` 相对总行数极小时才成立。若 `LIMIT 1000000`，走索引就是 100 万次随机 I/O，远不如全表扫描 + Top-N 堆。

**统一的判断准则**：

```
走非聚簇索引的代价  ≈ N_top × random_io_latency
全表扫描 + Top-N    ≈ N_pages × seq_io_latency

走索引更优  ⟺  N_top × random_io_latency < N_pages × seq_io_latency
            ⟺  N_top < N_pages × (seq/random ratio)
```

对 HDD（ratio ≈ 100）、`N_pages = 1,000,000`：`N_top < 10^8` —— 看起来索引总是更优？**但这个估算忽略了两个关键因素**：

1. **缓冲池命中率**：全表扫描的页可能部分已在缓冲池；索引的随机访问几乎必然缺失。
2. **同值组的放大效应**：若 `x` 高度重复且查询需要组内再排序，`N_top` 实际会膨胀成「整个最小组的行数」。

所以**真正的判断必须结合「值分布」与「查询是否只按单键排序」**：

| `x` 的分布 | 单键 `ORDER BY x LIMIT N`（N 小） | 复合 `ORDER BY x, y LIMIT N` |
|---|---|---|
| 近乎唯一 | **走索引**（N 次随机 I/O） | 走索引（同左，因组内只有 1 行） |
| 高度重复（1000 值） | 走索引（N 次随机 I/O，但可能跨多个组） | **全表扫描 + Top-N 堆**（组内无序，索引失效） |
| 完全均匀（如 `status` 只有 3 值） | 全表扫描 + Top-N 堆 | 全表扫描 + Top-N 堆 |

**最后一个实践要点**：现代优化器不会硬编码这些规则，而是用**统计信息**（不同值个数 ndv、直方图、索引聚簇因子）估算两条路径的代价，选便宜的。若统计信息过期（`x` 的分布变了但没 `ANALYZE`），优化器就会选错——这是生产环境最常见的性能事故之一。**这就是为什么 `EXPLAIN` 之后常要 `ANALYZE` 再 `EXPLAIN` 一次。**

</details>

## 12. 进一步学习

- 上一讲：[[15-445-10-Index-Concurrency-Control]] —— latch、crabbing、叶子扫描的死锁与 no-wait 协议。
- 下一讲：[[15-445-13-Joins-Algorithms]] —— 三种连接算法（Nested Loop / Sort-Merge / Hash）与代价对比。
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]、[[40-CMU-15-445/04-学习进度|CMU 15-445 - 学习进度]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：Knuth, *The Art of Computer Programming, Vol. 3: Sorting and Searching* —— 外部排序的经典分析。
- 延伸阅读：Graefe, *Query Evaluation Techniques for Large Databases*, ACM Computing Surveys 1993 —— 查询执行算法的权威综述，外部排序与哈希聚合的权衡讲得最透。
- 延伸阅读：Ramakrishnan & Gehrke, *Database Management Systems* 第 13–14 章 —— 外部排序与哈希连接的教材级推导。
- 延伸阅读：Balkesen et al., *Multi-Core, Main-Memory Joins: Sort vs. Hash Revisited* (VLDB 2013) —— 内存时代「排序 vs 哈希」的实测结论（结论是哈希通常更快，但差距在缩小）。
- 延伸阅读：Unicode Consortium, *UTS #10: Unicode Collation Algorithm* —— UCA 的规范文档，本讲 collation 部分的原始来源。
- 延伸阅读：ICU 项目文档（`unicode-org/icu`）—— sort key 预计算的具体实现。
- 动手建议：用 Python 实现一个外部归并排序模拟器，输入 `N` 页与 `B` 缓冲页，输出每一趟的 run 长度序列与总 I/O 次数。先验证讲义 `N=108, B=5 → 4 趟 / 864 I/O`，再画出「I/O 次数随 B 变化」的曲线，观察 `log_{B-1}` 的递减特性在 B 较小时最陡。
