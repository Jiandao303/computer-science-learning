---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: L18
topic: Concurrency Control Theory
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 数据库
  - 事务
  - ACID
  - 可串行化
  - 冲突可串行化
---

# 15-445 L18：并发控制理论（Concurrency Control Theory）

> 从这一讲开始，课程的重心从「单条查询怎么跑得快」转向「多个事务同时跑怎么保证正确」。这一讲几乎不讲实现，只讲**定义与判据**：什么是事务、ACID 各自靠什么机制实现、什么叫「一个调度是正确的」。后续的 2PL、时间戳排序、MVCC 全都是为了让调度满足这里的定义。

## 1. 本节学习目标

学完本讲，你应该能够：

1. 用形式化的语言定义**数据库（database）**、**事务（transaction）**、**调度（schedule）**，并说明事务的边界由谁定义（`BEGIN` / `COMMIT` / `ABORT`）。
2. 逐条解释 **ACID** 四性的含义，并指出每一性在 DBMS 里由哪类机制实现（日志 / 影子页 / 约束 / 并发控制协议）。
3. 区分**临时不一致（temporary inconsistency）**与**永久不一致（permanent inconsistency）**，并解释为什么 DBMS 只对后者负责。
4. 定义**冲突（conflict）**（不同事务、同一对象、至少一个写），并列举读-写、写-读、写-写三类冲突对应的异常。
5. 用**优先图（precedence graph / dependency graph）**判定一个调度是否**冲突可串行化（conflict serializable）**。
6. 说明**视图可串行化（view serializability）**比冲突可串行化更宽松（允许 blind write），以及为什么 DBMS 实践中不用它。
7. 画出调度集合的包含关系：`Serial ⊂ Conflict Serializable ⊂ View Serializable ⊂ All Schedules`，并说明 Recoverable / ACA / Strict 等性质的位置。

## 2. 前置知识

- **事务的 SQL 语法**：`BEGIN` / `COMMIT` / `ROLLBACK`、隔离级别，见 [[15-445-02-Modern-SQL]]。
- **缓冲池与磁盘**：为什么需要「未提交的修改先留在内存」、为什么要写日志，见 [[15-445-04-Memory-Management]]。
- **锁与闩锁的区别**：latch 保护内存数据结构，lock 保护数据库内容（本讲之后的第 19 讲会展开）。
- **并发编程基础**：竞态条件、原子性、可见性。
- **C++ 提醒**：本课程项目用 **C++17** 编写、遵循 **Google C++ Style** 并用 clang-format 格式化；Project #4 要用 `std::mutex`、`std::atomic`、条件变量实现锁管理器与事务管理器，建议先补内存序（memory order）基础。

## 3. 核心概念

### 3.1 Transaction（事务）

一个或多个操作在共享数据库上的**执行序列**，是变更的**基本单位**：不允许部分执行。要么全部生效，要么全部不生效。例：Andy 账户有 $100，付 $25 给 concert promoter——读余额、判断余额 > 25、扣 25、写回 75，这四步必须整体成功或整体失败。

### 3.2 ACID

- **Atomicity（原子性）**：全有或全无。事务的所有操作要么都生效，要么都不生效。
- **Consistency（一致性）**：每个事务单独执行时保持数据库一致；若初始状态一致，则事务结束后仍一致（数据满足 constraints / cascades / triggers）。
- **Isolation（隔离性）**：并发执行多个事务的结果，等价于**某种串行执行**的结果。
- **Durability（持久性）**：事务提交后，其效果必须在崩溃/重启后仍然存在。

### 3.3 Logging（日志）

有序的**账本**，记录事务做过的每个动作，以便撤销（undo）。内存与磁盘都保留 undo 记录，崩溃后重放日志恢复。**几乎所有现代 DBMS 都用它**实现原子性与持久性。

### 3.4 Shadow Paging（影子分页）

修改页的**副本**，commit 之前不覆盖原页；commit 后副本成为当前页，abort 时直接丢弃副本。崩溃恢复极快（删掉未提交的页即可），但运行时更慢、且并发控制困难。讲义明确标注 "Don't Do This!"。

### 3.5 Schedule（调度）

多个事务的操作按时间排列的**交错序列**。交错是必要的（I/O 慢、多核、应用暂停），但交错必须可控。

### 3.6 Serial Schedule（串行调度）

事务之间完全不交错：一个事务的全部操作执行完后，才开始下一个。

### 3.7 Serializable Schedule（可串行化调度）

与**某个串行调度**等价（对任意初始数据库状态，执行效果相同）。不同的串行顺序可能给出不同结果，但它们**都算正确**。

### 3.8 Conflict（冲突）

两个操作满足三个条件即为冲突：① 属于**不同事务**；② 访问**同一数据对象**；③ **至少有一个是写**。三类冲突：

- **Read-Write（读-写）**：导致**不可重复读（unrepeatable read）**。
- **Write-Read（写-读）**：导致**脏读（dirty read）**。
- **Write-Write（写-写）**：导致**丢失更新（lost update）**。

### 3.9 Conflict Serializability（冲突可串行化）

调度 S 是冲突可串行化的，当且仅当它与某个串行调度**冲突等价**（conflict equivalent）：两者涉及相同事务的相同操作，且每一对冲突操作的**相对顺序相同**。

### 3.10 Precedence Graph（优先图 / 依赖图）

节点是事务；若 Ti 的操作 Oi 与 Tj 的操作 Oj 冲突且 Oi 先于 Oj，则画边 `Ti → Tj`。**调度冲突可串行化 ⟺ 图无环**。

### 3.11 View Serializability（视图可串行化）

比冲突可串行化更**宽松**的可串行化：允许所有冲突可串行化的调度，**外加**包含 **blind write（盲写：不看原值直接写）** 的调度。允许更多调度，但难以高效实施（DBMS 不知道应用如何解释值），实践中不用。

### 3.12 Pessimistic vs Optimistic（悲观 vs 乐观）

并发控制协议的两大流派：**悲观**假定冲突会发生，提前用锁阻止；**乐观**假定冲突很少，先执行、提交时再检查。

## 4. 通俗理解

把数据库想成一本**共享账本**，事务是**同时动笔的多个会计**。

- **原子性** = 「一笔分录要么整笔写完，要么整笔划掉」。不能出现「借方写了、贷方没写」的半笔。
- **一致性** = 「借贷必须平衡」这条规则，任何时候都不能破。
- **隔离性** = 「每个会计都以为账本只有自己在写」。哪怕十个人同时在写，最终结果也要像他们**排队一个一个写**一样。
- **持久性** = 「记到账本上的，就再也不会消失」。哪怕当晚停电。

**交错**本身不是坏事：会计 A 在等打印机（I/O）时，会计 B 可以先写自己的分录——这就是**临时不一致**，只要最终账目对得上就没事。真正可怕的是**永久不一致**：比如「A 扣了钱但 B 没收到」，这种错误一旦落盘就再也修不回来。

**冲突可串行化**的判定就像**看有没有「互相等对方」的循环**：A 等 B 先写、B 等 C 先写、C 又等 A 先写——这个环一旦出现，就说明有人的操作顺序颠倒，结果不可能等价于任何排队顺序。

## 5. 原理与推导

### 5.1 为什么需要并发控制：两个动机问题

讲义用两个场景开场：

**问题一：丢失更新（Lost Update）**。Andy 账户 $100，两个并发事务都执行「读余额 → 判断 > 25 → 扣 25 → 写回」。两者都读到 $100，都判断通过，都写回 $75——结果只扣了一次 $25，但付了两次款。

**问题二：持久性（Durability）**。事务提交后机器崩溃，已提交的修改丢失。

这两个问题分别对应**并发控制**与**恢复**两条主线，它们渗透整个 DBMS 架构（从 Query Planning 到 Disk Manager 的每一层都要考虑）。

### 5.2 朴素方案为什么不行

**Strawman**：只用一个 worker 串行执行所有事务，并且每个事务开始时**复制整个数据库**（shadow paging），成功则新文件成为当前库，失败则丢弃旧副本。

三个致命缺点：

1. **慢**：每事务复制全库，代价与库大小成正比。
2. **无并行**：单 worker 浪费多核。
3. **空间爆炸**：同时存在两份全库副本。

所以必须允许并发，同时用协议保证正确性——这就是并发控制存在的理由。

### 5.3 临时不一致 vs 永久不一致

设不变量 `A + B = 2120`（A、B 各 $1000，之后都要加 6% 利息）。

- T1 从 A 转 $100 给 B，T2 给 A、B 各加 6%。允许的最终结果：`A = 954, B = 1166`（先转账后加息）或 `A = 960, B = 1160`（先加息后转账）。
- 如果交错过程中出现 `A = 954, B = 1160`（总和 $2114），那就**丢了 $6**——这是**永久不一致**，不可接受。
- 而执行中途出现 `A = 900, B = 1000`（转账扣了 A 还没加给 B）是**临时不一致**，只要最终恢复不变量就没问题。

结论：DBMS 只保证**最终状态**等价于某个串行执行，不保证每一瞬间都一致。

### 5.4 ACID 与实现机制的对应

| 性质 | 含义 | 实现机制 |
|---|---|---|
| **Atomicity** | 全有或全无 | Logging（undo 记录 + 崩溃重放）或 Shadow Paging |
| **Consistency** | 事务前后都满足约束 | SQL 完整性约束（`PRIMARY KEY`、`FOREIGN KEY`、`CHECK`）+ 应用逻辑；分布式场景还需复制协议 |
| **Isolation** | 等价于某个串行执行 | 并发控制协议（2PL、时间戳排序、MVCC、OCC） |
| **Durability** | 提交后不丢失 | Logging（redo 记录 + 强制刷盘）或 Shadow Paging |

关键洞察：**Atomicity 与 Durability 靠同一套日志机制**（undo 保原子、redo 保持久），**Consistency 主要靠约束与应用**，**Isolation 才是并发控制协议的战场**。

### 5.5 冲突与三类异常

| 冲突类型 | 记号 | 典型异常 | 场景 |
|---|---|---|---|
| Read-Write | R-W | 不可重复读（unrepeatable read） | T1 读 A，T2 改 A 并提交，T1 再读 A 得到不同值 |
| Write-Read | W-R | 脏读（dirty read） | T1 改 A 未提交，T2 读到 A 的新值，T1 回滚 |
| Write-Write | W-W | 丢失更新（lost update） | T1、T2 都基于旧值写 A，后写者覆盖前者 |

讲义还提到两类**后续讲才展开**的异常：**幻读（phantom read）**（Scan-Write 冲突，第 19 讲）与**写偏斜（write skew）**（R-W 冲突的特殊形态，第 20/21 讲）。

### 5.6 冲突可串行化的判定：优先图

**算法**：

1. 为每个事务建一个节点。
2. 对每一对冲突操作（Ti 的 Oi 与 Tj 的 Oj，Oi 在调度中先于 Oj），画边 `Ti → Tj`。
3. **图无环 ⟺ 冲突可串行化**；若有环，则不可串行化。

**例（讲义 example #3）**：T1 转账（读 A、写 A、读 B、写 B），T2 求和（读 A、读 B）。若 T2 在 T1 写 A 之后读 A、在 T1 写 B 之前读 B，则：

- T2 读 A 与 T1 写 A 冲突 → `T1 → T2`
- T1 写 B 与 T2 读 B 冲突 → `T2 → T1`

图有环 `T1 ↔ T2`，**不可串行化**。但注意：这个调度在实际业务上可能是「正确」的（T2 求的是转账过程中的中间和），而 DBMS **不理解语义**，只按冲突规则判定。这是「可串行化」作为判据的保守性来源。

**另一种判定法**：不断交换**相邻的非冲突操作**，直到形成串行调度。事务一多，交换的组合爆炸，代价过高——所以实践中用优先图（或等价的锁协议）。

### 5.7 视图可串行化与 blind write

两个调度 S1、S2 **视图等价（view equivalent）**的条件：

1. 若 T1 在 S1 中读了 A 的**初始值**，则 S2 中也读初始值。
2. 若 T1 在 S1 中读了 T2 写的 A，则 S2 中也读 T2 写的 A。
3. 若 T1 在 S1 中写了 A 的**最终值**，则 S2 中也写 A 的最终值。

**blind write** 的作用：若事务不看原值直接写（如 `SET balance = 100`），那么「读到什么」不重要，只有「最终写什么」重要。这类调度可能优先图有环，但视图等价于某个串行调度，因此**视图可串行化**。

为什么 DBMS 不用视图可串行化：判断它需要知道**应用如何解释读到的值**（哪些读是「有意义」的），而 DBMS 只有读写序列，没有语义信息。冲突可串行化只需看操作顺序，可以用锁/时间戳**在线**高效实施。

### 5.8 调度集合的包含关系

```
All Schedules
 └── View Serializable
      └── Conflict Serializable
           └── Recoverable
                └── ACA (Avoids Cascading Aborts)
                     └── Strict
                          └── Rigorous
                               └── Serial
```

（严格说 Serial 在最内层：串行调度必然满足所有性质。）

四层性质的定义：

- **Recoverable（可恢复）**：事务只在它所读数据的所有写入者都已提交后才提交。
- **ACA（避免级联回滚）**：事务只读**已提交**事务写的数据。
- **Strict（严格）**：事务既不读、也不写**未提交**事务写过的对象。
- **Rigorous（严谨）**：在 Strict 基础上，读锁也保持到事务结束。

这四层是第 19 讲 2PL 变体的理论基础：**Strict 2PL 保证 Recoverable + ACA + Strict**，**Strong Strict 2PL（SS2PL）再加 Rigorous**。

### 5.9 Durability 的要求

已提交事务的所有更改在崩溃/重启后必须持久，且**不允许 torn update**（半个页写成功、半个失败），也不允许失败事务的更改残留。实现手段：logging（WAL）或 shadow paging。通常要求**已提交事务的日志先于数据页写入非易失存储**（这就是 WAL 规则，第 22 讲展开）。

## 6. 代码示例

### 6.1 官方课程代码

**（1）好的交错与坏的交错**——`90-原始PDF/15-445/notes/17-concurrencycontrol.pdf` 第 4 页，Figure 1 "Good interleaving schedule" 与 Figure 2 "Bad interleaving schedule"：用 A、B 两个账户演示「总和不变」的不变量在两种交错下的不同结局。

**（2）依赖图示例**——同文件第 5 页，Figure 3 "Dependency Graph Example"：给出一个三事务调度的优先图，含环（不可串行化）的示例。

**（3）事务的形式化定义**——`90-原始PDF/15-445/slides/17-concurrencycontrol.pdf` 第 10 页：数据库是固定命名对象集合（A、B、C…，类型可为属性/tuple/页/表/库，但所有对象须同类型）；事务是读写操作序列（`R(A)`、`W(B)`）。

**（4）ACID 与两套原子性机制**——同 slides 第 11 页（ACID 定义）、第 13–15 页（Logging 与 Shadow Paging 的对比，Shadow Paging 标 "Don't Do This!"）。

**（5）三类冲突的时序图**——同 slides 第 31–33 页：读-写、写-读、写-写各给一个时序与结果。

**（6）优先图判定**——同 slides 第 35–39 页：conflict equivalent 定义、dependency graph 构造、三个示例（含 example #3 的环）。

**（7）视图可串行化与调度全集**——同 slides 第 40–44 页：view equivalent 三条件、blind write 示例、`All ⊃ View Serializable ⊃ Conflict Serializable ⊃ Recoverable ⊃ ACA ⊃ Strict ⊃ Rigorous ⊃ Serial` 的嵌套图。

### 6.2 Agent 自行编写的教学示例

> 以下代码**非官方，仅用于说明概念**。

用结构体表示一个调度，并检测优先图是否有环（示意）：

```cpp
// 非官方示例：优先图环检测
struct Operation {
  int txn_id;
  char kind;      // 'R' 或 'W'
  char object;    // 'A'、'B' ...
};

bool IsConflictSerializable(const std::vector<Operation> &sched) {
  std::set<std::pair<int, int>> edges;               // (from, to)
  for (size_t i = 0; i < sched.size(); i++) {
    for (size_t j = i + 1; j < sched.size(); j++) {
      const auto &a = sched[i], &b = sched[j];
      if (a.txn_id == b.txn_id) continue;             // 同一事务不算冲突
      if (a.object != b.object) continue;             // 不同对象不算冲突
      if (a.kind == 'R' && b.kind == 'R') continue;   // 读读不算冲突
      edges.insert({a.txn_id, b.txn_id});             // 其余都是冲突
    }
  }
  return !HasCycle(edges);                            // 无环 ⟺ 冲突可串行化
}
```

一个「丢失更新」的最小复现（伪代码，示意）：

```cpp
// 非官方示例：不加并发控制时两条 UPDATE 会丢一次
// T1: READ(A)=100; ... ; WRITE(A, 75)
// T2: READ(A)=100; ... ; WRITE(A, 75)   ← 两次付款只扣了一次钱
```

Logging 的 undo 记录形态（示意，对应第 22 讲的 WAL）：

```cpp
// 非官方示例：一条 undo 日志记录
struct LogRecord {
  int txn_id;
  char object;
  int old_value;    // undo 需要它
  int new_value;    // redo 需要它
};
```

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| 冲突可串行化 | 视图可串行化 | 前者只看冲突操作的顺序，可用优先图判定；后者还允许 blind write，更宽松但难以高效实施 |
| 临时不一致 | 永久不一致 | 前者在执行中途出现、最终会消失，可接受；后者落盘后无法修复，必须避免 |
| Atomicity | Durability | 前者保证「失败的事务不留下痕迹」（undo）；后者保证「成功的事务不丢失」（redo）；两者共用日志 |
| 串行调度 | 可串行化调度 | 前者**就是**不交错；后者**等价于**某个不交错，但实际是交错的 |
| 冲突 | 竞争条件 | 冲突是**形式化定义**（不同事务、同对象、有写）；竞争条件是**运行时现象**，冲突是它的抽象 |
| Latch | Lock | latch 保护内存数据结构、只在临界区持有；lock 保护数据库内容、持续整个事务（第 19 讲详述） |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Slides | `90-原始PDF/15-445/slides/17-concurrencycontrol.pdf` | 49 | 4（并发控制在架构中的位置）、5–8（动机与朴素方案）、9（两种不一致）、10（形式化定义）、11（ACID）、13–15（Logging vs Shadow Paging）、16（Consistency）、17–18（Isolation 两派）、19–24（转账+利息的例子）、25–29（调度定义）、30–33（冲突与三类异常）、34–39（两级可串行化与优先图）、40–44（视图可串行化与调度全集）、45–47（Durability 与 ACID 实现映射）、48（结论） |
| Notes | `90-原始PDF/15-445/notes/17-concurrencycontrol.pdf` | 5 | 第 1–3 页（丢失更新与持久性动机、事务定义、ACID、Logging vs Shadow Paging、冲突与可串行化）、第 4 页 Figure 1/2（好/坏交错）、第 5 页 Figure 3（依赖图示例） |

原始 URL：

- Slides：`https://15445.courses.cs.cmu.edu/fall2026/slides/17-concurrencycontrol.pdf`
- Notes：`https://15445.courses.cs.cmu.edu/fall2026/notes/17-concurrencycontrol.pdf`

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内，本讲内容对应 2025 年第 17 讲）

- 标题：Concurrency Control Theory（2025 年第 17 讲）
- URL：`https://www.youtube.com/watch?v=tMFAgvDViAI&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 年份：2025
- 时间戳：未核实，故不标注。

说明：FAQ Q11 明确 Fall 2026 的录像只对 CMU 学生开放，非 CMU 学习者应观看 Fall 2025 的公开视频。

## 10. 本节复习

- 能用一句话定义事务，并说明事务边界由谁定义。
- 能逐条解释 ACID，并指出每一条对应的实现机制。
- 能举例说明临时不一致与永久不一致的差别。
- 能列举三类冲突及其对应的异常名称。
- 能对给定的调度画出优先图，并判断是否冲突可串行化。
- 能解释 blind write 为什么让视图可串行化比冲突可串行化更宽松。
- 能默写调度集合的包含关系，并说明 Recoverable / ACA / Strict / Rigorous 的定义。
- 能说出 Durability 对「已提交日志必须先落盘」的要求。

## 11. 自我检查

**Q1.** 调度 `R1(A) W2(A) R1(A) C1 C2` 是否冲突可串行化？请画出优先图说明。

<details><summary>参考答案</summary>

**不是冲突可串行化的**。

逐步找冲突：

- `R1(A)`（第 1 个操作）与 `W2(A)`：不同事务、同对象 A、有一个写 → 冲突，且 `R1` 在前 → 边 `T1 → T2`。
- `W2(A)` 与 `R1(A)`（第 3 个操作）：不同事务、同对象、有一个写 → 冲突，且 `W2` 在前 → 边 `T2 → T1`。

优先图有 `T1 → T2` 与 `T2 → T1`，**成环**，故不可冲突可串行化。

从语义上看，这正是**不可重复读（unrepeatable read）**：T1 两次读 A 得到不同值（第一次读到初值，第二次读到 T2 写的值）。任何串行执行都不可能让 T1 在自己的生命周期内看到 A 变化（因为串行执行下 T2 要么全在 T1 前、要么全在 T1 后），所以确实不可能等价于串行。

</details>

**Q2.** 为什么 shadow paging 能同时提供原子性和持久性，却仍然在实践中被淘汰？

<details><summary>参考答案</summary>

**它能提供的原因**：修改写在页的副本上，commit 时用一个**原子的指针切换**（更新根页指针）让新版本生效。崩溃时若指针未切换，旧版本完好（原子性）；若已切换，新版本完整（持久性）。恢复只需「删掉未提交的页」，几乎是 O(1)。

**被淘汰的原因**：

1. **写放大严重**：每次修改都要复制整页，即使只改一个字节；页越大浪费越多。
2. **页分配与碎片**：频繁复制导致物理页分散，破坏顺序性，后续扫描变慢。
3. **并发控制困难**：多个事务同时修改同一页会产生多份副本，如何合并、如何判定冲突都很复杂。
4. **与 WAL 相比没有优势**：WAL 只需顺序追加日志（顺序 I/O 极快），数据页可以延迟批量刷盘；而 shadow paging 的页复制是随机写。
5. **长事务代价爆炸**：事务越长，复制的页越多，空间占用越大。

今天只有少数嵌入式系统（CouchDB、Tokyo Cabinet、LMDB）还用类似机制，因为它们的数据量小、并发低、追求恢复简单。

</details>

**Q3.** 一个调度含 blind write：`W1(A) W2(A) W2(A) R3(A)`（T1、T2 都不读 A 直接写）。它的优先图有环吗？它视图可串行化吗？

<details><summary>参考答案</summary>

**优先图**：`W1(A)` 与 `W2(A)` 冲突 → 边 `T1 → T2`；两个 `W2(A)` 同事务不算冲突；`W2(A)` 与 `R3(A)` 冲突 → `T2 → T3`；`W1(A)` 与 `R3(A)` 也冲突 → `T1 → T3`。图是 `T1 → T2 → T3` 加 `T1 → T3`，**无环**，所以它其实**也是冲突可串行化**的（等价于串行顺序 T1, T2, T3）。

要构造「优先图有环但视图可串行化」的例子，需要 blind write **覆盖**掉某个读的结果，例如：`R1(A) W2(A) W1(A)`。这里 `R1(A)` 与 `W2(A)` 冲突 → `T1 → T2`；`W2(A)` 与 `W1(A)` 冲突 → `T2 → T1`，成环，**不是冲突可串行化**。但因为 `W1(A)` 是 blind write（不看 A 的当前值），T1 读到的 A 值对最终结果**没有影响**，所以它**视图等价于串行顺序 T1, T2**（T1 先读初值再盲写，T2 后写覆盖），因此**是视图可串行化**的。

结论：blind write 正是「冲突可串行化」与「视图可串行化」的分界线。

</details>

**Q4.** DBMS 为什么不干脆要求所有事务串行执行？那样不是最简单、绝对正确吗？

<details><summary>参考答案</summary>

**性能不可接受**。串行执行意味着：

1. **无法隐藏 I/O 延迟**：一个事务在等磁盘时，其他事务只能干等。现代存储的延迟是微秒到毫秒级，而 CPU 是纳秒级，串行会让 CPU 几乎全程空闲。
2. **浪费多核**：一台 64 核服务器只能用 1 个核。
3. **长事务阻塞全体**：一个跑 10 分钟的报表会让所有 OLTP 请求排队 10 分钟——这在任何生产系统里都是灾难。
4. **吞吐塌陷**：事务的响应时间变成「所有并发事务时间之和」，吞吐量降到 1/N。

并发控制的意义就是：**在保证结果等价于串行执行的前提下，允许实际操作交错**。换句话说，「可串行化」是**语义要求**，不是**执行方式要求**——这是理解整个并发控制部分的关键。

</details>

**Q5.** 一个系统实现了「冲突可串行化」，是否就一定不会出现「写偏斜（write skew）」？为什么讲义把写偏斜留到后面的讲次？

<details><summary>参考答案</summary>

**冲突可串行化能防住写偏斜**——因为写偏斜的本质是两个事务读了重叠的数据集、各自写了不相交的部分，形成的读写依赖环（`T1 →rw T2 →rw T1`），这个环在优先图里就是环，冲突可串行化会拒绝它。

但**快照隔离（snapshot isolation）不是冲突可串行化的**：它只检测写-写冲突，允许两个事务各自基于同一快照读、写不同行，于是写偏斜会漏过去。讲义把写偏斜留到第 20/21 讲（时间戳排序与 MVCC），是因为：

1. 写偏斜需要**多版本**或**快照**的概念才能自然描述（「两个事务读同一快照」）；
2. 它是「隔离级别 != 可串行化」的最典型反例，讲完 MVCC 与快照隔离后才有对照物；
3. 它还是「为什么 PostgreSQL 的 `REPEATABLE READ` 仍可能写偏斜、需要 `SERIALIZABLE`」这一实践问题的理论根源。

</details>

## 12. 进一步学习

- 上一讲：[[15-445-17-Query-Optimization-II]] —— 查询优化的最后一讲，本讲起进入事务处理。
- 下一讲：[[15-445-19-Two-Phase-Locking]] —— 把「可串行化」这个判据变成**可在线执行的协议**：锁、2PL、死锁处理、层次锁。
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：教材 *Database System Concepts*（第 7 版）第 17 章「Transactions」与第 18 章前半；Bernstein & Goodman 的 "Concurrency Control in Distributed Database Systems"（1981）是冲突可串行化理论的经典综述。
- 动手建议：在 PostgreSQL 里开两个 `psql` 会话，手动执行「读-改-写」序列，观察 `READ COMMITTED` 下丢失更新与不可重复读的实际表现；再用 `BEGIN ISOLATION LEVEL SERIALIZABLE` 重跑，观察 `could not serialize access due to concurrent update` 报错。
