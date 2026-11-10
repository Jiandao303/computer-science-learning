---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L11
topic: Design Principles - GRASP, Modularity and Information Hiding
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - GRASP
  - 信息隐藏
  - 模块化
  - 耦合
  - 内聚
  - 职责分配
  - Parnas
  - CRC 卡
---

# 第 11 讲 设计原则：GRASP 与信息隐藏

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。本讲合并同一天的两份 slides：`design-grasp.pdf`（76 页，标题 "Design: GRASP and Refinement"）与 `design-information-hiding.pdf`（35 页，标题 "Design and Information Hiding"，页脚日期 1 October 2013）。

## 1. 本节学习目标

- 能说明「职责（responsibility）」的两大类型（knowing / doing），并据此为类分配方法。
- 能列举并解释 GRASP 九原则，尤其是 Information Expert、Creator、Low Coupling、High Cohesion、Controller 五个基础原则。
- 能用耦合与内聚的**具体形式**（属性引用、方法参数、继承、实现接口）评估两个设计方案。
- 能复述 Parnas 1972 年 KWIC 案例的两种模块化方案，并说明信息隐藏分解为什么在变化面前更优。
- 能区分**功能分解**与**信息隐藏分解**，并说明「接口」在概念上包含哪些内容（不止函数签名）。
- 能列出 Meyer 的模块化五准则与四条接口规则，并用它们评价一个设计。
- 能用 CRC 卡做职责分配，并知道如何验证（validation）。

## 2. 前置知识

- [[15-214-10-Conceptual-Modeling]]：领域模型是 GRASP 的输入——先有概念，才谈职责分配。
- [[15-214-03-Encapsulation-and-Inheritance]]：封装与可见性，是信息隐藏在语言层面的落地手段。
- [[15-214-06-Mutability-and-Java-Potpourri]]：表示暴露与防御性拷贝，与「Explicit Interfaces」「信息隐藏」直接相关。
- [[15-214-09-Design-Patterns-Continued]]：Strategy 等模式与 GRASP 原则互为表里。
- 外部概念：UML 顺序图、CRC 卡、Parnas 1972 论文。

## 3. 核心概念

- **Responsibility（职责）**：对象在行为上的义务，分 **knowing（知道）** 与 **doing（做）** 两类。
- **GRASP**：General Responsibility Assignment Software Patterns，通用职责分配软件模式，九条原则。
- **Information Expert（信息专家）**：把职责分配给拥有完成该职责所需信息的类。
- **Creator（创建者）**：把创建 A 的职责分配给聚合/包含/记录/密切使用 A 的类 B。
- **Controller（控制器）**：把处理系统事件的职责分配给代表整体系统（facade）或用例（use case）的类。
- **Low Coupling / High Cohesion（低耦合 / 高内聚）**：评价性原则，贯穿所有设计决策。
- **Polymorphism（多态）**：用多态操作处理类型相关的行为变化，替代按类型分支。
- **Indirection（间接）**：在两者之间引入中间对象以解耦。
- **Pure Fabrication（纯虚构）**：为高内聚低耦合而虚构一个不对应领域概念的类。
- **Protected Variations（受保护的变化）**：识别变化点，用稳定接口包裹它。
- **Information Hiding（信息隐藏）**：Parnas 提出——每个模块隐藏一个「可能变化的设计决策」。
- **Functional Decomposition（功能分解）**：按主要处理步骤切分模块（与信息隐藏分解相对）。
- **Modularity（模块化）**：Meyer 的五准则 + 四条接口规则构成的可操作定义。
- **CRC Card（类-职责-协作卡）**：用卡片记录类名、职责、协作者的轻量设计方法。

## 4. 通俗理解

**设计到底在做什么？** 课件（`design-grasp.pdf` 第 2 页）引用了 Larman 的流程：

> "After identifying your requirements and creating a domain model, then add methods to the software classes, and define the messaging between the objects to fulfill the requirements."
>
> But how?
> - What method belongs where?
> - How should the objects interact?

三个问题看起来很朴素，但课件说这是「a critical, important, and non-trivial task」。原因在于：**领域模型只告诉你「有哪些东西」，不告诉你「谁该干什么」**。而「谁该干什么」决定了耦合、内聚、可扩展性——也就是第 10 讲说的内部质量。

**GRASP 是干什么的？**（第 3 页）

> The GRASP patterns are a learning aid to
> - help one understand essential object design
> - apply design reasoning in a **methodical, rational, explainable** way.

最后三个词是关键：**有条理的、理性的、可解释的**。GRASP 不是「必须遵守的规则」，而是让你在评审时能说清「我为什么把 `getTotal()` 放在 `Sale` 而不是 `Register`」的语言。课件第 5 页还特意补了一句：

> General principles, **may be overruled by others**.
> （一般性原则，可以被其他原则推翻。）

所以 GRASP 是**论据**，不是**法条**。

**为什么需要「设计词汇」？**（第 6 页）课件给了一段真实对话：

> **Fred**: "Where do you think we should place the responsibility for creating a `SalesLineItem`? I think a Factory."
>
> **Wilma**: "By Creator, I think `Sale` will be suitable."
>
> **Fred**: "Oh, right - I agree."

三句话就结束了讨论。如果没有「Creator」这个词，Fred 和 Wilma 就要花十分钟各自描述「谁持有谁」「谁初始化谁」——而结论其实是一样的。**词汇压缩了论证成本。**

## 5. 原理与推导

### 5.1 职责：knowing 与 doing

课件（`design-grasp.pdf` 第 4 页）：

> Responsibilities are related to the **obligations** of an object in terms of its behavior.
>
> Two types: **knowing** and **doing**.

| 类型 | 具体内容 |
|---|---|
| **Doing（做）** | 自己做某事（创建对象、做计算）；**发起**对其他对象的动作；**控制与协调**其他对象的活动 |
| **Knowing（知道）** | 知道私有的封装数据；知道相关联的对象；知道它能**推导或计算**出来的东西 |

这个二分非常有解释力，因为**每个方法都能归到其中一类**：

- `getTotal()` 是 knowing（它知道总额，或知道如何算出总额）；
- `addLineItem()` 是 doing（它改变自身状态）；
- `makePayment()` 在 `Register` 上是 doing（协调 `Sale` 与 `Payment`）。

最后一条「知道它能推导或计算出来的东西」容易被忽略。`Sale.getTotal()` 并没有把总额存成字段，它**计算**出来——但它仍然「知道」这个值，因为它是唯一拥有计算所需信息（`lineItems`）的对象。这正是 Information Expert 的基础。

### 5.2 GRASP 九原则总览

课件第 7 页列出九条：

| # | 原则 | 一句话 |
|---|---|---|
| 1 | **Low Coupling** | 分配职责以最小化耦合 |
| 2 | **High Cohesion** | 分配职责以保持高内聚 |
| 3 | **Information Expert** | 把职责给拥有所需信息的类 |
| 4 | **Creator** | 把创建职责给聚合/包含/记录/密切使用该对象的类 |
| 5 | **Controller** | 把系统事件处理给 facade 或用例控制器 |
| 6 | **Polymorphism** | 用多态处理类型相关的行为变化 |
| 7 | **Indirection** | 引入中间者解耦 |
| 8 | **Pure Fabrication** | 虚构一个非领域类以获得高内聚低耦合 |
| 9 | **Protected Variations** | 用稳定接口包裹可预见的變化点 |

前五条是课件重点展开的（第 50 页总结也只列了 Information Expert、Creator、Low Coupling/High Cohesion、Controller），后四条在 `design-grasp.pdf` 中没有单独展开页——它们与第 9 讲的模式直接对应（Polymorphism ≈ Strategy/Template Method，Indirection ≈ Adapter/Mediator，Pure Fabrication ≈ 各种 Service/Repository 类，Protected Variations ≈ 一切封装变化点的模式）。这是本讲的**原文覆盖局限**，笔记在此标注，不做臆造展开。

### 5.3 Low Coupling：定义、形式与反例

课件第 8 页的三段式：

> **Problem**: How to increase reuse and decrease the impact of change.
> **Solution**: Assign responsibilities to minimize coupling.
> **Use this principle when evaluating alternatives.**

注意第三条：Low Coupling 是**评价性**原则（evaluative principle），不是生成性原则——它不告诉你「职责放哪」，只在你有了几个候选方案后帮你比较。第 16 页再次强调：

> It is an **evaluative principle** that a designer applies while evaluating all design decisions.

**耦合的定义**（第 13 页）：

> Coupling is a measure of how strongly one element is connected to, has knowledge of, or relies on other elements.

高耦合的三条害处：

- 相关类的变化**迫使**本类改动；
- 难以**孤立地**理解（读懂它必须先读懂它依赖的一堆东西）；
- 难以**复用**（复用它必须把依赖一起搬过来）。

**耦合的四种具体形式**（第 15 页，这是最实用的一页）：

| 形式 | 说明 |
|---|---|
| **属性耦合** | `TypeX` 有一个属性（数据成员/实例变量）引用 `TypeY` 的实例，或 `TypeY` 本身 |
| **方法耦合** | `TypeX` 有方法通过任何方式引用 `TypeY` 的实例或 `TypeY` 本身——通常是参数、局部变量，或某个消息返回 `TypeY` |
| **继承耦合** | `TypeX` 是 `TypeY` 的直接或间接子类 |
| **实现耦合** | `TypeY` 是接口，`TypeX` 实现了它 |

有了这张表，「耦合高不高」就从感觉变成了**可数**的东西：数一数这个类引用了多少个其他类型。

### 5.4 Low Coupling 的案例：`Register` 要不要 `new Payment()`

课件第 9–12 页用同一个场景对比两种职责分配。

**场景**：创建 `Payment` 并与 `Sale` 关联。

**方案 A**（第 10 页顺序图）：

```
:Register          :Sale           p :Payment
makePayment()
  1: create()  ------------------->  (创建 Payment)
  2: addPayment(p) ---------------->  (关联)
```

即 `Register` 自己 `new Payment()`，然后调用 `sale.addPayment(p)`。

**方案 B**（第 11 页顺序图）：

```
:Register          :Sale              :Payment
makePayment()
  1: makePayment() ------------>
        1.1: create()  -------------------->
```

即 `Register` 只调用 `sale.makePayment()`，由 `Sale` 自己创建 `Payment`。

**结论**（第 12 页）：

> Second solution has less coupling. **Register does not know about Payment class.**

这就是 Low Coupling 的具体应用：方案 B 中 `Register` 的代码里根本不出现 `Payment` 这个类型名，所以 `Payment` 的构造方式变化（比如需要传入币种、需要工厂）不会波及 `Register`。

而且注意：**方案 B 同时也符合 Creator 原则**——`Sale` 记录（records）`Payment` 实例，所以 `Sale` 应该负责创建它。两个原则在这里指向同一答案，这正是课件第 16 页说的「Can't be considered in isolation from other patterns such as Expert and High Cohesion」。

### 5.5 Low Coupling 的两条重要限定

课件第 17 页给出两个必须知道的限定，它们让这条原则不至于被滥用：

**（1）继承是一种特别糟糕的耦合形式**

> Subclassing produces a particularly problematic form of high coupling
> - Dependence on implementation details of superclass
> - **-> Prefer composition over inheritance**

这一条把第 3 讲的「优先组合」从「风格建议」提升为「耦合分析结论」：子类依赖的不只是父类的**接口**，还有它的**实现细节**（比如父类方法内部调用了哪些可覆写方法、字段的初始化顺序）。这就是所谓的「脆弱基类问题（fragile base class problem）」。

**（2）极低的耦合可能导致糟糕的设计**

> Extremely low coupling may lead to a poor design
> - **Few incohesive, bloated classes do all the work; all other classes are just data containers**

这是反面警告：如果你把耦合压到极低，结果往往是「一两个巨大的类干所有活，其他类只是数据容器」。这时耦合确实低了，但**内聚崩了**——那个巨类承担了太多不相关的职责。这正是需要 High Cohesion 来平衡的原因。

**（3）反例条件（contraindication）**

> High coupling to **very stable** elements is usually not problematic.

依赖 JDK 的 `String`、`List` 不算问题，因为 `String` 不会变。**耦合的代价 = 依赖强度 × 变化的可能性**，稳定元素的变化概率接近零，所以耦合代价也接近零。

### 5.6 High Cohesion

课件第 18 页：

> **Problem**: How to keep complexity manageable.
> **Solution**: Assign responsibilities so that cohesion remains high.
>
> Cohesion is a measure of how strongly related and focused the responsibilities of an element are. An element with highly related responsibilities, and which does not do a tremendous amount of work, has **high cohesion**.

**四种内聚程度**（第 23 页）：

| 程度 | 描述 |
|---|---|
| **Very Low（极低）** | 一个类独自负责许多**完全不同功能领域**的事情 |
| **Low（低）** | 一个类独自负责**一个功能领域内**的一项复杂任务 |
| **High（高）** | 一个类在**一个功能领域内**承担**适度**的职责，并与其他类**协作**完成任务 |

注意「Low」这一档很有意思：它并不是「跨领域」，而是「一个领域内但独自扛下一整件复杂任务」。课件认为这仍然不够好，因为**协作**才是高内聚的标志——适度的类 + 明确的协作，比一个能干的巨类更好。

**经验法则**（第 23 页）：

> a class with high cohesion has a **relatively small number of methods**, with **highly related functionality**, and **does not do too much work**.

**内聚的好处**（第 19 页）：易维护、易理解、**常常支持低耦合**、因职责粒度细而支持复用。

「常常支持低耦合」这个措辞很谨慎——不是「必然」。一个高内聚的类仍然可能依赖很多类型；但职责聚焦的类通常需要的协作者也更少。

### 5.7 内聚的案例：`Register` 的职责膨胀

课件第 20 页对方案 A（`Register` 自己创建 `Payment`）给出评价：

> (except for cohesion), looks OK if `makePayment` considered in isolation, but **adding more system operations, `Register` would take on more and more responsibilities and become less cohesive**.

这是内聚评估的**正确方法**：不要只看单个方法，要看**这个类随着系统演进而会变成什么**。`makePayment` 一个方法里 `new Payment()` 看起来无害；但当 `Register` 还要处理 `enterItem`、`endSale`、`makeNewSale`、打印小票、连接秤、计算税……它就会变成一个「上帝类（god class）」。

第 21 页把两个方案并排，第 22 页插入一个「Extra: isVisited」的反例：

```java
class Graph { 
    Node[] nodes; 
    boolean[] isVisited; 
}

class Algorithm { 
    int shortestPath(Graph g, Node n, Node m) { 
        for (int i; …)  
            if (!g.isVisited[i]) { 
                …
                g.isVisited[i] = true; 
            } 
        return v; 
    } 
}
```

这个例子演示**信息泄露导致的内聚问题**：`isVisited` 是**算法**的临时状态（某次最短路径搜索中访问过哪些节点），却放在了 `Graph` 里。后果：

- `Graph` 承担了「图结构」+「算法执行状态」两种不相关的职责 → 内聚降低；
- 两个算法**不能并行**运行（共享 `isVisited` 数组）；
- `Graph` 的接口暴露了算法细节 → 客户端可能误用。

正确做法是把 `isVisited` 变成 `shortestPath` 的局部变量（或封装在算法自己的辅助对象里）。这个例子与第 8 讲「类不变式」呼应：**一个字段如果只在某个方法的执行期间有意义，它就不该是对象的字段**。

### 5.8 Information Expert

课件第 24–30 页是 GRASP 中最核心的一条。

**问题**（第 24 页）：谁应该负责知道一次销售的总额（grand total）？

领域模型（第 24、34 页）：

```
Register 1 ──Captured-on──> * Sale
Sale 1 ──Contains──> 1..* SalesLineItem
SalesLineItem * ──Described-by──> 1 ProductDescription
Sale * ──Paid-by──> 1 Customer
```

**解法**（第 25 页）：

> **Problem**: What is a general principle of assigning responsibilities to objects?
> **Solution**: Assign a responsibility to the **information expert**, the class that has the information necessary to fulfill the responsibility.

**推导过程**（第 26 页）：

- 确定总额需要什么信息？→ **各行项（line items）及其小计之和**。
- 谁拥有 `lineItems`？→ `Sale`。
- 所以 `Sale` 是这项职责的信息专家 → `Sale.getTotal()`。

**但职责不会只落在一处**（第 27–28 页）。课件指出：

> To fulfill the responsibility of knowing and answering the sale's total, **three responsibilities were assigned to three design classes**.

```
:Sale                    lineItems[i] :SalesLineItem      :ProductDescription
t = getTotal()
   1 *: st = getSubtotal()
                              1.1: p := getPrice()  -------->
```

- `Sale.getTotal()`：需要 `lineItems` → 它是「总额」的专家；
- `SalesLineItem.getSubtotal()`：需要 `quantity` 与单价 → 它是「小计」的专家；
- `ProductDescription.getPrice()`：拥有 `price` → 它是「价格」的专家。

这是 Information Expert 最重要的特征：**它把一个职责递归地分解到多个类上**。`getTotal()` 不是「把所有逻辑写在一个方法里」，而是「沿着信息的分布逐层委托」。

第 28 页还标注了 `getPrice()` 是 **New method**——说明这一步设计**新增**了一个方法，而不是照搬领域模型。这印证了第 25 页那句：

> Design Classes (Software Classes) instead of Conceptual Classes. If Design Classes do not yet exist, look in Domain Model for fitting abstractions (**-> low representational gap**).

### 5.9 Information Expert 的哲学：「Do It Myself」

课件第 29 页有一段很有洞察力的话：

> Expert usually leads to designs where a software object does those operations that are normally done **to** the inanimate real-world thing it represents
> - a sale does not tell you its total; it is an inanimate thing
>
> In OO design, **all software objects are "alive" or "animated"**, and they can take on responsibilities and do things. They do things related to the information they know.

这段话点出了 OO 与「数据 + 过程」思维的分野。在现实世界里，一张销售单是**被动**的纸，你得自己拿计算器算总额；在 OO 里，`Sale` 是**活的**，你问它 `getTotal()`，它自己算。所以 Information Expert 又叫 **"Do It Myself Strategy"**——**拥有信息的对象自己动手**。

这个转变的收益是**封装**：总额的计算逻辑和数据（`lineItems`）待在一起，而不是散落在客户端。客户端不需要知道「总额 = 各行项小计之和」，它只需要问。

### 5.10 Information Expert 的两条反例

课件第 30 页给出两条 contraindication，它们同样重要：

**（1）与关注点分离冲突**

> Example: Who is responsible for saving a sale in the database?
> Adding this responsibility to `Sale` would **distribute database logic over many classes** → low cohesion.

`Sale` 确实「知道」自己要存什么，按 Expert 它该负责持久化。但这样一来，**每个领域类都要写 SQL/ORM 代码**，数据库逻辑散布在几十个类里——内聚崩溃。所以持久化职责应该交给一个专门的类（如 `SaleRepository`）——这正是 **Pure Fabrication** 原则的应用：虚构一个不对应领域概念的类，换取高内聚低耦合。

**（2）与延迟绑定（late binding）冲突**

> Late binding is available only for the receiver object. But maybe the variability of late binding is needed in some **method argument** instead.
> - So make the argument the receiver instead.
> - Example: use a **strategy pattern** to compute the total. Different strategies may capture special discounts.

在 Java 里，动态分派只作用于**接收者**（`obj.method()` 中的 `obj`）。如果变化点在**参数**上（比如「不同的折扣算法」），Expert 会把 `getTotal()` 放在 `Sale` 里，然后用 `if (discountType == ...)` 分支——这就失去了多态。

解法是把参数变成接收者：让 `Sale` 持有/接收一个 `DiscountStrategy`，调用 `strategy.computeTotal(lineItems)`。**这时 Strategy 原则压倒了 Expert 原则**——课件第 5 页说的「may be overruled by others」在这里得到验证。

### 5.11 Creator

课件第 31–36 页。

**问题**（第 31 页）用四个具体提问开场：

- 谁创建 `Graph` 里的 `Node`？
- 谁创建 `SalesLineItem` 的实例？
- 谁创建游戏里的 `Rabbit-Actor`？
- 谁创建大富翁（Monopoly）里的 `Tile`？
  - AI？Player？Main 类？Board？Meeple（狗棋子）？

**直觉答案**（第 32 页）：

> Typical Answer: The board. **Container creates things contained.**

**原则**（第 33 页）：

> Assign class B responsibility of creating instance of class A if
> - B **aggregates** A objects
> - B **contains** A objects
> - B **records** instances of A objects
> - B **closely uses** A objects
> - B has the **initializing data** for creating A objects
>
> Where there is a choice, prefer B aggregates or contains A objects.
>
> **Key idea**: Creator needs to keep reference anyway and will frequently use the created object.

五条判据的顺序有讲究：前两条（聚合/包含）最强，所以「有选择时优先」。核心逻辑是**避免多余的引用**：如果 B 反正要持有 A 的引用（聚合/包含/记录），那让 B 创建 A 就不增加任何耦合；如果让 C 创建再传给 B，就多了一条 C→A 的依赖。

**应用**（第 34–35 页）：谁创建 `SalesLineItem`？按 Creator，答案是 `Sale`——因为 `Sale` **contains** `1..*` 个 `SalesLineItem`。顺序图即 5.4 节方案 B 的形态。

**代价**（第 36 页）：

> Promotes low coupling by making instances of a class responsible for creating objects they need to reference. By creating the objects themselves, they avoid being dependent on another class to create the object for them.
>
> **Contraindications**:
> - creation may require significant complexity, such as
>   - using **recycled instances** for performance reasons
>   - **conditionally creating an instance from one of a family of similar classes** based upon some external property value
> - Sometimes desired to **outsource object wiring ("dependency injection")**

第二条 contraindication 就是 **Factory Method / Abstract Factory** 的适用场景：如果创建时要在「一族相似类」中按外部属性选择，把 `if-else` 塞进 `Sale` 会让 `Sale` 依赖整族类——这时应该引入工厂。第三条则指向现代框架的依赖注入（Spring 等）：对象自己 `new` 依赖，会让它无法被替换、无法测试（回想第 8 讲的 Mock Object）。

### 5.12 Controller

课件第 37–41 页。

**问题**：谁应该负责处理一个输入系统事件？

**解法**（第 37 页）：

> Assign the responsibility for receiving or handling a system event message to a class representing
> - the **overall system, device, or subsystem**（**facade controller**），或
> - a **use case scenario** within which the system event occurs（**use case controller**）

**POS 例子**（第 39 页）给出四个候选：

| 候选 | 类型 | 含义 |
|---|---|---|
| `Register` | Facade | 代表「设备」 |
| `POSSystem` | Facade | 代表整个「系统」 |
| `ProcessSaleSession` | Use Case | 代表「处理销售」这个用例 |
| `ProcessSaleHandler` | Use Case | 同上，Handler 风格命名 |

**讨论**（第 40 页）：

> Normally, a controller should **delegate** to other objects the work that needs to be done; it **coordinates or controls** the activity. It **does not do much work itself**.
>
> - Facade controllers are suitable when there are **not "too many"** system events.
> - A **use case controller** is an alternative when placing responsibilities in a facade controller leads to low cohesion or high coupling — typically when the facade controller is becoming **"bloated"** with excessive responsibilities.

**收益与警告**（第 41 页）：

> **Benefits**
> - Increased potential for **reuse, and pluggable interfaces**
> - **No application logic in the GUI**
> - Dedicated place to place **state that belongs to some use case**（e.g. operations must be performed in a specific order）
>
> **Avoid bloated controllers!**
> - E.g. single controller for the whole system, low cohesion, lots of state in controller
> - Split into use case controllers, if applicable
> - Interface layer does not handle system events

「No application logic in the GUI」这一条是 MVC 的雏形，会在第 12–13 讲（GUI）展开。「Interface layer does not handle system events」则明确了分层：**界面层只负责显示与收集输入，不负责业务决策**。

「Controller 不做多少工作，只协调」这条与内聚原则一致：Controller 的职责是**路由**，如果它开始做业务计算，就变成了 god class。

### 5.13 设计模型与实现

课件第 42 页给出「Resulting Design Model」的节选（UML 类图），包含：

```
SalesLineItem: quantity : Integer, getSubtotal()
ProductCatalog: ..., getProductDesc(...)
ProductDescription: description : Text, price : Money, itemID : ItemID
Store: address : Address, name : Text, addCompleteSale(...)
Payment: amount : Money
Register: ..., endSale(), enterItem(...), makeNewSale(), makePayment(...)
Sale: isComplete : Boolean, time : DateTime, becomeComplete(), makeLineItem(...), makePayment(...), getTotal()
```

关联标注包括 `catalog`、`register`、`currentSale`、`descriptions {Map}`、`lineItems {ordered}`、`payment`、`completedSales {ordered}`、`description`。

注意 `{ordered}` 与 `{Map}` 这样的**约束标注**——它们说明集合的语义（有序列表 / 映射），而不只是「一堆对象」。这在实现时直接决定用 `List` 还是 `Map`。

**从设计到实现**（第 43 页）：

> - Use Design Model as **roadmap** for implementation
> - Decision making and creativity **still required**
>   - Models typically **incomplete** at first
>   - Models foster better understanding and help making better implementation decisions
> - **Start with class with least dependencies**

最后一条是实用的实现顺序建议：先实现依赖最少的类（如 `SalesLineItem`、`ProductDescription`），因为它们可以被独立编译与测试；依赖多的类（`Register`）最后实现。这与「自底向上」的构建顺序一致，也让单元测试能逐层建立。

第 43 页同时给出映射示例：

```java
public class SalesLineItem {
    private int quantity;
    private ProductDescription description;
    public SalesLineItem(ProductDescription desc, int qty) { ... }
    public Money getSubtotal() { ... }
}
```

**关联的实现**（第 44 页，非常实用的一页）给出四种多重性组合到字段的映射：

| 关联 | X 侧 | Y 侧 | 实现 |
|---|---|---|---|
| `X 1 —— 1 Y` | `1` | `1` | `class X { Y a; }` / `class Y { X a; }`（双向） |
| `X 1 —— 0..n Y` | `1` | `0..n` | `class X { List<Y> a; }` / `class Y { X a; }` |
| `X 1 —— 1 Y`（单向） | `1` | （无） | `class X { Y a; }` / `class Y {}` |
| `X 0..n —— 0..n Y` | `0..n` | `0..n` | `class X { List<Y> a; }` / `class Y { List<X> a; }` |

这与第 10 讲 6.2 节的「多重性 → 字段类型」完全对应，只是这里给了完整的四象限表。要点：**多重性 `0..n`/`1..n` → `List`；`1` → 单个引用；双向关联两侧都要有字段（并需要维护一致性）**。

### 5.14 CRC 卡

课件第 45–46 页（`design-grasp.pdf`）与第 26–28 页（`design-information-hiding.pdf`）都讲了 CRC：

> **Class-Responsibility-Collaboration**
> - Name of class
> - Responsibilities/functionality of the class
> - Other classes it invokes to achieve that functionality

**四条职责准则**：

| 准则 | 理由 |
|---|---|
| **Spread out functionality（分散功能）** | 不要「上帝类」，它们让维护困难 |
| **State responsibilities generally（概括地陈述职责）** | 更可复用、更抽象 |
| **Group behavior with related information（把行为与相关信息放在一起）** | 增强内聚、降低耦合；**促进数据结构的信息隐藏** |
| **Information about one thing goes in one place（一个事物的信息放一处）** | 分散会让它难以追踪 |

第三条「Group behavior with related information」正是 Information Expert 的另一表述；第四条则是 Parnas 信息隐藏的通俗版本。

**验证（CRC Validation，第 46 页）**：

> - Ensure **all functionality in specification is covered** by some class
> - **Reason through how functionality could be achieved**
>   - Abstractly executing the program
>   - What other classes are needed?
>   - Are their responsibilities enough for this class to do what it needs to do?
> - Refine as needed

「抽象地执行程序（abstractly executing the program）」是 CRC 验证的精髓：拿一个用例，在脑子里（或白板上）逐个对象地走一遍消息传递，看每一步需要的信息是否都在某个类的职责范围内。这其实就是**用手工方式跑一遍顺序图**。

### 5.15 精化设计（Refining a Design）

课件第 47 页：

> - **Step through Use Cases**：验证图的完整性，问：哪些方法会执行？哪些方法被调用？每个方法或对象必须知道什么？
> - **Consider quality attributes**：用测试把属性具体化（如修改场景、性能目标）
> - **Generate multiple designs — not just one!**
>   - 什么设计模式能达到这个属性？
>   - 让不同的人独立设计可能有用
> - **Evaluate designs**：这个设计在**整组**质量属性上表现如何？可能需要**排优先级**。

第二条「用测试把属性具体化」很有操作性：不要说「这个设计更可扩展」，而要说「如果需求变成支持多币种，这个设计要改 1 个类，那个设计要改 5 个类」——这就是**修改场景（modification scenario）**，一种可执行的评估。

第三条「生成多个设计」呼应第 10 讲「设计的核心动作是比较」。课件甚至建议让不同人**独立**设计——因为独立设计能暴露你没想到的方案，避免群体思维。

### 5.16 阶段与术语总结

课件第 49 页给出三阶段对照，正好接上第 10 讲的「三种视角」：

| 阶段 | 产出 | UML 的角色 | 视角 |
|---|---|---|---|
| **Conceptual Modeling / OOA** | Domain Model / Conceptual Model | **sketching**（草图） | conceptual |
| **Object-Oriented Design** | Design Model / Object Model / Design Class Diagrams | **blueprint**（蓝图） | specification |
| **Implementation** | 代码 | **programming language**（代码生成） | implementation |

课件第 50 页的总结只列了四条 GRASP 原则（Information Expert、Creator、Low Coupling/High Cohesion、Controller），并再次强调「Design requires tradeoffs」。

第 51 页给出文献：

> - Craig Larman, *Applying UML and Patterns*, Prentice Hall, 2004
>   - Chapter 9 introduces conceptual modeling
>   - **Chapter 16+17+22 introduce GRASP**
> - Bertrand Meyer, *Object-Oriented Software Construction*, Prentice Hall, 1997
>   - **Chapter 3 and 4 discuss Design Goals and Modularity**

### 5.17 从 GRASP 到模块化：Meyer 的五准则

`design-grasp.pdf` 第 53–76 页（以及 `design-information-hiding.pdf` 第 32–35 页）转向「什么让一个设计更好」的根本问题。`design-information-hiding.pdf` 第 2 页给出回答：

> **What makes one design better than another?**
> - **Not** what result is produced, or whether it is right
> - Instead, **quality attributes**
> - **How** the result is produced
> - Characteristics of the code
>
> Examples: Evolvability, Local reasoning, Reuse, Robustness, Performance, Testability, security, fault-tolerance

「**Not** what result is produced」——这与第 10 讲「行为等价的程序有无穷多个」是同一句话的两种说法。

Meyer 的五条模块化准则（第 54–65 页）：

**（1）Modular Decomposability（模块可分解性）**

> 一种软件开发方法满足模块可分解性，如果它有助于把软件问题分解为**少量较简单的子问题**，这些子问题由**简单的结构**连接，并且**足够独立**，使得后续工作可以在每个子问题上**分别进行**。

POS 例子：数据模型、用户界面、打印小票、税务会计、管理界面、连接秤……课件点出关键收益：**Modular Decomposability implies: Division of Labor possible!**（可以分工）

**（2）Modular Composability（模块可组合性）**

> 如果一种方法有利于产生可**自由组合**以构建新系统的软件元素（可能在与最初开发完全不同的环境中），则满足模块可组合性。

- 与可分解性**对偶**；
- 直接关联**可复用性**；
- 例子：库在无数领域被成功复用；Unix shell 命令；
- POS 例子：复用现成的存储管理系统、接入 CRM 系统；
- **反例：预处理器（preprocessors）**——宏展开后的代码与上下文纠缠，无法独立组合。

**（3）Modular Understandability（模块可理解性）**

> 如果一种方法有助于产生这样的软件：人类读者**无需了解其他模块**就能理解每个模块，或者至多只需查看**少数几个**其他模块，则它有利于模块可理解性。

- 对维护至关重要；
- **适用于所有软件制品，不只是代码**（文档、构建脚本、配置）；
- **反例：模块之间的顺序依赖（sequential dependencies）**——你必须先读 A 才能读 B。

**（4）Modular Continuity（模块连续性）**

> 如果一种方法产生的架构中，问题规格的**一个小变化**只触发**一个模块**（或少数模块）的变化，则满足模块连续性。

- POS 例子：更换货币、更换税率、更换打印机；
- 例子：**符号常量**（而非魔法数字）；**在接口后面隐藏数据表示**；
- **反例：依赖硬件或编译器脆弱细节的程序设计**。

这一条就是「开闭原则」的 Meyer 版本，也是 Parnas 信息隐藏的直接目标。

**（5）Modular Protection（模块保护性）**

> 如果一种方法产生的架构中，某模块运行时发生的**异常状况**的影响会**局限在该模块内**，或至多传播到少数邻近模块，则满足模块保护性。

- 动机：**大型软件总会有 bug，故障不可避免**；
- POS 例子：打印机崩溃、扫描到未知商品；
- 例子：**防御式编程（defensive programming）**；
- **反例：一个模块里的空指针错误导致另一个模块出错**。

这一条把第 5 讲的异常处理提升为**架构准则**：异常不该穿透多层。它也与「Modular Protection」的字面意思一致——保护其他模块不受本模块故障影响。

**Direct Mapping / Low Representational Gap（直接映射 / 低表示差距）**（第 64–65 页）：

> 构建软件系统时设计的模块结构，应当与建模问题领域时设计的模块结构**保持兼容**。
> Follows from continuity and decomposability.

第 65 页用 `Payment` 对照两张图：UP Domain Model 里 `Payment` 是一个**概念**（`amount`，关联 `Sale` `Pays-for`）；UP Design Model 里 `Payment` 是一个**软件类**（`amount: Money`、`getBalance(): Money`）。课件强调：

> A `Payment` in the Domain Model is a **concept**, but a `Payment` in the Design Model is a **software class**. They are **not the same thing**, but the former **inspired** the naming and definition of the latter.
>
> This reduces the representational gap. **This is one of the big ideas in object technology.**

这段话精确回答了第 10 讲的「概念类 vs 软件类」——它们不是同一个东西，但名字与定义上的**连续性**降低了理解成本。

### 5.18 Meyer 的四条接口规则

课件第 66–74 页：

**（1）Few Interfaces（少接口）**

> 每个模块应当与**尽可能少**的其他模块通信。

- 想要**连接数少**的拓扑；
- 由连续性与保护性推出：否则变化/错误会传播得更广。

**（2）Small Interfaces（小接口）**

> 如果两个模块通信，它们应交换**尽可能少**的信息。

- 由连续性与保护性推出，且是**可组合性**的必要条件；
- **反例：大接口**（Big Interfaces）。

注意「Few」与「Small」是两个不同维度：Few 是**边的数量**，Small 是**每条边传输的信息量**。一个模块可以只连一个模块，但每次传一个巨大的结构体——Few 达标，Small 不达标。

**（3）Explicit Interfaces（显式接口）**

> 每当模块 A 与 B 通信，这必须能从 A 或 B（或两者）的接口中**明显看出**。

- **反例 1：全局变量**——A 写全局变量，B 读，接口上完全看不出来；
- **反例 2：别名（aliasing）——对共享堆结构的修改**——两个对象持有同一个可变对象的引用，一方的修改悄悄影响另一方。

第二个反例把第 6 讲的「别名与可变性」提升为**接口设计问题**：共享可变状态是一种**隐式接口**，它违反了 Explicit Interfaces。

**Intermezzo: Law of Demeter（迪米特法则）**（第 72 页）：

> LoD（或 **Principle of Least Knowledge**，最少知识原则）：每个模块应当对其它单元只有**有限的知识**——只了解与当前单元「密切」相关的单元。
>
> In particular: **Don't talk to strangers!**
>
> For instance, no `a.getB().getC().foo()`.
>
> Motivated by **low coupling**.

`a.getB().getC().foo()` 这种「火车残骸（train wreck）」式调用，让 A 依赖了 B、C 以及 C 的 `foo()`——三条耦合，其中两条是「陌生人的陌生人」。正确做法是让 B 提供一个 `b.doSomething()`，把 C 藏起来。

**（4）Information Hiding（信息隐藏）**

> 每个模块的设计者必须**选择该模块属性的一个子集**，作为关于该模块的**官方信息**，提供给客户端模块的作者。

第 75 页用 Monopoly 例子演示：

```java
// 违反信息隐藏
class Player { 
    Board board; 
    Square getSquare(String name) { 
        for (Square s: board.getSquares()) 
            if (s.getName().equals(name)) 
                return s; 
        return null; 
    }
}

// 遵守信息隐藏
class Player {  
    Board board; 
    Square getSquare(String n) { return board.getSquare(n); } 
}

class Board { 
    List<Square> squares; 
    Square getSquare(String name) { 
        for (Square s: squares) 
            if (s.getName().equals(name)) 
                return s; 
        return null; 
    }
}
```

第一个版本里，`Player` 需要知道 `Board` 内部有「一个可遍历的 `Square` 集合」——它依赖了 `Board` 的**数据表示**。第二个版本里，`Player` 只知道「`Board` 能按名字给我一个 `Square`」——数据表示（`List<Square>`）被 `Board` 藏起来了。**如果 `Board` 改用 `Map<String, Square>`，第二个版本的 `Player` 一行都不用改。**

第 76 页的总结列出全部十条：

> Modular Decomposability / Modular Composability / Modular Understandability / Modular Continuity / Modular Protection / Direct Mapping / Low Representational Gap / Few Interfaces / Small Interfaces / Explicit Interfaces / Information Hiding

## 6. 代码示例

### 6.1 官方课程代码

出自 `design-grasp.pdf` 第 22 页（`isVisited` 反例）：

```java
class Graph { 
    Node[] nodes; 
    boolean[] isVisited; 
}

class Algorithm { 
    int shortestPath(Graph g, Node n, Node m) { 
        for (int i; …)  
            if (!g.isVisited[i]) { 
                …
                g.isVisited[i] = true; 
            } 
        return v; 
    } 
}
```

出自同文件第 43 页（设计模型到代码的映射）：

```java
public class SalesLineItem {
    private int quantity;
    private ProductDescription description;
    public SalesLineItem(ProductDescription desc, int qty) { ... }
    public Money getSubtotal() { ... }
}
```

出自同文件第 44 页（关联的实现，四种多重性组合）：

```java
// 1 —— 1（双向）
class X { Y a; }
class Y { X a; }

// 1 —— 0..n
class X { List<Y> a; }
class Y { X a; }

// 1 —— 1（单向）
class X { Y a; }
class Y {}

// 0..n —— 0..n
class X { List<Y> a; }
class Y { List<X> a; }
```

出自同文件第 75 页（Monopoly 的信息隐藏对照）：

```java
class Player { 
    Board board; 
    Square getSquare(String name) { 
        for (Square s: board.getSquares()) 
            if (s.getName().equals(name)) 
                return s; 
        return null; 
    }
}

class Player {  
    Board board; 
    Square getSquare(String n) { return board.getSquare(n); } 
}

class Board { 
    List<Square> squares; 
    Square getSquare(String name) { 
        for (Square s: squares) 
            if (s.getName().equals(name)) 
                return s; 
        return null; 
    }
}
```

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：GRASP 五原则在同一个小设计中的权衡**

```java
// 违反 Creator + Low Coupling：Register 知道 Payment 的构造细节
public final class Register {
    private Sale currentSale;
    public void makePayment(Money amount) {
        Payment p = new Payment(amount);      // Register 依赖 Payment
        currentSale.addPayment(p);
    }
}

// 遵守 Creator（Sale records Payment）+ Low Coupling
public final class Sale {
    private final List<Payment> payments = new ArrayList<>();
    public Payment makePayment(Money amount) {
        Payment p = new Payment(amount);      // Sale 自己创建自己记录的对象
        payments.add(p);
        return p;
    }
}
```

`Register` 的代码里不再出现 `Payment` 类型名。若将来 `Payment` 需要新增币种参数，只改 `Sale`。

**示例 B：Information Expert 的递归分解**

```java
public final class Sale {
    private final List<SalesLineItem> lineItems = new ArrayList<>();
    // Sale 是「总额」的专家：它拥有 lineItems
    public Money getTotal() {
        Money total = Money.zero();
        for (SalesLineItem li : lineItems) total = total.plus(li.getSubtotal());
        return total;
    }
}

public final class SalesLineItem {
    private final int quantity;
    private final ProductDescription description;
    // SalesLineItem 是「小计」的专家：它拥有 quantity 与 description
    public Money getSubtotal() {
        return description.getPrice().times(quantity);
    }
}

public final class ProductDescription {
    private final Money price;
    // ProductDescription 是「价格」的专家
    public Money getPrice() { return price; }
}
```

三个类各答一段，`getTotal()` 沿信息分布逐层委托——这正是 `design-grasp.pdf` 第 28 页顺序图对应的代码。

**示例 C：Expert 被 Strategy 推翻（课件第 30 页的延伸）**

```java
// 只用 Expert：Sale 内部按类型分支，新增折扣类型要改 Sale
public Money getTotal() {
    Money total = sumOfLineItems();
    if (discountType == DiscountType.NONE)      return total;
    else if (discountType == DiscountType.VIP)  return total.times(0.9);
    else if (discountType == DiscountType.SEASON) return total.minus(fixedOff);
    ...
}

// Expert + Strategy：把变化点交给策略对象
public interface DiscountStrategy {
    Money apply(Money subtotal);
}

public final class Sale {
    private final DiscountStrategy discount;      // 组合
    public Money getTotal() { return discount.apply(sumOfLineItems()); }
}
```

`Sale` 仍然是「总额」的专家（它拥有行项），但「折扣怎么算」这个**变化点**被外置。这演示了课件第 5 页「General principles, may be overruled by others」。

**示例 D：Parnas 式信息隐藏——把「会变的决策」藏进模块**

```java
// 设计决策：行存储的物理表示（可能变化：内存数组 / 压缩编码 / 磁盘分页）
public interface LineStorage {
    String getLine(int index);
    int lineCount();
}

// 决策 A：全部放内存
final class InMemoryLineStorage implements LineStorage {
    private final List<String> lines;
    InMemoryLineStorage(List<String> lines) { this.lines = List.copyOf(lines); }
    public String getLine(int i) { return lines.get(i); }
    public int lineCount() { return lines.size(); }
}

// 决策 B：用编码压缩，接口不变
final class EncodedLineStorage implements LineStorage {
    private final byte[] blob;   // 完全不同的内部表示
    ...
    public String getLine(int i) { return decode(i); }
    public int lineCount() { return count; }
}
```

客户端只依赖 `LineStorage`（**稳定决策**），不依赖「是否压缩」（**易变决策**）。这正是 `design-information-hiding.pdf` 第 13 页的定义：**把每个可能变化的设计决策放进一个模块，给它一个隐藏该决策的接口**。

**示例 E：Explicit Interfaces 的反例——别名造成隐式耦合**

```java
// 违反 Explicit Interfaces：Client 通过共享可变列表悄悄影响 Repository
public final class Repository {
    private final List<String> items = new ArrayList<>();
    public List<String> getItems() { return items; }   // 泄漏内部表示！
}

Repository r = new Repository();
List<String> leak = r.getItems();
leak.clear();                    // 从接口上完全看不出这修改了 r 的内部状态

// 修正：接口显式、返回不可变视图或副本
public List<String> getItems() { return Collections.unmodifiableList(items); }
```

这是第 6 讲「表示暴露」与 Meyer「Explicit Interfaces」的交汇点：**别名让一条不存在于接口上的通信通道成立了**。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| **knowing 职责** | **doing 职责** | 前者是「知道」（私有数据、相关对象、可推导的值）；后者是「做」（自己计算/创建、发起他人动作、协调他人）。`getTotal()` 是 knowing，`addLineItem()` 是 doing |
| **Low Coupling** | **High Cohesion** | 前者看**模块之间**的依赖数量（要少）；后者看**模块内部**职责的相关度（要高）。压耦合过头会导致「一个巨类 + 一堆数据容器」，反而破坏内聚 |
| **Information Expert** | **Creator** | 前者问「谁有信息来完成这个职责」；后者问「谁该 `new` 这个对象」。二者常指向同一类（`Sale` 既记录 `Payment` 又创建它），但理由不同 |
| **Creator** | **Factory** | Creator 是「谁天然该创建」（聚合/包含/记录者）；Factory 是「创建逻辑复杂时的外置方案」（一族相似类中按外部属性选择、复用实例、依赖注入）——Creator 的 contraindication 正是 Factory 的适用场景 |
| **Facade Controller** | **Use Case Controller** | 前者代表整个系统/设备（`Register`、`POSSystem`），适合系统事件不多时；后者代表一个用例（`ProcessSaleHandler`），在 facade 变得臃肿（低内聚/高耦合）时拆分 |
| **Controller** | **god class** | 好的 Controller 只**协调与委托**，不做多少实际工作；一旦它开始承载业务逻辑与大量状态，就退化为 god class |
| **功能分解** | **信息隐藏分解** | 前者按**主要处理步骤**切分（输入→移位→排序→输出）；后者让每个模块**隐藏一个可能变化的设计决策**（如「行如何存储」）。Parnas 的 KWIC 案例证明后者在变化面前改动更少 |
| **耦合（coupling）** | **信息隐藏** | 耦合数「有多少依赖」；信息隐藏问「依赖的是**稳定**决策还是**易变**决策」。所以信息隐藏是更直接的「设计价值」度量（`design-information-hiding.pdf` 第 35 页） |
| **接口 = 函数签名** | **接口 = 客户端可依赖的一切** | 课件第 16 页：接口在概念上包括**性能、调用顺序、资源使用、加锁策略**——「everything clients are allowed to depend on」，且**未必能用你喜欢的语言表达** |
| **Few Interfaces** | **Small Interfaces** | Few 是**边的数量**少；Small 是**每条边传的信息量**少。两者独立：可以只连一个模块但每次传巨型结构 |
| **Modular Continuity** | **Modular Protection** | 前者管**正常变化**（需求小改只动一个模块）；后者管**异常状况**（运行时故障局限在模块内）。一个管变更成本，一个管故障传播 |
| **Modular Decomposability** | **Modular Composability** | 前者是「拆得开」（可分工）；后者是「拼得起」（可复用）。二者对偶 |
| **概念模型中的 `Payment`** | **设计模型中的 `Payment`** | 前者是**概念**（现实世界的支付）；后者是**软件类**（有字段与方法）。「它们不是同一个东西，但前者启发了后者的命名与定义」——这降低了表示差距 |
| **GRASP 原则** | **GoF 模式** | GRASP 是**分配职责的原则**（更基础、更抽象，如「给信息专家」）；GoF 模式是**具体的类结构方案**（如 Strategy、Adapter）。模式往往是 GRASP 原则的产物 |

## 8. 对应原版讲义

本讲对应两份 PDF。

**（1）GRASP 与精化**

- PDF 相对路径：`90-原始PDF/15-214/slides/design-grasp.pdf`
- 总页数：76 页
- 重点页码：
  - 第 1 页：封面（Fall 2013；"With slides from Klaus Ostermann"）
  - 第 2 页：对象设计的三问（方法放哪、对象如何交互）
  - 第 3–5 页：GRASP 的定位、职责二分（knowing/doing）、名称含义
  - 第 6 页：Fred 与 Wilma 的对话（模式词汇促进沟通）
  - 第 7 页：九原则清单
  - 第 8 页：Low Coupling 三段式定义
  - 第 9–12 页：`Register`/`Sale`/`Payment` 两个方案的顺序图对比
  - 第 13–14 页：耦合的定义与低耦合收益
  - 第 15 页：OO 中耦合的四种常见形式
  - 第 16–17 页：Low Coupling 的讨论、继承耦合、过度解耦的陷阱
  - 第 18–19 页：High Cohesion 定义与收益
  - 第 20–21 页：`Register` 职责膨胀的讨论
  - 第 22 页：`isVisited` 反例
  - 第 23 页：四种内聚程度与经验法则
  - 第 24–28 页：Information Expert（总额的例子、递归分解、顺序图）
  - 第 29 页："Do It Myself Strategy"
  - 第 30 页：Expert 的两条 contraindication（持久化、延迟绑定/Strategy）
  - 第 31–33 页：Creator 的提问、直觉答案、五条判据
  - 第 34–36 页：Creator 的例子与 contraindication（工厂、依赖注入）
  - 第 37–41 页：Controller（facade vs use case、讨论、收益与警告）
  - 第 42 页：Resulting Design Model 节选
  - 第 43 页：从设计到实现（先做依赖最少的类）+ `SalesLineItem` 代码
  - 第 44 页：关联实现的四象限表
  - 第 45–46 页：CRC 卡与验证
  - 第 47 页：精化设计（走用例、质量属性、多个设计、评估）
  - 第 49–51 页：阶段与术语总结、总结、文献（Larman ch.9/16/17/22；Meyer ch.3/4）
  - 第 53–65 页：Meyer 五准则（可分解、可组合、可理解、连续性、保护性）+ 低表示差距
  - 第 66–74 页：四条接口规则（Few/Small/Explicit/Information Hiding）+ 迪米特法则
  - 第 75 页：Monopoly 信息隐藏对照代码
  - 第 76 页：设计目标总结（十条）
- 原始网页链接：`https://www.cs.cmu.edu/~aldrich/214/slides/design-grasp.pdf`

**（2）设计与信息隐藏**

- PDF 相对路径：`90-原始PDF/15-214/slides/design-information-hiding.pdf`
- 总页数：35 页
- 重点页码：
  - 第 1 页：封面（标题 "Design and Information Hiding"，课程名写作 "15-214: Foundations of Software Engineering"，引用 Parnas 1972）
  - 第 2 页：什么让设计更好——质量属性
  - 第 3 页：KWIC 案例的 Parnas 原始定义与示例输出
  - 第 4–5 页：KWIC 的两种模块化（#1 功能分解 / #2 数据访问接口）
  - 第 6 页：KWIC 观察——运行时相似、代码不同
  - 第 7 页：软件变化（Brooks 1974、Belady & Lehman）
  - 第 8–9 页：五类变化对两种设计的影响对照（核心论证）
  - 第 10 页：其他因素（独立开发、可理解性）
  - 第 11 页：性能说明（编译器内联、不要过早优化）
  - 第 12 页：分解准则（功能分解 vs 信息隐藏分解）
  - 第 13 页：信息隐藏的五步定义与「big if」
  - 第 14–15 页：五类设计决策及其隐藏机制
  - 第 16 页：接口是什么（不止函数签名）
  - 第 17 页：Correspondence 与 Separation of Concerns
  - 第 20 页：规格是设计的起点
  - 第 23–25 页：名词提取找类（含 Coad & Yourdon 判据）
  - 第 26–28 页：CRC 卡与验证
  - 第 29 页：属性、关联、操作的识别
  - 第 30–31 页：质量属性与精化设计
  - 第 33–35 页：内聚、耦合、耦合与信息隐藏的关系
- 原始网页链接：`https://www.cs.cmu.edu/~aldrich/214/slides/design-information-hiding.pdf`

> 待核实：`design-information-hiding.pdf` 第 1 页把课程名写作 "15-214: Foundations of Software Engineering"，与官方课程名 "Principles of Software Construction: Objects, Design and Concurrency" 不一致（疑为该讲义早期版本的标题）；第 1 页页码缺失（无页码标注）。`design-grasp.pdf` 第 6 页对话中 "SalesLineltem" 为 `SalesLineItem` 的 OCR/排版错误（小写 L 误作大写 I），同类错误在 24、28、34、42 页的图中亦出现。另 `design-grasp.pdf` 第 15 页 "TypeX"/"TypeY" 的耦合四形式未给出 Polymorphism/Indirection/Pure Fabrication/Protected Variations 的展开页，这四条原则在本讲义中仅有清单式提及。

## 9. 对应视频

未找到官方公开录像。2013 年秋季的 15-214 课堂没有公开发布录像，故不提供链接与时间戳。

## 10. 本节复习

- 职责分 knowing 与 doing；每个方法都能归入其中一类。
- GRASP = 通用职责分配模式，九条：Low Coupling、High Cohesion、Information Expert、Creator、Controller、Polymorphism、Indirection、Pure Fabrication、Protected Variations。
- GRASP 是**可解释的论据**，不是法条——「may be overruled by others」。
- 耦合的四种形式：属性引用、方法引用（参数/局部变量/返回值）、继承、实现接口。
- 继承是特别糟糕的耦合（依赖父类实现细节）→ 优先组合；但耦合到**稳定**元素通常无害。
- 过度解耦会导致「少数臃肿类干所有活，其余只是数据容器」——必须与 High Cohesion 联合使用。
- Information Expert：把职责给拥有所需信息的类；它会把职责**递归分解**到多个类（`getTotal` → `getSubtotal` → `getPrice`）。
- Expert 的两条反例：持久化（会散布数据库逻辑）、延迟绑定（变化点在参数上时改用 Strategy）。
- Creator 五判据：聚合、包含、记录、密切使用、拥有初始化数据；核心是「反正要持有引用」。
- Controller：facade（整体系统）vs use case（单个用例）；只协调不干活；警惕臃肿。
- 关联实现：`1` → 单个引用，`0..n`/`1..n` → `List`，双向两侧都要字段。
- Parnas KWIC：功能分解（#1）在五类变化中改动面远大于信息隐藏分解（#2）。
- 信息隐藏 = 把**可能变化的决策**放进一个模块，接口只暴露**稳定决策**；它不只是数据表示（还有平台、I/O 格式、UI、算法）。
- 接口在概念上包含性能、调用顺序、资源使用、加锁策略——「客户端被允许依赖的一切」。
- Meyer 五准则：可分解、可组合、可理解、连续性、保护性；加低表示差距。
- 四条接口规则：Few（边少）、Small（信息少）、Explicit（无全局变量/别名）、Information Hiding。
- 迪米特法则：不要 `a.getB().getC().foo()`。

## 11. 自我检查

1. 下面两种职责分配，哪一种耦合更低？请用课件中「耦合的四种形式」逐条分析，并说明哪一种同时符合 Creator 原则。
   ```java
   // 方案 A
   class Register { void makePayment(Money amt) { Payment p = new Payment(amt); sale.addPayment(p); } }
   // 方案 B
   class Register { void makePayment(Money amt) { sale.makePayment(amt); } }
   ```
2. 「Low Coupling」被列为 GRASP 原则，但课件又警告「Extremely low coupling may lead to a poor design」。请解释这个表面矛盾，并说明应当用什么原则来平衡。
3. 用 Information Expert 推导「一次销售的总金额」这项职责该分配给谁。要求写出至少三层委托，并说明每一层依据的是什么信息。
4. Parnas 的 KWIC 案例中，面对「不要一次把所有行都放进内存」这一变化，设计 #1 需要改动所有模块，设计 #2 只需改动 Line Storage。请说明两种设计在**模块边界**上的根本差别，以及这与「接口 = 客户端被允许依赖的一切」有什么关系。
5. 下面的代码违反了 Meyer 的哪几条接口规则？请逐条指出并给出修正。
   ```java
   public class Config {
       public static Map<String, String> VALUES = new HashMap<>();   // 全局可变
       private List<String> keys = new ArrayList<>();
       public List<String> getKeys() { return keys; }                 // 直接返回内部列表
       public String get(String k) { return VALUES.get(k); }
   }
   ```

<details>
<summary>参考答案</summary>

1. **方案 B 耦合更低。** 用四种形式逐条分析：
   - **属性耦合**：两方案中 `Register` 都有 `Sale` 字段，相同。
   - **方法耦合**：方案 A 的 `makePayment` 方法体内出现 `Payment` 类型（局部变量 + 构造调用），因此 `Register` 依赖 `Payment`；方案 B 的方法体内**不出现** `Payment`，无此依赖。**这是差别所在。**
   - **继承耦合**：两方案都没有继承，相同。
   - **实现耦合**：两方案都没有实现接口，相同。
   结论：方案 B 少一条 `Register → Payment` 的依赖，正是课件第 12 页「Register does not know about Payment class」。
   **方案 B 同时符合 Creator**：`Sale` **records**（记录）`Payment` 实例（它持有 `payments` 列表），按 Creator 五判据之一，`Sale` 应当负责创建 `Payment`。而且 `Sale` 反正要持有这个引用，让它创建不增加任何耦合——这正是课件第 33 页的 "Key idea"。

2. **不矛盾，因为两者衡量的是不同方向的东西。** Low Coupling 只约束「模块**之间**的依赖数量」，它对「模块**内部**是否合理」一无所知。如果把耦合压到极低，最常见的做法是让一两个类承担所有跨模块协调工作，其他类退化为纯数据容器（课件第 17 页原话：`Few incohesive, bloated classes do all the work; all other classes are just data containers`）——模块之间的边确实少了，但那个巨类**内部**塞满了不相关的职责，内聚崩塌。
   平衡手段是 **High Cohesion**：要求每个类只承担「一个功能领域内适度且相关」的职责。两条原则必须联合使用，课件第 16 页明确说「Can't be considered in isolation from other patterns such as Expert and High Cohesion」。此外还要注意课件第 17 页的第三条限定：**耦合到非常稳定的元素（如 JDK 的 `String`）通常无害**，因为耦合的代价 ≈ 依赖强度 × 变化概率。

3. 三层委托：
   - **第一层 `Sale.getTotal()`**：依据的信息是「本次销售包含哪些行项」——`Sale` 拥有 `lineItems`（关联 `Contains 1..*`），所以它是「总额」的信息专家。它遍历 `lineItems` 求和。
   - **第二层 `SalesLineItem.getSubtotal()`**：依据的信息是「买了多少件」与「单价是多少」——`SalesLineItem` 拥有 `quantity`，并通过 `Described-by` 关联到 `ProductDescription`。它做 `price × quantity`。
   - **第三层 `ProductDescription.getPrice()`**：依据的信息是「该商品的价格」——`price` 字段就在 `ProductDescription` 里，它是「价格」的信息专家。
   每一层都是「谁拥有完成这一步所需的信息，谁就负责」，且每层只需知道下一层的**接口**（`getSubtotal()`、`getPrice()`），不需要知道其内部如何计算。这就是课件第 28 页顺序图 `t = getTotal()` → `1 *: st = getSubtotal()` → `1.1: p := getPrice()` 的含义。

4. **根本差别在模块边界的划分依据。** 设计 #1 按**处理步骤**切分（Input → Circular Shift → Alphabetize → Output），模块之间通过**共享的数据格式**（`Lines`、`Shifts` 这些内存中的数据结构）通信。因此「行怎么存」这个决策**渗透在每一个模块里**：Input 往 `Lines` 里写、Circular Shift 从 `Lines` 读并生成 `Shifts`、Alphabetize 排序 `Shifts`、Output 打印。一旦要改存储方式，所有模块都要改。
   设计 #2 按**隐藏的设计决策**切分，专门有一个 `Line Storage` 模块，对外只暴露 `getChar(r, w, c)` / `setChar(r, w, c, d)` 这样的**字符访问接口**。其他模块不知道行是存在数组里、压缩过、还是在磁盘上分页——它们只依赖「能按行列字符位置读写」这个抽象。
   这与「接口 = 客户端被允许依赖的一切」（`design-information-hiding.pdf` 第 16 页）直接相关：#2 的接口**故意设计得只暴露稳定决策**（「能取到某个字符」几乎不可能变），而把易变决策（物理表示）藏在模块内部。#1 的「接口」实际上是共享数据结构，而数据结构的具体形态恰恰是易变的——客户端被迫依赖了最不该依赖的东西。课件第 10 页还补充了副作用：`#1` 的数据格式比 `#2` 的数据访问接口更复杂，**更难就接口达成一致**，因此并行开发更困难。

5. 违反的规则：
   - **Explicit Interfaces（显式接口）**：`public static Map<String, String> VALUES` 是**全局可变变量**。任何代码都能 `Config.VALUES.put(...)`，而这次通信在 `Config` 的接口上完全看不出来（课件第 71 页反例 1 正是全局变量）。修正：改为 `private static final Map<...>`，只通过 `get`/`put` 方法访问。
   - **Information Hiding（信息隐藏）**：`public static` 字段把内部存储结构（一个 `HashMap`）完全暴露；客户端会依赖「它是一个 `Map`」这个决策，将来换成 properties 文件或远程配置就会全面崩坏。修正：同上，字段私有化。
   - **Explicit Interfaces（别名）**：`getKeys()` 直接返回内部 `List` 的引用，客户端 `config.getKeys().clear()` 会悄悄清空内部状态——这是一条**不存在于接口签名上的通信通道**（课件第 71 页反例 2「Aliasing – mutation of shared heap structures」）。修正：`return Collections.unmodifiableList(keys);` 或 `return List.copyOf(keys);`。
   - 附带违反 **Small Interfaces** 的精神：暴露整个 `Map` 比暴露少量具名方法交换的信息多得多。
   修正后：
   ```java
   public final class Config {
       private static final Map<String, String> VALUES = new HashMap<>();
       private final List<String> keys = new ArrayList<>();
       public static String get(String k) { return VALUES.get(k); }
       public static void put(String k, String v) { VALUES.put(k, v); }
       public List<String> getKeys() { return Collections.unmodifiableList(keys); }
   }
   ```
   注意：如果 `VALUES` 需要被多方并发访问，还应明确其**加锁策略**——课件第 16 页提醒「接口在概念上还包括 locking policies」，而这类约定往往无法用 Java 的类型系统表达。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-10-Conceptual-Modeling]]
- 下一讲：[[15-214-12-DSM-and-GUIs]]
- 课程总览：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]
- 课程目录：[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸：D. L. Parnas, "On the Criteria To Be Used in Decomposing Systems into Modules," *CACM* 15(12):1053–1058, Dec 1972——本讲后半的核心文献，全文不长，强烈建议读原文；Craig Larman《Applying UML and Patterns》第 16、17、22 章是 GRASP 的出处，第 9 章讲概念建模；Bertrand Meyer《Object-Oriented Software Construction》第 3、4 章讲设计目标与模块化（五准则的原始出处）；Karl Lieberherr 的迪米特法则原始文献。下一讲 [[15-214-12-DSM-and-GUIs]] 会把「模块之间的依赖」变成可计算的矩阵（DSM），是本章耦合概念的定量化延伸。
