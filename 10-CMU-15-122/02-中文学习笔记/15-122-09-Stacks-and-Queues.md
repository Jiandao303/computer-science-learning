---
course: CMU 15-122
course_name: Imperative Computation
semester: Fall 2026
lecture_id: L09
topic: Stacks and Queues
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-122
  - 栈与队列
  - C0
---

# 第 9 讲：栈与队列（Stacks and Queues）

## 1. 本节学习目标

学完本讲后，你应该能够：

1. 用 **LIFO**（后进先出）与 **FIFO**（先进先出）分别刻画栈与队列，并各举两个真实应用。
2. 写出 `stack_t` 与 `queue_t` 两个**抽象类型**的完整接口（四个函数 + 契约 + `O(1)` 标注）。
3. 说明为什么 `pop`/`deq` 的前置必须包含 `!stack_empty(S)` / `!queue_empty(Q)`，而 `push` 只需 `S != NULL`。
4. 在**不违反抽象**的前提下，用 `pop` + `push` 实现 `peek`，并说明为什么它仍是 `O(1)`。
5. 写出 `stack_size` 的**破坏性**版本与**非破坏性**版本，说明后者的两阶段结构与 `O(n)` 复杂度。
6. 解释 `queue_t C = Q;` 为什么**不是**复制（别名），以及为什么「读一个、写回一个」的复制尝试**不终止**。
7. 推导出 `queue_copy` 必须借助**第三个队列** `T`，并说明两阶段各自的断言。
8. 找出 `stack_copy` 初版「返回逆序」的 bug 并修正。
9. 用「辅助栈 + 循环不变式」实现 `stack_sort`，说明为什么它是 `O(n²)`。
10. 解释**纯性（purity）**为什么使 `stack_sorted_ascending` **不能**出现在 `//@loop_invariant` 里，以及这会导致「带 `-d` 与不带 `-d` 结果不同」。
11. 用递归实现 `stack_size`，并说明为什么递归版比迭代版短——**调用栈本身就是那个临时栈**。

## 2. 前置知识

- [[15-122-08-Libraries]]：抽象类型、接口与实现分离、`typedef ______* ssa_t;`、数据结构不变式、客户端视角 vs 库视角、纯性。
- [[15-122-01-Contracts]]：`requires`/`ensures`/`loop_invariant`/`assert`；契约必须纯。
- [[15-122-05-Big-O]]：`O(1)` 与 `O(n)`；为什么「常数次操作」的循环体 + `n` 轮 = `O(n)`。
- [[15-122-03-Arrays]]：别名（`G = F` 同址）——本讲 `queue_t C = Q;` 是同一现象在抽象类型上的重演。
- [[15-122-07-Quicksort]]：`is_permutation` 因分配内存而不纯、只能放 `assert(...)`；本讲的 `stack_sorted_ascending` 是同一类问题。

## 3. 核心概念

**Stack（栈）**：只在**一端**（栈顶，top）插入与删除的数据结构。后进先出。

**LIFO（Last In First Out，后进先出）**：最后压入的元素最先被取出。

**push（压栈）**：把元素加到栈顶。

**pop（弹栈）**：取出并删除栈顶元素。

**peek（查看栈顶）**：读出栈顶元素但**不删除**。本讲中它不是接口的一部分，而是客户端用 `pop`+`push` 合成的。

**Queue（队列）**：在**一端**（队尾，back）插入、在**另一端**（队首，front）删除的数据结构。先进先出。

**FIFO（First In First Out，先进先出）**：最先入队的元素最先被取出。

**enq / deq（入队 / 出队）**：`enq` 在队尾加元素，`deq` 从队首取走元素。

**Abstraction（抽象）**：客户端**只能**使用接口里的函数，**不许**知道也不许使用实现的细节。讲义原话：**「we are not permitted to use or even know about details of the implementation」**。

**Destructive Operation（破坏性操作）**：会改变输入数据结构的操作。`pop`/`deq` 都是破坏性的；本讲大量技巧都是在「只能用破坏性操作」的前提下**恢复**原状。

**Alias（别名）**：两个变量指向同一块内存。`queue_t C = Q;` 让 `C` 与 `Q` 成为别名。

**Purity（纯性）**：函数不分配、不修改已分配内存。只有纯函数能出现在 `//@` 契约里。

## 4. 通俗理解

**栈 = 桌上的一摞纸**。新纸放最上面，取纸也从最上面取。你**永远碰不到**中间那张，除非先把上面的都拿走。讲义原文：「They operate like a stack of papers or books on our desk」。

**队列 = 排队买饭**。后来的人站队尾，先来的人先买到。讲义原文：「a queue is like 'waiting in line'」。

**为什么这两个结构值得单独一讲**：它们的**接口几乎一模一样**（都是「加一个、删一个、看空不空、新建」），唯一的区别是**删除发生在哪一端**。**接口相同、行为不同**——这正是抽象类型设计的精髓：客户端代码的形状完全一样，语义却截然不同。

**为什么 `peek` 要绕这么大一圈**：如果你知道栈是用数组实现的，`peek` 就是 `S->data[S->top]` 一行。**但客户端不该知道这件事。** 讲义用一个漂亮的手法解决：**pop 出来、存到临时变量、再 push 回去**。净效果是「什么都没变」，但客户端只用了接口里的两个函数。

**为什么这个「绕路」是可接受的**：讲义说得很清楚——**只要 `push` 与 `pop` 是 `O(1)`，`peek` 就是 `O(1)`**。三个 `O(1)` 操作串起来还是 `O(1)`。**抽象有代价，但代价是常数因子，不是复杂度阶。**

**为什么 `stack_size` 是个难题**：栈的接口**故意不提供长度**。你只能一个一个 pop 出来数。但数完栈就空了——**「测量」破坏了「被测对象」**。这正是量子力学式的困境，解法是「量完再装回去」。

**为什么复制队列要三个队列**：这是本讲最精彩的一段。第一次尝试（读 `Q` 写 `C`）成功了，但 `Q` 被清空了。第二次尝试（读一个、写回一个）**死循环**——因为你每拿走一个就往回放一个，队列长度永远不变。**必须**先把元素搬到第三个地方暂存，再从那里同时补给 `C` 和 `Q`。讲义用两次「Before you read on, can you find out which problem?」逼你自己撞墙，然后才给答案。

**为什么递归版 `stack_size` 这么短**：因为它**不需要显式的临时栈**——**递归的调用栈就是那个临时栈**。每次递归调用「记得」自己 pop 出来的那个元素，返回时再 push 回去。讲义原文：「Each call to `stack_size` 'remembers' the data item it pops」。

## 5. 原理与推导

### 5.1 用「序列」给栈与队列建模

把栈写成一个序列：

```
S = x1, x2, ..., xn
```

`x1` 是**栈底**，`xn` 是**栈顶**。三个操作对序列的作用：

| 操作 | 序列变化 | 代价 |
|---|---|---|
| `push(S, x)` | `x1, ..., xn` → `x1, ..., xn, x` | `O(1)` |
| `pop(S)` | `x1, ..., xn` → `x1, ..., xn-1`，返回 `xn` | `O(1)` |
| `stack_empty(S)` | 判断 `n == 0` | `O(1)` |

队列：

```
Q = x1, x2, ..., xn
```

`x1` 是**队首**（front），`xn` 是**队尾**（back）。

| 操作 | 序列变化 | 代价 |
|---|---|---|
| `enq(Q, e)` | `x1, ..., xn` → `x1, ..., xn, e` | `O(1)` |
| `deq(Q)` | `x1, ..., xn` → `x2, ..., xn`，返回 `x1` | `O(1)` |

**关键对比**：`push` 与 `enq` **完全相同**（都在右端追加）。区别只在删除端：`pop` 删右端，`deq` 删**左端**。**「同样的入、不同的出」是这两个结构的全部差别。**

**为什么 `deq` 也是 `O(1)` 却更难以实现**：删左端意味着所有元素都要「往前挪」——如果用朴素数组，`deq` 会是 `O(n)`。**这个问题留到下一讲**（本讲只谈接口，不谈实现）。讲义明说：「Today we will not talk about the implementation of stacks and queues; we will implement them in the next lecture.」

### 5.2 `stack_t` 接口与每条契约的理由

```c0
// typedef ______* stack_t;
bool stack_empty(stack_t S)
/* O(1), check if stack empty */
/*@requires S != NULL; @*/;

stack_t stack_new()
/* O(1), create new empty stack */
/*@ensures \result != NULL; @*/
/*@ensures stack_empty(\result); @*/;

void push(stack_t S, string x)
/* O(1), add item on top of stack */
/*@requires S != NULL; @*/
/*@ensures !stack_empty(S); @*/;

string pop(stack_t S)
/* O(1), remove item from top */
/*@requires S != NULL; @*/
/*@requires !stack_empty(S); @*/;
```

**逐条理由**：

| 契约 | 为什么需要 |
|---|---|
| `stack_empty`: `S != NULL` | 栈是**可变**的抽象类型，用指针表示；解引用前必须非空（见 [[15-122-08-Libraries]] 5.3） |
| `stack_new`: `\result != NULL` | `alloc` 从不返回 `NULL`，但**接口必须承诺**，否则客户端无法证明 `stack_empty(\result)` 安全 |
| `stack_new`: `stack_empty(\result)` | 新建的栈**必须**是空的——这是「新建」的全部语义 |
| `push`: `S != NULL` | 同上 |
| `push`: `!stack_empty(S)` | 压栈后**必然非空**——这是客户端唯一能拿到的「正向信息」 |
| `pop`: `S != NULL` **与** `!stack_empty(S)` | **这是本讲最重要的契约**：空栈不能 pop |

**为什么 `pop` 的空栈前置如此重要**：讲义说这是「a fundamental aspect of the interface」——**客户端只能从非空栈读数据**。若没有这条前置，`pop` 在空栈上的行为就无法定义（返回什么？报错？），而**接口必须让每个调用都可判定安全**。

**注意 `push` 有后置而 `pop` 没有**：`push` 之后栈**必然**非空，这是个确定的事实；`pop` 之后栈**可能**空也可能不空，接口**故意不承诺**任何关于剩余元素的信息。**「接口只说它敢保证的」**——这与 [[15-122-08-Libraries]] 里 `ssa_set` 故意不承诺「写入的值还在原处」是同一种克制。

**`typedef ______* stack_t;` 的星号**：与 `ssa_t` 一样，`stack_t` 是**未知的指针类型**。理由也一样——栈是**可变**的，必须能通过它修改内存，所以必须是指针。讲义原文：「we will again be explicit in the interface that stacks are pointers to allocated memory, though we won't be explicit about what they point to.」

**为什么接口里没有 `stack_size`**：讲义把它留作**客户端的练习**（第 4 节），并说明「A library-side implementation of `stack_size` can be done in `O(1)`」——**但库侧能做的 `O(1)` 版本不属于接口**，因为接口要隐藏「栈里有个计数字段」这个实现细节。**这是一个刻意的设计取舍**：把性能留给实现者，把可移植性留给客户端。

**元素类型是 `string`**：讲义坦白这是**简化**——「there's nothing special about the `string` type here」。泛型（generic）留到后面讲。

### 5.3 `queue_t` 接口

```c0
// typedef ______* queue_t;
bool queue_empty(queue_t Q)
/* O(1) */
/*@requires Q != NULL; @*/;

queue_t queue_new()
/* O(1) */
/*@ensures \result != NULL; @*/
/*@ensures queue_empty(\result); @*/;

void enq(queue_t Q, string e)
/* O(1) */
/*@requires Q != NULL; @*/;

string deq(queue_t Q)
/* O(1) */
/*@requires Q != NULL; @*/
/*@requires !queue_empty(Q); @*/;
```

**与栈接口逐项对照**：

| 栈 | 队列 | 差别 |
|---|---|---|
| `stack_empty(S)` | `queue_empty(Q)` | 无 |
| `stack_new()` | `queue_new()` | 无 |
| `push(S, x)`，后置 `!stack_empty(S)` | `enq(Q, e)`，**无后置** | **不对称** |
| `pop(S)`，前置 `!stack_empty(S)` | `deq(Q)`，前置 `!queue_empty(Q)` | 无 |

**`enq` 缺少 `!queue_empty(Q)` 的后置**：这是讲义的一处**不对称**。逻辑上 `enq` 之后队列**必然**非空（与 `push` 完全一样），这条后置**本可以也本应该**写上。**不影响正确性，但削弱了客户端的推理能力**——若客户端想写「`enq` 之后循环守卫一定为真」，它得自己想办法。

**为什么两个接口的「形状」完全一样**：因为两者都是「单端插入 + 单端删除」的容器。**形状相同、语义不同**，这正是抽象类型的力量——**你可以把用栈写的代码改成用队列，只改类型名与函数名，语义就从 LIFO 变成 FIFO**。讲义开篇说「They follow similar principles of organizing the data ... But they differ in terms of the order in which the elements are removed.」

### 5.4 抽象的纪律：`peek` 的两种写法

**违规写法**（讲义 p4 明确标注为「if we knew how stacks were implemented」）：

```c0
string peek(stack_t S)
//@requires is_stack(S) && !stack_empty(S);
{
  return S->data[S->top];
}
```

**两处违规**：

1. **`S->data`、`S->top`**：`stack_t` 是抽象类型，客户端**不知道**它有字段。即使实现里真有这两个字段，客户端也不许碰。
2. **`is_stack(S)`**：这是**库侧的数据结构不变式**，与 `ssa` 的 `is_ssa` 一样，**不属于接口**（见 [[15-122-08-Libraries]] 5.11）。

**合规写法**：

```c0
string peek(stack_t S)
//@requires S != NULL && !stack_empty(S);
{
  string x = pop(S);
  push(S, x);
  return x;
}
```

**正确性推导**（用 5.1 的序列模型）：

- 入口：`S = x1, ..., xn`，`n >= 1`（由 `!stack_empty(S)`）。
- `pop(S)`：返回 `xn`，`S` 变成 `x1, ..., xn-1`。`x = xn`。
- `push(S, x)`：`S` 变成 `x1, ..., xn-1, xn`。**与入口完全相同。**
- `return x`：返回 `xn`——**正是栈顶**。

**净效果为零**：序列在函数返回时与调用时**逐元素相同**。这就是「非破坏性读取」的全部秘密。

**复杂度**：`pop` 是 `O(1)`、`push` 是 `O(1)`、赋值与返回是 `O(1)`，故 `peek` 是 `O(1)`。讲义原文：「as long as `push` and `pop` are still a constant-time operations, `peek` will still be constant time (`O(1)`).」

**为什么这可能比库侧实现慢**：库侧的 `peek` 只读一个字段，客户端的 `peek` 要做两次函数调用 + 两次内存写。**但都是常数**——`O(1)` 与 `O(1)` 之间只差常数因子，而 [[15-122-05-Big-O]] 的第一条原则就是**忽略常数因子**。**这正是大 O 记号让「抽象」在性能上可接受的原因。**

### 5.5 `stack_size`：破坏性版本

```c0
int stack_size(stack_t S)
//@requires S != NULL;
//@ensures \result >= 0;
{
  int count = 0;
  while (!stack_empty(S)) {
    pop(S);
    count++;
  }
  return count;
}
```

**正确性**（循环不变式）：

```
//@loop_invariant count >= 0;
//@loop_invariant count + <S 中元素个数> == n0;
```

其中 `n0` 是入口时的元素个数。**这是一个「守恒式」不变式**：`count` 增加多少，`S` 就减少多少，总和不变。

- **INIT**：`count = 0`，`S` 有 `n0` 个元素，`0 + n0 == n0`。成立。
- **PRES**：`pop` 让 `S` 少一个，`count++` 让 `count` 多一。和不变。
- **EXIT**：`stack_empty(S)` 为真，即 `S` 有 0 个元素，故 `count == n0`。

**问题**：**这个函数把栈毁了**。讲义原文：「in order to compute the size we have to destroy the stack!」**返回值是对的，但副作用不可接受。**

### 5.6 `stack_size`：非破坏性版本（两阶段）

```c0
int stack_size(stack_t S)
//@requires S != NULL;
//@ensures \result >= 0;
{
  stack_t T = stack_new();
  int count = 0;
  while (!stack_empty(S)) {
    push(T, pop(S));
    count++;
  }
  while (!stack_empty(T)) {
    push(S, pop(T));
  }
  return count;
}
```

**为什么这能「修复」**：把元素**依次**搬到 `T`，再从 `T` **依次**搬回 `S`。**两次反转 = 一次还原。**

**推导**：设入口 `S = x1, ..., xn`（`x1` 底、`xn` 顶）。

**第一阶段**（`n` 轮）：

| 轮 | 从 `S` 弹出 | `T` 的变化（底→顶） |
|---|---|---|
| 1 | `xn` | `xn` |
| 2 | `xn-1` | `xn, xn-1` |
| ... | ... | ... |
| `n` | `x1` | `xn, xn-1, ..., x1` |

**结束时**：`S` 空，`T = xn, xn-1, ..., x1`（**恰好是 `S` 的逆序**），`count == n`。

**第二阶段**（`n` 轮）：从 `T` 依次弹出 `x1, x2, ..., xn`（因为 `T` 的顶是 `x1`），压入 `S`：

| 轮 | 从 `T` 弹出 | `S` 的变化（底→顶） |
|---|---|---|
| 1 | `x1` | `x1` |
| 2 | `x2` | `x1, x2` |
| ... | ... | ... |
| `n` | `xn` | `x1, x2, ..., xn` |

**结束时**：`T` 空，`S = x1, ..., xn`——**与入口完全相同**。

**「两次反转 = 还原」是本讲反复出现的核心技巧**：5.8 的 `stack_copy`、5.10 的 `queue_copy`、5.12 的 `stack_sort` 全都建立在它上面。**记住这一条，本讲一半的题都能推出来。**

**复杂度**：两个循环各 `n` 轮，每轮常数次 `O(1)` 操作 → **`O(n)`**。讲义原文：「The complexity of this function is clearly `O(n)` ... For that, we need to know that `push` and `pop` are constant time (`O(1)`).」

**注意这句「For that, we need to know...」**：`O(n)` 的结论**依赖接口上的 `O(1)` 承诺**。若某天实现改成 `pop` 是 `O(n)`，这个客户端函数就变成 `O(n²)`。**接口的复杂度标注是契约的一部分。**

### 5.7 复制队列：第一次尝试（成功但破坏）

```c0
queue_t C = queue_new();
while (!queue_empty(Q)) {
  enq(C, deq(Q));
}
//@assert queue_empty(Q);
```

**先看为什么 `queue_t C = Q;` 不行**：这只是**别名**——`C` 与 `Q` 指向同一个队列对象。往 `C` 里 `enq` 一个元素，`Q` 里也会多一个。**这与 [[15-122-03-Arrays]] 里 `G = F` 让两个数组变量同址是同一个现象**，只是从数组升级到了抽象类型。

**第一次尝试的正确性**：`deq` 从 `Q` 队首取出，`enq` 加到 `C` 队尾。取出顺序 = 入队顺序 = `Q` 的原始顺序，故 `C` 的元素顺序与 `Q` 原顺序**完全一致**。**复制本身是对的。**

**问题**：`Q` 被清空了。末尾那句 `//@assert queue_empty(Q);` 是**故意**写在那里的——它不是「成功标志」，而是**「破坏的证据」**。

### 5.8 第二次尝试：为什么必然死循环

```c0
queue_t C = queue_new();
while (!queue_empty(Q)) {
  string s = deq(Q);
  enq(Q, s);
  enq(C, s);
}
//@assert queue_empty(Q);
```

**想法**：「读一个、放回一个、复制一个」——`Q` 应该保持原样。

**致命缺陷**：**循环不终止**。

**证明**：设 `|Q|` 表示 `Q` 中元素个数。循环体每轮：

- `deq(Q)`：`|Q| -= 1`
- `enq(Q, s)`：`|Q| += 1`

**净变化为 0**。故 `|Q|` 在整个循环中**恒等于入口值 `n0`**。

**若 `n0 >= 1`**：守卫 `!queue_empty(Q)` 即 `|Q| > 0` **永远为真**，循环**永不退出**。
**若 `n0 == 0`**：守卫一开始就假，循环不执行，`C` 是空队列——**这唯一的情形下反而正确**。

**讲义的结论**：「the loop will never terminate unless `Q` is empty to begin with.」**注意这个精确的措辞**——不是「从不终止」，而是「除非一开始就空」。

**这是一个「不变量导致不终止」的教科书例子**：`|Q|` 恒定是一个**保持性完美成立**的循环不变式，但它**不递减**，因此不能用来证终止。**回顾 [[15-122-01-Contracts]] 的框架：部分正确性（partial correctness）与终止性（termination）是两个独立的证明义务。** 这段代码的部分正确性甚至都成立（如果它终止，`Q` 确实保持原样、`C` 确实是副本），**唯独终止性失败**。

### 5.9 `queue_copy`：三队列方案

```c0
queue_t queue_copy(queue_t Q)
//@requires Q != NULL;
//@ensures \result != NULL;
{
  queue_t T = queue_new();
  while (!queue_empty(Q)) {
    enq(T, deq(Q));
  }
  //@assert queue_empty(Q);
  queue_t C = queue_new();
  while (!queue_empty(T)) {
    string s = deq(T);
    enq(Q, s);
    enq(C, s);
  }
  //@assert queue_empty(T);
  return C;
}
```

**两阶段的分工**：

| 阶段 | 从 | 到 | 效果 |
|---|---|---|---|
| 1 | `Q` | `T` | `Q` 清空，`T` 得到 `Q` 的**原序**副本 |
| 2 | `T` | `Q` **与** `C` | `T` 清空，`Q` 与 `C` **都**得到原序副本 |

**为什么阶段 2 不会死循环**：这次循环的**数据源是 `T`**，而 `T` 只减不增（`deq(T)` 之后没有任何 `enq(T, ...)`）。**`|T|` 每轮严格减 1，故必然终止。** 上一版之所以死循环，是因为数据源与被写入者是**同一个队列**。

**「数据源必须与写入目标分离」是本讲最重要的工程教训。**

**为什么阶段 1 不用 `C` 而用 `T`**：若阶段 1 直接写 `C`，阶段 2 就只能从 `C` 读——**读完 `C` 又空了**，回到起点。**必须有一个「只用于中转、用完即弃」的第三个容器。** 讲义原文：「instead of putting them into `C`, we will put them into a third queue `T` for temporary storage.」

**正确性推导（顺序保持）**：

设入口 `Q = x1, ..., xn`（`x1` 队首）。

- **阶段 1**：`deq` 依次给出 `x1, x2, ..., xn`，`enq` 依次追加到 `T`。故 `T = x1, x2, ..., xn`（**顺序完全一致**，因为 `deq` 从首取、`enq` 往尾加，正好抵消）。
- **阶段 2**：`deq(T)` 依次给出 `x1, ..., xn`，每次都 `enq(Q, s)` 与 `enq(C, s)`。故 `Q` 与 `C` 都变成 `x1, ..., xn`。

**关键洞察：队列的「deq + enq」是保序的，栈的「pop + push」是反序的。** 这就是为什么 5.6 的 `stack_size` 需要「两次反转」，而 `queue_copy` 一次中转就够——**队列的一进一出本身就是「平移」而非「反转」**。

**边界情形**：若 `Q` 入口为空，阶段 1 与阶段 2 都不执行，`C` 与 `Q` 都仍是空。讲义特意点明：「Except if `Q` was empty to begin with, in which case both `C` and `Q` will still be empty in the end.」

**复杂度**：两个循环各 `n` 轮 → `O(n)`。

**`//@assert queue_empty(T);` 的意义**：它在函数返回前确认 `T` 确实空了（没有漏掉元素），是「阶段 2 跑完了」的机器可检查证据。

### 5.10 `stack_copy` 的 bug：一次遍历不够

讲义习题 1 给了一段**有 bug** 的代码：

```c0
stack_t stack_copy(stack_t S)
//@requires S != NULL;
{
  stack_t tmp = stack_new();   // temporary stack
  stack_t copy = stack_new();  // stack to be returned
  // move all elements of S into tmp
  while (!stack_empty(S)) {
    string x = pop(S);
    push(copy, x);   // <-- bug 在这里
    push(tmp, x);
  }
  while (!stack_empty(tmp))
    push(S, pop(tmp));
  return copy;
}
```

**追踪**：设 `S = a, b, c`（`a` 底、`c` 顶）。

| 轮 | `pop(S)` | `push(copy, x)` 后 `copy`（底→顶） | `push(tmp, x)` 后 `tmp` |
|---|---|---|---|
| 1 | `c` | `c` | `c` |
| 2 | `b` | `c, b` | `c, b` |
| 3 | `a` | `c, b, a` | `c, b, a` |

**`copy` 得到 `c, b, a`——是 `S` 的逆序。** 而 `tmp` 也是 `c, b, a`，第二阶段搬回 `S` 后 `S` 恢复成 `a, b, c`（正确）。

**bug 的机制**：**`copy` 与 `tmp` 走了完全相同的路径**，所以两者都是逆序。要得到正序副本，必须**让 `copy` 在第二次反转之后才收到元素**。

**修正**（讲义 p16）：

```c0
stack_t stack_copy(stack_t S)
//@requires S != NULL;
{
  stack_t tmp = stack_new();   // temporary stack
  stack_t copy = stack_new();  // stack to be returned
  // move all elements of S into tmp
  // -- they will be in the reverse order
  while (!stack_empty(S))
    push(tmp, pop(S));
  //@assert stack_empty(S);
  // move them back to both S and to copy
  while (!stack_empty(tmp)) {
    string x = pop(tmp);
    push(S, x);      // restore x onto S
    push(copy, x);   // put a copy of x onto copy
  }
  //@assert stack_empty(tmp);
  return copy;
}
```

**为什么这次对了**：第一阶段 `tmp` 得到逆序 `c, b, a`；第二阶段从 `tmp` 弹出 `a, b, c`（**正序**），同时压入 `S` 与 `copy`，两者都得到 `a, b, c`。**`copy` 在第二次反转后才收元素，所以是正序。**

**与 `stack_size` 的结构对比**：

```
stack_size:   搬走 → 搬回 S                    （只需恢复）
stack_copy:   搬走 → 搬回 S 与 copy             （恢复 + 副本）
queue_copy:   搬到 T → 搬到 Q 与 C              （恢复 + 副本，但只需一次中转）
```

**`stack_copy` 与 `queue_copy` 的差别只在第一阶段**：栈的 `pop+push` 反转，故需要两次搬运才能还原顺序；队列的 `deq+enq` 保序，一次搬运就够。**这个差别正是 LIFO 与 FIFO 的本质。**

### 5.11 `stack_reverse`：故意不还原

```c0
stack_t stack_reverse(stack_t S)
//@requires S != NULL;
//@ensures stack_empty(S);
{
  stack_t rev = stack_new();
  while (!stack_empty(S))
    push(rev, pop(S));
  //@assert stack_empty(S);
  return rev;
}
```

**这是 `stack_copy` 的「一半」**——只做第一阶段。`rev` 得到 `S` 的逆序，`S` 变空。

**后置 `stack_empty(S)` 是「破坏性」的契约化**：函数**承诺**输入被清空。这与 `pop` 的破坏性一致——**破坏本身不是错，隐藏破坏才是错。**

**与 5.6 的 `stack_size` 对照**：两者第一阶段完全相同，区别在于 `stack_size` **还要**第二阶段来恢复。**同一个「反转」操作，一个用来数数（数完还原），一个用来倒序（不用还原）。**

### 5.12 `stack_sort`：辅助栈 + 不变式

讲义习题 4 要求把栈排成「最大在顶、最小在底」。算法思路：用辅助栈 `tmp`，**始终维持 `tmp` 有序**，把 `S` 的元素逐个「插入」到 `tmp` 的正确位置。

```c0
void stack_sort(stack_t S)
//@requires S != NULL;
{
  stack_t tmp = stack_new();   // auxiliary stack
  //@assert stack_sorted_ascending(tmp);   // invariant
  while (!stack_empty(S))
  //@loop_invariant stack_sorted_ascending(tmp);
  {
    int n = pop(S);
    // Move all items in tmp smaller than n back onto S
    while (!stack_empty(tmp) && peek(tmp) < n) {
      push(S, pop(tmp));
    }
    // Push n onto tmp: tmp remains sorted
    push(tmp, n);
  }
  //@assert stack_empty(S);
  // Move them back to S
  while (!stack_empty(tmp))
  //@loop_invariant stack_sorted_ascending(tmp);
  //@loop_invariant stack_sorted_descending(S);
  {
    push(S, pop(tmp));
  }
}
```

**先厘清「ascending」在这里指什么**（讲义的定义有点绕，必须看清）：

> `stack_sorted_ascending(S)` 返回真当「the items in stack `S` are sorted in ascending order, **with the largest item at the top and the smallest at the bottom**」。

用 5.1 的序列记号（`x1` 底、`xn` 顶）：`x1 <= x2 <= ... <= xn`。**从底到顶递增，故最大在顶。**

**推论**：`stack_sorted_ascending` 的栈，**弹出序列是递减的**（先弹最大的）。反之 `stack_sorted_descending` 的栈（最小在顶）**弹出序列递增**。

**算法的实际行为**：`tmp` 中维护的是**最小在顶**（即 `stack_sorted_descending`），因为：

- 内层循环 `while (!stack_empty(tmp) && peek(tmp) < n)` 把 `tmp` 中所有**小于 `n`** 的元素弹回 `S`。
- 于是 `tmp` 剩下的元素**全部 `>= n`**，把 `n` 压上去后，`n` 在它们上面。
- 故 `tmp` 从底到顶是**递减**的：底最大、顶最小。

**所以 `tmp` 满足的是 `stack_sorted_descending`，不是 `stack_sorted_ascending`。**

**最后一步**：把 `tmp` 全部搬回 `S`。`tmp` 顶最小，故先搬最小的到 `S` 底，再搬次小的……**`S` 最终从底到顶递增，最大在顶**——**正是习题要求的「descending order, with the largest item at the top」**（注意习题这里的 "descending" 指的是**弹出顺序递减**，与 `stack_sorted_descending` 这个函数名的含义**相反**）。

> **原文异常（重要）**：讲义 p18 的 `stack_sort` 解答里，两条 `//@loop_invariant` 的**名称写反了**：`tmp` 实际满足 `stack_sorted_descending`，`S` 的已搬回前缀实际满足 `stack_sorted_ascending`，而代码写的是 `stack_sorted_ascending(tmp)` 与 `stack_sorted_descending(S)`。**算法本身是对的，只是不变式的名字贴错了。** 更麻烦的是习题 4 的文字用 "descending order, with the largest item at the top" 描述目标，而习题 3 又把 "largest at top" 定义为 `ascending`——**同一份讲义里 "ascending/descending" 的用法前后不一致**。阅读时务必以「最大在顶 / 最小在顶」这个**具体描述**为准，不要依赖函数名。

**内层循环为什么正确（「插入」的机制）**：设 `tmp` 当前从底到顶递减（顶最小）。弹出一个 `n`：

- 若 `peek(tmp) >= n`（顶元素不小于 `n`）：`n` 应当放在顶元素**下面**，但栈只能在顶操作，所以**先不动**，直接把 `n` 压上去——`n` 现在在顶，且 `n <= 旧顶`，递减性保持。**注意此时 `n` 是新顶（更小），完全正确。**
- 若 `peek(tmp) < n`（顶元素比 `n` 小）：`n` 应当放在**更下面**，于是把顶元素弹回 `S`（它稍后会被重新处理），继续检查下一个。

**「被弹回 `S` 的元素会被重新处理」是关键**：讲义原文说「Note that the same item may be shufﬂed between `S` and `tmp` multiple times.」**这不是 bug，而是算法的一部分**——`S` 在这里充当「待处理池」。

**复杂度**：最坏情形下每个元素可能在 `S` 与 `tmp` 之间来回多次。外层 `n` 轮，内层最多 `n` 轮 → **`O(n²)`**。**这与 [[15-122-05-Big-O]] 的选择排序、插入排序同阶**——事实上 `stack_sort` 就是**用栈实现的插入排序**。

### 5.13 纯性：为什么 `stack_sorted_ascending` 不能进契约

讲义 p18 有一句极重要的坦白：

> **「As written, this code will now compile however. The reason is that these functions write to allocated memory — they are impure.」**

> **原文异常**：这句话里的 **"will now compile"** 显然应为 **"will not compile"**（或 "will not verify"）。紧接着的两句在解释**为什么不能编译**：「a program may produce different outcome depending on whether it is compiled with or without the `-d` flag」。**从上下文看这是一个漏字。**

**为什么 `stack_sorted_ascending` 不纯**：看它的实现（习题 3 解答）：

```c0
bool stack_sorted_ascending(stack_t S)
//@requires S != NULL;
{
  if (stack_empty(S)) return true;
  //@assert !stack_empty(S);
  stack_t tmp = stack_copy(S);   // <-- 分配内存！
  //@assert !stack_empty(tmp);
  int n = pop(tmp);              // <-- 修改 tmp！
  while (!stack_empty(tmp)) {
    int m = pop(tmp);
    if (!(n > m)) return false;
    n = m;
  }
  //@assert stack_empty(tmp);
  return true;
}
```

**两处不纯**：

1. **`stack_copy(S)`** 内部调用 `stack_new()`，即 `alloc`——**分配新内存**。
2. **`pop(tmp)`** 修改 `tmp` 的内容——**修改已分配内存**。

**为什么「不纯」在契约里是致命的**：`//@` 契约在**不带 `-d`** 时**根本不执行**（验证器静态检查后丢弃），在**带 `-d`** 时**每轮循环都执行**。若契约里的表达式有副作用：

- 不带 `-d`：`tmp` 没被修改，算法照常跑。
- 带 `-d`：每轮循环都调用一次 `stack_sorted_ascending`，每次都在堆上分配一个副本并弹空它——**内存暴涨、时间暴涨**，甚至可能因为分配失败而崩溃。

**同一份源码在两种编译选项下行为不同**——这是**语义上的不确定**，比性能下降严重得多。**这正是 [[15-122-01-Contracts]] 里「契约必须是纯的」这条规则的由来。**

**有没有办法写出纯版本**：讲义明确回答：

> **「There is no way to write pure versions of these functions based on the given interface of our stack library. An extended stack library may however export pure versions.」**

**为什么基于现有接口写不出纯版本**：接口只有 `push`/`pop`/`stack_empty`，**任何读取操作都必须先 pop**，而 pop 就是修改。**没有「只读遍历」的能力。** 要写纯版本，接口必须**扩展**——比如导出一个纯的 `stack_to_array`（返回一个新数组而不改栈），或者让栈内部维护一个「长度」字段并导出一个纯的 `stack_size_lib`。

**这条结论的普适意义**：**抽象类型的接口设计会限制客户端能写出什么样的契约。** 接口太窄（只有破坏性操作），客户端的规格说明就写不精确。**这是「抽象」的真实代价**，也是为什么真实库（如 Java 的 `Collection`）会额外提供 `iterator()` 这种只读遍历能力。

### 5.14 递归版 `stack_size`：调用栈就是临时栈

```c0
int stack_size(stack_t S)
//@requires S != NULL;
//@ensures \result >= 0;
{
  if (stack_empty(S))    // Base case
    return 0;
  int data = pop(S);     // Recursive case
  int n = stack_size(S);
  push(S, data);
  return n+1;
}
```

**执行轨迹**（`S = a, b, c`，`a` 底）：

| 深度 | 入口 `S` | `pop` 出的 `data` | 递归调用 | 返回后 `push` | 返回 |
|---|---|---|---|---|---|
| 1 | `a, b, c` | `c` | `stack_size(a, b)` | `push(S, c)` | `2+1 = 3` |
| 2 | `a, b` | `b` | `stack_size(a)` | `push(S, b)` | `1+1 = 2` |
| 3 | `a` | `a` | `stack_size()` | `push(S, a)` | `0+1 = 1` |
| 4 | （空） | — | — | — | `0` |

**返回时逐层 `push` 回去**，`S` 恢复成 `a, b, c`（因为最深的 `push(a)` 最先执行，`a` 在底）。**顺序自动正确。**

**为什么不需要显式临时栈**：**每一层递归调用都在自己的栈帧里保存了 `data`**。这就是「调用栈（call stack）」。**递归与显式栈是同一件事的两种写法**——讲义原文：「Each call to `stack_size` 'remembers' the data item it pops, so when coming back from the recursive call it can be pushed back onto `S`.」

**复杂度**：`n` 层递归，每层 `O(1)` → **`O(n)` 时间 + `O(n)` 栈空间**。迭代版是 `O(n)` 时间 + `O(n)` **堆**空间（那个 `T`）。**空间复杂度同阶，只是位置不同。**

**递归版的优势**：代码短得多（6 行 vs 11 行），**不需要想「两次反转」**。**递归的代价是栈深度**——若 `n` 极大（比如百万级），会**栈溢出（stack overflow）**；迭代版不会。

### 5.15 三个「只读」客户端的统一模式

本讲所有「读但不改」的函数都遵循同一个骨架：

```
1. 建临时容器
2. 把元素从源搬到临时容器（此时源被破坏）
3. 从临时容器搬回源 + 顺便做你想做的事
```

| 函数 | 临时容器 | 第二阶段做什么 |
|---|---|---|
| `peek` | **一个变量**（不是容器） | 搬回 + 返回 |
| `stack_size` | 栈 `T` | 搬回 + 计数 |
| `stack_copy` | 栈 `tmp` | 搬回 `S` **与** `copy` |
| `queue_copy` | 队列 `T` | 搬回 `Q` **与** `C` |
| `queue_sum` | 队列 `T` | 搬回 + 累加 |

**`peek` 是 `n == 1` 的特例**——临时容器退化成一个变量。**`queue_sum`（习题 5）与 `stack_size` 完全同构**，只是把 `count++` 换成 `sum += x`：

```c0
int queue_sum(queue_t Q)
//@requires Q != NULL;
{
  int sum = 0;
  queue_t T = queue_new();
  while (!queue_empty(Q)) {
    int x = deq(Q);
    sum += x;
    enq(T, x);
  }
  while (!queue_empty(T))
    enq(Q, deq(T));
  return sum;
}
```

**注意 `queue_sum` 第一阶段就同时做两件事**（累加 + 搬到 `T`），因为队列的 `deq+enq` 保序，不需要第二阶段来「纠正顺序」——第二阶段只是单纯地搬回。**对比 `stack_copy`，第一阶段不能同时写 `copy`，因为顺序是反的。**

**这个「统一模式」是本讲最实用的收获**：以后遇到「只能用破坏性接口但要只读」的问题，直接套这个骨架。

## 6. 代码示例

### 6.1 官方课程代码

以下引自讲义 PDF `09-stackqueue.pdf`，语言为 **C0**（不是标准 C/C++）。`//@` 注解、`\result`、`alloc` 都是 C0 特有语法。

**（1）`stack_t` 接口，第 2 页：**

```c0
// typedef ______* stack_t;
bool stack_empty(stack_t S)
/* O(1), check if stack empty */
/*@requires S != NULL; @*/;
stack_t stack_new()
/* O(1), create new empty stack */
/*@ensures \result != NULL; @*/
/*@ensures stack_empty(\result); @*/;
void push(stack_t S, string x)
/* O(1), add item on top of stack */
/*@requires S != NULL; @*/
/*@ensures !stack_empty(S); @*/;
string pop(stack_t S)
/* O(1), remove item from top */
/*@requires S != NULL; @*/
/*@requires !stack_empty(S); @*/;
```

**（2）违规的 `peek`（用了实现细节），第 4 页：**

```c0
string peek(stack_t S)
//@requires is_stack(S) && !stack_empty(S);
{
  return S->data[S->top];
}
```

**（3）合规的 `peek`（客户端实现），第 4 页：**

```c0
string peek(stack_t S)
//@requires S != NULL && !stack_empty(S);
{
  string x = pop(S);
  push(S, x);
  return x;
}
```

**（4）`stack_size` 的破坏性版本，第 6 页：**

```c0
int stack_size(stack_t S)
//@requires S != NULL;
//@ensures \result >= 0;
{
  int count = 0;
  while (!stack_empty(S)) {
    pop(S);
    count++;
  }
  return count;
}
```

**（5）`stack_size` 的非破坏性版本，第 7 页：**

```c0
int stack_size(stack_t S)
//@requires S != NULL;
//@ensures \result >= 0;
{
  stack_t T = stack_new();
  int count = 0;
  while (!stack_empty(S)) {
    push(T, pop(S));
    count++;
  }
  while (!stack_empty(T)) {
    push(S, pop(T));
  }
  return count;
}
```

**（6）`queue_t` 接口，第 8 页：**

```c0
// typedef ______* queue_t;
bool queue_empty(queue_t Q)
/* O(1) */
/*@requires Q != NULL; @*/;
queue_t queue_new()
/* O(1) */
/*@ensures \result != NULL; @*/
/*@ensures queue_empty(\result); @*/;
void enq(queue_t Q, string e)
/* O(1) */
/*@requires Q != NULL; @*/;
string deq(queue_t Q)
/* O(1) */
/*@requires Q != NULL; @*/
/*@requires !queue_empty(Q); @*/ ;
```

**（7）破坏性的复制尝试（`Q` 被清空），第 10 页：**

```c0
queue_t C = queue_new();
while (!queue_empty(Q)) {
  enq(C, deq(Q));
}
//@assert queue_empty(Q);
```

**（8）死循环的复制尝试，第 12 页：**

```c0
queue_t C = queue_new();
while (!queue_empty(Q)) {
  string s = deq(Q);
  enq(Q, s);
  enq(C, s);
}
//@assert queue_empty(Q);
```

**（9）正确的 `queue_copy`（三队列），第 13 页：**

```c0
queue_t queue_copy(queue_t Q)
//@requires Q != NULL;
//@ensures \result != NULL;
{
  queue_t T = queue_new();
  while (!queue_empty(Q)) {
    enq(T, deq(Q));
  }
  //@assert queue_empty(Q);
  queue_t C = queue_new();
  while (!queue_empty(T)) {
    string s = deq(T);
    enq(Q, s);
    enq(C, s);
  }
  //@assert queue_empty(T);
  return C;
}
```

**（10）习题 1 的 bug 版 `stack_copy`，第 14 页：**

```c0
stack_t stack_copy(stack_t S)
//@requires S != NULL;
{
  stack_t tmp = stack_new();   // temporary stack
  stack_t copy = stack_new();  // stack to be returned
  // move all elements of S into tmp
  while (!stack_empty(S)) {
    string x = pop(S);
    push(copy, x);
    push(tmp, x);
  }
  while (!stack_empty(tmp))
    push(S, pop(tmp));
  return copy;
}
```

**（11）修正后的 `stack_copy`，第 16 页：**

```c0
stack_t stack_copy(stack_t S)
//@requires S != NULL;
{
  stack_t tmp = stack_new();   // temporary stack
  stack_t copy = stack_new();  // stack to be returned
  // move all elements of S into tmp
  // -- they will be in the reverse order
  while (!stack_empty(S))
    push(tmp, pop(S));
  //@assert stack_empty(S);
  // move them back to both S and to copy
  while (!stack_empty(tmp)) {
    string x = pop(tmp);
    push(S, x);      // restore x onto S
    push(copy, x);   // put a copy of x onto copy
  }
  //@assert stack_empty(tmp);
  return copy;
}
```

**（12）`stack_reverse`，第 16 页：**

```c0
stack_t stack_reverse(stack_t S)
//@requires S != NULL;
//@ensures stack_empty(S);
{
  stack_t rev = stack_new();
  while (!stack_empty(S))
    push(rev, pop(S));
  //@assert stack_empty(S);
  return rev;
}
```

**（13）`stack_sorted_ascending`，第 17 页：**

```c0
bool stack_sorted_ascending(stack_t S)
//@requires S != NULL;
{
  if (stack_empty(S))   // the empty stack is sorted
    return true;
  //@assert !stack_empty(S);
  stack_t tmp = stack_copy(S);   // make a copy of S
  //@assert !stack_empty(tmp);
  int n = pop(tmp);
  while (!stack_empty(tmp)) {
    int m = pop(tmp);
    if (!(n > m)) return false;   // tmp is not in ascending order
    n = m;
  }
  //@assert stack_empty(tmp);
  return true;
}
```

（`stack_sorted_descending` 相同，只把第 14 行的 `!(n > m)` 换成 `!(n < m)`）

**（14）`stack_sort`，第 18 页：**

```c0
void stack_sort(stack_t S)
//@requires S != NULL;
{
  stack_t tmp = stack_new();   // auxiliary stack
  //@assert stack_sorted_ascending(tmp);   // invariant
  while (!stack_empty(S))
  //@loop_invariant stack_sorted_ascending(tmp);
  {
    int n = pop(S);
    // Move all items in tmp smaller than n back onto S
    while (!stack_empty(tmp) && peek(tmp) < n) {
      push(S, pop(tmp));
    }
    // Push n onto tmp: tmp remains sorted
    push(tmp, n);
  }
  //@assert stack_empty(S);
  // Move them back to S
  while (!stack_empty(tmp))
  //@loop_invariant stack_sorted_ascending(tmp);
  //@loop_invariant stack_sorted_descending(S);
  {
    push(S, pop(tmp));
  }
}
```

**（15）`queue_sum`（习题 5 答案），第 19 页：**

```c0
int queue_sum(queue_t Q)
//@requires Q != NULL;
{
  int sum = 0;
  queue_t T = queue_new();
  while (!queue_empty(Q)) {
    int x = deq(Q);
    sum += x;
    enq(T, x);
  }
  while (!queue_empty(T))
    enq(Q, deq(T));
  return sum;
}
```

**（16）递归版 `stack_size`（习题 6 答案），第 19 页：**

```c0
int stack_size(stack_t S)
//@requires S != NULL;
//@ensures \result >= 0;
{
  if (stack_empty(S))    // Base case
    return 0;
  int data = pop(S);     // Recursive case
  int n = stack_size(S);
  push(S, data);
  return n+1;
}
```

**官方代码包**：`90-原始PDF/15-122/code/09-stackqueue.tgz`（原始 URL：`https://cs.cmu.edu/~15122/handouts/code/09-stackqueue.tgz`）。

### 6.2 Agent 自行编写的教学示例

> **非官方，仅用于说明概念。** 以下由本笔记自行编写，不是 CMU 官方代码，语言为 **C0**。

**示例 A：`peek` 的完整追踪（含不变式）。**

`S = "a", "b", "c"`（`"a"` 底、`"c"` 顶）。

```c0
string peek(stack_t S)
//@requires S != NULL && !stack_empty(S);
//@ensures S 的内容与入口完全相同;
{
  string x = pop(S);
  push(S, x);
  return x;
}
```

| 语句 | `S`（底→顶） | `x` | 备注 |
|---|---|---|---|
| 入口 | `a, b, c` | — | `!stack_empty(S)` 成立 |
| `x = pop(S)` | `a, b` | `c` | `pop` 前置满足 |
| `push(S, x)` | `a, b, c` | `c` | 恢复原状 |
| `return x` | `a, b, c` | `c` | 返回 `"c"` = 栈顶 |

**「恢复原状」这条后置是本讲的隐含契约**：接口**没有**承诺 `peek` 不改栈，但**客户端的正确性依赖它**。讲义把这个责任交给客户端实现者——**你自己写的函数，你自己负责它的后置。**

**示例 B：证明「读一个写回一个」的队列复制不终止。**

```c0
while (!queue_empty(Q)) {
  string s = deq(Q);
  enq(Q, s);
  enq(C, s);
}
```

**取不变式 `|Q| == n0`**（`n0` 为入口长度）。

- **INIT**：入口时 `|Q| == n0`。成立。
- **PRES**：`deq` 使 `|Q|` 减 1，`enq(Q, s)` 使其加 1，净 0。故 `|Q|` 仍为 `n0`。成立。
- **EXIT**：守卫为假需 `|Q| == 0`，即 `n0 == 0`。

**结论**：若 `n0 >= 1`，`|Q| == n0 >= 1` **恒成立**，守卫**永不为假**，**循环不终止**。

**这个证明的形态值得记住**：**保持性（PRES）完美成立，但终止性失败**。因为 `|Q|` 是**非增但不严格减**的量。**终止性需要严格递减且非负的「秩函数（ranking function）」**，而 `|Q|` 在这里是**常数**，不是秩函数。对比 5.12 的 `stack_sort`：`|S|` 在外层循环中**严格递减**（每次 `pop(S)` 且内层只往 `S` 里 `push` 但外层接着又 `pop`……）——严格说 `stack_sort` 的外层终止性也需要仔细论证，因为内层会把元素推回 `S`。

**`stack_sort` 的外层终止性证明**（这是一个好练习）：取秩函数 `R = |S| + |tmp|`。外层每轮：

- `pop(S)`：`R -= 1`
- 内层每轮：`pop(tmp)` 后 `push(S)`，`R` 不变
- `push(tmp, n)`：`R += 1`

**净变化 0**——`R` 不递减！**所以 `R` 不是秩函数。** 正确的秩函数需要更细的度量：**`S` 中「尚未插入 `tmp`」的元素数**。外层每轮恰好处理一个 `S` 的元素并把它永久移入 `tmp`（内层弹回 `S` 的都是**已经**在 `tmp` 里的，之后会被重新处理，但它们的「待插入」状态已被消耗）。用「外层已完成的轮数」更直接：**外层循环体执行一次，`tmp` 的最终大小增加 1 且不再减少**（内层只弹 `tmp` 再压 `tmp`，`push(tmp, n)` 后 `tmp` 净增 1）。故外层至多执行 `n` 轮。**内层**：`tmp` 在每轮内层中严格减小，故内层至多 `|tmp|` 轮。

**这个例子说明：秩函数要选对。** 选 `|S| + |tmp|` 失败，选「`tmp` 的净增长次数」成功。

**示例 C：`stack_copy` 的 bug 用「两次反转」框架诊断。**

把 `S = a, b, c` 的搬运画成「反转次数」：

| 方案 | 路径 | `copy` 收到元素时的反转次数 | 结果 |
|---|---|---|---|
| bug 版 | `S → copy`（同时 `S → tmp`） | **1**（直接搬） | 逆序 `c, b, a` |
| 修正版 | `S → tmp → copy` | **2** | 正序 `a, b, c` |

**`S` 本身**：bug 版走 `S → tmp → S`（2 次反转，正确）；修正版走 `S → tmp → S`（同样 2 次）。

**所以 bug 版的 `S` 恢复是对的，只有 `copy` 错了**——因为 `copy` 少走了一站。**「数反转次数」是诊断这类 bug 最快的办法。**

**示例 D：用 `stack_sort` 排一个具体栈。**

`S = 3, 1, 4, 1, 5`（`3` 底、`5` 顶）。目标：最大在顶。

初始：`tmp` 空。

**外层第 1 轮**：`n = pop(S) = 5`。`S = 3, 1, 4, 1`。

- 内层：`tmp` 空 → 守卫假，0 轮。
- `push(tmp, 5)`：`tmp = 5`。

**外层第 2 轮**：`n = pop(S) = 1`。`S = 3, 1, 4`。

- 内层：`peek(tmp) = 5 < 1`？假。0 轮。
- `push(tmp, 1)`：`tmp = 5, 1`（底→顶，递减）。

**外层第 3 轮**：`n = pop(S) = 4`。`S = 3, 1`。

- 内层：`peek(tmp) = 1 < 4`？真 → `push(S, pop(tmp))`：`S = 3, 1, 1`，`tmp = 5`。
- 内层：`peek(tmp) = 5 < 4`？假。退出。
- `push(tmp, 4)`：`tmp = 5, 4`。

**外层第 4 轮**：`n = pop(S) = 1`。`S = 3, 1`。

- 内层：`peek(tmp) = 4 < 1`？假。0 轮。
- `push(tmp, 1)`：`tmp = 5, 4, 1`。

**外层第 5 轮**：`n = pop(S) = 1`。`S = 3`。

- 内层：`peek(tmp) = 1 < 1`？假（不是 `<`）。0 轮。
- `push(tmp, 1)`：`tmp = 5, 4, 1, 1`。

**外层第 6 轮**：`n = pop(S) = 3`。`S` 空。

- 内层：`peek(tmp) = 1 < 3`？真 → `S = 1`，`tmp = 5, 4, 1`。
- 内层：`peek(tmp) = 1 < 3`？真 → `S = 1, 1`，`tmp = 5, 4`。
- 内层：`peek(tmp) = 4 < 3`？假。退出。
- `push(tmp, 3)`：`tmp = 5, 4, 3`。

**外层退出**（`S` 空）。**注意 `S` 里还有 `1, 1`**——它们是被内层弹回来的，尚未重新插入！但外层守卫是 `!stack_empty(S)`，**`S` 非空，所以外层还要继续**。

**外层第 7 轮**：`n = pop(S) = 1`。`S = 1`。

- 内层：`peek(tmp) = 3 < 1`？假。0 轮。
- `push(tmp, 1)`：`tmp = 5, 4, 3, 1`。

**外层第 8 轮**：`n = pop(S) = 1`。`S` 空。

- 内层：`peek(tmp) = 1 < 1`？假。
- `push(tmp, 1)`：`tmp = 5, 4, 3, 1, 1`。

**外层退出**（`S` 空）。`tmp = 5, 4, 3, 1, 1`（底→顶递减）。

**最后一步**：把 `tmp` 全部搬回 `S`：

| 轮 | `pop(tmp)` | `S`（底→顶） |
|---|---|---|
| 1 | `1` | `1` |
| 2 | `1` | `1, 1` |
| 3 | `3` | `1, 1, 3` |
| 4 | `4` | `1, 1, 3, 4` |
| 5 | `5` | `1, 1, 3, 4, 5` |

**`S = 1, 1, 3, 4, 5`，最大在顶——正确。**

**这个追踪揭示了两个要点**：

1. **外层循环跑了 8 轮，而元素只有 5 个**——因为内层会把元素弹回 `S` 重新处理。**这正是 `O(n²)` 的来源。**
2. **`tmp` 始终递减**（`5, 1` → `5, 4` → `5, 4, 1` → `5, 4, 3` → `5, 4, 3, 1` → `5, 4, 3, 1, 1`），**即 `stack_sorted_descending`**。这印证了 5.12 指出的「讲义把不变式名字写反了」。

**示例 E：为什么 `queue_sum` 可以「一边搬一边加」，而 `stack_copy` 不行。**

`Q = 1, 2, 3`（`1` 队首）。

**`queue_sum` 第一阶段**（`deq(Q)` + `sum += x` + `enq(T, x)`）：

| 轮 | `deq(Q)` | `sum` | `T`（首→尾） |
|---|---|---|---|
| 1 | `1` | `1` | `1` |
| 2 | `2` | `3` | `1, 2` |
| 3 | `3` | `6` | `1, 2, 3` |

**`T` 与 `Q` 的原序完全一致**（`deq` 从首取、`enq` 往尾加，正好抵消）。故第二阶段直接搬回即可，**不需要「纠正顺序」**。

**若换成栈**（`S = 1, 2, 3`，`3` 顶），第一阶段 `push(T, pop(S))` 得到 `T = 3, 2, 1`（**逆序**）。若此时也「一边搬一边算」，算出来的东西**顺序是反的**——对「求和」无所谓（加法可交换），但对「拼字符串」或「求第一个满足条件的元素」就**全错**。

**这就是 `stack_copy` 必须等第二阶段的原因**：它需要**正序**，而第一阶段只给出逆序。**`queue_sum` 能偷懒，是因为队列的搬运保序。**

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键区别 | 记忆点 |
|---|---|---|---|
| 栈（LIFO） | 队列（FIFO） | 插入端相同（右端），**删除端不同**（栈右、队列左） | 一摞纸 vs 排队 |
| `push` | `enq` | **完全相同**（都在右端追加） | 差别只在删除 |
| `pop` | `deq` | 前者删右端，后者删左端 | LIFO vs FIFO 的唯一来源 |
| `peek`（客户端版） | `S->data[S->top]`（库版） | 前者用 `pop`+`push`，合规；后者用实现细节，违规 | 抽象有常数代价 |
| `stack_empty(S)` | `!stack_empty(S)` | 前者是**函数调用**（`O(1)`）；后者是它的否定 | `pop` 前置要后者 |
| `pop` 的前置 `!stack_empty(S)` | `push` 的后置 `!stack_empty(S)` | 一个是**要求**，一个是**保证** | 一进一出 |
| `queue_t C = Q;` | `queue_copy(Q)` | 前者是**别名**（同址）；后者是真复制 | 与数组 `G = F` 同源 |
| 破坏性读取 | 非破坏性读取 | 前者毁掉输入（`pop` 到空）；后者用临时容器还原 | 本讲的核心技巧 |
| 栈的「搬两次」 | 队列的「搬一次」 | 前者 `pop+push` 反转，需两次才还原；后者 `deq+enq` 保序 | 两次反转 = 还原 |
| `stack_size`（客户端） | `stack_size`（库侧） | 前者 `O(n)`；后者 `O(1)`（读一个计数字段） | 接口隐藏了计数 |
| `stack_sorted_ascending` | 「弹出序列递减」 | 前者 = **最大在顶**；故弹出时先给最大的 | 别被名字骗 |
| 不纯的函数 | 纯函数 | 前者分配/修改内存，**不能**进 `//@`；后者可以 | `stack_sorted_ascending` 不纯 |
| 递归版 `stack_size` | 迭代版 `stack_size` | 前者用**调用栈**当临时栈；后者用**堆**上的 `T` | 空间同阶，位置不同 |
| 部分正确性 | 终止性 | 死循环的 `queue_copy` 前者成立、后者失败 | 两个独立义务 |
| `|Q|` 恒定（不变式） | 秩函数（严格递减） | 前者能证保持性，**不能**证终止 | 终止要严格递减 |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-122/lectures/09-stackqueue.pdf`
- **讲义标题**：PDF 内页标题为 **"Lecture 9: Stacks and Queues"**，作者 Frank Pfenning、André Platzer、Rob Simmons。
- **总页数**：19 页
- **本节重点页码**（PDF 页码，即提取文本中 `=== [page N] ===` 的 N）：
  - 第 1 页：开篇；栈与队列「organizing the data 的原则相同，取出的顺序不同」；本讲**只谈接口不谈实现**（实现留到下一讲）；复习幻灯片与代码包链接
  - 第 1–2 页：栈 = 一摞纸；LIFO 定义；`stack_t` 完整接口（`stack_empty`/`stack_new`/`push`/`pop`）；四个 `O(1)` 标注；`typedef ______* stack_t;`
  - 第 2 页：可变抽象类型是指针；`pop` 的空栈前置是「fundamental aspect」；`string` 只是临时选择，泛型以后讲
  - 第 3 页：栈的序列记号 `x1, ..., xn`（`x1` 底、`xn` 顶）；**抽象（abstraction）**：客户端只能用接口函数，不许知道实现
  - 第 4 页：`peek` 的违规写法（`S->data[S->top]` + `is_stack(S)`）；合规写法（`pop` + `push`）；`O(1)` 论证
  - 第 4–5 页：`stack_size` 的签名（**第 5 页几乎空白，只有签名**，正文从第 6 页继续）
  - 第 6 页：破坏性 `stack_size`（`while` + `pop` + `count++`）；「in order to compute the size we have to destroy the stack」；引出临时栈 `T`
  - 第 7 页：非破坏性 `stack_size` 完整代码；`O(n)` 论证；库侧可做到 `O(1)`
  - 第 8 页：队列 = 排队；FIFO；两个应用（按序读文件、网络缓冲）；`queue_t` 完整接口；`deq` 的空队列前置；抽象在 C 里「mostly a matter of adhering to conventions」
  - 第 9 页：队列的序列记号（`x1` 首、`xn` 尾）；队列操作追踪（**配图未被文本提取**）
  - 第 9–10 页：`queue_copy` 问题提出；`queue_t C = Q;` 是别名不是复制
  - 第 10 页：第一次尝试（`deq(Q)` → `enq(C, ...)`）；`//@assert queue_empty(Q);`；「our copying process was destructive」
  - 第 11 页：为什么「从 `C` 读回 `Q`」也不行（读完 `C` 又空了）；第二次「Before you read on」提问
  - 第 12 页：第二次尝试（读一个写回一个）；再次提问
  - 第 13 页：**死循环的证明**（`Q` 长度不变）；三队列方案 `queue_copy` 完整代码；`Q` 与 `C` 都被补满；空队列边界情形
  - 第 14 页：习题 1（bug 版 `stack_copy`）、习题 2（`stack_reverse`）、习题 3（`stack_sorted_ascending`/`descending`）
  - 第 15 页：习题 3 续（可用临时栈）；习题 4（`stack_sort`，提示「carefully consider what loop invariants should hold」）；习题 5（`queue_sum`）；习题 6（递归 `stack_size`）
  - 第 16 页：习题 1 答案（bug 是「返回逆序」+ 修正版）；习题 2 答案（`stack_reverse`）
  - 第 17 页：习题 3 答案（`stack_sorted_ascending`，用 `stack_copy` 复制后弹空比较）；`stack_sorted_descending` 只改一行
  - 第 17–18 页：习题 4 答案（`stack_sort` 完整代码 + 算法说明「the same item may be shufﬂed between `S` and `tmp` multiple times」）
  - 第 18 页：**纯性讨论**（`stack_sorted_ascending` 不纯 → 不能进 `//@`；带 `-d` 与不带 `-d` 结果不同；基于现有接口写不出纯版本）
  - 第 19 页：习题 5 答案（`queue_sum`）；习题 6 答案（递归 `stack_size`）
- **原始网页链接**：`https://www.cs.cmu.edu/~15122-archive/f26/handouts/lectures/09-stackqueue.pdf`
- **配套代码包**：`https://cs.cmu.edu/~15122/handouts/code/09-stackqueue.tgz`（本库已下载为 `90-原始PDF/15-122/code/09-stackqueue.tgz`，**未解压**）
- **复习幻灯片**：`https://cs.cmu.edu/~15122/handouts/slides/review/09-stackqueue.pdf`（本库**未**收录其提取文本，页码待人工核对）

> **原文异常**：
> 1. **第 18 页**：「As written, this code **will now compile** however.」——应为 **"will not compile"**（或 "will not verify"）。紧接的两句在解释「带 `-d` 与不带 `-d` 结果不同」，显然是在说**编译/验证失败**。**漏了一个 `not`。**
> 2. **第 18 页**：`stack_sort` 解答里两条 `//@loop_invariant` 的**函数名写反**：`tmp` 实际满足 `stack_sorted_descending`（最小在顶），`S` 的已搬回部分满足 `stack_sorted_ascending`，代码却写成 `stack_sorted_ascending(tmp)` 与 `stack_sorted_descending(S)`。**算法正确，标签错误。** 详见本笔记 5.12 与 6.2 示例 D。
> 3. **术语前后不一致**：习题 3（p14）把「largest item at the top」定义为 `stack_sorted_ascending`；习题 4（p15）却要求结果「sorted in **descending** order, with the largest item at the top」。**同一个物理状态被两个相反的名字描述。** 阅读时以「最大在顶 / 最小在顶」为准。
> 4. **第 5 页几乎空白**：只有 `int stack_size(stack_t S)` 的签名与两条契约，正文从第 6 页「We encourage you to consider this problem and program it before you read on」继续。**这是排版分页造成的，不是内容缺失**，但直接阅读会以为漏了一页。
> 5. **第 8 页 `enq` 缺少后置**：`push` 有 `/*@ensures !stack_empty(S); @*/`，`enq` 却**没有任何后置**。逻辑上 `enq` 之后队列必然非空，这条后置本应存在。**接口不对称**（不影响正确性，但削弱客户端推理能力）。
> 6. **第 3 页与第 9 页的配图未被文本提取**：栈与队列的操作追踪图（「If we're feeling artistic, we can draw stacks with arrows」、「Here's a trace of the queues in action」）在提取文本中只剩图注。**具体图形待人工核对原 PDF。**
> 7. **习题 3–4 的类型混用**：题目说「you may assume that the stack items have type `int` rather than `string`」，但接口签名是 `string pop(stack_t S)`。解答里直接写 `int n = pop(tmp);`——**默认了「把接口里的 `string` 全部替换为 `int`」这个改写**。题目有说明，但代码里没有任何类型标注，容易让读者以为 `pop` 真的返回 `int`。

## 9. 对应视频

未找到官方公开录像。建议的动手顺序：(1) 在 `coin` 里实现一个**最简栈**（用 C0 数组 + 一个 `top` 下标），然后**只用接口函数**写 `peek`、`stack_size`、`stack_copy`、`stack_reverse`，体会「不知道实现也能编程」；(2) 把 5.8 的死循环代码原样跑起来，**观察它确实卡住**，再想为什么；(3) 用 `cc0 -d` 编译 `stack_sort`（带 `stack_sorted_ascending` 的循环不变式），观察**内存与时间如何爆炸**，理解纯性的必要性；(4) 把 `stack_sort` 的不变式改成 `stack_sorted_descending(tmp)`，看是否仍然通过——这会让你确信讲义那处是笔误；(5) 用 `stack_sort` 排 `3, 1, 4, 1, 5`，打印每轮 `S` 与 `tmp`，对照 6.2 示例 D。

## 10. 本节复习

1. 栈 = LIFO（一摞纸）；队列 = FIFO（排队）。
2. `push` 与 `enq` **完全相同**（右端追加）；区别只在 `pop` 删右端、`deq` 删左端。
3. 两个接口都是 `typedef ______* xxx_t;`——**未知的指针类型**，因为是可变的。
4. `pop`/`deq` 的前置**必须**含 `!xxx_empty(...)`：空容器不能取元素。
5. `push` 有后置 `!stack_empty(S)`；`enq` 讲义里**漏了**这条（不对称）。
6. `peek` 用 `pop` + `push` 实现，净效果为零，仍是 `O(1)`。
7. `stack_size` 破坏性版：`pop` 到空 + 计数，`O(n)`，**但毁掉栈**。
8. `stack_size` 非破坏性版：搬到 `T` 再搬回，**两次反转 = 还原**，`O(n)`。
9. `queue_t C = Q;` 是**别名**，不是复制。
10. 「读一个写回一个」的队列复制**不终止**（`|Q|` 恒定，不是秩函数）。
11. `queue_copy` 必须用**第三个队列** `T`：数据源与写入目标必须分离。
12. 栈的搬运**反转**顺序，队列的搬运**保持**顺序——这是 `stack_copy` 需要两阶段而 `queue_copy` 只需一次中转的原因。
13. `stack_copy` 初版 bug：`copy` 与 `tmp` 走了同一条路径，故都是逆序。
14. `stack_reverse` = `stack_copy` 的第一阶段，后置 `stack_empty(S)` 把破坏性契约化。
15. `stack_sort` 用辅助栈维持有序，**同一元素可能来回搬多次**，`O(n²)`。
16. `stack_sorted_ascending` 不纯（`stack_copy` 分配 + `pop` 修改），**不能**进 `//@`；否则带 `-d` 与不带 `-d` 行为不同。
17. 基于现有接口**写不出**纯版本的 `stack_sorted_ascending`——接口太窄（只有破坏性操作）。
18. 递归版 `stack_size`：**调用栈就是临时栈**，代码更短，但深递归会栈溢出。
19. 统一模式：建临时容器 → 搬空源 → 搬回源（+ 顺便做事）。
20. 终止性需要**严格递减的秩函数**；`|Q|` 恒定只能证保持性。

## 11. 自我检查

**题 1.** 写出 `S = "a", "b", "c"`（`"a"` 底）上依次执行 `push(S, "d")`、`pop(S)`、`pop(S)`、`push(S, "e")` 后 `S` 的内容（底→顶），并说明最后 `stack_size(S)` 返回几。

**题 2.** 为什么 `stack_size` 的破坏性版本「返回值是对的但不能用」？非破坏性版本靠什么机制还原顺序？如果是**队列**而不是栈，还原需要几次搬运？

**题 3.** 证明下面这段代码不终止（`Q` 入口非空）：

```c0
while (!queue_empty(Q)) {
  enq(Q, deq(Q));
}
```

**题 4.** 讲义习题 1 的 `stack_copy` 初版返回逆序。用「反转次数」解释为什么，并说明修正版为什么正确。

**题 5.** 为什么 `stack_sorted_ascending` 不能写进 `//@loop_invariant`？如果强行写进去，带 `-d` 编译会发生什么？

<details>
<summary>参考答案</summary>

**答 1.**

| 操作 | `S`（底→顶） | 说明 |
|---|---|---|
| 初始 | `a, b, c` | `"c"` 在顶 |
| `push(S, "d")` | `a, b, c, d` | `"d"` 成新顶 |
| `pop(S)` | `a, b, c` | 弹出 `"d"` |
| `pop(S)` | `a, b` | 弹出 `"c"` |
| `push(S, "e")` | `a, b, e` | `"e"` 成新顶 |

**最终**：`S = "a", "b", "e"`（`"a"` 底、`"e"` 顶）。**`stack_size(S)` 返回 3。**

**注意两次 `pop` 的顺序**：第一次弹 `"d"`（刚压进去的），第二次弹 `"c"`。**「最后进的先出」在两步之内就体现出来了。** 若换成队列，`deq` 会先取 `"a"`——同样的操作序列会得到完全不同的结果（`Q` 变成 `b, c, d, e` 再……）。

**答 2.** **破坏性版**：`pop` 到空 + `count++`。返回值 `count` 确实等于入口元素数（守恒式不变式可证），**但副作用是栈被清空**。若调用者在 `stack_size(S)` 之后还要用 `S`，就拿到一个空栈——**这在语义上是灾难，尽管返回值正确**。讲义的说法：「in order to compute the size we have to destroy the stack!」

**非破坏性版的机制**：**两次反转 = 还原**。

- 第一阶段 `push(T, pop(S))`：`S = x1, ..., xn` → `T = xn, ..., x1`（**逆序**）。
- 第二阶段 `push(S, pop(T))`：`T` 的顶是 `x1`，故依次弹出 `x1, x2, ..., xn`，压回 `S` 后 `S = x1, ..., xn`（**与入口相同**）。

**如果是队列**：**一次搬运就够**。因为 `deq(Q)` 从队首取、`enq(T, x)` 往队尾加，**取出顺序 = 入队顺序**，故 `T` 与 `Q` 原序**完全一致**（不是逆序）。搬回时 `deq(T)` + `enq(Q, ...)` 同样保序，`Q` 直接还原。**不需要「两次反转」——队列的搬运本身就是保序的。**

**这个对比是理解 LIFO 与 FIFO 的关键**：栈的搬运是「反转」，队列的搬运是「平移」。

**答 3.** 取不变式 `|Q| == n0`（`n0` 为入口长度，`n0 >= 1`）。

- **INIT**：入口时 `|Q| == n0`。成立。
- **PRES**：循环体 `enq(Q, deq(Q))` —— `deq(Q)` 使 `|Q| -= 1`，`enq(Q, ...)` 使 `|Q| += 1`，**净变化 0**。故 `|Q|` 仍为 `n0`。成立。
- **EXIT**：守卫 `!queue_empty(Q)` 为假需 `|Q| == 0`。

**但由不变式 `|Q| == n0` 且 `n0 >= 1`，得 `|Q| >= 1 > 0`，故守卫恒为真，EXIT 不可达。**

**结论**：循环不终止。

**补充**：这段代码的**部分正确性**甚至成立——如果它终止，`Q` 的内容确实保持原样（`deq` 取出队首再 `enq` 到队尾，整体是「旋转一格」，但因为是无限次旋转，若真能停下则内容不变）。**失败的只是终止性。** 这印证了 [[15-122-01-Contracts]] 的框架：**部分正确性与终止性是两个独立的证明义务**。

**修复**：把数据源与写入目标分开——用 `T` 暂存（见 5.9 的 `queue_copy`）。

**答 4.** **反转次数分析**（`S = a, b, c`，`a` 底）：

**初版**：循环体是 `x = pop(S); push(copy, x); push(tmp, x);`。

- `S → copy`：**直接搬，1 次反转**（`pop` 从顶取 `c`，`push` 到 `copy` 顶，故 `copy` 底→顶是 `c, b, a`）。
- `S → tmp`：同样 **1 次反转**（`tmp = c, b, a`）。
- `tmp → S`：**再 1 次反转**，`S` 恢复成 `a, b, c`（**正确**）。

**故 `S` 对了，`copy` 错了**——因为 `copy` 只走了「1 次反转」的路径。

**修正版**：`S → tmp`（1 次反转，`tmp = c, b, a`），然后 `tmp → S` 与 `tmp → copy`（各再 1 次反转）。**`copy` 总共经历 2 次反转，故正序 `a, b, c`。** `S` 也经历 2 次，同样正确。

**一般规律**：**奇数次反转 = 逆序，偶数次反转 = 正序。** 要得到正序副本，目标容器必须位于「偶数次反转」的路径末端。**这个规律对栈成立；对队列，搬运本身保序，「反转次数」恒为 0，所以一次就够。**

**答 5.** **`stack_sorted_ascending` 不纯**，有两处副作用：

1. **`stack_copy(S)`** 内部调用 `stack_new()`，即 `alloc`——**分配新内存**。
2. **`pop(tmp)`** 修改 `tmp` 的内容——**修改已分配内存**。

**契约必须纯**（见 [[15-122-01-Contracts]]），因为 `//@` 注解的执行策略依赖编译选项：

- **不带 `-d`**：验证器静态检查后**丢弃**契约，运行时**完全不执行**。`tmp` 不被创建、不被弹空。
- **带 `-d`**：契约在运行时**每轮循环都执行一次**。每次调用 `stack_sorted_ascending` 都会**新建一个完整副本**并**把它弹空**。

**强行写进去、带 `-d` 编译的后果**：

1. **内存爆炸**：若外层循环 `n` 轮，每轮分配一个大小为 `|tmp|` 的副本，总分配量 `O(n²)` 个节点。**在 `coin` 里可能直接耗尽内存**。
2. **时间爆炸**：`stack_sorted_ascending` 本身是 `O(|tmp|)`，每轮调用 → `O(n²)` 额外开销。
3. **最严重：语义不确定**。同一份源码在 `-d` 与不带 `-d` 下**行为不同**——不带 `-d` 时 `tmp` 从未被复制，带 `-d` 时每轮都在堆上折腾。**若程序有依赖内存分配失败的边界行为，两种编译会给出不同结果。** 讲义原文：「a program may produce different outcome depending on whether it is compiled with or without the `-d` flag.」

**能不能修**：讲义明确说**不能**——「There is no way to write pure versions of these functions based on the given interface of our stack library.」因为接口只有 `push`/`pop`/`stack_empty`，**任何读取都必须先 `pop`，而 `pop` 就是修改**。要写纯版本，接口必须**扩展**（例如导出纯的 `stack_to_array`，或让库内部维护长度并提供纯的 `stack_size_lib`）。

**这正是「接口设计限制客户端规格强度」的实例**：抽象越彻底，客户端的契约越弱。

</details>

## 12. 进一步学习

- 上一讲：[[15-122-08-Libraries]] —— 抽象类型、`typedef ______* ssa_t;`、数据结构不变式；本讲把同一套方法用在两个更简单的结构上，**只谈接口不谈实现**。
- 下一讲：[[15-122-10-Linked-Lists]] —— **实现**栈与队列：用指针把节点串起来，`NULL` 从「错误值」变成「链表结束标记」，`push`/`pop` 变成 `O(1)` 的指针操作。
- 后续讲次：[[15-122-11-Unbounded-Arrays]] —— 用数组实现「无界」容器，引入**摊还分析**；[[15-122-12-Hashing]]、[[15-122-13-Hash-Dictionaries]] —— 另一个抽象类型（字典）。
- 相关基础：[[15-122-03-Arrays]]（别名现象）、[[15-122-05-Big-O]]（`O(1)` 与 `O(n)`）、[[15-122-07-Quicksort]]（`is_permutation` 的不纯性）。
- 课程入口：[[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]]、[[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 术语查询：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Stack、Queue、LIFO、FIFO、push、pop、peek、enq、deq、Abstraction、Alias、Purity、Destructive Operation 等条目）。
- 延伸阅读：Barbara Liskov & Stephen Zilles 的 "Programming with Abstract Data Types"（1974）——抽象类型的奠基论文；本讲的 `stack_t`/`queue_t` 是它最朴素的实例。
