---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: L10
topic: Index Concurrency Control — Latches, Latch Crabbing, Leaf Node Scans
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 数据库
  - 并发控制
  - 闩锁
  - B+树
  - latch-crabbing
---

# 15-445 L10：索引并发控制（Index Concurrency Control）

> 前九讲的所有数据结构都隐含一个假设：**只有一个 worker 在操作它**。真实 DBMS 必须让多个线程同时读写同一棵 B+ 树——否则多核 CPU 白买、磁盘 I/O 停顿无法被掩盖。本讲解决「如何让索引线程安全」：先厘清 **lock 与 latch** 的区别，再看三种 latch 实现，最后给出 B+ 树的 **latch crabbing（闩锁螃蟹协议）**、乐观优化与**叶子节点扫描**的死锁难题。

## 1. 本节学习目标

学完本讲，你应该能够：

1. 清晰区分 **lock（锁）** 与 **latch（闩锁）**：保护对象、持有时间、模式、死锁处理方式、由谁管理。
2. 说明 latch 的两种模式与兼容矩阵，解释为什么 READ 模式可以共享而 WRITE 模式独占。
3. 比较三种 latch 实现（TAS 自旋、阻塞式 OS mutex、读写锁）的优缺点，并给出各自的典型 C++ 对应物。
4. 说明哈希表并发的三种粒度（全局 / 页级 / 槽级），解释为什么哈希表**不可能死锁**。
5. 完整叙述 **latch crabbing** 协议的三步，准确定义「**safe 节点**」在插入与删除时的判据。
6. 说明 **乐观（optimistic）latch crabbing** 为什么能大幅提升并发，以及失败后如何回退。
7. 解释**叶子节点扫描**为什么打破了 top-down 加锁顺序、为什么可能死锁，以及为什么只能用「no-wait + 自我中止重试」解决。
8. 说明 B+ 树写操作为什么要维护 **private write-set**，以及取不到 latch 时如何回滚。

## 2. 前置知识

- **B+ 树的结构与分裂/合并**：见 [[15-445-08-Indexes-and-Filters-I]]；本讲所有协议都建立在「插入可能 split、删除可能 merge」之上。
- **哈希表与可扩展哈希**：见 [[15-445-07-Hash-Tables]]；哈希表 latching 是本讲第一个案例。
- **缓冲池与页**：见 [[15-445-04-Memory-Management]]；latch 保护的是**内存中的页**，而页由缓冲池管理。
- **事务与锁**：本讲只做对比，细节见 [[15-445-18-Concurrency-Control-Theory]]；关键是记住「lock 属事务层、latch 属物理层」。
- **C++ 原子操作**：`std::atomic`、`std::atomic_flag`、CAS 指令；Project #2 会大量使用。

## 3. 核心概念

### 3.1 Worker（工作单元 / 执行上下文）

执行查询的线程或进程。讲义定义为 "Execution Context (i.e., Thread, Process)"。PostgreSQL 用**多进程**模型，多数系统用**多线程**模型。本讲的「并发」指的是多个 worker 同时访问同一份内存数据结构。

### 3.2 Concurrency Control Protocol（并发控制协议）

DBMS 用来保证「对共享对象的并发操作产生正确结果」的方法。讲义把正确性分成两个层次：

- **Logical Correctness（逻辑正确性）**：worker 能否读到它「应该」读到的数据。这是事务层的议题（隔离级别）。
- **Physical Correctness（物理正确性）**：对象的内部表示是否始终健全——没有野指针、没有读到写了一半的节点。

**本讲只关心 physical correctness**。这是理解全文的关键：我们不管「读到的是不是最新版本」，只管「读到的结构不能崩」。

### 3.3 Lock（锁）

保护**数据库的逻辑内容**（表、行、元组）不被其他事务干扰的机制。由**事务**持有、持续**整个事务**、模式有 Shared / Exclusive / Update / Intention 四种、死锁靠**检测与解决**（waits-for 图、超时、中止）、由独立的 **Lock Manager** 管理、**需要回滚**（事务中止时撤销修改）。

### 3.4 Latch（闩锁）

保护 **DBMS 内部数据结构**（B+ 树节点、哈希表、缓冲池映射表）的**临界区**不被其他 worker 干扰的机制。由 **worker** 持有、持续**一次操作**、模式只有 Read / Write 两种、死锁靠**编码纪律**规避、**不需要回滚**（因为不涉及事务语义）、latch 本身就是被保护结构的一部分。

### 3.5 Latch Mode（闩锁模式）

- **Read Mode（读模式）**：多个线程可同时持有同一对象的读 latch。若已有其他线程以读模式持有，仍可获取。
- **Write Mode（写模式）**：独占。若已有任何线程以任何模式持有，则无法获取。

兼容矩阵：Read-Read ✔；Read-Write ✘；Write-Read ✘；Write-Write ✘。

### 3.6 Test-and-Set Spin Latch（TAS 自旋闩锁）

用一个原子标志位实现的闩锁。加锁就是原子地把标志位置 1 并读回旧值；若旧值为 1 说明已被占用，则**原地循环重试**（自旋）。对应 `std::atomic_flag` / `std::atomic<T>`。

### 3.7 Compare-and-Swap（CAS，比较并交换）

原子指令：比较内存位置 M 的内容与给定值 V，若相等则把 M 改为 V'，否则失败。是构建所有无锁结构与闩锁的基础原语。C++ 里是 `std::atomic<T>::compare_exchange_weak/strong`，GCC 内建为 `__sync_bool_compare_and_swap(&M, V, V')`。

### 3.8 Blocking OS Mutex（阻塞式操作系统互斥量）

由操作系统提供的互斥量。Linux 上 `std::mutex` 底层是 **futex**（fast userspace mutex）：无争用时在用户态用一个自旋闩锁解决，有争用时才陷入内核把自己挂起。约 **25 ns** 一次 lock/unlock。

### 3.9 Reader-Writer Latch（读写闩锁）

区分读/写模式的闩锁，内部维护读者计数、写者标志与等待队列。对应 `std::shared_mutex`，底层常用 `pthread_rwlock_t`（由 `pthread_mutex_t` + `pthread_cond_t` 组合实现）。需要决定**读者优先 / 写者优先 / 公平**策略以避免饥饿。

### 3.10 Latch Crabbing / Coupling（闩锁螃蟹协议 / 闩锁耦合）

允许**多个 worker 同时遍历并修改** B+ 树的协议。核心三步：**取父节点 latch → 取子节点 latch → 若子节点 safe 则释放父节点 latch**。「螃蟹」的比喻来自它像螃蟹一样「先抓住下一个再松开上一个」地横向移动。

### 3.11 Safe Node（安全节点）

一个节点在**本次更新**中**不会发生 split / merge / redistribute**。判据：

- **插入**时：节点**未满**（还有空位）→ safe。
- **删除**时：节点**多于半满**（删掉一个键后仍满足最少键数）→ safe。

**读操作不需要考虑 safe**——读不会改变结构。

### 3.12 Optimistic Latch Crabbing（乐观闩锁螃蟹）

针对「绝大多数更新不会引起分裂/合并」这一事实的优化：先用 **READ latch** 一路向下走到叶子，再对叶子取 **WRITE latch**；若叶子不 safe，则释放所有 latch 并用**悲观（basic）协议重来**。

### 3.13 Leaf Node Scan（叶子节点扫描）

范围查询需要沿叶子链表**水平移动**。此时加锁方向从「自上而下」变成「水平」，与自上而下的更新线程交叉时可能形成环——这是本讲唯一的真正死锁来源。

### 3.14 No-Wait Mode（不等待模式）

获取兄弟节点 latch 时**不允许阻塞等待**：取不到就立即失败返回。调用方据此释放已持有的 latch 并重试。这是打破死锁的唯一手段。

### 3.15 Private Write-Set（私有写集合）

每个 worker 在操作期间维护的「我改了什么」记录：**节点标识 + 在该节点插入/删除的键列表**。用于在操作失败时**撤销**已做的修改（因为 latch 层没有事务回滚）。

## 4. 通俗理解

- **Lock vs Latch = 银行柜台 vs 卫生间门锁**。Lock 像银行柜台：你办业务期间整个窗口归你（**整个事务**），后面的人排队，银行有叫号系统统一管理（**Lock Manager**），你办到一半反悔要走撤销流程（**回滚**）。Latch 像卫生间门锁：你进去就锁、出来就开（**临界区**），只有「有人/没人」两种状态（**Read/Write 两模式**），没人管你排多久（**无死锁检测**），你也不会因为上过厕所就需要「撤销」（**无需回滚**）。
- **Latch Crabbing = 走钢丝时先抓下一根再松上一根**。你要沿着一排栏杆移动，规则是**始终至少抓着一根**。先抓 B 再松 A，先抓 C 再松 B。这样你永远不会「悬空」——也就是永远不会出现「我以为父节点还在，其实它已经被别人改掉了」。
- **Safe 节点 = 手上有余量的行李箱**。你往里塞东西前先看：这个箱子还有空位吗？有 → 塞完也不会溢出，那我就不用再盯着上面的箱子了（释放祖先 latch）。没有 → 我塞进去它会爆，那我就得**一直抓着它和它的父箱**，准备随时处理爆箱（split）。
- **乐观 crabbing = 先按最省事的方式试，不行再老老实实来**。绝大多数插入不会导致分裂（就像绝大多数过马路不会遇到车），所以先「读着走过去」，只在最后一步真正动手时加写锁。万一发现要分裂，退回来重走一遍悲观流程。
- **叶子扫描的死锁 = 两条相向而行的人在独木桥上**。T1 自上而下要写，T2 自左向右要读，两人各持一半、都在等对方手里那根——而**闩锁没有交警**（无 Lock Manager），谁也判不出这是死锁。唯一出路是**规定谁都不许干等**：抓不到就立刻松手退回去重来。

具体数字：`std::mutex` 一次 lock/unlock 约 **25 ns**。一棵 4 层 B+ 树的一次点查若每层取一次 mutex，就是 **100 ns** 的纯闩锁开销——而一次 DRAM 访问只要 ~100 ns。这就是为什么讲义强调「latch 要小、要快、要无争用快路径」，也是为什么 TAS 自旋闩锁（单条原子指令）在高性能 DBMS 里更受欢迎。

## 5. 原理与推导

### 5.1 为什么单 worker 假设必须被打破

讲义开篇的观察：前面讨论的所有数据结构都假设**单 worker**。但 DBMS 必须让多个 worker 安全地并发访问，原因有二：

1. **利用多核**：单线程无法吃满现代 CPU 的核心数。
2. **掩盖磁盘 I/O 停顿**：一个线程等页从磁盘读入时，其他线程应该能继续干活（这与第 4 讲「缓冲池隐藏 I/O 延迟」是同一目标的另一面）。

> 讲义在第 6 页直接标注 "They Don't Do This!"——即「只支持单 worker 的 DBMS」是不存在的（除了 Redis 这类特例）。

### 5.2 Lock 与 Latch：为什么必须分开

这是全讲最重要的一张表（讲义第 11–12 页，来源 Goetz Graefe, *A Survey of B-Tree Locking Techniques*, ACM TODS 2010）：

| 维度 | Locks | Latches |
|---|---|---|
| 隔离谁 | **事务（Transactions）** | **Worker（线程、进程）** |
| 保护什么 | **数据库内容** | **内存数据结构** |
| 持有多久 | **整个事务** | **临界区** |
| 模式 | Shared, Exclusive, Update, Intention | Read, Write |
| 死锁处理 | **检测与解决** | **规避（avoidance）** |
| 靠什么 | Waits-for 图、超时、中止 | **编码纪律（coding discipline）** |
| 存在哪里 | **Lock Manager** | **被保护的数据结构本身** |

**为什么不能合并成一套机制**：两者的**生命周期**与**失败语义**根本不同。

- 事务可能运行几秒到几分钟，锁必须跨越大量 I/O；而 latch 只保护几条指令，必须极轻量（字节级、单指令）。
- 事务中止需要**撤销**已写入的数据（这正是 WAL 与 undo 的职责）；而 latch 保护的临界区如果中途失败，只需**把内存改回去**，不涉及持久化。
- 锁的数量可能有百万级（每行一把），必须有集中的 Lock Manager 做死锁检测；latch 若也走集中管理，开销会毁掉性能——所以 latch 用**原子指令直接嵌在数据结构里**。

**Physical vs Logical Correctness** 的区分正是由此而来：latch 只保证**物理**正确（结构不崩、无野指针），事务层才保证**逻辑**正确（读到该读的版本）。

### 5.3 Latch 的两种模式与兼容矩阵

```
        ┌─────────┬─────────┐
        │  Read   │  Write  │   ← 已持有
┌───────┼─────────┼─────────┤
│ Read  │    ✔    │    ✘    │   ← 请求
│ Write │    ✘    │    ✘    │
└───────┴─────────┴─────────┘
```

**为什么读读兼容**：读操作不改变结构，多个读者同时读不会互相破坏。这是并发度的主要来源——B+ 树的绝大多数访问是读。

**为什么读写不兼容**：写者可能分裂节点、搬移键、改指针；读者若同时遍历，会读到「键已搬走但指针还没更新」的中间状态——物理不正确。

**为什么写写不兼容**：两个写者同时改一个节点，后写者会覆盖前者的修改（丢失更新）。

注意模式只有两种，而**事务锁有四种**（Shared / Exclusive / Update / Intention）。Update 锁与 Intention 锁的存在是因为事务需要「先读后写」的两阶段语义与层次化加锁（见第 18 讲），latch 不需要这些——它只保护一段几十条指令的临界区。

### 5.4 Latch 实现的四个目标

讲义引用 Filip Pizlo 的四条目标：

1. **Small memory footprint（小内存足迹）**：B+ 树的每个节点都可能带一把 latch。若每把 latch 要 64 字节，一个 8 KB 的节点就浪费近 1%；若有百万个节点，开销惊人。所以 latch 必须是**字节级**的。
2. **Fast execution path when no contention（无争用时的快路径要快）**：绝大多数 latch 获取是**无争用**的。这条路径必须是几条指令，不能有函数调用、不能进内核。
3. **Decentralized management（去中心化管理）**：不能有全局的 latch 表（会变成新的瓶颈与争用点），latch 必须**嵌在数据里**。
4. **Avoid expensive system calls（避免昂贵系统调用）**：每次 `futex` 陷入内核约 25 ns 到微秒级，比一次 DRAM 访问还贵。

这四条目标直接决定了三种实现的取舍。

### 5.5 三种 latch 实现

**① Test-and-Set Spin Latch（TAS 自旋闩锁）**

```cpp
std::atomic_flag latch;          // 或 std::atomic<bool>

while (latch.test_and_set()) {   // 原子地置 1 并返回旧值
    // Retry? Yield? Abort?       ← 讲义原样留了这三个问号
}
// 临界区
latch.clear();
```

- **优点**：加锁/解锁是**单条原子指令**，极快；不需要内核介入；内存足迹 1 字节。
- **缺点**：
  - **不可扩展（non-scalable）**：争用时所有线程在同一个缓存行上自旋，形成「缓存行乒乓」。
  - **不 cache friendly**：自旋会不断使其他核心的缓存行失效。
  - **不 OS friendly**：自旋线程占着 CPU 不放，操作系统无法把它调度去干别的活。
  - **NUMA 下更糟**：轮询远端节点的缓存行代价极高。

讲义的三个问号（Retry / Yield / Abort）正是自旋策略的设计空间：纯自旋浪费 CPU；`yield` 让出时间片但增加延迟；`abort` 适合乐观场景。实践中常用**自旋若干次后 yield** 的混合策略。

**② Blocking OS Mutex（阻塞式 OS 互斥量）**

```cpp
std::mutex m;
m.lock();
// Do something special...
m.unlock();
```

Linux 上 `std::mutex` 底层是 **futex**：

```
futex = Userspace Latch + OS Latch
         ↑ 无争用时只走用户态（快）
                        ↑ 有争用时陷入内核挂起线程（慢但不烧 CPU）
```

- **优点**：**使用简单**（不用考虑自旋策略、不用管内存序），语义清晰。
- **缺点**：约 **25 ns** 一次 lock/unlock，比 TAS 慢一个数量级；**不可扩展**（内核需要维护等待队列等簿记）；内存足迹大（`pthread_mutex_t` 通常 40 字节）。

**③ Reader-Writer Latch（读写闩锁）**

```cpp
std::shared_mutex latch;
// 读者： latch.lock_shared() / unlock_shared()
// 写者： latch.lock()        / unlock()
```

内部结构（讲义第 43–52 页的动画）：一个**读者计数**、一个**写者标志**、以及**读/写两个等待队列**。

```
初始:        readers=0, writer=0
读者1进入:   readers=1
读者2进入:   readers=2          ← 读读兼容
写者请求:    writer=1（等待）    ← 必须等 readers 归零
读者1退出:   readers=1
读者2退出:   readers=0 → 唤醒写者
```

- **优点**：允许**并发读**，对读多写少的索引极其有利。
- **缺点**：需要管理等待队列以防**饥饿**（读者源源不断时写者永远等不到）；元数据（计数 + 队列）比单字节的 TAS 大得多；加解锁路径更长。

**饥饿策略三选一**：

- **Reader-preferred**：新读者可越过等待的写者 → 写者可能饿死。
- **Writer-preferred**：有写者等待时新读者排队 → 读者可能饿死。
- **Fair（公平）**：按到达顺序放行，实现最复杂。

**更高级的实现**（讲义第 17 页列出，不展开）：

| 名称 | 出处 | 解决什么 |
|---|---|---|
| Adaptive Spinlock | Apple **ParkingLot** | 根据争用情况在自旋与阻塞间自适应切换 |
| Queue-based Spinlock | **MCS Locks** | 每个等待者在自己的缓存行上自旋，消除缓存行乒乓 |
| Optimistic Lock Coupling | "The Germans"（指德国研究组） | 读路径不加 latch，靠版本号验证 |
| Cache-Friendly Queues | Google **nsync** | 减少等待队列本身的缓存争用 |

讲义的告诫：**"developers should not write their own latch implementations"**——这些细节（内存序、NUMA、饥饿、虚假唤醒）极其容易出错，应使用经过验证的库。

### 5.6 哈希表的并发：为什么它简单

讲义第 53 页的核心论断：

```
Easy to support concurrent access due to the limited ways workers access
the data structure.
  → All workers move in the same direction and only access a single
    page/slot at a time.
  → Deadlocks are not possible.
```

**为什么不可能死锁**：哈希表的访问是**单向、单点**的——计算 `hash(key)` 直接跳到目标页/槽，**不经过中间结构**。每个 worker 在任一时刻只持有一个页/槽的 latch，且**从不回头**。既然不存在「持有 A 等 B、持有 B 等 A」的环，就没有死锁。

（对比 B+ 树：遍历要**逐层下降**，更新要**向上传播分裂**，天然存在多节点同时持锁的需求。）

**三种粒度**（讲义第 54–56 页）：

| 粒度 | 做法 | 并行度 | 开销 |
|---|---|---|---|
| **Global Latch** | 一把 latch 保护整个表 | 最低（同一时刻只有一个 worker 能改） | 最小（1 把 latch） |
| **Page/Block Latches** | 每页内嵌一把读写 latch，访问前取、离开前放 | 中 | 中（每页一把） |
| **Slot Latches** | 每个槽一把 latch | 最高（不同槽完全并行） | 最大（每槽都要 latch 元数据） |

**Page latch 的动画**（第 57–76 页）：T1 `Find D` 对 D 所在页取 **R** latch；T2 `Insert E` 对 E 所在页取 **W** latch。两者在不同页，完全并行。讲义标注「It's safe to release the latch on Page #1」——因为 T1 已经拿到目标页的 latch，不再需要前一页。

**Slot latch 的动画**（第 77–91 页）：T1 只对槽 D 取 R，T2 只对槽 E 取 W。粒度更细，但**每个槽都要存 latch 元数据**——讲义建议「可用单模式（single-mode）latch 减少元数据与计算开销」，即放弃读写区分、只用 TAS 自旋锁，因为槽级临界区极短，读写区分带来的收益不抵元数据成本。

**扩展（resize）**：哈希表扩容/缩容需要搬移大量数据、改变全局结构，因此必须对**整个表**（通常是 header page）取**全局写 latch**。这与「正常路径用细粒度、结构变更用粗粒度」的一般模式一致。

**无锁方案**：讲义还提到可以用 **CAS 直接做 latch-free 线性探查**——用 CAS 尝试把 `null` 槽替换为新值，失败则探查下一个槽。因为线性探查本身就是「向后找空位」，CAS 失败天然等价于「这个槽被抢了，继续下一个」，语义完美契合。

### 5.7 B+ 树的并发：两个必须防范的问题

讲义第 92 页明确列出：

```
We need to protect against two types of problems:
  → Workers modifying the contents of a node at the same time.
  → One worker traversing the tree while another worker splits/merges nodes.
```

**问题一**：两个 worker 同时改一个节点 → 丢失更新、结构损坏。用**节点级 latch**（写模式）解决。

**问题二**（更难）：T1 正在删除 44 并触发 rebalance，T2 同时在查找 41。若 T2 读到「父节点已更新但子节点还没搬完」的中间状态，就会走到错误的位置甚至野指针。讲义第 93–107 页的动画演示了这一点：T1 `Delete 44` 触发 `Rebalance!`，T2 `Find 41` 此时看到的树是**不一致的**（页面标注 `???`）。

**latch crabbing 正是为解决第二个问题而设计的**——它保证任何时刻，一个 worker 沿着路径向下走时，**至少持有当前节点的 latch**，因此它看到的子树是稳定的。

### 5.8 Latch Crabbing 协议

**三步核心**（讲义第 108 页）：

```
1. Get latch for parent
2. Get latch for child
3. Release latch for parent if "safe"
```

**Safe 的判据**（第 108 页）：

```
A safe node is one that will not split or merge when updated.
  → Not full (on insertion)
  → More than half-full (on deletion)
```

**为什么 safe 就能释放祖先**：若子节点 safe，则本次更新**不会改变子节点的存在性或它在父节点中的条目**。既然父节点的内容不会因这次操作而改变，就没必要继续持有父节点的 latch——后面的 worker 可以自由通过。

反之，若子节点**不 safe**（插入时已满、删除时恰好半满），则本次操作可能**分裂或合并**它，进而**修改父节点**（插入新条目或删除条目），甚至级联到祖父。此时必须**保留祖先的 latch**，以便随时向上传播结构变更。

**Find 的协议**（第 109 页）：

```
Start at root and traverse down the tree:
  → Acquire R latch on child,
  → Then unlatch parent.
  → Repeat until we reach the leaf node.
```

注意：读操作**不需要检查 safe**——读不会引起分裂/合并，所以拿到子节点后立刻放父节点即可。这使读路径的并发度非常高（多个读者可以同时在同一路径上下降）。

**Insert/Delete 的协议**（第 109 页）：

```
Start at root and go down, obtaining W latches as needed.
Once a child node is latched, check if it is safe:
  → If child is safe, release all latches on ancestors.
  → Optimization: When at an inner node that is "safe" can release
    all latches on ancestors.
```

**释放顺序**：讲义 notes 指出——释放顺序**对正确性没有影响**（只要在取到子节点之后再放父节点），但**对性能有影响**：应**先释放靠近根的 latch**，因为它阻塞的子树范围最大。一棵 4 层树里，根 latch 阻塞全部，叶子 latch 只阻塞一个叶子。

**四个讲义示例**：

**Example #1: Find 38**（第 110–118 页）

```
根 A 取 R → 下降到 B 取 R → 释放 A → 下降到 F 取 R → 释放 B → 到达叶子，找到 38
讲义标注："It is now safe to release the latch on A."
```

**Example #2: Delete 38**（第 119–129 页）

```
根 A 取 W → 下降到 B 取 W
  B 删除 38 后只剩 [10,11,12,13]，恰好半满 → B 不 safe（可能 coalesce）
  → 讲义标注："We may need to coalesce B, so we can't release the latch on A."
→ 继续下降到 D 取 W
  D 是 [20,22]，删除不涉及 D，且 D 不会与 C 合并 → D safe
  → 讲义标注："We know that D will not merge with C, so it is safe to
     release latches on A and B."
→ 释放 A、B，只在 D 上操作
```

这个例子演示了关键点：**safe 判断是逐层进行的**，而且判断依据是「这个节点在本次操作后是否还满足最少填充」——B 删掉 38 后只剩 4 个键（假设 m=5 时最少 2 个键），看起来够，但**它原本就是最小填充**，所以合并风险存在。

**Example #3: Insert 45**（第 130–137 页）

```
根 A 取 W → 下降到 B 取 W
  讲义："We know that if D needs to split, B has room, so it is safe to
        release the latch on A."
  → B 未满，即使 D 分裂也能容纳新条目 → 释放 A
→ 下降到 I 取 W，I 未满 → 释放 B、D
```

**Example #4: Insert 25**（第 138–148 页）

```
根 A 取 W → B 取 W → F 取 W
  F 已满 [23,31] → 插入 25 会分裂 → F 不 safe
  → 讲义："We need to split F, so we need to hold the latch on its
     parent node."
→ 分裂 F 为 F 与 J，把中间键 push up 到父节点
```

**Example #4 是整个协议存在的理由**：如果提前释放了父节点 latch，就无法安全地把分裂产生的新节点挂到父节点上。

### 5.9 乐观 latch crabbing：消除根节点瓶颈

**观察**（第 149–150 页）：所有更新示例的第一步都是**对根取写 latch**。三个并发更新（Insert 45、Delete 38、Insert 25）在根上**完全串行化**——树的并发度被根节点限制为 1。

```
A  W  Insert 45
A  W  Delete 38      ← 三者在根 A 上排队
A  W  Insert 25
```

**洞察**：**绝大多数 B+ 树修改不需要分裂或合并**。一棵高填充率的树里，插入导致分裂的概率约为 1/(m-1)，删除导致合并的概率更低。为极小概率的事件付出「每次都对根加写锁」的代价是巨大的浪费。

**乐观协议**（第 151–152 页）：

```
Search: Same as before.

Insert/Delete:
  → Set latches as if for search: 一路取 R latch 到叶子
  → 在叶子上取 W latch
  → If leaf is not safe:
        release all latches, and restart thread using previous
        insert/delete protocol with write latches（悲观重来）
```

**代价分析**（讲义第 152 页的原话）：

```
This approach optimistically assumes that only leaf node will be modified;
if not, R latches set on the first pass to leaf are wasteful.
```

即：失败时白走了一趟（拿了又放的 R latch 全是浪费）。但由于失败率低（叶子分裂/合并罕见），**期望收益远大于期望损失**。

**示例**（第 153–163 页）：

- **Delete 38 成功路径**：一路 R latch 到叶子 H，对 H 取 W；H 删除后仍多于半满 → safe → 完成。讲义标注 "Node H will not coalesce, so we're safe!"。
- **Insert 25 失败路径**：一路 R latch 到 F，对 F 取 W；F 已满 → 不 safe → **释放全部 latch，改用悲观协议重来**。讲义标注 "We need to split F, so we must restart and re-execute like before."

**latch 升级（upgrade）**：某些实现支持把已持有的 R latch **原地升级**为 W latch，从而避免「释放全部再重走」。但这更复杂：升级需要等待其他读者退出，可能死锁（若两个线程都想升级）；且要求沿途的祖先 R latch 仍然持有。讲义只把它列为可选优化。

**乐观协议的正确性前提**：先取 R latch 下降时，读到的路径是稳定的；一旦在叶子上拿到 W latch，就拥有了修改权。若叶子不 safe，说明需要改父节点，而此时父节点的 R latch 已被释放（按 Find 协议），无法安全修改——所以必须**整体重来**。

### 5.10 叶子节点扫描：唯一真正的死锁来源

**问题**（第 164 页）：

```
The workers in all the examples so far have acquired latches in a
"top-down" manner.
  → A worker can only acquire a latch from a node that is below its
    current node.
  → If the desired latch is unavailable, the worker must wait until it
    becomes available.

But what if workers want to move from one leaf node to another leaf node?
```

**为什么 top-down 无死锁**：所有 worker 都按「根 → 叶」的**同一方向**获取 latch，形成的是**有向无环图**（树本身），不可能出现环。这是 latch crabbing 天然安全的根本原因。

**水平扫描打破了这个性质**：范围查询要沿叶子链表走，方向变成「左 → 右」（或右 → 左）。于是：

```
T1（更新）: 自上而下，持有父节点，想要叶子 X 的 W latch
T2（扫描）: 自左向右，持有叶子 X，想要右边兄弟 Y 的 R latch
                                    ↑
            若 T1 想要的正是 T2 持有的，而 T2 想要的正是 T1 路径上的…
            → 环 → 死锁
```

**讲义 Example #3**（第 181–192 页）：

```
T1: Delete 4        → 对 C 取 W latch（删除触发 rebalance，需独占）
T2: Find Keys > 1   → 持有 B 的 R latch，想要 C 的 R latch
                      → 但 C 上有 T1 的 W latch → 拿不到
                      → 讲义："T2 does not know what T1 is doing…"
```

**T2 的三个选择**（讲义列在页面上）：

| 选择 | 问题 |
|---|---|
| **Wait** | 不知道 T1 会不会等自己 → 可能死锁。latch **没有死锁检测**（无 Lock Manager） |
| **Abort the other worker** | latch **不记录持有者**，无法中止别人；且中止别人需要对方能回滚 |
| **Abort ourself** | ✔ 唯一可行：释放已持有的全部 latch，退回去重试 |

讲义在三个选项后只对 **"Abort ourself"** 做了高亮（第 192 页），这就是答案。

**为什么「等待」不可行**：等待的正确性依赖于「对方最终会释放」。在 lock 的世界里，Lock Manager 会检测 waits-for 环并中止一方；但 **latch 没有集中管理器、不记录持有者、不检测环**——两个线程可以永远互等。

**解决方案：no-wait 模式 + 编码纪律**（第 193 页）：

```
Latches do not support deadlock detection or avoidance. The only way we
can deal with this problem is through coding discipline.

The leaf node sibling latch acquisition protocol must support a "no-wait"
mode.

The DBMS's data structures must cope with failed latch acquisitions.
  → Usually transparent to end-user / application.
```

**具体做法**：

```
取兄弟节点 latch 时传入 no-wait 标志：
  成功 → 释放原叶子 latch，继续水平移动
  失败 → 立即释放所有已持有的 latch，从头重试本次扫描
         （或根据「已完成多少工作」决定是否短暂等待后再试）
```

**关键约束**（第 169–170 页）：**在拿到兄弟节点 latch 之前，绝不能释放当前叶子的 latch**。否则会出现「我放开了 C，还没抓住 B，中间被别人插进来改了 C→B 的指针」的窗口——水平方向的结构就断了。这与垂直方向的 crabbing 是同一个原则：**始终至少持有一个 latch 来锚定当前位置**。

**高争用时怎么办**：讲义 notes 指出，应由**更高层的线程调度器**介入（例如检测到某 worker 反复失败就降低其优先级或让它让出 CPU），但这**不属于数据结构实现的责任**——数据结构只能保证「不死锁、可重试」，公平性是调度层的事。

### 5.11 写操作的原子性与 private write-set

**问题**（第 194 页）：worker 可能在操作**中途**失败（取不到某个 latch）。此时它可能已经修改了几个节点（插入了一些键、分裂了一个节点）。**latch 层没有事务回滚**——不能指望 WAL 或 undo 来撤销这些内存修改。

**解决方案**：

```
Each worker keeps leaf node modifications in its private write-set
during an operation.
  → List of node identifiers with keys inserted/deleted.

A worker holds write latches on modified nodes until it finishes that
operation.
  → Ensures consistency by never exposing partial updates to other threads.

If a worker cannot acquire a write latch on a node:
  → Rollback modifications found in its write-set.
  → Abort the operation by releasing all latches.
```

**三个要点**：

1. **write-set 记录粒度是「节点 + 键」**：不是整页快照，而是「我在节点 X 插入了键 25、在节点 Y 删除了键 38」。回滚就是反向执行这些操作。
2. **修改过的节点必须持有 W latch 直到操作结束**：否则其他线程会看到「部分更新」的中间状态——这正是 physical correctness 要防的。
3. **失败即回滚 + 释放全部 latch**：对终端用户**透明**（用户只看到操作失败，可以重试）。

**为什么这个方案够用**：B+ 树的单次操作（一次插入）涉及的修改量很小（通常 1–2 个节点，最坏 O(log n) 个），所以 write-set 很小，回滚代价可控。这也是「latch 不需要事务级回滚」的具体体现——**局部撤销**就够了。

### 5.12 全景：一个并发 B+ 树操作的完整流程

把上面所有协议串起来，一次并发的点查与插入大致是：

```
【点查 Find(key)】
  1. 对根取 R latch
  2. 循环：对子节点取 R latch → 释放父节点 R latch → 下降
  3. 到达叶子，在叶子内二分查找
  4. 释放叶子 R latch

【插入 Insert(key) —— 乐观路径】
  1. 对根取 R latch
  2. 循环：对子节点取 R latch → 释放父节点 → 下降（同 Find）
  3. 到达叶子，对叶子取 W latch
  4. 若叶子 safe（未满）→ 插入 → 释放叶子 W latch → 完成 ✔
  5. 若叶子不 safe → 释放全部 latch → 转悲观路径

【插入 Insert(key) —— 悲观路径】
  1. 对根取 W latch，记入 write-set 的「待定祖先」
  2. 循环：对子节点取 W latch → 若子节点 safe 则释放所有祖先
  3. 到达叶子，插入
  4. 若溢出 → 分裂 → 中间键 push up 到父节点（父节点 latch 仍持有）
  5. 若父节点也溢出 → 级联分裂
  6. 释放所有 latch，清空 write-set

【范围扫描 Scan(lo, hi)】
  1. 用 Find 走到 lo 所在叶子，持有其 R latch
  2. 沿叶子链表向右：
       a. 对右兄弟取 R latch（no-wait 模式）
       b. 成功 → 释放左叶子的 R latch → 继续
       c. 失败 → 释放全部 R latch → 重试（或短暂退避）
  3. 到 hi 后释放
```

### 5.13 为什么「线程安全的数据结构」如此困难

讲义结论页（第 195 页）：

```
Making a data structure thread-safe is notoriously difficult in practice.
We focused on B+Trees, but the same high-level techniques are applicable
to other data structures.
```

困难的根源有三：

1. **正确性难以推理**：要同时考虑「结构不变量」与「并发交错」，人脑很难穷举。一个漏掉的释放时机可能在百万次运行后才触发。
2. **性能与正确性的张力**：粗粒度 latch 容易写对但慢；细粒度快但容易错。乐观协议用「重试」换并发，又引入了活锁风险。
3. **缺乏工具**：latch 没有 Lock Manager、没有死锁检测、没有事务回滚——一切靠**编码纪律**。这就是讲义反复强调 "coding discipline" 的原因。

**这些技术是可迁移的**：latch crabbing（沿路径增量加解锁）、no-wait 获取 + 重试、private write-set 回滚——这三者在跳表、哈希表、缓冲池映射表、乃至文件系统的目录树里都能用。

## 6. 代码示例

### 6.1 讲义原文示例

**Worker 与并发控制的定义**（`10-indexconcurrency.pdf` 第 4、7 页）：

```
We (mostly) assumed all the data structures that we have discussed so far
are single-worker.
  → Worker = Execution Context (i.e., Thread, Process)

A DBMS needs to allow multiple worker to safely access data structures to
take advantage of additional CPU cores and hide disk I/O stalls.

A concurrency control protocol is the method that the DBMS uses to ensure
"correct" results for concurrent operations on a shared object.
A protocol's correctness criteria can vary:
  → Logical Correctness: Can a worker see the data that it is supposed to see?
  → Physical Correctness: Is the internal representation of the object valid?
```

**Locks vs Latches**（第 10 页）：

```
Locks (Transactions)
  → Protect the database's logical contents from other transactions.
  → Held for transaction's duration.
  → Application is not responsible for rolling back changes.

Latches (Workers)
  → Protect the critical sections of the DBMS's internal data structure
    from other workers.
  → Held for operation duration.
  → Workers are responsible for rolling back changes.
```

**Latch 模式**（第 13 页）：

```
Read Mode
  → Multiple threads can read the same object at the same time.
  → A thread can acquire the read latch if another thread has it in read mode.

Write Mode
  → Only one thread can access the object.
  → A thread cannot acquire a write latch if another thread has it in any mode.
```

**TAS 自旋闩锁**（第 20–21 页）：

```cpp
// Approach #1: Test-and-Set Spin Latch (TAS)
// → Very efficient (single instruction to latch/unlatch)
// → Non-scalable, not cache friendly, not OS friendly.
// → Example: std::atomic<T>

std::atomic_flag latch;
⋮
while (latch.test_and_set()) {
    // Retry? Yield? Abort?
}
```

**CAS 指令**（第 25–26 页）：

```
Atomic instruction that compares contents of a memory location M to a
given value V
  → If values are equal, installs new given value V' in M
  → Otherwise, operation fails

__sync_bool_compare_and_swap(&M, 20, 30)
        ↑Address  ↑Compare Value  ↑Exchange Value
```

**阻塞式 OS Mutex**（第 31–35 页）：

```cpp
// Approach #2: Blocking OS Mutex
// → Simple to use
// → Non-scalable (about 25ns per lock/unlock invocation)
// → Example: std::mutex

std::mutex m;
⋮
m.lock();
// Do something special...
m.unlock();
```

其内部结构（第 35 页）：`pthread_mutex_t` → **futex** → **Userspace Latch + OS Latch**。

**读写闩锁**（第 40–42 页）：

```cpp
// Approach #3: Reader-Writer Latches
// → Allows for concurrent readers. Must manage read/write queues
//    to avoid starvation.
// → Can be implemented on top of spinlocks.
// → Example: std::shared_mutex

// 内部：pthread_rwlock_t = pthread_mutex_t + pthread_cond_t
// 状态：read 计数、write 标志
```

**哈希表 latching**（第 53–56 页）：

```
Easy to support concurrent access due to the limited ways workers access
the data structure.
  → All workers move in the same direction and only access a single
    page/slot at a time.
  → Deadlocks are not possible.

To resize the table, take a global write latch on the entire table
(e.g., in the header page).

Approach #1: Global Latch
  → Use a single latch to protect the entire data structure.
Approach #2: Page/Block Latches
  → Each page/block has an embedded reader-writer latch.
  → Workers acquire latch before accessing a page/block.
  → Release latch before moving to the next page/block.
Approach #3: Slot Latches
  → Each slot has its own latch.
  → Can use a single-mode latch to reduce meta-data and computational
    overhead.
```

**B+ 树并发的两个问题**（第 92 页）：

```
We want to allow multiple workers to read and update a B+Tree at the same time.
We need to protect against two types of problems:
  → Workers modifying the contents of a node at the same time.
  → One worker traversing the tree while another worker splits/merges nodes.
```

**Latch Crabbing 协议**（第 108–109 页）：

```
Protocol to allow multiple workers to access/modify B+Tree at the same time.
  → Get latch for parent
  → Get latch for child
  → Release latch for parent if "safe"

A safe node is one that will not split or merge when updated.
  → Not full (on insertion)
  → More than half-full (on deletion)

Find: Start at root and traverse down the tree:
  → Acquire R latch on child,
  → Then unlatch parent.
  → Repeat until we reach the leaf node.

Insert/Delete: Start at root and go down, obtaining W latches as needed.
Once a child node is latched, check if it is safe:
  → If child is safe, release all latches on ancestors.
  → Optimization: When at an inner node that is "safe" can release all
    latches on ancestors.
```

**乐观协议**（第 151–152 页）：

```
Most modifications to a B+Tree will not require a split or merge.
Instead of assuming there will be a split/merge, optimistically traverse
the tree using read latches.
If a worker guesses wrong, repeat traversal with pessimistic algorithm.

Search: Same as before.
Insert/Delete:
  → Set latches as if for search, get to leaf, and set W latch on leaf.
  → If leaf is not safe, release all latches, and restart thread using
    previous insert/delete protocol with write latches.

This approach optimistically assumes that only leaf node will be modified;
if not, R latches set on the first pass to leaf are wasteful.
```

**叶子扫描的死锁**（第 193 页）：

```
Latches do not support deadlock detection or avoidance. The only way we
can deal with this problem is through coding discipline.

The leaf node sibling latch acquisition protocol must support a "no-wait"
mode.

The DBMS's data structures must cope with failed latch acquisitions.
  → Usually transparent to end-user / application.
```

**写操作的 write-set**（第 194 页）：

```
Each worker keeps of leaf node modifications in its private write-set
during an operation.
  → List of node identifiers with keys inserted/deleted.

A worker holds write latches on modified nodes until it finishes that
operation.
  → Ensures consistency by never exposing partial updates to other threads.

If a worker cannot acquire a write latch on a node:
  → Rollback modifications found in its write-set.
  → Abort the operation by releasing all latches.
```

**Project #2 与四个 Task**（第 197–200 页）：

```
You will build a thread-safe B+tree backed by your buffer pool manager.
  → Page Layout
  → Insert/Delete/Find Operations
  → Iterator
  → Latch Crabbing
We define the API for you. You need to provide the method implementations.
WARNING: This is more difficult than Project #1. Start immediately!

Task #1: Page Layouts
  → How each node will store its key/values in a page.
  → Leaf nodes include tombstones of deleted keys to delay merges.
  → You only need to support unique keys.
Task #2: Operations
  → Support point queries (single key).
  → Support inserts with node splitting.
  → Support removal of keys with sibling stealing + merging.
  → Does not need to be thread-safe.
Task #3: Index Iterator
  → Create a STL iterator for range scans on leaf nodes.
  → You only need to support ascending scans.
Task #4: Concurrent Index
  → Introduce latch crabbing/coupling protocol to support safe
    concurrent operations.
  → Make sure you have splits / merges working correctly before
    proceeding with this task.

DEVELOPMENT HINTS
  → Follow the textbook semantics and algorithms.
  → Set the page size to be small (e.g., 512B) when you first start so
    that you can see more splits/merges.
  → Make sure that you protect the internal B+Tree root_page_id member.
```

### 6.2 补充示例（非官方，仅用于说明概念）

**用 `std::atomic_flag` 实现 TAS 自旋闩锁**：

```cpp
class SpinLatch {
    std::atomic_flag flag_ = ATOMIC_FLAG_INIT;
public:
    void Lock() {
        int spins = 0;
        while (flag_.test_and_set(std::memory_order_acquire)) {
            // 讲义留的三个问号：Retry / Yield / Abort
            if (++spins > 100) { std::this_thread::yield(); spins = 0; }
        }
    }
    void Unlock() { flag_.clear(std::memory_order_release); }
};
```

`memory_order_acquire` / `release` 保证临界区内的读写不会被重排到闩锁之外——这是编译器层面的正确性，很容易漏。

**用 CAS 做无锁线性探查插入**：

```cpp
bool InsertLatchFree(Slot* table, size_t cap, Key k, Value v) {
    size_t i = hash(k) % cap;
    for (size_t probes = 0; probes < cap; ++probes, i = (i + 1) % cap) {
        Slot expected{};
        Slot desired{k, v};
        // 只有槽仍为空时才写入；失败说明被别人抢先，继续下一个槽
        if (table[i].CAS(expected, desired)) return true;
        if (table[i].key == k) return false;   // 键已存在
    }
    return false;                              // 表满
}
```

这正是讲义提到的「用 CAS 直接做 latch-free 线性探查」——`CAS` 失败**天然等价于**「该槽被占用，继续探查」，语义完美契合。

**简化版 latch crabbing（读路径）**：

```cpp
// 非官方伪代码，仅示意协议结构
Value* Find(Node* root, Key k) {
    Node* cur = root;
    cur->RLatch();                       // 对根取 R
    while (!cur->is_leaf) {
        Node* child = cur->child_for(k);
        child->RLatch();                 // ① 先取子
        cur->RUnlatch();                 // ② 再放父（读不需要 safe 判断）
        cur = child;
    }
    Value* v = cur->lookup(k);
    cur->RUnlatch();
    return v;
}
```

注意顺序：**先取子、后放父**。反过来就会出现「手里什么都没有」的悬空窗口。

**乐观插入的骨架**：

```cpp
bool InsertOptimistic(Node* root, Key k, Value v) {
    // 第一趟：全程 R latch，只在叶子升级为 W
    std::vector<Node*> path;
    Node* cur = root; cur->RLatch(); path.push_back(cur);
    while (!cur->is_leaf) {
        Node* child = cur->child_for(k);
        child->RLatch();
        cur->RUnlatch();                 // 按 Find 协议释放父
        path.back() = child;             // 只保留当前节点
        cur = child;
    }
    cur->WUpgrade();                     // 叶子 R → W
    if (cur->is_safe_for_insert()) {     // 未满
        cur->insert(k, v);
        cur->WUnlatch();
        return true;
    }
    cur->WUnlatch();                     // 不 safe：放弃，走悲观路径
    return InsertPessimistic(root, k, v);
}
```

`is_safe_for_insert()` 就是「未满」。失败时**必须释放全部 latch 再重来**，不能带着叶子 W latch 去改父节点（父节点已经放开，无法安全修改）。

**叶子水平扫描的 no-wait 重试**：

```cpp
void Scan(Node* leaf, Key lo, Key hi) {
    leaf->RLatch();
    Node* cur = leaf;
    while (cur) {
        for (auto& e : cur->entries) if (e.key >= lo && e.key <= hi) emit(e);
        if (cur->next == nullptr) break;
        // 关键：no-wait 获取右兄弟；失败则放弃重试，绝不干等
        if (!cur->next->RTryLatch()) {
            cur->RUnlatch();             // 释放全部已持有
            std::this_thread::yield();
            return Scan(leaf, lo, hi);   // 从头重试（可加退避）
        }
        cur->RUnlatch();                 // 拿到兄弟后才放当前
        cur = cur->next;
    }
    cur->RUnlatch();
}
```

这个骨架体现了三条纪律：**no-wait**、**拿到下一个才放上一个**、**失败整体重试**。

**private write-set 的回滚**：

```cpp
struct WriteSet {
    struct Entry { Node* node; std::vector<Key> inserted, deleted; };
    std::vector<Entry> entries;

    void Rollback() {                     // 反向撤销，对用户透明
        for (auto it = entries.rbegin(); it != entries.rend(); ++it) {
            for (Key k : it->inserted) it->node->remove(k);
            for (Key k : it->deleted)  it->node->insert_raw(k);
        }
        entries.clear();
    }
};
```

回滚是**反向**执行（`rbegin` 到 `rend`），因为插入与删除可能作用于同一节点，顺序反了会出错。

## 7. 容易混淆的概念

| 概念对 | 区别 | 记忆要点 |
|---|---|---|
| Lock vs Latch | Lock 保护数据库内容、持整个事务、有 Lock Manager、需回滚；Latch 保护内存结构、持临界区、无集中管理、无需回滚 | 一个管逻辑，一个管物理 |
| Logical vs Physical Correctness | 前者「读到该读的数据」；后者「内部表示健全、无野指针」 | 本讲只管后者 |
| TAS 自旋 vs OS Mutex | 前者单指令、快、不可扩展、烧 CPU；后者 ~25 ns、简单、进内核 | 一个空转，一个挂起 |
| Reader-Writer Latch vs Mutex | 前者区分读写、允许并发读、需防饥饿；后者独占 | 一个分模式，一个不分 |
| Global / Page / Slot Latch | 粒度由粗到细，并行度由低到高，元数据开销由小到大 | 越细越快也越占空间 |
| Safe vs Unsafe 节点 | 插入看「未满」、删除看「多于半满」；safe 才能释放祖先 | 有余量才敢松手 |
| 悲观 vs 乐观 crabbing | 前者全程 W latch；后者全程 R + 叶子 W，失败重来 | 一个稳，一个快 |
| 垂直 crabbing vs 水平 crabbing | 前者自上而下（无死锁）；后者叶子间左右移动（可能死锁） | 一个顺树，一个顺链 |
| Wait vs Abort-ourself | 前者可能永久互等（无死锁检测）；后者释放重试，唯一可行 | 干等必死，退让求生 |
| Latch vs 事务回滚 | latch 失败靠 write-set 局部撤销；事务失败靠 WAL/undo | 一个局部，一个全局 |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Slides | `90-原始PDF/15-445/slides/10-indexconcurrency.pdf` | 202 | 2（Project #1 due Sept 27、HW#3 due Oct 4、DRC #1 Oct 5 含 P0/P1、期中 Oct 7 覆盖 L01–11、study guide 见 Piazza @85）、4–6（单 worker 假设与 "They Don't Do This!"）、7（并发控制协议与两种正确性）、9（今日议程）、10–12（Locks vs Latches 表，来源 Graefe TODS 2010）、13（Latch 两模式与兼容矩阵）、14（四个实现目标，来源 Filip Pizlo）、17（三种实现 + 四种高级方案）、20–21（TAS 与 `std::atomic_flag` 代码）、25–29（CAS 与 `__sync_bool_compare_and_swap`）、31–35（`std::mutex` / `pthread_mutex_t` / futex 双层结构）、40–52（读写闩锁：`pthread_rwlock_t` = mutex + cond、读写计数动画）、53–56（哈希表 latching 与三种粒度）、57–76（Page latch 动画：T1 Find D / T2 Insert E）、77–91（Slot latch 动画）、92（B+ 树两个并发问题）、93–107（T1 Delete 44 与 T2 Find 41 的不一致）、108–109（crabbing 三步、safe 判据、Find 与 Insert/Delete 协议）、110–118（Example #1 Find 38）、119–129（Example #2 Delete 38）、130–137（Example #3 Insert 45）、138–148（Example #4 Insert 25 触发分裂）、149–150（根节点写锁瓶颈）、151–152（乐观算法）、153–161（乐观 Delete 38 成功）、162–163（乐观 Insert 25 失败重来）、164（top-down 与水平移动的问题）、165–171（叶子扫描 Example #1）、172–180（Example #2 两读者）、181–192（Example #3 死锁与 T2 三选择，仅 "Abort ourself" 高亮）、193（no-wait 模式与编码纪律）、194（private write-set）、195（结论）、196（下讲：查询执行）、197–201（Project #2 与四个 Task、开发提示、extra credit）、202（抄袭警告：禁用生成式 AI） |
| Notes | `90-原始PDF/15-445/notes/10-indexconcurrency.pdf` | 6 | 第 1 页（单线程模型与 Redis 论、读写锁保护整表的问题、并发控制协议定义、Logical vs Physical Correctness、Locks vs Latches 表）、第 2 页（Latch 两模式、四个实现目标、TAS 自旋闩锁与 CAS、阻塞 OS mutex 与 futex、读写闩锁与饥饿策略）、第 3 页（高级 latch 实现、"should not write their own"、哈希表 latching 与三种粒度、CAS 无锁线性探查）、第 4 页（B+ 树两个问题、latch crabbing 三步与 safe 判据、Basic 协议的释放顺序建议）、第 5 页（乐观 crabbing 与 latch 升级、叶子扫描的水平 crabbing 与双向加锁死锁、no-wait 与三种选择）、第 6 页（private write-set 与回滚、B+ 树写操作的可撤销性） |

原始 URL：

- Slides：`https://15445.courses.cs.cmu.edu/fall2026/slides/10-indexconcurrency.pdf`
- Notes：`https://15445.courses.cs.cmu.edu/fall2026/notes/10-indexconcurrency.pdf`

> 待核实：讲义第 12 页 Locks 列底部标注 "Lecture #15"，指向后续事务并发控制讲次；本课程 2026 课表中第 15 讲是 Query Execution II，事务理论在第 18 讲（`17-concurrencycontrol.pdf`）。该标注可能是旧版课表遗留，建议人工核对。
> 待核实：Example #2（Delete 38）中判定「B 不 safe」的具体键数与树阶 m 未在抽取文本中明确给出（动画逐步显示），本笔记按「删除后恰好处于最小填充」解释，需人工核对 PDF 原图。
> 待核实：notes 提到「latch 升级（read→write upgrade）更复杂且可能需已持有祖先读 latch」，但未给出具体算法；不同实现的可行性差异较大。

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内，本讲内容对应 2025 年第 10 讲）

- 标题：Index Concurrency Control — Latches, Latch Crabbing, Leaf Node Scans（2025 年第 10 讲）
- URL：`https://www.youtube.com/watch?v=YgOvfXl6pss&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 年份：2025
- 时间戳：未核实，故不标注。

## 10. 本节复习

- 能默写 Locks vs Latches 的七行对比表，并解释为什么两者不能合并成一套机制。
- 能画出 latch 兼容矩阵，说明读读兼容的物理原因。
- 能说出 latch 实现的四个目标，并用它们解释 TAS 与 OS mutex 的取舍。
- 能解释 futex 的「用户态 latch + 内核 latch」双层结构为什么能兼顾快路径与阻塞。
- 能说明读写闩锁的三种饥饿策略，以及为什么需要等待队列。
- 能说出哈希表为什么不可能死锁（单向、单点、不回头），并比较三种粒度。
- 能默写 crabbing 三步，准确给出插入与删除时 safe 的判据。
- 能说明为什么 safe 之后可以释放**所有祖先**而不只是直接父节点。
- 能解释乐观 crabbing 消除了什么瓶颈，失败时为什么要「释放全部再重来」。
- 能说明叶子扫描为什么打破 top-down 顺序、为什么「等待」不可行、为什么只能 "Abort ourself"。
- 能复述 no-wait 协议的两条纪律：拿到下一个才放上一个、失败整体重试。
- 能说明 private write-set 记什么、为什么必须持 W latch 到操作结束、回滚为什么是反向的。

## 11. 自我检查

**Q1.** 为什么 DBMS 需要两套完全不同的机制（lock 与 latch）？如果只用 lock 会怎样，只用 latch 又会怎样？

<details><summary>参考答案</summary>

**两者的本质差异在于「生命周期」与「失败语义」**：

| 维度 | Lock | Latch |
|---|---|---|
| 隔离对象 | 事务 | Worker（线程/进程） |
| 保护内容 | 数据库逻辑内容 | 内存数据结构 |
| 持有时间 | 整个事务（可能几秒到几分钟） | 临界区（几十条指令） |
| 模式 | Shared / Exclusive / Update / Intention | Read / Write |
| 死锁 | 检测与解决（waits-for、超时、中止） | 规避（编码纪律） |
| 管理 | 独立 Lock Manager | 嵌在被保护结构里 |
| 失败 | 需要回滚（WAL/undo） | 局部撤销（write-set） |

**只用 lock 会怎样**：

- **性能崩溃**。事务锁有集中的 Lock Manager，每次加解锁要走哈希表查找、可能入等待队列、可能要检测死锁。一棵 4 层 B+ 树的点查要加 4 次锁，每次几十到几百纳秒，而整个查询可能只想读一个键。latch 的设计目标之一是「无争用时几条指令」，lock 做不到。
- **粒度不匹配**。锁的语义是「保护一行/一张表」，而 B+ 树的 latch 要保护「一个 8 KB 的节点」。用事务锁保护节点意味着把内部实现细节暴露给事务层。
- **无法嵌在数据里**。锁要百万级数量（每行一把），必须集中管理；latch 必须嵌在节点里（去中心化），否则节点访问都要查全局表。
- **持有时间过长**。事务锁要持到事务提交，会阻塞其他事务几秒；latch 只持几十条指令。

**只用 latch 会怎样**：

- **失去逻辑正确性**。latch 只保证「结构不崩」（physical correctness），不保证「读到该读的版本」（logical correctness）。两个事务并发更新同一行，latch 保护下两次写都不会破坏内存结构，但**后写会覆盖前写**（丢失更新），或者读到未提交的数据（脏读）。
- **无法回滚**。latch 的失败处理只是「把内存改回去」，没有持久化日志，无法撤销已经写到磁盘的修改。事务中止需要 WAL/undo，这是 latch 层不提供的。
- **无死锁检测**。latch 不记录持有者、不建 waits-for 图，两个线程互等就是永久死锁。事务层必须有检测机制。

**结论**：两套机制解决的是**不同层次**的问题。latch 是「让数据结构在多线程下不崩」的**物理层**机制；lock 是「让并发事务产生可串行化结果」的**逻辑层**机制。DBMS 必须同时具备——这正是讲义把「Physical vs Logical Correctness」单列出来的原因。

</details>

**Q2.** 请完整描述 latch crabbing 协议，并解释：为什么 safe 节点可以释放**所有祖先**而不只是直接父节点？乐观 crabbing 又优化掉了什么？

<details><summary>参考答案</summary>

**协议三步**：

```
1. Get latch for parent
2. Get latch for child
3. Release latch for parent if "safe"
```

**Safe 的判据**：节点在**本次更新**中不会 split / merge / redistribute。

- **插入**：节点**未满** → safe（插进去也不会溢出）。
- **删除**：节点**多于半满** → safe（删掉一个仍满足最少键数）。
- **读**：不需要判断（读不改结构）。

**Find 的协议**：从根开始，对子节点取 R latch，然后释放父节点，重复到叶子。因为读不会引起结构变更，拿到子节点后父节点就没有用了。

**Insert/Delete 的协议**：从根向下取 W latch；一旦某个子节点被 latch 且判定为 safe，就释放**所有祖先**的 latch。

**为什么 safe 可以释放所有祖先（而不只是直接父节点）**：

关键在于 safe 的定义是「**这个节点在本次更新中不会被分裂/合并**」。由此可以推出：

1. 本次操作**不会改变这个节点在父节点中的条目**（不会新增一个兄弟节点，也不会删除自己）。
2. 因此父节点的内容**不会因为这次操作而改变**。
3. 父节点不变 → 祖父节点也不需要变 → **一路向上都不需要变**。

所以「这个节点 safe」等价于「**从它到根的这一整条路径在本次操作中都不会被修改**」。祖先的 latch 只是为了防止「子节点结构变更时需要向上传播」——既然不会有变更传播，祖先的 latch 就是多余的，可以全部释放。

**反例**（讲义 Example #4，Insert 25）：F 已满 `[23,31]`，插入 25 会分裂 → F 不 safe → **必须保留父节点的 W latch**，因为分裂后要把中间键 push up 到父节点、并新增一个指向新节点的条目。若提前释放了父节点，就无法安全地完成这一步。

**乐观 crabbing 优化掉了什么**：

**问题**：悲观协议的第一步永远是「对根取 W latch」。所有并发更新在根上**完全串行化**——一棵树无论多大，同一时刻只有一个写操作能进行。讲义用三个并发的 Insert 45 / Delete 38 / Insert 25 演示了这个瓶颈（第 150 页）。

**洞察**：**绝大多数更新不会导致分裂/合并**。插入导致分裂的概率约为 1/(m-1)（只有叶子恰好满时才分裂），删除导致合并的概率更低。为极小概率的事件付出「每次都锁根」的代价极不划算。

**乐观协议**：

```
1. 像 Find 一样，一路取 R latch 下降到叶子（读者之间可并发）
2. 在叶子上取 W latch（或把 R 升级为 W）
3. 若叶子 safe（未满/多于半满）→ 直接完成 ✔
4. 若叶子不 safe → 释放全部 latch，改用悲观协议重来
```

**收益**：正常情况下所有 worker 都以**读模式**下降，彼此完全并发；只有真正落在同一个叶子上的写才会争用。根节点的瓶颈消失。

**代价**（讲义原文承认）："if not, R latches set on the first pass to leaf are wasteful"——失败时白走一趟，那一趟取的 R latch 全是浪费。但由于失败率低，**期望收益远大于期望损失**。

**为什么失败时必须「释放全部再重来」**：走到叶子时，沿途的祖先 latch 已按 Find 协议释放。既然叶子不 safe 意味着「需要修改父节点」，而父节点现在没有 latch 保护，就**无法安全修改**——所以只能放弃、从头用悲观协议重走一遍（这次沿途保留 W latch）。

**可选优化：latch 升级（upgrade）**。某些实现允许把叶子的 R latch 原地升级为 W latch，省掉「释放再重取」。但升级本身要等所有其他读者退出，两个线程同时想升级就可能死锁；且升级后祖先的 R latch 仍需持有。所以多数实现选择简单的「重来」。

</details>

**Q3.** 叶子节点扫描为什么会死锁？为什么「等待」和「中止对方」都不可行，只有「中止自己」可行？请描述 no-wait 协议的具体做法。

<details><summary>参考答案</summary>

**为什么会死锁**：

latch crabbing 的垂直协议是 **top-down** 的：所有 worker 都按「根 → 叶」的同一方向获取 latch。树本身是有向无环的，因此**不可能形成环**——这是 crabbing 天然无死锁的根本原因。

**叶子扫描打破了这一点**。范围查询要沿叶子链表水平移动，方向变成「左 → 右」。于是可能出现：

```
T1（更新 Delete 4）：自上而下，持有父节点的 W latch，想要叶子 C 的 W latch
T2（扫描 Find Keys > 1）：持有叶子 B 的 R latch，想要右兄弟 C 的 R latch
```

若 C 上有 T1 的 W latch，T2 拿不到；而 T1 若要等 T2 释放 B（在某种情况下），就形成了环。讲义 Example #3 演示的正是这个场景（第 181–192 页），页面标注 "T2 does not know what T1 is doing…"。

更一般地说，**只要存在两种相反的加锁方向**（垂直向下 + 水平向右），就可能形成环。这与「哲学家就餐」是同一类问题。

**为什么「等待」不可行**：

等待的正确性依赖「对方最终会释放」。在 lock 的世界里，Lock Manager 会维护 waits-for 图、检测到环就中止一方。但 **latch 完全没有这些设施**：

- **没有集中管理器**：latch 嵌在数据结构里，没有一个组件知道全局的等待关系。
- **不记录持有者**：你无法查询「这个 latch 被谁持有」。
- **不检测环**：即使能查到，也没有算法去发现环。
- **不记录等待**：连「谁在等谁」都无从得知。

因此两个线程可以**永久互等**。讲义明确写："Latches do not support deadlock detection or avoidance."

**为什么「中止对方」不可行**：

- latch **不记录持有者**，你根本不知道要中止谁。
- 即使知道，中止别人意味着对方必须能**撤销已做的修改**——但对方的 write-set 是**私有**的，你无法访问；而且对方可能正处于临界区中间，强行中止会留下损坏的结构。
- 这是**越权**行为：latch 的语义是「保护自己的临界区」，不是「管理别人的执行」。

**为什么「中止自己」可行**：

- 你**知道自己做了什么**（private write-set），可以安全撤销。
- 你**知道自己持有哪些 latch**，可以全部释放。
- 释放后其他线程得以推进，你重试时可能就成功了——这是**打破环**的标准手段（与数据库的「wound-wait / wait-die」中的 wait-die 同思路：年轻者主动退出）。
- 代价是**活锁风险**（反复重试反复失败），但可以用退避（backoff）缓解，或由更高层的调度器介入。

**no-wait 协议的具体做法**：

```
取兄弟节点 latch 时，传入 no-wait 标志：
  → 成功：释放当前叶子的 latch，继续水平移动
  → 失败：立即释放所有已持有的 latch，放弃本次扫描，稍后重试
```

**三条必须遵守的纪律**：

1. **no-wait**：获取兄弟 latch **绝不允许阻塞等待**。这是打破死锁的唯一手段——只要没人等，就永远没有环。
2. **拿到下一个才放上一个**：在取得右兄弟 latch 之前，**绝不能释放当前叶子的 latch**（讲义第 169 页："Do not release latch on C until thread has latch on B"）。否则会出现「手里什么都没有」的窗口，别的线程可能趁机改掉 `cur->next` 指针，导致扫描走错位置或访问已释放节点。
3. **失败整体重试**：失败时释放**全部**已持有的 latch（不只是当前这个），然后从头开始（或从已知的安全点开始）。

**退避策略**：讲义 notes 提到可以「依已完成的工作量决定是否短暂等待一会」——若已经扫描了 90% 的数据，重来的代价高，可以短暂让出 CPU 后再试；若刚开始，立即重试更划算。

**高争用时**：应由**更高层的线程调度器**介入（例如检测到某 worker 反复失败就降低其优先级、或让它让出 CPU），但这**不属于数据结构实现的责任**。数据结构只能保证「不死锁、可重试、对用户透明」，公平性是调度层的事。

**这也解释了为什么 Project #2 的 Task #3 只要求「升序扫描」**——单向扫描只需要向右的兄弟指针，不需要同时支持左右双向遍历，减少了一半的死锁风险面。

</details>

**Q4.** 乐观 latch crabbing 在什么情况下会退化？如果一个工作负载是「持续往同一棵 B+ 树插入导致频繁分裂」，乐观协议还划算吗？请定量分析。

<details><summary>参考答案</summary>

**乐观协议的核心假设**：绝大多数更新不会引起分裂/合并。它的收益是「正常情况下全程 R latch，读者完全并发」；成本是「失败时白走一趟 + 重走悲观路径」。

**定量分析**：

设树阶为 m（每个节点最多 m-1 个键），叶子平均填充率为 f（0.5 ≤ f ≤ 1）。

**插入导致分裂的概率**：叶子有 (m-1)·f 个键，剩余空位 (m-1)(1-f)。随机插入落在某个特定叶子的概率是 1/(叶子数)，而该叶子「恰好满」的概率约为 `1/((m-1)(1-f) + 1)`。对典型参数 m=512、f=0.69：

```
剩余空位 = 511 × 0.31 ≈ 158
分裂概率 ≈ 1/159 ≈ 0.63%
```

即**约 99.4% 的插入不需要分裂**，乐观协议几乎总是成功。

**失败成本**：一次失败 = 白走一趟（O(log n) 次 R latch 取放）+ 重走一趟悲观路径（O(log n) 次 W latch）。相当于该次插入的 latch 开销变成约 2 倍，且悲观路径会短暂串行化。

**期望开销**：

```
E[cost] = 0.994 × C_optimistic + 0.006 × (C_optimistic + C_pessimistic)
        ≈ C_optimistic × 1.006 + 0.006 × C_pessimistic
```

对比纯悲观：`C_pessimistic`（每次都要在根上串行）。由于 `C_optimistic << C_pessimistic`（读 latch 可并发、写 latch 串行），乐观协议**即使算上失败重试也远优于悲观**。

**「持续插入导致频繁分裂」的极端情况**：

假设工作负载是**严格升序插入**（1, 2, 3, 4, ...）。这时：

- 所有插入都落在**最右边那个叶子**（"rightmost leaf"）。
- 该叶子被填满后分裂，新插入又落在新的最右叶子。
- 分裂频率 = 每 (m-1)(1-f) 次插入一次，仍是 **0.63%** 左右，**并没有显著升高**。

**关键洞察**：升序插入虽然「总是打同一个叶子」，但那个叶子分裂后会腾空一半，接下来 158 次插入都不会再分裂。所以**分裂率不变**，只是**热点集中在一个叶子**上——这是**争用**问题，不是**失败率**问题。

真正的退化场景是：

1. **树很浅且叶子很少**（例如只有 2–3 个叶子）：此时「随机插入」几乎必然落在同一个叶子，分裂率大幅上升。但这只发生在树极小的时候。
2. **m 很小**（例如 m=4，每个节点 3 个键）：剩余空位只有 1–2 个，分裂率高达 30–50%。讲义 Project #2 的开发提示正好提到「先把页大小设成 512B 以便看到更多分裂/合并」——小 m 时乐观协议明显不划算。
3. **删除密集且填充率接近 50%**：此时大量节点处于「恰好半满」，删除触发合并的概率大增。若工作负载是「插入到半满再删」，乐观协议会频繁失败。

**所以答案是**：

- **常规插入密集负载**：乐观协议仍然划算（分裂率约 1%）。
- **小 m 或填充率临界**：悲观协议可能更好，因为失败重试的浪费超过了并发的收益。
- **真正的瓶颈不是失败率而是争用**：升序插入让所有写落在最右叶子，此时无论乐观还是悲观，那个叶子都是串行点。解法不是改 latch 协议，而是：
  - **反向插入**（交替升降序）打散热点；
  - **预分裂（pre-splitting）**：批量加载时先按最终分布建树；
  - **B-link 树 / B^link 树**：用「右指针 + 高键」允许分裂期间的无锁读；
  - **乐观锁耦合（OLC）**：读路径完全不加 latch，靠版本号验证——这正是讲义第 17 页提到的 "Optimistic Lock Coupling (The Germans)"。

**实务上的判断准则**：乐观协议在「读远多于写」或「写但分裂罕见」时最优；在「写密集 + 小节点 + 填充率临界」时应改用悲观或 OLC。这也是为什么真实系统（如 PostgreSQL 的 nbtree）会根据操作类型与树状态动态选择策略，而不是固定一种协议。

</details>

**Q5.** 哈希表的并发比 B+ 树简单得多，为什么？如果把 B+ 树的 latch 粒度也做得和哈希表的槽级一样细（每个键一把 latch），会有什么问题？

<details><summary>参考答案</summary>

**哈希表为什么简单**：

讲义第 53 页给出三条理由：

1. **所有 worker 朝同一方向移动**：哈希函数直接算出目标位置，**不经过中间结构**。没有「逐层下降」的过程。
2. **一次只访问一个页/槽**：任一时刻只持有一个位置的 latch。
3. **从不回头**：线性探查只往后走，链地址只沿桶链前进，不会回到之前访问过的位置。

**推论：不可能死锁**。死锁需要「持有 A 等 B、持有 B 等 A」的环。既然每个 worker 在任一时刻只持有一个 latch，且获取顺序是「算出来的、单调的」，就不存在环。

**对比 B+ 树**：

- **必须逐层下降**：路径长度 O(log_m n)，每层都要 latch。这是「多节点同时持有」的根源。
- **更新要向上传播**：分裂/合并会修改父节点，甚至级联到根。这要求「持有子节点的同时持有父节点」，即**多 latch 嵌套**。
- **需要水平移动**：范围扫描沿叶子链表走，方向与垂直下降交叉 → 可能成环。
- **需要判断 safe**：因为要决定何时能释放祖先，这引入了「节点状态」的推理。

**如果把 B+ 树的 latch 做到键级（每键一把），会有什么问题**：

**① 元数据开销爆炸**。一把 latch 最少 1 字节（TAS）。一个 8 KB 的节点若装 512 个键，就要 512 字节的 latch 数组——占节点的 6.25%。而且 latch 数组本身要**原子访问**，会与键数组争缓存行。哈希表的槽级 latch 之所以可行，是因为**槽数相对少**且槽本身就是「一个值」；B+ 树的键是密集排列的，每个都配 latch 极其浪费。

**② 无法解决核心问题**。B+ 树并发的难点**不是**「两个线程改同一个键」，而是「一个线程分裂节点时另一个线程在遍历」。键级 latch 只解决前者，对后者毫无帮助——分裂会**搬移大量键**，涉及整个节点的结构重排，必须用**节点级**的排他 latch。所以键级 latch 无法替代节点级 latch，只能叠加，成本翻倍而收益有限。

**③ 分裂/合并的原子性无法保证**。分裂要把一个节点的后半部分键搬到新节点，并修改父节点。若每个键有独立 latch，就需要**同时持有几十上百把键 latch** 才能原子地搬移——这既昂贵又极易死锁（加锁顺序必须全局一致）。

**④ 缓存行乒乓（false sharing）**。相邻键的 latch 往往在同一个缓存行上。两个线程分别锁相邻的两个键，仍然会互相使缓存行失效——细粒度 latch 的收益被硬件层面的伪共享吃掉。这正是 MCS 锁等「cache-friendly」方案存在的原因。

**⑤ 指针/结构的完整性不在键的层面**。B+ 树的正确性依赖「节点内的键有序」「子指针与键的对应关系」「叶子链表指针」这些**节点级或结构级**的不变量。键级 latch 保护不了这些不变量——你锁住了键 25，但另一个线程可能正在重排整个节点的键数组。

**实务上的正确做法**（讲义与工业实践）：

- **节点级 latch** 是基本单位（这是 crabbing 的基础）。
- 想进一步提高并发，走的是**别的路线**：
  - **乐观锁耦合（OLC）**：读路径完全不加 latch，只在最后验证版本号（"The Germans" 的方案）。这把「读」的开销降到近零，而不是把 latch 变细。
  - **B-link 树 / B^link 树**：节点带「右指针 + 高键」，允许分裂期间读者继续前进（读到旧节点就沿右指针走），从而**消除读侧的 latch**。
  - **Bw-tree**：把节点变成「无锁的 delta 链」，写入是 CAS 追加 delta，后台再合并。这是把「细粒度」做到了极致，但代价是实现复杂度极高（讲义第 8 讲把它列为 B 树家族的一员）。
  - **分区（partitioning）**：把一棵大树拆成多棵小树（按 key range 分片），每棵树独立加锁。这是**用架构换并发**，比细粒度 latch 简单得多。

**结论**：哈希表简单是因为它的访问模式（单向、单点、无嵌套）天然无环；B+ 树复杂是因为它必须「逐层下降 + 向上传播 + 水平移动」。把 latch 做细并不能消除这些结构性难题——真正的解法是改变**协议**（OLC、B-link）或改变**架构**（分区），而不是改变**粒度**。

</details>

## 12. 进一步学习

- 上一讲：[[15-445-09-Indexes-and-Filters-II]] —— 布隆过滤器、跳表、Trie、倒排索引与向量索引。
- 下一讲：[[15-445-14-Query-Execution-I]] —— 终于开始讲查询执行（2026 课表第 14 讲；第 12 讲 DRC 无课，第 13 讲为 Joins）。
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]、[[40-CMU-15-445/04-学习进度|CMU 15-445 - 学习进度]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：Goetz Graefe, *A Survey of B-Tree Locking Techniques*, ACM TODS 2010 —— 讲义 Locks vs Latches 表的原始出处，也是 latch crabbing 的经典综述。
- 延伸阅读：Bayer & Schkolnick, *Concurrency of Operations on B-Trees* (1977) —— crabbing 协议的原始论文。
- 延伸阅读：Lehman & Yao, *Efficient Locking for Concurrent Operations on B-Trees* (1981) —— B-link 树，允许分裂期间无锁读。
- 延伸阅读：Levandoski, Lomet & Sengupta, *The Bw-Tree: A B-tree for New Hardware Platforms* (ICDE 2013) —— 无锁 delta 链。
- 延伸阅读：Mellor-Crummey & Scott, *Algorithms for Scalable Synchronization on Shared-Memory Multiprocessors* (TOPC 1991) —— MCS 锁，讲义列出的 queue-based spinlock。
- 延伸阅读：David, Guerraoui & Trigonakis, *Everything You Always Wanted to Know About Synchronization but Were Afraid to Ask* (SOSP 2013) —— 各种同步原语的实测对比。
- 动手建议：在 Project #2 之前，先写一个单线程的 `std::map` 包装，用 `std::shared_mutex` 保护，测出 8 线程读、1 线程写的吞吐；再换成 `std::mutex` 对比。这能直观感受到读写锁在「读多写少」下的收益，也能体会 25 ns 的固定开销在多线程下的放大效应。
