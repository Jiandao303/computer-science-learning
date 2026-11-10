---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: L06
topic: Storage Models & Compression
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 数据库
  - 存储模型
  - 列存
  - PAX
  - 压缩编码
---

# 15-445 L06：存储模型与压缩（Storage Models & Compression）

> 前两讲讨论的是「页内怎么放元组」，本讲问一个更根本的问题：**一个元组的所有属性，真的必须存在同一页里吗？** 讲义给出的答案是「关系模型并没有这样规定」。于是有了行存（NSM）、列存（DSM）与混合的 PAX 三种存储模型。后半讲讨论压缩——它是列存能大幅超越行存的另一半原因。

## 1. 本节学习目标

学完本讲，你应该能够：

1. 区分 OLTP / OLAP / HTAP 三类工作负载的特征（操作复杂度、读写比例），并各举一个真实例子。
2. 描述 NSM（行存）的物理组织，列出它的三条优点与三条缺点，并说明为什么它适合 OLTP。
3. 描述 DSM（列存）的物理组织（每属性独立页 + header + null bitmap），说明它为什么在 OLAP 扫描中节省 I/O，并解释「tuple stitching」的代价。
4. 说出列存拼接元组的两种方式（定长偏移 / 内嵌元组 id），并说明后者为什么是坏主意。
5. 画出 PAX 的层次结构（file → row group → column chunk），说明它同时获得了列存的处理效率与行存的空间局部性。
6. 复述数据库压缩的三条设计目标（定长、延迟解压、无损）与四种压缩粒度。
7. 说明朴素压缩（naive compression）的两个局限，以及 MySQL InnoDB 如何用 mod log 缓解「读必须先解压」。
8. 手算 RLE、位打包、mostly encoding、位图、delta、字典六种编码的压缩前后比特数，并判断各自适用的数据特征。
9. 解释「保序编码（order-preserving encoding）」为什么对范围查询是必需的，以及字典编码为什么是 DBMS 中最常用的方案。
10. 区分 HTAP 的两种实现：fractured mirrors 与 delta store。

## 2. 前置知识

- **分槽页与 record id**：见 [[15-445-03-Database-Storage-I]]；NSM 的物理组织就是分槽页。
- **缓冲池与页**：见 [[15-445-04-Memory-Management]]；「一次 I/O 搬一整页」是列存省 I/O 论证的前提。
- **日志结构与索引组织存储**：见 [[15-445-05-Database-Storage-II]]；本讲开头会回顾它们的 SSTable 细节。
- **位运算**：位打包、位图编码依赖移位与掩码；只需知道「一个 32 位字可以塞进多个小整数」。
- **聚合与 GROUP BY**：讲义反复用 `SELECT COUNT(...) ... GROUP BY ...` 作为 OLAP 代表查询，见 [[15-445-02-Modern-SQL]]。

## 3. 核心概念

### 3.1 OLTP（联机事务处理）

On-Line Transaction Processing（联机事务处理）。特征是**快速、短小、重复、简单**的操作，每次只读写少量数据，通常作用于单个实体。写入多于读取。典型例子是 Amazon 的购物车与下单——用户的操作只影响自己的账户。讲义建议创业公司先建 OLTP 系统（Postgres 通常是对的选择）。

### 3.2 OLAP（联机分析处理）

On-Line Analytical Processing（联机分析处理）。特征是**长时间运行、复杂**的查询，通常涉及聚合计算，读取数据库的很大一部分。OLAP 系统往往在分析 OLTP 侧收集的数据并从中派生新数据。典型例子是 Amazon 的个性化购物广告——分析所有用户的购物车与购买记录，为不同用户挑选不同广告。

### 3.3 HTAP（混合事务与分析处理）

Hybrid Transaction + Analytical Processing（混合事务与分析处理）。OLTP 与 OLAP 工作负载**同时存在于同一个数据库实例**上。讲义以 SingleStore 作为宣称 HTAP 的例子。

### 3.4 NSM（N 元存储模型 / 行存）

N-Ary Storage Model（N 元存储模型），即 **row store（行存）**。DBMS 把一个元组（行）的（几乎）所有属性**连续**存放在同一页中，因此读取一个元组只需一次 fetch。NSM 页大小通常是 4 KB 硬件页的整数倍，用 record id（page# + slot#）标识物理元组。

### 3.5 DSM（分解存储模型 / 列存）

Decomposition Storage Model（分解存储模型），即 **column store（列存）**。DBMS 把**同一个属性**在所有元组上的值连续存放在一个数据块中。每个属性维护独立的页，页内有 header 与 null bitmap。DBMS 负责在读写时把元组的属性**拼接（stitch）或拆分（split）**。

### 3.6 PAX（跨属性分区 / 混合存储）

Partition Attributes Across（跨属性分区）。一种混合存储模型：在**页内**对属性做垂直分区。行被水平分成 row group（行组），每个行组内部再按列切成 column chunk（列块）。目标是同时拿到列存的处理效率与行存的空间局部性。Parquet、ORC、Arrow 都是 PAX 格式。

### 3.7 Naive Compression（朴素压缩）

用通用压缩算法（Deflate、LZO、LZ4、Snappy、Zstd 等）压缩**整页**。压缩后的数据对 DBMS 是**不透明黑盒**：任何读写都必须先解压整页，因此压缩的「作用域」被限制在一页之内，且算法完全不理解数据的语义，无法做延迟物化。

### 3.8 Late Materialization（延迟物化）

推迟解压与物化的时机——尽可能长时间地在**压缩态**上完成过滤、连接等操作，只在真正需要输出元组时才解压。这是列存压缩的核心收益来源。

### 3.9 RLE（游程编码）

Run-Length Encoding（游程编码）。把一列中**连续重复**的值压成三元组：值、起始偏移、长度。压缩比高度依赖数据特征，通常需要先对列排序以聚集重复值。

### 3.10 Bit-Packing（位打包）

当某整数属性的所有值都小于其声明类型能表示的最大值时，用**更少的位**表示每个值，并用移位技巧在单个机器字里同时操作多个值。

### 3.11 Patching / Mostly Encoding（补丁编码 / 大多数编码）

位打包的变体：当属性值**大多数**小于最大尺寸时，用较小类型存储，超出范围的少数值用特殊标记标出并放入查找表。

### 3.12 Bitmap Encoding（位图编码）

为属性的**每个不同值**维护一个位图，第 i 位对应表中第 i 个元组，表示该元组在此属性上是否取该值。只在**基数（cardinality）低**时实用。

### 3.13 Delta Encoding（差分编码）

不存精确值，而存同一列中相邻值的**差值**，基准值可内联或存在查找表中。可与 RLE 组合。Frame-of-Reference 变体用全局最小值作基准。

### 3.14 Dictionary Compression（字典压缩）

DBMS 用**更小的定长编码**替换频繁出现的值，并维护一个从编码到原值的映射（字典）。这是 DBMS 中最广泛使用的原生压缩方案。字典需支持快速编码/解码，且若要与范围查询配合就必须**保序**。

### 3.15 Fractured Mirrors（碎裂镜像）

HTAP 的一种实现：DBMS 自动维护数据库的**第二份 DSM 副本**。所有更新先进入 NSM 主副本，随后被复制到 DSM 镜像；分析查询跑在镜像上。若支持更新，必须在镜像中**失效**对应元组。

### 3.16 Delta Store（增量存储）

HTAP 的另一种实现：更新先暂存在 NSM 的 delta store 表，后台线程把更新迁移并应用到 DSM 数据上（批量攒够后写成 PAX 文件），写完后从 delta store 删除记录。与碎裂镜像不同，**一个元组只能存在于 NSM 或 DSM 之一**。

## 4. 通俗理解

把三种存储模型想成三种整理衣柜的方式。

- **行存 = 按「套装」挂衣**：一套西装的上衣、裤子、领带挂在一起。早上要穿整套时，伸手一次就拿全了（一次 fetch 拿到整个元组）。但如果只想统计「所有衣服里有多少件是蓝色」，你得把每一套都翻一遍，还要忽略掉裤子和领带——大量无用功。
- **列存 = 按「品类」叠放**：所有上衣一摞、所有裤子一摞、所有领带一摞。想数蓝色上衣，只翻上衣那一摞，其他两摞碰都不用碰。但想穿一整套，就得从三摞里各抽一件再配起来（tuple stitching）。
- **PAX = 抽屉里再分格**：每个抽屉放 100 套衣服（行组），抽屉内部再按品类分格（列块）。找一套衣服只需打开一个抽屉；数蓝色上衣只需扫每个抽屉的上衣格，不必跨整个衣柜。

具体数字：一张 `useracct(userID, userName, userPass, lastLogin, hostname)` 表，假设每行 200 字节、页 16 KB（每页约 80 行）。若 OLAP 查询只需要 `lastLogin` 与 `hostname`（约 40 字节），行存要把 200 字节全读进来，**有效载荷只有 20%**，等于浪费 80% 的 I/O；列存只读这两列，I/O 直接降到约 1/5。在 100 GB 的表上，这就是 80 GB 的无用读取。

## 5. 原理与推导

### 5.1 为什么「关系模型不要求属性存在一起」

讲义的关键观察是：**关系模型是逻辑层面的抽象，它没有规定物理布局**。Codd 的关系模型只要求「关系是元组的集合」，至于元组的属性在磁盘上是否相邻，完全是实现选择。

由此可以按工作负载分化设计：

- 若查询总是取整个元组、且写多 → 属性放一起（NSM）。
- 若查询只扫少数几列、且读多 → 属性分开放（DSM）。

讲义用 Stonebraker 的一张二维图定位：横轴「操作复杂度（简单→复杂）」，纵轴「读写倾向（写重→读重）」。OLTP 落在「简单 + 写重」，OLAP 落在「复杂 + 读重」，HTAP 在中间。

### 5.2 NSM 的物理组织与代价推导

```
NSM 页（分槽页）
┌──────────────────────────────────────────────┐
│ header │ slot array →                            │
│        │ ... free space ...                      │
│        │ ← tuple: [b0 a0 c0] [b1 a1 c1] [b2 ...] │
└──────────────────────────────────────────────┘
   一次 fetch = 一整行 (a_i, b_i, c_i) 全部到手
```

**优点**：插入/更新/删除快（新元组直接写进有空隙的页）；取整行只需一次 fetch（OLTP 的典型访问）；可用索引组织存储做聚簇。

**缺点推导**：

1. **扫描大范围或属性子集时低效**。假设表有 5 列共 200 字节，查询只用 2 列共 40 字节。行存必须读全部 200 字节，有效利用率 20%。表越大，浪费的绝对量越大。
2. **内存局部性差**。CPU 缓存行（cache line，典型 64 字节）加载进来时，若只用到其中少数属性，其余字节被浪费；而且无用属性把有用数据挤出缓存。
3. **不利于压缩**。同一页里混着 int、varchar、timestamp 等多个**值域（value domain）**，通用算法难以发现规律；而同一列的值往往高度相似（例如全是 `.gov` 结尾的域名、全是 5 位邮编），分开放才能利用。

第 3 点是列存压缩优势的根本原因——**压缩的前提是数据的同质性**。

### 5.3 DSM 的物理组织与 I/O 节省推导

```
列存：每个属性独立页
Page #1: header │ null bitmap │ a0 a1 a2 a3 a4 a5
Page #2: header │ null bitmap │ b0 b1 b2 b3 b4 b5
Page #3: header │ null bitmap │ c0 c1 c2 c3 c4 c5
```

**为什么省 I/O**：查询只读它需要的列的页，其余列的页**根本不加载**。若表有 100 列而查询用 3 列，理论上 I/O 降到 3%。

**代价推导：tuple stitching**。OLAP 查询几乎不会只碰一列——`WHERE hostname LIKE '%.gov'` 过滤之后，`SELECT` 还要输出其他列，`GROUP BY` 还要用 `lastLogin`。所以 DBMS 在某个时刻必须把其他列取来，**把原始元组重新拼起来**。这一步需要知道「第 i 个值属于哪个元组」，于是有了两种方案：

**方案一：定长偏移（fixed-length offsets）**——最常用。同一偏移位置上的各列值属于同一元组。前提是**每列的值必须等长**。变长字段用两种手段处理：填充（浪费空间）或字典压缩（把变长值转成定长整数编码）。这是列存与字典压缩天然绑定的原因。

**方案二：内嵌元组 id（embedded tuple ids）**——每个属性值旁边都存一个元组 id，再维护映射以跳到该 id 的其他属性。讲义直接标注 **"Don't Do This!"**：每个属性条目都要多存一个 id，存储开销巨大（若 id 是 8 字节、属性值本身只有 4 字节，开销是 200%）。

**DSM 的其他缺点**：点查询、插入、更新、删除都慢，因为涉及元组的拆分/拼接/重组。

### 5.4 PAX：为什么要「页内列化」而非「全表列化」

DSM 的问题是**空间局部性丢失**：一个元组的 100 个属性分散在 100 个不同的页/文件区域，取一行要 100 次跳转。

PAX 的观察是：**OLAP 查询虽然只用少数列，但用的行是连续的、大量的**。于是折中方案是——**在一个页（或行组）内部做列化**：

```
PAX File
├── File Meta-Data（全局目录：到各 row group 的偏移；不可变文件存在 footer 中）
├── Row Group 0
│   ├── Row Group Meta-Data
│   ├── Column Chunk A: a0 a1 a2 ...
│   ├── Column Chunk B: b0 b1 b2 ...
│   └── Column Chunk C: c0 c1 c2 ...
├── Row Group 1 ...
```

**收益推导**：

- 行组内的列块连续存放 → 扫描某列时是**顺序 I/O**，且同一列的值同质 → 压缩率高。
- 一个行组内的所有列在**同一个物理区域** → 取整行只需在该区域内的几次跳转，而不是跨整个文件。
- 行组大小可控（典型几 MB），因此「解压单位」也被限制在行组内，不会出现「为取一个值要解压整表」。

**例子**：Parquet（2013）、ORC（2013）、Arrow（2016）、Nimble（2023）、Vortex（2025）。讲义强调：**当 DBMS 说自己是列存时，它很可能用的是 PAX**。

### 5.5 压缩的三条设计目标与推导

讲义给出三条硬性目标，每条都有明确的工程理由：

1. **必须产生定长值**（唯一例外是存放在独立池中的变长数据）。理由：DBMS 要遵守**字对齐（word alignment）**，并且要能用**偏移**直接寻址第 i 个值。若压缩后长度不定，就无法 O(1) 定位。
2. **必须尽可能推迟解压**（late materialization）。理由：解压是 CPU 开销；若能在压缩态上先过滤掉大部分数据，只解压幸存者，CPU 与内存带宽都省。这要求编码**保留足够语义**让 DBMS 能直接在编码上做比较。
3. **必须无损**。理由：「人们（通常）不喜欢丢数据」。任何有损压缩必须由应用层自己做。

**为什么压缩在磁盘型 DBMS 中如此重要**：磁盘 I/O 几乎总是主要瓶颈。压缩后一次 I/O 能搬更多**有用**元组，等于放大了 I/O 带宽；代价是压缩/解压的 CPU 开销。内存型 DBMS 的情况更微妙——它不需要从磁盘取数，但压缩能降低 DRAM 需求，并可能降低查询执行时的 CPU 成本（数据更紧凑、缓存命中更好），因此要在速度与压缩比之间找平衡。

### 5.6 四种压缩粒度

| 粒度 | 压缩对象 | 适用模型 | 说明 |
|---|---|---|---|
| Block-level（块级） | 同表的一批元组 | 两者皆可 | 最粗，压缩比高但解压单位大 |
| Tuple-level（元组级） | 整个元组的内容 | 仅 NSM | 行存专用 |
| Attribute-level（属性级） | 单个元组内的一个属性值 | 两者皆可 | 可同时针对同一元组的多个属性 |
| Column-level（列级） | 多个元组在一个或多个属性上的多个值 | 仅 DSM | 允许最复杂的编码方案 |

粒度越细，越能利用同质性，但元数据开销越大。

### 5.7 朴素压缩的两个局限与 mod log 的补救

**局限一：作用域受限**。压缩后的页是黑盒，读写都要先解压整页。因此不能「把整张表压成一个大块」——否则每次访问都要解压整表。MySQL 的做法是把表切成小块（页级压缩），把压缩作用域限制在页内。

**局限二：不理解语义**。通用算法对数据的结构、查询将如何访问数据一无所知，因此**无法做延迟物化**——它不知道哪些字节将来会被用到。

**MySQL InnoDB 的 mod log 补救**（`06-storage3.pdf` 第 83–88 页）：

```
Database File                 Buffer Pool
Compressed Page0 + mod log ←→ Compressed Page0 + mod log   [1,2,4,8] KB
Compressed Page1 + mod log    Compressed Page1 + mod log
Compressed Page2 + mod log    Compressed Page2 + mod log
```

- **写**：直接写进 mod log，**不解压**页。
- **读**：若数据在 mod log 中找到，**不解压**。
- **合并时机**：有空闲周期或 mod log 满时，才解压页、应用 mod log 中的更新、重新压缩。
- 读到的未压缩版本会以 16 KB 的未压缩页形式存在于缓冲池。

这本质上是「在压缩页上叠一个小的增量日志」，把解压从每次读写降为周期性操作。

### 5.8 六种列式编码的比特账

讲义对每种编码都给了具体的压缩前后位数，这是理解「为什么列存快」的最好材料。

**(1) RLE**。原始 `isDead` 列：`Y Y N Y N Y Y Y`。压成三元组（值, 偏移, 长度）：

```
(Y, 0, 3)  (N, 3, 1)  (Y, 4, 1)  (N, 5, 1)  (Y, 6, 2)
```

若先**排序**成 `Y Y Y Y Y Y N N`，只需两个三元组：`(Y, 0, 6) (N, 7, 2)`。这就是「必须先智能排序」的含义——排序把重复值聚集，压缩比从 5 个三元组降到 2 个。

**(2) 位打包**。8 个 int32 值（191, 13, 92, 56, 120, 81, 172, 231）全都不超过 255，可用 8 位表示：

```
原始:   8 × 32 bits = 256 bits
压缩后: 8 ×  8 bits =  64 bits        → 压缩比 4:1
```

要点是用移位技巧在单个机器字里同时处理多个值（SIMD 式的批量比较/加法）。

**(3) Patching / Mostly Encoding**。假设 8 个值里只有 1 个是 99999999，其余都小于 256：

```
原始:   8 × 32 bits = 256 bits
压缩后: (8 × 8 bits) + 16 bits + 32 bits = 112 bits
        └ 主数组 ┘   └ 偏移 ┘  └ 溢出值 ┘
```

主数组用 8 位（标为 `mostly8`），偏移指向那个异常值，异常值原样存在查找表里。

**(4) 位图**。`isDead` 只有 Y/N 两个不同值，8 个元组：

```
原始:   8 × 8 bits = 64 bits
压缩后: 8 × 2 bits + 2 × 8 bits = 32 bits
        └ 每元组 2 位索引 ┘  └ 两个位图 ┘
```

**反例（讲义第 124–127 页）**：1000 万行、43000 个邮编。

```
原始 zip_code 列: 10,000,000 × 32 bits = 40 MB
位图编码:        10,000,000 × 43,000 bits = 53.75 GB
```

位图比原数据**大 1300 倍**，而且每插入一行都要扩展 43000 个位图。这就是「只在基数低时实用」的量化含义。稀疏数据的解法是 **Roaring Bitmaps**：稠密块用未压缩位图，稀疏块用 16 位整数的位打包数组。

**(5) Delta 编码**。原始 `time64` 列 `12:01, 12:00, 12:03, 12:02, 12:04`，`temp` 列 `99.4, 99.5, 99.6, 99.5, 99.4`：

```
time64 压缩: 基准 12:00 + [+1, +1, +1, +1]  → 64 bits + (4 × 16 bits) = 128 bits（原 5 × 64 = 320）
temp   压缩: 基准 99.5  + [-0.1, +0.1, +0.1, -0.2] → 64 bits + (2 × 16 bits) = 96 bits
```

再对差值套 RLE（`(+1, 4)` 表示 4 个 +1）可进一步压缩。**Frame-of-Reference 变体**：不用「前一个值」作基准，而用**全局最小值**作基准，这样每个差值都是非负的，便于位打包。

**(6) 字典编码**。把 `name` 列 `Andrea, Mr.Pickles, Andy, Jignesh, Mr.Pickles` 映射到排好序的字典：

```
字典:  Andrea(1)  Andy(2)  Jignesh(3)  Mr.Pickles(4)
编码:  1, 4, 2, 3, 4
```

关键在于**保序（order-preserving）**：字典必须按原值的排序规则排列，使编码之间的大小关系与原值一致。这样才能把

```sql
SELECT * FROM users WHERE name LIKE 'And%'
```

改写为对编码的范围查询（讲义示例写作 `WHERE name BETWEEN 10 AND 20`，示意编码区间）。若用哈希函数做编码，顺序关系就丢失了，范围查询无法下推——所以讲义明确说「不可能使用哈希函数」。

**保序还有一个额外收益**：`SELECT DISTINCT name ... LIKE 'And%'` 只需访问**字典**（几十个条目），无需扫描整列（百万级值）。

### 5.9 为什么字典编码最有用

讲义结论页给出理由：**字典编码不需要预排序**。RLE 要靠排序聚集重复值，delta 要靠列本身有序，位图要靠低基数——而字典编码对任意分布的数据都能工作，只要值有重复。它同时满足定长（编码是定长整数）、可延迟物化（可直接在编码上比较）、无损、保序（若字典排好序）。这就是它成为「DBMS 中最广泛使用的原生压缩方案」的原因。

### 5.10 HTAP 的两条路线

OLAP DBMS 做分析查询更强，OLTP DBMS 处理事务更强。若两者分开，就需要把数据从 OLTP 搬到 OLAP（数据仓库/湖仓），这套流程叫 **ETL：Extract, Transform, Load**，好处是能清洗与规范化不同 schema 的数据。

HTAP 试图在一个系统内同时支持两者，前提假设是**数据有时间性（temporal nature）**：数据刚进入时是「热」的，随元组变老，更新频率下降。于是可以「新数据用行存、老数据转列存」。

**路线一：Fractured Mirrors**（Oracle、IBM DB2 Blu、Microsoft SQL Server）

- DBMS 自动维护一份 DSM 布局的第二副本。
- 所有更新先进入 NSM 主副本，随后被复制进 DSM 镜像。
- 分析查询直接跑在镜像上。
- **若支持更新，必须在镜像中失效（invalidate）对应元组**，否则镜像会返回旧值。

**路线二：Delta Store**（SAP HANA、Vertica、SingleStore、Databricks、Google Napa）

- 更新先暂存在 NSM 的 delta store 表。
- 后台线程把更新迁移并应用到 DSM 历史数据上：批量攒成大块，写成 PAX 文件。
- 一旦进入列存，就从 delta store 删除该记录。
- 与碎裂镜像的关键区别：**一个元组只能存在于 NSM 或 DSM 之一，不能同时存在**（碎裂镜像是两份副本）。

## 6. 代码示例

### 6.1 讲义原文示例

**三类工作负载的代表 SQL**（`06-storage3.pdf` 第 17–18 页）：

```sql
-- OLTP：简单、只碰单个实体
UPDATE useracct
SET lastLogin = NOW(), hostname = ?
WHERE userID = ?;

INSERT INTO revisions VALUES (?, ?, ...);

SELECT P.*, R.*
FROM pages AS P
INNER JOIN revisions AS R
  ON P.latest = R.revID
WHERE P.pageID = ?;

-- OLAP：复杂、扫描大量数据并聚合
SELECT COUNT(U.lastLogin),
       EXTRACT(month FROM U.lastLogin) AS month
FROM useracct AS U
WHERE U.hostname LIKE '%.gov'
GROUP BY EXTRACT(month FROM U.lastLogin);
```

讲义用这两段 SQL 对比同一条查询在 NSM 与 DSM 上的 I/O：NSM 版本（第 39–47 页）必须把所有页的所有列读进来，幻灯片上直接标注 **"Useless Data!"**；DSM 版本（第 54–64 页）只加载 `hostname` 与 `lastLogin` 两列。

**Wikipedia 示例 schema**（第 13 页）：

```sql
CREATE TABLE revisions (
  revID    INT PRIMARY KEY,
  userID   INT REFERENCES useracct (userID),
  pageID   INT REFERENCES pages (pageID),
  content  TEXT,
  updated  DATETIME
);
CREATE TABLE pages (
  pageID INT PRIMARY KEY,
  title  VARCHAR UNIQUE,
  latest INT REFERENCES revisions (revID)
);
CREATE TABLE useracct (
  userID   INT PRIMARY KEY,
  userName VARCHAR UNIQUE,
  ...
);
```

**位图编码的代价示例**（第 124 页）：

```sql
CREATE TABLE customer (
  id       INT PRIMARY KEY,
  name     VARCHAR(32),
  email    VARCHAR(64),
  address  VARCHAR(64),
  zip_code INT
);
-- 10,000,000 行，43,000 个邮编
-- 原始:     10,000,000 × 32 bits          = 40 MB
-- 位图编码: 10,000,000 × 43,000 bits      = 53.75 GB
```

**MySQL InnoDB 压缩页布局**（第 83 页）：

```
Database File            Buffer Pool
Compressed Page0 + mod log  ←→  Compressed Page0 + mod log   ([1,2,4,8] KB)
Compressed Page1 + mod log       Compressed Page1 + mod log
Compressed Page2 + mod log       Compressed Page2 + mod log
```

**RLE 的三元组定义**（第 98 页）：

```
Compress runs of the same value in a single column into triplets:
  - The value of the attribute.
  - The start position in the column segment.
  - The # of elements in the run.
Requires the columns to be sorted intelligently to maximize compression opportunities.
```

**保序字典与查询改写**（第 138–145 页）：

```
字典（已排序）: Andrea | Andy | Jignesh | Mr.Pickles

SELECT * FROM users WHERE name LIKE 'And%';
  → SELECT * FROM users WHERE name BETWEEN 10 AND 20;   -- 在编码上做范围查询

SELECT DISTINCT name FROM users WHERE name LIKE 'And%';
  → Only need to access dictionary    -- 只扫字典，不扫整列
```

### 6.2 补充示例（非官方，仅用于说明概念）

**列存元组拼接伪代码**（非官方）：

```
-- 定长偏移方案：第 i 个元组 = 各列数组的第 i 个元素
def get_tuple(i):
    return (colA.values[i], colB.values[i], colC.values[i])

-- 变长值经字典编码后变定长，偏移方案仍然成立
def get_tuple_via_dict(i):
    code = colA.codes[i]
    return (colA.dictionary[code], colB.values[i], colC.values[i])
```

**在压缩态上做过滤（延迟物化）**（非官方）：

```
def scan_where_hostname_gov(columns):
    # 1. 只读 hostname 列，且直接在编码上比较（字典已保序）
    lo, hi = columns.hostname.code_range_for_prefix(".gov")
    survivors = []                      # 存的是行号，不是元组
    for i, code in enumerate(columns.hostname.codes):
        if lo <= code <= hi:
            survivors.append(i)         # 此时尚未物化任何元组
    # 2. 只为幸存行取 lastLogin
    return [(i, columns.lastLogin.values[i]) for i in survivors]
```

这个顺序正是「延迟物化」的实现形态：**先用最窄的列把候选行筛到很少，再为这些行取其他列**。

**压缩比估算**（非官方，仅说明概念）：

```
一张 1 亿行的表，某列是 8 位低基数字符串（共 200 个不同值）：
  原始:   100,000,000 × 8 bytes  = 800 MB
  字典后: 100,000,000 × 1 byte   = 100 MB   （200 < 256，1 字节足够）
           + 字典 200 × 8 bytes  ≈ 1.6 KB
  压缩比 ≈ 8:1
若再对编码做 RLE（假设按该列排序后平均游程 50）：
  100,000,000 / 50 × (1 + 2 + 2) bytes ≈ 10 MB   → 压缩比 ≈ 80:1
```

## 7. 容易混淆的概念

| 概念对 | 区别 | 记忆要点 |
|---|---|---|
| NSM vs DSM | NSM 把一行的所有属性放一起（行存）；DSM 把一列的所有值放一起（列存） | 一个横着切，一个竖着切 |
| DSM vs PAX | DSM 是**全表**列化（每列独立页）；PAX 是**页/行组内**列化（行组内分列块） | 一个跨全表，一个限于行组 |
| Block-level vs Column-level 压缩 | 块级压一批元组（含多列）；列级压多行在同一列上的多个值 | 一个混合值域，一个单一值域 |
| RLE vs Delta | RLE 压「重复」；Delta 压「相近」 | 一个要相等，一个只要有规律 |
| 位图编码 vs 位图索引 | 前者是**存储压缩**（每个不同值一张位图）；后者是**访问路径**（用位图加速谓词） | 一个为省空间，一个为省扫描 |
| 位打包 vs Mostly Encoding | 位打包要求**所有**值都小；mostly 允许少数值超标并放入查找表 | 一个要求全体，一个容忍例外 |
| 字典编码 vs 哈希 | 字典要**保序**且可逆；哈希会打乱顺序、不可逆 | 保序才能做范围查询 |
| Fractured Mirrors vs Delta Store | 前者维护**两份副本**（NSM + DSM 镜像）；后者元组**只在一处**（NSM delta 或 DSM 历史） | 一个是镜像，一个是迁移 |
| Naive vs Columnar Compression | 前者是通用算法压整页、黑盒、必须整页解压；后者理解语义、可延迟物化 | 一个不透明，一个可下推 |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Slides | `90-原始PDF/15-445/slides/06-storage3.pdf` | 165 | 2（作业与项目截止、Apache Doris 讲座）、3–4（上讲回顾与 SSTable 结构）、6–12（三类工作负载与 Stonebraker 二维图）、13（Wikipedia schema）、16（关系模型不规定物理布局）、17–18（OLTP/OLAP 代表 SQL）、19–20（三种存储模型）、21–38（NSM 物理组织与 OLTP 示例）、39–48（NSM 上的 OLAP 示例与 "Useless Data!"、NSM 优缺点）、49–68（DSM 物理组织、OLAP 示例、元组识别、变长处理、优缺点）、69–77（PAX 的动机与结构）、78–80（压缩的动机、三条目标）、80（四种粒度）、82–89（朴素压缩与 MySQL InnoDB mod log）、90–94（理想：在压缩数据上直接操作）、97–106（RLE）、107–112（位打包）、113–115（mostly encoding）、116–127（位图编码与 43000 邮编反例）、128–136（delta 编码与 frame-of-reference）、137–145（字典编码与保序）、146–151（ETL 与分裂式环境）、152–161（HTAP：fractured mirrors、delta store）、163（结论）、165（下讲预告：哈希表） |
| Notes | `90-原始PDF/15-445/notes/06-storage3.pdf` | 5 | 第 1 页（三类工作负载、存储模型、NSM）、第 2 页（DSM、元组识别两种方案、PAX）、第 3 页（压缩的动机与三条目标、四种粒度、朴素压缩与 mod log）、第 4 页（RLE、位打包、mostly、位图与 53.75 GB 反例）、第 5 页（delta、字典与保序、分裂式环境与 ETL、HTAP 两种方案） |

原始 URL：

- Slides：`https://15445.courses.cs.cmu.edu/fall2026/slides/06-storage3.pdf`
- Notes：`https://15445.courses.cs.cmu.edu/fall2026/notes/06-storage3.pdf`

> 待核实：slides 第 97 页列出六种列式编码，其中 **Incremental Encoding** 在 notes 与后续幻灯片中均未展开讲解（notes 只覆盖 RLE、位打包、patching、位图、delta、字典五种）。增量编码（前缀/后缀共享）的具体内容需人工核对讲义后续版本或其他资料。
> 待核实：slides 第 124–127 页位图示例中 `10,000,000 × 43,000` 未写明单位，按位图定义应为 bit；按 43,000 个位图各 1000 万位计算得 5.375×10^11 bit ≈ 53.75 GB，与幻灯片一致。
> 待核实：slides 第 153 页把 "Fractured Mirrors" 的实现者列为 Oracle、IBM DB2 Blu、Microsoft SQL Server，具体哪些版本实现需人工核对。

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内，本讲内容对应 2025 年第 6 讲）

- 标题：Storage Models & Compression（2025 年第 6 讲）
- URL：`https://www.youtube.com/watch?v=yWnToWrskXE&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 年份：2025
- 时间戳：未核实，故不标注。

## 10. 本节复习

- 能画出 OLTP/OLAP/HTAP 在「操作复杂度 × 读写倾向」二维图上的位置，并各举一个真实系统例子。
- 能默写 NSM 页的布局，说出三条优点与三条缺点，并解释第 3 条（不利于压缩）的原因。
- 能说明 DSM 每属性独立页的结构（header + null bitmap + 值数组），并推导「只读 3/100 列 → I/O 降到 3%」。
- 能解释 tuple stitching 为什么不可避免，以及定长偏移方案为何依赖字典压缩处理变长值。
- 能画出 PAX 的三层结构，说出 Parquet / ORC / Arrow 都是 PAX 格式。
- 能复述压缩的三条设计目标，并说明每条背后的工程理由（字对齐与偏移寻址、CPU 节省、不丢数据）。
- 能手算 RLE（含排序前后）、位打包（256→64 bit）、mostly（256→112 bit）、位图（64→32 bit）、delta（320→128 bit）的压缩结果。
- 能算出 1000 万行 × 43000 邮编的位图编码是 53.75 GB，并说出 Roaring Bitmaps 的解决思路。
- 能解释保序编码的必要性，并写出把 `LIKE 'And%'` 改写成编码范围查询的思路。
- 能对比 fractured mirrors 与 delta store 在「副本数」与「元组位置」上的差别。

## 11. 自我检查

**Q1.** 关系模型为什么允许列存？NSM 的三条缺点分别是什么，其中哪一条是列存压缩优势的根本原因？

<details><summary>参考答案</summary>

关系模型是**逻辑层的抽象**：它规定「关系是元组的集合」以及属性与域的对应，但不规定元组的属性在磁盘或内存中是否相邻。物理布局是实现选择，因此 DBMS 可以按目标工作负载选择行存、列存或混合布局。

NSM 的三条缺点：

1. **扫描大范围或属性子集时低效**：读整行但只用少数列，I/O 浪费。若行 200 字节、查询只用 40 字节，有效利用率仅 20%。
2. **内存局部性差**：CPU 缓存行装入后大部分字节用不上，有用数据还被无用属性挤出缓存。
3. **不利于压缩**：一页内混合多个值域（int、varchar、timestamp），通用算法难以发现规律。

**第 3 条是列存压缩优势的根本原因**：压缩的前提是数据的**同质性**。同一列的值共享类型、语义与分布（例如全是 `.gov` 域名、全是 5 位邮编、全是月份），因此 RLE、位打包、位图、字典这些编码才能奏效。行存把不同值域混在一页，只能退回到「通用算法压整页」的朴素压缩。

</details>

**Q2.** 列存如何拼接元组？两种方案的名称、原理与代价分别是什么？为什么讲义把其中一种标为 "Don't Do This!"？

<details><summary>参考答案</summary>

两种方案：

1. **定长偏移（fixed-length offsets）**——最常用。各列数组中**同一偏移**的值属于同一元组，因此第 i 个元组 = 各列的第 i 个元素。前提是每列的值等长；变长字段用**填充**（浪费空间）或**字典压缩**（把变长值转成定长整数编码）处理。代价：变长数据要么浪费空间，要么需要字典；插入/删除会引起数组中间的重排。
2. **内嵌元组 id（embedded tuple ids）**——每个属性值旁边存一个元组 id（如主键），再维护映射以跳到该 id 的其他属性。代价：**每个属性条目都要多存一个 id**，存储开销巨大（若 id 8 字节而值本身 4 字节，开销 200%），因此讲义标注 "Don't Do This!"。

补充：碎裂镜像/增量存储这类 HTAP 系统在拼接时还需要处理「元组只在一侧存在」的情况，通常靠失效标记或删除记录解决。

</details>

**Q3.** 分别计算下列编码的压缩前后位数：(a) 8 个 int32 值均不超过 255；(b) 8 个值中 7 个不超过 255、1 个是 99999999；(c) 8 个元组的布尔列用位图编码；(d) `time64` 列 5 个值 `12:01,12:00,12:03,12:02,12:04` 用 delta 编码。

<details><summary>参考答案</summary>

(a) **位打包**：原始 `8 × 32 = 256 bits`；全部值 ≤ 255 可用 8 位 → `8 × 8 = 64 bits`。压缩比 4:1。

(b) **Patching / Mostly Encoding**：原始 `8 × 32 = 256 bits`；主数组 `8 × 8 = 64 bits`，加 16 位偏移指向异常值，加 32 位原样存该值 → `64 + 16 + 32 = 112 bits`。

(c) **位图编码**：原始 `8 × 8 = 64 bits`（假设每个布尔值占 1 字节）；压缩后为「每元组 2 位索引」`8 × 2 = 16 bits` 加「两个不同值的位图」`2 × 8 = 16 bits`，合计 `32 bits`。

(d) **Delta 编码**：原始 `5 × 64 = 320 bits`；取基准 `12:00` 占 64 位，四个差值 `+1,+1,+1,+1` 各占 16 位 → `64 + 4 × 16 = 128 bits`。若再对差值套 RLE（`(+1, 4)`），还可进一步降低。

</details>

**Q4.** 位图编码在什么情况下会「越压越大」？请用讲义的数字说明，并给出稀疏数据的解决思路。字典编码为什么被称为最有用的方案？

<details><summary>参考答案</summary>

**越压越大的条件**：位图编码需要为**每个不同值**维护一个 N 位的位图，总空间为 `N × D` 位（N 元组数，D 不同值数）。当**基数 D 很高**时，`N × D` 会远超原数据。

**讲义数字**：1000 万行、43000 个邮编。原始 `zip_code` 为 int32，占 `10,000,000 × 32 bits = 40 MB`；位图编码占 `10,000,000 × 43,000 bits ≈ 53.75 GB`，是原数据的约 **1300 倍**。而且每插入一行都要扩展 43000 个位图，写代价也极高。

**稀疏数据的解决思路**：用压缩位图结构，例如 **Roaring Bitmaps**——把位图按块切分，稠密块用未压缩位图存，稀疏块用 16 位整数的位打包数组存。这样只在实际出现值的块上付出空间。

**字典编码为什么最有用**：它**不需要预排序**。RLE 要靠排序聚集重复值，delta 要靠列本身有序，位图要靠低基数；而字典编码对任意分布都有效，只要值有重复。它同时满足压缩的三条目标（定长整数编码、可在编码上直接比较以支持延迟物化、无损），并且在字典排好序时**保序**，使范围查询与 `DISTINCT` 都能下推到字典上。因此它是 DBMS 中最广泛使用的原生压缩方案。

</details>

**Q5.** Fractured Mirrors 与 Delta Store 都实现了 HTAP，它们在数据组织上有什么本质区别？各自需要处理什么一致性问题？

<details><summary>参考答案</summary>

**本质区别：副本数**。

- **Fractured Mirrors**：维护**两份副本**——NSM 主副本与 DSM 镜像。所有更新先写入 NSM，随后被复制进 DSM 镜像；分析查询跑在镜像上。**同一元组同时存在于两个副本**。
- **Delta Store**：只有**一份历史数据**（DSM 列存）加一个**暂存区**（NSM delta store 表）。更新先进入 delta store，后台线程批量迁移并应用到 DSM（攒成大块后写成 PAX 文件），写完后从 delta store 删除。**一个元组只能存在于 NSM 或 DSM 之一**，不能同时存在。

**一致性问题**：

- Fractured Mirrors：镜像可能落后于主副本。若 DBMS 支持更新，**必须在镜像中失效（invalidate）对应元组**，否则分析查询会读到旧值。需要处理「已失效元组」的可见性判断。
- Delta Store：需要保证迁移过程中的读写一致性——分析查询必须同时看到 DSM 历史数据与 delta store 中的新更新（通常是合并两个来源），迁移完成并删除 delta 记录时不能丢失或重复计算。批量迁移还涉及事务边界与失败恢复。

补充：两者都依赖「数据有时间性」这一前提——新数据热、老数据冷，因此把新数据留在行存、老数据转列存是合理的资源分配。

</details>

## 12. 进一步学习

- 上一讲：[[15-445-05-Database-Storage-II]] —— 日志结构存储与索引组织存储。
- 下一讲：[[15-445-07-Hash-Tables]] —— 哈希表：链地址法、开放寻址、可扩展哈希、线性哈希。
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]、[[40-CMU-15-445/04-学习进度|CMU 15-445 - 学习进度]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：教材 *Database System Concepts*（第 7 版）第 13 章「Data Storage Structures」中 column-oriented storage 一节，以及第 20 章关于列存压缩的讨论。
- 延伸阅读：Abadi et al., *Column-Stores vs. Row-Stores: How Different Are They Really?* (SIGMOD 2008) —— 讲义的核心论点（列存的优势来自延迟物化、压缩与块级处理，而非仅仅「按列存」）即出自此脉络。
- 延伸阅读：Stonebraker 的 "One Size Fits All" 论点与讲义第 7 页的二维图直接相关；可对照读 *The End of an Architectural Era*。
- 动手建议：用 `pyarrow` 读一个 Parquet 文件，检查 `row_group` 与 `column chunk` 的元数据，验证 PAX 的三层结构；再用 `SELECT` 只取两列，观察读取的字节数远小于整表大小。
