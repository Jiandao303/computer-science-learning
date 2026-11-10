---
course: CMU 15-122
course_name: Imperative Computation
semester: Fall 2026
lecture_id: L16
topic: AVL Trees
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-122
  - AVL树
  - 平衡树
  - 旋转
---

# 第 16 讲：AVL 树（AVL Trees）

## 1. 本节学习目标

学完本讲后，你应该能够：

1. 陈述 Height Invariant（高度不变式）：任一节点左右子树高度差的绝对值不超过 1，并解释为什么这条局部条件能推出全局的 h ∈ O(log n)。
2. 写出 `rotate_left` 与 `rotate_right` 的完整代码（含前置条件），并手工追踪一次旋转中所有指针的变化。
3. 说明为什么一次插入最多需要 1 次单旋或 1 次双旋，且旋转之后**不需要**继续向上修复。
4. 解释「在每个节点缓存 `height` 字段」为什么能把 `height(T)` 从 O(n) 降到 O(1)，以及这要求 `fix_height` 在哪些位置被调用、按什么顺序调用。
5. 区分 LL、LR、RR、RL 四种失衡情形，并说明「外侧用单旋、内侧用双旋」的判据。
6. 从讲义第 7 节的实验数据说明 AVL 树与普通 BST 在性能与**可预测性**上的差别。

## 2. 前置知识

- 前序讲次：[[15-122-15-Binary-Search-Trees]]（有序不变式、`bst_insert`、高度定义、退化成链的问题）。课程入口见 [[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]] 与 [[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 需要熟练递归：本讲所有函数都是「对子树递归，再修当前节点」的形状。
- 需要理解「不变式」的双重角色：既是对外承诺，也是递归正确性证明的归纳假设。
- 需要知道 `abs`、`max` 的语义（C0 有 `abs`，或自己写三目运算）。
- 术语统一以 [[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]] 为准。

> **语言边界提醒**：本讲仍属前九周的 **C0**（`alloc`、`//@` 契约、垃圾回收）。**不是标准 C。** 标准 C 从第 17 讲开始。

## 3. 核心概念

**Height Invariant（高度不变式）**：对树中每个节点，其左右子树高度之差的绝对值 ≤ 1。只有满足这条的 BST 才叫 AVL 树。

**AVL Tree（AVL 树）**：同时满足 Ordering Invariant（有序不变式）与 Height Invariant 的二叉搜索树。名字来自两位发明者 Adelson-Velsky 与 Landis。

**Rotation（旋转）**：一种局部重构操作，把一棵子树的根换成它的某个孩子，同时保持中序遍历序列不变（因而保持有序不变式）。分左旋与右旋。

**Single Rotation（单旋）**：一次 `rotate_left` 或 `rotate_right`。

**Double Rotation（双旋）**：先对孩子做一次反方向的旋，再对自己做一次正方向的旋。用于「内侧」失衡。

**Balance Factor（平衡因子）**：`height(T->right) - height(T->left)`。AVL 要求它恒为 −1、0 或 1。

**Cached Height（缓存高度）**：在每个节点存一个 `int height` 字段，使得读取高度是 O(1) 而非 O(n)。代价是每次结构变化后必须更新，且更新顺序有讲究。

## 4. 通俗理解

把 AVL 树想成**叠罗汉**。

- 规则是：任何一个人脚下左右两边的「人塔高度」差不能超过 1 层。
- 现在在最底下塞进一个新的人。从他往上，每一层的平衡都可能被破坏。
- 但你只需要在**最底下那个被破坏的节点**上做一次「换位」——把比较高那一侧的顶端那个人提上来当新的支点。做完之后，这个子塔的总高度会回到原来的值，于是上面所有层的平衡**自动恢复**。
- 这就是为什么「一次插入最多 1 次单旋或 1 次双旋」：修复是从下往上第一次遇到失衡时就完成的，而且修完就收工。

另一种直观：旋转就像**把一根斜着的扁担重新挂到重心上**。扁担两端的货物（中序序列）不变，只是挂点换了。

## 5. 原理与推导

### 5.1 为什么高度不变式能给出 O(log n)

先证明一个引理。

**引理**：高度为 h 的 AVL 树至少有 F(h) 个节点，其中 F(0)=0、F(1)=1、F(h) = F(h−1) + F(h−2) + 1。

**证明**（对 h 归纳）：

- h = 0：空树，0 个节点，等于 F(0)。✓
- h = 1：单节点，1 个节点，等于 F(1)。✓
- h ≥ 2：设根的两个子树高度为 h₁、h₂。由高度不变式 |h₁ − h₂| ≤ 1，且整棵树高度为 h，所以 max(h₁,h₂) = h−1。为了**让节点数最少**，应让两个子树都尽量矮：取 {h₁,h₂} = {h−1, h−2}。于是
  n ≥ F(h−1) + F(h−2) + 1 = F(h)。

这个递推与斐波那契同阶。令 G(h) = F(h) + 1，则 G(h) = G(h−1) + G(h−2)，G(0)=1、G(1)=2，正是斐波那契数列平移。而斐波那契数列以 φ^h 增长（φ = (1+√5)/2 ≈ 1.618），所以

> F(h) = Θ(φ^h)，即 n ≥ c·φ^h。

两边取对数：

> **h ≤ log_φ(n) + O(1) = O(log n)**

因为 log_φ(n) = log₂(n) / log₂(φ) ≈ 1.44·log₂(n)，所以 AVL 树的高度最多比完美平衡树高约 44%。这是一个常数因子，不影响 O(log n) 的结论。

**这就是局部条件（每个节点差 ≤ 1）如何约束全局量（总高度）的完整逻辑。** 注意证明里最关键的一步是「最坏情况取 {h−1, h−2}」——这是把「局部约束」翻译成「节点数下界」的桥梁。

### 5.2 旋转：保持中序序列的局部重构

**`rotate_left`（`16-avl.pdf` 第 5–6 页）**

```c0
tree* rotate_left(tree* T)
/*@requires T != NULL && T->right != NULL;
  @ensures is_bst(\result) && is_avl(\result);   /* 简化表述 */
  @*/
{
  tree* R = T->right;
  T->right = T->right->left;
  R->left = T;
  return R;
}
```

逐行解释：

1. `tree* R = T->right;` —— 记住右孩子 `R`，它将成为新的根。
2. `T->right = T->right->left;` —— 把 `R` 的左子树（记为 β）过继给 `T` 当右子树。**这一步是保持有序性的关键**：β 中的所有键都大于 T 的键、小于 R 的键，所以它既可以在 T 的右边，也可以在 R 的左边。
3. `R->left = T;` —— 把 `T` 挂到 `R` 的左边。
4. `return R;` —— 新根是 `R`。

指针变化图示（旋转前 → 旋转后）：

```
      T                R
     / \              / \
    A   R    ==>     T   C
       / \          / \
      B   C        A   B
```

中序遍历：

- 旋转前：A, T, B, R, C
- 旋转后：A, T, B, R, C

**完全相同**。这就是「旋转不改变有序性」的证明方式：只要论证 β 的键范围在 T 与 R 之间，中序序列就逐项一致。而 β 的键范围由有序不变式给出：β 是 R 的左子树，所以 β 的所有键 < R 的键；β 又曾是 T 的右子树的一部分，所以 β 的所有键 > T 的键。

`rotate_right` 完全对称：

```c0
tree* rotate_right(tree* T)
/*@requires T != NULL && T->left != NULL;
  @*/
{
  tree* L = T->left;
  T->left = T->left->right;
  L->right = T;
  return L;
}
```

**前置条件不可省**：`T->right` 为 NULL 时，`T->right->left` 是解引用空指针。这就是为什么 `rebalance` 里要先判断高度差为 2（这已经蕴含了那一侧非空）。

### 5.3 四种失衡情形与选旋规则

设节点 T 的右子树比左子树高 2（`height(T->right) - height(T->left) == 2`）。失衡一定发生在右子树的某一侧：

| 情形 | 结构特征 | 处理 | 助记 |
|---|---|---|---|
| **RR** | 右子树的**右**子树更高（外侧） | 一次 `rotate_left(T)` | 外侧 → 单旋 |
| **RL** | 右子树的**左**子树更高（内侧） | 先 `rotate_right(T->right)`，再 `rotate_left(T)` | 内侧 → 双旋 |

左子树高 2 时对称：

| 情形 | 结构特征 | 处理 |
|---|---|---|
| **LL** | 左子树的**左**子树更高（外侧） | 一次 `rotate_right(T)` |
| **LR** | 左子树的**右**子树更高（内侧） | 先 `rotate_left(T->left)`，再 `rotate_right(T)` |

**为什么内侧必须双旋？** 看 RL 情形：

```
     T                    T                     Y
    / \                  / \                   / \
   A   R      单旋?      R   ...   ==>        T   Z
      / \      ---->    / \                  / \   \
     Y   Z             Y   ...              A   X   ...
    / \               / \
   X   ...           T   X
```

如果直接对 T 做左旋，`R` 上位，`T` 变成 `R` 的左孩子，而 `R` 的左子树是 `Y`——但 `Y` 的键比 `T` 大，把 `Y` 挂到 `T` 的右边会让 T 的右子树包含比 T 大的键（这没问题），可 `T` 又变成了 `R` 的左孩子而 `T` 的键 < `R`（也没问题）……真正的问题是**高度**：单旋后新根的左子树（以 T 为根）仍然偏高，平衡因子还是 2，没修好。

正确的做法是先把 `Y` 提到 `R` 的位置（`rotate_right(R)`），让结构从「内侧」变成「外侧」，再对 `T` 做左旋。这样一次双旋就把高度降下来了。

**判据的精确形式**（讲义第 13 页）：

```c0
if (height(T->right->right) > height(T->right->left))
    T = rotate_left(T);                 /* RR：外侧单旋 */
else {
    T->right = rotate_right(T->right);  /* RL：先转孩子 */
    T = rotate_left(T);                 /*     再转自己 */
}
```

注意判据用的是 `>` 而不是 `>=`。当两侧等高时走 `else`（双旋），这也正确，只是多做一次旋转；用 `>` 是为了在等高时选择「更保守」的路径，避免某些边界情形下的错误。

### 5.4 为什么一次插入最多 1–2 次旋转

这是 AVL 最漂亮的性质，值得完整推导。

设插入发生在子树 T 中，插入后 T 的高度从 h 变成 h+1，导致 T 的平衡因子变成 ±2（失衡）。分两种情形：

**情形 A：单旋（外侧）**。旋转后新子树的高度是 h+1（与插入前相同）。既然高度回到了插入前的值，那么 T 的父节点看到的子树高度没有变化，父节点的平衡因子也不变，**无需继续修复**。

**情形 B：双旋（内侧）**。双旋后新子树的高度也是 h+1，同理无需继续修复。

**关键洞察**：旋转把「插入带来的 +1 高度」**吸收**掉了。所以修复只在**最深的失衡点**发生一次，之后一路上溯都不会再失衡。

严格地说，这里的「h+1」需要验证。以 RR 情形为例：设 T 的左子树高 h−1（因为失衡后右子树高 h+1），右子树 R 高 h+1，R 的右子树高 h（外侧更高）。左旋后：新根 R 的左子树是以 T 为根的树，其高度 = 1 + max(h−1, height(R->left))。R 的左子树高度 ≤ h，所以 T 的高度 ≤ 1 + max(h−1, h) = h+1；又因为 R 右子树高 h，R 的高度 = 1 + max(T 的高度, h) = h+1。所以新子树高 h+1 = 插入前的高度。✓

**对比：删除可能需要 O(log n) 次旋转**。删除会让子树高度**降低**，降低可能传播到根（因为「变矮」不会自动被吸收）。本讲只讨论插入，删除的旋转上溯性质留到后续课程。

### 5.5 缓存高度：从 O(n) 到 O(1)

上一讲的 `tree_height` 是 O(n)。如果每次 `rebalance` 都调用它，一次插入的代价会退化成 O(n)，AVL 就白做了。

解法是在节点里存高度：

```c0
typedef struct tree_node tree;
struct tree_node {
  entry data;
  int height;        /* 该节点为根的子树高度，>= 1 */
  tree* left;
  tree* right;
};

int height(tree* T) {
  return T == NULL ? 0 : T->height;
}
```

`height` 现在是 O(1)。代价是**必须维护它**：任何改变子树结构的操作后，都要重算受影响节点的高度。

```c0
void fix_height(tree* T)
/*@requires T != NULL && is_specified_height(T->left)
             && is_specified_height(T->right);
  @ensures is_specified_height(T);
  @*/
{
  int hl = height(T->left);
  int hr = height(T->right);
  T->height = (hl > hr ? hl + 1 : hr + 1);
}
```

三目运算读作「取较大的那个加 1」。这里用 `>` 而不是 `>=` 是任意的——两侧等高时结果一样。

**调用顺序是正确性的关键**：旋转改变了两个节点的孩子，所以两个节点的高度都需要重算，且**必须先算子节点、再算父节点**。以 `rotate_left` 为例：

```
旋转前：T 是父，R 是子
旋转后：R 是父，T 是子
```

所以必须先 `fix_height(T)`（此时 T 是子），再 `fix_height(R)`（此时 R 是父）。如果顺序反了，`fix_height(R)` 读到的 `T->height` 还是旧值，算出来的 R 高度就是错的。

双旋的情形要 fix 三个节点，顺序同样是「从新的叶子往上」：

```c0
/* rotate_right_left 的一种写法，见习题 Ex11 */
tree* rotate_right_left(tree* T) {
  tree* X = T;
  tree* Z = T->right;
  tree* Y = T->right->left;
  X->right = Y->left;
  Z->left  = Y->right;
  Y->left  = X;
  Y->right = Z;
  fix_height(X);     /* 先：X 现在是最下层 */
  fix_height(Z);     /* 再：Z 在中间层 */
  fix_height(Y);     /* 最后：Y 是新的根 */
  return Y;
}
```

### 5.6 插入的完整流程

```c0
tree* avl_insert(tree* T, entry e)
/*@requires is_avl(T) && e != NULL;
  @ensures is_avl(\result);
  @*/
{
  if (T == NULL) return leaf(e);

  int cmp = key_compare(entry_key(e), entry_key(T->data));
  if (cmp == 0) {
    T->data = e;                 /* 覆盖，高度不变 */
  } else if (cmp < 0) {
    T->left = avl_insert(T->left, e);
    T = rebalance_left(T);       /* 可能旋转，也可能只 fix_height */
  } else {
    T->right = avl_insert(T->right, e);
    T = rebalance_right(T);
  }
  return T;
}
```

四个要点：

1. **`leaf(e)`** 是一个辅助函数，分配新节点并把 `height` 初始化为 1。如果忘了初始化 `height`，整棵树的高度信息就全错了。
2. **`cmp == 0` 分支不需要 rebalance**。覆盖只改 `data`，不改结构，高度不变。
3. **`rebalance_left` 在递归返回后调用**，此时左子树已经是 AVL 且高度可能 +1。这个顺序不能颠倒——先修复子树，再修当前节点。
4. **`rebalance_left` 必须返回（可能的新）根**，因为旋转会换根。这就是为什么写 `T = rebalance_left(T);` 而不是 `rebalance_left(T);`。

`rebalance_right` 的完整实现（讲义第 13 页）：

```c0
tree* rebalance_right(tree* T)
/*@requires T != NULL && is_avl(T->left) && is_avl(T->right);
  @requires abs(height(T->right) - height(T->left)) <= 2;
  @ensures is_avl(\result);
  @*/
{
  if (height(T->right) - height(T->left) == 2) {
    if (height(T->right->right) > height(T->right->left)) {
      T = rotate_left(T);                    /* RR */
    } else {
      T->right = rotate_right(T->right);     /* RL 第一步 */
      T = rotate_left(T);                    /* RL 第二步 */
    }
  } else {
    fix_height(T);                           /* 没失衡，只更新高度 */
  }
  return T;
}
```

注意 `else` 分支：**即使没有失衡也必须 `fix_height`**，因为插入可能让高度从 h 变成 h+1 而没有触发旋转。漏掉这一步，父节点读到的高度就是过期的。

`rebalance_left` 完全对称：判据是 `height(T->left) - height(T->right) == 2`，外侧判据是 `height(T->left->left) > height(T->left->right)`。

### 5.7 检查不变式

三个谓词，逐层加强：

```c0
/* 1. 高度字段与实际结构一致 */
bool is_specified_height(tree* T) {
  if (T == NULL) return true;
  return T->height == (height(T->left) > height(T->right)
                       ? height(T->left) : height(T->right)) + 1
      && is_specified_height(T->left)
      && is_specified_height(T->right);
}

/* 2. 平衡 */
bool is_balanced(tree* T) {
  if (T == NULL) return true;
  int diff = height(T->right) - height(T->left);
  return abs(diff) <= 1
      && is_balanced(T->left)
      && is_balanced(T->right);
}

/* 3. AVL = 有序 + 平衡 + 高度正确 */
bool is_avl(tree* T) {
  return is_bst(T) && is_specified_height(T) && is_balanced(T);
}
```

**为什么 `is_avl` 里要包含 `is_specified_height`？** 因为 `is_balanced` 用的是 `height()`，而 `height()` 读的是缓存字段。如果缓存是错的，`is_balanced` 的判断就毫无意义。**任何依赖缓存的不变式，都必须同时断言缓存本身正确。** 这是「用空间换时间」时普遍要付的契约代价。

### 5.8 实验数据：可预测性比平均值更重要

讲义第 7 节给出了一组测量（n 从 2⁹ 到 2¹⁵，插入 n 个随机元素）：

| n | AVL 树耗时 | 普通 BST 耗时 |
|---|---|---|
| 2⁹ = 512 | 0.129 | 1.018 |
| … | … | … |
| 2¹⁵ = 32768 | 13.785 | 48.242 |

两个观察：

1. **AVL 更快**，差距随 n 增大而扩大（约 3.5 倍）。
2. **普通 BST 的耗时不可预测**——同样的 n、不同的随机种子，耗时可能相差数倍。AVL 的耗时则与 n log n 高度吻合。

第二点比第一点更重要。工程上，「稳定地慢」往往比「有时快有时极慢」更可接受，因为后者会让容量规划、超时设置、性能回归测试全部失效。这也是为什么标准库里的有序容器（C++ `std::map`、Java `TreeMap`）都用平衡树而非裸 BST。

### 5.9 习题要点

- **Ex1（第 15 页，解在第 17 页）**：给出一组插入序列，画出每次插入后的树。要点是每次插入后**从插入点往上找第一个失衡节点**，只修那一个。
- **Ex2（解在第 17–19 页）**：依次插入 1, 10, 5, 7, 3, 13, 6, 4, 8, 9。三个关键节点：
  - 插入 5 时：1 的右子树（10）比左子树高 2，且 10 的左孩子（5）比右孩子高 → **RL 情形，双旋**。
  - 插入 4 时：**单左旋**。
  - 插入 9 时：**双右旋**。
- **Ex3（解在第 19–20 页）**：给定失衡形状，判断用单旋还是双旋。判据就是「失衡发生在内侧还是外侧」。
- **Ex4（解在第 20–21 页）**：给定插入序列 20, 6, 45, 96, 80，画出每步的树并标注旋转点。
- **Ex11（解在第 27–29 页）**：把双旋写成一个函数 `rotate_right_left`。这是很好的练习，因为双旋写成单函数后必须正确处理三组指针与三次 `fix_height` 的顺序。讲义给的实现见 5.5 节末尾。

## 6. 代码示例

### 6.1 官方课程代码

以下代码出自 `16-avl.pdf`，页码为该 PDF 的页码。

**（1）旋转**（第 5–6 页）

`rotate_left`：`tree* R = T->right; T->right = T->right->left; R->left = T; return R;`，前置 `T != NULL && T->right != NULL`。`rotate_right` 对称。

**（2）高度不变式与缓存字段**（第 12 页）

```c0
struct tree_node {
  entry data;
  int height;
  tree* left;
  tree* right;
};
int height(tree* T) { return T == NULL ? 0 : T->height; }
```

**（3）`fix_height`**（第 12 页）

`T->height = (hl > hr ? hl + 1 : hr + 1);`

**（4）`avl_insert`**（第 12 页）

NULL → `leaf(e)`；`cmp == 0` 覆盖；`cmp < 0` → `T->left = avl_insert(T->left, e); T = rebalance_left(T);`；否则对称。

**（5）`rebalance_right`**（第 13 页）

高度差为 2 时按「右子的右子 vs 右子的左子」选单旋或双旋；否则 `fix_height(T)`。

**（6）不变式检查**（第 8–11 页）

`is_specified_height`、`is_balanced`、`is_avl` 三层谓词。

**（7）实验**（第 13–14 页）

n 从 2⁹ 到 2¹⁵ 的耗时对比表。

**（8）习题与答案**（第 15–16 页题目，第 17–29 页答案）

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念

**示例一：打印平衡因子，直观看到失衡与修复。**

```c0
int balance_factor(tree* T)
/*@requires T != NULL;
  @ensures -2 <= \result && \result <= 2;
  @*/
{
  return height(T->right) - height(T->left);
}

void print_bf(tree* T) {
  if (T == NULL) return;
  print_bf(T->left);
  printint(balance_factor(T));   /* 中序：输出顺序 = 键升序 */
  print_bf(T->right);
}
```

在插入序列 1, 10, 5, 7, 3 的每一步后调用 `print_bf`，能亲眼看到某个节点的平衡因子从 0 变 1 变 2，然后在下一步回到 0 或 ±1。**调试平衡树时，打印平衡因子比打印整棵树有效得多**——因为失衡是一个局部量。

**示例二：验证「旋转保持中序遍历」。**

```c0
bool same_inorder(tree* A, tree* B)
/*@requires is_bst(A) && is_bst(B);
  @*/
{
  if (A == NULL && B == NULL) return true;
  if (A == NULL || B == NULL) return false;
  return key_compare(entry_key(A->data), entry_key(B->data)) == 0
      && same_inorder(A->left,  B->left)
      && same_inorder(A->right, B->right);
}
```

对一个满足 `T->right != NULL` 的 T，`same_inorder(T, rotate_left(T))` 应为 true。这个测试不检查形状（形状本来就变了），只检查「键序列一致」——正好对应旋转的唯一承诺。

**示例三：递归计算「最少节点数」，验证 5.1 节的引理。**

```c0
/* 高度为 h 的 AVL 树最少需要多少节点 */
int min_nodes(int h)
/*@requires h >= 0;
  @ensures \result >= 0;
  @*/
{
  if (h == 0) return 0;
  if (h == 1) return 1;
  return min_nodes(h-1) + min_nodes(h-2) + 1;
}
```

手算前几项：h=0→0、h=1→1、h=2→2、h=3→4、h=4→7、h=5→12、h=6→20、h=7→33、h=8→54。与斐波那契的比值稳定在约 1.44^h，验证了 5.1 节的结论。

反过来算：**n = 1000 时 AVL 的最大高度是多少？** 查表：h=15 → 1596 个节点（F(15) = 1596），h=14 → 986。所以 1000 个节点的 AVL 树高度最多 15，而完美平衡是 ⌈log₂(1001)⌉ = 10。**最多高 50%**，与理论吻合。

**示例四：一个「只做单旋会失败」的反例。**

构造 RL 情形并只做单旋：

```c0
void wrong_single_rotation() {
  tree* T = NULL;
  T = avl_insert(T, mk_entry(10));   /* 10 */
  T = avl_insert(T, mk_entry(20));   /* 10 -> 20 */
  T = avl_insert(T, mk_entry(15));   /* 10 -> 20 -> 15（左） */
  /* 此时 10 的平衡因子 = 2，且是 RL 情形 */
  /* 错误做法：只做 rotate_left(T) */
  tree* bad = rotate_left(T);
  /* bad 的平衡因子仍是 2，没有修复 */
  /* 正确做法：T->right = rotate_right(T->right); T = rotate_left(T); */
}
```

手工追踪：旋转前 T=10、右子 20、20 的左子 15。左旋后新根 20，20 的左子 10，10 的右子 15。此时 20 的左子树高度 2（10→15），右子树高度 0，平衡因子 −2。**没修好**。这就是双旋存在的理由。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键区别 | 记忆点 |
|---|---|---|---|
| Height Invariant（高度不变式） | Ordering Invariant（有序不变式） | 前者约束**形状**（差 ≤ 1），后者约束**键序**（左小右大） | AVL = BST + 高度不变式 |
| 单旋 `rotate_left` | 双旋（`rotate_right` 后 `rotate_left`） | 单旋用于外侧（RR/LL），双旋用于内侧（RL/LR） | 「外侧单、内侧双」 |
| `rotate_left(T)` | `T = rotate_left(T)` | 前者丢弃返回值 = 白做；后者把新根接回去 | 旋转**换根**，必须赋值 |
| `height(T)`（O(1)） | `tree_height(T)`（O(n)） | 前者读缓存字段，后者递归计算；前者要求缓存正确 | 「读字段 vs 数节点」 |
| `is_balanced` | `is_specified_height` | 前者检查差 ≤ 1，后者检查缓存字段本身对不对 | 缓存错了，平衡检查就没意义 |
| 插入后最多 1–2 次旋转 | 删除后可能 O(log n) 次 | 插入让高度 +1，旋转能吸收；删除让高度 −1，变矮会传播 | 本讲只讲插入 |
| AVL 树 | 完美平衡树 | 前者高度可达 1.44·log₂n，后者恰为 ⌈log₂(n+1)⌉ | AVL 允许「略歪」以换取插入代价低 |
| 本讲 C0 代码 | 标准 C | C0 有 `alloc`、`//@`、垃圾回收；标准 C 要 `malloc`/`free`（第 17 讲起） | **本讲不是标准 C** |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-122/lectures/16-avl.pdf`
- **总页数**：29 页
- **本节重点页码**（PDF 页码，即提取文本中 `=== [page N] ===` 的 N）：
  - 第 2–4 页：高度不变式的陈述与「为什么它能保证 O(log n)」的直觉
  - 第 4–6 页：`rotate_left` / `rotate_right` 的代码与图示
  - 第 6 页：查找（与 BST 完全相同，因为 AVL 是 BST）
  - 第 6–8 页：插入流程、四种失衡情形、单旋 vs 双旋的判据
  - 第 8–11 页：`is_specified_height`、`is_balanced`、`is_avl` 三层谓词
  - 第 12 页：`struct tree_node` 增加 `height` 字段、`height()`、`fix_height`、`avl_insert`
  - 第 13 页：`rebalance_right` 的完整实现（含 `else fix_height(T);`）
  - 第 13–14 页：实验数据（AVL vs 普通 BST，n 从 2⁹ 到 2¹⁵）
  - 第 15–16 页：习题 Ex1–Ex11
  - 第 17–29 页：参考答案（Ex2 的插入序列在第 17–19 页，Ex11 的 `rotate_right_left` 在第 27–29 页）
- **原始网页链接**：`https://www.cs.cmu.edu/~15122-archive/f26/handouts/lectures/16-avl.pdf`
- **配套代码包**：`90-原始PDF/15-122/code/16-avl.tgz`

## 9. 对应视频

未找到官方公开录像。本讲强烈建议配合纸笔：把 `rotate_left` 的三行代码在每个指针上手工画一遍，比读十遍文字有效。习题 Ex2 的十次插入值得完整手算一次。

## 10. 本节复习

1. Height Invariant：每个节点左右子树高度差 ≤ 1。它把「全局高度」约束到 O(log n)：高度 h 的 AVL 树至少 F(h) 个节点，F 与斐波那契同阶，故 h ≤ 1.44·log₂n + O(1)。
2. 旋转保持中序序列不变，因此保持有序不变式。`rotate_left` 三步：记住右子 → 右子的左子过继给自己 → 自己挂到右子左边。
3. 旋转**换根**，所以必须写 `T = rotate_left(T)`。前置条件 `T->right != NULL` 不可省。
4. 外侧（RR/LL）用单旋，内侧（RL/LR）用双旋。内侧单旋修不好，因为高度没降下来。
5. 一次插入最多 1 次单旋或 1 次双旋，且修完不需要继续上溯——因为旋转后子树高度回到插入前的值。
6. 缓存 `height` 字段把 `height()` 从 O(n) 降到 O(1)，代价是必须维护：旋转中先 `fix_height` 子节点、再 `fix_height` 父节点；没失衡时也要 `fix_height`。
7. `is_avl = is_bst && is_specified_height && is_balanced`。缓存字段本身正确性必须作为不变式的一部分，否则平衡检查失去意义。
8. 实验表明 AVL 比普通 BST 快约 3.5 倍，更重要的是**耗时稳定可预测**——这是工程上选择平衡树的真正理由。

## 11. 自我检查

**题 1.** 对下面的树，判断它是否是 AVL 树。若不是，指出所有失衡节点，并说明应做哪种旋转（单旋还是双旋、在哪个节点上）。

```
        50
       /  \
     30    70
     / \     \
   20   40    90
   /
  10
```

**题 2.** 执行 `rotate_left` 前树为：T 的键 10，T 的右子 R 键 20，R 的左子 B 键 15，R 的右子 C 键 25。写出旋转后每个节点的 `left`、`right`、`height`（设叶子高度为 1），并验证中序序列不变。

**题 3.** 为什么 `rebalance_right` 的 `else` 分支必须写 `fix_height(T)`？如果不写会发生什么？请举一个具体的插入序列说明。

**题 4.** 1000 个节点的 AVL 树，最大可能高度是多少？完美平衡的 1000 节点二叉树高度是多少？两者相差多少倍？

**题 5.** 若把 `rebalance_right` 的判据 `height(T->right->right) > height(T->right->left)` 改成 `>=`，程序还正确吗？会有什么性能影响？

<details>
<summary>参考答案</summary>

**答 1.** **不是 AVL 树**。逐节点算平衡因子（height 用节点数）：

- 节点 10：叶子，h=1，bf=0 ✓
- 节点 20：左子树 h=1，右子树 h=0，h=2，bf = 0−1 = −1 ✓
- 节点 40：叶子，h=1，bf=0 ✓
- 节点 30：左子树（20）h=2，右子树（40）h=1，h=3，bf = 1−2 = −1 ✓
- 节点 90：叶子，h=1，bf=0 ✓
- 节点 70：左子树 h=0，右子树（90）h=1，h=2，bf = 1−0 = +1 ✓
- 节点 50：左子树（30）h=3，右子树（70）h=2，h=4，bf = 2−3 = **−1** ✓

所有节点的平衡因子都在 [−1, 1] 内，所以**这棵树是 AVL 树**。

（这道题的目的是提醒：不要看到「一边深一边浅」就断定失衡，必须真的算高度。这里 30 的子树虽然左边多一层，但差值只有 1。）

**答 2.** 旋转前：

```
      T(10)               R(20)
      /  \                /  \
         R(20)    ==>   T(10) C(25)
        /  \             /
      B(15) C(25)      B(15)
```

（T 没有左子树。）

旋转后各节点：

| 节点 | left | right | height |
|---|---|---|---|
| T(10) | NULL | B(15) | 2 |
| B(15) | NULL | NULL | 1 |
| C(25) | NULL | NULL | 1 |
| R(20) | T(10) | C(25) | 3 |

计算过程：`fix_height(T)`：hl = height(NULL) = 0，hr = height(B) = 1，T->height = 2。`fix_height(R)`：hl = height(T) = 2，hr = height(C) = 1，R->height = 3。

中序序列：旋转前 = T(10), B(15), R(20), C(25)；旋转后 = T(10), B(15), R(20), C(25)。**一致** ✓。

注意新根 R 的高度是 3，与旋转前 T 的高度（1 + max(0, 3) = 4？）不同——因为这道题的旋转前 T 高度是 1 + max(0, height(R)) = 1 + 3 = 4。旋转后变成 3，**高度降低了 1**。这正好说明旋转是「修复失衡」而非「保持高度」：当旋转由插入触发时高度会回到插入前的值，而这里我们是对一棵本来就不平衡的树做旋转，所以高度会变。

**答 3.** `else` 分支处理「没有失衡」的情形（高度差不是 2）。此时不需要旋转，但**高度可能已经变了**：插入让某个子树从 h 变成 h+1，当前节点的 `height` 字段必须相应更新。

不写 `fix_height(T)` 的后果：当前节点的 `height` 保持旧值，而实际高度已经 +1。父节点读到的是过期的高度，于是：
1. 父节点的 `is_balanced` 判断基于错误数据，可能**漏判**真正的失衡；
2. 父节点的 `fix_height` 算出错误的高度，错误继续向上传播；
3. 最终 `is_specified_height` 失败，整棵树不再是 AVL。

**具体序列**：空树依次插入 10、5、7。
- 插入 10：根 10，h=1。
- 插入 5：10 的左子 5，`rebalance_left(10)` 被调用。高度差 = height(NULL) − height(5) = 0 − 1 = −1，不是 2，走 `else` → `fix_height(10)` → 10 的 h=2。✓
- 若漏掉 `fix_height(10)`：10 的 h 仍是 1。
- 插入 7：7 走到 5 的右边。`rebalance_left(5)`：差 = 0 − 1 = −1，`else` → fix_height(5) → h=2。然后 `rebalance_left(10)`：差 = height(NULL) − height(5) = 0 − 2 = −2 → 触发旋转。这里恰好还能工作。
- 但继续插入 3、1 等，错误的 h 会让「差 == 2」的判断在错误的时机触发或漏触发，最终 `is_avl` 检查失败。

更直接的观察：**任何改变子树的路径都必须更新高度**，这是「缓存一致性」的基本要求，没有例外。

**答 4.**
- **AVL 最大高度**：用 5.1 节的 F(h)（最少节点数）表：F(14) = 986、F(15) = 1596。1000 > 986，所以高度 14 装不下 1000 个节点，最小高度为 **15**。（即 1000 个节点的 AVL 树高度最大可达 15。）
- **完美平衡**：n 个节点的完美平衡二叉树高度 = ⌈log₂(n+1)⌉ = ⌈log₂(1001)⌉ = ⌈9.967⌉ = **10**。
- **比值**：15 / 10 = **1.5 倍**。

与理论值 1.44 吻合（log_φ(1000) ≈ 14.4，加上常数项后约 15）。这个 50% 的高度代价换来了「插入只需 O(log n) 且无需重构整棵树」，非常划算。

**答 5.** **程序仍然正确**，但有性能影响。

正确性：当两侧等高（`height(T->right->right) == height(T->right->left)`）时，无论选单旋还是双旋，都能恢复平衡——因为等高时两种旋转都有效（此时子树形状对称，单旋后高度也能降下来）。所以 `>=` 不会引入错误。

性能影响：`>=` 会在等高时选**单旋**，而 `>` 会在等高时选**双旋**。单旋只做 1 次旋转 + 2 次 `fix_height`，双旋做 2 次旋转 + 3 次 `fix_height`。所以 `>=` 在等高情形下**更快**。

那为什么讲义用 `>`？因为等高时选双旋是「更保守」的选择：双旋在等高情形下必然恢复平衡，而单旋的正确性依赖于「外侧确实更高」这个前提——虽然等高时也能work，但论证要多一步。用 `>` 让「外侧严格更高 → 单旋」的推理链更干净，代价是偶尔多做一次旋转。这是**可证明性优先于常数优化**的典型取舍，很符合 15-122 的风格。

</details>

## 12. 进一步学习

- 上一讲：[[15-122-15-Binary-Search-Trees]] —— 有序不变式与 `bst_insert`，本讲在它之上加一条高度不变式。
- 下一讲：[[15-122-17-Introduction-to-C]] —— **语言分界点**：从这里开始是标准 C，不再有 `alloc` 与 `//@` 契约。
- 相关：[[15-122-25-Priority-Queues]] —— 另一种「用形状不变式换复杂度」的数据结构，堆的形状不变式比 AVL 更强（完全树），但只要求偏序。
- 相关：[[15-122-26-Restoring-Invariants]] —— 把「临时违反不变式再恢复」这个方法论讲透，AVL 的旋转正是这个方法的一个实例。
- 课程入口：[[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]]、[[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 术语查询：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（AVL Tree、Rotation、Height、Balance 等条目）。
