---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: P1
topic: Project 1 - Buffer Pool Manager
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 项目
  - 缓冲池
  - LRU-K
  - 并发
---

# 15-445 Project #1：缓冲池管理器（Buffer Pool Manager）

> **重要边界说明**：本 vault **未抓取** Fall 2026 的 project1 官方页面，本篇内容为「课程结构公开信息 + 通用知识」整理，**所有具体规格细节标 `> 待核实：`**，不编造。
>
> 官方页面（待人工核对）：`https://15445.courses.cs.cmu.edu/fall2026/project1/`
>
> 本项目的主题与讲义 [[15-445-04-Memory-Management]] 直接对应。Fall 2026 课表把 Buffer Pool Manager 安排在第 03 周。
>
> **Fall 2026 政策提醒**：Project #1 与 #2 **禁止使用 coding agents**（官方主页原文 "P1-P2 prohibit coding agents"），且项目代码必须由你理解并拥有。

## 1. 本节学习目标

1. 说清**缓冲池（buffer pool）** 在数据库架构中的位置，以及它为什么不能用操作系统的页缓存代替。
2. 理解 **frame（帧）**、**page（页）**、**page table（页表）**、**pin count（钉住计数）**、**dirty flag（脏位）** 五个核心概念的关系。
3. 掌握 **LRU-K 替换策略**：K 距离的定义、历史队列与缓存队列的双队列结构、为什么 K=2 比 LRU 好。
4. 理解 **页守卫（Page Guard）** 的 RAII 设计：为什么用 guard 而不是手动 `UnpinPage`。
5. 理解**并发安全**的三个层次：page table 的 latch、frame 的 latch、以及「持锁顺序」如何避免死锁。
6. 掌握**磁盘调度器（disk scheduler）** 的角色与常见策略（FIFO、SSTF、Elevator/SCAN）。
7. 能写出一个正确的 `FetchPage` 流程（含淘汰、读盘、更新元数据）。

## 2. 前置知识

- **C++17**：`std::unique_ptr`、`std::shared_mutex`、`std::atomic`、`std::list`、`std::unordered_map`。见 `01-Project0-Cpp-Primer.md`。
- **操作系统内存管理**：虚拟内存、页表、TLB、页错误（page fault）、脏页回写。见 [[15-445-04-Memory-Management]]。
- **数据库存储层**：页布局、页 ID（`page_id_t`）、磁盘管理器（`DiskManager`）。见 [[15-445-03-Database-Storage-I]]、[[15-445-05-Database-Storage-II]]。
- **并发基础**：mutex、读写锁、条件变量、死锁四条件。
- 上一个项目：`01-Project0-Cpp-Primer.md`（P0 的分片锁思想在这里会用到）。

## 3. 核心概念

### 3.1 Buffer Pool（缓冲池）

数据库在内存中预留的一块**固定大小的区域**，用来缓存磁盘上的页。所有对页的读写都经过缓冲池，而不是直接访问磁盘。

**为什么不用 OS 页缓存**：

1. **无法控制替换策略**：OS 用 LRU，但数据库知道「这个页马上要被顺序扫描用到」，LRU 会把它淘汰。
2. **无法控制刷盘时机**：数据库需要保证 WAL 先于数据页落盘（write-ahead logging），OS 的刷盘时机不可控。
3. **无法做预取（prefetch）**：数据库知道查询计划，可以提前把页读进来；OS 不知道。
4. **无法保证正确性**：OS 可能在事务未提交时把脏页刷盘（虽然数据库用 undo 能处理，但控制权在数据库手里更好）。

### 3.2 Frame（帧）

缓冲池中的一个**槽位**，能容纳一个页。帧的数量固定（由构造参数 `pool_size` 决定）。每个帧包含：

- 页数据（`char data_[PAGE_SIZE]`）
- `page_id_t page_id_`（当前装的哪一页，无效时是 `INVALID_PAGE_ID`）
- `int pin_count_`（被钉住次数）
- `bool is_dirty_`（是否被修改过）
- 一个 latch（读写闩锁，保护页内容）

### 3.3 Page Table（页表）

从 `page_id_t` 到 `frame_id_t` 的映射。`FetchPage(pid)` 时先查页表：

- **命中（hit）**：直接返回对应帧，`pin_count++`。
- **未命中（miss）**：找一个空闲帧或淘汰一个帧，从磁盘读入，更新页表。

### 3.4 Pin Count（钉住计数）

表示「有多少个使用者正在使用这个页」。**`pin_count > 0` 的页不能被淘汰**——否则使用者手里的指针会失效。

**规则**：

- `FetchPage` 成功 → `pin_count++`
- `UnpinPage` → `pin_count--`
- 只有 `pin_count == 0` 的帧才能进入淘汰候选

**常见 bug**：忘记 unpin → 帧永久泄漏 → 缓冲池逐渐耗尽 → `FetchPage` 返回 `nullptr`。

### 3.5 Dirty Flag（脏位）

标记页自上次刷盘后是否被修改。淘汰脏页时必须**先写回磁盘**；淘汰干净页可以直接丢弃。

### 3.6 LRU-K Replacer（LRU-K 替换器）

LRU 的推广：用**最近第 K 次访问的时间**作为淘汰依据，而不是最近一次。K=2 时叫 **LRU-2**，实践中效果最好。

**为什么比 LRU 好**：LRU 会被**顺序扫描（sequential scan）** 污染——一次全表扫描把所有页都读进来，把真正热的数据挤出去。LRU-K 要求「至少访问 K 次」才算热，一次性的扫描页不会被提升。

### 3.7 Page Guard（页守卫）

RAII 封装：构造时 `FetchPage` + 加锁，析构时自动 `UnpinPage` + 解锁。防止忘记 unpin。

**三种 guard**（BusTub 的命名，待核实）：

- `ReadPageGuard`：读锁 + unpin
- `WritePageGuard`：写锁 + unpin + 标脏
- `BasicPageGuard`：只 unpin，不加锁

### 3.8 Disk Scheduler（磁盘调度器）

把「读/写页」的请求排队，按某种策略排序后交给磁盘。目的是**减少寻道时间**（机械盘）或**提高吞吐**（SSD）。

**常见策略**：

- **FIFO**：先来先服务，简单但可能饥饿。
- **SSTF（Shortest Seek Time First）**：优先服务最近的请求，可能饥饿远处请求。
- **Elevator / SCAN**：磁头单向扫，到端点反向，公平且高效。

### 3.9 Latch（闩锁）

保护内存数据结构的轻量同步原语。与事务的 lock 不同：latch **持有时间短**、**无死锁检测**、**不支持回滚**。

## 4. 通俗理解

**缓冲池 = 图书馆的阅览桌**：

- **磁盘** = 书库（容量大，取书慢）。
- **缓冲池** = 阅览桌（容量小，就在手边）。
- **frame** = 桌上的一个位置。
- **page** = 一本书。
- **pin count** = 「有几个人正在看这本书」。有人在看，管理员就不能把书收回书库。
- **dirty flag** = 「这本书被读者做了笔记」。收回时必须先更新书库的版本。
- **LRU-K** = 「至少被借过 2 次的书才值得留在桌上」。只被翻过一次的书（顺序扫描）不该占位置。

**页守卫 = 借书证**：你拿证借书（构造 guard），还书时自动注销（析构 guard）。如果你忘了还书，管理员会一直等着——这就是 pin count 泄漏。

**LRU vs LRU-K**：

- **LRU** = 「最近谁来过？」——一个只来一次的游客也会被记住。
- **LRU-K** = 「最近谁来过至少 K 次？」——游客不算，常客才算。

**磁盘调度 = 电梯**：电梯不会按「谁先按按钮」的顺序停，而是沿一个方向一路停过去，到顶再反向。这样总行程最短。

## 5. 原理与推导

> **以下为通用知识整理，非依据 2026 官方讲义。** 具体任务拆解与 API 需以官方 project1 页面为准。

### 5.1 缓冲池的整体结构

```
                 ┌─────────────────────────────────────┐
   SQL 层 ──────►│  BufferPoolManager                  │
                 │  ┌───────────────────────────────┐  │
                 │  │ page_table_: page_id → frame  │  │
                 │  └───────────────────────────────┘  │
                 │  ┌──────┬──────┬──────┬──────┐      │
                 │  │Frame0│Frame1│Frame2│ ...  │      │
                 │  │ data │ data │ data │      │      │
                 │  │ pid  │ pid  │ pid  │      │      │
                 │  │ pin  │ pin  │ pin  │      │      │
                 │  │dirty │dirty │dirty │      │      │
                 │  └──────┴──────┴──────┴──────┘      │
                 │  ┌───────────────────────────────┐  │
                 │  │ replacer_ (LRU-K)             │  │
                 │  └───────────────────────────────┘  │
                 └──────────────┬──────────────────────┘
                                │
                 ┌──────────────▼──────────────────────┐
                 │ DiskScheduler → DiskManager → 磁盘   │
                 └─────────────────────────────────────┘
```

### 5.2 `FetchPage` 的完整流程

```
FetchPage(pid):
  1. 锁 page_table_
  2. 若 pid 在 page_table_ 中:
        frame = page_table_[pid]
        frame.pin_count++
        frame.latch.lock()          # 页级闩锁
        解锁 page_table_
          → 返回 frame（调用者负责解锁 + unpin）
  3. 否则（miss）:
        frame_id = replacer_.Evict()       # 找一个可淘汰的帧
        若没有可淘汰的帧（全被 pin 住）:
            解锁 page_table_
            → 返回 nullptr
        若被淘汰的帧是脏的:
            把 frame.data_ 写回旧 pid（异步或同步）
        从 page_table_ 删除旧 pid 的映射
        frame.pin_count = 1
        frame.is_dirty = false
        从磁盘读 pid 的数据到 frame.data_
        page_table_[pid] = frame_id
        replacer_.RecordAccess(pid)
        解锁 page_table_
        → 返回 frame
```

**关键点**：

1. **`page_table_` 的锁粒度**：如果整个 `FetchPage` 都持 `page_table_` 的锁，那么并发度很低（所有 `FetchPage` 串行）。BusTub 的常见做法是**只在对 page table 读写时持锁**，读盘/写盘时释放。
2. **淘汰时不能持有 page table 锁做 I/O**：否则 I/O 期间所有 `FetchPage` 阻塞。正确做法是标记该帧为「正在淘汰」，释放锁，做 I/O，再回来更新。
3. **`nullptr` 语义**：所有帧都被 pin 住时，`FetchPage` 返回 `nullptr`。调用者必须处理。

### 5.3 LRU-K 的双队列结构

**K 距离（backward K-distance）**：`K-dist(p) = 当前时间 - 第 K 次最近访问的时间`。K-dist 越大 → 越久没被访问 K 次 → 越应该淘汰。

**双队列实现**（BusTub 的 `LRUKReplacer`）：

```
┌─────────────────────────────┐   ┌─────────────────────────────┐
│  历史队列（history list）    │   │  缓存队列（cache list）      │
│  访问次数 < K 的帧           │   │  访问次数 >= K 的帧          │
│  按「首次访问时间」淘汰       │   │  按「第 K 次访问时间」淘汰   │
└─────────────────────────────┘   └─────────────────────────────┘
```

**`RecordAccess(frame_id)` 的逻辑**：

```
若 frame 在 cache list:
    从 cache list 移除，按当前时间重新插入（更新 K-dist）
否则若 frame 在 history list:
    访问次数 + 1
    若 访问次数 == K:
        从 history list 移除，插入 cache list
否则:
    插入 history list，访问次数 = 1
```

**`Evict()` 的逻辑**（淘汰优先级）：

1. 先尝试从 **history list** 淘汰（这些是「还没证明自己热」的帧）。
2. 若 history 为空，从 **cache list** 淘汰「K-dist 最大」的帧。
3. 跳过 `pin_count > 0` 的帧和「不可淘汰（evictable=false）」的帧。

**为什么先淘汰 history**：history 里的帧只被访问过 1 次（K=2 时），是「一次性访问」的候选，优先淘汰它们能保护真正的热数据。

**复杂度**：需要 O(1) 的查找（`unordered_map<frame_id, Node>`）+ O(log n) 或 O(1) 的「找 K-dist 最大」。若用 `std::list` + 按时间排序插入，删除是 O(1)，但「找最大」需要遍历 → O(n)。实践中常用**有序结构**（如 `std::set` 按时间戳排序）或**惰性删除**（`std::list` + 定期清理）。

> 待核实：BusTub 的 `LRUKReplacer` 是否要求 `Evict` 为 O(1) 或有时间限制。官方页面未抓取，需查仓库头文件与测试。

### 5.4 LRU-K 为什么能抵抗顺序扫描

**场景**：缓冲池 10 帧，热数据 A、B、C 各被访问 100 次。然后一次全表扫描读入 D1…D100（每页只访问一次）。

**LRU 的行为**：D1…D100 依次进入，把 A、B、C 全部挤出。扫描结束后，A、B、C 的缓存全部失效 → 后续访问全部 miss。

**LRU-2 的行为**：D1…D100 只被访问一次，停留在 **history list**，不进入 cache list。淘汰时优先淘汰 history → A、B、C（在 cache list）被保护。扫描结束后，热数据仍在。

**这就是「扫描污染（scan pollution）」问题**，也是所有数据库不用纯 LRU 的原因。工业界的解法还有：

- **LRU-K**（本项目的方案）
- **2Q**（two-queue，类似思想）
- **ARC**（adaptive replacement cache，动态调整）
- **Clock / CLOCK-Pro**
- **分段 LRU**（MySQL InnoDB 的 young/old 分区）

### 5.5 页守卫与 RAII

**手动管理的痛点**：

```cpp
Page *p = bpm->FetchPage(pid);
// ... 一堆逻辑，中途可能 return / throw ...
bpm->UnpinPage(pid, is_dirty);   // 忘了就泄漏
```

**Guard 方案**：

```cpp
{
  auto guard = bpm->FetchPageRead(pid);   // 构造：fetch + 读锁
  auto data = guard.GetData();
  // ... 使用 ...
}   // 析构：解锁 + unpin，即使中途 throw 也保证执行
```

**移动语义**：guard 必须**可移动不可拷贝**（`unique_ptr` 式的所有权）。移动后源 guard 不再持有资源，析构时不做任何事（避免 double-unpin）。

**`Drop()` 方法**：某些实现允许提前释放（手动调用 `Drop()`），析构时检测是否已释放。

**为什么 guard 比手动 unpin 好**：

1. **异常安全**：`throw` 时自动 unpin。
2. **早退安全**：`return` 时自动 unpin。
3. **可读性**：作用域即生命周期，一眼看出页被持有多久。

### 5.6 并发安全的三层锁

| 层次 | 保护对象 | 锁类型 | 持有时间 |
|---|---|---|---|
| **page table 锁** | `page_table_` 映射、frame 元数据（pid、pin_count、dirty） | `std::mutex` 或 `std::shared_mutex` | 短（微秒级） |
| **frame 闩锁** | 页**内容**（`data_`） | `std::shared_mutex`（读写锁） | 长（整个使用期间） |
| **replacer 锁** | LRU-K 的内部结构 | `std::mutex` | 短 |

**持锁顺序（避免死锁）**：必须定义全局顺序，所有代码遵守。例如：

```
page_table_ 锁 → frame 闩锁 → replacer 锁
```

**反例（死锁）**：

- 线程 1：持 frame 0 的闩锁，等 page_table_ 锁。
- 线程 2：持 page_table_ 锁，等 frame 0 的闩锁。
- → 循环等待 → 死锁。

**BusTub 的常见设计**：`page_table_` 用 `std::shared_mutex`（读多写少），`FetchPage` 时先拿读锁查表，miss 时升级为写锁（或释放读锁再拿写锁，然后**双重检查**是否已被别人读入）。

**双重检查（double-checked locking）**：

```
1. 拿读锁，查表 → 命中，返回
2. 释放读锁，拿写锁
3. 再查一次表（可能别人已经读入了）→ 命中，返回
4. 仍未命中 → 淘汰 + 读盘 + 插入
```

第 3 步是必须的，否则两个线程会同时读入同一页，浪费 I/O 并可能覆盖。

### 5.7 磁盘调度器

**为什么需要**：`FetchPage` 的 miss 会触发读盘。如果多个线程同时 miss，会有多个读请求排队。调度器决定**按什么顺序**发给磁盘。

**FIFO**：简单，但一个慢请求会阻塞后面所有请求（ convoy effect）。

**SSTF**：优先服务离当前磁头最近的请求。问题：远处的请求可能永远得不到服务（饥饿）。

**Elevator / SCAN**：磁头从一端扫到另一端，沿途服务所有请求，到端点反向。**公平且总行程短**。

**SSD 时代的意义**：SSD 没有寻道时间，但有**队列深度**与**并行通道**。调度器的目标从「减少寻道」变成「最大化并行度 + 保证公平」。现代数据库多用 **multi-queue** 调度（如 Linux 的 `blk-mq`）。

**BusTub 的 `DiskScheduler`**：通常是一个**后台线程 + 请求队列**，把同步的 `DiskManager::ReadPage` 包装成异步的 `Schedule(DiskRequest)` + `future`。这样 `FetchPage` 不会阻塞在 I/O 上。

> 待核实：BusTub 的 `DiskScheduler` 在 Fall 2026 是否仍要求实现，以及是否要求特定的调度策略（FIFO 即可，还是要 SCAN）。官方页面未抓取。

### 5.8 常见的正确性不变式

实现缓冲池时，以下不变式**必须始终成立**（可用断言检查）：

1. 每个 `frame.pin_count >= 0`。
2. `page_table_[pid] == fid` **当且仅当** `frames_[fid].page_id_ == pid`（双向一致）。
3. 被 pin 的帧**不在** replacer 的可淘汰集合中（`evictable == false`）。
4. `pin_count == 0` 且 `evictable == true` 的帧**必须**在 replacer 中。
5. 所有帧的 `pin_count` 之和 = 所有未释放的 guard 数量。
6. 淘汰一个脏帧时，必须先把旧数据写回磁盘**再**装入新页。

**第 3/4 条最容易错**：`UnpinPage` 时 `pin_count` 减到 0，必须**同时**调用 `replacer_.SetEvictable(fid, true)`。忘记这一步 → 帧永远不可淘汰 → 缓冲池「假死」。

## 6. 代码示例

### 6.1 官方课程代码

**本 vault 未抓取 Fall 2026 project1 官方页面，无官方代码可引。**

待官方页面获取后需补充：

- 官方给出的 `BufferPoolManager` 类声明（成员变量、方法签名）；
- `LRUKReplacer` 的接口（`RecordAccess`、`Evict`、`SetEvictable`、`Remove`）；
- `PageGuard` 的三种类型与 `Drop()` 语义；
- `DiskScheduler` 的 `Schedule` 接口。

> 待核实：官方页面的具体 API 名称与任务拆解（是否分为 LRU-K replacer、buffer pool manager、page guard、disk scheduler 四个子任务）。

### 6.2 Agent 自行编写的教学示例

> 以下代码**非官方，仅用于说明概念**，不是 BusTub 的实现，也不构成项目答案。

**`FetchPage` 的核心骨架**（说明双重检查 + 淘汰流程）：

```cpp
// 非官方示例：仅示意流程，省略错误处理与部分细节
auto BufferPoolManager::FetchPage(page_id_t pid) -> std::optional<FrameId> {
  // 第一次检查：读锁
  {
    std::shared_lock<std::shared_mutex> read_guard(page_table_latch_);
    auto it = page_table_.find(pid);
    if (it != page_table_.end()) {
      FrameId fid = it->second;
      frames_[fid].pin_count_++;
      replacer_.SetEvictable(fid, false);
      return fid;
    }
  }

  // 未命中：升级为写锁
  std::unique_lock<std::shared_mutex> write_guard(page_table_latch_);

  // 第二次检查：可能别人已经读入了
  {
    auto it = page_table_.find(pid);
    if (it != page_table_.end()) {
      FrameId fid = it->second;
      frames_[fid].pin_count_++;
      replacer_.SetEvictable(fid, false);
      return fid;
    }
  }

  // 找一个可淘汰的帧
  auto victim = replacer_.Evict();
  if (!victim.has_value()) return std::nullopt;   // 所有帧都被 pin 住

  FrameId fid = *victim;
  Frame &frame = frames_[fid];

  // 若受害者是脏页，先写回
  if (frame.is_dirty_ && frame.page_id_ != INVALID_PAGE_ID) {
    disk_scheduler_.ScheduleWrite({frame.page_id_, frame.data_});
    // 注意：真实实现中应释放 page_table_latch_ 再做 I/O，此处简化
  }

  // 更新映射
  page_table_.erase(frame.page_id_);
  page_table_[pid] = fid;
  frame.page_id_ = pid;
  frame.pin_count_ = 1;
  frame.is_dirty_ = false;

  // 从磁盘读入
  disk_scheduler_.ScheduleRead({pid, frame.data_});
  replacer_.RecordAccess(fid);
  replacer_.SetEvictable(fid, false);

  return fid;
}
```

**LRU-K 的 `RecordAccess` 骨架**：

```cpp
// 非官方示例：双队列 LRU-K
void LRUKReplacer::RecordAccess(FrameId fid) {
  std::lock_guard<std::mutex> guard(latch_);
  auto &node = nodes_[fid];          // nodes_ 是 unordered_map<FrameId, Node>
  ++current_timestamp_;

  if (node.in_cache_list) {
    // 已在 cache list：更新时间戳（移到队尾）
    cache_list_.erase(node.cache_pos);
    cache_list_.push_back(fid);
    node.cache_pos = std::prev(cache_list_.end());
    node.last_access = current_timestamp_;
    return;
  }

  ++node.access_count;
  if (node.access_count >= k_) {
    // 达到 K 次：从 history 移到 cache
    history_list_.erase(node.history_pos);
    node.in_cache_list = true;
    cache_list_.push_back(fid);
    node.cache_pos = std::prev(cache_list_.end());
    node.last_access = current_timestamp_;
  } else {
    // 仍在 history：更新位置
    if (node.in_history_list) history_list_.erase(node.history_pos);
    history_list_.push_back(fid);
    node.history_pos = std::prev(history_list_.end());
    node.in_history_list = true;
  }
}
```

**Page Guard 的 RAII 骨架**：

```cpp
// 非官方示例：写守卫
class WritePageGuard {
 public:
  WritePageGuard(BufferPoolManager *bpm, FrameId fid, char *data,
                 std::unique_lock<std::shared_mutex> &&latch)
      : bpm_(bpm), fid_(fid), data_(data), latch_(std::move(latch)) {}

  ~WritePageGuard() { Drop(); }

  WritePageGuard(WritePageGuard &&other) noexcept
      : bpm_(other.bpm_), fid_(other.fid_), data_(other.data_),
        latch_(std::move(other.latch_)) {
    other.bpm_ = nullptr;            // 移动后源对象不再持有资源
  }

  WritePageGuard(const WritePageGuard &) = delete;
  WritePageGuard &operator=(const WritePageGuard &) = delete;

  void Drop() {
    if (bpm_ == nullptr) return;     // 已被移动或已 Drop
    bpm_->UnpinPage(fid_, /*is_dirty=*/true);
    bpm_ = nullptr;
    // latch_ 析构时自动解锁
  }

  auto GetData() -> char * { return data_; }

 private:
  BufferPoolManager *bpm_{nullptr};
  FrameId fid_{0};
  char *data_{nullptr};
  std::unique_lock<std::shared_mutex> latch_;
};
```

**说明**：真实实现中，`UnpinPage` 与解锁的**顺序**很关键——必须先解锁页闩锁，再 unpin（否则可能出现「unpin 后帧被淘汰，但闩锁还在」的窗口）。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| frame | page | frame 是**内存中的槽位**；page 是**磁盘上的数据单元**。一个 frame 可以装不同的 page（随时间变化） |
| pin count | 引用计数（`shared_ptr`） | pin count 是**手动**管理（Fetch/Unpin 配对）；`shared_ptr` 是**自动**的。语义类似但用途不同 |
| latch | lock | latch 保护**内存结构**（短、无死锁检测、不可回滚）；lock 保护**逻辑数据**（长、有死锁检测、可回滚） |
| LRU | LRU-K | LRU 看「最近一次」访问；LRU-K 看「第 K 次最近」访问。后者抗扫描污染 |
| 脏页 | 已刷新的页 | 脏页必须写回才能淘汰；干净页可直接丢弃 |
| page table 锁 | frame 闩锁 | 前者保护**映射与元数据**（短持有）；后者保护**页内容**（长持有） |
| `FetchPage` 返回 `nullptr` | 页不存在 | `nullptr` 表示「**所有帧都被 pin 住**」，不是「页不存在」。页不存在时应该分配新页 |
| 缓冲池 | OS 页缓存 | 缓冲池由数据库控制（替换策略、刷盘时机、预取）；OS 页缓存不透明 |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Slides（L04 Memory Management） | `90-原始PDF/15-445/slides/04-memorymanagement.pdf` | 待人工核对 | 缓冲池结构、替换策略、LRU-K |
| Notes（L04） | `90-原始PDF/15-445/notes/04-memorymanagement.pdf` | 待人工核对 | 同上（Figure 编号待补） |
| Slides 文本 | `_scout/text/15-445__slides__04-memorymanagement.pdf.txt` | — | 用 `=== [page N] ===` 定位 |
| Project #1 官方页面 | **未抓取** | — | — |

原始 URL：

- 讲义 slides：`https://15445.courses.cs.cmu.edu/fall2026/slides/04-memorymanagement.pdf`
- 讲义 notes：`https://15445.courses.cs.cmu.edu/fall2026/notes/04-memorymanagement.pdf`
- 项目页面：`https://15445.courses.cs.cmu.edu/fall2026/project1/`（**待人工访问核对**）

> 待核实：`04-memorymanagement.pdf` 的页数与重点页码（`_scout/pdf-pages.json` 无 15-445 条目，需用 `=== [page N] ===` 计数）；Project #1 的任务拆解、允许修改的文件、截止日期、是否包含 DiskScheduler。

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内，本讲内容对应 2025 年第 03 讲）

- 标题：Database Storage I / Memory Management（2025 年第 03 讲）
- URL：`https://www.youtube.com/watch?v=b53huOGcsZ8&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 年份：2025
- 时间戳：未核实，故不标注。

> 待核实：2025 年第 03 讲的确切标题与 ID。任务给定的映射表从 2026 第 14 讲开始（→2025 第 13 讲），未覆盖第 04 讲。上方的 `b53huOGcsZ8` 是 2025 年第 15 讲的 ID（对应 2026 第 16 讲 Query Optimization I），**不是** Memory Management 讲次，此处仅作播放列表入口示意。

说明：FAQ Q11 明确 Fall 2026 的录像只对 CMU 学生开放，非 CMU 学习者应观看 Fall 2025 的公开视频。播放列表：`https://www.youtube.com/playlist?list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`

## 10. 本节复习

- 能画出缓冲池的结构图，标出 page table、frames、replacer、disk scheduler 的位置。
- 能完整叙述 `FetchPage` 的流程，包括命中、未命中、淘汰、读盘四种情况。
- 能解释 `pin_count` 与 `dirty` 的作用，以及忘记 unpin 的后果。
- 能描述 LRU-K 的双队列结构与 `RecordAccess` / `Evict` 的逻辑。
- 能说明 LRU-K 为什么能抵抗顺序扫描污染。
- 能说出 Page Guard 相比手动 `UnpinPage` 的三个好处。
- 能列出缓冲池的三层锁，并说明持锁顺序如何避免死锁。
- 能说出至少四条缓冲池的正确性不变式。

## 11. 自我检查

**Q1.** 为什么 `FetchPage` 在未命中时要做「双重检查」？不做会怎样？

<details><summary>参考答案</summary>

**因为「释放读锁 → 获取写锁」之间有一个时间窗口，其他线程可能已经把这个页读进来了。**

**完整场景**：

1. 线程 A 拿读锁查表，pid=5 未命中。
2. 线程 A 释放读锁，准备拿写锁。
3. **（窗口）** 线程 B 拿写锁，把 pid=5 读入 frame 3，释放写锁。
4. 线程 A 拿到写锁，**如果不做第二次检查**，它会认为 pid=5 仍未命中，于是：
   - 淘汰一个帧（可能是 frame 3，如果它已经被 unpin）；
   - 从磁盘再读一次 pid=5；
   - 在 `page_table_` 中插入 `5 → 新帧`。
5. 结果：**同一个页在内存里有两份**，两份内容可能不一致（一份被修改、一份是旧的）→ **数据损坏**。

**即使不淘汰 frame 3**，也会浪费一次磁盘 I/O（读了两遍）。

**双重检查的写法**：

```cpp
// 第一次：读锁
{ std::shared_lock g(latch_); if (found) return ...; }

// 升级
std::unique_lock g(latch_);

// 第二次：写锁下再查
if (found) return ...;      // 别人已经读入了

// 真正未命中：淘汰 + 读盘
```

**另一种方案：不释放锁**。直接从读锁升级为写锁（`std::shared_mutex` 不支持原子升级，所以做不到）。或者一开始就拿写锁（简单但并发度低）。

**第三种方案：per-page latch**。用一个 `page_id → latch` 的映射，每个页一把锁，`FetchPage` 时锁住该页的 latch，其他线程对同一页的 `FetchPage` 会阻塞。这样不需要双重检查，但需要管理大量 latch。

**结论**：双重检查是「读写锁 + 释放再获取」模式的标准做法。类似模式在单例初始化（Meyer's singleton）、缓存加载中都很常见。

</details>

**Q2.** LRU-K 中，如果 K=2，一个页被访问了 1 次后就不再被访问，它会在哪个队列？淘汰时会被优先选中吗？

<details><summary>参考答案</summary>

**在 history list**，且**会被优先淘汰**。

**过程**：

1. 第一次访问：`access_count = 1 < K=2` → 插入 **history list**。
2. 之后不再访问 → 一直留在 history list。
3. `Evict()` 时，**优先从 history list 淘汰** → 这个页会被最先选中。

**这正是 LRU-K 的设计意图**：

- 只被访问一次的页（典型的顺序扫描、一次性查询）不值得占用缓冲池。
- 优先淘汰它们，保护 cache list 中「至少被访问 K 次」的热数据。

**对比 LRU**：LRU 只看「最近一次访问时间」。这个页如果刚刚被访问过（时间戳很新），LRU **不会**淘汰它——反而会淘汰一个很久没访问但访问过 100 次的老热数据。这就是 LRU 的缺陷。

**边界情况**：

- 如果 **history list 为空**（所有页都被访问 >= K 次），则从 cache list 淘汰 K-dist 最大的页。
- 如果某个页在 history list 中但 `pin_count > 0`，跳过它，看下一个。
- 如果所有页都被 pin 住 → `Evict()` 返回 `nullopt` → `FetchPage` 返回 `nullptr`。

**一个微妙之处**：如果 K 很大（如 K=5），history list 会积累大量「访问 1–4 次」的页，占用内存但永远不会被提升。这些页在淘汰时优先级最高，所以不影响热数据——但它们的元数据（时间戳、计数）有开销。

**实践建议**：K=2 是经验最优值（O'Neil 等人的原始论文与后续工业实践都支持）。K 太大 → 冷启动慢（新页要访问 K 次才进 cache）；K=1 → 退化为 LRU。

</details>

**Q3.** 一个学生实现了缓冲池，测试全部通过，但在长时间运行后 `FetchPage` 开始返回 `nullptr`。最可能的原因是什么？如何定位？

<details><summary>参考答案</summary>

**最可能的原因：pin count 泄漏（忘记 unpin，或 unpin 次数少于 fetch 次数）。**

**机制**：

1. 每次 `FetchPage` 使 `pin_count++`。
2. 如果某条代码路径忘记 `UnpinPage`，该帧的 `pin_count` 永远 > 0。
3. 该帧永远不可淘汰。
4. 累积到所有帧都被 pin 住 → `Evict()` 返回 `nullopt` → `FetchPage` 返回 `nullptr`。

**为什么「测试全部通过」但长跑才出问题**：短测试的访问模式可能只用到少数帧，泄漏几个帧不影响。长跑（或全表扫描）才会用尽所有帧。

**其他可能原因**：

1. **`SetEvictable` 忘记调用**：`UnpinPage` 时 `pin_count` 减到 0，但没有把帧重新加入 replacer 的可淘汰集合 → 帧「消失了」（既不在使用中，也不可淘汰）。
2. **`Remove` / `DeletePage` 的路径没有清理 replacer**：删除页时忘记 `replacer_.Remove(fid)`。
3. **异常路径泄漏**：`throw` 之前没有 unpin（这就是为什么要用 Page Guard）。
4. **死锁导致某些线程永远持有 pin**：不是泄漏，但效果类似。

**定位方法**：

1. **加断言**：在 `UnpinPage` 中检查 `pin_count >= 0`；在 `FetchPage` 返回 `nullptr` 前打印所有帧的 `pin_count` 与 `page_id`。
2. **统计配对**：维护两个计数器 `total_fetches` 与 `total_unpins`，在 `FetchPage` 返回 `nullptr` 时打印。若 `total_fetches != total_unpins`，就是泄漏。
3. **记录调用栈**：在 `FetchPage` 时记录 `__builtin_return_address(0)` 或 `backtrace()`，泄漏时对比哪些调用点没有配对的 unpin。
4. **Sanitizer + 压力测试**：用 ASAN 跑长测试；用 TSAN 检查是否有数据竞争导致 `pin_count` 更新丢失（如果 `pin_count` 不是原子操作且没有锁保护）。
5. **二分法**：注释掉一半功能（如禁用淘汰），看是否还泄漏。

**最有效的预防**：**用 Page Guard 替代手动 Fetch/Unpin**。guard 的析构函数保证配对，即使 `throw` 或 `return` 也不会泄漏。这也是 BusTub 引入 guard 的原因。

**一个具体的 bug 模式**：

```cpp
// 错误：异常路径泄漏
Page *p = bpm->FetchPage(pid);
if (some_condition) {
  throw std::runtime_error("...");   // pin_count 永远是 1
}
bpm->UnpinPage(pid, false);

// 正确：guard
auto guard = bpm->FetchPageRead(pid);
if (some_condition) throw std::runtime_error("...");   // guard 析构，自动 unpin
```

</details>

**Q4.** 为什么缓冲池需要自己的替换策略，而不是直接用操作系统的页缓存（如 mmap）？

<details><summary>参考答案</summary>

**四个核心原因**：

1. **替换策略的控制权**：
   - OS 用 LRU 类的策略，会被顺序扫描污染（把热数据挤出去）。
   - 数据库知道查询计划：它知道「这个页马上要被顺序扫描」，可以主动降低其优先级，或使用 LRU-K / 2Q / ARC 等抗污染策略。
   - 数据库还知道「这个页是索引的根节点，必须常驻」，可以 pin 住它。

2. **刷盘时机的控制权（WAL 正确性）**：
   - 数据库必须保证 **WAL 先于数据页落盘**（write-ahead logging）。如果数据页先落盘而日志没落盘，崩溃后无法恢复。
   - 用 OS 页缓存时，`write()` 返回不代表落盘，OS 可能在任意时刻刷盘 → 无法保证 WAL 顺序。
   - 缓冲池可以精确控制：刷数据页前先检查 `flushedLSN >= pageLSN`。

3. **预取（prefetch）能力**：
   - 数据库知道「接下来要扫描这 100 个页」，可以**异步批量读入**，隐藏 I/O 延迟。
   - OS 的预读（readahead）是启发式的，不如数据库的计划信息准确。

4. **可观测性与调优**：
   - 数据库需要统计「缓冲池命中率」「每个页的访问频率」，用于调优（如调整缓冲池大小、识别热点表）。
   - OS 页缓存的统计对数据库不透明。

**补充：mmap 的具体问题**：

- **页错误不可控**：`mmap` 的页错误发生在访问时，数据库无法预知何时会阻塞。
- **脏页回写时机不可控**：OS 决定何时 `msync`，数据库无法保证 WAL 顺序。
- **无法 pin**：OS 可以在任何时候回收一个 mmap 页（只要没有硬引用），数据库无法保证「这个页在内存里」。
- **信号处理复杂**：`SIGBUS`（文件被截断）等边界情况难处理。

**工业实践**：

- **PostgreSQL**：用自己的 shared buffers（默认 128MB），不用 mmap。
- **MySQL InnoDB**：自己的 buffer pool（可配几十 GB），带 young/old 分区。
- **SQLite**：自己的 page cache，但可选 `mmap` 模式（`PRAGMA mmap_size`），用于只读场景。
- **LMDB**：**用** mmap（read-only B+ 树，写时复制），因为它的设计保证了 mmap 安全。

**结论**：是否需要自己的缓冲池，取决于**是否需要精确控制替换策略与刷盘时机**。对需要 WAL 与事务的系统，答案是「必须」。

</details>

## 12. 进一步学习

- 项目导航：[[00-项目总览]]
- 上一个项目：`01-Project0-Cpp-Primer.md`
- 下一个项目：`03-Project2-BPlusTree.md`
- 相关讲义：[[15-445-04-Memory-Management]]（缓冲池）、[[15-445-03-Database-Storage-I]]（页与磁盘）、[[15-445-05-Database-Storage-II]]（存储引擎）
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：
  - O'Neil, O'Neil, Weikum, "The LRU-K Page Replacement Algorithm for Database Disk Buffering"（SIGMOD 1993）——LRU-K 原始论文。
  - Megiddo & Modha, "ARC: A Self-Tuning, Low Overhead Replacement Cache"（FAST 2003）。
  - Johnson & Shasha, "2Q: A Low Overhead High Performance Buffer Management Replacement Algorithm"（VLDB 1994）。
  - 教材 *Database System Concepts*（7th Ed.）第 12.3 节（Buffer Manager）。
  - BusTub 仓库 `src/include/buffer/` 下的头文件注释——**最权威的规格来源**。
- 动手建议：实现后用「顺序扫描 + 随机访问混合」的负载测试，对比 LRU 与 LRU-2 的命中率；用 `perf stat` 观察 cache miss 与 I/O 次数。
- **提醒**：本篇依据课程结构公开信息 + 通用知识整理，具体任务以官方 project1 页为准。`> 待核实：` 处需人工核对。
