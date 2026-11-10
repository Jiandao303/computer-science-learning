---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L16
topic: Frameworks
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 框架
  - 库
  - 好莱坞法则
  - 白盒框架
  - 黑盒框架
  - 插件
  - 扩展点
  - 回调
  - 生命周期方法
  - 反射
  - Mediator
  - Visitor
  - instanceof
  - MapReduce
  - Eclipse
---

# 第 16 讲 框架（Frameworks）

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。本讲对应 `14-frameworks.pdf`（65 页）。按 2013 年课表，**10 月 22 日**（主题「Formal Analysis, Continued ; Frameworks」）与 **10 月 24 日**（主题「Design case study: Frameworks, continued」）两次课都使用这份 65 页讲义，因此本笔记把两天的内容合并整理。10 月 24 日之后课表还有 10 月 29 日「Concurrency, part 1」等多次课，本讲**不是**学期最后一次新内容课。注意文件名以 `14-` 开头，但按课表顺序这是第 16 讲（`14_Collections.pdf` 才是第 14 讲）——课件编号与讲次存在错位。
>
> 讲义前 12 页是**上一讲遗留的两个「每日设计建议」**（Scrabble 的 Mediator 问题、`instanceof` 为何有害），第 13 页才是本讲正式封面。笔记按讲义顺序组织，把前 12 页作为「引子」处理。

## 1. 本节学习目标

- 能用**控制权归属**区分 **库（library）** 与 **框架（framework）**，并说明好莱坞法则（Hollywood principle）的含义。
- 能准确定义 API、Client、Plugin、Extension point、Protocol、Callback、Lifecycle method 七个术语，并说明它们之间的关系。
- 能说明「用一个 API」为什么像「用半个设计模式」，以及为什么插件树与框架间协作很常见。
- 能用 MapReduce 说明框架如何**内化质量属性**（并行化、容错、可扩展），以及客户端为此付出的**约束代价**。
- 能对比**白盒框架**（子类化 / Template Method）与**黑盒框架**（实现插件接口 / Strategy、Observer），并说明各自的「需要理解什么」。
- 能说明**框架设计的黄金法则**：扩展框架**不应**修改框架源码；并列举三种实现方式（客户端写 `main`、框架写 `main` + 命令行参数、框架读配置文件）。
- 能用 Java 反射（`Class.forName` + `newInstance`）实现插件加载，并说明这种做法的代价。
- 能说明 **Eclipse 插件机制**（Manifest + `plugin.xml` + 扩展点）如何实现「不修改框架而扩展」。
- 能说明框架设计的核心决策是**区分共性与可变部分**（hot spots vs cold spots），以及「扩展点太少/太多」的双向风险。
- 能解释「**最大化复用会最小化使用**」（Szyperski）这一使用 vs 复用困境。
- 能说明 `instanceof` 的三个问题，以及两种替代方案（多态分派、Visitor 模式）的适用条件。

## 2. 前置知识

- [[15-214-07-Design-Patterns]]：Mediator、Visitor、Strategy、Observer、Template Method、Factory——本讲把这些模式放进「框架」这个更大的语境。
- [[15-214-09-Design-Patterns-Continued]]：Template Method 与 Decorator 的细节，Java I/O 作为「库」的例子。
- [[15-214-11-Design-Principles-GRASP]]：Low Coupling / High Cohesion / Protected Variations / Indirection——框架设计是这些原则的集中体现。
- [[15-214-12-DSM-and-GUIs]]：GUI 的事件驱动与「Don't call us, we'll call you」——本讲把这句话提升为框架的定义性特征。
- [[15-214-13-GUIs-Continued]]：Swing 线程架构、`SwingWorker`——本讲第 45–51 页回到 Swing，说明它其实是**库 + 框架的混合体**。
- [[15-214-08-Specification-and-Testing]]：JUnit——本讲第 44 页把它作为「用注解做插件机制」的例子。

## 3. 核心概念

- **库（Library）**：一组提供可复用功能的类与方法；**客户端控制**系统结构与控制流；库执行一个函数并返回数据。
- **框架（Framework）**：可被定制成应用的可复用**骨架代码**；**框架控制**程序结构与控制流；框架**回调**客户端代码。
- **好莱坞法则（Hollywood Principle）**：「Don't call us; we'll call you.」（不要调用我们，我们会调用你）
- **API（Application Programming Interface）**：库或框架的接口。
- **客户端（Client）**：使用 API 的代码。
- **插件（Plugin）**：定制框架的客户端代码。
- **扩展点（Extension point）**：框架支持用插件扩展的位置。
- **协议（Protocol）**：API 与客户端之间**预期的交互序列**。
- **回调（Callback）**：框架为访问定制功能而调用的插件方法。
- **生命周期方法（Lifecycle method）**：按协议与插件状态、在特定序列中被调用的回调方法（如 `init`、`destroy`）。
- **白盒框架（White-box framework）**：通过**子类化与覆写**扩展（Template Method）。
- **黑盒框架（Black-box framework）**：通过**实现插件接口**扩展（Strategy、Observer）。
- **反射（Reflection）**：运行时按名字加载类并实例化的能力（`Class.forName`、`newInstance`）。
- **热 spot / 冷 spot（hot spot / cold spot）**：框架中**可变**的部分（应提供扩展点）与**不变**的部分（应固化在框架里）。
- **领域工程（Domain engineering）**：在设计框架前，系统研究该领域可能的需求与扩展。
- **作用域（Scoping）**：有意识地决定框架支持什么、不支持什么。

## 4. 通俗理解

**这一讲的核心问题只有一个：什么叫「复用别人的代码」，以及它有几种截然不同的形态？**

大多数人说的「复用」是指**调用别人的函数**——`Math.sqrt(x)`、`list.sort()`、`ImageIO.read(file)`。这叫**库**。你写 `main`，你决定什么时候调、按什么顺序调、拿到结果后干什么。**控制权在你手里。**

但还有另一种复用：**别人写好骨架，你只填几个空**。比如写一个 Swing 应用——`main` 里只有 `new MyFrame().setVisible(true)`，然后就**结束了**。之后是 Swing 的事件循环在调用**你的** `actionPerformed`。**控制权在框架手里。**

课件第 16 页用一个很生动的对话表达这个区别：

> **Framework**: Reusable skeleton code that can be customized into an application
> - **Framework controls**
>   - **Program structure**
>   - **Control flow**
> - **Framework calls back into client code**
>   - **The Hollywood principle: "Don't call us; we'll call you."**
>
> （图上标注：`Swing`、`Eclipse`、`Spring`、`Applet`；旁白气泡：
> 「**But this is an application!**」「**Hey, wasn't this a library?**」）

那两个旁白气泡是这一讲最有趣的地方。它们在说：

- **「But this is an application!」**——`Applet` 看起来像一个应用（它有界面、有生命周期），但它其实是一个**框架**：浏览器调用它的 `init`/`start`/`paint`/`stop`/`destroy`。
- **「Hey, wasn't this a library?」**——`Swing` 在上一讲（第 12–13 讲）被当作**库**使用（`new JPanel()`、`panel.add(...)`），但它的**事件机制**是框架（框架调用你的 listener）。所以 Swing **既是库又是框架**。

**这个「既是……又是……」正是本讲要讲清楚的东西**：库与框架不是两个互斥的盒子，而是**控制权光谱上的两个位置**。同一个软件可以在某些方面是库、在另一些方面是框架。

**为什么要区分？** 因为**学习成本与设计约束完全不同**：

| | 库 | 框架 |
|---|---|---|
| 你要学什么 | 每个方法的**契约** | 整个**协议**（何时被调用、调用顺序、状态约束） |
| 谁的结构 | 你的结构 | **框架的结构**（你嵌进去） |
| 出问题在哪 | 你的调用 | 你的**回调**（而你不知道它何时被调） |
| 复用的是什么 | **实现** | **设计与实现**（架构） |

第 54 页引用 Erich Gamma 的定义把这个区别说得最清楚：

> **OO Frameworks**
> - A customizable set of cooperating classes that defines a **reusable solution** for a given problem
> - defines key abstractions and their interfaces
>   - object interactions
>   - invariants
>   - **flow of control**
>   - **override and be called**
>   - defaults
> - Reuse
>   - **reuse of design and code**
>   - **reuse of a macro architecture**
> - Framework provides **architectural guidance**

（图上三层：`class library` → `framework` → `application`，标注 `reusing a framework`）

**「reuse of a macro architecture」是关键**。用库，你复用**实现**；用框架，你连**架构**一起复用——包括「有哪些类」「它们怎么交互」「控制流怎么走」。这是**更深**的复用，也是**更强**的约束。

## 5. 原理与推导

### 5.1 引子一：Scrabble 的临时放置问题（Mediator）

讲义第 1–3 页是上一讲留下的「每日设计问题」：

> **Design Problem of the Day**
> - **Consider the Scrabble game**
> - **The game has simple actions**
> - **You play a word and it is scored**
> - **The GUI is more complex**
> - **You choose tiles one by one and place them**
> - **How to resolve?**

**问题的本质**：游戏逻辑（`Game`）只需要「一个词 + 得分」；但 GUI 需要「逐块选瓦片、逐格放置、可以反悔、可以预览」。**GUI 的状态比游戏模型的状态更细**。

三种方案（第 2 页）：

> - **Have the game keep track of temporary tile placement**
> - **Have the GUI keep track of temporary tile placement**
> - **Use a mediator**（`GUI` — `VisualState` — `Game`）

**方案 1（游戏管临时状态）**：把「临时放置」塞进 `Game`。缺点是**污染模型**——`Game` 本来只需要知道「最终局面」，现在还要知道「用户正在拖哪块瓦片」。而且这些临时状态**只对 GUI 有意义**，对游戏规则毫无用处。这违反第 11 讲的 **High Cohesion**（一个类只做一件事）。

**方案 2（GUI 管临时状态）**：GUI 自己维护「临时放置」，只在用户确认时才调 `game.playWord(...)`。缺点是**GUI 变复杂**，而且如果将来有第二种前端（命令行、网络对战），临时放置逻辑要**重写一遍**。

**方案 3（Mediator）**：引入 `VisualState` 作为**中介者**，`GUI` 与 `Game` 都只跟它打交道。

```
GUI  ──→  VisualState  ──→  Game
```

**Mediator 的适用性**（第 3 页）：

> - **Applicability**
>   - **A set of objects that communicate in well-defined but complex ways**
>   - **Reusing an object is difficult because it communicates with others**
>   - **A behavior distributed between several classes should be customizable without a lot of subclassing**
> - **Consequences**
>   - **Avoids excessive subclassing to customize behavior**
>   - **Decouples colleagues, enhancing reuse**
>   - **Simplifies object protocols: many-to-many to one-to-many**
>   - **Abstracts how objects cooperate into the mediator**
>   - **Centralizes control**
>   - **Danger of mediator monolith**（中介者变成巨石）

**「Danger of mediator monolith」** 是最重要的后果。Mediator 把所有交互集中到一个类，很容易变成「什么都做的上帝类」——这正是第 11 讲警告的 **bloated controller**。所以 Mediator 是一把双刃剑：**它降低耦合，但集中复杂度**。

**为什么这一页出现在「框架」这一讲的开头？** 因为**框架本质上就是一个巨大的 Mediator**——它集中控制流，把「谁在什么时候被调用」的复杂度收进自己，让客户端只关注「填什么」。这也预告了后面「框架很难维护」「框架设计难」的讨论。

### 5.2 引子二：`instanceof` 为什么有害

第 4–12 页是第二个「每日设计建议」，用了 9 页反复讲一个点。

**第 4–6 页：三条理由**

> **Why is `instanceof` bad?**
> - **Often OK if you are testing against just one thing**
>   - **Especially if that thing is an interface**
>   - i.e. an **abstract concept, not an implementation**
> - **Problems come when testing against several things:**
>   - **You might forget one**
>     ```java
>     if (x instanceof Rabbit) …
>     else if (x instanceof Fox) …
>     // oops, forgot the Grass!
>     ```
>   - **A sequence of `instanceof`s is inefficient**
>     - **Better to do one dispatch than several `instanceof`s**
>   - **`instanceof`-based code is not extensible**
>     - **If a new class comes, you have to change code everywhere**

三条理由分别对应三个不同的质量问题：

| 理由 | 性质 | 对应第 11 讲原则 |
|---|---|---|
| 可能忘掉一个分支 | **正确性** | — |
| 一串 `instanceof` 效率低 | **性能** | — |
| 新类出现时要改多处 | **可扩展性** | **Protected Variations** |

**注意课件的措辞很克制**：它说「**Often OK if you are testing against just one thing**」。这是很重要的限定——`instanceof` **不是**绝对禁止的。第 3 讲讲过的 `equals` 实现里就有 `if (!(obj instanceof Point)) return false;`，那是**合法的**（测试单个接口/类，做类型检查后强转）。**问题出在「一串 `instanceof` 做多路分支」**。

这个区分很实用：**`instanceof` 作为「类型守卫」是好的，作为「类型分派」是坏的**。

**第 7–8 页：反例的演化**

```java
class Animal { … }
class Rabbit extends Animal { … }
class Fox extends Animal { … }

void move(Animal a) {
  if (a instanceof Rabbit)
    // move like a Rabbit
  if (a instanceof Fox)
    // move like a Fox
}
void eat(Animal a) {
  if (a instanceof Rabbit)
    // eat like a Rabbit
  if (a instanceof Fox)
    // eat like a Fox
}
```

加入 `Wolf` 之后（第 8 页）：

```java
class Wolf extends Animal { … }

void move(Animal a) {
  if (a instanceof Rabbit) …
  if (a instanceof Fox) …
  if (a instanceof Wolf)
    // move like a Wolf
}
void eat(Animal a) {
  if (a instanceof Rabbit) …
  if (a instanceof Fox) …
  if (a instanceof Wolf)
    // eat like a Wolf
}
```

课件批注：

> **Multiple files must change**
> **Easy to forget some changes**

**这就是「散弹式修改（shotgun surgery）」**——加一个类要改 N 个文件。这是第 11 讲 **Protected Variations** 的反面：变化没有被**局部化**。

注意一个细节：**`move` 与 `eat` 是两个独立的 `if` 序列**，它们的结构**完全相同**（都是「按类型分派」）。这说明「按类型分派」这个**关注点**被**重复**了 N 次——每加一个操作（`sleep`、`reproduce`…）就要再写一遍完整的类型分派。这是 **DRY（Don't Repeat Yourself）** 的违反。

**第 9 页：替代方案一——多态分派**

```java
interface Animal {
  void move();
  void eat();
}
class Rabbit extends Animal {
  void move() { /* move like a Rabbit */}
  void eat() { /* eat like a Rabbit */}
}
class Fox extends Animal {
  void move() { /* move like a Fox */}
  void eat() { /* eat like a Fox */}
}
class Wolf extends Animal {
  void move() { /* move like a Wolf */}
  void eat() { /* eat like a Wolf */}
}
```

> - **Now extension only affects one file.**
> - **Java's type system ensures we can't forget operations**

两个收益：

1. **扩展只影响一个文件**（加 `Wolf` 只需写一个类）；
2. **类型系统保证不会漏掉操作**（`Wolf` 不实现 `eat()` 就编译失败）。

第 2 条是本讲的重要洞见：**把「运行时的 `instanceof` 检查」换成「编译时的接口实现检查」**，把错误从**运行时**提前到**编译时**。这与第 4 讲「类型检查的价值」完全一致。

> 注意第 9 页的代码有一个排版/逻辑错误：`class Rabbit extends Animal` 但 `Animal` 是 `interface`——Java 里实现接口应写 `implements`。课件第 10–12 页的 Visitor 版本也有同样问题（`class Rabbit extends Animal` 而 `Animal` 是接口）。这是排版疏忽，不影响概念。**笔记按原样引用，此处指出。**

**第 10–12 页：替代方案二——Visitor 模式**

```java
interface Animal {
  void visit(AnimalVisitor v);
}
interface AnimalVisitor {
  void visitRabbit(Rabbit r);
  void visitFox(Fox f);
}
class Rabbit extends Animal {
  void visit(AnimalVisitor v) {
    v.visitRabbit(this);
  }
}
class Fox extends Animal {
  void visit(AnimalVisitor v) {
    v.visitFox(this);
  }
}
class MoveVisitor implements Visitor {
  void visitRabbit(Rabbit r) {
  /* move like a Rabbit */ }
  void visitFox(Fox f) {
  /* move like a Fox */ }
}
```

加入 `EatVisitor`（第 11 页）：

```java
class EatVisitor implements Visitor {
  void visitRabbit(Rabbit r) {
  /* eat like a Rabbit */ }
  void visitFox(Fox f);
  /* eat like a Fox */ }
}
```

> - **Good when you add operations frequently**

加入 `Wolf`（第 12 页）：

```java
interface AnimalVisitor {
  void visitRabbit(Rabbit r);
  void visitFox(Fox f);
  void visitWolf(Wolf w);      // ← 接口变了！
}
class Wolf extends Animal {
  void visit(AnimalVisitor v) {
    v.visitWolf(this);
  }
}
class MoveVisitor implements Visitor {
  void visitRabbit(Rabbit r) { … }
  void visitFox(Fox f) { … }
  void visitWolf(Wolf w) {
  /* move like a Wolf */ }
}
class EatVisitor implements Visitor {
  void visitRabbit(Rabbit r) { … }
  void visitFox(Fox f) { … }
  void visitWolf(Wolf w) {
  /* eat like a Wolf */ }
}
```

> - **Bad when you add new classes frequently**

**这就是「表达式问题（expression problem）」**——课件没有用这个名字，但讲的正是它：

| 变化方向 | 多态分派（虚方法） | Visitor 模式 |
|---|---|---|
| **加新类**（如 `Wolf`） | ✓ 只写一个新类 | ✗ 要改 `AnimalVisitor` 接口 + **所有** visitor 实现 |
| **加新操作**（如 `sleep`） | ✗ 要改**所有**类 | ✓ 只写一个新 visitor |

**没有一种方案对两个方向都友好**——这是 OOP 的一个**根本**限制（在 Java 这样的单分派语言里）。课件用两页分别说「Good when you add operations frequently」和「Bad when you add new classes frequently」，把这个对称性讲得很清楚。

**实用判据**：

- 如果**类型固定、操作常变**（如编译器 AST：节点类型稳定，但 pass 很多）→ **Visitor**；
- 如果**操作固定、类型常变**（如游戏角色：`move`/`eat` 稳定，但角色种类多）→ **多态分派**。

**这与「框架」有什么关系？** 关系很大：**Visitor 是「框架式」的**——`AnimalVisitor` 是框架定义的扩展点，你写 visitor 插件。所以 Visitor 模式本身就是一个小型框架（第 10 讲讲过的「框架 = 半个设计模式」的例证）。

### 5.3 库 vs 框架：控制权

第 15–16 页是本讲的核心定义。

**第 15 页：库**

> **Terminology: Libraries**
> - **Library: A set of classes and methods that provide reusable functionality**
> - **Client calls library to do some task**
> - **Client controls**
>   - **System structure**
>   - **Control flow**
> - **The library executes a function and returns data**

（图上库的例子：`I/O`、`Collections`、`Swing`、`Math`）

**第 16 页：框架**

> **Terminology: Frameworks**
> - **Framework: Reusable skeleton code that can be customized into an application**
> - **Framework controls**
>   - **Program structure**
>   - **Control flow**
> - **Framework calls back into client code**
> - **The Hollywood principle: "Don't call us; we'll call you."**

（图上框架的例子：`Swing`、`Eclipse`、`Spring`、`Applet`）

**注意 `Swing` 同时出现在两个列表里**——这就是那两个旁白气泡的来源。Swing 的**组件与布局**是库（你调用 `panel.add(button)`），Swing 的**事件循环**是框架（它调用你的 `actionPerformed`）。

**用一张图表达控制流的差别**：

```
库（Library）：
    客户端 main()
        │
        ├──→ lib.foo()  ──→ 返回
        ├──→ lib.bar()  ──→ 返回
        └──→ lib.baz()  ──→ 返回
    （客户端决定顺序、次数、何时停）

框架（Framework）：
    框架 main() / 事件循环
        │
        ├──→ plugin.init()      ← 框架调用你
        ├──→ plugin.handle(e)   ← 框架调用你
        └──→ plugin.destroy()   ← 框架调用你
    （框架决定顺序、次数、何时停）
```

**这个区别的实际后果**：

| 维度 | 库 | 框架 |
|---|---|---|
| 谁写 `main` | 客户端 | 框架（或客户端只写一行启动） |
| 调用方向 | 单向（客户端 → 库） | **双向**（客户端 → 框架，框架 → 客户端回调） |
| 调试难度 | 低（栈是线性的） | **高**（栈里有框架的帧，且回调时机不直观） |
| 学习成本 | 学 API | 学**协议**（何时被调、什么状态、能做什么） |
| 出错模式 | 调用参数错 | **在错误的时机做错事**（比如在 `init` 之前访问资源） |
| 复用深度 | 实现 | **设计与实现 + 架构** |

**「双向调用」是最本质的差别**。它带来一个特有的困难：**你的代码在什么时候被调用，不完全由你决定**。这正是第 13 讲 Swing 线程问题的根源——`actionPerformed` 在 GUI 线程上被调用，你在里面做耗时计算就会卡界面。

### 5.4 七个术语：API 生态的词汇表

第 17–18 页给出完整的术语表：

> **More terms**
> - **API**: Application Programming Interface, the interface of a library or framework
> - **Client**: The code that uses an API
> - **Plugin**: Client code that customizes a framework
> - **Extension point**: A place where a framework supports extension with a plugin
>
> - **Protocol**: The expected sequence of interactions between the API and the client
> - **Callback**: A plugin method that the framework will call to access customized functionality
> - **Lifecycle method**: A callback method of an object that gets called in a sequence according to the protocol and the state of the plugin

**七个术语的关系图**：

```
        框架（Framework）
          │ 暴露
          ├──→ API（接口）
          │      │ 被
          │      ↓
          │   Client（客户端代码）
          │      │ 若它定制框架，则称
          │      ↓
          ├──→ Plugin（插件）
          │      │ 通过
          │      ↓
          ├──→ Extension point（扩展点）挂载
          │      │ 遵循
          │      ↓
          ├──→ Protocol（交互序列）
          │      │ 其每一步是
          │      ↓
          └──→ Callback（回调）──→ 其中按状态/顺序调用的称 Lifecycle method
```

**「Protocol」是本讲最容易被忽视但最重要的概念**。它不只是「方法签名」，而是**交互的顺序约束**。举例（Swing 的 `Applet` 协议）：

```
init() → start() → paint() → stop() → destroy()
         ↑___________________|
         （start/stop 可以反复）
```

如果你在 `init()` 之前调用 `paint()`，或者 `destroy()` 之后再 `start()`，就是**违反协议**。这类错误**编译器查不出来**——因为每个方法的签名都对，只是**顺序**错了。

**这正是框架最难学的地方**：库的错误是「类型错」，编译器能抓；框架的错误是「顺序错」「状态错」，**只能靠文档和运行时**。

第 64 页把这一点写成设计建议：

> **Framework Design Advice**
> - **It's hard to understand framework code**
> - **So ensure it can be understood from the documentation**
>   - **Preconditions, postconditions, exceptions, order of calls, …**

「**order of calls**」被明确列出——这就是 protocol。

**Lifecycle method 的定义**值得再读一遍：「a callback method of an object that gets called **in a sequence according to the protocol and the state of the plugin**」。两个限定词：

- **according to the protocol**：顺序由协议规定；
- **according to the state of the plugin**：不是所有方法都会在所有情形下被调（比如 Servlet 的 `destroy()` 只在容器关闭或重新部署时调）。

第 53 页的 Servlet 例子完美对应：

> **Other Aspects of Java Servlets**
> - **Lifecycle methods**
>   - `void init(ServletConfig config)` —— **Sets up a Servlet object**
>   - `void destroy()` —— **Asks a Servlet object to clean itself up**
> - **Service methods**
>   - `doGet`, `doPut`, `doPost`, `doDelete`, etc.
> - **web.xml**
>   - **Defines mapping from pages to Servlet classes**
>   - **Alternative to `@WebServlet` annotation**

Servlet 的协议是：容器创建实例 → 调 `init(config)` **一次** → 对每个 HTTP 请求调 `doGet`/`doPost`（**多次**，可能**并发**）→ 容器关闭时调 `destroy()` **一次**。

**这个协议有三个隐含约束**，文档必须说清楚（否则客户端会写错）：

1. `init` 只调一次，所以可以在里面做昂贵初始化；
2. `doGet` 会被**多线程并发**调用，所以**不能**用实例字段存请求相关状态（这是 Servlet 最常见的 bug）；
3. `destroy` 之后不会再有任何调用，所以要在里面释放资源。

这三条**没有一条**能靠类型系统检查。这就是框架的「协议」必须写进文档的原因。

### 5.5 「用一个 API 像用半个设计模式」

第 19 页：

> **Using an API**
> - **Like a partial design pattern**
> - **Framework provides one part**
> - **Client provides the other part**
> - **Very common for plugin trees to exist**
> - **Also common for two frameworks to work better together**

**「半个设计模式」这个说法很精妙**。举例：

| 模式 | 框架提供 | 客户端提供 |
|---|---|---|
| **Strategy** | `Comparator` 接口 + 调用它的排序算法 | 具体的 `Comparator` 实现 |
| **Observer** | `Subject` 的 `addListener`/`notify` + 事件分发 | `Listener` 实现 |
| **Template Method** | 抽象类的骨架方法 | 覆写的钩子方法 |
| **Visitor** | `Visitor` 接口 + `accept` 机制 | 具体 visitor |
| **Factory Method** | 抽象 creator | 具体 factory |
| **Command** | 菜单/按钮的触发机制 | 具体 command 对象 |

**这个视角的价值**：它把「设计模式」与「框架 API」统一起来。你学过的每个模式，在真实 API 里都能找到「框架提供一半、你提供一半」的形态。

**「plugin trees」**：插件本身也可以是框架。比如 Eclipse 插件可以定义**自己的扩展点**，让别人扩展它。这样就形成了**插件树**（插件 → 子插件 → 孙插件）。Eclipse 的整个生态就是这样长出来的。

**「two frameworks work better together」**：比如 Spring + Hibernate、Eclipse + JUnit。它们各自是框架，但通过**适配**能协作。这也是第 9 讲 Adapter 模式在架构层面的应用。

### 5.6 MapReduce：框架如何内化质量属性

第 20–24 页用 Google 的 MapReduce 作为「框架威力」的案例。

**第 20 页：编程模型**

> **Google's Map-Reduce**
> - **Programming model for processing large data sets**
> - **Example: word count**
>   ```
>   map(URL, contents):
>     for each word w in contents
>       emit (w, 1)
>
>   reduce(word, listOfCounts):
>     for each count c in listOfCounts
>       result += c
>     emit result
>   ```
> - 类型签名：
>   ```
>   map    : (k1, v1) → list (k2, v2)
>   reduce : (k2, list(v2)) → list (v2)
>   ```
> （图：Input key-value pairs → Intermediate key-value pairs → Output key-value pairs）

**第 21 页：三个问题**

> **Questions**
> - **Is this a framework? How do you know?**
> - **What are the benefits?**
> - **Could those benefits be achieved if it were not?**

这三个问题是**苏格拉底式**的，逼你自己推导。答案在下一页。

**第 22 页：收益**

> **Some Benefits of Map-Reduce**
> - **Automatically parallelizes and distributes computation**
> - **Scales to 1000s of machines, terabytes of data**
> - **Automatically handles failure via re-execution**
> - **Simple programming model**
> - **Successful: hundreds of plugins**
> - **Functional model facilitates correctness**

**「Is this a framework? How do you know?」的答案**：是。判据是**控制权**——你只写 `map` 和 `reduce` 两个函数（插件），**框架**决定：

- 数据怎么切分（split）；
- 哪些 map 任务分配到哪台机器；
- 中间结果怎么按 key 分区（partition）与排序；
- 什么时候启动 reduce；
- 任务失败怎么重试。

你**完全不控制**这些——你只填两个函数。这就是框架。

**「What are the benefits?」** 上面六条。注意它们**没有一条**是你的 `map`/`reduce` 代码提供的——它们全部来自**框架**。

**「Could those benefits be achieved if it were not?」** 这是最关键的问题。答案是：**理论上可以，但实践中不会**。

如果 MapReduce 只是一个**库**（比如你调 `MapReduce.run(myMapper, myReducer)`），那么：

- 并行化要你自己写；
- 容错要你自己写；
- 数据分片要你自己写；
- 结果就是：**每个用户都会写一遍，而且大多数人会写错**。

**框架把这些「横切关注点（cross-cutting concerns）」内化了**。第 65 页的总结用了一个精确的词：

> - **Can often internalize qualities like reliability (cf. MapReduce)**

**「internalize qualities」是本讲最深的一句**。它说的是：**质量属性（可靠性、可扩展性、性能）可以被「装进」框架**，于是客户端**自动获得**它们，而不需要自己实现。

这与第 11 讲「质量属性是设计的目标」形成一个漂亮的闭环：

- 第 11 讲：**设计的目标是质量属性**（可演化性、可复用性、健壮性…）；
- 第 16 讲：**框架是把质量属性「产品化」的手段**——你设计一次，所有客户端都获得。

**第 23 页：代价**

> **Constraints**
> - **Computation must fit the model**
>   - **Not everything can be phrased in terms of map and reduce**
> - **Map and Reduce must be largely functional**
>   - **Side effects allowed but must be atomic and idempotent**
> - **What benefits does the client get in exchange for accepting these restrictions?**

**这三条约束是本讲的另一个核心洞见**：**框架的威力来自约束**。

- 「必须能用 map/reduce 表达」——限制了你能解决的问题；
- 「必须基本函数式」——限制了你能用的编程风格；
- 「副作用必须原子且幂等」——这是**容错**的前提（失败重试时，重复执行不能产生额外效果）。

**最后那个问题**（「客户端接受这些限制，换来什么好处？」）的答案是第 22 页的六条收益。这是一个**明确的交易**：

```
客户端放弃：表达自由（只能用 map/reduce、必须函数式、副作用受限）
客户端获得：自动并行、自动分布、自动容错、千台机器规模、简单模型
```

**这个交易是否值得，取决于问题**。这正是第 59 页「使用 vs 复用困境」的伏笔。

**第 24 页：Hadoop 的真实接口比「显而易见的」更丰富**

> **Hadoop: Map-Reduce in Java**
> - See `http://hadoop.apache.org/`
> - `http://hadoop.apache.org/docs/current/api/org/apache/hadoop/mapred/Mapper.html`
> - `http://hadoop.apache.org/docs/current/api/org/apache/hadoop/mapred/Reducer.html`
> - **The interface is richer than the obvious one!**
> - **Map and Reduce are separate abstractions**
> - **May have several maps followed by one reduce, for example**
> - `configure()` **supports setup operations, e.g. prefilling a cache**
> - `close()` **allows a job to clean up resources**
> - `OutputCollector` **supports mapping to >1 pair**
> - `Reporter` **supports incremental progress updates**
>   - **Used to decide whether to kill a job, for example**

这一页讲的是**真实框架与教学模型的差距**：

| 教学模型 | Hadoop 真实接口 | 为什么需要 |
|---|---|---|
| `map(k1,v1) → list(k2,v2)` | `Mapper.map(...)` + `OutputCollector` | 一个输入可能产出多个输出对 |
| `reduce(k2, list(v2)) → list(v2)` | `Reducer.reduce(...)` | 同上 |
| （无） | `configure()` | 初始化（预填缓存） |
| （无） | `close()` | 清理资源 |
| （无） | `Reporter` | 进度上报（用于决定是否 kill 任务） |

**「The interface is richer than the obvious one!」** 这句话很值得记住。它说的是：**真实框架的接口总比教科书模型复杂**，因为真实世界有：

- **生命周期**（`configure` / `close`）——这是 5.4 节的 Lifecycle method；
- **多个输出**（`OutputCollector`）——教学模型假设一对一，现实是一对多；
- **进度与可观测性**（`Reporter`）——长时间运行的任务需要报告进度，否则无法运维。

**这对框架设计者的启示**：不要以为「核心抽象」就够了。**运维需求**（生命周期、进度、日志、取消）**也是接口的一部分**，而且往往是后来才加上的（这就是为什么很多框架的接口看起来「不优雅」——它们是**演化**出来的，不是设计出来的）。

### 5.7 白盒框架：子类化

第 25–28 页讲白盒框架。

**第 25 页：动机**

> **Implementing Frameworks**
> - **Family of programs consisting of buttons and text fields only**
> - **Share 90% of the source code**
>   - **Main method**
>   - **Initialization of GUI**
>   - **Layout**
>   - **Closing the window**
>   - …

**「Share 90% of the source code」** 是框架的动机：如果一类程序有 90% 的代码相同，那么**把这 90% 抽出来**就得到框架。

**第 26 页：一个具体的应用（没有框架）**

```java
public class Calc extends JFrame {
  private JTextField textfield;

  public static void main(String[] args) { new Calc().setVisible(true); }
  public Calc() { init(); }

  protected void init() {
    JPanel contentPane = new JPanel(new BorderLayout());
    contentPane.setBorder(new BevelBorder(BevelBorder.LOWERED));

    JButton button = new JButton();
    button.setText("calculate");
    contentPane.add(button, BorderLayout.EAST);

    textfield = new JTextField("");
    textfield.setText("10 / 2 + 6");
    textfield.setPreferredSize(new Dimension(200, 20));
    contentPane.add(textfield, BorderLayout.WEST);

    button.addActionListener(/* code zum berechnen */);

    this.setContentPane(contentPane);
    this.pack();
    this.setLocation(100, 100);
    this.setTitle("My Great Calculator");
    // impl. for closing the window
  }
}
```

**这个类里哪些是「共性」、哪些是「可变」？**

| 代码 | 性质 |
|---|---|
| `JPanel` + `BorderLayout` + `BevelBorder` | **共性**（所有这类程序都一样） |
| `button` 在东、`textfield` 在西 | **共性** |
| `setPreferredSize(new Dimension(200, 20))` | **共性** |
| `setContentPane` / `pack` / `setLocation` / 关闭窗口 | **共性** |
| `button.setText("calculate")` | **可变**（每个程序不同） |
| `textfield.setText("10 / 2 + 6")` | **可变** |
| `addActionListener(...)` 的**内容** | **可变** |
| `setTitle("My Great Calculator")` | **可变** |

**白盒框架的做法：把「可变」抽成抽象方法，把「共性」放进 `init()`。**

**第 27 页：白盒框架的定义**

> **White-Box Frameworks**
> - **Extension through subclassing and method overriding**
> - **see Template Method design pattern**
> - **Design steps:**
>   - **Identify the common and the variable code**
>   - **Abstract variable code as method calls**

**两个设计步骤就是全部**——但第 1 步（识别共性与可变）是最难的，也是第 58 页说的「Key Decision」。

**第 28 页：白盒框架的实现**

```java
public abstract class Application extends JFrame {
  protected abstract String getApplicationTitle();
  protected abstract String getButtonText();
  protected String getInititalText() {return "";}     // 钩子，有默认实现
  protected void buttonClicked() { }                    // 钩子，有默认实现

  private JTextField textfield;

  public Application() { init(); }

  protected void init() {
    JPanel contentPane = new JPanel(new BorderLayout());
    contentPane.setBorder(new BevelBorder(BevelBorder.LOWERED));

    JButton button = new JButton();
    button.setText(getButtonText());                    // ← 调用抽象方法
    contentPane.add(button, BorderLayout.EAST);

    textfield = new JTextField("");
    textfield.setText(getInititalText());               // ← 调用钩子
    textfield.setPreferredSize(new Dimension(200, 20));
    contentPane.add(textfield, BorderLayout.WEST);

    button.addActionListener(/* … buttonClicked(); … */);  // ← 调用钩子

    this.setContentPane(contentPane);
    this.pack();
    this.setLocation(100, 100);
    this.setTitle(getApplicationTitle());               // ← 调用抽象方法
    // impl. for closing the window
  }

  protected String getInput() { return textfield.getText();}
}
```

**四个扩展点，两种性质**：

| 方法 | 类型 | 子类**必须**实现？ |
|---|---|---|
| `getApplicationTitle()` | **抽象方法** | ✓ 是 |
| `getButtonText()` | **抽象方法** | ✓ 是 |
| `getInititalText()` | **钩子（hook）**，有默认实现 `""` | ✗ 否 |
| `buttonClicked()` | **钩子**，默认空实现 | ✗ 否 |

**抽象方法 vs 钩子的区别**是本讲的一个实用知识点：

- **抽象方法**：框架**需要**这个信息才能工作，子类**必须**提供；
- **钩子（hook）**：框架**提供默认行为**，子类**可以**覆写。

为什么 `getInititalText()` 是钩子而不是抽象方法？因为「初始文本为空」是一个**合理的默认**——`Ping` 程序可能需要默认 IP，但很多程序不需要初始文本。如果强制实现，每个子类都要写 `return "";`，很烦。

**这就是第 9 讲讲过的 Template Method 的「钩子」概念**，在白盒框架里得到完整应用。

两个具体应用：

```java
public class Calculator extends Application {
  protected String getButtonText() { return "calculate"; }
  protected String getInititalText() { return "(10 – 3) * 6"; }
  protected void buttonClicked() {
    JOptionPane.showMessageDialog(this, "The result of "+getInput()+
        " is "+calculate(getInput())); }
  protected String getApplicationTitle() { return "My Great Calculator"; }
  public static void main(String[] args) {
    new Calculator().setVisible(true);
  }
}

public class Ping extends Application {
  protected String getButtonText() { return "ping"; }
  protected String getInititalText() { return "127.0.0.1"; }
  protected void buttonClicked() {  /* … */  }
  protected String getApplicationTitle() { return "Ping"; }
  public static void main(String[] args) {
    new Ping().setVisible(true);
  }
}
```

**两个应用各只写了 4 个方法**，就获得了整个 GUI 骨架（布局、边框、尺寸、pack、关闭窗口）。这就是白盒框架的威力。

**注意 `Application` 的构造函数调用 `init()`**——而 `init()` 又会调用**子类覆写的方法**。这是一个**经典陷阱**：

```java
public Application() { init(); }     // 构造器里调用可覆写方法
```

**问题**：当 `new Calculator()` 执行时，`Application()` 构造器先运行，此时 `Calculator` 的**字段还没初始化**（字段初始化在 `super()` 之后）。如果 `buttonClicked()` 依赖子类字段，就会读到 `null`/`0`。

这个陷阱在 Java 里很常见（Effective Java 第 17 条：「Design and document for inheritance or else prohibit it」）。课件**没有**指出这个问题——它是一个真实的坑。**笔记在此标出**。

**更安全的写法**是延迟到 `setVisible` 之后初始化，或者用**两阶段初始化**（构造器只做最小工作，`init()` 由客户端显式调用）。但那样客户端要多写一行——这是**安全 vs 便利**的权衡。

### 5.8 黑盒框架：插件接口

第 29–30 页。

**第 29 页：定义**

> **Black-Box Frameworks**
> - **Extension by Implementing Plug-in Interface**
> - **see Strategy Pattern, Observer Pattern**
> - **Design steps:**
>   - **Identify the common and the variable code**
>   - **Abstract variable code as methods of an interface**

**与白盒的唯一差别**：可变部分被抽成**接口的方法**，而不是**抽象类的方法**。

**第 30 页：实现**

```java
public class Application extends JFrame {
  private JTextField textfield;
  private Plugin plugin;

  public Application(Plugin p) { this.plugin=p; p.setApplication(this); init(); }

  protected void init() {
    JPanel contentPane = new JPanel(new BorderLayout());
    contentPane.setBorder(new BevelBorder(BevelBorder.LOWERED));

    JButton button = new JButton();
    if (plugin != null)
      button.setText(plugin.getButtonText());
    else
      button.setText("ok");
    contentPane.add(button, BorderLayout.EAST);

    textfield = new JTextField("");
    if (plugin != null)
      textfield.setText(plugin.getInititalText());
    textfield.setPreferredSize(new Dimension(200, 20));
    contentPane.add(textfield, BorderLayout.WEST);

    if (plugin != null)
      button.addActionListener(/* … plugin.buttonClicked();… */);

    this.setContentPane(contentPane);
    …
  }
  public String getInput() { return textfield.getText();}
}
```

**注意三个变化**：

1. `Application` **不再是 abstract**——它可以直接实例化（`plugin` 可以为 `null`，此时用默认值 `"ok"`）；
2. 可变部分改为**委托给 `plugin`**（`plugin.getButtonText()` 而非 `getButtonText()`）；
3. 增加了**双向引用**：`Application` 持有 `plugin`，`plugin` 也持有 `application`（通过 `p.setApplication(this)`）。

**第 3 点是黑盒框架的典型特征**：插件需要**回调框架**（比如 `CalcPlugin.buttonClicked()` 里要 `application.getInput()`）。这就形成了**双向依赖**。

```java
public interface Plugin {
  String getApplicationTitle();
  String getButtonText();
  String getInititalText();
  void buttonClicked();
  void setApplication(Application app);      // ← 让插件拿到框架引用
}
```

**`setApplication` 是「依赖注入」的手工版本**。它的存在说明：黑盒框架的插件**不是完全独立的**——它需要框架提供的能力（`getInput()`）。

**这带来一个耦合问题**：`Plugin` 接口**依赖** `Application` 类（因为 `setApplication(Application)` 的参数类型）。这意味着：

- 插件**必须**知道 `Application` 类；
- 如果想让插件复用到**另一个**框架，就要改接口。

**更好的设计**是把「框架提供的能力」也抽成接口：

```java
interface ApplicationContext {
    String getInput();
    void showMessage(String msg);
}
interface Plugin {
    String getButtonText();
    void buttonClicked(ApplicationContext ctx);   // 能力通过参数传入
}
```

这样 `Plugin` 就**不依赖**具体的 `Application` 类。这是**接口隔离原则（ISP）**的应用，也是现代框架（Spring、Eclipse）的常见做法。

课件**没有**讨论这一点——它展示的是最简版本。**笔记在此补充**，因为这是真实框架设计中的关键改进。

**插件的实现**：

```java
public class CalcPlugin implements Plugin {
  private Application application;
  public void setApplication(Application app) { this.application = app; }
  public String getButtonText() { return "calculate"; }
  public String getInititalText() { return "10 / 2 + 6"; }
  public void buttonClicked() {
    JOptionPane.showMessageDialog(null, "The result of "
        + application.getInput() + " is "
        + calculate(application.getText())); }
  public String getApplicationTitle() { return "My Great Calculator"; }
}

class CalcStarter {
  public static void main(String[] args) {
    new Application(new CalcPlugin()).setVisible(true);
  }
}
```

**注意 `CalcPlugin` 没有 `main`**——`main` 在 `CalcStarter` 里（也可以由框架提供）。这是白盒与黑盒的一个实际差别：白盒的每个子类都有自己的 `main`（因为它是应用），黑盒的插件**不是应用**（它只是配置）。

> 课件这里有两处代码问题：`CalcPlugin.buttonClicked()` 里调用 `application.getText()`，但 `Application` 类里只有 `getInput()`，没有 `getText()`——应是笔误。另外 `calculate(...)` 方法在 `CalcPlugin` 里没有定义（第 26 页的 `Calc` 里也没有定义），应视为伪代码。**笔记按原样引用并指出。**

### 5.9 白盒 vs 黑盒：对比与选择

第 37 页给出权威对比：

> **Whitebox vs. Blackbox Frameworks**
> - **Whitebox uses subclassing**
>   - **Allows clients to extend every non-private/-final method**
>   - **Need to understand when overridable methods are called**
>   - **May need to read the implementation, if not properly documented**
> - **Blackbox uses composition**
>   - **Allows clients to extend only functionality exposed in interface**
>   - **Only need to understand the interface**

| 维度 | 白盒（子类化） | 黑盒（组合 + 接口） |
|---|---|---|
| 扩展机制 | `extends` + 覆写 | `implements` + 注入 |
| 扩展范围 | **所有**非 private/final 方法 | **仅**接口暴露的方法 |
| 需要理解什么 | **何时**调用可覆写方法（+ 可能要看实现） | **只需**接口 |
| 对应模式 | **Template Method** | **Strategy、Observer** |
| 耦合度 | 高（子类依赖父类实现细节） | 低（只依赖接口） |
| 灵活性 | 低（编译期绑定） | 高（运行期可换） |
| 学习成本 | 高（要读源码/文档） | 低（看接口即可） |

**「Need to understand when overridable methods are called」是白盒的核心代价**。举例：`Application()` 构造器里调 `init()`，`init()` 里调 `getButtonText()`。如果你不知道这个调用链，就可能写出「在 `getButtonText()` 里访问未初始化字段」的 bug。

**这正是第 11 讲「信息隐藏」的反面**：白盒框架**暴露了实现细节**（调用顺序），客户端**不得不**依赖它。而黑盒框架只暴露接口，实现可以自由变化。

**「Only need to understand the interface」是黑盒的核心收益**——但也带来代价：**接口必须设计得很好**，因为一旦发布就难改（第 58 页：「Once designed, little place for change」）。

**实际框架大多是混合的**：

| 框架 | 白盒部分 | 黑盒部分 |
|---|---|---|
| **Swing** | `extends JPanel` 覆写 `paintComponent` | `addActionListener(Listener)` |
| **JUnit 3** | `extends TestCase` | — |
| **JUnit 4** | — | `@Test` 注解 + `Runner` |
| **Servlet** | `extends HttpServlet` | （主要是白盒） |
| **Eclipse** | `extends TextEditor` | `plugin.xml` 声明扩展点 |
| **Spring** | — | 接口 + 注解 + XML |

**JUnit 的演化是一个绝佳案例**：JUnit 3 要求 `extends TestCase`（白盒），JUnit 4 改为 `@Test` 注解（黑盒）。为什么？因为白盒的 `extends TestCase` 强制了**继承**——如果你的测试类已经继承了别的类，就没法用 JUnit 3。这是第 3 讲「优先组合而非继承」的教训在框架层面的重演。

**第 38 页：可运行 vs 必须扩展**

> **Running a Framework**
> - **Some frameworks are runnable by themselves**
>   - **E.g. Eclipse JDT**
> - **Other frameworks must be extended to be run**
>   - **Eclipse RCP, MapReduce, Swing, Servlets, JUnit**

**这个区分很实用**：

| 类型 | 例子 | 你能直接运行吗 |
|---|---|---|
| **可独立运行** | Eclipse JDT（Java 开发工具） | ✓ 装了就能用 |
| **必须扩展** | Eclipse RCP、MapReduce、Swing、Servlet、JUnit | ✗ 必须先写插件 |

**「必须扩展才能跑」是框架的一个奇怪性质**：框架本身**不能**完成任何有用的事——它只是一副骨架。这既是它的力量（可定制），也是它的弱点（空框架无价值）。

**这也解释了为什么框架的「开箱即用」很重要**（第 55 页）：

> - **late commitment to implementation**
> - **but, frameworks still have to work out of the box!**

**「必须开箱即用」与「延迟实现承诺」是一对矛盾**：框架想让客户端晚点决定实现（灵活性），但又必须提供一个能跑的默认实现（可用性）。这个矛盾是框架设计的核心张力之一。

### 5.10 框架设计的黄金法则

第 32 页是本讲最重要的一页：

> **The Golden Rule of Framework Design**
> - **Extending the framework should NOT require modifying the framework source code!**
> - **Discussion: how can we extend without modification?**
>   - **Client writes `main()`, creates a plugin, and passes it to framework**
>     - **See examples above**
>   - **Framework writes `main()`, client passes name of plugin**
>     - **E.g. using a command line argument or environment variable**
>   - **Framework looks in a magic location**
>     - **Config files or JAR files there are automatically loaded and processed**

**这条法则为什么是「黄金」的？** 因为修改框架源码有**三重代价**：

1. **你要维护一个 fork**——框架升级时你要合并改动，冲突不断；
2. **你的改动无法分享**——别人用不到你的修复；
3. **你违反了封装**——你依赖了框架的内部细节，而它们随时可能变。

这与第 11 讲的 **Protected Variations** 完全一致：**变化应该被局部化**，而「修改框架源码」把变化扩散到了框架内部。

**三种「不修改而扩展」的方式**：

| 方式 | 谁写 `main` | 客户端提供 | 例子 |
|---|---|---|---|
| **A. 客户端写 `main`** | 客户端 | 一个插件对象 | `new Application(new CalcPlugin()).setVisible(true)` |
| **B. 框架写 `main`，客户端传类名** | 框架 | 命令行参数/环境变量 | `java Framework my.pkg.MyPlugin` |
| **C. 框架读「魔法位置」** | 框架 | 配置文件/JAR | `.config`、`plugin.xml`、`META-INF/services` |

**第 33 页：方式 B 的实现（反射）**

```java
public static void main(String[] args) {
  if (args.length != 1) {
    System.out.println("Plugin name not specified");
  } else {
    String pluginName = args[0];
    try {
      Class<?> pluginClass = Class.forName(pluginName);
      Plugin plugin = (Plugin) pluginClass.newInstance();
      new Application(plugin).setVisible(true);
    } catch (Exception e) {
      System.out.println("Cannot load plugin " + pluginName
          + ", reason: " + e);
    }
  }
}
```

**三行核心代码**：

```java
Class<?> pluginClass = Class.forName(pluginName);   // 1. 按名字加载类
Plugin plugin = (Plugin) pluginClass.newInstance(); // 2. 实例化 + 强转
new Application(plugin).setVisible(true);           // 3. 交给框架
```

**这就是 Java 反射（reflection）的最小用法**。它的价值：**框架在编译时不知道插件的存在**——插件可以在框架发布**之后**才写。这就是「不修改而扩展」的技术基础。

**代价（课件未说，笔记补充）**：

| 代价 | 说明 |
|---|---|
| **编译期无类型检查** | `pluginName` 写错只有运行时才发现 |
| **强转可能失败** | 若类存在但没实现 `Plugin`，抛 `ClassCastException` |
| **`newInstance()` 要求无参构造** | 有参构造会抛 `InstantiationException` |
| **性能开销** | 反射调用比直接调用慢（但加载一次，通常可忽略） |
| **安全限制** | 某些环境（如旧版 Applet、模块化 JDK）限制反射 |
| **错误处理复杂** | 要捕获 `ClassNotFoundException`、`InstantiationException`、`IllegalAccessException` |

**现代替代**：Java 9+ 的 `ServiceLoader`（`META-INF/services/` 声明式注册）、依赖注入容器（Spring）、`java.util.ServiceLoader`。它们把「按名字加载」变成「按声明发现」，避免了硬编码类名。

**第 34 页：方式 C 的实现（读配置文件）**

```java
public static void main(String[] args) {
  File config = new File(".config");
  BufferedReader reader = new BufferedReader(new FileReader(config));
  Application = new Application();
  String pluginName = null;
  while ((pluginName = reader.readLine()) != null) {
    try {
      Class<?> pluginClass = Class.forName(pluginName);
      application.addPlugin((Plugin) pluginClass.newInstance());
    } catch (Exception e) {
      System.out.println("Cannot load plugin " + pluginName
          + ", reason: " + e);
    }
  }
  reader.close();
  application.setVisible(true);
}
```

**与方式 B 的差别**：支持**多个**插件（`while` 循环读多行）。这引出第 36 页的「支持多插件」。

> 课件第 34 页代码有笔误：`Application = new Application();`（缺变量声明与变量名，应为 `Application application = new Application();`）。另外没有 try-with-resources / finally，`reader.close()` 在异常时不会执行——这是资源泄漏。**笔记按原样引用并指出。**

**第 36 页：多插件 + Observer**

```java
public class Application {
  private List<Plugin> plugins;

  public Application(List<Plugin> plugins) {
    this.plugins=plugins;
    for (Plugin plugin: plugins)
      plugin.setApplication(this);
  }

  public Message processMsg (Message msg) {
    for (Plugin plugin: plugins)
      msg = plugin.process(msg);
    ...
    return msg;
  }
}
```

课件批注：

> - **see Observer pattern**
> - **Load and initialize multiple plugins**
> - **Plugins can register for events**
> - **Multiple plug-ins can react to same events**
> - **Different interfaces for different events possible**

**注意 `processMsg` 是「链式」而非「广播」**：每个插件**修改** `msg` 并传给下一个（`msg = plugin.process(msg)`）。这是 **Chain of Responsibility**（责任链）而非纯 Observer。

课件说「see Observer pattern」，但代码更像责任链。**两者的区别**：

| 模式 | 语义 | 代码特征 |
|---|---|---|
| **Observer** | 广播：所有观察者**都**收到**同一**事件 | `for (o : observers) o.update(e);`（`e` 不变） |
| **Chain of Responsibility** | 链式：每个处理者**可以**修改/拦截/终止 | `e = h.handle(e);`（`e` 逐级传递） |

课件把两者混在一起了——这是**教学简化**。真实框架里两者都有：Eclipse 的 builder 是责任链，Eclipse 的 listener 是 Observer。**笔记在此区分。**

### 5.11 Eclipse：工业级插件框架

第 31、39–43 页用 Eclipse 展示真实框架的复杂度。

**第 41 页：Manifest 文件**

```
Manifest-Version: 1.0
Bundle-ManifestVersion: 2
Bundle-Name: MyEditor Plug-in
Bundle-SymbolicName: MyEditor; singleton:=true
Bundle-Version: 1.0.0
Bundle-Activator: myeditor.Activator
Require-Bundle: org.eclipse.ui,
 org.eclipse.core.runtime,
 org.eclipse.jface.text,
 org.eclipse.ui.editors
Bundle-ActivationPolicy: lazy
Bundle-RequiredExecutionEnvironment:
 JavaSE-1.6
```

课件批注：

> - **A popular Java IDE**
> - **More generally, a framework for tools that facilitate "building, deploying and managing software across the lifecycle."**
> - **Plug-in framework based on OSGI standard**
> - **Starting point: Manifest file**
>   - **Plugin name**
>   - **Activator class**
>   - **Meta-data**

**关键字段**：

| 字段 | 作用 |
|---|---|
| `Bundle-SymbolicName` | 插件唯一标识（框架靠它识别） |
| `Bundle-Version` | 版本（支持多版本共存） |
| `Bundle-Activator` | 启动类（**生命周期入口**） |
| `Require-Bundle` | **依赖声明**（我要用哪些别的插件） |
| `Bundle-ActivationPolicy: lazy` | **懒加载**（用到才启动） |
| `Bundle-RequiredExecutionEnvironment` | 运行环境要求 |

**`Bundle-ActivationPolicy: lazy` 值得注意**：Eclipse 有上千个插件，如果全部启动要几分钟。`lazy` 让插件**只在第一次被用到时**才加载。这是**性能与启动时间**的设计取舍，也是大型框架的必备机制。

**第 42 页：`plugin.xml` 与扩展点**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<?eclipse version="3.2"?>
<plugin>
  <extension
    point="org.eclipse.ui.editors">
    <editor
      name="Sample XML Editor"
      extensions="xml"
      icon="icons/sample.gif"
      contributorClass="org.eclipse.ui.texteditor.BasicTextEditorActionContributor"
      class="myeditor.editors.XMLEditor"
      id="myeditor.editors.XMLEditor">
    </editor>
  </extension>
</plugin>
```

课件批注：

> - **`plugin.xml`**
> - **Main configuration file**
> - **XML format**
> - **Lists extension points**
> - **Editor extension**
>   - **extension point: `org.eclipse.ui.editors`**
>   - **file extension**（`extensions="xml"`）
>   - **icon used in corner of editor**（`icon="icons/sample.gif"`）
>   - **class name**（`class="myeditor.editors.XMLEditor"`）
>   - **unique id**（`id="myeditor.editors.XMLEditor"`）
> - **refer to this editor**
> - **other plugins can extend with new menu items, etc.!**

**这是「不修改而扩展」的极致形态**：你**声明**（`<extension point="...">`）而不是**调用**。框架读 XML，按 `point` 找到扩展点，按 `class` 加载你的类。

**三个关键概念**：

1. **扩展点（extension point）**：由**框架**定义的字符串标识（`org.eclipse.ui.editors`），代表一个可扩展的位置；
2. **扩展（extension）**：由**插件**声明的 XML 块，声明「我要往这个扩展点挂东西」；
3. **贡献（contribution）**：扩展里的具体配置（`<editor>` 元素），框架据此实例化你的类。

**为什么用 XML 而不是代码？** 因为：

- **声明式**：框架可以在**不加载你的类**的情况下知道你提供了什么（用于菜单构建、图标显示）；
- **懒加载**：只有真正打开 XML 文件时才实例化 `XMLEditor`；
- **可发现**：其他插件可以**查询**「谁扩展了 `org.eclipse.ui.editors`」，从而构建「打开方式」菜单。

**这与第 5.10 节的「方式 C：框架读魔法位置」完全对应**——`plugin.xml` 就是那个「魔法位置」。

**第 43 页：真正的代码**

```java
package myeditor.editors;
import org.eclipse.ui.editors.text.TextEditor;

public class XMLEditor extends TextEditor {
  private ColorManager colorManager;

  public XMLEditor() {
    super();
    colorManager = new ColorManager();
    setSourceViewerConfiguration(
        new XMLConfiguration(colorManager));
    setDocumentProvider(
        new XMLDocumentProvider());
  }

  public void dispose() {
    colorManager.dispose();
    super.dispose();
  }
}
```

课件批注：

> - **At last, code!**
> - **`XMLEditor.java`**
> - **Inherits `TextEditor` behavior**
>   - **open, close, save, display, select, cut/copy/paste, search/replace, …**
>   - **REALLY NICE not to have to implement this**
> - **But could have used `ITextEditor` interface if we wanted to**
> - **Extends with syntax highlighting**
>   - **`XMLDocumentProvider` partitions into tags and comments**
>   - **`XMLConfiguration` shows how to color partitions**

**这一页是「框架价值」的最好证明**：整个 XML 编辑器只有 **15 行代码**，却拥有：

- 打开/关闭/保存文件；
- 显示、选择、剪切/复制/粘贴；
- 搜索/替换；
- 撤销/重做；
- 语法高亮（通过 `XMLConfiguration`）。

**「REALLY NICE not to have to implement this」** —— 这句话是框架存在的全部理由。

**但注意课件的限定**：「But could have used `ITextEditor` interface if we wanted to」——**白盒与黑盒的选择**。`extends TextEditor` 是白盒（拿到所有默认实现，但耦合了 `TextEditor` 类）；`implements ITextEditor` 是黑盒（只依赖接口，但要自己实现更多）。

**Eclipse 的演化故事**（第 57 页）：

> **Evolution: Extract Interface from Class**（credit: Erich Gamma）
> - **⇒ JHotDraw defines framework abstractions as interfaces**
> - **extracting interfaces is a new step in evolutionary design**
> - **abstract classes are discovered from concrete classes**
> - **interfaces are distilled from abstract classes**
> - **start once the architecture is stable!**
> - **remove non-public methods from class**
> - **move default implementations into an abstract class which implements the interface**

**这是一段极其重要的设计史**。它说的是：

```
具体类  →（发现共性）→  抽象类  →（提炼契约）→  接口 + 骨架类
```

**「start once the architecture is stable!」** —— 这是关键警告。**不要一开始就设计接口**——你还不知道什么是稳定的。正确的顺序是：

1. 先写**具体类**（几个相似的实现）；
2. 从具体类**提取抽象类**（发现共性）；
3. 架构稳定后，从抽象类**提炼接口**（只留稳定契约）；
4. 把默认实现移进**骨架类**（`AbstractXxx implements Xxx`）。

**这正是第 14 讲 `AbstractList` 的来历**——`List` 接口 + `AbstractList` 骨架类 + `ArrayList` 具体类。这个三层结构不是一开始就有的，而是**演化**出来的。

**「interfaces are distilled from abstract classes」** 与第 11 讲的 **Direct Mapping** 原则一致：设计应当反映领域的自然结构，而自然结构是**逐步发现**的。

### 5.12 框架分层：Kit / Framework / Defaults

第 56 页（credit: Erich Gamma）给出框架的三层结构：

> **Framework Layering**
>
> （图：`Drawing` / `Figure` —— Framework Package；`StandardDrawing` / `AbstractFigure` —— Defaults/Standard Package；`LineConnection` —— Kit Packages）
>
> - **Kit Packages**
>   - **reuse of implementation**
>   - **least stable → implementation only**
>   - **more concrete**
> - **Framework Package**
>   - **reuse of design**
>   - **stable → no implementation**
>   - **specifies public interfaces**
> - **Defaults/Standard Package**
>   - **reuse of design and code**
>   - **less stable → more implementation**
>   - **specifies protected interfaces**
> - （轴：more stable ←→ more concrete）

**三层结构表**：

| 层 | 内容 | 复用的是什么 | 稳定性 | 可见性 |
|---|---|---|---|---|
| **Framework Package** | `Drawing`、`Figure`（接口） | **设计** | **最稳定** | `public` 接口 |
| **Defaults/Standard Package** | `StandardDrawing`、`AbstractFigure`（抽象类） | **设计 + 代码** | 较不稳定 | `protected` 接口 |
| **Kit Packages** | `LineConnection` 等（具体类） | **实现** | 最不稳定 | 纯实现 |

**这个分层的洞见是**：**稳定性与具体性反相关**。

- 接口最**抽象** → 最**稳定**（`Figure` 十年不变）；
- 骨架类**部分实现** → 中等稳定（`AbstractFigure` 会加新钩子）；
- 具体类**完全实现** → 最**不稳定**（`LineConnection` 可能被替换）。

**这与第 11 讲的「信息隐藏」完美对应**：**越稳定的东西越应该暴露，越易变的东西越应该隐藏**。分层正是这个原则的**物理体现**——不同的包，不同的稳定性，不同的可见性。

**实践指导**：

- 客户端代码应**尽量依赖 Framework Package**（接口），这样框架升级时受影响最小；
- 只有在需要**复用实现**时才继承 Defaults Package（抽象类）；
- **绝不**依赖 Kit Packages 的内部结构（它们是可替换的）。

### 5.13 框架设计的核心困难

第 55、58–61 页集中讨论「框架设计为什么难」。

**第 58 页：核心决策**

> **Designing a Framework**
> - **Difficult task – requires experience to do well**
> - **Once designed, little place for change**
> - **Key Decision: Separating common from variable parts**
> - **Identify hot spots vs cold spots**
> - **Too few extension points: limited to a narrow class of users**
> - **Too many extension points: hard to learn, slow**
> - **Too generic: little reuse value**

**「Once designed, little place for change」** 是框架与普通代码的**根本差别**：

| | 普通代码 | 框架 |
|---|---|---|
| 改动成本 | 改自己的代码 | 改**所有客户端**的代码 |
| 兼容性 | 不用考虑 | **必须**向后兼容 |
| 发布节奏 | 随时 | 大版本才能破坏兼容 |

**这就是为什么框架设计「requires experience」**——你必须**一次做对**，因为后来改不动。

**「hot spots vs cold spots」** 是框架设计的核心词汇（来自 Schmid 的框架设计方法）：

- **hot spot（热点）**：领域中**会变化**的部分 → 提供**扩展点**；
- **cold spot（冷点）**：领域中**不变**的部分 → **固化**在框架里。

**「Too few extension points」vs「Too many」** 是一个**双向陷阱**：

```
扩展点太少              扩展点太多
    ↓                       ↓
只能解决窄类问题        难学、慢、配置复杂
用户觉得「不够用」      用户觉得「太重」
```

**这与第 59 页的「使用 vs 复用困境」是同一个问题的两面**。

**第 59 页：Szyperski 的警句**

> **Use vs. Reuse Dilemma**
> - (for Frameworks, Libraries, Components, …)
> - **Large rich components are very useful, but rarely fit**
> - **Small or extremely generic components often fit, but provide little benefit**
> - **"maximizing reuse minimizes use"** —— C. Szyperski

**「maximizing reuse minimizes use」是本讲最精辟的一句**。它的意思是：

- 组件越**通用**（能复用的场景越多），它对**每个具体场景**的帮助就越小；
- 组件越**专用**（对某个场景帮助越大），它能复用的场景就越少。

**这是一个根本的张力，无法消除**。因为：

```
通用组件 = 抽象掉所有具体细节 = 对具体问题帮助有限
专用组件 = 针对具体问题优化 = 换个问题就不能用
```

**框架设计者的应对**：**分层**（第 56 页）。底层接口通用（`Figure`），中层骨架类半通用（`AbstractFigure`），上层 kit 专用（`LineConnection`）。这样不同用户各取所需。

**第 60 页：领域工程**

> **Domain Engineering**
> - **Think of possible users/customers in your domain**
> - **What might they need? What extensions are likely?**
> - **Collect example applications before starting a framework/component**
> - **Make a conscious decision what to support (called "scoping")**
> - **Eclipse Policy:**
>   - **"Internal" interfaces at first (unsupported, may change)**
>   - **Public stable extension points only with at least two "customers"**

**「Collect example applications before starting a framework」** 是极实用的建议——它把 5.11 节的「演化」原则操作化了：**先写三个应用，再抽框架**。

**Eclipse 的政策尤其值得学习**：

| 政策 | 含义 | 为什么 |
|---|---|---|
| 「Internal」接口先上（不承诺支持，可改） | 新 API 先标 `internal` | 观察它是否真的有用、是否稳定 |
| 有**至少两个**客户才升为 public | 两个独立使用者的需求才可信 | **一个**用户的需求可能是特例；**两个**用户的需求才有共性 |

**「at least two customers」是一个可操作的经验法则**。它直接对抗「过早抽象」——只有一个用例时，你无法区分「共性」与「偶然」。这与第 11 讲的 **Modular Decomposability** 一致：好的模块划分需要**足够的证据**。

**第 61 页：领域工程练习**

> **Domain Engineering Exercises**
> - **Think about a framework for:**
>   - **Video playing software**
>   - **Viewing, printing, editing a portable document format**
>   - **Compression and archiving software**
>   - **Instant messaging software**
>   - **Music editing software**
> - **Questions**
>   - **What are the dimensions of variability/extensibility?**
>   - **What interfaces would you need?**
>   - **What are the core methods for each interface?**
>   - **How do you set up the framework?**

**四个问题正是框架设计的完整流程**：

1. **变化维度是什么？**（找 hot spots）
2. **需要哪些接口？**（每个 hot spot 一个接口）
3. **每个接口的核心方法是什么？**（最小接口，第 11 讲 Small Interfaces）
4. **框架怎么装配？**（谁写 `main`、怎么加载插件，第 5.10 节）

**以「压缩归档软件」为例**（笔记自答）：

| 问题 | 答案 |
|---|---|
| 变化维度 | 压缩算法（zip/tar/7z）、加密方式、分卷策略、进度显示 |
| 接口 | `Compressor`（`compress(InputStream, OutputStream)`）、`Encryptor`、`ProgressListener` |
| 核心方法 | `Compressor`: `compress`/`decompress`/`extension()`；`ProgressListener`: `progress(long done, long total)` |
| 装配 | 客户端写 `main` + 配置（选算法）；或读配置文件 |

**注意「进度显示」也是变化维度**——这正是 Hadoop 的 `Reporter` 存在的原因（5.6 节）。

**第 62 页：框架设计的技术手段**

> **Framework Design**
> - **After identifying common and variable parts**
> - **Common parts go into the framework**
> - **Provide plug-in interface/extension/callback mechanisms for variable parts**
> - **Use design patterns: Strategy, Decorator, Observer, Command, Template Method, Factories …**

**这一页把整门课串起来了**：框架设计 = 识别共性与可变 + **用设计模式实现扩展点**。

| 扩展点类型 | 用哪个模式 |
|---|---|
| 可替换算法 | **Strategy** |
| 可叠加功能 | **Decorator** |
| 事件通知 | **Observer** |
| 可撤销操作 / 菜单项 | **Command** |
| 骨架 + 钩子 | **Template Method** |
| 可替换创建逻辑 | **Factory** |
| 访问者 / 双分派 | **Visitor**（第 10–12 页） |
| 解耦多方交互 | **Mediator**（第 1–3 页） |

**这就是为什么第 7–9 讲要花那么多时间讲设计模式**——它们是**框架的建材**。

### 5.14 框架的维护困难

第 55 页（credit: Erich Gamma）是本讲最「诚实」的一页：

> **Framework Challenges**（credit: Erich Gamma）
> - **frameworks are hard to maintain**
> - **framework enables reuse of both design and implementation**
> - **easy for clients to add implementation dependencies**
> - **"what is the framework - what is just default implementation"**
> - **therefore:**
>   - **separation of design from implementation**
>   - "we believe that interface design and functional factoring constitute the key intellectual content of software and that they are far more difficult to create or re-create than code" —— **Peter Deutsch**
> - **late commitment to implementation**
> - **but, frameworks still have to work out of the box!**

**逐条解读**：

**「frameworks are hard to maintain」** —— 因为改框架 = 改所有客户端。这是**规模效应**：库的一个 bug 影响一个调用点，框架的一个 bug 影响**所有**应用。

**「easy for clients to add implementation dependencies」** —— 这是**白盒框架的致命问题**。客户端继承 `TextEditor` 后，可能无意中依赖了 `TextEditor` 的**实现细节**（比如某个 `protected` 字段的语义）。框架升级时这些细节一变，客户端就崩。**这是「继承是强耦合」在框架层面的体现**（第 11 讲第 16–17 页：「subclassing 是特别糟的耦合」）。

**「what is the framework - what is just default implementation」** —— 这是**语义模糊**问题。客户端看到一个 `protected` 方法，不知道它是：

- **框架契约的一部分**（必须按某种方式覆写）？
- 还是**只是一个默认实现**（可以随意覆写）？

**这个模糊性是框架维护困难的根源**。解决办法是**明确文档化** + **分离设计实现**（`Framework Package` 的接口 vs `Defaults Package` 的抽象类，第 56 页）。

**Peter Deutsch 的引文**是本讲的哲学核心：

> **"we believe that interface design and functional factoring constitute the key intellectual content of software and that they are far more difficult to create or re-create than code"**

翻译：**「接口设计与功能分解构成软件的智识核心，它们比代码本身更难创造或重建。」**

**这句话解释了整门课为什么这样安排**：

- 为什么讲封装、继承、类型（第 2–4 讲）——它们是**接口设计**的基础；
- 为什么讲契约与规格（第 5、8 讲）——**接口就是契约**；
- 为什么讲设计模式（第 7、9 讲）——它们是**功能分解**的成熟方案；
- 为什么讲 GRASP 与信息隐藏（第 11 讲）——**功能分解的原则**；
- 为什么讲框架（本讲）——**接口设计与功能分解的集大成**。

**「late commitment to implementation」 vs「must work out of the box」** 是最后一对张力：

```
延迟实现承诺 ←──────────────→ 开箱即用
（灵活性、可替换）            （可用性、低门槛）
```

框架想让你**晚点决定**（所以有扩展点），但又必须**现在就能跑**（所以有默认实现）。**这两个要求同时满足的唯一方式**就是第 56 页的三层分层——默认实现在 `Defaults Package`，接口在 `Framework Package`。

### 5.15 学习框架的技巧

第 63 页（"Getting up a framework's learning curve"）给出实用建议：

> - **Tips on using frameworks**
>   - **Tutorials, Wizards, and Examples**
>     - **SourceForge, Google Code Search**
>   - **Communities – email lists and forums**
>     - **Eclipse.org**
>   - **Group knowledge dispersal**
>     - **Wiki of resources, Problem/solution log**
> - **Common client trick: Follow the leader**
>   - **Appropriate code from examples – find an "imputed pattern"**
>     - **Search source code**
>     - **Infer compatible intent**
>     - **Identify scope (not too much, not too little)**
>   - **Copy it**
>     - **Tear out the app-specific logic, keep the bureaucracy**
>     - **Insert your own logic into the reused bureaucracy**
> - **But there's a problem**
>   - **Classic copy-and-paste problem – looks just like my own code**
>   - **Design intent is lost – "my intention is to use the framework this way"**
> - **Framework designer's conundrum: complexity vs. capability**

**「Follow the leader」是真实世界最常用的框架学习法**：找一个能跑的示例，**复制、删掉业务逻辑、填自己的**。

课件很诚实地指出了它的**问题**：

- **「looks just like my own code」** —— 复制来的代码看起来像自己写的，于是**没人知道**它是框架要求的「仪式（bureaucracy）」；
- **「Design intent is lost」** —— 你**为什么**要这样写（「框架要求我先调 `super.init()`」）丢失了，于是后人可能「优化」掉它，导致崩溃。

**「keep the bureaucracy」这个说法很传神**——框架要求的样板代码就是**官僚程序**，它看起来冗余，但**删了就出事**。

**这与第 8 讲「代码即文档」的问题同构**：一段代码**为什么**这样写，如果不在注释/文档里，就会丢失。

**「Framework designer's conundrum: complexity vs. capability」**（图上：`effort` vs `reward`，`Library` 与 `Framework` 两条曲线）：

```
reward
  ↑
  │        ╱ Framework（起步慢，上限高）
  │      ╱
  │    ╱      ╱ Library（起步快，上限低）
  │  ╱      ╱
  │╱      ╱
  └──────────────→ effort
```

**这个图说清了库与框架的投入产出**：

- **库**：学习成本低，但**天花板也低**（只能复用实现）；
- **框架**：学习成本高（要学协议、要读文档、要理解架构），但**天花板高**（复用架构 + 内化质量属性）。

**「conundrum（难题）」在于**：你**无法预先知道**一个项目会不会撞到天花板。如果项目小，用框架是**浪费**；如果项目大，不用框架是**灾难**。

**这就是为什么框架设计需要经验**（第 58 页）——判断「这个领域值不值得做框架」需要见过足够多的项目。

### 5.16 框架设计建议

第 64 页给出五条可操作建议：

> **Framework Design Advice**
> - **It's hard to understand framework code**
> - **So ensure it can be understood from the documentation**
>   - **Preconditions, postconditions, exceptions, order of calls, …**
> - **Keep the interface narrow**
>   - **Don't make methods package-public unless used by clients**
> - **Help your users**
>   - **Provide example plugins**
>   - **Check parameters defensively for validity**

**五条建议对应五个原则**：

| 建议 | 对应原则 |
|---|---|
| 文档必须包含前置/后置/异常/**调用顺序** | 第 5、8 讲的**契约**；`order of calls` = **protocol** |
| 保持接口窄 | 第 11 讲 **Small Interfaces** |
| 不要随便 `public` | 第 11 讲 **Information Hiding** |
| 提供示例插件 | 第 5.15 节「Follow the leader」 |
| 防御性检查参数 | 第 6 讲**防御性编程**；第 8 讲「robust libraries」 |

**「Don't make methods package-public unless used by clients」** 特别值得注意——这是**信息隐藏**在包级别的应用。`package-private` 方法看似「内部」，但同包的其他类可以调，一旦有人依赖就难改。所以**默认应该 `private`**，只在确有必要时放宽。

**「Check parameters defensively for validity」** 与第 8 讲第 16 页的批注一致：「Check arguments even when assertions are disabled. Good for robust libraries!」——框架是**库**的一种，所以这条完全适用。

### 5.17 Swing 与 Servlet：两个真实的框架案例

第 45–53 页用 Swing 与 Servlet 收尾，展示「库与框架的边界是模糊的」。

**第 45 页：Swing 是库**

> **Java Swing: It's a Library!**
> - **Create a GUI using pre-defined containers**
>   - **`JFrame`, `JPanel`, `JDialog`, `JMenuBar`**
> - **Use a layout manager to organize components in the container**
> - **Add pre-defined components to the layout**
>   - **Components: `JLabel`, `JTextField`, `JButton`**
> - **This is no different that the File I/O library!**

**「This is no different than the File I/O library!」** —— 从**创建组件、设置布局、添加组件**的角度看，Swing 完全是库：你调它，它返回。

**第 46–47 页：库式用法**

```java
// create the container
JPanel panel = new JPanel();
// create the label, add to the container
JLabel label = new JLabel();
label.setText("Enter your userid:");
panel.add(label);
// create a text field, add to the container
JTextField textfield = new JTextField(16);
panel.add(textfield)
```

```java
panel.setLayout(new GridBagLayout());
GridBagConstraints c = new GridBagConstraints();
// create and position the button
JButton button = new JButton("Click Me!");
c.fill = GridBagConstraints.HORIZONTAL;
c.gridx = 0;      // first column
c.gridy = 1;      // second row
c.gridwidth = 2;  // span two columns
c.weightx = 1.0;  // use all horizontal space
c.anchor = GridBagConstraints.WEST;
c.insets = new Insets(0,5,0,5); // add side padding
pane.add(button, c);
```

**第 48 页：但事件是框架**

```java
// create an anonymous MouseAdapter, which extends
// the MouseListener class
button.add(new MouseAdapter () {
  public void mouseClicked(MouseEvent e) {
    System.err.println("You clicked me! " +
        "Do it again!")
  }
});
```

课件批注（关键提问）：

> **But this extending a class to add custom behaviors, right?**

**这个问题很尖锐**：`new MouseAdapter() { ... }` 是**匿名内部类**，它**继承**了 `MouseAdapter`。所以 Swing 的事件机制**既是** Observer（`addMouseListener`）**又是**白盒（`extends MouseAdapter`）。

**为什么 Swing 提供 `MouseAdapter` 而不只是 `MouseListener` 接口？** 因为 `MouseListener` 有 **5 个方法**（`mouseClicked`、`mousePressed`、`mouseReleased`、`mouseEntered`、`mouseExited`），而你通常只关心一个。`MouseAdapter` 提供了**全部 5 个方法的空实现**，你只覆写关心的那个。

**这是「骨架类」的经典应用**——与第 14 讲 `AbstractList` 的「伪抽象方法」是同一手法：**提供默认实现，让子类只覆写需要的**。

**第 49 页：边界在哪里？**

> **Where is the boundary?**
>
> （图：`Container` → `JComponent` → `JPanel` → `JButton`；`EventListener` → `MouseAdapter` → `$1`；`MyWidget`）
>
> 标注：**AWT Framework** / **Swing Framework** / **Our Implementation**

**这一页是本讲的「总结图」**：它展示了**三层归属**：

| 层 | 内容 | 谁写的 |
|---|---|---|
| **AWT Framework** | `Container`、`EventListener` | JDK（AWT） |
| **Swing Framework** | `JComponent`、`JPanel`、`JButton`、`MouseAdapter` | JDK（Swing） |
| **Our Implementation** | `MyWidget`、`$1`（匿名类） | 你 |

**「Where is the boundary?」这个问题的答案**：边界**不是一条线**，而是**每层各自的一段**。你的代码继承 Swing 的类（`MyWidget extends JPanel`），Swing 又继承 AWT 的类。**每一层都既是「框架的使用者」又是「框架的提供者」**。

**这正是第 19 页「plugin trees」的含义**——插件可以再定义扩展点，形成层次。

**第 50–51 页：自定义组件的两种方式**

```java
// 方式 1：组合（把已有组件装进自己的面板）
public MyWidget extends JPanel {
  public MyWidget(int param) {
    setLayout(new GridBagLayout());
    GridBagConstraints c = new GridBagConstraints();
    …
    add(label, c);
    add(textfield, c);
    add(button, c);
  }
  public void setParameter(int param) {
    // update the widget, as needed
  }
}
```

```java
// 方式 2：自绘（覆写 paintComponent）
public MyWidget extends JContainer {
  public MyWidget(int param) {
    // setup internals, without rendering
  }
  // render component on first view and resizing
  protected void paintComponent(Graphics g) {
    // draw a red box on this component
    Dimension d = getSize();
    g.setColor(Color.red);
    g.drawRect(0, 0, d.getWidth(), d.getHeight());
  }
}
```

**两种方式的差别**：

| 方式 | 手段 | 适用 |
|---|---|---|
| **组合** | 把现有组件装进 `JPanel` | 复用现成外观 |
| **自绘** | 覆写 `paintComponent` | 需要完全自定义外观 |

**方式 2 是白盒框架的典型**：你**覆写** `paintComponent`，框架在**需要重绘时**调用它。注意批注「render component on first view and resizing」——这就是**调用时机**，即 5.4 节的 protocol。

**「Don't call us, we'll call you」在这里体现得最纯粹**：你**从不**主动调 `paintComponent`，是 Swing 在需要时调你。

> 课件第 50–51 页代码有误：`public MyWidget extends JPanel` 缺 `class` 关键字（应为 `public class MyWidget extends JPanel`）。第 51 页的 `JContainer` 也应是 `JComponent`。**笔记按原样引用并指出。**

**第 52–53 页：Servlet**

```java
package servletDemo;
import java.io.*;
import javax.servlet.*;
import javax.servlet.annotation.*;
import javax.servlet.http.*;

@WebServlet("/hello")
public class HelloWorld extends HttpServlet {
  @Override
  public void doGet(HttpServletRequest request,
                    HttpServletResponse response)
      throws ServletException, IOException {
    PrintWriter out = response.getWriter();
    out.println("Hello World");
  }
}
```

（来源标注：`http://courses.coreservlets.com/Course-Materials/csajsp2.html`）

**Servlet 是纯白盒框架**：

- 你 `extends HttpServlet`；
- 你**覆写** `doGet`；
- **容器**（Tomcat）在收到 HTTP 请求时**调用**你的 `doGet`；
- 你**从不**写 `main`——`main` 在容器里。

**生命周期**（第 53 页）：

```
容器启动
   ↓
创建 Servlet 实例（一次）
   ↓
init(ServletConfig)          ← 一次
   ↓
┌──────────────────────────┐
│ 对每个请求：              │
│   doGet / doPost / ...   │  ← 多次，可能并发
└──────────────────────────┘
   ↓
destroy()                    ← 一次
   ↓
容器关闭
```

**这个协议的关键约束**（5.4 节讨论过）：`doGet` 会被**并发**调用，所以**不能**用实例字段存请求状态。这是 Servlet 最常见的 bug，也是「协议必须写进文档」的最好例证。

**`@WebServlet("/hello")` 是黑盒式的配置**：注解替代了 `web.xml`。课件第 53 页明确说「web.xml: Alternative to `@WebServlet` annotation」——**同一个框架可以同时支持白盒（继承）与黑盒（注解配置）**。

### 5.18 总结：框架的四个维度

第 65 页的总结把整讲收成五条：

> **Summary**
> - **Frameworks capture reusable infrastructure**
> - **Hollywood principle: Don't call us, we'll call you**
> - **Different, and often deeper, reuse than libraries provide**
> - **Can often internalize qualities like reliability (cf. MapReduce)**
> - **Also challenging: framework impacts applications that use it**
> - **Framework setup**
>   - **Multiple paths: client in charge, loading plugins by reflection, …**
> - **Designing a framework**
>   - **Key issue is identifying important variability points**
> - **Learning a framework**
>   - **Leverage examples, experience of others**

**把整讲浓缩成四个维度**：

| 维度 | 核心问题 | 本讲答案 |
|---|---|---|
| **是什么** | 库与框架的差别 | **控制权**：谁控制结构与控制流。好莱坞法则 |
| **为什么** | 框架的价值 | **复用架构**（不只是实现）+ **内化质量属性**（MapReduce 的并行与容错） |
| **怎么建** | 框架设计 | **识别 hot spots vs cold spots** + 用设计模式实现扩展点 + 三层分层 + 黄金法则（不改源码） |
| **怎么用** | 学习框架 | 读文档（尤其**调用顺序**）+ Follow the leader + 注意「bureaucracy」不可删 |

**「framework impacts applications that use it」** 是最后一条警告，也是最容易被忽视的：

**框架不是中立的工具**。一旦用了框架：

- 你的**架构**被框架决定（第 54 页「architectural guidance」）；
- 你的**部署**被框架约束（要有容器、要有配置文件）；
- 你的**升级**被框架节奏绑定（框架不升级，你也不能升）；
- 你的**团队技能**要围绕框架建设。

**这就是「框架是双向的」**：它给你复用，也给你约束。第 59 页 Szyperski 的「maximizing reuse minimizes use」说的就是这个——**你复用越多，你能自主决定的部分越少**。

**选择框架是一个架构决策，不是技术细节**。这是本讲（也是整门课）最后要传达的东西。

## 6. 代码示例

### 6.1 官方课程代码

出自 `14-frameworks.pdf` 第 7–8 页（`instanceof` 反例）：

```java
class Animal { … }
class Rabbit extends Animal { … }
class Fox extends Animal { … }

void move(Animal a) {
  if (a instanceof Rabbit)
    // move like a Rabbit
  if (a instanceof Fox)
    // move like a Fox
}
void eat(Animal a) {
  if (a instanceof Rabbit)
    // eat like a Rabbit
  if (a instanceof Fox)
    // eat like a Fox
}
```

```java
abstract class Animal { … }
class Rabbit extends Animal { … }
class Fox extends Animal { … }
class Wolf extends Animal { … }

void move(Animal a) {
  if (a instanceof Rabbit)
    // move like a Rabbit
  if (a instanceof Fox)
    // move like a Fox
  if (a instanceof Wolf)
    // move like a Wolf
}
void eat(Animal a) {
  if (a instanceof Rabbit)
    // eat like a Rabbit
  if (a instanceof Fox)
    // eat like a Fox
  if (a instanceof Wolf)
    // eat like a Wolf
}
```

出自第 9 页（替代方案一：多态分派）：

```java
interface Animal {
  void move();
  void eat();
}
class Rabbit extends Animal {
  void move() { /* move like a Rabbit */}
  void eat() { /* eat like a Rabbit */}
}
class Fox extends Animal {
  void move() { /* move like a Fox */}
  void eat() { /* eat like a Fox */}
}
class Wolf extends Animal {
  void move() { /* move like a Wolf */}
  void eat() { /* eat like a Wolf */}
}
```

出自第 10–12 页（替代方案二：Visitor 模式）：

```java
interface Animal {
  void visit(AnimalVisitor v);
}
interface AnimalVisitor {
  void visitRabbit(Rabbit r);
  void visitFox(Fox f);
  void visitWolf(Wolf w);
}
class Rabbit extends Animal { …}
class Fox extends Animal { …}
class Wolf extends Animal {
  void visit(AnimalVisitor v) {
    v.visitWolf(this);
  }
}
class MoveVisitor implements Visitor {
  void visitRabbit(Rabbit r) { … }
  void visitFox(Fox f) { … }
  void visitWolf(Wolf w) {
  /* move like a Wolf */ }
}
class EatVisitor implements Visitor {
  void visitRabbit(Rabbit r) { … }
  void visitFox(Fox f) { … }
  void visitWolf(Wolf w) {
  /* eat like a Wolf */ }
}
```

出自第 26 页（无框架的 `Calc`）：

```java
public class Calc extends JFrame {
  private JTextField textfield;

  public static void main(String[] args) { new Calc().setVisible(true); }
  public Calc() { init(); }

  protected void init() {
    JPanel contentPane = new JPanel(new BorderLayout());
    contentPane.setBorder(new BevelBorder(BevelBorder.LOWERED));

    JButton button = new JButton();
    button.setText("calculate");
    contentPane.add(button, BorderLayout.EAST);

    textfield = new JTextField("");
    textfield.setText("10 / 2 + 6");
    textfield.setPreferredSize(new Dimension(200, 20));
    contentPane.add(textfield, BorderLayout.WEST);

    button.addActionListener(/* code zum berechnen */);

    this.setContentPane(contentPane);
    this.pack();
    this.setLocation(100, 100);
    this.setTitle("My Great Calculator");
    // impl. for closing the window
  }
}
```

出自第 28 页（白盒框架 `Application` + 两个应用）：

```java
public abstract class Application extends JFrame {
  protected abstract String getApplicationTitle();
  protected abstract String getButtonText();
  protected String getInititalText() {return "";}
  protected void buttonClicked() { }

  private JTextField textfield;

  public Application() { init(); }

  protected void init() {
    JPanel contentPane = new JPanel(new BorderLayout());
    contentPane.setBorder(new BevelBorder(BevelBorder.LOWERED));

    JButton button = new JButton();
    button.setText(getButtonText());
    contentPane.add(button, BorderLayout.EAST);

    textfield = new JTextField("");
    textfield.setText(getInititalText());
    textfield.setPreferredSize(new Dimension(200, 20));
    contentPane.add(textfield, BorderLayout.WEST);

    button.addActionListener(/* … buttonClicked(); … */);

    this.setContentPane(contentPane);
    this.pack();
    this.setLocation(100, 100);
    this.setTitle(getApplicationTitle());
    // impl. for closing the window
  }

  protected String getInput() { return textfield.getText();}
}

public class Calculator extends Application {
  protected String getButtonText() { return "calculate"; }
  protected String getInititalText() { return "(10 – 3) * 6"; }
  protected void buttonClicked() {
    JOptionPane.showMessageDialog(this, "The result of "+getInput()+
        " is "+calculate(getInput())); }
  protected String getApplicationTitle() { return "My Great Calculator"; }
  public static void main(String[] args) {
    new Calculator().setVisible(true);
  }
}

public class Ping extends Application {
  protected String getButtonText() { return "ping"; }
  protected String getInititalText() { return "127.0.0.1"; }
  protected void buttonClicked() {  /* … */  }
  protected String getApplicationTitle() { return "Ping"; }
  public static void main(String[] args) {
    new Ping().setVisible(true);
  }
}
```

出自第 30 页（黑盒框架 `Application` + `Plugin` + `CalcPlugin`）：

```java
public class Application extends JFrame {
  private JTextField textfield;
  private Plugin plugin;

  public Application(Plugin p) { this.plugin=p; p.setApplication(this); init(); }

  protected void init() {
    JPanel contentPane = new JPanel(new BorderLayout());
    contentPane.setBorder(new BevelBorder(BevelBorder.LOWERED));

    JButton button = new JButton();
    if (plugin != null)
      button.setText(plugin.getButtonText());
    else
      button.setText("ok");
    contentPane.add(button, BorderLayout.EAST);

    textfield = new JTextField("");
    if (plugin != null)
      textfield.setText(plugin.getInititalText());
    textfield.setPreferredSize(new Dimension(200, 20));
    contentPane.add(textfield, BorderLayout.WEST);

    if (plugin != null)
      button.addActionListener(/* … plugin.buttonClicked();… */);

    this.setContentPane(contentPane);
    …
  }

  public String getInput() { return textfield.getText();}
}

public interface Plugin {
  String getApplicationTitle();
  String getButtonText();
  String getInititalText();
  void buttonClicked() ;
  void setApplication(Application app);
}

public class CalcPlugin implements Plugin {
  private Application application;
  public void setApplication(Application app) { this.application = app; }
  public String getButtonText() { return "calculate"; }
  public String getInititalText() { return "10 / 2 + 6"; }
  public void buttonClicked() {
    JOptionPane.showMessageDialog(null, "The result of "
        + application.getInput() + " is "
        + calculate(application.getText())); }
  public String getApplicationTitle() { return "My Great Calculator"; }
}

class CalcStarter {  public static void main(String[] args) {
  new Application(new CalcPlugin()).setVisible(true); }}
```

出自第 33 页（用反射按类名加载插件）：

```java
public static void main(String[] args) {
  if (args.length != 1) {
    System.out.println("Plugin name not specified");
  } else {
    String pluginName = args[0];
    try {
      Class<?> pluginClass = Class.forName(pluginName);
      Plugin plugin = (Plugin) pluginClass.newInstance();
      new Application(plugin).setVisible(true);
    } catch (Exception e) {
      System.out.println("Cannot load plugin " + pluginName
          + ", reason: " + e);
    }
  }
}
```

出自第 34 页（读配置文件加载多个插件）：

```java
public static void main(String[] args) {
  File config = new File(".config");
  BufferedReader reader = new BufferedReader(new FileReader(config));
  Application = new Application();
  String pluginName = null;
  while ((pluginName = reader.readLine()) != null) {
    try {
      Class<?> pluginClass = Class.forName(pluginName);
      application.addPlugin((Plugin) pluginClass.newInstance());
    } catch (Exception e) {
      System.out.println("Cannot load plugin " + pluginName
          + ", reason: " + e);
    }
  }
  reader.close();
  application.setVisible(true);
}
```

出自第 36 页（多插件 + 链式处理）：

```java
public class Application {
  private List<Plugin> plugins;

  public Application(List<Plugin> plugins) {
    this.plugins=plugins;
    for (Plugin plugin: plugins)
      plugin.setApplication(this);
  }

  public Message processMsg (Message msg) {
    for (Plugin plugin: plugins)
      msg = plugin.process(msg);
    ...
    return msg;
  }
}
```

出自第 41–42 页（Eclipse 插件的 Manifest 与 `plugin.xml`）：

```
Manifest-Version: 1.0
Bundle-ManifestVersion: 2
Bundle-Name: MyEditor Plug-in
Bundle-SymbolicName: MyEditor; singleton:=true
Bundle-Version: 1.0.0
Bundle-Activator: myeditor.Activator
Require-Bundle: org.eclipse.ui,
 org.eclipse.core.runtime,
 org.eclipse.jface.text,
 org.eclipse.ui.editors
Bundle-ActivationPolicy: lazy
Bundle-RequiredExecutionEnvironment:
 JavaSE-1.6
```

```xml
<?xml version="1.0" encoding="UTF-8"?>
<?eclipse version="3.2"?>
<plugin>
  <extension
    point="org.eclipse.ui.editors">
    <editor
      name="Sample XML Editor"
      extensions="xml"
      icon="icons/sample.gif"
      contributorClass="org.eclipse.ui.texteditor.BasicTextEditorActionContributor"
      class="myeditor.editors.XMLEditor"
      id="myeditor.editors.XMLEditor">
    </editor>
  </extension>
</plugin>
```

出自第 43 页（Eclipse 编辑器插件本体）：

```java
package myeditor.editors;
import org.eclipse.ui.editors.text.TextEditor;

public class XMLEditor extends TextEditor {
  private ColorManager colorManager;

  public XMLEditor() {
    super();
    colorManager = new ColorManager();
    setSourceViewerConfiguration(
        new XMLConfiguration(colorManager));
    setDocumentProvider(
        new XMLDocumentProvider());
  }

  public void dispose() {
    colorManager.dispose();
    super.dispose();
  }
}
```

出自第 44 页（JUnit 用注解作插件机制）：

```java
public class SampleTest  {
  private List<String> emptyList;

  @Before
  public void setUp() {
    emptyList = new ArrayList<String>();
  }

  @After
  public void tearDown() {
    emptyList = null;
  }

  @Test
  public void testEmptyList() {
    assertEquals("Empty list should have 0 elements",
        0, emptyList.size());
  }
}
```

课件批注：「**Here the important plugin mechanism is Java annotations**」。

出自第 46–48 页（Swing 的库式用法与事件）：

```java
// create the container
JPanel panel = new JPanel();
// create the label, add to the container
JLabel label = new JLabel();
label.setText("Enter your userid:");
panel.add(label);
// create a text field, add to the container
JTextField textfield = new JTextField(16);
panel.add(textfield)
```

```java
panel.setLayout(new GridBagLayout());
GridBagConstraints c = new GridBagConstraints();
// create and position the button
JButton button = new JButton("Click Me!");
c.fill = GridBagConstraints.HORIZONTAL;
c.gridx = 0;      // first column
c.gridy = 1;      // second row
c.gridwidth = 2;  // span two columns
c.weightx = 1.0;  // use all horizontal space
c.anchor = GridBagConstraints.WEST;
c.insets = new Insets(0,5,0,5); // add side padding
pane.add(button, c);
```

```java
// create an anonymous MouseAdapter, which extends
// the MouseListener class
button.add(new MouseAdapter () {
  public void mouseClicked(MouseEvent e) {
    System.err.println("You clicked me! " +
        "Do it again!")
  }
});
```

出自第 50–51 页（自定义组件的两种方式）：

```java
public MyWidget extends JPanel {
  public MyWidget(int param) {
    setLayout(new GridBagLayout());
    GridBagConstraints c = new GridBagConstraints();
    …
    add(label, c);
    add(textfield, c);
    add(button, c);
  }
  public void setParameter(int param) {
    // update the widget, as needed
  }
}
```

```java
public MyWidget extends JContainer {
  public MyWidget(int param) {
    // setup internals, without rendering
  }
  // render component on first view and resizing
  protected void paintComponent(Graphics g) {
    // draw a red box on this component
    Dimension d = getSize();
    g.setColor(Color.red);
    g.drawRect(0, 0, d.getWidth(), d.getHeight());
  }
}
```

出自第 52 页（Servlet）：

```java
package servletDemo;
import java.io.*;
import javax.servlet.*;
import javax.servlet.annotation.*;
import javax.servlet.http.*;

@WebServlet("/hello")
public class HelloWorld extends HttpServlet {
  @Override
  public void doGet(HttpServletRequest request,
                    HttpServletResponse response)
      throws ServletException, IOException {
    PrintWriter out = response.getWriter();
    out.println("Hello World");
  }
}
```

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：同一个功能，库版 vs 框架版**

```java
// ========== 库版：客户端控制一切 ==========
public final class CsvLib {
    public static List<String[]> parse(String text) {
        List<String[]> rows = new ArrayList<>();
        for (String line : text.split("\n")) rows.add(line.split(","));
        return rows;
    }
    public static int countRows(List<String[]> rows) { return rows.size(); }
    public static String column(List<String[]> rows, int i, int r) {
        return rows.get(r)[i];
    }
}

// 客户端：自己决定顺序、次数、何时停
public class LibClient {
    public static void main(String[] args) {
        List<String[]> rows = CsvLib.parse(readFile("data.csv"));
        System.out.println("rows = " + CsvLib.countRows(rows));
        System.out.println("first = " + CsvLib.column(rows, 0, 0));
    }
}
```

```java
// ========== 框架版：框架控制一切，你只填两个钩子 ==========
public interface RowHandler {
    void start();                        // 生命周期：开始
    void handle(int rowIndex, String[] cells);   // 回调：每一行
    void finish();                       // 生命周期：结束
}

public final class CsvFramework {
    private final RowHandler handler;
    public CsvFramework(RowHandler handler) { this.handler = handler; }

    // 框架写 main 的等价物：控制整个流程
    public void run(String text) {
        handler.start();                            // 框架调用你
        String[] lines = text.split("\n");
        for (int i = 0; i < lines.length; i++) {
            handler.handle(i, lines[i].split(",")); // 框架调用你
        }
        handler.finish();                           // 框架调用你
    }
}

// 客户端：只写插件，不写 main 的流程
public class SumColumnPlugin implements RowHandler {
    private long sum;
    public void start()  { sum = 0; }
    public void handle(int rowIndex, String[] cells) {
        sum += Long.parseLong(cells[2].trim());     // 第 3 列求和
    }
    public void finish() { System.out.println("sum = " + sum); }

    public static void main(String[] args) {
        new CsvFramework(new SumColumnPlugin()).run(readFile("data.csv"));
    }
}
```

**对比**：

| | 库版 | 框架版 |
|---|---|---|
| 谁遍历行 | 客户端 | **框架** |
| 客户端写什么 | 完整流程 | 三个钩子 |
| 加「跳过表头」 | 改客户端 | 改框架（**所有**客户端受益） |
| 加「进度显示」 | 每个客户端自己写 | 框架加一个钩子，客户端选用 |

框架版的 `handle` 就是 **callback**，`start`/`finish` 就是 **lifecycle method**，`run` 的调用序列就是 **protocol**。

**示例 B：白盒版（子类化）**

```java
public abstract class AbstractCsvApp {
    // 抽象方法：子类必须实现
    protected abstract void handle(int rowIndex, String[] cells);

    // 钩子：有默认实现，子类可选覆写
    protected void start()  { }
    protected void finish() { }

    // 骨架：final，子类不能改流程
    public final void run(String text) {
        start();
        String[] lines = text.split("\n");
        for (int i = 0; i < lines.length; i++) handle(i, lines[i].split(","));
        finish();
    }
}

public class SumColumnApp extends AbstractCsvApp {
    private long sum;
    @Override protected void start() { sum = 0; }
    @Override protected void handle(int i, String[] cells) {
        sum += Long.parseLong(cells[2].trim());
    }
    @Override protected void finish() { System.out.println("sum = " + sum); }

    public static void main(String[] args) {
        new SumColumnApp().run(readFile("data.csv"));
    }
}
```

**`run` 声明为 `final` 是关键**——它保证子类**不能**改流程（否则就不是框架了）。这是 Template Method 的标准做法。

**白盒 vs 黑盒的取舍**：

| | 白盒（`extends AbstractCsvApp`） | 黑盒（`implements RowHandler`） |
|---|---|---|
| 子类能改什么 | 所有非 `final` 方法 | 只有接口方法 |
| 能否继承别的类 | ✗（Java 单继承） | ✓ |
| 能否运行时换行为 | ✗ | ✓（换一个 handler 对象） |
| 需要读源码吗 | 可能要（`start` 何时被调） | 不用（接口说明一切） |

**示例 C：黄金法则的三种实现**

```java
// ---------- 方式 A：客户端写 main ----------
public class MainA {
    public static void main(String[] args) {
        new CsvFramework(new SumColumnPlugin()).run(readFile("data.csv"));
    }
}

// ---------- 方式 B：框架写 main，插件类名从命令行来 ----------
public class MainB {
    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            System.err.println("usage: java MainB <plugin-class>");
            return;
        }
        RowHandler h = (RowHandler) Class.forName(args[0])
                                        .getDeclaredConstructor()
                                        .newInstance();
        new CsvFramework(h).run(readFile("data.csv"));
    }
}
// 运行：java MainB SumColumnPlugin

// ---------- 方式 C：框架读「魔法位置」 ----------
public class MainC {
    public static void main(String[] args) throws Exception {
        Properties cfg = new Properties();
        try (InputStream in = Files.newInputStream(Paths.get("app.properties"))) {
            cfg.load(in);
        }
        List<RowHandler> handlers = new ArrayList<>();
        for (String cls : cfg.getProperty("plugins", "").split(",")) {
            if (cls.isBlank()) continue;
            handlers.add((RowHandler) Class.forName(cls.trim())
                                           .getDeclaredConstructor()
                                           .newInstance());
        }
        new CsvFramework(new CompositeHandler(handlers)).run(readFile("data.csv"));
    }
}
// app.properties: plugins=SumColumnPlugin,CountRowsPlugin
```

三种方式**框架源码都不需要改**——这就是黄金法则。

**注意方式 B/C 的 `getDeclaredConstructor().newInstance()`** 而非课件用的 `newInstance()`：后者在 Java 9 被废弃（因为它会把构造器抛的异常原样抛出，包括受检异常，破坏类型系统）。现代写法更安全。这是 2013 年之后的变化。

**示例 D：`instanceof` 的三种改法**

```java
// ---------- 原始：一串 instanceof ----------
void move(Animal a) {
    if (a instanceof Rabbit) { /* ... */ }
    else if (a instanceof Fox) { /* ... */ }
    else if (a instanceof Wolf) { /* ... */ }
    // 加 Grass 时忘了改这里 → bug
}

// ---------- 改法 1：多态（适合「操作固定、类型常变」）----------
interface Animal { void move(); void eat(); }
class Rabbit implements Animal {
    public void move() { /* ... */ }
    public void eat()  { /* ... */ }
}
// 加新类型：写一个新类即可，编译器强制实现 move/eat

// ---------- 改法 2：Visitor（适合「类型固定、操作常变」）----------
interface AnimalVisitor<R> {
    R visitRabbit(Rabbit r);
    R visitFox(Fox f);
    R visitWolf(Wolf w);
}
interface Animal { <R> R accept(AnimalVisitor<R> v); }
class Rabbit implements Animal {
    public <R> R accept(AnimalVisitor<R> v) { return v.visitRabbit(this); }
}
// 加新操作：写一个新 visitor 即可，编译器强制实现所有 visitXxx

// ---------- 改法 3：合法的 instanceof（单个类型守卫）----------
@Override public boolean equals(Object obj) {
    if (this == obj) return true;
    if (!(obj instanceof Rabbit)) return false;   // ← 这是好的用法
    Rabbit r = (Rabbit) obj;
    return name.equals(r.name);
}
```

**三种改法的判据**：

| 情形 | 用什么 |
|---|---|
| 按类型分派**多个**分支，类型会加 | **多态** |
| 按类型分派**多个**分支，操作会加 | **Visitor** |
| 只是**一个**类型守卫（`equals`、`compareTo`） | **保留 `instanceof`** |

第三种是课件第 4 页明确认可的：「Often OK if you are testing against just one thing」。

**示例 E：插件协议违规的三种典型 bug**

```java
// ---------- bug 1：在构造器里依赖子类字段（白盒框架陷阱）----------
public abstract class BadFramework {
    protected String name;                     // 子类字段（在 super() 之后才初始化）
    public BadFramework() {
        init();                                // ← 调用可覆写方法
    }
    protected void init() { System.out.println(name.length()); }  // NPE!
}
public class BadPlugin extends BadFramework {
    public BadPlugin() {
        super();
        name = "plugin";                       // ← 太晚了，init() 已经跑完
    }
}
// 修复：不要在构造器里调用可覆写方法；或改为两阶段初始化

// ---------- bug 2：在回调里用实例字段存请求状态（Servlet 陷阱）----------
public class BadServlet extends HttpServlet {
    private String currentUser;                // ← 危险！多线程共享
    @Override public void doGet(HttpServletRequest req, HttpServletResponse resp) {
        currentUser = req.getParameter("user");  // 线程 A
        // ... 线程 B 在这里覆盖了 currentUser ...
        log("user = " + currentUser);            // ← 可能是 B 的用户
    }
}
// 修复：把请求相关状态放在局部变量里

// ---------- bug 3：在错误的生命周期阶段做重活（Swing 陷阱）----------
public class BadPanel extends JPanel {
    @Override protected void paintComponent(Graphics g) {
        super.paintComponent(g);
        byte[] data = downloadFromNetwork();     // ← 在 GUI 线程上做 IO！
        g.drawString(new String(data), 10, 10);  // 界面卡死
    }
}
// 修复：用 SwingWorker 在后台线程取数据，完成后 repaint()
```

三个 bug 分别对应本讲的三个概念：

| bug | 违反的协议 |
|---|---|
| 1 | 白盒框架的**调用时机**（`init()` 在字段初始化前被调） |
| 2 | Servlet 的**并发约束**（`doGet` 可能并发） |
| 3 | Swing 的**线程约束**（`paintComponent` 在 GUI 线程） |

**三者都编译通过、都不报类型错误**——这正是框架「协议」无法被类型系统检查的证明（5.4 节）。

**示例 F：框架的三层分层**

```java
// ========== Framework Package：稳定、无实现 ==========
package framework;

public interface Figure {                       // 最稳定
    void draw(Graphics g);
    Rectangle bounds();
}

public interface Drawing {
    void add(Figure f);
    void drawAll(Graphics g);
}

// ========== Defaults Package：半实现、protected 接口 ==========
package framework.defaults;

import framework.*;

public abstract class AbstractFigure implements Figure {
    protected int x, y;                          // protected：给子类用
    protected AbstractFigure(int x, int y) { this.x = x; this.y = y; }
    @Override public Rectangle bounds() {
        return new Rectangle(x, y, width(), height());
    }
    protected abstract int width();              // 钩子
    protected abstract int height();             // 钩子
}

public class StandardDrawing implements Drawing {
    private final List<Figure> figures = new ArrayList<>();
    @Override public void add(Figure f) { figures.add(f); }
    @Override public void drawAll(Graphics g) {
        for (Figure f : figures) f.draw(g);
    }
}

// ========== Kit Package：具体实现、最不稳定 ==========
package framework.kit;

import framework.defaults.AbstractFigure;
import java.awt.*;

public class LineFigure extends AbstractFigure {
    private final int x2, y2;
    public LineFigure(int x1, int y1, int x2, int y2) {
        super(x1, y1);
        this.x2 = x2; this.y2 = y2;
    }
    @Override protected int width()  { return Math.abs(x2 - x); }
    @Override protected int height() { return Math.abs(y2 - y); }
    @Override public void draw(Graphics g) { g.drawLine(x, y, x2, y2); }
}
```

**客户端应该依赖哪一层？**

```java
// ✓ 好：只依赖 framework 包（接口）
import framework.Figure;
import framework.Drawing;

// △ 可接受：需要复用实现时继承 defaults 包
import framework.defaults.AbstractFigure;

// ✗ 坏：依赖 kit 包的内部结构（它随时可能被替换）
import framework.kit.LineFigure;
```

**这就是第 56 页三层分层的实践含义**：**稳定性决定依赖方向**。依赖越稳定的东西，你的代码越稳定。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| **库（Library）** | **框架（Framework）** | 前者**客户端**控制结构与控制流（你调它）；后者**框架**控制（它调你）。判据是**控制权**，不是代码量 |
| **「调用库」** | **「被框架调用」** | 前者是**单向**（客户端 → 库）；后者是**双向**（客户端 → 框架 + 框架 → 客户端回调）。双向是框架的本质 |
| **好莱坞法则** | **依赖倒置原则** | 前者是框架的**行为特征**（"Don't call us, we'll call you"）；后者是**设计原则**（依赖抽象而非具体）。两者常一起出现但不等价 |
| **API** | **Protocol** | 前者是**方法签名的集合**（有哪些方法）；后者是**预期的交互序列**（何时调、什么顺序、什么状态）。协议**无法**被类型系统检查 |
| **Callback** | **Lifecycle method** | 前者是**任何**被框架调用的插件方法；后者是**按协议与状态**在特定序列中被调的回调（如 `init`/`destroy`）。后者是前者的子集 |
| **Plugin** | **Client** | 前者是**定制框架**的客户端代码；后者是**任何**使用 API 的代码。所有 plugin 都是 client，反之不然 |
| **Extension point** | **Plugin** | 前者是**框架提供的位置**（如 `org.eclipse.ui.editors`）；后者是**填进位置的代码**。一个是插座，一个是插头 |
| **白盒框架** | **黑盒框架** | 前者靠**子类化 + 覆写**（Template Method），需理解**调用时机**、可能要读源码；后者靠**实现接口 + 组合**（Strategy/Observer），只需理解接口 |
| **白盒的「扩展范围」** | **黑盒的「扩展范围」** | 前者可覆写**所有**非 private/final 方法（范围大但脆弱）；后者只能用**接口暴露的**方法（范围小但稳定） |
| **抽象方法** | **钩子（hook）** | 前者子类**必须**实现（框架需要这个信息）；后者有**默认实现**，子类**可选**覆写。白盒框架通常两者都有 |
| **`extends` 抽象类** | **`implements` 接口** | 前者拿到**默认实现**（省事，但耦合父类、占用唯一的继承位）；后者只拿到**契约**（要自己实现，但可继承别的类） |
| **`instanceof` 作类型守卫** | **`instanceof` 作类型分派** | 前者（`equals` 里检查一个类型）是**好的**；后者（一串 `if/else if` 分派）是**坏的**（易漏、慢、不可扩展） |
| **多态分派** | **Visitor 模式** | 前者**加新类**容易、**加新操作**要改所有类；后者**加新操作**容易、**加新类**要改所有 visitor。这是**表达式问题**，无万全解 |
| **Mediator** | **框架** | 前者是**设计模式**（集中对象间交互）；后者是**架构**（集中控制流）。框架本质上是一个巨大的 Mediator——所以同样有「monolith」风险 |
| **Observer（广播）** | **Chain of Responsibility（链式）** | 前者所有观察者收到**同一**事件（`e` 不变）；后者每个处理者可**修改/拦截**（`e = h.handle(e)`）。课件第 36 页把两者混称 |
| **反射加载插件** | **配置文件加载插件** | 前者从**命令行参数**拿类名（一次一个）；后者从**文件**读多个类名（支持多插件）。两者都靠 `Class.forName` |
| **`newInstance()`（旧）** | **`getDeclaredConstructor().newInstance()`（新）** | 前者在 Java 9 被废弃（会把构造器的受检异常原样抛出，破坏类型系统）；后者安全。课件用旧版（2013 年） |
| **Eclipse Manifest** | **`plugin.xml`** | 前者声明**元数据与依赖**（我是谁、我要谁）；后者声明**扩展**（我往哪个扩展点挂什么） |
| **扩展点（extension point）** | **扩展（extension）** | 前者由**框架**定义（`org.eclipse.ui.editors`）；后者由**插件**声明（`<extension point="...">`）。一个是契约，一个是实现 |
| **`Bundle-ActivationPolicy: lazy`** | **立即加载** | 前者**用到才加载**（Eclipse 上千插件的启动优化）；后者启动时全加载。这是性能 vs 简单性的取舍 |
| **框架「可独立运行」** | **框架「必须扩展」** | 前者如 Eclipse JDT（装了就能用）；后者如 Swing、Servlet、JUnit（必须先写插件）。后者才是典型框架 |
| **框架分层中的 Framework Package** | **Kit Package** | 前者**最稳定、无实现**（`public` 接口）；后者**最不稳定、纯实现**。稳定性与具体性**反相关** |
| **「hot spot」** | **「cold spot」** | 前者是领域中**会变**的部分（提供扩展点）；后者是**不变**的部分（固化进框架）。识别这两者是框架设计的**核心决策** |
| **扩展点太少** | **扩展点太多** | 前者只能服务窄类用户（「不够用」）；后者难学、慢、配置复杂（「太重」）。两个方向都是失败 |
| **「maximizing reuse minimizes use」** | **「复用越多越好」** | 前者（Szyperski）指出：越通用的组件对具体问题帮助越小。**复用与可用是反相关的** |
| **框架的「复用」** | **库的「复用」** | 前者复用**设计与实现 + 宏架构**（更深）；后者只复用**实现**（更浅） |
| **框架的「学习成本」** | **库的「学习成本」** | 前者要学**协议**（何时被调、什么状态、顺序）；后者只学**契约**（每个方法做什么）。前者高得多 |
| **框架的「错误」** | **库的「错误」** | 前者常是**时机/状态/顺序**错（编译器查不出）；后者常是**类型/参数**错（编译器能查） |
| **框架的「内化质量」** | **客户端「实现质量」** | 前者（如 MapReduce 自动并行/容错）由**框架**提供，客户端**免费获得**；后者要客户端自己写，且容易写错 |
| **框架的「威力」** | **框架的「约束」** | 两者**同源**：MapReduce 的自动容错**依赖**「副作用必须幂等」这一约束。**约束是威力的前提** |
| **框架的「黄金法则」** | **「改框架源码」** | 前者：扩展**不应**修改框架源码（否则要维护 fork、无法分享、破坏封装）；后者是**反模式** |
| **Swing 是库** | **Swing 是框架** | **两者都对**：组件与布局是库（你调 `panel.add`），事件循环是框架（它调你的 `actionPerformed`）。同一个软件可以两者兼具 |
| **`MouseListener`** | **`MouseAdapter`** | 前者是**接口**（5 个方法都要实现）；后者是**骨架类**（5 个方法都有空实现，只覆写关心的）。与 `AbstractList` 同一手法 |
| **`web.xml`** | **`@WebServlet`** | 前者是**外部配置**（XML）；后者是**注解配置**（编译进 class）。Servlet 同时支持两者——白盒 + 黑盒并存 |
| **「Follow the leader」** | **「理解设计意图」** | 前者是**复制示例代码**（高效但有风险）；后者是**知道为什么这样写**。课件的警告：复制会**丢失设计意图**，后人可能「优化」掉必需的 bureaucracy |
| **框架的「开箱即用」** | **框架的「延迟实现承诺」** | 前者要求**现在就能跑**（有默认实现）；后者要求**晚点决定实现**（有扩展点）。两者矛盾，靠**三层分层**调和 |
| **「框架很难维护」** | **「库很难维护」** | 前者改一处影响**所有客户端**（规模效应）；后者影响**调用点**。这是框架的根本代价 |

## 8. 对应原版讲义

- PDF 相对路径：`90-原始PDF/15-214/slides/14-frameworks.pdf`
- 总页数：65 页
- 重点页码：
  - 第 1–2 页：**每日设计问题**——Scrabble 的临时瓦片放置（游戏管 / GUI 管 / 用 Mediator），图：`GUI` — `VisualState` — `Game`
  - 第 3 页：**Mediator 模式**——适用性三条 + 后果五条（含「**Danger of mediator monolith**」）
  - 第 4–6 页：**每日设计建议**——`instanceof` 为何有害：可能漏分支、一串判断低效、不可扩展
  - 第 7–8 页：`instanceof` 反例（`Animal`/`Rabbit`/`Fox` → 加 `Wolf` 后「Multiple files must change」「Easy to forget some changes」）
  - 第 9 页：**替代方案一：多态分派**（「Now extension only affects one file」「Java's type system ensures we can't forget operations」）
  - 第 10–12 页：**替代方案二：Visitor 模式**（第 11 页「Good when you add operations frequently」；第 12 页加 `Wolf` 后「Bad when you add new classes frequently」）
  - 第 13 页：**本讲封面**——"Frameworks"，"15-214: Principles of Software Construction: Objects, Design, and Concurrency"，"Some material from Ciera Jaspan, Bill Scherlis, Travis Breaux, and Erich Gamma"
  - 第 14 页：「Reuse and Variations」过渡页（`SWT` GUI Widgets）
  - 第 15 页：**术语：库**——客户端控制结构与控制流；库执行函数并返回数据（例：`I/O`、`Collections`、`Swing`、`Math`）
  - 第 16 页：**术语：框架**——框架控制结构与控制流；框架回调客户端；好莱坞法则（例：`Swing`、`Eclipse`、`Spring`、`Applet`；旁白「But this is an application!」「Hey, wasn't this a library?」）
  - 第 17 页：术语——API、Client、Plugin、Extension point
  - 第 18 页：术语——Protocol、Callback、Lifecycle method
  - 第 19 页：**用 API 像用「半个设计模式」**；插件树；两框架协作
  - 第 20 页：**Google MapReduce**——编程模型（word count 例）+ 类型签名 `map : (k1,v1) → list(k2,v2)`、`reduce : (k2,list(v2)) → list(v2)`
  - 第 21 页：三个提问（是框架吗？怎么知道？收益？若不是框架能否达到？）
  - 第 22 页：MapReduce 六条收益（自动并行分布、千台机器、自动容错重执行、简单模型、数百插件、函数式利于正确性）
  - 第 23 页：**约束**——计算必须能表达为 map/reduce；必须基本函数式；副作用须原子且幂等
  - 第 24 页：**Hadoop**——「The interface is richer than the obvious one!」（`configure`/`close`/`OutputCollector`/`Reporter`）
  - 第 25 页：框架动机——「Family of programs consisting of buttons and text fields only」「Share 90% of the source code」
  - 第 26 页：无框架的 `Calc extends JFrame` 完整代码
  - 第 27 页：**白盒框架定义**——子类化 + 覆写（Template Method）；两步设计法
  - 第 28 页：白盒框架代码（`abstract class Application` + `Calculator` + `Ping`）
  - 第 29 页：**黑盒框架定义**——实现插件接口（Strategy、Observer）；两步设计法
  - 第 30 页：黑盒框架代码（`Application` + `interface Plugin` + `CalcPlugin` + `CalcStarter`）
  - 第 31 页：Eclipse 作为框架（Rich Client Platform）过渡页
  - 第 32 页：**框架设计黄金法则**——扩展不应修改框架源码；三种实现方式
  - 第 33 页：**用反射按类名加载插件**（`Class.forName` + `newInstance`）
  - 第 34 页：**读配置文件加载多个插件**（`.config` + `while` 循环）
  - 第 35 页：Plugin Management 过渡页
  - 第 36 页：**支持多插件**（`List<Plugin>` + 链式 `processMsg`；批注「see Observer pattern」）
  - 第 37 页：**白盒 vs 黑盒对比**——子类化 vs 组合；「Need to understand when overridable methods are called」vs「Only need to understand the interface」
  - 第 38 页：**可独立运行的框架**（Eclipse JDT）vs **必须扩展的框架**（Eclipse RCP、MapReduce、Swing、Servlets、JUnit）
  - 第 39–40 页：Eclipse 作为「Family of Development Tools」过渡页
  - 第 41 页：**Eclipse 插件 Manifest**（`Bundle-SymbolicName`、`Bundle-Activator`、`Require-Bundle`、`Bundle-ActivationPolicy: lazy`）
  - 第 42 页：**`plugin.xml` 与扩展点**（`org.eclipse.ui.editors`）
  - 第 43 页：**`XMLEditor extends TextEditor`**（15 行代码获得完整编辑器；「REALLY NICE not to have to implement this」；「could have used `ITextEditor` interface」）
  - 第 44 页：**JUnit 插件**（`@Before`/`@After`/`@Test`；「the important plugin mechanism is Java annotations」）
  - 第 45 页：**Swing 是库**（容器、布局管理器、组件；「no different than the File I/O library」）
  - 第 46 页：Swing 容器与组件代码（`JPanel`/`JLabel`/`JTextField`）
  - 第 47 页：Swing 布局管理器（`GridBagLayout` + `GridBagConstraints`）
  - 第 48 页：Swing 事件（匿名 `MouseAdapter`；批注「But this extending a class to add custom behaviors, right?」）
  - 第 49 页：**边界在哪里**——AWT Framework / Swing Framework / Our Implementation 三层归属图
  - 第 50 页：自定义组件（组合方式，`extends JPanel` 装入子组件）
  - 第 51 页：自定义组件（自绘方式，覆写 `paintComponent`）
  - 第 52 页：**Servlet**（`@WebServlet("/hello")` + `extends HttpServlet` + `doGet`）
  - 第 53 页：**Servlet 其他方面**——生命周期方法（`init`/`destroy`）、服务方法（`doGet`/`doPut`/`doPost`/`doDelete`）、`web.xml` vs 注解
  - 第 54 页：**OO 框架定义**（credit: Erich Gamma）——可定制的协作类集合；复用设计 + 实现 + 宏架构；「architectural guidance」
  - 第 55 页：**框架挑战**（credit: Erich Gamma）——难维护、客户端易加实现依赖、「what is the framework - what is just default implementation」；Peter Deutsch 引文；「late commitment」vs「must work out of the box」
  - 第 56 页：**框架分层**（credit: Erich Gamma）——Kit Packages / Framework Package / Defaults-Standard Package；稳定性与具体性反相关
  - 第 57 页：**演化：从类提取接口**（credit: Erich Gamma，JHotDraw）——具体类 → 抽象类 → 接口；「start once the architecture is stable!」
  - 第 58 页：**设计框架**——难、需要经验、「Once designed, little place for change」；核心决策是区分共性与可变（hot spots vs cold spots）；扩展点太少/太多/太通用
  - 第 59 页：**使用 vs 复用困境**——「Large rich components are very useful, but rarely fit」；**「maximizing reuse minimizes use」**（C. Szyperski）
  - 第 60 页：**领域工程**——先收集示例应用；有意识地「scoping」；**Eclipse 政策**（先 internal，有两个客户才升 public）
  - 第 61 页：领域工程练习（视频播放、PDF、压缩归档、即时通讯、音乐编辑）+ 四个问题
  - 第 62 页：**框架设计技术**——共性进框架、可变部分提供插件/扩展/回调机制、用 Strategy/Decorator/Observer/Command/Template Method/Factory
  - 第 63 页：**学习框架的技巧**——教程/示例、社区、Follow the leader（复制示例、推断意图、撕掉业务逻辑）；问题：丢失设计意图；**框架设计者的难题：复杂度 vs 能力**（effort vs reward 曲线）
  - 第 64 页：**框架设计建议**——文档要含前置/后置/异常/**调用顺序**；保持接口窄；不要随便 `public`；提供示例插件；防御性检查参数
  - 第 65 页：**总结**——框架捕获可复用基础设施、好莱坞法则、比库更深层的复用、**内化质量属性**（如 MapReduce 的可靠性）、框架影响使用它的应用；三条实践路径（setup / designing / learning）
- 原始网页链接：`https://www.cs.cmu.edu/~aldrich/214/slides/14-frameworks.pdf`

> 待核实：本讲义前 12 页（Mediator、`instanceof`）明显是**上一讲遗留内容**（「Design Problem of the Day」「Design Advice of the Day」是每讲开头的固定栏目），第 13 页才是本讲封面——这说明第 15 讲（Formal Analysis，10 月 17 日）与第 16 讲（Frameworks，10 月 22 日）之间可能还有内容未包含在这份 PDF 里，或前 12 页本属第 15 讲末尾而 PDF 合并时归到了本文件。另：文件名以 `14-` 开头（与 `14_Collections.pdf` 同前缀）但按课表是第 16 讲，属课件编号错位。第 9–12 页 `class Rabbit extends Animal` 中 `Animal` 是 `interface`，Java 应写 `implements`（排版/示例错误）。第 34 页 `Application = new Application();` 缺变量声明与名字。第 50–51 页 `public MyWidget extends JPanel` 缺 `class` 关键字；第 51 页 `JContainer` 应为 `JComponent`。第 30 页 `CalcPlugin.buttonClicked()` 调用 `application.getText()` 但 `Application` 只有 `getInput()`；`calculate(...)` 方法未定义。第 36 页批注说「see Observer pattern」但代码是**链式**（`msg = plugin.process(msg)`），实为 Chain of Responsibility。第 63 页「Getting up a framework's learning curve」标题语法略怪（应为 "Getting up" 或 "Climbing"）。第 54–57 页标注 "credit: Erich Gamma"、第 41–44 页标注 "© 2009 Jonathan Aldrich / Analysis of Software Artifacts"，说明部分幻灯片复用了更早的课程材料。

## 9. 对应视频

未找到官方公开录像。2013 年秋季的 15-214 课堂没有公开发布录像，故不提供链接与时间戳。

## 10. 本节复习

- **库 vs 框架**：判据是**控制权**。库：客户端控制结构与控制流（你调它，它返回）。框架：框架控制（它调你，你回调）。
- **好莱坞法则**：「Don't call us; we'll call you.」——框架的本质特征。
- **Swing 既是库又是框架**：组件与布局是库，事件循环是框架。同一个软件可以两者兼具。
- **七个术语**：API（接口）、Client（使用者）、Plugin（定制框架的客户端）、Extension point（框架提供的挂载点）、Protocol（**交互序列**）、Callback（框架调你的方法）、Lifecycle method（按协议与状态在特定序列中被调的回调）。
- **Protocol 是最难学的部分**：它约束**顺序**与**状态**，**无法**被类型系统检查。框架的 bug 常是「时机错」而非「类型错」。
- **用 API = 用半个设计模式**：框架提供一半（接口 + 调用机制），客户端提供一半（实现）。Strategy、Observer、Template Method、Visitor、Factory、Command 都是这个形态。
- **MapReduce 是框架的典范**：你只写 `map`/`reduce`，框架负责并行、分布、容错、规模。
- **框架的威力来自约束**：MapReduce 的自动容错**依赖**「副作用必须原子且幂等」。**约束是威力的前提**。
- **「internalize qualities」**：框架可以把**质量属性**（可靠性、可扩展性）装进去，客户端免费获得。这是框架最深的价​​值。
- **真实框架的接口总比教科书模型复杂**：Hadoop 的 `configure`/`close`/`OutputCollector`/`Reporter`——生命周期、多输出、可观测性都是接口的一部分。
- **白盒框架**：子类化 + 覆写（Template Method）。扩展范围大（所有非 private/final 方法），但**必须理解调用时机**，可能要读源码。
- **黑盒框架**：实现插件接口 + 组合（Strategy、Observer）。扩展范围小（只有接口方法），但**只需理解接口**。
- **抽象方法 vs 钩子**：前者子类**必须**实现（框架需要）；后者有默认实现，子类**可选**覆写。
- **白盒陷阱**：构造器里调用可覆写方法（子类字段尚未初始化）。`Application() { init(); }` 就是例子。
- **黑盒陷阱**：插件需要回调框架（`setApplication(this)`），形成**双向依赖**。更好的做法是把框架能力也抽成接口（`ApplicationContext`）。
- **黄金法则**：**扩展框架不应修改框架源码**。三种实现：客户端写 `main` / 框架写 `main` + 命令行传类名（反射）/ 框架读配置文件。
- **反射加载**：`Class.forName(name).newInstance()` 三行。代价：无编译期检查、强转可能失败、要求无参构造、性能开销、错误处理复杂。
- **Eclipse 插件**：Manifest（元数据 + 依赖 + `Bundle-ActivationPolicy: lazy`）+ `plugin.xml`（`<extension point="...">` 声明扩展）+ 代码（`extends TextEditor`）。**声明而非调用**是「不改源码而扩展」的极致。
- **框架分层**：Framework Package（最稳定、无实现、`public` 接口）/ Defaults Package（半实现、`protected` 接口）/ Kit Package（最不稳定、纯实现）。**稳定性与具体性反相关**。
- **演化的正确顺序**：具体类 →（发现共性）→ 抽象类 →（提炼契约）→ 接口 + 骨架类。「**start once the architecture is stable!**」
- **框架设计的核心决策**：识别 **hot spots**（会变 → 提供扩展点）与 **cold spots**（不变 → 固化）。
- **双向陷阱**：扩展点太少（服务窄类用户）/ 太多（难学、慢）/ 太通用（复用价值低）。
- **Szyperski**：「**maximizing reuse minimizes use**」——越通用的组件对具体问题帮助越小。复用与可用反相关。
- **领域工程**：先收集示例应用，再抽框架；有意识地 **scoping**；Eclipse 政策「先 internal，有**两个**客户才升 public」（对抗过早抽象）。
- **框架设计建议**：文档必须含**调用顺序**；接口窄；不要随便 `public`；提供示例插件；防御性检查参数。
- **学习框架**：读文档（尤其顺序）+ Follow the leader（复制示例、撕掉业务逻辑、填自己的）。风险：**设计意图丢失**，后人「优化」掉必需的 bureaucracy。
- **库 vs 框架的投入产出**：库起步快、上限低；框架起步慢、上限高。「conundrum」在于你无法预知项目会不会撞到天花板。
- **`instanceof`**：作**类型守卫**（单个）是好的；作**类型分派**（一串）是坏的（易漏、慢、不可扩展）。替代：多态分派（加类易）或 Visitor（加操作易）——**表达式问题**无万全解。
- **Mediator**：集中对象间交互，降低耦合；风险是「**mediator monolith**」。框架本质上是巨大的 Mediator。
- **框架的代价**：难维护（改一处影响所有客户端）、客户端易加实现依赖、「什么是框架 vs 什么是默认实现」模糊、**框架影响使用它的应用**（架构、部署、升级节奏、团队技能）。
- **选择框架是架构决策，不是技术细节**。

## 11. 自我检查

1. 下面三个软件分别是库、框架，还是两者兼具？请说明判断依据（控制权在哪）。
   (a) `java.util.Collections`；(b) `javax.servlet.HttpServlet`；(c) `javax.swing.JPanel` + `ActionListener`。

2. 课件说「Using an API is like a partial design pattern」。请以 `Collections.sort(list, comparator)` 和 Swing 的 `button.addActionListener(l)` 为例，分别指出「框架提供哪一半」「客户端提供哪一半」，并说出对应的设计模式名称。

3. 下面的白盒框架有什么 bug？在什么情况下会出错？请修正。
   ```java
   public abstract class ReportGenerator {
       protected List<String> rows;
       public ReportGenerator() {
           rows = new ArrayList<>();
           generateHeader();          // 调用可覆写方法
       }
       protected abstract void generateHeader();
       public final String generate(List<String[]> data) {
           for (String[] r : data) rows.add(String.join(",", r));
           generateHeader();
           return String.join("\n", rows);
       }
   }
   public class SalesReport extends ReportGenerator {
       private final String title;
       public SalesReport(String title) { super(); this.title = title; }
       @Override protected void generateHeader() { rows.add("== " + title + " =="); }
   }
   ```

4. 为什么框架设计的黄金法则要求「扩展不应修改框架源码」？请列出至少三条代价，并说明三种「不修改而扩展」的技术手段各自的优缺点。

5. MapReduce 的框架提供了自动并行、自动分布、自动容错。请说明这些收益**依赖**客户端的哪些约束，以及为什么「副作用必须原子且幂等」是容错的前提。

<details>
<summary>参考答案</summary>

1. **(a) `java.util.Collections` 是纯库。** 你调用 `Collections.sort(list)`、`Collections.frequency(...)`，它们执行并返回；**你**决定调用顺序、次数、何时停止。`Collections` 从不回调你的代码（除非你传入 `Comparator`——但即使那时，也是**你的调用栈**里发生的，`Collections` 没有自己的控制循环）。所以它是库。
   **(b) `javax.servlet.HttpServlet` 是纯框架。** 你 `extends HttpServlet` 并覆写 `doGet`；**容器（Tomcat）**控制一切：它创建实例、调 `init` 一次、对每个请求调 `doGet`（可能并发）、关闭时调 `destroy`。你**从不**写 `main`，也**从不**主动调 `doGet`。控制权完全在框架手里。这就是好莱坞法则的纯粹形态。
   **(c) `javax.swing.JPanel` + `ActionListener` 是两者兼具。** `JPanel` 的**组件与布局**部分是库：`new JPanel()`、`panel.add(button)`——你调它，它返回，控制权在你。但**事件机制**是框架：`button.addActionListener(l)` 之后，是 Swing 的**事件分发线程**在用户点击时调用 `l.actionPerformed(e)`——你**无法**控制何时被调。所以 Swing 同时是库（构建 UI）与框架（事件循环）。课件第 15–16 页把 `Swing` 同时列在两个列表里，正是这个原因；第 16 页的旁白气泡「Hey, wasn't this a library?」就是在问这个。

2. **`Collections.sort(list, comparator)`**：
   - **框架（库）提供的一半**：排序**算法**（归并排序/ TimSort 的实现）、遍历 `list` 的逻辑、调用 `compare` 的时机与次数。
   - **客户端提供的一半**：`Comparator` 的**具体实现**（`compare(a, b)` 的语义——按什么排序）。
   - **对应模式**：**Strategy**。`Collections.sort` 是 Context，`Comparator` 是 Strategy 接口，你的实现是 ConcreteStrategy。
   **`button.addActionListener(l)`**：
   - **框架提供的一半**：**事件源**（按钮的点击检测）、**事件对象**（`ActionEvent`）、**分发机制**（在 GUI 线程上遍历监听器列表并调用）。
   - **客户端提供的一半**：`ActionListener` 的**具体实现**（`actionPerformed` 里做什么）。
   - **对应模式**：**Observer**。按钮是 Subject，`ActionListener` 是 Observer 接口，你的实现是 ConcreteObserver。
   **共同点**：两者都是「框架提供**调用机制**，客户端提供**被调用的代码**」——这就是「半个设计模式」。框架的那一半是**不变的、可复用的**（排序算法、事件分发），客户端的那一半是**可变的、与应用相关的**（比较规则、点击行为）。这正是第 62 页说的「Common parts go into the framework; provide plug-in interface for variable parts」。

3. **bug：构造器里调用了可覆写方法 `generateHeader()`，而它依赖子类字段 `title`。**
   执行 `new SalesReport("Q3")` 时：
   1. `SalesReport` 的字段初始化**尚未运行**（`title` 还是 `null`）；
   2. 调用 `super()` → `ReportGenerator()` 构造器；
   3. 构造器里 `rows = new ArrayList<>()`，然后 `generateHeader()`；
   4. **动态分派**到 `SalesReport.generateHeader()`；
   5. 它执行 `rows.add("== " + title + " ==")`，此时 `title == null` → 加入 `"== null =="`；
   6. 构造器返回，`title = "Q3"` 才被赋值。
   **结果**：`rows` 里有一个错误的 `"== null =="` 表头，而且 `generate()` 又调了一次 `generateHeader()`，于是表头出现**两次**（一次错的一次对的）。
   **修正方案（两种）**：
   ```java
   // 方案 1：构造器不调用可覆写方法（推荐）
   public abstract class ReportGenerator {
       protected List<String> rows = new ArrayList<>();
       public ReportGenerator() { /* 什么都不做 */ }
       protected abstract void generateHeader();
       public final String generate(List<String[]> data) {
           rows.clear();                    // 幂等
           for (String[] r : data) rows.add(String.join(",", r));
           generateHeader();                // 只在这里调
           return String.join("\n", rows);
       }
   }
   ```
   ```java
   // 方案 2：两阶段初始化，客户端显式调 init()
   public abstract class ReportGenerator {
       protected List<String> rows;
       protected final void init() { rows = new ArrayList<>(); generateHeader(); }
       ...
   }
   public class SalesReport extends ReportGenerator {
       public SalesReport(String title) { this.title = title; }   // 先赋值
       // 客户端：new SalesReport("Q3").init()...
   }
   ```
   方案 1 更简单：**构造器只做「不依赖子类」的事**，把需要子类参与的逻辑推迟到明确的入口方法。这也是 Effective Java 第 17 条的建议（「Design and document for inheritance or else prohibit it」）。本讲第 28 页的 `Application() { init(); }` 有**完全相同**的问题——课件没有指出，这是一个真实的坑。

4. **三条代价**：
   - **要维护一个 fork**：框架升级时，你的修改要**手工合并**，冲突不断。框架改得越频繁，成本越高。
   - **改动无法分享**：别人用不到你的修复/扩展，你也没法受益于别人的。社区的改进全部与你无关。
   - **破坏封装**：修改框架源码意味着你依赖了它的**内部实现细节**，而这些细节随时可能变（第 55 页：「easy for clients to add implementation dependencies」）。
   - （第四条）**无法升级**：一旦 fork，你可能永远停在旧版本，错过安全修复与性能改进。
   **三种技术手段的优缺点**：
   | 手段 | 优点 | 缺点 |
   |---|---|---|
   | **A. 客户端写 `main`，传入插件对象** | 类型安全（编译期检查）、简单、无需反射 | 客户端必须能改自己的 `main`；框架不能独立启动；一个 `main` 只能配一个（或固定几个）插件 |
   | **B. 框架写 `main`，命令行传类名（反射）** | 框架可独立启动；插件可后加（框架发布后）；配置与代码分离 | 无编译期检查（类名拼错只有运行时发现）；强转可能 `ClassCastException`；要求无参构造；错误处理繁琐 |
   | **C. 框架读配置文件/JAR（魔法位置）** | 支持**多个**插件；配置可热改；插件可自动发现 | 配置文件格式错误难调试；隐式依赖（不知道谁加载了什么）；启动变慢；安全问题（任意类都能被加载） |
   **实践中的组合**：Eclipse 用 **C**（`plugin.xml` + `META-INF/services`）+ 声明式扩展点；Spring 用 **C**（XML/注解扫描）+ **A**（`ApplicationContext`）；JUnit 4 用 **B**（`Runner` 按类名加载）+ 注解。**没有一种手段适合所有场景**——选择取决于「谁控制启动」与「插件何时加入」。

5. **依赖的约束**（第 23 页）：
   - **计算必须能表达为 map/reduce**：不能表达的问题（如图算法、迭代式机器学习）用不了这个框架。
   - **map 与 reduce 必须基本函数式**：不能依赖全局可变状态、不能有顺序依赖。
   - **副作用必须原子且幂等**：这是最关键的一条。
   **为什么「原子且幂等」是容错的前提**：
   MapReduce 的容错机制是**失败重执行（re-execution）**——某台机器挂了，框架就把那个 map/reduce 任务**在另一台机器上重跑一遍**。这要求：
   - **原子（atomic）**：任务的副作用要么**全部生效**，要么**全部不生效**。如果写到一半崩了，重跑会产生「半写」的脏数据。所以框架要求你**通过框架提供的输出机制**（`OutputCollector`）写结果，而不是直接写文件/数据库——框架能在任务失败时丢弃未提交的输出。
   - **幂等（idempotent）**：同一个任务执行**一次**和执行**两次**，效果相同。因为框架**无法区分**「任务失败了」和「任务成功了但汇报失败的机器挂了」——它可能重跑一个**已经成功**的任务。如果你的 `map` 里有 `counter++` 这样的非幂等副作用，重跑就会多加一次。
   **为什么不能去掉这个约束**：如果允许任意副作用，框架就**无法安全重试**——它必须知道「这次重试会不会产生重复效果」。而要判断这一点，框架需要理解你副作用的语义，这**不可能**（图灵完备）。所以唯一可行的办法是**把责任推给客户端**：你保证幂等，我保证重试安全。
   **这正是「约束是威力的前提」的最好例证**：MapReduce 的自动容错（威力）**完全建立在**「副作用幂等」（约束）之上。没有约束，就没有威力。第 23 页最后那个问题（「客户端接受这些限制，换来什么好处？」）的答案是第 22 页的六条收益——**这是一个明确的交易，而交易的另一端就是约束**。第 59 页 Szyperski 的「maximizing reuse minimizes use」说的是同一件事的另一面：**框架越强大，它对你能做的事的限制就越多**。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-15-Formal-Analysis]]
- 下一讲：[[15-214-17-Concurrency-Part1]]（10 月 29 日，Concurrency, part 1）
- 课程总览：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]
- 课程目录：[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸：
  - Erich Gamma, Richard Helm, Ralph Johnson, John Vlissides, *Design Patterns: Elements of Reusable Object-Oriented Software*（GoF, 1994）——Template Method、Strategy、Observer、Visitor、Mediator 的原始定义。本讲第 54–57 页的「credit: Erich Gamma」材料即出自其框架设计经验。
  - Ralph Johnson & Brian Foote, "Designing Reusable Classes", *Journal of Object-Oriented Programming* 1(2), 1988 —— 「框架」概念与「好莱坞法则」的经典出处，也是「白盒 vs 黑盒」讨论的源头。
  - Clemens Szyperski, *Component Software: Beyond Object-Oriented Programming*（2nd ed., 2002）——「maximizing reuse minimizes use」的出处，组件复用的经济学分析。
  - Markus Völter 等关于「框架 vs 库」的讨论，以及 Wolfgang Pree 的 *Design Patterns for Object-Oriented Software Development*（1994）——「hot spots / cold spots」框架设计方法的原始文献。
  - Mohamed Fayad & Ralph Johnson, "Object-Oriented Application Frameworks", *CACM* 42(10), 1999 —— 框架开发与演化的综述（含「框架难维护」「框架成熟度三阶段」等实践结论）。
  - 官方文档：`http://hadoop.apache.org/docs/current/api/org/apache/hadoop/mapred/Mapper.html` 与 `.../Reducer.html`（讲义第 24 页给出）——看真实框架接口比教学模型丰富多少。
  - Eclipse 插件开发：`https://www.eclipse.org/articles/`（2013 年的文章仍在，含「Plug-in architecture」「Extension points」的入门教程）；现代等价物是 VS Code 扩展（`package.json` 的 `contributes` 声明扩展点，与本讲的 `plugin.xml` 同构）。
  - Java 现代插件机制：`java.util.ServiceLoader`（`META-INF/services/` 声明式注册）——本讲第 33–34 页「反射加载」的标准库替代；Java 9 模块系统的 `provides ... with ...` 是其进一步演化。
  - 与前面各讲的连接：[[15-214-07-Design-Patterns]]（模式总览）、[[15-214-09-Design-Patterns-Continued]]（Template Method + Decorator）、[[15-214-11-Design-Principles-GRASP]]（Protected Variations / Indirection）、[[15-214-14-Java-Collections]]（`List` + `AbstractList` + `ArrayList` 的三层结构，正是本讲第 56 页框架分层的实例）。
