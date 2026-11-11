---
title: 07 函数指针与 void 指针
description: void* 的语义与转换、函数指针的声明与调用、回调、qsort 泛型接口与类型转换
date: 2026-11-11
---

# 07 函数指针与 void 指针

> 对应模块 07。系统编程里「通用接口」只有两种实现方式：`void *` 抹掉类型，函数指针抹掉行为。这两个工具一起构成了 C 的「泛型」。

## 学习目标

1. 说清 `void *` 能做什么、不能做什么。
2. 读懂并写出函数指针的声明（含返回函数指针的函数）。
3. 用函数指针实现回调（callback）。
4. 看懂 `qsort` 的签名，并写一个比较函数。
5. 说明函数指针与数据指针的转换限制。

## 前置知识

- [03-指针](03-指针.md)、[05-内存管理](05-内存管理.md)。

## 核心概念

### 1. `void *`：无类型指针

`void *` 是「指向未知类型」的指针。它能存任何对象指针，但**不能解引用、不能做算术**（标准 C）。

```c
int x = 42;
void *vp = &x;          /* 任何对象指针都能隐式转成 void * */
int *ip = vp;           /* 反向转换在 C 里也不需要强转（C++ 需要） */
printf("%d\n", *(int *)vp);   /* 必须转回具体类型才能解引用 */
```

**三个限制**：

| 操作 | `void *` 允许？ |
| --- | --- |
| 存任意对象指针 | ✅ |
| 与具体类型指针互相赋值 | ✅（C，不需要强转） |
| 解引用 `*vp` | ❌ 不知道大小 |
| 算术 `vp + 1` | ❌ 标准 C 不允许（GNU 扩展允许，按 1 字节） |
| 函数指针与 `void *` 互转 | ❌ 标准不保证 |

### 2. 函数指针

函数也有地址。函数指针存的就是函数的入口地址。

```c
int add(int a, int b) { return a + b; }

int (*fp)(int, int) = add;     /* fp 是指向「返回 int、接受两个 int」的函数的指针 */
int r = fp(2, 3);              /* 等价于 (*fp)(2, 3) */
```

**声明读法**（右左法则）：

```c
int (*fp)(int, int);
```

从 `fp` 开始：`fp` 是一个指针（`*fp`），指向函数（`(...)`），函数接受 `(int, int)`，返回 `int`。

### 3. 函数指针的常见写法

```c
typedef int (*binop_t)(int, int);    /* 用 typedef 简化 */

binop_t op = add;
printf("%d\n", op(2, 3));
```

**返回函数指针的函数**：

```c
int (*pick(int which))(int, int);    /* 返回 int(*)(int,int) */
```

**函数指针数组**（跳转表）：

```c
binop_t ops[] = {add, sub, mul};
printf("%d\n", ops[2](3, 4));        /* mul(3,4) = 12 */
```

### 4. 回调（callback）

把函数指针传给另一个函数，让它在合适的时候调用。

```c
void for_each(int *arr, size_t n, void (*fn)(int)) {
    for (size_t i = 0; i < n; i++) fn(arr[i]);
}

static void print_int(int x) { printf("%d ", x); }
for_each(a, n, print_int);
```

**这是 C 里实现「策略模式」的唯一方式**，也是 `qsort`、`pthread_create`、信号处理的接口基础。

### 5. `qsort`：泛型的标准范例

```c
void qsort(void *base, size_t nmemb, size_t size,
           int (*compar)(const void *, const void *));
```

- `base`：数组首地址（`void *`，抹掉类型）。
- `nmemb`：元素个数。
- `size`：每个元素字节数（`void *` 不知道大小，必须另给）。
- `compar`：比较函数，返回负 / 0 / 正。

```c
static int cmp_int(const void *a, const void *b) {
    int x = *(const int *)a;
    int y = *(const int *)b;
    return (x > y) - (x < y);      /* 避免减法溢出 */
}

int a[] = {3, 1, 2};
qsort(a, 3, sizeof a[0], cmp_int);
```

**比较函数里必须先把 `void *` 转回具体类型**，这是 `void *` 与函数指针配合的典型场景。

### 6. 类型转换

| 转换 | 是否安全 |
| --- | --- |
| 任意对象指针 → `void *` → 原类型 | ✅ 保证往返 |
| 任意对象指针 → 不相关类型指针 | ⚠ 对齐与别名问题 |
| 函数指针 ↔ 对象指针 | ❌ 标准不保证（POSIX 允许） |
| 整数 ↔ 指针 | ⚠ 实现定义，只在必要时用 |

**别名规则（strict aliasing）**：通过不相关类型的指针访问同一对象是 UB。`-fstrict-aliasing`（`-O2` 默认开启）会利用这条优化，导致诡异 bug。`memcpy` 是安全的类型双关方式。

## 英文术语与中文解释

| 英文 | 中文 | 一句话 |
| --- | --- | --- |
| void pointer | 无类型指针 | 能存任意对象地址，不能解引用 |
| function pointer | 函数指针 | 存函数入口地址的变量 |
| callback | 回调 | 把函数当参数传给别的函数 |
| comparator | 比较函数 | `qsort` 需要的「小于返回负」函数 |
| generic | 泛型 | 用 `void *` 抹掉类型 |
| strict aliasing | 严格别名 | 不同时用两种类型指针访问同一对象 |

## 通俗类比

- 函数指针 = 遥控器上的一个按键。按键本身不知道按下去会发生什么，只存着「对应哪个功能」。
- `void *` = 一个没有标签的包裹。你知道它是个东西，但不知道里面是什么，必须看标签（转换）才能拆。

## 原理讲解

### 函数指针调用发生了什么

```asm
; 普通调用
call add
; 函数指针调用
call *%rax     ; rax 里存着函数地址
```

函数指针调用比直接调用多一次**间接跳转**，但代价很小。它换来的是「运行时决定调用哪个函数」。

### 为什么 `qsort` 需要 `size` 参数

`qsort` 用 `memcpy` 交换元素。它不知道元素类型，所以需要 `size` 来计算每个元素的位置：

```c
/* qsort 内部交换的等价写法 */
char *p = (char *)base + i * size;
```

**这是 `void *` 与 `char *` 配合做字节级操作的标准技巧。**

### 严格别名为什么危险

```c
float f = 1.0f;
int *ip = (int *)&f;
*ip = 0;              /* UB：通过 int* 写 float 对象 */
printf("%f\n", f);    /* 结果不可预测 */
```

正确写法：

```c
uint32_t bits;
memcpy(&bits, &f, sizeof bits);   /* 类型双关的安全方式 */
```

## 内存示意图

### 函数指针

```text
.text 段：
0x401130:  add 的机器码
0x401150:  sub 的机器码

数据区：
fp = 0x401130   （8 字节，存函数地址）

调用 fp(2,3)：
  1. 从 fp 取出 0x401130
  2. 跳转到 0x401130
  3. 执行 add
```

### `qsort` 的比较函数

```c
int a[3] = {3, 1, 2};
qsort(a, 3, sizeof a[0], cmp_int);
```

```text
a:       +---+---+---+
         | 3 | 1 | 2 |
         +---+---+---+
           ^
base ----+
size = 4，nmemb = 3
qsort 内部：
  第 i 个元素地址 = (char *)base + i * 4
  比较时调用 cmp_int(addr_i, addr_j)
```

## 代码示例

```c
/* day07_funcptr.c */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef int (*binop_t)(int, int);

static int add(int a, int b) { return a + b; }
static int sub(int a, int b) { return a - b; }
static int mul(int a, int b) { return a * b; }

static void apply_all(int *arr, size_t n, int (*fn)(int)) {
    for (size_t i = 0; i < n; i++) arr[i] = fn(arr[i]);
}

static int double_it(int x) { return x * 2; }

static int cmp_int(const void *a, const void *b) {
    int x = *(const int *)a;
    int y = *(const int *)b;
    return (x > y) - (x < y);
}

int main(void) {
    binop_t ops[] = {add, sub, mul};
    const char *names[] = {"add", "sub", "mul"};
    for (int i = 0; i < 3; i++) {
        printf("%s(7,3) = %d\n", names[i], ops[i](7, 3));
    }

    int a[] = {3, 1, 2};
    apply_all(a, 3, double_it);
    qsort(a, 3, sizeof a[0], cmp_int);
    for (int i = 0; i < 3; i++) printf("%d ", a[i]);
    printf("\n");
    return 0;
}
```

## 逐行代码解释

| 行 | 说明 |
| --- | --- |
| `typedef int (*binop_t)(int, int)` | 把「二元运算函数指针」命名成 `binop_t` |
| `binop_t ops[] = {add, sub, mul}` | 函数名退化为函数指针 |
| `ops[i](7, 3)` | 通过函数指针调用 |
| `apply_all(..., int (*fn)(int))` | 回调：对每个元素应用 `fn` |
| `*(const int *)a` | 把 `void *` 转回 `int *` 再解引用 |
| `(x > y) - (x < y)` | 返回 −1/0/1，避免 `x - y` 溢出 |

## 常见错误

| 错误 | 后果 | 正确做法 |
| --- | --- | --- |
| `*vp` 直接解引用 `void *` | 编译错误 | 先转具体类型 |
| `vp + 1` | 标准 C 编译错误 | 转 `char *` 再算术 |
| 忘记 `typedef` 导致声明难读 | 写错括号 | 用 `typedef` |
| `qsort` 比较函数返回 `x - y` | 大数相减溢出 | 用 `(x > y) - (x < y)` |
| 函数指针未初始化就调用 | 崩溃 | 初始化为 `NULL` 并检查 |
| 通过不相关类型指针访问对象 | strict aliasing UB | 用 `memcpy` |

## 边界情况

- **函数指针可以为 `NULL`**，调用前检查。
- **函数名与 `&func` 等价**：`fp = add` 与 `fp = &add` 相同。
- **`(*fp)(args)` 与 `fp(args)` 等价**。
- **`qsort` 不稳定**：相等元素顺序不保证。
- **`bsearch`**：要求数组已排序，比较函数签名与 `qsort` 相同。

## 实践练习

`exercises/C-Language/Day-07/`：

| 文件 | 任务 |
| --- | --- |
| `ex1_funcptr_basic.c` | 用函数指针数组实现简易计算器 |
| `ex2_callback.c` | 实现 `for_each` / `map` / `filter`（用函数指针） |
| `ex3_qsort.c` | 用 `qsort` 排序 `int` 数组与字符串数组 |
| `ex4_void_ptr.c` | 实现 `swap_any(void *a, void *b, size_t size)` |

## 测试用例

```text
ex1_funcptr_basic: add(7,3)=10 sub(7,3)=4 mul(7,3)=21
ex2_callback:      map([1,2,3], double) -> [2,4,6]; filter 偶数 -> [2]
ex3_qsort:         int {3,1,2} -> {1,2,3}; 字符串按字典序
ex4_void_ptr:      swap_any 交换 int 与 struct 均正确
```

## 测试结果

| 项目 | 命令 | 结果 |
| --- | --- | --- |
| 编译 | `gcc -std=c11 -Wall -Wextra -Wpedantic -g -O0 Day-07/ex1_funcptr_basic.c` | ✅ 通过，0 警告 |
| 运行 | `./ex1_funcptr_basic` | ✅ `add(7,3)=10` / `sub(7,3)=4` / `mul(7,3)=21` / `sorted: 1 2 3` / `after swap_any: x=20 y=10` |

> 测试环境：WSL Ubuntu 24.04 + gcc 13.3.0，2026-11-11 实测。

## 对应原版资料

- **CMU C Boot Camp（S23）**：`90-原始PDF/15-213/bootcamps/cprogramming-bootcamp-s23.pdf`
  - p8：Pointers（函数指针引入）
  - p31：C Libraries
  - p40：`<stdlib.h>`（`qsort` / `bsearch`）
- **官方链接**：https://www.cs.cmu.edu/~213/bootcamps/cprogramming-bootcamp-s23.pdf

## 对应官方来源

- cppreference 函数指针：https://en.cppreference.com/w/c/language/pointer
- cppreference `qsort`：https://en.cppreference.com/w/c/algorithm/qsort
- 后续衔接：[[15-213-05-Machine-Programming-III-Procedures]]（间接调用）

## 自我检查问题

1. `void *` 能做哪三件事，不能做哪三件事？
2. 写出「指向返回 `int`、接受两个 `double` 的函数的指针」的声明。
3. `fp = add` 与 `fp = &add` 有区别吗？
4. `qsort` 为什么需要 `size` 参数？
5. `qsort` 的比较函数为什么不能直接返回 `x - y`？
6. 什么是 strict aliasing？为什么 `memcpy` 做类型双关是安全的？

## 本节总结

- `void *` 抹掉类型，不能解引用、不能算术。
- 函数指针存函数地址，用 `typedef` 简化声明。
- 回调是 C 实现「策略」的唯一方式；`qsort` 是标准范例。
- 类型双关用 `memcpy`，不要用指针强转。

## 下一节

→ [08-编译与链接](08-编译与链接.md)
