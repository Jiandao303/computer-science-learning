---
course: CMU 15-213
course_name: Introduction to Computer Systems
semester: Fall 2026
lecture_id: L16
topic: Processes
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-213
  - 进程
  - fork
  - execve
  - 上下文切换
  - 系统调用
  - shell
---

# 进程（Processes）

## 1. 本节学习目标

- 能用“运行中程序的一个实例”定义进程，并说明进程提供的两个关键抽象：私有地址空间与逻辑控制流。
- 能解释上下文切换（context switch）在内核中如何发生：保存寄存器 → 调度 → 装载寄存器与切换地址空间。
- 能说出系统调用（system call）的机制与错误处理约定（返回 −1、设置 `errno`）。
- 能准确描述 `fork` 的“调用一次、返回两次”、地址空间复制（写时复制）、文件描述符共享。
- 能用进程图（process graph）判断一段 `fork` 代码的某个输出序列是否可行。
- 能区分僵尸进程（zombie）与孤儿进程（orphan），会用 `wait`/`waitpid` 回收子进程。
- 能解释 `execve` 做了什么（覆盖代码/数据/栈，保留 PID 与打开的文件），以及它与 `fork` 的组合如何构成 shell。

## 2. 前置知识

- [[15-213-12-Virtual-Memory-Details]]：地址空间、页表、写时复制（copy-on-write）——本节 `fork` 的优化直接建立在它之上。
- [[15-213-17-Exceptional-Control-Flow]] 会接续本节：异常表、信号。本节只提到“收到默认动作是终止的信号”。
- C 的指针、数组、字符串（`argv`/`envp` 的 `NULL` 结尾约定）。
- 命令行使用经验：`ps`、`kill`、`&` 后台运行。

## 3. 核心概念

- **Process（进程）**：一个正在运行的程序实例（an instance of a running program）。既不是“程序”，也不是“处理器”。
- **Private Address Space（私有地址空间）**：每个程序都以为自己独占主存，由虚拟内存机制提供。
- **Logical Control Flow（逻辑控制流）**：每个程序都以为自己独占 CPU，由上下文切换提供。
- **Physical Control Flow（物理控制流）**：CPU 从启动到关机逐条执行的指令序列。
- **Kernel（内核）**：常驻内存的操作系统代码。**不是独立进程**，而是作为某个已有进程的一部分运行。
- **Context Switch（上下文切换）**：控制流从一个进程转到另一个进程的机制。
- **Multitasking（多任务）**：单处理器上交错执行多个进程。
- **Multicore（多核）**：单芯片多个 CPU，共享主存与部分缓存。
- **Concurrent / Sequential（并发/顺序）**：两个进程的执行在时间上重叠即为并发。
- **System Call（系统调用）**：程序想在本进程之外产生效果时，向内核请求服务的手段。
- **`errno`**：系统级函数出错时设置的全局变量，说明失败原因。
- **Wrapper（包装函数）**：Stevens 风格的首字母大写函数（如 `Fork`），出错时打印并退出。
- **PID（Process ID）**：进程标识符。
- **Zombie（僵尸进程）**：已终止但父进程尚未回收的进程，仍占用退出状态等资源。
- **Orphan（孤儿进程）**：父进程先终止的子进程，由 `init`（PID 1）收养。
- **Reaping（回收）**：父进程用 `wait`/`waitpid` 取走子进程退出状态并让内核删除它。
- **Process Graph（进程图）**：用顶点表示语句执行、边表示先后关系的偏序图；任一拓扑排序都是一个可行的全序。
- **Shell（shell）**：代表用户运行程序的应用程序。

## 4. 通俗理解

最早的计算机一次只跑一个批处理作业（讲义第 4 页的 IBM 704，1957）。要让很多人高效共享一台机器（第 5 页的提问），操作系统给出了一个漂亮的骗局：**让每个程序都以为自己独占整台机器**。

骗局分两半。地址空间那一半由虚拟内存实现——每个进程有自己的页表，看到的都是从 0 开始的干净地址空间。CPU 那一半由上下文切换实现——内核在进程之间快速换手，每个进程都觉得自己一直在跑。

关键在于“换手”这件事本身。CPU 只会一条一条执行指令，程序里并没有写“现在去跑内核”。所以内核必须靠某种**陷入**机制接管控制权（这就是系统调用，以及下一讲的异常与信号）。一旦接管，内核就有机会做一件程序员看不见的事：把当前进程的寄存器存到内存里，把另一个进程的寄存器装回来，顺手换掉页表基址寄存器。这就是上下文切换的全部魔法。

本讲后半段把这些机制拼成一个真实程序——shell。你敲 `ls`，shell 做的事是：`fork` 出一个自己的副本，让副本 `execve` 变成 `ls`，自己则 `waitpid` 等它结束。三行代码，就是命令行的全部原理。理解了这三行，`fork` 那些看似诡异的输出顺序就都能用手画出来了。

## 5. 原理与推导

### 5.1 进程提供的两个抽象

讲义第 7 页：

| 抽象 | 程序的感觉 | 内核机制 |
|---|---|---|
| 私有地址空间 | 我独占主存 | 虚拟内存（virtual memory） |
| 逻辑控制流 | 我独占 CPU | 上下文切换（context switching） |

讲义称这是“计算机科学中最深刻的思想之一”，并强调进程**不等于**程序（program，磁盘上的静态文件），也**不等于**处理器（processor，硬件）。

第 8 页给出一个真实例子：在 `hammerheadshark` 上运行 `top`，系统有 425 个“task”，其中 7 个处于活动状态，每个用 PID、用户账号、命令名标识。

### 5.2 物理控制流与内核的接管

讲义第 9 页：CPU 从启动到关机，只是逐条读并执行机器指令。这个序列就是**物理控制流**。脚注说明：现代 CPU 会同时执行多条指令、乱序执行，但对程序员不可见。

第 10 页的关键论断：**内核不是独立进程，而是作为某个已有进程的一部分运行**。这句话解释了很多现象——比如为什么 `ps` 里看不到一个叫“kernel”的进程，以及为什么系统调用期间“当前进程”仍然是你的进程（只是运行在内核态）。

第 18 页提出本节的核心问题：“我们并没有在程序里写‘现在跑内核代码’，那内核怎么拿到控制权？”答案就是系统调用（以及中断、异常），图中画出了 `syscall` → `<kernel entry>` → 内核指令 → `<kernel exit>` 的插入。

### 5.3 上下文切换的四个步骤

讲义第 11–14 页用四张图讲单处理器上的切换：

1. **保存当前寄存器到内存**（第 12 页）：把正在运行的进程的寄存器值写进它的 `Saved registers` 区。
2. **调度下一个要执行的进程**（第 13 页）：内核决定谁上。
3. **装载保存的寄存器并切换地址空间**（第 14 页）：把新进程的寄存器值装回 CPU，同时换掉地址空间（实际就是换页表基址寄存器 CR3，见 [[15-213-11-Virtual-Memory-Concepts]] 的 PTBR）。

第 15 页补充多核情形：多个 CPU 在同一芯片上，共享主存与部分缓存，每个核可以执行不同进程，核上的调度也由内核完成。

为什么切换代价不小？因为切 CR3 会让 TLB 里的旧映射失效（除非 CPU 带 PCID/ASID 标签），新进程一开始要经历一批 TLB miss；再加上寄存器存取、cache 冷启动。这就是为什么“上下文切换是昂贵的”成了系统编程的常识。

### 5.4 并发的两种现实

讲义第 16 页（用户视角）：两个进程的执行在时间上重叠就叫**并发**（concurrent），否则是**顺序**（sequential）。图中 A 与 B 并发、A 与 C 并发，但 B 与 C 顺序。

第 17 页（单处理器现实）：其实同一时刻只有一个进程在跑，A 与 B 是**交错**（interleaved）而非真正并行。但**它们仍然可能互相干扰**——这一点在后面的并发编程（信号、线程）里会成为主要麻烦来源。

### 5.5 系统调用

讲义第 20 页给出 `fopen` 的实现链：

```c
// fopen.c
FILE *fopen(const char *fname, const char *mode) {
  int flags = mode2flags(mode);
  if (!flags) return NULL;
  int fd = open(fname, flags, DEFPERMS);
  if (fd == -1) return NULL;
  return fdopen(fd, mode);
}
```

```asm
// open.S
    .global open
open:
    mov $SYS_open, %eax
    syscall
    cmp $SYS_error_thresh, %rax
    ja  __syscall_error
    ret
```

要点：

- 库函数（`fopen`）最终落到一个薄薄的汇编包装（`open`），它把**系统调用号**放进 `%eax`，然后执行 `syscall` 指令。
- `syscall` 让 CPU 从用户态陷入内核态，内核根据 `%eax` 里的号分派到对应服务。
- 返回值若落在错误区间（`> SYS_error_thresh`，即 −4095..−1）就跳去设 `errno`。

第 21 页列了一张极长的系统调用清单（`accept`、`brk`、`clone`、`execve`、`fork` 在 x86-64 上其实是 `clone`、`wait4`、`write`……），意在说明：**你在用户态能做的一切“有外部效果”的事，背后都是这张表里的一项**。

### 5.6 系统调用的错误处理

讲义第 22 页：

- 几乎所有的系统级操作都可能失败，唯一例外是少数返回 `void` 的函数。
- 出错时大多数函数返回 **−1**，并把全局变量 **`errno`** 设为原因码。
- 必须显式检查。

```c
pid_t pid = fork();
if (pid == -1) {
    fprintf(stderr, "fork error: %s\n", strerror(errno));
    exit(1);
}
```

第 23 页的 `unix_error` 把这段重复代码封装：

```c
void unix_error(char *msg) {
    fprintf(stderr, "%s: %s\n", msg, strerror(errno));
    exit(1);
}
```

讲义提醒：**出错就退出并不总是合适的**（比如服务器应该记录错误继续服务）。

第 24 页再进一步，给出 Stevens 风格的首字母大写包装：

```c
pid_t Fork(void) {
    pid_t pid = fork();
    if (pid == -1)
        unix_error("Fork error");
    return pid;
}
```

这样 `pid = Fork();` 只会在成功时返回。讲义明确警告：**这不是真实应用该有的做法**，只是为了让课堂代码简洁（CS:APP 的 `csapp.c` 就是这样写的，注意它的 `unix_error` 退出码是 0，与常规的 1 不同）。

### 5.7 进程状态

讲义第 27 页，任一时刻进程处于四种状态之一：

| 状态 | 含义 |
|---|---|
| Running（运行） | 正在执行指令，或“若有足够多的核就能执行” |
| Blocked / Sleeping（阻塞/睡眠） | 必须等外部事件（通常是 I/O）才能继续 |
| Stopped（停止） | 被用户操作阻止执行（如 `control-Z`） |
| Terminated / Zombie（终止/僵尸） | 已结束，但父进程尚未收到通知 |

注意 Running 的定义包含“就绪但没核”的情况——这是单核多任务的关键。

### 5.8 终止进程

讲义第 28 页，三种终止原因：

1. 收到默认动作是终止的信号（下一讲详述）。
2. 从 `main` 返回。
3. 调用 `exit`。

```c
void exit(int status);
```

约定：正常返回 0，出错返回非 0。`main` 的返回值同样能设置退出状态。讲义的名句：“`exit` is called once but never returns.”

### 5.9 fork：调用一次，返回两次

讲义第 29 页：

```c
int fork(void);
```

- 对**子进程**返回 0，对**父进程**返回子进程的 PID。
- 子进程几乎是父进程的完整副本：
  - 得到父进程虚拟地址空间的**完全相同但独立**的副本。
  - 得到父进程打开的文件描述符的**副本**（注意：描述符表是复制的，但指向同一批打开文件）。
  - PID 不同。

第 30–31 页的“概念视图”：把执行状态（CPU 寄存器 + 内存）整体复制一份，一份标为 parent、一份标为 child，然后两者都从 `fork` 返回处继续。图下方的括号注释很重要：**优化手段是写时复制（copy-on-write），避免真的复制 RAM**。回忆 [[15-213-12-Virtual-Memory-Details]] 第 34–37 页：复制页表、把两边的页都标为只读，谁写谁触发缺页再复制那一页。

### 5.10 fork 的行为示例

讲义第 32–33 页：

```c
int main(int argc, char** argv) {
    pid_t pid;
    int x = 1;
    pid = Fork();
    if (pid == 0) {                      /* Child */
        printf("child : x=%d\n", ++x);
        return 0;
    }
    /* Parent */
    printf("parent: x=%d\n", --x);
    return 0;
}
```

运行三次得到不同顺序：

```
linux> ./fork
parent: x=0
child : x=2
linux> ./fork
child : x=2
parent: x=0
```

四个要点（第 33 页）：

1. **调用一次，返回两次**。
2. **并发执行**：无法预测父子谁先跑。
3. **地址空间重复但独立**：`fork` 返回时两边 `x` 都是 1；之后 `++x` 与 `--x` 互不影响，所以一个得 2、一个得 0。
4. **共享打开的文件**：`stdout` 在父子中是同一个（所以输出不会互相覆盖成乱码，但顺序不定）。

第 3 点是最容易搞错的：**不是**“父进程的 `x` 被改了”，而是各有一份。

### 5.11 用进程图推理输出顺序

讲义第 34–36 页介绍工具：

- 顶点 = 一条语句的执行。
- 边 `a → b` 表示 a 发生在 b 之前。
- 边可以标注变量当前值，`printf` 顶点标注输出。
- 图从一个无入边的顶点开始。
- **图的任一拓扑排序都是一个可行的全序**。

第 35 页为上面的 `fork.c` 画出图：`main → fork →`（分叉）`printf(child) → exit` 与 `printf(parent) → exit`。

第 36 页把图重贴标签为 a–f 并给出 `a b e c f d`，问这是否可行。答案：**不可行**，因为它不是拓扑排序（`c` 必须在 `f` 之前之类）。

这套方法的价值在于：不需要真的运行程序，就能判断某个输出序列“可能”还是“绝不可能”。

### 5.12 连续 fork 与嵌套 fork

**连续两次 fork（第 37 页）**：

```c
void fork2() {
    printf("L0\n");
    fork();
    printf("L1\n");
    fork();
    printf("Bye\n");
}
```

可行输出：

```
L0 L1 Bye Bye L1 Bye Bye
```

不可行输出：

```
L0 Bye L1 Bye L1 Bye Bye
```

为什么后者不可能？`L0` 之后一定先打印两个 `L1`（第一次 fork 的两个进程各打一个），然后才轮到 `Bye`。任何 `Bye` 出现在第二个 `L1` 之前都违反图中的先后约束。

**父进程中嵌套 fork（第 38 页）**：

```c
void fork4() {
    printf("L0\n");
    if (fork() != 0) {          /* 只有父进程进入 */
        printf("L1\n");
        if (fork() != 0) {
            printf("L2\n");
        }
    }
    printf("Bye\n");
}
```

- 不可行：`L0 L1 Bye Bye L2 Bye`
- 可行：`L0 Bye L1 Bye Bye L2`

**子进程中嵌套 fork（第 39 页）**：

```c
void fork5() {
    printf("L0\n");
    if (fork() == 0) {          /* 只有子进程进入 */
        printf("L1\n");
        if (fork() == 0) {
            printf("L2\n");
        }
    }
    printf("Bye\n");
}
```

- 不可行：`L0 Bye L1 L2`
- 可行：`L0 Bye L1 Bye Bye L2`

做题技巧：先数一共有几个进程（每次 `fork` 让进程数翻倍），再确认每个 `printf` 由哪些进程执行，最后用“谁在谁之后”的约束去排除序列。

### 5.13 回收子进程：僵尸与孤儿

讲义第 40 页：

- 进程终止后**仍占用系统资源**（退出状态、各种 OS 表项），称为**僵尸**（zombie）——“半死不活的活尸”。
- **回收**（reaping）由父进程对已终止的子进程执行（`wait`/`waitpid`），父进程拿到退出状态，内核随后删除僵尸。
- 若父进程未回收就终止，孤儿子进程应由 `init`（PID 1）回收。若连 `init` 都终止了……只能重启。
- 结论：只有**长期运行**的进程（shell、服务器）需要显式回收。

**僵尸示例（第 41 页）**：

```c
void fork7() {
    if (fork() == 0) {
        printf("Terminating Child, PID = %d\n", getpid());
        exit(0);
    } else {
        printf("Running Parent, PID = %d\n", getpid());
        while (1) ;        /* 父进程不回收 */
    }
}
```

`ps` 输出里子进程显示为 `<defunct>`：

```
 6639 ttyp9    00:00:03 forks
 6640 ttyp9    00:00:00 forks <defunct>
```

`kill 6639` 杀掉父进程后，僵尸被子进程的收养者 `init` 回收，`ps` 里消失。

**孤儿示例（第 42 页）**：

```c
void fork8() {
    if (fork() == 0) {
        printf("Running Child, PID = %d\n", getpid());
        while (1) ;        /* 子进程不退出 */
    } else {
        printf("Terminating Parent, PID = %d\n", getpid());
        exit(0);
    }
}
```

父进程退出后子进程仍在跑（`ps` 里能看到 `6676 forks`），必须显式 `kill 6676`。

### 5.14 wait 与 waitpid

讲义第 43 页：

```c
pid_t wait(int *status);
pid_t waitpid(pid_t pid, int *status, int options);
```

- `wait`：挂起当前进程，直到**某个**子进程终止；返回该子进程 PID，退出状态写入 `status`。
- `waitpid`：更灵活，可以等**指定**的子进程或进程组，也可以要求“没有可回收子进程时立即返回”。

**wait 示例（第 44 页）**：

```c
void fork9() {
    int child_status;
    if (fork() == 0) {
        printf("HC: hello from child\n");
        exit(0);
    } else {
        printf("HP: hello from parent\n");
        wait(&child_status);
        printf("CT: child has terminated\n");
    }
    printf("Bye\n");
}
```

可行输出：`HC HP CT Bye` 或 `HP HC CT Bye`。
不可行：`HP CT Bye HC`——因为 `wait` 返回意味着子进程已打印过 `HC`。

**状态码（第 45 页）**：`wait` 的返回值是子进程 PID；若 `status != NULL`，它指向的整数包含比 `exit` 参数**更多**的信息，必须用 `sys/wait.h` 的宏解码：

`WIFEXITED`、`WEXITSTATUS`、`WIFSIGNALED`、`WTERMSIG`、`WIFSTOPPED`、`WSTOPSIG`、`WIFCONTINUED`。

**多子进程示例（第 46 页）**：

```c
void fork10() {
    pid_t pid[N];
    for (i = 0; i < N; i++)
        if ((pid[i] = fork()) == 0)
            exit(100+i);
    for (i = 0; i < N; i++) {
        pid_t wpid = wait(&child_status);
        if (WIFEXITED(child_status))
            printf("Child %d terminated with exit status %d\n",
                   wpid, WEXITSTATUS(child_status));
        else
            printf("Child %d terminate abnormally\n", wpid);
    }
}
```

要点：多个子进程完成时，`wait` **按任意顺序**返回——所以打印顺序不确定。

**waitpid 指定顺序（第 47 页）**：把循环改成 `for (i = N-1; i >= 0; i--) waitpid(pid[i], ...)`，就能按固定顺序回收。这在 Tsh Lab 里是必需的。

### 5.15 execve：加载并运行程序

讲义第 48 页：

```c
int execve(char *filename, char *argv[], char *envp[]);
```

- 在当前进程中加载并运行：
  - 可执行文件 `filename`，可以是目标文件，也可以是以 `#!interpreter` 开头的脚本（如 `#!/bin/bash`）。
  - 参数列表 `argv`，约定 `argv[0] == filename`。
  - 环境变量列表 `envp`，形如 `"name=value"`（如 `USER=droh`），可用 `getenv`/`putenv`/`printenv` 访问。
- **覆盖代码、数据与栈**。
- **保留** PID、打开的文件、信号上下文。
- **调用一次，永不返回**——除非出错。

第 49 页的例子在子进程里执行 `/bin/ls -lt /usr/include`：

```c
if ((pid = Fork()) == 0) {
    if (execve(myargv[0], myargv, environ) < 0) {
        printf("%s: %s\n", myargv[0], strerror(errno));
        exit(1);
    }
}
```

`myargv` 三个元素加一个 `NULL` 结尾；`environ` 是全局变量，指向 `envp` 数组。

**新程序启动时的栈布局（第 50 页）**：从栈底到栈顶依次是环境变量字符串区、命令行参数字符串区、`envp[]` 指针数组（以 NULL 结尾）、`argv[]` 指针数组（以 NULL 结尾），然后是 `libc_start_main` 的栈帧。`main` 收到的三个参数分别在：`argc` 在 `%rdi`、`argv` 在 `%rsi`、`envp` 在 `%rdx`。

**execve 与进程内存布局（第 51 页）**：要加载新程序，内核必须

1. 丢弃旧程序的虚拟内存区域与页表；
2. 为新程序创建新的 VM 区域与页表：
   - 代码与已初始化数据由目标文件支撑（file-backed）；
   - `.bss` 与栈由匿名文件支撑（anonymous file，按需零填充）；
3. 把 PC 设为 `.text` 的入口点；Linux 随后按需缺页调入代码与数据页。

图中标注了各段的属性：共享库映射区（shared, file-backed）、运行时堆（private, demand-zero）、`.text`/`.data`（private, file-backed）、`.bss`（private, demand-zero）、用户栈（private, demand-zero）。这与 [[15-213-13-Dynamic-Memory-Allocation-Basic]] 第 4 页的堆起点图一致。

### 5.16 shell 的实现

讲义第 55–56 页：shell 是代表用户运行程序的应用程序。`sh`（Bourne, 1977）、`csh`/`tcsh`、`bash`（Linux 默认）。

第 56 页的 `shellex` 演示：只支持全路径命令名；`&` 表示后台运行；`quit` 退出。

**主循环（第 58 页）**：

```c
int main(int argc, char** argv) {
    char cmdline[MAXLINE];
    while (1) {
        printf("> ");
        fgets(cmdline, MAXLINE, stdin);
        if (feof(stdin)) exit(0);
        eval(cmdline);
    }
}
```

经典的“读—求值”循环。

**eval（第 58–66 页）**：

```c
void eval(char *cmdline) {
    char *argv[MAXARGS];
    char buf[MAXLINE];
    int bg;
    pid_t pid;

    strcpy(buf, cmdline);
    bg = parseline(buf, argv);       /* 解析，返回是否以 & 结尾 */
    if (argv[0] == NULL) return;     /* 空行 */

    if (!builtin_command(argv)) {
        if ((pid = Fork()) == 0) {           /* 子进程跑用户作业 */
            execve(argv[0], argv, environ);
            /* 走到这里说明 execve 失败 */
            printf("%s: %s\n", argv[0], strerror(errno));
            exit(127);
        }
        if (!bg) {                            /* 前台：等它结束 */
            int status;
            if (waitpid(pid, &status, 0) < 0)
                unix_error("waitfg: waitpid error");
        } else                                /* 后台：报 PID 继续 */
            printf("%d %s\n", pid, cmdline);
    }
}
```

这段代码就是 `fork` + `execve` + `waitpid` 的教科书组合：

- **内建命令**（`quit`）在当前进程里直接处理，不 fork。
- 其它命令：`fork` 出子进程，子进程立刻 `execve`（成功就再也不回来），父进程按前台/后台决定是否 `waitpid`。

**这个简化 shell 的 bug（第 66–67 页）**：它正确回收了**前台**作业，但**后台**作业终止后会变成僵尸，永远不会被回收——因为 shell 通常不退出。后果是耗尽内存，更可能是**耗尽 PID**。

修法（Tsh Lab 的核心内容）：用 `SIGCHLD` 信号处理函数在后台子进程终止时回收。这就接到下一讲 [[15-213-17-Exceptional-Control-Flow]]。

### 5.17 全讲总结

讲义第 67–68 页：

- 系统任一时刻有多个活动进程，单核上只有一个能执行，每个进程都以为自己独占处理器与私有内存。
- 创建进程：`fork`，一次调用、两次返回。
- 结束进程：`exit`，一次调用、不返回。
- 回收与等待：`wait` / `waitpid`。
- 加载并运行程序：`execve`（或其变体），一次调用、（通常）不返回。

## 6. 代码示例

### 6.1 官方课程代码

**系统调用包装（16-processes.pdf 第 20 页）**：

```asm
    .global open
open:
    mov $SYS_open, %eax
    syscall
    cmp $SYS_error_thresh, %rax
    ja  __syscall_error
    ret
```

**fork 示例（16-processes.pdf 第 32–33 页）**：

```c
int x = 1;
pid = Fork();
if (pid == 0) { printf("child : x=%d\n", ++x); return 0; }
printf("parent: x=%d\n", --x);
```

**僵尸演示（16-processes.pdf 第 41 页）**：`forks.c` 的 `fork7`，子进程 `exit(0)`、父进程死循环不回收，`ps` 显示 `<defunct>`。

**孤儿演示（16-processes.pdf 第 42 页）**：`fork8`，父进程退出、子进程死循环。

**wait 示例（16-processes.pdf 第 44 页）**：`fork9`，输出 `HC`/`HP`/`CT`/`Bye` 的可行与不可行序列。

**waitpid 按序回收（16-processes.pdf 第 47 页）**：`fork11` 从 `N-1` 递减调用 `waitpid(pid[i], ...)`。

**shell 的 eval（16-processes.pdf 第 58–66 页）**：`shellex.c`，见 5.16 节完整代码。

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

最小 shell（补上后台回收，对应讲义第 66 页指出的 bug）：

```c
/* 非官方示例：fork + execve + waitpid 的最小 shell，含 SIGCHLD 回收 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <signal.h>
#include <sys/wait.h>

extern char **environ;

/* 后台子进程终止时回收，避免僵尸 */
static void sigchld_handler(int sig) {
    (void)sig;
    int saved = errno;                 /* 处理函数里要保护 errno */
    pid_t pid;
    while ((pid = waitpid(-1, NULL, WNOHANG)) > 0)
        ;                              /* 有多少收多少 */
    errno = saved;
}

int main(void) {
    char line[1024];
    struct sigaction sa = {0};
    sa.sa_handler = sigchld_handler;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = SA_RESTART;          /* 让被中断的 read 自动重启 */
    sigaction(SIGCHLD, &sa, NULL);

    while (1) {
        printf("> ");
        fflush(stdout);
        if (!fgets(line, sizeof line, stdin)) break;

        char *argv[64];
        int argc = 0, bg = 0;
        char *tok = strtok(line, " \t\n");
        while (tok && argc < 63) { argv[argc++] = tok; tok = strtok(NULL, " \t\n"); }
        argv[argc] = NULL;
        if (argc == 0) continue;
        if (argc > 0 && strcmp(argv[argc-1], "&") == 0) { bg = 1; argv[--argc] = NULL; }
        if (strcmp(argv[0], "quit") == 0) break;

        pid_t pid = fork();
        if (pid == 0) {
            execve(argv[0], argv, environ);
            fprintf(stderr, "%s: %s\n", argv[0], strerror(errno));
            _exit(127);                /* 注意用 _exit，不刷新父进程的 stdio 缓冲 */
        } else if (pid < 0) {
            fprintf(stderr, "fork: %s\n", strerror(errno));
        } else {
            if (!bg) waitpid(pid, NULL, 0);
            else     printf("[%d] %s\n", (int)pid, argv[0]);
        }
    }
    return 0;
}
```

两个细节值得注意：

- 子进程用 `_exit` 而不是 `exit`。`fork` 之后父子共享 stdio 缓冲区的内容，`exit` 会刷新缓冲区导致输出重复（这是 `fork` 与 `printf` 组合的经典坑）。
- 信号处理函数里保存并恢复 `errno`，因为 `waitpid` 可能改写它，而处理函数返回后原代码还要用 `errno`。

用进程图判断输出（可对照讲义第 37 页的 `fork2`）：

```c
/* 非官方示例：三个 fork 会产生 8 个进程，共 8 行 Bye */
#include <stdio.h>
#include <unistd.h>

int main(void) {
    printf("L0\n");
    fork(); printf("L1\n");
    fork(); printf("L2\n");
    fork(); printf("Bye\n");
    return 0;
}
```

统计规律：`n` 次 `fork` → `2^n` 个进程；若每次 fork 后都打印一个标签，则该标签出现 `2^(n-1)` 次。可以配合 `./a.out | sort | uniq -c` 验证。

观察写时复制（Linux 上可用 `/proc/self/statm` 或 `smaps`）：

```bash
# 非官方示例：fork 之后父子共享物理页，写入才复制
gcc -O0 -o cow cow.c && ./cow
# 在程序里 fork 前后各读一次 /proc/self/statm 的第二个字段（resident pages），
# 若 fork 后立刻读，父子 RSS 之和不会翻倍，说明页是共享的。
```

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| 程序（program） | 进程（process） | 前者是磁盘上的静态可执行文件，后者是它的一个运行实例；同一程序可对应多个进程 |
| 进程 | 线程（thread） | 进程有独立地址空间；线程共享地址空间（后续课程内容） |
| 内核 | 进程 | 内核**不是**独立进程，它作为某个进程的一部分运行 |
| `fork` | `execve` | 前者复制当前进程（一次调用两次返回）；后者在当前进程中加载新程序（一次调用不返回） |
| 僵尸 | 孤儿 | 前者是“子死父未收”；后者是“父死子还在”，由 `init` 收养 |
| `wait` | `waitpid` | 前者等任意子进程；后者可指定 PID、可非阻塞（`WNOHANG`） |
| 退出状态 | 信号编号 | 前者由 `exit`/`return` 给出，用 `WEXITSTATUS` 取；后者表示被信号杀死，用 `WTERMSIG` 取 |
| 并发 | 并行 | 并发是执行在时间上重叠（单核交错也算）；并行是真正同时执行（需要多核） |
| 进程图 | 拓扑排序 | 图记录偏序约束；任一拓扑排序都是一个可行的实际执行顺序 |
| `exit` | `_exit` | 前者刷新 stdio 缓冲、执行 atexit；后者直接陷入内核。`fork` 后的子进程应用 `_exit` |

## 8. 对应原版讲义

- PDF 相对路径：`90-原始PDF/15-213/lectures/16-processes.pdf`
- 总页数：68 页
- 重点页码：
  - 标题页（16th Lecture, October 27, 2026）：第 2 页
  - 今日大纲：第 3 页
  - 早期批处理（IBM 704, 1957）：第 4 页
  - 多道处理与多进程：第 6 页
  - 进程定义与两个抽象：第 7 页
  - `top` 实例（425 tasks）：第 8 页
  - 物理控制流：第 9 页
  - 内核不是独立进程 + 上下文切换：第 10 页
  - 单处理器切换四步：第 11–14 页
  - 多核：第 15 页
  - 并发 vs 顺序（用户视角/单核现实）：第 16–17 页
  - 内核如何接管（syscall）：第 18 页
  - 系统调用与 `open.S`：第 20 页
  - 系统调用全表：第 21 页
  - 错误处理与 `errno`：第 22 页
  - `unix_error`：第 23 页
  - Stevens 包装：第 24 页
  - `getpid`/`getppid`：第 26 页
  - 四种进程状态：第 27 页
  - `exit`：第 28 页
  - `fork` 语义：第 29 页
  - `fork` 概念视图与 COW：第 30–31 页
  - `fork` 示例与四个要点：第 32–33 页
  - 进程图：第 34–36 页
  - 两次 fork（`fork2`）：第 37 页
  - 父进程嵌套（`fork4`）：第 38 页
  - 子进程嵌套（`fork5`）：第 39 页
  - 僵尸与回收：第 40 页
  - 僵尸实例（`fork7`）：第 41 页
  - 孤儿实例（`fork8`）：第 42 页
  - `wait`/`waitpid`：第 43 页
  - `wait` 示例（`fork9`）：第 44 页
  - 状态码宏：第 45 页
  - 多子进程（`fork10`）：第 46 页
  - `waitpid` 指定顺序（`fork11`）：第 47 页
  - `execve` 语义：第 48 页
  - `execve` 示例：第 49 页
  - 新程序栈布局：第 50 页
  - `execve` 与内存布局：第 51 页
  - shell 历史：第 55 页
  - `shellex` 演示：第 56 页
  - 主循环：第 58 页
  - `eval` 逐行讲解：第 58–66 页
  - 简化 shell 的 bug（后台僵尸）：第 66–67 页
  - 总结：第 67–68 页
- 原始链接：https://www.cs.cmu.edu/~213/lectures/16-processes.pdf
- 待人工核对：自第 51 页起，PDF 页码与幻灯片印的编号相差 1（PDF 第 51 页印 “52”），引用时以 PDF 页码为准。

## 9. 对应视频

未找到官方公开录像。

## 10. 本节复习

- 进程 = 运行中程序的实例；两个抽象：私有地址空间（虚拟内存）+ 逻辑控制流（上下文切换）。
- 内核不是独立进程，靠 syscall/异常插入控制流。
- 上下文切换三步：存寄存器 → 调度 → 装寄存器 + 换地址空间（换 CR3，TLB 会受影响）。
- 系统调用：`%eax` 放调用号、`syscall` 陷入、出错返回 −1 并设 `errno`。
- 四种进程状态：Running / Blocked / Stopped / Zombie。
- `fork` 一次调用两次返回（子 0、父 子PID）；地址空间独立复制（COW 优化）；文件描述符共享。
- 进程图：任一拓扑排序都是可行输出；不可行的序列一定违反某条边。
- `n` 次 `fork` 产生 `2^n` 个进程。
- 僵尸（子死父未收）需要 `wait`/`waitpid`；孤儿（父死子活）由 `init` 收养。
- `execve` 覆盖代码/数据/栈，保留 PID 与打开文件，正常不返回。
- shell = 读循环 + `fork` + `execve` + `waitpid`；后台作业需要 `SIGCHLD` 才能回收。

## 11. 自我检查

1. 内核为什么“不是独立进程”？这对理解上下文切换有什么帮助？
2. 下面的程序会打印几行 `Bye`？一共创建了多少个进程？
   ```c
   printf("L0\n"); fork(); printf("L1\n"); fork(); printf("Bye\n");
   ```
3. `fork` 之后父子进程的 `x` 为什么互不影响，而 `stdout` 却是共享的？这两件事分别对应 `fork` 复制了什么、没复制什么？
4. `fork9` 中输出 `HP CT Bye HC` 为什么不可能？
5. 讲义第 66 页指出简化 shell 有 bug。这个 bug 的具体表现是什么？为什么前台作业没问题？

<details>
<summary>参考答案</summary>

1. 因为内核代码没有自己独立的地址空间与进程上下文，它是**借用**当前进程的上下文运行的：系统调用或中断发生时，CPU 陷入内核态，仍在同一个进程的地址空间里（内核页被映射在高地址区），只是权限提升。理解这一点就明白上下文切换为什么是“在某个进程的内核态里”完成的——正是当前进程在跑内核代码时，才有机会把它的寄存器存起来、把别人的装回去。

2. 2 次 `fork`，产生 `2^2 = 4` 个进程，共打印 4 行 `Bye`（每个进程各打一行）。`L0` 只打 1 次（在第一次 fork 之前），`L1` 打 2 次。

3. `x` 是进程地址空间里的一个变量，`fork` 复制了**整个地址空间**（概念上完整复制，实际用 COW），所以父子各有一份 `x`，之后 `++x`/`--x` 互不干扰。`stdout` 是**打开的文件描述符**，`fork` 复制的是描述符表（每个进程一份表），但表项指向的是**同一个打开文件对象**（同一个文件偏移、同一套缓冲），所以父子写的是同一个流。讲义第 33 页把这两条并列为“duplicate but separate address space”和“shared open files”。

4. 因为 `wait(&child_status)` 只有在**某个子进程已经终止**时才会返回，而子进程在 `exit(0)` 之前一定会先执行 `printf("HC: ...")`。所以 `CT` 一定在 `HC` 之后。`HP CT Bye HC` 让 `CT` 出现在 `HC` 之前，违反进程图中 `HC → CT` 这条边，因此不可行。

5. 后台作业（以 `&` 结尾）终止后不会被回收：shell 只在前台分支调用 `waitpid`，后台分支只是打印 PID 就继续循环了。这些后台子进程终止后变成僵尸，而 shell 长期不退出，僵尸会一直累积，最终耗尽内存（更可能是耗尽 PID）。前台作业没问题是因为父进程立刻 `waitpid` 把它回收了。修法是在 `SIGCHLD` 处理函数里循环 `waitpid(-1, NULL, WNOHANG)`。

</details>

## 12. 进一步学习

- 下一讲：[[15-213-17-Exceptional-Control-Flow]]（异常表、信号、`SIGCHLD` 与 `sigaction`）
- 前一讲：[[15-213-15-Code-Optimization]]
- 相关实验：[[00-Lab总览]]（Tsh Lab 就是本节内容的完整工程化：作业控制、前后台、信号处理）
- 课程总览：[[20-CMU-15-213/00-课程总览|CMU 15-213 - 课程总览]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Process、Context Switch、Fork、Exec、File Descriptor）
- CSAPP 第 3 版 8.2–8.4 节；8.4 节末尾的 `shellex` 完整代码（书中 p.753 起）建议亲手敲一遍并在 `fork`/`execve`/`waitpid` 三处下断点观察。
