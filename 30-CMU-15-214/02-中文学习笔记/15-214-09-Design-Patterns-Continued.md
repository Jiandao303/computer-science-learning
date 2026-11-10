---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L09
topic: Design Patterns Continued - Strategy, Template Method, Decorator and Java I/O
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 设计模式
  - Strategy
  - Template Method
  - Decorator
  - Composite
  - Java IO
  - 流
---

# 第 9 讲 设计模式续：策略、模板方法与装饰器，以及 Java I/O

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。本讲 slides 标题为「Design Patterns and Java I/O」。

## 1. 本节学习目标

- 能说明「模式」为什么是**被发现**而非被发明，以及模式名称作为**设计词汇**的价值。
- 能对 Composite、Template Method、Strategy、Decorator 四个模式，分别说出它的通用问题、通用解法与代价。
- 能解释 Template Method 的「好莱坞法则（don't call us, we'll call you）」控制反转，并说明为什么模板方法要用 `final`。
- 能用 Strategy 替代 if-else 分支，并说清「继承 vs 组合」在算法可变性上的差别。
- 能说明 Java I/O 的流抽象（`InputStream`/`OutputStream`）如何用 Decorator 组合出压缩、加密、缓冲等功能。
- 能判断在什么场景下**不该**使用某个模式。

## 2. 前置知识

- [[15-214-07-Design-Patterns]]：模式四要素（Name/Problem/Solution/Consequences）、三条基本原则、GoF 三分类。
- [[15-214-03-Encapsulation-and-Inheritance]]：抽象类、`final`、模板方法的雏形（用模板方法消除 `instanceof`）。
- [[15-214-04-Inheritance-Typechecking-Dispatch]]：动态分派、覆写。
- [[15-214-02-Objects-Encapsulation-Polymorphism]]：接口与「变量应声明为接口类型」。
- 外部概念：Java 的 `java.io` 包、`Comparator` 接口。

## 3. 核心概念

- **Composite（组合）**：表达部分-整体层次，使客户端能把「一组对象」当作「一个对象」对待。
- **Template Method（模板方法）**：在父类中固定算法骨架，把可变步骤留给子类实现。
- **Strategy（策略）**：把可变的算法抽成接口，让上下文对象持有并委托给它。
- **Decorator（装饰器）**：通过包装同类型对象，动态叠加职责，而不改变原对象。
- **Hollywood Principle（好莱坞法则）**：don't call us, we'll call you——由框架调用你的代码，而非你调用框架。
- **Stream（流）**：Java I/O 的基本抽象，把数据看作有序字节序列。
- **`FilterOutputStream` / `FilterInputStream`**：Java I/O 中 Decorator 模式的基类。
- **Design Vocabulary（设计词汇）**：模式名称构成的、能提高沟通层次的共享语言。

## 4. 通俗理解

**模式是什么？** 课件第 2 页引用 Christopher Alexander 的定义：

> "Each pattern describes a problem which occurs over and over again in our environment, and then describes the core of the solution to that problem, in such a way that you can use this solution a million times over, without ever doing it the same way twice."

关键词是最后半句：**用一百万次，但每次都不重样**。模式不是可复制的代码模板，而是「问题-解法」的对应关系——每次落地都长得不一样，但骨架相同。

课件第 2 页还点出一个容易忽略的事实：

> Every Composite has its own domain-specific interface. But they share a common problem and solution.

`ShapeGroup` 和文件系统的 `Directory` 都是 Composite，接口完全不同（一个是 `draw()`，一个是 `getSize()`），但「部分-整体」这个**问题**和「让组合与叶子实现同一接口」这个**解法**是一样的。这就是模式抽象的正确层次：**抽象问题与解法结构，不抽象接口**。

**模式名称为什么重要？**（第 4 页）因为它成为设计词汇（design vocabulary），**提高了沟通的层次**。说「这里用 Strategy」比说「这里把算法抽成接口、让上下文持有它、运行时替换」快十倍，而且对方立刻能想到它的代价。

## 5. 原理与推导

### 5.1 模式四要素（复习与深化）

课件第 4 页：

| 要素 | 内容 | 为什么重要 |
|---|---|---|
| **Name（名称）** | 成为设计词汇，提高沟通层次 | 一个词承载一整套权衡 |
| **Problem（问题）** | 模式何时适用 | 判断「该不该用」的唯一依据 |
| **Solution（解法）** | 设计元素及其关系，**是抽象的，必须被特化** | 不能照抄，必须落到具体领域 |
| **Consequences（后果）** | 应用的权衡 | **每个模式都有代价**，涉及灵活性、可扩展性等 |

课件特别强调：

> Each pattern has costs as well as benefits. There may be variations in the pattern with different consequences.

「每个模式都有代价」这句话是本讲的主线——下面四个模式，每个都会明确列出代价。

### 5.2 Composite：从 Shape 到通用结构

课件第 3、5 页给出领域实例（窗口系统中的图形）：

**问题**：表达图形的部分-整体层次；允许把一组图形当作单个图形处理。

**结构**：

```
        Shape
        draw()
       /      \
Rectangle    ShapeGroup
draw()       draw()
             components *
             for s in components: s.draw()
```

**后果**：客户端变简单（可以忽略「单个 vs 一组」的差别）；容易添加新的图形种类。

第 6 页把它抽象成通用形式：

**通用问题**：表达组件的部分-整体层次；允许把组合当作组件。

**通用后果**：
- 客户端变简单，可以忽略差别；
- 容易添加新组件类型；
- **可能过度泛化（can be overly general）——一致性并不总是好事**。

最后这条是 Composite 的核心代价。「统一对待」意味着 `Shape` 接口上的每个操作都必须对叶子有意义。如果 `ShapeGroup` 需要 `add(Shape)` 而 `Rectangle` 不需要，那 `add` 就只能放在 `ShapeGroup` 上——客户端又得区分类型，统一性被破坏。课件第 7 讲（`07-design-patterns.pdf` 第 3 页）已经列过这个问题：某些操作并非在所有组件上都有意义。

### 5.3 Template Method：把不变的骨架钉死

课件第 7 页的领域实例是「图形变更通知」：

**问题**：
- `draw()` 各图形不同，但「更新（update）」的逻辑不变——想复用更新代码；
- 未来的图形实现**不应忘记**更新。

**结构**：

```
        AbstractShape
        +draw()        «final»
        #doUpdate()
        #doDraw()
        draw() { doDraw(); doUpdate(); }
       /            \
Rectangle        ShapeGroup
#doDraw()        #doUpdate()
                 #doDraw()
```

关键点：`draw()` 是 `final` 的，它固定了「先画自己，再通知更新」这个**顺序**；子类只能实现 `doDraw()` 与 `doUpdate()` 两个钩子（hook）。

**通用形式**（第 8 页）：

**问题**：
- 表达一个算法中「可变部分」与「不变部分」；
- 当公共行为应当被提取并局部化；
- 当子类扩展应当被限制。

**后果**：
- 代码复用；
- **控制反转（inverted "Hollywood" control）：don't call us, we'll call you**；
- 不变部分不会被修改。

「好莱坞法则」这个比喻很精准：演员（子类）不主动找剧组（父类），而是等剧组来叫你。控制权在父类的 `templateMethod()` 手里，它在合适的时机回调子类的 `primitiveOperation()`。这就是**框架**与**库**的根本差别——用库时你调它，用框架时它调你。

`«final»` 标注出现在 `templateMethod()` 上，不是装饰：如果子类能覆写 `templateMethod()`，它就能绕过整个骨架，模板方法的意义就消失了。**`final` 在这里是「算法骨架不可协商」的强制执行手段**。

课件第 9 页有一个课堂追问：Virtual World 作业（hw2）里你用到模板方法了吗？怎么用的、为什么？并指向 Piazza 帖子「How to Reuse Code in hw2」。这说明模板方法是那次作业的实际重构方向——很可能是「所有图形都要先更新状态再绘制」这类重复逻辑。

### 5.4 从「加个参数」到 Strategy：一次完整的设计推演

课件第 10–12 页是整讲最精彩的部分：它没有直接抛出 Strategy，而是**先让你走一遍错误的路**。

**背景**：文档编辑器，把段落断成行的算法有多种：

| 算法 | 策略 |
|---|---|
| **Blind（盲断）** | 到 80 列直接切断 |
| **Greedy（贪心）** | 本行尽量多放词，然后换行 |
| **Global（全局，如 TeX）** | 最小化整段的 badness；可能为了减少下一行的多余空格，把一个小词挪到下一行 |

**方案一：放进 `Paragraph` 类**。课件列出四条反对理由：

- 这不是 `Paragraph` 的主要职责；
- 把许多算法塞进 `Paragraph` 会让它过于庞大；
- 其他类也可能需要断行；
- 添加新的断行算法很困难。

注意这四条覆盖了不同的设计原则：单一职责（第一条）、类的规模（第二条）、可复用性（第三条）、可扩展性（第四条）。这是「**职责分配**」问题，不只是「代码放哪」问题。

**方案二：把断行策略封装成独立对象**（第 11 页）：

**问题**：
- `Paragraph` 需要以不同方式断行；
- 想容易地改变或扩展断行算法；
- 想在新地方复用算法。

**结构**：

```
Paragraph                    LineBreakStrategy
draw()                       computeBreaks(text)
   strategy 1               /                  \
                    SimpleLineBreaker      TeXLineBreaker
                    computeBreaks(text)    computeBreaks(text)
```

**后果**：
- 容易添加新的断行策略；
- 分离了策略——**算法与段落可以独立变化**；
- **增加了对象与动态性——代码更难理解**。

**通用形式（Strategy，第 12 页）**：

**问题**：行为在抽象的不同实例间变化；一个抽象需要算法的不同变体。

**后果**：
- 容易添加新策略（相比条件分支）；
- 分离算法——算法与上下文独立变化；
- **增加对象与动态性——代码更难理解**；
- **固定的策略接口——对某些实现来说开销过高（high overhead for some impls.）**。

最后一条容易被忽略。如果策略算法只有一行（比如比较两个整数），把它抽成接口 + 两个实现类，就产生了：一个接口、两个类、一次虚调用、一次对象分配。**Strategy 的收益随算法复杂度上升，成本却基本固定**——所以简单算法用 Strategy 是亏的。这是「模式有代价」的具体量化。

### 5.5 Strategy 的代码对照：if-else vs 接口

课件第 14 页并排放了两段排序代码：

**版本 A：字符串参数 + if-else**

```java
void sort(int[] list, String order) {
    … 
    boolean mustswap; 
    if (order.equals("up")) {
        mustswap = list[i] < list[j];
    } else if (order.equals("down")) {
        mustswap = list[i] > list[j];
    }
    …
}
```

**版本 B：`Comparator` 接口**

```java
void sort(int[] list, Comparator cmp) {
    … 
    boolean mustswap; 
    mustswap = cmp.compare(list[i], list[j]);
    …
}

interface Comparator {
    boolean compare(int i, int j);
}

class UpComparator implements Comparator {
    boolean compare(int i, int j) { return i < j; }
}

class DownComparator implements Comparator {
    boolean compare(int i, int j) { return i > j; }
}
```

对比：

| 维度 | 版本 A（`String order`） | 版本 B（`Comparator`） |
|---|---|---|
| 新增一种排序顺序 | **必须修改 `sort`**，加一个 `else if` | 新增一个类，**`sort` 不动** |
| 类型安全 | 拼错 `"upx"` 编译期无感知，运行时 `mustswap` 未初始化 | 编译期检查 |
| 非法值的处理 | 需要一个 `else` 兜底（否则 `mustswap` 可能未赋值） | 不可能出现「非法策略」 |
| 调用方负担 | 记住字符串常量 | 传对象，IDE 可补全 |
| 复杂度 | 低 | 多两个类 |
| 复用 | 比较逻辑埋在 `sort` 里 | 比较逻辑可单独测试、单独复用 |

这正好对应**开闭原则（Open-Closed Principle）**：对扩展开放（加 `UpComparator` 不用改 `sort`），对修改关闭。版本 A 每加一种顺序都要改 `sort`，是「对修改开放」，违反原则。

注意幻灯片里的 `class UpComparator implements Comparator` 写成了 `compare(int I, int j)`（大写 `I`），是排版错误。

### 5.6 三条基本原则如何「生成」Strategy

课件第 15 页回到根本：

> Patterns emerge from fundamental principles applied to recurring problems.
> - Design to interfaces（面向接口设计）
> - Favor composition over inheritance（优先组合而非继承）
> - Find what varies and encapsulate it（找出变化点并封装它）
>
> Patterns are discovered, not invented. Best practice by experienced developers.

第 16 页逐条对应到 Strategy：

| 原则 | 在 Strategy 中的体现 |
|---|---|
| **Design to interfaces** | 策略的算法接口（`LineBreakStrategy`、`Comparator`） |
| **Favor composition over inheritance** | 上下文**持有**一个策略对象，而不是继承算法 |
| **Find what varies and encapsulate it** | 变化点是「所用的算法」，把它封装成对象 |

**如果用继承实现 Strategy 会怎样？**（第 16 页）

> Strategy could be implemented with inheritance: multiple subclasses of `Context`, each with an algorithm.
>
> - Drawback: **couples Context to algorithm, both become harder to change**；
> - Drawback: **can't change algorithm dynamically**。

这两条 drawback 值得展开：

- **耦合**：`TeXParagraph extends Paragraph` 意味着 `Paragraph` 的任何变化都会影响 `TeXParagraph`；而 `Paragraph` 持有 `TeXLineBreaker` 只是「使用」关系，`Paragraph` 不需要知道 `TeXLineBreaker` 的内部结构。
- **不能动态改变**：一个 `TeXParagraph` 对象永远是 TeX 断行的；而持有策略的 `Paragraph` 可以在运行时 `setStrategy(new SimpleLineBreaker())`——比如用户切换「草稿模式」时。

课件第 16 页末尾留了一个延伸问题：

> Side note: how do you implement the Strategy pattern in functional languages?

答案：**函数即策略**。在函数式语言里，策略就是一个函数值，直接作为参数传递——不需要接口、不需要实现类，`sort(list, (a, b) -> a < b)` 就够了。这也说明 Strategy 模式在 OO 中的「接口 + 类」结构，本质是在**用对象模拟一等函数**。Java 8 引入 lambda 后，`Comparator` 可以用 `Comparator.comparing(...)` 一行写出，正是这个道理。

### 5.7 模式分类与「必知清单」

课件第 17 页（与上一讲重复）：

- **Structural（结构型）**：变化的是**对象结构**；
- **Behavioral（行为型）**：变化的是**你想要的行为**；
- **Creational（创建型）**：变化的是**对象创建**。

UML 图来源标注为 Pekka Nikander：`http://www.tml.tkk.fi/~pnr/GoF-models/html/`。

第 18 页的「必知清单」（与上一讲相同）：

> Façade, Adapter, Composite, Strategy, Bridge, Abstract Factory, Factory Method, Decorator, Observer, Template Method, Singleton, Command, State, Proxy, and Model-View-Controller
>
> **Know pattern name, problem, solution, and consequences.**

注意最后一个词是 **consequences**——课件反复强调这一点，说明考试与实战中「这个模式的代价是什么」比「它的 UML 长什么样」重要得多。

### 5.8 Java I/O：一个真实的 Decorator 案例

课件从第 19 页开始转向 Java I/O，目的是**在真实标准库里看到模式**。

**起点：`System.out` 是什么？**（第 19–20 页）

`System.out` 是 `java.io.PrintStream` 的实例。`PrintStream` 提供便利的打印方法：

```java
void close();
void flush();
void print(String s);
void print(int i);
void print(boolean b);
void print(Object o);
…
void println(String s);
void println(int i);
void println(boolean b);
void println(Object o);
…
```

这里已经能看到一个设计选择：`print` 有**大量重载**（`String`/`int`/`boolean`/`Object`…）。为什么不只留 `print(Object)`？因为那样每次打印 `int` 都要装箱，而且格式化行为要靠在 `Object` 上做 `instanceof` 分派——重载在编译期就解决了分派，既快又类型安全。

**基本 I/O 抽象：数据流**（第 22 页）

```java
// java.io.InputStream
void          close();
abstract int  read();
int           read(byte[] b);

// java.io.OutputStream
void          close();
void          flush();
abstract void write(int b);
void          write(byte[] b);
```

注意 `abstract` 标记：`InputStream.read()` 与 `OutputStream.write(int)` 是**唯一必须实现的方法**，其余方法（`read(byte[])`、`write(byte[])`）都可以基于它们用循环实现。这是**最小接口 + 派生便利方法**的设计——子类只需实现一个方法就能工作。

课件还提示：有了 `OutputStream` 就能构造 `PrintStream`：

```java
PrintStream(OutputStream out);
PrintStream(File file);
PrintStream(String filename);
…
```

这暗示了 `PrintStream` 是一个**包装器**——它把「打印格式化数据」的能力加在一个字节流之上。这正是 Decorator 的形态。

**设计问题**（第 23 页）：

> 如何给流添加功能？我们可以对流做很多事：压缩它、加密它、计算（或校验）校验和/摘要、翻译它、（你的想法）。
>
> 把所有这些东西显式加到 `OutputStream` 里是不合理的。我们能做什么？

如果采用继承，会得到组合爆炸：`CompressedEncryptedOutputStream`、`EncryptedCompressedOutputStream`、`CompressedWithChecksumOutputStream`……**n 种功能需要 2^n 个子类**。而且功能是**可叠加**的，继承是**静态**的，天生不匹配。

### 5.9 Decorator 模式

课件第 24 页的结构：

```
                Component
                + operation()
                    |
        ┌───────────┴───────────┐
  ConcreteComponent          Decorator
  + operation()              + operation()
                                  |
                    ┌─────────────┴─────────────┐
            ConcreteDecoratorA           ConcreteDecoratorB
            + operation()                # newAfterBehavior()
            – addedState                 # newBeforeBehavior()
                                         + operation()
```

`Decorator` 的 `operation()` 实现为：

```java
newBeforeBehavior()
super.operation()        // 委托给被包装的组件
newAfterBehavior()
```

关键：`Decorator` **既是 `Component` 又持有 `Component`**（`component.operation()` 那条 `1` 的关联）。这让装饰器可以无限嵌套：`new A(new B(new C(concrete)))`。

**适用性（Applicability）**（第 25 页）：

- 动态、透明地给**单个对象**添加职责；
- 用于**可以撤销**的职责；
- 当用子类扩展不切实际时。

**后果（Consequences）**：

- 比静态继承更灵活；
- 避免庞大的单体类（avoids monolithic classes）；
- **破坏对象身份（breaks object identity）**；
- **大量小对象（lots of little objects）**。

两条代价都很实在：

- **破坏身份**：`new BufferedOutputStream(new FileOutputStream(f))` 得到的对象 `!=` 原来的 `FileOutputStream`，用 `==` 或 `equals` 判断「是不是同一个流」会失败；`instanceof` 也可能出人意料（装饰器是 `FilterOutputStream` 而非 `FileOutputStream`）。
- **大量小对象**：每层包装一个对象，嵌套五层就是五个对象加五次虚调用。对 I/O 来说这是值得的（I/O 本身慢），但对热路径上的小对象就未必。

课件第 26 页指向 `FilterOutputStream` 作为 Decorator 的实例——`FilterOutputStream` 继承 `OutputStream` 并持有一个 `OutputStream`，正是「既是组件又是包装者」的结构。

### 5.10 为什么叫「装饰器」：GUI 中的起源

课件第 27 页给了一个极好的直观解释：

> 起源在 GUI。想象你有一个窗口，能在任意尺寸的屏幕上显示大量文本，但**不能滚动**。
>
> 滚动可以通过一个装饰器添加，它：
> - 覆写 `draw`；
> - 画一个滚动条；
> - 根据滚动位置缩放并移动视口；
> - 对底层窗口调用 `draw()`。

这个例子的妙处在于：**底层窗口完全不知道自己被滚动了**。它还是老老实实画自己的内容；装饰器改变的是「画在哪、画多少」。这就是「透明地添加职责」——被装饰者无需任何修改，甚至无需知晓。

而且「可撤销」在这里也很自然：不需要滚动了，就把装饰器摘掉，窗口还是那个窗口。

### 5.11 四个模式的横向比较

把本讲四个模式放在一张表里，能看清它们的差异：

| 模式 | 分类 | 变化点 | 结构手段 | 主要代价 |
|---|---|---|---|---|
| **Composite** | 结构型 | 部分 vs 整体 | 组合持有子组件列表，实现同一接口 | 过度泛化；并非所有操作对叶子都有意义 |
| **Template Method** | 行为型 | 算法的可变步骤 | 父类 `final` 骨架 + 子类钩子 | 继承耦合；子类受骨架约束；难以运行时改变 |
| **Strategy** | 行为型 | 整个算法 | 上下文持有策略接口 | 增加对象与间接层；简单算法开销过高 |
| **Decorator** | 结构型 | 对象职责的叠加 | 包装同类型对象，前后加行为 | 破坏对象身份；大量小对象 |

一个有用的判别：

- 变化的是「**算法的哪几步**」→ Template Method（继承，编译期确定）；
- 变化的是「**整个算法**」→ Strategy（组合，运行期可换）；
- 变化的是「**对象由哪些部分组成**」→ Composite（树形结构）；
- 变化的是「**对象带哪些附加职责**」→ Decorator（链式包装）。

### 5.12 Template Method vs Strategy：最常被混淆的一对

两者都解决「算法可变」，但方向相反：

| 维度 | Template Method | Strategy |
|---|---|---|
| 复用机制 | **继承**（子类覆写钩子） | **组合**（上下文持有策略对象） |
| 绑定时机 | 编译期（对象的类型决定） | 运行期（可 `setStrategy`） |
| 控制流 | 父类调用子类（好莱坞法则） | 上下文调用策略（普通委托） |
| 复用粒度 | 复用**骨架**，替换**步骤** | 复用**上下文**，替换**整个算法** |
| 耦合 | 子类依赖父类的骨架细节 | 上下文只依赖策略接口 |
| 类数量 | 每种变体一个子类 | 每种算法一个类 + 上下文不变 |
| 典型场景 | 框架的扩展点、`AbstractList` | 可配置的算法、`Comparator` |

一个经验判断：**如果你需要「在运行时切换算法」，Strategy；如果「算法的顺序不能变、只有几步可变」，Template Method。** 如果两者都要，可以组合使用：模板方法中的某个钩子委托给一个策略对象。

## 6. 代码示例

### 6.1 官方课程代码

出自 `09-design-patterns-continued.pdf` 第 7 页（Template Method，图形变更通知）：

```
AbstractShape
  +draw()        «final»
  #doUpdate()
  #doDraw()
  // draw() 的实现：
  doDraw();
  doUpdate();
```

出自同文件第 8 页（Template Method 的通用结构）：

```
AbstractClass
  +templateMethod()   «final»
  #primitiveOperation1()
  #primitiveOperation2()
  // templateMethod() 的实现：
  primitiveOperation1();
  …
  primitiveOperation2();
  …
```

出自同文件第 11 页（Strategy，断行算法）：

```
Paragraph
  draw()
  strategy 1 —— LineBreakStrategy
                 computeBreaks(text)
                 ├── SimpleLineBreaker.computeBreaks(text)
                 └── TeXLineBreaker.computeBreaks(text)
```

出自同文件第 14 页（`Comparator` 版排序）：

```java
void sort(int[] list, Comparator cmp) {
    … 
    boolean mustswap; 
    mustswap = cmp.compare(list[i], list[j]);
    …
}

interface Comparator {
    boolean compare(int i, int j);
}

class UpComparator implements Comparator {
    boolean compare(int i, int j) { return i < j; }
}

class DownComparator implements Comparator {
    boolean compare(int i, int j) { return i > j; }
}
```

出自同文件第 22 页（Java 流的抽象）：

```java
// java.io.InputStream
void          close();
abstract int  read();
int           read(byte[] b);

// java.io.OutputStream
void          close();
void          flush();
abstract void write(int b);
void          write(byte[] b);
```

出自同文件第 24 页（Decorator 的 `operation()` 骨架）：

```java
newBeforeBehavior()
super.operation()
newAfterBehavior()
component.operation()
```

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：Template Method——数据导入器**

```java
public abstract class DataImporter {
    // 骨架：顺序不可协商，故 final
    public final void importAll(String path) {
        open(path);                 // 钩子
        while (hasMore()) {         // 钩子
            Row r = nextRow();      // 钩子
            if (isValid(r)) {       // 钩子（有默认实现）
                store(r);           // 钩子
            }
        }
        close();                    // 钩子
    }

    protected abstract void open(String path);
    protected abstract boolean hasMore();
    protected abstract Row nextRow();
    protected abstract void store(Row r);
    protected void close() { /* 默认：什么都不做 */ }

    // 默认实现：子类可覆写，但多数情况够用
    protected boolean isValid(Row r) { return r != null; }
}

final class CsvImporter extends DataImporter {
    private BufferedReader in;
    private String line;

    protected void open(String path) {
        try { in = new BufferedReader(new FileReader(path)); }
        catch (IOException e) { throw new UncheckedIOException(e); }
    }
    protected boolean hasMore() {
        try { line = in.readLine(); return line != null; }
        catch (IOException e) { throw new UncheckedIOException(e); }
    }
    protected Row nextRow() { return Row.parseCsv(line); }
    protected void store(Row r) { System.out.println("stored: " + r); }
    protected void close() {
        try { in.close(); } catch (IOException ignored) { }
    }
}
```

要点：`importAll` 是 `final`，子类无法改变「打开→循环→校验→存储→关闭」的顺序，也就无法忘记 `close()`——这正是课件第 7 页「未来实现不应忘记更新」的同类保证。子类只填四个空。

**示例 B：Strategy——与示例 A 对照的同一问题**

```java
public interface StoreStrategy {
    void store(Row r);
}

public final class Importer {
    private final StoreStrategy store;         // 组合，不是继承
    public Importer(StoreStrategy store) { this.store = store; }

    public void importAll(String path) {
        // …读文件…
        for (Row r : rows) {
            if (r != null) store.store(r);      // 委托给策略
        }
    }
    public Importer withStrategy(StoreStrategy s) { return new Importer(s); }
}

// 两种策略，Importer 一行不改
StoreStrategy toConsole = r -> System.out.println(r);
StoreStrategy toDb      = r -> db.insert(r);

Importer a = new Importer(toConsole);
Importer b = new Importer(toDb);
```

对照：Template Method 版把变化点交给**子类**，Strategy 版把变化点交给**构造参数**。前者编译期确定，后者运行期可换（`new Importer(toConsole)` 与 `new Importer(toDb)` 是同一套 `Importer` 代码）。

**示例 C：Decorator——给 Writer 加「编号行」与「大写」**

```java
public abstract class LineWriter {                 // Component
    public abstract void writeLine(String s);
}

public final class ConsoleLineWriter extends LineWriter {   // ConcreteComponent
    @Override public void writeLine(String s) { System.out.println(s); }
}

public abstract class LineWriterDecorator extends LineWriter {  // Decorator
    protected final LineWriter inner;              // 既 is-a 又 has-a
    protected LineWriterDecorator(LineWriter inner) { this.inner = inner; }
}

public final class NumberingWriter extends LineWriterDecorator {  // ConcreteDecoratorA
    private int n = 0;
    public NumberingWriter(LineWriter inner) { super(inner); }
    @Override public void writeLine(String s) {
        inner.writeLine((++n) + ". " + s);          // 前置行为
    }
}

public final class UpperCaseWriter extends LineWriterDecorator {  // ConcreteDecoratorB
    public UpperCaseWriter(LineWriter inner) { super(inner); }
    @Override public void writeLine(String s) {
        inner.writeLine(s.toUpperCase());           // 转换后委托
    }
}

// 任意叠加，顺序不同则结果不同
LineWriter w = new UpperCaseWriter(new NumberingWriter(new ConsoleLineWriter()));
w.writeLine("hello");     // 输出：1. HELLO
```

注意 `new NumberingWriter(...)` 与 `new UpperCaseWriter(...)` 的顺序会改变结果（大写先于编号 → `1. HELLO`；编号先于大写 → `1. HELLO` 但编号数字也被大写，若换成字母编号就能看出差别）。这就是课件第 25 页「破坏对象身份」的具体体现：`w` 不是 `ConsoleLineWriter`，`w instanceof ConsoleLineWriter` 为 `false`。

**示例 D：Composite——与 Decorator 的形态对比**

```java
public interface Shape { void draw(); }             // Component

public final class Rect implements Shape {          // Leaf
    public void draw() { System.out.println("rect"); }
}

public final class ShapeGroup implements Shape {    // Composite：持有多个
    private final List<Shape> children = new ArrayList<>();
    public void add(Shape s) { children.add(s); }
    public void draw() { for (Shape s : children) s.draw(); }
}
```

对比 Decorator：Composite 持有**多个**同类型对象（一对多，树），Decorator 持有**一个**（一对一，链）。两者都让「容器」实现与「元素」相同的接口，但一个是**聚合**，一个是**包装**。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| **Composite** | **Decorator** | 前者是**一对多**的树（聚合多个子组件，`draw()` 遍历全部）；后者是**一对一**的链（包装一个组件，加前后行为）。前者「把多个当一个」，后者「把一个变成更强的那个」 |
| **Template Method** | **Strategy** | 前者用**继承**固定骨架、子类填步骤，编译期绑定；后者用**组合**持有整个算法，运行期可换。前者「步骤可变」，后者「算法可变」 |
| **Strategy** | **State** | 结构几乎相同（都是上下文持有接口对象并委托），但意图不同：Strategy 是**客户端选择**算法，State 是**对象内部状态变化**驱动行为切换，状态之间会互相转换 |
| **Decorator** | **Proxy** | 都是「包装同接口对象」。Decorator 目的是**添加职责**（可叠加多层）；Proxy 目的是**控制访问**（延迟加载、权限、远程代理），通常只有一层 |
| **Decorator** | **Adapter** | 前者包装**同接口**的对象（接口不变）；后者把**不同接口**转成目标接口（接口改变） |
| **Decorator** | **继承** | 继承在**编译期**静态地给**整类**添加行为；Decorator 在**运行期**动态地给**单个对象**添加行为，且可撤销 |
| **`«final»` 模板方法** | 普通可覆写方法 | `final` 保证骨架不被绕过；若子类能覆写 `templateMethod()`，整个模式失效。所以 `final` 不是风格，是**语义要求** |
| **好莱坞法则** | 普通回调 | 两者都是「被调用」，但好莱坞法则强调**控制权反转**：调用时机由框架决定，你只提供钩子 |
| **`read(byte[])`** | `read()` | 前者是**便利方法**（基于 `read()` 循环实现），后者是 `abstract` 的**必须实现**方法。这是「最小接口 + 派生便利方法」的设计 |
| **`PrintStream` 的重载 `print`** | 单一 `print(Object)` | 重载在编译期分派，避免装箱与运行时 `instanceof`；单一 `Object` 版更「统一」但更慢且更易错 |
| **模式 = 代码模板** | 模式 = 问题-解法对应 | 课件第 2 页：Alexander 强调「用一百万次而不重样」。模式**必须被特化**，照抄 UML 不是用模式 |

## 8. 对应原版讲义

- PDF 相对路径：`90-原始PDF/15-214/slides/09-design-patterns-continued.pdf`
- 总页数：27 页
- 重点页码：
  - 第 1 页：封面（标题为「Design Patterns and Java I/O」）
  - 第 2 页：Alexander 的模式定义、「每个 Composite 有自己的领域接口」
  - 第 3、5 页：Composite 的领域实例（`Shape`/`Rectangle`/`ShapeGroup`）
  - 第 4 页：模式四要素（Name/Problem/Solution/Consequences）
  - 第 6 页：Composite 的通用形式与「可能过度泛化」
  - 第 7 页：Template Method 的领域实例（`AbstractShape` 的 `draw()` 为 `final`）
  - 第 8 页：Template Method 的通用形式与好莱坞法则
  - 第 9 页：Virtual World 作业中的模板方法（指向 Piazza 帖）
  - 第 10 页：断行算法的三种实现（Blind/Greedy/Global）与「放进 `Paragraph` 的四条反对理由」
  - 第 11 页：把断行策略封装成对象
  - 第 12 页：Strategy 的通用形式与「固定接口开销过高」
  - 第 13 页：Virtual World 作业中的 Strategy
  - 第 14 页：`sort(int[], String)` vs `sort(int[], Comparator)` 代码对照
  - 第 15 页：三条基本原则、「模式是被发现的」
  - 第 16 页：三条原则如何生成 Strategy、用继承实现的两个 drawback、函数式语言的实现
  - 第 17 页：GoF 三分类与 UML 图来源
  - 第 18 页：必知模式清单（含 MVC）
  - 第 19–20 页：`System.out` 是 `PrintStream`，及其重载方法
  - 第 21–22 页：流抽象 `InputStream`/`OutputStream`，`abstract` 标记与便利方法
  - 第 23 页：设计问题——如何给流添加功能
  - 第 24 页：Decorator 结构与 `super.operation()` 骨架
  - 第 25 页：Decorator 的适用性与后果（破坏身份、大量小对象）
  - 第 26 页：`FilterOutputStream` 作为 Decorator
  - 第 27 页：Decorator 名称的由来（GUI 滚动条）
- 原始网页链接：`https://www.cs.cmu.edu/~aldrich/214/slides/09-design-patterns-continued.pdf`

> 待核实：`09-design-patterns-continued.pdf` 第 1 页页脚标注为 **Spring 2013**（版权行 `© 2012-13 C Kästner, C Garrod, J Aldrich, and W Scherlis`），与 Fall 2013 学期不符，应为复用旧封面所致，已按 Fall 2013 归档。第 14 页 `UpComparator`/`DownComparator` 中的 `compare(int I, int j)` 参数名写成大写 `I`，属排版错误。

## 9. 对应视频

未找到官方公开录像。2013 年秋季的 15-214 课堂没有公开发布录像，故不提供链接与时间戳。

## 10. 本节复习

- 模式 = 反复出现的问题 + 解法核心，**可复用一百万次而不重样**；模式有名称、问题、解法（抽象，须特化）、后果四要素。
- 每个模式都有代价；「consequences」是理解模式的关键，比 UML 图重要。
- Composite：部分-整体，容器与叶子同接口；代价是可能过度泛化。
- Template Method：父类 `final` 骨架 + 子类钩子；好莱坞法则；代价是继承耦合、不能运行期换算法。
- Strategy：把整个算法抽成接口，上下文**组合**持有；代价是对象与间接层、简单算法开销过高。
- 用继承实现 Strategy 的两个致命缺陷：上下文与算法耦合、无法动态改变算法。
- Strategy 在函数式语言里就是「传一个函数」；Java 8 lambda 让 `Comparator` 一行可写。
- 三条基本原则（面向接口、优先组合、封装变化）是模式的**生成器**，模式是它们被**发现**的结果。
- Java I/O 用 Decorator：`FilterOutputStream` 既是 `OutputStream` 又持有一个 `OutputStream`，从而可无限嵌套（压缩+加密+缓冲）。
- Decorator 的两条代价：破坏对象身份（`instanceof`/`==` 失效）、大量小对象。
- 若用继承给流加功能，n 种功能需要 2^n 个子类——这是 Decorator 存在的根本理由。

## 11. 自我检查

1. 下面这个设计违反了哪条基本原则？请用 Strategy 重构，并说明重构后新增一种「按长度降序」排序需要改哪些文件。
   ```java
   void sort(int[] list, String order) {
       boolean mustswap;
       if (order.equals("up"))        mustswap = list[i] < list[j];
       else if (order.equals("down")) mustswap = list[i] > list[j];
       …
   }
   ```
2. 为什么 Template Method 的 `templateMethod()` 必须声明为 `final`？如果去掉 `final` 会发生什么？请举一个具体的破坏方式。
3. Decorator 和 Composite 都能让「容器」与「元素」实现同一接口，但它们的结构与意图完全不同。请分别说明：各持有几个同类型对象？各自解决什么问题？各举一个 Java 标准库或常见框架中的例子。
4. 有人提议给 `OutputStream` 加一个 `compress()` 方法，用一个布尔参数控制是否压缩，再用一个 `encrypt()` 方法控制加密。请说明这个方案在「功能组合」上会遇到什么问题，并给出正确的替代方案。
5. 判断下列场景应当用 Template Method 还是 Strategy，并说明理由：
   (a) 一个报表生成器，输出格式（PDF/HTML/CSV）在程序运行中由用户切换；
   (b) 一个测试框架，要求「setUp → 运行测试 → tearDown」的顺序绝对不能被使用者改变。

<details>
<summary>参考答案</summary>

1. 违反了**「找出变化点并封装它」**（以及由此推出的**开闭原则**）：变化的「比较顺序」被硬编码成 `if-else` 分支，新增一种顺序必须修改 `sort` 本身。重构：
   ```java
   interface Comparator { boolean compare(int i, int j); }
   void sort(int[] list, Comparator cmp) {
       boolean mustswap = cmp.compare(list[i], list[j]);
       …
   }
   class UpComparator   implements Comparator { public boolean compare(int i,int j){ return i < j; } }
   class DownComparator implements Comparator { public boolean compare(int i,int j){ return i > j; } }
   ```
   新增「按长度降序」只需**新建一个类** `class ByLengthDescComparator implements Comparator`，`sort` 与已有比较器**一行都不用改**——这就是「对扩展开放、对修改关闭」。同时拼错策略名的风险消失（编译期检查替代运行时字符串比较）。
2. 因为 `final` 是**算法骨架不可协商**的强制执行手段。若去掉 `final`，子类可以完全覆写 `templateMethod()`，绕过骨架中的关键步骤。具体破坏方式：假设 `AbstractShape.draw()` 是 `final` 的，实现为 `doDraw(); doUpdate();`。若去掉 `final`，某个子类写出
   ```java
   @Override public void draw() { doDraw(); }   // 忘了 doUpdate()
   ```
   编译完全通过，但「变更通知」被静默丢弃——屏幕不再重绘，而这种 bug 极难定位（没有任何异常，只是画面不更新）。课件第 7 页的原始动机正是「未来 shape 实现不应忘记更新」，`final` 就是把这条约定从「文档」变成「编译器强制」。
3. **Composite**：持有**多个**同类型对象（`List<Component>`），组织成**树**；解决「部分-整体层次」问题，让客户端把一组对象当作一个对象处理。例子：`java.awt.Container`（持有多个 `Component`，自身也是 `Component`）、文件系统的 `Directory`/`File`、`07-design-patterns.pdf` 里的 `IntSet`/`UnionSet`。
   **Decorator**：持有**一个**同类型对象，形成**链**；解决「动态、透明地给单个对象添加可撤销的职责」问题。例子：`java.io.FilterOutputStream` 及其子类（`BufferedOutputStream`、`GZIPOutputStream`、`CipherOutputStream`）、`Collections.unmodifiableList(...)`、Servlet API 的 `HttpServletRequestWrapper`。
   一句话区分：Composite 是**聚合**（一 → 多），Decorator 是**包装**（一 → 一）。
4. 这个方案会遇到**组合爆炸**与**职责膨胀**两个问题：
   - `compress(boolean)` 与 `encrypt(boolean)` 两个开关只能表达 4 种组合，但功能种类一旦增加到 n 种，`OutputStream` 就需要 n 个布尔参数（2^n 种组合），而每加一种功能都要**修改 `OutputStream` 本身**——违反开闭原则；
   - `OutputStream` 会被迫承担压缩、加密、校验和等所有职责，变成课件第 25 页所说的「monolithic class」（单体巨类），任何一处改动都可能影响全部使用者；
   - 布尔参数在调用点不可读：`new FileOutputStream(f, true, false, true)` 完全看不出含义。
   正确方案是 **Decorator**：每种功能一个包装类，都实现 `OutputStream` 并持有一个 `OutputStream`，客户端按需嵌套：
   ```java
   OutputStream out = new CipherOutputStream(
                          new GZIPOutputStream(
                              new BufferedOutputStream(
                                  new FileOutputStream(f))), key);
   ```
   新增功能只需新增一个类，`OutputStream` 与已有装饰器都不改；功能组合通过**嵌套顺序**表达，无需 2^n 个子类。代价是对象数量增加、且 `out` 不再 `instanceof FileOutputStream`（破坏身份）。
5. (a) **Strategy**。理由是「运行中由用户切换」——需要**运行期**替换算法。Template Method 用继承，一个 `PdfReport` 对象永远是 PDF 格式，无法在运行时变成 HTML。用 Strategy：`ReportGenerator` 持有 `OutputFormat` 接口，用户切换时 `setFormat(new HtmlFormat())` 即可。
   (b) **Template Method**。理由是「顺序绝对不能被使用者改变」——这正是 `final` 骨架的用途：
   ```java
   public final void run() { setUp(); try { test(); } finally { tearDown(); } }
   ```
   JUnit 3 的 `TestCase`（`setUp`/`testXxx`/`tearDown`）就是这种形态。若用 Strategy，使用者可以自己决定调用顺序，保证就消失了；而 Template Method 通过 `final` 把顺序锁死，只暴露钩子。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-08-Specification-and-Testing]]
- 下一讲：[[15-214-10-Conceptual-Modeling]]
- 课程总览：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]
- 课程目录：[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸：GoF《Design Patterns》原书对 Strategy/Template Method/Decorator 的完整讨论；Shalloway & Trott《Design Patterns Explained》（本课教材）用「星巴克咖啡」讲 Decorator；Java 8 之后 Strategy 可用 lambda 简化；`java.io` 与 `java.nio` 的设计对比能看清 Decorator 的代价。本讲的 Java I/O 内容会与 [[15-214-16-Frameworks]] 中「框架 vs 库」的讨论呼应——好莱坞法则正是框架的定义性特征。
