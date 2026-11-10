---
course: CMU 15-213
course_name: Introduction to Computer Systems
semester: Fall 2026
lecture_id: lab-cprogramminglab
topic: CProgrammingLab（L0）实验笔记
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-213
  - Lab
  - CProgrammingLab
  - C
  - 链表
---

# CMU 15-213 · CProgrammingLab（L0）实验笔记

> 实验总览见 [[20-CMU-15-213/03-Lab实验笔记/00-Lab总览|15-213 Lab 总览]]。
>
> **原文**：`90-原始PDF/15-213/labs/cprogramminglab.pdf`（8 页），标题 "C Programming Lab: Assessing Your C Programming Skills"，Fall 2026。
> **原始链接**：<https://www.cs.cmu.edu/~213/labs/cprogramminglab.pdf>（官方 schedule 页下载）
> **代码包**：`90-原始PDF/15-213/labs/cprogramminglab-handout.tar`
> 本笔记所有内容均取自上述 PDF 与 handout 的真实结构，**不包含任何官方解答**。

---

## 1. 本节学习目标

学完本页并动手做完 L0，你应当能够：

1. **写出**一条带 `head` / `tail` / `size` 三个字段的单链表队列，并在**每一条修改路径**上正确维护三者的不变量。
2. **解释**为什么 `queue_insert_tail` 与 `queue_size` 的朴素实现是 O(n)，以及「存冗余信息换 O(1)」的代价具体落在哪里。
3. **判断**一段队列代码在 NULL 队列、空队列、单元素队列这三种边界上会不会崩，并说出崩在哪一行。
4. **读懂** AddressSanitizer 的报错栈，定位到 `queue.c` 的具体行号。
5. **区分**「深拷贝」与「浅拷贝」、`malloc(strlen(s))` 与 `malloc(strlen(s)+1)`、NULL 队列与空队列这几组容易混的东西。
6. **搭建**一个不依赖 CMU 账号的本地实验环境，跑通 `qtest` 与 `driver.py`。

---

## 2. 前置知识

- **C 语言基础**：指针、`struct`、`malloc` / `free`、字符串与 `'\0'` 结尾、`sizeof`。参考 K&R《The C Programming Language》第 2 版第 5–6 章（`01-overview.pdf` 第 47 页推荐）。
- **链表**：单链表的插入 / 删除 / 遍历。15-122 的对应讲义：<https://www.cs.cmu.edu/~15122/handouts/lectures/10-linkedlist.pdf>。
- **渐进复杂度**：O(1) 与 O(n) 的含义。15-122 的对应讲义：<https://www.cs.cmu.edu/~15122/handouts/lectures/05-bigo.pdf>。
- **本课程内的相关讲次**：
  - 调试方法：[[20-CMU-15-213/02-中文学习笔记/15-213-08-Design-and-Debugging|L08 Design and Debugging]]
  - 堆与动态内存分配（本 lab 的「下一站」）：[[20-CMU-15-213/02-中文学习笔记/15-213-13-Dynamic-Memory-Allocation-Basic|L13 Dynamic Memory Allocation: Basic]]
- **环境**：命令行、`make`、`tar`。

---

## 3. 核心概念

- **Queue（队列）**：先进先出（FIFO）的线性结构。本 lab 用**单链表**实现，但允许在头部插入（LIFO 纪律）与尾部插入（FIFO 纪律）两种操作并存。
- **`list_ele_t`（链表结点）**：`{ char *value; struct list_ele *next; }`。`value` 指向一个**独立分配**的字符串，`next` 指向下一个结点。
- **`queue_t`（队列顶层结构）**：起始代码只有 `head` 一个字段；为了达到 O(1) 要求，需要自己加 `tail` 与 `size`。
- **Deep copy（深拷贝）**：为新结点**另外分配**一块内存并把字符串内容复制过去，而不是只复制指针。本 lab 要求必须深拷贝。
- **Invariant（不变量）**：在每次公开操作返回后都必须成立的条件。本 lab 的不变量是「`head == NULL` ⟺ `tail == NULL` ⟺ `size == 0`」，且 `size` 等于实际结点数。
- **AddressSanitizer（地址消毒器，ASan）**：编译期插桩的内存错误检测器，能抓越界读写、重复 `free`、内存泄漏。`qtest` 默认启用。
- **NULL queue vs empty queue（空指针队列 vs 空队列）**：前者是 `queue_t *` 本身为 `NULL`；后者是指针有效但 `head == NULL`。**两者是不同的错误条件**。
- **Trace（追踪脚本）**：一行一条 `qtest` 命令的文本文件，`traces/` 下有 15 个，是评分的基本单位。

---

## 4. 通俗理解

把队列想成**食堂的取餐队伍**：

- 每个结点是一个人，手里举着一张写着名字的纸条（`value` 指向的字符串）。
- `head` 是队首的人，`tail` 是队尾的人，`size` 是队伍长度。
- **深拷贝**的意思是：如果两个人同名（都是 `"cab"`），他们必须各举一张自己的纸条。你不能让两个人共用一张纸条——因为一个人走了把纸条撕了，另一个人手里就只剩空气（悬空指针）。
- **存冗余信息**的意思是：在门口挂一块牌子写「当前队伍长度」。这样有人问「多少人」时你不用从头数一遍（O(n)），直接看牌子（O(1)）。代价是：**每次有人进出，都必须记得改牌子**。忘了改一次，牌子就永久错了。

一个具体数字：队列里有 1,000,000 个元素时，`queue_size` 的朴素实现要遍历 100 万个结点。假设每个结点访问 1 纳秒，一次 `size` 就是 1 毫秒。如果 trace 里有 1000 次 `size` 调用，光这一项就 1 秒——性能 trace 必然超时。加一个 `int size` 字段，这个操作变成一次内存读，约 0.3 纳秒。

---

## 5. 原理与推导

### 5.1 实验基本信息

| 项目 | 内容 |
|---|---|
| 名称 | C Programming Lab（L0） |
| 发布 | 周二 **Aug 25, 2026** |
| 截止 | 周二 **Sep 01, 2026, 11:59pm ET** |
| 最后可交 | 周五 **Sep 04, 2026, 11:59pm ET** |
| 形式 | **个人作业**（individual project），全部电子提交 |
| 预期用时 | 准备充分的学生 **1–2 小时** |
| 迟交 | 本作业有 **1 个 late day** |
| 运行环境 | **Shark 机器**（<https://www.cs.cmu.edu/~213/labmachines.html>） |
| 评分 | **Autolab 自动评分，无代码风格分** |
| 语言 | C（C89/C99 风格，用 `make` 构建） |

**为什么先做这个 lab**：讲义第 1 页把它的定位说得很直白——**这些内容全部是复习**。它检验的五项能力是：

1. **显式内存管理**（C 要求你自己 `malloc` / `free`）。
2. **基于指针的数据结构**的创建与操作。
3. **字符串**处理。
4. **通过在数据结构里存冗余信息来提升关键操作的性能**（这是本 lab 唯一「不复习」的部分，也是它的核心设计意图）。
5. 写**健壮代码**，能正确处理非法参数，包括 `NULL` 指针。

第 8 页的「反思」一节给出明确信号：**如果你写这个 lab 有困难，说明你需要在一个月内补齐 C 语言能力**，因为从 Lab 4 开始的所有作业都需要这里测试的技能。

### 5.2 数据结构（PDF 第 3–4 页）

```c
/* Linked list element */
typedef struct list_ele {
    char *value;
    struct list_ele *next;
} list_ele_t;

/* Queue structure */
typedef struct {
    list_ele_t *head;   /* First element in the queue */
} queue_t;
```

- `queue_t` 起始只有 `head` 一个字段，PDF 明确说「你会想加别的字段」。
- 队列内容是一条单链表，最后一个结点的 `next` 是 `NULL`。
- 字符串长度 `l` 时占 **`l + 1` 个字节**（前 `l` 个存字符，最后一个是 `0`）。
- PDF 第 4 页 Figure 1 用 `["cab", "bead", "cab"]` 举例，特别强调：**两个 `"cab"` 是两个独立的字符数组**，每个结点必须有自己的一份拷贝。

两种特殊情况必须都处理（PDF 第 4 页）：

| 情况 | 定义 |
|---|---|
| **NULL queue** | `queue_t *` 指针本身是 `NULL` |
| **空队列** | 指针有效，但 `head` 是 `NULL` |

### 5.3 七个函数（PDF 第 5 页）

| 函数 | 要求 | 关键约束 |
|---|---|---|
| `queue_new` | 创建一个新的空队列 | 失败时返回 `NULL` |
| `queue_free` | 释放队列占用的**所有**存储 | 必须同时释放每个结点**和**它的字符串 |
| `queue_insert_head` | 在队头插入新元素（**LIFO** 纪律） | 必须 `malloc` 拷贝字符串 |
| `queue_insert_tail` | 在队尾插入新元素（**FIFO** 纪律） | **必须 O(1)**，朴素实现是 O(n) |
| `queue_remove_head` | 移除队头元素 | 空队列 / NULL 队列要能安全处理 |
| `queue_size` | 返回元素个数 | **必须 O(1)**，朴素实现是 O(n) |
| `queue_reverse` | 把队列元素顺序反转 | **不得分配或释放任何链表结点**，只能重排 |

### 5.4 三个硬性约束（最容易丢分的地方）

1. **字符串必须深拷贝**（PDF 第 5 页）：对带字符串参数的函数，必须用 `malloc` 分配空间（**记得给结尾的 `\0` 留位置**）再拷贝。释放结点时必须同时释放字符串。
2. **不能假设字符串长度有上界**：必须按实际长度分配。
3. **只能用 `malloc` / `calloc` / `realloc`**：其它在堆上分配内存的函数会导致扣分。

### 5.5 性能要求怎么满足（本 lab 的核心设计）

`queue_insert_tail` 与 `queue_size` 的朴素实现都是 O(n)。要达到 O(1)，必须在 `queue_t` 里**存冗余信息**：

- 想 O(1) 插入队尾 → 需要一个指向**队尾**的指针。
- 想 O(1) 求长度 → 需要一个**计数器**。

但加了这两个字段之后，**每个会改变队列结构的函数都必须同步维护它们**——这才是本 lab 真正的难点：不是「会不会写链表」，而是「能不能在所有路径上都保持不变量」。

推导：设队列状态为三元组 `(head, tail, size)`，不变量 `I` 定义为

```
I ≡ (head == NULL ∧ tail == NULL ∧ size == 0)
  ∨ (head ≠ NULL ∧ tail ≠ NULL ∧ tail->next == NULL ∧ size ≥ 1)
```

每条语句执行后必须重新满足 `I`。把所有会破坏 `I` 的操作列出来，就得到必须维护的路径表：

| 操作 | 对 `tail` 的影响 | 对 `size` 的影响 | 破坏 `I` 的原因 |
|---|---|---|---|
| `queue_new` | 置 `NULL` | 置 0 | 初始为空，天然满足 |
| `queue_insert_head`（空队列时） | 新结点**同时**成为 tail | +1 | 若只改 `head`，`tail` 仍为 `NULL`，违反 `head ≠ NULL ⇒ tail ≠ NULL` |
| `queue_insert_head`（非空） | 不变 | +1 | 只改 `size` |
| `queue_insert_tail` | 指向新结点 | +1 | 若为空队列，还要同时改 `head` |
| `queue_remove_head`（只剩一个） | 必须置回 `NULL` | −1 | 否则 `tail` 指向已释放结点 |
| `queue_remove_head`（多个） | 不变 | −1 | 只改 `size` |
| `queue_free` | 置 `NULL` | 置 0 | 全部清空 |
| `queue_reverse` | **head 与 tail 互换** | 不变 | 否则 `tail->next != NULL` |

> `queue_reverse` 那一行是最容易漏的：反转之后原来的头变成了尾，原来的尾变成了头。如果忘了交换 `tail`，后续的 `queue_insert_tail` 会写到错误的位置，而 `queue_size` 却仍然正确——这种 bug 在 trace 里表现为「前面几关全过，到某个混合 trace 突然崩」。

### 5.6 不能用递归

PDF 第 5 页明确：**测试会用超过 1,000,000 个元素的队列**，递归会耗尽栈空间。所有遍历必须写成循环。按 Linux 默认 8 MB 栈、每帧 48 字节估算，100 万层递归需要约 48 MB，**远超栈上限**——这就是「必须循环」的定量理由。

### 5.7 文件布局与可改范围（PDF 第 3 页）

解包后得到 16 项：

```
check-format   console.h   driver.py   harness.h   Makefile
queue.c        README      report.h    console.c   cprogramminglab.pdf
harness.c      helper.mk   qtest.c     queue.h     report.c    traces/
```

**只能改 `queue.h` 和 `queue.c`**。可以改隐藏文件 `.clang-format` 来定制格式。**改其它文件没有意义**——autograder 会忽略你的修改，而且很可能导致编译失败。

### 5.8 评分与 trace

`traces/` 目录有 **15 个 trace 文件**，命名格式 `trace-k-cat.txt`（`k` 是编号，`cat` 是测试性质）。每条 trace **6 或 7 分**，满分 **100**。评分完全自动化，`driver.py` 就是 Autolab 用的同一个程序。

---

## 6. 代码示例

### 6.1 官方课程代码

**（1）数据结构声明**（`cprogramminglab.pdf` 第 3 页，`queue.h`）

```c
/* Linked list element */
typedef struct list_ele {
    char *value;
    struct list_ele *next;
} list_ele_t;

/* Queue structure */
typedef struct {
    list_ele_t *head;   /* First element in the queue */
} queue_t;
```

**（2）官方示例 trace**（`cprogramminglab.pdf` 第 6 页，`traces/trace-eg.cmd`）

```
# Demonstration of queue testing framework
# Initial queue is NULL.
show
# Create empty queue
new
# Fill it with some values. First at the head
ih dolphin
ih bear
ih gerbil
# Now at the tail
it meerkat
it bear
# Reverse it
reverse
# See how long it is
size
# Delete queue. Goes back to a NULL queue.
free
# Exit program
quit
```

**（3）下载与解包**（`cprogramminglab.pdf` 第 3 页）

```bash
linux> mkdir ~/private/15213
linux> cd ~/private/15213
linux> autolab download 15213-f26:cprogramminglab
linux> cd cprogramminglab
linux> tar --strip=1 -xf cprogramminglab-handout.tar
linux> rm cprogramminglab-handout.tar
```

`--strip=1` 去掉 tar 包里的顶层目录，让 16 个文件直接落在当前目录。

**（4）构建与测试**（`cprogramminglab.pdf` 第 6 页）

```bash
linux> make
linux> ./qtest -f traces/trace-eg.cmd     # 示例 trace
linux> ./qtest -f traces/trace-01-ops.cmd # 第一个真实 trace
linux> ./driver.py                        # 等价于 make check
```

**（5）提交**（`cprogramminglab.pdf` 第 8 页）

```bash
linux> make                # 生成 cprogramminglab-handin.tar
linux> make submit         # 在 Andrew / Shark 机器上直接提交
```

**（6）官方 ASan 报错样例**（`cprogramminglab.pdf` 第 7 页）

```
==4662==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x602000000318
READ of size 1025 at 0x602000000318 thread T0
    #0 0x4e37e1 in __asan_memcpy
    #1 0x52e251 in queue_remove_head <...>/queue.c:160:9
    #2 0x5276f9 in do_remove_head <...>/qtest.c:273:16
```

PDF 第 7 页的原话解读：编号最小的 `#0` 是**最内层**调用；**第一个属于你代码的帧**才是要找的地方——这里是 `#1`，指向 `queue.c:160:9`，所以错误在 `queue.c` 第 160 行第 9 列。

### 6.2 Agent 自行编写的教学示例

以下代码**均非官方**，只是把 5.5 节的不变量翻译成可读的实现骨架，用于说明「维护路径」具体长什么样。**不要把它当作官方解答**，也不要直接照抄——L0 的评分 trace 覆盖的边界比这里多。

**（1）扩展后的 `queue_t` 与不变量注释**（非官方，仅用于说明概念）

```c
/* 非官方，仅用于说明概念 */
typedef struct {
    list_ele_t *head;   /* 队首；空队列时为 NULL */
    list_ele_t *tail;   /* 队尾；空队列时为 NULL，否则 tail->next == NULL */
    int size;           /* 结点数；空队列时为 0 */
} queue_t;

/*
 * 不变量 I：
 *   (head == NULL) == (tail == NULL) == (size == 0)
 *   且 head != NULL 时 tail->next == NULL，且 size 等于实际结点数。
 * 每个公开函数返回前都必须满足 I。
 */
```

**（2）深拷贝辅助函数**（非官方，仅用于说明概念）

```c
/* 非官方，仅用于说明概念 */
static char *dup_string(const char *s) {
    if (s == NULL) return NULL;              /* 健壮性：NULL 入参不崩 */
    size_t n = strlen(s) + 1;                /* +1 给结尾的 '\0' 留位置 */
    char *copy = malloc(n);
    if (copy == NULL) return NULL;           /* 调用者负责回滚 */
    memcpy(copy, s, n);
    return copy;
}
```

对照 5.4 节的三个硬性约束：这段代码同时满足「深拷贝」「不假设长度上界」「只用 `malloc`」。

**（3）`queue_insert_tail` 的不变量维护**（非官方，仅用于说明概念）

```c
/* 非官方，仅用于说明概念 */
bool queue_insert_tail(queue_t *q, char *s) {
    if (q == NULL) return false;             /* NULL queue */

    char *copy = dup_string(s);
    if (copy == NULL) return false;          /* 字符串分配失败，尚未改动队列 */

    list_ele_t *node = malloc(sizeof(list_ele_t));
    if (node == NULL) { free(copy); return false; }  /* 回滚，避免泄漏 */

    node->value = copy;
    node->next  = NULL;

    if (q->head == NULL) {                   /* 空队列：head 与 tail 同时指向它 */
        q->head = node;
        q->tail = node;
    } else {                                 /* 非空：只动 tail */
        q->tail->next = node;
        q->tail = node;
    }
    q->size++;                               /* 三条路径都必须 +1 */
    return true;
}
```

三个要点：

1. **先分配字符串，再分配结点**。反过来的话，结点分配失败时你已经改动了 `head` / `tail`，回滚更麻烦。
2. **`node->next = NULL` 必须显式写**。`malloc` 不清零。
3. **空队列分支同时改 `head` 与 `tail`**——这正是 5.5 节表格里「破坏 `I`」的那一行。

**（4）`queue_reverse` 的 head/tail 互换**（非官方，仅用于说明概念）

```c
/* 非官方，仅用于说明概念 */
void queue_reverse(queue_t *q) {
    if (q == NULL || q->head == NULL) return;

    list_ele_t *prev = NULL, *cur = q->head, *next;
    while (cur != NULL) {                    /* 循环，不用递归 */
        next = cur->next;
        cur->next = prev;
        prev = cur;
        cur = next;
    }
    list_ele_t *old_head = q->head;          /* 反转后旧的 head 变成 tail */
    q->head = prev;                          /* prev 最终停在旧的 tail 上 */
    q->tail = old_head;                      /* ← 最容易漏的一行 */
    /* size 不变：没有增删结点 */
}
```

**（5）本地替代环境**（非官方，仅用于说明概念）

```bash
# 非官方，仅用于说明概念
mkdir -p ~/cs213/lab0 && cd ~/cs213/lab0
tar --strip=1 -xf /path/to/cprogramminglab-handout.tar
make
./qtest
```

需要的工具：`gcc`、`make`、`python3`（`driver.py` 依赖）、`clang-format`（`make format` 用）、AddressSanitizer（gcc 内置）。

> 待核实：handout 的 `Makefile` 与 `helper.mk` 是针对 shark 机器的 gcc 版本写的。本地较新的 gcc 上可能出现警告升级为错误，必要时在 `CFLAGS` 里加 `-Wno-error`。

---

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| **NULL queue** | **空队列** | 前者 `queue_t *` 本身为 `NULL`（非法入参，要返回失败）；后者指针有效但 `head == NULL`（合法状态） |
| **深拷贝** | **浅拷贝** | 前者为新结点另分配一块内存复制字符串内容；后者只复制指针，两个结点共享同一字符串 → 一个释放后另一个悬空 |
| **`malloc(strlen(s))`** | **`malloc(strlen(s) + 1)`** | 前者漏掉 `'\0'`，`strcpy` 会越界写 1 字节；后者正确 |
| **`queue_insert_head`（LIFO）** | **`queue_insert_tail`（FIFO）** | 前者 O(1) 天然成立（只动 `head`）；后者必须靠 `tail` 字段才能 O(1) |
| **`queue_reverse` 的「反转」** | **`queue_free` 的「清空」** | 前者**不得**分配或释放任何结点，只重排 `next`；后者必须释放每个结点**和**它的字符串 |
| **ASan** | **Valgrind** | 前者是编译期插桩，`qtest` 默认启用；后者是运行时模拟，**两者不能同时用** |
| **`make check`** | **`./driver.py`** | 完全等价，前者只是后者的包装；都调用与 Autolab 相同的评分程序 |
| **代码风格分** | **格式检查** | L0 **没有**风格分，但 `make format`（clang-format）**必须**跑，否则 Autolab 不给分 |

---

## 8. 对应原版讲义

| 材料 | 相对路径 | 页数 | 重点页码 |
|---|---|---|---|
| CProgrammingLab 说明 | `90-原始PDF/15-213/labs/cprogramminglab.pdf` | **8** | 第 1 页（技能清单与日期）、2 页（资源与搜索禁令）、3 页（Autolab 流程、16 个文件、可改范围）、4 页（两个结构体、Figure 1、NULL vs 空队列）、5 页（7 个函数、三条约束、O(1) 与 100 万元素）、6 页（trace 示例、15 条 trace、评分）、7 页（风格、ASan、DWARF）、8 页（提交与反思） |
| 代码包 | `90-原始PDF/15-213/labs/cprogramminglab-handout.tar` | — | 16 项文件；只有 `queue.h` / `queue.c` 可改 |
| 课程总览（lab 定位） | `90-原始PDF/15-213/lectures/01-overview.pdf` | 73 | 第 49 页（8 个 lab 主题）、56 页（Lab0 忠告："If this lab takes you more than 10 hours, please think hard about taking the course."）、57 页（评分政策）、58 页（迟交） |

原始链接：

- 实验说明 <https://www.cs.cmu.edu/~213/labs/cprogramminglab.pdf>（经官方 schedule 页 <https://www.cs.cmu.edu/~213/schedule.html> 下载）
- Lab 机器 <https://www.cs.cmu.edu/~213/labmachines.html>
- 代码风格 <https://www.cs.cmu.edu/~213/codeStyle.html>
- 学术诚信 <https://www.cs.cmu.edu/~213/academicintegrity.html>
- Autolab <https://autolab.andrew.cmu.edu/courses/15213-f26>
- 15-122 链表讲义 <https://www.cs.cmu.edu/~15122/handouts/lectures/10-linkedlist.pdf>
- 15-122 复杂度讲义 <https://www.cs.cmu.edu/~15122/handouts/lectures/05-bigo.pdf>
- man pages <https://man7.org/linux/man-pages/>

> 待人工核对：`cprogramminglab.pdf` 只有 8 页，PDF 页码与正文里的「第 N 页」一致，无跳号。

---

## 9. 对应视频

**未找到官方公开录像。** 15-213 的 lecture / recitation / bootcamp 录像仅对 CMU 校内开放。rec01「How to Succeed in x13 + Datalab」的 slides 在公开材料中可下载（`90-原始PDF/15-213/recitations/rec01-slides.pdf`），但**没有配套录像**。

---

## 10. 本节复习

1. 五项技能：显式内存管理、指针数据结构、字符串、存冗余信息换性能、健壮性（含 NULL）。
2. 两个结构体：`list_ele_t { char *value; list_ele_t *next; }` 与 `queue_t { list_ele_t *head; }`（起始只有一个字段）。
3. 七个函数：`queue_new` / `queue_free` / `queue_insert_head` / `queue_insert_tail` / `queue_remove_head` / `queue_size` / `queue_reverse`。
4. 三条约束：字符串深拷贝（含 `'\0'`）、不假设长度上界、只用 `malloc` / `calloc` / `realloc`。
5. 两个 O(1) 要求靠加 `tail` 与 `size` 字段实现，代价是每条修改路径都要维护不变量。
6. `queue_reverse` 不得分配或释放结点，但**必须交换 `head` 与 `tail`**。
7. 100 万元素测试 → 不能递归。
8. 只改 `queue.h` / `queue.c`；`qtest` 默认启用 ASan；Valgrind 与 ASan 不能同时用。
9. 15 条 trace，每条 6 或 7 分，满分 100；`driver.py` 与 Autolab 同一程序。
10. 提交只接受 `make` 生成的 `cprogramminglab-handin.tar`，每次都要去 Autolab 确认分数。

---

## 11. 自我检查

**Q1.** 某同学的 `queue_insert_tail` 只在非空分支里 `q->size++`，空队列分支忘了加。哪几条 trace 会挂？为什么可能「前面全过、后面突然崩」？

**Q2.** 如果 `queue_t` 只加 `size` 不加 `tail`，`queue_insert_tail` 仍然是 O(n)。这在 15 条 trace 里会以什么形式暴露——是「答案错」还是「超时」？为什么？

**Q3.** `queue_reverse` 的实现里如果不交换 `head` 与 `tail`，但 `size` 不变、`next` 指针都正确重排了，队列的「逻辑内容」其实是对的。请构造一个最小的操作序列，证明这个 bug 会在**后续操作**中暴露。

**Q4.** 为什么本 lab 要求「先 `malloc` 字符串再 `malloc` 结点」，而不是反过来？请从「失败回滚」的角度分析两种顺序的最坏情况。

**Q5.** ASan 报 `READ of size 1025` 出现在 `queue_remove_head` 里。这个数字 1025 提示了什么？为什么它几乎一定指向「固定长度缓冲区」而不是「漏了 `'\0'`」？

<details>
<summary>参考答案</summary>

**A1.** 空队列分支漏 `size++` 意味着：**只要队列曾经从空状态插入过元素，`size` 就永久少 1**。所以凡是先 `new`（空队列）再 `it`（尾部插入）的 trace 都会挂——也就是绝大多数 trace。但为什么可能「前面全过」？因为如果某条 trace 只在**已有元素**的队列上 `it`（先用 `ih` 建了队列），就走的是非空分支，`size` 是对的。于是 bug 只在「空队列首次 `it`」的路径上暴露，表现成「看起来随机地某几条挂」。

**A2.** 是**超时 / 性能分丢失**，不是答案错。`queue_insert_tail` 遍历到尾部再插入，结果完全正确——`head` / `tail` / `size`（如果加了）都对。但每次插入是 O(n)，n 个元素总共 O(n²)。100 万元素时是 10¹² 次结点访问，**远超任何超时阈值**。这正是 lab 把「性能」单列一类 trace 的原因：正确性与复杂度是**两个独立维度**。

**A3.** 最小序列：`new` → `it A` → `it B` → `reverse` → `it C` → `show`。

- 不交换 `tail` 时：反转后链表是 `B → A`，`head = B`，但 `tail` 仍指向 `A`（而 `A->next` 已经是 `NULL`）。
- `it C` 走非空分支：`q->tail->next = node` 即 `A->next = C`，然后 `q->tail = C`。
- 此时链表是 `B → A → C`，而正确结果应该是 `B → A` 后面接 `C`——看起来对了？

关键在于 `reverse` 之后 `A->next` 是 `NULL`，`A` 恰好就是新的尾部，所以这个特定序列**碰巧不暴露**。真正暴露的是**连续两次 `reverse`**：第一次反转后 `tail` 指向 `A`，第二次反转遍历仍然从 `head` 开始，结果正确，但 `tail` 又被设为「旧的 head」——它指向的是第一次反转后的 `head`，链条错位。更直接的暴露方式是 `reverse` 后立刻 `remove_head` 直到空：`remove_head` 会检查 `q->head == NULL` 来把 `tail` 置 `NULL`，这时 `tail` 的旧值被覆盖，bug 被掩盖；但如果 trace 在 `reverse` 之后直接 `show` 并检查 `tail` 相关的不变量（某些 trace 会打印内部状态），就会暴露。**结论**：这个 bug 的隐蔽性正是它危险的原因——它可能通过大部分 trace，只在「`reverse` 后接 `insert_tail` 且随后 `reverse`」这类组合上崩。

**A4.** 两种顺序的最坏情况：

- **先字符串后结点**（推荐）：字符串分配成功、结点分配失败 → `free(copy)` 即可回滚，队列**完全未被改动**，不变量 `I` 保持。
- **先结点后字符串**：结点分配成功、字符串分配失败 → 你必须 `free(node)` 并确保没有把它挂进链表。如果代码是「先挂进链表再拷字符串」，那就必须**从链表里摘下来**再释放，这在单链表里需要知道前驱——代码复杂度陡增，且容易漏。

所以顺序的本质是「让失败点尽可能早、让回滚尽可能局部」。

**A5.** `READ of size 1025` 说明代码要读 **1025 个连续字节**，这是一个**写死的常量**（1024 + 1 是很典型的缓冲区大小）。如果是漏了 `'\0'`，读的长度会是 `strlen(s)` 或 `strlen(s)+1`——一个**随输入变化**的值，不会是整齐的 1025。所以这个数字几乎一定来自 `char buf[1025]` 或 `strncpy(dst, src, 1025)` 之类的固定长度缓冲区，而队列里的字符串是**变长**的，一旦实际字符串短于 1024，读就会越界。这也解释了 PDF 第 2 页为什么专门警告 `strncpy` 的截断行为。

</details>

---

## 12. 进一步学习

- Lab 总览（全部 8 个 lab 的日期与获取方式）：[[20-CMU-15-213/03-Lab实验笔记/00-Lab总览|15-213 Lab 总览]]
- 受限 Lab 说明（L1–L6 的合法替代路径）：[[20-CMU-15-213/03-Lab实验笔记/02-受限Lab说明|受限 Lab 说明]]
- 下一站——堆与动态内存分配：[[20-CMU-15-213/02-中文学习笔记/15-213-13-Dynamic-Memory-Allocation-Basic|L13 Dynamic Memory Allocation: Basic]]
- 进阶——显式空闲链表与分离适配：[[20-CMU-15-213/02-中文学习笔记/15-213-14-Dynamic-Memory-Allocation-Advanced|L14 Dynamic Memory Allocation: Advanced]]
- 调试方法（gdb 与 ASan 的完整讲解）：[[20-CMU-15-213/02-中文学习笔记/15-213-08-Design-and-Debugging|L08 Design and Debugging]]
- 课程总览：[[20-CMU-15-213/00-课程总览|CMU 15-213 - 课程总览]]
- 学习进度：[[20-CMU-15-213/04-学习进度|CMU 15-213 - 学习进度]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Linked List、Pointer、Memory Leak、Heap）
- 原始材料：`90-原始PDF/15-213/labs/cprogramminglab.pdf`、`90-原始PDF/15-213/labs/cprogramminglab-handout.tar`
