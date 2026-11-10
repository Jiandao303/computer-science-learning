---
course: CMU 15-122
course_name: Imperative Computation
semester: Fall 2026
lecture_id: L19
topic: Types in C
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-122
  - 标准C
  - 类型系统
  - 整数转换
  - union
---

# 第 19 讲：C 中的类型（Types in C）

## 1. 本节学习目标

学完本讲后，你应该能够：

1. 列出 C 的整数类型族与它们的位宽关系，并用 `<stdint.h>` 的定宽类型（`int8_t`…`int64_t`、`uint32_t`、`size_t`）写出可移植代码。
2. 说出 `size_t` 的定义与用途，解释为什么「数组长度、`sizeof` 结果、`strlen` 返回值」都用它。
3. 复述本讲新增的四类 Undefined Behavior（除零、移位量为负或过大、左移负数、**有符号溢出**），并说明为什么 C0 的有符号溢出是「定义良好的模运算」而 C 的不是。
4. 应用 C 的整数转换规则：能表示则保值；无符号目标截断取低位；无符号更宽时符号扩展；有符号装不下时 implementation-defined。
5. 手工计算 `(short)x`、`(unsigned int)x`、`(unsigned short)x`、`(signed char)x` 等转换的十六进制结果。
6. 说明浮点数的两个经典陷阱（`0.1` 累加不等于 `5.0`、`10E20/10E10*10E10` 不等于 `10E20`），并解释 IEEE 754 的表示误差来源。
7. 用 `enum` + `union` + `struct` 实现 tagged union（带标签的联合体），并说明为什么 `switch` 的每个分支都要 `break`。

## 2. 前置知识

- 前序讲次：[[15-122-18-C-Memory-Model]]（指针算术、UB 的概念）、[[15-122-02-Ints]]（补码与模运算的 C0 版本，本讲是它的 C 版本并指出关键差异）。课程入口见 [[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]] 与 [[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 需要知道二进制、十六进制、补码的基本换算。
- 需要知道 32 位 `int` 的表示范围 −2³¹ 到 2³¹−1。
- 术语统一以 [[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]] 为准。

> **语言提醒**：本讲是**标准 C**。C0 与 C 在整数语义上有一个**关键差异**：C0 的有符号溢出按模 2³² 定义（结果确定），C 的有符号溢出是 undefined behavior（结果不确定）。这一条差异会让很多在 C0 下「能跑」的代码在 C 下出错。

## 3. 核心概念

**Implementation-defined（实现定义）**：标准允许各编译器自行决定，但**必须文档化**。与 UB 的区别是：implementation-defined 有确定结果，只是不同编译器可能不同；UB 则是「什么都可能」。

**Two's Complement（补码）**：n 位补码表示 −2^(n−1) 到 2^(n−1)−1，最高位是符号位。C99 允许其他表示（反码、原码），但现代平台全是补码。

**`size_t`**：`sizeof` 运算符的返回类型，无符号整数，64 位平台上 8 字节。定义在 `<stddef.h>`（通常被 `<stdlib.h>` 间接包含）。

**Fixed-width Integer（定宽整数）**：`<stdint.h>` 提供的 `int8_t`、`int16_t`、`int32_t`、`int64_t` 及对应的 `uintN_t`，保证精确位宽。

**Integer Promotion（整型提升）**：小于 `int` 的类型（`char`、`short`、`bool`）在参与算术运算前会先提升为 `int`。这是 C 里许多「意外结果」的根源。

**Union（联合体）**：所有成员共享同一块内存的类型。大小等于最大成员的大小。同一时刻只有一个成员有效。

**Enum（枚举）**：具名整数常量的集合。C 的 `enum` 本质上就是 `int`。

**Tagged Union（带标签的联合体）**：`struct` 里放一个 `enum` 标签和一个 `union` 内容，用来安全地表示「多种可能形状之一」。

## 4. 通俗理解

**类型是「怎么解释这堆比特」的说明书。**

同一串 32 个比特 `11111111111111111111111111111111`：

- 当 `int` 看：−1
- 当 `unsigned int` 看：4294967295
- 当 `float` 看：NaN

**转换（cast）不是「改变比特」，而是「换一本说明书」。** `(unsigned int)x` 不修改 `x` 的比特，只是让编译器用「无符号」的方式去读它。

**`union` 就像一间只能住一户的房子，但户型可以换**：你可以按「一个 `int`」的户型住，也可以按「四个 `char`」的户型住，但房子总面积固定，且同一时刻只有一种解读是有效的。

**`enum` + `union` 的组合**就是「快递盒 + 面单」：盒子里装什么由面单（`enum`）说明，你按面单去拆（`switch`），拆错格式就出事。

## 5. 原理与推导

### 5.1 整数类型族

C 的整数类型按位宽从小到大：

| 类型 | 典型位宽 | 范围（补码） | `<stdint.h>` 对应 |
|---|---|---|---|
| `signed char` | 8 | −128 … 127 | `int8_t` |
| `unsigned char` | 8 | 0 … 255 | `uint8_t` |
| `short` | 16 | −32768 … 32767 | `int16_t` |
| `unsigned short` | 16 | 0 … 65535 | `uint16_t` |
| `int` | 32 | −2147483648 … 2147483647 | `int32_t` |
| `unsigned int` | 32 | 0 … 4294967295 | `uint32_t` |
| `long` | 64（Linux）/ 32（Windows） | — | `int64_t`（Linux） |
| `long long` | 64 | — | `int64_t` |
| `size_t` | 64（64 位平台） | 0 … 2⁶⁴−1 | `uint64_t` |

**注意 `long` 的位宽依赖平台**：Linux 64 位是 8 字节，Windows 64 位是 4 字节。这是 C 可移植性最臭名昭著的问题之一。**要精确位宽就用 `<stdint.h>`，不要用 `long`。**

`<limits.h>` 提供这些类型的极值宏：`INT_MAX`、`INT_MIN`、`CHAR_BIT`、`SHRT_MAX`、`LONG_MAX` 等。

**`size_t` 的特殊地位**：它是「能表示任何对象大小」的无符号类型。所以

```c
size_t n = sizeof(int);           /* 4 */
size_t len = strlen("hello");     /* 5 */
```

用它做数组下标是**正确的**，用 `int` 做下标是**常见的 bug 来源**：

```c
int n = strlen(s);                /* 若 s 极长，int 可能溢出 */
for (int i = 0; i < strlen(s); i++)   /* 每次循环都重算 strlen，O(n²) */
```

第二个问题更隐蔽：`strlen` 是 O(n)，放在循环条件里让整个循环变成 O(n²)。正确写法是 `for (size_t i = 0, n = strlen(s); i < n; i++)`。

### 5.2 本讲新增的四类 UB

讲义第 2 页列出：

| UB | 例子 | 为什么是 UB |
|---|---|---|
| **除零** | `int x = 5 / 0;` | 数学上无定义；硬件可能抛异常，也可能不 |
| **移位量为负或 ≥ 位宽** | `x << 32`、`x << -1` | 标准只定义了 0 ≤ 移位量 < 位宽 的情形 |
| **左移负数** | `(-1) << 3` | 结果可能溢出符号位 |
| **有符号溢出** | `INT_MAX + 1` | 标准未规定；C0 则规定为模 2³² |

**最重要的一条是有符号溢出**。回忆 C0（第 2 讲）：C0 的 `int` 溢出**定义为**模 2³² 的运算，所以 `INT_MAX + 1 == INT_MIN` 是**保证**的。C 里不是——`INT_MAX + 1` 是 UB，编译器可以做任何事（包括第 18 讲第 4 题演示的「删掉溢出检测分支」）。

**两种对策**：

```c
/* 对策一：用无符号类型（无符号溢出是定义良好的模运算） */
unsigned int u = UINT_MAX;
u = u + 1;                 /* 保证等于 0 */

/* 对策二：让 gcc 用 C0 的语义 */
/* gcc -fwrapv ... */      /* 强制有符号溢出按补码回绕 */
```

`-fwrapv` 是一个「退让」选项：它让编译器放弃某些依赖「无溢出」假设的优化，换取可预测的行为。工程上，如果代码里大量依赖溢出回绕（例如哈希函数、加密算法），必须开这个选项或改用无符号类型。

### 5.3 整数转换规则

C 的转换规则可以整理成四种情形（`19-cnum.pdf` 第 4–6 页）：

**情形 1：目标类型能表示原值 → 值不变。**

```c
int x = 100;
long y = x;              /* 100，值不变 */
```

**情形 2：目标是无符号，且比源窄或同宽 → 保留最低有效位（模 2^n）。**

```c
int x = INT_MAX;                  /* 0x7FFFFFFF */
unsigned char c = (unsigned char)x;   /* 0xFF = 255 */
```

推导：`INT_MAX` = 0x7FFFFFFF，取最低 8 位 = 0xFF = 255。

**情形 3：目标是无符号，且比源宽 → 先符号扩展，再按无符号解释。**

```c
signed char s = -3;                     /* 0xFD */
unsigned int u = (unsigned int)s;       /* 0xFFFFFFFD = 4294967293 */
```

推导：`-3` 的 8 位补码是 0xFD。扩展到 32 位时**符号扩展**（高位补 1）得 0xFFFFFFFD。按无符号读 = 4294967293。

注意：如果源类型是 `unsigned char`，则**零扩展**而非符号扩展：

```c
unsigned char uc = 253;                 /* 0xFD */
unsigned int u2 = (unsigned int)uc;     /* 0x000000FD = 253 */
```

**这一条是 C 里最容易出错的地方**：`char` 是否有符号由实现决定（x86 上通常有符号）。所以 `(unsigned int)(char)253` 与 `(unsigned int)(unsigned char)253` 结果完全不同。

**情形 4：目标是有符号，且装不下 → implementation-defined（通常就是按位重解释）。**

```c
signed char c = (signed char)INT_MAX;   /* 0xFF = -1 */
```

推导：`INT_MAX` = 0x7FFFFFFF，取低 8 位 = 0xFF。按 8 位补码读 0xFF = −1。

标准说这是 implementation-defined，GCC 文档明确说明「按补码截断」。所以实际可预测，但**严格来说不可移植**。

**整型提升的陷阱**：

```c
unsigned short a = 65535;
unsigned short b = 1;
if (a + b > 0) ...        /* 这里 a+b 是 int 类型的 65536，不是 unsigned short 的 0 */
```

因为 `unsigned short` 在运算前被提升为 `int`（`int` 能表示 `unsigned short` 的全部值），所以 `a + b` = 65536，比较结果为真。如果期望「16 位回绕」，必须显式截断：`(unsigned short)(a + b)`。

### 5.4 完整的手算示例：`int x = -15122`

这是讲义习题 Ex2 的核心。`-15122` 的 32 位补码：

```
15122 = 0x3B12
-15122 = ~0x3B12 + 1 = 0xFFFFC4ED + 1 = 0xFFFFC4EE
```

验证：`0xFFFFC4EE` 的低 16 位是 0xC4EE = 50414；作为 16 位补码，50414 − 65536 = −15122 ✓。

四种转换：

| 转换 | 结果（十六进制） | 十进制 | 依据 |
|---|---|---|---|
| `(short)x` | 0xC4EE | −15122 | 取低 16 位，按 16 位补码读（值恰好装得下，保值） |
| `(unsigned int)x` | 0xFFFFC4EE | 4294952174 | 同宽，按无符号读 |
| `(unsigned short)x` | 0xC4EE | 50414 | 取低 16 位，按无符号读 |
| `(signed char)x` | 0xEE | −18 | 取低 8 位 0xEE = 238，按 8 位补码读 = 238 − 256 = −18 |
| `(short)(signed char)x` | 0xFFEE | −18 | 0xEE 符号扩展到 16 位 = 0xFFEE = −18 |

**最后一个转换值得注意**：先截到 8 位（−18），再扩展到 16 位（仍是 −18）。如果直接 `(short)x` 会得到 −15122。**转换的顺序影响结果**，因为每一步都可能丢信息。

### 5.5 浮点数：IEEE 754 与两个经典陷阱

C 的 `float` 是 32 位 IEEE 754（1 位符号 + 8 位指数 + 23 位尾数），`double` 是 64 位（1 + 11 + 52）。

**根本问题**：二进制无法精确表示大多数十进制小数。`0.1` 的二进制是无限循环小数 `0.0001100110011...`，只能截断存储。

**陷阱一：累加不等于目标值**

```c
for (float res = 0.0; res != 5.0; res += 0.1) {
  /* ... */
}
```

这个循环**永不终止**。因为 `0.1` 的实际存储值略大于或小于 0.1，累加 50 次后得到的不是精确的 5.0，而是 5.0000001 或 4.9999995 之类。`res != 5.0` 永远为真。

正确写法：

```c
for (int i = 0; i < 50; i++) {
  float res = i * 0.1f;
  /* ... */
}
```

或者用容差比较：`if (fabs(res - 5.0) < 1e-6)`。

**陷阱二：乘除不互逆**

```c
printf("%f\n", 10E20 / 10E10 * 10E10);
```

输出 `999999949672133165056.000000`，而不是 `1e21`。

原因：`10E20` 作为 `double` 存储时已经有舍入误差（它的精确值不是 10²¹）。除以 10E10 再乘 10E10，误差被放大而非抵消。**浮点运算不满足结合律与分配律**：

```
(a / b) * b  ≠  a        （一般情况下）
(a + b) + c  ≠  a + (b + c)
```

**工程建议**：

1. 涉及金额、精确计数时**不要用浮点**，用整数（以「分」为单位）或定点数。
2. 比较浮点用容差，不要用 `==`。
3. 求和的顺序会影响结果，大数小数混合时先加小数。

### 5.6 `enum` 与 `union`

**`enum`（第 9–11 页）**：

```c
enum nodetype { INNER, LEAF, EMPTY };
```

- `INNER` = 0、`LEAF` = 1、`EMPTY` = 2（默认从 0 开始递增）。
- 可以显式赋值：`enum color { RED = 1, GREEN = 2, BLUE = 4 };`
- **C 的 `enum` 就是 `int`**：不做类型检查，`enum nodetype t = 99;` 编译通过（虽然语义错误）。

这与 Java/C# 的 `enum` 完全不同——后两者是真正的类型。C 的 `enum` 只是「给整数起名字」的语法糖。

**`union`（第 9–11 页）**：

```c
union nodecontent {
  int data;
  struct innernode node;
};
```

- 所有成员**共享同一块内存**，大小 = 最大成员的大小。
- 同一时刻只有一个成员有效。写入 `data` 后读 `node` 是 UB（严格来说是 implementation-defined 的位重解释）。
- 用途：**节省内存**。当「多种可能形状互斥」时，`union` 只占最大那个的空间。

**Tagged union（带标签的联合体）**：

```c
struct ltree {
  enum nodetype type;        /* 标签：现在哪个成员有效 */
  union nodecontent content; /* 内容 */
};
```

这是 C 里实现「多态数据结构」的标准手法。使用模式：

```c
switch (T->type) {
  case LEAF:
    return T->content.data;
  case INNER:
    return sum(T->content.node.left) + sum(T->content.node.right);
  case EMPTY:
    return 0;
  default:
    /* 不应到达 */
    return -1;
}
```

**为什么每个分支都要 `break`？** C 的 `switch` 默认**贯穿（fall through）**：匹配到一个 `case` 后，会继续执行后面所有 `case` 的代码，直到遇到 `break` 或 `switch` 结束。忘记 `break` 会让 `LEAF` 分支执行完接着执行 `INNER` 分支的代码——这是 C 里最常见的 bug 之一。

讲义第 11 页的说法是「除最后一支外都要 break」。严格说，**最后一个分支之后 `switch` 就结束了，`break` 可以省**，但加上更安全（以后添加新分支时不会忘）。

现代编译器能对「忘记 break」给出警告（`-Wimplicit-fallthrough`），但需要显式开启。

### 5.7 为什么 `union` 比「多个字段」省内存

假设一个树节点可能是「叶子（一个 `int`）」或「内部节点（两个指针）」。不用 `union`：

```c
struct bad_node {
  enum nodetype type;
  int data;              /* 4 字节（内部节点时浪费） */
  struct node* left;     /* 8 字节（叶子时浪费） */
  struct node* right;    /* 8 字节（叶子时浪费） */
};
/* 总大小：4 + 4 + 8 + 8 = 24 字节（含对齐） */
```

用 `union`：

```c
union nodecontent {
  int data;                    /* 4 字节 */
  struct { struct node* left; struct node* right; } inner;  /* 16 字节 */
};
struct good_node {
  enum nodetype type;          /* 4 字节 */
  union nodecontent content;   /* 16 字节（最大成员） */
};
/* 总大小：4 + 4(填充) + 16 = 24 字节 */
```

在这个例子里两者相同，因为 `union` 被最大的成员撑到 16 字节，加上标签与对齐还是 24。但若内部节点只有**一个**指针（例如单链表 vs 整数），`union` 就能省下 4 字节。**`union` 的收益取决于「最大成员」与「其他成员」的大小差距。**

真正的收益在**缓存友好性**上：`union` 保证所有变体占用相同空间，数组元素大小一致，访问模式可预测。

### 5.8 习题要点

- **Ex1（第 12 页，解在第 14 页）**：判断若干表达式是否 UB。要点是区分「UB」「implementation-defined」「定义良好」三类。
- **Ex2（第 12–13 页，解在第 14 页）**：`int x = -15122` 的四种转换，见 5.4 节的完整表格。
- **Ex3（第 13 页，解在第 14 页）**：判断哪些转换是 implementation-defined。答案：**只有 `(char)x` 是**——因为 `char` 是否有符号由实现决定。其余转换（到 `short`、`unsigned int`、`unsigned short`）都由标准明确规定。

## 6. 代码示例

### 6.1 官方课程代码

以下代码出自 `19-cnum.pdf`，页码为该 PDF 的页码。

**（1）数字类型与位宽**（第 2–3 页）

整数类型族、`<limits.h>` 的极值宏、`<stdint.h>` 的定宽类型对照表（`signed char`↔`int8_t`、`short`↔`int16_t`、`int`↔`int32_t`、`long`↔`int64_t`）。

**（2）本讲新增的 UB**（第 2 页）

除零、移位量为负或过大、左移负数、有符号溢出。对策：`unsigned int` 或 `gcc -fwrapv`。

**（3）`size_t`**（第 3 页）

`sizeof` 的返回类型，8 字节无符号。

**（4）Implementation-defined 清单**（第 3–4 页）

`char` 是否有符号、`long` 的位宽、有符号右移的行为等。

**（5）数值转换规则**（第 4–6 页）

四种情形与具体例子，包括 `(unsigned char)INT_MAX == 255`、`(unsigned int)(signed char)-3 == 4294967293`、`(signed char)INT_MAX == -1`。

**（6）陷阱示例**（第 6 页）

`int64_t i = 1 << 40;` —— `1` 是 `int`（32 位），`1 << 40` 的移位量 ≥ 位宽，是 UB。正确写法是 `int64_t i = (int64_t)1 << 40;` 或 `1LL << 40`。

**（7）浮点数**（第 7–8 页）

`10E20/10E10*10E10` 输出 `999999949672133165056.000000`；`for (float res=0.0; res!=5.0; res+=0.1)` 永不终止。

**（8）`enum` 与 `union`**（第 9–11 页）

`enum nodetype { INNER, LEAF, EMPTY };`、`union nodecontent { int data; struct innernode node; };`、`struct ltree { enum nodetype type; union nodecontent content; };`、`switch` 的 `break` 规则。

**（9）习题与答案**（第 12–13 页题目，第 14 页答案）

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念

**示例一：一个可移植的「打印位模式」函数。**

```c
#include <stdio.h>
#include <stdint.h>

void print_bits(uint32_t x) {
  for (int i = 31; i >= 0; i--) {
    printf("%u", (x >> i) & 1u);
    if (i % 8 == 0 && i != 0) printf(" ");
  }
  printf("\n");
}

int main(void) {
  int32_t x = -15122;
  printf("as int32_t:   %d\n", x);
  print_bits((uint32_t)x);          /* 11111111 11111111 11000100 11101110 */
  printf("as uint32_t:  %u\n", (uint32_t)x);
  printf("(short)x:     %d\n", (short)x);
  printf("(uint16_t)x:  %u\n", (uint16_t)x);
  printf("(int8_t)x:    %d\n", (int8_t)x);
  return 0;
}
```

输出：

```
as int32_t:   -15122
11111111 11111111 11000100 11101110
as uint32_t:  4294952174
(short)x:     -15122
(uint16_t)x:  50414
(int8_t)x:    -18
```

用 `uint32_t` 打印位模式而不是 `int`，是因为**对无符号类型做右移是逻辑移位**（高位补 0），对有符号类型做右移是算术移位（高位补符号位）——后者是 implementation-defined，可能让位模式打印出错。**这条规则本身就是一个重要的可移植性细节。**

**示例二：用 `-fwrapv` 观察有符号溢出的行为差异。**

```c
#include <stdio.h>
#include <limits.h>

int main(void) {
  int x = INT_MAX;
  int y = x + 1;                   /* UB（无 -fwrapv 时） */
  printf("y = %d\n", y);           /* -fwrapv 下保证 INT_MIN */
  printf("y < x ? %s\n", y < x ? "yes" : "no");
  return 0;
}
```

- `gcc -O0`：输出 `y = -2147483648`、`y < x ? yes`（因为不优化，真的做了加法）。
- `gcc -O2`：可能输出 `y = -2147483648`、`y < x ? no`（编译器假定无溢出，判定 `y < x` 为假）。
- `gcc -O2 -fwrapv`：输出 `y = -2147483648`、`y < x ? yes`（回绕语义被保证）。

**同一个程序，三种结果。** 这就是为什么「UB 不是崩溃」这句话要反复强调。

**示例三：用 tagged union 实现一个「整数或字符串」的值。**

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "lib/xalloc.h"

typedef enum { VAL_INT, VAL_STR } valkind;

typedef struct value {
  valkind kind;
  union {
    int i;
    char *s;          /* 拥有所有权 */
  } u;
} value;

value *mk_int(int i) {
  value *v = xmalloc(sizeof(value));
  v->kind  = VAL_INT;
  v->u.i   = i;
  return v;
}

value *mk_str(const char *s) {
  value *v = xmalloc(sizeof(value));
  v->kind  = VAL_STR;
  v->u.s   = xmalloc(strlen(s) + 1);
  strcpy(v->u.s, s);
  return v;                       /* 归属权：value 拥有 u.s */
}

void value_free(value *v) {
  if (v == NULL) return;
  if (v->kind == VAL_STR) free(v->u.s);   /* 只有 STR 才需要释放内层 */
  free(v);
}

void value_print(value *v) {
  switch (v->kind) {
    case VAL_INT:
      printf("%d\n", v->u.i);
      break;                      /* 不能省！ */
    case VAL_STR:
      printf("\"%s\"\n", v->u.s);
      break;
    default:
      printf("<unknown>\n");
      break;
  }
}
```

三个要点：

1. **`value_free` 必须按 `kind` 分支释放**。如果对 `VAL_INT` 也 `free(v->u.s)`，会把一个整数值当指针 free，UB。
2. **`switch` 的 `break` 不能省**。省略后 `VAL_INT` 分支会贯穿到 `VAL_STR`，把整数当 `char*` 打印，可能段错误。
3. **`default` 分支不该省**。虽然 `kind` 只有两个合法值，但内存损坏或未初始化可能让它变成别的值；`default` 提供一道兜底。

**示例四：浮点误差的可视化。**

```c
#include <stdio.h>

int main(void) {
  double sum = 0.0;
  for (int i = 0; i < 10; i++) sum += 0.1;
  printf("sum = %.20f\n", sum);
  printf("sum == 1.0 ? %s\n", sum == 1.0 ? "yes" : "no");
  printf("fabs(sum-1.0) = %.3e\n", sum > 1.0 ? sum - 1.0 : 1.0 - sum);
  return 0;
}
```

输出（典型）：

```
sum = 0.99999999999999988898
sum == 1.0 ? no
fabs(sum-1.0) = 1.110e-16
```

`0.1` 的 `double` 表示略小于 0.1，累加 10 次后与 1.0 相差约 1.1×10⁻¹⁶。**这个误差在大多数应用里可以忽略，但 `sum == 1.0` 会返回假**——这就是为什么浮点比较必须用容差。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键区别 | 记忆点 |
|---|---|---|---|
| Undefined Behavior（UB） | Implementation-defined（实现定义） | 前者「什么都可能」；后者「有确定结果，各编译器可能不同但必须文档化」 | UB 更危险 |
| C0 的有符号溢出 | C 的有符号溢出 | 前者定义为模 2³² 运算；后者是 UB | **本讲最关键差异** |
| `int` 溢出 | `unsigned int` 溢出 | 前者 UB；后者定义良好（模 2³²） | 要回绕就用无符号 |
| `char` | `signed char` / `unsigned char` | `char` 是否有符号**由实现决定**；后两者明确 | 要确定就用后两者 |
| `long` | `int64_t` | 前者位宽随平台变（Linux 8、Windows 4）；后者固定 8 字节 | 要可移植用 `<stdint.h>` |
| 整型提升 | 显式转换 | 前者是运算前自动发生（`char`→`int`）；后者是 `(type)x` 显式指定 | 提升常导致意外 |
| `union` | `struct` | 前者成员共享内存（同一时刻一个有效）；后者成员各占空间 | 「共享 vs 并列」 |
| C 的 `enum` | Java 的 `enum` | 前者就是 `int`，不做类型检查；后者是真正的类型 | C 的 `enum` 只是命名常量 |
| `switch` 有 `break` | 无 `break` | 后者**贯穿**到下一个 `case`，是 C 的默认行为 | 「忘了 break 是经典 bug」 |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-122/lectures/19-cnum.pdf`
- **总页数**：14 页
- **本节重点页码**（PDF 页码，即提取文本中 `=== [page N] ===` 的 N）：
  - 第 2 页：整数类型族、本讲新增的四类 UB
  - 第 2–3 页：`<stdint.h>` 定宽类型对照表
  - 第 3 页：`size_t` 的定义与用途
  - 第 3–4 页：Implementation-defined 清单（`char` 的符号性、`long` 的位宽）
  - 第 4–6 页：数值转换的四种情形与具体例子
  - 第 6 页：`1 << 40` 的 UB 陷阱
  - 第 7–8 页：浮点数的两个经典陷阱
  - 第 9–11 页：`enum`、`union`、tagged union、`switch` 的 `break`
  - 第 12–13 页：习题 Ex1–Ex3
  - 第 14 页：参考答案（Ex2 的四种转换）
- **原始网页链接**：`https://www.cs.cmu.edu/~15122-archive/f26/handouts/lectures/19-cnum.pdf`
- **配套代码包**：`90-原始PDF/15-122/code/19-cnum.tgz`

## 9. 对应视频

未找到官方公开录像。本讲建议配合 6.2 节的示例一，亲手打印几个数的位模式——把「转换就是换说明书」这个抽象说法变成看得见的比特。

## 10. 本节复习

1. 整数类型：`char`/`short`/`int`/`long`/`long long` 及无符号版本。要精确位宽用 `<stdint.h>`；`long` 的位宽随平台变。
2. `size_t` 是 `sizeof` 的返回类型，8 字节无符号，用于数组长度与下标。
3. 本讲新增四类 UB：除零、移位量为负或过大、左移负数、**有符号溢出**。C0 的有符号溢出是定义良好的模运算，C 的不是——这是关键差异。对策：`unsigned` 或 `-fwrapv`。
4. 转换四情形：能表示则保值；无符号窄/同宽取低位；无符号更宽做符号扩展；有符号装不下是 implementation-defined。
5. `-15122` = 0xFFFFC4EE；`(short)` → 0xC4EE（−15122）、`(unsigned int)` → 0xFFFFC4EE（4294952174）、`(unsigned short)` → 0xC4EE（50414）、`(signed char)` → 0xEE（−18）。
6. 浮点：`0.1` 无法精确表示；`res != 5.0` 的循环永不终止；`(a/b)*b ≠ a`；比较必须用容差；金额用整数。
7. `enum` 就是 `int`；`union` 成员共享内存；tagged union = `enum` 标签 + `union` 内容；`switch` 默认贯穿，`break` 不能省。

## 11. 自我检查

**题 1.** 写出 `int x = -15122;` 的 32 位十六进制表示，并计算下列各式的值（十进制）：
（a）`(short)x` （b）`(unsigned int)x` （c）`(unsigned short)x` （d）`(signed char)x`

**题 2.** 下面哪些表达式是 UB？哪些是 implementation-defined？哪些是定义良好的？

```c
int a = 5 / 0;                    /* (A) */
int b = 1 << 40;                  /* (B) */
int c = (-1) << 3;                /* (C) */
int d = INT_MAX + 1;              /* (D) */
unsigned int e = UINT_MAX + 1;    /* (E) */
char f = (char)300;               /* (F) */
int g = (int)3.9;                 /* (G) */
```

**题 3.** 为什么 `for (float res = 0.0; res != 5.0; res += 0.1)` 永不终止？请给出两种修正方案，并说明各自的适用场景。

**题 4.** 解释 `struct { enum t type; union { int i; char *s; } u; }` 相比 `struct { enum t type; int i; char *s; }` 的优势与风险。

**题 5.** 下面这段代码在什么情况下会出错？请指出并修正。

```c
unsigned short a = 65535;
unsigned short b = 1;
unsigned short c = a + b;
if (c == 0) printf("wrapped\n");
else printf("c = %u\n", c);
```

<details>
<summary>参考答案</summary>

**答 1.** `-15122` 的 32 位补码：

```
15122  = 0x3B12
~0x3B12 = 0xFFFFC4ED
+1      = 0xFFFFC4EE
```

所以 `x` = **0xFFFFC4EE**。

- （a）`(short)x`：取低 16 位 0xC4EE。按 16 位补码读：0xC4EE = 50414，50414 − 65536 = **−15122**。（值恰好装得下，保值。）
- （b）`(unsigned int)x`：同宽，按无符号读 0xFFFFC4EE = **4294952174**。
- （c）`(unsigned short)x`：取低 16 位 0xC4EE，按无符号读 = **50414**。
- （d）`(signed char)x`：取低 8 位 0xEE = 238，按 8 位补码读 = 238 − 256 = **−18**。

（补充：`(short)(signed char)x` = 0xFFEE = −18，即先截到 8 位再符号扩展到 16 位。与直接 `(short)x` 的 −15122 不同——**转换顺序影响结果**。）

**答 2.**
- **（A）`5 / 0`：UB**。除零是 UB。
- **（B）`1 << 40`：UB**。`1` 是 `int`（32 位），移位量 40 ≥ 32，是 UB。正确写法 `(int64_t)1 << 40` 或 `1LL << 40`。
- **（C）`(-1) << 3`：UB**。左移负数是 UB。
- **（D）`INT_MAX + 1`：UB**。有符号溢出。
- **（E）`UINT_MAX + 1`：定义良好**。无符号溢出是模 2³² 运算，结果保证为 0。
- **（F）`(char)300`：implementation-defined**。300 = 0x12C，取低 8 位 0x2C = 44。但若 `char` 有符号且值 ≥ 128 时结果依赖实现。这里 44 < 128，实际不触发歧义，但**类型层面的规则是 implementation-defined**（因为 `char` 的符号性由实现决定）。
- **（G）`(int)3.9`：定义良好**。浮点转整数向零截断，结果 3。注意：若浮点值超出 `int` 范围（如 `(int)1e20`），则是 UB。

**答 3.**
**原因**：`0.1` 在二进制中是无限循环小数，`float` 只能存近似值（略大或略小于 0.1）。累加 50 次后，结果不是精确的 `5.0`，而是 `5.0000001` 或 `4.9999995` 之类。`res != 5.0` 的比较因此永远为真。

**修正方案一：用整数计数**

```c
for (int i = 0; i < 50; i++) {
  float res = i * 0.1f;
  /* ... */
}
```

适用场景：**循环次数已知且是整数**。这是最推荐的方案——把「浮点累加」换成「整数计数 + 一次乘法」，误差不累积。

**修正方案二：用容差比较**

```c
for (float res = 0.0f; res < 5.0f - 1e-6f; res += 0.1f) {
  /* ... */
}
```

适用场景：**循环条件本身是浮点比较，且无法改成计数**（例如步长是运行时决定的浮点值）。注意用 `<` 而不是 `!=`，并留出容差。

**不推荐的方案**：`res != 5.0f` 改成 `res <= 5.0f`。虽然能终止，但最后一次迭代的 `res` 可能略大于 5.0，导致多做或少做一次迭代，边界不确定。

**答 4.**
**优势**：
1. **省内存**。`union` 的大小等于最大成员（这里 `char*` 8 字节），而并列写法是 `4 + 8 = 12` 字节（含对齐可能 16）。当变体数量多或最大成员远大于其他成员时，节省显著。
2. **语义更强**。`union` 明确表达「同一时刻只有一个成员有效」，读者一眼看出这是 tagged union 而非「两个独立字段」。并列写法容易被误读为「两个字段都有意义」。
3. **缓存友好**。所有变体占用相同空间，数组元素大小一致。

**风险**：
1. **读错成员是 UB**。若 `type == INT` 却读 `u.s`，会把整数值当指针解引用，可能段错误。并列写法不会有这个风险（虽然读到垃圾值，但不是 UB）。
2. **写入一个成员会让其他成员失效**。这在维护时容易忘记——例如给 `u.i` 赋值后，之前的 `u.s` 就丢了。
3. **不能同时持有两个值**。如果业务上确实需要「同时有整数和字符串」，`union` 不适用。

**结论**：`union` 适合「互斥的多种形状」，且必须配 `enum` 标签 + `switch` 分支访问，才能保证安全。

**答 5.**
**代码本身没有出错**——`c` 会等于 0，打印 `wrapped`。

但**推理过程容易出错**：`a + b` 中 `a` 和 `b` 都是 `unsigned short`，运算前**整型提升**为 `int`。`int` 能表示 65535 和 1，所以 `a + b` 是 `int` 类型的 **65536**，不发生 16 位回绕。然后赋值给 `unsigned short c` 时，65536 装不下，按「取最低有效位」截断为 **0**。

所以最终结果确实是 0，但**回绕发生在赋值处，不是加法处**。这个区别在下面这个变体里就暴露了：

```c
unsigned short a = 65535;
unsigned short b = 1;
if (a + b > 0) printf("positive\n");   /* 打印 positive！因为 a+b 是 int 的 65536 */
else printf("wrapped\n");
```

这里 `a + b` 是 `int` 的 65536 > 0，打印 `positive`——与「16 位回绕」的直觉相反。

**修正**（若确实想要 16 位回绕语义）：

```c
unsigned short c = (unsigned short)(a + b);   /* 显式截断，意图清晰 */
```

或者直接用 `uint16_t` 并显式转换，让意图在代码里可见。

**教训**：C 的整型提升让「小类型的算术」在 `int` 上进行，回绕只发生在**赋值/转换**时。写依赖回绕的代码必须显式转换，不能依赖隐式行为。

</details>

## 12. 进一步学习

- 上一讲：[[15-122-18-C-Memory-Model]] —— 指针算术与 UB 的内存视角；本讲是「类型视角」的补充。
- 下一讲：[[15-122-20-Virtual-Machines]] —— 从「C 的语义」下沉到「字节码如何在栈机上执行」，`int` 的 32 位语义在那里变成具体的指令行为。
- 回顾：[[15-122-02-Ints]] —— C0 的补码与模运算。对照本讲能看清「C0 定义了溢出、C 没有」这个关键差异。
- 相关：[[15-122-17-Introduction-to-C]] —— `-fwrapv` 与编译选项的关系。
- 课程入口：[[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]]、[[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 术语查询：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Type、Cast、Undefined Behavior、Union、Enum 等条目）。
