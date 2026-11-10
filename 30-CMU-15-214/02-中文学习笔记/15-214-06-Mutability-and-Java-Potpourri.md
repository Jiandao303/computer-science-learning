---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L06
topic: Mutability and Java Potpourri
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 可变性
  - 不可变性
  - static
  - 内部类
  - 泛型
---

# 第 6 讲 可变性与 Java 杂烩（Mutability and Java Potpourri）

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。

## 1. 本节学习目标

- 能区分「变量不可变」与「对象不可变」，并解释 `final List<Integer>` 为什么仍可 `add`。
- 能说出可变与不可变各自的优势场景，并按课件第 10 页的五条建议写出一个不可变类。
- 能说明 `static` 字段/方法与实例字段/方法的区别，并解释 `main` 为什么必须是 `static`。
- 能写出内部类（含 `private static class Node`）并说明它解决了什么封装问题。
- 能识别变量遮蔽（variable shadowing）与块作用域陷阱（`try` 块内声明的变量在块外不可见）。
- 能用泛型 `Stack<T>` 替代 `Object` + 强制转换，并说明它改善了类型检查。

## 2. 前置知识

- [[15-214-05-Object-Contracts-and-Exceptions]]：`Object` 的契约、异常基础。
- [[15-214-03-Encapsulation-and-Inheritance]]：可见性修饰符、信息隐藏。
- [[15-214-02-Objects-Encapsulation-Polymorphism]]：接口类型、静态类型 vs 动态类。
- 外部概念：Java 集合框架的基本接口（`Collection`/`List`/`Set`）。

## 3. 核心概念

- **Mutability（可变性）**：数据可以随时间改变。
- **Immutability（不可变性）**：数据一旦创建就不可改变。
- **`final` 字段**：引用一旦赋值不可再指向别的对象——但被引用对象的内容仍可改变。
- **Defensive Copy（防御性拷贝）**：把外部传入的可变数据复制一份自己保存，避免别名共享。
- **Leak（泄漏）**：把内部可变数据（尤其是数组/集合的引用）交给外部。
- **`static`（静态）**：属于类本身而不是某个实例的字段或方法，又称类字段/类方法。
- **Inner Class（内部类）**：定义在另一个类（甚至方法）内部的类。
- **Variable Shadowing（变量遮蔽）**：内层作用域的同名声明遮住外层同名变量。
- **Scope（作用域）**：由花括号界定，变量在其声明所在块内可见。
- **Generics（泛型）**：用类型参数 `T` 让一个类/方法适用于多种类型，同时保留编译期类型检查。
- **Type Polymorphism（类型多态）**：同一份代码对多种类型工作。

## 4. 通俗理解

**不可变对象**像打印好的 PDF：你拿到手之后内容不会变，谁读都一样，可以随便复印分发，不用担心别人改了影响你。

**可变对象**像共享的 Google Doc：方便多人协作修改，但你得时刻担心「我看到的还是我刚才读的那段吗」。

课件的 `String` 双版本对比把这件事说得最清楚。第 6 页的「一种可能的 `String` 实现」：

```java
public class String {
    private char value[];
    public void concat(String s) { … value = newValue; }     // 改自己
    public void replace(char old, char new) { … value[i] = new; }  // 改自己
}
```

第 7 页的「另一种可能的实现」：

```java
public class String {
    private final char value[];
    public String concat(String s) { … return new String(newValue); }   // 造新的
    public String replace(char old, char new) { … return new String(newValue); }  // 造新的
}
```

差别只有两处：字段加 `final`、方法从「改自己」变成「返回新对象」。这两处差别决定了 `String` 能不能被安全地当作 `HashMap` 的键、能不能在线程间自由共享、能不能被字符串常量池（string interning）复用。

Java 选择了第二个版本。这不是风格偏好，而是**为了让 `String` 能作为值使用**。

## 5. 原理与推导

### 5.1 可变 vs 不可变：定义与 `final` 的边界

课件第 8 页的定义：**数据可以随时间变化就是可变的，否则不可变。**

紧接着一个关键澄清：`final` 变量强制的是「这个变量不能再指向别的对象」，**不**保证它引用的数据不可变：

```java
final List<Integer> vals = new ArrayList<Integer>();

vals.add(42);                       // OK even though it changes the list
vals = new ArrayList<Integer>();    // Not OK because it changes vals
```

用内存模型的语言说：`final` 冻结的是**引用（指针）**，不是**被指向的对象**。所以「不可变类」的完整要求是：所有字段 `private final` + 字段类型本身不可变（或是可变类型的防御性拷贝且从不外泄）。

### 5.2 可变与不可变的取舍

课件第 9 页标题为 `Advantages: Mutability vs. Immutability`，但正文内容在提取的文本中为空（应为排版在图形/表格中）。

> 待核实：第 9 页的具体对照表在文本提取结果中缺失，以下取舍分析依据课件第 10 页的建议与通用软件工程结论整理，非逐字复述原页。

| 维度 | 可变（Mutable） | 不可变（Immutable） |
|---|---|---|
| 修改成本 | 原地修改，O(1)，无分配 | 每次修改都要复制，O(n) 分配 |
| 别名安全 | 需小心共享，易出意外耦合 | 可自由共享，无需防御性拷贝 |
| 作为哈希键 | 修改后哈希变化，容器中会「丢失」 | 哈希恒定，安全 |
| 线程安全 | 需加锁或同步 | 天然线程安全（无写入） |
| 推理难度 | 任何方法调用都可能改变状态 | 状态只由构造决定，易于推理 |
| 典型代表 | `ArrayList`、`StringBuilder`、`Date` | `String`、`Integer`、`LocalDate` |

选择原则可以概括为一句话：**默认选不可变，只有当性能剖析证明复制是瓶颈、或状态确实需要频繁原地演进时才用可变**。

### 5.3 写出不可变类的五条建议

课件第 10 页：

1. **Make all data private and final**——所有数据私有且 `final`。
2. **Guarantee exclusive access to your data**——保证对数据的独占访问。
3. **Defensively copy your data**——对传入的可变数据做防御性拷贝。
4. **Don't leak your data**——不要把内部可变数据的引用交出去（包括 getter 直接返回内部数组）。
5. **Don't provide public mutator methods** + **Make your classes final**——不提供公有修改方法；把类声明为 `final`，防止子类「加回」可变性。

第 5 条的第二半常被忽略：如果类不是 `final`，子类可以添加可变字段并重写方法，父类的「不可变」承诺就被打破了。`String` 正是 `final` 的。

第 4 条也有个微妙处：即使字段是 `private final int[]`，只要 getter 返回这个数组本身，调用者就能改内容——`final` 只保护引用。正确做法是返回 `Arrays.copyOf(...)` 或返回不可变视图。

### 5.4 `static`：属于类而非实例

课件第 12 页的定义：**若一个属性关联于类（而不是类的某个实例），它就是静态的**，又称类字段（class fields）与类方法（class methods）。

课件举了三个例子：

1. **简单的 `Counter`**——计数器通常做成类字段，所有实例共享同一个计数。
2. **`main` 方法——为什么是 `static`？** 因为 JVM 在启动时还没有任何对象，它必须能在「不创建实例」的前提下调用入口点。若 `main` 不是 `static`，JVM 就得先知道该 `new` 哪个类、用哪个构造函数——这形成了先有鸡还是先有蛋的循环。
3. **`java.lang.String.valueOf` 系列**——把各种类型转成字符串的工厂方法，不需要任何 `String` 实例作为接收者。

一个推论：`static` 方法内部**不能**直接访问实例字段或 `this`，因为它没有接收者。这也是为什么工具方法（utility methods）都写成 `static`。

### 5.5 内部类

课件第 13 页：**类可以定义在其他类内部，甚至定义在类的方法内部。**

```java
public class LinkedList {
    private static class Node {
        public int val;
        public Node next;
        public Node(int v, Node n) {
            val = v;
            next = n;
        }
    }
    Node head;
    // …
}
```

这个例子的价值在 `private static`：`Node` 是链表实现的细节，外界既不需要也不应该看到它。如果把它做成顶层类（top-level class），它要么必须是 `public`（污染 API），要么必须在同包内可见（`LinkedList` 的表示就部分暴露给了同包的所有类）。放在内部并标 `private`，信息隐藏才彻底。

`static` 在这里的含义是「不持有外部类实例的引用」。非静态内部类（inner class）会隐式持有 `Outer.this`，因此可以访问外部实例的字段——这在实现迭代器（iterator）时非常有用，但也意味着每个内部类实例都多一个指针。

### 5.6 变量遮蔽与作用域

课件第 14 页：**变量遮蔽指内层作用域中的名字与外层作用域中的名字相同。**

```java
public class Dog {
    String name;                                  // 实例变量
    public Dog(String name) {                     // 参数遮蔽了实例变量
        this.name = name;                         // 用 this 消除歧义
    }
}
```

Java 有三种变量：类变量（`static`）、实例变量、局部变量。课件列出的遮蔽情形：

- 局部变量可以遮蔽实例变量或类变量；
- 子类的变量可以遮蔽父类的变量。

最后一条值得单独警惕：字段**不参与动态分派**（第 4 讲的分派只针对方法），所以「子类同名字段」不是重写而是两个独立字段，通过不同的静态类型访问会看到不同的值。这是 Java 中一个经典的困惑源。

**块作用域陷阱**（第 15 页）：

```java
public void printAsInt(String s) {
    try {
        Integer x = Integer.valueOf(s);
    } catch (NumberFormatException e) {
        // we ignore the exception!
    }
    System.out.println(x);   // x is undefined
}
```

`x` 声明在 `try` 的块内，块一结束就不可见，所以最后一行**编译错误**（`cannot find symbol`）。这与 JavaScript 的 `var` 函数作用域形成鲜明对比，也是 Java 强制「声明尽量靠近使用点、作用域尽量小」的语言级体现。

顺带一提，这段代码还有一个逻辑问题：即使把 `x` 提到 `try` 外面，一旦解析失败 `x` 就是 `null`（或未初始化），后面的打印要么 NPE 要么打印 `null`——「忽略异常」正是第 5 讲列为坏实践的行为。

### 5.7 泛型：从 `Object` + 强制转换到 `Stack<T>`

课件第 16 页先复习了集合 API 的骨架：

```
Collection
├── List          → AbstractList → ArrayList / LinkedList / Vector
│                   AbstractSequentialList
└── Set           → AbstractSet  → HashSet
（Cloneable 为标记接口）
```

然后第 17–19 页用一个 `Stack` 讲泛型的动机。**泛型之前**（第 17 页）：

```java
public class Stack {
    public void push(Object obj) { … }
    public Object pop() { … }
}
```

客户端：

```java
Stack stack = new Stack();
String s = "Hello!";
stack.push(s);
String t = stack.pop();      // 编译错误：Object 不能赋给 String
```

必须强转（第 18 页）：

```java
String t = (String) stack.pop();   // To fix the type error
```

问题在于：编译器**无法**检查你转换得对不对。`stack.push(Integer.valueOf(42))` 完全合法，之后 `(String) stack.pop()` 会在运行期抛 `ClassCastException`——错误从编译期推迟到了运行期，而且可能在上线后才出现。

**泛型之后**（第 19 页）：

```java
public class Stack<T> {
    public void push(T obj) { … }
    public T pop() { … }
}

Stack<String> stack = new Stack<String>();
String s = "Hello!";
stack.push(s);
String t = stack.pop();      // 无需强转
```

课件对收益的表述是 `Improves typechecking, simplifies(?) client code`——那个问号很有意思：客户端确实不用强转了，但声明处多了 `<String>` 这样的类型参数，代码噪音增加。总体上收益远大于成本，因为**类型错误从运行期移回了编译期**。

需要提醒的是，Java 泛型是**类型擦除（type erasure）**实现的：`Stack<String>` 与 `Stack<Integer>` 在运行期是同一个类，`T` 在字节码中被擦成 `Object`（或有界类型）。这带来两个限制：不能 `new T[]`，不能对 `T` 做 `instanceof` 检查。这一点课件未展开，但会在后续课程中反复出现。

## 6. 代码示例

### 6.1 官方课程代码

出自 `06_Mutability_and_Java_Potpourri.pdf` 第 7 页（不可变 `String` 的写法）：

```java
public class String {
    private final char value[];
    // …
    public String concat(String s) {
        char newValue[] = new char[value.length + s.value.length];
        for (int i = 0; i < value.length; ++i) {
            newValue[i] = value[i];
        }
        for (int i = 0; i < s.value.length; ++i) {
            newValue[value.length+i] = s.value[i];
        }
        return new String(newValue);
    }
    public String replace(char old, char new) {
        char newValue[] = new char[value.length];
        for (int i = 0; i < value.length; ++i) {
            newValue[i] = value[i];
            if (value[i] == old) {
                newValue[i] = new;
            }
        }
        return new String(newValue);
    }
}
```

出自同文件第 13 页（内部类）：

```java
public class LinkedList {
    private static class Node {
        public int val;
        public Node next;
        public Node(int v, Node n) {
            val = v;
            next = n;
        }
    }
    Node head;
    // …
}
```

出自同文件第 19 页（泛型 `Stack`）：

```java
public class Stack<T> {
    public void push(T obj) { … }
    public T pop() { … }
}
```

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

下面演示「表面不可变、实际可变」的三种常见漏洞，以及正确写法：

```java
import java.util.*;

// 漏洞 1：getter 泄漏内部数组
class LeakyRange {
    private final int[] data;
    LeakyRange(int[] data) { this.data = data; }        // 漏洞 2：构造时未拷贝
    int[] getData() { return data; }                     // 漏洞 3：返回内部引用
}

// 正确写法
final class SafeRange {                                  // final：防止子类加回可变性
    private final int[] data;
    SafeRange(int[] data) { this.data = Arrays.copyOf(data, data.length); }  // 进：拷贝
    int[] getData() { return Arrays.copyOf(data, data.length); }             // 出：拷贝
    int size() { return data.length; }
}

public class Demo {
    public static void main(String[] args) {
        int[] src = {1, 2, 3};

        LeakyRange lr = new LeakyRange(src);
        src[0] = 99;                       // 外部修改影响了对象内部
        lr.getData()[1] = 88;              // 通过 getter 修改内部
        System.out.println(Arrays.toString(lr.getData()));   // [99, 88, 3] —— 全被改

        int[] src2 = {1, 2, 3};
        SafeRange sr = new SafeRange(src2);
        src2[0] = 99;                      // 无影响
        sr.getData()[1] = 88;              // 改的是副本，无影响
        System.out.println(Arrays.toString(sr.getData()));   // [1, 2, 3]
    }
}
```

再演示「遮蔽 + 静态字段」的一个小陷阱：

```java
class Counter {
    static int count = 0;              // 类字段，所有实例共享
    int local = 0;                     // 实例字段
    void inc() { count++; local++; }
}
Counter a = new Counter(), b = new Counter();
a.inc(); a.inc(); b.inc();
System.out.println(Counter.count + " " + a.local + " " + b.local);  // 3 2 1
```

`count` 是类级的，三次调用累加到 3；`local` 是实例级的，`a` 两次、`b` 一次。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| `final` 变量 | 不可变对象 | 前者只冻结引用；后者要求字段全 `private final` 且字段类型不可变、不外泄。`final List` 仍可 `add` |
| 不可变（immutable） | 只读（read-only） | 不可变是「永远不能改」；只读是「通过这个接口不能改」，底层可能仍被别处修改（如 `Collections.unmodifiableList` 的视图） |
| `static` 方法 | 实例方法 | 前者无接收者、不能访问 `this`、编译期即可绑定（不算重写）；后者依赖对象，参与动态分派 |
| 静态内部类 | 非静态内部类 | 前者不持有外部实例引用（`private static class Node`）；后者隐式持有 `Outer.this`，可访问外部实例字段 |
| 变量遮蔽（shadowing） | 方法重写（overriding） | 遮蔽是名字解析规则，编译期按静态作用域决定；重写是运行期按动态类分派。字段**不会**被重写，只会被遮蔽 |
| 泛型 `Stack<String>` | 裸 `Stack` + 强转 | 前者类型错误在编译期暴露；后者推迟到运行期抛 `ClassCastException`。运行期两者是同一个类（类型擦除） |
| `try` 块内声明 | 方法级声明 | 前者块结束即失效（第 15 页 `x is undefined`）；后者在整个方法内可见 |

## 8. 对应原版讲义

- PDF 相对路径：`90-原始PDF/15-214/slides/06_Mutability_and_Java_Potpourri.pdf`
- 总页数：20 页
- 本节重点页码：
  - 第 2 页：administrivia（Charlie 的 office hour 本周临时改到周日 12:00–14:00，Wean 5101）
  - 第 6–7 页：两种 `String` 实现（可变 vs 不可变）
  - 第 8 页：可变/不可变定义与 `final` 的边界
  - 第 9 页：可变 vs 不可变的优势对照（文本提取为空）
  - 第 10 页：写不可变类的五条建议
  - 第 12 页：`static` 的定义与三个例子（`Counter`、`main`、`String.valueOf`）
  - 第 13 页：内部类与 `private static class Node`
  - 第 14–15 页：变量遮蔽、三种变量、块作用域陷阱
  - 第 16 页：集合 API 骨架（`Collection`/`List`/`Set` 及实现类）
  - 第 17–19 页：`Object` 版 `Stack` → 强转 → 泛型 `Stack<T>`
  - 第 20 页：下周转入设计与测试
- 原始网页链接：`https://www.cs.cmu.edu/~aldrich/214/slides/06_Mutability_and_Java_Potpourri.pdf`
- > 待核实：第 9 页 `Advantages: Mutability vs. Immutability` 在 PDF 文本层中只有标题、无正文，可能为图形化对照表，本笔记的对照表为整理补充而非原文。

## 9. 对应视频

未找到官方公开录像。2013 年秋季的 15-214 课堂没有公开发布录像，故不提供链接与时间戳。

## 10. 本节复习

- 可变 = 数据可随时间变化；`final` 只冻结引用，不冻结被引用对象。
- 不可变类的五条：全 `private final`、独占访问、防御性拷贝、不泄漏、无公有修改方法 + 类 `final`。
- 不可变换来别名安全、哈希稳定、天然线程安全；代价是每次修改都要复制。
- `static` = 属于类；`main` 必须 `static` 因为 JVM 启动时还没有实例。
- `private static class Node` 把实现细节彻底藏进 `LinkedList` 内部。
- 遮蔽是编译期的名字解析；字段不参与动态分派。
- 花括号定义作用域，`try` 块内声明的变量块外不可见。
- 泛型把类型错误从运行期移回编译期；Java 泛型靠类型擦除实现。

## 11. 自我检查

1. 下面这个类是不可变的吗？逐条对照课件第 10 页的五条建议说明。
   ```java
   public class Person {
       private final String name;
       private final List<String> nicknames;
       public Person(String name, List<String> nicknames) {
           this.name = name;
           this.nicknames = nicknames;
       }
       public List<String> getNicknames() { return nicknames; }
   }
   ```
2. 为什么 `main` 方法必须声明为 `static`？如果它不是 `static`，JVM 启动时会遇到什么问题？
3. `private static class Node` 与 `private class Node`（非静态内部类）在内存与可访问性上有什么差别？在 `LinkedList` 这个场景里应该选哪个，为什么？
4. 下面的代码能编译吗？如果不能，错在哪一行、为什么？
   ```java
   public void f(String s) {
       try {
           Integer x = Integer.valueOf(s);
       } catch (NumberFormatException e) { }
       System.out.println(x);
   }
   ```
5. 用泛型改写 `public Object pop()` 为 `public T pop()` 之后，客户端代码少了一次强转。请说明这次改写把什么错误从运行期移到了编译期，并指出泛型在运行期的局限。

<details>
<summary>参考答案</summary>

1. **不是不可变的**，违反了两条。
   - 第 1 条「全 `private final`」：满足。
   - 第 2 条「独占访问」与第 3 条「防御性拷贝」：**违反**。构造函数直接把外部传入的 `List` 存进字段，外部持有同一个 `List` 引用，可以随时 `nicknames.add(...)` 改变对象内部状态。
   - 第 4 条「不泄漏数据」：**违反**。`getNicknames()` 直接返回内部 `List`，调用者可以 `person.getNicknames().clear()`。
   - 第 5 条「无公有修改方法 + 类 `final`」：没有 mutator，但类**不是 `final`**，子类可以添加可变状态。
   修正：构造时 `this.nicknames = new ArrayList<>(nicknames);`，getter 返回 `Collections.unmodifiableList(nicknames)` 或副本，类声明为 `final`。

2. 因为 JVM 在调用入口点时**还没有创建任何对象**。若 `main` 是实例方法，JVM 必须先用某个构造函数 `new` 一个实例才能调用它，但「用哪个构造函数、需要什么参数」本身无从得知（可能没有无参构造函数），形成循环依赖。声明为 `static` 后，JVM 只需加载类、按 `类名.main(args)` 直接调用，无需实例。这也是 `static` 方法「属于类而不属于实例」这一定义的直接体现。

3. **内存**：非静态内部类的每个实例都隐式持有一个指向外部类实例的引用（`Outer.this`），因此多一个指针的开销，且会阻止外部实例被 GC 回收（若内部实例活得比外部久，会造成内存泄漏）；静态内部类不持有该引用。**可访问性**：两者都能访问外部类的 `private` 成员（Java 编译器生成合成访问器），但非静态内部类还能访问外部实例的字段与方法。**在 `LinkedList` 场景应选 `private static class Node`**：`Node` 只是链表节点的数据结构，不需要访问 `LinkedList` 实例的任何状态，加一个外部引用纯属浪费且埋下泄漏隐患。只有当内部类需要读写外部实例状态时（例如实现 `Iterator` 需要知道当前遍历位置）才用非静态内部类。

4. **不能编译**。错误在 `System.out.println(x);` 这一行，报 `cannot find symbol: variable x`。原因是 `Integer x` 声明在 `try` 块的花括号内，作用域止于该块的右花括号；`catch` 块与 `println` 都在该作用域之外。修正方式是把声明提到 `try` 之前（`Integer x = null;`），但要注意此时解析失败后 `x` 仍为 `null`，直接打印会输出 `null`，更好的做法是在 `catch` 中返回或抛出。

5. 移走的是**「往容器里放了 A 类型、却按 B 类型取出」这类类型不匹配错误**。裸 `Stack` 版本中，`stack.push(Integer.valueOf(42))` 编译通过，`(String) stack.pop()` 也编译通过，`ClassCastException` 要等到运行期那一行执行才抛出——可能在测试覆盖不到的分支里，也可能上线后才爆。改成 `Stack<String>` 后，`push(Integer)` 直接编译失败，错误在写代码时就暴露。**运行期局限**：Java 泛型通过类型擦除实现，`Stack<String>` 与 `Stack<Integer>` 在运行期是同一个 `Class` 对象，`T` 被擦成 `Object`（或有界类型的上界）。因此不能 `new T[]`、不能 `x instanceof T`、不能用 `T.class`，也无法在运行期区分两个不同参数化的 `Stack` 实例——这也导致「泛型数组创建」和「重载时仅类型参数不同」都不合法。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-05-Object-Contracts-and-Exceptions]]
- 下一讲：[[15-214-07-Design-Patterns]]
- 课程总览：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]
- 课程目录：[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸：Josh Bloch《Effective Java》第 15–17 条（最小化可变性、优先使用组合、最小化可访问性）；不可变性在并发编程中的价值会在课程后半段（并发模块）再次出现。
