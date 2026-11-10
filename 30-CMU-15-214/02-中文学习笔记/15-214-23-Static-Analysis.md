---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L23
topic: Static Analysis - Abstract Interpretation, Soundness, and Data-Flow Analysis
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 静态分析
  - 抽象解释
  - 数据流分析
  - 可靠性
  - 完备性
---

# 第 23 讲 静态分析（Static Analysis）

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。

## 1. 本节学习目标

- 能用「抽象（abstraction）+ 系统化（systematic）」两个词定义静态分析，并解释它与「执行程序」的根本区别。
- 能列举静态分析擅长的七类「机械性错误」，并说明为什么人做这些检查不划算。
- 能画出一棵抽象语法树（AST），并说明 AST 分析「忽略」了哪些信息。
- 能画出控制流图（CFG），并手工跑一遍「中断未恢复」检查。
- 能手工跑一遍数据流分析（空指针检查、资源泄漏检查），并说明 join（合并）为什么必要。
- 能画出可靠性/完备性的 2×2 混淆矩阵，并解释假阳性与假阴性。
- 能陈述 Rice 定理，并说明它为什么导致「五条好处不可兼得」。
- 能说明注解（SAL / JSR-305）如何同时提升精度与可扩展性。

## 2. 前置知识

- [[15-214-17-Concurrency-Part1]] 与 [[15-214-18-Concurrency-Part2]]：线程与竞态——静态分析的一个重点目标。
- [[15-214-05-Object-Contracts-and-Exceptions]]：前置条件/后置条件、类不变式——模块化分析依赖它们。
- [[15-214-06-Mutability-and-Java-Potpourri]]：`final` 字段与不可变性——静态分析常检查的规则之一。
- 外部概念：抽象语法树、控制流图、格（lattice）与不动点、图灵机与可判定性。

## 3. 核心概念

- **Static Analysis（静态分析）**：**不执行程序**而分析代码，用于发现缺陷或证明正确性。
- **Abstract Interpretation（抽象解释）**：对程序状态空间的一个**抽象**做**系统化**检查——不追踪一切，只追踪关键信息。
- **AST Walker（抽象语法树遍历器）**：把代码当作结构化树来检查，忽略控制流、变量值与堆。
- **Control-Flow Analysis（控制流分析）**：沿程序的所有路径追踪「程序计数器」与少量状态（如中断开关）。
- **Data-Flow Analysis（数据流分析）**：追踪数据在程序中如何流动，为每个变量维护一个抽象状态（如 null / not-null / maybe-null）。
- **State Explosion（状态爆炸）**：分路径精确追踪会导致路径数指数增长。
- **Join（合并）**：在分支汇合处把多条路径的抽象状态合并成一个（更不精确但状态数不增长）。
- **Soundness（可靠性）**：报告了**所有**缺陷——**没有假阴性**；通常靠**过近似（overapproximation）**实现。
- **Completeness（完备性）**：报告的每一个都是真缺陷——**没有假阳性**；通常靠**欠近似（underapproximation）**实现。
- **False Positive（假阳性/误报）**：报了错，但代码其实没问题。
- **False Negative（假阴性/漏报）**：有问题，但没报出来。
- **Rice's Theorem（赖斯定理）**：图灵机所识别语言的任何**非平凡性质**都是不可判定的。
- **Model Checking（模型检验）**：穷举抽象状态的所有可能交错（interleaving），用于竞态检测。
- **Annotation / Specification（注解/规约）**：写在代码里的前置/后置条件、不变式，用来告诉分析器「设计意图」。

## 4. 通俗理解

**静态分析是什么？** 想象你是代码审查员，但你不运行程序，只是盯着代码看。人做这件事很贵、会犯错、看多了会忘（课件第 5 页的原话：people "are very high cost", "make mistakes", "have a memory limit"）。所以——**把审查自动化**。

**「抽象」是什么意思？** 你检查「文件有没有关」时，不需要知道文件里是什么内容、变量叫 `reader` 还是 `r`、堆上有多少对象。你只需要知道两件事：**当前在第几行**（程序计数器）和**文件是开着还是关着**。把所有其他信息扔掉，只留这两样——这就是抽象。扔掉的信息越多，分析越快，但能发现的错误越少。

**「系统化」是什么意思？** 人审查代码会走神：这段看仔细了，那段扫一眼。机器不会——它对每一行都用同一套规则检查。这就是「系统化」，也是它能给出**保证**的原因。

**可靠性 vs 完备性，用门禁打比方。** 机场安检有两种失败方式：
- **漏放**（假阴性）：危险品被带进去了。**可靠性（sound）**要求「一个都不漏」——代价是把所有人的包都翻一遍，误报很多。
- **误拦**（假阳性）：老太太的矿泉水被拦下。**完备性（complete）**要求「拦下的都是真危险品」——代价是可能漏掉一些。

**两者都做到？** Rice 定理说：不可能。所以现实中的工具必须选边站。

## 5. 原理与推导

### 5.1 为什么需要静态分析：一个真实 bug

课件第 4 页给出一个 Java 方法，让读者找 bug：

```java
public void loadFile(String filename) throws IOException {
    BufferedReader reader =
        new BufferedReader(
            new FileReader(filename));
    if (reader.readLine().equals("version 1.0"))
        return;                       // invalid version
    String c;
    while ((c = reader.readLine()) != null) {
        processData(c)
    }
    reader.close();
}
```

**Bug**：版本号是 "version 1.0" 时，方法直接 `return`，**没有关闭 `reader`**——文件句柄泄漏。在长时间运行的服务里，泄漏几千个句柄后，进程会因 `Too many open files` 而崩溃。

人的审查为什么可能漏掉？因为 `return` 出现在方法开头，与 `close()` 隔了 10 行，中间还夹着一个循环。人的工作记忆装不下整条路径。

**机器怎么做？** 课件第 6 页给出一个「心智模型」——一个两状态自动机：

```
         allocate              close
  free ──────────→ allocated ──────────→ free
                      │
                      │ close（重复关闭）
                      ↓
                    err(double close)

  路径结束仍在 allocated
        ↓
  err(end path without close)
```

只要把方法里每条路径都跑一遍这个自动机，就能发现「某条路径结束时仍处于 allocated」——这正是第 7 页标注的：

```
initial state free
transition to allocated
final state allocated: ERROR!        ← 版本 1.0 的 return 路径
transition to free
final state free is OK               ← 正常路径
```

这个「状态机 + 走遍所有路径」的框架，就是本讲所有技术的共同骨架。

### 5.2 静态分析擅长什么：机械性错误

课件第 8 页的清单——注意标题用词是 **"mechanical" errors**（机械性错误）：

> Defects that result from inconsistently following simple, mechanical design rules.

| 类别 | 例子 |
|---|---|
| **安全漏洞（security vulnerabilities）** | 缓冲区溢出、未校验的输入 |
| **内存错误（memory errors）** | 空指针解引用、未初始化数据 |
| **资源泄漏（resource leaks）** | 内存、操作系统资源（文件句柄、套接字） |
| **API/框架规则违反** | Windows 设备驱动、实时库、GUI 框架的调用约束 |
| **异常（exceptions）** | 算术异常、库异常、用户自定义异常 |
| **封装破坏（encapsulation violations）** | 访问内部数据、调用私有函数 |
| **竞态条件（race conditions）** | 两线程访问同一数据且无同步 |

**为什么叫「机械性」？** 因为这些规则**简单且明确**：`close()` 必须被调用；`synchronized` 必须覆盖所有共享访问；`equals` 必须与 `hashCode` 一致。规则越机械，越适合机器检查；规则越需要「理解意图」，越适合人。静态分析不该试图取代人的判断，而该接管那些「人做会烦、会忘、会错」的部分。

### 5.3 工具实例：FindBugs

课件第 10 页：

- 起源于马里兰大学的研究项目，现为开源；
- 独立工具，也有 Eclipse 插件；
- 检查 **250+ 种 bug 模式**，其中 **100+ 是正确性 bug**，还包括许多风格问题；
- 上面两个例子（未关闭流、错误的 `equals`）都在其中；
- **专注简单、局部的检查**；
- 检查的是 **bytecode，不是 AST**——「更难写，但更高效，且不需要源码」。

第 11 页列出的一些模式：

```
Correct equals()
Use of ==
Closing streams
Illegal casts
Null pointer dereference
Infinite loops
Encapsulation problems
Inconsistent synchronization
Inefficient String use
Dead store to variable
```

**「检查 bytecode 而不是 AST」这个选择值得玩味**：bytecode 里泛型已被擦除、局部变量名已丢失，所以某些检查（如「变量名不符合规范」）做不了；但 bytecode 是**所有 JVM 语言的共同目标**，所以 FindBugs 也能分析 Scala、Kotlin 编译出的类。这是「在哪个抽象层做分析」的典型取舍。

**实证效果**（第 13 页，引自 Chaturvedi 2005 的 InfoSys 研究）：5 个项目、平均每个 700 个功能点，对比「有静态分析」与「无静态分析」的代码审查——结论是**缺陷更少、生产率更高**。

### 5.4 抽象解释的两个关键词

课件第 16 页给出本讲最核心的定义：

> **Static program analysis is the systematic examination of an abstraction of a program's state space.**
> （静态程序分析是对程序状态空间的一个抽象所进行的系统化检查。）

拆开看：

- **Abstraction（抽象）**：不要追踪一切（那是「正常解释/执行」）；只追踪一个重要的抽象。
- **Systematic（系统化）**：确保每一处都用同一种方式被检查。

这个定义的精妙之处在于：它把「静态分析」与「测试」区分开了。测试是**具体执行**若干条路径；静态分析是**抽象地覆盖**所有路径。前者精确但只能覆盖极少部分，后者粗糙但覆盖全部。

课件接着说「Let's start small…」，然后按**抽象程度递增**的顺序介绍四种技术：

1. AST 分析（几乎不抽象，只看语法结构）
2. 类型检查（抽象掉值，只看类型）
3. 控制流分析（抽象掉数据，只看程序计数器 + 少量状态）
4. 数据流分析（抽象掉具体值，看每个变量的抽象状态）
5. 模型检验（抽象掉堆与变量，穷举线程交错）

### 5.5 AST 分析：最弱但最便宜

**例子：性能 bug**（第 18 页）

```java
public foo() {
    …
    logger.debug("We have " + conn + "connections.");
}
```

看起来无害，但**字符串拼接在 `debug()` 被调用之前就发生了**——即使日志级别是 INFO，程序也会先构造这个字符串、再发现不该输出。课件算了一笔账：

> 如果这个性能提升在 1000 台服务器上意味着少买一台机器，那就能省很多钱。

修复：

```java
public foo() {
    …
    if (logger.inDebug()) {
        logger.debug("We have " + conn + "connections.");
    }
}
```

**如何自动检查？**（第 19 页）

- **抽象**：找 `Logger.debug()` 的调用，确认它被 `if (Logger.inDebug())` 包住；
- **系统化**：检查所有代码；
- 这叫做 **AST walker**：把代码当作结构化树，**忽略控制流、变量值与堆**。

第 20 页给出一棵 AST 的示意（以 `if (logger.inDebug()) { logger.debug(...) }` 为例）：

```
class X
├── field logger
└── method foo
    └── if stmt
        ├── method invoc. logger.inDebug
        └── block
            └── method invoc. logger.debug
                └── parameter …
```

**AST 分析的局限**：它只看「长什么样」，不看「会发生什么」。如果 `debug` 调用被包在一个 `if (false)` 里，或者 `inDebug` 检查在 10 行之前、中间有 `return`，AST walker 都看不出来。它也无法判断 `logger` 是否为 null。

课件的评语很到位：**"Simplest static analysis: grep"**——最简的静态分析就是 `grep`。代码风格检查器本质上都是 AST walker，所以课件强调：**「你永远不该手工检查代码风格」**。

### 5.6 类型检查：把值抽象成类型

课件第 24 页：

> - Classifying values into types
> - Checking whether operations are allowed on those types
> - Detects a class of problems at compile time, e.g.
>   - Method not found
>   - Cannot compare int and boolean

第 25 页在 AST 上叠加了类型标注：

```
if stmt  ...  logger.inDebug  →  boolean   (expects boolean ✓)
              logger.debug    →  String -> void   (参数 String ✓)
```

类型检查的**抽象**是：**忘掉具体的值，只记住类型**。`int x = 5` 和 `int x = 999999` 在类型检查器眼里完全一样。这个抽象极其粗糙（丢失了所有数值信息），但换来两个巨大好处：**极快**（线性时间）与**模块化**（可以单独检查每个文件）。

第 26 页对比了不同语言的类型检查策略：

| 语言 | 类型检查方式 | 特点 |
|---|---|---|
| **Perl** | 完全没有类型检查 | 灵活但错误留到运行时 |
| **ML** | 不需要写类型标注，全局类型推断 | 强大，但错误信息难懂，编译慢 |
| **Java** | 需要写类型标注，**模块化**检查 | 类型本身就是一种规约（specification） |
| **C# / Scala** | 局部变量不写类型，参数与返回值必须写 | 「两全其美」 |

**「Types are a specification!」** 这句话很重要：`void debug(String msg)` 这个签名就是一个契约——「你给我一个 String，我不返回任何东西」。类型检查器在编译期验证所有调用者都遵守这个契约。这与 [[15-214-05-Object-Contracts-and-Exceptions]] 里的契约思想完全一致，只是契约的**表达力**被限制在「类型」这个维度上。

### 5.7 可靠性与完备性：2×2 混淆矩阵

课件第 29 页给出本讲最重要的一张表：

|  | 确实有错误 | 确实无错误 |
|---|---|---|
| **报告了错误** | **True positive**（真阳性，正确结果） | **False positive**（假阳性，误报） |
| **没有报告** | **False negative**（假阴性，漏报） | **True negative**（真阴性，正确结果） |

两个定义（课件原文）：

- **Sound Analysis（可靠分析）**：报告**所有**缺陷 → **没有假阴性**；通常是**过近似（overapproximated）**的。
- **Complete Analysis（完备分析）**：报告的每一个都是真缺陷 → **没有假阳性**；通常是**欠近似（underapproximated）**的。

第 30 页的集合图更直观：把所有缺陷画成一个大圆，「可靠分析」覆盖整个圆（可能溢出圆外），「完备分析」完全落在圆内（可能没盖满），「既不可靠也不完备」则两头都不满足。

课件还留了一个思考题：**「How does testing relate? And formal verification?」**

- **测试**：只覆盖实际执行到的路径。它能发现错误（所以不是完全没用），但**既不可靠也不完备**——没测到的路径全漏（假阴性），而且测出来的都是真错误（在确定性程序里没有假阳性）。所以测试是**欠近似**的。
- **形式验证（formal verification）**：目标是**可靠且完备**——证明「程序满足规约」或「存在违反」。在有限状态系统上可以做到两者兼顾（模型检验）；在无限状态（图灵完备）系统上，Rice 定理说不存在通用算法。

### 5.8 Rice 定理：坏消息

课件第 31 页：

> **The Bad News: Rice's Theorem**
> Every static analysis is necessarily incomplete or unsound or undecidable (or multiple of these).
>
> "Any nontrivial property about the language recognized by a Turing machine is undecidable."
> — Henry Gordon Rice, 1953

**什么是「非平凡性质（nontrivial property）」？** 不是「所有程序都有」也不是「所有程序都没有」的性质。例如「这个程序会终止吗」「这个程序会访问空指针吗」「这个程序会关闭所有文件吗」——都是非平凡的，因此都不可判定。

**推论**：不存在一个分析器能同时做到「报出所有真缺陷」和「不报任何假缺陷」并且「总是停机」。三者必舍其一（通常还要加上性能要求）。

### 5.9 控制流分析：中断检查

课件第 33 页给出定义与例子：

> - **抽象**：2 个状态（enabled / disabled）+ 程序计数器
> - **系统化**：检查函数内的所有路径
> - **错误条件**：到达函数末尾时中断仍是 disabled
> - 这叫做**控制流分析**——比把代码当纯文本读更强大，因为它考虑程序状态与路径。

第 34 页的完整例子（Linux 内核风格的代码）：

```c
1.  int foo() {
2.      unsigned long flags;
3.      int rv;
4.      save_flags(flags);
5.      cli();                       // 关中断
6.      rv = dont_interrupt();
7.      if (rv > 0) {
8.          do_stuff();
9.          restore_flags();         // 开中断
10.     } else {
11.         handle_error_case();
12.     }
13.     return rv;
14. }
```

课件给出的状态标注：

```
行 2-4:  enabled
行 5:    unknown → disabled
行 6-7:  disabled
行 8-9:  disabled → enabled
行 11:   disabled            ← else 分支没有 restore_flags
行 13:   enabled / disabled ← 两条路径汇合，一个是 enabled 一个是 disabled
end:     错误：某条路径未重新开启中断
```

**结论**：`else` 分支走完 `handle_error_case()` 后直接 `return rv`，中断仍是 disabled。若此时返回上层，系统会在关中断状态下继续运行——可能导致整个系统挂起。这是一个**只在错误路径上出现**的 bug，人工审查和测试都极易漏掉。

### 5.10 状态爆炸与 Join

课件第 35 页提出关键问题：

> When we get to a branch, what should we do?

**方案 1：分别探索每条路径。**
- 每条路径的信息最精确；
- 但路径数可能有多少？**指数级状态爆炸（exponential state explosion）**。
- 一个函数里有 10 个 `if` 就有 2¹⁰ = 1024 条路径；20 个就是一百万条。加上循环（可能执行任意次）与异常，实际路径数无界。

**方案 2：把路径合并回来（join）。**
- 精度降低；
- 但没有状态爆炸。

**join 怎么做？** 在汇合点，对每个变量的抽象状态取「并集」：一条路径说 `enabled`、另一条说 `disabled`，合并结果就是「可能是 enabled，也可能是 disabled」——即 `unknown`。上面的例子里，第 13 行的状态正是这样得到的。

课件提醒：**「Not just conditionals!」**——循环、`switch`、异常都会产生分支，都需要 join。循环尤其麻烦：循环体可能执行 0 次、1 次或多次，join 之后必须迭代到**不动点（fixed point）**才能保证结果稳定。

**这就是静态分析的核心权衡**：精度（precision）vs 可扩展性（scalability）。join 越多，精度越低，但分析越快、越能处理大程序。

### 5.11 数据流分析：空指针检查

课件第 37 页：

> - **抽象**：程序计数器 + 每个变量的 3 个状态（null / not-null / maybe-null）
> - **系统化**：沿方法或程序的所有路径探索所有变量的所有数据值
> - **这叫做数据流分析**——追踪数据如何在程序中移动
> - 非常强大，很多分析都这么做（编译器优化是最早的应用）；**代价高昂**

第 38 页的例子：

```java
1.  int foo() {
2.      Integer x = new Integer(6);
3.      Integer y = bar();
4.      int z;
5.      if (y != null)
6.          z = x.intValue() + y.intValue();
7.      else {
8.          z = x.intValue();
9.          y = x;
10.         x = null;
11.     }
12.     return z + x.intValue();     // ← 错误：x 可能是 null
13. }
```

课件给出的逐点状态（注意 join 的效果）：

```
行 2:    x → not-null
行 3:    x → not-null, y → maybe-null
行 4-5:  x → not-null, y → maybe-null
行 6:    x → not-null, y → not-null        （then 分支：y != null 成立）
行 8-10: x → null,      y → not-null       （else 分支：x 被置 null，y 得到 x 的旧值）
行 12:   x → maybe-null, y → not-null      ← join！两条路径合并
```

**第 12 行的 `x` 状态是 `maybe-null`**：then 分支结束时 `x` 是 not-null，else 分支结束时 `x` 是 null，join 得到 maybe-null。而第 12 行调用了 `x.intValue()`——在 maybe-null 上解引用，报错。

**这个例子展示了 join 的威力**：如果不 join、分别走两条路径，then 分支通过、else 分支报错——结论一样，但路径数会随分支增长。join 用「精度」换「规模」。

### 5.12 方法调用：全局分析 vs 模块化分析

课件第 39 页提出新问题——分析遇到方法调用怎么办？

```java
1.  int foo() {
2.      Integer x = bar();
3.      Integer y = baz();
4.      Integer z = noNullsAllowed(x, y);
5.      return z.intValue();
6.  }
7.
8.  Integer noNullsAllowed(Integer x, Integer y) {
9.      int z;
10.     z = x.intValue() + y.intValue();
11.     return new Integer(z);
12. }
```

**方案 1：全局分析（global analysis）**（第 40 页）
- 深入每一个方法调用（像内联一样展开）；
- 与分支一样，不做 join 就会指数爆炸；
- 即使做了 join，复杂度通常是**程序规模的立方甚至更高**；
- 还有一个哲学问题：**「谁该检查 null？调用者还是被调用者？」**——需要开发者自己判断「哪个方法有错」。

**方案 2：带规约的模块化分析（modular analysis with specifications）**（第 41 页）
- 每个模块单独分析；
- 用**规约**把它们拼起来：前置条件与后置条件；
- 分析一个方法时：**假设前置条件成立**，**检查它是否产生后置条件**；
- 分析遇到方法调用时：**检查前置条件是否被满足**，**假设调用会产生后置条件**；
- 参见形式验证与 Dafny。

这是 [[15-214-05-Object-Contracts-and-Exceptions]] 里契约思想在静态分析中的直接应用。**契约把「全局推理」分解成「局部推理 + 接口假设」**——和 [[15-214-07-Design-Patterns]] 的信息隐藏是同一个道理。

第 42 页给出加了注解的版本：

```java
1.  int foo() {
2.      Integer x = bar();
3.      Integer y = baz();
4.      Integer z = noNullsAllowed(x, y);   // ← 这里报错：baz() 可能返回 null
5.      return z.intValue();
6.  }
7.
8.  @Nonnull Integer noNullsAllowed(
9.      @Nonnull Integer x,
10.     @Nonnull Integer y) {
11.     int z;
12.     z = x.intValue() + y.intValue();
13.     return new Integer(z);
14. }
15. @Nonnull Integer bar();
16. @Nullable Integer baz();
```

有了注解，分析变得极其简单：`noNullsAllowed` 要求两个 `@Nonnull` 参数，而 `baz()` 声明返回 `@Nullable`，所以第 4 行**确定**有错——不需要深入方法体，不需要枚举路径，**零假阳性**。这就是注解的威力。

### 5.13 其他规约类型

课件第 44–45 页列出规约的种类，并把静态分析与前面讲过的契约概念连起来：

**类不变式（class invariants）**——复习：

```java
public class Buffer {
    boolean isOpen;
    int available;
    /*@ invariant isOpen <==> available > 0  @*/
    public void open() {
        isOpen = true;
        //invariant is broken         ← 中间状态可以暂时破坏
        available = loadBuffer();
    }
}
```

> 不变式在类的方法**之外**永远为真；方法**内部**可以暂时破坏，但必须重新拼好。

课件特别指出：**ESC/Java、Dafny 就是这类静态分析工具**。

**其他规约**：

| 规约类型 | 回答的问题 |
|---|---|
| 类不变式（class invariants） | 进入/离开一个类时，什么永远为真？ |
| 循环不变式（loop invariants） | 循环内部什么永远为真？ |
| 锁不变式（lock invariants） | 使用这个对象必须持有什么锁？ |
| 协议（protocols） | 方法必须以什么顺序调用？ |

**协议的例子**（课件原文）：

- Good: `Open, Write, Read, Close`
- Bad: `Open, Write, Close, Read`

这正是 [[15-214-24-Static-Analysis-for-Concurrency]] 与 [[15-214-27-Why-Objects-Typestate-DSLs]] 中「类型状态（typestate）」的雏形。

### 5.14 模型检验：竞态检测

课件第 47 页：

> - **竞态条件的定义**（引自 Savage et al., Eraser）：
>   - 两个线程访问同一个变量
>   - 至少一个是写
>   - 没有显式机制阻止这两个访问同时发生
> - **抽象**：每个线程的程序计数器 + 每把锁的状态；**抽象掉堆与程序变量**
> - **系统化**：检查所有线程的所有可能交错（interleaving）
> - **若两个访问之间没有同步则报错**
> - 探索是**穷举的**，因为抽象状态抽象了所有具体程序状态
> - 这叫做**模型检验（model checking）**

第 48–51 页用四张图展示了「同一个程序、四种交错、两种结果」：

```java
thread1() { read x; }
thread2() { lock(); write x; unlock(); }
```

| 交错 | 顺序 | 结果 |
|---|---|---|
| 1 | T1.read → T2.lock → T2.write → T2.unlock | **OK** |
| 2 | T2.lock → T2.write → T2.unlock → T1.read | **OK** |
| 3 | T2.lock → T1.read → T2.write → T2.unlock | **竞态**（read 发生在 lock 与 write 之间，无保护） |
| 4 | T2.lock → T2.write → T1.read → T2.unlock | **竞态**（read 在临界区内但 T1 未持锁） |

**关键洞察**：`thread1` 的 `read x` **完全没有加锁**，而 `thread2` 的 `write x` 加了锁。锁只在双方都遵守时才有意义——单方面加锁等于没加。这个 bug 在 4 种交错中只有 2 种会暴露，**测试时可能跑一万次都是对的**（这正是 [[15-214-17-Concurrency-Part1]] 里「并发 bug 难以复现」的静态版本）。

### 5.15 五个好处不可兼得

课件第 53 页给出本讲最精彩的总结：

> **Tradeoffs — You can't have it all:**
> 1. No false positives
> 2. No false negatives
> 3. Perform well
> 4. No specifications
> 5. Modular
>
> **You can't even get 4 of the 5.**
> - 停机问题意味着前三条互不相容（Rice 定理）
> - 模块化分析需要规约

**推导**：

- 要 1+2（既无假阳性又无假阴性）= 完全正确 = 完备且可靠 → 由 Rice 定理，这不可判定 → 必然违反 3（无法保证在有限时间内给出答案）。
- 要 5（模块化）→ 必须知道「被调用方法的契约」→ 必须有规约 → 违反 4。
- 所以最多只能拿 3 条。每个工具都在这个五维空间里选一个点。

第 55 页进一步说明不同工具的选择：

- **类型检查**：能抓住特定一类问题，但找不到所有问题（完备性好，可靠性差）；
- **编译器优化的数据流分析**：必须**偏向安全侧**——只在确定正确时才做优化（可靠，宁可少优化）；
- **很多实用的 bug 查找工具**：**既不可靠也不完备**——抓住典型问题，可能对正确代码报警，也可能漏掉问题。
- **大量假阴性会让分析变得无用**（报了 3 个 bug 但漏了 300 个，用户就不信了）；
- **不是所有「bug」都需要修**。

### 5.16 「假」阳性到底假不假？

课件第 56–57 页用两个例子挑战「假阳性」这个概念。

**例子 1**：

```java
1.  int foo(Person person) {
2.      if (person != null) {
3.          person.foo();
4.      }
5.      return person.bar();
6.  }
```

工具报：**第 5 行，与 null 的冗余比较（redundant comparison to null）**。

课件追问：
- 这是假阳性吗？
- 如果那个分支在实践中从未被执行呢？
- 你会修吗？怎么修？

**分析**：从技术定义看，第 2 行已经检查了 `person != null`，第 5 行再解引用确实「不冗余」——因为 `person` 可能为 null（第 2 行的 `if` 不成立时）。所以工具报的其实是「你可能忘了在这里也检查 null」，措辞却是「冗余比较」，容易误导。而如果调用者永远传非 null，这就是**实践中的假阳性**。修法有两种：加 `@Nonnull` 注解（表达意图），或者真的加一个 null 检查（防御式编程）。

**例子 2**：

```java
1.  public class Constants {
2.      static int myConstant = 100;
3.  }
```

工具报：**第 3 行，字段不是 final 但应该是**。

课件追问：
- 这是假阳性吗？
- 如果它来自你引入的开源库呢？
- 如果有 1000 个这样的警告呢？

**分析**：技术上这是真问题（常量应该 `final`）。但如果它在一个第三方库里，你**不能改**；如果有一千个，你会被淹没。于是「技术上的真阳性」在工程上变成了「噪声」。

### 5.17 真阳性：技术定义 vs 工程定义

课件第 59 页给出一个非常实用的区分：

> **True Positives**
> - 技术定义：可能引发运行时错误的问题
> - 我们关心的真阳性：
>   1. 开发者**打算修**的任何问题
>   2. （更微妙）开发者**想看到**的任何问题，无论是否修
> - 因项目与人而异
>
> 可靠性与完备性是**技术定义**的——但有时并不完全匹配人们真正想要的。

这段话点出了静态分析落地的核心矛盾：**工具的「正确性」与用户的「有用性」不是一回事**。一个技术上 100% 可靠的工具，如果报出的 10000 条警告没人看，价值为零。

### 5.18 工程落地：eBay 与 Microsoft

**eBay 案例**（第 60–64 页）：

- eBay 想用静态分析，需要**开箱即用**的工具，聚焦**安全与性能**；
- **过去的坏经验**：假阳性太多；工具在流程中引入得太晚；
- 任务：帮他们选工具并接入流程。

**如何判断一个问题重不重要？**（第 61 页）

```java
// 这个重要吗？
void foo(int x, int y) {
    int z;
    z = x + y;        // 死存储（dead store）：算了但没用
}

// 那这个呢？
void foo(int x, int y) {
    List dataValues;
    dataValues = getDataFromDatabase(x, y);   // 死存储，但代价巨大！
}
```

两者都是「死存储」，但第二个从数据库拉了一大堆数据却扔掉——**显著的开销，而且没有别的方法能发现它**。所以同一个检测器报出的问题，重要性可以差几个数量级。

**工具定制流程**（第 62 页）：

1. 打开所有检测器；
2. 在**单个团队**的代码上运行；
3. 按检测器分类结果；
4. 给每个检测器分配优先级；
5. **重复直到达成共识（跑 3 个团队）**。

**优先级 = 执行力**（第 63 页）：

> 优先级必须有意义（否则就全是「高优先级」）。

| 优先级 | 包含什么 |
|---|---|
| **High** | 高严重度的功能问题；中等严重度但容易修的 |
| **Medium** | 中等严重度的功能问题；重构信号；性能问题 |
| **Low** | 只有某些领域团队关心的；风格问题 |
| **Toss（丢弃）** | 不划算且噪声大 |

**成本/收益分析**（第 64 页）：

- **成本**：工具许可、内部支持工程师、缺陷报告的同行评审；
- **收益**：能发现多少缺陷？什么优先级？
- **对比 QA 工程师测试的等效成本**（eBay 的主要质量保证机制）；
- 粗略估算：**FindBugs 发现的缺陷显著更多（数量级差异），但优先级没那么高**。

这个结论很务实：静态分析不是「更好的测试」，而是「**测试覆盖不到的角落的补充**」。

**Microsoft 案例**（第 65–73 页）：

质量保证机制的演进史：

1. **最初：人工代码审查**——系统与团队小的时候有效，系统变大后路径太多，看不过来；
2. **1990 年代初：大规模系统测试与单元测试**——测试要跑几周；平台与配置多样；测试量巨大；对**常见模式与安全漏洞**的检测效率低；对**非局部、间歇性、罕见路径**的 bug 无能为力；「在 Windows Vista 开发中已经是在踩水（treading water）」；
3. **2000 年代初：引入静态分析**。

**PREFast**（第 66 页）：关注**内存使用**——这是安全问题的主要成因；专门投入人力开发定制工具。

**SAL（Standard Annotation Language）**（第 67 页）：一门**规定函数间契约**的语言：
- 目标是**轻量且实用**；
- 前置条件与后置条件；
- 更强大但更不实用的契约由 JML、Spec# 等系统支持；
- 初期聚焦内存：缓冲区大小、空指针、内存分配。

**SAL 的缓冲区/指针注解**（第 69 页）：

| 注解 | 含义 |
|---|---|
| `_in` | 函数从缓冲区**读**；调用者提供并初始化 |
| `_inout` | 函数**读写**缓冲区；调用者提供并初始化 |
| `_out` | 函数**写**缓冲区；用在返回值上表示函数提供并初始化，否则调用者提供、函数初始化 |
| `_bcount(size)` | 缓冲区大小以**字节**计 |
| `_ecount(size)` | 缓冲区大小以**元素**计 |
| `_opt` | 该参数**可以为 NULL** |

**PREfast 的即时检查**（第 70 页）：
- 库函数用法：废弃函数（如 `gets()` 易受缓冲区溢出）、`printf` 格式串与参数类型是否匹配、结果类型（用宏测试 `HRESULT`）；
- 编码错误：`if` 里把 `==` 写成 `=`；
- 局部内存错误：假设 `malloc` 返回非零、数组越界。

**注解的收益**（第 71 页）——这段值得逐条记住：

1. **注解表达设计意图**：你打算如何达成某个质量属性（例如「绝不向这个数组写超过 N 个元素」）。
2. **注解越多，发现的错误越多**：免费获得对**库使用者**的检查；而且这些错误**更不可能是假阳性**——因为分析器不用猜你的意图。
3. **注解通过模块化提升可扩展性**：PreFAST 用了非常复杂的分析技术，这些技术**无法在大程序上运行**；注解**隔离了函数**，使得可以一次只分析一个。

第 3 条是本讲最实用的工程洞察：**注解不只是「告诉工具更多信息」，它还是让分析变得可扩展的手段**。全局分析是 O(n³)，模块化分析是 O(n)——差距就在这里。

**如何激励开发者写注解？**（第 72 页）——尤其是面对几百万行未注解的代码：

- **在 check-in 时强制要求**：拒绝「有 `char*` 却没有 `__ecount()`」的代码；
- **让注解自然**：理想情况下，它就是你本来会写在注释里的东西——但现在机器可检查；
- **避免形式化与工程实践脱节**；
- **增量性**：每次编译都检查「代码 ↔ 设计」的一致性；每一份努力都有回报；**部分注解也有收益**；可以先关注最重要的部分；避免「截止日期之后再做」的借口；
- **构建注解推断工具**：推断是近似的；可惜当时在微软之外还不可用。

**「即时满足原则（Instant Gratification Principle）」** 是这段的精华：写一行注解，立刻就能看到它抓出一个 bug。这种正反馈是让开发者持续投入的唯一办法。

**微软的成效**（第 73 页）：
- **每月抓出数千个 bug**；
- 观察到显著的质量提升（例如代码库中潜伏的缓冲区溢出）；
- 开发者广泛接受：分层的 check-in 门禁、写规约。

### 5.19 本讲总结

课件第 74 页：

> **Static Analysis in Engineering Practice**
> - 一个有着不同取舍的工具
>   - 可靠性：能找出某一类中的所有错误
>   - 聚焦：机械地遵循设计规则
> - 在 Microsoft 与 eBay 有重大影响
>   - 针对公司特定问题调优
>   - 影响工程流程的每一个环节

## 6. 代码示例

### 6.1 官方课程代码

讲义 `24-staticanalysis.pdf` 中的代码全部是**待检查的示例代码**，而非分析器的实现。按页码列出：

**第 4 / 7 页：资源泄漏示例**

```java
public void loadFile(String filename) throws IOException {
    BufferedReader reader =
        new BufferedReader(
            new FileReader(filename));
    if (reader.readLine().equals("version 1.0"))
        return; // invalid version
    String c;
    while ((c = reader.readLine()) != null) {
        processData(c)
    }
    reader.close();
}
```

**第 18 页：AST 分析的性能示例**

```java
public foo() {
    …
    logger.debug("We have " + conn + "connections.");
}
```

修复版：

```java
public foo() {
    …
    if (logger.inDebug()) {
        logger.debug("We have " + conn + "connections.");
    }
}
```

**第 34 页：控制流分析的中断示例**

```c
1.  int foo() {
2.      unsigned long flags;
3.      int rv;
4.      save_flags(flags);
5.      cli();
6.      rv = dont_interrupt();
7.      if (rv > 0) {
8.          do_stuff();
9.          restore_flags();
10.     } else {
11.         handle_error_case();
12.     }
13.     return rv;
14. }
```

**第 38 页：数据流分析的空指针示例**

```java
1.  int foo() {
2.      Integer x = new Integer(6);
3.      Integer y = bar();
4.      int z;
5.      if (y != null)
6.          z = x.intVal() + y.intVal();
7.      else {
8.          z = x.intVal();
9.          y = x;
10.         x = null;
11.     }
12.     return z + x.intVal();
13. }
```

**第 39 / 42 页：方法调用与注解**

```java
1.  int foo() {
2.      Integer x = bar();
3.      Integer y = baz();
4.      Integer z = noNullsAllowed(x, y);
5.      return z.intValue();
6.  }
7.
8.  Integer noNullsAllowed(Integer x, Integer y) {
9.      int z;
10.     z = x.intValue() + y.intValue();
11.     return new Integer(z);
12. }
```

注解版：

```java
7.  @Nonnull Integer noNullsAllowed(
8.      @Nonnull Integer x,
9.      @Nonnull Integer y) {
10.     int z;
11.     z = x.intValue() + y.intValue();
12.     return new Integer(z);
13. }
14. @Nonnull Integer bar();
15. @Nullable Integer baz();
```

**第 44 页：类不变式**

```java
public class Buffer {
    boolean isOpen;
    int available;
    /*@ invariant isOpen <==> available > 0  @*/
    public void open() {
        isOpen = true;
        //invariant is broken
        available = loadBuffer();
    }
}
```

**第 48–51 页：模型检验的竞态示例**

```java
thread1() {
    read x;
}
thread2() {
    lock();
    write x;
    unlock();
}
```

**第 56 / 57 页：两个「假阳性」示例**

```java
1.  int foo(Person person) {
2.      if (person != null) {
3.          person.foo();
4.      }
5.      return person.bar();
6.  }
```

```java
1.  public class Constants {
2.      static int myConstant = 100;
3.  }
```

**第 61 页：两个「死存储」示例**

```java
void foo(int x, int y) {
    int z;
    z = x + y;
}

void foo(int x, int y) {
    List dataValues;
    dataValues = getDataFromDatabase(x, y);
}
```

**第 69 页：SAL 注解表**（见 5.18 节的表格）。

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：一个极简的资源泄漏检查器（用正则 + 手写状态机）。**

```java
import java.nio.file.*;
import java.util.regex.*;

public class NaiveLeakChecker {
    public static void main(String[] args) throws Exception {
        String src = Files.readString(Path.of(args[0]));

        boolean opened = false;
        boolean closed = false;
        int line = 0;

        for (String l : src.split("\n")) {
            line++;
            if (l.contains("new BufferedReader") || l.contains("new FileReader")) {
                opened = true;
            }
            if (l.contains("return") && opened && !closed) {
                System.out.println("行 " + line + ": 提前 return 时资源仍开着（可能泄漏）");
            }
            if (l.contains(".close()")) {
                closed = true;
            }
        }
        if (opened && !closed) {
            System.out.println("文件结束时资源仍未关闭");
        }
    }
}
```

这个「检查器」只用一个布尔变量做抽象——它**完全不知道控制流**（`return` 在 `if` 里还是不在 `if` 里都一样），所以会有大量假阳性。但它已经能抓住第 4 页那个真实 bug。**从 grep 到真正的静态分析，差距就在「抽象里有没有程序计数器」。**

**示例 B：手工实现「文件状态」数据流分析（含 join）。**

```java
import java.util.*;

public class FileStateAnalysis {
    enum State { NEEDS_CLOSING, CLOSED, UNKNOWN }

    /** 抽象状态：变量名 → 状态。join 就是逐变量取并集。 */
    static Map<String, State> join(Map<String, State> a, Map<String, State> b) {
        Map<String, State> out = new HashMap<>();
        Set<String> keys = new HashSet<>(a.keySet());
        keys.addAll(b.keySet());
        for (String k : keys) {
            State sa = a.getOrDefault(k, State.UNKNOWN);
            State sb = b.getOrDefault(k, State.UNKNOWN);
            out.put(k, sa == sb ? sa : State.UNKNOWN);   // 不同则退化为 UNKNOWN
        }
        return out;
    }

    public static void main(String[] args) {
        // 模拟 loadFile 的两条路径
        Map<String, State> thenBranch = new HashMap<>();
        thenBranch.put("reader", State.NEEDS_CLOSING);   // return 前没 close

        Map<String, State> elseBranch = new HashMap<>();
        elseBranch.put("reader", State.CLOSED);          // 正常路径 close 了

        Map<String, State> merged = join(thenBranch, elseBranch);
        System.out.println(merged);   // {reader=UNKNOWN}

        // 但真正的问题不是 join 后的状态，而是 then 分支在「函数出口」的状态
        if (thenBranch.get("reader") == State.NEEDS_CLOSING) {
            System.out.println("错误：某条路径在函数出口时资源仍开着");
        }
    }
}
```

**关键点**：join 之后 `reader` 变成 `UNKNOWN`——精度丢了，所以「函数出口」的检查不能只看 join 后的状态，必须在**每条路径到达出口时**分别检查。这就是「join 会丢失信息」的具体体现，也是为什么实际工具会同时维护「路径敏感」与「路径不敏感」两套分析。

**示例 C：用 JSR-305 风格的注解让检查变精确。**

```java
import javax.annotation.Nonnull;
import javax.annotation.Nullable;

public class NullSafe {
    @Nonnull
    static Integer bar() { return 42; }

    @Nullable
    static Integer baz() { return Math.random() > 0.5 ? 42 : null; }

    @Nonnull
    static Integer noNullsAllowed(@Nonnull Integer x, @Nonnull Integer y) {
        return x.intValue() + y.intValue();
    }

    public static void main(String[] args) {
        Integer x = bar();                 // 静态可知：not-null
        Integer y = baz();                 // 静态可知：maybe-null
        // noNullsAllowed(x, y);           // ← IDE/分析器在此报错：y 可能为 null
        if (y != null) {
            noNullsAllowed(x, y);          // ✓ 检查过之后再调用，通过
        }
    }
}
```

把最后两行的注释去掉，IntelliJ IDEA 或 Checker Framework 会立刻在 `noNullsAllowed(x, y)` 上报错。注意分析器**没有深入 `baz()` 的方法体**——它只看注解。这就是模块化分析的全部秘密：**用注解把方法体替换成一个契约**。

**示例 D：用枚举 + 状态机检查方法调用协议（typestate 的手工版）。**

```java
import java.util.*;

public class ProtocolChecker {
    enum FileState { CLOSED, OPEN }

    /** 检查一串方法调用是否符合 open → read* → close 协议。 */
    static List<String> check(List<String> calls) {
        List<String> errors = new ArrayList<>();
        FileState s = FileState.CLOSED;
        for (int i = 0; i < calls.size(); i++) {
            String c = calls.get(i);
            switch (c) {
                case "open":
                    if (s == FileState.OPEN) errors.add("第 " + i + " 步：重复 open");
                    s = FileState.OPEN;
                    break;
                case "read":
                    if (s != FileState.OPEN) errors.add("第 " + i + " 步：未 open 就 read");
                    break;
                case "close":
                    if (s != FileState.OPEN) errors.add("第 " + i + " 步：未 open 就 close");
                    s = FileState.CLOSED;
                    break;
                default:
                    errors.add("第 " + i + " 步：未知操作 " + c);
            }
        }
        if (s == FileState.OPEN) errors.add("结束时文件仍未关闭");
        return errors;
    }

    public static void main(String[] args) {
        System.out.println(check(List.of("open", "read", "close")));  // []
        System.out.println(check(List.of("open", "close", "read")));  // 未 open 就 read
        System.out.println(check(List.of("open", "read")));           // 结束时未关闭
    }
}
```

这个「状态机 + 逐条走」的结构，与课件第 6 页的资源状态图、第 33 页的中断状态机完全同构。**类型状态（typestate）就是把这种检查从「工具外挂」变成「类型系统的一部分」**——详见 [[15-214-27-Why-Objects-Typestate-DSLs]]。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| 静态分析（static analysis） | 测试（testing） | 前者**不执行**程序、抽象覆盖所有路径；后者执行具体路径、精确但覆盖极少 |
| Soundness（可靠性） | Completeness（完备性） | 可靠 = 不漏报（无假阴性），靠过近似；完备 = 不误报（无假阳性），靠欠近似 |
| 假阳性（false positive） | 假阴性（false negative） | 前者报了但没问题（噪声，烦人）；后者有问题但没报（危险，可能上线崩溃） |
| AST 分析 | 数据流分析 | 前者只看语法结构，忽略控制流与值；后者追踪变量状态的流动，精度高但昂贵 |
| 控制流分析 | 数据流分析 | 前者抽象掉数据、只看程序计数器 + 少量状态（如中断开关）；后者为每个变量维护抽象状态 |
| 全局分析（global） | 模块化分析（modular） | 前者深入每个调用、复杂度立方以上；后者用规约隔离方法，线性、可扩展，但需要写注解 |
| 分别探索路径 | Join（合并） | 前者精确但指数爆炸；后者状态数不增长但精度下降——静态分析的核心权衡 |
| 过近似（overapprox.） | 欠近似（underapprox.） | 前者把「可能的」都算进来（可靠但有误报）；后者只算「确定的」（完备但有漏报） |
| 技术上的真阳性 | 工程上的真阳性 | 前者是「可能引发运行时错误」；后者是「开发者打算修或想看到」——两者常常不一致 |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-214/slides/24-staticanalysis.pdf`
- **总页数**：74 页
- **本节重点页码**：
  - 第 2 页：课程四大主题（线程与并发、OOP、分析与建模、设计）
  - 第 3–5 页：静态分析的定义与「人工审查的局限」
  - 第 4 / 7 页：资源泄漏示例与两状态心智模型
  - 第 8 页：静态分析擅长的七类机械性错误
  - 第 9–12 页：FindBugs 介绍与演示
  - 第 13 页：InfoSys 实证研究（缺陷更少、生产率更高）
  - 第 14–15 页：本讲大纲（为什么 / 怎么做 / 难点 / 落地）
  - 第 16 页：抽象解释的定义（抽象 + 系统化）
  - 第 17–20 页：AST 分析与性能 bug 例子
  - 第 22–26 页：类型检查与不同语言的策略对比
  - 第 28–31 页：可靠性与完备性的 2×2 表、集合图、Rice 定理
  - 第 32–35 页：控制流分析与中断检查、状态爆炸与 join
  - 第 36–38 页：数据流分析与空指针检查
  - 第 39–42 页：方法调用——全局分析 vs 模块化分析 + 注解
  - 第 43 页：资源状态的另一个数据流例子（needs-closing / closed / unknown）
  - 第 44–45 页：类不变式与其他规约类型（循环不变式、锁不变式、协议）
  - 第 46–51 页：模型检验与竞态检测（四种交错）
  - 第 52–55 页：五个好处不可兼得、不同工具的取舍
  - 第 56–59 页：「假」阳性、真阳性的技术定义 vs 工程定义
  - 第 60–64 页：eBay 案例（工具定制、优先级、成本收益）
  - 第 65–73 页：Microsoft 案例（QA 演进史、PREFast、SAL、注解的收益与激励）
  - 第 74 页：总结
- **原始链接**：https://www.cs.cmu.edu/~aldrich/214/slides/24-staticanalysis.pdf
- **原文异常**：该 PDF 第 1 页页脚标注为 **Spring 2013**（本课程公开页面为 Fall 2013 版本，此讲可能沿用了春季学期的幻灯片版本，内容与 Fall 2013 课程安排一致）。

> 待核实：第 4 页与第 7 页的 `processData(c)` 缺少分号，可能是幻灯片录入时的笔误；第 38 页代码使用 `intVal()`（第 39 页用 `intValue()`），推测 `intVal()` 为幻灯片笔误，正确方法名是 `Integer.intValue()`。

## 9. 对应视频

未找到官方公开录像。

## 10. 本节复习

- 静态分析 = 对程序状态空间的**抽象**做**系统化**检查；不执行程序。
- 它擅长**机械性**错误：安全漏洞、内存错误、资源泄漏、API 规则、异常、封装破坏、竞态。
- 四种技术按抽象程度递增：AST walker（只看语法）→ 类型检查（值抽象成类型）→ 控制流分析（只看 PC + 少量状态）→ 数据流分析（每变量一个抽象状态）→ 模型检验（穷举线程交错）。
- 分支处必须选择：分别探索（精确但指数爆炸）或 join（状态不增长但精度下降）。
- 可靠性 = 无假阴性（过近似）；完备性 = 无假阳性（欠近似）。
- Rice 定理：任何非平凡性质都不可判定 → 五个好处（无假阳性、无假阴性、高性能、无需规约、模块化）最多拿三个。
- 模块化分析需要规约；规约（注解）同时提升**精度**（不用猜意图）与**可扩展性**（隔离方法，把立方复杂度降为线性）。
- 工程落地的关键不是技术指标，而是**信噪比**：优先级必须有意义，否则「全是高优先级」等于没有优先级。
- 微软的经验：注解要在 check-in 时强制、要自然、要增量、要能立刻见效（即时满足原则）。

## 11. 自我检查

**Q1.** 请为下面这段代码画出控制流，并判断「资源是否在所有路径上都被关闭」：

```java
BufferedReader r = new BufferedReader(new FileReader(f));
String line = r.readLine();
if (line == null) {
    return;
}
while ((line = r.readLine()) != null) {
    process(line);
}
r.close();
```

**Q2.** 某工具对一段代码报出 10 条警告，其中 7 条是假阳性、3 条是真问题但都不严重。另一个工具报出 2 条警告，都是真问题且严重。从工程角度你会选哪个？为什么？如果两个都要用，怎么设计流程？

**Q3.** 请解释为什么「模块化分析需要规约」，并说明如果没有规约，分析一个包含 100 个方法调用的函数会发生什么。

**Q4.** 下面这个分析属于「可靠但不可靠完备」还是「完备但不可靠」？请说明理由。

> 一个检查器只要看到 `synchronized` 关键字就认为该方法是线程安全的，否则报「可能存在竞态」。

**Q5.** 课件说「You can't even get 4 of the 5」。请具体说明为什么不能同时拿到「无假阳性 + 无假阴性 + 高性能 + 模块化」这四条。

<details>
<summary>参考答案</summary>

**A1.** 控制流有三条路径通向函数出口：① `line == null` 时提前 `return`——此时 `r` **未关闭**，泄漏；② 循环正常结束后 `r.close()`——正确；③ 若 `readLine()` 抛 `IOException`，`r` 也未关闭（虽然异常会向上传播，但句柄仍未释放）。所以结论是：**并非所有路径都关闭**。修复方式是用 try-with-resources：

```java
try (BufferedReader r = new BufferedReader(new FileReader(f))) { ... }
```

或用 `finally` 块。这个例子说明：真实代码里「提前 return」「异常」「循环」是资源泄漏的三大来源，也正是静态分析最擅长抓的「机械性错误」。

**A2.** 工程上优先选**第二个**。判断依据不是「谁报得多」，而是**信噪比**：第一个工具 70% 是噪声，开发者看几次就会开始忽略所有警告（这叫「警告疲劳」），最终 3 个真问题也会被跳过。第二个工具 100% 精确，开发者会信任它。若两个都要用：① 把第一个工具降级为「只在 nightly 构建运行、只报告高置信度类别」；② 为它的高频误报类别配置抑制规则（suppression）；③ 先在单个团队试点、按检测器分配优先级（这正是课件 eBay 案例的五步流程）；④ 设定硬指标——如果某个检测器的误报率超过阈值，直接关掉。

**A3.** 模块化分析的核心是「**只分析当前方法，不深入被调用方法**」。要做到这一点，必须知道被调用方法的**行为摘要**——它要求什么（前置条件）、保证什么（后置条件）。这个摘要就是规约。没有规约，分析器只有两个选择：① **深入方法体**（全局分析），像内联一样展开每个调用；② **假设最坏情况**（所有参数都可能为 null、所有返回值都可能为 null），这会淹没在假阳性里。对于含 100 个方法调用的函数，全局分析要展开 100 层调用树，若每个方法内部又有分支，复杂度至少是程序规模的立方，实际不可行；而且错误定位会变得极其困难——报错在深层被调用者里，但你不知道该改调用者还是被调用者。

**A4.** 属于**既不可靠也不完备**（两者都不是）。理由：① **不完备**（有假阳性）——一个方法即使加了 `synchronized`，仍可能通过未同步的字段暴露内部状态，或者锁的对象不对（锁 `this` 而其他线程锁 `ClassName.class`），检查器只看关键字就放行，属于「该报没报」的反面情形之外，更直接的是：未加 `synchronized` 的方法**未必**有竞态（它可能只访问不可变数据或线程封闭数据），所以会误报 → 假阳性 → 不完备。② **不可靠**（有假阴性）——加了 `synchronized` 的方法仍可能不安全（锁粒度不对、锁对象不一致、`wait`/`notify` 使用错误），检查器不报 → 假阴性 → 不可靠。所以这是一个典型的「启发式」检查器：靠简单规则抓住常见情形，两头都不保证。这正是课件第 55 页所说的「许多实用的 bug 查找工具既不可靠也不完备」。

**A5.** 关键在于「无假阳性 + 无假阴性」= 分析结果**完全正确**。由 Rice 定理，程序行为的任何非平凡性质都不可判定，所以不存在一个**总能停机**的算法能给出完全正确的答案——这就与「高性能（必然停机且在可接受时间内完成）」冲突。所以前三条（无假阳性、无假阴性、高性能）最多拿两条。再看「模块化」：模块化意味着分析每个方法时**不进入被调用者**，那就必须知道被调用者的行为摘要——这只能来自规约。所以「模块化」蕴含「需要规约」，即与「无需规约」互斥。因此在这五条里，无论怎么选，最多只能同时满足三条（例如：无假阳性 + 高性能 + 模块化 + 需要规约 = 4 条？不行，因为「无假阳性」+「无假阴性」不可兼得，所以是「无假阳性 + 高性能 + 模块化 + 有规约」——这是 4 条，但代价是**牺牲了无假阴性**）。课件说「连 4 条都拿不到」，指的是在「无假阳性、无假阴性、高性能、无需规约、模块化」这五条**正面表述**里最多拿 3 条：因为前三条最多拿两条，而「模块化」要求放弃「无需规约」，所以剩下的可选组合最多是「两条（从前三条）+ 模块化」= 3 条。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-22-Distributed-Systems-Part3]]——MapReduce 与 data-centric 架构。
- 下一讲：[[15-214-24-Static-Analysis-for-Concurrency]]——把静态分析专门用于竞态检测（JSure、Fluid 注解、cut points）。
- 相关讲次：[[15-214-05-Object-Contracts-and-Exceptions]]（前置/后置条件与类不变式）、[[15-214-17-Concurrency-Part1]]（竞态与数据竞争的定义）、[[15-214-27-Why-Objects-Typestate-DSLs]]（类型状态与协议）。
- 课程导航：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]、[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]。
- 术语条目：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Static Analysis 静态分析、Dataflow Analysis 数据流分析、Abstract Interpretation 抽象解释、Soundness/Completeness 可靠性/完备性）。
- 延伸阅读：Rice "Classes of Recursively Enumerable Sets and Their Decision Problems"（1953）、Cousot & Cousot "Abstract Interpretation"（POPL 1977）、Savage et al. "Eraser"（TOCS 1997）、Ayewah et al. "Using Static Analysis to Find Bugs"（IEEE Software 2008）。
