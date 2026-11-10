---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: L22
topic: Database Logging
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 数据库
  - 恢复
  - 预写日志
  - WAL
  - LSN
  - 检查点
  - 待发布
---

# 15-445 L22：数据库日志（Database Logging）

> **重要说明**：截至 2026-11-10，Fall 2026 官网**尚未发布**本讲的 slides 与 notes（课表日期 Nov 18）。因此本篇第 5 节及之后的技术内容**以下为通用知识整理，非依据 2026 官方讲义**，仅按数据库教材的标准知识框架组织，供预习与对照使用。官方材料发布后须逐条核对并重写。
>
> 本讲在课程中的定位：第 18 讲说过 Atomicity 与 Durability 都靠**日志**。这一讲把日志讲透：日志里记什么、**LSN** 是什么、**WAL 规则**为什么必须遵守、**检查点（checkpoint）** 如何缩短恢复时间、以及**缓冲池如何与日志协同**（steal / no-steal、force / no-force 四种策略）。下一讲（第 23 讲）在此之上给出 **ARIES** 三阶段恢复算法。

## 1. 本节学习目标

学完本讲，你应该能够：

1. 解释**崩溃恢复（crash recovery）** 要解决的两个问题：**已提交事务的修改不能丢**、**未提交事务的修改不能留**。
2. 说明**物理日志（physical logging）** 与**逻辑日志（logical logging）** 的区别，以及 **physiological logging（物理-逻辑混合）** 为什么是主流。
3. 定义 **LSN（Log Sequence Number）**，说明它在日志记录、数据页、日志文件三处的含义与作用。
4. 精确陈述 **WAL（Write-Ahead Logging）规则**的两条内容，并解释违反它会带来什么后果。
5. 描述 **检查点（checkpoint）** 的作用与**模糊检查点（fuzzy checkpoint）** 的必要性，说明检查点里记录什么。
6. 区分 **steal / no-steal** 与 **force / no-force** 四种缓冲池策略，并指出哪种组合需要 undo、哪种需要 redo。
7. 说明**组提交（group commit）** 与 **日志刷盘（fsync）** 对性能的影响，以及为什么「每次提交都 fsync」会成为瓶颈。

## 2. 前置知识

- **事务与 ACID**：见 [[15-445-18-Concurrency-Control-Theory]]，尤其 Atomicity 与 Durability 的实现机制。
- **缓冲池与页**：见 [[15-445-04-Memory-Management]]，理解「脏页（dirty page）」与「驱逐（eviction）」。
- **磁盘管理器**：见 [[15-445-03-Database-Storage-I]]，理解页的读写与 fsync。
- **并发控制**：见 [[15-445-19-Two-Phase-Locking]]，Strict 2PL 的「锁持有到提交」与日志的「undo 到提交」是配套的。
- **C++ 提醒**：本课程项目用 **C++17**、**Google C++ Style** 与 clang-format；Project #4 的日志部分需要实现 `LogManager`（`AppendLogRecord`、`Flush`）、`std::atomic<lsn_t>` 与页的 `GetLSN/SetLSN`。

## 3. 核心概念

> 以下概念定义为通用教材口径，待 2026 官方 slides 发布后核对术语与侧重。

### 3.1 Write-Ahead Log（预写日志，WAL）

一种日志协议：**日志记录必须先于对应的数据页写入非易失存储**。这是实现 Atomicity + Durability 的标准手段，也是几乎所有 DBMS 的选择。

### 3.2 Log Sequence Number（日志序列号，LSN）

日志文件中每条记录的**唯一、单调递增**的标识（通常是该记录在日志文件中的字节偏移）。三个位置都有 LSN：

- **日志记录**自身的 LSN；
- **数据页**上记录的 `pageLSN`（最后一次修改该页的日志记录的 LSN）；
- **日志文件**的 `flushedLSN`（已持久化的最大 LSN）。

### 3.3 Physical Logging（物理日志）

记录**字节级**的变化：「页 P 的偏移 42 处的 8 个字节从 X 改成 Y」。恢复精确，但日志体积大。

### 3.4 Logical Logging（逻辑日志）

记录**逻辑操作**：「事务 T 在表 R 上插入一行 (1, 'Andy')」。日志小，但恢复时需要重新执行、且结果可能不确定（非确定性函数）。

### 3.5 Physiological Logging（物理-逻辑日志）

折中方案：**以页为单位物理定位，页内用逻辑描述**。「页 P 上插入槽位 3 的元组」。这是 ARIES 与主流 DBMS 的选择。

### 3.6 Checkpoint（检查点）

DBMS 定期记录的一个「一致点」：此刻所有已修改的页都已刷盘（或至少记录了脏页表），日志在此之前的部分在恢复时可以跳过。缩短恢复时间。

### 3.7 Fuzzy Checkpoint（模糊检查点）

不停止事务、不强制刷所有脏页的检查点：只记录**当前活跃事务表（ATT）** 与**脏页表（DPT）** 的快照。恢复时从这些表的**最早 LSN** 开始。

### 3.8 Steal / No-Steal

**Steal**：允许把**未提交事务修改的脏页**驱逐出缓冲池（写回磁盘）。**No-Steal**：不允许。

### 3.9 Force / No-Force

**Force**：事务提交时**强制**把它的所有脏页刷盘。**No-Force**：提交时不强制刷页，只保证日志落盘。

### 3.10 Group Commit（组提交）

把多个事务的提交日志**攒成一批**一起 fsync，用一次 I/O 的代价完成多次提交，显著提升吞吐。

## 4. 通俗理解

**日志 = 记账本，数据页 = 正式账本**。

- **WAL 规则** = 「**先在草稿上记下你要改什么，再去改正式账本**」。这样万一改到一半停电，你可以对着草稿知道「哪些改完了、哪些没改」，从而补完或撤销。
- **LSN** = 草稿上的**行号**。正式账本每一页上也记着「我最后是按草稿第几行改的」，这样恢复时就知道「这一页已经包含了草稿到第几行的内容」。
- **检查点** = 「**到此为止的草稿都已经抄进正式账本了，前面那些草稿可以不用再看了**」。没有检查点，恢复就要从开天辟地开始重放。
- **Steal** = 「允许把还没定稿的草稿内容先抄到正式账本上」。好处是缓冲区不会被长事务占满；坏处是崩溃后必须**撤销**这些未定稿的内容。
- **No-Force** = 「提交时不急着抄正式账本，只保证草稿落盘」。好处是提交极快（一次顺序写 vs 多次随机写）；坏处是崩溃后必须**重做**已提交但未落页的内容。

一句话记忆：**Steal 需要 undo，No-Force 需要 redo**。

## 5. 原理与推导

> **以下为通用知识整理，非依据 2026 官方讲义。**

### 5.1 崩溃恢复的两个目标

崩溃（断电、进程被杀、OS panic）发生时，内存中的一切丢失，磁盘上的数据页可能是**任意时刻的旧值**。恢复要保证：

1. **Durability**：所有**已提交**事务的修改必须在重启后可见 → 需要 **redo**。
2. **Atomicity**：所有**未提交**事务的修改必须不可见 → 需要 **undo**。

这两件事都要求 DBMS 在崩溃前把「足够的信息」写到磁盘上——这就是日志。

### 5.2 为什么不能靠「影子分页」

第 18 讲已经说过 shadow paging 被淘汰。补充一个恢复视角的原因：shadow paging 需要维护**页映射表（page table）** 的双份副本与原子切换，页表本身可能很大，且随机写多；而 WAL 是**顺序追加**，对 SSD/HDD 都友好。

### 5.3 日志记录的形态

一条典型的 **update 记录**包含：

| 字段 | 含义 |
|---|---|
| `LSN` | 本条记录的编号 |
| `prevLSN` | **同一事务**上一条日志记录的 LSN（用于反向遍历，undo 时用） |
| `txn_id` | 事务 ID |
| `type` | `UPDATE` / `COMMIT` / `ABORT` / `BEGIN` / `CLR`（补偿日志记录） |
| `page_id` | 被修改的页 |
| `offset` / `length` | 页内位置（physiological） |
| `before_image` | 修改前的值（undo 用） |
| `after_image` | 修改后的值（redo 用） |

**`prevLSN` 是 ARIES 的关键设计**：它让每个事务的日志成为一条**独立的链**，undo 时可以「只沿着某个事务的链回溯」，而不必扫描整个日志。

### 5.4 LSN 的三处作用

1. **日志记录 LSN**：标识位置，用于「从哪个 LSN 开始恢复」。
2. **页的 `pageLSN`**：每页头部记录「最后修改我的日志记录的 LSN」。
   - **Redo 时的幂等判定**：若 `pageLSN >= 待重放的日志 LSN`，说明这一页已经包含了该修改，**跳过**（这保证 redo 是**幂等**的，崩溃后重复恢复不会出错）。
3. **`flushedLSN`**（日志管理器维护）：已持久化的最大 LSN。
   - **WAL 检查**：刷页前必须保证 `pageLSN <= flushedLSN`。

### 5.5 WAL 规则（两条）

**规则一（undo 规则）**：在把**未提交事务**修改的页写入磁盘之前，必须先把这个页对应的 **undo 日志**（含 `before_image`）刷盘。

**规则二（redo 规则）**：在**提交**之前，必须把该事务的**所有日志记录**（含 `after_image` 与 `COMMIT` 记录）刷盘。

**统一表述**：**日志必须先于数据页落盘**，且**提交记录必须先于「告诉用户提交成功」**。

**违反的后果**：

- 违反规则一：脏页先落盘、日志没落盘，崩溃后**无法 undo**（不知道原值是什么）→ 原子性被破坏。
- 违反规则二：告诉用户「提交成功」但日志没落盘，崩溃后**无法 redo** → 持久性被破坏（用户以为存了，其实没存）。

### 5.6 缓冲池策略的四种组合

| 策略 | 含义 | 恢复需要 | 典型系统 |
|---|---|---|---|
| **Steal + No-Force** | 允许驱逐未提交页；提交不强制刷页 | **undo + redo** | 几乎所有主流 DBMS |
| Steal + Force | 允许驱逐；提交强制刷页 | 只需 undo | 少见（提交太慢） |
| No-Steal + No-Force | 不允许驱逐未提交页；提交不刷页 | 只需 redo | 部分内存数据库 |
| No-Steal + Force | 不允许驱逐；提交强制刷页 | 都不需要（但性能极差） | 几乎不用 |

**为什么主流选 Steal + No-Force**：

- **Steal** 让缓冲池可以自由驱逐，不被长事务卡住（否则一个更新百万行的事务会占满缓冲池）。
- **No-Force** 让提交只需一次**顺序日志写**，而不是多次**随机页写**——这是性能的关键。
- 代价是恢复时必须同时 undo 与 redo，所以算法更复杂（ARIES 就是为此设计的）。

### 5.7 检查点：为什么要它

**没有检查点**：恢复时必须从日志**开头**重放，日志可能几十 GB，恢复要几十分钟。

**检查点记录**（在日志里写一条 `CHECKPOINT` 记录）包含：

- **活跃事务表（Active Transaction Table, ATT）**：当前未提交的事务及其 `lastLSN`、`status`。
- **脏页表（Dirty Page Table, DPT）**：每个脏页的 `recLSN`（**最早**使该页变脏的日志 LSN）。

**恢复起点**：从检查点中**所有 `recLSN` 与 `lastLSN` 的最小值**开始重放。

**为什么需要 `recLSN` 而不是页的 `pageLSN`**：`pageLSN` 是**最后**一次修改的 LSN，而 redo 必须从**最早**未落盘的修改开始——否则会漏掉中间的修改。这是初学者最容易搞错的点。

### 5.8 模糊检查点（Fuzzy Checkpoint）

**朴素检查点**要「停止接受新事务 + 把所有脏页刷盘 + 写检查点记录」——这会**冻结系统**几秒到几分钟，不可接受。

**模糊检查点**的做法：

1. 暂停一瞬间，记录 ATT 与 DPT 的**快照**，写入日志（`CHECKPOINT-BEGIN`）。
2. **立刻恢复**正常处理。
3. 后台**异步**把 DPT 里的脏页刷盘。
4. 刷完后写 `CHECKPOINT-END`。

**关键**：检查点期间事务继续执行，新产生的脏页也记录在 DPT 里；恢复时从快照的 `recLSN` 最小值开始，保证不漏。

### 5.9 日志刷盘的性能问题

每次 `COMMIT` 都要 `fsync` 日志文件，而一次 fsync 在机械盘上约 **5–10 ms**，在 SSD 上约 **0.1–1 ms**。如果串行执行，吞吐上限就是 **100–200 TPS**（机械盘）——这对现代系统完全不够。

**解决方案**：

1. **组提交（Group Commit）**：把 N 个事务的提交日志攒在一起，一次 fsync 全部落盘。吞吐提升接近 N 倍，代价是每个事务的延迟略微增加（等一小批）。
2. **批量提交（Batching）**：应用层把多个操作合并成一个事务。
3. **`synchronous_commit = off`**（PostgreSQL）：提交时不 fsync，崩溃可能丢失最近几百毫秒的事务——牺牲一点持久性换吞吐。
4. **NVMe / 持久内存（PMem）**：硬件层面降低 fsync 成本。
5. **日志写在独立设备**：避免与数据页 I/O 争抢。

### 5.10 日志与恢复的分工

本讲讲「日志怎么写、怎么刷、检查点怎么记」；下一讲（第 23 讲）讲「崩溃后怎么用这些日志」：

- **Analysis（分析）**：从最后一个检查点开始，重建 ATT 与 DPT，确定「哪些事务要 undo、哪些页要 redo」。
- **Redo（重做）**：从 DPT 的最小 `recLSN` 开始，重放所有修改（**包括将回滚事务的修改**，因为 ARIES 要求 redo 一切）。
- **Undo（撤销）**：从日志尾部反向扫描，撤销所有未提交事务的修改，并写 **CLR（Compensation Log Record，补偿日志记录）** 防止重复 undo。

## 6. 代码示例

### 6.1 官方课程代码

**截至 2026-11-10，Fall 2026 官方 slides 与 notes 尚未发布**，本讲无官方代码可引。待发布后须补充：

- 官方 slides 中的日志记录格式与 WAL 规则示意；
- 官方 notes 中的 Figure（LSN 在页与日志中的位置、检查点结构）。

> 待核实：官方材料发布后，本节的页码引用需要重新填写。

### 6.2 Agent 自行编写的教学示例

> 以下代码**非官方，仅用于说明概念**。

日志记录与 LSN（示意）：

```cpp
// 非官方示例：一条 update 日志记录
using lsn_t = uint64_t;

struct LogRecord {
  lsn_t lsn;            // 本条记录的编号
  lsn_t prev_lsn;       // 同一事务上一条记录的 LSN
  txn_id_t txn_id;
  enum class Type { kBegin, kUpdate, kCommit, kAbort, kClr } type;
  page_id_t page_id;
  uint32_t offset;
  uint32_t length;
  std::string before_image;   // undo 用
  std::string after_image;    // redo 用
};
```

WAL 检查（示意）：刷页前必须确认日志已落盘。

```cpp
// 非官方示例：把脏页写回磁盘前的 WAL 检查
void BufferPoolManager::FlushPage(page_id_t pid) {
  Page *page = GetPage(pid);
  // WAL 规则一：pageLSN 之前的日志必须已持久化
  if (page->GetLSN() > log_manager_->GetFlushedLSN()) {
    log_manager_->Flush(page->GetLSN());   // 先把日志刷到该 LSN
  }
  disk_manager_->WritePage(pid, page->GetData());
}
```

提交路径（示意）：

```cpp
// 非官方示例：提交时必须先刷日志，再返回成功
void Transaction::Commit() {
  lsn_t commit_lsn = log_manager_->AppendLogRecord(
      LogRecord{.txn_id = txn_id_, .type = LogRecord::Type::kCommit});
  log_manager_->Flush(commit_lsn);   // WAL 规则二：提交记录必须落盘
  // 此时才能告诉客户端 "commit ok"
}
```

检查点记录（示意）：

```cpp
// 非官方示例：模糊检查点写入的内容
struct CheckpointRecord {
  std::unordered_map<txn_id_t, lsn_t> active_txn_last_lsn;  // ATT
  std::unordered_map<page_id_t, lsn_t> dirty_page_rec_lsn;  // DPT：recLSN 是最早让页变脏的 LSN
};
```

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| LSN | pageLSN | LSN 标识日志记录的位置；pageLSN 是**页上记录的**「最后修改我的日志 LSN」，用于 redo 幂等判定 |
| pageLSN | recLSN | pageLSN 是**最后**一次修改的 LSN；recLSN 是**最早**一次未落盘修改的 LSN（redo 起点） |
| WAL 规则一 | WAL 规则二 | 规则一保证 **undo 能力**（未提交页落盘前日志先落盘）；规则二保证 **redo 能力**（提交前日志落盘） |
| Steal | No-Force | Steal 决定「要不要 undo」；No-Force 决定「要不要 redo」；两者正交 |
| 物理日志 | 逻辑日志 | 前者记字节级差异，恢复精确但体积大；后者记逻辑操作，体积小但可能不确定 |
| 检查点 | 快照 | 检查点是**日志里的标记 + 表快照**（用于恢复）；快照是 MVCC 的**版本可见性边界**（用于并发控制） |
| Undo | CLR | undo 是「撤销一个操作」；CLR 是「记录我已经撤销过这个操作」的日志，防止重复 undo |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Slides | **尚未发布** | — | 截至 2026-11-10，`https://15445.courses.cs.cmu.edu/fall2026/slides/` 下无本讲文件；本地 `90-原始PDF/15-445/slides/` 亦无 |
| Notes | **尚未发布** | — | 同上，`90-原始PDF/15-445/notes/` 下无本讲文件 |

原始 URL（待发布后核对）：

- Slides：`https://15445.courses.cs.cmu.edu/fall2026/slides/`（本讲具体文件名待定，2026 课表第 22 讲日期 Nov 18）
- Notes：`https://15445.courses.cs.cmu.edu/fall2026/notes/`（同上）

> 待核实：2025 年该讲对应的 slides 文件名按错位规律推断为 `21-logging.pdf` 或 `21-databaselogging.pdf`，但**未在本地 `_scout` 中确认**，故不写具体页码。

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内，本讲内容对应 2025 年第 21 讲）

- 标题：Database Logging（2025 年第 21 讲）
- URL：`https://www.youtube.com/watch?v=CedEy54pe3g&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 年份：2025
- 时间戳：未核实，故不标注。

说明：FAQ Q11 明确 Fall 2026 的录像只对 CMU 学生开放，非 CMU 学习者应观看 Fall 2025 的公开视频。

## 10. 本节复习

- 能说出崩溃恢复的两个目标，以及各自对应 redo 还是 undo。
- 能区分物理日志、逻辑日志、physiological 日志，并说明为什么主流选第三种。
- 能说出 LSN 在三处的含义（日志记录、pageLSN、flushedLSN），以及 pageLSN 如何保证 redo 幂等。
- 能精确陈述 WAL 的两条规则，并说明违反各自的后果。
- 能列出 steal / no-steal × force / no-force 四种组合及各自需要 undo 还是 redo。
- 能说明检查点记录里 ATT 与 DPT 的内容，以及为什么 redo 起点用 `recLSN` 而不是 `pageLSN`。
- 能解释模糊检查点为什么必要。
- 能说明组提交如何把 fsync 的瓶颈摊薄。

## 11. 自我检查

**Q1.** 如果 DBMS 违反了 WAL 规则一（先把未提交的脏页刷盘，日志还没刷），崩溃后会发生什么？

<details><summary>参考答案</summary>

**原子性被破坏**。具体场景：

1. 事务 T 修改页 P（A 从 100 改成 50），日志记录写进**内存中的日志缓冲区**但**未 fsync**。
2. 缓冲池因空间不足驱逐页 P，把 `A=50` 写回磁盘。
3. 此刻崩溃。

**恢复时**：

- 磁盘上的 P 已经是 `A=50`（未提交的值）。
- 日志文件里**没有**这条 update 记录（还在内存缓冲区，已丢失）。
- 恢复程序根本**不知道** T 曾经修改过 P，因此**无法 undo**。

结果：数据库里留下了 `A=50`——一个**从未提交**的修改，永久生效。原子性被破坏。

**正确做法**：在 `FlushPage` 之前检查 `pageLSN > flushedLSN`，若是则先 `Flush(pageLSN)`。这样日志一定先于数据页落盘，恢复时必然能找到 undo 信息。

**补充**：如果日志记录已落盘但 `COMMIT` 记录没落盘，恢复时会把 T 当作「未提交」而 undo 它——这是正确的（T 确实没提交成功）。

</details>

**Q2.** 为什么 redo 的起点要用脏页表里的 `recLSN`（最早 LSN），而不是页上的 `pageLSN`（最后 LSN）？

<details><summary>参考答案</summary>

因为**页可能被修改多次**，而磁盘上的版本只包含「到某个时刻为止」的修改。

**例子**：页 P 在 LSN 100、200、300 处被修改三次，但一直没有刷盘。此刻崩溃，磁盘上的 P 是**初始状态**（不含任何修改）。

- 若用 `pageLSN = 300` 作为起点：只会重放 LSN 300 的修改，**漏掉 100 和 200**——P 的最终状态错误。
- 若用 `recLSN = 100`（第一次让它变脏的 LSN）：从 100 开始重放，100、200、300 全部应用——正确。

**`recLSN` 的定义**：**第一次**使该页变脏的日志记录的 LSN。它在页**从干净变为脏**的那一刻被设置，之后即使继续修改也不更新（除非页被刷盘后再次变脏）。

**`pageLSN` 的作用不同**：它是 redo 时的**幂等判定**——「若 `pageLSN >= 待重放的 LSN`，说明这页已经包含该修改，跳过」。所以：

- `recLSN` 决定**从哪里开始**（下界）；
- `pageLSN` 决定**每条记录是否要应用**（幂等检查）。

两者配合，才能既不漏、又不重复。

</details>

**Q3.** 为什么主流 DBMS 都选 Steal + No-Force，而不选「No-Steal + Force」（后者理论上恢复最简单）？

<details><summary>参考答案</summary>

「No-Steal + Force」理论上恢复只需「什么都不做」（未提交页不会落盘、已提交页一定落盘），但**运行时性能不可接受**：

**No-Steal 的问题**：

1. **缓冲池被长事务锁死**：一个更新 1000 万行的事务，在提交前所有脏页都不能驱逐——需要把 1000 万行的页全部驻留内存。缓冲池装不下就**必须暂停事务**（或拒绝），系统停滞。
2. **并发度低**：多个大事务同时进行时，缓冲池需求叠加，很快耗尽。

**Force 的问题**：

1. **提交延迟高**：提交时必须把所有脏页刷盘，而脏页在磁盘上是**随机分布**的——100 个页就是 100 次随机 I/O。机械盘上可能要几十毫秒。
2. **写放大**：同一个页在事务中被修改多次，Force 只写一次（还好），但如果事务短、页分散，随机写代价极高。
3. **与 WAL 的顺序写优势相悖**：WAL 的日志是**顺序追加**（极快），Force 却强迫随机页写。

**Steal + No-Force 的代价**：恢复要同时 undo + redo，算法复杂（ARIES）。但这是**一次性的复杂度**，换来的是**运行时的吞吐**——工程上完全值得。

**一句话**：把复杂度放在**罕见的崩溃恢复路径**上，而不是**每时每刻的正常路径**上。

</details>

**Q4.** 组提交（group commit）为什么能提升吞吐？它的代价是什么？

<details><summary>参考答案</summary>

**原理**：`fsync` 的成本主要是「等待设备确认」（机械盘约 5–10 ms，SSD 约 0.1–1 ms），而不是数据量。如果 100 个事务各自 fsync，总时间 ≈ 100 × 5 ms = 500 ms；如果攒成一批一次 fsync，总时间 ≈ 5 ms——**吞吐提升 100 倍**。

**实现**：日志管理器维护一个待刷队列；一个「刷盘线程」周期性（或当队列达到阈值时）把队列里所有记录一次性写入并 fsync，然后唤醒所有等待的事务。

**代价**：

1. **单事务延迟增加**：事务要等一小批攒齐（通常是毫秒级），P99 延迟变差。
2. **实现复杂度**：需要正确的同步（避免「以为刷了其实没刷」），以及处理「刷盘失败」的路径。
3. **批量大小的调参**：太小则提升有限，太大则延迟不可接受。常见做法是「时间窗口 + 数量阈值」双条件。

**相关优化**：

- **流水线式组提交**：把「写」与「fsync」分离，多个 fsync 可以重叠进行（Linux 的 `io_uring`、AIO）。
- **`synchronous_commit = off`**：完全跳过提交时的 fsync，靠后台周期性刷盘——崩溃可能丢失最近的事务，但吞吐最高。
- **NVMe / 持久内存**：把 fsync 成本降到微秒级，组提交的收益随之下降。

</details>

**Q5.** 模糊检查点（fuzzy checkpoint）与「停止世界（stop-the-world）检查点」相比，恢复时多做了什么工作？

<details><summary>参考答案</summary>

**Stop-the-world 检查点**：暂停所有事务 → 把所有脏页刷盘 → 写检查点记录 → 恢复。此刻**没有任何脏页**，所以恢复可以从检查点**直接开始**（DPT 为空）。

**模糊检查点**：只记录 ATT 与 DPT 的快照，**脏页仍在内存中**（甚至检查点期间还在产生新的脏页）。因此恢复时必须：

1. **从 DPT 的最小 `recLSN` 开始 redo**，而不是从检查点位置开始——因为检查点时刻磁盘上的页可能是很旧的版本。
2. **处理检查点期间新产生的脏页**：这些页的 `recLSN` 可能大于检查点记录，但只要它们在 DPT 里就会被处理。
3. **重建 ATT**：检查点时的活跃事务可能已经提交或中止，需要扫描日志确定它们的最终状态。

**代价对比**：

- Stop-the-world：**恢复快**（从检查点直接开始），但**运行时卡顿**（可能几秒到几分钟，取决于脏页数量）。
- 模糊检查点：**恢复稍慢**（要多重放一些日志），但**运行时不卡顿**。

**工程选择**：几乎所有生产系统都用模糊检查点——因为「每 5 分钟卡顿 10 秒」是不可接受的，而「恢复多花 30 秒」完全可以接受。

**极端优化**：PostgreSQL 的 `CHECKPOINT` 会限制刷页速率（`checkpoint_completion_target`），把 I/O 摊平到整个检查点周期，进一步减少对正常查询的影响。

</details>

## 12. 进一步学习

- 上一讲：[[15-445-21-MVCC]] —— 多版本并发控制，MVCC 的旧版本也需要日志保护。
- 下一讲：[[15-445-23-Database-Recovery]] —— ARIES 三阶段（Analysis / Redo / Undo），本讲的日志格式正是为它设计的。
- 相关：[[15-445-04-Memory-Management]] —— 缓冲池的驱逐策略与 steal 语义。
- 相关：[[15-445-18-Concurrency-Control-Theory]] —— Atomicity 与 Durability 的机制来源。
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：教材 *Database System Concepts*（第 7 版）第 19 章「Recovery System」前半；Mohan 等人的 "ARIES: A Transaction Recovery Method Supporting Fine-Granularity Locking and Partial Rollbacks Using Write-Ahead Logging"（ACM TODS 1992）是 WAL + 恢复的奠基论文。
- 动手建议：读 PostgreSQL 的 `src/backend/access/transam/xlog.c` 中 `XLogFlush` 的实现，观察 `flushedLSN` 与组提交的具体写法；用 `pg_controldata` 查看检查点信息。
- **注意**：本讲 2026 官方材料尚未发布，以上内容为通用知识整理，**待官方 slides 发布后必须核对并重写第 5、6、8 节**。
