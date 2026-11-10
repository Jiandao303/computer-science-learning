---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L13
topic: GUIs Continued - Threading, Responsiveness and SwingWorker
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - GUI
  - Swing
  - 线程
  - EDT
  - SwingWorker
  - 响应性
  - MVC
  - 关注点分离
---

# 第 13 讲 GUI 进阶：线程、响应性与 SwingWorker

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。本讲对应 `guis-continued.pdf`（15 页），页码标注为讲义内部的第 26–40 页（说明它是上一份 `gui-intro.pdf` 讲义的直接延续）。讲义前半段（第 32–39 页）与 `gui-intro.pdf` 第 26–33 页内容**几乎完全重复**，真正新增的只有三页：Homework Hint（第 26 页）、GUIDemo 例子（第 27 页）、以及 GUI 线程架构的三页图解（第 28–31 页）。本笔记把重复部分压缩复习，把新增部分讲透。

## 1. 本节学习目标

- 能说明「UI 类应当承担全部用户交互，其他类不碰用户交互」这条设计约束的理由，并能识别违反它的代码。
- 能画出 GUI 的双线程架构：`main()` 线程（创建后结束）与 GUI 线程（永久循环）。
- 能解释为什么「在回调里做耗时计算」会让界面失去响应，并说明这不是性能问题而是**架构**问题。
- 能写出 `SwingWorker` 的三段式用法（`doInBackground` / `done` / `get`），并说明每一段运行在哪个线程上。
- 能说明为什么 `done()` 里可以安全地更新界面，而 `doInBackground()` 里不行。
- 能复述「继承 `JPanel` vs 实现 `ActionListener`」的三条判据。
- 能说明 passive model 与 active model 的差别，以及它如何决定「谁负责刷新界面」。

## 2. 前置知识

- [[15-214-12-DSM-and-GUIs]]：Swing 六步、布局管理器、监听器、MVC、passive/active model——本讲前半是它的复习，后半是它的深入。
- [[15-214-09-Design-Patterns-Continued]]：Template Method、好莱坞法则——GUI 线程循环与 `paintComponent` 都靠它。
- [[15-214-07-Design-Patterns]]：Observer 模式——`ActionListener` 的本质。
- 并发基础概念：线程、主线程与工作线程、共享可变状态（正式内容在本课程后续并发部分展开，本讲只用到最直观的部分）。

## 3. 核心概念

- **GUI 线程（GUI Thread / EDT, Event Dispatch Thread）**：唯一负责取事件、调回调、绘制的线程。
- **`main()` 线程**：只负责创建窗口、注册回调、显示窗口，然后**结束**。
- **工作线程（Worker Thread）**：由 `SwingWorker` 创建，负责执行耗时计算。
- **响应性（Responsiveness）**：界面能在合理时间内对用户操作作出反应的能力。
- **`SwingWorker<T, V>`**：Swing 提供的后台任务类，`T` 是最终结果类型，`V` 是中间进度类型。
- **`doInBackground()`**：在**工作线程**上运行，做耗时计算。
- **`done()`**：在**GUI 线程**上运行，读取结果并更新界面。
- **`get()`**：取出计算结果；在 `done()` 里调用是安全的，因为它此时已完成。
- **UI 类（imaginary）**：作业提示中的虚构类，承载**全部**用户交互，其他类完全不碰 UI。
- **passive model / active model**：模型是否持有视图引用、是否主动通知（复习自第 12 讲）。

## 4. 通俗理解

**为什么界面会「卡住」？** 你在窗口里点了一个按钮，程序开始算第 40 个斐波那契数，算了五秒。这五秒里窗口拖不动、按钮点不动、连关闭都不响应。很多人的第一反应是「我的算法太慢了」——但这句话不准确。算法慢只是**原因之一**，真正让界面**冻结**的是：**计算发生在那个唯一能处理界面事件的线程上**。

这就是第 12 讲第 6 页伪代码里那句「This thread loops: 向 OS 要事件 → 找窗口 → 调你的回调 → 绘制」的后果。这个循环是**串行**的：你的回调没返回，循环就无法进入下一轮，新的鼠标点击就排在队列里没人处理。于是界面看起来「死了」。

所以这**不是**一个「优化算法」的问题，而是一个**架构**问题：**耗时的工作必须离开 GUI 线程**。课件给的方案是 `SwingWorker`。

**为什么讲这个要放在设计课里？** 因为它是「关注点分离」在**线程维度**上的又一次体现。第 12 讲讲了「数据 / 显示 / 输入」三方分离（MVC）；本讲加上第四个维度：「**耗时计算**」也要分离出去。而且这种分离不是靠「注意一下」就能做到的——它需要**具体的机制**（`SwingWorker` 的回调约定），否则你会不小心在错误的地方更新界面，引发更难查的 bug。

## 5. 原理与推导

### 5.1 Homework Hint：UI 类是一道防火墙

`guis-continued.pdf` 第 1 页（讲义第 26 页）是一张只有文字标注的图，标题「Homework Hint!」。它的结构是：

```
┌─────────────────────────┐        ┌─────────────────────────┐
│  UI Class (imaginary)   │        │   Other Classes (real)  │
│                         │        │                         │
│  All user interaction   │        │  No user interaction    │
│  goes here—and nothing  │        │  here—all game and      │
│  else!                  │        │  player state here      │
└─────────────────────────┘        └─────────────────────────┘
              │                                  ▲
              └────── Only make calls this way ──┘
```

三个标注值得逐字读：

> - **UI Class (imaginary)**：**All user interaction goes here—and nothing else!**
> - **Other Classes (real)**：**No user interaction here—all game and player state here**
> - **Only make calls this way!**（箭头从 UI 类指向其他类，单向）

三个要点：

**（1）「imaginary」这个词很关键。** UI 类被标为「虚构的」，意思是它**不对应领域模型中的任何概念**。领域模型里的 `Rabbit`、`Fox`、`World` 都是「真实」的概念；而 `WorldUI`、`WorldPanel` 纯粹是为了和用户打交道而存在的技术产物。这正是第 11 讲 GRASP 中 **Pure Fabrication（纯虚构）** 原则的实例——为了高内聚低耦合，虚构一个不对应领域概念的类。

**（2）「and nothing else!」是硬约束。** UI 类里**只能**有用户交互代码：读控件状态、更新显示、注册监听器。不能有游戏规则、不能有寻路算法、不能有「兔子繁殖概率」这种领域逻辑。理由：UI 代码**几乎无法单元测试**（需要构造事件、需要真实窗口），一旦领域逻辑混进去，那部分逻辑就失去了自动化测试的保护。第 8 讲说过「可测试代码」的价值，这里是它在架构层面的体现。

**（3）「Only make calls this way!」是单向依赖。** 箭头只有一个方向：UI → 其他类。反方向（领域类持有 UI 引用、调用 `showMessage()`、弹对话框）是**禁止**的。理由：

- 领域类一旦依赖 UI，就**无法脱离界面运行**（不能跑批处理、不能写测试、不能换界面）；
- 这正是第 12 讲 DSM 里会出现 `Domain ↔ UI` **相互依赖**的情形，两个模块从此无法分开理解；
- 这也是 MVC 中 **passive model** 的定义：模型不持有视图引用。

这个提示与作业（hw2 Virtual World）直接相关：学生很容易在 `Rabbit` 里写 `System.out.println` 或持有 `WorldUI` 引用来「方便调试」，然后发现无法测试。

### 5.2 GUIDemo：一个刻意制造问题的例子

第 2 页（讲义第 27 页）：

> **GUIDemo Example**
> - Shows how to construct a basic UI
> - **Illustrates an interesting UI responsiveness issue**

课件明确说这个例子的目的**不是**教你怎么写 UI（那是上一讲的事），而是**制造一个 bug 让你看见**。这是一个很好的教学手法：先让你体验症状，再给诊断，最后给处方。

从第 3、5、6 页的流程图可以推断出例子的形态：界面上有一个按钮，点击后**在回调里同步计算斐波那契数**，算完把结果显示出来。斐波那契（递归版）是一个完美的「耗时计算」道具：代码只有三行，耗时随 n 指数增长，而且没有任何 I/O 或共享状态干扰——**卡顿的唯一原因就是计算本身**。

### 5.3 GUI 的双线程架构

第 3 页（讲义第 28 页）给出完整图景：

> **The GUI Threading Architecture**
>
> **main() thread**
> - Create window
> - Set up callbacks
> - Show window
> - **(thread ends)**
>
> **GUI Thread**
> - **Loop forever:**
>   - Get system event
>   - Invoke callback
>
> **Callback code:**
> - Compute fibonacci
> - **(UI is unresponsive)**
> - Show result

把它画成时间线更清楚：

```
main() thread:  [创建窗口][注册回调][显示窗口] ✗ 结束
                                              │
GUI thread:     ──────────────────────────────┴──→ 无限循环
                  ┌──────────────────────────────────┐
                  │ 取事件 → 调回调 → 绘制 → 取事件…│
                  └──────────────────────────────────┘
                              │
                    回调里：compute fibonacci（5 秒）
                              │
                    这 5 秒内循环停在这里 → 界面冻结
```

**关键洞察**：`main()` 线程**结束了**（第 12 讲第 6 页已强调过 "main() exits"），所以整个程序只剩下**一个** GUI 线程在跑。这个线程既是「事件泵」又是「绘图器」还是「你的回调执行者」。它是**单线程**的——这意味着：

| 性质 | 后果 |
|---|---|
| 单线程串行执行回调 | 一个回调不返回，所有后续事件都排队 |
| 同一线程负责绘制 | 计算期间无法重绘，窗口被遮挡后不会恢复 |
| 系统判定「无响应」 | 长时间不处理事件，操作系统会标记窗口「未响应」 |
| 状态访问天然安全 | 因为只有一个线程碰 UI，所以不需要锁——这是**好处** |

最后一条很重要：Swing 的单线程模型虽然带来响应性问题，但它**消除了 UI 的竞态条件**。这是 Swing 的**设计决策**：宁可要求你把耗时工作挪走，也不要让你在多个线程里同步 UI 状态。这与第 6 讲「不可变对象天然线程安全」是同一类思路——**用结构约束替代事后同步**。

### 5.4 为什么不能在回调里做耗时计算

把症状、诊断、处方列成表：

| 层次 | 内容 |
|---|---|
| **症状** | 点击按钮后窗口冻结数秒；拖动无效；关闭按钮无反应；窗口被其他窗口遮挡后留下空白 |
| **直接原因** | 回调在 GUI 线程上同步执行，循环无法进入下一轮 |
| **根本原因** | 耗时计算与事件处理**共享同一个线程**——关注点未分离 |
| **错误处方** | 优化算法（可能有效但治标：换个更慢的操作又复现） |
| **正确处方** | 把计算**移出** GUI 线程，用回调把结果送回来 |

「错误处方」这一栏值得强调：如果学生把斐波那契从递归改成迭代，卡顿消失了，于是以为问题解决了。但只要下次操作是「读一个大文件」或「发一个网络请求」，卡顿会原样回来。**优化算法降低的是常数，架构缺陷依然存在。**

### 5.5 SwingWorker 的三段式

第 4 页（讲义第 29 页）只有一行：

> **GUIDemo Example**
> - **A fix: `SwingWorker`**

接下来两页（第 30、31 页）用两张流程图把 `SwingWorker` 的生命周期画清楚。

**第 5 页（讲义第 30 页）——启动阶段**：

> **GUI thread**
> - Create window / Set up callbacks / Show window
> - Loop forever: Get system event / **Invoke callback**
>
> **Callback code:**
> - **create `SwingWorker`**
> - **start it executing**
>
> **Worker thread**
> - **Worker thread execution:**
>   - invoke `doInBackground()`
>   - **compute fibonacci**
>   - **store result in `SwingWorker`**
>   - **signal to UI that we are done**
>
> （图中标注 `SwingWorker` 有一个字段 `result : Long`）

**第 6 页（讲义第 31 页）——完成阶段**：

> **GUI thread**
> - Loop forever: Get system event / Invoke callback
> - **Invoke `SwingWorker.done()`**
>   - **`get()` result from `SwingWorker`**
>   - **show result in the UI**
>
> **Worker thread**：`doInBackground()` … store result … **signal to UI that we are done**

把两页合起来，就是完整的三段式：

```
① GUI 线程（回调内）      ② 工作线程                ③ GUI 线程（done）
   new SwingWorker  ──→     doInBackground()   ──→    done()
   .execute()                 compute fibonacci        get() 取结果
   （立刻返回）                store result             show result in UI
                              signal done
```

**三个方法各自运行在哪个线程上**，这是本讲最容易记混、也最必须记清的知识点：

| 方法 | 运行线程 | 典型内容 | 能否碰 UI |
|---|---|---|---|
| `doInBackground()` | **工作线程** | 耗时计算、I/O、网络 | **不能** |
| `done()` | **GUI 线程** | 取结果、更新控件、`repaint()` | **能**（且只有这里能） |
| `get()` | 调用它的线程 | 取结果（会阻塞直到完成） | — |
| `publish()` / `process()` | `publish` 在工作线程，`process` 在 GUI 线程 | 中间进度 | `process` 能 |

为什么 `done()` 能碰 UI？因为**框架保证它在 GUI 线程上被调用**。这就是「signal to UI that we are done」这句话的实现方式：工作线程不直接调用 `done()`，而是通过 `SwingUtilities.invokeLater` 之类的机制把 `done()` 投递到 GUI 线程的事件队列里。**SwingWorker 把这个繁琐的线程切换封装起来了**——这正是它作为框架的价值。

为什么 `doInBackground()` 不能碰 UI？因为它在另一个线程上，而 Swing 组件**不是线程安全的**。两个线程同时改一个 `JLabel` 的文本，可能让内部状态不一致（比如文本已更新但布局缓存还是旧的）。Swing 的单线程模型就是靠「只有 GUI 线程碰组件」这条纪律维持的。

### 5.6 为什么在 done() 里 get() 是安全的

第 6 页明确写「`get()` result from `SwingWorker`」发生在 **`done()` 内部**（GUI 线程）。这里有个潜在的疑虑：`get()` 是一个**阻塞**方法，在 GUI 线程上阻塞不是又会冻结界面吗？

答案是**不会**，原因是时序：`done()` 被调用的**前提**就是 `doInBackground()` 已经返回、结果已经写入 `result` 字段。所以此时 `get()` 会立即返回，不会阻塞。

但如果**在回调里**（而不是 `done()` 里）调用 `get()`，就会**再次冻结界面**——因为那时计算还没完成，`get()` 会一直等到它完成。这是一个非常容易犯的错误：以为「用了 SwingWorker 就万事大吉」，结果在回调里写了 `worker.execute(); label.setText(worker.get());`——等于什么都没改。

**判据**：`get()` 只应出现在 `done()` 里（或明确知道任务已完成的地方）。若需要在任务进行中获取进度，应使用 `publish()`/`process()` 而不是 `get()`。

### 5.7 SwingWorker 的代码形态

讲义没有给出 `SwingWorker` 的完整代码（只有流程图），此处按 Java 的 API 约定补出形态（属笔记补充，见 6.2 节标注）。

`SwingWorker<T, V>` 是**抽象类**（不是接口），所以用法是**匿名子类 + 覆写钩子**：

```java
SwingWorker<Long, Void> worker = new SwingWorker<Long, Void>() {
    @Override
    protected Long doInBackground() {      // 工作线程
        return fibonacci(n);               // 耗时计算，返回值即结果
    }
    @Override
    protected void done() {                // GUI 线程
        try {
            label.setText("fib(" + n + ") = " + get());
        } catch (Exception ex) { ... }
    }
};
worker.execute();                          // 启动，立即返回
```

注意三点：

1. **`SwingWorker` 是抽象类而非接口**——这与第 12 讲第 28 页「`ActionListener` 用接口」形成对照。为什么？因为 `SwingWorker` 需要**提供大量已有实现**（线程管理、状态机、`done()` 的投递机制），子类只需要填 `doInBackground` 与 `done` 两个钩子。这是**模板方法模式**的典型形态：父类定义骨架（启动线程 → 调 `doInBackground` → 存结果 → 投递 `done`），子类只填可变部分。这也解释了第 12 讲第 28 页那条判据「子类需要回调父类（`super`）/ 行为骨架固定」为什么倾向继承。
2. **`doInBackground()` 有返回值**（`T`），框架自动存进 `result` 字段（正是第 5 页图中标注的 `result : Long`），`done()` 里用 `get()` 取。
3. **`get()` 抛受检异常**（`InterruptedException`、`ExecutionException`），所以 `done()` 里必须 `try-catch`——这是第 5 讲「受检异常迫使你处理」的实例。

`SwingWorker` 的泛型参数：`T` 是最终结果类型，`V` 是 `publish`/`process` 传递的中间进度类型。本例不需要进度，所以 `V` 写 `Void`。

### 5.8 复习：组织技巧与「接口 vs 继承」

第 7–9 页（讲义第 32–34 页）与 `gui-intro.pdf` 第 26–28 页**逐字相同**，此处只做要点回顾（详细推导见 [[15-214-12-DSM-and-GUIs]] 5.14 节）。

第 7 页：

> - **Declare references to components you'll be manipulating as instance variables**
> - **Put the code that performs the actions in private "helper" methods.** (Keeps things neat)

第二条在**本讲的语境下**多了一层意义：把动作放进私有辅助方法，不仅让代码整洁，还让**耗时计算可以被单独识别**——你一眼就能看出「这个方法要跑五秒」，从而知道它该不该被挪进 `SwingWorker`。如果所有逻辑都塞在 `actionPerformed` 里，你很难判断哪一段是慢的。

第 8–9 页的「接口 vs 继承」三条判据（复习）：

| 判据 | 继承 `JPanel` | 实现 `ActionListener` |
|---|---|---|
| 是否 is-a | 是（是一种特殊的 Panel） | 否（不是一种特殊的 Button） |
| 是否回调父类 | 是（用 `super()` 绘制背景） | 否（被调用后不再碰 Button） |
| 行为是否运行时变化 | 否（绘制方式固定） | 是（可能要换动作） |
| 结论 | **继承** | **独立对象 + 接口** |

### 5.9 复习：MVC 与 RabbitWorld

第 10–12 页（讲义第 34–37 页）同样与 `gui-intro.pdf` 第 29–31 页重复。要点：

**MVC 三方**（第 10 页）：

> - **Controller**：Manage inputs from user: mouse, keyboard, menu, etc.
> - **View**：Manage display of information on the screen
> - **Model**：Manage data related to the application domain

**两种模型**（第 11 页）：passive model / active model。

**RabbitWorld 映射**（第 12 页）：

> - `...hw2.lib.ui.WorldImpl` —— **The Model class**，**Model is passive: does not have a reference to the view**
> - `...hw2.lib.ui.WorldUI` —— **The Controller class**，Listener callbacks in constructor react to events，**Delegating to the view (is this design ideal?)**
> - `...hw2.lib.ui.WorldPanel` —— **The View class**，Gets data from Model to find out where to draw rabbits, foxes, etc.，Implements stepping (in `step()`)：Invokes model to update world / **Invokes `repaint()` on self to update UI**

**本讲新增的关联**：passive model 与 GUI 线程有一个隐含的配合关系。因为模型是被动的（不通知），所以**控制器在改完模型后必须记得 `repaint()`**；而 `repaint()` 本身**不立即绘制**——它只是**请求**重绘，把绘制任务排进 GUI 线程的事件队列。所以：

- 如果你在 GUI 线程上调用 `repaint()`，绘制会在当前回调返回后发生（正常）；
- 如果你在**工作线程**上调用 `repaint()`，虽然 `repaint()` 本身是少数线程安全的方法之一，但**在此之前你对组件状态的修改**（如 `label.setText`）是不安全的；
- 所以 `SwingWorker.done()` 之所以存在，就是为了给你一个「在 GUI 线程上安全地改完状态再 `repaint()`」的时机。

这条链条把「MVC 的刷新责任」与「线程模型的切换点」串起来了——这是本讲真正的综合点。

### 5.10 「Find That Pattern!」与延伸资料

第 13 页（讲义第 38 页）与 `gui-intro.pdf` 第 32 页相同，五个提问：

> - What pattern is **`BorderLayout`** a part of?
> - What pattern is **`JPanel`** a part of?
> - What pattern are the **`ActionListener`s** part of?
> - There are classes representing the AI's decision to **Eat, Breed, or Move**. What pattern are these representing?
> - Look at the documentation for **`JComponent.paint()`**. What pattern is used?

答案（依据第 7、9 讲推导，讲义未给）：Strategy、Composite、Observer、Command、Template Method。详见 [[15-214-12-DSM-and-GUIs]] 5.15 节。

**本讲可以追加第六问**：`SwingWorker` 是什么模式？——**Template Method**。父类 `SwingWorker` 定义了完整流程（创建线程 → 调 `doInBackground()` → 存结果 → 投递 `done()`），子类只覆写 `doInBackground()` 与 `done()` 两个钩子。这与 `JComponent.paint()` 是同一个模式的两个实例，而且**都体现了好莱坞法则**：「不要调用我们，我们会调用你」——你的代码不主动驱动流程，而是被框架在合适的时机调用。

第 14 页（讲义第 39 页）延伸资料与上一讲相同：

> - Oracle's Swing tutorials：`http://download.oracle.com/javase/tutorial/uiswing/`
> - *Introduction to Programming Using Java*, Ch. 6：`http://math.hws.edu/javanotes/c6/index.html`

### 5.11 把三讲串起来：GUI 的四层分离

到本讲为止，GUI 部分（第 12–13 讲）其实在讲同一件事的四次重复：**分离**。

| 层次 | 分离什么 | 机制 | 出处 |
|---|---|---|---|
| **1. 数据 / 显示 / 输入** | 领域状态、屏幕呈现、用户操作 | MVC 三个角色 | 第 12 讲第 29–31 页 |
| **2. UI 代码 / 领域代码** | 用户交互、游戏与玩家状态 | 「UI Class (imaginary)」防火墙 + 单向调用 | 本讲第 26 页 |
| **3. 骨架 / 变体** | 固定流程、可变行为 | Template Method（`paintComponent`、`SwingWorker`） | 第 12 讲第 32 页、本讲第 30–31 页 |
| **4. 耗时计算 / 事件处理** | 后台工作、界面响应 | `SwingWorker` + 线程切换 | 本讲第 28–31 页 |

四层分离的共同理由是第 11 讲 Meyer 的 **Modular Continuity**（小变化只动一个模块）与 **Modular Protection**（故障局限在模块内）：GUI 卡顿不该影响领域逻辑，领域逻辑变化不该影响显示，反之亦然。

而它们的共同代价也一样：**多了一层间接**。多一个类、多一次转发、多一个回调——第 9 讲讲 Strategy 时说的「Adds objects and dynamism, code harder to understand」在这里同样成立。**分离不是免费的，它买的是可演进性。**

## 6. 代码示例

### 6.1 官方课程代码

`guis-continued.pdf` **没有包含任何 Java 源代码**——它是一份以流程图和标注为主的讲义。第 5、6 页（讲义第 30、31 页）用流程图描述了 `SwingWorker` 的执行路径，其中出现的「代码」只有方法名与字段名：

```
Callback code:
  create SwingWorker
  start it executing

Worker thread execution:
  invoke doInBackground()
  compute fibonacci
  store result in SwingWorker
  signal to UI that we are done

GUI thread:
  Invoke SwingWorker.done()
  get() result from SwingWorker
  show result in the UI

SwingWorker
  result : Long
```

以及第 7 页（讲义第 32 页）的伪代码式建议：

```
Declare references to components you'll be manipulating as instance variables
Put the code that performs the actions in private "helper" methods.
```

第 1 页（讲义第 26 页）的设计约束以图的形式给出：

```
UI Class (imaginary)          Other Classes (real)
All user interaction          No user interaction here—
goes here—and nothing else!   all game and player state here
        └──────── Only make calls this way! ────────┘
```

> 说明：讲义中的 `GUIDemo` 示例代码在课堂上现场演示（第 2、4 页写着 "GUIDemo Example"、"Let's look at the code"式的指引），但**未随 slides 公开发布**，故本笔记无法引用其原文。

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：错误的写法——在回调里做耗时计算**

```java
// 反例：界面会冻结
JButton btn = new JButton("fib(40)");
JLabel out = new JLabel("—");

btn.addActionListener(new ActionListener() {
    public void actionPerformed(ActionEvent e) {
        long r = fibonacci(40);              // 在 GUI 线程上跑数秒
        out.setText("fib(40) = " + r);       // 计算完成后才更新
    }
});

// 朴素递归，n=40 时约十亿次调用
static long fibonacci(int n) {
    return n < 2 ? n : fibonacci(n - 1) + fibonacci(n - 2);
}
```

症状：点击后窗口完全冻结，`out` 也不会显示「计算中…」——因为**没有任何一次重绘机会**。即使你在 `fibonacci` 之前加一行 `out.setText("计算中…")`，用户也**看不到**它，因为 `setText` 只是改了组件状态，真正的绘制要等回调返回后由 GUI 线程执行。

**示例 B：正确写法——`SwingWorker`**

```java
JButton btn = new JButton("fib(40)");
JLabel out = new JLabel("—");

btn.addActionListener(new ActionListener() {
    public void actionPerformed(final ActionEvent e) {
        out.setText("计算中…");                    // 先给用户反馈
        btn.setEnabled(false);                     // 防止重复点击
        new SwingWorker<Long, Void>() {
            @Override
            protected Long doInBackground() {      // 工作线程
                return fibonacci(40);
            }
            @Override
            protected void done() {                // GUI 线程
                try {
                    out.setText("fib(40) = " + get());   // get() 此时立即返回
                } catch (InterruptedException | ExecutionException ex) {
                    out.setText("计算出错：" + ex.getCause());
                } finally {
                    btn.setEnabled(true);          // 恢复按钮
                }
            }
        }.execute();                               // 启动后立即返回
    }
});
```

与示例 A 的逐行对照：

| 关注点 | 示例 A | 示例 B |
|---|---|---|
| 计算在哪个线程 | GUI 线程 | 工作线程（`doInBackground`） |
| 回调是否立即返回 | 否（数秒后） | 是（毫秒级） |
| 界面能否响应 | 不能 | 能（可拖动、可关闭） |
| 「计算中…」是否可见 | 不可见 | 可见（回调返回后立即绘制） |
| 结果更新位置 | 回调内 | `done()` 内 |
| 重复点击防护 | 无 | `setEnabled(false)` |

注意 `final ActionEvent e` 的 `final`——虽然本例没用到 `e`，但若在匿名内部类里使用它就必须 `final`（第 12 讲第 24–25 页的作用域规则）。

**示例 C：常见错误——在回调里 `get()`**

```java
// 反例：等于没改，界面照样冻结
new SwingWorker<Long, Void>() {
    protected Long doInBackground() { return fibonacci(40); }
}.execute();

try {
    out.setText("fib(40) = " + worker.get());   // 在 GUI 线程上阻塞等待！
} catch (Exception ex) { ... }
```

`get()` 会**阻塞**直到任务完成，而它运行在 GUI 线程上——所以界面冻结的时间与示例 A 完全一样，只是多创建了一个线程。这是「用了 `SwingWorker` 但没理解它」的典型症状。判据：**`get()` 只能出现在 `done()` 里**。

**示例 D：带进度的 `SwingWorker`（`publish` / `process`）**

```java
new SwingWorker<Long, Integer>() {          // T = Long（结果），V = Integer（进度）
    @Override
    protected Long doInBackground() {
        long a = 0, b = 1;
        for (int i = 0; i < 40; i++) {
            long t = a + b; a = b; b = t;
            publish(i);                      // 工作线程 → 投递给 process
        }
        return a;
    }
    @Override
    protected void process(java.util.List<Integer> chunks) {   // GUI 线程
        progressBar.setValue(chunks.get(chunks.size() - 1));
    }
    @Override
    protected void done() {                  // GUI 线程
        try { out.setText("结果 = " + get()); }
        catch (Exception ex) { out.setText("出错"); }
    }
}.execute();
```

`publish` 在**工作线程**上调用，`process` 在 **GUI 线程**上被调用，中间由框架合并与投递。这解决了「计算过程中也要更新界面」的需求——而且**不需要你自己写任何线程同步代码**。

**示例 E：把「UI 类是一道防火墙」落到实处**

```java
// ---- 领域类：完全不知道 UI 存在 ----
public final class World {
    private final List<Rabbit> rabbits = new ArrayList<>();
    public void step() {                       // 纯领域逻辑，可单元测试
        for (Rabbit r : rabbits) r.act();
        rabbits.removeIf(Rabbit::isDead);
    }
    public List<Rabbit> rabbits() { return List.copyOf(rabbits); }
}

// ---- UI 类：只有用户交互，没有任何领域规则 ----
public final class WorldPanel extends JPanel {
    private final World world;                 // 单向：UI 依赖领域
    WorldPanel(World world) { this.world = world; }

    @Override
    protected void paintComponent(Graphics g) {
        super.paintComponent(g);
        for (Rabbit r : world.rabbits())       // 只读取状态来画
            g.fillOval(r.x(), r.y(), 8, 8);
    }

    void onStepClicked() {                     // 只做「协调」，不含规则
        world.step();                          // 调领域
        repaint();                             // 请求重绘（passive model 的刷新责任）
    }
}
```

反例（违反防火墙）：

```java
// 反例 1：领域类里弹对话框
public final class Rabbit {
    void act() {
        if (energy <= 0) {
            JOptionPane.showMessageDialog(null, "兔子饿死了！");  // 领域依赖 UI！
        }
    }
}

// 反例 2：UI 类里写领域规则
public final class WorldPanel extends JPanel {
    void onStepClicked() {
        for (Rabbit r : world.rabbits()) {
            if (r.energy() > 50 && Math.random() < 0.3) r.breed();  // 繁殖规则在 UI 里！
        }
        repaint();
    }
}
```

反例 1 的后果：`Rabbit` 无法在无界面环境下测试（会弹真窗口），也无法在服务器端复用。反例 2 的后果：繁殖规则无法被单元测试覆盖（它藏在 `onStepClicked` 里，需要构造 `WorldPanel` 才能调用），而且换一个界面就要重写一遍。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| **`main()` 线程** | **GUI 线程** | 前者只做三件事（建窗口、注册回调、显示）然后**结束**；后者**永久循环**（取事件 → 调回调 → 绘制）。程序活着靠后者 |
| **GUI 线程** | **工作线程** | 前者是唯一能碰 Swing 组件的线程；后者由 `SwingWorker` 创建，只能做计算。**跨线程直接改组件是 bug 的源头** |
| **`doInBackground()`** | **`done()`** | 前者在**工作线程**（不能碰 UI，做耗时活）；后者在 **GUI 线程**（能碰 UI，只做收尾）。这是 `SwingWorker` 唯一必须记住的一条 |
| **在 `done()` 里 `get()`** | **在回调里 `get()`** | 前者**安全**（任务已完成，立即返回）；后者**冻结界面**（阻塞等待）。判据：`get()` 只写在 `done()` 里 |
| **`SwingWorker`（抽象类）** | **`ActionListener`（接口）** | 前者要提供大量骨架实现（线程管理、`done` 投递），所以用**继承 + 覆写钩子**（Template Method）；后者只约定一个方法，且动作可变，所以用**接口 + 独立对象**。对照第 12 讲第 28 页的三条判据 |
| **`repaint()`** | **立即绘制** | `repaint()` 只是**请求**：把绘制任务排进 GUI 线程队列，回调返回后才真正执行。所以在回调里先 `setText` 再 `repaint`，用户看到的仍是最终状态（中间态不可见） |
| **响应性问题** | **性能问题** | 前者是**架构**问题（耗时工作跑错线程），换更快的算法只是治标；后者是常数因子问题。诊断方法：问「这段时间 GUI 线程在干什么」 |
| **passive model** | **active model** | 前者模型不知道视图，**控制器**负责在改完模型后 `repaint()`（易漏）；后者模型持观察者列表，变化时**主动通知**（多视图自动同步）。RabbitWorld 用的是 passive |
| **UI 类** | **领域类** | 前者是 **imaginary**（不对应领域概念，Pure Fabrication），只装用户交互；后者是 **real**，装游戏与玩家状态。依赖**单向**：UI → 领域 |
| **`SwingWorker`** | **`Thread` / `ExecutorService`** | 前者专为 Swing 设计：自动把 `done()` 投递到 GUI 线程，还能 `publish` 进度；后者需要你自己用 `SwingUtilities.invokeLater` 切线程 |
| **`publish()`** | **`process()`** | 前者在**工作线程**调用（投递进度）；后者在 **GUI 线程**被调用（处理进度）。名字相似，线程不同 |
| **单线程 UI 模型** | **多线程 UI** | Swing 选择单线程：**牺牲**并发响应性，**换来**无需同步 UI 状态。要响应性就自己把工作挪走（`SwingWorker`），而不是让多个线程碰组件 |

## 8. 对应原版讲义

- PDF 相对路径：`90-原始PDF/15-214/slides/guis-continued.pdf`
- 总页数：15 页（讲义内部页码为第 26–40 页，接续 `gui-intro.pdf` 的编号）
- 重点页码：
  - 第 1 页（讲义 26）：**Homework Hint!**——UI 类（imaginary）承载全部用户交互且「nothing else」；其他类（real）无用户交互、装全部游戏与玩家状态；只允许 UI → 其他类的单向调用
  - 第 2 页（讲义 27）：GUIDemo 例子的定位——展示基本 UI 构造 + 一个界面响应性问题
  - 第 3 页（讲义 28）：**GUI 线程架构**——`main()` 线程建窗口/注册回调/显示后结束；GUI 线程永久循环取事件调回调；回调里算斐波那契导致「UI is unresponsive」
  - 第 4 页（讲义 29）：修复方案——`SwingWorker`
  - 第 5 页（讲义 30）：修复后的架构（启动阶段）——回调里创建并启动 `SwingWorker`；工作线程执行 `doInBackground()`、计算、存结果、通知 UI；图中标注 `SwingWorker.result : Long`
  - 第 6 页（讲义 31）：修复后的架构（完成阶段）——GUI 线程调用 `SwingWorker.done()`，`get()` 取结果并显示
  - 第 7 页（讲义 32）：组织技巧——组件引用声明为实例变量；动作放进私有辅助方法
  - 第 8 页（讲义 33）：GUI 设计问题引子——接口 vs 继承、模型与视图
  - 第 9 页（讲义 34）：接口 vs 继承的三条判据（`JPanel` 用继承、`ActionListener` 用接口）
  - 第 10 页（讲义 35）：MVC 三方职责
  - 第 11 页（讲义 36）：passive model vs active model
  - 第 12 页（讲义 37）：RabbitWorld 到 MVC 的映射（`WorldImpl`/`WorldUI`/`WorldPanel`），含「Delegating to the view (is this design ideal?)」
  - 第 13 页（讲义 38）：「Find That Pattern!」五个复习提问
  - 第 14 页（讲义 39）：延伸资料（Oracle Swing 教程、*Introduction to Programming Using Java* Ch.6）
  - 第 15 页（讲义 40）：Questions?
- 原始网页链接：`https://www.cs.cmu.edu/~aldrich/214/slides/guis-continued.pdf`

> 待核实：本讲义第 1 页无标题页，直接以「Homework Hint!」开始，且页码从 26 起——说明它是 `gui-intro.pdf`（第 1–25 页）的**直接续篇**，两者在课堂上可能是同一次讲授或连续两次。第 7–14 页（讲义 32–39 页）与 `gui-intro.pdf` 第 26–33 页内容**逐字重复**，讲义本身未说明重复原因（推测为跨课时衔接时的复习）。第 2、4 页提到的 `GUIDemo` 示例源码**未随 slides 公开发布**，其具体实现（例如斐波那契的 n 值、界面布局）无法从讲义确认。第 1 页的图仅以文字标注形式存在于 PDF 文本层，原图的连线与箭头方向（「Only make calls this way!」具体指向哪一侧）需对照 PDF 原图核对；笔记按「UI → 其他类」单向理解，依据是第 12 讲 MVC 的 passive model 与「Model is passive: does not have a reference to the view」。

## 9. 对应视频

未找到官方公开录像。2013 年秋季的 15-214 课堂没有公开发布录像，故不提供链接与时间戳。

## 10. 本节复习

- **UI 类是一道防火墙**：全部用户交互都在 UI 类里，且**只有**用户交互；领域类完全不碰 UI；依赖**单向**（UI → 领域）。
- 「imaginary」= Pure Fabrication：UI 类不对应任何领域概念。
- **双线程架构**：`main()` 线程建窗口、注册回调、显示，然后**结束**；GUI 线程**永久循环**「取事件 → 调回调 → 绘制」。
- 在回调里做耗时计算 → 循环停住 → 界面冻结。这是**架构**问题，不是性能问题；优化算法只是治标。
- Swing 选**单线程 UI 模型**：牺牲并发响应性，换来「无需同步 UI 状态」。
- `SwingWorker` 三段式：回调里 `new` + `execute()`（立即返回）→ 工作线程跑 `doInBackground()` → GUI 线程跑 `done()`。
- **线程归属**：`doInBackground`/`publish` 在工作线程；`done`/`process` 在 GUI 线程。只有后者能碰组件。
- `get()` 只应写在 `done()` 里（此时任务已完成，立即返回）；写在回调里会阻塞 GUI 线程，等于没修。
- `SwingWorker` 是**抽象类**（Template Method）：父类定流程，子类填 `doInBackground` 与 `done` 两个钩子。
- 改完模型要 `repaint()`（passive model 的刷新责任）；`repaint()` 只是**请求**，回调返回后才真正绘制。
- 接口 vs 继承三条判据：is-a？需要 `super()` 回调？行为运行时变化？
- MVC：Controller 管输入、View 管显示、Model 管领域数据；passive model 不知道视图。
- GUI 的四层分离：MVC（数据/显示/输入）、UI 防火墙（交互/领域）、Template Method（骨架/变体）、`SwingWorker`（耗时/响应）。

## 11. 自我检查

1. 为什么在 `actionPerformed` 里调用 `fibonacci(40)` 会让窗口冻结？请从「GUI 线程在做什么」的角度解释，并说明为什么「把递归改成迭代」不是正确的修复。

2. 下面三段代码分别运行在哪个线程上？哪些可以安全地更新 `JLabel`？
   ```java
   new SwingWorker<String, Void>() {
       protected String doInBackground() { return load(); }        // ①
       protected void process(List<Void> c) { ... }                // ②
       protected void done() { label.setText(get()); }             // ③
   }.execute();
   ```

3. 下面这段「修复」为什么没有效果？请指出问题所在并改写。
   ```java
   btn.addActionListener(e -> {
       SwingWorker<Long, Void> w = new SwingWorker<Long, Void>() {
           protected Long doInBackground() { return fibonacci(40); }
       };
       w.execute();
       try { out.setText("结果 = " + w.get()); } catch (Exception ex) { }
   });
   ```

4. 为什么 `SwingWorker` 被设计成**抽象类**而不是接口，而 `ActionListener` 被设计成**接口**？请用第 12 讲第 28 页的三条判据分析。

5. 下面的 `Rabbit` 类违反了本讲「UI 类是一道防火墙」的哪条约束？会造成什么具体后果？请给出修正方向。
   ```java
   public class Rabbit {
       private int energy;
       public void act() {
           energy -= 5;
           if (energy <= 0) {
               JOptionPane.showMessageDialog(null, "一只兔子饿死了");
           }
       }
   }
   ```

<details>
<summary>参考答案</summary>

1. **因为 GUI 线程被你的回调占住了。** GUI 线程是**唯一**的线程，它在一个永久循环里做四件事：向 OS 要事件、找到对应窗口、调用你的回调、绘制。这个循环是**串行**的——`actionPerformed` 不返回，循环就无法进入下一轮。于是：新的鼠标点击排在队列里没人取；`repaint()` 请求排在队列里没人执行（所以窗口被遮挡后不会恢复）；系统检测到窗口长时间不处理事件，标记为「未响应」。用户感知就是「卡住了」。
   **「改成迭代」不是正确修复**，因为它是**治标**：它只是把这个特定计算的常数因子降下来。架构缺陷依然存在——只要下次操作是读大文件、发网络请求、或者用户输入一个更大的 n，冻结会原样复现。正确的修复是**把耗时工作移出 GUI 线程**（用 `SwingWorker`），让 GUI 线程始终能回到循环里处理事件。判据：不要问「这个算法能不能更快」，要问「**这段时间 GUI 线程在干什么**」。

2. - **① `doInBackground()`：工作线程**（`SwingWorker` 自己创建的）。**不能**更新 `JLabel`——Swing 组件不是线程安全的。
   - **② `process()`：GUI 线程**。可以更新组件（框架负责把调用投递到 GUI 线程）。
   - **③ `done()`：GUI 线程**。可以更新组件，这也是它存在的目的。
   所以 **② 和 ③ 安全，① 不安全**。补充：① 里也不能调用 `publish()` 之外任何会碰组件的方法；若要在 ① 里报告进度，只能用 `publish()`（它在工作线程调用，但只是投递数据，不碰组件）。

3. **问题：`w.get()` 在 GUI 线程（回调内）上被调用，而任务还没完成。** `get()` 是阻塞方法，会一直等到 `doInBackground()` 返回。于是 GUI 线程被阻塞的时间与「直接在回调里算」**完全一样**——界面照样冻结，只是白白多创建了一个线程。这是「用了 `SwingWorker` 但没理解它」的典型症状。
   判据：**`get()` 只能出现在 `done()` 里**，因为那时任务必然已完成，`get()` 立即返回。
   改写：
   ```java
   btn.addActionListener(e -> {
       out.setText("计算中…");
       btn.setEnabled(false);
       new SwingWorker<Long, Void>() {
           @Override protected Long doInBackground() { return fibonacci(40); }
           @Override protected void done() {
               try { out.setText("结果 = " + get()); }
               catch (InterruptedException | ExecutionException ex) { out.setText("出错"); }
               finally { btn.setEnabled(true); }
           }
       }.execute();
   });
   ```
   注意 `done()` 里必须 `try-catch`——`get()` 抛 `InterruptedException` 与 `ExecutionException` 两个**受检异常**（第 5 讲：受检异常迫使调用者处理）。

4. 用第 12 讲第 28 页的三条判据逐条分析：
   **`SwingWorker` 用抽象类（继承）**：
   - **需要父类提供大量骨架实现**：`SwingWorker` 必须自己实现线程创建与启动、结果字段的存储、`done()` 到 GUI 线程的投递、`publish`/`process` 的合并与转发、状态机（pending → started → done）。这些都不是「一个方法签名」能表达的，接口无法携带。所以必须是**类**（且是抽象类，因为 `doInBackground` 必须由子类提供）。
   - **子类需要回调父类**：`done()` 里调 `get()` 就是在用父类的字段与方法；`doInBackground` 的返回值由父类接管存入 `result`。子类与父类**密切交互**。
   - **骨架在运行时不变**：`SwingWorker` 的执行流程（启动 → 后台 → 存结果 → 投递 done）是**固定**的，只有两个钩子的内容可变。这正是 **Template Method** 的形态。
   **`ActionListener` 用接口（独立对象）**：
   - **不是 is-a**：一个「动作」不是一种「按钮」。
   - **不需要回调父类**：监听器被调用后不再碰按钮（单向解耦）。
   - **行为可能运行时变化**：同一个按钮可能在不同状态下执行不同动作，所以监听器应当是**可替换的独立对象**。
   一句话总结：**「骨架固定 + 需要大量实现」→ 抽象类；「只约定一个方法 + 行为可变」→ 接口**。二者都是「优先组合」原则的合理例外或体现，关键是要能**论证**。

5. **违反的约束**：「Other Classes (real) — No user interaction here」。`Rabbit` 是**领域类**（real），却直接调用了 `JOptionPane.showMessageDialog`——这是一次**用户交互**，而且方向是**领域 → UI**，恰好是「Only make calls this way!」禁止的反方向。
   **具体后果**：
   - **无法单元测试**：`rabbit.act()` 会弹出真实窗口，测试会阻塞或需要人工点击；无法在 CI 中自动运行。
   - **无法脱离界面运行**：想在服务器端跑批量模拟（比如统计一千次模拟的平均存活时间）时，会弹出一千个对话框。
   - **无法换界面**：改成 Web 或命令行界面时，`Rabbit` 里的 `JOptionPane` 必须删掉重写——领域逻辑被迫随界面变化而变化，违反第 11 讲的 Modular Continuity。
   - **无法在国际化/无头（headless）环境中运行**：`java.awt.HeadlessException`。
   **修正方向**：把「通知」变成**领域层的中立事件**，由 UI 层决定怎么呈现。
   ```java
   // 领域层：只记录「发生了什么」，不知道如何显示
   public final class Rabbit {
       private int energy;
       private boolean justDied = false;
       public void act() {
           energy -= 5;
           if (energy <= 0) justDied = true;      // 只置标志，不弹窗
       }
       public boolean hasJustDied() { return justDied; }
   }

   // UI 层：自己决定怎么呈现（对话框 / 日志 / 声音 / 什么都不做）
   void onStepClicked() {
       world.step();
       for (Rabbit r : world.rabbits())
           if (r.hasJustDied()) statusLabel.setText("一只兔子饿死了");
       repaint();
   }
   ```
   更彻底的方案是让 `World` 维护一个**事件列表**（或使用 Observer，但观察者是 UI 层的对象，由 UI 注册），领域层只负责「产生事件」，UI 层负责「消费并呈现」。这就是第 12 讲 passive model 的精神：**模型不知道视图存在**。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-12-DSM-and-GUIs]]
- 下一讲：[[15-214-14-Java-Collections]]
- 课程总览：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]
- 课程目录：[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸：Oracle 官方教程中 *Concurrency in Swing* 一章（`http://download.oracle.com/javase/tutorial/uiswing/concurrency/`）系统讲了 EDT、`SwingWorker`、`invokeLater`，是讲义第 28–31 页的完整版；`SwingWorker` 的 Javadoc 对 `doInBackground`/`done`/`process`/`publish` 的线程归属有权威说明。本课程后续的并发部分会把「线程、共享可变状态、竞态条件」正式展开，届时可以回头理解为什么 Swing 选择单线程 UI 模型——那是用**结构约束**替代**事后同步**的一种设计取舍，与第 6 讲「不可变对象天然线程安全」同源。
