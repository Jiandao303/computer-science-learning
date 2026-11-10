---
course: CMU 15-213
course_name: Introduction to Computer Systems
semester: Fall 2026
lecture_id: L14
topic: Dynamic Memory Allocation Advanced
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-213
  - 动态内存分配
  - malloc
  - 分离适配
  - 内存错误
---

# 动态内存分配：进阶（Dynamic Memory Allocation: Advanced Concepts）

## 1. 本节学习目标

- 能画出显式空闲链表（explicit free list）的结构，说明它与隐式链表在时间与空间上的取舍。
- 能说出三种插入策略（LIFO、FIFO、地址有序）的优劣，并描述 LIFO 下四种 `free` 情形的指针操作。
- 能解释分离适配（segregated fit）为什么能同时提高吞吐量与利用率，以及 size class 的设计方式。
- 能识别讲义列出的七类内存相关错误，并说出每一类的典型代码。
- 能用 gdb、valgrind、一致性检查器、`MALLOC_CHECK_` 定位内存错误。

## 2. 前置知识

- [[15-213-13-Dynamic-Memory-Allocation-Basic]]：header 的 size|a 编码、隐式链表遍历、splitting、boundary tag、四种合并情形、dummy 哨兵。
- 双向链表（doubly-linked list）的插入与删除操作。
- C 的运算符优先级（讲义第 34 页专门贴了 K&R 的表）。
- 基本的调试工具概念：gdb 断点、valgrind。

## 3. 核心概念

- **Explicit Free List（显式空闲链表）**：只把**空闲块**串成双向链表，指针存在空闲块的 payload 里。
- **Splicing（摘链/插链）**：把块从链表中摘下或插入链表，需要改前后邻居的指针。
- **Insertion Policy（插入策略）**：新释放的块放到链表哪里——LIFO（头插）、FIFO（尾插）、地址有序（address-ordered）。
- **Segregated Free List / Seglist（分离空闲链表）**：按大小分级的多个空闲链表，每个 size class 一条。
- **Size Class（大小类）**：一组大小相近的块共用一条链表，如 16、32–48、64–∞。
- **Approximate Best Fit（近似最佳适配）**：在合适的 size class 里 first fit，效果接近全堆 best fit。
- **Memory Leak（内存泄漏）**：分配了块但永不释放，堆持续增长。
- **Dangling Pointer（悬垂指针）**：指向已被 `free` 的块，继续读写会破坏堆或读到脏数据。
- **Double Free（重复释放）**：对同一块调用两次 `free`，会破坏空闲链表。
- **Buffer Overflow（缓冲区溢出）**：写超出分配边界，覆盖相邻块的 header 或数据。
- **Valgrind**：二进制翻译器（binary translator），重写可执行文件的 text 段，在运行时逐条检查每次内存引用。

## 4. 通俗理解

上一讲的隐式链表有个硬伤：`malloc` 要扫描**所有**块（包括已分配的），程序跑久了块数上万，每次分配都走一遍链表，慢得不可接受。

显式链表的第一层改进很自然：既然只需要在**空闲块**里找地方，为什么还要走已分配的块？于是只把空闲块串起来。代价是空闲块里要存两个指针（`prev`、`next`）——反正空闲块的 payload 本来也没人用。

第二层改进是分离链表：不再维护一条大链表，而是按大小分成若干条。要 40 字节就去“32–48”那一档找，找不到再去更大的档。这就像图书馆不再把所有书混在一个架子上，而是按开本大小分架——找起来快得多，而且顺手拿到的书尺寸也最接近需求。

第三层不是优化而是避坑：`malloc`/`free` 用错了不会立刻报错，而是在几百万条指令之后以莫名其妙的方式崩溃。讲义最后三分之一全在讲这些坑，因为**会用 malloc 比会实现 malloc 更重要**。

## 5. 原理与推导

### 5.1 显式空闲链表的结构

讲义第 9 页：

```
已分配块：  [ size | a=1 ][ payload ............ ]
空闲块：    [ size | a=0 ][ next | prev | 剩余空间 ][ size | a=0 ]
                           ^^^^^^^^^^^^
                           存在 payload 里的两个指针
```

要点：

- 仍需 **boundary tag**（header + footer），因为合并要按**内存顺序**找相邻块，而链表的顺序是任意的。
- `next`/`prev` 指向的是**链表中的**前后空闲块，与内存地址相邻无关。
- 代价：每个空闲块多 2 个字（16 字节）。讲义第 17 页提问“这会增加内部碎片吗？”——答案是不会，因为这两个字只存在于空闲块中，而空闲块本来就不承载用户数据；但它会增加**最小块大小**，间接影响小请求的利用率。

第 10 页的图说明“逻辑顺序”与“物理顺序”可以完全不同：链表 A → B → C，而内存里可能是 A、C、B 的排列。

### 5.2 从显式链表分配

第 11 页：流程与隐式链表相同（找块 → 标记已分配 → 分割），差别在于：

- 找到的块必须先从链表中**摘下**（splice out）。
- 若发生分割，剩余部分要**插回**合适的链表位置。

摘链是标准的双向链表删除：

```c
/* 非官方示例 */
static void remove_from_list(block_t *bp) {
    if (bp->prev) bp->prev->next = bp->next;
    else          free_list_head = bp->next;
    if (bp->next) bp->next->prev = bp->prev;
}
```

### 5.3 三种插入策略

讲义第 12 页：

| 策略 | 做法 | 优点 | 缺点 |
|---|---|---|---|
| LIFO | 插到链表头 | 简单、常数时间 | 碎片比地址有序差 |
| FIFO | 插到链表尾 | 简单、常数时间 | 同上 |
| Address-ordered | 按地址顺序插入 | 研究显示碎片最少 | 插入需要搜索，O(n) |

为什么地址有序能减少碎片？因为按地址排列后，链表顺序与内存顺序一致，相邻的空闲块在链表中也相邻，合并后链表结构更“紧凑”，搜索时也更容易命中大块。代价是每次 `free` 要线性搜索插入点。

### 5.4 LIFO 下的四种 free 情形

讲义第 13–16 页，以“释放块 + 头插”为主线：

| 情形 | 前块 | 后块 | 操作 |
|---|---|---|---|
| 1 | 已分配 | 已分配 | 直接头插 |
| 2 | 已分配 | 空闲 | 把后块从链表摘下，与当前块合并，新块头插 |
| 3 | 空闲 | 已分配 | 把前块从链表摘下，与当前块合并，新块头插 |
| 4 | 空闲 | 空闲 | 把前后两块都摘下，三块合并，新块头插 |

与隐式链表的区别只有一点：**合并前必须先把被合并的空闲块从链表中摘除**。隐式链表不需要，因为它根本没有链表指针。

这是 malloclab 里最容易写错的地方：摘链的顺序、更新头指针的时机、合并后 size 的写入位置，任何一步错了都会在后续操作中崩溃，且现场往往已经离 bug 很远。

### 5.5 显式链表的评价

讲义第 17 页：

- **分配**：O(空闲块数) 而非 O(总块数)。内存大部分被占用时优势极大（空闲块少）。
- **实现**更复杂：需要 splice 操作。
- **空间**：每个空闲块多 2 个字。
- 仍然没有解决“空闲块很多时依然线性”的问题——这就引出分离链表。

### 5.6 分离适配

讲义第 19–22 页。

**结构**：一个空闲链表数组，每个元素对应一个 size class。

常见的分级方式：

- 小尺寸逐个一类：16、32、48、64……
- 到某个阈值后按 2 的幂分档：[2^i + 1, 2^(i+1)]，如 65–128、129–256……
- **最后一档必须无上界**（直到 2^64），否则超大请求无处可去。

**分配流程（第 20–21 页）**：

1. 计算请求大小 n，定位到对应的 size class。
2. 在该链表中 first fit 找 m ≥ n 的块。
3. 找到：分割，把剩余碎片放回**它所属的** size class（注意不是原来那条）。
4. 没找到：去下一个更大的 class 找，重复。
5. 所有 class 都没有：调 `sbrk` 向 OS 要新堆空间，从中分配 n 字节，剩余部分作为一个大空闲块放进对应 class。

**释放流程（第 22 页）**：合并相邻空闲块（仍需要 boundary tag），然后把结果放进对应的 size class。

**两个优势**（第 22 页，对比同样用 first fit 的非分离分配器）：

1. **更高吞吐量**：按 2 的幂分级时，查找是 O(log n) 而不是 O(n)。
2. **更好的内存利用率**：在分离链表上做 first fit，近似于在全堆做 best fit。极端情况——每个块大小单独一类——就**等价于** best fit。

第二点的直觉：你去 32–48 这一档找，拿到的块最多比需求大 16 字节；而全堆 first fit 可能给你一个 4KB 的块。分级本身就是一种“预先缩小搜索范围”的最佳适配。

### 5.7 参考资料

讲义第 23 页列出三份：

- Knuth, TAOCP vol 1, 3rd ed., 1997：动态存储分配的经典文献。
- Wilson et al., “Dynamic Storage Allocation: A Survey and Critical Review”, 1995：最全面的综述，可在 CS:APP 学生站点获取。
- Railing et al., “Implementing Malloc: Students and Systems Programming”, SIGCSE'18：专门讨论 malloclab 的教学论文。

### 5.8 七类内存错误

讲义第 26 页列出清单，第 27–40 页逐一举例。

**1. 解引用坏指针（第 27 页）**

```c
int val;
scanf("%d", val);      /* 应为 &val */
```

`scanf` 会把读到的整数当作地址写入。讲义注释很传神：“Crash here … if you're lucky”——运气好立刻崩溃，运气不好静默改掉某个变量，几小时后才出问题。

**2. 读未初始化内存（第 28 页）**

```c
int *y = malloc(N*sizeof(int));
for (i=0; i<N; i++)
    for (j=0; j<N; j++)
        y[i] += A[i][j]*x[j];    /* y[i] 初值是垃圾 */
```

`malloc` 不清零。修法：用 `calloc`，或先 `memset`，或把内层改成赋值而非累加。

**3. 覆盖内存（第 29–33 页）**，有五个子类：

- **分配大小错误**（第 29 页）：

```c
int **p;
p = malloc(N*sizeof(int));       /* 应为 sizeof(int *)，64 位上小了一半 */
for (i=0; i<N; i++)
    p[i] = malloc(M*sizeof(int));
```

- **off-by-one（第 30 页）**：

```c
p = malloc(N*sizeof(int *));
for (i=0; i<=N; i++)             /* 应为 i < N */
    p[i] = malloc(M*sizeof(int));

char *p = malloc(strlen(s));     /* 应为 strlen(s)+1，漏掉 '\0' */
strcpy(p, s);
```

- **不检查字符串长度（第 31 页）**：

```c
char s[8];
gets(s);                          /* 输入 "123456789" 就越界了 */
```

讲义指出这是经典缓冲区溢出攻击的基础。

- **误解指针算术（第 32 页）**：

```c
int *search(int *p, int val) {
    while (p && *p != val)
        p += sizeof(int);          /* 应为 p++，指针算术已按元素大小缩放 */
    return p;
}
```

`p += sizeof(int)` 在 int 为 4 字节时每次跳 16 字节，既漏元素又可能越界。

- **引用指针而非所指对象（第 33、35 页）**：

```c
*size--;        /* 等价于 *(size--)，递减的是指针本身！ */
(*size)--;      /* 这才是递减所指的整数 */
```

讲义第 34 页贴出 K&R 的运算符优先级表解释原因：后缀 `--` 优先级高于一元 `*`。

**4. 引用不存在的变量（第 36 页）**

```c
int *foo() {
    int val;
    return &val;      /* val 在函数返回后失效 */
}
```

栈帧被回收，返回的指针指向一块随时会被复用的内存。

**5. 重复释放（第 37 页）**

```c
x = malloc(N*sizeof(int));
free(x);
y = malloc(M*sizeof(int));   /* 可能复用了 x 的空间 */
free(x);                     /* 再次释放 x：破坏 y 甚至链表结构 */
```

讲义评语：“Nasty!”。

**6. 引用已释放的块（第 38 页）**

```c
x = malloc(N*sizeof(int));
free(x);
y = malloc(M*sizeof(int));
for (i=0; i<M; i++)
    y[i] = x[i]++;           /* x 已失效，且可能被 y 占用 */
```

讲义评语：“Evil!”——这是悬垂指针，读写都错，而且往往读到的“像是合理数据”。

**7. 忘记释放（第 39–40 页）**

```c
foo() {
    int *x = malloc(N*sizeof(int));
    ...
    return;                   /* x 泄漏 */
}
```

更隐蔽的是**只释放数据结构的一部分**（第 40 页）：释放了链表头，其余节点全部泄漏。讲义评语：“Slow, long-term killer!”——不会立刻出错，但长时间运行的服务会逐渐耗尽内存。

### 5.9 调试手段

讲义第 41 页：

| 工具 | 擅长 | 局限 |
|---|---|---|
| gdb | 坏指针解引用导致的崩溃 | 其它内存错误很难发现 |
| 数据结构一致性检查器 | 静默运行，只在出错时打印；可当探针逐步缩小范围 | 需要自己写 |
| valgrind | 重写 text 段，运行时逐条检查每次引用；能抓坏指针、越界写、引用已释放块 | 慢（10–50 倍） |
| glibc 自带检查 | `setenv MALLOC_CHECK_ 3` | 只覆盖堆结构破坏的一部分 |

一致性检查器的思路值得记住：写一个 `check_heap()`，遍历整个堆，验证每个 header 的 size 合法、相邻块不都是空闲（未合并）、链表指针自洽，然后在每个 `malloc`/`free` 前后调用它。一旦某次操作后检查失败，bug 就在那一步——这是 malloclab 调试的标准手法。

### 5.10 实现技巧：循环双向链表

讲义第 43 页（附加页）：

用**循环**双向链表，可以用同一套数据结构支持多种策略：

- **first fit vs next fit**：free pointer 固定不动 = first fit；每次搜索后把 free pointer 移到搜索结束处 = next fit。
- **LIFO vs FIFO**：插入到 free pointer 的 `next` = LIFO；插入到 `prev` = FIFO。

这个技巧的价值在于：malloclab 里想比较几种策略时，不必重写数据结构，只改一个指针的移动方式即可。

## 6. 代码示例

### 6.1 官方课程代码

**空闲块结构（14-malloc-advanced.pdf 第 9 页）**：

```
Free block:  [ Size | a=0 ][ Next | Prev | ... ][ Size | a=0 ]
Allocated:   [ Size | a=1 ][ Payload ............ ]
```

**scanf 的经典错误（14-malloc-advanced.pdf 第 27 页）**：

```c
int val;
scanf("%d", val);      /* bug: 缺 & */
```

**指针算术错误（14-malloc-advanced.pdf 第 32 页）**：

```c
int *search(int *p, int val) {
    while (p && *p != val)
        p += sizeof(int);      /* bug: 应 p++ */
    return p;
}
```

**优先级错误（14-malloc-advanced.pdf 第 33、35 页）**：

```c
*size--;      /* 等价 *(size--) */
(*size)--;    /* 正确写法 */
```

**分离链表分配流程（14-malloc-advanced.pdf 第 20–21 页）**：以 `malloc(40)` 为例，先查 32–48 类，没有再查 64–∞ 类，仍没有则 `sbrk`。

**循环双向链表技巧（14-malloc-advanced.pdf 第 43 页）**：free pointer 的位置决定 first/next fit，插入到 next/prev 决定 LIFO/FIFO。

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

显式链表的摘链/插链（双向链表标准操作，配合 boundary tag）：

```c
/* 非官方示例：显式空闲链表的插入与删除 */
#include <stddef.h>
#include <stdint.h>

typedef struct free_block {
    size_t size_alloc;          /* header: size | a */
    struct free_block *next;
    struct free_block *prev;
    /* ... payload 剩余空间 ... */
} free_block_t;

static free_block_t *free_head = NULL;

/* LIFO 头插 */
static void insert_lifo(free_block_t *bp) {
    bp->prev = NULL;
    bp->next = free_head;
    if (free_head) free_head->prev = bp;
    free_head = bp;
}

/* 从链表中摘除（O(1)，不需要搜索） */
static void splice_out(free_block_t *bp) {
    if (bp->prev) bp->prev->next = bp->next;
    else          free_head = bp->next;
    if (bp->next) bp->next->prev = bp->prev;
}

/* 地址有序插入：需要线性搜索 */
static void insert_address_ordered(free_block_t *bp) {
    free_block_t *cur = free_head, *prev = NULL;
    while (cur && cur < bp) { prev = cur; cur = cur->next; }
    bp->prev = prev;
    bp->next = cur;
    if (prev) prev->next = bp; else free_head = bp;
    if (cur)  cur->prev = bp;
}
```

分离链表的 size class 定位（按 2 的幂分级）：

```c
/* 非官方示例：把请求大小映射到 size class 下标 */
#include <stdint.h>

#define NUM_CLASSES 16

/* 16,32,48,64 逐个一类；之后按 2 的幂：[65,128],[129,256],... */
static int size_to_class(size_t n) {
    if (n <= 64) return (int)((n + 15) / 16) - 1;   /* 0..3 */
    int cls = 4;
    size_t bound = 128;
    while (n > bound && cls < NUM_CLASSES - 1) {
        bound <<= 1;
        cls++;
    }
    return cls;                                     /* 最后一类无上界 */
}
```

分配时从 `size_to_class(n)` 开始向后找第一条非空链表，找到就 first fit；这正是“近似 best fit”的实现。

一个能抓住越界的自检函数（malloclab 常用手法）：

```c
/* 非官方示例：堆一致性检查，出错时打印并 abort */
#include <stdio.h>
#include <stdlib.h>

static void check_heap(void) {
    char *bp = heap_start;
    int prev_free = 0;
    while (bp < heap_end) {
        size_t size = get_size(bp);
        int alloc = (int)get_alloc(bp);
        if (size == 0 || size % 16 != 0) {
            fprintf(stderr, "bad size %zu at %p\n", size, (void *)bp);
            abort();
        }
        if (!alloc && prev_free) {
            fprintf(stderr, "adjacent free blocks at %p\n", (void *)bp);
            abort();          /* 应该已合并 */
        }
        prev_free = !alloc;
        bp += size;
    }
    if (bp != heap_end) {
        fprintf(stderr, "heap walk overran: %p != %p\n", (void *)bp, (void *)heap_end);
        abort();
    }
}
```

在每个 `mm_malloc`/`mm_free` 的开头和结尾调用它，一旦某次操作破坏了结构，立刻就能定位到那一次调用。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| 隐式链表 | 显式链表 | 前者遍历所有块（靠 size 算下一个），后者只串空闲块（存指针） |
| 链表顺序 | 内存顺序 | 显式链表中二者可以完全不同；boundary tag 保证按**内存顺序**合并仍然 O(1) |
| LIFO 插入 | 地址有序插入 | 前者 O(1) 但碎片多；后者 O(n) 但碎片少 |
| 分离链表 | 分级索引 | 分离链表是“多条空闲链表”；它带来的近似 best fit 是副作用，不是定义 |
| `*size--` | `(*size)--` | 前者递减指针，后者递减所指整数；后缀 `--` 优先级更高 |
| 内存泄漏 | 悬垂指针 | 前者是不释放，堆越来越大；后者是释放后还用，读到脏数据或破坏堆 |
| valgrind | gdb | 前者逐条检查所有内存引用，能抓越界与悬垂；后者主要定位崩溃点 |

## 8. 对应原版讲义

- PDF 相对路径：`90-原始PDF/15-213/lectures/14-malloc-advanced.pdf`
- 总页数：43 页
- 重点页码：
  - 课程事务（作业延期、期中范围）：第 3 页
  - 四种记录空闲块的方法：第 5、8 页
  - 隐式链表总结：第 6 页
  - 显式空闲链表结构：第 9–10 页
  - 从显式链表分配：第 11 页
  - 三种插入策略：第 12 页
  - LIFO 的四种 free 情形：第 13–16 页
  - 显式链表评价：第 17 页
  - 分离链表与 size class：第 19 页
  - 分离链表的分配与释放流程：第 20–22 页
  - 两个优势（吞吐与利用率）：第 22 页
  - 参考文献：第 23 页
  - 七类内存错误清单：第 26 页
  - 解引用坏指针：第 27 页
  - 读未初始化内存：第 28 页
  - 覆盖内存（五种）：第 29–33 页
  - 运算符优先级表：第 34 页
  - 引用不存在变量：第 36 页
  - 重复释放：第 37 页
  - 引用已释放块：第 38 页
  - 内存泄漏：第 39–40 页
  - 调试工具：第 41 页
  - 循环双向链表技巧（附加页）：第 43 页
- 原始链接：https://www.cs.cmu.edu/~213/lectures/14-malloc-advanced.pdf

## 9. 对应视频

未找到官方公开录像。

## 10. 本节复习

- 显式链表只串空闲块，指针存在 payload 里，仍需 boundary tag 做内存顺序合并。
- 分配 O(空闲块数)，摘链/插链是双向链表标准操作。
- 三种插入策略：LIFO/FIFO 常数时间但碎片多，地址有序 O(n) 但碎片少。
- LIFO 四种 free 情形：合并前先把邻居摘链。
- 分离链表：按 size class 分多条链表，分配时从对应档往后找，找不到就 `sbrk`。
- 分离链表两大优势：O(log n) 查找 + 近似 best fit。
- 七类内存错误：坏指针、未初始化、覆盖（五种）、不存在变量、重复释放、悬垂指针、泄漏。
- 工具：gdb、一致性检查器、valgrind、`MALLOC_CHECK_`。
- 循环双向链表 + free pointer 可同时支持 first/next fit 与 LIFO/FIFO。

## 11. 自我检查

1. 显式空闲链表相比隐式链表，`malloc` 的复杂度从 O(总块数) 降到 O(空闲块数)。在什么场景下这个改进几乎无感？什么场景下提升巨大？
2. 为什么显式链表在合并前必须先把相邻空闲块从链表中摘除，而隐式链表不需要？
3. 分离链表中，若 `malloc(40)` 在 32–48 类里找到 48 字节的块并分割，剩下的 8 字节该放到哪里？为什么？
4. 下面这段代码有几个 bug？分别属于讲义中的哪一类？
   ```c
   char *dup(const char *s) {
       char *p = malloc(strlen(s));
       strcpy(p, s);
       return p;
   }
   ```
5. 为什么说“每个块单独一个 size class 就等价于 best fit”？

<details>
<summary>参考答案</summary>

1. 当堆中**大部分块都是空闲**时，空闲块数接近总块数，改进几乎无感。当程序长期运行、大部分内存已被占用（空闲块很少）时，隐式链表仍要走遍成千上万个已分配块，而显式链表只需走少数几个空闲块，提升巨大——这正是讲义第 17 页说的“much faster when most of the memory is full”。

2. 显式链表的链表节点就是空闲块本身。若直接合并两个相邻空闲块而不摘链，被吞并的那个块的 `next`/`prev` 指针会残留在合并后的块内部，链表里出现一个指向已不存在的块的节点，后续遍历会读到垃圾。隐式链表没有链表指针，合并只是改 size 字段，所以无需摘链。

3. 8 字节太小，连一个 header（8 字节）+ footer（8 字节）都放不下，根本无法构成合法块。所以分割条件应是“剩余 ≥ 最小块大小”，此处不分割，直接把整个 48 字节块分配出去（内部碎片 8 字节）。若剩余足够（如请求 32、块 64、剩 32），则剩余块应放进**32 对应的** size class，而不是原来的 32–48 类（32 恰好是独立的一类）。

4. 两个 bug：(a) `malloc(strlen(s))` 少分配 1 字节给结尾的 `'\0'`，属于“覆盖内存”中的 off-by-one / 不检查字符串长度；(b) `malloc` 返回值未检查是否为 `NULL`，失败时 `strcpy` 会解引用空指针，属于“解引用坏指针”。正确写法是 `malloc(strlen(s) + 1)` 并检查返回值。

5. 若每个块大小单独一类，那么请求 n 时只能去“恰好 n”的那一类找，找到的块大小必然等于 n（没有更大的块会在这一类里），于是既没有剩余可分割，也不会选到比 n 大的块——这正是 best fit 的定义（选剩余最少的够大块）。所以极端情况下分离链表退化为 best fit。

</details>

## 12. 进一步学习

- 下一讲：[[15-213-15-Code-Optimization]]
- 前一讲：[[15-213-13-Dynamic-Memory-Allocation-Basic]]
- 相关实验：[[00-Lab总览]]（Malloc Lab 的评分就是吞吐量 + 利用率两项，本节所有策略都在那里落地）
- 课程总览：[[20-CMU-15-213/00-课程总览|CMU 15-213 - 课程总览]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Throughput、Linking）
- CSAPP 第 3 版 9.9.13–9.9.14 与 9.11 节；9.11 的 “Memory-Related Perils and Pitfalls” 与本节 5.8 逐条对应，建议对照书中代码重读一遍。
