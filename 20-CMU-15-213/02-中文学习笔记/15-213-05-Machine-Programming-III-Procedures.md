---
course: CMU 15-213
course_name: Introduction to Computer Systems
semester: Fall 2026
lecture_id: L05
topic: Machine Programming III - Procedures
language: zh-CN
source_language: en
status: draft
tags:
  - CMU-15-213
  - 汇编语言
  - 栈帧
  - 调用约定
  - 数组
  - 结构体
  - 内存对齐
---

# L05 Machine Programming III: Procedures（机器级编程 III：过程）

> 开课日期：2026 年 9 月 8 日。本讲把「函数调用」这件 C 程序员习以为常的事拆到寄存器与栈的层面：参数放哪、返回值放哪、谁的寄存器谁负责保存、局部变量什么时候被回收。后半段转到数组与结构体的地址计算——**C 里看起来一样的 `A[i][j]`，在嵌套数组和多级数组里是完全不同的两次访存**。

## 1. 本节学习目标

1. 列出 x86-64 过程机制的三个方面（传递控制、传递数据、管理局部数据），并说明每个由哪些指令实现。
2. 背出六个参数寄存器顺序 `%rdi %rsi %rdx %rcx %r8 %r9` 与返回值寄存器 `%rax`，说明第 7 个参数之后放哪里。
3. 说明 caller-saved 与 callee-saved 的分工，并解释「为什么必须有这个约定」。
4. 画出 x86-64/Linux 栈帧的完整布局（从高地址到低地址）。
5. 逐条跟踪 `call_incr` 调用 `incr` 的栈变化，说明 `subq $16, %rsp` 与 `leaq 8(%rsp), %rdi` 的作用。
6. 说明递归为什么不需要特殊机制（栈帧 + 保存约定就够了），并能读懂 `pcount_r` 的汇编。
7. 计算一维、嵌套、多级数组的元素地址，写出对应的 `leaq`/`movl` 序列。
8. 计算结构体各字段偏移、总大小、对齐要求 K，并说明内部填充与外部填充的成因。

## 2. 前置知识

- **L03**：寄存器、寻址模式 `D(Rb,Ri,S)`、`mov`/`lea`。
- **L04**：`call`/`ret`、`push`/`pop`、栈向低地址生长。
- **C 语言**：数组与指针的关系、`typedef`、结构体、递归、`size_t`。

## 3. 核心概念

- **Procedure Call（过程调用）**：调用者（caller）把控制权与数据交给被调用者（callee），callee 完成后返回。
- **Argument Register（参数寄存器）**：`%rdi`、`%rsi`、`%rdx`、`%rcx`、`%r8`、`%r9`。
- **Return Value（返回值）**：放在 `%rax`。
- **Caller-Saved（调用者保存 / Call-Clobbered）**：callee 可随意改写的寄存器，caller 若要跨调用保留必须自己先存。
- **Callee-Saved（被调用者保存 / Call-Preserved）**：callee 若要使用必须先保存、返回前恢复：`%rbx`、`%rbp`、`%r12`–`%r15`。
- **Stack Frame（栈帧）**：一次过程调用占用的栈区域。
- **Frame Pointer（帧指针）**：`%rbp`，可选，指向当前帧底部。
- **Reentrant（可重入）**：同一段代码可以有多份同时活跃的实例。
- **Row-Major Ordering（行主序）**：二维数组按行连续存放。
- **Alignment（对齐）**：大小为 B 字节的基本类型，其地址必须是 B 的倍数。
- **Internal Padding（内部填充）**：结构体字段之间为满足对齐插入的空隙。
- **External Padding（外部填充）**：结构体末尾为使其长度为 K 的倍数插入的空隙。

## 4. 通俗理解

**寄存器像公共办公桌，栈像每个人的抽屉。** 六个参数寄存器是「传阅文件」——递给下一个人后，桌上就空了，你不能指望回来时它还在（caller-saved）。`%rbx` 这类是「你的私人抽屉」——你借用之前得先把别人的东西收好，用完放回去（callee-saved）。

**栈帧像餐厅的托盘。** 你点单时服务员端来一个托盘（`subq $16, %rsp` 分配），把菜摆上去（`movq $15213, 8(%rsp)`），吃完把整个托盘端走（`addq $16, %rsp`）。**托盘里的菜不需要一个个清理**——这就是栈回收局部变量为什么是零成本的。

**嵌套数组是「一整块连排座位」，多级数组是「索引牌」。** `pgh[2][1]` 是「从第 0 排数起走 2 排半再找 1 号座」——一次计算就到位。`univ[2][1]` 是「先看 2 号牌子写着哪块区域，再去那块区域找 1 号」——两次访存。C 语法几乎一样，代价差一倍。

## 5. 原理与推导

### 5.1 过程的三个方面

讲义 p5/p12/p15 反复出现同一张图：任何过程调用都要解决三件事。

| 机制 | 具体内容 | 实现手段 |
|---|---|---|
| **传递控制（passing control）** | 跳到过程入口；返回时回到调用点之后 | `call` / `ret` + 栈上的返回地址 |
| **传递数据（passing data）** | 参数传入；返回值传出 | 6 个参数寄存器 + `%rax`；超出部分走栈 |
| **管理局部数据（managing local data）** | 执行期间分配；返回时释放 | `subq`/`addq %rsp`，或 `push`/`pop` |

关键一句（讲义 p5）：「**x86-64 的实现只使用它需要的机制**」——不是每个函数都有栈帧。`incr` 这种只用寄存器的函数，汇编里连 `%rsp` 都不碰。

### 5.2 传递控制：call/ret 复习

讲义 p7–p11 用四张幻灯片跟踪 `multstore` 调 `mult2`：

| 阶段 | `%rip` | `%rsp` | 栈顶内容 |
|---|---|---|---|
| `call` 之前（p8） | `0x400544` | `0x120` | — |
| `call` 执行后（p9） | `0x400550` | `0x118` | `0x400549` |
| 进入 `mult2`（p10） | `0x400557` | `0x118` | `0x400549` |
| `ret` 执行后（p11） | `0x400549` | `0x120` | （`0x400549` 仍在内存） |

**注意 p9 的细节**：`call` 之后 `%rip` 已经是 `0x400550`（`mult2` 的第一条指令），而压栈的是 `0x400549`（`call` 的**下一条**指令）。讲义 p7 明确指出返回地址的定义：「**紧跟在 call 之后那条指令的地址**」。

讲义 p7 还有一句小注：`call`/`ret` 有时写成 `callq`/`retq`，`q` 只是提醒你在看 64 位代码，语义无差别。

### 5.3 栈式语言与栈帧

讲义 p16 解释为什么需要栈：支持递归的语言（C、Pascal、Java）要求代码**可重入**——同一个过程可以有多份同时活跃的实例，每份都要有自己的状态（参数、局部变量、返回地址）。

栈纪律成立的前提是两条时间性质：

1. 一个过程的状态只需要有限时间（从被调用到返回）。
2. **callee 一定在 caller 之前返回**（LIFO）。

讲义 p17 给出调用链示例：`yoo` 调 `who`，`who` 调两次 `amI`，`amI` 递归调自己。讲义 p19–p29 用 11 张幻灯片演示栈帧随调用/返回的增减，直观展示「栈是一摞帧」。

### 5.4 x86-64/Linux 栈帧布局

讲义 p30 的完整布局（从高地址到低地址）：

```
        ┌──────────────────────┐  高地址
        │  Arguments 7+        │  ← caller 为被调函数准备的栈参数
        ├──────────────────────┤
Caller  │  Return Addr         │  ← call 指令压入
Frame   ├──────────────────────┤
        │  (Optional) Old %rbp │  ← push %rbp（若用帧指针）
        ├──────────────────────┤
        │  Saved Registers     │  ← 被调用者保存寄存器的旧值
        ├──────────────────────┤
Current │  Local Variables     │  ← 放不进寄存器的局部变量
Frame   ├──────────────────────┤
        │  Argument Build      │  ← 为「即将调用的函数」准备的第 7+ 个参数
        └──────────────────────┘  低地址
                                    %rsp
```

讲义 p30 底部强调：「**Important Note: Stack space only allocated if needed by procedure!**」——没有局部变量、不需要保存寄存器的函数，`%rsp` 一动不动。

讲义 p18 说 `%rbp` 是帧指针、`%rsp` 是栈指针。**现代编译器在 `-O1` 及以上通常不用 `%rbp`**（把它解放成通用寄存器），所以你在优化后的汇编里经常看不到它。但 `-O0` 的代码几乎总是 `push %rbp; mov %rsp, %rbp`。

### 5.5 传递数据：incr 与 call_incr

**`incr`（讲义 p31）—— 纯寄存器，无栈帧**：

```c
long incr(long *p, long val) {
    long x = *p;
    long y = x + val;
    *p = y;
    return x;
}
```

```asm
incr:
    movq (%rdi), %rax    # x = *p        （%rdi = p）
    addq %rax, %rsi      # y = x + val   （%rsi = val，原地累加）
    movq %rsi, (%rdi)    # *p = y
    ret                  # 返回 x（在 %rax 里）
```

寄存器分配（讲义 p31 表格）：

| 寄存器 | 用途 |
|---|---|
| `%rdi` | 参数 `p` |
| `%rsi` | 参数 `val`，后来复用为 `y` |
| `%rax` | `x`，同时是返回值 |

**注意 `%rsi` 被复用**：`val` 读完后就没用了，直接当 `y` 用。这是寄存器分配的常规操作，也是读汇编时的常见困惑点。

**`call_incr`（讲义 p32）—— 需要一个局部变量的地址，必须上栈**：

```c
long call_incr() {
    long v1 = 15213;
    long v2 = incr(&v1, 3000);
    return v1 + v2;
}
```

```asm
call_incr:
    subq $16, %rsp          # 分配 16 字节栈帧
    movq $15213, 8(%rsp)    # v1 存在 %rsp+8
    movl $3000, %esi        # 参数 2 = 3000
    leaq 8(%rsp), %rdi      # 参数 1 = &v1
    call incr
    addq 8(%rsp), %rax      # %rax = v2 + v1（incr 改了 v1，现在是 18213）
    addq $16, %rsp          # 回收栈帧
    ret
```

**四个值得注意的细节**：

1. **为什么 `subq $16` 而不是 `$8`？** x86-64 ABI 要求调用点的 `%rsp` 是 16 字节对齐（为了 SSE 指令能对齐访存）。`call` 会压入 8 字节返回地址，所以进入函数时 `%rsp ≡ 8 (mod 16)`，再减 16 仍保持对齐。
2. **为什么 `v1` 放在 `8(%rsp)` 而不是 `(%rsp)`？** 讲义 p33–p35 的图示显示 `%rsp` 处标着「Unused」。这样安排让 `&v1` 落在 8 的倍数上（`%rsp` 本身 16 对齐，+8 是 8 对齐），满足 `long` 的对齐要求。
3. **`movl $3000, %esi` 而不是 `movq`**（讲义 p35 的 Aside 1）：`movl` 写 32 位寄存器会**自动清零高 32 位**，效果等同 `movq`，但指令短 1 字节。
4. **`leaq 8(%rsp), %rdi`**（讲义 p35 的 Aside 2）：`lea` 在这里是「正经用途」——它本来就算地址，而这里要的正是地址 `&v1`。前面 L04 说 `lea` 常被拿来当算术用，此处是回归本职。

**栈变化全过程**（讲义 p33–p40）：

| 幻灯片 | 事件 | `8(%rsp)` | `%rax` |
|---|---|---|---|
| p33 | 进入 `call_incr`，`call` 已压返回地址 | — | — |
| p34 | `subq $16` + `movq $15213` | 15213 | — |
| p35 | 设置 `%rdi = &v1`、`%rsi = 3000` | 15213 | — |
| p36 | 进入 `incr`，执行 `*p = *p + val` | 18213 | 15213 |
| p37 | `incr` 返回 | 18213 | 15213（v2） |
| p38 | `addq 8(%rsp), %rax` | 18213 | 33426 |
| p39 | `addq $16, %rsp` | （已出栈） | 33426 |
| p40 | `ret` | — | 33426 |

**注意 p36→p37 的关键**：`incr` 改的是 `v1` 的**内存**（通过指针），所以 `call_incr` 里 `addq 8(%rsp), %rax` 读到的是**修改后的 18213**，而不是 15213。结果 `15213 + 18213 = 33426`。这是「指针让 callee 能改 caller 的局部变量」的最小例子。

### 5.6 寄存器保存约定

讲义 p41 提出矛盾：**寄存器传参之所以高效，正是因为 caller 和 callee 共用同一批寄存器**——但如果 callee 要拿寄存器当临时存储，就会覆盖 caller 还没用完的值。

```asm
yoo:
    movq $15213, %rdx
    call who
    addq %rdx, %rax      # 期望 %rdx 还是 15213
    ret
who:
    subq $18213, %rdx    # 但 who 把 %rdx 改了！
    ret
```

解法（讲义 p42）：**寄存器保存约定**。

| 类别 | 别名 | 规则 | 由谁负责 |
|---|---|---|---|
| Caller-Saved | Call-Clobbered | callee 可以随便改 | caller 在调用**前**把要保留的值存进自己的栈帧 |
| Callee-Saved | Call-Preserved | callee 若要用，必须先存后恢复 | callee 在**使用前**存、返回前恢复 |

具体划分（讲义 p43–p44）：

| 寄存器 | 用途 | 类别 |
|---|---|---|
| `%rax` | 返回值；也常作临时 | Caller-saved |
| `%rdi`, `%rsi`, `%rdx`, `%rcx`, `%r8`, `%r9` | 参数 1–6 | Caller-saved |
| `%r10`, `%r11` | 临时 | Caller-saved |
| `%rbx`, `%r12`, `%r13`, `%r14` | 临时 | **Callee-saved** |
| `%rbp` | 帧指针（可选） | **Callee-saved** |
| `%rsp` | 栈指针 | 特殊：返回时必须恢复原值 |

**记忆法**：`%r12`–`%r15` 与 `%rbx`、`%rbp` 是「贵重物品」，用前存后用还；其余全是「一次性餐具」，用完就扔。

**为什么 `%rsp` 单列**：它形式上属于 callee-saved（返回时值必须复原），但机制不同——它不是靠 `push`/`pop` 保存，而是靠 `addq` 与 `subq` 对称抵消。

**这就是 L04 里 `multstore` 开头 `push %rbx` 的原因**：它要把 `dest` 跨过 `call mult2` 保存下来，而 `%rbx` 是 callee-saved，所以它自己必须遵守规则先存后恢复。

### 5.7 递归

讲义 p77–p83 用 `pcount_r` 演示递归不需要任何特殊机制：

```c
long pcount_r(unsigned long x) {
    if (x == 0) return 0;
    else return (x & 1) + pcount_r(x >> 1);
}
```

```asm
pcount_r:
    movl $0, %eax          # 默认返回值 0（终止情形直接返回）
    testq %rdi, %rdi
    je   .L6               # if (x == 0) return 0
    pushq %rbx             # 保存 %rbx
    movq %rdi, %rbx        # %rbx = x
    andl $1, %ebx          # %rbx = x & 1
    shrq %rdi              # %rdi = x >> 1（作为递归实参）
    call pcount_r          # 递归调用
    addq %rbx, %rax        # return (x&1) + pcount_r(x>>1)
    popq %rbx              # 恢复 %rbx
.L6:
    rep; ret
```

**三个精妙之处**：

1. **`movl $0, %eax` 放在最前面**：终止情形不需要额外代码，直接 `je .L6` 后 `ret` 就返回 0。这叫「提前设置默认返回值」。
2. **`x & 1` 必须存进 callee-saved 的 `%rbx`**：因为它在 `call` 之后还要用（`addq %rbx, %rax`）。若放在 `%rdx` 之类 caller-saved 寄存器，递归调用会把它毁掉。这是 callee-saved 规则最直观的应用场景。
3. **`shrq %rdi` 直接改 `%rdi`**：`%rdi` 是 caller-saved，且当前值用完即弃（`x` 已经在 `%rbx` 里存了一份完整值？其实没有——但 `x & 1` 已经算出来了，剩下只需要 `x >> 1`），所以可以就地修改。

讲义 p84 总结递归「无需特殊考虑」的三条理由：

- **栈帧保证每次调用有私有存储**（保存的寄存器、局部变量、返回地址）。
- **寄存器保存约定防止一次调用破坏另一次的数据**——除非 C 代码显式越界（下一讲 buffer overflow）。
- **栈纪律与 call/return 模式一致**：P 调 Q，Q 必先于 P 返回，天然 LIFO。

讲义 p84 补充：**互递归（mutual recursion）同样适用**——P 调 Q、Q 调 P，栈照样一摞帧。

### 5.8 尾递归（附加内容）

讲义 p85 展示尾递归优化：

```c
long popcount_t(unsigned long x, long s) {
    if (x == 0) return s;
    long b = x & 1UL;
    return popcount_t(x >> 1, s + b);   // 调用之后没有其他计算
}
```

```asm
popcount_t:
    movq %rsi, %rax        # 累加器 s 放 %rax
    testq %rdi, %rdi
    je   .L18
.L15:
    movq %rdi, %rdx
    andl $1, %edx
    addq %rdx, %rax        # s += x & 1
    shrq %rdi              # x >>= 1
    jne  .L15              # 循环！不是 call
.L18:
    ret
```

**编译器把递归变成了循环**——没有 `call`，没有 `push`，栈深度 O(1)。判据是「**函数调用之后没有任何计算**」：既然返回值就是调用的返回值，那就不需要保留当前帧，直接跳回函数开头即可。讲义 p85 说「许多编译器/语言能优化这类函数」，但注意 **C 标准不保证**，深度依赖时不要指望它。

### 5.9 数组：一维

讲义 p48 先立规矩：**内存位置没有数据类型**，类型完全隐含在「指令怎么用这块内存」里。地址指向字节，大对象的地址是其第一个字节的地址，相邻元素的地址差等于元素大小。

讲义 p49 的分配示例：

| 声明 | 元素大小 | 总大小 | 地址序列 |
|---|---|---|---|
| `char string[12]` | 1 | 12 | x, x+1, …, x+11 |
| `int val[5]` | 4 | 20 | x, x+4, x+8, x+12, x+16 |
| `double a[3]` | 8 | 24 | x, x+8, x+16 |
| `char *p[3]` | 8 | 24 | x, x+8, x+16 |

**数组名等价于指向第 0 个元素的指针**（讲义 p50）：

| 表达式 | 类型 | 值 |
|---|---|---|
| `val[4]` | `int` | 1 |
| `val[5]` | `int` | `??`（越界访问，无检查） |
| `*(val+3)` | `int` | 1（等同 `val[3]`） |
| `val` | `int *` | x |
| `val+1` | `int *` | x+4 |
| `&val[2]` | `int *` | x+8（等同 `val+2`） |
| `val+i` | `int *` | x+4i（等同 `&val[i]`） |

**`val[5]` 那行标着 `??`**——C 不做边界检查，读越界是未定义行为，但机器照样会去读那块内存。这就是后面 attack lab 的入口。

**访问代码**（讲义 p52）：

```c
int get_digit(zip_dig z, int digit) { return z[digit]; }
```

```asm
# %rdi = z, %rsi = digit
movl (%rdi,%rsi,4), %eax    # z[digit]
```

一条指令搞定：`%rdi + 4 * %rsi`。这里 `4` 就是 scale，正好是 `sizeof(int)`。

**循环代码**（讲义 p53）：

```c
void zincr(zip_dig z) {
    size_t i;
    for (i = 0; i < ZLEN; i++) z[i]++;
}
```

```asm
# %rdi = z
    movl $0, %eax              # i = 0
    jmp  .L3                   # goto middle
.L4:                           # loop:
    addl $1, (%rdi,%rax,4)     # z[i]++
    addq $1, %rax              # i++
.L3:                           # middle:
    cmpq $4, %rax              # i : 4
    jbe  .L4                   # if <=, goto loop
    rep; ret
```

**`jbe` 而不是 `jl`**：`i` 是 `size_t`（无符号），所以用无符号比较。`i <= 4` 是编译器把 `i < 5` 改写成的形式（少一次比较常量的开销）。这个改写之所以安全，正是因为 `i` 无符号、不会溢出成负数。

### 5.10 嵌套数组（二维）

讲义 p55：`T A[R][C]`，大小 `R * C * sizeof(T)`，**行主序**——先排完第 0 行再排第 1 行。

讲义 p56 的例子：

```c
#define PCOUNT 4
typedef int zip_dig[5];
zip_dig pgh[PCOUNT] = {
    {1, 5, 2, 0, 6},
    {1, 5, 2, 1, 3},
    {1, 5, 2, 1, 7},
    {1, 5, 2, 2, 1}
};
```

内存布局是**一整块连续的 80 字节**：

```
1 5 2 0 6 | 1 5 2 1 3 | 1 5 2 1 7 | 1 5 2 2 1
   pgh+0       pgh+20      pgh+40      pgh+60
```

讲义 p56 标注的地址是 76, 96, 116, 136, 156（每行 20 字节）。

**行地址**（讲义 p57）：`A[i]` 的起始地址 = `A + i * (C * sizeof(T))` = `pgh + 20*i`。

**行指针代码**（讲义 p58）：

```c
int *get_pgh_zip(int index) { return pgh[index]; }
```

```asm
# %rdi = index
leaq (%rdi,%rdi,4), %rax    # %rax = 5 * index
leaq pgh(,%rax,4), %rax     # %rax = pgh + 20 * index
```

**为什么绕一圈算 `5*index` 再乘 4**？因为 `lea` 的 scale 只能是 1/2/4/8，**没有 20**。所以先算 `5*i`（用 `%rdi + %rdi*4`），再乘 4 得 `20*i`。这是「用两条 lea 拼出任意小整数乘法」的标准套路。

**元素地址**（讲义 p59）：`A[i][j]` = `A + i*(C*K) + j*K` = `A + (i*C + j)*K`。

**元素访问代码**（讲义 p60）：

```c
int get_pgh_digit(int index, int dig) { return pgh[index][dig]; }
```

```asm
leaq (%rdi,%rdi,4), %rax    # 5 * index
addl %rax, %rsi             # 5*index + dig
movl pgh(,%rsi,4), %eax     # M[pgh + 4*(5*index+dig)]
```

**注意只用了三条指令、一次访存**——因为整块数组是连续的，编译器把二维下标压成了一维。

### 5.11 多级数组

讲义 p61：`int *univ[3] = {mit, cmu, ucb};` —— 这是**指针数组**，每个元素 8 字节，指向各自独立的 `int[5]`。

```
univ (168):  [0] → 56  (mit)
             [1] → 16  (cmu)
             [2] → 36  (ucb)
```

三个被指向的数组分散在内存各处（16、36、56），**彼此不一定相邻**。

**访问代码**（讲义 p62）：

```c
int get_univ_digit(size_t index, size_t digit) {
    return univ[index][digit];
}
```

```asm
# %rdi = index, %rsi = digit
salq $2, %rsi                # 4*digit
addq univ(,%rdi,8), %rsi     # p = univ[index] + 4*digit
movl (%rsi), %eax            # return *p
ret
```

**两次访存**：第一次 `univ(,%rdi,8)` 从数组里取指针，第二次 `(%rsi)` 用该指针取元素。

讲义 p63 把两者并排对比，这是本讲最重要的一张表：

| 声明 | C 表达式 | 地址计算 | 访存次数 |
|---|---|---|---|
| 嵌套 `int pgh[4][5]` | `pgh[i][j]` | `Mem[pgh + 20*i + 4*j]` | **1** |
| 多级 `int *univ[3]` | `univ[i][j]` | `Mem[Mem[univ + 8*i] + 4*j]` | **2** |

**C 代码长得几乎一样，机器代价差一倍。** 嵌套数组适合固定形状的矩阵（缓存友好、无额外指针）；多级数组适合「行长度不一」或「行需要独立分配」的场景（如字符串数组 `char *argv[]`）。

### 5.12 定长 vs 变长矩阵

讲义 p64–p66 对比 `int A[16][16]` 与 `int A[n][n]`。

**定长**（讲义 p65）：

```asm
# A in %rdi, i in %rsi, j in %rdx
salq $6, %rsi                # 64*i    （C=16, K=4 → C*K=64）
addq %rsi, %rdi              # A + 64*i
movl (%rdi,%rdx,4), %eax     # Mem[A + 64*i + 4*j]
```

**`salq $6` 而不是 `imulq $64`**：64 是 2 的幂，移位比乘法快（虽然现代 CPU 上 `imul` 也就 3 周期，但移位是 1 周期且不占乘法单元）。讲义 p65 明确点出：「No need for integer multiplication (for power of 2)」。

**变长**（讲义 p66）：

```asm
# n in %rdi, A in %rsi, i in %rdx, j in %rcx
imulq %rdx, %rdi             # n*i
leaq (%rsi,%rdi,4), %rax     # A + 4*n*i
movl (%rax,%rcx,4), %eax     # Mem[A + 4*n*i + 4*j]
```

**必须用 `imulq`**：`n` 编译期未知，`C*K = 4n` 不是常数，无法用移位。这是「变长数组慢一点」的机器级原因。

### 5.13 结构体

讲义 p68：结构体是「一块足够容纳所有字段的内存」，**字段按声明顺序排列**（即使换个顺序能更省空间），编译器决定总大小与各字段偏移。汇编里只看得到偏移，看不到字段名。

```c
struct rec {
    int a[4];        // 偏移 0，  16 字节
    size_t i;        // 偏移 16， 8 字节
    struct rec *next;// 偏移 24， 8 字节
};                   // 总大小 32
```

**取成员地址**（讲义 p69）：

```c
int *get_ap(struct rec *r, size_t idx) { return &r->a[idx]; }
```

```asm
# r in %rdi, idx in %rsi
leaq (%rdi,%rsi,4), %rax     # r + 4*idx
ret
```

`a` 的偏移是 0，所以 `&r->a[idx]` 就是 `r + 4*idx`——和普通数组完全一样。若字段不在偏移 0，就会多一条 `addq $offset`。

**遍历链表**（讲义 p70）：

```c
long length(struct rec *r) {
    long len = 0L;
    while (r) { len++; r = r->next; }
    return len;
}
```

```asm
.L11:
    addq $1, %rax            # len++
    movq 24(%rdi), %rdi      # r = Mem[r+24]
    testq %rdi, %rdi         # Test r
    jne  .L11                # if != 0, goto loop
```

**`movq 24(%rdi), %rdi`** 这一条同时做了三件事：从偏移 24 读指针、解引用、写回同一个寄存器。这是链表遍历的经典形态。

**讲义 p88 的 `set_val`** 展示了一个「无边界检查」的危险例子：

```c
void set_val(struct rec *r, int val) {
    while (r) {
        size_t i = r->i;
        r->a[r->i] = val;    // No bounds check!
        r = r->next;
    }
}
```

```asm
.L11:
    movq 16(%rdi), %rax      # i = Mem[r+16]
    movl %esi, (%rdi,%rax,4) # Mem[r+4*i] = val
    movq 24(%rdi), %rdi      # r = Mem[r+24]
    testq %rdi, %rdi
    jne  .L11
```

若 `r->i >= 4`，`movl %esi, (%rdi,%rax,4)` 就会写到 `a` 数组之外——**可能覆盖 `i` 或 `next` 字段本身**，造成链表被劫持。这是 attack lab 的思想雏形。

### 5.14 对齐

讲义 p71–p74。

**规则**：大小为 B 字节的基本类型，其地址必须是 B 的倍数。

| 类型 | 大小 | 地址低比特要求 |
|---|---|---|
| `char` | 1 | 无限制 |
| `short` | 2 | 最低 1 位为 0 |
| `int`, `float` | 4 | 最低 2 位为 00 |
| `double`, `long`, `char *` | 8 | 最低 3 位为 000 |

**动机**（讲义 p72）：

1. 内存按 4 或 8 字节的块访问，跨块的数据需要两次访问。
2. 跨 cache line（64 字节）的访存效率低。
3. 跨页（4 KiB）的数据会让虚拟内存处理变复杂（可能触发两次缺页）。

**结构体的对齐规则**（讲义 p73）：

- 每个字段满足自己的对齐要求。
- 结构体本身有个对齐要求 **K = 所有字段中最大的对齐值**。
- 结构体的**起始地址与总长度都必须是 K 的倍数**。

**例 1**（讲义 p71/p73）：`struct S1 { char c; int i[2]; double v; }`

| 字段 | 偏移 | 大小 | 说明 |
|---|---|---|---|
| `c` | 0 | 1 | |
| （填充） | 1–3 | 3 | 使 `i[0]` 落在 4 的倍数 |
| `i[0]` | 4 | 4 | |
| `i[1]` | 8 | 4 | |
| （填充） | 12–15 | 4 | 使 `v` 落在 8 的倍数 |
| `v` | 16 | 8 | |

总大小 **24**，K = 8（因为 `double`）。24 是 8 的倍数，**末尾不需要额外填充**。讲义 p73 特别标注：「**NOTE: K < sizeof(struct S1)**」——对齐要求 8 小于总大小 24，别把两者搞混。

**例 2**（讲义 p74）：`struct S2 { double v; int i[2]; char c; }`

| 字段 | 偏移 | 大小 |
|---|---|---|
| `v` | 0 | 8 |
| `i[0]` | 8 | 4 |
| `i[1]` | 12 | 4 |
| `c` | 16 | 1 |
| （外部填充） | 17–23 | 7 |

字段本身只用到 17 字节，但 K = 8，总长必须是 8 的倍数，所以补到 **24**。这 7 字节叫**外部填充（external padding）**，与 S1 里的**内部填充（internal padding）**相对。

**重新排列能省空间**：把 `S2` 的字段改成 `double v; int i[2]; char c;` 已经是较优顺序（大的在前）。若写成 `char c; double v; int i[2];`，`c` 后面要补 7 字节，`v` 在 8，`i` 在 16–23，总长仍是 24 但内部空隙更多——实际上三种顺序里 `S1` 的顺序（1+3+8+4+8）最差。**大字段优先排列**是减少填充的通用建议。

## 6. 代码示例

### 6.1 官方课程代码

**mult2 / multstore**（讲义 p6），出处 `90-原始PDF/15-213/lectures/05-machine-gamma.pdf` 第 6 页，见 5.2 节。

**incr**（讲义 p31），出处同上 PDF 第 31 页：

```asm
incr:
    movq (%rdi), %rax
    addq %rax, %rsi
    movq %rsi, (%rdi)
    ret
```

**call_incr**（讲义 p32），出处同上 PDF 第 32 页，完整代码见 5.5 节。

**get_digit / zincr**（讲义 p52–p53），出处同上 PDF 第 52–53 页，见 5.9 节。

**get_pgh_zip / get_pgh_digit**（讲义 p58/p60），出处同上 PDF 第 58、60 页，见 5.10 节。

**get_univ_digit**（讲义 p62），出处同上 PDF 第 62 页，见 5.11 节。

**fix_ele / var_ele**（讲义 p65–p66），出处同上 PDF 第 65–66 页，见 5.12 节。

**struct rec 系列**（讲义 p68–p70、p88），出处同上 PDF 第 68–70、88 页。

**pcount_r**（讲义 p77），出处同上 PDF 第 77 页，完整代码见 5.7 节。

**popcount_t**（讲义 p85），出处同上 PDF 第 85 页，见 5.8 节。

**数组访问综合示例**（讲义 p86–p87），出处同上 PDF 第 86–87 页：

```c
int main(int argc, char** argv) {
    zip_dig pgh[PCOUNT] = {{1,5,2,0,6},{1,5,2,1,3},{1,5,2,1,7},{1,5,2,2,1}};
    int *linear_zip = (int *) pgh;
    int *zip2 = (int *) pgh[2];
    int result = pgh[0][0] + linear_zip[7] + *(linear_zip + 8) + zip2[1];
    printf("result: %d\n", result);
    return 0;
}
```

输出 `result: 9`。逐项拆解：

- `pgh[0][0]` = 1
- `linear_zip[7]`：把整块当一维，第 7 个 = `pgh[1][2]` = 2
- `*(linear_zip + 8)` = 第 8 个 = `pgh[1][3]` = 1
- `zip2[1]` = `pgh[2][1]` = 5

1 + 2 + 1 + 5 = **9**。这个例子完美说明「二维数组就是一维数组 + 编译器的乘法」。

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：验证 caller-saved 导致的 bug**

```c
/* clobber.c —— 非官方示例，仅用于说明概念 */
#include <stdio.h>

long helper(long x) { return x * 2; }

long broken(long a) {
    register long keep asm("%rdx") = a;   /* 强制放在 %rdx（caller-saved） */
    helper(7);                            /* helper 可能覆盖 %rdx */
    return keep;
}

int main(void) { printf("%ld\n", broken(15213)); return 0; }
```

`register ... asm("...")` 是 GCC 扩展。`helper` 是否真的破坏 `%rdx` 取决于优化级别——这正是 caller-saved 的危险之处：**它能工作，但你不该依赖它**。正确做法是把值放进 `%rbx`（callee-saved），或让编译器自己分配。

**示例 B：手工计算结构体布局**

```c
/* layout.c —— 非官方示例，仅用于说明概念 */
#include <stdio.h>
#include <stddef.h>

struct A { char c; int i[2]; double v; };
struct B { double v; int i[2]; char c; };
struct C { char c; double v; int i[2]; };

int main(void) {
    printf("A: size=%zu c=%zu i=%zu v=%zu\n",
           sizeof(struct A), offsetof(struct A, c),
           offsetof(struct A, i), offsetof(struct A, v));
    printf("B: size=%zu v=%zu i=%zu c=%zu\n",
           sizeof(struct B), offsetof(struct B, v),
           offsetof(struct B, i), offsetof(struct B, c));
    printf("C: size=%zu c=%zu v=%zu i=%zu\n",
           sizeof(struct C), offsetof(struct C, c),
           offsetof(struct C, v), offsetof(struct C, i));
    return 0;
}
```

预期输出（x86-64）：

```
A: size=24 c=0 i=4 v=16
B: size=24 v=0 i=8 c=16
C: size=24 c=0 v=8 i=16
```

三者大小都是 24，但内部空隙分布不同。**手算方法**：从偏移 0 开始，每个字段的偏移向上取整到自己对齐值的倍数，最后总长向上取整到 K 的倍数。

**示例 C：用 GDB 观察栈帧**

```
$ gcc -g -O0 -o call_incr call_incr.c
$ gdb ./call_incr
(gdb) break incr
(gdb) run
(gdb) info registers rsp rbp rdi rsi
(gdb) x /4xg $rsp          # 看返回地址与栈上内容
(gdb) x /2i $rip           # 看当前指令
(gdb) stepi                # 单步执行一条
(gdb) info registers rsp
(gdb) finish               # 执行到 incr 返回
(gdb) info registers rsp rax
```

重点观察：`incr` 入口处 `(%rsp)` 就是返回地址；`-O0` 下 `%rbp` 被用作帧指针（`push %rbp; mov %rsp, %rbp`），`-O1` 下通常看不到 `%rbp`。

**示例 D：嵌套 vs 多级数组的访存次数**

```c
/* access.c —— 非官方示例，仅用于说明概念 */
#define R 4
#define C 5
int nested[R][C];
int *multi[R];
int row0[C], row1[C], row2[C], row3[C];

void init(void) {
    multi[0] = row0; multi[1] = row1; multi[2] = row2; multi[3] = row3;
}

int get_nested(int i, int j) { return nested[i][j]; }   /* 1 次访存 */
int get_multi(int i, int j)  { return multi[i][j]; }    /* 2 次访存 */
```

用 `gcc -O1 -S` 对比两者的汇编：

```asm
get_nested:
    leaq (%rdi,%rdi,4), %rax     # 5*i
    addl %eax, %esi              # 5*i + j
    movslq %esi, %rsi
    movl nested(,%rsi,4), %eax   # 1 次访存
    ret

get_multi:
    movslq %esi, %rsi
    movq multi(,%rdi,8), %rax    # 第 1 次访存：取指针
    movl (%rax,%rsi,4), %eax     # 第 2 次访存：取元素
    ret
```

**示例 E：递归深度与栈溢出**

```c
/* depth.c —— 非官方示例，仅用于说明概念 */
#include <stdio.h>

long depth(long n) {
    volatile char pad[64];       /* 强制每帧占 64 字节，避免被优化掉 */
    pad[0] = (char)n;
    if (n == 0) return 0;
    return 1 + depth(n - 1) + pad[0] * 0;
}

int main(void) {
    printf("%ld\n", depth(100000));
    return 0;
}
```

默认栈大小 8 MiB，每帧约 80 字节，约 10 万层就会段错误。用 `ulimit -s` 查看/调整栈大小，或用 `ulimit -s unlimited` 后重试。这是理解「栈是有限资源」的最直接实验。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| Caller-saved | Callee-saved | 前者 callee 可随意改，caller 要自己存；后者 callee 用前必须存、返回前恢复 |
| `%rbp`（callee-saved） | `%rsp`（特殊 callee-save） | 前者靠 `push`/`pop` 保存；后者靠 `sub`/`add` 对称抵消 |
| 参数寄存器 `%rdi`…`%r9` | 第 7 个及以后的参数 | 前者走寄存器；后者由 caller 压在栈上（argument build 区） |
| `call` 压入的地址 | `call` 的目标地址 | 前者是 `call` 的**下一条**指令地址（返回地址）；后者是被调函数入口 |
| `%rax` 是返回值 | `%rax` 是临时寄存器 | 两者都对：它是 caller-saved，返回时是返回值，过程中可随意当临时用 |
| `movl $3000, %esi` | `movq $3000, %rsi` | 前者短 1 字节，且自动清零高 32 位，效果相同 |
| 栈帧里的 local variables | 栈帧里的 saved registers | 前者是放不进寄存器的局部变量；后者是被调用者保存寄存器的旧值 |
| 嵌套数组 `A[R][C]` | 多级数组 `*A[R]` | 前者一整块连续，1 次访存；后者指针数组，2 次访存 |
| `A[i]` 的类型（嵌套） | `A[i]` 的类型（多级） | 前者是 `int[C]`（数组，退化为指针）；后者是 `int *`（指针值存在内存里） |
| 内部填充 | 外部填充 | 前者在字段之间；后者在结构体末尾，为使总长为 K 的倍数 |
| K（对齐要求） | `sizeof(struct)` | K 是最大字段对齐值；sizeof 是含填充的实际大小，通常 ≥ K 且是 K 的倍数 |
| 递归 | 尾递归 | 前者每层一个栈帧；后者调用后无计算，可被优化成循环（C 不保证） |
| `salq $6`（定长矩阵） | `imulq`（变长矩阵） | 前者 C*K 是 2 的幂，可用移位；后者运行时才知道，必须真乘法 |
| `z[i]` 的 `jbe` | `jl` | 前者无符号比较（`size_t i`）；后者有符号 |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-213/lectures/05-machine-gamma.pdf`
- **总页数**：88 页
- **重点页码**：
  - p2 标题（2026 年 9 月 8 日，第 5 讲）；p3 公告（Data Lab 当晚截止）
  - p4 本讲大纲（CSAPP 3.7 过程 / 3.8 数组 / 3.9 结构体）
  - p5、p12、p15 过程机制的三个方面（重复三次强调）
  - p6–p11 mult2/multstore 与 call/ret 逐帧跟踪
  - p13 参数寄存器与栈参数布局
  - p16–p29 栈式语言、调用链 yoo/who/amI、栈帧增减动画
  - p30 x86-64/Linux 栈帧完整布局
  - p31–p40 incr 与 call_incr 的栈全过程（含两条 Aside）
  - p41–p42 caller/callee 寄存器冲突与保存约定
  - p43–p44 寄存器分类表（caller-saved / callee-saved）
  - p45 过程机制总结
  - p48–p50 内存组织、数组分配、数组访问表达式表
  - p51–p53 zip_dig 示例与 zincr 循环
  - p55–p60 嵌套数组：布局、行地址、元素地址、两段汇编
  - p61–p63 多级数组与「1 次 vs 2 次访存」对比表
  - p64–p66 定长 vs 变长矩阵（`salq $6` vs `imulq`）
  - p68–p70 结构体表示、成员地址、链表遍历
  - p71–p74 对齐规则、S1/S2 布局、内部与外部填充
  - p77–p84 pcount_r 递归与「递归无需特殊机制」总结
  - p85 尾递归优化
  - p86–p87 数组综合示例（结果 9）
  - p88 set_val 无边界检查的危险示例
- **原始链接**：https://www.cs.cmu.edu/~213/lectures/05-machine-gamma.pdf
- **教材对应**：CS:APP 3e §3.7（过程）、§3.8（数组）、§3.9（异质数据结构）

> 待核实：讲义 p46 引用 Canvas 小测链接（`canvas.cmu.edu/courses/55964/quizzes/169253`），非 CMU 用户无法访问。讲义 p3 提到「Data Lab 今晚 11:59pm 截止」，具体日期以课程 schedule 为准。

## 9. 对应视频

**未找到官方公开录像。**

可参考的公开资源：

- 教材站点：https://csapp.cs.cmu.edu/ —— 第 3 章配套的 `struct` 与对齐示例代码。
- 课程日程：https://www.cs.cmu.edu/~213/schedule.html
- Bomb Lab 说明（https://csapp.cs.cmu.edu/3e/bomblab.pdf）—— 递归 phase 需要读懂本讲的栈帧。
- Attack Lab 说明（https://csapp.cs.cmu.edu/3e/attacklab.pdf）—— 直接利用本讲的栈布局与「无边界检查」漏洞。
- 本课 GDB 速查：`90-原始PDF/15-213/recitations/gdbnotes-x86-64.pdf`（文本在 `_scout/text/15-213__recitations__gdbnotes-x86-64.pdf.txt`）。

## 10. 本节复习

- 过程三机制：传递控制（`call`/`ret`）、传递数据（6 寄存器 + `%rax`）、管理局部数据（`sub`/`add %rsp`）。
- 参数顺序：`%rdi %rsi %rdx %rcx %r8 %r9`；第 7 个起走栈（argument build）。
- Caller-saved：`%rax`、6 个参数寄存器、`%r10`、`%r11`。
- Callee-saved：`%rbx`、`%rbp`、`%r12`–`%r15`；`%rsp` 特殊，返回时须复原。
- 栈帧从高到低：栈参数 → 返回地址 → 旧 `%rbp` → 保存的寄存器 → 局部变量 → argument build。
- 栈空间「按需分配」——纯寄存器函数不碰 `%rsp`。
- `subq $16, %rsp` 保持 16 字节对齐；`call` 压 8 字节。
- `movl $imm, %esi` 自动清零高 32 位且更短。
- 递归靠栈帧 + 保存约定，无需特殊机制；互递归同理。
- 尾递归可被优化成循环（调用后无计算），但 C 不保证。
- 一维数组：`z[i]` → `(%rdi,%rsi,4)`；无边界检查。
- 嵌套数组行主序：`A[i][j]` = `A + (i*C + j)*K`，1 次访存。
- 多级数组：`A[i][j]` = `Mem[Mem[A + 8i] + Kj]`，2 次访存。
- 定长矩阵用 `salq`（2 的幂），变长矩阵用 `imulq`。
- 结构体字段按声明顺序；偏移编译期确定；汇编只见偏移不见字段名。
- 对齐：B 字节类型地址须是 B 的倍数；K = 最大字段对齐值；起始地址与总长须是 K 的倍数。
- 内部填充在字段间，外部填充在末尾。

## 11. 自我检查

**题 1**：函数 `long f(long a, long b, long c, long d, long e, long g, long h, long i)` 的 8 个参数分别在哪里？返回值在哪里？

<details><summary>参考答案</summary>

| 参数 | 位置 |
|---|---|
| `a` | `%rdi` |
| `b` | `%rsi` |
| `c` | `%rdx` |
| `d` | `%rcx` |
| `e` | `%r8` |
| `g` | `%r9` |
| `h` | 栈上 `8(%rsp)`（进入函数后，`(%rsp)` 是返回地址） |
| `i` | 栈上 `16(%rsp)` |

返回值在 `%rax`。

注意「进入函数后」这个前提：`call` 已经压入了 8 字节返回地址，所以第 7 个参数在 `8(%rsp)` 而不是 `(%rsp)`。

</details>

**题 2**：`struct T { char a; double b; short c; int d; }` 在 x86-64 上的各字段偏移、内部填充位置、总大小、对齐要求 K 分别是多少？

<details><summary>参考答案</summary>

| 字段 | 偏移 | 大小 | 说明 |
|---|---|---|---|
| `a` | 0 | 1 | |
| （填充） | 1–7 | 7 | 使 `b` 落在 8 的倍数 |
| `b` | 8 | 8 | |
| `c` | 16 | 2 | |
| （填充） | 18–19 | 2 | 使 `d` 落在 4 的倍数 |
| `d` | 20 | 4 | |

字段结束于偏移 24。K = 8（`double` 最大），24 是 8 的倍数，**末尾无需外部填充**。

**总大小 = 24 字节**，内部填充共 7 + 2 = 9 字节。

若重排为 `double b; int d; short c; char a;`：`b`@0、`d`@8、`c`@12、`a`@14，填充 1 字节到 16，总大小 **16** 字节——省了 8 字节。这就是「大字段优先」的价值。

</details>

**题 3**：`int A[4][5]` 起始地址为 `0x1000`。求 `A[2][3]` 的地址。若改成 `int *B[4]`（多级数组），`B[2][3]` 需要几次访存？地址如何算？

<details><summary>参考答案</summary>

**嵌套数组**：`A[2][3]` = `A + (2*5 + 3)*4` = `0x1000 + 13*4` = `0x1000 + 52` = `0x1034`。**1 次访存**。

**多级数组**：`B` 是 4 个指针，每个 8 字节，起始地址 `0x1000`。

1. 读 `B[2]`：地址 `0x1000 + 2*8 = 0x1010`，读出指针值（假设为 `0x2000`）——**第 1 次访存**。
2. 读 `*(0x2000 + 3*4)` = `0x200C`——**第 2 次访存**。

共 **2 次访存**。地址公式：`Mem[Mem[B + 8*i] + 4*j]`。

</details>

**题 4**：下面的汇编中 `%rbx` 的使用是否必要？改成 `%rdx` 会怎样？

```asm
pcount_r:
    movl $0, %eax
    testq %rdi, %rdi
    je   .L6
    pushq %rbx
    movq %rdi, %rbx
    andl $1, %ebx
    shrq %rdi
    call pcount_r
    addq %rbx, %rax
    popq %rbx
.L6:
    rep; ret
```

<details><summary>参考答案</summary>

**必要**。`%rbx` 里存的 `x & 1` 要跨过 `call pcount_r` 存活，因为 `addq %rbx, %rax` 在调用之后执行。`%rbx` 是 callee-saved，递归调用（以及它内部的所有调用）必须保证返回时 `%rbx` 不变，所以这个值安全。

若改用 `%rdx`：`%rdx` 是 caller-saved，`pcount_r` 递归调用自己时，被调用的那份 `pcount_r` 会执行 `shrq %rdi` 之前的操作并可能使用 `%rdx`（在当前这份代码里恰好没用到，但编译器有权用），返回后 `%rdx` 的值不可信，`addq %rdx, %rax` 会加上垃圾值。结果随优化级别与编译器版本变化——**这是最坏的一类 bug：有时正确，有时错误**。

另外，若真用 `%rdx` 且希望它存活，就必须由 `pcount_r` 自己在 `call` 前把它压栈（caller-saved 的规则），那反而比用 `%rbx` 更啰嗦（因为 `%rbx` 只需 `push`/`pop` 各一次）。

</details>

**题 5**：`call_incr` 为什么用 `subq $16, %rsp` 而不是 `subq $8, %rsp`？如果改成 `$8` 会有什么后果？

<details><summary>参考答案</summary>

x86-64 ABI 要求**调用点的 `%rsp` 是 16 字节对齐**。`call` 会压入 8 字节返回地址，所以进入函数时 `%rsp ≡ 8 (mod 16)`。

- `subq $16`：`%rsp ≡ 8 - 16 ≡ 8 (mod 16)`，再 `call` 压 8 字节 → 进入被调函数时 `%rsp ≡ 0 (mod 16)`。**正确**。
- `subq $8`：`%rsp ≡ 8 - 8 ≡ 0 (mod 16)`，再 `call` → 进入被调函数时 `%rsp ≡ 8 (mod 16)`。**违反 ABI**。

后果：若被调函数使用 SSE 对齐指令（如 `movaps` 要求 16 字节对齐的操作数地址），会触发**通用保护异常（general protection fault）**，程序崩溃。即使不用 SSE，某些库函数（如 `printf` 内部的 `movaps`）也会崩。

另外，`v1` 放在 `8(%rsp)` 需要 8 字节对齐，`$8` 的分配也能满足这个要求，所以**问题不在 `v1` 本身，而在调用点的对齐**。

</details>

## 12. 进一步学习

- 上一讲：[[15-213-04-Machine-Programming-II-Control|CMU 15-213 - L04 Machine Programming II Control]]
- 下一讲：[[15-213-06-Machine-Programming-IV-Data|CMU 15-213 - L06 Machine Programming IV Data]] —— 浮点、联合体、缓冲区溢出。
- 课程导航：[[20-CMU-15-213/00-课程总览|CMU 15-213 - 课程总览]]、[[20-CMU-15-213/01-课程目录|CMU 15-213 - 课程目录]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- CS:APP 3e §3.7（过程）、§3.8（数组）、§3.9（异质数据结构）。
- x86-64 System V ABI 官方文档（https://gitlab.com/x86-psABIs/x86-64-ABI）—— 参数传递与寄存器保存的权威定义。
- Attack Lab（https://csapp.cs.cmu.edu/3e/attacklab.pdf）—— 本讲的栈布局是 attack 的前提。
- 课程日程：https://www.cs.cmu.edu/~213/schedule.html
