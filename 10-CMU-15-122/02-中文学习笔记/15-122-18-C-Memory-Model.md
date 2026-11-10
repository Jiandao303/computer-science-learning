---
course: CMU 15-122
course_name: Imperative Computation
semester: Fall 2026
lecture_id: L18
topic: C's Memory Model
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-122
  - 标准C
  - 内存模型
  - 指针算术
  - undefined-behavior
---

# 第 18 讲：C 的内存模型（C's Memory Model）

## 1. 本节学习目标

学完本讲后，你应该能够：

1. 画出标准 C 进程地址空间的五段布局，说明每段的增长方向、可写性与典型内容，并指出它与第 14 讲 C1 内存模型的差异。
2. 解释「C 中数组与指针几乎不可区分」这句话的确切含义，并写出 `int* x = A + 3; *x += 5;` 与 `A[3] += 5;` 的等价关系。
3. 说明为什么只能 `free` 分配起点的指针，`free(A + 3)` 会造成什么后果。
4. 列出本讲的七类 Undefined Behavior（未定义行为），并解释为什么它们「不是崩溃，而是什么都可能发生」。
5. 用 `&` 取局部变量的地址，说明由此产生的两类 bug：`free(&local)` 与「返回局部变量地址」。
6. 解释栈数组与堆数组在生命周期上的根本区别，以及为什么函数返回后栈数组的内容不可依赖。

## 2. 前置知识

- 前序讲次：[[15-122-17-Introduction-to-C]]（`malloc`/`free`、`xmalloc`、valgrind 的基本读法）、[[15-122-14-Genericity]]（C1 的五段内存模型，本讲是它的标准 C 版本）。课程入口见 [[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]] 与 [[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 需要知道 `sizeof` 的用法与常见类型的大小（`int` 4、指针 8、`char` 1）。
- 需要理解「按值传递」：函数参数是实参的副本。
- 术语统一以 [[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]] 为准。

> **语言提醒**：本讲是**标准 C**，不是 C0。这里的 `&` 可以作用于**任何对象**（C0/C1 里只能作用于函数名），指针可以参与算术运算（C0/C1 里不行），没有垃圾回收，没有 `//@` 契约。

## 3. 核心概念

**Memory Model（内存模型）**：规定程序可以访问哪些地址、每段地址的用途与权限、以及越界访问会发生什么的规则集合。

**Stack（栈）**：存放函数调用的局部变量与返回地址的区域，由编译器自动管理，随函数调用/返回自动增长/收缩。向下增长。

**Heap（堆）**：由 `malloc` 显式分配、由 `free` 显式归还的区域。向上增长。

**TEXT**：编译后的机器码。只读。

**DATA**：全局变量、静态变量、字符串字面量。字符串字面量部分只读。

**Undefined Behavior（未定义行为，UB）**：标准**不规定**程序行为的操作。编译器可以假定它永不发生，因而可能产生任意结果——包括「看起来正常运行」。

**Pointer Arithmetic（指针算术）**：对指针加减整数，结果按「元素大小」缩放。`A + 3` 不是「地址 +3 字节」，而是「地址 + 3×sizeof(*A) 字节」。

**Dangling Pointer（悬垂指针）**：指向已失效内存（已 `free` 的堆块、或已返回的栈帧）的指针。

**Aliasing（别名）**：两个或多个指针指向同一块内存。

## 4. 通俗理解

把内存想成一栋**五层楼**：

- **顶层与底层是物业的**（OS AREA），你进不去。底层最角落的门牌号是 0，那就是 NULL——一扇永远打不开的门。
- **栈在楼上，往下盖**：每进一个函数，就在当前楼层下面加一层，函数返回就把那层拆掉。所以函数一返回，那层的家具（局部变量）就全没了。
- **堆在地下，往上盖**：你向物业申请仓库（`malloc`），物业给你一把钥匙（指针）。**你不退租，仓库永远占着**；退了租钥匙还在你手上，你回去开门就是非法闯入（use-after-free）。
- **TEXT 与 DATA 在一楼，是刻在墙上的**：机器码和字符串字面量都刻死了，你拿笔去改墙（往字面量里写字节）会被保安抓（段错误）。

## 5. 原理与推导

### 5.1 五段布局

标准 C 的进程地址空间（`18-cmem.pdf` 第 2 页）：

```
高地址
┌─────────────────────────┐
│      OS AREA            │  操作系统保留（内核空间）
├─────────────────────────┤
│  System stack  ↓        │  局部变量、返回地址；向下增长
│                         │
│      (unused)           │  未分配的空隙
│                         │
│  System heap   ↑        │  malloc 分配；向上增长
├─────────────────────────┤
│  TEXT and DATA          │  机器码 + 全局/静态变量 + 字符串字面量；只读
├─────────────────────────┤
│      OS AREA            │  操作系统保留；地址 0x0 = NULL
└─────────────────────────┘
低地址
```

与第 14 讲 C1 模型的三点差异：

1. **C1 把 DATA 与 TEXT 分成两段**，标准 C 通常合称「TEXT and DATA」，因为两者都在低地址且都只读。
2. **C1 的 Stack 只存局部变量**（有 GC，不需要返回地址的概念）；标准 C 的 Stack 还存**返回地址与保存的寄存器**，这就是为什么「栈溢出」可以通过递归深度精确预测。
3. **C1 没有真正的指针算术**，所以「地址 + 3」这种概念在 C1 里不存在。标准 C 的指针算术是新增能力，也是新增 bug 来源。

**为什么 NULL 是 0x0 而不是别的值？** 因为 0x0 落在最低的 OS AREA 里，任何进程都无权访问。把「空指针」映射到一个必然不可访问的地址，可以让「解引用 NULL」变成硬件级的段错误（立即崩溃），而不是静默读到垃圾数据。**这是一次「用崩溃换安全」的设计**——崩溃是可定位的，静默错误不是。

### 5.2 数组与指针：几乎不可区分

```c
int *A = xmalloc(sizeof(int) * 5);
```

`A` 的类型是 `int*`，但它可以像数组一样用：

```c
A[0] = 10;
A[4] = 20;
```

**为什么？** 因为 C 标准规定：在大多数表达式里，数组类型的值会**退化**（decay）成指向首元素的指针。而 `A[i]` 的定义就是 `*(A + i)`。所以：

| 写法 | 等价于 | 说明 |
|---|---|---|
| `A[0]` | `*(A + 0)` = `*A` | 首元素 |
| `A[3]` | `*(A + 3)` | 第 4 个元素 |
| `*(A + 3)` | `A[3]` | 完全相同 |
| `&A[3]` | `A + 3` | 取地址就是指针加法 |
| `3[A]` | `*(3 + A)` = `A[3]` | 合法但别这么写 |

**指针算术的缩放**：`A + 3` 的字节偏移是 `3 * sizeof(int)` = 12 字节，不是 3 字节。这就是为什么指针必须有类型——编译器需要知道缩放因子。`void*` 不能参与算术（GCC 允许 `void* + 1` 作为扩展，但 `-pedantic` 会拒绝）。

**`free` 只能接受分配起点**：

```c
int *x = A + 3;
*x += 5;          /* 合法：读写第 4 个元素 */
free(x);          /* 错误：x 不是 malloc 返回的指针 */
```

为什么错？因为分配器在**起点之前**存了元数据（块大小、链表指针等）。`free` 需要根据起点找到这些元数据。给一个偏移过的指针，分配器会读到错误的元数据，破坏堆结构——这是**堆损坏**，症状可能在很久之后才出现（下次 `malloc` 时崩溃），极难调试。

正确做法永远是 `free(A)`。

### 5.3 七类 Undefined Behavior

讲义第 4 页列出：

1. **读未初始化的内存**。`malloc` 返回的内存是垃圾，读它得到不确定的值。
2. **数组越界读写**。`A[317] = 29;`（数组只有 5 个元素）、`A[-1] = 32;`。
3. **解引用 NULL**。
4. **写只读段**。例如往字符串字面量里写。
5. **Use-after-free**：`free(p)` 后读写 `*p`。
6. **Double free**：对同一指针 `free` 两次。
7. **`free` 非分配起点的指针**。

**为什么叫「未定义」而不是「会崩溃」？** 因为标准什么都没规定。实践中的表现谱系：

- 最好的情况：立刻段错误（例如解引用 NULL、越界到未映射页）。
- 常见情况：静默读写到相邻变量，程序算出错误结果但「看起来正常」。
- 最坏情况：编译器**假定 UB 不会发生**，据此做优化。例如：

```c
int f(int x) {
  int y = x + 1;        /* 若 x == INT_MAX，有符号溢出是 UB */
  if (y < x) { ... }    /* 编译器可以断定「这永远不会发生」并删掉整个分支 */
  return y;
}
```

`gcc -O2` 确实会删掉那个分支，因为「`x+1 < x` 只可能在有符号溢出时成立，而有符号溢出是 UB，所以这个分支不可达」。**UB 不是「运行时随机」，而是「编译期给了编译器说谎的许可」。**

讲义第 4 页的实验：`A[317] = 29; A[-1] = 32;` 在 `gcc -Wall -Wextra -Wshadow -Werror -std=c99 -pedantic -g -DDEBUG` 下**没有任何警告**（因为编译器无法静态判断下标是否越界），但 valgrind 报：

```
ERROR SUMMARY: 4 errors from 4 contexts
```

**这就是 valgrind 存在的理由**：编译器管不了的事，运行时工具能管。

### 5.4 Address-of：`&` 的完整能力

标准 C 里 `&` 可以作用于任何**左值**（有确定地址的对象）：

```c
typedef struct wallet { int count; int bills[10]; } wallet;

wallet* wc = xmalloc(sizeof(wallet));
int* p1 = &(wc->count);     /* 取字段地址 */
int* p2 = &wc->bills[3];    /* 取数组元素地址，等价于 wc->bills + 3 */
int* p3 = &wc->bills[0];    /* 等价于 wc->bills */
```

注意 `&wc->bills[3]` 与 `wc->bills + 3` **完全等价**——这再次印证了 `&A[i] ≡ A + i`。

**不能取的值**：`&(x + y)`（表达式结果不是左值）、`&42`（常量没有地址）、`&register_var`（寄存器变量）。

**与 C0/C1 的关键差异**：C1 里 `&` **只能**作用于函数名，因为 C1 的局部变量可能被垃圾回收器移动，取地址会失效。标准 C 没有 GC，对象地址稳定，所以可以随便取——**但代价是生命周期要你自己管**。

### 5.5 栈分配与它的两类致命错误

```c
void f() {
  int a1 = 42;          /* 栈上 */
  int A[5];             /* 栈上，5 个 int，内容未初始化 */
  int B[] = {0,1,2,3,4};/* 栈上，已初始化 */
  ...
}
```

栈变量的生命周期 = 从声明到函数返回。函数返回后，那块栈空间会被**下一次函数调用复用**。

**错误一：`free` 栈地址**

```c
void f() {
  int a1 = 42;
  free(&a1);          /* BUG：a1 在栈上，不是 malloc 来的 */
}
```

后果：分配器把栈地址当成堆块起点，读它前面的「元数据」得到垃圾，然后试图把这块内存插回空闲链表——**堆结构被破坏**。程序可能在很久之后崩溃。

**错误二：返回局部变量的地址**

```c
int *f_ohno() {
  int a = 1;
  return &a;          /* BUG：a 在函数返回时就失效了 */
}
```

返回的指针指向一块**已经失效的栈空间**。调用者拿到它后，任何后续函数调用都可能覆盖那块内存，于是 `*p` 读到的值随时会变。

新版 gcc 会直接报错：

```
error: function returns address of local variable [-Werror=return-local-addr]
```

这属于「幸运的 UB」——编译器能静态发现。但如果是通过指针间接返回（例如 `int* p = &a; return p;` 或经过一层函数），编译器可能抓不到。

**对比堆分配**：

```c
int *f_ok() {
  int *p = xmalloc(sizeof(int));
  *p = 1;
  return p;           /* 正确：堆内存的生命周期与函数无关 */
}
```

堆内存的生命周期由 `malloc`/`free` 决定，与函数调用无关。**这是「返回指针」唯一正确的做法。**

### 5.6 字符串字面量在只读段

```c
char *s = "hello";
s[0] = 'H';           /* UB：字面量在只读 DATA 段 */
```

编译能通过（`s` 是 `char*` 不是 `const char*`），运行时段错误。正确做法：

```c
const char *s = "hello";        /* 编译器会阻止写入 */
char buf[6] = "hello";          /* 栈上的可写副本 */
buf[0] = 'H';                   /* 合法 */
```

或者堆上复制：

```c
char *s = xmalloc(6);
strcpy(s, "hello");
s[0] = 'H';                     /* 合法 */
free(s);
```

**推论**：任何「修改传入字符串」的函数都不能直接收字面量。例如习题 Ex9 的 `str_shorten`：

```c
void str_shorten(char *s, size_t len) {
  /* 若 s 来自字面量，下面这行是 UB */
  s[len] = '\0';
}
```

调用 `str_shorten("hello world", 5)` 会崩。这不是函数的错，是**接口契约没写清**——函数应该声明「`s` 必须指向可写内存」，或者干脆接受 `char*` 并在文档里说明。

### 5.7 `calloc` 与清零

```c
int *A = calloc(7, sizeof(int));      /* 7 个 int，全 0 */
int *B = xcalloc(7, sizeof(int));     /* 同上，且失败时报错退出 */
```

`calloc` 的两个好处：

1. **清零**：避免「读未初始化内存」这一类 UB。
2. **参数语义更清晰**：`(个数, 单个大小)` 比 `malloc` 的「总字节数」更不容易算错。

代价：清零有开销（对小块可忽略，对大块可能显著）。所以「确定会立即覆盖全部元素」的场景用 `malloc` 更快。

**注意 `calloc(7, sizeof(int))` 不是 `calloc(sizeof(int), 7)`**——虽然字节总数相同，但语义上第一个参数是元素个数。标准保证「按元素个数 × 元素大小」计算并检查溢出，顺序写反在某些实现上可能触发不同的溢出检查行为。

### 5.8 习题要点

- **Ex1（第 9–11 页题目，解在第 18–21 页）**：把 C0 的 UBA（unbounded array）翻译成 C。两个要点：
  - `uba_free` 必须**先 free `data`，再 free `A`**。顺序不能反：`A` 被 free 后，`A->data` 就是 use-after-free。
  - 索引类型从 `int` 改成 `size_t`（因为要与 `\length` 比较，而 `\length` 在 C 里对应 `size_t`）。
- **Ex2（解在第 22–24 页）**：一个 `rect` 结构体的三个 bug：
  1. `int* area;` 声明后未初始化就解引用；
  2. `free(r)` 试图释放栈变量；
  3. `xmalloc` 后字段未初始化。
  修法：改用 `xcalloc(sizeof(rect), 1)`（注意这个参数顺序是 `xcalloc(size, count)` 的写法，实际应为 `xcalloc(1, sizeof(rect))`——**参数顺序是这类 bug 的常见来源，值得警惕**）。
- **Ex8（解在第 27–28 页）**：交换两个 `struct foobar` 指向的内容。正确做法是**整体交换结构体值**：
  ```c
  struct foobar temp = *x;
  *x = *y;
  *y = temp;
  ```
  不要逐字段交换（字段多了容易漏）。
- **Ex9（解在第 29–31 页）**：`str_shorten` 不能直接写 `s[len] = '\0'`，因为字面量在只读 DATA 段。解法是让调用者提供可写缓冲区，或返回一个新分配的字符串。

## 6. 代码示例

### 6.1 官方课程代码

以下代码出自 `18-cmem.pdf`，页码为该 PDF 的页码。

**（1）C0 与 C 的内存模型对比**（第 1–3 页）

五段布局图（第 2 页）：OS AREA（两端，含 0x0 = NULL）、System stack（向下）、unused、System heap（向上）、TEXT and DATA（只读）。

**（2）数组与指针算术**（第 3–4 页）

```c
int *A = xmalloc(sizeof(int) * 5);
A[0] = 10;
int *x = A + 3;
*x += 5;              /* 等价于 A[3] += 5 */
free(A);              /* 只能 free 原始指针 */
```

**（3）Undefined Behavior 清单**（第 4–5 页）

七类 UB；`A[317] = 29; A[-1] = 32;` 在严格编译选项下无警告，valgrind 报 `ERROR SUMMARY: 4 errors from 4 contexts`。

**（4）Address-of**（第 6 页）

`&(wc->count)`、`&A[3]` ≡ `A + 3`。

**（5）栈分配**（第 6–8 页）

`free(&a1)` 是 BUG；`int *f_ohno() { int a = 1; return &a; }` 是 BUG（新版 gcc 直接报错）；`int A[5];` 与 `int A[] = {0,1,2,3,4};`。

**（6）习题与答案**（第 9–17 页题目，第 18–31 页答案）

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念

**示例一：一个「看起来对、实际越界」的程序，以及 valgrind 如何抓它。**

```c
#include <stdio.h>
#include <stdlib.h>
#include "lib/xalloc.h"

int main(void) {
  int n = 5;
  int *A = xcalloc(n, sizeof(int));   /* 5 个元素，全 0 */

  /* 经典 off-by-one：i <= n 而不是 i < n */
  for (int i = 0; i <= n; i++) {
    A[i] = i * 10;
  }

  for (int i = 0; i < n; i++) {
    printf("%d ", A[i]);
  }
  printf("\n");

  free(A);
  return 0;
}
```

`gcc` 严格选项下**编译通过、无警告**。运行输出 `0 10 20 30 40`——看起来完全正确，因为 `A[5] = 50` 写到了分配块之后的 4 个字节，那里恰好是分配器的填充区，没人读它。

valgrind 输出：

```
==1234== Invalid write of size 4
==1234==    at 0x4006A3: main (demo.c:11)
==1234==  Address 0x5204044 is 0 bytes after a block of size 20 alloc'd
==1234==    at 0x4C2DB8F: malloc (...)
```

`0 bytes after a block of size 20` —— 精确指出「写在了 20 字节块的紧后面」。**这就是 valgrind 的核心价值：它知道每个分配块的边界。**

**示例二：use-after-free 的三种表现。**

```c
#include <stdlib.h>
#include "lib/xalloc.h"

int main(void) {
  int *p = xmalloc(sizeof(int));
  *p = 42;
  free(p);

  int a = *p;        /* (1) 读：可能得到 42，也可能是垃圾 */
  *p = 7;            /* (2) 写：可能破坏分配器元数据 */
  free(p);           /* (3) double free：分配器可能崩溃 */

  return a;
}
```

三种行为都可能发生，取决于分配器的实现与当时堆的状态：

- **(1)** 若这块内存还没被复用，读到 42；若已被其他分配复用，读到别人的数据。valgrind 报 `Invalid read of size 4 ... free'd`。
- **(2)** 写已释放内存，valgrind 报 `Invalid write of size 4 ... free'd`。
- **(3)** double free：现代分配器（glibc）通常能检测并 `abort()`，报 `double free or corruption`。但这不是标准保证的。

**防御性写法**：

```c
free(p);
p = NULL;            /* 后续误用变成「解引用 NULL」，更容易定位 */
```

**示例三：栈帧复用的实证。**

```c
#include <stdio.h>

int *danger(void) {
  int local = 12345;
  return &local;             /* gcc 会警告/报错 */
}

void clobber(void) {
  int junk[4] = {999, 999, 999, 999};   /* 复用同一块栈空间 */
}

int main(void) {
  int *p = danger();
  printf("before: %d\n", *p);   /* 可能打印 12345 */
  clobber();
  printf("after:  %d\n", *p);   /* 很可能打印 999 */
  return 0;
}
```

第二次打印很可能变成 999，因为 `clobber` 的栈帧覆盖了 `danger` 的栈帧。**这直观展示了「栈变量的生命周期在函数返回时结束」**——不是「值被清零」，而是「那块空间被回收，谁都可以用」。

注意：这个程序的行为是 UB，不同编译器/优化级别下结果可能完全不同。用 `-O2` 时，编译器甚至可能把第一次打印优化成常量。**这正是 UB 的可怕之处：它让「实验验证」失去意义。**

**示例四：正确的动态数组（含扩容）。**

```c
#include <stdlib.h>
#include <string.h>
#include "lib/xalloc.h"

typedef struct uba_header {
  size_t size;      /* 已用元素个数 */
  size_t limit;     /* 容量 */
  int *data;        /* \length(data) == limit */
} uba;

uba *uba_new(size_t limit) {
  uba *A = xmalloc(sizeof(uba));
  A->size  = 0;
  A->limit = limit;
  A->data  = xcalloc(limit, sizeof(int));
  return A;
}

void uba_add(uba *A, int x) {
  if (A->size == A->limit) {
    /* 扩容：分配新块，复制，释放旧块 */
    size_t newlimit = A->limit * 2;
    int *newdata = xcalloc(newlimit, sizeof(int));
    memcpy(newdata, A->data, A->size * sizeof(int));
    free(A->data);              /* 旧块必须释放，否则泄漏 */
    A->data  = newdata;
    A->limit = newlimit;
  }
  A->data[A->size] = x;
  A->size++;
}

void uba_free(uba *A) {
  free(A->data);                /* 先释放内层 */
  free(A);                      /* 再释放外层 */
}
```

两个要点：

1. **`uba_free` 的顺序**：先 `free(A->data)` 再 `free(A)`。反过来的话，`free(A)` 之后 `A->data` 就是 use-after-free 的读。
2. **扩容时的 `memcpy` 长度**是 `A->size * sizeof(int)`（已用元素），不是 `A->limit * sizeof(int)`（容量）。复制多余部分是浪费但不致错；复制不足会丢数据。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键区别 | 记忆点 |
|---|---|---|---|
| Stack（栈） | Heap（堆） | 前者自动管理、向下增长、生命周期 = 函数调用；后者手工管理、向上增长、生命周期 = malloc 到 free | 「自动 vs 手工」 |
| `A[i]` | `*(A + i)` | 完全等价，前者是后者的语法糖 | 数组就是指针算术 |
| `A + 3` | 地址 + 3 字节 | 前者按元素大小缩放，`int*` 时是 +12 字节 | 指针算术有类型 |
| `free(A)` | `free(A + 3)` | 前者正确；后者破坏堆元数据 | 只能 free 分配起点 |
| 栈数组 `int A[5]` | 堆数组 `xmalloc(...)` | 前者函数返回即失效；后者要手工 free | 「生命周期谁管」 |
| `char *s = "hi"` | `char s[] = "hi"` | 前者指向只读字面量；后者是栈上可写副本 | 「指针 vs 数组」 |
| 未定义行为（UB） | 「会崩溃」 | UB 可能正常运行、可能崩溃、可能算出错误结果；编译器可以假定它不发生 | **UB 不是崩溃** |
| 编译期警告 | 运行时检查 | 前者能抓语法/类型问题；后者（valgrind）能抓越界与生命周期问题 | 两者互补 |
| 本讲标准 C | 第 14 讲 C1 | C1 的 `&` 只能取函数地址、无指针算术、有 GC | **本讲是 C** |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-122/lectures/18-cmem.pdf`
- **总页数**：31 页
- **本节重点页码**（PDF 页码，即提取文本中 `=== [page N] ===` 的 N）：
  - 第 1–3 页：C0 与 C 内存模型的对比、五段布局图（第 2 页）
  - 第 3–4 页：数组与指针算术、`A[3]` ≡ `*(A+3)`、只能 free 原始指针
  - 第 4–5 页：七类 Undefined Behavior 与 valgrind 实验
  - 第 6 页：Address-of（`&(wc->count)`、`&A[3]`）
  - 第 6–8 页：栈分配、`free(&a1)` 的错误、返回局部变量地址的错误
  - 第 9–17 页：习题 Ex1–Ex9
  - 第 18–31 页：参考答案（Ex1 UBA 翻译在第 18–21 页，Ex2 三个 bug 在第 22–24 页，Ex8 结构体交换在第 27–28 页，Ex9 字面量只读在第 29–31 页）
- **原始网页链接**：`https://www.cs.cmu.edu/~15122-archive/f26/handouts/lectures/18-cmem.pdf`
- **配套代码包**：`90-原始PDF/15-122/code/18-cmem.tgz`

## 9. 对应视频

未找到官方公开录像。本讲建议配合 valgrind 亲手跑一遍 6.2 节的三个示例——UB 的可怕之处只有亲眼看到「同一份代码在不同优化级别下结果不同」才能体会。

## 10. 本节复习

1. 五段布局：OS AREA（两端，0x0 = NULL）、Stack（向下）、unused、Heap（向上）、TEXT and DATA（只读）。Stack 与 Heap 相向生长。
2. `A[i]` ≡ `*(A + i)` ≡ `*(i + A)` ≡ `i[A]`；`&A[i]` ≡ `A + i`。指针算术按元素大小缩放。
3. 只能 `free` 分配起点的指针。`free(A + 3)` 会破坏分配器元数据，症状延迟出现。
4. 七类 UB：读未初始化内存、越界、解引用 NULL、写只读段、use-after-free、double free、free 非起点。UB 不是「会崩溃」，而是「编译器可以假定它不发生」。
5. `&` 在标准 C 里可以作用于任何左值（C1 里只能作用于函数名）。
6. 栈变量的生命周期在函数返回时结束；`free(&local)` 与「返回局部变量地址」都是 UB。要返回指针就用堆。
7. 字符串字面量在只读 DATA 段；要修改就用 `char buf[] = "..."` 或堆上复制。
8. `calloc(n, size)` 清零且参数语义更清晰；`xcalloc` 额外处理分配失败。

## 11. 自我检查

**题 1.** 设 `int *A = xmalloc(sizeof(int) * 8);`，且 `A` 的地址是 0x1000（假设 `int` 4 字节、指针 8 字节）。写出下列表达式的值（或指出非法）：

（a）`A + 3` （b）`&A[5]` （c）`*(A + 2)` 的地址 （d）`A[3]` 与 `3[A]` 是否相同 （e）`free(A + 4)`

**题 2.** 下面这段代码有两个 bug，请指出并修正。

```c
int *make_array(int n) {
  int A[n];
  for (int i = 0; i < n; i++) A[i] = i;
  return A;
}
```

**题 3.** 解释为什么「读未初始化的 `malloc` 内存」是 UB，而「读未初始化的 `calloc` 内存」不是。这两者在实际运行中可能都「看起来正常」，为什么前者仍然危险？

**题 4.** 下面这段代码在 `-O2` 下会输出什么？为什么？

```c
#include <stdio.h>
#include <limits.h>

int main(void) {
  int x = INT_MAX;
  int y = x + 1;
  if (y < x) printf("overflow detected\n");
  else       printf("no overflow\n");
  return 0;
}
```

**题 5.** 一个 `struct` 有两个字段 `int a; int b;`，你分别用 `free(&s.a)` 和 `free(&s.b)`（`s` 是栈上的局部变量）。这两次调用分别会发生什么？如果 `s` 是 `xmalloc` 来的呢？

<details>
<summary>参考答案</summary>

**答 1.**
- （a）`A + 3` = 0x1000 + 3×4 = **0x100C**。类型仍是 `int*`。
- （b）`&A[5]` = `A + 5` = 0x1000 + 20 = **0x1014**。
- （c）`*(A + 2)` 的地址 = `A + 2` = 0x1000 + 8 = **0x1008**。
- （d）**相同**。`A[3]` 定义为 `*(A + 3)`，`3[A]` 定义为 `*(3 + A)`，加法交换律保证二者相等。两者都访问地址 0x100C 处的 `int`。
- （e）**非法（UB）**。`A + 4` 是 0x1010，不是分配起点 0x1000。`free` 会读到错误的元数据并破坏堆。正确写法是 `free(A)`。

**答 2.** 两个 bug：

1. **返回栈数组的地址**。`int A[n];` 是 VLA（变长数组），分配在栈上。函数返回时栈帧销毁，`A` 失效。调用者拿到的指针指向已回收的栈空间。
2. **`n` 未做合法性检查**。`n <= 0` 时 `A[n]` 的声明本身是 UB（VLA 长度必须为正）。

修正：

```c
int *make_array(int n) {
  if (n <= 0) return NULL;            /* 或 REQUIRES(n > 0) */
  int *A = xmalloc(sizeof(int) * n);  /* 堆上分配 */
  for (int i = 0; i < n; i++) A[i] = i;
  return A;                           /* 正确：堆内存生命周期与函数无关 */
}
```

调用者现在有义务 `free` 返回值——**归属权转移给了调用者**，这一点应写进注释或文档。

**答 3.**
- **`malloc` 的内存是「不确定值」**：标准规定它「没有初始化」，其内容可以是任意位模式。对于某些类型，任意位模式可能是**陷阱表示**（trap representation）——例如某些平台上 `_Bool` 的非法值、或指针的非法编码。读陷阱表示是 UB，可能导致硬件异常。
- **`calloc` 的内存是全零位模式**：标准保证「所有位为零」，且对整数类型全零就是 0，是合法值。所以读它是安全的。

**为什么前者仍然危险？** 三个理由：

1. **结果不确定**：同一份代码在不同运行、不同分配器状态下读到不同的值。这让「测试通过」失去意义——你测的那次恰好读到了 0。
2. **可能触发陷阱表示**：虽然对 `int` 极少见，但对指针、浮点、`_Bool` 是真实的。
3. **编译器可以据此优化**：如果编译器能证明某个变量未初始化就被使用，它可以假定「这条路径不可达」并删掉相关代码。这是 UB 最阴险的一面。

**实践建议**：除非确定会立即覆盖全部元素，否则用 `calloc`。这是「一点性能换确定性」的划算交易。

**答 4.** 输出 **`no overflow`**。

原因：`int y = x + 1;` 中 `x == INT_MAX`，有符号溢出是 **UB**。编译器据此推理：

> 「如果 `y < x` 成立，那么 `x + 1 < x`，即 `1 < 0`，矛盾——除非发生了有符号溢出。但有符号溢出是 UB，本程序不含 UB，所以 `y < x` 永远为假。」

于是 `gcc -O2` 把整个 `if` 分支删掉，只保留 `printf("no overflow\n")`。

**这个例子说明**：UB 的后果不是「运行时随机」，而是「编译期给了编译器说谎的许可」。同一份代码在 `-O0` 下可能打印 `overflow detected`（因为不优化，真的算了 `x+1` 得到 `INT_MIN`，`INT_MIN < INT_MAX` 为真），在 `-O2` 下打印 `no overflow`。**「在我的机器上能跑」对 UB 毫无意义。**

要在 C 里安全地检测溢出，必须用无符号算术（无符号溢出是**定义良好**的模运算）或编译器内建函数 `__builtin_add_overflow`。

**答 5.**
- **`s` 是栈上的局部变量**：
  - `free(&s.a)` 与 `free(&s.b)` 都是 **UB**。这两个地址都在栈上，不是 `malloc` 返回的。分配器会把它们当成堆块起点，读前面的「元数据」得到垃圾，然后试图把这块「块」插入空闲链表——**堆结构被破坏**。程序可能在这次调用后立刻崩溃（`free(): invalid pointer`），也可能在很久之后的某次 `malloc` 才崩溃。
  - 注意 `&s.a` 与 `&s.b` 通常相差 4 字节，所以第二次 `free` 甚至可能读到第一次 `free` 写入的链表指针——这会让损坏更难诊断。
- **`s` 是 `xmalloc` 来的**（即 `struct foo *s = xmalloc(sizeof(struct foo));`）：
  - `free(&s->a)`：`&s->a` 等于 `s`（第一个字段的地址就是结构体地址，前提是没有前置填充），所以**这次调用实际上等价于 `free(s)`，是正确的**。
  - `free(&s->b)`：`&s->b` = `s + 4`，不是分配起点，**UB**。而且如果先 `free(&s->a)` 再 `free(&s->b)`，第二次是 double free + 非起点，双重错误。

**教训**：永远 `free` 你从 `malloc`/`xmalloc` 拿到的那个变量本身，不要 free 它的字段地址——即使「碰巧」第一个字段的地址相同，这也是脆弱的（一旦结构体加了前置字段或对齐要求变化就会失效）。

</details>

## 12. 进一步学习

- 上一讲：[[15-122-17-Introduction-to-C]] —— `malloc`/`free`、`xmalloc`、valgrind 的基本用法；本讲是它的「内存布局」深化。
- 下一讲：[[15-122-19-Types-in-C]] —— C 的类型系统、`<stdint.h>`、数值转换规则、`union`/`enum`。
- 回顾：[[15-122-14-Genericity]] —— C1 的五段内存模型。对照本讲能看清「`&` 的能力扩张」与「GC 的消失」这两个关键差异。
- 相关：[[15-122-20-Virtual-Machines]] —— 从「进程地址空间」到「虚拟机」的抽象层次跃迁。
- 课程入口：[[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]]、[[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 术语查询：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Memory Model、Pointer、Dereference、Undefined Behavior 等条目）。
