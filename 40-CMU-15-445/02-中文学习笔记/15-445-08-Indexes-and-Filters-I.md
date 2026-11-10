---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: L08
topic: Indexes & Filters I — B+Tree
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 数据库
  - B+树
  - 索引
  - 过滤器
  - 聚簇索引
---

# 15-445 L08：索引与过滤器 I —— B+ 树（Indexes & Filters I）

> 讲义标题写的是 "Indexes + Filters: B+Trees (aka The GOAT Data Structure)"。哈希表能 O(1) 等值查找，但完全不保序；现实中绝大多数查询需要范围扫描与排序输出，于是需要一个**保序**的索引结构。B+ 树是五十多年里没被取代的答案：它是自平衡的 m 路搜索树，把随机 I/O 转成顺序 I/O，并且几乎所有支持保序索引的现代 DBMS 都用它。

## 1. 本节学习目标

学完本讲，你应该能够：

1. 区分**索引（index）**与**过滤器（filter）**的职责，各举一个代表结构。
2. 写出 B+ 树的三个形式化性质（完美平衡、至少半满、k 个键对应 k+1 个子节点），并解释 m（fanout）的含义。
3. 画出 B+ 树的叶子节点与内部节点的布局，说明叶子值可以是 record id 也可以是元组数据，以及内部节点的键为什么只是「路标」。
4. 完整走一遍插入流程，并区分**叶子分裂时的 copy up（复制上去）**与**内部分裂时的 push up（推上去）**。
5. 完整走一遍删除流程，说明「先借后合并」的顺序，以及合并内部节点时为什么是 **pull down（拉下来）**。
6. 说明复合索引的前缀匹配规则，解释为什么 `(b=2)` 单独用不了 `(a,b,c)` 索引。
7. 区分聚簇索引与非聚簇索引，说明为什么非聚簇索引按索引顺序取元组会重复读页，以及 index scan page sorting 如何缓解。
8. 说出 B+ 树的四个设计维度（节点大小、合并阈值、变长键、节点内查找）各自的权衡。
9. 列举至少五种 B+ 树优化（指针 swizzling、Bε 树、前缀压缩、去重、后缀截断、批量构建），并说明各自省了什么。
10. 计算给定节点大小与键/指针大小下的 fanout 与树高，估算一次点查的 I/O 次数。

## 2. 前置知识

- **页与 record id**：见 [[15-445-03-Database-Storage-I]]；B+ 树的节点就是页，叶子的值通常是 RecordId。
- **缓冲池与 pin**：见 [[15-445-04-Memory-Management]]；pointer swizzling 依赖「页被 pin 住」这一事实。
- **索引组织存储**：见 [[15-445-05-Database-Storage-II]]；B+ 树可以作为表的主存储（索引组织表）。
- **哈希表与哈希索引**：见 [[15-445-07-Hash-Tables]]；本讲反复与之对比。
- **有序数组与二分查找**：B+ 树的节点内查找本质是在有序数组上做二分。

## 3. 核心概念

### 3.1 Index（索引）

表的一个属性子集上的数据结构，把这些属性**组织并/或排序**，从而定位到具体元组。索引回答「数据在哪」。代表结构：B+ 树。

### 3.2 Filter（过滤器）

回答**集合成员查询**的数据结构：告诉你某个键**（很可能）**存在于集合中，但**不告诉你它在哪**。代表结构：布隆过滤器（Bloom Filter）。

### 3.3 B+Tree（B+ 树）

自平衡的、有序的 m 路搜索树，查找、顺序访问、插入、删除均为 O(log_m n)，m 为树的扇出（fanout）。它是**完美平衡**的：所有叶子节点在同一深度。

### 3.4 Fanout（扇出）

一个节点最多能容纳的子节点数，等于「节点大小 / 每个键值对的大小」再加 1。fanout 越大，树越矮，一次点查需要的 I/O 次数越少。

### 3.5 Inner Node / Leaf Node（内部节点 / 叶子节点）

内部节点只存「键 + 子节点指针」，键充当**路标（guide post）**，用于把搜索导向正确的子树；叶子节点存「键 + 值」，值可以是 RecordId，也可以是元组数据本身。B+ 树**只在叶子节点存值**。

### 3.6 Sibling Pointer（兄弟指针）

叶子节点之间用双向链表连接（现代实现连内部节点也有）。它让范围扫描**不需要回溯到父节点**，也让分裂与合并能高效地修改相邻节点。

### 3.7 Copy Up vs Push Up（复制上去 vs 推上去）

**叶子分裂**时，中间键既留在右（或左）叶子里，又**复制**一份到父节点，所以叫 copy up。**内部分裂**时，中间键被**移走**（不再留在任何子节点），只出现在父节点，所以叫 push up。

### 3.8 Pull Down（拉下来）

合并两个内部节点时，父节点中分隔它们的那个键必须**下移**到合并后的节点里，否则这个键会丢失（因为内部节点的键不重复存在于子节点中）。

### 3.9 Composite Index（复合索引）

键由两个或更多属性组成的索引，如 `<a, b, c>`。只有当查询提供了复合键的**前导属性前缀**时，B+ 树才能被有效利用。

### 3.10 Clustered Index（聚簇索引）

表的元组**按索引键的顺序物理存储**。可以是堆存储（堆中的页按序分配）或索引组织存储（元组直接放在叶子节点里）。一个表最多一个聚簇索引。

### 3.11 Index Scan Page Sorting（索引扫描的页排序）

用非聚簇索引取元组时，按索引顺序访问会导致同一页被反复读取。DBMS 可以先收集所有匹配元组的位置，**按 page id 排序**，然后每页只取一次。

### 3.12 Pointer Swizzling（指针混写）

B+ 树节点之间用 page id 引用。若目标页已被 pin 在缓冲池中，DBMS 可以把 page id 替换成**内存裸指针**，省掉每次遍历时的页表查找。被驱逐前必须还原成 page id。

### 3.13 Prefix Compression（前缀压缩）

同一叶子节点中相邻的有序键往往共享前缀。只存一次公共前缀，每个键只存不同的后缀。示例：`robbed / robbing / robot` 共享前缀 `rob`，后缀为 `bed / bing / ot`。

### 3.14 Deduplication（去重）

非唯一索引的叶子会存多份相同键。去重后键只存一次，后面跟一个 **posting list**（该键对应的所有元组位置）。

### 3.15 Suffix Truncation（后缀截断）

内部节点的键只用于「指挥交通」，不需要完整键。只存**能正确路由**的最短前缀即可（如 `abcdefghijk` 截成 `abc`）。

### 3.16 Bulk Insert（批量构建）

为已有表建新 B+ 树的最快方式：先**排序全部键**，再从**底向上**逐层构建。叶子可以紧凑打包，也可以预留空位以便后续插入。

## 4. 通俗理解

B+ 树像一本**多级目录的电话簿**。

- 你要找姓「张」的人：先翻到「Z」那一册（根节点），再看册内页边的字母分段（内部节点），最后落到具体一页（叶子）。每一层的「分段标签」只是告诉你**往哪边走**，标签本身并不携带完整信息——这正是内部节点的键只是路标的含义。
- 每页都写满了条目，页与页之间还印着「续下页」的箭头（兄弟指针）。所以你要找「张」到「赵」之间的所有人，只要沿箭头一路往后翻，**不需要每次回到目录**。
- 某一页写满了要加人怎么办？把这一页**对半分**成两页，把中间那个名字抄一份到上一级目录里（copy up）。如果上一级目录也满了，就对半分目录，但这次中间那个名字要**从下级抽走**放到更上一级（push up）——因为它只在目录里起作用，下级不需要它。
- 有人迁走了，某页太空怎么办？先从隔壁**借**几个名字过来（顺便改一下目录里的分隔名）；隔壁也穷，就把两页**合并**，并把目录里那个分隔名**划掉**——如果合并的是目录页，那个分隔名还得**抄回**合并后的目录里（pull down），否则就丢了。

具体数字：设页大小 4 KB，键 4 B，子节点指针 4 B，则内部节点每个键值对 8 B，fanout ≈ 4096/8 = 512。一棵 3 层（根 + 2 层内部 + 叶子）的 B+ 树能索引 512³ ≈ **1.34 亿**个键——也就是说索引一亿行数据，一次点查只需 3 次页读取。

## 5. 原理与推导

### 5.1 索引与过滤器的分工

```
Index  → 键在哪里？  （保序 → 支持范围、排序）
Filter → 键可能存在吗？（不保序 → 只回答存在性，绝不返回位置）
```

两者常**配合**使用：先用布隆过滤器挡掉不可能命中的键（省掉一次磁盘 I/O），命中后再用索引定位。第 9 讲会展开过滤器（布隆过滤器、quotient filter、cuckoo filter、xor filter）。

**索引不是免费的**：每个索引都要占空间、要在每次写操作时维护、还要参与并发控制与恢复（日志）。因此「索引越多查询越快」是错的——写密集负载下，多余的索引会显著拖慢事务。这是 DBMS 需要「索引选择（index selection）」这个优化问题的原因。

### 5.2 B 树家族与 B+ 树的形式定义

讲义列的家族（`08-indexes1.pdf` 第 7 页）：

| 结构 | 年份 | 特点 |
|---|---|---|
| B-Tree | 1970 | 所有节点都存键与值 |
| B+Tree | 1973 | 只在叶子存值，内部节点只做路标 |
| B*Tree | 1977? | 分裂前先尝试把数据挪给兄弟，保持更高填充率 |
| Blink-Tree | 1981 | 加兄弟指针 + 高位键，支持无锁并发 |
| Bε-Tree | 2003 | 内部节点带缓冲，写优化（Fractal Tree） |
| Bw-Tree | 2013 | 无锁、只用 CAS 更新映射表（微软） |
| Bf-Tree | 2024 | 面向新型存储的读写优化 |

**形式定义**（m 路搜索树，m = fanout）：

```
① 完美平衡：所有叶子节点在同一深度
② 除根外每个节点至少半满：⌈m/2⌉ - 1 ≤ #keys ≤ m - 1
③ 含 k 个键的内部节点有 k+1 个非空子节点
```

讲义补一句：真实实现常常放宽这些性质（见 5.9 的合并阈值），但教学上先按理想模型讨论。

**为什么要求「至少半满」**：保证空间利用率不低于 50%，从而树高有上界。若允许任意稀疏，树可能退化成链表。**为什么要求「完美平衡」**：保证任何键的查找路径长度相同，最坏情况可预测——这对 DBMS 的延迟保证很重要。

### 5.3 节点布局

**内部节点**：

```
<node*> | <key> | <node*> | <key> | <node*> | ... | <key> | <node*>
```

n 个键把键空间切成 n+1 段，每段对应一个子节点。讲义图示用 `<20 | ≥20`、`<10 | ≥10`、`<35 | ≥35` 这样的区间标记。

**叶子节点**：

```
<K1,V1> | <K2,V2> | ... | <Kn,Vn> | Prev | Next
```

现代实现还会在页头存 `# Slots`（槽数）、`Level`（层级，用于判断是不是叶子）、`High Key`（该节点的上界，Blink-Tree 引入，用于并发分裂时判断键是否已迁走）。

**叶子值的两种方案**：

| 方案 | 说明 | 使用场景 |
|---|---|---|
| Record ID | 指向元组位置的指针 | 最常见（堆存储的表） |
| Tuple Data | 直接存元组内容 | 索引组织存储的主键索引；二级索引存主键值 |

**内部节点的键可能不在叶子上**：这是 B+ 树与 B-Tree 的关键差异之一。插入时 copy up 的键会留在叶子；但删除时从叶子移除的键**可能仍留在内部节点**作为路标。所以「在索引里找不到某个键」不能靠检查内部节点判断，必须走到叶子。

**NULL 的处理**：所有 NULL 键集中放在**第一个或最后一个**叶子节点（对应 `NULLS FIRST` / `NULLS LAST`）。

### 5.4 B-Tree 与 B+ 树的对比

| 维度 | B-Tree (1970) | B+Tree (1973) |
|---|---|---|
| 值的存放位置 | 所有节点 | 仅叶子 |
| 键的重复 | 每个键只出现一次 | 内部节点的键可能是叶子键的副本 |
| 空间效率 | 更高 | 略低（路标占空间） |
| 并发访问 | 更难（修改可能发生在任意层） | 更容易（值只在叶子，分裂模式规整） |
| 范围扫描 | 需中序遍历，回溯多 | 沿叶子链即可 |
| 删除 | 直接从所在节点删 | 必须从叶子删，内部可能残留 |

### 5.5 插入：copy up 与 push up 的区别

**算法**：

```
1. 从根开始，按内部节点的键导航，找到键所属的叶子 L
2. 在 L 中按序插入该条目
3. 若 L 未满 → 完成
4. 若 L 满 → 把 L 的条目均分成 L 与 L2，中间键 copy up 到父节点
5. 父节点插入指向 L2 的条目；若父满 → 递归分裂
6. 若根满 → 分裂根，树高 +1
```

**讲义示例（插入 6，`08-indexes1.pdf` 第 38–53 页）**：目标叶子区间是 `[4,12)`，已满。分裂后得到 `[4,9)` 与 `[9,12)` 两个叶子，中间键 9 **复制**到父节点，父节点的区间标记从 `<4 | ≥4 ...` 变为 `<4 | [4,9) | [9,12) | ≥12`。

**讲义示例（插入 16、17，第 57–75 页，讲内部分裂）**：

```
初始：根 = [9, 13, 19]，叶子 9,11 | 13,14,15 | 20,21,23
Insert 17 → 落到叶子 13,14,15 → 变为 13,14,15,17（满）
Insert 16 → 该叶子无空间 → 分裂为 13,14,15 与 16,17
   → 中间键 16 copy up 到根 → 但根 [9,13,19] 已满！
   → 此时 16,17 是「孤儿节点」（orphan）：没有父节点指向它
   → 分裂根：把根的中间键 13 push up 成新根
   → 根分裂为 [9,11] 与 [16,19] 两个内部节点，新根 = [13]
   → 树高 +1
最终：新根 [13]；左内部 [9,11] 指 9,11 与 13,14,15；
      右内部 [16,19] 指 16,17 与 20,21,23
```

**关键对比**：

```
叶子分裂：中间键既留在右叶子，又复制一份到父节点  → copy up
内部分裂：中间键从节点移走，只放在父节点          → push up
```

**为什么不同**：叶子的中间键是**真实数据**（有对应的元组），必须留在叶子里才能被查到；内部节点的键只是**路标**，不承载数据，移走不影响正确性。

### 5.6 删除：先借后合并，pull down

**算法**：

```
1. 找到键所在的叶子 L，删除该条目
2. 若 L 仍至少半满 → 完成
3. 若 L 欠满（underfull）：
   a. 尝试向相邻兄弟（同父）借一个条目，并更新父节点中的分隔键
   b. 借不到（兄弟也只有半满）→ 合并 L 与兄弟
4. 若发生合并 → 从父节点删除指向被合并节点的条目
5. 若父节点因此欠满 → 递归处理
6. 若根只剩一个子节点 → 删除根，树高 -1
```

**讲义三个删除示例**：

- **示例 1（第 77–86 页）**：删除 6。目标叶子欠满，从「富裕」的兄弟借一个条目，父节点的分隔键从 `≥4` 更新为 `≥9`（再后来是 `≥12`）。注意：**借必须同时更新父键**，否则路由会错。
- **示例 2（第 87–93 页）**：删除 15，同样是从富裕兄弟借，父键从 13 更新为 17。
- **示例 3（第 94–104 页）**：删除 15 后再删除 19。此时两个兄弟都只有半满，**没有富裕兄弟可借**，于是合并。合并叶子后，父节点中的分隔键被删除；父节点因此欠满，又触发**内部节点的合并**——此时必须把父节点中的分隔键 **pull down** 到合并后的节点里。最终树高从 3 降到 2（"The tree has shrunk in height"）。

**为什么内部合并必须 pull down**：内部节点的键不出现在子节点中（不同于叶子的 copy up）。若合并两个内部节点时只删掉父键，这个键就彻底消失了，而它可能仍对应着某个叶子里的真实键。把它下移到合并后的内部节点，才能保住路由信息。

### 5.7 复合索引与前缀匹配

```sql
CREATE INDEX my_idx ON xxx (a, b DESC, c NULLS FIRST);
```

索引键是 `<a, b DESC, c NULLS FIRST>` 这个**有序元组**。B+ 树按字典序排列这些元组，因此：

| 查询条件 | 能否用索引 | 原因 |
|---|---|---|
| `a=1 AND b=2 AND c=3` | ✓ 完整匹配 | 精确定位到单个键 |
| `a=1 AND b=2` | ✓ 前缀匹配 | 对应一个连续区间 |
| `a=1` | ✓ 前缀匹配 | 对应一个连续区间 |
| `b=2` | ✗（很少支持） | b 不是前导属性，满足条件的键分散在整个键空间 |
| `c=3` | ✗（很少支持） | 同上 |
| `a=1 AND c=3` | 部分 | 只能用 `a=1` 缩小范围，再过滤 c |

**为什么非前缀用不了**：B+ 树只保证「按 (a,b,c) 字典序」的连续性。`b=2` 的键可能出现在任意 a 值之下，即键空间中**不连续**的多段，无法用一次范围扫描覆盖。

**skip scan**：少数 DBMS（如 Oracle、DuckDB）实现了「跳过前导属性」的扫描——若前导属性基数很低（比如只有 3 个不同值），就对外层每个取值各做一次 `(b,c)` 的范围扫描。讲义把 `Skip Scans` 标在复合索引页上，属于「部分 DBMS 支持」的范畴。

**哈希索引的对比**：哈希索引一般要求**完整的搜索键等值条件**——`(a,b,c)` 的哈希索引无法回答 `a=1`，因为哈希打散了前缀关系。

**讲义的选择条件图示（第 110–122 页）**：用二维键 `(x, y)` 演示。`Find (1,2)` 是精确点查；`Find (1,*)` 是一段连续区间（`1 ≤ 1` 且 `(1,*) ≤ (2,*)`）；而 `Find (*,1)` 命中的键分散在各处（`(*,1)` 在每行第一列下各有一个），必须逐段查找。

### 5.8 聚簇索引与非聚簇索引

**聚簇索引（clustered index）**：表的元组按索引键顺序存储。

- 可以是**堆存储**（页按主键顺序分配）或**索引组织存储**（元组放在叶子节点里）。
- 某些 DBMS **强制**使用聚簇索引：若表没有主键，就自动造一个隐藏主键（如 InnoDB 的隐式 row id）。
- 另一些 DBMS 根本不支持聚簇索引（如某些列存系统，或只能通过排序重写表来近似）。

**全表顺序扫描的最优方式**：走到**最左叶子**，然后沿兄弟指针遍历所有叶子。这比「每次查询都排序」永远更好——因为排序是 O(n log n)，而沿叶子链是 O(n)。

**非聚簇索引的问题**：索引顺序与元组的物理顺序不一致。按索引顺序取元组会**反复读同一页**：

```
索引顺序给出: Page 102, 103, 102, 104, 104, 103, 102, 101, 104, 103, ...
→ 页 102 被读了 4 次、103 被读 4 次……缓存不命中时每次都是随机 I/O
```

**Index Scan Page Sorting 的解法**：

```
1. 遍历索引，收集所有匹配元组的位置（不立即取元组）
2. 按 page id 排序这些位置
3. 逐页取出，每页只读一次
   排序后: 101, 102, 102, 102, 102, 103, 103, 103, 103, 104, ...
```

代价是引入一次内存排序（可能溢写磁盘），但省掉了重复的随机 I/O。当匹配元组很多时收益巨大；当只有一两条时排序开销反而多余，因此优化器会按选择率决定是否启用。

**选择率与聚簇的交互**：非聚簇索引在**低选择率**（返回少量元组）时很好；选择率高时（比如返回 20% 的行）顺序扫描往往更快，因为随机 I/O 太多。

### 5.9 四个设计维度

**① 节点大小（node size）**

```
存储设备越慢，最优节点越大
HDD:       ~1 MB
SSD:       ~10 KB
In-Memory: ~512 B
```

原因：大节点减少树高（减少 I/O 次数），但每次读入的无效数据更多。HDD 的每次 I/O 有很高的固定开销（寻道 + 旋转），所以值得一次多读；内存里没有 I/O 开销，只有缓存行利用率，所以小节点更好。

**权衡还与工作负载有关**：叶子扫描偏好大节点（顺序读更连续）；根到叶的遍历偏好小节点（每层读得少）。同一棵树的不同层甚至可以用不同大小。

**② 合并阈值（merge threshold）**

不是所有 DBMS 都在节点降到半满时立刻合并。讲义给的数据：**B+ 树节点的平均占用率约 69%**（这是随机插入下的理论值）。延迟合并的好处：

- 减少重组次数（避免「刚合并又分裂」的抖动 / thrashing）；
- 减少写 latch 的持有时间（对并发友好）；
- 可以让欠满节点存在，**周期性整树重建**。

PostgreSQL 因此把自己的 B+ 树叫 **"non-balanced" B+Tree（nbtree）**——它不保证严格平衡。

**③ 变长键（variable-length keys）**

| 方案 | 做法 | 代价 |
|---|---|---|
| Pointers | 键存成指向元组属性的指针（内存 DBMS 中叫 T-Tree） | 多一次间接访问 |
| Variable-Length Nodes | 节点大小可变 | 内存管理复杂，页大小不再固定 |
| Padding | 填充到该类型的最大长度 | 空间浪费严重 |
| Key Map / Indirection | 节点内嵌一个指针数组，指向「键+值」列表 | 多一层间接，但键可紧凑存放 |

**④ 节点内查找（intra-node search）**

| 方案 | 复杂度 | 特点 |
|---|---|---|
| Linear | O(n) | 顺序比较，可用 **SIMD** 向量化（讲义示例 `_mm_cmpeq_epi32_mask(a, b)`） |
| Binary | O(log n) | 跳中间、按比较结果左右走；插入时要移动元素，代价高 |
| Interpolation | O(log log n) 期望 | 按键的已知分布**估算**位置；只适合整数等有良好分布的类型，主要见于学术系统 |

**插值查找的推导**（`08-indexes1.pdf` 第 158 页）：在 `[4, 10]` 之间找 8，

```
Offset = (8 - 4) × 7 / (10 - 4) = 4
```

即估计目标在偏移 4 处，直接跳过去检查。若键分布均匀，一次就命中；分布偏斜时退化。

### 5.10 六种优化

**① Pointer Swizzling**

```
问题：节点用 page id 引用彼此，每次遍历都要查页表（page id → frame）
优化：若目标页已 pin 在缓冲池，把 page id 换成内存裸指针
代价：必须跟踪哪些指针被 swizzle 过，页被驱逐前还原成 page id
```

讲义图示（第 162–170 页）：遍历 `Find Key>3` 时，先把 Page #2 的引用 swizzle 成 `<Page*>`，再 swizzle Page #3，之后的路由不再需要页表查找。

**② Write-Optimized B+Tree（Bε-Tree / Fractal Tree）**

```
问题：修改 B+ 树可能触发分裂/合并，最坏要重组整棵树；
      而且做这件事的是「引发分裂的那个 worker」，它必须等
想法：能否延迟对结构的更新，把多个改动批量应用？
做法：内部节点带 log buffer（mod log），更新先写进 buffer，
      不立即下推；buffer 满了才**增量**级联下推到下层节点
```

好处：把随机写变成顺序写，写放大降低，延迟更平滑。代价：读要检查沿途所有 buffer（读放大）。

**③ Partial Indexes（部分索引）**

只对满足条件的行建索引（如 `WHERE status='active'`），减小索引体积、降低维护成本。讲义在优化列表里提到但未展开。

**④ Include Columns（包含列）**

把非键列附加到叶子节点，使某些查询可以**只扫索引**（covering index）而不回表。同样只在列表中提及。

**⑤ Prefix Compression（前缀压缩）**

同一叶子的有序键共享前缀。`robbed / robbing / robot` → 前缀 `rob` + 后缀 `bed / bing / ot`。省空间 → 提高 fanout → 降低树高。变体很多（整节点一个前缀、每几个键一组前缀等）。

**⑥ Deduplication（去重）**

```
未去重：K1,V1 | K1,V2 | K1,V3 | K2,V4
去重后：K1,[V1,V2,V3] | K2,[V4]
```

对非唯一索引效果显著。讲义注明「同样的思想也适用于哈希表」。

**⑦ Suffix Truncation（后缀截断）**

内部节点的键只需能正确路由。`abcdefghijk` 与 `lmnopqrstuv` 两个分隔键，只需存 `abc` 与 `lmn` 就能区分左右子树。省空间，提高 fanout。

**⑧ Bulk Insert（批量构建）**

```
朴素做法：逐个插入 n 个键 → 每次 O(log n)，且大量随机 I/O 与分裂
批量做法：① 排序全部键（外部排序）
         ② 自底向上构建：按顺序填满叶子，记录每层的分隔键
         ③ 递归构建上层
```

复杂度从 O(n log n) 次随机写降到「排序 + 一次顺序写」。叶子可以**紧凑打包**（填充率 100%，但后续插入立刻分裂）或**留空**（如填充 70%，给未来插入留余地）。这是 `CREATE INDEX` 和 `LOAD DATA` 的标准实现。

### 5.11 树高与 I/O 次数的估算

设页大小 P、键大小 K、子节点指针大小 R（叶子值大小 V）。

```
内部节点 fanout:  m ≈ P / (K + R)
叶子节点容量:      L ≈ P / (K + V)
树高 h（叶子为第 1 层）:  m^(h-1) × L ≥ N
点查 I/O 次数 ≈ h（根通常常驻内存，实际 h-1）
```

**例 1**：P = 4 KB，K = 4 B，R = 4 B，V = 8 B（RecordId）

```
m = 4096 / 8 = 512
L = 4096 / 12 ≈ 341
N = 1 亿 → 需要 m^(h-1) × L ≥ 1e8
h = 3: 512² × 341 ≈ 8.9e7  ← 略不够
h = 4: 512³ × 341 ≈ 4.6e10 ← 足够
→ 约 3–4 层，点查 3–4 次页读取
```

**例 2**：P = 1 MB（HDD 优化），K = 4 B，R = 4 B

```
m = 1048576 / 8 = 131072
h = 3 时可索引 131072² × L ≈ 1.7e10 × L，远超一亿
→ 两层内部节点足够，点查 2–3 次 I/O
```

这就是「设备越慢、节点越大」的量化理由：HDD 上一次 I/O 约 10 ms，把 4 次降到 2 次就省 20 ms；而 SSD 上一次 I/O 约 100 µs，省 200 µs，代价是每次多读 1 MB（内存带宽与缓存污染）。

## 6. 代码示例

### 6.1 讲义原文示例

**索引与过滤器的定义**（`08-indexes1.pdf` 第 4 页）：

```
An index data structure of a subset of a table's attributes that are
organized and/or sorted to the location of specific tuples using those
attributes.
  → Example: B+Tree

A filter is a data structure that answers set membership queries; it
tells you whether a key (likely) exists in a set but not where it is
located.
  → Example: Bloom Filter
```

**B+ 树的三个性质**（第 17 页）：

```
A B+Tree is a self-balancing, ordered m-way tree for searches,
sequential access, insertions, and deletions in O(logm n) where m is
the tree fanout.
  → It is perfectly balanced (every leaf node is at the same depth)
  → Every node other than the root is at least half-full
        ⌈m/2⌉-1 ≤ #keys ≤ m-1
  → Every inner node with k keys has k+1 non-null children
  → Optimized for reading/writing large data blocks.
```

**节点布局**（第 21–25、31–32 页）：

```
Inner node:  <node*>|<key>|<node*>|…|<key>|<node*>

Leaf node:   K1 | V1 | • • • | Kn | Vn | Prev | Next
             # | Level | # | Slots | Kx | High Key
```

**插入算法**（第 37 页，Source: Chris Re）：

```
1. Find correct leaf node L.
2. Insert data entry into L in sorted order.
3. If L has enough space, done!
4. Otherwise, split L keys into L and a new node L2
   → Redistribute entries evenly, copy up middle key.
   → Insert index entry pointing to L2 into parent of L.
5. To split inner node, redistribute entries evenly, but push up middle key.
```

**删除算法**（第 76 页，Source: Chris Re）：

```
1. Start at root, find leaf L where entry belongs.
2. Remove the entry.
3. If L is at least half-full, done!
4. Otherwise, L is underfull
   → Try to re-distribute, borrowing from sibling (adjacent node
     with same parent as L).
   → If re-distribution fails, merge L and sibling.
5. If merge occurred, must delete entry (pointing to L or sibling)
   from parent of L.
```

**复合索引**（第 105–107 页）：

```
A composite index is when the key is comprised of two or more attributes.
  → Example: Index on <a,b,c>
DBMS can use B+Tree index if the query provides a "prefix" of composite key.
  → Supported: (a=1 AND b=2 AND c=3)
  → Supported: (a=1 AND b=2)
  → Rarely Supported: (b=2), (c=3)

CREATE INDEX my_idx ON xxx (a, b DESC, c NULLS FIRST);
```

**Index Scan Page Sorting**（第 127 页）：

```
Retrieving tuples in the order they appear in a non-clustered index is
inefficient due to redundant reads. A better approach is to find all the
tuples that the query needs and then sort them based on their page ID.
The DBMS retrieves each page once.
```

**节点大小建议**（第 135 页）：

```
The slower the storage device, the larger the optimal node size for a B+Tree.
  → HDD: ~1MB
  → SSD: ~10KB
  → In-Memory: ~512B
```

**合并阈值**（第 136 页）：

```
Some DBMSs do not always merge nodes when they are half full.
  → Average occupancy rate for B+Tree nodes is 69%.
  → Delaying a merge operation may reduce the amount of reorganization.
  → This is why PostgreSQL calls their B+Tree a "non-balanced" B+Tree (nbtree).
```

**变长键四方案**（第 137 页）：

```
Approach #1: Pointers → T-Trees (in-memory DBMSs)
Approach #2: Variable-Length Nodes → requires careful memory management
Approach #3: Padding → always pad the key to max length of the key type
Approach #4: Key Map / Indirection → embed an array of pointers that map
            to the key + value list within the node
```

**节点内查找三方案**（第 141 页）：

```
Approach #1: Linear → scan node keys from beginning to end; use SIMD
Approach #2: Binary → jump to middle key, pivot left/right
Approach #3: Interpolation → approximate location based on known distribution
```

**指针混写**（第 162 页）：

```
Nodes use page ids to reference other nodes in the index. The DBMS must
get the memory location from the page table during traversal. If a page is
pinned in the buffer pool, then DBMS can store raw pointers instead of page
ids. This avoids address lookups from the page table.
```

**写优化 B+ 树**（第 172 页）：

```
Instead of immediately applying updates, store changes to key/value entries
in log buffers at inner nodes.
  → aka Fractal Trees / Bε-trees.
  → Updates cascade down to lower nodes incrementally when buffers get full.
```

**前缀压缩与后缀截断**（第 181–188 页）：

```
Prefix Compression:  robbed / robbing / robot  →  Prefix: rob
                     suffixes: bed / bing / ot
Suffix Truncation:   abcdefghijk → abc
                     lmnopqrstuv → lmn
```

**批量构建**（第 189–191 页）：

```
The fastest way to build a new B+Tree for an existing table is to first
sort the keys and then build the index from the bottom up.
  Keys: 3, 7, 9, 13, 6, 1
  Sorted Keys: 1, 3, 6, 7, 9, 13
```

### 6.2 补充示例（非官方，仅用于说明概念）

**B+ 树查找伪代码**：

```
def search(node, key):
    if node.is_leaf:
        i = binary_search(node.keys, key)
        return node.values[i] if i >= 0 else None
    # 内部节点：找到最后一个 <= key 的分隔键
    i = upper_bound(node.keys, key) - 1
    child = node.children[max(i, 0)]
    return search(read_page(child), key)
```

注意内部节点的 `child` 是 page id，需要 `read_page` 走缓冲池；这就是 pointer swizzling 想省掉的那一步。

**叶子分裂伪代码**：

```
def split_leaf(L):
    mid = len(L.keys) // 2
    L2 = new_leaf()
    L2.keys, L2.values = L.keys[mid:], L.values[mid:]
    L.keys, L.values = L.keys[:mid], L.values[:mid]
    L2.next = L.next; L2.prev = L
    if L.next: L.next.prev = L2
    L.next = L2
    copy_up_key = L2.keys[0]        # 中间键复制上去，仍留在 L2
    parent_insert(L.parent, copy_up_key, L2)
```

**内部分裂伪代码（对比 push up）**：

```
def split_inner(N):
    mid = len(N.keys) // 2
    push_up_key = N.keys[mid]       # 中间键被移走，不留在任何子节点
    N2 = new_inner()
    N2.keys = N.keys[mid+1:]
    N2.children = N.children[mid+1:]
    N.keys = N.keys[:mid]
    N.children = N.children[:mid+1]
    parent_insert(N.parent, push_up_key, N2)
```

**合并内部节点（pull down）伪代码**：

```
def merge_inner(left, right, parent, sep_index):
    sep_key = parent.keys[sep_index]          # 父中的分隔键
    left.keys = left.keys + [sep_key] + right.keys   # pull down
    left.children = left.children + right.children
    parent.remove(sep_index)                  # 删父中的键与右指针
    if parent.underfull():
        rebalance(parent)
```

**树高估算脚本思路（非官方）**：

```
page = 4096; key = 4; ptr = 4; val = 8
m = page // (key + ptr)          # 512
L = page // (key + val)          # 341
for h in range(1, 8):
    capacity = (m ** (h - 1)) * L
    print(h, capacity)
# 输出可看出 1 亿行需要 4 层
```

## 7. 容易混淆的概念

| 概念对 | 区别 | 记忆要点 |
|---|---|---|
| Index vs Filter | 索引给出**位置**且保序；过滤器只回答**可能存在** | 一个定位，一个筛查 |
| B-Tree vs B+Tree | 前者所有节点存值、键不重复；后者只在叶子存值、内部键是副本 | 一个处处有值，一个只在叶 |
| Copy Up vs Push Up | 叶子分裂复制中间键（键仍留在叶子）；内部分裂移走中间键 | 叶子留副本，内部只上路 |
| 借（redistribute）vs 合并（merge） | 借只移动一个条目并更新父键；合并删除父条目（内部合并还要 pull down） | 先借后合，合要下移 |
| 聚簇 vs 非聚簇索引 | 前者元组按索引顺序物理存放（表最多一个）；后者顺序无关 | 一个决定物理序，一个只是附加 |
| 复合索引前缀 vs 任意属性 | 只有前导前缀能用；非前缀键在键空间不连续 | 前缀连续，非前缀散乱 |
| Pointer Swizzling vs Page Table | swizzling 把 page id 换成裸指针，**依赖页被 pin**；页表始终存在 | 一个缓存指针，一个查表 |
| Prefix Compression vs Suffix Truncation | 前者压**叶子**的键（省空间提 fanout）；后者截**内部**的路标键 | 叶子压前缀，内部截后缀 |
| 立即合并 vs 延迟合并 | 立即合并保证严格半满但易抖动；延迟合并提高吞吐但允许欠满 | 一个严格，一个宽松 |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Slides | `90-原始PDF/15-445/slides/08-indexes1.pdf` | 195 | 2（Project #1 due Sept 27、DRC #1 Oct 5、期中 Oct 7 覆盖 L01–11）、3（上讲回顾）、4（索引 vs 过滤器定义）、6（今日议程）、7（B 树家族年表）、17（B+ 树形式定义）、18–25（B+ 树示例与节点布局）、26（节点组成与 NULL 处理）、27–32（叶子节点布局与 High Key）、34–35（叶子值的两种方案）、36（B-Tree vs B+Tree）、37（插入算法）、38–56（插入示例 1：叶子分裂）、57–75（插入示例 2/3：内部分裂、孤儿节点、根分裂）、76（删除算法）、77–86（删除示例 1：借）、87–93（删除示例 2：借并更新父键）、94–104（删除示例 3：合并、pull down、树高下降）、105–108（复合索引与前缀、skip scan）、110–122（选择条件二维图示）、123–126（聚簇索引与聚簇 B+ 树扫描）、127–132（index scan page sorting）、133–140（设计选择：节点大小、合并阈值、变长键）、141–160（节点内查找：线性/SIMD/二分/插值，含 offset 公式）、161–170（指针混写）、171–180（写优化 B+ 树 / Bε 树）、181–184（前缀压缩）、185–188（去重、后缀截断）、189–193（批量构建）、194（结论）、195（下讲预告：布隆过滤器、Trie、跳表、倒排索引、向量索引） |
| Notes | `90-原始PDF/15-445/notes/08-indexes1.pdf` | 8 | 第 1 页（索引与过滤器定义、索引数量的权衡、B+ 树概述与 B-Tree 差异）、第 2 页（形式定义三条性质、叶子值的两种表示、内部键作为 guide post、NULL 处理、兄弟指针）、第 3 页（插入算法与 copy up / push up 的区别）、第 4 页（删除算法与 pull down）、第 5 页（复合索引与前缀匹配、聚簇索引）、第 6 页（index scan page sorting、节点大小与合并阈值）、第 7 页（变长键四方案、节点内查找三方案）、第 8 页（六种优化：swizzling、Bε 树、前缀压缩、去重、后缀截断、批量构建） |

原始 URL：

- Slides：`https://15445.courses.cs.cmu.edu/fall2026/slides/08-indexes1.pdf`
- Notes：`https://15445.courses.cs.cmu.edu/fall2026/notes/08-indexes1.pdf`

> 待核实：slides 第 161 页的优化列表包含 `Partial Indexes` 与 `Include Columns`，但后续页面只展开了 pointer swizzling、Bε 树、前缀压缩、去重、后缀截断、批量构建六项，未找到部分索引与包含列的专门页面；可能只在口头讲解中出现。
> 待核实：slides 第 57–75 页的插入示例中，讲义同时标注了 "Copy the middle key" 与 "Push the key up"，措辞可能针对不同层级的操作；本笔记按「叶子 copy up、内部 push up」的标准定义叙述，需人工核对讲义原意。
> 待核实：notes 与 slides 对「平均占用率 69%」的出处未标注来源（该数值通常归于 Yao 1978 或 Comer 1979 的随机插入分析）。

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内，本讲内容对应 2025 年第 8 讲）

- 标题：Indexes & Filters I — B+Tree（2025 年第 8 讲）
- URL：`https://www.youtube.com/watch?v=u7ii_Lvm9rM&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 年份：2025
- 时间戳：未核实，故不标注。

## 10. 本节复习

- 能说出索引与过滤器的分工，并解释为什么两者常配合使用。
- 能默写 B+ 树的三个形式化性质，并说明「至少半满」与「完美平衡」各自保证了什么。
- 能画出内部节点与叶子节点的布局，说明 High Key、Level、Slots 三个页头字段的用途。
- 能完整走一遍插入，明确指出哪一步是 copy up、哪一步是 push up，以及「孤儿节点」是怎么产生的。
- 能完整走一遍删除，说明「先借后合并」的顺序、为什么借要更新父键、为什么内部合并要 pull down。
- 能判断给定复合索引 `(a,b,c)` 下哪些 WHERE 条件能用索引，并解释 skip scan 的原理与限制。
- 能区分聚簇与非聚簇索引，说明 index scan page sorting 解决什么问题、代价是什么。
- 能说出四个设计维度的权衡，特别是「设备越慢节点越大」的原因。
- 能列举六种优化，并说明每种优化省掉的是空间、I/O 还是 CPU。
- 能给定页大小与键/指针大小估算 fanout、树高与点查 I/O 次数。

## 11. 自我检查

**Q1.** B+ 树插入时，叶子分裂用 copy up，内部分裂用 push up。为什么两者不同？如果叶子分裂也用 push up 会怎样？

<details><summary>参考答案</summary>

**为什么不同**：叶子的键是**真实数据**，每个键都对应一个（或多个）元组，必须留在叶子中才能被查到。所以分裂叶子时，中间键既留在右（或左）叶子里，又**复制**一份到父节点作为路由用的分隔键——这就是 copy up。

内部节点的键只是**路标（guide post）**，不承载数据。一个键在内部节点出现，只表示「左子树的键都小于它、右子树都大于等于它」。因此分裂内部节点时，中间键可以从原节点**移走**，只放到父节点，不违反任何不变量——这就是 push up。移走后，两个子节点各自的路由范围仍然正确。

**如果叶子分裂也用 push up**：那个中间键会从叶子中消失，而它对应的元组就再也无法通过索引查到（索引与表失去同步）。例如叶子 `[13,14,15,17]` 分裂时把 15 推到父节点，叶子变成 `[13,14]` 与 `[17]`，那么 `WHERE k=15` 的查询沿父节点的路标 15 往下走，却找不到 15 这个键，只能返回空——**索引漏数据**，这是最严重的正确性错误。

反过来，如果内部分裂用 copy up（键同时留在子节点），也不会有正确性问题，但会浪费空间（路标重复），且会让「内部节点的键是叶子的副本」这一性质更混乱，删除时的维护逻辑也更复杂。

</details>

**Q2.** 删除一个键后叶子欠满。请说明「先借后合并」的完整流程，并解释为什么合并两个**内部**节点时必须把父节点的分隔键 pull down。

<details><summary>参考答案</summary>

**流程**：

1. 找到键所在叶子 L，删除该条目。
2. 若 L 仍至少半满（`⌈m/2⌉-1 ≤ #keys`），结束。
3. 否则尝试向**同父的相邻兄弟**借一个条目：
   - 从左兄弟借最大的那个（或从右兄弟借最小的），移到 L；
   - **必须更新父节点中分隔 L 与兄弟的那个键**，否则路由会错——这是最容易漏的一步，讲义第 83–86 页专门标注 "Need to update parent node!"。
4. 若两个兄弟都只有半满（没有「富裕」兄弟可借），就**合并** L 与一个兄弟：
   - 把两个叶子的条目合并到一个节点；
   - 从父节点**删除**指向被合并掉的那个节点的条目（键 + 指针）；
   - 修复叶子链表的兄弟指针。
5. 父节点因删除条目而欠满 → 递归执行 3–4。
6. 若根只剩一个子节点 → 删除根，树高减 1（讲义第 103 页 "The tree has shrunk in height"）。

**为什么内部合并必须 pull down**：

内部节点的键**不出现在子节点中**（这是与叶子 copy up 的根本差异）。设父节点 P 有键 k，把左子 A 与右子 B 合并。k 原本的作用是分隔 A 与 B：A 中所有键 < k ≤ B 中所有键。合并后 A∪B 成为同一个节点，不再需要 k 来分隔它们。

但如果直接**丢弃** k，就会丢失信息：k 可能对应着某个叶子中真实存在的键（内部键是「路标」，其值可能等于某叶子键，也可能只是路由用的近似值）。更重要的是，丢弃 k 会破坏「子树键范围」的完整性——某些落在 k 附近的键可能既不在 A 也不在 B 的范围内，路由就会失效。

正确做法是把 k **下移**到合并后的节点中（pull down），使它成为该节点内部的一个键，继续分隔它自己的左右子树。这样合并后节点的键集合完整保留了 A 的键、k、B 的键，路由关系不变。

**与叶子的对比**：叶子合并时，父节点的分隔键是叶子键的**副本**（因为当初是 copy up），所以合并后删掉它不丢信息——真实数据仍在叶子里。内部合并时父键是**唯一副本**（因为当初是 push up），必须 pull down 保住。

</details>

**Q3.** 有复合索引 `CREATE INDEX idx ON t (a, b, c)`。判断下列查询能否有效使用该索引，并说明理由：①`a=1 AND b=2`；②`b=2 AND c=3`；③`a>1 AND b=2`；④`a=1 AND c=3`。

<details><summary>参考答案</summary>

索引键是三元组 `(a,b,c)`，B+ 树按字典序排列，因此**只有前导属性的前缀能对应连续区间**。

① **`a=1 AND b=2` — 能用，前缀匹配。** 所有 `(1,2,*)` 的键在索引中连续排列，可用一次范围扫描 `[(1,2,-∞), (1,2,+∞))` 取出。c 未指定不影响。

② **`b=2 AND c=3` — 不能有效使用。** b 不是前导属性。满足 `b=2` 的键分散在 a 的每个取值之下，即键空间中**不连续的多段**，B+ 树无法用一次范围扫描覆盖。少数 DBMS 的 **skip scan** 可以缓解：若 a 的基数很低（如只有 3 个值），就对 a 的每个取值各做一次 `(2,3)` 的范围扫描——但这需要额外遍历，且 a 基数高时完全不可行。

③ **`a>1 AND b=2` — 部分使用。** 可以用 `a>1` 做范围扫描，把范围缩到 a>1 的所有键；但 b=2 无法在索引层过滤（因为在 a>1 的前提下，b 的取值在每个 a 下都重新开始，不是连续的），必须在取回元组后**逐条过滤**。效果远不如 ①。

④ **`a=1 AND c=3` — 部分使用。** 用 `a=1` 缩小到 `(1,*,*)` 的连续区间，然后在这段区间内扫描并过滤 `c=3`（因为 b 未指定，c 的取值在 b 的每个取值下重新开始）。比全表扫描好，但不如 ①。

**延伸**：若这类查询频繁出现，应考虑建 `(a,c)` 或 `(b,c)` 索引，而不是依赖一个宽索引。这也说明索引设计必须基于实际查询模式，而非「索引越多越好」。

</details>

**Q4.** 为什么非聚簇索引按索引顺序取元组效率低？index scan page sorting 如何解决？它在什么情况下反而更慢？

<details><summary>参考答案</summary>

**为什么低效**：非聚簇索引的键顺序与元组的物理页顺序**无关**。按索引顺序逐个取元组，会得到类似 `102, 103, 102, 104, 104, 103, 102, 101, ...` 的页访问序列（讲义第 130 页）。同一个页被反复读取：若页仍在缓冲池里，代价只是 latch 与查找开销；若已被驱逐，每次都是一次**随机 I/O**。返回的元组越多，重复读越严重——最坏情况是「每个元组一次随机 I/O」。

**解法（index scan page sorting）**：

1. 先只遍历索引，把**所有匹配元组的位置**（RecordId）收集到内存列表，**不立即取元组**。
2. 按 **page id 排序**这个列表。
3. 按排序后的顺序逐页取元组，**每页只读一次**，页内按需过滤。

排序后访问序列变成 `101, 102, 102, 102, 102, 103, 103, 103, 103, 104, ...`，随机 I/O 变成顺序 I/O，次数从「元组数」降到「页数」。

**什么情况下反而更慢**：

- **匹配元组很少**（如只返回 2–3 条）：排序的开销（以及可能的分配）超过了省下的 I/O，此时直接按索引顺序取更快。优化器通常按选择率阈值决定是否启用。
- **元组列表大到无法放进内存**：排序本身要溢写到磁盘，引入额外 I/O，可能抵消收益。
- **需要有序输出**（`ORDER BY` 与索引顺序一致）：排序破坏了顺序，DBMS 必须再排一次才能满足 `ORDER BY`，反而多了一次排序。这种情况下直接按索引顺序取更划算，或者用「按页取但保持输出顺序」的折中。
- **索引本身是聚簇的**：元组已按索引顺序存放，访问序列本来就接近顺序，不需要这一步。

</details>

**Q5.** 设页大小 8 KB，键 8 B，子节点指针 4 B，叶子值为 8 B 的 RecordId。计算内部节点 fanout、叶子容量，并估算索引 5000 万行所需的树高与点查 I/O 次数。若把页大小改成 1 MB（HDD 优化），结果如何变化？

<details><summary>参考答案</summary>

**8 KB 页**：

```
内部节点每个键值对 = 键 8 B + 指针 4 B = 12 B
fanout m = 8192 / 12 ≈ 682

叶子每个条目 = 键 8 B + 值 8 B = 16 B
叶子容量 L = 8192 / 16 = 512
（实际还要减去页头、槽数组、兄弟指针，约 500 条）
```

树高 h（叶子为第 1 层）需满足 `m^(h-1) × L ≥ N`：

```
h = 1: 512                      ≈ 5.1e2
h = 2: 682 × 512                ≈ 3.5e5
h = 3: 682² × 512 ≈ 4.65e5 × 512 ≈ 2.4e8   ← 已超过 5e7
```

所以 **3 层**足够（根 + 1 层内部 + 叶子），点查需 **3 次页读取**；根节点几乎总在缓冲池中，实际常是 **2 次 I/O**。

**1 MB 页**：

```
fanout m = 1048576 / 12 ≈ 87381
叶子容量 L = 1048576 / 16 = 65536

h = 1: 65536                    ≈ 6.6e4
h = 2: 87381 × 65536 ≈ 5.7e9    ← 已远超 5e7
```

所以 **2 层**足够（根本身是内部节点 + 叶子），点查 **2 次 I/O**；根常驻内存时只需 **1 次**。

**权衡**：

- 8 KB → 1 MB 把 I/O 次数从 3 降到 2，HDD 上省约 10 ms（一次寻道 + 旋转）。
- 但每次读 1 MB 而非 8 KB：若只是点查一条记录，读入的 99% 数据是浪费，且会**污染缓冲池**（一个 1 MB 节点占掉大量 frame），挤掉其他有用的页。
- 因此「HDD 用大节点、SSD 用中等节点、内存用小节点」是合理的默认；进一步还可**分层设置**：根附近用小页（常驻内存、读得少），叶子用大页（顺序扫描友好）。

**注意**：以上忽略了页头开销、填充因子（实际平均占用约 69%）与内部节点的键可能更长（变长键）。真实估算应把这些算进去，结论的量级不变。

</details>

## 12. 进一步学习

- 上一讲：[[15-445-07-Hash-Tables]] —— 哈希函数、线性探查、可扩展哈希与线性哈希。
- 下一讲：[[15-445-09-Indexes-and-Filters-II]] —— 布隆过滤器、Trie / Radix Tree、跳表、倒排索引、向量索引。
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]、[[40-CMU-15-445/04-学习进度|CMU 15-445 - 学习进度]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：教材 *Database System Concepts*（第 7 版）第 11 章「Indexing and Hashing」与第 24 章「Advanced Indexing Techniques」。
- 延伸阅读：Comer, *The Ubiquitous B-Tree* (ACM Computing Surveys, 1979) —— B 树家族的经典综述，也是「平均占用率 69%」的常见出处之一。
- 延伸阅读：Bayer & McCreight, *Organization and Maintenance of Large Ordered Indices* (1972) —— B 树原始论文；Lehman & Yao, *Efficient Locking for Concurrent Operations on B-Trees* (1981) —— Blink-Tree，兄弟指针与 High Key 的来源。
- 延伸阅读：Bender et al., *An Introduction to Bε-trees and Write-Optimization* (;login:, 2015) —— 写优化 B+ 树的入门材料。
- 动手建议：用 Python 实现一个内存版 B+ 树（支持插入、删除、范围扫描），打印每次分裂/合并后的树结构，验证「叶子 copy up、内部 push up、内部合并 pull down」三条规则。再统计随机插入 10 万条后的节点平均填充率，与讲义给的 69% 对照。
