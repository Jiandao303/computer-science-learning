---
course: CMU 15-122
course_name: Imperative Computation
semester: Fall 2026
lecture_id: L15
topic: Binary Search Trees
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-122
  - 二叉搜索树
  - 数据结构
  - 有序不变式
---

# 第 15 讲：二叉搜索树（Binary Search Trees）

## 1. 本节学习目标

学完本讲后，你应该能够：

1. 说明为什么用有序数组实现字典时 lookup 是 O(log n) 而 insert 是 O(n)，并解释 BST 如何让两者都做到「平均 O(log n)」。
2. 画出 `struct tree_node { entry data; tree* left; tree* right; }` 的内存布局，说明为什么 `data` 必须是 `entry` 指针而不能是 `entry` 本身。
3. 准确复述 Ordering Invariant（有序不变式）：任一节点的键严格大于左子树所有键、严格小于右子树所有键；并说明它为什么蕴含「键不重复」。
4. 解释为什么字典接口要用 `struct dict_header { tree* root; }` 包一层，而不能直接把 `tree*` 当作 `dict_t`。
5. 说明 `bst_insert` 为什么必须**返回**新的子树根，而不能只做就地修改。
6. 指出「只比较父子节点」的弱不变式为什么是错的，并写出带上下界的 `is_ordered(T, lo, hi)` 正确版本。
7. 分析递增插入如何让 BST 退化成链表，从而说明为什么需要 AVL 树。

## 2. 前置知识

- 前序讲次：[[15-122-14-Genericity]]（`typedef void* elem;` 与客户端回调）、[[15-122-06-Binary-Search]]（二分查找与有序数组）、[[15-122-13-Hash-Dictionaries]]（字典的另一种实现，可对比复杂度）。课程入口见 [[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]] 与 [[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 需要熟悉递归函数的写法与「递归函数必须有 base case」的直觉。
- 需要理解指针与结构体字段访问 `T->data`、`T->left`。
- 需要知道空指针 NULL 可以作为「空树」的表示。
- 术语统一以 [[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]] 为准。

> **语言边界提醒**：本讲仍在前九周的 **C0 家族**（讲义中的代码用 C0 语法，`alloc` 分配、有 `//@` 契约）。**不是标准 C。** 标准 C 从第 17 讲开始。

## 3. 核心概念

**Dictionary（字典）**：一种抽象数据类型，维护「键 → 值」的映射，至少支持 insert（插入或覆盖）、lookup（按键查询）、delete（删除）。本讲只讲 insert 与 lookup，delete 不讲。

**Entry（条目）**：字典里存的一个「键值对」。在 C0 中它是一个指针，指向某个客户端定义的结构体。

**Key（键）**：entry 中用于排序与查找的那一部分。通过客户端提供的 `key entry_key(entry e)` 取出。

**Binary Search Tree（二叉搜索树，BST）**：每个节点最多两个孩子的二叉树，且满足有序不变式。

**Ordering Invariant（有序不变式）**：对任一节点，其左子树中所有键严格小于该节点的键，右子树中所有键严格大于该节点的键。

**Height（高度）**：从根出发沿指针能到达的最大节点数。空树高度为 0，单节点树高度为 1。注意这是「节点数」而非「边数」，与某些教材的定义差 1。

**Balanced（平衡）**：树的高度与节点数的对数同阶，即 h ∈ O(log n)。本讲只讨论「不平衡会怎样」，平衡的维护在下一讲。

**Invariant（不变式）**：数据结构在所有对外可见的时刻都必须满足的性质。BST 的不变式有两条：结构上是一棵树（`is_tree`），顺序上有序（`is_ordered`）。

## 4. 通俗理解

把 BST 想成**图书馆的分区书架**。

- 每层书架中间放一本「标尺书」，左边的书都比它薄（键小），右边的书都比它厚（键大）。
- 找一本书：先看标尺书，比它薄就往左走一层，比它厚就往右走一层。每走一层就排除掉一半区域——这就是 O(log n)。
- 插一本书：先按同样方式找到它该在的位置，然后放进去。**问题在于**：如果你走到一个空位，你没法「在空位里放书」——空位本身不是书架。你必须回到上一层，告诉那一层的管理员「你左边/右边多了一个新书架」。这就是 `bst_insert` 为什么必须**返回**新子树。
- 如果大家按厚度从薄到厚依次捐书，而且每本都放在最右边，书架会长成一条直线——这时找书就退化成一本一本翻。这就是 BST 退化的直观图景。

## 5. 原理与推导

### 5.1 有序数组做字典：为什么不够好

用有序数组存 n 个 entry：

- **lookup**：二分查找，每次比较把搜索区间减半，O(log n)。
- **insert**：先用二分找到位置（O(log n)），但插入要把它后面的元素整体右移一格，O(n)。

插入的 O(n) 不是查找造成的，是**数组的连续性**造成的：数组要求元素紧邻存放，腾出一个位置就必须搬移。要摆脱这个代价，就得放弃「连续存放」，改用指针链接——这正是链表与树的价值。

BST 的目标：让 insert 也只做 O(log n) 次操作。

### 5.2 树的表示

```c0
typedef struct tree_node tree;
struct tree_node {
  entry data;      /* Non NULL */
  tree* left;
  tree* right;
};
```

三个要点：

1. **`data` 是 `entry` 而不是 `entry` 本身的内容**。`entry` 在 C0 里是 `typedef void* entry;`（泛型），所以 `data` 是一个指针字段，8 字节。客户端把自己的结构体分配在堆上，把指针交给字典。
2. **空树用 NULL 表示**。这样「叶子」和「空」不需要区分：叶子的 `left` 与 `right` 都是 NULL。
3. **契约里 `data` 必须非 NULL**。因为 `entry_key(T->data)` 会在 `data` 为 NULL 时崩溃。这条要求写进 `is_tree` 里。

`is_tree` 的定义（`15-bst.pdf` 第 5 页）：

```c0
bool is_tree(tree* T) {
  if (T == NULL) return true;
  return T->data != NULL
      && is_tree(T->left)
      && is_tree(T->right);
}
```

它做两件事：检查每个节点的 `data` 非 NULL，以及**排除环**。第二点容易被忽略：如果某个节点的 `left` 指回祖先，`is_tree` 会无限递归下去（最终栈溢出），所以「返回 true」本身就意味着「结构是有限的树」。这个函数对每个节点访问一次，O(n)。

### 5.3 有序不变式

**Ordering Invariant（`15-bst.pdf` 第 6 页）**：对树中任一节点，设其键为 k，则

- 左子树中所有节点的键 **严格小于** k；
- 右子树中所有节点的键 **严格大于** k。

三个推论：

1. **键不重复**。若有两个节点键相同，设其中一个是另一个的祖先（树上任意两节点必有祖先关系），则后代那个必然违反严格不等式；若二者不是祖先关系，它们必分处某个节点的左右两侧，同样违反。所以 BST 里键是唯一的。
2. **中序遍历得到升序序列**。左 → 根 → 右 的遍历顺序恰好按 key 从小到大输出。这条性质在实际中很有用（例如「按顺序打印字典」）。
3. **查找路径唯一**。从根出发，每步比较后只有一条分支可能包含目标键。

注意不变式说的是「**所有**后代」，不是「直接孩子」。这个区别是本讲后面那个 bug 的根源。

### 5.4 查找

```c0
entry bst_lookup(tree* T, key k)
/*@requires is_bst(T);
  @ensures \result == NULL || key_compare(entry_key(\result), k) == 0;
  @*/
{
  if (T == NULL) return NULL;
  int cmp = key_compare(k, entry_key(T->data));
  if (cmp == 0) return T->data;
  if (cmp < 0)  return bst_lookup(T->left, k);
  /*@assert cmp > 0; @*/
  return bst_lookup(T->right, k);
}
```

`key_compare(k1, k2)` 是客户端提供的回调，返回负数 / 0 / 正数分别表示 k1 < k2 / 相等 / k1 > k2。

后置条件值得逐字读：

> `\result == NULL || key_compare(entry_key(\result), k) == 0`

它说的是「要么没找到，要么找到的那个 entry 的键与 k 相等」。**它没有说「如果 k 在字典里就一定能找到」**——那需要更强的契约（`\result != NULL <==> k 存在`），讲义把这一点留到讨论 `is_ordered` 的强度时再提。

`//@assert cmp > 0;` 这一行不是装饰：它告诉读者（和契约检查器）「前两个分支已经排除了 cmp == 0 与 cmp < 0，所以这里必然 cmp > 0」。没有它，读者要自己心算三分法的完备性。

### 5.5 复杂度：为什么是 O(h) 而不是 O(log n)

每次递归调用把问题交给一个子树，树的高度减 1。所以递归深度 = 查找路径长度 ≤ h。每次调用做常数工作（一次 `key_compare`）。因此

> **lookup 的复杂度是 O(h)**，h 为树高。

只有当树**平衡**时 h = O(log n)，才有 O(log n)。完美平衡的 n 节点二叉树高度是 ⌈log₂(n+1)⌉，所以最好情况是 O(log n)；最坏情况（退化成链）h = n，退化为 O(n)。

这就是本讲的核心张力：**BST 的复杂度不是由节点数决定的，而是由形状决定的。** 而形状由插入顺序决定——这是第 10 节要展开的。

### 5.6 接口：为什么需要 `struct dict_header`

一个自然的想法是 `typedef tree* dict_t;`，直接用树根当字典。但这样有两个致命问题：

**问题一：空字典无法表示。** 空树的表示是 NULL，可 `dict_new` 的后置条件必然包含 `\result != NULL`（否则客户端拿到 NULL 后无法区分「空字典」与「创建失败」）。如果 `dict_t` 就是 `tree*`，新建的空字典必然是 NULL，直接违反契约。

**问题二：无法就地插入。** 这一点更根本。C0（以及 C）的函数参数是**按值传递**的：调用 `bst_insert(D, e)` 时，`D` 的**副本**进入函数。函数内部把 `T` 改成新节点，只是改了这个副本，调用者的 `D` 毫无变化。

解决办法是把树根装进一个 header 结构体：

```c0
typedef struct dict_header dict;
struct dict_header {
  tree* root;
};
typedef dict* dict_t;
```

现在 `dict_t` 是一个**非 NULL 的指针**，它指向的 header 里的 `root` 字段可以被就地修改：`D->root = bst_insert(D->root, e);`。空字典就是 `root == NULL` 的 header，本身不是 NULL，契约满足。

不变式也随之分成两层：

```c0
bool is_dict(dict_t D) {
  return D != NULL && is_bst(D->root);
}
```

**这个「header 包一层」的模式在本课程里反复出现**（第 14 讲的 `hdict_header`、第 21 讲的 `graph_header`、第 22 讲的 `neighbor_header`、第 26 讲的 `heap_header`）。它的通用作用是：给「用 NULL 表示空」的数据结构提供一个稳定的、非 NULL 的句柄，并给「需要就地修改的字段」提供一个可写的落点。

### 5.7 插入：为什么要返回新子树

```c0
tree* bst_insert(tree* T, entry e)
/*@requires is_bst(T) && e != NULL;
  @ensures is_bst(\result);
  @*/
{
  if (T == NULL) {
    tree* N = alloc(tree);
    N->data  = e;
    N->left  = NULL;
    N->right = NULL;
    return N;
  }
  int cmp = key_compare(entry_key(e), entry_key(T->data));
  if (cmp == 0) {
    T->data = e;                    /* 覆盖旧值 */
  } else if (cmp < 0) {
    T->left = bst_insert(T->left, e);
  } else {
    T->right = bst_insert(T->right, e);
  }
  return T;
}
```

关键在 `if (T == NULL)` 这个分支。走到这里意味着「要插入的位置是一个空位」，而空位**没有内存可以写入**——NULL 不是一个对象。所以函数必须**新建**一个节点并把它**返回**给调用者，由调用者把它接到自己的 `left` 或 `right` 字段上。

这就解释了 `T->left = bst_insert(T->left, e);` 这个看似多余的赋值：它把「递归调用可能换掉整棵子树」这件事落实下去。如果递归只是往下走而没有返回，新节点就会丢失。

对比 `cmp == 0` 的分支：那里是**就地修改** `T->data`，不需要返回新树，因为 `T` 本身已经存在。`return T;` 只是为了让所有分支的返回类型一致。

**递归的正确性**依赖有序不变式：

- `cmp < 0` 说明新键小于当前键，它只能落在左子树（右子树的所有键都大于当前键，更大于新键）。所以只递归左边不丢信息。
- `cmp > 0` 对称。

如果没有有序不变式，「只走一边」就是错的——新键可能该去另一边。这就是为什么插入的正确性证明必须引用不变式。

### 5.8 检查不变式：一个被明确标注为错误的版本

讲义第 11 页给出了一段**标着 `/* THIS CODE IS BUGGY */`** 的代码，值得仔细看：

```c0
/* 错误版本 */
bool is_ordered(tree* T) {
  if (T == NULL) return true;
  bool ok = true;
  if (T->left != NULL)
    ok = ok && key_compare(entry_key(T->left->data),  entry_key(T->data)) < 0;
  if (T->right != NULL)
    ok = ok && key_compare(entry_key(T->data), entry_key(T->right->data)) < 0;
  return ok && is_ordered(T->left) && is_ordered(T->right);
}
```

它只比较**父子**。为什么不够？构造反例：

```
        10
       /  \
      5    15
     / \
    3   12
```

检查每一对父子：5 < 10 ✓、15 > 10 ✓、3 < 5 ✓、12 > 5 ✓。全部通过。但 12 在 10 的左子树里，而 12 > 10，违反了不变式。此时 `bst_lookup(T, 12)` 会从根往左走（因为 12 < 10 为假？不，12 > 10，会往右走），永远找不到 12——**树里明明有 12，查找却返回 NULL**。

这就是「弱不变式」的危害：它允许了不该存在的状态，而这个状态会让其他函数的正确性论证失效。

### 5.9 正确版本：带上下界的递归

正确的检查要传**区间**：当前子树中所有键必须落在 (lo, hi) 这个开区间内。

```c0
bool is_ordered(tree* T, entry lo, entry hi)
/*@requires is_tree(T);
  @*/
{
  if (T == NULL) return true;
  key k = entry_key(T->data);
  return (lo == NULL || key_compare(entry_key(lo), k) < 0)
      && (hi == NULL || key_compare(k, entry_key(hi)) < 0)
      && is_ordered(T->left,  lo, T->data)
      && is_ordered(T->right, T->data, hi);
}

bool is_bst(tree* T) {
  return is_tree(T) && is_ordered(T, NULL, NULL);
}
```

逐个变量解释：

- `lo`：当前子树所有键的**下界**（不含）。NULL 表示「没有下界」，即 −∞。
- `hi`：当前子树所有键的**上界**（不含）。NULL 表示「没有上界」，即 +∞。
- 用 `entry` 而不是 `key` 表示边界，是为了**避免需要 ±∞ 这种不存在的键**。`key` 是客户端定义的类型，我们无法凭空造出一个「比所有键都小」的值；但我们可以用 NULL 表示「无边界」。
- 递归左子树时，上界收紧为 `T->data`（新键必须小于当前键），下界不变。
- 递归右子树时，下界收紧为 `T->data`，上界不变。

用这个版本检查上面的反例：走到节点 5 时 `lo = 10`、`hi = NULL`；检查 5 是否满足 `10 < 5` —— 不满足，返回 false。正确识别出错误。

**复杂度**：每个节点访问一次，O(n)。`is_bst` 是 `is_tree` + `is_ordered`，两次遍历，仍是 O(n)。

讲义第 13 页有一个重要的警告：`is_ordered(T, NULL, NULL)` 作为 `bst_insert` / `bst_lookup` 的前置/后置条件**不够强**。因为它只说了「整棵树有序」，没说「这棵树包含哪些键」。例如插入后，后置条件 `is_bst(\result)` 无法保证「新键确实在里面」，也无法保证「原有的键都还在」。要表达这些，需要更强的规格（例如「树的键集合 = 旧集合 ∪ {新键}」），讲义把这件事留到后续讨论。

### 5.10 形状决定性能

讲义第 14–15 页对比两种插入顺序：

**递增插入 1, 2, 3, 4：**

```
1
 \
  2
   \
    3
     \
      4
```

每次新键都大于当前所有键，所以永远往右走到底。树退化成一条右斜链，高度 h = n。lookup 变成 O(n)，与链表无异。

**递减插入**完全对称，退化成左斜链。

**插入 3, 1, 4, 2：**

```
      3
     / \
    1   4
     \
      2
```

高度 3，节点 4 个，接近平衡。lookup 是 O(log n) 量级。

**结论**：BST 的性能完全由插入顺序决定，而插入顺序通常由客户端的数据决定，库无法控制。一个「平均情况下不错、最坏情况退化成链表」的数据结构，在工程上是不够的——特别是当输入可能被恶意构造时（攻击者只要按升序发送请求，就能让服务器每次查找都 O(n)，这是算法复杂度攻击的经典形式）。

**下一讲（AVL 树）的动机正是如此**：如果能在每次插入后通过局部调整把高度维持在 O(log n)，那么无论插入顺序如何，lookup 与 insert 都是 O(log n)。

### 5.11 BST 集合：当 key 就是元素本身

讲义第 13–14 页讨论了一个简化情形：如果字典只需要回答「某个元素在不在」，那么 entry 与 key 可以是同一个东西，都叫 `elem`。此时比较函数是

```c0
int elem_compare(elem e1, elem e2);   /* 保证返回 -1、0 或 1 */
```

而 `set_contains` 返回 `bool`，所以 `elem` **不必**是指针类型——它可以是 `int`、`char` 等值类型。这是泛型接口的一个细节差异：哈希字典要求 entry 是指针（因为要存进链表节点并返回），而集合只回答是非，可以更自由。

### 5.12 习题要点

- **Ex1（第 16 页，解在第 17 页）**：依次插入 24, 33, 10, 2, 1, 7, 6，画出最终的树。要点是每次插入都从根开始比较，沿唯一路径下行。
- **Ex2（解在第 17 页）**：给定键集合 {2,8,10,11,12,13,14,15,17,20} 与树的形状，反推插入顺序。答案是**唯一**的：根必须是 11（因为它是唯一能把其余键分成「全小于」与「全大于」两组的元素）。一个合法的插入序是 11, 17, 13, 10, 20, 15, 2, 14, 8, 12。这类题的关键洞察是：**任一子树的根必须是该子树键集合中「第一个被插入」的元素**，因此可以自顶向下唯一确定。
- **Ex3（解在第 18 页）**：迭代版 `dict_lookup`。用 `while` 循环沿指针下行，循环不变式是「目标键若存在，必在当前子树中」。
- **Ex4（解在第 19 页）**：迭代版 `dict_insert`。这题比 lookup 难，因为要修改父节点的字段。解法是维护一个 `parent` 尾指针：走到 NULL 时，根据 `parent` 与 `e` 的比较结果决定写入 `parent->left` 还是 `parent->right`；若 `parent == NULL`（空树），则写 `D->root = leaf(e)`。辅助函数 `leaf(e)` 分配一个左右都为 NULL 的新节点。
- **Ex5（解在第 20–22 页）**：BST 集合的实现。注意 `is_ordered(tree* T, elem* lo, elem* hi)` 要用 `alloc` 出来的 `elem` 承载边界值，因为集合的 elem 可能是值类型，无法用 NULL 表示「无边界」。这是一个真实的工程约束：**用 NULL 表示无边界的前提是类型本身是指针**。

## 6. 代码示例

### 6.1 官方课程代码

以下代码出自 `15-bst.pdf`，页码为该 PDF 的页码。

**（1）树的表示**（第 3–5 页）

```c0
typedef struct tree_node tree;
struct tree_node {
  entry data;      /* Non NULL */
  tree* left;
  tree* right;
};
```

**（2）`is_tree`**（第 5 页）

检查 `data != NULL` 且左右递归为树。它同时排除了环。

**（3）`bst_lookup`**（第 7 页）

三分支递归：`cmp == 0` 返回、`cmp < 0` 走左、`cmp > 0` 走右，中间插一条 `//@assert cmp > 0;`。后置条件为 `\result == NULL || key_compare(entry_key(\result), k) == 0`。

**（4）字典 header**（第 8 页）

```c0
typedef struct dict_header dict;
struct dict_header { tree* root; };
bool is_dict(dict_t D) { return D != NULL && is_bst(D->root); }
```

**（5）`bst_insert`**（第 10 页）

四个分支：NULL 处新建并返回、`cmp == 0` 覆盖、`cmp < 0` 递归左并赋值、否则递归右并赋值。最后 `return T;`。

**（6）错误的不变式检查**（第 11 页，明确标注 `/* THIS CODE IS BUGGY */`）

只比较父子节点的 `is_ordered`，以及用它构造的反例。

**（7）正确的 `is_ordered`**（第 12–13 页）

带 `lo`/`hi` 两个 `entry` 边界的递归版本，NULL 表示无边界。第 13 页说明这个规格对 `bst_insert`/`bst_lookup` 而言仍然不够强。

**（8）BST 集合与形状讨论**（第 13–15 页）

`elem_compare` 返回 −1/0/1；递增插入退化成链的例子。

**（9）习题与答案**（第 16 页题目，第 17–22 页答案）

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念

**示例一：用「中序遍历」验证有序不变式。**

这是检查 BST 的一个独立手段：如果中序遍历得到的键序列严格递增，那么有序不变式成立（反之亦然，对无重复键的树）。它比 `is_ordered` 慢（需要额外数组），但更直观，适合调试。

```c0
/* 把中序遍历的结果依次写入 out[]，返回写入个数 */
int inorder_fill(tree* T, key[] out, int i)
/*@requires is_tree(T) && out != NULL;
  @requires 0 <= i && i + tree_size(T) <= \length(out);
  @ensures \result == i + tree_size(T);
  @*/
{
  if (T == NULL) return i;
  i = inorder_fill(T->left, out, i);
  out[i] = entry_key(T->data);
  i = i + 1;
  i = inorder_fill(T->right, out, i);
  return i;
}

bool is_ordered_via_inorder(tree* T) {
  int n = tree_size(T);
  if (n <= 1) return true;
  key[] buf = alloc_array(key, n);
  inorder_fill(T, buf, 0);
  for (int i = 0; i < n - 1; i++)
  //@loop_invariant 0 <= i && i <= n - 1;
  {
    if (key_compare(buf[i], buf[i+1]) >= 0) return false;
  }
  return true;
}
```

注意 `key_compare(buf[i], buf[i+1]) >= 0` 用的是 `>=` 而不是 `>`：BST 不允许重复键，所以相等也算违规。这个细节在写测试时很容易漏掉。

**示例二：统计树高与「平衡度」。**

用来观察插入顺序对形状的影响。

```c0
int tree_height(tree* T)
/*@requires is_tree(T);
  @ensures \result >= 0;
  @*/
{
  if (T == NULL) return 0;
  int hl = tree_height(T->left);
  int hr = tree_height(T->right);
  return 1 + (hl > hr ? hl : hr);
}

int tree_size(tree* T)
/*@requires is_tree(T);
  @ensures \result >= 0;
  @*/
{
  if (T == NULL) return 0;
  return 1 + tree_size(T->left) + tree_size(T->right);
}
```

**复杂度警告**：`tree_height` 是 O(n)，`tree_size` 也是 O(n)。如果在 `bst_insert` 的每次递归里都调用 `tree_height`，总代价会变成 O(n) per insert，整体 O(n²)——这正好抵消了 BST 的优势。下一讲的 AVL 树用「在每个节点缓存 height 字段」把这个代价降到 O(1)，这是理解 AVL 实现的关键动机之一。

**示例三：验证「递增插入退化」的最小实验。**

```c0
void degenerate_demo() {
  dict_t D = dict_new();
  for (int i = 1; i <= 1000; i++) {
    D = dict_insert(D, mk_int_entry(i));
  }
  /* 此时 tree_height(D->root) == 1000，而不是约 10 */
  printint(tree_height(D->root));
}
```

对比：若按「每次取中位数」的顺序插入 1..1000，高度约为 10。同样的 1000 个键，高度相差 100 倍——这就是为什么 AVL 树值得单独一讲。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键区别 | 记忆点 |
|---|---|---|---|
| BST（二叉搜索树） | Binary Tree（二叉树） | 前者额外要求有序不变式；后者只要求每节点至多两个孩子 | 「有序」是 BST 的全部价值 |
| Ordering Invariant（有序不变式） | `is_tree`（结构不变式） | 前者管键的大小关系，后者管「是一棵有限的、data 非 NULL 的树」 | 「有序 vs 有形」 |
| 高度（节点数） | 高度（边数） | 本课程用**节点数**：空树 0、单节点 1；部分教材用边数：空树 −1、单节点 0 | 差 1，做题时先确认定义 |
| `bst_lookup` 的 O(h) | O(log n) | h 是树高，n 是节点数；只有平衡时 h = O(log n) | 「O(h) 是真相，O(log n) 是理想」 |
| 弱不变式（只比父子） | 强不变式（带区间） | 前者允许「12 出现在 10 的左子树」这种非法状态 | **弱不变式会放过真 bug** |
| `dict_t` = `tree*` | `dict_t` = `struct dict_header*` | 前者无法表示空字典（NULL 违反 `\result != NULL`）、无法就地插入 | 「header 提供可写落点」 |
| 就地修改 `T->data` | 返回新子树 `T->left = ...` | 前者用于「节点已存在」；后者用于「在 NULL 处新建」 | NULL 处没有内存可写 |
| 本讲 C0 代码 | 标准 C | C0 有 `alloc`、`//@` 契约、垃圾回收；标准 C 要 `malloc`/`free`（第 17 讲起） | **本讲不是标准 C** |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-122/lectures/15-bst.pdf`
- **总页数**：22 页
- **本节重点页码**（PDF 页码，即提取文本中 `=== [page N] ===` 的 N）：
  - 第 1–2 页：有序集合的动机、与有序数组的复杂度对比
  - 第 2–3 页：抽象二分查找
  - 第 3–5 页：用指针表示二叉树、`struct tree_node` 的定义
  - 第 5–6 页：`is_tree` 与 Ordering Invariant 的正式陈述
  - 第 6–7 页：`bst_lookup` 的实现与后置条件
  - 第 7 页：复杂度分析（O(h)）与高度定义
  - 第 7–9 页：字典接口、`struct dict_header` 的必要性
  - 第 9–10 页：`bst_insert` 与「返回新子树」的原因
  - 第 10–13 页：**错误的不变式检查**（第 11 页标注 BUGGY）与正确的 `is_ordered(T, lo, hi)`（第 12–13 页）
  - 第 13–14 页：BST 集合（`elem_compare`）
  - 第 14–15 页：树的形状、递增插入退化成链
  - 第 16 页：习题 Ex1–Ex5
  - 第 17–22 页：参考答案（Ex2 的唯一性论证在第 17 页，Ex4 迭代插入在第 19 页，Ex5 在第 20–22 页）
- **原始网页链接**：`https://www.cs.cmu.edu/~15122-archive/f26/handouts/lectures/15-bst.pdf`
- **配套代码包**：`90-原始PDF/15-122/code/15-bst.tgz`

## 9. 对应视频

未找到官方公开录像。本讲可配合讲义 PDF 自学；第 11 页那个 BUGGY 的反例建议亲手在纸上画一遍，比读文字有效得多。

## 10. 本节复习

1. 有序数组做字典：lookup O(log n)、insert O(n)。insert 的瓶颈是数组的连续性，不是查找。BST 用指针链接摆脱这个瓶颈。
2. 树的表示：`data`（`entry`，非 NULL）、`left`、`right`；空树是 NULL；`is_tree` 同时排除 NULL data 与环。
3. Ordering Invariant：左子树所有键 < 本节点键 < 右子树所有键（严格）。它蕴含键唯一、中序升序、查找路径唯一。
4. lookup 是 O(h) 而非无条件 O(log n)；h 由形状决定，形状由插入顺序决定。
5. `dict_t` 必须是 `struct dict_header*`：既能表示空字典（root == NULL 的 header 本身非 NULL），又提供了可写的 `root` 字段供就地插入。
6. `bst_insert` 必须返回新子树，因为 NULL 处没有内存可写；`T->left = bst_insert(T->left, e);` 这个赋值不可省。
7. 只比较父子的 `is_ordered` 是**错的**：它允许「12 在 10 的左子树」这种状态，会让 lookup 漏掉存在的键。正确版本传 `lo`/`hi` 两个边界，用 NULL 表示无边界。
8. 递增或递减插入会让树退化成链，h = n，性能退化为 O(n)。这是下一讲 AVL 树的动机。

## 11. 自我检查

**题 1.** 依次向空 BST 插入 24, 33, 10, 2, 1, 7, 6。画出最终的树，写出它的高度、中序遍历序列，以及 `bst_lookup(T, 7)` 的比较路径（每次比较的两个键）。

**题 2.** 下面这棵树是否满足有序不变式？如果不满足，指出所有违规的节点对。

```
        20
       /  \
      10   30
     /  \    \
    5   15    25
       /
      18
```

**题 3.** 为什么 `bst_insert` 里 `cmp == 0` 的分支可以就地 `T->data = e;`，而 `T == NULL` 的分支必须 `return N;`？请从「内存是否已存在」的角度解释。

**题 4.** 若把 `dict_t` 定义为 `typedef tree* dict_t;`，`dict_new()` 返回什么？这会违反哪条契约？除了契约问题，还会造成什么功能性缺陷？

**题 5.** 给定键集合 {1,2,3,4,5,6,7} 与「高度为 3 的完美平衡树」这个形状，插入顺序是唯一的吗？如果不是，举出两个不同的插入顺序都产生该形状。

<details>
<summary>参考答案</summary>

**答 1.**

插入过程：24（根）→ 33（24 右）→ 10（24 左）→ 2（10 左）→ 1（2 左）→ 7（2 右）→ 6（7 左）。

最终树：

```
        24
       /  \
     10    33
     /
    2
   / \
  1   7
     /
    6
```

- **高度**：最长路径 24 → 10 → 2 → 7 → 6，共 5 个节点，所以 h = 5。
- **中序遍历**：1, 2, 6, 7, 10, 24, 33（严格递增，验证了有序不变式）。
- **`bst_lookup(T, 7)` 的比较路径**：
  1. `key_compare(7, 24) < 0` → 走左
  2. `key_compare(7, 10) < 0` → 走左
  3. `key_compare(7, 2) > 0` → 走右
  4. `key_compare(7, 7) == 0` → 返回该 entry

共 4 次比较。

**答 2.** **不满足**。有两处违规：
1. **18 在 20 的左子树里，但 18 < 20** —— 这一条其实满足。真正的问题是：18 位于 10 的右子树，而 10 的右子树要求所有键 > 10，18 > 10 ✓。再看 18 相对 15：18 > 15 ✓（18 是 15 的左孩子，左孩子要求 < 15）。**这里违规**：18 是 15 的左孩子，但 18 > 15，违反「左子树所有键 < 本节点键」。
2. **25 是 30 的右孩子**，要求 25 > 30，但 25 < 30。**违规**。

所以违规点是：节点 15 与其左孩子 18（18 应小于 15），以及节点 30 与其右孩子 25（25 应大于 30）。

顺带验证弱不变式会怎么判：只比父子的话，18 vs 15 这一对会被抓到（因为 18 是直接孩子），25 vs 30 也会被抓到。要构造「弱不变式放过、强不变式抓到」的例子，需要让违规发生在**隔代**：例如把 18 挂到 15 的左孩子的左孩子位置，这样父子比较都通过，但 18 > 10 违反祖先约束。

**答 3.**
- `cmp == 0` 时，`T` 是一个**已经存在的节点**，`T->data` 是一块已经分配好的、可写的内存（8 字节的指针字段）。`T->data = e;` 只是往这块内存里写一个新地址，完全合法。
- `T == NULL` 时，**没有任何内存存在**。NULL 不是一个对象，它是一个「什么都没有」的标记。要放一个新 entry，必须先用 `alloc(tree)` 分配一块新内存，把数据写进去，然后**把这块新内存的地址交给调用者**——因为只有调用者知道该把它接到哪个字段（`parent->left` 还是 `parent->right`）。函数自己无法完成「接上去」这个动作，因为它不知道父节点是谁。

一句话：**就地修改的前提是内存已存在；内存不存在时必须返回新地址，由持有指针的一方负责接线。**

**答 4.**
- `dict_new()` 必须返回**空字典**，而空树就是 NULL，所以它只能 `return NULL;`。
- 这违反了 `dict_new` 的后置条件 `\result != NULL`。更根本的是：客户端拿到 NULL 后无法区分「创建成功但为空」与「创建失败」，也无法对它调用任何操作（所有操作的前置条件都是 `D != NULL`）。
- **功能性缺陷**：即使放宽契约允许 NULL，`dict_insert(D, e)` 也无法工作。因为参数按值传递，函数内部把 `D` 改成新节点只是改了副本，调用者的 `D` 仍然是 NULL。空字典的第一次插入**永远无法生效**。这正是需要 header 包一层的根本原因。

**答 5.** **不唯一**。高度为 3 的完美平衡树，7 个键，根必须是 4（唯一能把 {1,2,3} 与 {5,6,7} 分开的元素），左子树的根必须是 2，右子树的根必须是 6。但**插入的先后**有多种可能，只要保证「祖先先于后代」即可。

两个合法顺序：
- `4, 2, 6, 1, 3, 5, 7`（逐层，从左到右）
- `4, 6, 2, 7, 5, 3, 1`（逐层，从右到左；每层内部顺序任意）

两者都产生同一形状：

```
        4
       / \
      2   6
     / \ / \
    1  3 5  7
```

一般规律：**给定形状与键集合，每个子树的根是唯一确定的**（必须是该子树键集合的中位数），但插入顺序只需满足「父先于子」这个偏序，因此有多种拓扑序。

</details>

## 12. 进一步学习

- 上一讲：[[15-122-14-Genericity]] —— `entry`、`key` 的泛型表示与客户端回调（`key_compare` 就是那一讲 `equiv` 的同族）。
- 下一讲：[[15-122-16-AVL-Trees]] —— 直接解决本讲第 10 节的退化问题：用旋转把高度维持在 O(log n)。
- 相关：[[15-122-06-Binary-Search]] —— 数组上的二分查找；与 BST 的查找是同一个「每次排除一半」的思想，只是载体从下标变成指针。
- 相关：[[15-122-13-Hash-Dictionaries]] —— 字典的另一种实现。哈希表期望 O(1) 但无序；BST 是 O(log n) 且支持有序遍历。工程上按需求选择。
- 课程入口：[[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]]、[[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 术语查询：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Binary Search Tree、Invariant、Height、Dictionary 等条目）。
