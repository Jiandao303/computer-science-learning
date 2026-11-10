---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L21
topic: Distributed System Design, Part 2 - Caching, Invalidation, and Partitioning
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 分布式系统
  - 缓存
  - 缓存失效
  - 分区
  - 一致性哈希
---

# 第 21 讲 分布式系统设计（二）：缓存、失效与分区

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。

## 1. 本节学习目标

- 能解释「可用性（availability）」与「可扩展性（scalability）」这两个成功度量，并说明「5 个 9」意味着多少停机时间。
- 能画出客户端缓存、分层缓存、服务端缓存三种架构，并说明各自解决什么问题。
- 能对比基于时间（expiration）与基于更新（invalidation）两种失效策略的优缺点。
- 能说明 Belady 最优、LRU、LFU、Random 四种替换策略的差别，并解释为什么 Belady 最优无法实现。
- 能区分复制（replication）与分区（partitioning）：前者解决读吞吐与可靠性，后者解决写吞吐与容量。
- 能解释一致性哈希（consistent hashing）如何让「加/减一台服务器」只需移动少量数据。
- 能说明 master/tablet 架构中 master 与 tablet server 的职责分工。

## 2. 前置知识

- [[15-214-20-Distributed-Systems-Part1]]：失败模型、被动主备复制、端到端原则、健壮性原则。
- [[15-214-07-Design-Patterns]]：缓存本质上是「用空间换时间」，与 Proxy、Decorator 等结构型模式同源。
- 外部概念：哈希表与哈希函数、模运算、LRU 链表。

## 3. 核心概念

- **Reliability（可靠性）**：系统持续正确工作的能力；工程上常量化为**可用性（availability）**——系统处于可工作状态的时间占比。
- **5 nines（5 个 9）**：99.999% 可用性。一年约 31,536,000 秒，5 个 9 意味着全年不可用时间不超过约 **5.26 分钟**。
- **Scalability（可扩展性）**：系统处理负载增长的能力——加机器能否近似线性地提升吞吐。
- **Cache（缓存）**：把「计算/获取代价高的结果」存在离使用者更近的地方，用空间换时间。
- **Cache Invalidation（缓存失效）**：让缓存中的旧数据不再被使用的机制。分为时间驱动（过期）与更新驱动（广播失效）。
- **Cache Replacement Policy（缓存替换策略）**：缓存满了以后决定淘汰谁。
- **Replication（复制）**：同一份数据存在多个副本——提升读吞吐与可靠性。
- **Partitioning（分区）**：把数据按某个属性切分，不同分片放在不同服务器上——提升写吞吐与总容量。
- **Sharding（分片）**：水平分区的同义词（horizontal partitioning）。
- **Distributed Hash Table（分布式哈希表，DHT）**：每个服务器负责哈希空间的一个桶，前端对 key 求哈希后直接定位服务器。
- **Consistent Hashing（一致性哈希）**：把哈希值空间首尾相接成一个环，每个节点负责环上一段；增删节点时只影响相邻区间。
- **Master / Tablet（主控/子表）**：master 保存「区间 → 服务器」的映射，tablet server 存实际数据，前端缓存映射表。

## 4. 通俗理解

**缓存是什么？** 你每天上班要路过一家便利店。你不会每次都跑三公里外的大超市——你把常用的东西（牛奶、面包）先买一点放冰箱里。冰箱就是缓存。它让「重复的读取」变快，代价是「冰箱里的牛奶可能过期」。

**缓存失效是什么？** 过期就是两种处理方式：**时间驱动**——牛奶盒上印着保质期，到点就扔（哪怕它其实还没坏）；**更新驱动**——超市一上架新牛奶就打电话通知你「你冰箱里那盒该扔了」（哪怕你还没喝）。前者简单但可能浪费，后者精确但需要「打电话」的成本，而且电话可能打不通。

**分区是什么？** 一家公司人太多，一间办公室坐不下，就分成几个部门：CMU 的人在这层，Yale 的人在那层，MIT 的人在那层。找某个人时，先看他在哪个部门（哈希），再去那层找。**分区的核心是「把查找变成一次哈希 + 一次网络跳转」**。

**一致性哈希解决什么问题？** 普通哈希表扩容时，`hash % n` 里的 `n` 变了，几乎所有 key 的归属都会变——相当于把整仓库的货重新搬一遍。一致性哈希把哈希空间做成一个**环**，每台机器负责环上一段。加一台机器，只是从环上切下一段给它，其他区间纹丝不动。这就像在一条街上新开一家便利店——只有原本要跑远路的那一小片居民改去新店，其他人完全不受影响。

## 5. 原理与推导

### 5.1 两个成功度量

课件第 8 页给出两个度量：

- **可靠性（reliability）**，常以**可用性（availability）**表述：系统处于工作状态的时间比例。「99.999% 可用」就是「5 nines」。
- **可扩展性（scalability）**：处理负载增长的能力。

算一下 5 个 9 的分量：一年 365 天 = 31,536,000 秒，不可用时间 ≤ 0.001% × 31,536,000 ≈ **315 秒 ≈ 5.3 分钟**。也就是说，全年允许的故障总时长还不到一次午饭的时间。这对「主备复制要等所有 ack」这种设计提出了严峻挑战——任何一台备库抖动都可能突破这个预算。

这两个度量经常**互相拉扯**：为了可用性要复制，为了可扩展性要分区，而复制与分区都会让「一致性」变难（这将在 [[15-214-25-Data-Consistency]] 中展开，并最终收敛到 CAP 定理）。

### 5.2 复制的三种形态：缓存放在哪一层

课件把「客户端缓存」与「服务端缓存」作为复制的两种变体，其动机都是**可扩展性**（不是可靠性）。

**① 客户端缓存（client-side caching）**：把响应缓存在客户端或前端附近。

```
client → front-end → database server
              ↓
           cache（命中则直接返回，不打数据库）
```

**问题**：数据库吞吐太低。**方案**：在客户端（或前端）缓存响应，重复的读请求由缓存直接回答。

**② 分层客户端缓存（hierarchical client-side caches）**：缓存本身也分层次——本地内存缓存 → 前端共享缓存 → 区域缓存 → 数据库。这跟 CPU 的 L1/L2/L3 是同一个思路：越靠近使用者越快要小，越远越慢越大。

**③ 服务端缓存（server-side caching）**：在多台服务器上缓存响应，请求被负载均衡到任意一台都能命中。这解决的是「单台缓存服务器本身成为瓶颈」的问题。

三者的共同点：**都只加速读**。写必须穿透到数据库，否则就会出现「缓存与数据库不一致」。

### 5.3 缓存失效：时间驱动 vs 更新驱动

课件第 21 页给出两种策略，并留了一个思考题（各自的优缺点）。

**时间驱动（time-based invalidation，又称 expiration 过期）**

- 语义：**read-any, write-one**——读可以打到任意副本，写只写一个地方。
- 机制：旧缓存条目到时间自动丢弃。
- 只读数据**不需要**设置过期时间（永远不会变脏）。

| 优点 | 缺点 |
|---|---|
| 实现极简，无需任何协调 | 过期窗口内读到的是**旧数据**（stale） |
| 无需广播，可扩展性极好 | 过期时间难调：太短命中率低，太长不一致窗口大 |
| 数据库不可达时仍能降级服务 | 无法表达「这条数据已经变了」的语义 |

**更新驱动（update-based invalidation）**

- 语义：**read-any, write-all**——数据库更新时向所有缓存广播失效消息。
- 机制：缓存收到消息后删除对应条目（或标记为脏）。

| 优点 | 缺点 |
|---|---|
| 一致性强：数据一改，缓存立刻失效 | 需要广播，n 个缓存就是 n 条消息 |
| 过期时间可以设得很长，命中率高 | 广播丢失会导致长期脏读（必须有兜底过期） |
| 语义精确 | 数据库要维护「哪些缓存持有哪个 key」的映射 |

**工程上的常见做法是两者叠加**：以更新驱动为主（快速失效），同时设一个较长的过期时间作为**兜底（safety net）**——万一广播丢了，数据最多脏这么久。这是「乐观 + 兜底」的典型模式，和 [[15-214-20-Distributed-Systems-Part1]] 里主备复制的「唯一 ID 去重」是同一类思路：不指望某个机制永不失效，而是叠加一个成本更低的保护网。

### 5.4 缓存替换策略

缓存容量有限，满了必须淘汰。课件列出四种（并给「Common*」打了星号，暗示实际系统里最常用的是后三种）：

| 策略 | 规则 | 特点 |
|---|---|---|
| **Optimal（Belady 最优）** | 淘汰「未来最长时间内不会被用到」的条目 | 命中率理论上最高，但**需要预知未来**，不可实现；只用作评估其他策略的基准 |
| **LRU（Least Recently Used）** | 淘汰「最久未被访问」的条目 | 利用时间局部性；实现需维护访问顺序（链表 + 哈希）；对「扫描式访问」不友好（会冲掉热点） |
| **LFU（Least Frequently Used）** | 淘汰「访问次数最少」的条目 | 保护长期热点；但历史计数难衰减，新出现的热点会被旧热点压制（cache pollution） |
| **Random** | 随机淘汰一条 | 实现最简、无状态、无锁友好；实践中表现意外地不差，且能避免「所有节点同时淘汰同一条」的惊群效应 |

Belady 最优不可实现的原因很直接：要淘汰「未来最久不用」的，就必须知道未来的访问序列。但它给出了一个**上界**——如果你的策略在某个 trace 上离 Belady 很近，就说明已经很难再改进了。

一个常被忽略的点：**分布式环境下，随机淘汰比 LRU 更有优势**。如果所有缓存节点都用 LRU 且访问模式相似，它们会在同一时刻淘汰同一批条目，然后同时回源查询数据库——这叫**惊群（thundering herd）**。随机化能天然打散这种同步。

### 5.5 分区：把数据切开

复制的极限是「每台机器都存全量数据」——写放大不可避免。要真正提升**写吞吐**与**总容量**，必须分区。

课件的例子（第 23 页）：

```
CMU server:  {alice:90, pete:12, …}
Yale server: {deb:16, reif:40, …}
MIT server:  {cohen:9, bob:42, …}
```

每个前端根据某个属性（这里是学校）把请求路由到对应服务器。

**水平分区（horizontal partitioning，又称 sharding）** 是其中最常见的形式：把一张表按行切开。

| username | school | value |
|---|---|---|
| cohen | CMU | 9 |
| bob | CMU | 42 |
| alice | Yale | 90 |
| pete | Yale | 12 |
| deb | MIT | 16 |
| reif | MIT | 40 |

按 `school` 切分后，三台服务器各存两行。查询 `WHERE school='CMU'` 只需访问一台；但查询 `WHERE value > 20` 必须访问全部三台再合并（这叫 scatter-gather，代价很高）。

**分区的核心权衡**：**分片键（partition key）选得好，查询局部性就好；选得不好，跨片查询就会拖垮系统。** 上面按 `school` 分片，那么「按用户名查」就必须先知道这个人在哪个学校——或者维护一张额外的索引。

### 5.6 分布式哈希表（DHT）

最直接的分区方式：对 key 求哈希，`hash % n` 决定去哪个桶。课件用 13 个桶的例子（第 25 页）：

```
0  {reif:40}
3  {bob:42}
5  {pete:12}
10 {deb:16}
12 {alice:90}
…  {cohen:9}
```

每台服务器负责一个（或几个）桶。前端要存/取一个 key 时：计算 `key.hashCode() % n`，直接联系负责那个桶的服务器。

**问题一：`n` 变了就全乱。** 假设原来 13 台服务器，现在加一台变成 14 台。`hash % 13` 与 `hash % 14` 对**几乎所有** key 都给出不同结果——这意味着**几乎全部数据都要搬家**。对于 PB 级系统，这是一场灾难：搬迁期间网络被打满，服务性能崩塌。

**问题二：前端如何知道谁负责哪个桶？** 三种做法（课件第 28 页）：
- 每个前端各自存一份查找表（简单，但更新时要同步给所有前端）；
- 一个 master 服务器保存查找表（单一真相源，但 master 是瓶颈/单点）；
- 基于路由（routing-based）：请求先发给任意节点，节点转发给正确节点（多一跳，但前端无需状态）。

### 5.7 一致性哈希：让增删节点只影响局部

课件第 27 页给出的解法：

> 把哈希码的取值范围解释成一个**环（ring）**；每个桶负责环上的一段；给每个桶分配一个位于哈希码范围内的 ID；存 item X 时**不**计算 `X.hashCode() % n`，而是把它放进「ID 与 `X.hashCode()` 相同或更大的那个桶」。

形式化：设环上顺时针方向第一个 ID ≥ `h = hash(X)` 的节点为 `succ(h)`，则 X 存放在 `succ(h)` 上。

**为什么这样好？** 加一个节点 `N` 时，只有「原本 `succ` 是 `N` 的后继、且 `h` 落在 `N` 与其前驱之间」的那些 key 需要搬到 `N`。平均而言，只搬 `1/(n+1)` 的数据，而不是几乎全部。删节点同理，只需把它的区间交给后继。

**代价**：每个节点的 ID 是随机的，环上的区间长度不均——某些节点可能负责很大一段，负载不均。工程上的解法是**虚拟节点（virtual nodes）**：每台物理机在环上占很多个位置（如 100–200 个），大数定律让负载趋于均匀。这一点课件没有展开，属于实践知识。

**一致性哈希在 2013 年的意义**：它是 Dynamo、Cassandra、Riak 等系统的基石，也是「能从增量变更中获益」这条设计目标（见 [[15-214-20-Distributed-Systems-Part1]] 第 31 页）最漂亮的落地。

### 5.8 哈希分区的两个遗留问题

课件第 28 页指出，即使有了一致性哈希，仍有两个问题：

**① 前端如何定位服务器？** 见上文三种方案。

**② 相关数据被拆散。** 哈希函数会把「逻辑上相邻」的数据打散到不同服务器。考虑范围查询：

```sql
SELECT * FROM users WHERE lastname STARTSWITH 'G'
```

哈希分区下，`Garcia`、`Green`、`Gupta` 可能分散在三台不同的机器上，这条查询必须**广播到所有分片**再合并——代价与分片数成正比。这是哈希分区最本质的缺陷：它优化了**点查（point query）**，牺牲了**范围查（range query）**。

### 5.9 Master / Tablet 架构：按范围分区 + 集中元数据

课件第 29 页给出的解法是把「按范围分区」和「集中式元数据」结合起来：

```
Master:  {a-c:2, d-g:3, h-j:3, k-z:1}      ← 只存「区间 → 服务器」的映射

Tablet server 1:  k-z: {pete:12, reif:42}
Tablet server 2:  a-c: {alice:90, bob:42, cohen:9}
                  d-g: {deb:16}
                  h-j: {}
Tablet server 3:  （第 29 页图中标注略）
```

- **Master server**：维护「tablet（一段 key 区间）→ 服务器」的分配表。它不存业务数据。
- **Tablet servers**：存实际数据，每个负责若干区间。
- **Front-ends**：缓存 tablet 分配表，直接联系 tablet server，**不经过 master**（master 只在缓存失效时被查询）。

**为什么按范围分区能救范围查询？** 因为 `lastname STARTSWITH 'G'` 只落在 `d-g` 这一个 tablet 上，一次请求就够。

**为什么 master 不是瓶颈？** 因为前端缓存了映射表，绝大多数请求不经过 master。master 只在「tablet 分裂/迁移/故障」时才被访问——这是**读多写极少**的元数据，非常适合缓存。

**Bigtable / HBase 的形态**：这套架构正是 Google Bigtable 与开源 HBase 的结构。tablet 会随着数据增长自动**分裂（split）**，master 负责调度分裂后的新 tablet 到哪台服务器。

### 5.10 组合使用：各层是正交的

课件最后一页（第 30 页）强调：**这些手段大多是正交的（orthogonal），可以叠加**。以 master/tablet 系统为例：

- Master 本身被分区（多个 master 各管一部分 tablet）并被复制（避免单点）；
- Tablet 被复制（通常 3 副本，保证可靠性）；
- 元数据被频繁缓存（前端缓存 tablet 映射）；
- 整个 master/tablet 系统还可以再被复制到另一个数据中心（跨地域容灾）。

这就是真实分布式存储系统的样貌：**没有单一银弹，只有层层叠加的、各自解决一小块问题的机制**。每加一层，就多一份需要协调的状态——这也正是 [[15-214-20-Distributed-Systems-Part1]] 中「健壮性 vs 冗余度」曲线会掉头向下的原因。

## 6. 代码示例

### 6.1 官方课程代码

讲义 `22-distributed-systems-part2.pdf` 是概念性讲义，**全篇没有给出 Java 代码**。它用架构图（第 10、18–20、23、26、29 页）与表格（第 24 页的分片表、第 25 页的哈希桶）来表达设计。

其中第 24 页的分片示例表：

| username | school | value |
|---|---|---|
| cohen | CMU | 9 |
| bob | CMU | 42 |
| alice | Yale | 90 |
| pete | Yale | 12 |
| deb | MIT | 16 |
| reif | MIT | 40 |

第 25 页的哈希桶（13 个桶，`hashCode() % 13`）：

```
桶 0:  {reif:40}
桶 3:  {bob:42}
桶 5:  {pete:12}
桶 10: {deb:16}
桶 12: {alice:90}
…     {cohen:9}
```

第 11 页复述的被动主备复制五步协议与第 12–13 页的问题清单，与 [[15-214-20-Distributed-Systems-Part1]] 相同，属于复习。

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：朴素取模分区 vs 一致性哈希的搬迁量对比。**

```java
import java.util.*;

public class HashMigration {
    /** 朴素方案：key 归属 hash % n。 */
    static int naiveBucket(String key, int n) {
        return Math.floorMod(key.hashCode(), n);
    }

    /** 一致性哈希：环上顺时针第一个 ID >= h 的节点。 */
    static int consistentBucket(String key, TreeMap<Integer, Integer> ring) {
        int h = key.hashCode();
        Map.Entry<Integer, Integer> e = ring.ceilingEntry(h);
        if (e == null) e = ring.firstEntry();   // 绕回环首
        return e.getValue();
    }

    public static void main(String[] args) {
        List<String> keys = new ArrayList<>();
        for (int i = 0; i < 100_000; i++) keys.add("user" + i);

        // 朴素：13 台 → 14 台
        long movedNaive = keys.stream()
                .filter(k -> naiveBucket(k, 13) != naiveBucket(k, 14))
                .count();

        // 一致性哈希：13 个节点 → 14 个节点
        TreeMap<Integer, Integer> ring13 = buildRing(13);
        TreeMap<Integer, Integer> ring14 = buildRing(14);
        long movedConsistent = keys.stream()
                .filter(k -> consistentBucket(k, ring13) != consistentBucket(k, ring14))
                .count();

        System.out.printf("naive moved:      %.1f%%%n", 100.0 * movedNaive / keys.size());
        System.out.printf("consistent moved: %.1f%%%n", 100.0 * movedConsistent / keys.size());
    }

    /** 每台物理机放 150 个虚拟节点，让环上区间趋于均匀。 */
    static TreeMap<Integer, Integer> buildRing(int servers) {
        TreeMap<Integer, Integer> ring = new TreeMap<>();
        for (int s = 0; s < servers; s++) {
            for (int v = 0; v < 150; v++) {
                ring.put(("node" + s + "#" + v).hashCode(), s);
            }
        }
        return ring;
    }
}
```

运行结果的量级：朴素方案约 **92%** 的 key 需要搬迁（理论上 `1 - 1/14 ≈ 92.9%`）；一致性哈希约 **7%**（理论上 `1/14 ≈ 7.1%`）。这个 13 倍的差距就是一致性哈希存在的全部理由。

**示例 B：带过期时间与主动失效的两级缓存。**

```java
import java.util.concurrent.*;

public class TwoLevelCache<K, V> {
    private record Entry<V>(V value, long expireAtMillis) {}

    private final ConcurrentHashMap<K, Entry<V>> cache = new ConcurrentHashMap<>();
    private final long ttlMillis;

    public TwoLevelCache(long ttlMillis) { this.ttlMillis = ttlMillis; }

    public V get(K key, java.util.function.Function<K, V> loader) {
        Entry<V> e = cache.get(key);
        if (e != null && System.currentTimeMillis() < e.expireAtMillis()) {
            return e.value();                       // 命中且未过期
        }
        V fresh = loader.apply(key);                // 回源
        cache.put(key, new Entry<>(fresh, System.currentTimeMillis() + ttlMillis));
        return fresh;
    }

    /** 更新驱动失效：写数据库后主动清掉缓存条目。 */
    public void invalidate(K key) {
        cache.remove(key);
    }

    /** 时间驱动：定期清理过期条目，防止内存无限增长。 */
    public void evictExpired() {
        long now = System.currentTimeMillis();
        cache.entrySet().removeIf(en -> now >= en.getValue().expireAtMillis());
    }
}
```

注意这里**同时用了两种失效**：`invalidate()` 负责精确失效（更新驱动），`expireAtMillis` 负责兜底（时间驱动）——即使某次 `invalidate` 因为进程崩溃而丢失，数据最多脏 `ttlMillis` 毫秒。

**示例 C：LRU 缓存（用 `LinkedHashMap` 的访问顺序模式）。**

```java
import java.util.LinkedHashMap;
import java.util.Map;

public class LruCache<K, V> extends LinkedHashMap<K, V> {
    private final int capacity;

    public LruCache(int capacity) {
        super(16, 0.75f, true);      // true = 按访问顺序排序，最近访问的排到队尾
        this.capacity = capacity;
    }

    @Override
    protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
        return size() > capacity;    // 超容量就淘汰队首（最久未访问）
    }

    public static void main(String[] args) {
        LruCache<Integer, String> c = new LruCache<>(2);
        c.put(1, "a");
        c.put(2, "b");
        c.get(1);                    // 1 变成最近使用
        c.put(3, "c");               // 淘汰 2（最久未使用）
        System.out.println(c.keySet());   // [1, 3]
    }
}
```

`LinkedHashMap` 的第三个构造参数 `accessOrder=true` 会把每次 `get`/`put` 的条目移到链表尾，`removeEldestEntry` 则在插入后回调——两者合起来就是教科书级的 LRU。这也是「用标准库组合出设计模式」的好例子。

**示例 D：按范围路由的 tablet 查找（对应 master/tablet 架构）。**

```java
import java.util.Map;
import java.util.TreeMap;

public class TabletRouter {
    /** tablet 起始 key → tablet server 名。用 TreeMap 支持「找第一个 >= key 的区间」。 */
    private final TreeMap<String, String> tabletToServer = new TreeMap<>();

    public void assign(String rangeStart, String server) {
        tabletToServer.put(rangeStart, server);
    }

    public String serverFor(String key) {
        Map.Entry<String, String> e = tabletToServer.floorEntry(key);   // 所在区间
        return e == null ? null : e.getValue();
    }

    public static void main(String[] args) {
        TabletRouter r = new TabletRouter();
        r.assign("a", "tablet-2");     // a-c
        r.assign("d", "tablet-2");     // d-g
        r.assign("h", "tablet-3");     // h-j
        r.assign("k", "tablet-1");     // k-z

        System.out.println(r.serverFor("green"));   // tablet-2，范围查询天然局部
        System.out.println(r.serverFor("zhao"));    // tablet-1
    }
}
```

`floorEntry` 找到「起始 key ≤ 目标 key 的最大区间」，这正是范围分区路由的核心操作。与哈希分区对比：`serverFor("green")` 与 `serverFor("gupta")` 落在同一台服务器上，所以 `STARTSWITH 'G'` 只需一次请求。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| 复制（replication） | 分区（partitioning） | 复制是「同一份数据放多处」，提升读吞吐与可靠性；分区是「不同数据放不同处」，提升写吞吐与总容量 |
| 时间驱动失效（expiration） | 更新驱动失效（invalidation） | 前者 read-any/write-one，简单但有脏读窗口；后者 read-any/write-all，精确但要广播、可能丢消息 |
| 客户端缓存 | 服务端缓存 | 前者把结果放在离用户最近处，省网络往返；后者把结果放在多台服务器上，避免单台缓存成为瓶颈 |
| LRU（最近最少使用） | LFU（最不经常使用） | LRU 看「多久没用」，适应访问模式变化；LFU 看「用了多少次」，保护长期热点但会压制新热点 |
| Belady 最优 | LRU / LFU / Random | Belady 需要预知未来，**不可实现**，只作为评估基准 |
| 哈希分区（DHT） | 范围分区（master/tablet） | 前者点查 O(1)、范围查要广播；后者范围查局部、但需要维护区间映射与分裂 |
| 普通取模哈希 | 一致性哈希 | 前者增删节点几乎全部 key 搬家；后者只搬相邻区间（约 1/n） |
| master（主控） | tablet server（子表服务器） | master 只存「区间 → 服务器」映射，读多写极少、可缓存；tablet server 存真实数据 |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-214/slides/22-distributed-systems-part2.pdf`
- **总页数**：31 页
- **本节重点页码**：
  - 第 2 页：教务通知（Homework 5b 当晚截止，5c 下周二截止）
  - 第 3–4 页：上次课回顾（更高层抽象：RPC、RMI、MapReduce）
  - 第 6 页：健壮性 vs 冗余度曲线
  - 第 7 页：本讲大纲——复制与分区
  - 第 8 页：成功度量（可用性、5 个 9、可扩展性）
  - 第 9–11 页：被动主备复制复习（架构与五步协议）
  - 第 12–13 页：主备复制的问题（部分失败、性能、可扩展性）
  - 第 14 页：失败行为类型
  - 第 15 页：常见失败假设
  - 第 16 页：分布式系统设计目标
  - 第 18–19 页：客户端缓存与分层客户端缓存
  - 第 20 页：服务端缓存
  - 第 21 页：缓存失效（时间驱动 vs 更新驱动）
  - 第 22 页：缓存替换策略（Belady / LRU / LFU / Random）
  - 第 23 页：按属性分区（CMU / Yale / MIT 三台服务器）
  - 第 24 页：水平分区（sharding）与示例表
  - 第 25 页：基础哈希表的 13 个桶
  - 第 26 页：分布式哈希表（每服务器负责一个桶）
  - 第 27 页：一致性哈希（环 + 顺时针第一个更大 ID）
  - 第 28 页：哈希分区的两个问题（前端定位、范围查询被拆散）
  - 第 29 页：master/tablet 架构
  - 第 30 页：组合使用（master 分区+复制、tablet 复制、元数据缓存）
- **原始链接**：https://www.cs.cmu.edu/~aldrich/214/slides/22-distributed-systems-part2.pdf

## 9. 对应视频

未找到官方公开录像。

## 10. 本节复习

- 两个成功度量：可用性（5 个 9 ≈ 全年停机 5.3 分钟）与可扩展性。
- 缓存的三种位置：客户端、分层客户端、服务端——都只加速读。
- 两种失效策略：时间驱动（read-any/write-one，简单但有脏读窗口）与更新驱动（read-any/write-all，精确但需广播）。实践中两者叠加，后者为主、前者兜底。
- 四种替换策略：Belady 最优（不可实现，仅作基准）、LRU（时间局部性）、LFU（频率热点）、Random（简单、抗惊群）。
- 复制解决读吞吐与可靠性，分区解决写吞吐与容量——两者正交，可叠加。
- 朴素取模分区在扩容时几乎全部 key 要搬家；一致性哈希把搬迁量降到约 1/n。
- 哈希分区牺牲范围查询；master/tablet 用范围分区 + 集中元数据救回范围查询。
- 真实系统是多种手段的叠加：master 分区+复制、tablet 三副本、元数据缓存、跨数据中心复制。

## 11. 自我检查

**Q1.** 「5 个 9 的可用性」意味着一年中系统最多可以不可用多长时间？请写出计算过程。

**Q2.** 某系统用 `hashCode() % n` 分区，n 从 10 扩到 11。请估算需要搬迁的数据比例，并说明为什么一致性哈希能把比例降到约 1/11。

**Q3.** 一个电商系统把商品描述缓存在 CDN 上（时间驱动，TTL = 1 小时），把库存数量缓存在应用服务器本地（更新驱动，写库后广播失效）。请说明这个设计为什么合理，并指出它可能出问题的地方。

**Q4.** 请解释为什么 Belady 最优策略无法在真实系统中实现，但它仍然有价值。

**Q5.** 一个社交应用要支持「按用户名前缀搜索」和「按用户 ID 精确查询」两种访问模式。你会选择哈希分区还是范围分区？请说明理由，并指出你的选择在另一种访问模式下会遇到什么问题。

<details>
<summary>参考答案</summary>

**A1.** 一年按 365 天算 = 365 × 24 × 3600 = 31,536,000 秒。5 个 9 = 99.999% 可用，不可用比例 = 0.001% = 1/100,000。31,536,000 / 100,000 ≈ **315.36 秒 ≈ 5 分 15 秒**。若按每月计，约 26 秒/月。

**A2.** 一个 key 在扩容后仍留在原桶，需要 `h % 10 == h % 11`。对随机 h，这个概率约为 1/11 ≈ 9%，所以需要搬迁的比例约 **1 − 1/11 ≈ 91%**。一致性哈希中，新节点只从环上「抢走」它前驱与自身之间那一段区间，平均长度是环的 1/(n+1)；其余区间的归属完全不变，所以只有落在该区间的 key 需要搬迁，比例约 **1/11 ≈ 9%**。差距来自「取模把整个映射关系全局打乱」vs「环上只切一段」。

**A3.** 合理之处：商品描述**读极多、写极少、允许短暂陈旧**，用 CDN + 长 TTL 能把 99% 的读请求挡在源站之外，成本极低；库存**写频繁且绝不能超卖**，必须用更新驱动失效保证读到最新值，且库存通常还要配合数据库事务/条件更新做最终校验。可能出问题的地方：① 商品改价或下架时，CDN 上最长 1 小时内仍在展示旧内容——对价格敏感的业务不可接受，需要主动 purge；② 库存的失效广播若丢失（网络分区、应用服务器重启），本地缓存会长期持有旧库存，必须再叠加一个较短的 TTL 兜底；③ 多台应用服务器各自缓存，广播是 n 条消息，规模大时本身就是瓶颈。

**A4.** Belady 需要淘汰「未来最长时间不会被访问」的条目，这就要求知道**未来的完整访问序列**，而真实系统的访问序列由用户行为决定，不可预知。它的价值在于：① 提供一个**理论最优上界**，让工程师知道当前策略还有多少改进空间（例如某 trace 上 LRU 命中率 85%、Belady 92%，说明最多还能提升 7 个百分点）；② 作为**评估新策略的基准**，避免用「感觉更快」来判断；③ 帮助理解「为什么 LRU 在某些访问模式下很差」——扫描式访问会冲掉全部热点，而 Belady 不会。

**A5.** 若「按用户 ID 精确查询」是主路径（绝大多数请求），应选**哈希分区**：点查 O(1)，负载天然均匀，扩容靠一致性哈希控制搬迁量。代价是「按用户名前缀搜索」必须**广播到所有分片**再合并（scatter-gather），分片越多越慢。反过来若前缀搜索是主路径，则选**范围分区**（按用户名排序切分），前缀搜索只落在一个 tablet 上；但按 ID 查询就需要额外的「ID → 用户名」索引，否则同样要广播。工程上常见的解法是**双索引**：数据按一个维度分区，另一个维度建全局索引表（索引本身再分区），或者引入 Elasticsearch 这类专为搜索设计的系统。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-20-Distributed-Systems-Part1]]——Java I/O、网络、失败模型、被动主备复制。
- 下一讲：[[15-214-22-Distributed-Systems-Part3]]——MapReduce：在分区+复制的数据上做分布式计算。
- 相关讲次：[[15-214-25-Data-Consistency]]（事务、2PL、2PC、CAP）、[[15-214-19-Concurrency-Part3]]（本地缓存的并发安全）。
- 课程导航：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]、[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]。
- 术语条目：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Cache 缓存、Distributed System 分布式系统、Consistency 一致性）。
- 延伸阅读：Karger et al. "Consistent Hashing and Random Trees"（1997）、DeCandia et al. "Dynamo: Amazon's Highly Available Key-value Store"（SOSP 2007）、Chang et al. "Bigtable"（OSDI 2006）。
