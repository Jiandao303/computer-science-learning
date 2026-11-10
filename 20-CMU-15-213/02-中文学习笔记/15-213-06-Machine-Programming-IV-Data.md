---
course: CMU 15-213
course_name: Introduction to Computer Systems
semester: Fall 2026
lecture_id: L06
topic: Machine Programming IV - Data
language: zh-CN
source_language: en
status: draft
tags:
  - CMU-15-213
  - 汇编语言
  - 结构体
  - 内存对齐
  - 缓冲区溢出
  - 栈保护
  - ROP
  - 联合体
---

# L06 Machine Programming IV: Data（机器级编程 IV：数据）

> 开课日期：2026 年 9 月 10 日。本讲是机器级编程的收尾：先把结构体与对齐讲完，再画一张进程的完整内存地图，然后用整讲的篇幅讲**缓冲区溢出**——一个 4 字节的 `char buf[4]` 如何变成任意代码执行。最后是 union 与字节序。

## 1. 本节学习目标

1. 计算结构体数组的步长（含对齐填充），并说明为什么「元素之间没有额外填充」仍能保证每个元素对齐。
2. 说明重排字段顺序如何省空间，以及编译器为什么不自动重排。
3. 画出 x86-64 Linux 的四段内存布局（Stack / Heap / Data / Text），并判断一个变量落在哪一段。
4. 解释 `gets` 为什么不可修复，列出至少三个安全替代品。
5. 逐字节构造一个覆盖返回地址的攻击串，并说明偏移量的计算方法。
6. 说明栈随机化（ASLR）、不可执行栈（NX）、栈金丝雀（canary）三种防护各自挡住什么、挡不住什么。
7. 说明 ROP（return-oriented programming）如何绕过 NX，以及 gadget 的构造方式。
8. 说明 union 的内存分配规则，以及它和 struct 在大小上的差别。
9. 用 union 观察小端/大端字节序。

## 2. 前置知识

- **L05**：栈帧布局、`call`/`ret`、参数寄存器、结构体偏移与对齐规则。
- **L04**：`push`/`pop`、`call`/`ret` 的栈语义。
- **L02**：字节序、`0x` 十六进制表示。
- **C 语言**：数组越界、`char` 字符串与 `'\0'` 结尾、`union`、`malloc`。

## 3. 核心概念

- **Array of Structures（结构体数组）**：元素连续存放，步长 = `sizeof(struct)`（含填充）。
- **Memory Layout（内存布局）**：进程地址空间的四段划分：Stack、Heap、Data、Text。
- **Buffer Overflow（缓冲区溢出）**：写入超过数组容量的数据，覆盖相邻内存。
- **Stack Smashing（栈粉碎）**：溢出发生在栈上的缓冲区，覆盖返回地址。
- **Code Injection（代码注入）**：把可执行机器码放进缓冲区，再让返回地址指向它。
- **Stack Canary（栈金丝雀）**：放在缓冲区与返回地址之间的哨兵值，返回前检查是否被改。
- **ASLR（Address Space Layout Randomization，地址空间布局随机化）**：每次运行随机化栈/堆/库的基址。
- **NX（No-eXecute，不可执行）**：把栈与堆标记为不可执行。
- **ROP（Return-Oriented Programming，返回导向编程）**：串联已有代码片段（gadget）构造攻击。
- **Gadget（代码片段）**：以 `ret`（`0xc3`）结尾的一小段指令序列。
- **Union（联合体）**：所有字段共享同一块内存，大小取最大字段。
- **Little Endian（小端序）**：最低有效字节放在最低地址（x86）。

## 4. 通俗理解

**缓冲区溢出像往杯子里倒水。** 杯子只有 4 毫升（`char buf[4]`），你却倒了 24 毫升。多出来的 20 毫升流到桌上——桌上放着什么，就被泡坏什么。如果桌上放的是「下一站去哪」的纸条（返回地址），你就能让程序去你指定的地方。

**栈金丝雀像封条。** 在杯子和纸条之间贴一张易碎封条。倒水时若封条破了，函数返回前会检查并报警（`__stack_chk_fail`）。名字来自矿井里的金丝雀——它对毒气敏感，先死，矿工就知道该跑。

**ROP 像用乐高积木拼武器。** 你被禁止带新积木进场（栈不可执行），但场里到处都是现成的积木（程序自己的代码）。每块积木末尾都有个凸起（`ret`），正好能接上下一块。用现成的积木，也能拼出想要的东西。

## 5. 原理与推导

### 5.1 结构体数组

讲义 p4–p6 复习 `struct rec`：

```c
struct rec {
    int a[4];          // 偏移 0，16 字节
    size_t i;          // 偏移 16，8 字节
    struct rec *next;  // 偏移 24，8 字节
};                     // 总大小 32，K = 8
```

**`get_ap`**（讲义 p5）：

```asm
# r in %rdi, idx in %rsi
leaq (%rdi,%rsi,4), %rax    # r + 4*idx
ret
```

**`length`**（讲义 p6）：

```asm
.L11:
    addq $1, %rax            # len++
    movq 24(%rdi), %rdi      # r = Mem[r+24]
    testq %rdi, %rdi
    jne  .L11
```

**结构体数组**（讲义 p11–p12）：`struct S2 a[10]`。

讲义 p11 给出关键推理链：

1. 结构体长度是 K 的倍数（`S2` 长 24，K = 8）。
2. 起始地址 `a` 是 K 的倍数。
3. 元素之间**没有额外填充**。
4. 因此 `a + 24*n` 也是 K 的倍数——**整个数组里每个元素都自动满足对齐**。

这是「末尾外部填充」的真正用途：它不是浪费，而是让「按 `sizeof` 步进」这件事本身就能保持对齐。少了它，`a[1]` 就可能落在非 8 倍数地址上。

**`struct S3 { short i; float v; short j; } a[10];`**（讲义 p12）：

| 字段 | 偏移 | 大小 | 说明 |
|---|---|---|---|
| `i` | 0 | 2 | |
| （填充） | 2–3 | 2 | 使 `v` 落在 4 的倍数 |
| `v` | 4 | 4 | |
| `j` | 8 | 2 | |
| （填充） | 10–11 | 2 | 使总长为 K=4 的倍数 |

`sizeof(struct S3) = 12`，K = 4。

```asm
short get_j(int idx) { return a[idx].j; }

# %rdi = idx
leaq   (%rdi,%rdi,2), %rax     # 3*idx
movzwl a+8(,%rax,4), %eax      # a + 12*idx + 8，读 2 字节零扩展
```

**两个细节**：

1. **`3*idx` 再乘 4 = 12*idx**：因为 scale 只能是 1/2/4/8，没有 12，所以先算 `3*i` 再乘 4（和 L05 里算 `20*i` 是同一套路）。
2. **`movzwl`（move zero-extended word to long）**：读 2 字节（word）并零扩展成 4 字节。因为返回值类型是 `short`，写 `%eax` 会自动把高 16 位清零，符合 C 的整型提升规则。若用 `movw` 会留下 `%eax` 的高位垃圾。
3. **`a+8` 是链接期才解析的偏移**：`a` 是全局数组，其地址在链接时才确定（见 L07），所以汇编里写成符号 `a` 加常量偏移。

**重排字段省空间**（讲义 p13）：

| 结构体 | 字段顺序 | 布局 | 大小 |
|---|---|---|---|
| `S4` | `char c; int i; char d;` | `c`@0，填充 3，`i`@4，`d`@8，填充 3 | **12** |
| `S5` | `int i; char c; char d;` | `i`@0，`c`@4，`d`@5，填充 2 | **8** |

**同样的三个字段，顺序不同差 4 字节（33%）。** 讲义 p60 解释编译器为什么不自动重排：

- 编译器**必须**遵循声明顺序（C 标准要求，且字段顺序影响 ABI）。
- 有些顺序有语义理由：程序员理解性、常用字段相邻（提高缓存局部性）。

所以「大字段优先」是程序员的责任，不是编译器的。

### 5.2 x86-64 Linux 内存布局

讲义 p16：

```
0x00007FFFFFFFFFFF  ┌─────────────────┐
                    │  Stack          │  8 MB 上限，%rsp 在此
0x00007FFFF8000000  ├─────────────────┤
                    │  （随机化空隙）  │
                    │  Shared Libraries│
                    ├─────────────────┤
                    │  （随机化空隙）  │
                    │  Heap           │  malloc 向上生长
                    ├─────────────────┤
                    │  Data           │  全局/静态变量、字符串常量
                    │  （.bss/.data） │
0x0000000000400000  ├─────────────────┤
                    │  Text           │  可执行指令，只读
0x0000000000001000  └─────────────────┘
```

讲义 p16 标注：栈上限 8 MB；`0x00007FFFFFFFFFFF - 4096` 是栈顶；Text 从 `0x400000` 开始（这是 Linux 默认的非 PIE 可执行文件基址）；Heap 与 Shared Libraries 之间、库与栈之间各有一段随机化空隙。

**`char big_array[1L<<24]`（16 MB）与 `char huge_array[1L<<31]`（2 GB）放哪？** 讲义 p17 提出问题，p18 给出实测答案：

| 对象 | 地址 | 段 |
|---|---|---|
| `local` | `0x00007ffe4d3be87c` | Stack |
| `phuge1`（malloc 256 MB） | `0x00007f7262a1e010` | mmap 区（大块 malloc） |
| `phuge3`（malloc 4 GB） | `0x00007f7162a1d010` | mmap 区 |
| `psmall2`（malloc 256 B） | `0x000000008359d010` | Heap |
| `psmall4`（malloc 256 B） | `0x000000008359d120` | Heap |
| `big_array`（16 MB 全局） | `0x0000000080601060` | Data（.bss） |
| `huge_array`（2 GB 全局） | `0x0000000000601060` | Data（.bss） |
| `main()` | `0x000000000040060c` | Text |
| `useless()` | `0x0000000000400590` | Text |

**三个观察**：

1. **大块 malloc 走 mmap**：`phuge1`、`phuge3` 的地址在 `0x7f...` 区间（与共享库同一区域），而小块的 `psmall2`/`psmall4` 在 `0x83...`（紧邻 .bss 的 heap）。glibc 的 `malloc` 对超过 `MMAP_THRESHOLD`（默认 128 KiB）的请求直接用 `mmap`。
2. **`big_array` 与 `huge_array` 地址相差极小**（`0x80601060` vs `0x601060`），但 `huge_array` 声明在前——因为 .bss 段从低地址开始，2 GB 的 `huge_array` 占了 `0x601060` 到 `0x80601060`，16 MB 的 `big_array` 紧接着放在后面。**注意 `0x80601060` 已经超过了经典的 `0x400000`–`0x800000` 区间**，这就是为什么现代 Linux 的可执行文件基址会更高（ASLR 生效）。
3. **栈地址 `0x7ffe...` 每次运行都不同**——这就是 ASLR。

> 待核实：讲义 p18 的地址来自一次具体运行，讲义本身标注「Exact values can vary」。不同内核/发行版的布局细节（尤其 .bss 与 heap 的相对位置、`0x400000` 基址是否仍适用）会有差异。

### 5.3 缓冲区溢出：从 bug 到漏洞

**入门示例**（讲义 p20）：

```c
typedef struct { int a[2]; double d; } struct_t;

double fun(int i) {
    volatile struct_t s;
    s.d = 3.14;
    s.a[i] = 1073741824;   /* Possibly out of bounds */
    return s.d;
}
```

实测结果（讲义 p20）：

| `i` | 返回的 `s.d` | 实际访问的位置 |
|---|---|---|
| 0 | 3.1400000000 | `a[0]` |
| 1 | 3.1400000000 | `a[1]` |
| 2 | 3.1399998665 | `d` 的低 4 字节（d3…d0） |
| 3 | 2.0000006104 | `d` 的高 4 字节（d7…d4） |
| 4 | Segmentation fault | 越过结构体（栈帧外） |
| 6 | （另一版本：stack smashing detected） | 更远 |
| 8 | （另一版本：Segmentation fault） | 更远 |

讲义 p20 的图把位置标成 `struct_t`(0)、`a[0]`(1)、`a[1]`(2)、`d3...d0`(3)、`d7...d4`(4)、`Critical State`(5–8)。

**为什么 `fun(2)` 得到 3.1399998665 而不是 3.14？** 因为 `s.a[2] = 1073741824`（即 `0x40000000`）覆盖了 `d` 的低 4 字节。`3.14` 的 IEEE 754 双精度表示是 `0x40091EB851EB851F`，低 32 位 `0x51EB851F` 被换成 `0x40000000`，于是变成 `0x40091EB840000000` ≈ 3.1399998665。

**这是「类型系统只是幻觉」的最强证明**：内存里只有字节，写 `int` 却改了 `double`，机器不会阻止你。

**缓冲区溢出的定义**（讲义 p22）：写入超出数组分配大小的数据。讲义 p22 说：「多年来它是安全漏洞的**第一大技术原因**」（总第一是社工/用户无知）。最常见形态是**字符串输入不检查长度**，尤其是栈上的定长 `char` 数组——即「栈粉碎（stack smashing）」。

**罪魁祸首 `gets`**（讲义 p23）：

```c
char *gets(char *dest) {
    int c = getchar();
    char *p = dest;
    while (c != EOF && c != '\n') {
        *p++ = c;
        c = getchar();
    }
    *p = '\0';
    return dest;
}
```

**`gets` 的接口里根本没有长度参数**——它不是「实现有 bug」，而是「设计上无法安全使用」。这就是为什么 C11 把它从标准里删掉了。

同类问题函数（讲义 p23）：`strcpy`、`strcat`（复制任意长度字符串）、`scanf`/`fscanf`/`sscanf` 用 `%s`（无宽度限制）。

**脆弱代码**（讲义 p24）：

```c
void call_echo() { echo(); }

void echo() {
    char buf[4];   /* Way too small! */
    gets(buf);
    puts(buf);
}
```

**反汇编**（讲义 p25）：

```asm
000000000040069c <echo>:
  40069c: 48 83 ec 18        sub    $0x18,%rsp      # 分配 24 字节
  4006a0: 48 89 e7           mov    %rsp,%rdi       # 参数 = buf
  4006a3: e8 a5 ff ff ff     callq  40064d <gets>
  4006a8: 48 89 e7           mov    %rsp,%rdi
  4006ab: e8 50 fe ff ff     callq  400500 <puts@plt>
  4006b0: 48 83 c4 18        add    $0x18,%rsp
  4006b4: c3                 retq
```

**`sub $0x18`（24 字节）里只有 4 字节是 `buf`，其余 20 字节是「未使用」的填充**（讲义 p26 标为「20 bytes unused」）。为什么？因为 ABI 要求 `%rsp` 16 字节对齐，`4` 字节的缓冲区需要向上取整到 24 才能让 `call` 后的对齐正确。

**栈布局**（讲义 p26，从低地址到高地址）：

```
%rsp →  [3][2][1][0]  buf（4 字节）
        20 bytes unused
        Return Address (8 bytes)  ← 0x000000000040 06c3
```

**实测**（讲义 p27–p28）：

```
输入 23 个字符 "01234567890123456789012"
→ 正常回显，程序正常退出（溢出到 20 字节未使用区，没碰到返回地址）

输入 24 个字符 "012345678901234567890123"
→ 回显后 Segmentation fault
```

**24 个字符为什么崩？** 4（buf）+ 20（unused）= 24 字节刚好填满到返回地址之前；第 25 个字节是 `'\0'`（`gets` 自动加的），它覆盖了返回地址的**最低字节**。

原返回地址 `0x00000000004006c3` 在内存里是小端存放：`c3 06 40 00 00 00 00 00`。`'\0'` 覆盖 `c3` 后变成 `00 06 40 00 00 00 00 00` = **`0x0000000000400600`**。讲义 p28 明确写：「Program "returned" to 0x0400600, and then crashed.」

**这就是偏移量的计算方法**：从 `buf` 起始到返回地址的距离 = 24 字节。

### 5.4 构造攻击串

**栈粉碎原理**（讲义 p30）：把返回地址 A 覆盖成另一段代码 S 的地址，`ret` 时就跳到 S。

**目标**：让程序跳到 `smash`：

```c
void smash() {
    printf("I've been smashed!\n");
    exit(0);
}
```

`smash` 的地址是 `0x00000000004006c8`（讲义 p31）。

**攻击串**（讲义 p31）：

```
30 31 32 33 34 35 36 37 38 39 30 31 32 33 34 35 36 37 38 39 30 31 32 33
c8 06 40 00 00 00 00 00
```

逐段拆解：

| 字节 | 内容 | 作用 |
|---|---|---|
| `30`–`33` | `"0123"` | 填满 `buf[0..3]` |
| `34`–`37` | `"4567"` | 填充 1 |
| `38`–`39`,`30`–`33` | `"890123"` | 填充 2（到第 12 字节） |
| `34`–`39`,`30`–`33` | `"4567890123"` | 填充 3（到第 24 字节） |
| `c8 06 40 00 00 00 00 00` | `0x00000000004006c8`（小端） | **覆盖返回地址** |

总共 **32 字节**（24 填充 + 8 地址）。讲义 p31 标注「24 bytes」指前面的填充部分。

**执行**（讲义 p33）：

```
linux> cat smash-hex.txt | ./hexify | ./bufdemo-nsp
Type a string:012345678901234567890123?@
I've been smashed!
```

`hexify` 把十六进制文本转成原始字节（因为 `c8`、`06` 等是非打印字符，无法直接键入）。

### 5.5 代码注入攻击

**更强的攻击**（讲义 p34）：不跳到已有函数，而是把**机器码本身**放进缓冲区，然后让返回地址指向缓冲区。

```
返回地址 A  →  B（缓冲区地址）
缓冲区内容：  exploit code + padding + 覆盖的返回地址 B
```

`ret` 时 `%rip` 变成 B，CPU 开始在栈上取指执行——因为老 x86 **任何可读地址都可执行**。

讲义 p35 的图展示 `%rip` 沿栈向上移动执行注入的代码，`%rsp` 同步变化。

**为什么这比跳已有函数更强**：攻击者可以执行任意逻辑（开 shell、下载文件），不受程序里现有函数的限制。

### 5.6 三层防护

讲义 p37 列出三条防线。

**防线 1：写安全的代码**（讲义 p38）：

| 危险函数 | 安全替代 |
|---|---|
| `gets(buf)` | `fgets(buf, size, stdin)` |
| `strcpy(d, s)` | `strncpy(d, s, n)` |
| `strcat(d, s)` | `strncat(d, s, n)` |
| `scanf("%s", buf)` | `scanf("%15s", buf)`（带宽度）或 `fgets` |

```c
void echo() {
    char buf[4];
    fgets(buf, 4, stdin);   /* 最多读 3 字符 + '\0' */
    puts(buf);
}
```

**注意 `fgets(buf, 4, ...)` 只读 3 个字符**——`n` 包含结尾的 `'\0'`。这是最常见的 off-by-one 误解。

**防线 2：系统级保护**

**(a) 栈随机化（ASLR）**（讲义 p39）：程序启动时在栈上分配随机大小的空间，整个程序的栈地址整体平移。攻击者无法预测注入代码的地址 B。讲义 p39 说「5 次执行同一段 malloc 代码，栈位置每次都不同」。

**(b) 不可执行内存（NX）**（讲义 p40）：老 x86 任何可读地址都可执行；**x86-64 增加了「标记某段内存不可执行」的能力**。当前 Linux 与 Windows 都把栈标记为不可执行，跳进去立即崩溃。

这直接杀死了 5.5 节的代码注入攻击，但**没有**杀死 5.4 节的「跳到已有函数」攻击（因为 Text 段本来就可执行）。

**防线 3：栈金丝雀**（讲义 p42–p45）

思路：在缓冲区与返回地址之间放一个特殊值（canary），函数返回前检查它是否被改。

GCC 实现：`-fstack-protector`（现在是默认开启）。

**设置金丝雀**（讲义 p43）：

```asm
echo:
    sub    $0x18,%rsp
    mov    %fs:0x28,%rax      # 从段寄存器取 canary
    mov    %rax,0x8(%rsp)     # 放到栈上（缓冲区与返回地址之间）
    xor    %eax,%eax          # 擦掉寄存器里的副本
    mov    %rsp,%rdi
    callq  gets
    ...
```

**`%fs:0x28`** 是线程局部存储（TLS）里的一个固定位置，进程启动时由内核写入一个随机值。每个线程有自己的 canary。

**`xor %eax,%eax` 的作用**：把 `%rax` 里的 canary 副本清零，避免它残留在寄存器里被后续代码（或攻击者通过格式化字符串）读到。**金丝雀的价值在于「未知」**，泄漏了就失效。

**检查金丝雀**（讲义 p44）：

```asm
    mov    0x8(%rsp),%rax     # 从栈上取回
    xor    %fs:0x28,%rax      # 与真值比较（xor 为 0 则相同）
    je     .L6                # 相同 → 正常返回
    call   __stack_chk_fail   # 不同 → 报错并 abort
```

**用 `xor` 而不是 `cmp` 的原因**：`xor` 不会把 canary 值留在标志位之外的地方，且不产生中间结果；某些实现还会在比较后清零寄存器。更重要的是 `xor` 是常数时间操作，避免时序侧信道。

**效果**（讲义 p42）：

```
输入 7 个字符 → 正常
输入 9 个字符 → *** stack smashing detected ***
```

**canary 的边界**（讲义 p44 小注）：有些系统的 canary **最低字节是 `0x00`**。原因是 `gets` 之类的字符串函数会在末尾写 `'\0'`，若 canary 最低字节非零，即使只溢出一个字节也会被发现——而 `0x00` 结尾让「正常写入字符串」不会误触发。代价是：攻击者只要先写 `0x00` 就能保留这个字节，只需猜剩余 7 字节。

**canary 挡不住什么**：讲义 p46 明确说 ROP「does not overcome stack canaries」——意思是 ROP 也**绕不过** canary。若攻击能读到 canary 值（信息泄漏），canary 就失效了。

### 5.7 ROP：绕过 NX

讲义 p46–p50。

**困境**：

- 栈随机化 → 不知道缓冲区地址（挡住代码注入）。
- 栈不可执行 → 即使知道地址也不能执行（挡住代码注入）。

**ROP 的思路**：不注入新代码，**用程序里已有的代码**。把若干「以 `ret` 结尾的小片段」（gadget）串起来，每个 gadget 干一小件事，串起来完成整体目标。

**gadget 的定义**（讲义 p46）：以 `ret`（单字节 `0xc3`）结尾的指令序列。为什么强调 `ret`？因为 `ret` 会从栈上弹地址并跳转——**攻击者只要在栈上排好一串地址，就能让 gadget 一个接一个执行**。

**Gadget 例 1**（讲义 p47）：

```c
long ab_plus_c(long a, long b, long c) { return a*b + c; }
```

```asm
00000000004004d0 <ab_plus_c>:
  4004d0: 48 0f af fe    imul %rsi,%rdi
  4004d4: 48 8d 04 17    lea  (%rdi,%rdx,1),%rax
  4004d8: c3             retq
```

**从 `0x4004d4` 进入**（跳过 `imul`），得到的就是一个 gadget：`rax ← rdi + rdx` 然后 `ret`。

**关键洞察**：gadget 不必是函数开头，**可以从指令中间进入**。x86 是变长指令集，任意字节序列都可能解码成有效指令。

**Gadget 例 2**（讲义 p48）—— 更精彩的「字节重用」：

```c
void setval(unsigned *p) { *p = 3347663060u; }
```

```asm
<setval>:
  4004d9: c7 07 d4 48 89 c7    movl $0xc78948d4,(%rdi)
  4004df: c3                   retq
```

**从 `0x4004dc` 进入**——跳过 `c7 07 d4`，从 `48 89 c7` 开始解码：

```
48 89 c7  =  movq %rax, %rdi
c3        =  ret
```

于是 `0x4004dc` 处就是一个 `rdi ← rax; ret` 的 gadget。

**这是 ROP 的精髓**：`0xc78948d4` 这个立即数里，`48 89 c7` 恰好是 `mov %rax,%rdi` 的编码。攻击者不创造代码，只是**从已有字节流里挑出想要的指令序列**。

**组合攻击**（讲义 p49–p50）：

```
Gadget #1 @ 0x4004d4:  rax ← rdi + rdx
Gadget #2 @ 0x4004dc:  rdi ← rax
组合效果:              rdi ← rdi + rdx
```

**攻击串**：

```
30 31 ... 32 33                       ← 24 字节填充
d4 04 40 00 00 00 00 00               ← 覆盖返回地址 = Gadget #1
dc 04 40 00 00 00 00 00               ← Gadget #1 的 ret 会弹出这个 = Gadget #2
```

**执行流程**（讲义 p51）：

1. `echo` 执行 `ret` → 弹出 `0x4004d4`，跳到 Gadget #1。
2. Gadget #1 执行 `lea (%rdi,%rdx,1),%rax`，然后 `ret` → 弹出 `0x4004dc`，跳到 Gadget #2。
3. Gadget #2 执行 `mov %rax,%rdi`，然后 `ret` → 弹出栈上的下一个值……

讲义 p51 注明「**Multiple gadgets will corrupt stack upwards**」——每个 gadget 的 `ret` 都会把 `%rsp` 往上推 8 字节，所以整条 gadget 链的地址必须**从低到高依次排列**在栈上。

**ROP 为什么能绕过 NX**：gadget 都在 Text 段（可执行），攻击者从不往栈上写代码，只往栈上写**地址**。栈不可执行对「只放数据」的栈毫无影响。

**ROP 为什么绕不过 canary**：要覆盖返回地址，必须先覆盖 canary，而 canary 值未知。除非配合信息泄漏漏洞。

### 5.8 Union

讲义 p53–p56。

**分配规则**（讲义 p53）：所有字段从偏移 0 开始，**共享同一块内存**，大小取最大字段（并对齐到 K）。

```c
union U1 { char c; int i[2]; long v; };   // 大小 8（long）
struct S1 { char c; int i[2]; long v; };  // 大小 24
```

| 字段 | union 偏移 | struct 偏移 |
|---|---|---|
| `c` | 0 | 0 |
| `i[0]` | 0 | 4 |
| `i[1]` | 4 | 8 |
| `v` | 0 | 16 |

**「同一时刻只能用一个字段」**——写 `c` 会毁掉 `v` 的内容。这是 union 的语义约束，编译器不检查。

**用 union 看位模式**（讲义 p54）：

```c
typedef union { float f; unsigned u; } bit_float_t;

float bit2float(unsigned u) { bit_float_t arg; arg.u = u; return arg.f; }
unsigned float2bit(float f) { bit_float_t arg; arg.f = f; return arg.u; }
```

**这跟 `(float)u` / `(unsigned)f` 完全不同**：

- `(float)u` 是**数值转换**：`u = 3` → `3.0f`（位模式大改）。
- `bit2float(u)` 是**位模式重解释**：`u = 0x40490FDB` → `3.14159f`（位模式完全不变）。

这是 union 最重要的用途：在类型系统之外做「同一块字节的两种解读」。

**Sum type 模式**（讲义 p55）：

```c
typedef union { float f; unsigned u; } num_t;
typedef struct { bool is_float; num_t val; } value_t;
```

用一个 `bool` 标签 + 一个 union 表示「可能是 float 也可能是 unsigned」。这是 C 里实现变体类型（variant / tagged union）的标准手法。讲义 p55 小注：`is_float` 只占 1 字节，后面有 3 字节填充，`val` 从偏移 4 开始，总大小 8。

**字节序观察**（讲义 p56）：

```c
union {
    unsigned char  c[8];
    unsigned short s[4];
    unsigned int   i[2];
    unsigned long  l[1];
} dw;

for (int j = 0; j < 8; j++) dw.c[j] = 0xf0 + j;
```

**x86-64（小端）结果**（讲义 p56）：

| 视图 | 值 |
|---|---|
| `c[0..7]` | `f0 f1 f2 f3 f4 f5 f6 f7` |
| `s[0..3]` | `0xf1f0, 0xf3f2, 0xf5f4, 0xf7f6` |
| `i[0..1]` | `0xf3f2f1f0, 0xf7f6f5f4` |
| `l[0]` | `0xf7f6f5f4f3f2f1f0` |

**读法**：`c[0]=0xf0` 是最低地址的字节，在小端下它就是 `s[0]` 的**最低有效字节**，所以 `s[0] = 0xf1f0`（高字节 `f1` 在地址 1）。同理 `i[0] = 0xf3f2f1f0`。

**Sun（大端）对照**（讲义 p65）：

| 视图 | 值 |
|---|---|
| `s[0..3]` | `0xf0f1, 0xf2f3, 0xf4f5, 0xf6f7` |
| `i[0..1]` | `0xf0f1f2f3, 0xf4f5f6f7` |
| `l[0]` | `0xf0f1f2f3`（32 位 Sun） |

大端下 `c[0]=0xf0` 是**最高有效字节**。

**这个实验是理解字节序最直观的方式**——不需要背定义，看数字就知道。

讲义 p62 给出字节序分类：

| 类型 | 规则 | 代表 |
|---|---|---|
| Big Endian（大端） | 最高有效字节在最低地址 | SPARC、网络字节序 |
| Little Endian（小端） | 最低有效字节在最低地址 | Intel x86、ARM（Android/iOS） |
| Bi Endian（双端） | 可配置 | ARM |

**网络字节序是大端**，所以 socket 编程要用 `htons`/`htonl`/`ntohs`/`ntohl` 转换。这是「跨机器交换二进制数据」出问题的经典来源。

### 5.9 真实案例与失控栈

讲义 p67–p71 给出历史案例：

- **1988 年 Internet Worm**：`fingerd` 用 `gets()` 读参数，攻击者发送「exploit code + padding + new return address」。蠕虫在数小时内感染约 6000 台机器（当时互联网的 10%）。作者被起诉，CERT 因此成立（至今仍在 CMU）。
- **1999 年 IM 大战**：AOL 发现自家 AIM 客户端有缓冲区溢出，**反过来利用它**检测并阻断微软的 Messenger 客户端——exploit code 返回 AIM 客户端某处的 4 字节签名给服务器。微软改代码匹配签名，AOL 就改签名位置，至少 13 个回合。讲义 p70 展示一封「举报信」，后来查明**发自微软内部**。

讲义 p72 区分三类恶意软件：

| 类型 | 传播方式 |
|---|---|
| Trojan（木马） | 诱骗用户运行 |
| Worm（蠕虫） | 自动传播，无需人工 |
| Virus（病毒） | 感染已安装的程序 |

**失控栈**（讲义 p61）：

```c
int recurse(int x) {
    int a[1<<15];   /* 128 KiB per frame */
    printf("x = %d. a at %p\n", x, a);
    a[0] = (1<<14)-1;
    a[a[0]] = x-1;
    if (a[a[0]] == 0) return -1;
    return recurse(a[a[0]]) - 1;
}
```

每帧 128 KiB，栈上限 8 MB，所以约 64 层就耗尽。实测输出（讲义 p61）：

```
x = 67.  a at 0x7ffd18aba930
x = 66.  a at 0x7ffd18a9a920
x = 65.  a at 0x7ffd18a7a910
...
x = 2.  a at 0x7ffd1829a520
Segmentation fault (core dumped)
```

**注意每层地址相差 `0x20010` ≈ 128 KiB + 16 字节**（128 KiB 是数组，16 字节是返回地址与对齐）。x 从 67 递减到 2 就崩了，共约 66 层。

## 6. 代码示例

### 6.1 官方课程代码

**struct rec / get_ap / length**（讲义 p4–p6），出处 `90-原始PDF/15-213/lectures/06-machine-delta.pdf` 第 4–6 页，见 5.1 节。

**struct S3 数组访问**（讲义 p12），出处同上 PDF 第 12 页：

```asm
# %rdi = idx
leaq   (%rdi,%rdi,2), %rax
movzwl a+8(,%rax,4), %eax
```

**S4 / S5 空间对比**（讲义 p13），出处同上 PDF 第 13 页，见 5.1 节表格。

**内存分配示例**（讲义 p17–p18），出处同上 PDF 第 17–18 页：

```c
char big_array[1L<<24];   /* 16 MB */
char huge_array[1L<<31];  /*  2 GB */
int global = 0;
int useless() { return 0; }

int main() {
    void *phuge1, *psmall2, *phuge3, *psmall4;
    int local = 0;
    phuge1  = malloc(1L << 28);  /* 256 MB */
    psmall2 = malloc(1L << 8);   /*   256 B */
    phuge3  = malloc(1L << 32);  /*    4 GB */
    psmall4 = malloc(1L << 8);   /*   256 B */
}
```

**fun 越界示例**（讲义 p20），出处同上 PDF 第 20 页，见 5.3 节。

**gets 实现**（讲义 p23），出处同上 PDF 第 23 页，见 5.3 节。

**echo 反汇编**（讲义 p25），出处同上 PDF 第 25 页，见 5.3 节。

**栈粉碎攻击串**（讲义 p31–p33），出处同上 PDF 第 31–33 页，见 5.4 节。

**带 canary 的 echo**（讲义 p43–p44），出处同上 PDF 第 43–44 页，见 5.6 节。

**ab_plus_c / setval gadget**（讲义 p47–p48），出处同上 PDF 第 47–48 页，见 5.7 节。

**union 字节序实验**（讲义 p56、p63–p65），出处同上 PDF 第 56、63–65 页，见 5.8 节。

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：验证结构体数组的步长与对齐**

```c
/* stride.c —— 非官方示例，仅用于说明概念 */
#include <stdio.h>
#include <stddef.h>

struct S3 { short i; float v; short j; };

int main(void) {
    struct S3 a[3];
    printf("sizeof(S3) = %zu\n", sizeof(struct S3));
    printf("offsetof j  = %zu\n", offsetof(struct S3, j));
    printf("&a[0] = %p\n", (void *)&a[0]);
    printf("&a[1] = %p\n", (void *)&a[1]);
    printf("&a[2] = %p\n", (void *)&a[2]);
    printf("&a[1].j = %p\n", (void *)&a[1].j);
    return 0;
}
```

预期：`sizeof = 12`、`offsetof(j) = 8`，三个元素地址相差 12，且都是 4 的倍数（因为 `a` 本身按 K=4 对齐）。

**示例 B：用 canary 观察溢出何时被拦截**

```c
/* canary.c —— 非官方示例，仅用于说明概念 */
#include <stdio.h>
#include <string.h>

void vulnerable(const char *s) {
    char buf[8];
    strcpy(buf, s);        /* 故意不安全 */
    printf("buf = %s\n", buf);
}

int main(int argc, char **argv) {
    vulnerable(argv[1]);
    return 0;
}
```

编译与测试：

```
$ gcc -fstack-protector-all -o canary canary.c
$ ./canary 0123456            # 7 字符，安全
buf = 0123456
$ ./canary 012345678901234   # 溢出
*** stack smashing detected ***: terminated
Aborted (core dumped)
```

对比 `gcc -fno-stack-protector`：同样的输入不报 canary 错误，但可能在 `ret` 时段错误（返回地址被覆盖）。

**示例 C：用 union 判断本机字节序**

```c
/* endian.c —— 非官方示例，仅用于说明概念 */
#include <stdio.h>

int main(void) {
    union { unsigned u; unsigned char c[4]; } x;
    x.u = 0x01234567u;
    if (x.c[0] == 0x67)      printf("Little Endian\n");
    else if (x.c[0] == 0x01) printf("Big Endian\n");
    else                     printf("Unexpected\n");
    for (int i = 0; i < 4; i++) printf("c[%d] = 0x%02x\n", i, x.c[i]);
    return 0;
}
```

x86-64 上输出 `Little Endian`，`c[0]=0x67, c[1]=0x45, c[2]=0x23, c[3]=0x01`——最低有效字节 `0x67` 在最低地址。

**示例 D：计算溢出偏移量**

```c
/* offset.c —— 非官方示例，仅用于说明概念 */
#include <stdio.h>

void target(void) { printf("hijacked!\n"); }

void victim(void) {
    char buf[4];
    printf("buf  at %p\n", (void *)buf);
    printf("ret  near %p\n", (void *)__builtin_frame_address(0));
    /* 用 gdb 观察：buf 到返回地址的距离 */
}

int main(void) { victim(); return 0; }
```

用 GDB 求偏移：

```
(gdb) disassemble victim
(gdb) break *victim+<sub 之后>
(gdb) run
(gdb) p &buf
(gdb) info frame           # 会显示 saved rip 的位置
(gdb) p/x $rsp
```

更可靠的方法：`objdump -d` 看 `sub $N, %rsp`，则偏移 = `N`（若 `buf` 在 `%rsp` 处）或 `N + buf 的偏移`。讲义 p25 的 `sub $0x18` 对应偏移 24，正好印证。

**示例 E：手工推演 `fun(i)` 的浮点结果**

```c
/* funbits.c —— 非官方示例，仅用于说明概念 */
#include <stdio.h>
#include <string.h>

int main(void) {
    double d = 3.14;
    unsigned long bits;
    memcpy(&bits, &d, 8);
    printf("3.14 bits = 0x%016lx\n", bits);

    /* 把低 32 位换成 0x40000000 */
    bits = (bits & 0xFFFFFFFF00000000UL) | 0x40000000UL;
    memcpy(&d, &bits, 8);
    printf("after = %.10f\n", d);   /* 约 3.1399998665 */
    return 0;
}
```

这解释了讲义 p20 中 `fun(2)` 为什么返回 `3.1399998665`：`s.a[2] = 1073741824`（`0x40000000`）正好覆盖 `d` 的低 4 字节。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| `struct` | `union` | 前者字段各有独立偏移、总大小是各字段之和加填充；后者全部从偏移 0 开始、大小取最大字段 |
| `(float)u` | `bit2float(u)` | 前者数值转换（位模式改变）；后者位模式重解释（数值改变） |
| 代码注入 | ROP | 前者往栈写机器码并跳过去（被 NX 挡住）；后者只用已有 gadget（绕过 NX） |
| ASLR | NX | 前者让地址不可预测；后者让栈不可执行。两者独立，需同时存在 |
| canary 挡住 | canary 挡不住 | 挡住「连续覆盖返回地址」；挡不住「信息泄漏后精确伪造」 |
| `fgets(buf, 4, stdin)` | 读 4 个字符 | 前者最多读 **3** 个字符 + `'\0'` |
| `movzwl` | `movw` | 前者零扩展到 32 位；后者只写低 16 位，高位不变 |
| 内部填充 | 外部填充 | 前者在字段之间；后者在结构体末尾（使总长为 K 的倍数） |
| `sizeof(struct S3)` = 12 | K = 4 | 前者是实际占用（含填充）；后者是对齐要求（最大字段对齐值） |
| 小端 `0x01234567` | 大端 `0x01234567` | 前者内存为 `67 45 23 01`；后者为 `01 23 45 67` |
| 栈上 24 字节溢出 | 25 字节溢出 | 前者填满 buf + unused，不崩；后者 `'\0'` 覆盖返回地址最低字节，崩溃 |
| `%fs:0x28` | 普通全局变量 | 前者是线程局部存储的固定偏移，每线程独立随机值 |
| 大块 `malloc` | 小块 `malloc` | 前者走 `mmap`（地址在 `0x7f...`）；后者走 heap（地址在 .bss 之后） |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-213/lectures/06-machine-delta.pdf`
- **总页数**：71 页
- **重点页码**：
  - p2 标题（2026 年 9 月 10 日，第 6 讲）
  - p3 本讲大纲（CSAPP 3.9 结构体 / 3.10 缓冲区溢出 / 3.9.2 union）
  - p4–p6 struct rec、get_ap、length
  - p7–p10 对齐规则、S1/S2 布局、内部与外部填充
  - p11–p12 结构体数组的步长推理、S3 与 `movzwl a+8(,%rax,4)`
  - p13 S4（12 字节）vs S5（8 字节）
  - p16–p18 x86-64 内存布局与实测地址
  - p20 fun(i) 越界结果表
  - p22–p23 缓冲区溢出定义、gets 实现、同类危险函数
  - p24–p25 echo 源码与反汇编（`sub $0x18`）
  - p26–p28 栈布局与 23/24 字符实测
  - p30–p33 栈粉碎原理与攻击串构造、hexify 执行
  - p34–p35 代码注入攻击与执行过程
  - p37–p38 三层防护概览、安全替代函数
  - p39–p40 栈随机化、不可执行内存
  - p42–p45 canary 设置与检查（`%fs:0x28`）
  - p46–p51 ROP 原理、两个 gadget、组合攻击串与执行流程
  - p53–p56 union 分配、位模式重解释、sum type、字节序实验
  - p60 编译器为何不重排字段
  - p61 失控栈（128 KiB/帧）
  - p62–p65 字节序分类与 x86-64 / Sun 对照
  - p67–p71 Internet Worm、IM 大战
  - p72 木马/蠕虫/病毒的区别
- **原始链接**：https://www.cs.cmu.edu/~213/lectures/06-machine-delta.pdf
- **教材对应**：CS:APP 3e §3.9（异质数据结构，含 §3.9.2 union）、§3.10（缓冲区溢出）

> 待核实：讲义 p41 引用 Canvas 小测链接（`canvas.cmu.edu/courses/55964/quizzes/169254`），非 CMU 用户无法访问。讲义 p20 与 p21 的 `fun(i)` 结果表略有差异（p20 有 fun(6)="Stack smashing detected"、p21 有 fun(4)=Segmentation fault），可能对应不同编译选项；本笔记以 p20 为主并注明差异。讲义 p18 的地址为一次具体运行结果，讲义本身标注「Exact values can vary」。

## 9. 对应视频

**未找到官方公开录像。**

可参考的公开资源：

- 教材站点：https://csapp.cs.cmu.edu/ —— 第 3 章配套的 `bufdemo`、`bufdemo-nsp`、`bufdemo-sp` 示例。
- 课程日程：https://www.cs.cmu.edu/~213/schedule.html
- Attack Lab 说明（https://csapp.cs.cmu.edu/3e/attacklab.pdf）—— 本讲的栈溢出与 ROP 就是 attack lab 的题目内容（Phase 1–3 代码注入，Phase 4–5 ROP）。
- xkcd 1354（https://xkcd.com/1354/）—— 讲义 p57 引用的「Heartbleed」漫画，讲的就是越界读。
- 本课 GDB 速查：`90-原始PDF/15-213/recitations/gdbnotes-x86-64.pdf`。

## 10. 本节复习

- 结构体数组步长 = `sizeof(struct)`（含填充）；因为长度是 K 的倍数，元素间无需额外填充。
- `movzwl` 读 2 字节并零扩展到 32 位；`short` 返回值走 `%eax` 会自动清零高位。
- 字段按大小降序排列可省空间（S4 12 字节 vs S5 8 字节）；编译器不会自动重排。
- 内存布局（低到高）：Text（只读、从 `0x400000`）→ Data（全局/静态）→ Heap（malloc 小块）→ Shared Libraries → Stack（8 MB，`%rsp`）。
- 大块 `malloc` 走 `mmap`，地址在 `0x7f...` 区间。
- 缓冲区溢出 = 写入超出数组容量；最常见来源是 `gets`/`strcpy`/`%s`。
- `gets` 接口无长度参数，无法安全使用；替代 `fgets`/`strncpy`/`%ns`。
- 溢出偏移 = 从 `buf` 起始到返回地址的字节数（讲义例子为 24）。
- 覆盖返回地址最低字节即可让 `ret` 跳到附近地址（`0x4006c3` → `0x400600`）。
- 代码注入 = 缓冲区放机器码 + 返回地址指向缓冲区；被 NX 挡住。
- ASLR = 随机化栈/堆/库基址；NX = 栈不可执行；canary = 哨兵值。
- canary 从 `%fs:0x28` 取，放在缓冲区与返回地址之间；返回前 `xor` 比较。
- ROP = 串联以 `ret`（`0xc3`）结尾的 gadget；gadget 可从指令中间进入。
- union 所有字段偏移 0，大小取最大字段；用于位模式重解释与 sum type。
- x86 小端：最低有效字节在最低地址；网络字节序是大端。
- 递归失控：每帧 128 KiB × 8 MB 栈 ≈ 64 层就段错误。

## 11. 自我检查

**题 1**：`struct P { char a; short b; int c; char d; }` 在 x86-64 上的各字段偏移、`sizeof`、K 分别是多少？若重排为 `int c; short b; char a; char d;` 呢？

<details><summary>参考答案</summary>

**原顺序**：

| 字段 | 偏移 | 大小 | 说明 |
|---|---|---|---|
| `a` | 0 | 1 | |
| （填充） | 1 | 1 | 使 `b` 落在 2 的倍数 |
| `b` | 2 | 2 | |
| `c` | 4 | 4 | 已是 4 的倍数 |
| `d` | 8 | 1 | |
| （填充） | 9–11 | 3 | 使总长为 K=4 的倍数 |

`sizeof = 12`，K = 4。

**重排后**：

| 字段 | 偏移 | 大小 |
|---|---|---|
| `c` | 0 | 4 |
| `b` | 4 | 2 |
| `a` | 6 | 1 |
| `d` | 7 | 1 |

`sizeof = 8`，K = 4。**省了 4 字节（33%）**，且无任何填充。

</details>

**题 2**：`char buf[4]` 在 `%rsp` 处，返回地址在 `%rsp+24`。攻击串需要多长才能覆盖返回地址？若想跳到 `0x00000000004006c8`，最后 8 字节的十六进制是什么？

<details><summary>参考答案</summary>

**长度**：24 字节填充 + 8 字节地址 = **32 字节**。

**最后 8 字节**（小端，低字节在前）：

```
c8 06 40 00 00 00 00 00
```

验证：把 `c8 06 40 00 00 00 00 00` 按小端读回 = `0x00000000004006c8`。

**注意**：`gets` 会在输入末尾自动追加 `'\0'`，所以实际写入 33 字节。第 33 字节落在返回地址之后的栈位置上，通常无害。

</details>

**题 3**：为什么 `movl $0xc78948d4,(%rdi)` 这条指令能提供 `movq %rax,%rdi` 的 gadget？请写出字节拆解。

<details><summary>参考答案</summary>

指令的机器码是：

```
c7 07 d4 48 89 c7
```

- `c7` = `movl` 的操作码
- `07` = ModR/M（`(%rdi)` 目标）
- `d4 48 89 c7` = 立即数 `0xc78948d4`（小端）

**从第 4 个字节 `48` 开始解码**（地址 `0x4004dc`）：

```
48 89 c7   →  movq %rax, %rdi     （REX.W + 89 /r，reg=rax, r/m=rdi）
c3         →  ret
```

于是 `0x4004dc` 处就是一个完整的 gadget：`rdi ← rax; ret`。

**要点**：x86 是变长指令集，没有对齐要求，任意字节偏移都可能成为合法指令起点。ROP 正是利用这一点，从已有代码的字节流里「开采」gadget。

</details>

**题 4**：`union { char c; int i[2]; long v; }` 和 `struct { char c; int i[2]; long v; }` 的大小各是多少？若先写 `u.c = 'A'` 再读 `u.v`，会得到什么？

<details><summary>参考答案</summary>

- **union**：大小 **8**（最大字段 `long v`），K = 8，8 是 8 的倍数，无需外部填充。所有字段偏移都是 0。
- **struct**：大小 **24**（`c`@0、填充 3、`i[0]`@4、`i[1]`@8、填充 4、`v`@16），K = 8，24 是 8 的倍数。

**写 `u.c = 'A'` 再读 `u.v`**：`'A'` = `0x41` 被写到最低地址字节，`u.v` 的其余 7 字节是**未初始化的垃圾**。所以读到的 `u.v` 的最低价字节是 `0x41`，高位不确定——**这是未定义行为**，结果取决于之前那块内存里有什么。

正确做法是先用 `memset` 清零，或改用 struct。

</details>

**题 5**：栈随机化（ASLR）与不可执行栈（NX）分别挡住哪种攻击？ROP 为什么能绕过 NX 却绕不过 canary？

<details><summary>参考答案</summary>

| 防护 | 挡住 | 原理 |
|---|---|---|
| ASLR | 代码注入（不知道缓冲区地址 B） | 每次运行栈基址随机，攻击串里的硬编码地址失效 |
| NX | 代码注入（即使知道 B 也不能执行） | 栈页标记为不可执行，跳进去立即 fault |
| canary | 覆盖返回地址（任何形式） | 缓冲区与返回地址之间的哨兵值被改，返回前检测到并 abort |

**ROP 绕过 NX**：gadget 全部位于 Text 段（可执行），攻击者**从不往栈上写代码**，只往栈上写**地址**。NX 保护的是「栈上的字节不能当指令执行」，而 ROP 的栈上只有数据（地址），指令来自 Text 段——完全不冲突。

**ROP 绕不过 canary**：要覆盖返回地址（或 gadget 链的第一个地址），必须先把 canary 那 8 字节也覆盖掉。canary 值攻击者不知道，无法「原样写回」。除非配合一个信息泄漏漏洞（如格式化字符串、越界读）先读出 canary，否则 canary 检查必然失败，程序在 `__stack_chk_fail` 处 abort。

**注意**：ASLR 单独也挡不住 ROP（因为 Text 段地址在非 PIE 程序里是固定的），所以需要 ASLR + canary 组合。这也是为什么现代系统默认开启 PIE + canary + NX 三者。

</details>

## 12. 进一步学习

- 上一讲：[[15-213-05-Machine-Programming-III-Procedures|CMU 15-213 - L05 Machine Programming III Procedures]]
- 下一讲：[[15-213-07-Linking|CMU 15-213 - L07 Linking]] —— 符号解析、重定位、静态库与动态库。
- 课程导航：[[20-CMU-15-213/00-课程总览|CMU 15-213 - 课程总览]]、[[20-CMU-15-213/01-课程目录|CMU 15-213 - 课程目录]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- CS:APP 3e §3.9.2（union）、§3.10（缓冲区溢出）。
- Attack Lab（https://csapp.cs.cmu.edu/3e/attacklab.pdf）—— 本讲的直接练习。
- xkcd 1354（https://xkcd.com/1354/）—— Heartbleed 越界读漫画。
- 课程日程：https://www.cs.cmu.edu/~213/schedule.html
