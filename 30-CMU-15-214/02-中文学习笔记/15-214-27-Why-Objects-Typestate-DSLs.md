---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L27
topic: Why Objects, Typestate, and Domain-Specific Languages
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 面向对象
  - 类型状态
  - 权限
  - DSL
  - 领域特定语言
---

# 第 27 讲 对象的价值、类型状态与领域特定语言（Why Objects, Typestate, and DSLs）

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。本讲由三份讲义组成：`28-why-objects.pdf`（对象的价值）、`28-protocol-programming.pdf`（类型状态与权限）、`28-dsls-in-wyvern.pdf`（Wyvern 中的 DSL）。

## 1. 本节学习目标

- 能说明为什么「封装」「继承」「动态分派」单独都不足以定义 OO，并指出 OO 真正的独特价值。
- 能解释 Cook 的「对象 = 导出一个过程式接口的值」这一观点，以及它与 ADT（抽象数据类型）的区别。
- 能通过 `IntSet` 的例子说明为什么对象比 ADT 更**可互操作**，而 ADT 在**性能**上可能更优。
- 能解释「服务抽象（service abstraction）」与「设计杠杆（design leverage）」三要素。
- 能说明框架（framework）与库（library）的区别，以及「好莱坞原则」。
- 能说明类型状态（typestate）的定义，并写出一个 `ClosedFile → OpenFile` 的状态迁移。
- 能说明权限（permission）的四种类型及其分裂规则，并用它构造数据流图。
- 能解释为什么需要「类型特定的语言（TSL）」，以及 Wyvern 的两阶段解析如何保证安全组合。

## 2. 前置知识

- [[15-214-02-Objects-Encapsulation-Polymorphism]]：对象、封装、多态。
- [[15-214-03-Encapsulation-and-Inheritance]]：信息隐藏、脆弱基类问题。
- [[15-214-04-Inheritance-Typechecking-Dispatch]]：动态分派。
- [[15-214-07-Design-Patterns]]：策略、模板方法、观察者——本讲会把它们放到「设计杠杆」的框架里重新解释。
- [[15-214-23-Static-Analysis]]：类型检查作为规约、协议检查。
- [[15-214-26-History-and-Future-of-Objects]]：对象的历史，特别是 Kay 的「消息」观点。

## 3. 核心概念

- **Service Abstraction（服务抽象）**：一组对象对外提供的、有明确契约的操作集合。
- **Autognostic**：Cook 的术语——对象能**自我解释**其行为，因为方法体与数据在同一个单元里。
- **ADT（Abstract Data Type，抽象数据类型）**：由类型名 + 操作签名定义的数据类型，**操作是外部函数**（如 `Set.insert(s, x)`）。
- **Object（对象）**：把操作与数据封装在一起、通过**动态分派**调用的实体（如 `s.insert(x)`）。
- **First-Class Interoperability（一等互操作性）**：不同实现的对象可以在同一处互换使用，无需适配。
- **Design Leverage（设计杠杆）**：用少量设计投入获得大量复用收益的能力。
- **Framework（框架）**：定义**架构骨架**、由用户填充**热 spots（hot spots）**的复用单元；控制流由框架掌握（好莱坞原则：Don't call us, we'll call you）。
- **Hot Spot / Cold Spot**：框架中**可扩展**的点 / **固定不变**的部分。
- **Extension Point（扩展点）**：框架提供给用户的钩子（接口、抽象类、回调、生命周期方法）。
- **Typestate（类型状态）**：对象的**协议状态**——同一类型在不同时刻允许的操作不同（如文件「已关闭」时不能 `read`）。
- **Protocol（协议）**：方法必须遵守的调用顺序。
- **Permission（权限）**：对引用的访问能力分类——unique / immutable / shared / full / pure。
- **Permission Splitting（权限分裂）**：把一个引用分裂成多个，各自获得较弱权限。
- **DSL（Domain-Specific Language，领域特定语言）**：为特定领域设计的语言（SQL、正则、HTML 模板）。
- **TSL（Type-Specific Language，类型特定语言）**：与某个**类型**关联、由该类型定义语法与语义的 DSL。
- **Metaobject（元对象）**：在 Wyvern 中，为某个类型提供 parser 与 typechecker 的对象。

## 4. 通俗理解

**「为什么要有对象？」这个问题比想象中难。** 因为对象的三条常见理由都站不住脚：

- **封装？** 很多语言有封装但不是 OO（比如 Modula-2 的模块）。
- **继承？** Go 语言完全没有继承，照样很好用；Self 语言用「委托」代替继承。
- **代码复用？** 函数、泛型、模块都能复用。

那 OO 到底独特在哪？这一讲的答案分三层：

1. **动态分派（dynamic dispatch）是核心**——只有对象能在**运行时**根据实际类型选择行为，而且**调用者与被调用者可以独立演化**。
2. **对象比 ADT 更可互操作**——一个 `IntSet` 接口可以有十种实现，它们能互相嵌套使用；而 ADT 的 `isSubsetOf(IntSetA other)` 只能接受**自己那一种**实现。
3. **对象支撑「设计杠杆」**——框架、服务抽象、生态。Linux 内核不是用 OO 语言写的，但它是**地道的 OO 框架**（结构体里放函数指针）。

**什么是「类型状态」？** 想象一个文件对象：刚创建时是「已关闭」，`open()` 之后是「已打开」。在「已关闭」状态下调用 `read()` 是**错误**的。普通类型系统看不出这个区别——`File` 就是 `File`，编译器不知道它现在能不能读。**类型状态把「对象当前处于哪个协议状态」也纳入类型**，于是「在错误状态下调用方法」变成**编译错误**，而不是运行时异常。

**为什么需要 DSL？** 因为通用语言表达领域概念很笨拙。写 SQL 时你不想用字符串拼（容易注入、没有语法检查）；写正则时你不想调用一堆 `Pattern.compile`。DSL 让你用**领域专家看得懂的语法**写代码。但 DSL 有个大问题：**每加一个 DSL 就多一套语法，它们会互相冲突**。Wyvern 的答案是：**让语法与类型绑定**——看到一段 `regex` 字面量，编译器知道它是 `Regex` 类型，于是用 `Regex` 的语法规则解析它。这样多个 DSL 可以安全共存。

## 5. 原理与推导

### 5.1 OOP 有多普及（以及为什么有人讨厌它）

课件（`28-why-objects.pdf`）第 2–3 页给出普及度数据：在 TIOBE 排行榜前十中，有 6–8 个是面向对象的语言。第 4 页引用 Alexander Stepanov（STL 的作者）的批评：

> "I find OOP technically unsound. It attempts to decompose the world in terms of interfaces that vary on a single type. To deal with the real problems you need multisorted algebras — families of interfaces that span multiple types. I find OOP philosophically unsound. It claims that everything is an object. Even if it is true it is not very interesting — saying that everything is an object is saying nothing at all."

**Stepanov 的三条批评**：

1. **技术上的不健全**：OO 按「单个类型上变化的接口」分解世界，但真实问题需要**多类型代数**（multisorted algebras）——即一族跨多个类型的接口（想想泛型算法 `sort(Iterator first, Iterator last)` 需要两个类型协作）。
2. **哲学上的不健全**：「一切皆对象」如果为真，也没说什么有用的东西。
3. **（隐含）** 对象把「数据」和「算法」绑死，妨碍了泛型编程。

第 6 页引用 Joe Armstrong（Erlang 的作者）的另一类批评：

> "The problem with object-oriented languages is they've got all this implicit environment that they carry around with them. You wanted a banana but what you got was a gorilla holding the banana and the entire jungle."

**Armstrong 的批评**：对象携带**隐式环境**——你想要一个香蕉（一个函数），却得到了拿着香蕉的大猩猩和整片丛林（一堆依赖、状态、上下文）。这是**耦合**问题：对象的「自包含」变成了「难以拆分」。

**课件的态度**：这些批评都有道理，但它们批评的是**某些 OO 实现**，不是 OO 的**核心价值**。接下来的部分就是在找那个核心。

### 5.2 封装与继承都不是 OO 独有

课件第 9–10 页：

> **Encapsulation is not unique to OO**
> - Modules (Modula-2, OCaml) provide encapsulation without objects
>
> **Inheritance is not unique to OO**
> - Go has no inheritance at all
> - Self uses delegation instead of inheritance

**Modula-2 的模块**：可以把一组数据和操作放在一个 `MODULE` 里，只导出接口部分——封装得非常好，但**没有对象**（没有「实例」，没有动态分派）。

**Go 的接口**：Go 有方法、有接口（隐式实现），但**没有继承**（没有 `extends`）。它靠**组合（embedding）** 复用。这证明继承不是 OO 的必要条件。

**Self 的委托**：Self 语言（1980 年代末，PARC）用**原型（prototype）+ 委托（delegation）** 代替类与继承——每个对象直接复制另一个对象，方法查找失败时把消息**转发**给父对象。JavaScript 的原型链就是这条路线。

**结论**：封装、继承、复用都不是 OO 的本质。那什么是？

### 5.3 动态分派是核心

课件第 15 页：

> **Dynamic dispatch is the core of OO**
> - The ability to call a method on an object and have the *actual* implementation chosen at runtime
> - Enables **open recursion** and **independent evolution**

**为什么动态分派是核心？** 因为它同时提供了两件别的机制做不到的事：

1. **调用者不需要知道被调用者的具体类型**——这实现了**依赖倒置**（depend on abstractions, not concretions），是 [[15-214-07-Design-Patterns]] 里几乎所有模式的基础。
2. **被调用者可以独立演化**——你新增一个 `Circle` 类，所有调用 `shape.draw()` 的代码**一行都不用改**。这是「开闭原则（open-closed principle）」的机制基础。

**对比泛型**：泛型（`List<T>`）也能做到「调用者不知道具体类型」，但它是**编译期**的——所有类型在编译时必须已知。动态分派是**运行期**的——可以在程序运行时加载新的实现（插件、热更新）。这是 OO 独有的能力。

**对比函数指针**：C 的结构体里放函数指针也能实现运行期分派（Linux 内核就这么做），但那是**手工的**——没有类型检查、没有继承、没有封装。OO 把这套机制**语言化、类型化、自动化**了。

### 5.4 对象 = 导出一个过程式接口的值

课件第 16 页引用 William Cook（2009）的观点：

> **Objects are values that export a procedural interface**
> - An object is a value
> - Its interface consists of procedures (methods)
> - The procedures can access the object's state (closure over `this`)
> - **Autognostic**: the object knows how to interpret its own behavior

**这个定义的精妙之处**：它把对象还原成两个更基本的概念——**值** 与 **闭包**。

- **对象是一个值**：可以传递、存储、放入集合；
- **它的接口是过程**：方法就是函数；
- **方法闭包了 `this`**：所以方法能访问对象的状态——这就是「封装」的实现机制；
- **autognostic（自我解释）**：对象**自己**知道怎么执行它的方法，调用者不需要知道。

**为什么这个定义重要？** 因为它解释了 OO 与**函数式编程**的关系：对象就是「一组共享同一环境的闭包」。反过来，闭包也可以模拟对象（这就是 SICP 第 3 章的内容）。两者是**同一件事的两种视角**。

**这也解释了 Cook 的另一个论点**：OO 与 ADT 是**两种不同的抽象机制**，不是同一种东西的两个名字。下面详细展开。

### 5.5 对象 vs ADT：`IntSet` 的例子

课件第 17 页给出**对象版本**：

```java
interface IntSet {
    boolean contains(int x);
    boolean isSubsetOf(IntSet other);
}
```

**注意 `isSubsetOf` 的参数类型是 `IntSet`（接口）**。这意味着：

- 任何实现了 `IntSet` 的类（`ListIntSet`、`TreeIntSet`、`BitmapIntSet`）都可以传进来；
- 一个 `TreeIntSet` 可以检查自己是否是某个 `BitmapIntSet` 的子集；
- **互操作性（interoperability）** 是「一等（first-class）」的——不需要适配器、不需要转换。

课件第 18 页给出**ADT 版本**：

```java
interface IntSetA {
    boolean contains(int x);
    boolean isSubsetOf(IntSetA other);      // ← 注意这里
}
```

**看起来一样？** 课件指出的关键差别在**实现**：ADT 的 `isSubsetOf` 只能接受**同一种实现**。如果你想支持「TreeIntSet 是 BitmapIntSet 的子集」，就必须：

- 要么提供 `isSubsetOf(IntSetB other)` 的重载——**类型的组合爆炸**（n 种实现需要 n² 个方法）；
- 要么先转换成统一表示——**性能损失**。

**更准确地说**，课件的对比是：**ADT 的操作是「外部函数」，它只能看到类型名与签名，无法在运行时根据实现选择算法**。而对象的 `isSubsetOf` 可以**动态分派**到最优实现（例如 `BitmapIntSet.isSubsetOf(TreeIntSet)` 可以用位运算快速判断）。

课件还给出一个具体的编译错误示例（第 18 页）：如果 ADT 版本写成

```java
class IntSetA {
    boolean isSubsetOf(IntSetA other) { ... }
}
class IntSetB {   // 注意：不是 IntSetA 的子类型
    ...
}
...
IntSetA a = ...;
IntSetB b = ...;
a.isSubsetOf(b);      // ← 编译错误：IntSetB 不能转换为 IntSetA
```

**对象版本没有这个问题**，因为两者都实现了 `IntSet` 接口。

### 5.6 ADT 的性能优势

课件第 19 页给出反过来的例子：

> **ADT version can be more efficient**
> - `isSubsetOf` implemented as a loop over `contains`
> - O(n) calls to `contains`, each O(log n) → O(n log n)
> - Object version must go through the interface for every element

**具体分析**：

**ADT 版本**（假设 `IntSetA` 是一个有序数组）：

```java
boolean isSubsetOf(IntSetA other) {
    for (int x : this.elements) {
        if (!other.contains(x)) return false;   // 直接访问 other 的内部数组
    }
    return true;
}
```

因为 ADT 的 `isSubsetOf` 是**外部函数**，它可以**直接访问 `other` 的内部表示**（在同一个模块内），所以可以用双指针归并——**O(n)**。

**对象版本**：`this.isSubsetOf(other)` 只能通过 `other.contains(x)` 这个**接口**逐个查询——每次都是虚方法调用，无法利用「两者都是有序数组」这个信息，除非用 `instanceof` 判断（那就破坏了封装）。

**这就是「表达力 vs 性能」的经典权衡**：

| | 对象 | ADT |
|---|---|---|
| **互操作性** | 强（任何实现都能互换） | 弱（同实现才能互操作） |
| **性能** | 可能差（必须走接口） | 可能好（可直接访问内部） |
| **扩展性** | 强（加新实现不改旧代码） | 弱（加新类型要改所有操作） |
| **推理** | 难（动态分派，不知道跑哪个） | 易（静态可知） |

**这就是「表达式问题（expression problem）」的两种解法**：对象擅长「加新类型」（加一个 `Circle` 类，不改 `draw` 的调用者），ADT 擅长「加新操作」（加一个 `area` 函数，不改所有类型）。

课件第 20 页引用 Barbara Liskov（1993）关于 CLU 的论述，指出 ADT 的价值在于**用类型名隐藏表示**，让「表示可以独立于使用而改变」。

### 5.7 服务抽象

课件第 22 页：

> **Service abstraction**
> - A set of operations with a well-defined contract
> - Clients depend only on the contract, not the implementation
> - Enables **substitution** and **independent evolution**

**「服务」这个词的选择很讲究**：它强调对象是**为别人提供能力**的，而不是「数据的容器」。这与 [[15-214-07-Design-Patterns]] 里的「面向接口编程」是同一件事，但视角不同——「服务」强调的是**契约**与**可替换性**。

**Emerald 的例子**（第 23 页）：Emerald 是 1980 年代的一个分布式 OO 语言，它的核心洞察是：**分布式系统中的「对象」天然就是「远程服务」**——你调用一个对象的方法，可能实际上是在另一台机器上执行。所以 OO 的「消息发送」模型**天然适合分布式**。

这与 [[15-214-20-Distributed-Systems-Part1]] 的 RPC 概念直接对应：**方法调用 = 消息发送 = 远程过程调用**。

### 5.8 Widget 与 CompositeWidget：一个具体的服务抽象

课件第 25–26 页给出 GUI 组件的经典设计：

```java
abstract class Widget {
    abstract void draw();
    abstract void handleClick(int x, int y);
}

class CompositeWidget extends Widget {
    private List<Widget> children = new ArrayList<>();

    void add(Widget w) { children.add(w); }

    @Override
    void draw() {
        for (Widget w : children) w.draw();        // 递归 + 动态分派
    }

    @Override
    void handleClick(int x, int y) {
        for (Widget w : children) w.handleClick(x, y);
    }
}
```

**这个设计的美妙之处**：

- `CompositeWidget` **既是** `Widget`（可以被放进另一个 `CompositeWidget`），**又包含** `Widget`（它的孩子）；
- 这是 [[15-214-07-Design-Patterns]] 里的 **Composite 模式**；
- `draw()` 的递归调用**不需要知道任何具体类型**——加一个 `Button`、`Slider`、`Canvas`，`CompositeWidget` 一行都不用改；
- 这就是**开放-封闭原则**的完美体现。

### 5.9 设计杠杆三要素

课件第 27 页：

> **Design leverage requires:**
> 1. **Nontrivial abstractions** — 非平凡的抽象（不只是 getter/setter）
> 2. **Modular extensibility** — 模块化的可扩展性（加新东西不改旧的）
> 3. **First-class interoperability** — 一等的互操作性（不同实现能直接互换）

**逐条解释**：

**(1) 非平凡的抽象**：一个只有 `getX()`/`setX()` 的类是「平凡的抽象」——它没有隐藏任何复杂度，只是把字段换了个名字。**真正的抽象要能隐藏复杂度、提供更高层的概念**（如 `CompositeWidget` 隐藏了「递归遍历子树」的复杂度）。

**(2) 模块化可扩展性**：加一个新类型/新功能时，**不需要修改已有代码**。这要求「变化点」被封装在接口后面。

**(3) 一等互操作性**：不同实现能**直接**互换使用，不需要适配器。这要求「接口是语言的一等公民」（Java 的 `interface`、Go 的 `interface`）。

**这三条合起来就是「设计杠杆」**：少量设计投入（定义好接口）→ 大量复用收益（所有实现都能组合、都能扩展、都能互换）。

### 5.10 框架：设计杠杆的极致

课件第 30 页引用 Ralph Johnson（1997）：

> **A framework is a reusable design of all or part of a system that is represented by a set of abstract classes and the way their instances interact.**
> - Frameworks give **10x** productivity gains (Johnson's estimate)

**框架 vs 库**：

| | 库（library） | 框架（framework） |
|---|---|---|
| **控制流** | 你调用库 | 框架调用你 |
| **复用单位** | 函数/类 | 架构/设计 |
| **扩展方式** | 传参数 | 继承/实现接口/注册回调 |
| **原则** | — | **好莱坞原则**：Don't call us, we'll call you |

**好莱坞原则**是框架的本质：**控制权反转（inversion of control）**。你写的是「被框架调用的代码」，而不是「调用框架的代码」。

**课件第 32 页的例子：Java Servlet**

```java
public class HelloServlet extends HttpServlet {
    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp)
            throws ServletException, IOException {
        resp.getWriter().println("Hello, world");
    }
}
```

**你从来不写 `main` 方法**——容器（Tomcat）负责监听端口、解析 HTTP、创建线程、调用你的 `doGet`。你只需要填一个「热 spot」。

**框架的「热 spot 与冷 spot」**：

- **Cold spots（冷点）**：框架固定的部分——HTTP 解析、线程管理、生命周期。你**不能**改。
- **Hot spots（热点）**：框架留给你填的部分——`doGet`、`doPost`、`init`、`destroy`。你**必须**填。

### 5.11 Linux 内核是 OO 框架

课件第 33–34 页给出一个惊人的例子：**Linux 内核不是用 OO 语言写的（是 C），但它是地道的 OO 框架**。

```c
struct file_operations {
    struct module *owner;
    loff_t (*llseek) (struct file *, loff_t, int);
    ssize_t (*read) (struct file *, char __user *, size_t, loff_t *);
    ssize_t (*write) (struct file *, const char __user *, size_t, loff_t *);
    int (*open) (struct inode *, struct file *);
    int (*release) (struct inode *, struct file *);
    // ... 约 20 个函数指针
};
```

**这就是一个「虚函数表（vtable）」**：

- `struct file_operations` 是**接口**（一组函数指针）；
- 每个文件系统（ext4、NTFS、proc）提供**自己的实现**；
- 内核在打开文件时，根据文件系统类型**填入不同的函数指针**——这就是**动态分派**；
- `open()` 系统调用最终调用 `file->f_op->open(inode, file)`——**运行期决定**。

课件引用 Robert Love（《Linux Kernel Development》作者）的说法：内核里有约 **100 个服务抽象**（`file_operations`、`inode_operations`、`net_device_ops`、`block_device_operations` 等）。

**这个例子的意义**：

1. **OO 不是语法，是设计思想**——C 语言没有 `class`，但可以实现完整的 OO 框架；
2. **设计杠杆的巨大威力**——Linux 支持几十种文件系统、上百种网卡，全部通过这 100 个抽象；
3. **「用不用 OO 语言」与「用不用 OO 设计」是两件事**。

### 5.12 「我可以自己造对象」的反驳

课件第 35 页回应一个常见反驳：

> **"I can build objects myself"**（我可以用函数指针自己造对象）
> - 是的，你可以——Linux 内核就这么做了
> - **但语言支持带来的是**：
>   - 类型检查（函数指针没有签名检查）
>   - 封装（C 的 struct 字段全是公开的）
>   - 语法支持（`obj.method()` vs `obj->ops->method(obj)`）
>   - 工具支持（IDE 的跳转、重构、自动补全）

**结论**：手工造对象是**可行的**，但语言支持让它变得**便宜、安全、可维护**。这与 [[15-214-23-Static-Analysis]] 里「注解让分析变便宜」是同一个论证结构——**机制的价值在于降低正确做事的成本**。

### 5.13 软件生态

课件第 36 页引用 Bosch（2009）关于软件生态系统的论述：现代软件的价值越来越来自**生态**（插件、第三方集成、开发者社区），而生态的基础是**稳定的接口**。

**Android 的 ContentProvider**（第 37 页）是一个典型例子：

```java
public class MyProvider extends ContentProvider {
    @Override
    public Cursor query(Uri uri, String[] projection, String selection,
                        String[] selectionArgs, String sortOrder) { ... }

    @Override
    public Uri insert(Uri uri, ContentValues values) { ... }

    @Override
    public int update(Uri uri, ContentValues values, String selection,
                      String[] selectionArgs) { ... }

    @Override
    public int delete(Uri uri, String selection, String[] selectionArgs) { ... }
}
```

**为什么这个设计重要？** 因为它让**任意应用的数据**都能被**任意其他应用**访问——联系人、日历、照片、音乐，全部通过同一套接口。这就是「一等互操作性」在**跨进程、跨应用**层面的体现。

**代价**：这套接口非常笨重（`Uri` + `Cursor` + `ContentValues`），远不如直接的对象访问优雅。**但它的笨重是刻意的**——它必须能跨越进程边界、跨越语言、跨越版本。这是「接口设计」的经典权衡：**越通用的接口越抽象，越抽象的接口越难用**。

### 5.14 ADT 与对象的结论

课件第 38 页给出总结：

> **ADTs vs Objects**
> - ADTs: 类型名 + 操作签名，操作是外部函数，表示被隐藏
> - Objects: 值 + 过程式接口，操作是方法，动态分派
> - **两者是正交的抽象机制，不是同一种东西的两个名字**
> - 现代语言常常**两者都用**（Java 的 `interface` + 泛型 + 函数式接口）

**关键洞察**：这不是「谁更好」的问题，而是「**用哪个工具解决哪类问题**」：

- 需要**加新类型**（图形、AST 节点、UI 组件）→ 用对象；
- 需要**加新操作**（编译器 pass、序列化器、分析器）→ 用 ADT/模式匹配；
- 需要**高性能**（数值计算、容器）→ 用 ADT（可直接访问内部）；
- 需要**跨实现互操作**（插件、生态）→ 用对象。

### 5.15 类型状态：从协议到类型

课件（`28-protocol-programming.pdf`）第 2 页给出第一个例子——**文件读取协议**：

```
        open()              read()
  Closed ──────→ Open ──────────→ Open
                   │
                   │ close()
                   ↓
                 Closed
```

**状态机**：

- 初始状态：`Closed`；
- `open()`：`Closed → Open`；
- `read()`：只在 `Open` 状态可用；
- `close()`：`Open → Closed`。

**在普通 Java 里，这个协议完全没有被检查**：

```java
FileReader r = new FileReader("f.txt");
r.close();
r.read();       // ← 编译通过，运行时抛 IOException
```

第 3 页给出第二个例子——**迭代器协议**：

```
  hasNext() → true  →  next() 可用
  hasNext() → false →  只能 remove() 或停止
  remove() 只能调用一次，且必须在 next() 之后
```

**这些都是「协议（protocol）」**：方法必须按某种顺序调用。

### 5.16 协议的实证研究

课件第 5 页引用 Beckman、Kim、Aldrich 在 ECOOP 2011 的研究：

> - 分析了 200 万行代码
> - **7% 的类型定义了协议**（相比之下，只有 2.5% 使用了泛型）
> - **13% 的类是某个协议的客户端**
> - **25% 的协议用于并发场景**

**这组数据的意义**：

1. **协议比泛型更常见**（7% vs 2.5%）——但语言对泛型的支持远好于对协议的支持；
2. **协议无处不在**（13% 的类是客户端）——说明这不是边缘特性；
3. **四分之一与并发相关**——协议错误在并发下后果更严重。

### 5.17 协议错误的真实代价

课件第 7 页给出两个证据：

**(1) ASP.NET 论坛分析**：75% 的帖子涉及**时序约束**（temporal constraints）——即「我该先调用哪个方法」「为什么这个状态不能这么做」。

**(2) Georgiev 等人（CCS 2012）的研究**：**SSL 证书验证**的错误——很多应用在验证证书时**跳过了关键步骤**（比如没有检查主机名、没有检查证书链），导致中间人攻击。这些错误的本质是**协议违规**：调用了 `SSL_get_peer_certificate()` 却忘了调用 `X509_check_host()`。

**这解释了为什么类型状态重要**：如果「必须先验证再使用」被编码进类型，编译器就能阻止这类错误——**而不是等到被攻击才发现**。

### 5.18 用户研究：协议问题占 71% 的时间

课件第 8–9 页引用一项用户研究：

> - 开发者 **71% 的时间**花在 4 类协议问题上：
>   - **当前状态是什么？**（24%）
>   - **这个状态下我能做什么？**（20%）
>   - **有哪些可用操作？**（24%）
>   - **如何转换到另一个状态？**（3%）

**这组数据的震撼之处**：**超过七成的开发时间花在「搞清楚对象现在处于什么状态、能做什么」上**。如果语言能直接表达「状态」，这些时间大部分可以省掉。

**注意第一项与第三项都是 24%**——「我在哪」和「我能做什么」是同一个问题的两面。这正是类型状态要回答的。

### 5.19 类型状态导向编程（Typestate-Oriented Programming）

课件第 11 页给出定义：

> **Typestate-oriented programming**
> - Objects have a **typestate** that changes over time
> - The typestate determines which methods can be called
> - State transitions are **explicit** in the type system
> - A method call may **change the object's type**

**核心思想**：**对象的类型不是固定的**——它会随着方法调用而改变。`ClosedFile.open()` 返回的不再是 `void`，而是一个 **`OpenFile`**。

**这与普通 OO 的根本区别**：

| | 普通 OO | 类型状态 OO |
|---|---|---|
| 对象类型 | 固定（`File` 永远是 `File`） | 可变（`ClosedFile` → `OpenFile`） |
| 非法调用 | 运行时异常 | **编译错误** |
| 状态 | 隐藏在字段里 | **显式在类型里** |
| 检查 | 靠文档/约定 | 靠类型系统 |

### 5.20 Plaid 语言

课件第 12–13 页介绍 **Plaid**（Aldrich 等人开发的研究语言）的语法：

```plaid
state ClosedFile = File with {
    method void open() [ClosedFile >> OpenFile];
}

state OpenFile = File with {
    method int read() [OpenFile];
    method void close() [OpenFile >> ClosedFile];
}
```

**语法解读**：

- `state ClosedFile = File with { ... }`：定义一个**状态** `ClosedFile`，它是 `File` 的一个变体，附加一些方法；
- `method void open() [ClosedFile >> OpenFile]`：`open()` 方法**要求**当前状态是 `ClosedFile`，**执行后**对象变成 `OpenFile`——这就是 `[旧状态 >> 新状态]` 的语法；
- `method int read() [OpenFile]`：`read()` 要求当前状态是 `OpenFile`，**不改变**状态（只有一个状态标注）；
- `method void close() [OpenFile >> ClosedFile]`：`close()` 把对象从 `OpenFile` 变回 `ClosedFile`。

**状态转换的实现**（第 13 页）：

```plaid
method void open() [ClosedFile >> OpenFile] {
    this <- OpenFile { fileResource = fopen(filename); };
}
```

**`this <- OpenFile { ... }`** 的语义：**把当前对象原地转换成 `OpenFile` 状态**，同时初始化新状态的字段 `fileResource`。注意这是**原地（in-place）** 转换——对象的身份不变，但它的类型变了。

**为什么这个设计优雅？** 因为它把「状态」从**隐式的字段值**变成了**显式的类型**：

- 你不需要写 `if (state == OPEN) throw new IllegalStateException()`；
- 编译器在你调用 `read()` 时就检查「当前类型是不是 `OpenFile`」；
- 如果类型不对，**编译失败**——零运行时开销。

### 5.21 为什么要把状态放进语言

课件第 14 页列出五条理由：

1. **世界是有状态的**——文件、连接、事务、UI 都有生命周期；
2. **语言影响思维（Sapir-Whorf 假说）**——如果语言有「状态」概念，你就会自然地按状态思考；
3. **更好的规范与验证**——状态机是可以被形式化检查的；
4. **表达力**——用类型表达状态，比用注释表达更精确；
5. **推理更简单**——每个状态只需考虑该状态下的行为，而不是「所有字段的所有组合」。

### 5.22 状态检查的例子

课件第 16 页给出一个**辅助方法**的例子：

```plaid
method void openHelper(ClosedFile>>OpenFile aFile) {
    aFile.open();
    // 此处 aFile 的类型已经是 OpenFile
    aFile.read();       // ✓ 合法
}
```

**`ClosedFile>>OpenFile aFile`** 是一个**参数类型标注**：它声明「这个参数进入时必须是 `ClosedFile`，退出时（如果方法正常返回）会变成 `OpenFile`」。

**这个标注的作用**：

- 调用者必须传一个 `ClosedFile`；
- 调用者**知道**方法返回后 `aFile` 变成了 `OpenFile`（如果它是别名的话）；
- 方法内部可以安全地假设「开始时是 Closed、结束时是 Open」。

**这就是「类型状态的方法签名」**——它把「前置状态」与「后置状态」都写进了类型，就像契约的前置/后置条件（参见 [[15-214-05-Object-Contracts-and-Exceptions]]），但是**机器可检查**的。

### 5.23 权限：解决别名问题

课件第 17 页介绍 **permissions（权限）**：

| 权限 | 含义 | 能做什么 |
|---|---|---|
| **unique** | 唯一引用，没有别名 | 读、写、**转移所有权**、**分裂**成其他权限 |
| **immutable** | 只读，可自由别名 | 只能读，永远不能写 |
| **shared** | 可读写，但可能有别名 | 读、写（但需要同步，因为可能有别人也在访问） |
| **full** | 默认权限，可读可写可有别名 | 读、写（最弱，无法保证任何事） |
| **pure** | 无副作用 | 只能读不可变数据，不能写任何东西 |

**为什么需要权限？** 回到 [[15-214-24-Static-Analysis-for-Concurrency]] 的**别名问题**：如果两个引用指向同一个对象，你就无法静态地知道「谁在什么时候访问它」。权限系统通过**限制引用的能力**来解决这个问题：

- 如果某个引用是 `unique`，那么**只有它能访问这个对象**——没有竞态；
- 如果某个引用是 `immutable`，那么**没人能改它**——没有竞态；
- 如果某个引用是 `shared`，那么**可能有人并发访问**——需要同步。

### 5.24 权限分裂规则

课件第 18 页：

> **Permission splitting**
> - `unique` → `full` + `shared`（把唯一引用分成两个，一个可读写、一个共享）
> - `unique` → `full` + `immutable`（分成一个可写、一个只读）
> - `shared` → `shared` + `shared`（共享引用可以复制）
> - `X` → `X` + `pure`（任何权限都可以额外获得一个「只读且无副作用」的视图）

**逐条理解**：

**(1) `unique → full + shared`**

你有一个唯一引用，想把它交给别人用（但保留自己的访问权）。分裂后：

- 你自己拿 `full`（可以读写）；
- 别人拿 `shared`（也可以读写，但**知道**可能有别名，所以必须同步）。

**这什么时候有用？** 例如把一个缓冲区交给一个工作线程处理，同时自己保留引用。

**(2) `unique → full + immutable`**

你有一个唯一引用，想让别人**只读**访问：

- 你自己保留 `full`（可写）；
- 别人拿 `immutable`（只读）——**他不需要同步**，因为他知道没人会改（在他持有期间）。

**这是「读写分离」的类型级保证**——比 `Collections.unmodifiableList()` 更强，因为后者只是运行时包装，而权限是**编译期**的。

**(3) `shared → shared + shared`**

共享引用可以任意复制——因为它本来就允许多个别名。

**(4) `X → X + pure`**

任何引用都可以额外获得一个 `pure` 视图：**只读、无副作用**。这意味着「通过这个视图，你只能调用不修改任何状态的方法」。

**为什么这条重要？** 因为它让你能把「只读访问」传给不信任的代码（如回调、插件），而**不用担心它们修改你的数据**。

### 5.25 用权限构造数据流图

课件第 19–21 页展示如何用权限描述**并发数据流**：

```plaid
method unique Data createData();
method void print(immutable Data d);

split QG: produce(q) || consume(q);
```

**逐行解读**：

- `method unique Data createData();`：创建一个 `Data` 对象，返回**唯一**引用——调用者是唯一持有者；
- `method void print(immutable Data d);`：打印一个 `Data`，参数是 `immutable`——**print 保证不修改**，且可以被多个线程同时调用；
- `split QG: produce(q) || consume(q);`：**分裂**引用 `q`，让 `produce` 和 `consume` 分别在**两个并行分支**里使用。

**`split ... || ...` 的语义**：把当前执行流分成两个**并行**的分支，各自持有一部分权限。这就是**用类型系统描述并发**：

- 生产者拿 `full`（可写）；
- 消费者拿 `immutable`（只读）；
- **类型系统保证**：生产者不会读到消费者正在改的东西（因为消费者不能改），消费者不会看到半成品（因为……嗯，这里需要额外的同步，权限只保证不冲突，不保证顺序）。

**这个设计的价值**：它让「这个对象在哪些线程之间流动、每个线程有什么能力」变成**类型的一部分**，可以在编译期检查。这与 [[15-214-19-Concurrency-Part3]] 的「不可变性 + 线程封闭」是同一套思想，但用类型强制。

### 5.26 用户实验：Plaiddoc 快 2 倍

课件第 23 页给出一个用户实验的结果：

> - 参与者用 Plaid 写文档处理任务
> - **Plaiddoc（带类型状态）比对照组快 2 倍**
> - **p = 0.0003**（统计显著）

**这个结果的意义**：类型状态不只是「更安全」，它还**更快**——因为开发者不需要花时间想「现在是什么状态」「能不能调这个方法」（回顾 5.18 节的 71%）。**类型系统承担了这些心智负担**。

### 5.27 DSL：为什么单体语言不可持续

课件（`28-dsls-in-wyvern.pdf`）第 2–6 页给出一堆**专用记号**的例子：

- **数学**：`∑`、`∫`、矩阵、下标；
- **列表字面量**：`[1, 2, 3]`；
- **正则表达式**：`[a-z]+@[a-z]+\.com`；
- **SQL**：`SELECT * FROM users WHERE age > 18`；
- **HTML 模板**：`<div class="x">{{ name }}</div>`。

**这些记号的共同点**：它们**在自己的领域里极其简洁**，但**用通用语言写就极其笨拙**。写 SQL 你要拼字符串（容易注入、没有语法检查）；写正则你要调 `Pattern.compile("...")`（转义地狱）；写 HTML 你要 `new Div().attr("class", "x")`（完全失去结构感）。

**课件第 8 页的核心论点**：

> **Monolithic languages are unsustainable**
> - A language that tries to support every domain becomes huge and complex
> - Each domain has its own experts, its own notation, its own semantics
> - **No single language can be best at everything**

**这是「通用语言 vs DSL」的根本张力**：通用语言想「什么都能写」，但结果往往是「什么都写不好」。DSL 想「一件事写得极好」，但结果是「每件事都要学一门新语言」。

### 5.28 内部可扩展语言

课件第 9 页提出一个折中方案：

> **Internally extensible languages**
> - The language provides mechanisms for users to add new syntax and semantics
> - Examples: Lisp macros, Racket's `#lang`, Scala's implicits/parser combinators

**Lisp 的宏**是最早的答案：因为 Lisp 的代码就是数据（homoiconicity），所以宏可以**任意**改写语法。Racket 把它发展成 `#lang`——每门 DSL 是一个独立的语言模块。

**但这些方案都有问题**：

- **Lisp 宏**：太强大，导致每段代码都可能是「另一种语言」，可读性差；
- **Racket `#lang`**：需要整个文件用一种语言，无法在同一个文件里混用；
- **Scala 的隐式/解析组合子**：语法扩展有限，且容易产生「隐式地狱」。

### 5.29 表达力 vs 安全性

课件第 10 页给出核心权衡：

> **Expressiveness vs Safety**
> - More expressive syntax → more power, but harder to check
> - More restricted syntax → easier to check, but less useful

**具体表现**：

- 如果 DSL 的语法完全自由（像 Lisp 宏），那么**类型检查器无法理解**这些语法——它只看到宏展开后的代码；
- 如果 DSL 的语法完全固定（像 SQL 字符串），那么**IDE 无法提供补全**，错误只能在运行时发现。

### 5.30 Sugar* 的问题：语法会互相干扰

课件第 11 页指出一个具体的失败案例：

> **Sugar* library extensions interfere with each other**
> - Each library defines its own syntax
> - The parser cannot tell which syntax applies where
> - Result: ambiguity, conflicts, unpredictable behavior

**具体场景**：假设你有一个「正则字面量」库和一个「SQL 字面量」库，两者都用 `[...]` 作为分隔符。那么代码里的 `[...]` 到底是正则还是 SQL？解析器无法判断。

**这就是「语法污染」**：每加一个库，就多一套语法规则，它们可能：

- 与已有语法冲突（同一记号有两种含义）；
- 与未来语法冲突（你现在选的记号，别人以后也想用）；
- 让错误信息变得无法理解（「这个 `[` 到底是哪个库的？」）。

### 5.31 Wyvern 的答案：TSL

课件第 12 页给出核心方案：

> **Type-Specific Languages (TSL)**
> - Syntax is **associated with a type**
> - The type determines how to parse the syntax
> - Multiple DSLs can coexist **without conflict**

**核心思想**：**语法不是全局的，而是局部的**——它绑定到某个**类型**上。当你写一段 `regex` 字面量时，编译器知道它的类型是 `Regex`，于是用 `Regex` 的语法规则解析它。另一个库的 `[...]` 属于 `SQL` 类型，用另一套规则。

**这就解决了「语法冲突」**：因为**同一个记号在不同类型上下文里可以有不同含义**，而类型是由**上下文**决定的（就像方法重载）。

### 5.32 分隔符

课件第 14 页列出 Wyvern 支持的分隔符：

| 分隔符 | 例子 | 用途 |
|---|---|---|
| **反引号** | `` `regex` `` | 短小的内联 DSL |
| **单引号** | `'sql'` | 同上，另一种风格 |
| **花括号** | `{ ... }` | 块状 DSL（如 HTML 模板） |
| **方括号** | `[ ... ]` | 列表/集合类 DSL |
| **尖括号** | `< ... >` | 标记语言类 DSL |
| **波浪号 `~`** | `~` 布局 | 布局敏感的 DSL（如 Python 风格的缩进） |

**为什么需要多种分隔符？** 因为不同的 DSL 有不同的「自然边界」：

- 正则表达式很短，用反引号合适；
- HTML 模板有多行嵌套，用花括号合适；
- 布局敏感的 DSL（如 YAML）需要缩进，用 `~` 标记。

### 5.33 两阶段解析

课件第 15–16 页给出 Wyvern 的核心机制——**两阶段解析（two-phase parsing）**：

**Phase I：顶层解析（top-level parsing）**

- 用**布局敏感文法（layout-sensitive grammar）** 解析整个文件；
- 但**遇到 DSL 分隔符时，不解析内部**——把它当作一个「黑盒」，只记录它的位置与分隔符类型；
- 这样，**主语言的解析不受 DSL 影响**。

**Phase II：类型检查与 DSL 解析**

- 在类型检查阶段，确定每个 DSL 块的**期望类型**；
- 期望类型来自三个来源：
  1. **显式注解**（`Regex r = `...`;`）；
  2. **函数签名**（`void f(Regex r)` 的参数类型）；
  3. **类型传播**（从上下文推断）。
- 知道了期望类型，就用该类型关联的 **metaobject** 来解析 DSL 内容。

**这个设计的关键**：**解析被推迟到类型信息可用时**。这解决了「语法依赖类型」的问题——传统解析器必须在**不知道类型**的情况下解析，所以无法支持「同一个记号在不同类型下有不同语法」。

### 5.34 Metaobject：把 parser 与类型关联

课件第 17–18 页给出 `casetype` 与 `metaobject` 的语法：

```wyvern
casetype Regex

def regexParser : Parser = ...

metaobject regexParser for Regex
```

**逐行解读**：

- `casetype Regex`：声明一个**类型** `Regex`（`casetype` 是 Wyvern 里定义类型的语法）；
- `def regexParser : Parser = ...`：定义一个**解析器**（一个值）；
- `metaobject regexParser for Regex`：把 `regexParser` **关联**到类型 `Regex`——从此，所有期望类型为 `Regex` 的 DSL 块都用 `regexParser` 解析。

**这个设计的优雅之处**：

- **解析器是普通的值**——可以传递、组合、从库里导入；
- **关联是显式的**——`metaobject ... for ...` 一行代码就说清了「谁解析谁」；
- **可以有多套实现**——不同库可以提供不同的 `Regex` 解析器（一个严格、一个宽松），由导入决定用哪个。

### 5.35 TSL 的四大好处

课件第 19 页：

> **Four benefits of TSLs**
> 1. **Modularity and safe composition** — 多个 DSL 可以安全共存
> 2. **Recognizability** — 语法一眼可辨（看到反引号就知道是 DSL）
> 3. **Simplicity** — 主语言不需要为每个领域加特性
> 4. **Flexibility** — 库作者可以自由设计语法

**逐条展开**：

**(1) 模块化与安全组合**：这是 TSL 的核心卖点。因为语法绑定到类型，不同 DSL 的语法**永远不会冲突**——即使它们用同一个分隔符。而且 DSL 的解析器是**库的一部分**，可以独立版本化、独立测试。

**(2) 可识别性（recognizability）**：看到 `` `...` `` 就知道「这是 DSL」，不会与主语言混淆。这对**代码审查**与**工具支持**都很重要——IDE 可以高亮、可以跳转、可以补全。

**(3) 简单性**：主语言（Wyvern）不需要内置 SQL、正则、HTML 的语法——它只需要提供**扩展机制**。这让语言核心保持小而稳定。

**(4) 灵活性**：库作者可以**为自己的领域设计最自然的语法**，而不是被迫用主语言的表达方式。这对**领域专家**（不是程序员）特别有价值——他们可以直接读写自己熟悉的记号。

### 5.36 三份讲义的共同主题

把 `28-why-objects.pdf`、`28-protocol-programming.pdf`、`28-dsls-in-wyvern.pdf` 串起来：

```
对象的价值（why-objects）
   ↓ 动态分派 + 服务抽象 + 设计杠杆
   ↓ 但对象有「协议」这个未被类型系统覆盖的维度
类型状态（protocol-programming）
   ↓ 把「状态」放进类型 → 编译期检查协议
   ↓ 用「权限」解决别名 → 支持并发推理
   ↓ 但表达协议需要「领域特定的语法」
类型特定语言（dsls-in-wyvern）
   ↓ 语法绑定到类型 → 多 DSL 安全共存
   ↓ 两阶段解析 → 类型信息可用后再解析
```

**共同主线**：**让「设计意图」从注释和文档，变成机器可检查的东西**。

- 对象：把「数据 + 操作」的意图编码进类；
- 类型状态：把「协议」的意图编码进类型；
- 权限：把「谁能访问什么」的意图编码进引用类型；
- TSL：把「领域记号」的意图编码进类型关联的语法。

这条主线与 [[15-214-23-Static-Analysis]] 的「规约 + 检查」完全一致——**静态分析的终极形态，是让语言本身能表达并检查设计意图**。

## 6. 代码示例

### 6.1 官方课程代码

**`28-why-objects.pdf` 第 13 页：脆弱基类（fragile base class）**

```java
class CachedSizeList extends List {
    private int cachedSize;
    @Override
    public void add(Object o) {
        super.add(o);
        cachedSize++;
    }
}
```

课件用它说明：如果父类 `List` 的 `addAll` 内部调用了 `add`，那么子类的 `cachedSize` 会被**重复计数**——因为 `addAll` 的每一次 `add` 都会触发子类的覆写。这就是「脆弱基类」：**子类的正确性依赖于父类的实现细节**。

**`28-why-objects.pdf` 第 17 页：对象版的 `IntSet`**

```java
interface IntSet {
    boolean contains(int x);
    boolean isSubsetOf(IntSet other);
}
```

**`28-why-objects.pdf` 第 18 页：ADT 版的 `IntSetA`**

```java
interface IntSetA {
    boolean contains(int x);
    boolean isSubsetOf(IntSetA other);
}
```

**`28-why-objects.pdf` 第 25 页：Widget / CompositeWidget**

```java
abstract class Widget {
    abstract void draw();
}

class CompositeWidget extends Widget {
    private List<Widget> children;
    void draw() {
        for (Widget w : children) w.draw();
    }
}
```

**`28-why-objects.pdf` 第 32 页：Java Servlet**

```java
public class HelloServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp)
            throws ServletException, IOException {
        resp.getWriter().println("Hello, world");
    }
}
```

**`28-why-objects.pdf` 第 33–34 页：Linux 的 `file_operations`**

```c
struct file_operations {
    struct module *owner;
    loff_t (*llseek) (struct file *, loff_t, int);
    ssize_t (*read) (struct file *, char __user *, size_t, loff_t *);
    ssize_t (*write) (struct file *, const char __user *, size_t, loff_t *);
    int (*open) (struct inode *, struct file *);
    int (*release) (struct inode *, struct file *);
};
```

**`28-protocol-programming.pdf` 第 12 页：Plaid 的状态定义**

```plaid
state ClosedFile = File with {
    method void open() [ClosedFile >> OpenFile];
}

state OpenFile = File with {
    method int read() [OpenFile];
    method void close() [OpenFile >> ClosedFile];
}
```

**`28-protocol-programming.pdf` 第 13 页：原地状态转换**

```plaid
method void open() [ClosedFile >> OpenFile] {
    this <- OpenFile { fileResource = fopen(filename); };
}
```

**`28-protocol-programming.pdf` 第 16 页：带状态迁移的参数**

```plaid
method void openHelper(ClosedFile>>OpenFile aFile) {
    aFile.open();
    aFile.read();
}
```

**`28-protocol-programming.pdf` 第 19–21 页：权限与并行分裂**

```plaid
method unique Data createData();
method void print(immutable Data d);

split QG: produce(q) || consume(q);
```

**`28-dsls-in-wyvern.pdf` 第 17–18 页：casetype 与 metaobject**

```wyvern
casetype Regex

def regexParser : Parser = ...

metaobject regexParser for Regex
```

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：用 Java 的「状态对象」模拟类型状态（运行时检查版）。**

```java
/** 普通 OO 写法：状态藏在字段里，错误在运行时才暴露 */
class NaiveFile {
    private boolean open = false;

    void open() { open = true; }

    int read() {
        if (!open) throw new IllegalStateException("文件未打开");
        return 42;
    }

    void close() { open = false; }
}

/** 类型状态写法：状态变成类型，错误在编译期暴露 */
interface TFile {
    TOpenFile open();
}

interface TOpenFile {
    int read();
    TClosedFile close();
}

interface TClosedFile {
    TOpenFile open();
}

class RealFile implements TFile, TOpenFile, TClosedFile {
    private final String name;
    private boolean open = false;

    RealFile(String name) { this.name = name; }

    @Override public TOpenFile open() {
        open = true;
        return this;
    }

    @Override public int read() {
        if (!open) throw new IllegalStateException("不该发生");
        return 42;
    }

    @Override public TClosedFile close() {
        open = false;
        return this;
    }
}

public class TypestateInJava {
    public static void main(String[] args) {
        TFile f = new RealFile("data.txt");
        TOpenFile o = f.open();          // 现在类型是 TOpenFile
        int x = o.read();                // ✓ 合法
        TClosedFile c = o.close();       // 现在类型是 TClosedFile
        // c.read();                     // ← 编译错误：TClosedFile 没有 read()
        System.out.println(x);
    }
}
```

**这个「用接口模拟状态」的技巧在 Java 里很常用**（例如 `java.nio.channels` 的部分 API）。它**不是真正的类型状态**——因为 `RealFile` 同时实现了三个接口，你可以用 `instanceof` 绕过去；但它已经能捕获大部分错误，而且**零运行时开销**。

**示例 B：用 Builder 模式演示「协议」的另一种表达。**

```java
/** 用「分阶段接口」强制调用顺序：必须先 setHost 才能 setPort，必须先 build 才能用 */
public class StagedBuilder {
    interface HostStage { PortStage host(String h); }
    interface PortStage { BuildStage port(int p); }
    interface BuildStage { Client build(); }

    static class Client {
        final String host; final int port;
        Client(String h, int p) { host = h; port = p; }
        public String toString() { return host + ":" + port; }
    }

    static class Builder implements HostStage, PortStage, BuildStage {
        private String host; private int port;

        @Override public PortStage host(String h) { host = h; return this; }
        @Override public BuildStage port(int p) { port = p; return this; }
        @Override public Client build() { return new Client(host, port); }
    }

    public static void main(String[] args) {
        Client c = new Builder().host("example.com").port(8080).build();
        System.out.println(c);       // example.com:8080

        // new Builder().port(8080);            // ← 编译错误：PortStage 不可用
        // new Builder().host("x").build();     // ← 编译错误：缺少 port
    }
}
```

**这是 Java 里最实用的「类型状态」技巧**：每个阶段返回一个**只暴露下一步**的接口。它在 [[15-214-07-Design-Patterns]] 的 Builder 模式基础上，加上了**顺序强制**——这正是协议检查的轻量版。

**示例 C：权限的 Java 近似——用 `Collections.unmodifiableList` 模拟 `immutable`。**

```java
import java.util.*;

public class PermissionDemo {
    /** 模拟 unique：创建者独占，可以安全地「转移」给消费者 */
    static List<String> createData() {
        return new ArrayList<>(List.of("a", "b", "c"));
    }

    /** 模拟 immutable：只读视图，多线程可安全共享 */
    static void print(List<String> data) {
        for (String s : data) System.out.print(s + " ");
        System.out.println();
    }

    public static void main(String[] args) {
        List<String> unique = createData();            // 我是唯一持有者

        // 分裂：unique → full + immutable
        List<String> full = unique;                     // 我保留可写权限
        List<String> immutableView = Collections.unmodifiableList(unique);

        Thread producer = new Thread(() -> full.add("d"));
        Thread consumer = new Thread(() -> print(immutableView));
        producer.start(); consumer.start();

        try { producer.join(); consumer.join(); } catch (InterruptedException e) { }
        // 注意：这里仍可能抛 ConcurrentModificationException！
        // 因为 unmodifiableList 只是「禁止通过这个视图修改」，
        // 并不阻止「别人通过 full 修改」——这正是 Java 与 Plaid 的差距。
    }
}
```

**这个例子的教育价值在于「它不安全」**：`Collections.unmodifiableList` 只提供**运行时的写保护**，不提供**并发安全**。真正的 `immutable` 权限（Plaid）要求：

1. 视图**不能**被转换成可写视图；
2. **没有任何**其他可写别名存在（这需要 `unique → full + immutable` 的分裂来保证）。

Java 的类型系统表达不了第 2 点——所以这个例子只能「近似」。**这就是为什么需要专门的权限系统**。

**示例 D：一个极简的 TSL 原型——按「期望类型」选择解析器。**

```java
import java.util.*;
import java.util.function.Function;

/**
 * 模拟 Wyvern 的两阶段解析：
 * Phase I 只识别分隔符与位置；Phase II 按「期望类型」选择解析器。
 */
public class MiniTSL {

    /** Phase II：类型 → 解析器 */
    static final Map<Class<?>, Function<String, Object>> METAOBJECTS = new HashMap<>();

    static {
        // Regex 类型的解析器：把字面量编译成 Pattern
        METAOBJECTS.put(Regex.class, src -> new Regex(src));

        // Sql 类型的解析器：把字面量变成一条「查询对象」
        METAOBJECTS.put(Sql.class, src -> new Sql(src));
    }

    static class Regex {
        final String pattern;
        Regex(String p) { this.pattern = p; }
        boolean matches(String s) { return s.matches(pattern); }
        public String toString() { return "Regex(" + pattern + ")"; }
    }

    static class Sql {
        final String query;
        Sql(String q) { this.query = q; }
        public String toString() { return "Sql(" + query + ")"; }
    }

    /** Phase I：扫描出所有 DSL 块（这里用 `...` 作为分隔符） */
    static List<String> phase1(String source) {
        List<String> blocks = new ArrayList<>();
        int i = 0;
        while (i < source.length()) {
            int start = source.indexOf('`', i);
            if (start < 0) break;
            int end = source.indexOf('`', start + 1);
            if (end < 0) break;
            blocks.add(source.substring(start + 1, end));
            i = end + 1;
        }
        return blocks;
    }

    /** Phase II：按期望类型解析每个块 */
    @SuppressWarnings("unchecked")
    static <T> T phase2(String src, Class<T> expectedType) {
        Function<String, Object> parser = METAOBJECTS.get(expectedType);
        if (parser == null) throw new IllegalArgumentException("没有为 " + expectedType + " 注册解析器");
        return (T) parser.apply(src);
    }

    public static void main(String[] args) {
        String source = "val r = `[a-z]+@[a-z]+\\.com`; val q = `SELECT * FROM users`;";

        // Phase I：只知道有两个块，不知道它们是什么
        System.out.println("Phase I 找到 " + phase1(source).size() + " 个 DSL 块");

        // Phase II：类型信息可用后，才决定用哪个解析器
        Regex r = phase2("[a-z]+@[a-z]+\\.com", Regex.class);
        Sql q = phase2("SELECT * FROM users", Sql.class);

        System.out.println(r + " → matches(\"a@b.com\") = " + r.matches("a@b.com"));
        System.out.println(q);
    }
}
```

**这个原型的要点**：

- **Phase I 完全不知道 DSL 的语法**——它只切分出块的位置；
- **Phase II 才根据期望类型选择解析器**——这就是「语法绑定到类型」；
- 因为解析器是**普通的值**（`Function<String, Object>`），它们可以来自**不同的库**，互不干扰。

**真实的 Wyvern 要复杂得多**（布局敏感的顶层文法、类型传播、增量解析），但这个两阶段结构是它的核心。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| 对象（object） | ADT（抽象数据类型） | 前者操作是**方法**、动态分派、擅长加新类型；后者操作是**外部函数**、静态分派、擅长加新操作 |
| 封装 | OO | 封装是「隐藏内部表示」，模块也能做到；OO 的核心是**动态分派** |
| 继承 | 复用 | 继承是**类型关系 + 实现复用**；复用可以用组合、委托、泛型实现，不一定要继承 |
| 库（library） | 框架（framework） | 你调用库；框架调用你（好莱坞原则） |
| 热 spot | 冷 spot | 前者是框架留给你的扩展点；后者是框架固定、你不能改的部分 |
| 类型（type） | 类型状态（typestate） | 前者是「这个对象是什么」；后者是「这个对象现在处于协议中的哪一步」 |
| 协议（protocol） | 接口（interface） | 前者约束**调用顺序**（时序）；后者约束**有哪些方法**（结构） |
| unique 权限 | immutable 权限 | 前者「只有一个引用」但**可以改**；后者「不能改」但**可以有很多引用** |
| shared 权限 | full 权限 | 前者「知道有别名，必须同步」；后者「不知道有没有别名，最弱」 |
| 权限分裂 | 类型转换 | 前者把**一个**引用变成**多个更弱的**引用（unique → full + immutable）；后者改变引用的**静态类型**，不改变别名关系 |
| DSL | TSL | 前者是「领域特定语言」的通称；后者是「语法**绑定到某个类型**」的 DSL，可安全组合 |
| Phase I 解析 | Phase II 解析 | 前者用主语言文法切出 DSL 块（不解析内部）；后者在类型信息可用后，用 metaobject 解析内部 |

## 8. 对应原版讲义

本讲由三份 PDF 组成。

### 8.1 `28-why-objects.pdf`

- **PDF 相对路径**：`90-原始PDF/15-214/slides/28-why-objects.pdf`
- **总页数**：39 页
- **重点页码**：
  - 第 2–3 页：OOP 的普及度数据（TIOBE 前十中 6–8 个）
  - 第 4 页：Stepanov 对 OOP 的批评
  - 第 6 页：Joe Armstrong 的「香蕉与大猩猩」引语
  - 第 9–10 页：封装与继承都不是 OO 独有（Go 无继承、Self 用委托）
  - 第 13 页：脆弱基类示例（`CachedSizeList extends List`）
  - 第 15 页：动态分派是 OO 的核心
  - 第 16 页：Cook 2009「对象是导出一个过程式接口的值」、autognostic、Reynolds 1975
  - 第 17 页：对象版 `IntSet`（可互操作）
  - 第 18 页：ADT 版 `IntSetA`（编译错误示例）
  - 第 19 页：ADT 的性能优势（O(n) vs O(n) 次 `contains`）
  - 第 20 页：Liskov 1993 关于 CLU 的引语
  - 第 22 页：服务抽象的定义
  - 第 23 页：Emerald 分布式对象
  - 第 25–26 页：Widget / CompositeWidget
  - 第 27 页：设计杠杆三要素
  - 第 30 页：框架的定义（Johnson 1997，10x 生产率）
  - 第 32 页：Java Servlet 接口
  - 第 33–34 页：Linux 是 OO 框架（`file_operations`、约 100 个服务抽象、Robert Love 引语）
  - 第 35 页：「我可以自己造对象」的反驳
  - 第 36 页：软件生态（Bosch 2009）
  - 第 37 页：Android ContentProvider
  - 第 38 页：ADT vs Objects 的结论
  - 第 39 页：总结
- **原始链接**：https://www.cs.cmu.edu/~aldrich/214/slides/28-why-objects.pdf
- **说明**：这是 Onward! Essay 2013 的演讲稿版本。

### 8.2 `28-protocol-programming.pdf`

- **PDF 相对路径**：`90-原始PDF/15-214/slides/28-protocol-programming.pdf`
- **总页数**：24 页
- **重点页码**：
  - 第 2 页：`FileReader` 的 read/close 协议状态机（open/closed）
  - 第 3 页：`Iterator` 的 hasNext/next/remove 协议
  - 第 5 页：实证研究（Beckman/Kim/Aldrich, ECOOP 2011：2M LOC、7% 类型定义协议 vs 2.5% 用泛型、13% 类是协议客户端、25% 协议用于并发）
  - 第 7 页：问题证据（ASP.NET 论坛 75% 涉及时序约束；Georgiev CCS'12 的 SSL 证书验证）
  - 第 8–9 页：用户研究（71% 时间用于 4 类协议问题：当前状态 24%、状态能力 20%、可用操作 24%、状态转换）
  - 第 11 页：typestate-oriented programming 定义
  - 第 12 页：Plaid 的 `state ClosedFile = File with { ... }`
  - 第 13 页：`this <- OpenFile { fileResource = fopen(filename); }`
  - 第 14 页：为何把状态放进语言（世界有状态、Sapir-Whorf、更好的规范与验证、表达力、推理更简单）
  - 第 16 页：`method void openHelper(ClosedFile>>OpenFile aFile)` 检查示例
  - 第 17 页：权限（unique / immutable / shared / full / pure）
  - 第 18 页：权限分裂规则
  - 第 19–21 页：用权限构造数据流图（`createData` / `print` / `split QG: produce(q) || consume(q);`）
  - 第 23 页：用户实验（Plaiddoc 快 2 倍，p = 0.0003）
  - 第 24 页：总结
- **原始链接**：https://www.cs.cmu.edu/~aldrich/214/slides/28-protocol-programming.pdf
- **说明**：Plaid 语言与类型状态研究，与本课程作者 Aldrich 的研究直接相关。

### 8.3 `28-dsls-in-wyvern.pdf`

- **PDF 相对路径**：`90-原始PDF/15-214/slides/28-dsls-in-wyvern.pdf`
- **总页数**：19 页
- **重点页码**：
  - 第 2–6 页：专用记号的例子（数学、列表字面量、正则、SQL、HTML 模板）
  - 第 7 页：Wyvern 的目标（单一静态类型语言内做安全 web/mobile）
  - 第 8 页：单体语言不可持续
  - 第 9 页：内部可扩展语言（Lisp 宏、Racket `#lang`）
  - 第 10 页：表达力 vs 安全性
  - 第 11 页：Sugar* 库扩展语法会互相干扰
  - 第 12 页：解决方案 TSL（语法与类型关联）
  - 第 14 页：分隔符（反引号/单引号/花括号/方括号/尖括号/`~` 布局）
  - 第 15 页：Phase I 顶层解析（布局敏感文法，TSL 内不解析）
  - 第 16 页：Phase II 类型检查与 DSL 解析（显式注解/函数签名/类型传播）
  - 第 17–18 页：`casetype Regex` + `metaobject` 关联 parser
  - 第 19 页：四大好处（模块化与安全组合、可识别性、简单、灵活）
- **原始链接**：https://www.cs.cmu.edu/~aldrich/214/slides/28-dsls-in-wyvern.pdf
- **说明**：作者为 Cyrus Omar 等，Wyvern 语言研究。

## 9. 对应视频

未找到官方公开录像。

## 10. 本节复习

- 封装、继承、复用都**不是** OO 独有；**动态分派**才是核心（运行期选择实现、支持独立演化）。
- 对象 = 导出一个过程式接口的值；方法闭包了 `this`；对象「自我解释」（autognostic）。
- 对象 vs ADT：前者擅长**加新类型 + 互操作**，后者擅长**加新操作 + 性能**；两者正交。
- 设计杠杆三要素：非平凡抽象、模块化可扩展性、一等互操作性。
- 框架 = 好莱坞原则（Don't call us）；有热 spot（你填）与冷 spot（框架定）；Linux 内核用 C 实现了地道的 OO 框架。
- 类型状态：对象在协议中的位置成为**类型的一部分**；非法调用变编译错误；Plaid 用 `[ClosedFile >> OpenFile]` 表达迁移。
- 权限：unique / immutable / shared / full / pure；分裂规则 `unique → full + immutable` 等；用权限可描述并发数据流。
- TSL：语法**绑定到类型**，多个 DSL 安全共存；两阶段解析（Phase I 切块、Phase II 按期望类型解析）；`metaobject` 把 parser 关联到类型。
- 三份讲义的共同主线：**把设计意图从注释变成机器可检查的东西**。

## 11. 自我检查

**Q1.** 请说明为什么「封装」和「继承」都不足以定义面向对象，并举出反例语言。那么 OO 的核心是什么？

**Q2.** 下面两个设计，哪个更「对象」、哪个更「ADT」？分别在什么场景下更优？

```java
// 设计 A
interface Shape { double area(); }

// 设计 B
class ShapeOps {
    static double area(Circle c) { return Math.PI * c.r * c.r; }
    static double area(Rect r) { return r.w * r.h; }
}
```

**Q3.** 请解释 `split QG: produce(q) || consume(q);` 这一行在做什么，以及它为什么能让并发变得「可检查」。如果 `produce` 需要写、`consume` 需要读，权限该怎么分裂？

**Q4.** 为什么 Wyvern 需要「两阶段解析」？如果只用一阶段（传统解析器），会遇到什么问题？

**Q5.** 类型状态与「用 `if (state == OPEN)` 检查」相比，优势在哪里？有没有劣势？

<details>
<summary>参考答案</summary>

**A1.** **封装的反例**：Modula-2 的 `MODULE` 能把数据和操作包在一起，只导出接口——封装得很好，但没有对象（没有实例、没有动态分派）。OCaml 的模块与签名也是如此。**继承的反例**：Go 语言完全没有继承（没有 `extends`），靠接口的隐式实现与结构体嵌入（embedding）复用，仍然被广泛认为支持 OO 风格；Self 语言用「原型 + 委托」代替类与继承；JavaScript 的原型链也是这条路线。**OO 的核心是动态分派**：调用 `obj.method()` 时，实际执行哪个实现由**运行时**的 `obj` 决定。它带来两个别处难以同时获得的能力：① 调用者只依赖抽象，不依赖具体类型（依赖倒置）；② 被调用者可以**独立演化**——新增一个实现类，所有调用点一行都不用改（开闭原则）。泛型提供①但不提供②（编译期封闭），函数指针提供②但没有类型检查与封装。

**A2.** **设计 A 是对象式**：`area()` 是 `Shape` 的方法，每个具体形状（`Circle`、`Rect`）自己实现——**动态分派**。**设计 B 是 ADT 式**：`area` 是外部静态函数，用**重载**（静态分派）区分类型。**优劣**：
- **加新形状**（`Triangle`）：A 只需加一个类，`ShapeOps` 不动；B 必须给 `ShapeOps` 加一个新重载（而且要改所有类似的 `ShapeOps` 类）。→ **A 优**。
- **加新操作**（`perimeter()`）：A 必须给每个形状类都加方法（要改所有类，可能在你没有源码的类上做不到）；B 只需加一个新的 `ShapeOps2` 类。→ **B 优**。
- **性能**：B 的重载在编译期解析，可以内联；A 的虚调用有间接开销（JIT 通常能去虚化）。→ **B 略优**。
- **跨模块互操作**：A 的 `Shape` 接口可以被第三方实现；B 的 `ShapeOps` 无法处理第三方类型（除非修改 `ShapeOps`）。→ **A 优**。
这就是「表达式问题」：**没有一种设计能同时优雅地支持「加类型」和「加操作」**。实践中，UI/图形库偏 A（类型多变），编译器/分析器偏 B（pass 多变）。

**A3.** `split QG: produce(q) || consume(q);` 把当前执行流**分成两个并行分支**，并把引用 `q` 的权限**分裂**给两边——`produce` 在左分支、`consume` 在右分支。它让并发「可检查」的原因是：**权限分裂规则保证了两个分支的能力不会冲突**，而这是编译期可验证的静态性质。具体到「`produce` 写、`consume` 读」：应该用 **`unique → full + immutable`** 的分裂——`produce` 拿 `full`（可写），`consume` 拿 `immutable`（只读）。这样：
- 类型系统保证 `consume` **不能**修改数据（它只有 `immutable` 权限），所以不需要加锁；
- 类型系统保证 `produce` 是**唯一**的写者（因为原来的 `unique` 被分裂，没有别的可写别名），所以也不需要加锁；
- 唯一的风险是「读到写了一半的数据」——权限系统**不保证顺序**，所以仍需某种同步（如消息传递）来保证「写完了才读」。这正是课件第 21 页所强调的：权限解决**冲突**，不解决**时序**。

**A4.** 因为**语法的选择依赖于类型**。传统解析器在解析时必须**立即决定**「这段记号是什么意思」，但 TSL 的整个设计前提是「同一个记号在不同类型上下文里有不同含义」——没有类型信息，解析器无法决定。具体问题：① **歧义**——两个库都用 `[...]`，解析器不知道该用哪个语法；② **无法消歧**——传统解析器只能靠文法规则（如运算符优先级）消歧，但 DSL 的歧义是**语义层面**的（取决于期望类型），文法规则表达不了；③ **错误信息差**——如果解析器猜错，报出的语法错误会指向错误的库，用户无法理解。两阶段解析把「切块」（Phase I，不需要类型）与「解析内部」（Phase II，需要类型）分开，于是：Phase I 只需识别分隔符与边界（这是纯语法的），Phase II 在类型检查时才知道该用哪个 parser（这是语义的）。**代价**是：解析被推迟，工具（IDE）需要更复杂的增量机制；错误报告也分两阶段（先报「块未闭合」，后报「块内语法错」）。

**A5.** **优势**：
1. **编译期捕获**——`if (state == OPEN)` 是运行时检查，错误要等到执行到那一行；类型状态在**编译时**就报错，测试不用覆盖到也能发现。
2. **零运行时开销**——不需要存状态字段、不需要分支判断（Plaid 的 `this <- OpenFile` 是编译期的类型转换，状态信息在类型里，不在内存里）。
3. **文档化**——类型签名 `ClosedFile >> OpenFile` 一眼就能看出「进入什么状态、离开什么状态」，比注释可靠（注释会过期）。
4. **支持推理**——每个状态只需考虑该状态下的合法操作，不需要考虑「所有字段的所有组合」。
5. **实证收益**——用户研究显示 Plaiddoc 快 2 倍（p=0.0003），因为省掉了「我现在在哪」的心智负担。
**劣势**：
1. **学习成本**——开发者要理解「类型会变」这个非传统概念，写起来也更啰嗦（每个状态一个类型）。
2. **与既有代码的兼容**——绝大多数语言（Java、C#、Python）没有类型状态，无法渐进采用。
3. **别名问题**——如果对象有别名，一个引用改了状态，另一个引用的类型也得跟着变——这需要权限系统配合（这正是 Plaid 同时引入 permissions 的原因）。
4. **表达力边界**——有些协议是**动态的**（状态数在运行时才知道，如状态机从配置文件加载），静态类型表达不了。
5. **工具生态**——没有 IDE 支持、没有调试器支持，实际项目难以落地。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-26-History-and-Future-of-Objects]]——从 SIMULA 到 Smalltalk 的对象史。
- 下一讲：[[15-214-28-Course-Review]]——全课程复习。
- 相关讲次：[[15-214-02-Objects-Encapsulation-Polymorphism]]（对象与多态基础）、[[15-214-07-Design-Patterns]]（Composite、Template Method、Strategy）、[[15-214-23-Static-Analysis]]（类型检查作为规约、协议检查）、[[15-214-24-Static-Analysis-for-Concurrency]]（别名问题与唯一性注解）。
- 课程导航：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]、[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]。
- 术语条目：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Typestate 类型状态、DSL 领域特定语言、Static Analysis 静态分析）。
- 延伸阅读：Cook "On Understanding Data Abstraction, Revisited"（OOPSLA 2009）、Johnson "Frameworks = (Components + Patterns)"（CACM 1997）、Beckman et al. "Partial Typestate-Oriented Programming"（ECOOP 2011）、Bierhoff & Aldrich "Modular Typestate Checking of Aliased Objects"（OOPSLA 2007）、Omar et al. "Safely Composable Type-Specific Languages"（ECOOP 2014）、Gabriel "Objects Have Failed"（2002）。
