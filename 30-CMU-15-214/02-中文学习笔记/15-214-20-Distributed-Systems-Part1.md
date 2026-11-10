---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L20
topic: Distributed System Design, Part 1 - Java I/O, Networks, Failures, and Replication
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - 分布式系统
  - Java-IO
  - 套接字
  - 失败模型
  - 复制
---

# 第 20 讲 分布式系统设计（一）：Java I/O、网络与失败模型

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。

## 1. 本节学习目标

- 能说出 `InputStream` / `OutputStream` 这一对流抽象的职责，并解释为什么它们是「一切 I/O 的根基」。
- 能用 `Serializable` 把对象写进文件流再读回来，并知道什么情况下会抛 `NotSerializableException`。
- 能描述 TCP 与 UDP 的差别，并说明各自适合什么场景。
- 能写一个最小的 `ServerSocket` + `Socket` 回声服务端与客户端。
- 能列举至少六种失败行为（fail-stop、网络分区、消息损坏、拜占庭……），并说明哪些「常见假设」是危险的。
- 能复述被动主备复制（passive primary-backup replication）的五步协议，并指出它的四个以上缺陷。
- 能解释「健壮性 vs 冗余度」曲线与端到端原则（end-to-end principle）。

## 2. 前置知识

- [[15-214-19-Concurrency-Part3]]：线程池、`Callable`/`Future`、并行任务的失败传播。
- [[15-214-07-Design-Patterns]]：Adapter（适配器）与 Decorator（装饰器）——`InputStream` 的包装器家族正是这两个模式的工业级应用。
- [[15-214-06-Mutability-and-Java-Potpourri]]：不可变性与 `final`，理解「共享状态」为何在分布式下更难。
- 外部概念：进程与文件描述符、字节与字符编码、IP 地址与端口号。

## 3. 核心概念

- **Stream（流）**：一串按顺序到达的数据。I/O 的基本抽象——不管背后是文件、内存、管道还是网络，看到的都是流。
- **InputStream / OutputStream（输入流/输出流）**：字节级的读写抽象，核心方法是 `int read()` 与 `void write(int b)`。
- **PrintStream（打印流）**：带 `print`/`println` 便利方法的输出流；`System.out` 就是它的实例。
- **Serializable（可序列化）**：一个**标记接口（marker interface）**，没有任何方法；实现它即表示「这个对象允许被转换成字节序列」。
- **Serialization（序列化）/ Deserialization（反序列化）**：把对象图转成字节流 / 把字节流转回对象图。
- **Protocol（协议）**：通信双方就「如何通信」达成的约定——先说什么、后说什么、什么算合法回应。
- **TCP（传输控制协议）**：可靠的、面向连接的**字节流**；保证顺序与不丢失，代价是握手、确认与重传。
- **UDP（用户数据报协议）**：不可靠的、无连接的**离散数据包**；不保证到达、不保证顺序，但开销小、延迟低。
- **Socket（套接字）**：`(IP 地址, 端口号)` 组成的通信端点。客户端用 `Socket` 主动连接，服务端用 `ServerSocket` 被动接受。
- **Fail-stop（停止式失败）**：组件一旦失败就彻底停下、不再发出任何消息——这是最容易处理的失败模型，也是最不现实的假设。
- **Byzantine failure（拜占庭失败）**：组件不仅失败，还发出**错误甚至恶意**的消息。
- **Replication（复制）**：把同一份数据放在多台机器上，用冗余换可靠性。
- **Availability（可用性）**：「5 个 9」= 99.999% 的时间系统可用。

## 4. 通俗理解

**流是什么？** 想象一根水管。你不在乎水是从水库、水塔还是另一根管子来的，你只在乎「拧开就有水，一滴一滴地来」。`InputStream` 就是这根水管的进水口，`read()` 就是接一滴水。文件、网络连接、压缩数据、加密数据——全都套着同一根管子的接口，所以你可以随意串联（这就是装饰器模式在 I/O 库中的大规模应用）。

**协议是什么？** 课件用「通过旅行社买机票」举例：

```
友好的问候。        →  Friendly greeting.
含糊的回应。        →  Muttered reply.
目的地？            →  Destination?
匹兹堡。            →  Pittsburgh.
谢谢。              →  Thank you.
```

双方不需要事先商量每一句措辞，但**都必须知道这个对话的骨架**：先打招呼，再问目的地，再回答，最后致谢。如果一方突然开始问「你要靠窗还是靠走道」，而另一方还在等「目的地」，对话就崩了。协议就是那个骨架。

**为什么分布式这么难？** 单机程序里，「出错」基本等于「程序崩了」，你能立刻知道。分布式系统里，你给另一台机器发了个请求，然后**没收到回复**。可能的原因有：请求丢了、对方崩了、对方算完了但回复丢了、网络慢到还没到、对方根本不存在。**你无法区分这些情况**——这就是「部分失败（partial failure）」的本质困难。课件里 Facebook 工程师那句回答最传神：

> 学者：「如果 X 发生了会怎样？」
> 工程师：「我们不知道。X 还没发生过……但真发生了会很糟。」

## 5. 原理与推导

### 5.1 Java I/O：一条从字节到对象的抽象阶梯

课件的讲解顺序本身就是一条抽象阶梯，从最底层往上爬。

**第一层：字节流。** `java.io.InputStream` 与 `java.io.OutputStream` 是所有字节 I/O 的根：

```java
public abstract class InputStream {
    void close();
    abstract int read();          // 返回 0-255，流结束返回 -1
    int read(byte[] b);           // 批量读，返回实际读到的字节数
}

public abstract class OutputStream {
    void close();
    void flush();                 // 把缓冲区内容真正推出去
    abstract void write(int b);
    void write(byte[] b);
}
```

注意 `read()` 返回 `int` 而不是 `byte`——因为要用 `-1` 表示「流结束（EOF）」，而 `byte` 的取值范围装不下这个额外值。这是 Java I/O 设计里一个常被误解的细节。

**第二层：便利流。** `PrintStream` 在 `OutputStream` 之上加了类型化的打印方法：

```java
void print(String s);   void print(int i);
void print(boolean b);  void print(Object o);
void println(String s); void println(int i); ...
```

`System.out` 就是 `PrintStream` 的实例，所以 `System.out.println("hi")` 本质上是在往一个字节流里写字节。

**第三层：对象流。** 要读写任意对象，让类实现 `java.io.Serializable`：

```java
public class QABean implements Serializable { ... }
```

`Serializable` 是个空接口（marker interface）——它不提供任何方法，只起「打标记」的作用，让 `ObjectOutputStream` 知道「这个类允许被序列化」。Java 会递归地序列化所有非 `transient` 字段；**如果某个字段的类型本身不可序列化，运行时会抛 `NotSerializableException`**。

课件提到的示例文件是 `QABean.java` 与 `FileObjectExample.java`。

这里有个重要的设计取舍：序列化把「对象的内部表示」暴露成了持久格式。一旦类结构改变（加字段、改类型），旧的字节流就可能读不回来。这也是后来 Java 引入 `serialVersionUID` 与 `transient` 关键字的原因。

### 5.2 网络分层：每一层只关心自己那一段

课件给出的分层图（自下而上）：

| 层次 | 例子 | 关心什么 |
|---|---|---|
| 物理层 / 数据链路层 | 以太网、Wi-Fi | 比特如何在介质上传输 |
| 网络层 | IP | 数据包如何从一台主机路由到另一台 |
| 传输层 | TCP / UDP | 端到端的可靠性、顺序、流量控制 |
| 应用层协议 | HTTP / FTP / SMTP | 应用之间说什么话 |
| 内容格式 | HTML / Text / JPG / GIF / PDF | 字节如何解释为有意义的数据 |

**关键点：每一层都是对下一层的抽象。** 写 HTTP 服务器的人不需要关心 TCP 的重传算法；写 TCP 实现的人不需要关心以太网的电压。这就是「信息隐藏」在网络栈上的体现。

### 5.3 TCP 与 UDP：两种传输语义

| 维度 | UDP（User Datagram Protocol） | TCP（Transmission Control Protocol） |
|---|---|---|
| 连接 | 无连接，直接发 | 面向连接，需三次握手 |
| 数据单位 | 离散的数据包（datagram），边界保留 | 连续字节流，**边界不保留** |
| 可靠性 | 不保证到达、不保证顺序、不保证不重复 | 保证按序到达、不丢失、不重复 |
| 开销 | 小（8 字节头） | 大（20 字节头 + 确认 + 重传） |
| 典型用途 | DNS 查询、视频直播、游戏状态同步、日志上报 | HTTP、SSH、数据库连接、文件传输 |
| 失败时的表现 | 静默丢包，应用自己发现 | 卡住或连接被重置 |

课件的措辞非常精简：**UDP = "Unreliable, discrete packets of data"；TCP = "Reliable data stream"**。

一个常被忽略的后果：TCP 是**字节流**，它不保留「消息边界」。你 `write` 了两次 100 字节，对方可能一次 `read` 到 200 字节，也可能分三次读到。所以应用层协议必须自己定义「一条消息到哪里结束」（长度前缀、分隔符、或固定长度）。UDP 则天然保留边界——一个 `send` 对应一个 `receive`（如果没丢的话）。

### 5.4 地址与套接字

- **IPv4 地址**：4 字节，例如 `127.0.0.1`（本机回环）。全空间约 40 亿个地址。
- **DNS（域名系统）**：把人类可读的主机名映射到 IP 地址。
- **端口（port）**：16 位无符号数，范围 0–65535。约定俗成：80 是 HTTP，443 是 HTTPS，22 是 SSH。
- **套接字（socket）**：`(IP, port)` 二元组唯一标识网络上的一个通信端点。

Java 中的对应类：

```java
java.net.InetAddress     // 主机地址（Inet4Address / Inet6Address 是子类）
java.net.Socket          // 客户端连接
java.net.ServerSocket    // 服务端监听
```

课件列出的 API：

```java
// InetAddress
static InetAddress getByName(String host);
static InetAddress getByAddress(byte[] b);
static InetAddress getLocalHost();

// Socket
Socket(InetAddress addr, int port);
boolean      isConnected();
boolean      isClosed();
void         close();
InputStream  getInputStream();
OutputStream getOutputStream();

// ServerSocket
ServerSocket(int port);
Socket       accept();     // 阻塞直到有客户端连进来
void         close();
```

`accept()` 是理解服务端结构的关键：它**阻塞**等待，每来一个客户端就返回一个新的 `Socket`。所以「一个服务端服务多个客户端」的标准做法是：主线程循环 `accept()`，每接受一个连接就把它交给一条新线程（或线程池）处理。课件中的示例文件 `TransferThread.java`、`TextSocketClient.java`、`TextSocketServer.java` 就是这个结构。

### 5.5 失败模型：先假设最坏情况

课件列出的失败行为类型（第 29 页）：

1. **Fail-stop**：进程崩溃，不再产生任何输出。最容易处理。
2. **其他停止式失败**：进程挂起（hang）、死循环、被 SIGSTOP 暂停——它不发出错误消息，但也不再前进。
3. **通信失败**：
   - 发送/接收遗漏（send/receive omission）：消息丢了；
   - **网络分区（network partition）**：网络被切成两半，两边互相看不见但各自都活着；
   - 消息损坏（message corruption）：收到的字节和发出的不一样。
4. **性能失败**：丢包率高、吞吐低、延迟高。注意这些不是「错误」，但会让系统表现为「像挂了」。
5. **数据损坏（data corruption）**：磁盘上的数据悄悄变了。
6. **拜占庭失败（Byzantine failures）**：节点发出任意错误消息，甚至恶意串通。

课件接着列出一串「常见假设」，并用 "(ugh)" 标注了其中两条最危险的：

- 其他人的行为是 fail-stop（ugh）
- 网络是可靠的（ugh）
- 网络半可靠但是异步的
- 网络有丢包但消息不损坏
- 网络故障是传递性的（A 连不上 B、B 连不上 C ⇒ A 连不上 C）
- 失败是独立的
- 本地数据不会损坏
- 失败可以被可靠检测
- 失败只能被不可靠检测

**为什么 fail-stop 假设危险？** 因为真实系统里最常见的是「半死不活」：进程还在、端口还开着，但业务逻辑卡死了。这时候从外部看它「没响应」，与网络分区**完全无法区分**。课件在第 26 页反复强调这一点：

> 主库失败 vs 网络失败？（Primary failure vs. network failure?）
> 备库失败 vs 网络失败？（Backup failure vs. network failure?）

这个「无法区分」正是分布式系统一切复杂性的源头。

### 5.6 设计目标与两条原则

课件列出的分布式系统设计目标（第 31 页）：

- **端到端原则（end-to-end principle）**：能在端节点实现的功能就不要放在中间节点。例如「可靠传输」若由应用自己校验，就不必让每个路由器都做——中间节点的通用机制越少，系统越简单、越可扩展。
- **健壮性原则（robustness principle）**：「发送时严格，接收时宽容」（Be strict in what you send, but be liberal in what you accept）。这条也叫 Postel 定律，是 TCP/IP 成功的文化基础之一，但现代实践也批评它导致了协议实现的松散。
- **协议（protocols）**：明确定义交互序列。
- **明确的失败行为（failure behaviors）**：写清楚「失败时会发生什么」。
- **能从增量变更中获益**：加一台机器不该要求全系统停机重配（这条直接导向后面的「一致性哈希」）。
- **冗余（redundancy）**：数据复制 + 正确性校验。

### 5.7 健壮性 vs 冗余度曲线

课件第 22 页有一张只标了两个轴的图：横轴 **redundancy（冗余度）**，纵轴 **robustness（健壮性）**，中间一个问号。

图的含义是：冗余增加初期，健壮性快速上升；但**超过某个点后收益递减**，甚至可能因为「更多副本意味着更多需要协调的失败点」而下降。这就是为什么「多加几个副本」不是万能药——每多一个副本，就多一份需要检测、需要同步、可能不一致的状态。

### 5.8 案例：被动主备复制

**问题**：单个数据库服务器可能挂掉。**方案**：把数据复制到多台服务器，一台 primary（主），其余 backup（备）。

架构：

```
client → front-end → primary:  {alice:90, bob:42, …}
                          ↓ 同步
                     backup:   {alice:90, bob:42, …}
                     backup:   {…}
```

**协议五步（第 24 页）**：

1. 前端把带**唯一 ID** 的请求发给主库；
2. 主库检查请求 ID——**如果这个请求已经执行过，就直接重发上次的响应并退出协议**（这是幂等性/去重的关键）；
3. 主库执行请求并保存响应；
4. **如果请求是更新**，主库把「更新后的状态 + ID + 响应」发给所有备库，每个备库回一个确认（ack）；
5. 收到**所有**确认后，主库才把响应发回前端。

第 5 步是「被动」的含义：主库要等所有备库都落盘才算成功。这保证了「只要主库回复了客户端，数据就一定在至少两台机器上」——即所谓**强一致（strong consistency）**的雏形。

**为什么第 2 步必要？** 因为前端可能因为超时而重发同一请求。若主库不做去重，「转账 100 元」会被执行两次。唯一 ID + 缓存响应 = 幂等重试（idempotent retry）。

### 5.9 主备复制的七个问题

课件第 26–27 页列出的问题，值得逐条理解：

1. **主库崩溃后，谁来当新主库？** 多个前端可能各自认为不同的备库是新的主库，导致**脑裂（split-brain）**。
2. **主库失败 vs 网络失败无法区分**：主库可能只是暂时联系不上，此时选新主会导致两个主库。
3. **新主库上位后，存活副本必须就当前状态达成一致**：新主可能落后于旧主（有些更新还没同步完）。
4. **备库崩溃时主库必须检测到并把它移出集群**——否则主库会永远等它的 ack。
5. **备库失败 vs 网络失败无法区分**：误踢一个只是网络抖动的备库，会降低冗余度。
6. **副本失败后恢复，必须能察觉自己曾经失败过**：它本地状态可能是旧的，需要重新同步。
7. **消息乱序**：并发请求的更新消息可能乱序到达备库，导致备库状态错乱。

**性能与吞吐问题**：

- **2n 条消息**（n 个副本）：一条更新要发 n−1 份 + 收 n−1 个 ack，约 2(n−1) 条。
- **任一副本失败都会拖慢响应**：因为要等「所有」ack。
- **常规网络抖动也会拖慢响应**：TCP 重传、路由收敛都需要时间。
- **吞吐上不去**：每次更新都写所有副本，但只有主库回应请求——写放大严重。课件直言「Does not address the scalability challenge」。

### 5.10 Facebook 的变体：read-any, write-all

课件第 28 页提到 Facebook 只用主备复制解决**可扩展性**（不解决一致性）：读可以打到任意副本，写必须写全部。主副本在加州 Palo Alto。这种方案在读多写少的场景下很划算，但读到的可能是旧数据（最终一致性）。

### 5.11 RAID：单机内的「矛盾案例」

RAID = Redundant Array of Inexpensive Disks。在一台机器内把数据复制/校验到多块磁盘：5 块 1TB 盘可得 4TB 可用空间，并能从任意单盘故障中恢复。

课件把它称作「a case of contradictions（一个矛盾案例）」，并在第 33 页抛出问题：**Google 用 RAID 吗？** 这个问题指向一个重要的工程判断——Google 认为「磁盘故障是常态而非异常」，因此在**软件层**做冗余（GFS 的三副本），而不是依赖硬件 RAID。这正好呼应「端到端原则」：可靠性放在能看见全局的那一层做，比放在底层硬件里更有效。

## 6. 代码示例

### 6.1 官方课程代码

讲义 `21-distributed-systems.pdf` 第 9 页给出 `PrintStream` 的接口：

```java
void close();
void flush();
void print(String s);
void print(int i);
void print(boolean b);
void print(Object o);
…
void println(String s);
void println(int i);
void println(boolean b);
void println(Object o);
…
```

第 10 页给出流抽象：

```java
// java.io.InputStream
void          close();
abstract int  read();
int           read(byte[] b);

// java.io.OutputStream
void          close();
void          flush();
abstract void write(int b);
void          write(byte[] b);

// PrintStream 的构造器
PrintStream(OutputStream out);
PrintStream(File file);
PrintStream(String filename);
```

第 17 页给出网络 API：

```java
// java.net.InetAddress
static InetAddress getByName(String host);
static InetAddress getByAddress(byte[] b);
static InetAddress getLocalHost();

// java.net.Socket
Socket(InetAddress addr, int port);
boolean      isConnected();
boolean      isClosed();
void         close();
InputStream  getInputStream();
OutputStream getOutputStream();

// java.net.ServerSocket
ServerSocket(int port);
Socket       accept();
void         close();
```

第 18 页引用示例文件：`TransferThread.java`、`TextSocketClient.java`、`TextSocketServer.java`。

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：对象序列化往返。**

```java
import java.io.*;

public class QABean implements Serializable {
    private static final long serialVersionUID = 1L;   // 版本号：类结构变化时用于检测不兼容
    private final String question;
    private final String answer;
    private transient String cachedHash;               // transient：不参与序列化

    public QABean(String q, String a) { this.question = q; this.answer = a; }

    public static void main(String[] args) throws Exception {
        QABean bean = new QABean("What is a stream?", "An ordered sequence of bytes.");
        File f = new File("qa.ser");

        try (ObjectOutputStream out = new ObjectOutputStream(new FileOutputStream(f))) {
            out.writeObject(bean);                     // 序列化
        }
        try (ObjectInputStream in = new ObjectInputStream(new FileInputStream(f))) {
            QABean back = (QABean) in.readObject();     // 反序列化，注意强转
            System.out.println(back.question + " -> " + back.answer);
        }
    }
}
```

若把 `answer` 的类型换成某个未实现 `Serializable` 的类，`writeObject` 就会抛 `NotSerializableException`。注意 `serialVersionUID` 与 `transient` 这两个关键字在课件里没有展开，但它们是工程上必须知道的。

**示例 B：最小 TCP 回声服务端（每连接一线程）。**

```java
import java.io.*;
import java.net.*;
import java.util.concurrent.*;

public class EchoServer {
    public static void main(String[] args) throws IOException {
        ExecutorService pool = Executors.newCachedThreadPool();   // 复用线程，别为每个连接 new Thread
        try (ServerSocket server = new ServerSocket(8080)) {
            System.out.println("listening on 8080");
            while (true) {
                Socket conn = server.accept();        // 阻塞等待下一个客户端
                pool.submit(() -> handle(conn));      // 交给线程池处理
            }
        }
    }

    private static void handle(Socket conn) {
        try (Socket s = conn;
             BufferedReader in = new BufferedReader(
                     new InputStreamReader(s.getInputStream(), "UTF-8"));
             PrintWriter out = new PrintWriter(
                     new OutputStreamWriter(s.getOutputStream(), "UTF-8"), true)) {
            String line;
            while ((line = in.readLine()) != null) {  // readLine 依赖对端发 '\n'
                out.println("echo: " + line);
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
```

**注意这里应用层自定义了协议**：一行一条消息，以换行符分隔。TCP 本身不提供「行」的概念，`readLine()` 之所以能工作，是因为双方都同意「`\n` 是消息边界」。这就是课件「应用层协议」那一层在做的事。

**示例 C：客户端。**

```java
import java.io.*;
import java.net.*;

public class EchoClient {
    public static void main(String[] args) throws IOException {
        try (Socket s = new Socket(InetAddress.getByName("127.0.0.1"), 8080);
             PrintWriter out = new PrintWriter(
                     new OutputStreamWriter(s.getOutputStream(), "UTF-8"), true);
             BufferedReader in = new BufferedReader(
                     new InputStreamReader(s.getInputStream(), "UTF-8"))) {

            out.println("hello distributed world");
            System.out.println(in.readLine());   // 会阻塞直到服务端回应
        }
    }
}
```

`in.readLine()` 的阻塞正是「部分失败」的日常版本：如果服务端崩了而 TCP 还没超时，客户端会**一直等**。生产代码必须设置 `setSoTimeout(ms)`，否则一个卡死的对端就能拖住整条线程。

**示例 D：幂等请求去重（对应协议第 2 步）。**

```java
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

public class IdempotentHandler {
    private final ConcurrentMap<String, String> executedResponses = new ConcurrentHashMap<>();

    /** 若同一 requestId 已执行过，直接返回上次的响应，不重复执行副作用。 */
    public String handle(String requestId, Runnable sideEffect) {
        return executedResponses.computeIfAbsent(requestId, id -> {
            sideEffect.run();                 // 只执行一次
            return "ok:" + id;
        });
    }
}
```

`computeIfAbsent` 在 `ConcurrentHashMap` 上是原子的，所以即使两个前端同时重发同一 ID，副作用也只会发生一次。这就是「唯一 ID + 缓存响应」在单机上的实现。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 关键差别 |
|---|---|---|
| `InputStream`（字节流） | `Reader`（字符流） | 前者读写 `byte`，后者读写 `char` 并处理编码；网络传输永远是字节，字符层是应用自己加的 |
| `read()` 返回 `-1` | `read()` 返回 `0` | `-1` 表示流结束（EOF）；`read(byte[])` 返回 `0` 只表示「这次没读到数据」，不代表结束 |
| TCP（字节流） | UDP（数据报） | TCP 可靠、有序、**无消息边界**；UDP 不可靠、可能乱序、**保留消息边界** |
| `Socket` | `ServerSocket` | 前者是「已建立的一条连接」，客户端主动创建；后者是「监听端口」，服务端被动等待 `accept()` |
| Fail-stop（停止式失败） | Byzantine failure（拜占庭失败） | 前者失败后**沉默**，可从「无响应」推断；后者失败后**说谎**，必须靠多副本投票才能识别 |
| 主库失败 | 网络失败 | 从外部**无法区分**——这正是主备复制所有复杂性的根源 |
| 复制（replication） | 分区（partitioning） | 复制是「同一份数据放多处」换可靠性/读吞吐；分区是「不同数据放不同处」换写吞吐与容量 |
| 冗余度增加 | 健壮性增加 | 初期正相关，超过拐点后收益递减甚至反转——更多副本 = 更多需要协调的失败点 |

## 8. 对应原版讲义

- **PDF 相对路径**：`90-原始PDF/15-214/slides/21-distributed-systems.pdf`
- **总页数**：34 页
- **本节重点页码**：
  - 第 2–5 页：教务通知与软件工程辅修介绍（非技术内容）
  - 第 6–7 页：上次课回顾——Java 并发框架实现前缀和
  - 第 8 页：本讲大纲
  - 第 9 页：`PrintStream` 接口
  - 第 10 页：`InputStream` / `OutputStream` 与 `PrintStream` 构造器
  - 第 11 页：`Serializable` 与 `NotSerializableException`
  - 第 12 页：分布式系统的定义与六大挑战
  - 第 13 页：协议（旅行社买机票类比）
  - 第 14 页：网络分层图
  - 第 15 页：UDP vs TCP
  - 第 16 页：IPv4 地址、DNS、端口、Java 网络类
  - 第 17 页：`InetAddress` / `Socket` / `ServerSocket` API
  - 第 18 页：Sockets 示例文件
  - 第 19 页：更高层抽象（RPC、RMI、MapReduce）
  - 第 22 页：健壮性 vs 冗余度曲线
  - 第 23–24 页：被动主备复制架构与五步协议
  - 第 26–27 页：主备复制的七类问题与性能/吞吐问题
  - 第 28 页：Facebook 的 read-any write-all 变体
  - 第 29 页：失败行为类型
  - 第 30 页：常见（危险）失败假设
  - 第 31 页：分布式系统设计目标（端到端原则、健壮性原则）
  - 第 32–33 页：RAID 与「Google 用 RAID 吗」
- **原始链接**：https://www.cs.cmu.edu/~aldrich/214/slides/21-distributed-systems.pdf

## 9. 对应视频

未找到官方公开录像。

## 10. 本节复习

- I/O 的根基是字节流：`InputStream.read()` / `OutputStream.write(int)`；`PrintStream` 只是加了打印便利方法。
- `Serializable` 是标记接口；字段不可序列化则运行时抛 `NotSerializableException`。
- 网络分层：物理/链路 → IP → TCP/UDP → 应用协议 → 内容格式，每层只关心自己那一段。
- TCP 可靠有序但是字节流（无消息边界）；UDP 不可靠但保留包边界。
- 套接字 = `(IP, port)`；服务端 `accept()` 阻塞等待，通常配合线程池处理并发连接。
- 失败类型：fail-stop、挂起、send/receive omission、网络分区、消息损坏、性能失败、数据损坏、拜占庭。
- 「主库失败」与「网络失败」不可区分——这是分布式系统复杂性的总源头。
- 被动主备复制五步：唯一 ID → 去重检查 → 执行并保存响应 → 广播更新并收集全部 ack → 回客户端。
- 主备复制的代价：2n 条消息、任一副本失败都拖慢响应、写放大导致吞吐上不去。
- 端到端原则：能在端节点做的就别放中间节点；健壮性原则：发送严格、接收宽容。

## 11. 自我检查

**Q1.** 为什么 `InputStream.read()` 的返回类型是 `int` 而不是 `byte`？

**Q2.** 有同学写了一个 TCP 聊天程序：客户端连续 `write("hello")` 和 `write("world")`，服务端一次 `read(buf)` 却读到了 `"helloworld"`。这是 bug 吗？应该怎么改？

**Q3.** 请解释为什么「主库崩溃」和「主库网络不通」在被动主备复制中必须被区分，但又无法被可靠区分。系统设计上通常怎么应对？

**Q4.** 被动主备复制协议第 2 步（检查请求 ID、若已执行则重发响应）如果被删掉，会出现什么问题？请举一个具体场景。

**Q5.** 课件把 RAID 称为「a case of contradictions」，并追问「Google 用 RAID 吗」。请说明这个问题背后的设计判断。

<details>
<summary>参考答案</summary>

**A1.** 因为需要用 `-1` 表示「流已结束（EOF）」。`byte` 的取值范围是 −128…127，无法在合法数据之外再腾出一个哨兵值；`int` 的 0…255 覆盖全部字节值，−1 则专门表示 EOF。`read(byte[])` 同样用 `-1` 表示 EOF，用 `0` 表示「本次没有数据但流未结束」（仅当传入长度为 0 的数组时才会返回 0）。

**A2.** 不是 bug，而是 TCP 语义的必然结果。TCP 是**字节流**，不保留应用层的消息边界；两次 `write` 的字节完全可能被合并成一次 `read`，也可能被拆成三次。修复方式是在应用层协议中显式定义边界，常见三种：① 长度前缀（先写 4 字节长度，再写内容）；② 分隔符（如 `\n`，配合 `BufferedReader.readLine()`）；③ 固定长度消息。UDP 则不会有这个问题，因为数据报天然保留边界。

**A3.** 必须区分：如果主库真的崩了，就需要选一个新主库继续服务；如果只是网络不通而主库还活着，选新主就会造成**两个主库同时接受写**（脑裂），数据永久分叉。无法可靠区分：从备库视角，「没收到心跳」既可能是对方进程死了，也可能是链路断了或消息丢了，二者在可观测行为上完全一致（这正是 FLP 不可能性与「两军问题」的直觉版本）。应对手段包括：引入**租约（lease）**让主库的权威自动过期、用**多数派 quorum**（如 Paxos/Raft）而非「任意一个备库」来选主、用** fencing token** 让旧主库的写被存储层拒绝。课件在本讲只提出问题，具体协议在后续课程/15-440 中展开。

**A4.** 前端在超时后会重发同一请求，而主库无法判断「这是新请求还是重发」，于是同一笔操作被执行两次。具体场景：用户点击「转账 100 元」，主库执行成功但响应在回程丢失，前端超时重发，主库再执行一次——用户被扣 200 元。加上唯一 ID + 响应缓存后，第二次请求命中缓存直接返回上次结果，副作用只发生一次，这就是**幂等重试（idempotent retry）**。

**A5.** RAID 在**单机硬件层**做冗余，能抵御单块磁盘故障。但 Google 的工程判断是：在大规模集群里，磁盘故障、整机故障、机架断电都是**常态**而非异常，硬件 RAID 无法抵御整机/机架级失败，而且 RAID 控制器本身也是单点。因此 Google 选择在**软件层**（GFS/Colossus）用跨机器的多副本实现冗余——把可靠性放在能看见全局的那一层。这体现了课件的「端到端原则」：功能应实现在能获得完整信息的端节点，而不是被封装在看不见全局的中间层。

</details>

## 12. 进一步学习

- 上一讲：[[15-214-19-Concurrency-Part3]]——不可变性与并行前缀和。
- 下一讲：[[15-214-21-Distributed-Systems-Part2]]——缓存、失效策略与分区（分片、一致性哈希、master/tablet）。
- 相关讲次：[[15-214-22-Distributed-Systems-Part3]]（MapReduce）、[[15-214-25-Data-Consistency]]（事务与两阶段提交）。
- 课程导航：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]、[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]。
- 术语条目：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Distributed System 分布式系统、Serialization 序列化）。
- 延伸阅读：Fielding 的 REST 论文（分层与端到端原则）、Saltzer/Reed/Clark 的 End-to-End Arguments in System Design。
