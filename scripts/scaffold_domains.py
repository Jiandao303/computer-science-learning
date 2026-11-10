#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 docs/ 下 16 个知识领域的骨架文件（幂等脚手架）。

每个领域生成三份文件：
    00-领域总览.md       定位、边界、前置、学习顺序
    01-知识点目录.md     可勾选的知识点清单
    02-权威课程与资料.md  课程 / 教材 / 官方文档

安全约定：
  * **只创建不覆盖**——目标文件已存在则跳过并打印 SKIP，绝不改动已有内容。
  * 课程链接会对照 sources/_url-check.json（由 scripts/verify_urls.py 生成）；
    未核验或核验失败的链接会被标注「⚠ 待核实」，不会被当成可用来源。

用法：
    python scripts/scaffold_domains.py
    python scripts/scaffold_domains.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(VAULT, "docs")
URLCHECK = os.path.join(VAULT, "sources", "_url-check.json")

DOMAINS = [
dict(
    key="10-数学基础", name="数学基础",
    tagline="为计算机科学提供三样工具：证明、计数、概率。",
    questions=["一个命题怎样才算被证明？", "算法的代价如何用数学界定？", "随机性如何建模并推出结论？"],
    not_scope="不做数学分析、实变函数、泛函分析的深度训练；不替代数值计算与最优化专门课程。",
    prereq=["高中代数与基础微积分直觉"],
    leads_to=["30 数据结构与算法", "160 计算机高级选修"],
    points=[
        ("逻辑与证明", ["命题逻辑与真值表", "谓词逻辑与量词", "直接证明与逆否", "反证法", "数学归纳法（弱/强）", "结构归纳法", "良序原理"]),
        ("集合与关系", ["集合运算与幂集", "笛卡尔积", "二元关系的性质", "等价关系与划分", "偏序关系与格", "单射/满射/双射", "可数性与对角线论证"]),
        ("图论", ["图的定义与表示", "路径、回路与连通性", "树与生成树", "欧拉回路与哈密顿回路", "平面图与欧拉公式", "图着色", "二分图与匹配"]),
        ("计数", ["加法原理与乘法原理", "排列与组合", "容斥原理", "鸽巢原理", "二项式系数与恒等式", "递推关系求解", "生成函数初步"]),
        ("离散概率", ["样本空间与事件", "条件概率", "贝叶斯公式", "随机变量与分布", "期望与方差", "独立性", "马尔可夫不等式与切比雪夫不等式", "大数定律", "中心极限定理"]),
        ("线性代数", ["向量空间与子空间", "矩阵运算与逆", "线性变换", "秩、零空间与列空间", "特征值与特征向量", "正交性与投影", "最小二乘", "奇异值分解"]),
        ("微积分", ["极限与连续", "导数与链式法则", "积分与微积分基本定理", "多元偏导与梯度", "泰勒展开", "拉格朗日乘子"]),
        ("数论", ["整除与同余", "模运算", "素数与算术基本定理", "欧几里得算法与扩展形式", "中国剩余定理", "快速幂与模逆元"]),
    ],
    courses=[
        ("6.042J Mathematics for Computer Science", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/6-042j-mathematics-for-computer-science-fall-2010/", "主课 · 离散数学，配合证明训练"),
        ("18.06 Linear Algebra", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/", "主课 · 线性代数"),
        ("6.041 Probabilistic Systems Analysis", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/6-041-probabilistic-systems-analysis-and-applied-probability-fall-2010/", "备选 · 概率论"),
        ("CS 70 Discrete Mathematics and Probability Theory", "UC Berkeley", "https://www.eecs70.org/", "备选 · 离散+概率合并讲"),
        ("CS 109 Introduction to Probability for Computer Scientists", "Stanford", "https://web.stanford.edu/class/cs109/", "备选 · 偏应用与统计推断"),
        ("18.404J Theory of Computation", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/18-404j-theory-of-computation-fall-2020/", "延伸 · 自动机与可计算性"),
    ],
    books=[("《Mathematics for Computer Science》", "6.042J 配套免费教材，证明写法最规范"),
           ("《Linear Algebra and Its Applications》", "Gilbert Strang，配 18.06"),
           ("《Introduction to Probability》", "Bertsekas & Tsitsiklis，配 6.041")],
),
dict(
    key="20-编程基础", name="编程基础",
    tagline="把一个想法变成能跑、能调、能改的程序。",
    questions=["语言如何表达控制流与数据？", "程序出错时如何定位？", "如何建立第一层抽象？"],
    not_scope="不教具体框架与业务；不追求某门语言的全部语法特性；不涉及工程协作（见 90 软件工程）。",
    prereq=["无（本领域是入口）"],
    leads_to=["30 数据结构与算法", "40 计算机组成"],
    points=[
        ("程序如何被执行", ["源文件到可执行文件：预处理/编译/汇编/链接", "解释执行与字节码", "栈与堆的区别", "值语义与引用语义"]),
        ("基本构件", ["变量、类型与类型转换", "表达式与运算符优先级", "条件与分支", "循环与迭代", "函数定义与调用", "参数传递（值/引用）", "递归与基准情形", "作用域与生命周期"]),
        ("数据组织", ["数组与越界", "字符串与编码", "结构体/记录/对象", "链表的构造与遍历", "字典/哈希表的使用", "文件读写", "命令行参数"]),
        ("错误处理与调试", ["异常与错误传播", "返回值约定（错误码）", "断言与不变式", "日志打印", "断点、单步、查看调用栈", "构造最小可复现例子"]),
        ("抽象机制", ["模块与包", "接口/协议/抽象类", "泛型初步", "高阶函数", "闭包与捕获"]),
        ("工具链", ["编辑器与 IDE", "编译器/解释器与版本管理", "包管理器与虚拟环境", "Git 基础命令", "终端与 shell 基础"]),
        ("质量习惯", ["单元测试的写法", "边界值与异常路径", "代码风格与格式化", "读懂报错信息"]),
    ],
    courses=[
        ("CS50x Introduction to Computer Science", "Harvard", "https://cs50.harvard.edu/x/", "主课 · 从 C 到 Python，作业密度高"),
        ("CS 61A Structure and Interpretation of Computer Programs", "UC Berkeley", "https://cs61a.org/", "主课备选 · Python 为主，抽象讲得深"),
        ("6.100L Introduction to CS and Programming Using Python", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/6-100l-introduction-to-cs-and-programming-using-python-fall-2022/", "备选 · 节奏平缓"),
        ("15-112 Fundamentals of Programming", "CMU", "https://www.cs.cmu.edu/~112/", "备选 · 作业量大、覆盖广"),
        ("Structure and Interpretation of Computer Programs", "MIT Press（在线全文）", "https://mitp-content-server.mit.edu/books/content/sectbyfn/books_pres_0/6515/sicp.zip/index.html", "教材 · 抽象与解释器视角"),
        ("The Python Tutorial", "Python 官方", "https://docs.python.org/3/tutorial/", "官方文档 · 查阅用"),
    ],
    books=[("《C Programming: A Modern Approach》", "K.N. King，C 语言最稳的教材"),
           ("《SICP》", "抽象与元语言抽象，读前几章即可")],
),
dict(
    key="30-数据结构与算法", name="数据结构与算法",
    tagline="回答「什么样的数据组织与求解策略，是足够快的」。",
    questions=["如何衡量一个算法的代价？", "哪种数据结构让目标操作最便宜？", "面对新问题该用哪种设计范式？"],
    not_scope="不做竞赛技巧的穷举；不替代具体系统的工程优化（见 40/50/70）。",
    prereq=["20 编程基础（函数、递归、指针/引用）", "10 数学基础（归纳、计数、渐进）"],
    leads_to=["40 计算机组成", "80 编译原理", "160 计算机高级选修"],
    points=[
        ("复杂度分析", ["渐进记号 O/Ω/Θ", "最坏、平均与摊还分析", "空间复杂度", "递归式与主定理", "增长率比较"]),
        ("线性结构", ["静态数组与动态数组", "单/双链表", "栈与应用（括号匹配、表达式求值）", "队列与双端队列", "并查集（路径压缩+按秩合并）"]),
        ("树", ["二叉树与遍历", "二叉搜索树", "平衡树（AVL/红黑树）", "堆与优先队列", "Trie", "线段树与树状数组", "B 树与 B+ 树（概念）"]),
        ("哈希", ["哈希函数设计", "链地址法与开放寻址", "负载因子与扩容", "一致性哈希"]),
        ("图", ["邻接表与邻接矩阵", "BFS 与 DFS", "拓扑排序", "Dijkstra / Bellman-Ford / Floyd", "最小生成树（Prim/Kruskal）", "强连通分量", "最大流初步"]),
        ("排序与选择", ["比较排序的下界", "归并排序", "快速排序与划分", "堆排序", "计数/基数排序", "稳定性与原地性", "快速选择"]),
        ("算法设计范式", ["分治", "贪心与正确性证明", "动态规划（状态定义/转移/边界）", "回溯与剪枝", "随机化算法"]),
        ("字符串", ["KMP", "Rabin-Karp", "后缀数组初步"]),
        ("复杂度理论入门", ["P 与 NP", "多项式归约", "NP 完全问题示例", "近似算法"]),
    ],
    courses=[
        ("6.006 Introduction to Algorithms", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/", "主课 · 讲原理不讲背诵"),
        ("Algorithms, 4th Edition（配套站）", "Princeton", "https://algs4.cs.princeton.edu/", "主课备选 · 代码与可视化最全"),
        ("CS 61B Data Structures", "UC Berkeley", "https://cs61b.org/", "备选 · 项目驱动，Java"),
        ("CS 161 Design and Analysis of Algorithms", "Stanford", "https://web.stanford.edu/class/cs161/", "备选 · 证明与复杂度理论更强"),
        ("CP-Algorithms", "社区维护", "https://cp-algorithms.com/", "参考 · 实现细节与模板"),
        ("15-122 Principles of Imperative Computation", "CMU（本地已有笔记）", "https://www.cs.cmu.edu/~15122-archive/f26/", "衔接 · 不变式与 C0/C"),
    ],
    books=[("《Introduction to Algorithms》(CLRS)", "查阅型工具书，不建议通读"),
           ("《Algorithms》Sedgewick", "配 algs4 站点"),
           ("《Algorithm Design Manual》Skiena", "偏实战选型")],
),
dict(
    key="40-计算机组成", name="计算机组成",
    tagline="一行代码在机器层面到底发生了什么。",
    questions=["数据在寄存器里长什么样？", "函数调用如何压栈？", "为什么这段循环快十倍？"],
    not_scope="不深入芯片物理与工艺；不替代体系结构研究（见 160）。",
    prereq=["20 编程基础", "二进制与基本的逻辑门直觉"],
    leads_to=["50 操作系统", "80 编译原理", "120 软件安全"],
    points=[
        ("数据表示", ["二进制与十六进制", "无符号与补码", "符号扩展与截断", "字节序（大端/小端）", "IEEE 754 浮点", "整数与浮点溢出"]),
        ("机器级程序", ["寄存器与调用约定", "寻址模式", "算术与逻辑指令", "条件码与跳转", "过程调用与栈帧", "数组与结构体的内存布局"]),
        ("链接与加载", ["目标文件与节", "符号解析", "静态链接与重定位", "动态链接与共享库", "位置无关代码"]),
        ("存储层次", ["寄存器/缓存/内存/磁盘的延迟阶梯", "局部性原理", "缓存映射与组相联", "缓存命中率与写策略", "TLB"]),
        ("处理器", ["指令流水线", "数据冒险与控制冒险", "分支预测", "乱序执行与超标量"]),
        ("虚拟内存", ["地址空间", "页表与多级页表", "缺页处理", "内存映射文件"]),
        ("并发硬件基础", ["原子指令", "内存序与屏障", "缓存一致性协议"]),
        ("性能", ["基准测试与测量方法", "Amdahl 定律", "perf 等剖析工具", "缓存友好代码改写"]),
    ],
    courses=[
        ("15-213 Introduction to Computer Systems", "CMU（本地已有笔记）", "https://www.cs.cmu.edu/~213/", "主课 · CSAPP 配套"),
        ("CS 61C Great Ideas in Computer Architecture", "UC Berkeley", "https://cs61c.org/", "主课备选 · 含 RISC-V"),
        ("Nand2Tetris", "nand2tetris.org", "https://www.nand2tetris.org/", "补课 · 从逻辑门造到 VM"),
        ("6.004 Computation Structures", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/6-004-computation-structures-spring-2017/", "备选 · 数字电路视角"),
        ("CS:APP 教材站", "CMU", "https://csapp.cs.cmu.edu/", "教材 · 官方配套资源"),
    ],
    books=[("《Computer Systems: A Programmer's Perspective》", "15-213 指定教材，第三版"),
           ("《Computer Organization and Design》", "Patterson & Hennessy，硬件视角")],
),
dict(
    key="50-操作系统", name="操作系统",
    tagline="多个程序如何安全、公平地共享同一台机器。",
    questions=["进程切换时到底保存了什么？", "两个线程为什么会互相卡死？", "内存不够时系统做了什么？"],
    not_scope="不深入内核某个子系统的实现细节（驱动、文件系统专项）；不替代分布式系统。",
    prereq=["40 计算机组成"],
    leads_to=["60 计算机网络", "110 后端开发", "140 分布式系统"],
    points=[
        ("进程与线程", ["进程控制块与状态机", "上下文切换的开销", "fork / exec / wait", "线程模型与用户态线程", "协程与调度"]),
        ("CPU 调度", ["FCFS / SJF / 优先级", "时间片轮转", "多级反馈队列", "优先级反转与继承", "实时调度"]),
        ("同步与并发", ["竞态条件", "互斥锁与自旋锁", "条件变量", "信号量", "管程/监视器", "读写锁", "死锁的四个必要条件", "死锁预防/避免/检测"]),
        ("内存管理", ["地址空间与重定位", "分页与分段", "多级页表", "页面置换（OPT/FIFO/LRU/Clock）", "工作集与抖动", "写时复制"]),
        ("文件系统", ["文件与目录抽象", "inode 与数据块", "硬链接与软链接", "日志与崩溃一致性", "页缓存与回写"]),
        ("I/O 与设备", ["中断与 DMA", "缓冲与设备驱动模型", "阻塞/非阻塞/异步 I/O"]),
        ("内核接口", ["用户态与内核态", "系统调用的实现路径", "信号", "权限位与 capabilities"]),
        ("隔离与虚拟化", ["namespace 与 cgroup", "容器与虚拟机的差别", "hypervisor 类型"]),
    ],
    courses=[
        ("6.S081 / 6.828 Operating System Engineering", "MIT", "https://pdos.csail.mit.edu/6.S081/2021/schedule.html", "主课 · xv6 实验，动手最扎实"),
        ("Operating Systems: Three Easy Pieces", "Wisconsin", "https://pages.cs.wisc.edu/~remzi/OSTEP/", "主课备选 · 免费教材，概念最清楚"),
        ("CS 162 Operating Systems", "UC Berkeley", "https://cs162.org/", "备选 · Pintos 项目"),
        ("15-410 Operating System Design and Implementation", "CMU", "https://www.cs.cmu.edu/~410/", "备选 · 难度高，Project 重"),
    ],
    books=[("《Operating Systems: Three Easy Pieces》", "免费在线，先读这本"),
           ("《xv6: a simple, Unix-like teaching operating system》", "配 6.S081，源码不到一万行")],
),
dict(
    key="60-计算机网络", name="计算机网络",
    tagline="两台机器之间如何可靠地把字节送过去。",
    questions=["一个包从浏览器到服务器经过哪些层？", "TCP 为什么需要三次握手？", "网络卡顿时该调什么？"],
    not_scope="不深入无线/光传输物理层；不替代分布式系统的一致性讨论。",
    prereq=["50 操作系统（socket、缓冲、阻塞）"],
    leads_to=["100 前端开发", "110 后端开发", "120 软件安全"],
    points=[
        ("分层与封装", ["OSI 与 TCP/IP 模型", "封装与解封装", "端到端原则", "协议头开销"]),
        ("链路层", ["以太网帧", "MAC 地址与 ARP", "交换机与学习", "VLAN"]),
        ("网络层", ["IPv4 地址与子网划分", "CIDR", "路由表与最长前缀匹配", "距离向量与链路状态路由", "NAT", "ICMP", "IPv6"]),
        ("传输层", ["UDP 与无连接语义", "TCP 三次握手与四次挥手", "序号、确认与重传", "滑动窗口与流量控制", "拥塞控制（Reno/CUBIC/BBR）", "粘包与拆包"]),
        ("应用层", ["HTTP/1.1 与持久连接", "HTTP/2 多路复用", "HTTP/3 与 QUIC", "DNS 解析链路", "TLS 握手与证书链", "WebSocket", "gRPC 与 protobuf"]),
        ("套接字编程", ["listen/accept/connect", "阻塞与非阻塞", "select / poll / epoll", "缓冲区与背压"]),
        ("性能", ["RTT 与带宽时延积", "队头阻塞", "连接池与长连接", "CDN 与边缘缓存"]),
    ],
    courses=[
        ("CS 144 Introduction to Computer Networking", "Stanford", "https://cs144.github.io/", "主课 · 从零实现 TCP"),
        ("Computer Networking: A Top-Down Approach（配套站）", "UMass / Kurose & Ross", "https://gaia.cs.umass.edu/kurose_ross/index.php", "主课备选 · 自顶向下，概念清晰"),
        ("15-441 Computer Networks", "CMU", "https://computer-networks.github.io/fa20/", "备选 · 更偏系统实现"),
    ],
    books=[("《Computer Networking: A Top-Down Approach》", "Kurose & Ross"),
           ("《TCP/IP Illustrated, Vol.1》", "Stevens，查细节用")],
),
dict(
    key="70-数据库", name="数据库",
    tagline="数据如何持久化、并发地被查询与修改。",
    questions=["一条 SQL 在引擎里怎么执行？", "索引为什么能让查询快两个数量级？", "两个事务同时改同一行会发生什么？"],
    not_scope="不深入某个商业数据库的运维参数调优；不替代数据分析/数仓建模。",
    prereq=["30 数据结构与算法（B+ 树、哈希）", "50 操作系统（页、缓冲）"],
    leads_to=["110 后端开发", "140 分布式系统", "150 系统架构"],
    points=[
        ("关系模型", ["关系与元组", "主键/外键/唯一约束", "关系代数", "范式与反范式"]),
        ("SQL", ["DDL 与 DML", "各类 JOIN", "聚合与 GROUP BY", "子查询与 CTE", "窗口函数", "事务控制语句", "执行计划 EXPLAIN"]),
        ("存储引擎", ["页的组织", "行存与列存", "缓冲池", "空闲空间管理", "元组布局与变长字段"]),
        ("索引", ["B+ 树索引", "哈希索引", "复合索引与最左前缀", "覆盖索引", "索引选择性", "索引维护代价"]),
        ("查询执行", ["顺序扫描与索引扫描", "连接算法（嵌套循环/哈希/归并）", "排序与聚合", "谓词下推"]),
        ("查询优化", ["代价模型", "统计信息与基数估计", "连接顺序选择"]),
        ("事务", ["ACID", "隔离级别与异常现象", "MVCC", "锁与意向锁", "幻读与间隙锁"]),
        ("日志与恢复", ["WAL", "ARIES 三阶段", "检查点", "崩溃恢复流程"]),
        ("分布式数据库", ["分片", "复制与读写分离", "分布式事务 2PC", "一致性取舍"]),
        ("NoSQL", ["键值/文档/列族/图", "CAP 与 BASE", "何时不该用关系库"]),
    ],
    courses=[
        ("15-445 Database Systems", "CMU（本地已有笔记）", "https://15445.courses.cs.cmu.edu/fall2026/", "主课 · 讲引擎实现，C++17"),
        ("CS 186 Introduction to Database Systems", "UC Berkeley", "https://cs186berkeley.net/", "主课备选 · 偏使用与优化"),
        ("Database System Concepts（配套站）", "Silberschatz 等", "https://db-book.com/", "教材 · 理论最全"),
        ("PostgreSQL Documentation", "PostgreSQL", "https://www.postgresql.org/docs/", "官方文档 · 实现细节参考"),
        ("SQLite Documentation", "SQLite", "https://www.sqlite.org/docs.html", "官方文档 · 最小可读的引擎实现说明"),
    ],
    books=[("《Database System Concepts》", "Silberschatz，理论"),
           ("《Database Internals》", "Petrov，存储引擎与分布式"),
           ("《Designing Data-Intensive Applications》", "Kleppmann，选型与权衡")],
),
dict(
    key="80-编译原理", name="编译原理",
    tagline="文本如何变成可执行的语义。",
    questions=["一段源码怎样被切成 token？", "语法树如何构造？", "优化器凭什么敢改你的代码？"],
    not_scope="不追求某语言完整前端实现；不替代程序语言理论（见 160）。",
    prereq=["30 数据结构与算法（树、图、哈希）", "40 计算机组成（寄存器、指令）"],
    leads_to=["90 软件工程", "160 计算机高级选修"],
    points=[
        ("词法分析", ["正则表达式", "NFA 与 DFA", "子集构造", "手写词法分析器", "词法分析器生成器"]),
        ("语法分析", ["上下文无关文法", "推导与语法树", "递归下降", "LL(1) 与 FIRST/FOLLOW", "LR(0)/SLR/LALR", "错误恢复"]),
        ("语义分析", ["符号表", "作用域与名字解析", "类型检查", "类型推断（Hindley-Milner 直觉）", "类型转换"]),
        ("中间表示", ["三地址码", "SSA 形式", "控制流图", "基本块"]),
        ("优化", ["常量折叠与传播", "死代码消除", "公共子表达式", "内联", "循环不变量外提", "寄存器分配与图着色"]),
        ("代码生成", ["指令选择", "栈式与寄存器式目标", "调用约定与栈帧布局"]),
        ("运行时系统", ["栈帧与闭包表示", "垃圾回收（标记清除/复制/分代）", "异常展开"]),
        ("解释器与虚拟机", ["字节码设计", "树遍历解释器", "JIT 基本思路"]),
    ],
    courses=[
        ("CS 143 Compilers", "Stanford", "https://web.stanford.edu/class/cs143/", "主课 · Cool 语言完整编译器"),
        ("Crafting Interpreters", "Robert Nystrom", "https://craftinginterpreters.com/", "主课备选 · 手写两遍解释器，最适合自学"),
        ("Kaleidoscope: Implementing a Language with LLVM", "LLVM", "https://llvm.org/docs/tutorial/", "实践 · 用 LLVM 做后端"),
        ("15-411 Compiler Design", "CMU", "https://www.cs.cmu.edu/~fp/courses/15411-f08/", "备选 · 版本较旧，实验设计仍可参考"),
    ],
    books=[("《Compilers: Principles, Techniques, and Tools》（龙书）", "体系完整，偏重"),
           ("《Engineering a Compiler》", "Cooper & Torczon，工程视角"),
           ("《Crafting Interpreters》", "免费在线，先读这本")],
),
dict(
    key="90-软件工程", name="软件工程",
    tagline="多人长期维护的代码，如何不腐化。",
    questions=["如何设计一个三个月后还看得懂的结构？", "测试要写到什么程度才够？", "如何安全地改一段不熟悉的代码？"],
    not_scope="不教具体语言语法；不替代项目管理与组织行为学。",
    prereq=["20 编程基础", "至少一个完整项目的经验"],
    leads_to=["100 前端开发", "110 后端开发", "150 系统架构"],
    points=[
        ("需求与规格", ["用户故事与用例", "验收标准", "前置/后置条件与不变式", "规格与实现的分离"]),
        ("设计原则", ["封装与信息隐藏", "抽象与模块化", "单一职责/开闭/里氏替换/接口隔离/依赖倒置", "耦合与内聚", "组合优于继承"]),
        ("设计模式", ["工厂与建造者", "适配器与装饰器", "策略与模板方法", "观察者", "单例的问题"]),
        ("测试", ["单元/集成/端到端", "等价类与边界值", "测试替身（mock/stub）", "覆盖率与其局限", "属性测试", "回归测试"]),
        ("协作", ["分支策略", "代码评审关注点", "提交信息规范", "冲突解决", "代码所有权"]),
        ("构建与依赖", ["构建系统", "语义化版本", "依赖冲突与锁定"]),
        ("重构", ["代码坏味道", "提取函数/类", "消除重复", "遗留代码的接缝"]),
        ("质量保障", ["静态分析与 lint", "CI 门禁", "技术债的记录与偿还"]),
        ("过程", ["敏捷与迭代", "估算", "文档的取舍", "复盘"]),
    ],
    courses=[
        ("15-214 Principles of Software Construction", "CMU（Fall 2013，本地已有笔记）", "https://www.cs.cmu.edu/~aldrich/214/", "主课 · 注意资料年代为 2013"),
        ("6.031 Software Construction", "MIT", "https://web.mit.edu/6.031/www/sp21/", "主课备选 · 规格与不变式讲得最清楚"),
        ("Google Engineering Practices", "Google", "https://google.github.io/eng-practices/", "实践 · code review 标准"),
        ("Martin Fowler 站点", "Martin Fowler", "https://martinfowler.com/", "参考 · 重构与架构随笔"),
        ("Refactoring Guru · Design Patterns", "Refactoring Guru", "https://refactoring.guru/design-patterns", "参考 · 模式图解"),
    ],
    books=[("《Code Complete》", "构造层面的实践手册"),
           ("《Refactoring》", "Martin Fowler，第二版"),
           ("《A Philosophy of Software Design》", "Ousterhout，复杂度视角，篇幅短")],
),
dict(
    key="100-前端开发", name="前端开发",
    tagline="界面如何被构建、渲染、交互。",
    questions=["浏览器从收到 HTML 到画出像素做了什么？", "状态变了界面为什么没更新？", "首屏为什么慢？"],
    not_scope="不深入某框架内部源码；不替代视觉设计与交互设计。",
    prereq=["20 编程基础", "60 计算机网络（HTTP、缓存、CORS）"],
    leads_to=["120 软件安全", "150 系统架构"],
    points=[
        ("HTML", ["语义化标签", "表单与校验", "可访问性（ARIA、键盘导航）", "文档元信息"]),
        ("CSS", ["盒模型", "层叠、继承与优先级", "Flexbox", "Grid", "响应式与媒体查询", "CSS 变量", "过渡与动画"]),
        ("JavaScript", ["类型与隐式转换", "作用域、闭包与 this", "原型链与 class", "事件循环与微任务", "Promise 与 async/await", "模块系统"]),
        ("浏览器运行时", ["渲染流水线（解析/样式/布局/绘制/合成）", "重排与重绘", "DOM 与事件模型", "事件委托", "Web Storage 与 IndexedDB"]),
        ("框架", ["组件化与 props/state", "单向数据流", "副作用与生命周期", "路由", "状态管理何时需要"]),
        ("构建工具", ["打包器与模块解析", "转译与 polyfill", "HMR", "tree-shaking 与代码分割"]),
        ("工程化", ["TypeScript 类型系统", "lint 与格式化", "单元测试与端到端测试", "性能指标 LCP/CLS/INP"]),
        ("网络与安全", ["HTTP 缓存策略", "CORS", "Cookie 属性（HttpOnly/SameSite）", "XSS 与 CSP", "Service Worker"]),
    ],
    courses=[
        ("MDN Web Docs", "Mozilla", "https://developer.mozilla.org/zh-CN/", "主课 · 唯一权威参考，中文可用"),
        ("web.dev", "Google", "https://web.dev/", "主课备选 · 性能与最佳实践"),
        ("javascript.info", "javascript.info", "https://javascript.info/", "教材 · 语言机制讲得最透"),
        ("React 官方文档", "Meta", "https://react.dev/", "官方文档 · 以文档当教材"),
        ("Vue 官方文档（中文）", "Vue.js", "https://cn.vuejs.org/", "官方文档 · 中文质量高"),
        ("TypeScript Handbook", "Microsoft", "https://www.typescriptlang.org/docs/handbook/intro.html", "官方文档 · 类型系统"),
    ],
    books=[("《Eloquent JavaScript》", "免费在线，语言基础"),
           ("《CSS: The Definitive Guide》", "CSS 系统参考")],
),
dict(
    key="110-后端开发", name="后端开发",
    tagline="服务如何承载业务、连接存储、对外提供 API。",
    questions=["一个请求在服务内部经过哪些环节？", "并发上来后哪里先崩？", "接口出错时如何让调用方正确处理？"],
    not_scope="不绑定某一语言生态；不替代数据库内核与分布式共识。",
    prereq=["50 操作系统", "60 计算机网络", "70 数据库"],
    leads_to=["120 软件安全", "130 DevOps与运维", "150 系统架构"],
    points=[
        ("HTTP 服务", ["路由与中间件", "请求生命周期", "状态码语义", "内容协商", "超时与重试"]),
        ("API 设计", ["REST 资源建模", "GraphQL", "gRPC", "版本化策略", "错误模型", "幂等性设计", "分页与过滤"]),
        ("数据访问", ["ORM 与原生 SQL 的取舍", "连接池", "N+1 查询", "事务边界", "乐观锁与悲观锁"]),
        ("认证与授权", ["Session 与 Cookie", "JWT 与其缺陷", "OAuth2 流程", "RBAC/ABAC"]),
        ("并发模型", ["线程池", "事件循环", "协程", "背压与限流"]),
        ("缓存", ["本地缓存与分布式缓存", "失效策略", "缓存穿透/击穿/雪崩", "缓存一致性"]),
        ("异步与消息", ["消息队列模型", "投递语义", "幂等消费", "死信与重试"]),
        ("可观测性", ["结构化日志", "指标与直方图", "链路追踪", "健康检查"]),
        ("部署形态", ["单体", "模块化单体", "微服务与它的代价"]),
    ],
    courses=[
        ("6.033 Computer System Engineering", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/6-033-computer-system-engineering-spring-2018/", "主课 · 系统设计视角，非框架课"),
        ("The Twelve-Factor App（中文）", "12factor.net", "https://12factor.net/zh_cn/", "实践 · 服务化十二条"),
        ("Node.js Documentation", "Node.js", "https://nodejs.org/docs/latest/api/", "官方文档 · 事件循环与流"),
        ("Spring Guides", "VMware", "https://spring.io/guides", "官方文档 · Java 生态入门"),
        ("FastAPI Documentation", "FastAPI", "https://fastapi.tiangolo.com/", "官方文档 · Python 现代框架"),
    ],
    books=[("《Designing Data-Intensive Applications》", "Kleppmann，后端选型的底层依据"),
           ("《Release It!》", "稳定性模式：熔断、舱壁、超时")],
),
dict(
    key="120-软件安全", name="软件安全",
    tagline="对手存在时，系统如何仍然正确。",
    questions=["攻击者会从哪里进来？", "这个输入为什么能变成代码执行？", "如何证明我没漏掉一整类漏洞？"],
    not_scope="不做渗透测试的社工与物理入侵；不替代合规审计。",
    prereq=["40 计算机组成", "50 操作系统", "60 计算机网络"],
    leads_to=["130 DevOps与运维"],
    points=[
        ("威胁建模", ["攻击面枚举", "STRIDE", "信任边界", "数据流图"]),
        ("Web 漏洞", ["SQL 注入与参数化", "XSS（存储/反射/DOM）", "CSRF 与 SameSite", "SSRF", "越权（水平/垂直）", "文件上传", "反序列化", "路径穿越"]),
        ("密码学应用", ["哈希与加盐", "对称与非对称加密", "TLS 与证书验证", "密钥管理", "常见误用"]),
        ("内存安全", ["缓冲区溢出", "释放后使用", "整数溢出", "格式化字符串", "缓解措施（ASLR/DEP/Canary）"]),
        ("认证与会话", ["密码存储", "多因素认证", "会话固定与轮换", "OAuth 常见坑"]),
        ("供应链", ["依赖漏洞", "SBOM", "构建产物签名", "typosquatting"]),
        ("安全开发", ["安全编码规范", "SAST/DAST", "模糊测试", "安全评审清单"]),
        ("漏洞管理", ["CVE/CWE", "负责任披露", "补丁与回归"]),
    ],
    courses=[
        ("OWASP Top 10", "OWASP", "https://owasp.org/www-project-top-ten/", "主课 · Web 风险清单"),
        ("SEED Labs", "Syracuse University", "https://seedsecuritylabs.org/", "主课备选 · 动手实验最完整"),
        ("PortSwigger Web Security Academy", "PortSwigger", "https://portswigger.net/web-security", "实践 · 免费靶场+讲解"),
        ("6.858 Computer Systems Security", "MIT", "https://css.csail.mit.edu/6.858/", "备选 · 系统安全，含论文阅读"),
        ("CWE", "MITRE", "https://cwe.mitre.org/", "参考 · 弱点分类字典"),
    ],
    books=[("《Security Engineering》", "Ross Anderson，免费在线，第三版"),
           ("《The Web Application Hacker's Handbook》", "Web 攻防经典（年代较早，原理仍有效）")],
),
dict(
    key="130-DevOps与运维", name="DevOps与运维",
    tagline="代码如何稳定、可重复地到达生产环境。",
    questions=["如何做到一次构建、处处运行？", "上线出问题时如何三分钟内回滚？", "系统慢了，从哪一层开始查？"],
    not_scope="不做云厂商认证题库；不替代安全合规。",
    prereq=["50 操作系统（Linux）", "60 计算机网络", "110 后端开发"],
    leads_to=["150 系统架构"],
    points=[
        ("Linux 运维", ["进程与信号", "权限与用户", "systemd 服务", "日志（journald/rsyslog）", "磁盘与文件系统", "网络排查（ip/ss/tcpdump/curl）"]),
        ("Shell 与脚本", ["管道与重定向", "变量与引用", "错误处理与 set -e", "常用文本处理"]),
        ("版本与发布", ["Git 工作流", "tag 与 release", "变更日志"]),
        ("持续集成", ["流水线阶段划分", "缓存与并行", "矩阵构建", "制品管理"]),
        ("持续部署", ["蓝绿部署", "金丝雀发布", "滚动更新", "回滚策略"]),
        ("容器", ["镜像分层", "Dockerfile 最佳实践", "多阶段构建", "网络与卷"]),
        ("编排", ["Pod/Deployment/Service/Ingress", "配置与密钥", "健康探针", "水平扩缩容"]),
        ("基础设施即代码", ["声明式与命令式", "Terraform 状态", "不可变基础设施"]),
        ("可观测性", ["指标与 Prometheus", "日志聚合", "分布式追踪", "SLO/SLI/错误预算", "告警设计"]),
        ("事故响应", ["on-call 轮值", "故障分级", "复盘模板（无指责）"]),
    ],
    courses=[
        ("Site Reliability Engineering", "Google", "https://sre.google/sre-book/table-of-contents/", "主课 · SRE 方法论原典，免费在线"),
        ("Docker Documentation", "Docker", "https://docs.docker.com/", "官方文档 · 容器基础"),
        ("Kubernetes Documentation", "CNCF", "https://kubernetes.io/docs/home/", "官方文档 · 编排"),
        ("GitHub Actions Documentation", "GitHub", "https://docs.github.com/en/actions", "官方文档 · CI/CD"),
        ("The Linux Command Line（TLCL）", "William Shotts", "https://linuxcommand.org/tlcl.php", "教材 · 命令行基础，免费 PDF"),
    ],
    books=[("《Site Reliability Engineering》", "Google，免费在线"),
           ("《The Phoenix Project》", "交付流程的小说化入门"),
           ("《Accelerate》", "DORA 四项指标的实证依据")],
),
dict(
    key="140-分布式系统", name="分布式系统",
    tagline="多台机器如何表现得像一台。",
    questions=["网络分区时，系统该牺牲什么？", "两个节点如何就一个值达成一致？", "为什么「最终一致」经常不最终？"],
    not_scope="不做特定中间件的运维调参；不替代共识算法的形式化证明。",
    prereq=["50 操作系统", "60 计算机网络", "70 数据库"],
    leads_to=["150 系统架构"],
    points=[
        ("基础模型", ["部分失败", "不可靠网络与超时", "时钟漂移与逻辑时钟", "同步 vs 异步系统假设"]),
        ("复制", ["主从复制", "多主复制", "无主复制", "复制日志与状态机复制", "复制延迟与读己之写"]),
        ("一致性模型", ["线性一致性", "顺序一致性", "因果一致性", "最终一致", "会话保证"]),
        ("共识", ["FLP 结论的直觉", "Paxos", "Raft（选举/日志复制/成员变更）", "法定人数与脑裂"]),
        ("分区", ["分片键选择", "再平衡", "热点与倾斜", "请求路由"]),
        ("分布式事务", ["2PC 与 3PC", "Saga", "补偿事务", "幂等与去重"]),
        ("容错", ["故障检测器", "租约", "副本修复", "反熵"]),
        ("分布式计算", ["MapReduce 模型", "批处理与流处理", "恰好一次语义的实现代价"]),
        ("实践系统", ["etcd / ZooKeeper", "Kafka 的分区与消费组", "对象存储的一致性"]),
    ],
    courses=[
        ("6.824 Distributed Systems", "MIT", "https://pdos.csail.mit.edu/6.824/", "主课 · Lab 实现 Raft/KV"),
        ("Raft 共识算法", "raft.github.io", "https://raft.github.io/", "主课备选 · 论文+可视化+实现"),
        ("Jepsen", "Jepsen", "https://jepsen.io/", "参考 · 真实系统的一致性缺陷分析"),
        ("15-440 Distributed Systems", "CMU", "https://www.cs.cmu.edu/~440/", "备选 · 课程页可能随学期变化"),
    ],
    books=[("《Designing Data-Intensive Applications》", "Kleppmann，本领域第一本书"),
           ("《Distributed Systems》", "van Steen & Tanenbaum，免费在线教材")],
),
dict(
    key="150-系统架构", name="系统架构",
    tagline="在约束下做技术选型与权衡——它不引入新知识，只做取舍。",
    questions=["这个设计牺牲了什么换来了什么？", "流量涨十倍，哪一层先断？", "什么时候不该上微服务？"],
    not_scope="不提供「正确答案」；不替代具体领域的实现能力。没有 50/60/70/110/140 的基础，本领域只会剩下名词。",
    prereq=["50 操作系统", "60 计算机网络", "70 数据库", "110 后端开发", "140 分布式系统"],
    leads_to=["（汇聚层，无后继）"],
    points=[
        ("架构决策", ["质量属性：性能/可用性/可维护性/成本", "权衡记录 ADR", "约束识别"]),
        ("架构风格", ["分层", "六边形/端口适配器", "事件驱动", "CQRS", "微服务与模块化单体", "Serverless"]),
        ("伸缩性", ["无状态化", "水平扩展", "读写分离", "分片", "异步化削峰"]),
        ("可用性", ["冗余与多副本", "故障隔离（舱壁）", "熔断", "限流", "降级", "重试与指数退避"]),
        ("数据架构", ["一致性与可用性的取舍", "数据所有权", "事件溯源", "读写模型分离"]),
        ("集成", ["同步调用 vs 异步消息", "契约与版本兼容", "幂等设计"]),
        ("演进", ["绞杀者模式", "渐进迁移", "双写与对账"]),
        ("评审", ["容量规划", "成本模型", "架构评审清单", "技术债登记"]),
    ],
    courses=[
        ("System Design Primer", "donnemartin（GitHub）", "https://github.com/donnemartin/system-design-primer", "主课 · 面试与入门框架"),
        ("AWS Well-Architected Framework", "Amazon Web Services", "https://aws.amazon.com/architecture/well-architected/", "主课备选 · 六大支柱的检查清单"),
        ("Azure Architecture Center", "Microsoft", "https://learn.microsoft.com/en-us/azure/architecture/", "参考 · 模式目录（Cloud Design Patterns）"),
        ("The Twelve-Factor App", "12factor.net", "https://12factor.net/", "参考 · 服务化基线"),
    ],
    books=[("《Designing Data-Intensive Applications》", "先读完这本再谈架构"),
           ("《Software Architecture: The Hard Parts》", "权衡与拆分决策"),
           ("《Building Evolutionary Architectures》", "适应度函数与演进")],
),
dict(
    key="160-计算机高级选修", name="计算机高级选修",
    tagline="在主干之上选一个专门方向深入。",
    questions=["我该往 AI、系统、图形还是 PL 走？", "这个方向的前置到底缺什么？", "如何判断一门课值不值得投入三个月？"],
    not_scope="本领域是方向索引，不为每个方向提供完整知识点清单；选定方向后应另建子目录。",
    prereq=["10 数学基础", "30 数据结构与算法"],
    leads_to=["150 系统架构"],
    points=[
        ("人工智能 / 机器学习", ["监督与无监督学习", "损失函数与梯度下降", "过拟合与正则化", "偏差-方差分解", "模型评估与交叉验证", "集成方法"]),
        ("深度学习", ["反向传播", "CNN 与感受野", "RNN/LSTM", "注意力与 Transformer", "训练技巧（归一化/学习率调度）", "迁移学习"]),
        ("计算机图形学", ["光栅化管线", "几何变换与投影", "光照模型与 BRDF", "着色器编程", "光线追踪", "纹理与采样"]),
        ("并行与高性能计算", ["SIMD", "多线程与任务并行", "GPU 编程模型", "缓存与内存带宽瓶颈", "性能建模（Roofline）"]),
        ("程序语言理论", ["λ 演算", "操作语义与小步语义", "类型系统与类型安全性", "多态", "类型推断"]),
        ("计算理论", ["有限自动机", "正则语言与泵引理", "上下文无关语言", "可判定性与停机问题", "复杂度类 P/NP/PSPACE"]),
        ("密码学", ["对称加密与分组模式", "公钥加密", "哈希与 MAC", "零知识证明入门"]),
        ("人机交互", ["可用性评估", "用户研究方法", "原型设计"]),
    ],
    courses=[
        ("CS 229 Machine Learning", "Stanford", "https://cs229.stanford.edu/", "方向 · 机器学习，数学要求高"),
        ("CS 231N Deep Learning for Computer Vision", "Stanford", "https://cs231n.stanford.edu/", "方向 · 视觉"),
        ("CS 224N NLP with Deep Learning", "Stanford", "https://web.stanford.edu/class/cs224n/", "方向 · 自然语言处理"),
        ("15-462 Computer Graphics", "CMU", "https://15462.courses.cs.cmu.edu/", "方向 · 图形学，作业强度大"),
        ("15-418 Parallel Computer Architecture", "CMU", "https://www.cs.cmu.edu/~418/", "方向 · 并行与性能"),
        ("15-312 Foundations of Programming Languages", "CMU", "https://www.cs.cmu.edu/~crary/312/", "方向 · 程序语言理论"),
        ("CS 285 Deep Reinforcement Learning", "UC Berkeley", "https://rail.eecs.berkeley.edu/deeprlcourse/", "方向 · 强化学习"),
    ],
    books=[("《Pattern Recognition and Machine Learning》", "Bishop，ML 理论"),
           ("《Deep Learning》", "Goodfellow 等，免费在线"),
           ("《Real-Time Rendering》", "图形学参考")],
),
]


def load_url_status() -> dict[str, dict]:
    if not os.path.exists(URLCHECK):
        return {}
    with open(URLCHECK, encoding="utf-8") as f:
        data = json.load(f)
    return {r["url"]: r for r in data.get("results", [])}


def render_overview(d: dict) -> str:
    q = "\n".join(f"- {x}" for x in d["questions"])
    pre = "、".join(d["prereq"])
    nxt = "、".join(d["leads_to"])
    return f"""# {d['name']} · 领域总览

> **一句话**：{d['tagline']}

## 这个领域回答的问题

{q}

## 边界：它不负责什么

{d['not_scope']}

## 前置与后继

| | |
| --- | --- |
| **学之前最好已掌握** | {pre} |
| **学完之后支撑** | {nxt} |

## 学完应该能做到

1. 用本领域的术语准确描述一个具体问题，而不是用「感觉慢」「好像有问题」。
2. 拿到一个陌生系统，能判断它在本领域的哪一层、瓶颈可能在哪里。
3. 读得懂本领域的经典教材章节与官方文档，不需要先看二手解读。

## 目录

- [01-知识点目录](01-知识点目录.md)
- [02-权威课程与资料](02-权威课程与资料.md)

## 回到

- [计算机科学知识地图](../00-知识地图.md)
- [学习路径与排期](../01-学习路径.md)
"""


def render_points(d: dict) -> str:
    lines = [f"# {d['name']} · 知识点目录", "",
             "> 条目粒度是「能独立讲清的一个概念」。勾选表示**能不看资料讲出来并举例**，",
             "> 不是「看过」。未勾选但学过的，在条目下方补一行「卡在哪」。", ""]
    total = 0
    for group, items in d["points"]:
        lines.append(f"## {group}")
        lines.append("")
        for it in items:
            lines.append(f"- [ ] {it}")
            total += 1
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"共 {total} 个知识点，分 {len(d['points'])} 组。")
    lines.append("")
    lines.append("## 自测方式")
    lines.append("")
    lines.append("随机抽 5 个已勾选条目，向一个没学过的人解释；解释不清的把勾去掉。")
    lines.append("")
    lines.append("## 回到")
    lines.append("")
    lines.append("- [00-领域总览](00-领域总览.md)")
    lines.append("- [02-权威课程与资料](02-权威课程与资料.md)")
    return "\n".join(lines) + "\n"


def render_courses(d: dict, status: dict[str, dict]) -> str:
    lines = [f"# {d['name']} · 权威课程与资料", "",
             "> 链接可达性由 `scripts/verify_urls.py` 实测，原始结果见 `sources/_url-check.json`。",
             "> 「⚠ 本机网络不可达」表示本机到该站点的网络不通（DNS/连接失败），**不代表网址失效**，换网络环境再试。",
             "> 「⚠ 待核实」的条目未通过自动核验，引用前请自行确认；不要把它当成可用来源。", "",
             "## 一、大学课程与公开课", "",
             "| 课程 | 机构 | 定位 | 链接 |", "| --- | --- | --- | --- |"]
    suspicious = 0
    for name, org, url, note in d["courses"]:
        st = status.get(url)
        if st is None:
            link = f"[{url}]({url}) ⚠ 待核实"
            suspicious += 1
        elif st.get("reachable"):
            link = f"[{url}]({url})"
        elif st.get("status") == "ERR":
            link = f"[{url}]({url}) ⚠ 本机网络不可达"
            suspicious += 1
        else:
            link = f"[{url}]({url}) ⚠ 待核实（HTTP {st.get('status')}）"
            suspicious += 1
        lines.append(f"| {name} | {org} | {note} | {link} |")
    lines += ["", "## 二、教材与参考书", "", "| 书名 | 说明 |", "| --- | --- |"]
    for b, note in d["books"]:
        lines.append(f"| {b} | {note} |")
    lines += ["", "## 三、怎么用这份清单", "",
              "1. **只选一门主课**。「主课」那一行是建议首选；同时开两门同类课是常见的时间黑洞。",
              "2. **教材用来查，不用来读**。除非主课没有配套讲义，否则不要从第一页读教材。",
              "3. **官方文档优先于二手教程**。文档更新更快，且不会漏掉版本差异。",
              "4. **链接失效时**：先在 `sources/00-资料来源总览.md` 查是否有镜像或存档记录，再决定是否替换。", ""]
    if suspicious:
        lines.append(f"> 本页有 {suspicious} 条链接未通过自动核验，已标注 ⚠。")
        lines.append("")
    lines += ["## 回到", "", "- [00-领域总览](00-领域总览.md)", "- [01-知识点目录](01-知识点目录.md)"]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="覆盖本脚本生成的三个文件（只限 00/01/02 这三个名字）")
    args = ap.parse_args()

    status = load_url_status()
    print(f"URL 核验记录：{len(status)} 条" if status else "URL 核验记录：未找到（所有链接将标注待核实）")

    created = skipped = 0
    for d in DOMAINS:
        outdir = os.path.join(DOCS, d["key"])
        files = {
            "00-领域总览.md": render_overview(d),
            "01-知识点目录.md": render_points(d),
            "02-权威课程与资料.md": render_courses(d, status),
        }
        if not args.dry_run:
            os.makedirs(outdir, exist_ok=True)
        for fname, content in files.items():
            path = os.path.join(outdir, fname)
            if os.path.exists(path) and not args.force:
                print(f"SKIP {d['key']}/{fname}（已存在，不覆盖）")
                skipped += 1
                continue
            if args.dry_run:
                print(f"WOULD CREATE {d['key']}/{fname}")
            else:
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(content)
                print(f"{'UPDATE' if os.path.exists(path) else 'CREATE'} {d['key']}/{fname}")
            created += 1

    print(f"\n写入 {created} 个文件，跳过 {skipped} 个已存在文件。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
