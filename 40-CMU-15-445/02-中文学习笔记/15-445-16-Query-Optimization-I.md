---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: L16
topic: Query Planning & Optimization I
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 数据库
  - 查询优化
  - 等价变换
  - 启发式优化
  - System R
---

# 15-445 L16：查询规划与优化 I（Query Planning & Optimization I）

> 同一条 SQL 可以写出无数种执行计划，代价可能相差几个数量级。这一讲回答两件事：**哪些计划在逻辑上等价**（变换规则），以及**用什么策略在等价计划里挑一个**（启发式 vs 基于代价）。它是整个课程里「最像编译器」的一讲。

## 1. 本节学习目标

学完本讲，你应该能够：

1. 画出从 SQL 文本到物理计划的**五级流水线**（Parser → AST → Binder → Logical Plan → Optimizer → Physical Plan），并说明每一级做什么、需要什么元数据。
2. 用讲义给出的 `Emp ⋈ Dept` 例子说明**为什么优化重要**：不同计划的 I/O 次数可以相差三个数量级。
3. 写出至少 6 条**等价变换规则**（谓词拆分、谓词下推、连接交换、连接结合、笛卡尔积转连接、投影下推），并判断某条变换是否**总是**等价。
4. 区分**启发式/基于规则（heuristic / rule-based）**与**基于代价（cost-based）**两类搜索策略，说出各自的优缺点。
5. 说明基于代价优化器的四种**终止条件**（墙钟时间、代价阈值、枚举穷尽、变换次数上限）。
6. 描述 **System R** 的自底向上优化三步法，以及它为什么要同时保留「有序 / 无序」两套最优计划。
7. 解释 **top-down（Volcano / Cascades）** 的 branch-and-bound 剪枝，以及 **enforcer** 如何强制子计划输出某种物理属性（如排序）。

## 2. 前置知识

- **关系代数**：σ/π/⋈/× 的语义与等价性，见 [[15-445-01-Relational-Model-and-Algebra]]。
- **查询执行**：算子、流水线、访问路径，见 [[15-445-14-Query-Execution-I]]。
- **并行执行**：exchange 算子与并行计划形态，见 [[15-445-15-Query-Execution-II]]。
- **连接算法与代价直觉**：嵌套循环 / 排序归并 / 哈希连接的 I/O 量级，见 [[15-445-13-Joins-Algorithms]]。
- **索引与统计信息**：B+ 树索引、聚簇与否对代价的影响，见 [[15-445-08-Indexes-and-Filters-I]]。
- **C++ 提醒**：本课程项目用 **C++17** 编写、遵循 **Google C++ Style** 并用 clang-format 格式化；优化器代码涉及大量 `std::shared_ptr` 表达式树节点与 `std::unordered_map`，建议先熟悉智能指针所有权语义与 `const` 成员函数。

## 3. 核心概念

### 3.1 Query Planning Pipeline（查询规划流水线）

`Application → SQL Query → Parser → Abstract Syntax Tree → Binder → Logical Plan → Optimizer → Physical Plan`。Parser 只做语法分析；Binder 把名字解析成内部 ID 并查 **system catalog** 拿到 schema；Optimizer 用 schema、统计信息与代价模型把逻辑计划翻成物理计划。

### 3.2 Logical Plan vs Physical Plan（逻辑计划 vs 物理计划）

**逻辑计划**只描述「做什么」：`⋈`、`σ`、`π`，不含算法。**物理计划**描述「怎么做」：`HASH_JOIN`、`INDEX_SCAN`、`SORT`，每个算子有具体实现与代价。

### 3.3 Equivalence Rule（等价变换规则）

把逻辑计划 A 改写成逻辑上等价的 B（对任何数据库实例结果相同）。例如 `σ_{p1∧p2}(R) ≡ σ_{p1}(σ_{p2}(R))`、`R ⋈ S ≡ S ⋈ R`。

### 3.4 Predicate Pushdown（谓词下推）

把过滤尽量推到**靠近叶子**的位置，先减小中间结果再连接。代价上的意义是**乘性收益**：连接代价与输入大小成正比，早过滤一行可能省掉后续多次比较。

### 3.5 Search Algorithm（搜索算法）

在等价计划空间里找代价最低者的策略。两大流派：**启发式/规则（heuristics / rules）**——不看数据，按固定规则改写；**基于代价（cost-based）**——枚举候选并估算代价。

### 3.6 Cost Model（代价模型）

把计划映射成一个可比较的数值（CPU cycles、I/O 次数、内存、网络字节）。代价模型需要**统计信息**（表行数、不同值个数、直方图）才能估计中间结果大小。

### 3.7 Access Path（访问路径）

单个表的读取方式：顺序扫描、索引扫描、索引-only 扫描。代价取决于选择率、索引结构（B+ 树 vs 哈希）、是否需要排序、是否覆盖索引、是否有区图/压缩。

### 3.8 Sargable Predicate（可走索引的谓词）

**Sargable = Search ARGument Able**，指谓词能转成索引查找条件（如 `val >= 123 AND val <= 456` 可用 B+ 树范围查找）。`WHERE f(x) = 3` 这类对列施加函数的谓词通常**不 sargable**，除非有表达式索引。

### 3.9 Bottom-Up / Forward Chaining（自底向上）

从叶子表出发，先枚举单表访问路径，再逐步组合成更大的子计划，用**动态规划**保留每个子集的最优计划。代表：**System R**、Starburst。

### 3.10 Top-Down / Backward Chaining（自顶向下）

从根节点（目标）出发，把目标拆成子目标，遇到不满足的物理属性就插入 enforcer 或换算法，用 **branch-and-bound** 剪枝。代表：**Volcano**、**Cascades**（SQL Server 的优化器即 Cascade 风格）。

### 3.11 Enforcer（强制算子）

当子计划无法自然提供父节点要求的物理属性（如「按 `ARTIST.ID` 有序」）时，插入一个算子强制满足，例如 `SORT`，或者把扫描换成 `INDEX_SCAN(ARTIST.ID)`（天然有序）。

### 3.12 Heuristic Optimization（启发式优化）

用固定规则改写计划，不查数据、不算代价。优点是实现简单、可预测、调试容易；缺点是依赖**魔法常数（magic constants）**，且当算子之间相互影响时几乎不可能得到好计划。

## 4. 通俗理解

把优化器想成**导航软件**。

你告诉它「从 A 到 B」（SQL），它内部先算出**所有可能的路线拓扑**（逻辑计划），再根据**实时路况**（统计信息）估算每条路线的耗时（代价模型），最后选一条（物理计划）。

- **等价变换** = 「先上高速再走辅路」和「先走辅路再上高速」在拓扑上是同一条路的不同写法，你可以自由改写而不改变起点终点。
- **启发式优化** = 「永远优先走高速」这种固定规则：不用查路况，反应快，但遇到高速大堵车就傻了。
- **基于代价的优化** = 真的去查实时路况，算出每条路的预计时间。准，但要花时间查（优化时间本身也是成本）。
- **终止条件** = 导航不能算十分钟才给结果，所以「算够 100 毫秒就停」「找到一条 30 分钟以内的就够了」。

**System R 的三步法**像「先给每段路单独选最优走法，再用动态规划拼全程」：先给三张表各选最佳访问路径，再枚举所有连接顺序，每步只保留当前最便宜的方案。

**Top-down 的 branch-and-bound** 像「先估一个总时间上限，任何分支一旦预计超过它就立刻放弃」——这就是剪枝。

## 5. 原理与推导

### 5.1 为什么优化重要：一个具体例子

讲义给的例子：`Emp` 有 10,000 条记录、占 1,000 页；`Dept` 有 500 条记录、占 50 页。查询：

```sql
SELECT DISTINCT ename
FROM Emp E JOIN Dept D ON E.did = D.did
WHERE D.dname = 'Toy';
```

| 计划 | 估计 I/O 次数 |
|---|---|
| 直接写笛卡尔积再过滤 | ≈ 2,000,000 |
| 页嵌套循环连接（Page NLJ） | ≈ 54,000 |
| 排序归并连接（50 个缓冲区） | ≈ 7,159 |
| 索引嵌套循环连接（Index NLJ） | ≈ 3,151 |

推导：笛卡尔积要物化 `10,000 × 500 = 5,000,000` 个元组；索引 NLJ 只需对 `Dept` 中满足 `dname='Toy'` 的少数行做索引查找。**同样的 SQL，最好与最差差 600 倍以上**——这就是优化器存在的理由。

### 5.2 五级流水线

1. **Parser**：SQL 文本 → 抽象语法树（AST）。只检查语法，不认识表。
2. **Binder**：把 AST 里的名字（表名、列名）解析成**内部 ID**，去 **system catalog** 查 schema、类型、约束。输出「已绑定」的逻辑计划。
3. **Optimizer（逻辑改写）**：应用等价变换（谓词下推、投影下推等），得到更小的搜索空间。
4. **Optimizer（物理选择）**：枚举访问路径与连接算法，用代价模型选最低代价者。
5. **Execution**：把物理计划交给执行引擎（上一讲）。

关键点：**Binder 之后才有 schema 信息**，所以「列是否存在」「类型是否兼容」这类错误在绑定阶段报出，而不是解析阶段。

### 5.3 等价变换规则（讲义给出的四条核心 + 两条基础）

**基础等价性**：

- `σ` 可拆分：`σ_{p1 ∧ p2}(R) ≡ σ_{p1}(σ_{p2}(R))`
- 连接可交换：`R ⋈ S ≡ S ⋈ R`；可结合：`(R ⋈ S) ⋈ T ≡ R ⋈ (S ⋈ T)`

**四种实用变换**：

1. **Split Conjunctive Predicates（拆分合取谓词）**：把 `WHERE a=1 AND b=2` 拆成两个独立过滤，便于分别下推。
2. **Predicate Pushdown（谓词下推）**：把过滤推到叶子。注意**外连接不能随意下推**（会改变语义），`LEFT JOIN` 的右表谓词下推要谨慎。
3. **Replace Cartesian Products with Joins（笛卡尔积转连接）**：识别 `WHERE R.a = S.a` 把 `R × S` 改写成 `R ⋈ S`。这是**最重要**的一条——没有它，优化器会去物化笛卡尔积。
4. **Projection Pushdown（投影下推）**：只保留后续用得到的列，减小元组宽度，减少 I/O 与内存。

**连接顺序的数量**：n 张表的连接顺序有 `(n-1)! × C(n-1)` 种，其中 `C` 是 Catalan 数。n=4 时是 `3! × 5 = 30` 种；n=10 时已超过 170 亿种——**必须靠动态规划或剪枝**，不能暴力枚举。

### 5.4 启发式 vs 基于代价

| 维度 | 启发式（规则） | 基于代价 |
|---|---|---|
| 是否看数据 | 否 | 是（统计信息） |
| 实现难度 | 低 | 高 |
| 可预测性 | 高（同样输入 → 同样计划） | 中（统计信息变化会改计划） |
| 最坏情况 | 可能极差（规则相互冲突） | 通常较好，但依赖统计准确性 |
| 典型系统 | 早期 MySQL、部分 NoSQL | System R、Postgres、SQL Server、Oracle |

实践中两者**结合**：先用规则做「显然正确」的改写（去笛卡尔积、谓词下推），再用基于代价的方法在缩小的空间里搜索。

### 5.5 四种终止条件

1. **Wall-clock Time（墙钟时间）**：优化最多花 N 毫秒，超时就返回当前最优。
2. **Cost Threshold（代价阈值）**：找到代价低于阈值的计划就停（「够好就行」）。
3. **Exhaustion（枚举穷尽）**：搜索空间全部枚举完（小查询常见）。
4. **Transformation Count（变换次数上限）**：最多应用 N 次变换规则。

为什么需要终止条件：**优化时间本身是成本**。一条点查如果优化花 100 ms、执行只要 1 ms，那优化器就是瓶颈——这就是为什么 OLTP 系统常用「简单查询走启发式、复杂查询才走代价搜索」的分流策略。

### 5.6 System R 的三步法

以 `SELECT ARTIST.NAME FROM ARTIST, APPEARS, ALBUM WHERE ...` 为例：

**第一步：为每张表选最佳访问路径**。`ARTIST` 与 `APPEARS` 用顺序扫描（没有可用谓词），`ALBUM` 用 `NAME` 上的索引查找（`ALBUM.NAME = 'Andy''s OG Remix'`）。

**第二步：枚举所有连接顺序**，包括含笛卡尔积的顺序（如 `ARTIST × ALBUM ⋈ APPEARS`），因为某些情况下笛卡尔积后再过滤反而更便宜。

**第三步：自底向上动态规划**。对每一对表，考虑所有物理连接算法（NLJ / SMJ / HJ），每个中间结果**只保留当前代价最低的算子**。这叫 **interesting orders** 的简化版：System R 实际上会为每个子集保留多套计划。

**ORDER BY 的处理**：`ORDER BY ARTIST.ID` 不是逻辑属性，无法在逻辑计划里表达。System R 的做法是**同时保留「有序」与「无序」两套最优计划**，最后比较「无序最优 + 加 SORT」与「有序最优」哪个更便宜。

### 5.7 Top-down 与 branch-and-bound

自顶向下从「根需要什么」开始：

1. 根要求输出按 `ARTIST.ID` 有序。
2. 尝试 `MERGE_JOIN(A1⋈A2, A3)`——排序归并连接天然产出有序结果，满足要求。
3. 尝试 `HASH_JOIN(A1⋈A2, A3)`——不满足有序要求，必须在其上加 `SORT` enforcer，代价更高。
4. 若某分支的**下界代价**已超过当前最优，直接剪掉（branch-and-bound）。

Top-down 的优势：**物理属性（排序、分区）是一等公民**，可以在搜索过程中传播与满足；而 bottom-up 只能在最后再补 SORT。

### 5.8 Enforcer 的工作方式

```sql
SELECT * FROM xxx WHERE xxx.a > 10 ORDER BY xxx.b;
```

- 若 `xxx.b` 上有索引：用 `INDEX_SCAN(xxx.b)`，扫描输出天然按 `b` 有序，**不需要额外排序**。
- 若无索引：`SEQ_SCAN` + `QUICKSORT(T.b)`，代价里必须加上排序的 I/O。

Enforcer 规则的实现方式：当子计划的输出属性不满足父节点要求时，插入一个算子（排序、分区、广播）并**把它的代价计入总数**，然后继续搜索。

### 5.9 表达式重写

两类常见规则：

- **不可能 / 冗余谓词（Impossible / Unnecessary Predicates）**：`WHERE 1 = 0` → 直接返回空；`NOW() IS NULL` → 恒假；`WHERE a = a` → 恒真可删。
- **谓词合并（Merging Predicates）**：`val BETWEEN 1 AND 100 OR val BETWEEN 50 AND 150` → `val BETWEEN 1 AND 150`，把两个范围合并成一个更宽的索引扫描区间。

实现方式：用 **if/then/else 规则引擎**或**模式匹配（pattern matching）**——匹配 → 重写 → 无规则可匹配则停止。

## 6. 代码示例

### 6.1 官方课程代码

本讲**没有官方 notes**（Fall 2026 的 notes 目录中不存在 `15-optimization1.pdf`，2025 版同名文件也未随本讲发布到公开目录），因此本节只引用 slides 中的示意与伪代码。

**（1）五级流水线图**——`90-原始PDF/15-445/slides/15-optimization1.pdf` 第 6–13 页：Application → SQL → Parser → AST → Binder → Logical Plan → Optimizer → Physical Plan，标注了 Binder 查 System Catalog、Optimizer 用 Schema/Estimates/Statistics/Cost Model。

**（2）动机例子的四种计划与 I/O 数字**——同 slides 第 14–42 页：`Emp` 10,000 条 / 1,000 页、`Dept` 500 条 / 50 页，笛卡尔积 2M I/O、Page NLJ 54k、Sort-Merge 7,159、Index NLJ 3,151。

**（3）四种等价变换的图示**——同 slides 第 53–64 页：Split Conjunctive Predicates、Predicate Pushdown、Replace Cartesian Products with Joins、Projection Pushdown（示例用 ARTIST / APPEARS / ALBUM 三表，谓词 `ALBUM.NAME = "Mooshoo Tribute"`）。

**（4）System R 三步法**——同 slides 第 98–113 页：Step #1 选访问路径、Step #2 枚举连接顺序、Step #3 选最低代价；含 `ORDER BY ARTIST.ID` 时保留有序/无序两套计划。

**（5）Top-down 与 enforcer**——同 slides 第 114–142 页：branch-and-bound 示例、`MERGE_JOIN` / `HASH_JOIN` + `SORT` 的竞争、`INDEX_SCAN(xxx.b)` 天然满足 `ORDER BY xxx.b`。

**（6）表达式重写**——同 slides 第 143–154 页：`WHERE 1 = 0` → false、`NOW() IS NULL` → false、`BETWEEN 1 AND 100 OR BETWEEN 50 AND 150` → `BETWEEN 1 AND 150`。

> 待核实：本讲 notes 在 Fall 2026 官网缺失，上述页码全部来自 slides 文本；若后续发布 notes，第 6.1 节应补充 notes 的 Figure 编号与页码。

### 6.2 Agent 自行编写的教学示例

> 以下代码**非官方，仅用于说明概念**，不是 BusTub 的真实优化器代码。

谓词下推的示意（把 `Filter` 推到 `Join` 之下）：

```cpp
// 非官方示例：谓词下推的树改写
// 改写前：Filter(p, Join(R, S))
// 改写后：Join(Filter(p_r, R), Filter(p_s, S))
std::unique_ptr<PlanNode> PushDownPredicate(
    std::unique_ptr<PlanNode> plan, const Predicate &pred) {
  if (auto *join = dynamic_cast<JoinNode *>(plan.get())) {
    // 只下推到谓词实际引用的那一侧
    if (pred.OnlyReferences(join->left()->OutputColumns()))
      join->SetLeft(PushDownPredicate(join->TakeLeft(), pred));
    else if (pred.OnlyReferences(join->right()->OutputColumns()))
      join->SetRight(PushDownPredicate(join->TakeRight(), pred));
  }
  return plan;  // 无法下推时保持在原位
}
```

笛卡尔积转连接的示意（识别等值谓词）：

```cpp
// 非官方示例：把 CrossProduct + 等值谓词改写为 Join
bool IsEquiJoinPredicate(const Predicate &p) {
  // 形如 R.a = S.b，两侧各引用一张表的列
  return p.IsEquality() &&
         p.left().IsColumnRef() && p.right().IsColumnRef() &&
         p.left().table_id() != p.right().table_id();
}
```

自底向上动态规划枚举连接顺序的骨架（非官方，仅示意 Catalan 级复杂度）：

```cpp
// 非官方示例：对子集 S 求最优计划（bitmask DP）
// best[S] = 连接 S 中所有表的最低代价计划
for (size_t mask = 1; mask < (1u << n); mask++) {
  if (__builtin_popcount(mask) == 1) { best[mask] = BestAccessPath(mask); continue; }
  for (size_t sub = (mask - 1) & mask; sub; sub = (sub - 1) & mask) {
    size_t other = mask ^ sub;
    if (!best[sub] || !best[other]) continue;
    auto plan = MakeJoin(best[sub], best[other]);   // 枚举 HJ / SMJ / NLJ
    if (!best[mask] || plan->cost < best[mask]->cost) best[mask] = plan;
  }
}
```

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| 逻辑计划 | 物理计划 | 前者说「做什么」（⋈、σ），后者说「怎么做」（HASH_JOIN、INDEX_SCAN） |
| 等价变换 | 代价估计 | 前者保证**结果相同**、只改结构；后者给结构**打分**，不改结构 |
| 启发式优化 | 基于代价优化 | 前者不看数据、规则固定；后者依赖统计信息枚举+估算 |
| Bottom-up | Top-down | 前者从叶子往上组合（System R），后者从根往下拆解并剪枝（Volcano/Cascades） |
| Predicate Pushdown | Projection Pushdown | 前者把**过滤**推近叶子（减行数）；后者把**列裁剪**推近叶子（减列数） |
| Enforcer | 等价变换 | Enforcer **新增**算子以满足物理属性（改变代价）；等价变换不改变语义也不新增算子 |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Slides | `90-原始PDF/15-445/slides/15-optimization1.pdf` | 156 | 6–13（五级流水线）、14–42（动机例子与四种计划 I/O）、44–47（优化器定义与质量三因素）、49–64（等价变换与四种实用规则）、65–77（搜索算法两派与终止条件）、78–84（访问路径与 sargable）、85–113（bottom-up / System R 三步）、114–142（top-down / branch-and-bound / enforcer）、143–154（表达式重写） |
| Notes | **缺失** | — | Fall 2026 与 Fall 2025 的公开 notes 目录均无 `15-optimization1.pdf`；本讲无官方 notes 可引用 |

原始 URL：

- Slides：`https://15445.courses.cs.cmu.edu/fall2026/slides/15-optimization1.pdf`
- Notes：官方未发布（`https://15445.courses.cs.cmu.edu/fall2026/notes/15-optimization1.pdf` 无对应文件）

> 待核实：notes 缺失一事基于 2026-11-10 的本地镜像与官网目录检查；若后续补发 notes，请重核第 6.1 节与第 8 节的页码。

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内，本讲内容对应 2025 年第 15 讲）

- 标题：Query Planning & Optimization I（2025 年第 15 讲）
- URL：`https://www.youtube.com/watch?v=b53huOGcsZ8&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 年份：2025
- 时间戳：未核实，故不标注。

说明：FAQ Q11 明确 Fall 2026 的录像只对 CMU 学生开放，非 CMU 学习者应观看 Fall 2025 的公开视频。由于 2026 版 notes 缺失，2025 版视频是该讲最完整的公开讲解材料。

## 10. 本节复习

- 能默画五级流水线，并说明 Binder 为什么必须查 system catalog。
- 能复述 `Emp ⋈ Dept` 例子中四种计划的 I/O 数量级差异（2M / 54k / 7,159 / 3,151）。
- 能写出连接交换、结合、谓词拆分、谓词下推、笛卡尔积转连接、投影下推六条规则。
- 能算出 4 张表的连接顺序数量（30 种），并解释为什么要用 DP 而不是暴力枚举。
- 能说出启发式与基于代价各自的优缺点，以及为什么实践中要结合。
- 能列举四种终止条件，并解释「优化时间也是成本」。
- 能描述 System R 三步法，并解释为什么 `ORDER BY` 要保留两套计划。
- 能解释 branch-and-bound 的剪枝条件，以及 enforcer 的插入时机。

## 11. 自我检查

**Q1.** 为什么「谓词下推」几乎总是好的，而「投影下推」在某些情况下收益不明显？

<details><summary>参考答案</summary>

**谓词下推**减少的是**行数**，收益是乘性的：早一步把 1,000,000 行过滤到 100 行，后续所有连接、排序、聚合的代价都按 100 行算。而且它不增加任何额外工作（过滤本来就要做，只是换了个位置做）。

**投影下推**减少的是**列数（元组宽度）**。收益取决于存储格式：

- **行存**：读一页就把整行都读进来了，裁列**不能减少 I/O**，只能减少后续算子处理的数据量（CPU 与内存），收益有限。
- **列存**：每列独立存储，裁列能**直接少读磁盘块**，收益很大。

所以在行存系统里，投影下推主要是省内存与 CPU，不是省 I/O；而且如果下推后需要在上层重新拼装元组（projection 后再 projection），还会增加一次拷贝。这就是「收益不明显」的来源。

</details>

**Q2.** 一个 3 表连接的查询，基于规则（启发式）的优化器与基于代价的优化器可能给出完全不同的计划。举一个具体的反例：规则说「永远用小表做 build 侧」，什么情况下这是错的？

<details><summary>参考答案</summary>

规则「小表做哈希连接的 build 侧」的直觉是：build 侧建哈希表，越小越省内存、越快。

反例：设 `S`（小表，1,000 行）与 `B`（大表，10,000,000 行）连接，连接键上 `S` 有**唯一索引**而 `B` 没有，且查询只取 `B` 中匹配 `S` 的少数行。

- 若按规则把 `S` 做 build 侧：要**全表扫描 10,000,000 行的 `B`** 来 probe，代价 ≈ 扫完整个大表。
- 若改为**索引嵌套循环连接**：对 `S` 的 1,000 行逐个用索引查 `B`，每行几次 I/O，总代价 ≈ 几千次随机 I/O，远小于扫描一千万行。

也就是说，**「小表 build」这条规则只在哈希连接内部成立**，它没有考虑「换一种连接算法（索引 NLJ）可能整体更优」。基于代价的优化器会把「HJ with S build」「HJ with B build」「Index NLJ」三种方案都估一遍代价，再选最低的——这正是规则优化器做不到的。

</details>

**Q3.** System R 为什么要在每个中间结果上同时保留「有序」和「无序」两套最优计划，而不是只保留最便宜的那一套？

<details><summary>参考答案</summary>

因为**最便宜的无序计划 + 一次排序**可能比**稍贵但天然有序的计划**更贵，也可能更便宜——这取决于上层算子是否需要有序输入。

具体地：如果最终要 `ORDER BY ARTIST.ID`，而上层用的是排序归并连接，那么「有序」这个属性可以在连接过程中**免费传播**下来（SMJ 的输出天然有序）；如果只保留了最便宜的无序计划，最后就得额外加一次 `SORT`，而排序大结果集的代价可能远超「选一个稍贵的 SMJ」的差额。

只保留一套计划会导致**局部最优不等于全局最优**：当前最便宜的子树，可能因为不满足上层的物理属性要求而在整体上变贵。System R 的做法是对每个子集保留「按每种 interesting order 的最优计划」，最后在根节点比较「有序计划」与「无序计划 + SORT」的总代价。这与 top-down 优化器把物理属性当一等公民是同一个思想的两种实现。

</details>

**Q4.** 优化器的终止条件里有一条是「代价阈值（cost threshold）」。如果阈值设得太宽松会怎样？太严格呢？

<details><summary>参考答案</summary>

**太宽松（阈值很高，几乎任何计划都算「够好」）**：优化器几乎不搜索就返回第一个可行计划，优化时间极短，但可能选到代价高出几个数量级的计划——典型的「省了 1 ms 优化时间，多花 10 秒执行时间」。对长查询尤其致命。

**太严格（阈值很低，几乎不可能达到）**：优化器会一直搜索到其他终止条件触发（枚举穷尽或墙钟超时），等于把「阈值」这个条件废掉，退化成「尽力搜」。在复杂查询（10 张表以上）上会让优化时间膨胀到秒级甚至分钟级，而收益可能只有几个百分点。

正确做法是**按查询复杂度自适应**：简单查询（≤3 张表）用很小的阈值快速返回，复杂查询才放开搜索预算；同时用墙钟时间做硬上限兜底。Postgres 的 `geqo_threshold`（超过 N 张表才启用遗传算法搜索）就是这种分层策略的体现。

</details>

**Q5.** `WHERE val BETWEEN 1 AND 100 OR val BETWEEN 50 AND 150` 被重写为 `BETWEEN 1 AND 150`。这个改写总是安全的吗？如果 `val` 是字符串类型呢？

<details><summary>参考答案</summary>

对**数值类型**是安全的：两个区间的并集确实是 `[1, 150]`，因为 `[50, 100]` 有重叠，合并后无空洞。

但对**字符串类型不一定安全**：`BETWEEN` 在字符串上按**排序规则（collation）**比较。如果数据库使用非二进制排序（如 `en_US.UTF-8`，忽略大小写与重音），`'a' BETWEEN 'A' AND 'Z'` 的结果与按字节序比较不同；更麻烦的是某些 collation 下区间**不满足稠密性**，合并两个区间可能引入原查询不包含的值。此外若 `val` 是 `CHAR` 定长类型且有尾随空格，比较语义也可能与直觉不同。

更普遍地说，这条规则要求**区间运算在該类型的序关系上是良定义的**（全序、可比较、无 collation 干扰）。对浮点数还要注意 `NaN`：`NaN` 与任何值比较都是 false，合并区间不会把它包含进来，但如果原查询用 `NOT BETWEEN` 就可能出错。所以规则引擎必须**按类型分派**，不能对所有类型套用同一条重写。

</details>

## 12. 进一步学习

- 上一讲：[[15-445-15-Query-Execution-II]] —— 并行执行，决定了物理计划里 exchange 与分区的位置。
- 下一讲：[[15-445-17-Query-Optimization-II]] —— 代价模型、统计信息、基数估计与选择率计算，是本讲「基于代价」那条路的具体化。
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：教材 *Database System Concepts*（第 7 版）第 16 章「Query Optimization」；Goetz Graefe 的 "The Cascades Framework for Query Optimization"（1995）是 top-down 优化器的经典文献；Selinger 等人 1979 年的 "Access Path Selection in a Relational Database Management System" 是 System R 优化器的原始论文。
- 动手建议：在 PostgreSQL 里对同一张表写「笛卡尔积 + WHERE 等值条件」与「显式 JOIN」两种写法，用 `EXPLAIN` 确认优化器把前者改写成了后者（`Nested Loop` / `Hash Join` 而不是 `Nested Loop` 套 `Cartesian Product`）；再关闭 `enable_hashjoin` / `enable_mergejoin` 观察计划如何变化。
