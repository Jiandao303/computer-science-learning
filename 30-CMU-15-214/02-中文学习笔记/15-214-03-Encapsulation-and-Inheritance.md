---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L03
topic: Encapsulation and Inheritance
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 封装
  - 继承
  - 包
  - 可见性
---

# 第 3 讲 封装与继承（Encapsulation and Inheritance）

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。

## 1. 本节学习目标

- 能解释 Java 四种可见性修饰符（public / protected / default / private）分别对类内、包内、子类、全世界是否可见，并能查表判断。
- 能说明包（package）为什么是「另一种封装机制」，以及限定名（qualified name）与 `import` 的关系。
- 能区分**继承用于代码复用**与**子类型用于多态**这两件常被混为一谈的事。
- 能用「is-a 检验」判断何时该用继承、何时该用组合（composition）+ 转发（forwarding）。
- 能读懂并画出 UML 类图的基本记号（接口虚线三角、继承实线三角、`+ - # ~` 可见性）。

## 2. 前置知识

- [[15-214-02-Objects-Encapsulation-Polymorphism]]：接口与类、`implements`、动态分派、对象标识与等价。
- 外部概念：Java 的包机制；C 语言中「模块 + 头文件」的封装方式（可作对照）。

## 3. 核心概念

- **Package（包）**：Java 用来划分命名空间、组织相关类的机制，声明形式为 `package edu.cmu.cs.cs214.geo;`。
- **Visibility Modifier（可见性修饰符）**：控制名字（类、字段、方法）在多大范围内可见。四档：`public`、`protected`、默认（package-private）、`private`。
- **Qualified Name（限定名）**：带完整包路径的名字，如 `java.util.Queue`。
- **Inheritance（继承）**：子类自动获得父类的字段与方法（代码复用），用 `extends` 表示。
- **Abstract Class（抽象类）**：不能实例化、允许含抽象方法（只有签名没有方法体）的类，是接口与完整实现之间的「混合体」。
- **Override（重写）**：子类提供与父类同签名的方法体，以特化行为。
- **Subtyping（子类型）**：若 `A <: B`，则 A 的对象可以出现在任何需要 B 的地方（可替换性，substitutability）。
- **Composition and Forwarding（组合与转发）**：把可复用代码放进另一个对象，本类持有一个引用并把调用转发过去。
- **UML Class Diagram（UML 类图）**：用方框表示类/接口，用线表示关系的图；虚线空心三角 = implements，实线空心三角 = extends。

## 4. 通俗理解

把「包」想成**小区**，把「可见性」想成**门禁等级**：

- `public`：小区大门敞开，谁都能进。
- `protected`：本小区居民 + 住在别处但有血缘关系的亲属（子类）能进。
- 默认（无修饰符）：只有本小区居民能进，外人一律不行。
- `private`：只有自己家里能进，连邻居都不行。

课件引用 Josh Bloch 的一句话作为封装的总纲：

> "The single most important factor that distinguishes a well-designed module from a poorly designed one is the degree to which the module hides its internal data and other implementation details."

翻成中文：**区分一个模块设计得好不好的最重要因素，是它把内部数据与实现细节藏得有多深。**

一个具体对比：一个 5 万行的项目里，如果所有字段都是 `public`，某天想把 `int x, y` 改成极坐标 `double r, theta`，就必须修改**所有**读写过 `x`、`y` 的地方（可能上百处）。如果字段是 `private`，只改类内的 getter/setter 即可，外部代码零改动。

## 5. 原理与推导

### 5.1 编程语言的两层视角

课件第 9 页给出一张非常有用的分类表，把语言特性按「小规模 / 较大规模」排列：

| 维度 | 小规模 | 较大规模 |
|---|---|---|
| 数据（Data） | 基本类型（primitives）、数组、结构体 | 对象（objects）、堆（heaps） |
| 控制（Control） | `if`、`while`、`;`、函数/方法调用 | 方法分派、并发 |
| 命名与引用（Naming and Reference） | 局部变量、参数 | 包、import、可见性、限定名 |

这张表的用法：当你觉得某个语言特性「多余」时，问一句「它解决的是小规模问题还是较大规模问题」。`private` 对写 100 行的程序毫无意义，对写 10 万行的程序是生死线。

### 5.2 四种可见性的完整表格

课件第 11 页给出的表（Y = 可见，N = 不可见）：

| 修饰符 | 类内（Class） | 包内（Package） | 子类（Subclass） | 全世界（World） |
|---|---|---|---|---|
| `public` | Y | Y | Y | Y |
| `protected` | Y | Y | Y | N |
| 默认（无修饰符） | Y | Y | N | N |
| `private` | Y | N | N | N |

两个容易记错的点：

1. **`protected` 比默认更宽**：它允许子类访问，即使子类在别的包里。默认（package-private）反而不允许跨包子类访问。
2. **接口中的方法隐式 `public`**：在接口里写方法声明不需要加 `public`，加了也不改变语义。

### 5.3 包与限定名：三种引用方式

课件第 12 页给出三种写法，效果相同：

```java
// 方式 1：全限定名
java.util.Queue q = …;

// 方式 2：导入单个类
import java.util.Queue;
Queue q = …;

// 方式 3：导入整个包
import java.util.*;
Queue q = …;
```

当两个包里有同名类时，编译器会报警告，此时必须用全限定名消歧。这一机制的意义在于：**包让「名字」也有了作用域**，从而让两个团队可以各自定义 `Point` 而不冲突。

### 5.4 封装的第一原则

课件第 13 页给的规则只有一句：**尽可能限制可访问性（Restrict accessibility as much as possible）**。默认全部写成 `private`，只有当你有明确理由时才放宽。

这条规则之所以是「第一原则」，是因为放宽可见性是不可逆的：一旦外部代码依赖了某个 public 字段，你就再也无法自由修改它的表示。相反，把 private 改成 public 是随时可以做的安全操作。

### 5.5 继承的引入：Dog 例子

课件第 6–7、14 页用一个具体例子引出继承：

```java
public interface Dog {
    public String getName();
    public String getBreed();
    public void bark();
}
public class Chiuaua implements Dog {
    public String getName()  { return "Bob"; }
    public String getBreed() { return "Chiuaua"; }
    public void bark()       { /* How do I bark? */ }
}
```

问题立刻出现：`GermanShepherd`、`Poodle`……每个品种都要重复实现 `getName`、`getBreed`。于是引入 `AbstractDog` 作为中间层：

```
      «interface» Dog
            △
            |  (implements)
        AbstractDog
            △
            |  (extends)
   ┌────────┴────────┐
Chiuaua        GermanShepherd  …
```

课件第 14 页总结三种角色的典型分工：

- **接口（interface）**：定义对客户的期望/承诺。
- **抽象类（abstract class）**：接口与完整实现之间的便利混合体——已实现的方法直接复用，未实现的留给子类。
- **子类（subclass）**：重写（override）某个方法以特化其实现。

Java 的硬限制（第 17 页）：**一个类只能直接 `extends` 一个父类，但可以 `implements` 多个接口**。这解释了为什么「用接口表达能力、用抽象类复用代码」成为 Java 的标准做法。

### 5.6 账户层次的完整推演

课件第 19–21 页展示了一次真实的设计改进：

**初始设计（坏的）**：`CheckingAccount` 与 `SavingsAccount` 两个接口各自重复声明 `getBalance`、`deposit`、`withdraw`、`transfer`。重复意味着「改一处要改两处」，而且客户端无法把它们放进同一个列表统一处理。

**改进设计（好的）**：抽出 `Account` 作为公共父接口，两个子接口只声明各自特有的方法：

```java
public interface CheckingAccount extends Account {
    …
}
public interface InterestCheckingAccount
        extends CheckingAccount, SavingsAccount {   // 多重接口继承
    …
}
```

课件第 20 页的批注点出三条语义：

- `SavingsAccount` 是 `Account` 的**子类型（subtype）**，`Account` 是 `SavingsAccount` 的**超类型（supertype）**。
- `CheckingAccount extends Account` 表示 `Account` 的所有方法都被**继承**（复制到 `CheckingAccount`）。
- 若已知手上是 `CheckingAccount`，则额外方法（`getFee`）可用。

多态的价值（第 22 页）用一段伪代码说明：

```
If today is the last day of the month:
   For each acct in allAccounts:
      acct.monthlyAdjustment();
```

新增一种账户类型时，这段客户端代码**不用改**——它只依赖 `Account` 接口。

### 5.7 继承 vs 组合：同一个复用问题的两条路

课件第 23–28 页对比了三种实现方式。

**方案 A：只用接口**。每个实现类（`CheckingAccountImpl` 等）各自重写全部方法——复用为零。

**方案 B：抽象类复用**。

```java
public abstract class AbstractAccount implements Account {
    protected float balance = 0.0;
    public float getBalance() { return balance; }
    abstract public void monthlyAdjustment();     // 留给子类
    // 其它方法…
}
public class CheckingAccountImpl
        extends AbstractAccount implements CheckingAccount {
    public void monthlyAdjustment() { balance -= getFee(); }
    public float getFee() { /* 手续费计算 */ }
}
```

好处：`getBalance` 只写一次。风险：子类依赖 `AbstractAccount` 的**实现**（例如 `balance` 字段），一旦父类改内部结构，子类可能被破坏。

**方案 C：组合 + 转发**。

```java
public class CheckingAccountImpl implements CheckingAccount {
    BasicAccountImpl basicAcct = new BasicAccountImpl(…);
    public float getBalance() { return basicAcct.getBalance(); }   // 转发
    // …
}
```

课件第 29 页给出权衡表：

| 维度 | 继承 | 组合 + 转发 |
|---|---|---|
| 代码量 | 少（无需写转发函数） | 多（每个方法都要写一行转发） |
| 封装性 | **破坏**：子类依赖父类实现 | 保持：只依赖被组合对象的公开接口 |
| 递归依赖 | 容易出现（父类调用被子类重写的方法） | 较易避免 |
| 适用判据 | 「每个 Foo 真的都是 Bar 吗？」 | 「Foo 只是**使用**一个 Bar」 |

结论性建议：**少用继承（Use inheritance sparingly）**。在写 `class Foo extends Bar` 之前，先回答「Is every Foo really a Bar?」。

### 5.8 继承的细节机制

**`super`：扩展而非替换**（第 30 页）

```java
public class ExpensiveCheckingAccountImpl
        extends AbstractAccount implements CheckingAccount {
    public boolean withdraw(float amount) {
        balance -= HUGE_ATM_FEE;                  // 先扣手续费
        boolean success = super.withdraw(amount); // 再调用父类实现
        if (!success) balance += HUGE_ATM_FEE;    // 失败则退回手续费
        return success;
    }
}
```

`super.m()` 的含义是「调用父类版本」，它**不是**「调用某个特定对象」——它仍然作用在当前 `this` 上。

**构造函数链**（第 31 页）

```java
public CheckingAccountImpl(float initialBalance, float fee) {
    super(initialBalance);      // 必须是构造函数的第一条语句
    this.fee = fee;
}
public CheckingAccountImpl(float initialBalance) {
    this(initialBalance, 5.00); // 调用同类中的另一个构造函数
}
```

`super(...)` 必须是第一条语句，因为父类部分必须先完成初始化，子类才能安全使用继承来的字段。

**`final` 的三种用法**（第 32 页）

| 修饰对象 | 含义 | 典型动机 |
|---|---|---|
| `final class` | 不能被继承 | 防止子类破坏不变量（如 `String`） |
| `final method` | 不能被重写 | 锁定关键算法步骤，防止行为被篡改 |
| `final field` | 只能赋值一次（初始化时） | 表达不可变（immutability），让读者与编译器都能依赖它 |

**强制转换与 `instanceof`**（第 33–34 页）

```java
Account acct = …;
CheckingAccount checkingAcct = (CheckingAccount) acct;   // 向下转型
float fee = checkingAcct.getFee();                        // 类型不兼容会抛 ClassCastException
```

```java
if (acct instanceof CheckingAccount) {
    CheckingAccount c = (CheckingAccount) acct;
    adj = c.getFee();
}
```

课件建议：**尽量避免 `instanceof`**。理由见下一节——它通常是「该用多态却用了类型判断」的信号。

### 5.9 用多态消除 `instanceof`：模板方法

课件第 15–16 页给出对照。**坏味道**：

```java
float adj = 0.0;
if (acct instanceof CheckingAccount) {
    adj = ((CheckingAccount) acct).getFee();
} else if (acct instanceof SavingsAccount) {
    adj = ((SavingsAccount) acct).getInterest();
}
```

**改写**：在接口里加一个 `getMonthlyAdjustment()`，每个实现类自己回答：

```java
public interface Account {
    …
    public float getMonthlyAdjustment();
}
public class CheckingAccount implements Account {
    public float getMonthlyAdjustment() { return getFee(); }
}
public class SavingsAccount implements Account {
    public float getMonthlyAdjustment() { return getInterest(); }
}
// 客户端
float adj = acct.getMonthlyAdjustment();
```

这就是 **Template Method（模板方法）** 思路的雏形：把「做什么」固定在接口/父类，「怎么做」下放给子类。新增账户类型时客户端不变——这正是第 2 讲「面向接口编程」的直接收益。

## 6. 代码示例

### 6.1 官方课程代码

出自 `03_Encapsulation_and_inheritance.pdf` 第 24–25 页（抽象类复用 + 子类特化）：

```java
public abstract class AbstractAccount implements Account {
    protected float balance = 0.0;
    public float getBalance() { return balance; }
    abstract public void monthlyAdjustment();      // 抽象方法，留给子类
    // 其它方法…
}

public class CheckingAccountImpl
        extends AbstractAccount implements CheckingAccount {
    public void monthlyAdjustment() { balance -= getFee(); }
    public float getFee() { /* 手续费计算 */ }
}
```

出自同文件第 28 页（组合 + 转发）：

```java
public class CheckingAccountImpl implements CheckingAccount {
    BasicAccountImpl basicAcct = new BasicAccountImpl(…);
    public float getBalance() { return basicAcct.getBalance(); }
    // 其余方法同样转发
}
```

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

下面的例子把「可见性」与「组合 vs 继承」放在同一个程序里对照：

```java
package demo;

class Engine {                       // 包私有类
    protected int horsepower = 100;  // 子类可见
    private int serial = 0;          // 仅本类可见
    public int getSerial() { return serial; }
}

class TurboEngine extends Engine {
    void boost() { horsepower += 50; }   // OK：protected 对子类可见
    // void peek() { System.out.println(serial); }  // 编译错误：private
}

// 组合：Car 使用 Engine，但不是 Engine
class Car {
    private final Engine engine;     // has-a
    Car(Engine e) { this.engine = e; }
    int power() { return engine.horsepower; }   // 同包，可访问 protected
}

// 继承：TurboCar 是一种 Car
class TurboCar extends Car {
    TurboCar(Engine e) { super(e); }
}

public class Main {
    public static void main(String[] args) {
        Car c = new TurboCar(new TurboEngine());
        System.out.println(c.power());     // 100，通过组合转发拿到
        // c.boost();                      // 编译错误：Car 没有 boost
    }
}
```

要点：`Car` 与 `Engine` 是 has-a（组合），`TurboCar` 与 `Car` 是 is-a（继承）。把两者混用——例如让 `Car extends Engine`——会得到一个荒谬的结论：「汽车是一种发动机」。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| Inheritance（继承） | Subtyping（子类型） | 继承是为了**复用代码**（父类实现自动可用）；子类型是为了**多态**（可在需要父类型处替换）。Java 中 `extends`/`implements` 同时产生两者，但概念上可分离 |
| `protected` | 默认（package-private） | `protected` 对**跨包子类**可见；默认只对**同包**可见。跨包时 `protected` 更宽 |
| Overriding（重写） | Overloading（重载） | 重写要求签名相同、在子类中替换父类实现（运行期分派）；重载是同名不同参数（编译期选最具体） |
| `extends`（类） | `extends`（接口） | 类继承只能有一个父类且继承实现；接口继承可以多个且只继承声明 |
| `instanceof` 分支 | 多态分派 | 前者把「类型 → 行为」的知识写在客户端，新增类型要改客户端；后者把知识放在类型内部，新增类型不改客户端 |
| 抽象类 | 接口 | 抽象类可有字段、构造器、已实现方法，单继承；接口（Java 8 前）只有声明，可多实现 |

## 8. 对应原版讲义

- PDF 相对路径：`90-原始PDF/15-214/slides/03_Encapsulation_and_inheritance.pdf`
- 总页数：38 页
- 本节重点页码：
  - 第 6–7 页：Dog 接口与继承层次预览
  - 第 9 页：语言特性「小规模 / 较大规模」分类表
  - 第 10–12 页：包、四种可见性表、限定名与 import
  - 第 13 页：封装第一原则 + Josh Bloch 引语
  - 第 14 页：接口 / 抽象类 / 子类的角色分工
  - 第 16–17 页：Java Collections 层次片段、单继承多接口
  - 第 18 页：UML 类图记号
  - 第 19–22 页：账户接口的坏设计与改进、多态伪代码
  - 第 23–29 页：只用接口 / 抽象类复用 / 组合转发 三方案与权衡
  - 第 30–34 页：`super`、构造函数链、`final`、强制转换、`instanceof`
  - 第 15–16 页（`04` 讲义重讲）：用 Template Method 消除 `instanceof`
  - 第 35–38 页：类型检查的价值、值流与子类型关系、子类型规则
- 原始网页链接：`https://www.cs.cmu.edu/~aldrich/214/slides/03_Encapsulation_and_inheritance.pdf`
- > 待核实：第 24–25、30–31 页原文将 `AbstractAccount` 拼写为 `AbstractAcount`（缺 c），应为幻灯片笔误。

## 9. 对应视频

未找到官方公开录像。2013 年秋季的 15-214 课堂没有公开发布录像，故不提供链接与时间戳。

## 10. 本节复习

- 四种可见性由窄到宽：`private` < 默认 < `protected` < `public`；`protected` 比默认多了「跨包子类」。
- 包是命名空间级的封装；限定名与 `import` 只是写法差异。
- 封装第一原则：默认全 private，有理由才放宽。
- 继承 = 代码复用；子类型 = 可替换性。Java 用一个关键字同时给出两者，但设计时要分开想。
- 组合 + 转发保封装但要多写转发代码；继承省代码但让子类依赖父类实现。
- 判据：「Is every Foo really a Bar?」——答不上来就用组合。
- `super(...)` 必须是构造函数第一条语句；`this(...)` 用于委托同类构造函数。
- `instanceof` 分支通常可以用多态（模板方法）消除。

## 11. 自我检查

1. 一个类 `A` 在包 `p1`，类 `B extends A` 在包 `p2`。`A` 中有一个默认（无修饰符）方法 `m()` 和一个 `protected` 方法 `n()`。`B` 能否调用 `m()`？能否调用 `n()`？请说明依据。
2. 课件说「继承违反封装原则」。请用 `AbstractAccount.balance` 这个具体字段解释这句话的含义，并说明如果改用组合，问题如何消失。
3. 给定 `Account acct = …;`，写出用 `instanceof` 判断账户类型并计算月度调整的代码，然后把它改写成多态版本。改写后新增 `MoneyMarketAccount` 需要改哪些文件？
4. 为什么 `super.withdraw(amount)` 不能写成「对父类对象调用 withdraw」？`super` 到底指什么？

<details>
<summary>参考答案</summary>

1. `B` **不能**调用 `m()`：默认可见性只在同一个包内有效，`p2` 与 `p1` 不同包，即使 `B` 是 `A` 的子类也不行。`B` **能**调用 `n()`：`protected` 对子类可见，无论子类在哪个包（但注意：`B` 只能通过 `B` 类型或其子类型的引用访问该成员，不能通过任意 `A` 引用访问）。

2. `AbstractAccount` 把 `balance` 声明为 `protected`，于是所有子类都能直接读写这个字段。这意味着 `balance` 的**表示**（一个 `float`）成了父子类之间的契约：如果将来想把余额改成「以分为单位的 `long`」或「交易列表」，所有子类都会编译失败或行为错误。改用组合后，`CheckingAccountImpl` 只持有 `BasicAccountImpl` 的引用并调用它的公开方法，`BasicAccountImpl` 内部怎么存余额与子类无关，因此可以独立演化。

3. `instanceof` 版本：
   ```java
   float adj = 0.0f;
   if (acct instanceof CheckingAccount) {
       adj = ((CheckingAccount) acct).getFee();
   } else if (acct instanceof SavingsAccount) {
       adj = ((SavingsAccount) acct).getInterest();
   }
   ```
   多态版本：在 `Account` 接口中声明 `float getMonthlyAdjustment();`，各实现类返回自己的值，客户端写 `float adj = acct.getMonthlyAdjustment();`。改写后新增 `MoneyMarketAccount` **只需要新增一个实现类**，客户端与既有实现类都不用改（这正是「对扩展开放、对修改关闭」的雏形）。

4. 因为 `super` 不是对象引用，而是「在**当前对象** `this` 上，从父类那一层开始查找方法」的语法标记。不存在一个独立的「父类对象」；父类部分就嵌在子类对象内部。所以 `super.withdraw(...)` 的接收者仍然是 `this`，只是方法查找的起点上移一层。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-02-Objects-Encapsulation-Polymorphism]]
- 下一讲：[[15-214-04-Inheritance-Typechecking-Dispatch]]
- 课程总览：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]
- 课程目录：[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
