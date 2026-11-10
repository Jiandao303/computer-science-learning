---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L02
topic: Objects, Encapsulation, Polymorphism, Equality
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 面向对象
  - 封装
  - 多态
  - 相等性
---

# 第 2 讲 对象、封装、多态与相等性（Objects, Encapsulation, Polymorphism, Equality）

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。

## 1. 本节学习目标

- 能用接口（interface）与类（class）分别表达「期望」与「交付」，并解释二者的分工。
- 能对一段客户端代码逐步做类型检查（typechecking），指出每一步检查依据的是哪个声明。
- 能解释动态分派（dynamic dispatch）的四步过程，并预测任意「父类引用指向子类对象」的调用结果。
- 能区分对象标识（identity，`==`）与对象等价（equality，`equals`），并说明字符串字面量带来的陷阱。
- 能判断一个类是否构成组合（Composite）：它是否「把其它对象组合起来，却与被组合对象行为一致」。

## 2. 前置知识

- [[15-214-01-Course-Intro-and-Organization]]：对象 = 状态 + 行为，类 = 模板，`new` 在堆上分配并调用构造函数。
- 外部概念：Java 的基本语法、引用与堆栈的区别；C 语言的头文件（用于类比 interface）。

## 3. 核心概念

- **Interface（接口）**：只列出「一个对象能理解哪些消息」的类型声明，不含实例字段，也不含方法体。课件把它类比为 C 的头文件，但强调差别：接口描述的是**对象理解的消息集合**。
- **Implementation（实现）**：用类（class）为接口中的每条消息提供方法体。漏写一个方法或改动签名都会编译报错。
- **Subtype（子类型）**：`class A implements I` 或 `class A extends B` 都使 A 成为 I/B 的子类型，因此 A 的实例可以赋给 I/B 类型的变量。
- **Receiver（接收者）**：方法调用 `s.contains(0)` 中 `s` 所指的对象，在方法体内以 `this` 访问，是一个隐式参数。
- **Dynamic Dispatch（动态分派）**：编译期按**静态类型**确定「到哪个类型里找方法签名」，运行期按**对象真实类**确定「调用哪份实现」。
- **Polymorphism（多态）**：「多种形态」。同一个 `IntSet` 变量可以指向 `EmptySet` 或 `SingletonSet`，行为随实际形态而变。
- **Composite（组合）**：一个自身也实现了某接口、内部却持有若干同接口对象的类。`UnionSet` 是典型：它由集合组成，本身也是集合，因此可以嵌套。
- **Object Identity（对象标识）**：两个引用是否指向堆上同一个对象，用 `==` 判断。
- **Object Equality（对象等价）**：两个（可能不同的）对象在客户端看来内容是否等价，用 `equals` 判断。
- **Encapsulation（封装）**：字段设为 `private`，外部只能通过方法访问；接口中的所有方法隐式 `public`。

## 4. 通俗理解

把接口想成**餐厅菜单**，类想成**厨房**：

- 菜单（interface）告诉你「可以点哪些菜」，不告诉你厨房用什么锅。
- 厨房（class）负责真正做出来。换一个厨房（换实现），菜单不变，顾客不用重新学习点菜。
- 你点「宫保鸡丁」（发消息），厨房按自己的做法出品（动态分派）——同一个菜名，不同分店味道不同（多态）。

一个具体例子（课件第 18–21 页）：下面这段代码打印什么？

```java
IntSet s1 = new EmptySet();
IntSet s2 = new SingletonSet(5);
IntSet temp = s1;
s1 = s2;
s2 = temp;
System.out.println(s1.contains(5));   // true
System.out.println(s2.contains(5));   // false
```

只是交换了两个引用。`s1` 现在指向那个「只含 5」的集合，所以打印 `true`；`s2` 指向空集，打印 `false`。这说明变量里存的是**指向对象的引用**，赋值只改指向，不改对象。

## 5. 原理与推导

### 5.1 从「数学集合」推出接口

课件第 3–4 页的推导很干净：

1. 我们与对象交流的方式是**发消息**（等价于调用方法）。
2. 那么「一个集合应该能理解哪些消息」？提示是：想想数学里的集合运算。
3. 于是得到最小接口：

```java
interface IntSet {
    /** does the IntSet contain element? */
    boolean contains(int element);
    /** is the IntSet a subset of otherSet? */
    boolean isSubsetOf(IntSet otherSet);
}
```

注意 `isSubsetOf` 的参数类型是 `IntSet` 而不是某个具体类——这一开始就为多态留了口子。

### 5.2 用类「交付」接口

```java
class EmptySet implements IntSet {
    public boolean contains(int element) { return false; }
    public boolean isSubsetOf(IntSet otherSet) { return true; }
}
```

课件第 5–7 页特意演示了「只写一半」的中间状态：如果只实现 `contains`，编译器报错

```
error: method isSubsetOf from interface IntSet is not implemented
```

这条错误的含义是：**实现接口是一份全或无的承诺**，不能只交付一部分。

`SingletonSet` 展示了一个有状态的实现：

```java
class SingletonSet implements IntSet {
    private int member;
    public SingletonSet(int element) { member = element; }
    public boolean contains(int e) { return member == e; }
    public boolean isSubsetOf(IntSet otherSet) { return otherSet.contains(member); }
}
```

`isSubsetOf` 的实现体现了「面向接口编程」：它不关心 `otherSet` 具体是哪种集合，只发一条 `contains` 消息。

### 5.3 类型检查：五个检查点

课件第 9 页把 `IntSet s = new EmptySet(); boolean f = s.contains(0);` 拆成五步：

1. `new EmptySet()` 表达式的类型是 `EmptySet`。
2. 把 `EmptySet` 赋给 `IntSet` 合法，因为 `EmptySet implements IntSet`（子类型关系）。
3. `s` 的静态类型是 `IntSet`，因此编译器在 `IntSet` 中查找名为 `contains` 的方法。
4. `IntSet.contains` 接受一个 `int`，实参 `0` 是 `int`，合法。
5. `contains` 返回 `boolean`，赋给 `boolean f` 合法。

课件第 10 页用一段**故意写错**的代码展示五类错误：

```java
EmptySet s = new IntSet();          // 错误 1：接口不能实例化
                                    // 错误 2：IntSet 不是 EmptySet 的子类型，不能赋值
int f = s.contans("hello");         // 错误 3：拼写错误，EmptySet 没有 contans
                                    // 错误 4：参数类型错，String 不是 int 的子类型
                                    // 错误 5：返回 boolean 不能赋给 int（与 C 不同）
```

第 5 条值得单独记：Java 的 `boolean` 与 `int` 之间**没有**隐式转换，这一点和 C 不同。

### 5.4 动态分派：编译期两步 + 运行期两步

课件第 48–49 页（以及第 4 讲第 21–22 页的完整版）给出四步：

| 阶段 | 步骤 | 依据 |
|---|---|---|
| 编译期 | 1. 确定到哪个类型里找 | 接收者表达式的**静态类型** |
| 编译期 | 2. 确定方法签名 | 在该类型（及其父类型）中找同名、可访问、参数适用的方法；多个时选最具体的一个 |
| 运行期 | 3. 确定接收者的动态类 | 堆上对象头里记录的类 |
| 运行期 | 4. 定位实现并调用 | 从动态类开始向上查找与第 2 步签名相同的方法 |

关键结论：**方法名在编译期绑定，方法实现在运行期绑定**。这就是为什么 `IntSet s = new EmptySet();` 之后 `s.contains(0)` 不会去 `IntSet` 里找方法体（接口根本没有方法体），而是去 `EmptySet` 里找。

课件第 50–52 页的链表拼接练习是这套规则的实战：`fourList.concatenate(fiveList)` 中 `fourList` 的静态类型是 `IntList`，动态类是 `IntListCell`；`IntListCell.concatenate` 内部又调用 `next.concatenate(other)`，此时 `next` 指向 `EmptyIntList` 实例，因此调用的是 `EmptyIntList.concatenate`，直接返回 `other`。最终结果是「4 后面接 5」的新链表。

### 5.5 组合：UnionSet 与递归结构

```java
interface IntSet {
    boolean contains(int element);
    boolean isSubsetOf(IntSet otherSet);
    IntSet union(IntSet otherSet);
}

class UnionSet implements IntSet {
    private IntSet set1;
    private IntSet set2;
    public UnionSet(IntSet s1, IntSet s2) { set1 = s1; set2 = s2; }
    public boolean contains(int elem) { return set1.contains(elem) || set2.contains(elem); }
    public boolean isSubsetOf(IntSet otherSet) {
        return set1.isSubsetOf(otherSet) && set2.isSubsetOf(otherSet);
    }
    public IntSet union(IntSet otherSet) { return new UnionSet(this, otherSet); }
}
```

课件第 24 页的批注是本节最重要的一句设计观察：`UnionSet` 是 **Composite**——「一个把其它对象组合起来、行为却与被组合对象一样的对象」。因为 `union` 返回 `new UnionSet(this, otherSet)`，你可以把 `UnionSet` 再组合进 `UnionSet`，结构可以任意深度嵌套，而客户端代码完全不需要知道深度。

> 待核实：课件第 23 页打印的 `isSubsetOf` 实现写成 `set1.isSubsetOf(elem) && set2.isSubsetOf(elem)`，参数名 `elem` 在该方法作用域内并不存在，应为 `otherSet`。第 24 页的版本仍是 `elem`，推断是幻灯片笔误。

### 5.6 接口 vs 类：期望与交付

课件第 26–31 页把这条分界讲成三条 OO 原则：

1. 围绕**抽象对象的种类**组织功能：每种对象提供一组操作，对象本身不透明，表示细节隐藏，操作即「发给接收者的消息」。
2. **区分接口与类**：接口 = 期望（expectations），类 = 对期望的交付（delivery）。
3. 显式表达对象类型的分类体系（taxonomy），即继承层次：「正方形是一种形状」。

由此得出两条最佳实践（第 29 页）：

- **只要一个概念可能有多种实现，就定义接口。**
- **变量应该声明为接口类型，而不是类类型。**

```java
int sum(UnionSet set) { … }   // 不推荐
int sum(IntSet set) { … }     // 推荐
```

课件第 30–31 页还提醒：类可以**额外**定义接口里没有的 public 方法（如 `getMember()`），但通过接口类型的变量看不到它们：

```java
IntSet s = new SingletonSet(4);
SingletonSet ss = new SingletonSet(3);
int i = ss.getMember();   // OK
int j = s.getMember();    // 错误：IntSet 中没有 getMember
```

### 5.7 对象标识 vs 对象等价

课件第 33 页给出两种「相等」：

- **同一个对象**：引用相同，`s1 == s2`。
- **内容等价**：可能是不同对象，但客户端看来内容相同，`s1.equals(s2)`。

```java
String s1 = new String("abc");
String s2 = new String("abc");
// 两个不同的 String 对象
if (s1 == s2) { /* 同一个对象 */ } else { /* 不同对象 */ }        // 走 else
if (s1.equals(s2)) { /* 内容等价 */ } else { /* 不等价 */ }        // 走 if
```

字面量的陷阱：

```java
String s3 = "abc";
String s4 = "abc";
// s3 == s4        → true（同一个驻留字符串对象）
// s3.equals(s2)   → true（内容相同）
// s2 != s3        → true（s2 是 new 出来的另一个对象）
```

结论：**永远用 `equals` 比较内容，用 `==` 只比较「是不是同一个对象」**。`equals` 由 `String` 类自己定义（第 4 讲会展开它的契约）。

### 5.8 用归纳定义驱动实现

课件第 35–46 页用函数式整数链表把「接口 → 多个实现 → 递归」串起来：

```java
public interface IntList {
    int size();
    int get(int n);
    IntList concatenate(IntList otherList);
    String toString();
}
```

`size` 的**归纳定义**（第 38 页）：空表为 0；否则为 `1 + 尾表的 size`。于是两个实现类自然分工：

```java
public class EmptyIntList implements IntList {
    public int size() { return 0; }                 // 基础情形
    …
}
public class IntListCell implements IntList {
    private int value;
    private IntList next;                            // 注意：接口类型
    public int size() { return 1 + next.size(); }    // 归纳情形
    …
}
```

课件第 40 页特意展示了一个**错误版本**：把 `next` 声明成 `IntListCell` 类型。这样 `next` 就不能指向 `EmptyIntList`，链表的最后一段无处安放。修正就是把字段类型改成接口 `IntList`——「接口类型提供了所需的灵活性」。

复杂度对比（第 37 页表格，部分格子在原文中留空，由本笔记补全）：

| 操作 | 数组实现 | 链表实现 |
|---|---|---|
| 创建空表 | 常数 | 常数 |
| 返回 size | 常数（需维护计数字段） | 线性（要走到尾部） |
| 取第 i 个元素 | 常数（下标访问） | 线性 |
| 在头部添加 | 线性（要搬移）或需预留空间 | 常数 |
| 拼接两个表 | 线性（复制） | 线性（复制左侧） |

这张表本身就是「接口的价值」的证明：同一组操作，两种实现的代价结构完全不同，客户端按需选择，而代码不用改。

## 6. 代码示例

### 6.1 官方课程代码

出自 `02-objects.pdf` 第 22–24 页（`UnionSet`，含 Composite 批注）：

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
    public boolean isSubsetOf(IntSet otherSet) {
        return set1.isSubsetOf(elem) && set2.isSubsetOf(elem);   // 原文如此
    }
    public IntSet union(IntSet otherSet) { return new UnionSet(this, otherSet); }
}
```

出自同文件第 46 页（`concatenate` 的基础情形与归纳情形）：

```java
public class EmptyIntList implements IntList {
    public IntList concatenate(IntList other) { return other; }   // 基础情形
}
public class IntListCell implements IntList {
    public IntList concatenate(IntList other) {
        IntList newNext = next.concatenate(other);                 // 先拼尾部
        return new IntListCell(value, newNext);                    // 再造新头
    }
}
```

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

下面用「图形」演示同一套「接口 + 多态 + 组合」的结构，并额外演示「通过接口类型调用不到类私有扩展方法」这一编译期事实：

```java
interface Shape {
    double area();
    String name();
}

class Circle implements Shape {
    private final double r;
    Circle(double r) { this.r = r; }
    public double area() { return Math.PI * r * r; }
    public String name() { return "circle"; }
    public double radius() { return r; }          // 接口之外的扩展方法
}

class Rect implements Shape {
    private final double w, h;
    Rect(double w, double h) { this.w = w; this.h = h; }
    public double area() { return w * h; }
    public String name() { return "rect"; }
}

// 组合：一组图形本身也是图形
class Group implements Shape {
    private final java.util.List<Shape> parts = new java.util.ArrayList<>();
    void add(Shape s) { parts.add(s); }
    public double area() {
        double total = 0;
        for (Shape s : parts) total += s.area();   // 动态分派：逐个问它自己的面积
        return total;
    }
    public String name() { return "group(" + parts.size() + ")"; }
}

public class Demo {
    public static void main(String[] args) {
        Shape c = new Circle(1.0);
        Group g = new Group();
        g.add(c);
        g.add(new Rect(2, 3));
        g.add(new Group());                 // 组合可以嵌套
        System.out.println(g.area());       // 3.14159... + 6 + 0
        // c.radius();                      // 编译错误：Shape 中没有 radius
        Circle cc = (Circle) c;
        System.out.println(cc.radius());    // 强制转换后才可见
    }
}
```

要点：`Group.area()` 里的 `s.area()` 是**一次**动态分派，但因为 `parts` 里可以再放 `Group`，递归地就得到了任意深度的树求和——客户端完全不需要写 `if (是圆) … else if (是矩形) …`。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| Interface（接口） | Class（类） | 接口只声明期望、无实例字段、不能 `new`；类提供方法体、可有字段、可以 `new` |
| Static type（静态类型） | Dynamic class（动态类） | 变量的声明类型决定编译期能调用哪些方法；对象的实际类决定运行期执行哪份实现 |
| `==` | `equals` | `==` 比较引用是否指向同一对象；`equals` 比较客户端视角下的内容等价，默认实现等同于 `==` |
| Overriding（重写） | Overloading（重载） | 重写是子类用相同签名替换父类方法（运行期分派）；重载是同类中同名不同参数（编译期选最具体） |
| Composite（组合模式） | Composition（组合/持有） | Composite 是一种特殊组合：容器自身实现同一接口，可与被容纳对象同等对待；普通组合只是「has-a」 |
| `implements` | `extends` | `implements` 承诺实现接口全部方法（可多个）；`extends` 继承类实现（只能一个） |

## 8. 对应原版讲义

- PDF 相对路径：`90-原始PDF/15-214/slides/02-objects.pdf`
- 总页数：53 页
- 本节重点页码：
  - 第 3–8 页：从集合运算推出 `IntSet` 接口、`EmptySet` 实现、客户端调用
  - 第 9–10 页：类型检查五个检查点与五类错误
  - 第 11–13 页：执行期的方法查找过程
  - 第 14–17 页：`SingletonSet`、隐式构造函数、字段可见性
  - 第 18–21 页：引用交换实验、动态分派与多态的定义
  - 第 22–24 页：`UnionSet` 与 Composite
  - 第 26–31 页：契约与客户、接口 vs 类、变量应声明为接口类型
  - 第 33 页：对象标识 vs 对象等价（含字符串字面量陷阱）
  - 第 35–46 页：`IntList` 的归纳定义、错误与修正后的表示、`concatenate`
  - 第 48–52 页：分派四步与链表拼接练习答案
- 原始网页链接：`https://www.cs.cmu.edu/~aldrich/214/slides/02-objects.pdf`
- > 待核实：第 23–24 页 `isSubsetOf` 中的 `elem` 变量名疑似笔误（应为 `otherSet`）。

## 9. 对应视频

未找到官方公开录像。本讲对应的 2013 年秋季课堂录像没有公开发布，故不提供链接与时间戳。

## 10. 本节复习

- 接口 = 期望，类 = 交付；实现接口是「全或无」的承诺。
- 变量声明为接口类型，可以容纳任何实现，并在将来替换实现而不改客户端。
- 类型检查看**静态类型**；方法执行看**动态类**。四步：编译期找类型、编译期定签名、运行期取类、运行期找实现。
- Composite 的标志：容器实现了与被容纳者相同的接口，因此可以自嵌套。
- `==` 比身份，`equals` 比内容；字符串字面量会被驻留，导致 `==` 偶然为真。
- 归纳定义（基础情形 + 归纳情形）天然对应「两个实现类 + 递归方法」。
- 字段类型要用接口而不是具体类，否则表示会被锁死。

## 11. 自我检查

1. 已知 `IntSet s = new UnionSet(new EmptySet(), new SingletonSet(5));`，请写出 `s.contains(5)` 从编译到执行的完整四步，并说明每一步依据的是静态类型还是动态类。
2. 如果把 `IntListCell.next` 声明成 `IntListCell` 而不是 `IntList`，为什么「在空表前插入一个元素」这个操作就无法表示？请画出两种声明下的对象图。
3. 下面两行代码的结果为什么不同？
   ```java
   String a = new String("abc");
   String b = "abc";
   System.out.println(a == b);        // ?
   System.out.println(a.equals(b));   // ?
   ```
4. `UnionSet` 为什么被称为 Composite？请说明它满足哪两个条件，并给出一个「不是 Composite 的组合」的反例。

<details>
<summary>参考答案</summary>

1. (a) 编译期：`s` 的静态类型是 `IntSet`，在 `IntSet` 中查找 `contains(int)` —— 依据**静态类型**；(b) 编译期：确认 `contains` 可访问（接口方法隐式 public）、实参 `5` 是 `int`，确定签名 `contains(int)` —— 依据**静态类型与实参类型**；(c) 运行期：读取 `s` 指向的堆对象，得到其动态类 `UnionSet` —— 依据**动态类**；(d) 运行期：从 `UnionSet` 开始查找签名 `contains(int)` 的实现，找到并调用；其中 `set1.contains(elem)` 与 `set2.contains(elem)` 各自再走一遍这四步（分别分派到 `EmptySet.contains` 与 `SingletonSet.contains`）。结果是 `false || true = true`。

2. 若 `next` 声明为 `IntListCell`，则「空表」`EmptyIntList` 不是 `IntListCell` 的子类型，无法赋给 `next`，因此链表必须至少有一个元素，无法表示长度为 0 的链表，也无法表示尾部为空。对象图上：`IntList` 版本是 `IntListCell(value=5) → EmptyIntList`；`IntListCell` 版本要么编译失败，要么必须引入哨兵节点（把空表伪装成一个 `IntListCell`），从而污染 `size()` 的基础情形。

3. `a == b` 为 `false`：`new String("abc")` 在堆上新建对象，而字面量 `"abc"` 指向字符串常量池中的驻留对象，两者引用不同。`a.equals(b)` 为 `true`：`String.equals` 按字符内容比较。这正说明「`==` 判身份、`equals` 判内容」。

4. 两个条件：(a) `UnionSet` 实现了 `IntSet`，与被组合对象具有**相同接口**；(b) 它内部持有若干 `IntSet`（`set1`、`set2`），并在方法中把请求**转发**给它们。反例：`class Car { Engine e; }`——`Car` 不实现 `Engine` 接口，也不能当作 `Engine` 使用，这只是普通组合（has-a），不是 Composite。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-01-Course-Intro-and-Organization]]
- 下一讲：[[15-214-03-Encapsulation-and-Inheritance]]
- 课程总览：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]
- 课程目录：[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 相关主题：第 4 讲会把本节的分派规则补全为「重载解析 + 重写分派」，并给出 `equals` 的完整契约与 `ColorPoint` 难题。
