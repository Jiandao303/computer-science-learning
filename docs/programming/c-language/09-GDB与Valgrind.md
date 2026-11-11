---
title: 09 GDB 与 Valgrind
description: 编译错误、逻辑错误与段错误的区分；GDB 断点/单步/调用栈；Valgrind 内存检查；AddressSanitizer 入门
date: 2026-11-11
---

# 09 GDB 与 Valgrind

> 对应模块 09。**调试能力的分水岭是：出问题时你会不会立刻打开调试器，而不是加 `printf` 猜。** 15-213 的 `bomblab` 与 `malloclab` 都要求熟练使用 GDB。

## 学习目标

1. 区分编译错误、链接错误、运行时错误（段错误）与逻辑错误。
2. 用 GDB 设置断点、单步、查看变量、查看调用栈、查看内存。
3. 用 GDB 定位一次段错误（segmentation fault）。
4. 用 Valgrind 检测内存泄漏与越界。
5. 用 `-fsanitize=address` 在编译期启用 AddressSanitizer。

## 前置知识

- [05-内存管理](05-内存管理.md)、[08-编译与链接](08-编译与链接.md)。
- 编译时必须带 `-g`，否则 GDB 没有行号信息。

## 核心概念

### 1. 四类错误的区分

| 类型 | 何时发现 | 典型信息 |
| --- | --- | --- |
| 编译错误 | 编译时 | `error: expected ';'` |
| 链接错误 | 链接时 | `undefined reference to 'f'` |
| 运行时错误 | 运行时 | `Segmentation fault (core dumped)` |
| 逻辑错误 | 结果不对 | 程序正常结束，答案错 |

**段错误（segmentation fault）** = 访问了不属于自己的内存页。常见原因：

```c
int *p = NULL;
*p = 1;                  /* 解引用空指针 */

int a[3];
a[100] = 1;              /* 越界写（不一定立刻崩，可能静默破坏） */

free(p);
*p = 1;                  /* use-after-free */
```

### 2. GDB 基本流程

```bash
gcc -std=c11 -g -O0 prog.c -o prog    # 必须带 -g
gdb ./prog
```

```text
(gdb) break main          # 在 main 下断点
(gdb) run                 # 运行
(gdb) next                # 下一行（不进入函数）
(gdb) step                # 下一行（进入函数）
(gdb) print x             # 打印变量
(gdb) backtrace           # 查看调用栈
(gdb) frame 1             # 切换到第 1 帧
(gdb) continue            # 继续运行
(gdb) quit                # 退出
```

### 3. GDB 常用命令表

| 命令 | 简写 | 作用 |
| --- | --- | --- |
| `break file:line` | `b` | 在指定行下断点 |
| `break func` | `b` | 在函数入口下断点 |
| `run [args]` | `r` | 运行 |
| `next` | `n` | 单步，不进入函数 |
| `step` | `s` | 单步，进入函数 |
| `finish` | — | 运行到当前函数返回 |
| `print expr` | `p` | 打印表达式 |
| `print *ptr` | `p *ptr` | 打印指针指向的内容 |
| `print arr[0]@5` | — | 打印数组前 5 个元素 |
| `x/4xb ptr` | — | 以十六进制看 4 个字节 |
| `backtrace` | `bt` | 调用栈 |
| `info locals` | — | 当前帧所有局部变量 |
| `info frame` | — | 当前帧信息 |
| `watch x` | — | 监视变量，变化时停下 |
| `delete` | `d` | 删除断点 |
| `list` | `l` | 显示源码 |

### 4. 定位段错误

```bash
gcc -g -O0 crash.c -o crash
./crash                     # Segmentation fault
gdb ./crash
(gdb) run                   # 停在崩溃处
(gdb) backtrace             # 看是哪一行
(gdb) print ptr             # 看指针值（是否为 NULL 或垃圾值）
```

**没有 GDB 时**：开 core dump（`ulimit -c unlimited`），然后 `gdb ./prog core`。

### 5. Valgrind

Valgrind 在运行时监控内存访问，**不需要重新编译**（但带 `-g` 信息更全）。

```bash
valgrind --leak-check=full --show-leak-kinds=all ./prog
```

典型输出：

```text
==12345== HEAP SUMMARY:
==12345==     in use at exit: 40 bytes in 1 blocks
==12345==   total heap usage: 1 allocs, 0 frees, 40 bytes allocated
==12345==
==12345== 40 bytes in 1 blocks are definitely lost in loss record 1 of 1
==12345==    at 0x4C2FB0F: malloc (in /usr/lib/valgrind/...)
==12345==    by 0x108697: leak (leak.c:5)
==12345==    by 0x1086A7: main (leak.c:10)
```

| 报告类型 | 含义 |
| --- | --- |
| `definitely lost` | 确定泄漏：没有任何指针指向它 |
| `indirectly lost` | 间接泄漏：被泄漏的结构体引用 |
| `possibly lost` | 可能有泄漏：内部指针指向块中间 |
| `still reachable` | 程序结束时仍可达（常见于全局缓存，通常无害） |
| `Invalid write of size N` | 越界写 |
| `Invalid read of size N` | 越界读 |
| `Use of uninitialised value` | 使用未初始化内存 |

### 6. AddressSanitizer

编译期插桩，比 Valgrind 快得多（约 2 倍开销 vs 20 倍）。

```bash
gcc -std=c11 -g -O1 -fsanitize=address -fno-omit-frame-pointer prog.c -o prog
./prog
```

典型输出：

```text
==12345==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x...
WRITE of size 4 at 0x... thread T0
    #0 0x... in overflow /home/user/overflow.c:8
    #1 0x... in main /home/user/overflow.c:12
```

| 选项 | 检测 |
| --- | --- |
| `-fsanitize=address` | 越界、use-after-free、double free |
| `-fsanitize=undefined` | 有符号溢出、移位越界、空指针解引用 |
| `-fsanitize=leak` | 内存泄漏 |

**建议**：本地开发时 `-fsanitize=address,undefined` 一起开。

## 英文术语与中文解释

| 英文 | 中文 | 一句话 |
| --- | --- | --- |
| breakpoint | 断点 | 程序运行到这里暂停 |
| step into / over | 单步进入 / 跳过 | 是否进入函数体 |
| call stack | 调用栈 | 当前函数调用链 |
| frame | 栈帧 | 调用栈中的一层 |
| segmentation fault | 段错误 | 访问非法内存页 |
| core dump | 核心转储 | 崩溃时的内存快照 |
| memory leak | 内存泄漏 | 分配未释放 |
| instrumentation | 插桩 | 在代码中插入检查 |

## 通俗类比

- **GDB** = 视频播放器的暂停键 + 逐帧播放。你可以随时停下来看每一帧的状态。
- **Valgrind** = 事后审计员。程序跑完后，它告诉你哪些内存被借了没还、哪些门被强行撬开过。

## 原理讲解

### GDB 如何知道行号

`-g` 让编译器在可执行文件里写入**调试信息**（DWARF 格式），记录「地址 → 源文件:行号 → 变量名」的映射。没有 `-g`，GDB 只能看汇编。

### `-O2` 为什么破坏调试

优化器会：

1. 把变量放进寄存器（`print x` 显示 `<optimized out>`）。
2. 重排语句（`next` 跳来跳去）。
3. 内联函数（`backtrace` 看不到调用帧）。

**调试时一律 `-O0`。**

### Valgrind 的工作方式

Valgrind 把程序放在一个**虚拟 CPU** 上运行，每条内存访问都被拦截并检查。这就是它慢 20 倍的原因，也是它能检测「读未初始化内存」这类 ASan 检测不到的问题的原因。

### ASan 的工作方式

编译时在每个内存访问前后插入检查代码，并在每块分配周围放**红区（redzone）**。越界访问红区立刻报错。开销小，但需要重新编译。

## 内存示意图

### 一次段错误的现场

```c
int main(void) {
    int *p = NULL;
    *p = 42;            /* 崩溃在这一行 */
    return 0;
}
```

```text
gdb 输出：
Program received signal SIGSEGV, Segmentation fault.
0x0000555555555159 in main () at crash.c:3
3           *p = 42;

(gdb) print p
$1 = (int *) 0x0        <- 空指针

(gdb) backtrace
#0  main () at crash.c:3
```

### 堆越界的红区（ASan）

```text
+----------+------------------+----------+
| 红区      | 用户数据（4 字节）  | 红区      |
+----------+------------------+----------+
           ^
           malloc 返回
写入 p[1] 落在右侧红区 -> ASan 立刻报 heap-buffer-overflow
```

## 代码示例

```c
/* day09_buggy.c —— 故意包含三类错误，用于练习调试 */
#include <stdio.h>
#include <stdlib.h>

static int *make_array(int n) {
    int *p = malloc((size_t)n * sizeof *p);
    /* 错误 1：没有检查 p == NULL */
    for (int i = 0; i <= n; i++) {   /* 错误 2：i <= n 越界写 */
        p[i] = i;
    }
    return p;                        /* 错误 3：调用者不知道要 free */
}

int main(void) {
    int *a = make_array(4);
    int sum = 0;
    for (int i = 0; i < 4; i++) sum += a[i];
    printf("sum = %d\n", sum);
    return 0;                        /* 错误 4：泄漏 */
}
```

## 逐行代码解释

| 行 | 说明 |
| --- | --- |
| `malloc((size_t)n * sizeof *p)` | 正确写法；但仍需检查 `NULL` |
| `i <= n` | 越界写 `p[n]`，ASan 会报 heap-buffer-overflow |
| `return p;` | 所有权转移给调用者，应注释说明 |
| `return 0;` | 未 `free(a)`，Valgrind 报 definitely lost |

**练习**：用 GDB 与 ASan 分别定位这三个问题，并修复。

## 常见错误

| 错误 | 后果 | 正确做法 |
| --- | --- | --- |
| 编译不带 `-g` | GDB 没有行号与变量名 | 调试构建加 `-g -O0` |
| 用 `-O2` 调试 | 变量 `<optimized out>` | 改 `-O0` |
| 只加 `printf` 猜 | 定位慢、可能改变时序 | 用 GDB |
| Valgrind 报 `still reachable` 就慌 | 多半是全局缓存，无害 | 看 `definitely lost` |
| 不读 ASan 的调用栈 | 只看到第一行 | 往下读 `#0` `#1` 的源码行 |
| 在崩溃点之后继续跑 | 现场被破坏 | 崩溃后先 `backtrace` |

## 边界情况

- **ASan 与 Valgrind 不能同时用**：都会接管内存，选一个。
- **`-fsanitize=address` 需要 `-fno-omit-frame-pointer`** 才有完整调用栈。
- **GDB 的 `print` 对 `void *`**：需要先强转 `(int *)p`。
- **多线程调试**：`info threads`、`thread N`。
- **`watch` 有性能代价**：只在小范围使用。

## 实践练习

`exercises/C-Language/Day-07/`（GDB 与编译同一天）：

| 文件 | 任务 |
| --- | --- |
| `ex7_gdb_crash.c` | 制造空指针解引用，用 GDB 找到行号与 `p` 的值 |
| `ex8_valgrind_leak.c` | 制造泄漏，用 Valgrind 定位并修复 |
| `ex9_asan_overflow.c` | 制造越界写，用 ASan 定位并修复 |
| `ex10_backtrace.c` | 三层函数调用中出错，用 `backtrace` 找到源头 |

## 测试用例

```text
ex7_gdb_crash:     gdb -> run -> SIGSEGV -> bt 显示崩溃行；print p 得到 0x0
ex8_valgrind_leak: valgrind --leak-check=full 报告 definitely lost
ex9_asan_overflow: 运行输出 "heap-buffer-overflow" 并指出源文件行号
ex10_backtrace:    bt 显示 #0 f3 #1 f2 #2 f1 #3 main
```

## 测试结果

| 项目 | 命令 | 结果 |
| --- | --- | --- |
| GDB | `gdb --version` | **本机 WSL 未安装 gdb，待 `sudo apt install gdb` 后运行** |
| Valgrind | `valgrind --version` | **本机 WSL 未安装 valgrind，待 `sudo apt install valgrind` 后运行** |
| ASan | `gcc -fsanitize=address ...` | 待运行 |

> **如实记录**：本机 WSL Ubuntu 只装了 `gcc 13.3.0` 与 `make 4.3`，没有 `gdb` 与 `valgrind`。笔记中的命令与输出格式依据标准工具行为编写，但**未在本机实际执行**。装好后再回填本表。

## 对应原版资料

- **CMU C Boot Camp（S23）**：`90-原始PDF/15-213/bootcamps/cprogramming-bootcamp-s23.pdf`
  - p20：C Tools（Git / Valgrind / GDB）
  - p26：Valgrind
  - p27–p29：What's wrong? 反例 / Hooray!
  - p30：GDB
  - p48–p49：`parse_int` / `echo` 反例
- **官方链接**：https://www.cs.cmu.edu/~213/bootcamps/cprogramming-bootcamp-s23.pdf

## 对应官方来源

- GDB 官方文档：https://sourceware.org/gdb/documentation/
- Valgrind 官方文档：https://valgrind.org/docs/manual/manual.html
- AddressSanitizer：https://clang.llvm.org/docs/AddressSanitizer.html
- 15-213 Bootcamp 2（Debugging & GDB）：https://www.cs.cmu.edu/~213/schedule.html
- 后续衔接：[[15-213-08-Design-and-Debugging]]

## 自我检查问题

1. 编译错误、链接错误、运行时错误、逻辑错误分别在哪一步发现？
2. 为什么调试必须用 `-g -O0`？
3. `next` 与 `step` 的区别？
4. 段错误最常见的三个原因是什么？
5. `definitely lost` 与 `still reachable` 有什么区别？哪个才是真泄漏？
6. ASan 与 Valgrind 各自的优缺点？为什么不能同时用？
7. 如何查看一个指针指向的 4 个字节？

## 本节总结

- 调试构建：`-g -O0`；发布构建：`-O2`。
- GDB：`break` / `run` / `next` / `step` / `print` / `backtrace`。
- Valgrind：`--leak-check=full`，关注 `definitely lost`。
- ASan：`-fsanitize=address`，比 Valgrind 快，需要重新编译。

## 下一节

→ [10-综合练习](10-综合练习.md)
