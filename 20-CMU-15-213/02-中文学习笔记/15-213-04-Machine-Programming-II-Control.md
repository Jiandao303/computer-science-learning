---
course: CMU 15-213
course_name: Introduction to Computer Systems
semester: Fall 2026
lecture_id: L04
topic: Machine Programming II - Control
language: zh-CN
source_language: en
status: draft
tags:
  - CMU-15-213
  - 汇编语言
  - 控制流
  - 循环
  - switch
  - 跳转表
  - 过程调用
---

# L04 Machine Programming II: Control（机器级编程 II：控制）

> 开课日期：2026 年 9 月 3 日。本讲把 C 的三种控制结构——循环、`switch`、函数调用——全部拆成 goto 与栈操作。核心结论：**x86-64 没有循环，也没有函数调用，只有跳转和栈。**

## 1. 本节学习目标

1. 说明 AT&T 与 Intel 语法的六项差异，并能在两者之间转换。
2. 从寄存器值判断哪些是「可能的指针」，解释 `%rsp`、`%rip` 必然是指针。
3. 说明 `leaq` 的三个优势（三操作数、一条指令完成复杂算术、不影响条件码）。
4. 把 `do-while`、`while`（两种翻译）、`for` 循环翻译成 goto 形式，并说明 `-Og` 与 `-O1` 的差异。
5. 说明 `switch` 的跳转表（jump table）结构、`ja` 边界检查的作用与间接跳转的写法。
6. 说明 `pushq`/`popq` 的语义与栈的生长方向。
7. 说明 `call`/`ret` 如何用栈传递控制权，并手工跟踪返回地址的入栈出栈。
8. 说明过程机制的三个方面：传递控制、传递数据、内存管理。

## 2. 前置知识

- **L03**：寄存器、寻址模式、`mov`/`lea`、条件码、`cmp`/`test`、`setX`/`jX`。
- **C 控制结构**：`do-while`、`while`、`for`、`switch`（含 fall-through）、函数调用。
- **栈的概念**：LIFO 结构，但这里要落到具体地址与 `%rsp`。

## 3. 核心概念

- **AT&T Syntax（AT&T 语法）**：源在前、目标在后，寄存器带 `%`，立即数带 `$`。
- **Jump Table（跳转表）**：存放各 `case` 目标地址的数组，用 `jmp *table(,%rdi,8)` 间接跳转。
- **Indirect Jump（间接跳转）**：目标地址来自寄存器或内存，而非指令中的标签。
- **Stack（栈）**：向低地址生长的内存区域，`%rsp` 指向栈顶。
- **Return Address（返回地址）**：`call` 之后那条指令的地址，由 `call` 自动压栈。
- **ABI（Application Binary Interface，应用二进制接口）**：过程调用中寄存器用途、参数位置、栈布局的约定。
- **Calling Convention（调用约定）**：ABI 中关于参数与返回值传递的具体规则。
- **Stack Frame（栈帧）**：一次过程调用占用的栈区域。

## 4. 通俗理解

**循环就是「往回跳的 goto」。** 讲义 p19 提出一个很好的判别法：`if` 的 goto 往后跳（跳过一段代码），循环的 goto 往回跳（重复一段代码）。看清跳转方向，就看清了控制结构。

**`switch` 是「查表跳转」。** 与其写七个 `cmp` 逐个比较，编译器干脆造一张表：第 x 项存着「x 对应的代码在哪」。执行时一条 `jmp *表(,%rdi,8)` 就到位了。代价是要先检查 x 在不在表的范围内——这就是那条 `ja` 的来历。

**栈是「便利贴堆」。** `call` 时把「回来时该去哪」写在便利贴上贴到堆顶，`ret` 时撕下最上面那张照着走。嵌套调用就是越贴越高（地址越低）。忘记撕（或撕错）就是栈溢出攻击的原理。

## 5. 原理与推导

### 5.1 AT&T 与 Intel 语法

讲义 p6 的对照表：

| 特性 | AT&T 语法 | Intel 语法 |
|---|---|---|
| 操作数顺序 | source, destination | destination, source |
| 寄存器前缀 | `%`（`%eax`） | 无（`eax`） |
| 立即数前缀 | `$`（`$10`） | 无（`10`） |
| 内存寻址 | `disp(base,index,scale)` | `[base + index*scale + disp]` |
| 尺寸后缀 | `b`/`w`/`l`/`q`（`movl`） | 由操作数推断或 `dword ptr` |

本课与 gcc、objdump、gdb 默认都使用 AT&T。读 Intel 手册（如 Intel SDM）时必须做心算转换，这是读文档时最常见的失误来源。

### 5.2 机器指令的三层表示

讲义 p4–p5 用同一条指令展示三层：

```
C:         *dest = t;
Assembly:  movq %rax, (%rbx)
Machine:   0x40059e:  48 89 03
```

进一步拆到比特（讲义 p5）：

```
0100 1 0 0 0   10001011   00 000 011
REX  W R X B   MOV r->x   Mod R  M
```

- `REX` 前缀的 `W` 位表示 64 位操作数。
- `10001011` 是 `MOV r/m64, r64` 的操作码。
- `ModR/M` 字节 `00 000 011`：mod=00（寄存器间接）、reg=000（`%rax`）、r/m=011（`%rbx`）。

这段编码分析是理解「机器码为什么长短不一」的入口：一条 `mov` 可能 3 字节，也可能 7 字节，取决于寻址模式与位移大小。

### 5.3 哪些寄存器值是指针

讲义 p10–p15 讨论一个实战问题：`gdb` 的 `info registers` 只给数字，怎么知道哪个是指针？

三条判据：

1. **`%rsp` 与 `%rip` 永远是指针**（栈顶地址与指令地址）。
2. **与 `%rsp`/`%rip` 数值接近的寄存器很可能也是指针**（同一栈帧或同一代码段）。
3. **看它怎么被使用**：若出现 `mov (%rsi), %rsi`，则 `%rsi` 的值被当作地址解引用，必定是指针。

讲义 p15 进一步给出寻址模式中的推断规则：

| 表达式 | 谁是地址 | 理由 |
|---|---|---|
| `(%rsi, %rbx)` | 不确定 | 两者相加，都可能是基址或偏移 |
| `(%rsi, %rbx, 2)` | `%rsi` | 有 scale 的必是索引（数组下标），基址才是指针 |
| `0x400570(, %rbx, 2)` | `0x400570` | 常量基址（如跳转表），`%rbx` 是下标 |
| `lea (anything), %rax` | 不确定 | `lea` 可能只是做算术 |

这条「带 scale 的是索引」的规则在 Bomb Lab 里极其有用。

### 5.4 leaq 的三个优势

讲义 p9 明确列出编译器偏爱 `lea` 的原因：

1. **一条指令完成复杂计算**：`x + k*y + d`。
2. **它是 x86 少有的三操作数指令**：`lea (%rbx,%rbx,2), %rax` 读一个写一个，不破坏源操作数。相比之下 `addq %rbx, %rax` 是两操作数，会覆盖 `%rax`。
3. **它不影响条件码**：可以在 `cmp` 之后、`jX` 之前插入 `lea` 而不破坏比较结果。这一点在优化后的代码里非常关键。

讲义 p8 强调 `lea` 与普通内存操作数的区别：

```asm
mov 6(%rbx,%rdi,8), %ax    # ax = *(rbx + rdi*8 + 6)     访问内存
add 6(%rbx,%rdi,8), %ax    # ax += *(rbx + rdi*8 + 6)    访问内存
xor %ax, 6(%rbx,%rdi,8)    # *(rbx + rdi*8 + 6) ^= ax    访问内存
lea 6(%rbx,%rdi,8), %rax   # rax = rbx + rdi*8 + 6       不访问内存
```

### 5.5 循环的三种翻译

**do-while**（讲义 p20–p22）。C：

```c
long pcount_do(unsigned long x) {
    long result = 0;
    do {
        result += x & 0x1;
        x >>= 1;
    } while (x);
    return result;
}
```

goto 形式：

```c
long pcount_goto(unsigned long x) {
    long result = 0;
loop:
    result += x & 0x1;
    x >>= 1;
    if (x) goto loop;
    return result;
}
```

编译结果（讲义 p21）：

```asm
    movl $0, %eax          # result = 0
.L2:
    movq %rdi, %rdx
    andl $1, %edx          # t = x & 0x1
    addq %rdx, %rax        # result += t
    shrq %rdi              # x >>= 1（逻辑右移，因为是无符号）
    jne  .L2               # if (x) goto loop
    rep; ret
```

注意 `jne` 直接复用 `shrq` 设置的条件码——`shrq` 的结果就是新的 x，若不为 0 则 ZF=0，`jne` 成立。这就是「算术指令隐式设条件码」的实用价值：**省掉一条 `test`**。

**while 的翻译 #1：jump-to-middle**（讲义 p23–p24），`-Og` 使用：

```c
    goto test;
loop:
    Body
test:
    if (Test) goto loop;
done:
```

**while 的翻译 #2：do-while 转换**（讲义 p25–p26），`-O1` 使用：

```c
    if (!Test) goto done;
loop:
    Body
    if (Test) goto loop;
done:
```

两者差别：前者在循环体之前先跳一次到测试；后者把测试「前置」一次作为守卫，循环末尾再测一次。后者少一次跳转，是优化后的形态。

**for 循环**（讲义 p27–p30）：先转成 while（`Init; while (Test) { Body; Update; }`），再转成 do-while。讲义 p30 指出「初始测试可以被优化掉」——因为 `i = 0` 且 `0 < WSIZE` 恒真，编译器直接删掉前置守卫。

### 5.6 switch 与跳转表

讲义 p32 的例子 `switch_eg(long x, long y, long z)` 包含四种典型情形：

| case | 特征 |
|---|---|
| 1 | 普通分支 |
| 2 | **fall through** 到 case 3 |
| 3 | 被 case 2 落入 |
| 5、6 | **多个标签共享同一代码块** |
| 4 | **缺失**（落入 default） |
| default | 兜底 |

**setup 部分**（讲义 p34–p35）：

```asm
switch_eg:
    movq %rdx, %rcx      # 把 z 挪到 %rcx（因为 %rdx 后面要用？实际是避免被覆盖）
    cmpq $6, %rdi        # 比较 x 与 6
    ja   .L8             # x > 6（无符号）→ default
    jmp  *.L4(,%rdi,8)   # 间接跳转：goto *(L4 + x*8)
```

**`ja` 的妙用**：`ja` 是**无符号**「大于」。因为 x 若是负数，转成无符号后是一个巨大的数，同样会被 `ja` 拦下。**一条指令同时挡住了「x > 6」和「x < 0」两种情况**——这是无符号比较的经典技巧，也是 L02「两副眼镜」的又一次应用。

**跳转表**（讲义 p35–p37）：

```asm
    .section .rodata
    .align 8
.L4:
    .quad .L8      # x = 0 → default
    .quad .L3      # x = 1 → case 1
    .quad .L5      # x = 2 → case 2
    .quad .L9      # x = 3 → case 3
    .quad .L8      # x = 4 → default（缺失的 case）
    .quad .L7      # x = 5 → case 5,6
    .quad .L7      # x = 6 → case 5,6
```

`.quad` 表示 8 字节（quad word）数据，每项存一个代码地址。表放在 `.rodata`（只读数据段）。

**各代码块**（讲义 p38–p41）：

```asm
.L3:                    # case 1: w = y*z
    movq  %rsi, %rax
    imulq %rdx, %rax
    ret

.L5:                    # case 2: w = y/z, 然后 fall through
    movq  %rsi, %rax
    cqto                # 把 %rax 符号扩展到 %rdx:%rax
    idivq %rcx          # 有符号除法
    jmp   .L6           # goto merge

.L9:                    # case 3: w = 1
    movl  $1, %eax
.L6:                    # merge: w += z
    addq  %rcx, %rax
    ret

.L7:                    # case 5, 6: w = 1 - z
    movl  $1, %eax
    subq  %rdx, %rax
    ret

.L8:                    # default: w = 2
    movl  $2, %eax
    ret
```

**fall-through 的实现**（讲义 p39–p40）：C 里 case 2 落入 case 3，等价于

```c
case 3: w = 1;          /* 先执行 case 3 自己的赋值 */
case 2: w = y/z;        /* 再执行 case 2 的 */
        goto merge;
merge:  w += z;
```

注意顺序被**颠倒**了：源码里 case 2 在前，但 goto 形式里 case 3 的初始化必须先执行（因为从 case 3 进入时要先 `w=1`），然后两者共用 `merge`。这是理解 fall-through 汇编的关键。

**`idivq` 的两个前置条件**：被除数在 `%rdx:%rax`（128 位），所以必须先 `cqto`（把 `%rax` 的符号位填满 `%rdx`）。忘了 `cqto` 会得到垃圾结果或除零异常。

### 5.7 在二进制中找跳转表

讲义 p42–p44 展示完整流程：

```
4005e9:  ff 24 fd f0 07 40 00   jmpq *0x4007f0(,%rdi,8)
```

机器码 `ff 24 fd` 后跟 4 字节位移 `f0 07 40 00`（小端）= `0x004007f0`。这就是表基址。

用 GDB 查看表内容：

```
(gdb) x /8xg 0x4007f0
0x4007f0:  0x0000000000400614  0x00000000004005f0
0x400800:  0x00000000004005f8  0x0000000000400602
0x400810:  0x0000000000400614  0x000000000040060b
0x400820:  0x000000000040060b  0x2c646c25203d2078
```

对照反汇编：

| 表项 | 值 | 对应标签 | case |
|---|---|---|---|
| [0] | 0x400614 | `.L8` | default |
| [1] | 0x4005f0 | `.L3` | 1 |
| [2] | 0x4005f8 | `.L5` | 2 |
| [3] | 0x400602 | `.L9` | 3 |
| [4] | 0x400614 | `.L8` | default（缺失） |
| [5] | 0x40060b | `.L7` | 5 |
| [6] | 0x40060b | `.L7` | 6 |

最后一项 `0x2c646c25203d2078` 已经不是地址了——它是紧邻表的字符串数据 `"x = %ld,\0"`（小端），说明表只有 7 项。

**这是 Bomb Lab 与 Attack Lab 的必备技能**：看到 `jmp *0x...(,%rXX,8)` 就知道要找表，用 `x/Nxg` dump 出来即可还原 `switch` 的全部映射。

**新版跳转表**（讲义 p45）：较新的编译器改用 4 字节**偏移量**而非 8 字节地址，目标地址 = `%rip + 表地址 + 偏移`。这样表小一半，且天然支持位置无关代码（PIC，见 L07）。

### 5.8 栈与 push/pop

讲义 p54–p59：

- 栈是内存的一段，用栈纪律管理。
- **向低地址生长**：压栈使 `%rsp` 减小。
- `%rsp` 始终指向栈顶（最低地址）。

**`pushq Src`** 的三步语义：

1. 取 `Src` 的值。
2. `%rsp = %rsp - 8`。
3. 把值写到 `(%rsp)`。

**`popq Dest`** 的三步语义：

1. 读 `(%rsp)` 的值。
2. `%rsp = %rsp + 8`。
3. 把值写到 `Dest`。

讲义 p59 特别强调：**`pop` 只是移动栈指针，内存里的旧值仍然存在**——这就是为什么未初始化变量可能「读到上一个函数留下的数据」，也是栈溢出攻击能工作的原因之一。

### 5.9 call 与 ret

**`call label`**（讲义 p62）：

1. 把**返回地址**（`call` 之后那条指令的地址）压栈。
2. 跳转到 `label`。

**`ret`**：

1. 从栈顶弹出地址。
2. 跳转到该地址。

讲义 p61 的例子：

```asm
0000000000400550 <mult2>:
  400550: mov  %rdi,%rax
  400553: imul %rsi,%rax
  400557: ret

0000000000400540 <multstore>:
  400540: push %rbx          # 保存 %rbx（被调用者保存寄存器）
  400541: mov  %rdx,%rbx     # dest 存到 %rbx，因为 %rdx 会被调用破坏
  400544: call 400550 <mult2>
  400549: mov  %rax,(%rbx)   # *dest = 返回值
  40054c: pop  %rbx          # 恢复 %rbx
  40054d: ret
```

**逐帧跟踪**（讲义 p63–p66，`%rsp` 初始为 0x120）：

| 时刻 | `%rsp` | `%rip` | 栈顶内容 |
|---|---|---|---|
| `call` 之前 | 0x120 | 0x400544 | — |
| `call` 执行后 | 0x118 | 0x400550 | 0x400549（返回地址） |
| `ret` 之前 | 0x118 | 0x400557 | 0x400549 |
| `ret` 执行后 | 0x120 | 0x400549 | （0x400549 仍在内存中） |

这张表把「传递控制」讲透了：**`call` 与 `ret` 唯一做的事就是压栈/弹栈一个地址**，其余全靠 `jmp`。

### 5.10 过程机制的三个方面

讲义 p48–p52 列出任何过程都需要解决的三个问题：

| 机制 | 内容 |
|---|---|
| **传递控制（passing control）** | 跳到过程入口；返回时回到调用点之后 |
| **传递数据（passing data）** | 参数传入；返回值传出 |
| **内存管理（memory management）** | 过程执行期间分配局部存储；返回时释放 |

讲义 p52 强调：机器指令只提供「机制」，具体「怎么用」由设计者约定，这些约定合起来就是 **ABI**。x86-64 的 ABI 规定（详见 L05）：

- 参数：`%rdi`、`%rsi`、`%rdx`、`%rcx`、`%r8`、`%r9`。
- 返回值：`%rax`。
- 被调用者保存：`%rbx`、`%rbp`、`%r12`–`%r15`。
- 调用者保存：其余。

`multstore` 里的 `push %rbx` / `pop %rbx` 正是「被调用者保存」规则的体现：`%rbx` 归被调用者管，`mult2` 可能改它，所以 `multstore` 必须先存后恢复。

## 6. 代码示例

### 6.1 官方课程代码

**pcount_do 与 pcount_goto**（讲义 p20–p21），出处 `90-原始PDF/15-213/lectures/04-machine-beta.pdf` 第 20–21 页，完整代码与汇编见 5.5 节。

**switch_eg**（讲义 p32–p41），出处同上 PDF 第 32–41 页。C 源码：

```c
long switch_eg(long x, long y, long z) {
    long w = 1;
    switch (x) {
    case 1:
        w = y*z;
        break;
    case 2:
        w = y/z;
        /* Fall Through */
    case 3:
        w += z;
        break;
    case 5:
    case 6:
        w -= z;
        break;
    default:
        w = 2;
    }
    return w;
}
```

汇编与跳转表见 5.6 节。

**mult2 / multstore**（讲义 p61），出处同上 PDF 第 61 页，见 5.9 节。

**GDB 查跳转表**（讲义 p43–p44），出处同上 PDF 第 43–44 页：

```
(gdb) x /8xg 0x4007f0
```

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：手工把 for 循环翻译成 goto 并验证**

```c
/* loop_goto.c —— 非官方示例，仅用于说明概念 */
long sum_to(long n) {
    long sum = 0;
    for (long i = 1; i <= n; i++)
        sum += i;
    return sum;
}

/* 等价的 goto 形式 */
long sum_to_goto(long n) {
    long sum = 0;
    long i = 1;
    if (i > n) goto done;
loop:
    sum += i;
    i++;
    if (i <= n) goto loop;
done:
    return sum;
}
```

编译 `gcc -Og -S` 后可以观察到：现代编译器会把 `sum_to` 优化成闭式公式 `n*(n+1)/2`（涉及 `imul` 与 `shr`），这是优化器比源码「更聪明」的典型例子。若想看到循环，请用 `-O0` 或加 `volatile`。

**示例 B：构造一个小型跳转表并用 GDB 读出**

```c
/* jumptab.c —— 非官方示例，仅用于说明概念 */
long classify(long x) {
    switch (x) {
    case 0: return 100;
    case 1: return 200;
    case 2: return 300;
    case 3: return 400;
    default: return -1;
    }
}
```

```asm
# gcc -O1 -S 后的典型输出
classify:
    cmpq  $3, %rdi
    ja    .L2                 # x > 3 或 x < 0 → default
    jmp   *.L4(,%rdi,8)       # 间接跳转
.L8:  movl $100, %eax
      ret
.L7:  movl $200, %eax
      ret
.L6:  movl $300, %eax
      ret
.L5:  movl $400, %eax
      ret
.L2:  movl $-1, %eax
      ret
```

GDB 操作：

```
(gdb) disassemble classify
(gdb) x /5xg &classify+0x0     # 先找到 jmp 指令里的位移，得到表地址
(gdb) x /5xg <表地址>
```

**示例 C：手工模拟 call/ret 的栈变化**

```asm
# 非官方示例，仅用于说明概念
# 假设进入 main 时 %rsp = 0x7fffffffe000
main:
    subq  $8, %rsp          # %rsp = 0x7fffffffdff8
    call  foo               # 压入返回地址 → %rsp = 0x7fffffffdff0
    addq  $8, %rsp          # %rsp = 0x7fffffffdff8
    ret                     # 弹出 → %rsp = 0x7fffffffe000
foo:
    movl  $42, %eax
    ret                     # 弹出返回地址 → %rsp = 0x7fffffffdff8
```

用 GDB 验证：

```
(gdb) break foo
(gdb) run
(gdb) x /2xg $rsp        # 栈顶就是返回地址
(gdb) info registers rsp rip
(gdb) finish             # 执行到 foo 返回
(gdb) info registers rsp rip
```

**示例 D：`ja` 同时挡住负数的验证**

```c
/* ja_demo.c —— 非官方示例，仅用于说明概念 */
int pick(long x) {
    switch (x) {
    case 0: return 10;
    case 1: return 11;
    case 2: return 12;
    default: return -1;
    }
}

int main(void) {
    printf("%d %d %d\n", pick(-1), pick(0), pick(99));
    return 0;
}
```

`pick(-1)` 会走 default：`-1` 的无符号值是 `0xFFFFFFFFFFFFFFFF`，`cmpq $2, %rdi` 之后 `ja` 判定为「above」，直接跳 default。若编译器误用 `jg`（有符号），`-1 > 2` 为假，就会跳进表里越界读取——这正是 `ja` 存在的安全意义。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| AT&T `mov %rax, %rbx` | Intel `mov rbx, rax` | 前者「rax→rbx」，后者「rax→rbx」，字面顺序相反 |
| `lea` | `mov` | 前者只算地址表达式，不访存；后者访存（若操作数是内存） |
| `jmp .L8`（直接） | `jmp *.L4(,%rdi,8)`（间接） | 前者目标写在指令里；后者目标从表中读取，带 `*` 前缀 |
| `ja` | `jg` | 前者无符号比较，同时挡负数与超上界；后者有符号 |
| jump-to-middle | do-while 转换 | 前者 `-Og`，先跳到测试；后者 `-O1`，前置守卫 + 尾部测试 |
| `pushq` | `subq $8, %rsp` + `movq` | 前者是后者的合体，但只占 1 字节 |
| `popq` 清除内存 | `popq` 只移动指针 | 内存中的旧值仍可读，这是信息泄漏与攻击的入口 |
| `call` 压入的地址 | `call` 的目标地址 | 压入的是**下一条指令**的地址（返回地址），不是目标 |
| 传递控制 | 传递数据 | 前者靠 `call`/`ret` + 栈；后者靠寄存器与栈（详见 L05） |
| ABI | ISA | ABI 是软件约定（参数放哪），ISA 是硬件规范（有哪些指令） |
| `idivq` 前的 `cqto` | 可省略 | 不可省略：被除数是 `%rdx:%rax` 128 位 |
| fall-through 的 goto 形式 | 源码顺序 | 汇编里 case 3 的初始化在 case 2 之前，顺序被颠倒 |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-213/lectures/04-machine-beta.pdf`
- **总页数**：66 页
- **重点页码**：
  - p1 标题（2026 年 9 月 3 日）；p2 公告（Bomb Lab 当晚发布）
  - p4–p5 机器指令的三层表示与 REX/ModR/M 编码
  - p6 AT&T vs Intel 语法对照表
  - p7–p8 寻址模式与 `lea` 不访存
  - p9 `lea` 的三个优势
  - p10–p15 哪些寄存器值是指针（含寻址模式推断规则）
  - p16 条件码与跳转回顾
  - p18–p22 do-while 与 goto 翻译
  - p23–p26 while 的两种翻译
  - p27–p30 for 循环的三步转换
  - p32–p41 switch_eg 全流程（含跳转表与各代码块）
  - p42–p44 在二进制中定位跳转表（GDB `x/8xg`）
  - p45 新版 4 字节偏移跳转表
  - p48–p52 过程机制的三个方面与 ABI
  - p54–p59 栈结构与 push/pop 语义
  - p61–p66 mult2/multstore 与 call/ret 逐帧跟踪
- **原始链接**：https://www.cs.cmu.edu/~213/lectures/04-machine-beta.pdf
- **教材对应**：CS:APP 3e §3.6（控制）与 §3.7（过程）的前半部分

> 待核实：讲义 p46 引用了 Canvas 小测链接（`canvas.cmu.edu/courses/55964/quizzes/169247`），非 CMU 用户无法访问。讲义 p2 提到「Bomb Lab 今晚发布」，具体日期以课程 schedule 为准。

## 9. 对应视频

**未找到官方公开录像。**

可参考的公开资源：

- 教材站点：https://csapp.cs.cmu.edu/ —— 第 3 章配套代码与 `switch` 示例。
- 课程日程：https://www.cs.cmu.edu/~213/schedule.html
- Bomb Lab 官方说明（https://csapp.cs.cmu.edu/3e/bomblab.pdf）—— 本讲的跳转表技能在 phase 3 与 phase 4 直接用到。
- 本课 recitation 材料 `_scout/text/15-213__recitations__gdbnotes-x86-64.pdf.txt`（对应 `90-原始PDF/15-213/recitations/gdbnotes-x86-64.pdf`）—— GDB 断点、`x` 命令、跳转表 dump 的完整速查。

## 10. 本节复习

- AT&T：`mov src, dest`，寄存器 `%`，立即数 `$`，内存 `disp(base,index,scale)`。
- `%rsp`、`%rip` 永远是指针；带 scale 的操作数是索引不是指针。
- `lea` 三优势：三操作数、一条算复杂式、不改条件码。
- 循环 = 往回跳的 goto；`if` = 往前跳的 goto。
- while 两种翻译：jump-to-middle（`-Og`）与 do-while 转换（`-O1`）。
- `switch` 用跳转表 + `ja` 边界检查 + `jmp *表(,%rdi,8)`。
- `ja` 是无符号比较，一条指令同时挡住负数与超上界。
- 跳转表在 `.rodata`，每项 8 字节（新版为 4 字节偏移）。
- 栈向低地址生长，`%rsp` 指向栈顶。
- `pushq` = `%rsp -= 8` 再写；`popq` = 读再 `%rsp += 8`（不擦内存）。
- `call` 压入返回地址并跳转；`ret` 弹出地址并跳转。
- 过程三机制：传递控制、传递数据、内存管理；约定即 ABI。
- `%rbx` 等是被调用者保存寄存器，用前必须 `push`、用后 `pop`。

## 11. 自我检查

**题 1**：把下面的 while 循环翻译成「jump-to-middle」形式的 goto 代码。

```c
long f(long n) {
    long s = 0;
    while (n > 0) { s += n; n--; }
    return s;
}
```

<details><summary>参考答案</summary>

```c
long f_goto(long n) {
    long s = 0;
    goto test;
loop:
    s += n;
    n--;
test:
    if (n > 0) goto loop;
    return s;
}
```

对应的汇编（`-Og` 典型形态）：

```asm
f:
    movl $0, %eax        # s = 0
    jmp  .L2
.L3:
    addq %rdi, %rax      # s += n
    subq $1, %rdi        # n--
.L2:
    testq %rdi, %rdi     # n == 0 ?
    jg   .L3             # n > 0 → 循环
    ret
```

注意 `jg` 是有符号比较（`n` 是 `long`）。

</details>

**题 2**：`switch_eg` 的 setup 中 `cmpq $6, %rdi` 后跟 `ja .L8`。如果改成 `jg .L8` 会出什么问题？举一个具体输入。

<details><summary>参考答案</summary>

`jg` 是有符号比较，只挡 `x > 6`，**不挡负数**。若 `x = -1`，`jg` 判定 `-1 > 6` 为假，于是继续执行 `jmp *.L4(,%rdi,8)`，用 `-1 * 8` 作偏移去表之前的地址取目标——**越界读取**，可能跳到任意代码，造成崩溃或安全漏洞。

用 `ja`（无符号）时，`-1` 被解释为 `0xFFFFFFFFFFFFFFFF`，`ja` 判定为「above 6」，正确跳 default。

具体输入：调用 `switch_eg(-1, 2, 3)`。

</details>

**题 3**：某程序 `%rsp = 0x7fffffffd000`，依次执行 `pushq %rbx`、`call f`（`f` 内又 `pushq %rbp`）。求这三步之后的 `%rsp`。

<details><summary>参考答案</summary>

- `pushq %rbx`：`%rsp = 0x7fffffffcff8`
- `call f`：压入返回地址，`%rsp = 0x7fffffffcff0`
- `f` 内 `pushq %rbp`：`%rsp = 0x7fffffffcfe8`

此时栈从高到低依次是：`%rbx` 的旧值、返回地址、`%rbp` 的旧值。

</details>

**题 4**：跳转表在 `0x4007f0`，每项 8 字节，`x = 3`。间接跳转 `jmp *0x4007f0(,%rdi,8)` 会从哪个地址取目标？若该处内容为 `0x0000000000400602`，则跳到哪里？

<details><summary>参考答案</summary>

取目标的地址 = `0x4007f0 + 3 × 8 = 0x4007f0 + 0x18 = 0x400808`。

该地址存放 `0x0000000000400602`（小端字节序为 `02 06 40 00 00 00 00 00`），因此跳转到 **`0x400602`**。

在讲义 p43 的 dump 中，`0x400800` 行是 `0x4005f8  0x400602`，第二项即 `0x400808`，对应 `.L9`（case 3），与 `x = 3` 一致。

</details>

**题 5**：为什么 `multstore` 要把 `dest` 从 `%rdx` 挪到 `%rbx`，而不是留在 `%rdx`？

<details><summary>参考答案</summary>

因为 `%rdx` 是**调用者保存（caller-saved）**寄存器：`call mult2` 之后，`mult2` 有权随意改写 `%rdx`，`multstore` 不能假设它还在。而 `%rbx` 是**被调用者保存（callee-saved）**寄存器，`mult2` 若要使用必须先保存、返回前恢复，因此 `multstore` 可以安全地把 `dest` 放在 `%rbx` 里跨过这次调用。

代价是 `multstore` 自己也要遵守规则：它改动了 `%rbx`，所以开头 `push %rbx`、结尾 `pop %rbx`。

</details>

## 12. 进一步学习

- 上一讲：[[15-213-03-Machine-Programming-I-Basics|CMU 15-213 - L03 Machine Programming I Basics]]
- 下一讲：[[15-213-05-Machine-Programming-III-Procedures|CMU 15-213 - L05 Machine Programming III Procedures]] —— 展开参数传递的六个寄存器与栈帧布局。
- 课程导航：[[20-CMU-15-213/00-课程总览|CMU 15-213 - 课程总览]]、[[20-CMU-15-213/01-课程目录|CMU 15-213 - 课程目录]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- CS:APP 3e §3.6.5–§3.6.8（`switch` 与跳转表）、§3.7.1–§3.7.3（栈帧与传递控制）。
- Bomb Lab 的 phase 3（`switch`）与 phase 4（递归）直接检验本讲内容。
- 课程日程：https://www.cs.cmu.edu/~213/schedule.html
