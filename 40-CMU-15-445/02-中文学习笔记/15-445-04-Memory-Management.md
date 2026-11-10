---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: L04
topic: Memory Management (Buffer Pool)
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 数据库
  - 缓冲池
  - 替换策略
  - ARC
  - 内存管理
---

# 15-445 L04：内存管理（Memory Management / Buffer Pool）

> 上一讲解决了「问题 #1：数据库在磁盘上怎么表示」。这一讲解决「问题 #2：DBMS 如何管理内存、如何在磁盘与内存之间来回搬数据」。答案是一个所有数据库都绕不开的组件——**缓冲池管理器（Buffer Pool Manager）**。本讲也是 **Project #1** 的全部内容：ARC 替换策略、磁盘调度器、缓冲池管理器。

## 1. 本节学习目标

学完本讲，你应该能够：

1. 说出**空间控制（spatial control）**与**时间控制（temporal control）**两个优化目标，并解释它们各自要最小化什么。
2. 画出缓冲池的组织结构：frame 数组、页表（page table）、每页元数据（dirty flag、pin counter、access tracking）。
3. 严格区分 **page table** 与 **page directory**、**lock** 与 **latch**——这两组概念是本课程最常考的混淆点。
4. 列举「为什么不用 OS 的 mmap」的四个问题，并说明 `madvise` / `mlock` / `msync` 为什么不足以解决。
5. 解释 LRU、CLOCK、LFU、LRU-K、ARC 五种替换策略的机制、开销与失效场景（尤其 **sequential flooding**）。
6. 说明钉住页（pinned page）为什么不能被驱逐，以及缓冲区全被钉住时的后果。
7. 描述脏页驱逐的快路径/慢路径、后台写（background writing）与日志顺序的约束。
8. 列举四种缓冲池优化：多缓冲池、预取、扫描共享、缓冲池旁路，并说出各自适用场景。

## 2. 前置知识

- **上一讲的存储层次与页概念**：见 [[15-445-03-Database-Storage-I]]。必须清楚「数据库页 ≠ 硬件页 ≠ OS 页」，以及页目录的作用。
- **缓存（cache）的基本思想**：命中率、驱逐、写回 vs 写穿。学过 15-213 的 cache 章节即可。
- **虚拟内存与缺页（page fault）**：理解 mmap 把文件映射进地址空间后，访问未驻留页会触发缺页中断。
- **哈希表与链表**：页表是哈希表，LRU 链是双向链表，ARC 是四个链表 + 一个自适应参数。
- **C++17 与并发基础**：Project #1 要求用 `std::mutex`、`std::shared_mutex`、`std::promise`、`std::future` 实现线程安全的缓冲池；代码需符合 **Google C++ Style**，提交前跑 `make format` 与 `make check-clang-tidy-p1`。

## 3. 核心概念

### 3.1 Disk-Oriented DBMS（面向磁盘的数据库系统）

主存储位于持久存储（HDD/SSD）的 DBMS。与之相对的是内存数据库（in-memory DBMS）。冯·诺依曼架构要求数据先在内存中才能被运算，因此面向磁盘的 DBMS 必须高效地在磁盘与内存之间搬运数据——这就是缓冲池管理器的职责。

### 3.2 Spatial Control（空间控制）

决定**页写在磁盘的什么位置**。目标是让经常一起被使用的页在物理上尽量靠近，从而有利于预取（prefetching）与其他优化。上一讲的 extent（区段）就是空间控制的手段之一。

### 3.3 Temporal Control（时间控制）

决定**何时把页读进内存、何时把修改过的页写回磁盘**。目标是**最小化因读磁盘而产生的停顿（stall）**。本讲绝大部分内容（替换策略、预取、后台写）都属于时间控制。

### 3.4 Buffer Pool（缓冲池）

DBMS 在内存中分配的一大块区域，组织成**固定大小 frame 的数组**。DBMS 请求某页时，先查该页是否已在某个 frame 中；若不在，则从磁盘读出并复制进一个空闲 frame。它是**写回缓存（write-back cache）**：脏页被缓冲，不立即写回磁盘，这与写穿缓存（write-through cache）相反。

### 3.5 Frame（帧）

缓冲池数组中的一个槽位，大小等于一个数据库页。一个 frame 可以先后装不同的页；「物理上第 3 个 frame」与「逻辑上第 3 页」没有固定关系，这正需要页表这层间接。

### 3.6 Page Table（页表）

**内存中的哈希表**，记录当前哪些页在内存中，把 page id 映射到 frame 位置。通常大小固定，用闩锁（latch）保护以支持多线程安全访问。它是纯内存结构，**不需要持久化**。

### 3.7 Page Directory（页目录）

**磁盘上的映射**，记录 page id → 该页在数据库文件中的物理位置。任何改动都必须落盘，否则重启后找不到页。通常也常驻内存以减少访问延迟，但语义上它是持久结构。

### 3.8 Dirty Flag（脏位）

线程修改某页时置位，告诉存储管理器「驱逐前必须写回磁盘」。未置位的页可以直接丢弃（快路径）。

### 3.9 Pin / Reference Counter（钉住计数 / 引用计数）

记录当前有多少线程正在访问该页（读或写）。线程访问前必须自增，访问结束自减。**pin count > 0 的页不允许被驱逐**。注意：钉住**不阻止其他事务并发访问该页**——它只阻止驱逐，不提供隔离性（隔离性由 lock 负责）。

### 3.10 Access Tracking Information（访问追踪信息）

记录「谁在访问这一页」，为替换策略（LRU 时间戳、CLOCK 引用位、LRU-K 历史、ARC 列表）提供输入。

### 3.11 Lock（锁）

**高层逻辑原语**，保护数据库的逻辑内容（元组、表、数据库）不受其他事务干扰，持有期是**整个事务**，并且**必须能回滚**。

### 3.12 Latch（闩锁）

**低层保护原语**，保护 DBMS 内部数据结构的临界区（哈希表、内存区域），持有期只是**一次操作**，**不需要回滚**，通常用 mutex / 条件变量实现。

### 3.13 Sequential Flooding（顺序 flooding / 顺序扫描污染）

一次顺序扫描（例如嵌套循环连接的内表扫描）快速读入大量页，把缓冲池里其他查询有用的页全部挤出去。这些被读入的页往往只用一次就再也不用了。此时 **LRU/CLOCK 会做出最坏的决策**：在 OLAP 负载下，「最近使用过的页」往往正是最该被驱逐的页。

### 3.14 LRU-K（K 阶最近最少使用）

记录每页**最近 K 次**访问的时间戳，用「当前时间 − 第 K 次最近访问时间」即**后退距离（backward distance）**作为驱逐依据，并维护**幽灵缓存（ghost cache）**保存刚被驱逐页的历史，防止抖动（thrashing）。

### 3.15 ARC（Adaptive Replacement Cache，自适应替换缓存）

IBM Research 2003 年提出的策略，同时支持**新近性（recency）**与**频率（frequency）**：维护 T1（只访问过一次的页）、T2（至少访问过两次的页）两个实列表与 B1、B2 两个幽灵列表，用目标大小参数 `p` 动态调整 T1/T2 的配额。

### 3.16 Scan Sharing（扫描共享 / 同步扫描）

允许多个查询**挂载到同一个游标**上共享一次表扫描；DBMS 记录第二个查询从哪里加入，扫到末尾后再回头补扫它错过的部分。注意这不同于结果缓存（result caching）。

### 3.17 Buffer Pool Bypass（缓冲池旁路）

顺序扫描算子**不把读到的页放进缓冲池**，而是用查询私有的局部内存。适用于「读一大段连续页且不会再用」的场景，也用于排序、连接等临时数据。Informix 称之为 "Light Scans"。

## 4. 通俗理解

把 DBMS 想成一家**图书馆**，缓冲池就是**阅览室里的桌子**。

- 桌子只有 100 张（frame），书库有 100 万本（磁盘页）。
- 读者要看书，先看桌上有没有（页表查找）；没有就去书库取（读盘），放到空桌上。
- **钉住（pin）** = 你正把书摊在桌上看，别人不能把这本书收走。但别人可以坐到你旁边看同一本书（钉住不排除并发访问）。
- **脏位（dirty）** = 你在书上做了笔记。收走之前必须先还回书库（写回磁盘），否则笔记就丢了。
- **替换策略** = 桌子满了该收走哪本书。LRU 说「收最久没人碰的」；CLOCK 说「我拿手指在桌上转一圈，碰到没被翻过的就收」；LFU 说「收借阅次数最少的」。
- **顺序扫描污染** = 来了一个学生要把整套百科全书从第 1 卷翻到第 100 卷，桌子瞬间被占满，把其他人正在用的书全挤走了——而且他翻完就再也不看了。这时「刚放上桌的书」恰恰是最该收走的。

具体数字：一个 16 KB 页、8 GB 缓冲池 = 约 52 万个 frame；若每次随机读盘 90 µs，而内存命中只需 100 ns，两者差 **900 倍**——这就是为什么缓冲池的命中率是数据库性能的第一决定因素。

## 5. 原理与推导

### 5.1 为什么必须自己做缓冲池：mmap 的四个问题

朴素想法：用 `mmap` 把数据库文件映射进进程地址空间，让 OS 的页缓存替我们做缓存。推导它为什么不行：

1. **事务安全（transaction safety）**：OS 可以**在任何时刻**刷回脏页。DBMS 无法保证「日志先于数据落盘」这一 WAL 规则，崩溃后可能恢复出错误状态。
2. **I/O 停顿（I/O stalls）**：DBMS 不知道哪些页在内存里。访问一个未驻留页会触发缺页，OS 会**阻塞这个线程**，但 DBMS 无法预知、无法调度、也无法把这页换成另一次更紧急的 I/O。
3. **错误处理（error handling）**：难以校验页。任何访问都可能触发 `SIGBUS`，DBMS 必须自己装信号处理器，而信号处理上下文里做恢复极其危险。
4. **性能问题**：OS 内部数据结构争用、**TLB shootdown**（多核上修改页表需要让其他核的 TLB 失效，代价高昂）。

有人会提 `madvise`（告知访问模式）、`mlock`（禁止换出）、`msync`（强制刷盘）。但讲义的评价很直接：**用这些 syscall 让 OS 表现正确，其麻烦程度不亚于自己管理内存**。

结论：DBMS 自己管能做得更好——按正确顺序刷脏页、专用预取、更好的替换策略、线程/进程调度。讲义反复强调一句话：**"The OS is not your friend."**

### 5.2 页表与页目录：两层间接的必然性

```
逻辑 page id
   ├─(页目录, 磁盘持久)──> 文件 + 偏移      ← 页在磁盘哪儿
   └─(页表,   内存易失)──> frame 编号        ← 页在内存哪儿
```

为什么必须分开？因为两者**生命周期与持久性完全不同**：页目录描述「数据的永久位置」，必须落盘；页表描述「当前这一刻的内存副本位置」，重启即失效、可随时重建。混为一谈会导致「重启后 frame 编号无意义」或「每次访问都读盘查目录」的荒谬结果。

### 5.3 钉住计数为什么是正确性的核心

考虑没有 pin 的情况：线程 A 通过页表拿到 frame 7 的指针，正准备读；此时线程 B 触发驱逐，把 frame 7 换成了另一页；A 读到的就是**别的表的数据**——静默错误，比崩溃更可怕。

因此协议必须是：

1. 查页表，命中则 **pin count++**；未命中则选一个 pin count = 0 的 frame，读入页，pin count = 1。
2. 访问期间 pin count 保持 > 0。
3. 访问结束 **pin count--**。

由此推出一个必然的失败模式：**如果所有 frame 都被钉住且缓冲池已满，则无法驱逐，只能抛 out-of-memory 错误**。这不是实现缺陷，而是「钉住」语义的直接后果。

### 5.4 替换策略的推导链：从 LRU 到 ARC

**LRU（1965）**：维护每页最后一次访问的时间戳，驱逐最旧的。要快速找到最旧者，需把页按时间排序（链表或堆）。问题：**每页要存一个大时间戳**，且每次访问都要更新有序结构，元数据开销大。

**CLOCK（1969）**：用一位「引用位」近似 LRU。页排成环形，有一个时钟指针；访问时置位为 1；驱逐时指针扫过：位=1 则清零继续，位=0 则驱逐并前移。**代价从「一个时间戳 + 有序维护」降到「一个 bit + 一次扫描」**，这就是「近似」换来的效率。指针位置在两次驱逐之间保留。

但 LRU 与 CLOCK 有共同的致命缺陷——**sequential flooding**。推导：顺序扫描会以极快速度读入 N 个页，每个页的时间戳都很新，于是缓冲池中原本「稍旧但还会再用」的页全部被挤出。更糟的是，这些新页**不会再被访问**，等于缓冲池被一次性数据彻底污染。在 OLAP 负载下，**MRU 反而常常优于 LRU**。

**LFU（1971）**：记录每页访问**次数**，驱逐次数最少的。解决「频繁但久未访问」的页被误杀的问题。但引入两个新问题：实现复杂度随缓冲池大小呈对数增长（需要按频次分桶的链表）；**忽略时间**，一个曾经很热但现在已冷的页会因高计数长期赖着不走（stale page）。

**LRU-K（1993）**：折中方案。记录最近 K 次访问时间戳，用 `当前时间 − 第 K 次最近访问时间 = 后退距离` 排序，后退距离最大者被驱逐（距离为 ∞ 表示访问次数不足 K 次，优先驱逐）。它**同时考虑了新近性与频率**：只被访问一次的页（第 K 次不存在）天然排在最前，正好解决顺序扫描污染。代价是每页要存 K 个时间戳，且需要维护**幽灵缓存**（记录刚被驱逐页的历史，防止「刚驱逐又被读回」的抖动）。

MySQL 的近似 LRU-2：**单链表 + 两个入口**。页被访问时，若已在 old 区则移到 young 区头部，否则放到 old 区头部；驱逐永远从 old 区尾部取。这用一条链表就实现了「二次访问才晋升」的 LRU-2 语义。

**ARC（2003）**：更进一步，把「新近」与「频率」做成**可自适应调节的两个列表**：

- `T1`：最近只访问过一次的页（新近性）。
- `T2`：至少访问过两次的页（频率）。
- `B1`、`B2`：分别记录从 T1、T2 被驱逐的页（幽灵列表，**只存 page id，页本身不在缓冲池里**）。
- 参数 `p`：T1 的目标大小。约束是 `|T1| + |T2| ≤ C`（C = 缓冲池容量）且 `|T1| + |T2| + |B1| + |B2| ≤ 2C`。

自适应规则（这是 Project #1 的核心逻辑）：

| 情形 | 动作 |
|---|---|
| 命中 T1 或 T2 | 移到 T2 头部（已访问 ≥2 次） |
| 未命中，页在 B1（T1 的幽灵） | **增大 p**（更偏向新近性），页移入 T2 |
| 未命中，页在 B2（T2 的幽灵） | **减小 p**（更偏向频率），页移入 T2 |
| 完全冷未命中 | 先腾位置（按 `|T1|` 与 `p` 的关系决定从 T1 还是 T2 驱逐到对应幽灵列表），新页插入 T1 |

直觉：如果「刚被淘汰的页马上又被访问」（B1 命中），说明 T1 给得太小，应该**多看重新近性**；如果「很久以前热过的页又被访问」（B2 命中），说明 T2 太小，应该**多看中频率**。ARC 不需要人工调参就能自动适应 OLAP/OLTP 混合负载。

### 5.5 脏页驱逐的两条路径

- **快路径（fast path）**：页不脏 → 直接丢弃 frame，无需 I/O。
- **慢路径（slow path）**：页脏 → 必须先写回磁盘，再释放 frame。

这里有一个必须权衡的矛盾：**频繁驱逐**能快速腾出空间，但会把「其实不会再被读」的脏页写出去，浪费 I/O。解决办法是**后台写（background writing / page cleaning / buffer flushing）**：DBMS 周期性扫描页表，提前把脏页写出；写完后可以驱逐，也可以只清脏位。

**关键约束**：后台写必须保证**日志记录先于数据页落盘**（WAL 规则），否则崩溃恢复会看到「数据已改但日志没有」的不可恢复状态。

### 5.6 为什么还要自己调度 I/O 与绕过 OS 页缓存

OS/硬件会重排并批量合并 I/O 请求以最大化带宽，但它**不知道哪些请求更重要**。DBMS 知道：顺序 vs 随机、关键路径 vs 后台任务、表 vs 索引 vs 日志 vs 临时数据、事务信息、用户 SLA。所以 DBMS 维护自己的请求队列并定优先级。很多 DBMS 建议把 Linux 调度器换成 `deadline` 或 `noop`（FIFO）（Oracle、Vertica、MySQL 都有类似建议）。

即便如此，写操作最终还是走 OS API，而 OS 默认维护自己的页缓存，导致：页的**冗余副本**、**两套互相冲突的驱逐策略**、**失去对文件 I/O 的控制**。所以多数 DBMS 用 **Direct I/O（`O_DIRECT`）** 绕过 OS 页缓存。Postgres 是反例，它使用 OS 页缓存。

`fsync` 的坑（讲义标注 "Don't Do This!"）：如果 `fsync` 因 `EIO` 失败，**Linux 会把脏页标记为 clean**；DBMS 再调用一次 `fsync` 就会得到「成功」的答复——于是 DBMS 以为数据安全落盘了，实际没有。这是「OS 不是你的朋友」的最锋利例证。

### 5.7 四种缓冲池优化的适用条件推导

1. **多缓冲池（multiple buffer pools）**：单个缓冲池的 LRU 元数据是全局热点，多线程下闩锁争用严重。按数据库/页类型分池可降低争用、改善局部性。页到池的映射有两种：**Object ID**（在 record id 里嵌对象标识，再查对象→池的映射，控制更细但有存储开销）与**哈希**（`HASH(page_id) % n`，通用均匀）。
2. **预取（prefetching）**：利用查询计划的已知访问顺序，在处理第 1 批页时把第 2 批读进来。顺序扫描与索引扫描（预取**逻辑上**下一个叶子页，不一定是物理相邻页）都适用；有的 DBMS 启动时也预取填满空 frame。
3. **扫描共享（scan sharing）**：当多个查询都要全表扫描时，让后来的查询挂到已在进行的游标上，只读一遍数据。正确性成立的前提是 **DBMS 本就不保证扫描顺序**。注意「连续扫描共享」（continuous scan sharing）是学术原型，按 I/O 计费时非常浪费。
4. **缓冲池旁路（bypass）**：对于「读一遍就不再需要」的大顺序扫描，进缓冲池只会污染它。改为查询私有内存（或用临时文件），代价是放弃复用。

### 5.8 什么负载该选什么策略

| 负载特征 | 推荐 | 理由 |
|---|---|---|
| OLTP，热点页集中，重复访问多 | LRU / CLOCK / ARC | 新近性足够，开销低 |
| OLAP，大量顺序扫描 | LRU-K、ARC、缓冲池旁路 | 抵抗顺序扫描污染 |
| 混合负载、访问模式随时间漂移 | ARC | `p` 自适应，无需人工调参 |
| 频繁全表扫描且多查询重叠 | 扫描共享 | 一次 I/O 服务多个查询 |
| 超大临时数据（排序、连接） | 缓冲池旁路 | 不进池，避免污染 |

## 6. 代码示例

### 6.1 讲义原文示例

**ARC 的四列表与不变量**（`04-bufferpool.pdf` 第 108–112 页）：

```
MRU List (T1):        pages accessed once recently
MRU Ghost List (B1):  history of pages recently evicted from T1 (recency misses)
MFU List (T2):        pages accessed at least twice
MFU Ghost List (B2):  history of pages recently evicted from T2 (frequency misses)
Target Size Parameter (p): adaptively favors recency (T1) vs frequency (T2)

|T1| + |T2| <= C            (C = buffer pool capacity)
|T1| + |T2| + |B1| + |B2| <= 2C
```

讲义第 111 页特别注明：**所有列表只存 page id；幽灵列表中的页不在缓冲池里，而 T1/T2 中的页在缓冲池里。**

**ARC 未命中处理协议**（第 158–162 页原文）：

```
Cache Miss, Page Found in B1 (Ghost of T1):
  -> Increase target size p (favor more recency pages).
  -> Move page into T2 (since it's now accessed again).
Cache Miss, Page Found in B2 (Ghost of T2):
  -> Decrease target size p (favor more frequency pages).
  -> Move page into T2.
Cache Miss, Page Not in Cache or Ghost Lists:
  -> When |T1| + |B1| = C: if |T1| = C, evict from T1;
     otherwise discard from B1, then T1 -> B1 when |T1| > p, else T2 -> B2.
  -> When |T1| + |B1| < C and |T1| + |T2| + |B1| + |B2| >= C:
     if this total = 2C, first discard from B2.
     Next T1 -> B1 when |T1| > p, else T2 -> B2.
  -> Insert new page into T1.
```

**LRU-K 的后退距离**（第 94–96 页）：

```
Eviction Policy:
  CurrentTime - kth LastAccess = Backward Distance
  Use oldest access time to break ties.
```

**fsync 的问题**（第 183–188 页，标注 "Don't Do This!"）：

```
If the DBMS calls write, what happens?
If the DBMS calls fsync, what happens?
If fsync fails (EIO), what happens?
  -> Linux marks the dirty pages as clean.
  -> If the DBMS calls fsync again, then Linux tells you that the
     flush was successful. Since the DBMS thought the OS was its
     friend, it assumed the write was successful...
```

**Project #1 的三个任务**（第 236–244 页）：

```
TASK #1 - ARC REPLACEMENT POLICY
  Build a data structure that tracks the usage of pages using the ARC policy.
  Hints: your eviction algorithm needs to check the "pinned" status of each page;
         you are allowed to use STL containers for internal lists (e.g., MRU, MFU).
TASK #2 - DISK SCHEDULER
  Create a background worker to read/write pages from disk.
  Single request queue but each request can contain multiple requested pages.
  Simulates asynchronous IO using std::promise for callbacks.
TASK #3 - BUFFER POOL MANAGER
  Use your ARC replacer to manage the allocation of pages.
  Need to maintain internal data structures to track allocated + free pages.
  Implement page guards.
Due Date: Sunday Sept 27th @ 11:59pm
```

代码质量要求（第 243 页）：**Google C++ Style Guide + Doxygen Javadoc Style**，提交前必须运行 `make format` 与 `make check-clang-tidy-p1`。项目用 **C++17** 编写，因此需要掌握 `std::optional`、`std::shared_mutex`、结构化绑定等特性。

### 6.2 补充示例（非官方，仅用于说明概念）

**CLOCK 驱逐的伪代码**（非官方）：

```
evict():
    while true:
        p = frames[hand]
        if p.pin_count > 0:            # 钉住的页跳过，不改变引用位
            hand = (hand + 1) % N
            continue
        if p.ref_bit == 1:
            p.ref_bit = 0              # 给第二次机会
            hand = (hand + 1) % N
            continue
        victim = p
        hand = (hand + 1) % N          # 指针位置保留，下次从这继续
        return victim
```

注意两点：钉住页必须**跳过而不清引用位**（否则解钉后它就失去了「最近被用过」的信息）；`hand` 必须在函数返回后保持，这就是讲义说的「clock 在两次驱逐之间记住位置」。

**LRU-K 的记账过程**（非官方，K=2）：

```
on_access(page, now):
    h = history[page]                  # 保存最近 K 个时间戳
    h.push_front(now)
    if len(h) > K: h.pop_back()

backward_distance(page, now):
    if len(history[page]) < K: return INF   # 访问次数不足 K 次
    return now - history[page][K-1]

evict():
    return argmax over unpinned pages of backward_distance(page, now)
```

`INF` 的存在解释了为什么 LRU-2 能抗顺序扫描：只读一次的页后退距离为 ∞，永远先被淘汰，不会挤掉反复访问的页。

## 7. 容易混淆的概念

| 概念对 | 区别 | 记忆要点 |
|---|---|---|
| Page Table vs Page Directory | 页表是**内存哈希表**（page id → frame），易失、不需落盘；页目录是**磁盘映射**（page id → 文件位置），必须落盘 | 表管内存副本，目录管磁盘位置 |
| Lock vs Latch | lock 保护逻辑内容、持有整个事务、可回滚；latch 保护内部数据结构、持有一次操作、不可回滚 | 锁管数据，闩锁管代码 |
| LRU vs CLOCK | LRU 存精确时间戳、需有序结构；CLOCK 只存 1 bit + 环形指针，是 LRU 的近似 | 精度换开销 |
| LFU vs LRU-K | LFU 只看**次数**，忽略时间，会积压 stale 页；LRU-K 看最近 K 次的**时间间隔**，兼顾新近与频率 | LFU 会记仇，LRU-K 会遗忘 |
| 钉住（pin） vs 加锁（lock） | pin 只阻止页被驱逐，不阻止并发访问；lock 才提供隔离 | pin 保命，lock 保正确 |
| 预取（prefetch） vs 扫描共享（scan sharing） | 预取是**一个查询**提前读后续页；扫描共享是**多个查询**共用一次扫描 | 一个提前，一个合并 |
| 缓冲池旁路 vs 多缓冲池 | 旁路是**不进池**；多池是**分池** | 一个绕开，一个分流 |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Slides | `90-原始PDF/15-445/slides/04-bufferpool.pdf` | 245 | 3（空间/时间控制）、4–16（面向磁盘 DBMS 全链路动画）、17（其他内存池）、19–21（frame 与写回缓存）、22–29（页表与每页元数据）、30–31（lock vs latch）、32（页表 vs 页目录）、33–56（mmap 与四个问题、madvise/mlock/msync）、57–62（LRU）、63–76（CLOCK）、77–86（顺序扫描污染）、87–88（LFU）、89–106（LRU-K 与后退距离）、107–162（ARC：列表、不变量、协议）、163–172（局部化与优先级提示）、173–174（脏页与后台写）、175–182（I/O 调度与 OS 页缓存）、183–188（fsync 的坑）、189–233（四种优化）、234（结论）、236–245（Project #1 与学术诚信） |
| Notes | `90-原始PDF/15-445/notes/04-bufferpool.pdf` | 6 | 第 1 页（面向磁盘 DBMS、空间/时间控制、缓冲池定义）、第 2 页（写回缓存、其他内存池、页目录、页表与元数据）、第 3 页（脏位、钉住计数、页表 vs 页目录、lock vs latch、为什么不用 OS）、第 4 页（替换策略目标、LRU、CLOCK、顺序扫描污染、LFU）、第 5 页（LRU-K、MySQL 近似、局部化、优先级提示、ARC、脏页、后台写、磁盘 I/O 与 OS 缓存）、第 6 页（fsync 静默错误、多缓冲池、预取、扫描共享、旁路、结论） |

原始 URL：

- Slides：`https://15445.courses.cs.cmu.edu/fall2026/slides/04-bufferpool.pdf`
- Notes：`https://15445.courses.cs.cmu.edu/fall2026/notes/04-bufferpool.pdf`

> 待核实：第 107 页称 ARC「只在 IBM DB2、PostgreSQL 和 ZFS 中实现，PostgreSQL 为规避 IBM 专利而重写」，此为讲义表述，各系统当前版本的实际实现情况需人工核对。
> 待核实：Project #1 截止日期讲义写的是「Sunday Sept 27th @ 11:59pm」，是否与 Fall 2026 实际校历一致需以官网 project1 页面为准。

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内，本讲内容对应 2025 年第 4 讲）

- 标题：Buffer Pools（2025 年第 4 讲）
- URL：`https://www.youtube.com/watch?v=8-2yv4z0VZc&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 年份：2025
- 时间戳：未核实，故不标注。

## 10. 本节复习

- 能一句话说清空间控制与时间控制分别优化什么。
- 能画出缓冲池结构图，标出 frame 数组、页表、dirty flag、pin counter 的位置。
- 能不看笔记说出页表与页目录的四点区别，以及 lock 与 latch 的三点区别。
- 能复述 mmap 的四个问题，并解释为什么 `mlock` 不能解决事务安全问题。
- 能手工推演一次 CLOCK 驱逐：给定引用位与指针位置，说出淘汰哪一页、指针停在哪。
- 能解释顺序扫描污染为什么让 LRU 在 OLAP 下表现最差，以及 LRU-K 如何靠「后退距离 = ∞」免疫。
- 能画出 ARC 的 T1/T2/B1/B2 四列表，写出两条容量不变量，并说明 B1 命中为什么增大 `p`。
- 能说出脏页驱逐的快/慢路径，以及后台写为什么必须遵守 WAL 顺序。
- 能列举四种缓冲池优化并各举一个适用场景。

## 11. 自我检查

**Q1.** 为什么 DBMS 不用操作系统的页缓存（mmap）？请列出四个问题，并说明为什么用 `madvise` / `mlock` / `msync` 不足以解决。

<details><summary>参考答案</summary>

四个问题：

1. **事务安全**：OS 可以在任意时刻刷回脏页，DBMS 无法保证日志先于数据落盘（WAL 规则被破坏），崩溃后可能恢复出不一致状态。
2. **I/O 停顿**：DBMS 不知道哪些页驻留内存，访问未驻留页会在缺页时**阻塞线程**，DBMS 既无法预知也无法把这次 I/O 换成更紧急的请求。
3. **错误处理**：难以校验页，任何访问都可能触发 `SIGBUS`，DBMS 必须自己处理这个信号，而在信号上下文里做恢复极不可靠。
4. **性能问题**：OS 内部数据结构争用，以及多核上的 **TLB shootdown** 开销。

为什么 syscall 不够：`madvise` 只是给 OS 一个访问模式的**建议**，不保证执行；`mlock` 能防止换出但无法阻止 OS 刷脏页，也无法让 DBMS 获知哪些页在内存、无法控制刷盘顺序；`msync` 只是要求刷某个范围，仍然不解决「OS 在任意时刻自行刷脏页」与「无法按 WAL 顺序刷」的问题。讲义的结论是：用这些 syscall 让 OS 行为正确，其繁琐程度不亚于自己实现缓冲池。

</details>

**Q2.** 页表（page table）与页目录（page directory）有什么区别？为什么两者必须同时存在？

<details><summary>参考答案</summary>

- **页目录**：page id → 该页在**数据库文件中的物理位置**。它是持久结构，任何改动都必须写入磁盘，否则重启后 DBMS 找不到页。通常也缓存在内存以降低延迟，但语义上必须落盘。
- **页表**：page id → 该页在**缓冲池 frame 中的位置**。它是纯内存哈希表，大小固定、用 latch 保护，**不需要也不应该**持久化。

两者必须同时存在，是因为它们回答的是不同的问题、有不同的生命周期。页目录回答「数据永久在哪里」，重启后依然有效；页表回答「此刻内存副本在哪」，重启后 frame 编号毫无意义、需要重建。若只有页目录，每次访问都要读盘查目录；若只有页表，重启后无从知道页在文件中的位置。此外缓冲池淘汰一页后页表项消失，但页目录项必须保留——这正是两者不能合并的原因。

</details>

**Q3.** 给定 4 个 frame、页 p0–p4，初始均为空，指针指向 frame0。依次访问 p1、p3、p4（均置引用位=1），然后需要为 p5 腾位置。请描述 CLOCK 的扫描过程并给出被驱逐的页。

<details><summary>参考答案</summary>

初始：frame0=p1(ref=1)、frame1=p3(ref=1)、frame2=p4(ref=1)、frame3=空，指针在 frame0。

驱逐 p5 时从 frame0 开始扫描：

1. frame0：p1 的 ref=1 → **清 0**，指针移到 frame1。
2. frame1：p3 的 ref=1 → **清 0**，指针移到 frame2。
3. frame2：p4 的 ref=1 → **清 0**，指针移到 frame3。
4. frame3：空 frame，直接放入 p5（指针移到 frame0 或保持在 frame3 之后，取决于实现；讲义强调指针位置需在两次驱逐间保留）。

如果 frame3 不是空的（4 个 frame 全满），则扫描会继续第二轮：此时 p1、p3、p4 的 ref 都已被清 0，于是 frame0 的 p1 被驱逐，p5 放入 frame0，指针停在 frame1。

要点：**CLOCK 的第一次扫描往往不驱逐任何页，只是「给第二次机会」**；钉住的页应被跳过且**不清引用位**。

</details>

**Q4.** 什么是顺序扫描污染（sequential flooding）？为什么 LRU 在这种场景下表现最差，而 LRU-K 能免疫？

<details><summary>参考答案</summary>

**顺序扫描污染**：一个查询对表做顺序扫描（例如嵌套循环连接反复扫内表），以极快速度读入大量页，这些页通常只读一次就不再使用，却把缓冲池中其他查询正在使用的、稍旧但仍会被访问的页全部挤出去，导致整个系统的命中率骤降。

**LRU 最差的原因**：LRU 依据「最后一次访问时间」驱逐，刚被顺序扫描读入的页时间戳最新，因此永远不会被选中；而被挤出的恰恰是有复用价值的页。在 OLAP 负载下，「最近使用过的页」往往正是最该被驱逐的页——LRU 的假设完全反向。

**LRU-K 免疫的原因**：它用「当前时间 − 第 K 次最近访问时间」作为后退距离，访问次数不足 K 次的页其后退距离为 **∞**，被优先驱逐。顺序扫描读入的页只访问一次，距离恒为 ∞，因此它们会立刻互相淘汰，而重复访问的页（有真实的第 K 次访问时间）得以保留。K=2 时即「访问过两次以上才值得留在池中」。

</details>

**Q5.** ARC 中 T1、T2、B1、B2 各存什么？当一次未命中在 B1 中命中页时，为什么要增大 `p`？

<details><summary>参考答案</summary>

- **T1（MRU List）**：最近只被访问过一次的页，这些页**在缓冲池中**。
- **T2（MFU List）**：至少被访问过两次的页，**在缓冲池中**。
- **B1（MRU Ghost List）**：最近从 T1 被驱逐的页的历史，**只存 page id，页不在缓冲池中**（recency misses）。
- **B2（MFU Ghost List）**：最近从 T2 被驱逐的页的历史，只存 page id（frequency misses）。
- **p**：T1 的目标大小，`T2` 的目标大小为 `C − p`；约束 `|T1| + |T2| ≤ C`、`|T1| + |T2| + |B1| + |B2| ≤ 2C`。

**B1 命中就增大 p 的原因**：B1 里的页是「只访问过一次就被从 T1 淘汰」的页。它现在又被访问了，说明「只访问一次的页」其实有复用价值，之前 T1 给的空间太小、淘汰得太早。因此应**增大 p，给新近性（T1）更多配额**，让这类页有机会活到第二次访问。反之，若命中发生在 B2（曾经访问过至少两次、从 T2 淘汰的页又被访问），说明频繁访问的页被过早淘汰，应**减小 p**，把配额让给 T2（频率）。这一机制让 ARC 无需人工调参即可自适应 OLAP/OLTP 混合负载。

</details>

## 12. 进一步学习

- 上一讲：[[15-445-03-Database-Storage-I]] —— 页布局、slotted page、元组布局。
- 下一讲：[[15-445-05-Database-Storage-II]] —— 日志结构存储（log-structured storage）、索引组织表（index-organized storage）与系统目录（catalogs）。
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]、[[40-CMU-15-445/04-学习进度|CMU 15-445 - 学习进度]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：教材 *Database System Concepts*（第 7 版）第 13 章「Data Storage Structures」中的 buffer manager 与 page replacement 小节；ARC 原始论文 Megiddo & Modha, *ARC: A Self-Tuning, Low Overhead Replacement Cache*（FAST 2003）。
- 延伸阅读：讲义第 53–56 页引用的 CIDR 2022 论文 `https://db.cs.cmu.edu/mmap-cidr2022`（关于 mmap 在数据库中的实际表现），可作为「为什么不用 OS 页缓存」的量化证据。
- 动手建议（对应 Project #1，C++17）：先用 `std::vector` + `std::list` 实现一个单线程 ARC，写单元测试验证四条不变量；再加 `std::shared_mutex` 保护页表，最后接入磁盘调度器。注意讲义第 241 页的提醒：**pin 的顺序必须正确**——先 pin 再拿指针，不能反过来。
