---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: P0
topic: Project 0 - C++ Primer
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 项目
  - C++
  - 哈希表
  - 并发
---

# 15-445 Project #0：C++ 入门（C++ Primer / Robin Hood Hash Set）

> 依据项目页公开说明整理，具体任务以官方 project0 页为准：`https://15445.courses.cs.cmu.edu/fall2026/project0/`
>
> **Fall 2026 的实际任务**：实现一个**定容 Robin Hood 哈希集合（Robin Hood Hash Set）**——定容开放寻址 + 线性探测 + 罗宾汉交换 + 墓碑删除 + 分片并发。**不是**「读一遍 C++ 语法」的练习。
>
> 官方明确：**不计分，但必须拿到满分才能继续课程**；单人项目，**no groups, no coding agents**；Release Aug 24 2026，Due Sep 06 2026 11:59pm。

## 1. 本节学习目标

1. 掌握 C++ 的 **RAII** 与**所有权语义**：`std::unique_ptr` / `std::shared_ptr` 的适用场景，以及为什么数据库代码偏爱 `unique_ptr`。
2. 掌握**移动语义**：move constructor / move assignment 的正确实现，以及「移动后源对象仍处于有效但未指定状态」这一契约。
3. 理解**模板**与**策略注入**：`RobinHoodHashSet<Key, Hasher, KeyEqual>` 如何用模板参数替换行为。
4. 掌握 **`const` 正确性**：哪些成员函数必须是 `const`，`mutable` 何时使用。
5. 理解**开放寻址哈希表**的插入/查找/删除算法，以及 Robin Hood 交换为什么能降低探测距离方差。
6. 理解**细粒度并发**：为什么禁止单把全局锁，分片锁（sharded locks）如何实现。
7. 掌握 **Google C++ Style** 的要点与 `clang-format` / `clang-tidy` 的使用。

## 2. 前置知识

- **C++ 基础**：类、构造函数/析构函数、运算符重载、模板初步。
- **C++11/14/17 特性**：`auto`、range-for、`std::move`、`std::forward`、`std::optional`、`std::string_view`、structured bindings、`if constexpr`。
- **并发基础**：`std::thread`、`std::mutex`、`std::lock_guard`、`std::atomic`。
- **哈希表理论**：哈希函数、冲突解决（链地址 vs 开放寻址）、负载因子。
- 课程相关：[[15-445-07-Hash-Tables]] —— 讲义里讲了哈希表在数据库中的角色（哈希连接、哈希索引），与本项目直接对应。

## 3. 核心概念

### 3.1 RAII（Resource Acquisition Is Initialization，资源获取即初始化）

C++ 的核心资源管理惯用法：**把资源的生命周期绑定到对象的生命周期**。构造函数获取资源，析构函数释放资源。这样即使中途 `throw`，栈展开也会调用析构函数，不会泄漏。

**在 P0 中**：桶数组用 `std::unique_ptr<Bucket[]>` 管理，而不是裸 `new[]` / `delete[]`。这样 move 时自动转移所有权，异常时自动释放。

### 3.2 `std::unique_ptr`（独占所有权智能指针）

表示**唯一所有权**：同一时刻只有一个 `unique_ptr` 拥有对象。**不可拷贝，只能移动**。开销与裸指针相同（零开销抽象）。

**在 P0 中**：桶数组、内部状态全部用 `unique_ptr`。移动构造时 `std::move` 转移，源对象变为 `nullptr`。

### 3.3 `std::shared_ptr`（共享所有权智能指针）

表示**共享所有权**：多个 `shared_ptr` 指向同一对象，内部有**引用计数**，最后一个析构时释放。开销：一次原子引用计数 + 一个控制块。

**在 P0 中**：**不需要** `shared_ptr`。哈希集合没有共享所有权的语义——用它反而是设计错误（会掩盖所有权问题）。

### 3.4 Move Semantics（移动语义）

C++11 引入：把资源从一个对象**转移**到另一个对象，而不是拷贝。通过**右值引用** `T&&` 与 `std::move` 触发。

**移动后的契约**：源对象处于「**有效但未指定（valid but unspecified）**」状态——可以安全析构、可以重新赋值，但**不能假设它的值**。

**P0 的官方要求更严格**：移动后 `Capacity() == 0`、`Size() == 0`，且仍可安全调用 `Clear()`。这是「有效但未指定」的一个**具体化**。

### 3.5 Template（模板）

C++ 的泛型机制。P0 的类模板签名（官方）：

```cpp
template <typename Key, typename Hasher = std::hash<Key>,
          typename KeyEqual = std::equal_to<Key>>
class RobinHoodHashSet;
```

三个参数：键类型、哈希函数、相等比较。用**策略注入**而非继承，是 C++ 标准库的惯用法（`std::unordered_set` 也是这样）。

### 3.6 Const Correctness（`const` 正确性）

**规则**：不修改对象状态的成员函数必须标 `const`。

**在 P0 中**：`Contains`、`Size`、`Capacity`、`BucketCount`、`LoadFactor`、`MaxProbeDistance`、`GetBucket` 全部是 `const` 成员函数。`Insert`、`Remove`、`Clear` 不是。

**为什么重要**：`const` 成员函数可以被 `const RobinHoodHashSet&` 调用。如果 `Contains` 不是 `const`，那么在 `const` 引用上就无法查找——这是 API 设计的硬伤。

### 3.7 Open Addressing（开放寻址）

所有元素都存放在**桶数组本身**里（不像链地址法那样用外部链表）。冲突时按某种**探测序列**（probing sequence）找下一个空桶。

**线性探测（linear probing）**：`slot = (hash(key) + i) % capacity`，`i = 0, 1, 2, ...`。缓存友好，但会产生**一次聚集（primary clustering）**。

### 3.8 Robin Hood Hashing（罗宾汉哈希）

线性探测的改进：插入时比较「探测距离（probe distance）」，**距离大的键可以抢占距离小的键的位置**，被抢占的键继续往后找。效果是**探测距离方差大幅降低**。

### 3.9 Tombstone（墓碑）

开放寻址中删除元素的标记。不能直接置空（会切断探测链，导致后面的元素找不到），所以标记为「已删除」。

### 3.10 Sharded Lock（分片锁）

把一把大锁拆成 N 把小锁，每把保护一部分数据（如按桶的下标取模）。不同分片的操作可以并行，从而提高吞吐。

## 4. 通俗理解

**RAII = 酒店的房卡**：你拿到房卡（构造）就拥有了房间；退房时把卡还回去（析构）。不管你是正常退房还是被赶出来（异常），房卡都会被回收。你**不需要手动记得**「我要去前台说一声」。

**`unique_ptr` vs `shared_ptr` = 独栋别墅 vs 合租公寓**：
- `unique_ptr`：房本上只有一个名字，要转手必须**过户**（move），不能同时写两个人。
- `shared_ptr`：合租，每人一份钥匙，最后一个人搬走时才退租（引用计数归零）。合租要维护「谁还在住」的账本（原子计数），成本更高。

**移动语义 = 搬家而不是复制房子**：拷贝一个 `vector` 是「再盖一栋一模一样的房子」；移动是「把家具搬过去，旧房子清空」。移动后旧房子还在（对象有效），但里面空了（`Capacity()==0`）。

**Robin Hood = 公交车上的座位**：
- 普通线性探测：先上车的人坐靠窗，后来的人一路往后走，走到最后的人站得最远。
- Robin Hood：如果新来的人已经走了 5 站还没座，而旁边坐着的人只走了 1 站就有座，那就**让座**——把「走了 1 站的人」赶到后面去。这样所有人的「辛苦程度」被拉平，**最长的那条队伍变短了**。

**Tombstone = 「此座已预留」的牌子**：有人下车了，但你不能直接把座位当成空座——因为后面的人还在按「这个座位曾经有人」的规则找座。所以放一个「已下车」的牌子，找座的人看到牌子会继续往后走，但新来的人可以坐这个座位。

**分片锁 = 超市的多个收银台**：一个收银台（全局锁）排长队；开 8 个收银台（8 把锁），每个顾客按「购物车编号 mod 8」去对应收银台，队伍短了 8 倍。

## 5. 原理与推导

### 5.1 为什么 P0 用哈希表而不是「语法练习」

见 [[00-项目总览]] 第 5.2 节。核心：哈希表同时覆盖**手动内存管理、移动语义、模板、`const` 正确性、异常安全、并发**六项技能，而这六项正是后续三个项目的地基。

### 5.2 Robin Hood 插入算法推导

**目标**：把 `(key, distance)` 放进表里，`distance` 是「从理想位置走了多远」。

**朴素线性探测**：

```
i = 0
while slot(hash + i) is occupied:
    if slot.key == key: return  (已存在)
    i += 1
place key at slot(hash + i)
```

问题：先插入的键占据理想位置，后插入的键被推得越来越远。若哈希分布不均，某些键的探测距离可达 O(n)。

**Robin Hood 的关键观察**：设当前槽位的「原住民」的探测距离为 `d_old`，新键当前的探测距离为 `d_new`。若 `d_old < d_new`，说明**原住民比新键更「轻松」**——把新键放这里、让原住民继续走，总体的「最大探测距离」会下降。

**算法**：

```
insert(key):
    if size + tombstones 达到阈值: rehash / 扩容
    d = 0
    cur = key
    loop:
        slot = bucket(hash(cur) + d)
        if slot is EMPTY or TOMBSTONE:
            slot = {cur, d, OCCUPIED}; size += 1; return true
        if slot.key == cur:
            return true                    # 重复插入，Size 不变
        if slot.distance < d:
            swap(cur, slot.key)            # 劫富济贫
            swap(d, slot.distance)
        d += 1
```

**正确性论证**：

1. **终止性**：每次循环 `d` 至少加 1；表未满时必存在空桶或墓碑 → 终止。表满且键不存在 → 返回 false。
2. **不变式**：循环中始终满足「`cur` 是一个尚未插入的键，`d` 是它当前的探测距离」。swap 后，原住民变成 `cur`，其探测距离 `d_old` 成为新的 `d`——仍然满足不变式。
3. **查找正确性**：Robin Hood 的查找与普通线性探测**完全相同**（一路往后扫，遇到 EMPTY 停止）。为什么？因为 swap 不改变「键在探测链上」这一事实——每个键的位置仍然在它的理想位置之后、且在某个空桶之前。**关键性质**：Robin Hood 保证「探测距离单调不减」——沿探测链往后走，每个槽位的 `distance` 不会变小。因此查找时若发现 `slot.distance < d`，说明目标键**不可能**在更后面（否则它的距离会 >= d），可以提前终止。

**这个「提前终止」优化**是 Robin Hood 相对普通线性探测的主要优势之一：

```
contains(key):
    d = 0
    loop:
        slot = bucket(hash(key) + d)
        if slot is EMPTY: return false
        if slot is OCCUPIED and slot.key == key: return true
        if slot is OCCUPIED and slot.distance < d: return false   # 提前终止
        d += 1
```

**注意**：官方 API 里 `MaxProbeDistance()` 只统计 **occupied** 桶。若查询不存在的键，返回 `Capacity()` 作为哨兵。

### 5.3 探测距离方差分析

**普通线性探测**：设负载因子 α，成功查找的平均探测次数 ≈ `(1 + 1/(1-α))/2`；**不成功**查找 ≈ `(1 + 1/(1-α)²)/2`。方差大——α=0.9 时不成功查找平均要 50 次。

**Robin Hood**：成功查找的平均探测次数**几乎不变**（约 1.5–2），但**方差大幅降低**——最长探测距离从 O(log n) 降到 O(log n) 的小常数倍。**最坏情况（tail latency）显著改善**。

**代价**：插入时的 swap 次数增加（每次插入平均 ~1 次 swap）。但 swap 是寄存器级别的操作，代价可忽略。

**为什么数据库关心 tail latency**：一个查询的响应时间由**最慢的那次查找**决定（木桶效应）。降低方差比降低均值更重要。

### 5.4 删除与墓碑

**为什么不能直接置空**：

```
表: [A, B, _, C]     假设 A、B、C 的哈希都映射到下标 0
删除 B → 置空: [A, _, _, C]
查找 C: 从 0 开始，看到下标 1 是空 → 返回 false  ✘ 但 C 明明在！
```

**墓碑方案**：

```
删除 B → 标记: [A, TOMB, _, C]
查找 C: 0=A, 1=TOMB(继续), 2=空(停止) → 找不到  ✘
```

**等等，还是找不到！** 因为下标 2 是空。所以墓碑的语义必须是「**继续探测，但可以插入**」：

```
contains(C): 0=A, 1=TOMB(继续), 2=EMPTY(停止) → false  ✘
```

**这里有个真实的坑**：如果 B 被删除后留下墓碑，C 在下标 3，那么从 0 到 3 的路径上必须**没有 EMPTY**。原始表 `[A, B, _, C]` 中间就有一个空位——这说明 C 的探测链本来就断了，C 根本插不进下标 3（它会在下标 2 停下）。

**修正后的例子**：`[A, B, C, _]`（A/B/C 哈希都在 0，线性探测依次占 0/1/2）。

```
删除 B → [A, TOMB, C, _]
contains(C): 0=A, 1=TOMB(继续), 2=C ✔
insert(D, hash=0): 0=A, 1=TOMB → 可以复用！插入 D 到下标 1
```

**关键规则**：

1. **查找**：遇到 TOMBSTONE **继续**，遇到 EMPTY **停止**。
2. **插入**：遇到 TOMBSTONE **可以复用**（但要注意：如果同一个键在后面已经存在，复用墓碑会导致重复——所以必须先确认键不存在，或者在复用前继续扫完探测链）。
3. **墓碑过多会导致性能退化**：探测链被墓碑拉长，查找变慢。所以需要**定期 rehash**（重建表，清除墓碑）。

**P0 的官方要求**：`Remove` 留 tombstone。是否要求 rehash 墓碑，官方页面未明说。

> 待核实：P0 是否要求/允许在墓碑比例过高时 rehash，以及 `LoadFactor()` 是否把墓碑计入分子。官方页面列出了 `LoadFactor()` 与 `MaxProbeDistance()`，但具体公式需查页面原文。

### 5.5 并发设计：为什么禁止全局锁

**官方硬指标**：最后一个测试要求**相对串行加速比 > 1.2**，并明确**禁止单把全局 latch**。

**全局锁的问题**：

```
Insert/Remove/Contains 全部 lock_guard(global_mutex)
→ 所有操作串行化 → 多线程吞吐 = 单线程吞吐 → 加速比 ≈ 1.0（甚至更差，因为锁竞争）
```

**分片锁方案**：

```cpp
static constexpr size_t kNumShards = 16;   // 2 的幂，便于取模
std::array<std::mutex, kNumShards> shards_;

std::mutex &ShardFor(const Key &k) {
  return shards_[hasher_(k) % kNumShards];
}
```

**问题**：Robin Hood 的插入会 **swap 到别的桶**，可能跨越分片边界 → 需要同时持有两把锁 → 锁顺序问题 → 死锁风险。

**实际可行的方案**（几种，官方未指定）：

1. **粗粒度分片 + 每个分片内部独立表**：把整个哈希表拆成 N 个**独立的子表**，每个子表有自己的桶数组和锁。`key` 按 `hash % N` 路由到固定子表。**优点**：无跨分片操作，简单。**缺点**：子表内仍是线性探测，负载因子按子表算（需要预留更多空间）。
2. **细粒度锁 + 手递手（hand-over-hand）加锁**：插入时按探测顺序依次加锁、释放前一把。复杂，容易死锁。
3. **无锁（lock-free）开放寻址**：用 CAS（compare-and-swap）原子操作。极难正确实现（ABA 问题、墓碑回收）。
4. **`std::atomic` + 序列锁（seqlock）**：读无锁、写加锁。

**推荐**：方案 1（独立子表）——最简单、最不容易出错，且能轻松达到 > 1.2 的加速比。

**注意 `Capacity()` 的语义**：如果拆成子表，`Capacity()` 应返回**总容量**（所有子表之和），`BucketCount()` 同理。`MaxProbeDistance()` 应返回所有子表中的最大值。

> 待核实：官方是否允许「拆成独立子表」这种实现（因为它改变了「一个连续的桶数组」的语义，`GetBucket(i)` 的下标映射会变）。若 `GetBucket` 的测试依赖连续下标，则必须用单一数组 + 细粒度锁。

### 5.6 移动语义的正确实现

**官方要求**：移动构造/移动赋值后，`Capacity() == 0`、`Size() == 0`，且仍可安全 `Clear()`。

**正确写法**：

```cpp
RobinHoodHashSet(RobinHoodHashSet &&other) noexcept
    : buckets_(std::move(other.buckets_)),
      capacity_(other.capacity_),
      size_(other.size_),
      hasher_(std::move(other.hasher_)),
      key_equal_(std::move(other.key_equal_)) {
  other.capacity_ = 0;      // 关键：源对象必须处于「空」状态
  other.size_ = 0;
  // other.buckets_ 已被 move，变为 nullptr
}

RobinHoodHashSet &operator=(RobinHoodHashSet &&other) noexcept {
  if (this != &other) {                    // 自赋值保护
    buckets_ = std::move(other.buckets_);
    capacity_ = other.capacity_;
    size_ = other.size_;
    hasher_ = std::move(other.hasher_);
    key_equal_ = std::move(other.key_equal_);
    other.capacity_ = 0;
    other.size_ = 0;
  }
  return *this;
}
```

**三个要点**：

1. **`noexcept`**：移动操作必须标 `noexcept`，否则 `std::vector` 等容器在扩容时会退化为拷贝（因为移动可能抛异常，无法保证强异常安全）。
2. **自赋值保护**：`if (this != &other)`。虽然移动自赋值很少见，但不加会 double-free。
3. **源对象置空**：`other.capacity_ = 0`。若不置空，源对象的 `Capacity()` 仍返回旧值，但 `buckets_` 已经是 `nullptr` → 后续 `Clear()` 会崩溃。

**`Clear()` 的健壮性**：`Clear()` 必须能处理 `capacity_ == 0` 的情况（直接返回，不解引用 `nullptr`）。

### 5.7 `const` 正确性与 `mutable`

**规则**：不修改**逻辑状态**的成员函数标 `const`。

**陷阱**：`Contains` 是 `const`，但它可能需要**加锁**（因为要防止并发 `Insert`）。而 `std::mutex::lock()` 不是 `const` 成员函数 → 编译错误。

**解法**：把 mutex 声明为 `mutable`：

```cpp
mutable std::mutex latch_;   // mutable 允许在 const 成员函数中修改

bool Contains(const Key &key) const {
  std::lock_guard<std::mutex> guard(latch_);   // OK，因为 latch_ 是 mutable
  ...
}
```

**为什么这是正确的**：加锁不改变**逻辑状态**（从调用者视角看，集合的内容没变），只是改变**同步状态**。所以 `mutable` 是合理的。

**注意**：不要滥用 `mutable`。如果一个函数真的修改了数据，它就不该是 `const`。

### 5.8 Google C++ Style 要点

| 规则 | 说明 |
|---|---|
| 文件名 | 全小写 + 下划线：`robin_hood_hash_set.h` |
| 类型名 | 大驼峰：`RobinHoodHashSet` |
| 变量名 | 全小写 + 下划线，成员变量加尾下划线：`capacity_` |
| 函数名 | 大驼峰：`Insert`、`MaxProbeDistance`（BusTub 用大驼峰，与 Google 默认的小写下划线不同） |
| 常量 | `k` 前缀 + 大驼峰：`kDefaultCapacity` |
| 命名空间 | 全小写：`bustub` |
| 头文件保护 | `#ifndef BUSTUB_PRIMER_ROBIN_HOOD_HASH_SET_H_` |
| 行宽 | 80 列 |
| 缩进 | 2 空格 |
| 指针/引用 | `int *p`（星号靠变量） |
| 禁止 | 异常用于控制流、RTTI（部分场景）、`using namespace` 在头文件中 |

**`clang-format`**：`make format` 自动格式化。**必须在提交前运行**——官方明确「Clang 检查不过则 0 分」。

**`clang-tidy`**：`make check-clang-tidy-p0` 做静态分析（未使用变量、隐式转换、性能问题等）。

## 6. 代码示例

### 6.1 官方课程代码

**官方页面给出的构建与测试命令**（来源 `_scout/15445_project0_.html`）：

```bash
# 依赖安装
sudo build_support/packages.sh

# 构建
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Debug ..
make -j$(nproc)

# 跑 P0 测试
make -j$(nproc) robin_hood_hash_set_test
./test/robin_hood_hash_set_test
```

**风格检查**：

```bash
make format
make check-lint
make check-clang-tidy-p0
```

**官方 API 清单**（从项目页整理，签名以官方头文件为准）：

| 成员 | 语义 |
|---|---|
| `RobinHoodHashSet(size_t capacity, Hasher, KeyEqual)` | `capacity == 0` 抛 `std::invalid_argument` |
| 移动构造 / 移动赋值 | 移动后 `Capacity()==0`、`Size()==0`，仍可安全 `Clear()` |
| `bool Insert(const Key &)` | 重复插入返回 `true` 且 `Size` 不变；表满且键不存在返回 `false` |
| `bool Remove(const Key &)` | 删除并留 tombstone |
| `bool Contains(const Key &) const` | 查找 |
| `void Clear()` | 清空（容量不变） |
| `GetBucket(i)` | 访问第 i 个桶（用于测试） |
| `Size()` / `Capacity()` / `BucketCount()` | 元素数 / 容量 / 桶数 |
| `LoadFactor()` | 负载因子 |
| `MaxProbeDistance()` | 最大探测距离；键不存在时返回 `Capacity()`；只统计 occupied |

**三种桶状态**：`EMPTY` / `OCCUPIED` / `TOMBSTONE`。

**并发要求**：`Insert` / `Remove` / `Contains` 线程安全；最后一个测试要求相对串行加速比 **> 1.2**；**禁止单把全局 latch**。

> 待核实：`BucketCount()` 与 `Capacity()` 的区别（通常 `BucketCount()` 是桶数组长度，`Capacity()` 是可容纳元素数的上限，可能等于 `BucketCount()` 或略小）；`LoadFactor()` 的分子是否含墓碑。需查官方头文件注释。

### 6.2 Agent 自行编写的教学示例

> 以下代码**非官方，仅用于说明概念**，不是 P0 的答案，也未实现完整的并发与墓碑策略。

**最小可运行的单线程 Robin Hood 哈希集合**（说明算法骨架）：

```cpp
// 非官方示例：仅示意 Robin Hood 插入/查找/删除的算法结构
#include <cstddef>
#include <functional>
#include <memory>
#include <optional>
#include <stdexcept>
#include <utility>

enum class BucketState : char { kEmpty, kOccupied, kTombstone };

template <typename Key, typename Hasher = std::hash<Key>,
          typename KeyEqual = std::equal_to<Key>>
class ToyRobinHoodSet {
 public:
  explicit ToyRobinHoodSet(size_t capacity, Hasher hasher = Hasher{},
                           KeyEqual eq = KeyEqual{})
      : capacity_(capacity),
        buckets_(std::make_unique<Bucket[]>(capacity)),
        hasher_(std::move(hasher)),
        key_equal_(std::move(eq)) {
    if (capacity == 0) throw std::invalid_argument("capacity must be > 0");
  }

  ToyRobinHoodSet(ToyRobinHoodSet &&other) noexcept
      : capacity_(other.capacity_), size_(other.size_),
        buckets_(std::move(other.buckets_)),
        hasher_(std::move(other.hasher_)), key_equal_(std::move(other.key_equal_)) {
    other.capacity_ = 0;
    other.size_ = 0;
  }

  bool Insert(const Key &key) {
    if (capacity_ == 0) return false;
    Key cur = key;
    size_t dist = 0;
    for (size_t step = 0; step < capacity_; ++step) {
      Bucket &b = buckets_[(hasher_(cur) + dist) % capacity_];
      if (b.state == BucketState::kEmpty || b.state == BucketState::kTombstone) {
        b.key = std::move(cur);
        b.dist = dist;
        b.state = BucketState::kOccupied;
        ++size_;
        return true;
      }
      if (key_equal_(b.key, cur)) return true;          // 已存在
      if (b.dist < dist) {                               // 劫富济贫
        std::swap(cur, b.key);
        std::swap(dist, b.dist);
      }
      ++dist;
    }
    return false;                                        // 表满
  }

  bool Contains(const Key &key) const {
    if (capacity_ == 0) return false;
    size_t dist = 0;
    for (size_t step = 0; step < capacity_; ++step) {
      const Bucket &b = buckets_[(hasher_(key) + dist) % capacity_];
      if (b.state == BucketState::kEmpty) return false;
      if (b.state == BucketState::kOccupied && key_equal_(b.key, key)) return true;
      if (b.state == BucketState::kOccupied && b.dist < dist) return false;  // 提前终止
      ++dist;
    }
    return false;
  }

  bool Remove(const Key &key) {
    if (capacity_ == 0) return false;
    size_t dist = 0;
    for (size_t step = 0; step < capacity_; ++step) {
      Bucket &b = buckets_[(hasher_(key) + dist) % capacity_];
      if (b.state == BucketState::kEmpty) return false;
      if (b.state == BucketState::kOccupied && key_equal_(b.key, key)) {
        b.state = BucketState::kTombstone;
        --size_;
        return true;
      }
      if (b.state == BucketState::kOccupied && b.dist < dist) return false;
      ++dist;
    }
    return false;
  }

  size_t Size() const { return size_; }
  size_t Capacity() const { return capacity_; }

  void Clear() {
    if (capacity_ == 0) return;                 // 关键：move 后仍可安全调用
    for (size_t i = 0; i < capacity_; ++i) buckets_[i] = Bucket{};
    size_ = 0;
  }

 private:
  struct Bucket {
    Key key{};
    size_t dist{0};
    BucketState state{BucketState::kEmpty};
  };

  size_t capacity_{0};
  size_t size_{0};
  std::unique_ptr<Bucket[]> buckets_;
  Hasher hasher_;
  KeyEqual key_equal_;
};
```

**分片锁骨架**（说明并发思路，非完整实现）：

```cpp
// 非官方示例：16 个独立子表，按 hash 路由
class ShardedSet {
 public:
  explicit ShardedSet(size_t capacity_per_shard)
      : shards_() {
    for (auto &s : shards_) s = std::make_unique<Shard>(capacity_per_shard);
  }

  bool Insert(const Key &k) {
    Shard &s = ShardFor(k);
    std::lock_guard<std::mutex> guard(s.latch);
    return s.set.Insert(k);
  }

 private:
  struct Shard {
    mutable std::mutex latch;
    ToyRobinHoodSet<Key> set{1};   // 实际容量由构造函数设置
  };
  static constexpr size_t kShards = 16;
  std::array<std::unique_ptr<Shard>, kShards> shards_;
  Hasher hasher_;

  Shard &ShardFor(const Key &k) { return *shards_[hasher_(k) % kShards]; }
};
```

**说明**：这个分片方案能轻松达到 > 1.2 的加速比，但**改变了 `GetBucket(i)` 的语义**（如果官方测试依赖连续桶数组，就不能这样写）。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| `unique_ptr` | `shared_ptr` | 前者独占所有权、零开销、只能 move；后者共享所有权、有原子引用计数、可拷贝。P0 只需 `unique_ptr` |
| 拷贝 | 移动 | 拷贝复制资源（源不变）；移动转移资源（源变空）。移动必须 `noexcept` |
| `Capacity()` | `Size()` | 前者是**能装多少**（桶数/上限）；后者是**已装多少**（元素数） |
| `EMPTY` | `TOMBSTONE` | 查找遇 `EMPTY` **停止**；遇 `TOMBSTONE` **继续**。插入可复用 `TOMBSTONE` |
| 线性探测 | Robin Hood | 前者「先到先得」，探测距离方差大；后者「劫富济贫」，方差小、尾延迟低 |
| 链地址法 | 开放寻址 | 前者用外部链表（可无限装，缓存不友好）；后者全在数组内（缓存友好，需要墓碑） |
| `const` 成员函数 | `mutable` 成员 | 前者承诺不改逻辑状态；后者允许在 `const` 函数中修改（如 mutex） |
| `BUSTUB_ASSERT` | `BUSTUB_ENSURE` | 前者 release 不执行（仅调试）；后者始终执行（必须保证的不变式） |
| 全局锁 | 分片锁 | 前者简单但吞吐 = 单线程；后者并行但有跨分片操作的复杂度 |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Project #0 官方页面（HTML） | `_scout/15445_project0_.html` | — | 全部：任务描述、API、构建、评分、并发要求、学术诚信 |
| 相关讲义 slides | `90-原始PDF/15-445/slides/07-hashtables.pdf` | 待人工核对 | 哈希表在数据库中的应用（哈希索引、哈希连接） |
| 相关讲义文本 | `_scout/text/15-445__slides__07-hashtables.pdf.txt` | 待人工核对 | 同上 |

原始 URL：

- Project #0 页面：`https://15445.courses.cs.cmu.edu/fall2026/project0/`（Last Updated Nov 10 2026）
- 讲义 slides：`https://15445.courses.cs.cmu.edu/fall2026/slides/07-hashtables.pdf`

> 待核实：`07-hashtables.pdf` 的总页数与重点页码未在本笔记中核实（`_scout/pdf-pages.json` 无 15-445 条目，需用 `=== [page N] ===` 计数）。P0 本身**没有对应的官方讲义**——它是 C++ 技能训练，不是数据库理论。

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内）

Project #0 **没有官方讲解视频**——它是纯编程任务，说明只在网页上。

若需要补 C++ 基础，可参考：

- 2025 年第 07 讲（Hash Tables）——对应 [[15-445-07-Hash-Tables]]
- URL：`https://www.youtube.com/watch?v=tMFAgvDViAI&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`（注：该 ID 对应 2025 年第 17 讲，哈希表讲次的准确 ID 未核实）
- 年份：2025
- 时间戳：未核实，故不标注。

> 待核实：2025 年哈希表（Hash Tables）讲次的 YouTube ID。任务给定的映射表只覆盖 2026 第 14–24 讲 → 2025 第 13–23 讲，未给出第 07 讲的 ID。上方的 `tMFAgvDViAI` 是 2025 年第 17 讲（Concurrency Control Theory）的 ID，**不是哈希表讲次**，此处仅作播放列表入口示意，请勿当作哈希表视频。

说明：FAQ Q11 明确 Fall 2026 的录像只对 CMU 学生开放，非 CMU 学习者应观看 Fall 2025 的公开视频。

## 10. 本节复习

- 能解释 RAII 如何保证异常安全，并举出 P0 中的例子。
- 能说出 `unique_ptr` 与 `shared_ptr` 的三个差别，并说明为什么 P0 不需要 `shared_ptr`。
- 能写出一个正确的移动构造函数（含 `noexcept`、自赋值保护、源对象置空）。
- 能解释 Robin Hood 插入算法中的 swap 条件，以及它为什么降低探测距离方差。
- 能说明墓碑的必要性，以及查找/插入时对 `EMPTY` 与 `TOMBSTONE` 的不同处理。
- 能解释为什么禁止全局锁，并描述一种分片并发方案。
- 能说出 Google C++ Style 的五条命名规则。
- 能说明 `mutable` 在 `const` 成员函数中的作用。

## 11. 自我检查

**Q1.** 为什么移动构造函数必须标 `noexcept`？如果不标会怎样？

<details><summary>参考答案</summary>

**因为标准库容器在扩容时需要「强异常安全保证（strong exception safety）」，而移动可能抛异常会破坏这个保证。**

**具体机制**：

`std::vector<T>` 扩容时，需要把旧缓冲区的元素搬到新缓冲区。有两种方式：

1. **拷贝**：如果拷贝中途抛异常，旧缓冲区仍然完好，可以回滚 → 强异常安全。
2. **移动**：如果移动中途抛异常，旧元素已经被部分修改（处于「有效但未指定」状态），**无法回滚** → 只能提供基本保证。

所以 `std::vector` 的规则是：

- 若 `T` 的移动构造函数是 `noexcept`（或 `T` 不可拷贝）→ **用移动**（快）。
- 否则 → **用拷贝**（慢，但安全）。

**后果**：如果你的类型有移动构造但没标 `noexcept`，`std::vector<YourType>` 扩容时会**静默地退化为拷贝**——性能下降但你不会收到任何警告。

**P0 的语境**：`RobinHoodHashSet` 本身可能被放进容器，或者它的成员（如 `std::vector`）依赖这一点。标 `noexcept` 是**零成本的正确性**。

**注意**：标 `noexcept` 是一种**承诺**。如果函数体真的抛了异常，程序会直接 `std::terminate`。所以只有当你能保证不抛时才能标——移动构造通常只是转移指针与整数，不会抛。

</details>

**Q2.** 假设表容量 8，哈希函数把所有键都映射到下标 0。依次插入 A、B、C、D，画出桶数组，并说明每个元素的探测距离。然后删除 B，再插入 E（哈希也是 0），画出结果。

<details><summary>参考答案</summary>

**插入 A、B、C、D**（线性探测 + Robin Hood，但所有键哈希都是 0，所以 Robin Hood 的 swap 不会触发——因为每个新键的 `dist` 都等于「当前空位数」，而原住民的 `dist` 恰好也等于它的下标）：

```
下标:   0    1    2    3    4    5    6    7
      [A]  [B]  [C]  [D]  [ ]  [ ]  [ ]  [ ]
dist:   0    1    2    3
```

- A：理想位置 0，空 → 放在 0，`dist=0`。
- B：理想位置 0 被占（A 的 `dist=0`，B 的 `dist=0`，`0 < 0` 为假，不 swap）→ 走到 1，`dist=1`。
- C：走到 2，`dist=2`。
- D：走到 3，`dist=3`。

**删除 B**（留墓碑）：

```
下标:   0    1    2    3    4    5    6    7
      [A] [T]  [C]  [D]  [ ]  [ ]  [ ]  [ ]
dist:   0    -    2    3
```

**插入 E**（哈希 0）：

```
E 从下标 0 开始，dist=0：
  下标 0：A 占用，A.dist=0，0 < 0 为假 → 不 swap，dist 变 1
  下标 1：TOMBSTONE → 可复用！放 E，dist=1
```

结果：

```
下标:   0    1    2    3    4    5    6    7
      [A]  [E]  [C]  [D]  [ ]  [ ]  [ ]  [ ]
dist:   0    1    2    3
```

**关键观察**：

1. 墓碑被复用后，探测链完好（0→1→2→3 连续）。
2. C 的 `dist=2`、D 的 `dist=3` 不变——因为 E 插在了 B 原来的位置，没有改变它们的相对顺序。
3. **如果 E 的哈希是 1**（理想位置 1），E 会直接放到下标 1，`dist=0`。此时 C 在下标 2、`dist=2`，而 C 的理想位置仍是 0——探测链上出现 `dist` 从 0 跳到 2 的「断崖」，但**这不影响查找正确性**（查找 C 时从 0 开始，0=A、1=E（dist=0 < 1 → 提前终止！））。

**等等，这里有问题！** 查找 C 时：`dist=0`，下标 0 是 A（`dist=0`，`0 < 0` 假），继续；`dist=1`，下标 1 是 E（`dist=0`，`0 < 1` **真**）→ **提前终止，返回 false**。但 C 明明在下标 2！

**这说明 Robin Hood 的「提前终止」优化有一个前提**：表必须满足「探测距离沿探测链单调不减」。而这个性质**只在插入时通过 swap 维护**。如果删除后墓碑被一个「距离更小」的键复用，单调性就被破坏了。

**正确的解法**：Robin Hood 的删除不能简单留墓碑，而要用**向后移位删除（backward shift deletion）**：删除后，把后面探测链上的元素**依次前移**，直到遇到空桶或一个「dist=0」的元素。

**结论**：这道题暴露了 P0 的一个真实难点——**墓碑 + Robin Hood + 提前终止优化三者不兼容**。实际实现中必须选：

- (a) 用墓碑但**放弃提前终止**（查找一直扫到 EMPTY）；
- (b) 用墓碑 + 记录「探测链上是否有墓碑」来调整终止条件；
- (c) 用 backward shift deletion（无墓碑）。

> 待核实：P0 官方要求「`Remove` 留 tombstone」，那么 `Contains` 是否允许提前终止？若允许，必须额外维护单调性。**这是本笔记中最需要对照官方测试验证的一点。**

</details>

**Q3.** 为什么 `Contains` 必须是 `const` 成员函数，而它内部又需要加锁？这两者矛盾吗？

<details><summary>参考答案</summary>

**不矛盾，用 `mutable` 解决。**

**为什么 `Contains` 必须 `const`**：

1. **API 语义**：查找不改变集合内容。如果 `Contains` 不是 `const`，那么 `const RobinHoodHashSet &s` 就无法调用 `s.Contains(k)`——这会让集合无法在 `const` 上下文（如 `const` 成员函数的参数）中使用。
2. **接口一致性**：标准库的 `std::unordered_set::contains` 是 `const`。用户期望 `Contains` 也是。
3. **编译器优化**：`const` 成员函数可以被更激进地优化（虽然实践中影响很小）。

**为什么需要加锁**：因为 `Contains` 可能与并发的 `Insert` / `Remove` 同时执行。如果不加锁，读到一半表被修改 → 数据竞争（undefined behavior）。

**矛盾的表面**：`std::mutex::lock()` 是**非 const** 成员函数（它修改 mutex 的内部状态）。所以在 `const` 成员函数里调用 `latch_.lock()` 会编译失败。

**解法**：把 mutex 声明为 `mutable`：

```cpp
mutable std::mutex latch_;   // 允许在 const 成员函数中被修改

bool Contains(const Key &key) const {
  std::lock_guard<std::mutex> guard(latch_);   // OK
  ...
}
```

**为什么这是「语义正确」的而不是「绕过编译器」**：

C++ 的 `const` 承诺的是「**逻辑常量性（logical constness）**」——从**调用者的可观察视角**看，对象的状态没变。加锁改变了 mutex 的**物理状态**（locked/unlocked），但这**不是对象逻辑状态的一部分**——调用者不关心锁是开是关，只关心集合里有什么元素。

所以 `mutable` 在这里是**正确的语义表达**，不是 hack。

**反例（滥用 mutable）**：如果一个函数真的修改了元素（如 `Insert`），把它标 `const` 并用 `mutable` 绕过编译器，那就是**错误**——因为调用者会观察到状态变化，违反了逻辑常量性。

**另一个选择**：用 `std::shared_mutex` 做读写锁，`Contains` 加读锁（`std::shared_lock`），`Insert`/`Remove` 加写锁（`std::unique_lock`）。这样多个读可以并行。但 `shared_mutex` 的读锁也有开销，在短临界区下不一定比 `mutex` 快。

</details>

**Q4.** 官方要求「相对串行加速比 > 1.2」且「禁止单把全局 latch」。给你 8 核机器，你会怎么设计？为什么加速比只有 1.2 这么低的要求？

<details><summary>参考答案</summary>

**设计（分片独立子表）**：

```cpp
static constexpr size_t kNumShards = 16;   // 16 > 8 核，减少碰撞

struct Shard {
  mutable std::mutex latch;
  std::unique_ptr<Bucket[]> buckets;
  size_t size, capacity;
};

std::array<Shard, kNumShards> shards_;

Shard &ShardFor(const Key &k) {
  return shards_[hasher_(k) % kNumShards];   // 固定路由
}
```

- **Insert / Remove / Contains**：先算 `hasher_(k) % 16`，锁对应 shard，然后在 shard 内部做单线程 Robin Hood。
- **无跨分片操作**：每个 key 永远只属于一个 shard，不存在「swap 到别的分片」的问题。
- **`Capacity()`**：返回所有 shard 容量之和。
- **`MaxProbeDistance()`**：返回所有 shard 的最大值。

**为什么加速比只要 > 1.2**：

1. **测试负载可能很小**：如果测试只跑几千次操作，线程创建/销毁的开销（~10–100 μs/线程）会吃掉大部分并行收益。Amdahl 定律：串行部分（初始化、结果汇总）占比大时，加速比上不去。
2. **哈希分布可能不均**：如果测试用的键分布偏斜，某些 shard 成为热点，其他 shard 空闲 → 实际并行度远低于 16。
3. **内存带宽是瓶颈**：哈希表操作是内存密集型，8 核同时跑可能撞上内存带宽上限（NUMA 架构下更明显）。
4. **> 1.2 是「下限」而非「目标」**：官方的意图是**筛掉全局锁**（全局锁的加速比 ≈ 1.0 或更低），而不是要求你做到线性扩展。1.2 是一个「明显超过噪声」的阈值。
5. **测试可能有写操作**：写操作需要修改共享状态（`size_` 计数），即使分片，`size_` 的原子累加也是竞争点。可以用**每 shard 独立计数**，`Size()` 时求和。

**注意事项**：

- **`Size()` 的原子性**：如果每个 shard 独立计数，`Size()` 求和时可能读到不一致的快照（某个 shard 正在插入）。官方测试可能不检查这个，但严格来说需要加锁或用 `std::atomic` 累加。
- **`Clear()` 的并发语义**：`Clear()` 是否需要与 `Insert` 互斥？如果测试中有并发 `Clear`，必须锁所有 shard（按固定顺序避免死锁）。
- **false sharing**：16 个 `std::mutex` 如果紧挨着放在内存里，会共享 cache line → 一个核锁 shard 0 会让 shard 1 的 cache line 失效。解法：`alignas(64)` 填充。

**如果官方测试依赖连续桶数组**（`GetBucket(i)`），就不能拆成独立子表，必须用「单一数组 + 每桶或每段一把锁」的方案，复杂度和死锁风险都高得多。

> 待核实：官方测试是否使用 `GetBucket(i)` 验证内部布局。若使用，分片方案不可行。

</details>

## 12. 进一步学习

- 项目导航：[[00-项目总览]]
- 下一个项目：`02-Project1-Buffer-Pool.md`
- 相关讲义：[[15-445-07-Hash-Tables]]（哈希表在数据库中的角色）、[[15-445-04-Memory-Management]]（内存管理，P1 的前置）
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：
  - Celis, "Robin Hood Hashing"（1986，PhD thesis）——原始论文，分析了探测距离方差。
  - 陈硕《Linux 多线程服务端编程》——C++ 并发与 RAII 的实践。
  - Scott Meyers, *Effective Modern C++*（2014）第 5 章（右值引用、移动语义、完美转发）——**移动语义的最佳参考**。
  - cppreference：`std::unique_ptr`、`std::shared_ptr`、`std::atomic`、`std::shared_mutex` 的完整语义。
  - Google C++ Style Guide：`https://google.github.io/styleguide/cppguide.html`
  - BusTub 仓库 `src/include/primer/robin_hood_hash_set.h` 的注释——**最权威的规格来源**（若仓库已公开 Fall 2026 分支）。
- **提醒**：本笔记依据项目页公开说明整理，具体任务以官方 project0 页与仓库头文件注释为准。`> 待核实：` 标记处需人工核对。
