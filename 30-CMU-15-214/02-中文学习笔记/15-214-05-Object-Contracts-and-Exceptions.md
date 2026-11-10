---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L05
topic: Object Behavioral Contracts and Exceptions
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 行为契约
  - equals
  - 异常
  - 受检异常
---

# 第 5 讲 对象行为契约与异常（Object Behavioral Contracts and Exceptions）

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。

## 1. 本节学习目标

- 能解释「行为契约（behavioral contract）」的含义，并说明为什么签名正确不等于契约正确。
- 能完整列出 `equals`、`hashCode`、`clone` 三个契约的条款，并各举一个违反后果。
- 能复述 `ColorPoint` 三次尝试的失败原因，说出课件给的两条建议。
- 能画出 `Throwable` 继承树的主要分支，并区分受检异常（checked）与非受检异常（unchecked）。
- 能说明 `try`/`catch`/`finally` 的控制流语义，特别是「`finally` 总会执行」意味着什么。
- 能列出异常的五个好处与四条使用准则。

## 2. 前置知识

- [[15-214-04-Inheritance-Typechecking-Dispatch]]：重写 vs 重载、分派四步、`equals(Point)` 的陷阱、`ColorPoint` 的四种尝试（本讲会再过一遍但角度不同）。
- [[15-214-03-Encapsulation-and-Inheritance]]：抽象类、`extends`、可见性。
- 外部概念：等价关系（自反、对称、传递）；C 语言的 `errno` 与返回码错误处理风格。

## 3. 核心概念

- **Behavioral Contract（行为契约）**：一个方法对调用者作出的承诺，包括前置条件、后置条件，以及在 `Object` 这类通用方法上的等价语义约定。
- **Equivalence Relation（等价关系）**：自反 + 对称 + 传递的关系。
- **Consistency（一致性）**：在对象未被修改的前提下，反复调用返回同一结果。
- **Exception（异常）**：向调用者通知「异常情况（通常是操作失败）」的机制。
- **Propagation（传播）**：异常沿函数调用栈向上冒泡，直到被 `catch` 或被 `main` 兜住。
- **Checked Exception（受检异常）**：`Exception` 的子类但不是 `RuntimeException` 的子类；编译器强制调用者处理或声明。
- **Unchecked Exception（非受检异常）**：`RuntimeException` 及其子类；通常表示程序错误，编译器不强制处理。
- **`finally`**：无论 `try`/`catch` 如何结束（正常、异常、甚至 `return`）都会执行的块。
- **Stack Trace（栈轨迹）**：异常对象携带的调用栈快照。

## 4. 通俗理解

**契约**就像租房合同：签名（方法名 + 参数 + 返回类型）只是合同封面，真正约束双方的是里面的条款。`equals` 的条款是「你必须实现一种等价关系」——不是「返回一个 boolean 就行」。

课件第 7 页给了一个反例，把「合法但不合契约」推到极端：

```java
public class CheckingAccountImpl implements CheckingAccount {
    @Override
    public boolean equals(Object obj) { return false; }
}
```

签名完全正确、编译通过、运行不崩——但它违反了自反性：`x.equals(x)` 返回 `false`。任何把它放进 `HashSet` 的代码都会出现「加进去之后再也找不到」的鬼故事。

**异常**则像火警：老式做法（C 的 `errno`）是每个房间门口贴一张小纸条告诉你「刚才可能出事了」，你得每次出门都低头看一眼，忘了看就漏了。异常是把警报器接到整栋楼——一旦触发，所有人必须响应：要么就地处理（`catch`），要么往上报告（声明 `throws`），要么整栋楼疏散（栈展开到 `main`）。

## 5. 原理与推导

### 5.1 为什么 `Object` 的方法需要「契约」而不是「实现」

`java.lang.Object` 是所有 Java 类的根，它只提供了四个常被重写的公有方法（第 6 页）：

| 返回类型 | 签名 | 默认行为 |
|---|---|---|
| `String` | `toString()` | 类名 + `@` + 哈希的十六进制 |
| `boolean` | `equals(Object obj)` | `return this == obj;`（身份比较） |
| `int` | `hashCode()` | 通常由对象地址派生 |
| `Object` | `clone()` | 逐字段浅拷贝（且要求实现 `Cloneable`） |

关键洞察：**这四个方法的默认实现都是「对当前实现而言正确，但对任何有值语义的类都不正确」**。`Point` 的默认 `equals` 会让两个坐标相同的点不相等；默认 `hashCode` 会让两个「应该相等」的对象哈希不同。所以子类一旦决定采用值语义（value semantics），就必须同时接管这两个方法，并且必须满足契约。

### 5.2 `equals` 契约：五条

第 8 页给出：

| 条款 | 形式化 | 反例的后果 |
|---|---|---|
| 自反 Reflexive | `∀x. x.equals(x)` | 集合中「有却查不到」 |
| 对称 Symmetric | `∀x,y. x.equals(y) ⇔ y.equals(x)` | `contains` 结果依赖参数顺序 |
| 传递 Transitive | `∀x,y,z. x.equals(y) ∧ y.equals(z) ⇒ x.equals(z)` | 等价类交叉，去重与合并出错 |
| 一致 Consistent | 未修改时反复调用返回同值 | 同一个对象在集合中「时隐时现」 |
| 非空 | `x.equals(null)` 恒 `false` | 抛 `NullPointerException` |

值得强调「一致」这一条：它允许对象**可变**（`equals` 的结果可以随修改而变化），但禁止「无理由地变化」，例如用随机数或当前时间参与比较。

### 5.3 `hashCode` 契约：三条 + 一条建议

第 9 页：

1. **一致**：未修改时反复调用返回同值。
2. **`x.equals(y) ⇒ x.hashCode() == y.hashCode()`**。
3. **反向不成立**：`x.hashCode() == y.hashCode()` 不蕴含 `x.equals(y)`。
4. **建议**：**当且仅当**关系——重写 `equals` 就必须重写 `hashCode`，反之亦然。

为什么第 2 条是硬性要求？因为哈希容器（`HashMap`、`HashSet`）的查找是两步：先算 `hashCode` 定位桶，再在桶内用 `equals` 线性确认。若两个相等对象哈希不同，它们落在不同桶，第二步根本没机会执行，容器就会「找不到」。

为什么第 3 条必须允许？因为哈希把「无限多的对象」映射到「有限的 32 位整数」，碰撞（collision）在数学上不可避免。要求「同哈希 ⇒ 相等」等于要求哈希函数是单射，这不可能。

### 5.4 `clone` 契约

第 10 页：**返回对象的深拷贝（deep copy）**。通常（但不是必须）满足：

- `x.clone() != x`（不是同一个对象）
- `x.clone().equals(x)`（内容相等）

「深」这个字是重点：如果对象持有可变引用字段，浅拷贝会让副本与原对象共享内部状态，修改一个会影响另一个——这违反「拷贝」的直觉。

### 5.5 「平等的一课」：从 `Point` 到 `ColorPoint`

这一段与第 4 讲重叠，但课件在这里给出的是**教学叙事**（第 11–20 页），可以按「错误 → 修正 → 新错误 → 再修正 → 根本性解法」的顺序理解：

**第 1 步（第 12 页）** 学生直觉写法：

```java
public boolean equals(Point p) { return x == p.x && y == p.y; }
```

课件批注：`boolean equals(Point p) does not override boolean equals(Object obj)`，并配一句 `Types must match`。这是**重载**，`Object.equals` 依然生效。

**第 2 步（第 13 页）** 正确写法 + `hashCode`：

```java
public boolean equals(Object obj) {
    if (!(obj instanceof Point)) return false;
    Point p = (Point) obj;
    return x == p.x && y == p.y;
}
public int hashCode() { return 31*x + y; }
```

**第 3 步（第 15 页）** 给 `ColorPoint` 加 `equals`，用 `instanceof ColorPoint` 做守卫。

**第 4 步（第 16 页）** 发现**对称性**破坏：`p.equals(cp)` 为 `true`，`cp.equals(p)` 为 `false`。

**第 5 步（第 17 页）** 让 `ColorPoint.equals` 对非 `ColorPoint` 参数退化为 `super.equals(obj)`。发现**传递性**破坏：`cp1.equals(p)` 真、`p.equals(cp2)` 真、但 `cp1.equals(cp2)` 假。

**第 6 步（第 18 页）** 把 `Point` 改成 `abstract`，再加一个 `PointImpl` 承载「无色点」。这样「裸 `Point` 实例」不存在，跨类型比较的场景消失，对称性与传递性同时恢复。

**第 7 步（第 19–20 页）** 课件给的两条建议：

1. **Don't allow equality between distinct types**（不要让不同具体类型之间可以相等）。
2. **Be careful when inheriting from a concrete class**（从具体类继承要格外小心）。

并引用 Josh Bloch：

> "Overriding the equals method seems simple, but there are many ways to get it wrong and the consequences can be dire."

第 20 页还有一个小彩蛋 `EvilButTrue`：

```java
public class EvilButTrue {
    public boolean equals(Object obj) { return obj != null; }
    public int hashCode() { return 0; }
}
```

它满足「自反、对称（非 null 时互相为真）、一致、非空」，也满足 `hashCode` 的一致性；但**传递性**塌了：所有非 null 对象两两相等，把任意对象塞进集合都会「吞掉」后续所有元素。

### 5.6 为什么需要异常：一段 C 风格的错误处理

第 22 页展示「返回码 + 全局 `errno`」的写法：

```java
FileInputStream fIn = new FileInputStream(filename);
if (fIN == null) {
    switch (errno) {
    case _ENOFILE:
        System.err.println("File not found: " + …);
        return -1;
    default:
        System.err.println("Something else bad happened: " + …);
        return -1;
    }
}
DataInput dataInput = new DataInputStream(fIn);
if (dataInput == null) { … return -1; }
int i = dataInput.readInt();
if (errno > 0) { … return -1; }
return i;
```

课件自嘲地在注释里写「The slide lacks space to close the file. Oh well.」——这句玩笑本身就是论点：**错误处理代码把正常逻辑挤没了**，连 `close()` 都写不下。

对照第 24 页的异常版本：

```java
try {
    FileInputStream fileInput = new FileInputStream(filename);
    DataInput dataInput = new DataInputStream(fileInput);
    int i = dataInput.readInt();
    fileInput.close();
    return i;
} catch (FileNotFoundException e) {
    System.out.println("Could not open file " + filename);
    return -1;
} catch (IOException e) {
    System.out.println("Error reading binary data from file " + filename);
    return -1;
}
```

正常路径一眼可见，错误路径集中在下面。

### 5.7 异常的语义与控制流

第 23 页的语义定义：**异常沿函数调用栈向上传播，直到到达 `main()` 或被捕获。**

两个来源：(1) 程序里显式 `throw`；(2) Java 运行时抛出（如数组越界）。

**控制流实验一**（第 25 页）：

```java
try {
    System.out.println("Top");
    int[] a = new int[10];
    a[42] = 42;                      // 抛 IndexOutOfBoundsException
    System.out.println("Bottom");    // 不执行
} catch (IndexOutOfBoundsException e) {
    System.out.println("Caught index out of bounds");
}
```

输出 `Top` / `Caught index out of bounds`，`Bottom` 被跳过。

**控制流实验二**（第 26 页）：`test()` 内部的 `catch` 抓的是 `NegativeArraySizeException`，抓不住 `IndexOutOfBoundsException`，于是异常穿出 `test()`，被 `main` 的 `catch (IndexOutOfBoundsException e)` 接住。输出同样是 `Top` / `Caught index out of bounds`，但**打印它的是另一层**。这演示了传播（propagation）。

**`finally`**（第 28–29 页）：

```java
try {
    System.out.println("Top");
    int[] a = new int[10];
    a[42] = 42;
    System.out.println("Bottom");
} catch (IndexOutOfBoundsException e) {
    System.out.println("Caught index out of bounds");
} finally {
    System.out.println("Finally got here");
}
```

输出 `Top` / `Caught index out of bounds` / `Finally got here`。

把 `a[42]` 改成 `a[2]`（第 29 页），没有异常，输出 `Top` / `Bottom` / `Finally got here`。**两种情况都执行 `finally`**——这正是「允许在正常与异常路径上做一致的清理」的实现机制，也是 5.9 节第 5 条好处的来源。

### 5.8 异常层次与受检/非受检

第 30 页的继承树（简化）：

```
Object
└── Throwable
    ├── Exception
    │   ├── RuntimeException
    │   │   ├── NullPointerException
    │   │   └── IndexOutOfBoundsException
    │   ├── IOException
    │   │   ├── EOFException
    │   │   └── FileNotFoundException
    │   └── ClassNotFoundException
    └── Error（课件图中省略）
```

第 31 页的定义：

| 类别 | 定义 | 语义 | 编译器行为 |
|---|---|---|---|
| 非受检 Unchecked | `RuntimeException` 的任意子类 | 极不可能发生且/或通常不可恢复的错误 | 不强制 `catch` 或 `throws` |
| 受检 Checked | `Exception` 的子类，但**不是** `RuntimeException` 的子类 | 每个调用者都该知道并**显式决定**处理还是继续上报 | 必须 `catch` 或在方法签名 `throws` |

判断口诀：**看它是不是 `RuntimeException` 的后代**。`IOException` 是受检；`NullPointerException`、`IndexOutOfBoundsException`、`ClassCastException`、`IllegalArgumentException` 都是非受检。

### 5.9 自定义异常与好处、准则

**自定义异常**（第 32 页）：方法必须声明它可能抛出的受检异常；若你的类 `extends java.lang.Exception`，就能 `throw` 它：

```java
if (someErrorBlahBlahBlah) {
    throw new MyCustomException("Blah blah blah");
}
```

课件提到的示例文件：`ReadFromFileV*.java`（第 27 页）、`IllegalBowlingScoreException` 与 `ReadBowlingScore`（第 32 页）。

**五个好处**（第 34 页）：

| 好处 | 对照 |
|---|---|
| 提供错误的高层摘要与栈轨迹 | 对比 C 的 `core dumped` |
| 无法忘记处理常见失败模式 | 对比用标志位或特殊返回值 |
| 可以选择性地从失败中恢复 | 对比直接 `System.exit()` |
| 改善代码结构 | 把常规操作与错误处理分离 |
| 正常与异常路径都能一致地清理 | 由 `finally` 保证 |

**四条准则**（第 35 页）：

1. 捕获并处理所有受检异常——除非确实没有好办法。
2. 用运行时异常表示程序错误。
3. 不要捕获异常却完全不处理。
4. 抛异常时描述错误；重新抛出时**总是把原异常作为 cause 附上**（`new XxxException(msg, cause)`），否则栈轨迹断裂。

## 6. 代码示例

### 6.1 官方课程代码

出自 `05_Object_contracts_and_exceptions.pdf` 第 13 页（`Point` 的正确 `equals` 与 `hashCode`）：

```java
public class Point {
    private final int x;
    private final int y;
    public Point(int x, int y) { this.x = x; this.y = y; }

    public boolean equals(Object obj) {
        if (!(obj instanceof Point))
            return false;
        Point p = (Point) obj;
        return x == p.x && y == p.y;
    }

    public int hashCode() { return 31*x + y; }
}
```

出自同文件第 18 页（抽象 `Point` + `PointImpl` 的解法）：

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

出自同文件第 28 页（`finally` 必定执行）：

```java
try {
    System.out.println("Top");
    int[] a = new int[10];
    a[42] = 42;
    System.out.println("Bottom");
} catch (IndexOutOfBoundsException e) {
    System.out.println("Caught index out of bounds");
} finally {
    System.out.println("Finally got here");
}
```

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

下面这个例子同时演示三件事：哈希容器的两步查找、`finally` 的清理作用、以及自定义受检异常的传播。

```java
import java.util.*;
import java.io.*;

class InsufficientFundsException extends Exception {      // 受检异常
    InsufficientFundsException(String msg, Throwable cause) { super(msg, cause); }
}

class Account {
    private int balance;
    Account(int balance) { this.balance = balance; }
    void withdraw(int amount) throws InsufficientFundsException {
        if (amount > balance) {
            throw new InsufficientFundsException(
                "余额不足: 请求 " + amount + "，可用 " + balance, null);
        }
        balance -= amount;
    }
}

public class Demo {
    static void run(Account a, int amount) throws InsufficientFundsException {
        System.out.println("尝试取出 " + amount);
        a.withdraw(amount);                       // 可能抛出，向上传播
        System.out.println("取款成功");
    }

    public static void main(String[] args) {
        Account a = new Account(100);
        try {
            run(a, 30);
            run(a, 500);                          // 这里抛出
            System.out.println("这一行不会执行");
        } catch (InsufficientFundsException e) {
            System.out.println("捕获: " + e.getMessage());
        } finally {
            System.out.println("finally: 无论成功失败都会执行（可用于释放资源）");
        }
        // 输出：
        // 尝试取出 30
        // 取款成功
        // 尝试取出 500
        // 捕获: 余额不足: 请求 500，可用 70
        // finally: 无论成功失败都会执行（可用于释放资源）
    }
}
```

再给一个「哈希容器为什么需要 `hashCode`」的最小验证：

```java
class OnlyEquals {
    final int v;
    OnlyEquals(int v) { this.v = v; }
    @Override public boolean equals(Object o) {
        return o instanceof OnlyEquals && ((OnlyEquals) o).v == v;
    }
    // 故意不重写 hashCode
}
Set<OnlyEquals> s = new HashSet<>();
s.add(new OnlyEquals(1));
System.out.println(s.contains(new OnlyEquals(1)));   // 很可能 false
```

要点：`equals` 说「相等」，但两个对象的默认 `hashCode` 不同，落进不同桶，`contains` 在错误的桶里找不到。这就是「当且仅当」建议的实证。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| 签名正确 | 契约正确 | 签名由编译器检查；契约（自反/对称/传递等）只能靠规格与测试保证。`EvilButTrue.equals` 签名正确、契约崩塌 |
| `equals` 相等 | `hashCode` 相等 | 前者蕴含后者；后者不蕴含前者（碰撞合法）。哈希容器两步查找，缺一不可 |
| 受检异常 Checked | 非受检异常 Unchecked | 前者是 `Exception` 的非 `RuntimeException` 分支，编译期强制处理或声明；后者是 `RuntimeException` 分支，通常表示程序错误 |
| `catch` | `finally` | `catch` 只在匹配的异常发生时执行；`finally` **总是**执行（正常、异常、`return` 都执行） |
| 异常传播 | 异常吞掉 | 传播 = 不捕获、让上层处理（必要时 `throws` 声明）；吞掉 = 捕获后什么都不做，课件明确列为坏实践 |
| `x.clone() != x` | `x.clone().equals(x)` | 前者是「新对象」；后者是「内容相等」。前者是通常要求，后者是通常期望，但契约只说「深拷贝」 |
| 浅拷贝 | 深拷贝 | 浅拷贝共享内部可变对象；深拷贝递归复制。`clone` 契约要求深拷贝 |

## 8. 对应原版讲义

- PDF 相对路径：`90-原始PDF/15-214/slides/05_Object_contracts_and_exceptions.pdf`
- 总页数：35 页
- 本节重点页码：
  - 第 2 页：administrivia（Homework 1 当晚截止，Homework 2 于 9 月 19 日周四截止）
  - 第 6–7 页：`java.lang.Object` 的四个常用方法、默认 `equals` 与反例
  - 第 8–10 页：`equals` / `hashCode` / `clone` 三份契约
  - 第 11–13 页：`Point.equals` 的「诱人但错误」与正确解
  - 第 14–17 页：`ColorPoint` 的对称性与传递性失败
  - 第 18–20 页：抽象 `Point` 解法、两条建议、Josh Bloch 引言、`EvilButTrue`
  - 第 22–24 页：错误码风格 vs 异常风格的文件读取
  - 第 25–26 页：异常控制流与跨函数传播
  - 第 27 页：`ReadFromFileV*.java` 示例
  - 第 28–29 页：`finally` 在异常/正常两条路径上都执行
  - 第 30–32 页：异常继承树、受检/非受检定义、自定义异常
  - 第 33–35 页：异常的五个好处、四条准则
- 原始网页链接：`https://www.cs.cmu.edu/~aldrich/214/slides/05_Object_contracts_and_exceptions.pdf`
- > 待核实：第 12–18 页打印的 `if (!(obj instanceof Point)` 缺右括号，应为幻灯片排版遗漏；第 26 页的 `System.out.println"("Caught index out of bounds");` 引号位置错乱，同属排版问题。

## 9. 对应视频

未找到官方公开录像。2013 年秋季的 15-214 课堂没有公开发布录像，故不提供链接与时间戳。

## 10. 本节复习

- `Object` 的四个常用方法默认实现都只适用于「身份语义」，有值语义的类必须接管 `equals`/`hashCode`。
- `equals` 五条：自反、对称、传递、一致、非空。
- `hashCode` 三条：一致、「相等蕴含同哈希」、反向不成立；建议与 `equals` 成对重写。
- `clone` 契约是「深拷贝」，通常满足 `!=` 与 `equals`。
- `equals(Point)` 是重载，不是重写——第 4 讲已强调，本讲再以教学叙事展开。
- `ColorPoint` 的三次失败：对称性、传递性、以及抽象父类的解法。
- 两条建议：不要让不同具体类型之间可以相等；从具体类继承要小心。
- 异常沿栈传播到 `main` 或被捕获；`finally` 在两条路径上都执行。
- 受检 = `Exception` 且非 `RuntimeException`；非受检 = `RuntimeException` 分支。
- 五个好处、四条准则（尤其「重抛要带 cause」）。

## 11. 自我检查

1. 下面这个类违反了 `equals` 契约的哪几条？请逐条判断并说明。
   ```java
   class Weird {
       public boolean equals(Object o) { return o instanceof Weird; }
       public int hashCode() { return 42; }
   }
   ```
2. 解释为什么 `x.hashCode() == y.hashCode()` 不能推出 `x.equals(y)`，并说明如果强行要求这个反向蕴含会发生什么。
3. 有下面代码，输出是什么？如果把 `catch (IndexOutOfBoundsException e)` 改成 `catch (NegativeArraySizeException e)`，输出会变吗？
   ```java
   public static void main(String[] args) {
       try {
           System.out.println("A");
           int[] a = new int[3];
           a[10] = 1;
           System.out.println("B");
       } catch (IndexOutOfBoundsException e) {
           System.out.println("C");
       } finally {
           System.out.println("D");
       }
   }
   ```
4. 什么情况下应该用受检异常、什么情况下用非受检异常？请各举一个 JDK 中的例子并说明理由。
5. 为什么课件说「重新抛出异常时总是要把原异常作为 cause 附上」？如果不这么做，会丢失什么信息？

<details>
<summary>参考答案</summary>

1. **自反**满足（`x instanceof Weird` 为真）。**对称**满足（两边判断条件相同）。**非空**满足（`null instanceof Weird` 为 `false`）。**传递**满足（所有 `Weird` 实例两两相等，是「全等关系」）。**一致**满足（结果只依赖类型）。所以 `equals` 本身**没有**违约——它是一个把所有 `Weird` 实例粘成一个等价类的合法等价关系。真正的问题在**语义**：它丢弃了所有字段信息，几乎肯定不是设计者想要的「值相等」。`hashCode` 返回常量 `42` 也**满足契约**（相等对象哈希必相等），只是性能退化为链表。这说明：**契约是下限，不是充分条件**——通过契约检查的 `equals` 仍可能是糟糕的设计（对比课件第 20 页的 `EvilButTrue`，那个才是真的违约：它让 `Weird` 与**任意非 null 对象**相等，从而破坏对称性）。

2. 哈希把「可能无限多的对象」映射到「32 位整数」这一有限集合，由鸽笼原理必然有不同对象共享同一哈希。若强行要求反向蕴含，等价于要求哈希函数是单射，这既不可实现（对象可能比整数多），也会让 `hashCode` 退化成必须携带完整对象信息。实际后果是所有哈希容器都失去意义——因为「同桶」将等价于「相等」，桶内永远只有一个元素，等于退化为「用完整比较做 O(1) 定位」，而这在一般情况下不可能。

3. 输出 `A` / `C` / `D`。`a[10] = 1` 抛 `IndexOutOfBoundsException`，跳过 `B`，进入 `catch` 打印 `C`，随后 `finally` 打印 `D`。改成 `catch (NegativeArraySizeException e)` 后，`catch` 不匹配，异常向外传播出 `main`，程序以未捕获异常终止；输出为 `A` 然后 `D`（`finally` 仍然执行），最后打印栈轨迹。

4. **受检异常**用于「调用者可以合理恢复、并且必须知情」的失败，例如 `IOException`（文件不存在、磁盘满）——调用者可以选择重试、换文件、提示用户。**非受检异常**用于「程序写错了」，例如 `NullPointerException`、`IndexOutOfBoundsException`、`IllegalArgumentException`——正确编写的程序不应该遇到它们，强制每个调用者写 `catch` 只会制造噪音。判据可以概括为：**这个失败是环境的问题还是代码的问题？**环境问题用受检，代码问题用非受检。

5. 因为原始异常携带了**最接近故障现场**的栈轨迹与消息。如果重抛时只 `throw new ServiceException("failed")`，调用者看到的栈从服务层开始，真正出错的文件名、行号、底层原因（如 `FileNotFoundException: /etc/x.conf`）全部丢失，排查时只能靠猜。带上 cause（`throw new ServiceException("failed", e)`）后，栈轨迹会打印 `Caused by: ...` 链，保留完整因果。这也是课件第 35 页把它列为「好的实践」的原因。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-04-Inheritance-Typechecking-Dispatch]]
- 下一讲：[[15-214-06-Mutability-and-Java-Potpourri]]
- 课程总览：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]
- 课程目录：[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸：Josh Bloch《Effective Java》第 10–11 条（`equals`/`hashCode`）与第 69–77 条（异常）；本讲的「行为契约」会在 [[15-214-08-Specification-and-Testing]] 中展开为前置/后置条件与框架条件。
