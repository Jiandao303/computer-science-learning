---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: L15
topic: Query Execution II
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 数据库
  - 并行执行
  - 进程模型
  - exchange 算子
  - SIMD
---

# 15-445 L15：查询执行 II（Query Execution II）

> 上一讲解决「单个 worker 怎么跑一条查询」，这一讲解决「怎么让几十个核一起跑」。核心问题只有三个：**用什么执行模型**（进程 / 线程 / 嵌入式）、**并行度加在哪里**（算子间 / 算子内 / 算子重叠）、**并行的粒度是什么**（数据并行 SIMD / I/O 并行 / 分区）。

## 1. 本节学习目标

学完本讲，你应该能够：

1. 说清**并行（parallel）**与**分布式（distributed）**在「资源距离、通信代价、故障假设」三方面的差别。
2. 比较**每 worker 一进程（process per DBMS worker）**、**每 worker 一线程（thread per DBMS worker）**、**嵌入式（embedded DBMS）**三种执行模型的调度权、崩溃隔离与实现复杂度。
3. 解释 **inter-query parallelism（查询间并行）** 与 **intra-query parallelism（查询内并行）** 各自优化的指标（吞吐 vs 延迟）。
4. 画出 **intra-operator（水平）并行**的计划，并说明 **exchange 算子**的三种类型（Gather / Distribute / Repartition）分别做什么。
5. 说明 **inter-operator（垂直）并行** 与 **bushy parallelism（混合并行）** 的适用场景与局限。
6. 解释 **数据并行**：SIMD 向量寄存器、范围谓词如何向量化、**选择向量（selection vector）**如何表示过滤结果。
7. 区分 **多磁盘并行（RAID）** 与 **数据库分区（database partitioning）** 两种 I/O 并行手段，并说明 DBMS 是否感知。

## 2. 前置知识

- **执行模型与流水线**：迭代器 / 物化 / 向量化、pipeline breaker，见 [[15-445-14-Query-Execution-I]]。
- **连接算法**：哈希连接的 build/probe 两阶段，并行 grace hash join 的分区思想，见 [[15-445-13-Joins-Algorithms]]。
- **缓冲池与磁盘调度**：buffer pool 的并发访问、预取，见 [[15-445-04-Memory-Management]]。
- **闩锁（latch）**：并发数据结构的基本保护手段，见 [[15-445-10-Index-Concurrency-Control]]。
- **C++ 提醒**：本课程项目用 **C++17** 编写、遵循 **Google C++ Style** 并用 clang-format 格式化；并行执行涉及 `std::thread`、`std::atomic`、`std::mutex`、`std::condition_variable`，请先掌握 RAII 锁（`std::lock_guard` / `std::unique_lock`）与内存序的基本概念。

## 3. 核心概念

### 3.1 Parallel vs Distributed（并行 vs 分布式）

**并行**：资源物理相邻（同一台机器、同一个机架），通过高速互连通信，通信廉价且（通常）可靠。**分布式**：资源跨机架、跨数据中心，通过公网通信，代价高且**故障不可忽略**。两者的关键区别不是「几台机器」，而是**通信代价与故障模型**。

### 3.2 Process per DBMS Worker（每 worker 一进程）

每个 worker 是一个独立 OS 进程，由**操作系统调度**，进程间通过共享内存或消息传递通信。优点是单进程崩溃不会拖垮整个 DBMS；缺点是依赖 OS 调度削弱了 DBMS 的控制力，且共享内存/消息传递有额外开销。代表系统：IBM DB2、PostgreSQL、Oracle。

### 3.3 Thread per DBMS Worker（每 worker 一线程）

单个进程内多线程，由 **DBMS 自己调度**，上下文切换开销小、共享数据无需序列化。缺点是**一个线程崩溃可能杀死整个进程**。代表系统：SQL Server、MySQL、DB2（也支持）。

### 3.4 Embedded DBMS（嵌入式数据库）

数据库与应用运行在**同一地址空间**，由**应用**负责调度。代表系统：DuckDB、SQLite、RocksDB。省去进程间通信，适合单机分析型负载与嵌入式场景。

### 3.5 Scheduling（调度）

DBMS 要决定：用多少个 task / 多少个核、把 task 放到哪些核上、每个 task 的输出放到哪里。DBMS 通常比 OS **更懂查询语义**（知道哪个 task 更关键、哪段数据在缓存里），所以倾向自己调度。

### 3.6 Inter-Query Parallelism（查询间并行）

同时执行多条查询，**提高吞吐（throughput）**、降低平均延迟。只读查询之间协调很少；并发写则冲突复杂（见 [[15-445-18-Concurrency-Control-Theory]]）。

### 3.7 Intra-Query Parallelism（查询内并行）

把**一条查询**拆给多个 worker 一起做，**降低长查询的延迟（latency）**。三种拆法：算子内（水平）、算子间（垂直）、混合（bushy）。

### 3.8 Intra-Operator Parallelism（算子内并行 / 水平并行）

把算子切成多个 **fragment（片段）**，每个 fragment 处理**不相交的数据子集**，fragment 之间插入 **exchange 算子**做数据重分布。也叫 **horizontal parallelism**。

### 3.9 Exchange Operator（交换算子）

并行计划中的「数据搬运工」，有三种类型：

- **Gather**：多个 worker 的输出合并成**一条**数据流（最常见的收尾）。
- **Distribute**：把**一条**数据流拆成多条，分给多个 worker。
- **Repartition**：多条输入流按某个键**重新分区**成多条输出流（shuffle）。

### 3.10 Inter-Operator Parallelism（算子间并行 / 垂直并行）

不同算子**同时运行**，上游产出的元组立刻被下游消费，即 **pipelined parallelism**。流处理系统常用。局限：若某算子极慢（如 build 哈希表），整体仍被它拖住；不适合需要全量输入才能开始的算子。

### 3.11 Bushy Parallelism（混合并行）

同时使用水平与垂直并行：把一个 4-way join 切成 4 个 fragment，fragment 之间既有流水又有数据分区。它是实际系统的默认形态。

### 3.12 Data Parallelism（数据并行）

在**单个指令**层面同时处理多个数据：利用 CPU 的**向量寄存器（vector registers）**执行 SIMD 指令（AVX2 一次 8 个 int32，AVX-512 一次 16 个）。适合「同一运算作用于大量值」的场景，如谓词求值、聚合。

### 3.13 Selection Vector（选择向量）

用一个**下标数组**表示「批中哪些行通过了谓词」，而不是真的把通过的行拷贝出来。后续算子只遍历这些下标。省内存、省拷贝，是向量化执行引擎的标准做法。

### 3.14 I/O Parallelism（I/O 并行）

两种手段：**多磁盘并行（multi-disk parallelism）**——用 RAID 或存储阵列把 I/O 摊到多块盘上，对 DBMS **透明**；**数据库分区（database partitioning）**——把逻辑表切成不相交的物理段（按范围 / 哈希 / 轮转）放到不同磁盘，**由 DBMS 自己管理**。

## 4. 通俗理解

把一条查询想成**搬家**。

- **查询间并行** = 同时搬 10 户人家，每户派一辆车。总的搬家量（吞吐）上去了，但每户的完成时间没变。
- **算子内并行** = 一户人家请 10 个工人，每人负责一个房间（数据子集）。**这一户的完成时间**缩短了，但需要有人在中间协调「谁搬完了把东西交给谁」——这就是 exchange 算子。
- **算子间并行** = 流水线作业：一个人专门打包、一个人专门搬下楼、一个人专门装车。三个人同时在干活，但最慢的那一环决定整体速度。
- **bushy** = 既有流水线，每个环节又有多个人——现实中的搬家公司就是这样。

**进程模型**像「每户人家单独雇一个外包队」：互不干扰，一家出事不影响别家，但调度靠外包公司（OS），协调成本高。**线程模型**像「一个公司自己的员工」：配合默契、切换快，但一个人受伤可能整个队停工。**嵌入式**像「自己家人搬家」：不用沟通成本，但只有自己这几双手。

## 5. 原理与推导

### 5.1 并行 vs 分布式的判据

| 维度 | 并行 | 分布式 |
|---|---|---|
| 物理距离 | 同机 / 同机架 | 跨机架 / 跨数据中心 |
| 互连 | 高速总线 / 专用网络 | 公网 |
| 通信代价 | 低 | 高（毫秒级 RTT） |
| 故障假设 | 通常假设不发生 | **必须**假设随时发生 |
| 典型难点 | 锁竞争、缓存一致性 | 一致性协议、部分失败、2PC |

关键推论：**分布式系统必须处理部分失败（partial failure）**，而并行系统通常不需要；这就是为什么分布式事务要引入 2PC、Paxos/Raft 等协议，而单机并行不需要。

### 5.2 三种执行模型的取舍推导

| 维度 | Process per Worker | Thread per Worker | Embedded |
|---|---|---|---|
| 调度者 | OS | DBMS | 应用 |
| 崩溃隔离 | 好（进程级） | 差（进程级共享） | 无（同应用） |
| 上下文切换开销 | 高 | 低 | 最低 |
| 共享数据方式 | 共享内存 / 消息传递 | 直接共享内存 | 直接访问 |
| 实现复杂度 | 中 | 低 | 低 |
| 代表系统 | Postgres、Oracle、DB2 | SQL Server、MySQL | DuckDB、SQLite、RocksDB |

推导：进程模型的隔离性最好但调度权在 OS 手里，DBMS 无法精细控制「哪个查询优先」；线程模型把调度权收回 DBMS，但要求 DBMS 自己做线程安全与崩溃恢复。现代云原生 DBMS 常采用「**进程池 + 线程池混合**」：进程提供隔离，进程内多线程提供并行。

### 5.3 算子内并行的计划改写

原始计划：

```
        Join
       /    \
   Scan(A) Scan(B)
```

改成 2-way 水平并行后：

```
            Exchange(Gather)
                  |
                Join
              /      \
   Exchange(Distribute)  Exchange(Distribute)
        |                      |
    Scan(A) #1             Scan(B) #1
    Scan(A) #2             Scan(B) #2
```

每个 `Scan` 处理表的一半页；`Distribute` 把每个 worker 的输出汇总后分给下游的多个 join worker；最后 `Gather` 把多个 join worker 的结果合成一条流返回客户端。

推导要点：

1. **数据子集必须不相交**，否则结果重复（对 `SELECT` 无所谓但会浪费，对 `COUNT` 会算错）。
2. **exchange 的位置决定网络/内存开销**：Gather 之前的数据要跨 worker 传输，越早 aggregate 越省。
3. **分区键的选择决定是否需要 repartition**：如果 join 键恰好等于扫描的分区键，可以直接 **co-located join**，省掉一次 shuffle。

### 5.4 并行 grace hash join

```
Build 侧：Partition 1..N（按 hash(key) % N）
Probe 侧：Partition 1..N（同一 hash 函数）
Worker i：用 Build 的 Partition i 建哈希表，probe Probe 的 Partition i
```

每个 worker 只处理一对分区，互不干扰；`N` 通常取 CPU 核数的倍数。这就是 **Repartition** exchange 的典型应用。若某个分区过大（数据倾斜），会成为长尾——实践中用 **skew handling**（把大分区再切分）缓解。

### 5.5 SIMD 与选择向量

标量做法：

```cpp
for (size_t i = 0; i < n; i++)
  if (age[i] > 18) out.push_back(i);
```

SIMD 做法：一次读入 8 个 `age`，用一条比较指令得到 8 位掩码，再用 `pext` / `compress` 类指令把通过的下标压紧。理论加速比上限是向量宽度（8 或 16），实际受内存带宽与数据分布限制，通常 2–4 倍。

**选择向量**的意义：过滤算子不拷贝数据，只输出下标数组 `[3, 7, 12, ...]`；下游算子按这个数组去原数组取值。这样一次过滤可以被多个下游算子复用，且保持数据在缓存里。

### 5.6 I/O 并行的两条路

- **RAID / 存储阵列**：把一次逻辑读摊到多块盘，DBMS 完全不知道底层有几块盘。优点是透明、无需改代码；缺点是 DBMS 无法利用「数据在哪块盘」的信息做调度。
- **数据库分区**：DBMS 自己按范围/哈希/轮转把表切段，知道每段在哪块盘，可以针对分区做裁剪（partition pruning）与并行扫描。代价是要维护分区元数据，且分区键选得不好会导致倾斜。

## 6. 代码示例

### 6.1 官方课程代码

**（1）每 worker 一进程模型**——`90-原始PDF/15-445/notes/14-queryexecution2.pdf` 第 1–2 页，Figure 1 "Process per Worker Model"：客户端连接被分配到独立进程，进程之间通过共享内存或消息传递交换数据。

**（2）每 worker 一线程模型**——同文件第 2–3 页，Figure 2 "Thread per Worker Model"：单进程内多个线程，DBMS 自己维护线程池与调度。

**（3）嵌入式 DBMS 调度**——同文件第 3 页，Figure 3 "Embedded DBMS Scheduling"：应用线程直接调用 DBMS 的函数，无跨进程通信。

**（4）算子内并行计划**——同文件第 4 页，Figure 4 "Intra-Operator Parallelism"：给出一个 `SELECT` 的并行计划，展示 fragment 与 exchange 的插入位置。

**（5）算子间并行与 bushy**——同文件第 5 页，Figure 5 "Inter-operator Parallelism"（流水线重叠）、Figure 6 "Bushy Parallelism"（4-way JOIN 切成多个 fragment）。

**（6）三种处理模型的并行含义**——`90-原始PDF/15-445/slides/14-queryexecution2.pdf` 第 8–21 页（进程/线程/嵌入式）、第 22–23 页（调度与多线程架构优点）、第 24–29 页（查询间 / 查询内并行）、第 30–53 页（算子内并行与 exchange 三型）、第 54–59 页（算子间与 bushy）。

**（7）SIMD 与选择向量**——同 slides 第 68–80 页（SIMD 的 `X + Y = Z` 例子）、第 81–97 页（范围谓词向量化）、第 98–103 页（Selection Vectors）。

### 6.2 Agent 自行编写的教学示例

> 以下代码**非官方，仅用于说明概念**。

用线程池实现「每个 worker 处理不相交页区间」的顺序扫描（示意）：

```cpp
// 非官方示例：按页区间切分，worker 之间不重叠
void ParallelScan(Table *table, size_t num_workers,
                  const std::function<void(Tuple &)> &emit) {
  const size_t num_pages = table->GetPageCount();
  const size_t per_worker = (num_pages + num_workers - 1) / num_workers;

  std::vector<std::thread> threads;
  std::mutex emit_latch;                     // 保护共享输出
  for (size_t w = 0; w < num_workers; w++) {
    const size_t begin = w * per_worker;
    const size_t end = std::min(begin + per_worker, num_pages);
    threads.emplace_back([=, &emit, &emit_latch] {
      for (size_t p = begin; p < end; p++) {
        for (Tuple &t : table->GetPage(p)->GetTuples()) {
          std::lock_guard<std::mutex> guard(emit_latch);  // RAII
          emit(t);
        }
      }
    });
  }
  for (auto &t : threads) t.join();          // 必须 join，否则 UB
}
```

Gather / Distribute / Repartition 的接口示意：

```cpp
// 非官方示例：exchange 算子三型
class ExchangeOperator {
 public:
  enum class Type { kGather, kDistribute, kRepartition };
  // Gather：多个 child 的结果合成一条流
  // Distribute：一条流按轮转/哈希分给多个 consumer
  // Repartition：按 key 的 hash 重新分区，保证同 key 到同一 worker
};
```

选择向量的用法（非官方）：

```cpp
// 非官方示例：过滤只产出下标，不拷贝元组
void FilterWithSelectionVector(const std::vector<int32_t> &ages,
                               std::vector<uint32_t> *sel) {
  sel->clear();
  for (uint32_t i = 0; i < ages.size(); i++)
    if (ages[i] > 18) sel->push_back(i);   // 只记下标
}
```

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| 并行 | 分布式 | 前者资源邻近、通信廉价、故障可忽略；后者跨机房、通信昂贵、**必须处理部分失败** |
| Inter-query 并行 | Intra-query 并行 | 前者同时跑多条查询，优化**吞吐**；后者拆一条查询，优化**延迟** |
| Intra-operator（水平） | Inter-operator（垂直） | 前者把**一个算子**的数据切给多个 worker；后者让**不同算子**同时运行（流水线） |
| Gather | Repartition | Gather 是 **N → 1** 合并；Repartition 是 **N → N** 按键重分布（shuffle） |
| 多磁盘并行（RAID） | 数据库分区 | 前者对 DBMS **透明**，由 OS/硬件负责；后者由 **DBMS 管理**，可做分区裁剪 |
| 数据并行（SIMD） | 算子内并行 | SIMD 在**一条指令**内处理多个值（CPU 级）；算子内并行是**多个 worker 线程**处理不同数据子集 |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Slides | `90-原始PDF/15-445/slides/14-queryexecution2.pdf` | 126 | 5–6（并行 vs 分布式）、8–21（三种执行模型）、22–23（调度）、24–29（查询间 / 查询内并行）、30–53（算子内并行与 exchange）、54–59（算子间与 bushy）、68–103（数据并行、SIMD、选择向量）、106–117（I/O 并行与数据库分区）、118（结论）、120–126（Project #3 说明） |
| Notes | `90-原始PDF/15-445/notes/14-queryexecution2.pdf` | 6 | 第 1–2 页 Figure 1 进程模型、第 2–3 页 Figure 2 线程模型、第 3 页 Figure 3 嵌入式、第 4 页 Figure 4 算子内并行、第 5 页 Figure 5/6 算子间与 bushy；第 1 页并行 vs 分布式定义、第 6 页 exchange 三型与 I/O 并行两法 |

原始 URL：

- Slides：`https://15445.courses.cs.cmu.edu/fall2026/slides/14-queryexecution2.pdf`
- Notes：`https://15445.courses.cs.cmu.edu/fall2026/notes/14-queryexecution2.pdf`

> 待核实：slides 第 120–126 页是 Project #3 的说明页（实现 query operators、leaderboard、只改允许的文件），具体任务要求以官方 project3 页面为准，本笔记不作为规格依据。

> 待核实：slides 文本抽取时出现若干乱码（如 "TODAY��S AGENDA"、"Type #1 �C Gather"），系 PDF 文本层编码问题，正文按语义还原为 "TODAY'S AGENDA"、"Type #1 – Gather"。

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内，本讲内容对应 2025 年第 14 讲）

- 标题：Query Execution II（2025 年第 14 讲）
- URL：`https://www.youtube.com/watch?v=Kzf1hGjtZOU&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 年份：2025
- 时间戳：未核实，故不标注。

说明：FAQ Q11 明确 Fall 2026 的录像只对 CMU 学生开放，非 CMU 学习者应观看 Fall 2025 的公开视频。2026 版把「并行执行」独立成第 15 讲，2025 版也是第 14 讲，讲次错位一格。

## 10. 本节复习

- 能说出并行与分布式在通信代价、故障模型上的两个本质差别。
- 能比较三种执行模型的调度权归属与崩溃隔离能力，并各举两个代表系统。
- 能解释为什么「查询间并行提高吞吐、查询内并行降低延迟」。
- 能画出带 Gather / Distribute / Repartition 的并行计划，并说明每个 exchange 的作用。
- 能描述并行 grace hash join 的分区过程，以及数据倾斜的后果。
- 能说出 SIMD 的收益上限与限制（内存带宽、数据分布）。
- 能解释选择向量为什么不拷贝数据，以及它对下游算子的好处。
- 能区分 RAID 与数据库分区在「DBMS 是否感知」上的差异。

## 11. 自我检查

**Q1.** 一台 64 核服务器上跑一条分析查询，用「每 worker 一进程」还是「每 worker 一线程」？如果这个查询要跑 10 分钟且中间可能因为 bug 崩溃，选择会变吗？

<details><summary>参考答案</summary>

**默认选线程模型**：64 核意味着 64 个 worker，进程模型的上下文切换与共享内存开销在这个规模下很显著，而线程模型让 DBMS 自己控制调度、共享哈希表等中间结构无需序列化，通常快 10–30%。

**如果查询长且可能崩溃，选择会倾向于进程模型或混合模型**：线程模型下一个 worker 段错误会让整个进程（连同其他 63 个 worker 的工作）一起丢失；进程模型只丢失一个进程，其余查询不受影响。生产系统常用「进程池 + 进程内线程池」：进程提供故障隔离，线程提供并行效率。此外长查询还应配合 checkpoint / 中间结果落盘，避免重跑全部工作。

</details>

**Q2.** 一个 4-way join 的查询在 8 核机器上跑得很慢，`EXPLAIN` 显示只用了一个 worker。可能的原因是什么？如何改？

<details><summary>参考答案</summary>

可能原因：

1. **优化器判断并行不划算**：表太小、启动 worker 的开销大于收益，或查询的选择率极高导致结果集很小。
2. **存在不可并行的算子**：某些聚合（如无分组的全局 `COUNT(DISTINCT)`）、窗口函数、递归 CTE 在部分系统中是单线程的。
3. **并行度配置为 1**：如 Postgres 的 `max_parallel_workers_per_gather = 0`，或 SQL Server 的 `MAXDOP = 1`。
4. **写操作或事务隔离限制**：某些系统对 `UPDATE`/`DELETE` 或可串行化隔离下的查询禁用并行。

改法：先确认配置（`SHOW max_parallel_workers_per_gather`），再检查计划里是否有 `Gather` 节点；若是代价判断问题，可降低 `parallel_setup_cost` / `parallel_tuple_cost` 强制并行后再观察；若是算子本身不可并行，改写查询（把 `COUNT(DISTINCT)` 拆成子查询分组计数）。

</details>

**Q3.** 并行 grace hash join 中，如果 join key 严重倾斜（某个 key 占 40% 的行），会发生什么？两种解法各是什么代价？

<details><summary>参考答案</summary>

**发生什么**：`hash(key) % N` 会把该 key 的所有行送到同一个分区，负责这个分区的 worker 要处理 40% 的数据，其余 worker 早早做完闲置——这就是**长尾（straggler）**，整体耗时接近单线程处理 40% 数据的时间，加速比大幅下降。

**解法一：skew-aware partitioning（倾斜感知分区）**。先采样统计各 key 的频次，对超大 key 单独建分区并让多个 worker 协同处理（每个 worker 处理该 key 的一部分 probe 行，共享一份 build 哈希表）。代价：需要额外的采样/统计阶段，实现复杂。

**解法二：广播小表（broadcast join）**。若倾斜侧是 build 侧且能放进内存，把 build 表完整复制给每个 worker，probe 侧任意分区都不需要 shuffle。代价：每个 worker 都要存一份 build 表，内存占用 ×N，只适合小 build 表。

实践中还会用「salting」：给热点 key 加随机后缀打散到多个分区，probe 时对同一 key 复制到所有后缀分区查询。

</details>

**Q4.** 为什么 `SELECT COUNT(*) FROM t` 在并行执行下容易算错？正确做法是什么？

<details><summary>参考答案</summary>

如果多个 worker **重复扫描了相同的页**（分区边界算错、或 exchange 把同一批数据分发给了多个下游），每个 worker 都会把自己看到的行数加进局部计数，最后汇总就会偏大。另一种常见错误是：`COUNT(*)` 的**部分聚合结果没有正确合并**（例如把各 worker 的 count 求了平均而不是求和）。

正确做法：① 保证每个 worker 的页区间**严格不相交且并集为全表**（`begin = w * per_worker`，`end = min(begin + per_worker, num_pages)`）；② 每个 worker 输出**局部 count**，最后由 Gather 侧的 `SUM` 合并；③ 用 `BUSTUB_ASSERT` 或测试校验「各 worker 处理行数之和 == 全表行数」。

</details>

**Q5.** 一台机器有 4 块 SSD，表有 1 亿行。用 RAID-0 和用「按主键范围分成 4 个分区」相比，哪种更适合「按主键范围扫描」的查询？为什么？

<details><summary>参考答案</summary>

**按主键范围分区更适合范围扫描**。原因：

- **RAID-0** 把每个逻辑块条带化到 4 块盘，一次范围扫描的 I/O 确实被摊到 4 块盘上，但 DBMS 不知道数据在物理上怎么分布，无法做**分区裁剪**——查询 `WHERE id BETWEEN 100 AND 200` 仍然要扫过所有盘上的对应区间。
- **按主键范围分区**让 DBMS 知道「id 100–200 只在分区 0」，可以直接只读一个分区（**partition pruning**），其余 3 块盘完全不动；同时 4 个分区可以并行扫描。

代价：分区后若查询**不按主键**过滤（如 `WHERE city = 'X'`），就要扫描所有分区，此时不如 RAID 的均匀条带。所以实践常两者叠加：先分区，再把每个分区放到 RAID 上。

</details>

## 12. 进一步学习

- 上一讲：[[15-445-14-Query-Execution-I]] —— 单 worker 的执行模型与访问路径，本讲在其上叠加并行维度。
- 下一讲：[[15-445-16-Query-Optimization-I]] —— 从「怎么执行」转向「怎么选计划」：等价变换、启发式优化、System R 的自底向上搜索。
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：教材 *Database System Concepts*（第 7 版）第 22 章「Parallel Databases」；Goetz Graefe 的 "Encapsulation of Parallelism in the Volcano Query Processing System"（1990）是 exchange 算子的经典文献。
- 动手建议：在 PostgreSQL 里对同一张大表分别设置 `SET max_parallel_workers_per_gather = 0` 与 `= 4`，用 `EXPLAIN (ANALYZE)` 对比 `Gather` 节点前后的耗时；再用 `EXPLAIN (ANALYZE, VERBOSE)` 观察 workers planned / launched 的差异。
