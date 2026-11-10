---
course: CMU 15-122
course_name: Imperative Computation
semester: Fall 2026
lecture_id: L08
topic: Libraries
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-122
  - 库与接口
  - C0
---

# 第 8 讲：库与接口（Libraries）

> 讲义 PDF 的内页标题是 **"Lecture 8: Data Structures"**，但本讲的核心是**接口（interface）与库（library）的分离**——课程配套的复习幻灯片与短视频都叫 "Libraries"。本笔记按课程目录的讲次名 `Libraries` 命名，内容以讲义原文为准。

## 1. 本节学习目标

学完本讲后，你应该能够：

1. 说出 C0 的**五种类型**（`int`、`bool`、`char`、`string`、`t[]`），并解释为什么数组与字符串的「值」是**地址**。
2. 声明 `struct`、用 `typedef` 起别名，并解释为什么**结构体不能作局部变量**（`type struct ... not small`）。
3. 用 `alloc` 分配结构体、用 `p->f` 读写字段，并说明 `(*p).f` 与 `p->f` 的等价关系。
4. 解释指针值的两种：**有效地址**（`alloc` 分配的）与 **`NULL`**（无效地址），并说明为什么每次解引用都必须有「`p != NULL`」的理由。
5. 为一个**抽象类型** `ssa_t` 设计接口：三个基本操作 + `ssa_len`，并说明**为什么必须加 `ssa_len`**。
6. 解释 `ssa_t` 为什么必须是**指针类型**（`// typedef ______* ssa_t;`）。
7. 写出并解释**数据结构不变式**（data structure invariant）`is_ssa`，说明它由哪三部分组成。
8. 说明库侧为什么必须给 `ssa_len` 加前置 `A->length == \length(A->data)`，以及这条前置如何「传染」到 `ssa_get`。
9. 说明为什么 `ssa_set` 之后**再 `ssa_get` 同一个下标未必拿回刚写进去的值**。
10. 区分**客户端视角**与**库视角**：客户端只能用接口导出的东西，库内部的不变式与打印函数**不得**出现在客户端代码里。

## 2. 前置知识

- [[15-122-03-Arrays]]：`alloc_array`、`\length`、越界与未初始化错误、数组别名。
- [[15-122-01-Contracts]]：`requires`/`ensures`/`loop_invariant`/`assert`；规格函数；**契约必须是纯的**。
- [[15-122-02-Ints]]：十六进制字面量 `0xFF00FF00` 与补码（`0xFF00FF00` 打印为 `-16711936`）。
- [[15-122-05-Big-O]]：`O(log n)`——本讲的「自排序数组」之所以值得做，就是为了让客户端能用 [[15-122-06-Binary-Search]] 的二分查找。
- [[15-122-07-Quicksort]]：`is_sorted`、`swap`；本讲 `ssa_set` 的两个循环本质上是**插入排序的一步**。

## 3. 核心概念

**Struct（结构体）**：把**不同类型**的数据聚合在一起的复合类型。必须先声明「形状」。与数组相对：数组是**同一类型**元素的聚合。

**Field（字段）**：结构体里的一个具名分量，如 `data`、`width`、`height`。

**Pointer（指针）**：存放**地址**的值。`int*` 是「指向 `int` 的指针」，`struct img_header*` 是「指向该结构体的指针」。

**alloc（分配）**：`alloc(T)` 在堆上分配一个 `T` 类型的位置并返回指向它的指针。结构体**只能**这样创建。

**NULL**：一个**不是有效地址**的特殊指针值。解引用它必报错。

**Dereference（解引用）**：`*p` 读出或写入 `p` 指向的位置；`p->f` 是「解引用并取字段」的简写。

**Abstract Type（抽象类型）**：客户端只知道「能对它做什么」，不知道「它长什么样」。本讲的 `ssa_t` 是第一个例子。

**Interface（接口）**：抽象类型的**函数原型 + 契约**的集合。客户端只能看见接口，看不见实现。

**Data Structure Invariant（数据结构不变式）**：一个描述「这个数据结构处于良构（well-formed）状态」的**规格函数**，如 `is_ssa`。每个库函数都把它写进前置与后置。

**Self-Sorting Array（自排序数组）**：本讲的数据结构。固定长度、可按下标访问、**始终保持有序**——`ssa_set` 写入后会自行把元素挪到正确位置。

**Representation / Implementation Type（表示类型/实现类型）**：库内部真正用的类型，如 `struct ssa_header`。

## 4. 通俗理解

**结构体 vs 数组**：数组是「一排同样的柜子」，结构体是「一张登记表，每栏填不同类型的东西」。图像就是典型：一堆像素（数组）+ 宽 + 高（两个整数），三样东西**类型不同**，只能用结构体捆在一起。

**为什么结构体不能放局部变量**：局部变量住在**栈**上，而栈上的东西要能被整体复制（赋值、传参都要复制）。一个结构体可能很大（比如含一个 100 万元素的数组），复制起来代价高得离谱。C0 干脆禁止：**结构体只存在于堆上，你手里永远只有一个指针**。讲义的原话是「C0 does not allow us to use structs as locals」，编译器提示也很直白：`[Hint: cannot pass or store structs in variables directly; use pointers]`。

**指针 vs 数组地址**：数组变量里存的其实也是地址，所以以前我们说「数组的值就是地址」是对的。但指针多了一个数组没有的东西——**`NULL`**。所以「指针就是地址」这句话**不完整**：地址有两种，有效的和无效的（`NULL`）。

**为什么 `ssa_len` 必须进接口**：`\length` 是 **C0 数组的原始操作**，只能用在 `t[]` 上。`ssa_t` 是抽象类型，编译器根本不知道它内部有没有长度。可契约里**必须**写出上界 `i < 长度`，否则客户端传 `i = 100` 给长度 12 的数组就没人拦。**没有长度就没法写安全契约，所以长度必须成为接口的一部分**。

**为什么 `ssa_t` 一定是指针**：假如 `ssa_t` 就是 `string[]`，那 `ssa_len` 根本没法实现——返回 `\length(A)` 是**契约专用**的，不能写在函数体里当返回值。既然 `ssa_t` 不能是数组，那它只能是「指向某个结构体的指针」。**这是一条纯粹由「必须能实现接口」倒推出来的结论**，讲义称之为 "we do know something about `ssa_t` now"。

**`ssa_set` 的「反直觉」之处**：普通数组里 `A[i] = x;` 之后 `A[i]` 一定还是 `x`。自排序数组不保证——因为 `x` 会被挪到有序位置上。讲义特别提醒：**「it is unlikely that a subsequent call to `ssa_get(A, i)` will return `x` as its value」**。这是「抽象类型可以有自己的脾气」的第一个实例，后面几讲的栈、队列、链表都会反复出现这种「操作语义与底层数组不同」的现象。

## 5. 原理与推导

### 5.1 五种类型与「值 vs 地址」

讲义列出 C0 已有的五种类型：`int`、`bool`、`char`、`string`，以及**对每个类型 `t` 都存在的** `t[]`。

关键区分：

| 类型 | 变量里存的是什么 |
|---|---|
| `int`、`bool`、`char` | **值本身** |
| `string`、`t[]` | **地址**（指向存放数据的地方） |

所以下面这段 coin 会话里，`A` 这个变量里装的是一个地址，`A[0]`、`A[1]` 这些格子才装字符串的地址：

```c0
--> char c = '\n';
--> int i = 4;
--> string[] A = alloc_array(string, 4);
--> A[0] = "hi";
--> A[1] = "je";
--> A[2] = "ty";
--> A[3] = "lo";
```

### 5.2 结构体：声明、分配、访问

**声明**（定义「形状」）：

```c0
struct img_header {
  pixel_t[] data;
  int width;
  int height;
};
```

`data`、`width`、`height` 是**字段**。讲义指出这个声明**不完整**：本该还有「`\length(data) == width * height`」这样的约束，但那属于**数据结构不变式**，不写在 `struct` 里。

**为什么不能作局部变量**：

```c0
% coin structs.c0
--> struct img_header IMG;
<stdio>:1.1-1.22:error:type struct img_header not small
[Hint: cannot pass or store structs in variables directly; use pointers]
```

`not small` 是 C0 的术语：**小类型**（最多 64 位，因为地址是 32 位或 64 位）才能放进变量、传参、返回。结构体可能很大，故被排除。**即使它碰巧小于 32 位也不行**——这是语言规则，不是优化判断。

**分配**：

```c0
--> struct img_header* IMG = alloc(struct img_header);
IMG is 0xFFAFFF20 (struct img_header*)
```

**默认值**（`alloc` 会把内存清零）：

```c0
--> IMG->data;
(default empty int[] with 0 elements)
--> IMG->width;
0 (int)
--> IMG->height;
0 (int)
```

注意 `data` 的默认值是**空数组**（长度 0），不是 `NULL`——数组类型没有 `NULL` 这个值。

**写入**：

```c0
--> IMG->data = alloc_array(pixel_t, 2);
IMG->data is 0xFFAFC130 (int[] with 2 elements)
--> IMG->width = 1;
IMG->width is 1 (int)
--> (*IMG).height = 2;
(*(IMG)).height is 2 (int)
--> IMG->data[0] = 0xFF00FF00;
IMG->data[0] is -16711936 (int)
--> IMG->data[1] = 0xFFFF0000;
IMG->data[1] is -65536 (int)
```

**`(*p).f` 与 `p->f`**：`*p` 先沿指针到达内存里的结构体，`.f` 再选字段。讲义说课程里**极少**用点号形式，一律用箭头。`(*IMG).height` 里那对括号**不可省**——`*IMG.height` 会被解析成 `*(IMG.height)`，而 `IMG` 是指针、没有字段，直接报错。

**十六进制与负数**：`0xFF00FF00` 打印成 `-16711936`，因为 C0 的 `int` 是 32 位补码（见 [[15-122-02-Ints]]）。`0xFF00FF00` 最高位是 1，故是负数。

### 5.3 指针与 NULL

```c0
--> int* ptr1 = alloc(int);
ptr1 is 0xFFAFC120 (int*)
--> *ptr1 = 16;
*(ptr1) is 16 (int)
--> *ptr1;
16 (int)
```

```c0
--> int* ptr2 = NULL;
ptr2 is NULL (int*)
--> *ptr2;
Error: null pointer was accessed
Last position: <stdio>:1.1-1.3
```

**「指针就是地址」为什么不完整**：地址分两类——

- **有效地址**：用 `alloc` 显式分配得到的。
- **无效地址**：`NULL` 是最典型的一个。讲义还预告：**在标准 C 里还能造出许多别的无效地址**（后续讲内存管理时会讲），这是 C0 与 C 的重大差别。

**为什么这条规则如此重要**（讲义 p6）：

> **Whenever you dereference a pointer `p`, either as `*p` or `p->f`, you must have a reason to know that `p` cannot be `NULL`.**

**在 C0 里**：解引用 `NULL` 与数组越界属于**同一类安全性违规**，**必然**得到错误信息。
**在 C 里**：结果是**未定义行为（undefined behavior）**，可能不报错、可能崩溃、可能「看起来正常」——这是最难查的一类 bug。

**怎么获得「`p != NULL`」的理由**：与数组越界一样，靠**前置条件**或**循环不变式**。本讲后面每一个库函数都以 `A != NULL` 或 `is_ssa(A)`（它蕴含 `A != NULL`）开头。

### 5.4 设计接口：从三个操作到四个

自排序数组（self-sorting array，缩写 `ssa`）的**原始操作**对应 C0 数组的三件事：

```c0
// typedef _______ ssa_t;
ssa_t  ssa_new(int size);            // ~ alloc_array(string, size)
string ssa_get(ssa_t A, int i);      // ~ A[i]
void   ssa_set(ssa_t A, int i, string x);  // ~ A[i] = x
```

**但这不是完整接口**——接口还必须**捕获安全使用所需的全部前置条件**。

**第一轮补全**：长度必须非负，下标必须非负。

```c0
ssa_t ssa_new(int size)
/*@requires size >= 0 @*/;
string ssa_get(ssa_t A, int i)
/*@requires 0 <= i; @*/;
```

**第二轮补全**：还需要**上界**。但我们没有 `\length`——它是 C0 数组的原始操作，不适用于 `ssa_t`。**于是必须往接口里加一个取长度的函数**：

```c0
int ssa_len(ssa_t A);
string ssa_get(ssa_t A, int i)
/*@requires 0 <= i && i < ssa_len(A); @*/;
```

**这一步的推理链值得记住**（讲义 p7–8 专门强调）：

1. 契约里必须有上界 → 2. 上界需要长度 → 3. `\length` 只对数组有效 → 4. 长度必须由接口函数提供 → 5. **故 `ssa_t` 不能是 `string[]`**（否则 `ssa_len` 无法实现，因为 `\length` 只能出现在契约里）→ 6. **故 `ssa_t` 是「未知的指针类型」**。

**第三轮补全**：既然是指针，就必须防 `NULL`。

```c0
// typedef ______* ssa_t;
int ssa_len(ssa_t A)
/*@requires A != NULL; @*/
/*@ensures \result >= 0; @*/ ;

ssa_t ssa_new(int size)
/*@requires 0 <= size; @*/
/*@ensures \result != NULL; @*/
/*@ensures ssa_len(\result) == size; @*/ ;

string ssa_get(ssa_t A, int i)
/*@requires A != NULL; @*/
/*@requires 0 <= i && i < ssa_len(A); @*/ ;

void ssa_set(ssa_t A, int i, string x)
/*@requires A != NULL; @*/
/*@requires 0 <= i && i < ssa_len(A); @*/ ;
```

**注意 `ssa_new` 的第二条后置**：`ssa_len(\result) == size`。这是**客户端能依赖的唯一「长度信息」**，它让 `ssa_new(5)` 之后 `ssa_get(A, 4)` 的前置可证。

**注意 `ssa_set` 没有后置**：客户端**不**被告知「写进去的值还在原处」——因为自排序数组不保证这一点。接口**故意**不承诺。

### 5.5 库视角：表示类型与 `ssa_t` 的接线

```c0
struct ssa_header {
  // Implementation type
  int length;
  string[] data;
};
typedef struct ssa_header ssa;   // Abbreviation
typedef ssa* ssa_t;              // Interface type
```

**最后一行是接口与实现的接缝**：把导出的 `ssa_t` 定义为「指向 `ssa` 的指针」。讲义说**惯例上把它写在实现的最后一行**。

**命名纪律**：

- **库内部**一律写 `ssa*`，提醒自己「我在操作指针结构」。
- **库外部**一律写 `ssa_t`，即抽象类型。

### 5.6 第一次撞墙：`ssa_get` 的越界无法证明

先写两个最简单的函数：

```c0
int ssa_len(ssa* A)
//@requires A != NULL;
{
  return A->length;
}

string ssa_get(ssa* A, int i)
//@requires A != NULL;
//@requires 0 <= i && i < ssa_len(A);
{
  return A->data[i];
}
```

**`A != NULL` 让 `A->length` 与 `A->data` 安全**。但 **`A->data[i]` 为什么不越界？** 讲义直说：**我们不知道**。

`ssa_get` 的第二条前置只告诉我们 `i < ssa_len(A)`，而 `ssa_len(A)` 返回的是 `A->length`——**一个普通的 `int` 字段**，它与 `\length(A->data)` 之间的关系**从未被声明**。

### 5.7 补丁的连锁反应（本讲最精彩的一段推理）

讲义用三行「……」把这条链推完：

1. **想让 `ssa_len` 有用**，就要给它加后置 `\result == \length(A->data)`。
2. **这个后置证不出来**，除非给 `ssa_len` 加前置 `A->length == \length(A->data)`。
3. **加了前置之后，`ssa_get` 里那句 `ssa_len(A)` 就不再必然安全**（它现在有前置了），**所以 `ssa_get` 也必须加上同样的前置**。

**客户端完全不受影响**——客户端根本不知道 `length` 与 `data` 这两个字段存在。但**库内部每一处**都要背上这条约束。

**「每一处」有多少？** 想一想：`ssa_new` 建立它、`ssa_set` 必须保持它、`ssa_len` 与 `ssa_get` 假设它。**这就是不变式（invariant）的形态**——不是某一处的前置，而是**贯穿所有库函数的一条恒真命题**。

### 5.8 数据结构不变式 `is_ssa`

```c0
bool is_ssa(ssa* A) {
  return A != NULL
      && is_array_expected_length(A->data, A->length)
      && ssa_sorted(A);
}
```

**三项的含义**：

| 项 | 保证什么 | 属于 |
|---|---|---|
| `A != NULL` | 解引用安全 | 安全性（safety） |
| `is_array_expected_length(A->data, A->length)` | `\length(A->data) == A->length`，故 `ssa_len` 的后置可证、`A->data[i]` 不越界 | 安全性 |
| `ssa_sorted(A)` | 数组真的有序，故客户端能二分查找 | **正确性（correctness）** |

讲义明确区分：前两项「capture safety but do not say anything about the array being sorted」；第三项是**正确性不变式**。

**为什么 `is_array_expected_length` 只能写成「断言 + 返回 true」**：

```c0
bool is_array_expected_length(string[] A, int length) {
  //@assert \length(A) == length;
  return true;
}
```

因为**长度检查被限制在契约里**（`\length` 不能出现在普通表达式里），所以没法写出「返回 `\length(A) == length` 这个 bool」的函数。讲义坦白这是**破例**，并说：

> **「Whenever possible, however, we prefer data structure invariants that return true or false to data structure invariants that raise assertion failures.」**

**为什么偏好「返回 false」**：断言失败会**中止程序**，你只看到「某处断言失败」；而返回 `false` 的不变式可以被**上层函数检查并打印诊断信息**（见 5.12 的打印函数）。**诊断能力**是这里的核心考量。

### 5.9 用不变式重写四个函数

```c0
int ssa_len(ssa* A)
//@requires is_ssa(A);
//@ensures \result == \length(A->data);
{
  return A->length;
}

string ssa_get(ssa* A, int i)
//@requires is_ssa(A);
//@requires 0 <= i && i < ssa_len(A);
{
  return A->data[i];
}
```

**现在 `A->data[i]` 的安全性可以证明了**：

1. 前置 `0 <= i && i < ssa_len(A)`。
2. `ssa_len` 的前置是 `is_ssa(A)`，**由 `ssa_get` 的第一条前置满足**，故调用合法。
3. 由 `ssa_len` 的后置得 `ssa_len(A) == \length(A->data)`。
4. 代入 1 得 `0 <= i && i < \length(A->data)`——**正是数组访问所需的安全条件**。

**这是一条完整的「契约接力」**：`ssa_get` 的前置 → 满足 `ssa_len` 的前置 → 得到 `ssa_len` 的后置 → 满足数组访问的条件。**每一步都只用到契约，没有偷看任何函数体。**

```c0
ssa* ssa_new(int size)
//@requires 0 <= size;
//@ensures is_ssa(\result);
{
  ssa* A = alloc(ssa);
  A->length = size;
  A->data = alloc_array(string, size);
  return A;
}
```

**`is_ssa` 的三项在返回时都成立**：

- `A != NULL`：`alloc` 从不返回 `NULL`。
- `is_array_expected_length`：`A->length = size`，且 `alloc_array(string, size)` 的长度就是 `size`。**但这一步需要 `//@assert` 才能让验证器相信**（因为 `\length` 在契约之外不可用）——这正是 `is_array_expected_length` 内部那句断言的作用。
- `ssa_sorted(A)`：**长度 0 到 `size` 的数组全是默认值 `""`（空串）**，而 `""` 与 `""` 相等，故有序。**「全同即有序」是这里的空真式论证。**

讲义把规则总结成两句：

> **创建型函数**（`ssa_new`）要把不变式写进**后置**。
> **修改型函数**（`ssa_set`）要保证不变式**在返回时仍成立**。

### 5.10 `ssa_set`：两个循环就是一次插入排序

```c0
void ssa_set(ssa* A, int i, string x)
//@requires is_ssa(A);
//@requires 0 <= i && i < ssa_len(A);
//@ensures is_ssa(A);
{
  A->data[i] = x;
  // Move x up the array if needed
  for (int j=i; j < A->length-1 &&
       string_compare(A->data[j],A->data[j+1]) > 0;
       j++)
  //@loop_invariant i <= j && j <= A->length - 1;
    swap(A->data, j, j+1);

  // Move x down the array if needed
  for (int j=i; j > 0 &&
       string_compare(A->data[j],A->data[j-1]) < 0;
       j--)
  //@loop_invariant 0 <= j && j <= i;
    swap(A->data, j, j-1);
}
```

**先看为什么需要两个循环**：写入 `x` 之后，`x` 可能**太大**（需要往右挪）也可能**太小**（需要往左挪）。**只有其中一个循环会真正执行**：

- 若 `x` 比右邻居大，第一个循环启动，把 `x` 一路右移到正确位置。移到之后 `x` 已经 `<=` 右邻居，第二个循环的守卫立刻为假。
- 若 `x` 比左邻居小，第一个循环的守卫立刻为假，第二个循环启动，把 `x` 一路左移。

**「先写坏、再修好」的中间状态**：`A->data[i] = x;` 之后、循环结束之前，`is_ssa(A)` 是**假的**（数组可能无序）。**这没问题**——不变式只要求在**函数入口**与**函数出口**成立，中间可以暂时破坏。这一点与循环不变式不同：循环不变式必须**每轮**成立。

**第一个循环的不变式 `i <= j && j <= A->length - 1`**：

- **INIT**：`j = i`。需要 `i <= i`（真）与 `i <= A->length - 1`。后者由前置 `i < ssa_len(A)` 与 `is_ssa` 给的 `ssa_len(A) == A->length` 得 `i <= A->length - 1`。**这是前置条件在这里发挥作用的地方。**
- **PRES**：`j` 每轮 `+1`，`j <= A->length - 1` 需要重新成立——由**守卫** `j < A->length - 1` 得 `j+1 <= A->length - 1`。
- **EXIT**：`j == A->length - 1` 或右邻居已 `>= A->data[j]`。**这两种退出情形分别对应「移到末尾」与「找到位置」。**

**第二个循环的不变式 `0 <= j && j <= i`**：

- **INIT**：`j = i`，需要 `0 <= i`（由前置）与 `i <= i`。
- **PRES**：`j` 每轮 `-1`，`0 <= j-1` 由守卫 `j > 0` 得。
- **EXIT**：`j == 0`（移到最左）或左邻居已 `<= A->data[j]`（找到位置）。

**为什么两个循环合起来能重建 `ssa_sorted`**：这正是**插入排序**（insertion sort）的一步。区别在于插入排序通常从「已排序前缀」插入新元素，而这里是**从中间插入**——但因为插入前整个数组有序，`i` 左边与右边各自有序，把 `x` 往任一方向挪到第一个合适的位置，全局就有序了。**「有序数组里改一个元素，只需把它挪到正确位置」** 是本讲的隐含引理。

**注意守卫用了短路求值**：`j < A->length-1 && string_compare(...)` —— 先查下标，再访问 `A->data[j+1]`。**若顺序反过来，`j == A->length-1` 时就会越界读取**。这与 [[15-122-06-Binary-Search]] 里 `lo == 0 || A[lo-1] < x` 的写法是同一个技巧。

### 5.11 「不变式不属于接口」

讲义有一整段专论（p12）：

> **「When we have interfaces that hide implementations from the user, then the data structure invariant ... should not be a part of the interface.」**

**理由**：客户端不需要知道内部不变式。**只要它按接口用，不变式自然成立。**

**但客户端怎么确信元素真的有序？** 讲义给了两条路：

1. **信任库的作者**。
2. **自己写一个客户端版的 `ssa_sorted`**——只用接口导出的 `ssa_len` 与 `ssa_get`。

**第二条路是可验证的**：客户端版 `ssa_sorted` 只依赖接口契约，因此**换一个实现也照样成立**。这就是抽象类型的价值。

### 5.12 调试库实现：两条互补的路

讲义指出「注意到有 bug」有**两种互补方法**：

1. **契约推理**：在**第一次运行之前**就发现错误。适合「潜在不安全操作是否真的安全」这类问题。
2. **测试**：写一批测试用例。**除非用例极大，一律用 `-d` 编译**（debug 模式，让契约生效）。

**「找到 bug 在哪」也有两条路**：

1. **契约报错**：失败时**中止并报出确切行号**。讲义补了一句关键的例外：**「except when what fails is a data structure invariant」**——不变式失败时，报的是**不变式函数内部**的行号（比如 `is_array_expected_length` 里那句 `//@assert`），**不是**真正出错的地方。**这就是不变式的诊断弱点。**
2. **打印语句**：把数据结构的内容打出来看。

**于是讲义推荐写两个打印函数**：

```c0
void ssa_print_unsafe(ssa* A) {
  int len = A->length;
  printf("SSA length: %d; SSA data: [", len);
  for (int i = 0; i < len; i++)
  //@loop_invariant 0 <= i && i <= len;
  {
    printf(A->data[i]);
    if (i < len-1) printf(", ");
  }
  printf("]");
}

void ssa_print_internal(ssa* A)
//@requires is_ssa(A);
{
  ssa_print_unsafe(A);
}
```

**为什么要两个**：

- **`ssa_print_unsafe` 不检查不变式**。当不变式**本身**出错时（比如你忘了排序、或把不变式写得太严导致合法数据被拒），带检查的版本会直接中止，你什么都看不到。**不带检查的版本才能让你看见「坏数据长什么样」。**
- **`ssa_print_internal` 带前置 `is_ssa(A)`**。当不变式**没**被破坏、但其他契约不够强时（比如 `ssa_set` 把 `x` 写满了整个数组），用这个版本。

**一个容易被忽略的细节**：`ssa_print_unsafe` 用的是**字段**（`A->length`）而**不是接口函数**（`ssa_len(A)`）。讲义解释：**因为我们要用它来抓这些函数自己的 bug**。若打印函数依赖 `ssa_len`，而 `ssa_len` 恰好是错的，打印结果就跟着错，你永远看不到真相。

**最后一条工程建议**：**在实现任何库函数之前，先写 `is_ssa` 与两个打印函数。** 这样你有了「观察工具」再动手。

### 5.13 客户端视角

```c0
void display_this_ssa(ssa_t A)
//@requires A != NULL;
{
  printf("\n");
  for (int j = 0; j < ssa_len(A); j++)
  //@loop_invariant 0 <= j;
  {
    printf("%d => %s\n", j, ssa_get(A, j));
  }
}
```

**三个「不许」**：

1. **不许用字段**（`A->length`、`A->data`）——那是实现细节，换个实现就编译不过。
2. **不许调 `ssa_print_internal`**——它没有被导出。
3. **不许用 `is_ssa`**——它是实现侧的不变式。

**只许用**：`ssa_t` 这个类型名 + 接口导出的四个函数。

**为什么客户端的 `//@loop_invariant` 只写 `0 <= j`**：客户端**不知道** `ssa_len(A)` 在循环中是否变化（接口没承诺它是常量），所以**不能**写 `j <= ssa_len(A)` 这样的不变式。**这是「接口越弱，客户端能写的不变式越弱」的直接体现。**

### 5.14 表示函数与 `pixel_t`：抽象类型的第二种用法

习题 4–6 用像素库演示同一套思路，但接口**故意**不检查 `NULL`：

```c0
struct pixel_as_struct {
  int alpha;   // 0 <= alpha < 256
  int red;     // 0 <= red   < 256
  int green;   // 0 <= green < 256
  int blue;    // 0 <= blue  < 256
};
typedef struct pixel_as_struct pixel;

// typedef ___________ pixel_t;   // Abstract client type

pixel_t make_pixel(int alpha, int red, int green, int blue)
/*@requires 0 <= alpha && alpha < 256; @*/
/*@requires 0 <= red   && red   < 256; @*/
/*@requires 0 <= green && green < 256; @*/
/*@requires 0 <= blue  && blue  < 256; @*/ ;
int get_alpha(pixel_t p) /*@ensures 0 <= \result && \result < 256; @*/ ;
int get_red  (pixel_t p) /*@ensures 0 <= \result && \result < 256; @*/ ;
int get_green(pixel_t p) /*@ensures 0 <= \result && \result < 256; @*/ ;
int get_blue (pixel_t p) /*@ensures 0 <= \result && \result < 256; @*/ ;
```

**为什么接口里没有 `p != NULL`**：讲义说这是为了**与「`pixel_t` 就是 `int`」的旧实现兼容**——`int` 没有 `NULL`。**这是「同一接口、多种实现」的代价**：接口必须弱到能容纳最弱的实现。

**表示函数 `is_pixel`**：

```c0
bool is_pixel(pixel* p) {
  return p != NULL
      && (0 <= p->alpha && p->alpha < 256)
      && (0 <= p->red   && p->red   < 256)
      && (0 <= p->blue  && p->blue  < 256)
      && (0 <= p->green && p->green < 256);
}
```

**`is_pixel` 把 `NULL` 检查也包进去了**——所以库函数写 `//@requires is_pixel(p);` 就同时获得了「非空」与「四个分量都在范围内」两个事实。**这比逐个写五条前置更省事，也更难写漏。**

**`set_` 系列为什么返回新像素而不是原地改**：

```c0
pixel_t set_alpha(pixel_t p, int alpha)
/*@requires 0 <= alpha && alpha < 256; @*/
/*@ensures get_alpha(\result) == alpha; @*/
/*@ensures get_red(\result)   == get_red(p); @*/
/*@ensures get_green(\result) == get_green(p); @*/
/*@ensures get_blue(\result)  == get_blue(p); @*/ ;
```

讲义的理由：**因为 `pixel_t` 可能被实现为 `int`**。若写成 `void set_alpha(pixel_t p, int alpha)` 原地修改，那么在 `pixel_t == int` 的实现下，**修改对调用者不可见**（`int` 是按值传递的）。**返回新值**在两种实现下语义一致。

**这组契约的写法值得学**：它**只用 `get_` 函数**表达「哪一项变了、哪三项没变」。**这就是抽象类型的契约该怎么写——用接口自己的语言说话，不用实现的字段。**

**习题 6 的四个错误**（客户端写了 `void complement_pixel(pixel* p)`）：

1. 用了实现类型 `pixel`，客户端只能用 `pixel_t`。
2. 前置 `p != NULL` 假设像素是指针，**接口从没这么说**。
3. 后置用了 `is_pixel`，**那是实现内部的不变式**。
4. 函数体访问 `p->red`、`p->green`、`p->blue`，**假设了结构体字段的存在**。

**正确写法**：

```c0
pixel_t complement_pixel(pixel_t p) {
  int r = 255 - get_red(p);
  int g = 255 - get_green(p);
  int b = 255 - get_blue(p);
  return make_pixel(get_alpha(p), r, g, b);
}
```

**四条错误全消失了**：只用接口函数、只用抽象类型、不假设任何内部结构。**换实现照样能编译、照样正确**——这就是「尊重接口」的回报。

## 6. 代码示例

### 6.1 官方课程代码

以下引自讲义 PDF `08-libraries.pdf`，语言为 **C0**（不是标准 C/C++）。`//@` 注解、`\length`、`\result`、`alloc`、`alloc_array` 都是 C0 特有语法；`p->f` 箭头运算符虽在 C 里也有，但本讲的类型系统与安全性保证是 C0 独有的。

**（1）结构体声明与默认值，第 2–3 页：**

```c0
struct img_header {
  pixel_t[] data;
  int width;
  int height;
};
```

```c0
--> struct img_header* IMG = alloc(struct img_header);
IMG is 0xFFAFFF20 (struct img_header*)
--> IMG->data;
(default empty int[] with 0 elements)
--> IMG->width;
0 (int)
--> IMG->height;
0 (int)
```

**（2）指针与 NULL，第 5 页：**

```c0
--> int* ptr1 = alloc(int);
ptr1 is 0xFFAFC120 (int*)
--> *ptr1 = 16;
*(ptr1) is 16 (int)
--> int* ptr2 = NULL;
ptr2 is NULL (int*)
--> *ptr2;
Error: null pointer was accessed
Last position: <stdio>:1.1-1.3
```

**（3）`ssa_t` 的完整接口，第 7–8 页：**

```c0
// typedef ______* ssa_t;
int ssa_len(ssa_t A)
/*@requires A != NULL;
@*/
/*@ensures \result >= 0;
@*/ ;
ssa_t ssa_new(int size)
/*@requires 0 <= size;
@*/
/*@ensures \result != NULL;
@*/
/*@ensures ssa_len(\result) == size;
@*/ ;
string ssa_get(ssa_t A, int i)
/*@requires A != NULL;
@*/
/*@requires 0 <= i && i < ssa_len(A);
@*/ ;
void ssa_set(ssa_t A, int i, string x)
/*@requires A != NULL;
@*/
/*@requires 0 <= i && i < ssa_len(A);
@*/ ;
```

**（4）库的表示类型，第 8–9 页：**

```c0
struct ssa_header {
  // Implementation type
  int length;
  string[] data;
};
typedef struct ssa_header ssa;   // Abbreviation
typedef ssa* ssa_t;              // Interface type
```

**（5）数据结构不变式 `is_ssa`，第 10 页：**

```c0
bool is_ssa(ssa* A) {
  return A != NULL
      && is_array_expected_length(A->data, A->length)
      && ssa_sorted(A);
}
```

**（6）`is_array_expected_length`（破例用断言），第 10–11 页：**

```c0
bool is_array_expected_length(string[] A, int length) {
  //@assert \length(A) == length;
  return true;
}
```

**（7）四个库函数，第 11–12 页：**

```c0
int ssa_len(ssa* A)
//@requires is_ssa(A);
//@ensures \result == \length(A->data);
{
  return A->length;
}

string ssa_get(ssa* A, int i)
//@requires is_ssa(A);
//@requires 0 <= i && i < ssa_len(A);
{
  return A->data[i];
}

ssa* ssa_new(int size)
//@requires 0 <= size;
//@ensures is_ssa(\result);
{
  ssa* A = alloc(ssa);
  A->length = size;
  A->data = alloc_array(string, size);
  return A;
}

void ssa_set(ssa* A, int i, string x)
//@requires is_ssa(A);
//@requires 0 <= i && i < ssa_len(A);
//@ensures is_ssa(A);
{
  A->data[i] = x;
  // Move x up the array if needed
  for (int j=i; j < A->length-1 &&
       string_compare(A->data[j],A->data[j+1]) > 0;
       j++)
  //@loop_invariant i <= j && j <= A->length - 1;
    swap(A->data, j, j+1);

  // Move x down the array if needed
  for (int j=i; j > 0 &&
       string_compare(A->data[j],A->data[j-1]) < 0;
       j--)
  //@loop_invariant 0 <= j && j <= i;
    swap(A->data, j, j-1);
}
```

**（8）两个打印函数，第 13–14 页：**

```c0
void ssa_print_unsafe(ssa* A) {
  int len = A->length;
  printf("SSA length: %d; SSA data: [", len);
  for (int i = 0; i < len; i++)
  //@loop_invariant 0 <= i && i <= len;
  {
    printf(A->data[i]);
    if (i < len-1) printf(", ");
  }
  printf("]");
}

void ssa_print_internal(ssa* A)
//@requires is_ssa(A);
{
  ssa_print_unsafe(A);
}
```

**（9）客户端打印函数，第 14–15 页：**

```c0
void display_this_ssa(ssa_t A)
//@requires A != NULL;
{
  printf("\n");
  for (int j = 0; j < ssa_len(A); j++)
  //@loop_invariant 0 <= j;
  {
    printf("%d => %s\n", j, ssa_get(A, j));
  }
}
```

**（10）习题 4 答案：`pixel_t` 库实现，第 23–25 页：**

```c0
bool is_pixel(pixel* p) {
  return p != NULL
      && (0 <= p->alpha && p->alpha < 256)
      && (0 <= p->red   && p->red   < 256)
      && (0 <= p->blue  && p->blue  < 256)
      && (0 <= p->green && p->green < 256);
}

pixel* make_pixel(int alpha, int red, int green, int blue)
//@requires 0 <= alpha && alpha < 256;
//@requires 0 <= red   && red   < 256;
//@requires 0 <= green && green < 256;
//@requires 0 <= blue  && blue  < 256;
//@ensures is_pixel(\result);
{
  pixel* p = alloc(pixel);
  p->alpha = alpha;
  p->red = red;
  p->green = green;
  p->blue = blue;
  return p;
}

int get_alpha(pixel* p)
//@requires is_pixel(p);
//@ensures 0 <= \result && \result < 256;
{
  return p->alpha;
}
```

（`get_red`/`get_green`/`get_blue` 结构相同，最后一行是 `typedef pixel* pixel_t;`）

**（11）习题 5 答案：`set_green` 的实现，第 27 页：**

```c0
pixel* set_green(pixel* p, int green)
//@requires is_pixel(p);
//@requires 0 <= green && green < 256;
//@ensures is_pixel(\result);
//@ensures get_alpha(\result) == get_alpha(p);
//@ensures get_red(\result)   == get_red(p);
//@ensures get_green(\result) == green;
//@ensures get_blue(\result)  == get_blue(p);
{
  return make_pixel(get_alpha(p), get_red(p), green, get_blue(p));
}
```

**（12）习题 1 答案：嵌套结构体，第 20 页：**

```c0
struct address_info {
  string street;
  int zipcode;
  string city;
  string state;
};
typedef struct address_info address;

struct contact_info {
  string name;
  string phone;
  string email;
  address* address;
};
typedef struct contact_info contact;
```

**官方代码包**：`90-原始PDF/15-122/code/08-libraries.tgz`（原始 URL：`https://cs.cmu.edu/~15122/handouts/code/08-libraries.tgz`），含 `ssa` 库的完整实现与 `ssa_sorted`（讲义 p10 说它「can be found in the code accompanying this lecture」）。

### 6.2 Agent 自行编写的教学示例

> **非官方，仅用于说明概念。** 以下由本笔记自行编写，不是 CMU 官方代码，语言为 **C0**。

**示例 A：追踪一次 `ssa_set` 的两个循环。**

`A` 的内容（`ssa_len(A) == 6`）：`["ant", "cat", "dog", "fox", "owl", "yak"]`。执行 `ssa_set(A, 3, "bee")`：

**第一步**：`A->data[3] = "bee"` →

`["ant", "cat", "dog", "bee", "fox", "owl", "yak"]`？**不对，长度是 6**，实际是 `["ant", "cat", "dog", "bee", "owl", "yak"]`（原 `A[3] = "fox"` 被覆盖）。**数组此刻无序**（`"bee" < "dog"`）。

**第二步：第一个循环（往右挪）**。`j = 3`，守卫 `j < 5 && compare(A[3], A[4]) > 0`，即 `compare("bee","owl") > 0`？**假**（`"bee" < "owl"`）。**循环一次都不执行。**

**第三步：第二个循环（往左挪）**。`j = 3`，守卫 `j > 0 && compare(A[3], A[2]) < 0`，即 `compare("bee","dog") < 0`？**真**。

| 迭代 | j | `A[j]` | `A[j-1]` | 比较 | 动作 | 数组 |
|---|---|---|---|---|---|---|
| 1 | 3 | `"bee"` | `"dog"` | `"bee" < "dog"` | `swap(A,3,2)`，`j=2` | `[ant, cat, bee, dog, owl, yak]` |
| 2 | 2 | `"bee"` | `"cat"` | `"bee" < "cat"` | `swap(A,2,1)`，`j=1` | `[ant, bee, cat, dog, owl, yak]` |
| 3 | 1 | `"bee"` | `"ant"` | `"bee" > "ant"` | 守卫失败，退出 | `[ant, bee, cat, dog, owl, yak]` |

**结果**：`ssa_get(A, 3)` 现在返回 **`"dog"`**，不是 `"bee"`。**`"bee"` 跑到了下标 1。** 这直接演示了讲义那句「unlikely that a subsequent call to `ssa_get(A, i)` will return `x`」。

**注意不变式的记账**：第二个循环的不变式 `0 <= j && j <= i` 在 INIT 时是 `0 <= 3 && 3 <= 3`；每轮 `j` 减 1，上界 `j <= i` 自然保持（因为 `j` 只会更小）；下界 `0 <= j` 由守卫 `j > 0` 保证。**这是一条「单调递减但有下界」的标准不变式。**

**示例 B：为什么 `ssa_len` 的后置必须写成 `\result == \length(A->data)`。**

假设我们偷懒，把 `ssa_len` 的后置写成 `\result == A->length`（用字段而不是 `\length`）。那么：

- `ssa_get` 的前置 `i < ssa_len(A)` 展开后是 `i < A->length`。
- 但 `A->data[i]` 的安全需要 `i < \length(A->data)`。
- **`A->length` 与 `\length(A->data)` 是两个不同的量**，验证器无法把前者换成后者。

**这就是 `is_ssa` 里 `is_array_expected_length` 那一项的全部意义**：它把两个量**焊死**。有了它，`ssa_len` 的后置 `\result == \length(A->data)` 才可证；有了那个后置，`ssa_get` 的数组访问才安全。**一条不变式，撑起整条证明链。**

**示例 C：一个「不变式太弱」的 bug。**

假设 `is_ssa` 漏写了 `ssa_sorted(A)`，只保留前两项。那么：

```c0
void ssa_set(ssa* A, int i, string x)
//@requires is_ssa(A);
//@requires 0 <= i && i < ssa_len(A);
//@ensures is_ssa(A);
{
  A->data[i] = x;      // 两个循环都删掉
}
```

**这个版本能通过全部契约检查**——因为 `is_ssa` 不再要求有序，而「长度不变」「非空」都保持。**但客户端拿到的数组已经乱了**，之后用二分查找就会得到错误结果。

**教训**：**不变式太弱 = 契约失去了约束力**。讲义特意把 `ssa_sorted` 单独拿出来称为「correctness invariant」，就是为了提醒：**安全性（不越界、不解空指针）与正确性（数据真的有序）是两件事，不能只做前者。**

**示例 D：客户端版 `ssa_sorted`（只用接口）。**

```c0
bool client_ssa_sorted(ssa_t A)
//@requires A != NULL;
{
  for (int i = 0; i+1 < ssa_len(A); i++)
  //@loop_invariant 0 <= i;
  {
    if (string_compare(ssa_get(A, i), ssa_get(A, i+1)) > 0)
      return false;
  }
  return true;
}
```

**只用 `ssa_len` 与 `ssa_get`**，不碰任何字段。**换一个 `ssa_t` 的实现，这个函数照样编译、照样正确。** 这就是讲义说的「write a client-side version of `ssa_sorted` using only the operations exported by the interface」。

**注意 `i+1 < ssa_len(A)` 而不是 `i < ssa_len(A)-1`**：两者等价，但前者的写法在 `ssa_len(A) == 0` 时不会算出 `-1`。**边界安全的小习惯。**

**示例 E：习题 3 的安全推理，逐行标注理由。**

```c0
1  int main() {
2    int* p = alloc(int);
3    *p = 7;
4    int*[] A = alloc_array(int*, 2);
5    A[0] = p;
6    A[1] = alloc(int);
7    *A[1] = 5;
8    int*[]* B = alloc(int*[]);
9    *B = alloc_array(int*, 2);
10   (*B)[0] = A[1];
11   (*B)[1] = p;
12   return 0;
13 }
```

| 行 | 安全性理由 |
|---|---|
| 2 | **N/A**（`alloc` 不涉及解引用） |
| 3 | 由第 2 行：`p` 是 `alloc(int)` 的结果，非 `NULL` |
| 4 | **N/A** |
| 5 | 由第 4 行：`A` 长度为 2，`0 < 2` 不越界 |
| 6 | 由第 4 行：`1 < 2` 不越界 |
| 7 | 由第 4 行（`A` 长度 2，`A[1]` 存在）**与**第 6 行（`A[1]` 是 `alloc` 的结果，非 `NULL`） |
| 8 | **N/A** |
| 9 | 由第 8 行：`B` 是 `alloc` 的结果，非 `NULL`，故 `*B` 可解引用 |
| 10 | 由第 8 行（`B` 非 `NULL`）、第 9 行（`*B` 长度为 2）、第 4 行（`A` 长度 2，`A[1]` 存在） |
| 11 | 由第 8 行（`B` 非 `NULL`）与第 9 行（`*B` 长度 2） |

**这张表就是「指向式推理（point-to reasoning）」的完整形态**：**每一行都指出「我从哪一行知道它是安全的」**。注意第 7 行与第 10 行都需要**两条**理由——一条给数组下标，一条给指针非空。**「两个解引用叠在一起时，要两个理由」是这类题的核心考点。**

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键区别 | 记忆点 |
|---|---|---|---|
| `struct`（结构体） | `t[]`（数组） | 前者聚合**不同类型**；后者聚合**同一类型** | 图像 = 像素数组 + 宽 + 高 |
| 结构体的值 | 结构体的指针 | C0 **只有**后者能放进变量 | `type struct ... not small` |
| `p->f` | `(*p).f` | 完全等价；后者是「先解引用再取字段」 | 课程一律用 `->` |
| `*p` 的读 | `*p` 的写 | 同一记号，位置决定方向（表达式 / 赋值左侧） | 与 `A[i]` 同理 |
| 有效地址 | `NULL` | 前者由 `alloc` 产生；后者永远不能解引用 | 「指针是地址」不完整 |
| C0 解引用 `NULL` | C 解引用 `NULL` | 前者**必定**报错；后者是**未定义行为** | C0 安全，C 不安全 |
| `ssa_t` 是数组 | `ssa_t` 是指针 | 前者无法实现 `ssa_len`（`\length` 只属于契约） | 由「必须能实现」倒推 |
| `\length(A)` | `A->length` | 前者是**数组原始操作**，只用于契约；后者是**普通字段** | 二者靠不变式焊死 |
| 数据结构不变式 | 循环不变式 | 前者在**函数入口/出口**成立；后者**每轮**成立 | `ssa_set` 中途可以破坏 `is_ssa` |
| 安全性不变式 | 正确性不变式 | 前者防越界/空指针；后者保证数据有序 | `is_ssa` 的两项 vs `ssa_sorted` |
| 库视角 | 客户端视角 | 前者用字段与 `is_ssa`；后者只用接口函数 | 客户端写 `A->length` 即违规 |
| `ssa_print_unsafe` | `ssa_print_internal` | 前者**不查**不变式（用于不变式本身出错时）；后者**查** | 两个都要写 |
| `ssa_set` 后 `ssa_get(A,i)` | 普通数组 `A[i] = x; A[i]` | 前者**不保证**返回 `x` | 抽象类型可以有自己的脾气 |
| `//@requires`（契约） | 函数体里的 `if` | 前者**不产生运行时开销**（除非 `-d`）；后者总是执行 | 契约是给验证器看的 |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-122/lectures/08-libraries.pdf`
- **讲义标题**：PDF 内页标题为 **"Lecture 8: Data Structures"**，作者 Frank Pfenning、André Platzer、Rob Simmons、Iliano Cervesato。**注意：课程目录里本讲名为 "Libraries"，与 PDF 内页标题不一致**（讲义第 1 页明确列出复习幻灯片 "Libraries" 与短视频 "Libraries"，可见「库」是本讲的实际主题）。
- **总页数**：28 页
- **本节重点页码**（PDF 页码，即提取文本中 `=== [page N] ===` 的 N）：
  - 第 1 页：开篇；已有接口（pixels、string bundles）都是**不可变**的；本讲引入**可变**的数据结构接口；两个复习幻灯片链接（Pointers and Structs、Libraries）；代码包；短视频
  - 第 2 页：C0 的五种类型；值 vs 地址；`struct img_header` 声明；字段概念
  - 第 3 页：`not small` 错误与提示；`alloc(struct img_header)`；`p->f` 记号；默认值（空数组 / 0 / 0）
  - 第 4 页：字段赋值；`(*IMG).height`；`(*p).f` 是 `p->f` 的长形式；十六进制像素值
  - 第 5 页：`int*` 指针；`*p` 读/写；`NULL` 与 `Error: null pointer was accessed`；「指针是地址」为何不完整；接地符号
  - 第 6 页：解引用 `NULL` 与数组越界同类；C0 必报错、C 未定义；**解引用必须有非空理由**；靠前置与循环不变式
  - 第 7 页：接下来十讲聚焦数据结构；自排序数组；三个基本操作 `ssa_new`/`ssa_get`/`ssa_set`；第一轮契约（`size >= 0`、`0 <= i`）；需要上界 → 加 `ssa_len`
  - 第 8 页：`\length` 只属于数组；`ssa_t` 不能是 `string[]`；**未知指针类型** `// typedef ______* ssa_t;`；四个函数的完整契约（含 `A != NULL`）
  - 第 9 页：`struct ssa_header`；`typedef struct ssa_header ssa;`；`typedef ssa* ssa_t;`（最后一行）；库内用 `ssa*`；`ssa_len`/`ssa_get` 初版；**越界无法证明**；三行「……」的连锁补丁
  - 第 10 页：客户端无需知情；库侧必须依赖整体一致性；**数据结构不变式**；`is_ssa` 三部分；`is_array_expected_length` 的破例写法
  - 第 11 页：偏好「返回 true/false」胜过「断言失败」；用 `is_ssa` 重写 `ssa_len`/`ssa_get`；`ssa_new` 与 `ssa_set` 的契约；`ssa_new` 实现
  - 第 12 页：`ssa_set` 两个循环的完整代码；`ssa_get` 未必返回刚写入的值；**不变式不属于接口**；客户端可自写 `ssa_sorted`
  - 第 13 页：调试的两条路（契约推理 vs 测试，测试用 `-d`）；契约报错给出确切行号，**但数据结构不变式例外**；打印函数
  - 第 14 页：`ssa_print_unsafe` 完整代码；`ssa_print_internal`；**两个都要写**；用字段而非接口函数的原因
  - 第 15 页：客户端 `display_this_ssa`；用字段或 `ssa_print_internal` 都是违规
  - 第 16–19 页：习题 1–6
  - 第 20–21 页：习题 1 答案（`address_info`/`contact_info`，CMU 联系方式）
  - 第 21–23 页：习题 2 答案（三张内存图，**图本身未被文本提取**）
  - 第 23 页：习题 3 答案（逐行安全性理由表）
  - 第 23–25 页：习题 4 答案（`is_pixel`、`make_pixel`、四个 `get_`、`typedef pixel* pixel_t;`）
  - 第 25–27 页：习题 5 答案（四个 `set_` 的接口与实现）
  - 第 28 页：习题 6 答案（四条错误 + 正确的客户端 `complement_pixel`）
- **原始网页链接**：`https://www.cs.cmu.edu/~15122-archive/f26/handouts/lectures/08-libraries.pdf`
- **配套代码包**：`https://cs.cmu.edu/~15122/handouts/code/08-libraries.tgz`（本库已下载为 `90-原始PDF/15-122/code/08-libraries.tgz`，**未解压**）
- **复习幻灯片**：
  - `https://cs.cmu.edu/~15122/handouts/slides/review/08-pointers.pdf`（本库有提取文本 `_scout/text/15-122__review-slides__08-pointers.pdf.txt`）
  - `https://cs.cmu.edu/~15122/handouts/slides/review/08-library.pdf`（本库**未**收录其提取文本，页码待人工核对）

> **原文异常**：
> 1. **讲义内页标题与课程目录不一致**：PDF 内页写 "Lecture 8: Data Structures"，课程目录与复习材料写 "Libraries"。内容两者都覆盖（前半讲 structs/pointers，后半讲接口设计），但**标题取舍会影响检索**。
> 2. **第 21–23 页习题 2 的三张内存图未被文本提取**（只有图注文字）。答案里说「lines 5, 12, 19」，但第 16 页给出的程序**只有 15 行**（`int main() {` 到 `}`），标注的三处「Memory diagram 1/2/3」注释分别在**第 5、12、19 行**——而程序本身只有 15 行。**疑似程序代码在提取时丢了若干行**（或原 PDF 中该程序含空行/注释行计数方式不同）。**具体行号待人工核对原 PDF 第 16 页。**
> 3. **第 17–18 页习题 4 的 `struct pixel_as_struct` 注释被换行切断**：`// 0 <= red` 与 `< 256` 分在两行，`// 0 <= blue` 与 `< 256` 同理。这是 PDF 排版（注释框宽度）导致，**不是内容错误**，但直接复制会得到语法错误。
> 4. **第 24 页 `is_pixel` 的字段顺序与 `struct` 声明顺序不一致**：声明里是 alpha/red/green/blue，`is_pixel` 检查的是 alpha/red/**blue**/**green**。逻辑上无影响（都是合取），但**说明讲义排版时做过调整**。
> 5. **第 13 页**说「Except sometimes for very large test cases, we always want to run our tests in debug mode (by compiling them with the `-d` flag)」——`-d` 在 C0 里是 `cc0 -d` 的编译选项（见 [[15-122-01-Contracts]]），此处讲义未重复说明。
> 6. **第 1 页列出的短视频** `https://youtu.be/ERGA4PaaUrE`（标题 "Libraries"）**本库未收录**，内容与可用性**待人工核对**。

## 9. 对应视频

未找到官方公开录像。**补充说明**：讲义第 1 页确实列出了一个短视频链接 `https://youtu.be/ERGA4PaaUrE`（标题 "Libraries"），但本库未收录该视频，其内容与可用性待人工核对；除此之外本讲没有完整的公开课堂录像。

建议的动手顺序：(1) 在 `coin` 里逐条敲 5.2 与 5.3 的会话，观察 `not small` 错误与 `null pointer was accessed` 错误；(2) 手工实现 `ssa_new`/`ssa_len`/`ssa_get`/`ssa_set`，**先只写 `A != NULL` 的前置**，用 `cc0 -d` 编译，观察 `ssa_get` 里 `A->data[i]` 的越界警告；(3) 加上 `is_ssa` 与 `is_array_expected_length`，再编译，观察警告消失；(4) 故意删掉 `ssa_set` 的两个循环，看 `is_ssa(A)` 这条后置在哪一行失败；(5) 用 `ssa_print_unsafe` 打印「坏数据」，体会为什么需要一个不查不变式的打印函数。

## 10. 本节复习

1. C0 五种类型：`int`、`bool`、`char`、`string`、`t[]`；前三者存**值**，后两者存**地址**。
2. 结构体聚合**不同类型**，数组聚合**同一类型**。
3. 结构体**不能作局部变量**（`type struct ... not small`），只能 `alloc` 在堆上，手里永远只有指针。
4. `p->f` 等价于 `(*p).f`；括号不可省。
5. 指针值是地址，地址分**有效**（`alloc` 产生）与**无效**（`NULL`）；解引用前必须有非空理由，靠前置或循环不变式。
6. 解引用 `NULL` 在 C0 必报错，在 C 是未定义行为。
7. `ssa_t` 的三个基本操作对应 `alloc_array`/`A[i]`/`A[i] = x`；**必须**再加 `ssa_len`，因为 `\length` 只属于 C0 数组。
8. `ssa_t` 不能是 `string[]`（否则 `ssa_len` 无法实现），故是**未知指针类型**：`// typedef ______* ssa_t;`。
9. 库的表示类型：`struct ssa_header { int length; string[] data; };` + `typedef struct ssa_header ssa;` + `typedef ssa* ssa_t;`（**最后一行**）。
10. `is_ssa(A)` = `A != NULL` && `\length(A->data) == A->length` && `ssa_sorted(A)`；前两项管**安全**，第三项管**正确**。
11. 前置补丁链：`ssa_len` 要后置 `\result == \length(A->data)` → 需前置 `A->length == \length(A->data)` → `ssa_get` 里调 `ssa_len` 也要这条前置。
12. 创建型函数把不变式写进**后置**；修改型函数保证不变式**返回时仍成立**。
13. `ssa_set` 写入后可能往左或往右挪（两个循环，只有一个会跑）；**之后 `ssa_get(A,i)` 未必返回 `x`**。
14. **不变式不属于接口**；客户端可自写客户端版 `ssa_sorted`（只用 `ssa_len` 与 `ssa_get`）。
15. 调试两条路：契约推理 + 测试（用 `-d`）；找 bug 两条路：契约报错行号（**数据结构不变式例外**）+ 打印。
16. 写**两个**打印函数：`ssa_print_unsafe`（不查不变式）与 `ssa_print_internal`（查）；**先写不变式与打印函数，再实现库函数**。
17. 客户端**只许**用接口：不许碰字段、不许调 `ssa_print_internal`、不许用 `is_ssa`。
18. `set_` 系列返回**新**像素而不是原地改，因为 `pixel_t` 可能被实现为 `int`（按值传递，原地改不可见）。

## 11. 自我检查

**题 1.** 解释为什么 `struct img_header IMG;` 会报 `type struct img_header not small`，而 `struct img_header* IMG = alloc(struct img_header);` 不会。为什么讲义说「即使结构体碰巧小于 32 位也不行」？

**题 2.** 为什么必须往 `ssa_t` 的接口里加 `ssa_len`？如果不加，`ssa_get` 的契约会缺什么？由此如何推出 `ssa_t` 必须是**指针类型**？

**题 3.** 已知 `is_ssa(A)` 成立、`0 <= i && i < ssa_len(A)` 成立。逐步证明 `A->data[i]` 不越界。**每一步要说明用了哪条契约。**

**题 4.** 对 `A = ["ant", "cat", "dog", "fox", "owl", "yak"]`（长度 6）执行 `ssa_set(A, 4, "emu")`。写出每次交换后的数组、两个循环各执行几轮、最终 `"emu"` 落在哪个下标。

**题 5.** 下面这个客户端函数有哪几处违反接口？

```c0
void show(ssa_t A) {
  for (int i = 0; i < A->length; i++)
    printf("%s\n", A->data[i]);
}
```

<details>
<summary>参考答案</summary>

**答 1.** C0 规定**只有「小类型」（最多 64 位，与地址等宽）才能放进变量、传参、返回**。`int`、`bool`、`char`、`string`、`t[]` 都是小类型（数组变量存的是地址，也是 32 或 64 位）。结构体由**多个字段**组成，总大小可能远超 64 位，所以被排除。`alloc(struct img_header)` 返回的是**指针**——指针永远是 32 或 64 位，**小类型**，所以能放进变量。

**「即使碰巧小于 32 位也不行」**：这是**语言规则**而非优化判断。原因有两点：(1) 若允许小结构体作局部变量、大结构体不行，程序员就要记住「哪些结构体够小」，规则变得依赖实现；(2) 结构体的**大小可以随实现改变**（加一个字段就变了），若代码依赖「它够小」，加字段就会突然编译失败。**统一禁止**让规则简单且稳定。讲义原文：「This is true even if they happen to be small enough to fit into 32 bits.」

**答 2.** `ssa_get` 的契约必须有**上界** `i < 长度`，否则客户端传 `i = 100` 给长度 12 的数组就没人拦，`A->data[i]` 会越界。但 `\length` 是 **C0 数组的原始操作**，只对 `t[]` 有效，对抽象类型 `ssa_t` 不可用。**所以长度必须由接口函数 `ssa_len` 提供。**

**由此推出 `ssa_t` 是指针**：假如 `ssa_t` 就是 `string[]`，那 `ssa_len` 的实现只能是 `return \length(A);`——但 `\length` **只能出现在契约里**，不能当普通表达式用。**故 `ssa_t` 不能是数组**。既然不是数组，又要能「装下长度和数组」，唯一的选择是**指向某个结构体的指针**。讲义的说法是：`ssa_t` 是「unknown **pointer** type」，写成 `// typedef ______* ssa_t;`。

**答 3.** 逐步证明：

1. **`is_ssa(A)` 成立** → 展开定义得 `A != NULL`、`is_array_expected_length(A->data, A->length)`、`ssa_sorted(A)` 三者都成立。
2. **`A != NULL`** → `A->length` 与 `A->data` 的解引用**安全**（不会 null pointer）。
3. **`is_array_expected_length(A->data, A->length)`** → 其内部 `//@assert \length(A->data) == A->length` 通过，**故 `\length(A->data) == A->length`**。
4. **调用 `ssa_len(A)`**：其前置是 `is_ssa(A)`，**由第 1 步满足**，故调用合法。
5. **`ssa_len` 的后置** `\result == \length(A->data)` → 得 `ssa_len(A) == \length(A->data)`。
6. **前置 `0 <= i && i < ssa_len(A)`** 与第 5 步代入 → **`0 <= i && i < \length(A->data)`**。
7. **这正是 C0 数组访问的安全条件**（见 [[15-122-03-Arrays]]），故 `A->data[i]` **不越界**。

**这条链的关键在第 3 步与第 5 步**：`is_array_expected_length` 把 `A->length` 与 `\length(A->data)` 焊死，`ssa_len` 的后置把返回值与 `\length(A->data)` 焊死。**两处焊接，缺一不可。** 若 `is_ssa` 少了那一项（见 6.2 示例 B），第 3 步就断，整条链失效。

**答 4.** `ssa_set(A, 4, "emu")`：`A->data[4] = "emu"` →

`["ant", "cat", "dog", "fox", "emu", "yak"]`。原 `A[4] = "owl"` 被覆盖。此时 `"emu" < "fox"`，**无序**。

**第一个循环（往右）**：`j = 4`，守卫 `4 < 5 && compare(A[4], A[5]) > 0` = `compare("emu","yak") > 0`？**假**（`"emu" < "yak"`）。**0 轮。**

**第二个循环（往左）**：`j = 4`，守卫 `4 > 0 && compare(A[4], A[3]) < 0` = `compare("emu","fox") < 0`？**真**。

| 迭代 | j | 比较 | 动作 | 数组 |
|---|---|---|---|---|
| 1 | 4 | `"emu" < "fox"` | `swap(A,4,3)`，`j=3` | `[ant, cat, dog, emu, fox, yak]` |
| 2 | 3 | `"emu" < "dog"` | `swap(A,3,2)`，`j=2` | `[ant, cat, emu, dog, fox, yak]` |
| 3 | 2 | `"emu" > "cat"` | 守卫失败，退出 | `[ant, cat, emu, dog, fox, yak]` |

**`"emu"` 最终在下标 2**，第二个循环跑了 **2 轮**，第一个循环 **0 轮**。

**验证**：`ssa_get(A, 4)` 现在返回 `"fox"`（不是 `"emu"`），`ssa_get(A, 2)` 返回 `"emu"`。数组 `[ant, cat, emu, dog, fox, yak]` **有序**——`is_ssa(A)` 重建成功。

**答 5.** 三处违规，全部源于**把库内部的东西当成客户端可用的**：

1. **`A->length`**：`ssa_t` 是**抽象类型**，客户端不知道它有任何字段。`->` 要求左侧是指向结构体的指针，而客户端手里的 `ssa_t` 是个「未知指针类型」——**没有字段可访问**。正确写法是 `ssa_len(A)`。**这是最严重的一处：换个实现（比如把 `ssa_t` 定义成别的结构体）这段代码直接编译失败。**
2. **`A->data[i]`**：同上，`data` 也是实现细节。正确写法是 `ssa_get(A, i)`。
3. **缺少契约**：`ssa_len` 与 `ssa_get` 的前置都有 `A != NULL`（`ssa_get` 还有下标范围）。虽然循环条件 `i < ssa_len(A)` 恰好给了下标范围，但**函数本身没有前置声明 `A != NULL`**，因此**无法证明 `ssa_len(A)` 的调用是安全的**。正确写法是加 `//@requires A != NULL;`（或更强的不变式，但客户端没有 `is_ssa` 可用）。

**正确版本**：

```c0
void show(ssa_t A)
//@requires A != NULL;
{
  for (int i = 0; i < ssa_len(A); i++)
  //@loop_invariant 0 <= i;
  {
    printf("%s\n", ssa_get(A, i));
  }
}
```

**注意循环不变式只能写 `0 <= i`**：客户端不知道 `ssa_len(A)` 在循环中是否恒定（接口没承诺），所以不能写 `i <= ssa_len(A)`。**这正是「接口弱 → 客户端能写的不变式也弱」的具体表现**（对比 6.1 第 9 项官方 `display_this_ssa`，写法完全相同）。

</details>

## 12. 进一步学习

- 上一讲：[[15-122-07-Quicksort]] —— `is_sorted`、`swap`、`ge_seg`/`le_seg` 这些规格函数；本讲的 `is_ssa` 是同一类「规格函数」，但用于**整个数据结构**而非单个数组。
- 上一讲（数组基础）：[[15-122-03-Arrays]] —— `alloc_array`、`\length`、越界错误；本讲解释了**为什么 `\length` 不能用在抽象类型上**。
- 下一讲：[[15-122-09-Stacks-and-Queues]] —— 用同样的「接口 + 表示类型 + 数据结构不变式」套路，实现栈与队列两个抽象类型。
- 后续讲次：[[15-122-10-Linked-Lists]] —— 用指针把元素串起来，`NULL` 从「错误值」变成「链表结束标记」；[[15-122-11-Unbounded-Arrays]] —— 让「固定长度」这个限制消失；[[15-122-12-Hashing]]、[[15-122-13-Hash-Dictionaries]] —— 另一个抽象类型（字典）与它的实现。
- 课程入口：[[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]]、[[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 术语查询：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Struct、Field、Pointer、Dereference、NULL、Abstract Type、Interface、Data Structure Invariant、Representation Type、Client、Library、Encapsulation 等条目）。
- 延伸阅读：John C. Reynolds 的 "Separation Logic: A Logic for Shared Mutable Data Structures"（2002）——把「指向式推理」形式化为可组合的逻辑；本讲的 `is_ssa` 是它在 C0 里的轻量版本。
