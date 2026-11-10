---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L07
topic: Introduction to Design and Patterns
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 设计模式
  - Composite
  - 模板方法
  - 设计过程
---

# 第 7 讲 设计入门与设计模式（Intro to Design and Patterns）

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。

## 1. 本节学习目标

- 能按「需求 → 名词/动词 → 领域模型 → 软件设计」的流程，把一个简单需求整理成类图。
- 能说出设计中的四个权衡维度（可扩展性、灵活性、复用、复杂度），并解释接口与抽象类各提供哪一个。
- 能复述设计模式的四个要素（Name / Problem / Solution / Consequences）。
- 能用 Composite（组合）模式表达「整体—部分」层次，并说出它的两条代价。
- 能用 Template Method（模板方法）把「不变的骨架」与「变化的一步」分离，并解释「好莱坞原则」。
- 能区分 Façade 与 Adapter、Strategy 与 Template Method、Factory Method 与 Abstract Factory。

## 2. 前置知识

- [[15-214-06-Mutability-and-Java-Potpourri]]：接口、泛型、内部类。
- [[15-214-03-Encapsulation-and-Inheritance]]：抽象类 vs 接口、组合优于继承。
- [[15-214-02-Objects-Encapsulation-Polymorphism]]：`IntSet` 的 `EmptySet`/`SingletonSet`/`UnionSet`——本讲的 Composite 就是它的推广。
- [[15-214-04-Inheritance-Typechecking-Dispatch]]：动态分派是所有这些模式能工作的底层机制。

## 3. 核心概念

- **Domain Model（领域模型）**：用概念、属性、关系描述问题域的模型，尚未涉及实现。
- **Responsibility-Driven Design（职责驱动设计）**：每个类分配「知道什么」与「做什么」两类职责。
- **Quality Attribute（质量属性）**：不是功能需求，而是对设计的约束，如「可扩展」。
- **Design Pattern（设计模式）**：反复出现的问题与其解决方案核心的配对描述。
- **Composite（组合）**：让「单个对象」与「对象的组合」被统一对待的结构模式。
- **Template Method（模板方法）**：父类固定算法骨架，把可变的步骤留给子类实现。
- **Hollywood Principle（好莱坞原则）**：「Don't call us, we'll call you」——由框架调用你的代码，而非你调用框架。
- **Façade（外观）**：为复杂子系统提供简化接口。
- **Adapter（适配器）**：把已有类的接口转换成客户端期望的接口。
- **Strategy（策略）**：把可互换的算法封装成对象。
- **Factory Method / Abstract Factory**：把对象创建的责任延迟到子类或工厂对象。
- **Decorator（装饰器）/ Observer（观察者）/ Proxy（代理）/ Bridge（桥接）/ Singleton（单例）/ Command（命令）/ Visitor（访问者）**。

## 4. 通俗理解

**设计模式**就像木工里的「榫卯类型」。课件第 9–11 页用了一个极好的类比：

> 木匠 A：这些抽屉怎么做？
> 木匠 B：先直着切下去，然后 45 度退回来，再直着切下去，再 45 度退回来……
>
> 木匠 A：我们是做**燕尾榫**还是**斜接榫**？

第二种对话的效率高得多，因为「燕尾榫」「斜接榫」这两个词**自带全部信息**：斜接榫便宜、看不出接缝、容易裂；燕尾榫贵、好看、结实。一个词就压缩了「怎么做 + 代价是什么」。

课件把这个类比直接映射到软件：

| 木工对话 | 软件对话 |
|---|---|
| 「用燕尾榫还是斜接榫？」 | 「这里该用 Composite 吗？」 |
| 潜台词：贵/便宜、结实/易裂 | 潜台词：有整体—部分关系吗？统一对待组合与个体有好处吗？ |

所以模式的第一个价值不是「代码模板」，而是**词汇**：它把一大段设计推理压缩成一个可讨论的名字。

## 5. 原理与推导

### 5.1 设计过程：从需求到类图（讲义 notes 第 1–2 页）

讲义笔记（`07-design-pattern-notes.pdf`）给了一个完整的「画图编辑器」设计演练，需求如下：

- **R1**：能创建一幅图和图中的图形（figure）
- **R2**：每个图形在图中有一个可移动的位置
- **R3**：把图显示在屏幕上
- **R4**：支持多种图形，包括直线与矩形
- **R5**：图形的种类应当**可扩展**
- **R6**（第 2 页补充）：把小图形组合成大图形，并把大组当作一个图形来操作

**第一步：找名词与动词。**

| 类别 | 结果 |
|---|---|
| 名词 | drawing, figure, position, screen, line, rectangle |
| 动词 | create, move, display |

课件给了一条判断准则：**如果你在现实世界里会把它想成一段文字或一个数字，它多半是属性（attribute）；如果它有更复杂的结构或性质，它多半是概念（concept）。** 领域模型中，概念画成类，属性画成字段。

所以 `position` 是属性（两个数字），`figure` 是概念，`line`/`rectangle` 是 `figure` 的特化（specialization）。

**第二步：从领域模型到软件设计。** 动词变成方法，`create` 往往变成构造函数。方法该放在哪个类上？课件给的答案是**职责驱动设计**：每个类有一组职责，通常是「知道某些事」与「完成某些任务」。例如 figure 负责知道自己的位置，也负责把自己画到屏幕上。

**第三步：识别质量属性。** R5 与 R1–R4 性质不同：它不描述功能，而是一个**质量属性**——它要求设计对未来新增图形是开放的。这一条直接决定了 `figure` 该做成什么。

### 5.2 四个权衡维度：接口 vs 抽象类

讲义 notes 第 2 页把这一步的推理写得很清楚：

| 选择 | 提供 | 牺牲 |
|---|---|---|
| 只有接口 | **可扩展性**（多种实现）+ **灵活性**（实现方式完全独立） | 没有代码复用，每个实现都要重写全部方法 |
| 只有抽象类 | **复用**（公共代码写一次） | 牺牲**灵活性**（固定了部分设计决策，且 Java 单继承） |
| 接口 + 抽象类（骨架实现） | 复用 + 灵活性兼得 | **复杂度上升**，理解与实现都更费力 |

课件明确说这个取舍是「marginally more difficult to understand and implement」——注意「marginally」，它的立场不是「越抽象越好」，而是「按需付费」。

### 5.3 什么是设计模式

课件第 5 页引用 Christopher Alexander 的经典定义：

> "Each pattern describes a problem which occurs over and over again in our environment, and then describes the core of the solution to that problem, in such a way that you can use this solution a million times over, without ever doing it the same way twice."

最后半句是关键：**模式描述的是解决方案的「核心」，不是可复制粘贴的代码**。同一个 Composite，在图形编辑器里接口是 `Figure`，在集合库里接口是 `IntSet`，在运输系统里接口是 `Item`——接口各不相同，但「整体与部分同型」的结构一模一样。

课件第 6 页补充了 Alexander 的背景：模式是**捕捉设计知识**的方式，每个模式是「经过验证的解法」，通常是「以有利方式化解冲突力量的工程折中」。

### 5.4 模式的四要素与三大分类

**四要素**（第 12 页）：

| 要素 | 内容 | 为什么重要 |
|---|---|---|
| **Name** | 模式名 | 成为设计词汇的一部分，提升沟通层次 |
| **Problem** | 何时适用 | 决定「该不该用」 |
| **Solution** | 设计元素及其关系 | **抽象的**，必须被特化到具体领域 |
| **Consequences** | 权衡 | 每个模式都有代价，涉及灵活性、可扩展性等 |

**三大分类**（第 16 页）：

| 类别 | 变化的是什么 | 代表 |
|---|---|---|
| **Structural（结构型）** | 对象结构 | Composite、Façade、Adapter、Decorator、Bridge、Proxy |
| **Behavioral（行为型）** | 想要的行为 | Strategy、Template Method、Observer、Command、State、Visitor、Mediator |
| **Creational（创建型）** | 对象的创建 | Factory Method、Abstract Factory、Singleton、Builder、Prototype |

课件第 16 页还有一句提醒，值得原样记住：**"Experienced students: please don't jump straight to the pattern"**。模式是**从场景推导出来**的，不是先选模式再找场景。先看问题，再想模式。

### 5.5 Composite：整体与部分同型

**问题**（第 3 页）：要表示「部分—整体」的层次结构，并且希望能忽略「对象的组合」与「单个对象」之间的差别。

课件第 2 页的运输公司练习是最好的引入：货物有信件、包裹、易碎品，各有重量与保险成本；公司还卖箱子，客户可以把多件货物装进箱子；软件要能算箱子的总重与总保额，但**大部分代码应该把「装着若干货物的箱子」当作「一件货物」来处理**。

**解法**：定义一个公共接口（如 `Item`），叶子类（`Letter`、`Package`、`FragileItem`）实现它，容器类（`Box`）**也实现它**并持有一组 `Item`。容器的方法把调用转发给子元素并汇总结果。

**后果**（第 3 页原文）：

| 好处 | 代价 |
|---|---|
| 客户端简单，可以统一处理个体与组合 | 设计可能**过度泛化** |
| 容易添加新的组件类型 | 某些操作**并非在每个类上都有意义**（例如「给信件称重」在「箱子」上意义不同） |
| | 组合可能只允许包含**特定种类**的组件，而统一接口无法表达这个约束 |

第二条代价值得展开：一旦 `Box` 与 `Letter` 共享 `Item` 接口，接口上每个方法都必须对两者都有合理语义。如果接口里有 `getStampValue()`，`Box` 该怎么实现？返回 0？抛异常？这就是「过度泛化」的具体表现。

**我们见过它**（第 4 页）：第 2 讲的 `IntSet` 就是 Composite：

```java
interface IntSet {
    boolean contains(int element);
    boolean isSubsetOf(IntSet otherSet);
    IntSet union(IntSet otherSet);
}
class UnionSet implements IntSet {
    private IntSet set1;
    private IntSet set2;
    public UnionSet(IntSet s1, IntSet s2) { this.set1 = s1; this.set2 = s2; }
    public boolean contains(int elem) {
        return set1.contains(elem) || this.set2.contains(elem);
    }
    public IntSet union(IntSet otherSet) {
        return new UnionSet(this, otherSet);
    }
}
```

`UnionSet` 既是 `IntSet`（组合），又持有两个 `IntSet`（部分），客户端不需要区分「空集」「单元素集」「并集」。课件第 4 页的批注正是本讲的核心论点：

> Our designs for composite figures, grouped packages, and union sets solve similar problems in similar ways. We call this problem-solution pair a design pattern.

> 待核实：第 4 页打印的 `isSubsetOf` 方法体为 `return set1.isSubsetOf(elem) && set2.isSubsetOf(elem);`，其中 `elem` 未定义（参数名是 `otherSet`），应为幻灯片排版错误。

### 5.6 Template Method：把骨架固定，把一步留空

**问题**（第 30 页）：一个算法由「变化的部分」与「不变的部分」组成，且不变的部分必须被保护起来不被子类改坏。

**解法**：父类实现算法骨架（模板方法），在需要变化的地方调用抽象方法（或可重写方法）；子类只实现那些「钩子」。

**后果**（第 30 页）：

- **代码复用**——骨架写一次；
- **控制反转（好莱坞原则）**：「Don't call us, we'll call you」，是父类的骨架在调用子类的步骤，而不是子类调用父类；
- **保证不变部分不被子类篡改**——因为骨架在父类里，子类无法重写整个流程。

讲义 notes 第 3 页给了一个绝佳的动机：画图编辑器里每个图形 `resize` 的方式不同（圆改半径、矩形改长宽、组合图形改尺寸后重新布局子元素），但**所有图形在 resize 之后都要重绘**。如果每个 `resize` 实现里都写一行 `updateScreen()`：

1. 重复代码（一行 × N 个类）；
2. 更糟的是——**新增图形时可能忘记写这一行**，产生一个极其隐蔽的 bug。

模板方法把 `updateScreen()` 提到父类的 `resize()` 里，子类只实现 `doResize()`：

```
父类：public final void resize(...) { doResize(...); updateScreen(); }
子类：protected void doResize(...) { … }        // 只关心自己的几何变化
```

这样「重绘」这件事**在结构上不可能被忘记**。这是模式比「约定」强的地方：它把正确性做进了类型系统与继承结构。

**我们见过它**（第 31 页）：Recitation 3 的图书馆系统。`Item` 超类里的滞纳金计算：

1. 取得该物品的借阅期（**下调用（downcall）**到子类）；
2. 从借出天数中减去借阅期，若不是正数则无罚金；
3. 否则根据逾期天数计算罚金（**下调用**到子类）。

其中 Books 与 Magazines 的费率结构相同（第一周每天 $0.15 / $0.20，之后每天 $0.50 / $0.10），只是数字不同——课件把它留作挑战：**如何用第二个模板方法在 Books 与 Magazines 之间复用「两段费率」的计算逻辑**。答案的思路是再抽一层：父类实现「按两段费率分别计算再相加」的骨架，子类只提供两个费率数字与分界点。

### 5.7 其余模式速览（意图 / 适用 / 代价）

以下按课件第 20–43 页整理。每行都对应「Name / Problem / Solution / Consequences」四要素。

| 模式 | 类别 | 意图（一句话） | 适用信号 | 主要代价 |
|---|---|---|---|---|
| **Façade** | 结构 | 为复杂子系统提供一个简化接口 | 库太大、类太多、想切换实现、想分层 | 客户端若需要细粒度控制仍要绕过它；可能变成「上帝类」 |
| **Adapter** | 结构 | 把已有类的接口转成客户端期望的接口 | 接口不匹配；想复用与现有接口无关的类 | 多一层间接；适配器本身可能变成瓶颈 |
| **Composite** | 结构 | 统一对待个体与组合 | 整体—部分层次 | 过度泛化；接口方法在部分类上无意义 |
| **Strategy** | 行为 | 把可互换的算法封装成对象 | 多个类只行为不同；需要运行时切换算法 | 增加对象与间接层；代码更难读；策略接口对简单算法是额外开销 |
| **Template Method** | 行为 | 父类定骨架，子类填空 | 算法有不变骨架 + 可变步骤 | 继承耦合；子类受父类骨架约束 |
| **Command** | 行为 | 把请求封装成对象 | 需要撤销、排队、日志重放、宏命令 | 类数量膨胀 |
| **Factory Method** | 创建 | 让子类决定创建哪个类 | 类无法预知要创建的对象类 | 需要引入平行的类层次 |
| **Abstract Factory** | 创建 | 创建「一族」相互配套的对象 | 多套实现族，且不能混用 | **难以支持新的产品种类**（要改所有工厂） |
| **Decorator** | 结构 | 动态给单个对象加职责 | 需要可撤销的职责；子类爆炸 | **破坏对象身份**（`equals`/`==` 失效）；大量小对象 |
| **Observer** | 行为 | 一对多依赖，状态变化时通知 | 一个变化要引发多处更新，且不知道有多少 | 通知可能级联；可能造成更新风暴 |
| **Bridge** | 结构 | 抽象与实现分离，各自独立演化 | 多个抽象 × 多种实现 | 需要固定的实现接口 |
| **Singleton** | 创建 | 保证唯一实例并提供全局访问点 | 全局数据与操作需要一致使用 | 全局状态难以测试；并发下需小心 |
| **Proxy** | 结构 | 用代理对象控制对真实对象的访问 | 远程对象、延迟加载、访问控制、引用计数 | 增加一层间接与簿记开销 |
| **Mediator** | 行为 | 把多对多通信集中到中介者 | 对象间通信复杂，难以复用 | 中介者可能膨胀成单体 |
| **Visitor** | 行为 | 把「操作」从「元素类」中分离 | 类集合稳定，但要频繁加新操作 | **添加新元素类型很难**（要改所有 visitor） |

几个值得单独记住的对照：

**Façade vs Adapter**（第 24 页）——两者都「包一层」，但动机相反：

| 维度 | Façade | Adapter |
|---|---|---|
| 动机 | **简化**接口 | **匹配**已有接口 |
| 接口从哪来 | 你自己设计的新接口 | **给定的**（客户端已按它编程） |
| 多态性 | 通常在 Façade 内部**静态**选定实现 | **动态**分派到多个实现 |
| 典型场景 | 用图片库的一小部分功能 | 把 JDBC 的 `next()/getObject()` 适配成 `Iterator` 的 `hasNext()/next()` |

**Strategy vs Template Method**（第 26、28、30 页）——两者都处理「算法可变」，但机制不同：

| 维度 | Strategy | Template Method |
|---|---|---|
| 变化载体 | **组合**：上下文持有策略对象 | **继承**：子类重写钩子 |
| 切换时机 | **运行期**可换 | **编译期**由类决定 |
| 耦合 | 上下文与算法解耦 | 父类与子类紧耦合 |
| 课件原话 | "Strategy could be implemented with inheritance… Drawback: couples Context to algorithm… can't change algorithm dynamically" | "Inverted 'Hollywood' control" |

课件第 28 页还留了一个很好的思考题：**在函数式语言里怎么实现 Strategy？** 答案是把「策略接口」直接换成一个函数值（`Comparator` 就是一个 SAM 接口，Java 8 之后可以用 lambda 传入）——这说明 Strategy 的本质是「把行为作为一等值传递」，而对象只是 Java 7 时代的载体。

**Factory Method vs Abstract Factory**：前者是**一个**创建方法由子类决定；后者是**一族**产品的创建接口，保证同族配套（课件第 33 页的窗口库例子：不能把 Swing 与 SWT 的组件混用）。

## 6. 代码示例

### 6.1 官方课程代码

出自 `07-design-patterns.pdf` 第 4 页（Composite：`IntSet` 与 `UnionSet`）：

```java
interface IntSet {
    boolean contains(int element);
    boolean isSubsetOf(IntSet otherSet);
    IntSet union(IntSet otherSet);
}
class UnionSet implements IntSet {
    private IntSet set1;
    private IntSet set2;
    public UnionSet(IntSet s1, IntSet s2) { this.set1 = s1; this.set2 = s2; }
    public boolean contains(int elem) {
        return set1.contains(elem) || this.set2.contains(elem);
    }
    public IntSet union(IntSet otherSet) {
        return new UnionSet(this, otherSet);
    }
}
```

出自同文件第 27 页（Strategy：把 `if-else` 换成 `Comparator`）：

```java
void sort(int[] list, String order) {          // 变化前：用字符串选分支
    …
    boolean mustswap;
    if (order.equals("up")) {
        mustswap = list[i] < list[j];
    } else if (order.equals("down")) {
        mustswap = list[i] > list[j];
    }
    …
}

void sort(int[] list, Comparator cmp) {        // 变化后：算法作为对象传入
    …
    boolean mustswap;
    mustswap = cmp.compare(list[i], list[j]);
    …
}
interface Comparator {
    boolean compare(int i, int j);
}
class UpComparator implements Comparator {
    boolean compare(int i, int j) { return i<j; }
}
class DownComparator implements Comparator {
    boolean compare(int i, int j) { return i>j; }
}
```

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：Composite** —— 运输公司的货物与箱子（对应课件第 2 页的课堂练习）：

```java
interface Item {
    int weightInOunces();
    int insuranceCents();
}

class Letter implements Item {
    public int weightInOunces() { return 1; }            // 信件固定 1 盎司
    public int insuranceCents() { return 50; }
}

class FragileItem implements Item {
    private final int weight;
    FragileItem(int weight) { this.weight = weight; }
    public int weightInOunces() { return weight; }
    public int insuranceCents() { return 200 + weight * 10; }   // 易碎品保险更贵
}

class Box implements Item {                              // 关键：Box 也实现 Item
    private final java.util.List<Item> contents = new java.util.ArrayList<>();
    void add(Item i) { contents.add(i); }
    public int weightInOunces() {
        int sum = 0;
        for (Item i : contents) sum += i.weightInOunces();   // 递归汇总
        return sum;
    }
    public int insuranceCents() {
        int sum = 0;
        for (Item i : contents) sum += i.insuranceCents();
        return sum;
    }
}

// 客户端完全不需要区分单个物品与箱子
Item shipment = new Box();
((Box) shipment).add(new Letter());
((Box) shipment).add(new FragileItem(12));
System.out.println(shipment.weightInOunces());   // 13
```

注意 `Box` 内部的循环调用 `i.weightInOunces()` 可以作用在 `Letter` 上，也可以作用在另一个 `Box` 上——嵌套箱子自动工作，这就是 Composite 的递归本质。

**示例 B：Template Method** —— 对应讲义 notes 第 3 页的 resize/重绘问题：

```java
abstract class Figure {
    // 模板方法：骨架固定，声明 final 防止子类改坏流程
    public final void resize(int factor) {
        doResize(factor);       // 变化的一步，留给子类
        updateScreen();         // 不变的一步，不可能被忘记
    }
    protected abstract void doResize(int factor);
    private void updateScreen() { System.out.println("repaint " + getClass().getSimpleName()); }
}

class Circle extends Figure {
    private int radius = 5;
    protected void doResize(int factor) { radius *= factor; }
}
class Rectangle extends Figure {
    private int w = 3, h = 4;
    protected void doResize(int factor) { w *= factor; h *= factor; }
}

new Circle().resize(2);      // repaint Circle
new Rectangle().resize(3);   // repaint Rectangle
```

对比「每个子类自己写 `updateScreen()`」：新增 `Triangle` 时若忘记调用，编译器不会报错，测试也未必覆盖——模板方法把这类遗漏变成了**结构上不可能**。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| Façade | Adapter | Façade **简化**接口（新接口由你设计）；Adapter **匹配**接口（目标接口已给定）。Façade 内部实现通常静态选定；Adapter 常做动态分派 |
| Strategy | Template Method | Strategy 用**组合**，运行期可换算法；Template Method 用**继承**，编译期由类决定，且能保护骨架不被篡改 |
| Composite | Decorator | 两者都持有同类型对象并实现同一接口。Composite 持有**多个**子节点、目的是**聚合**；Decorator 持有**一个**被装饰对象、目的是**叠加职责**，且会破坏对象身份 |
| Factory Method | Abstract Factory | 前者是**一个**创建方法，由子类决定返回哪个具体类；后者是**一族**产品的创建接口，保证同族配套、不能混用 |
| 设计模式 | 代码模板 | 模式描述「问题 + 解法核心 + 代价」，必须**特化**到具体领域接口；照抄代码往往带来过度设计 |
| 质量属性（R5） | 功能需求（R1–R4） | 功能需求说「做什么」；质量属性说「设计要满足什么性质」（可扩展、可复用）。后者直接决定抽象层次的取舍 |
| 接口 | 抽象类（在设计取舍中） | 接口给**灵活性 + 可扩展性**但无复用；抽象类给**复用**但固定部分决策；两者并用兼得但**增加复杂度** |

## 8. 对应原版讲义

本讲对应两份 PDF：

**（1）幻灯片**

- PDF 相对路径：`90-原始PDF/15-214/slides/07-design-patterns.pdf`
- 总页数：44 页
- 重点页码：
  - 第 2 页：运输公司设计练习（Composite 的动机）
  - 第 3 页：Composite 的适用性与后果
  - 第 4 页：`IntSet`/`UnionSet`——我们见过的 Composite
  - 第 5–8 页：设计模式的定义（Alexander 引言）、历史、好处
  - 第 9–11 页：木匠的榫卯类比
  - 第 12 页：模式的四要素
  - 第 13–14 页：GoF 与 Shalloway & Trott 两本书
  - 第 15–18 页：三条基本 OO 原则、三大分类、必知模式清单
  - 第 20 页：Façade
  - 第 22 页：Adapter
  - 第 23–24 页：回到基本原则、Façade vs Adapter
  - 第 26–28 页：Strategy 与 `Comparator` 代码对照
  - 第 29 页：Command
  - 第 30–31 页：Template Method 与 Recitation 3 的图书馆例子
  - 第 32–34 页：Factory Method、Abstract Factory
  - 第 35–36 页：Decorator、Observer
  - 第 38 页：Bridge
  - 第 40 页：Singleton
  - 第 41 页：Proxy
  - 第 42–43 页：Mediator、Visitor
  - 第 44 页：其他 GoF 模式（Builder、Prototype、Flyweight、Chain of Responsibility、Interpreter、Memento、State）
- 原始网页链接：`https://www.cs.cmu.edu/~aldrich/214/slides/07-design-patterns.pdf`

**（2）讲义笔记**

- PDF 相对路径：`90-原始PDF/15-214/slides/07-design-pattern-notes.pdf`
- 总页数：3 页
- 内容：画图编辑器的完整设计演练（R1–R6、名词/动词分析、职责驱动设计、接口 vs 抽象类）、Composite 与 Template Method 的引入动机
- 原始网页链接：`https://www.cs.cmu.edu/~aldrich/214/slides/07-design-pattern-notes.pdf`
- 文件头打印的原始路径为 `C:\plaid\courses\15-214\2013-2fall\lectures\07-design-patterns\07-design-pattern-notes.txt`，日期 `Tuesday, September 17, 2013`，与本讲日期一致。

> 待核实：`07-design-patterns.pdf` 第 1 页页脚标注为 **Spring 2013**（版权行含 C Kästner），与本次 Fall 2013 学期的其他讲义不同，应为复用旧版封面所致；第 4 页 `isSubsetOf` 的 `elem` 未定义，属排版错误。

## 9. 对应视频

未找到官方公开录像。2013 年秋季的 15-214 课堂没有公开发布录像，故不提供链接与时间戳。

## 10. 本节复习

- 设计流程：需求 → 名词/动词 → 领域模型 → 职责驱动设计 → 软件设计。
- 名词/动词判别：文字或数字 → 属性；复杂结构 → 概念。
- 四个权衡：可扩展性、灵活性、复用、复杂度。接口给前两个，抽象类给第三个，两者并用增加第四个。
- 模式四要素：Name / Problem / Solution（抽象，需特化）/ Consequences。
- 三大分类：结构型（对象结构）、行为型（行为）、创建型（对象创建）。
- 三条基本 OO 原则：面向接口设计、优先组合、找出变化并封装。
- Composite：整体与部分实现同一接口，客户端统一处理；代价是过度泛化与「某些操作并非处处有意义」。
- Template Method：父类定骨架、子类填空，好莱坞原则；好处是复用 + 防止不变部分被改坏。
- Façade 简化接口，Adapter 匹配接口；Strategy 用组合可动态换，Template Method 用继承编译期定。
- 别一上来就选模式——模式从场景推导。

## 11. 自我检查

1. 需求里写「系统应当支持在未来添加新的图形类型」。这属于功能需求还是质量属性？它会如何影响你对 `Figure` 的设计（接口 / 抽象类 / 两者都要）？
2. 为什么说 `UnionSet` 是 Composite 模式？请指出其中的「整体」「部分」与「统一接口」分别是什么。如果把 `UnionSet` 改成持有 `List<IntSet>`，模式还成立吗？
3. 下面这个 `resize` 实现有什么问题？请用模板方法改写，并说明改写后哪一类 bug 变得不可能发生。
   ```java
   class Circle { void resize(int f) { radius *= f; updateScreen(); } }
   class Rectangle { void resize(int f) { w *= f; h *= f; updateScreen(); } }
   class Triangle { void resize(int f) { side *= f; } }   // 忘了 updateScreen
   ```
4. Façade 与 Adapter 都是「包一层」，请各举一个你熟悉的 JDK 或常见库中的例子，并说明它属于哪一个、为什么。
5. Strategy 与 Template Method 都能实现「可替换的算法」。请说明在什么情况下你会选 Strategy 而不是 Template Method，给出至少两条判据。

<details>
<summary>参考答案</summary>

1. 这是**质量属性**（quality attribute），因为它不描述系统做什么，而是约束设计应具备的性质（可扩展性）。它直接影响 `Figure` 的抽象方式：如果只做抽象类，未来新增图形必须继承它，受单继承限制，且被固定了部分设计决策（灵活性下降）；如果只做接口，每个新图形都要重写全部方法（无复用）。因此**接口 + 抽象骨架实现**（如 `Figure` 接口 + `AbstractFigure` 提供 `updateScreen()` 等公共实现）是最贴合该质量属性的选择——代价是设计复杂度上升。若 R5 不存在（图形种类固定），只需一个具体类或抽象类即可。

2. 「统一接口」是 `IntSet`；「部分」是 `set1`、`set2` 两个 `IntSet` 字段；「整体」是 `UnionSet` 本身——它**同时实现** `IntSet`，所以客户端可以把它当作一个普通集合继续参与 `union`，从而形成任意深度的嵌套。改成持有 `List<IntSet>` 后模式**仍然成立**，而且更通用（n 元并集而非二元）。Composite 的本质是「容器实现与元素相同的接口并递归转发」，容器持有 2 个还是 n 个子节点只是实现细节。课件选择二元版本是为了让 `union` 的构造更简洁（`new UnionSet(this, otherSet)`）。

3. 问题：`Triangle` 忘记调用 `updateScreen()`，导致 resize 后屏幕不刷新。编译器不会报错，如果测试没有覆盖「Triangle 的 resize 后界面状态」，这个 bug 会一直潜伏——而且随着新图形增多，遗漏概率线性上升。模板方法改写：
   ```java
   abstract class Figure {
       public final void resize(int f) { doResize(f); updateScreen(); }   // 骨架
       protected abstract void doResize(int f);
       private void updateScreen() { … }
   }
   class Triangle extends Figure {
       protected void doResize(int f) { side *= f; }    // 只需实现几何变化
   }
   ```
   改写后「忘记重绘」**在结构上不可能发生**：子类根本没有机会写 `resize`，它只能实现 `doResize`，而 `updateScreen()` 由父类的 `final` 模板方法保证调用。这正是课件所说的「Ensures the invariant parts of the algorithm are not changed by subclasses」。

4. **Façade**：`java.sql.DriverManager` 或更典型的 `javax.swing.JOptionPane`——`JOptionPane.showMessageDialog(...)` 一行就能弹出对话框，而底层涉及 `JFrame`、`JDialog`、布局管理器、事件线程等大量类；接口是新设计的简化接口，符合 Façade。**Adapter**：`java.io.InputStreamReader`——它把 `InputStream`（字节流接口）适配成 `Reader`（字符流接口），目标接口 `Reader` 是**已给定**的（客户端按 `Reader` 编程），适配器把 `read()` 调用转发给底层 `InputStream` 并做解码，符合 Adapter。另一个常见例子是 `Arrays.asList(...)` 把数组适配成 `List`。

5. 选 Strategy 而非 Template Method 的判据：(1) **需要在运行期切换算法**——例如电商结算时按用户所在地区动态选择税率策略，Template Method 的算法在编译期由类固定，换算法就得换对象；(2) **不想让上下文与算法形成继承耦合**——Strategy 通过组合持有算法，上下文可以独立演化，也不会被单继承限制（一个类只能继承一个父类，但可以持有任意多个策略）；(3) **算法需要被独立测试或复用**——策略对象可以单独实例化测试，也能被多个不同的上下文共用，而 Template Method 的钩子只能在其子类中存在；(4) **算法数量多且组合复杂**——用继承会导致子类爆炸（每种组合一个子类），用 Strategy 只需组合对象。反过来，如果算法骨架固定、只有一两步变化，且希望强制子类不篡改流程，Template Method 更轻量。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-06-Mutability-and-Java-Potpourri]]
- 下一讲：[[15-214-08-Specification-and-Testing]]
- 课程总览：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]
- 课程目录：[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：GoF《Design Patterns: Elements of Reusable Object-Oriented Software》（C++/Smalltalk 示例，适合当参考手册）；Shalloway & Trott《Design Patterns Explained》（Java，本课指定教材，教学性更强）。Composite 与 Template Method 会在 [[15-214-09-Design-Patterns-Continued]] 中继续深化，并在 [[15-214-11-Design-Principles-GRASP]] 中被归纳为 GRASP 原则的具体应用。
