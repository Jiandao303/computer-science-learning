---
course: CMU 15-122
course_name: Imperative Computation
semester: Fall 2026
lecture_id: L11
topic: Unbounded Arrays
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-122
  - 无界数组
  - C0
---

# 第 11 讲：无界数组（Unbounded Arrays）

## 1. 本节学习目标

学完本讲后，你应该能够：

1. 说明数组与链表的**两难**：数组 `O(1)` 访问但**大小固定**，链表可扩展但访问 `O(n)`；并说明无界数组如何**同时拿到两者**。
2. 用 **n 位二进制计数器**完整走一遍摊还分析：`k` 次自增的总代价是 `2k - 1`，故**摊还 `O(1)`**。
3. 复述摊还分析的**四步方法**（发明代币 → 指定储备不变式 → 给每个操作定摊还代价 → 证明不变式可恢复）。
4. 解释**「代币不变式」为什么只存在于头脑中**，与普通数据结构不变式的异同。
5. 说明**摊还分析（amortized analysis）**与**平均情况分析（average-case analysis）**的本质区别：**前者没有运气成分**。
6. 写出 `uba_header` 的三个字段与 `is_uba` 的三条不变式，并解释为什么 `size < limit` 必须是**严格**小于。
7. 说明 `uba_new` 里 `limit = size == 0 ? 1 : size*2` 的**两个**理由。
8. 逐行证明 `uba_add` + `uba_resize` 保持 `is_uba`，并说明 `assert(A->limit <= int_max()/2)` 为什么是**硬断言（hard assert）**而不是 `//@assert`。
9. 用**金色代币 + 蓝色代币**方案证明 `uba_add` 的摊还代价是 **3 次数组写**，并推导「代币数 = `2*size - limit`」。
10. 解释为什么**不能**在「少于一半就缩容」——必须等到**少于四分之一**，并说明这个阈值如何改变不变式。
11. 用**摊还分析**算出扩容因子 `1.75` 时摊还代价 `10/3`、因子 `4` 时 `7/3`，并解释**为什么不用最大因子**。
12. 用**咖啡店寓言**把「每次扩容请所有老客户喝咖啡」与「每次翻倍才请客」的成本差异算清楚（`$(4+2n)` vs `$6`）。

## 2. 前置知识

- [[15-122-03-Arrays]]：`alloc_array(t, n)`、`\length(A)`、越界报错。
- [[15-122-05-Big-O]]：`O(1)`/`O(n)`/`O(n²)`；「忽略常数因子」——本讲的「3 次数组写」正是靠这条原则才等价于 `O(1)`。
- [[15-122-08-Libraries]]：抽象类型、`typedef ______* uba_t;`、数据结构不变式 `is_uba`、**「长度检查只能放在契约里」**（`is_uba_expected_length` 的写法与 `is_array_expected_length` 完全同构）。
- [[15-122-10-Linked-Lists]]：链表是「可扩展」的另一条路——本讲最后要与它对比。
- [[15-122-07-Quicksort]]：随机枢轴的**期望** `O(n log n)` 是本讲反复对照的「平均情况分析」。

## 3. 核心概念

**Unbounded Array（无界数组）**：对外表现为「长度可变、随机访问 `O(1)`」的数组；内部用**固定大小的数组 + 一个 `size` 计数 + 一个 `limit` 容量**实现。

**`size`（逻辑长度）**：客户端看到的元素个数。

**`limit`（容量）**：底层数组的实际槽位数，`limit >= size`，通常**远大于** `size`。

**`uba_add(A, x)`（追加）**：在末尾加一个元素，`size` 加一。

**`uba_rem(A)`（删除末尾）**：删掉最后一个元素并返回它，`size` 减一。

**`uba_resize(A)`（调整容量）**：分配一个新数组、复制旧内容、替换 `A->data`。**这是唯一 `O(n)` 的操作。**

**Amortized Analysis（摊还分析）**：证明**一串操作的累计代价**不超过「每个操作的摊还代价之和」，即使单个操作可能很贵。

**Amortized Cost（摊还代价）**：为每个操作「预算」的代币数，使得任意序列的总实际代价 `<=` 总预算。

**Token（代币）**：抽象的成本单位。本讲中**一个代币 = 一次数组写**。

**Potential Method（势能法）**：摊还分析的另一种名字——把「储备的代币」看成数据结构的**势能**。

**Hard Assert（硬断言）**：`assert(...)`（不带 `//@`），**任何编译选项下都执行**；用于捕捉「契约无法排除但也不想写进接口」的不可能情形。

**Doubling（翻倍扩容）**：`limit` 满时把它变成 `2 * size`。这是让摊还代价为常数的**关键**。

## 4. 通俗理解

**本讲要解决的矛盾（讲义开篇原话）**：

> **「Arrays have efﬁcient `O(1)` access to elements given an index, but their size is set at allocation time. ... Linked lists do not have this problem at all since they are extensible, but accessing an element is `O(n)`.」**

**数组**：像一排编了号的储物柜，**直接开第 7 号**（`O(1)`），但**柜子数量在造楼时就定死了**。东西多了放不下，东西少了浪费。
**链表**：像一队手拉手的人，**想加多少加多少**，但**找第 7 个人要从头数**（`O(n)`）。

**无界数组 = 会自己搬家的储物柜**：先租 10 个柜子。第 11 件东西来了，就**租 20 个新柜子、把 10 件都搬过去**。之后 9 次都不用搬。**单次可能很贵（搬 10 件），但平均下来每次只搬一点点。**

**讲义的问句**：「like lists can hold an arbitrary number of elements, but also allow these element to be retrieved in `O(1)` time? **What gives?**」——**天下没有免费的午餐，代价是「偶尔的 `O(n)` 搬家」。** 摊还分析要证明的就是「偶尔」足够少。

**二进制计数器 = 摊还分析的入门教具**：数 0, 1, 2, 3, ... 时，最低位每次翻，第二位每 2 次翻一次，第三位每 4 次翻一次……

| 自增 | 翻的位数 | 代价 |
|---|---|---|
| 0→1 | `1` | 1 |
| 1→2 | `01→10` | 2 |
| 2→3 | `10→11` | 1 |
| 3→4 | `011→100` | 3 |
| 4→5 | `100→101` | 1 |
| 5→6 | `101→110` | 2 |
| 6→7 | `110→111` | 1 |
| 7→8 | `0111→1000` | 4 |

**代价序列**：`1, 2, 1, 3, 1, 2, 1, 4, ...`——**贵的操作越来越稀**。前 8 次总代价 `15 = 2*8 - 1`。**这就是「摊还 2」的来源：每次预算 2 个代币，总预算 `2k`，永远够用。**

**银行比喻（讲义原文）**：每次自增「预算 2 个代币」，花掉 1 个（翻最右边的 0），**存 1 个**。当某个 1 将来要变回 0 时，**用当初存的那个代币付账**。**储蓄账户永不为空。**

**为什么这个比喻能变成证明**：讲义的关键一跃——

> **「we can see a very useful invariant: the number of 1 bits always matches the number in our savings account!」**

**「1 的个数 = 存款数」**——这条等式把「模糊的银行直觉」变成了**可检查的不变式**。**这是本讲最漂亮的一步。**

**为什么这条不变式「只存在于头脑中」**：讲义特意点明——

> **「Differently from normal data structure invariants, it is not captured in code — it resides in our minds only.」**

**因为代币不是真实数据。** 你没法在 `struct` 里加一个 `int tokens` 字段——那就变成真的在数了，而且「代币」本来是**为了分析而虚构的记账单位**。**普通不变式（`is_uba`）写进代码、由 `cc0 -d` 检查；代币不变式写进论文、由人脑检查。** 这是本讲对「不变式」这个概念的一次重要扩展。

**摊还 ≠ 平均**：这是本讲最容易被误解的一点。讲义原文：

> **「This is different than average case analysis for quicksort, where we know that sometimes the total cost of sorting could be higher than predicted (if we get unlucky in our random pivot selection). There's no luck in our amortized analysis.」**

**快排的平均分析**：假设枢轴随机，**期望**是 `O(n log n)`，但**可能倒霉**（连续选到最差枢轴）→ 退化成 `O(n²)`。
**无界数组的摊还分析**：**没有随机性**。`k` 次 `uba_add` 的总代价**一定** `<= 3k` 次数组写，**不管你怎么调用**。**这是最坏情况的界，不是期望。**

**一句话**：**平均分析是「通常如此」，摊还分析是「永远如此」。**

**为什么缩容不能在一半就做**：想象数组刚好半满（`size == limit/2`）。此时**代币储备恰好是 0**（见 5.7 的公式 `2*size - limit = 0`）。若此时缩容，**要复制 `limit/2` 个元素，但一个代币都没有**——**破产**。

**更糟的是「抖动（thrashing）」**：若在「半满」这个临界点反复 `add`/`rem`，每次都会触发一次 `O(n)` 的扩容或缩容，`n` 次操作变成 `O(n²)`。**必须留出「缓冲带」**：扩容在**满**时（100%），缩容在**四分之一**时（25%）。**两个阈值之间的 75% 是安全区。**

**咖啡店寓言（习题 4）**：你有 `n` 台咖啡机、`50n` 个客户。**每次买新机器就请所有老客户免费喝一杯**——下一次扩张前只多 50 个客户，他们得付 `$(4 + 2n)` 一杯！**客户越多，咖啡越贵**，生意做不下去。
**改成「每次翻倍才请客」**：`n` 台变 `2n` 台，请 `50n` 个老客户，然后要等 `50n` 个新客户才再扩张——**每人付 `$6`，与 `n` 无关**。**这正是 `uba_add` 的翻倍策略。** 讲义原文：「each new customer corresponds to adding an element to the array, and each coffee corresponds to a token.」

## 5. 原理与推导

### 5.1 n 位计数器：`k` 次自增的总代价是 `2k - 1`

**计数器的行为**（讲义 p3 原文）：

> **「Whenever we increment the counter, we'll always ﬂip some number (maybe zero) of lower-order 1's to 0, and then we'll ﬂip exactly one 0 to 1 (unless we're out of bits in the counter).」**

**例**：`10010011` 自增得 `10010100`——**两个最低的 1 变成 0**，**最右边的 0 变成 1**，其余不变。

**为什么是这个模式**：二进制加 1 就是「从最低位往高位找第一个 0，把它变 1，把途经的所有 1 变 0」。**没有进位时（最低位是 0）只翻 1 位。**

**代价的精确计数**：设第 `k` 次自增（从 0 开始数，第 1 次是 `0→1`）。**第 `i` 位（从 0 数）在 `k` 次自增中被翻多少次**：

- 第 0 位每 1 次翻一次 → `k` 次
- 第 1 位每 2 次翻一次 → `floor(k/2)` 次
- 第 2 位每 4 次翻一次 → `floor(k/4)` 次
- ...

**总代价**：

```
T(k) = k + floor(k/2) + floor(k/4) + floor(k/8) + ... < k * (1 + 1/2 + 1/4 + ...) = 2k
```

**故 `T(k) < 2k`。** 更精确地，讲义给出（p2）：

> **「whenever we reach a most-expensive-so-far operation at step `k`, the total cost of all the operations up to and including that operation is `2k − 1`.」**

**验证**：`k = 8`（第 8 次是 `0111 → 1000`，翻 4 位），总代价 `1+2+1+3+1+2+1+4 = 15 = 2*8 - 1`。✅

**为什么「最贵的操作」处恰好是 `2k-1`**：第 `k` 次自增翻 `log2(k) + 1` 位，这种操作发生在 `k` 是 2 的幂时。此时计数器从 `0111...1` 变成 `1000...0`，**前面 `k-1` 次已经把每一位都翻遍了**，总代价恰好 `2k - 1`。**这是一个可归纳证明的等式**（讲义只说「we can observe」，没给证明）。

**两个非形式观察（讲义 p2 原文）**：

> **「First, the most expensive operations get further and further apart as time goes on. Second, whenever we reach a most-expensive-so-far operation at step `k`, the total cost of all the operations up to and including that operation is `2k − 1`.」**

**第一条是直觉，第二条是数字。** 摊还分析的工作就是**把第二条变成不变式**。

### 5.2 四步方法：从银行比喻到形式证明

**讲义的完整方法论（p4，值得逐字抄下来）**：

> **1. Invent a notion of tokens that stand in for the resource that we're interested in (usually time — in our example, a token is spent each time a bit is ﬂipped);**
> **2. Specify, for any instance of the data structure, how many tokens need to be held in reserve as part of the data structure invariant (in our example, one token for each 1-bit);**
> **3. Assign, for each operation we might perform on the data structure, an amortized cost in tokens (in our example, two tokens for each increment);**
> **4. Prove that, for any operation we might perform on the data structure, the amortized cost plus the tokens held in reserve as part of the data structure invariant sufﬁces to restore the data structure invariant.**

**逐条对应计数器**：

| 步 | 计数器中的实例 |
|---|---|
| 1 | **1 代币 = 翻 1 位** |
| 2 | **储备 = 每个 1 位配 1 个代币**（故 `10010011` 有 4 个代币） |
| 3 | **每次自增收 2 个代币** |
| 4 | 见下面的逐情形证明 |

**第 4 步的逐情形证明**（讲义 p3 的论证，形式化）：

设自增前有 `p` 个 1 位、储备 `p` 个代币。自增收 2 个代币，**共 `p + 2` 个**。设最低位起有 `j` 个连续的 1（`j >= 0`）。

**情形 A：`j` 个低位的 1 变 0，最右边的 0 变 1**（计数器未满）：

- **翻位代价**：`j + 1` 次翻位。
- **支付**：那 `j` 个 1 各自**带着 1 个代币**（不变式保证），正好付 `j` 次；**新收的 2 个代币**中 1 个付「0 变 1」。
- **剩余**：`p + 2 - j - 1 = p + 1 - j` 个代币。
- **新的 1 位数**：`p - j + 1`（少了 `j` 个，多了 1 个）。
- **核对**：`p + 1 - j == p - j + 1`。✅ **不变式恢复。**

**情形 B：所有位都是 1，全部变 0**（计数器溢出）：

- **翻位代价**：`n` 次（`n` 是位数）。
- **支付**：`p = n` 个 1 各带 1 个代币，正好付清。
- **剩余**：新收的 2 个代币**用不上**——**直接扔掉**。
- **新的 1 位数**：0，故需要 0 个代币。
- **核对**：0 个代币 == 0 个 1 位。✅ **不变式恢复。**

**讲义对这一情形的说明（p3–4）**：

> **「if the counter is limited to `n` bits and they're all 1, then we'll ﬂip all the bits to 0. In this case, we can just throw away or lose track of our two new tokens, because we can restore the data structure invariant without needing the two new tokens.」**

**结论（讲义 p4）**：

> **「a series of `k` increments of the `n`-bit counter, starting when the counter is all zeroes, will take time in `O(k)`. We can also say that each individual operation has an amortized running time of 2 bit ﬂips, which means that the amortized cost of each operation is in `O(1)`.」**

**以及那句关键的「不矛盾」**：

> **「It's not at all contradictory for bit ﬂips to have an amortized running time in `O(1)` and a worst-case running time in `O(n)`.」**

**这是本讲最重要的一句话**：**「摊还 `O(1)`」与「最坏 `O(n)`」可以同时为真。** 它们回答的是**不同的问题**：

- 最坏 `O(n)`：**单次**操作最多要多久？
- 摊还 `O(1)`：**`k` 次操作平均**每次多久？

### 5.3 摊还分析的保证强度

**讲义 p5 的精确表述**：

> **「This analysis proves that, for any sequence of operations on a data structure, the cumulative cost of that sequence of operations will be less than or equal to the sum of the amortized cost of those operations.」**

**形式化**：

```
对任意操作序列 op1, op2, ..., opk：
    Σ actual_cost(opi)  <=  Σ amortized_cost(opi)
```

**注意这是对「任意序列」的陈述**，不是「期望」。**没有概率，没有「通常」。**

**讲义对「代币不是真的」的说明（p4–5）**：

> **「Tokens aren't real things, of course! They are stand-ins for the actual resources we're interested in. Usually, the resource we are concerned about is time, so we match up tokens to the (frequently constant-time) operations we have to do on our data structure.」**

**在计数器里**：1 代币 = 1 次翻位（如果计数器存在 `bool[]` 里，就是 1 次数组写）。
**在无界数组里**：1 代币 = 1 次数组写。

**为什么选「数组写」当代币**：讲义 p11 原文——

> **「We do things that aren't array writes in the process of doing `uba_add`, but the cost is dominated by array writes, so this gives the right big-O notion of (amortized) cost.」**

**「被数组写支配」是关键**：`uba_add` 里还有指针赋值、比较、函数调用——**都是 `O(1)`**。若数组写是 `O(n)`，其余 `O(1)` 项被**吸收**进大 O。**这就是 [[15-122-05-Big-O]] 的「忽略常数因子」在摊还分析里的用法。**

**「势能法」这个名字（p4 末）**：

> **「This form of amortized analysis is sometimes called the potential method.」**

**为什么叫「势能」**：把「储备的代币数」看成数据结构的**势能** `Φ`。摊还代价 = 实际代价 + `ΔΦ`。**物理学里「势能 + 动能守恒」，这里是「储备 + 花费守恒」。** 本讲只用最朴素的版本，不引入 `Φ` 记号。

### 5.4 无界数组的接口

**基础接口（p6，与 [[15-122-08-Libraries]] 的自排序数组同构）**：

```c0
// typedef ______* uba_t;
int uba_len(uba_t A)
/*@requires A != NULL; @*/
/*@ensures \result >= 0; @*/;

uba_t uba_new(int size)
/*@requires 0 <= size; @*/
/*@ensures \result != NULL; @*/
/*@ensures uba_len(\result) == size; @*/;

string uba_get(uba_t A, int i)
/*@requires A != NULL; @*/
/*@requires 0 <= i && i < uba_len(A); @*/;

void uba_set(uba_t A, int i, string x)
/*@requires A != NULL; @*/
/*@requires 0 <= i && i < uba_len(A); @*/;
```

**扩展接口（p6–7）**：

```c0
void uba_add(uba* A, string x)
/*@requires A != NULL; @*/;

string uba_rem(uba* A)
/*@requires A != NULL; @*/
/*@requires 0 < uba_len(A); @*/;
```

**`uba_rem` 的前置 `0 < uba_len(A)`**：空数组不能删元素。**与 [[15-122-09-Stacks-and-Queues]] 的 `pop` 前置 `!stack_empty(S)` 完全同构。**

**为什么 `uba_add` 没有后置**：接口只承诺「能加」，**没有承诺「加在哪」**。若要写，应该是 `uba_len(A) == \old(uba_len(A)) + 1` 且 `uba_get(A, \old(uba_len(A))) == x`。**讲义省略了，这是接口的一处不完整**（见第 8 节原文异常）。

**复杂度目标（p7 原文）**：

> **「We'd like to give all the operations in this extended array interface except `uba_new` a running time in `O(1)`. It's not practical to give `uba_add(A,x)` a worst case running time in `O(1)`, but with a careful implementation we can show that is possible to give the function an amortized running time in `O(1)`.」**

**`uba_new` 例外**：脚注 1 原文——**「By necessity, `uba_new(n)` has cost `O(n)` since it allocates an `n`-element array.」** **分配 `n` 个槽位本身就要 `O(n)`**，无法避免。

**为什么 `uba_add` 的「最坏 `O(1)`」不可能**：容量满时必须**搬走所有元素**，那是 `O(n)`。**除非你放弃「连续内存」**（那就是链表了）。**故只能求摊还。**

### 5.5 `uba_header` 与 `is_uba`

**结构（p7）**：

```c0
typedef struct uba_header uba;
struct uba_header {
  int size;
  /* 0 <= size && size < limit */
  int limit;
  /* 0 < limit */
  string[] data;
  /* \length(data) == limit */
};
typedef uba* uba_t;
```

**三个字段的分工**：

| 字段 | 含义 | 谁能看见 |
|---|---|---|
| `size` | **逻辑长度**（客户端看到的元素数） | 通过 `uba_len` |
| `limit` | **物理容量**（底层数组槽位数） | **隐藏** |
| `data` | 底层数组（长度恰为 `limit`） | **隐藏** |

**`uba_len`（p7）**：

```c0
int uba_len(uba* A)
//@requires is_uba(A);
//@ensures 0 <= \result && \result <= \length(A->data);
{
  return A->size;
}
```

**后置 `\result <= \length(A->data)`** 就是 `size <= limit`，**但不变式给的是严格 `size < limit`**——**后置比不变式弱一点，这是有意的**（见下）。

**为什么 `size < limit` 必须是严格小于（讲义 p8 原文）**：

> **「Because we require that the size be strictly less than the limit, we can always implement `uba_add` by storing the new string in `A->data[A->size]` and then incrementing the size.」**

**推导**：若 `size < limit`，则 `A->data[size]` **一定在界内**（因为 `size < limit == \length(data)`）。**故 `uba_add` 可以无条件先写再检查。** 若允许 `size == limit`，则 `A->data[size]` **越界**，`uba_add` 必须先检查再写。

**这个「严格小于」是「先写后修」的前提**——`uba_add` 的三行代码全靠它才安全。**不变式的一个字符（`<` vs `<=`）决定了整个实现的形状。**

**`is_uba`（p8）**：

```c0
bool is_uba_expected_length(string[] A, int limit) {
  //@assert \length(A) == limit;
  return true;
}
bool is_uba(uba* A) {
  return A != NULL
      && 0 <= A->size && A->size < A->limit
      && is_uba_expected_length(A->data, A->limit);
}
```

**`is_uba_expected_length` 的写法与 [[15-122-08-Libraries]] 的 `is_array_expected_length` 完全一样**：`\length` **只能出现在契约里**，不能出现在普通表达式里（它是 C0 的注解语法）。故用一个**永远返回 `true`** 的规格函数，把长度检查藏在 `//@assert` 里。

**为什么这个技巧必需**：`\length(A->data) == A->limit` 是**真正要检查的不变式**，但 `\length` 在函数体里非法。**规格函数 `is_uba_expected_length` 是「把契约语法偷渡进布尔表达式」的唯一合法通道。**

**`0 < A->limit` 没写进 `is_uba`**：因为 `0 <= size && size < limit` **已经蕴含** `limit >= 1 > 0`。**多余的合取项是噪声**，讲义省略得对。

### 5.6 `uba_add` 与 `uba_resize`

**`uba_add`（p8–9）**：

```c0
void uba_add(uba* A, string x)
//@requires is_uba(A);
//@ensures is_uba(A);
{
  A->data[A->size] = x;
  (A->size)++;
  uba_resize(A);
}
```

**三行的逻辑**：

1. **写**：`A->data[size] = x`——**安全**，因为 `size < limit`（5.5）。
2. **加一**：`size++`。
3. **修**：`uba_resize(A)`——**可能现在 `size == limit` 了，不变式被破坏**，必须修。

**注意第 3 步是「无条件调用」**：即使 `size < limit`，也调 `uba_resize`。**由 `uba_resize` 自己判断要不要真的扩容**（`if (A->size == A->limit)`）。**这是「把条件检查收进辅助函数」的常见手法**——`uba_add` 保持三行不变。

**`uba_resize`（p9）**：

```c0
void uba_resize(uba* A)
//@requires A != NULL && \length(A->data) == A->limit;
//@requires 0 < A->size && A->size <= A->limit;
//@ensures is_uba(A);
{
  if (A->size == A->limit) {
    assert(A->limit <= int_max() / 2);   // Can't handle bigger
    A->limit = A->size * 2;
  } else {
    return;
  }
  //@assert 0 <= A->size && A->size < A->limit;
  string[] B = alloc_array(string, A->limit);
  for (int i = 0; i < A->size; i++)
  //@loop_invariant 0 <= i && i <= A->size;
  {
    B[i] = A->data[i];
  }
  A->data = B;
}
```

**前置的两条**：

| 前置 | 为什么需要 |
|---|---|
| `A != NULL && \length(A->data) == A->limit` | 解引用 `A->data` 的前提；也是 `alloc_array` 大小正确的前提 |
| `0 < A->size && A->size <= A->limit` | **`0 < size`** 因为 `uba_rem` 可能把 `size` 减到 0（此时不该缩容到 `limit = 0`）；**`size <= limit`** 因为 `uba_add` 之后可能恰好满 |

**为什么前置是 `size <= limit` 而 `is_uba` 要求 `size < limit`**：`uba_add` 在 `size++` **之后**调用 `uba_resize`，**此时可能已经 `size == limit`**——**函数内部暂时违反不变式**（这是 [[15-122-09-Stacks-and-Queues]] 与 [[15-122-10-Linked-Lists]] 反复出现的允许情形）。故 `uba_resize` 的前置**故意放宽**。

**扩容分支**：

```c0
if (A->size == A->limit) {
  assert(A->limit <= int_max() / 2);
  A->limit = A->size * 2;
} else {
  return;
}
```

**为什么用 `A->size * 2` 而不是 `A->limit * 2`**：两者在**此分支内相等**（`size == limit`），**写法等价**。讲义用 `size` 更贴合「按元素数翻倍」的语义。

**`assert(A->limit <= int_max() / 2)` 为什么是硬断言（讲义 p9 原文）**：

> **「The assertion `assert(A->limit <= int_max() / 2)` is there because, without it, we have to worry that doubling the limit in the next line might overflow. Hard asserts like this allow us to safely detect unlikely failures that we can't exclude with contracts but that we don't want to encode into our interface.」**

**三个要点**：

1. **防溢出**：`limit * 2` 若超过 `int_max()` 会**回绕成负数**（[[15-122-02-Ints]] 的模 2^32 语义），后续 `alloc_array(string, 负数)` **崩溃或更糟**。
2. **为什么不写成 `//@requires`**：那会**强加给所有客户端**一个「你的数组不能超过 10 亿元素」的义务。**接口不该为这种极端情形增加负担。**
3. **为什么用 `assert` 而不是 `//@assert`**：**`//@assert` 只在 `-d` 下执行**，不带 `-d` 时**完全没有保护**。而溢出是**真实的安全隐患**，必须**任何编译选项下都检查**。**硬断言 = 「我宁可运行时崩，也不要静默溢出」。**

**这是 `assert` 与 `//@assert` 的语义分水岭**：

| | `assert(e)` | `//@assert e;` |
|---|---|---|
| 不带 `-d` | **执行**，失败则 abort | **完全不执行** |
| 带 `-d` | 执行 | 执行 |
| 用途 | 运行时安全检查（防溢出、防越界） | 帮助验证器证明契约 |

**复制循环**：

```c0
string[] B = alloc_array(string, A->limit);
for (int i = 0; i < A->size; i++)
//@loop_invariant 0 <= i && i <= A->size;
{
  B[i] = A->data[i];
}
A->data = B;
```

**不变式 `0 <= i && i <= A->size`**：只需要这一条——**因为 `B` 与 `A->data` 都是 `limit` 长，而 `i < size <= limit`，故两边都不越界**。**这里不需要「已复制的部分相等」这样的不变式**，因为**没有循环后的断言需要它**（`A->data = B` 之后，`is_uba` 只关心长度，不关心内容）。**这是「不变式只需够用」的范例**——多写无益。

**`A->data = B` 是「换指针」，不是「复制回去」**：旧数组**整个被丢弃**，变成**不可达（unreachable）**，由 C0 的垃圾回收器回收（[[15-122-10-Linked-Lists]] 5.8 讲过同一机制）。**这是无界数组比「原地扩容」优越的地方**——C0 的数组**不能原地变长**。

**`uba_resize` 的复杂度**：`alloc_array` 是 `O(limit)`、复制循环是 `O(size)`，**故 `O(limit) = O(size)`**。**这就是那个「偶尔的 `O(n)`」。**

### 5.7 摊还分析：3 次数组写

**成本模型**：**1 代币 = 1 次数组写。**

**代币不变式（讲义 p10 原文）**：

> **「our data structure invariant for tokens is that every cell in use in the second half of the array (i.e., each cell at index `i` in `[limit/2, size)`) and the corresponding cell in the ﬁrst half of the array (at index `i − limit/2`) will have one token associated with it.」**

**用图说**：设 `limit = 8`、`size = 6`。

```
下标:   0    1    2    3  |  4    5    6    7
        [蓝] [蓝] [ ]  [ ] | [金] [金] [空] [空]
         ↑                  ↑
      与 4、5 配对        已用的后半部分
```

**规则**：

- **后半部分已用的格子**（`i ∈ [limit/2, size)`）**各带 1 个金色代币**。
- **前半部分对应的格子**（`i - limit/2 ∈ [0, size - limit/2)`）**各带 1 个蓝色代币**。

**代币总数**：

```
金色: size - limit/2
蓝色: size - limit/2
总计: 2*(size - limit/2) = 2*size - limit
```

**这就是讲义 p11 的公式**：「the number of tokens associated with an unbounded array is `2 × size − limit`」。

**`uba_add` 的摊还代价 = 3**（讲义 p10 原文）：

> **「Each time we add an element to the array (at index `size`), we use one token to perform that very write, store one gold token with this element for copying it next time we double the size the array in a future resize, and store one blue token for copying the corresponding element in the ﬁrst half of the array (at index `size − limit/2`) on that same resize.」**

**三个代币的用途**：

| 代币 | 用途 |
|---|---|
| 1 个 | **付当前的写**（`A->data[size] = x`） |
| 1 个金 | 存给**这个新元素自己**，将来扩容时复制它 |
| 1 个蓝 | 存给**前半部分对应的元素**，将来扩容时复制它 |

**为什么需要「蓝色代币」**：扩容时要复制**整个旧数组**（`limit` 个元素），而金色代币只覆盖**后半部分**（`limit/2` 个）。**前半部分的那 `limit/2` 个元素也需要代币**——它们的代币是**在它们被加入时**（那时它们还在后半部分）存下的蓝色代币。**「蓝色」标记的是「这笔钱是为前半部分预留的」。**

**不变式保持性验证（非满情形）**：设 `size < limit`，加入一个元素后 `size' = size + 1`。

- **消耗**：3 个代币（1 付写、1 金、1 蓝）。
- **代币数变化**：`(2*size' - limit) - (2*size - limit) = 2`——**增加了 2 个**。✅ 正好等于新存的 1 金 + 1 蓝。

**满情形（`size == limit`）的验证**（讲义 p10–11 原文）：

> **「In the cases where the addition does completely ﬁll the array, we need to copy over every element in the old array into a new, larger array ... This requires one write for every element in the old array. We can pay for each one of those writes because we now have one gold token for each element in the second half of the old array (at indices `[limit/2, limit)`) and one blue token for each element in the ﬁrst half of that array (at indices `[0, limit/2)`) — which is the same as having one token for each cell in the old array.」**

**推导**：满时 `size == limit`，故代币数 `2*limit - limit = limit`——**恰好 `limit` 个代币，恰好够复制 `limit` 个元素**。✅

**扩容后**：`limit' = 2*limit`，`size' = limit`，故 `size' == limit'/2`——**刚好半满**。代币数 `2*limit - 2*limit = 0`。**讲义原文**：「After the resize, exactly half the array is full, so our data structure invariant for tokens doesn't require us to have any tokens in reserve.」✅ **不变式恢复，储备归零，下一个循环开始。**

**这个「归零」是设计的精髓**：扩容后**储备恰好为 0**，说明**预算刚好够用，一分不多一分不少**。**3 是紧的下界**（在只考虑常数因子的大 O 意义下，任何常数都行；但精确到这个代币模型，3 是恰好够）。

**结论（讲义 p11）**：

> **「This establishes that the amortized cost of `uba_add` is three array writes.」**

**故 `k` 次 `uba_add` 的总代价 `<= 3k` 次数组写，即 `O(k)`。** **单次最坏 `O(n)`，摊还 `O(1)`。**

### 5.8 缩容：为什么必须等到四分之一

**`uba_rem`（p11）**：

```c0
string uba_rem(uba* A)
//@requires is_uba(A);
//@requires 0 < uba_len(A);
//@ensures is_uba(A);
{
  (A->size)--;
  string x = A->data[A->size];
  uba_resize(A);
  return x;
}
```

**注意顺序**：**先减 `size`，再读 `data[size]`**——这样读到的正是**被删的那个元素**（原 `size - 1` 位置）。**顺序反了就会读错元素。**

**为什么 `uba_resize` 能同时处理扩容与缩容**：目前它只写了扩容分支。要支持缩容，得加一个分支（讲义说「We could also call `uba_resize(A)` in our `uba_rem` function, and allow that function to make the array either bigger or smaller」，但**没给完整代码**）。

**为什么不能在「半满」时缩容（讲义 p11–12 原文）**：

> **「If we want `uba_rem` to take amortized constant time, it will not work to resize the array as soon as `A` is less than half full. An array that is exactly half full doesn't have any tokens in reserve, so it wouldn't be possible to pay for halving the size of the array in this case.」**

**推导**：半满时 `size == limit/2`，代币数 `2*(limit/2) - limit = 0`。**缩容要复制 `limit/2` 个元素，需要 `limit/2` 个代币，但手里是 0。** **破产。**

**更致命的是抖动（thrashing）**：设 `limit = 2k`、`size = k`（半满）。

| 操作 | 结果 |
|---|---|
| `rem` | `size = k-1 < limit/2` → **缩容到 `limit = k`**，复制 `k` 个元素（`O(k)`） |
| `add` | `size = k == limit` → **扩容到 `limit = 2k`**，复制 `k` 个元素（`O(k)`） |
| `rem` | 又缩容…… |
| `add` | 又扩容…… |

**每次操作都是 `O(k)`，`n` 次操作 `O(nk) = O(n²)`。** **摊还 `O(1)` 彻底失效。**

**解法（讲义 p12 原文）**：

> **「In order to make the constant-time amortized cost work, the easiest thing to do is only resize the array when it is less than one-quarter full.」**

**四分之一的好处**：缩容后 `limit' = limit/2`、`size = limit/4`，故 `size = limit'/2`——**又是半满**，与扩容后的状态**对称**。**两个阈值之间留出 `[limit/4, limit)` 的缓冲带，任何「加一个减一个」的抖动都发生在缓冲带内，不触发重分配。**

**不变式的修改（讲义 p12）**：

> **「it's possible to reﬂect it in the data structure invariant, requiring that `A->size` be in the range `[A->limit/4, A->limit)` rather than the range `[0, A->limit)` that we required before.」**

**故新的 `is_uba` 应该写成**：

```c0
bool is_uba(uba* A) {
  return A != NULL
      && 0 <= A->size && A->size < A->limit
      && A->limit / 4 <= A->size          // 新增：至少四分之一满
      && is_uba_expected_length(A->data, A->limit);
}
```

**注意 `A->limit/4 <= A->size` 在 `size == 0` 时也成立**（`0 <= 0`），**故空数组合法**——只要 `limit` 不缩到 0。**这就是 `uba_resize` 前置 `0 < A->size` 的作用**：`size == 0` 时不缩容，避免 `limit = 0`（那样 `limit/4 == 0` 会允许空数组，但 `alloc_array(string, 0)` 与后续 `data[size]` 会出问题）。

**代币不变式也要扩展（讲义 p12）**：

> **「In order to show that this deletion operation has the correct amortized cost, we must extend our data structure invariant to also store tokens for every unused cell in the left half of the array. (See the exercises below.)」**

**习题 5 的答案（p18–19）**：

> **「`uba_rem` resizes the array to half its size, `k/2` once it becomes a quarter full, i.e., once it contains `k/4` elements. ... we need to have enough tokens in reserve to copy all the elements from the old array to the new array: that's `k` and `k/4` tokens respectively.」**

**`uba_rem` 的摊还代价 = 1**（讲义 p18 原文）：

> **「We can show that `uba_rem` has `O(1)` amortized cost by charging one token for this operation (each call to `uba_add` continues to cost three tokens) — the amortized cost is constant since the number of tokens charged is constant too.」**

**为什么 1 个就够（讲义 p18–19 的推导）**：

- **最坏情形**：`uba_add` 刚把 `limit` 从 `k` 翻到 `2k`，储备为 0。此时 `size = k`。
- **连续 `k/2` 次 `uba_rem`**：每次收 1 个代币，`k/2` 次后共 `k/2` 个代币；此时 `size = k/2 = (2k)/4`——**刚好四分之一满**，触发缩容。
- **缩容代价**：复制 `k/2` 个元素到 `limit = k` 的新数组，需要 `k/2` 个代币。**恰好够。** ✅ **缩容后储备归零。**

**混合序列也成立**（讲义 p19 原文）：

> **「In this more general setting, we may not consume all saved tokens when resizing the array, but we will always have enough tokens in reserve to pay for copying its elements.」**

**理由**：`uba_add` 收 3 个（花 1 存 2），`uba_rem` 收 1 个（不花）。**任何混合序列的代币积累速度都不低于纯 `rem` 序列**（纯 `rem` 是「最穷」的情形）。**故纯 `rem` 情形够用，混合情形必然够用。**

**最终结论（讲义 p12）**：

> **「any valid sequence of `n` operations (`uba_add` or `uba_rem`) that we perform on an unbounded array will take time in `O(n)`, even if any single one of those operations might take time proportional to the current length of the array.」**

### 5.9 扩容因子的代价：`1.75` → `10/3`，`4` → `7/3`

**习题 2 的答案（p17）**。设上次扩容后数组有 `k` 个元素。

**因子 1.75（即 +75%）**：

- 新 `limit = k + 0.75k = 7k/4`。
- 还能加 `7k/4 - k = 3k/4` 个元素。
- 下次扩容要复制 `7k/4` 个元素。
- **复制成本摊到每个新增元素**：`(7k/4) / (3k/4) = 7/3` 个代币。
- **加上「写新元素」本身** 1 个 → **总计 `7/3 + 1 = 10/3`**。

**因子 4（即 +300%）**：

- 新 `limit = 4k`。
- 还能加 `3k` 个。
- 复制 `4k` 个 → `4k/3k = 4/3`。
- **总计 `4/3 + 1 = 7/3`**。

**因子 2（基准）**：

- 新 `limit = 2k`，还能加 `k` 个，复制 `2k` 个 → `2k/k = 2`。
- **总计 `2 + 1 = 3`**。✅ 与 5.7 的结论一致。

**通式**：设扩容因子为 `f > 1`（新容量 `= f*k`），则

```
摊还代价 = f/(f-1) + 1
```

**验证**：`f=2` → `2/1 + 1 = 3` ✅；`f=1.75` → `1.75/0.75 + 1 = 7/3 + 1 = 10/3` ✅；`f=4` → `4/3 + 1 = 7/3` ✅。

**`f → ∞` 时 `f/(f-1) → 1`**，故**摊还代价趋近于 2**（下界）。**`f → 1` 时趋于无穷**——**这解释了为什么必须「按倍数」扩容，而不是「按固定增量」**：

**若每次只加固定 `c` 个槽位**（比如每次 +10）：第 `k` 次扩容要复制 `ck` 个元素，而每次扩容之间只加了 `c` 个。**每个元素的摊还代价 `= ck/c = k`**——**随 `k` 增长！** `n` 次操作 `O(n²)`。**「按倍数」是摊还 `O(1)` 的充要条件。**

**为什么不用最大因子（习题 3 的答案，p17 原文）**：

> **「Resizing by a larger factor requires allocating more memory which will remain unused longer. For example, if we resize a length `k` array by a factor of 2, the new array will contain `k` empty positions and it will take `k` calls to `uba_add` to ﬁll the last position. On average, `k/2` positions will be empty during this time, which amounts to a quarter of the resized array being empty. If we resize by a larger factor, say 4, the new array will contain `3k` empty positions and it will take `3k` calls to ﬁll the last position. On average, `3k/2` positions will be empty during this time, i.e., `3/8` of the array will be empty on average.」**

**推导**：

| 因子 | 新容量 | 空位数 | 填满所需 `add` 数 | 平均空位 | 平均浪费比例 |
|---|---|---|---|---|---|
| 2 | `2k` | `k` | `k` | `k/2` | `(k/2)/(2k) = 1/4` |
| 4 | `4k` | `3k` | `3k` | `3k/2` | `(3k/2)/(4k) = 3/8` |

**通式**：因子 `f` 时，平均浪费比例 `= (f-1)/(2f)`。**`f=2` → `1/4`；`f=4` → `3/8`；`f→∞` → `1/2`。**

**结论（讲义 p17）**：

> **「If space usage is the only consideration, smaller resize factors are preferable. However, if space is not too much of a concern for some niche application but we want resizes to be infrequent, then using a larger resize factor may be beneﬁcial.」**

**这就是**时间—空间权衡（time-space trade-off）**：因子小 → 省内存、多扩容；因子大 → 费内存、少扩容。**业界常用 1.5 或 2**（Java 的 `ArrayList` 用 1.5，C++ 的 `vector` 用 2）。**1.5 还有个额外好处：释放的旧块可能被后续分配复用**（因为 `1.5^k` 序列不会像 `2^k` 那样总是要求「比所有已释放块之和还大」的新块）。

### 5.10 习题 1：`uba_new` 的 `limit` 与「分配也算成本」

**`uba_new`（p13）**：

```c0
uba* uba_new(int size)
//@requires 0 <= size;
//@ensures is_uba(\result);
//@ensures uba_len(\result) == size;
{
  uba* A = alloc(uba);
  int limit = size == 0 ? 1 : size*2;
  A->data = alloc_array(string, limit);
  A->size = size;
  A->limit = limit;
  return A;
}
```

**`limit = size == 0 ? 1 : size*2` 的两个理由**：

**理由一（习题 1 答案，p15 原文）**：

> **「Were line 59 to be simply `int limit = size*2`, then `limit` would remain at 0 whenever `size == 0`.」**

**`limit = 0` 违反 `0 < limit`**，而且 `alloc_array(string, 0)` 造出的数组**无法写入任何元素**——第一次 `uba_add` 就会越界。**故 `size == 0` 时必须给 `limit = 1`。**

**理由二：`size*2` 让 `is_uba` 的严格不等式成立**。若 `limit = size`，则 `size < limit` **为假**，`is_uba` 立刻不成立。**故 `limit` 必须严格大于 `size`。**

**为什么是 `size*2` 而不是 `size+1`**：`size+1` 也能满足 `size < limit`，但**会让第一次 `uba_add` 就触发扩容**（`size+1 == limit`），**白白浪费一次 `O(n)` 的复制**。`size*2` 留出 `size` 个空位，**前 `size` 次 `uba_add` 都不用扩容**——**符合「扩容后至少半满」的设计目标**（5.7）。

**习题 1 的第二问：把「分配 `n` 个元素」也算 `n` 个代币**：

**新的成本模型**：1 次数组写 = 1 代币，**`alloc_array(t, n)` = `n` 代币**。

**最坏情形的 `uba_add`（p15 原文）**：

> **「Assume the array has limit `n` and size `n − 1`. The next `uba_add` will trigger a resize. We will write the new element (which costs one token), allocate a new array of length `2n` (which costs `2n` tokens), and copy the elements of the old array to the new array (which costs `n` tokens). The total cost is therefore `3n + 1` tokens, which is in `O(n)`.」**

**分解**：

| 步骤 | 代价 |
|---|---|
| 写新元素 | 1 |
| `alloc_array(string, 2n)` | `2n` |
| 复制 `n` 个元素 | `n` |
| **合计** | **`3n + 1`** |

**摊还代价的推导（p15–16）**。讲义给出一个**六步流程**（值得记住）：

> **「• Draw a short sequence of operations.**
> **• Write the cost of each operation.**
> **• Flag the most expensive**
> **• For each operation, compute the total cost up to it.**
> **• Divide the total cost of the most expensive operations by the operation number in the sequence.**
> **• Round up — that's the candidate amortized cost.」**

**具体计算**：从「长度 2 的数组、1 个元素、0 储备」开始，跑 8 次 `uba_add`。

**设第 `k` 次扩容后 `limit = 2k`**，则**下次扩容前有 `k` 次 `uba_add`**，期间**总代价**：

- **扩容那一次**：写 1 + 分配 `4k`（新 limit 是 `2k` 的两倍）+ 复制 `2k` = `1 + 4k + 2k = 6k + 1`。
- **其余 `k - 1` 次**：每次只写 1 个 = `k - 1`。
- **总计**：`6k + 1 + (k - 1) = 7k`。
- **摊到 `k` 次操作**：`7k / k = 7`。

**讲义原文（p16）**：「we see that the total cost of the most expensive operations divided by the operation number is 7. This is is the amortized number of tokens we pretend each call to `uba_add` costs.」（**注意原文的 "is is" 是笔误**）

**保持性证明（p16 原文）**：

> **「assume we have zero tokens in reserve after resizing the array from size `k` to `2k`. Since each call to `uba_add` writes to the array, we will use one of the 7 tokens obtained from the user right away, leaving a surplus of 6 tokens. ...**
> **• If `0 < i < k`, we simply save these surplus tokens. Right after step `k + i`, we will have `6i` tokens in reserve.**
> **• When `i = k`, we need to resize. ... we will need to perform one write to the old array, allocate a new array of size `4k` and copy all `2k` elements from the old array to the new array. Altogether, we need `6k+1` tokens. We have `6(k−1)` tokens in reserve and receive 7 additional tokens from this call to `uba_add`. Now, `6(k−1)+7 = 6k+1`, which is exactly what we need for this step. We are left with zero tokens in reserve as we start the next cycle.」**

**核对算术**：

- 第 `k + i` 步（`0 < i < k`）后储备 `6i`。
- 第 `2k` 步（`i = k`）时，扩容前储备 `6(k-1)`。
- 收 7 个 → `6k - 6 + 7 = 6k + 1`。
- 需要：写 1 + 分配 `4k` + 复制 `2k` = `6k + 1`。✅ **恰好够，储备归零。**

**注意这里的「分配 `4k`」**：扩容前 `limit = 2k`，翻倍后 `limit = 4k`。**分配成本是新容量 `4k`，不是增量 `2k`。** 这是「分配也算成本」模型带来的差别。

**结论**：在「分配也算成本」的模型下，**摊还代价从 3 涨到 7**——**因为每次扩容要额外付「分配新数组」的钱**。**「分配 `n` 个槽位」与「写 `n` 个槽位」在真实机器上确实都是 `O(n)` 的工作量**（前者要清零或至少建立映射），所以这个更严格的模型**更贴近现实**。

**注意 `7/3 ≈ 2.33`**：真实比率 `7/3` 恰好是「因子 2 的摊还代价 3」加上「分配成本 4k/(2k)·... 」——不必强求直觉，**照流程算就是**。

### 5.11 咖啡店寓言：为什么「每次翻倍才请客」

**习题 4 的设定（p13）**：每位客户每天喝一杯咖啡、第二天必回。**1 台机器服务 50 人/天**。机器 `$100`，每杯成本 `$2`。

**策略 A：每次满员就买 1 台新机器 + 请所有老客户喝一杯**：

设现在有 `n` 台机器、`50n` 个客户。**满员时**：

- 买 1 台新机器：`$100`。
- 请 `50n` 个老客户：`$100n`（每人 `$2`）。
- **总支出**：`$100 + $100n`。

**下一次满员**要等 **50 个新客户**（因为只多了 1 台机器）。这 50 人必须承担：

- 新机器 `$100`
- 请客 `$100n`
- 自己喝的 50 杯 `$2 × 50 = $100`
- **合计 `$100 + $100n + $100 = $200 + $100n`**

**每人付**：`($200 + $100n)/50 = $(4 + 2n)`。

**讲义原文（p17–18）**：「Thus, these next 50 customers must be charged `($100 + $100n + $100)/50`, i.e., `$(4 + 2n)` for each cup of coffee. **This depends on `n` and therefore can get very expensive!** Your new business is not likely to go very far if you charge this much for coffee!」

**关键问题**：**价格随 `n` 线性增长**——客户越多，咖啡越贵。**这不是「摊还 `O(1)`」，而是「摊还 `O(n)`」。**

**策略 B：每次翻倍才请客**（`n` 台 → `2n` 台）：

- 买 `n` 台新机器：`$100n`。
- 请 `50n` 个老客户：`$100n`。
- **总支出**：`$200n`。

**下一次翻倍**要等 **`50n` 个新客户**（因为机器翻倍，容量也翻倍）。这 `50n` 人必须承担：

- 机器 `$100n`
- 请客 `$100n`
- 自己喝的 `50n` 杯 `$2 × 50n = $100n`
- **合计 `$300n`**

**每人付**：`$300n / 50n = $6`。

**讲义原文（p18）**：「To cover these costs, you need to charge each of them `($100n + $100n + $100n)/50n = $6`.」**与 `n` 无关！**

**寓言与代码的对应（讲义 p18 原文）**：

> **「You may have noticed that this second scenario matches closely the analysis of `uba_add` for unbounded arrays: each new customer corresponds to adding an element to the array, and each coffee corresponds to a token.」**

| 咖啡店 | 无界数组 |
|---|---|
| 新客户 | `uba_add` 一个元素 |
| 一杯咖啡 | 1 个代币（1 次数组写） |
| 咖啡机 | 数组槽位（`limit`） |
| 买机器 | `alloc_array` |
| 请所有老客户 | 复制所有旧元素到新数组 |
| **「满员就加 1 台」** | **「每次 +1 个槽位」** → 摊还 `O(n)`，**错误** |
| **「翻倍才请客」** | **「翻倍扩容」** → 摊还 `O(1)`，**正确** |

**这个寓言的真正价值**：它把「摊还分析」变成了一件**每个小生意人都懂的事**——**「扩张的庆祝成本必须由『扩张带来的新增收入』承担，而不是由『所有人』承担」。** 若你每次都请所有人，那么**客户基数越大，单客成本越高**；若你只在翻倍时请客，**单客成本恒定**。

**`$(4 + 2n)` vs `$6` 的对照是本讲最好的记忆锚点**：**`2n` 那一项就是「线性增长的成本」，它的消失就是「摊还 `O(1)`」。**

### 5.12 习题 6：从哪一步看出「半满缩容」是错的

**习题 6 的问法（p14）**：

> **「We have argued by example why that does not give us constant amortized cost `O(n)` for a sequence of `n` operations. We have also sketched an argument why `L->size <= L->limit/4` gives the right amortized cost. At which step in that argument would you notice that `L->size <= L->limit/2` is the wrong choice?」**

**答案在第 4 步（「证明不变式可恢复」）**：

**若阈值是 `limit/2`**：设在「刚好半满」（`size == limit/2`）时缩容。此时代币数 `2*size - limit = 0`。**缩容要复制 `limit/2` 个元素，需要 `limit/2` 个代币，手里是 0**——**第 4 步（「摊还代价 + 储备 >= 恢复不变式所需」）直接失败**。

**若阈值是 `limit/4`**：缩容发生在 `size == limit/4`，此时代币数 `2*(limit/4) - limit = -limit/2`——**按公式是负数**。**这说明「原来的代币不变式不够用了」**，必须按讲义 p12 说的**扩展不变式**（给「左半部分的空格子」也存代币）。**扩展后，`rem` 每步收的 1 个代币正好攒够 `limit/4` 个**（5.8 的推导），第 4 步通过。

**所以「在哪一步看出来」的答案是**：**第 4 步**。前 3 步（发明代币、定储备、定摊还代价）**都不会报错**——你完全可以给「半满缩容」定一个摊还代价，**只是第 4 步会发现无论定多大都不够**（因为抖动会让 `n` 次操作触发 `n` 次重分配，而每次重分配是 `O(n)`）。

**更本质的说法**：**阈值的选择决定了「储备是否可能为负」。** `limit/4` 时，缩容前已经攒了 `limit/4` 个代币（因为从 `limit/2` 降到 `limit/4` 有 `limit/4` 次 `rem`）；`limit/2` 时，缩容前一个代币都没攒（因为一开始就在 `limit/2`）。**「缓冲带」就是「攒钱的时间」。**

## 6. 代码示例

### 6.1 官方课程代码

以下引自讲义 PDF `11-uba.pdf`，语言为 **C0**（不是标准 C/C++）。`//@` 注解、`\length`、`\result`、`alloc`、`alloc_array` 都是 C0 特有语法；`assert(...)`（不带 `//@`）是**硬断言**，任何编译选项下都执行。

**（1）无界数组的基础接口，第 6 页：**

```c0
// typedef ______* uba_t;
int uba_len(uba_t A)
/*@requires A != NULL; @*/
/*@ensures \result >= 0; @*/;

uba_t uba_new(int size)
/*@requires 0 <= size; @*/
/*@ensures \result != NULL; @*/
/*@ensures uba_len(\result) == size; @*/;

string uba_get(uba_t A, int i)
/*@requires A != NULL; @*/
/*@requires 0 <= i && i < uba_len(A); @*/;

void uba_set(uba_t A, int i, string x)
/*@requires A != NULL; @*/
/*@requires 0 <= i && i < uba_len(A); @*/;
```

**（2）扩展接口 `uba_add` / `uba_rem`，第 6–7 页：**

```c0
void uba_add(uba* A, string x)
/*@requires A != NULL; @*/;

string uba_rem(uba* A)
/*@requires A != NULL; @*/
/*@requires 0 < uba_len(A); @*/;
```

**（3）`uba_header` 的三个字段与内嵌不变式注释，第 7 页：**

```c0
typedef struct uba_header uba;
struct uba_header {
  int size;
  /* 0 <= size && size < limit */
  int limit;
  /* 0 < limit */
  string[] data;
  /* \length(data) == limit */
};
typedef uba* uba_t;
```

**（4）`uba_len`，第 7 页：**

```c0
int uba_len(uba* A)
//@requires is_uba(A);
//@ensures 0 <= \result && \result <= \length(A->data);
{
  return A->size;
}
```

**（5）`is_uba_expected_length` 与 `is_uba`，第 8 页：**

```c0
bool is_uba_expected_length(string[] A, int limit) {
  //@assert \length(A) == limit;
  return true;
}
bool is_uba(uba* A) {
  return A != NULL
      && 0 <= A->size && A->size < A->limit
      && is_uba_expected_length(A->data, A->limit);
}
```

**（6）`uba_add`，第 8–9 页：**

```c0
void uba_add(uba* A, string x)
//@requires is_uba(A);
//@ensures is_uba(A);
{
  A->data[A->size] = x;
  (A->size)++;
  uba_resize(A);
}
```

**（7）`uba_resize`，第 9 页：**

```c0
void uba_resize(uba* A)
//@requires A != NULL && \length(A->data) == A->limit;
//@requires 0 < A->size && A->size <= A->limit;
//@ensures is_uba(A);
{
  if (A->size == A->limit) {
    assert(A->limit <= int_max() / 2);   // Can't handle bigger
    A->limit = A->size * 2;
  } else {
    return;
  }
  //@assert 0 <= A->size && A->size < A->limit;
  string[] B = alloc_array(string, A->limit);
  for (int i = 0; i < A->size; i++)
  //@loop_invariant 0 <= i && i <= A->size;
  {
    B[i] = A->data[i];
  }
  A->data = B;
}
```

**（8）`uba_rem`，第 11 页：**

```c0
string uba_rem(uba* A)
//@requires is_uba(A);
//@requires 0 < uba_len(A);
//@ensures is_uba(A);
{
  (A->size)--;
  string x = A->data[A->size];
  uba_resize(A);
  return x;
}
```

**（9）习题 1 的 `uba_new`，第 13 页：**

```c0
uba* uba_new(int size)
//@requires 0 <= size;
//@ensures is_uba(\result);
//@ensures uba_len(\result) == size;
{
  uba* A = alloc(uba);
  int limit = size == 0 ? 1 : size*2;
  A->data = alloc_array(string, limit);
  A->size = size;
  A->limit = limit;

  return A;
}
```

**（10）n 位计数器的自增模式（讲义文字描述，第 3 页）：**

`10010011` 自增后为 `10010100`——**两个最低的 1 变 0，最右边的 0 变 1**。

**官方代码包**：`90-原始PDF/15-122/code/11-uba.tgz`（原始 URL：`https://cs.cmu.edu/~15122/handouts/code/11-uba.tgz`）。

**配套短视频**：Amortized Analysis —— `https://youtu.be/L8cXZ_4RHt8`（讲义第 1 页列出，本库未收录内容）。

### 6.2 Agent 自行编写的教学示例

> **非官方，仅用于说明概念。** 以下由本笔记自行编写，不是 CMU 官方代码。

**示例 A：逐轮追踪 n 位计数器，验证 `T(k) = 2k - 1`（`k` 为 2 的幂时）。**

4 位计数器，从 `0000` 开始：

| 步 `k` | 自增前 | 自增后 | 翻位数 | 本步代价 | 累计 |
|---|---|---|---|---|---|
| 1 | `0000` | `0001` | 1 | 1 | 1 |
| 2 | `0001` | `0010` | 2 | 2 | 3 |
| 3 | `0010` | `0011` | 1 | 1 | 4 |
| 4 | `0011` | `0100` | 3 | 3 | 7 |
| 5 | `0100` | `0101` | 1 | 1 | 8 |
| 6 | `0101` | `0110` | 2 | 2 | 10 |
| 7 | `0110` | `0111` | 1 | 1 | 11 |
| 8 | `0111` | `1000` | 4 | 4 | **15** |

**`k = 8` 时累计 `15 = 2*8 - 1`。** ✅

**代币账本（每次收 2 个）**：

| 步 | 收 | 花 | 1 的个数 | 储备 |
|---|---|---|---|---|
| 0 | — | — | 0 | 0 |
| 1 | 2 | 1 | 1 | 1 |
| 2 | 2 | 2 | 1 | 1 |
| 3 | 2 | 1 | 2 | 2 |
| 4 | 2 | 3 | 1 | 1 |
| 5 | 2 | 1 | 2 | 2 |
| 6 | 2 | 2 | 2 | 2 |
| 7 | 2 | 1 | 3 | 3 |
| 8 | 2 | 4 | 1 | **1** |

**每行「储备 == 1 的个数」**——**代币不变式在每一步后都成立**。✅ **这就是 5.2 的「第 4 步」的具体验证。**

**注意第 8 步**：`0111 → 1000` 翻了 4 位，**花掉 4 个代币**（原来 3 个 1 各带 1 个，加新收的 2 个中的 1 个），**剩 1 个**（新收的 2 个中另 1 个）——**正好给新的那 1 个 1 位。** 完美对上。

**示例 B：`uba_add` 的代币账本（`limit = 8`，从空开始）。**

| `add` 次数 | `size` | 是否扩容 | 写代价 | 金 | 蓝 | 储备 | `2*size - limit` |
|---|---|---|---|---|---|---|---|
| 0 | 0 | — | — | 0 | 0 | 0 | `0 - 8 = -8` |
| 1 | 1 | 否 | 1 | 1 | 1 | 2 | 负数 |
| 2 | 2 | 否 | 1 | 2 | 2 | 4 | 负数 |
| 3 | 3 | 否 | 1 | 3 | 3 | 6 | 负数 |
| 4 | 4 | 否 | 1 | 4 | 4 | 8 | `8 - 8 = 0` |
| 5 | 5 | 否 | 1 | 5 | 5 | 10 | `10 - 8 = 2` |
| 6 | 6 | 否 | 1 | 6 | 6 | 12 | `12 - 8 = 4` |
| 7 | 7 | 否 | 1 | 7 | 7 | 14 | `14 - 8 = 6` |
| 8 | 8 | **是** | 1 + 复制 8 | 0 | 0 | **0** | `16 - 16 = 0` |

**说明**：

- **`size <= limit/2`（即 `size <= 4`）时，公式 `2*size - limit <= 0`**——**这说明「后半部分已用的格子」为空**，不需要代币。**实际储备是 0**，公式给负数只是代数外推（讲义 p11 的公式只在 `size >= limit/2` 时有效，见第 8 节原文异常）。
- **`size = 5..7` 时**，储备 `= 2*size - 8 = 2, 4, 6`——**与公式一致**。✅
- **第 8 步（扩容）**：`size = 8 = limit`，储备 `2*8 - 8 = 8`——**恰好够复制 8 个元素**。扩容后 `limit = 16`、`size = 8`，储备 `2*8 - 16 = 0`。✅ **归零，进入下一轮。**

**这张表是 5.7 全部论证的具体化**。**注意第 1–4 步「储备为 0」不是浪费**——那时候 `size <= limit/2`，**扩容还远**，不需要存钱。

**示例 C：为什么「半满缩容」会抖动——用具体数字算。**

设 `limit = 8`、`size = 4`（半满）。**假设阈值是 `size <= limit/2` 就缩容**。

| 操作 | `size` | `limit` | 是否重分配 | 代价 |
|---|---|---|---|---|
| 初始 | 4 | 8 | — | — |
| `rem` | 3 | 8 | **是**（`3 <= 4`）→ `limit = 4` | 复制 4 个 |
| `add` | 4 | 4 | **是**（`4 == 4`）→ `limit = 8` | 复制 4 个 |
| `rem` | 3 | 8 | **是**（`3 <= 4`）→ `limit = 4` | 复制 4 个 |
| `add` | 4 | 4 | **是** → `limit = 8` | 复制 4 个 |
| ... | ... | ... | ... | ... |

**每次操作都触发一次 `O(4)` 的复制。** `n` 次操作 `O(4n)`——**在 `limit` 固定时看起来还行**，但**若 `limit` 是 `2m`**（`m` 很大），每次都是 `O(m)`，**`n` 次就是 `O(nm)`**。**这就是「摊还 `O(n)` 而非 `O(1)`」的具体表现。**

**改成四分之一阈值（`size <= limit/4`）**：

| 操作 | `size` | `limit` | 是否重分配 |
|---|---|---|---|
| 初始 | 4 | 8 | — |
| `rem` | 3 | 8 | 否（`3 > 2`） |
| `add` | 4 | 8 | 否 |
| `rem` | 3 | 8 | 否 |
| `add` | 4 | 8 | 否 |
| ... | ... | ... | **永不重分配** |

**抖动完全消失**——**因为 `size` 在 `3` 与 `4` 之间摆动，而阈值是 `2`，永远碰不到。** ✅

**这就是「缓冲带」的作用**：`[limit/4, limit)` 是安全区，`add`/`rem` 在安全区内的任何摆动都**不触发重分配**。

**示例 D：用「通式」快速算任意扩容因子的摊还代价。**

设因子 `f`（`f > 1`），则

```
摊还代价 = f/(f-1) + 1
```

| `f` | `f/(f-1)` | 摊还代价 | 平均浪费比例 `(f-1)/(2f)` |
|---|---|---|---|
| 1.1 | 11 | 12 | `0.1/2.2 ≈ 4.5%` |
| 1.5 | 3 | 4 | `0.5/3 ≈ 16.7%` |
| **1.75** | `7/3 ≈ 2.33` | **`10/3 ≈ 3.33`** | `0.75/3.5 ≈ 21.4%` |
| **2** | 2 | **3** | **25%** |
| 3 | 1.5 | 2.5 | `2/6 ≈ 33.3%` |
| **4** | `4/3 ≈ 1.33` | **`7/3 ≈ 2.33`** | **37.5%** |
| 10 | 1.11 | 2.11 | 45% |
| ∞ | 1 | 2（下界） | 50% |

**读法**：

- **`f` 从 1.1 涨到 2**：摊还代价从 12 降到 3（**降了 4 倍**），浪费从 4.5% 涨到 25%（**涨了 5 倍**）。
- **`f` 从 2 涨到 4**：摊还代价从 3 降到 2.33（**只降 22%**），浪费从 25% 涨到 37.5%（**涨了 50%**）。
- **`f` 再大**：摊还代价趋近 2（**收益递减**），浪费趋近 50%（**代价递增**）。

**故「2 附近」是甜点**——**这也是为什么 Java 选 1.5、C++ 选 2**。**`f = 4` 已经明显不划算：多浪费 12.5% 内存，只换来 22% 的摊还代价下降。**

**示例 E：把「分配也算成本」的摊还账本算一遍（`f = 2`）。**

从 `limit = 2`、`size = 1`、储备 0 开始。

| 阶段 | `size` | `limit` | 本阶段操作数 | 扩容那次代价 | 其余代价 | 阶段总代价 | 每操作摊还 |
|---|---|---|---|---|---|---|---|
| 1 | 1→2 | 2→4 | 1 | 写1 + 分配4 + 复制2 = 7 | 0 | 7 | 7 |
| 2 | 2→4 | 4→8 | 2 | 写1 + 分配8 + 复制4 = 13 | 1 | 14 | 7 |
| 3 | 4→8 | 8→16 | 4 | 写1 + 分配16 + 复制8 = 25 | 3 | 28 | 7 |
| 4 | 8→16 | 16→32 | 8 | 写1 + 分配32 + 复制16 = 49 | 7 | 56 | 7 |

**每阶段摊还代价恒为 7。** ✅ **这就是 5.10 的 `6k+1` 推导的表格化版本**（这里 `k` 是阶段开始时的 `size`：阶段 2 的 `k = 2`，`6k+1 = 13` ✅；阶段 3 的 `k = 4`，`6k+1 = 25` ✅）。

**注意阶段总代价 `= 7k`**（`k` 为该阶段操作数）：`7*1 = 7`、`7*2 = 14`、`7*4 = 28`、`7*8 = 56`。✅ **完美吻合。**

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键区别 | 记忆点 |
|---|---|---|---|
| 摊还分析 | 平均情况分析 | 前者对**任意序列**成立（无运气）；后者是**期望**（可能倒霉） | 「永远如此」vs「通常如此」 |
| 摊还 `O(1)` | 最坏 `O(n)` | **可以同时为真**——回答不同问题 | 单次 vs `k` 次平均 |
| `size` | `limit` | 前者是**逻辑长度**（客户端可见）；后者是**物理容量**（隐藏） | `size < limit` 恒成立 |
| `size < limit`（严格） | `size <= limit` | 前者让 `data[size]` **必然在界内** | 一个字符决定实现形状 |
| `uba_add` 的 `//@ensures is_uba(A)` | 它的**真实后置** | 后者还应含 `uba_len(A) == \old(...) + 1` | 接口不完整 |
| `assert(...)`（硬断言） | `//@assert ...;` | 前者**任何选项下都执行**；后者**只在 `-d` 下** | 防溢出用硬断言 |
| `is_uba_expected_length` | 普通布尔函数 | 前者用 `//@assert` 偷渡 `\length`（**只能放契约里**） | 规格函数的惯用手法 |
| 代币不变式 | `is_uba` 不变式 | 前者**只在头脑中**；后者**写进代码** | 分析工具 vs 运行时检查 |
| 扩容因子 2 | 扩容因子 4 | 前者摊还 3、浪费 25%；后者摊还 2.33、浪费 37.5% | 收益递减，代价递增 |
| 「按倍数」扩容 | 「按固定增量」扩容 | 前者摊还 `O(1)`；后者摊还 `O(n)` | 倍数才收敛 |
| 半满缩容 | 四分之一缩容 | 前者**抖动**（`O(n²)`）；后者摊还 `O(1)` | 缓冲带 = 攒钱时间 |
| `uba_resize` 前置 `size <= limit` | `is_uba` 的 `size < limit` | 前者**故意放宽**（函数内暂时违反） | 内部可违反，出口必修好 |
| `A->data = B`（换指针） | 原地复制回 `A->data` | 前者 `O(1)` + 旧数组变不可达；后者 `O(n)` 且 C0 数组不能变长 | 无界数组的核心技巧 |
| 无界数组 | 链表 | 前者 `O(1)` 访问 + 摊还 `O(1)` 追加；后者 `O(n)` 访问 + 严格 `O(1)` 追加 | 连续内存 vs 指针 |
| 「3 次数组写」 | 「3 次操作」 | 前者是**代币计数**（只算数组写）；后者含指针操作等 `O(1)` 项 | 被数组写支配 |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-122/lectures/11-uba.pdf`
- **讲义标题**：PDF 内页标题为 **"Lecture 11: Unbounded Arrays"**，作者 Rob Simmons、Frank Pfenning。
- **总页数**：19 页
- **本节重点页码**（PDF 页码，即提取文本中 `=== [page N] ===` 的 N）：
  - 第 1 页：开篇；数组 `O(1)` 访问但**大小固定**；链表可扩展但访问 `O(n)`；无界数组**兼得两者**；「Adding (and removing) an element ... has cost either `O(1)` or `O(n)`, but in the long run the average cost of each such operation is constant — **the challenge will be to prove this last statement!**」；三条学习目标；复习幻灯片、代码包、**短视频 Amortized Analysis** 链接
  - 第 2 页：n 位计数器；**单次最坏 `O(n)`，但 `k` 次不必是 `O(kn)`**；两个非形式观察（贵操作越来越稀；第 `k` 步累计 `2k-1`）；**银行/代币比喻**；每次收 2 个、存 1 个
  - 第 3 页：**「1 的个数 == 存款数」**；**元数据不变式（meta data structure invariant）只存在于头脑中**；8 位例 `10010011 → 10010100`；两个代币的用途分解
  - 第 3–4 页：**全 1 溢出的情形**（2 个代币用不上，扔掉）；**四步方法论**；`k` 次自增 `O(k)`、摊还 `O(1)`；**「摊还 `O(1)` 与最坏 `O(n)` 不矛盾」**；**势能法（potential method）** 之名
  - 第 4–5 页：代币不是真的；1 代币 = 1 次数组写；**摊还分析无不确定性**；**与快排平均分析的对比**
  - 第 5–6 页：读文件（莎士比亚全集、Scrabble 词典、推文）的动机；**不知道有多少词 → 无法定长**；`uba_t` 基础接口（`uba_len`/`uba_new`/`uba_get`/`uba_set`）
  - 第 6–7 页：扩展接口 `uba_add`/`uba_rem`；**目标：除 `uba_new` 外全部 `O(1)`**；脚注：**`uba_new(n)` 必然是 `O(n)`**
  - 第 7 页：`uba_header` 三字段 + 内嵌不变式注释；`uba_len`；**「size 严格小于 limit 才能先写后检查」**
  - 第 8 页：`uba_add` 的三行；`is_uba_expected_length`；`is_uba`；配图（内存视图 vs 客户端视图）**未提取**
  - 第 9 页：`uba_resize` 完整代码；**硬断言 `assert(A->limit <= int_max()/2)` 的理由**（防溢出 + 不写进接口）
  - 第 10 页：**摊还分析开始**；1 代币 = 1 次数组写；**金/蓝双色代币不变式**；每次 `uba_add` 预算 3 个；非满情形的保持性
  - 第 10–11 页：**满情形的保持性**（`limit` 个代币付 `limit` 次复制）；**扩容后半满 → 储备 0**；**代币数 `= 2*size - limit`**；结论：摊还 3 次数组写
  - 第 11 页：`uba_rem` 完整代码；**「半满就缩容不行」**（半满时代币为 0）
  - 第 12 页：**改为「少于四分之一才缩容」**；不变式改为 `size ∈ [limit/4, limit)`；**必须扩展代币不变式**（给左半空格子也存代币）；`n` 次操作 `O(n)`
  - 第 13 页：习题 1（`uba_new` 的 `limit` 三元式 + 新成本模型）、习题 2（75% / 300%）、习题 3（为何不用大因子）、习题 4（**咖啡店寓言**）
  - 第 14 页：习题 5（缩容的精确不变式与摊还代价）、习题 6（从哪一步看出半满缩容是错的）
  - 第 15–16 页：习题 1 答案（`size == 0` 时 `limit` 会是 0；最坏 `3n+1`；**六步流程**；8 次 `add` 的图；**摊还 7**；`6(k-1)+7 = 6k+1` 的保持性）
  - 第 17 页：习题 2 答案（75% → `10/3`；300% → `7/3`）；习题 3 答案（**平均浪费 1/4 vs 3/8**；时间—空间权衡）
  - 第 17–18 页：习题 4 答案（策略 A `$(4+2n)`；策略 B `$6`；**「each new customer corresponds to adding an element ... each coffee corresponds to a token」**）
  - 第 18–19 页：习题 5 答案（`uba_rem` 收 1 个代币；最坏情形 `k/2` 次 `rem` 攒够 `k/2` 个；混合序列仍够用；`3k` 个剩余代币的例子）
- **原始网页链接**：`https://www.cs.cmu.edu/~15122-archive/f26/handouts/lectures/11-uba.pdf`
- **配套代码包**：`https://cs.cmu.edu/~15122/handouts/code/11-uba.tgz`（本库已下载为 `90-原始PDF/15-122/code/11-uba.tgz`，**未解压**）
- **复习幻灯片**：`https://cs.cmu.edu/~15122/handouts/slides/review/11-uba.pdf`（本库**未**收录其提取文本，页码待人工核对）
- **配套短视频**：Amortized Analysis —— `https://youtu.be/L8cXZ_4RHt8`（讲义第 1 页列出；本库未收录内容，时长待人工核对）

> **原文异常**：
> 1. **接口与实现里 `uba_t` / `uba*` 混用**：第 6 页接口用 `uba_t`（`uba_len(uba_t A)`、`uba_add` 的声明在第 7 页却写成 `void uba_add(uba* A, string x)`），第 7–12 页的实现全部用 `uba*`。**两者是同一个类型（`typedef uba* uba_t;`），但接口应当统一用 `uba_t`**，否则「抽象」的意图被削弱。同类问题见第 8 页 `is_uba(uba* A)`。
> 2. **第 11 页的代币公式 `2 × size − limit` 只在 `size >= limit/2` 时有效**：当 `size < limit/2` 时该式为**负数**，而「代币数」不可能为负。讲义没有说明「负数按 0 处理」。**严格的写法应是 `max(0, 2*size - limit)`。** 本笔记 6.2 示例 B 的表格里能看到这个负数（`size = 1..3` 时公式给 `-6..-2`）。
> 3. **第 16 页「This is is the amortized number」**——多了一个 `is`，应为「This is the amortized number」。
> 4. **第 13 页习题 1 的代码带行号 `53–65`**：说明它是从某个 `.c0` 文件里截取的片段，**但没有说明是哪个文件**。且代码块内的缩进被提取文本破坏（第 58–64 行参差不齐）。
> 5. **`uba_new` 的 `//@ensures is_uba(\result)` 在 `size == 0` 时依赖 `limit = 1`**：讲义只解释了「否则 `limit` 会是 0」，**没有明说「若 `limit = size`，则 `size < limit` 不成立、`is_uba` 立刻为假」**。这是 `limit = size*2` 的第二个（也是更根本的）理由，讲义省略了。本笔记 5.10 补上了。
> 6. **第 12 页说「it's possible to reﬂect it in the data structure invariant, requiring that `A->size` be in the range `[A->limit/4, A->limit)`」，但没给出修改后的 `is_uba` 代码**。习题 5 要求读者自己写。**且这个新条件与 `uba_resize` 的 `0 < A->size` 前置如何配合，讲义未讨论**（若 `size == 0` 且 `limit == 1`，则 `limit/4 == 0 <= 0`，成立；但若 `limit == 1`、`size == 0` 时调用 `uba_resize`，`size == limit` 为假，会走 `else return`，安全）。
> 7. **第 11 页的 `uba_rem` 没有缩容分支**：`uba_resize` 在 p9 只写了「满则翻倍」，**没有「少于四分之一则减半」的代码**。第 11–12 页讨论了缩容，但**完整实现留给读者**（习题 5）。**读者照抄 p9 的 `uba_resize` 会得到一个「只涨不缩」的数组。**
> 8. **`uba_add` 的 `//@ensures` 只有 `is_uba(A)`**：没有承诺「`size` 加一」或「新元素在末尾」。**接口层面无法证明任何关于内容的性质。** 若客户端想知道「刚加的元素在哪」，接口给不出答案。**这是接口设计的实质缺失，不是笔误。**
> 9. **第 8 页的两张内存/客户端视图配图未被提取**：只剩图注「The images to the left above represent how the data structure is actually stored in memory, and the images in the thought bubbles to the right represent how the client ... can think about the data structure」。**具体图形待人工核对原 PDF。**
> 10. **第 15 页习题 1 答案的「8 次 `add` 的图」未被提取**：只剩「The following picture starts with no tokens in reserve, and a length-2 array containing one element. It goes through eight calls to `uba_add`.」**图中每步的代币数无法核对。**
> 11. **第 3 页的「increment 示意图」未被提取**：只剩「Graphically, any time we increment the counter, it looks like this:」。
> 12. **第 1 页「retrieved in `O(1)` time? What gives?」的标点是修辞性问号**，但前后文是陈述句，**读起来像排版错误**（应为「in `O(1)` time. What gives?」）。**不影响理解。**

## 9. 对应视频

未找到官方公开录像。**但讲义第 1 页列出了一个配套短视频**：**Amortized Analysis —— `https://youtu.be/L8cXZ_4RHt8`**（本库未收录其内容，时长与讲解范围待人工核对）。除此之外没有完整的课堂录像。

建议的动手顺序：(1) 用 6.2 示例 A 的 4 位计数器手算 8 步，**在纸上画代币账本**，亲眼看到「储备 == 1 的个数」每一步都成立；(2) 在 `coin` 里实现 `uba_add`/`uba_resize`，**在每次扩容时打印 `size`/`limit`**，跑 100 次 `add`，数一数扩容了几次（应该是 `log2(100) ≈ 7` 次）；(3) 把扩容因子改成 1.1（`limit = size + size/10`），**再跑 100 次**，观察扩容次数从 7 次涨到几十次——**这就是「小因子多扩容」的直观感受**；(4) 把扩容因子改成「每次 +1」（`limit = size + 1`），跑 10000 次 `add`，**观察它变成 `O(n²)`**；(5) 实现缩容，先用「半满」阈值，写一个 `add`/`rem` 交替的循环，**打印每次的 `limit`**，你会看到 `limit` 疯狂抖动；改成「四分之一」后抖动消失；(6) 把 `assert(A->limit <= int_max()/2)` 注释掉，然后想办法让 `limit` 接近 `int_max()`（可以先手动把 `limit` 设成一个很大的值），**观察溢出后 `alloc_array` 拿到负数会怎样**。

## 10. 本节复习

1. 数组 `O(1)` 访问但大小固定；链表可扩展但访问 `O(n)`；**无界数组兼得两者**，代价是「偶尔 `O(n)`」。
2. **摊还分析**证明「任意序列的累计代价 `<=` 摊还代价之和」；**不是期望**，**没有运气**。
3. 摊还 `O(1)` 与最坏 `O(n)` **可以同时为真**。
4. n 位计数器：单次最坏 `O(n)`，但 `k` 次总计 `< 2k`（第 `k` 步最贵时恰好 `2k-1`）。
5. **四步方法论**：发明代币 → 定储备不变式 → 定每个操作的摊还代价 → 证明不变式可恢复。
6. 计数器的代币不变式：**「1 的个数 == 存款数」**；它**只存在于头脑中**，不写进代码。
7. 计数器每次收 2 个代币：1 个付「0 变 1」，1 个存给这个新 1。
8. 全 1 溢出时**扔掉** 2 个新代币（不变式仍可恢复）。
9. `uba_header` = `size`（逻辑长度）+ `limit`（容量）+ `data`（长度 `limit` 的数组）。
10. **`size < limit` 必须严格**——否则 `A->data[size]` 越界，`uba_add` 不能「先写后修」。
11. `is_uba` = `A != NULL && 0 <= size && size < limit && \length(data) == limit`。
12. `is_uba_expected_length` 用 `//@assert` **偷渡 `\length`**（`\length` 只能出现在契约里）。
13. `uba_add` 三行：写 `data[size]` → `size++` → `uba_resize`。
14. `uba_resize`：满则 `limit = size*2`；**硬断言防溢出**；`alloc_array` 新数组 + 复制 + **换指针**。
15. **`assert` 任何选项下都执行；`//@assert` 只在 `-d` 下执行。** 防溢出必须用前者。
16. 扩容后**恰好半满、代币归零**——这是「3 个代币刚好够」的标志。
17. **金/蓝双色代币**：金色给后半部分已用格子，蓝色给前半部分对应格子；总数 `= 2*size - limit`。
18. `uba_add` 摊还 **3 次数组写**：1 付写、1 金、1 蓝。
19. **缩容必须等到四分之一**：半满时代币为 0，付不起；且会抖动。
20. 新不变式：`size ∈ [limit/4, limit)`；**代币不变式也要扩展**（给左半空格子存代币）。
21. `uba_rem` 摊还 **1 个代币**；最坏情形 `k/2` 次 `rem` 恰好攒够 `k/2` 个。
22. 摊还通式：因子 `f` → 代价 `f/(f-1) + 1`；平均浪费 `(f-1)/(2f)`。
23. 因子 2 → 3 个代币、浪费 25%；因子 1.75 → `10/3`、21.4%；因子 4 → `7/3`、37.5%。
24. **「按倍数」是摊还 `O(1)` 的充要条件**；「按固定增量」是 `O(n)`。
25. 把**分配**也算成本后，摊还代价从 3 涨到 **7**（最坏单次 `3n+1`）。
26. 咖啡店寓言：**每次满员请客 → `$(4+2n)`（随 `n` 涨）；每次翻倍请客 → `$6`（恒定）**。
27. 「半满缩容错在哪一步」的答案是**第 4 步**（不变式不可恢复），前 3 步都不会报错。
28. `uba_resize` 前置 `0 < size` 是为了**防止缩容到 `limit = 0`**。

## 11. 自我检查

**题 1.** 8 位计数器从 `00000000` 开始自增 12 次。写出第 12 次自增前/后的值、这次翻了几位，并验证累计代价是否仍满足 `< 2k`。用代币账本说明第 12 步后储备是多少。

**题 2.** 为什么 `is_uba` 要求 `size < limit` 而不是 `size <= limit`？如果改成 `<=`，`uba_add` 的实现必须怎么改？

**题 3.** `limit = 8`、`size = 7` 时，按金/蓝代币不变式，储备是多少个代币？下一次 `uba_add` 会触发扩容，扩容时代价是多少、代币够不够？扩容后 `limit` 与储备各是多少？

**题 4.** 用通式 `f/(f-1) + 1` 算出扩容因子 `f = 1.5` 与 `f = 8` 的摊还代价，并用「平均浪费比例」公式说明为什么不该选 `f = 8`。

**题 5.** 为什么不能在「半满」时缩容？请分别从「代币够不够」与「抖动」两个角度回答，并说明为什么「四分之一」能同时解决两个问题。

<details>
<summary>参考答案</summary>

**答 1.**

12 次自增后计数器是 `00001100`（十进制 12）。**第 12 次自增**是 `00001011 → 00001100`：

- 自增前 `00001011`（十进制 11）。
- 自增后 `00001100`（十进制 12）。
- **翻了 3 位**：最低两位的 `11` 变 `00`，第三位的 `0` 变 `1`。

**累计代价**：前 12 次的总代价

```
T(12) = 12 + floor(12/2) + floor(12/4) + floor(12/8)
      = 12 + 6 + 3 + 1 = 22
```

**验证 `< 2k = 24`**：`22 < 24` ✅

**代币账本**：每次收 2 个，共收 `24` 个；花掉 `22` 个；**储备 `= 24 - 22 = 2` 个**。

**核对不变式**：`00001100` 有 **2 个 1 位**，储备应为 2。✅ **完美吻合。**

**答 2.** **为什么必须严格 `<`**：`uba_add` 的第一行是 `A->data[A->size] = x`。**这个写操作要求 `size < \length(data) == limit`**。若允许 `size == limit`，则 `A->data[limit]` **越界**，C0 会报 `Error: accessing element ... in ...-element array`（[[15-122-03-Arrays]]）。

**改成 `<=` 后 `uba_add` 必须怎么改**：

```c0
void uba_add(uba* A, string x)
//@requires is_uba(A);
//@ensures is_uba(A);
{
  if (A->size == A->limit) {     // 必须先检查
    uba_resize(A);               // 先扩容
  }
  A->data[A->size] = x;          // 再写（此时保证 size < limit）
  (A->size)++;
}
```

**代价**：

1. **多一次比较**（`size == limit`）——虽然 `O(1)`，但每次 `add` 都付。
2. **`uba_resize` 的语义必须改**：它现在要处理「`size == limit` 但**还没写**」的情形，故前置 `0 < A->size` 在 `size == 0` 时**不成立**——空数组第一次 `add` 时 `size == limit == 0`，`uba_resize` 的 `0 < A->size` **失败**。得再加特判。
3. **`limit = 0` 的数组无法写入**——`uba_new(0)` 若给 `limit = 0`，第一次 `add` 就卡住。

**结论**：**「严格小于」这个不变式让 `uba_add` 保持三行、无条件写、把判断全部推给 `uba_resize`。** 这是「不变式的一个字符决定实现形状」的最佳例证。**代价是 `uba_new` 必须给 `limit >= size + 1`（讲义用 `size*2`，既满足又留出空间）。**

**答 3.** `limit = 8`、`size = 7`。

**储备（金/蓝代币）**：

- **后半部分已用格子**：`i ∈ [limit/2, size) = [4, 7) = {4, 5, 6}`，共 **3 个** → 3 个金色代币。
- **前半部分对应格子**：`i - limit/2 ∈ [0, 3) = {0, 1, 2}`，共 **3 个** → 3 个蓝色代币。
- **总储备 `= 6` 个代币**。

**用公式核对**：`2*size - limit = 2*7 - 8 = 6`。✅

**下一次 `uba_add`**：写 `data[7]`（1 个代币），`size` 变 8，**`size == limit` 触发扩容**。

**扩容代价**：复制 8 个元素 = **8 个代币**。

**够不够**：手里 6 个 + 本次 `add` 收 3 个 = **9 个**；花 1 个（写）+ 8 个（复制）= **9 个**。**恰好够，剩 0。** ✅

**扩容后**：`limit = 16`、`size = 8`。

**新储备**：`2*8 - 16 = 0`。✅ **归零，进入下一轮。**

**这个例子展示了「3 个代币刚好够」的精确性**：`size = 7` 是扩容前的最后一格，此时储备 6 + 新收 3 = 9，恰好等于「1 写 + 8 复制」。**少一个代币就破产。**

**答 4.**

**`f = 1.5`**：

```
摊还代价 = 1.5/(1.5-1) + 1 = 1.5/0.5 + 1 = 3 + 1 = 4
平均浪费 = (1.5-1)/(2*1.5) = 0.5/3 ≈ 16.7%
```

**`f = 8`**：

```
摊还代价 = 8/(8-1) + 1 = 8/7 + 1 ≈ 1.14 + 1 = 2.14
平均浪费 = (8-1)/(2*8) = 7/16 = 43.75%
```

**为什么不该选 `f = 8`**：与 `f = 2`（摊还 3、浪费 25%）相比，`f = 8` 的摊还代价只从 3 降到 2.14（**降 29%**），但浪费从 25% 涨到 **43.75%（涨 75%）**。

**收益递减的原因**：摊还代价 `f/(f-1) + 1` 的**下界是 2**（`f → ∞`）。`f` 从 2 涨到 8，`f/(f-1)` 从 2 降到 1.14，**已经接近下界 1**；再增大 `f` 最多再降 0.14。

**代价递增的原因**：平均浪费 `(f-1)/(2f)` 的**上界是 50%**。`f = 8` 已经到 43.75%，**再增大就逼近「一半内存永远空着」**。

**结论**：**`f` 在 1.5–2 附近是甜点。** `f` 太小（如 1.1）→ 摊还代价 12，扩容太频繁；`f` 太大（如 8）→ 浪费近半内存，收益却只有 0.86 个代币。**Java 的 `ArrayList` 用 1.5、C++ 的 `vector` 用 2，都是这个权衡的产物。**

**答 5.**

**角度一：代币够不够**。

设数组**刚好半满**：`size == limit/2`。按公式 `2*size - limit = 2*(limit/2) - limit = 0`。**储备为 0 个代币。**

缩容要**复制 `size = limit/2` 个元素**到新的 `limit/2` 长数组，需要 `limit/2` 个代币。**手里 0 个**——**第 4 步（「摊还代价 + 储备 >= 恢复不变式所需」）直接失败**。

**即使把 `rem` 的摊还代价定得再大也没用**：因为「刚好半满」是**缩容的触发点**，而**触发那一刻储备必须是 0**（公式决定），**没有任何「攒钱的时间」**。

**角度二：抖动（thrashing）**。

设 `limit = 2k`、`size = k`。若阈值是 `size <= limit/2`：

| 操作 | 结果 |
|---|---|
| `rem` | `size = k-1 <= k` → 缩容到 `limit = k`，复制 `k` 个 |
| `add` | `size = k == limit` → 扩容到 `limit = 2k`，复制 `k` 个 |
| `rem` | 又缩容，复制 `k` 个 |
| `add` | 又扩容，复制 `k` 个 |

**每次操作都是 `O(k)`。** `n` 次操作 `O(nk)`——**若 `k = Θ(n)`，就是 `O(n²)`**。**摊还 `O(1)` 完全失效。**

**为什么「四分之一」同时解决两个问题**：

**解决代币问题**：从「半满」降到「四分之一满」需要 **`limit/4` 次 `rem`**，每次收 1 个代币 → **攒够 `limit/4` 个**。而缩容要复制 `limit/4` 个元素（因为此时 `size = limit/4`）→ **恰好够**。

**解决抖动问题**：缩容后 `limit' = limit/2`、`size = limit/4 = limit'/2`——**新数组半满**。要再触发缩容，得先降到 `limit'/4 = limit/8`；要触发扩容，得先涨到 `limit' = limit/2`。**两者之间隔了 `limit/8` 到 `limit/2` 的缓冲带**，`add`/`rem` 的任意摆动都困在里面。

**一句话总结**：**「缓冲带」就是「攒钱的时间」，也是「防抖动的空间」。** 阈值 `1/4` 让这两件事恰好同时成立——**这就是为什么不是 `1/3` 也不是 `1/5`**（`1/4` 让「缩容后的半满」与「扩容后的半满」完全对称）。

</details>

## 12. 进一步学习

- 上一讲：[[15-122-10-Linked-Lists]] —— 用**指针**实现可扩展容器：`push` 严格 `O(1)`，但每个元素多一个指针、缓存局部性差。本讲用**连续数组 + 摊还**实现同一目标：访问 `O(1)`、追加摊还 `O(1)`、单次可能 `O(n)`。**两条路各有取舍，讲义开篇的矛盾在这里得到完整回答。**
- 下一讲：[[15-122-12-Hashing]] —— 另一个抽象类型（集合/字典），同样面临「数组 vs 链表」的选择：**哈希表就是「数组 + 链表」的混合体**（链地址法）。
- 相关讲次：[[15-122-05-Big-O]]（`O(1)` 与「忽略常数因子」是本讲摊还分析的语言）、[[15-122-07-Quicksort]]（**平均情况分析**的对照物）、[[15-122-03-Arrays]]（`alloc_array` 与越界检查）。
- 课程入口：[[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]]、[[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 术语查询：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Unbounded Array、Amortized Analysis、Amortized Cost、Potential Method、Token、Load Factor、Capacity 等条目）。
- 延伸阅读：Michael Sipser 的《Introduction to the Theory of Computation》不涉及此话题；更相关的是 **Robert Sedgewick 的《Algorithms》** 中「resizing arrays」一节，以及 **Cormen et al. 《Introduction to Algorithms》第 17 章「Amortized Analysis」**（讲三种方法：聚合分析、记账法、势能法——本讲的「代币法」就是记账法，「势能法」是它的别名）。
