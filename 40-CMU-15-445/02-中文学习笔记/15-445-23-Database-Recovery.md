---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: L23
topic: Database Recovery
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 数据库
  - 恢复
  - ARIES
  - CLR
  - 检查点
  - 待发布
---

# 15-445 L23：数据库恢复（Database Recovery）

> **重要说明**：截至 2026-11-10，Fall 2026 官网**尚未发布**本讲的 slides 与 notes（课表日期 Nov 23）。因此本篇第 5 节及之后的技术内容**以下为通用知识整理，非依据 2026 官方讲义**，仅按数据库教材的标准知识框架组织，供预习与对照使用。官方材料发布后须逐条核对并重写。
>
> 本讲在课程中的定位：第 22 讲说明了**日志怎么写、怎么刷、检查点记什么**。这一讲回答「崩溃之后怎么用这些日志把数据库修好」，主角是 **ARIES**——**A**lgorithms for **R**ecovery and **I**solation **E**xploiting **S**emantics，1992 年 IBM Almaden 的 Mohan 等人提出，至今仍是几乎所有主流 DBMS 的恢复算法骨架。核心是三个阶段：**Analysis（分析）→ Redo（重做）→ Undo（撤销）**，以及两个关键设计：**repeating history（重演历史）** 与 **CLR（补偿日志记录）**。

## 1. 本节学习目标

学完本讲，你应该能够：

1. 列出崩溃可能发生的**三种时刻**（事务修改前 / 修改中 / 提交中），并说明恢复算法要覆盖全部情况。
2. 描述 **ARIES 三阶段**各自的目标、输入与输出。
3. 解释 **Analysis 阶段**如何从最后一个检查点重建 **ATT（活跃事务表）** 与 **DPT（脏页表）**。
4. 解释 **Redo 阶段**为什么必须「**repeating history**」——连将要回滚的事务的修改也要重做，以及 `pageLSN` 如何保证幂等。
5. 解释 **Undo 阶段**如何沿每个事务的 `prevLSN` 链反向撤销，以及 **CLR（Compensation Log Record）** 为什么必需。
6. 说明 ARIES 如何处理**崩溃发生在恢复过程中**（恢复的恢复）——靠 CLR 的 `undoNextLSN`。
7. 说明**非易失存储的失败**（磁盘损坏）为什么需要**镜像 / 副本 / 备份**，日志本身不够。

## 2. 前置知识

- **WAL、LSN、pageLSN、recLSN、检查点**：见 [[15-445-22-Database-Logging]]，这是本讲的直接前提；不熟悉这些术语无法理解 ARIES。
- **缓冲池的 steal / no-force**：见 [[15-445-04-Memory-Management]]，ARIES 是为 steal + no-force 设计的。
- **事务与 Strict 2PL**：见 [[15-445-19-Two-Phase-Locking]]，ARIES 假设锁在 undo 完成后才释放（否则会有「读未回滚数据」的问题）。
- **MVCC**：见 [[15-445-21-MVCC]]，MVCC 的 undo log 与恢复的 undo 是两套不同机制，容易混淆。
- **C++ 提醒**：本课程项目用 **C++17**、**Google C++ Style** 与 clang-format；Project #4 的恢复部分需要实现 `LogRecovery`（`Redo` / `Undo`）与 `LogManager::ReadLogRecord`，注意日志迭代器的边界处理。

## 3. 核心概念

> 以下概念定义为通用教材口径，待 2026 官方 slides 发布后核对术语与侧重。

### 3.1 ARIES

IBM Almaden 于 1992 年提出的恢复算法，三阶段：**Analysis → Redo → Undo**。设计目标是支持**细粒度锁（fine-granularity locking）** 与**部分回滚（partial rollback）**。

### 3.2 Analysis Phase（分析阶段）

从最后一个检查点开始正向扫描日志，重建崩溃时刻的 **ATT**（哪些事务还活着）与 **DPT**（哪些页是脏的、各自 `recLSN` 是多少），并确定 redo 起点。

### 3.3 Redo Phase（重做阶段）

从 DPT 的**最小 `recLSN`** 开始正向扫描，**重放所有 update**（包括即将回滚的事务的 update），用 `pageLSN` 判断是否跳过。目标是**恢复到崩溃前一刻的状态**。

### 3.4 Undo Phase（撤销阶段）

从日志尾部**反向**扫描，撤销所有**未提交**事务的修改，每撤销一条就写一条 **CLR**。

### 3.5 CLR（Compensation Log Record，补偿日志记录）

一条特殊的日志记录，表示「我已经撤销了 LSN=X 的那条修改」。CLR 含 `undoNextLSN`（该事务下一条待撤销记录的 LSN），使得**恢复过程中再次崩溃**时可以从中断处继续。

### 3.6 Repeating History（重演历史）

ARIES 的核心原则：redo 阶段**无条件重放**日志中的每一条 update（只要 `pageLSN < LSN`），**不管它属于已提交还是未提交事务**。先把数据库恢复到崩溃前的**精确状态**，再统一 undo。这样恢复逻辑简单、且 undo 时页面状态是确定的。

### 3.7 Fuzzy Checkpoint Recovery（模糊检查点恢复）

从检查点的 ATT/DPT 快照出发，继续扫描检查点之后的日志，补上期间发生的事务开始/结束与新的脏页。

### 3.8 Undo Next LSN（下一条待撤销 LSN）

CLR 中的字段，指向「这个事务还需要撤销的下一条日志记录的 LSN」。它是「恢复的恢复」能正确工作的关键。

### 3.9 Media Failure（介质故障）

磁盘本身损坏（不是进程崩溃），日志文件也可能一起损坏。需要**归档日志 + 全量备份 + 副本**（RAID 只能防单盘故障，不能防逻辑损坏或机房事故）。

## 4. 通俗理解

**ARIES 像「事故现场重建 + 清理」**：

1. **Analysis（看监控）**：从最后一次「系统状态快照」（检查点）开始看录像，搞清楚「出事那一刻，哪些人还在楼里（活跃事务）、哪些房间还没打扫完（脏页）」。
2. **Redo（重演）**：把录像里发生过的每一个动作**原样重放一遍**，哪怕这个动作是「一个后来被判定为无效的人做的」。为什么？因为只有把现场恢复到**出事那一刻的精确样子**，你才知道该清理什么。这就是 **repeating history**。
3. **Undo（清理）**：从后往前，把「还没办完手续的人」做的事一件件撤销，每撤销一件就在本子上记一笔（**CLR**）——万一清理到一半又出事了，下次接着这本子继续，不会重复撤销。

**CLR 就像「清理进度表」**：没有它，清理到一半再出事，下次就不知道哪些已经清理过、哪些没有，可能重复撤销（把别人的东西也撤了）。

**为什么不能「跳过未提交事务的 redo」**：假设 T1 改了页 P（LSN 100），T2 又改了同一页 P（LSN 200），T1 未提交、T2 已提交。如果 redo 时跳过 T1 的修改，直接应用 T2 的修改——但 T2 的 `after_image` 是**基于 T1 修改后**的值算出来的！跳过 T1 会导致 T2 的结果错误。所以必须**先全部重放，再统一撤销**。

## 5. 原理与推导

> **以下为通用知识整理，非依据 2026 官方讲义。**

### 5.1 崩溃的三种时刻

| 时刻 | 崩溃前状态 | 恢复要求 |
|---|---|---|
| 事务修改前 | 日志未写、页未改 | 无需处理 |
| 事务修改中 | 日志可能已写、页可能部分落盘 | **undo** 未完成的修改 |
| 事务提交中 | `COMMIT` 记录可能已写、页可能未落盘 | 若 `COMMIT` 已落盘 → **redo**；否则 **undo** |

关键判据：**`COMMIT` 记录是否已持久化到日志文件**。已落盘 = 事务提交成功（必须 redo）；未落盘 = 事务未提交（必须 undo）。

### 5.2 Analysis 阶段详解

**输入**：最后一个成功的检查点记录（`CHECKPOINT-BEGIN` 的 ATT/DPT 快照）。
**输出**：崩溃时刻的 ATT、DPT，以及 `redo_start_lsn`。

**算法**（正向扫描）：

```
初始化 ATT = 检查点快照中的活跃事务（status = running）
初始化 DPT = 检查点快照中的脏页表
redo_start_lsn = min(DPT 中所有 recLSN)

for each log record R from checkpoint onward:
    if R is UPDATE:
        if R.page_id not in DPT:
            DPT[R.page_id] = R.lsn        # 第一次让该页变脏
        if R.txn_id not in ATT:
            ATT[R.txn_id] = {lastLSN: R.lsn, status: running}
        else:
            ATT[R.txn_id].lastLSN = R.lsn
    elif R is COMMIT or ABORT (end of txn):
        ATT.remove(R.txn_id)              # 事务已结束
    elif R is CLR:
        if R.txn_id not in ATT:
            ATT[R.txn_id] = {lastLSN: R.lsn, status: running}
        else:
            ATT[R.txn_id].lastLSN = R.lsn
```

**结束时的 ATT 就是「崩溃时仍未提交的事务」**，它们全部要 undo。

**注意**：ABORT 记录也算「事务结束」——但一个已经开始回滚的事务，它的部分修改可能还没撤销完，此时需要特殊处理（ARIES 用 CLR 与 `undoNextLSN` 追踪，见 5.6）。

### 5.3 Redo 阶段详解

**起点**：`redo_start_lsn = min(recLSN in DPT)`。
**终点**：日志末尾。

**算法**（正向扫描）：

```
for each log record R from redo_start_lsn onward:
    if R is UPDATE or CLR:
        page = fetch_page(R.page_id)
        if page.pageLSN >= R.lsn:
            continue                       # 幂等：这页已包含该修改
        apply(R.after_image or CLR 的效果)
        page.pageLSN = R.lsn
```

**两个关键点**：

1. **不区分事务是否提交**——所有 update 都重放（repeating history）。
2. **`pageLSN >= R.lsn` 就跳过**——保证幂等，即使恢复被中断并重启多次也正确。

**为什么必须 repeating history**（核心论证）：设 T1（未提交）在 LSN 100 把 A 从 100 改成 200，T2（已提交）在 LSN 200 把 A 从 200 改成 300。若 redo 时跳过 T1，则 T2 的 `after_image`（300）虽然还是对的，但如果 T2 的操作是「A = A * 1.5」（逻辑操作），跳过 T1 会得到 150 而不是 300——**结果错误**。即使全是物理日志，跳过 T1 也会让「undo T1」时找不到正确的 `before_image` 上下文。所以**必须完整重演**。

### 5.4 Undo 阶段详解

**输入**：Analysis 阶段得到的 ATT（未提交事务集合）。
**起点**：日志末尾（反向扫描）。

**算法**：

```
to_undo = 所有未提交事务的 lastLSN（放进一个最大堆/优先队列，按 LSN 降序）

while to_undo not empty:
    L = to_undo.pop_max()                  # 取最大的 LSN（最新的修改先撤）
    R = read_log(L)
    if R is CLR:
        to_undo.push(R.undoNextLSN)        # 跳过已撤销的部分，继续往前
    elif R is UPDATE:
        apply(R.before_image)              # 撤销
        write CLR(txn=R.txn, undoNextLSN=R.prevLSN, lsn=new_lsn)
        to_undo.push(R.prevLSN)            # 沿该事务的链继续
    elif R is BEGIN:
        write ABORT record for R.txn
```

**为什么用最大堆**：多条事务交错修改同一页时，**必须按 LSN 从大到小撤销**，否则会撤销错误的版本。这与「栈」的语义一致。

**为什么每条 undo 都要写 CLR**：

1. **崩溃发生在恢复过程中**：下次恢复时看到 CLR，就知道「这条已经撤销过了」，通过 `undoNextLSN` 直接跳到下一条，**不会重复撤销**。
2. **CLR 本身是 redo-only 的**：CLR 永远不会被 undo（撤销一个撤销没有意义）。
3. **审计与部分回滚**：CLR 让「回滚到 savepoint」也能用同一套机制。

### 5.5 「恢复的恢复」

**场景**：恢复进行到一半，系统又崩溃了。

**分析阶段**：日志尾部有若干 CLR。扫描时：
- 遇到 CLR → 该事务仍在 ATT 中，`lastLSN = CLR.lsn`。
- 于是 undo 阶段从这个 CLR 开始，读它的 `undoNextLSN`，**跳过已经撤销的部分**，从那里继续。

**关键**：`undoNextLSN` 记录了「这个事务还需要撤销的下一条记录」。它等价于「撤销进度指针」。

**为什么不能用 `prevLSN` 代替**：`prevLSN` 指向「日志中该事务的上一条记录」，但那条记录可能**已经被撤销过**（对应某条 CLR）。`undoNextLSN` 是「**还没撤销的**下一条」，语义不同。

### 5.6 事务回滚（正常路径）vs 恢复（异常路径）

两者都调用 undo 逻辑，但触发方式不同：

| 维度 | 正常回滚（`ROLLBACK`） | 崩溃恢复 |
|---|---|---|
| 触发 | 应用显式请求 / 死锁受害者 | 重启时自动 |
| 范围 | 单个事务 | 所有未提交事务 |
| 锁 | undo 完成后释放 | 恢复期间不释放（重启后重新获取） |
| 日志 | 写 CLR + ABORT 记录 | 写 CLR + ABORT 记录 |
| 顺序 | 沿该事务的链 | 多事务按 LSN 降序交错 |

**共用 CLR 机制**是 ARIES 的设计优点：一套代码处理两种场景。

### 5.7 检查点与恢复时间的权衡

**恢复时间 ≈ (日志末尾 - redo_start_lsn) 的重放时间 + undo 时间**。

- 检查点**越频繁** → `redo_start_lsn` 越靠近日志末尾 → 恢复越快，但**运行时开销越大**（刷页 I/O）。
- 检查点**越稀疏** → 运行时开销小，但恢复慢。

**调参**：PostgreSQL 的 `checkpoint_timeout`（默认 5 分钟）与 `max_wal_size` 共同决定检查点频率；`checkpoint_completion_target`（默认 0.9）控制刷页速率，把 I/O 摊平。

### 5.8 介质故障与备份

日志只能防**进程崩溃 / 断电**（内存丢失但磁盘完好）。若磁盘本身损坏：

- **RAID** 防单盘故障，但不防「控制器把坏数据写进去」（write hole）、不防机房火灾。
- **归档日志（archive log / WAL 归档）**：把日志文件持续拷贝到另一处存储。
- **全量备份 + 增量备份**：定期做基础备份（base backup），配合归档日志可以恢复到任意时间点（**PITR, Point-In-Time Recovery**）。
- **副本（replica）**：流复制到从库，主库全毁时切换。

**恢复流程（PITR）**：恢复基础备份 → 重放归档日志到目标时间点 → 打开数据库。

### 5.9 ARIES 与其他恢复方案的对比

| 方案 | 特点 | 问题 |
|---|---|---|
| **Shadow Paging** | 不需要 undo/redo，恢复只需切指针 | 写放大、并发控制难（第 18 讲已述） |
| **WAL + ARIES** | 主流，支持细粒度锁与部分回滚 | 实现复杂，日志量大 |
| **WAL + 简单 redo/undo**（无 CLR） | 实现简单 | 恢复中断后无法继续，必须从头再来 |
| **MVCC + undo log**（InnoDB） | 读不阻塞写 | undo log 双用途（MVCC + 回滚），purge 复杂 |

**ARIES 的历史地位**：它把「恢复」从「一堆特例」变成了「一个有清晰不变式的算法」，其 `pageLSN` 幂等判定、CLR、repeating history 三个设计被后续所有系统继承。

## 6. 代码示例

### 6.1 官方课程代码

**截至 2026-11-10，Fall 2026 官方 slides 与 notes 尚未发布**，本讲无官方代码可引。待发布后须补充：

- 官方 slides 中的 ARIES 三阶段流程图与 CLR 结构；
- 官方 notes 中的 Figure（ATT/DPT 演化、undo 链）。

> 待核实：官方材料发布后，本节的页码引用需要重新填写。

### 6.2 Agent 自行编写的教学示例

> 以下代码**非官方，仅用于说明概念**。

ATT 与 DPT 的结构（示意）：

```cpp
// 非官方示例：Analysis 阶段维护的两张表
struct TxnEntry {
  lsn_t last_lsn;
  enum class Status { kRunning, kCommitting, kAborting } status;
};

struct DirtyPageEntry {
  lsn_t rec_lsn;   // 第一次让该页变脏的 LSN
};

using ATT = std::unordered_map<txn_id_t, TxnEntry>;
using DPT = std::unordered_map<page_id_t, DirtyPageEntry>;
```

Analysis 阶段骨架（示意）：

```cpp
// 非官方示例
void Analysis(LogIterator &it, ATT &att, DPT &dpt, lsn_t &redo_start) {
  for (; it.HasNext(); it.Next()) {
    const LogRecord &r = it.Get();
    switch (r.type) {
      case LogRecord::Type::kUpdate:
        dpt.try_emplace(r.page_id, DirtyPageEntry{r.lsn});
        att[r.txn_id] = TxnEntry{r.lsn, TxnEntry::Status::kRunning};
        break;
      case LogRecord::Type::kCommit:
      case LogRecord::Type::kAbort:
        att.erase(r.txn_id);
        break;
      case LogRecord::Type::kClr:
        att[r.txn_id] = TxnEntry{r.lsn, TxnEntry::Status::kAborting};
        break;
      default: break;
    }
  }
  redo_start = std::min_element(dpt.begin(), dpt.end(),
      [](auto &a, auto &b) { return a.second.rec_lsn < b.second.rec_lsn; })->second.rec_lsn;
}
```

Redo 阶段的幂等判定（示意）：

```cpp
// 非官方示例
void Redo(const LogRecord &r, Page *page) {
  if (page->GetLSN() >= r.lsn) return;   // 已经应用过，跳过
  ApplyImage(page, r.after_image);
  page->SetLSN(r.lsn);
}
```

Undo 阶段（示意）：

```cpp
// 非官方示例：按 LSN 降序撤销，每条写 CLR
void Undo(std::priority_queue<lsn_t> &to_undo) {
  while (!to_undo.empty()) {
    lsn_t l = to_undo.top(); to_undo.pop();
    LogRecord r = ReadLog(l);
    if (r.type == LogRecord::Type::kClr) {
      to_undo.push(r.undo_next_lsn);          // 已撤销过，跳过
    } else if (r.type == LogRecord::Type::kUpdate) {
      ApplyImage(GetPage(r.page_id), r.before_image);
      lsn_t clr_lsn = AppendClr(r.txn_id, r.prev_lsn, l);
      to_undo.push(r.prev_lsn);
    } else if (r.type == LogRecord::Type::kBegin) {
      AppendAbort(r.txn_id);
    }
  }
}
```

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| Redo 起点 | Undo 起点 | redo 从 DPT 最小 `recLSN` **正向**；undo 从日志**末尾反向** |
| `prevLSN` | `undoNextLSN` | 前者是「该事务上一条日志」；后者是「该事务**还没撤销**的下一条」，CLR 专用 |
| Redo | Undo | redo 恢复**已提交**的效果（也重演未提交的，随后再撤）；undo 撤销**未提交**的效果 |
| ARIES 的 undo | MVCC 的 undo log | 前者服务**崩溃恢复**；后者服务**多版本读**（InnoDB 两者共用一套结构，但语义不同） |
| 事务回滚 | 崩溃恢复 | 前者是**正常路径**（单事务）；后者是**异常路径**（所有未提交事务），共用 CLR 机制 |
| 检查点 | 备份 | 检查点是**日志里的标记**（缩短恢复）；备份是**数据的副本**（防介质故障） |
| 进程崩溃 | 介质故障 | 前者磁盘完好，日志能救；后者磁盘损坏，必须靠备份 + 归档日志 |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Slides | **尚未发布** | — | 截至 2026-11-10，`https://15445.courses.cs.cmu.edu/fall2026/slides/` 下无本讲文件；本地 `90-原始PDF/15-445/slides/` 亦无 |
| Notes | **尚未发布** | — | 同上，`90-原始PDF/15-445/notes/` 下无本讲文件 |

原始 URL（待发布后核对）：

- Slides：`https://15445.courses.cs.cmu.edu/fall2026/slides/`（本讲具体文件名待定，2026 课表第 23 讲日期 Nov 23）
- Notes：`https://15445.courses.cs.cmu.edu/fall2026/notes/`（同上）

> 待核实：2025 年该讲对应的 slides 文件名按错位规律推断为 `22-recovery.pdf` 或 `22-databaserecovery.pdf`，但**未在本地 `_scout` 中确认**，故不写具体页码。

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内，本讲内容对应 2025 年第 22 讲）

- 标题：Database Recovery（2025 年第 22 讲）
- URL：`https://www.youtube.com/watch?v=X2jc4qalNy0&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 年份：2025
- 时间戳：未核实，故不标注。

说明：FAQ Q11 明确 Fall 2026 的录像只对 CMU 学生开放，非 CMU 学习者应观看 Fall 2025 的公开视频。

## 10. 本节复习

- 能列出崩溃的三种时刻，并说明判据是「`COMMIT` 记录是否落盘」。
- 能按顺序描述 ARIES 三阶段的目标与输入输出。
- 能写出 Analysis 阶段对各类日志记录的处理规则。
- 能解释 repeating history 的必要性（用「T1 未提交、T2 已提交、同一页」的例子）。
- 能说明 `pageLSN` 如何保证 redo 幂等。
- 能说明 CLR 的 `undoNextLSN` 如何支持「恢复的恢复」。
- 能区分 `prevLSN` 与 `undoNextLSN`。
- 能说明为什么日志不能防介质故障，以及 PITR 的流程。

## 11. 自我检查

**Q1.** 为什么 ARIES 的 redo 阶段要重做**未提交**事务的修改？直接跳过不是更省事吗？

<details><summary>参考答案</summary>

**不能跳过，因为后续事务的修改可能依赖于前面未提交事务的结果。**

**具体例子**：

```
LSN 100: T1（未提交）UPDATE A = A + 100   （A: 100 → 200）
LSN 200: T2（已提交）  UPDATE A = A * 2    （A: 200 → 400）
崩溃
```

若 redo 时跳过 LSN 100（因为 T1 未提交），直接应用 LSN 200 的 `after_image`：

- 如果是**物理日志**（记录 `after_image = 400`）：A 会变成 400，看起来对——但**页上原本是 100**（假设崩溃时页未落盘），直接写 400 恰好正确。这种情况跳过没问题。
- 如果是**逻辑日志**（记录 `A = A * 2`）：A 从 100 变成 200——**错误**（应该是 400）。

**更根本的理由**：ARIES 用 **physiological logging**，`after_image` 是页内字节级的值，看似可以直接应用。但**undo 阶段需要正确的页面状态**：如果跳过 T1 的修改，undo T1 时页上的值就不是「T1 修改后」的状态，`before_image` 的应用会出错。

**第三个理由**：**简化算法**。若 redo 要判断「这个事务最终会不会提交」，就必须先完整分析所有事务的结局——这实际上要求先把日志扫完，与「redo 是正向单遍扫描」的设计冲突。repeating history 让 redo 变成**无状态的单遍扫描**，undo 才需要复杂逻辑。

**一句话**：repeating history 把「部分恢复」的复杂判断，转化成了「先全做、再全撤」的简单两段式。

</details>

**Q2.** 恢复进行到一半系统又崩溃了，重启后 ARIES 如何保证不重复撤销？

<details><summary>参考答案</summary>

靠 **CLR 的 `undoNextLSN`**。

**场景**：

```
LSN 100: T1 UPDATE A（before=100, after=200）
LSN 200: T1 UPDATE B（before=50, after=60）
崩溃 → 恢复开始
  undo LSN 200 → 写 CLR(lsn=300, undoNextLSN=100)   ← 表示"200 已撤销，下一条撤 100"
  ... 此时又崩溃 ...
重启 → 第二次恢复
```

**第二次 Analysis**：扫描到 LSN 300 的 CLR，把 T1 放回 ATT，`lastLSN = 300`。

**第二次 Undo**：从 LSN 300 开始（不是从 200！）：

1. 读 LSN 300，是 CLR → 把 `undoNextLSN = 100` 推入待撤销队列，**跳过 200**（已经撤销过）。
2. 读 LSN 100，是 UPDATE → 撤销（应用 `before_image = 100`），写 CLR(lsn=400, undoNextLSN=BEGIN 的 LSN)。
3. 读 BEGIN → 写 ABORT 记录，事务结束。

**关键**：CLR 本身是 **redo-only** 的——它记录「这个撤销动作已经发生」，永远不会被再撤销。所以第二次恢复只需**重放 CLR**（redo 阶段），然后从 `undoNextLSN` 继续。

**如果没有 CLR**：第二次恢复不知道 LSN 200 是否已撤销，只能从头（LSN 200）再来一遍——如果撤销是幂等的还好，但若 `before_image` 的应用不是幂等的（例如「A = A - 100」这种逻辑操作），就会**重复扣款**。

</details>

**Q3.** Analysis 阶段为什么需要从**最后一个检查点**开始扫描，而不是从日志开头？

<details><summary>参考答案</summary>

因为**检查点已经包含了「到那一刻为止的完整状态摘要」**：

- **ATT 快照**：检查点时刻所有活跃事务及其 `lastLSN`。检查点之前已经开始、且到检查点仍未提交的事务，都在这里。
- **DPT 快照**：检查点时刻所有脏页及其 `recLSN`。检查点之前变脏且尚未落盘的页，都在这里。

**因此检查点之前的日志记录不影响崩溃时刻的状态**——它们要么属于已提交/已中止的事务（不需要 undo），要么对应的修改已经被检查点记录在 DPT 里（redo 起点已经确定）。

**反例说明为什么不能从开头**：如果日志有 100 GB，从开头扫描需要几十分钟到几小时；而检查点每 5 分钟一次，从最后一个检查点扫描只需重放最多 5 分钟的日志——**恢复时间从小时级降到秒级**。

**边界情况**：

1. **检查点记录本身可能损坏**（写了一半崩溃）→ ARIES 会往前找**上一个完整的检查点**。
2. **检查点之后没有新日志**（刚检查点完就崩溃）→ Analysis 直接结束，ATT/DPT 就是快照内容。
3. **模糊检查点**（第 22 讲）：检查点的 DPT 可能不完整（有些页在检查点期间才变脏），但 Analysis 会继续扫描检查点之后的日志补上——这正是「从检查点**开始**扫描」而非「只用检查点快照」的原因。

</details>

**Q4.** 一个事务在 `COMMIT` 记录写入日志文件后、但数据页还没落盘时崩溃。恢复后这个事务的修改还在吗？

<details><summary>参考答案</summary>

**在**。这正是 **No-Force** 策略下 redo 的作用。

**时间线**：

```
1. 事务 T 修改页 P（日志记录 LSN 100 写入内存缓冲区）
2. T 执行 COMMIT → 写 COMMIT 记录（LSN 200）到日志缓冲区
3. WAL 规则二：fsync 日志到 LSN 200  ← 此刻 T 已"提交成功"
4. 应用收到 "commit ok"
5. 页 P 仍在缓冲池中，未落盘
6. 崩溃
```

**恢复**：

- Analysis：扫描到 LSN 200 的 COMMIT 记录 → T 不在 ATT 中（已提交）。
- Redo：从 DPT 的 `recLSN`（可能是 100）开始，重放 LSN 100 的 update（页 P 的 `pageLSN` 是 0，小于 100 → 应用）。
- Undo：ATT 为空，什么都不做。

**结果**：页 P 包含了 T 的修改，**持久性得到保证**。

**关键点**：**「提交成功」的判据是 COMMIT 记录落盘，而不是数据页落盘**。这是 WAL 规则二的意义——它让提交只需一次顺序日志写，而不必等待随机页写。

**反过来**：若崩溃发生在第 3 步**之前**（COMMIT 记录未落盘），恢复时 T 会被当作未提交而 undo——应用也没收到 "commit ok"，所以语义一致（客户端会重试）。

</details>

**Q5.** 日志能防机房断电，但防不住磁盘物理损坏。为什么？该怎么补？

<details><summary>参考答案</summary>

**为什么防不住**：日志与数据页通常放在**同一块磁盘**（或同一存储系统）上。磁盘物理损坏（磁头撞击、闪存颗粒失效、控制器故障）会**同时损坏日志与数据**。此时：

- 没有日志 → 无法 redo 也无法 undo。
- 即使有部分日志，日志中的 `page_id` 指向的页可能已经不存在。

**RAID 也不够**：RAID 1/5/6 能防**单盘/双盘故障**，但防不住：

- **Write hole**：RAID 5 在断电时可能让奇偶校验与数据不一致。
- **控制器级故障**：整块 RAID 卡烧毁。
- **逻辑损坏**：软件 bug 或误操作把好数据写成坏数据（RAID 会忠实地把坏数据复制到所有盘）。
- **机房级事故**：火灾、水淹、地震。

**补充手段（三层防御）**：

1. **归档日志（WAL archiving）**：持续把日志文件拷贝到**异地存储**（对象存储、另一机房）。PostgreSQL 的 `archive_command` 或 `pg_receivewal`。
2. **基础备份（base backup）**：定期做全量物理备份（`pg_basebackup`），配合归档日志可以恢复到**任意时间点**（PITR）。
3. **副本（replica）**：流复制到从库，主库全毁时**故障切换（failover）**。副本还能分担只读查询。

**恢复流程（PITR）**：

```
1. 从备份恢复基础数据目录
2. 配置 recovery_target_time = '2026-11-10 12:00:00'
3. 重放归档日志直到该时间点
4. 打开数据库（此时一致性恢复）
```

**成本**：三层防御都有成本（存储、带宽、运维复杂度），所以按 **RPO（恢复点目标）/ RTO（恢复时间目标）** 分级设计——不是所有系统都需要异地三副本。

</details>

## 12. 进一步学习

- 上一讲：[[15-445-22-Database-Logging]] —— WAL、LSN、检查点，本讲的直接前提。
- 下一讲：[[15-445-24-Distributed-Databases]] —— 分布式环境下的复制与 2PC，恢复问题在多机场景下的延伸。
- 相关：[[15-445-18-Concurrency-Control-Theory]] —— Atomicity 与 Durability 的原始定义。
- 相关：[[15-445-21-MVCC]] —— MVCC 的 undo log 与恢复的 undo 是两套机制。
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：教材 *Database System Concepts*（第 7 版）第 19 章「Recovery System」；Mohan 等人的 "ARIES: A Transaction Recovery Method Supporting Fine-Granularity Locking and Partial Rollbacks Using Write-Ahead Logging"（ACM TODS 1992）——本讲的原始论文，强烈建议读第 3–5 节。
- 动手建议：读 BusTub 的 `src/recovery/log_recovery.cpp`（如果已发布）观察 Analysis/Redo/Undo 的骨架；在 PostgreSQL 中用 `pg_waldump` 查看 WAL 记录的实际格式。
- **注意**：本讲 2026 官方材料尚未发布，以上内容为通用知识整理，**待官方 slides 发布后必须核对并重写第 5、6、8 节**。
