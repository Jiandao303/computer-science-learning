---
course: CMU 15-213
course_name: Introduction to Computer Systems
semester: Fall 2026
lecture_id: L18
topic: System-Level I/O
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-213
  - 系统级IO
  - 文件描述符
  - 标准IO
  - RIO
  - 重定向
  - dup2
---

# 系统级 I/O（System-Level I/O）

## 1. 本节学习目标

- 能说清文件（file）就是字节序列，以及“一切皆文件”在 Linux 里的具体体现。
- 能熟练使用 Unix I/O 的五个原语：`open`、`close`、`read`、`write`、`lseek`，以及 `stat`。
- 能解释为什么 `read`/`write` 的**短计数（short count）**不是错误，以及什么场景必然出现短计数。
- 能说明标准 I/O 的流（stream）= 文件描述符 + 内存缓冲区，以及缓冲区何时被刷出（flush）。
- 能画出三张表（描述符表、打开文件表、v-node 表）并据此解释文件共享、`fork` 继承、`dup2` 重定向。
- 能判断一个场景该用标准 I/O、Unix I/O 还是 RIO，并说出理由。
- 能写出一个健壮的 `cat`（正确区分 EOF、错误、短计数）。

## 2. 前置知识

- [[15-213-16-Processes]]：`fork`、`execve`、进程的文件描述符继承。
- [[15-213-17-Exceptional-Control-Flow]]：异步信号安全（async-signal-safe）——这一讲会反复用到这个结论。
- [[15-213-12-Virtual-Memory-Details]]：内存映射文件（memory-mapped files）是内核实现 I/O 的底层手段。
- C 的 `ssize_t` / `size_t` 区别：前者有符号（可为负 = 错误），后者无符号。

## 3. 核心概念

- **文件（File）**：一个字节序列 `B0, B1, …, Bm-1`；内核不区分文本与二进制。
- **File Descriptor（文件描述符，fd）**：小的非负整数，代表一个打开的文件；`-1` 表示出错。
- **Regular File（普通文件）**：存放任意数据；文本文件是人类可读的那一类。
- **Directory（目录）**：文件名到文件的映射数组，至少含 `.` 与 `..`。
- **Socket（套接字）**：与另一台机器上的进程通信的文件类型。
- **Current File Position（当前文件位置）**：下一次读/写的偏移，位于字节 `k-1` 与 `k` 之间。
- **Short Count（短计数）**：`read`/`write` 返回的字节数小于请求的字节数。
- **Stream（流）**：标准 I/O 对“文件描述符 + 内存缓冲区”的抽象，类型为 `FILE *`。
- **Flush（刷出）**：把用户态缓冲区的内容通过 `write` 交给内核。
- **Metadata（元数据）**：关于文件数据的数据（大小、类型、所有者、时间戳等），由 `stat` 取得。
- **Descriptor Table（描述符表）**：每进程一张，fd → 打开文件表项的指针。
- **Open File Table（打开文件表）**：全局共享，记录文件位置（file pos）与引用计数（refcnt）。
- **v-node Table（v-node 表）**：全局共享，记录文件访问模式、大小、类型等 `stat` 信息。
- **Redirection（重定向）**：用 `dup2(oldfd, newfd)` 让 `newfd` 指向 `oldfd` 所指的同一文件。
- **RIO（Robust I/O，健壮 I/O）**：CS:APP 提供的包装库，正确处理短计数，并带缓冲读。

## 4. 通俗理解

写 C 程序时我们用 `fopen`/`fputs`/`fclose`，觉得“写文件”就是这么回事。但讲义第 3 页把这三行代码**展开**给你看：`fopen` 内部只是 `open` + `fdopen`，`fputs` 内部是 `strlen` + 循环 `write`，`fclose` 内部是 `close`，而 `close` 底下不过是一条 `mov $3, %eax; syscall`。

也就是说：**标准 I/O 是建立在 Unix I/O 之上的便利层，Unix I/O 是建立在系统调用之上的唯一真相**。讲义第 4 页用一张“两套函数”的对照图收束这件事——左边是 `open`/`read`/`write`/`lseek`/`stat`/`close`（最大控制、最小便利），中间是 RIO（折中），右边是 `fopen`/`fgets`/`fprintf`/`fclose`（最小控制、最大便利）。

为什么不能只用最方便的那套？因为便利层有代价：它带缓冲区，而缓冲区意味着**状态**，状态意味着在信号处理函数里可能被破坏（第 17 讲 G1 准则），在网络套接字上可能因为“短计数”而语义错乱。反过来，只用最底层那套也很痛苦：每次 `read` 一个字节要花一万多个时钟周期，还得自己处理短计数。

这一讲的主线就是：**先看清底层（Unix I/O），再看懂上层的实现（标准 I/O 与 RIO），最后根据场景选对工具**。中间穿插的三张表（描述符表、打开文件表、v-node 表）是理解 `fork` 共享文件位置、`dup2` 重定向的关键——几乎所有“为什么子进程读到了第二个字节”的疑惑，答案都在这三张表里。

## 5. 原理与推导

### 5.1 系统级 I/O 在标准 I/O 之下

讲义第 3 页把“用标准 I/O 写文件”的程序和它的底层实现并排放：

```c
/* 应用层 */
#include <stdio.h>
int main(void) {
    FILE *fp = fopen("output.txt", "w");
    if (!fp) { perror("output.txt"); return 1; }
    fputs("baby shark (do doo dooo)\n", fp);
    if (fclose(fp)) { perror("output.txt"); return 1; }
    return 0;
}
```

```c
/* 标准库实现层 */
FILE *fopen(const char *fname, const char *mode) {
    int fd = open(fname, __mode2flags(mode), DEFFILEPERMS);
    if (fd == -1) { return NULL; }
    return fdopen(fd, mode);
}
int fputs(const char *s, FILE *fp) {
    size_t n = strlen(s);
    while (n > 0) {                       /* 循环写，处理短计数 */
        ssize_t written = write(fp->fd, s, n);
        if (written < 0) return EOF;
        n -= written;
        s += written;
    }
    return 0;
}
int fclose(FILE *fp) {
    int rv = close(fp->fd);
    __ffree(fp);
    return rv;
}
```

```asm
/* 系统调用层 */
.globl close
close:
    mov  $3, %eax          # close 是 3 号系统调用
    syscall
    cmp  $-4096, %rax
    jae  __syscall_error
    ret
```

三点值得注意：

1. `fputs` 里那个 `while` 循环正是“处理短计数”的标准写法，与 5.6 节 RIO 的做法一致。
2. `close` 的 `cmp $-4096, %rax; jae __syscall_error` 与上一讲 `__open` 的 `cmp $0xfffffffffffff001` 是同一件事的两种写法：返回值落在 `[-4095, -1]` 即为错误。
3. `fclose` 先 `close` 再释放 `FILE` 结构，返回的是 `close` 的结果——这解释了 5.4 节“关闭也可能报错”。

### 5.2 两套接口的分工

讲义第 4 页的对照：

| | Unix I/O（`open`/`read`/`write`/`lseek`/`stat`/`close`） | RIO（`rio_readn`/`rio_writen`/`rio_readlineb`/`rio_readnb`/`rio_readinitb`） | 标准 I/O（`fopen`/`fread`/`fgets`/`fprintf`/`fclose`/`fseek`/`ftell`/`fflush`） |
|---|---|---|---|
| 控制力 | 最大 | 中 | 最小 |
| 便利性 | 最小 | 中 | 最大 |
| 可用于信号处理函数 | **可以**（async-signal-safe） | 可以（只调 `read`/`write`） | **不可以** |
| 可用于网络连接 | 可以 | **最合适** | 不合适 |
| 短计数 | 手动处理 | 自动处理 | 自动处理 |

讲义的结语很提气：“You can write your own set of high-level convenient functions if you want!”——RIO 就是 CS:APP 作者自己写的那套。

### 5.3 文件就是字节序列

讲义第 6 页：

- 文件是字节序列 `B0, B1, …, Bk, …, Bm-1`。
- **所有 I/O 设备都表示为文件**：
  - `/dev/sda2`（磁盘分区）
  - `/dev/tty2`（终端）
  - `/dev/null`（丢弃所有写入 / 读取得到空文件）
- **内核数据结构也以文件形式暴露**：
  - `cat /proc/$$/status`（当前 shell 的状态）
  - `ls -l /proc/$$/fd/`（当前 shell 打开的所有 fd）
  - `ls -RC /sys/devices | less`（设备树）

“一切皆文件”不是比喻，是内核的统一接口：因为读磁盘、读终端、读管道在抽象上都是“从某个对象读出字节流”，所以它们能共用同一套 `read`/`write`。

### 5.4 Unix I/O 的五个基本操作

讲义第 7 页：

| 操作 | 函数 | 说明 |
|---|---|---|
| 打开 / 关闭 | `open()`、`close()` | 获得 / 归还文件描述符 |
| 读 / 写 | `read()`、`write()` | 在当前位置搬运字节 |
| 查询信息 | `stat()`、`lstat()`、`fstat()` | 大小、类型、最后修改时间等 |
| 改变当前位置 | `lseek()` | 指定下一次读/写的偏移 |

图示：文件 `B0 B1 … Bk-1 | Bk Bk+1 …`，当前文件位置 = `k`，即**位于字节 `k-1` 与 `k` 之间**。这个“位置在字节之间的缝隙里”的表述很重要：偏移 `0` 表示第一个字节之前。

### 5.5 文件类型

讲义第 8 页：

- **Regular file（普通文件）**：存放任意数据。
- **Directory（目录）**：一组相关文件的索引。
- **Socket（套接字）**：与另一台机器上的进程通信。

超出本课范围但存在的类型：命名管道（FIFO）、符号链接、字符设备、块设备。

**普通文件（第 9 页）**：

- 应用常区分文本与二进制文件；**内核完全不在乎，它眼里全是字节**。
- 文本文件是**文本行**的序列；文本行是**以行尾指示符终止**（不是分隔！）的字符序列。
- 字符由文本编码定义（ASCII、UTF-8、EUC-JP…）。
- 行尾（EOL）指示符：
  - 所有 Unix：单字节 `0x0A`（line feed, LF）
  - DOS/Windows：两字节 `0x0D 0x0A`（carriage return + line feed, CRLF），很多互联网协议也用它
  - **C 库会把它翻译成 `'\n'`**

最后这一条解释了为什么在 Windows 上用文本模式读写文件时字节数会对不上——翻译发生在 C 库里，内核看到的始终是原始字节。

**目录（第 10–12 页）**：

- 目录由**目录项（entry，也叫 link）**数组构成，每项把文件名映射到一个文件。
- 每个目录至少含两项：`.`（自身）、`..`（父目录）。
- 操作命令：`mkdir`（建空目录）、`ls`（查看）、`rmdir`（删空目录）。
- 所有文件构成以 `/` 为根的**层次结构**；内核为每个进程维护**当前工作目录（cwd）**，用 `cd` 修改。
- **路径名（pathname）**：绝对路径以 `/` 开头（如 `/home/droh/hello.c`）；相对路径从 cwd 出发（如 `../droh/hello.c`，当 cwd 是 `/home/bryant` 时）。

### 5.6 打开文件

讲义第 13 页：

- 打开文件是告知内核“我要开始访问这个文件了”。
- 返回一个小的标识整数：**文件描述符**；`fd == -1` 表示出错。
- **每个进程出生时就带着三个打开的文件**：
  - `0`：标准输入（stdin）
  - `1`：标准输出（stdout）
  - `2`：标准错误（stderr）
  - 它们可以是文件、管道、你的终端，甚至网络连接。

```c
int fd;
if ((fd = open("/etc/hosts", O_RDONLY)) < 0) {
    perror("open");
    exit(1);
}
```

**`open` 的两种调用形式（第 14 页）**：

1. 打开已存在的文件：`open(path, flags)`
   - `flags` 必须含且只含一个：`O_RDONLY`（只读）、`O_WRONLY`（只写）、`O_RDWR`（读写）
   - 可选用 `|` 组合：`O_APPEND`（所有写入到末尾）、`O_TRUNC`（删除原有内容）、`O_CLOEXEC`（`execve` 时关闭此文件）等
2. 打开或创建文件：`open(path, flags, mode)`
   - `flags` 必须含 `O_CREAT`
   - 且必须含且只含一个：`O_WRONLY`、`O_RDWR`
   - 可能还要：`O_EXCL`（文件已存在则失败）、`O_APPEND`、`O_TRUNC`、`O_CLOEXEC`

**第三个参数（第 15 页）**：

- 是的，`open` 有两个或三个参数——“你大概以为 C 里做不到这个”（靠可变参数 `...`，见 `/usr/include/fcntl.h`）。
- 第三个参数只在第二个参数含 `O_CREAT` 时必需，否则被忽略。
- `mode` 给新建文件默认访问权限；会受 `umask` 影响（`man umask`）。
- **除非有特别理由，用 `sys/stat.h` 里的 `DEFFILEMODE`**。

`O_CLOEXEC` 值得单独记一笔：它与第 16 讲 `execve` 的“继承打开文件”相呼应。默认情况下 `execve` 后打开的文件会保留（这正是 shell 重定向能生效的原因），但若你不想让子程序继承某个 fd（比如安全敏感的场景），加 `O_CLOEXEC`。

### 5.7 关闭文件

讲义第 16 页：

- 关闭是告知内核“我用完了”。
- **不要重复关闭同一个文件**——等同于不要对同一个指针 `free` 两次。
- **关闭可能“失败”**：
  - 其实文件还是被关掉了；
  - 操作系统是在借这个机会**报告之前某次写操作延迟产生的错误**；
  - 不检查返回值，你可能**静默丢数据**。

```c
if (close(fd) < 0) {
    fprintf(stderr, "%s: write error: %s", filename, strerror(errno));
    exit(1);
}
```

这个“延迟错误”机制源于写回缓存：`write` 只是把数据交给内核的页缓存就返回了，真正的落盘可能延后；等到 `close`（或 `fsync`）时才可能发现磁盘满了、配额超了。所以 `close` 的返回值必须检查——这是一个非常容易被忽略的坑。

### 5.8 读文件

讲义第 17 页：

- 读 = 从当前文件位置把字节复制到内存，然后更新文件位置。
- 返回从 `fd` 读入 `buf` 的字节数：
  - 返回类型是 `ssize_t`（**有符号**整数）
  - `nbytes < 0` 表示出错
  - **短计数**（`nbytes < sizeof(buf)`）是可能的，而且**不是错误**

```c
char buf[512];
int fd, nbytes;
if ((nbytes = read(fd, buf, sizeof(buf))) < 0) {
    perror("read");
    exit(1);
}
```

### 5.9 写文件

讲义第 18 页：

- 写 = 从内存把字节复制到当前文件位置，然后更新文件位置。
- 返回写入的字节数；`nbytes < 0` 表示出错；**短计数同样可能且不是错误**。

```c
char buf[512];
int fd, nbytes;
if ((nbytes = write(fd, buf, sizeof(buf))) < 0) {
    perror("write");
    exit(1);
}
```

注意：讲义原文这一行 `if ((nbytes = write(fd, buf, sizeof(buf)) < 0)` 括号位置有误（`< 0` 落在了赋值号右边），照抄会得到 `nbytes` 为 0 或 1 而非字节数。**正确写法应为 `if ((nbytes = write(fd, buf, sizeof(buf))) < 0)`**。这属于讲义笔误，学习时按正确语义理解。

### 5.10 一个完整的 Unix I/O 例子（三次演进）

**版本一（第 19 页，太天真）**：

```c
#include <unistd.h>
int main(void) {
    char c;
    while (read(STDIN_FILENO, &c, 1) != 0)
        write(STDOUT_FILENO, &c, 1);
    return 0;
}
```

问题：`read` 返回 `-1` 时循环也继续（`-1 != 0`），会把错误当成正常数据流。讲义在旁边写着“Always check return codes from system calls!”。

**版本二（第 20 页，健壮）**：

```c
#include <unistd.h>
#include <stdio.h>
int main(void) {
    char c;
    for (;;) {
        ssize_t nread = read(STDIN_FILENO, &c, 1);
        if (nread == 0) {
            return 0;                 /* EOF */
        } else if (nread < 0) {
            perror("stdin");
            return 1;
        }
        if (write(STDOUT_FILENO, &c, 1) < 1) {
            perror("stdout: write error");
            return 1;
        }
    }
}
```

三个分支清晰：`0` = EOF，`< 0` = 错误，`>= 1` = 正常。`write` 检查的是 `< 1` 而不是 `< 0`，因为请求写 1 字节却写 0 字节也说明出了问题。

**版本三（第 21 页，Stevens 包装）**：

```c
#include "csapp.h"
int main(void) {
    char c;
    while (Read(STDIN_FILENO, &c, 1) != 0) {
        Write(STDOUT_FILENO, &c, 1);
    }
    return 0;
}
```

“Stevens wrappers”（首字母大写的 `Read`/`Write`/`Open`/`Close`/`Fork`…）让代码变短，**但它们不允许你从错误中恢复**——出错时直接打印信息并退出。

顺带一句性能现实：逐字节复制要走 `read`/`write` 系统调用，每次一万多个时钟周期，所以这个 `cat` 极慢。这正是标准 I/O 缓冲要解决的问题。

### 5.11 短计数

讲义第 22 页：

**会出现短计数的情况**：

- 读到**文件结尾（EOF）**
- 从**终端**读取文本行（用户还没敲完回车）
- 读写**网络套接字、管道**等

**永远不会出现短计数的情况**：

- 从磁盘文件读（除 EOF 外）
- 向磁盘文件写

**最佳实践：永远为短计数做好准备。**

为什么网络和终端会出现短计数？因为内核的缓冲区是有限的，而且数据是陆续到达的：套接字上此刻只有 20 字节可读，你请求 512 字节，`read` 就返回 20。磁盘文件则不同，只要没到 EOF，内核可以把请求补齐。

这条规则直接决定了网络编程里为什么不能直接 `read(fd, buf, n)` 然后假定读满了 `n`——必须循环，或者用 RIO。

### 5.12 标准 I/O

讲义第 24 页：C 标准库 `libc.so` 提供了一组更高层的函数（文档在 K&R 附录 B）：

- 打开/关闭：`fopen`、`fclose`
- 读写字节：`fread`、`fwrite`
- 读写文本行：`fgets`、`fputs`
- 格式化读写：`fscanf`、`fprintf`

**流（stream，第 25 页）**：

- 标准 I/O 把打开的文件建模为**流**——**一个文件描述符加一块内存缓冲区的抽象**。
- C 程序出生时就有三个打开流（定义在 `stdio.h`）：

```c
#include <stdio.h>
extern FILE *stdin;   /* standard input  (descriptor 0) */
extern FILE *stdout;  /* standard output (descriptor 1) */
extern FILE *stderr;  /* standard error  (descriptor 2) */
int main() {
    fprintf(stdout, "Hello, world\n");
}
```

注意 `stdout` 与 `STDOUT_FILENO` 不同：前者是 `FILE *`（带缓冲的流对象），后者是整数 `1`（裸描述符）。混用两者是经典 bug 来源（见 5.16 节的坑）。

### 5.13 为什么要缓冲

讲义第 26 页：

- 应用常常一次读/写一个字符：`getc`、`putc`、`ungetc`、`gets`、`fgets`，还有“逐字符读到换行为止”的读行逻辑。
- 若直接用 Unix I/O 实现，代价巨大：**`read` 和 `write` 需要陷入内核，超过 10,000 个时钟周期**。
- 解决方案：**缓冲读（buffered read）**
  - 用 `read` 一次抓取一块字节
  - 用户输入函数从缓冲区里一次取一个字节
  - 缓冲区空了再补充

图示把缓冲区标成两段：`already read`（已读）与 `unread`（未读）。

**缓冲写（第 27 页）**：

- 缓冲区在三种时机被**刷出（flush）**到输出 fd：
  1. 遇到 `"\n"`
  2. 调用 `fflush`
  3. 调用 `exit`，或从 `main` 返回
- 图示：`printf("h"); printf("e"); printf("l"); printf("l"); printf("o"); printf("\n"); fflush(stdout);` 之后，缓冲区里是 `hello\n` 六个字节，一次 `write(1, buf, 6)` 全部写出。

对比一下：六次 `printf` 只产生**一次** `write` 系统调用。这就是缓冲的全部价值。

**用 strace 看缓冲（第 28–30 页）**：

```
linux> strace ./hello
execve("./hello", ["hello"], [/* ... */]).
...
write(1, "hello\n", 6)               = 6
...
exit_group(0)                        = ?
```

程序里有六次 `printf`，`strace` 里只有**一次** `write(1, "hello\n", 6)`。这就是缓冲区在起作用的直接证据。

第 29–30 页展示完整的 `strace` 输出，可以看到程序启动时的一系列系统调用：

- `execve`：加载程序
- `brk`、`mmap`：分配内存
- `access("/etc/ld.so.preload", R_OK)`：检查预加载库
- `openat(AT_FDCWD, "/etc/ld.so.cache", O_RDONLY|O_CLOEXEC) = 3`：打开动态链接器缓存
- `fstat(3, ...)`、`mmap(...)`、`close(3)`：读取并映射
- `openat(..., "/lib/x86_64-linux-gnu/libc.so.6", ...) = 3`：加载 libc
- `read(3, "\177ELF\2\1\1\3...", ...)`：读 ELF 头（`\177ELF` 是 ELF 魔数）
- `fstat(1, {st_mode=S_IFCHR|0620, ...})`：检查 stdout 是不是终端（决定缓冲策略！）
- `getrandom(...)`：初始化
- `brk(NULL)` / `brk(0x...)`：确定堆起始并扩展
- `write(1, "hello\n", 6) = 6`：真正的输出
- `exit_group(0)`：进程退出

第 30 页的 `fstat(1, ...)` 特别值得注意：**标准 I/O 会检查输出目标是终端还是文件，并采用不同的缓冲策略**（终端上通常是行缓冲，文件上通常是全缓冲）。这解释了很多“重定向到文件后输出顺序变了”的谜题。

### 5.14 什么时候用哪套 I/O

**Unix I/O 的优缺点（第 33 页）**：

| 优点 | 缺点 |
|---|---|
| 最通用的 I/O 形式 | 处理短计数麻烦且易错 |
| 所有其它 I/O 包都是用 Unix I/O 实现的 | 高效读文本行需要某种缓冲，同样麻烦易错 |
| 提供访问文件元数据的函数 | |
| 函数**异步信号安全**，可用于信号处理函数 | |

**标准 I/O 的优缺点（第 34 页）**：

| 优点 | 缺点 |
|---|---|
| 缓冲减少 `read`/`write` 系统调用次数，提升效率 | 不提供访问文件元数据的函数 |
| 自动处理短计数 | 函数**不异步信号安全**，不适合信号处理函数 |
| | 不适合网络套接字上的输入输出 |
| | 流（stream）的限制与套接字的限制交互不良，文档又很差（CS:APP 3e 第 10.11 节） |

**选择原则（第 35 页）**：

- **通用规则：用你能用的最高层 I/O 函数。**
  - 很多 C 程序员完全靠标准 I/O 就能做完所有工作；
  - 但一定要理解你用的函数。
- **何时用标准 I/O**：处理“普通”文件时。
- **何时用裸 Unix I/O**：
  - 信号处理函数内部（因为 Unix I/O 异步信号安全）
  - 读写网络套接字时（可用专门做缓冲网络 I/O 的库简化：CS:APP 的 `rio_*`、libevent、libuv…）
  - 极少数需要绝对最高性能的场合

这三条判据其实可以浓缩成一句话：**便利层为“普通文件 + 单线程 + 无信号”这个默认场景优化，一旦离开这个场景，就得下沉到更底层。**

**二进制文件的额外禁忌（第 36 页）**：

- **绝不要对二进制文件用的函数**：
  - 面向文本的 I/O：`fgets`、`scanf`、`rio_readlineb`——它们会解释 EOL 字符
  - 字符串函数：`strlen`、`strcpy`、`strcat`——它们把字节值 `0`（字符串结尾）当作特殊
- 改用 `rio_readn` 或 `rio_readnb`。

理由很直白：二进制文件里 `0x0A` 和 `0x00` 都是普通数据，但文本函数会把它们当“行尾”和“字符串结束”。

### 5.15 元数据：struct stat

讲义第 38 页：

- **元数据是“关于数据的数据”**，这里是关于文件数据的数据。
- 每文件的元数据由内核维护，用户通过 `stat` / `fstat` 访问。

```c
/* Metadata returned by the stat and fstat functions */
struct stat {
    dev_t         st_dev;      /* Device */
    ino_t         st_ino;      /* inode */
    mode_t        st_mode;     /* Protection and file type */
    nlink_t       st_nlink;    /* Number of hard links */
    uid_t         st_uid;      /* User ID of owner */
    gid_t         st_gid;      /* Group ID of owner */
    dev_t         st_rdev;     /* Device type (if inode device) */
    off_t         st_size;     /* Total size, in bytes */
    unsigned long st_blksize;  /* Blocksize for filesystem I/O */
    unsigned long st_blocks;   /* Number of blocks allocated */
    time_t        st_atime;    /* Time of last access */
    time_t        st_mtime;    /* Time of last modification */
    time_t        st_ctime;    /* Time of last change */
};
```

`st_mode` 是“文件类型 + 权限位”的合体（第 7 讲链接部分讲过硬链接 `st_nlink`）。`st_atime`/`st_mtime`/`st_ctime` 分别是访问时间、内容修改时间、inode 变更时间——三者含义不同，`ctime` 不是“创建时间”。

### 5.16 内核如何表示打开的文件：三张表

讲义第 39 页，这是全讲的结构核心。

```
描述符表（每进程一张）        打开文件表（所有进程共享）      v-node 表（所有进程共享）
fd 0 ─────────────────────→  File pos
fd 1 ─────────────────────→  refcnt=1  ────────────────→  File access
fd 2 ─────────────────────→  ...                          File size
fd 3                                                        File type
fd 4 ─────────────────────→  File pos                     （即 stat 结构里的信息）
                             refcnt=1
                             ...
```

- **描述符表（descriptor table）**：每进程一张，把 fd 映射到打开文件表项。
- **打开文件表（open file table）**：所有进程共享，每项记录**文件位置（file pos）**与**引用计数（refcnt）**。
- **v-node 表（v-node table）**：所有进程共享，记录文件访问模式、大小、类型等 `stat` 信息。

第 39 页的情形：两个描述符引用**两个不同的打开文件**——fd 1（stdout）指向终端，fd 4 指向一个打开的磁盘文件。

**关键点：`File pos` 是每个“打开文件”维护的，不是每个 fd 维护的。** 这个细节决定了后面所有共享行为。

### 5.17 文件共享：同一文件的两个独立打开

讲义第 40 页：

- 两个不同的描述符通过**两个不同的打开文件表项**共享同一个磁盘文件。
- 例子：用同一个文件名调用 `open` 两次。

此时两个打开文件表项各有自己的 `File pos`，但 v-node 表项只有一个（“different logical but same physical file”）。后果：两个 fd 各自从头开始读，互不影响位置。

### 5.18 fork 与文件共享

讲义第 41–42 页：

- **子进程继承父进程的打开文件**。
- 注意：`exec` 系列函数**不改变**这一状况（要用 `fcntl` 才能改）。

**fork 之前**：父进程的描述符表里 fd 0–4 各指向一个打开文件表项，`refcnt=1`。

**fork 之后**：

- 子进程的描述符表**与父进程相同**（fd 编号与指向的表项都相同）；
- 每个打开文件表项的 `refcnt` **加 1**（变成 2）；
- 文件在进程之间共享。

**这一点极其重要**：父子进程共享的是**同一个打开文件表项**，因此共享**同一个 `File pos`**。子进程读走了 `a`，父进程的下一次读就从 `b` 开始。这正是下面 ffiles2 例子的全部玄机。

### 5.19 I/O 重定向与 dup2

讲义第 44 页：

- 问题：shell 怎么实现 I/O 重定向？`linux> ls > foo.txt`
- 答案：调用 `dup2(oldfd, newfd)`。
- 作用：把（每进程的）描述符表中 `oldfd` 那一项**复制到** `newfd` 那一项。

```
dup2(4, 1) 之前：        之后：
fd 0 → a                 fd 0 → a
fd 1 → b                 fd 1 → b     （现在指向 b，即 fd 4 的目标）
fd 2                     fd 2
fd 3                     fd 3
fd 4 → b                 fd 4 → b
```

**重定向的两步（第 45–46 页）**：

1. **第 1 步**：打开要重定向到的目标文件——发生在执行 shell 代码的子进程里，`exec` **之前**。
   - 此时 fd 3（或 4）指向新打开的磁盘文件，`refcnt=1`。
2. **第 2 步**：调用 `dup2(4, 1)`，让 fd 1（stdout）指向 fd 4 所指的磁盘文件。
   - 原来的终端文件表项 `refcnt` 从 1 变成 **0**，被释放；
   - 新的文件表项 `refcnt` 从 1 变成 **2**（fd 1 和 fd 4 都指向它）。

这就是 shell 里 `ls > foo.txt` 的全部机制：**在 exec 之前把 fd 1 改指向文件，`ls` 自己完全不知道发生了什么**。这也是“Unix 哲学”的漂亮之处——程序不需要支持重定向，重定向是 shell 在进程级别做的把戏。

### 5.20 三个经典例题

**ffiles1（第 47–48 页）**：文件内容 `abcde`

```c
fd1 = open(fname, O_RDONLY, 0);
fd2 = open(fname, O_RDONLY, 0);
fd3 = open(fname, O_RDONLY, 0);
dup2(fd2, fd3);
read(fd1, &c1, 1);
read(fd2, &c2, 1);
read(fd3, &c3, 1);
printf("c1 = %c, c2 = %c, c3 = %c\n", c1, c2, c3);
```

**答案：`c1 = a, c2 = a, c3 = b`**

推导：

- 三次 `open` 产生三个**独立**的打开文件表项，各有自己的 `File pos = 0`。
- `dup2(fd2, fd3)` 让 fd3 改指向 fd2 的表项，fd3 原来的表项 `refcnt` 归零被释放。
- `read(fd1)`：fd1 的表项 pos=0 → 读到 `a`，fd1 的 pos 变 1。
- `read(fd2)`：fd2 的表项 pos 还是 0 → 读到 `a`，该表项 pos 变 1。
- `read(fd3)`：fd3 现在与 fd2 **共享同一表项**，pos 已是 1 → 读到 `b`。

这道题的唯一考点就是“`File pos` 属于打开文件表项，`dup2` 让两个 fd 共享表项”。

**ffiles2（第 49–50 页）**：文件内容 `abcde`

```c
int fd1;
int s = getpid() & 0x1;
char c1, c2;
fd1 = open(fname, O_RDONLY, 0);
read(fd1, &c1, 1);
if (fork()) { /* Parent */
    sleep(s);
    read(fd1, &c2, 1);
    printf("Parent: c1 = %c, c2 = %c\n", c1, c2);
} else { /* Child */
    sleep(1-s);
    read(fd1, &c2, 1);
    printf("Child: c1 = %c, c2 = %c\n", c1, c2);
}
```

**答案取决于 `getpid() & 0x1`**，讲义给了两种可能：

```
Child: c1 = a, c2 = b
Parent: c1 = a, c2 = c
```
或
```
Parent: c1 = a, c2 = b
Child: c1 = a, c2 = c
```

推导：

- `open` 发生在 `fork` **之前**，所以只有一个打开文件表项（`refcnt=1`）。
- `read(fd1, &c1, 1)` 也发生在 fork 之前，父子进程的 `c1` 都是 `a`（fork 复制了地址空间）。
- `fork` 之后 `refcnt=2`，父子**共享同一个 `File pos`**（此时 pos=1）。
- `s = getpid() & 0x1` 决定谁先睡：睡 0 的那个先跑，读走 `b`（pos→2）；睡 1 的后跑，读走 `c`（pos→3）。
- 因此**先打印的那行 `c2 = b`，后打印的那行 `c2 = c`**，而谁的 `c1` 都是 `a`。

这道题把“`fork` 共享打开文件表项”讲透了：**`c2` 不同，正说明 `File pos` 是共享的；`c1` 相同，正说明内存是复制的。**

## 6. 代码示例

### 6.1 官方课程代码

**标准 I/O 的底层实现（18-system-io.pdf 第 3 页）**：`fopen`/`fputs`/`fclose` 的展开，以及 `close` 的汇编 `mov $3, %eax; syscall; cmp $-4096, %rax; jae __syscall_error`。

**两套函数对照图（18-system-io.pdf 第 4 页）**：Unix I/O、RIO、标准 I/O 三列，标注控制力/便利性/信号安全/网络适用性。

**`open` 打开文件（18-system-io.pdf 第 13 页）**：

```c
int fd;
if ((fd = open("/etc/hosts", O_RDONLY)) < 0) {
    perror("open");
    exit(1);
}
```

**`open` 的 flag 全表（18-system-io.pdf 第 14 页）**：`O_RDONLY`/`O_WRONLY`/`O_RDWR`、`O_CREAT`/`O_EXCL`/`O_APPEND`/`O_TRUNC`/`O_CLOEXEC`。

**`close` 的延迟错误（18-system-io.pdf 第 16 页）**：

```c
if (close(fd) < 0) {
    fprintf(stderr, "%s: write error: %s", filename, strerror(errno));
    exit(1);
}
```

**`read`（第 17 页）/ `write`（第 18 页）**：基本用法与“短计数不是错误”。

**逐字节 cat 的三个版本（18-system-io.pdf 第 19–21 页）**：天真版（不检查返回值）、健壮版（区分 EOF/错误）、Stevens 包装版（`Read`/`Write`）。

**缓冲的证据（18-system-io.pdf 第 28–30 页）**：`strace ./hello` 显示六次 `printf` 只产生一次 `write(1, "hello\n", 6)`。

**`struct stat`（第 38 页）**：十三个字段的完整定义。

**三张表（18-system-io.pdf 第 39–43 页）**：描述符表 / 打开文件表 / v-node 表；两个独立打开；`fork` 后 `refcnt` 加 1。

**`dup2` 重定向（18-system-io.pdf 第 44–46 页）**：`ls > foo.txt` 的两步实现，`refcnt` 从 1→0 与 1→2。

**`ffiles1.c`（第 47–48 页）**：答案 `c1 = a, c2 = a, c3 = b`。

**`ffiles2.c`（第 49–50 页）**：答案随 `getpid() & 0x1` 变化，先跑者读 `b`，后跑者读 `c`。

**RIO 接口（补充页第 52–55 页）**：

```c
ssize_t rio_readn(int fd, void *usrbuf, size_t n);
ssize_t rio_writen(int fd, void *usrbuf, size_t n);
void    rio_readinitb(rio_t *rp, int fd);
ssize_t rio_readlineb(rio_t *rp, void *usrbuf, size_t maxlen);
ssize_t rio_readnb(rio_t *rp, void *usrbuf, size_t n);
```

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

一个正确处理 EOF / 错误 / 短计数的 `cat`（比讲义第 20 页进一步加了缓冲）：

```c
/* 非官方示例：健壮的 cat，用固定缓冲区循环读写 */
#include <unistd.h>
#include <stdio.h>
#include <errno.h>

int main(void) {
    char buf[8192];
    for (;;) {
        ssize_t n = read(STDIN_FILENO, buf, sizeof buf);
        if (n == 0) break;                  /* EOF */
        if (n < 0) {
            if (errno == EINTR) continue;   /* 被信号打断，重试 */
            perror("read"); return 1;
        }
        char *p = buf;
        while (n > 0) {                     /* 写也要处理短计数 */
            ssize_t w = write(STDOUT_FILENO, p, (size_t)n);
            if (w < 0) {
                if (errno == EINTR) continue;
                perror("write"); return 1;
            }
            if (w == 0) { perror("write: 0"); return 1; }
            p += w; n -= w;
        }
    }
    return 0;
}
```

三点与讲义呼应：(1) `n == 0` 才是 EOF，`n < 0` 是错误；(2) `EINTR` 必须重试，否则信号一到读就失败；(3) 写侧同样要循环，因为 `write` 也可能短计数。

用 `dup2` 手工实现 `./prog > out.txt`：

```c
/* 非官方示例：不用 shell，用 dup2 把 stdout 重定向到文件 */
#include <fcntl.h>
#include <stdio.h>
#include <unistd.h>

int main(void) {
    int fd = open("out.txt", O_WRONLY | O_CREAT | O_TRUNC, DEFFILEMODE);
    if (fd < 0) { perror("open"); return 1; }

    dup2(fd, STDOUT_FILENO);   /* 现在 fd 1 指向 out.txt */
    close(fd);                 /* 原 fd 不再需要；注意此时 refcnt 从 2 降到 1 */

    printf("this goes to out.txt\n");
    fflush(stdout);            /* 标准 I/O 有缓冲，务必刷出 */
    return 0;
}
```

注意两个坑：`dup2` 之后 `close(fd)` 是安全的，因为 fd 1 已持有同一表项（`refcnt` 2→1）；以及**必须 `fflush`**，否则缓冲区里的内容在 `exit` 前还没走到新 fd——实践中这一步常被忽略却“碰巧能工作”，因为从 `main` 返回会自动 flush。

演示 `fork` 后父子共享文件位置（复现 ffiles2 的机制）：

```c
/* 非官方示例：父子共享 File pos，因此各自读到不同的字符 */
#include <fcntl.h>
#include <stdio.h>
#include <unistd.h>
#include <sys/wait.h>

int main(void) {
    int fd = open("abcde.txt", O_RDONLY);   /* 内容 "abcde" */
    char c1, c2;
    read(fd, &c1, 1);                        /* 父子都是 'a'（fork 前读） */

    pid_t pid = fork();
    if (pid == 0) {
        read(fd, &c2, 1);                    /* 先跑：读 'b' */
        printf("child : c1=%c c2=%c\n", c1, c2);
        _exit(0);
    }
    waitpid(pid, NULL, 0);                   /* 等子进程读完再读，保证顺序 */
    read(fd, &c2, 1);                        /* 后跑：读 'c' */
    printf("parent: c1=%c c2=%c\n", c1, c2);
    close(fd);
    return 0;
}
```

输出固定为 `child : c1=a c2=b` / `parent: c1=a c2=c`。把 `open` 挪到 `fork` **之后**，父子就会各有一个打开文件表项，各自读到 `a`——这一个改动就能验证“共享的是表项而不是文件”。

用 RIO 读文本行（避免短计数带来的麻烦）：

```c
/* 非官方示例：rio_readlineb 逐行读，短计数由库处理 */
#include "csapp.h"

int main(void) {
    rio_t rio;
    char line[MAXLINE];
    rio_readinitb(&rio, STDIN_FILENO);
    while (rio_readlineb(&rio, line, MAXLINE) > 0)
        rio_writen(STDOUT_FILENO, line, strlen(line));
    return 0;
}
```

注意讲义补充页的警告：`rio_readlineb`/`rio_readnb` 可以任意交错，但**不要与 `rio_readn` 交错**——因为前者有内部缓冲，后者没有，混用会导致缓冲区里的字节被跳过。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| `stdout`（`FILE *`） | `STDOUT_FILENO`（`1`） | 前者是带缓冲的流对象，后者是裸描述符；`fprintf(stdout,…)` 与 `write(1,…)` 混用会乱序 |
| `FILE *` | `fd` | 前者是标准 I/O 的流（含缓冲区），后者是 Unix I/O 的描述符；`fileno(fp)` 可以从前者取后者 |
| 短计数 | 错误 | 短计数是正常现象（`n >= 0`），错误是 `n < 0`；两者必须分开处理 |
| EOF | 错误 | `read` 返回 **0** 是 EOF；返回**负数**才是错误 |
| `close` 失败 | 文件没关掉 | `close` 出错时文件**已被关闭**，错误来自之前某次写的延迟报告 |
| `dup2` | `open` 两次 | 前者让两个 fd **共享**打开文件表项（共享 `File pos`）；后者产生两个独立表项 |
| `fork` 后共享文件 | `fork` 后共享内存 | 文件表项**真的共享**（`refcnt` 共享）；内存是**复制**的（COW 后才分离） |
| 文本文件 | 二进制文件 | 前者有行尾语义（`0x0A`）；后者只是字节；`fgets`/`strlen` 不能用于后者 |
| 行缓冲 | 全缓冲 | 终端上通常行缓冲（遇 `\n` 刷出）；重定向到文件时通常全缓冲（缓冲区满才刷出） |
| `fflush` | `fsync` | 前者把用户态缓冲区交给内核；后者要求内核把数据真正落盘 |
| Unix I/O | 标准 I/O（信号语境） | 前者异步信号安全（`write` 可用）；后者**不安全**（`printf`/`malloc` 不可用） |
| `rio_readn` | `rio_readnb` | 前者无缓冲，只在 EOF 才短计数；后者有缓冲，可与 `rio_readlineb` 交错 |

## 8. 对应原版讲义

- PDF 相对路径：`90-原始PDF/15-213/lectures/18-system-io.pdf`
- 总页数：54 页
- 重点页码（以 PDF 页码为准；讲义印刷页码自 PDF 第 39 页起比 PDF 页码大 1）：
  - 标题页（18th Lecture, November 5, 2026）：第 2 页
  - 标准 I/O 展开成 Unix I/O 的三段实现 + `close` 汇编：第 3 页
  - 两套函数对照图（控制力/便利性/信号安全/网络）：第 4 页
  - 今日大纲与 CSAPP 对应章节：第 5 页
  - 文件是字节序列、一切皆文件：第 6 页
  - Unix I/O 五个基本操作与文件位置：第 7 页
  - 文件类型：第 8 页
  - 普通文件、文本/二进制、EOL（LF vs CRLF）：第 9 页
  - 目录与 `.`/`..`：第 10 页
  - 目录层次与 cwd：第 11 页
  - 绝对/相对路径名：第 12 页
  - 打开文件、fd 0/1/2：第 13 页
  - `open` 的 flag 全表：第 14 页
  - `open` 第三个参数与 `umask`/`DEFFILEMODE`：第 15 页
  - 关闭文件与延迟错误：第 16 页
  - 读文件与短计数：第 17 页
  - 写文件与短计数：第 18 页
  - 逐字节 cat（天真版）：第 19 页
  - 逐字节 cat（健壮版）：第 20 页
  - 逐字节 cat（Stevens 包装）：第 21 页
  - 短计数的出现/不出现场景：第 22 页
  - 今日大纲（第二段）：第 23 页
  - 标准 I/O 函数清单：第 24 页
  - 流 `FILE *` 与三个标准流：第 25 页
  - 缓冲的动机（>10,000 时钟周期）：第 26 页
  - 缓冲写与三种 flush 时机：第 27 页
  - `strace ./hello` 看到一次 write：第 28 页
  - `strace` 完整输出（启动阶段）：第 29 页
  - `strace` 完整输出（输出与退出）：第 30 页
  - 课堂 quiz 链接：第 31 页
  - Unix I/O 优缺点：第 33 页
  - 标准 I/O 优缺点：第 34 页
  - 选择原则：第 35 页
  - 二进制文件的禁忌函数：第 36 页
  - `struct stat` 全字段：第 38 页
  - 三张表（描述符表/打开文件表/v-node 表）：第 39 页
  - 文件共享（两个独立打开）：第 40 页
  - `fork` 之前：第 41 页
  - `fork` 之后（`refcnt=2`）：第 42 页
  - `dup2(oldfd, newfd)` 图示：第 44 页
  - 重定向第 1 步（打开目标文件）：第 45 页
  - 重定向第 2 步（`dup2` 后 `refcnt` 1→0 与 1→2）：第 46 页
  - `ffiles1.c` 题目与答案：第 47–48 页
  - `ffiles2.c` 题目与答案：第 49–50 页
  - 补充页首页：第 51 页
  - RIO 包介绍：第 52 页
  - `rio_readn` / `rio_writen`：第 53 页
  - `rio_readinitb` / `rio_readlineb` / `rio_readnb`：第 54–55 页
- 原始链接：https://www.cs.cmu.edu/~213/lectures/18-system-io.pdf
- 待核实：讲义第 18 页 `write` 示例的括号位置有误（`sizeof(buf)) < 0)`），应为 `sizeof(buf))) < 0)`；讲义印刷页码自 PDF 第 39 页起比 PDF 页码大 1（如 PDF p.39 印作 40），引用时需注意。

## 9. 对应视频

未找到官方公开录像。

## 10. 本节复习

- 文件 = 字节序列；一切设备与内核数据结构都以文件暴露。
- Unix I/O 五原语：`open`/`close`/`read`/`write`/`lseek`，加 `stat`/`fstat`/`lstat` 取元数据。
- `open` 两种形式：`open(path, flags)` 与 `open(path, flags, mode)`；`mode` 只在含 `O_CREAT` 时有用。
- fd 0/1/2 = stdin/stdout/stderr；`-1` 表示出错。
- `read`/`write` 返回 `ssize_t`：`0` = EOF（仅读），`<0` = 错误，正数可能小于请求（短计数）。
- 短计数必现于：EOF、终端、套接字/管道；不出现于：磁盘文件读写。
- `close` 可能报告之前写的延迟错误，必须检查返回值；不要重复关闭。
- 标准 I/O 流 = fd + 缓冲区；flush 时机：`\n`、`fflush`、`exit`/`main` 返回。
- 缓冲的价值：六次 `printf` → 一次 `write`。
- 三张表：描述符表（每进程）、打开文件表（全局，含 `File pos` 与 `refcnt`）、v-node 表（全局，含 `stat` 信息）。
- `fork` 后子进程继承描述符表，`refcnt` 加 1，**共享 `File pos`**。
- `dup2(oldfd, newfd)` 让 `newfd` 指向 `oldfd` 的表项；旧表项 `refcnt` 减 1，减到 0 就释放。
- 选择 I/O：普通文件用标准 I/O；信号处理函数与套接字用 Unix I/O 或 RIO；二进制文件禁用文本函数与字符串函数。

## 11. 自我检查

1. `read` 返回 0、返回 `-1`、返回小于请求的正数，三者分别是什么意思？哪一个最常见于网络编程？
2. 为什么 `printf("h"); printf("e"); ... fflush(stdout);` 在 `strace` 里只有一次 `write`？如果去掉 `fflush` 会怎样？
3. `ffiles1.c` 中为什么 `c2` 是 `a` 而 `c3` 是 `b`？如果去掉 `dup2(fd2, fd3)` 这行，三个字符会是什么？
4. `ffiles2.c` 中父子进程的 `c1` 相同但 `c2` 不同，这两件事分别证明了什么？
5. 为什么信号处理函数里能用 `write` 但不能用 `printf`？如果要输出格式化内容该怎么办？

<details>
<summary>参考答案</summary>

1. 返回 `0` 表示 EOF（读到了文件末尾，没有更多数据）；返回 `-1` 表示出错（具体原因在 `errno`，如 `EINTR` 表示被信号打断、`EBADF` 表示 fd 无效）；返回小于请求的正数就是**短计数**——只读到了这么多字节，不是错误。在网络编程中最常见的是**短计数**：套接字的接收缓冲区此刻只有那么多数据可读，所以网络代码必须循环读或使用 RIO。

2. 因为标准 I/O 有用户态缓冲区：六次 `printf` 只是把六个字节陆续放进缓冲区，一次 `write` 系统调用都没有发生；`fflush(stdout)` 把缓冲区里的 `hello\n` 一次性 `write(1, buf, 6)` 出去，所以 `strace` 只看到一次 `write`。去掉 `fflush` 也仍然只会看到一次 `write`——因为从 `main` 返回（或调用 `exit`）时会自动 flush 所有流；但若程序在 flush 之前被 `_exit` 或信号终止，缓冲区里的内容就会**丢失**。

3. 三次 `open` 产生三个独立的打开文件表项，各有自己的 `File pos=0`。`dup2(fd2, fd3)` 让 fd3 改指向 fd2 的表项，因此 fd2 和 fd3 共享同一个 `File pos`。`read(fd1)` 读走 `a`（fd1 的 pos→1）；`read(fd2)` 从 fd2 表项的 pos=0 读走 `a`（pos→1）；`read(fd3)` 共享 fd2 表项、pos 已是 1，读走 `b`。若去掉 `dup2`，fd3 保留自己的表项（pos=0），三个字符就是 `a`、`a`、`a`。

4. `c1` 相同证明 `fork` **复制了内存**：`c1` 在 `fork` 之前被赋值，父子各有一份副本，所以都是 `a`。`c2` 不同证明 `fork` **共享打开文件表项**：父子指向同一个表项，也就共享同一个 `File pos`，谁先读谁拿到 `b`，另一个拿到 `c`。（顺带说明：`getpid() & 0x1` 只决定谁先跑，不影响“共享”这个结论。）

5. `printf` 内部有静态缓冲区和锁，若主程序正在 `printf` 中途被信号打断、处理函数又调用 `printf`，缓冲区会处于半更新状态，导致输出错乱甚至死锁，因此它不在 POSIX 保证的 117 个异步信号安全函数里。`write` 是无缓冲的系统调用，每次调用独立完成、没有跨调用的共享状态，所以安全。若需要格式化输出，用 CS:APP 的 `sio_printf`/`sio_puts`（内部最终只调 `write`），或自己用 `snprintf` 拼到栈上缓冲区后调用 `write`（注意 `snprintf` 本身的安全性在信号处理函数中同样有争议，最稳妥是 `sio_*`）。

</details>

## 12. 进一步学习

- 前一讲：[[15-213-17-Exceptional-Control-Flow]]
- 课程总览：[[20-CMU-15-213/00-课程总览|CMU 15-213 - 课程总览]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]（File Descriptor 文件描述符）
- 实验：[[00-Lab总览]]——Tsh Lab 的输入输出与重定向几乎完全建立在本讲之上；`csapp.c` 里的 `rio_*` 与 `sio_*` 是 Tsh Lab 的标准工具箱。
- CSAPP 第 3 版第 10 章；重点读 10.11 节“Putting It Together: Which I/O Functions Should I Use?”以及该节关于流与套接字限制的讨论。
- 手册页：`man 2 open`、`man 2 read`、`man 2 dup2`、`man 2 stat`；RIO 源码见 `http://csapp.cs.cmu.edu/3e/code.html` → `src/csapp.c`、`include/csapp.h`。
- `strace` 是理解本讲所有抽象的最佳工具：`strace -e trace=openat,read,write,close ./prog` 能把“标准 I/O → Unix I/O”的翻译过程完整摊开。
