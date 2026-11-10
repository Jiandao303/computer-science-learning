---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L01
topic: Course Introduction and Organization
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 课程导论
  - 软件构造
  - Java
---

# 第 1 讲 课程导论与课程组织（Course Introduction and Organization）

> 说明：15-214 的公开课程网页是 **2013 年秋季学期（Fall 2013）** 的历史存档版本，本笔记按该版本整理，可能与 CMU 现行 15-214 的内容、作业和评分方式有较大差异。

## 1. 本节学习目标

- 能用自己的话说出 15-214 与 15-122 的区别：从「写程序（programs）」转向「构造系统（systems）」，核心矛盾是**管理复杂度**。
- 能列举课程的四大主题（线程与并发、面向对象编程、分析与建模、设计），并各举一个例子说明它解决什么问题。
- 能解释对象（Object）由「状态（state）+ 行为（behavior）」构成，类（Class）是同类对象的模板，方法调用等价于向对象「发消息（message）」。
- 能根据课程组织信息判断：本课的先修要求、评分构成、迟交政策、需要安装的工具链。
- 能说明为什么「程序规模从 KLOC 增长到 MLOC」会带来质变，而不是简单地把小程序设计放大。

## 2. 前置知识

- 前序课程：15-122（Imperative Computation，命令式计算）。本讲默认你已经会用 C 族语言写中等规模程序、理解基本算法与数据结构。
- 外部概念：编译器与运行时（本课用 Java）、版本控制（Git）、集成开发环境（Eclipse）。
- 本讲是整门课的第一讲，没有前置笔记。后续讲次见 [[15-214-02-Objects-Encapsulation-Polymorphism]]。

## 3. 核心概念

- **Scale（规模）**：课件用「KLOC → MLOC」表示代码量从千行级增长到百万行级。规模变化带来的不是「同样的事做更多遍」，而是**新的失效模式**：编译时间、团队协作、外部 I/O、网络、异步、库与框架的边界都会成为一等公民。
- **Software Complexity（软件复杂度）**：本课的总主题。课件把它拆成四个维度：代码规模、外部环境（worldly environment：I/O、网络、异步）、软件基础设施（库、框架、组件）、软件演化（随时间变化）。
- **Object-Oriented Programming（面向对象编程，OOP）**：以「概念/事物」为中心自底向上组织代码，而不是以「操作步骤」为中心自顶向下展开。
- **Object（对象）**：一个把状态（数据）与行为（操作）打包在一起的单位。字段（field）保存数据，方法（method）描述对该数据的操作。
- **Class（类）**：一族相似对象的模板。课件用「某一个具体的按钮（对象）」与「按钮这一类东西（类）」作对比。
- **Message（消息）**：方法调用的另一种说法。调用 `s.contains(0)` 可以理解成「向对象 s 发送一条 contains 消息，附带参数 0」。
- **Encapsulation（封装）**：对象像一个通过受管接口访问的服务，外部只能看到接口，看不到内部表示。课件给出的最佳实践是「不要让字段从外部可见」。
- **Concurrency（并发）**：多个控制流在时间上重叠地推进。课件强调本课关注的是**应用级并发**（application-level concurrency），与 15-210 的函数式并行、15-213 的系统级并发不同。
- **Analysis and Modeling（分析与建模）**：用实用的规格说明技术与验证工具，为「所有可能的执行」建立信心，尤其是多线程和库的正确使用这类难以靠测试覆盖的场景。
- **Design（设计）**：提出并评估多种方案，关注模块化（modularity）、信息隐藏（information hiding）、为变化做准备（planning for change），以及模式（patterns）——对反复出现的设计问题的成熟解法。

## 4. 通俗理解

把写软件比作盖楼：

- 15-122 教你**砌墙**：砖怎么摆、灰怎么抹，单面墙要直、要稳。
- 15-214 教你**造一座会持续扩建二十年的城市**：哪面墙属于谁的产权（封装）、不同楼之间怎么共用一套水电标准（接口）、城市要新增一种建筑时怎么不改动已有管网（开闭原则的雏形）、以及几千个工地同时开工时怎么不互相撞车（并发）。

一个具体数字：课件引用的经验曲线是「代码量每增长一个数量级，缺陷密度不会自动下降，而沟通成本按人数平方增长」。10 万行（100 KLOC）的代码库，如果有 20 个开发者，两两沟通渠道就有 `20 × 19 / 2 = 190` 条；这就是为什么「把小程序写对」和「把系统构造对」是两类问题。

再举课件里的两个动机例子：

- **GraphLayout**（Java 官方 applet 示例）：一个把图画出来并支持拖拽的图形布局程序。它同时涉及 GUI 组织、对象设计（节点、边、布局算法如何分工）以及事件响应中的并发。
- **Virtual Worlds（虚拟世界/多人在线游戏）**：要支撑上千用户，必须回答「如何组织系统才能方便地加入新种类的物体」「如何利用相似性支持不同种类的物体」——这正是继承与多态的动机。

## 5. 原理与推导

### 5.1 为什么规模会改变问题性质

课件第 9 页把「从小程序到系统」的跃迁拆成四条，逐条解释：

1. **代码规模（KLOC → MLOC）**：一个人能在大脑里装下的代码量大约是一个模块；百万行代码必须靠接口、文档、测试来「外部化」记忆。于是**接口设计**成为主要工作，写实现反而变得次要。
2. **外部环境（worldly environment）**：小程序是「输入 → 计算 → 输出」的封闭函数；真实系统要读文件、发网络请求、等待用户点击。这些操作**不确定何时返回**，因此引入了异步（asynchrony）与并发。
3. **软件基础设施（software infrastructure）**：你写的代码大部分不是自己从零写的，而是调用库（library）与框架（framework）。课件把「从零写算法与数据结构」和「复用库与框架」列为两种不同的能力。
4. **软件演化（software evolution）**：系统会存在很多年，需求会变。设计的价值在于让**变化被局部化**（localized）——改一个概念只需要改一处代码。

课件第 10 页给出一张对照表，把「程序」与「系统」逐项对比：

| 维度 | 程序（Programs） | 系统（Systems） |
|---|---|---|
| 代码来源 | 从零写算法与数据结构 | 复用库与框架 |
| 结构 | 函数：输入与输出 | 异步与响应式设计（asynchronous and reactive designs） |
| 执行 | 顺序的、局部的计算 | 并行与分布式计算 |
| 规格 | 完整的函数式规格 | 部分的、可组合的、有针对性的模型 |

表格最后一行最关键：系统无法写出「完整规格」，只能写出**部分规格（partial specification）**，并让它可组合。这是后续「契约」「框架条件」等概念的伏笔。

### 5.2 四大主题为什么是这四块

课件第 12 页给出四个主题，并说明各自的必要性：

- **Threads and Concurrency（线程与并发）**：并发是重要的系统抽象（例如后台计算的同时仍能响应用户），也是性能的必要条件（多核处理器与分布式计算）。本课聚焦应用级并发。
- **Object-Oriented Programming（面向对象编程）**：支持灵活设计与可复用代码，是工业界的主流范式，也是现代框架的基础。本课用 Java。
- **Analysis and Modeling（分析与建模）**：实用的规格技术与验证工具，应对多线程、正确使用库等挑战。
- **Design（设计）**：提出并评估替代方案；模块化、信息隐藏、为变化做规划；模式。

用两个动机例子把这四块串起来（课件第 17 页）：

- 图形界面程序里，GUI 线程与计算线程需要并发 → **并发**。
- 游戏里有玩家、怪物、道具等大量相似但不同的东西 → **面向对象**。
- 「如何对所有可能的执行都有信心」→ **分析与建模**。
- 「如何组织会增长、会演化的系统」「如何定义基础设施与我们自己代码之间的接口」→ **设计**。

### 5.3 对象模型的最小白话推导

课件第 22 页从「C 的结构体」推导出对象：

1. 结构体（struct）把多个数据字段打包成一个整体 → 这就是**状态**。
2. 但如果只有数据，任何外部代码都能直接改字段，无法保证数据始终合法。
3. 于是给数据配上一组**函数**（方法），这些函数能访问全部字段，外部只能通过函数间接读写 → 这就是**行为 + 封装**。
4. 方法调用需要知道「对谁操作」，因此有一个隐式参数 `this`（接收者，receiver）。调用写成 `obj.m(args)`，读作「向 obj 发送消息 m」。
5. 既然方法控制了字段访问，就可以「只暴露该暴露的」，从而在将来替换内部表示而不影响调用者。

课件第 24–26 页用 Point/Rectangle 演示了这个模型：

```java
class Point {
    int x, y;
    int getX() { return x; }
    Point(int px, int py) { x = px; y = py; }  // 构造函数
}
class Rectangle {
    Point origin;
    int width, height;
    Point getOrigin() { return origin; }
    int getWidth() { return width; }
    void draw() { /* 画四条边 */ }
    Rectangle(Point o, int w, int h) { origin = o; width = w; height = h; }
}
```

客户端代码 `Point o = new Point(0, 10); Rectangle r = new Rectangle(o, 5, 10); r.draw();` 的执行要点：

- `new` 做两件事：在**堆（heap）**上分配内存，然后调用构造函数初始化。
- 局部变量 `o`、`r` 里存放的是**引用（reference）**，不是对象本身。
- `r.getOrigin().getX() + r.getWidth()` 的结果是 `0 + 5 = 5`，这要求两次方法调用各自返回正确类型，链式调用才能通过类型检查。

### 5.4 课程组织：把「契约」用在课程本身上

课件（01b 第 2–3 页）罕见地用契约语言描述课程：

- **Preconditions（前置条件）**：15-122 或等价课程；两学期编程经验；了解 C 族语言；具备基本编程技能、基本程序推理、基本算法与数据结构。
- **Postconditions（后置条件）**：掌握 OO 概念与技能（对象、类、类型、Java 开发）；掌握开发较大规模软件的工具（设计方法与模式、库与框架的设计与使用）；建模与分析（开发、测试、分析工具）；并发与分布式系统（扩展性与性能、显式并发的安全编程实践）。

这种写法本身就是本课的教学内容：**用契约思考任何接口，包括一门课**。

课程运行细节：

| 项目 | 内容 |
|---|---|
| 讲师 | Jonathan Aldrich（aldrich@cs.cmu.edu）、Charlie Garrod（charlie@cs.cmu.edu） |
| 上课 | 周二、周四 15:00–16:20，DH 2315 |
| Recitation | 六个 section A–F，均为周三，**必须出席** |
| 助教 | Beth Anne Katz (A)、Alex Lockwood (B)、Bailey Forrest (C)、Shannon Lee (D)、Mat Gray (E)、Dan Lu (F) |
| 网站 | 课程页（schedule、作业、slides、政策文件） |
| 工具 | Git（分发/提交/评分）、Piazza（讨论）、Eclipse（推荐 IDE） |
| 评分 | 作业 60%、期中 15%、期末 20%、参与 5%（可能调整） |
| 教材 | Shalloway & Trott,《Design Patterns Explained》第 2 版；另有若干免费在线 Java 教材 |
| 迟交 | 全学期共 5 个 late day；双人作业另有 2 个；超出预算每天扣 10%；单次作业最多用 2 天；超过 2 天不收（极端情况除外） |

Recitation 具体时间（课件 01b 第 4 页）：A 周三 9:30–10:20 GHC 4211；B 周三 10:30–11:20 WEH 5310；C 周三 11:30–12:20 WEH 5310；D 周三 12:30–13:20 BH 235B；E 周三 9:30–10:20pm PH A20；F 周三 15:30–16:20 PH 226C。

> 待核实：section E 的时间在提取文本中写作「Weds 9:30-10:20pm」，与其它 section 的上午时段差异很大，可能是排版或提取错误。

## 6. 代码示例

### 6.1 官方课程代码

以下代码出自 `01a-intro.pdf` 第 24–25 页（Point 与 Rectangle 的对象模型示例，逐字保留结构，省略号为原文所有）：

```java
class Point {
    int x, y;
    int getX() { return this.x; }        // 显式写 this
    Point(int px, int py) { this.x = px; this.y = py; }
}
class Rectangle {
    Point origin;
    int width, height;
    Point getOrigin() { return this.origin; }
    int getWidth() { return this.width; }
    void draw() {
        this.drawLine(this.origin.getX(), this.origin.getY(),   // 第一条边
                      this.origin.getX() + this.width, this.origin.getY());
        // … 其余三条边
    }
    Rectangle(Point o, int w, int h) {
        this.origin = o; this.width = w; this.height = h;
    }
}
```

客户端（同页）：

```java
Point o = new Point(0, 10);       // 分配内存并调用构造函数
Rectangle r = new Rectangle(o, 5, 10);
r.draw();
int rightEnd = r.getOrigin().getX() + r.getWidth();   // 5
```

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

下面用「银行账户」演示同一套对象模型，并显式对比「字段公开」与「字段私有」两种写法的后果：

```java
// 版本 1：字段公开 —— 外部可以随意破坏内部一致性
class BadAccount {
    public double balance;                       // 谁都能量接改
    public void deposit(double amt) { balance += amt; }
}

// 版本 2：字段私有 + 公开方法 —— 只有方法能改状态
class Account {
    private double balance = 0.0;                // 外部看不见
    public double getBalance() { return balance; }
    public void deposit(double amt) {
        if (amt <= 0) throw new IllegalArgumentException("amount must be positive");
        balance += amt;                          // 所有修改都经过这里，可加检查
    }
}

public class Demo {
    public static void main(String[] args) {
        BadAccount b = new BadAccount();
        b.balance = -1000;                       // 编译通过：状态被直接破坏
        Account a = new Account();
        a.deposit(-5);                           // 运行期被拒绝：不变量守住了
    }
}
```

要点：两个版本编译后都能「跑起来」，区别在于**谁能保证「余额永远等于所有交易之和」这条不变量**。版本 1 把不变量交给了所有调用者，版本 2 把它收回类内部——这就是第 3 讲要展开的封装原则。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| Program（程序） | System（系统） | 程序是可以写出完整规格的封闭计算；系统只有部分、可组合的规格，且必须面对 I/O、并发、演化 |
| Object（对象） | Class（类） | 对象是堆上一个具体实例（「这个按钮」）；类是模板（「按钮这一类」），描述同类对象共有的字段与方法 |
| 方法调用 | 函数调用 | 方法调用隐含一个接收者 `this`，且具体执行哪个实现由运行时类型决定（动态分派）；普通函数调用在编译期就确定 |
| 应用级并发（本课） | 系统级并发（15-213）/ 函数式并行（15-210） | 本课关心「如何在应用逻辑里正确使用线程与锁」；15-213 关心 OS/硬件层机制；15-210 关心可并行的算法 |
| 复杂度（本课含义） | 算法复杂度（Big-O） | 课件明确说算法复杂度「不是本课重点」；本课指的是软件系统规模带来的工程复杂度 |

## 8. 对应原版讲义

- PDF 相对路径：
  - `90-原始PDF/15-214/slides/01a-intro.pdf`（27 页）
  - `90-原始PDF/15-214/slides/01b-orga.pdf`（8 页）
- 本节重点页码：
  - `01a-intro.pdf`：第 9–10 页（KLOC→MLOC、程序 vs 系统对照表）、第 12 页（四大主题）、第 13–17 页（GraphLayout 与 Virtual Worlds 两个动机例子）、第 21 页（OO 历史：Simula 67、SmallTalk-76）、第 22 页（对象 = 状态 + 行为）、第 24–26 页（Point/Rectangle 与内存模型）、第 27 页（take-home messages）。
  - `01b-orga.pdf`：第 2–3 页（课程前置/后置条件）、第 4 页（讲师、助教、时间地点）、第 6–7 页（评分、教材、迟交政策）。
- 原始网页链接：
  - `https://www.cs.cmu.edu/~aldrich/214/slides/01a-intro.pdf`
  - `https://www.cs.cmu.edu/~aldrich/214/slides/01b-orga.pdf`
- > 待核实：`01a-intro.pdf` 第 1 页与第 18 页页脚标注为「Fall 2012」，与课程实际学期（Fall 2013）不一致，推测是沿用旧版封面未改；`01b-orga.pdf` 第 1 页版权行为「© 2012-2013」。

## 9. 对应视频

未找到官方公开录像。2013 年版本的 15-214 没有公开的完整授课视频；网络上流传的相关视频多为其它学期或非官方录制，无法确认与本讲义逐页对应，故不提供链接，也不编造时间戳。

## 10. 本节复习

- 15-214 的一句话主题：**管理复杂度，从程序走向系统**。
- 复杂度来自四个方向：代码规模、外部环境（I/O/网络/异步）、软件基础设施（库/框架）、软件演化。
- 四大主题：线程与并发、面向对象编程、分析与建模、设计。
- 对象 = 状态（字段）+ 行为（方法）；类 = 一族相似对象的模板；方法调用 = 向对象发消息。
- 封装的第一条实践：字段不要对外可见，所有访问经由方法。
- 系统只能写出**部分、可组合**的规格，这是后续契约与框架条件讨论的起点。
- 课程本身也用契约描述：先修是前置条件，学完应达到的能力是后置条件。

## 11. 自我检查

1. 课件说「算法复杂度不是本课重点」。那么本课所谓的「复杂度」具体指什么？请至少写出三个来源，并各举一个 15-122 里不会遇到、但 15-214 必须面对的例子。
2. 如果把 `Rectangle` 的 `origin`、`width`、`height` 都改成 `public`，程序仍然能编译运行。请说明这会破坏哪条「不变量」，并给出一个具体的破坏场景。
3. 为什么课件说系统只能有「部分规格（partial specification）」？请用 GraphLayout 或虚拟世界举例说明「完整规格」为什么写不出来。
4. 用自己的话解释：为什么「对象」这个概念比「结构体 + 一组自由函数」更适合应对需求变化？

<details>
<summary>参考答案</summary>

1. 三个来源：(a) **代码规模**——百万行代码无法靠个人记忆维护，必须靠接口与文档外部化，15-122 的作业规模不会触发这个问题；(b) **外部环境**——网络请求、磁盘 I/O、用户点击的返回时间不确定，15-122 的程序是封闭的「输入→计算→输出」；(c) **软件演化**——系统寿命长、需求变化，需要让改动局部化。第四个可答「基础设施」：必须正确使用他人写的库与框架，而不是从零实现。

2. 破坏的不变量是「矩形的四条边闭合，且 width/height 非负」。具体场景：外部代码执行 `r.width = -5;`，随后 `draw()` 用 `origin.getX() + width` 计算右边界，得到比左边界更小的坐标，画出反向或异常的图形；又如外部把 `origin` 指向 `null`，`draw()` 立即抛 `NullPointerException`。这类错误在编译期完全查不出来。

3. 因为系统的行为依赖外部世界：GraphLayout 的最终画面取决于用户拖拽的顺序与时机、窗口系统的重绘请求；虚拟世界里成千上万客户端的消息到达顺序不确定。这些「所有可能的执行」是指数级的，无法用一个完整的输入→输出函数描述。可行的做法是写出**部分规格**：例如「无论顺序如何，任何一个节点都不会同时出现在两个位置」，再让这些局部性质可组合成整体保证。

4. 结构体 + 自由函数把「数据布局」暴露给了所有调用者，任何需求变化（例如把 `int x, y` 改成极坐标 `r, theta`）都会波及全部调用点。对象把表示藏在方法后面，调用者只依赖方法签名（接口），因此内部表示可以整体替换而调用者无需改动；同时「同类对象」可以被统一对待（多态），新增一种对象不需要修改已有代码。

</details>

## 12. 进一步学习

- 下一讲：[[15-214-02-Objects-Encapsulation-Polymorphism]]
- 课程总览：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]
- 课程目录：[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 建议延伸阅读：Josh Bloch《Effective Java》中关于「最小化可访问性」的条目（对应第 3 讲的封装原则）；Shalloway & Trott《Design Patterns Explained》第 1–2 章（对应第 7 讲的设计模式导论）。
