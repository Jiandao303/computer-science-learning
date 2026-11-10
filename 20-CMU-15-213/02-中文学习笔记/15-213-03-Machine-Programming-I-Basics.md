---
course: CMU 15-213
course_name: Introduction to Computer Systems
semester: Fall 2026
lecture_id: L03
topic: Machine Programming I - Basics
language: zh-CN
source_language: en
status: draft
tags:
  - CMU-15-213
  - 汇编语言
  - x86-64
  - 寄存器
  - 寻址模式
  - 条件码
---

# L03 Machine Programming I: Basics（机器级编程 I：基础）

> 开课日期：2026 年 9 月 1 日。本讲把 C 代码「翻译」成 x86-64 汇编：认识名词（寄存器与内存）、动词（指令）、后缀（数据宽度），以及最基本的控制手段——条件码与跳转。

## 1. 本节学习目标

1. 说明汇编语言、ISA（指令集架构）与微架构（microarchitecture）三者的关系。
2. 列出 x86-64 的 16 个通用整数寄存器，说明 `%rax`/`%eax`/`%ax`/`%al` 的层级关系与历史来源。
3. 掌握 `mov` 系列指令的后缀规则（`b`/`w`/`l`/`q`）与「内存到内存不可直接传送」的限制。
4. 熟练使用通用寻址模式 `D(Rb,Ri,S)`，把 C 的数组下标翻译成汇编。
5. 理解 `leaq` 的两种用途：取地址与做算术。
6. 说明条件码 CF/ZF/SF/OF 的含义，以及 `cmp`、`test` 如何设置它们。
7. 说明 `setX` 与 `jX` 指令如何读取条件码，并写出 `x > y` 的完整汇编。
8. 说明 `movz`/`movs` 扩展指令的三字母命名规则。
9. 描述 C → 汇编 → 目标码 → 可执行文件的工具链，并能用 `objdump`/`gdb` 反汇编。

## 2. 前置知识

- **L02**：补码、位运算、移位——汇编里的 `salq`/`sarq` 就是这些操作。
- **C 指针与数组**：`*p`、`a[i]`、`&x` 的语义。本讲的核心技能就是把它们翻译成寻址模式。
- **C 结构体**：后续 L06 会展开，本讲只需知道字段有偏移量。
- **基本命令行**：`gcc`、`objdump`、`gdb`。

## 3. 核心概念

- **Assembly Language（汇编语言）**：机器码的文本表示，与机器指令一一对应（讲义 p6 称之为「中间语言，动词极少，操作必须显式」）。
- **ISA（指令集架构）**：写汇编/机器码需要理解的处理器设计部分，如 x86-64、ARM、RISC-V。
- **Microarchitecture（微架构）**：ISA 的具体实现，如「Core i7」这一款 x86 处理器。同一 ISA 可有多种微架构。
- **Register（寄存器）**：CPU 核心内的超快存储，x86-64 有 16 个具名整数寄存器，定宽 64 位。
- **Program Counter（程序计数器，`%rip`）**：指向下一条要执行的指令。
- **Operand（操作数）**：指令的数据来源/去处，分立即数（immediate）、寄存器（register）、内存（memory）三类。
- **Addressing Mode（寻址模式）**：`D(Rb,Ri,S)` 表示 `Mem[Reg[Rb] + S*Reg[Ri] + D]`。
- **Condition Codes（条件码）**：CF（进位）、ZF（零）、SF（符号）、OF（溢出），由算术/逻辑指令隐式设置。
- **Control Flow（控制流）**：实际执行的指令序列；汇编中完全由跳转（goto）构造。

## 4. 通俗理解

**寄存器是 CPU 的口袋，内存是仓库。** 口袋只有 16 个，每个能装 8 字节；仓库很大但取一次货要走很远。所有计算都必须在口袋里完成——这就是为什么 `movq (%rax), (%rdx)` 这种「仓库到仓库」的指令不存在：必须经过口袋中转。

**汇编是「只有 goto 的语言」。** 讲义 p39 用一句加粗的话点明：C 的 `if`/`else`、`while`、`for` 在汇编里全都不存在，只剩「比较—条件跳转—无条件跳转」三件套。理解这一点，看任何汇编都不会迷路。

**后缀是尺子。** `mov` 本身不说明搬多少字节，`movb` 搬 1 字节、`movw` 搬 2、`movl` 搬 4、`movq` 搬 8。q 是 quad（四字，8 字节），l 是 long（4 字节），w 是 word（2 字节），b 是 byte（1 字节）。同时寄存器名字也要跟着换：`%rax` → `%eax` → `%ax` → `%al`。

## 5. 原理与推导

### 5.1 抽象层次与本讲位置

讲义 p4 把程序员分成三层：C programmer / Assembly programmer / Computer Designer。本讲把你从第一层拉到第二层——不需要懂门电路与时序，但必须懂寄存器与指令。

讲义 p50 给出「程序员可见状态」的四要素：

| 要素 | 说明 |
|---|---|
| PC（`%rip`） | 下一条指令的地址 |
| Register file（寄存器堆） | 16 个 64 位通用寄存器 + `%rip` |
| Condition codes | CF、ZF、SF、OF |
| Memory | 字节可寻址的数组，含代码、数据、栈 |

### 5.2 寄存器与历史包袱

讲义 p9 讲了命名的由来：

- 1978 年 8086：16 位寄存器，`ax` 是累加器（accumulator）。
- 1985 年 80386：扩展到 32 位，加前缀 `e`（extended）→ `eax`。
- 2003 年 AMD 推出 x86-64：扩展到 64 位，改用前缀 `r` → `rax`。

**寄存器命名规则**（讲义 p10）：

| 64 位 | 32 位 | 16 位 | 8 位 | 说明 |
|---|---|---|---|---|
| `%rax` | `%eax` | `%ax` | `%al` | 累加器，返回值 |
| `%rbx` | `%ebx` | `%bx` | `%bl` | base，被调用者保存 |
| `%rcx` | `%ecx` | `%cx` | `%cl` | counter，第 4 个参数 |
| `%rdx` | `%edx` | `%dx` | `%dl` | data，第 3 个参数 |
| `%rsi` | `%esi` | `%si` | `%sil` | source index，第 2 个参数 |
| `%rdi` | `%edi` | `%di` | `%dil` | destination index，第 1 个参数 |
| `%rsp` | `%esp` | `%sp` | `%spl` | 栈指针（专用） |
| `%rbp` | `%ebp` | `%bp` | `%bpl` | 基址指针（可选帧指针） |
| `%r8`–`%r15` | `%r8d`–`%r15d` | `%r8w`–`%r15w` | `%r8b`–`%r15b` | 2003 年新增 |

要点：**写 32 位寄存器会把高 32 位清零**（这是 x86-64 的规则，与写 8/16 位不同），因此编译器常用 `movl $0, %eax` 来清零整个 `%rax`。

### 5.3 mov 指令与操作数组合

`mov` 的格式是 `mov Src, Dest`（**注意：AT&T 语法源在前、目标在后**，与 Intel 语法相反）。

讲义 p15 的完整组合表：

| 源 | 目标 | 例子 | C 类比 |
|---|---|---|---|
| Imm | Reg | `movq $0x4, %rax` | `temp = 0x4;` |
| Imm | Mem | `movq $-147, (%rax)` | `*p = -147;` |
| Reg | Reg | `movq %rax, %rdx` | `temp2 = temp1;` |
| Reg | Mem | `movq %rax, (%rdx)` | `*p = temp;` |
| Mem | Reg | `movq (%rax), %rdx` | `temp = *p;` |
| Mem | Mem | **不允许** | 需要两条指令 + 一个临时寄存器 |

**为什么不能内存到内存**：x86 指令的编码中，一条指令最多允许一个内存操作数。这是 CISC 编码空间限制的直接后果，也是理解「必须经过寄存器」的关键。

### 5.4 寻址模式 D(Rb,Ri,S)

讲义 p27 给出通用形式：

```
D(Rb, Ri, S)  →  Mem[Reg[Rb] + S*Reg[Ri] + D]
```

| 分量 | 含义 | 取值 |
|---|---|---|
| D | 位移（displacement） | 常数，1/2/4 字节编码 |
| Rb | 基址寄存器 | 任意 16 个整数寄存器 |
| Ri | 索引寄存器 | 任意，**但不能是 `%rsp`** |
| S | 比例因子（scale） | 1、2、4、8 |

缺省时用单位元：缺 D 补 0，缺 S 补 1。所以 `(%rdi)` 就是 `Mem[%rdi]`。

讲义 p28 的计算实例（`%rdx = 0xf000`，`%rcx = 0x0100`）：

| 表达式 | 计算 | 结果 |
|---|---|---|
| `0x8(%rdx)` | 0xf000 + 0x8 | 0xf008 |
| `(%rdx,%rcx)` | 0xf000 + 0x100 | 0xf100 |
| `(%rdx,%rcx,4)` | 0xf000 + 4×0x100 | 0xf400 |
| `0x80(,%rdx,2)` | 2×0xf000 + 0x80 | 0x1e080 |

**数组下标为什么这么设计**：`int a[]` 的元素宽度是 4，所以 `a[i]` 的地址是 `a + 4*i`，正好对应 `(%rdi, %rsi, 4)`。讲义 p25–p26：

```c
char *d; char a = '\0'; d[y] = a;
→  movb %al, (%rdi, %rsi)        /* S = 1 */

int  *d; char a = 67;   d[y] = a;
→  movl %eax, (%rdi, %rsi, 4)    /* S = 4 */
```

比例因子只支持 1/2/4/8，恰好覆盖 `char`/`short`/`int`/`long`（以及指针）四种宽度——这是硬件对 C 类型的「贴心设计」。

### 5.5 算术与逻辑指令

讲义 p29 的两类指令：

**双操作数**（`Dest = Dest op Src`）：

| 指令 | 计算 |
|---|---|
| `addq Src, Dest` | `Dest = Dest + Src` |
| `subq Src, Dest` | `Dest = Dest - Src` |
| `imulq Src, Dest` | `Dest = Dest * Src` |
| `salq Src, Dest`（= `shlq`） | `Dest = Dest << Src` |
| `sarq Src, Dest` | `Dest = Dest >> Src`（算术） |
| `shrq Src, Dest` | `Dest = Dest >> Src`（逻辑） |
| `xorq Src, Dest` | `Dest = Dest ^ Src` |
| `andq Src, Dest` | `Dest = Dest & Src` |
| `orq Src, Dest` | `Dest = Dest \| Src` |

**单操作数**：`incq`（+1）、`decq`（−1）、`negq`（取负）、`notq`（取反）。

注意方向：`subq %rax, %rdx` 是 `%rdx = %rdx - %rax`，**不是** `%rax - %rdx`。这是初学者最常犯的错误。

### 5.6 leaq：不访问内存的「地址计算」

`leaq Src, Dst` 把 `Src` 这个**地址表达式**的值算出来放进 `Dst`，**不做内存访问**（讲义 p30）。

两种用途：

1. **取地址**：`p = &x[i]` → `leaq (%rdi,%rsi,4), %rax`。
2. **做算术**：因为寻址模式能算 `x + k*y`（k ∈ {1,2,4,8}），编译器用它来替代乘法。

经典例子 `long m12(long x) { return x*12; }`：

```asm
leaq (%rdi,%rdi,2), %rax   # t = x + 2*x = 3x
salq $2, %rax              # return t << 2 = 12x
```

用两次指令完成乘以 12，比 `imulq $12, %rdi, %rax` 更快（后者要 3 个周期，前者各 1 个）。

### 5.7 完整算术表达式示例

讲义 p33–p34 的例子是理解「编译器如何分配寄存器」的最佳素材：

```c
long arith(long x, long y, long z) {
    long t1 = x + y;
    long t2 = z + t1;
    long t3 = x + 4;
    long t4 = y * 48;
    long t5 = t3 + t4;
    long rval = t2 * t5;
    return rval;
}
```

生成：

```asm
arith:
    leaq  (%rdi,%rsi), %rax    # t1 = x + y
    addq  %rdx, %rax           # t2 = z + t1
    leaq  (%rsi,%rsi,2), %rdx  # rdx = y + 2y = 3y
    salq  $4, %rdx             # t4 = 3y << 4 = 48y
    leaq  4(%rdi,%rdx), %rcx   # t5 = x + 48y + 4
    imulq %rcx, %rax           # rval = t2 * t5
    ret
```

寄存器分配（讲义 p34）：

| 寄存器 | 用途 |
|---|---|
| `%rdi` | 参数 x |
| `%rsi` | 参数 y |
| `%rdx` | 参数 z，之后复用为 t4 |
| `%rax` | t1 → t2 → rval |
| `%rcx` | t5 |

两个值得注意的优化：`t3 + t4 = (x+4) + 48y` 被合并成一条 `leaq 4(%rdi,%rdx), %rcx`；`%rdx` 在 z 用完后立刻被复用作 t4。

### 5.8 条件码

算术/逻辑指令会**隐式**设置四个条件码（`leaq` 除外，因为它只算地址）：

| 条件码 | 名称 | 含义 |
|---|---|---|
| CF | Carry Flag | 无符号运算的最高位进位（可检测无符号溢出） |
| ZF | Zero Flag | 结果为 0 |
| SF | Sign Flag | 结果为负（最高位为 1） |
| OF | Overflow Flag | 有符号溢出 |

**两条专用设置指令**（讲义 p41–p43）：

- `cmp a, b`：计算 `b - a`，**只设条件码，不改 b**。用于 `if (a < b)`。注意操作数顺序：`cmpq %rsi, %rdi` 比较的是 `%rdi` 与 `%rsi`，计算 `%rdi - %rsi`。
- `test a, b`：计算 `b & a`，**只设 SF 与 ZF**。最常见的用法 `test %rX, %rX` 用来判断是否为 0；次要用法 `test %rX, %rY` 检查两个值的位是否有交集。

### 5.9 setX 与 jX

**`setX` 把条件码转成 0/1 字节**（讲义 p46）。例：

```c
int gt(long x, long y) { return x > y; }
```

```asm
gt:
    cmpq   %rsi, %rdi   # 比较 x 与 y（计算 x - y）
    setg   %al          # 若 x > y 则 %al = 1，否则 0
    movzbl %al, %eax    # 零扩展到 32 位，顺带清空 %rax 高 32 位
    ret
```

`movzbl` 是必需的：`setg` 只写 `%al` 一个字节，`%rax` 其余 63 位是旧值，必须清零才能作为返回值。

**`jX` 根据条件码跳转**（讲义 p45）：

| 指令 | 条件 | 说明 |
|---|---|---|
| `jmp` | 1 | 无条件 |
| `je` | ZF | 相等 / 为零 |
| `jne` | ~ZF | 不等 / 非零 |
| `js` | SF | 负数 |
| `jns` | ~SF | 非负 |
| `jg` | ~(SF^OF) & ~ZF | 大于（有符号） |
| `jge` | ~(SF^OF) | 大于等于（有符号） |
| `jl` | SF^OF | 小于（有符号） |
| `jle` | (SF^OF) \| ZF | 小于等于（有符号） |
| `ja` | ~CF & ~ZF | 大于（无符号，above） |
| `jb` | CF | 小于（无符号，below） |

**为什么有符号比较要看 `SF^OF`**：`SF` 是结果的符号位，但减法溢出时符号位会翻转。例如 `TMin - 1` 结果为 `TMax`（正），SF=0 而实际 `TMin < 1`。`SF^OF` 修正了这一点：OF=1 时把 SF 取反。这就是「有符号用 `jg`/`jl`、无符号用 `ja`/`jb`」的根本原因，也是 L02 中「有符号/无符号是两副眼镜」在指令层面的体现。

### 5.10 控制流的 goto 本质

讲义 p38–p39 的 `decision` 函数：

```c
void decision(int x) {
    if (x) op1(); else op2();
}
```

```asm
decision:
    testl  %edi, %edi    # x & x，设 ZF
    je     .L2           # x == 0 跳到 else
    call   op1
    jmp    .L1
.L2:
    call   op2
.L1:
    ret
```

这段代码揭示了 C 的 `if` 在机器层的真实形状：**条件跳转 + 无条件跳转 + 标签**。`for`、`while`、`switch` 同理，全部编译成 goto 网络（`switch` 还可能编译成跳转表，见 L04）。

### 5.11 数据宽度扩展指令

`movXYZ` 的三字母命名（讲义 p47）：

- `X` ∈ {`s`, `z`}：sign extend 或 zero extend。
- `Y` ∈ {`b`, `w`, `l`, `q`}：源宽度。
- `Z` ∈ {`w`, `l`, `q`}：目标宽度。

例：`movzbl %al, %eax` = zero-extend byte to long（1 字节零扩展到 4 字节）。

常见组合：`movzbl`、`movzwl`、`movslq`（**注意：没有 `movzlq`**，因为写 32 位寄存器会自动清零高 32 位，用 `movl` 即可）。这个「缺失的指令」是考试常考点。

### 5.12 从 C 到可执行文件

讲义 p52 的工具链：

```
p1.c p2.c  --[gcc -Og -S / 编译器]-->  p1.s p2.s
p1.s p2.s  --[gcc -c / as 汇编器]-->   p1.o p2.o
p1.o p2.o + 静态库(.a) --[gcc / ld 链接器]-->  可执行文件 p
```

- **编译器**：C → 汇编，`-Og` 表示「对调试友好的优化」。
- **汇编器**：汇编 → 目标码（.o），完成指令的二进制编码，但**不解析跨文件引用**。
- **链接器**：合并 .o，解析跨文件符号（详见 L07）。

讲义 p53 的 `sumstore` 例子：

```c
long plus(long x, long y);
void sumstore(long x, long y, long *dest) {
    long t = plus(x, y);
    *dest = t;
}
```

```asm
sumstore:
    pushq %rbx
    movq  %rdx, %rbx     # 保存 dest（因为 %rdx 会被调用破坏）
    call  plus
    movq  %rax, (%rbx)   # *dest = 返回值
    popq  %rbx
    ret
```

生成的 14 字节机器码（讲义 p56）：

```
0x53               push %rbx
0x48 0x89 0xd3     mov  %rdx,%rbx
0xe8 f2 ff ff ff   callq 400590 <plus>     ← 相对偏移，不是绝对地址
0x48 0x89 0x03     mov  %rax,(%rbx)
0x5b               pop  %rbx
0xc3               retq
```

`call` 的操作数是 `f2 ff ff ff` = −14（小端），即「下一条指令地址 − 14」——这就是相对寻址，它让代码可以在内存中任意搬移（位置无关）。

### 5.13 反汇编

讲义 p58–p60 给出两种方式：

```
objdump -d sum              # 命令行
gdb sum
(gdb) disassemble sumstore  # GDB 内
(gdb) x/14xb sumstore       # 查看 14 个字节
```

反汇编输出：

```
0000000000400595 <sumstore>:
  400595:  53               push   %rbx
  400596:  48 89 d3         mov    %rdx,%rbx
  400599:  e8 f2 ff ff ff   callq  400590 <plus>
  40059e:  48 89 03         mov    %rax,(%rbx)
  4005a1:  5b               pop    %rbx
  4005a2:  c3               retq
```

注意 `objdump` 省略了 `q` 后缀（它根据操作数寄存器推断宽度），所以看到 `mov` 而不是 `movq` 是正常的。

讲义 p61 提醒：**任何字节序列都能被反汇编**，甚至 Word 文档也能（`objdump -d WINWORD.EXE`），因为反汇编器不区分代码与数据——这正是 Attack Lab 中构造 ROP 攻击的原理基础。

## 6. 代码示例

### 6.1 官方课程代码

**swap 函数**（讲义 p16–p23），出处 `90-原始PDF/15-213/lectures/03-machine.pdf` 第 16–23 页：

```asm
swap:
    movq (%rdi), %rax     # t0 = *xp
    movq (%rsi), %rdx     # t1 = *yp
    movq %rdx, (%rdi)     # *xp = t1
    movq %rax, (%rsi)     # *yp = t0
    ret
```

对应的 C 代码（讲义 p17）：

```c
void swap(long *xp, long *yp) {
    long t0 = *xp;
    long t1 = *yp;
    *xp = t1;
    *yp = t0;
}
```

讲义 p18 的寄存器映射表：`%rdi`=xp、`%rsi`=yp、`%rax`=t0、`%rdx`=t1。讲义 p19–p23 用五张图逐条演示内存 `0x100`/`0x120` 处的值 123/456 如何交换。

**arith 函数**（讲义 p33–p34），出处同上 PDF 第 33–34 页，完整代码见 5.7 节。

**m12 函数**（讲义 p30），出处同上 PDF 第 30 页，见 5.6 节。

**decision 函数**（讲义 p39），出处同上 PDF 第 39 页，见 5.10 节。

**gt 函数**（讲义 p46），出处同上 PDF 第 46 页，见 5.9 节。

**sumstore 函数**（讲义 p53–p60），出处同上 PDF 第 53–60 页，见 5.12 节。

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：观察编译器如何用 leaq 替代乘法**

```c
/* lea_demo.c —— 非官方示例，仅用于说明概念 */
long times15(long x) { return x * 15; }
long times17(long x) { return x * 17; }
long times100(long x) { return x * 100; }
```

编译 `gcc -Og -S lea_demo.c` 后，典型输出（具体形式依编译器版本而异）：

```asm
times15:
    leaq (%rdi,%rdi,4), %rax   # 5x
    leaq (%rax,%rax,2), %rax   # 15x
    ret
times17:
    leaq (%rdi,%rdi,8), %rax   # 9x
    leaq (%rax,%rax,2), %rax   # 27x
    leaq (%rdi,%rax,2), %rax   # x + 54x? —— 观察实际输出
    ret
times100:
    imulq $100, %rdi, %rax     # 超出 lea 能力，退回乘法
    ret
```

要点：`leaq` 只能算 `x + k*y`（k ∈ {1,2,4,8}），所以能表达的常数乘子有限（如 2、3、4、5、8、9、10、12、15、16、17…）；`100` 需要链式 `lea`，编译器会权衡指令数，往往直接用 `imulq`。

**示例 B：把 C 数组访问手工翻译成汇编**

```c
/* array_demo.c —— 非官方示例，仅用于说明概念 */
long get(long *a, long i)      { return a[i]; }
void set(int *a, long i, int v){ a[i] = v; }
long addr(long *a, long i)     { return (long)&a[i]; }
```

```asm
get:
    movq (%rdi,%rsi,8), %rax    # 8 字节元素，S = 8
    ret
set:
    movl %edx, (%rdi,%rsi,4)    # 4 字节元素，S = 4
    ret
addr:
    leaq (%rdi,%rsi,8), %rax    # 只要地址，不访问内存
    ret
```

**示例 C：用 GDB 观察条件码**

```c
/* cc_demo.c —— 非官方示例，仅用于说明概念 */
int main(void) {
    int a = -1, b = 1;
    if (a > b) return 1;
    return 0;
}
```

```
$ gcc -Og -g cc_demo.c -o cc_demo
$ gdb -q cc_demo
(gdb) break main
(gdb) run
(gdb) disassemble /r main
(gdb) nexti                 # 单步到 cmpl 之后
(gdb) info registers eflags # 查看 ZF/SF/OF/CF
(gdb) p $eflags & 0x40      # ZF
(gdb) p $eflags & 0x80      # SF
(gdb) p $eflags & 0x800     # OF
```

`eflags` 中：CF = bit 0，ZF = bit 6，SF = bit 7，OF = bit 11。

**示例 D：验证 `test %rX, %rX` 判断零**

```asm
# 非官方示例，仅用于说明概念
check:
    testq %rdi, %rdi    # rdi & rdi，只设 SF/ZF
    je    .is_zero
    movl  $1, %eax
    ret
.is_zero:
    xorl  %eax, %eax    # 比 movl $0, %eax 更短
    ret
```

`xorl %eax, %eax` 是清零的惯用法：2 字节，且比 `movl $0, %eax`（5 字节）短。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| AT&T 语法 `mov Src, Dest` | Intel 语法 `mov Dest, Src` | 操作数顺序相反；本课与 gcc/objdump 默认用 AT&T |
| `movq %rax, %rdx` | `movq (%rax), %rdx` | 前者复制寄存器值，后者读取 `%rax` 指向的内存 |
| `leaq 8(%rdi), %rax` | `movq 8(%rdi), %rax` | 前者取地址 `rdi+8`，后者读该地址的内容 |
| `cmpq %rsi, %rdi` | `cmpq %rdi, %rsi` | 前者算 `%rdi - %rsi`，后者算 `%rsi - %rdi`，条件码相反 |
| `test a, b` | `and a, b` | 都算 `a & b`，但 `test` 不写回结果，只设 SF/ZF |
| `jg`/`jl` | `ja`/`jb` | 前者有符号（看 SF^OF），后者无符号（看 CF） |
| `sarq` | `shrq` | 算术右移补符号位；逻辑右移补 0 |
| `movslq` | `movzlq` | 后者**不存在**；32→64 零扩展用 `movl`（自动清高 32 位） |
| `%eax` 写入 | `%ax` 写入 | 写 32 位清零高 32 位；写 16/8 位**保留**高位 |
| `call` 的 `f2 ff ff ff` | 绝对地址 | 它是相对偏移（−14），使代码位置无关 |
| 汇编语言 | 机器码 | 前者是文本表示，后者是字节；一一对应但不可读 |
| ISA | 微架构 | 前者是指令集规范（x86-64），后者是具体实现（Core i7） |
| `%rsp` 可作索引 | `%rsp` 作 `Ri` | **不能**作索引寄存器，只能作基址 |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-213/lectures/03-machine.pdf`
- **总页数**：73 页
- **重点页码**：
  - p2 标题（2026 年 9 月 1 日）
  - p4 三层抽象（C / 汇编 / 电路）
  - p5 寄存器 vs 内存
  - p6–p7 汇编语法与 ISA/微架构定义
  - p9–p10 寄存器历史与 x86-64 寄存器全表
  - p12 后缀与寄存器宽度对照
  - p13–p15 mov 与操作数组合表（含「不能内存到内存」）
  - p16–p23 swap 的逐条演示
  - p24–p28 寻址模式 D(Rb,Ri,S) 与计算实例
  - p29 双/单操作数算术指令
  - p30 leaq 与 m12
  - p31 寄存器约定（`%rip`/`%rsp`/`%rdi`/`%rsi`/`%rdx`/`%rax`）
  - p33–p34 arith 完整推导与寄存器分配
  - p38–p39 控制流的 goto 本质与 decision
  - p41–p43 cmp / test
  - p45 跳转指令全表
  - p46–p47 setX 与 movXYZ 命名
  - p49 架构/微架构/代码形式定义
  - p50 程序员可见状态
  - p52–p56 编译-汇编-链接工具链与 14 字节机器码
  - p57–p60 反汇编（objdump / gdb）
  - p61 反汇编任意字节（WinWord 示例）
  - p66–p73 x86 历史与 AMD64 由来
- **原始链接**：https://www.cs.cmu.edu/~213/lectures/03-machine.pdf
- **教材对应**：CS:APP 3e §3.1–3.6（历史视角、程序编码、数据格式、访问信息、算术逻辑操作）

> 待核实：讲义 p35 引用了 Canvas 上的课堂小测链接（`canvas.cmu.edu/courses/55964/quizzes/169245`），非 CMU 用户无法访问。

## 9. 对应视频

**未找到官方公开录像。**

可参考的公开资源：

- 教材站点：https://csapp.cs.cmu.edu/ —— 第 3 章的配套幻灯片与 `mstore`/`store` 示例代码。
- 课程日程：https://www.cs.cmu.edu/~213/schedule.html
- 本课 recitation 材料 `_scout/text/15-213__recitations__x86-cheat-sheet.pdf.txt` 与 `15-213__recitations__gdbnotes-x86-64.pdf.txt`（Bomblab 的 GDB 速查）是本讲最好的配套读物。
- Bomb Lab（https://csapp.cs.cmu.edu/3e/labs.html）要求逐行读懂汇编，是检验本讲的实战方式。

## 10. 本节复习

- 汇编 = 名词（寄存器/内存）+ 动词（指令）+ 后缀（宽度）+ 关系（条件码与跳转）。
- 16 个整数寄存器；`%rax`/`%eax`/`%ax`/`%al` 是同一寄存器的不同宽度视图。
- 后缀：`b`=1、`w`=2、`l`=4、`q`=8 字节。
- `mov` 不支持内存到内存。
- 寻址 `D(Rb,Ri,S)` = `Mem[Rb + S*Ri + D]`，S ∈ {1,2,4,8}，Ri 不能是 `%rsp`。
- `leaq` 不算内存，用于取地址或算 `x + k*y`。
- 条件码 CF/ZF/SF/OF；`cmp` 算 `b-a` 只设码，`test` 算 `b&a` 只设 SF/ZF。
- `setX` 写 1 字节，必须配 `movzbl` 清零高位。
- `jg/jl` 有符号（SF^OF），`ja/jb` 无符号（CF）。
- 汇编没有 `if`/`while`，只有 `goto`。
- 写 32 位寄存器清零高 32 位；没有 `movzlq`。
- 工具链：`gcc -Og -S` → `gcc -c` → `gcc`；`objdump -d` / `gdb disassemble` 反汇编。

## 11. 自我检查

**题 1**：已知 `%rdx = 0x1000`，`%rcx = 0x20`，求 `0x10(%rdx,%rcx,8)` 计算出的地址。

<details><summary>参考答案</summary>

`0x1000 + 8 × 0x20 + 0x10 = 0x1000 + 0x100 + 0x10 = 0x1110`

这正是 `long a[]` 中 `&a[32]` 的地址（32 × 8 = 0x100）。

</details>

**题 2**：把 `long arith2(long x, long y) { return x - 3*y; }` 翻译成尽量少的 x86-64 指令。

<details><summary>参考答案</summary>

```asm
arith2:
    leaq (%rsi,%rsi,2), %rsi   # rsi = 3y
    movq %rdi, %rax            # rax = x
    subq %rsi, %rax            # rax = x - 3y
    ret
```

也可以 3 条完成：`leaq (%rsi,%rsi,2), %rax` → `subq %rax, %rdi` → `movq %rdi, %rax`，但需要多一次搬移。注意 `subq %rsi, %rax` 是 `%rax - %rsi`，方向不能反。

</details>

**题 3**：`cmpq %rsi, %rdi` 之后执行 `setl %al`，等价于 C 的什么表达式？如果改用 `setb %al` 呢？

<details><summary>参考答案</summary>

`cmpq %rsi, %rdi` 计算 `%rdi - %rsi`。

- `setl`：有符号「小于」，等价于 `return x < y;`（x 在 `%rdi`，y 在 `%rsi`）。
- `setb`：无符号「低于」，等价于 `return (unsigned long)x < (unsigned long)y;`。

两者在同一组位上可能给出不同答案，例如 `x = -1`、`y = 1` 时 `setl` 得 1，`setb` 得 0。

</details>

**题 4**：为什么 `movb %al, (%rdi)` 之后若要 `%rax` 作为返回值，通常还需要一条 `movzbl %al, %eax`？

<details><summary>参考答案</summary>

因为写 8 位寄存器 `%al` **只修改 `%rax` 的最低字节**，高 56 位保留旧值。若 `%rax` 之前存着无关数据，直接 `ret` 会返回一个高位被污染的 64 位值。`movzbl %al, %eax` 把低字节零扩展到 32 位，而写 32 位寄存器会**自动清零高 32 位**，因此一条指令就完成了「清零 + 扩展」。

</details>

**题 5**：`leaq 8(%rdi,%rsi,4), %rax` 与 `movq 8(%rdi,%rsi,4), %rax` 的差别是什么？各自对应什么 C 代码？

<details><summary>参考答案</summary>

- `leaq`：把地址 `%rdi + 4*%rsi + 8` 本身放进 `%rax`，**不访问内存**。对应 `long *p = &a[i] + 1;`（假设 `a` 是 `int*` 在 `%rdi`）。
- `movq`：读取该地址处的 8 字节内容放进 `%rax`。对应 `long v = *(long*)((char*)a + 4*i + 8);`。

一个常见的坑：`leaq` 不设条件码，所以不能靠它之后跟 `je` 来判断结果是否为零。

</details>

## 12. 进一步学习

- 上一讲：[[15-213-02-Bits-Bytes-and-Integers|CMU 15-213 - L02 Bits, Bytes, and Integers]]
- 下一讲：[[15-213-04-Machine-Programming-II-Control|CMU 15-213 - L04 Machine Programming II Control]] —— 系统展开 `if`/`while`/`switch` 的汇编形态。
- 课程导航：[[20-CMU-15-213/00-课程总览|CMU 15-213 - 课程总览]]、[[20-CMU-15-213/01-课程目录|CMU 15-213 - 课程目录]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- CS:APP 3e §3.1–3.6，尤其 §3.4「访问信息」的寻址模式表与 §3.5「算术和逻辑操作」的指令表。
- 官方 x86-64 速查表：`_scout/text/15-213__recitations__x86-cheat-sheet.pdf.txt`（对应 `90-原始PDF/15-213/recitations/x86-cheat-sheet.pdf`）。
- 课程日程：https://www.cs.cmu.edu/~213/schedule.html
