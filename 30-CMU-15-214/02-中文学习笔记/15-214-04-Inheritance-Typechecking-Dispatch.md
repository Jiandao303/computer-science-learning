---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L04
topic: Inheritance, Type-Checking, and Method Dispatch
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 继承
  - 类型检查
  - 动态分派
  - equals
  - hashCode
---

# 第 4 讲 继承、类型检查与方法分派（Inheritance, Type-Checking, and Method Dispatch）

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。

## 1. 本节学习目标

- 能写出子类型关系 `A <: B` 的定义，并验证它的自反性与传递性。
- 能按「值流（value flow）」规则逐个判断赋值、传参、返回是否类型安全。
- 能完整复述方法分派四步，并区分其中的**重载解析**（编译期选最具体签名）与**重写分派**（运行期选实现）。
- 能默写 `equals(Object)` 与 `hashCode()` 的契约条款，并解释为什么必须成对重写。
- 能说明 `ColorPoint extends Point` 时 `equals` 的对称性难题，以及课件给出的「抽象 Point」解法。

## 2. 前置知识

- [[15-214-03-Encapsulation-and-Inheritance]]：包与可见性、继承与子类型、抽象类、组合 vs 继承、`super`、`instanceof`。
- [[15-214-02-Objects-Encapsulation-Polymorphism]]：接口、静态类型 vs 动态类、`==` vs `equals`。
- 外部概念：等价关系（自反、对称、传递）的数学定义；哈希表为什么需要 `hashCode`。

## 3. 核心概念

- **Type Checking（类型检查）**：分析程序，判断每个操作是否适用于它所作用的类型。
- **Value Flow（值流）**：值通过赋值、传参、返回在变量之间流动；每一处流动都要检查「源类型是目标类型的子类型」。
- **Subtype Relation（子类型关系）`A <: B`**：A 可以替换 B。基本情形：`A extends B` 或 `A implements B`，以及 `A <: A`（自反）；归纳情形：传递性。
- **Static Type（静态类型）**：变量声明时写下的类型，编译期已知。
- **Dynamic Class（动态类）**：对象在堆上实际的类，运行期由对象头提供。
- **Overload Resolution（重载解析）**：编译期在多个同名方法中选「最具体（most specific）」的那个。
- **Method Dispatch（方法分派）**：运行期从动态类出发向上查找与已选签名一致的实现。
- **Behavioral Subtyping（行为子类型）**：子类型不仅签名兼容，行为也必须符合父类规格。
- **`java.lang.Object`**：所有 Java 类的根，定义了 `toString()` 与 `equals(Object)`、`hashCode()`、`clone()` 等。
- **Equivalence Relation（等价关系）**：满足自反、对称、传递的关系；`equals` 必须实现它。
- **`clone()`**：返回对象的深拷贝（deep copy）。

## 4. 通俗理解

把**类型检查**想成机场安检，把**分派**想成登机口找航班：

- 安检（编译期）检查「你持有的登机牌类型」是否符合这一关的要求。它不关心你最终坐哪班飞机，只关心「这张牌能不能过这道门」。
- 登机口（运行期）才根据你的**实际航班**（动态类）决定你去哪个廊桥。同一张「机票类型」（静态类型），可能是不同航空公司的实际航班（动态类）。

一个具体例子（课件第 23–30 页的分派练习）：

```java
class GenericAnimal { public String getNoise() { return "Noise"; } }
class Cat extends GenericAnimal { public String getNoise() { return "Meow"; } }
class Bird extends GenericAnimal { public String getNoise() { return "Chirp"; } }
class GenericDog extends GenericAnimal { /* 没有重写 */ }
class Ewokian extends GenericDog { public String getNoise() { return "Oonga!"; } }
```

| 客户端代码 | 打印 | 原因 |
|---|---|---|
| `GenericAnimal A = new GenericAnimal(); A.getNoise();` | Noise | 动态类就是 `GenericAnimal` |
| `Bird B = new Bird(); B.getNoise();` | Chirp | 动态类就是 `Bird` |
| `GenericAnimal B = new Bird(); B.getNoise();` | Chirp | 静态类型是 `GenericAnimal`，但实现取 `Bird` 的 |
| `GenericAnimal C = new Cat(); C.getNoise();` | Meow | 同上，取 `Cat` 的 |
| `GenericAnimal D = new GenericDog(); D.getNoise();` | Noise | `GenericDog` 没重写，向上找到 `GenericAnimal` 的实现 |
| `GenericAnimal E = new Ewokian(); E.getNoise();` | Oonga! | 动态类是 `Ewokian` |
| `Ewokian E = new Ewokian(); GenericAnimal F = E; F.getNoise();` | Oonga! | 变量类型变了，对象没变 |

这张表是整个第 4 讲的核心：**变量类型只影响「能调用什么」，不影响「调用到哪份实现」**。

## 5. 原理与推导

### 5.1 类型检查是什么、为什么值得做

课件第 17 页的定义：**分析程序，判断每个操作是否适用于它所作用的类型。** 两个收益：

1. **尽早发现错误**。`int h = "hi" / 2;` 在编译期就被拒绝，不必等到运行时崩溃。
2. **帮助文档化代码**。

```java
baz(frob) { /* frob 到底是什么？我能对它做什么？ */ }
void baz(Car frob) { /* 哦，我能开它 */ }
```

第二种收益常被低估：类型签名是最不容易过期的文档，因为编译器会强制它保持真实。

### 5.2 值流与子类型

课件第 18 页给出判定规则。对 `Foo f = expression;`：

1. 求出源表达式 `expression` 的类型 `Tsource`；
2. 取出目标变量 `f` 的声明类型 `Tdest`；
3. 检查 `Tsource <: Tdest`。

子类型关系 `A <: B` 的**基本情形**：

- `A extends B`（类继承）→ `A <: B`
- `A implements B`（接口实现）→ `A <: B`
- `A <: A`（自反性，reflexivity）

**归纳情形**：

- 若 `A <: B` 且 `B <: C`，则 `A <: C`（传递性，transitivity）

传递性解释了为什么 `Ewokian <: GenericDog <: GenericAnimal`，所以 `GenericAnimal F = new Ewokian();` 合法。

### 5.3 表达式的类型怎么算

课件第 19 页给出基础情形：

| 表达式形式 | 类型 |
|---|---|
| 变量、字段 | 声明时写的类型 |
| `new C(...)` | 被创建的类 `C` |
| 强制转换 `(T) e` | 转换目标 `T` |
| 方法调用 `e1.m(e2)` | 见下面四步 |

方法调用的四步：

1. 求接收者 `e1` 的类型 `T1`；
2. 求实参 `e2` 的类型 `T2`；
3. 在 `T1`（及其父类型）中按分派规则找到方法声明 `m`；
4. 整个表达式的类型 = 第 3 步找到的声明的**返回类型**。

注意第 3 步用的是 **`T1`（静态类型）**，第 4 步用的是**声明处的返回类型**，两者都在编译期确定。

### 5.4 子类型规则：签名层面

课件第 20 页：

- 若具体类 `B extends` 类型 `A`：
  - `B` 继承 `A` 中所有具体方法；
  - `B` 可以重写 `A` 中非 `final` 的继承方法；
  - `B` **必须**重写 `A` 中的抽象方法或接口中未定义的方法。
- 若 `B` 重写 `A` 中声明的方法：
  - **参数类型必须完全相同**（不能「窄化」也不能「宽化」）；
  - **返回类型必须是 `A` 中返回类型的子类型**（协变返回，covariant return）。

参数类型必须相同这一点值得单独强调：Java 不支持「参数逆变」，所以 `equals(Point p)` **不是**对 `equals(Object obj)` 的重写，而是**重载**。这正是 5.7 节 `Point` 例子的全部要害。

### 5.5 行为子类型

签名兼容只是必要条件，**行为也必须兼容**。课件第 20 页末尾的警句：

> If `Cowboy.draw()` overrides `Circle.draw()`, somebody gets hurt!

含义：如果父类 `Shape.draw()` 的规格承诺「在画布上画出该图形」，子类就不能把它实现成「掏出枪开火」——即使签名完全合法。规格（specification）是继承契约的一部分，第 5 讲会把这条落实为契约式设计。

### 5.6 方法分派四步（完整版）

课件第 21–22 页把第 2 讲的简化版补全：

| 阶段 | 步骤 | 细节 |
|---|---|---|
| 编译期 | 1. 确定查找起点 | 接收者表达式的**静态类型** |
| 编译期 | 2. 确定要执行的**签名** | 找出所有可访问、实参适用的方法，选**最具体**的一个 |
| 运行期 | 3. 确定接收者的**动态类** | 对象头里记录的类 |
| 运行期 | 4. 定位并调用实现 | 从动态类开始，找与第 2 步签名相同的方法；找不到就上移一层 |

第 2 步的「最具体」定义为：`m1` 比 `m2` 更具体，当且仅当 `m1` 的每个参数类型都是 `m2` 对应参数类型的子类型。例如 `foo(Apple, int)` 比 `foo(Fruit, int)` 更具体。

第 4 步的一个结论值得记住：**这个过程一定能找到方法**。理由是第 2 步已在静态类型中找到签名，而动态类一定是静态类型的子类型，所以沿父类链向上必然能到达那个声明处。

### 5.7 `java.lang.Object` 与 `equals` 的陷阱

所有 Java 类都隐式继承 `java.lang.Object`。常用/常重写的方法（第 31 页）：

| 方法签名 | 作用 |
|---|---|
| `String toString()` | 返回对象的字符串表示 |
| `boolean equals(Object obj)` | 内容等价判断 |
| `int hashCode()` | 哈希值 |
| `Object clone()` | 复制对象 |

课件第 32–33 页的分派练习 F 是一个经典陷阱：

```java
public class Point {
    private final int x, y;
    public Point(int px, int py) { x = px; y = py; }
    String toString() { return String.valueOf(x) + " " + String.valueOf(y); }
    boolean equals(Point p) { return x == p.x && y == p.y; }   // 注意参数是 Point
    int hashCode() { return toString().hashCode(); }
}
```

客户端：

```java
public static void check(Object a, Object b) {
    if (a.equals(b)) System.out.println("True");
    else System.out.println("False");
}
Point p = new Point(1, 42);
Point q = new Point(1, 42);
check(p, q);          // 打印 False
```

为什么是 `False`？因为 `check` 内部 `a` 的静态类型是 `Object`，第 2 步在 `Object` 中选中的签名是 `equals(Object)`。`Point` 里写的 `equals(Point p)` 是**重载**而不是重写，签名不匹配，因此第 4 步沿 `Point → Object` 找到的是 `Object.equals`，而它的默认实现是 `return this == obj;`——`p` 与 `q` 是两个不同对象，返回 `false`。

课件第 40 页的批注一句话点破：**`boolean equals(Point p)` does not override `boolean equals(Object obj)`**。

正确写法（第 41 页）：

```java
public boolean equals(Object obj) {
    if (!(obj instanceof Point)) return false;
    Point p = (Point) obj;
    return x == p.x && y == p.y;
}
```

### 5.8 `equals` 与 `hashCode` 的契约

**`equals(Object obj)` 必须构成等价关系**（第 35 页）：

| 条款 | 形式化表述 | 违反后果 |
|---|---|---|
| 自反（Reflexive） | `∀x. x.equals(x)` | 集合里找不到自己 |
| 对称（Symmetric） | `∀x,y. x.equals(y) ⇔ y.equals(x)` | 集合行为依赖查询方向 |
| 传递（Transitive） | `∀x,y,z. x.equals(y) ∧ y.equals(z) ⇒ x.equals(z)` | 等价类分裂，去重失效 |
| 一致（Consistent） | 反复调用返回同一结果（除非对象被修改） | 哈希表/集合中出现幽灵元素 |
| 非空 | `x.equals(null)` 恒为 `false` | 空指针异常 |

**`hashCode()` 的契约**（第 36 页）：

1. **一致**：反复调用返回同一值（除非对象被修改）。
2. **相等蕴含同哈希**：`x.equals(y) ⇒ x.hashCode() == y.hashCode()`。
3. **反向不要求**：`x.hashCode() == y.hashCode()` **不**蕴含 `x.equals(y)`（哈希碰撞是合法的）。

课件给的建议是**当且仅当**关系：**重写 `equals` 就必须重写 `hashCode`，反之亦然**。理由：哈希容器（`HashMap`、`HashSet`）先用 `hashCode` 定位桶，再用 `equals` 在桶内确认；如果两个相等对象哈希不同，它们会被放进不同桶，容器就「找不到」本该找到的元素。

**`clone()` 的契约**（第 37 页）：返回深拷贝。通常（但不必然）满足 `x.clone() != x` 与 `x.clone().equals(x)`。

### 5.9 ColorPoint 难题：对称性的四次失败

课件第 42–46 页用「给 `Point` 加颜色」这个看似无害的需求，把 `equals` 的坑挖到最深。

**尝试 1**（第 43 页）：`ColorPoint.equals` 用 `instanceof ColorPoint` 判断。

```java
public boolean equals(Object obj) {
    if (!(obj instanceof ColorPoint)) return false;
    ColorPoint cp = (ColorPoint) obj;
    return super.equals(cp) && color.equals(cp.color);
}
```

问题：`Point p = new Point(2,42); ColorPoint cp = new ColorPoint(2,42,BLUE);`
`p.equals(cp)` 为 `true`（`Point.equals` 只看坐标），但 `cp.equals(p)` 为 `false`（`p` 不是 `ColorPoint`）。**破坏对称性**。

**尝试 2**（第 45 页）：让 `Point.equals` 只对非 `ColorPoint` 生效。

```java
if (!(obj instanceof Point)) return false;
if (!(obj instanceof ColorPoint)) return super.equals(obj);
ColorPoint cp = (ColorPoint) obj;
return super.equals(cp) && color.equals(cp.color);
```

新问题：`cp1 = ColorPoint(2,42,BLUE)`、`cp2 = ColorPoint(2,42,MAUVE)`。
`cp1.equals(cp2)` 为 `false`（颜色不同），但 `cp1.equals(p)` 与 `p.equals(cp2)` 都为 `true`。取 `x = cp1, y = p, z = cp2`，则 `x.equals(y)` 与 `y.equals(z)` 为真而 `x.equals(z)` 为假——**破坏传递性**。

**尝试 3（课件的解法）**（第 46 页）：把 `Point` 改成**抽象类**，坐标比较留给「非彩色」的具体子类。

```java
public abstract class Point {
    private final int x, y;
    public Point(int x, int y) { this.x = x; this.y = y; }
    public boolean equals(Object obj) {
        if (!(obj instanceof Point)) return false;
        Point p = (Point) obj;
        return x == p.x && y == p.y;
    }
}
public class ColorPoint extends Point {
    private final Color color;
    public ColorPoint(int x, int y, Color color) { super(x, y); this.color = color; }
    public boolean equals(Object obj) {
        if (!(obj instanceof ColorPoint)) return false;
        ColorPoint cp = (ColorPoint) obj;
        return super.equals(cp) && color.equals(cp.color);
    }
}
public class PointImpl extends Point {
    public PointImpl(int x, int y) { super(x, y); }
    public boolean equals(Object obj) {
        if (!(obj instanceof PointImpl)) return false;
        return super.equals(obj);
    }
}
```

关键点：抽象 `Point` **没有直接实例**，因此不存在「一个 `Point` 与一个 `ColorPoint` 比较」的场景，对称性难题从源头消失。这是「优先使用组合/抽象、避免可变等价语义跨层次继承」的一个具体胜利。

> 待核实：课件第 41–46 页打印的 `if (!(obj instanceof Point)` 缺少一个右括号，应为幻灯片排版遗漏。

## 6. 代码示例

### 6.1 官方课程代码

出自 `04_Inheritance,_type-checking,_and_Method_dispatch.pdf` 第 15–16 页（用模板方法消除 `instanceof`）：

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
// 客户端从 if-instanceof 链变成一行：
Account acct = …;
float adj = acct.getMonthlyAdjustment();
```

出自同文件第 46 页（`ColorPoint` 的抽象解法）：

```java
public abstract class Point {
    private final int x, y;
    public Point(int x, int y) { this.x = x; this.y = y; }
    public boolean equals(Object obj) {
        if (!(obj instanceof Point)) return false;
        Point p = (Point) obj;
        return x == p.x && y == p.y;
    }
}
public class PointImpl extends Point {
    public PointImpl(int x, int y) { super(x, y); }
    public boolean equals(Object obj) {
        if (!(obj instanceof PointImpl)) return false;
        return super.equals(obj);
    }
}
```

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

下面演示「正确重写 equals/hashCode」与「错误重载」的差别，并验证哈希容器的行为：

```java
import java.util.*;

class BadPoint {                         // 错误示范：参数类型是 BadPoint，构成重载
    final int x, y;
    BadPoint(int x, int y) { this.x = x; this.y = y; }
    public boolean equals(BadPoint o) { return o != null && x == o.x && y == o.y; }
    // 没有重写 hashCode
}

class GoodPoint {                        // 正确示范
    final int x, y;
    GoodPoint(int x, int y) { this.x = x; this.y = y; }
    @Override public boolean equals(Object o) {
        if (!(o instanceof GoodPoint)) return false;
        GoodPoint p = (GoodPoint) o;
        return x == p.x && y == p.y;
    }
    @Override public int hashCode() { return 31 * x + y; }
}

public class Demo {
    public static void main(String[] args) {
        Set<Object> s1 = new HashSet<>();
        s1.add(new BadPoint(1, 2));
        System.out.println(s1.contains(new BadPoint(1, 2)));   // false：默认 equals 是身份比较

        Set<Object> s2 = new HashSet<>();
        s2.add(new GoodPoint(1, 2));
        System.out.println(s2.contains(new GoodPoint(1, 2)));  // true：equals 与 hashCode 都正确

        // 对称性检查
        Object a = new GoodPoint(1, 2), b = new GoodPoint(1, 2);
        System.out.println(a.equals(b) + " " + b.equals(a));   // true true
    }
}
```

要点：`BadPoint` 的 `equals(BadPoint)` 只是一个普通重载，`HashSet` 调用的是从 `Object` 继承的 `equals(Object)`，即身份比较，所以第二个「相等」的点找不到。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| Overriding（重写） | Overloading（重载） | 重写：子类同签名替换父类方法，运行期分派；重载：同名不同参数，编译期选最具体。`equals(Point)` 是重载，`equals(Object)` 才是重写 |
| 静态类型（static type） | 动态类（dynamic class） | 静态类型决定编译期「能调用哪些方法」；动态类决定运行期「执行哪份实现」 |
| `A <: B`（子类型） | `A extends B`（继承） | 子类型是语义关系（可替换）；`extends` 是语法机制，同时也带来代码复用。`implements` 只产生子类型关系 |
| `equals` 相等 | `hashCode` 相等 | 前者蕴含后者；后者不蕴含前者（允许碰撞）。哈希容器两者都要用 |
| 参数类型必须相同 | 返回类型可以协变 | 重写时参数**不变**（否则是重载）；返回类型可以是父类返回类型的**子类型** |
| 签名兼容 | 行为兼容 | 前者由编译器检查；后者（behavioral subtyping）只能靠规格与人工保证，`Cowboy.draw()` 就是签名合法但行为非法 |

## 8. 对应原版讲义

- PDF 相对路径：`90-原始PDF/15-214/slides/04_Inheritance,_type-checking,_and_Method_dispatch.pdf`
- 总页数：46 页
- 本节重点页码：
  - 第 7–11 页：继承 vs 组合复习、`super`、构造函数链
  - 第 12–14 页：`final` 三种用法、强制转换、`instanceof`
  - 第 15–16 页：用模板方法消除 `instanceof` 的前后对照
  - 第 17–20 页：类型检查的定义与收益、值流、子类型关系、子类型规则
  - 第 21–22 页：方法分派四步（含重载解析）
  - 第 23–30 页：七道分派练习（A、B-1、B-2、C、D、E-1、E-2）
  - 第 31–33 页：`java.lang.Object` 的常用方法、`Point` 重载陷阱
  - 第 34–37 页：`equals` 契约、`hashCode` 契约、`clone` 契约
  - 第 38–46 页：`ColorPoint` 的四种尝试与抽象解法
- 原始网页链接：`https://www.cs.cmu.edu/~aldrich/214/slides/04_Inheritance,%20type-checking,%20and%20Method%20dispatch.pdf`
- > 待核实：第 41–46 页的 `if (!(obj instanceof Point)` 缺右括号；第 26–30 页练习的答案未在 slides 中给出，本笔记的答案表由分派规则推导。

## 9. 对应视频

未找到官方公开录像。2013 年秋季的 15-214 课堂没有公开发布录像，故不提供链接与时间戳。

## 10. 本节复习

- 类型检查 = 判断每个操作是否适用于其作用的类型；收益是早发现错误 + 文档化。
- 值流三检查：赋值、传参、返回，都要求 `Tsource <: Tdest`。
- `A <: B` 的基本情形是 `extends` / `implements` / 自反；归纳情形是传递。
- 重写规则：参数类型完全相同，返回类型可协变；再加一条行为必须符合父类规格。
- 分派四步：静态类型找起点 → 编译期选最具体签名 → 运行期取动态类 → 沿父类链找实现。
- `Object.equals` 默认是 `this == obj`；写 `equals(Point)` 只是重载，不起作用。
- `equals` 要满足自反、对称、传递、一致、非空；`hashCode` 要一致且「相等蕴含同哈希」。
- 继承层次里加字段会让 `equals` 的对称性/传递性同时告急，抽象父类是一种解法。

## 11. 自我检查

1. 有 `class A {}`、`class B extends A {}`、`class C extends B {}`、`interface I {}`、`class D extends B implements I {}`。请列出所有成立的 `X <: Y` 关系对（只列直接与传递得到的，不列无意义的）。
2. 已知
   ```java
   class P { public String f(Object o) { return "P(Object)"; } }
   class Q extends P { public String f(String s) { return "Q(String)"; } }
   P p = new Q(); System.out.println(p.f("hi"));
   ```
   输出什么？如果把 `Q` 的方法改成 `public String f(Object o)` 又输出什么？请用分派四步解释。
3. 为什么 `x.hashCode() == y.hashCode()` 不能推出 `x.equals(y)`？请给出一个具体的、合法的反例（不需要写完整代码，说清构造即可）。
4. 在 `ColorPoint` 难题中，课件的最终解法是「把 `Point` 改成抽象类」。请说明这个改动消除了哪一个具体场景，从而使对称性问题不再出现。如果业务上确实需要「无色点」与「有色点」可以直接比较，你会怎么设计？

<details>
<summary>参考答案</summary>

1. 成立的：`B <: A`、`C <: B`、`C <: A`（传递）、`D <: B`、`D <: A`（传递）、`D <: I`；以及各自的自反关系 `A <: A`、`B <: B` 等。`A <: B`、`B <: C` 等反向关系不成立。

2. 第一次输出 `P(Object)`。四步：(1) 接收者 `p` 的静态类型是 `P`；(2) 实参 `"hi"` 是 `String`，在 `P` 中只有一个 `f(Object)`，`String <: Object` 适用，选中签名 `f(Object)`；(3) 运行期动态类是 `Q`；(4) 从 `Q` 开始找**签名 `f(Object)`**——`Q` 只有 `f(String)`，签名不同，不算重写，于是上移到 `P`，调用 `P.f(Object)`。第二次（`Q` 重写 `f(Object)`）输出 `Q(Object)`：第 2 步仍选 `f(Object)`，第 4 步在 `Q` 中直接找到同签名实现。这个对比说明「重载在编译期定，重写在运行期定」。

3. 因为哈希是「把无限多的对象映射到有限整数」，必然碰撞。合法反例：`String` 类中 `"Aa"` 与 `"BB"` 的 `hashCode()` 相同（都等于 2112），但 `equals` 为 `false`。另一个通用构造：任何自定义类都可以让 `hashCode()` 恒返回 `0`——满足契约（相等对象哈希必相等），但所有不相等对象也同哈希。

4. 消除的场景是「一个**裸 `Point` 实例**与一个 `ColorPoint` 实例互相比较」。抽象 `Point` 不能 `new`，所有点要么是 `ColorPoint`（带颜色）要么是 `PointImpl`（不带），而 `ColorPoint.equals` 只接受 `ColorPoint`、`PointImpl.equals` 只接受 `PointImpl`，两者互不相等且**双向都返回 false**，于是对称性自动成立。如果业务要求「无色点可以与有色点比较且只比坐标」，可让 `ColorPoint` 不继承 `Point` 而是各自实现一个 `PointLike` 接口，并统一规定「颜色不参与相等」；或者干脆放弃「点相等」语义，改用显式的 `sameCoordinates(PointLike)` 方法，把「按坐标比较」与「按对象等价比较」分开。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-03-Encapsulation-and-Inheritance]]
- 下一讲：[[15-214-05-Object-Contracts-and-Exceptions]]
- 课程总览：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]
- 课程目录：[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸：Josh Bloch《Effective Java》第 10–11 条（`equals` 与 `hashCode`）；本讲的行为子类型概念会在第 5 讲展开为完整的契约式设计。
