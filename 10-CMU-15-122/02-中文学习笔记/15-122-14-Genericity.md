---
course: CMU 15-122
course_name: Imperative Computation
semester: Fall 2026
lecture_id: L14
topic: Genericity
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-122
  - 泛型
  - 函数指针
  - C1
---

# 第 14 讲：泛型（Genericity）

## 1. 本节学习目标

学完本讲后，你应该能够：

1. 解释 Generic Data Structure（泛型数据结构）的含义，并说明为什么用 `typedef void* elem;` 就能让一份队列代码服务任意元素类型。
2. 说清 Void Pointer（void 指针，`void*`）的两条铁律：可以隐式接收任意对象指针、可以显式转回原类型；但**不能解引用**，因为 `void` 不是一个完整的类型。
3. 用 `\hastag(type, p)` 在契约里表达「这个 void 指针指向的确实是 type 类型的对象」，并解释为什么 NULL 对任何类型都满足 `\hastag`。
4. 画出 C1 的五段 Memory Model（内存模型）：OS、Stack、Heap、DATA、TEXT，并说明每一段的方向、权限与典型内容。
5. 用「写原型 → 前置 `typedef` → 把函数名换成类型名」三步法为任意函数定义 Function Pointer Type（函数指针类型），并写出 `typedef int hash_string_fn(string s);` 与 `hash_string_fn* F = &hash_string;`。
6. 说明泛型哈希字典为什么要多存三个函数指针（`key`、`hash`、`equiv`），以及这如何体现「对象 = 数据 + 方法」的思想。

## 2. 前置知识

- 前序讲次：[[15-122-09-Stacks-and-Queues]]（队列接口与 `typedef` 的用法）、[[15-122-13-Hash-Dictionaries]]（哈希字典的接口与探测策略）。课程入口见 [[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]] 与 [[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 需要熟悉 C0 的 `typedef` 两种用法：`typedef int elem;`（类型别名）与 `typedef struct queue_header* queue_t;`（指针别名）。
- 需要知道 C0 的 `alloc(type)` 与 `alloc_array(type, n)` 分别分配一个对象与一个数组。
- 需要理解「结构体字段本身没有名字，只有类型」——这是后面函数指针必须写 `*` 的根本原因。
- 术语统一以 [[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]] 为准。

> **语言边界提醒**：本讲仍属于前九周的 **C0 家族**，具体说是 **C1**（文件扩展名 `.c1`，用 `cc0` 编译）。C1 是 C0 的扩展，仍然有垃圾回收、仍然有 `//@` 契约注解。**它不是标准 C。** 标准 C 从第 17 讲才开始，那之后才有 `malloc`/`free`、才有预处理器。本讲出现的 `void*` 与函数指针是 C1 新增的两个特性，而标准 C 里它们同样存在但语义细节不同（例如标准 C 中 `void*` 可以隐式转成任何对象指针，C1 要求显式强转）。

## 3. 核心概念

**Genericity（泛型）**：让同一份数据结构代码服务于多种元素类型的能力。C0 的做法不是像 Java 那样引入类型参数，而是把所有元素统一「擦除」成一个万能指针类型 `void*`，在接口边界上用 `typedef void* elem;` 起个别名。

**Void Pointer（void 指针）**：`void*` 是「指向某个对象，但我不知道也不关心它是什么类型」的指针。它是 C0/C1 里唯一的「万能指针」。

**Tag（类型标签）**：C1 在运行时给每个非 NULL 的 `void*` 附带一个隐藏的类型标签，记录它原本指向什么类型。强转回错误类型就是 Safety Violation（安全性违规），`-d` 模式下会报错。

**`\hastag(type, p)`**：契约语言里的谓词，读作「指针 `p` 带的标签与 `type` 一致」。它是唯一能在契约里表达「这个 void 指针的原始类型」的工具。

**Function Pointer（函数指针）**：指向函数代码的指针。在 C1 中，函数名 `f` 求值得到的是函数代码的地址，类型是「函数类型」；要声明一个能存这个地址的变量，必须用「函数指针类型」，也就是在函数类型后加 `*`。

**Memory Model（内存模型）**：把进程地址空间划分为若干语义不同的段，规定每段存什么、能否写、增长方向。C1 的模型有五段。

**Higher-order Function（高阶函数）**：接受函数作为参数、或返回函数的函数。C1 借助函数指针第一次能写出真正的高阶函数，例如 `compose`、`pipeline`。

**Callback（回调）**：把「将来要调用的函数」作为参数传进去。泛型哈希字典里的 `hash`、`equiv`、`key` 都是回调。

## 4. 通俗理解

把泛型想成**快递柜**。

- 快递柜的格子不关心你放的是书、衣服还是水果，它只认「这是一个包裹」。这就是 `void*`：柜子只存地址，不存类型知识。
- 但你取件时必须知道「我这个格子里放的是书」，才能正确拆包。这就是**强转回原类型**：`(book*)p`。如果你记错了，把装衣服的格子当书拆，就会拆坏东西——这就是 tag 不匹配导致的 safety violation。
- 柜子本身**不能**替你「打开看看里面是什么」：它没有这个能力，因为「打开」这个动作必须知道包裹的结构。这就是 `void*` 不能解引用。
- 快递柜的管理系统里还存着「这格子的主人是谁、超时怎么计费、坏了找谁修」——这些就是存在 `hdict_header` 里的三个函数指针：它们是随数据一起携带的「操作说明」。

## 5. 原理与推导

### 5.1 为什么 `typedef void* elem;` 就够泛型了

先看非泛型的队列。假设元素是整数：

```c0
typedef int elem;
typedef struct queue_header* queue_t;
void enq(queue_t Q, elem x);
elem deq(queue_t Q);
```

队列实现里对 `elem` 做了什么？只有两件事：把 `x` 存进链表节点、把节点里的值取出来返回。**它从不读 elem 的内部结构**——不比较、不运算、不取字段。也就是说，队列对 elem 的唯一要求是「能被存进一个字段、能被取出来」。

任何对象指针都满足这个要求。于是把 `typedef int elem;` 换成 `typedef void* elem;`，实现代码一行不改就能编译通过。这就是泛型的全部秘密：**队列只搬运地址，不解释内容**。

### 5.2 为什么 `void*` 不能解引用

`*p` 的语义是「取出 `p` 指向的那个对象的**值**」。要取出值，编译器必须知道两件事：

1. 这个对象占几个字节；
2. 这几个字节怎么解释（整数？浮点？指针？结构体？）。

`void` 恰好表示「没有类型信息」，所以这两件事编译器都不知道。`*p1`（`p1` 类型为 `void*`）在 C1 中是**类型错误**，不是运行时错误。要取出内容，必须先告诉编译器类型：

```c1
int* p2 = (int*)p1;   /* 现在编译器知道：4 字节，按 int 解释 */
int  x  = *p2;        /* 合法 */
```

顺带一提：C1 甚至不允许声明 `void x;` 这样的变量，因为「void 类型的对象」在概念上不存在。

### 5.3 tag 与 `\hastag`：把类型信息带到运行时

强转在 C1 中是「有据可查」的：每个非 NULL 的 `void*` 都带一个 tag。所以下面这段代码是安全的：

```c1
//@assert \hastag(int*, p1);
int* p2 = (int*)p1;
```

而下面这段在 `-d` 下会失败：

```c1
//@assert \hastag(char*, p1);   /* p1 实际指向 int，tag 不符 */
```

两个要点：

1. **NULL 对任何类型都满足 `\hastag`。** 因为 NULL 不指向任何对象，谈不上「指向的类型错了」。这带来一个契约写法上的便利：写 `//@assert \hastag(t, p);` 时不必先排除 `p == NULL`。
2. `\hastag` 是**契约专用**谓词，不能写进普通代码当表达式用。它和 `\length`、`\result` 同属「只有契约检查器认识」的词汇。

### 5.4 五段内存模型

C1 把地址空间划成五段（`14-generic.pdf` 第 8 页 Figure 1）：

| 段 | 位置 | 增长方向 | 可写 | 存什么 |
|---|---|---|---|---|
| OS | 两端（低地址 0x0 与高地址） | — | 否 | 操作系统保留；地址 0x0 就是 NULL，解引用它属于 safety violation |
| Stack | 中部偏上 | **向下** | 是 | 局部变量（C0 里叫 local memory） |
| Heap | 中部偏下 | **向上** | 是 | `alloc` 分配的对象（C0 里叫 allocated memory） |
| DATA | 底部 | — | 否（只读） | 字符串字面量 |
| TEXT | 底部 | — | 否（只读） | 编译后的机器码，函数指针指向这里 |

三条推论：

1. Stack 向下、Heap 向上，两者相向生长，中间是未分配的空隙。空隙被吃光时就是 Stack Overflow（栈溢出）。
2. DATA 与 TEXT 只读。往字符串字面量里写字节会触发 safety violation——这一点在第 18 讲会以「标准 C 的 undefined behavior」的形式再次出现。
3. 地址是 64 位的，所以指针统一 8 字节。这也是为什么 `void*` 能容纳任何对象指针。

### 5.5 函数类型与函数指针类型：三步法

C1 里最容易写错的就是函数指针的 `*`。用三步法可以机械地推出正确写法。

**第一步：写出函数原型。**

```c1
int hash_string(string s);
```

**第二步：把函数名换成一个类型名，得到「函数类型」。**

```c1
typedef int hash_string_fn(string s);
```

注意：`hash_string_fn` 是**函数类型**，不是指针类型。它的值是「一段代码」，不是一个地址变量。

**第三步：需要变量时，加 `*` 得到「函数指针类型」。**

```c1
hash_string_fn* F = &hash_string;
```

这里有两个必须记住的细节：

- **`*` 不能省。** `hash_string_fn F = &hash_string;` 是类型错误，因为 `F` 会变成一个「函数类型的变量」，而函数类型的变量在 C1 中不允许存在（函数不是可以赋值的对象）。
- **`&` 不能省。** C1 中 `&` 只能作用于函数名（不能取局部变量地址，那是标准 C 才有的能力，见第 18 讲）。`&hash_string` 的值是 TEXT 段里的一个地址。

调用时括号也必须写：

```c1
int h = (*F)("hello");   /* 正确 */
int h = *F("hello");     /* 错误：先调用 F 再解引用 */
```

`*F` 的优先级低于函数调用，所以 `*F("hello")` 会被解析成 `*(F("hello"))`。加上括号是为了强制先解引用。

### 5.6 泛型哈希字典：把「方法」和数据放在一起

第 11 讲的哈希字典有一个硬编码的假设：元素的 key 是字符串、哈希函数是 `key_hash`、相等判断是 `key_equiv`。这让字典只能存一种元素。

要泛型化，需要把这三个「方法」变成客户端提供的回调，存进 header：

```c1
struct hdict_header {
  int size;            /* 桶数组长度，> 0 */
  int capacity;        /* 已存条目数，>= 0 */
  chain** table;       /* \length(table) == size */
  entry_key_fn*    key;    /* != NULL */
  key_hash_fn*     hash;   /* != NULL */
  key_equiv_fn*    equiv;  /* != NULL */
};
```

构造时由客户端传入：

```c1
hdict_t hdict_new(int capacity,
                  entry_key_fn* entry_key,
                  key_hash_fn* hash,
                  key_equiv_fn* equiv)
/*@requires capacity > 0;
  @requires entry_key != NULL && hash != NULL && equiv != NULL;
  @ensures \result != NULL;
  @*/ ;
```

实现内部原本直接调 `key_equiv(H, x, y)`，现在要经 `H->equiv` 调用：

```c1
bool key_equiv(hdict_t H, entry x, key k)
{
  return (*H->equiv)(H->key(x), k);
}
```

**为什么还要保留一个同名 helper `key_equiv`？** 因为字典内部有十几处调用点，如果每处都写成 `(*H->equiv)(H->key(x), k)`，代码会变得难以阅读，而且一旦以后要改调用约定就得改十几处。用一个 helper 把「经函数指针调用」这件事封在一处，其余代码仍然写 `key_equiv(H, x, k)`，可读性与可维护性都保住了。

**一个契约上的副作用**：接口里原本有一条后置条件提到内部函数，但内部函数不能出现在接口契约中（客户端看不见它们）。所以这条后置条件被删掉，接口只剩 `/*@requires H != NULL; @*/`。这是「抽象」的代价：**暴露得越少，能写进契约的就越少**。

这件事的思想意义值得强调：`struct hdict_header` 现在同时装了**数据**（`size`、`capacity`、`table`）和**操作**（`key`、`hash`、`equiv`）。这正是面向对象里「对象 = 数据 + 方法」的雏形。区别只在于：C1 用函数指针手工实现「方法表」，而面向语言把这个机制内置了。

### 5.7 习题里的三个典型用法

**Ex1（`14-generic.pdf` 第 13 页，解在第 16 页）**：给 `genlist` 加一个 `type` 字段，写 `genlist_print`。核心是先用 `\hastag` 断言元素确实是声明的类型，再强转后打印。

**Ex2（第 13–14 页，解在第 16–17 页）**：定义 `typedef int int2int_fn(int x);`，实现

```c1
int compose(int2int_fn* f, int2int_fn* g, int x) {
  return (*f)((*g)(x));
}
```

以及 `pipeline`，它接受一个函数指针数组，依次作用。`pipeline` 里要断言 `F[i] != NULL`，否则会在运行时解引用空指针。

**Ex3（第 14–15 页，解在第 17 页）**：用 `void*` 实现「一个字段存两种客户类型」的 union 式写法。取用时 `((eggs*)(customers[0]->breakfast))->num`——两层括号：外层是强转，内层是取字段。

## 6. 代码示例

### 6.1 官方课程代码

以下代码出自 `14-generic.pdf`，页码为该 PDF 的页码。

**（1）泛型队列的客户端接口**（第 3 页）

```c0
/* Client interface for queues */
typedef void* elem;
```

只有这一行改动，队列库就变成了泛型库。第 3 页同时说明：`void*` 只能用于「转回原类型」这一种强转，不能解引用。

**（2）C1 内存模型图**（第 7 页 Figure 1，正文第 6–8 页讨论）

五段布局与增长方向见 5.4 节的表格。讲义强调：地址 0x0 属于 OS 段，它就是 NULL 的地址；Stack 与 Heap 相向生长。

**（3）函数指针类型与变量**（第 8–9 页）

```c1
typedef int hash_string_fn(string s);
hash_string_fn* F = &hash_string;
int h = (*F)("hello");
```

第 9 页明确指出：`hash_string_fn F = &hash_string;` 是**非法**的，`*` 不可省。

**（4）泛型哈希字典的 header 与构造**（第 10–12 页）

`struct hdict_header` 增加 `entry_key_fn* key`、`key_hash_fn* hash`、`key_equiv_fn* equiv` 三个字段，构造函数 `hdict_new` 多收三个参数，实现里通过 `H->equiv` 调用。第 12 页给出 helper `key_equiv` 的写法与「接口后置条件被删除」的说明。

**（5）习题 Ex1–Ex3 与参考答案**（第 13–15 页为题目，第 16–17 页为答案）

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念

下面这个例子演示「同一份泛型栈服务三种元素类型」，并展示 `\hastag` 断言的位置。

```c1
/* 客户端接口：元素类型擦除成 void* */
typedef void* elem;

typedef struct stack_header* stack_t;

stack_t stack_new();
/*@ensures \result != NULL; @*/

void push(stack_t S, elem x);
/*@requires S != NULL; @*/

elem pop(stack_t S);
/*@requires S != NULL && !stack_empty(S); @*/
```

三种客户端各自定义自己的元素类型，互不干扰：

```c1
/* 客户端 A：整数 */
typedef struct intcell { int value; } intcell;
intcell* mk_int(int v) {
  intcell* p = alloc(intcell);
  p->value = v;
  return p;
}
/* 使用：push(S, (elem)mk_int(42)); */

/* 客户端 B：字符串（C0 里 string 就是 char*） */
/* 使用：push(S, (elem)"hello"); */

/* 客户端 C：点 */
typedef struct point { int x; int y; } point;
point* mk_point(int x, int y) {
  point* p = alloc(point);
  p->x = x; p->y = y;
  return p;
}
```

取回时必须**先断言、再强转**：

```c1
elem e = pop(S);
//@assert \hastag(intcell*, e);
intcell* c = (intcell*)e;
int v = c->value;      /* 现在解引用是安全的 */
```

如果写成 `//@assert \hastag(point*, e);`，`-d` 模式下会立刻报错——因为 `e` 的 tag 是 `intcell*`。这就是 tag 的价值：**它把「类型记错」从「运行时读到垃圾」变成「一条可定位的断言失败」。**

再看一个高阶函数的例子，用函数指针实现「对数组每个元素做变换」：

```c1
typedef int int2int_fn(int x);

void map_array(int[] A, int n, int2int_fn* f)
/*@requires A != NULL && \length(A) >= n && n >= 0;
  @requires f != NULL;
  @*/ 
{
  for (int i = 0; i < n; i++)
  //@loop_invariant 0 <= i && i <= n;
  {
    A[i] = (*f)(A[i]);
  }
}
```

调用 `map_array(A, n, &square)` 就把每个元素平方，调用 `map_array(A, n, &negate)` 就取反。**同一份循环代码，行为由传入的函数决定**——这是泛型在「算法」层面的体现，与 `void*` 在「数据」层面的泛型是同一个思想的两个方向。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键区别 | 记忆点 |
|---|---|---|---|
| `void*`（万能指针） | `int*`（具体指针） | 前者无类型信息、不能解引用；后者知道元素大小与解释方式、可以解引用 | 「地址 vs 地址+说明书」 |
| 强转 `(int*)p` | 解引用 `*p` | 强转只改变「编译器如何看待这块内存」，不访问内存；解引用真的读写内存 | 「换个眼镜」vs「真的去看」 |
| 函数类型 `hash_string_fn` | 函数指针类型 `hash_string_fn*` | 前者描述「函数长什么样」，不能声明变量；后者是地址类型，可以声明变量 | 「图纸 vs 门牌号」 |
| `&f`（取函数地址） | `&x`（取变量地址） | C1 中 `&` 只能作用于函数名；标准 C 才允许取任意对象地址（第 18 讲） | **C1 限制** |
| `(*F)(x)` | `*F(x)` | 前者先解引用再调用；后者先调用再解引用，类型错误 | 「括号定生死」 |
| `\hastag(t, p)` | `p != NULL` | 前者检查类型标签，后者只检查非空；NULL 对任何 `t` 都满足 `\hastag` | 「类型对不对 vs 有没有」 |
| C1（本讲） | 标准 C（第 17 讲起） | C1 有垃圾回收、有 `//@` 契约、`&` 只能取函数地址；标准 C 要 `malloc`/`free`、契约变成宏 | **本讲是 C1，不是 C** |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-122/lectures/14-generic.pdf`
- **总页数**：17 页
- **本节重点页码**（PDF 页码，即提取文本中 `=== [page N] ===` 的 N）：
  - 第 3 页：`typedef void* elem;` 与 void 指针的第一条铁律
  - 第 4 页：泛型数据结构的第二次尝试
  - 第 5–6 页：走向泛型哈希字典、`\hastag` 的引入
  - 第 6–8 页：C1 内存模型（Figure 1 在第 7 页）
  - 第 8–9 页：函数指针的语法与调用
  - 第 10–12 页：泛型哈希字典的完整实现（三字段 header、`hdict_new`、`key_equiv` helper）
  - 第 13–15 页：习题 Ex1（genlist 打印）、Ex2（compose/pipeline）、Ex3（union 式 void*）
  - 第 16–17 页：参考答案
- **配套复习幻灯片**：`90-原始PDF/15-122/review-slides/14-fpointer.pdf`（25 页）。第 2–12 页精化五段内存模型（TEXT/DATA/STACK/HEAP/OS，Stack 向下、Heap 向上，相撞即 Stack Overflow）；第 13–16 页对比 C0 与 C1 可用地址；第 17 页说明 `&key_hash` 返回 TEXT 段地址；第 19–21 页给出函数类型定义的三步法；第 22–25 页是 `string_to_int_fn* F = &key_hash;`、`int h = (*F)("hello");`、以及 `&f` 永不为 NULL 的安全性契约 `//@ensures \result != NULL;`。
- **原始网页链接**：`https://www.cs.cmu.edu/~15122-archive/f26/handouts/lectures/14-generic.pdf`
- **配套代码包**：`90-原始PDF/15-122/code/14-generic.tgz`

## 9. 对应视频

未找到官方公开录像。本讲可配合讲义 PDF 与 `14-fpointer.pdf` 复习幻灯片自学；函数指针部分建议边看第 19–21 页的三步法边自己动手写一遍 `typedef`。

## 10. 本节复习

1. 泛型的核心手段是**类型擦除**：把具体元素类型统一成 `void*`，接口用 `typedef void* elem;` 起别名。队列之所以能泛型，是因为它从不解释元素内容，只搬运地址。
2. `void*` 可以隐式接收任意对象指针、可以显式强转回原类型，但**不能解引用**，因为 `void` 不提供大小与解释方式。
3. 非 NULL 的 `void*` 在 C1 中带运行时 tag；强转错类型是 safety violation。`\hastag(t, p)` 是契约里检查 tag 的唯一工具，NULL 对任何 `t` 都满足它。
4. C1 内存模型五段：OS（两端，含地址 0x0 = NULL）、Stack（向下）、Heap（向上）、DATA（字符串字面量，只读）、TEXT（代码，只读）。Stack 与 Heap 相撞即栈溢出。
5. 函数类型三步法：写原型 → `typedef` 换掉函数名 → 变量声明时加 `*`。`*` 与 `&` 都不能省，调用时 `(*F)(x)` 的括号也不能省。
6. 泛型哈希字典把 `key`、`hash`、`equiv` 三个回调存进 header，实现里经 `H->equiv` 调用，并用 helper 保持可读性。这是「对象 = 数据 + 方法」的雏形。
7. 抽象有代价：内部函数不能出现在接口契约里，所以部分后置条件必须删除，接口只剩 `/*@requires H != NULL; @*/`。
8. **本讲是 C1，不是标准 C。** C1 仍有垃圾回收与 `//@` 契约；`&` 在 C1 只能作用于函数名。

## 11. 自我检查

**题 1.** 下面三段代码哪些能通过 C1 类型检查？对不能通过的，说明原因。

```c1
void* p = alloc(int);
int a = *p;                    /* (A) */

void* q = alloc(int);
int* r = (int*)q;
int b = *r;                    /* (B) */

void* s = NULL;
//@assert \hastag(string, s);   /* (C) */
```

**题 2.** 用三步法写出「接受两个 `int`、返回 `bool`」的函数类型与函数指针类型，并声明一个指向名为 `less_than` 的函数的指针变量，然后调用它比较 3 和 5。

**题 3.** 为什么泛型哈希字典的实现里要保留一个 `key_equiv(H, x, k)` 的 helper，而不是在每个调用点都写 `(*H->equiv)(H->key(x), k)`？请给出两个理由。

**题 4.** 判断对错并说明理由：「因为 `void*` 能存任何指针，所以可以把一个 `int*` 直接赋给 `void*` 变量，之后再解引用这个 `void*` 变量得到原来的整数。」

**题 5.** 若 Stack 向下增长、Heap 向上增长，那么「栈溢出」发生在两者相遇时。请解释：为什么函数无限递归会导致栈溢出，而 `alloc` 无限循环导致的是堆耗尽而不是栈溢出？

<details>
<summary>参考答案</summary>

**答 1.**
- (A) **不能通过**。`p` 是 `void*`，`*p` 要求编译器知道对象大小与解释方式，而 `void` 两者都不提供。必须先强转成 `int*`。
- (B) **能通过**。先强转得到 `int*`，再解引用就是合法的。这也是 C1 允许的唯一一种 `void*` 用法。
- (C) **能通过**。NULL 对任何类型都满足 `\hastag`，因为 NULL 不指向任何对象，不存在「指向类型错误」的问题。

**答 2.**

```c1
/* 第一步：原型 */
bool less_than(int x, int y);

/* 第二步：函数类型 */
typedef bool int2bool_fn(int x, int y);

/* 第三步：函数指针类型 + 变量 */
int2bool_fn* F = &less_than;

/* 调用 */
bool b = (*F)(3, 5);   /* b == true */
```

注意 `*` 不能省（否则 `F` 是函数类型变量，非法），`&` 不能省（C1 中取函数地址必须写 `&`），调用时括号不能省（否则被解析成 `*(F(3,5))`）。

**答 3.** 两个理由：
1. **可读性**。字典内部有十几处需要比较 key，如果每处都写 `(*H->equiv)(H->key(x), k)`，调用意图被三层语法噪音淹没，读者要花力气才能看出「这是在比较 key」。
2. **可维护性**。如果以后调用约定变了（例如 `equiv` 改成收三个参数、或 key 需要预处理），只需改 helper 一处，不必改十几处。这是「把变化点收拢到一个地方」的通用工程原则。

补充一点：helper 还有利于写契约——helper 的前置条件可以集中表达「`H`、`x`、`k` 均有效」，调用点不必重复写。

**答 4.** **前半句对，后半句错。**
- 对的部分：`int*` 可以赋给 `void*`（C1 允许隐式转换，标准 C 也允许），这一步只丢类型信息，不丢地址。
- 错的部分：**不能解引用 `void*`**。`*p` 在 `void*` 上是类型错误，编译器根本不会生成代码。必须先强转回 `int*` 再解引用。原句把「能存」误当成「能用」，这是 `void*` 最典型的误解。

**答 5.**
- **无限递归**：每次函数调用都要在 Stack 上压一个新栈帧（存参数、局部变量、返回地址）。递归不终止就意味着栈帧无限累积，Stack 一直向下长，直到撞上 Heap 的边界（或操作系统给的上限），触发栈溢出。
- **`alloc` 无限循环**：每次 `alloc` 从 Heap 取内存，Heap 向上长。它不产生新的栈帧（循环在同一帧内反复执行），所以 Stack 不增长；被耗尽的是 Heap。在 C0/C1 中这表现为内存不足；在标准 C 中则表现为 `malloc` 返回 NULL 或进程被 OOM killer 杀掉。

一句话区分：**栈帧随调用深度增长，堆对象随分配次数增长。**

</details>

## 12. 进一步学习

- 上一讲：[[15-122-13-Hash-Dictionaries]] —— 哈希字典是泛型化的最佳起点，`typedef void* elem;` 就是在那一讲的接口上改一行。
- 下一讲：[[15-122-15-Binary-Search-Trees]] —— 从「泛型容器」转到「有序容器」，看 `key_compare` 如何像 `equiv` 一样作为客户端回调传入。
- 强相关：[[15-122-13-Hash-Dictionaries]] —— 本讲的泛型哈希字典是那一讲字典的泛型版本，建议对照阅读。
- 语言分界：[[15-122-17-Introduction-to-C]] —— 标准 C 从这里开始。届时函数指针的语法基本不变，但内存管理、`&` 的用法、契约的写法全部改变。
- 课程入口：[[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]]、[[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 术语查询：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Void Pointer、Function Pointer、Memory Model、Safety、Dereference 等条目）。
