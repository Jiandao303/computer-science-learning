---
course: CMU 15-122
course_name: Imperative Computation
semester: Fall 2026
lecture_id: L13
topic: Hash Dictionaries
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-122
  - 哈希字典
  - C0
---

# 第 13 讲：哈希字典（Hash Dictionaries）

## 1. 本节学习目标

学完本讲后，你应该能够：

1. 说明**关注点分离（separation of concerns）** 在库设计中的三层含义：**类型**、**操作及其前后置条件**、**渐进复杂度**都要写进接口。
2. 说出本讲引入的**新复杂情形**：**库需要客户端反过来提供一些操作**——并解释为什么哈希表是这个问题的最佳例子。
3. 用 `typedef _______ elem;`（下划线 = 客户端提供）实现「泛型」队列，并说明它**两个无法回避的缺点**（客户端必须拆文件、一个程序只能一种元素类型）。
4. 列出哈希字典接口中**库侧**提供的东西（`hdict_t`、`hdict_new`、`hdict_lookup`、`hdict_insert`）与**客户端**必须提供的东西（`entry`、`key`、`entry_key`、`key_hash`、`key_equiv`）。
5. **推导**出「客户端必须提供的函数恰好是三个」——从 `hdict_lookup` 与 `hdict_insert` 的算法需求逐条推出，而不是背下来。
6. 说明为什么 `entry` 必须是**指针类型且非 `NULL`**：因为 `hdict_lookup` 用 `NULL` 表示「键不存在」。
7. 说明 **Coherence（一致性）** 的精确含义：`key_equiv(k1,k2) ⟹ key_hash(k1) == key_hash(k2)`。
8. 用「`amlet` 查错词」这个反例**证明**「`key_equiv` 比 `key_hash` 粗」会导致**正确性**错误；并**证明**「`key_hash` 比 `key_equiv` 粗」只导致**性能**问题。
9. 写出字符串哈希的**多项式滚动**形式 `h = 31*h + ch`，并说明为什么 `h = h + ch` 会让**所有变位词（anagram）冲突**。
10. 读懂讲义的**三张链长分布统计表**（`h = h + ch` 最长链 176、`h = 31*h + ch` 最长链 10、`h = rand(r)*h` 最长链 11），并解释「最长链」为什么比「空链数」更能说明哈希质量。
11. 说明 `index_of_key` 里 `abs(...)` 为什么必需，以及它在 `key_hash(k) == int_min()` 时的**溢出隐患**。
12. 逐条列出 `is_hdict` 应有的**七条**不变式（讲义只写了三条，其余六条是注释），并说明为什么 `\length` 检查必须放在注解里。
13. 用**循环不变式**证明 `hdict_lookup` 与 `hdict_insert` 的后置条件，并说明 `//@assert p->data != NULL;` 那句「Not given by loop invariant!」的含义。
14. 说明扩容时**为什么必须重新插入每一个条目**（而不是复制），以及为什么判断「装载因子过高」要用**乘法** `size >= capacity * maxload` 而不是除法。
15. 解释 `hdict_insert` 与 `hdict_resize` 的**互递归**为什么需要**前向声明（forward declaration）**，以及为什么**不能**用 `hdict_new` 来「重定义」`H`。
16. 用 **`prev` 指针**技巧实现 `hdict_delete`，并说明为什么「把 `p` 设成 `p->next`」这种写法**根本不会修改链**。
17. 说明**哈希集合（hash set）** 如何从哈希字典**特化**而来（三个简化步骤），以及为什么 `elem` 可以是**任意类型**（不再必须是指针）。

## 2. 前置知识

- [[15-122-12-Hashing]]：链地址法、装载因子 `α = n/m`、冲突、平均 `O(1)`、生日悖论、LCG。**本讲是它的「工程化」版本**：把「哈希表」包装成有接口、有不变式、有客户端契约的**抽象类型**。
- [[15-122-08-Libraries]]：抽象类型、`typedef ______* xxx_t;`、`is_xxx` 不变式、**「长度检查只能放在契约里」**（`is_array_expected_length`）。
- [[15-122-10-Linked-Lists]]：`chain_node` 就是链表节点；头插法 `p->next = H->table[i]; H->table[i] = p;`。
- [[15-122-11-Unbounded-Arrays]]：**扩容 + 摊还 + 四分之一缩容**——本讲习题 3、5 直接复用。
- [[15-122-06-Binary-Search]]：`key_equiv` 与「键唯一」的关系，可对照「有序数组中不允许重复」的讨论。
- [[15-122-01-Contracts]]：`//@requires` / `//@ensures` / `//@loop_invariant` / `//@assert` 的语义；**「不看被调函数体」的指向式推理**——本讲的接口设计正是为了让客户端**不需要看实现**。

## 3. 核心概念

**Separation of Concerns（关注点分离）**：把「客户端能依赖什么」与「实现怎么变」分开。**接口 = 类型 + 操作 + 前后置条件 + 渐进复杂度。**

**Library（库）**：提供数据结构与操作的实现代码。

**Client（客户端）**：使用库的代码。

**Client-Supplied Type（客户端提供的类型）**：接口里写成 `// typedef _______ elem;`——**下划线表示「库不知道它是什么，由客户端定义」**。

**Library-Supplied Abstract Type（库提供的抽象类型）**：接口里写成 `// typedef ______* hdict_t;`——**下划线表示「客户端不知道它怎么实现，只知道它是个指针」**。

**Generic（泛型的）**：一份实现服务任意元素类型。

**hdict（哈希字典）**：用哈希表实现的字典。

**Entry（条目）**：哈希字典里存的东西，**必须是指针类型、必须非 `NULL`**。

**Key（键）**：从条目里能取出来的标识，**在一个字典内唯一**。

**entry_key(entry x)**：客户端提供的函数，**从条目里取出键**。

**key_hash(key k)**：客户端提供的函数，**把键映射成任意整数**（不必在 `[0, m)` 内）。

**key_equiv(key k1, key k2)**：客户端提供的函数，**判断两个键是否相等**。

**Coherence（一致性）**：`key_equiv(k1, k2)` 为真 ⟹ `key_hash(k1) == key_hash(k2)`。**「被认为相等的键必须哈希到同一个值」。**

**index_of_key(H, k)**：库内的辅助函数，把 `key_hash` 的结果压到 `[0, capacity)`。

**Load Factor（装载因子）** `α = size/capacity`；**maxload**：客户端可配置的扩容阈值。

**Hash Set（哈希集合）**：把「键」与「条目」合并成同一个 `elem` 的哈希字典特化版。

**Forward Declaration（前向声明）**：在首次使用前写出函数原型，用于**互递归**。

**Mutual Recursion（互递归）**：`hdict_insert` 调 `hdict_resize`、`hdict_resize` 调 `hdict_insert`。

## 4. 通俗理解

**本讲的主题不是「哈希表怎么实现」（上一讲已讲），而是「接口该怎么设计」。** 讲义 p1 开篇就把这一点摆明：

> **「With this lecture, we will also begin to discuss a new **separation of concerns**. Previously, we have talked a great deal about the distinction between a library's **interface** (which the client can rely on) and a library's **implementation** (which should be able to change without affecting a correctly-designed client).」**

**接口的三层内容（讲义 p1 原文）**：

> **「The interface deﬁnes not only the **types**, but also the available **operations** on them and the **pre- and post-conditions** for these operations. For general data structures it is also useful to note the **asymptotic complexity** of the operations so that potential clients can decide if the interface serves their purpose.」**

**第三条最容易忘**：**「`hdict_lookup` 是 `O(1) avg.`」这句话本身是接口的一部分**。**客户端有权根据它做设计决策**（比如「我要不要用这个库」）。**若某天实现退化成 `O(n)`，那是「违反接口」，不是「优化」**——**因为客户端可能已经按 `O(1)` 做了假设。**

**本讲的新问题（讲义 p1 原文）**：

> **「One wrinkle we have not yet encountered is that, **in order for a library to provide its services, it may in turn require some operations supplied by the client**. Hash tables provide an excellent example for this complication, so we will discuss the interface to hash tables in details before giving the hash table implementation.」**

**为什么是「新问题」**：前面所有库（栈、队列、无界数组、自排序数组）都是**单向依赖**——**客户端调库，库不认识客户端**。**但哈希字典做不到**：**库要算哈希、要比键、要从条目里取键，而这些都取决于「键是什么类型」「条目长什么样」**——**只有客户端知道**。

**一句话**：**哈希字典的库是「半成品」，必须由客户端补齐三块零件才能用。** **这是「泛型」在 C0 这种没有模板的语言里的唯一实现方式。**

**「下划线」的两种含义（讲义 p2–3）**：

| 写法 | 含义 | 谁被保护 |
|---|---|---|
| `// typedef ______* hdict_t;` | **客户端只知道它是指针** | **库的实现可以随便改**（客户端看不见字段） |
| `// typedef _______ elem;` | **库只知道有这么个类型** | **客户端可以随便改**（库不假设 `elem` 是什么） |

**讲义 p3 原文**：

> **「The underscores in the library interface, before `queue_t`, mean that the client doesn't know how the abstract type `queue_t` is implemented beyond knowing that it is a pointer. The library is therefore free to change this implementation without breaking any (interface-respecting) client code. The underscores in the client interface mean that the library doesn't know how the abstract type `elem` is implemented, which means that **the client is free to change this implementation without breaking the library**.」**

**两条对称的保证**——**这就是「关注点分离」的双向版本**：**不是「库隐藏实现」，而是「双方都隐藏对方的实现」。**

**代价（讲义 p3）**：**客户端必须拆成至少两个文件**——`queue-client.c0`（定义 `elem`）+ `main.c0`（用库）。**编译顺序也必须对**：

```
% cc0 queue-client.c0 queue.c0 main.c0
```

**为什么必须拆**：`elem` 必须在库**之前**定义（库要用它），而 `main` 必须在库**之后**（`main` 要用库的函数）。**同一个文件里做不到「先定义 `elem` 给库用、再用库的函数」**——**因为 `#include` 式的文本拼接顺序被文件边界切断了。**

**还剩下一个缺点（讲义 p3 原文）**：

> **「This approach is still not perfect, because **any given program only supports a single type of queue element**. We'll start working on that problem in the next lecture.」**

**一个程序只能有一种 `elem`**——**因为 `typedef string elem;` 与 `typedef int elem;` 同时存在就是重复定义。** **解法在下一讲（C1 的 `void*`）**——本库的复习幻灯片 `12-voidstar.pdf` 已经把这条路讲完了（见 [[15-122-12-Hashing]] 5.9）。

**为什么「三个客户端函数」正好是三个**：**这不是设计者拍脑袋决定的，而是被 `hdict_lookup` 的算法逼出来的。** 想一遍查找的过程：

1. **要算下标**：`index_of_key(H, k)` → 需要 **`key_hash(k)`**。
2. **要在链上比较**：`key_equiv(entry_key(p->data), k)` → 需要 **`entry_key`**（从条目取出键）与 **`key_equiv`**（比较两个键）。

**三个需求，三个函数。** **一个不多，一个不少。** **这就是「接口应由算法的需求推导，而非由实现者的方便决定」。**

**为什么 `entry` 必须是指针（讲义 p4–5）**：

> **「we will however require entries to have pointer type and be non-`NULL`. **Doing so allows `hdict_lookup` to return `NULL` to signal that the dictionary does not contain any entry with the requested key.**」**

**`NULL` 是「没有」的信使**。**若 `entry` 可以是 `int`，那「没找到」返回什么？** 返回 `0`？**那 `0` 这个条目怎么办？** **没有「哨兵值」可用。** **故 `entry` 必须是指针，`NULL` 才有意义。**

**注意对比**：**哈希集合里 `elem` 可以是任意类型**（讲义 p15）——**因为 `hset_contains` 返回 `bool`，不需要哨兵。** **「能不能用值类型」完全取决于「接口有没有用 `NULL` 表示缺失」。**

**Coherence 的直觉**：**「相等的东西必须哈希到同一个地方」**。**否则你把它放在 A 格，却去 B 格找它。**

**两个反例（讲义 p11–12）**：

**反例一（`key_equiv` 太粗）**：把「键相等」定义成「长度相等」。

- `key_hash("amlet")` 算出某个下标 `i`。
- 若 `H->table[i]` 上恰好挂着某个**长度也是 5** 的条目（比如 `"apple"`），**`key_equiv` 会说「相等」**。
- **于是 `hdict_lookup(H, "amlet")` 返回了 `"apple"` 的条目。** **这是彻头彻尾的错误答案。**

**反例二（`key_hash` 太粗）**：把 `key_hash` 定义成「首字母的 ASCII 码」。

- **所有以 `'a'` 开头的词都挤在同一格。**
- **但 `key_equiv` 还是严格的字符串相等**——**所以查 `"apple"` 时会在那条长链上逐个比，最终要么找到 `"apple"`、要么正确地返回 `NULL`。**
- **结果是对的，只是慢。** **这是性能问题，不是正确性问题。**

**讲义 p11–12 的总结**：

> **「In a well-designed hash table, **keys that are considered equal should hash to the same value**, a condition we call **coherence**. As we just saw, whenever the hashing and the equivalence functions are incoherent, there is the concrete risk of our hash dictionaries working incorrectly.」**

**为什么「一致」只在一个方向要求**：**只要求 `equiv ⟹ same hash`，不要求 `same hash ⟹ equiv`**。**因为「哈希相同」是「碰撞」，是允许的；「等价但哈希不同」才是致命的**——**那意味着「同一个东西有两个地址」。**

**形式化**：

```
Coherence:  ∀ k1, k2.  key_equiv(k1, k2)  ⟹  key_hash(k1) == key_hash(k2)
等价说法:   ∀ k1, k2.  key_hash(k1) != key_hash(k2)  ⟹  !key_equiv(k1, k2)     （逆否）
```

**第二条读法更直观**：**「哈希值不同 ⟹ 一定不相等」**——**故「哈希值不同」可以作为「不相等」的快速判据。** **这正是哈希表能跳过绝大多数比较的原因。**

**字符串哈希的三级进化（讲义 p7–10）**：

| 版本 | 代码 | 最长链（45600 词、22800 格） | 问题 |
|---|---|---|---|
| 1 | 不组合（`h` 恒 0） | **45600**（全在一条链上） | **等于链表** |
| 2 | `h = h + ch` | **176** | **变位词全冲突** |
| 3 | `h = 31*h + ch` | **10** | **好**（Java 采用） |
| 4 | `h = rand(r)*h + ch` | **11** | **略差于 3** |

**为什么 `h = h + ch` 会「变位词全冲突」**：**加法可交换**——`"abc"` 与 `"cab"` 的字符和相同。**故所有由同一组字母重排而成的词，哈希值必然相同。** 讲义 p9 原文：

> **「An even bigger problem is that **rearranging the letters in a string will always produce another string with the same hash value** — so we know that `"cab"` and `"abc"` will always collide in a hash table. **Hash collisions are inevitable, but when we can easily predict that two strings have the same hash value, we should be suspicious that something is wrong.**」**

**「可预测的冲突」是设计缺陷的标志**：**随机冲突无法避免（生日悖论），但「结构性的、能被对手构造的冲突」说明哈希函数丢了信息。** **`h = h + ch` 丢掉了「顺序」，而顺序是字符串的主要信息。**

**`31*h + ch` 为什么修好了**：**乘法使位置有权重**——`"abc"` 得 `(97*31+98)*31+99`，`"cab"` 得 `(99*31+97)*31+98`，**不同。** **这就是「多项式滚动哈希（polynomial rolling hash）」**：把字符串看成**以 31 为底的大数**。

**为什么是 31**：**奇数**（避免信息丢失）、**接近 2 的幂**（`31 = 32-1`，编译器可优化成 `(h<<5) - h`）、**足够小**（不溢出得太快）。**Java 选它就是因为这三点。**

**「最长链」比「空链数」更重要**：**查找的代价由「最坏那条链」决定**（讲义 p5 的 `O(n)` 最坏情形）。**空链多说明「分布不均」，最长链长说明「真的会慢」。** **三个统计里，`h = h+ch` 的最长链 176 是灾难性的**——**176 次字符串比较，比线性查找还慢（因为还要算哈希）。**

## 5. 原理与推导

### 5.1 接口的双向契约：谁提供什么

**把哈希字典接口的两侧摆在一起（讲义 p5–6）**：

```
/************************/
/*** Client interface ***/
/************************/
// typedef ______* entry;        // 客户端提供：条目类型（必须是指针）
// typedef _______ key;          // 客户端提供：键类型
key  entry_key(entry x)  /*@requires x != NULL; @*/ ;   // 客户端提供
int  key_hash(key k);                                    // 客户端提供
bool key_equiv(key k1, key k2);                          // 客户端提供

/*************************/
/*** Library interface ***/
/*************************/
// typedef ______* hdict_t;      // 库提供：字典类型（客户端只知是指针）
hdict_t hdict_new(int capacity)
/*@requires capacity > 0; @*/
/*@ensures \result != NULL; @*/ ;
entry hdict_lookup(hdict_t H, key k)
/*@requires H != NULL; @*/
/*@ensures \result == NULL || key_equiv(entry_key(\result), k); @*/ ;
void hdict_insert(hdict_t H, entry x)
/*@requires H != NULL && x != NULL; @*/
/*@ensures hdict_lookup(H, entry_key(x)) == x; @*/ ;
```

**注意三件事**：

**（1）库只提供一个类型 `hdict_t`。** 讲义 p3 原文：「That is really the only type provided by the implementation.」**所有别的类型都是客户端的。**

**（2）`hdict_lookup` 的后置条件用客户端的函数表达**：

```
\result == NULL || key_equiv(entry_key(\result), k)
```

**读法**：**「要么返回 `NULL`（没找到），要么返回的条目其键与 `k` 等价」。** **注意它没有承诺「找到了就一定是唯一的那个」**——**因为「键唯一」是 `hdict_insert` 的责任（重复插入会覆盖），不是 `lookup` 的责任。**

**（3）`hdict_insert` 的后置条件是「插入后能查回来」**：

```
hdict_lookup(H, entry_key(x)) == x
```

**这条非常强**：**它用 `hdict_lookup` 来定义 `hdict_insert` 的效果**——**「插入 `x` 之后，用 `x` 的键查，必须得到 `x` 本身」。** **这是「抽象规格」的典范：不描述「怎么存」，只描述「能观察到什么」。**

**为什么这条后置需要 `entry_key`**：**`hdict_lookup` 的参数是 `key`，而 `hdict_insert` 的参数是 `entry`。** **要把两者接起来，必须能「从条目取出键」**——**这就是 `entry_key` 存在的第一个理由。**

**为什么 `hdict_lookup` 的 `\result` 是 `entry` 而不是 `bool`**：**因为字典要「按键取值」**。**若只要「在不在」，那就是集合（见 5.11）。**

### 5.2 泛型的三条路：为什么 C0 只能走「客户端定义类型」

**问题**：栈/队列/字典的实现代码**与元素类型无关**。**怎么让一份代码服务所有类型？**

**三条可能的路**：

| 路 | 做法 | 在 C0 里可行？ |
|---|---|---|
| 1. **模板 / 泛型参数**（C++ `template<typename T>`、Java `<T>`） | 语言级支持 | ❌ **C0 没有** |
| 2. **`void*` 泛型指针** | 类型擦除 + 运行期标签 | ❌ **C0 没有**（**C1 才有**） |
| 3. **客户端定义类型名** | `typedef _______ elem;` | ✅ **本讲的做法** |

**为什么路 3 可行**：**C0 的 `typedef` 是「文本替换级」的**——`typedef string elem;` 之后，**库里的 `elem` 就是 `string`**。**编译器在编译库时已经知道 `elem` 是什么**（因为客户端文件先编译/先拼接）。**故不需要运行期类型信息，也不需要类型擦除。**

**代价一：必须拆文件（编译顺序约束）**。

**依赖图**：

```
client-queue.c0  (typedef string elem;)
       ↓ 提供 elem
    queue.c0     (库：用 elem)
       ↓ 提供 queue_t 与函数
    main.c0      (应用：用库)
```

**故编译命令必须按这个顺序**：

```
% cc0 queue-client.c0 queue.c0 main.c0
```

**讲义 p3 原文**：「in order to respect the dependencies」。

**代价二：一个程序只能一种 `elem`。**

**为什么**：`elem` 是**全局类型名**，**只能 `typedef` 一次**。**故 `main.c0` 里不可能同时有「字符串队列」与「整数队列」**——**除非你复制整个库、改名为 `int_queue` / `str_queue`**（**这正是幻灯片 `12-voidstar.pdf` p3–4 说的「灾难」**）。

**代价三：修 bug 要改多处**（如果你走了「复制库」的路）：

> **「If we discover a bug, we need to fix it in every copy of the library ... For a large application, this quickly becomes unmanageable.」**（`12-voidstar.pdf` p4）

**三条代价的根源都是「C0 没有真正的泛型」**。**路 3 是「在没有泛型的语言里模拟泛型」的最省事办法**——**它有代价，但比「复制库」好得多。**

### 5.3 为什么恰好三个客户端函数——从算法反推

**这一步值得慢慢走，因为它是「接口设计方法论」的核心。**

**`hdict_lookup(H, k)` 的算法（讲义 p13–14）**：

```c0
entry hdict_lookup(hdict* H, key k) {
  int i = index_of_key(H, k);                       // ← 需要 key → 下标
  for (chain* p = H->table[i]; p != NULL; p = p->next) {
    if (key_equiv(entry_key(p->data), k))            // ← 需要 entry → key，key × key → bool
      return p->data;
  }
  return NULL;
}
```

**逐行提取需求**：

| 代码 | 需求 | 客户端函数 |
|---|---|---|
| `index_of_key(H, k)` | 把 `key` 变成整数下标 | **`key_hash(key k)`** |
| `entry_key(p->data)` | 把 `entry` 变成 `key` | **`entry_key(entry x)`** |
| `key_equiv(..., k)` | 比较两个 `key` | **`key_equiv(key k1, key k2)`** |

**`hdict_insert` 需要什么额外的吗**：

```c0
void hdict_insert(hdict* H, entry x) {
  key k = entry_key(x);                    // ← 同一个 entry_key
  int i = index_of_key(H, k);              // ← 同一个 key_hash
  for (chain* p = H->table[i]; p != NULL; p = p->next) {
    if (key_equiv(entry_key(p->data), k)) { // ← 同一个 key_equiv
      p->data = x;
      return;
    }
  }
  // 头插
  chain* p = alloc(chain);
  p->data = x;
  p->next = H->table[i];
  H->table[i] = p;
  (H->size)++;
}
```

**没有新需求。** ✅ **故「三个」是精确的：少一个算法写不出来，多一个是冗余。**

**注意 `key_hash` 的返回类型是 `int`，不是 `[0, m)` 内的值**（讲义 p5 原文）：

> **「The result, the hash value, can be any integer, so our hash table implementation will have to take both this arbitrary integer and `m`, the size of the hash table's table, into consideration when ﬁguring out which index of the table the key hashes to.」**

**为什么不让客户端直接返回 `[0, m)`**：**因为客户端不知道 `m`**——**`m` 是库的内部状态（`H->capacity`）。** **故「取模」这一步必须由库做。**

**习题 4 就是这个设计的「另一种选择」**：把 `m` 传给客户端（`key_hash(key k, int m)`），**让客户端负责取模**。**讲义 p22–23 的解答说这样 `index_of_key` 就退化成一行**：

```c0
int index_of_key(hdict* H, key k) {
  return key_hash(k, H->capacity);
}
```

**代价是客户端的契约更重**：

```c0
int key_hash(key k, int m)
/*@requires m > 0; @*/
/*@ensures 0 <= \result && \result < m; @*/ ;
```

**「`\result < m`」这条后置现在成了客户端的义务**——**客户端写错就是越界。** **原设计里「取模」由库保证，客户端只负责「返回任意整数」，责任更轻。** **这就是「接口边界画在哪里」的权衡。**

### 5.4 Coherence：为什么「一致性」只在正确性上单向致命

**定义（讲义 p11）**：

```
Coherence:  key_equiv(k1, k2)  ⟹  key_hash(k1) == key_hash(k2)
```

**为什么这条是「正确性」的必要条件——严格论证**：

设 `x` 是已插入字典的条目，`k = entry_key(x)`。**由 `hdict_insert` 的代码，`x` 一定在链 `H->table[index_of_key(H, k)]` 上。**

**现在查 `k'`，满足 `key_equiv(k, k')`。** 若 **coherence 成立**，则 `key_hash(k') == key_hash(k)`，**故 `index_of_key(H, k') == index_of_key(H, k)`**——**`x` 就在要搜的那条链上**，`key_equiv` 会认出它。✅

**若 coherence 不成立**：`key_hash(k') != key_hash(k)`，**`x` 在另一条链上，`hdict_lookup(H, k')` 根本不会走到那里**——**返回 `NULL`，尽管字典里「按 `key_equiv` 的定义」确实有 `k'` 这个键。** ❌ **后置条件被违反。**

**这就是「等价但哈希不同」的致命后果**：**条目「存在但找不到」——比「不存在」更糟，因为客户端无法区分。**

**反例一的形式化**（`key_equiv` 太粗）：`key_equiv(k1,k2) := string_length(k1) == string_length(k2)`，`key_hash` 仍是好的字符串哈希。

- **coherence 显然不成立**：`"apple"` 与 `"amlet"` 长度都是 5，**故 `key_equiv` 为真，但 `key_hash` 不同**。
- **后果**：查 `"amlet"` 时，若 `"amlet"` 的哈希下标上恰有 `"apple"`（**这需要 `key_hash("amlet") == key_hash("apple")`**，即**一次真实的碰撞**），**`key_equiv("apple","amlet")` 返回真 → 返回 `"apple"` 的条目**。
- **讲义 p11 原文**：「If this chain contains an entry whose key has length 5 (the length of `"amlet"`), **it will return this entry, although its key is not `"amlet"`! This result is incorrect.**」

**注意这个反例需要「碰撞」才能触发**——**故它是「间歇性」的 bug**，**极难调试**。**这也是为什么 coherence 必须作为「接口约定」显式提出**：**没有它，客户端可以写出「大部分时候对、偶尔错」的代码。**

**反例二的形式化**（`key_hash` 太粗）：`key_hash(k) := char_ord(string_charat(k, 0))`（首字母 ASCII），`key_equiv` 是严格字符串相等。

- **coherence 成立吗？** **成立**——**若两个字符串相等，首字母必然相同，故哈希相同。** ✅
- **故正确性没问题。**
- **但性能崩了**：**所有以 `'a'` 开头的词在同一条链上。** 讲义 p11–12 原文：「Then every word starting with the same letter will have the same hash value ... Its chains will be very long for a large dictionary, while other indices will be empty ... **The issue here is performance, not correctness**: this choice leads to long chains and therefore slow searches.」

**故「coherence」是正确性的**必要**条件，但不是「性能」的充分条件。** **要性能好，还需要「分布均匀」**（[[15-122-12-Hashing]] 5.3 的均匀假设）。

**讲义 p12 的总结句**：

> **「The problem with both of these setups is that `key_hash` and `key_equiv` used the information in the key in **very different measures**. Instead, our original choices were very much in harmony.」**

**「用不同量的信息」**——**这是最精辟的诊断**：

| 组合 | `key_equiv` 用的信息 | `key_hash` 用的信息 | 结果 |
|---|---|---|---|
| 长度 + 长度 | 长度 | 全部（若哈希好） | **不一致 → 错误** |
| 全部 + 首字母 | 全部 | 首字母 | **一致但失衡 → 慢** |
| **全部 + 全部** | **全部** | **全部** | ✅ **正确且快** |

**故「coherence + 均匀」= 「两个函数用同样多的信息，且都用全部信息」。** **这是设计哈希字典时的第一原则。**

### 5.5 字符串哈希：从 `h + ch` 到多项式滚动

**骨架（讲义 p8）**：

```c0
int hash_string(string s) {
  int len = string_length(s);
  int h = 0;
  for (int i = 0; i < len; i++)
  //@loop_invariant 0 <= i;
  {
    int ch = char_ord(string_charat(s, i));
    // Do something to combine h and ch
  }
  return h;
}
```

**用到的两个 C0 库函数**（讲义 p7）：**`string_charat(s, i)`** 取第 `i` 个字符，**`char_ord(c)`** 取 `char` 的 ASCII 整数值。

**版本 1：什么都不做（`h` 恒 0）**。

讲义 p8 原文：「the function above will still allow the hash table to work correctly, it will just be **very slow** because **the hash value of every string will be zero**.」

**「正确但极慢」**——**所有条目一条链，退化成链表。** **注意这仍然是「合法」的**（讲义 p5 说过：「The hash set implementation will work correctly (albeit slowly) even if it maps every key to 0.」）——**故哈希函数的质量只影响性能，不影响正确性。** **这是「哈希表」与「哈希字典的正确性」之间的分工。**

**版本 2：`h = h + ch`**。

**为什么必然失败（数学论证）**：设字符串 `s` 的字符为 `c_0, c_1, ..., c_{n-1}`。则

```
h(s) = Σ_{i=0}^{n-1} char_ord(c_i)
```

**这是「字符的算术和」——与顺序无关。** 故**任意两个变位词（anagram）哈希值相同**：

```
h("abc") = 97 + 98 + 99 = 294
h("cab") = 99 + 97 + 98 = 294   ← 相同！
h("bca") = 98 + 99 + 97 = 294   ← 相同！
```

**更糟的是「值太小」**：45,600 个英文词的平均长度约 8，**平均字符和约 `8 × 100 = 800`**——**若 `m = 22800`，那么所有哈希值都落在 `[0, 800]` 这 801 个格子里！** **有效格子数只有 `m` 的 3.5%。**

**这解释了统计表（讲义 p8）**：

```
Hash table distribution: how many chains have size...
...0:     21217        ← 93% 的链是空的！
...1:       239
...2:       132
...3:        78
...4:        73
...5:        55
...6:        60
...7:        46
...8:        42
...9:        23
...10+:    835        ← 835 条链有 10 个以上
Longest chain: 176
```

**核对**：`21217 + 239 + 132 + 78 + 73 + 55 + 60 + 46 + 42 + 23 + 835 = 22800` ✅ **等于 `m`**（每条链恰好被数一次）。

**读法**：**`m = 22800`、`n = 45600`、`α = 2`——「名义上」平均链长 2。** **但实际 93% 的链空着，而 835 条链挤了绝大部分条目，最长一条 176 个。** **这就是「分布不均」的量化形态。**

**版本 3：`h = 31*h + ch`（多项式滚动哈希）**。

```c0
for (int i = 0; i < len; i++)
//@loop_invariant 0 <= i;
{
  int ch = char_ord(string_charat(s, i));
  h = 31*h;
  h = h + ch;
}
```

**数学形式**：

```
h(s) = ((((c_0)*31 + c_1)*31 + c_2)*31 + ...)*31 + c_{n-1}
     = Σ_{i=0}^{n-1} c_i * 31^(n-1-i)
```

**这就是「以 31 为底、把字符串看成大数」**——**故叫「多项式滚动哈希」。**

**为什么修好了变位词问题**：**位置 `i` 有权重 `31^(n-1-i)`，不同位置的字符贡献不同。** `"abc"` 得 `97*31^2 + 98*31 + 99 = 93214`，`"cab"` 得 `99*31^2 + 97*31 + 98 = 98230`——**不同** ✅。

**为什么选 31（三条理由）**：

1. **奇数**：**若选偶数，乘法会把低位「清零」**（乘 2 等于左移，最低位变 0），**信息丢失**。
2. **`31 = 2^5 - 1`**：**编译器可把 `31*h` 优化成 `(h << 5) - h`**——**一次移位 + 一次减法，比乘法快。**
3. **足够小**：**`31^7 ≈ 2.75 × 10^10 > 2^31`**，**故 7 个字符后开始溢出（模 `2^32`）**——**溢出本身是「免费取模」，但太小会损失区分度。** **31 在「区分度」与「不溢出太快」之间平衡。**

**统计表（讲义 p9）**：

```
...0:     3057        ← 只有 13% 空
...1:     6210
...2:     6139
...3:     4084
...4:     2151
...5:      809
...6:      271
...7:       53
...8:       21
...9:        4
...10+:      1
Longest chain: 10
```

**核对**：`3057+6210+6139+4084+2151+809+271+53+21+4+1 = 22800` ✅

**读法**：**最长链从 176 降到 10**——**17.6 倍的改善。** **且分布接近「泊松分布」（`α = 2` 时理论最长链约 `log n / log log n ≈ 10`）**——**这正是「均匀哈希」的期望形态。**

**版本 4：`h = rand(r)*h + ch`**。

```c0
rand_t r = init_rand(0x1337BEEF);
for (int i = 0; i < len; i++)
//@loop_invariant 0 <= i;
{
  int ch = char_ord(string_charat(s, i));
  h = rand(r) * h;
  h = h + ch;
}
```

**统计表（讲义 p10）**：

```
...0:     3796        ← 空链比版本 3 多
...1:     6214
...2:     5424
...3:     3589
...4:     2101
...5:     1006
...6:      455
...7:      145
...8:       48
...9:       15
...10+:      7
Longest chain: 11
```

**核对**：`3796+6214+5424+3589+2101+1006+455+145+48+15+7 = 22800` ✅

**讲义 p10 的评价**：

> **「If we look at the performance of this function, it is comparable to the Java hash function, though it is **not actually quite as good** — more of the chains are empty, and more are longer.」**

**为什么「随机乘数」没有更好**：**因为 `rand(r)` 的序列虽然看起来乱，但它是「按位置固定」的**——**第 `i` 个字符永远乘同一个数**（`r` 从同一个种子开始）。**故「随机」只是「换了一组固定的乘数」，并没有引入真正的不确定性。** **而 `31` 恰好是一组「碰巧很好」的固定乘数。**

**版本 5（讲义 p10 末）：每步做一次 LCG 步进**。

```c0
for (int i = 0; i < len; i++)
//@loop_invariant 0 <= i;
{
  int ch = char_ord(string_charat(s, i));
  h = 1664525 * h + 1013904223;
  h = h + ch;
}
```

**这是 `h = a*h + c + ch`**——**即「多项式滚动 + 仿射变换」**。**讲义没有给它的统计表**，**只说「Many other variants are possible」。**

**讲义 p10 的总结（本节的纲领）**：

> **「The key goals are that we want a hash function that is **very quick to compute** and that nevertheless **achieves good distribution** across our hash table. **Handwritten hash functions often do not work well**, which can significantly affect the performance of the hash table. Whenever possible, **the use of randomness can help to avoid any systematic bias**.」**

**两个目标互相冲突**：**快 = 少运算 = 少混合 = 分布差；分布好 = 多混合 = 慢。** **`31*h + ch` 是「每字符一次乘法 + 一次加法」——这是理论上的最小值（每个字符至少要参与一次运算）。** **故它在「快」这一端已经最优，而在「分布」这一端表现良好。**

### 5.6 `index_of_key`：`abs` 的必要性与隐患

**代码（讲义 p13）**：

```c0
int index_of_key(hdict* H, key k)
//@requires is_hdict(H);
//@ensures 0 <= \result && \result < H->capacity;
{
  return abs(key_hash(k) % H->capacity);
}
```

**为什么需要 `abs`**：**C0 的 `%` 结果符号跟被除数走**（[[15-122-02-Ints]]：`-7 % 5 == -2`）。**`key_hash` 可以返回负数**（讲义 p5：「The result, the hash value, can be **any integer**」），**故 `key_hash(k) % capacity` 可能是负数**——**不能直接当下标。**

**例**：`capacity = 10`、`key_hash(k) = -37`。则 `-37 % 10 = -7`，**`abs(-7) = 7`** ✅ **在 `[0, 10)` 内。**

**隐患（讲义未提，本笔记补充）**：**若 `key_hash(k) == int_min() = -2147483648`**，则

```
int_min() % capacity  →  某个负数 r，满足 -capacity < r <= 0
abs(r)                →  正常
```

**这条路径是安全的**（因为 `r` 的绝对值 `< capacity`，不会溢出）。

**但若有人写成 `abs(key_hash(k)) % H->capacity`（先 `abs` 再取模），就会出事**：`abs(int_min())` **在补码下等于 `int_min()` 本身**（因为 `-int_min()` 溢出回绕，[[15-122-02-Ints]] 5.4）——**结果仍是负数，后置条件被违反。**

**故「先取模、再 `abs`」的顺序是对的**，**而「先 `abs`、再取模」是错的**。**代码里 `abs(key_hash(k) % H->capacity)` 恰好是正确顺序**，**但这个正确性很脆弱**——**它依赖于「取模结果的绝对值小于除数」这条性质。**

**另一个隐含问题**：`abs` 使 `r` 与 `-r` 映到同一下标。**故 `capacity` 个槽位实际只用到约一半的「符号对称性」**——**但因为 `%` 已经把值压到 `(-capacity, capacity)`，`abs` 之后是 `[0, capacity)`，故没有浪费槽位。** **只是「`r` 与 `-r` 必然碰撞」**——**若 `key_hash` 是均匀的，这最多使有效槽位减半（当哈希值关于 0 对称时）。** **实践上影响不大，但值得知道。**

### 5.7 `is_hdict`：七条不变式，讲义只写了三条

**结构定义（讲义 p12）**：

```c0
typedef struct chain_node chain;
struct chain_node {
  entry data;      // != NULL
  chain* next;
};
typedef struct hdict_header hdict;
struct hdict_header {
  int size;        // 0 <= size
  int capacity;    // 0 < capacity
  chain*[] table;  // \length(table) == capacity
};
```

**讲义的 `is_hdict`（p12–13）——明确标注「incomplete」**：

```c0
bool is_hdict(hdict* H) {
  return H != NULL
      && 0 <= H->size
      && 0 < H->capacity
      && is_array_expected_length(H->table, H->capacity);
  /* && there are no NULL entries */
  /* && each entry satisfies its own representation invariants */
  /* && there aren't entries with equal key */
  /* && the number of entries matches the size */
  /* && every entry in H->table[i] hashes to i */
  /* && ... */
}
```

**六条注释 + 一个省略号 = 至少七条还缺着。** **逐条说明它们为什么必需**：

| # | 不变式 | 为什么必需 | 谁依赖它 |
|---|---|---|---|
| 1 | **链上无 `NULL` 条目** | `entry_key(p->data)` 的前置是 `p->data != NULL` | `hdict_lookup`、`hdict_insert` |
| 2 | **每个条目满足自己的表示不变式** | 库不该信任客户端的 `entry` 内部一致 | 客户端的 `entry_key`/`key_hash` |
| 3 | **没有两个条目有等价键** | 「键唯一」是字典的定义性性质 | `hdict_lookup` 的「返回唯一答案」 |
| 4 | **条目总数 == `size`** | `size` 是客户端可见的长度 | 未来的 `hdict_size`（习题 2） |
| 5 | **`H->table[i]` 上每个条目的键都哈希到 `i`** | 否则 `hdict_lookup` 找不到它 | **正确性核心** |
| 6 | **`table` 的每条链都是合法段（无环）** | 否则遍历不终止 | `for (p = ...; p != NULL; p = p->next)` |
| 7 | **`size <= capacity * maxload`**（扩容版才有） | 保证装载因子不超标 | 平均 `O(1)` 的承诺 |

**第 5 条是「哈希字典特有」的**——**讲义 p12 特意点出**：

> **「Besides the invariants noted above we should check **the hash index of the key of every entry in each chain stored in `A[i]` is indeed `i`**.」**

**为什么它是「正确性核心」**：**`hdict_lookup` 只搜一条链。** **若某条目挂错了链（它的键哈希到 `j != i`），那么查它的键时永远走不到 `i`**——**条目「存在但找不到」。** **这与 5.4 的 coherence 违反是同一个后果。**

**注意「第 5 条」与「coherence」的分工**：

- **Coherence** 是**客户端**的义务（`key_equiv` 与 `key_hash` 要一致）。
- **第 5 条** 是**库**的义务（插入时算对下标）。

**两者都满足，才能保证「查得到」。** **任一违反，都是「存在但找不到」。**

**为什么 `\length` 必须放在注解里（讲义 p13 原文）**：

> **「Recall that the test on the length of the array must be inside an annotation, because **the `\length` function is not available when the code is compiled without dynamic checking enabled**.」**

**`\length` 是 C0 的注解语法，不是运行期函数。** **故它只能出现在 `//@assert`、`//@requires`、`//@ensures` 里。** **这就是 `is_array_expected_length` 这个「永远返回 `true` 的规格函数」存在的原因**（[[15-122-08-Libraries]] 同款技巧）。

**`is_hdict` 不完整带来的实际后果**：**讲义明说了「This `is_hdict` function is incomplete」**——**故本讲的代码在 `cc0 -d` 下无法完整验证。** **这是「教学代码」与「生产代码」的差距：前者为了篇幅省略了六条不变式，后者必须写全。**

### 5.8 `hdict_lookup` 与 `hdict_insert` 的验证

**`hdict_lookup`（讲义 p13–14）**：

```c0
entry hdict_lookup(hdict* H, key k)
//@requires is_hdict(H);
//@ensures \result == NULL || key_equiv(entry_key(\result), k);
{
  int i = index_of_key(H, k);
  for (chain* p = H->table[i]; p != NULL; p = p->next) {
    if (key_equiv(entry_key(p->data), k))
      return p->data;
  }
  return NULL;
}
```

**需要的循环不变式（讲义未写，本笔记补）**：

```
//@loop_invariant p == NULL || is_segment(p, NULL);
//@loop_invariant !is_in_chain(H->table[i], k, <已扫描部分>);
```

**第二条的意思**：**「已经走过的那段链上没有键 `k` 的条目」**——**它是「找不到」这条返回路径的依据。** **与 [[15-122-06-Binary-Search]] 的 `!is_in(x, A, 0, lo)` 完全同构。**

**三种 `return` 的证明**：

| 返回路径 | 需要证明 | 依据 |
|---|---|---|
| `return p->data;`（在 `if` 内） | `key_equiv(entry_key(p->data), k)` | **`if` 条件直接给出** ✅ |
| `return NULL;`（循环后） | `\result == NULL` | **`NULL` 平凡满足 `\result == NULL` 这一支** ✅ |
| （任何路径） | `\result == NULL \|\| key_equiv(...)` | **两支各自成立，故析取成立** ✅ |

**注意第二条返回路径「太平凡了」**：**`return NULL` 自动满足后置条件的第一支。** **故 `hdict_lookup` 的后置条件「弱得几乎不用证」**——**它没有承诺「找不到时真的不存在」！**

**这是接口的一处「弱规格」**：**严格的后置条件应该是**

```
(\result == NULL && !exists_entry_with_key(H, k))
|| (\result != NULL && key_equiv(entry_key(\result), k))
```

**但 `exists_entry_with_key` 需要遍历整个表，客户端用不起**（那是 `O(n)`）。**故接口只承诺「找到的话键对」，不承诺「没找到就真没有」。** **这是「可观察行为」与「完整规格」之间的取舍**——**后者更强，但更难用。**

**`hdict_insert`（讲义 p14）**：

```c0
void hdict_insert(hdict* H, entry x)
//@requires is_hdict(H);
//@requires x != NULL;
//@ensures is_hdict(H);
//@ensures x == hdict_lookup(H, entry_key(x));
{
  key k = entry_key(x);
  int i = index_of_key(H, k);
  for (chain* p = H->table[i]; p != NULL; p = p->next) {
    //@assert p->data != NULL;            // Not given by loop invariant!
    if (key_equiv(entry_key(p->data), k)) {
      p->data = x;
      return;
    }
  }
  // prepend new entry
  chain* p = alloc(chain);
  p->data = x;
  p->next = H->table[i];
  H->table[i] = p;
  (H->size)++;
}
```

**那句 `//@assert p->data != NULL; // Not given by loop invariant!` 是本节最值得琢磨的一行。**

**它在说什么**：**`entry_key` 的前置是 `x != NULL`**（讲义 p4）。**故要调 `entry_key(p->data)`，必须知道 `p->data != NULL`。** **但循环不变式只写了「`p` 是合法段」，没写「段上每个节点的 `data` 非 `NULL`」。** **故验证器无法从不变式推出它——必须显式 `//@assert`。**

**为什么「应该」能从 `is_hdict` 推出来**：**`is_hdict` 的第 1 条不变式（「链上无 `NULL` 条目」）就蕴含它。** **但讲义说 `is_hdict` 是「incomplete」——那条没写进去。** **故只能靠局部的 `//@assert` 补上。**

**这是「不变式不完整」的具体代价**：**每处用到「缺失的那条不变式」的地方，都要手动 `//@assert` 一次。** **若不变式写全了，这一行就不需要。**

**两条后置条件的证明**：

**（a）`is_hdict(H)`**：**两条路径各自保持**。

- **覆盖路径**：`p->data = x;`——**只改了内容，没改链结构、没改 `size`、没改下标。** **需要证明「新条目 `x` 的键仍哈希到 `i`」**——**由 `i == index_of_key(H, k)` 与 `k == entry_key(x)` 直接得到** ✅。**需要证明「没有重复键」**——**因为 `x` 覆盖了同键的旧条目，键数不变** ✅。
- **头插路径**：`p->next = H->table[i]; H->table[i] = p; size++;`——**新条目挂在链头，其键哈希到 `i`**（同上的理由）✅；**`size` 加一，条目数也加一** ✅。

**（b）`x == hdict_lookup(H, entry_key(x))`**：**这是「插入后可查回」**。

- **覆盖路径**：**插入后链上有一条键为 `k` 的条目，其 `data` 是 `x`。** **`hdict_lookup(H, k)` 走到这条链，`key_equiv(entry_key(x), k)` 为真**（因为 `k == entry_key(x)` 且 `key_equiv` 自反），**返回 `x`** ✅。
- **头插路径**：**同理，`x` 在链头，第一个被检查，立即返回 `x`** ✅。

**这里用到了 `key_equiv` 的自反性**（`key_equiv(k, k)` 为真）——**这是客户端函数的隐含义务，讲义没有显式写进契约**。**若客户端的 `key_equiv` 不自反（比如写成「长度相等」——它是自反的；但若写成「不相等的字符串」就糟了），这条后置就证不出来。** **故 `key_equiv` 应当要求「等价关系」的三条性质**（自反、对称、传递）——**讲义未提，是本讲的一处遗漏。**

**头插 vs 尾插**：**代码用头插**（`p->next = H->table[i]; H->table[i] = p;`）——**`O(1)`，不需要遍历到链尾。** **代价是「同键的旧条目被埋在后面」**，**但反正会覆盖，无所谓。** **而「插入顺序」在链上是反的**——**这解释了为什么 `hdict_tabulate` 的输出顺序「in some order of your choice」**（习题 2）。

### 5.9 扩容：三个必须注意的坑

**习题 3 的解答（讲义 p20–22）分四步。**

**第一步：把阈值变成客户端可配的参数。**

```c0
hdict_t hdict_new(int capacity, int maxload)
/*@requires capacity > 0 && maxload > 0; @*/
/*@ensures \result != NULL; @*/ ;
```

**结构体加一个字段**：

```c0
struct hdict_header {
  int size;        // 0 <= size
  chain*[] table;  // \length(table) == capacity
  int capacity;    // 0 < capacity
  int maxload;     // 0 < maxload     ← ADDED
};
```

**讲义 p20 原文**：「This threshold, for example `2`, could be hard-coded inside the library implementation. **For applications that need careful ﬁne-tuning to achieve to performance, it is however best to let the client decide on what this threshold should be.**」

**为什么交给客户端**：**不同应用的「时间—空间偏好」不同**。**内存紧张的应用想 `maxload = 0.5`；速度优先的应用想 `maxload = 4`。** **库不该替客户端做这个决定。**

**第二步：用乘法判断阈值（不要用除法）。**

```c0
// 错误写法
if (H->size / H->capacity >= H->maxload) ...

// 正确写法
if (H->size >= H->capacity * H->maxload) ...
```

**为什么除法会错（讲义 p21 原文）**：

> **「The naive way to perform this test, by checking whether `H->size/H->capacity >= H->maxload`, **will may yield unexpected outcomes as `/` is integer division**. We are better off **multiplying both sides by `H->capacity`** (here we ignore possible overﬂow issues).」**

**具体例子**：`capacity = 10`、`maxload = 2`、`size = 19`。

- **除法版**：`19 / 10 = 1`（整数截断），`1 >= 2` **为假** → **不扩容。** **但 `α = 1.9 < 2`，确实还不该扩**——**这次碰巧对。**
- **再看 `size = 20`**：`20 / 10 = 2`，`2 >= 2` **为真** → **扩容** ✅。
- **但 `capacity = 10`、`maxload = 3`、`size = 29`**：`29/10 = 2`，`2 >= 3` **为假** → **不扩容** ✅（`α = 2.9 < 3`）。
- **`size = 30`**：`3 >= 3` **真** → 扩容 ✅。

**这个例子看起来都对……什么时候会错？** **当 `maxload` 不是整数时**——**但 `maxload` 声明为 `int`，故它是整数。** **故除法在 `maxload` 为整数时「恰好」正确？**

**不完全。** **问题在「截断方向」**：`size/capacity` **向下取整**。**故 `size/capacity >= maxload` 等价于 `size >= maxload * capacity`**——**在 `capacity > 0` 时这两者其实等价！** **（`floor(a/b) >= m ⟺ a >= m*b`，对正整数 `b`、`m` 成立。）**

**故讲义说的「will may yield unexpected outcomes」在 `maxload` 为 `int` 时其实不成立**——**除法与乘法在这里等价。** **但若 `maxload` 是 `real`（浮点），除法就会因精度出问题。** **讲义的警告更可能是「防御性编程」：乘法更直接地表达了「`size/capacity >= maxload`」的意图，且不受整数除法语义影响。**（**这是本讲的一处论证不严密，见第 8 节原文异常。**）

**讲义自己承认忽略了溢出**：「here we ignore possible overﬂow issues」。**`capacity * maxload` 若超过 `int_max()` 会回绕成负数**——**此时条件恒真，每次都扩容，直到 `capacity` 也溢出。** **严格的实现应加 `assert(H->capacity <= int_max() / H->maxload)`**（[[15-122-11-Unbounded-Arrays]] 的 `assert(A->limit <= int_max()/2)` 同款）。

**第三步：互递归 + 前向声明。**

```c0
void hdict_insert(hdict* H, entry x);   // forward declaration

void hdict_resize(hdict* H, int new_capacity)
//@requires is_hdict(H);
//@ensures is_hdict(H);
{
  int old_capacity = H->capacity;
  chain*[] old_table = H->table;
  H->capacity = new_capacity;
  H->table = alloc_array(chain*, H->capacity);
  H->size = 0;
  for (int i = 0; i < old_capacity; i++) {
    for (chain* p = old_table[i]; p != NULL; p = p->next) {
      hdict_insert(H, p->data);
    }
  }
}
```

**为什么需要前向声明（讲义 p22 原文）**：

> **「Note that `hdict_insert` calls `hdict_resize` and `hdict_resize` calls `hdict_insert`: **these two functions are mutually recursive**. Were we to simply place either one before the other, **the code would fail to compile**. We notify the compiler that a function will be deﬁned after its ﬁrst use in a ﬁle by means of a **forward declaration**.」**

**为什么「放前面」解决不了**：**C0（与 C）要求「调用前必须已声明」。** **`insert` 要调 `resize`（`resize` 得在前），`resize` 要调 `insert`（`insert` 得在前）**——**死循环。** **前向声明打破循环：`insert` 的原型放在 `resize` 之前，`resize` 的定义放在 `insert` 之前，`insert` 的完整定义放在最后。**

**为什么「不会级联扩容」（讲义 p21）**：

> **「Because the new table is **bigger** than the old table, we will not trigger cascaded resizings.」**

**论证**：`new_capacity = 2 * capacity`，**故 `size < capacity * maxload <= new_capacity * maxload`**——**新表的装载因子更小，不满足扩容条件** ✅。**若 `new_capacity` 比旧表小（缩容），就可能触发「缩了又扩」的循环**——**故缩容时必须保证新表的 `α` 不超标**（见 5.10 的四分之一阈值）。

**第四步：为什么不能「用 `hdict_new` 重定义 `H`」。**

**讲义 p22 原文**：

> **「One approach to writing `hdict_resize` that does not work is to redeﬁne the hash table `H` through a call to `hdict_new`. **This does not work because this changes the value contained in the variable `H` to a new address. But this new address is not shared with the caller of `hdict_resize`, here `hdict_insert`, which would never see the resized table** (unless `hdict_resize` were to return it).」**

**这是「按值传递指针」的经典陷阱**（[[15-122-08-Libraries]]、[[15-122-10-Linked-Lists]] 反复出现）：

```c0
void hdict_resize(hdict* H, int new_capacity) {
  H = hdict_new(new_capacity);   // ❌ 只改了局部变量 H
  // caller 的 H 仍指向旧表
}
```

**`H` 是「指向 `hdict_header` 的指针」，按值传递。** **`H = ...` 只改局部副本。** **故必须「原地修改 `*H` 的字段」**：

```c0
H->capacity = new_capacity;      // ✅ 改的是 *H
H->table = alloc_array(...);     // ✅
H->size = 0;                     // ✅
```

**这与 [[15-122-11-Unbounded-Arrays]] 的 `uba_resize` 完全同款**——**那里也是 `A->data = B;`（改字段），而不是 `A = 新数组`。**

**摊还代价**：**`hdict_resize` 是 `O(old_capacity + size)`**（分配新数组 + 重新插入每个条目）。**因为翻倍，摊到 `capacity` 次插入上，每次 `O(1)`。** **故 `hdict_insert` 是「摊还平均 `O(1)`」。** **但接口只写了 `/* O(1) avg. */`**——**漏了「摊还」二字**（见第 8 节原文异常）。

**为什么扩容必须「重新插入」而不是「复制」**：

**因为 `index_of_key` 依赖 `H->capacity`**：

```
i_old = abs(key_hash(k) % old_capacity)
i_new = abs(key_hash(k) % new_capacity)
```

**`old_capacity != new_capacity` 时 `i_old` 与 `i_new` 通常不同。** **故不能「整条链搬过去」**——**必须逐个条目重算下标、重新挂链。** **这正是讲义 p17 习题 3 的提示**：

> **「When doubling the size of the hash table you will need to **explicitly insert every entry from the old hash table into the new one**, because **the result of hashing depends on the size of the hash table**.」**

**代价**：**`O(n)` 次哈希计算 + `O(n)` 次插入**——**比无界数组的「`O(n)` 次复制」更贵**（哈希计算可能不便宜）。**但摊还后仍是 `O(1)`。**

### 5.10 删除：`prev` 指针技巧与一个真实的 bug

**习题 5 的接口（讲义 p23）**：

```c0
void hdict_delete(hdict_t H, key k)
/*@requires H != NULL; @*/
/*@ensures hdict_lookup(H, k) == NULL; @*/ ;
```

**后置条件很干脆**：**「删完之后查不到」。**

**第一个陷阱：`p = p->next` 不会修改链（讲义 p23 原文）**：

> **「It is tempting to loop through the chain where `k` belong (at index `i` of the hash table) using a pointer `p` and, once we ﬁnd `k`, simply set `p` to `p->next`. **This doesn't work however: `p` is an alias of the pointer in the chain, and modifying it does not change the pointer in the chain.**」**

**为什么**：`p` 是**局部变量**，**它的值（一个地址）与「链上某个 `next` 字段的值」是两个独立的内存单元。** **`p = p->next` 只改了 `p` 这个局部格子**——**链上那个 `next` 字段纹丝不动。**

**必须改「指针本身」，不是「指针的副本」**：

- **删第一个节点**：改 `H->table[i]`。
- **删后面的节点**：改 `prev->next`。

**第二个陷阱：头节点是特例（讲义 p23 原文）**：

> **「to update the ﬁrst pointer in the chain, we need to update `H->table[i]` ... For any other pointer, we need to update the `next` field of a node in the chain. ... Handling the ﬁrst node as a special case in this way would lead to (some) code repetition and likely bugs.」**

**解法：维护 `prev` 指针**（讲义 p23 原文）：

> **「A better way to implement the above idea is to **maintain a pointer `prev` to the node before the node we are currently examining**. We set `prev` to `NULL` for the previous node of the ﬁrst node of the chain.」**

**关键设计**：**`prev == NULL` 就代表「当前是头节点」**——**用一个哨兵值统一了两种情形。**

**讲义的实现（p23–24）**：

```c0
void hdict_delete(hdict* H, key k)
//@requires is_hdict(H);
//@ensures hdict_lookup(H, k) == NULL;
//@ensures is_hdict(H);
{
  int i = index_of_key(H, k);
  chain* prev = NULL;
  bool done = false;
  for (chain* p = H->table[i]; p != NULL && !done; p = p->next) {
    if (key_equiv(k, entry_key(p->data))) {
      if (prev == NULL)
        H->table[i] = p->next;
      else {
        prev->next = p->next;
        (H->size)--;
        done = true;
      }
    }
    prev = p;
  }
  if (H->size <= (H->capacity * H->maxload) / 4)
    hdict_resize(H, H->capacity/2 > 0 ? H->capacity/2 : 1);
}
```

**⚠️ 这段代码有一个真实的 bug**（**讲义未指出，见第 8 节原文异常**）：**`(H->size)--` 与 `done = true;` 都在 `else` 分支里**——**故「删除头节点」时 `size` 不减、`done` 不置真。**

**后果**：

1. **`size` 比实际条目数多 1** → **`is_hdict` 的「条目数 == `size`」被违反**（虽然那条不变式讲义没写进代码，故 `cc0 -d` 抓不到）。
2. **`done` 保持 `false`** → **循环继续**，`prev = p`（**已删除的节点**），`p = p->next`（**原第二个节点**）。**若链上还有另一个同键条目（理论上不该有），它会走 `else` 分支写 `prev->next`——但 `prev` 已不可达，写入丢失。** **故「静默失败」。**
3. **`size` 偏大还会影响后续扩容判断**：`size` 虚高 → **更早触发扩容 → 浪费内存**。

**修法**：把 `(H->size)--; done = true;` 移到 `if/else` **之外**：

```c0
if (key_equiv(k, entry_key(p->data))) {
  if (prev == NULL)
    H->table[i] = p->next;
  else
    prev->next = p->next;
  (H->size)--;        // ← 移到外面
  done = true;        // ← 移到外面
}
```

**这个 bug 是「教学代码」的典型风险**：**逻辑看起来对称，但花括号的位置错了。** **而由于 `is_hdict` 不完整，编译器抓不到。** **若把「条目数 == `size`」写进 `is_hdict`，`cc0 -d` 立刻会在下一次 `hdict_insert`/`hdict_delete` 的入口报错。**

**缩容的两行（讲义 p24 原文）**：

> **「The last two lines take care of resizing the table. **As for unbounded arrays, we resize the table when it is less than a quarter "full"**. Here, our notion of "full" is when it becomes a quarter of the maximum load factor, `H->maxload`, we conﬁgured the hash table with. ... **the table capacity should never be zero.** We do so by using the ternary operator `H->capacity/2 > 0 ? H->capacity/2 : 1`.」**

**为什么四分之一**：**与 [[15-122-11-Unbounded-Arrays]] 5.8 完全同构**——**半满缩容会抖动**（`rem` 触发缩容、`add` 立刻触发扩容，`O(n²)`）。**四分之一留出缓冲带。**

**为什么容量不能为 0**：**`capacity = 0` 时 `index_of_key` 里的 `% H->capacity` 会除零崩溃**，且 `is_hdict` 的 `0 < capacity` 失败。**故用三元式保底为 1。**

**注意这里缩容的判据用 `/ 4`（除法）而非乘法**——**与扩容判据的乘法写法不一致**。**这在整数下是等价的（`size <= capacity*maxload/4`），但风格不统一。**

### 5.11 哈希集合：三步特化

**定义（讲义 p14–15 原文）**：

> **「A set is a collection of elements **without duplicates**. ... we can think of **a set as a dictionary where both keys and entries are the elements**.」**

**三个简化步骤（讲义 p15 原文）**：

| 步骤 | 原文 | 后果 |
|---|---|---|
| 1 | **「We collapse the types `key` and `entry` into a single type that we call `elem`.」** | **`key` 与 `entry` 合并** |
| 2 | **「Extracting a key from an entry becomes vacuous. Consequently we can **do without an `entry_key` function**.」** | **少一个客户端函数** |
| 3 | **「The lookup function of dictionaries underlies a membership test: it returns `NULL` if the element is not in the set, and the element itself if it is. We can streamline this behavior by having the hash set version, which we call `hset_contains`, **return a boolean**. This also lets us **do without the requirement that the data contained in the hash table be a pointer type: `elem` can be any type**.」** | **`elem` 不必是指针** |

**第 3 步的因果链值得拆开**：

```
hset_contains 返回 bool
    ↓ 不需要用 NULL 表示「不存在」
    ↓ 不需要哨兵值
elem 可以不是指针（可以是 int、char、bool…）
```

**这解释了 5.1 结尾的那个对比**：**「`entry` 必须是指针」不是因为「哈希表要求指针」，而是因为「`hdict_lookup` 用 `NULL` 表示缺失」。** **换成 `bool` 返回值，约束就消失了。**

**接口（讲义 p15–16）**：

```c0
/************************/
/*** Client interface ***/
/************************/
// typedef _______ elem;          // 客户端提供（任意类型）
bool elem_equiv(elem x, elem y);  // 客户端提供
int  elem_hash(elem x);           // 客户端提供

/*************************/
/*** Library interface ***/
/*************************/
// typedef ______* hset_t;
hset_t hset_new(int capacity)
/* O(1) */
/*@requires capacity > 0; @*/
/*@ensures \result != NULL; @*/ ;
bool hset_contains(hset_t H, elem x)
/* O(1) avg. */
/*@requires H != NULL; @*/ ;
void hset_add(hset_t H, elem x)
/* O(1) avg. */
/*@requires H != NULL; @*/
/*@ensures hset_contains(H, x); @*/ ;
```

**客户端函数从三个降到两个**——**`entry_key` 消失了**（步骤 2）。

**`hset_add` 的后置条件 `hset_contains(H, x)`**：**「加进去之后一定查得到」**——**与 `hdict_insert` 的 `hdict_lookup(H, entry_key(x)) == x` 完全同构，只是省掉了 `entry_key`。**

**实现（讲义 p26–27）**：

```c0
bool hset_contains(hset* H, elem x)
//@requires is_hset(H);
{
  int i = index_of_elem(H, x);
  for (chain* p = H->table[i]; p != NULL; p = p->next) {
    if (elem_equiv(p->data, x))
      return true;
  }
  return false;
}

void hset_add(hset* H, elem x)
//@requires is_hset(H);
//@ensures is_hset(H);
//@ensures hset_contains(H, x);
{
  int i = index_of_elem(H, x);
  for (chain* p = H->table[i]; p != NULL; p = p->next) {
    if (elem_equiv(p->data, x)) {
      p->data = x;
      return;
    }
  }
  // prepend new element
  chain* p = alloc(chain);
  p->data = x;
  p->next = H->table[i];
  H->table[i] = p;
  (H->size)++;
}
```

**与 `hdict_insert` 的唯一差别**：**`elem_equiv(p->data, x)` 而不是 `key_equiv(entry_key(p->data), k)`**——**因为 `elem` 就是键。**

**`is_hset` 也简化了（讲义 p26 原文）**：

> **「This means that the data representation function `is_hset` (not shown) does not need to check that the chain node have non-`NULL` data ﬁelds.」**

**因为 `elem` 可以是 `int`，「非 `NULL`」这个概念不适用。** **故 5.7 表格里的第 1 条不变式在集合里消失了。**

**注意 `hset_add` 的「覆盖」分支**：`p->data = x; return;`——**看起来多余**（既然 `elem_equiv` 为真，`p->data` 与 `x` 「相等」，为什么要覆盖？）。**理由**：**`elem_equiv` 是「客户端定义的等价」，可能比「完全相同」更粗**（比如「学号相同即等价」）。**故覆盖保证了「字典里存的是最新的那个代表」。** **这与 `hdict_insert` 的 `p->data = x;` 同款。**

### 5.12 四种变体：接口的不同画法

**习题 1、4、6 展示了「同一功能、不同接口」的三种变体。**

**变体 A（本讲主设计）：键嵌在条目里。**

```
entry_key : entry → key
```

**适用**：**键本来就是数据的一部分**（学生记录里有学号、词频记录里有单词）。**讲义 p2 的术语区分**：**这种叫 `entry`**。

**变体 B（习题 6）：键与值分离。**

```c0
/******************** Client interface *********************/
// typedef _______ key;
// typedef _______ *value;
bool key_equiv(key x, key y);
int  key_hash(key x);
/******************** Library interface ********************/
// typedef ______* hdict_t;
value hdict_lookup(hdict_t H, key k);
void hdict_insert(hdict_t H, key k, value v)
/*@requires H != NULL; @*/
/*@requires v != NULL; @*/
/*@ensures hdict_lookup(H, k) == v; @*/ ;
```

**链节点（讲义 p25）**：

```c0
struct chain_node {
  key   key;      // ← 键单独存
  value value;    // ← 值单独存（!= NULL）
  chain* next;
};
```

**适用**：**值里不含键**（比如「日期 → 平均气温」）。**讲义 p2 的术语**：**这种叫 `value`。**

**代价**：**`hdict_insert` 变成三参数**；**`lookup` 直接返回 `value`（不再需要 `entry_key`）**；**`entry` 类型整个消失。**

**变体 C（习题 4）：把取模交给客户端。**

```c0
int key_hash(key k, int m)
/*@requires m > 0; @*/
/*@ensures 0 <= \result && \result < m; @*/ ;
```

**适用**：**客户端的哈希函数需要知道表大小**（比如「一致性哈希」、或者「用 `m` 做二次混合」）。

**代价**：**客户端契约更重**（要保证 `< m`）；**`index_of_key` 退化成一行**。

**变体 D（哈希集合）：键 = 值。**

**适用**：**只要「在不在」**（去重、成员测试）。

**四变体的对照表**：

| | 客户端类型 | 客户端函数 | `hdict_insert` 参数 | 缺失信号 |
|---|---|---|---|---|
| **A（主设计）** | `entry`（指针）、`key` | `entry_key`、`key_hash`、`key_equiv` | `(H, entry x)` | `NULL` entry |
| **B（键值分离）** | `key`、`value`（指针） | `key_hash`、`key_equiv` | `(H, key k, value v)` | `NULL` value |
| **C（传 `m`）** | 同 A | `entry_key`、`key_hash(k,m)`、`key_equiv` | 同 A | 同 A |
| **D（集合）** | `elem`（任意） | `elem_hash`、`elem_equiv` | `(H, elem x)` | **无（返回 `bool`）** |

**这张表说明了「接口设计」的核心权衡**：

- **要「按键取值」→ 必须有 `key` 与 `value` 的区分**（A 或 B）。
- **要「值可以为任意类型」→ 不能靠 `NULL` 表示缺失 → 必须用 `bool` 或额外查询**（D）。
- **要「客户端控制取模」→ 契约更重**（C）。

**没有一个变体「更好」——只有「更适合某个用途」。** **这就是「关注点分离」的最终目的：让不同的用途有不同的接口，而不是让一个接口试图服务所有用途。**

## 6. 代码示例

### 6.1 官方课程代码

以下引自讲义 PDF `13-hdict.pdf`，语言为 **C0**（不是标准 C/C++）。`//@` 注解、`\length`、`\result`、`alloc`、`alloc_array`、`_______` 占位都是 C0 特有语法。

**（1）泛型队列的客户端接口与库接口，第 2–3 页：**

```c0
/*** Client interface ***/
// typedef _______ elem;
// Supplied by client

/*** Library interface ***/
// typedef ______* queue_t;
bool queue_empty(queue_t Q)
/* O(1) */
/*@requires Q != NULL; @*/;
queue_t queue_new()
/* O(1) */
/*@ensures \result != NULL; @*/;
void enq(queue_t Q, elem x)
/* O(1) */
/*@requires Q != NULL; @*/;
elem deq(queue_t Q)
/* O(1) */
/*@requires Q != NULL && !queue_empty(Q); @*/ ;
```

**编译命令（第 3 页）：**

```
% cc0 queue-client.c0 queue.c0 main.c0
```

**（2）哈希字典的完整接口，第 5–6 页：**

```c0
/************************/
/*** Client interface ***/
/************************/
// typedef ______* entry;
// Supplied by client
// typedef _______
key;
// Supplied by client

key
entry_key(entry x)
// Supplied by client
/*@requires x != NULL; @*/ ;

int
key_hash(key k);
// Supplied by client

bool key_equiv(key k1, key k2);
// Supplied by client

/*************************/
/*** Library interface ***/
/*************************/
// typedef ______* hdict_t;

hdict_t hdict_new(int capacity)
/*@requires capacity > 0; @*/
/*@ensures \result != NULL; @*/ ;

entry hdict_lookup(hdict_t H, key k)
/*@requires H != NULL; @*/
/*@ensures \result == NULL
|| key_equiv(entry_key(\result), k); @*/ ;

void hdict_insert(hdict_t H, entry x)
/*@requires H != NULL && x != NULL; @*/
/*@ensures hdict_lookup(H, entry_key(x)) == x; @*/ ;
```

**（3）小客户端：词频统计，第 7 页：**

```c0
/******************************/
/* client-side implementation */
/******************************/
struct wcount {
  string word;   // key
  int count;     // other data
};

// Fulfilling the client interface
typedef struct wcount* entry;
typedef string key;

key entry_key(entry x)
//@requires x != NULL;
{
  return x->word;
}

int key_hash(key k) {
  return hash_string(k);
  /* defined below */
}

bool key_equiv(key k1, key k2) {
  return string_equal(k1, k2);
}
```

**（4）字符串哈希的骨架，第 8 页：**

```c0
int hash_string(string s) {
  int len = string_length(s);
  int h = 0;
  for (int i = 0; i < len; i++)
  //@loop_invariant 0 <= i;
  {
    int ch = char_ord(string_charat(s, i));
    // Do something to combine h and ch
  }
  return h;
}
```

**（5）三个递进的组合方式，第 8–10 页：**

```c0
// 版本 2：加法（变位词全冲突）
h = h + ch;

// 版本 3：多项式滚动（Java 采用）
h = 31*h;
h = h + ch;

// 版本 4：随机乘数
rand_t r = init_rand(0x1337BEEF);
h = rand(r) * h;
h = h + ch;

// 版本 5：每步 LCG 步进
h = 1664525 * h + 1013904223;
h = h + ch;
```

**（6）链与字典的类型定义，第 12 页：**

```c0
/*******************************/
/* library-side implementation */
/*******************************/
typedef struct chain_node chain;
struct chain_node {
  entry data;      // != NULL
  chain* next;
};

typedef struct hdict_header hdict;
struct hdict_header {
  int size;        // 0 <= size
  int capacity;    // 0 < capacity
  chain*[] table;  // \length(table) == capacity
};
```

**（7）`is_hdict`（讲义明确标注「incomplete」），第 12–13 页：**

```c0
bool is_hdict(hdict* H) {
  return H != NULL
      && 0 <= H->size
      && 0 < H->capacity
      && is_array_expected_length(H->table, H->capacity);
  /* && there are no NULL entries */
  /* && each entry satisfies its own representation invariants */
  /* && there aren't entries with equal key */
  /* && the number of entries matches the size */
  /* && every entry in H->table[i] hashes to i */
  /* && ... */
}
```

**（8）`index_of_key`、`hdict_new`，第 13 页：**

```c0
int index_of_key(hdict* H, key k)
//@requires is_hdict(H);
//@ensures 0 <= \result && \result < H->capacity;
{
  return abs(key_hash(k) % H->capacity);
}

hdict* hdict_new(int capacity)
//@requires capacity > 0;
//@ensures is_hdict(\result);
{
  hdict* H = alloc(hdict);
  H->size = 0;
  H->capacity = capacity;
  H->table = alloc_array(chain*, capacity);
  return H;
}
```

**（9）`hdict_lookup`，第 13–14 页：**

```c0
entry hdict_lookup(hdict* H, key k)
//@requires is_hdict(H);
//@ensures \result == NULL || key_equiv(entry_key(\result), k);
{
  int i = index_of_key(H, k);
  for (chain* p = H->table[i]; p != NULL; p = p->next) {
    if (key_equiv(entry_key(p->data), k))
      return p->data;
  }
  return NULL;
}
```

**（10）`hdict_insert`，第 14 页：**

```c0
void hdict_insert(hdict* H, entry x)
//@requires is_hdict(H);
//@requires x != NULL;
//@ensures is_hdict(H);
//@ensures x == hdict_lookup(H, entry_key(x));
{
  key k = entry_key(x);
  int i = index_of_key(H, k);
  for (chain* p = H->table[i]; p != NULL; p = p->next) {
    //@assert p->data != NULL;   // Not given by loop invariant!
    if (key_equiv(entry_key(p->data), k)) {
      p->data = x;
      return;
    }
  }
  // prepend new entry
  chain* p = alloc(chain);
  p->data = x;
  p->next = H->table[i];
  H->table[i] = p;
  (H->size)++;
}
```

**（11）哈希集合的接口，第 15–16 页：**

```c0
/************************/
/*** Client interface ***/
/************************/
// typedef _______ elem;
// Supplied by client
bool elem_equiv(elem x, elem y);
// Supplied by client
int elem_hash(elem x);
// Supplied by client

/*************************/
/*** Library interface ***/
/*************************/
// typedef ______* hset_t;

hset_t hset_new(int capacity)
/* O(1) */
/*@requires capacity > 0; @*/
/*@ensures \result != NULL; @*/ ;

bool hset_contains(hset_t H, elem x)
/* O(1) avg. */
/*@requires H != NULL; @*/ ;

void hset_add(hset_t H, elem x)
/* O(1) avg. */
/*@requires H != NULL; @*/
/*@ensures hset_contains(H, x); @*/ ;
```

**（12）扩容版的 `hdict_insert` 与 `hdict_resize`（习题 3 答案），第 21–22 页：**

```c0
// Change to the library interface
hdict_t hdict_new(int capacity, int maxload)     // EXTENDED
/*@requires capacity > 0 && maxload > 0; @*/    // EXTENDED
/*@ensures \result != NULL; @*/ ;

struct hdict_header {
  int size;        // 0 <= size
  chain*[] table;  // \length(table) == capacity
  int capacity;    // 0 < capacity
  int maxload;     // 0 < maxload    // ADDED
};

void hdict_insert(hdict* H, entry x) {
  ...
  // Resize
  if (H->size >= H->capacity * H->maxload)
    hdict_resize(H, 2 * H->capacity);
}

void hdict_insert(hdict* H, entry x);   // forward declaration

void hdict_resize(hdict* H, int new_capacity)
//@requires is_hdict(H);
//@ensures is_hdict(H);
{
  int old_capacity = H->capacity;
  chain*[] old_table = H->table;
  H->capacity = new_capacity;
  H->table = alloc_array(chain*, H->capacity);
  H->size = 0;
  for (int i = 0; i < old_capacity; i++) {
    for (chain* p = old_table[i]; p != NULL; p = p->next) {
      hdict_insert(H, p->data);
    }
  }
}
```

**（13）删除（习题 5 答案），第 23–24 页：**

```c0
void hdict_delete(hdict* H, key k)
//@requires is_hdict(H);
//@ensures hdict_lookup(H, k) == NULL;
//@ensures is_hdict(H);
{
  int i = index_of_key(H, k);
  chain* prev = NULL;
  bool done = false;
  for (chain* p = H->table[i]; p != NULL && !done; p = p->next) {
    if (key_equiv(k, entry_key(p->data))) {
      if (prev == NULL)
        H->table[i] = p->next;
      else {
        prev->next = p->next;
        (H->size)--;
        done = true;
      }
    }
    prev = p;
  }
  if (H->size <= (H->capacity * H->maxload) / 4)
    hdict_resize(H, H->capacity/2 > 0 ? H->capacity/2 : 1);
}
```

**（14）键值分离版（习题 6 答案），第 25–26 页：**

```c0
struct chain_node {
  key   key;
  value value;     // value != NULL
  chain* next;
};

value hdict_lookup(hdict* H, key k)
//@requires is_hdict(H);
{
  int i = index_of_key(H, k);
  for (chain* p = H->table[i]; p != NULL; p = p->next) {
    if (key_equiv(p->key, k)) {
      return p->value;
    }
  }
  return NULL;
}

void hdict_insert(hdict* H, key k, value v)
//@requires is_hdict(H);
//@requires v != NULL;
//@ensures is_hdict(H);
//@ensures hdict_lookup(H, k) == v;
{
  int i = index_of_key(H, k);
  for (chain* p = H->table[i]; p != NULL; p = p->next) {
    if (key_equiv(p->key, k)) {
      p->value = v;      // Override previous value for given key
      return;
    }
  }
  // prepend new entry
  chain* p = alloc(chain);
  p->key = k;
  p->value = v;
  p->next = H->table[i];
  H->table[i] = p;
  (H->size)++;
}
```

**（15）哈希集合的实现（习题 7 答案），第 26–27 页：**

```c0
struct chain_node {
  elem data;
  chain* next;
};

bool hset_contains(hset* H, elem x)
//@requires is_hset(H);
{
  int i = index_of_elem(H, x);
  for (chain* p = H->table[i]; p != NULL; p = p->next) {
    if (elem_equiv(p->data, x))
      return true;
  }
  return false;
}

void hset_add(hset* H, elem x)
//@requires is_hset(H);
//@ensures is_hset(H);
//@ensures hset_contains(H, x);
{
  int i = index_of_elem(H, x);
  for (chain* p = H->table[i]; p != NULL; p = p->next) {
    if (elem_equiv(p->data, x)) {
      p->data = x;
      return;
    }
  }
  // prepend new element
  chain* p = alloc(chain);
  p->data = x;
  p->next = H->table[i];
  H->table[i] = p;
  (H->size)++;
}
```

**（16）学生记录（习题 1 答案），第 19 页：**

```c0
struct student_record {
  int student_id;
  char[] grades;
  string notes;
  bool auditor;
};
typedef struct student_record* entry;
typedef int key;

key entry_key(entry x)
//@requires x != NULL;
{
  return x->student_id;
}

int key_hash(key k) {
  return hash_int(k);
}

bool key_equiv(key k1, key k2) {
  return k1 == k2;
}
```

**官方代码包**：`90-原始PDF/15-122/code/13-hdict.tgz`（原始 URL：`https://cs.cmu.edu/~15122/handouts/code/13-hdict.tgz`）。

### 6.2 Agent 自行编写的教学示例

> **非官方，仅用于说明概念。** 以下由本笔记自行编写，不是 CMU 官方代码。

**示例 A：`h = h + ch` 与 `h = 31*h + ch` 的碰撞对照（小规模可手算）。**

用三个字母、字符值取 `'a'=1, 'b'=2, 'c'=3`（简化，真实 ASCII 是 97/98/99），`m = 13`。

| 字符串 | `h + ch` | `% 13` | `31h+ch` | `% 13` |
|---|---|---|---|---|
| `abc` | `1+2+3 = 6` | **6** | `(1*31+2)*31+3 = 1026` | `1026 - 78*13 = 1026-1014 = 12` |
| `acb` | `6` | **6** ← 碰撞 | `(1*31+3)*31+2 = 1056` | `1056-1014 = 42-39 = 3` |
| `bac` | `6` | **6** ← 碰撞 | `(2*31+1)*31+3 = 1956` | `1956 - 150*13 = 1956-1950 = 6` |
| `bca` | `6` | **6** ← 碰撞 | `(2*31+3)*31+1 = 2016` | `2016-2010 = 6` ← **碰撞！** |
| `cab` | `6` | **6** ← 碰撞 | `(3*31+1)*31+2 = 2916` | `2916-2912 = 4` |
| `cba` | `6` | **6** ← 碰撞 | `(3*31+2)*31+1 = 2976` | `2976-2964 = 12` ← **碰撞！** |

**结果对比**：

- **`h + ch`**：**六个全在槽位 6。** **100% 碰撞率**（六个变位词）。
- **`31h + ch`**：**落在槽位 `{12, 3, 6, 6, 4, 12}`**——**六条链里只有 4 个不同槽位，两对碰撞。**

**为什么 `31h+ch` 还有碰撞**：**因为 `m = 13` 太小**（只有 13 个槽位装 6 个值，按生日悖论冲突概率 `1 - exp(-30/26) ≈ 68%`）。**但关键是：碰撞是「随机的、分散的」，而不是「全部挤在一处」。**

**这就是「好哈希」与「坏哈希」的本质差别**：**不是「有没有碰撞」（必然有），而是「碰撞是否结构化」。** **`h + ch` 的碰撞是 100% 可预测的**（任何变位词组必然全撞），**`31h+ch` 的碰撞是概率性的。**

**示例 B：Coherence 违反的三种组合，逐一推演后果。**

设键是字符串，字典里已插入 `"apple"`（`key_hash("apple") = 7`，`m = 10`）。

| `key_equiv` | `key_hash` | Coherence？ | 查 `"amlet"`（长度 5）的结果 |
|---|---|---|---|
| `string_equal` | `hash_string`（好） | ✅ | **正确返回 `NULL`**（若 `hash("amlet")=3`，槽位 3 上没有 `"amlet"`） |
| **`string_length` 相等** | `hash_string`（好） | ❌ | **若 `hash("amlet") == 7`（碰撞），返回 `"apple"` 的条目 → 错误！** |
| `string_equal` | **首字母 ASCII** | ✅（但失衡） | **正确返回 `NULL`**，但**所有 `'a'` 开头的词都在槽位 97 上** |

**第二行的详细推演**：

1. `index_of_key(H, "amlet")` = `hash("amlet") % 10`。**假设是 7**（碰撞）。
2. 走到 `H->table[7]`，**链上有 `"apple"` 的条目**。
3. `key_equiv(entry_key(p->data), "amlet")` = `key_equiv("apple", "amlet")` = **`string_length("apple") == string_length("amlet")`** = `5 == 5` = **`true`**。
4. **`return p->data;`**——**返回 `"apple"` 的词频记录。**

**后置条件 `\result == NULL || key_equiv(entry_key(\result), k)` 满足吗？** **满足！** **因为 `key_equiv("apple","amlet")` 确实为真。** **故验证器不会报错——这是一个「契约无法捕捉」的 bug。**

**这是最深刻的教训**：**`key_equiv` 的定义本身就是「什么是相等的键」。** **若它定得太粗，所有基于它的推理都「自洽但错误」。** **契约只能保证「实现符合规格」，不能保证「规格符合意图」。**

**第三行的推演**：`hash("amlet") = char_ord('a') = 97`，`97 % 10 = 7`。**故 `"amlet"` 与 `"apple"` 恰好同槽（都以 `'a'` 开头）。** 但 `key_equiv` 是严格的，**故逐个比字符串，`"apple" != "amlet"`，继续走，走到链尾返回 `NULL`** ✅ **正确。**

**代价**：**所有 `'a'` 开头的词（可能占词汇表 5–10%）都在槽位 7 上。** **45600 词、约 3000 个 `'a'` 开头 → 链长 3000。** **查任何 `'a'` 开头的词要走 3000 步。** **这就是「正确但不可用」。**

**示例 C：扩容的摊还账本（`maxload = 2`）。**

从 `capacity = 4`、`size = 0` 开始连续插入：

| 插入第 `n` 个 | `capacity` | `size` | `size >= capacity*2`？ | 本次代价 | 累计 |
|---|---|---|---|---|---|
| 1 | 4 | 1 | `1 >= 8` 否 | 1 | 1 |
| 2 | 4 | 2 | 否 | 1 | 2 |
| 3 | 4 | 3 | 否 | 1 | 3 |
| 4 | 4 | 4 | 否 | 1 | 4 |
| 5 | 4 | 5 | 否 | 1 | 5 |
| 6 | 4 | 6 | 否 | 1 | 6 |
| 7 | 4 | 7 | 否 | 1 | 7 |
| **8** | 4 | **8** | **`8 >= 8` 是** → `capacity = 8` | `1 + 8`（重插 8 个）= **9** | **16** |
| 9 | 8 | 9 | `9 >= 16` 否 | 1 | 17 |
| ... | | | | | |
| **16** | 8 | **16** | **`16 >= 16` 是** → `capacity = 16` | `1 + 16` = **17** | **33** |
| ... | | | | | |
| **32** | 16 | **32** | **是** → `capacity = 32` | `1 + 32` = **33** | **65** |

**读法**：

- **第 `2^k` 次插入触发扩容**（`k >= 2`）。
- **累计代价**：`n = 8` 时 16；`n = 16` 时 33；`n = 32` 时 65。
- **`65 / 32 ≈ 2.03`**——**摊还代价趋近 2**（= `1`（每次插入）+ `1`（均摊的重插））。

**一般推导**：**`n` 次插入的总代价 `= n + Σ(扩容时的重插) = n + 8 + 16 + ... + n/2 < n + n = 2n`。** **故摊还 `< 2`，是 `O(1)`。** ✅

**注意 `maxload = 2` 意味着「扩容后 `α = 1`」**：**`capacity` 翻倍后 `size = capacity/2`，故 `α = 0.5`？** **不对——重算**：`capacity = 4` 扩到 `8` 时 `size = 8`，**`α = 8/8 = 1`** ✅。**再扩到 16 时 `size = 16`，`α = 16/16 = 1`** ✅。**故扩容后 `α` 恒为 1，涨到 2 时再扩。** **这与无界数组「扩容后半满」是同一个模式**（`α` 从 1 涨到 2，翻倍后回到 1）。

**示例 D：`prev` 指针删除的逐步追踪。**

链：`H->table[3] → [A] → [B] → [C] → NULL`，要删 `B`。

| 步 | `p` | `prev` | `done` | 动作 |
|---|---|---|---|---|
| 初 | `A` | `NULL` | `false` | — |
| 1 | `A` | `NULL` | `false` | `key_equiv(B, A)` 假；末尾 `prev = A` |
| 2 | `B` | `A` | `false` | `key_equiv(B, B)` **真**；`prev != NULL` → `prev->next = p->next`（即 `A->next = C`）✅；`size--`；`done = true`；末尾 `prev = B` |
| 3 | `C` | `B` | `true` | **循环条件 `!done` 为假 → 退出** |

**结果**：`H->table[3] → [A] → [C] → NULL` ✅ **`B` 已摘除。**

**现在删头节点 `A`**（链 `[A] → [C]`）：

| 步 | `p` | `prev` | `done` | 动作 |
|---|---|---|---|---|
| 初 | `A` | `NULL` | `false` | — |
| 1 | `A` | `NULL` | `false` | `key_equiv(A, A)` **真**；`prev == NULL` → `H->table[3] = p->next`（即 `= C`）✅；**`size` 未减！`done` 未置真！** |
| 2 | `C` | `A`（已删的节点） | `false` | `key_equiv(A, C)` 假；末尾 `prev = C` |
| 3 | `NULL` | `C` | `false` | 循环条件 `p != NULL` 假 → 退出 |

**结果**：**链结构正确**（`H->table[3] → [C] → NULL`）✅，**但 `size` 比实际多 1** ❌。

**这就是 5.10 说的 bug 的完整追踪。** **链结构对、`size` 错**——**而 `size` 错会累积**：**删 `k` 次头节点，`size` 就多 `k`。** **后果**：`is_hdict` 的「条目数 == `size`」失败（若写了那条），**且扩容判断用的是虚高的 `size`**。

**示例 E：哈希集合与哈希字典的接口差异（代码对照）。**

```c0
// 哈希字典：三个客户端函数
key  entry_key(entry x);          // entry → key
int  key_hash(key k);             // key → int
bool key_equiv(key k1, key k2);   // key × key → bool

// 哈希集合：两个客户端函数
int  elem_hash(elem x);           // elem → int
bool elem_equiv(elem x, elem y);  // elem × elem → bool
```

**查找循环的对照**：

```c0
// 字典
if (key_equiv(entry_key(p->data), k))
  return p->data;      // 返回 entry

// 集合
if (elem_equiv(p->data, x))
  return true;         // 返回 bool
```

**两处差异**：

1. **少了 `entry_key`**——**因为 `elem` 本身就是键**（`p->data` 直接就是「键」）。
2. **返回 `bool` 而不是 `elem`**——**故不需要 `NULL` 哨兵，故 `elem` 不必是指针。**

**类型约束的对照表**：

| | 字典（变体 A） | 集合（变体 D） |
|---|---|---|
| `entry` / `elem` 必须是指针？ | **是** | **否** |
| 原因 | `NULL` 表示「没找到」 | 返回 `bool`，无需哨兵 |
| 能否存 `int`？ | **不能**（要包成 `int*`） | **能** |
| `is_xxx` 要查「非 `NULL`」？ | **要** | **不要** |

**这张表是 5.11 第 3 步的完整展开**——**「接口的返回类型决定了数据类型的约束」。** **这是「接口设计」里最不直观、也最容易忽略的一条因果链。**

**示例 F：`hdict_tabulate` 的两个循环不变式（习题 2）。**

```c0
entry[] hdict_tabulate(hdict* H)
//@requires is_hdict(H);
//@ensures is_hdict(H) && \length(\result) == hdict_size(H);
{
  entry[] result = alloc_array(entry, H->size);
  int j = 0;
  for (int i = 0; i < H->capacity; i++)
  //@loop_invariant 0 <= i && i <= H->capacity;
  {
    for (chain* p = H->table[i]; p != NULL; p = p->next)
    //@loop_invariant 0 <= j && j <= H->size;
    {
      result[j] = p->data;
      j++;
    }
  }
  return result;
}
```

**两条不变式的分工**：

- **外层 `0 <= i && i <= H->capacity`**：**`i` 在合法下标范围**——**保证 `H->table[i]` 不越界。**
- **内层 `0 <= j && j <= H->size`**：**`j` 不超过输出数组长度**——**保证 `result[j]` 不越界。**

**够不够？** **外层不变式缺一条关键的耦合**：**「已经复制的条目数 == `j`」**。**因为后置条件要求 `\length(\result) == hdict_size(H)`，即「最终 `j` 等于 `size`」。**

**严格的不变式应写成**：

```
//@loop_invariant 0 <= i && i <= H->capacity;
//@loop_invariant 0 <= j && j <= H->size;
//@loop_invariant j == <前 i 条链上的条目总数>;
```

**第三条需要一个新的规格函数**（如 `chains_count(H, 0, i)`）——**讲义省略了它，故这个后置条件在 `cc0 -d` 下证不出来。**

**这是「不变式只需够用」的反面例子**：**5.7 说「多写无益」，但这里「少写就不够」。** **判断标准是「后置条件需要什么」**——**需要 `j == size`，就必须有能推出它的不变式。**

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键区别 | 记忆点 |
|---|---|---|---|
| `// typedef ______* hdict_t;` | `// typedef _______ elem;` | 前者**库提供**（客户端不知实现）；后者**客户端提供**（库不知实现） | 下划线在谁那边，谁就被隐藏 |
| 库的接口 | 库的实现 | 前者**客户端可依赖**；后者**可随时改** | 接口是合同 |
| `entry` | `key` | 前者是**存的东西**；后者是**从东西里取出的标识** | `entry_key` 连接两者 |
| `entry` 必须是指针 | `elem` 可以是任意类型 | 前者因为**用 `NULL` 表示缺失**；后者因为**返回 `bool`** | 返回类型决定类型约束 |
| `key_hash` 返回任意 `int` | `index_of_key` 返回 `[0, capacity)` | 前者**不知道 `m`**；后者**由库取模** | 取模是库的责任 |
| Coherence 违反 | 分布不均 | 前者**正确性错**；后者**只是慢** | 一个致命，一个可忍 |
| `key_equiv` 太粗 | `key_hash` 太粗 | 前者**返回错条目**；后者**链太长** | 见 5.4 |
| `h = h + ch` | `h = 31*h + ch` | 前者**加法可交换 → 变位词全撞**；后者**位置有权重** | 最长链 176 vs 10 |
| 「空链多」 | 「最长链长」 | 前者说明**分布不均**；后者说明**真的会慢** | 看最长链 |
| `is_hdict` 讲义版 | 完整版 | 前者**只有 3 条**；后者**至少 10 条** | 讲义自己标了 incomplete |
| `//@assert p->data != NULL;` | 循环不变式 | 前者是**局部补丁**；后者应**由 `is_hdict` 提供** | 「Not given by loop invariant!」 |
| 扩容「复制」 | 扩容「重新插入」 | 前者**下标不变才可行**；哈希表**下标会变** | 必须重算哈希 |
| `size >= capacity * maxload` | `size / capacity >= maxload` | 前者**不受整数除法影响**；后者**截断** | 乘法更安全 |
| 前向声明 | `#include` | 前者**只声明原型**；后者**拼接整个文件** | C0 只有前者 |
| `H->table = ...` | `H = hdict_new(...)` | 前者**改 `*H` 的字段**（caller 可见）；后者**只改局部指针** | 按值传递陷阱 |
| `prev == NULL` | `prev != NULL` | 前者表示**当前是头节点**（改 `H->table[i]`）；后者改 `prev->next` | 哨兵统一两情形 |
| `p = p->next` | `prev->next = p->next` | 前者**只改局部变量**；后者**改链上的字段** | 别名 vs 本体 |
| 哈希字典 | 哈希集合 | 前者**键 ≠ 条目**；后者**键 = 条目** | 集合是字典的特化 |
| `maxload` 硬编码 | `maxload` 客户端可配 | 前者简单；后者**让客户端决定时间—空间偏好** | 交给客户端 |
| 四分之一缩容 | 半满缩容 | 前者**有缓冲带**；后者**抖动 `O(n²)`** | 同 [[15-122-11-Unbounded-Arrays]] |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-122/lectures/13-hdict.pdf`
- **讲义标题**：PDF 内页标题为 **"Lecture 13: Hash Dictionaries"**，作者 Frank Pfenning、Rob Simmons、Iliano Cervesato。
- **总页数**：27 页
- **本节重点页码**（PDF 页码，即提取文本中 `=== [page N] ===` 的 N）：
  - 第 1 页：开篇；**关注点分离（separation of concerns）**；接口 = **类型 + 操作 + 前后置条件 + 渐进复杂度**；**新问题：库可能需要客户端提供操作**；哈希表是最佳例子；**「library / client」的定义**；三条学习目标；**复习幻灯片、代码包**（**本讲无短视频**）
  - 第 2 页：**泛型数据结构 I**；队列接口为什么「一定要 `string`」不合理；**`// typedef _______ elem;`（客户端提供）**；`queue_t` 接口
  - 第 2–3 页：**下划线的两种含义**（库隐藏实现 / 客户端隐藏 `elem`）；**客户端必须拆两个文件**；`% cc0 queue-client.c0 queue.c0 main.c0`；**「any given program only supports a single type of queue element」**
  - 第 3 页：**哈希字典（hdict）**；库侧只提供 `hdict_t`；`hdict_new(int capacity)`、`hdict_lookup`、`hdict_insert` 的初版
  - 第 4 页：`hdict_new` 语义（容量必须严格正）；`hdict_lookup` 语义；**客户端必须提供 `entry` 与 `key`**；**`entry` 必须是指针且非 `NULL`**（为了用 `NULL` 表示缺失）
  - 第 4–5 页：**三个客户端函数**——`entry_key`（从条目取键）、`key_hash`（键 → 整数）、`key_equiv`（键相等）；`entry_key` 的前置 `x != NULL`
  - 第 5 页：`hdict_insert` 的后置 `hdict_lookup(H, entry_key(x)) == x`；**`key_hash` 可返回任意整数**，取模由库做；**「The hash set implementation will work correctly (albeit slowly) even if it maps every key to 0」**；`hdict_lookup` 的后置 `\result == NULL || key_equiv(entry_key(\result), k)`
  - 第 5–6 页：**完整接口汇总**（客户端接口 + 库接口）
  - 第 7 页：**小客户端：词频统计**；`struct wcount { string word; int count; }`；`entry_key`/`key_hash`/`key_equiv` 的实现
  - 第 7 页：**通用字符串哈希**；`string_charat`、`char_ord`
  - 第 8 页：`hash_string` 骨架；**不组合（`h` 恒 0）→ 正确但极慢**；**`h = h + ch`**；**第一张统计表**（`m = 22800`、`n = 45600`、`α = 2`）：21217 条空链、**最长链 176**
  - 第 9 页：**「变位词必然冲突」**；**`h = 31*h + ch`**（Java 采用）；**第二张统计表**：3057 条空链、**最长链 10**
  - 第 9–10 页：**`h = rand(r)*h + ch`**（`init_rand(0x1337BEEF)`）；**第三张统计表**：3796 条空链、**最长链 11**；「comparable ... not actually quite as good」
  - 第 10 页：**每步 LCG 步进** `h = 1664525*h + 1013904223; h = h + ch;`；**两个目标（快 + 分布好）**；**「Handwritten hash functions often do not work well」**
  - 第 11 页：**Coherence（一致性）**；`key_equiv` 换成「长度相等」的反例（**`"amlet"` 返回错条目**）
  - 第 11–12 页：**`key_hash` 换成「首字母」**的反例（**性能问题而非正确性**）；**「keys that are considered equal should hash to the same value」**；**「used the information in the key in very different measures」**
  - 第 12 页：**固定大小实现**；`chain_node`、`hdict_header`（`size`/`capacity`/`table` 与内嵌不变式注释）；**`is_hdict`（标注 incomplete）**；**六条注释缺失的不变式**
  - 第 13 页：**`\length` 必须在注解里**；**`index_of_key` = `abs(key_hash(k) % H->capacity)`**；`hdict_new`
  - 第 13–14 页：**`hdict_lookup`** 完整代码
  - 第 14 页：**`hdict_insert`** 完整代码；**`//@assert p->data != NULL; // Not given by loop invariant!`**；**头插法**
  - 第 14–16 页：**哈希集合**；**三个特化步骤**（合并 `key`/`entry`、去掉 `entry_key`、`hset_contains` 返回 `bool` 故 `elem` 可为任意类型）；`hset` 接口
  - 第 17 页：**习题 1**（学生记录）、**习题 2**（`hdict_size` / `hdict_tabulate`）、**习题 3**（动态扩容）、**习题 4**（`key_hash(k, m)`）、**习题 5**（删除 + 缩容）、**习题 6**（键值分离）、**习题 7**（哈希集合实现）
  - 第 18 页：习题 6 的接口（`key` / `value` 分离版）
  - 第 19 页：**习题 1 答案**（`student_record`）；**习题 2 答案**（`hdict_size` 一行、`hdict_tabulate` 双重循环）
  - 第 20 页：**习题 2 答案的完整代码**；**习题 3 答案开始**（`maxload` 参数、阈值硬编码 vs 客户端可配）
  - 第 21 页：`hdict_new(capacity, maxload)` 的扩展接口；`hdict_header` 加 `maxload` 字段；**「除法会得到意外结果，改用乘法」**；`hdict_insert` 的两行扩展
  - 第 22 页：**`hdict_resize` 完整代码**；**互递归与前向声明**；**「用 `hdict_new` 重定义 `H` 不工作」**（caller 看不到）；**习题 4 答案开始**
  - 第 22–23 页：**习题 4 答案**（`key_hash(key k, int m)` 的契约 `m > 0`、`0 <= \result < m`；`index_of_key` 退化成一行）
  - 第 23 页：**习题 5 答案开始**；`hdict_delete` 的接口与后置 `hdict_lookup(H, k) == NULL`；**「`p = p->next` 不修改链」**；**头节点特例**；**`prev` 指针方案**
  - 第 23–24 页：**`hdict_delete` 完整代码**；**四分之一缩容**；**`H->capacity/2 > 0 ? H->capacity/2 : 1`**（容量不能为 0）
  - 第 24–25 页：**习题 6 答案**（`chain_node` 加 `key` 与 `value` 字段；`value != NULL`）；`hdict_lookup` 更新
  - 第 25–26 页：**习题 6 的 `hdict_insert(H, k, v)`** 完整代码
  - 第 26 页：**习题 7 答案开始**（`chain_node` 用 `elem data`；`is_hset` 不查非 `NULL`）
  -第 26–27 页：**`hset_contains` 与 `hset_add` 完整代码**
- **原始网页链接**：`https://www.cs.cmu.edu/~15122-archive/f26/handouts/lectures/13-hdict.pdf`
- **配套代码包**：`https://cs.cmu.edu/~15122/handouts/code/13-hdict.tgz`（本库已下载为 `90-原始PDF/15-122/code/13-hdict.tgz`，**未解压**）
- **复习幻灯片**：`https://cs.cmu.edu/~15122/handouts/slides/review/13-hdict.pdf`（本库**未**收录其提取文本，页码待人工核对）
- **相关复习幻灯片（泛型与 `void*`）**：`https://cs.cmu.edu/~15122/handouts/slides/review/12-voidstar.pdf`（本库有提取文本 `_scout/text/15-122__review-slides__12-voidstar.pdf.txt`，共 **37 页**）。**本讲第 2–3 页的「泛型数据结构 I」正是它的前半部分**；幻灯片后半部分给出 **C1 的 `void*` 解法**（见 [[15-122-12-Hashing]] 5.9），**即讲义 p3 说的「next lecture」要解决的问题**。
- **短视频**：**本讲第 1 页没有列出任何短视频**（只有复习幻灯片与代码包两个链接）——**这是 L01–L13 中少数没有配套视频的讲次之一。**

> **原文异常**：
> 1. **第 2 页的队列接口有两处不一致**：第一块用 `string deq(queue_t S)`，第二块用 `elem deq(queue_t Q)` 但前置条件写成 `/*@requires Q != NULL && !queue_empty(S); @*/`——**`S` 在第二块里没有声明**（参数名是 `Q`）。**这是从第一块复制粘贴后未改完的遗留。**
> 2. **第 3 页 `hdict_new` 标注 `/* O(1) */` 与实现矛盾**：`hdict_new` 里 `alloc_array(chain*, capacity)` **必然是 `O(capacity)`**。**对比 [[15-122-11-Unbounded-Arrays]] 的脚注「By necessity, `uba_new(n)` has cost `O(n)`」——那里承认了，这里没有。** **接口声明 `O(1)` 是不准确的。**
> 3. **第 5 页「The hash **set** implementation will work correctly (albeit slowly) even if it maps every key to 0」中「hash set」应为「hash table」或「hash dictionary」**——**这段讨论的是字典的 `key_hash`，不是集合。**
> 4. **第 5–6 页的接口排版被提取文本破坏**：`// typedef _______` 与 `key;` 分在两行，`key` 与 `entry_key(entry x)` 分在两行，`int` 与 `key_hash(key k);` 分在两行。**这是 PDF 里「`typedef` 与类型名对齐」的排版在纯文本提取后的残留，原 PDF 应为一行。**
> 5. **第 12 页 `is_hdict` 明确标注「This `is_hdict` function is incomplete」**——**只写了 3 条不变式，另有 6 条以注释形式给出、1 个省略号。** **故本讲的代码在 `cc0 -d` 下无法完整验证。** **这是「教学代码」的已知缺口，不是笔误。**
> 6. **第 14 页 `hdict_insert` 里的 `//@assert p->data != NULL; // Not given by loop invariant!` 是一个「自认的缺口」**：**它承认循环不变式推不出这条断言，而这条断言本应由 `is_hdict` 的「链上无 `NULL` 条目」不变式提供。** **故这句 `//@assert` 是「不变式不完整」的直接症状。**
> 7. **第 21 页「The naive way ... checking whether `H->size/H->capacity >= H->maxload`, **will may** yield unexpected outcomes as `/` is integer division」有两点问题**：(a) **「will may」是笔误**（应为「will」或「may」）；(b) **论证不严密**——**当 `maxload` 是 `int` 且 `capacity > 0` 时，`floor(size/capacity) >= maxload` 与 `size >= capacity*maxload` 是等价的**（对正整数成立），**故整数除法并不会「产生意外结果」。** **真正的问题只在 `maxload` 为浮点时出现。** **讲义的警告更像「防御性编程」而非「必然的错误」。** 本笔记 5.9 已指出这一点。
> 8. **第 23–24 页 `hdict_delete` 有一个真实的 bug**：**`(H->size)--;` 与 `done = true;` 都在 `else` 分支内**——**故删除**头节点**（`prev == NULL`）时 `size` 不减、`done` 不置真。** **后果**：`size` 虚高（`is_hdict` 的「条目数 == `size`」被违反）、循环继续走到链尾（多走几步）、后续扩容判断基于错误的 `size`。** 讲义未指出此 bug。本笔记 5.10 与 6.2 示例 D 给出了完整追踪与修法。
> 9. **第 24 页缩容判据 `H->size <= (H->capacity * H->maxload) / 4` 用了除法**，而第 21 页扩容判据特意改成乘法并说「除法会有意外结果」——**同一份代码里两种风格不一致。** **虽在整数下等价，但自相矛盾。**
> 10. **第 22 页 `hdict_resize` 的两个 `for` 循环没有任何循环不变式**：**故 `//@ensures is_hdict(H)` 在 `cc0 -d` 下无法验证。** **严格来说需要「已重新插入的条目数」与「新表中每个条目的键都哈希到正确下标」这样的不变式。**
> 11. **第 20 页 `hdict_tabulate` 的不变式不足以证明后置条件**：**外层 `0 <= i && i <= H->capacity`、内层 `0 <= j && j <= H->size` 只保证不越界**，**但后置 `\length(\result) == hdict_size(H)` 需要「最终 `j == size`」**——**缺一条耦合不变式（如 `j == 前 i 条链的条目总数`）。** 本笔记 6.2 示例 F 已指出。
> 12. **第 25 页 `struct chain_node { key key; value value; ... }` 的字段名与类型名完全相同**：**在 C0 里这是合法的**（字段名与类型名在不同命名空间），**但可读性差，且容易与 `p->key` 的语义混淆。** **不是错误，是风格问题。**
> 13. **第 27 页「one different, also seen in `hset_contains`, is that we do not need to extract keys from entries」有语法错误**：**「one different」应为「one difference」。**
> 14. **第 17 页习题 1 的题干有笔误**：「the associated grades are **a** stored in a character array」——多了一个 `a`。
> 15. **第 8 页说「we can get access to the individual characters in a string with the function `string_charat(s, i)`」**——**C0 的字符串库确实有 `string_charat`，但同一句里的 `char_ord(c)` 取的是「`char` 的 ASCII 值」**。**两者配合才能得到字符的整数值，讲义说清了，但读者容易漏掉「必须两层嵌套」。**
> 16. **第 1 页说「We will discuss the interface to hash tables in details」——「in details」应为「in detail」。**
> 17. **第 9 页「Some versions of Java use this as their default string hashing function」**——**准确地说，`31*h + ch` 是 `java.lang.String.hashCode` 的**规定**算法（不是「some versions」，是「Java 规范」）。** 属于表述过弱，不是错误。

## 9. 对应视频

未找到官方公开录像。**本讲第 1 页也没有列出任何短视频**（只有「Review slides」与「Code for this lecture」两个链接）——**这与 L01–L12 多数讲次不同，那些讲次至少有一个短视频。** 故本讲只有讲义与代码包可用。

建议的动手顺序：(1) 用 6.2 示例 A 的六个变位词，**在纸上分别算 `h+ch` 与 `31h+ch` 的哈希值**，亲眼看到前者全撞、后者分散；(2) 实现 `hash_string` 的三个版本，**用一份 1000 词左右的词表跑 `ht_stats`**，打印「空链数」与「最长链」，**对比讲义的三张表**（你的数字会不同，但趋势应一致）；(3) 故意把 `key_equiv` 改成「长度相等」，**跑一个「查错词」的测试**，你会看到它返回一个长度相同但内容不同的条目——**这就是 5.4 的反例在你机器上复现**；(4) 把 `key_hash` 改成「首字母」，**用 `time` 比较查找 10000 次的耗时**，体会「正确但慢」；(5) 实现 `hdict_delete`，**先照抄讲义版本（带 bug）**，写一个「插入 100 个、删 50 个头节点」的测试，**打印 `H->size` 与实际遍历计数**，你会看到两者不等——**然后把 `size--` 移出 `else` 分支，再看一次**；(6) 实现 `hdict_resize`，**在每次扩容时打印 `capacity` 与 `size`**，验证「扩容后 `α == 1`」（当 `maxload = 2`）。

## 10. 本节复习

1. **关注点分离**：接口 = **类型 + 操作 + 前后置条件 + 渐进复杂度**。
2. **新问题**：**库可能需要客户端提供操作**——哈希字典是最佳例子。
3. `// typedef ______* hdict_t;`：**库提供，客户端不知实现**（只知道是指针）。
4. `// typedef _______ elem;`：**客户端提供，库不知实现**。
5. 泛型的代价：**客户端必须拆两个文件**（`elem` 在库之前、库在应用之前）。
6. 泛型的代价：**一个程序只能一种 `elem`**（`typedef` 只能一次）。**解法在 C1 的 `void*`**。
7. 哈希字典**库侧**只提供 `hdict_t` + `hdict_new` + `hdict_lookup` + `hdict_insert`。
8. **客户端必须提供**：`entry`（指针、非 `NULL`）、`key`、`entry_key`、`key_hash`、`key_equiv`。
9. **「三个函数」是从 `hdict_lookup` 的算法反推出来的**，不是拍脑袋。
10. `entry` 必须是**指针且非 `NULL`**，**因为 `hdict_lookup` 用 `NULL` 表示「不存在」**。
11. `key_hash` 返回**任意整数**，**取模由库做**（因为客户端不知道 `capacity`）。
12. `hdict_insert` 的后置：**`hdict_lookup(H, entry_key(x)) == x`**（插入后能查回）。
13. `hdict_lookup` 的后置：**`\result == NULL || key_equiv(entry_key(\result), k)`**（**弱规格**：不承诺「没找到就真没有」）。
14. **Coherence**：`key_equiv(k1,k2) ⟹ key_hash(k1) == key_hash(k2)`。
15. **违反 coherence 是正确性 bug**（`"amlet"` 返回 `"apple"`）；**哈希太粗只是性能问题**。
16. **「两个函数要用同样多的信息，且都用全部信息」**——哈希字典设计第一原则。
17. `hash_string` 骨架：遍历字符，`char_ord(string_charat(s, i))` 取 ASCII。
18. **不组合 → `h` 恒 0 → 正确但极慢**（一条链）。
19. **`h = h + ch` → 变位词全冲突**（加法可交换）；最长链 **176**（`n=45600, m=22800`）。
20. **`h = 31*h + ch` → 多项式滚动**；最长链 **10**；Java 采用。
21. **为什么是 31**：奇数、`= 2^5-1` 可优化、足够小。
22. **`h = rand(r)*h + ch`** 略差于 31（最长链 **11**）——**因为「随机」只是换了一组固定乘数**。
23. **每步 LCG 步进** `h = 1664525*h + 1013904223` 是另一种变体。
24. **两个目标冲突**：快（少运算）vs 分布好（多混合）。**`31*h+ch` 是「每字符最少运算」的最优解。**
25. **「可预测的冲突」是设计缺陷的标志**；随机冲突无法避免。
26. `index_of_key` = **`abs(key_hash(k) % H->capacity)`**——**`abs` 必需**（C0 的 `%` 可为负）。
27. **`abs(int_min())` 溢出**——故必须**先取模再 `abs`**，不能反过来。
28. `hdict_header` = `size` + `capacity` + `table`（`\length(table) == capacity`）。
29. **`is_hdict` 讲义版只有 3 条，完整版至少 10 条**（无 `NULL` 条目、无重复键、条目数 == `size`、每个条目哈希到自己的下标、链无环…）。
30. **「每个条目哈希到 `H->table[i]` 的下标 `i`」是哈希字典的正确性核心。**
31. **`\length` 只能出现在注解里**——故用 `is_array_expected_length` 偷渡。
32. `hdict_lookup`：**`for` 遍历链 + `key_equiv` + 返回 `p->data`**；找不到返回 `NULL`。
33. **`//@assert p->data != NULL; // Not given by loop invariant!`**——**不变式不完整的直接症状**。
34. `hdict_insert`：**先查同键覆盖，否则头插**；`O(1)`（不算扩容）。
35. **`key_equiv` 应满足自反、对称、传递**——**讲义未要求，但后置条件证明需要自反性**。
36. **扩容必须「重新插入每个条目」，不能「复制」**——**因为 `index_of_key` 依赖 `capacity`**。
37. **判断阈值用乘法** `size >= capacity * maxload`（避免整数除法）；**但整数下两者等价**（讲义的论证不严密）。
38. **`capacity * maxload` 可能溢出**——讲义说「we ignore possible overﬂow issues」。
39. **互递归需要前向声明**（`void hdict_insert(hdict* H, entry x);`）。
40. **不能用 `hdict_new` 重定义 `H`**——**只改局部指针，caller 看不到**；必须改 `*H` 的字段。
41. **扩容后 `α == 1`**（当 `maxload = 2`）——**与无界数组「扩容后半满」同构**。
42. **删除时 `p = p->next` 无效**——**`p` 是局部变量，不是链上的字段**。
43. **`prev` 指针 + `prev == NULL` 哨兵**统一「删头」与「删中间」两种情形。
44. **⚠️ 讲义的 `hdict_delete` 有 bug**：**`size--` 与 `done = true` 只在 `else` 分支**——**删头节点时 `size` 不减。**
45. **缩容到四分之一**（不是半满）——**避免抖动**；**容量不能为 0**（三元式保底为 1）。
46. **哈希集合是字典的特化**：合并 `key`/`entry` → 去掉 `entry_key` → `hset_contains` 返回 `bool`。
47. **`elem` 可以是任意类型**——**因为返回 `bool`，不需要 `NULL` 哨兵**。
48. **四种接口变体**：键嵌入条目（A）、键值分离（B）、传 `m`（C）、集合（D）——**没有「最好」，只有「最合适」。**
49. **`maxload` 交给客户端配置**——**不同应用有不同时间—空间偏好**。
50. **`hdict_new` 标注 `O(1)` 但实际是 `O(capacity)`**（`alloc_array`）——**接口声明不准确**。

## 11. 自我检查

**题 1.** 某客户端定义了 `typedef int key;` 与 `typedef struct rec* entry;`，并写 `int key_hash(key k) { return k; }`、`bool key_equiv(key k1, key k2) { return k1 == k2; }`。这个组合满足 coherence 吗？若客户端改 `key_hash` 为 `return k * 2;`，coherence 还成立吗？`hdict_lookup` 的行为会变吗？

**题 2.** 解释为什么 `hdict_lookup` 的后置条件**不**承诺「返回 `NULL` 时键真的不存在」。若强行加上这条承诺，接口会付出什么代价？请给出一个「客户端无法承受」的理由。

**题 3.** 设 `capacity = 8`、`maxload = 2`，字典里已有 `size = 16`。现在要插入第 17 个条目。按讲义的判据 `H->size >= H->capacity * H->maxload`，会触发扩容吗？扩容后 `capacity` 与 `α` 各是多少？若判据误写成 `H->size / H->capacity >= H->maxload`，结果会不同吗？

**题 4.** 讲义的 `hdict_delete` 删头节点时 `size` 不减。请写出完整追踪（链为 `[X] → [Y] → NULL`，删 `X`），并说明这个 bug 会在哪三个地方造成可观察的后果。

**题 5.** 为什么哈希集合的 `elem` 可以是 `int`，而哈希字典的 `entry` 必须是指针？请从「接口的返回类型」角度回答，并说明如果哈希字典的 `hdict_lookup` 改成返回 `bool` 加一个「输出参数」，`entry` 还需要是指针吗？

<details>
<summary>参考答案</summary>

**答 1.**

**原版（`key_hash(k) = k`、`key_equiv` 是 `==`）：coherence 成立** ✅。

因为 `k1 == k2` ⟹ `key_hash(k1) == key_hash(k2)`（同一个 `int` 值）。**这是「恒等哈希」——最简单的一致组合。**

**改成 `key_hash(k) = k * 2`：coherence 仍然成立** ✅。

因为 `k1 == k2` ⟹ `2*k1 == 2*k2`。**任何「确定性函数」都满足 coherence**——**只要 `key_hash` 是「键的函数」，相等的键必然得到相等的哈希。**

**故「coherence 违反」只在一种情况下发生**：**`key_equiv` 把「不同的键」判为相等**（即 `key_equiv` 比「值相等」更粗）。**上题里 `key_equiv` 是严格的 `==`，故不可能违反。**

**`hdict_lookup` 的行为会变吗？**

- **正确性：不变** ✅——**coherence 成立，故「等价键必在同一条链上」。**
- **性能：会变**——`key_hash(k) = 2*k` **只产生偶数**，`% capacity` 后**只有约一半的槽位被用到**（`capacity` 为偶数时尤其明显：`2k % 8` 只能是 `0, 2, 4, 6`）。

**具体例子**：`capacity = 8`、键为 `0..7`。

| 键 | `2k` | `% 8` |
|---|---|---|
| 0 | 0 | 0 |
| 1 | 2 | 2 |
| 2 | 4 | 4 |
| 3 | 6 | 6 |
| 4 | 8 | 0 ← 与 0 撞 |
| 5 | 10 | 2 ← 与 1 撞 |
| 6 | 12 | 4 |
| 7 | 14 | 6 |

**有效槽位只有 4 个**（`0, 2, 4, 6`），**装载因子实际翻倍。** **这属于「分布不均」（5.4 的反例二），不是 coherence 违反。**

**答 2.**

**为什么后置条件不承诺「`NULL` ⟹ 真的不存在」**：

**因为这条承诺需要遍历整张表才能验证**。**严格的写法是**：

```
(\result == NULL && !exists_entry_with_key(H, k))
|| (\result != NULL && key_equiv(entry_key(\result), k))
```

**其中 `exists_entry_with_key` 必须扫描 `capacity` 条链**——**那是 `O(n)` 的工作。**

**客户端无法承受的理由**：

1. **`hdict_lookup` 的接口承诺是 `O(1) avg.`**（讲义 p4）。**若后置条件需要 `O(n)` 的验证，那这个 `O(1)` 承诺就成了空话**——**因为 `cc0 -d` 下每次调用都要付 `O(n)` 的验证开销。**
2. **验证器无法用 `O(1)` 的信息证明 `O(n)` 的命题**。**`is_hdict` 只说「每个条目哈希到自己的下标」，它不会告诉你「槽位 `i` 上没有键 `k`」**——**除非你把整条链都检查一遍。**
3. **实践上不需要**。**客户端真正关心的是「找到了就一定是它」**（这条后置保证了）。**「没找到」时客户端的行为通常是「插入新条目」——它不需要证明「确实不存在」，只需要「查不到」。**

**故这是一个「弱规格」的有意选择**：**用「可 `O(1)` 验证」换「逻辑上的完整性」。** **讲义 p5 的 `key_hash` 讨论里也有同款取舍**——**「The hash set implementation will work correctly (albeit slowly) even if it maps every key to 0」**：**正确性不依赖哈希质量，正是因为这个后置条件足够弱。**

**答 3.**

**判据**：`H->size >= H->capacity * H->maxload`，即 `16 >= 8 * 2 = 16`。

**`16 >= 16` 为真 → 会触发扩容** ✅。

**扩容后**：`capacity = 2 * 8 = 16`，`size = 17`（插入后）。

**`α = size / capacity = 17 / 16 ≈ 1.06`**。

**注意**：**扩容发生在「插入之后」**（讲义 p21 的两行在 `hdict_insert` 末尾）。**故 `size = 17` 时才扩，扩容后 `α = 17/16`。**

**若判据误写成 `H->size / H->capacity >= H->maxload`**：`16 / 8 = 2`，`2 >= 2` **为真 → 同样触发扩容** ✅ **结果相同。**

**为什么相同**：**`floor(16/8) = 2` 与 `16 >= 16` 在整数下等价**（见 5.9 对讲义论证的批评）。**只有当 `maxload` 是浮点数（如 `2.5`）时，`size/capacity` 的整数截断才会给出错误结果**（`floor(19/8) = 2`，而 `2 >= 2.5` 为假，但 `19 >= 8*2.5 = 20` 也为假——**这次又巧合地对上**；真正的分歧出现在 `size = 20`：`floor(20/8) = 2 < 2.5` 为假 → 不扩，而 `20 >= 20` 为真 → 该扩）。

**故讲义的警告在 `maxload` 为 `int` 时是「过度防御」**，**但作为「不要依赖整数除法语义」的编程习惯，仍然值得遵守。**

**答 4.**

**链**：`H->table[i] → [X] → [Y] → NULL`，`size = 2`，删 `X`。

**追踪**：

| 步 | `p` | `prev` | `done` | 动作 |
|---|---|---|---|---|
| 初 | `X` | `NULL` | `false` | — |
| 1 | `X` | `NULL` | `false` | `key_equiv(k_X, entry_key(X))` **真**；`prev == NULL` → **`H->table[i] = p->next`**（即 `= Y`）✅ 链结构正确；**`size` 未减（仍 2）；`done` 未置真（仍 `false`）** ❌；末尾 `prev = X`（**已删节点**） |
| 2 | `Y` | `X`（已删） | `false` | `key_equiv(k_X, entry_key(Y))` 假；末尾 `prev = Y` |
| 3 | `NULL` | `Y` | `false` | 循环条件 `p != NULL` 假 → 退出 |

**结果**：链变成 `H->table[i] → [Y] → NULL` ✅，**但 `size` 仍是 2（应为 1）** ❌。

**三个可观察后果**：

**（1）`is_hdict` 的「条目数 == `size`」被违反**。**若这条不变式写进了代码，`cc0 -d` 会在下一次 `hdict_insert`/`hdict_delete` 的入口报 `is_hdict(H)` 失败。** **但讲义版 `is_hdict` 没写这条（只在注释里），故运行时抓不到。**

**（2）`size` 虚高导致扩容判断提前触发**。**判据 `size >= capacity * maxload` 用的是虚高的 `size`**——**若删了 `k` 个头节点，`size` 就多 `k`，于是「提前 `k` 次插入」就扩容。** **后果**：**内存浪费**（`capacity` 比需要的大）、**`α` 比实际小**（性能反而「看起来更好」，掩盖了问题）。

**（3）缩容判断也错**。**判据 `size <= (capacity * maxload) / 4` 用虚高的 `size`**——**故「该缩容时不缩」**，**表一直偏大。** **长期运行会「只涨不缩」。**

**修法**：把两行移到 `if/else` 之外：

```c0
if (key_equiv(k, entry_key(p->data))) {
  if (prev == NULL)
    H->table[i] = p->next;
  else
    prev->next = p->next;
  (H->size)--;
  done = true;
}
```

**另一个隐藏问题**：**即使修好了，第 1 步末尾 `prev = X`（已删节点）仍然危险**——**若链上还有第二个同键条目（理论上不该有），第 2 步会走 `else` 分支写 `X->next`，而 `X` 已不可达，写入丢失。** **故「键唯一」不变式（5.7 第 3 条）是这段代码正确性的另一个前提。** **若不变式被违反，`hdict_delete` 会「静默地少删」。**

**答 5.**

**从「接口的返回类型」看**：

- **哈希字典**：`entry hdict_lookup(hdict_t H, key k)`——**返回 `entry`，需要一个「没有」的值。** **C0 里唯一能表示「任意指针的缺失」的值是 `NULL`**，**故 `entry` 必须是指针类型。** **若 `entry` 是 `int`，「没找到」返回什么？** `0`？**那 `0` 这个条目怎么办？** `-1`？**那 `-1` 呢？** **没有安全的哨兵值。**
- **哈希集合**：`bool hset_contains(hset_t H, elem x)`——**返回 `bool`，`true`/`false` 覆盖了所有情形，不需要「缺失值」。** **故 `elem` 可以是任意类型**（`int`、`char`、`bool`、`string`…）。

**「如果 `hdict_lookup` 改成返回 `bool` + 输出参数」**：

```c0
bool hdict_lookup(hdict_t H, key k, entry* out)
/*@ensures \result == false || (*out != NULL && key_equiv(entry_key(*out), k)); @*/ ;
```

**此时 `entry` 还需要是指针吗？** **需要**——**但理由变了**：

1. **`out` 是 `entry*`（指向 `entry` 的指针）**。**若 `entry` 是 `int`，`out` 就是 `int*`，C0 允许**（`alloc(int)` 可以）。**故「输出参数」本身不要求 `entry` 是指针。**
2. **但 `entry_key(entry x)` 的前置是 `x != NULL`**（讲义 p4）。**若 `entry` 是 `int`，这条前置无意义**——**得改成「不需要前置」，或改成「`out` 已指向有效内存」。**
3. **真正的问题在「`hdict_insert` 的 `x != NULL` 前置」**：**这条前置是「拒绝插入 `NULL` 条目」的保证**，**它保证了「链上不会有 `NULL` 条目」这条不变式（5.7 第 1 条），从而保证 `entry_key(p->data)` 永远安全。** **若 `entry` 是 `int`，「拒绝 `NULL`」这个概念消失**——**你得另找一条不变式（比如「所有条目都满足某个 `is_entry`」），而那需要客户端提供 `is_entry` 函数。**

**故结论**：**`hdict_lookup` 改成 `bool` + 输出参数后，`entry` 在「类型层面」不再必须是指针**，**但会失去「用 `NULL` 表达「无条目」这个统一约定」**——**你需要引入 `is_entry(entry x)` 这样的客户端谓词来替代它，接口反而更复杂。**

**故「`entry` 必须是指针」的真正理由不是「`lookup` 要返回 `NULL`」，而是「`NULL` 是一个**库与客户端都无需额外定义就能理解的哨兵**」**。** 换成 `int` 后，你得自己发明一个哨兵，并让客户端承诺「不会插入那个哨兵值」——**这比「用 `NULL`」麻烦得多。**

**这就是讲义 p4 那句话的完整含义**：

> **「we will however require entries to have pointer type and be non-`NULL`. Doing so allows `hdict_lookup` to return `NULL` to signal that the dictionary does not contain any entry with the requested key.」**

**「allows」不只是「技术上可行」，而是「用语言内置的、双方都认的约定」。**

</details>

## 12. 进一步学习

- 上一讲：[[15-122-12-Hashing]] —— **哈希表的原理**（链地址法、装载因子、平均分析、LCG、生日悖论）。**本讲把那张表包装成有接口、有不变式、有客户端契约的抽象类型。**
- 下一讲：[[15-122-14-Genericity]] —— **泛型**：`typedef void* elem;` 与函数指针，让本讲的字典不再绑定某一种 `entry`。再往后是 [[15-122-15-Binary-Search-Trees]] —— **二叉搜索树**：不用哈希也能做到 `O(log n)`，**且保留顺序**（支持范围查询、有序遍历）。**这是哈希表做不到的事**（见 [[15-122-12-Hashing]] 5.1 的对比表）。
- 相关讲次：[[15-122-08-Libraries]]（抽象类型与不变式的写法；`is_array_expected_length` 同款技巧）、[[15-122-10-Linked-Lists]]（链就是链表；头插法；`prev` 指针技巧在 `deq` 里也用过）、[[15-122-11-Unbounded-Arrays]]（扩容 + 摊还 + 四分之一缩容，本讲习题 3、5 直接复用）、[[15-122-01-Contracts]]（指向式推理：客户端**不看实现**就能用库，这正是接口设计的目的）。
- 课程入口：[[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]]、[[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 术语查询：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Dictionary、Hash Table、Hash Function、Collision、Chaining、Load Factor、Key、Entry、Value、Coherence、Generic、Abstract Type、Forward Declaration、Mutual Recursion 等条目）。
- 延伸阅读：**Cormen et al. 《Introduction to Algorithms》第 11 章**（链地址法与开放寻址的完整分析）；**Sedgewick《Algorithms》第 3.4 节**（哈希函数的工程实践，含 Java 的 `31` 与 Python 的随机化哈希）；**Effective Java 第 9 条「Always override `hashCode` when you override `equals`」**——**这正是 coherence 的工程表述**（`equals` 相等则 `hashCode` 必须相等）；**《Design Patterns》的「Strategy 模式」**——**客户端提供 `key_hash`/`key_equiv` 正是「把算法作为参数传入」的雏形**（C0 没有函数指针，故用「客户端定义函数名」模拟）。
