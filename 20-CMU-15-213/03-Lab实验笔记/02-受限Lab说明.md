---
course: CMU 15-213
course_name: Introduction to Computer Systems
semester: Fall 2026
lecture_id: lab-restricted
topic: 受限 Lab 说明与替代学习路径
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-213
  - Lab
  - 受限材料
  - 替代路径
---

# CMU 15-213 · 受限 Lab 说明（Restricted Labs）

> Lab 总览见 [[20-CMU-15-213/03-Lab实验笔记/00-Lab总览|15-213 Lab 总览]]，唯一公开的 lab 见 [[20-CMU-15-213/03-Lab实验笔记/01-CProgrammingLab笔记|CProgrammingLab 笔记]]。
>
> **本页的立场**：以下 lab 的题目包、起始代码、测试用例**都是 CMU 课程的内部材料**，通过 Autolab 与 GitHub Classroom 发放给**已选课学生**。本知识库**不提供、也不寻求**这些材料的任何非官方副本，**不尝试绕过任何访问控制**。本页只做三件事：说清它们为什么拿不到、它们各自考什么、以及在没有课程权限的前提下如何用公开资源达到同等的学习效果。

---

## 1. 本节学习目标

学完本页，你应当能够：

1. **解释** Autolab + GitHub Classroom 的分发链路，并说出三个层面（技术 / 规则 / 实际）上「为什么拿不到」。
2. **复述** L1–L6 每个 lab 考什么、依赖哪几讲讲义、以及公开讲义对它的知识覆盖度。
3. **判断** 在没有官方题目包的情况下，哪个 lab 最值得自学（以及为什么是 L5）。
4. **设计** 一个不依赖官方测试框架的自测方案：自己出题、自己造 trace、自己算指标。
5. **区分**「使用公开的教材与讲义」与「使用泄漏的题解」这条界线在哪里，并说明为什么前者足够。

---

## 2. 前置知识

- 先读 [[20-CMU-15-213/03-Lab实验笔记/00-Lab总览|15-213 Lab 总览]]（8 个 lab 的日期、获取方式、评分机制）。
- 需要具备的课程知识：L02（位运算）、L03–L06（汇编）、L09–L10（缓存）、L11–L14（虚拟内存与 malloc）、L16–L18（进程、信号、I/O）。
- 外部概念：`git`（GitHub Classroom 的提交方式）、`ssh`、`make`。
- 相关页面：[[20-CMU-15-213/01-课程目录|CMU 15-213 - 课程目录]]、[[20-CMU-15-213/04-学习进度|CMU 15-213 - 学习进度]]。

---

## 3. 核心概念

- **Autolab（自动评分平台）**：CMU 的作业提交与评分系统，`https://autolab.andrew.cmu.edu/courses/15213-f26`。需 **Andrew ID + Shibboleth** 认证，且**必须已选课**（Autolab 与 Hub 名单每天同步一次，`01-overview.pdf` 第 64 页）。
- **GitHub Classroom（GitHub 课堂）**：L4 起的分发方式。每个学生一个**私有仓库**，邀请须 **7 天内**接受（否则扣 10%），学期结束后**仓库被删除**（syllabus §6.2）。
- **Starter code（起始代码）**：lab 的骨架文件，只通过 `autolab download` 发放。缺了它就没有可编译的工程。
- **Personalized binary（个性化二进制）**：L2 Bomb Lab 与 L3 Attack Lab 的可执行文件**按学号生成**，每个学生的炸弹 / 靶子都不同。这是「即使拿到别人的代码也没用」的技术原因。
- **Trace（追踪文件）**：L4 / L5 / L6 的评分输入。L4 是访存序列，L5 是 malloc/free 序列，L6 是 shell 命令脚本。**不公开**，所以无法复现官方评分。
- **Specification（规格）**：lab 的**行为契约**——命令行参数、输出格式、性能指标定义。**规格是公开的**（讲义里写得很清楚），实现是你自己的。
- **Academic integrity（学术诚信）**：syllabus §6.7 禁止使用未经授权的资料（含 AI 工具）。`cprogramminglab.pdf` 第 2 页点名举例：「linked-list implementation in C」这类搜索都是越界的。

---

## 4. 通俗理解

把 lab 想成**驾校的路考**：

- **起始代码**是教练车。没有车你没法练。
- **个性化二进制**（L2 / L3）是「你的考试路线」——每个学员的路线不一样，抄别人的路线没用。
- **Trace** 是考官的评分表。你知道考什么（倒车入库、坡道起步），但不知道考官具体用哪几条路线打分。
- **规格**是交通法规——**完全公开**，而且你真正要学会的就是它。

所以「拿不到路考评分表」不等于「学不会开车」。你可以按法规自己找场地练：倒车入库的距离标准是公开的，你自己拿桩桶摆一个就行。**这就是本页说的「按规格自己实现」**。

一个具体对比：L5 Malloc Lab 的规格是「实现 `mm_malloc` / `mm_free` / `mm_realloc`，在吞吐量与利用率之间取平衡」。这句话在 `13-malloc-basic.pdf` 与 `14-malloc-advanced.pdf` 里被拆成了 101 页的完整设计文档——**包括伪代码**。你缺的只是那 15 条评分 trace，不缺任何知识。

---

## 5. 原理与推导

### 5.1 发放链路

```
CMU 选课系统（SIO / roster）
        │
        ▼
   Autolab 账号（https://autolab.andrew.cmu.edu）
        │   ← 需要 Andrew ID + Shibboleth 认证
        ▼
   autolab download 15213-f26:<labname>
        │
        ▼
   起始代码 tar 包（在 shark 机器上解包）
        │
        ▼
   提交 → Autolab 自动评分 → 分数即 lab 分数
```

关键点：

- **Autolab 与 Hub 名单不是实时同步的**（`01-overview.pdf` 第 64 页：「Autolab is not tied into the Hub's rosters」，每天更新一次）。**必须先选上课**才有账号。
- 从 **L4 开始改用 GitHub Classroom**：私有仓库 + `git push`，Autolab 拉取评分。邀请须 7 天内接受，否则扣 10%（rec07、rec10 都强调过）。学期结束后**私有仓库被删除**。
- 即使有人在网上贴出某个 lab 的代码，那也**不是完整题目包**——缺 trace、缺测试脚本、缺评分阈值，无法复现评分。

### 5.2 三个层面的「拿不到」

1. **技术层面**：Autolab 在 `andrew.cmu.edu` 域内，走 Shibboleth 单点登录；GitHub Classroom 私有仓库需要组织成员身份。两者都不是「找到 URL 就能下载」的东西。
2. **规则层面**：syllabus §6.7 明确禁止使用未经授权的资料（包括 AI 工具与网上搜索解法）。**这些材料本身就是「未经授权」的**。
3. **实际层面**：即使拿到题解，你也拿不到评分反馈。而这些 lab 的价值恰恰在于「被自动评分反复打回、被迫修 bug」这个循环。

### 5.3 每个 lab 的具体受限环节

| Lab | 受限环节 | 具体原因 |
|---|---|---|
| **L1 Data Lab** | Autolab 下载 + 提交 | 起始代码（`bits.c`、`btest`、`dlc`、`Driverhdrs.pm`）只通过 `autolab download` 发放；评分依赖 Autolab 的 `dlc` 合法性检查与 `btest` 用例 |
| **L2 Bomb Lab** | Autolab 下载 | **每个学生的炸弹二进制不同**（由 Andrew ID 生成），没有账号就根本没有「你的那颗炸弹」 |
| **L3 Attack Lab** | Autolab 下载 | 同 L2，`ctarget` / `rtarget` 按学生生成；`hex2raw` 与 cookie 也是个人的 |
| **L4 Cache Lab** | Autolab + GitHub Classroom | Part A 的 trace 文件是评分输入，不公开；Part B 的 miss 阈值按机器标定 |
| **L5 Malloc Lab** | Autolab + GitHub Classroom | `mdriver` 的 trace 是评分输入；吞吐量 / 利用率阈值不公开 |
| **L6 Tsh Lab** | Autolab + GitHub Classroom | `tshref` 参考实现与 `trace*.txt` 测试脚本不公开；评分靠与参考 shell 的行为对比 |
| **L7 Proxy Lab** | Autolab + GitHub Classroom | 同上，且**不在 18 讲讲义范围内** |
| **L8 SFS Lab** | Autolab + GitHub Classroom | 同上，且**不在 18 讲讲义范围内** |

> 待核实：L4 / L5 / L6 的具体 trace 文件名与阈值未在公开讲义中出现，上表按 CS:APP 官方 lab 的通用结构描述。若与当学期实际材料不符，以官方为准。

### 5.4 逐个 lab：考什么，怎么自学

#### 5.4.1 L1 Data Lab —— 位运算

**官方目标**（`01-overview.pdf` 第 49 页）："Manipulating bits"。

**实际考什么**：

- 只允许用 `! ~ & ^ | + << >>`，在**限定运算符个数**的约束下实现一组函数。
- 整数部分：`bitAnd`、`bitOr`、`isZero`、`tmin`、`isTmax`、`allOddBits`、`negate`、`isAsciiDigit`、`conditional`、`isLessOrEqual`、`logicalNeg`、`howManyBits`。
- 浮点部分：`floatScale2`、`floatFloat2Int`、`floatPower2`（用整数运算模拟 IEEE 754 的位操作）。
- `dlc`（data lab checker）静态检查**没有违禁运算符、没有循环、没有超运算符数**。

**公开知识覆盖**：

| 主题 | 公开来源 |
|---|---|
| 补码、符号扩展、溢出 | `90-原始PDF/15-213/lectures/02-bits-bytes-ints.pdf`；CSAPP 2.1–2.3 |
| 位运算技巧（`x & (x-1)`、`!x` 的构造） | CSAPP 2.1.7–2.1.9 节 |
| IEEE 754 浮点格式 | `02-bits-bytes-ints.pdf` 浮点部分；CSAPP 2.4 节 |
| 练习题 | CSAPP 2.59–2.78 的作业题 |

**自学方案**：

1. 通读 `02-bits-bytes-ints.pdf`，做其中的课堂例题（讲义里每道题都有答案）。
2. 把 CSAPP 第 2 章的 2.59–2.78 全做一遍——这批题的设计目标与 Data Lab 完全重合。
3. **自己给自己出题**：写一个 `bits.c` 风格的练习文件，只允许用 `! ~ & ^ | + << >>`，实现上面列出的函数，自己数运算符个数，用 `printf("%x")` 验证。
4. 用 `gcc -O0 -S` 与 `-O2 -S` 对比你的实现与编译器的输出，理解「编译器怎么把高级运算拆成位运算」。

**检验标准**：能不看资料写出 `howManyBits`（求表示一个数所需的最少位数，要处理负数取反）与 `floatFloat2Int`（要处理溢出、舍入、非规格化）。

#### 5.4.2 L2 Bomb Lab —— 读汇编

**官方目标**（`01-overview.pdf` 第 49 页）："Defusing a binary bomb"。

**实际考什么**：给你一个二进制程序，6 个（+1 个隐藏）关卡，每关要输入正确的字符串或数字；输入错了「爆炸」并扣分；只能用 `objdump -d` 与 `gdb` 分析，不能改二进制。

**公开知识覆盖**：

| 主题 | 公开来源 |
|---|---|
| 汇编基础、寄存器、寻址 | `03-machine.pdf`；CSAPP 3.1–3.5 |
| 条件码、跳转、循环 | `04-machine-beta.pdf`；CSAPP 3.6 |
| 过程调用、栈帧 | `05-machine-gamma.pdf`；CSAPP 3.7 |
| 数组、结构体、指针 | `06-machine-delta.pdf`；CSAPP 3.8–3.9 |
| **官方配套练习（含答案）** | `90-原始PDF/15-213/activities/machine-control.pdf`、`machine-procedures.pdf` |

**自学方案**：

1. 先把 `machine-control.pdf` 与 `machine-procedures.pdf` **做完再对答案**——这两组就是 bomb lab 的「官方预习版」，题目形式几乎一样。
2. 自己写一个「炸弹」：6 个函数分别检查输入（字符串比较、数字序列、递归、链表遍历、排序后比较），编译成 `-O0`，然后**只给自己 `objdump -d` 的输出**，练习逆向。
3. 用 `gdb` 的 `disas`、`x/s`、`x/8gx`、`break *0x...`、`info registers` 把每关的判定逻辑写下来。
4. 进阶：读 CSAPP 3.6 节的 `switch` 跳转表与 3.7 节的递归例子，这是 bomb lab 第 4、6 关的原型。

**检验标准**：给一个陌生的 `-O0` 编译的 C 函数，能在 10 分钟内用 `objdump` 说出它的输入约束。

#### 5.4.3 L3 Attack Lab —— 缓冲区溢出

**官方目标**（`01-overview.pdf` 第 49 页）："The basics of code injection attacks"。

**实际考什么**：

- Phase 1–3：**代码注入**。利用 `getbuf` 的栈溢出，把机器码写进栈，覆盖返回地址跳到 `touch1` / `touch2` / `touch3`。
- Phase 4–5：**ROP（Return-Oriented Programming，面向返回编程）**。栈不可执行时，用现有代码里的 gadget 拼出等价效果。
- 需要构造 `hex2raw` 格式的字节串。

**公开知识覆盖**：

| 主题 | 公开来源 |
|---|---|
| 栈帧布局、返回地址位置 | `05-machine-gamma.pdf`；CSAPP 3.7 |
| x86-64 指令编码（`mov` / `pop` / `ret` 的字节形式） | `03-machine.pdf`；CSAPP 3.1–3.4 |
| 缓冲区溢出原理 | CSAPP 3.10.3 节 |
| ROP 原理 | CSAPP 3.10.4 节 |
| **官方配套练习（含答案）** | `90-原始PDF/15-213/activities/machine-advanced.pdf` |

**自学方案**：

1. 读 `machine-advanced.pdf`——它直接给了 `fun(int i)` 的栈溢出例子与 `gets()` 漏洞分析，**这是 attack lab 的官方入门版**。
2. 自己写一个带 `gets()`（或小缓冲区 + `fgets`）的程序，编译加 `-fno-stack-protector -z execstack`，练习覆盖返回地址。
3. 用 `objdump -d` 手动找 gadget（以 `c3` 结尾的短指令序列），理解 ROP 的组装方式。
4. 读 CSAPP 3.10.4 节的 farm 例子——完整可跑的 ROP 演示。

**检验标准**：能说清「为什么 `-z execstack` 关掉之后代码注入失效，而 ROP 仍然有效」。

#### 5.4.4 L4 Cache Lab —— 缓存

**官方目标**（`01-overview.pdf` 第 50 页）："Building a cache simulator and optimizing for locality"。

**实际考什么**：

- **Part A**：写一个 `csim` 缓存模拟器。参数 `-s`（组索引位数）、`-E`（相联度）、`-b`（块偏移位数）、`-t`（trace 文件）；输出 `hits:? misses:? evictions:?`。trace 格式 `I 0x1234,1`（指令加载）/ `L 0x1234,4`（数据加载）/ `M 0x1234,4`（数据修改）/ `S 0x1234,4`（数据存储）。
- **Part B**：优化 32×32、64×64、61×67 三个矩阵转置，把 miss 数压到阈值以下。只允许不超过 12 个局部变量，不允许在栈上开大数组。

**公开知识覆盖**：

| 主题 | 公开来源 |
|---|---|
| 缓存组织 S / E / B、地址划分 | `10-cache-memories.pdf` 第 10–21 页 |
| 直接映射与组相联的模拟 | 同上第 12–19 页（**两个完整手算示例**） |
| LRU 替换、写策略 | 同上第 20–21 页 |
| 矩阵乘的 miss rate 分析（`ijk` / `jik` / `kij` / `ikj` / `jki` / `kji`） | 同上第 33–43 页 |
| 分块（blocking）的推导 | 同上第 44–52 页 |
| CSAPP 6.4–6.6 节 | 书 + 6.6 节的矩阵乘案例 |

**自学方案**：

1. **Part A 完全可以自己做**：规格在 CSAPP 6.4 节与 `10-cache-memories.pdf` 里写得很完整。自己写 `csim.c`，自己生成 trace（随机产生 `L` / `S` / `M` 序列），自己手算几个用例对答案。
2. **Part B 的 32×32 与 64×64 也能自己做**：`10-cache-memories.pdf` 第 44–52 页已经把分块大小推导（`3B² < C`）讲完了。自己写 `trans.c`，用 `valgrind --tool=cachegrind` 或 `perf stat -e cache-misses` 测 miss 数。
3. 61×67 是「不规则尺寸」的经典难题，需要分块 + 对角线特殊处理，可参考 CSAPP 6.6 节末尾的讨论。

**检验标准**：能手算 `S=4, E=1, B=2` 缓存对序列 `0,1,7,8,0` 的每次命中 / 未命中（`10-cache-memories.pdf` 第 12–15 页有完整过程）；能解释 `kij` 顺序的 miss rate 为什么是 `jki` 的 1/4。

#### 5.4.5 L5 Malloc Lab —— 动态内存分配

**官方目标**（`01-overview.pdf` 第 51 页）："Writing your own malloc package"，"Get a real feel for systems-level programming"。

**实际考什么**：

- 实现 `mm_init`、`mm_malloc`、`mm_free`、`mm_realloc`、`mm_checkheap`。
- 评分同时看**吞吐量**（每秒完成多少次 malloc/free）与**内存利用率**（`U = 峰值有效载荷 / 堆大小`），两者互相制约。
- 需要一个堆检查器（heap checker）验证边界标记、空闲链表、对齐等不变量。
- **checkpoint（L5a）**：基本正确性 + 简单堆检查器。**final（L5b）**：双阈值 + 代码风格分。

**公开知识覆盖**：

| 主题 | 公开来源 |
|---|---|
| 堆与 `sbrk`、显式 vs 隐式分配器 | `13-malloc-basic.pdf` 第 4–6 页 |
| 碎片与吞吐量、`O_k` 公式 | 同上第 10–14 页 |
| 块头 / 块脚、隐式空闲链表 | 同上第 25–32 页 |
| 首次适配、分割、四种合并情形 | 同上第 30–50 页 |
| 显式空闲链表、LIFO / FIFO / 地址有序 | `14-malloc-advanced.pdf` 第 9–17 页 |
| 分离适配（segregated fit） | 同上第 19–22 页 |
| 七类内存错误 | 同上第 26–32 页 |
| 调试工具（gdb、一致性检查器、valgrind） | 同上第 41 页 |
| CSAPP 9.9–9.12 节 | 书 |

**自学方案**（**最适合自学的 lab**）：

1. 按 `13-malloc-basic.pdf` 第 25–50 页的伪代码写一个**隐式空闲链表 + 首次适配**的版本，跑通正确性。
2. 按 `14-malloc-advanced.pdf` 第 9–17 页改写成**显式空闲链表**，比较吞吐量变化。
3. 加**分离适配**（`14-malloc-advanced.pdf` 第 19–22 页给了 size class 例子：`16`、`32–48`、`64–∞`）。
4. **自己写一个 `mdriver`**：生成随机 malloc / free / realloc 序列，记录峰值有效载荷与堆大小算利用率；用 `clock_gettime` 测吞吐量。
5. **自己写一个堆检查器**：遍历整个堆，验证「每两个相邻块不能同时空闲」「空闲链表里每个块都在堆范围内」「每个块的 size 字段与实际跨度一致」。
6. 用 `valgrind` 与 AddressSanitizer 交叉验证。

**检验标准**：能手写 `coalesce` 的四种情形（前后都占用、前空后占、前占后空、前后都空）；能解释「为什么释放后还要写块脚」以及「为什么块脚只在空闲块里需要」。

#### 5.4.6 L6 Tsh Lab —— Unix shell

**官方目标**（`01-overview.pdf` 第 52 页）："Writing your own Unix shell"，"A first introduction to concurrency"。

**实际考什么**：

- 实现带**作业控制**（job control）的 shell：`eval`、`builtin_cmd`、`do_bgfg`、`waitfg`、`sigchld_handler`、`sigint_handler`、`sigtstp_handler`。
- 支持前台 / 后台作业、`ctrl-c`（SIGINT）、`ctrl-z`（SIGTSTP）、`fg` / `bg` / `jobs`。
- 用 `trace*.txt` 脚本与参考 shell `tshref` 的行为对比评分。

**公开知识覆盖**：

| 主题 | 公开来源 |
|---|---|
| 进程、`fork` / `execve` / `wait` / `exit` | `16-processes.pdf`；CSAPP 8.1–8.4 |
| 异常表、系统调用 | `17-ecf.pdf` 第 11–20 页；CSAPP 8.1 |
| 信号、`sigprocmask`、`sigsuspend` | 同上第 25–66 页；CSAPP 8.5–8.6 |
| 作业控制（进程组、`ctrl-c` / `ctrl-z`） | 同上第 36–39 页；CSAPP 8.5.5 |
| 文件描述符、重定向 | `18-system-io.pdf` 第 39–46 页；CSAPP 10.7–10.9 |
| shell 主循环与 `eval` | `16-processes.pdf` 第 55–66 页 |

**自学方案**：

1. **`16-processes.pdf` 第 55–66 页直接给了一个简化 shell 的完整代码**（`main` 循环 + `eval` + 内建命令 + 后台作业）。抄下来跑通，这是 Tsh Lab 的骨架。
2. 按 `17-ecf.pdf` 第 57–66 页补信号处理：`child_handler` 循环 `waitpid`（因为**信号不排队**）、`procmask` 阻塞 SIGCHLD 消除竞态、`sigsuspend` 实现 `waitfg`。
3. 按 `18-system-io.pdf` 第 44–46 页补重定向：`dup2(oldfd, newfd)` 的引用计数变化。
4. **自己写测试脚本**：一个 `.txt` 文件，每行一条命令，前面加 `tsh>` 表示输入、不加前缀表示期望输出。写个 Python 脚本对比实际输出与期望输出。
5. 用 `ps`、`/proc/<pid>/status`、`strace -f` 观察进程状态与系统调用。

**检验标准**：能解释为什么 `while (!pid) pause();` 有竞态而 `sigsuspend` 没有；能解释为什么 SIGCHLD handler 必须循环调用 `waitpid` 而不能只调一次。

#### 5.4.7 L7 / L8 —— 不在讲义范围内

| Lab | 主题 | 缺的讲义 |
|---|---|---|
| **L7 Proxy Lab** | 支持 HTTP/1.0 的 Web 代理，带缓存与并发 | 网络编程（CSAPP 第 11 章）、并发编程（第 12 章）——**18 讲讲义未覆盖** |
| **L8 SFS Lab** | 扩展一个基础的并行文件系统 | 文件系统与并行（CSAPP 第 12 章的一部分）——**18 讲讲义未覆盖** |

`01-overview.pdf` 第 53–54 页把 "Networking, and Concurrency" 与 "Parallelism and Files" 列为课程模块，但**公开讲义止于第 18 讲**。这两块只能读 CSAPP 第 11–12 章。

---

## 6. 代码示例

### 6.1 官方课程代码

本节没有可引用的官方 lab 代码（这正是「受限」的含义）。可引用的只有**讲义里给出的规格与伪代码**，例如：

**（1）缓存模拟器的命令行规格**（`10-cache-memories.pdf` 第 12–21 页的模拟框架）

讲义用 `S`（组数）、`E`（每组的行数）、`B`（块字节数）三个参数描述任意缓存，并给出地址划分：

```
| tag (t 位) | set index (s 位) | block offset (b 位) |
```

其中 `S = 2^s`、`B = 2^b`。这就是 L4 Part A 的 `-s` / `-E` / `-b` 三个参数的直接来源。

**（2）隐式空闲链表的块结构**（`13-malloc-basic.pdf` 第 25–32 页）

讲义给出块头格式：

```
| size (29 位) | 0 0 0 | a (1 位) |
```

`a` 是「已分配」位（bit 0），`size` 用 `~0xfL` 掩码取出。这是 L5 的 `mm_malloc` / `mm_free` 的基础。

**（3）shell 的主循环骨架**（`16-processes.pdf` 第 55–66 页）

讲义给出了 `main` 循环 + `eval` + 内建命令 + 后台作业的完整代码，是 L6 的骨架。

> 以上均为**讲义公开内容**，不是 lab 的起始代码。lab 的起始代码（`bits.c`、`csim.c`、`mm.c`、`tsh.c`）需要通过 Autolab 获取。

### 6.2 Agent 自行编写的教学示例

以下代码**均为非官方**，只用于说明「没有官方测试框架时怎么自测」。

**（1）自制的随机 malloc/free 驱动（替代 `mdriver`）**（非官方，仅用于说明概念）

```c
/* 非官方，仅用于说明概念 */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define N 2000
#define MAXSZ 4096

int main(void) {
    void *slot[N] = {0};          /* slot[i] == NULL 表示该槽位空闲 */
    size_t peak_payload = 0, cur_payload = 0;
    srand(12345);

    for (int step = 0; step < 200000; step++) {
        int i = rand() % N;
        if (slot[i] == NULL) {                     /* 分配 */
            size_t sz = (size_t)(rand() % MAXSZ) + 1;
            slot[i] = malloc(sz);
            if (!slot[i]) { fprintf(stderr, "OOM\n"); return 1; }
            cur_payload += sz;
            if (cur_payload > peak_payload) peak_payload = cur_payload;
        } else {                                   /* 释放 */
            free(slot[i]);
            slot[i] = NULL;
            cur_payload = 0;                       /* 简化：见下方说明 */
            for (int k = 0; k < N; k++)            /* 重算，仅用于演示 */
                if (slot[k]) cur_payload += 1;
        }
    }
    printf("peak payload = %zu bytes\n", peak_payload);
    return 0;
}
```

这段代码只演示**思路**：随机分配释放、记录峰值有效载荷。真正的 `mdriver` 还要记录堆大小（用 `sbrk(0)` 前后差值），才能算出利用率 `U = peak_payload / heap_size`。

**（2）自制的 trace 生成器（替代 L4 的 `traces/`）**（非官方，仅用于说明概念）

```python
# 非官方，仅用于说明概念
import random
random.seed(7)
for _ in range(1000):
    op = random.choice("LSM")
    addr = random.randrange(0, 4096, 4)   # 4 字节对齐，落在 4KB 内
    print(f"{op} 0x{addr:x},4")
```

生成的格式与 L4 Part A 的 trace 一致（`L` 加载 / `S` 存储 / `M` 修改）。你可以用自己写的 `csim` 跑它，再用**手算**验证前 20 行——手算对上了，模拟器就可信了。

**（3）自制的 shell 测试脚本（替代 L6 的 `trace*.txt`）**（非官方，仅用于说明概念）

```
# 非官方，仅用于说明概念
tsh> /bin/echo hello
hello
tsh> /bin/echo hello &
[1] (12345)
tsh> jobs
[1] (12345) Running /bin/echo hello &
tsh> fg
/bin/echo hello
hello
```

约定：`tsh>` 开头是输入，其余是期望输出。写个 Python 脚本用 `subprocess` 喂输入、比对输出即可。注意后台作业的 PID 每次不同，比对时要把它归一化。

**（4）自制的堆检查器骨架（L5 的 `mm_checkheap`）**（非官方，仅用于说明概念）

```c
/* 非官方，仅用于说明概念 */
int check_heap(void) {
    int errors = 0;
    char *p = heap_start;
    int prev_free = 0;

    while (p < heap_end) {
        size_t sz = get_size(p);
        int cur_free = !get_alloc(p);

        if (sz == 0 || sz % 16 != 0) {          /* 大小必须非零且 16 字节对齐 */
            printf("bad size at %p\n", p); errors++;
        }
        if (prev_free && cur_free) {            /* 相邻块不能同时空闲 */
            printf("adjacent free blocks at %p\n", p); errors++;
        }
        prev_free = cur_free;
        p += sz;
    }
    if (p != heap_end) {                        /* 必须正好走到堆尾 */
        printf("heap walk overran\n"); errors++;
    }
    return errors;
}
```

这三条检查对应 `14-malloc-advanced.pdf` 第 41 页提到的「一致性检查器」的核心不变量。

---

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| **起始代码（starter code）** | **规格（specification）** | 前者是 Autolab 发放的骨架文件（拿不到）；后者是讲义里的行为契约（**完全公开**）。缺前者不影响学，缺后者才真的没法做 |
| **使用公开讲义 / CSAPP** | **使用泄漏的题解** | 前者是课程明确允许的（syllabus §6.7 允许带署名的课程材料与教材）；后者违反学术诚信 |
| **「按规格自己实现」** | **「绕过访问控制」** | 前者用公开规格 + 自己的实现 + 自己的测试；后者是找账号 / 找镜像 / 找后门，越界 |
| **个性化二进制（L2 / L3）** | **通用起始代码（L4–L6）** | 前者按学号生成，别人的完全无用；后者是通用骨架，理论上可复用（但仍需权限获取） |
| **trace（评分输入）** | **测试脚本（自己写的）** | 前者不公开、决定分数；后者自己写、只验证行为。两者格式可以一致，但权威性完全不同 |
| **L5a（checkpoint）** | **L5b（final）** | 前者只考正确性 + 简单堆检查器；后者加吞吐量 / 利用率双阈值 + 代码风格分 |

---

## 8. 对应原版讲义

| 材料 | 相对路径 | 页数 | 重点页码 |
|---|---|---|---|
| 课程总览（lab 列表与政策） | `90-原始PDF/15-213/lectures/01-overview.pdf` | **73** | 第 49–54 页（8 个 lab 的主题与定位）、56 页（Lab0 忠告）、57 页（评分政策与 Parsons Puzzle）、58 页（迟交）、59 页（shark 机器）、62–64 页（Autolab 与「Autolab 分数就是 lab 分数」）、69 页（bootcamp）、70 页（总评构成） |
| 课程大纲 | `90-原始PDF/15-213/labs/syllabus.pdf` | **13** | §6.2（GitHub Education 与仓库删除）、§6.3（截止与迟交）、§6.6（评分）、§6.7（学术诚信） |
| L1 相关知识 | `90-原始PDF/15-213/lectures/02-bits-bytes-ints.pdf` | 见课表 | 补码、位运算、IEEE 754 全章 |
| L2 相关知识 | `90-原始PDF/15-213/lectures/03-machine.pdf`、`04-machine-beta.pdf`、`05-machine-gamma.pdf`、`06-machine-delta.pdf` | 见课表 | 汇编、控制流、过程、数据结构 |
| L2 / L3 官方 activity | `90-原始PDF/15-213/activities/machine-control.pdf`、`machine-procedures.pdf`、`machine-advanced.pdf` | 见 activity 清单 | 三组均**含答案**，是 bomb / attack lab 的公开预习版 |
| L4 相关知识 | `90-原始PDF/15-213/lectures/10-cache-memories.pdf` | **73** | 第 10–21 页（组织与模拟）、33–43 页（miss rate 分析）、44–52 页（分块） |
| L5 相关知识 | `90-原始PDF/15-213/lectures/13-malloc-basic.pdf`、`14-malloc-advanced.pdf` | **58**、**43** | 13 讲第 25–50 页（隐式链表与合并）、14 讲第 9–22 页（显式链表与分离适配）、26–32 页（七类错误）、41 页（调试工具） |
| L6 相关知识 | `90-原始PDF/15-213/lectures/16-processes.pdf`、`17-ecf.pdf`、`18-system-io.pdf` | **68**、**66**、**54** | 16 讲第 55–66 页（shell 骨架）、17 讲第 25–66 页（信号）、18 讲第 39–46 页（描述符与重定向） |

原始链接：

- 官方 labs 页 <https://www.cs.cmu.edu/~213/labs.html>
- 官方 schedule 页 <https://www.cs.cmu.edu/~213/schedule.html>
- 学术诚信 <https://www.cs.cmu.edu/~213/academicintegrity.html>
- Autolab <https://autolab.andrew.cmu.edu/courses/15213-f26>
- CS:APP 官方 lab 说明（**公开**，含部分 handout 与 FAQ）<https://csapp.cs.cmu.edu/3e/labs.html>
- CS:APP 学生站点 <https://csapp.cs.cmu.edu/3e/students.html>
- 教材站点 <https://csapp.cs.cmu.edu/>

> 待人工核对：CS:APP 官方站点上的 lab 说明是**教材作者**发布的通用版本，与 CMU 当学期（Fall 2026）的课程版在细节上可能有差异（尤其评分阈值与 trace 文件）。可公开访问的部分可以自由使用；需要 CMU 账号的部分不在其列。

---

## 9. 对应视频

**未找到官方公开录像。** 15-213 的 lecture / recitation / bootcamp 录像仅对 CMU 校内开放。本页涉及的所有 lab 讲解都没有公开录像。

---

## 10. 本节复习

1. 分发链路：选课名单 → Autolab（Shibboleth）→ `autolab download` → 本地解包 → 提交评分；L4 起改用 GitHub Classroom 私有仓库（7 天邀请、学期末删除）。
2. 三个层面的「拿不到」：技术（域内认证）、规则（学术诚信）、实际（没有评分反馈）。
3. L2 / L3 的二进制**按学号生成**，这是「拿到别人的代码也没用」的技术原因。
4. 知识覆盖度：L1 100%、L2 95%、L3 90%、L4 100%、L5 100%、L6 95%、L7 / L8 0%。
5. **L5 Malloc Lab 最适合自学**——两讲讲义（101 页）几乎就是设计文档，含伪代码。
6. L6 的骨架代码在 `16-processes.pdf` 第 55–66 页直接给出。
7. 三条原则：不找泄漏题解、不绕过访问控制、按规格自己实现。
8. 自测三件套：自制 driver（L5）、自制 trace（L4）、自制测试脚本（L6）。

---

## 11. 自我检查

**Q1.** 为什么说 L2 Bomb Lab 即使有人把完整题解贴到网上，对你也基本没用？请从「个性化」与「评分反馈」两个角度回答。

**Q2.** 本页说 L5 是「最适合自学的 lab」。如果只允许你读两讲讲义中的一讲，你选哪一讲？为什么？

**Q3.** L4 Part A 的规格是公开的（`-s` / `-E` / `-b` / `-t` 四个参数 + 三行输出）。那么「自己写一个 `csim`」与「做官方 L4 Part A」的差别到底在哪里？这个差别重要吗？

**Q4.** 有同学说：「既然规格公开，那我按规格实现完，就等于做完了 lab。」这个说法在哪一点上是对的，在哪一点上是错的？

**Q5.** L6 Tsh Lab 的检验标准里提到「`while (!pid) pause();` 有竞态而 `sigsuspend` 没有」。请说明这个竞态的窗口在哪里，以及 `sigsuspend` 是如何消除它的。

<details>
<summary>参考答案</summary>

**A1.** **个性化角度**：L2 的炸弹二进制按 Andrew ID 生成，每一关的正确输入（字符串 / 数字序列）都不同。别人贴出的题解是「他那颗炸弹」的答案，对你的炸弹无效——你连自己的炸弹都下载不到。**评分反馈角度**：bomb lab 的价值一半在于「输入错了立刻爆炸、扣分」这个即时反馈循环。没有 Autolab，你既没有自己的炸弹，也没有分数反馈，只剩下一堆与你无关的答案。

**A2.** 选 **`13-malloc-basic.pdf`（L13，58 页）**。理由：它从「堆是什么、`sbrk` 怎么用」讲到「块头块脚、隐式空闲链表、首次适配、四种合并情形」，**含完整伪代码**，是端到端可实现的。L14（43 页）讲的是**优化**（显式链表、分离适配），前提是已经有了一个能跑的隐式链表版本。所以先读 L13 能让你写出第一个可工作的 `mm_malloc`；只读 L14 会缺地基。

**A3.** 差别有三点：（a）**测试用例不同**——官方有 15 条精心设计的 trace，覆盖相联度、替换策略、边界地址等组合；你自己生成的 trace 是随机的，可能漏掉关键组合。（b）**评分阈值不同**——Part B 的 miss 阈值是按机器标定的，你自己测只能看相对改进。（c）**反馈粒度不同**——Autolab 会告诉你哪条 trace 挂了，自测只能看总数。**这个差别重要吗？** 对「学会缓存原理」不重要——Part A 的核心是地址划分与 LRU 模拟，手算验证足以确认正确性；对「拿到 lab 分数」很重要，但那条路本来就不通。

**A4.** **对的部分**：从「学到知识」的角度，按公开规格实现确实覆盖了 lab 的全部知识点，因为规格就是 lab 的行为契约。**错的部分**：lab 还有三个规格之外的东西——**边界条件的完备性**（官方 trace 会打你没想到的角落）、**性能阈值的标定**（你需要知道「多快才算够」）、**代码风格的工程要求**（TA 1:1 评审）。所以准确的说法是：「按规格实现」≈ 完成了 lab 的**学习目标**，但不等于完成了 lab 的**评分要求**。

**A5.** 竞态窗口：`waitforsignal.c` 式的写法是

```c
while (!pid)          /* 检查 pid */
    pause();          /* 睡眠等信号 */
```

问题在于 `while (!pid)` 判断与 `pause()` 调用之间有**时间窗口**。如果 SIGCHLD 恰好在这个窗口内到达并被处理（handler 把 `pid` 置 0），那么 `pause()` 执行时会**永远睡下去**——信号已经处理完了，不会再来一次。

`sigsuspend` 消除它的方式：把「解除阻塞」与「进入睡眠」合并成**一个原子操作**。调用前先 `sigprocmask(SIG_BLOCK, &mask, &prev)` 阻塞 SIGCHLD，然后 `sigsuspend(&prev)` 在**恢复旧掩码的同时**进入睡眠——内核保证「检查 pending 信号」与「睡眠」之间没有窗口。所以要么信号在 `sigsuspend` 之前就 pending（此时 `sigsuspend` 立刻返回），要么在睡眠中被递送（唤醒它），不存在丢失。

</details>

---

## 12. 进一步学习

- Lab 总览（全部 8 个 lab 的日期与获取方式）：[[20-CMU-15-213/03-Lab实验笔记/00-Lab总览|15-213 Lab 总览]]
- 唯一公开 lab 的详细笔记：[[20-CMU-15-213/03-Lab实验笔记/01-CProgrammingLab笔记|CProgrammingLab 笔记]]
- L4 的完整知识：[[20-CMU-15-213/02-中文学习笔记/15-213-10-Cache-Memories|L10 Cache Memories]]
- L5 的完整知识：[[20-CMU-15-213/02-中文学习笔记/15-213-13-Dynamic-Memory-Allocation-Basic|L13 Malloc Basic]]、[[20-CMU-15-213/02-中文学习笔记/15-213-14-Dynamic-Memory-Allocation-Advanced|L14 Malloc Advanced]]
- L6 的完整知识：[[20-CMU-15-213/02-中文学习笔记/15-213-16-Processes|L16 Processes]]、[[20-CMU-15-213/02-中文学习笔记/15-213-17-Exceptional-Control-Flow|L17 Exceptional Control Flow]]、[[20-CMU-15-213/02-中文学习笔记/15-213-18-System-Level-IO|L18 System-Level I/O]]
- 课程总览（含材料完整性盘点）：[[20-CMU-15-213/00-课程总览|CMU 15-213 - 课程总览]]
- 学习进度（含 lab 与讲次的对应）：[[20-CMU-15-213/04-学习进度|CMU 15-213 - 学习进度]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 官方 labs 页：<https://www.cs.cmu.edu/~213/labs.html>
- 官方学术诚信页：<https://www.cs.cmu.edu/~213/academicintegrity.html>
- CS:APP 公开 lab 说明：<https://csapp.cs.cmu.edu/3e/labs.html>
