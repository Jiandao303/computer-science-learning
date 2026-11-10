---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L10
topic: Conceptual Modeling in Design
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 概念建模
  - 领域模型
  - UML
  - 类图
  - 软件设计
  - 耦合与内聚
---

# 第 10 讲 设计中的概念建模（Conceptual Modeling in Design）

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。本讲 slides 页脚标注为 Fall 2013，与学期一致；部分幻灯片由 Klaus Ostermann 提供。

## 1. 本节学习目标

- 能说明「软件设计」要解决的问题：为什么要从无穷多个行为等价的程序中选择一个。
- 能区分**内部质量**与**外部质量**，并列举衡量内部质量的若干维度。
- 能对一个自然语言描述的需求，用「找名词与动词」的方法初步提炼候选概念。
- 能判断一个概念应当建模为**类**还是**属性**，并说出判别准则。
- 能说明关联（association）与多重性（multiplicity）在领域模型中的含义。
- 能区分类图的**三种视角**：概念层、规格层、实现层——并说明混用视角为什么会导致沟通失败。

## 2. 前置知识

- [[15-214-07-Design-Patterns]]：模式是「反复出现的问题 + 解法」，本讲之前的模式讨论都基于「已有设计」。
- [[15-214-09-Design-Patterns-Continued]]：Strategy 等模式的取舍，本讲把它纳入「设计质量」的框架。
- [[15-214-03-Encapsulation-and-Inheritance]]：UML 类图基本符号（继承、实现、可见性）。
- 外部概念：UML 类图；面向对象分析（OOA）。

## 3. 核心概念

- **Conceptual Modeling（概念建模）**：找出问题领域中的概念及其关系，形成领域模型。
- **Domain Model（领域模型）**：描述业务领域概念、属性与关联的图（常以 UML 类图作非形式记法）。
- **Conceptual Class（概念类）**：现实世界中的抽象，**不一定**对应软件对象。
- **Association（关联）**：两个概念之间有意义的连接，可带角色名与多重性。
- **Multiplicity（多重性）**：关联一端的数量约束，如 `1`、`*`、`1..*`、`0..1`。
- **Internal Quality（内部质量）**：设计的可扩展性、可维护性、可理解性等，本质是「模块化」。
- **External Quality（外部质量）**：正确性、易用性、资源消耗等用户可感知的质量。
- **Coupling / Cohesion（耦合 / 内聚）**：模块之间依赖的强度 / 模块内部元素的相关程度。
- **Analysis Paralysis（分析瘫痪）**：因追求完美模型而停滞不前的状态。

## 4. 通俗理解

**为什么设计难？** 课件第 4 页给出一个极其锋利的观察：

> For each desired program behavior there are infinitely many programs that have this behavior.
> - What are the differences between the variants?
> - Which variant should we choose?
>
> Since we usually have to **synthesize** rather than **choose** the solution…
> - How can we design a variant that has the desired properties?

这段话有两个层次：

1. **行为等价的程序有无穷多个**。`sort` 用冒泡还是快排、用 if-else 还是 `Comparator`，从「输出正确」的角度看没有区别。所以「正确」不能作为选择的依据——必须引入**别的判据**。
2. **我们不是「挑选」而是「合成」**。理论上你可以枚举无穷多个程序然后挑最好的，实际上你只能造一个出来。所以问题不是「哪个最好」，而是「**怎么造才能让它具备我想要的属性**」。

这就是设计（design）与编程（programming）的分界：编程解决「怎么让它跑对」，设计解决「怎么让它**以后**还好改」。

**概念建模是什么？** 它是在写代码之前，先弄清楚「这个领域里到底有哪些东西」。课件第 9 页说得很克制：

> - 找出问题领域中的概念——**现实世界的抽象，不一定是软件对象**
> - 建立共同词汇
> - 共同的文档、大图景
> - **为了沟通！**
> - 常用 UML 类图作为（非形式的）记法
> - 是找类的起点

注意第四条加了感叹号：**为了沟通**。领域模型的首要读者是人（产品经理、领域专家、新加入的开发者），不是编译器。这就解释了为什么它「不必完美」——沟通的目的是对齐理解，不是生成代码。

## 5. 原理与推导

### 5.1 内部质量 vs 外部质量

课件第 6 页把设计质量分成两层：

**内部质量（internal quality）**——「如何衡量软件设计的**内部**质量？」

- Extensibility（可扩展性）、Maintainability（可维护性）、Understandability（可理解性）、Readability（可读性）…
- **Robustness to change（对变化的健壮性）**
- **Low Coupling & High Cohesion（低耦合、高内聚）**
- Reusability（可复用性）
- Testability（可测试性）
- **=> modularity（归结为模块化）**

**外部质量（external quality）**——「与之相对的外部质量」：

- Correctness（正确性）：需求的合法实现
- Ease of Use（易用性）
- Resource consumption（资源消耗）
- Legal issues, political issues（法律、政治问题）…

这个划分解释了一件事：**内部质量是「为未来付费」的质量**。一个不可扩展但正确的程序，今天完全可用；它的缺陷只在需求变化时才显现。所以内部质量很难被非技术方感知，也最容易被进度压力牺牲——这正是设计需要被**论证**（justify）而不是被**感觉**的原因。

课件把内部质量归结为 **modularity（模块化）**，而模块化的两个可操作指标是**耦合**与**内聚**：

| 指标 | 含义 | 好设计的目标 |
|---|---|---|
| **Coupling（耦合）** | 模块之间相互依赖的程度 | **低**——改一个模块时不必改其他 |
| **Cohesion（内聚）** | 一个模块内部元素的相关程度 | **高**——一个模块只做一件事 |

低耦合高内聚几乎是所有设计原则的共同归宿：单一职责是内聚，依赖倒置是解耦，信息隐藏是减少耦合的手段。第 11 讲的 GRASP 会把这些原则系统化。

### 5.2 工程判断：来自 CMU 软件工程宣言

课件第 7 页引用 CMU-ISRI-05-108《Software Engineering for the 21st Century: A basis for rethinking the curriculum》：

> "Software engineering is the branch of computer science that creates practical, cost-effective solutions to computing and information processing problems, preferentially by applying scientific knowledge, developing software systems in the service of mankind.
>
> Software engineering entails **making decisions under constraints of limited time, knowledge, and resources**. […]
>
> **Engineering quality resides in engineering judgment.** […]
>
> Quality of the software product depends on the engineer's **faithfulness to the engineered artifact**. […]
>
> Engineering requires **reconciling conflicting constraints**. […]
>
> Engineering skills improve as a result of **careful systematic reflection on experience**. […]
>
> **Costs and time constraints matter, not just capability.** […]"

这段引文值得逐句读，因为它回答了「为什么设计没有标准答案」：

- **决策在时间、知识、资源受限下做出**——所以「最优设计」不存在，只有「当前约束下的合理设计」；
- **工程质量存在于工程判断中**——判断力不能被规则替代，规则只是判断的脚手架；
- **需要调和冲突的约束**——可扩展性与简单性冲突、性能与可读性冲突，设计就是权衡；
- **成本与时间约束同样重要，不只是能力**——一个需要三个月才能实现的好设计，在两周的工期里是坏设计。

这也解释了课件为什么把「设计」列为四大主题之一时写的是「**Proposing and evaluating alternatives（提出并评估备选方案）**」——设计的核心动作是**比较**，没有备选方案就没有设计。

### 5.3 概念建模的产出物

课件第 9 页给出概念建模/领域模型的定位：

| 方面 | 内容 |
|---|---|
| 找什么 | 问题领域中的概念（现实世界抽象，不一定是软件对象） |
| 目的 | 建立共同词汇 |
| 用途 | 共同文档、大图景 |
| 首要目标 | **沟通** |
| 记法 | 常用 UML 类图（**非形式**的） |
| 后续作用 | **是找类的起点** |

「非形式」这个词很关键：领域模型里的箭头不必严格符合 UML 语义，甚至可以有「Stocks」「Houses」这种自然语言角色名。它的价值在于**让领域专家看懂**，而不是让工具解析。

「是找类的起点」则说明它的下游用途：领域模型中的概念会成为候选类，但**不是一一对应**——有些概念会变成类，有些变成属性，有些根本不进代码。

### 5.4 方法：找名词与动词

课件第 10–13 页用一个完整例子演示，材料来自 Wikipedia 的「Point of sale」条目（第 11 页全文）：

> Point of sale (POS) or checkout is the place where a retail transaction is completed. It is the point at which a **customer** makes a **payment** to a **merchant** in exchange for **goods** or **services**. At the point of sale the **merchant** would use any of a range of possible **methods** to calculate the **amount owing** - such as a manual system, **weighing machines**, **scanners** or an **electronic cash register**. The merchant will usually provide **hardware** and **options** for use by the customer to make payment. The merchant will also normally issue a **receipt** for the transaction.
>
> For small and medium-sized retailers, the POS will be customized by retail industry as different industries have different needs. For example, a grocery or candy store will need a **scale** at the point of sale, while bars and restaurants will need to customize the **item** sold when a customer has a special meal or drink request. The modern point of sale will also include advanced functionalities to cater to different verticals, such as **inventory**, **CRM**, **financials**, **warehousing**, and so on, all built into the POS software. Prior to the modern POS, all of these functions were done independently and required the manual re-keying of **information**, which resulted in a lot of **errors**.

第 12 页的指令是：

> **Read description carefully, look for nouns and verbs.**
> （仔细阅读描述，寻找名词与动词）

幻灯片把关键名词加粗——customer, payment, merchant, goods, services, methods, amount owing, weighing machines, scanners, electronic cash register, hardware, options, receipt, scale, item, inventory, CRM, financials, warehousing, information, errors。

**名词 → 候选概念；动词 → 候选关联或操作。** 这是一个朴素但在实践中非常有效的启发式，因为自然语言的句法结构与对象模型有天然对应：名词指称实体，动词指称关系或行为。

第 13 页给出「迈向领域模型的第一步」——一个候选概念清单（尚未连线）：

```
Store   Register   Sale   Item   CashPayment   SalesLineItem
Cashier   Customer   Product   Catalog   ProductDescription   Ledger
```

注意这一步**只列名字，不画关系**。这是有意的：先确保词汇完整，再考虑结构。过早连线会让人陷入「这条关联到底该不该有」的细节争论。

### 5.5 类 vs 属性：一条实用的判别准则

课件第 15 页给出准则（原文带引号，说明是引用）：

> "If we do not think of some conceptual class X as text or a number in the real world, it's probably a conceptual class, not an attribute."
> （如果我们不会在现实世界中把某个概念 X 想成一段文本或一个数字，那它多半是概念类，而不是属性。）

对照示例：

```
Sale ── store ──> Store          （store 是关联，指向另一个概念类）
Sale ── phoneNr ──> （属性）      （phoneNr 只是一段文本）
```

判别方法：**问「在现实世界里，这个东西是一个独立存在的事物，还是一个值？」**

- `Store`（商店）：是一个有地址、有员工、能开门关门的**东西**——概念类；
- `phoneNr`（电话号）：是一串数字，离开商店就不存在——属性。

更细的判据：

| 特征 | 偏向概念类 | 偏向属性 |
|---|---|---|
| 现实世界是否独立存在 | 是 | 否（依附于宿主） |
| 是否只有单一值 | 否，可能有多条信息 | 是，一个文本或数字 |
| 是否需要被多方引用 | 是 | 否 |
| 是否有自己的行为/规则 | 是 | 否 |
| 例子 | `Customer`、`Product`、`Store` | `phoneNr`、`price`、`quantity`、`date` |

一个常见的反例思考：`price`（价格）看起来是数字，但如果系统需要记录「价格的历史变化」「不同门店价格不同」，那 `price` 就该变成一个概念类 `Price`（带生效日期、门店、金额）。**判据不是「它现在长什么样」，而是「模型需要它承担什么」。**

这与第 7 讲（`07-design-pattern-notes.pdf`）里的同类准则一致：「文字或数字 → 属性，复杂结构 → 概念」。

### 5.6 关联与多重性

课件第 16 页提出问题：

> When do we care about a relationship between two objects? (in the real world)
> （我们什么时候关心两个对象之间的关系？——在现实世界中）

并给出示例：

```
Store ──Stocks──> Item
  1                 *
```

两个要素：

- **角色名（role name）**：`Stocks`——从 `Store` 的角度看，这条关联表示「库存」这件**事**。角色名让关联可读：「一家 Store Stocks 多个 Item」。
- **多重性（multiplicity of the role）**：`*`——一个 `Store` 对应零到多个 `Item`；`1`——一个 `Item` 属于恰好一家 `Store`。

多重性的常见取值：

| 记法 | 含义 | 读法 |
|---|---|---|
| `1` | 恰好一个 | 「必须有一个」 |
| `0..1` | 零或一个 | 「可以有，可以没有」 |
| `*` | 零或多个 | 「一个集合，可能为空」 |
| `1..*` | 一个或多个 | 「至少一个」 |
| `3` | 恰好三个 | 如「一次 Sale 有 3 个 Cashier」 |

多重性不是装饰——它直接决定代码里的字段类型：

| 多重性 | 代码形态 |
|---|---|
| `1` | 一个非空字段，构造函数中强制赋值 |
| `0..1` | 一个可能为 `null` 的字段（或 `Optional<T>`） |
| `*` | 一个集合字段（`List`/`Set`），可能为空 |
| `1..*` | 一个集合字段，且需要非空校验 |

这也是「概念模型是找类的起点」的具体含义：**概念模型上的多重性，会变成代码里的空值检查与集合类型**。在建模阶段弄错一个 `0..1` 与 `1`，会在实现阶段变成一整类 `NullPointerException`。

### 5.7 完整的领域模型（节选）

课件第 17 页给出连好的模型（节选），包含九个概念与大量带角色名的关联：

```
Register ──Contains──> Sale (1..*)
Sale ──Used-by──> Cashier          （1）
Sale ──Captured-on──> Register     （1）
Sale ──Is-for──> Customer          （1，可空？见 0..1）
SalesLineItem ──Contained-in──> Sale （1..*）
SalesLineItem ──Records-sale-of──> Item （0..1）
CashPayment ──Paid-by──> Sale      （1）
Product ──Describes──> ProductDescription （*）
Product ──Contained-in──> Catalog  （1..*）
ProductDescription ──Stocks──> Store （*）
Store ──Houses──> Register         （1..*）
Ledger ──Logs-completed──> Sale    （*）
Ledger ──Records-accounts-for──> Store （1）
Cashier ──Works-on──> Register     （3）
```

（以上为按幻灯片布局的语义重构；原图为 11 个概念 + 十余条关联的完整类图。）

几个值得注意的建模决策：

1. **`SalesLineItem` 是独立的类，不是 `Sale` 的属性**。为什么？因为一行销售记录需要承载「买了什么（指向 `Item`）、买了几件、单价多少」——它是一个有结构的事物。这与 5.5 节的判据一致。
2. **`Product` 与 `ProductDescription` 分离**。这是经典的「价格与描述」模式：`ProductDescription` 承载名称、描述、**价格**（可能随目录变化），`Product` 代表货架上的具体物品。这也对应第 14 讲 Java Collections 之前的「对象身份 vs 值」思考。
3. **`Cashier Works-on Register` 的多重性是 `3`**——一个收银员同时操作三台收银机？这看起来是个示例值，实际建模中更可能是 `*`。它说明领域模型的数字需要**与领域专家核对**，不能凭直觉填。
4. **`CashPayment` 而不是 `Payment`**。为什么要带 `Cash`？因为未来会有 `CreditCardPayment`、`CheckPayment`——这是为扩展留的钩子，也是一种「**代码气味预警**」：一旦出现 `XxxPayment` 这样的命名，往往暗示着一个继承层次或 Strategy。
5. **`Ledger` 独立存在**，负责「记录已完成的销售」与「记录门店账目」。这是记账（accounting）关注点与销售（sales）关注点的分离——未来的单一职责原则在这里就有体现。

### 5.8 概念建模的六条实务建议

课件第 18 页的「Note」是整讲最实用的部分：

> - **Focus on concepts, not software classes, not data**
>   - ideas, things, objects
>   - **Give it a name, define it and give examples (symbol, intension, extension)**
>   - **Add glossary**
>   - Some might be implemented as classes, other might not
> - **There are many choices**
> - **Agree on a single vocabulary**
> - **The model will never be perfectly correct**
>   - that's okay
>   - start with a partial model, model what's needed
>   - extend with additional information later
>   - **communicate changes clearly**
>   - otherwise danger of **"analysis paralysis"**

逐条解读：

**（1）关注概念，不是软件类，也不是数据。** 领域模型描述「世界是怎样的」，不是「数据库表长什么样」，也不是「类怎么设计」。一旦混入 `id`、`created_at` 这类字段，模型就退化成了 schema。

**（2）给概念命名、定义、举例——符号、内涵、外延。** 这是逻辑学三个层次：

| 层次 | 含义 | 例子（`Customer`） |
|---|---|---|
| **Symbol（符号）** | 名字本身 | "Customer" |
| **Intension（内涵）** | 定义，判定某物是否属于该概念的规则 | 「在本店完成过至少一次交易的法人或自然人」 |
| **Extension（外延）** | 满足定义的具体实例集合 | 张三、李四、某某公司 |

三者缺一不可。只有符号，不同人对它的理解会分歧；只有外延，无法判断新出现的事物是否属于该类。**内涵是歧义的真正杀手**。

**（3）加术语表（glossary）。** 把「符号 + 内涵 + 示例」记下来，成为团队的共同语言。这正是本知识库维护「计算机专业术语词典」的同一动机。

**（4）有些概念会变成类，有些不**。别强求一一对应。

**（5）选择很多。** 同一个领域可以有多种合理建模（把 `Address` 做成类还是三个属性？），没有唯一正确答案。

**（6）模型永远不会完全正确——这没关系。** 关键是：

- 从**部分模型**开始，只建需要的部分；
- 后续**逐步扩展**；
- **清晰地沟通变更**；
- 否则会陷入**分析瘫痪（analysis paralysis）**。

「分析瘫痪」是这里最重要的警告：追求一个完美覆盖所有情况的模型，会让你在写第一行代码之前就耗尽预算。领域模型是**工具**，不是**交付物**。

### 5.9 类图的三种视角

课件第 19 页是理论上最重要的一页：

> **Three perspectives of class diagrams**
>
> - **Conceptual（概念层）**：画出研究对象领域中的概念。**几乎或完全不考虑可能实现它的软件。**
> - **Specification（规格层）**：描述软件的**接口**，而非实现。
>   - 在 OO 中常被混淆，因为类同时包含接口与实现。
> - **Implementation（实现层）**：图描述实际的实现类。
>
> **Understanding the intended perspective is crucial to drawing and reading class diagrams, even though the lines between them are not sharp.**
> （理解预期视角对绘制与阅读类图至关重要，尽管三者之间的界线并不清晰。）

三种视角的对照：

| 维度 | 概念层 | 规格层 | 实现层 |
|---|---|---|---|
| 描述对象 | 领域中的概念 | 软件的接口 | 实际的类 |
| 关心实现吗 | 完全不关心 | 不关心 | 关心 |
| 属性写什么 | 领域属性（`phoneNr`） | 接口暴露的操作 | 真实字段（含 `private`） |
| 方法写什么 | 通常**不写方法** | 只写公有操作 | 全部方法（含私有） |
| 读者 | 领域专家、产品、全体开发者 | 模块的使用者 | 模块的实现者 |
| 例子 | `Sale ──Is-for──> Customer` | `PaymentProcessor.process(Payment)` | `class AlipayProcessor implements PaymentProcessor { … }` |

**为什么要强调视角？** 因为**混用视角是类图最大的沟通陷阱**。典型场景：

- 架构师画了一张「概念图」（只有名词和关联），开发者却按「实现图」去读，于是追问「这个关联的字段名是什么？有没有 getter？」——两人在讨论不同的东西；
- 反过来，开发者画了一张满是 `private` 字段与 `List<Foo>` 的实现图给产品经理看，产品经理完全无法验证业务概念是否完整。

课件特别指出 OO 语言加剧了这个混淆：「**类同时包含接口与实现**」。在 Java 里，`class` 一个关键字同时承担了「概念」「接口」「实现」三重身份——而 C 语言里 `struct`（数据）+ 函数指针（行为）是分开的，反而不容易混。这正是很多设计讨论失焦的根源。

## 6. 代码示例

### 6.1 官方课程代码

本讲是概念建模专题，slides 中**没有 Java 代码**，唯一出现代码的是第 5 页复习上一讲的 `sort` 对照：

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
    boolean compare(int I, int j) { return i < j; }
}

class DownComparator implements Comparator {
    boolean compare(int I, int j) { return i > j; }
}
```

这段代码在本讲的作用不是讲设计模式，而是演示**「同一个行为有无穷多种实现」**（5.1 节）：两个 `sort` 的输出完全一致，差别只在内部质量。课件第 5 页的标题就是 `Tradeoffs`。

本讲的「官方内容」主要表现为 UML 结构，见 `conceptual-modeling.pdf`：

- 第 13 页：候选概念清单 `Store / Register / Sale / Item / CashPayment / SalesLineItem / Cashier / Customer / Product / Catalog / ProductDescription / Ledger`
- 第 15 页：`Sale ── store ──> Store` 与 `Sale ── phoneNr ──> （属性）` 的对照
- 第 16 页：`Store ──Stocks[*]──> Item`，一端标 `1`
- 第 17 页：完整的领域模型（11 个概念 + 十余条带角色名的关联）

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

本讲主题是建模，因此示例以「模型 → 代码」的映射为主。

**示例 A：从领域模型到 Java 代码（多重性决定字段类型）**

领域模型片段：

```
Store 1 ──Houses──> * Register
Register 1 ──Contains──> * Sale
Sale 1 ──Is-for──> 0..1 Customer
Sale 1 ──Paid-by──> 1 CashPayment
```

对应的实现层代码：

```java
public final class Store {
    private final String name;
    private final List<Register> registers = new ArrayList<>();   // * → 集合
    public Store(String name) { this.name = name; }
    public void addRegister(Register r) { registers.add(r); }
    public List<Register> getRegisters() {
        return Collections.unmodifiableList(registers);           // 防御性：不外泄可变内部状态
    }
}

public final class Register {
    private final int id;
    private final List<Sale> sales = new ArrayList<>();           // * → 集合
    public Register(int id) { this.id = id; }
    public void recordSale(Sale s) { sales.add(s); }
}

public final class Sale {
    private final Register register;      // 1  → 构造时强制赋值（非空）
    private final Customer customer;      // 0..1 → 可以为 null
    private final Payment payment;        // 1  → 构造时强制赋值（非空）

    public Sale(Register register, Customer customer, Payment payment) {
        this.register = Objects.requireNonNull(register, "register");
        this.customer = customer;                     // 允许 null
        this.payment  = Objects.requireNonNull(payment, "payment");
    }
}
```

要点：**多重性 `1` → 构造函数里的 `requireNonNull`；`0..1` → 允许 `null` 的字段；`*` → 集合字段**。建模阶段的一个数字，落地成代码里的一次非空校验。如果在模型里把 `customer` 标成 `1`，代码就会拒绝「匿名顾客结账」这个真实需求。

**示例 B：概念层 vs 实现层的同一张图**

概念层（给领域专家看，只有名词与关联，无方法、无 `private`）：

```
Sale ──Contains──> * SalesLineItem
SalesLineItem ──Records-sale-of──> 0..1 Item
Item ──Described-by──> 1 ProductDescription
```

实现层（给程序员看，有字段、有可见性、有集合类型）：

```java
public final class Sale {
    private final List<SalesLineItem> lineItems = new ArrayList<>();
}

public final class SalesLineItem {
    private final Item item;              // 0..1：可能是手工录入、无对应商品
    private final int quantity;
    private final Money unitPrice;
}

public final class Item {
    private final ProductDescription description;   // 1：必须有描述
}
```

对照看：概念层的「关联」在实现层变成**字段**，概念层的「多重性」变成**集合/可空性**，概念层没有的方法在实现层大量出现（`addLineItem`、`total()`）。**把这两张图混在一起讨论，就是沟通失败的开始。**

**示例 C：「类还是属性」的判定演练**

需求片段：「顾客下单时可以选择自提或配送；配送需要填写收货地址，自提需要指定门店。」

| 候选 | 建模为 | 理由 |
|---|---|---|
| 收货地址 | **概念类 `Address`** | 有省市区、街道、邮编多个部分；可能被多个订单复用；将来要支持地址簿 |
| 自提门店 | **关联到 `Store`** | 门店在模型中已存在，这里是引用而非新概念 |
| 配送方式 | **枚举/概念类 `DeliveryMethod`** | 只有两个取值，但行为不同（是否需要地址校验）→ 倾向做成多态 |
| 订单号 | **属性 `orderId`** | 只是一个标识串，无独立存在意义 |

如果把「收货地址」做成 `Sale` 的三个字符串属性（`addrProvince`、`addrStreet`、`addrZip`），当需求变成「支持地址簿、一键复用历史地址」时，就要重构整个 `Sale`。这就是 5.5 节判据的实战价值——**判据不是「它现在长什么样」，而是「模型需要它承担什么」**。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| **内部质量** | **外部质量** | 前者是设计层面的（可扩展、可维护、可测试，归结为模块化），只有开发者能感知；后者是用户层面的（正确性、易用性、资源消耗、法律问题） |
| **概念建模** | **数据库设计** | 前者描述领域中的概念与关系，可以完全不管存储；后者关心表、主键、范式、索引。把 `id`/`created_at` 塞进领域模型，就退化成 schema 了 |
| **概念类** | **软件类** | 概念类是现实世界抽象（可能不实现为类，可能实现为多个类）；软件类是代码实体。课件：「Some might be implemented as classes, other might not」 |
| **属性** | **关联** | 属性是「值」（文本、数字、日期）；关联指向另一个**概念**。判据：「现实中是否是独立存在的事物」 |
| **关联的角色名** | **关联的多重性** | 角色名回答「这条关系是什么」（`Stocks`、`Houses`）；多重性回答「有几个」（`1`、`*`、`1..*`） |
| **耦合** | **内聚** | 耦合是**模块之间**的依赖强度（要低）；内聚是**模块内部**元素的相关度（要高）。二者常一起出现，但衡量的是相反方向 |
| **概念层类图** | **实现层类图** | 前者只画领域概念与关联（通常无方法）；后者画真实类（含 `private` 字段、集合类型、私有方法）。**混用是沟通失败的头号原因** |
| **规格层类图** | **概念层类图** | 规格层描述**软件接口**（可调用什么），概念层描述**领域概念**（世界有什么）。OO 中二者易混，因为 `class` 同时承载接口与实现 |
| **模型不完美** | **模型错误** | 不完美是可接受的（部分覆盖、后续扩展）；错误是不可接受的（与领域专家确认过的事实相反）。前者要容忍，后者要修 |
| **迭代建模** | **分析瘫痪** | 前者是「建一部分 → 用起来 → 再扩展」；后者是无休止地追求完美模型而永不交付 |

## 8. 对应原版讲义

- PDF 相对路径：`90-原始PDF/15-214/slides/conceptual-modeling.pdf`
- 总页数：19 页
- 重点页码：
  - 第 1 页：封面（页脚 Fall 2013；标注 "With slides from Klaus Ostermann"）
  - 第 2 页：四大课程主题回顾（并发、OOP、分析与建模、设计）
  - 第 3 页：本讲学习目标（什么是软件设计／概念建模／设计目标／GRASP）
  - 第 4 页：设计的目标——「行为等价的程序有无穷多个」「合成而非选择」
  - 第 5 页：`sort` 两种实现的 Tradeoffs（复习 Strategy）
  - 第 6 页：内部质量 vs 外部质量；「=> modularity」
  - 第 7 页：CMU 软件工程宣言引文（CMU-ISRI-05-108）
  - 第 8 页：Conceptual Design 章节页
  - 第 9 页：概念建模/领域模型的定位（找概念、共同词汇、为了沟通、UML 非形式记法、找类的起点）
  - 第 10 页：Running Example 图片页（POS 照片，CC 许可 by Cyberslayer on Flickr）
  - 第 11 页：POS 的 Wikipedia 描述原文
  - 第 12 页：标注名词后的同一段文字（「look for nouns and verbs」）
  - 第 13 页：候选概念清单（12 个名词，尚未连线）
  - 第 14 页：Domain Model 章节页
  - 第 15 页：类 vs 属性（「text or a number」判据）
  - 第 16 页：关联与多重性（`Store Stocks * Item`）
  - 第 17 页：完整领域模型（节选）
  - 第 18 页：六条实务建议（概念优先、命名定义举例、术语表、单一词汇、模型永不完美、避免分析瘫痪）
  - 第 19 页：类图的三种视角（概念/规格/实现）
- 原始网页链接：`https://www.cs.cmu.edu/~aldrich/214/slides/conceptual-modeling.pdf`

> 待核实：第 9 页 "Common documentation, big pictutre" 中 `pictutre` 为 `picture` 的拼写错误；第 17 页 `Cashier Works-on Register` 的多重性标注为 `3`，实际业务中更可能是 `*`，疑为示例数值或排版取整，建议对照课堂讲解核对。另，第 11 页文本引自 Wikipedia "Point of sale" 条目，第 10 页图片标注 CC 许可（Cyberslayer on Flickr）。

## 9. 对应视频

未找到官方公开录像。2013 年秋季的 15-214 课堂没有公开发布录像，故不提供链接与时间戳。

## 10. 本节复习

- 设计要解决的问题：行为等价的程序有无穷多个，我们不是**选择**而是**合成**——因此需要「让设计具备期望属性」的方法。
- 内部质量（可扩展、可维护、可理解、低耦合高内聚、可复用、可测试）归结为**模块化**；外部质量是正确性、易用性、资源消耗等。
- 软件工程是「在时间、知识、资源受限下做决策」，**质量存在于工程判断中**，需要**调和冲突的约束**。
- 概念建模：找领域概念 → 建立共同词汇 → 为了**沟通** → 用非形式 UML → 是找类的起点。
- 「找名词与动词」是提炼候选概念的有效启发式：名词→概念，动词→关联或操作。
- 类 vs 属性判据：现实中是否是「文本或数字」；不是 → 概念类。
- 关联需要角色名（是什么关系）与多重性（有几个）；多重性直接决定代码里的集合/可空/非空。
- 六条实务：概念优先、命名+定义+举例（符号/内涵/外延）、加术语表、单一词汇、模型永不完美、避免分析瘫痪。
- 类图三视角：概念层（领域）/ 规格层（接口）/ 实现层（代码）。**混用视角是沟通失败的头号原因**，OO 中尤其严重，因为 `class` 同时承载接口与实现。

## 11. 自我检查

1. 阅读下面这段需求，用「找名词与动词」的方法列出至少 8 个候选概念，并指出哪些可能最终**不**成为类。
   > 图书馆的读者可以借阅图书。每本图书有唯一的 ISBN，馆内可能有多个副本。借阅记录包含借出日期与应还日期；逾期未还时按每天 0.5 元计罚金。管理员可以办理借书与还书，并可以查询某位读者的全部未还记录。
2. 判断下列各项应当建模为**概念类**还是**属性**，并说明理由：
   (a) 顾客的手机号；(b) 订单的收货地址；(c) 商品的当前价格；(d) 一次支付使用的支付方式（现金/信用卡/移动支付）。
3. 领域模型中某条关联的两端分别标为 `1` 与 `0..1`，另一条标为 `1` 与 `1..*`。请分别说明它们在 Java 实现中应当对应什么样的字段，以及构造函数需要做什么校验。
4. 为什么课件说「理解类图的预期视角至关重要」，并且「OO 语言让这个问题更严重」？请举一个因视角混用导致的具体沟通失败场景。
5. 什么是「分析瘫痪」？课件为什么说「模型永远不会完全正确——这没关系」？请给出防止分析瘫痪的两条具体做法。

<details>
<summary>参考答案</summary>

1. 名词候选：**图书馆**、**读者**、**图书**、**ISBN**、**副本**、**借阅记录**、**借出日期**、**应还日期**、**罚金**、**管理员**、**未还记录**。动词候选：**借阅/借书**、**还书**、**查询**、**计罚金**。
   - 可能成为概念类：`Reader`（读者）、`Book`（图书，以 ISBN 标识）、`Copy`（副本）、`Loan`（借阅记录）、`Librarian`（管理员）。
   - 可能成为属性：`ISBN`（一个字符串标识，依附于 `Book`）、`借出日期`/`应还日期`（`Loan` 上的日期属性）。
   - 可能不进入模型：`图书馆`（如果系统只服务单一馆，它就是隐含上下文而非类）、`未还记录`（是 `Loan` 的一个**查询结果**，不是独立概念——它等价于「`Loan` 中 `returnDate == null` 的集合」）、`罚金`（若只是按天数算出的一个数，它是方法返回值而非字段；若需要记录罚金的缴纳状态，则升级为概念类 `Fine`）。
   - 动词 → 关联/操作：`借阅` → `Loan` 这个关联实体（连接 `Reader` 与 `Copy`）；`办理借书/还书` → `Librarian` 的操作；`计罚金` → `Loan` 上的计算操作。
   注意 `Copy`（副本）与 `Book`（图书）必须分开：需求明说「馆内可能有多个副本」，这正是 5.5 节「模型需要它承担什么」的判断。

2. (a) **属性**。手机号是一段文本，在现实中不是一个独立存在的事物，只依附于顾客；除非系统需要「一个顾客有多个号码并区分主副」，那时才升级为概念类。
   (b) **概念类 `Address`**。地址由省、市、区、街道、邮编多个部分组成，现实中是一个有结构的事物；而且它可能被多个订单复用（地址簿）。若建模为属性，就只能是三个扁平字符串，无法复用也无法校验。
   (c) **概念类 `Price`（或至少是带生效期的关联）**。表面上是一个数字，但需求一旦涉及「价格历史」「不同门店不同价」「促销价」，就必须承载金额、币种、生效时间、适用门店等多条信息——这正是 5.5 节强调的「判据不是它现在长什么样，而是模型需要它承担什么」。
   (d) **概念类（多态层次）**。三种支付方式的行为不同（是否需要卡号、是否需要扫码、退款流程不同），只用一个枚举会让所有分支挤在同一个方法里。建模为 `PaymentMethod` 的继承层次或 Strategy，正是第 9 讲「变化点封装」的应用。

3. `1` 与 `0..1` 的关联：`1` 的一端是**非空字段**，在构造函数中用 `Objects.requireNonNull(...)` 强制赋值；`0..1` 的一端是**可为 `null` 的字段**（或 `Optional<T>`），构造时可传 `null`，使用方必须做空值分支。
   `1` 与 `1..*` 的关联：`1` 的一端是**非空字段**；`1..*` 的一端是**集合字段**（`List`/`Set`），且构造函数或 `add` 方法必须保证**至少有一个元素**——这通常不能靠字段初始化完成，而要延迟到业务操作后校验（例如 `Sale` 在结账时检查 `lineItems.isEmpty()`）。同时集合字段的 getter 应返回不可变视图（`Collections.unmodifiableList`），避免表示暴露。
   核心结论：**多重性 `*` 与 `1..*` 的差别不在于类型（都是集合），而在于不变式（后者非空）**——这正是第 8 讲「类不变式」的用武之地。

4. 因为**同一张图在不同视角下含义完全不同**，读图者若搞错视角，就会提出错误的问题或得出错误结论。课件指出 OO 加剧了问题，原因是「**类同时包含接口与实现**」——`class` 一个关键字同时承担了概念、接口、实现三重身份，读者无法从图上判断作者想表达哪一层。
   具体失败场景：架构师在白板上画了一张**概念层** POS 模型（`Sale ──Is-for──> Customer`，只有名词和关联，没有任何方法），意在让产品经理确认业务概念是否齐全。一位开发者看到后按**实现层**去读，追问：「`Sale` 的 `customer` 字段是不是 `final`？`Customer` 有没有 `getId()`？这条关联是单向还是双向，代码里要不要反向引用？」——两边讨论的是完全不同的东西，会议跑偏半小时。同样地，如果开发者把满是 `private List<SalesLineItem>` 的**实现图**拿给产品经理评审，产品经理无法判断「业务上是否还需要 `Return`（退货）这个概念」，因为他看到的全是技术细节。
   正确做法：**在图上或口头明确标注视角**（「这是一张概念模型，只讨论业务概念」），并针对不同读者画不同层次的图。

5. **分析瘫痪（analysis paralysis）**指团队为追求一个完美、完整、无歧义的模型而反复讨论、迟迟不进入实现，最终耗尽时间与预算却什么都没交付。
   课件说「模型永远不会完全正确——这没关系」，是因为领域模型的首要用途是**沟通**（第 9 页），而不是生成代码或形式化验证。只要它能让团队对核心概念达成一致，它就已经完成了使命；遗漏的细节可以在实现过程中发现并补上。追求完美模型违背了第 7 页的工程观：「决策在时间、知识、资源受限下做出」。
   两条具体做法：(1) **从部分模型开始，只建当前需要的部分**——先覆盖本次迭代要实现的用例所涉及的概念，其余留待后续；(2) **把模型当作活文档，变更时明确沟通**——每次扩展都同步给团队（更新术语表、在评审中过一遍），而不是悄悄改动。第三条可选的实践是设定**时间盒**（如「建模不超过半天」），到点就用当前模型开工。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-09-Design-Patterns-Continued]]
- 下一讲：[[15-214-11-Design-Principles-GRASP]]
- 课程总览：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]
- 课程目录：[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸：Craig Larman《Applying UML and Patterns》是「找名词与动词」与 GRASP 的源头，本讲第 13–17 页的 POS 例子即出自该书；Martin Fowler《UML Distilled》对三种视角（conceptual / specification / implementation）有更完整的讨论；CMU-ISRI-05-108《Software Engineering for the 21st Century》可在网上检索到全文。概念建模的成果会直接进入下一讲 [[15-214-11-Design-Principles-GRASP]] 的职责分配（GRASP 的 Information Expert 就是在问「这个概念该由谁负责」）。
