---
course: CMU 15-213
course_name: Introduction to Computer Systems
semester: Fall 2026
lecture_id: L17
topic: Exceptional Control Flow
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-213
  - 异常控制流
  - 异常
  - 信号
  - SIGCHLD
  - 进程组
  - 竞态
---

# 异常控制流（Exceptional Control Flow）

## 1. 本节学习目标

- 能说出为什么跳转、分支、调用、返回这四种机制不足以构建有用的系统，从而引出异常控制流（ECF）。
- 能按同步/异步、返回地址三个维度区分中断（interrupt）、陷阱（trap）、故障（fault）、中止（abort）。
- 能解释异常表（exception table / interrupt vector）的索引机制与系统调用的寄存器约定。
- 能说明信号的发送、待处理（pending）、阻塞（blocked）、接收全过程，以及“信号不排队”的后果。
- 能写出符合 G0–G5 六条准则的安全信号处理函数。
- 能诊断并修复 `SIGCHLD` 处理中的三类经典错误：只 `wait` 一次、竞态、忙等。
- 能用 `sigsuspend` 原子地“解除阻塞并等待”。

## 2. 前置知识

- [[15-213-16-Processes]]：`fork`、`execve`、`wait`/`waitpid`、僵尸进程、简化 shell 的后台僵尸 bug（本讲正是从修这个 bug 开始）。
- [[15-213-11-Virtual-Memory-Concepts]]：缺页（page fault）作为 fault 类异常的典型例子。
- [[15-213-05-Machine-Programming-III-Procedures]]：调用约定（`%rdi`、`%rsi`…、返回值在 `%rax`），因为系统调用复用了它。
- C 的 `volatile`、`sig_atomic_t` 类型概念。

## 3. 核心概念

- **ECF（Exceptional Control Flow，异常控制流）**：程序控制流因系统状态变化而偏离正常顺序的机制总称。
- **Exception（异常）**：响应某个事件（处理器状态变化）而将控制转移给 OS 内核。
- **Exception Table / Interrupt Vector（异常表/中断向量）**：以异常号为下标的跳转表，第 k 项指向处理程序 k。
- **Interrupt（中断）**：异步异常，来自处理器外部，处理完返回**下一条**指令。
- **Trap（陷阱）**：同步异常，**有意**触发，返回**下一条**指令；系统调用与断点属于此类。
- **Fault（故障）**：同步异常，**无意**但可能可恢复，返回时**重新执行**当前指令；缺页属于此类。
- **Abort（中止）**：同步异常，无意且不可恢复，终止当前程序。
- **Signal（信号）**：通知进程系统中发生了某类事件的小消息，只含 ID 与“到达”这一事实。
- **Pending（待处理）**：已发送但尚未被接收的信号。
- **Blocked / Signal Mask（阻塞/信号掩码）**：进程可以选择暂不接收某些信号。
- **Process Group（进程组）**：每个进程属于且仅属于一个进程组；`ctrl-c` 发给前台进程组的所有进程。
- **Signal Handler（信号处理函数）**：用户级函数，安装（install）后在被捕获（catch）时执行。
- **Async-Signal-Safe（异步信号安全）**：可重入或不可被信号中断的函数；POSIX 保证 117 个。
- **Race Condition（竞态条件）**：结果依赖不可控的执行交错。
- **`volatile`**：告诉编译器该变量可能被意外修改，不要缓存在寄存器里。
- **`sig_atomic_t`**：保证原子读写的整数类型，适合做标志。
- **`sigsuspend`**：原子地“设置信号掩码并挂起”，消除“检查—挂起”之间的竞态窗口。
- **Nonlocal Jump（非局部跳转）**：`setjmp`/`longjmp`，由 C 运行时库实现（讲义仅在层级图中提及）。

## 4. 通俗理解

到目前为止，程序改变执行顺序只有四种手段：跳转、分支、调用、返回。它们都只对**程序自身的状态**作出反应。但真实系统必须对**系统状态**作出反应：磁盘数据到了、网卡来了包、用户按下 Ctrl-C、定时器到期、除零、缺页。这些事件与当前执行到哪条指令无关，程序自己也无法预判。

于是硬件和操作系统联合提供了第四类机制：**异常控制流**。它像一次“强行插入的调用”——CPU 在执行 `I_curr` 时被拽去执行内核里的处理程序，处理完再决定回到 `I_next`（下一条）、回到 `I_curr`（重试当前这条），还是干脆终止进程。

如果说异常是硬件与内核之间的握手，信号就是内核与应用程序之间的握手。内核收到“子进程死了”这件事，转手给你发一个 `SIGCHLD`；你的程序在任意两条指令之间被拽去执行处理函数，执行完再回到原处。这种“同一进程里两条并发流动”的模型，正是本节所有麻烦的根源：处理函数与主程序共享全局变量，却以不可预测的时机交错执行。

理解了这一点，本节后半段的六条准则、三类 bug、`sigsuspend` 的原子性就都不是死记硬背，而是同一个道理的推论：**任何“先检查、后动作”的代码，如果中间可能被信号插入，就是错的**。

## 5. 原理与推导

### 5.1 为什么需要 ECF

讲义第 7–8 页：

- CPU 从启动到关机只是逐条读并执行指令，这就是**物理控制流**。
- 至今我们见过的改变控制流的机制只有两种：跳转/分支、调用/返回。它们都只对**程序状态**的变化作出反应。
- 但有用的系统必须能对**系统状态**的变化作出反应：
  - 磁盘或网卡的数据到达
  - 指令除以零
  - 用户按 Ctrl-C
  - 系统定时器到期
- 所以系统需要“异常控制流”机制。

### 5.2 ECF 的四个层次

讲义第 9 页（第 22 页重复一次并标注实现者）：

| 层次 | 机制 | 实现者 |
|---|---|---|
| 1（最低） | 异常（exceptions） | 硬件 + OS 内核软件 |
| 2 | 进程上下文切换 | OS 软件 + 硬件定时器 |
| 3 | 信号（signals） | OS 软件 + 应用软件 |
| 4（最高） | 非局部跳转 `setjmp`/`longjmp` | C 运行时库 |

这张表的价值在于建立“谁负责什么”的心智模型：越往下越依赖硬件，越往上越依赖软件。

### 5.3 异常的定义与异常表

讲义第 11 页：

> 异常（exception）是响应某个事件（即处理器状态的变化）而将控制转移给 OS 内核。

- 内核 = OS 中常驻内存的部分（回顾 [[15-213-16-Processes]] 第 10 页：内核不是独立进程）。
- 事件例子：除零、算术溢出、缺页、I/O 请求完成、输入 Ctrl-C。
- 处理程序完成后有三种去向：
  - 返回 `I_current`（重新执行当前指令）
  - 返回 `I_next`（执行下一条）
  - 终止（abort）

**异常表（第 12 页）**：每类事件有唯一的**异常号 k**，k 是**异常表**（也叫中断向量，interrupt vector）的下标，第 k 项是处理程序 k 的代码地址。硬件在异常发生时用 k 查表跳转，无需软件搜索——这就是它能做到极低延迟的原因。

### 5.4 异常的分类

讲义第 13 页的分类树：

```
                ECF
       ┌─────────┴─────────┐
  Asynchronous          Synchronous
  (异步)                 (同步)
       │              ┌──────┼──────┐
  Interrupts       Traps  Faults  Aborts
   (中断)          (陷阱)  (故障)  (中止)
```

**异步异常：中断（第 14 页）**

- 由**处理器外部**的事件引起，通过设置处理器的**中断引脚**（interrupt pin）指示。
- 处理程序返回时回到**下一条**指令（因为当前指令已经完整执行）。
- 例子：
  - **定时器中断**：外部定时器芯片每隔几毫秒触发一次；内核靠它从用户程序手里夺回控制权（这是抢占式多任务的基础）。
  - 外部设备的 **I/O 中断**：键盘按 Ctrl-C、网络包到达、磁盘数据到达。

**同步异常（第 15 页）**：由**执行某条指令**引起，共三类。

| 类型 | 是否有意 | 可恢复性 | 返回行为 | 例子 |
|---|---|---|---|---|
| Trap（陷阱） | 有意 | — | 返回 `I_next` | 系统调用、gdb 断点 |
| Fault（故障） | 无意 | 可能可恢复 | **重新执行**当前指令，或终止 | 缺页（可恢复）、保护故障（不可恢复）、浮点异常 |
| Abort（中止） | 无意 | 不可恢复 | 终止当前程序 | 非法指令、奇偶校验错、机器检查 |

记忆要点：**trap 是“故意踩的陷阱”**（`syscall` 指令就是主动触发），**fault 是“出了故障”**，**abort 是“直接报废”**。

### 5.5 系统调用是 trap

讲义第 16 页列出 x86-64 系统调用号：

| 号 | 名字 | 功能 |
|---|---|---|
| 0 | `read` | 读文件 |
| 1 | `write` | 写文件 |
| 2 | `open` | 打开文件 |
| 3 | `close` | 关闭文件 |
| 4 | `stat` | 取文件信息 |
| 57 | `fork` | 创建进程 |
| 59 | `execve` | 执行程序 |
| 60 | `_exit` | 终止进程 |
| 62 | `kill` | 向进程发信号 |

第 17–18 页给出 `__open` 的反汇编：

```asm
00000000000e5d70 <__open>:
...
e5d79:   b8 02 00 00 00      mov  $0x2,%eax      # open is syscall #2
e5d7e:   0f 05               syscall             # Return value in %rax
e5d80:   48 3d 01 f0 ff ff   cmp  $0xfffffffffffff001,%rax
...
e5dfa:   c3                  retq
```

寄存器约定（第 17 页）：

- `%rax`：系统调用号（这里是 2 = `open`）
- `%rdi`、`%rsi`、`%rdx`、`%r10`、`%r8`、`%r9`：参数（注意第 4 个参数用 `%r10` 而不是 `%rcx`，因为 `syscall` 指令会覆盖 `%rcx`）
- `%rax`：返回值；**负值表示错误，其绝对值就是 `errno`**

第 18 页对比“像函数调用”与“不像函数调用”：

**像函数调用**：控制转移；返回后执行下一条指令；按调用约定传参；结果在 `%rax`。

**重要区别**：由**内核**执行、**权限不同**（内核态 vs 用户态）、`cmp $0xfffffffffffff001` 检查的是“返回值落在 −4095..−1 区间”、使用 `errno` 而非直接返回错误码。

### 5.6 故障的两个例子

**可恢复的缺页（第 19 页）**：

```c
int a[1000];
main() { a[500] = 13; }
```

```asm
80483b7:  c7 05 10 9d 04 08 0d   movl $0xd,0x8049d10
```

流程：用户写内存 → 该页当前在磁盘上 → 触发**缺页异常** → 内核把页从磁盘复制到内存 → **返回并重新执行 `movl`**。注意是重新执行，不是执行下一条——这正是 fault 的定义特征。

**不可恢复的非法引用（第 20 页）**：

```c
int a[1000];
main() { a[5000] = 13; }
```

流程：用户写内存 → 缺页异常 → 内核检测到地址非法 → **向进程发送 `SIGSEGV`** → 进程以 “segmentation fault” 退出。

这两个例子的对比非常好：同一个异常类型（page fault），因为地址是否合法，走向完全不同的结局。这也解释了为什么段错误的报错信息总是来自内核而不是你的代码。

### 5.7 回到 shell 的 bug

讲义第 4 页与第 23 页重复提出 [[15-213-16-Processes]] 结尾的问题：简化 shell 正确回收前台作业，但**后台作业**终止后变成僵尸，永远不会被回收，因为 shell 通常不退出。后果：耗尽内存，更可能**耗尽 PID**。

第 24 页给出解法：**异常控制流**。内核会在后台进程完成时打断常规处理来通知我们；在 Unix 里这个通知机制叫**信号**。

### 5.8 信号的定义与常见类型

讲义第 25 页：

> 信号是通知进程系统中发生了某类事件的小消息。

- 类似异常与中断。
- 由内核发送（有时是应另一个进程的请求）给某个进程。
- 信号类型用小整数 ID 标识（1–30）。
- **信号里唯一的信息就是它的 ID 以及“它到了”这个事实**——没有参数、没有附加数据。

| ID | 名字 | 默认动作 | 对应事件 |
|---|---|---|---|
| 2 | `SIGINT` | 终止 | 用户按 ctrl-c |
| 9 | `SIGKILL` | 终止 | 杀死程序（**不可覆盖、不可忽略**） |
| 11 | `SIGSEGV` | 终止 | 段违规 |
| 14 | `SIGALRM` | 终止 | 定时器信号 |
| 17 | `SIGCHLD` | **忽略** | 子进程停止或终止 |

注意 `SIGCHLD` 的默认动作是**忽略**——这就是为什么默认情况下子进程终止后你什么都不做也不会崩，但僵尸会一直留着（忽略 ≠ 回收）。

### 5.9 发送信号

讲义第 26 页：

- 内核通过**更新目标进程上下文中的某些状态**来发送信号。
- 内核发送信号的两种原因：
  1. 检测到系统事件，如除零（`SIGFPE`）或子进程终止（`SIGCHLD`）。
  2. 另一个进程调用了 `kill` 系统调用，显式请求内核向目标进程发信号。

第 27–31、35 页用一组动画图说明：内核为**每个进程**维护 `pending` 与 `blocked` 两个位向量。发送 = 置 `pending` 的第 k 位；接收 = 清该位。

### 5.10 接收信号与三种反应

讲义第 32 页：

- 目标进程**接收**信号，是指它被内核强制对信号作出某种反应。
- 三种可能的反应：
  1. **忽略**（ignore）：什么都不做。
  2. **终止**进程（可选产生 core dump）。
  3. **捕获**（catch）：执行用户级函数，即**信号处理函数**（signal handler）。

图中画出四步：(1) 进程收到信号 → (2) 控制转到处理函数 → (3) 处理函数运行 → (4) 处理函数返回，回到被中断处的**下一条**指令。

### 5.11 pending 与 blocked：信号不排队

讲义第 33 页，这是本节最重要的性质：

- 信号是 **pending** 的，如果它已发送但尚未被接收。
- **每种类型最多只能有一个 pending 信号。**
- **信号不排队**（signals are not queued）：若进程已有一个类型 k 的 pending 信号，后续发来的同类型信号**直接丢弃**。
- 进程可以**阻塞**（block）某些信号的接收：被阻塞的信号仍可被发送，但要等解除阻塞后才被接收。
- 有些信号**不能被阻塞**（`SIGKILL`、`SIGSTOP`），有些只能在由其它进程发送时被阻塞（`SIGSEGV`、`SIGILL` 等）。
- **一个 pending 信号最多被接收一次。**

第 34 页说明实现：内核在每个进程的上下文里维护 `pending` 与 `blocked` 两个**位向量**：

- `pending`：发送类型 k 时置位 k，接收类型 k 时清位 k。
- `blocked`：可用 `sigprocmask` 设置/清除，也叫**信号掩码**（signal mask）。

“不排队”这个性质有一个非常实际的后果：**不能用信号来数事件**。比如 5 个子进程几乎同时终止，内核可能只留下一个 `SIGCHLD`，你的处理函数只被调用一次——这就是 5.15 节 bug 的根源。

### 5.12 进程组

讲义第 36 页：

- 每个进程属于且仅属于一个**进程组**。
- 图中：shell（pid=10, pgid=10）；前台作业进程组 20（pid=20 是组长，pid=21、22 也在组 20）；后台作业 #1 组 32；后台作业 #2 组 40。
- `getpgrp()` 返回当前进程的进程组；`setpgid()` 改变某进程的进程组。

进程组的意义在于**批量投递**：终端的 Ctrl-C 发给整个前台进程组，而不是某个进程。

### 5.13 用 kill 程序与键盘发送信号

**`/bin/kill`（第 37 页）**：

```
linux> /bin/kill -9 24818        # 给进程 24818 发 SIGKILL
linux> /bin/kill -9 -24817       # 给进程组 24817 的每个进程发 SIGKILL
```

注意第二个参数前面的负号表示“这是一个进程组”。例子中 `./forks 16` 创建了两个子进程 24818、24819，都在组 24817；`kill -9 -24817` 之后 `ps` 里两者都消失了。

**键盘（第 38 页）**：按 ctrl-c / ctrl-z 会让内核向前台进程组的**每个**进程发送 `SIGINT` / `SIGTSTP`。

- `SIGINT` 默认动作：终止每个进程。
- `SIGTSTP` 默认动作：停止（挂起）每个进程。

第 39 页给出 `ctrl-z` 与 `fg` 的实例，并解释 `ps w` 的 `STAT` 列：

- 首字母：`S` 睡眠、`T` 停止、`R` 运行。
- 第二字母：`s` 会话首进程、`+` 属于前台进程组。

`ctrl-z` 后两个 `forks` 进程都变成 `T`；`fg` 恢复后按 `ctrl-c` 全部终止。

**用 `kill` 函数（第 40 页）**：

```c
void fork12() {
    pid_t pid[N];
    for (i = 0; i < N; i++)
        if ((pid[i] = fork()) == 0)
            while (1) ;                 /* 子进程死循环 */
    for (i = 0; i < N; i++) {
        printf("Killing process %d\n", pid[i]);
        kill(pid[i], SIGINT);
    }
    for (i = 0; i < N; i++) {
        pid_t wpid = wait(&child_status);
        if (WIFEXITED(child_status))
            printf("Child %d terminated with exit status %d\n",
                   wpid, WEXITSTATUS(child_status));
        else
            printf("Child %d terminated abnormally\n", wpid);
    }
}
```

注意这里走的是 `else` 分支：被信号杀死的子进程**不是**正常退出，`WIFEXITED` 为假，要用 `WTERMSIG` 才能知道是哪个信号。

### 5.14 接收信号的精确算法

讲义第 41–42 页，这是本节最“可执行”的一段：

> 假设内核正从异常处理程序返回，准备把控制权交给进程 p。

1. 计算 `pnb = pending & ~blocked`，即进程 p 的**待处理且未被阻塞**的信号集合。
2. 若 `pnb == 0`：把控制权交给 p 逻辑流中的下一条指令。
3. 否则：
   - 选出 `pnb` 中**最小的非零位 k**，强制 p 接收信号 k，触发相应动作；
   - 对 `pnb` 中所有非零位重复；
   - 然后把控制权交给 p 逻辑流中的下一条指令。

“选最小位”这个细节说明信号的接收**按编号顺序**，而不是按到达顺序。所以 `SIGINT`（2）总是先于 `SIGCHLD`（17）被处理。

**默认动作（第 43 页）** 三类之一：终止进程；停止进程直到被 `SIGCONT` 重启；忽略。

### 5.15 安装处理函数

讲义第 45 页：

```c
handler_t *signal(int signum, handler_t *handler);
```

`handler` 的三种取值：

- `SIG_IGN`：忽略该类型信号。
- `SIG_DFL`：恢复默认动作。
- 其它：用户级处理函数的地址。

术语：把处理函数注册进去叫**安装**（install），执行它叫**捕获**（catch）或**处理**（handle）。处理函数执行 `return` 后，控制回到被信号打断的那条指令之后的**下一条**。

**示例（第 46 页）**：

```c
void sigint_handler(int sig) {
    printf("So you think you can stop the bomb with ctrl-c, do you?\n");
    sleep(2);
    printf("Well...");
    fflush(stdout);
    sleep(1);
    printf("OK. :-)\n");
    exit(0);
}
int main(int argc, char** argv) {
    if (signal(SIGINT, sigint_handler) == SIG_ERR)
        unix_error("signal error");
    pause();
    return 0;
}
```

（这段代码用 `printf` 是**不安全**的，第 55–56 页会给出安全版本。）

### 5.16 处理函数是并发的逻辑流

讲义第 47–48 页：

- 信号处理函数是与主程序**并发**运行的独立**逻辑流**（不是独立进程）。
- 但这个流只存在到它返回主程序为止。
- 第 48 页的图把整个过程展开：主程序 user code → kernel code（信号发送）→ 回到 user code → 再次进入 kernel（信号接收）→ 跳到 user code (handler) → 返回 kernel → 回到 user code (main) 的 `I_next`。

这个“同一进程内两条并发流”的模型是理解后面所有准则的关键：它们**共享全局变量**，却以不可预测的时机交错。

**嵌套处理（第 49 页）**：处理函数本身也能被其它处理函数打断。图中：主程序捕获信号 s → 进入 Handler S → 捕获信号 t → 进入 Handler T → T 返回 S → S 返回主程序。

### 5.17 阻塞与解除阻塞

讲义第 50 页，两种阻塞机制：

1. **隐式阻塞**：内核自动阻塞**当前正在处理的**那类信号。例如 `SIGINT` 处理函数执行期间，不会被另一个 `SIGINT` 打断。
2. **显式阻塞**：`sigprocmask` 函数。

配套函数：

- `sigemptyset`：创建空集合
- `sigfillset`：把所有信号号加入集合
- `sigaddset`：加入一个信号号
- `sigdelset`：删除一个信号号

**临时阻塞（第 51 页）**：

```c
sigset_t mask, prev_mask;
sigemptyset(&mask);
sigaddset(&mask, SIGINT);
/* Block SIGINT and save previous blocked set */
sigprocmask(SIG_BLOCK, &mask, &prev_mask);
    /* Code region that will not be interrupted by SIGINT */
/* Restore previous blocked set, unblocking SIGINT */
sigprocmask(SIG_SETMASK, &prev_mask, NULL);
```

注意 `prev_mask` 的用法：**保存并恢复**原来的掩码，而不是简单地“解除阻塞”——因为你不知道进入这段代码时 `SIGINT` 是否本来就被阻塞着。

### 5.18 安全信号处理的六条准则

讲义第 52–54 页。前提：处理函数与主程序并发、共享全局数据结构，可能破坏它们。

| 编号 | 准则 | 原因 |
|---|---|---|
| G0 | 处理函数尽量简单 | 例如只设一个全局标志然后返回 |
| G1 | 只调用**异步信号安全**的函数 | `printf`、`sprintf`、`malloc`、`exit` 都**不安全** |
| G2 | 进入时保存 `errno`，退出时恢复 | 否则会覆盖主程序正在用的 `errno` |
| G3 | 访问共享数据结构时临时阻塞所有信号 | 防止结构被破坏 |
| G4 | 全局变量声明为 `volatile` | 防止编译器把它缓存在寄存器里 |
| G5 | 全局标志声明为 `volatile sig_atomic_t` | 只读或只写的标志（如 `flag = 1`，不是 `flag++`）这样声明后无需 G3 保护 |

**异步信号安全（第 54 页）**：

- 定义：函数要么**可重入**（所有变量都在栈帧上），要么**不可被信号中断**。
- POSIX 保证 **117 个**函数异步信号安全（来源：`man 7 signal-safety`）。
- 常见的安全函数：`_exit`、`write`、`wait`、`waitpid`、`sleep`、`kill`。
- 常见的不安全函数：`printf`、`sprintf`、`malloc`、`exit`。
- **不幸的事实：`write` 是唯一异步信号安全的输出函数。**

为什么 `printf` 不安全？因为它内部有静态缓冲区和锁，若主程序正在 `printf` 中途被信号打断，处理函数再调 `printf`，缓冲区状态就乱了。

**安全输出方案一（第 55 页）**：用 `csapp.c` 里的可重入 SIO 库：

```c
ssize_t sio_puts(char s[]);   /* Put string */
ssize_t sio_putl(long v);     /* Put long */
void sio_error(char s[]);     /* Put msg & exit */
```

```c
void sigint_handler(int sig) {
    sio_puts("So you think you can stop the bomb with ctrl-c, do you?\n");
    sleep(2);
    sio_puts("Well...");
    sleep(1);
    sio_puts("OK. :-)\n");
    _exit(0);
}
```

**方案二（第 56 页）**：`sio_printf`，支持受限的格式串（`%c %s %d %u %x %%`，可带 `l` 与 `z` 长度修饰）：

```c
sio_printf("So you think you can stop the bomb (process %d) with ctrl-%c, do you?\n",
           (int) getpid(), 'c');
```

### 5.19 错误一：只 wait 一次

讲义第 57 页：

```c
volatile int ccount = 0;
void child_handler(int sig) {
    int olderrno = errno;
    pid_t pid;
    if ((pid = wait(NULL)) < 0)
        Sio_error("wait error");
    ccount--;
    sio_puts("Handler reaped child ");
    sio_putl((long)pid);
    sio_puts(" \n");
    sleep(1);
    errno = olderrno;
}
void fork14() {
    ccount = N;
    signal(SIGCHLD, child_handler);
    for (i = 0; i < N; i++)
        if ((pid[i] = fork()) == 0) {
            sleep(1);
            exit(0);
        }
    while (ccount > 0) ;      /* 父进程自旋 */
}
```

`N == 5` 的实际运行：

```
whaleshark> ./forks 14
Handler reaped child 23240
Handler reaped child 23241
. . .(hangs)
```

**为什么挂住**？因为**信号不排队**。5 个子进程几乎同时退出，内核只保留一个 pending 的 `SIGCHLD`（或少数几个），处理函数被调用的次数少于 5 次，`ccount` 永远减不到 0。讲义明确写出：“This code is incorrect!”

**修正（第 58 页）**：在循环里 `wait` 直到没有更多：

```c
void child_handler2(int sig) {
    int olderrno = errno;
    pid_t pid;
    while ((pid = wait(NULL)) > 0) {
        ccount--;
        sio_puts("Handler reaped child ");
        sio_putl((long)pid);
        sio_puts(" \n");
    }
    if (errno != ECHILD)
        sio_error("wait error");
    errno = olderrno;
}
```

现在 5 个子进程都被回收。

### 5.20 错误二：竞态

讲义第 59–61 页。`procmask1.c` 的处理函数：

```c
void handler(int sig) {
    int olderrno = errno;
    sigset_t mask_all, prev_all;
    pid_t pid;
    sigfillset(&mask_all);
    while ((pid = waitpid(-1, NULL, 0)) > 0) {   /* Reap child */
        sigprocmask(SIG_BLOCK, &mask_all, &prev_all);
        deletejob(pid);                          /* Delete from job list */
        sigprocmask(SIG_SETMASK, &prev_all, NULL);
    }
    if (pid != 0 && errno != ECHILD)
        sio_error("waitpid error");
    errno = olderrno;
}
```

主程序（第 60 页，**有 bug**）：

```c
while (n--) {
    if ((pid = fork()) == 0) {
        execve("/bin/date", argv, NULL);
    }
    sigprocmask(SIG_BLOCK, &mask_all, &prev_all);  /* Parent */
    addjob(pid);                                    /* Add to job list */
    sigprocmask(SIG_SETMASK, &prev_all, NULL);
}
```

**问题**：这段代码假设“父进程先跑”。如果子进程在父进程执行 `addjob(pid)` **之前**就终止了，`SIGCHLD` 处理函数会先执行 `deletejob(pid)`——但此时 job list 里还没有这个 pid。结果是 job list 里留下一个永远不会被删除的条目，或者 `deletejob` 访问不存在的节点。

**修正（第 61 页）**：在 `fork` **之前**就阻塞 `SIGCHLD`，等 `addjob` 完成后再解除：

```c
while (n--) {
    sigprocmask(SIG_BLOCK, &mask_one, &prev_one);   /* Block SIGCHLD */
    if ((pid = fork()) == 0) {
        sigprocmask(SIG_SETMASK, &prev_one, NULL);  /* Child: unblock */
        execve("/bin/date", argv, NULL);
    }
    sigprocmask(SIG_BLOCK, &mask_all, NULL);        /* Parent */
    addjob(pid);                                    /* Add to job list */
    sigprocmask(SIG_SETMASK, &prev_one, NULL);      /* Unblock SIGCHLD */
}
```

要点：

- 子进程里也要恢复掩码，否则 `execve` 后的新程序会继承被阻塞的 `SIGCHLD`。
- 父进程在 `addjob` 期间阻塞**所有**信号（`mask_all`），而不只是 `SIGCHLD`。
- 解除阻塞时用 `prev_one`（进入循环前的掩码），保证语义正确。

这个“先阻塞、再 fork、再改共享结构、再解除”的模式，是 Tsh Lab 的核心骨架。

### 5.21 错误三：忙等与 pause 竞态

讲义第 62–66 页。目标是“显式等待 `SIGCHLD` 到来”。处理函数：

```c
volatile sig_atomic_t pid;
void sigchld_handler(int s) {
    int olderrno = errno;
    pid = waitpid(-1, NULL, 0);     /* Main is waiting for nonzero pid */
    errno = olderrno;
}
void sigint_handler(int s) { }
```

主程序（第 63 页）：

```c
while (n--) {
    sigprocmask(SIG_BLOCK, &mask, &prev);   /* Block SIGCHLD */
    if (fork() == 0) exit(0);
    pid = 0;
    sigprocmask(SIG_SETMASK, &prev, NULL);  /* Unblock SIGCHLD */
    while (!pid) ;                          /* 忙等（浪费 CPU） */
    printf(".");
}
```

第 64 页列出三种等待写法的缺陷：

| 写法 | 问题 |
|---|---|
| `while (!pid) ;` | **正确但极浪费**：忙等，占满 CPU |
| `while (!pid) pause();` | **有竞态**：检查 `pid` 与进入 `pause` 之间若信号到达，`pause` 会永远睡下去 |
| `while (!pid) sleep(1);` | **安全但太慢**：最多要等 1 秒才响应 |

`pause()` 版本的竞态值得细想：`while (!pid)` 判断为真（`pid` 还是 0）→ 此时 `SIGCHLD` 到达，处理函数把 `pid` 设为非 0 并返回 → 主程序接着执行 `pause()` → 但信号已经处理完了，`pause()` 会一直等到**下一个**信号。如果不再有信号，程序永久挂起。

**根本原因**：“解除阻塞”和“挂起”是两个分开的操作，中间有窗口。

### 5.22 sigsuspend：原子地解除阻塞并挂起

讲义第 65 页：

```c
int sigsuspend(const sigset_t *mask);
```

它等价于**原子的**（不可打断的）以下三步：

```c
sigprocmask(SIG_SETMASK, &mask, &prev);
pause();
sigprocmask(SIG_SETMASK, &prev, NULL);
```

由于这三步不可分割，信号不可能“卡在中间”到达，竞态窗口消失。

**用法（第 66 页）**：

```c
while (n--) {
    sigprocmask(SIG_BLOCK, &mask, &prev);   /* Block SIGCHLD */
    if (fork() == 0) exit(0);
    pid = 0;
    while (!pid)
        sigsuspend(&prev);                  /* 原子地解除阻塞并等待 */
    sigprocmask(SIG_SETMASK, &prev, NULL);  /* 可选：恢复掩码 */
    printf(".");
}
```

注意传给 `sigsuspend` 的是 `prev`（**进入循环前**的掩码），而不是空集——这样在等待期间，原本就阻塞的信号仍然阻塞。

这套模式（阻塞 → fork → 用 `sigsuspend` 等 → 恢复）就是 shell 等待前台作业的标准写法，也是 Tsh Lab 的关键技巧。

### 5.23 本讲知识地图

```
ECF
├── 异常（硬件 + 内核）
│   ├── 中断（异步，返回 Inext）
│   ├── 陷阱（同步、有意，返回 Inext）—— 系统调用
│   ├── 故障（同步、无意、可恢复，重执行 Icurr）—— 缺页
│   └── 中止（同步、无意、不可恢复）
├── 上下文切换（内核 + 定时器）—— 上一讲
├── 信号（内核 + 应用）
│   ├── 发送：内核事件 / kill
│   ├── 状态：pending & blocked 位向量，不排队
│   ├── 接收：pnb = pending & ~blocked，取最小位
│   ├── 处理：SIG_IGN / SIG_DFL / 用户函数
│   └── 安全：G0–G5、async-signal-safe、sigsuspend
└── 非局部跳转（C 运行时）—— setjmp/longjmp（本讲未展开）
```

## 6. 代码示例

### 6.1 官方课程代码

**系统调用 `__open`（17-ecf.pdf 第 17 页）**：

```asm
00000000000e5d70 <__open>:
...
e5d79:   b8 02 00 00 00      mov  $0x2,%eax      # open is syscall #2
e5d7e:   0f 05               syscall
e5d80:   48 3d 01 f0 ff ff   cmp  $0xfffffffffffff001,%rax
```

**缺页与段错误（17-ecf.pdf 第 19–20 页）**：`a[500] = 13` 可恢复（重执行 `movl`）；`a[5000] = 13` 发 `SIGSEGV`。

**kill 发送信号（17-ecf.pdf 第 40 页）**：`fork12`，对 N 个死循环子进程逐个 `kill(pid[i], SIGINT)`，再用 `wait` 回收。

**SIGINT 处理（17-ecf.pdf 第 46 页）**：`sigint.c`（不安全版本，用 `printf`）。

**安全版本（17-ecf.pdf 第 55–56 页）**：`sigintsafe.c`，用 `sio_puts`/`sio_printf` + `_exit`。

**只 wait 一次的错误（17-ecf.pdf 第 57 页）**：`fork14`，5 个子进程只回收了 2 个就挂住。

**循环 wait 的修正（17-ecf.pdf 第 58 页）**：`child_handler2`，`while ((pid = wait(NULL)) > 0)`。

**竞态与修正（17-ecf.pdf 第 59–61 页）**：`procmask1.c`（bug）与 `procmask2.c`（在 fork 前阻塞 `SIGCHLD`）。

**sigsuspend（17-ecf.pdf 第 65–66 页）**：`sigsuspend.c`，`while (!pid) sigsuspend(&prev);`。

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

演示“信号不排队”导致漏收（可复现讲义第 57 页的挂起）：

```c
/* 非官方示例：N 个子进程几乎同时退出，但处理函数只被调用少数几次 */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <signal.h>
#include <errno.h>
#include <sys/wait.h>

static volatile sig_atomic_t ccount = 0;

static void bad_handler(int sig) {
    (void)sig;
    int saved = errno;
    pid_t pid = wait(NULL);          /* 只收一个！ */
    if (pid > 0) {
        ccount--;
        char buf[64];
        int n = snprintf(buf, sizeof buf, "reaped %d\n", (int)pid);
        write(STDOUT_FILENO, buf, (size_t)n);   /* write 是安全的 */
    }
    errno = saved;
}

int main(void) {
    const int N = 5;
    ccount = N;
    signal(SIGCHLD, bad_handler);
    for (int i = 0; i < N; i++)
        if (fork() == 0) { usleep(1000); _exit(0); }

    while (ccount > 0)               /* 很可能永远出不去 */
        pause();
    write(STDOUT_FILENO, "done\n", 5);
    return 0;
}
```

把 `wait(NULL)` 换成 `while ((pid = waitpid(-1, NULL, WNOHANG)) > 0) ccount--;` 就能稳定结束。

用 `sigsuspend` 正确等待（对照讲义第 64 页的三种错误写法）：

```c
/* 非官方示例：阻塞 → fork → sigsuspend 等待 → 恢复，无竞态 */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <signal.h>
#include <sys/wait.h>

static volatile sig_atomic_t got = 0;

static void chld(int s) { (void)s; got = 1; }

int main(void) {
    sigset_t block, prev;
    sigemptyset(&block);
    sigaddset(&block, SIGCHLD);
    signal(SIGCHLD, chld);

    sigprocmask(SIG_BLOCK, &block, &prev);   /* 先阻塞，避免 fork 后立刻到达 */
    pid_t pid = fork();
    if (pid == 0) _exit(0);

    while (!got)
        sigsuspend(&prev);                   /* 原子地解除阻塞并睡眠 */

    sigprocmask(SIG_SETMASK, &prev, NULL);
    waitpid(pid, NULL, 0);
    printf("child done\n");
    return 0;
}
```

按 G0–G5 写一个完整的处理函数（含 G2 的 errno 保护与 G3 的临界区）：

```c
/* 非官方示例：符合 G0-G5 的 SIGCHLD 处理函数骨架 */
#include <errno.h>
#include <signal.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static volatile sig_atomic_t reaped = 0;   /* G5 */
static int job_list[64];                    /* 共享数据，访问需 G3 保护 */
static int job_count = 0;

static void on_sigchld(int sig) {
    (void)sig;
    int saved_errno = errno;                /* G2 进入时保存 */
    sigset_t all, old;
    sigfillset(&all);
    pid_t pid;

    while ((pid = waitpid(-1, NULL, WNOHANG)) > 0) {   /* 循环收，防漏 */
        sigprocmask(SIG_BLOCK, &all, &old);            /* G3 临界区 */
        for (int i = 0; i < job_count; i++)
            if (job_list[i] == (int)pid) {
                job_list[i] = job_list[--job_count];
                break;
            }
        sigprocmask(SIG_SETMASK, &old, NULL);
        reaped++;                           /* 只做简单自增 */
    }
    errno = saved_errno;                    /* G2 退出时恢复 */
}
```

注意：`waitpid` 用 `WNOHANG` 版本更好——如果处理函数被调用时已无子进程可收（信号与回收交错），非阻塞版本会立刻返回 0 而不是让处理函数卡住。

用 `strace` 观察信号的实际投递（Linux）：

```bash
# 非官方示例：观察 SIGCHLD 的到达与 wait4 调用
strace -f -e trace=clone,wait4,rt_sigaction,rt_sigprocmask ./a.out
```

可以看到 `rt_sigaction` 安装处理函数、`clone` 创建子进程、`wait4` 回收，以及 `--- SIGCHLD ---` 这样的行。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| 异常（exception） | 信号（signal） | 前者由硬件 + 内核处理，控制转到内核；后者由内核发给进程，控制转到用户处理函数 |
| 中断 | 陷阱 | 前者**异步**（外部事件），后者**同步**（执行指令有意触发）；两者都返回 `I_next` |
| 陷阱 | 故障 | 前者有意（`syscall`），后者无意（缺页）；前者返回下一条，后者**重执行当前指令** |
| 故障 | 中止 | 前者可能可恢复，后者必然终止程序 |
| pending | blocked | 前者是“已发送未接收”，后者是“主动拒收”；接收条件为 `pending & ~blocked` |
| 信号不排队 | 信号会排队 | 事实是**不排队**：同类型最多一个 pending，后续直接丢弃 |
| `SIG_IGN` | 忽略僵尸 | `SIGCHLD` 默认动作就是 `SIG_IGN`，但僵尸仍存在；忽略信号 ≠ 回收子进程 |
| `SIGKILL` | `SIGINT` | 前者不可捕获、不可阻塞、不可忽略；后者可以被处理函数捕获 |
| `kill` 命令 | `kill` 函数 | 前者是 `/bin/kill` 程序（`-9 -PGID` 表示进程组）；后者是系统调用，只能指定 PID |
| 忙等 | `pause` 竞态 | 忙等浪费 CPU 但正确；`while(!pid) pause()` 有丢信号窗口；`sigsuspend` 两者都解决 |
| `volatile` | `sig_atomic_t` | 前者禁止寄存器缓存；后者额外保证读写的原子性；标志变量应两者兼有 |
| `printf` | `write` | 前者不安全（有静态缓冲与锁）；后者是**唯一**异步信号安全的输出函数 |

## 8. 对应原版讲义

- PDF 相对路径：`90-原始PDF/15-213/lectures/17-ecf.pdf`
- 总页数：66 页
- 重点页码：
  - 标题页（17th Lecture, October 29, 2026）：第 2 页
  - 今日大纲：第 3 页
  - 简化 shell 的后台僵尸问题：第 4 页
  - 打印机着火的梗图与 Linux `lp.c` 链接：第 5–6 页
  - 物理控制流：第 7 页
  - 为何需要 ECF：第 8 页
  - ECF 的四个层次：第 9 页
  - 异常定义与三种去向：第 11 页
  - 异常表 / 中断向量：第 12 页
  - 硬件 ECF 分类树：第 13 页
  - 异步异常（中断）：第 14 页
  - 同步异常（trap/fault/abort）：第 15 页
  - 系统调用号表：第 16 页
  - `__open` 反汇编与寄存器约定：第 17–18 页
  - 缺页（可恢复）：第 19 页
  - 非法引用（`SIGSEGV`）：第 20 页
  - ECF 各层的实现者：第 22 页
  - 后台僵尸问题重述：第 23 页
  - ECF 救场：第 24 页
  - 信号定义与常见信号表：第 25 页
  - 发送信号的两种原因：第 26 页
  - pending/blocked 位向量动画：第 27–31、35 页
  - 接收信号与三种反应：第 32 页
  - **信号不排队**：第 33 页
  - pending/blocked 位向量定义：第 34 页
  - 进程组：第 36 页
  - `/bin/kill`：第 37 页
  - 键盘发送信号：第 38 页
  - ctrl-z / fg 实例与 `ps` STAT：第 39 页
  - `kill` 函数示例（`fork12`）：第 40 页
  - 接收信号的四步算法：第 41–42 页
  - 默认动作：第 43 页
  - `signal` 安装处理函数：第 45 页
  - `sigint.c` 示例：第 46 页
  - 处理函数是并发逻辑流：第 47–48 页
  - 嵌套处理函数：第 49 页
  - 隐式/显式阻塞：第 50 页
  - `sigprocmask` 临时阻塞：第 51 页
  - 安全处理六准则 G0–G5：第 53 页
  - 异步信号安全与 117 个函数：第 54 页
  - `sio_puts` 安全输出：第 55 页
  - `sio_printf`：第 56 页
  - 只 `wait` 一次的错误：第 57 页
  - 循环 `wait` 修正：第 58 页
  - 竞态处理函数与有 bug 的主程序：第 59–60 页
  - 修正后的无竞态版本：第 61 页
  - 显式等待信号：第 62–63 页
  - 三种等待写法的缺陷：第 64 页
  - `sigsuspend` 语义：第 65 页
  - `sigsuspend` 用法：第 66 页
- 原始链接：https://www.cs.cmu.edu/~213/lectures/17-ecf.pdf
- 待人工核对：本讲未展开 `setjmp`/`longjmp`（仅在 ECF 层次表第 9 页提及），CSAPP 8.6 节的内容需另找材料。

## 9. 对应视频

未找到官方公开录像。

## 10. 本节复习

- ECF 四层：异常（硬件+内核）、上下文切换（内核+定时器）、信号（内核+应用）、非局部跳转（C 库）。
- 异常分类：中断（异步，返回下一条）、陷阱（同步有意，返回下一条）、故障（同步无意可恢复，重执行）、中止（不可恢复）。
- 异常表以异常号为下标；系统调用号在 `%rax`，参数在 `%rdi/%rsi/%rdx/%r10/%r8/%r9`，返回值在 `%rax`，负值为错误。
- 信号只含 ID；每类最多一个 pending；**不排队**；接收条件 `pending & ~blocked`，按最小位依次处理。
- 进程组：`ctrl-c` 发给前台进程组所有进程；`kill -9 -PGID` 发给整组。
- 处理函数是与主程序并发的逻辑流，共享全局数据。
- 六准则：G0 简单、G1 只用 async-signal-safe、G2 保 `errno`、G3 临界区阻塞信号、G4 `volatile`、G5 `volatile sig_atomic_t`。
- `write` 是唯一安全的输出函数；`printf`/`malloc`/`exit` 都不安全。
- 三类 bug：只 `wait` 一次（漏收）、`fork` 与 `addjob` 的竞态（先阻塞再 fork）、`while(!pid) pause()`（丢信号）。
- `sigsuspend` = 原子版“设掩码 + `pause` + 恢复”。

## 11. 自我检查

1. 陷阱（trap）与故障（fault）都返回，为什么一个返回 `I_next` 而另一个重执行 `I_curr`？举出各自的一个例子。
2. 内核为 5 个几乎同时退出的子进程只投递了 2 个 `SIGCHLD`，这是 bug 还是特性？如何写出正确的处理函数？
3. `while (!pid) pause();` 的竞态具体发生在哪两条指令之间？为什么 `sigsuspend` 能消除它？
4. 为什么 `printf` 不能在信号处理函数里用？`write` 为什么可以？`sio_puts` 又是怎么做到的？
5. 讲义第 60 页的 `procmask1.c` 为什么有 bug？修正版为什么要把“阻塞 `SIGCHLD`”放在 `fork` **之前**，而且子进程里还要恢复掩码？

<details>
<summary>参考答案</summary>

1. 陷阱是**有意**触发的，触发它的那条指令（如 `syscall`）本身已经完成了它的工作（陷入内核），所以处理完应该执行**下一条**。故障是执行当前指令时**出了意外**，当前指令的效果没有完成（比如 `movl` 因为页不在内存而没写成），所以处理完必须**重新执行**当前指令。例子：陷阱 = `open` 的 `syscall`；故障 = `a[500] = 13` 触发的缺页。

2. 是**特性**，不是 bug：讲义第 33 页明确说信号不排队，每类信号最多一个 pending，重复发送直接丢弃。所以处理函数必须在**循环**里回收，直到 `waitpid` 返回 ≤ 0：`while ((pid = waitpid(-1, NULL, WNOHANG)) > 0) { ... }`，并用 `errno == ECHILD` 判断是否收干净。第 57 页的 `fork14` 就是没这么写才挂住。

3. 竞态发生在“`while (!pid)` 判断为真”之后、“`pause()` 真正执行”之前。如果 `SIGCHLD` 恰好在这个窗口到达，处理函数会把 `pid` 设为非 0 并返回，然后主程序才执行 `pause()`——但信号已经被消费掉了，`pause()` 会一直等到**下一个**信号。`sigsuspend` 把“设置掩码（解除阻塞）”和“挂起”做成一条不可分割的原子操作，信号不可能卡在中间，因此窗口消失。

4. `printf` 内部有静态缓冲区和锁，如果主程序正在 `printf` 中途被信号打断，处理函数再调用它就会看到半更新的缓冲区状态，导致输出错乱甚至死锁。`write` 是无缓冲的系统调用，每次调用独立完成，没有跨调用的共享状态，因此可重入。`sio_puts`/`sio_printf` 是 CS:APP 提供的可重入实现：所有状态都在栈上，最终只调用 `write`。

5. 因为它假设“父进程一定先于子进程执行 `addjob`”。如果子进程在 `fork` 返回后立刻终止，`SIGCHLD` 处理函数可能抢在 `addjob(pid)` 之前运行 `deletejob(pid)`，此时 job list 里没有这个 pid——要么删除失败留下脏条目，要么破坏链表。修正版在 `fork` **之前**就阻塞 `SIGCHLD`，保证 `addjob` 一定先完成，再解除阻塞让处理函数运行。子进程里也要恢复掩码，是因为 `fork` 会继承父进程的信号掩码，若不恢复，`execve` 之后的新程序会带着被阻塞的 `SIGCHLD` 运行，行为异常。

</details>

## 12. 进一步学习

- 下一讲：[[15-213-18-System-Level-IO]]
- 前一讲：[[15-213-16-Processes]]
- 相关实验：[[00-Lab总览]]（Tsh Lab 需要完整的信号处理、作业控制与 `sigsuspend` 等待；Bomb Lab 的隐藏关卡与信号有关）
- 课程总览：[[20-CMU-15-213/00-课程总览|CMU 15-213 - 课程总览]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（Exception、Signal）
- CSAPP 第 3 版 8.5–8.8 节；8.5.5 节的 “Putting It Together: Writing a Shell with Job Control” 与本讲 5.19–5.22 完全对应，8.6 节的 `setjmp`/`longjmp` 是本讲未覆盖的部分。
- `man 7 signal`、`man 7 signal-safety`、`man 2 sigsuspend` 三份手册页值得通读。
