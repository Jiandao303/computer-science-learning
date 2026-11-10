---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: P2
topic: Project 2 - B+Tree Index
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 项目
  - B+树
  - 索引
  - latch-crabbing
---

# 15-445 Project #2：B+ 树索引（B+Tree Index）

> **重要边界说明**：本 vault **未抓取** Fall 2026 的 project2 官方页面，本篇为「课程结构公开信息 + 通用知识」整理，**具体规格细节一律标 `> 待核实：`**，不编造。
>
> 官方页面（待人工核对）：`https://15445.courses.cs.cmu.edu/fall2026/project2/`
>
> 对应讲义：[[15-445-08-Indexes-and-Filters-I]]、[[15-445-09-Indexes-and-Filters-II]]、[[15-445-10-Index-Concurrency-Control]]。Fall 2026 课表把 Database Index 安排在第 10 周。
>
> **Fall 2026 政策提醒**：Project #2 **禁止使用 coding agents**（官方主页 "P1-P2 prohibit coding agents"）。这是整个课程最需要「亲手调试」的项目。

## 1. 本节学习目标

1. 说清 **B+ 树**的结构：内部节点（internal node）与叶节点（leaf node）的分工、阶（order）与扇出（fan-out）的关系。
2. 掌握**点查（point lookup）**、**范围扫描（range scan）** 的算法与迭代器（iterator）设计。
3. 掌握**插入**的完整流程：找到叶节点、插入、分裂（split）、向上传播、根分裂。
4. 掌握**删除**的完整流程：删除、下溢（underflow）、合并（merge）或重分配（redistribute）、根收缩。
5. 理解 **latch crabbing（闩锁蟹行）** 协议：乐观/悲观两种模式、为什么乐观模式需要「重启」、死锁如何避免。
6. 理解 **B+ 树在磁盘上的布局**：节点大小 = 页大小、键值数组、`RID`（record id）的表示。
7. 能说出 B+ 树与 B 树、哈希索引、LSM 树的取舍。

## 2. 前置知识

- **C++17**：模板、`std::optional`、迭代器模式、`std::shared_mutex`。见 `01-Project0-Cpp-Primer.md`。
- **缓冲池**：B+ 树的节点是页，必须通过 `BufferPoolManager` 访问。见 `02-Project1-Buffer-Pool.md`。
- **页布局**：`RID`、槽位数组、变长记录。见 [[15-445-03-Database-Storage-I]]、[[15-445-06-Storage-Models-and-Compression]]。
- **并发控制基础**：latch vs lock 的区别。见 [[15-445-10-Index-Concurrency-Control]]。
- 上一个项目：`02-Project1-Buffer-Pool.md`（没有缓冲池，B+ 树无法工作）。

## 3. 核心概念

### 3.1 B+Tree（B+ 树）

一种**自平衡的多路搜索树**，专为**磁盘**设计：

- 每个节点是一个**页**（通常 4KB），扇出（一个节点能有多少子节点）可达数百。
- **内部节点**只存键与子指针，不存数据。
- **叶节点**存键与数据（或 `RID`），并用**兄弟指针**串成链表。
- **所有数据都在叶节点**，且叶节点按 key 有序 → 范围扫描只需沿链表走。

### 3.2 Order / Fan-out（阶 / 扇出）

一个节点最多能有多少个子指针。若页大小 4KB，键 8 字节、指针 4 字节，则内部节点扇出 ≈ `4096 / 12 ≈ 341`。三层 B+ 树可存 `341³ ≈ 4000 万` 条记录——这就是 B+ 树「浅而宽」的威力。

### 3.3 Internal Node（内部节点）

存 `n` 个键与 `n+1` 个子指针。键 `K_i` 表示「第 `i+1` 个子树的所有键都 `>= K_i` 且 `< K_{i+1}`」。

**两种键的存放约定**（BusTub 的选择待核实）：

- **键在内部节点重复**（PostgreSQL 风格）：内部节点的键是子树中最小键的副本。
- **键只存一次**（某些实现）：内部节点的键是分隔符，不重复。

### 3.4 Leaf Node（叶节点）

存 `n` 个键值对，以及指向**右兄弟**的指针。叶节点之间形成有序链表。

### 3.5 RID（Record Identifier，记录标识符）

指向表中实际记录的指针，通常是 `(page_id, slot_num)`。B+ 树的叶节点存 `(key, RID)` 对，通过 `RID` 找到表中的行。

### 3.6 Iterator（迭代器）

B+ 树的范围扫描接口。典型用法：

```cpp
for (auto it = tree->Begin(); !it.IsEnd(); it.Next()) {
  auto [key, rid] = *it;
  // ...
}
```

迭代器内部持有**当前叶节点的 guard** 与**当前槽位下标**，`Next()` 走到叶节点末尾时跳到右兄弟。

### 3.7 Latch Crabbing（闩锁蟹行）

并发访问 B+ 树的协议：

1. 拿父节点的 latch。
2. 拿子节点的 latch。
3. 若子节点「安全」（不会分裂/合并），释放父节点的 latch。
4. 继续向下。

像螃蟹横着走——**同时最多持有两个 latch**。

### 3.8 Optimistic vs Pessimistic（乐观 vs 悲观）

- **乐观（optimistic）**：假设不会分裂/合并，只加**读 latch** 一路向下，到叶节点加写 latch。若发现叶节点真的需要分裂，**释放所有 latch 并重启**（用悲观模式）。
- **悲观（pessimistic）**：从根开始就加**写 latch**，一路向下。安全但并发度低。

### 3.9 Safe Node（安全节点）

一个节点是「安全的」，如果对它做插入/删除**不会导致它分裂或合并**：

- **插入时**：节点未满（`size < max_size`）。
- **删除时**：节点超过半满（`size > min_size`）。

## 4. 通俗理解

**B+ 树 = 图书馆的多级索引卡**：

- **根节点** = 大厅的总目录：「A–F 在 1 楼，G–M 在 2 楼……」
- **内部节点** = 每层楼的分区指示牌。
- **叶节点** = 书架上的具体书位。
- **兄弟指针** = 书架之间的「继续往右走」箭头——找「所有姓 Smith 的人」时，不用回到总目录，沿箭头走就行。

**为什么 B+ 树「矮胖」好**：每次从根走到叶 = 一次磁盘 I/O（如果节点不在内存）。三层树 = 3 次 I/O。如果把扇出从 341 降到 2（二叉树），1000 万条记录需要 24 层 = 24 次 I/O。**扇出每翻倍，层数少一层**——这就是为什么数据库的 B+ 树要「尽量宽」。

**latch crabbing = 过旋转门**：你进旋转门之前先确认下一格是空的（拿子节点 latch），确认后就可以松手（释放父节点 latch）。如果发现下一格有人（子节点要分裂），你就退回去重新排队（重启）。

**乐观 vs 悲观 = 出门带不带伞**：

- **乐观**：看天气预报（读 latch），觉得不会下雨就不带伞。真下雨了就回家拿（重启）。
- **悲观**：永远带伞（写 latch）。麻烦但不会淋雨。

**分裂 = 书架放满了**：一个书架放 100 本书，第 101 本来了 → 买一个新书架，把一半书搬过去，然后在目录里加一条「从第 51 本开始去新书架」。

**合并 = 书架空了**：一个书架只剩 10 本书（低于下限）→ 把书搬到隔壁书架，把空书架撤掉，目录里删掉一条。

## 5. 原理与推导

> **以下为通用知识整理，非依据 2026 官方讲义。** 具体任务拆解与 API 需以官方 project2 页面为准。

### 5.1 B+ 树的结构与不变式

**定义**（阶为 `m`，即最多 `m` 个子指针）：

- 每个内部节点有 `⌈m/2⌉` 到 `m` 个子指针（根节点例外，可少至 2）。
- 每个叶节点有 `⌈(m-1)/2⌉` 到 `m-1` 个键值对。
- 所有叶节点在同一层（**平衡**）。
- 叶节点按 key 有序，且用兄弟指针串联。

**BusTub 的参数**（待核实）：通常 `leaf_max_size` 与 `internal_max_size` 是可配置的，测试中会用小值（如 2、3）来强制触发分裂/合并。

**为什么用「小 max_size」测试**：如果 `max_size = 300`，一个测试要插 300 条才触发一次分裂，很难覆盖边界。设成 2 或 3，几条插入就能触发各种分裂/合并路径。

### 5.2 点查（Point Lookup）

```
GetValue(key):
  node = root
  while node is internal:
      i = 第一个满足 key < node.key[i] 的下标   # 二分查找
      node = node.child[i]
  # node 是叶节点
  i = 二分查找 key 在 node 中的位置
  if node.key[i] == key: return node.value[i]
  else: return not found
```

**复杂度**：树高 `h = O(log_m n)`，每层一次二分 `O(log m)`。总计 `O(log n)` 次比较，`O(h)` 次页访问。

**为什么内部节点用「第一个 `key < node.key[i]`」而不是 `<=`**：取决于键的存放约定。若内部节点的键是「右子树的最小键」，则 `key < K_i` 走左子树，`key >= K_i` 走右子树。

### 5.3 范围扫描与迭代器

```
Scan(low, high):
  # 1. 找到 >= low 的第一个叶节点
  leaf = FindLeaf(low)
  # 2. 在叶节点内定位起始槽位
  i = lower_bound(leaf, low)
  # 3. 沿兄弟指针遍历
  while leaf != null:
      while i < leaf.size:
          if leaf.key[i] > high: return
          yield (leaf.key[i], leaf.value[i])
          i++
      leaf = leaf.next_leaf
      i = 0
```

**迭代器的状态**：

- 当前叶节点的 `ReadPageGuard`（保证叶节点不被淘汰）
- 当前槽位下标
- （可选）上界 `high`

**关键难点：guard 的生命周期**。当迭代器从叶 A 跳到叶 B 时：

1. 必须先**获取叶 B 的 guard**（`FetchPage(B_pid)`），**再释放**叶 A 的 guard。
2. 顺序反了会导致「叶 A 被淘汰，但 `next_leaf` 指针已失效」。

**死锁风险**：如果两个迭代器分别持叶 A、叶 B 的读 guard，然后都想获取对方的——读锁不会死锁（读锁相容），但如果涉及写锁就会。

**`End()` 的表示**：迭代器走到最后一个叶节点的末尾 → `IsEnd()` 返回 true。

### 5.4 插入与分裂

```
Insert(key, value):
  # 1. 找到目标叶节点（记录路径）
  path = FindLeafWithPath(key)
  leaf = path.back()

  # 2. 插入到叶节点
  if leaf already has key:
      leaf.value[key] = value     # 更新（或拒绝，取决于是否 unique index）
      return true
  InsertIntoLeaf(leaf, key, value)

  # 3. 若叶节点溢出，分裂
  if leaf.size > leaf_max_size:
      new_leaf = SplitLeaf(leaf)          # 把后半部分移到新叶
      new_leaf.next = leaf.next
      leaf.next = new_leaf
      # 把 new_leaf 的最小键 + 指针插入父节点
      InsertIntoParent(path, new_leaf.min_key, new_leaf)

  return true
```

**`InsertIntoParent` 的递归传播**：

```
InsertIntoParent(path, key, new_child):
  if path is empty:                       # 根分裂
      new_root = AllocateInternalNode()
      new_root.child[0] = old_root
      new_root.key[0] = key
      new_root.child[1] = new_child
      root_pid = new_root.pid
      return

  parent = path.pop()
  InsertIntoInternal(parent, key, new_child)
  if parent.size > internal_max_size:
      new_sibling = SplitInternal(parent)
      InsertIntoParent(path, new_sibling.min_key, new_sibling)
```

**分裂的细节（叶节点）**：

```
SplitLeaf(leaf):
  mid = leaf.size / 2
  new_leaf = AllocateLeafNode()
  # 把 leaf[mid..end] 移到 new_leaf
  MoveEntries(leaf, mid, leaf.size, new_leaf)
  leaf.size = mid
  return new_leaf
```

**分裂的细节（内部节点）**：

内部节点分裂时，**中间的键要「提升」到父节点**，不留在任何子节点里（因为内部节点的键是分隔符）：

```
SplitInternal(node):
  mid = node.size / 2
  promote_key = node.key[mid]
  new_node = AllocateInternalNode()
  # 把 node[mid+1..end] 的键与指针移到 new_node
  MoveEntries(node, mid + 1, node.size, new_node)
  node.size = mid
  return (new_node, promote_key)
```

**这就是 B 树与 B+ 树的关键区别之一**：B 树的键在内部节点也存数据，分裂时提升的键**同时**留在子节点；B+ 树的内部节点只存分隔符，提升后原位置删除。

### 5.5 删除与合并

```
Delete(key):
  path = FindLeafWithPath(key)
  leaf = path.back()

  if key not in leaf: return false
  RemoveFromLeaf(leaf, key)

  # 若叶节点下溢
  if leaf.size < leaf_min_size:
      HandleUnderflow(path, leaf)

  return true
```

**`HandleUnderflow` 的两种策略**：

1. **重分配（redistribute / borrow）**：从兄弟节点借一个键值对。
   - 若左兄弟有富余（`size > min`），借它的最后一个。
   - 否则若右兄弟有富余，借它的第一个。
   - 更新父节点的分隔键。

2. **合并（merge / coalesce）**：与兄弟合并。
   - 与左兄弟或右兄弟合并成一个节点。
   - 从父节点删除对应的键与指针。
   - 递归处理父节点的下溢。

**根节点的特殊处理**：

- 若根是内部节点且只剩 1 个子指针 → **根收缩（shrink）**：把根替换为唯一的子节点。
- 若根是叶节点且为空 → 树变空（根仍是叶节点）。

**删除的陷阱**：

- 合并内部节点时，**父节点的分隔键要下放到合并后的节点**（因为内部节点的键是分隔符，合并后不再需要这个分隔）。
- 与左兄弟合并 vs 与右兄弟合并，**父节点要删的键不同**（左兄弟合并删左分隔键，右兄弟合并删右分隔键）。

### 5.6 Latch Crabbing 协议详解

**基本协议**：

```
1. latch(root, READ)          # 或 WRITE（悲观模式）
2. child = root.child[i]
3. latch(child, READ/WRITE)
4. if child is safe:
       unlatch(root)          # 释放父节点
5. root = child; goto 2
```

**为什么叫「蟹行」**：同时最多持两个 latch（父 + 子），像螃蟹的两只钳子。

**乐观模式（查找/插入的快速路径）**：

```
1. 从根开始，全部加 READ latch
2. 一路向下，每次拿到子节点后释放父节点
3. 到达叶节点后，升级为 WRITE latch（释放 READ，获取 WRITE）
4. 若叶节点安全（不会分裂）→ 直接修改，完成
5. 若叶节点不安全 → 释放所有 latch，用悲观模式重来
```

**为什么需要重启**：乐观模式下，从根到叶的路径上**只加了 READ latch**。当发现叶节点需要分裂时，需要修改父节点——但父节点的 READ latch 已经释放了，而且可能已被其他线程修改。所以只能从头再来，这次用 WRITE latch 一路向下。

**悲观模式**：

```
1. 从根开始加 WRITE latch
2. 一路向下，只有确认子节点安全后才释放父节点
3. 到达叶节点，直接修改
```

**悲观模式的正确性**：因为一直持有 WRITE latch 直到确认子节点安全，所以路径上的节点不会被其他线程修改。

**死锁避免**：

- **自顶向下加锁**（总是先父后子）→ 无循环等待 → 无死锁。
- **释放顺序无关**（释放不会导致死锁）。

**性能对比**：

| 模式 | 读并发 | 写并发 | 适用 |
|---|---|---|---|
| 悲观 | 低（根节点是瓶颈） | 低 | 写密集、树很浅 |
| 乐观 | 高 | 中（冲突时重启） | 读密集、树较深 |

**BusTub 的要求**（待核实）：通常要求实现**乐观 + 悲观两种**，并在测试中验证并发正确性（多线程同时插入/删除/查找，最后检查树的结构）。

### 5.7 磁盘布局

B+ 树的每个节点 = 一个页。页内的布局：

```
┌────────────────────────────────────────────┐
│ Header:                                    │
│   node_type (leaf/internal)                │
│   size (当前键值对数量)                     │
│   max_size                                 │
│   next_page_id (仅叶节点，兄弟指针)         │
├────────────────────────────────────────────┤
│ Key[0] | Key[1] | ... | Key[n-1]           │
├────────────────────────────────────────────┤
│ Value[0]/RID[0] | ... | Value[n-1]         │
│ （内部节点：Child[0] | ... | Child[n]）     │
└────────────────────────────────────────────┘
```

**变长键的处理**：如果键是变长的（如 `std::string`），布局会复杂得多——需要槽位目录（slot directory）或偏移数组。BusTub 的 P2 通常用**定长键**（模板参数 `KeyType`），简化布局。

> 待核实：BusTub Fall 2026 的 P2 是否支持变长键（`GenericKey` 的大小限制）、是否要求实现 `Iterator` 的 `operator++` 与 `operator*`、是否要求支持非 unique index（重复键）。

### 5.8 B+ 树 vs 其他索引结构

| 结构 | 点查 | 范围扫描 | 写放大 | 适用 |
|---|---|---|---|---|
| **B+ 树** | O(log n) | **优秀**（叶链表） | 中（页分裂） | 通用，OLTP 默认 |
| **哈希索引** | **O(1)** | **不支持** | 低 | 等值查询、哈希连接 |
| **LSM 树** | O(log n)（多层） | 良好 | **低**（顺序写） | 写密集（RocksDB、Cassandra） |
| **ART（自适应基数树）** | O(k)（键长） | 良好 | 低 | 内存数据库（HyPer） |
| **B 树** | O(log n) | 良好 | 中 | 数据也存内部节点，扇出小 |

**为什么 OLTP 默认 B+ 树**：范围扫描是 SQL 的高频操作（`WHERE x BETWEEN a AND b`、`ORDER BY`、`JOIN` 的排序合并）。哈希索引不支持范围，LSM 的范围扫描要合并多层，B+ 树最均衡。

## 6. 代码示例

### 6.1 官方课程代码

**本 vault 未抓取 Fall 2026 project2 官方页面，无官方代码可引。**

待官方页面获取后需补充：

- `BPlusTreePage` 的基类声明（`GetSize()`、`GetMaxSize()`、`IsLeafPage()`）；
- `BPlusTreeLeafPage` / `BPlusTreeInternalPage` 的键值访问接口；
- `BPlusTree<KeyType, ValueType, KeyComparator>` 的公开 API（`Insert`、`GetValue`、`Remove`、`Begin`、`Begin(key)`）；
- `IndexIterator` 的接口。

> 待核实：官方页面的具体 API 名称、是否要求实现 `Iterator`、`leaf_max_size` / `internal_max_size` 的默认值、是否要求支持重复键。

### 6.2 Agent 自行编写的教学示例

> 以下代码**非官方，仅用于说明概念**，不是 BusTub 的实现，也不构成项目答案。

**叶节点分裂示意**：

```cpp
// 非官方示例：叶节点分裂
auto LeafPage::Split() -> std::pair<LeafPage *, KeyType> {
  auto *new_leaf = AllocateLeafPage();
  size_t mid = size_ / 2;

  // 把 [mid, size_) 的键值对移到新叶
  for (size_t i = mid; i < size_; ++i) {
    new_leaf->SetKeyAt(i - mid, KeyAt(i));
    new_leaf->SetValueAt(i - mid, ValueAt(i));
  }
  new_leaf->SetSize(size_ - mid);
  size_ = mid;

  // 维护兄弟链表：new_leaf 插在 leaf 之后
  new_leaf->SetNextPageId(GetNextPageId());
  SetNextPageId(new_leaf->GetPageId());

  // 返回新叶与它的最小键（用于插入父节点）
  return {new_leaf, new_leaf->KeyAt(0)};
}
```

**内部节点分裂示意**（注意键的「提升」）：

```cpp
// 非官方示例：内部节点分裂，中间键提升到父节点
auto InternalPage::Split() -> std::pair<InternalPage *, KeyType> {
  auto *new_node = AllocateInternalPage();
  size_t mid = size_ / 2;

  // 中间键提升，不留在任何子节点
  KeyType promote_key = KeyAt(mid);

  // 把 (mid, size_) 的键与指针移到新节点
  // 注意：child[0] 没有对应的 key，所以从 mid+1 开始拷 key
  new_node->SetValueAt(0, ValueAt(mid));      // 指针 mid
  for (size_t i = mid + 1; i < size_; ++i) {
    new_node->SetKeyAt(i - mid, KeyAt(i));
    new_node->SetValueAt(i - mid, ValueAt(i));
  }
  new_node->SetSize(size_ - mid);
  size_ = mid;

  return {new_node, promote_key};
}
```

**latch crabbing 的乐观模式骨架**：

```cpp
// 非官方示例：乐观插入
bool BPlusTree::InsertOptimistic(const KeyType &key, const ValueType &value) {
restart:
  // 1. 乐观下行：全部 READ latch
  ReadPageGuard guard = bpm_->FetchPageRead(root_page_id_);
  Page *node = guard.GetPage();

  while (!node->IsLeafPage()) {
    auto *internal = reinterpret_cast<InternalPage *>(node);
    page_id_t child_pid = internal->LookupChild(key);
    ReadPageGuard child_guard = bpm_->FetchPageRead(child_pid);
    guard = std::move(child_guard);        // 释放父，持有子
    node = guard.GetPage();
  }

  // 2. 到达叶节点：检查是否需要分裂
  auto *leaf = reinterpret_cast<LeafPage *>(node);
  if (leaf->GetSize() >= leaf->GetMaxSize()) {
    // 不安全 → 悲观模式重来
    guard.Drop();
    return InsertPessimistic(key, value);   // 或 goto restart with pessimistic
  }

  // 3. 安全：升级为写锁（Drop 读 guard，重新 Fetch 写 guard）
  page_id_t leaf_pid = leaf->GetPageId();
  guard.Drop();
  auto write_guard = bpm_->FetchPageWrite(leaf_pid);

  // 4. 双重检查：升级期间别人可能改了这个叶节点
  auto *leaf2 = reinterpret_cast<LeafPage *>(write_guard.GetPage());
  if (leaf2->GetSize() >= leaf2->GetMaxSize()) {
    write_guard.Drop();
    return InsertPessimistic(key, value);
  }

  leaf2->Insert(key, value);
  return true;
}
```

**说明**：真实的 BusTub 实现中，`ReadPageGuard` 升级为 `WritePageGuard` 通常需要先 `Drop()` 再重新 `FetchPageWrite()`——因为 `std::shared_mutex` 不支持原子升级。**升级后必须双重检查**（否则会丢失其他线程在这段时间做的修改）。

**悲观插入骨架**：

```cpp
// 非官方示例：悲观插入（一路 WRITE latch，确认子节点安全才释放父）
bool BPlusTree::InsertPessimistic(const KeyType &key, const ValueType &value) {
  WritePageGuard guard = bpm_->FetchPageWrite(root_page_id_);
  std::vector<WritePageGuard> path;   // 保存路径以便向上分裂

  while (!guard.GetPage()->IsLeafPage()) {
    auto *internal = reinterpret_cast<InternalPage *>(guard.GetPage());
    page_id_t child_pid = internal->LookupChild(key);
    WritePageGuard child_guard = bpm_->FetchPageWrite(child_pid);

    // 子节点安全（未满）→ 可以释放父节点
    if (!child_guard.GetPage()->IsFull()) {
      guard.Drop();                     // 释放父
    } else {
      path.push_back(std::move(guard)); // 不安全 → 保留父节点
    }
    guard = std::move(child_guard);
  }

  // 到达叶节点，插入
  auto *leaf = reinterpret_cast<LeafPage *>(guard.GetPage());
  leaf->Insert(key, value);

  // 若叶节点溢出，沿 path 向上分裂
  if (leaf->GetSize() > leaf->GetMaxSize()) {
    SplitAndPropagate(path, guard);
  }
  return true;
}
```

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| B 树 | B+ 树 | B 树的数据存在**所有节点**；B+ 树的数据**只在叶节点**，内部节点只存分隔符 |
| 叶节点分裂 | 内部节点分裂 | 叶节点分裂**复制**中间键到父节点（键仍在叶子里）；内部节点分裂**提升**中间键（键从子节点删除） |
| 重分配 | 合并 | 重分配是「借」一个键（节点数不变）；合并是「并」两个节点（节点数减一） |
| latch | lock | latch 保护内存结构（短、无死锁检测）；lock 保护逻辑数据（长、可回滚） |
| 乐观模式 | 悲观模式 | 前者全 READ latch，冲突时重启；后者全 WRITE latch，安全但并发低 |
| 点查 | 范围扫描 | 前者走一条根到叶的路径；后者还要沿叶链表遍历 |
| B+ 树 | 哈希索引 | 前者支持范围扫描与有序遍历；后者只支持等值查询 |
| B+ 树 | LSM 树 | 前者原地更新（随机写）；后者追加写 + 后台合并（顺序写） |
| `RID` | 主键 | `RID` 是**物理位置**（page + slot）；主键是**逻辑值**。B+ 树可以建在主键上，叶节点存 `RID` |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Slides（L08 Indexes I） | `90-原始PDF/15-445/slides/08-indexes1.pdf` | 待人工核对 | B+ 树结构、查找、插入 |
| Slides（L09 Indexes II） | `90-原始PDF/15-445/slides/09-indexes2.pdf` | 待人工核对 | 删除、合并、重复键 |
| Slides（L10 Index Concurrency） | `90-原始PDF/15-445/slides/10-indexconcurrency.pdf` | 待人工核对 | latch crabbing、乐观/悲观 |
| Notes（L08/L09/L10） | `90-原始PDF/15-445/notes/` | 待人工核对 | Figure 编号待补 |
| Project #2 官方页面 | **未抓取** | — | — |

原始 URL：

- Slides：`https://15445.courses.cs.cmu.edu/fall2026/slides/08-indexes1.pdf`、`.../09-indexes2.pdf`、`.../10-indexconcurrency.pdf`
- Notes：`https://15445.courses.cs.cmu.edu/fall2026/notes/`（对应文件名待核实）
- 项目页面：`https://15445.courses.cs.cmu.edu/fall2026/project2/`（**待人工访问核对**）

> 待核实：`08-indexes1.pdf` / `09-indexes2.pdf` / `10-indexconcurrency.pdf` 的确切文件名、总页数与重点页码（`_scout/pdf-pages.json` 无 15-445 条目，需用 `=== [page N] ===` 计数）；Project #2 的任务拆解、允许修改的文件、是否分 checkpoint、是否要求支持并发。

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内，本讲内容对应 2025 年第 07/08/09 讲）

- 标题：Indexes and Filters I / II、Index Concurrency Control（2025 年第 07–09 讲）
- URL（示例，第 07 讲）：`https://www.youtube.com/watch?v=tMFAgvDViAI&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 年份：2025
- 时间戳：未核实，故不标注。

> 待核实：2025 年第 07、08、09 讲（Indexes and Filters I/II、Index Concurrency Control）的 YouTube ID。任务给定的映射表从 2026 第 14 讲开始，未覆盖第 08–10 讲。上方的 `tMFAgvDViAI` 是 2025 年第 17 讲的 ID（Concurrency Control Theory），**不是索引讲次**，此处仅作播放列表入口示意。

说明：FAQ Q11 明确 Fall 2026 的录像只对 CMU 学生开放，非 CMU 学习者应观看 Fall 2025 的公开视频。播放列表：`https://www.youtube.com/playlist?list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`

## 10. 本节复习

- 能画出三层 B+ 树的结构图，标出内部节点、叶节点、兄弟指针。
- 能叙述点查的完整流程（含二分查找）。
- 能叙述范围扫描的流程，以及迭代器需要维护哪些状态。
- 能完整叙述插入 + 叶节点分裂 + 向上传播 + 根分裂的流程。
- 能完整叙述删除 + 下溢 + 重分配/合并 + 根收缩的流程。
- 能说出叶节点分裂与内部节点分裂的**关键差别**（复制 vs 提升）。
- 能描述 latch crabbing 的乐观与悲观模式，以及乐观模式为什么需要重启。
- 能说出 B+ 树与哈希索引、LSM 树的取舍。

## 11. 自我检查

**Q1.** 为什么内部节点分裂时，中间的键要「提升」到父节点，而叶节点分裂时是「复制」？

<details><summary>参考答案</summary>

**因为内部节点的键是「分隔符」，不是数据；叶节点的键是「数据」。**

**内部节点分裂（提升）**：

内部节点 `[K1, K2, K3, K4]` 配 `[C0, C1, C2, C3, C4]`，其中 `K_i` 是「`C_i` 子树中所有键的下界」。假设 `mid = 2`，`K3`（下标 2）是中间键：

```
分裂前: K1  K2  K3  K4
        C0  C1  C2  C3  C4

分裂后:
  父节点: K3
  左子: K1  K2        （C0 C1 C2）
  右子: K4            （C3 C4）
```

**为什么 `K3` 不在任何子节点里**：`K3` 的作用是「区分左子树与右子树」——「`< K3` 走左边，`>= K3` 走右边」。一旦它被提升到父节点，这个区分作用就由父节点承担了，子节点内部**不再需要**它。如果保留在右子节点，会与父节点的分隔逻辑重复，且浪费空间。

**叶节点分裂（复制）**：

叶节点 `[K1, K2, K3, K4]` 配 `[V1, V2, V3, V4]`，`mid = 2`：

```
分裂前: K1 K2 K3 K4

分裂后:
  父节点: K3（作为分隔键）
  左叶: K1 K2
  右叶: K3 K4
```

**为什么 `K3` 要同时出现在父节点与右叶**：

1. **叶节点存的是真实数据**：`K3` 对应的 `V3` 必须能被查到。如果 `K3` 只提升到父节点而不留在叶节点，那么「查找 `K3`」会走到右叶，但右叶里没有 `K3` → **查不到**。
2. **父节点的 `K3` 只是一个「路标」**：它告诉搜索「`>= K3` 走右边」，但真正的数据在右叶里。这是**冗余**，但冗余是必要的——因为 B+ 树的所有数据必须在叶节点。

**一句话总结**：

- 内部节点的键 = **路标**（提升后原位置不需要）。
- 叶节点的键 = **数据**（必须留在叶子里，父节点只是复制一份做路标）。

**这个区别是 B 树与 B+ 树的核心差异**：B 树的内部节点也存数据，所以分裂时键也是「提升 + 保留」（类似叶节点）；B+ 树为了「所有数据在叶节点」的一致性，内部节点只存路标，所以可以「提升后删除」。

</details>

**Q2.** 乐观模式的 latch crabbing 中，为什么在叶节点发现「不安全」后必须「重启」而不能「就地升级」？

<details><summary>参考答案</summary>

**因为从根到叶的路径上，父节点的 latch 已经被释放了，而且父节点可能已被其他线程修改。**

**详细场景**：

1. 线程 A 用乐观模式下行：拿根 READ latch → 拿子 READ latch → **释放根** → 拿孙 READ latch → **释放子** → ... → 到达叶节点，只持有叶节点的 READ latch。
2. 线程 A 发现叶节点已满（需要分裂），必须修改**父节点**（插入新的分隔键）。
3. 但父节点的 latch 已经释放了！线程 A 无法安全地修改父节点。
4. 更糟的是：在线程 A 下行期间，**其他线程可能已经修改了父节点**（比如父节点也分裂了，或者子指针变了）。线程 A 记下的「路径」已经失效。

**为什么不能「就地升级」**：

1. **技术限制**：`std::shared_mutex` **不支持**原子地从读锁升级为写锁（POSIX `pthread_rwlock` 也不支持）。必须释放读锁再获取写锁——这中间有窗口。
2. **逻辑限制**：即使支持升级，父节点的 latch 已经释放了。要修改父节点，必须**重新获取**父节点的写 latch——但此时父节点的状态可能已经变了（不再是线程 A 记下的那个父节点）。
3. **路径失效**：线程 A 在下降过程中记录的「从根到叶的路径」，可能因为其他线程的分裂/合并而**不再正确**。例如，线程 A 记下「根 → 节点 X → 叶 Y」，但另一个线程可能已经把 X 分裂成 X 和 X'，Y 的父节点变成了 X'。

**所以只能重启**：

- 释放所有持有的 latch。
- 用**悲观模式**重新从根开始（一路 WRITE latch），确保路径上的节点不会被其他线程修改。
- 悲观模式下，路径是「稳定」的——因为一直持有 WRITE latch，其他线程无法插入/删除。

**为什么乐观模式仍然值得**：

- **绝大多数插入/删除是「安全」的**（叶节点未满/未下溢），乐观模式能完成，不需要重启。
- 只有「恰好触发分裂/合并」时才重启，这是**低频事件**（概率约为 `1/max_size`）。
- 所以乐观模式的**期望性能**远高于悲观模式。

**优化：混合模式（optimistic with fallback）**：

有些实现会在乐观下行时**保留父节点的 READ latch**（不释放），这样发现叶节点不安全时，可以就地升级为写锁并修改父节点。代价是「同时持有更多 latch」，但避免了完整重启。BusTub 的 P2 是否要求这种优化，待核实。

> 待核实：BusTub 的 P2 是否要求实现「乐观 + 悲观」双模式，还是只要求一种；测试是否检查并发正确性（多线程压力测试）。

</details>

**Q3.** 删除一个键后，叶节点下溢。什么情况下选择「重分配」而不是「合并」？两者对父节点的影响有何不同？

<details><summary>参考答案</summary>

**选择重分配的时机：兄弟节点有「富余」（`size > min_size`）。**

**决策流程**：

```
若 leaf.size < min_size:
    若 左兄弟存在 且 左兄弟.size > min_size:
        → 从左兄弟借最后一个键值对（重分配）
    否则若 右兄弟存在 且 右兄弟.size > min_size:
        → 从右兄弟借第一个键值对（重分配）
    否则:
        → 与左兄弟或右兄弟合并
```

**优先重分配的原因**：

1. **重分配不改变树的形状**（节点数不变，树高不变），代价小。
2. **合并会减少节点数**，可能触发父节点的下溢，进而级联合并——代价大。
3. **重分配保持空间利用率**更均匀。

**两者对父节点的影响**：

**重分配**：

- 父节点的**分隔键要更新**（因为兄弟节点与当前节点之间的边界变了）。
- 例：左兄弟 `[1, 2, 3]`、当前 `[5]`、父节点分隔键 `4`。从左兄弟借 `3`：
  ```
  左兄弟: [1, 2]
  当前:   [3, 5]
  父节点分隔键: 4 → 3    （因为当前节点的最小键变成了 3）
  ```
- **父节点的大小不变**（键的数量不变，只是值改了）。

**合并**：

- 父节点**要删除一个键与一个子指针**（因为两个子节点变成一个）。
- 例：左兄弟 `[1, 2]`、当前 `[5]`、父节点分隔键 `4`。合并：
  ```
  合并后: [1, 2, 5]      （父节点的分隔键 4 被删除）
  父节点: 删掉键 4 与指向「当前」的指针
  ```
- **父节点可能因此下溢** → 递归处理。

**内部节点的合并还有一个额外步骤**：父节点的分隔键要**下放到合并后的节点**（作为新的分隔符）。因为内部节点的键是分隔符，合并两个子树后，原来区分它们的键变成了「区分合并后节点的左右两部分」的键。

**边界情况**：

- **根节点下溢**：根是内部节点且只剩 1 个子指针 → 根收缩（用唯一的子节点替换根），树高减一。
- **根是叶节点且为空**：树变空，根仍是叶节点（不能删掉根）。
- **只有一个子节点的内部节点**：在非根位置是不合法的（违反 `min_size`），必须合并或重分配。

**实现陷阱**：

- 与左兄弟合并 vs 与右兄弟合并，**父节点要删的键下标不同**（左合并删「当前节点对应的分隔键」，右合并删「右兄弟对应的分隔键」）。
- 合并后要**更新兄弟指针**（叶节点）或**子指针**（内部节点）。
- 合并后要**释放被删节点的页**（`DeletePage`），并清理缓冲池中的映射。

</details>

**Q4.** 为什么 B+ 树要用「页」作为节点大小，而不是像内存数据结构那样用任意大小？

<details><summary>参考答案</summary>

**因为磁盘 I/O 的最小单位是页（通常 4KB），而且 B+ 树的设计目标是「最小化磁盘 I/O 次数」。**

**三个理由**：

1. **一次 I/O 读一整页**：
   - 磁盘（无论 HDD 还是 SSD）的读操作以「块」为单位（4KB 或更大）。读 1 字节和读 4KB 的代价几乎相同。
   - 如果节点小于页，一次 I/O 会浪费带宽；如果节点大于页，一次节点访问需要多次 I/O。
   - **节点 = 页** 是最优：一次 I/O 正好读入一个完整节点。

2. **扇出最大化 → 树高最小化**：
   - 树高 `h = log_m(n)`，其中 `m` 是扇出。扇出越大，树越矮，I/O 次数越少。
   - 扇出 `m ≈ 页大小 / (键大小 + 指针大小)`。4KB 页、12 字节条目 → `m ≈ 341`。
   - 若节点只有 64 字节，`m ≈ 5`，树高会大 3 倍 → I/O 次数多 3 倍。

3. **与缓冲池的配合**：
   - 缓冲池以页为单位管理内存。节点 = 页 → 节点可以直接放进缓冲池的帧，无需额外转换。
   - 如果节点大小与页不同，就需要「一个节点跨多页」或「一页装多个节点」的复杂映射。

**为什么不用「更大的节点」（如 64KB）**：

- **写放大**：修改一个键要写整个节点。节点越大，写放大越严重。
- **内存浪费**：节点被读入缓冲池时占用一个帧。节点越大，帧越大，缓冲池能装的节点越少。
- **读放大**：范围扫描时，如果节点太大，一次读入的数据大部分用不上。

**为什么不用「更小的节点」**：

- **扇出小 → 树高 → I/O 多**（见上）。
- **页是硬件的最小单位**，小于页的节点仍然占用一整页的 I/O 带宽。

**现代变体**：

- **大页（huge page）**：某些系统用 2MB 页做 B+ 树节点（减少 TLB miss），但写放大严重。
- **分层节点**：节点内部再分「热区」与「冷区」（如 Bw-tree），减少写放大。
- **LSM 树**：完全放弃「原地更新」，用追加写 + 后台合并，避免随机写——这是另一种取舍。

**一句话**：**B+ 树的节点大小 = 磁盘页大小 = 缓冲池帧大小**，这三者对齐是「一次 I/O 读一个节点、一个节点占一个帧」的前提。

</details>

## 12. 进一步学习

- 项目导航：[[00-项目总览]]
- 上一个项目：`02-Project1-Buffer-Pool.md`
- 下一个项目：`04-Project3-Query-Execution.md`
- 相关讲义：[[15-445-08-Indexes-and-Filters-I]]（B+ 树基础）、[[15-445-09-Indexes-and-Filters-II]]（删除与重复键）、[[15-445-10-Index-Concurrency-Control]]（latch crabbing）
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：
  - Comer, "The Ubiquitous B-Tree"（ACM Computing Surveys, 1979）——B 树的经典综述。
  - Graefe, "Modern B-Tree Techniques"（Foundations and Trends in Databases, 2011）——**最全面的 B+ 树工程实践**，强烈推荐。
  - Bayer & McCreight, "Organization and Maintenance of Large Ordered Indices"（1972）——B 树原始论文。
  - Lehman & Yao, "Efficient Locking for Concurrent Operations on B-Trees"（TODS 1981）——latch crabbing 的原始论文。
  - 教材 *Database System Concepts*（7th Ed.）第 14 章（Indexing）。
  - BusTub 仓库 `src/include/storage/index/` 与 `src/include/storage/page/` 下的头文件注释。
- 动手建议：先用 `leaf_max_size = 2`、`internal_max_size = 3` 跑单线程测试（容易触发所有分裂/合并路径），再逐步增大；用 `BPlusTreePrinter`（若 BusTub 提供）打印树结构验证；最后跑多线程压力测试。
- **提醒**：本篇依据课程结构公开信息 + 通用知识整理，具体任务以官方 project2 页为准。`> 待核实：` 处需人工核对。
