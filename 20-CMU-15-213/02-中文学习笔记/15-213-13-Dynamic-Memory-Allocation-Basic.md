---
course: CMU 15-213
course_name: Introduction to Computer Systems
semester: Fall 2026
lecture_id: L13
topic: Dynamic Memory Allocation Basic
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-213
  - 动态内存分配
  - malloc
  - 空闲链表
  - 碎片
---

# 动态内存分配：基本概念（Dynamic Memory Allocation: Basic Concepts）

## 1. 本节学习目标

- 说清显式分配器（explicit allocator）与隐式分配器（implicit allocator）的区别，以及为什么 C 的 `malloc`/`free` 属于前者。
- 能用吞吐量（throughput）与峰值内存利用率两个指标评价分配器，并算出 overhead。
- 能区分内部碎片（internal fragmentation）与外部碎片（external fragmentation），说明为什么前者可测、后者不可测。
- 能在隐式空闲链表（implicit free list）上实现 `find_fit`、`split_block`、`coalesce_block`。
- 能画出 boundary tag（边界标记）的结构，并说明它如何让合并（coalescing）做到 O(1)。
- 能说明把 footer 从已分配块中去掉、改用 2 位状态标记的优化。

## 2. 前置知识

- [[15-213-12-Virtual-Memory-Details]]：堆（heap）是虚拟地址空间中 `brk` 之上的一段区域，`sbrk` 可以移动它。
- [[15-213-02-Bits-Bytes-and-Integers]]：位运算（掩码、清低位）、16 字节对齐意味着低 4 位恒为 0。
- [[15-213-03-Machine-Programming-I-Basics]]：指针算术、结构体布局、`offsetof`。
- C 语言：`void *`、`size_t`、`sizeof`、零长数组（flexible array member 的雏形）。

## 3. 核心概念

- **Dynamic Memory Allocator（动态内存分配器）**：管理进程虚拟内存中一块称为堆的区域，按需把块借给应用、回收应用归还的块。
- **Heap（堆）**：位于 `.bss` 之上、由 `brk`（the break）标定上界的一段虚拟内存，`malloc` 从中取内存。
- **Block（块）**：堆被划分成的变长单元，要么已分配（allocated）要么空闲（free）。
- **Explicit Allocator（显式分配器）**：应用自己调用分配与释放，如 C 的 `malloc`/`free`、C++ 的 `new`/`delete`。
- **Implicit Allocator（隐式分配器）**：应用只分配不释放，由运行时自动回收，如 Java 的垃圾回收（garbage collection）。
- **Throughput（吞吐量）**：单位时间内完成的请求数，例如 10 秒内 5000 次 `malloc` + 5000 次 `free` → 1000 次/秒。
- **Aggregate Payload（累计有效载荷）P_k**：截至第 k 次请求时所有已分配块的有效载荷之和。
- **Peak Aggregate Payload（峰值累计载荷）**：序列过程中 P_k 的最大值。
- **Heap Size（堆大小）H_k**：当前堆的字节数，假设只增不减。
- **Overhead（开销）**：O_k = H_k / max_{i≤k} P_i − 1.0，即堆中未用于程序数据的比例。
- **Internal Fragmentation（内部碎片）**：分配出去的块比请求的载荷大，多出的部分在块内部浪费。
- **External Fragmentation（外部碎片）**：堆中空闲总量够，但没有单个空闲块足够大，请求无法满足。
- **Implicit Free List（隐式空闲链表）**：不额外维护指针，靠每个块头部的 size 字段依次跳转，把所有块串成一条“链”。
- **Header（头部）**：块开头的一个字，存块大小与分配标志位。
- **Footer / Boundary Tag（脚部/边界标记）**：把头部复制到块末尾，使相邻块可以反向找到前一个块。
- **Splitting（分割）**：空闲块比请求大时，切出一部分用于分配，剩余部分变成新的空闲块。
- **Coalescing（合并）**：`free` 时把相邻的空闲块拼成一个大块，避免假碎片（false fragmentation）。
- **Placement Policy（放置策略）**：first fit、next fit、best fit，决定从哪个空闲块分配。

## 4. 通俗理解

### 4.1 为什么需要它

前面几讲的内存都是“编译期或运行期一开始就定好”的：全局变量在 `.data`/`.bss`，局部变量在栈上。但很多数据结构的大小只有运行时才知道——读一个文件要先知道文件多大、链表要按需插入节点。栈上的内存随函数返回自动消失，无法长期持有；于是需要一个可以随时借、随时还的内存池，这就是堆。

比喻：堆是一块空地，分配器是物业。你申请 40 平米（`malloc(40)`），物业从空地里划一块给你，并在门口挂个牌子写“这块 48 平米，已占用”。你退租（`free`）时把牌子翻成“空闲”。物业的难题是：空地会被切成很多小块，如何记录每块多大、谁在用、退租后能不能和邻居并成一块。

### 4.2 两个互相冲突的目标

- 想快（高吞吐）：别搜太久、别做太多簿记 → 简单的策略。
- 想省（高利用率）：尽量别浪费一个字节 → 复杂的搜索与合并。

这两个目标天然冲突，所以真实分配器都是折中。理解这一点，后面所有策略选择就都有了依据。

### 4.3 碎片的直觉

- **内部碎片**像买鞋：你穿 41 码，店里只有 42 码，多出来的那半码在你脚上浪费着，别人也用不了。
- **外部碎片**像停车：停车场总共还有 3 个空位，但每个只够停摩托，你的 SUV 停不进去。

## 5. 原理与推导

### 5.1 malloc 包的接口

讲义第 6 页：

```c
void *malloc(size_t size);
void free(void *p);
void *calloc(size_t nmemb, size_t size);   /* 分配并清零 */
void *realloc(void *p, size_t size);       /* 改变已分配块大小 */
void *sbrk(intptr_t incr);                 /* 分配器内部用来伸缩堆 */
```

关键约定：

- 成功时返回**至少** size 字节、在 x86-64 上 **16 字节对齐**的块指针。
- `size == 0` 时返回 `NULL`（或一个可 `free` 的唯一指针，取决于实现）。
- 失败时返回 `NULL` 并设置 `errno`。
- `free(p)` 的 `p` 必须来自之前的 `malloc`/`calloc`/`realloc`，否则行为未定义。

### 5.2 显式分配器的约束

讲义第 10 页列出五条，每条都直接限制了算法设计：

| 约束 | 后果 |
|---|---|
| 不能控制请求的数量与大小 | 必须能处理任意序列 |
| 必须立即响应，不能重排或缓冲 | 不能像 GC 那样延迟处理 |
| 只能从空闲内存里分配 | 不能覆盖已分配块 |
| 必须满足对齐要求（x86-64 为 16 字节） | 块大小必须是 16 的倍数，低 4 位可用作标志 |
| 只能操作空闲内存，**不能移动已分配块** | 不能做压缩（compaction），因此外部碎片无法彻底消除 |

最后一条最要命：C 的指针语义要求块地址稳定，一旦允许移动，所有指向该块的指针都得更新，语言层面做不到。所以外部碎片只能缓解、不能根治。

### 5.3 性能指标

**吞吐量**（第 11 页）：单位时间完成的请求数。简单直接，但只看它会让分配器倾向于“什么都不做”。

**内存利用率**（第 12 页）：用 overhead 衡量。

```
P_k      = 第 k 次请求后所有已分配块的 payload 之和
peak     = max_{i≤k} P_i
H_k      = 当前堆大小（只增不减）
O_k      = H_k / peak − 1.0
```

例：某 benchmark 峰值 payload 为 90,036 字节（讲义第 13 页 syn-array-short 的 Peak 列），若此时堆已增长到 100,000 字节，则 overhead = 100000/90036 − 1 ≈ 11.1%。

讲义第 18、20 页用同一 benchmark 给出对比：

| 情形 | overhead |
|---|---|
| 仅内部碎片（数据 + 对齐填充） | 1.5%（理论下界，实际达不到） |
| Perfect fit | 1.6% |
| Best fit | 8.3% |
| First fit | 11.9% |
| Next fit | 21.6% |

这组数字很说明问题：**放置策略的选择可以让开销差三倍**。

### 5.4 内部碎片

成因（第 17 页）：

1. 维护堆数据结构的开销（每个块的 header）。
2. 对齐填充（16 字节对齐的 padding）。
3. 显式策略决策（例如为了满足小请求返回一个大块）。

特点：**只取决于过去的请求模式**，因此可以在分配时精确计算，容易测量。

### 5.5 外部碎片

成因（第 19 页）：堆中空闲总量足够，但没有单个空闲块够大。

例：`p1 = malloc(32)`、`p2 = malloc(40)`、`p3 = malloc(48)`、`free(p2)`，此时空闲总量有 40 多字节但被切成一段；再来 `p4 = malloc(64)` 就失败。

特点：**取决于未来的请求模式**，无法在当下精确度量——这是它与内部碎片的本质区别。

### 5.6 隐式空闲链表的结构

**如何知道 free 要释放多少**（第 22 页）：在块前面放一个字，记录块大小（含 header）。

```
+----------------+---------------------------+
| header (8B)    | payload ...    padding    |
| size | a       |                           |
+----------------+---------------------------+
```

**如何同时记录大小和分配状态**（第 25 页）：块按 16 字节对齐，所以 size 的低 4 位恒为 0。用最低位当 allocated 标志：

```
header = size | a        a = 1 已分配，a = 0 空闲
get_alloc(h) = h & 0x1
get_size(h)  = h & ~0xfL
```

这是“用对齐浪费的位存元数据”的经典技巧，后面讲页表、tagged pointer 都会再遇到。

**如何遍历**（第 29 页）：没有 next 指针，靠 size 前进：

```c
static block_t *find_next(block_t *block) {
    return (block_t *)((unsigned char *)block + get_size(block));
}
```

于是整条链表就是“从 heap_start 开始，每次加自己的 size，直到 heap_end”。这就是“隐式”的含义：链是算出来的，不是存出来的。

讲义第 26 页的例子（1 格 = 1 word = 8 字节）：

```
16/0 | 32/1 | 32/1 | 64/0 | 8/1(End Block)
```

注意 header 位于**非对齐**位置，payload 才是对齐的——这是 header 占一个字带来的直接后果。

### 5.7 放置策略

| 策略 | 做法 | 时间复杂度 | 碎片表现 |
|---|---|---|---|
| First fit | 从头找第一个够大的空闲块 | O(块数) | 列表前部产生“碎片渣”（splinters） |
| Next fit | 从上次搜索结束处继续 | 平均更快 | 研究显示碎片更严重 |
| Best fit | 找剩余最少的够大块 | O(块数)，通常更慢 | 碎片小，利用率好，但仍是贪心 |

第 32 页的实测 overhead 已列在 5.3 节：best fit 8.3% < first fit 11.9% < next fit 21.6%。注意 best fit 也不是最优——它只是贪心，且会留下大量极小的、几乎无法使用的碎片。

### 5.8 分割

空闲块 64 字节，请求 32 字节：若整块给出，浪费 32 字节（内部碎片）；若切开，剩余 32 字节可留给后续请求。

```c
static void split_block(block_t *block, size_t asize) {
    size_t block_size = get_size(block);
    if ((block_size - asize) >= min_block_size) {   /* 剩余够放一个最小块 */
        write_header(block, asize, true);
        block_t *block_next = find_next(block);
        write_header(block_next, block_size - asize, false);
    }
}
```

关键判断 `block_size - asize >= min_block_size`：如果剩余部分小到连一个 header + footer + 最小 payload 都放不下，就不切——否则会产生无法使用的小碎片。这是“分割策略（splitting policy）”的典型取舍。

### 5.9 合并与假碎片

若 `free` 只是把标志位清零（第 35 页），会出现**假碎片（false fragmentation）**：

```
[32/1][16/1][16/1][32/1]
free(p)  ->  [32/1][16/0][16/1][32/1]
malloc(40) -> 失败！明明有 32 字节连续空闲，但被两个 header 隔开
```

解决办法是**合并（coalescing）**：`free` 时检查前后相邻块，若空闲就拼成一个大块。

- 与**后一个**块合并很容易：当前块地址 + size 就是下一个块的 header，读它即可（第 36–37 页）。
- 与**前一个**块合并很麻烦：不知道前一个块从哪开始，也不知道它多大。

### 5.10 Boundary Tag

Knuth 1973 的技巧（第 38 页）：在每个块的**末尾**再放一份 header 的副本，称为 footer 或 boundary tag。

```
+----------+------------------+----------+
| header   | payload+padding  | footer   |
| size | a |                  | size | a |
+----------+------------------+----------+
```

于是：

- 当前块 header 的前一个字，就是**前一个块的 footer**，从中读出前块大小与分配状态。
- 前块 header 地址 = 当前 header 地址 − 前块 size。

```c
static word_t *find_prev_footer(block_t *block) {
    return &(block->header) - 1;          /* 当前 header 往前一个字 */
}
static word_t *header_to_footer(block_t *block) {
    size_t asize = get_size(block);
    return (word_t *)(block->payload + asize - dsize);   /* dsize = 2*sizeof(word_t) */
}
```

代价：空闲块多一个字的开销；已分配块本来不需要 footer，但为了统一结构通常也加上（后面 5.12 会优化掉）。

### 5.11 四种合并情形（O(1)）

讲义第 43–47 页，设当前释放块为 n，前块 m1、后块 m2：

| 情形 | 前块 | 后块 | 动作 |
|---|---|---|---|
| 1 | 已分配 | 已分配 | 只把 n 标为空闲，不改 size |
| 2 | 已分配 | 空闲 | n 与 m2 合并，size = n + m2，改新块 header 与 footer |
| 3 | 空闲 | 已分配 | m1 与 n 合并，size = m1 + n，改 m1 的 header 与新 footer |
| 4 | 空闲 | 空闲 | 三块合并，size = m1 + n + m2，改 m1 header 与 m2 footer |

每种情形都只需常数次内存读写，因为 boundary tag 让“找到前块”和“找到后块”都是 O(1)。这就是“constant time coalescing”。

### 5.12 堆的两个哨兵

讲义第 48 页：边界情形会让合并逻辑出错。

- 释放**第一个**块时，它的“前块”不存在，`find_prev_footer` 会读到堆外的数据。
- 释放**最后**一个块时，它的“后块”是堆边界。

解决：在堆起始处放一个 **dummy footer**（标记为已分配），在堆末尾放一个 **dummy header**（标记为已分配，size = 8，即 End Block）。这样任何真实块的前后都“有块”，且都“已分配”，合并逻辑无需特判。

### 5.13 malloc 与 free 的顶层流程

**mm_malloc**（第 49 页）：

```c
void *mm_malloc(size_t size) {
    size_t asize = round_up(size + dsize, dsize);   /* 加 header+footer，向上取整到 16 */
    block_t *block = find_fit(asize);
    if (block == NULL) return NULL;
    size_t block_size = get_size(block);
    write_header(block, block_size, true);
    write_footer(block, block_size, true);
    split_block(block, asize);
    return header_to_payload(block);
}
```

其中 `round_up(n, m) = m * ((n + m - 1) / m)`。

**mm_free**（第 50 页）：

```c
void mm_free(void *bp) {
    block_t *block = payload_to_header(bp);
    size_t size = get_size(block);
    write_header(block, size, false);
    write_footer(block, size, false);
    coalesce_block(block);
}
```

顺序很重要：先把本块标为空闲（这样合并时前后块看到的“邻居状态”是对的），再做合并。

### 5.14 去掉已分配块的 footer

讲义第 51–56 页的优化：footer 只在**空闲块**中才需要——因为合并只在 `free` 时发生，而 `free` 时当前块刚变成空闲，需要知道前块的状态与大小；前块若已分配，其 footer 无意义。

替代方案：在 header 中多用一位。

```
b = 1: 前一个块已分配
b = 0: 前一个块空闲
header = size | (b << 1) | a
```

- 空闲块仍需 footer（下一个块要靠它判断“前块是否空闲”并找到其起始位置）。
- 已分配块不再需要 footer，节省 8 字节。

好处是减少内部碎片，代价是合并逻辑要更小心地维护 b 位：分配/释放/分割时必须同步更新**下一个块**的 b 位（第 53–56 页的四个 Case 图展示了每次操作后哪些位要改）。

### 5.15 策略总结

讲义第 57 页把分配器的设计空间归为三类策略：

- **放置策略（placement）**：first/next/best fit。用吞吐换碎片。讲义指出：分离空闲链表（下一讲）能在不搜索整条链的情况下近似 best fit。
- **分割策略（splitting）**：什么时候切、容忍多少内部碎片。
- **合并策略（coalescing）**：立即合并（每次 `free` 都做）vs 延迟合并（攒到 `malloc` 需要时再做）。

### 5.16 隐式链表的评价

第 58 页：

- 实现非常简单。
- `malloc` 最坏 O(n)（n 为块总数）。
- `free` 最坏 O(1)，即使带合并。
- 内存开销取决于放置策略。
- **实际 `malloc`/`free` 不采用**，因为线性时间的分配在频繁分配的场景下不可接受；但许多专用场景仍在用。
- 然而 **splitting 与 boundary tag coalescing 这两个概念对所有分配器都通用**——这是本讲真正的收获。

## 6. 代码示例

### 6.1 官方课程代码

**块结构体（13-malloc-basic.pdf 第 27 页）：**

```c
typedef uint64_t word_t;
typedef struct block {
    word_t header;
    unsigned char payload[0];   /* 零长数组，payload 紧跟 header */
} block_t;

/* payload 指针 -> 块指针 */
return (block_t *)((unsigned char *)bp - offsetof(block_t, payload));
/* 块指针 -> payload 指针 */
return (void *)(block->payload);
```

用零长数组让 `payload` 成为结构体的“柔性”尾部，`offsetof` 保证偏移计算与编译器布局无关。

**header 的读写（第 28 页）：**

```c
return header & 0x1;          /* 取分配位 */
return header & ~0xfL;        /* 取大小，清掉低 4 位 */
block->header = size | alloc; /* 写 header */
```

**first fit（第 30 页）：**

```c
static block_t *find_fit(size_t asize) {
    block_t *block;
    for (block = heap_start; block != heap_end; block = find_next(block)) {
        if (!(get_alloc(block)) && (asize <= get_size(block)))
            return block;
    }
    return NULL;
}
```

**带 footer 的 split（第 42 页）：**

```c
static void split_block(block_t *block, size_t asize) {
    size_t block_size = get_size(block);
    if ((block_size - asize) >= min_block_size) {
        write_header(block, asize, true);
        write_footer(block, asize, true);
        block_t *block_next = find_next(block);
        write_header(block_next, block_size - asize, false);
        write_footer(block_next, block_size - asize, false);
    }
}
```

注意讲义第 34 页的版本标了 “Warning: This code is incomplete”，因为缺了 footer 的写入——这正是引入 boundary tag 前后的差别。

**mm_malloc / mm_free（第 49–50 页）**：见 5.13 节，注意 `round_up(size + dsize, dsize)` 里 `dsize = 2*sizeof(word_t) = 16`，正好等于对齐粒度。

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

下面是一个能真正跑起来的极简隐式链表分配器（first fit + boundary tag + 四种合并），约 90 行，可直接在 Linux 上编译验证：

```c
/* 非官方示例：极简隐式空闲链表分配器 */
#include <stddef.h>
#include <string.h>
#include <stdint.h>

#define WSIZE 8
#define DSIZE 16
#define CHUNKSIZE 4096
#define ALIGN 16

extern char *heap_start;      /* 假设由测试框架提供一段静态缓冲区 */
static char heap[1 << 20];
static char *heap_ptr = heap;

#define PACK(size, alloc) ((size) | (alloc))
#define GET(p)            (*(uint64_t *)(p))
#define PUT(p, val)       (*(uint64_t *)(p) = (val))
#define GET_SIZE(p)       (GET(p) & ~0xfUL)
#define GET_ALLOC(p)      (GET(p) & 0x1)
#define HDRP(bp)          ((char *)(bp) - WSIZE)
#define FTRP(bp)          ((char *)(bp) + GET_SIZE(HDRP(bp)) - DSIZE)
#define NEXT_BLKP(bp)     ((char *)(bp) + GET_SIZE(HDRP(bp)))
#define PREV_BLKP(bp)     ((char *)(bp) - GET_SIZE((char *)(bp) - DSIZE))

static void *coalesce(void *bp) {
    size_t prev_alloc = GET_ALLOC(FTRP(PREV_BLKP(bp)));
    size_t next_alloc = GET_ALLOC(HDRP(NEXT_BLKP(bp)));
    size_t size = GET_SIZE(HDRP(bp));
    if (prev_alloc && next_alloc) {              /* Case 1 */
    } else if (prev_alloc && !next_alloc) {      /* Case 2 */
        size += GET_SIZE(HDRP(NEXT_BLKP(bp)));
        PUT(HDRP(bp), PACK(size, 0));
        PUT(FTRP(bp), PACK(size, 0));
    } else if (!prev_alloc && next_alloc) {      /* Case 3 */
        size += GET_SIZE(HDRP(PREV_BLKP(bp)));
        PUT(FTRP(bp), PACK(size, 0));
        PUT(HDRP(PREV_BLKP(bp)), PACK(size, 0));
        bp = PREV_BLKP(bp);
    } else {                                     /* Case 4 */
        size += GET_SIZE(HDRP(PREV_BLKP(bp))) + GET_SIZE(HDRP(NEXT_BLKP(bp)));
        PUT(HDRP(PREV_BLKP(bp)), PACK(size, 0));
        PUT(FTRP(NEXT_BLKP(bp)), PACK(size, 0));
        bp = PREV_BLKP(bp);
    }
    return bp;
}

void *my_malloc(size_t size) {
    size_t asize = (size + DSIZE + ALIGN - 1) & ~(size_t)(ALIGN - 1);
    if (asize < DSIZE + ALIGN) asize = DSIZE + ALIGN;
    for (char *bp = heap_ptr; bp < heap_ptr + sizeof(heap); bp = NEXT_BLKP(bp)) {
        if (!GET_ALLOC(HDRP(bp)) && GET_SIZE(HDRP(bp)) >= asize) {
            size_t csize = GET_SIZE(HDRP(bp));
            if (csize - asize >= DSIZE + ALIGN) {   /* 能切就切 */
                PUT(HDRP(bp), PACK(asize, 1));
                PUT(FTRP(bp), PACK(asize, 1));
                PUT(HDRP(NEXT_BLKP(bp)), PACK(csize - asize, 0));
                PUT(FTRP(NEXT_BLKP(bp)), PACK(csize - asize, 0));
            } else {
                PUT(HDRP(bp), PACK(csize, 1));
                PUT(FTRP(bp), PACK(csize, 1));
            }
            return bp;
        }
    }
    return NULL;
}

void my_free(void *bp) {
    size_t size = GET_SIZE(HDRP(bp));
    PUT(HDRP(bp), PACK(size, 0));
    PUT(FTRP(bp), PACK(size, 0));
    coalesce(bp);
}

void heap_init(void) {
    char *p = heap;
    PUT(p, 0);                                   /* 对齐填充 */
    PUT(p + WSIZE, PACK(DSIZE, 1));              /* dummy header */
    PUT(p + DSIZE, PACK(DSIZE, 1));              /* dummy footer */
    p += DSIZE;
    PUT(p, PACK(sizeof(heap) - 2 * DSIZE, 0));   /* 初始的空闲大块 */
    PUT(p + sizeof(heap) - 2 * DSIZE - WSIZE, PACK(sizeof(heap) - 2 * DSIZE, 0));
    heap_ptr = heap + DSIZE;
}
```

几个值得注意的细节：

- `PREV_BLKP` 用“当前块前一个字 = 前块 footer”来定位前块，这就是 boundary tag 的全部价值。
- 切块时判断 `csize - asize >= DSIZE + ALIGN`，保证剩下的块至少能放下 header + footer + 一个对齐的 payload。
- 合并顺序：Case 3/4 中必须**先写 footer 再写 header**（因为 `FTRP` 依赖 header 的 size），否则会写到错误位置。这是 malloclab 最常见的 bug 之一。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| 内部碎片 | 外部碎片 | 前者在块**内部**浪费，可精确测量；后者是块**之间**的空隙太小，依赖未来请求，不可测 |
| header | footer（boundary tag） | 两者内容相同；header 用于向后遍历，footer 用于向前定位前块 |
| 隐式空闲链表 | 显式空闲链表 | 前者靠 size 计算下一个块，不存指针；后者在空闲块里存 `prev`/`next` 指针 |
| `sbrk` | `malloc` | `sbrk` 是系统调用，直接移动堆顶；`malloc` 是库函数，在已获得的堆空间内做块管理，偶尔才调 `sbrk` |
| 假碎片（false fragmentation） | 外部碎片 | 假碎片是“本可以合并但没合并”造成的；外部碎片是即便合并后仍无足够大块 |
| first fit | best fit | 前者找第一个够大的，快但碎片多；后者找最贴合的，碎片少但慢 |
| 立即合并 | 延迟合并 | 前者每次 `free` 都合并，`free` 恒定时间但可能做无用功；后者攒着，`malloc` 时才合并 |

## 8. 对应原版讲义

- PDF 相对路径：`90-原始PDF/15-213/lectures/13-malloc-basic.pdf`
- 总页数：58 页
- 重点页码：
  - 堆在地址空间中的位置：第 4 页
  - 显式 vs 隐式分配器：第 5 页
  - malloc 接口与示例：第 6–7 页
  - 堆可视化约定（1 格 = 8 字节）：第 8–9 页
  - 分配器的五条约束：第 10 页
  - 吞吐量与 overhead 公式：第 11–12 页
  - benchmark 表格与曲线：第 13–15 页
  - 内部碎片成因与影响：第 16–18 页
  - 外部碎片成因与影响：第 19–20 页
  - 五个实现问题：第 21 页
  - header 记录块大小：第 22 页
  - 四种记录空闲块的方法：第 23 页
  - 隐式链表 header 格式（size | a）：第 25 页
  - 详细例子（16/0 32/1 32/1 64/0 8/1）：第 26 页
  - 块结构与指针换算：第 27 页
  - header 位运算：第 28 页
  - 遍历：第 29 页
  - first fit 代码：第 30 页
  - 三种放置策略对比：第 31 页
  - 策略 overhead 实测：第 32 页
  - 分割：第 33–34、42 页
  - 假碎片：第 35 页
  - 合并与 boundary tag：第 36–38 页
  - footer 定位代码：第 40–41 页
  - 四种合并情形：第 43–47 页
  - dummy header/footer：第 48 页
  - mm_malloc / mm_free：第 49–50 页
  - 去掉已分配块 footer 的优化：第 51–56 页
  - 策略总结与隐式链表评价：第 57–58 页
- 原始链接：https://www.cs.cmu.edu/~213/lectures/13-malloc-basic.pdf

## 9. 对应视频

未找到官方公开录像。

## 10. 本节复习

- 显式分配器由应用负责释放；隐式分配器由 GC 负责。
- 两个指标：throughput 与 peak utilization（overhead = H/peak − 1）。
- 内部碎片取决于过去的请求，可测；外部碎片取决于未来的请求，不可测。
- 隐式链表：header = size | a，用对齐留下的低位存标志；`find_next = block + size`。
- 放置策略实测：best 8.3% < first 11.9% < next 21.6%（perfect 1.6%）。
- 分割需判断剩余是否 ≥ 最小块大小。
- 只清标志会产生假碎片；boundary tag 让前后合并都是 O(1)。
- 四种合并情形 + 两个 dummy 哨兵。
- 优化：已分配块可去掉 footer，用 header 的 b 位表示前块是否已分配。
- 隐式链表 malloc 最坏 O(n)，实际不用于通用 malloc，但 splitting 与 coalescing 概念通用。

## 11. 自我检查

1. 一个序列：`p1=malloc(10)`、`p2=malloc(100)`、`p3=malloc(20)`、`free(p2)`、`p4=malloc(80)`。在 16 字节对齐、每块 8 字节 header + 8 字节 footer 的分配器上，各块的 asize 是多少？`p4` 能否复用 `p2` 的空间？
2. 为什么 `free` 必须传入 `malloc` 返回的原始指针，而不能传块中间的指针？
3. boundary tag 让合并变成 O(1)，代价是什么？讲义给出了什么优化来降低这个代价？
4. 假设某分配器的 peak aggregate payload 是 50,000 字节，堆大小始终是 60,000 字节，overhead 是多少？如果换成 best fit 后堆只需 54,000 字节，overhead 变成多少？
5. 解释“假碎片”，并说明为什么仅靠合并相邻块仍不能消除外部碎片。

<details>
<summary>参考答案</summary>

1. `dsize = 16`，`round_up(size + 16, 16)`：
   - `p1`：10 + 16 = 26 → 32
   - `p2`：100 + 16 = 116 → 128
   - `p3`：20 + 16 = 36 → 48
   - `p4`：80 + 16 = 96 → 96
   `free(p2)` 后留下 128 字节空闲块；`p4` 需要 96 字节，128 − 96 = 32 ≥ 最小块（16 + 16 = 32），可以切分复用：前 96 字节给 `p4`，剩余 32 字节成为新的空闲块。

2. 因为 `free` 需要从指针反推 header 的位置来读取块大小（`header = bp − 8`）。传入块中间的指针会算错 header 地址，读到垃圾 size，随后写 header/footer 就会破坏堆结构。这也是 C 里 `free` 一个非 `malloc` 指针属于未定义行为的原因。

3. 代价是每个块多一个字的 footer（8 字节），即使是已分配块也要占，增加了内部碎片。优化（讲义第 51–56 页）：footer 只在**空闲块**中保留，已分配块去掉 footer，改为在 header 中用一位 `b` 表示“前一个块是否已分配”。释放时若 `b = 1` 就不必读前块 footer。代价是每次分配/释放/分割都要同步更新下一个块的 `b` 位。

4. 原始：60000/50000 − 1 = 0.20，即 20%。换 best fit 后：54000/50000 − 1 = 0.08，即 8%。

5. 假碎片指相邻的空闲块本可以合并成一个大块，但由于没有合并（`free` 只清了标志位），分配器看不到这段连续空间。合并相邻空闲块能消除假碎片，但外部碎片还有更深的一层：即便所有能合并的都合并了，堆里仍可能只剩若干中等大小的空闲块，而请求要一个更大的连续块——此时唯一彻底的解法是压缩（移动已分配块），而 C 的指针语义禁止这样做。

</details>

## 12. 进一步学习

- 下一讲：[[15-213-14-Dynamic-Memory-Allocation-Advanced]]（显式空闲链表、分离适配、malloclab 的实现要点）
- 前一讲：[[15-213-12-Virtual-Memory-Details]]
- 相关实验：[[00-Lab总览]]（Malloc Lab 就是实现一个高性能分配器）
- 课程总览：[[20-CMU-15-213/00-课程总览|CMU 15-213 - 课程总览]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Throughput、Virtual Memory）
- CSAPP 第 3 版 9.9 节；9.9.12 的 `mm.c` 完整实现可与本节 5.13 的顶层流程对照阅读。
