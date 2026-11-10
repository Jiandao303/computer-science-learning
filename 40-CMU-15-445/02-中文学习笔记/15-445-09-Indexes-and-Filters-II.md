---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: L09
topic: Indexes & Filters II — Bloom Filters, Skip Lists, Tries, Inverted & Vector Indexes
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 数据库
  - 布隆过滤器
  - 跳表
  - Trie
  - 倒排索引
  - 向量索引
---

# 15-445 L09：索引与过滤器 II（Indexes & Filters II）

> B+ 树解决了「点查与范围查」，但它对三类需求无能为力：**判断键不存在**（内部节点的路标不能回答存在性，必须走到叶子）、**按内容关键词搜索**、**按语义相似度搜索**。本讲依次给出答案：布隆过滤器（省掉无谓查找）、跳表与 Trie（不同的保序结构）、倒排索引（关键词）、向量索引（语义）。最后补上两个 B+ 树的实用变体：部分索引与包含列。

## 1. 本节学习目标

学完本讲，你应该能够：

1. 说明为什么 B+ 树无法高效回答「键不存在」，以及布隆过滤器如何弥补这一点。
2. 手写布隆过滤器的 Insert / Lookup 算法，解释为什么**绝不会有假阴性**、为什么**不能删除**。
3. 说出计数布隆过滤器、Cuckoo 过滤器、SuRF 各自解决布隆过滤器的哪个缺陷。
4. 描述跳表的多层结构与抛硬币插入，说明它为什么能做到 O(log n) 且**不需要再平衡**，以及它的两个主要缺点。
5. 说明 Trie 的 shape 为什么只依赖键集合而非插入顺序，解释 span 与 fanout 的关系，以及 O(k) 的含义。
6. 说明 Radix Tree（Patricia Trie）的水平/垂直压缩，以及为什么压缩后会**产生假阳性**。
7. 描述倒排索引的 dictionary + posting list 结构，比较 Lucene（FST）与 PostgreSQL GIN（B+ 树 + pending list）两种实现。
8. 描述向量索引的两条路线（IVF 倒排聚类 vs HNSW 图），说明为什么它没有「正确答案」。
9. 说明部分索引（partial index）与包含列（INCLUDE / covering index）各自省掉了什么。

## 2. 前置知识

- **B+ 树与内部节点路标**：见 [[15-445-08-Indexes-and-Filters-I]]；本讲第一个动机就来自「内部键不能回答存在性」。
- **哈希表与 Cuckoo Hashing**：见 [[15-445-07-Hash-Tables]]；Cuckoo 过滤器是它的指纹版本。
- **位图与列式编码**：见 [[15-445-06-Storage-Models-and-Compression]]；布隆过滤器就是位图，倒排索引的字典常用 delta + 位打包压缩。
- **RecordId 与页**：见 [[15-445-03-Database-Storage-I]]；posting list 里存的是 record id。
- **概率数据结构**：允许假阳性、不允许假阴性的「单向误差」是布隆过滤器、跳表、Radix 截断的共同思路。

## 3. 核心概念

### 3.1 Bloom Filter（布隆过滤器）

用**位图**实现的概率型集合成员判断结构。它可能给出**假阳性**（说存在但其实不存在），但**绝不会给出假阴性**（说不存在就一定不存在）。构造时需确定两个参数：位图大小与哈希函数个数 k。

### 3.2 False Positive / False Negative（假阳性 / 假阴性）

**假阳性**：元素不在集合中，过滤器却说「可能存在」——后果是多做一次真实查找，只是浪费。
**假阴性**：元素在集合中，过滤器却说「不存在」——后果是**漏数据**，是正确性错误。布隆过滤器在设计上排除了这种情况。

### 3.3 Counting Bloom Filter（计数布隆过滤器）

把位图的每一位换成**整数计数器**，插入时加一、删除时减一。这样支持动态删除，代价是空间放大数倍。

### 3.4 Cuckoo Filter（布谷鸟过滤器）

用 Cuckoo 哈希表存元素的**指纹（fingerprint）**而非完整键。支持插入与删除，空间效率通常优于计数布隆过滤器。

### 3.5 SuRF（Succinct Range Filter，精简范围过滤器）

CMU 提出的**不可变紧凑 Trie**，支持近似的精确匹配**与范围过滤**。布隆过滤器只能回答点存在性，SuRF 能回答「这个范围内可能有键吗」。

### 3.6 Skip List（跳表）

多层有序链表。最底层包含全部键，每往上一层键数减半（每个键以 1/2 概率晋升）。查找从顶层开始，能跳就跳、不能跳就下降。期望 O(log n)，且插入/删除**不需要全局再平衡**。

### 3.7 Trie（字典树 / 前缀树）

把键按**数字位（digit）**逐位展开成树的结构，又称 digital search tree、prefix tree。路径即键，键**隐式存储**、可由路径重建。所有操作 O(k)，k 为键长。树形只取决于键集合与长度，**与插入顺序无关**，且不需要再平衡。

### 3.8 Key Span（键跨度）

Trie 每一层的一个 digit 代表多少个比特。span 决定了每个节点的 fanout 与树的高度：n-way trie 的 fanout 为 n。span = 1 时是二叉 trie，span = 8 时是 256 路。

### 3.9 Radix Tree（基数树 / Patricia Trie）

**垂直压缩**过的 Trie：把只有一个子节点的链合并成一个节点，节点内存一段字符串前缀。压缩后不再保存完整键，因此可能产生**假阳性**，DBMS 必须回表检查原始元组。

### 3.10 Inverted Index（倒排索引）

存「**词项（term）→ 包含该词项的记录列表（posting list）**」的映射，又称全文搜索索引。历史上叫 concordance（可追溯到 13 世纪）。结构上分两部分：**字典（dictionary）** 与 **倒排表（posting list）**。

### 3.11 Finite State Transducer（FST，有限状态转换器）

Lucene 用来实现倒排索引字典的结构：一个 Trie 状的图，但**边上存权重（weight）而不是指针**。沿路径把权重累加，最终得到该词项在字典中的**偏移量**。因为权重预先算好，结构是**不可变**的。

### 3.12 Vector Index（向量索引）

对**嵌入向量（embedding，一维浮点数组）**做最近邻搜索的专用结构。语义相近的文本其向量在几何上靠近。两条主流路线：倒排聚类（IVF）与图（HNSW）。

### 3.13 Embedding（嵌入向量）

由大语言模型/Transformer 把文本转成的一维浮点数组。语义相似 → 向量距离近。查询时把查询文本也编码成向量，再在向量索引中找最近的若干条。

### 3.14 Partial Index（部分索引）

带 `WHERE` 子句的索引，只覆盖表中满足条件的子集。减小索引体积与维护开销。常见用法是按时间分区建索引（每月/每年一个）。

### 3.15 Index Include Columns / Covering Index（包含列 / 覆盖索引）

用 `INCLUDE (...)` 把非键列附加到索引的**叶子节点**。若查询需要的全部属性都在索引里，DBMS 就**不需要回表**——这种扫描叫 index-only scan。

## 4. 通俗理解

- **布隆过滤器 = 门口的保安名单**。名单只有几行「暗号位」，不写名字。你说出名字，保安按两个规则算出两个位置，看这两格是否都被涂黑：有一格没涂黑 → 你**肯定不在**名单里，直接走人；两格都黑 → 可能在里面，得进去核实。名单只涂不改，所以**没法删人**（删了会把别人的格子擦掉）。偶尔有「两格恰好都被别人涂黑」的倒霉蛋被误放进场——这就是假阳性，代价只是白跑一趟。
- **跳表 = 高速公路 + 匝道**。底层是逐户访问的小路，上面每隔几户设一个高速出口。找远的地方先上高速，快到了再下来走小路。修高速不需要拆迁（不需要再平衡），只要抛硬币决定这户要不要开出口。
- **Trie = 按字母分格的档案柜**。第一格按首字母分，第二格按第二个字母分……查 `HELLO` 就是 H→E→L→L→O 一路开抽屉。抽屉数量只取决于有哪些单词，跟你按什么顺序归档无关。
- **Radix Tree = 把只有一个抽屉的整列柜子合并成一个长标签**。省地方，但标签只写了前缀（如 `ELLO`），可能把 `HELLO` 和 `HELLP` 混为一谈——所以要回原始档案核对。
- **倒排索引 = 书末的索引页**。「Pavlo → 第 3、17、42 页」，而不是让你从第 1 页读到最后一页找这个词。
- **向量索引 = 按「意思」聚类的书架**。你说「关于逃避警察的说唱」，它不是找包含这些词的 album，而是把这句话编码成一个点，去找书架上坐标最近的那几本书。

具体数字：一个 8 位位图 + 2 个哈希函数的布隆过滤器，插入 `RZA` 与 `GZA` 后（占用 4 位），查询 `ODB`（从未插入）会返回 TRUE——因为 `hash1('ODB') % 8 = 3` 与 `hash2('ODB') % 8 = 6` 恰好分别被 `GZA` 与 `RZA` 涂黑。这就是一次假阳性：白跑一趟，但绝不漏。

## 5. 原理与推导

### 5.1 动机：B+ 树回答不了「不存在」

B+ 树的内部节点键只是路标，**不能告诉你某个键是否存在**——你必须走到叶子才能确认（讲义第 62 页明确指出这一点）。这意味着：查询一个不存在的键，要付出**每层一次缓冲池页缺失**的代价。在一棵 4 层的树里，就是 4 次 I/O 换一个「不存在」的答案。

**布隆过滤器正是为此而生**：把它放在 B+ 树（或哈希表、SSTable）**前面**，先花几十纳秒判断「可能存在吗」：

```
过滤器说不存在  → 直接返回空，省掉 4 次 I/O
过滤器说可能存在 → 走正常查找流程（可能白跑）
```

讲义强调：索引与过滤器**都需要**，而且常常**组合**使用。同一个思路出现在第 5 讲的 SSTable key filter、第 7 讲的哈希桶过滤器。

### 5.2 布隆过滤器的算法与误差方向

**结构**：m 位的位图（初始全 0）+ k 个独立哈希函数。

**Insert(x)**：

```
for i in 1..k:
    pos = hash_i(x) % m
    bitmap[pos] = 1
```

**Lookup(x)**：

```
for i in 1..k:
    pos = hash_i(x) % m
    if bitmap[pos] == 0:
        return "DEFINITELY NOT PRESENT"     # 假阴性不可能
return "MAYBE PRESENT"                       # 需真实查找确认
```

**为什么绝无假阴性**：若 x 曾被插入，插入时已把它的 k 个位置全部置 1。位图只会从 0 变 1、**永远不会从 1 变 0**（无删除），所以之后任何时刻查 x，这 k 位必然都是 1，Lookup 必然返回 "MAYBE PRESENT"。这是**单调性**带来的硬保证。

**为什么会有假阳性**：其他元素的插入可能恰好把 x 的 k 个位置全部涂黑。此时 x 从未插入，但所有位都是 1。

**讲义的具体推导**（`09-indexes2.pdf` 第 9–24 页，8 位位图、2 个哈希函数）：

```
Insert 'RZA':  hash1('RZA') = 2222 % 8 = 6   → 置位 6
               hash2('RZA') = 4444 % 8 = 4   → 置位 4
Insert 'GZA':  hash1('GZA') = 5555 % 8 = 3   → 置位 3
               hash2('GZA') = 7777 % 8 = 1   → 置位 1

位图状态: [0, 1, 0, 1, 1, 0, 1, 0]   （位 1、3、4、6 为 1）

Lookup 'RZA':   位 6=1, 位 4=1  → TRUE（真阳性）
Lookup 'Raekwon': hash1 = 3333 % 8 = 5 → 位 5 = 0 → FALSE（正确排除）
Lookup 'ODB':   hash1 = 6699 % 8 = 3 → 位 3 = 1
                hash2 = 9966 % 8 = 6 → 位 6 = 1
                → TRUE，但 ODB 从未插入 → 这是假阳性！
```

> 说明：`ODB` 的两个位置（3 与 6）分别由 `GZA` 与 `RZA` 涂黑，因此返回 TRUE。位图只有 8 位却装了 2 个元素、共 4 位，装载率已达 50%，假阳性率自然很高——这是**故意选的小例子**，用于演示误差方向。

**为什么不能删除**：删除意味着把某些位从 1 改回 0。但那些位可能**被多个元素共享**（如上的位 3 同时服务 `GZA` 与 `ODB` 的查询），清掉它会让真正存在的元素变成假阴性——破坏了「绝不漏」的唯一硬保证。

**参数与假阳性率**：设插入 n 个元素、位图 m 位、k 个哈希函数，假阳性率近似为

```
f ≈ (1 - e^(-kn/m))^k
```

最优哈希函数个数为 `k* = (m/n) ln 2 ≈ 0.693 × (m/n)`。直观结论：**每个元素分配约 10 位、用 7 个哈希函数时，假阳性率约 1%**。这就是「10 bits per key ≈ 1% FPR」这一经验法则的来源。

**权衡**：位图越大假阳性越低，但占内存/缓存；k 越大每次查询的哈希次数越多。DBMS 通常在「过滤器多少能省下的 I/O」与「过滤器占的内存」之间权衡。

### 5.3 三种改进型过滤器

| 结构 | 解决什么 | 代价 |
|---|---|---|
| Counting Bloom Filter | 支持**删除**（每位换成计数器，插入 +1、删除 −1） | 空间放大数倍（每格 4+ 位）；计数器溢出风险 |
| Cuckoo Filter | 支持**删除**且空间效率更高（存指纹，用 Cuckoo 哈希定位） | 高装载率时插入可能失败需扩容；有假阳性 |
| SuRF | 支持**范围过滤**（布隆只能点查） | 不可变（需重建）；实现复杂 |

**SuRF 的意义**：B+ 树范围查询的痛点是「扫描时不断发现区间里其实没有键」。布隆过滤器无法回答「[a, b] 区间内可能有键吗」，SuRF 用紧凑 Trie 的前缀信息可以回答，从而跳过空的子树。

### 5.4 跳表：结构、复杂度与并发

**结构**（讲义第 35 页的示意）：

```
Level 3 (P = N/4):  K1 ──────────────→ K4 ──────→ ∞
Level 2 (P = N/2):  K1 ──────→ K2 ────→ K4 ──────→ ∞
Level 1 (P = N):    K1 → K2 → K3 → K4 → K5 → K6 → ∞
```

**查找**（第 55–60 页，找 `K3`）：

```
从顶层开始：
  在当前层沿链表前进，直到「下一个键 > 目标」
  然后下降到下一层，从当前位置继续
重复直到最底层，检查该位置的键是否等于目标

示例：K3 < K5（顶层走到 K4 前停下，因为 K4 > K3? → 实际先比较 K3<K5）
      K3 > K2 → 从 K2 继续
      K3 < K4 → 下降到下一层
      最终在底层找到 K3
```

**插入**（第 40–54 页，插入 `K5`）：

```
1. 找到每层应插入的位置（同查找）
2. 从最底层开始向上：抛硬币决定这一层是否插入
   正面 → 插入该层并继续向上抛；反面 → 停止
3. 示例：K5 连续两次抛硬币成功，故出现在第 1、2 层
   （讲义注：K2 与 K4 只通过了第一次抛硬币，其余键第一次就失败）
```

每层晋升概率 1/2 保证期望上每一层的元素数是下一层的一半，因此期望查找代价 O(log n)。

**为什么不需要再平衡**：B+ 树必须维护「完美平衡 + 至少半满」这两个**结构性不变量**，插入/删除一旦破坏就要分裂/合并。跳表的结构不变量只是「每层是有序链表」，插入一个节点只是改动几个指针，**不会破坏任何全局性质**——随机化替代了确定性再平衡。代价是**最坏情况**（所有硬币都反面，退化成单层链表）为 O(n)，只是概率极低。

**删除**：直接把节点从各层链表中摘除。notes 补充了一个并发友好的做法：每个节点带一个 **deleted 布尔标记**，先标记、后真正删除（由后台线程定期回收），避免读者线程访问已释放对象；真正删除时**先删上层节点再删下层**，以保持结构完整。

**并发插入**（notes）：**从下往上**插入。若从上往下，另一个线程可能先看到上层节点，却发现它还没有指向下层的指针，从而读到不完整结构。若链表是**单向**的，每层的插入可用一次**原子指针交换**完成，无需 latch。

**两个缺点**（讲义第 61 页）：

- **对磁盘/缓存不友好**：节点分散在堆上，没有局部性优化（B+ 树把几百个键塞进一页，一次 I/O 拿一大批）。
- **反向扫描困难**：单向链表无法倒着走；加反向指针能解决，但会增加内存与维护成本（也就抵消了「比 B+ 树省内存」的优势）。

**用武之地**：内存中的 **MemTable**（LSM 树的写缓冲）、Redis 的有序集合、LevelDB/RocksDB 的 memtable。这些场景数据在内存、写多、需要有序遍历，正好避开跳表的两个缺点。

### 5.5 Trie：形状与键集合绑定

**结构**（第 63–67 页，键 `HELLO`、`HAT`、`HAVE`）：

```
            H
            |
            A
          /   \
         T     V
               |
               E
               |
               L
               |
               L
               |
               O
```

**三条关键性质**：

1. **形状只取决于键集合与键长**，与插入顺序无关。插入 `HELLO, HAT, HAVE` 与插入 `HAVE, HELLO, HAT` 得到完全相同的树。这与 B+ 树、AVL 树都不同（后者的形状依赖插入顺序）。
2. **不需要再平衡**：没有「半满」「平衡」这类不变量，插一个键只是沿路径新建节点。
3. **O(k)**：代价只与键长 k 有关，**与集合大小 n 无关**。这是它相对 B+ 树 O(log n) 的理论优势——查 100 万个 8 字符的键，B+ 树要 ~20 次比较，Trie 只要 8 次。

**键隐式存储**：路径上的 digit 序列就是键，节点里不需要存完整键（只存「这是否是一个键的终点」的标志与元组指针）。这省下大量空间。

**Key Span 与 fanout**（第 68–79 页）：span = 每层 digit 的比特数。

```
Keys: K10 → 00000000 00001010
      K25 → 00000000 00011001
      K31 → 00000000 00011111
1-bit span trie：每层看 1 位 → 每节点 2 个分支
  → 3 个键都是 16 位整数，高位有 10 个 0（"Repeat 10x"）
  → 树高 = 16 层，大量单链节点（浪费）
```

**问题**：键的前缀高度重复时（如所有键都以 10 个 0 开头），1-bit trie 会产生长链，浪费空间与遍历时间。这直接引出压缩。

**span 的选择**：span 越大 → fanout 越大 → 树越矮，但每节点越大、稀疏时浪费越多。span = 8 时是 256 路 trie（每字节一层），这是多数实现的默认（如 ART）。

### 5.6 Radix Tree：两种压缩与假阳性的来源

**水平压缩（horizontal compression）**：若某层的 span 已知且固定，把「digit → 子节点」的映射从**哈希表/数组映射**换成**定长数组**，用 digit 直接下标索引。省掉间接查找。

**垂直压缩（vertical compression）**：若某节点只有一个子节点，把这条单链合并成一个节点，节点内存一段**字符串前缀**。合并后的结构就是 **Radix Tree**，二叉情形也叫 **Patricia Trie**。

**讲义示例**：上面 1-bit trie 中连续 10 个 0 的单链节点，压缩成一个「跳 10 位」的节点。

**为什么产生假阳性**：压缩后节点里存的是**键的前缀片段**，完整键不再存在于路径上。若查询的键恰好与某个已存键共享前缀，但后缀不同，遍历会一路匹配前缀、到达叶子，此时 Trie **无法判断后缀是否真的相等**——它必须回表取原始元组比较。所以压缩 Trie 的匹配是「可能的匹配」，需要通过元组验证。

**修改操作的复杂性**（第 86–95 页）：

- **Insert `HAIR`**：需要在 `HA` 节点下插入 `IR` 分支，同时保持 `ELLO`、`T`、`VE` 三条已有分支。
- **Delete `HAT`**：删除 `T` 分支。
- **Delete `HAVE`**：删除 `VE` 分支后，`HA` 节点只剩一条 `IR` 分支，此时应把 `HA` 与 `IR` **合并**成一条链（保持压缩性质）。讲义最后一步把 `HA` + `IR` 合并为 `HAIR` 路径，正是垂直压缩的维护。

因此 Radix Tree 的删除比 Trie 复杂：删完要检查是否需要「反压缩」（合并单链）。

### 5.7 Trie 的四个真实实现

| 实现 | 出处 | 特点 |
|---|---|---|
| Judy Arrays | HP | 256 路 radix tree，**第一个支持自适应节点表示**的 radix tree |
| ART（Adaptive Radix Tree） | HyPer | 256 路 radix tree，**节点类型随填充度自适应**（Node4 / Node16 / Node48 / Node256） |
| Masstree | Silo | B+ 树，但**每个节点内部用 trie** 做键值映射 |
| SuRF | CMU | 压缩的**静态** trie，支持点查与范围查询（也用作过滤器） |

**ART 的自适应节点**是这类结构的核心技巧：节点里只有 4 个键时用线性扫描的小数组（Node4），16 个时用有序数组，48 个时用「256 项索引数组 + 紧凑键数组」，256 个时才用完整 256 项数组。这样既保持 256 路的高 fanout，又不在稀疏时浪费内存。

### 5.8 倒排索引：字典与倒排表

**问题**（第 97–100 页）：`SELECT pageID FROM revisions WHERE content LIKE '%Pavlo%'` 无法用 B+ 树加速，因为 `%...%` 不是前缀匹配；即使建了 `CREATE INDEX idx_rev_cntnt ON revisions (content)`，也只能全索引扫描。

**结构**（第 101–106 页）：

```
Dictionary（字典，有序）        Posting Lists（倒排表）
  Wu-Tang | 2   ────────────→  [11, 44]
  Carnegie| 3   ────────────→  [11, 22, 33]
  Database| 2   ────────────→  [33, 44]
  ...
                     ↑ 数字是 term frequency（词频）
```

字典通常**有序**（便于前缀查询与前缀压缩）；倒排表是记录 id 的列表，按 id 升序存放以便求交集（AND 查询）。

**两种查询**：

```
单词查询:  在字典里找 term → 取出 posting list → 回表取记录
多词 AND:  各取 posting list → 求交集（有序归并，O(n1+n2)）
多词 OR:   求并集
```

**为什么有 term frequency**：它是排序（ranking）的输入——TF-IDF、BM25 都用词频计算相关性。

### 5.9 两种实现：Lucene FST vs PostgreSQL GIN

**Lucene：Finite State Transducer**（第 107–112 页）

```
问题：字典可能有上亿个 term，如何既省空间又快速定位？
做法：用 FST —— 一个 Trie 状的图，但边上存「权重」而非指针
      沿路径把权重累加，得到该 term 在字典中的偏移量
```

讲义示例：查 `PAV`。

```
根 → B (weight=1) → R (weight=0) → A (weight=1) → V (weight=0) → 终点
根 → P (weight=2) → A (weight=1) → V (weight=0) → 终点   → Offset = 2
根 → P → L (weight=2) → A (weight=0)                    → Offset = 3
```

`PAV` 的路径权重累加得 2，即它在字典中的偏移为 2（排在 `BR`、`BRAV` 之后）。**关键洞察**：FST 把「指针」换成了「可累加的权重」，于是整个结构可以按字节紧凑编码，且**不需要存指针**——这是 Lucene 字典能塞进内存的原因。

**不可变性与增量更新**：权重是预先算好的（取决于字典中有哪些 term 及其顺序），所以 FST **不可变**。增量更新的做法是：

```
1. 为新插入的键单独建一个小 FST（segment）
2. 后台任务定期把多个 segment 合并（merge）成更大的 FST
```

这是 LSM 思想在索引上的应用（与第 5 讲的 SSTable compaction 同构）。

**压缩与预聚合**：字典有序且不可变，因此可用 **delta 压缩**与**位打包**（第 6 讲的编码技术）。Lucene 还支持对 term 与出现次数做**预聚合**，加速按 term 分组的聚合查询。

**PostgreSQL GIN（Generalized Inverted Index）**（第 113–118 页）

```
Dictionary：用 B+ 树实现（term → posting list）
Posting list 的内容随记录数变化：
  → 记录少：有序的 record id 数组
  → 记录多：再建一棵 B+ 树（posting tree）存 record id
Pending List：独立的日志，累积小批量更新，再批量灌入字典
```

**两个设计要点**：

1. **posting list 的双形态**：少量记录时用紧凑数组（省空间、扫描快），大量记录时改用 B+ 树（支持增量插入与快速查找单个 id）。这与「小表用数组、大表用树」的一般原则一致。
2. **pending list**：倒排索引的更新代价高（要修改字典与倒排表，可能触发页分裂）。GIN 把增量更新先写进 pending list（本质是一个 mod log，与第 6 讲 InnoDB 的 mod log 同思路），查询时同时查主索引与 pending list，后台再批量合并。这把随机写转成顺序写、把小写放大成大写。

### 5.10 倒排索引的两项增强

**排名（Ranking）**：按 term 在记录中的频率相对于其他记录的高低给结果打分。

```
TF-IDF：词频（TF）× 逆文档频率（IDF）
        TF 高 → 该词在这篇文档里重要
        IDF 高 → 该词在整个语料里罕见，区分度强
BM25：TF-IDF 的改进版，加入文档长度归一化与饱和效应
```

**分词器（Tokenizer）**：把词切成 n-gram 以支持模糊搜索与自动补全。

```
'Wu-Tang' 的 tri-grams: WuT, uTa, Tan, ang
→ 查询 'Wu Tang'（空格代替连字符）也能命中，因为共享多个 tri-gram
→ 支持 "did you mean" 式的拼写纠错
实现：Elasticsearch N-gram tokenizer、PostgreSQL pg_trgm
```

### 5.11 向量索引：为什么没有「正确答案」

**动机**（第 124 页）：倒排索引按**内容**匹配，依赖语言学模型做归一化（`Wu-Tang` 匹配 `Wu Tang`）。但应用可能想按**语义**搜索：「关于逃避警察的说唱」——这个查询里没有任何词会出现在歌词中。

**流程**（第 125–136 页）：

```
1. 用 Transformer/LLM 把每条记录的文本编码成 embedding（一维浮点数组）
   Id1 → [0.32, 0.78, 0.30, ...]
2. 用 embedding 建向量索引
3. 查询时把查询文本也编码成向量
4. 在向量索引中找最近的若干条 → 返回按相似度排序的 id 列表
5. 常需要与结构化条件组合：'released after 2010' → year > 2010
```

**与前面所有索引的根本差异**：

- **没有「正确答案」**。B+ 树的点查要么命中要么不命中；向量搜索返回的是「最相似的 k 条」，正确性取决于结果「感觉对不对」（讲义原文：Result correctness depends on whether the result "feels right"）。这是**近似最近邻（ANN）**问题。
- **需要与结构化过滤结合**。`year > 2010` 这类条件要么在向量搜索**前**过滤（先缩小候选集，但可能破坏索引结构），要么在**后**过滤（先取 k×m 个候选再筛，可能筛不够）。这是向量数据库的核心工程难题之一。

**两条路线**：

**① 倒排聚类（IVF，Inverted File）** —— 第 139–150 页

```
建索引：
  1. 对全部 embedding 做 k-means 聚类，得到若干 centroid
  2. 把每个 embedding 分到最近的 centroid 所属的簇
  3. 建倒排索引：centroid → 该簇内记录的 posting list
查询：
  1. 计算查询向量最近的 centroid
  2. 扫描该簇的 posting list，计算距离
  3. 为提高召回率，还要检查**邻近的几个簇**（nprobe 参数）
优化：
  → 预处理/量化（quantization）降低维度以加速，原始向量仍完整保留
  实现：IVFFlat、pgVector
```

核心权衡是 **nprobe**：只查 1 个簇快但可能漏（召回率低）；查更多簇慢但更准。这与「布隆过滤器的假阳性率」是同一类「用精度换速度」的旋钮。

**② 图（HNSW，Hierarchical Navigable Small World）** —— 第 151–171 页

```
建索引：
  每个节点是一个向量，边连向它的（最多）n 个最近邻
查询：
  1. 从入口点（entry point）进入图
  2. 贪心地选择「能让我更接近查询向量」的那条边
  3. 重复直到没有更近的邻居
多层结构：
  像跳表一样建多层图 —— 上层稀疏（长距离跳跃），下层稠密（精细定位）
  查询从最上层开始，逐层下降
实现：Faiss、hnswlib、DiskANN
```

**为什么用多层**：单层图的贪心搜索容易陷入局部最优（近邻图不连通或「绕远路」）。多层结构让上层承担「长跳」，下层承担「精修」，与跳表用多层链表加速的思路完全一致——讲义也明确说 "with the idea similar to skip lists"。

**工程细节**：DiskANN 把图放在 SSD 上（内存只放压缩后的向量），面向十亿级规模；hnswlib 是全内存实现；Faiss 提供多种量化方案（PQ、SQ）。

### 5.12 部分索引与包含列

**部分索引（Partial Index）**（第 172–176 页）

```sql
CREATE INDEX idx_foo ON foo (a, b) WHERE c = 'WuTang';

-- 该索引可服务：
SELECT b FROM foo WHERE a = 123 AND c = 'WuTang';
```

- **省空间**：只索引满足 `c='WuTang'` 的行。
- **省维护**：不满足条件的行更新时不需要改索引。
- **常见用法**：按时间范围分区建索引（每月/每年一个），查询时只碰相关月份的索引；也可用于「只索引活跃行」（`WHERE status='active'`），因为历史行几乎不查。

**包含列（Index Include Columns / Covering Index）**（第 177–184 页）

```sql
CREATE INDEX idx_foo ON foo (a, b) INCLUDE (c);

-- 索引里已含 a、b、c，故无需回表：
SELECT b FROM foo WHERE a = 123 AND c = 'WuTang';
```

- 额外列**只存在叶子节点**，**不是搜索键的一部分**——它们不参与排序与路由，因此不能用于缩小扫描范围。
- 若查询需要的全部属性都在索引中，DBMS 就**不需要回表取元组**（index-only scan）。这避免了随机 I/O，是提升覆盖查询性能的标准手段。
- 与「把 c 加进键」的区别：`(a,b,c)` 会改变排序（c 参与路由），能加速 `a=1 AND b=2 AND c=3`；`(a,b) INCLUDE (c)` 只让 c 可读，不能用于范围缩小。所以选哪种取决于 c 是「过滤条件」还是「输出列」。

### 5.13 全景对比

| 结构 | 回答什么问题 | 有序 | 复杂度 | 典型场景 |
|---|---|---|---|---|
| B+ 树 | 键在哪（点查/范围） | ✓ | O(log_m n) | 通用索引 |
| 布隆过滤器 | 键可能存在吗 | ✗ | O(k) | 挡掉不存在的键 |
| 哈希表 | 键在哪（仅等值） | ✗ | O(1) 期望 | 内存哈希索引、连接 |
| 跳表 | 键在哪（有序、内存） | ✓ | O(log n) 期望 | MemTable、Redis |
| Trie / ART | 前缀、点查 | ✓ | O(k) | 字符串键、内存索引 |
| Radix Tree | 前缀（压缩） | ✓ | O(k) | ART、Judy、路由表 |
| 倒排索引 | 哪些记录含此词 | ✓（字典） | O(log |V|) + 扫表 | 全文搜索 |
| 向量索引 | 哪些记录语义最近 | ✗ | 近似 | 语义搜索、RAG |
| SuRF | 区间内可能有键吗 | ✓ | O(k) | 范围过滤 |

## 6. 代码示例

### 6.1 讲义原文示例

**索引 vs 过滤器**（`09-indexes2.pdf` 第 3 页）：

```
An index data structure of a subset of a table's attributes that are
organized and/or sorted to the location of specific tuples using those
attributes.  → Example: B+Tree

A filter is a data structure that answers set membership queries; it tells
you whether a key (likely) exists in a set but not where it is located.
  → Example: Bloom Filter
```

**布隆过滤器 API**（第 6 页）：

```
Probabilistic data structure (bitmap) that answers set membership queries.
  → False negatives will never occur.
  → False positives can sometimes occur.

Insert(x): Use k hash functions to set bits in the filter to 1.
Lookup(x): Check whether the bits are 1 for each hash function.
```

**讲义的哈希计算**（第 9、12、15、18、22 页）：

```
hash1('RZA')     = 2222 % 8 = 6
hash2('RZA')     = 4444 % 8 = 4
hash1('GZA')     = 5555 % 8 = 3
hash2('GZA')     = 7777 % 8 = 1
hash1('Raekwon') = 3333 % 8 = 5   → 位 5 为 0 → FALSE
hash2('Raekwon') = 8899 % 8 = 5
hash1('ODB')     = 6699 % 8 = 3
hash2('ODB')     = 9966 % 8 = 6   → 两位均为 1 → TRUE（假阳性）
```

**三种改进型过滤器**（第 25 页）：

```
Counting Bloom Filter
  → Supports dynamically adding and removing keys.
  → Uses integers instead of bits to count the number of occurrences
Cuckoo Filter
  → Also supports dynamically adding and removing keys.
  → Uses a Cuckoo Hash Table but stores fingerprints instead of full keys.
Succinct Range Filter (SuRF)
  → Immutable compact trie that supports approximate exact matches and
    range filtering.
```

**跳表的定义与优缺点**（第 34、61 页）：

```
Multiple levels of linked lists with extra pointers to skip over entries.
  → 1st level is a sorted list of all keys.
  → 2nd level links every other key.
  → 3rd level links every fourth key.
  → Each level has ½ the keys of one below it.
Maintains keys in sorted order without requiring global rebalancing.
  → Approximate O(log n) search times.
Mostly for in-memory data structures.
  → Example: LSM MemTable

Advantages:  May use less memory than a B+Tree, if you do not include
             reverse pointers. / Insertions and deletions do not require
             rebalancing.
Disadvantages: Not disk/cache friendly because they do not optimize
             locality of references. / Reverse search is non-trivial.
```

**为什么需要过滤器**（第 62 页）：

```
The inner node keys in a B+Tree cannot tell you whether a key exists in
the index. You must always traverse to the leaf node. This means that you
could have (at least) one buffer pool page miss per level in the tree just
to find out a key does not exist.
```

**Trie 的性质**（第 63、68 页）：

```
Use a digital representation of keys to examine prefixes one-by-one.
  → aka Digital Search Tree, Prefix Tree.
  → Shape depends on keys and lengths (does not depend on insertion order).
  → Does not require rebalancing operations.
  → All operations have O(k) complexity where k is the length of the key.
  → Path to a leaf node represents a key.
  → Keys are stored implicitly and can be reconstructed from paths.

The span of a trie level is the number of bits that each partial key /
digit represents.
  → This determines the fan-out of each node and the physical height.
  → n-way Trie = Fan-Out of n
```

**Radix Tree**（第 80 页）：

```
Vertically compressed trie that compacts nodes with a single child.
  → aka Patricia Trees (2-way tries)
Can produce false positives, so the DBMS always checks the original tuple
to see whether a key matches.
```

**四种 Trie 变体**（第 96 页）：

```
Judy Arrays (HP)      → 256-way radix tree; first known radix tree that
                        supports adaptive node representation.
ART Index (HyPer)     → 256-way radix tree that also adapts node types
                        based on its population.
Masstree (Silo)       → B+Tree that uses tries inside each node for its
                        key/value mapping.
SuRF (CMU)            → Compressed static trie that supports point and
                        range queries.
```

**为什么需要倒排索引**（第 97–101 页）：

```
The indexes that we've discussed are useful for "point" and "range" queries.
They are not good at keyword searches:
  → Example: Find all Wikipedia articles that contain the word "Pavlo"

CREATE INDEX idx_rev_cntnt ON revisions (content);
SELECT pageID FROM revisions WHERE content LIKE '%Pavlo%';   -- 用不上

An inverted index stores a mapping of terms to records that contain those
terms in the target attribute.
  → Sometimes called a full-text search index.
  → Originally called a concordance (1200s).
```

**Lucene 的 FST**（第 107–112 页）：

```
Uses a Finite State Transducer for determining offset of terms in dictionary.
Incrementally create dictionary segments and then merge them in the background.
  → Uses compression methods we previously discussed (e.g., delta, bit packing).
  → Also supports precomputed aggregations for terms and occurrences.

Dictionary: BR | BRAV | PAV | PLA
边权重:  B:1  P:2  A:1  R:0  A:1  A:0  L:2  V:0
Find PAV → Offset = 2
```

**PostgreSQL GIN**（第 113 页）：

```
PostgreSQL's Generalized Inverted Index (GIN) uses a B+Tree for the term
dictionary that map to a posting list data structure.
Posting list contents varies depending on number of records per term:
  → Few:  Sorted list of record ids.
  → Many: Another B+Tree of record ids.
Uses a separate "pending list" log to avoid incremental updates.
```

**倒排索引的两项增强**（第 119 页）：

```
Rankings: The DBMS can rank search results based on the frequency of terms
          in each record relative to other records.
  → Examples: TF-IDF, BM25
Tokenizers: Split terms into n-grams to support fuzzy text searches and
            autocomplete ("did you mean").
  → Examples: Elastic N-gram, pg_trgm

'Wu-Tang' 的 tri-grams: WuT | uTa | Tan | ang
```

**向量索引的两个前提**（第 137、124 页）：

```
Specialized data structures to perform nearest-neighbor searches on
embeddings (i.e., one-dimensional arrays of floating-point numbers).
  → May also need to filter data before / after vector searches.
  → Result correctness depends on whether the result "feels right".
Two approaches: Inverted Indexes | Graphs

Inverted indexes search data based on its contents with some term tweaking
based on linguistic models. Instead of searching for records containing
keywords, an application may want to search for records that are
semantically similar to topics.
```

**IVF 与图的流程**（第 139–151 页）：

```
IVF (IVFFlat, pgVector):
  1. Compute k-means clustering on embeddings to find centroids.
  2. Assign each embedding to the cluster with its closest centroid.
  3. Build an inverted index mapping centroids to a posting list.
  4. To find matches, compute centroid of closest cluster on search
     embedding and then evaluate posting list.
  → Preprocess / quantize vectors to reduce dimensionality.
  → Also check nearby groups to improve accuracy.

Graph (Faiss, hnswlib, DiskANN):
  Build a graph where each node represents a vector and it has edges to
  (at most) its n nearest neighbors.
  → Can use multiple levels of graphs (HNSW).
  To find a match, enter the graph and then greedily choose the next edge
  that moves closer to that vector.
```

**部分索引与包含列**（第 172–183 页）：

```sql
CREATE INDEX idx_foo ON foo (a, b) WHERE c = 'WuTang';
SELECT b FROM foo WHERE a = 123 AND c = 'WuTang';

CREATE INDEX idx_foo ON foo (a, b) INCLUDE (c);
-- "AKA covering index or index-only scans"
```

**结论页**（第 185 页）：

```
We will see filters again this semester.
B+Trees are still the way to go for tree indexes.
Inverted indexes are covered in CMU 11-442.
We did not discuss geo-spatial tree indexes:
  → Examples: R-Tree, Quad-Tree, KD-Tree
  → This is covered in CMU 15-826.
```

### 6.2 补充示例（非官方，仅用于说明概念）

**布隆过滤器的位图实现**：

```python
import hashlib

class BloomFilter:
    def __init__(self, m_bits, k):
        self.m = m_bits
        self.k = k
        self.bits = bytearray((m_bits + 7) // 8)

    def _positions(self, x):
        for i in range(self.k):
            h = hashlib.blake2b(f"{i}:{x}".encode(), digest_size=8).digest()
            yield int.from_bytes(h, "big") % self.m

    def insert(self, x):
        for p in self._positions(x):
            self.bits[p >> 3] |= 1 << (p & 7)

    def lookup(self, x):
        return all(self.bits[p >> 3] & (1 << (p & 7)) for p in self._positions(x))
        # False → 一定不存在；True → 可能存在，需回表确认
```

注意 `lookup` 的三值语义：`False` 是**确定的否定**，`True` 只是**可能**。调用方必须把 `True` 当作「继续查找」，而不能当作「存在」。

**虚假阳性率的估算**：

```python
import math

def fpr(n, m, k):
    return (1 - math.exp(-k * n / m)) ** k

# 每个元素 10 位、k = 7 时
for k in range(1, 10):
    print(k, round(fpr(1, 10, k) * 100, 2))   # 单位：%
# k=7 时约 0.82%——这就是「10 bits/key ≈ 1% FPR」的来源
```

**跳表的抛硬币插入**：

```python
import random

def random_level(p=0.5, max_level=32):
    lvl = 1
    while random.random() < p and lvl < max_level:
        lvl += 1
    return lvl
# 期望层数 = 1/(1-p) = 2；第 L 层约有 n * p^(L-1) 个节点
```

**Trie 的节点（radix 形式）**：

```python
class RadixNode:
    __slots__ = ("prefix", "children", "record_id")
    def __init__(self, prefix=""):
        self.prefix = prefix          # 压缩后存的一段前缀，而非单个 digit
        self.children = {}            # digit -> RadixNode
        self.record_id = None         # 非 None 表示这里是一个完整键的终点
```

`prefix` 字段正是垂直压缩的载体；`record_id` 非空表示该路径构成完整键。查询时必须**回表验证**，因为 `prefix` 可能只是真实键的一部分。

**倒排索引求交集（AND 查询）**：

```python
def intersect(a, b):
    # a、b 均为按 record id 升序的 posting list
    i = j = 0
    out = []
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            out.append(a[i]); i += 1; j += 1
        elif a[i] < b[j]:
            i += 1
        else:
            j += 1
    return out
# O(|a| + |b|)，前提是两条 posting list 都有序
```

**HNSW 贪心搜索的骨架**：

```python
def greedy_search(graph, entry, query):
    cur = entry
    while True:
        nxt = min(graph.neighbors(cur), key=lambda n: dist(n.vec, query), default=None)
        if nxt is None or dist(nxt.vec, query) >= dist(cur.vec, query):
            return cur
        cur = nxt
# 单层贪心可能陷入局部最优 → 所以 HNSW 用多层图，上层做长跳
```

## 7. 容易混淆的概念

| 概念对 | 区别 | 记忆要点 |
|---|---|---|
| 假阳性 vs 假阴性 | 前者「说存在其实不存在」（浪费一次查找）；后者「说不存在其实存在」（漏数据） | 过滤器只允许前者 |
| 布隆过滤器 vs 哈希表 | 前者只回答「可能存在」且不可删除；后者给出精确位置 | 一个筛查，一个定位 |
| 计数布隆 vs Cuckoo 过滤器 | 前者用计数器支持删除（空间放大）；后者存指纹（更省空间） | 一个加计数，一个存指纹 |
| 跳表 vs B+ 树 | 跳表靠随机化免再平衡但无局部性；B+ 树靠分裂合并保平衡但页内批量访问 | 一个随机，一个确定 |
| Trie vs Radix Tree | 前者每层一个 digit、存完整路径；后者压缩单链、可能假阳性 | 一个不压缩，一个压缩 |
| Trie vs 哈希表 | Trie 保序、支持前缀、O(k)；哈希无序、O(1)、不支持前缀 | 一个按位展开，一个打散 |
| 倒排索引 vs B+ 树索引 | 前者 term → 记录列表（多对多、按内容）；后者 key → 单条记录位置 | 一个按词，一个按值 |
| Lucene FST vs PostgreSQL GIN | 前者不可变 FST + 段合并；后者 B+ 树字典 + pending list | 一个不可变合并，一个日志缓冲 |
| IVF vs HNSW | 前者聚类 + 倒排表（查几个簇）；后者近邻图 + 贪心（多层级） | 一个分桶，一个走图 |
| 部分索引 vs 包含列 | 前者缩小**行**范围（WHERE）；后者扩充**列**（INCLUDE） | 一个减行，一个加列 |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Slides | `90-原始PDF/15-445/slides/09-indexes2.pdf` | 186 | 2（Project #1 due Sept 27、HW#3 due Oct 4、DRC #1 Oct 5、期中 Oct 7 覆盖 L01–11）、3（索引 vs 过滤器）、5（今日议程 + Flash Talk: Floe）、6（布隆过滤器 API）、7–24（8 位位图动画：Insert RZA/GZA，Lookup RZA/Raekwon/ODB）、25–29（计数布隆、Cuckoo、SuRF）、30–33（有序链表 O(n) 的动机）、34–54（跳表结构、插入与抛硬币）、55–60（跳表查找）、61（优缺点）、62（B+ 树内部键不能回答存在性）、63–67（Trie 示例 HELLO/HAT/HAVE）、68–79（key span：K10/K25/K31 的 1-bit trie）、80–85（Radix Tree 水平/垂直压缩）、86–95（Radix Tree 的插入与删除）、96（Judy/ART/Masstree/SuRF）、97–100（点查/范围查 vs 关键词搜索）、101–106（倒排索引字典 + posting list）、107–112（Lucene FST 与 offset 累加）、113–118（PostgreSQL GIN：B+ 树字典、posting tree、pending list）、119–123（Rankings 与 Tokenizers、tri-gram）、124–136（语义相似搜索与 embedding 流程）、137（向量索引两条路线与「feels right」）、139–150（IVF：k-means、centroid、posting list）、151–171（HNSW 图与多层贪心）、172–176（部分索引）、177–184（INCLUDE 列与 index-only scan）、185（结论：R-Tree/KD-Tree 属 15-826）、186（下讲预告：让索引线程安全） |
| Notes | `90-原始PDF/15-445/notes/09-indexes2.pdf` | 7 | 第 1 页（索引 vs 过滤器与哈希桶过滤器、布隆过滤器的参数与 Insert/Lookup、Figure 1）、第 2 页（Lookup 的三值语义、不可删除、三种变体、跳表结构与概率、Find 算法）、第 3 页（Insert 的抛硬币与自底向上、无 latch 的原子指针交换、Delete 的标记删除、跳表优缺点、Trie 定义与 span）、第 4 页（Trie 的水平/垂直压缩与假阳性、Inverted Index 定义与 posting list）、第 5 页（Lucene FST 的权重与 offset、不可变性与段合并、delta/位打包、PostgreSQL GIN 的 B+ 树字典与 pending list、Rankings 与 Tokenizers）、第 6 页（向量索引：embedding、IVFFlat 的 k-means 流程、图方法）、第 7 页（HNSW 的多层图、部分索引、包含列） |

原始 URL：

- Slides：`https://15445.courses.cs.cmu.edu/fall2026/slides/09-indexes2.pdf`
- Notes：`https://15445.courses.cs.cmu.edu/fall2026/notes/09-indexes2.pdf`

> 待核实：slides 第 18–20 页 `hash2('Raekwon') = 8899 % 8 =` 的数值在文本抽取中缺失（动画分步显示），本笔记据上下文推断为 5（与 `hash1('Raekwon')` 相同），需人工核对 PDF 原图。
> 待核实：slides 第 22–24 页 `ODB` 的两个哈希值（`6699 % 8` 与 `9966 % 8`）在抽取文本中未显示结果位；本笔记按 3 与 6 推导（恰好对应 GZA 与 RZA 的置位），需人工核对。
> 待核实：notes 第 3 页称跳表「若链表单向，每层插入可用原子指针交换完成，无需 latch」，但未讨论多层同时插入的可见性问题；该结论的适用范围建议以课堂讲解为准。

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内，本讲内容对应 2025 年第 9 讲）

- 标题：Indexes & Filters II — Bloom Filters, Skip Lists, Tries, Inverted Indexes（2025 年第 9 讲）
- URL：`https://www.youtube.com/watch?v=PjST2n7abAY&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 年份：2025
- 时间戳：未核实，故不标注。

## 10. 本节复习

- 能解释为什么 B+ 树的内部键无法回答「键不存在」，并说明布隆过滤器如何把「每层一次 I/O」变成「一次位图查询」。
- 能默写布隆过滤器的 Insert / Lookup，并从位图的单调性证明「绝无假阴性」。
- 能说明布隆过滤器为什么不能删除，以及三种改进型各自解决了什么。
- 能计算「m/n = 10、k = 7 时假阳性率约 1%」，并解释 k 的最优值为什么是 (m/n)ln2。
- 能描述跳表的多层结构、查找的「能跳就跳、不能跳就降」、插入的抛硬币，以及它为什么免再平衡。
- 能说出跳表的两个缺点与它的典型用武之地（MemTable）。
- 能说明 Trie 的 shape 与插入顺序无关、O(k) 的含义、span 与 fanout 的关系。
- 能解释 Radix Tree 的水平/垂直压缩，以及压缩后为什么必须回表验证。
- 能说出 ART 的自适应节点为什么能兼顾高 fanout 与低空间浪费。
- 能画出倒排索引的 dictionary + posting list，说出 Lucene FST（权重累加求 offset）与 GIN（B+ 树字典 + posting tree + pending list）的差别。
- 能描述 IVF 与 HNSW 的两条路线，说明向量搜索为什么「没有正确答案」、为什么需要前后过滤。
- 能区分部分索引（减行）与包含列（加列、免回表）。

## 11. 自我检查

**Q1.** 布隆过滤器为什么保证没有假阴性却有假阳性？如果允许删除会发生什么？请用讲义中 `RZA` / `GZA` / `ODB` 的例子说明。

<details><summary>参考答案</summary>

**为什么无假阴性**：插入 x 时把它 k 个哈希位置全部置 1。位图只会从 0 变 1，**永远不会从 1 变 0**（不支持删除）。因此只要 x 曾被插入，之后任何时刻查 x，这 k 位必然都是 1，Lookup 必然返回「可能存在」。这是**单调性**给出的硬保证。

**为什么有假阳性**：其他元素的插入可能恰好把 x 的 k 个位置全部涂黑。此时 x 从未插入，但所有位都是 1，Lookup 返回「可能存在」。讲义例子（8 位位图、2 个哈希函数）：

```
Insert 'RZA' → 置位 6（2222 % 8）与 4（4444 % 8）
Insert 'GZA' → 置位 3（5555 % 8）与 1（7777 % 8）
位图: 位 1、3、4、6 为 1

Lookup 'ODB' → hash1 = 6699 % 8 = 3（1）、hash2 = 9966 % 8 = 6（1）
             → 两位都是 1 → TRUE，但 ODB 从未插入 → 假阳性
```

而 `Lookup 'Raekwon'` 得到位 5，位 5 为 0，于是正确地返回 FALSE——**这正是过滤器有价值的地方**：它能可靠地排除不存在的键。

**如果允许删除**：删除意味着把某些位从 1 改回 0。但那些位**可能被多个元素共享**：上面的位 3 既服务 `GZA`（真实存在）也影响 `ODB` 的判断。若删除 `GZA` 时清掉位 3，那么将来查 `GZA`（若它被重新插入或仍在其他副本中）会得到假阴性；更严重的是任何依赖位 3 的元素都可能被误判为不存在。**一次假阴性就是漏数据**，破坏了过滤器唯一的硬保证。

因此布隆过滤器只能重建（重新插入全部现存键），或改用计数布隆过滤器 / Cuckoo 过滤器这类支持删除的变体。

</details>

**Q2.** 跳表为什么不需要再平衡就能保证期望 O(log n)？它的两个主要缺点是什么，为什么这些缺点在 MemTable 场景中不致命？

<details><summary>参考答案</summary>

**为什么免再平衡**：

B+ 树必须维护两个**确定性结构不变量**——「完美平衡」与「至少半满」。插入导致节点溢出就要分裂、删除导致欠满就要合并，这些操作会波及父节点甚至整棵树。跳表的结构不变量只有一条：「每一层都是有序链表」。插入一个键只是：

1. 找到各层的插入位置；
2. 从最底层开始，**抛硬币**决定是否插入这一层，正面则插入并继续向上抛，反面则停止。

任何一步都只改动几个指针，**不会破坏任何全局性质**，所以没有「再平衡」的概念。随机化替代了确定性再平衡。

**为什么期望 O(log n)**：每个键以 1/2 的概率晋升到上一层，因此第 L 层期望有 `n / 2^(L-1)` 个节点。层数期望为 2（几何分布），最高层约 log₂n。查找时每层最多走常数步（因为上一层节点间距是下一层的 2 倍），总步数 O(log n)。最坏情况（所有硬币都是反面）退化为单层链表 O(n)，但概率极低。

**两个缺点**：

1. **对磁盘/缓存不友好**：节点在堆上各自分配，指针追逐导致缓存缺失。B+ 树把一个节点（页）塞满几百个键，一次 I/O 就拿到一大批；跳表每下降一层几乎都要访问一个新节点。
2. **反向扫描困难**：单向链表无法倒着走。加反向指针可以解决，但会增加内存与维护复杂度——这恰好抵消了「比 B+ 树省内存」的优势。

**为什么在 MemTable 里不致命**：

- MemTable 完全在**内存**中，没有磁盘 I/O 的问题；缓存缺失的代价虽然存在，但比磁盘寻道低几个数量级。
- MemTable 的主要操作是**写入与有序遍历**（写满后要顺序刷成 SSTable）。有序遍历是单向的，正好不需要反向扫描。
- MemTable 生命周期短（写满即转为 SSTable），不需要极致的空间效率或长期的删除性能。
- 并发插入的实现也更简单（notes 指出：单向链表可用原子指针交换，从下往上插入即可避免读者看到不完整结构）。

相比之下，磁盘上的持久索引仍应选 B+ 树——这也是讲义结论「B+Trees are still the way to go for tree indexes」的含义。

</details>

**Q3.** Trie 的所有操作是 O(k)，B+ 树是 O(log n)。是不是说明 Trie 一定更快？请从空间、缓存、实际键长分布三个角度分析，并说明 Radix Tree 的压缩为什么引入假阳性。

<details><summary>参考答案</summary>

**不一定更快**，O(k) 只在「k 远小于 log n」且有大量共享前缀时才有优势。

**① 空间**：朴素 Trie 的每个节点要存一个 fanout 数组。1-bit span 时每节点 2 个指针，但键长 16 位就有 16 层；256 路 trie 每节点要 256 个指针（2 KB），若大部分为空则**极度浪费**。B+ 树把几百个键塞进一页，空间利用率高。

**② 缓存**：Trie 的查找要**逐层下降**，每层访问一个不同节点（很可能是不同的缓存行甚至不同的页）。B+ 树把 512 个键放在一页里，一次读入后节点内的二分查找全在缓存中。所以即使 Trie 的「比较次数」更少，**内存访问次数**往往更多。

**③ 实际键长分布**：若键都是 16 位整数且高位大量重复（讲义 `K10/K25/K31` 的例子：`00000000 00001010`、`00000000 00011001`、`00000000 00011111` 共享 10 个前导 0），朴素 Trie 会产生 10 层单链节点——O(k) 里的 k 全是浪费。这正是需要压缩的原因。

**Radix Tree 压缩为什么引入假阳性**：

垂直压缩把「只有一个子节点的链」合并成一个节点，节点内存一段**前缀字符串**而不是完整键。于是：

```
压缩前: H → A → V → E （路径即完整键 HAVE）
压缩后: 一个节点存 "HAVE"，到达即「看起来匹配」
```

问题在于，压缩后的路径**不再包含完整键的信息**。若树中存了 `HAVE` 而查询 `HAIR`，遍历可能匹配到共享前缀 `HA`，然后到达存着 `VE` 或 `IR` 的节点——此时结构只能告诉你「前缀匹配」，**无法证明整个键相等**（因为完整键没有被逐位存下来）。

所以 Radix Tree 的查找结果是「**可能的匹配**」，DBMS **必须回表取原始元组比较**才能确认。讲义明确写："Can produce false positives, so the DBMS always checks the original tuple to see whether a key matches."

这是用**空间换精度**的典型交易：压缩让树更矮更省空间，代价是引入了需要验证的假阳性。注意方向仍然是安全的——**不会有假阴性**（若键真的存在，路径必然匹配），只是可能多做一次验证。

</details>

**Q4.** 倒排索引的字典与 posting list 各承担什么职责？Lucene 用 FST、PostgreSQL 用 B+ 树 + pending list，两种设计各自的取舍是什么？

<details><summary>参考答案</summary>

**职责划分**：

- **字典（dictionary）**：term → posting list 的映射，通常**有序**。有序性支持前缀查询、前缀压缩，以及按范围扫描 term。它是「词表」。
- **Posting list（倒排表）**：包含该 term 的记录 id 列表，通常**按 id 升序**。有序性让多个 term 的 AND 查询可以用线性归并求交集，复杂度 O(n1+n2) 而非 O(n1×n2)。
- **term frequency**：与 posting list 一起存，供 TF-IDF / BM25 排序使用。

**Lucene 的 FST**：

- 用**有限状态转换器**替代普通 Trie：边上存**权重**而非指针，沿路径累加权重即得该 term 在字典中的**偏移量**。
- 好处：不需要指针，结构可以按字节紧凑编码，**整个字典能常驻内存**（Lucene 的核心竞争力）；天然支持前缀共享（`BR`、`BRAV` 共享前缀）。
- 代价：权重取决于「字典里有哪些 term、按什么顺序排列」，因此 FST **不可变**。更新只能「新建一个小 segment，后台合并」——这与 LSM 的 compaction 同构，带来**读放大**（查询要查多个 segment）与**合并开销**。
- 附加优势：不可变 + 有序 → 可以用 delta 压缩与位打包，还能预计算 term 的聚合。

**PostgreSQL GIN**：

- 字典用 **B+ 树**（可增量更新，无需重建），posting list 按规模**双形态**：少量记录用有序 id 数组（紧凑、扫描快），大量记录改用 **posting tree**（另一棵 B+ 树，支持增量插入与单 id 查找）。
- 代价：B+ 树字典的更新会触发页分裂，写放大明显；posting list 的插入也可能很贵。
- 缓解手段：**pending list**——增量更新先写入这个日志式的缓冲区，查询时同时扫主索引与 pending list，后台批量合并进字典。这把大量小随机写变成少量大顺序写（与 InnoDB 的 mod log 同思路）。
- 代价：查询路径变长（要查两处）、pending list 需要额外的空间与合并调度。

**取舍总结**：

| 维度 | Lucene FST | PostgreSQL GIN |
|---|---|---|
| 更新模型 | 不可变 + 段合并 | 可变 + pending list |
| 查询路径 | 查多个 segment，需归并 | 查主索引 + pending list |
| 空间效率 | 极高（无指针、可压缩） | 中等（B+ 树指针开销） |
| 写入延迟 | 低（只写新段） | 中（先写 pending list，合并时才贵） |
| 最适合 | 读多写少、需要极致查询性能 | 与事务型表混部、需要原地更新 |

两者本质上是**同一权衡的两种落点**：LSM 式的「不可变 + 后台合并」优化读路径的空间效率，B 树式的「原地更新 + 日志缓冲」优化写入的事务性。选择取决于工作负载的读写比与是否需要与事务系统紧密集成。

</details>

**Q5.** 向量索引与前面所有索引最根本的差别是什么？IVF 与 HNSW 各自的查询流程与调优旋钮是什么？为什么「先过滤再搜」与「先搜再过滤」都有问题？

<details><summary>参考答案</summary>

**最根本的差别：没有「正确答案」**。B+ 树、哈希表、倒排索引的查询结果都是**确定的**——键存在就返回，不存在就返回空。向量索引做的是**近似最近邻（ANN）**搜索，返回「最相似的 k 条」，而「最相似」在多高维空间里没有客观标准，讲义原文说：Result correctness depends on whether the result "feels right"。因此向量索引的评估指标是**召回率（recall@k）**与延迟，而不是「对/错」。

**IVF（倒排聚类，如 IVFFlat、pgVector）**：

```
建索引：k-means 聚类得到 centroid → 每个向量分到最近的簇
        → 建倒排索引 centroid → posting list
查询：  ① 算查询向量最近的 centroid
        ② 扫描该簇的 posting list，算距离排序
        ③ 再检查邻近的几个簇以提高召回
```

**调优旋钮**：簇数（nlist）与查询时检查的簇数（**nprobe**）。nprobe 越大召回越高、延迟越大。另有**量化（quantization）**降维以加速，原始向量仍完整保留以便精算。

**HNSW（多层近邻图，如 hnswlib、Faiss、DiskANN）**：

```
建索引：每节点连向它的（最多）n 个最近邻，建成多层图
        （上层稀疏做长跳，下层稠密做精修——与跳表同构）
查询：  从入口点进入，贪心地选「更接近查询向量」的边，
        直到没有更近的邻居；逐层下降
```

**调优旋钮**：每节点的邻居数 **M**（越大图越连通、召回越高、内存越大）、构建时的候选数 **efConstruction**、查询时的候选队列大小 **efSearch**（越大越准越慢）。

**为什么两种过滤顺序都有问题**：

- **先过滤再搜（pre-filter）**：先用 `year > 2010` 筛出候选集，再在这个子集上做向量搜索。问题是**索引结构被破坏**——IVF 的簇是按全部数据聚类的，子集可能让某些簇变空；HNSW 的图边可能全部指向被过滤掉的节点，导致图**不连通**，贪心搜索走不下去。解决成本高（要为每个过滤条件重建索引，或维护多份索引）。
- **先搜再过滤（post-filter）**：先取 k×m 个最近邻，再用 `year > 2010` 筛掉不合格的。问题是**可能筛不够**——若 99% 的数据都不满足条件，取 top-100 可能一条合格的都没有。加大 m 会线性增加延迟，且最坏情况仍需扫描全表。

因此工业界的折中包括：**过滤条件参与图遍历**（遍历时跳过不合格节点但仍用它们做「桥」）、**分区索引**（按过滤维度分片，每片一个向量索引）、以及**混合查询规划**（优化器按选择率决定用哪种顺序）。这也解释了讲义为什么把 "May also need to filter data before / after vector searches" 单列为向量索引的固有难点。

</details>

## 12. 进一步学习

- 上一讲：[[15-445-08-Indexes-and-Filters-I]] —— B+ 树的结构、插入删除、复合索引与优化。
- 下一讲：[[15-445-10-Index-Concurrency-Control]] —— 让索引线程安全：latch、crabbing、B-link 树。
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]、[[40-CMU-15-445/04-学习进度|CMU 15-445 - 学习进度]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：Bloom, *Space/Time Trade-offs in Hash Coding with Allowable Errors* (CACM 1970) —— 布隆过滤器原始论文。
- 延伸阅读：Pugh, *Skip Lists: A Probabilistic Alternative to Balanced Trees* (1990)；Herlihy et al. 关于并发跳表的实现讨论。
- 延伸阅读：Leis et al., *The Adaptive Radix Tree: ARTful Indexing for Main-Memory Databases* (ICDE 2013) —— ART 的原始论文。
- 延伸阅读：Zhang et al., *SuRF: Practical Range Query Filtering with Fast Succinct Tries* (SIGMOD 2018) —— CMU 出品，本讲提到的 SuRF。
- 延伸阅读：Malkov & Yashunin, *Efficient and Robust Approximate Nearest Neighbor Search Using HNSW Graphs* (TPAMI 2018)；Jégou et al., *Product Quantization for Nearest Neighbor Search* (TPAMI 2011) —— 向量索引的两条主线。
- 延伸阅读：Manning et al., *Introduction to Information Retrieval*（教材免费在线）—— 倒排索引、TF-IDF、BM25 的标准参考。
- 动手建议：用 Python 实现一个 8 位、2 个哈希函数的布隆过滤器，复现讲义中 `RZA`/`GZA`/`ODB` 的例子；再把位图扩到 1024 位、插入 100 个随机字符串，统计 1000 次不存在的键查询的假阳性率，与 `(1-e^(-kn/m))^k` 的理论值对照。
