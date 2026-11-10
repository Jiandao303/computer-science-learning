---
course: CMU 15-122
course_name: Imperative Computation
semester: Fall 2026
lecture_id: L07
topic: Quicksort
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-122
  - 快速排序
  - C0
---

# 第 7 讲：快速排序（Quicksort）

## 1. 本节学习目标

学完本讲后，你应该能够：

1. 用「分治（divide-and-conquer）」的三步框架描述快速排序：选枢轴、划分、递归排序两段。
2. 说明快速排序与归并排序（mergesort）在「划分 vs 合并」上的**成本位置相反**这一权衡。
3. 推导最好情况 `O(n log n)` 与最坏情况 `O(n²)`，并解释为什么**随机选枢轴**能让期望复杂度与输入分布无关。
4. 解释 `in-place`（原地）的含义，并说明为什么「临时数组版 partition」不是原地的。
5. 写出原地划分（in-place partition）的三条循环不变式，特别是 `ge_seg(pivot, A, lo+1, left)` 里为什么是 `lo+1` 而**不是** `lo`。
6. 证明划分结束时 `left == right`，以及 `swap(A, lo, left-1)` 为什么能完成划分。
7. 用**契约**（而不是展开递归）推理递归函数：只检查前置、只假设后置。
8. 证明两个递归调用的参数都**严格更小**，从而终止。
9. 说明 `stable`（稳定）的定义，并举例说明选择排序与快速排序都不稳定、归并排序稳定。

## 2. 前置知识

- [[15-122-06-Binary-Search]]：分治思想；用「区间长度严格递减」证终止。
- [[15-122-05-Big-O]]：`O(n²)` 与 `O(n log n)`；`n(n-1)/2` 求和；最紧界的要求。
- [[15-122-04-Searching-Arrays]]：`is_sorted`、`le_seg`、`le_segs` 等规格函数；`ge_seg` 是 `le_seg` 的镜像。
- [[15-122-03-Arrays]]：`swap`、`alloc_array`、数组别名。
- [[15-122-01-Contracts]]：递归函数用契约推理的原则；终止性 vs 部分正确性。

## 3. 核心概念

**Divide and Conquer（分治）**：把问题分成若干**可独立求解**的子问题，分别求解，再合并结果。三个动作是 divide（划分）、conquer（递归求解）、combine（合并）。

**Pivot（枢轴）**：快速排序中选出的参照元素。划分后它左边全 `<=` 它，右边全 `>=` 它，且它已落在最终位置上。

**Partition（划分）**：把数组段重排成「小的一堆 | 枢轴 | 大的一堆」的过程，返回枢轴的新下标。

**In-Place（原地）**：算法只使用**常数**额外空间（不含递归栈）。选择排序与快速排序是原地的，归并排序不是。

**Randomized Algorithm（随机化算法）**：算法内部使用随机数。快速排序随机选枢轴后，**期望**运行时间与输入的具体排列无关。

**Stable Sort（稳定排序）**：若两个元素在排序键上相等，排序后它们的**相对次序保持不变**，则该排序稳定。

**Purity（纯性）**：契约中调用的函数不得分配或修改已分配内存。纯函数才能在 `//@` 契约里使用，否则带 `-d` 与不带 `-d` 的运行结果可能不同。

**Permutation（排列）**：输出数组是输入数组的一个重排。排序函数的完整规格应包含「有序」+「是输入的排列」，但本讲只形式上表达前者。

## 4. 通俗理解

**快速排序 = 排队时随便找一个人当标杆**：让比他矮的站左边、比他高的站右边，然后左右两堆各自重复这个流程。标杆自己的位置就此确定，不用再动。

**与归并排序的分工正好相反**：快速排序「划分累、合并省」——划分要看每个元素（线性时间），但两段排好后整个数组自动就有序了，什么都不用做。归并排序「划分省、合并累」——对半切一刀就完事（`O(1)`），但把两个有序段合成一个有序段要线性时间和线性额外空间。

讲义的原话：**「In quicksort, dividing the problem into subproblems will be linear time, but putting the results back together is immediate. This kind of trade-off is frequent in algorithm design.」**

**为什么随机枢轴如此关键**：如果每次都取第一个元素当枢轴，那么**给一个已经排好序的数组，快速排序会退化成 `O(n²)`**——因为每次划分都得到「空 | 枢轴 | 其余全部」，`n` 层递归，每层 `O(n)`。这是最讽刺的情形：**排序算法被有序输入打败**。而随机选枢轴后，无论输入长什么样，期望都是 `O(n log n)`。

**为什么 `ge_seg` 的起点是 `lo+1` 而不是 `lo`**：枢轴被暂存在 `A[lo]`。如果把 `lo` 也纳入「左边那堆」，不变式 `pivot >= A[lo+1..left)` 就变成 `pivot >= A[lo..left)`，即 `pivot >= pivot`——这倒是真的，但**一旦 `left` 越过 `lo+1`，`A[lo]` 里的枢轴就可能被交换走**，`A[lo] = pivot` 这条就断了。讲义在代码注释里专门写了 `// Not lo!`。

**为什么稳定性值得关心**：讲义举的例子是「按学号排好的学生名单，再按讲次排序」。如果排序不稳定，同一讲次内的学生顺序就被打乱了，之前的排序白做。**这就是「多关键字排序」依赖稳定性的原因**（先按次要键排，再按主要键排）。

## 5. 原理与推导

### 5.1 分治的三个动作

快速排序：

1. **Divide**：选枢轴 `pivot`，把段 `A[lo..hi)` 重排成 `A[lo..mid)` 全 `<= pivot`、`A[mid] == pivot`、`A[mid+1..hi)` 全 `>= pivot`。返回 `mid`。**代价 `O(k)`，`k = hi - lo`。**
2. **Conquer**：递归排序 `A[lo..mid)` 与 `A[mid+1..hi)`。
3. **Combine**：**什么都不用做**。因为枢轴已在最终位置，且左边全不大于它、右边全不小于它。

归并排序：

1. **Divide**：算中点 `mid = lo + (hi-lo)/2`。**代价 `O(1)`。**
2. **Conquer**：递归排序两半。
3. **Combine**：`merge` 两个有序段。**代价 `O(k)` 时间 + `O(k)` 空间。**

### 5.2 划分阶段为什么是线性的

讲义举例：数组 `3, 1, 4, 4, 7, 2, 8`，取 `3` 当枢轴。要把每个元素与 `3` 比一次，才能决定它归左边还是右边。**「每个元素比一次」= `O(k)`。** 除此之外只是搬运元素，也是常数次操作/元素。

注意枢轴取 `3` 时，左边得到 `2, 1`，右边得到 `4, 7, 8, 4`——**段内顺序任意**。讲义强调：只要「小的都在左、大的都在右」，段内怎么排都无所谓，递归会处理。

### 5.3 最好情况：`O(n log n)`

枢轴恰好是中位数（median）时，两段各占一半。递推：

```
T(n) = 2*T(n/2) + c*n
```

展开（设 `n = 2^k`）：

```
T(n) = 2*T(n/2) + cn
     = 2*(2*T(n/4) + c*n/2) + cn = 4*T(n/4) + 2cn
     = 4*(2*T(n/8) + c*n/4) + 2cn = 8*T(n/8) + 3cn
     = ...
     = 2^j * T(n/2^j) + j*c*n
```

取 `j = k = log2 n`，`T(1) = O(1)`：

```
T(n) = n*O(1) + (log2 n)*c*n = O(n log n)
```

**直观版**：共 `log2 n` 层，每层所有划分加起来处理 `n` 个元素，故每层 `O(n)`，总 `O(n log n)`。

### 5.4 最坏情况：`O(n²)`

最坏时每次都选到最小或最大元素，划分成「空」与「其余 `n-1` 个」。

讲义的表（原文用方括号标出未排序部分）：

| 数组 | 枢轴 |
|---|---|
| `[3, 1, 4, 4, 8, 2, 7]` | 1 |
| `1, [3, 4, 4, 8, 2, 7]` | 2 |
| `1, 2, [3, 4, 4, 8, 7]` | 3 |
| `1, 2, 3, [4, 4, 8, 7]` | 4 |
| `1, 2, 3, 4, [4, 8, 7]` | 4 |
| `1, 2, 3, 4, 4, [8, 7]` | 7 |
| `1, 2, 3, 4, 4, 7, [8]` | — |

**规模为 `n` 时共有 `n-1` 次「有意义的」递归调用**（其余调用都是空段）。第 `k` 次调用要划分长度 `n-k` 的段，代价 `O(n-k)`。

总比较次数（`c` 为常数）：

```
c * Σ_{k=0}^{n-1} k = c * n(n-1)/2 ∈ O(n²)
```

**最后一步的依据**：多项式的大 O 只取最高次幂，且忽略常数系数。这与 [[15-122-05-Big-O]] 的结论一致。

### 5.5 随机化：把最坏情况变成「极不可能」

**固定策略必然有克星输入**：

- 总取第一个元素 → 已排序（或「几乎有序」）的数组退化成 `O(n²)`。
- 总取最后一个元素 → 逆序数组退化。
- 总取中间元素 → 存在专门构造的对抗性输入（习题 3 就是一个七元素例子）。

**随机选枢轴后**：无论输入数组长什么样，**期望运行时间都是 `O(n log n)`**。仍有可能随机抽到坏的枢轴序列，但概率极低。

讲义明确指出：**证明这一点超出本课程范围**（属于概率分析/随机算法课程）。但它给出了一个重要的方法论结论：

> **「This is an important example on how to exploit randomness to obtain a reliable average case behavior, no matter what the distribution of the input values.」**

**注意「平均情况」与「期望情况」的区别**：传统「平均情况分析」要对输入分布做假设（例如「所有排列等概率」），而随机化算法的期望是对**算法自己的随机选择**取期望，**与输入无关**。这是一个更强的保证。

**为什么不用「精确求中位数」**：中位数可以在 `O(n)` 时间内算出，但常数因子大，实践中几乎没人这么做。随机选枢轴的期望性能已经足够好。

### 5.6 递归函数如何用契约推理

讲义给出两条规则（对本讲的 `sort` 尤其重要）：

1. **必须确认被调函数的前置条件成立。**
2. **可以假设被调函数的后置条件成立**（返回后）。

**关键点：不要展开递归去分析**。哪怕调用的是自己，也把它当成一个「黑盒」——只要前置满足，它就保证后置。这是**把 what（契约）与 how（实现）分离**的典范。

### 5.7 主函数与终止性

```c0
void sort(int[] A, int lo, int hi)
//@requires 0 <= lo && lo <= hi && hi <= \length(A);
//@ensures is_sorted(A, lo, hi);
{
  if (hi-lo <= 1) return;
  int pi = lo + (hi-lo)/2;   /* should be random */
  int mid = partition(A, lo, pi, hi);
  sort(A, lo, mid);
  sort(A, mid+1, hi);
  return;
}
```

**基本情况**：`hi - lo <= 1`，即 0 或 1 个元素，**天然有序**，直接返回。

**终止性**：需要证明两个递归调用的参数都严格更小。设 `D = hi - lo`。

- 第一次调用：`mid - lo`。由 `partition` 的后置 `lo <= \result && \result < hi` 得 `mid < hi`，故 `mid - lo < hi - lo = D`。**严格更小。**
- 第二次调用：`hi - (mid+1)`。由后置 `lo <= mid` 得 `lo < mid + 1`，故 `hi - (mid+1) < hi - lo = D`。**严格更小。**

两个子问题的规模都严格小于 `D`，而 `D` 是非负整数，不可能无限递减——**终止**。

> **原文异常**：第 5–6 页讲义写「The expression `hi − lo` is divided by two for each recursive call and is therefore smaller since it is always greater or equal to 2」。这句话对**归并排序**成立（对半切），对**快速排序不成立**——快速排序的划分点由枢轴决定，可能是 `lo`（左段空），此时右段只小 1。真正保证严格递减的是 `partition` 的后置条件 `lo <= \result < hi`，而不是「除以二」。第 8 页给出的论证才是正确的（用后置条件），第 5–6 页那段话疑为从归并排序章节残留下来的笔误。

### 5.8 划分：从「临时数组」到「原地」

**朴素想法**：新建临时数组，把小于枢轴的放左边、大于等于的放右边，中间空一格放枢轴，最后整体拷回。

**问题**：每次调用 `partition` 都分配一个与原段等长的数组，**不是原地的**。而选择排序是原地的（不分配任何临时空间）。讲义把「最多分配常数空间」定义为 in-place。

**原地的难点**：**不知道枢轴最终会落在哪**——因为不知道有多少元素比它小。而且返回的下标**可能与传入的枢轴下标不同**（讲义脚注：想象有多个元素等于枢轴值）。

**原地方案**：

1. 把枢轴交换到段首 `A[lo]`，暂存起来。
2. 设两个指针 `left = lo+1`、`right = hi`。
3. 反复：若 `A[left] <= pivot`，`left++`（它已在正确的一侧）；否则把 `A[left]` 换到 `A[right-1]` 并 `right--`（它属于右侧）。
4. `left == right` 时停止，把 `A[lo]` 的枢轴换到 `A[left-1]`，返回 `left-1`。

### 5.9 三条不变式的来源

讲义在逐步手工执行算法后「读出」三条不变式：

```
(1) pivot >= A[lo+1..left)        -- 左段全部不大于枢轴
(2) pivot <= A[right..hi)         -- 右段全部不小于枢轴
(3) A[lo] = pivot                 -- 枢轴暂存在段首
```

再加上范围关系：

```
(4) lo+1 <= left <= right <= hi
```

**为什么 (4) 的下界是 `lo+1` 而不是 `lo`**：`left` 从 `lo+1` 出发（跳过暂存的枢轴），且只会增加。若允许 `left == lo`，不变式 (1) 的段 `A[lo+1..lo)` 就是「反向段」，语义崩坏。

**为什么 `right` 的上界是 `hi`**：`right` 从 `hi` 出发，只会减小。

### 5.10 初始化（INIT）

`left = lo+1`、`right = hi`。

- (4)：`lo+1 <= lo+1 <= hi <= hi`。**`lo+1 <= hi` 需要 `lo < hi`**——这正是 `partition` 前置条件里的 `lo <= pi < hi`（由 `lo <= pi` 与 `pi < hi` 得 `lo < hi`）。**讲义特别强调这一点：「The crucial observation here is that `lo < hi` by the precondition of the function.」**
- (1)：段 `A[lo+1..lo+1)` 为空，**空真**。
- (2)：段 `A[hi..hi)` 为空，**空真**。
- (3)：`swap(A, lo, pi)` 之后 `A[lo]` 就是原 `A[pi]`，即 `pivot`。

**「空段 + 空真」再次成为 INIT 的钥匙**（与 [[15-122-05-Big-O]] 的选择排序、[[15-122-06-Binary-Search]] 的析取项同源）。

### 5.11 保持性（PRES）

假设四条不变式成立且守卫 `left < right` 成立。两种情形：

**情形 `A[left] <= pivot`**：`left' = left + 1`，`right' = right`。

- (1)：新段是 `A[lo+1..left+1)` = 旧段 ∪ `{A[left]}`。旧段已满足，新增元素 `A[left] <= pivot`。**成立。**
- (2)：`right` 不变。**成立。**
- (3)：`A[lo]` 未被触碰（因为 `left >= lo+1 > lo`）。**成立。**
- (4)：`left' = left+1 <= right`（由守卫 `left < right`）；其余显然。

**情形 `A[left] > pivot`**：`swap(A, left, right-1)`，`right' = right - 1`，`left' = left`。讲义用 `//@assert A[left] > pivot;` 记下「前两个测试都失败」的结论（`<=` 失败即 `>`）。

- (2)：新段 `A[right-1..hi)` = 旧段 `A[right..hi)` ∪ `{A[right-1]}`。交换后 `A[right-1]` 里放的是**原来的 `A[left]`**，它 `> pivot`。旧段已满足。**成立。**
- (1)：`left` 不变，但**段内容变了**——`A[left]` 位置现在放的是原来的 `A[right-1]`。需要 `A[right-1] <= pivot`？**不！** 这里必须小心：旧不变式 (1) 说的是 `A[lo+1..left)` 全部 `<= pivot`，而位置 `left` **不在**这个段内（段是半开的，`left` 是右端点）。所以 `A[left]` 的内容变化**不影响** (1)。**这就是「不变式用半开区间」带来的便利：当前待处理的元素恰好在段外，可以自由改动。**
- (3)：`A[lo]` 未被触碰（`left >= lo+1`、`right-1 >= left >= lo+1`）。**成立。**
- (4)：`left <= right-1 = right'`（由守卫 `left < right` 得 `left <= right-1`）；`right' <= hi`。**成立。**

### 5.12 退出与收尾

守卫 `left < right` 为假且不变式给 `left <= right`，故 **`left == right`**（讲义用 `//@assert left == right;` 记录）。

**此时要证：`swap(A, lo, left-1)` 后枢轴归位。**

- 由 (1)，`A[lo+1..left)` 全部 `<= pivot`，即 `A[lo+1..left-1]` 全部 `<= pivot`。
- 由 (2)，`A[left..hi)` 全部 `>= pivot`（因为 `right == left`）。
- 交换 `A[lo]` 与 `A[left-1]`：枢轴放到 `left-1`，原来的 `A[left-1]`（`<= pivot`）放到 `lo`。

交换后：

- `A[lo..left-1)` 全 `<= pivot` → 满足 `ge_seg(A[\result], A, lo, \result)`（`\result = left-1`）。
- `A[left..hi)` 全 `>= pivot` → 满足 `le_seg(A[\result], A, \result+1, hi)`。
- `lo <= left-1 < hi`：`left >= lo+1` 给 `left-1 >= lo`；`left == right <= hi` 给 `left-1 < hi`。

**为什么 `left-1` 而不是 `left`**：因为 `A[lo+1..left)` 是**左段**（全部 `<= pivot`），它占据下标 `lo+1` 到 `left-1`。枢轴应当紧接在它右边，即 `left` 位置？——**不对**。枢轴原本在 `A[lo]`，交换到 `A[left-1]` 后：左段变成 `A[lo..left-1)`（原来的 `A[lo+1..left-1]` 左移一格占 `A[lo..left-2)`，加上换进来的原 `A[left-1]` 在 `A[left-1]`……）。

**更清楚的看法**：交换前数组形态是

```
[ pivot ][ 全部 <= pivot ][ 全部 >= pivot ]
  lo      lo+1        left-1  left        hi
```

交换 `A[lo]` 与 `A[left-1]`：

```
[ <=pivot ][ 全部 <= pivot ][ pivot ][ 全部 >= pivot ]
  lo        lo+1        left-2  left-1  left      hi
```

枢轴落在 `left-1`，左段是 `A[lo..left-1)`，右段是 `A[left..hi)`。**完全正确**，返回 `left-1`。

### 5.13 契约的强弱：`\result` 与 `\result+1`

`partition` 的三条后置条件：

```c0
//@ensures lo <= \result && \result < hi;
//@ensures ge_seg(A[\result], A, lo, \result);      // 左边段 [lo, result)
//@ensures le_seg(A[\result], A, \result+1, hi);    // 右边段 [result+1, hi)
```

- 第一条：返回的是**合法下标**。
- 第二条：`A[lo..result)` 全部 `<= A[result]`。
- 第三条：`A[result+1..hi)` 全部 `>= A[result]`。

**注意第三段的起点是 `\result+1`**——跳过枢轴自己。若写成 `\result`，就变成「`A[result] >= A[result]`」，虽然真但丢了「跳过枢轴」的语义。

> **原文异常**：第 16 页完整代码的第 6 行写作 `//@ensures le_seg(A[\result], A, \result, hi);`，缺少 `+1`；而第 7 页与第 13 页的版本都写作 `\result+1`。**第 16 页是笔误**，正确形式是 `\result+1`。

### 5.14 稳定性

**定义**：若排序把「在排序键上相等」的不同元素之间的**相对次序保持不变**，则称该排序**稳定**。

**讲义的反例**：按讲次（lecture number）排序学生记录。原始数组里 `(2, church)` 在 `(2, lovelace)` 之前，排序后 `lovelace` 跑到了 `church` 前面——不稳定。

**为什么这在实践中重要**：电子表格「按某列排序」时，如果两次排序键相同，用户期望原来的次序被保留（否则之前按另一列排好的结果会被打乱）。**多关键字排序的经典做法是「先按次要键排，再按主要键排」，这只有在排序稳定时才对。**

**选择排序不稳定的证明**（习题 5）：数组 `A = [2a, 2b, 1]`（下标 `a`、`b` 区分两个 `2`）。

| 迭代 | i | `find_min` 返回 m | `A[m]` | 交换后 |
|---|---|---|---|---|
| 1 | 0 | 2 | `1` | `[1, 2b, 2a]` |
| 2 | 1 | 1 | `2b` | `[1, 2b, 2a]`（自交换） |
| 3 | 2 | 2 | `2a` | `[1, 2b, 2a]`（自交换） |

**两个 `2` 的相对次序从 `2a, 2b` 变成了 `2b, 2a`**——第 1 轮的交换把 `2a` 从位置 0 甩到了位置 2。**不稳定的根源**：选择排序的「远距离交换」会跨越其他元素。

**三种排序的三项性质对比**：

| 算法 | 原地 | 速度 | 稳定 |
|---|---|---|---|
| 选择排序 | 是 | 慢（`O(n²)` 恒为最坏） | 否 |
| 快速排序 | 是 | 通常快（`O(n log n)` 期望） | 否 |
| 归并排序 | **否** | 快（`O(n log n)` **最坏**） | **是** |

**三者不能兼得**——这是本讲的核心权衡结论。

### 5.15 归并排序

**思路**：对半切（`O(1)`），两半各自排序，再 `merge`。

```c0
void sort (int[] A, int lo, int hi)
//@requires 0 <= lo && lo <= hi && hi <= \length(A);
//@ensures is_sorted(A, lo, hi);
{
  if (hi-lo <= 1) return;
  int mid = lo + (hi-lo)/2;
  sort(A, lo, mid);  //@assert is_sorted(A, lo, mid);
  sort(A, mid, hi);  //@assert is_sorted(A, mid, hi);
  merge(A, lo, mid, hi);
  return;
}
```

**与快速排序的结构对比**：

```
快速排序：  partition → sort(左) → sort(右)
归并排序：  sort(左) → sort(右) → merge
```

**「划分/合并」的位置正好相反**。讲义说两者「very similar」，差别只在顺序。

**`merge` 的实现**：新建临时数组，两个指针从左到右扫两个有序段，每次取较小的那个放进临时数组。时间 `O(n)`，空间 `O(n)`。讲义说实现在 `sortlib.c0` 里。

**复杂度**：`O(log n)` 层 × 每层 `O(n)` 合并 = `O(n log n)`。**中点计算是确定性的，所以这是最坏情况界**——不像快速排序只有期望界。

## 6. 代码示例

### 6.1 官方课程代码

以下引自讲义 PDF `07-quicksort.pdf`，语言为 **C0**（不是标准 C/C++）。`//@` 注解、`\length`、`\result`、`alloc_array` 都是 C0 特有语法。

**（1）`sort` 的契约，第 5 页：**

```c0
void sort(int[] A, int lo, int hi)
//@requires 0 <= lo && lo <= hi && hi <= \length(A);
//@ensures is_sorted(A, lo, hi);
{
  ...
}
```

**（2）基本情况，第 6 页：**

```c0
void sort(int[] A, int lo, int hi)
//@requires 0 <= lo && lo <= hi && hi <= \length(A);
//@ensures is_sorted(A, lo, hi);
{
  if (hi-lo <= 1) return;
  ...
}
```

**（3）`partition` 的契约，第 7 页：**

```c0
int partition(int[] A, int lo, int pi, int hi)
//@requires 0 <= lo && lo <= pi;
//@requires pi < hi && hi <= \length(A);
//@ensures lo <= \result && \result < hi;
//@ensures ge_seg(A[\result], A, lo, \result);
//@ensures le_seg(A[\result], A, \result+1, hi);
;
```

**（4）`sort` 完整实现，第 8 页：**

```c0
void sort(int[] A, int lo, int hi)
//@requires 0 <= lo && lo <= hi && hi <= \length(A);
//@ensures is_sorted(A, lo, hi);
{
  if (hi-lo <= 1) return;
  int pi = lo + (hi-lo)/2; /* should be random */
  int mid = partition(A, lo, pi, hi);
  sort(A, lo, mid);
  sort(A, mid+1, hi);
  return;
}
```

**（5）`partition` 的完整实现，第 16 页：**

```c0
int partition(int[] A, int lo, int pi, int hi)
//@requires 0 <= lo && lo <= pi;
//@requires pi < hi && hi <= \length(A);
//@ensures lo <= \result && \result < hi;
//@ensures ge_seg(A[\result], A, lo, \result);
//@ensures le_seg(A[\result], A, \result+1, hi);
{
  // Hold the pivot element off to the left at "lo"
  int pivot = A[pi];
  swap(A, lo, pi);

  int left = lo+1;
  int right = hi;

  while (left < right)
  //@loop_invariant lo+1 <= left && left <= right && right <= hi;
  //@loop_invariant ge_seg(pivot, A, lo+1, left); // Not lo!
  //@loop_invariant le_seg(pivot, A, right, hi);
  {
    if (A[left] <= pivot) {
      left++;
    } else {
      //@assert A[left] > pivot;
      swap(A, left, right-1);
      right--;
    }
  }
  //@assert left == right;

  swap(A, lo, left-1);
  return left-1;
}
```

**（6）`ge_seg` 与 `le_seg` 的语义，第 7 页：**

- `ge_seg(x, A, lo, mid)`：`x >= y` 对 `A[lo..mid)` 中每个 `y`。
- `le_seg(x, A, mid+1, hi)`：`x <= y` 对 `A[mid+1..hi)` 中每个 `y`。

两者定义在 `arrayutil.c0` 里。

**（7）归并排序骨架，第 18 页：**

```c0
void sort (int[] A, int lo, int hi)
//@requires 0 <= lo && lo <= hi && hi <= \length(A);
//@ensures is_sorted(A, lo, hi);
{
  if (hi-lo <= 1) return;
  int mid = lo + (hi-lo)/2;
  sort(A, lo, mid); //@assert is_sorted(A, lo, mid);
  sort(A, mid, hi); //@assert is_sorted(A, mid, hi);
  merge(A, lo, mid, hi);
  return;
}
```

`merge` 的实现在 `sortlib.c0`。

**（8）习题 4 答案：用临时数组的 `partition`，第 28 页：**

```c0
int partition(int[] A, int lo, int hi)
//@requires 0 <= lo && lo < hi && hi <= \length(A);
//@ensures lo <= \result && \result < hi;
//@ensures ge_seg(A[\result], A, lo, \result);
//@ensures le_seg(A[\result], A, \result+1, hi);
{
  int pi = lo + (hi - lo)/2;   // pivot index
  swap(A, lo, pi);             // move pivot to index 0
  int pivot = A[lo];           // pivot

  int[] TMP = alloc_array(int, hi-lo);
  int left = 0;
  int right = hi-lo;

  for (int i = lo+1; i < hi; i++)
  //@loop_invariant lo <= i && i <= hi;
  //@loop_invariant left + (hi - lo - right) == i - (lo+1);
  //@loop_invariant ge_seg(pivot, TMP, 0, left);
  //@loop_invariant lt_seg(pivot, TMP, right, hi-lo);
  {
    if (A[i] <= pivot) {
      TMP[left] = A[i];
      left++;
    }
    else {
      right--;
      TMP[right] = A[i];
    }
  }
  //@assert left == right - 1;
  TMP[left] = pivot;
  //@assert ge_seg(TMP[left], TMP, 0, left);
  //@assert lt_seg(TMP[left], TMP, right, hi-lo);

  for (int i = 0; i < hi-lo; i++)
  //@loop_invariant 0 <= i && i <= hi - lo;
  //@loop_invariant eq_segs(TMP, 0, i, A, lo, lo+i);
  {
    A[lo+i] = TMP[i];
  }

  return lo+left;  // pivot position in A
}
```

**第二条不变式 `left + (hi - lo - right) == i - (lo+1)`** 是「已处理元素数 = 左段长度 + 右段长度」的记账式：`left` 是左段长度，`hi-lo-right` 是右段长度，右边是已扫描的元素数。**这种「守恒式」不变式在多指针算法里很常见。**

**（9）`is_permutation` 及相关辅助函数（习题 1 答案），第 23–24 页：**

```c0
int[] seg_copy(int[] A, int lo, int hi)
//@requires 0 <= lo && lo <= hi && hi <= \length (A);
{
  int n = hi - lo;
  int[] C = alloc_array(int, n);
  for (int i = 0; i < n; i++)
  //@loop_invariant 0 <= i && i <= n;
  //@loop_invariant lo <= i+lo && i+lo <= hi;
  {
    C[i] = A[lo+i];
  }
  return C;
}

bool array_equal(int[] A, int[] B, int n)
//@requires 0 <= n && n <= \length(A) && n <= \length(B);
{
  for (int i = 0; i < n; i++)
  //@loop_invariant 0 <= i && i <= n;
  {
    if (A[i] != B[i])
      return false;
  }
  return true;
}

bool is_permutation(int[] A, int lo1, int hi1, int[] B, int lo2, int hi2)
//@requires 0 <= lo1 && lo1 <= hi1 && hi1 <= \length (A);
//@requires 0 <= lo2 && lo2 <= hi2 && hi2 <= \length (B);
{
  if (hi1 - lo1 != hi2 - lo2)
    // different lengths
    return false;
  int[] A_copy = seg_copy(A, lo1, hi1);
  int[] B_copy = seg_copy(B, lo2, hi2);
  int n = hi1 - lo1;
  //@assert n == hi2 - lo2;
  selsort(A_copy, 0, n);
  selsort(B_copy, 0, n);
  return array_equal(A_copy, B_copy, n);
}
```

**「是排列」的判定思路**：排序两个副本，逐位比较。**为什么不能在契约里用**：`is_permutation` 会 `alloc_array` 分配内存，**不纯（impure）**。讲义明确说明：契约必须纯，否则带 `-d` 与不带 `-d` 运行结果可能不同。因此只能在普通 `assert` 里调用（注意：`assert(...)` 是运行期函数调用，`//@assert ...;` 是契约）。

**官方代码包**：`90-原始PDF/15-122/code/07-quicksort.tgz`（原始 URL：`https://cs.cmu.edu/~15122/handouts/code/07-quicksort.tgz`），含 `sortlib.c0`（`merge` 等）、`arrayutil.c0`（`ge_seg`/`le_seg`/`eq_segs` 等规格函数）。

### 6.2 Agent 自行编写的教学示例

> **非官方，仅用于说明概念。** 以下由本笔记自行编写，不是 CMU 官方代码，语言为 **C0**。

**示例 A：手工执行一次完整的 `partition`。**

`A = [7, 3, 9, 1, 8, 2, 6]`，`lo = 0`、`hi = 7`、`pi = 3`（`A[3] = 1`）。

第 1 步：`pivot = A[3] = 1`，`swap(A, 0, 3)` → `A = [1, 3, 9, 7, 8, 2, 6]`。`left = 1`、`right = 7`。

| 迭代 | left | right | A[left] | 与 pivot=1 比较 | 动作 | 数组 |
|---|---|---|---|---|---|---|
| 1 | 1 | 7 | 3 | `3 > 1` | `swap(A,1,6)`，`right=6` | `[1, 6, 9, 7, 8, 2, 3]` |
| 2 | 1 | 6 | 6 | `6 > 1` | `swap(A,1,5)`，`right=5` | `[1, 2, 9, 7, 8, 6, 3]` |
| 3 | 1 | 5 | 2 | `2 > 1` | `swap(A,1,4)`，`right=4` | `[1, 8, 9, 7, 2, 6, 3]` |
| 4 | 1 | 4 | 8 | `8 > 1` | `swap(A,1,3)`，`right=3` | `[1, 7, 9, 8, 2, 6, 3]` |
| 5 | 1 | 3 | 7 | `7 > 1` | `swap(A,1,2)`，`right=2` | `[1, 9, 7, 8, 2, 6, 3]` |
| 6 | 1 | 2 | 9 | `9 > 1` | `swap(A,1,1)`，`right=1` | `[1, 9, 7, 8, 2, 6, 3]` |

`left == right == 1`，退出。`swap(A, 0, 0)`（自交换），返回 `left-1 = 0`。

**结果**：`A = [1, 9, 7, 8, 2, 6, 3]`，枢轴 `1` 在下标 0，右段 `A[1..7)` 全部 `>= 1`。左段为空。

**这就是最坏情况的一个实例**：枢轴恰好是最小值，划分退化成 `0 | 1 | n-1`。下一次递归处理 6 个元素，再下一次 5 个……总共 `n-1` 层。**这演示了为什么「取中间下标」也可能退化**——中间下标的**值**未必是中间值。

**示例 B：为什么「取中间元素」不是万灵药（对应习题 3）。**

讲义给的七元素最坏情况数组是 `[1, 3, 5, 7, 6, 4, 2]`。取中间下标 `pi = 0 + 7/2 = 3`，`A[3] = 7`——**恰好是最大值**。划分后得到 `[1,3,5,6,4,2]` 与空段。递归下去：

| 步骤 | 枢轴 | 剩余待排 |
|---|---|---|
| 1 | 7 | `[1,3,5,6,4,2]` |
| 2 | 6 | `[1,3,5,4,2]` |
| 3 | 5 | `[1,3,4,2]` |
| 4 | 4 | `[1,3,2]` |
| 5 | 3 | `[1,2]` |
| 6 | 2 | `[1]` |

**每一步都有一个空段**，完全退化。构造原理：让数组形如「递增到中间、再递减」，这样每次的中点都落在当前段的最大值上。

**示例 C：稳定性反例的最小化版本。**

数组 `A = [1a, 1b]`（两个相等的 `1`，下标区分身份），用选择排序：

| 迭代 | i | `find_min` 返回 | 交换 |
|---|---|---|---|
| 1 | 0 | 0（`A[0] = 1a` 已是最小） | `swap(A,0,0)` 自交换 |
| 2 | 1 | 1 | `swap(A,1,1)` 自交换 |

**这个例子恰好稳定**——因为数组已有序，选择排序只做自交换。

**要构造不稳定必须让最小值在远处**。最小例子需要三个元素：`[2a, 2b, 1]`（讲义习题 5 的版本）。第 1 轮把 `1` 换到位置 0，`2a` 被甩到位置 2，跨过了 `2b`。**「远距离交换跨越等价元素」是不稳定的充要机制。**

**示例 D：用递推式验证「4 倍输入 → 16 倍时间」（对应习题 6）。**

| 复杂度 | `T(n) = k` 时 `T(4n)` | 比值 |
|---|---|---|
| `O(n²)` | `c(4n)² = 16cn² = 16k` | **16** |
| `O(n log n)` | `c(4n)log(4n) = 4cn(log n + 2) = 4k + 8cn` | **4 到 8** |

讲义的两张实测表（输入规模每次 ×4）：

**表一（随机数组）**：

| 元素数 | #1 (s) | #2 (s) |
|---|---|---|
| `2^12` | 0.09 | 0.08 |
| `2^14` | 0.41 | 0.43 |
| `2^16` | 1.91 | 1.95 |
| `2^18` | 8.75 | 9.11 |
| `2^20` | 37.55 | 38.20 |

**表二（有序数组）**：

| 元素数 | #1 (s) | #2 (s) |
|---|---|---|
| `2^12` | 0.08 | 0.42 |
| `2^14` | 0.35 | 3.32 |
| `2^16` | 1.73 | 27.48 |
| `2^18` | 7.39 | 214.39 |
| `2^20` | 33.36 | 1726.54 |

**判读**：

- 表一两列几乎相同 → 两实现在随机输入上复杂度一致 → 只有随机枢轴才可能如此（固定策略在两实现间会有差异）。
- 表一每列比值约 4 → `O(n log n)`。
- 表二左列（#1）与表一几乎相同 → 输入有序不影响 #1 → **#1 是随机枢轴**。
- 表二右列（#2）比值约 8（`3.32/0.42 ≈ 7.9`、`27.48/3.32 ≈ 8.3`、`214.39/27.48 ≈ 7.8`、`1726.54/214.39 ≈ 8.1`）→ 明显劣于 4，指向 `O(n²)` → **#2 是固定取首元素**。
- 比值是 8 而非 16：讲义解释为「大 O 忽略低次项」，实际是 `cn² + dn log n` 这种混合形式在小规模下尚未完全被平方项支配。**这正是「渐近」的含义——常数项与低次项在有限规模上仍有余温。**

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键区别 | 记忆点 |
|---|---|---|---|
| 快速排序 | 归并排序 | 前者「划分贵、合成立刻」；后者「划分免费、合并贵」 | 快排先分后递归，归并先递归后合 |
| 快速排序最坏 `O(n²)` | 归并排序最坏 `O(n log n)` | 前者只有**期望**界；后者最坏就是 `O(n log n)` | 快排赌运气，归并保底 |
| 随机枢轴 | 取中间元素 | 前者期望与输入无关；后者有对抗性输入 | 中间下标的值未必是中间值 |
| `ge_seg(pivot, A, lo+1, left)` | `ge_seg(pivot, A, lo, left)` | 后者把暂存的枢轴 `A[lo]` 也纳入，一旦交换就断 | 代码注释写着 `// Not lo!` |
| `le_seg(..., \result+1, hi)` | `le_seg(..., \result, hi)` | 前者跳过枢轴自己；后者退化成 `pivot >= pivot` | 后置条件要 `+1` |
| `in-place`（原地） | 「不用递归栈」 | 原地只约束**分配**的空间，递归栈不算 | 快排原地但有 `O(log n)` 栈 |
| `//@assert P;`（契约） | `assert(f(...))`（函数调用） | 前者要求**纯**；后者是普通运行期调用 | 分配内存的检查只能放后者 |
| 稳定排序 | 原地排序 | 前者保等价元素次序；后者省空间；**二者常冲突** | 归并稳定不原地，快排原地不稳定 |
| 平均情况分析 | 随机化算法的期望 | 前者假设输入分布；后者对算法随机性取期望 | 后者与输入无关，更强 |
| `hi - lo <= 1` 基本情况 | `lo < hi` 循环守卫 | 递归用前者（0 或 1 个元素即有序）；循环用后者 | 递归与循环的边界约定不同 |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-122/lectures/07-quicksort.pdf`
- **讲义标题**：PDF 内页标题为 **"Lecture 7: Quicksort"**，作者 Frank Pfenning。
- **总页数**：31 页
- **本节重点页码**（PDF 页码，即提取文本中 `=== [page N] ===` 的 N）：
  - 第 1 页：开篇；分治的划分/征服/合并三步；快排原地、归并非原地；递归作为核心技术；补充资源链接
  - 第 2 页：分治的理想划分（对半）；`3^k` 与 `log2 n`/`log3 n` 只差常数
  - 第 2–3 页：快速排序三步；划分是线性的；`3, 1, 4, 4, 7, 2, 8` 取 `3` 为枢轴的例子
  - 第 3 页：最好情况 `O(n log n)`；最坏情况的递归调用表
  - 第 4 页：`c * Σ k = cn(n-1)/2 ∈ O(n²)`；中位数的 `O(n)` 算法；随机化的价值
  - 第 5 页：`sort` 的契约；递归用契约推理的两条规则；what 与 how 分离
  - 第 5–6 页：终止性讨论（此处有笔误，见下）
  - 第 6 页：`if (hi-lo <= 1) return;`
  - 第 7 页：`partition` 的契约；`ge_seg`/`le_seg` 的定义；`lo < hi` 的必要性
  - 第 8 页：`sort` 完整代码；终止性的正确论证（用 `partition` 后置）
  - 第 9 页：为什么不用临时数组（非原地）；枢轴位置未知；交换到段首
  - 第 10–11 页：逐步执行划分；`left`/`right` 两个指针
  - 第 11 页：读出三条不变式 `(1)(2)(3)`
  - 第 12 页：`(4) lo+1 <= left <= right <= hi`；`left == right`；`swap(A, lo, left-1)`
  - 第 13 页：`pivot = A[pi]; swap(A, lo, pi);`
  - 第 14 页：`left = lo+1`、`right = hi`；INIT 靠空段与 `lo < hi`
  - 第 15 页：循环体（`left++` 与 `swap(A,left,right-1)`）
  - 第 16 页：`partition` 完整代码（第 6 行 `le_seg` 缺 `+1`，笔误）
  - 第 16–17 页：稳定性；`(2, church)` / `(2, lovelace)` 的例子；三种排序的三项性质
  - 第 17–19 页：归并排序；`merge` 是 `O(n)` 时间 + `O(n)` 空间；`O(n log n)` 最坏界
  - 第 20–21 页：习题 1–6（含习题 6 的两张计时表）
  - 第 22–25 页：习题 1 答案（`seg_copy`、`array_equal`、`is_permutation`、纯性讨论）
  - 第 25–26 页：习题 2 答案（用 `partition` 后置证 `sort` 后置）
  - 第 26 页：习题 3 答案（`[1, 3, 5, 7, 6, 4, 2]`）
  - 第 26–29 页：习题 4 答案（临时数组版 `partition`）
  - 第 29 页：习题 5 答案（`[2a, 2b, 1]`）
  - 第 29–31 页：习题 6 答案（比值分析：`O(n²)` 期望 16 倍，`O(n log n)` 期望 4–8 倍）
- **原始网页链接**：`https://www.cs.cmu.edu/~15122-archive/f26/handouts/lectures/07-quicksort.pdf`
- **配套代码包**：`https://cs.cmu.edu/~15122/handouts/code/07-quicksort.tgz`
- **复习幻灯片**：`https://cs.cmu.edu/~15122/handouts/slides/review/07-quicksort.pdf`（本库未收录其提取文本，页码待人工核对）

> **原文异常**（共 5 处，均已在正文标注）：
> 1. **第 5–6 页**：「`hi − lo` is divided by two for each recursive call」——这是**归并排序**的性质，对快速排序不成立（划分点由枢轴决定，可能只缩小 1）。第 8 页的正确论证用的是 `partition` 的后置条件。
> 2. **第 16 页**：完整代码第 6 行 `//@ensures le_seg(A[\result], A, \result, hi);` 缺 `+1`；第 7 页与第 13 页均为 `\result+1`。
> 3. **第 3 页**：最坏情况表第 4 行写作 `1, 2, 3, [4, 4, 8, 8]`，按上下文应为 `[4, 4, 8, 7]`（下一行才出现 `7`）。另表首行 `[3, 1, 4, 4, 8, 2, 7]` 与第 2 页的例子 `3, 1, 4, 4, 7, 2, 8` 元素顺序不同。
> 4. **第 20 页**：习题 4 给出的 `partition` 原型 `int partition(int[] A, int lo, int hi)` 缺少 `pi` 参数，且与该页三条后置条件的 `\result` 用法不完全自洽；第 28 页的答案代码同样用三参数签名（内部自算 `pi`），与第 7 页的四参数版本不同——**习题 4 是有意设计成另一种接口**，不是笔误，但容易与主版本混淆。
> 5. **第 26 页**：习题 2 答案的 `sort` 代码用 `partition(A, lo, hi)`（三参数）与 `sort(A, lo, p)` / `sort(A, p+1, hi)`，与第 8 页的四参数版本不一致——同样是简化版接口。另第 26 页 `Case 2` 的论证里 `A` 与 `B` 两个符号（"by line 15 and A"、"by line 16 and B"）未在正文定义，疑为提取时丢失了归纳假设的标签。

## 9. 对应视频

未找到官方公开录像。建议的动手顺序：(1) 在 `coin` 里对 `[7,3,9,1,8,2,6]` 逐步执行 `partition`，打印每轮的 `left`、`right`、数组，对照 6.2 示例 A 的表；(2) 用 `[1,3,5,7,6,4,2]` 跑 `sort`，统计递归深度，验证 `O(n²)`；(3) 把 `pi` 改成 `lo`（固定取首元素），对已排序数组计时，复现习题 6 表二右列的现象；(4) 在 `coin -d` 下故意把 `ge_seg(pivot, A, lo+1, left)` 改成 `ge_seg(pivot, A, lo, left)`，观察哪一步断言失败。

## 10. 本节复习

1. 分治三步：divide（划分）、conquer（递归）、combine（合并）。快排的 combine 是空的。
2. 快排划分 `O(k)`、合并 `O(1)`；归并划分 `O(1)`、合并 `O(k)` 时间 + `O(k)` 空间。
3. 最好情况 `T(n) = 2T(n/2) + cn = O(n log n)`；最坏 `c*n(n-1)/2 = O(n²)`。
4. 最坏时规模 `n` 有 `n-1` 次有意义的递归调用。
5. 固定枢轴策略必有克星输入（取首元素 + 已排序 = `O(n²)`）；随机枢轴的**期望**与输入分布无关。
6. 递归函数用**契约**推理：查前置、假设后置，**不展开递归**。
7. 终止性：`mid - lo < hi - lo`（由 `mid < hi`）与 `hi - (mid+1) < hi - lo`（由 `lo <= mid`）。
8. `partition` 三条不变式：`lo+1 <= left <= right <= hi`、`ge_seg(pivot, A, lo+1, left)`、`le_seg(pivot, A, right, hi)`；**注意 `lo+1` 不是 `lo`**。
9. INIT 靠空段 + 空真 + 前置 `lo < hi`；退出时 `left == right`，`swap(A, lo, left-1)`，返回 `left-1`。
10. 契约必须**纯**：`is_permutation` 会分配内存，只能放 `assert(...)` 不能放 `//@assert`。
11. 三项性质不可兼得：选择排序（原地/慢/不稳定）、快排（原地/期望快/不稳定）、归并（非原地/最坏 `O(n log n)`/稳定）。
12. 计时判据：输入 ×4 时，`O(n²)` 约 ×16，`O(n log n)` 约 ×4–8。

## 11. 自我检查

**题 1.** 对 `A = [5, 2, 8, 2, 9, 1, 4]`、`lo = 0`、`hi = 7`、`pi = 3`，手工执行 `partition`，写出每轮后的 `left`、`right` 与数组，最后给出返回值和划分结果。

**题 2.** 为什么 `partition` 的不变式写 `ge_seg(pivot, A, lo+1, left)` 而不是 `ge_seg(pivot, A, lo, left)`？如果把 `left` 初始化为 `lo` 会发生什么？

**题 3.** 证明 `partition` 终止：说明为什么 `left < right` 时每次循环体执行都让 `right - left` 严格减小。

**题 4.** 设 `T(n) = T(n-1) + cn`（快速排序最坏情况的递推），解出 `T(n)` 并给出大 O 界。

**题 5.** 一个数组 `A = [(1,a), (1,b), (0,c)]`（按第一个分量排序，第二个分量是身份标记）。用选择排序排完后两个 `1` 的相对次序是什么？这说明选择排序具有什么性质？

<details>
<summary>参考答案</summary>

**答 1.** `pivot = A[3] = 2`，`swap(A, 0, 3)` → `A = [2, 2, 8, 5, 9, 1, 4]`。`left = 1`、`right = 7`。

| 迭代 | left | right | A[left] | 比较 | 动作 | 数组 |
|---|---|---|---|---|---|---|
| 1 | 1 | 7 | 2 | `2 <= 2` | `left = 2` | `[2, 2, 8, 5, 9, 1, 4]` |
| 2 | 2 | 7 | 8 | `8 > 2` | `swap(A,2,6)`，`right=6` | `[2, 2, 4, 5, 9, 1, 8]` |
| 3 | 2 | 6 | 4 | `4 > 2` | `swap(A,2,5)`，`right=5` | `[2, 2, 1, 5, 9, 4, 8]` |
| 4 | 2 | 5 | 1 | `1 <= 2` | `left = 3` | `[2, 2, 1, 5, 9, 4, 8]` |
| 5 | 3 | 5 | 5 | `5 > 2` | `swap(A,3,4)`，`right=4` | `[2, 2, 1, 9, 5, 4, 8]` |
| 6 | 3 | 4 | 9 | `9 > 2` | `swap(A,3,3)`，`right=3` | `[2, 2, 1, 9, 5, 4, 8]` |

`left == right == 3`，退出。`swap(A, 0, 2)` → `A = [1, 2, 2, 9, 5, 4, 8]`，**返回 2**。

**验证**：`A[0..2) = [1, 2]` 全部 `<= 2`；`A[3..7) = [9, 5, 4, 8]` 全部 `>= 2`；`A[2] = 2`。
**注意**：原数组里有**两个 2**，返回值 2 既不是传入的 `pi = 3`，也不是第一个 `2` 的位置。这正印证讲义脚注说的「返回下标可能不同于传入的枢轴下标」。

**答 2.** `A[lo]` 存放的是**暂存的枢轴**（`swap(A, lo, pi)` 的结果），它是「工作区之外」的元素。不变式的语义是「**已经处理过的**、确定在左侧的元素」，这个集合从 `lo+1` 开始。

若写成 `ge_seg(pivot, A, lo, left)`，含义变成「`A[lo..left)` 全部 `<= pivot`」，其中包含 `A[lo] = pivot` 本身（`pivot <= pivot` 平凡成立）。**在 INIT 时也成立**（`left = lo+1`，段是 `A[lo..lo+1) = {pivot}`）。**但保持性会断**：当 `A[left] > pivot` 时执行 `swap(A, left, right-1)`，如果某次 `left == lo`，枢轴就会被换走，`A[lo] = pivot` 不再成立，最后 `swap(A, lo, left-1)` 就把错的东西当枢轴了。

若把 `left` 初始化为 `lo`：第一次迭代会读 `A[lo]`——那是枢轴自己，`pivot <= pivot` 成立，于是 `left++` 到 `lo+1`。**看起来无害，但语义上多了一次无意义的迭代，且 `lo+1 <= left` 这条范围不变式在 INIT 时就失败了。** 更重要的是它给了「`left` 可能等于 `lo`」这个危险状态的存在许可。**代码注释 `// Not lo!` 就是提醒这一点。**

**答 3.** 设 `d = right - left > 0`（守卫）。

- 情形 `A[left] <= pivot`：`left' = left + 1`、`right' = right`，故 `d' = right - left - 1 = d - 1`。**严格减小。**
- 情形 `A[left] > pivot`：`left' = left`、`right' = right - 1`，故 `d' = right - 1 - left = d - 1`。**严格减小。**

**两种情形都恰好减 1**，没有第三种可能（`<=` 与 `>` 穷尽）。`d` 是非负整数且每轮严格减 1，故至多 `d` 轮后 `d = 0`，守卫失败，循环退出。**这是「用一个严格递减的自然数变量证终止」的教科书例子**，与 [[15-122-06-Binary-Search]] 里「区间长度递减」同构，区别在于这里每轮**恰好**减 1（二分查找是减半）。

**答 4.** 展开：

```
T(n) = T(n-1) + cn
     = T(n-2) + c(n-1) + cn
     = T(n-3) + c(n-2) + c(n-1) + cn
     = ...
     = T(0) + c*(1 + 2 + ... + n)
     = T(0) + c*n(n+1)/2
```

取 `T(0) = O(1)`，得 `T(n) = O(n²)`。

**注意求和的上界**：讲义写的是 `c * Σ_{k=0}^{n-1} k = c*n(n-1)/2`（因为规模 `n` 只有 `n-1` 次**有意义的**递归调用，其余是空段调用，代价 `O(1)`）。两种写法的差别只在 `n` 的一次项，大 O 意义下相同——**都是 `O(n²)`**。这个细节说明「精确计数」与「渐近阶」是两件事：前者要数清楚边界，后者只关心最高次幂。

**答 5.** `A = [(1,a), (1,b), (0,c)]`，按第一个分量排序。

| 迭代 | i | `find_min` 返回 m | `A[m]` 的第一分量 | 交换后 |
|---|---|---|---|---|
| 1 | 0 | 2 | `0` | `[(0,c), (1,b), (1,a)]` |
| 2 | 1 | 1 | `1`（`(1,b)`） | 自交换，不变 |
| 3 | 2 | 2 | `1`（`(1,a)`） | 自交换，不变 |

**结果**：`[(0,c), (1,b), (1,a)]`。原来 `(1,a)` 在 `(1,b)` 之前，现在 `(1,b)` 在 `(1,a)` 之前——**相对次序颠倒了**。

**结论**：选择排序**不稳定**。机制是第 1 轮的**远距离交换**：把 `(0,c)` 从下标 2 换到下标 0，同时把 `(1,a)` 从下标 0 甩到下标 2，**跨越了 `(1,b)`**。这是「不稳定」的典型成因——**任何做远距离交换的排序都可能不稳定**，而只做相邻交换的排序（如插入排序、冒泡排序）天然稳定。

</details>

## 12. 进一步学习

- 上一讲：[[15-122-06-Binary-Search]] —— 分治的第一次出现（只征服一个子问题）；本讲推广到「征服两个子问题」。
- 上一讲（排序系列）：[[15-122-05-Big-O]] —— `O(n²)`、`n(n-1)/2` 求和、选择排序的三条不变式；本讲的 `partition` 不变式与之同构。
- 下一讲：[[15-122-08-Libraries]] —— 把 `sort`、`merge`、`ge_seg` 这些函数组织成可复用的库；模块与接口的分离。
- 后续讲次：[[15-122-11-Unbounded-Arrays]] —— 摊还分析（amortized analysis），另一种「平均」视角；[[15-122-12-Hashing]] —— 用哈希达到 `O(1)` 平均查找。
- 课程入口：[[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]]、[[10-CMU-15-122/01-课程目录|CMU 15-122 - 课程目录]]。
- 术语查询：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Quicksort、Pivot、Partition、Divide and Conquer、In-Place、Stable Sort、Randomized Algorithm、Purity 等条目）。
- 延伸阅读：Jon Bentley & M. Douglas McIlroy 的 "Engineering a Sort Function"（1993）——工业级 `qsort` 的枢轴选择与退化防护；Joshua Bloch 关于 Java `Arrays.sort` 的笔记。
