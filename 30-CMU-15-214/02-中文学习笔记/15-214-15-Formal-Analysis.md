---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L15
topic: Formal Analysis of Software Artifacts
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 形式化分析
  - Dafny
  - 契约式设计
  - 类不变式
  - 循环不变式
  - 行为子类型
  - 里氏替换原则
  - 静态分析
---

# 第 15 讲 软件制品的形式化分析

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。本讲对应 `formal-analysis-part2.pdf`（17 页，页内编号 7–22，说明它是某个更长讲义的第二部分）以及配套讲义笔记 `90-原始PDF/15-214/notes/formal-analysis-notes.txt`。封面版权为 "© 2012-2013 W Scherlis, J Aldrich, C Garrod, and C Kästner"，署名 Jonathan Aldrich、Charlie Garrod。按 2013 年课表，本讲为 10 月 17 日（10 月 15 日为期中考试）。

## 1. 本节学习目标

- 能对比 **测试（Validation，验证）** 与 **证明（Verification，证成）** 在「覆盖的执行数」「能验证的性质」「实用程度」三个维度上的差别。
- 能说明「既然证明还不实用，为什么还要学」这一问题的四个理由。
- 能读懂 Dafny 代码中的 `requires` / `ensures` / `modifies` / `reads` / `invariant` / `decreases` / `old()` / `fresh()` 等规格构造，并说明每个的作用。
- 能解释为什么类不变式 `valid()` 必须显式出现在**构造函数后置条件**、**其他方法的前置条件**、**修改对象的方法的后置条件**三处。
- 能解释 `fresh(contents)` 的作用（防止表示暴露 / 别名）。
- 能用**行为子类型（behavioral subtyping）** 的规则判断一个子类是否合法：不变式相同或更强、后置条件相同或更强、前置条件相同或更弱。
- 能用 `Rectangle` / `Square` 例子说明「语法上合法的继承，行为上可能是非法的子类型」。
- 能说明形式化工具的**能力边界**：它减少手工证明的工作量，但仍需大量规格工作，且可能漏掉缺陷。

## 2. 前置知识

- [[15-214-05-Object-Contracts-and-Exceptions]]：前置条件 / 后置条件 / 契约式设计的基本定义——本讲把它们从「注释」提升为「可被机器检查的公式」。
- [[15-214-08-Specification-and-Testing]]：规格的六条理想属性、`assert` 与类不变式（第 21 页）——本讲直接延续那一节。
- [[15-214-03-Encapsulation-and-Inheritance]] 与 [[15-214-04-Inheritance-Typechecking-Dispatch]]：子类型、覆写、`Is every Foo really a Bar?`——本讲给出这个问题的**形式化判据**。
- [[15-214-11-Design-Principles-GRASP]]：信息隐藏与「接口是客户端被允许依赖的一切」——本讲把「接口」扩展为「契约」。
- CMU 15-122 的循环不变式与数据不变式（讲义笔记开头明确假设学生已学过）。

## 3. 核心概念

- **验证（Validation，测试）**：通过**执行**程序、观察**可观察性质**来发现错误；只覆盖**某一次**执行。
- **证成（Verification，证明）**：通过**逻辑推导**证明程序满足性质；覆盖**所有**执行。
- **Dafny**：微软研究院开发的**语言 + 程序验证器**，命令式、基于对象、**无继承**，内建前置/后置条件、不变式等规格构造。
- **`requires`**：前置条件（precondition），调用者责任。
- **`ensures`**：后置条件（postcondition），实现者责任。
- **`modifies`**：框架条件（frame condition），声明方法可能修改哪些对象——让验证器知道「哪些旧断言可能失效」。
- **`reads`**：函数的读集合，声明函数值依赖哪些对象的字段。
- **`invariant`（类不变式）**：`valid()` 这样的谓词，描述对象在任何**可观察**时刻都必须满足的性质。
- **`invariant`（循环不变式）**：循环开始前为真、每次循环体执行后仍为真的断言。
- **`decreases`**：终止性度量（variant function），每次迭代/递归严格减小且下界为 0。
- **`old(e)`**：方法入口时 `e` 的值（用于后置条件中比较前后状态）。
- **`fresh(x)`**：`x` 是新分配的对象，不与任何已存在对象别名。
- **行为子类型（Behavioral Subtyping）**：子类不仅类型兼容，而且**契约兼容**——可替换父类而不破坏任何客户端依赖。
- **里氏替换原则（Liskov Substitution Principle, LSP）**：若 `q(x)` 是关于类型 `T` 的对象 `x` 可证的性质，则对 `S <: T` 的对象 `y`，`q(y)` 也应可证。

## 4. 通俗理解

**这一讲回答一个很自然的疑问：既然我们已经有测试了，为什么还要学「证明」？**

课件的回答分两步。第一步，第 3 页把两者摆在同一个表里对照：

| | 测试（Validation） | 证明（Verification） |
|---|---|---|
| 能验证的性质 | **可观察性质**（observable properties） | **任意程序性质**（any program property） |
| 覆盖范围 | **一次执行** | **所有执行** |
| 开发方式 | 手工开发 + **自动化回归** | 手工开发 + **自动化证明检查器** |
| 实用程度 | **目前最实用的方法** | 小程序实用，未来可能扩展 |

第二步，课件自己提出反问并回答：

> **So why study proofs if they aren't (yet) practical?**
> - **Proofs tell us how to think about program correctness**
> - **Important for development, inspection, dynamic assertions**
> - **Foundation for static analysis tools**
>   - **These are just simple, automated theorem provers**
> - **Many are practical today!**

这段话是整讲的立论基础。它说的是：**证明的价值不只是「证明」本身，而是它提供的思维方式**。

具体来说：

1. **「如何思考正确性」**——一旦你习惯用「前置条件 → 后置条件」的框架看代码，你写的方法自然会有清晰的契约。这不需要任何工具，纯粹是思维训练。
2. **对开发、代码审查、运行时断言有用**——你在写 `assert` 时，实际上就是在写一个**局部定理**；你在 code review 时说「这个调用违反了前置条件」，就是在做**非形式的证明**。
3. **静态分析工具的基础**——FindBugs、Error Prone、Infer、甚至编译器的类型检查器，本质都是「简化的自动定理证明器」。理解证明理论，才能理解这些工具**为什么只能查某些 bug**、**为什么会有误报**。
4. **「Many are practical today!」**——类型检查是最成功的例子：它证明了一个非常弱但极有用的性质（「所有变量都持有其声明类型的值」），而且**每次编译都在跑**。所以「形式化方法不实用」这个说法是错的，只是**实用的形式化方法都很弱**。

**Dafny 的定位**：它是「介于手工证明与测试之间」的工具。你写规格（`requires`/`ensures`），写实现，Dafny 自动尝试证明「实现满足规格」。如果证不出来，它会指出哪一行无法验证。

Dafny 有一个刻意的设计取舍（讲义笔记第 6 行）：

> The language is imperative and object-based--that is, it has objects like Java, but **no inheritance** (leaving out inheritance **inhibits reuse in some cases, but simplifies verification substantially**).

这个取舍值得注意：**去掉继承，验证就简单很多**。为什么？因为继承引入了「动态分派」——验证器必须考虑「这个调用可能分派到哪个覆写版本」，而覆写版本可能有不同的契约。这正是本讲后半段「行为子类型」要处理的问题。Dafny 干脆不支持继承，绕开了这个难点。

这反过来解释了为什么「行为子类型」是 OOP 验证中最难的部分：**它是继承与契约的交叉点**。

## 5. 原理与推导

### 5.1 从测试到证明：为什么「所有执行」这么难

第 3 页的对照表里，「一次执行」vs「所有执行」是核心差别。

**测试的本质是抽样**：一个测试用例是**一个**输入，它验证程序在**那一个**输入上的行为。第 8 讲讲过的等价类划分、边界值分析，都是在**试图用有限的样本代表无限的输入空间**——但这只是启发式，没有保证。

Dijkstra 1969 年的名言（第 8 讲讲义第 2 页引用过）说得很清楚：

> **Testing shows the presence, not the absence of bugs.**
> （测试只能表明缺陷的存在，不能表明缺陷的不存在。）

**证明的本质是全称量化**：证明「对所有满足前置条件的输入，执行后都满足后置条件」——这是一个 **∀** 命题，覆盖**无穷**多个执行。

这就是为什么证明「更强」但也「更难」：∀ 命题无法通过枚举验证，只能通过**逻辑推导**。而逻辑推导需要**不变式（invariant）**——一个在变化中保持不变的性质。这正是本讲反复出现 `invariant` 关键字的原因。

### 5.2 Dafny 的规格构造：一个完整的例子

讲义笔记与幻灯片都用 `SimpleSet` 作贯穿例子。先看类不变式（幻灯片第 4 页）：

```dafny
class SimpleSet {
  var contents: array<int>;
  var size:int;

  function valid() : bool
    reads this, contents;
  {size >= 0
   && contents != null
   && contents.Length >= size }
```

课件对这一页的批注（逐条抄录）：

> - **`valid()` represents the class invariant.**
>   **It must be explicitly added to:**
>   - **The constructor postcondition**
>   - **The precondition of functions and methods**
>   - **The postcondition of methods that modify `this`**
> - **A Dafny `function` is used in specifications. It cannot be called (though function methods can).**
> - **The `reads` clause of a function defines the objects on whose fields the function's value depends. This is so Dafny can determine when a function's value might be affected by a field write.**
> - **In this case the class invariant asserts that:**
>   - **The size is non-negative**
>   - **The contents array is non-null**
>   - **The contents array is big enough to hold `size` elements**

**为什么不变式要显式写三遍？** 这是 Dafny（以及所有契约式验证工具）与人类直觉的最大差别。

人类看代码时会**默认**「不变式总是成立」，但验证器只认**它被明确告知的东西**。所以必须在三个「边界」处显式声明：

| 位置 | 为什么需要 |
|---|---|
| **构造函数后置条件** | 构造完成后，不变式**第一次**成立。验证器需要被告知「新对象是有效的」 |
| **普通方法的前置条件** | 方法**可以假定**不变式成立（因为调用者保证对象有效）。若不写，验证器会认为对象可能是任意状态 |
| **修改 `this` 的方法的后置条件** | 方法**必须重新建立**不变式。若不写，验证器无法知道方法结束后对象仍然有效 |

这三个位置构成一个**归纳**结构：

```
构造 → valid() 成立        （基础情形）
valid() → 方法执行 → valid()  （归纳步骤）
```

**这与第 8 讲的「类不变式在方法前后成立、执行中可临时破坏」完全一致**——只是那里是注释，这里是可检查的公式。

**`reads` 子句的作用**（课件批注）：声明函数的返回值依赖哪些对象的哪些字段。这样验证器在遇到 `contents[i] := x` 这样的写操作时，能判断「`valid()` 的值可能变了，之前的断言失效了」。

如果没有 `reads`，验证器只有两个选择：要么假设「任何写都可能影响任何函数值」（过于保守，几乎什么都证不出来），要么假设「函数值永远不变」（不可靠）。`reads` 让验证器**精确**地知道依赖关系。

这与第 11 讲「框架条件（frame condition）」是同一个概念——`reads` 是**读**的框架，`modifies` 是**写**的框架。

### 5.3 构造函数与 `fresh`：防表示暴露的形式化

幻灯片第 5 页：

```dafny
method init(capacity:int)
  requires capacity >=0;
  modifies this;
  ensures valid();
  ensures size == 0;
  ensures contents.Length == capacity;
  ensures fresh(contents);
{
  contents := new int[capacity];
  size := 0;
}
```

课件批注：

> - **An ordinary method can be called to initialize an object in Dafny. Here, `init` acts like a constructor.**
> - **We have to say what objects each method modifies. That way Dafny knows that previous assertions about the object might no longer be true.**
> - **The constructor establishes the class invariant, so `valid()` is in the postcondition (the `ensures` clause). `valid()` is not in the precondition because the object is uninitialized before calling `init`.**
> - **This helps Dafny to know that `contents` does not alias an external array. If it did, we could mess up the invariants of `SimpleSet` by writing to the external array.**

**最后一条批注是本讲最重要的洞察之一**。它说的是：

> `fresh(contents)` 告诉验证器「`contents` 是新分配的，不与任何外部数组别名」。如果它别名了外部数组，那么外部代码写那个数组就会**破坏 `SimpleSet` 的不变式**。

这正是第 6 讲「表示暴露（representation exposure）」与「防御性拷贝」的形式化版本！

回忆第 6 讲：不可变类要「保证独占访问」「防御性拷贝」「不泄漏内部表示」。当时的论证是**非形式的**（「如果别人拿到你的内部数组，就能改它」）。现在有了 `fresh`，这个论证变成**可机器检查的**：

- 若构造函数写 `contents := externalArray;`，则 `fresh(contents)` **无法证明**，验证失败；
- 若写 `contents := new int[capacity];`，则 `fresh(contents)` 成立。

**这就是形式化方法的价值**：它把「设计原则」变成「可检查的规则」。你不需要记住「要做防御性拷贝」，验证器会告诉你。

**`modifies this` 的作用**（批注第二条）：声明这个方法可能修改 `this` 的字段。验证器据此判断「调用此方法后，之前关于 `this` 的断言都失效了」。若不写 `modifies`，验证器会假设方法**不改变任何东西**——这在有副作用的方法上是错的，会导致**不可靠**（证出了错误的结论）。

这与第 8 讲「框架条件」的定义完全对应：**框架条件说明「什么没有变」，从而让调用者能保留关于未变部分的推理**。

### 5.4 方法规格：`old()` 与前后状态比较

幻灯片第 6 页：

```dafny
method add(i:int)
  requires valid();
  requires size < contents.Length || i in mset();
  modifies this, contents;
  ensures valid();
  ensures mset() == old(mset()) + {i};
  ensures contents == old(contents);
  ensures i in old(mset()) ==> size == old(size);
  ensures !(i in old(mset())) ==> size == old(size)+1;
{ … }
```

课件批注（逐条）：

> - **This method modifies the receiver object and its constituent array.**
> - **Typically methods other than the constructor need to assume the class invariant holds.**（指 `requires valid();`）
> - **Since we modified the object we need to assert the class invariant again.**（指 `ensures valid();`）
> - **The identity of the `contents` array did not change.**（指 `ensures contents == old(contents);`）
> - **Size is incremented iff the element was not in the mathematical set represented by this `SimpleSet` when the method was called.**（指最后两条 `ensures`）

逐条解读：

**（1）`requires size < contents.Length || i in mset();`**

这是前置条件，但它写得很讲究：**只有在「数组已满」且「`i` 不在集合里」时才需要扩容**。换句话说：

- 若 `size < contents.Length`（还有空位）→ 可以直接加；
- 若 `size == contents.Length`（满了）但 `i` 已在集合里 → 不需要加，直接返回；
- 若满了且 `i` 不在 → **前置条件不满足**，调用者必须先扩容。

这个前置条件精确地描述了「什么时候调用 `add` 是合法的」。它比「数组不能满」更宽松（因为「满了但元素已存在」是合法的），也比「总是合法」更严格。

**这正是第 8 讲「前置条件是客户端责任」的体现**：`add` 不负责扩容，它把「确保有空间」的责任交给调用者。这个设计选择（而不是让 `add` 自己扩容）让 `add` 的实现简单、后置条件清晰。

**（2）`ensures mset() == old(mset()) + {i};`**

`mset()` 是一个**抽象函数**（幻灯片第 7 页）：

```dafny
function mset() : set<int>
  reads this, contents;
  requires valid();
{
  set j:int | 0 <= j < size :: contents[j]
}
```

这是 Dafny 的**集合推导式**（set comprehension）：`{contents[j] | 0 <= j < size}`，即「`contents[0..size)` 这些元素构成的数学集合」。

`mset()` 是 `SimpleSet` 的**抽象值（abstraction function）**——它把「一个数组 + 一个长度」这个**表示（representation）**映射到「一个数学集合」这个**抽象值**。

有了它，后置条件就能写成**抽象的**：

> 新集合 = 旧集合 ∪ {i}

而**不需要**提及 `contents` 数组的具体布局（比如「新元素加在 `contents[size]` 位置」）。这是**规格与实现解耦**的关键：只要实现满足「抽象集合加了 i」这个后置条件，具体怎么存都行。

**这与第 8 讲「规格应说明做什么，而非怎么做」完全一致**，只是这里的形式让它可以被机器检查。

**（3）`ensures contents == old(contents);`**

课件批注：「`contents` 数组的**身份**没有变」。

注意在 Dafny 里，`array` 是**引用类型**，`==` 比较的是**引用身份**（identity），不是内容。所以这条后置条件说的是「`add` 不会重新分配数组」——它只是往已有数组里写。

**为什么这条重要？** 因为如果 `add` 重新分配了数组，那么：
- 之前持有 `contents` 引用的代码（如果有）会看到旧数组；
- 但 `contents` 字段已经指向新数组，两者不一致 → 别名问题。

所以这条后置条件**排除了「悄悄替换数组」这种实现**，让客户端可以安全地假定「数组对象稳定」。

**（4）最后两条：`i in old(mset()) ==> size == old(size)`**

这是**分情形**的后置条件，用逻辑蕴含 `==>` 表达：

| 情形 | 后置条件 |
|---|---|
| `i` 已在旧集合中 | `size` 不变（因为 `Set` 不允许重复） |
| `i` 不在旧集合中 | `size` 增加 1 |

这是 `Set` 语义的形式化表达：**加一个已存在的元素是 no-op**。注意它用的是 `old(mset())` 而不是 `mset()`——必须看**调用前**的状态。

**这四条 `ensures` 合起来，完整地刻画了 `add` 的行为**：
- 对象仍然有效（`valid()`）；
- 抽象集合加了一个元素（`mset()`）；
- 底层数组身份不变（`contents`）；
- `size` 按「是否新增」精确变化。

这个规格**完整**（覆盖所有情形）、**精确**（每种情形都有确定结论）、**抽象**（不提及数组布局）。它符合第 8 讲「规格六属性」的全部要求，而且**可被机器检查**。

### 5.5 循环不变式与 `decreases`：`contains` 的验证

幻灯片第 8 页：

```dafny
method contains(i:int) returns (b: bool)
  requires valid();
  ensures b <==> i in mset();
{
  var j := 0;
  while (j < size)
    invariant 0 <= j <= size;
    invariant !(i in set k:int | 0 <= k < j :: contents[k]);
    decreases size - j;
  {
    if (contents[j] == i) { return true; }
    j := j + 1;
  }
  return false;
}
```

**后置条件 `ensures b <==> i in mset();`**：返回值 `b` 为真**当且仅当** `i` 在抽象集合里。这是 `contains` 的完整规格——一个**等价式**（`<==>`），比两个蕴含更强。

**两条循环不变式**：

| 不变式 | 含义 |
|---|---|
| `0 <= j <= size` | `j` 在合法范围内（数组边界安全） |
| `!(i in set k:int \| 0 <= k < j :: contents[k])` | **`i` 不在 `contents[0..j)` 中** |

第二条是核心：它说的是「**已经检查过的部分不含 `i`**」。这就是循环的**进度不变式**。

**验证的逻辑结构**：

1. **初始化**：`j = 0` 时，`contents[0..0)` 是空集，`i` 自然不在其中 → 第二条不变式成立。
2. **保持**：循环体里如果 `contents[j] == i` 就 `return true`（此时后置条件成立，因为 `i in mset()`）；否则 `j++`，此时 `contents[0..j)` 扩展了一个元素 `contents[j-1]`，而它不等于 `i`（因为没 return），所以不变式仍成立。
3. **终止**：循环结束时 `j >= size`，结合 `j <= size` 得 `j == size`，于是第二条不变式变成「`i` 不在 `contents[0..size)` 中」，即「`i` 不在 `mset()` 中」→ 返回 `false` 满足后置条件。

**这个「不变式在循环退出时恰好等于后置条件」的模式，是循环不变式设计的标准技巧**（讲义笔记第 65 行明确说了这一点）：

> We choose our loop invariant so that when the loop exit condition is true, the postcondition of the function has been established. In fact our loop invariant looks just like our postcondition, except that the length of the array is replaced with the index.

翻译：**循环不变式 = 后置条件，把「数组长度」换成「当前索引」**。这样循环退出（索引到达长度）时，不变式自动变成后置条件。

**`decreases size - j;`**：终止性度量。`size - j` 每次迭代减 1，下界为 0，所以循环必然终止。

讲义笔记对 `decreases` 的定义（第 67 行）：

> A variant function is an integer-valued expression that **decreases on each iteration**, and is **bounded below by 0** at the end of the loop iteration. If the variant function decreases by at least 1 each iteration, and is bounded below by 0, then the loop must eventually terminate.

**注意一个实用细节**（讲义笔记第 71 行）：

> You may have noticed that Dafny verified our `FindMax` implementation even before we added the `decreases` annotation to the loop. **Dafny tries to infer `decreases` clauses automatically if they are not specified**, and is successful in many simple cases such as this loop.

Dafny 会**自动推断** `decreases`，简单情形下能成功。但复杂情形（比如度量不是显然的线性递减）需要手写。这个设计降低了使用门槛：大部分循环不用写 `decreases`。

### 5.6 讲义笔记中的其他 Dafny 例子

讲义笔记（`formal-analysis-notes.txt`）提供了四个完整例子，幻灯片没有全部展开，但它们是理解 Dafny 的好材料。

**（1）`Max`：最简单的规格**

```dafny
method Max(a: int, b:int) returns (c: int)
  ensures (c == a || c == b) && c >= a && c >= b;
{
  if (a > b)
    { return a; }
  else
    { return b; }
}
```

后置条件三部分：
- `c == a || c == b`：返回值必须是**其中一个**参数（不能凭空造）；
- `c >= a && c >= b`：返回值必须**不小于两者**。

合起来就是「`c` 是 `a` 和 `b` 中的较大者」。注意这个规格**没有前置条件**（任何 `int` 都行）——这是最理想的规格。

讲义笔记还讲了一个教学细节（第 26–38 行）：

> We will add a specification, but before we do, let's write a test function for Max. An assertion verifies the correct result:
> ```dafny
> method TestMax()
> {
>   var m := Max(10,5);
>   assert m == 10;
> }
> ```
> Of course, the Dafny program verifier **cannot prove that the assertion will succeed, because it doesn't look inside `Max`**--it only looks at `Max`'s specification, which we have not yet written.

**这段话极其重要**：验证器**不看方法体**（在验证调用者时），它只看**规格**。所以在写规格之前，`TestMax` 的断言无法证明。

这是**模块化验证（modular verification）** 的核心：每个方法单独验证「实现满足规格」，调用者只依赖规格。这样验证可以**分模块进行**，不需要一次性看整个程序。

**这与第 11 讲的「信息隐藏」完全同构**：规格就是方法的「接口」，实现是「被隐藏的决策」。验证器只依赖接口。

**（2）`FindMax`：数组与循环**

```dafny
method FindMax(a: array<int>) returns (m: int)
   requires a != null && a.Length >= 1;
   ensures forall k :: 0 <= k < a.Length ==> m >= a[k];
   ensures exists k :: 0 <= k < a.Length && m == a[k];
{
   m := a[0];
   var index := 1;
   while (index < a.Length)
      invariant 0 <= index <= a.Length;
      invariant forall k :: 0 <= k < index ==> m >= a[k];
      invariant exists k :: 0 <= k < index && m == a[k];
      decreases a.Length - index;
   {
      m := Max(m, a[index]);
      index := index + 1;
   }
}
```

两条后置条件（**∀ + ∃ 的经典组合**）：

| 后置条件 | 含义 |
|---|---|
| `forall k :: 0 <= k < a.Length ==> m >= a[k]` | `m` 是**上界**（不小于任何元素） |
| `exists k :: 0 <= k < a.Length && m == a[k]` | `m` 是**可达的**（等于某个元素） |

**为什么需要两条？** 单有第一条不够——任何足够大的数都是上界（比如 `Integer.MAX_VALUE`），但它不是最大值。单有第二条也不够——任何元素都满足，但不是最大值。**两条合起来**才唯一确定最大值：它是上界，且它自己就在数组里。

这个「∀ + ∃」的模式是**规格设计的通用技巧**：∀ 保证「不漏」，∃ 保证「不虚」。

**三条循环不变式**与后置条件一一对应，只是把 `a.Length` 换成 `index`：

| 不变式 | 对应后置条件 |
|---|---|
| `0 <= index <= a.Length` | （边界安全，无对应） |
| `forall k :: 0 <= k < index ==> m >= a[k]` | 第一条（上界），范围缩小到已处理部分 |
| `exists k :: 0 <= k < index && m == a[k]` | 第二条（可达），范围缩小到已处理部分 |

循环退出时 `index == a.Length`，三条不变式**恰好变成**后置条件。这就是 5.5 节说的标准模式。

**（3）`fib` 与 `ComputeFib`：数学函数 vs 高效实现**

```dafny
function fib(n: nat): nat
  decreases n;
{
    if n == 0 then 0 else
    if n == 1 then 1 else
                   fib(n - 1) + fib(n - 2)
}
```

这是**数学定义**（递归、指数级慢），但它是**规格**。

```dafny
method ComputeFib(n: nat) returns (b: nat)
   ensures b == fib(n);
{
   if (n == 0) { return 0; }
   var i: int := 1;
   var a := 0;
       b := 1;
   while (i < n)
      invariant 0 < i <= n;
      invariant a == fib(i - 1);
      invariant b == fib(i);
   {
      a, b := b, a + b;
      i := i + 1;
   }
}
```

这是**高效实现**（线性时间、常数空间），后置条件是 `b == fib(n)`。

**这个例子的教学价值**：它展示了「**用数学函数作为规格，用命令式代码作为实现，然后证明两者等价**」。这是形式化方法最典型的用法：

```
数学定义（清晰但低效）  ← 规格
        ⇕ 证明等价
命令式实现（高效但难懂） ← 实现
```

两条循环不变式 `a == fib(i-1)` 与 `b == fib(i)` 精确地描述了「两个滚动变量分别持有相邻的斐波那契数」。循环退出时 `i == n`，于是 `b == fib(n)`，正是后置条件。

注意 `a, b := b, a + b;` 是**并行赋值**（simultaneous assignment）——右边的 `a` 和 `b` 都是**旧值**。这是 Dafny（以及 Go、Python）的语法，避免了临时变量。

**（4）`Ack`：多重终止度量**

```dafny
function Ack(m: nat, n: nat): nat
   decreases m, n;
{
   if m == 0 then n + 1
   else if n == 0 then Ack(m - 1, 1)
   else Ack(m - 1, Ack(m, n - 1))
}
```

阿克曼函数是**非原始递归**的经典例子——它的值增长极快，且不能用简单的循环实现。它的终止性证明需要**字典序**（lexicographic）度量：先比 `m`，`m` 相同再比 `n`。

`decreases m, n;` 表达的就是这个字典序：`(m, n)` 按字典序递减。

**为什么普通的多参数 `decreases` 不够？** 因为在递归调用 `Ack(m - 1, Ack(m, n - 1))` 里：
- 内层 `Ack(m, n-1)`：`m` 不变、`n` 减 1 → 字典序减小 ✓；
- 外层 `Ack(m-1, ...)`：`m` 减 1 → 字典序减小 ✓（无论第二个参数多大）。

字典序保证了「每一层递归都严格下降」，因此必然终止。这是一个**非平凡**的终止性证明——人类需要想一会儿，Dafny 只需一行 `decreases m, n;`。

### 5.7 行为子类型：从类型兼容到契约兼容

幻灯片第 9 页把话题从「单个方法的验证」转向「继承层次中的验证」：

> **Behavioral Subtyping (Liskov Substitution Principle)**
> - **An object of a subclass should be substitutable for an object of its superclass**
> - **Known already from types:**
>   - **May use subclass instead of superclass**
>   - **Subclass can add, but not remove methods**
>   - **Overridden method must return same or supertype**
>   - **Overridden method may not throw additional exceptions**
> - **Applies more generally to behavior:**
>   - **A subclass must fulfill all contracts that the superclass does**
>     - **Same or stronger invariants**
>     - **Same or stronger postconditions for all methods**
>     - **Same or weaker preconditions for all methods**
> - **Let `q(x)` be a property provable about objects `x` of type `T`. Then `q(y)` should be provable for objects `y` of type `S` where `S` is a subtype of `T`.** — Barbara Liskov

这一页分两层：**类型层**（编译器能检查的）与**行为层**（编译器检查不了的）。

**类型层的规则**（第 3–4 讲讲过的）：

| 规则 | 原因 |
|---|---|
| 可以用子类替换父类 | 子类至少有父类的全部方法 |
| 子类可增加方法，不可删除 | 否则客户端调不到 |
| 覆写方法的返回类型必须是**相同或子类型**（协变返回） | 客户端期待父类型，子类型更具体 → 安全 |
| 覆写方法不可抛**额外**的受检异常 | 否则客户端的 `catch` 块可能漏掉 |

**行为层的规则**（本讲新增）：

| 规则 | 直白解释 |
|---|---|
| **不变式相同或更强** | 子类对象满足父类不变式，且可能更多 |
| **后置条件相同或更强** | 子类**承诺至少一样多**（可以多承诺） |
| **前置条件相同或更弱** | 子类**要求至多一样多**（可以少要求） |

**为什么方向是这样？** 关键在**替换**：客户端持有父类引用，按父类契约编写代码。换成子类对象后：

- 客户端**调用**方法时，会**满足父类的前置条件**。如果子类的前置条件**更强**（要求更多），那么客户端的调用可能**不满足**子类的要求 → 出错。所以子类的前置条件必须**更弱或相同**。
- 客户端**依赖**方法的**后置条件**。如果子类的后置条件**更弱**（承诺更少），那么客户端依赖的性质可能**不成立** → 出错。所以子类的后置条件必须**更强或相同**。
- 客户端**依赖**对象的不变式（比如假定「列表始终有序」）。如果子类的不变式**更弱**，客户端的依赖可能失效 → 出错。所以子类的不变式必须**更强或相同**。

这个推理有一个漂亮的记忆口诀：**「前置不能变强，后置不能变弱，不变式不能变弱」**——即**子类只能「要求更少、承诺更多」**。

**这与第 5 讲的契约式设计完全一致**，只是那里是文字论证，这里是形式规则。

### 5.8 `Vehicle` / `Car` / `Hybrid`：合法的行为子类型

幻灯片第 10–11 页给出一个**正确的**继承例子：

```java
abstract class Vehicle {
  int speed, limit;
  //@ invariant speed < limit;
  //@ requires speed != 0;
  //@ ensures |speed| < |\old{speed}|
  void break();
}

class Car extends Vehicle {
  int fuel;
  boolean engineOn;
  //@ invariant fuel >= 0;
  //@ requires fuel > 0 && ! engineOn;
  //@ ensures engineOn;
  void start() { … }
  void accelerate() { … }
  //@ requires speed != 0;
  //@ ensures |speed| < |\old{speed}|
  void break() { … }
}
```

课件批注：

> - **Subclass fulfills the same invariants (and additional ones)**
> - **Overridden method has the same pre and postconditions**

检查：

| 规则 | `Car` 的实际情况 | 判定 |
|---|---|---|
| 不变式 | 父 `speed < limit`；子 `fuel >= 0`（**新增**，父类不变式仍隐含） | ✓ 更强 |
| `break()` 前置 | 与父类**相同**（`speed != 0`） | ✓ 相同 |
| `break()` 后置 | 与父类**相同**（`\|speed\| < \|\old{speed}\|`） | ✓ 相同 |

注意 `break()` 的后置条件用了 `|\old{speed}|`——**绝对值**。这很重要：刹车后速度的**绝对值**减小。为什么用绝对值？因为车可能**倒车**（速度为负）。刹车让「速度的绝对值」变小，无论正负。这个细节说明**规格必须考虑所有合法状态**——如果写成 `speed < \old{speed}`，那么对负速度就错了（刹车应该让 `-10` 变成 `-5`，而 `-5 > -10`）。

**这是一个很好的规格陷阱例子**：直觉上「刹车让速度减小」，但形式化时必须写「速度的绝对值减小」。

再看 `Hybrid`（第 11 页）：

```java
class Hybrid extends Car {
  int charge;
  //@ invariant charge >= 0;
  //@ requires (charge > 0 || fuel > 0) && ! engineOn;
  //@ ensures engineOn;
  void start() { … }
  void accelerate() { … }
  //@ requires speed != 0;
  //@ ensures |speed| < |\old{speed}|
  //@ ensures charge > \old{charge}
  void break() { … }
}
```

课件批注：

> - **Subclass fulfills the same invariants (and additional ones)**
> - **Overridden method `start` has weaker precondition**
> - **Overridden method `break` has stronger postcondition**

检查：

**`start()` 的前置条件**：
- `Car`：`fuel > 0 && !engineOn`
- `Hybrid`：`(charge > 0 || fuel > 0) && !engineOn`

`Hybrid` 的条件**更弱**（`charge > 0` 也能启动，即使 `fuel == 0`）。**更弱的前置条件 = 更宽松的要求 = 合法**。✓

这在语义上完全正确：混动车有电也能启动，所以「需要油」这个要求被放宽了。客户端按 `Car` 的契约（保证有油）调用 `start()`，在 `Hybrid` 上必然成功（因为有油就满足 `charge > 0 || fuel > 0`）。

**`break()` 的后置条件**：
- `Car`：`|speed| < |\old{speed}|`
- `Hybrid`：`|speed| < |\old{speed}|` **且** `charge > \old{charge}`

`Hybrid` 承诺**更多**（还保证充电）。**更强的后置条件 = 更多的承诺 = 合法**。✓

语义上：混动车刹车时**能量回收**，所以电池电量增加。这是一个额外的保证，客户端可以依赖它（但客户端若只按 `Car` 编程，就不会依赖——这不违反契约）。

**这两个例子完美演示了「前置更弱、后置更强」的合法性**。而且它们都有清晰的**物理直觉**：混动车「更容易启动」（前置更弱）、「刹车还能充电」（后置更强）。

### 5.9 `Rectangle` / `Square`：非法的行为子类型

幻灯片第 12–16 页用五页逐步构造一个**经典反例**。

**第 12 页**：最初的版本

```java
class Rectangle {
  int h, w;
  Rectangle(int h, int w) {
    this.h=h; this.w=w;
  }
  //methods
}

class Square extends Rectangle {
  Square(int w) {
    super(w, w);
  }
}
```

> **Is `Square` a behavior subtype of `Rectangle`?**

此时没有不变式，也没有方法——**无法判断**。课件故意留白，引导思考「需要更多信息」。

**第 13 页**：加不变式

```java
class Rectangle {
  //@ invariant h>0 && w>0;
  int h, w;
  …
}

class Square extends Rectangle {
  //@ invariant h==w;
  …
}
```

> **Is `Square` a behavior subtype of `Rectangle`?**

检查不变式：`Square` 的 `h == w` **蕴含** `h > 0 && w > 0`（因为 `Square` 构造时 `super(w, w)`，且…嗯，其实这里有个漏洞：如果 `w <= 0`，`h == w` 成立但 `h > 0` 不成立）。

严格来说，`Square` 还需要 `w > 0` 才满足父类不变式。但课件的意图是「`Square` 的不变式更强」，所以这一步**暂时**判为合法。真正的破坏来自方法。

**第 14 页**：加 `scale`

```java
class Rectangle {
  //@ invariant h>0 && w>0;
  int h, w;
  …
  void scale(int factor) {
    w=w*factor;
    h=h*factor;
  }
}
```

`scale` 同时缩放两个维度。对 `Square` 来说，`h` 和 `w` 都乘以 `factor`，`h == w` **仍然成立**（因为 `h*factor == w*factor`）。所以 `scale` **不破坏** `Square` 的不变式。✓

**第 15 页**：加 `setWidth`

```java
class Rectangle {
  //@ invariant h>0 && w>0;
  int h, w;
  …
  void scale(int factor) {
    w=w*factor;
    h=h*factor;
  }
  void setWidth(int neww) {
    w=neww;
  }
}
```

`setWidth` 只改 `w`，不改 `h`。

**第 16 页**：结论

> **With these methods, `Square` is not a behavior subtype of `Rectangle`**
> **← Invalidates stronger invariant (w==h) in subclass**

**为什么？** 因为：

1. `Rectangle` 的契约允许客户端调用 `setWidth(5)`，期望「`w` 变成 5，`h` 不变」；
2. 但 `Square` 有不变式 `h == w`。如果 `setWidth(5)` 把 `w` 改成 5 而不改 `h`，那么 `h != w`（除非 `h` 恰好是 5）→ **`Square` 的不变式被破坏**；
3. 如果 `Square` 覆写 `setWidth` 让它**同时**改 `h`，那么它**违反了 `Rectangle` 的后置条件**（「`h` 不变」）→ 也非法。

**两条路都走不通**。所以 `Square` **不可能**是 `Rectangle` 的行为子类型（在 `setWidth` 存在的前提下）。

**这是一个深刻的教训**：`Square` **语法上**是 `Rectangle` 的子类（`extends` 合法、`is-a` 在数学上成立——正方形是矩形），但**行为上**不是子类型。

课件用五页逐步「加料」的方式，演示了**为什么这个问题不能靠直觉回答**：必须看**完整的契约**（不变式 + 所有方法的前/后置条件）。只有当 `setWidth` 出现时，矛盾才暴露。

**这与第 3 讲的「Is every Foo really a Bar?」完全呼应**——那一讲用文字警告「继承要小心」，这一讲给出**形式判据**。

**如何修复？** 有几种方案（笔记补充，非讲义内容）：

1. **让 `Square` 不继承 `Rectangle`**——两者独立，各自实现 `Shape` 接口（只读操作）。这符合「优先组合而非继承」。
2. **让 `Rectangle` 不可变**——去掉 `setWidth`/`scale`，改用 `withWidth(int)` 返回**新对象**。这样 `Square.withWidth(5)` 可以返回一个**新的 `Rectangle`**（不是 `Square`），契约仍成立。这是 `BigInteger`、`String` 等不可变类的做法。
3. **把 `setWidth` 的契约写弱**——如果 `Rectangle.setWidth` 的后置条件只说「`w` 变成 `neww`」，不说「`h` 不变」，那么 `Square` 覆写时同时改 `h` 就合法了。但这样 `Rectangle` 的规格就**太弱**（客户端无法依赖「只改宽度」），失去了 `setWidth` 的意义。

方案 2 是最优雅的：**不可变性让「协变返回」成为可能**——`Square.withWidth(5)` 返回 `Rectangle`，客户端按 `Rectangle` 用，没问题。这也解释了为什么第 6 讲强调不可变性的好处：**它消除了大量子类型问题**。

### 5.10 形式化分析的总结与局限

幻灯片第 17 页（最后一页）：

> **Formal Analysis Summary**
> - **Specification between textual and formal specifications**
> - **Proving (e.g. with Dafny) vs. Testing**
> - **Class Invariants and Behavioral Subtyping**
> - **Tools such as Dafny can make proofs more practical**
>   - **Reduces effort relative to proof by hand**
>   - **Still considerable work in writing specifications and invariants**
> - **Can be useful in documenting code and finding errors**
> - **The current tool may miss some defects**

这一页很诚实，值得逐条读：

**（1）「Specification between textual and formal specifications」**

规格有一个**光谱**：

```
纯文字注释  →  半形式（JML 注释）  →  完全形式（Dafny）
（人能读，机器不懂）              （机器能检查）
```

15-214 教的是**整个光谱**：第 8 讲的 Javadoc 与 JML 注释、第 21 页的 `assert`、本讲的 Dafny。选择哪一点取决于**成本收益**：

- 文字注释：成本低，但可能过时、有歧义、无法检查；
- 完全形式：可检查，但写起来贵，且需要专门的语言/工具。

**（2）「Reduces effort relative to proof by hand」**

Dafny 相比手工证明的**巨大**优势：你只写规格和不变式，**证明搜索是自动的**。手工证明（比如用 Coq、Isabelle）需要写证明脚本，工作量可能是代码的 10 倍。Dafny 把这个降到 2–3 倍。

**（3）「Still considerable work in writing specifications and invariants」**

但**写规格本身**仍然很贵。这是形式化方法的核心成本，而且**无法自动化**——规格是「程序应该做什么」的表达，这是人的工作。

而且规格写错了，验证器**不会告诉你**——它会「成功地」证明你的实现满足一个**错误的规格**。这是形式化方法最危险的地方：**它给你一种虚假的安全感**。

**（4）「Can be useful in documenting code and finding errors」**

即使不追求完全验证，写规格也有**文档价值**（比文字注释精确）和**找 bug 价值**（验证失败往往指向真实的实现错误，或者规格错误——两者都值得查）。

**（5）「The current tool may miss some defects」**

这一条最诚实。Dafny 不能保证「没有 bug」，因为：

- **规格可能不完整**（漏掉了某些应该保证的性质）；
- **验证器可能有 bug**（虽然罕见）；
- **环境假设可能不成立**（比如假定内存足够、硬件正确）；
- **抽象边界**：Dafny 验证的是**源程序**，编译后的机器码可能有 bug（编译器 bug、运行时 bug）。

**这与第 8 讲对覆盖率的结论同构**：

> 覆盖率不是好的充分性判据，应用它找出测试不充分之处。

同理：**「验证通过」不是「程序正确」的证明，而是「程序相对于规格正确」的证明**。而规格是否捕捉了真实需求，是**另一个**问题（而且是更难的问题——它属于需求工程，15-313 的范畴）。

第 8 讲第 6 页的功能性正确全景图在这里又浮现出来：

| 手段 | 课程 |
|---|---|
| Specification / Unit Testing / Type Checking | **15-214** |
| Formal Verification / Static Analysis / Requirements definition / Inspections / Integration Testing / Change Management | 15-313 |

**形式化验证只是「正确性」这个巨大拼图中的一块**。这一讲介绍它，是为了让你知道它**能做什么**、**不能做什么**、**什么时候值得用**。

## 6. 代码示例

### 6.1 官方课程代码

出自 `formal-analysis-part2.pdf` 第 4 页（`SimpleSet` 的类不变式）：

```dafny
class SimpleSet {
  var contents:array<int>;
  var size:int;

  function valid() : bool
    reads this, contents;
  {size >= 0
   && contents != null
   && contents.Length >= size }
```

出自第 5 页（构造函数 `init`）：

```dafny
method init(capacity:int)
  requires capacity >=0;
  modifies this;
  ensures valid();
  ensures size == 0;
  ensures contents.Length == capacity;
  ensures fresh(contents);
{
  contents := new int[capacity];
  size := 0;
}
```

出自第 6 页（方法 `add` 的规格）：

```dafny
method add(i:int)
  requires valid();
  requires size < contents.Length || i in mset();
  modifies this, contents;
  ensures valid();
  ensures mset() == old(mset()) + {i};
  ensures contents == old(contents);
  ensures i in old(mset()) ==> size == old(size);
  ensures !(i in old(mset())) ==> size == old(size)+1;
{ … }
```

出自第 7 页（抽象函数 `mset`）：

```dafny
function mset() : set<int>
  reads this, contents;
  requires valid();
{
  set j:int | 0 <= j < size :: contents[j]
}
```

出自第 8 页（`contains` 与循环不变式）：

```dafny
method contains(i:int) returns (b: bool)
  requires valid();
  ensures b <==> i in mset();
{
  var j := 0;
  while (j < size)
    invariant 0 <= j <= size;
    invariant !(i in set k:int | 0 <= k < j :: contents[k]);
    decreases size - j;
  {
    if (contents[j] == i) { return true; }
    j := j + 1;
  }
  return false;
}
```

出自第 10 页（`Vehicle` / `Car`，合法行为子类型）：

```java
abstract class Vehicle {
  int speed, limit;
  //@ invariant speed < limit;
  //@ requires speed != 0;
  //@ ensures |speed| < |\old{speed}|
  void break();
}

class Car extends Vehicle {
  int fuel;
  boolean engineOn;
  //@ invariant fuel >= 0;
  //@ requires fuel > 0 && ! engineOn;
  //@ ensures engineOn;
  void start() { … }
  void accelerate() { … }
  //@ requires speed != 0;
  //@ ensures |speed| < |\old{speed}|
  void break() { … }
}
```

出自第 11 页（`Hybrid`，前置更弱 + 后置更强）：

```java
class Hybrid extends Car {
  int charge;
  //@ invariant charge >= 0;
  //@ requires (charge > 0 || fuel > 0)
               && ! engineOn;
  //@ ensures engineOn;
  void start() { … }
  void accelerate() { … }
  //@ requires speed != 0;
  //@ ensures |speed| < |\old{speed}|
  //@ ensures charge > \old{charge}
  void break() { … }
}
```

出自第 12–15 页（`Rectangle` / `Square` 反例，逐步加料）：

```java
class Rectangle {
  //@ invariant h>0 && w>0;
  int h, w;
  Rectangle(int h, int w) {
    this.h=h; this.w=w;
  }
  void scale(int factor) {
    w=w*factor;
    h=h*factor;
  }
  void setWidth(int neww) {
    w=neww;
  }
}

class Square extends Rectangle {
  //@ invariant h==w;
  Square(int w) {
    super(w, w);
  }
}
```

出自配套讲义笔记 `90-原始PDF/15-214/notes/formal-analysis-notes.txt`（`Max` 的规格与实现）：

```dafny
method Max(a: int, b:int) returns (c: int)
  ensures (c == a || c == b) && c >= a && c >= b;
{
  if (a > b)
    { return a; }
  else
    { return b; }
}
```

出自同一份笔记（`FindMax` 的 ∀+∃ 规格与循环不变式）：

```dafny
method FindMax(a: array<int>) returns (m: int)
   requires a != null && a.Length >= 1;
   ensures forall k :: 0 <= k < a.Length ==> m >= a[k];
   ensures exists k :: 0 <= k < a.Length && m == a[k];
{
   m := a[0];
   var index := 1;
   while (index < a.Length)
      invariant 0 <= index <= a.Length;
      invariant forall k :: 0 <= k < index ==> m >= a[k];
      invariant exists k :: 0 <= k < index && m == a[k];
      decreases a.Length - index;
   {
      m := Max(m, a[index]);
      index := index + 1;
   }
}
```

出自同一份笔记（`fib` 数学定义与 `ComputeFib` 高效实现）：

```dafny
function fib(n: nat): nat
  decreases n;
{
    if n == 0 then 0 else
    if n == 1 then 1 else
                   fib(n - 1) + fib(n - 2)
}

method ComputeFib(n: nat) returns (b: nat)
   ensures b == fib(n);
{
   if (n == 0) { return 0; }
   var i: int := 1;
   var a := 0;
       b := 1;
   while (i < n)
      invariant 0 < i <= n;
      invariant a == fib(i - 1);
      invariant b == fib(i);
   {
      a, b := b, a + b;
      i := i + 1;
   }
}
```

出自同一份笔记（`Ack` 的字典序终止度量）：

```dafny
function Ack(m: nat, n: nat): nat
   decreases m, n;
{
   if m == 0 then n + 1
   else if n == 0 then Ack(m - 1, 1)
   else Ack(m - 1, Ack(m, n - 1))
}
```

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：用 JML 风格的注释表达契约（Java，无验证器）**

```java
public final class BoundedCounter {
    private int value;
    private final int limit;

    //@ public invariant 0 <= value && value <= limit;

    //@ requires limit > 0;
    //@ ensures value == 0 && this.limit == limit;
    public BoundedCounter(int limit) {
        if (limit <= 0) throw new IllegalArgumentException("limit must be > 0");
        this.limit = limit;
        this.value = 0;
    }

    //@ requires value < limit;
    //@ ensures value == \old(value) + 1;
    public void increment() {
        if (value >= limit) throw new IllegalStateException("at limit");
        value++;
    }

    //@ ensures \result == value;
    public /*@ pure @*/ int value() { return value; }
}
```

三点说明：

1. **注释不是装饰**。`//@ requires value < limit;` 明确告诉调用者「满了再调 `increment` 是你的 bug」——所以实现里抛 `IllegalStateException`（而非静默忽略）是合理的。
2. **类不变式只写一次**，但按 5.2 节的规则，它应当出现在三处（构造函数后置、其他方法前置、修改方法后置）。JML 工具会自动展开这三处——这是形式化工具的价值：**你写一次，工具展开到所有需要的地方**。
3. **`pure`** 表示方法无副作用（不改状态、不抛异常），这样它才能用在**其他规格**里（比如 `ensures \result == value` 中的 `value()`）。

**示例 B：用 `assert` 在 Java 里做「穷人版不变式检查」**

```java
public final class Interval {
    private final int lo, hi;

    public Interval(int lo, int hi) {
        this.lo = lo;
        this.hi = hi;
        checkInvariant();                 // 构造后检查
    }

    public Interval union(Interval other) {
        checkInvariant();                 // 方法入口假定不变式成立
        Interval r = new Interval(Math.min(lo, other.lo), Math.max(hi, other.hi));
        r.checkInvariant();               // 返回前确保不变式
        return r;
    }

    private void checkInvariant() {
        assert lo <= hi : "lo=" + lo + " > hi=" + hi;
    }

    public static void main(String[] args) {
        Interval a = new Interval(1, 5);
        Interval b = new Interval(3, 9);
        assert a.union(b).lo == 1;
        System.out.println("ok");
    }
}
```

运行需要 `java -ea Main`（`-ea` = enable assertions）。若不开启，`assert` 语句被**完全跳过**，零开销。

这就是 5.2 节「不变式要写在三处」的手工版本——但注意它只能检查**当前状态**，无法检查「所有可能的执行」。`assert` 是**动态**检查（运行时），Dafny 是**静态**验证（编译时）。前者是后者的**极弱近似**，但成本几乎为零，所以非常实用。

**示例 C：`Rectangle` / `Square` 的三种修复方案**

```java
// 方案 1：不继承，各自实现只读接口
interface Shape { int area(); }

final class Rectangle implements Shape {
    private final int h, w;
    Rectangle(int h, int w) { this.h = h; this.w = w; }
    public int area() { return h * w; }
    Rectangle withWidth(int nw) { return new Rectangle(h, nw); }
}

final class Square implements Shape {
    private final int side;
    Square(int side) { this.side = side; }
    public int area() { return side * side; }
    Square withSide(int ns) { return new Square(ns); }
}
// ✓ 没有子类型关系，就没有行为子类型问题

// 方案 2：不可变 + 协变返回
class Rectangle2 {
    protected final int h, w;
    Rectangle2(int h, int w) { this.h = h; this.w = w; }
    Rectangle2 withWidth(int nw) { return new Rectangle2(h, nw); }  // 注意：返回 Rectangle2
}

final class Square2 extends Rectangle2 {
    Square2(int side) { super(side, side); }
    @Override Square2 withWidth(int nw) { return new Square2(nw); }  // 协变返回，且仍满足「h==w」
}
// ✓ 返回新对象，所以可以同时满足「w 变成 nw」与「h == w」

// 方案 3：可变但契约写弱（不推荐）
class Rectangle3 {
    protected int h, w;
    // 后置条件只说「w == nw」，不说「h 不变」
    void setWidth(int nw) { w = nw; }
}
class Square3 extends Rectangle3 {
    @Override void setWidth(int nw) { w = nw; h = nw; }   // 满足弱契约，但客户端失去「只改宽」的保证
}
// △ 合法但契约太弱，setWidth 的意义被削弱
```

方案 2 是**最优雅**的：不可变性让「返回新对象」成为可能，从而让子类可以自由地维护自己的不变式。这也解释了为什么第 6 讲强调不可变性的好处——**它消除了一大类子类型问题**。

**示例 D：用 Dafny 风格的规格描述「栈」**

```java
// 规格（文字化的 Dafny 风格）
// class Stack<T> {
//   ghost var contents: seq<T>;     // 抽象值：一个序列
//
//   predicate valid()
//     reads this;
//   { size() == |contents| }
//
//   method push(x: T)
//     modifies this;
//     ensures contents == old(contents) + [x];
//
//   method pop() returns (x: T)
//     requires contents != [];
//     modifies this;
//     ensures contents == old(contents)[..|old(contents)|-1];
//     ensures x == old(contents)[|old(contents)|-1];
//
//   method peek() returns (x: T)
//     requires contents != [];
//     reads this;
//     ensures x == contents[|contents|-1];
//     ensures contents == old(contents);     // 不改变状态
// }

public final class IntStack {
    private int[] data = new int[8];
    private int size = 0;

    public void push(int x) {
        if (size == data.length) {
            int[] bigger = new int[data.length * 2];
            System.arraycopy(data, 0, bigger, 0, size);
            data = bigger;
        }
        data[size++] = x;
    }

    public int pop() {
        if (size == 0) throw new java.util.EmptyStackException();
        return data[--size];
    }

    public int peek() {
        if (size == 0) throw new java.util.EmptyStackException();
        return data[size - 1];
    }

    public int size() { return size; }
}
```

`peek` 的规格有两条后置条件：`\result == contents[|contents|-1]`（返回栈顶）**且** `contents == \old(contents)`（**不改状态**）。第二条常被忘记——但它正是「`peek` 与 `pop` 的区别」。

这就是形式化规格的价值：**它迫使你把「直觉上显然」的性质写下来**。写下来之后，你才发现「`peek` 不改状态」这条其实很重要（如果实现里不小心写了 `data[--size]` 就破坏了它）。

**示例 E：一个真实的「规格写错」场景**

```java
// 意图：返回数组中第一个 >= 0 的元素的下标，没有则返回 -1
// 规格（错误的版本）：
//   ensures \result >= -1;
//   ensures \result < a.length;
//   ensures \result == -1 || a[\result] >= 0;
//
// 问题：这个规格允许「返回任意一个 >= 0 的元素下标」，而不是「第一个」。
//       例如 a = {5, 3}，返回 1 也满足规格（a[1] == 3 >= 0），但它不是第一个。
// 正确的规格：
//   ensures \result == -1 ==>
//       (\forall int i; 0 <= i && i < a.length; a[i] < 0);
//   ensures 0 <= \result && \result < a.length ==>
//       (a[\result] >= 0 &&
//        (\forall int i; 0 <= i && i < \result; a[i] < 0));
```

这个例子说明 5.10 节第（3）条批注的严重性：**验证器不会告诉你规格写错了**。上面那个错误规格，验证器会「成功地」证明一个**错误的**实现（返回最后一个匹配元素）满足它。

**规格的正确性无法被自动验证**——它只能靠人的审查、靠测试的反向检查（用测试去「攻击」规格）、靠与其他规格的一致性检查。这是形式化方法**根本的**局限。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| **Validation（验证）** | **Verification（证成）** | 前者靠**执行**、覆盖**一次**执行、只能查**可观察性质**；后者靠**推导**、覆盖**所有**执行、可查**任意性质**。课件第 3 页的对照表 |
| **测试** | **证明** | 测试是**抽样**（有限输入），证明是**全称**（∀ 输入）。Dijkstra：「测试只能表明缺陷的存在，不能表明缺陷的不存在」 |
| **`requires`（前置）** | **`ensures`（后置）** | 前者是**调用者**的责任（调用前必须成立）；后者是**实现者**的责任（返回时必须成立）。第 5 讲的契约式设计 |
| **`requires`（前置条件）** | **`invariant`（类不变式）** | 前者只在**方法入口**成立；后者在**所有可观察时刻**成立（构造后、方法前后）。不变式要显式写三处 |
| **类不变式** | **循环不变式** | 前者描述**对象状态**的恒定性质；后者描述**循环进度**的恒定性质（循环前为真 + 每次迭代保持）。两者的证明结构相同（基础 + 归纳） |
| **`invariant`（不变式）** | **`decreases`（终止度量）** | 前者保证**正确性**（性质保持）；后者保证**终止性**（度量递减且有下界）。两者缺一不可：没有终止性，正确性无意义 |
| **`modifies`（框架条件）** | **`reads`（读集合）** | 前者声明方法**可能写**哪些对象（写框架）；后者声明函数**依赖**哪些对象的字段（读框架）。都是「让验证器知道什么没变」 |
| **`old(e)`** | **`e`** | 前者是**方法入口**时 `e` 的值；后者是**当前位置**的 `e`。后置条件里比较前后状态必须用 `old` |
| **`fresh(x)`** | **`x != null`** | 前者是「`x` 是**新分配**的，不与任何已存在对象别名」；后者只保证非空。`fresh` 是**防表示暴露**的形式化 |
| **`function`（Dafny）** | **`method`（Dafny）** | 前者是**纯**的（无副作用、可出现在规格里、不能有循环）；后者可有副作用（需 `modifies`）。`mset()`、`valid()` 是 function，`add()`、`init()` 是 method |
| **规格（specification）** | **实现（implementation）** | 前者说「做什么」，后者说「怎么做」。验证器证明「实现满足规格」，调用者只依赖规格（**模块化验证**） |
| **抽象值 `mset()`** | **表示 `contents` + `size`** | 前者是数学集合（客户端看到的）；后者是数组与长度（被隐藏的）。`mset()` 是**抽象函数**，把表示映射到抽象值 |
| **行为子类型** | **语法子类型** | 前者要求**契约兼容**（不变式不弱、后置不弱、前置不强）；后者只要求 `extends` 合法。`Square extends Rectangle` 语法合法但行为非法（有 `setWidth` 时） |
| **前置条件更强** | **前置条件更弱** | 更强 = 要求更多 = **非法**（子类）；更弱 = 要求更少 = **合法**。记忆：「子类只能要求更少」 |
| **后置条件更强** | **后置条件更弱** | 更强 = 承诺更多 = **合法**（子类）；更弱 = 承诺更少 = **非法**。记忆：「子类只能承诺更多」 |
| **`Car.start` 前置 `fuel > 0`** | **`Hybrid.start` 前置 `charge > 0 \|\| fuel > 0`** | 后者**更弱**（电也能启动）→ **合法**的行为子类型。第 11 页的例子 |
| **`Car.break` 后置 `\|speed\| < \|\old{speed}\|`** | **`Hybrid.break` 同前 + `charge > \old{charge}`** | 后者**更强**（还保证充电）→ **合法**。第 11 页的例子 |
| **`Rectangle.scale`** | **`Rectangle.setWidth`** | 前者同时改 `h` 和 `w`（`Square` 的不变式 `h==w` 仍成立）；后者只改 `w`（**破坏** `Square` 的不变式）。所以 `setWidth` 是矛盾所在 |
| **Dafny 有继承** | **Dafny 无继承** | 讲义笔记明确：「no inheritance (leaving out inheritance inhibits reuse in some cases, but **simplifies verification substantially**)」。去掉继承就绕开了行为子类型的难题 |
| **Dafny 自动证明** | **Coq/Isabelle 手工证明** | 前者只写规格与不变式，**证明搜索自动**；后者要写证明脚本。Dafny 的工作量约 2–3 倍代码，手工证明可能 10 倍 |
| **「验证通过」** | **「程序正确」** | 前者只意味着「程序**相对于规格**正确」。规格本身可能不完整或错误——而**规格的正确性无法自动验证** |
| **形式化验证** | **静态分析** | 前者是**健全**的（sound：说「通过」就一定对，但可能证不出来）；后者常**不健全**（可能有漏报/误报），但**全自动**且快。课件：「static analysis tools… are just simple, automated theorem provers」 |
| **`assert`（Java）** | **`ensures`（Dafny）** | 前者是**运行时**检查（`-ea` 开启，只查当前执行）；后者是**编译时**验证（查所有执行）。`assert` 是「穷人版」不变式 |

## 8. 对应原版讲义

- PDF 相对路径：`90-原始PDF/15-214/slides/formal-analysis-part2.pdf`
- 总页数：17 页（页内编号 7–22，说明这是某个更长讲义的第二部分；第一部分未随公开页面发布）
- 配套讲义笔记：`90-原始PDF/15-214/notes/formal-analysis-notes.txt`（纯文本，含 `Max` / `FindMax` / `ComputeFib` / `Ack` / `SimpleSet` 的完整 Dafny 代码与解答）
- 重点页码（按 PDF 页码）：
  - 第 1 页：封面（"© 2012-2013 W Scherlis, J Aldrich, C Garrod, and C Kästner"，标题 "Formal Analysis of Software Artifacts"，署名 Jonathan Aldrich、Charlie Garrod）
  - 第 2 页（页内 7）：**回到测试**——Piazza 提问「如何自动测试随机瓦片下玩家走对棋？」答案：**为测试而设计**（提供设置随机种子的方法；真实运行时用时间做种子）
  - 第 3 页（页内 8）：**测试 vs 证明**对照表 + 「为什么学证明」四条理由（教人思考正确性 / 对开发与审查与断言有用 / 静态分析工具的基础 / 很多已经实用）
  - 第 4 页（页内 9）：`SimpleSet` 的类不变式 `valid()` + `reads` 子句 + **不变式必须显式写三处**
  - 第 5 页（页内 10）：构造函数 `init` + `modifies this` + **`fresh(contents)` 防别名（表示暴露）**
  - 第 6 页（页内 11）：方法 `add` 的完整规格（`old(mset())`、`old(contents)`、分情形 `size`）
  - 第 7 页（页内 12）：抽象函数 `mset()`（集合推导式）
  - 第 8 页（页内 13）：`contains` + 两条循环不变式 + `decreases size - j`
  - 第 9 页（页内 14）：**行为子类型 / 里氏替换原则**——类型层四条 + 行为层三条（不变式不弱、后置不弱、前置不强）+ Liskov 原话
  - 第 10 页（页内 15）：`Vehicle` / `Car`——合法的行为子类型（不变式相同 + 新增，`break` 前后置相同）
  - 第 11 页（页内 16）：`Hybrid`——`start` **前置更弱**（合法）、`break` **后置更强**（合法）
  - 第 12 页（页内 17）：`Rectangle` / `Square` 第一版（无不变式、无方法）——「Is `Square` a behavior subtype of `Rectangle`?」
  - 第 13 页（页内 18）：加入不变式（`h>0 && w>0` vs `h==w`）
  - 第 14 页（页内 19）：加入 `scale`——不破坏 `Square` 的不变式
  - 第 15 页（页内 20）：加入 `setWidth`——矛盾出现
  - 第 16 页（页内 21）：**结论：`Square` 不是 `Rectangle` 的行为子类型**（`setWidth` 使子类更强的不变式 `w==h` 失效）
  - 第 17 页（页内 22）：**形式化分析总结**（规格光谱、证明 vs 测试、不变式与行为子类型、工具的价值与局限）
- 原始网页链接：`https://www.cs.cmu.edu/~aldrich/214/slides/formal-analysis-part2.pdf`
- 配套笔记原始路径：`https://www.cs.cmu.edu/~aldrich/214/notes/formal-analysis-notes.txt`（推测；讲义笔记文件头未给 URL，只给了 Dafny 的两个外链）

> 待核实：本讲义文件名含 `part2`，页内编号从 7 开始，说明存在 `formal-analysis-part1`（页内 1–6），但**公开页面上未找到**该文件——可能未发布或已下线。讲义笔记中提到的 `SimpleSet-orig.dfy`、`SimpleSet-soln1.dfy`、`SimpleSet-soln2.dfy` 三个 Dafny 源文件也**未随公开材料发布**。第 17 页 "formal specifictions" 拼写错误（应为 "specifications"）。第 10–11 页 `break()` 的后置条件 `|speed| < |\old{speed}|` 使用了绝对值——这暗示速度可以为负（倒车），是一个值得注意的规格细节。第 12–13 页的 `Square` 不变式 `h==w` **并不蕴含**父类的 `h>0 && w>0`（若 `w<=0` 则 `h==w` 成立但不满足 `h>0`），课件未指出这一点，属笔记补充观察。

## 9. 对应视频

未找到官方公开录像。2013 年秋季的 15-214 课堂没有公开发布录像，故不提供链接与时间戳。

## 10. 本节复习

- **测试 vs 证明**：测试覆盖**一次**执行、只能查**可观察性质**、**目前最实用**；证明覆盖**所有**执行、可查**任意性质**、小程序实用。
- **为什么学证明**：教人思考正确性、对开发/审查/运行时断言有用、是静态分析工具的基础、很多形式化方法已经实用（类型检查就是）。
- **Dafny**：命令式 + 基于对象 + **无继承**（去掉继承大幅简化验证）+ 内建规格构造。
- **规格关键字**：`requires`（前置，调用者责任）、`ensures`（后置，实现者责任）、`modifies`（写框架）、`reads`（读框架）、`invariant`（不变式）、`decreases`（终止度量）、`old()`（入口值）、`fresh()`（新分配、无别名）。
- **类不变式必须显式写三处**：构造函数后置、其他方法前置、修改 `this` 的方法后置。构成「基础 + 归纳」结构。
- **`fresh(contents)`** = 防表示暴露的形式化：若数组与外部别名，外部写入会破坏不变式。这是第 6 讲「防御性拷贝」的可检查版本。
- **抽象函数 `mset()`**：把表示（数组 + 长度）映射到抽象值（数学集合），让规格可以**只谈抽象值**，不提实现细节。
- **循环不变式设计技巧**：让不变式 = 后置条件，把「数组长度」换成「当前索引」。循环退出时自动变成后置条件。
- **`decreases`**：每次迭代严格递减且下界为 0 → 必然终止。Dafny 会**自动推断**简单情形。
- **模块化验证**：验证器验证调用者时**只看规格、不看方法体**。所以必须先写规格，否则断言无法证明。这与信息隐藏同构。
- **∀ + ∃ 的规格模式**：`FindMax` 用「`m >= 所有元素`（上界）+ `m == 某个元素`（可达）」唯一确定最大值。∀ 保证不漏，∃ 保证不虚。
- **数学函数作规格**：`fib` 是清晰的数学定义（低效），`ComputeFib` 是高效实现，证明两者等价。这是形式化方法最典型的用法。
- **行为子类型三条规则**：不变式**不弱**、后置条件**不弱**、前置条件**不强**。记忆：「子类只能要求更少、承诺更多」。
- **为什么方向如此**：客户端按父类契约编程。子类前置更强 → 客户端调用可能不满足；子类后置更弱 → 客户端依赖可能失效。
- **`Vehicle`/`Car`/`Hybrid`**：`Car.break` 前后置与父类相同（合法）；`Hybrid.start` 前置**更弱**（合法）；`Hybrid.break` 后置**更强**（合法）。
- **`Rectangle`/`Square`**：`scale` 不破坏 `Square` 的不变式（同时缩放）；`setWidth` 破坏（只改宽）。所以有 `setWidth` 时 `Square` **不是**行为子类型。
- **`Square` 的两难**：不改 `h` → 破坏自己的不变式；改 `h` → 违反父类后置条件（`h` 不变）。两条路都非法。
- **修复方案**：不继承（各自实现接口）/ 不可变 + 协变返回（`withWidth` 返回新对象）/ 弱化父类契约（不推荐）。不可变性最优雅。
- **形式化工具的局限**：写规格仍很贵；**规格写错时验证器不会告诉你**（会「成功」证明错误规格）；工具本身可能漏缺陷；「验证通过」≠「程序正确」。
- **与覆盖率的同构**：覆盖率不是充分性判据，应用它找测试不足；「验证通过」不是正确性证明，只是「相对于规格正确」。

## 11. 自我检查

1. 课件第 3 页说「Proofs tell us how to think about program correctness」。请举两个**不使用任何形式化工具**、但体现了「证明式思维」的日常开发实践，并说明它们各自对应本讲的哪个概念。

2. `SimpleSet` 的类不变式 `valid()` 必须显式出现在三个位置。请指出这三个位置，并解释如果**漏掉**其中任意一个，验证器会得出什么**错误结论**（分别说明）。

3. 下面的子类是否合法（行为子类型）？请逐条检查不变式、前置条件、后置条件，并说明理由。
   ```java
   class Account {
     //@ invariant balance >= 0;
     //@ requires amount > 0 && amount <= balance;
     //@ ensures balance == \old(balance) - amount;
     void withdraw(int amount) { … }
   }
   class OverdraftAccount extends Account {
     //@ invariant balance >= -1000;
     //@ requires amount > 0;
     //@ ensures balance == \old(balance) - amount;
     void withdraw(int amount) { … }
   }
   ```

4. 为什么 `Square` 在**没有** `setWidth` 时可以是 `Rectangle` 的行为子类型，而**加上** `setWidth` 之后就不行？请说明 `setWidth` 造成的两难，并给出一种修复方案。

5. 课件最后一页说「The current tool may miss some defects」。请举出至少三种「Dafny 验证通过但程序仍然有问题」的情形，并说明哪一种是最危险的。

<details>
<summary>参考答案</summary>

1. **实践一：写 Javadoc 的前置/后置条件。** 当你为一个方法写「`@param` 必须非空」「`@return` 保证返回非负」时，你实际上在写一个**契约**：调用者负责满足前置，实现者负责建立后置。这直接对应本讲的 `requires` / `ensures`——只是用自然语言而非逻辑公式。它的价值不在于「能被检查」，而在于**迫使你想清楚「这个方法对调用者承诺什么」**，从而发现「这个承诺其实不成立」之类的设计问题。
   **实践二：在 code review 中说「这个调用违反了前置条件」。** 你在做一次**非形式的证明**：从「调用点处 `x` 可能为 null」推出「被调方法的 `@param` 要求非空」→ 推出「这里会抛 NPE」。这个推理链正是验证器做的事（只是它用逻辑、你用直觉）。
   **第三个可选的例子：写 `assert`。** 每个 `assert` 是一个**局部定理**：你声称「此处这个性质成立」，运行时不成立就崩。这对应本讲的 `invariant`（尤其是循环不变式——很多人在循环里写 `assert` 来检查进度）。
   这三个例子共同说明课件的观点：**证明思维不需要工具就能用**，工具只是把它自动化、规模化。

2. **三个位置**：
   - **构造函数（`init`）的后置条件**（`ensures valid();`）
   - **普通方法的前置条件**（`requires valid();`）
   - **修改 `this` 的方法的后置条件**（`ensures valid();`）
   **漏掉构造函数后置条件**：验证器无法知道「新建的对象是有效的」。于是后续任何依赖 `valid()` 的推理都**无法进行**——不是得出错误结论，而是**证不出任何东西**（验证失败）。更糟的是，如果别处写了 `requires valid()`，验证器会认为「调用者必须证明 `valid()`」，而新建对象时无法证明 → 构造函数的所有调用点都报错。
   **漏掉普通方法的前置条件**：验证器会认为「对象可能是任意状态」——包括 `size < 0` 或 `contents == null`。于是方法体内任何依赖「`size >= 0`」的推理（比如数组下标 `contents[j]` 在界内）都**无法证明**。这会导致大量**假报警**（false positive），让验证无法完成。注意这里的危险方向：漏掉前置条件不会让你「证出错的」，而是让你「什么都证不出」。
   **漏掉修改方法的后置条件**：这是**最危险**的。验证器会认为方法返回后 `valid()` **不一定成立**，于是**调用者**在调用 `add` 之后无法继续依赖不变式——同样导致后续验证失败。但如果某个调用者**没有**检查（比如它自己在方法开头也没写 `requires valid()`），那么验证器可能**默认**「什么都没变」，从而**证出错误的结论**——这就是**不健全（unsound）** 的风险。
   一句话总结：**漏掉不变式的声明，要么让验证无法完成（假报警），要么让验证得出错误结论（漏报）**。前者烦人，后者危险。

3. **逐条检查**：
   - **不变式**：父 `balance >= 0`；子 `balance >= -1000`。子的不变式**更弱**（允许负余额）→ **违反规则**（要求「相同或更强」）。✗
   - **前置条件**：父 `amount > 0 && amount <= balance`；子 `amount > 0`。子**更弱**（去掉了 `amount <= balance`）→ **合法**。✓
   - **后置条件**：两者相同（`balance == \old{balance} - amount`）→ **合法**（相同即满足「不弱」）。✓
   **结论：不合法**，因为不变式变弱了。
   **为什么不变式变弱是致命的**：客户端持有 `Account` 引用，可能写：
   ```java
   // 客户端代码，依赖 Account 的不变式 balance >= 0
   int fee = account.balance() / 10;    // 若 balance 可能为负，这段逻辑（或后续）会出错
   if (account.balance() >= 100) { … }  // 客户端假定「非负」，负余额会让分支逻辑失效
   ```
   换成 `OverdraftAccount` 后，`balance` 可能为 `-500`，客户端的所有「非负」假设都失效。
   **如何修复**：让 `OverdraftAccount` **不继承** `Account`，而是两者都实现一个更抽象的接口（比如 `interface BalanceHolder { int balance(); }`），或者引入 `limit` 概念让 `Account` 本身支持透支（不变式改成 `balance >= -limit`，`limit >= 0`）。**后一种更好**：它把「透支额度」变成 `Account` 的**参数**，而不是用继承去特化——这正是第 3 讲「优先组合而非继承」的思想。
   （补充：`withdraw` 的前置从 `amount <= balance` 弱化为 `amount > 0`，这在**孤立看**是合法的；但配合「不变式变弱」，整体仍然非法。这说明**行为子类型要整体检查，不能逐条孤立判断**。）

4. **没有 `setWidth` 时合法**：此时 `Rectangle` 的方法只有 `scale(int factor)`，它同时把 `h` 和 `w` 乘以 `factor`。对 `Square` 来说，`h == w` 在缩放后**仍然成立**（`h*factor == w*factor`）。所以：
   - 不变式：`Square` 的 `h == w` 比父类的 `h > 0 && w > 0` **更强**（在 `w > 0` 的前提下）✓
   - `scale` 的前置：无（或相同）✓
   - `scale` 的后置：父类保证「`h`、`w` 都乘以 `factor`」，`Square` 继承同一实现，后置相同 ✓
   所以 `Square` 是合法的行为子类型。
   **加上 `setWidth` 后的两难**：`Rectangle` 的契约（由客户端依赖）是「`setWidth(n)` 之后 `w == n`，且 `h` **不变**」。`Square` 有不变式 `h == w`。
   - **选择 A：`Square` 不覆写 `setWidth`**（继承父类实现，只改 `w`）。那么 `setWidth(5)` 之后 `w = 5` 但 `h` 还是旧值 → **`h != w`** → **破坏 `Square` 自己的不变式**。这违反「子类不变式必须成立」的规则。✗
   - **选择 B：`Square` 覆写 `setWidth`，同时改 `h` 和 `w`**。那么 `setWidth(5)` 之后 `h = w = 5`，`Square` 的不变式成立 ✓，但**违反了父类的后置条件**（「`h` 不变」）→ 客户端依赖的性质失效。✗
   **两条路都不通** → `Square` 不可能是 `Rectangle` 的行为子类型。
   **修复方案（推荐：不可变 + 协变返回）**：
   ```java
   class Rectangle {
       protected final int h, w;
       Rectangle(int h, int w) { this.h = h; this.w = w; }
       Rectangle withWidth(int nw) { return new Rectangle(h, nw); }   // 返回新对象
   }
   class Square extends Rectangle {
       Square(int side) { super(side, side); }
       @Override Square withWidth(int nw) { return new Square(nw); }  // 协变返回
   }
   ```
   关键：`withWidth` **不修改** `this`，而是**返回新对象**。所以 `Square.withWidth(5)` 返回一个**新的 `Square`**（边长 5），既满足「宽度变成 5」又满足「`h == w`」。而 `Rectangle.withWidth(5)` 返回一个新 `Rectangle`（`h` 不变）——两者都满足各自的契约。
   这个方案的深层原因：**不可变性消除了「修改」带来的契约冲突**。可变对象的每个 mutator 都是对「所有子类不变式」的潜在威胁；不可变对象没有 mutator，就没有这个威胁。这就是第 6 讲强调不可变性的一个具体回报。

5. **三种情形**：
   - **（a）规格不完整**：规格只写了「返回最大值」，没写「不修改输入数组」。实现里悄悄排了序（原地修改），验证通过，但客户端依赖「输入不变」的代码出错。
   - **（b）规格写错**：比如 6.2 节示例 E 的「返回第一个 `>= 0` 的元素下标」写成了「返回任意一个 `>= 0` 的元素下标」。验证器会「成功地」证明一个返回最后一个匹配元素的实现满足规格——但这不是需求。
   - **（c）环境假设不成立**：Dafny 验证的是**源程序**的语义，假定「内存无限」「整数是数学整数（无溢出）」「编译器正确」。实际上 `array<int>` 会耗尽内存、`int` 可能溢出（取决于目标语言）、编译器可能有 bug。
   - **（d）抽象边界的漏洞**：如果程序调用外部库（未验证的代码），Dafny 只能按你写的**外部规格**信任它。规格若与库的实际行为不符，验证就失效。
   - **（e）并发**：Dafny（2013 年版本）主要针对**顺序程序**。多线程程序的验证需要额外的并发推理规则（如 rely-guarantee），不在本讲范围内。
   **最危险的是（b）规格写错**。理由：
   - （a）规格不完整至少「验证过的那部分是对的」，而且不完整往往能被测试或审查发现；
   - （c）（d）是**已知的、可管理的**边界，工程上会用测试兜底；
   - （b）则是**虚假的安全感**——你花了大量精力写规格、跑验证、看到「全部通过」的绿勾，于是**不再写测试、不再审查**，而 bug 恰好就在规格漏掉或写错的地方。这种「因为验证通过所以放心」的心态，比没有验证更危险。
   课件第 17 页把这条放在最后一句，正是要提醒：**形式化方法验证的是「实现 vs 规格」，而「规格 vs 需求」永远需要人来保证**。这也回到第 8 讲的结论：没有单一手段能保证正确性，必须组合使用（测试 + 审查 + 类型检查 + 形式化 + 静态分析）。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-14-Java-Collections]]（注：按 2013 年课表，10 月 15 日为 Midterm，10 月 17 日为本讲）
- 下一讲：[[15-214-16-Frameworks]]
- 课程总览：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]
- 课程目录：[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸：
  - Dafny 官网 `http://research.microsoft.com/en-us/projects/dafny/`（讲义笔记第 9 行给出，2013 年地址；现为 `https://dafny.org/`）与在线试用 `http://rise4fun.com/dafny/Hello`（讲义笔记第 10 行；现为 `https://rise4fun.com/Dafny/`）。
  - Barbara Liskov & Jeannette Wing, "A Behavioral Notion of Subtyping", *ACM TOPLAS* 16(6), 1994 —— 本讲第 9 页「行为子类型」三条规则的理论出处，也是里氏替换原则的正式化。
  - Bertrand Meyer, *Object-Oriented Software Construction*（2nd ed., 1997），第 11 章「Design by Contract」——前置/后置/不变式的原始论述，与 [[15-214-05-Object-Contracts-and-Exceptions]] 和 [[15-214-11-Design-Principles-GRASP]]（Meyer 五准则）直接相关。
  - K. Rustan M. Leino, "Dafny: An Automatic Program Verifier for Functional Correctness", *LPAR-16*, 2010 —— Dafny 的设计论文，解释「为什么去掉继承能大幅简化验证」。
  - CMU 15-313（Foundations of Software Engineering）—— 第 8 讲第 6 页的功能性正确全景图指出，形式化验证、静态分析、需求定义、审查、集成测试等都在 15-313 覆盖。若对形式化方法有兴趣，这是自然的后续课程。
  - 实践入口：用 Dafny 验证一个你自己写过的数据结构（比如 [[15-214-14-Java-Collections]] 里的 `AbstractList` 子类），体会「写规格」与「写实现」的工作量比例——这是判断「形式化方法是否值得」的最直接方式。
