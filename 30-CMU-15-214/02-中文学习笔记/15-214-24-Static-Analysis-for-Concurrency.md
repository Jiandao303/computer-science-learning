---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L24
topic: Static Analysis for Concurrency - Race Detection, Region Locking, and Cut Points
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 静态分析
  - 并发
  - 竞态条件
  - 数据竞争
  - 锁
  - 类型状态
---

# 第 24 讲 并发的静态分析（Static Analysis for Concurrency）

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。

## 1. 本节学习目标

- 能说明竞态条件（race condition）与数据竞争（data race）的精确定义，并解释二者的区别。
- 能解释为什么竞态是静态分析最难处理的目标：非局部性、坏代码污染好代码、难以测试。
- 能说清「不变式（invariant）被违反才算错误」这一判断标准，以及为什么必须先知道设计意图。
- 能列举避免竞态的四种实用手段，并说明锁粒度（lock granularity）的权衡。
- 能读懂 Fluid 的 `@RegionLock` / `@requiresLock` / `@aggregate` 注解，并说明每种分析结果的含义。
- 能解释别名（aliasing）问题为什么会破坏模块化推理，以及 `@Unique` / `@NotAliased` 如何解决它。
- 能解释构造器与继承带来的分析困难。
- 能说明 cut point 的定义与 `@RequiresLock` 检查的作用。

## 2. 前置知识

- [[15-214-17-Concurrency-Part1]]：线程、交错（interleaving）、竞态条件的直观例子。
- [[15-214-18-Concurrency-Part2]]：`synchronized`、监视器（monitor）、死锁、`wait`/`notify`。
- [[15-214-19-Concurrency-Part3]]：不可变性、线程封闭、fork/join。
- [[15-214-23-Static-Analysis]]：抽象解释、可靠性 vs 完备性、模型检验、规约与注解——本讲是它的直接延续。
- [[15-214-05-Object-Contracts-and-Exceptions]]：类不变式与规约。

## 3. 核心概念

- **Race Condition（竞态条件）**：程序的正确性依赖于线程的**相对时序**；某些交错会产生错误结果。
- **Data Race（数据竞争）**：两个线程访问同一内存位置，**至少一个是写**，且**没有任何同步机制**阻止它们同时发生。
- **Invariant（不变式）**：在「观察点」之间必须始终为真的条件；竞态之所以是 bug，是因为它可能违反不变式。
- **Design Intent（设计意图）**：开发者「打算」让哪些访问互斥；静态分析必须知道它才能判断对错。
- **Mutual Exclusion（互斥）**：保证同一时刻只有一个线程处于临界区。
- **Lock Granularity（锁粒度）**：一把锁保护多少数据；粗粒度简单但并发度低，细粒度并发度高但容易出错且开销大。
- **Region Lock（区域锁）**：Fluid 的抽象——用一个锁保护一组字段（一个「区域」）。
- **Aggregation（聚合）**：把多个对象实例的锁「聚」成一把类级别的锁（`@aggregate … into Instance`）。
- **Aliasing（别名）**：两个引用指向同一个对象；它让「这个对象的锁保护了哪些数据」变得难以静态判定。
- **Uniqueness（唯一性）**：某引用是通往该对象的唯一路径；有了唯一性，就能安全地转移所有权而无需同步。
- **Cut Point（切点）**：一段可以原子执行的代码区域（通常因为持有某把锁），其内部的中间状态对外不可见。
- **JSure**：本讲介绍的验证工具，检查代码是否遵守锁规约。

## 4. 通俗理解

**竞态为什么这么难查？** 课件用了一个真实的 `java.util.logging.Logger` bug 来说明。

`Logger` 有一个 `filter` 字段，`setFilter()` 会改它，`log()` 会读它。看起来只要在 `log()` 里加 `synchronized` 就安全了——但如果 `setFilter()` **没有加锁**，那么「读」的一方再怎么加锁也没用。好比你家门锁得再好，小偷是从没锁的后门进来的。

**这类 bug 的三个可怕之处**：

1. **错误不在出问题的地方**：崩溃点在 `log()`，但根因在 `setFilter()`。你盯着崩溃栈看一百遍也找不到。
2. **坏代码污染好代码**：`log()` 本来是正确同步的，却因为别人的错误而变得不安全。你**不能只检查一个模块就下结论**。
3. **测试几乎无效**：竞态窗口可能只有几纳秒，跑一万次单元测试也可能是绿的。

**所以需要静态分析**——它不跑程序，而是检查**所有**交错。但这就带来一个新问题：分析器怎么知道「哪些访问本该互斥」？

**答案是：它必须知道设计意图。** 就像交通警察不能只看车在动就开罚单——他得知道红绿灯是怎么设计的。课件里的一句话点破了全部难点：**「必须有设计意图才能判断一个竞态是不是 bug」**。

## 5. 原理与推导

### 5.1 引子：一个真实的 JDK bug

课件第 2–6 页剖析了 `java.util.logging.Logger` 的竞态。简化后的结构：

```java
public class Logger {
    private Filter filter;                       // 可被替换的过滤器

    public void setFilter(Filter newFilter) {
        filter = newFilter;                       // ← 没有 synchronized！
    }

    public void log(LogRecord record) {
        synchronized (this) {                     // ← 这里加了锁
            if (filter != null && !filter.isLoggable(record)) {
                return;
            }
        }
        // …实际写日志…
    }
}
```

**表面看 `log()` 是安全的**：它用 `synchronized (this)` 保护了对 `filter` 的读取。但 `setFilter()` 写入 `filter` 时**没有持锁**，所以：

- 线程 A 在 `log()` 里持锁读 `filter`；
- 线程 B 在 `setFilter()` 里无锁写 `filter`；
- 二者可以**同时**发生——这就是数据竞争。

**后果**：`log()` 可能读到 `filter` 的一个「撕裂」值（虽然在 32/64 位引用赋值上通常是原子的，但仍可能读到过期值），或者更微妙地——`filter` 与它内部状态之间的一致性被破坏。

**课件第 6 页给出的修复**：

```java
public synchronized void setFilter(Filter newFilter) {
    filter = newFilter;
}
```

只加两个词 `synchronized`，但如果没有工具提示，这个 bug 在 JDK 里潜伏了很久——因为它是**非局部**的：`log()` 看起来完全正确。

### 5.2 竞态与数据竞争的定义

课件第 7 页引用 Savage 等人（Eraser 论文）的定义：

> **A race condition** exists if two threads access the same variable, at least one is a write, and there is no explicit mechanism to prevent the accesses from occurring simultaneously.

拆成三个条件：

1. **两个线程**访问**同一变量**；
2. **至少一个是写**（读-读不算）；
3. **没有显式同步机制**阻止同时发生。

**注意第 3 条的关键词「显式（explicit）」**：这里的判据是**工程可检查的**——它不问「实际是否同时发生」（那取决于调度，不可判定），只问「有没有用一个机制声明它们不该同时发生」。这就是静态分析可以做的地方。

**竞态 vs 数据竞争的区别**（常被混淆）：

- **数据竞争**是按上述三条定义的**底层**现象，可以用工具机械检测；
- **竞态条件**是**语义**层面的概念——程序的正确性依赖时序。一个程序可以有竞态条件而没有数据竞争（例如两个线程用消息传递协调，但消息顺序错了），也可以有数据竞争而没造成实际错误（例如写同一个值）。

本讲主要讨论的是**数据竞争**这一类，因为它是可机械检测的。

### 5.3 竞态为什么是静态分析最难的目标

课件第 8 页列出三条难点：

**(1) 非局部错误（non-local errors）**

错误的表现位置与根因位置相距很远。`Logger` 的例子里，症状出现在 `log()`，根因在 `setFilter()`——可能在不同的文件、由不同的人、在不同的时间写。

**(2) 坏代码污染好代码（bad code spoils good code）**

这是并发分析独有的困难。在单线程程序里，一个函数只要自己不犯错就是对的；在并发程序里，**一个函数是否正确取决于它所有的调用者与被调用者**。你写了一个完美同步的 `log()`，别人写了个没同步的 `setFilter()`，你的代码就不安全了。

> 推论：**模块化推理在并发下失效**——而这正是 [[15-214-07-Design-Patterns]] 里信息隐藏的核心价值。并发的静态分析必须想办法把模块化「救回来」（本讲后半部分就是在做这件事）。

**(3) 难以测试（hard to test）**

竞态窗口可能极小，依赖于处理器数量、调度策略、负载。测试能证明「有 bug」（跑出一次失败），但**永远不能证明「没有 bug」**——这与 [[15-214-23-Static-Analysis]] 里的可靠/完备框架完全吻合：测试是严重欠近似的。

### 5.4 什么才算错误：不变式

课件第 9 页给出判据：

> **What is an error?**
> - A violation of an invariant
> - Many possible invariants:
>   - A variable should always be non-null
>   - A list should never contain duplicates
>   - A bank account should never have a negative balance
>   - A buffer should never hold more elements than its capacity
>   - The sum of the balances of all accounts should be constant

**竞态本身不是错误，「竞态导致不变式被违反」才是错误。**

这个区分非常重要，因为：

- 不是所有共享访问都是 bug。两个线程同时读一个不可变对象完全没问题。
- 分析器如果对「所有共享访问」都报警，会产生海量假阳性（参见 [[15-214-23-Static-Analysis]] 第 53 页的「五个好处不可兼得」）。
- 只有知道「哪条不变式该守」，才能判断哪些访问需要互斥。

### 5.5 设计意图

课件第 10 页：

> **Design intent**
> - Which accesses are supposed to be mutually exclusive?
> - Which accesses can happen concurrently?
> - The system designer decides
> - **Must know the design intent to tell whether a race is a bug**

这段话确立了整个讲的方向：**并发静态分析必须依赖规约（specification）**。这与 [[15-214-23-Static-Analysis]] 第 41 页「模块化分析需要规约」是同一条原理，但在并发下更紧迫——因为并发下**根本不存在「看一下代码就知道对不对」的可能**。

### 5.6 避免竞态的五种手段

课件第 11 页列出五种方式：

| 手段 | 做法 | 评价 |
|---|---|---|
| **线程局部化（thread-local）** | 让数据只属于一个线程 | 简单安全，但表达力受限 |
| **加锁（locking）** | 用 `synchronized` / `Lock` 保护共享数据 | 最常用，但容易漏、容易死锁 |
| **禁用中断（disabling interrupts）** | 关中断保证不被打断 | 只适合内核的极短临界区 |
| **分析所有交错（analyze all interleavings）** | 穷举所有可能的执行顺序 | 正确但不可扩展（状态爆炸） |
| **事务内存（transactional memory）** | 让一组操作原子化，冲突时自动重试 | 优雅，但当时（2013）生态不成熟 |

课件还提了一个重要观点：**这些手段里有些可以「组合」，有些不能**。比如线程局部化与加锁可以并存（把锁对象本身做成线程局部的），但「禁用中断」与「事务内存」在用户态程序里不适用。

**为什么这五种手段对静态分析重要？** 因为分析器的任务就是**验证开发者是否正确地使用了其中一种**。前两种（线程局部、加锁）是分析器最常检查的目标。

### 5.7 锁粒度

课件第 12 页讨论粗细粒度：

**粗粒度（coarse-grained）**：
- 一把大锁保护所有共享状态；
- 优点：简单，不容易漏；
- 缺点：并发度低（所有线程排队），可能成为性能瓶颈。

**细粒度（fine-grained）**：
- 每个数据结构（甚至每个字段）一把锁；
- 优点：并发度高；
- 缺点：容易漏锁、容易死锁（需要按固定顺序获取多把锁）、锁本身有开销。

**课件的关键提醒**：粒度不只是性能问题，**它决定了分析器能检查什么**。如果代码用一把大锁，分析器只需检查「所有共享访问都在 `synchronized` 块里」；如果用细粒度锁，分析器必须知道「哪个字段归哪把锁管」——这就是**区域锁（region lock）**概念的来源。

### 5.8 JSure 与 Fluid：让分析可模块化

课件第 13 页介绍 **JSure**（一个验证工具，来自 UT Austin 的研究，与本课程作者 Jonathan Aldrich 的工作密切相关）。它的核心思想是：**用注解把「设计意图」写进代码，然后机械地检查**。

第 15 页给出 Fluid 注解的语法：

```java
@RegionLock("FL is this protects filter")
private final Object filterLock = new Object();

private Filter filter;

@RequiresLock("FL")
public void setFilter(Filter newFilter) {
    filter = newFilter;
}

@RequiresLock("FL")
public void log(LogRecord record) {
    if (filter != null && !filter.isLoggable(record)) return;
    // …
}
```

逐个解释：

- **`@RegionLock("FL is this protects filter")`**：声明「`filter` 这个字段由 `this` 这把锁保护」，并给这个区域锁起名叫 `FL`。读法：`FL` **is** `this`（锁对象），**protects** `filter`（被保护的数据）。
- **`@RequiresLock("FL")`**：调用这个方法**必须持有 `FL`**。这就是把「设计意图」写成机器可检查的形式。
- 分析器检查两件事：① 每个访问被保护字段的地方是否持有对应锁；② 每个 `@RequiresLock` 方法的调用者是否持锁。

**注意这个设计的精妙**：注解让分析**变成模块化的**——分析一个方法时，只需要知道它的 `@RequiresLock` 声明，不需要看它的调用者。这与 [[15-214-23-Static-Analysis]] 里「注解隔离函数、把立方复杂度降为线性」完全一致。

### 5.9 聚合：同一类的所有实例共用一把锁

课件第 16 页介绍 `@aggregate`：

```java
@RegionLock("FL is lock protects filter")
@Aggregate("Instance into Instance")
public class Logger {
    private final Object lock = new Object();
    private Filter filter;
}
```

**问题背景**：`@RegionLock("FL is this protects filter")` 说「这把锁是 `this`」——即**每个 `Logger` 实例有自己的一把锁**。但如果实际代码里所有 `Logger` 实例共享同一份静态状态，或者你想用**类级别**的锁（`Logger.class`），就需要改变锁的「来源」。

**`@aggregate … into Instance`** 的作用：把**所有实例**的锁聚合成一个（类级别的）实例。这样分析器就知道「所有 `Logger` 对象共用一把锁」。

课件还提到相关的 `@Unique`：

- **`@Unique`**：这个引用是通往该对象的**唯一**路径（没有别名）。
- **`@Unique("return")`**：这个方法返回一个**唯一**引用。

### 5.10 三类分析结果

课件第 17 页给出工具输出的三种状态：

| 结果 | 含义 | 后续动作 |
|---|---|---|
| **Consistent（一致）** | 代码满足所有锁规约，未发现竞态 | 通过 |
| **Inconsistent（不一致）** | 发现确定的违规（某处访问未持锁） | 必须修 |
| **Requested annotations（请求注解）** | 分析器信息不足，需要开发者补充注解 | 加注解后重跑 |

**第三类结果非常重要，也常被误解**：它不是「分析失败」，而是**分析器在向开发者询问设计意图**。这正好呼应 5.5 节——没有设计意图就无法判断对错，所以工具必须能「问」。

从工程角度看，这个三分法比「报错/不报错」更诚实：它明确承认「我不知道」是第三种合法状态。这与 [[15-214-23-Static-Analysis]] 里「真阳性的技术定义 vs 工程定义」一脉相承——工具的价值在于让人做出判断，而不是替人做判断。

### 5.11 增量保证

课件第 19 页强调 **incremental guarantees（增量保证）**：

- 分析是**增量**的：只重新检查改动的部分；
- 但保证是**全局**的：只要每个部分都一致，整体就一致；
- 这让工具能用在大型代码库上（每次编译只跑几秒，而不是几小时）。

**这与 [[15-214-23-Static-Analysis]] 里微软 SAL 的「增量性」激励完全一致**：

> 每次编译都检查「代码 ↔ 设计」的一致性；每一份努力都有回报；部分注解也有收益。

### 5.12 别名问题

课件第 21 页提出并发分析最棘手的障碍：

> **The aliasing problem**
> - Aliasing: two references to the same object
> - Makes it hard to know which lock protects which data
> - Modular reasoning is hard when objects can be aliased

**具体困难**：

```java
class Buffer {
    private int[] data;
    public void put(int x) { data[0] = x; }     // 谁该保护 data？
}

Buffer b1 = new Buffer();
Buffer b2 = b1;              // 别名！
```

如果分析器认为「`b1` 的锁保护 `b1.data`」，那么通过 `b2` 访问同一个 `data` 时，它该检查哪把锁？如果 `b1` 和 `b2` 在不同线程里，用不同的锁，那么即使两边都「正确加锁」，数据仍然没有真正互斥。

**更糟的情形**：把一个对象的内部数据「泄漏」出去（return 一个内部数组的引用，或把它存到外部可见的地方），那么内部锁就完全失效了——外部代码可以绕过锁直接访问。

**Fugue 的解法**（课件提到）：**`@NotAliased`** 注解——声明「这个引用没有别名」。有了它，分析器就能确定「通过这个引用访问的对象，只可能被这把锁保护」。

**`@Unique` 的语义**正是 `@NotAliased` 的加强版：唯一引用不仅没有别名，还可以**转移所有权**（transfer）。这在并发里极其有用：如果一个对象是唯一的，你就可以把它从一个线程安全地交给另一个线程，**不需要任何锁**——因为不存在并发访问。这正是 [[15-214-19-Concurrency-Part3]] 里「线程封闭 + 安全发布」的理论基础。

### 5.13 构造器与继承

课件第 23 页列出两个「边缘但致命」的问题：

**构造器（constructors）**：
- 对象在构造完成前就被 `this` 逃逸（escape）出去了吗？
- 构造器里调用可被覆写的方法，会不会让子类看到「半成品」对象？
- 构造期间需要持锁吗？（通常不该，因为对象还没发布——但如果有 `this` 逃逸就必须）

**继承（inheritance）**：
- 子类是否遵守父类的锁规约？
- 子类新增的字段归哪把锁管？
- 父类的方法被子类覆写后，`@RequiresLock` 还成立吗？

**这与 [[15-214-26-History-and-Future-of-Objects]] 里提到的「脆弱基类（fragile base class）」问题同源**：继承让「局部推理」变得困难，因为子类可以改变父类假设的前提。在并发下，这个问题被放大了——一个不遵守锁规约的子类可以让整个父类层次都不安全。

**工程建议**：并发类的设计应优先**组合（composition）而非继承（inheritance）**，或者把类声明为 `final`。这与 [[15-214-07-Design-Patterns]] 里的「优先组合而非继承」原则完全一致。

### 5.14 Cut Points

课件第 25–27 页介绍 **cut points（切点）**：

> **Cut points**
> - A region of code that can be executed atomically
> - Usually because a lock is held
> - Intermediate states inside a cut point are not visible to other threads

**为什么需要切点？** 因为在 [[15-214-23-Static-Analysis]] 的模型检验里，分析器要穷举所有线程交错。但穷举**每一条指令**的交错是不可行的。切点把代码切成若干「原子块」——**块内部不产生交错**，只在块之间产生。这把交错数从指数级降到可控。

**例子**（课件第 27 页）：

```java
class Buf {
    private int[] data;
    private int size;

    @RequiresLock("BufLock")
    public void add(int x) {
        data[size] = x;      // ← 切点从这里开始
        size++;              // ← 到这里结束（持锁期间）
    }
}
```

因为整个方法持 `BufLock`，所以 `data[size] = x; size++;` 对外表现为**一个原子操作**——其他线程永远看不到「元素写入了但 `size` 没加」的中间态。

**切点的三个用途**：

1. **分析可扩展**：交错只在切点边界发生，状态空间大幅缩小；
2. **规约可表达**：「这个方法原子地完成 X」是一个可以写下来的契约；
3. **推理更简单**：调用者可以把整个方法当作一条指令来看。

**注意 `@RequiresLock("BufLock")` 在这里的双重作用**：它既是「调用者必须持锁」的**义务**，也是「方法内部原子」的**保证**——因为持锁就排除了其他持同一把锁的线程。这就是为什么 Fluid 的注解能同时支持「检查」与「推理」。

### 5.15 本讲总结

课件第 29 页总结要点：

- 竞态是「两个线程访问同一变量、至少一个写、没有显式同步」；
- 竞态的三大难点：非局部、污染、难测；
- 错误 = 不变式被违反，而判断不变式需要**设计意图**；
- 用注解（`@RegionLock`、`@RequiresLock`、`@aggregate`、`@Unique`）把设计意图写进代码；
- 分析结果三态：一致 / 不一致 / 请求注解；
- 别名问题是模块化推理的最大障碍，唯一性注解是解法；
- 切点让「原子性」既可分析又可规约。

## 6. 代码示例

### 6.1 官方课程代码

**第 2–6 页：`java.util.logging.Logger` 的竞态**

有 bug 的版本（课件用图形化方式呈现字段与方法的关系；此处按课件语义还原成可编译形式）：

```java
public class Logger {
    private Filter filter;

    public void setFilter(Filter newFilter) {
        filter = newFilter;                 // 未同步的写
    }

    public void log(LogRecord record) {
        synchronized (this) {               // 已同步的读
            if (filter != null && !filter.isLoggable(record))
                return;
        }
        // …输出日志…
    }
}
```

修复（课件第 6 页）：

```java
public synchronized void setFilter(Filter newFilter) {
    filter = newFilter;
}
```

**第 15 页：Fluid 区域锁注解**

```java
@RegionLock("FL is this protects filter")
private final Object filterLock = new Object();

private Filter filter;

@RequiresLock("FL")
public void setFilter(Filter newFilter) {
    filter = newFilter;
}
```

**第 16 页：`@aggregate` 与 `@Unique`**

```java
@RegionLock("FL is lock protects filter")
@Aggregate("Instance into Instance")
public class Logger {
    private final Object lock = new Object();
    private Filter filter;
}
```

课件同时列出：

```
@Unique
@Unique("return")
```

**第 21 页：别名问题（Fugue 的 `@NotAliased`）**

课件的注解写作：

```
@NotAliased
```

**第 27 页：cut point 与 `@RequiresLock`**

```java
@RequiresLock("BufLock")
public void add(int x) {
    data[size] = x;
    size++;
}
```

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：复现 `Logger` 竞态，并演示为什么「只锁读的一边」没用。**

```java
public class BrokenLogger {
    private Filter filter;

    public void setFilter(Filter newFilter) {
        filter = newFilter;                      // 未同步
    }

    public void log(String msg) {
        synchronized (this) {
            if (filter != null && !filter.accept(msg)) return;
        }
        System.out.println(msg);
    }

    interface Filter { boolean accept(String msg); }

    public static void main(String[] args) throws Exception {
        BrokenLogger logger = new BrokenLogger();
        logger.setFilter(m -> m.startsWith("ERR"));

        Thread writer = new Thread(() -> {
            for (int i = 0; i < 100_000; i++) {
                logger.setFilter(i % 2 == 0 ? (m -> true) : (m -> false));
            }
        });
        Thread reader = new Thread(() -> {
            for (int i = 0; i < 100_000; i++) logger.log("hello " + i);
        });
        writer.start(); reader.start();
        writer.join(); reader.join();
        System.out.println("跑完了——注意：这个程序通常不会崩溃，");
        System.out.println("但它的行为是不确定的（取决于读到哪个 filter）");
    }
}
```

**这个示例的教育价值恰恰在于「它不崩」**：竞态 bug 的可怕之处不是它总出错，而是它**偶尔**出错。`reader` 读到的 `filter` 可能是旧的、新的，甚至（在某些 JVM/架构上）是一个未完全构造的对象。测试跑一万遍也可能是绿的——这正是课件第 8 页「难以测试」的实证。

**示例 B：用 `@RegionLock` 的风格手写一个「锁规约检查器」（简化版）。**

```java
import java.util.*;

/**
 * 极简的锁规约检查器：
 * 用一组「(方法名, 是否持锁)」的记录来模拟静态分析的结果。
 * 真实工具（JSure）是分析字节码/源码，这里只是把检查逻辑可视化。
 */
public class LockSpecChecker {

    /** 声明的区域锁：锁名 → 被保护的字段集合 */
    static final Map<String, Set<String>> REGION_LOCKS = Map.of(
        "FL", Set.of("filter")
    );

    /** 方法的规约：方法名 → 需要的锁 */
    static final Map<String, String> REQUIRES_LOCK = Map.of(
        "setFilter", "FL",
        "log",       "FL"
    );

    /** 模拟「这个方法的这个方法体是否持锁」 */
    static final Map<String, Boolean> HOLDS_LOCK = Map.of(
        "setFilter", false,     // ← 真实 bug：没加 synchronized
        "log",       true
    );

    public static void main(String[] args) {
        for (String method : REQUIRES_LOCK.keySet()) {
            String required = REQUIRES_LOCK.get(method);
            boolean holds = HOLDS_LOCK.getOrDefault(method, false);
            if (!holds) {
                System.out.println("Inconsistent: " + method
                    + "() 的规约要求持有 " + required
                    + "，但方法体未持锁 → 数据竞争");
            } else {
                System.out.println("Consistent:   " + method + "() 正确持有 " + required);
            }
        }
    }
}
```

输出：

```
Inconsistent: setFilter() 的规约要求持有 FL，但方法体未持锁 → 数据竞争
Consistent:   log() 正确持有 FL
```

**这个例子的要点**：检查逻辑本身只有三行——`规约要求什么` vs `代码实际做了什么`。真正的工具（JSure）复杂的地方在于**从字节码里推断「代码实际做了什么」**，而不是判断本身。

**示例 C：别名如何击穿锁的保护。**

```java
import java.util.*;

public class AliasingBreaksLock {
    static class Buffer {
        private final Object lock = new Object();
        private final int[] data = new int[10];
        private int size = 0;

        public void add(int x) {
            synchronized (lock) {          // 内部访问：正确加锁
                data[size++] = x;
            }
        }

        /** 危险：把内部数组泄漏出去 */
        public int[] leak() {
            return data;                   // 外部拿到别名后可以绕过 lock
        }
    }

    public static void main(String[] args) {
        Buffer b = new Buffer();
        int[] aliased = b.leak();          // 别名！

        Thread t1 = new Thread(() -> { for (int i = 0; i < 1000; i++) b.add(i); });
        Thread t2 = new Thread(() -> { for (int i = 0; i < 1000; i++) aliased[i % 10] = -1; });
        t1.start(); t2.start();
        // t2 完全绕过 lock，Buffer 的所有同步保证失效
    }
}
```

**`@NotAliased` 要禁止的正是 `leak()` 这样的方法**。如果分析器知道 `data` 没有别名，它就能确信「所有对 `data` 的访问都经过 `lock`」；一旦出现 `leak()`，这个保证就崩了。

**示例 D：切点（cut point）如何把两个操作变成一个原子操作。**

```java
public class CutPointDemo {
    private final Object lock = new Object();
    private int[] data = new int[10];
    private int size = 0;

    /** 整个方法是一个 cut point：外部永远看不到中间态 */
    public void add(int x) {
        synchronized (lock) {
            data[size] = x;     // 若在此处被打断，外部会看到 size 未更新
            size++;             // ← 但因为持锁，这个中间态不可见
        }
    }

    /** 反例：不加锁，中间态可见 → 典型的「先检查后动作」竞态 */
    public int unsafeRemove() {
        if (size == 0) return -1;      // 检查
        return data[--size];           // 动作（中间可能被别人改 size）
    }

    public static void main(String[] args) throws Exception {
        CutPointDemo d = new CutPointDemo();
        d.add(42);

        Thread a = new Thread(() -> { for (int i = 0; i < 1000; i++) d.add(i); });
        Thread b = new Thread(() -> { for (int i = 0; i < 1000; i++) d.unsafeRemove(); });
        a.start(); b.start(); a.join(); b.join();
        // unsafeRemove 可能返回 -1 之外的错误值，甚至抛 ArrayIndexOutOfBounds
        System.out.println("size = " + d.size);
    }
}
```

**「先检查后动作（check-then-act）」是最经典的竞态模式**：`if (size == 0)` 与 `data[--size]` 之间没有原子性保证。切点的价值在于它把「持锁的整段代码」标记为一个不可分割的单元，从而让这类问题**在规约层面就可表达**（`@RequiresLock`），而不是靠人肉判断哪几行该在一起。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| 竞态条件（race condition） | 数据竞争（data race） | 前者是语义概念（正确性依赖时序，可无数据竞争）；后者是底层现象（同变量、至少一写、无同步），可机械检测 |
| 有竞态 | 有 bug | 竞态只有在**违反不变式**时才是 bug；读写不可变数据不是竞态 |
| 粗粒度锁 | 细粒度锁 | 前者简单不易漏、并发度低；后者并发度高但易漏锁、易死锁、难分析 |
| 线程局部化 | 加锁 | 前者根本不让共享（无需同步开销）；后者让共享变安全（有开销、可能死锁） |
| `@RegionLock` | `@RequiresLock` | 前者**声明**「哪把锁保护哪些字段」；后者**要求**「调用此方法必须持锁」 |
| 别名（aliasing） | 唯一性（uniqueness） | 前者让「哪把锁管哪块数据」无法静态判定；后者保证只有一个引用，可安全转移所有权 |
| 切点（cut point） | 临界区（critical section） | 二者常重合，但切点是**分析用的抽象**（原子块边界），临界区是**代码结构**（持锁的代码段） |
| 分析器说「一致」 | 程序绝对没有 bug | 前者只表示「满足所声明的规约」；规约本身写错或缺失时，一致也可能有 bug |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-214/slides/25-analysis-concurrency.pdf`
- **总页数**：29 页
- **本节重点页码**：
  - 第 2–6 页：`java.util.logging.Logger` 的 `filter` 字段竞态与 `synchronized` 修复
  - 第 7 页：竞态与数据竞争的定义（引自 Savage et al., Eraser）
  - 第 8 页：竞态的三大难点（非局部、污染好代码、难测试）
  - 第 9 页：错误 = 不变式被违反（五个不变式例子）
  - 第 10 页：必须有设计意图才能判断竞态是不是 bug
  - 第 11 页：避免竞态的五种手段
  - 第 12 页：锁粒度
  - 第 13 页：JSure 工具
  - 第 15 页：Fluid 的 `@RegionLock` / `@requiresLock`
  - 第 16 页：`@aggregate … into Instance`、`@Unique`、`@Unique("return")`
  - 第 17 页：三类分析结果（一致 / 不一致 / 请求注解）
  - 第 19 页：增量保证
  - 第 21 页：别名问题与 Fugue 的 `@NotAliased`
  - 第 23 页：构造器与继承带来的问题
  - 第 25–27 页：cut points 与 `@RequiresLock(BufLock)`
  - 第 29 页：总结
- **原始链接**：https://www.cs.cmu.edu/~aldrich/214/slides/25-analysis-concurrency.pdf

## 9. 对应视频

未找到官方公开录像。

## 10. 本节复习

- 数据竞争 = 两线程 + 同一变量 + 至少一个写 + 无显式同步。
- 竞态三大难点：错误非局部、坏代码污染好代码（模块化推理失效）、测试几乎无效。
- 竞态本身不是 bug；**违反不变式**才是。判断不变式需要**设计意图**。
- 五种避免手段：线程局部化、加锁、禁用中断、分析所有交错、事务内存。
- 锁粒度是性能与可分析性的双重权衡：粗粒度好分析、细粒度高性能。
- Fluid 注解：`@RegionLock("名字 is 锁对象 protects 字段")` 声明区域；`@RequiresLock("名字")` 要求持锁；`@aggregate … into Instance` 聚合成类级锁；`@Unique` / `@Unique("return")` 表达唯一性。
- 分析结果三态：一致 / 不一致 / **请求注解**（合法状态，不是失败）。
- 别名是模块化推理的最大障碍；`@NotAliased` / `@Unique` 是解法，且唯一性让「所有权转移」无需同步。
- 构造器与继承是两大边缘陷阱：`this` 逃逸、子类破坏父类锁规约。优先组合、优先 `final`。
- 切点 = 可原子执行的代码区域；它让交错数可控，也让「原子性」成为可写的规约。

## 11. 自我检查

**Q1.** 下面这段代码有数据竞争吗？它有没有可能是「正确的」？请分别从「技术定义」和「工程判断」两个角度回答。

```java
class Config {
    static volatile int timeout = 30;      // 由管理线程周期性写入
    static int readTimeout() { return timeout; }
}
```

**Q2.** 请解释为什么「给读的一方加锁、写的一方不加锁」等于完全没加锁。用 `Logger` 的例子说明。

**Q3.** 某团队用一把大锁保护所有共享状态。他们的程序没有竞态，但性能很差。请给出两条改进路径，并说明每条路径会带来什么**分析上的**新困难。

**Q4.** 请说明 `@RegionLock("FL is this protects filter")` 与 `@RequiresLock("FL")` 在分析中分别被用来检查什么。如果只写前者不写后者，会发生什么？

**Q5.** 什么是 cut point？为什么它对「穷举所有交错」这件事是必需的？

<details>
<summary>参考答案</summary>

**A1.**
- **技术定义**：严格说，`volatile` 是一种**显式同步机制**（它保证可见性与禁止重排序），所以按 Eraser 的三条件定义，这里**不构成数据竞争**——第 3 条「没有显式机制」不成立。
- **工程判断**：即便如此，`readTimeout()` 的语义仍可能是错的。如果 `timeout` 与另一个字段（如 `maxRetries`）构成不变式（「超时时间与重试次数必须匹配」），那么管理线程更新两者时，读线程可能看到「新的 timeout + 旧的 maxRetries」——这是一个**竞态条件**（语义层面），但不是数据竞争（底层层面）。修法是：要么把两个字段打包成一个不可变对象、用一次 `volatile` 引用写入（保证原子发布），要么用一个不可变快照加锁替换。
- **这个例子正好说明本讲的核心区分**：数据竞争可以机械检测，竞态条件需要知道不变式。

**A2.** 锁的作用是**互斥**——它保证「持同一把锁的两个线程不会同时执行」。如果写的一方不持锁，那么它可以在读的一方持锁期间任意时刻写入，**互斥根本不成立**。`Logger` 的例子：`log()` 里 `synchronized (this)` 保护了 `filter` 的读取，但 `setFilter()` 直接 `filter = newFilter;`——此时读线程可以持锁，写线程无锁并发写入，「保护」形同虚设。更准确的说法是：**锁只对「所有访问者都遵守」的协议有效**。这把锁的协议被 `setFilter()` 单方面破坏了，所以 `log()` 的加锁代码虽然是「好代码」，却因为「坏代码」而失效——这正是课件第 8 页「bad code spoils good code」的含义。

**A3.** 两条路径：
1. **拆分数据、每份一把锁（细粒度）**。新困难：分析器必须知道「哪个字段归哪把锁管」——需要 `@RegionLock` 这样的显式声明；而且多把锁引入**死锁**风险（需要全局锁序），静态分析要做锁序检查（这比单锁检查难得多，需要全局的锁获取图）。
2. **改用不可变数据 + 原子替换引用（copy-on-write）**。新困难：分析器要证明「被替换的对象真的是不可变的」——这需要检查所有字段是否 `final`、所有引用的对象是否也深不可变（递归不变性），而且对「读-改-写」模式（如 `counter++`）无能为力，必须改用 `AtomicInteger` 之类的原子类，分析器又得为每个原子类建模其语义。

**A4.**
- **`@RegionLock("FL is this protects filter")`** 用来检查**方法体内部**：每一个对 `filter` 的访问（读或写）是否发生在持有 `FL`（即 `this`）的区域内。如果没有持锁就访问，报 **Inconsistent**。
- **`@RequiresLock("FL")`** 用来检查**调用点**：每一个调用该方法的地方是否持有 `FL`。这保证了「方法体内部的原子性假设」在调用者那里也成立。
- **只写前者不写后者**：分析器会认为 `setFilter()` 可以在任意上下文被调用，那么它在方法体内「持锁访问 `filter`」的检查就无法通过（因为进入方法时并不保证持锁）——结果是工具报 **Inconsistent** 或者报 **Requested annotations**（要求你补 `@RequiresLock`）。更本质地说，`@RequiresLock` 是**把义务向上传递**的机制，没有它，模块化推理就断了：你无法在不知道调用者状态的情况下判断方法本身是否正确。

**A5.** **Cut point** 是一段可以**原子执行**的代码区域（通常因为持有某把锁），其内部的中间状态对其他线程不可见。它是必需的，因为：模型检验要穷举所有线程的**所有交错**，如果按「每条字节码」为单位计算交错，交错数是线程数 × 指令数的组合爆炸（两个线程各 10 条指令就有 C(20,10) ≈ 18 万种交错，再加上循环就无穷）。切点把若干条指令合并成一个不可分割的单元，交错只在切点边界发生——这把状态空间从「指令级」降到「事务级」，通常能缩小几个数量级。同时，切点还为**规约**提供了表达单位：「这个方法原子地完成 X」是可以写下来并检查的，而「这 37 条字节码原子地完成 X」既写不下来也无法验证。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-23-Static-Analysis]]——抽象解释、可靠性与完备性、模型检验的一般框架。
- 下一讲：[[15-214-25-Data-Consistency]]——从单机的锁走向分布式的事务与一致性。
- 相关讲次：[[15-214-17-Concurrency-Part1]]（竞态直观例子）、[[15-214-18-Concurrency-Part2]]（`synchronized` 与死锁）、[[15-214-19-Concurrency-Part3]]（不可变性与线程封闭）、[[15-214-27-Why-Objects-Typestate-DSLs]]（类型状态与权限——`@Unique` 的完整理论）。
- 课程导航：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]、[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]。
- 术语条目：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Race Condition 竞态条件、Data Race 数据竞争、Mutual Exclusion 互斥、Lock 锁、Monitor 监视器）。
- 延伸阅读：Savage et al. "Eraser: A Dynamic Data Race Detector for Multithreaded Programs"（TOCS 1997）、Flanagan & Freund "Type-based race detection for Java"（PLDI 2000）、Bierhoff & Aldrich "Modular Typestate Checking of Aliased Objects"（OOPSLA 2007）、Beckman et al. "Verifying Correct Usage of Atomic Blocks and Typestate"（OOPSLA 2008）。
