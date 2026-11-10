---
course: CMU 15-122
course_name: Imperative Computation
semester: Fall 2026
lecture_id: L10
topic: Linked Lists
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-122
  - 链表
  - C0
---

# 第 10 讲：链表（Linked Lists）

## 1. 本节学习目标

学完本讲后，你应该能够：

1. 写出 `struct list_node` 的递归定义，并说明**为什么递归必须发生在指针或数组之下**（`struct infinite` 为什么被拒绝）。
2. 区分**具体类型（concrete type）**与**抽象类型（abstract type）**，说明链表为什么是前者、栈/队列为什么是后者。
3. 用「**下界包含、上界排除**」精确描述链表**段（segment）** `[start, end)`，并说明为什么 `start == end` 表示空段。
4. 解释为什么 `a1` 与 `a3` 指向**内容相同**的节点却 `a1 != a3`。
5. 写出 `is_segment` 的**递归 / while / for** 三种实现，并说明它们**共同的致命缺陷**（遇到环不终止）。
6. 用 **Floyd 龟兔算法**写出 `is_acyclic`，并证明：有环时必然相遇、无环时兔子先撞 `NULL`。
7. 说明为什么 `//@assert t != NULL` **无法**用「`t != NULL` 当不变式」证出，而必须补 `is_segment(t, h)`。
8. 说明循环退出时 `h == t` **不足以**证明有环，必须再补 `is_segment(t->next, h)`。
9. 画出**带头节点（header）+ 哑节点（dummy node）**的链表队列，写出 `is_queue` 的表示不变式。
10. 逐行证明 `queue_new` / `enq` / `deq` **保持** `is_queue`，并说明 `deq` 里两次解引用为什么安全。
11. 说明 `deq` **不释放**被弹出的节点为什么不会内存泄漏（不可达 → 垃圾回收）。
12. 解释**共享（sharing）**为什么对栈安全、对队列危险，并给出破坏队列的具体操作序列。
13. 推导 `ith` 是 `O(n)`，从而链表上的二分查找是 **`O(n log n)`** 而不是 `O(log n)`。
14. 找出「环出现在 `end` 之后」这个 `is_acyclic + is_segment` 漏判的情形，并用 `is_definite_segment` 修补。

## 2. 前置知识

- [[15-122-09-Stacks-and-Queues]]：本讲是它的**实现篇**——上一讲只给接口，这一讲用链表把接口填上。
- [[15-122-08-Libraries]]：抽象类型、接口与实现分离、`is_ssa` 表示不变式。本讲的 `is_queue`/`is_stack` 是同一套方法。
- [[15-122-01-Contracts]]：`requires`/`ensures`/`loop_invariant`/`assert`；**规格函数必须安全**（不越界、不解引用 `NULL`、不除零）。
- [[15-122-06-Binary-Search]]：习题 5 要在链表上重写二分查找，直接复用那三条不变式。
- [[15-122-05-Big-O]]：`O(n)` 与 `O(n log n)`；「每次访问 `O(n)` × `log n` 次访问」。
- [[15-122-03-Arrays]]：数组的「隐式信息」是下标——本讲开篇的核心洞察就是**把下标显式化为地址**。

## 3. 核心概念

**Linked List（链表）**：每个元素存在一个**节点（node）**里，节点包含**数据**与**指向下一个节点的指针**。

**Node（节点）**：`struct list_node { elem data; struct list_node* next; };`。

**Recursive Type（递归类型）**：结构体里含有指向**同类型**的指针。C0 允许，但**递归必须发生在指针或数组之下**。

**Concrete Type（具体类型）**：客户端**知道并可以使用**其内部结构。链表是具体类型——本讲**不**给链表建接口。

**Abstract Type（抽象类型）**：实现被接口隐藏，客户端只能用接口函数。栈与队列是抽象类型。

**Segment（段）**：从 `start`（含）到 `end`（不含）的一串节点，记作 `[start, end)`。

**Dummy Node（哑节点）**：不存放有效数据的哨兵节点。队列的 `back` 指向它，它的存在让 `enq` 不必特判「队列为空」。

**Header（头节点 / 头部结构）**：只存指针、不存元素的 `struct`，例如 `struct queue_header { list* front; list* back; };`。

**Representation Invariant（表示不变式）**：一个 `struct` 何时算「合法」的判据，如 `is_queue`。

**Cycle（环）**：某个节点的 `next` 指回链表中更早的节点，形成无限循环。

**Tortoise and Hare（龟兔算法）**：一个慢指针每次走 1 步、一个快指针每次走 2 步的环检测算法（Floyd 1967）。

**Sharing（共享）**：多个数据结构共用同一批节点。对栈安全，对队列危险。

**Unreachable（不可达）**：没有任何指针能到达的内存。C0 的垃圾回收器会回收它。

## 4. 通俗理解

**数组 vs 链表 = 编号座位 vs 手拉手**。数组像电影院的座位，第 5 排第 3 座，你可以**直接走过去**（`O(1)`）；链表像一队手拉手的人，你要找第 5 个人，必须**从第一个开始数**（`O(n)`）。但要在队伍中间**插一个人**，链表只要**松开两只手、重新拉上**（`O(1)`），而电影院要**所有人往后挪一个座位**（`O(n)`）。

**讲义开篇的洞察值得单独抄下来**：

> **「arrays contain implicit information, namely the indices of elements, which can be made explicit as the addresses of the nodes of a linked list.」**

数组的「下标」是**隐式**的——它不占内存，因为位置本身就是身份。链表把这件事**显式化**：每个节点里存一个 `next` 指针，就是「下一个是谁」的地址。**代价是多花一个指针的内存，收益是插入删除不再需要搬家。** 讲义把这叫作**权衡（trade-off）**。

**为什么 `struct infinite` 会被拒绝**：编译器要为一个 `struct` 分配**固定大小**的内存。若 `struct infinite` 里直接嵌一个 `struct infinite`，那它的大小是 `4 + 4 + 4 + ...` **无穷大**。而指针的大小**永远是一个字**（在 C0 里是 4 字节），所以 `struct list_node* next` 让递归「落地」了。**一句话：递归必须有底，指针就是那个底。**

**为什么链表是「具体类型」而栈是「抽象类型」**：讲义说得很直白——链表**没有接口**，「we do not construct an interface and a layer of abstraction around them. When we use them we know about and exploit their precise internal structure.」你直接写 `l->next`、直接 `alloc(list)`。而栈/队列**有接口**，客户端不许知道里面是数组还是链表。**具体类型的代价是「一次定型，永不改进」**（"Concrete types are cast into concrete once and for all"）——你不能哪天偷偷把链表换成数组而不改客户端代码。

**为什么段要「含头不含尾」**：这是 C 语言家族的一贯传统（`for (i = 0; i < n; i++)`、`[begin, end)` 迭代器）。**最大的好处是「空段」有自然表示**：`start == end` 就是空段，不需要特判。**第二个好处是长度 = `end - start`（数组情形）或「走几步到 `end`」（链表情形），不用 `+1`/`-1` 的纠缠。**

**为什么 `a1 != a3`**：讲义特意强调这一点。假设 `a1` 和 `a3` 指向的两个节点**内容完全一样**（`data` 都是 `3`，`next` 都指向同一个节点），但它们是**两块不同的内存**。C0 比较指针时比的是**地址**，不是内容。**这是「指针相等」与「值相等」的根本区别**——后面 `is_segment` 全靠**指针相等**来判断「走到了吗」。

**龟兔算法的直觉**：环形跑道上，兔子速度是乌龟的两倍。**兔子一定会在某一刻从后面追上乌龟**（相对速度 1 圈/单位时间，必然追上）。如果跑道是**直的**（无环），兔子先跑到终点。**这个比喻的每一半都对应一条证明义务**：追上 → 有环；先到终点 → 无环。

**为什么共享对队列是灾难**：想象两个队列共用同一段链表。队列 A 的 `back` 指向某个哑节点。**A 往这个哑节点里写数据**（`enq` 的正常操作），而**这个哑节点恰好是队列 B 的有效数据节点**。**A 的一次普通入队，静默改掉了 B 的一个元素。** 栈不会出这个问题，因为**栈只在 `top` 一端操作**，而共享的总是「尾巴」那一端。讲义一句话总结：**「Sharing works wonderfully for stacks, but not for queues.」**

## 5. 原理与推导

### 5.1 递归类型：为什么指针是必需的

```c0
struct list_node {
  elem data;
  struct list_node* next;
};
typedef struct list_node list;
```

**`elem` 是什么**：讲义明确说「there will be a type definition elsewhere telling C0 what `elem` is supposed to be」，并强调「Keeping this in mind ensures that none of the code actually depends on what type is chosen」。**这是「用宏/别名做伪泛型」的朴素做法**——代码里只出现 `elem`，将来 `typedef int elem;` 或 `typedef string elem;` 都不用改。

**两种书写顺序等价**：

```c0
// 顺序一：先定义 struct，再 typedef
struct list_node { elem data; struct list_node* next; };
typedef struct list_node list;

// 顺序二：先 typedef，再定义 struct（struct 内部就能用 list*）
typedef struct list_node list;
struct list_node { elem data; list* next; };
```

**顺序二更好**，因为结构体内部不必重复写 `struct list_node*`。C0 允许**不完全类型（incomplete type）**的前向声明：`typedef struct list_node list;` 只告诉编译器「有这么个名字」，具体布局稍后补上。**指针的大小与所指类型无关，所以可以先声明后定义。**

**递归的合法边界**：

```c0
struct infinite { int x; struct infinite next; }   // 被 C0 拒绝
```

**为什么拒绝**：编译器要算 `sizeof(struct infinite)`，而它等于 `sizeof(int) + sizeof(struct infinite)`，**方程无解**（除非是 0，但 `int` 不是 0）。**这是「无限递归」在类型层面的表现。**

**规则（讲义原文）**：

> **「a struct can be recursive, but the recursion must occur beneath a pointer or array type, whose values are addresses. This allows a ﬁnite representation for values of the struct type.」**

**「beneath a pointer or array type」**：指针与数组存的是**地址**，地址的大小**固定**（与所指内容无关）。故 `struct list_node* next` 只占一个字，`sizeof(struct list_node)` 有限。

**为什么数组也允许**：`elem data[]` 里 `data` 也是**地址**（见 [[15-122-03-Arrays]]，C0 数组变量存的是地址），大小固定。

**为什么 `struct list_node next;`（无星号）不行**：那是**直接嵌入**，不是地址，大小无限。

### 5.2 段的语义与「指针相等 ≠ 内容相等」

**定义**：段 `[start, end)` 是从 `start` 出发，沿 `next` 走若干步（可以是 0 步）恰好到达 `end` 的那串节点，**包含 `start`，不含 `end`**。

**推论（讲义原文）**：「for any non-NULL list node pointer `l`, a segment from `l` to `l` is empty (contains no data)」。

**用讲义的图（p3）验证**：设 `a1 → a2 → a3 → a4 → NULL`，数据依次为 `3, 7, 3, ?`。

| 段 | 包含的节点 | 数据序列 |
|---|---|---|
| `[a1, a4)` | `a1, a2, a3` | `3, 7, 3` |
| `[a2, a3)` | `a2` | `7` |
| `[a1, a1)` | 无 | 空 |

**长度公式**：`len([s, e)) = 从 s 走到 e 的步数`。故 `len([a1,a4)) = 3`、`len([a2,a3)) = 1`、`len([a1,a1)) = 0`。**这就是「含头不含尾」带来的清爽：长度 = 步数，不用 `+1`。**

**`a1 != a3` 的关键性**：`a1` 与 `a3` 指向的两个节点 `data` 都是 `3`（讲义 p3 的图里确实如此），但：

- **内容相等**：`a1->data == a3->data`（都是 `3`）。
- **指针不等**：`a1 != a3`（不同地址）。

**`is_segment` 必须用指针相等**：段的存在性问的是「沿 `next` 能否**走到那个地址**」，不是「能否走到一个**内容一样**的节点」。若用 `data` 比较，`[a1, a4)` 会在走到 `a3` 时误判为「到了」（因为 `a3->data == 3 == a1->data`）——**完全错误**。

**这是本讲第一个「容易混淆」的点**：**指针是身份，内容是属性。** 判断「是不是同一个」永远用指针。

### 5.3 `is_segment` 的三种写法与共同缺陷

**递归版**（p4）：

```c0
bool is_segment(list* start, list* end) {
  if (start == NULL) return false;
  if (start == end) return true;
  return is_segment(start->next, end);
}
```

**终止性**：每次递归 `start` 前进一格。若链表**有限且无环**，必然在有限步内遇到 `end`（返回 `true`）或 `NULL`（返回 `false`）。**注意两个 base case 的顺序**：先查 `NULL`，因为「走到了 `NULL` 而没遇到 `end`」意味着失败。

**while 版**（p4）：

```c0
bool is_segment(list* start, list* end) {
  list* l = start;
  while (l != NULL) {
    if (l == end) return true;
    l = l->next;
  }
  return false;
}
```

**等价性**：循环不变式可取 `l` 是从 `start` 走若干步到达的节点，且**沿途所有节点都不等于 `end`**。退出时 `l == NULL`，故 `end` 不在路径上，返回 `false`。

**for 版**（p4）：

```c0
bool is_segment(list* start, list* end) {
  for (list* p = start; p != NULL; p = p->next) {
    if (p == end) return true;
  }
  return false;
}
```

**与 while 版逐字等价**，只是把「初始化 / 守卫 / 步进」塞进 `for` 头。

**三者的共同缺陷（讲义原文）**：

> **「every one of these implementations of `is_segment` has the same problem: if given a circular linked-list structure, the speciﬁcation function `is_segment` may not terminate.」**

**证明**：设链表有环，且 `end` **不在**环上。则 `l` 沿环无限转，**永远不等于 `end`，也永远不等于 `NULL`**，`while (l != NULL)` 守卫**恒真**，**循环不终止**。

**为什么这是「规格函数」的严重问题**：`is_segment` 出现在 `//@requires`/`//@ensures` 里。若它不终止：

- **带 `-d`**：每次检查契约都**卡死**，程序无法运行。
- **不带 `-d`**：契约不执行，**表面上没事**——但验证器若试图静态推理也会卡住。

**讲义的安全要求（p5）**：

> **「We do treat it as strictly necessary that our specification functions should always be safe — they should never divide by zero, access an array out of bounds, or dereference a null pointer.」**

**注意「safe」与「terminating」的区别**：讲义说规格函数**必须安全**（不崩溃），并说「Whenever possible ... should return `true` or `false` rather than not terminating or raising an assertion violation」——**「whenever possible」意味着终止性是「尽量」，而安全性是「必须」**。`is_segment` 违反的是**终止性**，不是安全性（它不会崩溃，只是不返回）。**这个区别很重要**：不终止会让验证器卡住，但不会产生错误的验证结果。

### 5.4 Floyd 龟兔算法：`is_acyclic` 与正确性推导

**代码（p7）**：

```c0
bool is_acyclic(list* start) {
  if (start == NULL) return true;
  list* h = start->next;   // hare
  list* t = start;         // tortoise
  while (h != t) {
    if (h == NULL || h->next == NULL) return true;
    h = h->next->next;
    //@assert t != NULL;    // faster hare hits NULL quicker
    t = t->next;
  }
  //@assert h == t;
  return false;
}
```

**初始设置的精妙**：`t = start`、`h = start->next`。**为什么不让两者都从 `start` 出发**？因为那样 `h != t` 一开始就为假，循环一次都不执行，直接返回 `false`（判定有环）——**对任何链表都错**。**让兔子先跑一步，才能让「相遇」成为有意义的信号。**

**无环情形的终止性**：兔子每轮走 2 步，乌龟走 1 步。若链表无环（长度有限），兔子**必然先到达 `NULL` 或 `NULL` 前一个节点**。检查 `if (h == NULL || h->next == NULL) return true;` 正是在**兔子还能安全走两步**时放行，否则判定「到终点了，无环」。

**为什么 `||` 的短路求值是必需的**：`h->next` 在 `h == NULL` 时会**解引用空指针**。靠 `||` 的**短路（short-circuit）**——左边为真时右边不求值——才安全。讲义原文：「in the condition inside the loop we exploit the short-circuiting evaluation of the logical or `||` so we only follow the `next` pointer for `h` when we know it is not `NULL`.」

**这是 C0/C 里指针代码的标准防御模式**：**先查 `NULL`，再解引用。** 后面 `h->next->next` 之所以安全，也是因为上一行刚确认了 `h != NULL && h->next != NULL`。

**有环情形的相遇证明**：设环长为 `L`（`L >= 1`）。进入环后，兔子与乌龟都在环上。设某一时刻兔子在乌龟**前方** `d` 步（沿前进方向，`0 <= d < L`；`d == 0` 即已相遇）。

- 一轮之后：兔子前进 2，乌龟前进 1，**距离缩小 1**（模 `L`）：`d' = (d - 1) mod L`。
- 若 `d == 0`：已相遇，循环退出。
- 否则 `d` 每轮减 1，**至多 `L - 1` 轮后 `d == 0`**。

**故必然相遇，且至多 `L` 轮。** 结合「无环时兔子先撞 `NULL`」，得：

**`is_acyclic` 必然终止**：无环时步数 `<= n/2`；有环时步数 `<= 进入环的步数 + L`。**两种情形都是有限的。**

**复杂度**：`O(n)` 时间、`O(1)` 空间。**这是龟兔算法最大的优势**——比「用哈希表记录访问过的节点」省内存。

**`//@assert t != NULL;` 的位置**：它写在 `h = h->next->next;` **之后**、`t = t->next;` **之前**。注释说「faster hare hits `NULL` quicker」——意思是**如果兔子会撞 `NULL`，那它已经在上面的 `if` 里返回了**，所以能走到这一行就说明兔子没撞 `NULL`，而乌龟在兔子后面，更不可能撞 `NULL`。**这个论证是对的，但需要形式化**——见 5.5。

### 5.5 习题 6：为什么 `t != NULL` 单独当不变式证不出来

**先试最自然的候选**：`//@loop_invariant t != NULL;`

- **INIT**：`t = start`。但 `start` 可能为 `NULL` 吗？**不会**——函数第一行 `if (start == NULL) return true;` 已经排除了。故 `t != NULL` 初始成立。✅
- **PRES**：假设某轮开始 `t != NULL`。循环体执行 `t = t->next;`。**要证 `t->next != NULL`，但 `t != NULL` 完全没说 `t->next` 是什么！** `t->next` 可以是 `NULL`（`t` 是最后一个节点），也可以是任何地址。**保持性失败。** ❌

**讲义原文**：

> **「we stumble on preservation however: knowing that `t != NULL` at the start of an arbitrary iteration of the loop does not allow us to conclude anything about the value of `t->next`.」**

**缺的是什么**：**乌龟与兔子之间的「连通性」**。讲义原文：

> **「The crucial loop invariant we are missing is the information that the tortoise `t` will be able to travel to the current position of the hare `h` by following `next` pointers.」**

**补上 `//@loop_invariant is_segment(t, h);`**：

```c0
bool is_acyclic(list* start) {
  if (start == NULL) return true;
  if (start->next == NULL) return true;
  list* h = start->next;   // hare
  list* t = start;         // tortoise
  while (h != t)
  //@loop_invariant is_segment(t, h);
  {
    if (h->next == NULL || h->next->next == NULL) return true;
    h = h->next->next;
    t = t->next;
  }
  //@assert h == t;
  return false;
}
```

**注意这段代码相比 p7 版有三处改动**（讲义 p25 的解答版）：

1. **新增 `if (start->next == NULL) return true;`**——因为循环条件改成了 `h->next == NULL || h->next->next == NULL`，若 `start->next == NULL` 则 `h == NULL`，此时 `h->next` **会解引用空指针**。**必须先挡掉。** 原版靠 `h == NULL ||` 挡住，新版没有这一项，所以要在入口挡。
2. **`h == NULL` 从循环内检查移到入口**——同上。
3. **加了 `is_segment(t, h)` 不变式**。

**`is_segment(t, h)` 如何同时解决两个问题**：

- **`t != NULL`**：讲义原文「The added loop invariant implies that `t` is not `NULL` since, whenever `is_segment(start, end)` is true, neither `start` nor `end` can be `NULL`.」——**因为 `is_segment` 的定义第一行就是 `if (start == NULL) return false;`，所以它返回 `true` 蕴含 `start != NULL` 且 `end != NULL`。** 于是 `t != NULL` 自动可得，`//@assert t != NULL;` 无需再写。
- **保持性**：从 `is_segment(t, h)` 与「兔子走两步、乌龟走一步」可推出 `is_segment(t->next, h->next->next)`——**因为 `[t, h)` 这条路径上，把两端各往前推一格仍然是子路径**。这里需要 `h != t`（循环守卫）保证路径**非空**，从而 `t->next` 与 `h->next` 都存在。

**`is_segment` 不能把 `is_acyclic` 当前置**：讲义指出，若给 `is_segment` 加上 `//@requires is_acyclic(start);`，两个规格函数就**互递归**了（`is_acyclic` 的不变式用 `is_segment`，`is_segment` 的前置用 `is_acyclic`），「which would greatly complicate proving the validity of our added loop invariant, or make the proof impossible if this could trigger an inﬁnite recursion」。**所幸不会无限递归**——理由是复杂度分析：兔子与乌龟的距离不超过环长。**但讲义特意点明「This is not a point-to proof however」**——**复杂度论证不是指向式推理（point-to reasoning）**，验证器不认。**这是「人类能证、机器不能证」的典型例子。**

### 5.6 退出时 `h == t` 不足以证明有环

**循环退出时**：守卫 `h != t` 为假，故 `h == t`。**但「两个指针相等」并不意味着「在环上」。**

**反例**：**任何空段都有 `start == end`**。若 `h` 与 `t` 都走到某个 `NULL` 前的节点并且恰好相等……更直接地说：**单节点链表 `start → NULL`**（但这种情况入口 `start->next == NULL` 已经返回 `true` 了）。真正的问题是：**`h == t` 只说明两者当前指向同一节点，不说明「从 `t->next` 能回到 `t`」**。

讲义原文：

> **「At the end of the loop, we know that `h == t` by the loop guard. This is not sufﬁcient to prove that the node they point to is part of a cycle: any empty segment has its start pointer equal to its end pointer whether there is cycle or not. For a cycle to be present, we need to know that we can reach `t` from `t->next`.」**

**补什么**：讲义给出答案——`//@loop_invariant is_segment(t->next, h);`

**为什么这条能证「有环」**：

- **INIT**：`t = start`、`h = start->next`，故 `t->next == h`，`is_segment(h, h)` 是**空段**，为真。✅
- **PRES**：每轮 `h` 走两步、`t` 走一步，`is_segment(t->next, h)` 描述的是「从乌龟的下一个节点能走到兔子」。两端同步前进后仍成立。✅
- **EXIT**：守卫给出 `h == t`；不变式给出 `is_segment(t->next, h)`，即 `is_segment(t->next, t)`——**从 `t->next` 能走回 `t`，这就是环的定义。** ✅

**两条不变式合起来的完整证明**：

```
//@loop_invariant is_segment(t, h);        // 连通性 → t != NULL
//@loop_invariant is_segment(t->next, h);  // 退出时 → 有环
```

**注意 `is_segment(t->next, h)` 在 INIT 时要求 `t->next` 存在**——这正是为什么改写版要**在入口挡掉 `start->next == NULL`**：否则 `t->next` 是 `NULL`，`is_segment(NULL, NULL)` 返回 `false`，INIT 失败。**两处改动是配套的，不是各自独立的。** 这是本讲最精妙的一处工程细节。

### 5.7 队列的链表表示与 `is_queue`

**结构（p8）**：

```c0
typedef struct queue_header queue;
struct queue_header {
  list* front;
  list* back;
};
typedef queue* queue_t;
```

**为什么需要两个指针**：`deq` 从队首删、`enq` 往队尾加，**两端都要 `O(1)` 访问**。只有 `front` 的话，`enq` 要遍历整个链表（`O(n)`）；只有 `back` 的话，`deq` 要遍历。

**哑节点的作用（p8 原文）**：

> **「It is convenient to have the `back` pointer point to one element past the end of the queue. Therefore, there is always one extra element at the end of the queue which does not have valid data or next pointer. We call it the dummy node.」**

**为什么 `back` 指向「末尾之后一格」而不是末尾本身**：

| 设计 | `enq` 的实现 | 是否需要特判空队列 |
|---|---|---|
| `back` 指向**最后一个元素** | 新建节点 → 挂到 `back->next` → `back = 新节点` | **需要**：空队列时 `back` 为 `NULL`，得特判 |
| `back` 指向**哑节点**（末尾之后） | 把 `x` 写进 `back->data` → `back->next = 新哑节点` → `back = 新哑节点` | **不需要**：空队列时 `back` 指向哑节点，同样可写 |

**这就是「哨兵（sentinel）」的全部价值：消灭边界特判。** 代价是**永远多一个节点**（空队列也有一个哑节点）。讲义原文：「with one element already allocated even if the queue is empty」。

**注意哑节点的 `data` 与 `next` 都「无效」**：刚 `alloc` 出来时 `data` 是默认值、`next` 是 `NULL`，但**表示不变式不检查它们**。`enq` 会往 `data` 里写，`next` 由下一次 `enq` 填。

**表示不变式（p9）**：

```c0
bool is_queue(queue* Q) {
  return Q != NULL
      && is_acyclic(Q->front)
      && is_segment(Q->front, Q->back);
}
```

**三条各管什么**：

| 条件 | 作用 |
|---|---|
| `Q != NULL` | 头节点本身存在（解引用 `Q->front` 的前提） |
| `is_acyclic(Q->front)` | 底层链表**无环**——这是 `is_segment` 能终止的前提 |
| `is_segment(Q->front, Q->back)` | 从 `front` **能走到** `back`，且**两者都非 `NULL`** |

**为什么必须同时有第 2、3 条**：`is_segment` 在有环时**不终止**（5.3）。故**必须先证无环，再调 `is_segment`**。讲义原文：「the `is_segment` function we already wrote enforces this」（指「`front` 与 `back` 都非 `NULL`」）。**顺序不能反**——`is_acyclic` 在前，`is_segment` 在后。

**`queue_empty`（p9）**：

```c0
bool queue_empty(queue* Q)
//@requires is_queue(Q);
{
  return Q->front == Q->back;
}
```

**为什么这样判空**：`front == back` 意味着段 `[front, back)` 是**空段**——正好对应「队列里没有元素，`front` 与 `back` 都指向同一个哑节点」。**这是「含头不含尾」语义的直接红利：判空就是「起点等于终点」，不需要计数器。**

**`//@requires is_queue(Q)` 的必要性**：`Q->front` 要求 `Q != NULL`，而这条正是 `is_queue` 的第一项。**没有前置，`Q->front` 不安全。**

**讲义的一句通用原则（p9）**：

> **「Generally, when working with a data structure, we should always require and ensure that its invariants are satisﬁed in the pre- and post-conditions of the functions that manipulate it. Inside the function, we will generally temporarily violate the invariants.」**

**「函数内部可以暂时违反不变式」是关键**——这是**唯一**允许违反的地方。`enq` 的中间状态（`back->next` 已改但 `back` 未改）就违反 `is_segment`，但只要**返回前修好**就行。

### 5.8 `queue_new` / `enq` / `deq` 的保持性

**`queue_new`（p9）**：

```c0
queue* queue_new()
//@ensures is_queue(\result);
//@ensures queue_empty(\result);
{
  queue* Q = alloc(queue);        // Create header
  list* dummy = alloc(list);      // Create dummy node
  Q->front = dummy;               // Point front
  Q->back = dummy;                // and back to dummy node
  return Q;
}
```

**逐条验证 `is_queue(Q)`**：

| 条件 | 为什么成立 |
|---|---|
| `Q != NULL` | `alloc` 从不返回 `NULL`（见 [[15-122-08-Libraries]]） |
| `is_acyclic(Q->front)` | `Q->front == dummy`，而 `dummy->next` 是 `alloc` 的默认值 `NULL`，单节点链表**无环** |
| `is_segment(Q->front, Q->back)` | `front == back == dummy`，**空段**，为真 |

**验证 `queue_empty(Q)`**：`Q->front == Q->back`（都是 `dummy`）。✅

**注意 `dummy->data` 与 `dummy->next` 未显式初始化**：讲义说「We do not initialize the list element because its contents are irrelevant, according to our representation.」但紧接着补一句**最佳实践**：

> **「it is good practice to always initialize memory if we care about its contents, even if it happens to be the same as the default value placed there.」**

**为什么「显式写成默认值」是好习惯**：读者一眼看到「这里我**有意**留成默认值」，而不是「作者**忘了**初始化」。**可读性 > 省一行代码。** 这与 [[15-122-08-Libraries]] 里「显式写 `A->length` 而不是依赖默认值」是同一种态度。

**`enq`（p10）**：

```c0
void enq(queue* Q, elem x)
//@requires is_queue(Q);
//@ensures is_queue(Q);
{
  list* new_dummy = alloc(list);   // Create a new dummy node
  Q->back->data = x;               // Store x in old dummy node
  Q->back->next = new_dummy;
  Q->back = new_dummy;
}
```

**四步的含义**（讲义说「You should draw yourself a diagram before you write this kind of code」）：

1. **`new_dummy = alloc(list)`**：先造好新哑节点，`data` 默认、`next` 为 `NULL`。
2. **`Q->back->data = x`**：把**旧哑节点**「转正」为真正的数据节点。
3. **`Q->back->next = new_dummy`**：把旧哑节点接上新哑节点。
4. **`Q->back = new_dummy`**：`back` 前移到新哑节点。

**为什么第 1 步必须在第 2 步之前**：若先改 `Q->back->data`，再 `alloc`，`alloc` 理论上可能失败（C0 里不会，但**好习惯**是「先备好资源，再动结构」）。**更重要的是**：`alloc` 之后**旧哑节点的地址**必须还保存在 `Q->back` 里才能写 `data`——所以 `Q->back` **最后**才改。

**保持性验证**：

- **`Q != NULL`**：`Q` 未变。✅
- **`is_acyclic(Q->front)`**：`front` 未变，底层链表只**追加**了一个节点，无环性不变。✅
- **`is_segment(Q->front, Q->back)`**：原来 `[front, old_back)` 是段；现在 `old_back->next = new_dummy` 且 `back = new_dummy`，故 `[front, new_dummy)` = `[front, old_back)` 再接一格，**仍是段**。✅

**关键点：`old_back` 从「段外」变成了「段内」**。`enq` 的语义就是「把哑节点转正 + 造新哑节点」。**这是「用哨兵实现入队」的全部秘密。**

**`deq`（p11）**：

```c0
elem deq(queue* Q)
//@requires is_queue(Q);
//@requires !queue_empty(Q);
//@ensures is_queue(Q);
{
  elem x = Q->front->data;
  Q->front = Q->front->next;
  return x;
}
```

**只有两行实质代码**：存下队首数据，`front` 前移一格。**被跳过的那个节点没有被释放，也没有被置 `NULL`。**

**保持性验证（p12 讲义逐条给出）**：

> **「We see that `Q->front` is okay, because by the first test we know that `Q != NULL` is the precondition holds. By the third test we see that both `Q->front` and `Q->back` are not null, and we can therefore dereference them.」**

**解引用安全性**：`Q->front->data` 是**两次解引用**：

1. `Q->front`：要求 `Q != NULL` ← `is_queue` 第一条。
2. `->data`：要求 `Q->front != NULL` ← `is_segment(Q->front, Q->back)` 为真蕴含 `Q->front != NULL`（5.3 的 base case）。

**`front = front->next` 的安全性**：要求 `Q->front->next != NULL`。讲义原文：

> **「Because we know that the queue is not empty (second precondition of `deq`) and therefore `Q->front != Q->back`. Because `Q->front` to `Q->back` is a valid non-empty segment, `Q->front->next` cannot be null.」**

**这段推理值得展开**：

- `!queue_empty(Q)` 即 `Q->front != Q->back`。
- `is_segment(Q->front, Q->back)` 为真，且两端**不相等**，故段**非空**——`Q->front` 到 `Q->back` 至少要走 1 步。
- 「至少走 1 步」意味着 `Q->front->next` **存在**（不是 `NULL`）。
- 于是 `Q->front = Q->front->next` 合法。

**若漏掉 `!queue_empty(Q)` 前置会怎样**：`front == back`，段为空（0 步），`front->next` **可能就是 `NULL`**（空队列的哑节点刚 `alloc` 出来，`next` 是默认 `NULL`）。执行 `Q->front = NULL` 后，`is_queue` 的 `is_segment(NULL, back)` **返回 `false`**——不变式破坏。**下一次 `deq` 就会解引用 `NULL` 崩溃。** 这就是习题 9 讨论的情形（见 5.13）。

**保持性**：新 `front` 是旧 `front->next`，它到 `back` 的路径是旧路径**去掉头一格**，仍是段；无环性不变。✅

**`deq` 不释放节点——为什么不泄漏**：讲义原文：

> **「If the interface is respected there cannot be another pointer to the item at the front of the queue, so it becomes unreachable: no operation of the remainder of the running programming could ever refer to it. This means that the garbage collector of the C0 runtime system will recycle this list item when it runs short of space.」**

**两个条件缺一不可**：

1. **「If the interface is respected」**——客户端只能用 `enq`/`deq`/`queue_empty`/`queue_new`，**拿不到内部节点指针**。所以弹出的节点**没有任何外部引用**。
2. **C0 有垃圾回收（garbage collection）**——不可达的内存会被自动回收。**这是 C0 与标准 C 的关键区别**：C 里同样的代码会**内存泄漏**，必须 `free`。

**「If the interface is respected」这个前提很重要**：若客户端偷偷存了 `Q->front` 的副本（违反抽象），那个节点就**可达**，不会被回收，而且**客户端手里的指针会指向一个「已经不在队列里」的节点**——这是悬垂指针（dangling pointer）的温床。**抽象不只是「礼貌」，它是内存安全的前提。**

### 5.9 栈的链表表示与 `pop`/`push`

**结构（p13）**：

```c0
typedef struct stack_header stack;
struct stack_header {
  list* top;
  list* floor;
};
bool is_stack(stack* S) {
  return S != NULL
      && is_acyclic(S->top)
      && is_segment(S->top, S->floor);
}
typedef stack* stack_t;
```

**`floor` 是「结构性冗余」**：讲义原文「Since we do not perform operations on the other side of the stack, we do not necessarily need a pointer to the other end. For structural reasons, and in order to identify the similarities with the queue implementation, we still decide to remember a pointer to a dummy node right after the last element (or bottom) of the stack.」**它的唯一用途是让 `is_stack` 与 `is_queue` 长得一模一样**——`is_segment(S->top, S->floor)` 与 `is_segment(Q->front, Q->back)` 完全同构。讲义紧接着说「The `floor` pointer of the stack is otherwise unused」，并在第 6 节把它**删掉**（见 5.10）。

**`pop`（p13）**：

```c0
elem pop(stack* S)
//@requires is_stack(S);
//@requires !stack_empty(S);
//@ensures is_stack(S);
{
  elem x = S->top->data;
  S->top = S->top->next;
  return x;
}
```

**与 `deq` 逐字同构**——只是 `front` 换成 `top`。**这是本讲「栈与队列的链表实现只差一个指针名字」的具体体现**（呼应 [[15-122-09-Stacks-and-Queues]] 5.3「形状相同、语义不同」）。

**`push`（p14）**：

```c0
void push(stack* S, elem x)
//@requires is_stack(S);
//@ensures is_stack(S);
{
  list* p = alloc(list);   // Allocate a new top node
  p->data = x;
  p->next = S->top;
  S->top = p;
}
```

**四步**：造节点 → 填数据 → **新节点的 `next` 指向旧 `top`** → `top` 前移到新节点。**这是「头插法（prepend）」**。

**与 `enq` 的对称性**：

| | `enq`（队尾插入） | `push`（栈顶插入） |
|---|---|---|
| 先做什么 | `alloc` 新哑节点 | `alloc` 新节点 |
| 往哪写数据 | **旧**哑节点（转正） | **新**节点 |
| 指针怎么接 | `old_back->next = new_dummy` | `p->next = S->top` |
| 指针怎么移 | `back = new_dummy` | `top = p` |
| 是否用哑节点 | **是**（队尾） | **否**（栈顶不需要） |

**为什么栈顶不需要哑节点**：`push` 只在一端操作，**没有「另一端也要 `O(1)`」的需求**，也就不需要「末尾之后一格」的哨兵。`floor` 是**为了结构对称**才留的，不是功能需要。

**保持性**：`top` 前移到新节点，`[p, floor)` = `p` 接上 `[old_top, floor)`，仍是段；无环性不变（新节点只被 `top` 指向，`p->next` 指向旧链，**没有回边**）。✅

**`push` 的 `O(1)` 是链表相对数组的**核心优势**：数组版 `push` 在容量满时要**扩容 + 复制**（见 [[15-122-11-Unbounded-Arrays]]），摊还 `O(1)` 但**单次可能 `O(n)`**；链表版**每次都是严格的 `O(1)`**。**代价是每个元素多一个指针的内存，以及缓存局部性差。**

### 5.10 去掉 `floor`：`NULL` 表示空栈

**更简的表示（p15）**：

```c0
typedef struct stack_header stack;
struct stack_header {
  list* top;
};
bool is_stack(stack* S) {
  return S != NULL && is_acyclic(S->top);
}
```

**为什么 `is_segment` 没了**：没有 `floor`，就没有「段的终点」。**改为「链表以 `NULL` 结尾」**——而讲义指出一个漂亮的等价：

> **「a linked list is acyclic if and only if it is NULL-terminated.」**

**为什么等价**：有限链表要么以 `NULL` 结尾、要么成环（没有第三种可能）。**故 `is_acyclic` 已经蕴含「`NULL` 结尾」，不需要 `is_segment`。**

**习题 10 的完整改动（p28）**：

```c0
stack* stack_new()
//@ensures is_stack(\result);
{
  stack* S = alloc(stack);
  return S;
}
bool stack_empty(stack *S)
//@requires is_stack(S);
{
  return S->top == NULL;
}
```

**`stack_new` 看起来「少了一句」**：讲义解释「recall however that the default pointer value is `NULL`. Therefore, the `top` ﬁeld of the returned stack `S` has implicitly been initialized to the empty linked list.」**`alloc` 把指针字段默认置 `NULL`**（见 [[15-122-08-Libraries]] 的默认值表），故 `S->top` 自动是空链表。**但按 5.8 的最佳实践，显式写 `S->top = NULL;` 更好读。**

**`stack_empty` 从 `top == floor` 变成 `top == NULL`**——语义完全一样（都是「空段」），只是「空」的表示从「两端重合」变成「一端为 `NULL`」。

**为什么讲义不推荐彻底去掉 `header`**：讲义用整整两页（p15–17）论证，**去掉 header 会强制改接口**：

1. **`NULL` 变成合法栈**（表示空栈），故**所有 `S != NULL` 的检查都要删掉**。
2. **更严重：`push`/`pop` 的签名必须改**。

**第 2 点的推导（p15–16）**：设 `stack_t` 就是 `list*`（指向栈顶节点）。调用 `push(S, 4)`：

- 函数内 `alloc` 出新节点 `p`，`p->next = S`，但**没有 header 可以更新**。
- 函数返回后，**调用者的 `S` 仍然指向旧节点**（C0 按值传递指针）。**栈在调用者看来完全没变！**
- **唯一出路**：让 `push` **返回**新栈顶——`stack_t push(stack_t S, elem x);`。
- **`pop` 更麻烦**：它已经要返回弹出的值，现在**还要返回新栈顶**——**一个返回值装不下两样东西**。

**这就是「header 的价值」**：header 是**一层间接（indirection）**，让「修改栈」变成「修改 header 里的字段」，而 header 的地址**不变**，故 `void push(stack_t S, elem x)` 就够了。**这与 [[15-122-09-Stacks-and-Queues]] 里「`stack_t` 必须是 `typedef ______* stack_t;`（指针）」是同一个道理：可变性需要一层间接。**

### 5.11 共享（sharing）：栈可以，队列不行

**无 header 版的「错觉」**：`stack_t S1 = push(S, 4); stack_t S2 = push(S, 5);` 之后，**三个栈 `S`、`S1`、`S2` 共享节点 `3, 2, 1`**。

```
S2 → [5] → [3] → [2] → [1] → NULL
S1 → [4] → [3] → [2] → [1] → NULL
S  →       [3] → [2] → [1] → NULL
```

**关键观察**：**第二次 `push` 操作的是 `S`，而 `S` 在第一次调用后没有改变**（因为 `push` 返回新栈，不修改旧栈）。故 `S2` 是基于 `S` 建的，不是基于 `S1`。

**共享的价值（讲义原文）**：「Sharing is an efﬁcient approach to maintaining multiple versions of a data structure as a sequence of operations is performed on them.」——**这就是「持久化数据结构（persistent data structure）」的雏形**，每次操作 `O(1)` 空间就得到一个新版本。

**共享对队列的破坏（习题 11，p28–29）**：

设队列 `Q1` 有一个元素 `1`，`front → [1] → [dummy] ← back`。

**第一步**：`enq(Q1, 2)`，返回 `Q2`。

- 把 `2` 写进 `Q1` 的哑节点（现在它有 `data = 2`）。
- 新哑节点 `d` 接在后面。
- `Q2` 的 `front` 指向 `[1]`、`back` 指向 `d`。
- **`Q1` 的 `front`/`back` 仍指向原位置**（返回新 header，不改旧 header）。

**现在 `Q1` 与 `Q2` 共享节点 `[1]` 与原哑节点（现在装 `2`）。** 讲义说「So far so good」。

**第二步**：`enq(Q1, 3)`。

- `Q1` 的 `back` 指向**那个装 `2` 的节点**（它现在是 `Q2` 的**有效数据节点**）。
- `Q1` 把 `3` **写进这个节点的 `data` 字段**——**`Q2` 的 `2` 被静默改成了 `3`！**
- 再把这个节点的 `next` 指向新哑节点——**`Q2` 的 `back` 指向的节点现在 `next` 也变了**。

**结果**：`Q2` 的 `front` 与 `back` **不再由一条有效段连接**，`is_queue(Q2)` 为假。**`Q2` 被 `Q1` 的一次普通入队摧毁了。**

**为什么栈不会出这个问题**：**栈只在 `top` 一端操作**。共享的节点总在**尾部（远离 `top` 的那一端）**，而 `push`/`pop` **只碰 `top` 附近的新节点**，**从不写共享节点的 `data`**。

**队列的 `enq` 却要写「哑节点的 `data`」**——而哑节点正是**另一端**的节点。**共享的恰恰是这一端。**

**一句话总结**：**「只在一端写」的结构可以安全共享；「两端都写」的结构不能。** 栈是前者，队列是后者。讲义原文：**「Sharing works wonderfully for stacks, but not for queues.」**

**推论**：**队列的 `enq`/`deq` 必须返回 `void`（原地修改 header）**，不能返回新 header——**因为返回新 header 会诱使客户端保留旧 header，而旧 header 随时可能被新操作破坏。** 这是**接口设计对共享安全的防御**。

### 5.12 复杂度：为什么链表上的二分是 `O(n log n)`

**`ith`（习题 3 答案，p23）**：

```c0
elem ith(list* l, int i)
//@requires i >= 0;
{
  for (list* p = l; p != NULL; p = p->next) {
    if (i == 0) return p->data;
    i--;
  }
  assert(false);   // i is greater than the length of l
  return p->data;  // possibly unsafe but unreachable
}
```

**复杂度**：从 `l` 走 `i` 步，**`O(i)`**，最坏 `O(n)`。**这就是链表的根本弱点**：**没有随机访问（random access）**。

**`lseg_binsearch`（习题 5 答案，p24）**：

```c0
int lseg_binsearch(int x, list* start, list* end)
//@requires is_segment(start, end);
//@requires is_sorted_lseg(start, end);
/*@ensures (\result == -1 && !is_in_lseg(x, start, end))
        || (0 <= \result && \result < lseg_len(start, end) &&
            ith(start, \result) == x); @*/
{
  int lo = 0;
  int hi = lseg_len(start, end);
  while (lo < hi)
  //@loop_invariant 0 <= lo && lo <= hi && hi <= lseg_len(start, end);
  {
    int mid = lo + (hi - lo)/2;
    //@assert lo <= mid && mid < hi;
    int mid_data = ith(start, mid);
    if (mid_data == x) return mid;
    if (mid_data < x) {
      lo = mid+1;
    } else { //@assert mid_data > x;
      hi = mid;
    }
  }
  //@assert !is_in_lseg(x,start,end);
  return -1;
}
```

**复杂度推导（讲义原文）**：

> **「The complexity of `lseg_binsearch` on a list segment of length `n` is `O(n log n)`: it makes `log n` accesses to the list (just like binary search on arrays) but each access now costs `O(n)`.」**

**乘法法则**：

```
访问次数 × 每次访问的代价 = log n × O(n) = O(n log n)
```

**这就是「数据结构决定算法复杂度」的教科书案例**：**二分查找的 `O(log n)` 依赖 `O(1)` 的随机访问**。链表没有这个能力，**同样的算法退化到 `O(n log n)`**——**甚至比线性查找（`O(n)`）还慢！**

**为什么仍然值得写**：**教学价值 > 实用价值**。它让你看清「`O(log n)` 不是算法的属性，而是算法 + 数据结构的联合属性」。

**对照 [[15-122-06-Binary-Search]]**：数组版的循环不变式有三条（`0<=lo<=hi<=n`、`lo==0 || A[lo-1]<x`、`hi==n || A[hi]>x`），这里**只写了一条**——**这是讲义解答的一处不足**（见第 8 节原文异常）。缺了后两条，`//@assert !is_in_lseg(x,start,end);` **证不出来**。

**一个更根本的问题**：`hi = lseg_len(start, end)` 本身就要**遍历整个段**（`O(n)`），所以**即使不算 `ith`，初始化就是 `O(n)`**。**链表上做二分，从一开始就不划算。**

### 5.13 习题 9：契约关闭时从空栈 `pop` 会怎样

**情形**：`pop` 在空栈上被调用，**契约不检查**（不带 `-d`）。

**空栈的表示**（带 `floor` 的版本）：`top == floor == dummy`，`dummy` 是哑节点。

**代码执行**：

```c0
elem x = S->top->data;   // 读哑节点的 data（无意义的值）
S->top = S->top->next;   // top 前移
```

**两个后果（讲义原文）**：

1. **返回的值无意义**：读的是哑节点的 `data`，它「is certainly a value that is not contained in the stack」。
2. **栈被破坏**：`top = top->next` 把 `top` 移到哑节点的 `next`，而 `next` **也是无意义的**。接下来两种可能：
   - **`top->next` 是 `NULL`** → **下一次 `pop` 解引用 `NULL`，程序中止（abort）**。
   - **`top->next` 不是 `NULL`** → 下一次 `pop` 返回**另一个不在栈里的值**。

**讲义结论**：「In both cases, the stack would be invalid. Were contracts enabled, this would be caught by the call to `is_segment` within `is_stack`.」

**这个习题的教学价值**：**契约不是「额外的检查」，而是「唯一的防线」**。关掉契约后，**错误不会立刻暴露，而是延迟到下一次操作**——**这正是「未定义行为」的可怕之处：它可能在离 bug 很远的地方崩溃。**

### 5.14 习题 13：交换 `enq` 最后两行为什么出错

**原版**：

```c0
void enq(queue* Q, string s)
//@requires is_queue(Q);
//@ensures is_queue(Q) && !queue_empty(Q);
{
  list* l = alloc(list);
  Q->back->data = s;
  Q->back->next = l;    // 第 3 行
  Q->back = l;          // 第 4 行
}
```

**交换后**：

```c0
  Q->back = l;          // 先移 back
  Q->back->next = l;    // 再改 next —— 但 Q->back 已经是 l 了！
```

**问题（讲义原文）**：

> **「If we swap the order of the last two lines, we ﬁrst assign `Q->back` to the new dummy node. However, by doing so, we lost access to the old dummy node, where the element we just enqueued is stored, and cannot reassign its `next` pointer to the new dummy node (without traversing the entire queue).」**

**推导**：

1. `Q->back = l` 之后，**旧哑节点的地址丢了**——`Q` 里只剩 `front` 与新 `back`。
2. 旧哑节点**装着我们刚写进去的 `s`**，但它的 `next` 仍是 `NULL`（`alloc` 的默认值）。
3. 现在写 `Q->back->next = l`，即 **`l->next = l`**——**自环！**
4. **后果**：`is_segment(Q->front, Q->back)` 从 `front` 走到 `l` 时，`l->next == l` 永远走不到 `Q->back`（因为 `Q->back == l`，其实**能走到**……）。**更严重的是**：`is_acyclic(Q->front)` **为假**（`l` 自环）。**`is_queue` 破坏。**

**修不修得回来**：理论上可以「遍历整个队列找到旧哑节点」，但那是 `O(n)`——**`enq` 的 `O(1)` 承诺就没了**。**故顺序不能换。**

**这个习题的一般教训**：**在链表上改指针时，「先接新链，再断旧链」是铁律。** 顺序反了就会**丢失句柄（handle）**。这与教科书上「删除节点时先 `p->next = q->next` 再 `free(q)`」是同一个原则的两种表现。

**注意习题 13 的 `//@ensures`**：`is_queue(Q) && !queue_empty(Q)`——**比 p10 的 `enq` 多了 `!queue_empty(Q)`**！这正是 [[15-122-09-Stacks-and-Queues]] 5.3 指出的「接口不对称」的修补版。**同一份讲义里 `enq` 的后置出现了两个版本**，见第 8 节原文异常。

## 6. 代码示例

### 6.1 官方课程代码

以下引自讲义 PDF `10-linkedlist.pdf`，语言为 **C0**（不是标准 C/C++）。`//@` 注解、`alloc`、`\result`、`elem` 都是 C0 特有语法；`->` 与 `NULL` 的用法虽与 C 相同，但**本讲全部代码是 C0**。

**（1）链表节点的递归定义，第 2 页：**

```c0
struct list_node {
  elem data;
  struct list_node* next;
};
typedef struct list_node list;
```

**（2）被拒绝的无限递归类型，第 2 页：**

```c0
struct infinite {
  int x;
  struct infinite next;
}
```

**（3）`is_segment` 的三种实现，第 4 页：**

```c0
bool is_segment(list* start, list* end) {
  if (start == NULL) return false;
  if (start == end) return true;
  return is_segment(start->next, end);
}

bool is_segment(list* start, list* end) {
  list* l = start;
  while (l != NULL) {
    if (l == end) return true;
    l = l->next;
  }
  return false;
}

bool is_segment(list* start, list* end) {
  for (list* p = start; p != NULL; p = p->next) {
    if (p == end) return true;
  }
  return false;
}
```

**（4）在 `coin` 里造一个环形链表，第 5 页：**

```c0
--> list* start = alloc(list);
--> start->data = 3;
--> start->next = alloc(list);
--> start->next->data = 7;
--> start->next->next = alloc(list);
--> start->next->next->data = 3;
--> start->next->next->next = alloc(list);
--> start->next->next->next->data = 12;
--> start->next->next->next->next = start->next;
--> list* end = alloc(list);
--> end->data = 18;
--> end->next = NULL;
--> is_segment(start, end);
```

**（5）龟兔环检测 `is_acyclic`，第 7 页：**

```c0
bool is_acyclic(list* start) {
  if (start == NULL) return true;
  list* h = start->next;   // hare
  list* t = start;         // tortoise
  while (h != t) {
    if (h == NULL || h->next == NULL) return true;
    h = h->next->next;
    //@assert t != NULL;    // faster hare hits NULL quicker
    t = t->next;
  }
  //@assert h == t;
  return false;
}
```

**（6）队列的 header 与表示不变式，第 8–9 页：**

```c0
typedef struct queue_header queue;
struct queue_header {
  list* front;
  list* back;
};
typedef queue* queue_t;

bool is_queue(queue* Q) {
  return Q != NULL
      && is_acyclic(Q->front)
      && is_segment(Q->front, Q->back);
}
```

**（7）`queue_empty`，第 9 页：**

```c0
bool queue_empty(queue* Q)
//@requires is_queue(Q);
{
  return Q->front == Q->back;
}
```

**（8）`queue_new`，第 9 页：**

```c0
queue* queue_new()
//@ensures is_queue(\result);
//@ensures queue_empty(\result);
{
  queue* Q = alloc(queue);        // Create header
  list* dummy = alloc(list);      // Create dummy node
  Q->front = dummy;               // Point front
  Q->back = dummy;                // and back to dummy node
  return Q;
}
```

**（9）`enq`，第 10 页：**

```c0
void enq(queue* Q, elem x)
//@requires is_queue(Q);
//@ensures is_queue(Q);
{
  list* new_dummy = alloc(list);   // Create a new dummy node
  Q->back->data = x;               // Store x in old dummy node
  Q->back->next = new_dummy;
  Q->back = new_dummy;
}
```

**（10）`deq`，第 11 页：**

```c0
elem deq(queue* Q)
//@requires is_queue(Q);
//@requires !queue_empty(Q);
//@ensures is_queue(Q);
{
  elem x = Q->front->data;
  Q->front = Q->front->next;
  return x;
}
```

**（11）栈的 header 与 `is_stack`（带 `floor`），第 13 页：**

```c0
typedef struct stack_header stack;
struct stack_header {
  list* top;
  list* floor;
};
bool is_stack(stack* S) {
  return S != NULL
      && is_acyclic(S->top)
      && is_segment(S->top, S->floor);
}
```

**（12）`pop`，第 13 页：**

```c0
elem pop(stack* S)
//@requires is_stack(S);
//@requires !stack_empty(S);
//@ensures is_stack(S);
{
  elem x = S->top->data;
  S->top = S->top->next;
  return x;
}
```

**（13）`push`，第 14 页：**

```c0
void push(stack* S, elem x)
//@requires is_stack(S);
//@ensures is_stack(S);
{
  list* p = alloc(list);   // Allocate a new top node
  p->data = x;
  p->next = S->top;
  S->top = p;
}
```

**（14）去掉 `floor` 的简化栈，第 15 页：**

```c0
typedef struct stack_header stack;
struct stack_header {
  list* top;
};
bool is_stack(stack* S) {
  return S != NULL && is_acyclic(S->top);
}
```

**（15）习题 6 答案：带 `is_segment(t,h)` 不变式的 `is_acyclic`，第 25 页：**

```c0
bool is_acyclic(list* start) {
  if (start == NULL) return true;
  if (start->next == NULL) return true;
  list* h = start->next;   // hare
  list* t = start;         // tortoise
  while (h != t)
  //@loop_invariant is_segment(t, h);
  {
    if (h->next == NULL || h->next->next == NULL) return true;
    h = h->next->next;
    t = t->next;
  }
  //@assert h == t;
  return false;
}
```

**（16）习题 1 答案 `is_sum`，第 22 页：**

```c0
bool is_sum(list* start, list* end, int sum)
//@requires is_segment(start, end);
{
  list* l = start;
  int n = 0;
  while (l != end) {
    n += l->data;
    l = l->next;
  }
  return n == sum;
}
```

**（17）习题 2 答案 `lseg_len`，第 22 页：**

```c0
int lseg_len(list* start, list* end)
//@requires is_segment(start, end);
{
  int n = 0;
  for (list* p = start; p != end; p = p->next)
  //@loop_invariant p != NULL;
  {
    n++;
  }
  return n;
}
```

**（18）习题 3 答案 `ith`，第 23 页：**

```c0
elem ith(list* l, int i)
//@requires i >= 0;
{
  for (list* p = l; p != NULL; p = p->next) {
    if (i == 0) return p->data;
    i--;
  }
  assert(false);   // i is greater than the length of l
  return p->data;  // possibly unsafe but unreachable
}
```

**（19）习题 4 答案 `is_in_lseg` / `is_sorted_lseg`，第 23 页：**

```c0
bool is_in_lseg(int x, list* start, list* end)
//@requires is_segment(start, end);
{
  for (list* p = start; p != end; p = p->next)
  //@loop_invariant p != NULL;
  {
    if (p->data == x) return true;
  }
  return false;
}

bool is_sorted_lseg(list* start, list* end)
//@requires is_segment(start, end);
{
  if (start == end) return true;   // empty list segment
  int x = start->data;
  for (list* p = start->next; p != end; p = p->next)
  //@loop_invariant p != NULL;
  {
    if (x > p->data) return false;
    x = p->data;
  }
  return true;
}
```

**（20）习题 5 答案 `lseg_binsearch`，第 24 页：**

```c0
int lseg_binsearch(int x, list* start, list* end)
//@requires is_segment(start, end);
//@requires is_sorted_lseg(start, end);
/*@ensures (\result == -1 && !is_in_lseg(x, start, end))
        || (0 <= \result && \result < lseg_len(start, end) &&
            ith(start, \result) == x); @*/
{
  int lo = 0;
  int hi = lseg_len(start, end);
  while (lo < hi)
  //@loop_invariant 0 <= lo && lo <= hi && hi <= lseg_len(start, end);
  {
    int mid = lo + (hi - lo)/2;
    //@assert lo <= mid && mid < hi;
    int mid_data = ith(start, mid);
    if (mid_data == x) return mid;
    if (mid_data < x) {
      lo = mid+1;
    } else { //@assert mid_data > x;
      hi = mid;
    }
  }
  //@assert !is_in_lseg(x,start,end);
  return -1;
}
```

**（21）习题 8 答案 `is_definite_segment`，第 27 页：**

```c0
bool is_definite_segment(list* start, list* end) {
  if (start == NULL || end == NULL) return false;   // MODIFIED
  if (start == end) return true;                    // ADDED
  list* h = start->next;   // hare
  list* t = start;         // tortoise
  while (h != t) {
    if (h == NULL) return false;                    // MODIFIED
    if (h == end || h->next == end) return true;    // ADDED
    if (h->next == NULL) return false;              // ADDED
    h = h->next->next;
    //@assert t != NULL;   // hare is faster and hits end quicker
    t = t->next;
  }
  //@assert h == t;
  return false;
}
```

**（22）习题 12 答案 `is_reachable_in` 与 `is_segmentC`，第 30 页：**

```c0
bool is_reachable_in(list *start, list* end, int numsteps)
//@requires numsteps >= 0;
{
  for (list *l = start; l != end; l = l->next) {
    if (l == NULL) return false;
    numsteps--;
  }
  if (numsteps == 0) return true;
  return false;
}

bool is_segmentC(list* start, list* end) {
  int numsteps = 0;
  for (list* p = start; p != NULL; p = p->next)
  //@loop_invariant is_reachable_in(start, p, numsteps);
  {
    if (p == end) return true;
    numsteps++;
  }
  return false;
}
```

**（23）习题 13 的 `enq`（注意 `//@ensures` 多了 `!queue_empty(Q)`），第 21 页：**

```c0
void enq(queue* Q, string s)
//@requires is_queue(Q);
//@ensures is_queue(Q) && !queue_empty(Q);
{
  list* l = alloc(list);
  Q->back->data = s;
  Q->back->next = l;
  Q->back = l;
}
```

**官方代码包**：`90-原始PDF/15-122/code/10-linkedlist.tgz`（原始 URL：`https://cs.cmu.edu/~15122/handouts/code/10-linkedlist.tgz`）。

### 6.2 Agent 自行编写的教学示例

> **非官方，仅用于说明概念。** 以下由本笔记自行编写，不是 CMU 官方代码，语言为 **C0**。

**示例 A：逐帧追踪 `enq` 的四个步骤。**

队列 `Q` 里有元素 `1, 2`。初始：`front → [1] → [2] → [X] ← back`（`X` 是哑节点）。

`enq(Q, 3)`：

| 步 | 语句 | 内存变化 |
|---|---|---|
| 0 | 入口 | `front → [1] → [2] → [X]`，`back → [X]` |
| 1 | `new_dummy = alloc(list)` | 新节点 `[Y]`（`data` 默认、`next = NULL`） |
| 2 | `Q->back->data = 3` | `[X].data = 3`——**`X` 转正为数据节点** |
| 3 | `Q->back->next = new_dummy` | `[X].next = [Y]` |
| 4 | `Q->back = new_dummy` | `back → [Y]` |

**结果**：`front → [1] → [2] → [3] → [Y] ← back`。**队列现在有 3 个元素，`Y` 是新的哑节点。**

**注意第 2 步的「转正」是本讲的精髓**：`X` 在 `enq` 之前**不是**队列元素（它是哨兵），`enq` 之后**是**队列元素。**同一个节点，身份变了。** 这就是为什么 `back` 要指向「末尾之后一格」——**那一格是「下一个要转正的节点」。**

**示例 B：用龟兔算法追踪一个具体的环。**

链表：`1 → 2 → 3 → 4 → 5 → 3`（节点 `5` 的 `next` 指回节点 `3`）。环是 `3 → 4 → 5 → 3`，环长 `L = 3`。

| 轮 | `t` | `h` | `h == t`？ | 说明 |
|---|---|---|---|---|
| 初始 | `1` | `2` | 否 | `h = start->next`，`t = start` |
| 1 | `2` | `4` | 否 | `h` 走 2 步（`2→3→4`），`t` 走 1 步 |
| 2 | `3` | `3` | **是** | `h` 走 2 步（`4→5→3`），`t` 走 1 步（`2→3`） |

**2 轮相遇**，返回 `false`（有环）。✅

**用 5.4 的距离公式验证**：进入环时 `t = 1`（不在环上），`h = 2`。第 1 轮后 `t = 2`、`h = 4`——此时 `t` 刚进环（`2` 不在环上，`t` 还在环外）。第 2 轮后 `t = 3`（环上）、`h = 3`，相遇。**实际步数取决于「进入环之前走了几步」+「环内追及步数」，上界是 `n + L`。**

**示例 C：为什么 `t != NULL` 单独当不变式的保持性会失败——一个具体反例。**

链表 `a → b → NULL`（无环，2 个节点）。`is_acyclic(a)`：

- 入口：`start = a`，`a->next = b != NULL`，故不触发前两个 `return true`。
- `h = b`、`t = a`。`h != t`，进入循环。
- 检查 `h->next == NULL || h->next->next == NULL`：`b->next == NULL` → **真**，`return true`。✅

**这个例子没有走到 `t = t->next`**，所以看不出问题。换一个**更长的链表** `a → b → c → NULL`：

- `h = b`、`t = a`。`h != t`，进入循环。
- `h->next = c != NULL`，`h->next->next = NULL` → **真**，`return true`。✅

**仍然没走到。** 实际上**无环链表总是在兔子撞 `NULL` 前返回**，所以 `t = t->next` 只在**有环**时执行。

**在有环时**：`t` 在环上走，`t->next` 永远不是 `NULL`（环上每个节点都有后继）。**故保持性「碰巧」成立。** 但**验证器不能靠「碰巧」**——它需要**从不变式推出**。`t != NULL` **推不出** `t->next != NULL`（`t` 可能是**无环链表的最后一个节点**，只是这条路径运行时不会发生）。

**这就是「运行时正确 ≠ 可验证」的经典区别**：代码在**所有可达状态**下都对，但**验证器不认**，因为它的推理不依赖可达性，只依赖不变式。**补 `is_segment(t, h)` 就是把「可达性信息」编码进不变式。**

**示例 D：构造一个破坏队列的共享序列（习题 11 的完整版）。**

**前提**：假设 `enq`/`deq` 返回**新 header** 而不是原地修改（这是讲义设想的「危险设计」）。

**初始**：`Q1` 有元素 `1`。`Q1 = {front: n1, back: d1}`，`n1 = [data:1, next:d1]`，`d1 = [data:?, next:NULL]`。

**第 1 步**：`Q2 = enq(Q1, 2)`。

- 写 `d1.data = 2`（`d1` 转正）。
- `d2 = alloc(list)`，`d1.next = d2`。
- `Q2 = {front: n1, back: d2}`。
- **`Q1` 仍是 `{front: n1, back: d1}`**。

**此刻**：`Q1` 认为队列是 `[n1]`（`n1` 到 `d1` 的段，含 `1`）；`Q2` 认为队列是 `[n1, d1]`（含 `1, 2`）。**两者共享 `n1` 与 `d1`，且 `d1` 在 `Q1` 眼里是哑节点、在 `Q2` 眼里是数据节点。** **已经不一致了**，但两个 `is_queue` 都还成立。

**第 2 步**：`Q3 = enq(Q1, 3)`。

- 写 `Q1.back->data = 3`，即 **`d1.data = 3`**——**`Q2` 的元素 `2` 变成了 `3`！**
- `d3 = alloc(list)`，`d1.next = d3`。
- `Q3 = {front: n1, back: d3}`。

**此刻 `Q2 = {front: n1, back: d2}`**，但 `d1.next` 已经被改成 `d3`，**`d2` 不再从 `n1` 可达**。故 `is_segment(n1, d2)` **为假**，`is_queue(Q2)` **为假**。**`Q2` 被摧毁。**

**三步总结**：

| 步 | 操作 | `Q2` 的状态 |
|---|---|---|
| 0 | 初始 | `Q2` 不存在 |
| 1 | `Q2 = enq(Q1, 2)` | 合法（但已与 `Q1` 不一致） |
| 2 | `Q3 = enq(Q1, 3)` | **非法**（`2` 被改成 `3`，`d2` 失联） |

**这个追踪证明了 5.11 的结论**：**队列的 `enq` 会写「另一端」的节点，而共享的正是那一端。** 栈的 `push` 只写**新节点**，从不碰共享部分，所以安全。

**示例 E：`is_definite_segment` 修的是什么 bug（习题 8）。**

**问题链表**：`start → a → b → c → b`（`c` 指回 `b`，**环在 `end` 之前还是之后？**）

讲义的情形是「**a cycle past its end pointer**」——即 `end` 在环**之前**：

```
start → a → end → b → c → b   （b、c 成环）
```

**这里 `[start, end)` 是合法段**（`start → a → end`，2 个节点）。

**`is_acyclic(start)` 的判定**：从 `start` 出发，龟兔会**走进环里**（因为 `is_acyclic` 不知道 `end` 在哪），**最终相遇，返回 `false`（有环）**。

**`is_queue` 的组合判定**：`is_acyclic(start)` 为 `false` → **`is_queue` 为 `false`**——**尽管 `[start, end)` 确实是合法段！**

**这就是漏判**：`is_acyclic` 检查的是**整条链**，而 `is_segment` 只关心 **`start` 到 `end` 那一段**。**段之外有没有环，与段是否合法无关。**

**`is_definite_segment` 的修法**：把 `end` 传给环检测，**一旦兔子到达或越过 `end` 就返回 `true`**：

```c0
if (h == end || h->next == end) return true;   // 兔子到 end 了 → 段合法
if (h->next == NULL) return false;             // 兔子撞 NULL 但没到 end → 段不合法
```

**逐项解释**：

| 行 | 作用 |
|---|---|
| `if (start == NULL \|\| end == NULL) return false;` | 段的定义要求两端非 `NULL`（**MODIFIED**：原来是 `start == NULL` 返回 `true`） |
| `if (start == end) return true;` | **空段**是合法的（**ADDED**） |
| `if (h == NULL) return false;` | 兔子撞 `NULL` 但没到 `end` → 不连通（**MODIFIED**：原来返回 `true`） |
| `if (h == end \|\| h->next == end) return true;` | **兔子到达或越过 `end`** → 段存在（**ADDED**） |
| `if (h->next == NULL) return false;` | 兔子下一步会撞 `NULL` 且不是 `end` → 不连通（**ADDED**） |

**注意 `h->next == end` 这一项的必需性**：兔子每轮跳 2 步，**可能「跳过」`end`**。若只查 `h == end`，兔子从 `end` 的前一个节点直接跳到 `end` 的后一个节点，就会**错过** `end`。**故必须同时查 `h->next == end`。**

**讲义结论**：「This enhanced version of `is_acyclic` subsumes our original `is_segment`: we do not need it anymore.」——**`is_definite_segment` 一个函数同时完成「无环」与「连通」两件事**，且**不会因为段外的环而误判**。

**为什么它「immune from this issue」**：因为它**只沿从 `start` 出发的路径检查到 `end` 为止**，**从不走进 `end` 之后的区域**。**段外的环永远不会被访问。**

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键区别 | 记忆点 |
|---|---|---|---|
| 数组 | 链表 | 前者 `O(1)` 随机访问 / 插入删除 `O(n)`；后者 `O(n)` 访问 / `O(1)` 插入删除 | 编号座位 vs 手拉手 |
| 隐式下标 | 显式地址 | 数组的位置**不占内存**；链表的 `next` **占一个字** | 讲义开篇的洞察 |
| `struct infinite` | `struct list_node` | 前者**直接嵌入**（大小无限，被拒）；后者**经指针**（大小有限） | 递归必须在指针/数组之下 |
| 具体类型 | 抽象类型 | 链表是前者（客户端知道结构）；栈/队列是后者（接口隐藏） | 「一次定型」vs「可换实现」 |
| 指针相等 | 内容相等 | `a1 != a3` 但 `a1->data == a3->data` | **指针是身份** |
| 段 `[start, end)` | 闭区间 `[start, end]` | 前者 `start == end` 是**空段**；后者不是 | 含头不含尾 |
| `is_segment` 递归版 | `is_segment` 循环版 | **语义等价**，但递归版可能栈溢出 | 都**不终止于有环链表** |
| `is_acyclic` | `is_segment` | 前者查**整条链**有没有环；后者查 `start` 到 `end` **连不连通** | 前者是后者的**终止性前提** |
| 龟兔相遇 | 兔子撞 `NULL` | 前者 → **有环**；后者 → **无环** | 环跑道 vs 直跑道 |
| `front` / `back`（队列） | `top` / `floor`（栈） | 前者两端都用；后者只用 `top` | 队列两端操作，栈一端 |
| 哑节点（dummy） | 数据节点 | 前者的 `data`/`next` **无效**；`enq` 时**转正** | 哨兵消灭边界特判 |
| header | 哑节点 | header 是**栈上的 struct**（存指针）；哑节点是**堆上的 list** | 一层间接 → 可变 |
| `deq` 不释放节点 | 内存泄漏 | **不可达 → 垃圾回收**；C0 有 GC，C 没有 | 「若遵守接口」是前提 |
| `push` 返回 `void` | 无 header 的 `push` 返回新栈 | 前者靠 header 的**固定地址**；后者必须返回 | header = 间接层 |
| 共享（栈） | 共享（队列） | 栈只写**新节点**；队列写**另一端**的哑节点 | 「只在一端写」才安全 |
| `O(log n)`（数组二分） | `O(n log n)`（链表二分） | 后者每次访问是 `O(n)` | 算法复杂度 = 算法 + 结构 |
| `is_acyclic` + `is_segment` | `is_definite_segment` | 前者**误判「段外有环」**；后者免疫 | 只检查到 `end` 为止 |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-122/lectures/10-linkedlist.pdf`
- **讲义标题**：PDF 内页标题为 **"Lecture 10: Linked Lists"**，作者 Frank Pfenning、Rob Simmons、André Platzer、Iliano Cervesato。
- **总页数**：30 页
- **本节重点页码**（PDF 页码，即提取文本中 `=== [page N] ===` 的 N）：
  - 第 1 页：开篇；用链表**实现上一讲的栈与队列接口**，从而支持**任意长度**的工作列表；三条学习目标（计算思维：把数组的隐式下标显式化为地址 + 权衡；数据结构：链表；编程：指针代码易错 → 不变式的力量）；复习幻灯片与代码包链接
  - 第 1–2 页：链表 = 数据 + `next` 指针；**插入删除容易**（数组是固定大小）；**中间访问 `O(n)`**；`struct list_node` 定义 + `typedef`；**递归类型**；`NULL` 表示结尾；两种书写顺序等价
  - 第 2 页：`struct infinite` 被拒；**规则：递归必须在指针或数组之下**
  - 第 3 页：**具体类型 vs 抽象类型**（「Concrete types are cast into concrete once and for all」）；**段（segment）** 定义，含头不含尾；`[a1,a4)` = `3,7,3`、`[a2,a3)` = `7`、`[a1,a1)` = 空；**`a1 != a3`**（不同地址）；配图未提取
  - 第 4 页：`is_segment` 的**递归 / while / for** 三种实现；**共同缺陷：有环时不终止**
  - 第 5 页：在 `coin` 里造环形链表的完整命令序列；**规格函数必须安全**（不除零、不越界、不解引用 `NULL`）；尽量返回 `true`/`false` 而非不终止
  - 第 6 页：环检测的动机（先查环再调 `is_segment`）；龟兔算法介绍；配图未提取
  - 第 7 页：`is_acyclic` 完整代码；`||` **短路求值**的必需性；Floyd 1967
  - 第 8 页：队列的链表表示图；`front`/`back` 两个指针的理由（两端 `O(1)`）；**哑节点**（`back` 指向末尾之后一格）；`struct queue_header`；`typedef queue* queue_t`
  - 第 8–9 页：**表示不变式**的必要性；`is_queue`（三条：`Q != NULL`、`is_acyclic(Q->front)`、`is_segment(Q->front, Q->back)`）；「with one element already allocated even if the queue is empty」
  - 第 9 页：`queue_empty`（`front == back`）；**「函数内部可以暂时违反不变式」**；`queue_new` 完整代码；**「总是初始化内存是好习惯」**
  - 第 9–10 页：`enq` 的 before/after 图（**配图未提取**）；`enq` 完整代码（四步）
  - 第 10–11 页：`deq` 的图（**配图未提取**）；`deq` 完整代码（两行）
  - 第 12 页：**`deq` 的解引用安全性逐条论证**；**`deq` 不释放节点 → 不可达 → 垃圾回收**（「If the interface is respected」）
  - 第 12–13 页：栈复用队列的基本结构；`top` + `floor`；`floor` **仅用于结构对称**；`struct stack_header`；`is_stack`；配图未提取
  - 第 13 页：`pop` 完整代码（与 `deq` 同构）
  - 第 13–14 页：`push` 的 before/after 图（**配图未提取**）；`push` 完整代码（头插法）；`typedef stack* stack_t`
  - 第 14–15 页：**简化表示**（去掉 `floor`，`NULL` 表示空栈）；`is_stack` 变成 `S != NULL && is_acyclic(S->top)`
  - 第 15 页：**为什么不去掉 header**：两条理由（`NULL` 变合法栈 → 删所有 `NULL` 检查；`push`/`pop` 签名必须改）
  - 第 15–16 页：`push(S,4)` 的图（**配图未提取**）；**调用者的 `S` 看不到更新** → `push` 必须返回新栈；`pop` 要返回「值 + 新栈」
  - 第 16 页：**共享（sharing）**；`S1 = push(S,4)`、`S2 = push(S,5)` 共享节点 `3,2,1`；「Sharing is an efﬁcient approach to maintaining multiple versions」
  - 第 16–17 页：**共享的陷阱**：队列若返回新 header，精心设计的 `enq`/`deq` 序列会破坏表示不变式
  - 第 18–21 页：**习题 1–14**（`is_sum`、`lseg_len`、`ith`、`is_in_lseg`/`is_sorted_lseg`、`lseg_binsearch`、龟兔不变式、`bad_is_acyclic`、`is_definite_segment`、空栈 `pop`、无 `floor` 栈、共享破坏队列、`is_reachable_in`、`enq` 行序、双端队列）
  - 第 22–23 页：习题 1–4 答案（`is_sum`、`lseg_len`、`ith`、`is_in_lseg`/`is_sorted_lseg`）；`ith` 是 `O(n)`
  - 第 24 页：习题 5 答案 `lseg_binsearch`；**`O(n log n)`**（`log n` 次访问 × 每次 `O(n)`）
  - 第 24–26 页：习题 6 答案（`t != NULL` 保持性失败；补 `is_segment(t,h)`；改写版 `is_acyclic`；`is_segment` 与 `is_acyclic` 不能互递归；**「This is not a point-to proof」**；退出时需 `is_segment(t->next,h)`）
  - 第 26 页：习题 7 答案（**自环 `a->next = a`** 使内层循环守卫立刻为假、外层死循环）；习题 8 答案（**环在 `end` 之后** → `is_acyclic` 误拒合法段）
  - 第 27 页：`is_definite_segment` 完整代码（三处 MODIFIED/ADDED 标注）；「subsumes our original `is_segment`」；习题 9 答案（空栈 `pop` 的两个后果）
  - 第 28 页：习题 10 答案（无 `floor` 栈的 `is_stack`/`stack_new`/`stack_empty`；**「acyclic iff NULL-terminated」**；`stack_new` 靠默认 `NULL`）；习题 11 答案开始（1 元素队列 `Q1`）
  - 第 29 页：习题 11 答案续（`enq` 返回新 header → 破坏 `Q2`；**「Sharing works wonderfully for stacks, but not for queues」**）；配图未提取
  - 第 30 页：习题 12 答案（`is_reachable_in` + `is_segmentC`）；习题 13 答案（交换最后两行 → 丢失旧哑节点的句柄）
- **原始网页链接**：`https://www.cs.cmu.edu/~15122-archive/f26/handouts/lectures/10-linkedlist.pdf`
- **配套代码包**：`https://cs.cmu.edu/~15122/handouts/code/10-linkedlist.tgz`（本库已下载为 `90-原始PDF/15-122/code/10-linkedlist.tgz`，**未解压**）
- **复习幻灯片**：`https://cs.cmu.edu/~15122/handouts/slides/review/10-linkedlist.pdf`（本库**未**收录其提取文本，页码待人工核对）

> **原文异常**：
> 1. **第 12 页 `is_queue` 的定义漏了星号**：正文写 `bool is_queue(queue Q) {`，而第 9 页与所有调用处都是 `is_queue(queue* Q)`。**`queue Q` 会试图按值传递一个 `struct`，在 C0 里是非法的**（见 [[15-122-08-Libraries]] 的「cannot pass or store structs in variables directly」）。
> 2. **第 10 页与第 21 页的 `enq` 后置条件不一致**：第 10 页写 `//@ensures is_queue(Q);`，第 21 页（习题 13）写 `//@ensures is_queue(Q) && !queue_empty(Q);`。**后者才是完整的**——`enq` 之后队列必然非空。第 10 页的版本**弱了一条**，与 [[15-122-09-Stacks-and-Queues]] 5.3 指出的「`enq` 缺后置」是同一个疏漏的两个表现。
> 3. **第 23 页 `ith` 的答案有作用域错误**：`for (list* p = l; ...)` 里的 `p` 在循环结束后**已超出作用域**，而 `return p->data;` 在循环之后引用 `p`。**这在 C0（以及标准 C）里是编译错误。** 该行注释说「possibly unsafe but unreachable」，意图是「`assert(false)` 之后不会执行到」，但**作用域问题与可达性无关**——编译器仍会报错。应把 `p` 声明在循环外。
> 4. **第 24 页 `lseg_binsearch` 的循环不变式不完整**：只写了 `0 <= lo && lo <= hi && hi <= lseg_len(start, end)`，**缺了 [[15-122-06-Binary-Search]] 里那两条关键不变式**（「`x` 不在 `[0,lo)`」与「`x` 不在 `[hi,n)`」）。**没有它们，退出后的 `//@assert !is_in_lseg(x,start,end);` 证不出来。** 这是答案的一处实质缺失，不是笔误。
> 5. **第 25 页改写版 `is_acyclic` 的三处改动未加说明**：新增 `if (start->next == NULL) return true;`、把 `h == NULL || h->next == NULL` 改成 `h->next == NULL || h->next->next == NULL`、加 `is_segment(t,h)`。**前两处是配套必需的**（否则 `h == NULL` 时 `h->next` 解引用空指针），但讲义只说「This is the loop invariant we are missing」，**没有解释为什么循环内的 `NULL` 检查也必须改**。读者照抄 p7 版只加不变式会**编译/运行出错**。
> 6. **第 5 页的环形链表命令序列有一处值得核对**：`start->next->next->next->next = start->next;` 让第 4 个节点（`data = 12`）指回第 2 个节点（`data = 7`），**环是 `7 → 3 → 12 → 7`**（环长 3），而 `start`（`data = 3`）**在环上**。**配图未提取**，无法核对图与代码是否一致。
> 7. **第 3、6、8、10、11、13、14、15、16、29 页共十余处配图未被文本提取**：段示意图、龟兔追踪图、队列/栈的结构图、`enq`/`deq`/`push` 的 before-after 图、`push(S,4)` 的调用者视角图、共享内存布局图、习题 11 的三张队列图。**本笔记的图示均为依据文字描述重绘，具体图形待人工核对原 PDF。**
> 8. **第 28 页 `bool stack_empty(stack *S)` 的星号位置与全文不一致**：全文用 `stack* S`，此处用 `stack *S`。**纯风格问题，不影响语义。**
> 9. **第 18 页习题 4 与第 23 页答案的类型不一致**：习题说「speciﬁcation functions on list segments with **integer** elements」，答案里 `is_sorted_lseg` 用 `int x = start->data;`——**默认了 `elem == int`**。而第 1 页强调「none of the code actually depends on what type is chosen」。**这是习题范围内的合理简化，但与全文的 `elem` 抽象有张力。**
> 10. **第 24 页习题 5 答案的 `hi` 初始化是 `O(n)`**：`int hi = lseg_len(start, end);` 需要**遍历整个段**。讲义在复杂度分析里只说「`log n` 次访问 × 每次 `O(n)`」，**没有把这次 `O(n)` 初始化算进去**——虽然结论 `O(n log n)` 不变（`O(n) + O(n log n) = O(n log n)`），但**论证跳过了一步**。

## 9. 对应视频

未找到官方公开录像。建议的动手顺序：(1) 在 `coin` 里照第 5 页的命令造一个环形链表，然后调 `is_segment`，**观察它卡死**——这会让你永久记住「规格函数必须终止」；(2) 手写 `is_acyclic`，用 6.2 示例 B 的链表（`1→2→3→4→5→3`）打印每轮的 `t`/`h`，验证 2 轮相遇；(3) 用 `cc0 -d` 编译 `is_acyclic`，先只写 `//@loop_invariant t != NULL;`，**看验证器在哪一行报保持性失败**，再补 `is_segment(t, h)`，看它通过；(4) 实现队列的三个函数，每步打印 `front`/`back` 的地址，对照 6.2 示例 A 的追踪表；(5) 故意把 `enq` 最后两行交换，看 `is_queue` 在哪一步变成假（习题 13）；(6) 用 `lseg_binsearch` 在一个 1000 元素的链表上查找，与 `is_in_lseg` 线性查找对比耗时——**你会发现链表上的二分并不比线性快**，这比任何公式都有说服力。

## 10. 本节复习

1. 链表 = 数据 + `next` 指针；插入删除 `O(1)`（若已定位），中间访问 `O(n)`。
2. 递归类型必须**在指针或数组之下**递归，否则大小无限（`struct infinite` 被拒）。
3. 链表是**具体类型**（客户端知道结构），栈/队列是**抽象类型**（接口隐藏实现）。
4. 段 `[start, end)` **含头不含尾**；`start == end` 是**空段**；长度 = 步数。
5. **指针相等 ≠ 内容相等**：`a1 != a3` 即使 `a1->data == a3->data`。
6. `is_segment` 三种写法语义等价，**遇到环都不终止**。
7. 规格函数**必须安全**（不崩溃）；终止性是「尽量」。
8. **龟兔算法**：慢指针 1 步、快指针 2 步；相遇 → 有环；兔子撞 `NULL` → 无环。
9. 无环时兔子先撞 `NULL`，靠 `||` 短路保护 `h->next` 的解引用。
10. 有环时距离每轮减 1（模 `L`），**至多 `L` 轮相遇**。
11. `t != NULL` 单独当不变式**保持性失败**（推不出 `t->next != NULL`）；必须补 `is_segment(t, h)`。
12. `is_segment(t, h)` 蕴含 `t != NULL`（因为 `is_segment` 的 base case 要求两端非 `NULL`）。
13. 退出时 `h == t` **不足以**证有环（空段也满足）；必须补 `is_segment(t->next, h)`。
14. 补 `is_segment(t->next,h)` 要求 `t->next` 存在 → **必须在入口挡掉 `start->next == NULL`**（与循环内 `NULL` 检查的改动配套）。
15. `is_segment` 与 `is_acyclic` **不能互递归**（前置互相依赖）；讲义说「这不是指向式证明」。
16. 队列 = header（`front`/`back`）+ **哑节点**；`back` 指向**末尾之后一格**。
17. 哑节点的作用：**消灭空队列的边界特判**（`enq` 往哑节点写数据，把它「转正」）。
18. `is_queue` = `Q != NULL` && `is_acyclic(front)` && `is_segment(front, back)`；**顺序不能反**。
19. `queue_empty` 就是 `front == back`（空段）。
20. `enq` 四步：`alloc` 新哑节点 → 写旧哑节点 `data` → 旧哑节点 `next` 接新 → `back` 前移。**最后两行顺序不能换。**
21. `deq` 两行：存 `front->data` → `front` 前移。**不释放节点**——不可达 → GC 回收。
22. 栈 = header（`top`/`floor`）+ 同样的哑节点；`pop` 与 `deq` 同构，`push` 是**头插法**。
23. `floor` 是**结构性冗余**（只为与队列同构）；去掉后 `is_stack` = `S != NULL && is_acyclic(S->top)`（**acyclic iff NULL-terminated**）。
24. **不能去掉 header**：`NULL` 会变成合法栈，且 `push`/`pop` 必须改签名（返回新栈）。
25. **共享**：栈安全（只写新节点），队列危险（`enq` 写另一端的哑节点）。
26. `ith` 是 `O(n)` → 链表上二分是 **`O(n log n)`**（`log n` 次 × 每次 `O(n)`）。
27. `is_acyclic + is_segment` **误判「段外有环」**；`is_definite_segment` 只检查到 `end` 为止，免疫。
28. 契约关闭时从空栈 `pop`：返回无意义值 + 破坏 `top`，**错误延迟到下一次操作才暴露**。

## 11. 自我检查

**题 1.** 链表 `a1 → a2 → a3 → a4 → NULL`，数据依次 `3, 7, 3, 5`。写出 `[a1, a4)`、`[a2, a3)`、`[a3, a3)` 的数据序列与长度，并说明为什么 `a1 != a3` 对 `is_segment` 是必需的。

**题 2.** 对链表 `1 → 2 → 3 → 4 → 5 → 6 → 3`（节点 `6` 指回 `3`），逐轮列出龟兔算法的 `t` 与 `h`，说明第几轮相遇。环长是多少？上界 `L` 轮成立吗？

**题 3.** 为什么 `//@loop_invariant t != NULL;` 的**保持性**会失败？补上 `is_segment(t, h)` 之后，为什么 `t != NULL` 就自动成立了？为什么改写版还必须新增 `if (start->next == NULL) return true;`？

**题 4.** 追踪 `enq` 的四步：队列 `Q` 有元素 `1, 2`，`front → [1] → [2] → [X] ← back`。逐步写出 `enq(Q, 3)` 后每个字段的值，并说明为什么最后两行**不能交换**。

**题 5.** 为什么 `lseg_binsearch` 是 `O(n log n)` 而不是 `O(log n)`？为什么共享对栈安全、对队列危险？各用一句话回答。

<details>
<summary>参考答案</summary>

**答 1.**

| 段 | 节点 | 数据序列 | 长度 |
|---|---|---|---|
| `[a1, a4)` | `a1, a2, a3` | `3, 7, 3` | 3 |
| `[a2, a3)` | `a2` | `7` | 1 |
| `[a3, a3)` | 无 | 空 | 0 |

**为什么 `a1 != a3` 是必需的**：`a1` 与 `a3` 的 `data` **都是 `3`**。若 `is_segment` 用 `data` 比较来判断「是否到达终点」，那么从 `a1` 出发走 2 步到 `a3` 时就会**误判为「已经到了」**（因为 `a3->data == a1->data == 3`），从而错误地认为 `[a1, a3)` 是段——**但 `[a1, a3)` 的真实长度是 2，不是 0**。

**正确做法**：用**指针相等** `p == end`。`a1` 与 `a3` 是**两块不同的内存**，地址不同，故 `a1 != a3`，不会被误判。**指针是身份，内容是属性**——判断「是不是同一个节点」永远只能比地址。

**答 2.** 链表：`1 → 2 → 3 → 4 → 5 → 6 → 3`（`6` 的 `next` 指回 `3`）。**环 = `3 → 4 → 5 → 6 → 3`，环长 `L = 4`。**

初始：`t = 1`、`h = 2`。

| 轮 | `t` | `h` | `h == t`？ | 说明 |
|---|---|---|---|---|
| 初始 | `1` | `2` | 否 | `t = start`，`h = start->next` |
| 1 | `2` | `4` | 否 | `h`: `2→3→4`；`t`: `1→2` |
| 2 | `3` | `6` | 否 | `h`: `4→5→6`；`t`: `2→3` |
| 3 | `4` | `4` | **是** | `h`: `6→3→4`；`t`: `3→4` |

**第 3 轮相遇**，返回 `false`（有环）。

**环长 `L = 4`**，相遇用了 **3 轮 <= `L`**，上界成立。

**为什么上界是 `L`**：进入环后，两者距离 `d`（模 `L`）每轮减 1。最坏情形 `d = L - 1`，需 `L - 1` 轮追上，**第 `L - 1` 轮结束即相遇**。故「至多 `L` 轮」成立（严格说是 `L - 1` 轮追上后循环退出）。

**补充**：若 `t` 进入环时 `h` 恰好在 `t` 的位置（`d = 0`），则**立刻相遇**，0 轮。**实际总步数 = 进入环的步数 + 环内追及步数 <= n + L。**

**答 3.** **保持性失败的原因**：假设某轮开始 `t != NULL`。循环体执行 `t = t->next;`。要证新一轮 `t != NULL`，即证 `t->next != NULL`。**但 `t != NULL` 只说 `t` 是个有效地址，完全没说 `t->next` 是什么**——`t` 可能是**无环链表的最后一个节点**，此时 `t->next == NULL`。**故保持性不成立。**

**补 `is_segment(t, h)` 后 `t != NULL` 为何自动成立**：`is_segment(start, end)` 的**第一行**就是 `if (start == NULL) return false;`。故「`is_segment(t, h)` 为真」**蕴含 `t != NULL` 且 `h != NULL`**。**`t != NULL` 不再是需要单独维护的不变式，而是 `is_segment(t,h)` 的推论。** 这也是为什么改写版把 `//@assert t != NULL;` **删掉了**——不需要了。

**为什么还必须新增 `if (start->next == NULL) return true;`**：改写版把循环内的 `NULL` 检查从 `h == NULL || h->next == NULL` 改成了 `h->next == NULL || h->next->next == NULL`。若 `start->next == NULL`，则 `h = start->next = NULL`，进入循环后**第一个检查就是 `h->next`，即解引用 `NULL`**——**崩溃**。

**原版为什么不需要**：原版循环内先查 `h == NULL`，短路后不会解引用。

**更深一层的原因**：`is_segment(t, h)` 在 INIT 时要成立。INIT 时 `t = start`、`h = start->next`，故需要 `is_segment(start, start->next)`——这要求 `start->next` **存在**（非 `NULL`），否则 `is_segment(start, NULL)` 返回 `false`，INIT 失败。**所以入口的 `NULL` 检查既是为了运行时安全，也是为了不变式的初始化。两处改动是配套的。**

**答 4.** 初始：`front → [1] → [2] → [X] ← back`。

| 步 | 语句 | 变化 |
|---|---|---|
| 0 | 入口 | `front = n1`、`back = X`；`n1 = [1, →n2]`、`n2 = [2, →X]`、`X = [?, →NULL]` |
| 1 | `new_dummy = alloc(list)` | 新节点 `Y`，`Y = [默认, →NULL]` |
| 2 | `Q->back->data = x` | **`X.data = 3`**（`X` 从哑节点**转正**为数据节点） |
| 3 | `Q->back->next = new_dummy` | **`X.next = Y`** |
| 4 | `Q->back = new_dummy` | **`back = Y`** |

**最终**：`front → [1] → [2] → [3] → [Y] ← back`。队列有 3 个元素。

**为什么最后两行不能交换**（习题 13）：若先 `Q->back = Y`，则 **`Q` 里再也找不到 `X` 的地址**（`front` 只指向 `n1`，`back` 已指向 `Y`）。而 `X` 里刚写入了 `3`，且 `X.next` 仍是 `NULL`。此时再执行 `Q->back->next = new_dummy`，即 **`Y.next = Y`**——**自环**。

**后果**：`is_acyclic(front)` 为假（`Y` 自环），`is_queue` 破坏。**且 `X` 与队列脱节，`3` 丢失。**

**能不能修**：可以遍历整个队列找到 `X`，但那是 `O(n)`，**`enq` 的 `O(1)` 就没了**。

**一般教训**：**改指针时「先接新链，再断旧链」**。顺序反了会**丢失句柄**。

**答 5.**

**（1）为什么 `lseg_binsearch` 是 `O(n log n)`**：二分查找做 `log n` 次探测，但**每次探测是 `ith(start, mid)`**，而链表没有随机访问——`ith` 必须从 `start` 走 `mid` 步，**`O(mid) = O(n)`**。故总代价 `log n × O(n) = O(n log n)`。**对照数组二分**：`A[mid]` 是 `O(1)`，故 `log n × O(1) = O(log n)`。**`O(log n)` 不是二分查找算法的固有属性，而是「二分 + 随机访问」这个组合的属性。**

**（2）为什么共享对栈安全、对队列危险**：**栈只在 `top` 一端操作**——`push` 只写**新分配的节点**，`pop` 只移动 `top`，**从不修改共享节点的内容**；**队列的 `enq` 要往「另一端的哑节点」写数据**，而共享的恰恰是那一端——一次普通入队就会**静默改掉另一个队列的元素并切断它的链**。**一句话：「只在一端写」的结构可以安全共享，「两端都写」的结构不能。**

</details>

## 12. 进一步学习

- 上一讲：[[15-122-09-Stacks-and-Queues]] —— 只给接口、不谈实现；本讲用链表把接口填上，**`pop`/`deq` 同构、`push` 与 `enq` 对称**。
- 下一讲：[[15-122-11-Unbounded-Arrays]] —— 换一条路：用**数组**实现无界容器，引入**摊还分析（amortized analysis）**。**对比本讲的链表：`push` 严格 `O(1)` 但每个元素多一个指针；无界数组摊还 `O(1)` 但单次可能 `O(n)`、且缓存友好。**
- 相关讲次：[[15-122-06-Binary-Search]]（习题 5 的数组版原型）、[[15-122-07-Quicksort]]（链表上排序是另一个经典话题）、[[15-122-13-Hash-Dictionaries]]（另一个抽象类型）。
- 课程入口：[[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]]、[[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 术语查询：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Linked List、Node、Recursive Type、Concrete Type、Segment、Dummy Node、Representation Invariant、Cycle、Tortoise and Hare、Sharing、Garbage Collection、Unreachable 等条目）。
- 延伸阅读：Robert W. Floyd 的 "Non-deterministic Algorithms"（1967）——龟兔算法的原始出处；本讲第 7 页明确引用。另可看「持久化数据结构（persistent data structure）」相关文献，本讲第 6 节的 sharing 是其最朴素的形态。
