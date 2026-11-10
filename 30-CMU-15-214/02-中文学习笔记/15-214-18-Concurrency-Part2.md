---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L18
topic: Concurrency 2 - Synchronization, Deadlock, and Higher-Level Abstractions
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 并发
  - 互斥
  - 死锁
  - 监视器
  - happens-before
---

# 第 18 讲 并发（二）：同步、死锁与高层抽象（Concurrency 2）

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。

## 1. 本节学习目标

- 能解释 Java 的 Intrinsic Lock（内在锁）模型，并判断 `synchronized` 方法/代码块实际锁住的是哪个对象。
- 能说明 `wait()` / `notify()` / `notifyAll()` 与锁的关系，以及为什么 `wait()` 必须放在循环里。
- 能用 Waits-for Graph（等待图）判断一组线程是否死锁，并说出死锁的四个必要条件。
- 能给出至少三种应对死锁的策略（全序加锁、重启、乐观并发控制），并比较其代价。
- 能区分 Deadlock（死锁）、Livelock（活锁）与 Starvation（饥饿）。
- 能用 happens-before 关系解释一段多线程代码是否存在数据竞争，并说明 `volatile` 的作用范围。
- 能说明 `ConcurrentHashMap` 的锁分段（lock striping）与 `CopyOnWriteArrayList` 的适用场景。

## 2. 前置知识

- [[15-214-17-Concurrency-Part1]]：线程与进程、原子性、竞态条件、check-then-act、Work/Depth。
- [[15-214-05-Object-Contracts-and-Exceptions]]：不变式（invariant）的概念——本节会把「不变式」用到并发场景。
- 外部概念：管程 / 监视器（monitor）的一般概念；队列（queue）的基本语义。

## 3. 核心概念

- **Intrinsic Lock（内在锁，又称 monitor lock）**：Java 中**每个对象**都自带的一把锁。初始无主，同一时刻只能被一条线程持有，不可剥夺。
- **`synchronized`（同步关键字）**：修饰实例方法时锁 `this`；修饰静态方法时锁该类的 `Class` 对象；作为代码块 `synchronized (obj) { ... }` 时锁 `obj`。
- **Critical Section（临界区）**：访问共享状态、必须被互斥保护的那段代码。`synchronized` 块体就是临界区。
- **Re-entrant（可重入）**：同一条线程可以重复获取自己已持有的锁，不会把自己锁死。因此 `synchronized` 方法可以调用同类中另一个 `synchronized` 方法。
- **`wait()` / `notify()` / `notifyAll()`**：`java.lang.Object` 上的协调方法。`wait()` 原子地释放锁并挂起，被唤醒后重新竞争锁再返回；`notify()` 随机唤醒一个在该对象上等待的线程；`notifyAll()` 唤醒全部。
- **Deadlock（死锁）**：一组线程各自持有对方需要的资源并互相等待，谁也推进不了。
- **Waits-for Graph（等待图）**：节点是线程，边 T1 → T2 表示「T1 正在等 T2 持有的锁」。图中存在环即死锁。
- **Livelock（活锁）**：线程都在运行（不是阻塞），但因为不断重试/退让而始终无法推进。
- **Starvation（饥饿）**：某个线程长期得不到所需资源（例如锁总是被别人抢走）。
- **happens-before（先行发生）**：Java 内存模型定义的偏序关系。若操作 A happens-before 操作 B，则 A 的结果对 B 可见。
- **`volatile`**：修饰字段，保证对该字段的写立即对后续读可见，并禁止相关重排序；但**不保证**复合操作的原子性。

## 4. 通俗理解

**内在锁 = 房间钥匙。** 每个对象是一间房，房里只有一把钥匙。想进屋（进入 `synchronized` 块）就得先拿到钥匙；出来时把钥匙挂回门口。钥匙只有一把，所以同一时刻房里只有一个人——这就是互斥（mutual exclusion）。

**可重入 = 你已经在屋里了。** 你进屋后想去里间（调用另一个 `synchronized` 方法），不需要再抢一次钥匙，因为钥匙本来就在你手上。若锁不可重入，你会在自己家门口把自己锁死。

**`wait` / `notify` = 候诊室。** 病人（线程）进屋发现医生还没准备好，就主动把钥匙交出来、去候诊室躺着（`wait()`）；医生准备好后到候诊室喊一声（`notify()`）。关键在于：**去候诊室之前必须先交出钥匙**，否则医生永远进不来。

**死锁 = 两个人各拿一半工具。** Alice 拿到了文件 A 的锁，Bob 拿到了网络连接 B 的锁；Alice 需要 B，Bob 需要 A。两人都不肯放手，于是永远僵住。

## 5. 原理与推导

### 5.1 从 `StringConverter` 到 `synchronized`

第 17 讲的 `StringConverter.get()` 里，`o == null` 的检查与 `o.toString()` 的调用之间存在窗口。修复的直觉是「把这两步打包成一个不可分割的单元」：

```java
public synchronized String get() {
    if (o == null) return "null";
    return o.toString();
}
```

`set()` 也必须加 `synchronized`（否则写不受锁约束，互斥只保护了一半）。课件用 `SynchronizedIncrementTest.java` 演示了同样的思路。

课件还展示了**锁的粒度选择**——不必锁整个方法，只锁需要保护的语句：

```java
synchronized (fromAcct) {
    if (fromAcct.getBalance() >= 30) {
        toAcct.deposit(30);
        fromAcct.withdrawal(30);
    }
}
```

这里把「查余额 + 转账」整体放进 `fromAcct` 的锁里，消除了第 17 讲转账例子中的丢失更新。

### 5.2 为什么 `synchronized` 同时解决了两件事

`synchronized` 提供两个保证，缺一不可：

1. **互斥（mutual exclusion）**：同一时刻只有一个线程执行临界区，消除交错；
2. **可见性（visibility）**：退出 `synchronized` 块时，线程对共享变量的修改被刷出；进入时重新读取最新值。

第 2 点是很多人忽略的：即使你的临界区只有一条写语句、不存在交错问题，`synchronized` 仍然必要，因为它建立了 happens-before 边，让别的线程**看得见**你的写。

### 5.3 `wait` / `notify` 的正确用法

`java.lang.Object` 上定义了这些方法：

```java
void wait();                                  // 无限等待
void wait(long timeout);                      // 带超时
void wait(long timeout, int nanos);
void notify();                                // 唤醒一个等待者
void notifyAll();                             // 唤醒全部等待者
```

三条铁律：

1. **只能在持有该对象锁时调用**，否则抛 `IllegalMonitorStateException`；
2. `wait()` 会**原子地**释放锁并挂起，返回前重新获取锁——这解决了「睡觉时还占着钥匙」的矛盾；
3. **必须放在 `while` 循环里**重新检查条件：

```java
synchronized (lock) {
    while (!condition) {     // 用 while 而不是 if
        lock.wait();
    }
    // 此处 condition 为真
}
```

为什么不能用 `if`？因为被唤醒不等于条件成立：可能另一条线程先一步消费掉了资源（虚假唤醒 spurious wakeup，或 `notifyAll` 唤醒了多个等待者）。醒来后必须重新检查。课件示例为 `Blocker.java`、`Notifier.java`、`NotifyExample.java`。

### 5.4 可重入性

Java 的锁是**可重入**的：线程持锁计数加一，退出时减一，减到零才真正释放。因此下面是合法的：

```java
synchronized (lock1) {
    synchronized (lock2) {   // 同时持有两把锁
        // ...
    }
}
```

可重入避免了「自锁」，但同时持有两把锁正是死锁的温床——这是下一个话题。

### 5.5 死锁的构造

课件给出 `Counter.java` 与 `DeadlockExample.java`：Alice 持有文件 A 的锁、等待网络连接 B 的锁；Bob 持有 B、等待 A。两人互相等待。

用等待图表示：

```
   T1 ──等待──> T2
   ↑             │
   └────等待──────┘
```

有向图出现环 ⟺ 死锁。死锁的四个必要条件（课件未逐条命名，这里按经典表述列出）：

1. **互斥**：资源同一时刻只能被一个线程持有；
2. **持有并等待**：持有资源的同时等待新资源；
3. **不可剥夺**：不能强行从持有者手里抢走资源；
4. **循环等待**：存在一个线程等待环。

四个条件**同时**成立才会死锁；破坏任意一个即可预防。

### 5.6 应对死锁的四条路

课件把处理方式归为三类（检测、避免、替代方案）：

**① 检测（detection）**：静态检测（分析代码中的加锁顺序）或动态检测（运行时维护等待图，发现环就报警或回滚）。代价高，适合调试。

**② 避免（avoidance）——全序加锁**：给所有锁规定一个全局次序（total order），要求每个线程**按序**获取。例如规定顺序 `lock1 < lock2 < lock9 < lock42`：线程取得 `lock42` 之后就不能再去取 `lock30`。既然是全序，环就不可能形成——循环等待条件被破坏。

**③ 重启（restart）**：如果无法保证顺序，就允许「死锁后重启」。任意杀掉并重启长跑的线程。优点是简单，缺点是可能反复重启、丢失工作。

**④ 乐观并发控制（optimistic concurrency control）**：干脆不加锁，先做（通常基于 copy-on-write，在副本上修改），提交时检查有没有冲突；有冲突就丢弃重做。这是数据库领域的主流思路之一（第 25 讲会再遇到）。

### 5.7 活锁与饥饿

重启策略带来两个新的坏情况：

- **Livelock（活锁）**：两条线程不断检测到冲突并互相退让，都保持「礼貌」地重试，系统整体毫无进展。类比：两人在走廊相遇，同时向左让、又同时向右让。
- **Starvation（饥饿）**：某些任务因为其它任务被反复重启/优先，长期得不到执行机会。

区别要点：死锁是「全部阻塞」，活锁是「全部在跑但无进展」，饥饿是「部分线程长期无进展」。

### 5.8 happens-before：Java 内存模型的骨架

课件列出五条 happens-before 规则：

| 规则 | 内容 |
|---|---|
| 程序顺序 | 同一线程内，前面的语句 happens-before 后面的语句 |
| 锁 | 对同一把锁的 `unlock` happens-before 后续的 `lock` |
| 线程启动 | `Thread.start()` happens-before 新线程中的任何动作 |
| 线程终止 | 线程中的所有动作 happens-before 其它线程从 `join()` 成功返回 |
| `volatile` | 对 `volatile` 字段的写 happens-before 后续对同一字段的读 |

此外 `notify()` happens-before 被唤醒线程从 `wait()` 返回。该关系是**传递**的：A → B 且 B → C 则 A → C。

**判定方法**：如果两条访问（同一变量、至少一个写）**没有被 happens-before 排序**，就存在数据竞争。这给了我们一个可操作的判据，而不必枚举所有交错。

### 5.9 `volatile` 能做什么、不能做什么

`volatile` 保证：

- 写立即对其他线程可见（不驻留缓存）；
- 禁止编译器/处理器把 `volatile` 访问与其它内存操作重排序。

`volatile` **不**保证：

- 复合操作（`count++` 仍是三步）的原子性；
- 多个字段之间的一致性（两个 `volatile` 字段不构成一个原子快照）。

因此 `volatile` 适合「一个线程写、多个线程读」的开关/标志位，不适合计数器。

### 5.10 高层抽象：把锁交给库

课件把 Java 提供的高层工具分为三层：

1. **`volatile`**：最小的可见性保证；
2. **`java.util.concurrent.atomic`**：`AtomicInteger` 等，用 CAS 指令实现无锁原子更新；
3. **`java.util.concurrent`**：并发容器、线程池、同步器。

`AtomicInteger` 的常用 API：

```java
int get();
void set(int newValue);
int getAndSet(int newValue);
int getAndAdd(int delta);
```

另有 `AtomicIntegerArray`、`AtomicBoolean`、`AtomicLong` 等。

`java.util.concurrent` 中的关键类：

- `ConcurrentHashMap`：线程安全的哈希表；
- `BlockingQueue`（实现：`ArrayBlockingQueue`、`SynchronousQueue`）：阻塞队列，天然适合生产者–消费者；
- `CopyOnWriteArrayList`：写时复制的列表；
- 线程池与 `Executor`：把「任务」与「线程管理」解耦；
- `Locks` 与 `Latches`：更灵活的显式锁与倒计时门闩。

### 5.11 三种并发容器的实现原理

**`ConcurrentHashMap` —— 锁分段（lock striping）**：内部维护多把锁，每把锁负责哈希表的一个区域。两条线程操作不同区域时互不阻塞，只有落到同一段才竞争。这把「一把大锁」换成了「多把小锁」，显著提升了并发度。

**`BlockingQueue` —— 用条件等待实现背压**：

- `SynchronousQueue`：没有容量，每个 `put` 直接等待一个对应的 `poll`（手递手交接）；
- `ArrayBlockingQueue`：有界数组，队满时 `put` 阻塞、队空时 `poll` 阻塞，内部正是用 `wait`/`notify`（或其等价机制）实现。

阻塞而不是丢弃，使生产者的速度自动被消费者限制——这就是背压（backpressure）。

**`CopyOnWriteArrayList` —— 写时复制**：每次写操作都复制一份底层数组、在副本上修改、再原子地换掉引用。读操作完全无锁，因此**读多写少**时性能极佳；写多时每次都要 O(n) 复制，非常昂贵。

### 5.12 选择策略的一张表

| 场景 | 推荐工具 | 理由 |
|---|---|---|
| 单个计数器 | `AtomicInteger` | 无锁 CAS，开销远低于抢锁 |
| 一个布尔开关 | `volatile boolean` | 只需可见性，不需原子复合操作 |
| 高并发键值缓存 | `ConcurrentHashMap` | 锁分段，多线程可并行读写不同段 |
| 生产者–消费者 | `BlockingQueue` | 内置阻塞与唤醒，不必手写 `wait`/`notify` |
| 读极多写极少 | `CopyOnWriteArrayList` | 读无锁；写代价高但很少发生 |
| 一组操作必须整体互斥 | `synchronized` 块 | 简单、可读、JVM 已高度优化 |

## 6. 代码示例

### 6.1 官方课程代码

讲义 `19-concurrency-part2.pdf` 第 10 页给出 `synchronized` 的两种写法：

```java
synchronized void foo() { ... }        // 锁住 "this"

synchronized (fromAcct) {
    if (fromAcct.getBalance() >= 30) {
        toAcct.deposit(30);
        fromAcct.withdrawal(30);
    }
}
```

同页引用示例 `SynchronizedIncrementTest.java`。

第 11 页给出 `java.lang.Object` 的协调方法原型：

```java
void wait();
void wait(long timeout);
void wait(long timeout, int nanos);
void notify();
void notifyAll();
```

并引用示例 `Blocker.java`、`Notifier.java`、`NotifyExample.java`。

第 12 页的嵌套加锁示意（可重入）：

```java
synchronized (lock1) {
    synchronized (lock2) {
        // ...
    }
}
```

第 13 页引用死锁示例 `Counter.java`、`DeadlockExample.java`；第 16 页给出全序加锁的示意：

```java
acquire(lock1);
acquire(lock2);
acquire(lock9);
acquire(lock42);
// 此后不得再 acquire(lock30)，否则破坏全序
```

第 22 页给出 `AtomicInteger` 的 API 列表（见 5.10 节）。

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：生产者–消费者，展示 `wait` 必须在 `while` 中调用。**

```java
public class BoundedBuffer<T> {
    private final Object[] items;
    private int count = 0;          // 受 this 锁保护

    public BoundedBuffer(int cap) { items = new Object[cap]; }

    public synchronized void put(T x) throws InterruptedException {
        while (count == items.length) {   // 用 while：醒来后必须重新检查
            wait();                       // 原子地释放锁并挂起
        }
        items[count++] = x;
        notifyAll();                      // 唤醒可能在等的消费者
    }

    @SuppressWarnings("unchecked")
    public synchronized T take() throws InterruptedException {
        while (count == 0) {
            wait();
        }
        T x = (T) items[--count];
        notifyAll();
        return x;
    }
}
```

若把两处 `while` 改成 `if`，在「一次 `notifyAll` 唤醒多个生产者」时会出现越界写——这就是必须重新检查条件的具体后果。

**示例 B：用全序加锁消除死锁。**

```java
public class OrderedTransfer {
    private final Object lock = new Object();   // 一把全局锁，最简单也最保守

    public void transfer(Account from, Account to, int amount) {
        // 用对象标识哈希决定加锁顺序：所有线程遵守同一顺序，环无法形成
        Account first  = (System.identityHashCode(from) < System.identityHashCode(to)) ? from : to;
        Account second = (first == from) ? to : from;
        synchronized (first) {
            synchronized (second) {
                if (from.getBalance() >= amount) {
                    from.withdraw(amount);
                    to.deposit(amount);
                }
            }
        }
    }
}
```

> 待核实：`System.identityHashCode` 在极少数情况下可能相等（哈希碰撞），生产代码通常再加一个决胜的 tie-breaker（例如自增的唯一 ID）。

**示例 C：`volatile` 的正确与错误用法。**

```java
public class VolatileDemo {
    private volatile boolean running = true;   // 正确：只需可见性的开关
    private volatile int counter = 0;          // 错误：counter++ 仍不是原子操作

    public void stop() { running = false; }    // 另一条线程能立刻看到

    public void bump() { counter++; }          // 依然会丢失更新！
}
```

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| `synchronized` | `volatile` | `synchronized` 同时给互斥与可见性，能保护复合操作；`volatile` 只给可见性与禁止重排序，不保证原子性 |
| Deadlock（死锁） | Livelock（活锁） | 死锁中线程全部阻塞、CPU 空闲；活锁中线程都在运行却互相退让，同样无进展 |
| Livelock（活锁） | Starvation（饥饿） | 活锁是「整体」无进展；饥饿是「部分」线程长期得不到资源，系统整体可能仍在推进 |
| `wait()` | `sleep()` | `wait()` 是 `Object` 的方法、会释放锁、需被 `notify` 唤醒；`sleep()` 是 `Thread` 的静态方法、**不释放锁**、到点自动返回 |
| `notify()` | `notifyAll()` | `notify()` 随机唤醒一个等待者，可能唤醒「错误的那一个」导致卡死；`notifyAll()` 唤醒全部，让它们各自重新检查条件，更安全但开销略大 |
| Coarse-grained lock（粗粒度锁） | Fine-grained lock（细粒度锁） | 粗粒度开销低但并发度差；细粒度并发度高但易出错（加锁顺序、动态创建的锁） |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-214/slides/19-concurrency-part2.pdf`
- **总页数**：27 页
- **本节重点页码**：
  - 第 6 页：重申 64 位 `long` 非原子
  - 第 7 页：本讲大纲
  - 第 8–9 页：并线例子与 `StringConverter` 竞态回顾
  - 第 10 页：内在锁与 `synchronized` 两种写法
  - 第 11 页：`wait` / `notify` / `notifyAll` API
  - 第 12 页：锁的可重入性
  - 第 13–14 页：死锁例子与三类处理方式
  - 第 15–16 页：等待图与全序加锁
  - 第 17–18 页：重启与乐观并发控制
  - 第 19 页：活锁与饥饿
  - 第 20–21 页：`volatile`、`java.util.concurrent` 概览、happens-before 五规则
  - 第 22 页：`AtomicInteger` API
  - 第 23 页：`java.util.concurrent` 类目
  - 第 24 页：`ConcurrentHashMap` 锁分段
  - 第 25 页：`BlockingQueue`（`SynchronousQueue`、`ArrayBlockingQueue`）
  - 第 26 页：`CopyOnWriteArrayList`
- **原始链接**：https://www.cs.cmu.edu/~aldrich/214/slides/19-concurrency-part2.pdf

## 9. 对应视频

未找到官方公开录像。

## 10. 本节复习

- 每个 Java 对象自带一把内在锁；`synchronized` 方法锁 `this`，静态方法锁 `Class` 对象，代码块锁指定对象。
- `synchronized` 同时提供互斥与可见性，两者缺一不可。
- `wait()` 原子地释放锁并挂起，返回前重新获取锁；必须放在 `while` 循环中重新检查条件。
- 锁可重入，避免自锁，但嵌套持有多把锁是死锁的温床。
- 死锁四条件：互斥、持有并等待、不可剥夺、循环等待；破坏任一即可预防。
- 等待图有环 ⟺ 死锁；全序加锁是破坏循环等待的标准手段。
- 活锁 = 都在动却无进展；饥饿 = 部分线程长期得不到资源。
- happens-before 提供可操作的判据：未被它排序的「同变量 + 至少一个写」就是数据竞争。
- `volatile` 只管可见性与重排序，不管复合操作的原子性。
- `ConcurrentHashMap` 用锁分段、`BlockingQueue` 用阻塞实现背压、`CopyOnWriteArrayList` 适合读多写少。

## 11. 自我检查

**Q1.** 一个类有两个 `synchronized` 实例方法 `a()` 与 `b()`，另有 `c()` 未加 `synchronized`。两条线程分别调用 `a()` 与 `b()` 会互相阻塞吗？调用 `a()` 与 `c()` 呢？如果方法是 `static synchronized` 呢？

**Q2.** 下面这段代码有什么问题？请给出修正，并说明为什么必须修：

```java
synchronized (lock) {
    if (queue.isEmpty()) {
        lock.wait();
    }
    consume(queue.remove());
}
```

**Q3.** 请用等待图论证：若所有线程都按 `A < B < C` 的顺序加锁，是否可能出现死锁？若某个线程违反顺序先锁 B 再锁 A，可能吗？

**Q4.** 一段代码用 `volatile int count` 做计数器，两条线程各 `count++` 十万次。最终结果一定等于二十万吗？为什么？`AtomicInteger` 为何能解决？

**Q5.** 一个服务需要频繁读取配置（每秒数十万次）、配置极少变更（每天几次）。你会选 `ConcurrentHashMap` 还是 `CopyOnWriteArrayList` 或其它？说明理由与代价。

<details>
<summary>参考答案</summary>

**A1.** `a()` 与 `b()` 都锁 `this`，同一实例上会互相阻塞（互斥）。`a()` 与 `c()` 不会——`c()` 不获取锁，因此可以在 `a()` 执行期间并发运行，也**不受**锁带来的可见性保护（`c()` 可能读到过期值）。若改成 `static synchronized`，锁的是 `Class` 对象，与实例锁 `this` 是**两把不同的锁**，因此一个实例的静态同步方法与实例同步方法不会互斥——这是极常见的误解。

**A2.** 问题有三处：① 用 `if` 而非 `while`，被唤醒后没有重新检查 `isEmpty()`；② `wait()` 可能被虚假唤醒；③ 若 `queue` 被其它线程消费空，醒来后 `remove()` 会失败。修正：

```java
synchronized (lock) {
    while (queue.isEmpty()) {
        lock.wait();
    }
    consume(queue.remove());
}
```

（真实代码应优先直接用 `BlockingQueue.take()`，把等待逻辑交给库。）

**A3.** 不会。全序意味着所有线程的加锁序列都是全局次序的一个上升子序列；死锁要求存在循环等待，即 T1 等 T2 持有的锁、T2 等 T1 持有的锁，这要求两人都持有一把「较大」的锁去等一把「较小」的锁，与全序矛盾。若某线程先锁 B 再锁 A，就同时存在 B→A 的反向边，此时与守序线程之间可能形成 A→B→A 的环，死锁重新可能。

**A4.** 不一定。`volatile` 只保证每次读都读到最新值、写立即可见，但 `count++` 仍是「读—加—写」三步，两条线程可能读到同一个旧值，各加一次却只生效一次。`AtomicInteger.incrementAndGet()` 用 CPU 的 CAS（compare-and-swap）指令把「比较 + 写回」做成一条不可分割的硬件操作，失败则重试，因此不会丢失更新。

**A5.** 三者都不理想，应按需求选：`ConcurrentHashMap` 更适合「按键读取大量不同键」的场景，若配置是单个对象则不合适；`CopyOnWriteArrayList` 适合「列表读多写极少」，每次写复制整个数组——每天只写几次，代价可忽略，读完全无锁，是合理选择。更好的方案是把整份配置做成一个**不可变对象**，用 `volatile` 引用指向它：读只需一次 volatile 读，更新时构造新对象再原子替换引用（copy-on-write 的极简版）。这正是第 19 讲「不可变性」的核心思想。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-17-Concurrency-Part1]]——竞态条件与原子性。
- 下一讲：[[15-214-19-Concurrency-Part3]]——不可变性、Fork/Join、前缀和并行化。
- 相关讲次：[[15-214-24-Static-Analysis-for-Concurrency]]（用注解与静态分析检查锁的使用）、[[15-214-25-Data-Consistency]]（事务与两阶段提交）。
- 课程导航：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]、[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]。
- 术语条目：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Mutual Exclusion 互斥、Critical Section 临界区、Lock 锁、Deadlock 死锁、Livelock/Starvation 活锁/饥饿、Monitor 监视器）。
