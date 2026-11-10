---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: L19
topic: Two-Phase Locking
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 数据库
  - 并发控制
  - 两阶段锁
  - 死锁
  - 意向锁
---

# 15-445 L19：两阶段锁（Two-Phase Locking）

> 上一讲给出了「正确调度」的判据——冲突可串行化；但优先图需要**预先知道整个调度**，在线系统做不到。这一讲的答案是：**用锁 + 一条协议规则（2PL）**，让 DBMS 在完全不知道未来会执行什么的情况下，自动产生只包含可串行化调度的执行。代价是**死锁**与**级联回滚**，于是又有了 Strict 2PL、等待-死亡、伤害-等待、意向锁这一整套工程方案。

## 1. 本节学习目标

学完本讲，你应该能够：

1. 说清 **Lock（锁）** 与 **Latch（闩锁）** 在保护对象、持有时间、模式、死锁处理上的六项差异。
2. 写出 **S-LOCK / X-LOCK** 的相容矩阵，并解释为什么 S-S 相容而 X 与任何模式都不相容。
3. 精确陈述 **两阶段锁（2PL）** 的两个阶段，并说明为什么 2PL 产生的调度一定是冲突可串行化的。
4. 说明 **2PL 的两种病**：**级联回滚（cascading aborts）** 与 **死锁（deadlock）**，以及 **Strict 2PL / Strong Strict 2PL** 如何消除前者。
5. 定义并区分 **Recoverable / ACA / Strict / Rigorous** 四类调度性质，说明它们与 2PL 变体的对应关系。
6. 用 **等待图（waits-for graph）** 检测死锁，列出**受害者选择（victim selection）**的常见启发式，并解释 **Wait-Die / Wound-Wait** 为什么能预防死锁。
7. 解释**锁粒度（lock granularity）**的权衡，并正确使用 **IS / IX / SIX 意向锁**及其相容矩阵与**加锁协议**。
8. 在 SQL 层面使用 `SELECT ... FOR UPDATE` 与 `SKIP LOCKED` 给出并发提示。

## 2. 前置知识

- **冲突可串行化与优先图**：见 [[15-445-18-Concurrency-Control-Theory]]，本讲的一切结论都建立在「无环优先图 = 正确」之上。
- **事务的边界**：`BEGIN` / `COMMIT` / `ABORT` 的语义，见 [[15-445-02-Modern-SQL]]。
- **闩锁与缓冲池**：latch 如何保护页与页表，见 [[15-445-04-Memory-Management]]。
- **B+ 树并发**：latch crabbing 是「latch 版本的 2PL」，见 [[15-445-10-Index-Concurrency-Control]]。
- **C++ 提醒**：本课程项目用 **C++17**、**Google C++ Style** 与 clang-format；Project #4 的 Lock Manager 需要实现 `LockShared` / `LockExclusive` / `LockUpgrade` / `Unlock`、`std::condition_variable` 等待队列与环检测，建议先熟悉条件变量与 `std::lock_guard`。

## 3. 核心概念

### 3.1 Lock（锁）

保护**数据库内容**（tuple、page、table、database）的逻辑锁，由 **Lock Manager（锁管理器）** 统一管理，**持续整个事务**，模式有 Shared / Exclusive / Update / Intention 四种。死锁由**检测或预防**处理。

### 3.2 Latch（闩锁）

保护**内存数据结构**（页、页表、索引节点）的低层同步原语，由**数据结构自身**持有，**只在临界区内**有效，模式只有 Read / Write 两种。死锁靠**编码纪律**（如固定加锁顺序）避免。

### 3.3 S-LOCK（共享锁）

Shared Lock，用于**读**。多个事务可同时持有同一对象的 S 锁（S-S 相容），因为读不改变值。

### 3.4 X-LOCK（排他锁）

Exclusive Lock，用于**写**。同一时刻只能有一个事务持有，且与 S 锁互斥（X 与任何模式都不相容）。

### 3.5 Two-Phase Locking（两阶段锁）

一个**运行时**并发控制协议：**增长阶段（growing phase）** 事务不断申请锁，可以升级（S→X）；**收缩阶段（shrinking phase）** 事务只能释放或降级锁，**不能再申请或升级**。协议不需要预先知道事务会执行哪些查询。

### 3.6 Cascading Aborts（级联回滚）

在纯 2PL 下，事务可以在提交前释放锁，于是别的事务可能读到**未提交**的数据（脏读）。若前者回滚，后者必须跟着回滚——一个回滚引发一串回滚。

### 3.7 Deadlock（死锁）

**事务等待锁的环**：T1 持有 A 等 B，T2 持有 B 等 A。两个事务都无法推进，必须由 DBMS 介入打破。

### 3.8 Waits-For Graph（等待图）

死锁检测用的有向图：节点是事务，若 Ti 正在等待 Tj 释放锁，则画边 `Ti → Tj`。**有环即死锁**。

### 3.9 Wait-Die / Wound-Wait（等待-死亡 / 伤害-等待）

两种基于**时间戳优先级**的死锁**预防**方案：老事务（时间戳小）优先级高。Wait-Die 是「老的等，年轻的死」；Wound-Wait 是「老的伤害（回滚）年轻的，年轻的等」。

### 3.10 Intention Lock（意向锁）

加在**高层节点**上的标记锁，表示「我的某个后代节点正被显式加锁」。三种：**IS**（后代有 S 锁）、**IX**（后代有 X 锁）、**SIX**（本节点整体 S + 后代有 X）。

### 3.11 Lock Escalation（锁升级）

当事务在低层节点上积累了太多锁时，DBMS 自动把它们合并成一个更粗粒度的锁，减少锁管理器的请求量。

## 4. 通俗理解

**锁**是「图书馆借书」：借走一本书（X 锁）别人就不能借也不能看；只想在馆内翻阅（S 锁）可以多人同时进行，但书被借走了就翻不了。

**2PL** 是「一次性把所有要用的书都借齐，然后才开始读，读的过程中一本本还，但绝不再借新书」。为什么这样就正确？因为如果两个事务都要同一本书，它们必然在「借书」阶段就撞上，谁先借到谁就先做——这个先后关系恰好构成了一个**全局一致的顺序**，等价于串行执行。

**级联回滚**是「你抄了我的作业，我发现我算错了撕掉重写，你的也得撕」。解决办法很简单：**作业交上去（提交）之前不许给别人看**——这就是 Strict 2PL。

**死锁**是「两个人各拿一把钥匙，都在等对方手里那把开门」。有两种处理：定期去走廊看有没有这种互相等待的环（**检测**），或者一开始就规定「只有资历老的能拿钥匙，年轻的必须让」（**预防**）。

**意向锁**是「我在三楼某个房间看书（S 锁），我在三楼门口挂个牌子写『三楼有人在』（IS 锁）」。这样有人想「把整个三楼锁起来装修」（X 锁）时，只要看门口牌子就知道不行，不必挨个房间敲门。

## 5. 原理与推导

### 5.1 为什么必须用锁

上一讲的优先图判定需要**完整调度**，而在线系统是**流式**到达的：DBMS 不知道事务接下来会读写什么。所以需要一个**增量式**协议：每来一个操作就检查一次，局部决策累积起来保证全局正确。

**Observation（讲义原话）**：我们需要一种方法，在**不预先知道整个调度**的前提下，保证所有执行调度都是正确的（可串行化）。方案：用锁保护数据库对象。

### 5.2 Locks vs Latches：六项对照

| 维度 | Lock（锁） | Latch（闩锁） |
|---|---|---|
| 隔离对象 | 事务（Transactions） | 工作线程 / 进程（Workers） |
| 保护内容 | 数据库内容（Database Contents） | 内存数据结构（In-Memory Data Structures） |
| 持有时长 | 整个事务（Entire Transactions） | 临界区（Critical Sections） |
| 模式 | Shared、Exclusive、Update、Intention | Read、Write |
| 死锁处理 | 检测与解除（waits-for、超时、回滚） | 靠编码纪律避免（Avoidance） |
| 存放位置 | 锁管理器（Lock Manager） | 被保护的数据结构内部 |

（表格来源：Goetz Graefe。）记忆要点：**lock 是「逻辑的、跨语句的、可回滚的」；latch 是「物理的、语句内的、不可回滚的」**。

### 5.3 锁的生命周期

1. 事务**申请**锁（或申请升级）。
2. 锁管理器**授予（grant）或阻塞（block）** 请求。
3. 事务**释放**锁。
4. 锁管理器更新内部**锁表（lock table）**：记录谁持有什么锁、谁在等什么锁。

如果请求被阻塞，请求事务进入该锁的**等待队列**；锁被释放时，锁管理器按队列顺序唤醒相容的等待者。

### 5.4 相容矩阵

|  | S-LOCK | X-LOCK |
|---|---|---|
| **S-LOCK** | ✔ | × |
| **X-LOCK** | × | × |

推导：S 只读、不改变值，多个读者互不影响 → S-S 相容；X 会改变值，若与 S 并存则读者可能读到「半个修改」→ X 与一切互斥。

### 5.5 2PL 为什么正确（核心证明思路）

**2PL 规则**：事务的加锁/升级操作全部发生在**第一个解锁之前**（增长阶段），之后只能解锁/降级（收缩阶段）。

**定理**：任何满足 2PL 的调度都是**冲突可串行化**的。

**证明思路**：给每个事务定义它的**锁点（lock point）**——即它获得最后一个锁的时刻。若 Ti 与 Tj 有冲突操作且 Ti 的冲突操作在前，可以证明 **Ti 的锁点早于 Tj 的锁点**：

- 若冲突是 W-R 或 W-W（Ti 写、Tj 读/写），则 Ti 必须先拿到 X 锁并释放，Tj 才能拿到它的锁；Ti 释放意味着 Ti 已进入收缩阶段，故 Ti 的锁点已过，而 Tj 还在增长阶段，锁点在未来 → Ti 锁点 < Tj 锁点。
- 若冲突是 R-W（Ti 读、Tj 写），对称地 Tj 必须先等到 Ti 释放 S 锁 → Ti 锁点 < Tj 锁点。

于是「按锁点排序」就是一个**拓扑序**，优先图不可能有环。**按锁点顺序串行执行**即为等价串行调度。

这个证明的关键是：**2PL 把「冲突顺序」与「锁点顺序」绑定成了同一个全序**。

### 5.6 2PL 的病一：级联回滚

纯 2PL 允许在事务**提交前**释放锁。考虑：

```
T1: X-LOCK(A) X-LOCK(B) R(A) W(A) UNLOCK(A) R(B) W(B) ... ROLLBACK
T2:                          X-LOCK(A) R(A) W(A) ...
```

T1 释放 A 后 T2 读到 T1 写的 A（**脏读**）。T1 最终 `ROLLBACK`，T2 基于脏数据做的所有计算都必须撤销——**T2 白干了**。若 T2 又把数据写给别人读，回滚会继续传染，形成**级联回滚（cascading aborts）**。

本质问题：**未提交的信息泄漏到了外部世界**，而任何已经发生的计算都必须能回滚。

### 5.7 四类调度性质

| 性质 | 定义 | 消除的问题 |
|---|---|---|
| **Recoverable（可恢复）** | 事务只在「它所读脏对象的所有写入者」都成功提交后才提交 | 不可恢复（回滚已提交事务） |
| **Avoids Cascading Aborts（ACA）** | 事务只能读**已提交**事务写过的对象 | 级联回滚 |
| **Strict（严格）** | 事务不能读**或写**一个对象，直到上一个写它的务提交/中止 | 脏读 + 脏写 |
| **Rigorous（严谨）** | 事务不能读或写一个对象，直到**最后一个**读或写它的务提交/中止 | 更强的隔离 |

包含关系：`Recoverable ⊃ ACA ⊃ Strict ⊃ Rigorous`（越往下越强）。

### 5.8 2PL 的三个变体

| 变体 | 规则 | 保证的调度性质 |
|---|---|---|
| **Strict 2PL（S2PL）** | 所有 **X 锁**持有到 commit/abort | Recoverable + ACA + Strict |
| **Strong Strict 2PL（SS2PL）** | **S 锁与 X 锁都**持有到 commit/abort | Recoverable + ACA + Strict + Rigorous |
| **Rigorous 2PL** | 所有锁持有到 commit/abort（实践中与 SS2PL 相同） | 同上 |

**SS2PL 的锁数量曲线**：增长阶段单调上升，到事务结束（commit/abort）时**一次性全部释放**——收缩阶段退化为一个点。

**代价**：SS2PL 只允许冲突可串行化的调度，但对某些负载**比必要的更强**。比如只读事务本可以早释放 S 锁，SS2PL 却要求它持有到结束，降低了并发度。这是「正确性 vs 并发度」的典型权衡。

### 5.9 反面教材：非 2PL 调度丢钱

初值 `A = 1000, B = 1000`（总和 2000）。

- **T1**：从 A 转 $100 到 B。
- **T2**：求所有账户总额。

**非 2PL 执行**：T1 依次 `X-LOCK(A) R(A) A=A-100 W(A) UNLOCK(A)`，然后 `X-LOCK(B) ...`；T2 在中间 `S-LOCK(A) R(A) UNLOCK(A) S-LOCK(B) R(B) UNLOCK(B)`。

结果 T2 读到 `A = 900`（已扣）与 `B = 1000`（还没加），返回 **`A + B = 1900`**——凭空少了 $100。T2 的优先图有环，不是冲突可串行化的。

**2PL 执行**：T1 在 `UNLOCK(A)` **之前**先 `X-LOCK(B)`（增长阶段同时持有 A、B 的锁）；T2 的 `S-LOCK(A)` 被阻塞，直到 T1 全部完成。T2 要么看到 `(1000, 1000)`，要么看到 `(900, 1100)`，**总和永远是 2000**。

这个例子是理解 2PL 为什么必须「先全部加锁、再解锁」的最好素材：**问题出在 T1 的解锁与下一次加锁之间留出了窗口**。

### 5.10 2PL 的病二：死锁

```
T1: X-LOCK(A) R(A) ... X-LOCK(B)   ← 等 T2 释放 B
T2: S-LOCK(B) R(B) ... S-LOCK(A)   ← 等 T1 释放 A
```

等待环形成，两者永远阻塞。**2PL 保证可串行化，但不保证不饿死**。

处理死锁有两条路：

#### 路线 A：死锁检测（Deadlock Detection）

维护 **waits-for graph**：节点是事务，若 Ti 在等 Tj 释放锁则画 `Ti → Tj`。**系统周期性检查是否有环**，有环就选一个**受害者（victim）**回滚以打破环。

- **检查频率的权衡**：检查太频繁浪费 CPU；检查太稀疏则事务白等很久。
- **受害者选择启发式**：按年龄（时间戳最小/最大）、按进度（已执行查询最少/最多）、按已持锁数量、按需要连带回滚的事务数；还要考虑**该事务历史上被重启过多少次**以防**饿死（starvation）**。
- **回滚长度**：① **完全回滚**（整个事务撤销并告知应用）；② **部分回滚**（回滚到某个 **savepoint**，然后重放被撤销的查询）。

#### 路线 B：死锁预防（Deadlock Prevention）

不加等待图，而是在**申请锁时**就杀掉一方。给每个事务在开始时分配**时间戳**作为优先级（例如**时间戳越小 = 优先级越高**）：

- **Wait-Die（「老的等，年轻的死」）**：若**申请者**优先级高于**持有者**，申请者**等待**；否则申请者**中止**。
- **Wound-Wait（「老的伤害，年轻的等」）**：若**申请者**优先级高于**持有者**，则**持有者中止**并释放锁；否则申请者**等待**。

**为什么不会死锁**：事务只沿**一个方向**等待（Wait-Die 中只有老等新；Wound-Wait 中只有新等老），等待关系不可能成环。

**重启后的优先级**：仍用**原始时间戳**，否则事务可能被反复重启而**饿死**。

### 5.11 锁粒度与层次结构

**问题**：前面所有例子都是「一个对象一把锁」。若事务要更新**十亿条 tuple**，就要拿十亿把锁——而**加锁比加 latch 还贵**，即使锁空闲。

**锁粒度（granularity）** 的选择：属性？tuple？页？表？数据库？

**权衡**：**锁越少、粒度越粗 → 并发度低但开销小**；**锁越多、粒度越细 → 并发度高但开销大**。理想是「拿到事务需要的**最少**数量的锁」。

**数据库锁层次（lock hierarchy）**：

```
Database
 └── Table 1, Table 2, ...
      └── Page 1, Page 2, ... (以及 Attr 1..n)
           └── Tuple 1, Tuple 2, ...
```

讲义标注了各层的访问频率：Tuple 层 **Very Common**，Page 层 **Common**，Table 层 **Slightly Rare**，Database 层 **Rare**。

### 5.12 意向锁与加锁协议

**意图锁（intention lock）** 的作用：允许在高层次节点上加 S/X 锁，而**不必检查所有后代**。若某节点被加了意向模式，说明**有事务正在更低层显式加锁**。

| 模式 | 含义 |
|---|---|
| **IS（Intention-Shared）** | 后代节点将被加 **S** 锁 |
| **IX（Intention-Exclusive）** | 后代节点将被加 **X** 锁 |
| **SIX（Shared + Intention-Exclusive）** | 本节点整体以 **S** 模式被锁，同时后代将被加 **X** 锁 |

**相容矩阵**：

|  | IS | IX | S | SIX | X |
|---|---|---|---|---|---|
| **IS** | ✔ | ✔ | ✔ | ✔ | × |
| **IX** | ✔ | ✔ | × | × | × |
| **S** | ✔ | × | ✔ | × | × |
| **SIX** | ✔ | × | × | × | × |
| **X** | × | × | × | × | × |

读法：IS 最「弱」，与除 X 外全部相容；SIX 是「表级读 + 行级写」，与任何写意图都不相容；X 与一切互斥。

**加锁协议（locking protocol）**：

1. 每个事务在**层次中尽可能高的层**获取合适的锁。
2. 要在节点上取 **S 或 IS**，必须至少在其**父节点**上持有 **IS**。
3. 要在节点上取 **X、IX 或 SIX**，必须至少在其**父节点**上持有 **IX**。

**两层次示例**（表 R 的 tuple）：

- T1 读 DJ Cache 的记录：`IS(R)` + `S(tuple)`。
- T2 更新 bookie 的记录：`IX(R)` + `X(tuple)`。
- 若 T1 要**扫描整个 R 并更新其中一个 tuple**：`SIX(R)` + `X(某 tuple)`——这样 T2 的单 tuple 读（`IS(R)` + `S(tuple)`）会被 SIX 阻塞在表级，保证 T1 的扫描结果稳定；而 T3 的全表扫描（`S(R)`）也被阻塞。
- 若只是三个事务分别「扫描+更新一个」「读一个」「全表扫描」，意向锁让它们能在**表级**快速判定冲突，而不必逐 tuple 比较。

**锁升级（lock escalation）**：当事务在低层积累了过多锁时，DBMS 自动换成更粗粒度的锁，减少锁管理器的请求量。

### 5.13 实践中的锁提示

应用通常**不手动加锁**（SQL 里没有通用的 `LOCK` 语句），但需要给 DBMS 提示以改善并发：

- **`SELECT ... FOR UPDATE`**：执行 SELECT 并对匹配的 tuple 加 **X 锁**（读后要更新时用，避免「读了再写」的窗口）。共享锁版本：PostgreSQL 用 `FOR SHARE`，MySQL 用 `LOCK IN SHARE MODE`。
- **`SELECT ... SKIP LOCKED`**：自动**跳过**已被不相容模式锁住的 tuple。用于在 DBMS 内部实现**队列**（多个 worker 抢任务，谁抢到算谁的，不排队等）。
- **显式锁**在大规模数据变更时也有用（例如维护操作期间锁表）。

## 6. 代码示例

### 6.1 官方课程代码

> 说明：本讲 **notes 未发布**（`90-原始PDF/15-445/notes/` 下无 `18-twophaselocking.pdf`），以下全部引自 slides。

**（1）Locks vs Latches 对照表**——`90-原始PDF/15-445/slides/18-twophaselocking.pdf` 第 7–8 页（来源标注 Goetz Graefe）。

**（2）锁管理器交互时序**——第 9–14 页（基本 `LOCK/UNLOCK` 与 Granted/Denied/Released 事件）、第 18–24 页（X-LOCK 与 S-LOCK 混合，含升级）。

**（3）相容矩阵**——第 16–17 页。

**（4）2PL 的增长/收缩阶段曲线**——第 26–29 页：`# of Locks` 对 `TIME` 的折线图，第 29 页标出 **"2PL Violation!"**（在收缩阶段又加锁）。

**（5）非 2PL 的反例**——第 49–64 页：`A=1000, B=1000`，T1 转账、T2 求和，第 64 页给出错误输出 **`A+B=1900`**。

**（6）2PL 的正例**——第 65–79 页（同样的场景，T1 在 `UNLOCK(A)` 前先 `X-LOCK(B)`）。

**（7）SS2PL 示例**——第 80–94 页：所有 `UNLOCK` 集中在 `COMMIT` 之前。

**（8）级联回滚**——第 40–43 页：T1 释放 A 后 T2 读 A，T1 `ROLLBACK`，第 43 页标注 **"Wasted work!"**。

**（9）四类调度性质定义**——第 44 页；**2PL 变体表**——第 45 页；**SS2PL 锁曲线**——第 46–47 页（"Release all locks at end of txn"）。

**（10）死锁与等待图**——第 95–98 页（"IT JUST GOT REAL" 的交叉等待）、第 100–104 页（T1/T2/T3 三事务等待图）。

**（11）受害者选择与回滚长度**——第 106–107 页。

**（12）Wait-Die / Wound-Wait**——第 109–115 页，第 112/114 页给出四种情形下的决策（"Wait-Die: T1 waits / Wound-Wait: T2 aborts" 等）。

**（13）锁层次与意向锁**——第 118–124 页（层次图、IS/IX/SIX 定义、五模式相容矩阵）、第 125 页（加锁协议三条规则）、第 128–153 页（两层次与三事务的完整示例）。

**（14）锁升级与实践提示**——第 154 页（lock escalation）、第 155–157 页（`FOR UPDATE`、`FOR SHARE` / `LOCK IN SHARE MODE`、`SKIP LOCKED` 的 SQL 语法）。

### 6.2 Agent 自行编写的教学示例

> 以下代码**非官方，仅用于说明概念**。

锁管理器的最小骨架（示意，非 BusTub 实现）：

```cpp
// 非官方示例：锁模式与请求
enum class LockMode { kShared, kExclusive };

struct LockRequest {
  txn_id_t txn_id;
  LockMode mode;
  bool granted{false};
};

class LockManager {
 public:
  // 申请锁：相容则立即授予，否则挂起（真实实现要用条件变量阻塞）
  bool Lock(txn_id_t tid, LockMode mode) {
    std::unique_lock<std::mutex> lk(latch_);
    auto &queue = table_[object_];
    // 检查当前已授予的锁是否与请求相容
    for (const auto &req : queue) {
      if (!req.granted) continue;
      if (req.mode == LockMode::kExclusive || mode == LockMode::kExclusive) {
        // 不相容：进入等待队列
        queue.push_back({tid, mode, false});
        return false;  // 调用方应阻塞等待
      }
    }
    queue.push_back({tid, mode, true});
    return true;
  }
};
```

2PL 的两种阶段在代码里的体现（伪代码）：

```cpp
// 非官方示例：Strict 2PL —— 只加锁不主动解锁，commit/abort 时统一释放
BEGIN;
  XLock(A);  Read(A); Write(A);   // 增长阶段
  XLock(B);  Read(B); Write(B);   // 仍可加锁
COMMIT;                            // 一次性释放所有锁（无收缩阶段）
```

Wait-Die 的判定逻辑（示意）：

```cpp
// 非官方示例：优先级 = 时间戳越小越高
bool ShouldWaitWaitDie(txn_id_t requester_ts, txn_id_t holder_ts) {
  // 申请者更老（优先级高）→ 等待；否则（更年轻）→ 中止
  return requester_ts < holder_ts;
}

bool ShouldAbortHolderWoundWait(txn_id_t requester_ts, txn_id_t holder_ts) {
  // 申请者更老 → 伤害持有者（回滚它）；否则等待
  return requester_ts < holder_ts;
}
```

意向锁的取锁顺序（示意）：

```cpp
// 非官方示例：想锁某个 tuple 的 X 锁，必须先沿路径拿 IX
IXLock(table);   // 父节点：有 X 意图
XLock(tuple);    // 叶子节点：真正的排他锁
// 释放顺序相反
Unlock(tuple);
Unlock(table);
```

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| Lock | Latch | lock 保护数据库内容、跨整个事务、可回滚；latch 保护内存结构、仅临界区、不可回滚 |
| 2PL | Strict 2PL | 前者允许提交前释放锁（会级联回滚）；后者要求 X 锁持有到事务结束 |
| Strict 2PL | Strong Strict 2PL | 前者只约束 X 锁；后者连 S 锁也持有到结束，额外保证 Rigorous |
| 死锁检测 | 死锁预防 | 检测是「先让它发生，再找环打破」；预防是「申请时按时间戳直接杀一方」，不需要等待图 |
| Wait-Die | Wound-Wait | 前者「老的等、年轻的死」；后者「老的杀、年轻的等」；两者等待方向都单向，故不死锁 |
| 锁粒度粗 | 锁粒度细 | 粗 = 锁少、开销小、并发低；细 = 锁多、开销大、并发高 |
| S 锁 | SIX 锁 | S 是「整棵子树只读」；SIX 是「整棵子树读 + 后代某处写」，因此 SIX 与 IX、S、SIX 都不相容 |
| 死锁 | 饿死（starvation） | 死锁是环，永远无法推进；饿死是「一直抢不到资源」，靠原始时间戳重排优先级避免 |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Slides | `90-原始PDF/15-445/slides/18-twophaselocking.pdf` | 158 | 4（上节回顾）、5（核心 Observation）、7–8（Locks vs Latches）、9–14 与 18–24（锁管理器时序）、16–17（相容矩阵）、25–29（2PL 定义与阶段曲线）、40–43（级联回滚）、44（四类调度性质）、45–47（2PL 变体）、49–64（非 2PL 反例，A+B=1900）、65–94（2PL 与 SS2PL 正例）、95–104（死锁与等待图）、105–107（受害者选择与回滚长度）、108–115（Wait-Die / Wound-Wait）、116–117（锁粒度权衡）、118–125（锁层次、意向锁、相容矩阵、加锁协议）、128–153（层次锁示例）、154（锁升级）、155–157（实践锁提示）、158（结论） |
| Notes | **缺失** | — | `90-原始PDF/15-445/notes/18-twophaselocking.pdf` 在官网与本地 `_scout` 中均不存在（截至 2026-11-10）。本讲第 6.1 节全部引用 slides。 |

原始 URL：

- Slides：`https://15445.courses.cs.cmu.edu/fall2026/slides/18-twophaselocking.pdf`
- Notes：`https://15445.courses.cs.cmu.edu/fall2026/notes/18-twophaselocking.pdf`（**待人工核对**：该 URL 目前返回 404，notes 尚未发布）

> 待核实：slides 第 2–8 页页眉仍写 "CMU DATABASE SYSTEMS (SPRING 2026)"，疑为模板未更新（课程实际为 Fall 2026）；第 2 页提到 "Project #3 is due Sunday Nov 15th"、"Homework #5 due Sunday Nov 22nd"，与 2026 课表一致。

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内，本讲内容对应 2025 年第 18 讲）

- 标题：Two-Phase Locking（2025 年第 18 讲）
- URL：`https://www.youtube.com/watch?v=drStlhNbfHI&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 年份：2025
- 时间戳：未核实，故不标注。

说明：FAQ Q11 明确 Fall 2026 的录像只对 CMU 学生开放，非 CMU 学习者应观看 Fall 2025 的公开视频。

## 10. 本节复习

- 能默写 Locks vs Latches 的六项差异。
- 能画出 S/X 相容矩阵并解释每一格的理由。
- 能精确陈述 2PL 的两个阶段，并说出「为什么 2PL 保证冲突可串行化」的证明思路（锁点全序）。
- 能构造一个纯 2PL 下的级联回滚例子。
- 能区分 Recoverable / ACA / Strict / Rigorous，并对应到 S2PL / SS2PL。
- 能对给定场景画出等待图并判定死锁。
- 能说清 Wait-Die 与 Wound-Wait 的判定规则，以及为什么它们不死锁。
- 能解释 IS / IX / SIX 的用途，并按加锁协议正确给出「读一个 tuple」与「扫全表并更新一个 tuple」的锁序列。

## 11. 自我检查

**Q1.** 纯 2PL 已经保证冲突可串行化了，为什么几乎所有真实 DBMS 用的都是 Strict 2PL 或 SS2PL？

<details><summary>参考答案</summary>

因为纯 2PL 只解决**正确性**，没解决**可恢复性与代价**：

1. **级联回滚**：纯 2PL 允许提交前释放锁，别的事务可能读到未提交数据。一旦写者回滚，所有读过它的事务都必须连带回滚——在长事务链上可能一次回滚几十个事务，吞吐骤降。
2. **不可恢复（non-recoverable）**：更糟的情况是读者已经提交了，写者才回滚。此时读者读到的是「从未存在过」的数据，而它已经提交、无法回滚，数据库进入不一致状态。
3. **Strict 2PL 只需一条规则**（X 锁持有到事务结束）就同时拿到 Recoverable + ACA + Strict，实现上比「追踪脏读依赖图」简单得多。
4. **SS2PL 再多拿一个 Rigorous**，而且实现更简单——事务结束时**一次性释放所有锁**，锁管理器不需要维护复杂的收缩阶段状态。

代价是并发度下降（只读事务也要持锁到结束），但工程上「简单 + 可恢复」远比「多几个并发」重要。所以实践中 SS2PL 是默认选择（MySQL InnoDB 在 `SERIALIZABLE` 下就是 SS2PL）。

</details>

**Q2.** 初值 `A=1000, B=1000`。T1 转账 $100（A→B），T2 求和。请说明非 2PL 调度为什么得到 `A+B=1900`，并给出 2PL 下的正确执行。

<details><summary>参考答案</summary>

**非 2PL 的执行**：

```
T1: X-LOCK(A) R(A)=1000 A=900 W(A) UNLOCK(A)   ← 此时 A 已提交可见为 900
T2:                                    S-LOCK(A) R(A)=900 UNLOCK(A)
T2:                                    S-LOCK(B) R(B)=1000 UNLOCK(B)  → 返回 1900
T1: X-LOCK(B) R(B)=1000 B=1100 W(B) UNLOCK(B) COMMIT
```

问题出在 T1 **先释放 A 锁、再去锁 B**：中间留出了一个窗口，T2 在这个窗口里读到了「A 已扣、B 未加」的**临时不一致**状态。虽然 T1 最终完成了转账，但 T2 已经基于中间状态给出了错误答案。

优先图：`T2 读 A` 与 `T1 写 A` 冲突 → `T1 → T2`；`T1 写 B` 与 `T2 读 B` 冲突 → `T2 → T1`。**有环**，不可串行化。

**2PL 的正确执行**：T1 在 `UNLOCK(A)` **之前**先 `X-LOCK(B)`，即增长阶段同时持有 A 和 B 的 X 锁：

```
T1: X-LOCK(A) X-LOCK(B) R(A) W(A) UNLOCK(A) R(B) W(B) UNLOCK(B) COMMIT
T2:                                                             S-LOCK(A) R(A) ...
```

T2 的 `S-LOCK(A)` 在 T1 释放前一直被阻塞。T2 要么在 T1 之前完成（读到 1000+1000=2000），要么在 T1 之后完成（读到 900+1100=2000）。**总和恒为 2000**。

注意：T1 只需要把「第二个 X 锁」提前到「第一个 UNLOCK」之前，不需要持有到 commit——这就是**纯 2PL**。若要防止级联回滚，则要升级为 **Strict 2PL**（X 锁持有到 commit）。

</details>

**Q3.** T1（时间戳 10，老）持有 A 的 X 锁；T2（时间戳 20，年轻）请求 A 的 S 锁。分别用 Wait-Die 与 Wound-Wait 说明会发生什么。

<details><summary>参考答案</summary>

前提：时间戳越小 = 越老 = 优先级越高，所以 **T1 优先级高于 T2**。

**Wait-Die（老的等，年轻的死）**：规则是「若**申请者**优先级高于**持有者**，申请者等待；否则申请者中止」。

这里申请者是 T2（年轻、优先级低），持有者是 T1（老、优先级高）。申请者优先级**不**高于持有者 → **T2 中止（abort）**，之后用**原始时间戳 20** 重启。

**Wound-Wait（老的伤害，年轻的等）**：规则是「若申请者优先级高于持有者，持有者中止；否则申请者等待」。

同样申请者 T2 优先级低 → **T2 等待**，直到 T1 释放 A。

**对比**：Wait-Die 下年轻事务会被反复中止（激进），Wound-Wait 下年轻事务排队等待（温和），但 Wound-Wait 可能让老事务「伤害」大量年轻事务导致它们白干。

**两者都不死锁**：Wait-Die 中等待关系只可能是「老等新」，Wound-Wait 中只可能是「新等老」，等待边方向单一，无法成环。

**重启必须用原始时间戳**，否则被中止的事务重启后拿到新（更年轻）的时间戳，会一直被中止，**饿死**。

</details>

**Q4.** 事务 T1 要「扫描表 R 的所有 tuple 并更新其中一个」，T2 要「读 R 中一个 tuple」，T3 要「扫描 R 的所有 tuple」。请给出各自的锁序列，并说明 T2 会不会被 T1 阻塞。

<details><summary>参考答案</summary>

**T1（扫描 + 更新一个）**：

```
SIX(R)          ← 表级：整体要读（扫描），同时后代要写
  X(tuple_k)    ← 行级：只对被更新的那个 tuple 加 X
```

用 **SIX** 而不是 `S(R) + X(tuple)`，是因为 SIX 一次性表达了「表级共享 + 行级排他」，避免先拿 S(R) 再升级（升级容易死锁）。

**T2（读一个 tuple）**：

```
IS(R)           ← 表级：后代要加 S 锁
  S(tuple_j)
```

**T3（扫全表）**：

```
S(R)            ← 表级：整表只读，不需要意向锁
```

**T2 会不会被阻塞**：查相容矩阵，`SIX` 与 `IS` **相容（✔）**，所以 T2 的 `IS(R)` 请求**不会被 T1 的 SIX(R) 阻塞**，T2 可以正常读 `tuple_j`。

但有一个例外：如果 `j == k`（T2 读的正好是 T1 要更新的那个 tuple），则 `S(tuple_j)` 会与 T1 的 `X(tuple_k)` 冲突，T2 在**行级**被阻塞。

**T3 会不会被阻塞**：`SIX` 与 `S` **不相容（×）**，所以 T3 的 `S(R)` 会被 T1 的 SIX(R) 阻塞。这是必要的——否则 T3 会在 T1 更新 tuple_k 的过程中扫到不一致的状态。

这正是意向锁的价值：**用表级的一个标记，快速判定「是否需要在行级等待」，而不必逐 tuple 检查**。

</details>

**Q5.** 死锁检测中，为什么「受害者选择」不能简单地总是选「已做工作最多的事务」或「已做工作最少的事务」？还要考虑什么？

<details><summary>参考答案</summary>

两种极端都有问题：

- **总选「做了最多工作」的事务回滚**：浪费最大（撤销的代价最高），而且这个事务往往是长事务，反复回滚会让它永远完不成 → **饿死**。
- **总选「做了最少工作」的事务回滚**：看起来代价最小，但如果某个短事务总是恰好卡在环里（例如它是高频的小查询），它会被反复回滚，同样**饿死**。

真实系统要综合考虑多个因素（讲义第 106 页列出的启发式）：

1. **年龄**（时间戳最小/最大）：老事务优先保护（它可能持有更多资源，回滚代价大）。
2. **进度**（已执行查询数最少/最多）：回滚代价估计。
3. **已持有锁的数量**：回滚后能释放多少资源。
4. **连带回滚的事务数**：避免一个回滚引发级联。
5. **历史重启次数**：这是防饿死的关键——**一个已经被回滚过很多次的事务应该被优先保护**，否则它会陷入「永远被选中」的循环。

此外还要决定**回滚长度**：完全回滚（简单、代价大）还是部分回滚到 savepoint 后重放（复杂、代价小）。InnoDB 的做法是回滚**最小代价**的事务（按修改的行数估计），并统计事务权重来抑制反复回滚。

</details>

## 12. 进一步学习

- 上一讲：[[15-445-18-Concurrency-Control-Theory]] —— 事务、ACID、冲突、优先图，本讲的理论基础。
- 下一讲：[[15-445-20-Timestamp-Ordering]] —— 不用锁的并发控制：时间戳排序、OCC、以及锁方案的固有开销。
- 相关：[[15-445-21-MVCC]] —— 多版本并发控制，读写不互相阻塞的另一种思路。
- 相关：[[15-445-10-Index-Concurrency-Control]] —— latch crabbing 是闩锁层面的 2PL，可对照理解。
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：教材 *Database System Concepts*（第 7 版）第 18 章「Concurrency Control Protocols」；Rosenkrantz、Stearns、Lewis 的 "System Level Concurrency Control for Distributed Database Systems"（1978）是 2PL 与 Wait-Die/Wound-Wait 的原始论文；Goetz Graefe 的 locks vs latches 对照表出自其数据库并发笔记。
- 动手建议：在 PostgreSQL 两个会话里执行 `SELECT * FROM t WHERE id = 1 FOR UPDATE;`，观察第二个会话阻塞；再用 `SELECT ... SKIP LOCKED` 观察它直接返回空行。用 `SELECT * FROM pg_locks` 查看锁表内容。
