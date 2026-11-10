---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: P3
topic: Project 3 - Query Execution
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 项目
  - 查询执行
  - 算子
  - 迭代器模型
---

# 15-445 Project #3：查询执行（Query Execution）

> **重要边界说明**：本 vault **未抓取** Fall 2026 的 project3 官方页面，本篇为「课程结构公开信息 + 通用知识」整理，**具体规格细节一律标 `> 待核实：`**，不编造。
>
> 官方页面（待人工核对）：`https://15445.courses.cs.cmu.edu/fall2026/project3/`
>
> **唯一可确认的官方线索**：`14-queryexecution2.pdf` 第 **120–126** 页（2026 版 L15 Query Execution II 的末尾）明确讲了项目 #3 的要求，包括：实现 query operators、Plan Node Executors、leaderboard、先实现 `Insert` 与 `Sequential Scan`、只能修改允许的文件、抄袭警告。
>
> 对应讲义：[[15-445-11-Sorting-and-Aggregation]]、[[15-445-14-Query-Execution-I]]、[[15-445-15-Query-Execution-II]]。Fall 2026 课表把 Query Execution 安排在第 13 周。
>
> **Fall 2026 政策提醒**：Project #3 **允许使用 coding agents**，但必须提交**一页反思（reflection）**说明如何使用（官方主页原文 "P3-P4 permit them and require a one-page reflection"）。

## 1. 本节学习目标

1. 掌握**迭代器模型（iterator model / Volcano model）**：`Init()` / `Next()` 的火山式拉取（pull-based）执行。
2. 能实现**顺序扫描（sequential scan）** 与**索引扫描（index scan）** 算子，理解谓词下推（predicate pushdown）。
3. 能实现**聚合（aggregation）**：哈希聚合 vs 排序聚合，以及 `GROUP BY` + `HAVING` 的处理。
4. 能实现**连接（join）**：Nested Loop Join（NLJ）、Index Nested Loop Join（INLJ）、Hash Join、Sort-Merge Join 的算法与适用场景。
5. 能实现**排序（sort）**：外部归并排序（external merge sort）与内存排序的取舍。
6. 能实现 **TopN**：堆（heap）优化，避免全排序。
7. 理解 **Plan Node Executor** 的架构：计划节点（plan node）如何与执行器（executor）配对。
8. 理解**表达式求值（expression evaluation）**：`Expression` 抽象、比较、算术、逻辑运算。

## 2. 前置知识

- **C++17**：虚函数/继承、`std::unique_ptr`、模板、`std::function`。见 `01-Project0-Cpp-Primer.md`。
- **缓冲池与 B+ 树**：扫描算子要读页，索引扫描要用 B+ 树。见 `02-Project1-Buffer-Pool.md`、`03-Project2-BPlusTree.md`。
- **查询执行的三种模型**：迭代器、物化、向量化。见 [[15-445-14-Query-Execution-I]]。
- **排序与聚合**：外部归并排序、哈希聚合。见 [[15-445-11-Sorting-and-Aggregation]]。
- **并行查询**：worker 模型、算子内/算子间并行。见 [[15-445-15-Query-Execution-II]]。
- **表与元组**：`Schema`、`Tuple`、`Column`、`Value`。见 [[15-445-01-Relational-Model-and-Algebra]]。

## 3. 核心概念

### 3.1 Iterator Model（迭代器模型 / Volcano 模型）

每个算子实现三个函数：

```cpp
void Init();                                  // 初始化（重置状态）
bool Next(Tuple *tuple, RID *rid);            // 产出下一行；无更多行返回 false
void Close();                                 // 清理
```

**执行方式**：**拉取（pull-based）**——顶层算子（如 `SELECT` 的输出）不断调用子算子的 `Next()`，子算子再调用它自己的子算子。数据像火山喷发一样从叶节点向上流。

**优点**：流水线（pipelining）、无需物化中间结果、内存占用小。
**缺点**：每个元组一次虚函数调用 → 高开销（约 5–10 ns/元组）。

### 3.2 Sequential Scan（顺序扫描）

从表中逐页、逐槽位读元组，应用谓词（predicate），产出匹配的元组。

**优化**：

- **谓词下推（predicate pushdown）**：把 `WHERE` 条件下推到扫描层，尽早过滤（减少上层的数据量）。
- **投影下推（projection pushdown）**：只读需要的列（列存数据库的关键优化）。
- **预取（prefetch）**：提前把下一页读入缓冲池。

### 3.3 Index Scan（索引扫描）

用 B+ 树定位满足谓词的元组。适用于**高选择性（high selectivity）** 的谓词——即「匹配的行很少」。

**代价权衡**：

- 若谓词匹配 1% 的行 → 索引扫描快（只读少量页）。
- 若谓词匹配 80% 的行 → 全表扫描快（索引扫描有大量随机 I/O + 回表）。

### 3.4 Aggregation（聚合）

**两种实现**：

1. **哈希聚合（hash aggregation）**：用哈希表维护 `group_key → 聚合状态`。适合**分组数少**的场景（哈希表能放进内存）。
2. **排序聚合（sort-based aggregation）**：先按 `group_key` 排序，再顺序扫描并聚合。适合**分组数多**或**数据已排序**的场景。

**聚合函数**：`COUNT`、`SUM`、`AVG`、`MIN`、`MAX`。`AVG` 通常拆成 `SUM / COUNT` 两个状态。

### 3.5 Join（连接）

| 算法 | 复杂度 | 内存 | 适用 |
|---|---|---|---|
| **Nested Loop Join（NLJ）** | O(N×M) | O(1) | 小表、无索引、非等值连接 |
| **Index Nested Loop Join（INLJ）** | O(N×log M) | O(1) | 外表小、内表有索引 |
| **Hash Join** | O(N+M) | O(M) | 等值连接、内存够 |
| **Sort-Merge Join** | O(N log N + M log M) | O(1)~O(M) | 等值连接、两表已排序、有范围条件 |

**Hash Join 的两个阶段**：

1. **Build 阶段**：用较小的表建哈希表（`join_key → tuple list`）。
2. **Probe 阶段**：扫描较大的表，用 `join_key` 探查哈希表。

**Grace Hash Join**（内存不够时）：先把两表按 `join_key` 分区到磁盘，再对每个分区做内存哈希连接。

### 3.6 Sort（排序）

**内存排序**：数据能全部放进内存 → 用 `std::sort`（或 radix sort，对整数更快）。

**外部归并排序（external merge sort）**：

1. **Phase 1（run generation）**：把数据分成若干块，每块在内存中排序，写回磁盘（形成有序 run）。
2. **Phase 2（merge）**：多路归并这些 run，直到只剩一个。

**K 路归并**：每次同时归并 K 个 run，需要 K 个输入缓冲 + 1 个输出缓冲。K 越大，归并轮数越少（`⌈log_K(N/M)⌉`）。

### 3.7 TopN

`ORDER BY ... LIMIT N` 的优化：维护一个**大小为 N 的最大堆**（或最小堆，取决于排序方向），只保留前 N 个。**复杂度 O(M log N)** 而不是 O(M log M)。

### 3.8 Plan Node Executor（计划节点执行器）

BusTub 的架构：**计划节点（`PlanNode`）描述「做什么」**，**执行器（`Executor`）实现「怎么做」**。

```
AbstractPlanNode (抽象计划节点)
  ├── SeqScanPlanNode
  ├── IndexScanPlanNode
  ├── AggregationPlanNode
  ├── NestedLoopJoinPlanNode
  ├── HashJoinPlanNode
  └── ...

AbstractExecutor (抽象执行器)
  ├── SeqScanExecutor
  ├── IndexScanExecutor
  ├── AggregationExecutor
  ├── NestedLoopJoinExecutor
  ├── HashJoinExecutor
  └── ...
```

`ExecutorFactory::Create(plan_node)` 根据计划节点类型创建对应执行器。

### 3.9 Expression（表达式）

`WHERE`、`SELECT`、`HAVING` 中的表达式被表示为**表达式树**：

```
ComparisonExpression(=)
  ├── ColumnValueExpression(col 0)
  └── ConstantValueExpression(42)
```

`Expression::Evaluate(tuple, schema)` 递归求值。

## 4. 通俗理解

**迭代器模型 = 流水线工厂**：最后一道工序（输出）说「给我下一个零件」，倒数第二道就向它前面要……一直到原料仓库（扫描算子）。每个工位只在被要求时才生产一个零件，**不需要仓库堆放半成品**。

**物化模型 = 批量生产**：每个工位一次生产一整批，堆在仓库里，下一道工序再去取。好处是可以优化批处理，坏处是仓库（内存）要够大。

**顺序扫描 = 逐本翻书**：从第一页翻到最后一页，看每页是否符合条件。

**索引扫描 = 查目录**：先查目录找到页码，直接翻到那一页。但如果「符合条件的内容遍布全书」，查目录反而更慢（要跳来跳去）。

**Hash Join = 建通讯录**：把小表的人名做成通讯录（build），然后拿大表的人名去查（probe）。

**Sort-Merge Join = 两份已排序的名单对齐**：两个人的名单都按姓氏排好，各拿一个手指，谁的小就往前挪——一次扫完就完成连接。

**TopN = 只记住前 10 名**：跑马拉松时，你不需要记住所有 3 万人的成绩，只要维护一个「前 10 名」的榜单，每来一个人比较一下，比第 10 名快就挤掉他。

## 5. 原理与推导

> **以下为通用知识整理 + 讲义可确认内容，非依据 project3 官方页面。** 具体任务拆解需以官方页面为准。

### 5.1 迭代器模型的执行过程

考虑查询 `SELECT * FROM t WHERE x > 10`：

```
ProjectionExecutor.Next()
  └─► FilterExecutor.Next()          # 谓词 x > 10
        └─► SeqScanExecutor.Next()   # 逐行读 t
```

**时序**：

1. 顶层调 `Projection.Next()`。
2. `Projection` 调 `Filter.Next()`。
3. `Filter` 调 `SeqScan.Next()` → 得到一行 → 检查 `x > 10`。
4. 若不满足，`Filter` 再调 `SeqScan.Next()`（循环）。
5. 若满足，`Filter` 返回该行给 `Projection`。
6. `Projection` 做投影，返回给顶层。

**关键**：**每次 `Next()` 只处理一行**。控制流是「自上而下的调用，自下而上的数据」。

**`Next()` 的返回约定**（BusTub 风格，待核实）：

- 返回 `true` 并填充 `tuple` / `rid` → 产出一行。
- 返回 `false` → 没有更多行。
- `Init()` 必须能重置状态（支持重新执行）。

### 5.2 顺序扫描的实现要点

```
SeqScanExecutor::Init():
    iter_ = table_heap->Begin()

SeqScanExecutor::Next(tuple, rid):
    while iter_ != table_heap->End():
        auto [current_rid, current_tuple] = *iter_
        ++iter_
        if predicate_ == nullptr or predicate_->Evaluate(&current_tuple, ...):
            *tuple = current_tuple
            *rid = current_rid
            return true
    return false
```

**要点**：

1. **表堆迭代器**：`TableHeap` 提供页级迭代，`TableIterator` 提供元组级迭代。
2. **谓词求值**：`predicate_->Evaluate(&tuple, &schema)` 返回 `Value`，需转成 `bool`。
3. **投影**：若计划要求只输出部分列，需要构造新的 `Tuple`（复制需要的列）。
4. **`RID` 的传递**：某些上层算子（如更新/删除）需要 `RID` 定位行。

**常见坑**：

- 忘记在 `Init()` 中重置迭代器 → 第二次执行返回空。
- 谓词求值时的 `Schema` 用错（应该用表的 schema，不是输出的 schema）。
- 空表时 `Begin() == End()`，`Next()` 直接返回 false。

### 5.3 聚合的实现

**哈希聚合**：

```
AggregationExecutor::Init():
    // 构建阶段：扫描子算子，填充哈希表
    child_->Init()
    while child_->Next(&tuple, &rid):
        group_key = EvaluateGroupByKeys(tuple)
        if group_key not in ht_:
            ht_[group_key] = MakeAggregateState(agg_types_)
        UpdateAggregate(ht_[group_key], tuple)
    // 准备输出
    ht_iter_ = ht_.begin()

AggregationExecutor::Next(tuple, rid):
    while ht_iter_ != ht_.end():
        group_key, state = *ht_iter_
        ++ht_iter_
        if having_ != nullptr and not having_->Evaluate(state):
            continue
        *tuple = MakeOutputTuple(group_key, state)
        return true
    return false
```

**聚合状态的设计**：

```cpp
struct AggregateState {
  // COUNT: 一个计数
  // SUM: 一个累加值
  // AVG: sum + count
  // MIN/MAX: 一个当前极值
  std::vector<Value> values;
};
```

**`COUNT(*)` 的特殊处理**：不需要读列，只需计数。

**`DISTINCT` 聚合**：在状态中维护一个 `unordered_set`（代价高，通常只在必要时用）。

**为什么 `Init()` 要一次性算完所有分组**：因为 `Next()` 是「流式」的，但聚合需要**看到所有输入**才能确定分组。所以聚合算子是**阻塞算子（blocking operator）**——`Init()` 会消耗完所有输入。

**阻塞算子的代价**：无法流水线，必须物化中间结果（哈希表或排序结果）。这就是为什么 `ORDER BY` 和 `GROUP BY` 是查询的「断点」。

### 5.4 连接的实现

**Nested Loop Join（NLJ）**：

```
for each tuple R in outer:
    for each tuple S in inner:
        if predicate(R, S): emit (R, S)
```

**复杂度 O(|R| × |S|)**。优化：

- **块嵌套循环（block NLJ）**：把内表按页缓存，减少重复读。
- **谓词提前**：先检查便宜的谓词（如等值），再检查昂贵的（如函数调用）。

**Index Nested Loop Join（INLJ）**：

```
for each tuple R in outer:
    key = R.join_key
    for each tuple S in index_lookup(inner, key):
        if predicate(R, S): emit (R, S)
```

**复杂度 O(|R| × log |S|)**。要求内表在连接键上有索引。

**Hash Join**：

```
// Build
for each tuple S in build_side:      # 通常是小表
    ht_[S.join_key].push_back(S)

// Probe
for each tuple R in probe_side:      # 通常是大表
    for each tuple S in ht_[R.join_key]:
        if predicate(R, S): emit (R, S)
```

**复杂度 O(|R| + |S|)**。要求**等值连接**（哈希函数需要「相等 → 同哈希」）。

**Grace Hash Join**（内存不够）：

1. **分区**：用 `hash(key) % N` 把两表分到 N 个磁盘文件。
2. **对每个分区**：做内存哈希连接。
3. 若单个分区仍太大 → **递归分区**。

**Sort-Merge Join**：

```
sort R by join_key
sort S by join_key
i = 0, j = 0
while i < |R| and j < |S|:
    if R[i].key < S[j].key: i++
    elif R[i].key > S[j].key: j++
    else:
        # 处理重复键：输出所有匹配对
        emit all pairs with equal key
```

**复杂度 O(|R| log |R| + |S| log |S|)**（排序）+ O(|R| + |S|)（归并）。若已排序，只有归并部分。

**为什么 Sort-Merge 在「有重复键」时很危险**：如果两表都有大量重复键（如 `gender = 'M'`），会产生**笛卡尔积**——归并阶段退化为 O(|R| × |S|)。

**BusTub 的 Hash Join 通常要求支持**：

- 多个连接键（复合键）。
- 输出 schema 的列顺序（左表列 + 右表列）。
- 左外连接（`LEFT JOIN`）——需要处理「右表无匹配」的情况。

> 待核实：BusTub 的 P3 是否要求实现 `HashJoin` 的 `LEFT JOIN` 变体、是否要求 `SortMergeJoin`、是否要求 `NestedLoopJoin` 的非等值谓词。

### 5.5 排序的实现

**外部归并排序的两个阶段**：

**Phase 1（run generation）**：

```
run_count = 0
while 还有数据:
    读入尽可能多的元组（填满内存缓冲 B 页）
    在内存中排序
    写回磁盘 → 形成一个 run
    run_count++
```

**Phase 2（merge）**：

```
while run_count > 1:
    每次归并 K 个 run（K = B - 1，留 1 页做输出缓冲）
    run_count = ceil(run_count / K)
```

**总 I/O 次数**：`2 × N × (1 + ⌈log_K(N/B)⌉)`（读 + 写，每轮一次）。

**优化**：

- **K 越大越好**：减少归并轮数。K = B-1 是最优（用满内存）。
- **预读（prefetch）**：归并时提前读下一个块。
- **替换选择（replacement selection）**：Phase 1 可以产生平均 2B 长度的 run（而不是 B），减少 run 数量。

**内存排序的算法选择**：

- **`std::sort`**：通用，O(n log n) 比较。
- **基数排序（radix sort）**：对整数键 O(n × k)（k = 键的字节数），比比较排序快 2–3 倍。
- **BusTub 的 `SortExecutor`**：通常要求实现外部归并排序（数据可能大于内存）。

> 待核实：BusTub 的 P3 是否要求外部归并排序，还是可以全部放进内存（测试数据量小）；`SortExecutor` 是否要求支持 `LIMIT`（TopN 优化）。

### 5.6 TopN 的实现

**朴素做法**：全排序后取前 N 个 → O(M log M)。

**堆优化**：

```
维护一个大小为 N 的最大堆（若求最小的 N 个）
for each tuple:
    if heap.size < N: heap.push(tuple)
    elif tuple < heap.top():      # 比当前最大还小
        heap.pop()
        heap.push(tuple)
最后堆中的 N 个元素就是答案（需排序输出）
```

**复杂度 O(M log N)**。当 N << M 时，比全排序快得多。

**为什么用最大堆求最小 N 个**：堆顶是「当前前 N 名中最差的那个」。新来的如果比它还差，直接丢弃；如果比它好，替换掉它。

**`ORDER BY ... LIMIT N` 的等价性**：如果查询还有 `OFFSET`，需要 N + offset 个元素。

### 5.7 Plan Node 与 Executor 的配对

**BusTub 的执行流程**：

```
SQL 文本
  → Parser（Binder）→ AST
  → Planner → PlanNode 树
  → Optimizer → 优化后的 PlanNode 树
  → ExecutorFactory::Create(plan) → Executor 树
  → executor->Init(); while (executor->Next(&tuple, &rid)) { ... }
```

**`PlanNode` 的职责**：描述「做什么」——输出 schema、子节点、谓词、连接类型等。**不含任何执行逻辑**。

**`Executor` 的职责**：实现「怎么做」——持有子 executor、状态（迭代器、哈希表）、`Init` / `Next`。

**`ExecutorFactory`**：

```cpp
static std::unique_ptr<AbstractExecutor> CreateExecutor(
    ExecutorContext *ctx, AbstractPlanNodeRef plan) {
  switch (plan->GetType()) {
    case PlanType::SeqScan: return std::make_unique<SeqScanExecutor>(ctx, std::move(plan));
    case PlanType::HashJoin: return std::make_unique<HashJoinExecutor>(ctx, std::move(plan));
    // ...
  }
}
```

**添加新算子的步骤**：

1. 定义 `XxxPlanNode`（若已存在则跳过）。
2. 实现 `XxxExecutor`（继承 `AbstractExecutor`）。
3. 在 `ExecutorFactory` 中注册。
4. 写测试。

### 5.8 表达式求值

**表达式树的节点类型**：

- `ConstantValueExpression`：常量（`42`、`'abc'`）。
- `ColumnValueExpression`：列引用（`t.a`，用 tuple_idx + col_idx 定位）。
- `ComparisonExpression`：`=, <>, <, <=, >, >=`。
- `ArithmeticExpression`：`+, -, *, /, %`。
- `LogicExpression`：`AND, OR, NOT`。
- `AggregateExpression`：`COUNT`, `SUM` 等（只在聚合上下文中）。

**求值**：

```cpp
Value Evaluate(const Tuple *tuple, const Schema *schema) const override {
  auto lhs = children_[0]->Evaluate(tuple, schema);
  auto rhs = children_[1]->Evaluate(tuple, schema);
  switch (cmp_type_) {
    case ComparisonType::Equal: return Value(lhs.CompareEquals(rhs) == CmpBool::kTrue);
    // ...
  }
}
```

**NULL 的处理**：SQL 的三值逻辑（`TRUE` / `FALSE` / `UNKNOWN`）。`NULL = NULL` 结果是 `UNKNOWN`，不是 `TRUE`。这在连接谓词与 `WHERE` 中都必须正确实现。

**常见坑**：

- `ColumnValueExpression` 的 `tuple_idx` 用于区分左表/右表（连接时两表都有 `col 0`）。
- 类型转换：`int` 与 `decimal` 比较时需要提升类型。
- 短路求值：`AND` 应该短路（左边 false 就不算右边），但 SQL 不保证求值顺序（因为可能有副作用）——实际上大多数实现还是短路的。

## 6. 代码示例

### 6.1 官方课程代码

**官方唯一可确认的项目线索**：`14-queryexecution2.pdf` 第 **120–126** 页（2026 版 L15 Query Execution II 末尾），内容包括：

- 项目目标：实现 **query operators**；
- **Plan Node Executors** 的架构说明；
- **Leaderboard**（性能排行榜）；
- 建议**先实现 `Insert` 与 `Sequential Scan`**；
- 只能修改**允许的文件**；
- **抄袭警告**。

> 待核实：该 6 页的具体图示与文字（本笔记未逐页引用原文）；项目页面的完整任务列表、允许修改的文件清单、评分构成、是否有 checkpoint。

### 6.2 Agent 自行编写的教学示例

> 以下代码**非官方，仅用于说明概念**，不是 BusTub 的实现，也不构成项目答案。

**`SeqScanExecutor` 骨架**：

```cpp
// 非官方示例：顺序扫描
class SeqScanExecutor : public AbstractExecutor {
 public:
  SeqScanExecutor(ExecutorContext *ctx, SeqScanPlanNodeRef plan)
      : AbstractExecutor(ctx), plan_(std::move(plan)) {}

  void Init() override {
    auto *table = ctx_->GetCatalog()->GetTable(plan_->GetTableOid());
    iter_ = table->table_->MakeIterator();      // 重置迭代器
  }

  bool Next(Tuple *tuple, RID *rid) override {
    auto *table_info = ctx_->GetCatalog()->GetTable(plan_->GetTableOid());
    const Schema *table_schema = &table_info->schema_;

    while (!iter_.IsEnd()) {
      auto [current_rid, current_tuple] = *iter_;
      ++iter_;

      // 谓词下推：在扫描层就过滤
      if (plan_->GetPredicate() != nullptr) {
        auto pred = plan_->GetPredicate()->Evaluate(&current_tuple, table_schema);
        if (!pred.GetAs<bool>()) continue;
      }

      // 投影（若计划只输出部分列）
      std::vector<Value> values;
      values.reserve(GetOutputSchema().GetColumnCount());
      for (const auto &col : GetOutputSchema().GetColumns()) {
        values.push_back(col.GetExpr()->Evaluate(&current_tuple, table_schema));
      }

      *tuple = Tuple(std::move(values), &GetOutputSchema());
      *rid = current_rid;
      return true;
    }
    return false;
  }

 private:
  SeqScanPlanNodeRef plan_;
  TableIterator iter_;
};
```

**`HashJoinExecutor` 骨架**：

```cpp
// 非官方示例：哈希连接（内连接）
class HashJoinExecutor : public AbstractExecutor {
 public:
  void Init() override {
    // Build 阶段：用右表建哈希表
    child_right_->Init();
    Tuple right_tuple;
    RID right_rid;
    while (child_right_->Next(&right_tuple, &right_rid)) {
      auto key = EvaluateJoinKey(right_tuple, /*is_left=*/false);
      ht_[key].push_back(right_tuple);
    }
    // Probe 阶段准备
    child_left_->Init();
    matched_.clear();
    probe_ready_ = false;
  }

  bool Next(Tuple *tuple, RID *rid) override {
    while (true) {
      // 若当前左行还有未输出的匹配，继续输出
      if (match_idx_ < current_matches_.size()) {
        *tuple = Combine(current_left_tuple_, current_matches_[match_idx_++]);
        return true;
      }
      // 否则取下一个左行
      if (!child_left_->Next(&current_left_tuple_, &dummy_rid_)) return false;
      auto key = EvaluateJoinKey(current_left_tuple_, /*is_left=*/true);
      auto it = ht_.find(key);
      current_matches_.clear();
      match_idx_ = 0;
      if (it != ht_.end()) {
        for (const auto &r : it->second) {
          if (plan_->GetPredicate() == nullptr ||
              plan_->GetPredicate()->EvaluateJoin(&current_left_tuple_, &r).GetAs<bool>()) {
            current_matches_.push_back(r);
          }
        }
      }
      // 循环回去输出匹配（若为空，继续取下一行）
    }
  }

 private:
  std::unordered_map<JoinKey, std::vector<Tuple>> ht_;
  std::vector<Tuple> current_matches_;
  size_t match_idx_{0};
  Tuple current_left_tuple_;
  RID dummy_rid_;
};
```

**`AggregationExecutor` 骨架**：

```cpp
// 非官方示例：哈希聚合
void AggregationExecutor::Init() {
  ht_.clear();
  child_->Init();
  Tuple tuple;
  RID rid;
  while (child_->Next(&tuple, &rid)) {
    auto group_key = EvaluateGroupBy(&tuple);
    auto &state = ht_[group_key];          // 不存在则默认构造
    UpdateState(state, tuple);
  }
  iter_ = ht_.begin();
}

bool AggregationExecutor::Next(Tuple *tuple, RID *rid) {
  while (iter_ != ht_.end()) {
    auto &[key, state] = *iter_;
    ++iter_;
    if (having_ != nullptr && !having_->EvaluateAggregate(state).GetAs<bool>()) continue;
    *tuple = MakeOutputTuple(key, state);
    *rid = RID{};
    return true;
  }
  return false;
}
```

**TopN 的堆实现**：

```cpp
// 非官方示例：TopN
struct TopN {
  size_t n;
  std::priority_queue<Tuple, std::vector<Tuple>, std::less<Tuple>> heap;   // 最大堆

  void Offer(const Tuple &t) {
    if (heap.size() < n) {
      heap.push(t);
    } else if (t < heap.top()) {        // 比当前最大还小
      heap.pop();
      heap.push(t);
    }
  }
};
```

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| 迭代器模型 | 物化模型 | 前者逐行拉取（流水线、低内存）；后者一次算完（可批优化、高内存） |
| 顺序扫描 | 索引扫描 | 前者读全表（适合低选择性）；后者走 B+ 树（适合高选择性） |
| Hash Join | Sort-Merge Join | 前者需等值连接、内存建哈希表；后者支持范围、可无额外内存（但排序有代价） |
| NLJ | INLJ | 前者暴力双重循环；后者内表有索引，用索引查找 |
| 阻塞算子 | 流水线算子 | 前者（`Sort`、`Aggregation`）必须看完所有输入；后者（`Filter`、`Projection`）可逐行处理 |
| `PlanNode` | `Executor` | 前者描述「做什么」（数据）；后者实现「怎么做」（逻辑） |
| `Init()` | 构造函数 | `Init()` 可重复调用（重置状态、支持重新执行）；构造函数只调用一次 |
| TopN | 全排序 | 前者 O(M log N)（堆）；后者 O(M log M) |
| `LEFT JOIN` | 内连接 | 前者右表无匹配时输出 NULL；后者直接丢弃 |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Slides（L14 Query Execution I） | `90-原始PDF/15-445/slides/13-queryexecution1.pdf` | 135 | 迭代器模型、物化、向量化、索引扫描、表达式 |
| Notes（L14） | `90-原始PDF/15-445/notes/13-queryexecution1.pdf` | 7 | Fig1 迭代器伪代码（p1–2）、Fig2 物化（p2）、Fig3 向量化（p3）、Fig5/6 索引与多索引扫描（p6）、Fig7 表达式树（p7） |
| Slides（L15 Query Execution II） | `90-原始PDF/15-445/slides/14-queryexecution2.pdf` | 126 | **p120–126：Project #3 说明（唯一可确认的项目线索）** |
| Notes（L15） | `90-原始PDF/15-445/notes/14-queryexecution2.pdf` | 6 | Fig1 进程模型（p1–2）、Fig2 线程模型（p2–3）、Fig3 嵌入式（p3）、Fig4 算子内并行（p4）、Fig5/6 算子间 + bushy（p5） |
| Slides（L11 Sorting & Aggregation） | `90-原始PDF/15-445/slides/11-sortingandaggregation.pdf` | 待人工核对 | 外部归并排序、哈希聚合 |
| Project #3 官方页面 | **未抓取** | — | — |

原始 URL：

- `https://15445.courses.cs.cmu.edu/fall2026/slides/13-queryexecution1.pdf`
- `https://15445.courses.cs.cmu.edu/fall2026/slides/14-queryexecution2.pdf`
- `https://15445.courses.cs.cmu.edu/fall2026/notes/13-queryexecution1.pdf`
- `https://15445.courses.cs.cmu.edu/fall2026/notes/14-queryexecution2.pdf`
- 项目页面：`https://15445.courses.cs.cmu.edu/fall2026/project3/`（**待人工访问核对**）

> 待核实：`11-sortingandaggregation.pdf` 的总页数与重点页码；project3 页面的任务拆解、允许修改的文件、评分构成（是否含 leaderboard 加分）、是否要求外部排序。

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内，本讲内容对应 2025 年第 13/14 讲）

- 标题：Query Execution I / II（2025 年第 13、14 讲）
- URL（第 13 讲）：`https://www.youtube.com/watch?v=E-UUd6cB57w&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- URL（第 14 讲）：`https://www.youtube.com/watch?v=Kzf1hGjtZOU&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 年份：2025
- 时间戳：未核实，故不标注。

说明：FAQ Q11 明确 Fall 2026 的录像只对 CMU 学生开放，非 CMU 学习者应观看 Fall 2025 的公开视频。排序与聚合对应 2025 年第 10 讲（2026 第 11 讲），ID 未在任务映射表中给出，待核实。

## 10. 本节复习

- 能写出迭代器模型的三个函数签名，并说明 `Next()` 的返回约定。
- 能实现顺序扫描 + 谓词下推。
- 能说明索引扫描的适用条件（高选择性），以及为什么低选择性时全表扫描更快。
- 能实现哈希聚合，并说明为什么它是阻塞算子。
- 能对比 NLJ / INLJ / Hash Join / Sort-Merge Join 的复杂度与适用场景。
- 能画出外部归并排序的两个阶段，并计算 I/O 次数。
- 能说明 TopN 为什么用堆、复杂度是多少。
- 能说出 `PlanNode` 与 `Executor` 的职责分工。

## 11. 自我检查

**Q1.** 为什么迭代器模型（Volcano）在高性能分析型查询中会被向量化模型取代？

<details><summary>参考答案</summary>

**因为迭代器模型的「每行一次虚函数调用」开销在大数据量下不可忽略。**

**具体分析**：

1. **虚函数调用开销**：每次 `Next()` 是一次间接跳转（vtable 查找），约 5–10 ns。处理 10 亿行 → 5–10 秒的纯调度开销。
2. **无法利用 CPU 流水线与 SIMD**：一次只处理一行，编译器无法向量化循环（因为 `Next()` 是不透明的函数调用）。
3. **分支预测失败**：`Next()` 内部的 `if (predicate)` 每次都要判断，分支预测器难以学习（数据随机）。
4. **缓存不友好**：每次 `Next()` 只返回一行，数据在寄存器/缓存中停留时间短。

**向量化模型（vectorized / batch model）**：

- `Next()` 一次返回**一批**（如 1024 行）而不是一行。
- 算子内部用**紧凑循环**处理这批数据 → 编译器可以自动向量化（SIMD）、流水线友好。
- 虚函数调用摊薄到 1/1024。
- 列存布局（columnar）进一步让同一列的数据连续存放 → 缓存友好、压缩率高。

**性能差距**：TPC-H 类查询上，向量化通常比行式迭代器快 **5–20 倍**。

**但迭代器模型仍有价值**：

- **OLTP**（点查、小事务）：每次只处理几行，向量化的批处理优势无法体现，反而增加延迟。
- **实现简单**：`Init`/`Next` 接口清晰，易于扩展新算子。
- **流水线**：无需物化中间结果，内存占用低。

**工业实践**：

- **PostgreSQL**：行式迭代器（Volcano），通过「表达式 JIT 编译」部分弥补。
- **DuckDB、ClickHouse、Vectorwise**：向量化。
- **MonetDB**：最早的向量化实现之一。
- **HyPer、TUM**：编译执行（compilation / code generation），把整个查询编译成机器码，彻底消除算子间的调度开销。

**一句话**：迭代器模型是「通用且简单」，向量化是「分析型查询的最优」。这就是为什么 [[15-445-14-Query-Execution-I]] 要专门讲这三种模型的对比。

</details>

**Q2.** 哈希连接中，应该用哪个表建哈希表（build side）？如果选错了会怎样？

<details><summary>参考答案</summary>

**应该用「较小的表」建哈希表。**

**理由**：

1. **内存占用**：哈希表的大小与 build side 的行数成正比。用大表建 → 哈希表可能装不进内存 → 需要 Grace Hash Join（分区到磁盘），代价大增。
2. **构建成本**：build 阶段要遍历整个 build side 并插入哈希表。用小表 → 构建快。
3. **Probe 成本**：probe 阶段遍历 probe side 并查表。用大表 probe → 查找次数多，但每次查找是 O(1)，总成本 O(|probe|)。**总成本 = O(|build| + |probe|)**，与谁做 build 无关（在内存足够时）。
4. **缓存局部性**：小哈希表能放进 CPU 缓存（L2/L3），probe 时命中率高。

**如果选错（用大表 build）**：

- **哈希表溢出内存** → 必须用 Grace Hash Join：
  1. 把两表按 `hash(key) % N` 分区到磁盘。
  2. 对每个分区做内存哈希连接。
  3. I/O 成本增加 2×（写分区 + 读分区），可能还要递归分区。
- **性能下降 2–10 倍**（取决于溢出程度）。
- **可能 OOM**（内存不足）→ 查询失败。

**优化器如何选**：

- 用**基数估计（cardinality estimation）** 估算两表的大小。
- 若估计不准（统计信息过期）→ 选错 build side → 性能灾难。
- 这就是为什么 [[15-445-16-Query-Optimization-I]] 要花大量篇幅讲基数估计。

**特殊情况**：

- **两表都很大**：选「过滤后更小」的那个（考虑谓词下推后的行数）。
- **有 `LEFT JOIN`**：build side 必须是**右表**（因为要保留左表的所有行，包括无匹配的）。若右表很大，可能需要特殊处理（记录哪些左行已匹配）。
- **有 `LIMIT`**：可以用「惰性 build」——只 build 需要的部分。

**一个实践技巧**：**Bloom filter 预过滤**。如果 build side 很大但 probe side 的匹配率很低，可以在 build 阶段同时构建一个 Bloom filter，probe 时先用 Bloom filter 快速排除不匹配的键（避免访问哈希表）。这在分布式连接（半连接）中很常用。

</details>

**Q3.** 外部归并排序中，为什么 K 路归并的 K 要取「内存页数 - 1」？

<details><summary>参考答案</summary>

**因为归并需要 K 个输入缓冲 + 1 个输出缓冲，总共 K+1 页内存。**

**具体分析**：

1. **K 路归并**：同时从 K 个有序 run 中取最小元素。每个 run 需要一个**输入缓冲页**（存放当前读入的一块数据）。
2. **输出缓冲**：归并结果要先写到输出缓冲，满了再刷盘。需要 **1 页**。
3. **总内存**：`K + 1` 页。若可用内存是 `B` 页，则 `K = B - 1`。

**为什么 K 越大越好**：

- **归并轮数** = `⌈log_K(N/B)⌉`（N 是总页数，B 是内存页数，Phase 1 产生 `N/B` 个 run）。
- **总 I/O** ≈ `2N × (1 + 归并轮数)`。
- K 从 2 增到 B-1：轮数从 `log_2(N/B)` 降到 `log_{B-1}(N/B)`。

**具体数字**：设 N = 1,000,000 页（4GB），B = 100 页（400KB）。

- **2 路归并**：`log_2(10000) ≈ 14` 轮 → I/O ≈ `2 × 10^6 × 15 = 3 × 10^7` 页次。
- **99 路归并**：`log_99(10000) ≈ 2` 轮 → I/O ≈ `2 × 10^6 × 3 = 6 × 10^6` 页次。
- **差 5 倍**。

**为什么不能 K = B**：

- 没有输出缓冲 → 每次写一个元组就要刷盘（或写半页），写放大严重。
- 实际上输出缓冲可以小于 1 页，但至少要有一定大小才能 amortize 写成本。

**为什么不能 K > B - 1**：

- 内存不够，无法同时持有 K 个输入缓冲。

**优化：不均衡缓冲**：

- 不是每个 run 都分配 1 页，而是按「run 的长度」分配（长 run 多分配）。
- 这叫 **不均衡 K 路归并（uneven K-way merge）**，能进一步减少 I/O。

**Phase 1 的优化：替换选择（replacement selection）**：

- 朴素做法：读满 B 页 → 排序 → 写出一个长度 B 的 run。
- 替换选择：维护一个大小为 B 的堆，每输出一个元素就从输入读一个新元素。若新元素比刚输出的元素大，可以继续放在当前 run；否则留到下一个 run。
- **平均 run 长度 = 2B**（而不是 B）→ run 数量减半 → 归并轮数减一。

**现代硬件的考虑**：

- SSD 的随机读很快，K 的选择不那么关键（但仍影响顺序读的带宽利用率）。
- 大内存机器上，数据可能全部放得下 → 直接内存排序（`std::sort` 或 radix sort），不需要外部排序。
- 这就是为什么很多现代数据库在内存足够时**完全跳过外部排序**。

</details>

**Q4.** 为什么聚合算子（`GROUP BY`）和排序算子（`ORDER BY`）被称为「阻塞算子」，而 `Filter` 不是？

<details><summary>参考答案</summary>

**因为阻塞算子必须「看到全部输入」才能产出第一行输出；`Filter` 只需要看到一行就能决定是否输出。**

**具体对比**：

| 算子 | 能否在看到第一行输入后立即输出？ | 原因 |
|---|---|---|
| `Filter`（`WHERE`） | **能** | 每行的去留独立判断，不依赖其他行 |
| `Projection`（`SELECT`） | **能** | 每行的投影独立计算 |
| `Limit` | **能**（到 N 行就停） | 只需计数 |
| `Aggregation`（`GROUP BY`） | **不能** | 要看到所有行才能确定每个分组的最终聚合值（`SUM` 要累加完） |
| `Sort`（`ORDER BY`） | **不能** | 要看到所有行才能确定第一行是谁 |
| `Hash Join`（build 阶段） | **部分** | build 阶段必须看完 build side；probe 阶段可以流式输出 |
| `TopN` | **部分** | 要看完所有输入，但只维护 N 个元素（内存 O(N)） |

**阻塞的后果**：

1. **无法流水线**：上游必须先把所有数据算完并物化（哈希表、排序结果），下游才能开始。
2. **内存压力**：物化的中间结果可能很大 → 需要溢出到磁盘（Grace Hash Join、外部排序）。
3. **延迟高**：用户要等整个聚合/排序完成才能看到第一行（除非是流式聚合，如「按时间窗口」）。
4. **优化机会**：优化器会尽量把阻塞算子**上移**（靠近根），减少它处理的数据量。例如：
   - `SELECT dept, SUM(sal) FROM emp WHERE age > 30 GROUP BY dept`
   - 谓词 `age > 30` 应该在聚合**之前**执行（下推到扫描层），减少聚合的输入。

**例外：流式聚合**：

某些系统支持「流式聚合」——如果输入已经按 `group_key` 排序，聚合算子可以**边读边输出**（每读完一个分组就输出该组的结果）。这时它不再是阻塞的。

**这就是「排序聚合」相对「哈希聚合」的一个优势**：如果数据已经按 `group_key` 排序（比如 B+ 树的聚簇索引），排序聚合可以流水线输出，而哈希聚合必须等所有输入。

**另一个例外：`LIMIT` + `ORDER BY`**：

`ORDER BY x LIMIT 10` 可以用 TopN 算子——它不是完全阻塞的（内存 O(10)），但仍需看完所有输入才能确定最终的 10 个。

**对查询优化的启示**：

- 阻塞算子是查询计划的「断点」，优化器会围绕它们做决策（如选择 hash join 还是 sort-merge join）。
- 多个阻塞算子串联 → 多次物化 → 性能下降。优化器会尝试合并或重排。

</details>

## 12. 进一步学习

- 项目导航：[[00-项目总览]]
- 上一个项目：`03-Project2-BPlusTree.md`
- 下一个项目：`05-Project4-Concurrency-Control.md`
- 相关讲义：[[15-445-11-Sorting-and-Aggregation]]（外部排序、哈希聚合）、[[15-445-14-Query-Execution-I]]（迭代器/物化/向量化）、[[15-445-15-Query-Execution-II]]（并行查询，**p120–126 含 Project #3 说明**）、[[15-445-16-Query-Optimization-I]]（基数估计与连接顺序）
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：
  - Graefe, "Volcano — An Extensible and Parallel Query Evaluation System"（TKDE 1994）——迭代器模型的原始论文。
  - Graefe, "Query Evaluation Techniques for Large Databases"（ACM Computing Surveys, 1993）——**查询执行的经典综述**，涵盖所有算子。
  - Neumann, "Efficiently Compiling Efficient Query Plans for Modern Hardware"（VLDB 2011）——编译执行（HyPer）。
  - Boncz, Zukowski, Nes, "MonetDB/X100: Hyper-Pipelining Query Execution"（CIDR 2005）——向量化执行的经典论文。
  - 教材 *Database System Concepts*（7th Ed.）第 15 章（Query Processing）。
  - BusTub 仓库 `src/include/execution/` 下的 `executors/` 与 `expression/` 目录。
- 动手建议：先实现 `SeqScan` + `Insert`（官方建议的顺序），跑通 `seq_scan_test`；再实现 `Aggregation`、`Join`、`Sort`；最后用 `EXPLAIN` 观察计划树，验证算子之间的数据流。
- **提醒**：本篇依据课程结构公开信息 + 通用知识整理，唯一可确认的官方项目线索是 `14-queryexecution2.pdf` p120–126。具体任务以官方 project3 页为准。`> 待核实：` 处需人工核对。
