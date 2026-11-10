---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: L05
topic: Database Storage II (Log-Structured & Index-Organized Storage)
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 数据库
  - 存储
  - LSM-Tree
  - SSTable
  - 索引组织表
  - 系统目录
---

# 15-445 L05：数据库存储 II（Log-Structured & Index-Organized Storage）

> 第 3 讲讲的是「页里怎么放元组」，第 5 讲把视角拉高一层：**整张表应该怎么组织**？讲义给出三种页存储架构：分槽页（slotted page，上一讲已讲）、索引组织存储（index-organized）、日志结构存储（log-structured）。后两者正是现代系统里最常见的两种「非堆文件」组织方式——前者是 MySQL InnoDB 的主键表，后者是 RocksDB / LevelDB / Cassandra 的根基。

## 1. 本节学习目标

学完本讲，你应该能够：

1. 复述分槽页存储的读、插入、更新流程，并列出它的三个问题（碎片、无用 I/O、随机 I/O）。
2. 解释日志结构存储的核心思想：把「就地更新」换成「追加日志」，并说明它为什么适合只能追加的存储（HDFS、Colossus、对象存储）。
3. 画出 MemTable → SSTable → 多层级（Level 0/1/2…）的写入路径，说明 PUT / DELETE 记录的内容与「只看最新版本」的语义。
4. 描述日志结构存储的读路径：先查 MemTable，再逐层查 SSTable（每层二分查找），一旦找到最新版本即停止。
5. 说明 SummaryTable 的两个作用（每 SSTable 的 min/max key、每层的 key filter 如布隆过滤器），以及它如何避免「查不存在的键要扫全部 SSTable」。
6. 区分 **Leveled Compaction（分层压缩）** 与 **Universal Compaction（通用压缩）** 的触发条件、层结构、适用负载。
7. 解释索引组织存储（index-organized storage）与堆文件的区别，说明为什么它省掉一次索引→元组的跳转。
8. 说明系统目录（system catalog）存什么、如何用 `INFORMATION_SCHEMA` 查询，以及加列/删列/改列/建索引的代价。

## 2. 前置知识

- **分槽页（slotted page）与 record id**：见 [[15-445-03-Database-Storage-I]]，本讲的读/写流程直接复用。
- **缓冲池**：见 [[15-445-04-Memory-Management]]。「整块读入才能改一个元组」这一无用 I/O 的根源就是页级 I/O。
- **B+ 树的基本形态**：下一讲才正式展开，但本讲的索引组织存储需要先知道「索引有内部节点与叶子节点」。
- **哈希与布隆过滤器**：key filter 常用布隆过滤器，第 9 讲会详细讲，这里只需知道「它能用很小空间判断某键是否**一定不存在**」。
- **LSM-Tree 的背景**：讲义注明日志结构存储源自 1996 年的 log-structured merge trees（LSM Trees）与 log-structured file systems（LSFS）。

## 3. 核心概念

### 3.1 Tuple-Oriented Storage / Slotted Page Storage（面向元组的存储 / 分槽页存储）

最常见的元组存储架构：页头 + 槽数组 + 从页尾向前生长的元组数据。通过 record id（file id + page id + slot #）定位元组。适合读，但更新代价高。

### 3.2 Record ID（记录标识）

DBMS 给每个逻辑元组分配的唯一物理位置标识，典型为 `File Id + Page Id + Slot #`。多数 DBMS 不把 id 存进元组；SQLite 把 `ROWID` 当作真正主键并作为隐藏属性存储。**应用不应依赖这些 id 的语义**。常见大小：TID 4 B、CTID 6 B、ROWID 8/10 B、`%%physloc%%` 8 B、`RDB$DB_KEY` 8 B。

### 3.3 Log-Structured Storage（日志结构存储）

不在页内就地更新元组，而是维护一个**记录元组变更的日志**。每条日志是一个 PUT 或 DELETE 操作；DBMS 先把变更写入内存结构 MemTable，写满后按 key 排序、顺序刷出为不可变的 SSTable。

### 3.4 MemTable（内存表）

内存中的有序结构（通常是跳表或红黑树），暂存最新的 PUT/DELETE 记录。写操作先落到这里，因此写入是纯内存操作，极快。

### 3.5 SSTable（Sorted String Table，有序字符串表）

MemTable 写满后序列化、按 key 排序、**顺序**写到磁盘形成的不可变文件。因为不可变且顺序写，随机 I/O 大大减少，也完美契合追加型存储（对象存储、云盘）。

### 3.6 SummaryTable（摘要表）

内存中的辅助结构，记录**每个 SSTable 的 min/max key** 与**每一层的 key filter（如布隆过滤器）**。作用是在读路径上快速排除「不可能包含该 key」的 SSTable，避免最坏情况下扫遍所有 SSTable。

### 3.7 Compaction（压缩 / 合并）

周期性地用**排序归并（sort-merge）**把多个 SSTable 合并，每个 key 只保留最新版本，从而回收空间、加快读。代价是**写放大（write amplification）**：一次逻辑写可能引发多次物理写。

### 3.8 Leveled Compaction（分层压缩）

数据按层组织，每层有大小上限；同一层内 SSTable 的 key 范围**不重叠**（Level 0 例外，它是刚从内存刷出的、范围可能重叠的文件）。压缩时把某层的文件合并进下一层，保持有序且不重叠。**适合读密集型负载**。

### 3.9 Universal Compaction（通用压缩）

所有 SSTable 在**单一「通用」层**中，没有多级层次。当 key 范围重叠过多或超过大小阈值时触发压缩。**适合写密集（插入密集）负载与时间序查询**。

### 3.10 Index-Organized Storage（索引组织存储）

DBMS 直接把表的元组**作为索引数据结构的值**存储（索引可以是 B+ 树、跳表、trie）。叶子节点的页布局类似分槽页，但元组按 key 排序，页内用 key→offset 数组定位。省掉了「先查索引拿 record id，再去堆文件取元组」的第二次跳转。

### 3.11 System Catalog（系统目录）

DBMS 内部保存的元数据：表/视图/列/存储过程/索引、用户与权限、内部统计信息（如某属性的最大值）。几乎所有 DBMS 都把目录**当作表存在自己内部**，并用特殊代码「自举（bootstrap）」这些目录表。

## 4. 通俗理解

把三种存储架构想成三种记账方式。

- **分槽页 = 活页笔记本**：每页写满就换页，改动直接划掉重写在同一页上。查找要翻目录（索引）找到页码，再翻到那一页。问题是：划掉的地方会留空白（碎片），而且为了改一个字你都得把整页抽出来（无用 I/O），改 20 条分散的记录要翻 20 次（随机 I/O）。
- **日志结构 = 只写不可撕的收据本**：所有改动按时间顺序往后写，绝不涂改。收据攒够一叠，就按编号排好序、装订成一册（SSTable）。想查某笔账，先看桌上还没装订的收据（MemTable），再逐册倒着查。册子越攒越多，就得定期把几册合并、只保留每笔账的最新记录（compaction）。
- **索引组织表 = 按姓名排序的电话簿**：号码不是另存一处再索引，而是**直接印在姓名旁边**。找张三，翻到 Z 开头就直接看到号码，不用「先查索引卡再去找档案柜」。

具体数字：一张 100 GB 的表，若每行 100 字节、页 16 KB，约 **6.7 亿行、655 万个页**。就地更新若随机分布，1000 次更新可能触发 1000 次随机 I/O（约 90 ms）；而日志结构把这 1000 次更新先在内存合并，再一次性顺序写出（一次 I/O 量级），差距近三个数量级。

## 5. 原理与推导

### 5.1 分槽页的三个问题是怎么来的

**问题 1：碎片（fragmentation）**。删除元组只把槽标记失效，页内留下无法立刻复用的小洞；若新元组比洞大，洞就浪费了。页利用率因此低于 100%，同样数据需要更多页。

**问题 2：无用磁盘 I/O**。非易失存储是**块寻址**的，改一个 100 字节的元组也必须把整页（比如 16 KB）读进来再写回去，有效载荷比 100/16384 ≈ 0.6%。

**问题 3：随机磁盘 I/O**。若一次事务要更新 20 个分散在不同页的元组，就要 20 次随机 I/O。按每次 90 µs 计约 1.8 ms——在 OLTP 里已是难以接受的数量级。

这三个问题指向同一个前提：**必须就地更新**。于是自然要问：如果存储**只允许创建新页、不允许覆盖旧页**呢？（HDFS、Google Colossus、S3 Express 这类追加型存储就是这样。）日志结构存储正是为这个前提设计的。

### 5.2 日志结构存储的写路径推导

```
写请求 (PUT key101=a1)
   ↓
[1] 追加到 MemTable（内存有序结构）        ← 快，纯内存
   ↓ MemTable 满
[2] 序列化 + 按 key 排序
   ↓
[3] 顺序写盘 → SSTable（不可变）           ← 一次顺序 I/O
   ↓
[4] 注册到 SummaryTable（min/max key、filter）
```

**为什么这是顺序写**：MemTable 在刷出前已经按 key 排好序，所以写出时是一次从头到尾的顺序追加，不需要在文件中间找位置。这正是它能适配 HDFS/对象存储的原因——这些系统**只支持追加或整体重写文件**。

**为什么每条记录要带操作类型**：同一个 key 会被反复 PUT/DELETE。读的时候**只关心最新版本**，所以记录必须携带 `PUT/DELETE` 标志，且同一 key 的多条记录中只有最新的那条有意义。

### 5.3 读路径推导：为什么会「最坏扫全部 SSTable」

读 `GET(key101)` 的协议：

1. 查 MemTable——若命中，直接返回（最新数据一定在内存里）。
2. 否则按层从 Level 0 开始逐层查，每个 SSTable 内部**二分查找**（因为已按 key 排序）。
3. **一旦找到该 key 的第一次出现就停止**——因为我们是按「新→旧」的顺序找的，第一次找到就是最新版本。

最坏情况：查一个**从未插入过**的 key。此时 MemTable 没有，每一层的每个 SSTable 都不会命中，必须全部查完。若系统有 5 层、每层 10 个 SSTable，就是 50 次文件查找。

**SummaryTable 的两级剪枝**：

- **每 SSTable 的 min/max key**：若 `key < min` 或 `key > max`，这个 SSTable 直接被排除（O(1) 判断，取代一次二分查找 + 可能的磁盘读）。
- **每层的 key filter（布隆过滤器）**：用极小的空间回答「这个 key **一定不在**本层」；只有过滤器说「可能在」时才真正去查。对「查不存在的键」这个最坏场景，布隆过滤器几乎能全部挡掉。

### 5.4 压缩（compaction）的必然性与两种策略

**为什么必须压缩**：写密集负载下 SSTable 会无限累积。同一个 key 的 100 个历史版本占着 100 份空间，读的时候还要逐个跳过。压缩用**排序归并**只保留每个 key 的最新记录（DELETE 记录在合并后若无更旧版本可以一并丢弃）。

**Leveled Compaction 的结构推导**：

- Level 0：刚从 MemTable 刷出的文件，**key 范围可以重叠**（因为每次刷出的时间不同，内容自然重叠）。
- Level 1 及以下：同层内 SSTable 的 key 范围**互不重叠**，因此查一层只需**定位一个文件**（先二分找范围，再在文件内二分找 key）。
- 压缩时把某层的一个文件合并进下一层，与下一层中 key 范围重叠的文件一起归并，产生新的不重叠文件。

推论：**层数 ≈ log_{扇出} 数据量**，读放大有上界（每层最多查 1 个文件），所以**读快**；但每次压缩都要重写大量数据，**写放大高**。适合读多的负载。

**Universal Compaction 的结构推导**：

- 只有一个「通用」层，所有 SSTable 平铺在一起，key 范围大量重叠。
- 触发条件：key 范围重叠的 SSTable 太多，或总大小超过阈值。
- 压缩时把**一整批重叠文件**一起归并成一个大文件。

推论：写入时基本只需追加，压缩时批量合并，**写放大低**；但读的时候同一层可能有很多重叠文件要逐个查，**读放大高**。适合插入密集、按时间序查询的负载（例如时序数据、日志）。

### 5.5 权衡表：什么时候用哪种存储

| 维度 | 分槽页（堆文件） | 日志结构 | 索引组织 |
|---|---|---|---|
| 写入模式 | 就地更新 | 追加 | 就地更新（在索引叶子内） |
| 写性能 | 随机写，差 | 顺序写，好 | 随机写 + 树维护，中等 |
| 读性能 | 需索引 + 二次跳转 | 可能查多层，较慢 | 一次树查找直达元组 |
| 空间效率 | 有碎片 | 有多版本冗余，压缩后回收 | 高（无额外 record id 跳转） |
| 主要代价 | 碎片、随机 I/O | 压缩昂贵、写放大 | 树分裂/合并、维护成本 |
| 典型系统 | Postgres、MySQL（堆表） | RocksDB、LevelDB、Cassandra | MySQL InnoDB（主键表）、SQLite（部分） |

### 5.6 索引组织存储省掉了什么

堆文件下按主键查一行的路径是：**索引树查找 → 得到 record id → 页目录 → 缓冲池 → 页内 slot → 元组**。索引组织存储把元组直接放在索引叶子节点里，路径变成：**索引树查找 → 叶子页内 key→offset 数组 → 元组**。省掉的是「record id → 另一个文件/页」这一次可能跨文件的跳转。

代价有两个：其一，**任何二级索引都必须存主键值**（因为无法用物理 record id，主键更新会导致所有二级索引失效）；其二，**非主键的插入会导致叶子页分裂与元组搬移**，写代价高于堆文件的尾部追加。

### 5.7 系统目录：为什么「目录也是表」

DBMS 需要知道「student 表有哪些列、什么类型、有没有索引、谁有权限、某列最大值是多少」。最自然的实现是**把目录本身存成表**（例如 `pg_catalog.pg_class`、`information_schema.tables`），这样就可以用 SQL 查询、用事务保护、用缓冲池缓存——复用已有的一切机制。

问题是「先有鸡还是先有蛋」：查 `pg_class` 需要知道 `pg_class` 的结构。解法是**自举（bootstrap）**：在代码里硬编码最基础几张目录表的模式，启动时先构建它们，再由它们描述其他所有表。

标准入口是 `INFORMATION_SCHEMA`——ANSI 标准的**只读视图**集合，提供所有表、视图、列、存储过程的信息。各系统还有非标准快捷方式（见 6.1）。

### 5.8 模式变更（schema change）的代价分析

- **ADD COLUMN**：慢做法是把所有元组复制到新页并写入新列；快做法是**只在目录里记录默认值**，旧元组读出来时动态补上默认值（incremental update）。后者是 OLTP 系统的主流做法。
- **DROP COLUMN**：把列标记为「deprecated」，新元组不再写该列，旧空间稍后清理。
- **CHANGE COLUMN**：重命名只改目录元数据（O(1)）；改类型要检查新旧类型是否**二进制兼容**，不兼容则必须重写所有元组；改约束需要**全表扫描**验证；改默认值只改目录。
- **CREATE INDEX**：全表扫描填充索引，同时必须记录扫描期间其他事务造成的修改，扫描结束后**锁表**并把遗漏的修改补上。
- **DROP INDEX**：先从目录里逻辑删除，但只有在删索引的事务**提交后**才对其他事务不可见；在此之前所有事务仍须维护它。

## 6. 代码示例

### 6.1 讲义原文示例

**三种页存储架构**（`05-storage2.pdf` 第 4 页）：

```
Approach #1: Slotted Page Storage
Approach #2: Index-organized Storage
Approach #3: Log-structured Storage
```

**Slotted Page 结构**（第 6–14 页）：`Header | Slot Array | ... free space ... | Tuple #4 | Tuple #2 | Tuple #3 | Tuple #1`；header 记录「已用槽数」与「最后一个已用槽的起始偏移」。

**Record ID 大小对照**（第 15–16 页）：

```
TID          4-bytes
CTID         6-bytes
ROWID        8-bytes
%%physloc%%  8-bytes
RDB$DB_KEY   8-bytes
ROWID       10-bytes
```

**日志记录示例**（第 39–47 页的动画，最终生成的 SSTable 内容）：

```
MemTable 依次收到:  PUT(key101, a1) → PUT(key102, b1) → PUT(key101, a2) → PUT(key103, c1)
刷出为 SSTable（按 key 升序）:
  PUT (key101, a2)     ← 注意：a1 已被覆盖，只保留最新
  PUT (key102, b1)
  PUT (key103, c1)
```

**带删除记录的 SSTable**（第 64 页）：

```
DEL (key100)
PUT (key101, a3)
PUT (key102, b2)
PUT (key103, c1)
```

**压缩前后对比**（第 66–77 页，两个 SSTable 归并）：

```
SSTable A（较新）: DEL(key100)  PUT(key101,a3)  PUT(key102,b2)  PUT(key103,c1)
SSTable B（较旧）: PUT(key101,a2)  PUT(key102,b1)  DEL(key103)  PUT(key104,d2)
归并结果:          DEL(key100)  PUT(key101,a3)  PUT(key102,b2)  PUT(key103,c1)  PUT(key104,d2)
```

讲解要点：key101 取较新的 a3；key102 取较新的 b2；key103 在 A 中是 PUT、在 B 中是 DEL → **较新的 PUT 胜出**；key100 只在 A 中是 DEL，且 B 中无更旧版本 → DEL 保留（等待更旧层合并时才能彻底丢弃）；key104 只在 B 中出现 → 保留。

**查询系统目录（SQL-92 标准方式）**（第 103–104 页）：

```sql
-- 列出当前数据库的所有表
SELECT * FROM INFORMATION_SCHEMA.TABLES
WHERE table_catalog = '<db name>';

-- 查看 student 表的信息
SELECT * FROM INFORMATION_SCHEMA.TABLES
WHERE table_name = 'student';
```

各系统的非标准快捷方式（第 103–104 页）：

| 系统 | 列出表 | 查看表结构 |
|---|---|---|
| Postgres | `\d` | `\d student;` |
| MySQL | `SHOW TABLES;` | `DESCRIBE student;` |
| SQLite | `.tables` | `.schema student` |

**索引维护的事务细节**（第 106 页）：

```
CREATE INDEX:
  - Scan the entire table and populate the index.
  - Must record changes made by txns that modified the table while
    another txn was building the index.
  - When the scan completes, lock the table and resolve changes
    that were missed after the scan started.
DROP INDEX:
  - Drop the index logically from the catalog.
  - It only becomes "invisible" when the txn that dropped it commits.
    All existing txns will still have to update it.
```

### 6.2 补充示例（非官方，仅用于说明概念）

**日志结构存储的读路径伪代码**（非官方）：

```
get(key):
    if memtable.contains(key):
        return memtable.get(key)            # 最新数据一定在内存

    for level in 0 .. max_level:
        for sstable in level:               # Level 0 范围可能重叠，需逐个查
            if key < sstable.min_key or key > sstable.max_key:
                continue                    # SummaryTable 剪枝（O(1)）
            if not level.filter.might_contain(key):
                continue                    # 布隆过滤器剪枝
            rec = sstable.binary_search(key)  # 文件内二分
            if rec is not None:
                return None if rec.type == DELETE else rec.value
    return None                             # 全层都未找到
```

两处剪枝的顺序很关键：先比 min/max（极便宜），再用过滤器（便宜），最后才二分（要读盘）。

**写放大估算**（非官方，仅说明概念）：

```
若 leveled compaction 的每层扇出为 10、共 4 层：
  一条记录从 Level 0 降到最底层，最多被重写 4 次
  → 写放大 ≈ 4（不含 WAL 与 SSD 内部的垃圾回收放大）
若 universal compaction 一次把 10 个文件合并成 1 个：
  写放大 ≈ 10/9 ≈ 1.1（但读放大显著上升）
```

这解释了讲义的结论：**RocksDB 这类日志结构引擎的代价是写放大与压缩开销**。

## 7. 容易混淆的概念

| 概念对 | 区别 | 记忆要点 |
|---|---|---|
| Slotted Page vs Log-Structured | 前者就地更新、有碎片与随机 I/O；后者只追加、顺序写、有多版本冗余 | 一个改写旧页，一个只写新记录 |
| MemTable vs SSTable | MemTable 在**内存**、可变、有序；SSTable 在**磁盘**、不可变、有序 | 内存可变，磁盘不可变 |
| Leveled vs Universal Compaction | 分层压缩：多层、同层不重叠、读快写放大高；通用压缩：单层、范围重叠、写快读放大高 | 分层重读，通用重写 |
| SummaryTable vs Bloom Filter | SummaryTable 是整体的摘要结构，包含每 SSTable 的 min/max **以及**每层的 key filter；布隆过滤器只是其中的 filter 部分 | 摘要表是容器，布隆过滤器是零件 |
| 索引组织表 vs 堆文件 + 索引 | 前者元组直接存在索引叶子里（一次查找）；后者索引只存 record id，需二次跳转 | 一个直达，一个中转 |
| Log-Structured Storage vs WAL | 日志结构存储是**表的组织方式**（SSTable 即数据本身）；WAL 是**崩溃恢复机制**（数据另存于页中） | 一个存数据，一个保正确 |
| System Catalog vs INFORMATION_SCHEMA | 目录是 DBMS 内部的元数据存储（实现）；`INFORMATION_SCHEMA` 是 ANSI 标准的只读视图（接口） | 一个是实现，一个是标准接口 |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Slides | `90-原始PDF/15-445/slides/05-storage2.pdf` | 108 | 2（作业与项目时间）、4（三种页存储架构）、6–16（分槽页与 record id）、17–26（分槽页读路径与索引跳转）、27–33（索引组织存储）、34–36（分槽页写路径与三个问题）、37–63（日志结构：MemTable→SSTable→分层→SummaryTable）、64（日志记录内容）、65–77（压缩与归并示例）、78–92（Leveled Compaction）、93–99（Universal Compaction）、100（讨论：RocksDB 与写放大）、101–104（系统目录与 INFORMATION_SCHEMA）、105（模式变更）、106（索引维护）、107（结论） |
| Notes | `90-原始PDF/15-445/notes/05-storage2.pdf` | 3 | 第 1 页（面向元组存储的读/插入/更新流程与三个问题、日志结构存储的引入）、第 2 页（MemTable 与 SSTable、读路径、SummaryTable、Compaction 与两种策略）、第 3 页（权衡、索引组织存储、系统目录） |

原始 URL：

- Slides：`https://15445.courses.cs.cmu.edu/fall2026/slides/05-storage2.pdf`
- Notes：`https://15445.courses.cs.cmu.edu/fall2026/notes/05-storage2.pdf`

> 待核实：讲义第 37 页称 LSM Tree 于「1996 年」提出，notes 给出的两篇参考文献分别为 LSFS（DOI 10.1145/146941.146943）与 LSM Tree（DOI 10.1007/s002360050048），具体年份与出处需人工核对原文。
> 待核实：讲义第 78、93 页标题拼写为 "STRATGEGIES"（原文如此），非本笔记引入的错误。

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内，本讲内容对应 2025 年第 5 讲）

- 标题：Database Storage II（2025 年第 5 讲）
- URL：`https://www.youtube.com/watch?v=2_sTdS4h-bY&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 年份：2025
- 时间戳：未核实，故不标注。

## 10. 本节复习

- 能说出三种页存储架构的名字，并各用一个真实系统举例。
- 能默写分槽页的读、插入、更新流程，并指出更新的「不拟合就删旧插新」策略。
- 能列出分槽页的三个问题，并说明它们共同的根源是「就地更新 + 块寻址」。
- 能画出 MemTable → SSTable 的写路径，说明为什么这是顺序写、为什么能适配对象存储。
- 能写出读路径的三步，并解释为什么「找到第一次出现就停止」是正确的。
- 能说明 SummaryTable 的 min/max 剪枝与布隆过滤器剪枝分别省掉了什么。
- 能对比 Leveled 与 Universal Compaction 的层结构、读放大、写放大与适用负载。
- 能解释索引组织表省掉了哪一次跳转、付出了哪两个代价。
- 能写出查 `INFORMATION_SCHEMA.TABLES` 的 SQL，并说出 ADD COLUMN 的快慢两种做法。

## 11. 自我检查

**Q1.** 分槽页存储有哪三个问题？它们共同的根源是什么？日志结构存储如何分别缓解这三点？

<details><summary>参考答案</summary>

三个问题：

1. **碎片（fragmentation）**：删除元组只标记槽失效，页内留下无法立即复用的小洞，页利用率下降。
2. **无用磁盘 I/O**：非易失存储按块寻址，改一个元组也必须把整页读入再写回。
3. **随机磁盘 I/O**：更新分散在 20 个页的 20 个元组，就要 20 次随机 I/O。

共同根源是**必须就地更新**，加上**块寻址**的物理约束。

日志结构存储的缓解方式：写入先在 MemTable 中累积并**在内存里合并**（多次逻辑写变成一次物理写，缓解无用 I/O 与随机 I/O）；写满后**顺序**刷出为不可变 SSTable（顺序 I/O 远快于随机 I/O）；空间浪费由**压缩**回收（缓解碎片，但代价是写放大）。它并不消除冗余（多版本共存直到压缩），而是把代价从「随机写」转移到「后台批量合并」。

</details>

**Q2.** 请描述日志结构存储的读路径，并解释为什么「查一个不存在的键」是最坏情况，以及 SummaryTable 如何改善它。

<details><summary>参考答案</summary>

读路径：

1. 查 MemTable，命中即返回（最新数据必在内存）。
2. 否则从 Level 0 开始逐层扫描 SSTable，每个 SSTable 内做二分查找。
3. 因为按「新→旧」顺序查找，**第一次找到该 key 即为最新版本**，立即停止。

最坏情况是查一个从未插入过的键：MemTable 不含，每一层的每个 SSTable 都不会命中，必须全部查完。若有 5 层、每层 10 个文件，就是 50 次文件级查找，每次都可能是磁盘 I/O。

SummaryTable 的两级剪枝：

- **每 SSTable 的 min/max key**：若目标 key 落在范围外，O(1) 排除该文件，省掉一次二分与可能的读盘。
- **每层的 key filter（布隆过滤器）**：以极小空间判断「该 key 一定不在本层」，对不存在的键几乎能全部挡掉，把 50 次查找压缩到接近 1 次。

</details>

**Q3.** 给定 SSTable A（较新）：`DEL(key100), PUT(key101,a3), PUT(key102,b2), PUT(key103,c1)`；SSTable B（较旧）：`PUT(key101,a2), PUT(key102,b1), DEL(key103), PUT(key104,d2)`。写出压缩后的结果并说明每个 key 的取舍理由。

<details><summary>参考答案</summary>

压缩结果（按 key 升序）：

```
DEL (key100)
PUT (key101, a3)
PUT (key102, b2)
PUT (key103, c1)
PUT (key104, d2)
```

逐 key 说明：

- `key100`：只在 A 中有 `DEL`，B 中没有更旧版本。删除标记**必须保留**——若此时丢弃，将来更旧层合并时旧值会「复活」。只有确认所有更旧层都不含该 key 时才能丢弃 DEL。
- `key101`：A 是 a3、B 是 a2，**较新的 A 胜出** → a3。
- `key102`：A 是 b2、B 是 b1，较新的胜出 → b2。
- `key103`：A 是 `PUT(c1)`、B 是 `DEL`。**较新的 PUT 胜出** → c1（该键被删除后又被重新插入）。
- `key104`：只在 B 中出现 → 保留 d2。

</details>

**Q4.** Leveled Compaction 与 Universal Compaction 有什么区别？各自适合什么负载，为什么？

<details><summary>参考答案</summary>

**Leveled Compaction（分层压缩）**：

- 数据按层组织，每层有大小上限；Level 0 是刚从 MemTable 刷出的文件，key 范围可重叠；Level 1 及以下同层 SSTable **key 范围互不重叠**。
- 压缩把某层文件合并进下一层，与目标层中范围重叠的文件一起归并。
- **读放大有上界**（每层最多定位一个文件，层数 ≈ log 扇出），**写放大高**（记录每下沉一层就被重写一次）。
- 适合**读密集型**负载。

**Universal Compaction（通用压缩）**：

- 所有 SSTable 在单一「通用」层，key 范围大量重叠。
- 当重叠文件过多或总大小超阈值时，把一整批文件归并成一个大文件。
- **写放大低**（批量合并，一次写多份数据只重写一次），**读放大高**（同层多个重叠文件都要查）。
- 适合**插入密集（写密集）负载与时间序查询**——因为新数据总在文件头部，按时间范围查询能快速定位。

本质权衡：**分层用读性能换写放大，通用用读放大换写性能**。

</details>

**Q5.** 索引组织存储（index-organized storage）相比「堆文件 + 二级索引」省掉了什么？付出的代价是什么？

<details><summary>参考答案</summary>

**省掉的**：堆文件下按主键查一行需要「索引树查找 → 拿到 record id → 页目录 → 缓冲池 → 页内 slot → 元组」，其中 record id 到实际页可能是一次跨文件的额外跳转。索引组织存储把元组**直接作为索引叶子节点的值**，路径变成「索引树查找 → 叶子页内 key→offset 数组 → 元组」，省掉这次跳转，主键查找更快、更可预测（一次树的下降）。

**代价**：

1. **二级索引必须存主键值**，因为无法使用会随页重组而变化的物理 record id；主键越长，所有二级索引越大。
2. **非主键插入会引起叶子页分裂与元组搬移**，写代价高于堆文件「追加到有空隙的页」；更新主键值等同于删除 + 插入，代价更高。
3. 表的数据物理上按主键有序，**插入顺序与主键顺序不一致时随机 I/O 增加**（InnoDB 因此推荐自增主键）。

</details>

## 12. 进一步学习

- 上一讲：[[15-445-04-Memory-Management]] —— 缓冲池、替换策略与 ARC。
- 下一讲：[[15-445-06-Storage-Models-and-Compression]] —— 行存 vs 列存、存储模型与压缩编码。
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]、[[40-CMU-15-445/04-学习进度|CMU 15-445 - 学习进度]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：教材 *Database System Concepts*（第 7 版）第 13 章「Data Storage Structures」中关于 log-structured storage 与 index-organized tables 的小节；O'Neil et al., *The Log-Structured Merge-Tree (LSM-Tree)*, Acta Informatica 1996（讲义第 1 页给出的 DOI `10.1007/s002360050048`）。
- 延伸阅读：RocksDB Wiki 的 "Compaction" 与 "Leveled Compaction" 页面，可与讲义的两种策略对照；讲义第 100 页指出日志结构存储的流行与 RocksDB 的普及直接相关。
- 动手建议：用 SQLite 建一张表并执行 `PRAGMA page_size;`、`SELECT * FROM sqlite_master;` 观察「目录也是表」；再对照 MySQL 的 `SHOW TABLES;` 与 `DESCRIBE`，体会标准接口（`INFORMATION_SCHEMA`）与各系统方言的差别。
