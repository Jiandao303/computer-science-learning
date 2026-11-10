---
course: CMU 15-213
course_name: Introduction to Computer Systems
semester: Fall 2026
lecture_id: L10
topic: Cache Memories
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-213
  - 缓存
  - 局部性
  - 存储器层次
---

# 缓存存储器（Cache Memories）

## 1. 本节学习目标

- 能用 S、E、B 三个参数描述缓存的组织结构，并把一个地址拆成 tag / set index / block offset 三段。
- 能对给定地址序列手算直接映射（direct-mapped）与组相联（set-associative）缓存的命中与缺失。
- 能解释写命中、写缺失的四种策略组合，以及 dirty bit 的作用。
- 能用 miss rate、hit time、miss penalty 估算平均访问时间，说明为什么 99% 命中率比 97% 好一倍。
- 能分析矩阵乘不同循环顺序的缺失率，并用分块（blocking）把缺失量从 O(n³) 降到 O(n³/B)。
- 能读懂 memory mountain（存储器山）图，指出空间局部性斜坡与时间局部性山脊。

## 2. 前置知识

- [[15-213-09-Memory-Hierarchy]]：存储器层次、locality（局部性）原则、缓存命中/缺失的基本定义。
- [[15-213-06-Machine-Programming-IV-Data]]：寄存器与 load/store 指令，理解一次内存访问在机器级是什么样。
- 数学：二进制位拆分、以 2 为底的指数（S = 2^s、E = 2^e、B = 2^b）。
- 编程：C 二维数组按行优先（row-major）存放，`a[i][j]` 的地址是 `a + i*N + j`。

## 3. 核心概念

- **Cache（缓存）**：位于 CPU 与主存之间的小而快的存储，保存主存中一部分块的副本。CPU 访问数据时先查缓存，命中就不必去主存。
- **Cache Line / Block（缓存行/块）**：缓存与内存之间数据传输的最小单位，通常 64 字节。即使只读 1 个字节，也会把整块搬进缓存——这是空间局部性能生效的硬件基础。
- **Set（组）**：缓存划分为 S = 2^s 个组，每组有 E 条 line。地址中间的 s 位决定映射到哪一组。
- **Tag（标记）**：地址中除去组索引和块偏移后剩下的高位，用来确认组里这条 line 是不是目标块。
- **Valid Bit（有效位）**：标记该 line 是否装有有效数据。开机时全部无效，所以第一次访问必然缺失。
- **Dirty Bit（脏位）**：write-back 缓存中标记该 line 被改写过、与主存不一致，驱逐时必须写回主存。
- **Direct-Mapped Cache（直接映射缓存）**：E = 1，每组一条 line。硬件最简单，但冲突缺失最严重。
- **Set-Associative Cache（组相联缓存）**：E > 1，每组多条 line，一个地址只能进固定的一组，但组内任选一条。E 越大冲突缺失越少，比较器越多、命中时间越长。
- **Fully Associative（全相联）**：S = 1，只有一组，任意块可放任意位置，是 E 取到最大值的特例。
- **Write-Through（写直达）**：写命中时同时写缓存和主存，简单但流量大。
- **Write-Back（写回）**：只改缓存并置 dirty bit，等该 line 被驱逐时才写回主存，流量小但需要脏位。
- **Write-Allocate（写分配）**：写缺失时先把块载入缓存再写，适合后续还会写同一位置的情况。
- **No-Write-Allocate（非写分配）**：写缺失时直接写主存，不载入缓存。
- **Blocking（分块）**：把大矩阵切成能同时装进缓存的小块，块内反复使用，提升时间局部性。
- **Memory Mountain（存储器山）**：以 working set size 和 stride 为两个水平轴、以读吞吐量为高度画出的三维曲面，用来直观展示各级缓存与局部性的影响。

## 4. 通俗理解

把缓存想成你书桌上的一小块地方，主存是走廊尽头的书架。

- 你正在写作业，需要某本书。如果书已经在桌上（hit），伸手就拿；如果不在（miss），要走到书架取，顺便把同一层相邻的几本一起抱回来（一次搬一个 block，不是一本）。
- 桌子太小，新书放不下时，必须扔掉一本（replacement / eviction）。直接映射相当于“桌上每个位置只放一本，且每本书按编号只允许放固定位置”；组相联相当于“每个格子里能叠两本，按编号只能进那个格子，但格内随便放”。
- 你刚查过的书很可能马上还要查（temporal locality）；你查了第 3 章，多半马上要第 4 章（spatial locality）。

具体数字：假设 L1 命中只需 1 个周期，缺失代价 100 个周期。97% 命中时平均访问时间 = 1 + 0.03×100 = 4 周期；99% 命中时 = 1 + 0.01×100 = 2 周期。命中率只提高 2 个百分点，速度却翻倍——这就是缓存课反复强调 miss rate 的原因。

## 5. 原理与推导

### 5.1 地址如何拆分

缓存由三个参数定义：

- S = 2^s 个组（set）；
- 每组 E = 2^e 条 line（E 又叫相联度 associativity）；
- 每块 B = 2^b 字节（block offset 需要 b 位）。

一个 m 位地址被切成三段：

```
| tag (t = m - s - b 位) | set index (s 位) | block offset (b 位) |
```

- **block offset（b 位）**：块内第几个字节，因为一次搬 B 字节，要能索引 B 个位置。
- **set index（s 位）**：选组，共 2^s = S 组。
- **tag（t 位）**：剩下的高位，和 line 里存的 tag 比较，确认“是不是同一块”。

为什么索引用中间位而不是高位？讲义第 60–63 页专门讨论：若用高位做索引，一段连续地址（空间局部性极好）会全部挤进同一个 set，造成大量冲突缺失；用中间位则连续块会分散到不同组，冲突少。

### 5.2 一次读访问的判定流程

1. 用 set index 找到组。
2. 在该组的 E 条 line 中逐条比较：valid == 1 且 tag 相等 → **hit**。
3. hit 时用 block offset 从块内取出目标字节。
4. 都不匹配 → **miss**：从下一级存储器取整块，按替换策略选一条 victim 驱逐，写入新块，置 valid = 1。

替换策略（replacement policy）：直接映射没有选择余地；组相联常用 LRU（least recently used，最近最少使用）或随机。真实硬件为了速度常用伪 LRU 或随机。

### 5.3 三种缺失（承接上一讲）

- **Cold / Compulsory miss（冷缺失/强制性缺失）**：块第一次被访问，无法避免。
- **Capacity miss（容量缺失）**：工作集大于缓存容量，即使全相联也会缺。
- **Conflict miss（冲突缺失）**：缓存容量够，但多个热点块映射到同一组互相驱逐。增大 E 或改变索引方式可缓解。

### 5.4 手算示例：直接映射

讲义第 15 页的例子：4 位地址（地址空间 16 字节），S = 4、E = 1、B = 2，因此 s = 2、b = 1、t = 1。

地址序列 0, 1, 7, 8, 0：

| 访问 | 二进制 | tag | set | offset | 结果 | 说明 |
|---|---|---|---|---|---|---|
| 0 | 0000 | 0 | 00 | 0 | miss | 冷缺失，装入 M[0-1] |
| 1 | 0001 | 0 | 00 | 1 | hit | 与 0 同块 |
| 7 | 0111 | 0 | 11 | 1 | miss | 冷缺失，装入 M[6-7] |
| 8 | 1000 | 1 | 00 | 0 | miss | set 0 原 line tag=0，被驱逐 |
| 0 | 0000 | 0 | 00 | 0 | miss | set 0 现在 tag=1，冲突缺失 |

最后那次 miss 就是典型的冲突缺失：缓存只有 2 块容量却要容纳 3 个块，而 0 和 8 又恰好同组。

### 5.5 手算示例：2 路组相联

讲义第 19 页：S = 2、E = 2、B = 2，于是 s = 1、b = 1、t = 2。同一序列 0, 1, 7, 8, 0：

| 访问 | tag | set | 结果 |
|---|---|---|---|
| 0 | 00 | 0 | miss，set 0 装入 M[0-1] |
| 1 | 00 | 0 | hit |
| 7 | 01 | 1 | miss，set 1 装入 M[6-7] |
| 8 | 10 | 0 | miss，set 0 第二条 line 装入 M[8-9]（不驱逐 0） |
| 0 | 00 | 0 | hit |

对比可见：同样是 4 块总容量，2 路组相联把最后一次冲突缺失变成了命中。相联度就是拿“比较器数量和命中延迟”换“冲突缺失”。

### 5.6 写策略

写操作比读复杂，因为数据在多级（L1、L2、L3、主存）各有一份副本。两个独立维度：

- 写命中：**write-through**（立即写下一级）vs **write-back**（只改本行，置 dirty bit，驱逐时写回）。
- 写缺失：**write-allocate**（先取块进缓存再写）vs **no-write-allocate**（直接写下一级）。

实际组合通常是：

| 组合 | 特点 | 常见场合 |
|---|---|---|
| write-through + no-write-allocate | 实现简单、一致性强，但写流量大 | 早期处理器、某些 L1 |
| write-back + write-allocate | 写流量小，适合重复写同一块 | 现代 CPU 的主流选择 |

write-back + write-allocate 的具体流程（讲义第 21 页）：

1. 写地址 X，命中：改块内容，dirty = 1（脏位是“粘性”的，只有驱逐时才清零）。
2. 写地址 X，缺失：先按读缺失把块取进来，再按写命中处理。
3. 某 line 被驱逐且 dirty = 1：把整个 2^b 字节块写回下一级，清 dirty，装入新块。

### 5.7 性能指标与平均访问时间

- **Miss Rate（缺失率）**= misses / accesses = 1 − hit rate。L1 典型 3%–10%，L2 常低于 1%。
- **Hit Time（命中时间）**：从发出地址到拿到数据，包括判断是否命中的时间。L1 约 4 周期，L2 约 10 周期。
- **Miss Penalty（缺失代价）**：缺失时额外花的时间，主存约 50–200 周期，且趋势在变大（CPU 变快比内存快）。

平均访问时间（AMAT）近似：

```
AMAT = hit time + miss rate × miss penalty
```

讲义第 24 页用 1 周期命中、100 周期缺失算过：97% → 4 周期，99% → 2 周期。

### 5.8 矩阵乘的缺失分析

假设块大小 32B（装 4 个 double），N 很大，缓存装不下多行。看内层循环每次迭代的缺失次数（讲义第 36–42 页）：

| 版本 | 内层循环 | A | B | C | 每次迭代缺失 |
|---|---|---|---|---|---|
| ijk | `sum += a[i][k] * b[k][j]` | 行优先，步长 1 | 列方向，步长 N | 固定在寄存器 | 0.25 + 1.0 + 0 = 1.25 |
| jik | 同上，i/j 交换 | 行优先 | 列方向 | 固定 | 1.25 |
| kij | `c[i][j] += r * b[k][j]` | 固定 | 行优先 | 行优先 | 0 + 0.25 + 0.25 = 0.5 |
| ikj | 同上 | 固定 | 行优先 | 行优先 | 0.5 |
| jki | `c[i][j] += a[i][k] * r` | 列方向 | 固定 | 列方向 | 1.0 + 0 + 1.0 = 2.0 |
| kji | 同上 | 列方向 | 固定 | 列方向 | 2.0 |

关键：C 数组按行存放，`c[i][j]` 在内层循环里沿 j 走是 stride-1；若内层沿 i 走（jki/kji），每次跨一整行，缺失率 100%。

### 5.9 分块（blocking）

即使循环顺序调到最优（kij，0.5 miss/iter），总缺失仍是 Θ(n³)。分块利用矩阵乘固有的时间局部性：每个元素被用 O(n) 次，只要让它在被驱逐前用完即可。

讲义第 45–51 页：

- 不分块：每次迭代 n/8 + n = 9n/8 次缺失，共 n² 次迭代，总缺失 (9/8)n³。
- 分块（块大小 B，注意此 B 不是 cache block size）：每个 B×B 子块缺失 B²/8 次，共 2n/B 个子块（A、B 各一）；总缺失约为 (n/B)² × 2 × (B²/8) = n³/(4B)。
- 选择 B 的约束：三个块（两个输入、一个输出）要同时驻留缓存，即 3B² < C。

从 (9/8)n³ 到 n³/(4B)，当 B = 32 时相差两个数量级。这是“改写循环结构就能把缓存利用率提高几十倍”的经典案例。

### 5.10 Memory Mountain

讲义的 memory mountain 用 `test(elems, stride)` 遍历一个全局 `long data[]` 数组，4×4 循环展开，测不同 working set size 与 stride 下的读吞吐（MB/s）。

- **山脊（ridges）**：固定 stride 沿 size 方向，吞吐在 32KB（L1）、256KB（L2）、8MB（L3）处阶梯下降——对应各级缓存容量。
- **斜坡（slopes）**：固定 size 沿 stride 方向，stride 从 1 增大时吞吐下降，因为一个 64B 块里被用到的字节比例是 8/stride（stride 以 8 字节为单位）；stride ≥ 8 时每个元素都要新块，缺失率 100%。

这张图把“局部性”这个定性概念变成了可测量的曲面，也是 cachelab 的理论基础。

## 6. 代码示例

### 6.1 官方课程代码

**矩阵乘 ijk（`matmult/mm.c`，讲义 10-cache-memories.pdf 第 33 页）：**

```c
/* ijk */
for (i = 0; i < n; i++) {
    for (j = 0; j < n; j++) {
        sum = 0.0;
        for (k = 0; k < n; k++)
            sum += a[i][k] * b[k][j];
        c[i][j] = sum;
    }
}
```

内层对 A 是 stride-1（好），对 B 是 stride-n（坏），每次迭代约 1.25 次缺失。

**kij（`matmult/mm.c`，第 38 页）：**

```c
/* kij */
for (k = 0; k < n; k++) {
    for (i = 0; i < n; i++) {
        r = a[i][k];
        for (j = 0; j < n; j++)
            c[i][j] += r * b[k][j];
    }
}
```

内层 B、C 都是 stride-1，缺失约 0.5 次/迭代，是六个版本里最好的。

**分块版本（`matmult/bmm.c`，第 48 页）：**

```c
void mmm(double *a, double *b, double *c, int n) {
    int i, j, k;
    for (i = 0; i < n; i += B)
        for (j = 0; j < n; j += B)
            for (k = 0; k < n; k += B)
                /* B x B mini matrix multiplications */
                for (i1 = i; i1 < i + B; i1++)
                    for (j1 = j; j1 < j + B; j1++)
                        for (k1 = k; k1 < k + B; k1++)
                            c[i1*n+j1] += a[i1*n+k1] * b[k1*n+j1];
}
```

讲义特别注明：这里的 B 是分块大小，不是缓存块大小。

**memory mountain 测试函数（`mountain/mountain.c`，第 29 页）：**

```c
int test(int elems, int stride) {
    long i, sx2 = stride*2, sx3 = stride*3, sx4 = stride*4;
    long acc0 = 0, acc1 = 0, acc2 = 0, acc3 = 0;
    long length = elems, limit = length - sx4;
    for (i = 0; i < limit; i += sx4) {
        acc0 = acc0 + data[i];
        acc1 = acc1 + data[i+stride];
        acc2 = acc2 + data[i+sx2];
        acc3 = acc3 + data[i+sx3];
    }
    for (; i < length; i++)
        acc0 = acc0 + data[i];
    return ((acc0 + acc1) + (acc2 + acc3));
}
```

四次累加拆成四个独立累加器，既做循环展开又避免串行依赖，测量的是纯内存吞吐而非 ALU 延迟。

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

下面这个函数模拟一个直接映射缓存的地址拆分，用于验证 5.4 节的手算：

```c
#include <stdio.h>

/* 参数：地址位数 m、组索引位数 s、块偏移位数 b */
void decode(unsigned addr, int m, int s, int b) {
    unsigned offset = addr & ((1u << b) - 1);
    unsigned set    = (addr >> b) & ((1u << s) - 1);
    unsigned tag    = addr >> (b + s);
    printf("addr=0x%0*x  tag=0x%x  set=%u  offset=%u\n",
           (m + 3) / 4, addr, tag, set, offset);
}

int main(void) {
    /* 4 位地址空间，S=4 (s=2)，B=2 (b=1) */
    unsigned trace[] = {0, 1, 7, 8, 0};
    for (int i = 0; i < 5; i++)
        decode(trace[i], 4, 2, 1);
    return 0;
}
```

输出中 0 与 8 的 set 都是 0、tag 分别是 0 和 1，正好解释 5.4 节最后一次冲突缺失。

再给一个分块矩阵乘的教学版（一维数组表示二维矩阵，便于对照讲义）：

```c
/* 非官方示例：分块矩阵乘，n 为矩阵阶，BS 为分块大小 */
void blocked_mmm(double *a, double *b, double *c, int n, int BS) {
    for (int ii = 0; ii < n; ii += BS)
        for (int jj = 0; jj < n; jj += BS)
            for (int kk = 0; kk < n; kk += BS)
                for (int i = ii; i < ii + BS && i < n; i++)
                    for (int j = jj; j < jj + BS && j < n; j++) {
                        double sum = c[i*n + j];
                        for (int k = kk; k < kk + BS && k < n; k++)
                            sum += a[i*n + k] * b[k*n + j];
                        c[i*n + j] = sum;
                    }
}
```

与讲义版的区别是内层用局部变量 `sum` 累加再写回，减少对 C 的重复读写；边界条件用 `&& i < n` 处理 n 不是 BS 整数倍的情况（讲义版为简化省略了）。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| Cache block size B（缓存块大小） | Blocking 的块大小 B | 前者是硬件一次搬运的字节数（如 64B）；后者是算法里手工切分的子矩阵阶数，两者无关，讲义第 48 页专门提醒 |
| Hit rate（命中率） | Miss rate（缺失率） | 二者互补；但性能讨论几乎只用 miss rate，因为缺失代价远大于命中时间 |
| Write-through（写直达） | Write-back（写回） | 前者每次写都同步到下一级；后者延迟到驱逐，需要 dirty bit |
| Write-allocate（写分配） | No-write-allocate（非写分配） | 写缺失时是否先把块取进缓存；前者适合后续重复写，后者适合流式写 |
| Set index（组索引） | Tag（标记） | 索引决定“去哪一组找”，tag 决定“组里哪条 line 是目标” |
| Conflict miss（冲突缺失） | Capacity miss（容量缺失） | 前者换一种映射/提高相联度可消除；后者只能增大缓存 |

## 8. 对应原版讲义

- PDF 相对路径：`90-原始PDF/15-213/lectures/10-cache-memories.pdf`
- 总页数：73 页
- 重点页码：
  - 缓存组织 S/E/B 与地址拆分：第 10–11 页
  - 直接映射示例与模拟：第 12–15 页
  - 组相联示例与模拟：第 16–19 页
  - 写策略与 dirty bit：第 20–21 页
  - Intel Core i7 缓存层次：第 22 页
  - 性能指标与平均访问时间：第 23–24 页
  - memory mountain：第 28–30、66–70 页
  - 矩阵乘缺失分析：第 32–43、71–73 页
  - 分块：第 45–51 页
  - 为什么用中间位做索引（附加页）：第 60–63 页
  - Core i7 L1 地址拆分练习：第 64–65 页
- 原始链接：https://www.cs.cmu.edu/~213/lectures/10-cache-memories.pdf

## 9. 对应视频

未找到官方公开录像。

## 10. 本节复习

- 缓存三参数：S 组、E 路、B 字节/块；地址 = tag | set index | block offset，位数分别是 t、s、b。
- 读流程：索引组 → 比较 valid 与 tag → 命中取偏移 / 缺失取块并驱逐。
- 直接映射 E = 1，组相联 E > 1，全相联 S = 1。
- 三类缺失：cold、capacity、conflict。
- 写策略两维：through/back × allocate/no-allocate；主流是 write-back + write-allocate。
- AMAT = hit time + miss rate × miss penalty；缺失代价是命中时间的几十到上百倍。
- 矩阵乘缺失率取决于内层循环是否 stride-1；kij/ikj 最优（0.5），jki/kji 最差（2.0）。
- 分块把缺失从 (9/8)n³ 降到 n³/(4B)，约束 3B² < C。

## 11. 自我检查

1. 一个缓存有 64 组、每组 4 路、块大小 32 字节，地址 48 位。写出 s、b、t 各多少位，并说明缓存总容量（数据部分）。
2. 给定地址序列 0, 4, 8, 0, 4（字节地址），缓存 S=2、E=1、B=4。列出每次访问的 tag/set/offset 与命中情况。
3. 为什么 write-back 缓存必须为每条 line 配一个 dirty bit，而 write-through 不需要？
4. 有人把矩阵乘 jki 版本的分块大小 B 设为 1000，而 L1 只有 32KB、元素为 double。会发生什么？应该怎么选 B？
5. 解释 memory mountain 上“斜坡”和“山脊”分别由什么局部性造成。

<details>
<summary>参考答案</summary>

1. S = 64 → s = 6；B = 32 → b = 5；t = 48 − 6 − 5 = 37 位。数据容量 = S × E × B = 64 × 4 × 32 = 8192 字节 = 8 KiB（不含 tag、valid、dirty 等开销）。

2. s = 1、b = 2、t = 1。
   - 0 = 00000：tag 0，set 0，off 0 → miss（装入 M[0-3]）
   - 4 = 00100：tag 0，set 1，off 0 → miss（装入 M[4-7]）
   - 8 = 01000：tag 1，set 0，off 0 → miss，set 0 原 tag 0 被驱逐（冲突缺失）
   - 0 = 00000：tag 0，set 0 → miss，又把 8 驱逐（冲突缺失）
   - 4 = 00100：tag 0，set 1 → hit（M[4-7] 仍在）
   总命中 1 次、缺失 4 次。

3. write-back 只在缓存里改数据，主存副本会过时；若驱逐时不写回，修改就丢了。dirty bit 记录“这条 line 与主存不一致”，只有它为 1 才需要写回，避免无谓的写流量。write-through 每次写都同步更新下一级，主存始终是最新的，不存在“未写回”的状态。

4. 三个 1000×1000 的 double 块各约 8MB，共 24MB，远大于 32KB L1，甚至超过 L2，3B² < C 完全不满足，分块退化为不分块，还会因频繁换入换出更慢。应按 3B² < C 选 B：若只用 L1（C ≈ 32KB），B ≤ sqrt(32768/3/8) ≈ 36（元素数），实际取 32 左右；若目标是 L2（256KB），B 可到约 100。工程上常取 32–64 并用实测调优。

5. 斜坡：固定 working set 大小、改变 stride。stride 越大，一个缓存块中被实际使用的字节越少，空间局部性变差，吞吐下降；stride ≥ 块大小/元素大小时每个元素都要新块。山脊：固定 stride（通常为 1）、改变 working set 大小。工作集依次超过 L1、L2、L3 容量时，命中率阶梯下降，吞吐出现台阶，台阶之间的平台就是“时间局部性”能覆盖的区域。

</details>

## 12. 进一步学习

- 下一讲：[[15-213-11-Virtual-Memory-Concepts]]
- 前一讲：[[15-213-09-Memory-Hierarchy]]
- 相关实验：[[00-Lab总览]]（Cache Lab 直接考缓存模拟与分块矩阵乘）
- 课程总览：[[20-CMU-15-213/00-课程总览|CMU 15-213 - 课程总览]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Cache、Cache Hit/Miss、Block/Cache Line、Throughput）
- CSAPP 第 3 版 6.4–6.7 节；6.6 的 mergesort 与矩阵乘案例可与本节对照阅读。
