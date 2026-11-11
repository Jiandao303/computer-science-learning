# exercises/C-Language/

C 语言练习代码。**这些文件会进入公开仓库**，所以：

- 只放**自己写的**练习代码；
- 不放课程 handout、作业原始代码、他人解答；
- 不复制 CMU 的 `cprogramminglab` 代码。

## 结构

```text
C-Language/
├── Day-01/  基础语法
├── Day-02/  数组与字符串
├── Day-03/  指针
├── Day-04/  结构体与数据结构
├── Day-05/  内存管理
├── Day-06/  二进制与位运算
├── Day-07/  函数指针 / 编译链接 / 调试
└── Day-08/  综合项目 memtool
```

## 怎么跑

在 WSL / Linux 下：

```bash
bash scripts/c-language/run_exercises.sh
```

脚本会自动发现 `Day-0*/` 下所有 `.c`，用固定参数编译并运行：

```bash
gcc -std=c11 -Wall -Wextra -Wpedantic -g -O0
```

## 已完成并实测通过

| 文件 | 主题 | 实测输出 |
| --- | --- | --- |
| `Day-01/ex1_types.c` | 类型大小 | `char=1 int=4 long=8 ptr=8` |
| `Day-01/ex2_swap.c` | 值传递 vs 指针 | `after pointer swap: a=2 b=1` |
| `Day-01/ex3_static.c` | `static` 局部变量 | `counter: 1 2 3` |
| `Day-02/ex1_array_sum.c` | 数组求和/最大值 | `sum=24 max=9 n=5` |
| `Day-02/ex3_strncpy_trap.c` | `strncpy` 陷阱 | `raw_has_nul=0` / `safe="abcdefg"` |
| `Day-03/ex1_swap_ptr.c` | 指针与二级指针 | `x=2 y=1` / `reset: NULL` |
| `Day-04/ex1_struct_basic.c` | 结构体 | `area=12 perimeter=14` |
| `Day-04/ex2_struct_size.c` | padding | `bad_order sizeof=12` / `good_order sizeof=8` |
| `Day-04/ex3_linked_list.c` | 链表 | `3 -> 2 -> 1 -> 4` |
| `Day-05/ex2_realloc_grow.c` | 动态数组 | `len=10 cap=16` |
| `Day-06/ex2_masks.c` | 位掩码 | `set_bit(0,3)=8` |
| `Day-07/ex1_funcptr_basic.c` | 函数指针 | `add(7,3)=10` |
| `Day-07/multi/` | 多文件 + Makefile | `add(2,3) = 5` / `sum = 10` |

**未完成**：Day-08 的 `memtool` 综合项目（结构已在 [10-综合练习](../../docs/programming/c-language/10-综合练习.md) 给出，需自己实现）。

## 相关

- [00-C语言学习总览](../../docs/programming/c-language/00-C语言学习总览.md)
- [11-八天复习路线](../../docs/programming/c-language/11-八天复习路线.md)
- `exercises/README.md`
