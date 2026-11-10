---
course: CMU 15-213
course_name: Introduction to Computer Systems
semester: Fall 2026
lecture_id: L15
topic: Code Optimization
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-213
  - 代码优化
  - 编译器优化
  - 指令级并行
  - 循环展开
  - CPE
---

# 代码优化（Code Optimization）

## 1. 本节学习目标

- 能说出编译器优化的三大目标：减少指令数、避免等内存、避免分支。
- 能列举五类与机器无关的优化（常量折叠、死代码消除、公共子表达式消除、代码移动、内联）并各举一例。
- 能解释存储器别名（memory aliasing）和函数调用为什么是优化的两大障碍，并给出 `restrict`、局部变量、循环外提等规避写法。
- 能看懂现代 CPU 的执行模型（指令控制单元、执行单元、分支预测、退役单元），解释分支误预测的代价。
- 能用 CPE（cycles per element）衡量性能，并说明 `combine1` → `combine4` → 循环展开 → 多累加器这条优化链每一步的收益来源。
- 能解释指令级并行（ILP）与延迟界限（latency bound）、吞吐量界限（throughput bound）的关系。

## 2. 前置知识

- [[15-213-03-Machine-Programming-I-Basics]] 与 [[15-213-04-Machine-Programming-II-Control]]：会读 x86-64 汇编，理解寄存器、`mov`/`add`/`cmp`/`jne`。
- [[15-213-10-Cache-Memories]]：cache-friendly 的访问模式（本节多次提到“存储器是瓶颈”）。
- 基本的数据结构与算法复杂度概念（本节会强调：编译器改不了算法复杂度）。
- C 的指针与 `restrict` 限定符。

## 3. 核心概念

- **Constant Folding（常量折叠）**：在编译期算出常量表达式的结果。
- **Dead Code Elimination（死代码消除）**：不生成永远不会执行、或结果会被覆盖的代码。
- **Common Subexpression Elimination, CSE（公共子表达式消除）**：重复计算只做一次。
- **Code Motion（代码移动）**：把循环不变量（loop-invariant）的计算移到循环外。
- **Inlining（内联）**：把函数体复制进调用点。
- **Memory Aliasing（存储器别名）**：两个指针可能指向同一块内存，编译器无法假设它们互不干扰。
- **Basic Block（基本块）**：没有跳入跳出的一段直线代码。
- **Local / Global Optimization（局部/全局优化）**：前者在单个基本块内，后者处理整个控制流图。
- **Instruction Control Unit, ICU（指令控制单元）**：取指、译码、预测分支，跑在执行单元前面。
- **Execution Unit, EU（执行单元）**：真正做算术、访存的部件，可以有多个。
- **Retirement Unit（退役单元）**：按程序顺序提交结果，保证分支预测错误时可回滚。
- **Branch Prediction（分支预测）**：猜分支方向并提前执行；猜错要作废（invalidate）并重载流水线。
- **CPE（Cycles Per Element，每元素周期数）**：`Cycles = CPE × n + Overhead`，CPE 是拟合直线的斜率。
- **Loop Unrolling（循环展开）**：复制循环体以减少循环控制开销。
- **Scheduling（调度）**：重排指令，让多个功能部件同时忙碌。
- **ILP（Instruction-Level Parallelism，指令级并行）**：多条无依赖的指令同时执行。
- **Latency Bound（延迟界限）**：由关键路径（依赖链）长度决定的下界。
- **Throughput Bound（吞吐量界限）**：由功能部件数量与发射能力决定的下界。

## 4. 通俗理解

编译器优化像一位极其谨慎的编辑：它能帮你删掉重复的句子、把无关的从句挪到前面、把缩写展开，但它**绝不会改动文章的意思**——哪怕那个意思是笔误。所以“写出编译器友好的代码”本质上是：不要给它制造“这里可能改变语义”的疑虑。

两大疑虑来源就是本节的主角。第一是**别名**：你写 `b[i] += a[...]`，编译器想“万一 `b` 和 `a` 是同一块内存呢？那我就不能把 `b[i]` 缓存在寄存器里”。第二是**函数调用**：你写 `i < strlen(s)`，编译器想“`strlen` 是外部函数，鬼知道它会不会改 `s`？那我只能每次重新调用”。这两条疑虑各自能把线性算法变成平方算法或让性能差好几倍，而它们都只需要改一行代码就能消除。

后半节转向硬件：现代 CPU 一次能发射好几条指令，但它必须**猜**分支方向才能不停下来等。猜对了流水线满负荷，猜错了几十拍的成果全部作废。于是“减少分支”“让分支可预测”成了优化的重要维度——这也是为什么排序后的数据能让同一个循环快好几倍。

最后是量化：用 CPE 把性能写成一条直线，斜率就是每个元素的平均代价。优化就是不断把这个斜率压向硬件的物理极限。

## 5. 原理与推导

### 5.1 编译器优化的目标

讲义第 9 页给出三条：

1. **减少指令数**
   - 不要重复计算（CSE）
   - 不要做无用计算（死代码消除）
   - 避开慢指令（乘、除）
2. **避免等内存**
   - 尽量把数据留在寄存器里
   - 用 cache 友好的访问模式
   - 尽早、且只加载一次
3. **避免分支**
   - 不做不必要的判断
   - 让 CPU 更容易预测分支去向
   - 展开循环，把分支开销摊到更多指令上

### 5.2 编译器优化的四条限制

讲义第 10 页，这段是理解“为什么我的代码没被优化”的关键：

1. **改不了算法复杂度**：只能改常数因子。但常数因子也可能值 10 倍以上。
2. **不能改变程序行为**：程序员可能不在乎某个边界情况，但编译器不知道你不在乎。例外是语言标准明确允许的改动（如 `-ffast-math` 允许重排浮点运算）。
3. **通常一次只看一个函数**：全程序分析（LTO, Link-Time Optimization）很贵但越来越流行；内联是把多个函数合成一个的手段。
4. **难以预知运行时输入**：PGO（profile-guided optimization）能针对常见情况优化，但“最坏情况”可能同样重要——尤其是暴露给恶意输入的网络服务。

### 5.3 五类与机器无关的优化

**#1 常量折叠（第 13 页）**

```c
long mask = 0xFF << 8;              →  long mask = 0xFF00;
int namelen = strlen("Harry Bovik"); →  int namelen = 11;
```

注意第二例：连库函数调用都能被消掉，因为参数是编译期已知的常量字符串。

**#2 死代码消除（第 14 页）**

```c
if (0) { puts("Kilroy was here"); }      /* 永不执行 */
if (1) { puts("Only bozos on this bus"); }
x = 23;
x = 42;                                   /* 前一次赋值被覆盖 */
```

讲义提醒：这些代码看起来傻，但**往往是其它优化产生的中间结果**，而且两次赋值可能相隔很远。

**#3 公共子表达式消除（第 15 页）**

```c
norm[i] = v[i].x * v[i].x + v[i].y * v[i].y;
/* 变成 */
elt = &v[i];
x = elt->x;
y = elt->y;
norm[i] = x*x + y*y;
```

`v[i]` 的三次地址计算被合并成一次。

**#4 代码移动（第 16 页）**

```c
for (j = 0; j < n; j++)
    a[n*i+j] = b[j];
/* 变成 */
int ni = n*i;
for (j = 0; j < n; j++)
    a[ni+j] = b[j];
```

前提：**每次迭代的结果都相同**。`n*i` 在循环中不变，所以可以外提。

**#5 内联（第 17–19 页）**

```c
int pred(int x) { return x == 0 ? 0 : x - 1; }
int func(int y) { return pred(y) + pred(0) + pred(y+1); }
```

内联后：

```c
int func(int y) {
  int tmp;
  if (y == 0) tmp = 0; else tmp = y - 1;
  if (0 == 0) tmp += 0; else tmp += 0 - 1;      /* 条件恒真，分支可删 */
  if (y+1 == 0) tmp += 0; else tmp += (y + 1) - 1;
  return tmp;
}
```

再经常量折叠与死代码消除（第 19 页）：

```c
int func(int y) {
  int tmp = 0;
  if (y != 0) tmp = y - 1;
  if (y != -1) tmp += y;
  return tmp;
}
```

讲义用这个例子说明：**内联本身不是目的，它是打开其它优化大门的钥匙**。代价是代码膨胀，可能挤爆 i-cache 反而变慢。

### 5.4 障碍一：存储器别名

讲义第 21 页：

```c
void sum_rows1(double *a, double *b, long n) {
    for (i = 0; i < n; i++) {
        b[i] = 0;
        for (j = 0; j < n; j++)
            b[i] += a[i*n + j];       /* 每轮都写回内存 */
    }
}
```

生成的汇编（第 21 页）：

```asm
movq    $0, (%rsi)
        pxor    %xmm0, %xmm0
.L4:
        addsd   (%rdi), %xmm0
        movsd   %xmm0, (%rsi)      ; 每轮都把累加值写回 b[i]
        addq    $8, %rdi
        cmpq    %rcx, %rdi
        jne     .L4
```

为什么不能把 `b[i]` 留在 `%xmm0` 里累加完再写回？因为**编译器不知道 `b` 与 `a` 是否重叠**。若 `B` 落在 `A` 内部，那么每轮写 `b[i]` 都会改动后续要读的 `a[...]`，写回时机就影响结果。

讲义第 22 页用一个具体例子证明这种担心不是多余的：

```c
double A[9] = {0,1,2, 4,8,16, 32,64,128};
double B[3] = A+3;          /* B 与 A 重叠 */
sum_rows1(A, B, 3);
```

执行过程（讲义逐帧给出数组快照）：

```
init:  B = [4, 8, 16]
i = 0: B = [3, 8, 16]
i = 1: B = [3, 22, 16]
i = 2: B = [3, 22, 224]
```

结果与“先累加再写回”的版本不同，说明别名情况下语义确实变了。

**解法（第 23 页）**：用局部变量做中间结果，让写回只发生一次：

```c
void sum_rows2(double *a, double *b, long n) {
    for (i = 0; i < n; i++) {
        double val = 0;
        for (j = 0; j < n; j++)
            val += a[i*n + j];
        b[i] = val;
    }
}
```

汇编变成：

```asm
        pxor    %xmm0, %xmm0
.L4:
        addsd   (%rdi), %xmm0
        addq    $8, %rdi
        cmpq    %rax, %rdi
        jne     .L4
        movsd   %xmm0, (%rsi)      ; 循环外只写一次
```

注意：这个改写**在别名情况下也是正确的**（局部变量天然不受别名影响），所以它既是性能优化也是正确性保证。另一种解法是加 `restrict`：

```c
void sum_rows(double *restrict a, double *restrict b, long n);
```

`restrict` 告诉编译器“这是访问该内存的唯一指针”，于是编译器可以放心地把 `b[i]` 缓存在寄存器里。

### 5.5 障碍二：函数调用

讲义第 24 页，同一个功能的三个版本：

```c
/* 平方时间：每轮都调 strlen */
void lower_quadratic(char *s) {
    for (i = 0; i < strlen(s); i++)
        if (s[i] >= 'A' && s[i] <= 'Z') s[i] += 'a' - 'A';
}

/* 仍是平方：每改一次就重算长度 */
void lower_still_quadratic(char *s) {
    size_t i, n = strlen(s);
    for (i = 0; i < n; i++)
        if (s[i] >= 'A' && s[i] <= 'Z') {
            s[i] += 'a' - 'A';
            n = strlen(s);
        }
}

/* 线性：只算一次 */
void lower_linear(char *s) {
    size_t i, n = strlen(s);
    for (i = 0; i < n; i++)
        if (s[i] >= 'A' && s[i] <= 'Z') s[i] += 'a' - 'A';
}
```

为什么编译器不能自动把 `strlen(s)` 外提？因为 `strlen` 是外部函数，编译器看不到它的实现，无法证明它不修改 `s`、也不依赖 `s` 的每次变化。**跨函数的信息缺失**是这里和别名的共同根源。

第 24–25 页的曲线图：横轴是字符串长度（0–32KB），纵轴是指令数（0–75M）。`lower_quadratic` 与 `lower_still_quadratic` 都是抛物线，`lower_linear` 是一条几乎贴地的直线。讲义还给了 `accidentallyquadratic.tumblr.com` 这个专门收集此类 bug 的站点。

### 5.6 现代 CPU 的执行模型

讲义第 28 页的框图：**指令控制单元**（取指、译码、分支预测）→ 操作（operations）→ **执行单元**（分支、算术、加载、存储）→ **退役单元** → 寄存器更新。指令 cache 与数据 cache 分开（对应 [[15-213-10-Cache-Memories]] 中的 L1 i-cache / d-cache）。

关键点（第 29 页）：**ICU 必须跑在 EU 前面很远**，才能持续喂饱执行单元。如果 CPU 必须等 `cmp` 的结果才知道下一条取哪里，就会浪费几十个周期。

### 5.7 分支预测与误预测代价

讲义第 30–33 页用一个循环说明：

```asm
401029:  mulsd  (%rdx),%xmm0,%xmm0
40102d:  add    $0x8,%rdx
401031:  cmp    %rax,%rdx
401034:  jne    401029
```

假设数组长度 100。执行到 `i = 99` 时，预测器按“向后跳转 = 循环 = 跳转发生”的启发式预测 taken，正确。到 `i = 100` 时它仍预测 taken，于是**取指并开始执行 `i = 101` 的迭代**——但这次实际不跳转。

- 第 31 页：`Predict Taken (Oops)`，已经 fetch 了 `i=101`，若真执行会读到数组外的非法位置。
- 第 32 页：**Invalidate（作废）**——因为这些指令还没退役（retirement），寄存器与内存都没被真正修改，直接丢弃即可。
- 第 33 页：**Recovery**——从正确地址 `401036: jmp 401040` 重新填充流水线。代价是若干时钟周期，现代处理器上可能成为主要性能瓶颈。

**预测技术（第 34 页）**：

- 简单启发式：向后分支（backwards）多为循环，预测 taken；向前分支（forwards）多为 if，预测 not taken。
- 更复杂的预测器记录每个分支的历史行为，因为分支行为往往相关。
- 权衡：准确率 vs 预测状态的开销。
- 讲义提到 2025 Championship Branch Prediction 竞赛，研究方向是剩下那些“无法预测”的分支（强数据依赖、与历史无相关）。

### 5.8 为分支预测而优化

讲义第 35 页给两条路：

**减少分支数**：变换循环、展开循环、使用条件传送（conditional move，`cmov`）。讲义特意注明“not always a good idea”——`cmov` 在有副作用或计算昂贵时反而更慢。

**让分支可预测**：排序数据（引用 StackOverflow 上那个著名问题 11227809：为什么排序后遍历数组快很多）；避免间接分支（indirect branch），如函数指针、虚函数。

第 35 页还给了 `cmov` 的具体对照。原版：

```asm
.Loop:
    movzbl 0(%rbp,%rbx), %edx
    leal   -65(%rdx), %ecx
    cmpb   $25, %cl
    ja     .Lskip              ; 数据相关分支，难预测
    addl   $32, %edx
    movb   %dl, 0(%rbp,%rbx)
.Lskip:
    addl   $1, %rbx
    cmpq   %rax, %rbx
    jb     .Loop
```

用 `cmov` 后：

```asm
.Loop:
    movzbl 0(%rbp,%rbx), %edx
    movl   %edx, %esi
    leal   -65(%rdx), %ecx
    addl   $32, %edx
    cmpb   $25, %cl
    cmova  %esi, %edx          ; 条件选择，无分支
    movb   %dl, 0(%rbp,%rbx)   ; 内存写变成无条件
    addl   $1, %rbx
    cmpq   %rax, %rbx
    jb     .Loop
```

注意讲义的批注：“Memory write now unconditional!”——代价是每次迭代都写内存，即使值没变。

### 5.9 循环展开与调度

**展开（第 36 页）**：

```c
for (size_t i = 0; i < nelts; i++)
    A[i] = B[i]*k + C[i];
/* 展开 4 次 */
for (size_t i = 0; i < nelts - 4; i += 4) {
    A[i  ] = B[i  ]*k + C[i  ];
    A[i+1] = B[i+1]*k + C[i+1];
    A[i+2] = B[i+2]*k + C[i+2];
    A[i+3] = B[i+3]*k + C[i+3];
}
```

收益：分摊循环条件判断的成本；为 CSE、代码移动、调度创造机会；为向量化做准备。风险：代码变大可能挤爆 i-cache。

讲义在此提问“**这个改动什么时候是错的？**”——提示：`nelts - 4` 在 `nelts` 是无符号类型且小于 4 时会下溢成巨大值；另外若 `A` 与 `B`/`C` 重叠，重排读写顺序会改变语义。

**调度（第 37 页）**：把加载都提到展开循环的开头：

```c
for (size_t i = 0; i < nelts - 4; i += 4) {
    B0 = B[i]; B1 = B[i+1]; B2 = B[i+2]; B3 = B[i+3];
    C0 = C[i]; C1 = C[i+1]; C2 = C[i+2]; C3 = C[i+3];   /* 讲义原文此处误写为 B[i+3] */
    A[i  ] = B0*k + C0;
    A[i+1] = B1*k + C1;
    A[i+2] = B2*k + C2;
    A[i+3] = B3*k + C3;
}
```

> 待核实：讲义第 37 页原文 `C3 = B[i+3];`，从上下文看应为 `C[i+3]`，疑为讲义笔误。

调度为什么有效？因为 `mulsd` 的延迟有好几拍，先把 4 个加载全发出去，乘法部件就不会空等。这也解释了“为什么我们需要很多寄存器”——同时驻留的中间值越多，能并行的指令越多。

### 5.10 基准测试：向量求和

讲义第 39–48 页用 CSAPP 第 5 章的 `combine` 系列函数做量化。

**数据结构与接口（第 39 页）**：

```c
typedef struct { size_t len; data_t *data; } vec;
int get_vec_element(vec *v, size_t idx, data_t *val) {
    if (idx >= v->len) return 0;
    *val = v->data[idx];
    return 1;
}
```

`data_t` 取 `int`/`long`/`float`/`double`，`OP` 取 `+`/`*`，`IDENT` 取 `0`/`1`。

**CPE（第 41 页）**：`Cycles = CPE × n + Overhead`。CPE 是 “cycles per element” 的斜率。图中 `psum1` 斜率 9.0，`psum2` 斜率 6.0。

**性能表（第 42、44、47 页）**，单位 CPE：

| 方法 | int add | int mult | double add | double mult |
|---|---|---|---|---|
| Combine1 未优化 | 22.68 | 20.02 | 19.98 | 20.18 |
| Combine1 -O1 | 10.12 | 10.12 | 10.17 | 11.14 |
| Combine1 -O3 | 4.5 | 4.5 | 6 | 7.8 |
| Combine4 | 1.27 | 3.01 | 3.01 | 5.01 |
| Unroll（2 累加器） | 0.81 | 1.51 | 1.51 | 2.51 |

**Combine4 的三项基本优化（第 43 页）**：

```c
void combine4(vec_ptr v, data_t *dest) {
    long length = vec_length(v);      /* 1. 把 vec_length 移出循环 */
    data_t *d = get_vec_start(v);     /* 2. 直接拿数据指针，省掉每次边界检查 */
    data_t t = IDENT;
    for (i = 0; i < length; i++)
        t = t OP d[i];                /* 3. 在临时变量里累加 */
    *dest = t;
}
```

三项分别对应：消除函数调用、消除边界检查分支、消除别名导致的反复写内存。

**为什么 double 比 int 慢？** 因为浮点加法/乘法的延迟更长（加法约 3–4 拍，乘法约 4–5 拍），而 `t = t OP d[i]` 是一条**串行依赖链**，每一轮必须等上一轮的结果。这就是**延迟界限**：CPE 不可能低于运算本身的延迟。

**循环展开的收益（第 45–46 页）**：

```c
for (i = 0; i < limit; i+=2) {
    x0 = x0 OP d[i];
    x1 = x1 OP d[i+1];
}
```

用两个**独立**的累加器 `x0`、`x1`，把一条长依赖链拆成两条，于是 CPU 能同时发射两次运算。汇编（第 46 页）：

```asm
.L3:
        addq   (%rdx), %rcx
        addq    $16, %rdx
        addq   -8(%rdx), %rdi
        cmpq   %r8, %rdx
        jne    .L3
```

注意两条 `addq` 互不依赖——这正是“multiple instructions every cycle”的来源。表中 int add 从 1.27 降到 0.81，double add 从 3.01 降到 1.51（约等于延迟的一半，因为两条链并行）。

**还能更快吗（第 48 页）**：手工调优 + 计算机体系结构知识可以做到每周期 4–16 个元素（多累加器 + 向量指令），最新的编译器正在缩小这个差距。

### 5.11 总结：如何获得高性能

讲义第 49 页：

1. **好的编译器与编译选项**。
2. **不做次优的事**：当心隐藏的算法低效（如循环里的 `strlen`）；写编译器友好的代码；注意优化障碍（函数调用与内存引用）；仔细看最内层循环（大部分工作在那里）。
3. **为机器调优**：利用多个功能部件（和向量指令）；避免不可预测的分支；让代码 cache 友好。

### 5.12 局部优化与全局优化

讲义第 51 页（附加页）：局部优化作用于单个基本块（常量折叠、强度削弱、死代码消除、局部 CSE），全局优化处理整个控制流图（循环变换、代码移动、全局 CSE）。图中的“setup / entry / loop / done / exit”展示了控制流图的结构，也提示了哪部分容易优化（直线代码）、哪部分复杂（带循环与分支）。

## 6. 代码示例

### 6.1 官方课程代码

**常量折叠（15-optimization.pdf 第 13 页）**：

```c
long mask = 0xFF << 8;                 → long mask = 0xFF00;
int namelen = strlen("Harry Bovik");   → int namelen = 11;
```

**别名导致的每轮写回（15-optimization.pdf 第 21 页）**：

```asm
movq    $0, (%rsi)
        pxor    %xmm0, %xmm0
.L4:
        addsd   (%rdi), %xmm0
        movsd   %xmm0, (%rsi)
        addq    $8, %rdi
        cmpq    %rcx, %rdi
        jne     .L4
```

**消除别名后的版本（15-optimization.pdf 第 23 页）**：

```asm
        pxor    %xmm0, %xmm0
.L4:
        addsd   (%rdi), %xmm0
        addq    $8, %rdi
        cmpq    %rax, %rdi
        jne     .L4
        movsd   %xmm0, (%rsi)
```

**`cmov` 替代分支（15-optimization.pdf 第 35 页）**：`cmova %esi, %edx`，见 5.8 节完整对照。

**Combine4（15-optimization.pdf 第 43 页）** 与 **两路展开（第 45 页）** 见 5.10 节。

**展开后的汇编（15-optimization.pdf 第 46 页）**：

```asm
.L3:
        addq   (%rdx), %rcx
        addq    $16, %rdx
        addq   -8(%rdx), %rdi
        cmpq   %r8, %rdx
        jne    .L3
```

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

演示别名如何改变结果（对应讲义第 22 页的例子，可直接编译运行）：

```c
/* 非官方示例：别名让“写回时机”影响结果 */
#include <stdio.h>

void sum_rows1(double *a, double *b, long n) {
    for (long i = 0; i < n; i++) {
        b[i] = 0;
        for (long j = 0; j < n; j++)
            b[i] += a[i*n + j];      /* 每轮写回 */
    }
}

void sum_rows2(double *a, double *b, long n) {
    for (long i = 0; i < n; i++) {
        double val = 0;              /* 局部变量，写回一次 */
        for (long j = 0; j < n; j++)
            val += a[i*n + j];
        b[i] = val;
    }
}

int main(void) {
    double A1[9] = {0,1,2, 4,8,16, 32,64,128};
    double A2[9] = {0,1,2, 4,8,16, 32,64,128};
    double B1[3], B2[3];
    sum_rows1(A1, A1 + 3, 3);        /* B 与 A 重叠 */
    sum_rows2(A2, A2 + 3, 3);
    printf("sum_rows1: %g %g %g\n", A1[3], A1[4], A1[5]);
    printf("sum_rows2: %g %g %g\n", A2[3], A2[4], A2[5]);
    return 0;
}
```

在 `-O0` 与 `-O2` 下分别运行，会看到两个函数的输出不同——这正是编译器不敢自动优化的原因。

用局部变量 + `restrict` 让编译器放心：

```c
/* 非官方示例：三种写法，性能依次提高 */
#include <stddef.h>

/* 慢：可能别名，且每轮调函数 */
double dot_slow(const double *a, const double *b, size_t n) {
    double s = 0;
    for (size_t i = 0; i < n; i++)
        s += a[i] * b[i];
    return s;
}

/* 中：告诉编译器互不重叠 */
double dot_restrict(const double *restrict a, const double *restrict b, size_t n) {
    double s = 0;
    for (size_t i = 0; i < n; i++)
        s += a[i] * b[i];
    return s;
}

/* 快：4 路展开 + 4 个独立累加器，打破依赖链 */
double dot_unroll4(const double *restrict a, const double *restrict b, size_t n) {
    double s0 = 0, s1 = 0, s2 = 0, s3 = 0;
    size_t i = 0;
    for (; i + 3 < n; i += 4) {
        s0 += a[i  ] * b[i  ];
        s1 += a[i+1] * b[i+1];
        s2 += a[i+2] * b[i+2];
        s3 += a[i+3] * b[i+3];
    }
    for (; i < n; i++) s0 += a[i] * b[i];
    return (s0 + s1) + (s2 + s3);    /* 注意：浮点重排会改变舍入 */
}
```

最后一行值得注意：**浮点加法不满足结合律**，`(s0+s1)+(s2+s3)` 与顺序累加的结果在最低位可能不同。这就是讲义第 10 页说的“编译器必须保持行为不变”——除非你用 `-ffast-math` 明确授权。

用 `perf` 观察分支误预测（Linux）：

```bash
# 非官方示例：对比排序前后的分支误预测率
gcc -O2 -o branchtest branchtest.c
perf stat -e branches,branch-misses ./branchtest
```

若把测试数据先 `qsort` 再跑，`branch-misses` 通常从百分之几降到千分之几——这就是讲义第 35 页引用的那个 StackOverflow 现象。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| 局部优化 | 全局优化 | 前者在单个基本块内（常量折叠、死代码），后者跨控制流图（代码移动、循环变换） |
| 代码移动 | 循环展开 | 前者把不变量提出循环，后者复制循环体；前者减少工作量，后者增加并行度 |
| 别名 | 悬垂指针 | 别名是两个合法指针指向同一处（合法但妨碍优化）；悬垂是指向已释放内存（bug） |
| `restrict` | `const` | 前者承诺“唯一访问路径”，帮助优化；后者承诺“本函数不修改”，不解决别名 |
| 延迟界限 | 吞吐量界限 | 前者由依赖链长度决定（`t = t OP x` 的串行性），后者由功能部件数量决定；展开打破的是前者 |
| 分支预测错误 | 分支本身慢 | 预测正确时分支几乎免费；代价全在误预测后的作废与重填 |
| CPE | 时间复杂度 | CPE 是每元素周期数（常数因子），不改变 O(n)；编译器只能改 CPE |
| `-O1` | `-O3` | 表里可见 `-O3` 对 int 从 10.12 降到 4.5，但对 double mult 只从 11.14 到 7.8——收益依代码而定 |

## 8. 对应原版讲义

- PDF 相对路径：`90-原始PDF/15-213/lectures/15-optimization.pdf`
- 总页数：51 页
- 重点页码：
  - 标题页（15th Lecture, October 22, 2026）：第 2 页
  - 今日大纲：第 4 页
  - 编译器先驱（Hopper、Backus、Allen）：第 6–8 页
  - 优化的三大目标：第 9 页
  - 优化的四条限制：第 10 页
  - Godbolt 现场演示链接：第 12 页
  - 常量折叠：第 13 页
  - 死代码消除：第 14 页
  - 公共子表达式消除：第 15 页
  - 代码移动：第 16 页
  - 内联三页：第 17–19 页
  - 存储器别名（含数组快照）：第 21–22 页
  - 消除别名惩罚：第 23 页
  - 函数调用不能外提（三个 lower 版本 + 曲线图）：第 24–25 页
  - 现代 CPU 框图：第 28 页
  - 分支是挑战：第 29 页
  - 分支预测与循环：第 30–31 页
  - 误预测作废与恢复：第 32–33 页
  - 预测技术与 CBP 竞赛：第 34 页
  - 为分支预测优化（含 cmov 对照）：第 35 页
  - 循环展开：第 36 页
  - 调度：第 37 页
  - 基准数据结构与计算：第 39–40 页
  - CPE 定义：第 41 页
  - 性能表：第 42、44、47 页
  - Combine4：第 43 页
  - 两路展开：第 45–46 页
  - 进一步优化空间：第 48 页
  - 总结：第 49 页
  - 附加页（局部/全局优化）：第 51 页
- 原始链接：https://www.cs.cmu.edu/~213/lectures/15-optimization.pdf
- 待人工核对：第 37 页 `C3 = B[i+3];` 疑为 `C[i+3]` 的笔误。

## 9. 对应视频

未找到官方公开录像。

## 10. 本节复习

- 优化三目标：少指令、少等内存、少分支。
- 四条限制：改不了复杂度、不能改行为、只看单函数、不知运行时输入。
- 五类优化：常量折叠、死代码消除、CSE、代码移动、内联（内联是打开其它优化的钥匙）。
- 两大障碍：别名（用局部变量或 `restrict`）、函数调用（手动外提）。
- CPU 执行模型：ICU 跑在 EU 前面，靠分支预测不停顿；误预测要作废并重填流水线。
- 减少分支的手段：展开、`cmov`、排序数据、避免间接分支。
- CPE 是性能直线的斜率；优化就是把斜率压向硬件极限。
- 优化链：Combine1 22.68 → -O3 4.5 → Combine4 1.27 → 展开 0.81（int add）。
- 浮点比整数慢是因为依赖链遇上长延迟；展开用多累加器打破依赖链。

## 11. 自我检查

1. 编译器为什么不能自动把 `for (i = 0; i < strlen(s); i++)` 里的 `strlen(s)` 提到循环外？两种修法各是什么？
2. 讲义第 22 页的 `sum_rows1(A, B, 3)`（`B = A+3`）为什么结果与 `sum_rows2` 不同？这说明编译器的什么假设是必要的？
3. 讲义第 36 页的 4 路展开 `for (i = 0; i < nelts - 4; i += 4)` 在什么情况下是错的？至少说出两种。
4. 下表中 double add 从 Combine4 的 3.01 降到展开后的 1.51，为什么恰好约一半？为什么 int add 从 1.27 降到 0.81 而不是 0.635？
5. 为什么 `cmov` 版本里“内存写变成无条件”可能反而是坏事？

<details>
<summary>参考答案</summary>

1. `strlen` 是外部函数，编译器看不到其实现，无法证明它不修改 `s`、也不依赖 `s` 在循环中的变化，因此不能把调用外提（这属于“不能改变程序行为”的限制）。修法一：手动把长度存进局部变量 `size_t n = strlen(s);`；修法二：如果确定字符串在循环中不变，也可以把 `strlen` 换成自己实现的、能被内联的版本，让编译器看到函数体。

2. 因为 `B = A+3` 与 `A` 重叠，`sum_rows1` 每轮把 `b[i]` 写回内存，这次写入会改变后续要读的 `a[...]`（具体是 `A[3..5]` 正是 `B[0..2]`），于是累加过程中读到的值被前面的写操作改掉了，最终得到 `[3, 22, 224]`。而 `sum_rows2` 在局部变量里累加完才写一次，读到的始终是原始 `A` 的值。这说明编译器必须假设“两个指针可能别名”，否则就会生成改变程序行为的代码。

3. (a) `nelts` 是无符号类型（`size_t`）且小于 4 时，`nelts - 4` 下溢成一个极大的数，循环会越界狂奔。(b) 若 `A` 与 `B` 或 `C` 指向重叠内存，展开后把 4 次“读-算-写”重排成“读4个-算4个-写4个”，读到的值可能与逐次执行不同，语义改变。(c) 展开版本没有处理尾部剩余元素（`nelts % 4`），需要补一个收尾循环。

4. `t = t OP d[i]` 是一条串行依赖链，CPE 受运算延迟限制：double 加法延迟约 3 拍，实测 3.01 正对应它。两路展开把一条链拆成两条独立链，两个加法可以重叠执行，于是每个元素摊到的周期减半（3.01 → 1.51）。int 加法延迟只有 1 拍，Combine4 的 1.27 已经不是延迟界限而是别的瓶颈（循环开销、加载吞吐），所以展开只能把循环控制开销摊薄，收益有限，降到 0.81 而不是 0.635。

5. 无条件写内存意味着每次迭代都产生一次 store，即使这个字符根本不需要转换。这增加了 store 单元的流量、占用 store buffer，还可能造成额外的 cache 写操作；如果数据大多不需要转换（分支本来高度可预测），用分支反而更快。所以讲义注明 `cmov` “not always a good idea”。

</details>

## 12. 进一步学习

- 下一讲：[[15-213-16-Processes]]
- 前一讲：[[15-213-14-Dynamic-Memory-Allocation-Advanced]]
- 课程总览：[[20-CMU-15-213/00-课程总览|CMU 15-213 - 课程总览]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Code Optimization、Throughput、Cache）
- CSAPP 第 3 版第 5 章全章，尤其是 5.1–5.6（CPE 与优化链）、5.7–5.8（循环展开与 ILP）、5.11（一些限制性的东西）；5.12 节用“identify and eliminate unnecessary work”总结了本节的两大障碍。
- 动手：用 Godbolt（讲义第 12 页给的 `https://godbolt.org/z/Es5s8qsvj`）把 `-O0`/`-Og`/`-O2`/`-O3` 的汇编并排对比，是理解本节最快的方式。
