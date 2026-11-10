---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L28
topic: Course Review - A Whole-Semester Checklist
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 课程复习
  - 面向对象
  - 设计模式
  - 并发
  - 静态分析
  - 分布式系统
---

# 第 28 讲 全课程复习（Course Review）

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。本讲对应的讲义 `course-review.pdf` 只有 6 页，是一份**复习提纲（review sheet）**，不是讲授型 slides——它把整学期 27 讲的内容压缩成一张检查清单。因此本笔记的组织方式是：**按提纲的板块逐条展开**，把每个条目接回它所属的讲次，并补充提纲没有写出来的「为什么」。

## 1. 本节学习目标

- 能用一张清单自查整学期的知识覆盖度：哪些概念能一句话说清，哪些只能「眼熟」。
- 能把提纲里的每个术语**接回具体讲次**，形成可检索的知识网络。
- 能回答提纲中以「Understand / Explain / Be able to」开头的**能力型要求**——这些才是考试真正考的东西。
- 能区分**记忆型知识**（模式名字、Java 关键字）与**理解型知识**（为什么这个模式有效、这个权衡为什么存在）。
- 能对任一设计问题，快速定位到「该用哪个原则/模式/并发抽象/分析工具」。

## 2. 前置知识

本讲是复习课，前置知识就是**整门课**。按顺序列出，便于回查：

- [[15-214-01-Course-Intro-and-Organization]]：课程组织、软件工程的成本曲线。
- [[15-214-02-Objects-Encapsulation-Polymorphism]]：对象、封装、多态。
- [[15-214-03-Encapsulation-and-Inheritance]]：信息隐藏、继承、脆弱基类。
- [[15-214-04-Inheritance-Typechecking-Dispatch]]：子类型、类型检查、动态分派。
- [[15-214-05-Object-Contracts-and-Exceptions]]：契约、前置/后置条件、不变式、异常。
- [[15-214-06-Mutability-and-Java-Potpourri]]：可变性、不可变对象、Java 语言细节。
- [[15-214-07-Design-Patterns]]：12 个设计模式。
- [[15-214-17-Concurrency-Part1]] ~ [[15-214-19-Concurrency-Part3]]：并发三讲。
- [[15-214-20-Distributed-Systems-Part1]] ~ [[15-214-22-Distributed-Systems-Part3]]：分布式三讲。
- [[15-214-23-Static-Analysis]]：静态分析、抽象解释、可靠性/完备性。
- [[15-214-24-Static-Analysis-for-Concurrency]]：竞态检测、区域锁、cut points。
- [[15-214-25-Data-Consistency]]：事务、ACID、2PL、2PC。
- [[15-214-26-History-and-Future-of-Objects]]：SIMULA、Smalltalk、设计智慧。
- [[15-214-27-Why-Objects-Typestate-DSLs]]：对象的价值、类型状态、权限、TSL。

## 3. 核心概念

提纲覆盖的板块与核心概念：

- **OOP 基础**：动态分派、封装、继承、子类型（subtyping）、行为子类型（behavioral subtyping）、组合、不可变对象。
- **Java 语言**：访问修饰符、抽象类/方法、`this`/`super`、`final`、`static`、`instanceof`、类型转换、泛型、`@Override`、同一性 vs 相等性、内部类、变量遮蔽、标记接口。
- **对象契约**：`toString` / `equals` / `hashCode`。
- **异常**：受检（checked）vs 非受检（unchecked）、`try`/`catch`/`finally`、异常控制流。
- **规约与验证**：前置条件、后置条件、循环不变式、类不变式。
- **测试**：单元测试、JUnit、黑盒/白盒、断言、回归测试、TDD、结构覆盖（方法/语句/分支/路径）、规约覆盖。
- **设计原则**：为变化而设计、信息隐藏、低耦合、高内聚、Worse is Better。
- **设计模型**：UML 类图、继承 vs 关联、多重性。
- **设计模式**：Adapter、Command、Composite、Decorator、Facade、Factory Method、Iterator、MVC、Observer、Singleton、Strategy、Template Method。
- **框架**：好莱坞原则、API、client、热/冷 spot、扩展点、协议、回调、生命周期方法。
- **GUI**：事件驱动编程、MVC、GUI 单线程。
- **Java 集合**：`List`/`Set`/`Queue`/`Map`、`Iterator`、`Collections.sort`、`Comparable`。
- **Stream I/O 与网络**：流抽象、对象序列化、Socket。
- **并发**：并发 vs 并行、死锁、活锁、饥饿、竞态（低级/高级）、`synchronized`、原子性、粗/细粒度锁、`wait`/`notify`、Amdahl 定律、work/depth/breadth、`ExecutorService`、`ForkJoinPool`。
- **静态分析**：可发现的错误类型、与测试的权衡、FindBugs 定制、JSure 与设计意图、可靠性/完备性/假阳性/假阴性、别名/唯一性/线程局部性。
- **分布式系统**：部分失败与静默失败、缓存权衡、分区/复制/分片、MapReduce 与失败处理、数据一致性与事务、可串行化/可线性化、UDP/TCP。
- **对象历史**：Simula 67 的语言创新、Kay 的「对象即计算机」类比、Smalltalk 的现代遗产。

## 4. 通俗理解

**这份复习提纲最值得注意的地方，是它的动词。** 提纲里反复出现三类动词，对应三种掌握程度：

1. **Know / Understand**（知道、理解）——例如「Know all the design patterns covered in class」。这是**最低要求**：能说出名字、能认出定义。
2. **Explain / Describe**（解释、描述）——例如「Explain why Worse can be Better」「Describe the tradeoffs between static analysis and other quality assurance approaches」。这是**中等要求**：能说清**为什么**，不只是**是什么**。
3. **Be able to / Apply**（能够、应用）——例如「Be able to write a good set of unit tests for a sample function」「Apply the map-reduce paradigm to solve simple problems in parallel」。这是**最高要求**：能在**新情境**下用出来。

**提纲里有一句关键的警告**（第 3 页，设计模式部分）：

> "However, mere memorization is insufficient for mastery; understanding is critical."

**这句话就是整门课的方法论**：背下 12 个模式的名字**没有用**，你必须知道「每个模式解决什么问题、为什么它有效、它有什么后果、有哪些常见变体」。因为考试（和真实工程）考的是**判断力**——面对一个新问题，你该选哪个模式？为什么不用另一个？它的代价是什么？

**另一个值得注意的地方：提纲是「问题清单」而不是「答案清单」。** 比如「Should extending a framework require modifying the source code of the framework?」——这是一个**开放问题**，答案是「不应该，否则框架就失去了复用价值；但这意味着框架必须预先设计好扩展点」。提纲不给你答案，因为**这些问题本身就是考点**。

**怎么用这份提纲？** 最好的用法是**遮住答案自测**：看到「Behavioral Subtyping - and recognizing deviations from it」，先自己解释一遍，再回 [[15-214-04-Inheritance-Typechecking-Dispatch]] 对照。能一口气说清的跳过，卡住的标记下来重点复习。**这比从头重读 27 讲高效得多**。

## 5. 原理与推导

### 5.1 板块一：面向对象编程（第 1 页）

提纲列出六项：**动态分派、封装、继承、子类型、行为子类型、组合、不可变对象**。

**动态分派（dynamic dispatch）**：「determining which methods are called based on the runtime class of an object」。这是 OO 的核心机制（参见 [[15-214-27-Why-Objects-Typestate-DSLs]] 第 5.3 节）。关键在于**运行期**——编译期只知道静态类型，实际执行哪个方法由对象的运行时类决定。

**子类型 vs 继承**：这是最容易被混淆的一对。提纲特意写「the rules and how it differs from inheritance」：

- **继承（inheritance）** 是**代码复用**机制——子类获得父类的字段与方法实现；
- **子类型（subtyping）** 是**类型关系**——`S` 是 `T` 的子类型，意味着「任何需要 `T` 的地方都能用 `S`」；
- 在 Java 里两者**绑定**（`extends` 同时意味着两者），但**概念上独立**：`implements` 只产生子类型关系，不产生继承；C++ 的私有继承产生继承但不产生子类型。

**行为子类型（behavioral subtyping）**：Liskov 替换原则（LSP）的实质——子类型不仅要**签名兼容**，还要**行为兼容**：

- 前置条件**不能加强**（子类不能要求更多）；
- 后置条件**不能减弱**（子类不能保证更少）；
- 不变式**必须保持**；
- 历史约束（history constraint）必须保持——子类不能允许父类禁止的状态变化。

**「recognizing deviations from it」**：提纲要求你能**看出违反**。经典例子：

```java
class Rectangle {
    void setWidth(int w) { this.w = w; }
    void setHeight(int h) { this.h = h; }
}
class Square extends Rectangle {
    void setWidth(int w) { this.w = w; this.h = w; }   // ← 违反 LSP
}
```

`Square` 的 `setWidth` 改变了高度——而 `Rectangle` 的客户端假设「改宽不影响高」。这就是**行为子类型被违反**：签名兼容、行为不兼容。

**组合 vs 继承**：提纲写「Composition - e.g. in contrast to inheritance」。核心论证是**组合优于继承**（Effective Java 第 16 条）：

- 继承**打破封装**——子类依赖父类的实现细节（脆弱基类问题，见 [[15-214-27-Why-Objects-Typestate-DSLs]] 第 6.1 节）；
- 组合**保持封装**——你只依赖被组合对象的**接口**；
- 组合**更灵活**——可以在运行时替换，可以只暴露部分接口（转发）。

**不可变对象**：「understand the difference between immutable and mutable objects」。不可变对象的定义是「创建后状态不能改变」——所有字段 `final`、`this` 不逃逸、可变组件不外泄。它的价值在并发里才完全显现（见 5.10 节）：**不可变对象天然线程安全**，无需同步。

### 5.2 板块二：Java 语言细节（第 1 页）

提纲列出的关键词，每一个都有**易错点**：

**访问修饰符**：`public` / `protected` / `private` / default（package-private）。易错点：

- `protected` 不只是「子类可见」，还包括**同包可见**；
- default（不写修饰符）是**包级私有**，不是 public；
- 接口里的方法默认是 `public`（Java 8 前不能有实现）。

**抽象类 vs 抽象方法**：抽象类**不能实例化**；抽象方法**没有方法体**，必须在具体子类中实现。易错点：抽象类**可以**有构造器（供子类调用）、**可以**有具体方法。

**`this` 与 `super`**：`this` 指当前对象，`super` 指父类部分。关键点：`super.method()` **不是**动态分派——它静态地调用父类实现（这就是为什么子类覆写后仍能调用父类版本）。

**`final`**：用在**方法**上表示「不能覆写」；用在**变量**上表示「只能赋值一次」（注意：**引用 final 不等于对象不可变**）；用在**类**上表示「不能继承」。

**`static`**：属于**类**而非实例。易错点：静态方法**不能**访问实例字段、**没有** `this`、**不能**被覆写（只能被隐藏）。

**`instanceof` 与类型转换**：`instanceof` 检查运行时类型；转换（cast）在运行时检查，失败抛 `ClassCastException`。易错点：`instanceof` 对 `null` 返回 `false`。

**泛型（generics）**：Java 的泛型是**类型擦除（type erasure）**——编译后 `List<String>` 和 `List<Integer>` 都是 `List`。后果：不能 `new T[]`、不能 `instanceof List<String>`、不能重载 `f(List<String>)` 与 `f(List<Integer>)`。

**`@Override`**：不是必须的，但**强烈建议**——它让编译器检查「你真的覆写了一个方法吗」。没有它的话，参数写错（如 `equals(MyType o)` 而非 `equals(Object o)`）会变成**重载**而不是覆写，静默地不生效。

**同一性 vs 相等性**：`==` 比较**引用**（是否是同一个对象），`equals()` 比较**内容**（由类定义）。易错点：`String` 的 `==` 在字符串常量池里可能「碰巧」为 `true`，这是**实现细节**，不能依赖。

**内部类（inner class）**：非静态内部类持有**外部类实例的隐式引用**——这会导致内存泄漏（内部类对象存活则外部类不能回收）。静态嵌套类（`static class`）没有这个引用。

**变量遮蔽（variable shadowing）**：局部变量可以遮蔽字段、字段可以遮蔽父类字段。易错点：构造器参数 `this.x = x` 的写法就是在解决遮蔽。

**标记接口（marker interface）**：没有方法的接口，纯粹用来**标记**类型。例子：`Serializable`、`Cloneable`。它与**注解**的区别：标记接口提供**类型关系**（可以写 `if (o instanceof Serializable)`），注解不提供。

### 5.3 板块三：对象契约与异常（第 2 页）

**`java.lang.Object` 的三个方法**：

- `String toString()`：返回文本表示。契约：应返回「简洁但信息丰富」的字符串，且**不应**包含会变化的状态（否则日志难以比较）。
- `boolean equals(Object obj)`：**等价关系**——自反、对称、传递、一致、非空（`x.equals(null)` 必须为 `false`）。
- `int hashCode()`：契约是「`equals` 相等则 `hashCode` 必须相等」；反之不要求。

**三个方法必须一起覆写**：如果覆写 `equals` 而不覆写 `hashCode`，那么两个「相等」的对象在 `HashMap` 里会落到**不同的桶**——`map.get(k)` 找不到。这是 [[15-214-05-Object-Contracts-and-Exceptions]] 的核心考点。

**异常的两大类**：

| | 非受检（unchecked） | 受检（checked） |
|---|---|---|
| 基类 | `RuntimeException` 及其子类 | `Exception` 中除 `RuntimeException` 外 |
| 编译器要求 | 不要求捕获或声明 | **必须**捕获或 `throws` 声明 |
| 语义 | **编程错误**或不可恢复错误 | 调用者**应该**处理的、可预期的失败 |
| 例子 | `NullPointerException`、`ArrayIndexOutOfBoundsException`、`IllegalArgumentException` | `IOException`、`FileNotFoundException` |
| 何时用 | 违反前置条件（调用者的 bug） | 外部环境的失败（文件不存在、网络断开） |

**`try`/`catch`/`finally` 的控制流**：`finally` **总是**执行（除非 `System.exit` 或 JVM 崩溃）。关键细节：

- `finally` 里 `return` 会**覆盖** `try` 里的 `return`（这是 bug 的常见来源）；
- `finally` 里抛异常会**覆盖**原异常；
- Java 7 的 try-with-resources 是 `finally` 的语法糖，用于自动关闭资源。

**什么时候不该用异常**：提纲写「Know when to use exceptions (and when not to)」。不该用的场景：

- **正常控制流**——用异常做循环退出是反模式（性能差、可读性差）；
- **可以预见的、频繁的失败**——用返回值（如 `Optional`、`null`、布尔）更合适；
- **可以用前置条件避免的情况**——如果调用者本可以检查，用 `IllegalArgumentException` 表达「你违反了契约」。

### 5.4 板块四：规约与验证（第 2 页）

**前置条件（precondition）**：调用者必须保证的条件。违反它是**调用者的 bug**——方法可以不做任何承诺（可以抛异常、可以返回垃圾）。

**后置条件（postcondition）**：方法必须保证的条件。违反它是**实现者的 bug**。

**不变式（invariant）**：

- **循环不变式**：每次循环迭代开始与结束时都为真的断言。它是**证明循环正确**的工具——初始化时成立、每次迭代保持、退出时结合循环条件推出结论。
- **类不变式**：对象「在任何公开方法调用前后」都为真的性质。注意「前后」——方法**执行期间**可以暂时违反。

**提纲要求「write simple specifications and invariants for sample code」**——这是**动手能力**，不是背诵。练习方式：给一段代码，写出它的前置条件、后置条件、循环不变式，然后检查「如果前置条件成立，后置条件是否必然成立」。

**规约的价值**（这是 [[15-214-23-Static-Analysis]] 的核心论点）：规约让**模块化推理**成为可能——你只需要相信「调用者满足前置条件」，就可以假设「后置条件成立」，不需要看方法体。这就是**契约式设计（design by contract）**。

### 5.5 板块五：测试（第 2–3 页）

**单元测试的价值**：提纲问「why unit testing and its advantages」。四条理由：

1. **早期发现**——bug 越早发现修复成本越低（课程开头的成本曲线）；
2. **回归保护**——重构/加功能时，测试是「没有破坏已有行为」的证据；
3. **文档**——测试是**可执行的规约**，展示「这个方法怎么用」；
4. **设计压力**——难测试的代码往往**耦合过高**，测试驱动你解耦。

**一个好的单元测试套件应包含**（提纲明确列出）：

- **代表性用例**（representative cases）——典型输入；
- **非法输入**（invalid inputs）——违反前置条件时是否按契约行为；
- **边界条件**（boundary conditions）——0、1、-1、`Integer.MAX_VALUE`、空集合、单元素集合；
- **压力测试**（stress tests）——大数据量、长时间运行。

**黑盒 vs 白盒**：

- **黑盒（blackbox）**：不看实现，只按规约设计测试——能发现「实现与规约不符」；
- **白盒（whitebox）**：看实现，针对代码路径设计测试——能发现「某些分支从未被执行」。

**结构覆盖的四个层次**（提纲要求「understand the different structural coverage types」）：

| 覆盖类型 | 要求 | 强度 |
|---|---|---|
| **方法覆盖（method）** | 每个方法至少被调用一次 | 最弱 |
| **语句覆盖（statement）** | 每条语句至少执行一次 | 弱 |
| **分支覆盖（branch）** | 每个判定的真假分支都执行 | 中 |
| **路径覆盖（path）** | 每条可能路径都执行 | 最强（通常不可行，路径数指数增长） |

**规约覆盖（specification coverage）**：黑盒版的覆盖——规约里的**每个条款**（每个前置条件组合、每个后置条件）都至少被一个测试覆盖。

**回归测试（regression testing）**：每次改动后重跑全部测试，确保没有破坏已有行为。它的前提是**测试套件足够快**（否则没人跑）。

**TDD（测试驱动开发）**：先写测试（红）、再写实现（绿）、再重构（refactor）。它的价值不在「测试」，而在**设计**——先写测试强迫你想清楚「这个 API 该怎么用」。

### 5.6 板块六：设计原则（第 3 页）

**Design for Change（为变化而设计）**：核心问题是「软件的成本主要在维护，而维护就是应对变化」。所以设计的目标不是「满足今天的需求」，而是「让明天的变化便宜」。

**Information Hiding（信息隐藏）**：Parnas 1972 的核心论点——**模块应该隐藏「可能变化的决定」**。典型例子：数据结构的选择（用数组还是链表）应该藏在模块内部，因为这是最可能变的东西。

**Low Coupling（低耦合）**：类之间尽量独立。耦合的度量：一个类依赖多少个其他类、依赖得多深（是否依赖实现细节）。低耦合的好处：改一个类不会连锁改一片；可以独立测试。

**High Cohesion（高内聚）**：一个类应该只有**一组紧密相关**的功能。高内聚的反面是「上帝类」——什么都干，什么都依赖。

**「Explain why Worse can be Better」**：这是 Gabriel 的著名文章（见 [[15-214-26-History-and-Future-of-Objects]] 第 5.11 节）。核心论证：

- **「更好的」设计**（更正确、更一致、更完备）往往**更难实现、更难理解、更难移植**；
- **「更差的」设计**（更简单、更早发布、更少特性）往往**先获得用户**，然后在用户反馈中演化；
- 例子：Unix 与 Multics、C 与 Lisp、JavaScript 与 Java Applet。
- **代价**：Worse is Better 会产生技术债——但「先有用户再改进」往往比「完美但没人用」更成功。

**注意**：这不是「鼓励写烂代码」，而是**承认工程是权衡**——在「正确性」与「可用性/可演化性」之间，有时后者更重要。

### 5.7 板块七：UML 与设计模式（第 3–4 页）

**UML 类图的基本记号**（提纲要求「know basic UML notation」）：

- **继承/子类型**：实线 + **空心三角箭头**，指向父类；
- **关联（association）**：**实线**（无箭头=双向，有箭头=单向）；
- **聚合（aggregation）**：空心菱形，整体在菱形一侧；
- **组合（composition）**：实心菱形；
- **依赖（dependency）**：虚线 + 箭头；
- **多重性（multiplicity）**：`1`、`0..1`、`*`、`1..*`，写在关联线两端。

**易混淆点**：继承是**空心三角**（不是实心），关联是**普通实线**（没有菱形）。

**12 个设计模式**——提纲列出全部，并要求四种能力：

1. **识别**（identify patterns in source code）；
2. **命名**（name given a description, or vice versa）；
3. **画结构**（draw UML or sketch code）；
4. **建议**（suggest a pattern for a problem）；
5. **论证**（argue benefits/drawbacks in a given setting）。

**按「解决什么问题」重新分组**（这比按字母背更有效）：

| 问题 | 模式 | 一句话机制 |
|---|---|---|
| 接口不兼容 | **Adapter** | 包一层，转换接口 |
| 请求需要被参数化/排队/撤销 | **Command** | 把请求封装成对象 |
| 部分-整体结构，统一对待 | **Composite** | 容器也实现同一接口，递归调用 |
| 动态添加职责 | **Decorator** | 包一层，同接口，转发 + 增强 |
| 子系统太复杂 | **Facade** | 提供一个简化入口 |
| 创建逻辑复杂/需延迟 | **Factory Method** | 把 `new` 交给子类/工厂 |
| 遍历集合而不暴露内部结构 | **Iterator** | 把「当前位置」抽成对象 |
| UI 与逻辑分离 | **MVC** | 三方分工：模型/视图/控制器 |
| 状态变化需通知多方 | **Observer** | 注册-通知（subject 持有 observer 列表） |
| 全局唯一实例 | **Singleton** | 私有构造器 + 静态实例 |
| 算法可替换 | **Strategy** | 把算法抽成接口，组合而非继承 |
| 算法骨架固定、步骤可变 | **Template Method** | 父类定骨架，子类填步骤 |

**「mere memorization is insufficient」的含义**：考试可能给你一段代码问「这里用了什么模式、为什么、有什么缺点」。你必须能说：

- **Decorator 的缺点**：会产生大量小对象；装饰链调试困难；某些操作（如 `equals`）难以正确实现。
- **Singleton 的缺点**：全局状态、难以测试、并发下的双重检查锁陷阱。
- **Observer 的缺点**：内存泄漏（忘记注销）、通知顺序不确定、可能引发无限递归。

### 5.8 板块八：框架与 GUI（第 4 页）

**好莱坞原则**：「Don't call us; we'll call you.」——控制权在框架手里。这是框架与库的**唯一本质区别**（见 [[15-214-27-Why-Objects-Typestate-DSLs]] 第 5.10 节）。

**术语表**：

- **API**：应用编程接口——框架/库对外暴露的契约；
- **client**：使用 API 的代码；
- **热 spot（hot spot）**：框架留给你的扩展点，**你填**；
- **冷 spot（cold spot）**：框架固定的部分，**你不能改**；
- **扩展点（extension point）**：热 spot 的具体形式（接口、抽象类、注解、配置文件）；
- **协议（protocol）**：框架对你代码的**调用顺序**要求（如「`init` 一定在 `service` 之前」）；
- **回调（callback）**：框架调用你的函数；
- **生命周期方法（lifecycle methods）**：框架在特定时机调用的方法（`init`/`start`/`stop`/`destroy`）。

**提纲的三个能力要求**：

1. **「Explain the difference between a library and a framework」**——见上表；例子：`java.util` 是库，JUnit 是框架（它调用你的 `@Test` 方法）。
2. **「Describe tradeoffs between the generality of a framework and the support it provides」**——**越通用的框架，对你具体问题的支持越少**。通用框架（如 Spring）能适配任何场景，但你需要写大量配置；专用框架（如 Rails）开箱即用，但一旦你要做它没预料的事，就会打架。
3. **「Should extending a framework require modifying the source code of the framework?」**——**不应该**。如果需要改源码，说明**扩展点设计失败**——框架失去了「复用」的价值（因为你 fork 了一份，再也跟不上上游更新）。正确做法：框架预留足够的扩展点（接口、钩子、插件机制）。

**GUI 三条**：

- **事件驱动编程**：控制流由**外部事件**驱动（点击、键盘、定时器），而不是从头到尾顺序执行。Swing 的 `ActionListener` 是典型。
- **MVC**：模型（数据+逻辑）、视图（显示）、控制器（处理输入）分离。GUI 里 MVC 的价值：同一个模型可以有多个视图（表格 + 图表），改一处两边都更新。
- **GUI 单线程**：几乎所有 GUI 工具包（Swing、Android、WinForms）都是**单线程**的——所有 UI 操作必须在**事件分发线程（EDT）** 上执行。**阻塞 GUI 线程 = 界面冻结**。所以耗时操作必须放到后台线程，完成后用 `SwingUtilities.invokeLater` 回到 EDT 更新 UI。

### 5.9 板块九：Java 集合与 I/O（第 5 页）

**集合接口**：

| 接口 | 语义 | 典型实现 | 关键特性 |
|---|---|---|---|
| `List` | 有序、可重复 | `ArrayList`、`LinkedList` | 按下标访问 |
| `Set` | 无重复 | `HashSet`、`TreeSet` | `HashSet` 靠 `hashCode`；`TreeSet` 有序 |
| `Queue` | FIFO（或优先） | `ArrayDeque`、`PriorityQueue` | `offer`/`poll`/`peek` |
| `Map` | 键值映射 | `HashMap`、`TreeMap` | 键唯一 |

**其他**：`Iterator`（遍历）、`Collections.sort`（排序，稳定归并）、`Comparable`（自然序，`compareTo`）。

**易错点**：`HashMap` 的键必须正确实现 `hashCode` 与 `equals`；`TreeSet`/`TreeMap` 要求元素 `Comparable` 或提供 `Comparator`；遍历时修改集合会抛 `ConcurrentModificationException`（要用 `Iterator.remove`）。

**Stream I/O 的核心抽象**（提纲问「describe the fundamental abstraction of input/output streams」）：

- **`InputStream`/`OutputStream`**：**字节流**——`read()` 返回一个字节（0–255）或 -1，`write(int b)` 写一个字节；
- **`Reader`/`Writer`**：**字符流**——处理编码；
- **装饰器模式**：`BufferedInputStream(new FileInputStream(f))`——这就是 [[15-214-07-Design-Patterns]] 的 Decorator 在标准库里的应用；
- **对象序列化**：`ObjectOutputStream.writeObject` / `ObjectInputStream.readObject`，要求类实现 `Serializable`（**标记接口**）。

**Socket 通信**：`Socket(host, port)` 客户端、`ServerSocket(port).accept()` 服务端（见 [[15-214-20-Distributed-Systems-Part1]] 第 5 节）。

### 5.10 板块十：并发（第 5 页）

**concurrent vs parallel**：

- **并发（concurrent）**：多个任务**在时间上重叠**（交替执行）——目的是**响应性**（一个任务等待时另一个能跑）；
- **并行（parallel）**：多个任务**真正同时**执行——目的是**吞吐量**（利用多核）。

**单核也能并发，但不能并行**。这是最常考的概念区分。

**三个「坏结局」**：

| 问题 | 定义 | 区别 |
|---|---|---|
| **死锁（deadlock）** | 线程互相等待对方持有的锁，永远不前进 | **没有任何线程在前进** |
| **活锁（livelock）** | 线程不断改变状态、互相礼让，但都不前进 | **在运行，但无进展**（像两个人走廊让路） |
| **饥饿（starvation）** | 某线程长期得不到资源（如低优先级） | **别人在前进，它不前进** |

**死锁四条件**（Coffman 条件）：互斥、持有并等待、不可剥夺、循环等待。破坏任一即可预防——实践中最常用的是**破坏循环等待**（全局锁顺序）。

**竞态条件（race condition）**：程序结果依赖于线程的**交错顺序**。提纲区分「低级（low-level）与高级（high-level）」：

- **低级竞态**：数据竞争（data race）——两个线程并发访问同一内存位置，至少一个是写，且没有同步；
- **高级竞态**：逻辑竞态——即使每个操作都原子，**操作之间的顺序**仍可能导致错误（如「检查-然后-行动」check-then-act）。

**`synchronized`**：提供**互斥**（同一时刻只有一个线程进入）+ **可见性**（进入时读主内存，退出时写回）。它可以修饰方法（锁 `this` 或 `Class` 对象）或代码块（锁指定对象）。

**原子性（atomicity）**：一个操作「要么全部完成，要么完全没发生」。`i++` **不是**原子的（读-改-写三步）。`AtomicInteger` 用 CAS 提供原子性。

**粗粒度 vs 细粒度锁**：

| | 粗粒度 | 细粒度 |
|---|---|---|
| 锁的数量 | 少（可能一把大锁） | 多（每个对象/字段一把） |
| 并发度 | 低（互相阻塞） | 高 |
| 死锁风险 | 低 | 高（需要锁顺序） |
| 开销 | 低（锁操作少） | 高（锁操作多） |
| 适用 | 简单、竞争不激烈 | 复杂、需要高吞吐 |

**`wait()` 与 `notify()`**：必须在**持有锁**时调用（否则 `IllegalMonitorStateException`）。`wait()` 释放锁并等待；`notify()` 唤醒一个等待者（`notifyAll()` 唤醒全部）。**必须用 `while` 而非 `if` 包裹 `wait()`**——因为被唤醒后条件可能又不成立（虚假唤醒、其他线程抢先）。

**Amdahl 定律**：加速比 `S(n) = 1 / ((1-p) + p/n)`，其中 `p` 是可并行部分的比例。**关键洞察**：即使 `n → ∞`，加速比上限是 `1/(1-p)`。如果 10% 是串行的，最多加速 10 倍。

**work / depth / breadth**（fork-join 的复杂度度量）：

- **work**：所有操作的总数（单处理器上的时间）；
- **depth（span）**：**关键路径**长度（无限处理器上的时间）；
- **breadth**：`work / depth`——理论最大并行度；
- **理想加速比**：`work / depth`。

**`ExecutorService` 与 `ForkJoinPool`**：

- `ExecutorService`：线程池 + 任务队列，`submit` 返回 `Future`；
- `ForkJoinPool`：为**分治**任务设计，用 **work-stealing**（空闲线程从别的线程队列尾部偷任务），配合 `RecursiveTask`/`RecursiveAction`。

### 5.11 板块十一：静态分析（第 6 页）

提纲这一节全是**能力型要求**，逐条对应：

**「Characterize the kinds of errors that static analysis can find」**：机械性的、有固定模式的错误——资源泄漏、空指针、竞态、类型错误、API 误用。**不能**发现的是「设计错误」「需求错误」「算法错误」（这些需要人的判断）。

**「Tradeoffs between static analysis and testing」**：

| | 静态分析 | 测试 |
|---|---|---|
| 覆盖 | **所有**可能执行路径（过近似） | 只覆盖**实际执行**的路径 |
| 时机 | 编译期，无需运行 | 运行期，需要可执行环境 |
| 误报 | 有（假阳性） | 无（测试失败就是失败） |
| 漏报 | 可能（假阴性，若不 sound） | 有（未覆盖的路径） |
| 成本 | 一次性配置 + 持续运行 | 每个测试要写、要维护 |

**「Explain these tradeoffs in a particular context, such as finding race conditions」**：竞态检测特别难，因为：

- **非局部**——bug 在两个相距很远的代码之间；
- **难测试**——需要特定交错，可能百万次运行才出现一次；
- **误报多**——分析器不知道哪些锁保护哪些数据（需要注解）；
- **好代码被坏代码污染**——一个未同步的字段让整个类的分析失效。

**「Cost-benefit analysis when adopting a static analysis tool」**：成本 = 工具费用 + 配置时间 + 误报处理时间 + 开发者学习曲线；收益 = 早期发现的 bug 数 × 每个 bug 的修复成本差（生产环境 vs 开发环境）。课件里 eBay 的案例（[[15-214-23-Static-Analysis]] 第 5 节）就是这个分析的实例。

**「Need to customize a generic tool like FindBugs」**：通用工具不知道**你的**约定——比如「所有 `close()` 必须在 `finally` 里调用」「这个字段由 `lock` 保护」。必须写**自定义检测器**或**注解**，否则误报率高到没人用。

**「Design intent and specification (e.g. JSure) make analysis both more modular and more effective」**：

- **更模块化**——有了 `@RegionLock("FL is this protects filter")` 这样的注解，分析器不需要看整个程序，只需看注解；
- **更有效**——注解告诉分析器「设计者的意图」，减少误报。

**「Define soundness, completeness, false positives, false negatives」**：

| 术语 | 定义 | 直觉 |
|---|---|---|
| **可靠性（soundness）** | 没有**假阴性**——报「无问题」就真的无问题 | 过近似（over-approximation）：把可能的状态都算进来 |
| **完备性（completeness）** | 没有**假阳性**——报「有问题」就真的有问题 | 欠近似（under-approximation） |
| **假阳性（false positive）** | 报了但**不是**真 bug | 狼来了 |
| **假阴性（false negative）** | 有 bug 但**没报** | 漏网之鱼 |

**关键权衡**：可靠性与完备性**不能同时满足**（Rice 定理）——任何非平凡的性质都是不可判定的。实践中的工具在两者之间取舍：FindBugs 偏向**完备**（低误报，但漏报多）；模型检验偏向**可靠**（不漏报，但误报多）。

**「Aliasing, uniqueness, and thread-locality bear on safe concurrency」**：

- **别名（aliasing）**：两个引用指向同一对象——分析器无法确定「谁在什么时候访问」；
- **唯一性（uniqueness）**：只有一个引用——没有竞态；
- **线程局部性（thread-locality）**：对象只被一个线程访问——没有竞态。

这三者是**线程安全的三条充分条件**——只要能证明其中之一，就不需要锁（见 [[15-214-24-Static-Analysis-for-Concurrency]]）。

### 5.12 板块十二：分布式系统（第 6 页）

**「High-level challenges」**：部分失败（partial failure）、静默失败（silent failure）、不一致（inconsistency）、安全（security）、异构（heterogeneity）、规模（scale）、地理分布（geography）、并发（concurrency）。

**部分失败是最根本的难点**：单机程序要么运行要么崩溃；分布式系统里**一部分在工作、一部分已死**，而且**你无法区分「对方死了」与「网络断了」**（这是 [[15-214-20-Distributed-Systems-Part1]] 的核心论点）。

**静默失败（silent failure）**：请求发出去了，但**没有响应、也没有错误**——你不知道它是否被执行。这是分布式事务必须用两阶段提交的原因。

**「Benefits and costs of caching」**：

| | 收益 | 代价 |
|---|---|---|
| 简单性 | — | 降低（需要失效逻辑） |
| 一致性 | — | 降低（可能读到旧数据） |
| 带宽 | 降低（少发请求） | — |
| 计算 | 降低（少算） | — |
| 延迟 | 降低 | — |

**客户端缓存 vs 服务端缓存**：客户端缓存**减少网络往返**，但**失效困难**（要通知所有客户端）；服务端缓存**失效容易**（数据在本地），但**不减少网络往返**。

**「Partitioning / replication / sharding」**：

- **复制（replication）**：同一份数据存多份——提高**可用性**与**读吞吐**，代价是**写放大**与**一致性**问题；
- **分区/分片（partitioning / sharding）**：不同数据存不同节点——提高**写吞吐**与**容量**，代价是**跨分片查询**与**再平衡**；
- **两者正交**：可以「先分片，每片再复制」。

**「MapReduce 与失败处理」**：

- `map`：`(k1, v1) → [(k2, v2)]`，在各分片上并行；
- `shuffle`：按 `k2` 分组；
- `reduce`：`(k2, [v2]) → [v2]`；
- **失败处理**：map worker 失败 → 用**输入副本**重跑；reduce worker 失败 → 从 map worker 的**本地磁盘**重拉中间结果；master 失败 → 重启整个作业（或从检查点恢复）。

**「Data consistency and transaction」**：事务是**一组操作的原子单元**——要么全做（commit），要么全不做（abort）。**ACID**：原子性、一致性、隔离性、持久性。

**「Tell if a trace of operations is serializable (or linearizable)」**：

- **可串行化（serializable）**：并发执行的结果**等价于**某个**串行**执行；
- **可线性化（linearizable）**：每个操作在「调用与返回之间」的某个瞬间**原子生效**，且尊重实时顺序。

判断方法：画出操作的时间区间，尝试找一个串行顺序，使每个读都读到「它之前最后一次写」的值。

**「UDP and TCP」**：

| | UDP | TCP |
|---|---|---|
| 连接 | 无连接 | 面向连接（三次握手） |
| 可靠性 | 不可靠（可能丢、乱序、重复） | 可靠（重传、排序、去重） |
| 边界 | 保留消息边界（数据报） | 字节流（无边界） |
| 开销 | 低 | 高 |
| 用途 | DNS、视频、游戏 | HTTP、文件传输 |

### 5.13 板块十三：对象历史（第 6 页）

提纲只有三个问题，但每个都是**开放题**：

**「What were the key language innovations introduced by Simula 67? Which is the most important, according to the last course lecture?」**

Simula 67 的创新（见 [[15-214-26-History-and-Future-of-Objects]]）：

1. **类（class）与对象（object）**——把数据和操作打包成模板；
2. **继承（inheritance）与类前缀（class prefix）**——复用与特化；
3. **虚过程（virtual procedures）**——**动态分派**；
4. **协程（coroutine）**——并发的前身。

**「哪一个最重要」**：按 [[15-214-27-Why-Objects-Typestate-DSLs]] 的论证，答案是**动态分派**——因为它是 OO 唯一**不可替代**的能力（封装、继承都能用别的机制实现）。

**「Explain the analogy Alan Kay makes between objects in Smalltalk and computers」**

Kay 的类比是「**recursion on the notion of computer**」——**把「计算机」这个概念递归地应用到它自身**：

- 一台计算机 = 硬件 + 软件 + 网络通信；
- 一个对象 = 状态 + 行为 + **消息传递**；
- 整个系统 = 一组对象通过**消息**互相通信，就像一组计算机通过**网络**互相通信。

**这个类比的深刻之处**：它把「对象」看成**独立的、并发的、只能通过消息交互的单元**——这直接预示了后来的**分布式系统**（Emerald，见 [[15-214-27-Why-Objects-Typestate-DSLs]] 第 5.7 节）与**Actor 模型**（Erlang）。

**「Name a feature of a modern language that derives from Smalltalk」**

候选答案（任一即可）：

- **垃圾回收（garbage collection）**——Smalltalk 是最早普及 GC 的语言之一；
- **反射（reflection）**——Smalltalk 的 `introspect` 一切皆对象，Java 的 `Class`/`Method` 源于此；
- **消息发送语法**——Objective-C 的 `[obj msg]` 直接来自 Smalltalk；
- **MVC**——Smalltalk-80 的 UI 框架，后来成为 Cocoa、MFC、AWT 的基础；
- **IDE 与实时编程环境**——Smalltalk 的浏览器/工作区是现代 IDE 的祖先；
- **纯面向对象**——「一切皆对象」（连 `3 + 4` 都是发送 `+` 消息）影响了 Ruby、Python。

## 6. 代码示例

### 6.1 官方课程代码

`course-review.pdf` 是**复习提纲**，本身**不含代码**——它只列术语与能力要求。提纲中提到的代码相关条目如下（对应的代码在各自讲次的讲义里）：

- **`java.lang.Object` 的方法签名**（`course-review.pdf` 第 2 页）：

```java
String toString()
boolean equals(Object obj)
int hashCode()
```

- **异常类型层次**（`course-review.pdf` 第 2 页）：
  - 非受检：`RuntimeException` 的子类，如 `NullPointerException`、`ArrayIndexOutOfBoundsException`；
  - 受检：非 `RuntimeException`，如 `IOException`、`FileNotFoundException`。

- **Java 集合接口**（`course-review.pdf` 第 5 页）：`java.util.List`、`java.util.Set`、`java.util.Queue`、`java.util.Map`、`java.util.Iterator`、`Collections.sort`、`java.util.Comparable`。

- **并发 API**（`course-review.pdf` 第 5 页）：`synchronized`、`wait()`、`notify()`、`ExecutorService`、`ForkJoinPool`。

> 待核实：`course-review.pdf` 第 3 页脚注给出的 UML cheatsheet 是一个 Google Docs 链接（`https://docs.google.com/document/d/1dtWtA5rUAZ8rX2S0Z5zbSsan6nGXEmxQRrLS177yJRw/edit?usp=sharing`），2013 年的分享链接可能已失效，未验证可访问性。

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：一个「考试风格」的小程序，串起 OOP + 契约 + 异常 + 泛型。**

```java
import java.util.*;

/** 一个不可变的有理数类：演示 equals/hashCode/toString 的契约 */
public final class Rational implements Comparable<Rational> {
    private final int num;      // 分子
    private final int den;      // 分母，恒 > 0

    public Rational(int num, int den) {
        if (den == 0) throw new IllegalArgumentException("分母不能为 0");  // 前置条件
        int g = gcd(Math.abs(num), Math.abs(den));
        // 规范化：分母为正，且已约分 —— 这是类不变式
        this.num = (den < 0 ? -num : num) / g;
        this.den = Math.abs(den) / g;
    }

    private static int gcd(int a, int b) { return b == 0 ? a : gcd(b, a % b); }

    public Rational plus(Rational o) {
        return new Rational(num * o.den + o.num * den, den * o.den);
    }

    @Override public String toString() { return num + "/" + den; }

    @Override public boolean equals(Object o) {
        if (this == o) return true;                     // 同一性捷径
        if (!(o instanceof Rational)) return false;     // 类型检查（含 null）
        Rational r = (Rational) o;
        return num == r.num && den == r.den;            // 已规范化，可直接比
    }

    @Override public int hashCode() { return 31 * num + den; }

    @Override public int compareTo(Rational o) {
        return Integer.compare(num * o.den, o.num * den);
    }

    public static void main(String[] args) {
        List<Rational> xs = new ArrayList<>(List.of(
                new Rational(1, 2), new Rational(1, 3), new Rational(2, 3)));
        Collections.sort(xs);
        System.out.println(xs);                                  // [1/3, 1/2, 2/3]

        System.out.println(new Rational(2, 4).equals(new Rational(1, 2)));  // true
        System.out.println(new Rational(1, 2).hashCode()
                == new Rational(2, 4).hashCode());               // true

        try {
            new Rational(1, 0);
        } catch (IllegalArgumentException e) {
            System.out.println("捕获：" + e.getMessage());        // 捕获：分母不能为 0
        }
    }
}
```

**这个例子覆盖的考点**：

- `final` 类 + `final` 字段 = **不可变对象**；
- 构造器检查**前置条件**，抛**非受检异常**（`IllegalArgumentException`）；
- **类不变式**（分母恒正、已约分）在构造器里建立；
- `equals` 的五个契约（自反、对称、传递、一致、非空）；
- `equals` 与 `hashCode` **一起覆写**；
- `instanceof` + 强制转换；
- `Comparable` + `Collections.sort`；
- `@Override` 让编译器检查签名。

**示例 B：并发 + 死锁 + 修复（考试高频题型）。**

```java
/** 有死锁风险的转账：两个账户互相转账 */
class Account {
    private final String id;
    private long balance;
    Account(String id, long balance) { this.id = id; this.balance = balance; }

    /** 错误版本：按参数顺序加锁 → 循环等待 → 死锁 */
    static void transferBad(Account from, Account to, long amount) {
        synchronized (from) {
            synchronized (to) {
                if (from.balance >= amount) {
                    from.balance -= amount;
                    to.balance += amount;
                }
            }
        }
    }

    /** 正确版本：按 id 排序加锁 → 破坏循环等待 */
    static void transferGood(Account a, Account b, long amount) {
        Account first = a.id.compareTo(b.id) < 0 ? a : b;
        Account second = (first == a) ? b : a;
        synchronized (first) {
            synchronized (second) {
                Account from = a, to = b;
                if (from.balance >= amount) {
                    from.balance -= amount;
                    to.balance += amount;
                }
            }
        }
    }

    long balance() { synchronized (this) { return balance; } }
    public String toString() { return id + ":" + balance(); }
}

public class DeadlockDemo {
    public static void main(String[] args) throws InterruptedException {
        Account x = new Account("A", 1000);
        Account y = new Account("B", 1000);

        // 线程 1：x → y；线程 2：y → x。用 transferBad 会死锁。
        Thread t1 = new Thread(() -> {
            for (int i = 0; i < 100_000; i++) Account.transferGood(x, y, 1);
        });
        Thread t2 = new Thread(() -> {
            for (int i = 0; i < 100_000; i++) Account.transferGood(y, x, 1);
        });
        t1.start(); t2.start();
        t1.join(); t2.join();
        System.out.println(x + " " + y);        // 总额守恒：2000
    }
}
```

**这个例子覆盖的考点**：

- **死锁四条件**：`transferBad` 里同时满足互斥、持有并等待、不可剥夺、循环等待；
- **预防**：`transferGood` 用**全局锁顺序**破坏「循环等待」；
- **`synchronized` 的双重作用**：互斥 + 可见性；
- **原子性**：`balance -= amount` 在锁内才是原子的；
- **高内聚**：`balance()` 也加锁，保证读到的不是中间状态。

**示例 C：用「检查-然后-行动」演示高级竞态。**

```java
import java.util.*;

/** 演示 check-then-act 竞态：即使每个操作都 synchronized，组合起来仍不安全 */
public class CheckThenAct {
    private final Map<String, Integer> cache = new HashMap<>();

    /** 错误：两个 synchronized 方法之间，状态可能被别的线程改变 */
    synchronized boolean contains(String k) { return cache.containsKey(k); }
    synchronized void put(String k, int v) { cache.put(k, v); }

    void badUse(String k) {
        if (!contains(k)) {          // ← 检查
            // 此处另一个线程可能已经 put 了 k
            put(k, compute(k));      // ← 行动（覆盖了别人的结果）
        }
    }

    /** 正确：把「检查 + 行动」放在同一个临界区 */
    synchronized void goodUse(String k) {
        if (!cache.containsKey(k)) {
            cache.put(k, compute(k));
        }
    }

    private int compute(String k) { return k.length(); }

    public static void main(String[] args) throws InterruptedException {
        CheckThenAct c = new CheckThenAct();
        List<Thread> ts = new ArrayList<>();
        for (int i = 0; i < 8; i++) {
            final int n = i;
            ts.add(new Thread(() -> {
                for (int j = 0; j < 10_000; j++) c.badUse("key" + (j % 16));
            }));
        }
        for (Thread t : ts) t.start();
        for (Thread t : ts) t.join();
        System.out.println("cache size = " + c.cache.size() + "（应为 16）");
    }
}
```

**这个例子覆盖的考点**：

- **低级竞态 vs 高级竞态**：`contains` 和 `put` 各自都是原子的，但**组合**不是——这就是高级竞态；
- **临界区应该包含「检查 + 行动」整体**——这是并发设计的核心原则；
- **为什么 `synchronized` 方法不够**：锁的粒度太细，保护不了跨方法的复合操作。

**示例 D：一个「判断可串行化」的练习框架。**

```java
import java.util.*;

/**
 * 判断一个执行历史是否可串行化（简化版：只处理读/写，忽略事务的本地计算）。
 * 方法：构造「冲突图」（conflict graph），检测是否有环。
 * 两个操作冲突 = 不同事务 + 访问同一数据 + 至少一个是写。
 */
public class SerializableCheck {

    record Op(String txn, boolean isWrite, String item) { }

    /** 判断历史是否冲突可串行化 */
    static boolean isSerializable(List<Op> history) {
        // 1. 构造冲突图：节点是事务
        Map<String, Set<String>> graph = new LinkedHashMap<>();
        for (Op o : history) graph.putIfAbsent(o.txn(), new LinkedHashSet<>());

        // 2. 对每一对「先发生」的操作，若冲突则加边
        for (int i = 0; i < history.size(); i++) {
            for (int j = i + 1; j < history.size(); j++) {
                Op a = history.get(i), b = history.get(j);
                if (a.txn().equals(b.txn())) continue;              // 同一事务不算冲突
                if (!a.item().equals(b.item())) continue;           // 不同数据不算冲突
                if (!a.isWrite() && !b.isWrite()) continue;         // 读-读不算冲突
                graph.get(a.txn()).add(b.txn());                    // a 必须先于 b
            }
        }

        // 3. 检测环（DFS 三色标记）
        Map<String, Integer> color = new HashMap<>();  // 0=白 1=灰 2=黑
        for (String t : graph.keySet()) color.put(t, 0);
        for (String t : graph.keySet()) {
            if (color.get(t) == 0 && hasCycle(t, graph, color)) return false;
        }
        return true;
    }

    private static boolean hasCycle(String u, Map<String, Set<String>> g, Map<String, Integer> color) {
        color.put(u, 1);                                   // 灰：正在访问
        for (String v : g.getOrDefault(u, Set.of())) {
            if (color.get(v) == 1) return true;            // 回到灰色 → 有环
            if (color.get(v) == 0 && hasCycle(v, g, color)) return true;
        }
        color.put(u, 2);                                   // 黑：完成
        return false;
    }

    public static void main(String[] args) {
        // 例 1：可串行化（等价于 T1 先、T2 后）
        List<Op> h1 = List.of(
                new Op("T1", true,  "x"),
                new Op("T2", false, "x"),
                new Op("T1", true,  "y"),
                new Op("T2", true,  "y"));
        System.out.println("h1 可串行化 = " + isSerializable(h1));   // true

        // 例 2：不可串行化（写-写交叉，形成 T1→T2→T1 的环）
        List<Op> h2 = List.of(
                new Op("T1", true,  "x"),
                new Op("T2", true,  "x"),
                new Op("T2", true,  "y"),
                new Op("T1", true,  "y"));
        System.out.println("h2 可串行化 = " + isSerializable(h2));   // false
    }
}
```

**这个例子覆盖的考点**：

- **冲突（conflict）的定义**：不同事务、同一数据、至少一个写；
- **冲突可串行化**：冲突图无环 ⟺ 可串行化；
- **与 [[15-214-25-Data-Consistency]] 的 2PL 的关系**：两阶段锁**保证**冲突图无环（因为锁的释放点在「生长阶段」之后）；
- **注意**：这里实现的是**冲突可串行化**（conflict serializability），比**视图可串行化**（view serializability）更严格但更易检查。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| 继承（inheritance） | 子类型（subtyping） | 前者是**代码复用**（拿到实现）；后者是**类型关系**（能替换）；Java 的 `extends` 同时提供两者，`implements` 只提供后者 |
| 子类型 | 行为子类型 | 前者只要求**签名兼容**；后者还要求**行为兼容**（前置不能加强、后置不能减弱） |
| 覆写（override） | 重载（overload） | 前者是**运行时**选择（同签名、子类替换）；后者是**编译期**选择（不同参数列表） |
| `==` | `equals()` | 前者比较**引用同一性**；后者比较**内容相等**（可覆写） |
| 覆写 `equals` | 覆写 `hashCode` | 必须**一起做**；只做前者会让 `HashMap`/`HashSet` 失效 |
| 受检异常 | 非受检异常 | 前者编译器**强制**处理（`IOException`）；后者表示**编程错误**（`NullPointerException`） |
| 前置条件违反 | 后置条件违反 | 前者是**调用者的 bug**；后者是**实现者的 bug** |
| 循环不变式 | 类不变式 | 前者在**每次迭代**前后为真；后者在**每个公开方法**调用前后为真 |
| 黑盒测试 | 白盒测试 | 前者按**规约**设计（不知实现）；后者按**实现**设计（覆盖路径） |
| 语句覆盖 | 分支覆盖 | 前者要求每条语句执行一次；后者要求每个判定的**两个方向**都执行 |
| 低耦合 | 高内聚 | 前者是**类之间**的关系（越少越好）；后者是**类内部**的关系（越集中越好） |
| 库（library） | 框架（framework） | 你调用库；框架调用你（好莱坞原则） |
| 热 spot | 冷 spot | 前者是**你填**的扩展点；后者是**框架固定**的部分 |
| 并发（concurrent） | 并行（parallel） | 前者是**时间上重叠**（可在单核）；后者是**真正同时**（需多核） |
| 死锁 | 活锁 | 前者**没人能前进**（互相等锁）；后者**都在动但无进展**（互相礼让） |
| 活锁 | 饥饿 | 前者是**集体**无进展；后者是**个别**线程长期得不到资源 |
| 数据竞争（data race） | 竞态条件（race condition） | 前者是**低级**的（同一内存并发访问、无同步）；后者是**高级**的（结果依赖交错，即使每个操作原子） |
| 粗粒度锁 | 细粒度锁 | 前者简单、并发度低、死锁风险低；后者复杂、并发度高、死锁风险高 |
| 可靠性（soundness） | 完备性（completeness） | 前者**无假阴性**（过近似）；后者**无假阳性**（欠近似）；两者不可兼得（Rice 定理） |
| 假阳性（FP） | 假阴性（FN） | 前者**报了但不是 bug**（狼来了）；后者**是 bug 但没报**（漏网） |
| 复制（replication） | 分区（partitioning） | 前者**同一份数据多副本**（提高可用性/读吞吐）；后者**不同数据不同节点**（提高写吞吐/容量） |
| 可串行化（serializable） | 可线性化（linearizable） | 前者只要求**等价于某个串行顺序**；后者还要求**尊重实时顺序**（更强） |
| UDP | TCP | 前者无连接、不可靠、保留消息边界；后者面向连接、可靠、字节流 |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-214/slides/course-review.pdf`
- **总页数**：6 页
- **重点页码**：
  - **第 1 页**：面向对象编程（动态分派、封装、继承、子类型、行为子类型、组合、不可变对象）+ 术语（receiver、member function、base/derived class）+ Java 关键字（访问修饰符、抽象类、`this`/`super`、`final`、`static`、`instanceof`、casting、泛型、`@Override`、同一性 vs 相等性）+ 其他（内部类、变量遮蔽、标记接口）
  - **第 2 页**：对象契约（`toString`/`equals`/`hashCode`）+ 异常（受检/非受检、`try`/`catch`/`finally`）+ 规约与验证（前置/后置条件、循环/类不变式）+ 测试（单元测试、JUnit、代表性/非法/边界/压力用例、黑盒/白盒、断言）
  - **第 3 页**：测试续（回归测试、TDD、结构覆盖方法/语句/分支/路径、规约覆盖）+ 设计原则（Design for Change、Information Hiding、Low Coupling、High Cohesion、Worse is Better）+ 设计模型（UML、继承 vs 关联、多重性）+ 设计模式开头（Adapater、Command；脚注给出 UML cheatsheet 的 Google Docs 链接）
  - **第 4 页**：设计模式续（Composite、Decorator、Facade、Factory Method、Iterator、MVC、Observer、Singleton、Strategy、Template Method）+ 框架（好莱坞原则、API、client、热/冷 spot、扩展点、协议、回调、生命周期方法）+ GUI（事件驱动、MVC、GUI 单线程）
  - **第 5 页**：GUI 续（GUI 线程阻塞导致冻结）+ Java 集合（`List`/`Set`/`Queue`/`Map`、`Iterator`、`Collections.sort`、`Comparable`）+ Stream I/O 与网络（流抽象、对象读写、Socket）+ 并发（concurrent vs parallel、死锁、活锁、饥饿、竞态、`synchronized`、原子性、粗/细粒度锁、`wait`/`notify`、Amdahl、work/depth/breadth、`ExecutorService`/`ForkJoinPool`）
  - **第 6 页**：静态分析（错误类型、与测试的权衡、竞态检测情境、成本收益、FindBugs 定制、JSure 与设计意图、可靠性/完备性/假阳性/假阴性、别名/唯一性/线程局部性）+ 分布式系统（挑战、缓存、分区/复制/分片、map-reduce 与失败、一致性与事务、可串行化/可线性化、UDP/TCP）+ 对象历史（Simula 67 创新、Kay 的类比、Smalltalk 的现代遗产）
- **原始链接**：https://www.cs.cmu.edu/~aldrich/214/slides/course-review.pdf
- **说明**：这是一份 **review sheet（复习提纲）**，不是讲授型 slides——它只列条目，不含讲解与代码。因此本笔记的「官方课程代码」一节（6.1）只能引用提纲里出现的**签名与类名**，实际代码请回各讲讲义。

> 待核实：提纲第 2 页把 `ArrayIndexOutOfBoundsException` 写作 `ArrayOutOfBoundsException`（漏了 `Index`），应为笔误。
> 待核实：提纲第 3 页把 `Adapter` 写作 `Adapater`（第 3 页列表首项），应为笔误。

## 9. 对应视频

未找到官方公开录像。

## 10. 本节复习

**按板块的一句话总结**：

- **OOP**：动态分派是核心；继承 ≠ 子类型 ≠ 行为子类型；组合优于继承；不可变对象天然线程安全。
- **Java**：`final` 引用 ≠ 不可变对象；`==` 是引用、`equals` 是内容；泛型是类型擦除；`@Override` 是安全网。
- **契约**：`equals`/`hashCode`/`toString` 必须一起覆写；`equals` 是等价关系。
- **异常**：受检 = 调用者必须处理（外部失败）；非受检 = 编程错误；`finally` 总执行，但会覆盖 `return`。
- **规约**：前置条件是调用者的责任，后置条件是实现者的责任；不变式让模块化推理成为可能。
- **测试**：好套件 = 代表性 + 非法 + 边界 + 压力；黑盒测规约，白盒测路径；路径覆盖通常不可行。
- **设计原则**：为变化而设计 → 信息隐藏 → 低耦合高内聚；Worse is Better 是工程权衡，不是鼓励烂代码。
- **模式**：按「解决什么问题」记，不按字母背；每个模式都要能说出代价。
- **框架**：好莱坞原则；热 spot 你填、冷 spot 框架定；扩展**不应该**改框架源码。
- **GUI**：事件驱动；MVC 分离；GUI 单线程，阻塞 = 冻结。
- **集合**：`List`/`Set`/`Queue`/`Map` 的语义与实现选择；`HashMap` 依赖 `hashCode`。
- **I/O**：字节流 vs 字符流；装饰器叠加；序列化需要 `Serializable`。
- **并发**：并发 ≠ 并行；死锁四条件；低级竞态 vs 高级竞态；`synchronized` = 互斥 + 可见性；`wait` 必须用 `while` 包；Amdahl 上限是 `1/(1-p)`。
- **静态分析**：可靠性 = 无假阴性，完备性 = 无假阳性，不可兼得；别名/唯一性/线程局部性是线程安全的三条充分条件；注解让分析更模块化。
- **分布式**：部分失败是根本难点；缓存换来延迟、付出一致性；复制提高可用性、分区提高容量；MapReduce 用重跑处理失败；2PL 保证可串行化，2PC 保证原子提交。
- **历史**：Simula 67 的四大创新（类、继承、虚过程、协程），最重要的是**动态分派**；Kay 的「对象即计算机」预言了分布式与 Actor；Smalltalk 留下了 GC、反射、MVC、消息语法。

**复习方法建议**：

1. **先做「一句话测试」**——对上面每个条目，能否不看笔记说清？卡住的标记。
2. **再做「对比表测试」**——第 7 节的 24 组对比，能否说出每组的**关键差别**？
3. **最后做「应用题」**——给一段代码，能否指出它用了什么模式、违反了什么原则、有什么并发问题？

## 11. 自我检查

**Q1.** 请解释「继承」与「子类型」的区别，并说明为什么 Java 的 `implements` 只产生子类型关系而不产生继承。举一个「行为子类型被违反」的例子。

**Q2.** 提纲要求「understand the tradeoffs between static analysis and testing」。请从**覆盖范围、误报、漏报、成本**四个维度对比，并说明为什么竞态检测特别适合静态分析（尽管它误报多）。

**Q3.** 一个执行历史包含事务 T1、T2 的以下操作（按时间顺序）：`R1(x), W2(x), W1(y), R2(y)`。它是否冲突可串行化？请画出冲突图并说明。如果不可串行化，两阶段锁能阻止它吗？

**Q4.** 请说明 `wait()` 为什么必须放在 `while` 循环里而不是 `if` 里，并举出一个用 `if` 会导致错误的场景。

**Q5.** 提纲问「Should extending a framework require modifying the source code of the framework?」请给出你的回答，并说明「如果必须修改源码」意味着框架设计出了什么问题。

<details>
<summary>参考答案</summary>

**A1.** **继承**是**代码复用**机制：子类获得父类的字段与方法实现，可以覆写。**子类型**是**类型关系**：`S <: T` 意味着「任何期望 `T` 的地方都能安全使用 `S`」——这是**可替换性**（LSP）。在 Java 里 `extends` **同时**产生两者（因为 Java 把继承与子类型绑定），但 `implements` **只**产生子类型关系：一个类实现接口时，**不获得**任何实现代码（Java 8 前），只是承诺「我提供这些方法」。所以 `implements` 是纯子类型。**反例：C++ 的私有继承**产生继承（拿到实现）但不产生子类型（不能替换）；**Go 的接口**产生子类型（隐式实现）但没有继承。**行为子类型违反的例子**：`Square extends Rectangle`，`Square.setWidth(w)` 同时把高度设为 `w`——签名完全兼容，但 `Rectangle` 的客户端假设「改宽不影响高」，于是 `Square` 不能安全替换 `Rectangle`。这就是**签名子类型但非行为子类型**。

**A2.** **四维对比**：
- **覆盖范围**：静态分析覆盖**所有可能路径**（过近似，包括不会实际执行的路径）；测试只覆盖**实际执行的路径**（未覆盖的分支完全没检查）。
- **误报**：静态分析**有**假阳性（报了但不是 bug），需要人工甄别；测试**没有**假阳性（测试失败就是失败，断言是确定的）。
- **漏报**：静态分析若**可靠（sound）**则无假阴性；但实用工具通常**不可靠**（为了降低误报而放弃 soundness），所以也会漏。测试**必然**有假阴性（未覆盖的输入/路径）。
- **成本**：静态分析是**一次性配置 + 持续运行**，边际成本极低；测试要**为每个用例编写与维护**，边际成本高。
**为什么竞态检测适合静态分析**：竞态的特点是 ①**非局部**（bug 分布在相距很远的代码之间，人工审查难以发现）；②**难复现**（需要特定交错，测试可能跑一百万次才出现一次，甚至永远不出现）；③**有固定模式**（未同步的共享访问、锁顺序反转）——这三条正好是静态分析的强项：它能**同时看到**所有代码、能**枚举**所有交错、能**模式匹配**。虽然误报多（分析器不知道哪些锁保护哪些数据），但**漏报的代价更高**（竞态 bug 在生产环境表现为随机崩溃/数据损坏，极难调试），所以工程上接受「高误报 + 人工甄别」的取舍。这正是课件里 eBay 与 Microsoft 的经验。

**A3.** **冲突分析**（按时间顺序 `R1(x), W2(x), W1(y), R2(y)`）：
- `R1(x)` 与 `W2(x)`：不同事务、同一数据 `x`、`W2` 是写 → **冲突**，`T1 → T2`；
- `R1(x)` 与 `W1(y)`：不同数据 → 不冲突；
- `R1(x)` 与 `R2(y)`：不同数据 → 不冲突；
- `W2(x)` 与 `W1(y)`：不同数据 → 不冲突；
- `W2(x)` 与 `R2(y)`：同一事务 → 不冲突；
- `W1(y)` 与 `R2(y)`：不同事务、同一数据 `y`、`W1` 是写 → **冲突**，`T1 → T2`。
**冲突图**：只有一条边 `T1 → T2`，**无环** → **可串行化**，等价于串行顺序 `T1, T2`。**两阶段锁能阻止吗**：能，但这个历史本来就合法。需要注意的是：2PL 保证「任何 2PL 产生的历史都可串行化」，但反过来不成立——可串行化的历史**不一定**由 2PL 产生（例如这个历史里 `T1` 在 `W1(y)` 之前就释放了 `x` 的锁，违反 2PL 的「收缩阶段不能再加锁」……但因为它只需要 `T1 → T2` 的顺序，实际执行中 `T1` 若先锁 `x`、`y` 再释放，仍然合法）。**更严格的例子**：`R1(x), W2(x), W2(y), R1(y)` 会产生 `T1 → T2`（因 `x`）与 `T2 → T1`（因 `y`），形成环 → **不可串行化**；2PL 会阻止它，因为 `T1` 持有 `y` 的锁时 `T2` 无法写 `y`（或反之），必然有一方等待。

**A4.** `wait()` 必须用 `while` 包裹，因为**被唤醒不等于条件成立**。三种情况：
1. **虚假唤醒（spurious wakeup）**——JVM 允许 `wait()` 在没有 `notify()` 的情况下返回（这是 POSIX 允许的，Java 继承了这个行为）；
2. **`notifyAll()` 唤醒多个线程**——只有一个能继续，其他的必须重新检查条件；
3. **条件被其他线程改变**——线程 A 被唤醒、抢到锁之前，线程 B 可能已经把条件改回不成立。
**用 `if` 出错的场景**（经典的生产者-消费者）：

```java
// 错误：用 if
synchronized (lock) {
    if (queue.isEmpty()) lock.wait();
    Object item = queue.poll();   // ← 可能抛 NoSuchElementException
}
```

假设队列空，消费者 C1、C2 都 `wait()`。生产者放入**一个**元素并 `notifyAll()`。C1 和 C2 都被唤醒，C1 抢到锁、取走元素、释放锁；C2 随后抢到锁，**从 `wait()` 之后继续执行**——它不会重新检查 `queue.isEmpty()`，于是 `poll()` 在空队列上抛异常。**用 `while` 就对了**：

```java
synchronized (lock) {
    while (queue.isEmpty()) lock.wait();   // 醒来后重新检查
    Object item = queue.poll();
}
```

C2 醒来后发现队列又空了，**继续 `wait()`**——正确。**这条规则是并发编程的硬性要求**，不是风格建议。

**A5.** **不应该。** 扩展框架**不应该**需要修改框架源码，理由有三：
1. **复用价值归零**——如果你 fork 了框架源码，你就**脱离了上游**：框架的 bug 修复、性能改进、安全补丁你都拿不到。你实际上是在维护一个**私有分支**，成本极高。
2. **升级路径断裂**——下次框架发布新版本，你要么放弃自己的修改（功能丢失），要么手工合并（冲突地狱）。
3. **违反开闭原则**——框架应该「对扩展开放、对修改关闭」。
**如果必须修改源码，说明框架设计出了这些问题**：
- **扩展点不足**——框架没有为你的场景预留钩子（接口、抽象方法、配置项）。这是最常见的原因。
- **扩展点设计错误**——预留了钩子，但**粒度不对**（太粗：你必须重写整个流程；太细：你需要组合几十个钩子才能做一件小事）。
- **过度封装**——关键类被 `final`、关键方法被 `private`，无法继承或覆写。
- **缺少组合机制**——框架只支持继承扩展，不支持组合/委托，导致你必须改父类。
**正确的做法**：框架设计者应该**预判变化点**（这是「为变化而设计」的直接应用），为每个可能的变化提供扩展点；如果确实无法预判，至少提供**逃生舱（escape hatch）**——比如允许替换某个内部组件、允许注册自定义策略。**判断一个框架是否成熟，就看它是否让你「不用改源码就能做到想做的事」。**

</details>

## 12. 进一步学习

- 上一讲：[[15-214-27-Why-Objects-Typestate-DSLs]]——对象的价值、类型状态、权限、TSL。
- 相关讲次（按板块回查）：
  - OOP 与 Java：[[15-214-02-Objects-Encapsulation-Polymorphism]]、[[15-214-03-Encapsulation-and-Inheritance]]、[[15-214-04-Inheritance-Typechecking-Dispatch]]、[[15-214-06-Mutability-and-Java-Potpourri]]
  - 契约与异常：[[15-214-05-Object-Contracts-and-Exceptions]]
  - 设计模式与原则：[[15-214-07-Design-Patterns]]
  - 并发：[[15-214-17-Concurrency-Part1]]、[[15-214-18-Concurrency-Part2]]、[[15-214-19-Concurrency-Part3]]
  - 分布式：[[15-214-20-Distributed-Systems-Part1]]、[[15-214-21-Distributed-Systems-Part2]]、[[15-214-22-Distributed-Systems-Part3]]
  - 静态分析：[[15-214-23-Static-Analysis]]、[[15-214-24-Static-Analysis-for-Concurrency]]
  - 数据一致性：[[15-214-25-Data-Consistency]]
  - 对象历史：[[15-214-26-History-and-Future-of-Objects]]
- 课程导航：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]、[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]。
- 术语条目：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]。
- 延伸阅读：Bloch《Effective Java》（`equals`/`hashCode`/组合优于继承）、Parnas "On the Criteria To Be Used in Decomposing Systems into Modules"（1972）、Liskov "Data Abstraction and Hierarchy"（1987）、Gamma et al.《Design Patterns》（GoF）、Johnson "Frameworks = (Components + Patterns)"（1997）、Gabriel "Lisp: Good News, Bad News, How to Win Big"（1991，Worse is Better）、Herlihy & Shavit《The Art of Multiprocessor Programming》、Kleppmann《Designing Data-Intensive Applications》。
