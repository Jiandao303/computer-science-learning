---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L08
topic: Specification and Unit Testing
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 规格
  - 契约式设计
  - 单元测试
  - JUnit
  - 测试覆盖率
  - 类不变式
---

# 第 8 讲 规格与单元测试（Specification and Unit Testing）

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。

## 1. 本节学习目标

- 能列出软件质量的八个维度，并说明「功能性正确」为什么只是其中之一。
- 能写出一个方法的前置条件与后置条件，并说明「客户端违反前置条件时实现者要负什么责任」这一问题的意义。
- 能用 JML 记法（`requires` / `ensures` / `invariant`）表达规格，并解释 `assert` 与显式参数检查的区别。
- 能定义类不变式（class invariant），并说出它在方法执行前后与执行中的有效性规则。
- 能用 JUnit 4 写出含 `@Before`、`@Test(expected=...)` 的测试类，并说明 `assert` 语句与 `org.junit.Assert` 的区别。
- 能区分方法覆盖、语句覆盖、分支覆盖、路径覆盖，并说明「覆盖率高 ≠ 测试充分」。

## 2. 前置知识

- [[15-214-05-Object-Contracts-and-Exceptions]]：`equals`/`hashCode` 的行为契约、异常分类——本讲把「契约」形式化。
- [[15-214-07-Design-Patterns]]：可测试性是一种质量属性，与可扩展性同类。
- [[15-214-02-Objects-Encapsulation-Polymorphism]]：表示不变式与封装的关系。
- 外部概念：命题逻辑、全称量词；Java 注解基础。

## 3. 核心概念

- **Specification（规格）**：对「系统应当做什么」的精确陈述，包含功能行为、错误行为、质量属性。
- **Precondition（前置条件）**：函数正确运行所依赖的条件，由**客户端**负责满足。
- **Postcondition（后置条件）**：函数正确运行后所建立的条件，由**实现者**负责保证。
- **Contract（契约）**：前置 + 后置构成的双方责任划分。
- **JML（Java Modeling Language）**：用注释形式书写规格的语言，`/*@ requires … @ ensures … @*/`。
- **Class Invariant（类不变式）**：关于对象字段的性质，构造函数建立、公有方法前后保持。
- **Unit Test（单元测试）**：测试最小可测单元（通常是方法或类），由开发者编写，快速、独立。
- **Test Coverage（测试覆盖率）**：测试触及程序结构的比例，分为方法/语句/分支/路径覆盖。
- **TDD（Test-Driven Development，测试驱动开发）**：先写测试再写实现。
- **Mock Object（模拟对象）**：替代真实依赖（如数据库）的假实现，用于隔离测试。
- **Continuous Integration（持续集成）**：每次提交都自动构建并跑全部测试。

## 4. 通俗理解

**规格**就是合同。课件第 9 页的类比：

> 如果你付我 30,000 美元（前置条件），我就给你的房子盖一个新房间（后置条件）。

这个类比的价值在于它明确了**责任边界**。如果客户没付钱（违反前置），我不盖房间不算违约——同理，如果调用者传了 `null`（违反前置），实现抛 `NullPointerException` 也不算 bug。

**测试**则是「抽样验收」。Dijkstra 1969 年的名言：

> "Testing shows the presence, not the absence of bugs."
> （测试只能证明 bug 的存在，不能证明其不存在）

课件第 6 页补了一个震撼的注脚：

> "While the first binary search was published in 1946, the first published binary search without bugs did not appear until 1962." —— Donald Knuth
>
> "Given ample time, only about 10% of professional programmers were able to get this small program right." —— Jon Bentley, AT&T Bell Labs

二分查找只有十几行，却花了 16 年才被写对，而且只有 10% 的专业程序员能在充裕时间里写对。这个事实说明：**「看起来简单」的代码非常容易出错，而错误往往藏在你不会想到去测的边界上**。

## 5. 原理与推导

### 5.1 正确性不是唯一的「质量」

课件第 5 页（引自 Braude & Bernstein, *Software Engineering*, Wiley 2011）列出八个质量维度，每个都是一个连续谱，从最差到最好：

| 维度 | 最差 | 最好 |
|---|---|---|
| **Sufficiency（充分性）** | 未能实现规格 | 满足全部规格 |
| **Robustness（健壮性）** | 任何异常事件都崩溃 | 从所有异常事件中恢复 |
| **Flexibility（灵活性）** | 规格一变就要整个替换 | 容易适应合理变更 |
| **Reusability（可复用性）** | 无法用于其他应用 | 无需修改即可用于所有相关应用 |
| **Efficiency（效率）** | 达不到速度或存储要求 | 有合理余量地满足要求 |
| **Reliability（可靠性）** | 达不到要求的平均无故障时间 | 达到要求的 MTBF |
| **Scalability（可扩展性）** | 无法作为更大规模版本的基础 | 是出色的扩展基础 |
| **Security（安全性）** | 完全未考虑安全 | 没有已知的突破方式 |

这解释了为什么课件第 6 页把「功能性正确（functional correctness）」画成一个大圈，里面装了很多技术：

```
功能性正确
├── 15-214 覆盖：Specification、Unit Testing、Type Checking
├── 15-313 覆盖：Formal Verification、Static Analysis、
│                Requirements definition、Inspections/Reviews、
│                Integration/System/Acceptance/Regression/
│                GUI/Blackbox/Model-Based/Random Testing、
│                Change/Release Management
```

本课只覆盖其中三块——**规格、单元测试、类型检查**。这是一个诚实的定位：完整的功能性正确需要一整套工程实践，单靠测试远远不够。

### 5.2 规格包含什么、好的规格应具备什么

课件第 8 页：

**规格包含三类内容**：功能行为、错误行为、质量属性。

**六条理想属性**：

| 属性 | 含义 |
|---|---|
| **Complete（完整）** | 不遗漏任何期望的行为 |
| **Minimal（最小）** | 不要求用户不关心的东西 |
| **Unambiguous（无歧义）** | 对用户关心的每种情况都完整规定 |
| **Consistent（一致）** | 内部无矛盾 |
| **Testable（可测试）** | 能够客观判定 |
| **Correct（正确）** | 如实反映最终用户的需求 |

前五条是「写得好不好」，第六条是「写得对不对」——一个完美无歧义的规格，如果描述的不是用户想要的东西，仍然是失败的规格。

课件第 7 页用一个真实例子说明「好的文本规格长什么样」：`InputStream.read(byte[] b, int off, int len)` 的 Javadoc。它规定得极其细致：

- 最多读 `len` 字节，可能少于 `len`；
- `len == 0` 时读 0 字节并返回 0；
- 已到 EOF 且无字节可读时返回 `-1`；
- 读到的 `k` 个字节存入 `b[off]` 到 `b[off+k-1]`，`b[off+k]` 到 `b[off+len-1]` **不受影响**；
- 任何情况下 `b[0]` 到 `b[off-1]`、`b[off+len]` 到 `b[b.length-1]` **不受影响**；
- 抛出 `IOException` / `NullPointerException` / `IndexOutOfBoundsException` 的确切条件。

课件第 12 页逐条标注了这段规格「好在哪」：多个错误情形各有前置条件、包含不在 `throws` 子句里的运行时异常、规定了返回值、规定了时序行为（blocks）、按情形分述（`len=0` → 0；`len>0 && eof` → -1；`len>0 && !eof` → >0）、精确说明数据写到哪里、哪些部分不受影响。

**这正是「无歧义」的具体样子**：不是写得优雅，而是把每个边界都钉死。

### 5.3 函数契约：前置与后置

课件第 9 页的定义：

> 一个函数的契约陈述了该函数的责任，以及调用它的代码的责任。

- **前置条件（precondition）**：函数正确运行所依赖的条件。
- **后置条件（postcondition）**：函数正确运行后所建立的条件。
- **（功能）正确性**：**若客户端满足函数的前置条件，则函数将执行至完成，并在终止时满足后置条件。**

注意这个定义的结构：它是一个**蕴含式**。当前置为假时，蕴含式自动为真——也就是说，**契约对「前置被违反」的情形没有任何要求**。

课件把这个问题留给课堂讨论：

> What does the implementation have to fulfill if the client violates the precondition?

三种常见立场：

| 立场 | 做法 | 优点 | 缺点 |
|---|---|---|---|
| 无义务（契约式设计经典立场） | 什么都不保证，可以做任何事 | 实现最简单，无运行时开销 | 难以调试；可能造成数据损坏 |
| 快速失败（fail-fast） | 检查参数并抛 `IllegalArgumentException` / `NullPointerException` | 错误立刻暴露在源头 | 每次调用都有检查开销 |
| 尽力而为 | 尽量处理非法输入 | 健壮 | 规格变得复杂，且「尽力」无法定义 |

课件第 16 页给出了工程上的折中，见 5.5 节。

### 5.4 形式化规格：JML

课件第 10 页：

```java
/*@ requires len >= 0 && array != null && array.length == len;
@
@ ensures \result == 
@            (\sum int j;  0 <= j && j < len;  array[j]);
@*/
int total(int array[], int len);
```

三个要点：

- `requires` 是前置条件，`ensures` 是后置条件；
- `\result` 表示返回值；
- `(\sum int j; 0 <= j && j < len; array[j])` 是 JML 的**量词求和**记法：`\sum 类型 变量; 范围; 表达式`。

注意这个规格的信息量：一行 `ensures` 就把「返回值等于前 len 个元素之和」说完了，而且**没有任何实现细节**——它没说要不要用循环、要不要递归、中间变量叫什么。这就是规格与实现的分离。

### 5.5 运行时检查规格：`assert` vs 显式检查

课件第 15 页给出第一种落地方式——用 `assert` 把前置条件写成可执行代码：

```java
float sum(int array[], int len) {
    assert len >= 0;
    assert array.length == len;
    float sum = 0.0;
    int i = 0;
    while (i < len) {
        sum = sum + array[i]; i = i + 1;
    }
    return sum;
}
```

课件特别标注了运行方式：`java -ea Main`（`-ea` = enable assertions）。**默认情况下 JVM 不检查断言**，所以断言是「开发期检查」，发布时可以关掉而不影响性能。

第 16 页给出第二种方式——用显式检查代替断言：

```java
float sum(int array[], int len) {
    if (len < 0 || array.length != len) 
        throw IllegalArgumentException(…);
    float sum = 0.0;
    …
}
```

课件对这段的批注是关键：

> **Check arguments even when assertions are disabled. Good for robust libraries!**

对比表：

| 方式 | 关闭断言后 | 适用场景 | 开销 |
|---|---|---|---|
| `assert` | **不再检查** | 内部不变式、开发期自检 | 零（关闭后） |
| 显式 `if` + `throw` | **仍然检查** | 公共 API 的参数校验 | 每次调用 |

这也回答了 5.3 节的立场问题：课件推荐公共库对参数做显式检查（快速失败），内部逻辑用断言。

注意课件第 15 页的代码把 `return sum;` 写在了 `assert …;` 之前——`return` 之后的语句是**不可达代码**，Java 编译器会报 `unreachable statement` 错误。这显然是排版错误（本意应是 `assert` 在 `return` 前，或删除末尾的 `assert`）。

> 待核实：`08-specification.pdf` 第 15、16 页的 `sum` 函数中，`assert …;` 出现在 `return sum;` 之后，属于不可达代码；第 16 页的 `throw IllegalArgumentException(…)` 缺少 `new` 关键字，也是排版问题。

### 5.6 数据结构不变式与类不变式

课件第 17–20 页用一个 C 语言的队列例子说明「数据结构不变式」：

```c
struct list { elem data; struct list* next; };
struct queue { list front; list back; };

bool is_queue(queue Q) {
    if (Q == NULL) return false;
    if (Q->front == NULL || Q->back == NULL) return false;
    return is_segment(Q->front, Q->back);
}
```

`is_queue` 就是一个**可执行的谓词**：它检查这个 `queue` 结构是否处于合法状态（`front` 与 `back` 非空，且从 `front` 能沿着 `next` 走到 `back`）。

然后课件把不变式写进契约：

```c
void enq(queue Q, elem s)
//@requires is_queue(Q);
//@ensures is_queue(Q);
{
    list l = alloc(struct list);
    Q->back->data = s;
    Q->back->next = l;
    Q->back = l;
}
```

注意：`enq` 的中间状态（`Q->back->data = s;` 之后、`Q->back = l;` 之前）**是不满足** `is_queue` 的。课件第 20 页明确说明：

> 数据结构的不变式：
> - 是数据结构的性质
> - **应当在方法执行前后始终成立**
> - **可能在方法执行期间被临时破坏**

这一点极其重要。它意味着不变式不是「任何时刻都成立」的全局真理，而是「在可观察点（方法边界）成立」的约束。这正是「表示不变式（representation invariant）」这一名称的由来。

**类不变式**（第 21 页）是同一思想在 OO 中的版本：

> 类不变式：
> - 关于对象字段的性质
> - **由构造函数建立**
> - **在公有方法执行前后应始终成立**
> - **可能在方法执行期间被临时破坏**

第 22 页给出 `SimpleSet` 的两种写法。**逐方法写法**（繁琐）：

```java
public class SimpleSet {
    int contents[];
    int size;
    //@ ensures sorted(contents);
    SimpleSet(int capacity) { … }
    //@ requires sorted(contents);
    //@ ensures sorted(contents);
    boolean add(int i) { … }
    //@ requires sorted(contents); 
    //@ ensures sorted(contents);
    boolean contains(int i) { … }
}
```

**不变式写法**（简洁）：

```java
public class SimpleSet {
    int contents[];
    int size;
    //@invariant sorted(contents);
    SimpleSet(int capacity) { … }
    boolean add(int i) { … }
    boolean contains(int i) { … }
}
```

`//@invariant` 一行替代了「每个公有方法都写 requires + ensures」的重复。这本身就是规格层面的 DRY（Don't Repeat Yourself）——不变式是「所有公有方法共享的那部分前后置条件」。

注意 `SimpleSet` 用**有序数组 + size** 表示集合，所以「`contents` 前 `size` 个元素有序」是它的表示不变式。`contains` 可以用二分查找，但前提是不变式成立；一旦 `add` 破坏了有序性，`contains` 就会给出错误答案——**不变式是「其他方法可以依赖的隐藏前提」**，这就是它必须由所有方法共同维护的原因。

### 5.7 单元测试：定义与定位

课件第 5 页（`08-testing.pdf`）的定义：

> 测试源代码的单元：系统中**最小的可测部分**，在组装之前先测试。通常是方法、接口这样的小单元，但也可以是包、子系统。目的是捕捉**局部** bug。

特征：

- 通常由开发者编写；
- 大量、小、快速、**相互独立**的测试；
- 对其他系统部件或环境**依赖很少**；
- 「不足够，但是好的起点」——额外收益：**文档（可执行的规格）**、**设计机制（促使你写出可测试的设计）**。

最后两条值得展开。第三条说「测试是文档」：一段注释可能过期，一个测试不会——它要么通过要么失败。第四条说「测试驱动设计」：如果一段代码无法测试，通常说明它的依赖太硬、职责太杂，测试的压力会推着你做解耦。

**测什么**（第 3 页）：方法的功能正确性、类的功能正确性（类不变式）、类在子系统/多子系统/整个系统中的行为、与世界交互时的行为（文件、网络、传感器、错误状态、非确定性、并行、用户交互）。

**谁测、何时测**（第 4 页）：开发者 / 其他开发者 / 独立 QA 团队 / 客户；开发前 / 开发中 / 里程碑后 / 发布前。课件让课堂讨论权衡——这里没有标准答案，只有成本与收益的匹配。

### 5.8 怎么写测试用例

课件第 7 页给出七条策略：

1. **读规格**——规格是测试的唯一依据；
2. **代表性的用例**——小实例通常足够；
3. **非法用例**——故意违反前置条件；
4. **边界条件**；
5. **困难用例（错误猜测）**——压力测试？复杂算法？
6. **像用户那样思考，而不是像程序员**——测试者的目标是**找 bug**；
7. **规格覆盖了吗？有信心吗？还有时间/预算吗？**

第 8–9 页用一个例子演示：

```java
/**
 * computes the sum of the first len values of the array
 * 
 * @param array array of integers of at least length len
 * @param len number of elements to sum up 
 * @return sum of the array values
 */
int total(int array[], int len);
```

测试清单：

- 空数组（`len == 0`）
- 长度为 1 和 2 的数组
- 负数
- 非法长度（负数，或大于 `array.length`）
- `null` 数组
- 很长的数组

注意第三条「负数」是**值域边界**，第四条「非法长度」是**前置条件违反**，第五条「null」是**引用边界**，第六条「很长」是**性能/溢出**。这四类正好对应「代表性 / 非法 / 边界 / 困难」四种策略。

### 5.9 JUnit 基础

课件第 11 页的最小例子：

```java
import org.junit.Test;
import static org.junit.Assert.assertEquals;

public class AdjacencyListTest {
    @Test
    public void testSanityTest(){
        Graph g1 = new AdjacencyListGraph(10);
        Vertex s1 = new Vertex("A");
        Vertex s2 = new Vertex("B");

        assertEquals(true, g1.addVertex(s1));
        assertEquals(true, g1.addVertex(s2));
        assertEquals(true, g1.addEdge(s1, s2));
        assertEquals(s2, g1.getNeighbors(s1)[0]);
    }
    @Test
    public void test….
    private int helperMethod…
}
```

课件把代码分成三类标注：**Set up**（前三行构造）、**tests**（四个断言）、**Check expected results**。

**`assert` 与 `org.junit.Assert` 的区别**（第 12 页）：

| | `assert`（Java 原生语句） | `org.junit.Assert`（库） |
|---|---|---|
| 形式 | `assert expression : "Error Message";` | `assertTrue` / `assertEquals` / `assertNotNull` / `fail` … |
| 失败时 | 抛 `AssertionError` | 抛 `AssertionError`（内部实现） |
| 是否受 `-ea` 控制 | **是**，关闭断言后完全不执行 | **否**，始终执行 |
| 表达能力 | 只有布尔表达式 | 有 `delta` 浮点比较、消息参数等 |

常用方法（第 12 页）：

```java
static void assertTrue(String message, boolean condition)
static void assertEquals(String message, long expected, long actual)
static void assertEquals(double expected, double actual, double delta)   // 浮点必须给 delta
static void assertNotNull(Object object)
static void fail(String message)
```

**JUnit 约定**（第 13 页）：

- `TestCase` 收集多个测试（一个类）；
- `TestSuite` 收集测试类（通常一个包）；
- 测试应**运行快速**；
- 测试应**相互独立**；
- 测试方法是**无参数、无返回值**的方法；
- `AssertionError` 表示测试失败（**非受检异常**）；
- Test Runner 通过**反射**找出所有带 `@Test` 注解的方法。

「测试方法无参数无返回值」这条约定现在看起来自然，但它解释了一件事：测试不能靠返回值传递结果，只能靠断言与异常——这逼着每个测试**自我判定**。

### 5.10 `@Before` 与异常测试

**共享 setup**（第 14 页）：

```java
import org.junit.*;
import org.junit.Before;
import static org.junit.Assert.assertEquals;

public class AdjacencyListTest {
    Graph g;

    @Before
    public void setUp() throws Exception {
        graph = createTestGraph();
    }

    @Test
    public void testSanityTest(){
        Vertex s1 = new Vertex("A");
        Vertex s2 = new Vertex("B");
        assertEquals(true, g.addVertex(s1));
    }
}
```

`@Before` 在**每个** `@Test` 之前都执行一次（不是一次性的 `@BeforeClass`），这正是「测试相互独立」的机制保证：每个测试都拿到一个全新的 `graph`，不会互相污染。

**测试异常**（第 15 页）两种写法：

```java
// 写法 1：try + fail
@Test
public void testSanityTest(){
    try {
        openNonexistingFile();
        fail("Expected exception");
    } catch(IOException e) { }
}

// 写法 2：注解
@Test(expected = IOException.class)
public void testSanityTestAlternative() {
    openNonexistingFile();
}
```

写法 1 的关键是 `fail("Expected exception")`：如果 `openNonexistingFile()` **没有**抛异常，就会执行到 `fail`，测试失败。少了这一行，这个测试永远通过，什么也没测到——这是新手最常犯的测试错误之一。

写法 2 更简洁，但有一个限制：它只能检查异常**类型**，不能检查异常消息或状态；而且如果异常在方法的前半段就抛出，后半段的代码就不会被执行，测试仍然通过——这可能掩盖问题。

### 5.11 测试组织与可测试代码

**组织约定**（第 16 页，强调是 conventions 而非 requirements）：

- 为每个类 `A` 建一个测试类 `ATest`；
- 源码目录与测试目录分开；
- 但 `ATest` 与 `A` 放在**同一个包**里——这样测试可以访问**默认（包）可见性**的成员；
- 或者把测试放在源码目录但用不同的包。

「同一个包」这条技巧很实用：它让测试能触及包级私有（package-private）的成员，从而在不把 API 扩大的前提下测试内部行为。

**可测试代码**（第 20 页）：

- 写代码时就考虑测试；
- 单元测试**促使**你写出可测试的代码；
- 把代码分成可独立测试的部分；
- **把功能抽象到接口后面，使其可替换**；
- 测试驱动开发（TDD）：**先写测试，再写代码**的设计与开发方法。

「抽象到接口后面，使其可替换」正是 Mock Object 能工作的前提，也是 [[15-214-07-Design-Patterns]] 里 Strategy/Adapter 的实战价值。

**频繁运行测试**（第 21 页）：

- 只提交通过全部测试的代码；
- 每次提交前跑测试；
- 读别人代码前先跑测试；
- 如果全量测试太慢：频繁跑包级测试，每晚跑全量（中型项目轻易有上千个用例、跑几分钟）；
- 用**持续集成服务器**（如 travis-ci.org）扩展测试。

**Mock Objects**（第 38–43 页，附加内容）：问题场景是一个「胖客户端」直接连 Oracle 数据库：

```java
Pair[] getFriends() {
    OracleDB database = oracle.getConnection();
    List<Node> persons = database.getTable("Persons");
    for (Node personA: persons) {
        for (Node personB: persons) { … }
    }
    return result;
}
```

这样的代码无法单元测试——必须有真实数据库。解法是引入接口 `IDatabase`：

```java
IDatabase database;
@Before void init() { database = new MockDatabase(); }

@Test void testGetFriends() { assert getFriends() == …; }

class MockDatabase implements IDatabase {
    void open() {}
    List<Node> getTable(String n) {
        if ("Persons".equals(n)) {
            List<Node> result = new List();
            result.add(…);
            return result;
        }
        …
    }
}
```

课件总结的两条原则（第 43 页）：

> - **把业务逻辑与数据表示从 GUI 中分离**，以便测试；
> - **在本地测试算法，无需大型环境**。

### 5.12 测试覆盖率：四种粒度

课件第 24 页先给出被分析的代码：

```java
public static int binsrch (int[] a, int key) {
    int low  = 0;
    int high = a.length - 1;
    while (true) {
        if ( low > high ) return -(low+1); 
        int mid = (low+high) / 2;
        if      ( a[mid] < key )  low  = mid + 1;
        else if ( a[mid] > key )  high = mid - 1;
        else    return mid; 
    }
}
```

并列出四个问题：这条语句会被执行到吗？它返回的结果对吗？这个数组下标可能越界吗？这个 `return` 会被到达吗？

**四种覆盖粒度**：

| 粒度 | 定义 | 优势 | 问题 |
|---|---|---|---|
| **方法覆盖（Method）** | 每个方法至少在某个测试中执行一次 | 最容易达成 | 几乎不保证任何东西 |
| **语句覆盖（Statement）** | 每条语句至少执行一次（流程图上的**节点**） | 测试规模与代码量成线性；易评估 | 死代码碰不到；容错/错误处理代码难以触及；**指标会诱导人删掉错误处理** |
| **分支覆盖（Branch）** | 每个条件分支（真/假）都覆盖 | 从布尔表达式结构推导用例；易评估 | 同样碰不到死代码与错误处理 |
| **路径覆盖（Path）** | 覆盖所有可能路径 | 对逻辑流的覆盖更好 | 路径数可能组合爆炸（n 个 if 可达 2^n）；并非所有路径都可能或必要；隐含「程序结构基本正确」的假设 |

**语句覆盖的三个具体问题**（第 28 页原文）：

- 死代码不会被触及；
- 选择输入集合可能需要相当技巧；
- 容错/错误处理代码可能很难「触到」；
- **这个指标可能产生「删掉错误处理器」的激励**。

最后一条是古德哈特定律（Goodhart's Law）的经典案例：一旦覆盖率成为考核指标，开发者就会优化指标本身而不是质量——把难测的错误处理删掉，覆盖率立刻上升，软件却更不安全。

**分支覆盖**还包括**条件测试**（condition testing, Tai）：**多重条件覆盖（multicondition coverage）**要求覆盖布尔表达式的**所有真值组合**。这对 `if (a && b || c)` 这种复合条件尤其重要——只覆盖「整体真/假」两次，可能漏掉某个子条件从未被单独求值的情况。

**路径覆盖的循环测试建议**（第 30 页）：

- 零次、一次、两次迭代；
- 若有上界 n：n-1、n、n+1 次迭代；
- 嵌套循环/条件从内向外处理。

「零次迭代」是最常被忘记的用例——很多循环 bug 只在「一次都不执行」时出现。

第 31 页留了一个练习：

```java
int binarySearch(int[] a, int key) { 
    int imin = 0;
    int imax = a.length-1;
    while (imax >= imin) { 
        int imid = midpoint(imin, imax); 
        if (a[imid] < key) 
            imin = imid + 1; 
        else if (a[imid] > key ) 
            imax = imid - 1; 
        else 
            return imid; 
    } 
    return -1; 
}
```

要求找出「最大化行覆盖、分支覆盖、路径覆盖」的测试用例。关键用例至少包括：空数组（`imax = -1 < imin = 0`，循环零次）、单元素命中、单元素未命中（小于/大于各一）、命中首元素、命中末元素、未命中且小于全部、未命中且大于全部。

### 5.13 覆盖率的危险与合理用法

课件第 34 页（标注作者 Aldrich）列出了覆盖率分析**会漏掉**的东西：

- 缺失的代码（missing code）——需求里有、代码里没有的功能；
- 错误的边界值；
- 时序问题（timing）；
- 配置问题；
- 数据/内存损坏类 bug；
- 可用性问题；
- 客户需求问题。

结论：

> **覆盖率不是好的充分性判据（adequacy criterion）。应该用它来找出「测试不充分的地方」。**

这两句话的差别是方向性的：

- **当作判据**：覆盖率 85% → 认为可以发布 → 危险，因为漏掉的 15% 可能正是核心逻辑，而覆盖到的 85% 也可能断言写错。
- **当作探照灯**：覆盖率报告显示某个异常处理分支从未被执行 → 去检查「这个分支是不是根本不可能发生？还是我的测试漏了？」→ 有价值。

课件第 35 页给出「理想测试套件」与「真实测试套件」的对照：

| 理想 | 现实 |
|---|---|
| 揭露代码中所有错误 | 只揭露一部分错误 |
| 揭露需求捕获的所有错误（所有场景、非功能属性） | **自身也有错误** |
| 最小规模与复杂度 | 辅助探索性测试以做验证 |
| 尽早揭露错误 | 对非功能属性帮助不大 |
| | 包含大量「修 bug 后补的测试」，防止复发 |

「自身也有错误」这一条尤其诚实：测试代码也是代码，也会写错——一个永远通过的测试（比如忘了 `fail()` 的那个）看起来是绿色的，实际什么都没验证。

## 6. 代码示例

### 6.1 官方课程代码

出自 `08-specification.pdf` 第 10 页（JML 规格）：

```java
/*@ requires len >= 0 && array != null && array.length == len;
@
@ ensures \result == 
@            (\sum int j;  0 <= j && j < len;  array[j]);
@*/
int total(int array[], int len);
```

出自同文件第 22 页（类不变式）：

```java
public class SimpleSet {
    int contents[];
    int size;
    //@invariant sorted(contents);
    SimpleSet(int capacity) { … }
    boolean add(int i) { … }
    boolean contains(int i) { … }
}
```

出自 `08-testing.pdf` 第 15 页（两种异常测试写法）：

```java
@Test
public void testSanityTest(){
    try {
        openNonexistingFile();
        fail("Expected exception");
    } catch(IOException e) { }
}

@Test(expected = IOException.class)
public void testSanityTestAlternative() {
    openNonexistingFile();
}
```

出自同文件第 24 页（覆盖率分析的目标代码）：

```java
public static int binsrch (int[] a, int key) {
    int low  = 0;
    int high = a.length - 1;
    while (true) {
        if ( low > high ) return -(low+1); 
        int mid = (low+high) / 2;
        if      ( a[mid] < key )  low  = mid + 1;
        else if ( a[mid] > key )  high = mid - 1;
        else    return mid; 
    }
}
```

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：带完整规格与不变式的 `IntRange`**

```java
/**
 * 一个整数区间 [low, high]。
 * 规格：
 *   requires: low <= high
 *   ensures:  getLow() == low && getHigh() == high
 * 不变式：low <= high
 */
public final class IntRange {
    private final int low, high;

    public IntRange(int low, int high) {
        if (low > high)                                  // 显式检查：库代码应快速失败
            throw new IllegalArgumentException("low > high: " + low + " > " + high);
        this.low = low;
        this.high = high;
        assert this.low <= this.high;                    // 断言：内部自检
    }
    public int getLow()  { return low; }
    public int getHigh() { return high; }

    /** requires: other != null; ensures: 返回值非负 */
    public int overlapLength(IntRange other) {
        int lo = Math.max(low, other.low);
        int hi = Math.min(high, other.high);
        return Math.max(0, hi - lo + 1);
    }
}
```

要点：构造函数建立不变式 `low <= high`；所有公有方法都不破坏它（字段 `final`，没有 mutator）；`overlapLength` 的前置条件 `other != null` 被违反时会抛 `NullPointerException`——按契约，这**不算**违约。

**示例 B：针对上面这个类的 JUnit 测试，覆盖四类用例**

```java
import org.junit.Test;
import org.junit.Before;
import static org.junit.Assert.*;

public class IntRangeTest {
    private IntRange r;

    @Before
    public void setUp() { r = new IntRange(1, 5); }      // 每个测试独立的新对象

    @Test
    public void testRepresentative() {                   // 代表性用例
        assertEquals(1, r.getLow());
        assertEquals(5, r.getHigh());
        assertEquals(3, r.overlapLength(new IntRange(3, 10)));
    }

    @Test
    public void testBoundary() {                         // 边界用例
        assertEquals(0, r.overlapLength(new IntRange(6, 9)));    // 完全不相交
        assertEquals(1, r.overlapLength(new IntRange(5, 5)));    // 只接触一个点
        assertEquals(5, r.overlapLength(new IntRange(0, 100)));  // 完全包含
    }

    @Test
    public void testSinglePointRange() {                 // 退化情形
        IntRange p = new IntRange(7, 7);
        assertEquals(1, p.overlapLength(p));
    }

    @Test(expected = IllegalArgumentException.class)     // 非法用例：违反前置条件
    public void testInvalidConstruction() {
        new IntRange(5, 1);
    }

    @Test
    public void testNullArgument() {                     // 违反「other != null」
        try {
            r.overlapLength(null);
            fail("Expected NullPointerException");
        } catch (NullPointerException e) { }
    }
}
```

**示例 C：覆盖率不是充分判据的演示**

```java
public static int abs(int x) {
    if (x >= 0) return x;
    return -x;
}
```

一个「100% 语句覆盖 + 100% 分支覆盖」的测试：

```java
assertEquals(5, abs(5));
assertEquals(5, abs(-5));
```

但 `abs(Integer.MIN_VALUE)` 会返回 `Integer.MIN_VALUE`（因为 `-Integer.MIN_VALUE` 溢出），这是错的。分支覆盖达到 100%，bug 依然存在——**因为 bug 在「值域」里，而不在「控制流」里**。这正是课件第 34 页「Incorrect boundary values」的意思。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| 前置条件 | 后置条件 | 前置由**客户端**保证（实现可依赖它）；后置由**实现者**保证（客户端可依赖它）。方向弄反，责任就错位 |
| `assert` 语句 | `org.junit.Assert` 方法 | 前者是 Java 语言关键字，受 `-ea` 控制、默认可关闭；后者是库方法，**始终执行**，且提供 `delta`、消息等 |
| `assert`（开发期自检） | 显式 `if` + `throw`（参数校验） | 前者关闭断言后消失，适合内部不变式；后者始终生效，适合公共 API——课件批注「Good for robust libraries!」 |
| 类不变式 | 方法的前置/后置条件 | 不变式是所有公有方法**共享**的那部分（构造函数建立、方法前后保持）；前后置条件可以因方法而异。`//@invariant` 是后者的 DRY 写法 |
| 不变式「始终成立」 | 不变式「在方法边界成立」 | 后者才对。方法执行**期间**可以临时破坏不变式（如 `enq` 修改 `back` 的两步之间） |
| 单元测试 | 集成/系统测试 | 单元测试针对最小可测单元、依赖少、快；集成测试验证组装后的交互。单元测试「不足够，但是好的起点」 |
| 测试 | 调试（debugging） | 测试**发现**失败；调试**定位并修复**原因。绿色测试不代表没有 bug |
| 语句覆盖 | 分支覆盖 | 前者看流程图**节点**是否被访问；后者看**边**（真/假两个方向）是否都被走。100% 语句覆盖可能只有 50% 分支覆盖（`if (x) A;` 只测 `x` 为真时，语句全覆盖但假分支未测） |
| 分支覆盖 | 路径覆盖 | 前者每个判定的两个方向；后者覆盖完整的执行路径组合，数量可能指数爆炸 |
| 覆盖率作为判据 | 覆盖率作为探针 | 前者危险（高覆盖 ≠ 高质量，还会诱导删错误处理）；后者有价值（找出没被检查的区域） |
| Mock | Stub | Stub 只返回预设值；Mock 还**验证**交互是否按预期发生（如「是否调用了一次 `close()`」）。课件把它们合称 Stub/Mock |
| 测试通过 | 程序正确 | Dijkstra：测试只能证明 bug 的存在，不能证明其不存在。测试通过只说明「这些用例没找到 bug」 |

## 8. 对应原版讲义

本讲对应两份 PDF：

**（1）规格与不变式**

- PDF 相对路径：`90-原始PDF/15-214/slides/08-specification.pdf`
- 总页数：22 页
- 重点页码：
  - 第 2–3 页：四大课程主题回顾、本讲学习目标
  - 第 5 页：软件质量八维度（Braude & Bernstein）
  - 第 6 页：功能性正确的技术全景（15-214 vs 15-313 分工）
  - 第 7 页：`InputStream.read` 的文本规格实例
  - 第 8 页：规格的构成与六条理想属性
  - 第 9 页：函数契约（前置/后置）与「违反前置怎么办」的提问
  - 第 10 页：JML 规格示例（`total` 求和）
  - 第 11–12 页：`InputStream.read` 规格逐条剖析（为何是「无歧义」的样板）
  - 第 13 页：`List.addAll` 的文本规格
  - 第 14 页：质量属性的规格化讨论题（可用性、可修改性、性能、安全、易用性）
  - 第 15–16 页：`assert` 运行时检查 vs 显式参数检查；`java -ea`
  - 第 17–20 页：C 语言队列的 `is_queue` 不变式与 `enq` 的契约
  - 第 21–22 页：类不变式定义与 `SimpleSet` 的两种写法
- 原始网页链接：`https://www.cs.cmu.edu/~aldrich/214/slides/08-specification.pdf`

**（2）测试**

- PDF 相对路径：`90-原始PDF/15-214/slides/08-testing.pdf`
- 总页数：45 页
- 重点页码：
  - 第 1–2 页：功能性正确的技术全景、测试的定义与 Dijkstra 引言
  - 第 3–4 页：测什么、谁测、何时测
  - 第 5 页：单元测试的定义与特征
  - 第 6 页：二分查找 16 年才写对的历史（Knuth、Bentley）
  - 第 7–9 页：测试用例策略与 `total` 示例清单
  - 第 10–13 页：JUnit 入门、`assert` vs `Assert`、JUnit 约定
  - 第 14–15 页：`@Before` 与异常测试两种写法
  - 第 16 页：测试组织约定（同包、独立目录）
  - 第 17–18 页：优先队列测试练习
  - 第 20–22 页：可测试代码、TDD、频繁运行测试、持续集成
  - 第 24–31 页：方法/语句/分支/路径覆盖与二分查找练习
  - 第 32 页：不可测试代码的反面教材（`thedailywtf.com`）
  - 第 33 页：覆盖率工具 EclEmma
  - 第 34–35 页：覆盖率的危险、理想与真实测试套件
  - 第 36 页：总结
  - 第 38–43 页：附加内容——Mock Objects
  - 第 44–45 页：TDD 与实践中的实证结果（标题页）
- 原始网页链接：`https://www.cs.cmu.edu/~aldrich/214/slides/08-testing.pdf`

> 待核实：`08-specification.pdf` 第 15、16 页的 `sum` 函数中 `assert …;` 位于 `return sum;` 之后（不可达代码），第 16 页 `throw IllegalArgumentException(…)` 缺 `new`；`08-testing.pdf` 第 14 页的 `@Before` 方法体内花括号不配对、第 38–40 页 Mock 示例中 `new List()` 应为 `new ArrayList<>()`，均属幻灯片排版问题。

## 9. 对应视频

未找到官方公开录像。2013 年秋季的 15-214 课堂没有公开发布录像，故不提供链接与时间戳。

## 10. 本节复习

- 软件质量有八个维度，功能性正确只是其中一个；本课只覆盖规格、单元测试、类型检查三块。
- 好规格六条：完整、最小、无歧义、一致、可测试、正确。
- 契约 = 前置（客户端负责）+ 后置（实现者负责）；前置被违反时契约不要求任何东西。
- JML：`requires` / `ensures` / `\result` / `invariant`。
- `assert` 受 `-ea` 控制可关闭，适合内部自检；显式 `if` + `throw` 始终生效，适合公共 API。
- 类不变式：构造函数建立，公有方法前后保持，**方法执行中可临时破坏**。
- 单元测试：最小单元、快、独立、依赖少；额外收益是可执行文档与可测试设计。
- JUnit：`@Test`、`@Before`、`@Test(expected=...)`、`Assert` 系列断言；测试方法无参无返回。
- 异常测试必须写 `fail("Expected exception")`，否则测试可能永远通过。
- 覆盖四级：方法 → 语句 → 分支 → 路径；粒度越细越贵，且都不能防住「值域 bug」。
- 覆盖率不是充分性判据，应当作「找出测试薄弱点」的探针。
- Dijkstra：测试只能证明 bug 的存在，不能证明其不存在。

## 11. 自我检查

1. 为下面这个方法写出前置条件与后置条件（用自然语言或 JML 均可），并说明如果调用者传了 `null`，实现者是否违约。
   ```java
   /** 返回数组中最大的元素 */
   int max(int[] array);
   ```
2. 为什么说「类不变式在方法执行期间可以被临时破坏」？请用一个具体的赋值序列说明这种「临时破坏」是不可避免的。
3. 下面这个测试有什么问题？请指出并改正。
   ```java
   @Test
   public void testThrows() {
       try {
           divide(1, 0);
       } catch (ArithmeticException e) {
           // 正确抛出了异常
       }
   }
   ```
4. 某模块的语句覆盖率达到 100%、分支覆盖率达到 100%，能否认为它「测试充分」？请举出至少三类这样仍然可能漏掉的缺陷。
5. 解释为什么「覆盖率指标可能产生删除错误处理代码的激励」，并说明团队应当如何正确使用覆盖率报告。

<details>
<summary>参考答案</summary>

1. **前置条件**：`array != null && array.length >= 1`（若允许空数组，则必须另行规定返回值，例如抛异常或返回哨兵值——这正是规格必须「无歧义」的地方）。**后置条件**：`\result` 是 `array` 中所有元素的某个上界，且存在下标 `j` 使得 `array[j] == \result`（即返回值确实取自数组，而不只是「大于等于所有元素」）。JML：`requires array != null && array.length >= 1; ensures (\forall int j; 0 <= j && j < array.length; \result >= array[j]) && (\exists int j; 0 <= j && j < array.length; \result == array[j]);`。**传 `null` 时实现者不违约**：`array != null` 是前置条件的一部分，客户端违反前置后契约不要求任何行为；实现抛 `NullPointerException` 完全合法。但按课件的工程建议，公共库最好显式检查并抛 `NullPointerException` 或 `IllegalArgumentException` 以便快速失败。

2. 因为不变式描述的是**结构的完整性**，而修改结构往往需要多个步骤，中间状态必然不完整。以课件第 19 页的 `enq` 为例：
   ```c
   Q->back->data = s;     // 步骤 1：把数据写进当前尾节点
   Q->back->next = l;     // 步骤 2：把新节点接到尾节点之后
   Q->back = l;           // 步骤 3：尾指针前移
   ```
   在步骤 1 与步骤 2 之间，`back->next` 仍为 `NULL`，此时若调用 `is_queue(Q)` 会返回 `false`（`front` 沿 `next` 走不到 `back`）。这个中间状态是**不可避免**的——除非用一次原子操作同时更新两处（多数语言无法做到）。因此不变式只能约束「可观察点」，即方法进入与退出的边界。这也解释了为什么不变式是**封装**的一部分：只要没有外部代码能在中间状态观察到对象，破坏就是安全的。

3. 问题：**如果 `divide(1, 0)` 没有抛异常，这个测试也会通过**——`try` 块正常结束后方法就返回了，JUnit 认为测试成功。这个测试实际上什么都没验证，是一个「永远绿色」的假测试（属于课件第 35 页所说的「测试自身也有错误」）。改正有两种：
   ```java
   // 方式一：补 fail
   @Test
   public void testThrows() {
       try {
           divide(1, 0);
           fail("Expected ArithmeticException");
       } catch (ArithmeticException e) { }
   }
   // 方式二：用注解（更简洁）
   @Test(expected = ArithmeticException.class)
   public void testThrows() { divide(1, 0); }
   ```
   注意方式二也有局限：它只检查异常类型，且如果异常在方法更早的位置抛出也会通过，无法确认是「因为除零」而不是别的原因。

4. **不能**。至少三类仍会漏掉：
   - **值域/边界缺陷**：如 `abs(Integer.MIN_VALUE)` 溢出，控制流完全覆盖但结果错误；
   - **缺失的代码**：需求要求但代码里根本没写的功能——覆盖率只统计已存在的代码，永远不会告诉你「少了什么」；
   - **时序与并发问题**：竞态、死锁只在特定交错下出现，覆盖率不反映交错；
   - 另外还有配置问题、数据/内存损坏、可用性问题、非功能属性（性能、安全）等（对应课件第 34 页的清单）。
   课件第 34 页的原话就是：覆盖率不是好的充分性判据。

5. 因为覆盖率的分母是「代码中可执行的结构」，**删掉难测的代码就能提高覆盖率**。容错与错误处理分支（如 `catch` 块、`if (x == null) throw …`）往往需要构造特殊输入才能触及，是最难覆盖的部分；把它们删掉，覆盖率立刻上升而工作量下降——指标变好，质量变差。这正是古德哈特定律：当指标成为目标，它就不再是好指标。正确用法是**把覆盖率当作探针而非判据**：看报告找出「哪些分支从未被执行」，然后逐个问「这个分支是不可能发生（可以删/可简化），还是我的测试漏了（需要补用例）」；同时结合规格审查（检查缺失功能）、边界值分析、非功能测试，而不是追求某个百分比阈值。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-07-Design-Patterns]]
- 下一讲：[[15-214-09-Design-Patterns-Continued]]
- 课程总览：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]
- 课程目录：[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸：JUnit 4 文档与 EclEmma 覆盖率工具；JML 与 ESC/Java2 的形式化验证；「契约式设计」的源头是 Bertrand Meyer 的 Eiffel 语言（Design by Contract）。规格的「框架条件（frame condition）」与本讲的「哪些部分不受影响」直接相关，会在后续讲次中正式命名。
