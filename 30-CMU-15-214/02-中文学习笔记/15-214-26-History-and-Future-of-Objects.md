---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L26
topic: The History and Future of Objects - Simula, Smalltalk, and Software Design Wisdom
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 面向对象
  - 编程语言史
  - Smalltalk
  - Simula
  - 重构
---

# 第 26 讲 对象的历史与未来（History and Future of Objects）

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。

## 1. 本节学习目标

- 能说明 SIMULA I 的诞生动机（模拟/运筹学）以及它为什么需要「对象」这个抽象。
- 能说出 SIMULA 67 引入的四项关键创新：类前缀（class prefix）、虚过程（virtual procedures）、协程（coroutine）、垃圾回收。
- 能解释 Hoare 1966 年 record class 的意义，以及它与 SIMULA 67 类的关系。
- 能说明 Alan Kay 的 Dynabook 构想如何导向 Smalltalk 的「一切皆对象 + 消息发送」模型。
- 能列举 Smalltalk 对后世的具体影响（GUI、MVC、C++/Java/Ruby、设计模式、敏捷）。
- 能解释 DRY / Once and Only Once / Rule of Three 三条重构原则的关系。
- 能说明「Worse is Better」与 KISS / YAGNI 的设计哲学，并指出它们的适用边界。

## 2. 前置知识

- [[15-214-02-Objects-Encapsulation-Polymorphism]]：对象、封装、多态的基本概念。
- [[15-214-03-Encapsulation-and-Inheritance]]：继承与类层次。
- [[15-214-04-Inheritance-Typechecking-Dispatch]]：动态分派——本讲会说明它是从 SIMULA 67 的虚过程演化而来。
- [[15-214-07-Design-Patterns]]：设计模式——本讲会说明它的思想源头在 Smalltalk 社区。
- [[15-214-06-Mutability-and-Java-Potpourri]]：可变性与 `equals`/`hashCode` 契约。

## 3. 核心概念

- **SIMULA I（1961–1965）**：Dahl 与 Nygaard 为「离散事件模拟」设计的语言，第一个引入「对象」概念的语言。
- **Class（类）**：一组对象共有的属性与行为的模板。
- **Class Prefix（类前缀）**：SIMULA 67 的继承机制——`class Glyph` 作为 `class Char` 的前缀。
- **Virtual Procedure（虚过程）**：可在子类中重新定义、调用时按动态类型分派的方法——动态分派的鼻祖。
- **Coroutine（协程）**：可暂停与恢复的执行单元，用于模拟中「多个并发进程」的建模。
- **Record Class（记录类）**：Hoare 1966 提出的、把相关数据打包在一起并赋予操作的类型构造。
- **Dynabook（动态书）**：Alan Kay 1970 年代构想的「人人可用的便携式学习计算机」。
- **Message Sending（消息发送）**：Smalltalk 的核心机制——`3 + 4` 不是「调用函数」，而是「向 3 发送 `+` 消息，参数是 4」。
- **Reflection（反射）**：程序可以检查和修改自身的结构（Smalltalk 的 `class`、`methods` 等）。
- **MVC（Model-View-Controller）**：Smalltalk-80 引入的架构模式，把数据、显示、交互分离。
- **DRY（Don't Repeat Yourself）**：每一处知识在系统中都应有单一、明确的表示。
- **Once and Only Once**：同样的代码只应出现一次（XP 社区的表述）。
- **Rule of Three（三次法则）**：第三次重复时才抽象——两次重复还不足以判断模式。
- **Worse is Better（更差即更好）**：Gabriel 提出的设计哲学——简单性优先于正确性与完整性，往往赢得市场。
- **KISS（Keep It Simple, Stupid）**：优先选择简单的方案。
- **YAGNI（You Aren't Gonna Need It）**：不要实现你现在不需要的功能。

## 4. 通俗理解

**为什么会有「对象」？** 1960 年代，挪威的 Kristen Nygaard 和 Ole-Johan Dahl 要解决一个具体问题：**模拟一艘船的装卸作业**。船到港、排队、装货、卸货、离港——每一艘船都有自己的状态（载重、位置、剩余作业），而且它们同时存在、互相影响。

用当时的语言（ALGOL 60）写这个模拟非常痛苦：ALGOL 只有「过程（procedure）」和「数据」，没有「把数据和操作绑在一起」的机制。你只能开一大堆全局数组，用索引把「第 3 艘船的载重」和「第 3 艘船的位置」关联起来——**数据和代码是分离的**。

Nygaard 和 Dahl 的洞察是：**应该有一种语言构造，直接对应「船」这个实体**——它有数据（载重）、有行为（装货）、有身份（是这一艘而不是那一艘）、有生命周期（到港到离港）。这个构造就是**类（class）**。

**为什么叫「面向对象」？** 因为在模拟里，你确实是在描述「一堆对象在互相作用」。这个概念后来被推广到所有软件——因为**几乎所有软件都在建模某种「有状态、有行为、有身份的实体」**。

**Smalltalk 又做了什么？** Alan Kay 想要一台「动态书（Dynabook）」——儿童可以随身携带、用来学习和创造东西的计算机。他意识到：要让小孩能编程，语言必须**极其统一**。于是 Smalltalk 的设计原则是：**一切皆对象，一切操作都是「向对象发送消息」**。连 `3 + 4` 都是消息发送——`3` 收到 `+` 消息，参数是 `4`。连 `if` 都是消息发送——`true` 和 `false` 各自知道怎么处理「then/else」。

这种「极端统一」带来了惊人的表达力，也带来了性能问题——但它的思想（消息、反射、GUI、MVC）统治了后来的四十年。

## 5. 原理与推导

### 5.1 SIMULA I：从运筹学来的对象

课件第 3 页：

> **SIMULA I**
> - Developed by Kristen Nygaard and Ole-Johan Dahl
> - Norwegian Computing Center, 1961–1965
> - **Motivation: operations research / simulation**

**具体动机**（课件第 4 页）：模拟一个收费站的排队——船（或车）到达、排队等待、接受服务、离开。这类模拟（离散事件模拟，discrete-event simulation）的核心需求是：

1. **多个实体同时存在**，每个有自己的状态；
2. **实体之间会交互**（一艘船占用码头，其他船必须等）；
3. **实体的生命周期不同**（有的刚到，有的已经离开）；
4. **需要能「暂停」一个实体的执行**，等条件满足再恢复。

第 4 条是当时语言的**致命缺口**：ALGOL 的过程一旦调用就必须执行到返回，无法「中途暂停、稍后继续」。这就是**协程（coroutine）** 的动机。

**SIMULA I 的问题**（课件第 5–6 页）：

- 它只有「活动对象（activity）」的概念，没有「类」——每个模拟都得从头写一套；
- 没有继承，无法复用「一般船」的行为来定义「油轮」；
- 类型系统很弱，容易出错。

**这些缺陷直接催生了 SIMULA 67。**

### 5.2 Hoare 的 record class：一个关键的中间步骤

课件第 7–8 页：

> **Tony Hoare, 1966: record class**
> - A type that bundles together data and operations
> - Precursor to the class concept

Hoare 在 1966 年的论文中提出：应该有一种类型，把**相关的数据**和**作用于这些数据的操作**打包在一起，并且**对外隐藏内部表示**。

**为什么这一步重要？** 因为它把「封装（encapsulation）」从「一种编程习惯」变成了「语言机制」。在 Hoare 之前，你只能靠约定（「请不要直接访问 `ship.weight`，要用 `getWeight()`」）；在 Hoare 之后，语言可以**强制**这一点。

**这与 [[15-214-03-Encapsulation-and-Inheritance]] 的核心论点完全一致**：封装的价值不在于「藏起来」，而在于「可以自由修改内部实现而不影响使用者」——即**信息隐藏（information hiding）**。

### 5.3 SIMULA 67：四项创新

课件第 9 页：

> **SIMULA 67**
> - **Class prefix**: inheritance
> - **Virtual procedures**: dynamic dispatch
> - **Coroutines**: concurrent objects
> - **Garbage collection**: automatic memory management

**(1) Class prefix（类前缀）= 继承**

SIMULA 67 的语法是「前缀式」的：

```simula
class Glyph;
begin
    ...
end;

Glyph class Char;
begin
    ...
end;
```

读法：`Char` 是一个 `Glyph`，`Glyph` 是它的**前缀（prefix）**。这就是继承的原始形态——子类把父类作为「前缀」拼在自己前面。

**为什么叫「前缀」而不是「父类」？** 因为在 SIMULA 的语法里，前缀类的代码**字面上**被拼接在子类代码之前——它是一个**文本/结构上的**组合机制，而不只是一个类型关系。这解释了后来 C++ 的 `class Char : public Glyph` 语法（基类写在冒号后面）。

**(2) Virtual procedures（虚过程）= 动态分派**

如果 `Glyph` 定义了 `procedure draw; virtual;`，那么 `Char` 可以重新定义 `draw`。当你通过一个 `Glyph` 类型的引用调用 `draw` 时，实际执行的是**运行时对象的真实类型**的方法。

**这是「多态（polymorphism）」的语言级实现**，也是 [[15-214-04-Inheritance-Typechecking-Dispatch]] 里讲的所有内容的源头。在 SIMULA 67 之前，「根据对象的实际类型选择行为」只能靠手写的 `switch`/`if-else` 类型标签——这就是所谓的「类型码（type code）」反模式。

**(3) Coroutines（协程）= 并发对象**

在模拟里，一艘船「装货」可能需要等待码头空闲。协程允许一个执行流**暂停在某个点**、把控制权交出去、稍后从同一点**恢复**。这是「并发对象」的最早模型——比线程更轻量，因为它是**协作式**的（由程序自己决定何时切换）。

**这与 [[15-214-17-Concurrency-Part1]] 的「并发 vs 并行」区分有关**：协程提供的是「并发的**表达**」，而不是「并行的**执行**」——单核上也能跑协程。

**(4) Garbage collection（垃圾回收）**

对象有生命周期：创建、使用、销毁。手动管理（`malloc`/`free`）容易出错（泄漏、重复释放、悬垂指针）。SIMULA 67 引入了自动回收——**这是「对象」这个概念能大规模使用的前提**，因为对象之间的引用关系太复杂，手工追踪几乎不可能。

**这四项创新的组合**定义了「面向对象」的完整图景：**封装（Hoare 的贡献）+ 继承 + 多态 + 自动内存管理**。

### 5.4 SIMULA 67 的代码示例

课件第 10 页给出一个 `Glyph` / `Char` / `Line` 的例子：

```simula
class Glyph;
begin
    procedure draw; virtual;
    begin
    end;
end;

Glyph class Char (c);
character c;
begin
    procedure draw;
    begin
        outchar(c);
    end;
end;

Glyph class Line (from, to);
ref(Char) from, to;
begin
    procedure draw;
    begin
        from.draw;
        outtext("--");
        to.draw;
    end;
end;
```

**逐点解读**：

- `class Glyph;` 定义一个基类，含一个**虚过程** `draw`（空实现）；
- `Glyph class Char (c);` 声明 `Char` 以 `Glyph` 为前缀，构造参数是字符 `c`；
- `procedure draw;` 在子类里**重新定义**——这就是覆写（override）；
- `Glyph class Line (from, to);` 的字段是两个 `ref(Char)`——**组合（composition）**，`Line` 由两个 `Char` 组成；
- `Line.draw` 依次调用 `from.draw` 和 `to.draw`——**动态分派**：`from` 的实际类型可能是 `Char`，也可能是 `Char` 的子类。

**这段代码已经包含了现代 OO 的全部要素**：继承、覆写、动态分派、组合、构造参数。它是 1967 年的——比 Java 早 28 年。

### 5.5 Dynabook 与 Alan Kay 的愿景

课件第 11–12 页介绍 Alan Kay：

> **Alan Kay**
> - "The best way to predict the future is to invent it."
> - Dynabook: a portable, personal computer for children to learn and create

**Dynabook 的构想**（1970 年代初，Xerox PARC）：一台笔记本大小、电池供电、有图形显示和键盘的计算机，价格低到学校能买得起，让儿童可以用它**阅读、写作、绘画、编程、模拟**。

**这个构想为什么导向 Smalltalk？** 因为 Kay 认为：要让儿童能编程，语言必须：

- **视觉化**：能画图、能做动画（所以有 GUI）；
- **统一**：没有「数据」与「函数」的分裂，孩子只需要理解一个概念（对象）；
- **可探索**：孩子能「打开」任何东西看它怎么工作（所以有反射）；
- **可组合**：小的东西能拼成大的东西（所以有消息发送）。

课件第 12 页引用 Kay 的话：

> "I invented the term 'object-oriented', and I can tell you I did not have C++ in mind."

这句话常被用来批评 C++，但更准确的理解是：**Kay 的「对象」是「生物细胞式的、通过消息通信的独立单元」，而不是「带有 vtable 的类型实例」**。前者强调**自治与消息**，后者强调**类型与分派**。这个区别是理解 OO 历史的关键。

### 5.6 Smalltalk：纯面向对象

课件第 13 页：

> **Smalltalk**
> - **Everything is an object**
> - **Computation is message sending**
> - `3 + 4` sends the message `+` to the object `3` with argument `4`
> - **Reflection**: objects can inspect themselves
> - **Garbage collection**

**「一切皆对象」有多彻底？**

- 数字是对象（`3` 是 `SmallInteger` 的实例）；
- 类是对象（`Point class` 本身是一个对象，你可以给它发消息）；
- `nil` 是对象（`UndefinedObject` 的唯一实例）；
- 代码块是对象（`[ :x | x * 2 ]` 是一个 `BlockClosure`）；
- **`if` 是消息发送**：`(x > 0) ifTrue: [ ... ] ifFalse: [ ... ]`——`true` 和 `false` 各自实现了 `ifTrue:ifFalse:`。

**最后一条最能说明 Smalltalk 的哲学**：在 Java 里 `if` 是**语法结构**（编译器处理）；在 Smalltalk 里 `if` 是**方法调用**（运行时处理）。这意味着你甚至可以定义自己的「布尔类」——虽然实践中没人这么做，但**语言的统一性**是惊人的。

**消息发送的语法**：

```smalltalk
3 + 4                      " 二元消息：3 收到 + 消息 "
'hello' size               " 一元消息：字符串收到 size "
Transcript show: 'hi'      " 关键字消息：show: 的参数是 'hi' "
```

**反射（reflection）**：任何对象都能被问「你是什么类」「你有哪些方法」「你的第 3 个实例变量是什么」。这让**浏览器（browser）式的开发环境**成为可能——你可以边运行边查看边修改，这就是今天的 IDE 的雏形。

**垃圾回收**：Smalltalk 是最早把 GC 作为**必备特性**的主流语言之一（Lisp 更早，但 Smalltalk 把它带进了 OO 世界）。

### 5.7 Kay 的「递归于计算机的概念」

课件第 15 页引用 Kay：

> "The computer revolution hasn't happened yet."
> — 以及关于「recursion on the notion of computer」的论述

**这句话的意思**：Kay 认为，计算机的真正潜力不是「把纸上的东西搬到屏幕上」（那样只是**替代**旧媒介），而是**创造出纸笔做不到的新媒介**——就像印刷术不只是「更快的手抄」，而是催生了小说、报纸、科学共同体。

**「recursion on the notion of computer」**（在「计算机」这个概念上做递归）：用计算机来**设计更好的计算机**——用 Smalltalk 写 Smalltalk 的编译器、用 Dynabook 来设计下一代 Dynabook。这是「元（meta）」层面的思考，也是**反射**和**自举（bootstrapping）** 的哲学基础。

**Dan Ingalls 的引语**（课件第 16 页）也值得一提——他是 Smalltalk 的主要实现者，强调「简洁」与「可理解性」：一个好的系统应该小到一个人能完全理解。

### 5.8 Smalltalk 的影响

课件第 17 页列出影响清单：

| 领域 | 具体影响 |
|---|---|
| **GUI** | Macintosh 的图形界面直接源自 PARC 的 Smalltalk 环境（窗口、图标、鼠标、弹出菜单） |
| **架构模式** | **MVC**（Model-View-Controller）→ 后来的 Cocoa（Apple）、MFC（Microsoft）、AWT/Swing（Java） |
| **语言** | **C++** ← SIMULA（类、继承、虚函数）；**Objective-C / Java / Ruby** ← Smalltalk（消息、纯 OO、GC） |
| **方法论** | 设计模式（GoF 的书大量例子来自 Smalltalk）、重构（Fowler 早期用 Smalltalk）、敏捷开发（XP 诞生于 Smalltalk 社区） |

**这张表最值得玩味的是最后一行**：设计模式、重构、敏捷——这三个今天看来「与语言无关」的软件工程实践，**全部诞生于 Smalltalk 社区**。原因可能是：Smalltalk 的动态性让「改代码」变得极其便宜，所以社区自然发展出了「小步改进」的方法论。

### 5.9 重构：定义与样例

课件第 18–19 页引用 Martin Fowler 的定义：

> **Refactoring**: a change made to the internal structure of software to make it easier to understand and cheaper to modify without changing its observable behavior.

**关键词逐个拆解**：

- **internal structure**：只改内部，不改外部；
- **easier to understand / cheaper to modify**：目的是**可维护性**，不是性能或功能；
- **without changing observable behavior**：**行为不变**是硬约束——这是重构与「重写」的分界。

**课件列出的样例重构**（第 19 页）：

| 重构名称 | 做什么 |
|---|---|
| **Extract Method** | 把一段代码抽成一个方法 |
| **Inline Method** | 把一个方法的内容内联回调用处 |
| **Extract Class** | 把一个类的部分职责抽成新类 |
| **Move Method** | 把方法移到更合适的类 |
| **Rename** | 改名（变量、方法、类） |
| **Pull Up / Push Down** | 把成员在类层次中上移/下移 |
| **Replace Conditional with Polymorphism** | 用多态替换 `switch`/`if-else` 类型判断 |

**最后一条与 [[15-214-04-Inheritance-Typechecking-Dispatch]] 直接相关**：它是「从类型码到动态分派」的现代化版本，也正是 SIMULA 67 虚过程要解决的问题。

**工具支持**（第 20 页）：现代 IDE（Eclipse、IntelliJ）能**自动化**大部分重构——因为它们是**行为保持的机械变换**，只要语法树分析正确，就可以安全执行。这与 [[15-214-23-Static-Analysis]] 的 AST 分析是同一套技术。

### 5.10 敏捷：重构的流程化

课件第 20 页把重构与敏捷联系起来：

- 重构让「持续改进设计」成为可能；
- 敏捷（特别是 XP）把「小步重构 + 持续测试」作为核心实践；
- **测试是重构的安全网**——没有测试，你无法确认「行为没变」。

**这与 [[15-214-23-Static-Analysis]] 的可靠/完备框架形成一个有趣的对照**：测试不完备（只能覆盖执行的路径），但对**行为保持**这个特定目标来说，它提供了足够的信心。而重构的「机械性」又让它适合工具自动化——**人的判断 + 机器的执行**，正是本课程反复强调的分工。

### 5.11 DRY / Once and Only Once / Rule of Three

课件第 22 页：

> **DRY: Don't Repeat Yourself**
> - Every piece of knowledge must have a single, unambiguous, authoritative representation within a system.
>
> **Once and Only Once**
> - The same code should appear only once.
>
> **Rule of Three**
> - Refactor on the third duplication, not the second.

**三者的关系**：

- **DRY** 是最抽象的表述——它说的是**知识**，不是**代码**。两段看起来不同的代码可能表达同一个知识（例如「税率计算」出现在两个地方，写法不同）；两段看起来相同的代码可能表达不同的知识（例如两个 `for (int i = 0; ...)` 循环只是碰巧长得像）。**盲目消除代码重复会破坏 DRY**。
- **Once and Only Once** 是 DRY 在**代码层面**的表述，来自 XP 社区，更具体也更激进。
- **Rule of Three** 是对前两者的**约束/纠偏**：不要看到两处重复就抽象，等第三处出现。理由是：**两次重复可能只是巧合**，过早抽象会引入错误的抽象边界，而错误抽象的代价比重复更高。

**Rule of Three 背后的经济学**：

- 抽象的成本：多一层间接、多一个需要维护的概念、可能绑错维度；
- 重复的成本：改一处忘另一处（这就是「霰弹式修改 shotgun surgery」坏味道）；
- 两次时：抽象的期望收益 < 成本（因为「第三处会不会出现」还不确定）；
- 三次时：模式已足够清晰，抽象收益 > 成本。

**这与 [[15-214-07-Design-Patterns]] 的「模式是被发现的，不是被发明的」是同一个道理**——模式（和抽象）应该在**第三次**出现时才被命名。

### 5.12 Worse is Better

课件第 23–24 页介绍 Richard Gabriel 的著名文章 "Lisp: Good News, Bad News, How to Win Big"（1991）中的 **"The Rise of Worse is Better"**：

> **The MIT/Stanford style ("the right thing")**:
> - Correctness first
> - Consistency first
> - Completeness first
> - **Simplicity of implementation is NOT the priority**
>
> **The New Jersey style ("worse is better")**:
> - **Simplicity** (of implementation) is the highest priority
> - Correctness: simple is better than correct
> - Consistency: simple is better than consistent
> - Completeness: simple is better than complete

**Gabriel 的核心论点**：在软件的历史上，**「更差但更简单」的方案往往战胜「更好但更复杂」的方案**。他举的例子是 C/Unix（新泽西风格）战胜 Lisp/MIT 风格。

**为什么？** 因为简单的东西：

- 更容易移植（Unix 能跑在任何机器上）；
- 更容易被更多人实现（C 编译器到处都是）；
- 更容易在 80% 的场景下「够用」；
- 一旦占据了生态位，就难以被取代（即使后来有更好的方案）。

**这与「对象的历史」有什么关系？** 关系极大：**C++ 就是「Worse is Better」在 OO 领域的胜利**。它不是最纯粹的 OO（Kay 说「我没想过 C++」），它有很多历史包袱（C 兼容、手动内存管理、复杂的模板），但它**够简单、够快、够早**，所以成了主流。而 Smalltalk 更纯粹、更优雅，却因为性能与生态输掉了市场。

**课件的态度**：不是要你「选择 Worse」，而是要你**意识到这个权衡存在**。很多技术决策的胜负不由「技术优劣」决定，而由「生态与复杂度」决定。

### 5.13 KISS 与 YAGNI

课件第 25 页：

> **KISS: Keep It Simple, Stupid**
> - Simplicity should be a key goal; unnecessary complexity should be avoided
>
> **YAGNI: You Aren't Gonna Need It**
> - Don't implement features you don't need right now

**KISS 是关于「怎么实现」**：用最简单的方式达成目标。它反对「为了炫技而用复杂方案」，也反对「过度设计」。

**YAGNI 是关于「做什么」**：不要实现现在不需要的功能。它反对「预留扩展点」「为了将来可能的复用而抽象」。

**YAGNI 与「设计为了变化（design for change）」的矛盾**：这是本课程里一个真实的张力。[[15-214-07-Design-Patterns]] 强调「为变化而设计」（用接口、用策略模式预留扩展点）；YAGNI 说「不要为想象中的变化写代码」。

**如何调和？** 课件（以及 Fowler、Beck 的实践）给出的答案是：

- **为「已知的、具体的变化」设计**（例如「我们下个季度要支持第二种支付方式」——这是需求，不是想象）；
- **不要为「可能的变化」设计**（例如「也许将来会支持区块链支付」——这是猜测）；
- **让「添加变化」变得便宜**（通过信息隐藏、低耦合、高内聚），而不是**预先实现**变化。

这正是 [[15-214-07-Design-Patterns]] 里「封装变化点（encapsulate what varies）」的正确理解：**封装的是「变化这个事实」，不是「每一种可能的变化」**。

### 5.14 本讲的历史线索

把整讲串成一条线：

```
1961-65  SIMULA I        模拟需求 → 对象、协程
   ↓
1966     Hoare record class  数据+操作打包 → 封装
   ↓
1967     SIMULA 67       类前缀（继承）+ 虚过程（多态）+ GC
   ↓
1970s    Dynabook        儿童教育 → 统一、可视、可探索
   ↓
1972-80  Smalltalk       一切皆对象 + 消息发送 + 反射 + MVC
   ↓
1980s    C++ / ObjC      工业化的 OO（Worse is Better）
   ↓
1990s    Java / Ruby     主流化 + GC 普及
   ↓
1990s    设计模式 / 重构 / 敏捷   从 Smalltalk 社区长出的方法论
   ↓
2000s+   Worse is Better 的持续胜利（简单方案占领生态）
```

**这条线索揭示的核心规律**：**语言特性来自真实需求**。对象来自模拟，协程来自「暂停」，GC 来自「引用太复杂」，消息来自「儿童要统一」，MVC 来自「界面要改而数据不变」。没有一个是「为了优雅而优雅」——它们都是被具体问题逼出来的。

## 6. 代码示例

### 6.1 官方课程代码

**第 10 页：SIMULA 67 的 Glyph / Char / Line**

```simula
class Glyph;
begin
    procedure draw; virtual;
    begin
    end;
end;

Glyph class Char (c);
character c;
begin
    procedure draw;
    begin
        outchar(c);
    end;
end;

Glyph class Line (from, to);
ref(Char) from, to;
begin
    procedure draw;
    begin
        from.draw;
        outtext("--");
        to.draw;
    end;
end;
```

**第 13 页：Smalltalk 的消息发送**

```smalltalk
3 + 4
```

课件对它的解读：这不是「把 3 和 4 相加」，而是**「向对象 3 发送 `+` 消息，参数是 4」**。

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：把 SIMULA 67 的 Glyph/Char/Line 翻译成 Java，观察哪些概念保留了下来。**

```java
import java.util.*;

/** 对应 SIMULA 的 class Glyph */
abstract class Glyph {
    /** 对应 SIMULA 的 virtual procedure draw */
    public abstract void draw(StringBuilder out);
}

/** 对应 Glyph class Char (c) —— 类前缀 = 继承 */
class Char extends Glyph {
    private final char c;
    Char(char c) { this.c = c; }

    @Override
    public void draw(StringBuilder out) { out.append(c); }
}

/** 对应 Glyph class Line (from, to) —— 组合两个 Char */
class Line extends Glyph {
    private final Char from, to;
    Line(Char from, Char to) { this.from = from; this.to = to; }

    @Override
    public void draw(StringBuilder out) {
        from.draw(out);                 // 动态分派
        out.append("--");
        to.draw(out);
    }
}

public class SimulaGlyphDemo {
    public static void main(String[] args) {
        List<Glyph> glyphs = new ArrayList<>();
        glyphs.add(new Char('A'));
        glyphs.add(new Line(new Char('B'), new Char('C')));

        StringBuilder out = new StringBuilder();
        for (Glyph g : glyphs) {
            g.draw(out);                    // 多态：不需要 instanceof
            out.append('\n');
        }
        System.out.print(out);
    }
}
```

输出：

```
A
B--C
```

**对照表**：

| SIMULA 67 | Java | 说明 |
|---|---|---|
| `class Glyph;` | `abstract class Glyph` | 基类 |
| `procedure draw; virtual;` | `public abstract void draw()` | 虚过程 / 抽象方法 |
| `Glyph class Char (c);` | `class Char extends Glyph` | 类前缀 / 继承 |
| `procedure draw;`（子类重定义） | `@Override public void draw()` | 覆写 |
| `ref(Char) from` | `private final Char from` | 引用类型字段 |
| `from.draw;` | `from.draw(out)` | 动态分派 |
| （自动 GC） | JVM GC | 垃圾回收 |

**28 年过去了，核心概念一字未变**。变的只是语法与类型系统的严格程度（Java 要求显式 `abstract`、显式 `@Override`，SIMULA 不需要）。

**示例 B：用 Java 模拟 Smalltalk 的「消息发送」—— `if` 也是消息。**

```java
import java.util.function.Supplier;

/** 对应 Smalltalk 的 Boolean：true 和 false 各自知道怎么处理 ifTrue:ifFalse: */
interface SBool {
    <T> T ifTrueIfFalse(Supplier<T> thenBranch, Supplier<T> elseBranch);
}

class STrue implements SBool {
    @Override
    public <T> T ifTrueIfFalse(Supplier<T> t, Supplier<T> f) { return t.get(); }
}

class SFalse implements SBool {
    @Override
    public <T> T ifTrueIfFalse(Supplier<T> t, Supplier<T> f) { return f.get(); }
}

public class SmalltalkStyleIf {
    static SBool greater(int a, int b) {
        return a > b ? new STrue() : new SFalse();
    }

    public static void main(String[] args) {
        // 等价于 Smalltalk: (3 > 4) ifTrue: [...] ifFalse: [...]
        String r = greater(3, 4).ifTrueIfFalse(
            () -> "3 > 4",
            () -> "3 <= 4"
        );
        System.out.println(r);      // 3 <= 4
    }
}
```

**这个例子不是要你写这样的 Java**（它有额外开销、可读性差），而是为了让你**体会 Smalltalk 的统一性**：在 Smalltalk 里，`if` 不是语法，是**对象的方法**。这种「用对象表达一切」的思路，后来演化为**策略模式**（用对象替代条件分支）——参见 [[15-214-07-Design-Patterns]]。

**示例 C：用「Rule of Three」判断何时该抽象。**

```java
/** 第一次出现：直接写 */
class Report1 {
    void print() {
        System.out.println("=== 报告 ===");
        System.out.println("内容 A");
        System.out.println("=== 结束 ===");
    }
}

/** 第二次出现：看起来重复了，但先别抽象（Rule of Three） */
class Report2 {
    void print() {
        System.out.println("=== 报告 ===");
        System.out.println("内容 B");
        System.out.println("=== 结束 ===");
    }
}

/** 第三次出现：模式确认，抽象成模板方法 */
abstract class Report {
    final void print() {
        header();
        body();
        footer();
    }
    void header() { System.out.println("=== 报告 ==="); }
    abstract void body();
    void footer() { System.out.println("=== 结束 ==="); }
}

class ReportA extends Report { void body() { System.out.println("内容 A"); } }
class ReportB extends Report { void body() { System.out.println("内容 B"); } }
class ReportC extends Report { void body() { System.out.println("内容 C"); } }
```

**为什么不在第二次就抽象？** 因为两次重复可能只是**巧合**：也许 `Report2` 的标题格式明天就要改（「报告」→「分析」），而 `Report1` 不变。过早抽象会把两个**独立变化**的东西绑在一起，反而增加维护成本。等到第三次，你才看清「什么是稳定的（头尾）、什么是变化的（内容）」——**这正是 Template Method 模式的本质**（参见 [[15-214-07-Design-Patterns]]）。

**示例 D：DRY 不等于「消除所有重复」。**

```java
import java.time.LocalDate;

/** 反例：为了 DRY 把两个「长得像但语义不同」的东西合并 */
class BadDesign {
    /** 税率计算 —— 税率会变 */
    double tax(double amount) { return amount * 0.08; }

    /** 折扣计算 —— 折扣规则会变，且与税率无关 */
    double discount(double amount) { return amount * 0.08; }   // 碰巧也是 8%
}

/** 正例：分开，因为它们变化的原因不同（单一职责原则） */
class GoodDesign {
    double tax(double amount)   { return amount * taxRate(); }
    double discount(double amount) { return amount * discountRate(); }

    private double taxRate()      { return 0.08; }
    private double discountRate() { return 0.08; }
}
```

**要点**：`BadDesign` 里两个方法代码**字面上重复**，但合并它们会违反 DRY——因为「税率」和「折扣率」是**两个不同的知识**，它们只是**此刻恰好相等**。DRY 说的是「每一条**知识**只有一个权威表示」，不是「每一段**代码**只出现一次」。判断标准是：**它们会因为同一个原因改变吗？** 如果不会，就不该合并。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| SIMULA 67 的 class prefix | Java 的 `extends` | 前者是**文本/结构上的前缀拼接**；后者是纯粹的**类型关系**（语法上也是 `extends`） |
| 虚过程（virtual procedure） | Java 的 `abstract` 方法 | 前者可以有空实现且默认可覆写；后者必须被子类实现（除非有默认实现，即 Java 8 的 default method） |
| 协程（coroutine） | 线程（thread） | 前者**协作式**切换（自己让出）；后者**抢占式**（由调度器打断），需要锁 |
| Smalltalk 的「消息」 | Java 的「方法调用」 | 前者在运行时查找（可 `doesNotUnderstand:` 兜底）；后者在编译期绑定（除虚方法外），找不到就编译错误 |
| Smalltalk 的「一切皆对象」 | Java 的「基本类型 + 对象」 | 前者 `3` 是对象；后者 `int` 是原始类型，`Integer` 才是对象（有装箱开销） |
| 重构（refactoring） | 重写（rewrite） | 前者**行为不变**，小步、可测试、可自动化；后者可以改变行为 |
| DRY | 「消除所有重复代码」 | 前者针对**知识**的单一表示；后者是机械的文本去重，常常破坏 DRY |
| Rule of Three | 「看到重复就抽象」 | 前者要求**第三次**才抽象；后者是过早抽象（premature abstraction） |
| Worse is Better | 「质量不重要」 | 前者说**简单性优先于正确性/完整性**（是一种权衡）；后者是误解 |
| YAGNI | 「不做设计」 | 前者反对**为想象中的需求**写代码；后者是放弃设计，两者不同 |
| KISS | YAGNI | 前者关于**怎么实现**（选简单方案）；后者关于**做什么**（不做不需要的） |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-214/slides/27-history-oo.pdf`
- **总页数**：26 页
- **本节重点页码**：
  - 第 3 页：SIMULA I（Nygaard & Dahl，挪威计算中心，1961–1965，运筹学/模拟动机）
  - 第 4 页：收费站队列的模拟动机
  - 第 5–6 页：SIMULA I 的问题
  - 第 7–8 页：Hoare 1966 的 record class
  - 第 9 页：SIMULA 67 的四项创新（类前缀、虚过程、协程、GC）
  - 第 10 页：SIMULA 67 的 Glyph / Char / Line 代码
  - 第 11–12 页：Dynabook 与 Alan Kay 的引语
  - 第 13 页：Smalltalk（一切皆对象、消息发送、`3 + 4`、反射、GC）
  - 第 15 页：Kay 关于「在计算机概念上递归」的论述
  - 第 16 页：Dan Ingalls 的引语
  - 第 17 页：Smalltalk 的影响清单（GUI、MVC、语言、方法论）
  - 第 18–19 页：重构的定义（Fowler）与样例重构清单
  - 第 20 页：工具支持与敏捷
  - 第 22 页：DRY / Once and Only Once / Rule of Three
  - 第 23–24 页：Worse is Better（Gabriel）
  - 第 25 页：KISS 与 YAGNI
- **原始链接**：https://www.cs.cmu.edu/~aldrich/214/slides/27-history-oo.pdf

## 9. 对应视频

未找到官方公开录像。

## 10. 本节复习

- 对象来自**模拟**：SIMULA I（1961–65）为离散事件模拟而生，需要「多实体 + 状态 + 生命周期 + 可暂停」。
- Hoare 1966 的 record class 把「数据 + 操作 + 隐藏内部」变成语言机制。
- SIMULA 67 四项创新：**类前缀（继承）、虚过程（动态分派）、协程（并发对象）、垃圾回收**。
- Alan Kay 的 Dynabook 愿景要求语言「统一、可视、可探索」→ Smalltalk 的「一切皆对象 + 消息发送 + 反射」。
- Smalltalk 的影响：GUI、MVC、C++/ObjC/Java/Ruby、设计模式、重构、敏捷。
- 重构 = 改变内部结构、**不改变可观察行为**、目的是可理解与可修改。
- DRY 针对**知识**而非代码；Once and Only Once 是代码层表述；Rule of Three 是纠偏（第三次才抽象）。
- Worse is Better：简单性优先于正确性/完整性，常赢得市场（C/Unix、C++）。
- KISS 关于「怎么实现」，YAGNI 关于「做什么」；YAGNI 与「为变化设计」的调和方式是「为已知变化设计，让添加变化变便宜」。

## 11. 自我检查

**Q1.** SIMULA I 为什么需要「协程」？用收费站模拟的例子说明。如果没有协程，用当时的 ALGOL 60 该怎么写？会有什么问题？

**Q2.** Alan Kay 说「我发明了『面向对象』这个词，但我当时想的不是 C++」。请解释他所说的「对象」与 C++ 的「对象」在关注点上的差异。

**Q3.** 下面两段代码「重复」了。按照 DRY 与 Rule of Three，你该不该抽象？请说明判断依据。

```java
double shippingCost(double weight) { return weight * 0.5 + 10; }
double packagingCost(double weight) { return weight * 0.5 + 10; }
```

**Q4.** 请解释「Worse is Better」为什么能解释 C++ 战胜 Smalltalk 成为主流 OO 语言。这个规律是否意味着「永远应该选更差的方案」？

**Q5.** YAGNI 说「不要实现现在不需要的功能」，但设计模式说「要为变化而设计」。这两者矛盾吗？请给出一个具体的调和方案。

<details>
<summary>参考答案</summary>

**A1.** 收费站模拟里，一艘船「装货」到一半时可能发现码头被占用，必须**停下来等**；等码头空出来，它要从**刚才停下的地方继续**装。ALGOL 60 的过程**没有「暂停/恢复」能力**——一旦调用就必须执行到 `return`。当时的变通做法是：把「装货」拆成很多小步骤，用一个**全局状态机**记录每艘船进行到哪一步，主循环里反复扫描所有船、推进一小步。问题有三：① **代码极其难写难读**——一个连贯的业务流程被拆成几十个 `case` 分支；② **状态必须全部放到全局变量**里（因为过程调用结束后局部变量就没了），破坏了封装；③ **无法表达「局部状态」**——每艘船的中间变量都得手动管理。协程把「暂停点」变成语言机制：局部变量保存在协程自己的栈上，`resume` 时自动恢复——**这就是后来「对象有状态」的直接来源**。

**A2.** Kay 的「对象」关注的是**自治的单元通过消息通信**：每个对象像一个生物细胞或一台小计算机，有自己的内部状态，只能通过**发送消息**与外界交互；接收者**自己决定**如何响应（甚至可以「不理解」这条消息而触发 `doesNotUnderstand:`）。核心词是**消息、自治、晚绑定、可组合**。C++ 的「对象」关注的是**类型与分派**：对象是某个类的实例，方法调用在编译期确定签名、在运行期通过 vtable 分派；核心词是**类、继承、静态类型、效率**。差异体现在：① Kay 反对「继承是 OO 的核心」（他认为继承只是实现复用的手段，甚至不必要）；② Kay 的消息是**动态**的（可以发送对象不认识的消息），C++ 的调用是**静态检查**的（编译错误）；③ Kay 关心「儿童能否理解」，C++ 关心「能否高效地写大型系统」。所以他那句话不是说 C++ 不好，而是说**C++ 解决的问题不是他当初想的问题**。

**A3.** **不该抽象**（至少现在不该）。判断依据有三层：① **DRY 的判据是「知识是否单一」**——`shippingCost`（运费）和 `packagingCost`（包装费）是**两条不同的业务知识**，它们只是**此刻恰好**公式相同。运费可能因为油价上涨而调整，包装费可能因为材料变化而调整——**变化的原因不同**，合并会让一次变化意外影响另一处（这就是「霰弹式修改」的反面：**错误的耦合**）。② **Rule of Three** 说第三次才抽象——现在只有两次，模式还不明确。③ **可读性**：`shippingCost` 里出现 `weight * 0.5 + 10` 是一眼能懂的；如果写成 `cost(weight, SHIPPING_RATE, SHIPPING_BASE)`，读者还得跳去看常量。**正确的做法**：先保持两份独立实现，等到第三处出现（比如 `insuranceCost` 也是同样公式）时，再判断「它们是不是真的共享一个概念」——如果是，抽成一个 `ShippingCalculator`；如果不是，继续分开。

**A4.** **能解释的原因**：① **可移植性与生态**——C++ 兼容 C，能直接复用海量现有代码与工具链；Smalltalk 需要自己的虚拟机与镜像（image），迁移成本高。② **性能**——C++ 编译成原生代码，Smalltalk 是解释/动态编译，1990 年代差距巨大。③ **简单性（实现层面）**——C++ 的「类 = 结构体 + 函数表」易于在现有编译器上实现；Smalltalk 的「一切皆对象 + 反射 + 动态消息」需要全新的运行时。④ **渐进采用**——团队可以先用 C++ 写一小部分，其余继续用 C；Smalltalk 要求整个系统都在镜像里。按 Gabriel 的框架，C++ 是「新泽西风格」（简单实现优先），Smalltalk 是「MIT 风格」（正确与完整优先）——历史证明前者更容易扩散。**但这个规律不意味着「永远选更差的」**：① Gabriel 的文章本身是**警示**，不是教条——他指出这个现象是为了让「做正确的事」的人理解为什么自己会输，而不是劝人放弃正确；② 「更差」是相对**某个评价维度**的——C++ 在「实现简单、性能、生态」上并不差，只是在「概念纯粹性」上差；③ 当**生态位已经饱和**或**切换成本极高**时，更好的方案可以赢（例如 Python 取代 Perl、Git 取代 SVN）；④ 现代实践更强调「足够好 + 可演进」，而不是「一次做对」或「一次做简单」。

**A5.** **表面矛盾，实质不矛盾**——因为两者针对的是**不同类型的变化**。调和方案：
- **区分「已知变化」与「想象变化」**：如果需求方明确说「下季度要接第二种支付渠道」，那就是**已知变化**，应该用 Strategy 模式预留扩展点（接口 + 注入）；如果只是「也许将来会有别的支付方式」，那是**想象变化**，按 YAGNI 不做。
- **让「添加变化」变便宜，而不是「预先实现」变化**：通过信息隐藏、低耦合、高内聚，把「未来加一个分支」的成本降到「写一个新类 + 改一行配置」；而不是现在就写五个空实现。
- **用 Rule of Three 作为时间判据**：第一次直接写，第二次复制，第三次抽象——这时候的抽象基于**真实观察到的**变化，而不是猜测。
- **具体例子**：日志输出。如果现在只需要输出到控制台，就写 `System.out.println`（YAGNI）；但如果你**已经知道**测试时需要捕获日志，那就定义一个 `Logger` 接口（已知变化）。判断的关键不是「将来会不会变」（一定会变），而是「**我现在是否知道它会怎么变**」。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-25-Data-Consistency]]——事务、2PC 与 CAP。
- 下一讲：[[15-214-27-Why-Objects-Typestate-DSLs]]——为什么对象有价值、类型状态、以及 DSL 与 Wyvern。
- 相关讲次：[[15-214-02-Objects-Encapsulation-Polymorphism]]（对象基础）、[[15-214-04-Inheritance-Typechecking-Dispatch]]（虚过程与动态分派）、[[15-214-07-Design-Patterns]]（模式与「为变化设计」）、[[15-214-23-Static-Analysis]]（重构的工具化基础）。
- 课程导航：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]、[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]。
- 术语条目：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（DSL 领域特定语言、Typestate 类型状态）。
- 延伸阅读：Nygaard & Dahl "SIMULA — An ALGOL-Based Simulation Language"（CACM 1966）、Hoare "Record Handling"（1966）、Kay & Goldberg "Personal Dynamic Media"（Computer 1977）、Goldberg & Robson《Smalltalk-80: The Language and its Implementation》、Fowler《Refactoring》（1999）、Gabriel "Lisp: Good News, Bad News, How to Win Big"（1991）、Hunt & Thomas《The Pragmatic Programmer》（DRY 的出处）。
