---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L12
topic: Design Structure Matrices and Introduction to GUIs
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - DSM
  - 设计结构矩阵
  - 模块化
  - 耦合
  - EDSM
  - GUI
  - Swing
  - 事件驱动
  - MVC
  - Observer
---

# 第 12 讲 设计结构矩阵与 GUI 入门

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。本讲合并同一天的两份 slides：`dsms.pdf`（27 页，标题 "Design Analysis: Design Structure Matrices"，页脚日期 3 October 2013）与 `gui-intro.pdf`（34 页，标题 "Introduction to GUIs"）。两份讲义风格差异很大：前半是把耦合**定量化**的分析工具，后半是事件驱动编程的入门。

## 1. 本节学习目标

- 能用 DSM（设计结构矩阵）表示一组模块之间的依赖关系，并读懂其中的 X 标记。
- 能识别 DSM 中四种典型形态：全连接、全独立、分层（layered）、严格分层（strictly layered）。
- 能解释「聚类（clustering）」「层次依赖（hierarchically dependent）」「相互依赖（interdependent）」「独立（independent）」四个术语。
- 能说明接口如何把一条依赖「实体化」为两个依赖，从而解耦两个模块。
- 能用 DSM 对比 Parnas KWIC 的两种设计，并解释为什么设计 #2 在变化面前代价更低。
- 能说明 EDSM（Environment DSM）如何把「可能的变化」作为一行加入矩阵，从而把信息隐藏假说变成**可检验**的东西。
- 能说明 GUI 与命令行 I/O 的本质区别（事件驱动 / 好莱坞法则），并描述框架与应用的分工。
- 能写出一个最小 Swing 程序的结构（`JFrame` + `JPanel` + 布局 + 监听器）。
- 能解释 Swing 中「继承 `JPanel`」与「实现 `ActionListener`」为何采用不同机制。
- 能画出 MVC 的三方关系，并说明 passive model 与 active model 的区别。

## 2. 前置知识

- [[15-214-11-Design-Principles-GRASP]]：耦合、内聚、信息隐藏、Parnas KWIC 案例——本讲前半就是把这些概念变成矩阵。
- [[15-214-07-Design-Patterns]]：Strategy、Observer、Template Method——本讲后半会反复用到。
- [[15-214-09-Design-Patterns-Continued]]：Decorator 与 Java I/O 的「包装」思想。
- [[15-214-04-Inheritance-Typechecking-Dispatch]]：接口与继承的区别，是 5.13 节「接口 vs 继承」的基础。
- Java 语法：内部类、匿名内部类、`final` 局部变量。

## 3. 核心概念

- **DSM（Design Structure Matrix，设计结构矩阵）**：N×N 矩阵，行与列都是模块，`X` 表示行依赖列。
- **聚类（clustering）**：DSM 中成组的 X 形成的方块，代表「原模块（proto-module）」。
- **层次依赖（hierarchical dependence）**：B 依赖 A（B 行 A 列有 X）——改 A 可能要改 B。
- **相互依赖（interdependence）**：B 与 C 互相有 X。
- **接口实体化（interface reification）**：引入接口 I，使「B 依赖 A」变成「A 与 B 都依赖 I」。
- **EDSM（Environment DSM）**：把环境变化（如「输入格式变化」）作为额外的行加入 DSM。
- **事件驱动编程（event-based programming）**：控制流由外部事件驱动，而非由程序顺序推进。
- **好莱坞法则（Hollywood Principle）**："Don't call us, we'll call you"——框架调用你的代码。
- **监听器（Listener）**：Observer 模式在 GUI 中的名字；实现接口并向组件注册。
- **布局管理器（Layout Manager）**：`BorderLayout`、`FlowLayout` 等，本身是 Strategy 模式。
- **MVC（Model-View-Controller）**：把领域数据、显示、输入处理三者分离。
- **被动模型 / 主动模型（passive / active model）**：模型是否持有视图引用、是否主动通知。

## 4. 通俗理解

**为什么需要 DSM？** 第 11 讲说了「低耦合好、高耦合坏」，但「耦合有多高」一直是个感觉。`dsms.pdf` 第 2 页把问题摆清楚：

> - **Ideal**: changes restricted to within a module
> - **Goal of information hiding**
> - Need to know which decisions may change
> - **Reality: some changes are surprises**
> - These may affect module interfaces
> - **Changes propagate to dependent modules**
> - **How bad is this propagation?**
> - **It depends on coupling**

最后两行是整讲的动机：信息隐藏的理想是「改动不出模块」，但现实中总有意外变化会穿透接口、传播到依赖者。**传播有多严重，取决于耦合**——所以我们需要一个能**看见**耦合的工具。

**DSM 就是一个「耦合雷达图」。** 它把「谁依赖谁」画成矩阵，让你一眼看出：哪些模块缠成一团（该拆）、哪些模块孤零零（可能没人用）、依赖是单向还是双向。

**为什么同一天讲 GUI？** 看起来突兀，其实有暗线：GUI 是**框架**（framework）的典型例子，而框架正是「依赖方向反转」的产物——不是你的代码调用框架，而是框架调用你的代码（第 3 页："Don't call us, we'll call you!"）。用 DSM 的语言说，你的应用与框架之间有一条**双向**的强耦合，但这种耦合是**可接受**的，因为框架的接口非常稳定（回想第 11 讲「High coupling to very stable elements is usually not problematic」）。这条暗线会在第 16 讲（Frameworks）被正式展开。

## 5. 原理与推导

### 5.1 DSM 的定义与读法

`dsms.pdf` 第 4 页：

> - A DSM is an **alternative to a directed graph**
> - An **N by N matrix**
> - Each **row is a module** in the system
> - **Columns also labeled with modules, in same order**
> - Dependencies are marked with **X's**
> - Marking **row A, column B means A depends on B**
> - **The diagonal is ignored** (self-dependence)
> - **Makes it easy to see common patterns**

三个要点必须记牢：

1. **行依赖列**（row depends on column）——不是反过来。这是最容易记混的地方。
2. **对角线忽略**（自依赖无意义），所以对角线常写作 `0` 或 `O` 或 `.`。
3. **行列顺序相同**，因此矩阵的**形状**本身携带信息：X 集中在对角线附近 = 依赖局部化；X 散布在远处 = 依赖跨模块。

第 5 页的最小例子（MVC 的两元素版）：

```
        Model  GUI
Model    0
GUI      X     0
```

读法：`GUI` 行、`Model` 列有 X → **GUI 依赖 Model**；`Model` 行、`GUI` 列空 → Model 不依赖 GUI。这就是「单向依赖」，也是 MVC 的核心约束（模型不知道视图存在）。

### 5.2 四种典型形态

课件第 6–9 页用同一个 5 模块系统（A–E）演示四种形态，这是 DSM 的「模式识别」训练。

**（1）全连接（Fully Connected，第 6 页）**

```
    A  B  C  D  E
A   O  X  X  X  X
B   X  O  X  X  X
C   X  X  O  X  X
D   X  X  X  O  X
E   X  X  X  X  O
```

除对角线外**全是 X**。含义：任何模块改动都可能影响其他所有模块。这是**最坏**的情况——系统退化为一个大泥球（big ball of mud），信息隐藏完全失效。

**（2）全独立（Fully Disconnected，第 7 页）**

```
    A  B  C  D  E
A   O
B      O
C         O
D            O
E               O
```

除对角线外**全空**。含义：五个模块互不相干。这看起来「完美解耦」，但课件只是把它作为**极端参照**——真实的系统不可能这样，因为模块之间总要通过某种方式协作。全独立意味着这个「系统」其实是五个独立程序。

**（3）分层架构（A Layered Architecture，第 8 页）**

```
        Kernel  Ring1  Ring2  Ring3  Ring4
Kernel    O
Ring1     X       O
Ring2     X       X       O
Ring3     X       X       X       O
Ring4     X       X       X       X       O
```

下半三角全 X：每个 Ring 都依赖**所有**内层（Kernel 及更内层的 Ring）。这是操作系统保护环（protection ring）的经典结构。特点：**依赖单向**（外层依赖内层，内层不知道外层），但**每个外层模块的依赖数随层数线性增长**。

**（4）严格分层（A Strictly Layered Architecture，第 9 页）**

```
             OS   VM   I/O lib  Middleware  App
OS           O
VM           X    O
I/O lib      X         O
Middleware   X              O
App          X                        O
```

只有**第一列**有 X：每个模块**只**依赖 OS（相邻的下层），不依赖其他任何层。这是「严格分层」——第 n 层只能调用第 n−1 层。对比第 8 页，依赖数从 O(n) 降到 O(1)，代价是**跨层调用必须逐层转发**（App 想用 I/O lib 的功能，必须经过 Middleware 转手，或者 I/O lib 也要依赖 OS 之上再加一层）。

这四种形态给出了一个可用的**评价标尺**：把真实系统的 DSM 画出来，看它更接近哪一种。

### 5.3 术语：层次依赖、相互依赖、独立

课件第 10 页：

> - **B is hierarchically dependent on A**
>   - If you change A, you might have to change B as well
>   - **Suggests you should implement A first**
> - **B and C are interdependent**
> - **C and A are independent**

三点值得展开：

**（1）「层次依赖」暗示实现顺序。** 这与第 11 讲第 43 页「Start with class with least dependencies」完全一致——DSM 给了这个建议一个**可视化的依据**：从矩阵中「没有任何 X 的行」开始（它不依赖别人），实现完删掉它的行列，重复。

这其实是**拓扑排序（topological sort）**：如果依赖图无环，就存在一个实现顺序；如果有环（相互依赖），就必须先打破环。

**（2）「相互依赖」是危险信号。** B 与 C 互相依赖，意味着它们实际上是一个**不可分割的单元**——你没法单独理解、单独测试、单独复用其中一个。这正是课件下一节「聚类」要处理的问题。

**（3）「独立」是最理想的但最罕见。** 真实系统中大多数模块对之间是「间接依赖」（通过第三方），DSM 只记录直接依赖，所以间接依赖要看「路径」。

### 5.4 聚类：proto-module 与「真模块」

课件第 11 页：

> - **Lines show clustering into proto-modules**
> - Indicates several design decisions will be **managed together**
> - **True modules should be independent**
>   - i.e., **no marks outside of its cluster**
> - **Not true here because B (in the B-C cluster) depends on A**

「聚类（clustering）」是把 DSM 中相邻的 X 圈成方块。被圈在一起的模块构成一个 **proto-module（原模块 / 准模块）**——它们的设计决策实际上是一起管理的。

判据很干脆：**真模块的聚类方块之外不能有 X**。课件举的反例是：B 与 C 聚成一簇，但 B 还依赖 A——于是 B 的决策既受 C 影响又受 A 影响，这个簇不是一个真正的模块。

这条判据可以直接操作化：**把 DSM 的行列重排，让 X 尽量靠近对角线；如果重排后仍有 X 落在方块外，那些就是「跨模块的隐藏耦合」**。这也是 Lattix LDM 之类工具的核心算法（第 27 页提到）。

### 5.5 接口：把依赖实体化

课件第 13 页，本讲最重要的一页：

> - **Interface reifies the dependence as a separate entity**
> - Instead of **B depending on A**, now **A and B both depend on I**
> - **Serves to decouple A and B**
> - **Think of I as the interface of A**

初看这像是**变糟了**：原来 1 条依赖（B→A），现在 2 条（A→I、B→I），依赖总数增加了。为什么说是「解耦」？

关键在于**依赖的强度与稳定性不同**：

| 维度 | B→A（直接依赖） | A→I、B→I（经接口） |
|---|---|---|
| 依赖的对象 | A 的**全部**（接口 + 实现 + 内部结构） | 只有 I 的**签名**（稳定决策） |
| A 的实现变化 | 可能波及 B | 不影响 B（只要 I 不变） |
| A 的替换 | 需要改 B | 只需提供另一个实现 I 的类 |
| 谁可以复用 B | 只有 A 的客户端 | 任何 I 的实现 |

所以「解耦」在这里的准确含义是：**依赖的数量可能增加，但依赖的「穿透深度」下降了**。B 不再能看见 A 的内部，只能看见 I 承诺的那几个方法。

这也解释了第 11 讲 Meyer 的「Few Interfaces / Small Interfaces」为什么是两条独立规则：接口化会让 Few 变差（边变多），但让 Small 与 Explicit 变好。**设计就是在这些张力中取舍。**

### 5.6 KWIC 的 DSM：设计 #1 与设计 #2

这是本讲的实证核心。课件第 15–20 页把 Parnas 的 KWIC 案例画成 DSM。模块编号如下（第 15、17 页）：

**设计 #1（按处理步骤分解）的 13 个元素**：

| 编号 | 元素 | 类别 |
|---|---|---|
| A | Input Type | 类型 |
| D | Circ Type | 类型 |
| G | Alph Type | 类型 |
| J | Out Type | 类型 |
| B | In Data | 数据 |
| E | Circ Data | 数据 |
| H | Alph Data | 数据 |
| K | Out Data | 数据 |
| C | Input Alg | 算法 |
| F | Circ Alg | 算法 |
| I | Alph Alg | 算法 |
| L | Out Alg | 算法 |
| M | Master | 主控 |

**设计 #2（信息隐藏分解）的 16 个元素**：在 #1 的 13 个之外，多了三个——`N - Line Type`、`O - Line Data`、`P - Line Alg`。

**设计 #1 的 DSM 结构**（第 16 页）的关键特征：

- `E - Circ Data` 依赖 `B - In Data`（X 在 B 列）——循环移位的数据结构**直接建立在**输入的数据结构上；
- `H - Alph Data` 依赖 `B` 与 `E`；
- `C - Input Alg`、`F - Circ Alg`、`I - Alph Alg`、`L - Out Alg` 各自依赖对应的 Data 与 Type；
- `M - Master` 依赖四个 Type。

课件在第 16 页给出三条批注：

> - **Interdependence of data formats**（数据格式相互依赖）
> - **True modules**（指 Type 那四行——它们没有出簇的 X）
> - **Many dependences on data format; problematic because data formats are unstable**（大量依赖数据格式；有问题，因为数据格式是不稳定的）
> - **Interface dependences follow calls**（接口依赖沿调用关系走）

第三行是全讲的**判决词**：设计 #1 的模块之间通过**共享数据结构**通信，而数据结构恰恰是最不稳定的决策。

**设计 #2 的 DSM 结构**（第 18 页）：

新增的 `N - Line Type`、`O - Line Data`、`P - Line Alg` 构成了一个 `Line Storage` 模块。批注只有两条：

> - **True modules**
> - **Dependence on interfaces**

也就是说，在设计 #2 中，`O - Line Data`（真正的存储实现）被 `P - Line Alg` 与 `N - Line Type` 包住，其他所有模块（`B`、`E`、`H`、`K`、`C`、`F`、`I`、`L`）都只依赖 `N`（Line Type 接口），**没有一个模块依赖 `O`（实际数据表示）**。

**定量比较**（第 20 页）：

> - Both designs allow changes within modules
> - However, in the first design **the modules do not hide much**
>   - **Many dependencies (2-4 per module) on data structures**
>   - **Data structure dependencies are strong: they restrict algorithms used**
>   - Furthermore, **data structures are likely to change**
> - The second design is **much less constrained**
>   - **Fewer dependencies (1-2 per module)**
>   - **Interfaces are more abstract, do not restrict code as much**
>   - **Interfaces are more stable in the face of likely changes**
> - **Result: design 2 minimizes re-engineering in response to change**

注意这里的比较维度是**每模块依赖数**（2–4 vs 1–2）——这正是 DSM 把「耦合」变成可数指标的成果。

### 5.7 EDSM：把「变化」也放进矩阵

课件第 21 页引入 EDSM（Environment DSM，出自 Sullivan et al., ESEC/FSE 2001）：

> - **Environment and Design Structure Matrices**
> - Add **changes as environmental parameters**
> - Note: **slightly more concrete than what Sullivan et al. propose**
> - **Only partially controlled by designer**
> - **May affect each other**
> - **May affect design decisions in code**
> - **What interfaces are affected?** → **Information hiding: interfaces should be stable**
> - **What implementations are affected?** → **Information hiding hypothesis: should be local to a module**

这是一个非常漂亮的方法论动作。第 11 讲说信息隐藏「把可能变化的决策藏进模块」，但「可能变化」是个**假说**——你凭什么相信某个决策会变？EDSM 的答案是：**把变化本身列成矩阵的行，让假说变成可检查的预测**。

五个环境参数（第 22、24 页）：

| 编号 | 变化 | 含义 |
|---|---|---|
| V | Input Fmt | 输入格式改变 |
| W | Store Mem | 不再把所有行放进内存 |
| X | Compress | 编码压缩以省空间 |
| Y | Shift Store | 直接存储循环移位结果 |
| Z | Amortize | 摊销排序成本 |

**设计 #1 的变化传播**（第 23 页）：五个变化行上，X 密密麻麻地铺满了 `B`、`E`、`H`、`C`、`F`、`I`、`L`、`M` 各列。批注：

> - **Unstable data interfaces depend on changes**（不稳定的数据接口依赖变化）
> - **Algorithms depend on data**（算法依赖数据）

后果是**级联**：变化 → 数据格式 → 算法 → 主控。改一个环境参数，几乎整个系统都要动。

**设计 #2 的变化传播**（第 25 页）：X 集中在 `O - Line Data`、`P - Line Alg`、`N - Line Type` 三列（即 Line Storage 模块内部），其他模块（`B`、`C`、`E`、`F`、`H`、`I`、`K`、`L`、`M`）几乎不受影响。批注：

> - **Interfaces are stable**
> - **Effect of change is localized**

第 26 页的「Comparison」有一处需要注意的表述：

> - **Design 1 hides information better**
>   - Interfaces are unaffected by likely change scenarios
>   - Changes required to implement likely change scenarios are local

> 待核实：第 26 页写作 "Design 1 hides information better"，但上下文（第 20、25 页的图与结论）都指向 **Design 2** 更好。结合第 25 页「Design #2 的接口稳定、变化局部化」与第 20 页「design 2 minimizes re-engineering」，此处「Design 1」应为笔误，实指 Design 2（即 Parnas 的信息隐藏设计）。笔记按 Design 2 理解，并在此标注原文疑误。

### 5.8 小结与工具

课件第 27 页：

> - **DSMs are a structured way of thinking about the value of design**
> - Are design decisions **isolated to a module**, or do they **affect several modules**?
> - How do modules **depend on interfaces**?
> - **On which parts of the system can I experiment independently?**
> - **How much value is there in the experiments?**
>   - Technical potential of the module
> - **EDSMs incorporate change scenarios**
>   - How are interfaces and code affected by change?
> - **More to explore**
>   - **Baldwin and Clark** – discuss value of modularity
>   - **Sullivan and Griswold** – apply B&C to S/W, introduce EDSMs
>   - **Lattix LDM tool** – derives DSMs from code

最后一条很重要：**DSM 可以从代码自动导出**（Lattix LDM 就是做这个的）。这意味着 DSM 不是只能用在设计阶段的草图，也可以用在**遗留系统的架构体检**上。

「On which parts of the system can I experiment independently?」这个问题把模块化与**真实期权（real options）**理论联系起来——Baldwin & Clark 的《Design Rules》正是用期权思维解释模块化的价值：模块化让你可以**先投资一小部分、保留以后改变主意的权利**，而不必一次性押注整个设计。

### 5.9 GUI 与命令行的本质区别

`gui-intro.pdf` 第 2–3 页用两个提问切入：

> **What makes GUIs different?**
> - How do they compare to command-line I/O?
>
> **Don't call us, we'll call you!**
> - GUI has to **react to the user's actions**
>   - Not just a response to a prompt
>   - **Could involve entirely different functionality**
> - Requires **structuring the GUI around reacting to events**

这个对比值得展开：

| 维度 | 命令行 I/O | GUI |
|---|---|---|
| 控制流 | 程序主导：打印提示 → 读输入 → 继续 | 用户主导：程序等待，事件到来时被调用 |
| 顺序 | 线性、可预测 | 任意、不可预测 |
| 功能范围 | 每次交互只做一件事 | 任何时刻可能触发任何功能 |
| 代码结构 | 一个 `main` 顺序执行 | 一组**回调（callback）**，由框架调用 |
| 状态 | 局部变量即可 | 需要长期存在的对象状态 |

第 3 页那句 **"Don't call us, we'll call you!"** 就是第 9 讲讲过的**好莱坞法则**（Template Method 的特征）。在 GUI 里它变成了**全局的组织原则**：你的 `main()` 创建窗口后就**退出**（第 6 页："main() exits"），此后所有代码都由框架通过事件回调驱动。

这与第 11 讲的 DSM 视角接上了：**框架与应用之间是一条双向强耦合**——框架调用应用（回调），应用调用框架（`repaint()`、`setLayout()`）。但这种耦合之所以可接受，是因为**框架的接口极其稳定**（Swing 的 `ActionListener` 十年没变），符合「耦合到稳定元素通常无害」。

### 5.10 事件驱动编程与框架/应用分工

课件第 4 页：

> **Event-based programming**
> - A style of programming where the **control-flow of the program is driven by (usually-) external events**

第 4 页用三张并排的图示意：同一个方法签名 `performAction(ActionEvent e)`，一个调用 `printSlides()`，一个调用 `editFigure()`，一个留空。这直观说明：**事件的「处理内容」由应用决定，事件的「分发机制」由框架提供**。

第 5 页给出分工：

> **Reacting to events - from framework**
> - **Setup phase**
>   - Describe how the GUI window should look
>   - Use libraries for windows, widgets, and layout
>   - **Define custom functionality**
>     - New widgets that display themselves in custom ways
>     - **How to react to events**
> - **Execution phase**
>   - **Framework gets events from OS**
>     - Mouse clicks, key presses, window becomes visible, etc.
>   - **Framework triggers application code in response**
>     - The customization described above

时序图（第 5 页）：`Framework` ← `OS` 取事件（get event）→ `Framework` 向 `Application` 发事件 → `Application` 回以绘图命令（drawing commands）→ `Framework` 再取下一个事件（next event）。事件类型包括 mouse、key、redraw。

**第 6 页的伪代码是整份讲义最实用的一页**，它把「谁负责什么」讲得极清楚：

> **Application code**
> - Creates and sets up a window
> - Asks framework to show the window
> - **main() exits**
> - Takes action in response to event
> - May contact GUI
>   - E.g. consider if event was a redraw
>   - Call GUI to paint lines, text
>
> **GUI framework code**
> - **Starts the GUI thread**
> - **This thread loops:**
>   - Asks OS for event
>   - Finds application window that event relates to
>   - **Asks application window to handle event**
>   - Draws lines/text on behalf of application

注意「**main() exits**」这一行——这是事件驱动与命令式最反直觉的差别。`main` 不是程序的主体，它只是**启动器**。真正的「主循环」在框架里（GUI thread），你的代码以回调形式被反复调用。

这个结构有一个重要后果：**所有回调都运行在同一个线程（EDT）上**，因此 GUI 代码天然是「单线程 + 事件队列」模型。这一点在第 13 讲与并发部分会被重新审视（长任务会冻结界面）。

### 5.11 Swing 的最小结构

课件第 8 页列出 Java 的 GUI 框架谱系：

| 框架 | 特点 |
|---|---|
| **AWT** | 原生控件（native widgets），只有基础组件，**过时（dated）** |
| **Swing** | Java 自己渲染（Java rendering），组件丰富 |
| **SWT + JFace** | 原生控件与 Java 渲染混合；为 Eclipse 创建，追求更快性能 |
| **其他** | Apache Pivot、SwingX、JavaFX… |

第 9 页给出 Swing 的类层次直觉：`JFrame` 是窗口，里面装 `JPanel`，`JPanel` 里装 `JButton`、`JTextField` 等。

**创建简单 Swing 应用的六步**（第 10 页）：

> 1. Make a Window (a `JFrame`)
> 2. Make a container (a `JPanel`)
>    - Put it in the window
> 3. **Add components** (Buttons, Boxes, etc.) to the container
>    - **Use layouts to control positioning**
>    - **Set up observers (a.k.a. listeners) to respond to events**
>    - Optionally, write **custom widgets** with application-specific display logic
> 4. Set up the window to display the container
> 5. **Then wait for events to arrive…**

第 11 页列出常用组件：`JLabel`、`JButton`、`JCheckBox`、`JChoice`、`JRadioButton`、`JTextField`、`JTextArea`、`JList`、`JScrollBar`。

第 12 页区分两个核心类：

> - **`JFrame` is the Swing Window**
> - **`JPanel` (aka a pane) is the container** to which you add your components (or other containers)

第 13 页讲布局管理器，并给出 Oracle 教程链接 `http://docs.oracle.com/javase/tutorial/uiswing/layout/visual.html`：

- **`FlowLayout`**：最简单、也是默认的布局，空间不够时**换行（wraps around）**；
- **`BorderLayout`**：像 `FlowLayout`，但**不换行**；
- 还有更复杂的布局管理器。

第 14 页有一个「Find the pattern…」的提问，代码是：

```java
contentPane.setLayout(new BorderLayout(0,0));
contentPane.setBorder(new EmptyBorder(5, 5, 5, 5));
```

第 15 页给出答案：**Strategy（策略）模式**。`LayoutManager` 是一个接口，`BorderLayout`、`FlowLayout` 是具体策略，`contentPane` 是 Context——`setLayout()` 就是「运行时替换算法」。课件列出 Strategy 的适用性与后果：

> **Applicability**
> - Many classes differ in only their behavior
> - Client needs different variants of an algorithm
>
> **Consequences**
> - Code is **more extensible** with new strategies（compare to conditionals）
> - **Separates algorithm from context** — each can vary independently
> - **Adds objects and dynamism** — code harder to understand
> - **Common strategy interface** — may not be needed for all Strategy implementations — may be **extra overhead**

最后两条是第 9 讲已经讲过的 Strategy 代价：多了一层对象、多了一个可能不必要的接口。布局管理器这个例子恰好展示了收益（换布局不改容器代码）与代价（多一层间接）。

### 5.12 事件与监听器

第 17 页提问：**How do you make a button work?**

第 18 页回答：

> - **An event is when something changes**
>   - Button clicked, scrolling, mouse movement
> - **Swing (actually AWT) generates an event**
> - **To do something you need to implement a Listener Interface and register interest**

注意「actually AWT」这个括注：Swing 建立在 AWT 的事件模型之上，事件类（`ActionEvent`、`MouseEvent`）来自 `java.awt.event`。

第 19 页给出 **Observer 模式**的完整 UML 与说明，并注明「Also called Listener」：

```
        Subject                      <<interface>> Observer
+ attach(o : Observer)                    + update()
+ detach(o : Observer)
# notify()                       ConcreteObserver
observers 0..*                       + update()
                                     + observerState
ConcreteSubject
+ getState()
+ setState()
subjectState

notify():  for all o in observers
               o.update();
```

> **Applicability**
> - When an abstraction has **two aspects, one dependent on the other**, and you want to reuse each
> - When change to one object requires changing others, and **you don't know how many objects need to be changed**
> - When an object should be able to **notify others without knowing who they are**
>
> **Consequences**
> - **Loose coupling between subject and observer**, enhancing reuse
> - **Support for broadcast communication**
> - **Notification can lead to further updates, causing a cascade effect**

第二条适用性正是 GUI 的核心：一个按钮可能被零个、一个或多个监听器关注，按钮**不需要知道**有多少个。第三条后果「级联（cascade）」在第 7 讲已经作为 Observer 的代价提过——在 GUI 里它表现为「一次点击引发连锁重绘」，如果处理不当会卡顿甚至无限循环。

第 20 页列出 Swing 的监听器家族：`ActionListener`、`AdjustmentListener`、`FocusListener`、`ItemListener`、`KeyListener`、`MouseListener`、`TreeExpansionListener`、`TextListener`、`WindowListener`……「and on and on…」。

第 21 页聚焦 `ActionListener`：

> - **Events for `JButton`s, `JTextField`s, etc** — the things we are using
> - **Implement `ActionListener`** — provide `actionPerformed` method
> - In `actionPerformed` method
>   - Use **`event.getSource()`** to determine which button was clicked, etc.

`event.getSource()` 这个细节值得注意：如果你用**同一个**监听器对象注册到多个按钮，就必须在 `actionPerformed` 里判断来源。这也是为什么更常见的做法是**每个按钮一个匿名内部类**——那样就不需要 `getSource()`。

### 5.13 匿名内部类与作用域陷阱

第 22 页讲 RabbitWorld 的例子：

> - `...hw2.lib.ui.WorldUI.WorldUI()`
>   - **Sets `ActionListener`s for the run and step buttons**
>   - **Anonymous inner classes used**
>   - A single method `actionPerformed(…)` is overridden
>   - **step button**: just calls `step()` on the `WorldPanel`
>     - Steps the world
>     - Requests that the window be refreshed (so the user can see the changes)
>   - **run button**
>     - Starts the world continuously stepping
>     - **Disables the step button (no point!)**
>     - **Sets a toggle flag** so that pressing the button again will stop the simulation

「Disables the step button」是一个小但重要的设计细节：**UI 状态应当反映应用的合法状态**。运行中手动步进没有意义，所以禁用——这避免了「用户能做出无效操作」的整类 bug。

第 23 页解释匿名内部类：

> You can implement an interface **without naming the implementing class**

```java
public interface Runnable {
    public void run();
}

public static void main(String[] args) {
    Runnable greeter = new Runnable() {
        public void run() {
            System.out.println("Hi mom!");
        }
    };
    greeter.run();
}
```

第 24–25 页讲**作用域陷阱**，这是 Java 初学者最常踩的坑之一：

> An anonymous inner class **cannot access non-final variables** in the scope where it is defined

```java
// 编译期错误
public static void main(String[] args) {
    String name = "Charlie";          // 非 final
    Runnable greeter = new Runnable() {
        public void run() {
            System.out.println("Hi " + name);   // compile-time error
        }
    };
    greeter.run();
}

// OK
public static void main(String[] args) {
    final String name = "Charlie";    // final
    ...
}
```

原因（讲义未展开，此处补充）：局部变量存在**栈**上，方法返回后即消失；而匿名内部类对象可能活得更久。所以 Java 在创建内部类对象时，会把捕获的局部变量**拷贝**进内部类的合成字段。如果原变量可变，拷贝就会与原变量不同步——两个「同名变量」值不同，会产生极难发现的 bug。因此语言**禁止**捕获非 final 局部变量（Java 8 起放宽为「effectively final」，即虽未写 `final` 但从未被重新赋值即可）。

这个陷阱在 GUI 代码里几乎必然遇到：监听器里要用到 `main` 或构造器里的局部变量，所以必须声明为 `final`（或 Java 8+ 的 effectively final）。

### 5.14 组织技巧与「接口 vs 继承」

第 26 页给出两条实用的组织建议：

> - **Declare references to components you'll be manipulating as instance variables**
> - **Put the code that performs the actions in private "helper" methods.** (Keeps things neat)

第一条的必要性来自事件驱动模型：`actionPerformed` 被调用时，你需要访问按钮、面板等组件来读取状态或修改显示，而它们不可能通过参数传进来——只能作为字段。这与「字段应当最小化」的直觉冲突，但在 GUI 里是必要的取舍（更准确地说，这些字段是**视图状态**，属于视图对象的合理职责）。

第二条把「回调方法」与「业务逻辑」分开：`actionPerformed` 只做分发，真正的工作在私有辅助方法里。这样辅助方法可以被**单元测试**直接调用——而 `actionPerformed` 很难测（需要构造 `ActionEvent`）。这是第 8 讲「可测试代码」在 GUI 场景的应用。

第 27–28 页是本讲最有教学价值的一段：**为什么 `JPanel` 用继承，而 `ActionListener` 用接口？**

第 27 页先摆出问题：

> **GUI design issues**
> - **Interfaces vs. inheritance**
>   - **Inherit from `JPanel`** with custom drawing functionality
>   - **Implement the `ActionListener` interface**, register with button
>   - **Why this difference?**
> - **Models and views**

第 28 页给出四条理由（前三条解释 `JPanel`，后三条解释 `ActionListener`）：

> **Inherit from `JPanel`:**
> - Subclass **"is a" special kind of Panel**（是 is-a 关系）
> - The subclass **interacts closely with the `JPanel`** — e.g. the subclass calls back with `super()`
> - **The way you draw the subclass doesn't change as the program executes**（行为在运行时不变）
>
> **Implement the `ActionListener`:**
> - The action to perform **isn't really a special kind of button**; it's just a way of **reacting** to the button. So it makes sense to be a **separate object**（不是 is-a 关系）
> - The `ActionListener` is **decoupled from the button**. Once the listener is invoked, **it doesn't call anything on the Button anymore**（单向依赖）
> - **We may want to change the action performed on a button press** — so once again it makes sense for it to be a separate object（需要在运行时替换）

这三条对照几乎可以作为「何时用继承、何时用组合」的**判定清单**：

| 判据 | 倾向继承 | 倾向组合/接口 |
|---|---|---|
| 是 is-a 关系吗 | 是 | 否 |
| 需要回调父类（`super`）吗 | 是 | 否 |
| 行为在运行时**会变**吗 | 不会 | 会 |
| 是否需要在运行时**替换** | 不需要 | 需要 |
| 与对方的耦合方向 | 双向（子类调 `super`） | 单向（只被调用） |

这与第 3 讲的「优先组合」并不矛盾——第 3 讲说的是**默认**倾向组合，而 `JPanel` 子类化是一个**经过论证的例外**：它满足 is-a、需要 `super` 回调、且绘制行为不随运行变化。课件没有说「继承是错的」，而是展示了**如何论证**继承的合理性。

第 28 页末尾「Models and views」是下一节的引子。

### 5.15 MVC 与 RabbitWorld 的映射

第 29 页给出 MVC 的三方职责（图源 `http://msdn.microsoft.com/en-us/library/ff649643.aspx`）：

> - **Controller**：Manage inputs from user: mouse, keyboard, menu, etc.
> - **View**：Manage display of information on the screen
> - **Model**：Manage data related to the application domain

第 30 页区分两种模型：

> - **Passive model**（被动模型）
> - **Active model**（主动模型）

两者差别在于**通知方向**：

| | Passive Model | Active Model |
|---|---|---|
| 模型是否知道视图 | **不知道** | 知道（持有观察者列表） |
| 数据变化时 | 模型**静默**变化 | 模型**主动通知**观察者 |
| 谁触发刷新 | **控制器**在改完模型后调用视图刷新 | **模型**通知视图 |
| 实现手段 | 直接方法调用 | Observer 模式 |
| 优点 | 模型最纯粹，可独立测试；无循环依赖 | 多视图自动同步；模型变化可广播 |
| 缺点 | 每个控制器都要记得刷新（易漏） | 模型依赖 Observer 机制；可能级联 |

第 31 页把 RabbitWorld 的三部分对上：

> - `...hw2.lib.ui.WorldImpl`
>   - **The Model class**
>   - **Model is passive: does not have a reference to the view**
> - `...hw2.lib.ui.WorldUI`
>   - **The Controller class**
>   - **Listener callbacks in constructor react to events**
>   - **Delegating to the view (is this design ideal?)**
> - `...hw2.lib.ui.WorldPanel`
>   - **The View class**
>   - **Gets data from Model to find out where to draw rabbits, foxes, etc.**
>   - **Implements stepping (in `step()`)**
>     - Invokes model to update world
>     - **Invokes `repaint()` on self to update UI**

这里有两个值得停下来想的点：

**（1）「Delegating to the view (is this design ideal?)」** —— 课件自己在质疑这个设计。`WorldUI`（Controller）把事件处理**委托给** `WorldPanel`（View），于是 View 实际上承担了部分 Controller 职责。这不是纯粹的 MVC。理想的分工是 Controller 决定「做什么」，View 只负责「怎么画」。但在小型 GUI 里，这种混合很常见——因为**分离需要额外的接口与转发代码**，而收益（可替换视图）在只有一个视图时体现不出来。这是一个典型的「原则 vs 成本」的取舍，课件用提问的方式留给学生判断。

**（2）`step()` 既改模型又 `repaint()`** —— 这是 **passive model** 的必然结果：模型不通知，所以**改完模型的人必须负责刷新**。`WorldPanel.step()` 里的两行代码（更新模型 + `repaint()`）正是这个责任的体现。这也解释了 passive model 的主要风险：**任何一处忘记 `repaint()`，界面就会显示过期数据**。

第 32 页「Find That Pattern!」用五个提问复习全课的 GoF 模式：

> - What pattern is **`BorderLayout`** a part of? → **Strategy**（布局算法可替换）
> - What pattern is **`JPanel`** a part of? → **Composite**（容器与组件同一接口，可嵌套）
> - What pattern are the **`ActionListener`s** a part of? → **Observer**（课件第 19 页已明确）
> - There are classes representing the AI's decision to **Eat, Breed, or Move**. What pattern are these representing? → **Command**（把动作封装成对象；也可视为 Strategy）
> - Look at the documentation for **`JComponent.paint()`**. What pattern is used? → **Template Method**（父类定义绘制流程，子类覆写具体绘制）

> 待核实：第 32 页只提出问题，未在讲义中给出答案。上述答案依据第 7、9 讲对各模式的描述推导（`Composite` 见第 7 讲第 4 页 `IntSet`/`UnionSet`；`Command` 见第 7 讲第 29 页；`Template Method` 见第 9 讲第 7 页 `AbstractShape`）。`JComponent.paint()` 的 Template Method 判定基于「`paint()` 依次调用 `paintComponent()`、`paintBorder()`、`paintChildren()`」这一 Swing 约定，属笔记补充，非讲义原文。

第 33 页给出延伸资料：

> - Oracle's Swing tutorials：`http://download.oracle.com/javase/tutorial/uiswing/`
> - *Introduction to Programming Using Java*, Ch. 6：`http://math.hws.edu/javanotes/c6/index.html`

## 6. 代码示例

### 6.1 官方课程代码

出自 `gui-intro.pdf` 第 14 页（「Find the pattern…」的提问代码）：

```java
contentPane.setLayout(new BorderLayout(0,0));
contentPane.setBorder(new EmptyBorder(5, 5, 5, 5));
```

出自同文件第 23 页（匿名内部类）：

```java
public interface Runnable {
    public void run();
}

public static void main(String[] args) {
    Runnable greeter = new Runnable() {
        public void run() {
            System.out.println("Hi mom!");
        }
    };
    greeter.run();
}
```

出自同文件第 24 页（编译期错误版本）：

```java
public interface Runnable {
    public void run();
}

public static void main(String[] args) {
    String name = "Charlie";
    Runnable greeter = new Runnable() {
        public void run() {
            System.out.println("Hi " + name);   // compile-time error
        }
    };
    greeter.run();
}
```

出自同文件第 25 页（修正版）：

```java
public interface Runnable {
    public void run();
}

public static void main(String[] args) {
    final String name = "Charlie";
    Runnable greeter = new Runnable() {
        public void run() {
            System.out.println("Hi " + name);   // OK
        }
    };
    greeter.run();
}
```

出自同文件第 4 页（事件处理方法的形态，三份并列）：

```java
public void performAction(ActionEvent e) {
    printSlides();
}

public void performAction(ActionEvent e) {
    editFigure();
}

public void performAction(ActionEvent e) {
    …
}
```

`dsms.pdf` 的「代码」是矩阵本身而非 Java 代码。第 5 页的最小 DSM：

```
        Model  GUI
Model    0
GUI      X     0
```

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：把一个小系统的 DSM 写出来**

假设有四个模块：`Storage`（持久化）、`Domain`（领域模型）、`Service`（用例编排）、`UI`（界面）。依赖关系：`Service` 用 `Domain` 与 `Storage`，`UI` 用 `Service` 与 `Domain`，`Domain` 谁都不用。

```
            Storage  Domain  Service  UI
Storage        O
Domain                  O
Service        X        X        O
UI                              X     O     ← 注意：UI 依赖 Service，但这里没写 Domain
```

若 `UI` 也直接依赖 `Domain`（比如直接读实体字段来显示），则 `UI` 行在 `Domain` 列也会出现 X：

```
            Storage  Domain  Service  UI
UI              .       X        X     O
```

这时 `UI` 与 `Service` 都依赖 `Domain`，而 `Domain` 不依赖任何人——这是**健康的单向依赖**。但若 `Domain` 为了「方便」持有了 `UI` 的引用去弹提示框，就会出现 `Domain` 行 `UI` 列的 X，形成 `Domain ↔ UI` 的**相互依赖**，两个模块从此无法分开理解与测试。这正是 DSM 要暴露的东西。

**示例 B：用接口把依赖实体化（对应 5.5 节）**

```java
// 改造前：Service 直接依赖 MySqlStorage
public final class Service {
    private final MySqlStorage storage = new MySqlStorage();   // 依赖具体实现
    public void placeOrder(Order o) { storage.insert(o); }
}

// 改造后：引入接口 I，Service 与 MySqlStorage 都依赖 I
public interface OrderStorage {          // I：稳定决策
    void insert(Order o);
}

public final class Service {
    private final OrderStorage storage;  // 只依赖接口
    Service(OrderStorage storage) { this.storage = storage; }
    public void placeOrder(Order o) { storage.insert(o); }
}

public final class MySqlStorage implements OrderStorage {   // 实现也依赖 I
    public void insert(Order o) { /* SQL */ }
}
```

依赖数从 1 条变成 2 条，但 `Service` 不再知道「数据存在 MySQL 里」这个易变决策。若以后换成内存存储或文件存储，`Service` 一行不改——这就是第 5.7 节 EDSM 中「接口稳定、变化局部化」的手工版。

**示例 C：一个最小可运行的 Swing 程序（含监听器与 MVC 雏形）**

```java
import javax.swing.*;
import java.awt.*;

public final class CounterApp {

    // ---- Model：被动模型，不知道视图存在 ----
    static final class CounterModel {
        private int value = 0;
        int getValue() { return value; }
        void increment() { value++; }
        void reset() { value = 0; }
    }

    // ---- View：只负责画 ----
    static final class CounterPanel extends JPanel {
        private final CounterModel model;          // 视图依赖模型（单向）
        CounterPanel(CounterModel model) {
            this.model = model;
            setPreferredSize(new Dimension(200, 100));
        }
        @Override
        protected void paintComponent(Graphics g) {   // Template Method 的钩子
            super.paintComponent(g);                  // 先让 JPanel 画背景
            g.drawString("count = " + model.getValue(), 20, 50);
        }
    }

    // ---- Controller：接事件，改模型，再让视图重画 ----
    static final class CounterController {
        private final CounterModel model;
        private final CounterPanel view;
        CounterController(CounterModel model, CounterPanel view) {
            this.model = model;
            this.view = view;
        }
        void onIncrement() { model.increment(); view.repaint(); }  // 手动刷新
        void onReset()     { model.reset();     view.repaint(); }
    }

    public static void main(String[] args) {
        CounterModel model = new CounterModel();
        CounterPanel panel = new CounterPanel(model);
        CounterController controller = new CounterController(model, panel);

        JFrame frame = new JFrame("Counter");
        JPanel content = new JPanel(new BorderLayout(5, 5));   // Strategy：可换布局
        content.setBorder(BorderFactory.createEmptyBorder(5, 5, 5, 5));

        JPanel buttons = new JPanel(new FlowLayout());
        JButton inc = new JButton("+1");
        JButton rst = new JButton("Reset");
        buttons.add(inc);
        buttons.add(rst);

        // Observer：注册监听器（匿名内部类）
        inc.addActionListener(e -> controller.onIncrement());
        rst.addActionListener(e -> controller.onReset());

        content.add(panel, BorderLayout.CENTER);
        content.add(buttons, BorderLayout.SOUTH);

        frame.setContentPane(content);
        frame.pack();
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.setVisible(true);          // 之后 main 就结束了，控制权交给框架
    }
}
```

对应关系：

- `BorderLayout` / `FlowLayout` → **Strategy**（`setLayout` 替换算法）；
- `addActionListener` → **Observer**（`ActionListener` 就是 `Observer`，`JButton` 就是 `Subject`）；
- `paintComponent` → **Template Method**（`JComponent.paint()` 定义流程，子类填钩子）；
- `content` 里既能放 `panel` 又能放 `buttons` → **Composite**（容器与叶节点同一接口）；
- `CounterModel` **不持有** `CounterPanel` 引用 → **passive model**，因此每次改模型都要 `view.repaint()`（这就是课件第 31 页 `WorldPanel.step()` 里那两行的形态）。

> 说明：示例用 lambda 而非匿名内部类，是 Java 8+ 的等价写法（`ActionListener` 是函数式接口）。课件写于 2013 年，用的是匿名内部类；两者语义相同。

**示例 D：EDSM 思路的手工版——列出变化，问「改哪里」**

```java
// 假设需求可能发生以下变化：
//   V: 输入从 CSV 变成 JSON
//   W: 数据量超过内存，必须流式处理
//   X: 存储必须压缩
// 对每个变化，回答两个问题：
//   (1) 哪些接口需要改？（信息隐藏的理想答案：一个都不用改）
//   (2) 哪些实现需要改？（信息隐藏的理想答案：只改一个模块）

public interface RecordSource {          // 稳定接口：只承诺「能逐条给出记录」
    boolean hasNext();
    Record next();
}

final class CsvRecordSource implements RecordSource { ... }   // V 变化 → 只改这里
final class JsonRecordSource implements RecordSource { ... }  // V 的另一个实现

public interface RecordSink {            // 稳定接口：只承诺「能收下一条记录」
    void accept(Record r);
}

final class InMemorySink implements RecordSink { ... }         // W 变化 → 换实现
final class StreamingFileSink implements RecordSink { ... }

final class CompressingSink implements RecordSink {            // X 变化 → 加一个装饰器
    private final RecordSink inner;
    CompressingSink(RecordSink inner) { this.inner = inner; }
    public void accept(Record r) { inner.accept(compress(r)); }
}
```

三个变化分别落在**一个**实现类上，两个接口都不用改——这正是 EDSM 第 25 页「Interfaces are stable / Effect of change is localized」的手工验证。注意 `CompressingSink` 用的是第 9 讲的 **Decorator**：不修改原实现，而是包一层。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| **行依赖列** | **列依赖行** | DSM 的约定是 **row A, column B → A 依赖 B**（第 4 页）。记反了会把整个矩阵读成反向依赖图，结论完全颠倒 |
| **DSM** | **有向图** | 二者表达能力等价（DSM 是邻接矩阵）。DSM 的优势是**模式易识别**（聚类、层次一眼可见），有向图的优势是**路径易追踪** |
| **层次依赖（hierarchical）** | **相互依赖（interdependent）** | 前者单向（B→A），可以用拓扑序排出实现顺序；后者成环（B↔C），两者必须一起理解、一起改、一起测 |
| **聚类（clustering）** | **真模块（true module）** | 聚类只是「X 挨得近」的视觉分组（proto-module）；真模块要求**簇外无 X**。聚类是观察，真模块是判据 |
| **全连接** | **全独立** | 前者是最坏（改一处动全身），后者是「理想但不可能」（模块间毫无协作）。真实系统在两者之间 |
| **分层架构** | **严格分层架构** | 前者每个模块依赖**所有**内层（依赖数 O(n)）；后者只依赖**相邻**下层（依赖数 O(1)），代价是跨层调用要逐层转发 |
| **DSM** | **EDSM** | DSM 只有模块×模块；EDSM 额外加入「环境变化」行，用来检验「哪些接口会被变化穿透」——把信息隐藏假说变成可检验的预测 |
| **耦合数量** | **耦合强度** | 接口化会让依赖**条数增加**（1 条变 2 条），但依赖**穿透深度下降**（只看到签名）。所以「解耦」不等于「减少依赖条数」 |
| **命令行 I/O** | **GUI** | 前者程序主导、线性、可预测；后者用户主导、事件驱动、任意顺序。GUI 的 `main()` 创建窗口后就**退出**，控制权交给框架的 GUI 线程 |
| **`JFrame`** | **`JPanel`** | `JFrame` 是**窗口**（有标题栏、边框、最小化按钮）；`JPanel` 是**容器**（无边框，用来装组件或其他容器）。通常 `JFrame` 里放一个 `JPanel` |
| **`FlowLayout`** | **`BorderLayout`** | 前者空间不够时**换行**；后者把区域分为 CENTER/NORTH/SOUTH/EAST/WEST，**不换行**。二者都是 Strategy 的具体策略 |
| **继承 `JPanel`** | **实现 `ActionListener`** | 前者是 is-a、需要 `super()` 回调、绘制行为运行时不变；后者不是 is-a、与按钮单向解耦、动作可能运行时替换——所以用独立对象（第 28 页的三条理由） |
| **Observer** | **Listener** | 同一个模式的两个名字。Swing 用「Listener」是因为它强调「注册兴趣」这个动作（`addActionListener`） |
| **`ActionListener`** | **`MouseListener`** | 前者关心「语义动作」（按钮被激活，可用键盘触发）；后者关心「原始鼠标事件」（按下/释放/进入/离开）。无障碍与键盘操作要求优先用 `ActionListener` |
| **passive model** | **active model** | 前者模型不知道视图，改完模型必须**手动**刷新（易漏）；后者模型持观察者列表，变化时**主动通知**（多视图自动同步，但可能级联） |
| **匿名内部类** | **lambda** | 语义等价（对函数式接口）。2013 年课程用匿名内部类；Java 8+ 可用 lambda。二者都只能捕获 **final / effectively final** 的局部变量 |

## 8. 对应原版讲义

本讲对应两份 PDF。

**（1）设计结构矩阵**

- PDF 相对路径：`90-原始PDF/15-214/slides/dsms.pdf`
- 总页数：27 页
- 重点页码：
  - 第 1 页：封面（"Design Analysis: Design Structure Matrices"，署名 Jonathan Aldrich，引用 Sullivan/Griswold/Cai/Hallen FSE 2001 与 Baldwin & Clark *Design Rules*）
  - 第 2 页：模块依赖的问题陈述（理想 vs 现实，传播取决于耦合）
  - 第 3 页：Hadoop 中的设计依赖（Rick Kazman 供图）
  - 第 4 页：DSM 的定义（N×N、行依赖列、对角线忽略）
  - 第 5 页：最小 DSM 例子（Model / GUI）
  - 第 6 页：全连接 DSM
  - 第 7 页：全独立 DSM
  - 第 8 页：分层架构 DSM（Kernel + Ring 1–4）
  - 第 9 页：严格分层架构 DSM（OS/VM/I-O lib/Middleware/App）
  - 第 10 页：术语（层次依赖、相互依赖、独立）
  - 第 11 页：聚类与「真模块」判据
  - 第 12 页：分层模块 DSM（A–E）
  - 第 13 页：接口实体化（B→A 变成 A→I、B→I）
  - 第 14 页：模块化的价值（信息隐藏 → 降低维护成本与上市时间）
  - 第 15–16 页：KWIC 设计 #1 的 DSM（含「数据格式不稳定」批注）
  - 第 17–18 页：KWIC 设计 #2 的 DSM（含 Line Type/Data/Alg）
  - 第 19–20 页：两种设计的并排对比与定量结论（每模块 2–4 依赖 vs 1–2 依赖）
  - 第 21 页：EDSM 的引入（环境变化作为参数）
  - 第 22–23 页：变化对设计 #1 的影响（级联传播）
  - 第 24–25 页：变化对设计 #2 的影响（局部化）
  - 第 26 页：Comparison（原文写 "Design 1 hides information better"，疑为笔误）
  - 第 27 页：总结与延伸（Baldwin & Clark、Sullivan & Griswold、Lattix LDM）
- 原始网页链接：`https://www.cs.cmu.edu/~aldrich/214/slides/dsms.pdf`

**（2）GUI 入门**

- PDF 相对路径：`90-原始PDF/15-214/slides/gui-intro.pdf`
- 总页数：34 页
- 重点页码：
  - 第 1 页：封面（Fall 2013；版权署名 Jeffrey Eppinger、Jonathan Aldrich、Charlie Garrod、Christian Kaestner、William Scherlis）
  - 第 2–3 页：GUI 与命令行的区别、"Don't call us, we'll call you!"
  - 第 4 页：事件驱动编程的定义与三个 `performAction` 并列
  - 第 5 页：Setup phase / Execution phase 与框架-OS-应用时序图
  - 第 6 页：GUI 伪代码（应用侧 vs 框架侧，"main() exits"）
  - 第 7 页：RabbitWorld 例子（`WorldUI.main()`、`WorldPanel.paintComponent()`）
  - 第 8 页：Java GUI 框架谱系（AWT/Swing/SWT+JFace/其他）
  - 第 9 页：Swing 类层次直觉（JFrame/JPanel/JButton/JTextField）
  - 第 10 页：创建 Swing 应用的六步
  - 第 11 页：常用组件清单
  - 第 12 页：`JFrame` vs `JPanel`
  - 第 13 页：布局管理器（含 Oracle 教程链接）
  - 第 14–15 页：「Find the pattern…」→ Strategy
  - 第 16 页：RabbitWorld 的布局代码（BorderLayout + SOUTH 按钮面板）
  - 第 17–18 页：如何让按钮工作（事件、Listener、注册）
  - 第 19 页：Observer 模式完整 UML 与适用性/后果
  - 第 20 页：Swing 监听器家族清单
  - 第 21 页：`ActionListener` 与 `event.getSource()`
  - 第 22 页：RabbitWorld 的 run/step 按钮（匿名内部类、禁用 step 按钮、toggle flag）
  - 第 23 页：匿名内部类语法
  - 第 24–25 页：匿名内部类只能访问 final 局部变量（错误版 + 修正版）
  - 第 26 页：组织技巧（组件声明为字段、动作放进私有辅助方法）
  - 第 27–28 页：接口 vs 继承（为什么 `JPanel` 用继承、`ActionListener` 用接口）
  - 第 29–30 页：MVC 三方职责、passive model vs active model
  - 第 31 页：RabbitWorld 到 MVC 的映射（含「Delegating to the view (is this design ideal?)」）
  - 第 32 页：「Find That Pattern!」五个复习提问（讲义未给答案）
  - 第 33 页：延伸资料（Oracle Swing 教程、*Introduction to Programming Using Java* Ch.6）
  - 第 34 页：Questions?
- 原始网页链接：`https://www.cs.cmu.edu/~aldrich/214/slides/gui-intro.pdf`

> 待核实：`dsms.pdf` 第 1 页引用 "K.J. Sullivan, W.G. Griswold, Y. Cai, and B. Hallen. The Structure and Value of Modularity in Software Design. Foundations of Software Engineering, 2001."——第 21 页则写作 "Sullivan et al., ESEC/FSE 2001"，同一篇论文的会议名称有两种写法（FSE 2001 与 ESEC/FSE 2001 实为同一会议的不同称谓，2001 年起合并为 ESEC/FSE）。`gui-intro.pdf` 第 13 页的布局管理器图示为图片，文本层只保留了少量文字（"The simplest, and default, layout." / "Wraps around when out of space." / "Like FlowLayout, but no wrapping" / "More sophisticated layout managers"），具体每个布局管理器对应哪段描述需对照原图确认；笔记按文字顺序对应 `FlowLayout`、`BorderLayout` 与「更复杂的布局管理器」处理。第 32 页五个模式问题讲义未给答案。

## 9. 对应视频

未找到官方公开录像。2013 年秋季的 15-214 课堂没有公开发布录像，故不提供链接与时间戳。

## 10. 本节复习

- DSM：N×N 矩阵，行列同为模块，**row A column B 的 X 表示 A 依赖 B**，对角线忽略。
- 四种形态：全连接（最坏）、全独立（理想但不可能）、分层（依赖所有内层，O(n)）、严格分层（只依赖相邻下层，O(1)）。
- 术语：层次依赖（B→A，暗示先实现 A）、相互依赖（B↔C，必须一起处理）、独立（C 与 A）。
- 聚类 = proto-module；**真模块要求簇外无 X**。
- 接口实体化：把 1 条 B→A 变成 2 条 A→I、B→I。依赖条数增加，但**穿透深度下降**——这是「解耦」的准确含义。
- KWIC 设计 #1 的模块通过**共享数据结构**通信（每模块 2–4 条依赖），而数据结构最不稳定；设计 #2 通过**抽象接口**通信（每模块 1–2 条依赖），接口稳定。
- EDSM 把「环境变化」作为矩阵行，用来检验两个问题：哪些**接口**受影响（理想：无）、哪些**实现**受影响（理想：局部）。
- DSM 可以从代码自动导出（Lattix LDM），所以它也是遗留系统架构体检的工具。
- GUI 的本质：**事件驱动 + 好莱坞法则**。`main()` 创建窗口后退出，框架的 GUI 线程循环「取事件 → 找窗口 → 调你的回调 → 绘图」。
- Swing 六步：`JFrame` → `JPanel` → 加组件 + 布局 + 监听器 → 显示 → 等事件。
- 布局管理器 = **Strategy**；`addActionListener` = **Observer**；`paintComponent` = **Template Method**；容器嵌套 = **Composite**。
- 匿名内部类只能捕获 **final / effectively final** 的局部变量（因为捕获的是拷贝）。
- `JPanel` 用继承（is-a、需要 `super()`、绘制不变），`ActionListener` 用接口（非 is-a、单向解耦、动作可变）。
- MVC：Controller 管输入、View 管显示、Model 管领域数据。passive model 不知道视图，改完模型要**手动**刷新；active model 主动通知（Observer）。
- RabbitWorld：`WorldImpl`（Model，passive）、`WorldUI`（Controller）、`WorldPanel`（View，`step()` 里改模型 + `repaint()`）。

## 11. 自我检查

1. 下面是一个 4 模块系统的 DSM。请指出：哪些模块对是相互依赖的？如果要排出实现顺序，应该从哪里开始？哪个模块最可能是「god class」？

   ```
            A    B    C    D
   A        O    X    X    X
   B             O    X
   C                  O
   D        X         X    O
   ```

2. 课件第 13 页说「接口把依赖实体化，从而解耦 A 与 B」，但依赖条数从 1 条变成了 2 条。请解释为什么这仍然算「解耦」，并用 KWIC 设计 #1 与 #2 的依赖数对比（每模块 2–4 条 vs 1–2 条）说明「依赖条数」与「耦合强度」为什么不是一回事。

3. EDSM 相比 DSM 多了什么？它回答的两个问题分别是什么？为什么说它把「信息隐藏」从一个**假说**变成了**可检验的预测**？

4. GUI 的 `main()` 在创建窗口后就退出了，那么程序是靠什么活着的？请描述框架侧的循环做了哪四件事，并解释这与 Template Method 的「好莱坞法则」有什么共同点。

5. 下面的代码有两个问题（一个编译错误、一个设计问题）。请指出并修正：

   ```java
   public static void main(String[] args) {
       int count = 0;
       JButton b = new JButton("Click");
       b.addActionListener(new ActionListener() {
           public void actionPerformed(ActionEvent e) {
               count++;
               System.out.println("clicked " + count);
           }
       });
   }
   ```

<details>
<summary>参考答案</summary>

1. **相互依赖**：`A ↔ D`（A 行 D 列有 X，D 行 A 列也有 X），以及 `A ↔ B`（A 行 B 列有 X，B 行 A 列……注意 B 行 A 列是空的，所以 `A → B` 单向）、`A ↔ C`（A 行 C 列有 X，C 行 A 列空，单向）。仔细读：
   - A 行：B、C、D 都有 X → **A 依赖 B、C、D**；
   - B 行：C 有 X → **B 依赖 C**；
   - C 行：无 X → **C 不依赖任何模块**；
   - D 行：A、C 有 X → **D 依赖 A、C**。
   所以**唯一的相互依赖是 A ↔ D**（A 依赖 D，D 依赖 A）。B 与 C 之间是单向（B→C），A→B 也是单向。
   **实现顺序**：应从**不依赖任何模块**的模块开始，即 `C`（它的行全空）。实现 C 后可以删除 C 的行列，此时 `B` 不再有依赖，可接着实现 B；然后 A 只剩 D 一个依赖……但 A 与 D 互相依赖，**无法拓扑排序**——必须先打破这个环（抽出一个接口，把 A→D 或 D→A 中的一条改成两者都依赖接口），才能继续。
   **最可能的 god class**：`A`。它依赖三个模块（B、C、D），是依赖数最多的；同时又被 `D` 依赖。高扇出（fan-out）+ 被依赖，通常意味着它在协调一切，内聚容易崩。这也是第 11 讲「Few incohesive, bloated classes do all the work」的形态。

2. **因为「解耦」衡量的是依赖的穿透深度，不是依赖的条数。**
   - 直接依赖 B→A 时，B 能看到 A 的**全部**：公开方法、返回类型、异常、甚至（通过返回的可变对象）内部数据结构。A 的任何实现变化都可能波及 B。
   - 引入接口 I 后，A→I 与 B→I 两条依赖都只指向 **I 的签名**——这是一组**稳定的、被明确承诺的**决策。A 的实现怎么改、换成哪个类，B 都感知不到。
   所以：依赖条数 1→2（变差），但每条依赖的「信息含量」与「变化敏感度」大幅下降（变好）。这正是第 11 讲 Meyer 的 Few Interfaces（边数少）与 Small Interfaces（每条边信息少）为什么是两条独立规则——接口化用 Few 换 Small 与 Explicit。
   **KWIC 的对比印证了这一点**：设计 #1 每模块 2–4 条依赖，设计 #2 每模块 1–2 条——设计 #2 的条数**更少**。但更关键的不是条数，而是**依赖的对象性质**：设计 #1 依赖的是**数据结构**（`Lines`、`Shifts`），课件第 16 页批注明确说 "problematic because data formats are unstable"；设计 #2 依赖的是**抽象接口**（`getChar`/`setChar`），第 18 页批注是 "Dependence on interfaces"。第 20 页的四条结论把差别说全了：依赖数更少、接口更抽象（不限制算法）、接口在可能的变化面前更稳定。

3. **EDSM 多了「环境变化」作为矩阵的行**（`V - Input Fmt`、`W - Store Mem`、`X - Compress`、`Y - Shift Store`、`Z - Amortize`），因此矩阵从「模块×模块」变成「变化×模块」+「模块×模块」。
   它回答的两个问题（第 21 页原文）：
   - **What interfaces are affected?** → 信息隐藏的要求是「接口应当稳定」（理想答案：没有接口受影响）；
   - **What implementations are affected?** → 信息隐藏的假说是「应当局限在一个模块内」（理想答案：只有一个模块受影响）。
   **为什么说它把假说变成了可检验的预测**：信息隐藏的核心主张是「如果你能预判哪些决策会变，把它们藏起来，那么变化发生时代价更小」。这个主张里有一个**未经检验的前提**——「你预判的那些决策真的会变」。DSM 本身无法检验它，因为它只记录「现在谁依赖谁」。EDSM 把「变化」显式列出来，于是你可以**逐条检查**：这个变化发生时，X 落在几个模块上？如果落在很多模块上，说明信息隐藏失败了（假说被推翻）；如果落在一个模块内、接口列全空，说明假说成立。第 23 页与第 25 页的对比就是这个检验的结果：设计 #1 的 X 铺满大半张表（假说失败），设计 #2 的 X 集中在 Line Storage 三列（假说成立）。这也解释了第 21 页那句 "Only partially controlled by designer"——变化本身不完全由设计者控制，所以必须把它当作**环境参数**而不是设计变量。

4. **程序靠框架的 GUI 线程活着。** 第 6 页的框架侧伪代码给出四步循环：
   - **Asks OS for event**（向操作系统要事件）；
   - **Finds application window that event relates to**（找到事件对应的应用窗口）；
   - **Asks application window to handle event**（请求应用窗口处理该事件——这就是调用你的回调）；
   - **Draws lines/text on behalf of application**（代表应用绘制线条与文字）。
   另外循环开始前还有一步：**Starts the GUI thread**。所以 `main()` 退出只是**主线程**结束，GUI 线程（EDT）继续运行，程序不会终止。
   **与 Template Method 的共同点**：两者都是「**控制权在框架手里**」。Template Method 里，抽象父类的 `draw()` 定义了「先 `doDraw()` 再 `doUpdate()`」的骨架，子类只填钩子；GUI 里，框架的循环定义了「取事件 → 分发 → 绘制」的骨架，应用只填 `actionPerformed` / `paintComponent` 这些钩子。两者都体现了第 9 讲第 8 页的好莱坞法则 **"don't call us, we'll call you"**——你的代码不是主动去调用框架的流程，而是被框架在合适的时机调用。这也是「**依赖倒置**」的一种表现：应用依赖框架的**稳定接口**（`ActionListener`、`paintComponent`），而框架不需要知道具体是哪个应用。

5. **编译错误**：`count` 是非 final 的局部变量，被匿名内部类捕获 → 编译期错误（"local variables referenced from an inner class must be final or effectively final"）。因为 `count++` 修改了它，所以它连 effectively final 都不是。
   **设计问题**：即使把 `count` 改成字段（或用 `int[] count = {0}` 之类的 hack 绕过），**计数状态放在监听器外部/局部**也是错的——GUI 的状态应当由**模型**持有，而不是散落在事件处理器里。这违反 MVC，也让「显示」与「状态」无法分别测试。此外 `System.out.println` 作为「显示」意味着界面更新绕过了视图，用户在窗口里看不到任何反馈。
   **修正**（引入一个最小 Model）：

   ```java
   static final class CounterModel {
       private int count = 0;
       int getCount() { return count; }
       void increment() { count++; }
   }

   public static void main(String[] args) {
       final CounterModel model = new CounterModel();     // final：可被内部类捕获
       JButton b = new JButton("Click");
       JLabel label = new JLabel("clicked 0");
       b.addActionListener(new ActionListener() {
           public void actionPerformed(ActionEvent e) {
               model.increment();                          // 改模型
               label.setText("clicked " + model.getCount()); // 更新视图
           }
       });
   }
   ```

   若计数需要跨多个视图共享或被持久化，应改用 **active model**：`CounterModel` 维护监听器列表，`increment()` 里 `notify` 所有观察者，视图自己订阅——这样就不需要每个控制器都记得手动刷新（对应第 31 页 passive model 的「易漏」风险）。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-11-Design-Principles-GRASP]]
- 下一讲：[[15-214-13-GUIs-Continued]]
- 课程总览：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]
- 课程目录：[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸：Carliss Baldwin & Kim Clark, *Design Rules: The Power of Modularity*（MIT Press）——用**真实期权**理论解释模块化的经济价值，是本讲 DSM 背后的理论；Kevin Sullivan et al., "The Structure and Value of Modularity in Software Design," ESEC/FSE 2001——EDSM 的原始论文；Oracle Swing 官方教程 `http://download.oracle.com/javase/tutorial/uiswing/`（讲义第 33 页推荐）；David Eck, *Introduction to Programming Using Java* 第 6 章 `http://math.hws.edu/javanotes/c6/index.html`。下一讲 [[15-214-13-GUIs-Continued]] 会继续深入 GUI 的结构问题。
