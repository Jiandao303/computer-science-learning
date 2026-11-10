---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L19
topic: Concurrency 3 - Immutability, Fork/Join, and Parallel Prefix Sums
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 并发
  - 不可变性
  - Fork-Join
  - 前缀和
---

# 第 19 讲 并发（三）：不可变性与并行算法（Concurrency 3）

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。

## 1. 本节学习目标

- 能说明「不可变对象天然线程安全」的理由，并写出一个真正不可变的 Java 类。
- 能解释并行算法中的 Winding / Unwinding 两阶段，并手工推演一遍 8 个元素的前缀和。
- 能计算迭代版与递归版前缀和的 Work 与 Depth，并判断理论上能获得多少加速。
- 能用 `ExecutorService` + `Callable` / `Future` 提交任务并取回结果。
- 能用 `ForkJoinPool` 与 `RecursiveAction` 写一个分治并行任务。
- 能解释为什么「并行版本做了更多加法、内存访问更不连续」会导致实际加速远低于理论值。

## 2. 前置知识

- [[15-214-17-Concurrency-Part1]]：Work / Depth / Breadth、Amdahl 定律、线程的创建与 `join`。
- [[15-214-18-Concurrency-Part2]]：`synchronized`、`volatile`、`java.util.concurrent` 概览。
- [[15-214-06-Mutability-and-Java-Potpourri]]：可变与不可变对象、`final` 字段的语义。
- 外部概念：递归与分治、二叉树的高度、算法的渐进复杂度。

## 3. 核心概念

- **Immutability（不可变性）**：对象创建后其可观察状态永不改变。所有字段 `private final`，构造完成后不再修改，且不泄露内部可变引用。
- **Thread Confinement（线程封闭）**：把数据限制在单条线程内（局部变量、`ThreadLocal`），其他线程根本访问不到，因此无需同步。
- **Callable\<V\>（可调用任务）**：`V call() throws Exception`——有返回值的任务，可抛受检异常。
- **Future\<V\>（未来值）**：代表一个尚未完成的计算结果。`get()` 会阻塞直到结果就绪。
- **ExecutorService（执行器服务）**：管理线程池并接受任务的对象；把「任务提交」与「线程生命周期管理」解耦。
- **Fork/Join（分叉/汇合）**：分治式并行框架。大任务 `fork` 成小任务并行执行，再 `join` 合并结果；工作窃取（work stealing）让空闲线程去偷别的线程队列里的任务。
- **RecursiveAction / RecursiveTask\<V\>**：Fork/Join 任务的两个基类，前者无返回值，后者返回 `V`。
- **Prefix Sums / Inclusive Scan（前缀和/包含式扫描）**：把 `[x0, x1, …, xn-1]` 变换为 `[x0, x0+x1, …, x0+…+xn-1]`。
- **Winding（上行）/ Unwinding（下行）**：前缀和并行算法的两个阶段——先自底向上建立部分和，再自顶向下把「前缀」传播回去。

## 4. 通俗理解

**不可变性为什么能治百病？** 想象一份打印好并塑封的文件。任何人都可以随便看，不需要排队、不需要加锁，因为没有人能改它。要「修改」只有一种方式：重新打印一份新文件，然后把公告栏上的钉子拔下来换上去——这一次替换是原子的。这就是不可变对象的全部秘密：**读永不冲突，写只有一次（换引用）**。

**前缀和是什么？** 你有一串数字 `[13, 9, -4, 19, -6, 2, 6, 3]`，前缀和就是「到目前为止累计多少」：`[13, 22, 18, 37, 31, 33, 39, 42]`。最后一个数 42 就是全部之和。

**为什么这件事能并行？** 顺序做法要做 7 次加法、依赖链长度 7，串行无法加速。并行做法把它想成一棵二叉树：先在每一层把「相邻两块的和」加起来（上行），再从根往下把「左边的累计量」发回去（下行）。树高只有 log₂8 = 3 层，所以 Depth 从 7 降到 3。

**一个具体数字：** 8 个元素时串行 7 次加法、深度 7；并行版本约 2n = 16 次有效加法、深度 2·lg 8 = 6。并行**做了两倍多的活**，只把深度减了一点——这就是为什么 8 核跑这个算法往往快不过 2 倍。

## 5. 原理与推导

### 5.1 不可变性：最强的线程安全策略

课件把线程安全的策略按「代价从低到高」排列，不可变性排在最前：

1. **不可变（immutable）**：`final` 的基本类型字段永远不可变；不可变对象初始化完成后免疫一切竞态。无需锁、无需 `volatile`，可以自由共享。
2. **线程封闭（confinement）**：局部变量、每次调用新建的对象、GUI 工具包（Java AWT/Swing 的单线程模型）、线程私有状态。
3. **同步（synchronization）**：`synchronized`、`java.util.concurrent`。

为什么不可变对象天然安全？因为数据竞争的定义要求「至少一个写」。若对象不可变，所有访问都是读，条件永不成立。而且没有写就没有「中间状态」，也就不存在可见性问题。

**写出真正不可变类的五条要求**（课件未逐条列出，这里按通行做法补全）：

1. 所有字段 `private final`；
2. 类声明为 `final`（或所有构造器私有 + 工厂方法），防止子类破坏；
3. 构造器中不泄露 `this`（不要让 `this` 逃逸到其它线程）；
4. 若字段是可变对象的引用，必须做**防御性拷贝（defensive copy）**，进出都拷；
5. 不提供任何修改状态的方法（`getter` 返回不可变视图或拷贝）。

第 4 条最容易被忽略：`final List<String> items` 只保证「引用不变」，`items.add(...)` 照样能改内容。

### 5.2 语言级并发：Java 的 `for` 与 Nesl 的集合推导

课件对比了不同语言表达并行的方式。

Java 的普通 `for` 循环是**顺序**语义，循环体逐次执行：

```java
long sum = 0;
for (int i = 0; i < a.length; i++) sum += a[i];
```

Python 同理，`for` 也保证顺序。要让它们并行，必须显式使用线程、`ForkJoin` 或流式 API。

而专门为并行设计的语言把并行写进了语法。Nesl 的并行快排：

```
function quicksort(a) =
  if (#a < 2) then a
  else
   let pivot   = a[#a/2];
       lesser  = {e in a | e < pivot};
       equal   = {e in a | e == pivot};
       greater = {e in a | e > pivot};
       result  = {quicksort(v): v in [lesser, greater]};
   in result[0] ++ equal ++ result[1];
```

`{ ... }` 内的元素级操作**默认并行**：过滤（`{e in a | …}`）与映射（`{f(v): v in …}`）都会自动分配到所有处理器上。程序员不需要写一行线程代码。

课件的观点是：**语言抽象决定了你能多容易地表达并行**。Java 需要库（`java.util.concurrent`），Nesl 需要语法，各有取舍。

### 5.3 前缀和：Winding 与 Unwinding 全推演

设 `x = [13, 9, -4, 19, -6, 2, 6, 3]`，目标是 `[13, 22, 18, 37, 31, 33, 39, 42]`。

**阶段一 Winding（上行）**：从 `gap = 1` 开始，每次把间隔为 `gap` 的一对数相加，结果写到右边那个位置，`gap` 翻倍。

- gap = 1：`x[1] += x[0]`、`x[3] += x[2]`、`x[5] += x[4]`、`x[7] += x[6]`
  得 `[13, 22, -4, 15, -6, -4, 6, 9]`
- gap = 2：`x[3] += x[1]`、`x[7] += x[5]`
  得 `[13, 22, -4, 37, -6, -4, 6, 5]`
- gap = 4：`x[7] += x[3]`
  得 `[13, 22, -4, 37, -6, -4, 6, 42]`

此时每个「块尾」元素存的是该块的**块内总和**（`x[7]` = 全数组之和 42），但中间元素还是局部值。

**阶段二 Unwinding（下行）**：`gap` 从 `n/2` 开始每次减半，把左侧块的前缀加到右侧块上。

- gap = 4：`x[i] += x[i-gap]`，i 从 3 开始步长 8，只有一个 i = 3：`x[3] += x[-1]`——下标越界，跳过（伪代码里写作 `if (i-gap >= 0)`）
  保持不变 `[13, 22, -4, 37, -6, -4, 6, 42]`
- gap = 2：i = 1, 5。`x[1] += x[-1]` 跳过；`x[5] += x[3]` → `-4 + 37 = 33`
  得 `[13, 22, -4, 37, -6, 33, 6, 42]`
- gap = 1：i = 0, 2, 4, 6。`x[0] += x[-1]` 跳过；`x[2] += x[1]` → `-4+22 = 18`；`x[4] += x[3]` → `-6+37 = 31`；`x[6] += x[5]` → `6+33 = 39`
  得 `[13, 22, 18, 37, 31, 33, 39, 42]`

与目标完全一致。

**为什么正确？** 归纳地看：上行结束后，位置 `i` 处存的是所在「gap 块」的块内和；下行时把左邻块的前缀和加进来，逐层把「全局前缀」传播到每个位置。两阶段合起来，每个元素都收到了它左边所有元素的和。

### 5.4 伪代码与 Work / Depth 分析

课件给出的伪代码：

```
prefix_sums(x):
  for d in 0 to (lg n)-1:                       // 上行
    parallelfor i in 2^d-1 to n-1, by 2^(d+1):
      x[i+2^d] = x[i] + x[i+2^d]
  for d in (lg n)-1 to 0:                       // 下行
    parallelfor i in 2^d-1 to n-1-2^d, by 2^(d+1):
      if (i-2^d >= 0):
        x[i] = x[i] + x[i-2^d]
```

**Work**：每一层 `d` 大约做 `n / 2^(d+1)` 次加法。上行 `lg n` 层加起来约 `n/2 + n/4 + … + 1 ≈ n`；下行同理约 `n`。总计 `W(n) = O(n)`。

**Depth**：两层循环各 `lg n` 次迭代，每次迭代内部的并行操作深度为 1（可同时完成）。因此 `D(n) = O(lg n)`。

对比串行版本：`W = n-1`，`D = n-1`。

于是理想加速比（n 远大于核心数 P 时）约为 `W_serial / W_parallel × P`——但注意**并行版本做功更多**（约 2n 而非 n），所以在核心数不多时，depth 的收益被 work 的膨胀吃掉。

### 5.5 递归版：更自然的表达

递归版本把「块」显式表达出来：

```
computePrefixSumsRecursive(a, gap):
    if (2*gap - 1 >= a.length) return;      // 终止条件：块已经比数组大
    parallelfor i in gap-1 .. a.length-1 by 2*gap:
        a[i+gap] = a[i] + a[i+gap]          // 上行
    computePrefixSumsRecursive(a, 2*gap)    // 递归处理更大的块
    parallelfor i in gap-1 .. a.length-1 by 2*gap:
        a[i] = a[i] + ((i-gap >= 0) ? a[i-gap] : 0)   // 下行
```

关键点：**递归调用夹在两个 `parallelfor` 之间**——这就是标准的 Fork/Join 形态（fork–递归–join）。`gap` 每层翻倍，递归深度 `lg n`。

### 5.6 如何真正把 `parallelfor` 变成线程

课件给出逐层递进的三条路线：

**① 手动切分**：把一个 `parfor` 的索引区间切成 `k` 段，每段交给一条 `Thread`：

```java
for (int i = left + gap - 1; i + gap < right; i += 2 * gap) { ... }
```

**② `ExecutorService` + `Callable` / `Future`**：把每段包装成有返回值的任务提交，再统一 `get()` 收集。这比手动 `Thread` 更好，因为线程由池复用，避免频繁创建销毁。

**③ Fork/Join**：递归地把任务二分，用 `invokeAll` 同时执行左右两半，`RecursiveAction`（无返回值）最适合原地修改数组的场景。

Fork/Join 的效率来自**工作窃取（work stealing）**：每个工作线程有自己的双端队列，任务被 `fork` 后压入自己的队列头；空闲线程从别人队列的**尾**部偷任务。这样切分产生的子任务自然地在多核间负载均衡，而且不必为每次 `fork` 付出创建线程的代价。

### 5.7 常数很重要（Constants Matter）

课件的性能对比给出了一个反直觉的结论：**并行版本不一定更快**。原因是三个「常数级」的成本：

1. **多做功**：串行 `n-1` 次加法，并行约 `2n` 次有效加法，另外循环索引本身也要做加法；
2. **内存访问模式**：串行是顺序扫描，对缓存与预取器（prefetcher）友好；并行版本跳跃式访问（步长 `2*gap`），缓存命中率下降；
3. **调度与同步开销**：`fork`/`join`、任务队列、线程唤醒都要花时间。

课件的结论就是那句 **"Constants matter"**：渐近复杂度告诉你「能快到什么程度」，常数决定「在小规模上到底快不快」。所以实践中常见的策略是——**小任务不做并行**（如 `RecursiveAction` 模板里的「任务足够小就地执行」），只在规模足够大时才分叉。

## 6. 代码示例

### 6.1 官方课程代码

讲义 `20-concurrency-part3.pdf` 第 19 页给出迭代版前缀和的 Java 实现：

```java
void computePrefixSums(long[] a) {
  for (int gap = 1; gap < a.length; gap *= 2) {
    parfor (int i = gap-1; i+gap < a.length; i += 2*gap) {
      a[i+gap] = a[i] + a[i+gap];
    }
  }
  for (int gap = a.length/2; gap > 0; gap /= 2) {
    parfor (int i = gap-1; i+gap < a.length; i += 2*gap) {
      a[i] = a[i] + ((i-gap >= 0) ? a[i-gap] : 0);
    }
  }
}
```

第 25 页给出 `Callable` 接口：

```java
public interface Callable<V> {
    V call() throws Exception;
}
```

第 26 页给出 `Future` 与 `ExecutorService`：

```java
public interface Future<V> {
    V get();
    V get(long timeout, TimeUnit unit);
    boolean isDone();
    boolean cancel(boolean mayInterruptIfRunning);
    boolean isCancelled();
}

public interface ExecutorService {
    Future<?> submit(Runnable task);
    <V> Future<V> submit(Callable<V> task);
    <V> List<Future<V>> invokeAll(Collection<Callable<V>> tasks);
    <V> Future<V> invokeAny(Collection<Callable<V>> tasks);
}
```

第 27 页给出 `Executors` 工厂方法：`newSingleThreadExecutor()`、`newFixedThreadPool(int n)`、`newCachedThreadPool()`、`newScheduledThreadPool(int n)`。

第 30 页给出 `RecursiveAction` 的标准模板：

```java
public class MyActionFoo extends RecursiveAction {
    public MyActionFoo(...) { store the data fields we need; }

    @Override
    public void compute() {
      if (the task is small) { do the work here; return; }
      invokeAll(new MyActionFoo(...), new MyActionFoo(...), ...);
    }
}
```

第 31 页引用示例文件 `PrefixSumsParallelImpl.java`、`PrefixSumsParallelLoop1.java`、`PrefixSumsParallelLoop2.java`。

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：串行前缀和（作为正确性基准）。**

```java
public static long[] prefixSumsSequential(long[] a) {
    long[] out = a.clone();
    for (int i = 1; i < out.length; i++) {
        out[i] = out[i - 1] + out[i];   // 依赖链长度 n-1，无法并行
    }
    return out;
}
```

**示例 B：用 Fork/Join 实现的并行分治前缀和（两趟：先求块和，再传播）。**

```java
import java.util.concurrent.RecursiveAction;

public class PrefixSumTask extends RecursiveAction {
    private final long[] a;
    private final int lo, hi;          // 处理区间 [lo, hi)
    private static final int THRESHOLD = 1024;   // 小于此规模就串行：Constants matter

    public PrefixSumTask(long[] a, int lo, int hi) {
        this.a = a; this.lo = lo; this.hi = hi;
    }

    @Override
    protected void compute() {
        if (hi - lo <= THRESHOLD) {
            for (int i = lo + 1; i < hi; i++) {   // 就地变成块内前缀和
                a[i] = a[i - 1] + a[i];
            }
            return;
        }
        int mid = (lo + hi) >>> 1;
        invokeAll(new PrefixSumTask(a, lo, mid),   // fork 左半
                  new PrefixSumTask(a, mid, hi));  // fork 右半
        // join 之后：左半已是正确前缀，右半只是块内前缀
        long leftTotal = a[mid - 1];
        for (int i = mid; i < hi; i++) {           // 把左边总和补到右半
            a[i] = a[i] + leftTotal;
        }
    }
}
```

调用方式：

```java
ForkJoinPool pool = new ForkJoinPool();          // 默认用可用核心数
pool.invoke(new PrefixSumTask(data, 0, data.length));
```

注意两点：① `THRESHOLD` 的存在正是「常数很重要」的体现，太小的任务分叉反而更慢；② `invokeAll` 会等待两个子任务都完成，相当于 fork + join 的组合。

**示例 C：用 `ExecutorService` 提交有返回值的任务。**

```java
ExecutorService pool = Executors.newFixedThreadPool(
        Runtime.getRuntime().availableProcessors());
try {
    List<Future<Long>> futures = new ArrayList<>();
    for (int part = 0; part < 8; part++) {
        final int p = part;
        futures.add(pool.submit(() -> sumRange(data, p * chunk, (p + 1) * chunk)));
    }
    long total = 0;
    for (Future<Long> f : futures) {
        total += f.get();       // 阻塞直到该分片算完
    }
    System.out.println(total);
} finally {
    pool.shutdown();            // 不 shutdown 的话 JVM 不会退出
}
```

`Future.get()` 会把子线程中的异常包装成 `ExecutionException` 抛出——这是它与「裸 `Thread` + 共享变量」相比的一大优点：错误不会被悄悄吞掉。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| Thread Confinement（线程封闭） | Immutability（不可变性） | 封闭是「别人根本拿不到」，靠隔离；不可变是「谁都能拿但改不了」，靠禁止写。前者依赖纪律，后者可由编译器强制 |
| `Callable<V>` | `Runnable` | `Runnable.run()` 无返回值、不能抛受检异常；`Callable.call()` 返回 `V` 且可抛异常，配合 `Future` 取值 |
| `invokeAll` | `invokeAny` | `invokeAll` 执行全部任务并返回所有结果；`invokeAny` 只要**任意一个**成功就返回，其余被取消 |
| `RecursiveAction` | `RecursiveTask<V>` | 前者无返回值（适合原地修改数组）；后者有返回值（适合归约求和） |
| Winding（上行） | Unwinding（下行） | 上行把「块内和」汇总到块尾，是 reduce 方向；下行把「左侧前缀」传播到右侧块，是 scan 方向 |
| Work（功）最优 | Depth（深度）最优 | 串行前缀和 Work = n-1 但 Depth = n-1；并行版 Depth = lg n 但 Work ≈ 2n。两者不可兼得，需要权衡 |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-214/slides/20-concurrency-part3.pdf`
- **总页数**：34 页
- **本节重点页码**：
  - 第 4–5 页：上节回顾（死锁处理、Java 并发工具）
  - 第 6 页：不可变性的力量、`final` 基本类型
  - 第 7–8 页：本讲大纲与 Work/Breadth/Depth 回顾
  - 第 9 页：Java `for` 与 Python 的顺序语义
  - 第 10 页：Nesl 并行快排
  - 第 11 页：前缀和定义与例子
  - 第 12–17 页：Winding / Unwinding 图解推演
  - 第 18 页：前缀和伪代码
  - 第 19 页：迭代版 Java 实现
  - 第 20 页：递归版实现
  - 第 21–22 页：Work O(n) / Depth O(lg n) 分析
  - 第 23 页：`parfor` 的分段并行化策略
  - 第 24–27 页：`Runnable`、`Callable`、`Future`、`ExecutorService`、`Executors`
  - 第 28–30 页：Fork/Join 与 `RecursiveAction` 模板
  - 第 31 页：`PrefixSumsParallelImpl.java` 等示例文件
  - 第 32–33 页：性能对比与「Constants matter」
- **原始链接**：https://www.cs.cmu.edu/~aldrich/214/slides/20-concurrency-part3.pdf

## 9. 对应视频

未找到官方公开录像。

## 10. 本节复习

- 线程安全策略优先级：不可变 > 线程封闭 > 同步。不可变对象无写操作，因而不可能构成数据竞争。
- 真正的不可变类需要：`final` 字段、`final` 类、无 `this` 逃逸、对可变字段做防御性拷贝、无修改方法。
- 前缀和并行化分两阶段：Winding（自底向上求块和）与 Unwinding（自顶向下传播前缀）。
- 串行前缀和 Work = Depth = n−1；并行版 Work ≈ 2n、Depth = 2·lg n。
- `Callable` + `Future` 让任务有返回值、可抛异常；`ExecutorService` 管理线程池。
- Fork/Join 通过工作窃取实现负载均衡；`RecursiveAction` 适合原地修改，`RecursiveTask<V>` 适合归约。
- 并行不必然更快：多做功、内存访问不连续、调度同步开销三项「常数」常吃掉理论收益。
- 实践准则：小任务串行执行（设置阈值），只在规模足够大时分叉。

## 11. 自我检查

**Q1.** 给定 `x = [2, 4, 6, 8, 10, 12, 14, 16]`，请手工写出 Winding 每一层结束后的数组，以及 Unwinding 每一层结束后的数组，最后给出前缀和。

**Q2.** 长度为 n = 1024 的数组，串行前缀和的 Work 与 Depth 各是多少？并行版呢？若只有 4 个核心，理论加速比上限大约是多少？请说明你的估算依据。

**Q3.** 为什么 `RecursiveAction` 的 `compute()` 里要先判断「任务是否足够小」？如果不判断会发生什么？

**Q4.** 下面这个类声称不可变，请指出至少两个问题：

```java
public class Schedule {
    private final List<String> slots;
    public Schedule(List<String> slots) { this.slots = slots; }
    public List<String> getSlots() { return slots; }
}
```

**Q5.** 有同学用 8 条线程各自计算数组的 1/8 段和，最后在主线程累加，测出的加速比只有 3 倍。请列出至少三个可能的原因。

<details>
<summary>参考答案</summary>

**A1.** 初始 `[2,4,6,8,10,12,14,16]`。
Winding：gap=1 → `[2,6,6,14,10,22,14,30]`；gap=2 → `[2,6,6,20,10,22,14,52]`；gap=4 → `[2,6,6,20,10,22,14,72]`。
Unwinding：gap=4 → 只有 i=3，`i-gap<0` 跳过，不变；gap=2 → i=1 跳过、i=5：`22+20=42` → `[2,6,6,20,10,42,14,72]`；gap=1 → i=0 跳过、i=2：`6+6=12`、i=4：`10+20=30`、i=6：`14+42=56` → `[2,6,12,20,30,42,56,72]`。
校验：总和应为 72 ✓。

**A2.** 串行：Work = 1023，Depth = 1023。并行：Work ≈ 2n = 2048（上行约 n、下行约 n），Depth = 2·lg 1024 = 20。4 核心时，按 `加速比 ≤ Work_serial / max(Depth_parallel, Work_parallel / P)`：`Work_parallel / P = 2048/4 = 512`，远大于 Depth = 20，所以并行版耗时约为 512 步（而非 20 步）；相对串行 1023 步，上限约 2 倍。也就是说 4 个核心时瓶颈是「做了两倍的功」，而不是深度。

**A3.** 若不判断，任务会一直二分到区间长度为 1 或 0，产生约 2n 个任务对象，每个都要入队、被调度、被 join。任务创建与调度开销远超「几次加法」的成本，程序会比串行慢若干倍，甚至因栈深/队列过长而栈溢出或内存耗尽。阈值的存在正是把「并行的固定成本」摊到足够多的有效工作上。

**A4.** ① 没有做防御性拷贝：调用者保留传入 `List` 的引用，之后 `slots.add(...)` 就能改掉「不可变」对象的内容；② `getSlots()` 直接返回内部引用，任何调用者都能修改列表；③ 类未声明 `final`，子类可以添加可变状态并覆盖方法。修正：构造器中 `this.slots = List.copyOf(slots)`（或 `Collections.unmodifiableList(new ArrayList<>(slots))`），`getSlots()` 返回不可变视图，并把类声明为 `final`。

**A5.** 可能原因包括：① **Amdahl 效应**——分片、提交、汇总等串行部分占比不小，尤其数组不大时；② **任务粒度过细**——每段工作量太小，线程创建/唤醒/`join` 开销占比高；③ **内存带宽与缓存**——8 条线程同时扫内存会争抢带宽，且各自数据不在同一缓存行/同一 NUMA 节点，实际带宽成为瓶颈；④ **伪共享（false sharing）**——若各线程写入的累加变量落在同一缓存行，会互相使缓存行失效；⑤ **负载不均或超线程**——8 条线程可能只对应 4 个物理核心。任答三条即可。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-18-Concurrency-Part2]]——同步、死锁与 `java.util.concurrent`。
- 下一讲：[[15-214-20-Distributed-Systems-Part1]]——从多核走向多机：Java I/O、套接字、失败模型。
- 相关讲次：[[15-214-17-Concurrency-Part1]]（Work/Depth/Amdahl）、[[15-214-22-Distributed-Systems-Part3]]（MapReduce 中的并行 reduce）。
- 课程导航：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]、[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]。
- 术语条目：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Thread Safety 线程安全、Concurrency 并发）。
