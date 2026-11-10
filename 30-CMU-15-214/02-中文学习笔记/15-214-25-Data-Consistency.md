---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L25
topic: Data Consistency - Transactions, ACID, Two-Phase Locking, and Two-Phase Commit
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 事务
  - 一致性
  - 分布式系统
  - 两阶段提交
  - 可串行化
---

# 第 25 讲 数据一致性（Data Consistency）

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。

## 1. 本节学习目标

- 能用「完整性约束 φ」与 `IsConsistent(D)` 精确定义「一致性」，并说明为什么一致性是**应用相关**的。
- 能把事务理解为一个**函数** T(D)，并解释 `begin` / `commit` / `abort` 的语义。
- 能逐条解释 ACID 四项，并说明每一项分别由什么机制保障。
- 能解释可串行化（serializability）与线性化（linearizability）的区别，并举例说明「丢失更新」与「不一致读取」。
- 能手工推导两阶段锁（2PL）为什么能保证可串行化，以及它为什么不能防死锁。
- 能说明分布式 2PL 相比单机 2PL 多出的两个问题。
- 能画出两阶段提交（2PC）的投票阶段与提交阶段，并列出四种参与者状态。
- 能说出 2PC 的三个主要缺陷，并用 CAP 定理解释其中的根本矛盾。

## 2. 前置知识

- [[15-214-17-Concurrency-Part1]]：竞态条件、交错。
- [[15-214-18-Concurrency-Part2]]：锁、死锁四条件。
- [[15-214-21-Distributed-Systems-Part2]]：复制、缓存失效、分区。
- [[15-214-20-Distributed-Systems-Part1]]：部分失败（partial failure）——2PC 存在的根本原因。
- [[15-214-05-Object-Contracts-and-Exceptions]]：不变式（invariant）——本讲把它推广到「数据的一致性」。

## 3. 核心概念

- **Data Store（数据存储）**：一组持久化的数据项 D（数据库、文件、键值存储）。
- **Integrity Constraint（完整性约束）φ**：数据必须始终满足的逻辑条件（如「账户余额不为负」「所有账户余额之和为常数」）。
- **Consistency（一致性）**：`IsConsistent(D)` 为真，即 D 满足 φ。
- **Transaction（事务）**：一组操作的**原子**执行单元，要么全部生效，要么全部不生效。
- **Commit（提交）**：事务成功结束，其效果永久生效。
- **Abort（中止/回滚）**：事务失败结束，其所有效果被撤销。
- **ACID**：Atomicity（原子性）、Consistency（一致性）、Isolation（隔离性）、Durability（持久性）。
- **Serializability（可串行化）**：并发执行多个事务的结果，等价于**某个串行顺序**执行它们的结果。
- **Linearizability（线性化/可线性化）**：每个操作看起来都在其调用与返回之间的某个瞬间原子生效，且尊重实时顺序。
- **Lost Update（丢失更新）**：两个事务都读同一值、各自修改、后写者覆盖先写者。
- **Inconsistent Read（不一致读取）**：一个事务读到另一个未提交事务的中间状态。
- **Two-Phase Locking（两阶段锁，2PL）**：增长阶段只加锁、收缩阶段只解锁——保证可串行化。
- **Two-Phase Commit（两阶段提交，2PC）**：分布式事务的原子提交协议，分投票与提交两阶段。
- **Coordinator（协调者）**：2PC 中负责驱动协议、做最终决定的节点。
- **Participant（参与者）**：2PC 中执行本地事务、投票的节点。
- **Prepared（已准备）**：参与者已投票 yes 但尚未知道最终决定的状态——**最危险的状态**。
- **CAP Theorem（CAP 定理）**：一致性（Consistency）、可用性（Availability）、分区容错性（Partition tolerance）三者不可兼得。

## 4. 通俗理解

**什么是「一致性」？** 想象一个银行，两个账户 A 和 B，总额必须永远是 100 元。这就是完整性约束 φ：`balance(A) + balance(B) == 100`。任何时刻你去看数据库，这个等式都得成立——这就是 `IsConsistent(D)`。

**为什么转账需要事务？** 转账要两步：`A -= 10`，`B += 10`。如果做完第一步程序崩了，A 少了 10 元而 B 没多——总额变成 90，约束被破坏。事务的作用就是：**要么两步都做，要么两步都不做**。这就像你写文档时按了「撤销」——但撤销的粒度是整个事务。

**并发为什么麻烦？** 两个转账同时发生：T1 从 A 转 10 到 B，T2 从 A 转 20 到 C。如果它们交错执行，可能都读到 A 的旧余额 100，各自算「A 还剩 90」和「A 还剩 80」，最后写回时后者覆盖前者——A 变成 80，但实际应该是 70。**10 元凭空消失了**。这就是「丢失更新」。

**怎么防？** 加锁。但普通的锁不够——你需要一个**协议**，保证「并发执行的结果」看起来像「一个一个排队执行的结果」。这个协议就是 2PL。

**分布式为什么更难？** 因为现在有两个数据库，各自在自己的机器上。你让它们都提交，但**网络可能在半路断掉**：一个收到了「提交」指令，另一个没收到。这时候你面临一个两难：如果让收到的那台提交，而另一台回滚，数据就不一致了；如果让收到的那台等待，它就得一直锁着资源。这就是 2PC 要解决的问题，也是 CAP 定理的根源。

## 5. 原理与推导

### 5.1 复式记账：一个具体的数据存储

课件第 5 页给出三个基本操作（复式记账，double-entry bookkeeping）：

```java
// 转账：从 from 账户转 amount 到 to 账户
void transfer(Account from, Account to, int amount) {
    deposit(to, amount);
    withdraw(from, amount);
}

// 存款
void deposit(Account acct, int amount) {
    acct.balance += amount;
    acct.transactions.add(new Transaction(acct, amount));
}

// 取款
void withdraw(Account acct, int amount) {
    acct.balance -= amount;
    acct.transactions.add(new Transaction(acct, -amount));
}
```

**为什么叫「复式」记账？** 每一笔金额变动都记录两次：一次改余额，一次追加一条流水。这两个动作**必须同时发生**——如果只改了余额没记流水，审计就对不上；如果只记了流水没改余额，余额就错了。

**注意 `transfer` 里的顺序**：先 `deposit` 再 `withdraw`。如果中间崩溃，`to` 账户多了钱而 `from` 没少——凭空造钱。这个顺序不是随便写的，它体现了「必须原子」的需求。

### 5.2 一致性的形式化定义

课件第 7 页：

> **Consistency**
> - A data store is consistent if it satisfies a set of integrity constraints φ
> - `IsConsistent(D)` returns true iff D satisfies φ
> - **Consistency is application-specific!**

课件给出的例子：

- 「每个账户的余额必须等于其交易流水之和」——这是复式记账的核心约束；
- 「所有账户余额之和必须等于某个常数」——转账不改变总额；
- 「余额不能为负」——除非允许透支。

**关键洞察：一致性不是数据库的属性，是应用的属性。** 数据库不知道「余额之和该是多少」——只有应用知道。所以数据库能提供的只是**机制**（事务），而**约束本身**必须由应用声明。

第 8 页给出形式化的伪代码：

```python
def IsConsistent(D):
    # 对 D 中的每个账户 a
    for a in D.accounts:
        # 余额必须等于流水之和
        if a.balance != sum(t.amount for t in a.transactions):
            return False
    return True
```

这个函数是整个讲义的「裁判」：事务的价值就在于**保证 `IsConsistent` 在事务前后都为真**。

### 5.3 事务：定义与语义

课件第 9 页：

> **Transactions**
> - A transaction is a set of operations that must be executed atomically
> - All operations in a transaction are executed, or none of them are
> - **Commit**: the transaction completes successfully
> - **Abort**: the transaction fails, and its effects are undone

第 10 页给出一个**用事务重写的取款**，注意它的返回值语义：

```java
boolean withdraw(Account acct, int amount) {
    begin();
    if (acct.balance < amount) {
        abort();          // 余额不足：放弃整个事务
        return false;
    }
    acct.balance -= amount;
    acct.transactions.add(new Transaction(acct, -amount));
    commit();
    return true;
}
```

**三个要点**：

1. `abort()` 之后 `return false`——**中止不是异常**，它是一种正常的控制流，用来表达「业务规则不满足」。
2. `abort()` 会撤销 `begin()` 之后的所有修改。注意这里 `abort` 发生在任何修改之前，所以实际没东西可撤销——但如果在 `acct.balance -= amount` 之后才发现余额不足（比如检查在另一个事务里），`abort` 就必须真的回滚。
3. `commit()` 之后才 `return true`——**提交成功才算成功**。如果 `commit()` 本身失败（比如磁盘满了），应该返回 `false` 或抛异常。

### 5.4 事务的函数视角

课件第 11–12 页给出一个非常优雅的抽象：

> **Transactions as functions**
> - A transaction T maps a data store D to a new data store D' = T(D)
> - If T aborts, D' = D (no change)
> - If T commits, D' is the result of applying all operations

这个视角的价值在于：它把「事务」变成了一个**数学对象**，于是可以谈论：

- **组合**：T2(T1(D)) —— 两个事务串行执行；
- **等价**：并发执行 T1 ∥ T2 的结果等于 T1(T2(D)) 或 T2(T1(D))；
- **正确性**：如果 `IsConsistent(D)` 为真，那么 `IsConsistent(T(D))` 也应为真——**这是应用的责任，不是数据库的**。

**注意最后一点**：事务保证原子性，但**不保证业务正确性**。如果你写了一个 `withdraw` 让余额变成负数，事务会忠实地执行它并提交——因为数据库不知道「余额不能为负」。这就是 ACID 里 C（Consistency）与其他三项的根本区别：**A、I、D 是数据库的机制，C 是应用的义务**。

### 5.5 ACID

课件第 13 页：

| 字母 | 名称 | 含义 | 由什么保障 |
|---|---|---|---|
| **A** | **Atomicity（原子性）** | 事务的所有操作要么全做、要么全不做 | 日志（undo log）+ 回滚 |
| **C** | **Consistency（一致性）** | 事务把一致的状态变成一致的状态 | **应用的责任**（数据库只提供机制） |
| **I** | **Isolation（隔离性）** | 并发事务互不干扰，如同串行执行 | 锁（2PL）或多版本并发控制（MVCC） |
| **D** | **Durability（持久性）** | 提交后的效果永久保存，即使崩溃 | 日志（redo log）+ fsync |

**常见误解**：很多人以为 ACID 是四个同等地位的「数据库保证」。实际上 C 是**应用层面**的——数据库无法知道你的业务约束。这也是为什么课件反复强调「Consistency is application-specific」。

**A 与 D 的关系**：原子性靠 undo log（记录「怎么撤销」），持久性靠 redo log（记录「怎么重做」）。两者常常合并在一个 write-ahead log（WAL）里。

### 5.6 可串行化

课件第 14–15 页：

> **Serializability**
> - A concurrent execution of transactions is serializable if it is equivalent to some serial execution
> - The database appears to execute transactions one at a time
> - **Linearizability** is a stronger condition: operations appear to take effect atomically at some point between invocation and response

**可串行化 vs 线性化**：

- **可串行化**只要求「存在某个串行顺序」，**不要求**该顺序与实际时间顺序一致。所以它允许「重排序」——只要结果对得上。
- **线性化**要求「每个操作在其调用与返回之间的某个瞬间生效」，且如果操作 A 在操作 B 开始前就返回了，那么 A 必须排在 B 前面。这更接近人的直觉，但代价更高。

**本课程主要讨论可串行化**，因为它是数据库隔离级别的标准（SQL 标准的 SERIALIZABLE）。

**两个经典的反例**：

**(1) 丢失更新（lost update）**

```
T1: 读 A = 100
T2: 读 A = 100
T1: 写 A = 100 - 10 = 90
T2: 写 A = 100 - 20 = 80        ← T1 的更新被覆盖
```

结果 A = 80，但正确值应是 70。**问题在于「读」与「写」之间没有原子性**。

**(2) 不一致读取（inconsistent read）**

```
T1: 写 A = 90                    （未提交）
T2: 读 A = 90                    ← 读到未提交的值（脏读）
T1: abort()                      （回滚，A 恢复 100）
T2: 基于 A = 90 做了决定        ← 决定基于一个从未存在过的值
```

**问题在于隔离性被破坏**。

### 5.7 两阶段锁（2PL）

课件第 16 页：

> **Two-phase locking (2PL)**
> - Phase 1 (growing): acquire locks, never release
> - Phase 2 (shrinking): release locks, never acquire
> - Guarantees serializability

**为什么 2PL 能保证可串行化？** 直观的证明：

1. 每个事务在**第一次释放锁之前**已经获得了它需要的**全部**锁。
2. 考虑任意两个事务 T1、T2，它们都访问了某个数据项 x。那么两者都必须持有 x 的锁——而锁是互斥的，所以一个必须先获得、另一个后获得。
3. 这个「谁先获得 x 的锁」的关系定义了 T1 与 T2 之间的一个**偏序**。
4. 由于 2PL 的「不释放后再获取」规则，这个偏序**不会成环**（否则会形成「T1 等 T2 释放、T2 等 T1 释放」的循环，而 2PL 保证了不存在这种循环等待）。
5. 因此存在一个**拓扑排序**，把偏序扩展成全序——这就是等价的串行顺序。

**关键点**：2PL 保证的是**冲突可串行化（conflict serializability）**——只要两个事务访问同一数据且至少一个是写，它们的相对顺序就被锁固定了。

**2PL 的代价**：

- **并发度低**：事务必须一次性拿齐所有锁，不能「用完就放」；
- **死锁**：2PL 不防死锁。T1 锁 A 等 B，T2 锁 B 等 A——经典死锁。
- 解法：**锁序（lock ordering）**（所有事务按同一顺序获取锁）或**死锁检测**（等待图找环，选一个牺牲者回滚）。

**这与 [[15-214-18-Concurrency-Part2]] 的死锁四条件是同一套理论**：2PL 违反了「不剥夺」条件的预防，所以只能靠「破坏循环等待」（锁序）来处理。

### 5.8 分布式 2PL：两个新问题

课件第 17 页：

> **Distributed 2PL**
> - Locks are acquired at multiple sites
> - **New problems:**
>   - Distributed deadlock: cycles can span multiple sites
>   - All-or-nothing commit: need agreement among all sites

**问题 1：分布式死锁**

单机死锁检测只需要看一个等待图。分布式下，等待图分散在多个节点上：T1 在节点 A 等 T2 释放锁，T2 在节点 B 等 T1 释放锁——**没有任何单个节点能看到完整的环**。解法有：

- **集中式检测**：把所有等待关系汇总到一个节点（有单点故障与延迟）；
- **分布式检测**：节点间传递「探针（probe）」消息，检测环（复杂，可能误判）；
- **超时**：简单粗暴，但可能误杀长事务。

**问题 2：全体一致决定提交（all-or-nothing commit）**

在单机数据库里，「提交」是一个本地决定——写日志、刷盘、完事。在分布式下，事务可能横跨三个数据库：**要么三个都提交，要么三个都回滚**。这需要**分布式共识**——而这正是 2PC 要解决的。

**这两个问题正是「分布式系统比单机难」的具体体现**：单机上的每一个「原子操作」，在分布式下都变成了「需要协议」的事情。这与 [[15-214-20-Distributed-Systems-Part1]] 里「部分失败」的主题完全一致。

### 5.9 两阶段提交（2PC）：角色与失败模型

课件第 18 页：

> **Two-phase commit (2PC)**
> - **Coordinator（协调者）**: drives the protocol, makes the final decision
> - **Participants（参与者）**: execute the local transaction, vote
> - **Failure model**: any node may crash; messages may be lost

**注意失败模型的措辞**：「any node may crash; messages may be lost」。这比单机系统的假设弱得多——单机数据库只需考虑「自己的进程崩溃 + 磁盘损坏」，2PC 还要考虑「协调者崩了」「参与者崩了」「消息丢了」「网络分区了」。

**课件特别强调的一点**（也是 2PC 最反直觉的地方）：**2PC 假设的是 fail-stop（节点崩溃即停止），而不是拜占庭失败（节点可能说谎）**。如果协调者可能发送矛盾的消息，2PC 就不安全了。参见 [[15-214-20-Distributed-Systems-Part1]] 第 29 页的失败类型分类。

### 5.10 投票阶段

课件第 19 页：

> **Phase 1: Voting**
> - Coordinator sends `canCommit?` to all participants
> - Each participant:
>   - Checks whether it can commit (locks acquired, constraints satisfied)
>   - Writes `<prepare>` to its log
>   - Replies `yes` or `no`
> - If any participant replies `no`, coordinator decides **abort**

**为什么参与者要先写日志再回复 yes？** 因为一旦回复 yes，它就**失去了单方面回滚的权利**——它必须等待协调者的最终决定。如果此时它崩溃，重启后必须能从日志里知道「我曾经投过 yes」，从而在恢复后继续等待或询问协调者。

**「写 `<prepare>` 到日志」这一步是 2PC 的持久性关键**：没有它，参与者崩溃重启后会「忘记」自己投过票，可能造成不一致。

**参与者投 yes 的条件**（隐含）：

- 它已经获得了所有需要的锁；
- 本地约束检查通过；
- 它能保证「如果协调者说 commit，我一定能 commit」（比如 redo log 已经写好）。

**注意这里的「yes」是一个承诺（promise），不是一个意见**。投了 yes 之后，参与者**不能反悔**——即使后来发现自己想回滚也不行。这是 2PC 的核心，也是它的脆弱之处。

### 5.11 提交阶段

课件第 20 页：

> **Phase 2: Commit**
> - If all participants replied `yes`:
>   - Coordinator writes `<commit>` to its log
>   - Sends `doCommit` to all participants
> - Otherwise:
>   - Coordinator writes `<abort>` to its log
>   - Sends `doAbort` to all participants
> - Participants:
>   - Write `<commit>` or `<abort>` to their log
>   - Execute the decision
>   - Reply `ack`
> - Coordinator: after all `ack`s, writes `<done>`

**关键顺序**：

1. 协调者**先写日志再发消息**——保证「决定不会丢失」；
2. 参与者**先写日志再执行**——保证「崩溃重启后能重做或撤销」；
3. 协调者**收到所有 ack 才写 done**——保证「所有人都知道了」。

**这个顺序不是随意的**：每一步都是「先把决定持久化，再做不可逆的动作」。这是所有分布式协议的通用模式，与 [[15-214-20-Distributed-Systems-Part1]] 里主备复制的「先更新状态再广播」同源。

### 5.12 参与者的四种状态

课件第 21 页用时序图展示参与者可能处于的状态：

| 状态 | 含义 | 能否单方面决定 |
|---|---|---|
| **prepared** | 已投 yes，等待协调者决定 | **不能**——必须等 |
| **committed** | 收到 doCommit 并已提交 | 已完成 |
| **uncertain** | 投了 yes 但没收到决定（协调者失联） | **不能**——最危险 |
| **done** | 完成并已 ack | 已完成 |

**`uncertain` 是 2PC 的死穴**：参与者投了 yes、锁着资源、等着决定，但协调者崩了。它**不能**自己决定提交（因为可能别人投了 no），也**不能**自己决定回滚（因为可能别人投了 yes 且已经提交）。它只能**一直等**——而它持有的锁会阻塞所有其他事务。

**这个「阻塞等待」是 2PC 最著名的缺陷**，也是后来三阶段提交（3PC）与 Paxos/Raft 想解决的问题。

### 5.13 2PC 的三个问题

课件第 23 页：

> **Problems with 2PC**
> 1. **Failure assumptions too strong**: assumes fail-stop, no message corruption, reliable network
> 2. **Temporary failures cause delays**: a participant down → everyone waits, locks held
> 3. **Many round trips**: 2 rounds of messages, plus acks

**逐条分析**：

**(1) 失败假设过强**

2PC 假设：节点崩溃即停止（fail-stop）、消息不会损坏、网络最终会恢复。现实中：

- **网络分区**：协调者与参与者之间的网络断了，参与者进入 `uncertain`，一直等；
- **消息损坏**：需要校验和，但 2PC 本身不处理；
- **拜占庭失败**：节点可能发送矛盾消息——2PC 完全不防。

**(2) 临时失败导致延迟**

一个参与者宕机 5 分钟，整个事务就卡 5 分钟，而且**它持有的锁一直不释放**。在高并发系统里，这会引起雪崩——其他事务全被阻塞。这就是为什么很多互联网系统**放弃 2PC**，改用「最终一致性」。

**(3) 往返消息多**

投票阶段一轮（1 次请求 + 1 次响应），提交阶段一轮（1 次请求 + 1 次响应 + 1 次 ack）——最少 2 个往返，实际更多。跨数据中心时，每次往返可能是几十毫秒，累积起来很可观。

**补充：2PC 还有一个「协调者单点」问题**——协调者崩了且日志丢失，所有参与者永久卡在 `uncertain`。实践中会用「协调者日志复制」来缓解，但那又变成了另一个共识问题。

### 5.14 CAP 定理

课件第 24 页：

> **CAP Theorem**
> - **Consistency**: all nodes see the same data at the same time
> - **Availability**: every request receives a response (success or failure)
> - **Partition tolerance**: the system continues to operate despite network partitions
> - **You can have at most two**

**逐项解释**：

- **C（一致性）**：这里的 C 与 ACID 的 C **不是一回事**。CAP 的 C 指**线性一致性（linearizability）**——所有节点看到同一份数据、同一时刻。
- **A（可用性）**：每个请求都能得到**非错误**的响应（不保证是最新数据）。
- **P（分区容错）**：网络分区时系统仍能工作。

**「最多两个」的推导**：

假设网络发生分区，节点 A 与节点 B 无法通信。

- 如果选 **C + P**：A 与 B 不能通信，为了保证一致性，至少有一边必须**拒绝服务**——违反 A。
- 如果选 **A + P**：A 与 B 都能响应，但无法同步，所以返回的数据可能不一致——违反 C。
- 如果选 **C + A**：那就必须**不允许分区**（放弃 P）——但网络分区是客观现实，你无法「不允许」它。

**结论**：在真实网络中，**P 是必选项**，所以你只能在 C 与 A 之间选。

**这个结论对系统设计的指导**：

| 选择 | 典型系统 | 适用场景 |
|---|---|---|
| **CP**（放弃可用性） | 传统关系数据库、ZooKeeper、HBase | 金融交易、配置管理——宁可拒绝服务也不能给错数据 |
| **AP**（放弃强一致性） | Cassandra、DynamoDB、DNS | 社交动态、购物车——宁可给旧数据也不能不响应 |

**2PC 属于 CP**：网络分区时，`uncertain` 的参与者会阻塞——牺牲可用性换取一致性。这与 [[15-214-22-Distributed-Systems-Part3]] 里 MapReduce 的设计哲学形成有趣对比：MapReduce 是「批处理」，可以容忍延迟，所以不追求低延迟一致性。

**一个常见的误解**：CAP 说的是「分区**期间**只能选两个」，不是「永远只能选两个」。在没有分区的时候，你**可以**同时有 C 和 A。CAP 的实用版本是 **PACELC**：如果有分区（P），在 A 与 C 之间选；否则（E, else），在延迟（L）与一致性（C）之间选。

### 5.15 本讲总结

从单机到分布式的三级递进：

1. **单机并发**：需要事务来保证「多个操作原子」；需要 2PL 来保证「并发等价于串行」。
2. **分布式并发**：2PL 的锁分散在多个节点，产生分布式死锁；「提交」变成需要共识的决定。
3. **分布式提交**：2PC 用两轮投票解决「全体一致」，但代价是阻塞、延迟、以及对失败模型的强假设。
4. **理论边界**：CAP 定理说明「分区时一致性 vs 可用性」不可兼得——这是所有分布式数据系统的设计出发点。

## 6. 代码示例

### 6.1 官方课程代码

**第 5 页：复式记账的三个操作**

```java
void transfer(Account from, Account to, int amount) {
    deposit(to, amount);
    withdraw(from, amount);
}

void deposit(Account acct, int amount) {
    acct.balance += amount;
    acct.transactions.add(new Transaction(acct, amount));
}

void withdraw(Account acct, int amount) {
    acct.balance -= amount;
    acct.transactions.add(new Transaction(acct, -amount));
}
```

**第 8 页：一致性检查（伪代码）**

```python
def IsConsistent(D):
    for a in D.accounts:
        if a.balance != sum(t.amount for t in a.transactions):
            return False
    return True
```

**第 10 页：用事务重写的取款**

```java
boolean withdraw(Account acct, int amount) {
    begin();
    if (acct.balance < amount) {
        abort();
        return false;
    }
    acct.balance -= amount;
    acct.transactions.add(new Transaction(acct, -amount));
    commit();
    return true;
}
```

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：用一个可回滚的内存数据存储演示事务。**

```java
import java.util.*;

public class TinyTransactionalStore {
    static class Account {
        int balance = 0;
        List<Integer> transactions = new ArrayList<>();
    }

    private final Map<String, Account> accounts = new LinkedHashMap<>();
    private Map<String, Account> snapshot = null;   // 事务开始时的快照

    public void create(String name) {
        Account a = new Account();
        accounts.put(name, a);
    }

    // ---- 事务 API ----
    public void begin() {
        snapshot = deepCopy(accounts);
    }

    public void commit() {
        snapshot = null;                             // 丢弃快照，修改生效
    }

    public void abort() {
        accounts.clear();
        accounts.putAll(snapshot);                   // 回滚
        snapshot = null;
    }

    private Map<String, Account> deepCopy(Map<String, Account> src) {
        Map<String, Account> out = new LinkedHashMap<>();
        for (var e : src.entrySet()) {
            Account a = new Account();
            a.balance = e.getValue().balance;
            a.transactions = new ArrayList<>(e.getValue().transactions);
            out.put(e.getKey(), a);
        }
        return out;
    }

    public boolean withdraw(String name, int amount) {
        Account a = accounts.get(name);
        if (a.balance < amount) {
            abort();
            return false;
        }
        a.balance -= amount;
        a.transactions.add(-amount);
        commit();
        return true;
    }

    public boolean transfer(String from, String to, int amount) {
        begin();
        Account f = accounts.get(from), t = accounts.get(to);
        if (f.balance < amount) { abort(); return false; }
        t.balance += amount;  t.transactions.add(amount);
        f.balance -= amount;  f.transactions.add(-amount);
        commit();
        return true;
    }

    public boolean isConsistent() {
        for (Account a : accounts.values()) {
            int sum = a.transactions.stream().mapToInt(Integer::intValue).sum();
            if (a.balance != sum) return false;
        }
        return true;
    }

    public static void main(String[] args) {
        TinyTransactionalStore db = new TinyTransactionalStore();
        db.create("A"); db.create("B");
        db.transfer("A", "B", 10);          // A 余额 0 < 10 → abort
        System.out.println("consistency = " + db.isConsistent());
        System.out.println("A.balance = " + db.accounts.get("A").balance);
    }
}
```

**这个示例的局限**：它用「整库快照」实现回滚，代价是 O(n) 内存——真实数据库用 undo log，只记录被改动的项。但语义是完全正确的：`begin` 记录起点、`abort` 回到起点、`commit` 丢弃起点。

**示例 B：手工复现「丢失更新」。**

```java
public class LostUpdateDemo {
    static int balance = 100;

    public static void main(String[] args) throws Exception {
        Runnable t1 = () -> {
            int read = balance;                 // 读 100
            sleep(10);
            balance = read - 10;                // 写 90
        };
        Runnable t2 = () -> {
            int read = balance;                 // 读 100
            sleep(10);
            balance = read - 20;                // 写 80 ← 覆盖了 T1 的结果
        };
        Thread a = new Thread(t1), b = new Thread(t2);
        a.start(); b.start(); a.join(); b.join();
        System.out.println("balance = " + balance);   // 80，但正确值应是 70
    }

    static void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException e) { }
    }
}
```

**注意 `sleep(10)` 的作用**：它把「读」与「写」之间的窗口放大，让竞态**必然**发生。真实系统里这个窗口可能只有几纳秒，所以 bug 是偶发的。这正是 [[15-214-24-Static-Analysis-for-Concurrency]] 里「难以测试」的具体演示。

**示例 C：用一把锁实现「串行化」的效果。**

```java
public class LockedCounter {
    private int balance = 100;
    private final Object lock = new Object();

    /** 整个「读-改-写」在一个临界区内 → 不会丢失更新 */
    public void withdraw(int amount) {
        synchronized (lock) {
            if (balance < amount) return;
            balance -= amount;
        }
    }

    public int getBalance() {
        synchronized (lock) { return balance; }
    }

    public static void main(String[] args) throws Exception {
        LockedCounter c = new LockedCounter();
        Thread a = new Thread(() -> { for (int i = 0; i < 100; i++) c.withdraw(1); });
        Thread b = new Thread(() -> { for (int i = 0; i < 100; i++) c.withdraw(1); });
        a.start(); b.start(); a.join(); b.join();
        System.out.println("balance = " + c.getBalance());   // 应为 0（若不足则停止）
    }
}
```

**这与 2PL 的关系**：这里的 `synchronized` 块就是「增长+收缩」的退化形式——进入时加锁、退出时释放，中间不再获取新锁。它是 2PL 的特例，也是「严格 2PL（strict 2PL）」的典型形式（持锁到事务结束）。

**示例 D：一个极简的 2PC 模拟（两个参与者 + 一个协调者）。**

```java
import java.util.*;

public class TwoPhaseCommitDemo {

    /** 参与者 */
    static class Participant {
        final String name;
        boolean canCommit = true;       // 本地能否提交
        String state = "init";          // init / prepared / committed / aborted

        Participant(String name) { this.name = name; }

        /** 投票阶段：返回 yes / no */
        String vote() {
            if (!canCommit) {
                state = "aborted";
                return "no";
            }
            state = "prepared";         // 写 <prepare> 日志
            return "yes";
        }

        /** 提交阶段 */
        void decide(boolean commit) {
            state = commit ? "committed" : "aborted";
        }
    }

    /** 协调者 */
    static class Coordinator {
        boolean run(List<Participant> ps) {
            // ---- 阶段 1：投票 ----
            boolean allYes = true;
            for (Participant p : ps) {
                String v = p.vote();
                System.out.println(p.name + " 投票: " + v + " → 状态 " + p.state);
                if (!v.equals("yes")) allYes = false;
            }

            // ---- 阶段 2：提交/中止 ----
            System.out.println("协调者决定: " + (allYes ? "COMMIT" : "ABORT"));
            for (Participant p : ps) {
                p.decide(allYes);
                System.out.println(p.name + " → 状态 " + p.state);
            }
            return allYes;
        }
    }

    public static void main(String[] args) {
        Participant p1 = new Participant("P1");
        Participant p2 = new Participant("P2");
        p2.canCommit = false;                        // P2 本地失败

        boolean committed = new Coordinator().run(List.of(p1, p2));
        System.out.println("最终结果: " + (committed ? "提交" : "全部回滚"));
    }
}
```

输出：

```
P1 投票: yes → 状态 prepared
P2 投票: no → 状态 aborted
协调者决定: ABORT
P1 → 状态 aborted
P2 → 状态 aborted
最终结果: 全部回滚
```

**关键观察**：P1 投了 yes 之后**无法反悔**——它必须等协调者说 abort 才能回滚。如果协调者在此时崩溃，P1 就永久卡在 `prepared`（即课件所说的 `uncertain`）。**这个「卡住」正是 2PC 的核心缺陷**，也是为什么它不能容忍协调者长时间不可用。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| ACID 的 Consistency | CAP 的 Consistency | 前者是「满足应用定义的完整性约束」；后者是「所有节点同时看到相同数据」（即线性一致性） |
| 可串行化（serializability） | 线性化（linearizability） | 前者只要求「等价于某个串行顺序」，可重排序；后者要求「尊重实时顺序」 |
| Commit（提交） | Consistency（一致性） | 提交只保证原子生效，**不保证**业务约束成立——约束是应用的责任 |
| Abort（中止） | 异常（exception） | 前者是**正常**的业务控制流（如余额不足）；后者是错误 |
| 2PL（两阶段锁） | 2PC（两阶段提交） | 前者解决**并发隔离**（单机或多机加锁）；后者解决**分布式原子提交**（投票决定提交/回滚） |
| 2PL 的增长/收缩阶段 | 2PC 的投票/提交阶段 | 名字都是「两阶段」，但前者关于**锁**，后者关于**决定** |
| 分布式死锁 | 单机死锁 | 前者等待图跨节点，无单一节点可见全环；后者一个等待图即可检测 |
| prepared 状态 | committed 状态 | 前者已投 yes 但不知道结果，**不可单方面决定**；后者已确定提交 |
| CP 系统 | AP 系统 | 前者分区时拒绝服务保一致（2PC、ZooKeeper）；后者分区时继续服务但可能返回旧数据（Cassandra） |
| 强一致性 | 最终一致性 | 前者读到的永远是最新值；后者保证「不再有更新时会收敛」 |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-214/slides/26-data-consistency.pdf`
- **总页数**：25 页
- **本节重点页码**：
  - 第 5 页：复式记账的 `transfer` / `deposit` / `withdraw`
  - 第 7–8 页：完整性约束 φ、`IsConsistent(D)` 的定义与实现
  - 第 9–10 页：事务定义、commit / abort、用事务重写的 `withdraw`
  - 第 11–12 页：事务的函数视角 T(D)
  - 第 13 页：ACID 四项
  - 第 14–15 页：可串行化与线性化、丢失更新、不一致读取
  - 第 16 页：两阶段锁 2PL
  - 第 17 页：分布式 2PL 的两个新问题（分布式死锁、全体一致提交）
  - 第 18 页：2PC 的角色（Coordinator / Participants）与失败模型
  - 第 19 页：投票阶段（`canCommit?` / yes / no + 日志）
  - 第 20 页：提交阶段（`doCommit` / `doAbort` + ack + done）
  - 第 21 页：时序图与参与者四状态（prepared / committed / uncertain / done）
  - 第 23 页：2PC 的三个问题
  - 第 24 页：CAP 定理
- **原始链接**：https://www.cs.cmu.edu/~aldrich/214/slides/26-data-consistency.pdf
- **讲者**：本讲幻灯片署名 Garrod（课件作者标注），属 Fall 2013 客座讲次。

## 9. 对应视频

未找到官方公开录像。

## 10. 本节复习

- 一致性 = 数据满足应用定义的完整性约束 φ；`IsConsistent(D)` 是裁判函数。
- **一致性是应用相关的**——数据库只提供机制，不提供业务约束。
- 事务 = 原子的操作集合；`commit` 生效、`abort` 撤销；`abort` 是正常控制流。
- 事务可看作函数 T(D)：中止则 D' = D，提交则 D' 是全部操作的结果。
- ACID：A 靠 undo log、D 靠 redo log、I 靠锁/MVCC、**C 靠应用**。
- 可串行化 = 并发结果等价于某个串行顺序；线性化更强（尊重实时顺序）。
- 两个经典反例：丢失更新（读-改-写非原子）、不一致读取（脏读）。
- 2PL：增长阶段只加锁、收缩阶段只解锁 → 冲突可串行化；但不防死锁。
- 分布式 2PL 新增两个问题：分布式死锁（等待图跨节点）、全体一致提交（需要共识）。
- 2PC：投票（`canCommit?` → yes/no + 写 prepare 日志）→ 提交（`doCommit`/`doAbort` → 写日志 → ack → done）。
- 参与者四状态：prepared / committed / **uncertain**（最危险）/ done。
- 2PC 三缺陷：失败假设过强、临时失败导致长时间阻塞、往返消息多。
- CAP：分区时 C 与 A 二选一；P 在现实中必选。2PC 属 CP。

## 11. 自我检查

**Q1.** 下面这个 `transfer` 在一个支持事务的数据库里执行，`IsConsistent` 会返回什么？为什么？

```java
boolean transfer(String from, String to, int amount) {
    begin();
    Account f = load(from);
    if (f.balance < amount) { commit(); return false; }   // 注意：这里 commit 而非 abort
    deposit(to, amount);
    withdraw(from, amount);
    commit();
    return true;
}
```

**Q2.** 请解释为什么 2PL 能保证可串行化，但**不能**防止死锁。如果要同时防死锁，需要额外加什么机制？

**Q3.** 2PC 中，参与者投了 yes 之后为什么不能自己决定回滚？请从「它不知道什么」的角度回答。

**Q4.** 某系统选择了 AP（放弃强一致性）。请说明它在网络分区期间会发生什么，并举一个这种选择是**正确**的业务场景和一个**错误**的业务场景。

**Q5.** 有人说「2PC 保证了 ACID 的 C」。这句话对吗？请说明。

<details>
<summary>参考答案</summary>

**A1.** `IsConsistent` 返回 **true**（假设原本一致）。原因：余额不足时它执行了 `commit()` 而不是 `abort()`，但由于**没有任何修改发生**（`deposit`/`withdraw` 都没执行），提交一个「空事务」不会破坏一致性。**但这是一个语义 bug**：从业务角度，「余额不足」应该是一个「未完成」的结果，用 `commit` 表达「我成功地什么都没做」在语义上容易误导（如果后续有「事务成功即触发通知」的逻辑，就会误发通知）。正确写法是 `abort()`——表达「我放弃了」。这个例子说明：**ACID 的 C 与「代码写对」是两件事**，事务机制不能替你保证业务语义。

**A2.** **能保证可串行化的原因**：2PL 要求事务在释放任何锁之前先获得全部锁，因此任意两个冲突事务（访问同一数据、至少一个写）之间的相对顺序被锁的互斥性固定，形成一个无环偏序，可拓扑排序为等价的串行顺序。**不能防死锁的原因**：2PL 只约束「加锁与解锁的**阶段顺序**」，不约束「加锁的**对象顺序**」。T1 可以先锁 A 再锁 B，T2 可以先锁 B 再锁 A——两者都在增长阶段，都合法，但互相等待，形成环。**额外机制**：① **锁序（lock ordering）**——所有事务按全局一致的顺序获取锁，破坏「循环等待」条件；② **死锁检测**——维护等待图（wait-for graph），发现环就选一个事务回滚（牺牲者，victim）；③ **超时**——等待超过阈值就回滚（简单但可能误杀）；④ **死锁预防**——用时间戳（wait-die / wound-wait）决定谁等谁。注意 2PL 本身**违反不了**死锁四条件中的任何一个，必须靠外部机制。

**A3.** 因为投 yes 之后，参与者**不知道其他参与者投了什么**。具体来说：① 它不知道自己是不是唯一投 yes 的——如果别人投了 no，协调者会决定 abort，那么它必须回滚；② 它也不知道**别人是否已经提交**——如果其他参与者都投了 yes 且已经收到 doCommit 并提交了，那么它单独回滚就会造成不一致。**它唯一知道的是「我准备好了」**，而「全局是否提交」是一个**全局性质**，必须由协调者（或共识协议）来决定。这就是为什么 `uncertain` 状态的参与者只能阻塞等待——它缺少做决定所需的信息，而任何猜测都可能造成不一致。这个「局部信息不足以做全局决定」是分布式系统的根本困难，也是 FLP 不可能性定理的直观体现。

**A4.** 分区期间，各节点**继续响应请求**，但由于无法互相通信，不同节点可能返回**不同的数据**（比如 A 节点显示余额 100，B 节点显示 90）。分区恢复后，系统需要**冲突解决**（如「最后写入者胜」、向量时钟、CRDT 合并）来收敛。**正确的场景**：社交媒体的「点赞数」——分区期间两个数据中心各自计数，恢复后相加，用户看到 100 或 102 个赞都无所谓；或者 DNS——返回一个稍旧的 IP 仍然能访问。**错误的场景**：银行转账——分区期间 A 数据中心认为余额 100、B 认为 90，两边都允许取款，恢复后账户透支。这类场景必须选 CP（宁可拒绝服务）。判断标准是：**「读到旧数据」的代价 vs 「拒绝服务」的代价**，哪个更高。

**A5.** **不对**（至少是严重的误导）。ACID 里的 C 指的是「事务把一致的状态变成一致的状态」，而「一致」是由**应用定义的完整性约束**决定的。2PC 保证的是 **A（原子性）**——所有参与者要么全提交要么全回滚——以及部分 **I（隔离性）**（通过 2PL 的锁）。它**完全不检查**业务约束：如果你的 `withdraw` 逻辑允许余额变负，2PC 会忠实地在所有节点上提交这个错误结果。**准确的说法是**：2PC 保证「分布式原子提交」，它是实现 ACID 中 A 的手段；C 需要应用自己保证（约束检查 + 正确的业务逻辑）。课件反复强调 "Consistency is application-specific"，正是为了纠正这个误解。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-24-Static-Analysis-for-Concurrency]]——单机并发的静态检测（锁规约、区域锁、切点）。
- 下一讲：[[15-214-26-History-and-Future-of-Objects]]——从 SIMULA 到 Smalltalk 的对象史。
- 相关讲次：[[15-214-18-Concurrency-Part2]]（锁与死锁四条件）、[[15-214-20-Distributed-Systems-Part1]]（部分失败与失败类型）、[[15-214-21-Distributed-Systems-Part2]]（复制与缓存失效）、[[15-214-22-Distributed-Systems-Part3]]（MapReduce 的批处理视角）。
- 课程导航：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]、[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]。
- 术语条目：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Transaction 事务、Consistency 一致性、Atomicity 原子性、Serialization 序列化、Distributed System 分布式系统）。
- 延伸阅读：Gray & Reuter《Transaction Processing: Concepts and Techniques》、Bernstein & Newcomer《Principles of Transaction Processing》、Brewer "Towards Robust Distributed Systems"（PODC 2000，CAP 原始演讲）、Gilbert & Lynch "Brewer's conjecture and the feasibility of consistent, available, partition-tolerant web services"（2002）。
