---
course: CMU 15-122
course_name: Imperative Computation
semester: Fall 2026
lecture_id: L17
topic: Introduction to C
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-122
  - 标准C
  - 预处理器
  - valgrind
  - 内存泄漏
---

# 第 17 讲：C 语言入门（Introduction to C）

## 1. 本节学习目标

学完本讲后，你应该能够：

1. 明确说出**本讲是语言分界点**：前 16 讲用 C0，从本讲起用**标准 C（不是 C0）**，并列出两者在内存管理、指针、类型、编译工具、调试工具五个方面的核心差异。
2. 用 `#include` 取代 `#use`，并说出 `<stdlib.h>`、`<stdio.h>`、`<string.h>`、`<stdbool.h>`、`<limits.h>` 各自对应 C0 的哪个库。
3. 解释为什么宏是「纯文本替换」，并用 `#define INT_MIN (-1 ^ 0x7FFFFFFF)` 这个例子说明漏写括号会怎样算出错误结果。
4. 说明「C 没有断言语言」这一事实，以及 `lib/contracts.h` 如何用宏把 `REQUIRES`/`ENSURES`/`ASSERT` 变成 `assert`。
5. 用 `gcc` 的完整选项编译一个 C 程序，并解释每个选项（`-Wall -Wextra -Wshadow -Werror -std=c99 -pedantic -g -DDEBUG`）的作用。
6. 说明为什么分离编译需要头文件与 include guard，并复现「缺少头文件」时的两类编译错误。
7. 用 `valgrind` 读出一段程序的内存泄漏报告，并说出 `free` 的两条限制。
8. 解释 Ownership（归属权）转移的含义，并写出接受 `entry_free_fn*` 回调的 `tree_free`。

## 2. 前置知识

- 前序讲次：[[15-122-16-AVL-Trees]]（最后一份 C0 代码）、[[15-122-13-Hash-Dictionaries]]（`typedef` 与接口/实现分离，本讲的分离编译是它的 C 版本）。课程入口见 [[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]] 与 [[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 需要熟悉命令行：`cd`、`ls`、运行可执行文件。
- 需要知道「编译」与「解释」的区别：C0 由 `coin` 解释执行，C 要先编译成机器码。
- 术语统一以 [[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]] 为准。

> **语言边界（本讲最重要的提醒）**
>
> | 方面 | C0（第 1–16 讲） | 标准 C（第 17 讲起） |
> |---|---|---|
> | 内存分配 | `alloc(t)` / `alloc_array(t, n)`，自动垃圾回收 | `malloc(sizeof(t))` / `calloc(n, sizeof(t))`，**必须手工 `free`** |
> | 空指针检查 | 分配失败不会发生 | `malloc` 可能返回 NULL，要用 `xmalloc` |
> | 契约 | `//@requires`、`//@ensures` 是**语言的一部分**，`coin -d` 检查 | `//@` **只是注释**；契约要用 `REQUIRES`/`ENSURES` 宏写成函数体里的语句 |
> | 指针 | `&` 只能取函数地址 | `&` 可以取任何对象的地址；有指针算术 |
> | 类型 | `int` 溢出按模 2³² 定义 | **有符号溢出是 undefined behavior** |
> | 编译 | `cc0`（C1）或 `coin`（C0） | `gcc` |
> | 调试 | `coin -d` 检查契约 | `valgrind` 检查内存错误 |
> | 头文件 | `#use "queue.h"` | `#include "queue.h"` + include guard |
>
> **本讲之后所有代码都是标准 C。把 C0 的 `alloc` 当成 C 的 `malloc` 用，是本课程最常见的错误来源。**

## 3. 核心概念

**Standard C（标准 C）**：由 ISO 标准定义的 C 语言。本课程使用 C99（`-std=c99`）。它没有垃圾回收、没有契约注解、没有 `alloc`。

**Preprocessor（预处理器）**：编译前对源文件做文本处理的程序。它以 `#` 开头的行作为指令：`#include`（插入文件）、`#define`（定义宏）、`#ifdef`/`#ifndef`/`#endif`（条件编译）。

**Macro（宏）**：`#define` 定义的文本替换规则。**纯文本**，不理解语法，不理解类型。

**Include Guard（包含卫士）**：用 `#ifndef X_H` / `#define X_H` / `#endif` 包住头文件内容，防止同一头文件被重复包含。

**Separate Compilation（分离编译）**：把程序拆成多个 `.c` 文件分别编译成 `.o`，再链接成可执行文件。头文件声明接口，`.c` 文件提供实现。

**Memory Leak（内存泄漏）**：`malloc` 分配的内存没有对应的 `free`，程序再也无法访问它，但它仍占着内存。

**Dangling Pointer（悬垂指针）**：指向已被 `free` 的内存的指针。解引用它是 undefined behavior。

**Ownership（归属权）**：约定「谁负责 `free` 这块内存」。归属权可以转移（例如把 entry 交给树，树负责 free 它）。

**`xmalloc` / `xcalloc`**：`lib/xalloc.h` 提供的包装，分配失败时直接报错退出，从而把「`malloc` 可能返回 NULL」这个负担从每个调用点消除。

## 4. 通俗理解

从 C0 到 C 的转变，像从**酒店**搬到**自己租的房子**。

- **C0 的 `alloc` 是酒店服务**：你随时要房间，酒店给你；你走了（对象不可达），酒店自动打扫。你不用管。
- **C 的 `malloc` 是租房**：你签合同拿钥匙，走的时候**必须自己退租**（`free`）。不退租，房租一直扣（内存泄漏）；退了租还留着钥匙回去住（use-after-free），会出事。
- **契约的转变**：C0 里 `//@requires` 是写进合同的法律条款，酒店必须执行；C 里 `//@requires` 只是你贴在墙上的便条，**没人看**。要真的执行，得自己写成代码（`REQUIRES(...)` 宏）。
- **valgrind 是房屋检查员**：它在你退房后检查有没有东西落下（泄漏）、有没有人偷偷回来住（use-after-free）。

## 5. 原理与推导

### 5.1 从 C0 到 C：逐项对照

**库的对应关系**（`17-cintro.pdf` 第 3–4 页）：

| C0 | 标准 C | 提供什么 |
|---|---|---|
| `#use <conio>` | `#include <stdio.h>` | `printf`、`puts`、文件 I/O |
| `#use <util>` | `#include <stdlib.h>` | `malloc`、`free`、`exit`、`atoi` |
| （无） | `#include <string.h>` | `strlen`、`strcmp`、`strcpy`、`memcpy` |
| （`bool` 是内建） | `#include <stdbool.h>` | `bool`、`true`、`false` |
| （`int_max()` 是内建） | `#include <limits.h>` | `INT_MAX`、`INT_MIN`、`CHAR_BIT` |

注意 `#use` 与 `#include` 的区别：`#use` 是 C0 特有的、会**自动去重**的指令；`#include` 是纯文本插入，**不去重**，所以必须自己写 include guard。

### 5.2 宏是纯文本替换

这是本讲最容易踩坑的地方。

```c
#define INT_MIN -1 ^ 0x7FFFFFFF
```

看起来没问题。但宏是**纯文本替换**，所以

```c
int x = INT_MIN / 256;
```

被展开成

```c
int x = -1 ^ 0x7FFFFFFF / 256;
```

而 `/` 的优先级高于 `^`，所以实际计算的是 `-1 ^ (0x7FFFFFFF / 256)` = `-1 ^ 0x7FFFFF` = `0xFFFFFFFFFF800000`... 具体值取决于整数宽度，但**不是**我们想要的 `INT_MIN / 256`。

讲义给出的正确写法：

```c
#define INT_MIN (-1 ^ 0x7FFFFFFF)
```

**规则：宏体里凡是出现运算符，整个表达式必须加括号；宏参数在宏体里每次出现也都要加括号。**

```c
/* 错误 */
#define SQUARE(x) x * x
SQUARE(a + 1)   /* 展开成 a + 1 * a + 1 = a + a + 1 */

/* 正确 */
#define SQUARE(x) ((x) * (x))
```

第二条更隐蔽的错误：`#define MAX(a,b) ((a) > (b) ? (a) : (b))`，调用 `MAX(i++, j)` 会让 `i` 自增两次。宏没有「参数只求值一次」的保证——这是宏与函数最本质的区别。

### 5.3 条件编译与宏函数

```c
#define DEBUG 1

#if DEBUG
  printf("debug: x = %d\n", x);
#endif

#ifdef __APPLE__
  /* macOS 特有代码 */
#else
  /* 其他平台 */
#endif
```

**宏函数**（第 6 页）：

```c
#define MAX(a, b) ((a) > (b) ? (a) : (b))
```

它「看起来像函数」，但**没有类型检查、没有参数求值次数保证、无法取地址、无法调试（断点打不进去）**。工程上，能用 `static inline` 函数就不要用宏函数。

### 5.4 C 没有断言语言

这是本讲最重要的观念转变。

在 C0 里：

```c0
int f(int x)
//@requires x >= 0;
//@ensures \result >= 0;
{ ... }
```

`coin -d` 会真的在每次调用时检查前置条件、在返回时检查后置条件。**契约是语言的一部分。**

在标准 C 里：

```c
int f(int x)
//@requires x >= 0;      /* 这只是一行注释 */
{ ... }
```

`gcc` 完全忽略它。**没有任何工具会检查它。** 契约退化成「给人看的文档」。

要在 C 里真的检查，必须写进函数体：

```c
#include "lib/contracts.h"

int f(int x) {
  REQUIRES(x >= 0);
  ...
  ENSURES(result >= 0);
  return result;
}
```

`lib/contracts.h` 的定义（第 6–7 页）：

```c
#ifdef DEBUG
#define ASSERT(COND) assert(COND)
#define REQUIRES(COND) assert(COND)
#define ENSURES(COND) assert(COND)
#else
#define ASSERT(COND) ((void)0)
#define REQUIRES(COND) ((void)0)
#define ENSURES(COND) ((void)0)
#endif
```

三个要点：

1. **未定义 `DEBUG` 时，宏展开成 `((void)0)`**，即「什么都不做」的合法语句。这保证发布版没有运行时开销。
2. **`((void)0)` 而不是空字符串**：如果展开成空，`if (x) REQUIRES(y); else ...` 会变成 `if (x) ; else ...`（语法错误）或 `if (x) else`（错误）。展开成一个语句解决了这个问题。
3. **`REQUIRES` 与 `ASSERT` 在实现上完全相同**，区别只在语义：`REQUIRES` 表达「调用者的义务」，`ASSERT` 表达「此处我依赖的事实」。这个区分对读代码的人有意义，对编译器没有。

**代价**：C 里无法表达 `\result`、`\length`、`\hastag` 这些契约专用词汇。所以 C 的 `ENSURES` 只能检查那些用普通表达式能写出来的性质，而且必须在 `return` 之前手工调用。这是 C0 到 C 的**表达能力损失**，不是语法差异。

### 5.5 内存分配：从 `alloc` 到 `malloc`

```c0
/* C0 */
int* p = alloc(int);
int[] A = alloc_array(int, 10);
```

```c
/* C */
#include <stdlib.h>
int* p = malloc(sizeof(int));
int* A = malloc(sizeof(int) * 10);
```

三个差异：

1. **`sizeof` 取代了类型参数**。`sizeof(int)` 是编译期常量，等于 4（在典型平台上）。
2. **`malloc` 不初始化内存**。分配到的字节是**上一次使用者留下的垃圾**。要清零用 `calloc`：
   ```c
   int* A = calloc(10, sizeof(int));   /* 10 个元素，全 0 */
   ```
   注意 `calloc` 的参数顺序是 `(元素个数, 单个大小)`，与 `malloc` 的「总字节数」不同。
3. **`malloc` 可能返回 NULL**（内存不足时）。C0 的 `alloc` 不会失败，所以 C0 代码里没有 NULL 检查——直接搬到 C 里就是 bug。

解法是用 `lib/xalloc.h`：

```c
#include "lib/xalloc.h"
int* p = xmalloc(sizeof(int));            /* 失败时打印错误并 exit */
int* A = xcalloc(10, sizeof(int));        /* 同上，且清零 */
```

`xmalloc` 把「检查 NULL」这件事封在一处，让其余代码可以假定分配总是成功。这是**用「快速失败」换「代码简洁」**的典型取舍。

### 5.6 编译：完整命令行

```bash
gcc -Wall -Wextra -Wshadow -Werror -std=c99 -pedantic -g -DDEBUG \
    main.c queue.c -o main
```

逐项解释：

| 选项 | 作用 |
|---|---|
| `-Wall` | 打开常用警告（未使用变量、隐式声明、缺返回值等） |
| `-Wextra` | 打开 `-Wall` 之外的额外警告（如符号比较、空循环体） |
| `-Wshadow` | 警告「局部变量遮蔽外层同名变量」 |
| `-Werror` | **把所有警告当作错误**，编译失败 |
| `-std=c99` | 使用 C99 标准（允许 `for (int i = ...)` 这样的声明） |
| `-pedantic` | 严格遵循标准，拒绝编译器扩展 |
| `-g` | 生成调试信息（`gdb`、`valgrind` 需要它来报行号） |
| `-DDEBUG` | 定义 `DEBUG` 宏，让 `REQUIRES`/`ASSERT` 生效 |

`-Werror` 值得单独说：它把「警告」升级为「错误」，强制你在提交前处理所有警告。工程上这是好事——「以后再说」的警告永远不会有「以后」。但在调试阶段，它可能让你无法快速试错，此时可以临时去掉。

**`-g` 与 `-DDEBUG` 的配合**：`-g` 让 valgrind 能报告「第 42 行」，`-DDEBUG` 让契约检查生效。两者都开才是完整的开发配置。

### 5.7 分离编译与头文件

把队列拆成三个文件：

```
queue.h     —— 接口：typedef、函数声明
queue.c     —— 实现：#include "queue.h"，写函数体
main.c      —— 客户端：#include "queue.h"，调用
```

`queue.h` 必须有 include guard：

```c
#ifndef QUEUE_H
#define QUEUE_H

typedef struct queue_header* queue_t;
queue_t queue_new(void);
void enq(queue_t Q, void* x);
void* deq(queue_t Q);

#endif
```

**为什么需要 guard？** 因为 `main.c` 可能间接包含 `queue.h` 两次（例如 `main.c` 包含 `queue.h` 和 `stack.h`，而 `stack.h` 也包含 `queue.h`）。第二次包含时，`typedef` 与结构体定义会重复，编译器报「重复定义」。

**缺少头文件会怎样？** 讲义第 9–11 页演示了两类错误：

1. **`invalid application of sizeof to incomplete type`** —— 在 `main.c` 里写 `malloc(sizeof(struct queue_header))`，但 `struct queue_header` 的定义只在 `queue.c` 里（这是**信息隐藏**的正确做法），所以 `main.c` 看到的是一个 incomplete type（不完整类型），不知道大小。**这正是抽象的目的**：客户端不该知道 header 的内部布局。
2. **`implicit declaration of function`** —— 调用 `queue_new()` 但没包含声明。C99 下这是警告（配合 `-Werror` 变成错误）。危险在于：编译器会**猜**一个签名（返回 `int`、参数按实际传入推断），如果真实签名不同（例如返回指针），链接后行为未定义。

第二类错误在旧版 C（C89）里只是警告，程序可能「看起来能跑」但在 64 位平台上因为指针被截断成 `int` 而崩溃。这是 C 语言历史上最著名的坑之一。

### 5.8 `free` 的两条限制

```c
void free(void* p);
```

**限制一：只能 `free` 由 `malloc`/`calloc`/`xmalloc`/`xcalloc` 返回的指针。**

- `free(&local_var)` —— 局部变量在栈上，不是堆，错误。
- `free(p + 1)` —— 指针算术的中间结果，不是分配起点，错误。
- `free(NULL)` —— **合法**，什么也不做。这是标准明确规定的。

**限制二：`free` 之后不得再引用该指针。**

```c
int* p = xmalloc(sizeof(int));
*p = 42;
free(p);
*p = 43;              /* undefined behavior：use-after-free */
int y = *p;           /* undefined behavior */
free(p);              /* undefined behavior：double free */
```

这就是 **Dangling Pointer（悬垂指针）**。防御性做法是 `free` 后立刻置 NULL：

```c
free(p);
p = NULL;
```

这样后续的误用至少会变成「解引用 NULL」这个更容易定位的错误（而不是静默读写已释放内存）。

### 5.9 归属权与 `entry_free_fn`

数据结构释放时，它该不该 `free` 里面的元素？这取决于**归属权约定**。

```c
typedef void entry_free_fn(void* e);
void tree_free(tree* T, entry_free_fn* Fr);
```

- `Fr != NULL`：树拥有元素，释放每个节点时调用 `(*Fr)(T->data)` 释放元素。
- `Fr == NULL`：树**不**拥有元素，只释放节点本身，元素由客户端自己管。

这个设计把「谁负责释放」的决定权交给客户端，而不是硬编码在库里。这是 C 里表达归属权的标准手法——**用 NULL 表示「我不拥有」**。

对比第 14 讲的函数指针：这里又一次用了「把操作作为参数传入」的模式。区别在于 `entry_free_fn` 的返回值是 `void`，因为释放不需要反馈。

### 5.10 valgrind：三类典型报告

**（1）内存泄漏**

```
==12345== HEAP SUMMARY:
==12345==     in use at exit: 8 bytes in 1 blocks
==12345==   total heap usage: 1 allocs, 0 frees, 8 bytes allocated
==12345==
==12345== LEAK SUMMARY:
==12345==    definitely lost: 8 bytes in 1 blocks
==12345==    indirectly lost: 0 bytes in 0 blocks
```

读法：程序退出时还有 8 字节没释放，1 次分配 0 次释放。`definitely lost` 表示「指针已丢失，无法再释放」。

**（2）修复后**

```
==12345== All heap blocks were freed -- no leaks are possible
```

**（3）use-after-free**

```
==12345== Invalid read of size 4
==12345==    at 0x4005F3: main (test.c:12)
==12345==  Address 0x5204040 is 0 bytes inside a block of size 8 free'd
==12345==    at 0x4C2DB8F: free (in /usr/lib/valgrind/vgpreload_memcheck.so)
```

读法：「读 4 字节时地址无效；该地址位于一个**已被释放**的 8 字节块的起始处」。这句话同时告诉你「错在读了」和「那块内存已经 free 过」——两个信息合起来就定位了 use-after-free。

**`definitely lost` vs `indirectly lost`**：前者是你直接丢失了指针；后者是「你丢失了 A，而 B 只能通过 A 到达」。修掉 A 的泄漏，B 通常一起解决。

## 6. 代码示例

### 6.1 官方课程代码

以下代码出自 `17-cintro.pdf`，页码为该 PDF 的页码。

**（1）第一个 C 程序与库对照**（第 3 页）

`#include <stdio.h>` 取代 `#use <conio>`，`printf` 取代 `print`/`printint`。

**（2）预处理器与宏**（第 4–5 页）

`#define INT_MIN -1 ^ 0x7FFFFFFF` 及其错误展开；正确写法加括号。

**（3）条件编译**（第 5 页）

`#if`/`#ifdef`/`#endif` 的用法。

**（4）宏函数**（第 6 页）

`#define MAX(a,b) ((a) > (b) ? (a) : (b))` 与它的三个缺陷。

**（5）`lib/contracts.h`**（第 6–7 页）

```c
#ifdef DEBUG
#define ASSERT(COND) assert(COND)
#define REQUIRES(COND) assert(COND)
#define ENSURES(COND) assert(COND)
#else
#define ASSERT(COND) ((void)0)
#define REQUIRES(COND) ((void)0)
#define ENSURES(COND) ((void)0)
#endif
```

**（6）内存分配**（第 7 页）

`alloc(int)` → `malloc(sizeof(int))`；`alloc_array(int, n)` → `malloc(sizeof(int) * n)`；`calloc` 清零；`xmalloc`/`xcalloc` 处理 NULL。

**（7）编译命令**（第 8 页）

```bash
gcc -Wall -Wextra -Wshadow -Werror -std=c99 -pedantic -g -DDEBUG \
    main.c queue.c -o main
```

**（8）分离编译**（第 9–11 页）

`queue.h` 的 include guard；缺少头文件时的 `invalid application of sizeof to incomplete type` 与 `implicit declaration of function`。

**（9）内存泄漏与 `free`**（第 11–13 页）

`free` 的两条限制；`free(NULL)` 合法；`entry_free_fn` 与归属权。

**（10）valgrind**（第 13–14 页）

`in use at exit: 8 bytes in 1 blocks`、`definitely lost: 8 bytes in 1 blocks`、`All heap blocks were freed -- no leaks are possible`、`Invalid read of size 4 ... is 0 bytes inside a block of size 8 free'd`。

**（11）习题与答案**（第 15–19 页题目，第 20–30 页答案）

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念

**示例一：从 C0 到 C 的完整迁移。**

C0 版本：

```c0
#use <conio>
#use <util>

typedef struct point { int x; int y; } point;

point* mk_point(int x, int y)
//@requires true;
//@ensures \result != NULL && \result->x == x && \result->y == y;
{
  point* p = alloc(point);
  p->x = x;
  p->y = y;
  return p;
}
```

C 版本：

```c
#include <stdio.h>
#include <stdlib.h>
#include "lib/xalloc.h"
#include "lib/contracts.h"

typedef struct point { int x; int y; } point;

point* mk_point(int x, int y)
/* 原来的 //@requires / //@ensures 现在只是注释 */
{
  point* p = xmalloc(sizeof(point));
  p->x = x;
  p->y = y;
  ENSURES(p != NULL && p->x == x && p->y == y);   /* 真的会检查（-DDEBUG 时） */
  return p;
}

void point_free(point* p) {
  REQUIRES(p != NULL);
  free(p);
  /* p 现在是悬垂指针，但调用者的副本仍指向它 */
}
```

四个改动：`#use` → `#include`；`alloc(point)` → `xmalloc(sizeof(point))`；契约从注解变成函数体里的宏调用；新增 `point_free`（C0 不需要，因为有 GC）。

**示例二：一个必然泄漏的程序，以及它的修复。**

```c
#include <stdlib.h>
#include <stdio.h>

typedef struct node {
  int value;
  struct node* next;
} node;

node* push(node* head, int v) {
  node* n = malloc(sizeof(node));
  n->value = v;
  n->next = head;
  return n;
}

int main(void) {
  node* list = NULL;
  for (int i = 0; i < 4; i++) list = push(list, i);
  /* 忘了释放：4 个节点 × 16 字节 = 64 字节泄漏 */
  return 0;
}
```

valgrind 报告：

```
in use at exit: 64 bytes in 4 blocks
   definitely lost: 64 bytes in 4 blocks
```

修复：

```c
void list_free(node* head) {
  while (head != NULL) {
    node* next = head->next;   /* 先存 next，再 free head */
    free(head);
    head = next;
  }
}
```

**顺序是关键**：如果先 `free(head)` 再读 `head->next`，就是 use-after-free。必须先保存 `next`。

在 `main` 里加 `list_free(list);` 后，valgrind 报告 `All heap blocks were freed -- no leaks are possible`。

**示例三：契约检查真的能抓到 bug。**

```c
#include "lib/xalloc.h"
#include "lib/contracts.h"

int safe_div(int a, int b) {
  REQUIRES(b != 0);
  return a / b;
}

int main(void) {
  printf("%d\n", safe_div(10, 0));   /* -DDEBUG 时在这里 abort */
  return 0;
}
```

编译时加 `-DDEBUG`：

```
main: main.c:6: safe_div: Assertion `b != 0' failed.
Aborted (core dumped)
```

不加 `-DDEBUG`：`REQUIRES(b != 0)` 展开成 `((void)0)`，程序继续执行，得到除以零的 undefined behavior（在 x86 上通常是 SIGFPE，但也可能被优化掉）。**这就是「契约只是注释」的实际后果**——它在你需要它的时候不生效，除非你显式启用。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键区别 | 记忆点 |
|---|---|---|---|
| `alloc(t)`（C0） | `malloc(sizeof(t))`（C） | 前者有 GC、不会失败；后者要手工 `free`、可能返回 NULL | **本讲是分界点** |
| `malloc` | `calloc` | 前者不清零、参数是总字节数；后者清零、参数是（个数, 单个大小） | 「m 是 raw，c 是 clean」 |
| `#use`（C0） | `#include`（C） | 前者自动去重；后者纯文本插入，需要 include guard | C 要自己防重复 |
| `//@requires`（C0） | `REQUIRES(...)`（C 宏） | 前者是语言的一部分、`coin -d` 检查；后者是宏、只在 `-DDEBUG` 时生效 | C 里契约是「可选自检」 |
| 宏 `#define` | 函数 | 宏是文本替换，无类型检查、参数可能多次求值、无法调试 | 「宏是抄写员，不是计算器」 |
| `free(p)` 后再用 `p` | 用完再 `free(p)` | 前者是 use-after-free（UB）；后者是正确顺序 | 「先关门再走人」 |
| `free(p+1)` | `free(p)` | 前者不是分配起点，UB；后者正确 | 只能 free 原始指针 |
| `free(NULL)` | `free(&x)` | 前者合法（什么也不做）；后者是释放栈地址，UB | NULL 是特例 |
| `definitely lost` | `indirectly lost` | 前者是直接丢了指针；后者是「通过丢失的指针才能到达」 | 修前者常连带修后者 |
| 本讲 C 代码 | 前 16 讲 C0 代码 | 见第 2 节的对照表 | 不要把 `alloc` 当 `malloc` 用 |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-122/lectures/17-cintro.pdf`
- **总页数**：30 页
- **本节重点页码**（PDF 页码，即提取文本中 `=== [page N] ===` 的 N）：
  - 第 3 页：第一个 C 程序、`#include` 与库的对照
  - 第 4 页：预处理器总览
  - 第 4–5 页：宏的文本替换本质、`INT_MIN` 的括号陷阱
  - 第 5 页：条件编译
  - 第 6 页：宏函数与它的缺陷
  - 第 6–7 页：**C 没有断言语言**、`lib/contracts.h` 的三组宏
  - 第 7 页：`malloc`/`calloc`/`xmalloc`/`xcalloc`
  - 第 8 页：完整 `gcc` 命令行与每个选项的作用
  - 第 9–11 页：分离编译、include guard、缺少头文件的两类错误
  - 第 11–13 页：内存泄漏、`free` 的两条限制、归属权与 `entry_free_fn`
  - 第 13–14 页：valgrind 的三类报告
  - 第 15–19 页：习题 Ex1–Ex7
  - 第 20–30 页：参考答案（Ex3 的 `stack_free` 在第 20–22 页，Ex5 的 32 字节泄漏在第 23–26 页，Ex7 的别名问题在第 27–30 页）
- **原始网页链接**：`https://www.cs.cmu.edu/~15122-archive/f26/handouts/lectures/17-cintro.pdf`
- **配套代码包**：`90-原始PDF/15-122/code/17-cintro.tgz`
- **官方视频**（讲义中给出的链接）：
  - Freeing in C：`https://youtu.be/J_FzhQAWiJ4`
  - Using Valgrind：`https://youtu.be/2e_u2eXe7P4`
- **官方教程**：`https://github.com/iliano/c0/wiki/From_C0_to_C_-_Basics`

## 9. 对应视频

未找到官方公开录像。讲义第 13–14 页给出的两个短视频可作补充：`https://youtu.be/J_FzhQAWiJ4`（Freeing in C）与 `https://youtu.be/2e_u2eXe7P4`（Using Valgrind）。系统性的 C0→C 迁移说明见官方 wiki：`https://github.com/iliano/c0/wiki/From_C0_to_C_-_Basics`。

## 10. 本节复习

1. **本讲是语言分界点**：L01–L16 用 C0（`coin`/`cc0`、`alloc`、`//@` 契约、GC）；L17 起用标准 C（`gcc`、`malloc`/`free`、契约宏、valgrind）。
2. 库映射：`<conio>`→`<stdio.h>`、`<util>`→`<stdlib.h>`，新增 `<string.h>`、`<stdbool.h>`、`<limits.h>`。`#use`→`#include`，后者不去重，要 include guard。
3. 宏是纯文本替换：宏体加括号、参数加括号；宏参数可能被求值多次；宏无法调试。
4. **C 没有断言语言**。`//@` 只是注释。要检查就写 `REQUIRES`/`ENSURES`/`ASSERT` 宏，它们只在 `-DDEBUG` 时生效，否则展开成 `((void)0)`。
5. `malloc` 不清零、可能返回 NULL；`calloc(n, size)` 清零；`xmalloc`/`xcalloc` 把 NULL 检查收拢到一处。
6. 编译选项：`-Wall -Wextra -Wshadow -Werror -std=c99 -pedantic -g -DDEBUG`。`-g` 给 valgrind 报行号，`-DDEBUG` 让契约生效。
7. `free` 两条限制：只能 free 分配起点、free 后不得再引用。`free(NULL)` 合法。归属权用 `entry_free_fn*` 表达，NULL 表示「不拥有」。
8. valgrind 三个关键报告：`definitely lost`（泄漏）、`All heap blocks were freed`（干净）、`Invalid read ... free'd`（use-after-free）。

## 11. 自我检查

**题 1.** 下面的宏有什么问题？请给出修正版本，并说明 `f(2, 3)` 在错误版本下会得到什么。

```c
#define AVG(a, b) a + b / 2
```

**题 2.** 下面这段 C 代码在 `-DDEBUG` 与不加 `-DDEBUG` 时行为有何不同？请分别说明。

```c
#include "lib/contracts.h"
int get(int* A, int i, int n) {
  REQUIRES(A != NULL && 0 <= i && i < n);
  return A[i];
}
/* 调用：get(A, 10, 5) */
```

**题 3.** 解释为什么 `queue.h` 需要 include guard。如果不写，在什么具体情形下会编译失败？报什么错？

**题 4.** 下面这段释放链表的代码错在哪里？请给出正确版本。

```c
void list_free(node* head) {
  while (head != NULL) {
    free(head);
    head = head->next;
  }
}
```

**题 5.** 一个程序分配了 3 个 16 字节的节点，只 `free` 了头节点，然后丢失了所有指针。valgrind 会报多少 `definitely lost`、多少 `indirectly lost`？请解释这两个数字的来源。

<details>
<summary>参考答案</summary>

**答 1.** 三个问题：
1. **没有外层括号**：`AVG(1+1, 2+2)` 展开成 `1 + 1 + 2 + 2 / 2` = `1+1+2+1` = 5，而正确结果是 3。
2. **参数没有括号**：即使加了外层括号 `#define AVG(a,b) ((a) + (b) / 2)`，`AVG(1+1, 2+2)` 仍展开成 `((1+1) + (2+2)/2)` = `2 + 2` = 4，仍是错的。
3. **语义错误**：`a + b / 2` 因为优先级只把 `b` 除以 2，正确语义应是 `(a+b)/2`。

修正：

```c
#define AVG(a, b) (((a) + (b)) / 2)
```

在错误版本下，`f(2, 3)` 展开成 `2 + 3 / 2` = `2 + 1` = **3**，而正确答案是 `(2+3)/2 = 2`（整数除法）。**注意这里连「巧合正确」都不是**——错得很干净。

补充：即使写成 `(((a)+(b))/2)`，`AVG(i++, j++)` 仍会让 `i`、`j` 各自增两次。要避免这一点只能用 `static inline` 函数。

**答 2.**
- **`-DDEBUG` 时**：`REQUIRES(A != NULL && 0 <= i && i < n)` 展开成 `assert(...)`。调用 `get(A, 10, 5)` 时 `i < n` 即 `10 < 5` 为假，`assert` 失败，程序打印 `Assertion 'A != NULL && 0 <= i && i < n' failed.` 并 `abort()`。**在越界读发生之前就终止了**，这正是我们想要的。
- **不加 `-DDEBUG` 时**：`REQUIRES(...)` 展开成 `((void)0)`，什么都不做。程序继续执行 `return A[10];`，**越界读取**。这是 undefined behavior：可能读到垃圾值、可能读到相邻变量、可能触发段错误（如果 10 远超数组范围）、也可能被优化器利用产生完全意外的行为。**没有任何保证。**

这个对比就是「C 没有断言语言」的实际含义：契约检查是**可选的、编译期决定的**，而不是语言强制的。发布版为了性能通常关掉它，所以**测试必须在 `-DDEBUG` 下跑**，否则契约等于不存在。

**答 3.** `#include` 是**纯文本插入**，不做去重。如果 `main.c` 这样写：

```c
#include "queue.h"     /* 第一次：定义 queue_t */
#include "stack.h"     /* stack.h 内部也 #include "queue.h" */
```

而 `stack.h` 里也有 `#include "queue.h"`，那么 `queue.h` 的内容会被插入两次。第二次插入时，`typedef struct queue_header* queue_t;` 重复定义，编译器报：

```
error: redefinition of typedef 'queue_t'
```

如果是结构体的**完整定义**（而不是 typedef），报 `redefinition of 'struct queue_header'`。

加 include guard 后：

```c
#ifndef QUEUE_H
#define QUEUE_H
/* ... 内容 ... */
#endif
```

第二次插入时 `QUEUE_H` 已被定义，`#ifndef` 为假，整段被跳过。**guard 的宏名必须全局唯一**，所以惯例是用文件名大写加 `_H` 后缀。

顺带一提：`#pragma once` 也能达到同样效果，但它不是 C99 标准的一部分（`-pedantic` 下可能警告），所以本课程用 `#ifndef` 形式。

**答 4.** **错误：先 `free(head)` 再读 `head->next`，这是 use-after-free。**

```c
free(head);          /* 内存已归还 */
head = head->next;   /* 读已释放内存的字段 → UB */
```

`free` 之后那块内存的内容**不保证还是原来的值**——它可能已被分配器回收、被其他分配复用、或者被 valgrind 填成垃圾。所以 `head->next` 读到什么都可能，最坏情况是死循环或段错误。

valgrind 会报：

```
Invalid read of size 8
   at ... list_free (list.c:4)
 Address 0x... is 0 bytes inside a block of size 16 free'd
```

正确版本（**先存 next，再 free**）：

```c
void list_free(node* head) {
  while (head != NULL) {
    node* next = head->next;   /* 先保存 */
    free(head);                /* 再释放 */
    head = next;
  }
}
```

这个模式在链表、树、图的释放中反复出现，可以记成一句话：**「走之前先记住下一步」**。

**答 5.** 设三个节点为 A → B → C，各 16 字节，`free(A)` 后所有指针丢失：

- **`definitely lost: 16 bytes in 1 blocks`**
- **`indirectly lost: 16 bytes in 1 blocks`**
- （C 的 16 字节也归入 `indirectly lost`，所以实际是 `indirectly lost: 32 bytes in 2 blocks`）

精确解释（valgrind 的判据是**有没有入边**，不是「是否可达」）：

1. **A** 被正确 `free`，不属于任何 lost 类别。
2. **B** 原本只被 A 的 `next` 字段指向，而 A 已被释放，**没有任何指针再指向 B** → `definitely lost`，16 字节 1 块。
3. **C** 被 B 的 `next` 指向，而 B 是 lost 块 → `indirectly lost`，16 字节 1 块。

所以完整报告是 `definitely lost: 16 bytes in 1 blocks` + `indirectly lost: 16 bytes in 1 blocks`，合计 32 字节。

实用推论：**`indirectly lost` 通常不需要单独修**——它由 `definitely lost` 引起，修掉后者（找到那个丢失的入口指针）后，前者自然消失。读 valgrind 报告时先看 `definitely lost`。

补充两种相邻情形：
- 若你 `free(A)` 但**保留**了指向 B 的指针（例如栈上还有 `node* p = B;`），则 B 是 `still reachable`，不算泄漏。
- 若三个节点全部丢失且**一个都没 free**，则 A 是 `definitely lost`、B 与 C 是 `indirectly lost`，总数 48 字节。

</details>

## 12. 进一步学习

- 上一讲：[[15-122-16-AVL-Trees]] —— 最后一份 C0 代码。建议把它「翻译」成标准 C 作为本讲的练习。
- 下一讲：[[15-122-18-C-Memory-Model]] —— C 的五段内存布局、指针算术、undefined behavior 的完整清单。
- 强相关：[[15-122-19-Types-in-C]] —— C 的类型系统、`<stdint.h>`、数值转换、`union`/`enum`。
- 相关：[[15-122-13-Hash-Dictionaries]] —— 本讲分离编译的 C0 原型，对照看接口/实现分离如何从 `#use` 变成 `#include`。
- 官方补充材料：`https://github.com/iliano/c0/wiki/From_C0_to_C_-_Basics`（C0→C 官方迁移教程）；`https://youtu.be/J_FzhQAWiJ4`（Freeing in C）；`https://youtu.be/2e_u2eXe7P4`（Using Valgrind）。
- 课程入口：[[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]]、[[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 术语查询：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Pointer、Memory Model、Dereference、Macro、Memory Leak 等条目）。
