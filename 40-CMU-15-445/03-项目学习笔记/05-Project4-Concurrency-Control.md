---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: P4
topic: Project 4 - Concurrency Control
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 项目
  - 并发控制
  - 锁管理器
  - MVCC
  - 事务
---

# 15-445 Project #4：并发控制（Concurrency Control）

> **重要边界说明**：本 vault **未抓取** Fall 2026 的 project4 官方页面，本篇为「课程结构公开信息 + 通用知识」整理，**具体规格细节一律标 `> 待核实：`**，不编造。
>
> 官方页面（待人工核对）：`https://15445.courses.cs.cmu.edu/fall2026/project4/`
>
> 对应讲义：[[15-445-18-Concurrency-Control-Theory]]、[[15-445-19-Two-Phase-Locking]]、[[15-445-20-Timestamp-Ordering]]、[[15-445-21-MVCC]]。Fall 2026 课表把 Concurrency Control 项目安排在第 19 周。
>
> **Fall 2026 政策提醒**：Project #4 **允许使用 coding agents**，但必须提交**一页反思（reflection）**说明如何使用（官方主页原文 "P3-P4 permit them and require a one-page reflection"）。同时官方强调 "You must understand and own all submitted code"，另有 Code Reasoning Interview 可能被要求。

## 1. 本节学习目标

1. 能设计并实现**锁管理器（Lock Manager）**：行级锁的授予、等待队列、相容性矩阵。
2. 能实现 **2PL（两阶段锁）** 与**严格 2PL（Strict 2PL）**，理解「增长阶段/收缩阶段」的边界。
3. 能实现**死锁检测（deadlock detection）**：waits-for graph、环检测、受害者选择。
4. 能实现**基于时间戳的并发控制**：Basic T/O、Thomas Write Rule、OCC。
5. 能实现 **MVCC（多版本并发控制）**：版本链、可见性判定、事务快照、垃圾回收。
6. 能实现**事务管理器（Transaction Manager）**：`Begin` / `Commit` / `Abort`、事务状态机、全局事务表。
7. 理解**隔离级别（isolation level）** 与 MVCC 的关系：快照隔离（SI）能防什么、不能防什么（写偏斜）。
8. 理解并发控制与**恢复（recovery）** 的接口：日志、LSN、回滚。

## 2. 前置知识

- **C++17**：`std::mutex`、`std::condition_variable`、`std::shared_mutex`、`std::atomic`、RAII、智能指针。见 `01-Project0-Cpp-Primer.md`。
- **缓冲池与页守卫**：MVCC 的版本数据要落在页上，读写要走 Page Guard。见 `02-Project1-Buffer-Pool.md`。
- **B+ 树与 latch crabbing**：索引层的并发（latch）与事务层的并发（lock）是两回事。见 `03-Project2-BPlusTree.md`。
- **事务的 ACID**：原子性、一致性、隔离性、持久性。见 [[15-445-18-Concurrency-Control-Theory]]。
- **可串行化与冲突可串行化**：优先图（precedence graph）、冲突（conflict）的定义。见 [[15-445-18-Concurrency-Control-Theory]]。
- **2PL 与死锁**：见 [[15-445-19-Two-Phase-Locking]]。
- **时间戳排序与 OCC**：见 [[15-445-20-Timestamp-Ordering]]。
- **MVCC 与快照隔离**：见 [[15-445-21-MVCC]]。

## 3. 核心概念

### 3.1 Lock Manager（锁管理器）

**职责**：管理所有事务对数据项（行/RID）的锁请求，保证相容性、处理等待与释放。

**核心数据结构**：

```cpp
struct LockRequest {
  txn_id_t txn_id;
  LockMode mode;              // SHARED / EXCLUSIVE / ...
  bool granted;
};

struct LockRequestQueue {
  std::list<LockRequest> request_queue;   // FIFO 等待队列
  std::condition_variable cv;             // 唤醒等待者
  bool upgrading = false;                 // 是否有升级请求在等待
};

std::unordered_map<RID, LockRequestQueue> lock_table_;
std::mutex latch_;                        // 保护 lock_table_
```

**接口**：

```cpp
bool LockShared(txn, rid);      // 申请 S 锁（阻塞直到授予）
bool LockExclusive(txn, rid);   // 申请 X 锁
bool LockUpgrade(txn, rid);     // S → X 升级
bool Unlock(txn, rid);          // 释放锁
```

**相容性矩阵（Compatibility Matrix）**：

| 请求 \ 持有 | SHARED | EXCLUSIVE |
|---|---|---|
| **SHARED** | 相容 | 冲突 |
| **EXCLUSIVE** | 冲突 | 冲突 |

### 3.2 Two-Phase Locking（两阶段锁，2PL）

**两条规则**：

1. **增长阶段（growing phase）**：只能加锁，不能解锁。
2. **收缩阶段（shrinking phase）**：只能解锁，不能加锁。

**严格 2PL（Strict 2PL）**：所有**排他锁（X 锁）** 持有到事务结束（`Commit` / `Abort`）。这保证**可恢复性（recoverability）** 和**无级联回滚（no cascading abort）**。

**强严格 2PL（Rigorous 2PL）**：**所有锁**（S 和 X）都持有到事务结束。实践中常用，因为实现简单（`Unlock` 只在事务结束时批量调用）。

### 3.3 Deadlock Detection（死锁检测）

**waits-for graph（等待图）**：

- 节点 = 事务。
- 边 `Ti → Tj`：`Ti` 在等待 `Tj` 持有的锁。
- **环 = 死锁**。

**检测时机**：

- **周期性**（后台线程每 N 毫秒跑一次）。
- **加锁时**（每次阻塞前检查）。

**受害者选择（victim selection）** 启发式：

- 工作量最少的事务（回滚代价小）。
- 已持有锁最少的事务。
- 已执行时间最短的事务。
- 避免「饿死」：记录回滚次数，优先不选被回滚过多次的。

**回滚方式**：

- **完全回滚（total rollback）**：撤销所有操作，重新开始。
- **部分回滚（partial rollback）**：回滚到某个 savepoint。

### 3.4 Timestamp Ordering（时间戳排序）

**核心思想**：给每个事务分配一个**时间戳（timestamp, TS）**，保证并发执行等价于「按时间戳串行执行」。

**Basic T/O 的两条规则**（对数据项 `X`）：

- **读规则**：若 `TS(Ti) < W-TS(X)`（`X` 已被更晚的事务写过）→ **中止 `Ti`**。
- **写规则**：若 `TS(Ti) < R-TS(X)` 或 `TS(Ti) < W-TS(X)` → **中止 `Ti`**。

**Thomas Write Rule（托马斯写规则）**：若 `TS(Ti) < W-TS(X)`，**忽略这次写**（而不是中止）。这产生**视图可串行化（view serializable）** 但**非冲突可串行化**的调度。

### 3.5 Optimistic Concurrency Control（乐观并发控制，OCC）

**三个阶段**：

1. **读阶段（read phase）**：事务读数据、在私有工作区（private workspace）做修改，**不写数据库**。
2. **验证阶段（validation phase）**：检查是否与其他事务冲突。通过则进入写阶段，否则中止。
3. **写阶段（write phase）**：把私有工作区的修改应用到数据库。

**验证条件**（对 `Ti` 与所有已提交的 `Tj`，`TS(Tj) < TS(Ti)`）：

- `Tj` 在 `Ti` 开始读之前已完成（`Tj` 的写阶段结束 < `Ti` 的读阶段开始），或
- `Tj` 的写集合与 `Ti` 的读集合不相交，或
- `Tj` 的写集合与 `Ti` 的写集合不相交（且 `Tj` 的写阶段在 `Ti` 的读阶段之前结束）。

### 3.6 MVCC（多版本并发控制）

**核心思想**：写操作**不覆盖**旧值，而是创建**新版本（version）**。读者读「对自己可见」的版本，从而**读写不阻塞**。

**版本链（version chain）**：每个逻辑元组维护一条版本链，按时间戳排序。

**两种布局**：

- **Append-only（追加式）**：新版本插到链头，旧版本保留。PostgreSQL 用堆表 + `ctid` 链。
- **Delta / undo（增量式）**：主版本存最新值，旧值存 undo log。MySQL InnoDB 用 undo log。

**可见性判定（visibility）**：

```
版本 V 对事务 T 可见 ⟺ V.begin_ts <= T.read_ts < V.end_ts
```

其中 `read_ts` 是事务开始时取的快照时间戳，`begin_ts` 是创建该版本的事务提交时间戳，`end_ts` 是删除/覆盖该版本的事务提交时间戳。

**快照隔离（Snapshot Isolation, SI）**：

- 事务开始时取一个快照，整个事务期间只读该快照。
- **写冲突规则**：两个并发事务写同一行 → **先提交者胜（first-committer-wins）**，后者中止。

**SI 不能防：写偏斜（write skew）**——两个事务各读对方的写集合、各写自己的读集合，无写写冲突但结果不满足约束。

### 3.7 Transaction Manager（事务管理器）

**职责**：维护事务的全局状态、分配事务 ID、协调 `Begin` / `Commit` / `Abort`。

**事务状态机**：

```
RUNNING ──Commit──► COMMITTED
   │
   └──Abort──► ABORTED
```

**事务表（transaction map）**：

```cpp
std::unordered_map<txn_id_t, Transaction> txn_map_;
std::atomic<txn_id_t> next_txn_id_{0};
std::atomic<timestamp_t> next_timestamp_{0};
```

**`Commit` 时要做的**：

1. 把事务状态置为 `COMMITTED`，记录 `commit_ts`。
2. 释放所有锁（严格 2PL 下）。
3. 写提交日志（若项目含恢复）。
4. 通知等待该事务的事务（如 MVCC 的版本可见性）。

**`Abort` 时要做的**：

1. 回滚所有修改（用 undo log 或版本链）。
2. 释放所有锁。
3. 把状态置为 `ABORTED`。

### 3.8 Isolation Levels（隔离级别）

| 级别 | 脏读 | 不可重复读 | 幻读 | 实现方式 |
|---|---|---|---|---|
| **READ UNCOMMITTED** | 可能 | 可能 | 可能 | 无锁 / 只加写锁 |
| **READ COMMITTED** | 不可能 | 可能 | 可能 | 读时加 S 锁并立即释放 |
| **REPEATABLE READ** | 不可能 | 不可能 | 可能 | 读时加 S 锁持有到事务结束 |
| **SERIALIZABLE** | 不可能 | 不可能 | 不可能 | 严格 2PL / SSI |

**MVCC 下的对应**：

- **READ COMMITTED**：每次读取新快照（statement-level snapshot）。
- **REPEATABLE READ / SNAPSHOT**：事务开始时取一次快照（transaction-level snapshot）。

## 4. 通俗理解

**锁管理器 = 图书馆借书台**：一本书（数据项）可以多人同时看（S 锁），但要修改（X 锁）就得独占。管理员记下谁在等，等书还回来就通知下一个。

**2PL = 「先全部借齐，再开始还」**：你不能一边借新书一边还旧书——必须先把手头需要的都借到（增长阶段），然后才开始还（收缩阶段）。

**严格 2PL = 「书用到项目结束才还」**：为了保证别人看到的数据是「最终态」，你把书留到整个项目（事务）结束才归还。

**死锁 = 两个人各拿一半工具等对方**：A 拿着锤子等螺丝刀，B 拿着螺丝刀等锤子。解决方式要么让一个人放弃（回滚），要么按固定顺序拿工具（预防）。

**时间戳排序 = 排队号决定顺序**：每个人进场拿一个号，规则是「号小的先做」。如果号大的人已经做完了某一步，号小的人就不能再做那一步（会被中止重来）。

**OCC = 先在自己草稿纸上写，最后统一提交**：你在草稿上改，改完检查「有没有人和我改了同一处」，没有就正式提交，有就重来。

**MVCC = 文档的版本历史**：每次修改都存一个新版本（像 Google Docs 的版本历史），读者想看哪个版本就看哪个，不需要等写者。写者也不需要等读者。

**写偏斜 = 两个医生同时请假**：值班表要求「至少一人值班」。A 医生看还有 B 在，就请假了；B 医生看还有 A 在，也请假了。两人各改各的行（无写写冲突），结果没人值班。

## 5. 原理与推导

> **以下为通用知识整理，非依据 project4 官方页面。** 讲义依据见 [[15-445-18-Concurrency-Control-Theory]]、[[15-445-19-Two-Phase-Locking]]、[[15-445-20-Timestamp-Ordering]]、[[15-445-21-MVCC]]。具体任务拆解需以官方页面为准。

### 5.1 锁管理器的实现要点

**加锁流程（`LockExclusive`）**：

```
1. 拿 lock_table_latch_（保护 lock_table_ 的闩锁）
2. 找到/创建 rid 对应的 LockRequestQueue
3. 把请求加入队列（granted = false）
4. 检查能否授予：
   - 队列为空 → 授予
   - 队首是同一个事务的升级请求 → 处理升级
   - 相容性检查：与所有已授予的锁相容 → 授予
5. 若不能授予 → 释放 latch，在 cv 上等待（释放 CPU）
6. 被唤醒后重新检查（循环）
7. 授予后释放 latch，返回
```

**关键细节**：

1. **latch 的粒度**：`lock_table_latch_` 保护的是**锁表本身**（哈希表结构），不是数据。持有它时不能阻塞（否则其他事务连加锁都进不来）。
2. **等待时必须释放 latch**：`cv.wait(lock, predicate)` 会自动释放底层 mutex，被唤醒时重新获取。
3. **唤醒策略**：一个事务释放 X 锁后，可能要唤醒多个等待 S 锁的事务（它们互相相容）。
4. **公平性**：FIFO 队列防止饿死。但**升级请求要特殊处理**——若队首是升级请求，后面的 S 请求必须等（否则升级永远等不到所有 S 释放）。
5. **避免死锁的加锁顺序**：若上层（如 B+ 树、表堆）有固定的加锁顺序，锁管理器本身不需要预防死锁，只需检测。

**常见坑**：

- **忘记在 `Unlock` 时唤醒**：等待的事务永远阻塞。
- **`cv.notify_all()` vs `notify_one()`**：释放 S 锁时若队列里还有 S 请求，`notify_all` 更安全。
- **升级死锁**：T1 持 S 等升级，T2 持 S 等升级 → 双方都等对方释放。解决：**同一时刻只允许一个升级请求**（用 `upgrading` 标志）。
- **锁表内存泄漏**：`Unlock` 后若队列为空，应从 `lock_table_` 中删除该 RID 的条目。

### 5.2 严格 2PL 的实现

**最简单的方式**：事务**从不主动 `Unlock`**，所有锁在 `Commit` / `Abort` 时统一释放。

```cpp
void TransactionManager::Commit(Transaction *txn) {
  // 1. 标记提交
  txn->SetState(TransactionState::COMMITTED);
  // 2. 分配提交时间戳（MVCC 需要）
  txn->SetCommitTs(next_timestamp_++);
  // 3. 释放所有锁
  auto lock_set = txn->GetSharedLockSet();
  for (auto &rid : lock_set) lock_manager_->Unlock(txn, rid);
  auto x_lock_set = txn->GetExclusiveLockSet();
  for (auto &rid : x_lock_set) lock_manager_->Unlock(txn, rid);
  // 4. 清理
}
```

**为什么严格 2PL 保证可恢复性**：因为 X 锁持有到提交，任何读该数据的事务都必须等 `Ti` 提交后才能读到——所以不会读到未提交的数据（无脏读），也就不会出现「读了脏数据后写者回滚」的级联问题。

**为什么严格 2PL 仍可能死锁**：锁持有时间变长 → 等待链更长 → 死锁概率上升。所以**死锁检测是必需的**，不是可选的。

### 5.3 死锁检测的实现

**waits-for graph 的维护**：

- 每次事务阻塞时，加边 `Ti → Tj`（`Tj` 持有 `Ti` 需要的锁）。
- 每次授予锁时，删边。

**环检测**：DFS 或拓扑排序，`O(V + E)`。

```cpp
bool HasCycle(txn_id_t *victim) {
  // DFS，记录访问状态：0=未访问，1=在栈中，2=已完成
  std::unordered_map<txn_id_t, int> state;
  for (auto &[tid, _] : waits_for_) {
    if (state[tid] == 0) {
      if (DFS(tid, &state, victim)) return true;
    }
  }
  return false;
}
```

**检测频率的权衡**：

- **太频繁**：CPU 开销大。
- **太稀疏**：死锁持续很久才被发现，事务等待时间长。
- **折中**：每 50–1000 ms 一次（PostgreSQL 默认 `deadlock_timeout = 1s`）。

**另一种做法：超时（timeout）**：

- 事务等待超过 N 秒 → 直接中止。
- 简单但粗暴：可能误杀（只是慢，不是死锁）。
- 实践中常与检测结合：先等 `deadlock_timeout`，超时后再跑检测。

**受害者选择**：

```cpp
txn_id_t PickVictim(const std::vector<txn_id_t> &cycle) {
  // 启发式：选「已写入最少」的事务（回滚代价小）
  txn_id_t victim = cycle[0];
  size_t min_write = SIZE_MAX;
  for (auto tid : cycle) {
    size_t w = txn_map_[tid].GetWriteSet().size();
    if (w < min_write) { min_write = w; victim = tid; }
  }
  return victim;
}
```

**回滚的实现**：

- **完全回滚**：撤销事务的所有写操作（需要 undo log 或版本链）。
- **部分回滚**：回滚到 savepoint（需要记录 savepoint 的 LSN）。

> 待核实：BusTub 的 P4 是否要求实现死锁检测（还是只要求锁管理器 + 超时）；是否要求 `LockUpgrade`；是否要求多粒度锁（IS/IX/SIX）。

### 5.4 时间戳排序的实现

**每个数据项维护两个时间戳**：

- `R-TS(X)`：最后一个读 `X` 的事务的时间戳。
- `W-TS(X)`：最后一个写 `X` 的事务的时间戳。

**Basic T/O 的读**：

```
Read(X):
    if TS(Ti) < W-TS(X):
        Abort(Ti)                       # 读到了「未来」的写
    else:
        R-TS(X) = max(R-TS(X), TS(Ti))
        return X
```

**Basic T/O 的写**：

```
Write(X):
    if TS(Ti) < R-TS(X) or TS(Ti) < W-TS(X):
        Abort(Ti)                       # 有更晚的事务已经读过/写过
    else:
        W-TS(X) = TS(Ti)
        X = new_value
```

**为什么 Basic T/O 无死锁**：**从不阻塞**——冲突时直接中止，不等待。所以不会形成等待环。

**为什么 Basic T/O 可能饿死（starvation）**：一个短事务反复被中止（因为它总遇到时间戳更晚的已提交事务）→ 永远无法完成。**解决**：事务重启动时**保留原始时间戳**（不重新分配），最终会成为最老的事务而成功。

**Thomas Write Rule**：

```
Write(X):
    if TS(Ti) < W-TS(X):
        ignore this write                # 而不是 Abort
    elif TS(Ti) < R-TS(X):
        Abort(Ti)
    else:
        W-TS(X) = TS(Ti); X = new_value
```

**为什么 Thomas Write Rule 产生视图可串行化而非冲突可串行化**：它丢弃了一个「过时的写」（被更晚的写覆盖了），这个丢弃不改变最终结果，但确实消除了一个冲突操作——所以冲突等价性不成立，但视图等价性成立。

**OCC 的实现**：

```
ReadPhase(Ti):
    读取所有需要的数据到私有工作区
    记录 read_set 和 write_set

ValidationPhase(Ti):
    for each Tj with TS(Tj) < TS(Ti) and Tj committed:
        if Tj.write_set ∩ Ti.read_set ≠ ∅ and Tj.finish > Ti.start:
            Abort(Ti)
        if Tj.write_set ∩ Ti.write_set ≠ ∅ and Tj.finish > Ti.start:
            Abort(Ti)

WritePhase(Ti):
    应用 write_set 到数据库（需加锁或用原子操作）
```

**OCC 的适用场景**：**冲突少**（读多写少）的工作负载。冲突多时，验证失败率高 → 大量重试 → 性能比 2PL 差。

### 5.5 MVCC 的实现

**版本链结构**：

```cpp
struct UndoLog {
  // 旧版本的内容
  Tuple tuple;
  // 版本的时间范围
  timestamp_t begin_ts;      // 创建该版本的事务的提交时间戳
  timestamp_t end_ts;        // 删除该版本的事务的提交时间戳
  // 链指针
  std::shared_ptr<UndoLog> prev_version;
};
```

**两种实现策略**：

**策略 A：Delta / Undo（InnoDB 风格）**

- 主记录存**最新版本**（在表堆里）。
- 旧版本存在 **undo log** 中，通过 `roll_ptr` 链接。
- 读旧版本时，从主记录沿 `roll_ptr` 链回溯，直到找到可见版本。
- **优点**：主记录紧凑，表堆不膨胀。
- **缺点**：读旧版本要遍历链（可能很长）。

**策略 B：Append-only（PostgreSQL 风格）**

- 每次更新**插入一个新元组**（新版本），旧元组标记为「已删除」。
- 版本链通过 `ctid`（物理位置）链接，或用索引指向多个版本。
- **优点**：读旧版本快（直接读页）。
- **缺点**：表膨胀（需要 VACUUM 回收）。

**可见性判定的实现**：

```cpp
bool IsVisible(const UndoLog *version, timestamp_t read_ts) const {
  return version->begin_ts <= read_ts && read_ts < version->end_ts;
}

Tuple GetVisibleVersion(RID rid, timestamp_t read_ts) {
  auto version = GetVersionChain(rid);
  while (version != nullptr) {
    if (IsVisible(version, read_ts)) return version->tuple;
    version = version->prev_version;
  }
  return NOT_FOUND;
}
```

**事务快照**：

- **READ COMMITTED**：每条语句开始时取 `read_ts = next_timestamp_`。
- **REPEATABLE READ / SI**：事务 `Begin` 时取一次 `read_ts`，整个事务用这个值。

**写冲突处理（first-updater-wins vs first-committer-wins）**：

- **first-updater-wins（悲观）**：写时立即加锁（或用 CAS），若版本已被更新的写覆盖 → 等待或中止。
- **first-committer-wins（乐观，SI 标准）**：写时创建新版本，提交时检查「我读的快照之后有没有人提交了对同一行的写」→ 有则中止。

**为什么 SI 能防「不可重复读」**：因为整个事务用同一个 `read_ts`，读到的是同一个快照。

**为什么 SI 不能防「写偏斜」**：

```
初始：x = 100, y = 100，约束 x + y >= 0
T1: read(x)=100; read(y)=100; write(x = -50)   -- 认为 y 还是 100，可以取
T2: read(x)=100; read(y)=100; write(y = -50)   -- 认为 x 还是 100，可以取
```

- 两个事务读的是同一快照（都看到 100, 100）。
- 它们写的是**不同的行**（T1 写 x，T2 写 y）→ **无写写冲突** → 都能提交。
- 结果：`x + y = -100`，违反约束。

**形式化**：写偏斜需要一个 **R-W 环（read-write cycle）**：`T1 --rw--> T2 --rw--> T1`（T1 读了 T2 写的，T2 读了 T1 写的）。SI 只检测 **W-W 冲突**，检测不到 R-W 环。

**解决方案**：**SSI（Serializable Snapshot Isolation）**——额外跟踪 R-W 依赖，检测「危险结构」（两个连续的 rw 依赖），主动中止其中一个事务。PostgreSQL 9.1+ 实现了 SSI。

**垃圾回收（GC / VACUUM）**：

- 旧版本何时可以删除？当**没有活跃事务**需要它时。
- **watermark（低水位）**：所有活跃事务中 `read_ts` 的最小值。版本 `end_ts < watermark` 且无活跃事务可见 → 可回收。
- **长事务阻塞 GC**：一个跑了 1 小时的事务会阻止回收 1 小时内的所有旧版本 → 表膨胀。这是 PostgreSQL 运维的经典问题。

**索引与 MVCC 的交互**：

- 索引项指向**物理位置**（RID）或**逻辑主键**。
- 若索引指向旧版本（已被覆盖）→ 需要「索引可见性检查」：读索引项后，检查该版本对当前事务是否可见，不可见则沿链找。
- PostgreSQL 用 **visibility map** 加速：页级标记「所有元组对所有事务可见」→ 跳过可见性检查。

> 待核实：BusTub 的 P4 采用哪种版本链布局（delta 还是 append-only）；是否要求实现 `VACUUM` / GC；是否要求 SSI；事务隔离级别是否可配置。

### 5.6 事务管理器的实现

**核心状态**：

```cpp
enum class TransactionState { RUNNING, COMMITTED, ABORTED };

class Transaction {
  txn_id_t txn_id_;
  TransactionState state_;
  timestamp_t read_ts_;        // 快照时间戳
  timestamp_t commit_ts_;
  IsolationLevel isolation_level_;
  std::unordered_set<RID> shared_lock_set_;
  std::unordered_set<RID> exclusive_lock_set_;
  std::shared_ptr<Page> ...    // 写集合（用于回滚）
};
```

**`Begin`**：

```cpp
Transaction *TransactionManager::Begin(IsolationLevel level) {
  auto txn = new Transaction(next_txn_id_++, level);
  txn->SetReadTs(next_timestamp_++);      // 取快照
  txn_map_[txn->GetTransactionId()] = txn;
  return txn;
}
```

**`Commit` / `Abort`**：见 5.2 节。

**并发安全**：

- `txn_map_` 本身需要 latch 保护（`std::shared_mutex`）。
- `next_txn_id_` / `next_timestamp_` 用 `std::atomic`。
- **不要持锁调用用户回调**（避免死锁）。

**`Abort` 的回滚**：

- 若有 undo log：逆序应用 undo 记录。
- 若用版本链：把本事务创建的版本的 `begin_ts` 置为「无效」（或用 `end_ts` 标记为已删除）。
- 释放所有锁。
- 若支持恢复：写 abort 日志。

> 待核实：BusTub 的 P4 的事务状态机具体状态（是否含 `TAINTED`、`COMMITTING` 等）；`Abort` 的回滚是否要求写 CLR。

### 5.7 锁（Lock）与闩锁（Latch）的区别

这是 P4 最容易混淆的一点：

| 维度 | Lock（锁） | Latch（闩锁） |
|---|---|---|
| **保护对象** | 数据库的逻辑内容（行、表） | 内存数据结构（哈希表、B+ 树节点） |
| **生命周期** | 整个事务 | 单个操作（短） |
| **实现** | 锁管理器（哈希表 + 等待队列） | `std::mutex` / `std::shared_mutex` |
| **模式** | S / X / IS / IX / SIX | READ / WRITE |
| **死锁处理** | 检测 + 回滚 | 靠代码纪律（固定加锁顺序） |
| **回滚** | 需要（事务回滚） | 不需要（不会「回滚」） |
| **可见性** | 用户可见（`LOCK TABLE`） | 用户不可见（内部实现） |

**在 P4 中的分工**：

- 事务层用 **lock**（`LockManager`）。
- 锁管理器内部、事务表、版本链用 **latch**（`std::mutex`）。
- **不要把两者混用**：用 latch 保护锁表，用 lock 保护数据。

## 6. 代码示例

### 6.1 官方课程代码

本 vault **未抓取** Fall 2026 的 project4 官方页面，**无官方项目代码可引**。

可参考的讲义内容（伪代码/图示，非项目代码）：

- `17-concurrencycontrol.pdf`（49 页，L18 Concurrency Control Theory）：notes p4 Fig1 好交错 / Fig2 坏交错、p5 Fig3 依赖图。
- `18-twophaselocking.pdf`（158 页，L19 Two-Phase Locking，**notes 缺失**）：p9–14 与 p18–24 锁管理器的 Granted/Denied/Released 时序、p16–17 S/X 相容矩阵、p25–29 2PL 增长/收缩曲线、p40–43 级联回滚、p44 四类调度性质、p45 2PL 变体表、p99–104 死锁与 waits-for graph、p108–115 Wait-Die / Wound-Wait、p118–125 锁层次与 IS/IX/SIX。
- L20 Timestamp Ordering / L21 MVCC 的 2026 slides **尚未发布**，见 [[15-445-20-Timestamp-Ordering]]、[[15-445-21-MVCC]]。

> 待核实：project4 页面上的任务列表（是否分 checkpoint）、允许修改的文件、评分构成、是否要求死锁检测、是否要求 MVCC 的具体布局。

### 6.2 Agent 自行编写的教学示例

> 以下代码**非官方，仅用于说明概念**，不是 BusTub 的实现，也不构成项目答案。

**锁管理器的加锁骨架**：

```cpp
// 非官方示例：行级 X 锁的申请
bool LockManager::LockExclusive(Transaction *txn, const RID &rid) {
  std::unique_lock<std::mutex> table_lock(latch_);
  auto &queue = lock_table_[rid];           // 不存在则默认构造

  // 加入等待队列
  queue.request_queue.push_back({txn->GetTransactionId(), LockMode::EXCLUSIVE, false});
  auto it = std::prev(queue.request_queue.end());

  while (true) {
    // 检查：队列中所有已授予的请求是否都相容
    bool can_grant = true;
    for (auto req = queue.request_queue.begin(); req != queue.request_queue.end(); ++req) {
      if (!req->granted) continue;
      if (req->mode == LockMode::EXCLUSIVE) { can_grant = false; break; }
    }
    if (can_grant) {
      it->granted = true;
      txn->GetExclusiveLockSet()->insert(rid);
      return true;
    }
    // 不能授予 → 记 waits-for 边，然后等待
    queue.cv.wait(table_lock);
  }
}

// 非官方示例：释放锁
bool LockManager::Unlock(Transaction *txn, const RID &rid) {
  std::unique_lock<std::mutex> table_lock(latch_);
  auto map_it = lock_table_.find(rid);
  if (map_it == lock_table_.end()) return false;
  auto &queue = map_it->second;

  for (auto it = queue.request_queue.begin(); it != queue.request_queue.end(); ++it) {
    if (it->txn_id == txn->GetTransactionId() && it->granted) {
      queue.request_queue.erase(it);
      txn->GetExclusiveLockSet()->erase(rid);
      txn->GetSharedLockSet()->erase(rid);
      break;
    }
  }
  queue.cv.notify_all();                    // 唤醒所有等待者重新检查
  if (queue.request_queue.empty()) lock_table_.erase(map_it);
  return true;
}
```

**注意**：上面的实现**没有**正确处理「S 锁可以并发授予」与「升级请求的优先级」——真实实现需要更细的相容性判断。

**死锁检测骨架**：

```cpp
// 非官方示例：waits-for graph 的环检测
bool LockManager::HasCycle(txn_id_t *victim_id) {
  std::unordered_map<txn_id_t, int> color;      // 0=白 1=灰 2=黑
  std::function<bool(txn_id_t)> dfs = [&](txn_id_t u) -> bool {
    color[u] = 1;
    for (auto v : waits_for_[u]) {
      if (color[v] == 1) { *victim_id = v; return true; }   // 找到环
      if (color[v] == 0 && dfs(v)) return true;
    }
    color[u] = 2;
    return false;
  };
  for (auto &[tid, _] : waits_for_) {
    if (color[tid] == 0 && dfs(tid)) return true;
  }
  return false;
}
```

**MVCC 可见性判定**：

```cpp
// 非官方示例：从版本链中找可见版本
Tuple Meta::GetVisibleTuple(const RID &rid, timestamp_t read_ts) {
  auto version = version_chain_head_[rid];
  while (version != nullptr) {
    if (version->begin_ts <= read_ts && read_ts < version->end_ts) {
      return version->tuple;
    }
    version = version->prev;
  }
  throw std::runtime_error("no visible version");   // 不该发生
}
```

**事务状态机**：

```cpp
// 非官方示例：事务管理器的 Commit
void TransactionManager::Commit(Transaction *txn) {
  {
    std::unique_lock<std::shared_mutex> lock(txn_map_latch_);
    txn->SetState(TransactionState::COMMITTED);
    txn->SetCommitTs(next_timestamp_.fetch_add(1));
  }
  // 释放锁（严格 2PL）
  for (auto &rid : *txn->GetExclusiveLockSet()) lock_manager_->Unlock(txn, rid);
  for (auto &rid : *txn->GetSharedLockSet())    lock_manager_->Unlock(txn, rid);
  // 通知等待该事务的 MVCC 读者
  commit_cv_.notify_all();
}
```

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| Lock（锁） | Latch（闩锁） | 前者保护逻辑数据、生命周期是整个事务、可回滚；后者保护内存结构、生命周期是单次操作、不回滚 |
| 2PL | Strict 2PL | 前者只要求「先增后减」；后者要求 X 锁持有到事务结束（保证可恢复性） |
| Strict 2PL | Rigorous 2PL | 前者只约束 X 锁；后者 S 和 X 都持有到结束（实现更简单） |
| 死锁预防（prevention） | 死锁检测（detection） | 前者用 Wait-Die/Wound-Wait 从源头避免；后者允许发生再回滚 |
| Basic T/O | Thomas Write Rule | 前者冲突即中止；后者对「过时的写」直接忽略（视图可串行化） |
| 2PL | T/O | 前者**阻塞**（等待锁）；后者**中止**（不等待） |
| OCC | 2PL | 前者先做后验（冲突多时性能差）；后者先锁后做（冲突多时阻塞多） |
| SI（快照隔离） | 可串行化 | 前者只防 W-W 冲突；后者还防 R-W 环（写偏斜） |
| MVCC | 2PL | 前者读写不阻塞（多版本）；后者读写互相阻塞（单版本 + 锁） |
| first-updater-wins | first-committer-wins | 前者写时就抢锁；后者提交时才检查冲突 |
| 脏读 | 不可重复读 | 前者读到未提交数据；后者同一事务两次读同一行结果不同 |
| 写偏斜 | 幻读 | 前者是「读-写」依赖环；后者是「同一查询返回的行集变化」 |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Slides（L18 Concurrency Control Theory） | `90-原始PDF/15-445/slides/17-concurrencycontrol.pdf` | 49 | 事务定义、ACID、冲突与可串行化、优先图 |
| Notes（L18） | `90-原始PDF/15-445/notes/17-concurrencycontrol.pdf` | 5 | p4 Fig1 好交错 / Fig2 坏交错、p5 Fig3 依赖图 |
| Slides（L19 Two-Phase Locking） | `90-原始PDF/15-445/slides/18-twophaselocking.pdf` | 158 | p7–8 Locks vs Latches、p16–17 相容矩阵、p25–29 2PL 曲线、p40–43 级联回滚、p44 调度性质、p45 2PL 变体、p99–104 死锁与 waits-for、p108–115 Wait-Die/Wound-Wait、p118–125 锁层次 IS/IX/SIX |
| Notes（L19） | **缺失** | — | 官网无 `18-twophaselocking` 的 notes |
| Slides（L20 Timestamp Ordering） | **尚未发布** | — | — |
| Slides（L21 MVCC） | **尚未发布** | — | — |
| Project #4 官方页面 | **未抓取** | — | — |

原始 URL：

- `https://15445.courses.cs.cmu.edu/fall2026/slides/17-concurrencycontrol.pdf`
- `https://15445.courses.cs.cmu.edu/fall2026/notes/17-concurrencycontrol.pdf`
- `https://15445.courses.cs.cmu.edu/fall2026/slides/18-twophaselocking.pdf`
- 项目页面：`https://15445.courses.cs.cmu.edu/fall2026/project4/`（**待人工访问核对**）

> 待核实：`18-twophaselocking` 的 notes 是否会在学期中补发；L20/L21 的 slides 发布后的文件名（按 2025 年错位规律推断为 `19-timestampordering.pdf`、`20-mvcc.pdf`，本地 `_scout` 未确认）；project4 的任务拆解与评分构成。

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内，本讲内容对应 2025 年第 17–20 讲）

- 标题：Concurrency Control Theory（2025 第 17 讲）
  - URL：`https://www.youtube.com/watch?v=tMFAgvDViAI&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 标题：Two-Phase Locking（2025 第 18 讲）
  - URL：`https://www.youtube.com/watch?v=drStlhNbfHI&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 标题：Timestamp Ordering（2025 第 19 讲）
  - URL：`https://www.youtube.com/watch?v=risHwKeWbBM&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 标题：Multi-Version Concurrency Control（2025 第 20 讲）
  - URL：`https://www.youtube.com/watch?v=tUFha9-DuSk&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 年份：2025
- 时间戳：未核实，故不标注。

说明：FAQ Q11 明确 Fall 2026 的录像只对 CMU 学生开放，非 CMU 学习者应观看 Fall 2025 的公开视频。项目 #4 覆盖的正是这四讲的内容，建议按顺序看完再动手。

## 10. 本节复习

- 能写出锁管理器的核心数据结构（`LockRequestQueue` + `lock_table_`）与加锁流程。
- 能说明 S/X 相容性矩阵，以及为什么 S 锁可以并发授予。
- 能区分 2PL / Strict 2PL / Rigorous 2PL 的锁释放时机。
- 能画出 waits-for graph 并检测环，说明受害者选择的启发式。
- 能写出 Basic T/O 的读写规则，说明为什么它无死锁但可能饿死。
- 能说明 Thomas Write Rule 为什么产生视图可串行化而非冲突可串行化。
- 能实现 MVCC 的可见性判定，说明 SI 为什么防不了写偏斜。
- 能区分 lock 与 latch，说明它们在 P4 中各自的职责。
- 能说出 `Commit` 与 `Abort` 各自要做哪几件事。

## 11. 自我检查

**Q1.** 为什么严格 2PL 能保证可恢复性（recoverability），而基本 2PL 不能？

<details><summary>参考答案</summary>

**因为严格 2PL 要求 X 锁持有到事务结束，所以任何事务都读不到未提交的写。**

**基本 2PL 的反例**：

```
T1: Write(X)          -- T1 修改 X，持 X 锁
T1: Unlock(X)         -- 进入收缩阶段，释放 X 锁
T2: Read(X)           -- T2 读到 T1 未提交的 X（脏读）
T1: Abort             -- T1 回滚，X 恢复旧值
T2: Commit            -- T2 基于脏数据提交
```

**问题**：`T2` 读了 `T1` 未提交的数据，`T1` 回滚后 `T2` 的数据就是错的，但 `T2` 已经提交——**不可恢复（non-recoverable）**。若要修正，必须**级联回滚（cascading abort）** `T2`，而 `T2` 可能已经被别的事务读过……连锁反应。

**严格 2PL 的保证**：

- `T1` 的 X 锁持有到 `Commit` / `Abort`。
- `T2` 想读 `X` 必须等 `T1` 结束。
- 若 `T1` 提交 → `T2` 读到的是已提交数据，安全。
- 若 `T1` 回滚 → `T2` 读到的是旧值（`T1` 的修改已撤销），安全。

**形式化**：可恢复性要求「若 `Tj` 读了 `Ti` 写的数据，则 `Ti` 必须先于 `Tj` 提交」。严格 2PL 下，`Tj` 读 `X` 时必须等 `Ti` 释放 X 锁，而 `Ti` 只在提交/回滚时释放 → `Ti` 的提交一定在 `Tj` 的读之前 → 满足可恢复性。

**更强：无级联回滚（ACA, Avoid Cascading Abort）**：

- 要求「只读已提交的数据」。
- 严格 2PL 满足 ACA（因为 X 锁持有到结束，读者只能读到提交后的值）。

**Rigorous 2PL 的额外好处**：

- S 锁也持有到结束 → 事务的**读集合**也固定 → 串行化顺序 = 提交顺序。
- 实现简单：`Unlock` 只在事务结束时批量调用，不需要跟踪「何时进入收缩阶段」。

**代价**：锁持有时间最长 → 并发度最低 → 死锁概率最高。所以严格 2PL 必须配死锁检测。

</details>

**Q2.** MVCC 下「读写不阻塞」，为什么还会需要锁？读操作真的完全不加锁吗？

<details><summary>参考答案</summary>

**MVCC 消除了「读等写」和「写等读」，但没有消除「写等写」。**

**具体分析**：

1. **读不阻塞写**：读者读旧版本（快照），写者创建新版本，互不干扰 → 读不需要等写的锁。
2. **写不阻塞读**：写者创建新版本，读者仍读旧版本 → 写不需要等读者的锁。
3. **写仍然阻塞写**：两个事务写同一行时，必须决定谁赢。
   - **first-updater-wins（悲观）**：写时对行加 X 锁（或 CAS），后到者等待/中止。
   - **first-committer-wins（乐观）**：写时创建版本，提交时检查冲突，冲突则中止。
   - 两种方式都需要某种同步原语（锁、latch、原子 CAS）。

**所以 MVCC 下仍然需要的锁/latch**：

| 场景 | 需要什么 |
|---|---|
| 两个事务写同一行 | 行级 X 锁（first-updater-wins）或提交时验证（first-committer-wins） |
| 更新版本链指针 | latch（保护版本链的 `prev` 指针，防止并发修改破坏链表） |
| 分配事务 ID / 时间戳 | 原子操作 |
| 插入新行（防止幻读） | **间隙锁（gap lock）** 或 **谓词锁（predicate lock）** 或 SSI |
| 索引并发修改 | B+ 树的 latch crabbing |
| 表结构变更（DDL） | 表级锁 |

**读操作并非完全无锁**：

1. **需要 latch 保护版本链**：读版本链时，若同时有写者在链头插入新版本，读者可能看到不一致的链。解决：
   - 用 latch（短持有，只保护指针读取）。
   - 或用**无锁数据结构**（原子指针 + hazard pointer / epoch-based reclamation）。
2. **需要检查事务状态**：判断版本是否可见时，要读事务表的提交状态 → 需要同步（通常用原子变量或无锁读）。
3. **索引可见性检查**：索引项可能指向已不可见的版本，需要检查。

**MVCC 的「不阻塞」是相对的**：

- **相对 2PL**：确实大幅减少阻塞（读不再等写）。
- **绝对意义**：仍有短期的 latch（微秒级），以及写写冲突的等待/中止。

**PostgreSQL 的实现**：

- 读：只拿 buffer 的 pin + 短 latch，不加行锁。
- 写：加行级 X 锁（`tuple lock`），first-updater-wins。
- 串行化：用 SSI（`SERIALIZABLE` 级别下跟踪 rw 依赖）。

**InnoDB 的实现**：

- 读：一致性非锁定读（consistent nonlocking read），读 undo log 中的旧版本。
- 写：加行锁（record lock / gap lock / next-key lock），**默认 REPEATABLE READ 下用 next-key lock 防幻读**。

**一句话**：MVCC 把「读-写冲突」从**阻塞**变成**多版本共存**，但「写-写冲突」和「内存数据结构的并发」仍然需要锁。

</details>

**Q3.** 快照隔离（SI）为什么防不了写偏斜？SSI 如何检测它？

<details><summary>参考答案</summary>

**因为 SI 只检测「写-写冲突」，而写偏斜只产生「读-写冲突」。**

**写偏斜的经典例子（医生值班）**：

```
约束：值班医生数 >= 1
初始：Alice 值班, Bob 值班

T1: SELECT COUNT(*) FROM oncall WHERE shift='A'   -- 看到 Alice 和 Bob，共 2 人
T1: DELETE FROM oncall WHERE name='Alice'          -- 认为还有 Bob，可以删

T2: SELECT COUNT(*) FROM oncall WHERE shift='A'   -- 看到 Alice 和 Bob，共 2 人
T2: DELETE FROM oncall WHERE name='Bob'            -- 认为还有 Alice，可以删

结果：0 人值班，违反约束
```

**SI 为什么放行**：

- `T1` 和 `T2` 读的是同一快照（都看到 2 人）。
- `T1` 删 Alice，`T2` 删 Bob——**写的是不同的行**。
- SI 的 first-committer-wins 只检查「有没有别人提交了对**同一行**的写」→ 无冲突 → 都提交。

**形式化：R-W 环（read-write cycle）**

定义依赖边：

- `Ti --ww--> Tj`：`Ti` 写了 `X`，`Tj` 之后写了 `X`（写写冲突）。
- `Ti --wr--> Tj`：`Ti` 写了 `X`，`Tj` 读了 `X`（写读依赖）。
- `Ti --rw--> Tj`：`Ti` 读了 `X`，`Tj` 之后写了 `X`（**读写反依赖，anti-dependency**）。

上例中：

- `T1` 读了「Bob 值班」这个事实，`T2` 删了 Bob → `T1 --rw--> T2`。
- `T2` 读了「Alice 值班」，`T1` 删了 Alice → `T2 --rw--> T1`。
- 形成 **`T1 --rw--> T2 --rw--> T1`** 的环。

**SI 只检测 ww 边**（first-committer-wins），检测不到 rw 环 → 允许了不可串行化的调度。

**SSI（Serializable Snapshot Isolation）如何检测**：

**核心思想**：跟踪所有 rw 反依赖，检测「**危险结构（dangerous structure）**」——两个连续的 rw 边：`Ti --rw--> Tj --rw--> Tk`。

**Cahill 等人的定理（SIGMOD 2008）**：在 SI 下，若存在 `Ti --rw--> Tj --rw--> Tk` 且 `Tk` 先于 `Ti` 提交，则调度不可串行化。

**实现**：

1. 每个事务维护 `inConflict` / `outConflict` 标志。
2. 读时记录「我读的版本是被谁写的」（若该版本已被覆盖，说明有人在我读之后写了它 → 记 rw 边）。
3. 提交时检查：若 `Tj` 有 `inConflict` 和 `outConflict`（即它是危险结构的中间节点），则中止其中一个。

**Ports & Grittner（VLDB 2012）的改进**：PostgreSQL 的实现，用更精确的规则减少误判（`SAFE` 快照、只读事务优化）。

**代价**：

- 额外的内存（跟踪读写集合）。
- 额外的 CPU（检查依赖）。
- **误判（false positive）**：会中止一些其实可串行化的事务 → 吞吐下降。
- PostgreSQL 的经验：SSI 的吞吐约为 SI 的 60–80%。

**其他解决方案**：

1. **物化冲突（materialize conflicts）**：把「约束」变成一个真实的行，让两个事务去写同一行 → 产生 ww 冲突 → SI 就能检测到。例如「值班表」加一行「当前值班人数」，两个事务都要更新它。
2. **显式加锁**：`SELECT ... FOR UPDATE` 读时加锁。
3. **可串行化 2PL**：直接用严格 2PL。

</details>

**Q4.** 为什么 Basic T/O 不会死锁，但会「饿死」？如何解决饿死？

<details><summary>参考答案</summary>

**不会死锁，因为 T/O 从不等待——冲突时直接中止。**

**死锁的必要条件**：存在循环等待。T/O 的规则是「冲突 → `Abort`」，事务**从不阻塞**，所以不可能形成等待环。

**对比 2PL**：2PL 冲突时**等待**锁释放 → 可能形成 `T1` 等 `T2`、`T2` 等 `T1` 的环。

**为什么会饿死（starvation）**：

考虑一个「老」事务 `T_old`（时间戳小）和一个不断到来的「新」事务流：

```
T_old: 读 X
T_new1: 写 X（时间戳更大，成功，W-TS(X) = TS(T_new1)）
T_old: 想读 X → TS(T_old) < W-TS(X) → Abort，重来
T_old 重启（若重新分配时间戳，变成更新的时间戳……）
```

**关键**：如果重启时**重新分配时间戳**，`T_old` 会变成「新事务」，但它需要的数据可能又被更新的写覆盖 → 永远被中止。

**更糟的情况**：`T_old` 是一个长事务（读很多数据），每次快完成时遇到一个新写 → 中止 → 重来 → 又遇到新写……**无限循环**。

**解决方案 1：重启时保留原始时间戳**

- 事务 `Abort` 后重启动，**不重新分配时间戳**，仍用原来的（小的）时间戳。
- 这样它始终是「最老」的事务之一。
- 但仍有问题：只要还有比它更老的事务在写它需要的数据，它就会被中止。不过**新事务的时间戳总是更大**，所以随着时间推移，`T_old` 最终会成为最小的 → 新事务不能覆盖它读的数据（因为新事务时间戳更大，写规则允许）……

**等等**，这里要仔细：`T_old` 时间戳小，新事务时间戳大。新事务写 `X` 时，规则是 `TS(T_new) < R-TS(X)` 或 `< W-TS(X)` 才中止。因为 `T_new` 更大，所以新事务**不会**因为 `T_old` 的读而中止——新事务成功写 `X`。然后 `T_old` 再读 `X` 就发现 `TS(T_old) < W-TS(X)` → 中止。

所以**保留时间戳并不能完全解决饿死**！`T_old` 还是会反复被中止。

**真正的解决方案**：

1. **保留时间戳 + 优先级**：当 `T_old` 想读被 `T_new` 写过的数据时，**中止 `T_new`** 而不是 `T_old`（因为 `T_old` 更老、优先级更高）。这实际上变成了 **Wait-Die / Wound-Wait** 的思路（但它们基于锁）。
2. **混合方案**：T/O + 有限等待。当 `T_old` 冲突时，让它**等待**而不是立即中止（给新事务一个完成的机会，但不无限等）。
3. **限制并发度**：控制活跃事务数量，减少冲突概率。
4. **多版本（MVCC）**：`T_old` 读旧版本，不冲突 → 根本不会中止。**这是最根本的解法**——MVCC 本质上就是「用空间换时间戳冲突」。

**为什么现代数据库不用纯 T/O**：

- 饿死问题难解决（需要额外的优先级机制）。
- 冲突多时中止率高（重试成本高）。
- MVCC 能提供更好的读性能（读不冲突）。

**但 T/O 的思想仍然重要**：

- **MVCC 的可见性判定**本质上是时间戳比较。
- **OCC**（乐观并发控制）是 T/O 的变体（验证阶段用时间戳）。
- **分布式数据库**（如 Spanner）用**全局时间戳**（TrueTime）做 MVCC。

**一句话**：T/O 用「中止」换「无死锁」，代价是「可能饿死」；MVCC 用「多版本」同时换掉了死锁和饿死。

</details>

## 12. 进一步学习

- 项目导航：[[00-项目总览]]
- 上一个项目：`03-Project3-Query-Execution.md`
- 相关讲义：[[15-445-18-Concurrency-Control-Theory]]（ACID、冲突、可串行化）、[[15-445-19-Two-Phase-Locking]]（2PL、死锁、锁层次）、[[15-445-20-Timestamp-Ordering]]（T/O、OCC）、[[15-445-21-MVCC]]（版本链、SI、写偏斜）、[[15-445-22-Database-Logging]]（WAL、LSN，与 `Abort` 回滚相关）、[[15-445-23-Database-Recovery]]（ARIES，与事务回滚相关）
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：
  - Bernstein & Goodman, "Concurrency Control in Distributed Database Systems"（ACM Computing Surveys, 1981）——并发控制的经典综述。
  - Berenson et al., "A Critique of ANSI SQL Isolation Levels"（SIGMOD 1995）——**隔离级别批判的经典论文**，首次提出「写偏斜」。
  - Cahill, Röhm, Fekete, "Serializable Isolation for Snapshot Databases"（SIGMOD 2008）——SSI 的原始论文。
  - Ports & Grittner, "Serializable Snapshot Isolation in PostgreSQL"（VLDB 2012）——工业实现。
  - Kung & Robinson, "On Optimistic Methods for Concurrency Control"（ACM TODS, 1981）——OCC 的原始论文。
  - Gray et al., "Granularity of Locks and Degrees of Consistency in a Shared Data Base"（1976）——多粒度锁与意向锁的经典。
  - 教材 *Database System Concepts*（7th Ed.）第 17–18 章（Concurrency Control、Recovery System）。
  - BusTub 仓库 `src/include/concurrency/` 下的 `transaction.h`、`transaction_manager.h`、`lock_manager.h`、`watermark.h`。
- 动手建议：先实现 `LockManager` 的 S/X 锁与相容性判断，跑通 `lock_manager_test`；再加死锁检测；再实现 `TransactionManager` 的 `Begin`/`Commit`/`Abort`；最后做 MVCC 的版本链与可见性判定。**每步都跑测试再往下走**，并发 bug 极难调试。
- 调试建议：
  - 用 `-fsanitize=thread`（TSan）检测数据竞争。
  - 用 `-fsanitize=address`（ASan）检测内存错误（版本链的悬垂指针）。
  - 死锁时用 `gdb` attach 看所有线程的栈（`thread apply all bt`）。
  - 在锁管理器里打日志（`LOG_DEBUG`），记录每次加锁/释放/等待，事后分析时序。
- **提醒**：本篇依据课程结构公开信息 + 通用知识整理，vault 未抓取 project4 官方页面。具体任务以官方 project4 页为准。`> 待核实：` 处需人工核对。
