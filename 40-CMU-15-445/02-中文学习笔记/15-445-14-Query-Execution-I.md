---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: L14
topic: Query Execution I
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 数据库
  - 查询执行
  - 迭代器模型
  - 向量化
  - 顺序扫描
---

# 15-445 L14：查询执行 I（Query Execution I）

> 优化器给出的是「逻辑上要做什么」，执行引擎要回答的是「在机器上具体怎么跑」。这一讲把查询计划拆成算子流水线，讲清三种执行模型（迭代器 / 物化 / 向量化）、三种访问路径（顺序扫描 / 索引扫描 / 多索引扫描）以及表达式求值——它们是 Project #3 的直接理论来源。

## 1. 本节学习目标

学完本讲，你应该能够：

1. 说出**查询计划（query plan）**是一张算子 DAG，并解释**流水线（pipeline）**与**流水线中断算子（pipeline breaker）**的区别，能对一条 SQL 手动切分流水线。
2. 对比**迭代器模型（iterator model）**、**物化模型（materialization model）**、**向量化模型（vectorization model）**三者的调用次数、内存行为与适用负载（OLTP vs OLAP）。
3. 说明**自顶向下拉取（top-to-bottom / pull）**与**自底向上推送（bottom-to-top / push）**两种控制流的差异，以及各自在虚函数开销、缓存局部性上的取舍。
4. 描述**顺序扫描（sequential scan）**的实现与常见优化（压缩、区图 zone map、近似查询），并解释**区图**为何是「无损」跳过。
5. 说明**索引扫描（index scan）**的代价影响因素，以及**多索引扫描（multi-index scan）**如何用集合交并求 record id。
6. 指出**修改查询（modification query）**要维护索引与约束，并解释**万圣节问题（Halloween problem）**的成因与两种解法。
7. 画出**表达式树（expression tree）**与**执行上下文（execution context）**的结构，说明常量折叠与公共子表达式消除为什么能加速求值。

## 2. 前置知识

- **关系代数与算子语义**：σ/π/⋈ 与 `WHERE`/`SELECT`/`JOIN` 的对应，见 [[15-445-01-Relational-Model-and-Algebra]]。
- **连接算法**：嵌套循环连接、排序归并连接、哈希连接的基本代价直觉，见 [[15-445-13-Joins-Algorithms]]。
- **排序与聚合**：外部归并排序、哈希聚合，见 [[15-445-11-Sorting-and-Aggregation]]。
- **存储与页**：页、槽式页、record id、行存 vs 列存，见 [[15-445-03-Database-Storage-I]] 与 [[15-445-06-Storage-Models-and-Compression]]。
- **索引**：B+ 树与哈希索引的查找代价，见 [[15-445-08-Indexes-and-Filters-I]]。
- **C++ 提醒**：本课程项目用 **C++17** 编写、遵循 **Google C++ Style** 并用 clang-format 格式化；执行器要写大量虚函数与 `std::unique_ptr` 所有权转移，建议先补 RAII、`std::move`、`override` 与 `const` 正确性。

## 3. 核心概念

### 3.1 Query Plan（查询计划）

优化器输出的**算子 DAG（有向无环图）**：叶子是表访问（顺序扫描 / 索引扫描），中间节点是连接、聚合、排序、投影，根节点产出结果。同一条 SQL 可以对应许多张执行代价不同的计划。

### 3.2 Pipeline（流水线）

在一条流水线内，一个算子产出的元组**不需要落盘或落中间结构**，直接被父算子消费。流水线越连续，内存占用越小、启动延迟越低。

### 3.3 Pipeline Breaker（流水线中断算子）

必须把**全部子输入消费完**才能产出第一个元组的算子：连接（build side 建哈希表时）、子查询、`ORDER BY`（要排完序才能输出）。它把计划切成多段流水线，是调优时关注的重点。

### 3.4 Iterator Model（迭代器模型）

每个算子实现 `Next()`（返回一个元组或「没有了」）、`Open()`、`Close()`。父算子循环调用子算子的 `Next()`，形成** Volcano / Pipeline 模型**。几乎所有行存 DBMS 都用它，因为实现简单、天然支持流水线、`LIMIT` 可以直接停止调用。

### 3.5 Materialization Model（物化模型）

每个算子一次把**全部输入**处理完，`Output()` 返回整个结果集。调用次数少、适合 OLTP（点查结果小）；但在 OLAP 中中间结果巨大，必须落盘（spill），代价高。讲义标注为 "Rare"。

### 3.6 Vectorization Model（向量化模型）

每个算子每次 `Next()` 返回**一批（batch）元组**（典型 1024–4096 个），batch 大小可随硬件与查询变化。它把「每元组一次虚函数调用」摊薄成「每批一次」，并且能在批内用 **SIMD** 与向量化指令；OLAP 的主流选择，讲义标注为 "Common"。

### 3.7 Top-to-Bottom (Pull) vs Bottom-to-Top (Push)（拉取 vs 推送）

**Pull**：从根节点开始，父算子调用子算子取数据——最常见的实现。**Push**：从叶子开始把元组推给父算子，把控制流下沉到叶节点，能更好地控制寄存器与 CPU 缓存，但实现更复杂。

### 3.8 Sequential Scan（顺序扫描）

遍历表的每个页、页内每个槽位，对每行求值谓词。DBMS 维护一个**游标（cursor）**记录当前页与槽位，可被并发访问。它是**兜底方案（fallback）**：任何时候都能用。

### 3.9 Zone Map（区图）

为**每一页（或每批页）的每一列**预先计算聚合信息（min / max / sum / count / null 数）。查询时先看区图，若谓词与 `[min, max]` 无交集，就**整页跳过**。与近似查询不同，区图是**无损（lossless）**的：它只用来跳过不可能匹配的页，不改变结果。

### 3.10 Index Scan（索引扫描）

用索引（B+ 树 / 哈希 / 倒排）定位满足谓词的 record id，再回表取元组。选择索引时要考虑：索引包含哪些列、查询引用了哪些列、谓词的值域、谓词组合方式、键是否唯一。

### 3.11 Multi-Index Scan（多索引扫描）

对同一张表的多个谓词各用一个索引，得到多个 record id **集合**，再按谓词逻辑求**交 / 并**（用 bitmap、hash set 或 Bloom filter），最后只回表读取通过筛选的记录。适合各谓词都有高选择性索引的场景。

### 3.12 Modification Query（修改查询）

`INSERT` / `UPDATE` / `DELETE` 要检查约束（主键、外键、`CHECK`）、更新**所有受影响的索引**、维护触发器，并输出被修改行的 record id 供上层使用。

### 3.13 Halloween Problem（万圣节问题）

更新操作若改变了元组的**物理位置**（例如更新索引键导致记录在索引中移动），扫描器可能**再次访问到刚被移动的记录**，造成重复更新。名字来自 1976 年 System R 团队在万圣节发现该问题。解法：扫描器记录**已修改过的 record id**，跳过它们（或使用临时表 / 快照）。

### 3.14 Expression Evaluation（表达式求值）

`WHERE` 子句被编译成**表达式树**：叶子是列引用、常量、参数，内部节点是比较、`AND`/`OR`、算术运算。求值时携带**执行上下文（execution context）**：当前元组、参数、输出 schema。逐节点遍历较慢，可采用 **JIT 编译**（把树编译成机器码）或向量化求值。

## 4. 通俗理解

把查询计划想成一条**工厂流水线**。

- **迭代器模型** = 装配工位「按需取件」：下一道工序伸手要一个零件，上一道工序才做一个。省库存（内存），但每要一次都要喊一嗓子（虚函数调用）。点查（OLTP）里一条查询只做几个零件，很划算。
- **物化模型** = 每道工序先把**一整批**做完堆在车间，再交给下一道。工位之间不用频繁喊话，但中间库存可能堆满整个车间（OLAP 大中间结果要落盘）。
- **向量化模型** = 用**托盘**送货，一次送 1024 个零件。喊话次数降到千分之一，还能用叉车（SIMD）一次搬一排。

**流水线中断算子**就是「必须等所有原料到齐才能开工」的工序——比如哈希连接要先把 build 侧全部装进哈希表。它像一道**水坝**，把上游流水线截断，所以调优时要尽量让它早一点、小一点。

**区图**像仓库每个货架挂的标签：「本架货物生产日期 2024-01 到 2024-06」。你找 2025 年的货，看一眼标签就知道整架不用翻——**不丢任何货**，只是省了翻找。

## 5. 原理与推导

### 5.1 从 SQL 到执行：计划是一张 DAG

讲义给的例子：

```sql
SELECT R.id, S.cdate
FROM R JOIN S ON R.id = S.id
WHERE S.value > 100;
```

计划：`R` 与 `S` 各自顺序扫描 → `S` 上做过滤（`value > 100`）→ 哈希连接 → 投影 `id, cdate`。因为哈希连接要先把 build 侧读完才能 probe，这条计划被切成**两段流水线**：

- Pipeline #1：扫描 `S` → 过滤 → 建哈希表（结束）
- Pipeline #2：扫描 `R` → probe 哈希表 → 输出

推导要点：**流水线的边界由 pipeline breaker 决定**，而不是由算子的逻辑顺序决定。反过来，如果把 `R` 当 build 侧，两段流水线的划分就变了——这是执行层与优化层交界处的实际决策。

### 5.2 三种执行模型的调用次数

设一个算子处理 N 个元组、每批 B 个元组：

| 模型 | 父算子调用子算子次数 | 每次返回 | 中间结果存放 |
|---|---|---|---|
| 迭代器 | ≈ N 次 | 1 个元组 | 不物化（流式） |
| 物化 | 1 次 | 全部 N 个元组 | 全部物化（可能落盘） |
| 向量化 | ≈ N / B 次 | B 个元组 | 批内驻留 CPU 缓存 |

虚函数调用在迭代器模型下是 `N × 算子数` 次；向量化把它降到 `(N/B) × 算子数`。B = 1024 时调用开销近似消失，剩下的时间花在真正的计算上——这就是向量化在 OLAP 上快数倍的根本原因。

### 5.3 拉取与推送的控制流

- **Pull**：`root.Next()` → `child.Next()` → … → 叶子。控制流自上而下，数据自下而上。优点是实现简单、`LIMIT` 天然短路；缺点是每层都有虚函数与分支。
- **Push**：叶子把元组 `Push()` 给父算子，父算子处理完再推给祖父。控制流自下而上，**叶子驱动**，编译器/CPU 更容易预测与内联，寄存器压力更可控。

两者产出的结果集完全相同，只是**谁掌握循环**不同（父算子掌握循环 = pull，子算子掌握循环 = push）。

### 5.4 顺序扫描的优化清单

讲义与 notes 给出的优化方向：

1. **压缩 / 编码**：把页压小，减少 I/O 带宽；`RLE`（游程编码）对有序、低基数列尤其有效。
2. **预取（prefetching）**：提前把后续页读进缓冲池，隐藏延迟。
3. **缓冲池旁路（buffer pool bypass）**：大扫描不要污染缓冲池（避免 sequential flooding），直接用临时缓冲。
4. **并行化**：多 worker 各扫一段。
5. **延迟物化（late materialization）**：列存里先只读谓词列，通过筛选后再读其他列。
6. **堆聚簇（heap clustering）**：让常一起访问的元组物理相邻。
7. **结果缓存 / 物化视图**。
8. **代码特化 / JIT**：为这条查询生成专用代码。
9. **近似查询（approximate queries，有损）**：抽样估算，牺牲精确性。
10. **区图（zone map，无损）**：跳过不可能命中的页。

### 5.5 区图为什么无损

区图只存每页每列的 `min`/`max` 等**上界信息**。谓词 `age > 50` 遇到某页 `max_age = 40`，则该页**必然**没有匹配行——跳过它是**逻辑蕴含**，不是近似。反之 `min_age = 60` 表示整页都满足，可以直接把整页加入结果，连谓词都不用求值。因此区图既能跳页，也能**整页短路**，但永远不会漏掉或错加结果。

### 5.6 索引扫描的选择

设一张 100 行的表，`age` 与 `department` 上各有一个索引。查询 `WHERE age = 20 AND department = 'CS'`：

- 若 `department = 'CS'` 只匹配 2 行，先用 department 索引找出这 2 个 record id，再回表验证 `age = 20`，只需 2 次回表。
- 若 `department = 'CS'` 匹配 80 行，用 age 索引更划算。

结论：**索引扫描的代价 ≈ 索引查找代价 + 命中行数 × 回表代价**，所以选择率（selectivity）决定选哪个索引；两个谓词都高选择时，用多索引扫描求交集。

### 5.7 多索引扫描的集合运算

对 `WHERE age = 20 AND department = 'CS' AND country = 'US'`：

1. `age` 索引给出集合 `S1`（record id）。
2. `department` 索引给出集合 `S2`。
3. `S1 ∩ S2` 得到同时满足前两个谓词的记录。
4. 回表读取这些记录，再应用无法走索引的谓词 `country = 'US'`。

集合用 **bitmap** 存最省内存（每个 record id 一位），也可用 hash set 或 Bloom filter（Bloom filter 有假阳性，需回表复核）。求交比求并更常见，因为 `AND` 谓词更常见。

### 5.8 万圣节问题的推导

设 `UPDATE employees SET salary = salary * 1.1 WHERE dept = 'CS'`，`salary` 上有 B+ 树索引（或者更新导致记录在堆中移动）：

1. 扫描器沿索引/堆顺序遍历。
2. 某条记录被更新后，物理位置发生变化，**移到了扫描器尚未访问的位置**。
3. 扫描器继续前进，又遇到这条记录，于是再乘一次 1.1。

结果同一条记录被加了两次薪。解法是让扫描器**记住已修改的 record id**（或记录已访问的物理位置），再次遇到时跳过。

### 5.9 表达式求值的优化

- **常量折叠（constant folding）**：编译期把 `1 + 2` 算成 `3`。
- **公共子表达式消除（common subexpression elimination）**：`(a+b)*c + (a+b)*d` 只算一次 `a+b`。
- **JIT**：把表达式树编译成机器码，消除树遍历与虚函数开销（Postgres、SQL Server、HyPer 都有实现）。
- **向量化求值**：一次对一批值求同一个表达式，便于 SIMD。

## 6. 代码示例

### 6.1 官方课程代码

**（1）迭代器模型的 `Next` 伪代码**——`90-原始PDF/15-445/notes/13-queryexecution1.pdf` 第 1–2 页，Figure 1 "Iterator Model Example – Pseudo code of the different Next functions"。讲义用三个算子（`SeqScan`、`Filter`、`Projection`）演示父算子如何循环调用子算子的 `Next()`，直到子算子返回空。

**（2）物化模型的 `Output`**——同文件第 2 页 Figure 2：每个算子一次返回整个结果集，父算子拿到完整输入后再做自己的处理。

**（3）向量化模型的批处理**——同文件第 3 页 Figure 3：`Next()` 返回一个 batch，父算子对整批求值。

**（4）区图示例**——同文件第 5 页 Figure 4 "Zone Map Example"：每页每列存预计算聚合，谓词与 `[min, max]` 无交集则跳过整页。

**（5）索引扫描与多索引扫描**——同文件第 6 页 Figure 5、Figure 6：100 行表、`age` 与 `department` 两个索引，演示选择率对索引选择的影响，以及多索引求交后再应用其余谓词。

**（6）表达式树**——同文件第 7 页 Figure 7 "Expression Evaluation Example"：把 `WHERE` 子句画成树，叶子是列引用/常量，内部节点是谓词与算术运算。

**（7）三种处理模型的总览**——`90-原始PDF/15-445/slides/13-queryexecution1.pdf` 第 7–9 页（Processing Models）、第 10–27 页（Iterator Model，含 `Next()`/`Open()`/`Close()`）、第 28–38 页（Materialization Model）、第 39–48 页（Vectorization Model）。

### 6.2 Agent 自行编写的教学示例

> 以下代码**非官方，仅用于说明概念**，不是 BusTub 的真实接口。

用现代 C++ 写一个最小迭代器模型（示意）：

```cpp
// 非官方示例：仅示意 Next()/Open()/Close() 的控制流
class Operator {
 public:
  virtual ~Operator() = default;
  virtual void Open() = 0;                       // 初始化游标 / 申请资源
  virtual bool Next(Tuple *out) = 0;             // 返回 false 表示输入耗尽
  virtual void Close() = 0;                      // 释放资源
};

class Filter : public Operator {
 public:
  Filter(std::unique_ptr<Operator> child, Predicate pred)
      : child_(std::move(child)), pred_(std::move(pred)) {}

  void Open() override { child_->Open(); }
  bool Next(Tuple *out) override {
    Tuple t;
    while (child_->Next(&t)) {          // 父算子驱动子算子
      if (pred_.Evaluate(t)) { *out = t; return true; }
    }
    return false;                        // 子算子耗尽
  }
  void Close() override { child_->Close(); }

 private:
  std::unique_ptr<Operator> child_;      // 独占所有权，符合 RAII
  Predicate pred_;
};
```

向量化版本只需把 `Next(Tuple*)` 换成 `Next(std::span<Tuple> batch)`，一次返回一批：

```cpp
// 非官方示例：向量化接口示意
class VectorizedOperator {
 public:
  virtual void Open() = 0;
  // 返回本批实际产出的行数，0 表示输入耗尽
  virtual size_t Next(std::span<Tuple> batch) = 0;
  virtual void Close() = 0;
};
```

区图跳页的示意（非官方）：

```cpp
// 非官方示例：用区图跳过不可能命中的页
struct ZoneMapEntry { int32_t min_age; int32_t max_age; };

bool PageCanMatch(const ZoneMapEntry &zm, int32_t lo, int32_t hi) {
  // 页内 [min,max] 与查询区间 [lo,hi] 无交集 → 整页跳过
  return !(zm.max_age < lo || zm.min_age > hi);
}
```

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| 迭代器模型 | 向量化模型 | 前者每次 `Next()` 返回 **1 个**元组，后者返回 **一批**；前者适合 OLTP，后者适合 OLAP |
| 物化模型 | 流水线中断算子 | 物化是**整个执行模型**（每算子一次处理全部输入）；pipeline breaker 是**单个算子**的性质（连接/排序必须等全部输入） |
| Pull（拉） | Push（推） | 谁掌握循环：父算子循环子算子 = pull；子算子把元组推给父算子 = push；结果集相同 |
| 区图（zone map） | 近似查询（approximate query） | 区图**无损**，只跳过不可能命中的页；近似查询**有损**，用样本估算 |
| 索引扫描 | 多索引扫描 | 前者用**一个**索引；后者用**多个**索引求 record id 集合的交/并 |
| 万圣节问题 | 幻读（phantom read） | 万圣节问题是**更新导致扫描器重复访问同一条记录**；幻读是**同一范围查询两次返回不同行集**（并发问题） |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Slides | `90-原始PDF/15-445/slides/13-queryexecution1.pdf` | 135 | 4–5（查询计划与流水线 / pipeline breaker）、7–9（三种处理模型总览）、10–27（迭代器模型）、28–38（物化模型）、39–48（向量化模型）、49–65（pull vs push）、68–88（顺序扫描、区图、索引扫描、多索引扫描）、89–107（修改查询与万圣节问题）、108–133（表达式求值、常量折叠、公共子表达式消除）、134（结论） |
| Notes | `90-原始PDF/15-445/notes/13-queryexecution1.pdf` | 7 | 第 1–2 页 Figure 1 迭代器伪代码、第 2 页 Figure 2 物化模型、第 3 页 Figure 3 向量化、第 5 页 Figure 4 区图、第 6 页 Figure 5/6 索引与多索引扫描、第 7 页 Figure 7 表达式树；第 4–5 页顺序扫描优化清单 |

原始 URL：

- Slides：`https://15445.courses.cs.cmu.edu/fall2026/slides/13-queryexecution1.pdf`
- Notes：`https://15445.courses.cs.cmu.edu/fall2026/notes/13-queryexecution1.pdf`

> 待核实：slides 第 2 页页眉印的是 "CMU DATABASE SYSTEMS (SPRING 2026)"，与本学期（Fall 2026）不符，疑为模板未更新；正文内容与本讲一致，以课程编号 #14 / 文件 `13-queryexecution1.pdf` 为准。

> 待核实：讲义第 68 页起把顺序扫描的各个优化点分散在多页动画中，各优化的完整清单以 notes 第 4–5 页为准；具体页码对应关系建议人工核对 PDF 后再引用。

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内，本讲内容对应 2025 年第 13 讲）

- 标题：Query Execution I（2025 年第 13 讲）
- URL：`https://www.youtube.com/watch?v=E-UUd6cB57w&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 年份：2025
- 时间戳：未核实，故不标注。

说明：FAQ Q11 明确 Fall 2026 的录像只对 CMU 学生开放，非 CMU 学习者应观看 Fall 2025 的公开视频。两版讲义顺序与细节可能略有差异（2026 版把并行执行单列到第 15 讲），请以 F26 的 slides/notes 为准。

## 10. 本节复习

- 能对一条带 `JOIN` + `ORDER BY` 的 SQL 画出计划 DAG，并标出所有 pipeline breaker。
- 能说出三种处理模型各自「父算子调用子算子多少次」，并解释向量化为什么在 OLAP 上更快。
- 能解释 pull 与 push 的差别，并各举一个真实系统（如 Postgres 用 pull、部分列存引擎用 push）。
- 能默写顺序扫描的至少 6 条优化，并区分哪条是有损、哪条是无损。
- 能解释区图为什么可以整页跳过而不影响正确性。
- 能针对给定谓词组合，判断该用哪个索引、是否该用多索引扫描。
- 能复述万圣节问题的触发条件与两种解法。
- 能画出 `WHERE a > 10 AND b = 'x'` 的表达式树。

## 11. 自我检查

**Q1.** 一条查询计划里有哈希连接和 `ORDER BY`，问：这条计划至少被切成几段流水线？如果哈希连接的两侧都很大，段数会变吗？

<details><summary>参考答案</summary>

至少 **3 段**：`ORDER BY` 是 pipeline breaker（要收完所有输入才能排序输出），哈希连接也是（build 侧要读完才能 probe）。典型切分是：段 1 构建哈希表 → 段 2 probe 产出连接结果 → 段 3 排序后输出。

段数**不会因为两侧变大而改变**，但每段内部会更容易 spill 到磁盘：哈希表放不下会分区落盘（grace hash join），排序放不下会外部归并排序。流水线的**段数由算子语义决定**，**段内的内存行为由数据量决定**——这是两个独立的维度。

</details>

**Q2.** 为什么向量化模型能把「虚函数调用开销」摊薄，却不能自动让所有查询变快？

<details><summary>参考答案</summary>

摊薄的是**每元组一次的函数调用与分支**：批大小 B 时，调用次数从 N 降到 N/B，B = 1024 时调用开销几乎消失，且批内数据驻留缓存、可向量化。

它不能自动变快的原因有三：

1. **OLTP 点查**每次只返回 1–2 行，凑不满一批，批处理反而增加延迟与内存拷贝。
2. 若算子是**选择率极高**的过滤，批内大部分行被丢弃，向量化的收益被浪费。
3. 若瓶颈在 **I/O**（随机读、缓冲池缺失）而非 CPU，减少函数调用对总时间影响很小。

所以向量化适合「大扫描 + 计算密集」的 OLAP 场景，不是万能加速器。

</details>

**Q3.** 表在 `age` 和 `city` 上各有一个索引。查询 `WHERE age > 18 AND city = 'Beijing'`，已知 `age > 18` 命中 90% 的行、`city = 'Beijing'` 命中 0.1% 的行。应该用哪个索引？能否用多索引扫描？

<details><summary>参考答案</summary>

应使用 **`city` 索引**。索引扫描代价 ≈ 索引查找 + 命中行数 × 回表代价，`city` 只命中 0.1% 的行，回表次数极少；`age > 18` 命中 90%，走索引几乎等于全表扫描外加随机 I/O，比顺序扫描更差（优化器通常会直接选顺序扫描）。

**不建议多索引扫描**：多索引扫描要先分别求出两个 record id 集合再求交，`age > 18` 的集合几乎等于全表，求交的收益完全被构造这个巨大集合的开销吃掉。多索引扫描只在**每个谓词都有高选择性索引**时才有意义。

</details>

**Q4.** 执行 `UPDATE employees SET salary = salary * 1.1 WHERE dept = 'CS'` 时，为什么可能给某些员工加两次薪？如果 `salary` 上没有索引，问题还会出现吗？

<details><summary>参考答案</summary>

当更新**改变了元组的物理位置**时会出现：例如 `salary` 上有索引，更新索引键使记录在索引/堆中移动到扫描器尚未访问的位置，扫描器稍后又访问到它，于是再更新一次——这就是万圣节问题。

如果 `salary` 上没有索引、且更新是**定长原地更新**（元组不移动、页不重组），更新不会改变记录的物理位置，扫描器不会重复访问，问题不出现。但只要更新可能导致记录移动（变长字段变长、页分裂、聚簇索引重排），就必须用「记录已修改 record id」的方式防护。

</details>

**Q5.** 区图（zone map）与稀疏索引（sparse index）都在「跳过数据」，它们的区别是什么？

<details><summary>参考答案</summary>

- **区图**存的是**每页每列的聚合统计**（min/max/sum/count），粒度是「页 × 列」，用于跳过**整页**；它不要求数据有序，也不指向任何具体记录。
- **稀疏索引**存的是「某个键值 → 第一條记录的页/偏移」的映射，**要求数据按该键有序**，粒度是「键区间 → 页」，用于**定位**而不是仅仅跳过。

换言之：区图是**统计信息**，靠「区间无交集」做否定判断；稀疏索引是**导航结构**，靠「有序性」做定位。区图对无序数据也有效，稀疏索引对无序数据完全无效。

</details>

## 12. 进一步学习

- 上一讲：[[15-445-13-Joins-Algorithms]] —— 连接算法是执行层最重要的算子，本讲的流水线切分主要由 join 决定。
- 下一讲：[[15-445-15-Query-Execution-II]] —— 并行执行：进程/线程模型、算子内并行、exchange 算子、SIMD 与 I/O 并行。
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：教材 *Database System Concepts*（第 7 版）第 15 章「Query Processing」；Goetz Graefe 的 "Volcano—An Extensible and Parallel Query Evaluation System"（1994）是迭代器模型的经典文献；"Query Evaluation Techniques for Large Databases"（1993）系统总结了物化与流水线的取舍。
- 动手建议：在 PostgreSQL 里对同一张表分别执行 `SELECT * FROM t LIMIT 10` 与 `SELECT * FROM t ORDER BY x LIMIT 10`，用 `EXPLAIN (ANALYZE, BUFFERS)` 观察前者几乎瞬时返回（流水线）、后者要先排完（pipeline breaker）；再对比 `SELECT count(*) FROM t WHERE x > 100` 在有无 BRIN 索引（Postgres 的区图式索引）下的差异。
