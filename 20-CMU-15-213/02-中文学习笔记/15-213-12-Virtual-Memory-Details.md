---
course: CMU 15-213
course_name: Introduction to Computer Systems
semester: Fall 2026
lecture_id: L12
topic: Virtual Memory Details
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-213
  - 虚拟内存
  - 页表
  - TLB
  - 写时复制
---

# 虚拟内存：细节（Virtual Memory: Details）

## 1. 本节学习目标

- 能在 CSAPP 9.6.4 的“简单存储系统”上完整走一遍 VPN → TLBI/TLBT → PTE → PPN → CI/CT/CO → 数据 的全链路。
- 能区分硬缺失（major/hard fault）与软缺失（soft/minor fault）、保护异常、段错误。
- 能读懂 Intel Core i7 的 4 级页表与两级 TLB 参数，并说明为什么 L1 可以用 VIPT（虚拟索引物理标记）。
- 能解释 memory-mapped file 如何把文件页当作物理页的后备存储。
- 能说明 `fork` 的 copy-on-write（写时复制）如何只复制页表而不复制数据。

## 2. 前置知识

- [[15-213-11-Virtual-Memory-Concepts]]：页表、PTE、page fault 七步、TLB 结构、多级页表动机。
- [[15-213-10-Cache-Memories]]：S/E/B、tag/set/offset 拆分、直接映射与组相联——本节要把缓存和页表两层拆位叠在一起。
- 十六进制与二进制互转（本节大量依赖手工拆位）。

## 3. 核心概念

- **Hard / Major Fault（硬缺失/主缺失）**：页确实在磁盘上，必须读盘才能装入，代价极高。
- **Soft / Minor Fault（软缺失/次缺失）**：页仍在物理内存里（例如被 OS 暂时标记无效、或来自共享的页缓存），只需修正页表项，不读盘。
- **Protection Exception（保护异常）**：地址合法但访问类型不被允许（如写只读页），通常表现为 SIGSEGV。
- **Segmentation Fault（段错误）**：访问了不属于任何合法 VM area 的地址。
- **VM Area（虚拟内存区域）**：内核用 `vm_area_struct` 一类的结构记录进程每段地址范围的权限与用途，缺页时据此判断该地址是否合法。
- **PTE 标志位**：P（present）、R/W、U/S（user/supervisor）、WT（write-through）、A（accessed/reference）、D（dirty）、PS（page size）、XD（execute disable）、G（global）。
- **VIPT（Virtually Indexed, Physically Tagged，虚拟索引物理标记）**：用虚拟地址中与物理地址相同的那几位先索引缓存，同时并行做地址翻译，用物理页号做 tag 比较。
- **Memory-Mapped File（内存映射文件）**：把文件的页映射进进程虚拟地址空间，读写内存即读写文件页，由缺页机制按需装入。
- **Copy-on-Write（COW，写时复制）**：`fork` 时只复制页表并把两边的页标为只读，任一方写入触发保护异常，内核此时才复制该页。
- **Swap Space（交换空间）**：磁盘上用于存放被换出的匿名页的区域。

## 4. 通俗理解

上一讲建立了“虚拟内存是一层缓存”的框架，这一讲把它落到具体数字上。

打个比方：地址翻译像快递分拣。虚拟地址是客户填的“我家的门牌号”，物理地址是仓库里的真实货架位置。

- 先查 TLB（分拣员手边的小本子，记着最近用过的门牌→货架对应关系）：有记录就直接去货架。
- 没有记录就翻总账（页表）：i7 的总账分成 4 本，先查“全局目录”找到下一本在哪，再查“上层目录”……一共翻 4 次才拿到货架号。
- 货架上的东西可能不在（page fault），得去仓库外的卡车（磁盘）上取，慢得离谱。

`fork` 的 COW 则是另一个比喻：父母和孩子共用一套房间，门上贴“暂不可改动”。谁真要改动，物业才现场复制一份给他——绝大多数情况下孩子只是读，根本不需要复制。

## 5. 原理与推导

### 5.1 缺页的三种后果

讲义第 12–14 页把“缺页之后会怎样”分成三类：

| 情况 | 地址是否合法 | 内核动作 | 用户可见结果 |
|---|---|---|---|
| 合法地址，页在磁盘 | 合法 | 选 victim、写回脏页、读入新页、更新 PTE | 正常继续（major fault） |
| 合法地址，页还在内存 | 合法 | 只需修正 PTE，不读盘 | 正常继续（minor fault） |
| 合法地址，权限不符 | 合法 | 触发保护异常 | SIGSEGV，进程通常终止 |
| 非法地址 | 不合法 | 无法修复 | 段错误 / 总线错误，进程终止 |

关键：内核凭什么知道地址是否合法？靠 VM area 表（第 13 页）。每个 area 记录起止地址、权限（读/写/执行）、用途（代码、堆、栈、mmap 文件）。缺页时内核查这张表：

- 地址落在某个 area 内且权限匹配 → 合法缺失，去装入。
- 地址落在 area 内但权限不符 → 保护异常。
- 地址不在任何 area 内 → 段错误。

这就是为什么 `NULL` 指针解引用会段错误：地址 0 附近根本没有 area。

### 5.2 简单存储系统（CSAPP 9.6.4）的参数

讲义第 19–22 页给出一套可以手工算完的完整系统：

- 虚拟地址 **14 位**，物理地址 **12 位**，页大小 **64 字节**（2^6）。
- 因此 VPO = PPO = 6 位，VPN = 14 − 6 = 8 位，PPN = 12 − 6 = 6 位。
- **TLB**：16 项、4 路 → 4 组，TLBI = 2 位，TLBT = 8 − 2 = 6 位。
- **页表**：2^8 = 256 项（讲义只展示前 16 项）。
- **Cache**：16 行、行大小 4 字节、直接映射、物理寻址 → CI = 4 位、CO = 2 位、CT = 12 − 4 − 2 = 6 位。

位域叠起来看：

```
虚拟地址(14): | VPN(8) | VPO(6) |
VPN 内部    : | TLBT(6) | TLBI(2) |
物理地址(12): | PPN(6) | PPO(6) |
PPO 内部    : |  CT(6) | CI(4) | CO(2) |
```

注意最后一行：**cache 的 tag/set/offset 是在物理地址上切的**，其中 CI 与 CO 落在 PPO 内（即与 VPO 相同），CT 落在 PPN 内。

### 5.3 全链路实例：VA = 0x369

讲义第 20–22 页的经典例子，逐步推：

1. **拆虚拟地址**：0x369 = 0b00_0011_0110_1001（14 位）。
   - VPN = 高 8 位 = 0b00001101 = **0x0D**
   - VPO = 低 6 位 = 0b101001 = **0x29**

2. **查 TLB**：VPN = 0x0D = 0b001101。
   - TLBI = 低 2 位 = 0b01 = **1** → 第 1 组
   - TLBT = 高 6 位 = 0b0011 = **0x03**
   - 第 1 组中存在一项 valid = 1、tag = 0x03、PPN = **0x2D** → **TLB 命中**
   - 命中后不必访问页表。

3. **（若 TLB 未命中）查页表**：以 VPN = 0x0D 为下标，PTE 显示 valid = 1、PPN = **0x2D**，与 TLB 一致。

4. **拼物理地址**：PA = PPN ‖ PPO = 0x2D ‖ 0x29。
   - 0x2D = 0b101101，0x29 = 0b101001
   - PA = 0b1011_0110_1001 = **0xB69**

5. **拆物理地址查 cache**：PA = 0xB69 = 0b1011_0110_1001。
   - CO = 低 2 位 = 0b01 = **1**
   - CI = 中间 4 位 = 0b1010 = **0xA**
   - CT = 高 6 位 = 0b101101 = **0x2D**

6. **查 cache 第 0xA 行**：valid = 1、tag = 0x2D，与 CT 相符 → **cache 命中**，取出块内偏移 1 的字节 = **0x15**。

讲义第 22 页的结论一行就是：`V[0b00001101101001] = V[0x369]`，`P[0b101101101001] = P[0xB69] = 0x15`。

这个例子值得亲手做三遍，因为它把三套拆分（页、TLB、cache）在同一串位上串起来了。考试和 cachelab 都吃这一套。

### 5.4 Intel Core i7 的层次

讲义第 23 页：

| 组件 | 容量 | 相联度 | 说明 |
|---|---|---|---|
| L1 i-cache | 32 KB | 8 路 | 指令 |
| L1 d-cache | 32 KB | 8 路 | 数据 |
| L2 统一缓存 | 256 KB | 8 路 | 每核私有 |
| L3 统一缓存 | 8 MB | 16 路 | 全核共享 |
| L1 d-TLB | 64 项 | 4 路 | 数据页 |
| L1 i-TLB | 128 项 | 4 路 | 指令页 |
| L2 统一 TLB | 512 项 | 4 路 | 两级 TLB |

内存侧：DDR3 控制器 3×64 位 @ 10.66 GB/s，合计 32 GB/s 全核共享；QuickPath 互连 4 链路 @ 25.6 GB/s。

### 5.5 端到端 i7 翻译（第 24、27 页）

虚拟地址 48 位（实际使用 48 位，VPN 36 位），物理地址 52 位（PPN 40 位）。

**4 级页表，每级 9 位索引**：

```
VA(48): | VPN1(9) | VPN2(9) | VPN3(9) | VPN4(9) | VPO(12) |
PA(52): |        PPN(40)         | PPO(12) |
```

每级 9 位正好索引 512 个 PTE，每个 PTE 8 字节 → 512 × 8 = 4KB，恰好一页，这就是“页表节点本身是一页”的落地。

各级覆盖的地址范围（第 27 页）：

| 级别 | 名称 | 单个 PTE 覆盖 |
|---|---|---|
| L1（最上层） | Page global directory | 512 GB 区域 |
| L2 | Page upper directory | 1 GB 区域 |
| L3 | Page middle directory | 2 MB 区域 |
| L4（最下层） | Page table | 4 KB 区域 |

**TLB 拆分（第 24 页）**：L1 d-TLB 16 组 × 4 项 → TLBI 4 位、TLBT 32 位（36 − 4）。TLB 命中直接得到 40 位 PPN。

**L1 cache 拆分（第 24 页）**：64 组 × 8 行 → CI 6 位、CO 6 位、CT 40 位。

TLB 缺失时，MMU 依次读 4 个 PTE（第 10 页标注了四次 “Cache miss!”），每次都可能是一次完整的内存访问——这就是为什么 TLB 如此重要。

### 5.6 PTE 的标志位

讲义第 25–26 页。L1–L3 的 PTE 指向下一级页表，字段包括：

- **P**：子页表是否在物理内存中。
- **R/W**：其下所有可达页的读/写权限。
- **U/S**：用户态或内核态可访问。
- **WT**：子页表的缓存写策略（write-through 或 write-back）。
- **A**：引用位，MMU 在读写时置 1，由软件清零——用于实现 LRU 近似。
- **PS**：页大小，4KB 或 4MB，只在 L1 PTE 中有意义。
- **XD**：禁止从这些页取指令（NX 位）。
- 高 40 位是页表物理基址（强制 4KB 对齐）。

L4 的 PTE 指向真实页，字段多一个 **D（dirty）** 和 **G（global，任务切换时不从 TLB 驱逐）**，少一个 PS。

对照上一讲的“VM 参数”表：A 位支撑替换策略，D 位支撑 write-back，U/S + R/W + XD 支撑保护。抽象概念在这里全部变成具体比特。

### 5.7 VIPT：让 L1 与翻译并行

问题（第 28 页）：如果严格先翻译再查 L1，每次访问都要等 MMU，L1 的 4 周期延迟就白费了。

观察：**决定 CI 的那些位，在虚拟地址和物理地址中完全相同**。因为 CI 落在 PPO 范围内，而 PPO = VPO。

于是可以：

1. 用 VA 的低位（VPO 中的 CI 部分）立刻索引 L1 的组，同时把 VPN 送进 TLB。
2. TLB 通常命中，很快拿到 PPN，取出 CT。
3. 用 CT 与 L1 中被索引行的 tag 比较，确认命中。

这就是 **virtually indexed, physically tagged**。约束是缓存必须“小心地设定大小”：CI 的位数不能超过页内偏移位数（12 位），否则索引会用到 VPN 位，同一物理页在不同虚拟地址下会落到不同组，产生别名问题。i7 的 L1 是 32KB、8 路、64B 块 → 64 组，CI 只需 6 位，远小于 12，安全。

### 5.8 Memory-Mapped Files

讲义第 31–33 页。

前提：分页的本质是“程序物理内存中的每一页，背后都有磁盘上的某一页作为后备”。传统上这些后备页来自 swap space。

新想法：**如果后备页来自一个文件呢？**

于是：

- `mmap` 把文件的某段映射进进程地址空间，PTE 初始 valid = 0。
- 第一次访问触发缺页，内核从文件读入对应页，PTE 指向它。
- 之后读写内存就是在读写文件页；脏页被驱逐时写回文件。
- **多个进程映射同一文件时，它们的 PTE 可以指向同一个物理页**（第 33 页），于是文件天然成为进程间共享内存。

这解释了为什么可执行文件不需要先“读进内存”再执行：`execve` 只是建立映射，代码页按需从可执行文件装入，只读代码页还能被多个运行同一程序的进程共享。

### 5.9 Copy-on-Write

讲义第 34–37 页。

`fork` 的语义是“复制整个地址空间”，听起来就慢，实际上也慢——如果真复制的话。

实际做法：

1. 复制父进程的**页表**（不是数据页）。
2. 把父子两边所有可写页的 PTE 都改成**只读**，并标记为 COW。
3. 父或子任意一方写入 → 保护异常 → 内核检查发现是 COW 页 → 分配一个新物理页、复制内容、把写入方的 PTE 指向新页并恢复可写。

效果：`fork` 的代价从“复制所有数据”降到“复制页表”。而 `fork` 后立刻 `execve` 的常见用法（shell 执行命令）根本不会写任何页，复制完全省掉。

第 37 页的图显示：只有 child 写过的那一页被真正复制，其余仍共享。

### 5.10 概念问答（讲义第 38–41 页）

- **为什么单级页表不实用？** 48 位地址、4KB 页、8 字节 PTE → 512GB，比大多数机器的内存还大。
- **为什么多级页表更慢？** k 级需要 k 次内存加载才能得到物理地址，而且这 k 次加载之间**没有空间局部性**（每次都在不同的页表页）。
- **TLB 是什么、解决什么问题、何时使用？** 专门缓存虚拟→物理映射的小缓存；避免多级页表查找的开销；MMU 对**每个地址**的第一个动作就是查 TLB。
- **VM 如何与 cache 交互？** cache 只认物理地址，MMU 夹在 CPU 与 cache 之间；因此多个进程的数据会共存于同一个 cache 中，也会互相竞争 cache 空间。

最后一点值得留意：这意味着一个进程的行为可以影响另一个进程的缓存命中率——这是侧信道攻击（如 Prime+Probe）的物理基础。

## 6. 代码示例

### 6.1 官方课程内容

**简单存储系统的 TLB 表（12-vm-details.pdf 第 20 页）**：16 项、4 路，每项含 Valid / Tag / PPN。第 1 组（Set 1）含 tag 0x03、PPN 0x2D 的有效项，正是 VA = 0x369 的命中来源。

**页表片段（12-vm-details.pdf 第 21 页）**：只展示前 16 项，其中 VPN 0x0D → PPN 0x2D（valid = 1）。

**cache 表（12-vm-details.pdf 第 22 页）**：16 行、4 字节行、直接映射，第 0xA 行 valid = 1、tag = 0x2D，块内字节（按 B3 B2 B1 B0）= 3B DA 15 93，偏移 1 处为 0x15。

**Core i7 的 4 级翻译图（12-vm-details.pdf 第 24、27 页）**：CR3 → L1 PT → L2 PT → L3 PT → L4 PT → PPN，每级 9 位索引，PTE 8 字节。

**COW 示意图（12-vm-details.pdf 第 34–37 页）**：父子进程的虚拟内存箭头最初指向同一批物理页，child 写入后只有那一页分叉。

本讲没有给出可运行的 C 代码，全部是结构与数值示例。

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

用 Python 复现 5.3 节的全链路，便于批量验证其它地址：

```python
# 非官方示例：CSAPP 9.6.4 简单存储系统的完整翻译
VA_BITS, PA_BITS, PAGE_BITS = 14, 12, 6
TLB_SETS, TLB_WAYS = 4, 4
CACHE_SETS, CACHE_LINE = 16, 4

# 页表：VPN -> (valid, PPN)
page_table = {0x00: (1, 0x28), 0x02: (1, 0x33), 0x03: (1, 0x02),
              0x05: (1, 0x16), 0x08: (1, 0x13), 0x09: (1, 0x17),
              0x0A: (1, 0x09), 0x0D: (1, 0x2D), 0x0E: (1, 0x11),
              0x0F: (1, 0x0D)}

# TLB：set -> list of (tag, ppn)
tlb = {1: [(0x03, 0x2D)], 3: [(0x03, 0x07)]}

# cache：index -> (tag, [b0, b1, b2, b3])
cache = {0xA: (0x2D, [0x93, 0x15, 0xDA, 0x3B])}

def translate(va):
    vpn = va >> PAGE_BITS
    vpo = va & ((1 << PAGE_BITS) - 1)
    tlbi = vpn & (TLB_SETS - 1)
    tlbt = vpn >> 2                       # 2 位 TLBI
    ppn = None
    for tag, p in tlb.get(tlbi, []):
        if tag == tlbt:
            ppn = p
            print(f"  TLB hit  TLBT=0x{tlbt:02X} TLBI={tlbi}")
            break
    if ppn is None:
        print(f"  TLB miss TLBT=0x{tlbt:02X} TLBI={tlbi}")
        valid, ppn = page_table[vpn]
        if not valid:
            raise RuntimeError("page fault")
    pa = (ppn << PAGE_BITS) | vpo
    ci = (pa >> 2) & (CACHE_SETS - 1)
    co = pa & 0x3
    ct = pa >> 6
    print(f"  VA=0x{va:04X} VPN=0x{vpn:02X} VPO=0x{vpo:02X} "
          f"PA=0x{pa:03X} CT=0x{ct:02X} CI=0x{ci:X} CO={co}")
    if ci in cache and cache[ci][0] == ct:
        print(f"  cache hit -> 0x{cache[ci][1][co]:02X}")
    else:
        print("  cache miss")

translate(0x369)   # 应输出 TLB hit, PA=0xB69, cache hit -> 0x15
```

下面是一个观察 COW 的小程序（Linux）：

```c
/* 非官方示例：观察 fork 后的写时复制 */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>

int main(void) {
    int *p = malloc(sizeof(int));
    *p = 100;
    pid_t pid = fork();
    if (pid == 0) {          /* 子进程 */
        printf("child before write: %d (%p)\n", *p, (void *)p);
        *p = 200;            /* 这一写触发 COW，复制出一个新物理页 */
        printf("child after  write: %d (%p)\n", *p, (void *)p);
        _exit(0);
    }
    wait(NULL);
    printf("parent sees: %d (%p)\n", *p, (void *)p);  /* 仍是 100 */
    free(p);
    return 0;
}
```

两个进程打印的虚拟地址完全相同（因为页表是复制的），但父进程看到的值仍是 100——写时复制保证了语义上的“完全独立”，同时避免了实际的复制开销。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| Major fault（硬缺失） | Minor fault（软缺失） | 前者要读磁盘，后者只需修正 PTE；`ps`/`/usr/bin/time` 能分别统计 |
| Protection exception（保护异常） | Segmentation fault（段错误） | 前者地址合法但权限不符；后者地址根本不合法 |
| TLB tag | Cache tag | 前者来自 VPN 的高位，后者来自 PPN 的高位；两者比较的对象完全不同 |
| VPO | PPO | 数值相同，但一个属于虚拟地址、一个属于物理地址；正是因为相同，才有 VIPT |
| Memory-mapped file | Swap | 前者后备是文件，改动会持久化；后者后备是匿名交换区，进程退出即丢弃 |
| `fork` 的语义 | `fork` 的实现 | 语义是复制整个地址空间；实现是复制页表 + COW |
| PTE 的 A 位 | PTE 的 D 位 | A（accessed）记录“被访问过”，用于替换；D（dirty）记录“被写过”，用于决定是否写回 |

## 8. 对应原版讲义

- PDF 相对路径：`90-原始PDF/15-213/lectures/12-vm-details.pdf`
- 总页数：41 页
- 重点页码：
  - 复习：无 VM 与有 VM 的访问路径、page fault 分支：第 5–8 页
  - 单级页表 512GB 问题与 k 级页表的多次 cache miss：第 9–10 页
  - 缺页的三种后果：第 12–14 页
  - 概念问答 1–2：第 16–17 页
  - 简单存储系统参数与位域：第 19 页
  - TLB 表与 VA=0x369 的 TLB 命中：第 20 页
  - 页表片段：第 21 页
  - cache 表与最终取值 0x15：第 22 页
  - Core i7 存储层次：第 23 页
  - 端到端翻译图：第 24 页
  - L1–L3 与 L4 PTE 字段：第 25–26 页
  - 4 级页表各级覆盖范围：第 27 页
  - VIPT 技巧：第 28 页
  - memory-mapped files：第 31–33 页
  - copy-on-write：第 34–37 页
  - 总结与概念问答 3–6：第 38–41 页
- 原始链接：https://www.cs.cmu.edu/~213/lectures/12-vm-details.pdf
- 注意：讲义打印页码与 PDF 页码在第 34 页之后相差 1（PDF 第 34 页印着 “35”），引用时以 PDF 页码为准。

## 9. 对应视频

未找到官方公开录像。

## 10. 本节复习

- 缺页三类后果：合法且需读盘（major）、合法且页仍在内存（minor）、权限不符（protection）、地址非法（segfault）。
- 内核靠 VM area 表判断地址合法性与权限。
- 简单系统：14 位 VA、12 位 PA、64B 页；TLB 16 项 4 路（TLBI 2、TLBT 6）；cache 16 行 4B 直接映射（CI 4、CO 2、CT 6）。
- VA 0x369 → VPN 0x0D、VPO 0x29 → TLB 命中 PPN 0x2D → PA 0xB69 → CI 0xA、CO 1、CT 0x2D → 0x15。
- i7：4 级页表，9/9/9/9/12；VPN 36 位、PPN 40 位；L1 32KB 8 路 64 组；L1 d-TLB 64 项 4 路。
- VIPT：CI 与物理地址一致，可与翻译并行；要求 CI 位数 ≤ 页内偏移位数。
- mmap 让文件成为页的后备存储，实现共享；COW 让 `fork` 只复制页表。

## 11. 自我检查

1. 在 CSAPP 9.6.4 的简单系统中，虚拟地址 0x1C4 的 VPN、VPO、TLBI、TLBT 各是多少？若页表中 VPN 0x07 有效且 PPN = 0x0B，物理地址是多少？CT、CI、CO 各是多少？
2. 一个缺页异常发生后，内核在什么情况下判定它是段错误而不是合法缺失？
3. 为什么 i7 的 L1 cache 可以做到 VIPT，而一个 128KB、8 路、64B 块的 L1 就不行（假设页 4KB）？
4. `fork` 之后父子进程各自写同一变量，为什么不会互相影响？内核在这一过程中做了什么？
5. memory-mapped file 与普通 `read`/`write` 读文件相比，各有什么优劣？

<details>
<summary>参考答案</summary>

1. 0x1C4 = 452 = 0b00_0111_0001_00（补齐 14 位）。
   - VPO = 低 6 位 = 0b000100 = 0x04
   - VPN = 高 8 位 = 0b00000111 = 0x07
   - TLBI = VPN 低 2 位 = 0b11 = 3；TLBT = VPN 高 6 位 = 0b000001 = 0x01
   - PA = PPN ‖ PPO = 0x0B ‖ 0x04 = 0b001011_000100 = 0x2C4
   - PA = 0x2C4 = 0b0010_1100_0100 → CO = 低 2 位 = 0b00 = 0；CI = 中间 4 位 = 0b0001 = 1；CT = 高 6 位 = 0b001011 = 0x0B

2. 内核查 VM area 表：若该地址不落在进程任何已注册的 area 内，则不是合法缺失，报段错误（或总线错误）；若落在 area 内但访问类型违反该 area 的权限（如向只读代码段写入），则报保护异常。只有落在 area 内且权限匹配的缺失才被当作正常缺页处理。

3. 判据是 CI 的位数是否超过页内偏移位数（4KB 页 → 12 位）。128KB、8 路、64B 块 → 组数 = 128K / (8×64) = 256 → CI 需 8 位，8 ≤ 12，**其实仍然可以 VIPT**。要让它失效需要更大的缓存：例如 2MB、8 路、64B → 组数 = 4096 → CI 需 12 位，已经用满页内偏移；再大（如 4MB）就需要 13 位，索引会用到 VPN 位，同一物理页在不同虚拟地址下会落到不同组，产生别名，必须靠硬件反别名或限制映射来补救。i7 的 L1 是 32KB、8 路、64B → 64 组 → CI 仅 6 位，余量很大，所以安全。

4. `fork` 时内核复制父进程的页表，并把两边的可写页都标记为只读且标记 COW，物理页仍然共享。任一方写入触发保护异常，内核识别为 COW 页，分配新物理页、复制原内容、更新写入方的 PTE 指向新页并恢复可写。此后两者各写各的物理页，互不影响，而虚拟地址保持不变。

5. mmap 的优点：按需分页，只读文件的一段不必全部载入；多进程映射同一文件可共享物理页；随机访问大文件方便，不需要自己管理缓冲区；内核负责预读与回写。缺点：缺页与 TLB 开销；文件被截断或修改时可能收到 SIGBUS；不适合流式顺序处理的简单场景，小文件用 `read` 更直接。`read`/`write` 的优点：语义简单、可控、有明确的返回值与错误处理；缺点：数据要经过内核缓冲区复制一次，大文件随机访问需要自己 `lseek` 并管理缓存。

</details>

## 12. 进一步学习

- 下一讲：[[15-213-13-Dynamic-Memory-Allocation-Basic]]
- 前一讲：[[15-213-11-Virtual-Memory-Concepts]]
- 课程总览：[[20-CMU-15-213/00-课程总览|CMU 15-213 - 课程总览]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Virtual Memory、Page、Fork/Exec、File Descriptor）
- CSAPP 第 3 版 9.7–9.8 节；9.7 的案例研究（简单系统与 i7）与本节 5.2–5.6 一一对应，建议对照书中表格重做一遍 VA = 0x369 的翻译。
