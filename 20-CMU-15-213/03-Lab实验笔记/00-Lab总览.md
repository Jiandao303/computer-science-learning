---
course: CMU 15-213
course_name: Introduction to Computer Systems
semester: Fall 2026
lecture_id: lab-overview
topic: Lab 总览与获取方式
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-213
  - Lab
  - 实验
  - 总览
---

# CMU 15-213 · Lab 总览（Lab Overview）

> 入口页：[[20-CMU-15-213/00-课程总览|CMU 15-213 - 课程总览]]；逐讲索引：[[20-CMU-15-213/01-课程目录|CMU 15-213 - 课程目录]]。
>
> **一句话结论**：8 个 lab 里**只有 L0 CProgrammingLab 的完整题目包是公开的**；L1–L6 全部通过 Autolab + GitHub Classroom 发放，需要 CMU 课程选课账号。本知识库只写能拿到原文的那一个，其余在 [[20-CMU-15-213/03-Lab实验笔记/02-受限Lab说明|受限 Lab 说明]] 里给出合法的替代学习路径。

---

## 1. 本节学习目标

学完本页，你应当能够：

1. **说出** 15-213 全部 8 个 lab 的名称、主题、发布日与截止日，并指出它们各自对应哪几讲讲义。
2. **解释** lab 材料的分发链路（选课名单 → Autolab → `autolab download` → 本地解包 → 提交评分），以及为什么非选课学生拿不到。
3. **判断** 一个 lab 的分数由哪几部分构成（正确性 / 性能 / 代码风格 / Parsons Puzzle），并算出一道迟交 4 天的 lab 会被扣多少分。
4. **区分** Autolab 分数与本地跑分、grace day 与普通迟交、`.tar` 与 `.zip` 这几组容易混的规则。
5. **搭建** 一个不依赖 CMU 账号的等价实验环境（Docker + Ubuntu），并说明它与 shark 机器的差异在哪里。

---

## 2. 前置知识

- 本页是 lab 的**入口页**，不依赖任何讲次；但读完之后要动手做 lab，需要先具备：
  - C 语言与指针（L0 的全部内容，见 [[20-CMU-15-213/02-中文学习笔记/15-213-01-Overview|L01 Course Overview]]）
  - 汇编与 gdb 调试（L03–L06，见 [[20-CMU-15-213/02-中文学习笔记/15-213-03-Machine-Programming-I-Basics|L03]] 起）
  - 缓存（L09–L10）、虚拟内存与 malloc（L11–L14）、进程与信号（L16–L18）
- 外部概念：命令行基本操作、`make`、`git`、`ssh`。
- 相关页面：[[20-CMU-15-213/04-学习进度|CMU 15-213 - 学习进度]]（lab 与讲次的时间对应）、[[20-CMU-15-213/01-课程目录|CMU 15-213 - 课程目录]]。

---

## 3. 核心概念

- **Lab（实验）**：15-213 的主要评分载体，占总评 **50%**（`01-overview.pdf` 第 70 页）。8 个 lab 覆盖从位运算到文件系统的全部课程主线。
- **Autolab（自动评分平台）**：CMU 的课程作业提交与评分系统，地址 `https://autolab.andrew.cmu.edu/courses/15213-f26`。**Autolab 上的分数就是你的 lab 分数**（`01-overview.pdf` 第 63 页）。
- **GitHub Classroom（GitHub 课堂）**：L4 起的作业分发方式。每个学生拿到一个**私有仓库**，`git push` 后由 Autolab 拉取评分；学期结束后仓库被删除（syllabus §6.2）。
- **Shark machine（Shark 机器）**：`shark.ics.cs.cmu.edu`，Intel 捐赠的服务器集群，官方指定的 lab 环境。编译器版本与课程一致，且支持 `make submit`。
- **Handin tarball（提交压缩包）**：`make` 生成的 `.tar` 文件，是唯一被接受的提交格式。**不接受** `.zip` / `.gzip` / `.tgz`。
- **Grace day（宽限日）**：全学期共 **5 天**，每个 lab 自动最多用 **2 天**，用完后再迟交每天扣 **15%**，超过 **3 天**不再收（`01-overview.pdf` 第 58 页）。
- **Parsons Puzzle（帕森斯拼图）**：一种**现场**测评形式——给你打乱顺序的代码行，让你拖拽成正确程序，在机房当面完成，约占该 lab 的 10%。L1 / L4 / L5b / L6 / L7 有。
- **Code style grade（代码风格分）**：由 TA 一对一评审的分数，L4 / L5a / L5b / L6 / L7 有。

---

## 4. 通俗理解

把 lab 想成**健身房的私教课**：

- 讲义是「动作示范视频」——看得懂，但不动手就不会。
- Lab 是「教练盯着你做的组数」——做错了当场被纠正（Autolab 打回），这才长肌肉。
- Autolab 是「器械上的计数器」——它只认它测到的次数。你说你举了 20 次但计数器显示 12 次，那就是 12 次。**本地跑得再好也不算**（`01-overview.pdf` 第 63 页的原话是「Your grade on autolab is your grade for the lab」）。
- Grace day 是「5 张请假条」——全学期只有 5 张，每个 lab 最多用 2 张。用完再缺课，每天扣 15% 的成绩，缺超过 3 天直接不给分。

一个具体数字：假设 L5 Malloc Lab 你拿到 90 分（满分 100），迟交 4 天，且这个 lab 已用满 2 天 grace day。那么超出 grace 的是 2 天，扣 `2 × 15% = 30%`，最终 `90 × 0.7 = 63` 分。**一次迟交就能把 A 变成 D**——这就是讲义反复强调「把 grace day 留到最后几个 lab」的原因。

---

## 5. 原理与推导

### 5.1 Lab 总表与知识映射

| Lab | 名称 | 主题 | 发布日 | 截止日 | 对应讲义 | 公开材料 | 获取方式 |
|---|---|---|---|---|---|---|---|
| **L0** | CProgrammingLab | 用单链表实现队列 | **Aug 25** | Sep 01 | 15-122 的 C 基础 | **有**：`cprogramminglab.pdf`（8 页）+ `cprogramminglab-handout.tar` | **直接下载** |
| **L1** | Data Lab | 只用 `! ~ & ^ \| + << >>` 实现整数与浮点函数 | **Aug 27** | Sep 08 | L02 | 无 | Autolab |
| **L2** | Bomb Lab | 用 gdb 拆解二进制炸弹 | **Sep 03** | Sep 15 | L03–L06 | 无 | Autolab |
| **L3** | Attack Lab | 缓冲区溢出代码注入 + ROP | **Sep 15** | Sep 24 | L05、L06 | 无 | Autolab |
| **L4** | Cache Lab | Part A 缓存模拟器；Part B 矩阵转置优化 | **Sep 24** | Oct 08 | L09、L10 | 无 | Autolab + GitHub Classroom |
| **L5** | Malloc Lab | 自己实现 `mm_malloc` / `mm_free` / `mm_realloc` | **Oct 08** | checkpoint Oct 27；final Nov 03 | L11–L14 | 无 | Autolab + GitHub Classroom |
| **L6** | Tsh Lab | 自己实现带作业控制的 Unix shell | **Nov 03** | Nov 12 | L16–L18 | 无 | Autolab + GitHub Classroom |
| **L7** | Proxy Lab | Web 代理（HTTP + 缓存 + 并发） | 讲义未给 | — | CSAPP 第 11 章（**讲义未覆盖**） | 无 | Autolab + GitHub Classroom |
| **L8** | SFS Lab | 扩展一个基础文件系统 | 讲义未给 | — | CSAPP 第 12 章（**讲义未覆盖**） | 无 | Autolab + GitHub Classroom |

> 待核实：L1–L8 的日期来自 recitation slides 的提醒（rec02：datalab due Sep 8、bomblab due Sep 15；rec04：attacklab due Sep 24；rec05：cachelab due Oct 8；rec07：malloclab checkpoint Oct 27、final Nov 3；rec09：tshlab released Nov 3；rec10：tshlab due Nov 12）与 `01-overview.pdf` 第 49–54 页的主题对应。L7 / L8 的日期在公开材料中没有出现。

发布节奏（`01-overview.pdf` 第 49–54 页 + recitation 提醒）：

```
Aug 25  L0 ──────────────────────────────┐
Aug 27     L1 ─────────────┐             │
Sep 03        L2 ────────┐  │             │
Sep 15           L3 ───┐ │  │             │
Sep 24              L4 ┐│ │  │             │
Oct 08                 L5 ────────────────┤
Nov 03                    L6 ──┐           │
                          (L7 / L8 讲义未给日期)
```

**读法**：lab 的发布日基本跟着讲义走，但**滞后 1–2 讲**。原因是 lab 要用到的那一讲讲完之后才发。例如 L5 Malloc Lab 在 Oct 08（L14 当天）发布，而它依赖 L13（Oct 06）+ L14（Oct 08）两讲；L6 Tsh Lab 在 Nov 03 发布，依赖 L16（Oct 27）–L18（Nov 05）三讲——**最后一讲甚至比 lab 发布还晚两天**，这意味着 Tsh Lab 的 I/O 部分要边做边学。

### 5.2 分数构成

| 项目 | 占比 / 说明 |
|---|---|
| **正确性分** | Autolab 自动评分，跑官方测试用例 |
| **性能分** | 部分 lab（L4 Part B、L5、L7）按指标给分：cache miss 数、吞吐量 |
| **代码风格分** | L4 / L5a / L5b / L6 / L7 有，由 TA 1:1 评审 |
| **Parsons Puzzle** | L1 / L4 / L5b / L6 / L7 有，约 10%，**现场在机房**拼代码 |

课程总评（`01-overview.pdf` 第 70 页）：Labs 50%、Written 6%、Paper Quizzes 4%、Midterm 15%、Final 25%。采用直尺制（90/80/70/60），只做向上的小幅调分，不给 +/- 等级。

### 5.3 提交链路与迟交计算

提交：

1. **L0**：`make` 生成 `cprogramminglab-handin.tar` 上传 Autolab；或在 Andrew / Shark 机器上 `make submit`。
2. **L4 起**：GitHub Classroom 私有仓库，`git push` 后 Autolab 拉取。**仓库邀请必须在 7 天内接受**，否则扣 10%（rec07、rec10 都强调过）。
3. **学期结束后私有仓库被删除**（syllabus §6.2）→ 尽早频繁 commit。

迟交（`01-overview.pdf` 第 58 页、syllabus §6.3）：

| 规则 | 数值 |
|---|---|
| 全学期 grace day 总数 | **5 天** |
| 每个 lab 自动最多使用 | **2 天** |
| 用完后每天扣分 | **15%** |
| 超过截止日多久不再收 | **3 天** |

推导：设某 lab 得分 `S`，迟交 `d` 天，已用 grace `g = min(d, 2)`，则实得 `S × (1 − 0.15 × (d − g))`，且 `d − g > 3` 时实得为 0。这就是 4.1 节那个「90 分 → 63 分」的算式。

### 5.4 学术诚信

syllabus §6.7：**不得使用未经授权的资料，包括 AI 工具**；不得在网上搜索解法（L0 说明里直接点名 "linked-list implementation in C" 这类搜索）。允许的是：课程提供的材料、带署名的课程材料引用、CS:APP 书与官网（带署名）。**所有 lab 必须独立完成**。

### 5.5 运行环境

官方环境：

```
linux> ssh shark.ics.cs.cmu.edu
```

- 用 Andrew ID 与密码登录；Intel 捐赠的服务器集群，专供 15-213 / 15-513。
- 存储与通用 Andrew 集群共享（AFS）。
- **不要**在通用 Andrew 集群上做 213 的作业：负载高，编译器版本不对。
- 本地机器理论上也能做，但编译器版本大概率不对，且 `make submit` 一定不能用。

各 lab 需要的工具：

| Lab | 工具 |
|---|---|
| L0 | `gcc`、`make`、`gdb`、AddressSanitizer |
| L1 | `gcc`、`dlc`（合法性检查器）、`btest` |
| L2 | `gdb`、`objdump`、`strings` |
| L3 | `gdb`、`objdump`、`hex2raw`（lab 自带） |
| L4 | `valgrind`、`getopt`、`clock_gettime` |
| L5 | `gdb`、`mdriver`（lab 自带）、`valgrind` |
| L6 | `gdb`、`valgrind`、`strace`、`ps`、`/proc` |
| L7 | `curl`、`wget`、`telnet`、`nc` |

---

## 6. 代码示例

### 6.1 官方课程代码

**（1）Shark 机器登录**（`01-overview.pdf` 第 59 页）

```bash
linux> ssh shark.ics.cs.cmu.edu
```

**（2）Autolab 下载与解包**（`cprogramminglab.pdf` 第 3 页）

```bash
linux> mkdir ~/private/15213
linux> cd ~/private/15213
linux> autolab download 15213-f26:cprogramminglab
linux> tar --strip=1 -xf cprogramminglab-handout.tar
linux> rm cprogramminglab-handout.tar
```

`--strip=1` 的作用是去掉 tar 包里的顶层目录，让 16 个文件直接落在当前目录。

**（3）本地测试**（`cprogramminglab.pdf` 第 6 页）

```bash
linux> make
linux> ./qtest -f traces/trace-eg.cmd
linux> ./driver.py
```

**（4）提交**（`cprogramminglab.pdf` 第 8 页）

```bash
linux> make                # 生成 cprogramminglab-handin.tar
linux> make submit         # 在 shark 上直接提交
```

### 6.2 Agent 自行编写的教学示例

**（1）Docker 等价环境**（非官方，仅用于说明概念）

```bash
# 非官方，仅用于说明概念
docker run -it --rm -v "$PWD":/work -w /work ubuntu:22.04 bash
apt-get update && apt-get install -y gcc gdb make valgrind python3 git
```

选 Ubuntu 22.04 是因为它的 gcc 11.x / glibc 2.35 与 CS:APP 3e 的示例基本兼容；shark 的具体版本官方未公开。

> 待核实：shark 机器的 gcc 版本未在讲义中给出。若你发现某个 lab 的行为在 Docker 里与描述不符，优先怀疑编译器版本差异（尤其 L3 Attack Lab 的栈布局）。

**（2）迟交扣分计算器**（非官方，仅用于说明概念）

```c
/* 非官方，仅用于说明概念 */
#include <stdio.h>

double late_factor(int days_late) {
    int grace = days_late < 2 ? days_late : 2;   /* 每 lab 最多用 2 天 grace */
    int charged = days_late - grace;            /* 真正扣分的天数 */
    if (charged > 3) return 0.0;                /* 超过 3 天不再收 */
    return 1.0 - 0.15 * charged;                /* 每天扣 15% */
}

int main(void) {
    int cases[] = {0, 1, 2, 3, 4, 5, 6};
    for (int i = 0; i < 7; i++)
        printf("late %d day(s): %.2f\n", cases[i], late_factor(cases[i]));
    return 0;
}
```

输出（可自行验证）：

```
late 0 day(s): 1.00
late 1 day(s): 1.00
late 2 day(s): 1.00
late 3 day(s): 0.85
late 4 day(s): 0.70
late 5 day(s): 0.55
late 6 day(s): 0.00
```

注意第 5 天：`charged = 3`，**仍然收**（规则是「超过 3 天」才不收），扣 45%；第 6 天 `charged = 4 > 3`，直接 0。

---

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| **Autolab 分数** | **本地跑分** | 前者是唯一有效的成绩（`01-overview.pdf` 第 63 页）；后者只作参考，因为 Autolab 的测试更严格，且截图与文件时间戳可伪造 |
| **Grace day** | **普通迟交** | Grace day 是「免费」的 5 天（每 lab 最多 2 天）；用完后每天扣 15%，超过 3 天不收 |
| **L5a（checkpoint）** | **L5b（final）** | L5a 只要求基本正确性 + 简单堆检查器；L5b 要求吞吐量与利用率双阈值，且有代码风格分 |
| **`.tar`** | **`.zip` / `.tgz`** | 只接受 `.tar`（`make` 生成的那个）；其他格式 Autolab 直接拒收 |
| **Autolab** | **GitHub Classroom** | Autolab 是**评分**平台（全学期都用）；GitHub Classroom 是 L4 起的**分发**平台，两者通过 `git push` → 拉取串联 |
| **Shark 机器** | **通用 Andrew 集群** | 只有 shark 是官方指定环境（编译器版本对、能 `make submit`）；通用集群负载高、版本不对 |

---

## 8. 对应原版讲义

| 材料 | 相对路径 | 页数 | 重点页码 |
|---|---|---|---|
| 课程总览讲义（lab 部分） | `90-原始PDF/15-213/lectures/01-overview.pdf` | **73** | 第 46–47 页（教材）、49–54 页（8 个 lab 的主题）、56 页（Lab0 忠告）、57 页（评分政策）、58 页（迟交）、59 页（shark）、62–64 页（Autolab）、65 页（recitation）、68 页（答疑）、69 页（bootcamp）、70 页（总评构成）、71 页（waitlist） |
| 课程大纲 | `90-原始PDF/15-213/labs/syllabus.pdf` | **13** | §6.2（GitHub Education）、§6.3（截止与迟交）、§6.6（评分）、§6.7（学术诚信） |
| CProgrammingLab 说明 | `90-原始PDF/15-213/labs/cprogramminglab.pdf` | **8** | 第 1 页（技能与日期）、2 页（资源与禁令）、3 页（Autolab 流程与 16 个文件）、4–5 页（数据结构与 7 个函数）、6 页（trace 与评分）、7 页（风格与 ASan）、8 页（提交） |

原始链接：

- 课程主页 <https://www.cs.cmu.edu/~213/>
- 课表 <https://www.cs.cmu.edu/~213/schedule.html>
- Labs 页 <https://www.cs.cmu.edu/~213/labs.html>
- Autolab <https://autolab.andrew.cmu.edu/courses/15213-f26>
- 学术诚信 <https://www.cs.cmu.edu/~213/academicintegrity.html>
- 代码风格 <https://www.cs.cmu.edu/~213/codeStyle.html>
- Lab 机器 <https://www.cs.cmu.edu/~213/labmachines.html>
- CS:APP 公开 lab 说明 <https://csapp.cs.cmu.edu/3e/labs.html>

> 待人工核对：`01-overview.pdf` 的页码按 PDF 页序（`=== [page N] ===`）；幻灯片页脚编号从第 51 页起与 PDF 页码相差 1（讲义自身有跳号），引用时以 PDF 页码为准。

---

## 9. 对应视频

**未找到官方公开录像。** 15-213 的 lecture 与 recitation 录像仅对 CMU 校内开放（Canvas / Panopto），公开页面上没有可访问的播放列表。Bootcamp 视频（`01-overview.pdf` 第 69 页列出 6 场）同样只对选课学生发布。

---

## 10. 本节复习

1. 8 个 lab 的名称与主题：CProgramming / Data / Bomb / Attack / Cache / Malloc / Tsh / Proxy（+ SFS）。
2. 只有 **L0** 的完整题目包公开（`cprogramminglab.pdf` + `cprogramminglab-handout.tar`），其余走 Autolab。
3. 分发链路：选课名单 → Autolab（Shibboleth）→ `autolab download` → 本地解包 → 提交评分。L4 起改用 GitHub Classroom 私有仓库。
4. 分数构成：正确性 + 性能 + 代码风格（TA 1:1）+ Parsons Puzzle（现场，约 10%）。
5. 总评：Labs 50%、Written 6%、Paper Quizzes 4%、Midterm 15%、Final 25%。
6. 迟交：5 天 grace day，每 lab 最多 2 天，之后每天 15%，超过 3 天不收。
7. Autolab 分数就是 lab 分数；本地跑分不作数。
8. 环境：shark 机器（`shark.ics.cs.cmu.edu`）；无账号时用 Docker + Ubuntu 22.04 近似。

---

## 11. 自我检查

**Q1.** 某同学 L4 Cache Lab 得了 85 分，迟交 5 天，此前已在该 lab 用掉 1 天 grace day。他的实得分是多少？如果他改迟交 6 天呢？

**Q2.** 为什么 L6 Tsh Lab 在 Nov 03 发布，而它依赖的 L18 System-Level I/O 在 Nov 05 才讲？这对你的学习安排意味着什么？

**Q3.** 讲义说「Autolab 上的分数就是你的 lab 分数」，同时又允许在 shark 机器上 `make submit`。这两句话矛盾吗？请解释 `make submit` 实际做了什么。

**Q4.** 为什么 L5 Malloc Lab 要拆成 L5a（checkpoint）与 L5b（final）两次提交？从「评分维度」的角度解释。

**Q5.** 一个 lab 同时有「代码风格分」和「Parsons Puzzle」，这两者考的是同一种能力吗？

<details>
<summary>参考答案</summary>

**A1.** 迟交 5 天、已用 1 天 grace：本 lab 还能再用 1 天（上限 2 天），所以 `g = 2`，`charged = 5 − 2 = 3`，`3 ≤ 3` 仍然收，扣 `3 × 15% = 45%`，实得 `85 × 0.55 = 46.75` 分。若改迟交 6 天：`charged = 4 > 3`，**不再收，得 0 分**。注意 grace day 是**全学期共享**的 5 天，这里「已用 1 天」指的是本 lab 已用的额度，全学期总额还要另外核算。

**A2.** 因为 lab 的发布日跟讲义有 1–2 讲的滞后，而 Tsh Lab 需要的知识横跨 L16（进程与 `fork`）、L17（信号与作业控制）、L18（文件描述符与重定向）。发布日定在 Nov 03 是为了让学生在 L17 讲完后立刻能动手，代价是 I/O 重定向那部分要边做边学。对你的安排意味着：**不要等 L18 讲完再开始 Tsh Lab**，可以先做进程与信号部分（`eval`、`waitfg`、信号处理），把重定向留到 L18 之后。

**A3.** 不矛盾。`make submit` 只是把 `make` 生成的 `.tar` **上传到 Autolab**，评分仍然在 Autolab 侧进行。它省掉的是「手动下载 tar 再拖到网页」这一步，而不是「本地评分」。所以「Autolab 分数就是 lab 分数」依然成立。

**A4.** 因为 L5 的评分有两个互相制约的维度：**正确性**与**性能（吞吐量 + 利用率）**。L5a 只考正确性 + 堆检查器，让学生先把「不崩、不漏、能合并」做对；L5b 才加性能阈值与代码风格分。分两次提交可以避免「为了追性能把正确性搞坏」这种常见失败模式，也给中途落后的学生一个止损点。

**A5.** 不是。**代码风格分**考的是可读性与工程规范（命名、注释、函数长度、`clang-format`），由 TA 人工评审；**Parsons Puzzle** 考的是**对程序结构的理解**——给你打乱顺序的代码行，你要能还原出正确的控制流与数据流。前者是「写得让人看得懂」，后者是「真的懂这段代码在干什么」。

</details>

---

## 12. 进一步学习

- 唯一公开 lab 的详细笔记：[[20-CMU-15-213/03-Lab实验笔记/01-CProgrammingLab笔记|CProgrammingLab 笔记]]
- 受限 lab 的说明与合法替代路径：[[20-CMU-15-213/03-Lab实验笔记/02-受限Lab说明|受限 Lab 说明]]
- 课程总览（含材料完整性盘点）：[[20-CMU-15-213/00-课程总览|CMU 15-213 - 课程总览]]
- 学习进度（lab 与讲次的时间对应）：[[20-CMU-15-213/04-学习进度|CMU 15-213 - 学习进度]]
- 课程目录（18 讲全表）：[[20-CMU-15-213/01-课程目录|CMU 15-213 - 课程目录]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 官方 labs 页：<https://www.cs.cmu.edu/~213/labs.html>
- 官方 schedule 页：<https://www.cs.cmu.edu/~213/schedule.html>
- CS:APP 公开 lab 说明：<https://csapp.cs.cmu.edu/3e/labs.html>
