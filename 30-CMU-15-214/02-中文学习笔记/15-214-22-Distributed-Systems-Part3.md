---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L22
topic: Distributed System Design, Part 3 - MapReduce
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 分布式系统
  - MapReduce
  - 函数式编程
  - 容错
---

# 第 22 讲 分布式系统设计（三）：MapReduce

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。

## 1. 本节学习目标

- 能从函数式角度写出 `map` 与 `reduce` 的定义，并分析并行版本的 Work 与 Depth。
- 能解释为什么 `reduce` 的二元函数需要满足**结合律（associativity）**才能安全并行化。
- 能画出 MapReduce 的三角色架构（master / map worker / reduce worker），并说明 shuffle 发生在哪一步。
- 能把「词频统计」「共同好友」「反向链接」三个问题各写成一对 `map` / `reduce` 函数。
- 能说明 MapReduce 如何处理 map worker、reduce worker、master 三者的失败。
- 能解释「把计算搬到数据旁边」这一 data-centric 设计为什么能降低通信成本。

## 2. 前置知识

- [[15-214-21-Distributed-Systems-Part2]]：分区（sharding）、复制、master/tablet 架构——MapReduce 就运行在这样的存储之上。
- [[15-214-19-Concurrency-Part3]]：Work / Depth 分析、分治与 Fork/Join。
- [[15-214-20-Distributed-Systems-Part1]]：失败模型、部分失败、幂等重试。
- 外部概念：高阶函数、`fold`/`reduce`、结合律与交换律。

## 3. 核心概念

- **map（映射）**：`map(f, x[0…n-1])` 把一元函数 `f` 应用到列表的每个元素，得到等长的新列表。
- **reduce（归约）**：`reduce(f, x[0…n-1])` 反复把二元函数 `f` 应用到相邻两个元素，把列表折叠成一个值。
- **Associativity（结合律）**：`f(f(a,b),c) = f(a,f(b,c))`。满足结合律时，归约的**分组方式**不影响结果，因此可以并行。
- **Data-centric architecture（以数据为中心的架构）**：把**函数**发送到数据所在的机器执行，而不是把数据搬到计算所在的机器。
- **Shuffle（洗牌）**：map 阶段产出的中间键值对，按 key 重新分发到 reduce worker 的过程——MapReduce 中最昂贵的阶段。
- **Map worker（映射工作节点）**：对自己本地那份数据执行 map 函数，产出中间键值对，写入**本地磁盘**。
- **Reduce worker（归约工作节点）**：拉取（pull）属于自己负责的 key 的中间数据，按 key 聚合后执行 reduce。
- **Master（主控节点）**：分配任务给 worker、定期 ping 检测失败、协调整个作业。
- **EmitIntermediate（发出中间结果）**：map 函数把 `(key2, value2)` 交给框架的调用，框架负责后续的分区与排序。

## 4. 通俗理解

**map 是什么？** 一条流水线上有 100 个零件，你给每个零件都喷一层漆。喷漆这个动作对每个零件独立进行，互不影响，所以可以叫 100 个人同时喷——这就是 map。**map 天生可并行，因为它没有「元素之间」的依赖。**

**reduce 是什么？** 100 个零件喷完漆，你要把它们装进一个大箱子。你每次只能把两个东西合成一个（"合并"这个动作是二元的），最后合成一个整体。这就是 reduce。**reduce 有依赖，因为每一步都要用上一步的结果**——但如果「合并」满足结合律，你就可以先分头合并成几堆，再把几堆合并，结果一样。

**为什么结合律这么关键？** 加法满足结合律：`(1+2)+(3+4) = 1+(2+(3+4)) = 10`。减法不满足：`(10-3)-2 = 5`，而 `10-(3-2) = 9`。所以「求和」可以并行归约，「依次相减」不能。

**MapReduce 是什么？** 想象一个巨大的图书馆，书分散在 1000 个分馆里。传统做法是把所有书运到一个中心机房再处理——网络会被打爆。MapReduce 的做法是：**把「怎么处理」这份说明书复印 1000 份，寄到每个分馆**，让它们各自在本地处理自己的书（map）；处理完的中间结果按「主题」重新归类（shuffle）；最后每个主题派一个人汇总（reduce）。**函数小、数据大，所以搬函数比搬数据便宜**——这就是 data-centric 的全部精髓。

## 5. 原理与推导

### 5.1 函数式视角的 map

课件第 8 页：

```
map(f, x[0…n-1])
```

把函数 `f` 应用到列表 `x` 的每个元素。Python 示例：

```python
def square(x): return x*x
map(square, [1, 2, 3, 4])   # 返回 [1, 4, 9, 16]
```

课件的评语是「Parallel map implementation is trivial（并行 map 的实现是平凡的）」，然后抛出问题：**What is the work? What is the depth?**

设 `f` 本身的 Work 为 `w`、Depth 为 `d`，列表长度为 `n`：

- **Work**：`W(n) = n·w`——每个元素都要处理一次，没有捷径。
- **Depth**：`D(n) = d`——所有元素**同时**处理，深度等于单个 `f` 的深度，与 `n` 无关。

这是并行算法里最理想的情形：**深度与问题规模无关**。所以只要有 n 个处理器，理论上就能获得 n 倍加速（忽略调度与内存带宽）。

### 5.2 函数式视角的 reduce

课件第 9 页给出定义：

```
reduce(f, x[0…n-1])
```

反复把二元函数 `f` 应用到列表中的一对元素，用结果替换这对元素，直到只剩一个。

课件给的顺序实现（Python）：

```python
def reduce(f, x):
    if len(x) == 1: return x[0]
    return reduce(f, [f(x[0], x[1])] + x[2:])
```

以 `reduce(add, [1,2,3,4])` 为例，课件展示了展开过程：

```
reduce(add, [1,2,3,4])
reduce(add, [3,3,4])      # 1+2=3
reduce(add, [6,4])        # 3+3=6
reduce(add, [10])  ->  10 # 6+4=10
```

注意这个实现是**严格从左往右**折叠的：`f(f(f(1,2),3),4)`。这种折叠方式的 Depth 是 `n-1`——**完全串行**，无法并行。

### 5.3 结合律：并行归约的前提

课件第 10 页的关键一句：

> If the function f is associative, the order f is applied does not affect the result.

并给出三种分组方式的图示：

```
1 + ((2+3) + 4)     1 + (2 + (3+4))     (1+2) + (3+4)
```

三者都等于 10。既然分组方式无关紧要，我们就可以**自由地把列表切成任意几段，各自归约，再归约各段的结果**——这就是并行归约。

**Work 与 Depth 分析**（分治式并行归约，n 个元素）：

- **Work**：`W(n) = n - 1` 次 `f` 调用——与串行版相同，一个不多。这是并行归约相对前缀和的巨大优势：**它不增加工作量**。
- **Depth**：`D(n) = lg n · d`——每一层把规模减半，共 `lg n` 层。

对比串行版 `W = D = (n-1)·d`：并行版把深度从 `n` 降到 `lg n`，而功保持不变。所以在处理器足够多时，加速比可达 `n / lg n`（更精确地说，是 `(n-1)d / (lg n · d)`）。

**但要注意**：结合律只保证「结果相同」，不保证「浮点结果相同」。浮点加法**不满足**结合律（`(0.1+0.2)+0.3 ≠ 0.1+(0.2+0.3)` 在二进制浮点下），所以并行归约求浮点和会得到与串行版**略有差异**的结果，且每次运行可能不同。这是科学计算中一个著名的坑，课件没有展开，但值得知道。

### 5.4 分布式 MapReduce 与函数式的差别

课件第 11 页特别强调：

> The distributed MapReduce idea is similar to (**but not the same as!**) `reduce(f2, map(f1, x))`

差别在哪？**关键在「中间结果的重新分组」**。函数式的 `reduce(f2, map(f1, x))` 里，`map` 产出的列表顺序原样传给 `reduce`；而分布式 MapReduce 里，`map` 产出的中间键值对会先按 **key 分组（group by key）**，每个 key 的所有 value 组成一个列表，再分别归约。这一步就是 **shuffle**。

形式化（课件第 13 页给出）：

```
Map:        (key1, v1)        → (key2, v2)*
Reduce:     (key2, v2*)       → v2*
MapReduce:  (key1, v1)*       → (key2, v2*)*
```

注意类型上的关键区别：`Reduce` 的输入是 `(key2, v2*)`——**一个 key 和它的 value 列表**，而不是两个 value。所以 MapReduce 的 reduce 不是「二元函数折叠」，而是「对一个 key 的所有 value 做聚合」。

**Data-centric 架构的两条主张**（第 11 页）：

1. **把函数 `f1` 直接送到数据所在的机器**，并发执行；
2. **用 reduce 合并结果**，也并发执行。

收益是：**程序员可以专注于数据处理逻辑，而不必操心分布式的种种挑战**（失败、重试、数据分布、网络）。这是框架存在的意义——把「横切关注点（cross-cutting concern）」封装起来。

### 5.5 三角色架构与数据流

课件第 12 页给出 Google 风格的架构：

| 角色 | 职责 |
|---|---|
| **Master** | 给 worker 分配任务；ping worker 检测失败 |
| **Map worker** | 对每个键值对执行 map；发出中间键值对 |
| **Reduce worker** | 按中间 key 排序并聚合（shuffle）；对每个 key 执行 reduce |

课件第 14 页补充了架构细节，这是理解性能的关键：

1. **通常与分布式存储系统集成**：map worker 在**自己那份数据**上执行函数（数据本地性，data locality）。
2. **map 输出写到 worker 的本地磁盘**（不是分布式存储）——因为中间结果是一次性的，写分布式存储太贵。
3. **shuffle**：reduce worker 主动**拉取（pull）** map worker 本地磁盘上的中间数据。
4. **reduce 输出写回分布式存储系统**——因为这是最终结果，需要持久化与多副本。

数据流可以画成：

```
分布式存储（输入）
      ↓ 本地读
  map worker  ──中间结果──→  本地磁盘
      ↑                        ↓ pull（shuffle）
      └──── reduce worker ←────┘
                ↓
        分布式存储（输出）
```

**为什么用 pull 而不是 push？** 因为 reduce worker 知道自己的 key 范围，可以精确地只拉取自己需要的分区；而 push 需要 map worker 知道所有 reduce worker 的分配，且 map 完成时间不一，push 会造成大量无效传输。pull 让 reduce 端控制节奏，也天然支持「map 完成后立刻被消费」。

### 5.6 三个经典例子

**① 词频统计（Word Count）**——MapReduce 的 "Hello World"（第 13 页）：

```
f1(String key1, String value):          // key1 = 文档名, value = 文档内容
  for each word w in value:
    EmitIntermediate(w, 1);

f2(String key2, Iterator values):       // key2 = 单词, values = 一串 1
  int result = 0;
  for each v in values:
    result += v;
  Emit(key2, result);
```

类型推导：

```
MapReduce: (docName, docText)*  →  (word, wordCount)*
```

**② 共同好友数**（第 17–18 页）：

问题：对社交网络中的每个人，输出他有多少对互为好友的朋友。

```
f1(String key1, String value):          // key1 = 人, value = 他的好友列表
  for each pair of friends in value:
    EmitIntermediate(pair, 1);

f2(String key2, Iterator values):       // key2 = 一对人, values = 一串 1
  int result = 0;
  for each v in values:
    result += v;
  Emit(key2, result);
```

类型：

```
MapReduce: (person, friends)*  →  (pair of people, count of mutual friends)*
```

**关键洞察**：`map` 的输入粒度是「一个人」，输出粒度是「一对人」。**map 可以改变 key 的粒度**——这正是 MapReduce 表达力的来源。某个共同好友 `X` 在 `A` 的好友列表里出现一次、在 `B` 的好友列表里出现一次，于是 `(A,B)` 这个 key 收到两个 1，reduce 求和得 2——但注意，如果 `A` 和 `B` 各有多个共同好友，`(A,B)` 会收到更多 1。课件的问题陈述是「number of mutual friends」，所以这个计数实际上是「共同好友的个数」，不是「是否有共同好友」。

**③ 反向链接（Inverted Index）**（第 19 页）：

问题：对网页上的每个页面，列出所有指向它的页面。

```
MapReduce: (docName, docText)*  →  (docName, list of incoming links)*
```

课件的这一页把 `f1` 与 `f2` 留白，作为课堂练习。思路是：

```
f1(String key1, String value):          // key1 = 当前文档名, value = 文档内容
  for each link target t in value:
    EmitIntermediate(t, key1);          // 反转：key 变成「被链接的页面」

f2(String key2, Iterator values):       // key2 = 被链接的页面, values = 指向它的页面名
  List<String> sources = new ArrayList<>();
  for each v in values:
    sources.add(v);
  Emit(key2, sources);
```

这里 reduce 不再求和，而是**收集成列表**——说明 reduce 的输出不一定是数值。

### 5.7 容错：三种角色的失败处理

课件第 15 页给出：

**① Map worker 失败**：用存储系统中的**数据副本**重新执行 map。这是可行的，因为 map 是**纯函数**——输入相同，输出必然相同，且没有副作用。所以重跑一遍完全安全。

**② Reduce worker 失败**：新的 reduce worker 可以从 map worker 的**本地磁盘**重新拉取中间数据，重新归约。同样可行，因为中间数据还在（除非那台 map worker 也挂了）。

**③ Master 失败**：课件给出三个选项——用新 master 重启系统、复制 master、或者其他方案（省略号）。这是三者中最难的，因为 master 保存着「任务分配」这份全局状态。现代实现（如 Hadoop）通常让 master 也做检查点（checkpoint）或依赖外部协调服务（ZooKeeper）。

**为什么 MapReduce 的容错如此简单？** 因为它对用户函数有强约束：

- map 与 reduce 必须是**确定性（deterministic）**且**无副作用（side-effect free）**的；
- 输入来自**不可变的分布式存储**（写一次、读多次）；
- 中间结果可以随时重算。

这三条合起来意味着「重试」永远安全。这是**函数式编程思想在分布式系统里的最大红利**：无副作用 ⇒ 可重放 ⇒ 容错只需重跑。

对比 [[15-214-20-Distributed-Systems-Part1]] 中的主备复制：那里每次更新都要广播并等待所有 ack，容错逻辑复杂到列出七类问题。MapReduce 因为把计算限制成纯函数，容错变得几乎免费。

### 5.8 MapReduce 的美与局限

课件第 16 页的「The beauty of MapReduce」：

- **通信成本低（通常）**：因为计算被搬到数据旁边，只有中间结果需要跨网络传输。唯一的昂贵环节是 **shuffle**（map 与 reduce 之间）。
- **MapReduce 可以迭代**：输入是分布式存储里的键值对，输出也是分布式存储里的键值对——所以一个作业的输出可以直接作为下一个作业的输入，串成流水线。

**课件没有明说、但值得补充的局限**：

1. **不适合低延迟场景**：一个作业通常要几十秒到几分钟，因为有调度、shuffle、落盘。
2. **不适合迭代式算法**：机器学习里的梯度下降要迭代几百轮，每轮都落盘再读盘，代价极高。这正是后来 Spark 用内存 RDD 取代 MapReduce 的动机。
3. **不适合有依赖的图计算**：图算法（PageRank、最短路）的迭代依赖复杂，MapReduce 表达起来很别扭。
4. **shuffle 是瓶颈**：所有中间数据都要按 key 重分布并排序，数据倾斜（某个 key 有海量 value）会让单个 reduce worker 成为长尾。

## 6. 代码示例

### 6.1 官方课程代码

讲义 `23-distributed-systems-part3.pdf` 是伪代码级讲义，使用类 Java 的伪代码而非可编译的 Java。

**第 8 页：map 的 Python 示例**

```python
def square(x): return x*x
map(square, [1, 2, 3, 4])   # -> [1, 4, 9, 16]
```

**第 9 页：reduce 的顺序 Python 实现**

```python
def reduce(f, x):
    if len(x) == 1: return x[0]
    return reduce(f, [f(x[0],x[1])] + x[2:])

def add(x,y): return x+y
reduce(add, [1,2,3,4])      # -> 10
```

**第 13 页：词频统计的 map / reduce**

```
f1(String key1, String value):
  for each word w in value:
    EmitIntermediate(w, 1);

f2(String key2, Iterator values):
  int result = 0;
  for each v in values:
    result += v;
  Emit(key2, result);

Map:        (key1, v1)   -> (key2, v2)*
Reduce:     (key2, v2*)  -> v2*
MapReduce:  (key1, v1)*  -> (key2, v2*)*
MapReduce:  (docName, docText)* -> (word, wordCount)*
```

**第 18 页：共同好友的 map / reduce**

```
f1(String key1, String value):
  for each pair of friends in value:
    EmitIntermediate(pair, 1);

f2(String key2, Iterator values):
  int result = 0;
  for each v in values:
    result += v;
  Emit(key2, result);

MapReduce: (person, friends)* -> (pair of people, count of mutual friends)*
```

**第 19 页：反向链接（f1/f2 留白，课堂练习）**

```
MapReduce: (docName, docText)* -> (docName, list of incoming links)*
```

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：用 Java 8 Stream 模拟单机 map / reduce（体会「函数被送过去」的直觉）。**

```java
import java.util.*;
import java.util.stream.*;

public class LocalMapReduce {
    public static void main(String[] args) {
        List<String> docs = List.of(
                "the quick brown fox",
                "the lazy dog sleeps",
                "the fox and the dog");

        // Map 阶段：每个文档 -> 一串 (word, 1)
        List<Map.Entry<String, Integer>> intermediate = docs.stream()
                .flatMap(doc -> Arrays.stream(doc.split(" "))
                        .map(w -> Map.entry(w, 1)))     // EmitIntermediate(w, 1)
                .collect(Collectors.toList());

        // Shuffle 阶段：按 key 分组（这就是分布式里的 shuffle）
        Map<String, List<Integer>> grouped = intermediate.stream()
                .collect(Collectors.groupingBy(Map.Entry::getKey,
                        Collectors.mapping(Map.Entry::getValue, Collectors.toList())));

        // Reduce 阶段：每个 key 的 value 列表求和
        Map<String, Integer> result = grouped.entrySet().stream()
                .collect(Collectors.toMap(Map.Entry::getKey,
                        e -> e.getValue().stream().mapToInt(Integer::intValue).sum()));

        result.forEach((k, v) -> System.out.println(k + " = " + v));
        // the = 4, quick = 1, brown = 1, fox = 2, lazy = 1, dog = 2, sleeps = 1, and = 1
    }
}
```

三段结构（flatMap → groupingBy → 求和）精确对应 map → shuffle → reduce。分布式版本只是把这三段分散到不同机器，并加上失败重试。

**示例 B：共同好友（用集合运算实现，展示 map 可以改变 key 粒度）。**

```java
import java.util.*;
import java.util.stream.*;

public class MutualFriends {
    public static void main(String[] args) {
        // 输入：(person, friends)  —— 即 key1, value1
        Map<String, List<String>> social = new LinkedHashMap<>();
        social.put("alice", List.of("bob", "carol", "dave"));
        social.put("bob",   List.of("alice", "carol", "eve"));
        social.put("carol", List.of("alice", "bob"));
        social.put("dave",  List.of("alice"));
        social.put("eve",   List.of("bob"));

        // Map：对每个人的好友列表，枚举所有无序对，发出 ((x,y), 1)
        List<Map.Entry<String, Integer>> intermediate = new ArrayList<>();
        for (var e : social.entrySet()) {
            List<String> fs = e.getValue();
            for (int i = 0; i < fs.size(); i++) {
                for (int j = i + 1; j < fs.size(); j++) {
                    String a = fs.get(i), b = fs.get(j);
                    String pair = a.compareTo(b) < 0 ? a + "|" + b : b + "|" + a;
                    intermediate.add(Map.entry(pair, 1));   // EmitIntermediate(pair, 1)
                }
            }
        }

        // Shuffle + Reduce：同一对的 1 求和
        Map<String, Integer> counts = intermediate.stream()
                .collect(Collectors.groupingBy(Map.Entry::getKey,
                        Collectors.summingInt(Map.Entry::getValue)));

        counts.forEach((pair, c) -> System.out.println(pair + " -> " + c));
        // alice|bob -> 2 (alice 的好友对 + bob 的好友对)
        // alice|carol -> 2, alice|dave -> 1, bob|carol -> 2, bob|eve -> 1
    }
}
```

注意 `alice|bob` 的计数是 2 而不是 1：`alice` 的好友列表里有 `bob`，`bob` 的好友列表里有 `alice`，两边各发一个 1。这暴露了课件例子的一个语义细节——如果要的是「共同好友数」，应该对「第三人」计数而不是对「好友对」计数。**这正说明：设计 MapReduce 作业时，map 发什么 key 决定了最终语义**，是最容易出错的地方。

**示例 C：反向链接（inverted index）的 map / reduce。** 上面第 5.6 节已给出伪代码，这里是可运行的 Java 版：

```java
import java.util.*;
import java.util.stream.*;

public class InvertedIndex {
    record Doc(String name, String text) {}

    public static void main(String[] args) {
        List<Doc> docs = List.of(
                new Doc("a.html", "see b.html and c.html"),
                new Doc("b.html", "see c.html"),
                new Doc("c.html", "nothing here"));

        // Map：(target, source)
        List<Map.Entry<String, String>> intermediate = docs.stream()
                .flatMap(d -> Arrays.stream(d.text().split(" "))
                        .filter(t -> t.endsWith(".html"))
                        .map(t -> Map.entry(t, d.name())))
                .collect(Collectors.toList());

        // Shuffle + Reduce：把 source 收集成列表
        Map<String, List<String>> index = intermediate.stream()
                .collect(Collectors.groupingBy(Map.Entry::getKey,
                        Collectors.mapping(Map.Entry::getValue, Collectors.toList())));

        index.forEach((target, sources) ->
                System.out.println(target + " <- " + sources));
        // b.html <- [a.html]
        // c.html <- [a.html, b.html]
    }
}
```

这里的 reduce 是「收集」而非「求和」——再次说明 reduce 的输出类型由业务决定，不限于数值。

**示例 D：结合律反例。**

```java
public class Associativity {
    public static void main(String[] args) {
        // 加法满足结合律：并行归约安全
        System.out.println((1 + 2) + 3 == 1 + (2 + 3));   // true

        // 减法不满足：不能并行归约
        System.out.println((10 - 3) - 2);                 // 5
        System.out.println(10 - (3 - 2));                 // 9

        // 浮点加法在二进制下也不严格满足结合律
        double a = 0.1, b = 0.2, c = 0.3;
        System.out.println((a + b) + c);                  // 0.6000000000000001
        System.out.println(a + (b + c));                  // 0.6
    }
}
```

最后两行输出不同，说明**即使数学上满足结合律的运算，在浮点表示下也可能不满足**。所以并行浮点归约的结果可能与串行版有微小差异，且每次运行可能不同——这是分布式数值计算必须接受的事实。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| `map` | `reduce` | map 逐元素独立变换，Work = n·w、Depth = d（与 n 无关）；reduce 折叠成单值，Depth = lg n（并行）或 n（串行） |
| 函数式 `reduce(f2, map(f1, x))` | 分布式 MapReduce | 后者在 map 与 reduce 之间多了 **shuffle**（按 key 分组），且 reduce 的输入是 `(key, value 列表)` 而非两个值 |
| 结合律（associativity） | 交换律（commutativity） | 结合律允许**改变分组**，是并行归约的前提；交换律允许**改变顺序**，是乱序到达仍正确的前提。MapReduce 通常两者都需要 |
| map worker 输出位置 | reduce 输出位置 | 前者写**本地磁盘**（中间结果，一次性）；后者写**分布式存储**（最终结果，需持久化） |
| push（推） | pull（拉） | MapReduce 的 shuffle 用 pull：reduce worker 主动拉取自己需要的分区，节奏由消费端控制 |
| map worker 失败 | master 失败 | 前者简单——用数据副本重跑（map 是纯函数）；后者困难——需要重启、复制 master 或依赖外部协调服务 |
| 数据本地性（data locality） | 数据搬移 | MapReduce 把**函数**搬到数据旁；传统做法把**数据**搬到计算处。前者通信量小得多 |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-214/slides/23-distributed-systems-part3.pdf`
- **总页数**：20 页
- **本节重点页码**：
  - 第 2 页：教务通知（Homework 5c 插件作业）
  - 第 3–4 页：上次课回顾（失败模型、设计原则、复制与分区、一致性哈希）
  - 第 5 页：master/tablet 架构复习
  - 第 6 页：本讲主题——MapReduce
  - 第 7 页：目标（在复制、分区的数据上做健壮可扩展的分布式计算）
  - 第 8 页：函数式 map 与 Work/Depth 提问
  - 第 9 页：函数式 reduce 与顺序实现
  - 第 10 页：结合律与并行 reduce 的 Work/Depth
  - 第 11 页：分布式 MapReduce 与 data-centric 架构
  - 第 12 页：三角色架构（master / map worker / reduce worker）与 shuffle
  - 第 13 页：词频统计例子与类型签名
  - 第 14 页：架构细节（本地磁盘、pull、输出回存储）
  - 第 15 页：三种失败的处理
  - 第 16 页：MapReduce 的优点（低通信成本、可迭代）
  - 第 17–18 页：共同好友例子
  - 第 19 页：反向链接例子（留白练习）
- **原始链接**：https://www.cs.cmu.edu/~aldrich/214/slides/23-distributed-systems-part3.pdf

## 9. 对应视频

未找到官方公开录像。

## 10. 本节复习

- `map`：逐元素独立变换，Work = n·w，Depth = d（与 n 无关），并行是平凡的。
- `reduce`：折叠成单值；顺序折叠 Depth = n；若 `f` 满足结合律，分治归约 Work = n−1、Depth = lg n，**不增加工作量**。
- 分布式 MapReduce ≠ `reduce(f2, map(f1, x))`，差别在于 shuffle（按 key 分组）。
- 类型签名：`Map: (k1,v1) → (k2,v2)*`；`Reduce: (k2,v2*) → v2*`；`MapReduce: (k1,v1)* → (k2,v2*)*`。
- 三角色：master 分配与检测、map worker 本地计算并写本地磁盘、reduce worker 拉取并聚合。
- 数据流：分布式存储 → map → 本地磁盘 → shuffle(pull) → reduce → 分布式存储。
- 容错简单的原因：map/reduce 是纯函数、输入不可变、中间结果可重算——「无副作用 ⇒ 可重放」。
- 优点：通信成本低、可迭代串联。局限：高延迟、不适合迭代算法与图计算、shuffle 易成瓶颈。

## 11. 自我检查

**Q1.** 对长度 n = 1,000,000 的列表做 map，单个 `f` 耗时 1 微秒。若用 1000 个处理器，理想情况需要多久？Work 与 Depth 各是多少？

**Q2.** 请说明为什么 `reduce` 需要结合律才能并行，并举一个满足结合律但不满足交换律的运算作为例子，说明它能否用于 MapReduce。

**Q3.** 词频统计的 map 发出的是 `(word, 1)`。如果改成发出 `(word, 该词在本行出现的次数)`，reduce 需要改吗？这样改有什么好处？

**Q4.** 为什么 map worker 的输出写在**本地磁盘**而不是分布式存储？如果改成写分布式存储，会带来什么问题？

**Q5.** 某 MapReduce 作业的 shuffle 阶段极慢，观察到 99% 的中间数据集中在 3 个 key 上。请诊断原因并给出至少两种缓解方案。

<details>
<summary>参考答案</summary>

**A1.** Work = n·w = 1,000,000 × 1 μs = 1 秒（这是总计算量）。Depth = d = 1 μs（所有元素同时处理）。用 1000 个处理器时，每个处理器处理 1000 个元素，理想耗时 = 1000 × 1 μs = **1 毫秒**（前提是调度与数据分发零开销，实际会有网络与磁盘开销）。

**A2.** 并行归约要把列表切成若干段，各段独立折叠，再把各段结果折叠——这实际上**改变了括号的分组方式**。只有当 `f(f(a,b),c) = f(a,f(b,c))` 时，改变分组才不改变结果，所以结合律是前提。反例：减法 `(10-3)-2 = 5` 而 `10-(3-2) = 9`，不能并行。满足结合律但不满足交换律的例子：**字符串拼接** `concat("a","b") = "ab"` 而 `concat("b","a") = "ba"`——它满足结合律 `(ab)c = a(bc) = "abc"`。它可以用于 MapReduce 的 reduce 阶段（只要同一 key 内的 value 顺序确定），但**不能用于需要乱序合并的场景**（如多个 map 的输出以任意顺序到达时，拼接结果会不同）。所以实际使用中通常还要求交换律，或者框架保证同一 key 内的 value 有序。

**A3.** reduce **不需要改**——它只是对 value 列表求和，value 是 1 还是 5 都无所谓。好处是**大幅减少中间数据量**：一行有 100 个 "the"，原方案发出 100 条 `(the,1)`，新方案只发 1 条 `(the,100)`。shuffle 的数据量直接降两个数量级，网络与排序开销大幅下降。这是 MapReduce 优化的经典手段，Hadoop 称之为 **combiner（合并器）**——在 map 端本地先做一次「迷你 reduce」，前提是 reduce 操作满足结合律与交换律。

**A4.** 因为中间结果**是一次性的**：它只被本次作业的 reduce worker 消费一次，作业结束后就没用了。写分布式存储意味着三副本、跨网络传输、磁盘持久化——成本是写本地磁盘的数倍，而收益为零。另外，本地写还带来**数据本地性**：reduce worker 可以从同一台或同机架的 map worker 拉取，走的是高速内网。改成写分布式存储的问题：① shuffle 数据量可能远大于输入（词频统计的中间结果通常比输入大一个数量级），写三副本会打爆网络与存储；② 增加了对存储系统的写压力，与真正的最终输出争抢带宽；③ 作业完成后还要清理这些临时数据，增加运维复杂度。

**A5.** 这是典型的**数据倾斜（data skew）**：少数 key 聚集了海量 value，导致负责这些 key 的 reduce worker 成为长尾，其他 worker 早已完成却只能空等。可能原因：① 数据本身长尾（如词频统计里的停用词 "the"、"a"）；② key 设计不当（如用「国家」做 key，小国数据极少、大国极多）；③ 空值或默认值被当成正常 key。缓解方案：① **加盐（salting）**——给热点 key 加随机后缀拆成多个 key（如 `the#0`…`the#9`），并行 reduce 后再做一次小规模归约；② **combiner 预聚合**——在 map 端先本地求和，把 `(the,1)` 压缩成 `(the,10000)`，直接减少传输量；③ **自定义分区函数**——让热点 key 分散到多个 reduce worker；④ 把热点 key 单独抽出来用另一种方式处理（如广播到所有节点做 map-side join）。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-21-Distributed-Systems-Part2]]——缓存、失效策略、分区与一致性哈希。
- 下一讲：[[15-214-23-Static-Analysis]]——从「运行时分布式」转向「编译期静态分析」。
- 相关讲次：[[15-214-25-Data-Consistency]]（事务、2PC、CAP）、[[15-214-19-Concurrency-Part3]]（Work/Depth 与并行归约）。
- 课程导航：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]、[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]。
- 术语条目：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Distributed System 分布式系统、Concurrency 并发）。
- 延伸阅读：Dean & Ghemawat "MapReduce: Simplified Data Processing on Large Clusters"（OSDI 2004）、Zaharia et al. "Resilient Distributed Datasets"（Spark, NSDI 2012）。
