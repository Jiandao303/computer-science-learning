---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: L03
topic: Database Storage I
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 数据库
  - 存储
  - 页
  - 磁盘
---

# 15-445 L03：数据库存储 I（Database Storage — Files & Pages）

> 前两讲都在「逻辑层」打转：表、关系、SQL。从这一讲开始下沉到「物理层」，回答两个问题——**数据库在磁盘上长什么样**（文件与页），以及**页里的字节怎么排列**（页布局与元组布局）。这一讲提出的两个问题，正好对应后续第 4、5、6 讲。

## 1. 本节学习目标

学完本讲，你应该能够：

1. 画出存储层次结构（寄存器 → L1/L2 → DRAM → SSD → HDD → 网络存储），标出易失/非易失的分界线，并复述各层典型访问延迟。
2. 解释「随机访问慢于顺序访问」这一事实如何塑造 DBMS 的设计目标，并说明 extent（区段）的作用。
3. 区分硬件页、OS 页、数据库页三种「页」，说明数据库页大小为什么随负载类型变化（读重用大页、写重用小页）。
4. 描述堆文件（heap file）的组织方式与页目录（page directory）的职责。
5. 说明 slotted page 的结构：header、slot array、tuple data 三段如何相向生长，以及删除/变长属性为何需要它。
6. 解释 record ID 的组成（file id + page id + slot #）以及为什么应用不应依赖它。
7. 说明元组为什么要字对齐（word alignment），掌握 padding 与重排（reordering）两种对齐手段。
8. 区分变精度数（FLOAT/REAL，IEEE-754）与定点数（NUMERIC/DECIMAL），并说出三种 NULL 表示法与三种大值存储方案（overflow page、German Strings、外部文件）。

## 2. 前置知识

- **计算机组成基础**：缓存层次、字节寻址 vs 块寻址、字（word）对齐。这些是 15-213 的内容，本讲直接使用。
- **SQL 与关系模型**：知道什么是元组、属性、模式，见 [[15-445-01-Relational-Model-and-Algebra]] 与 [[15-445-02-Modern-SQL]]。
- **指针与内存布局（C/C++）**：理解 `reinterpret_cast`、结构体对齐、`unsigned char[]` 缓冲区。本课程项目用 BusTub，**C++17 + Google C++ Style + clang-format**，本讲涉及的 `reinterpret_cast` 在项目 #1 的缓冲池里会大量出现。
- **数量级直觉**：1 ns / 100 ns / 100 µs / 10 ms 这几个数字要能脱口而出，否则无法理解后续所有设计取舍。

## 3. 核心概念

### 3.1 Disk-Oriented DBMS（面向磁盘的数据库系统）

假设数据库的**主要存储位置是非易失磁盘**的 DBMS 架构，与之相对的是内存数据库（memory-oriented DBMS，表常驻 DRAM）。本课程主线采用面向磁盘的假设，因为绝大多数真实系统如此。DBMS 的各组件负责在非易失存储与易失存储之间搬运数据。

### 3.2 Storage Hierarchy（存储层次）

从快到慢：CPU 寄存器（Registers）→ CPU 缓存（Caches）→ DRAM → SSD → HDD → 网络存储（Network Storage）→ 磁带归档。层次越靠上越快、越小、越贵；靠下越慢、越大、越便宜。**易失（volatile）与随机访问、字节寻址**是上半段的特征；**非易失（non-volatile）与顺序访问、块寻址**是下半段的特征。

### 3.3 Access Time（访问延迟）

讲义引用的「每个程序员都该知道的延迟数字」：L1 引用 1 ns、L2 引用 4 ns、DRAM 100 ns、SSD 16,000 ns（16 µs）、HDD 2,000,000 ns（2 ms）、网络存储约 50 ms、磁带归档约 1000 s。换算成「L1 = 1 秒」的类比：DRAM 100 秒、SSD 4.4 小时、HDD 3.3 周、网络存储 1.5 年、磁带 31.7 年。

### 3.4 Sequential vs Random Access（顺序 vs 随机访问）

非易失存储上随机访问几乎总是慢于顺序访问：讲义给的数字是随机 I/O 80–100 µs、顺序 I/O 10–100 µs（每块）。因此 **DBMS 的核心优化目标之一是最大化顺序访问**：算法尽量减少对随机页的写入，把数据放在连续块里。一次分配多个连续页叫做 **extent（区段）**。

### 3.5 Database Page（数据库页）

固定大小的数据块，可存放元组、元数据、索引项、日志记录等。多数系统**不混放页类型**；部分系统（如 Oracle）要求页**自包含（self-contained）**。每页有唯一页号（page ID），页号的作用域可以是 DBMS 实例级、数据库级或表级；DBMS 用一层**间接层（indirection layer）**把页号映射到物理位置。

### 3.6 三种「页」

- **Hardware Page（硬件页）**：通常 4 KB，是存储设备能**保证原子写**的最大块。
- **OS Page（操作系统页）**：通常 4 KB；x64 上还有 2 MB / 1 GB 的大页（huge page）。
- **Database Page（数据库页）**：512 B – 32 KB，由 DBMS 自己定义。

关键推论：若数据库页大于硬件页，一次页写入可能被打断（崩溃时只写了一半），DBMS 必须额外机制保证安全（校验和、日志）。

### 3.7 Heap File（堆文件）

**无序**的页集合，元组以任意顺序存放。需要支持 Create / Get / Write / Delete Page，以及**遍历所有页**。还需要额外元数据来跟踪文件位置与空闲空间。最简单的定位方式：`offset = page# × pageSize`。

### 3.8 Page Directory（页目录）

DBMS 维护的特殊页，记录数据页在文件中的位置，**每个数据库对象一条目录项**。目录必须与真实数据页保持同步。DBMS 还在目录里记录页的元数据：每页剩余空间、空闲/空页链表、页类型（数据页 or 元数据页）。

### 3.9 Slotted Page（分槽页）

最常见的元组式页布局。结构分三段：

- **Header**：记录已用槽位数、最后一个已用槽的起始偏移等。
- **Slot Array**：从页首向后生长，每个槽记录对应元组的**起始偏移**。
- **Tuple Data**：从页尾向前生长。

**当 slot array 与 tuple data 相遇时，页就满了**。删除元组只需把槽目标记失效（或压缩整理），变长属性也能通过偏移间接寻址。

### 3.10 Record ID（记录标识）

DBMS 给每个逻辑元组分配的唯一物理位置标识，典型组成是 **File ID + Page ID + Slot #**。多数 DBMS **不把 record id 存在元组里**；SQLite 例外，它把 `ROWID` 当作真正的主键并作为隐藏属性存储。**应用不应该依赖这些 ID 的语义**，因为页重组会让它们变化。常见大小：TID 4 字节、CTID 6 字节、ROWID 8/10 字节、`%%physloc%%` 8 字节。

### 3.11 Word Alignment（字对齐）

元组中所有属性必须按字对齐，CPU 才能在不产生异常或额外工作的情况下访问。手段有二：**填充（padding）**——在属性后补空位，把类型大小向上取整到字长；**重排（reordering）**——改变属性的物理顺序以减少填充（可能仍需少量 padding）。

### 3.12 Variable vs Fixed Precision Numbers（变精度 vs 定点数）

- **变精度（FLOAT / REAL / DOUBLE）**：按 IEEE-754 直接存储，CPU 有原生指令与寄存器支持，**更快但不保证精确**。讲义用 `0.1 + 0.2` 的例子演示：`%.20f` 打印出来是 `0.30000001192092895508`，而 `0.3` 是 `0.29999999999999998890`。
- **定点（NUMERIC / DECIMAL）**：任意精度与标度，舍入误差不可接受时使用；实现方式多样，Postgres 用变长二进制 + 元数据（`ndigits`/`weight`/`scale`/`sign`/`digits`）。

### 3.13 NULL 的三种表示

1. **Null Column Bitmap Header**：头部集中放一个位图，某位为 1 表示对应属性为 NULL。**行存最常见**。
2. **Special Values**：为每个类型指定一个占位值（如 `INT32_MIN`）。**列存更常见**。
3. **Per-Attribute Null Flag**：每个属性一个标志位；因为破坏字对齐、需要填充，**不推荐**（讲义明确标注 "Don't Do This!"）。

### 3.14 Large Values（大值存储）

多数 DBMS 不允许元组超过一页。超出部分存入**溢出页（overflow page）**：Postgres 的 TOAST（>2 KB 触发）、MySQL 的 Overflow（>页大小一半）、SQL Server 的 Overflow（>页大小）。元组里只存「大小 + 位置」。

## 4. 通俗理解

把数据库想成一座**超大型仓库**，把内存想成**你手边的工作台**。

仓库（磁盘）极大但取货极慢：去一趟要 2 毫秒（HDD）——按「L1 = 1 秒」的比例换算就是**三周半**。所以你不能一件一件去取，必须**一次推一整车**回来（读一整页），并且尽量**按货架顺序**取（顺序访问），别在仓库里来回跑（随机访问）。

工作台（缓冲池，下一讲）只有几平米，放不下所有货。于是需要一个管理员决定「哪些货留在台面上、哪些退回仓库」——这就是第 4 讲的替换策略。

每个货箱（页）内部还有讲究：箱子口有个**目录牌**（slot array），写着「第 1 件货在箱子第 30 厘米处，第 2 件在第 80 厘米处」；货从箱子**底部往上堆**，目录牌从**顶部往下挂**，两者相遇就说明箱子满了。这就是 slotted page。为什么需要目录牌？因为货的大小不一（变长字段），而且经常有人取走中间的某件货（删除元组）——如果没有目录牌，你根本不知道空出来的缝隙能不能塞进新货。

具体数字：一个 8 KB 的页，头部加 slot array 约 100 字节，剩余约 8 KB 放元组。若每行 100 字节，则一页约 80 行；一张 1 亿行的表约需 125 万个页，即约 10 GB。

## 5. 原理与推导

### 5.1 为什么必须是「面向磁盘」的架构

推导起点是一个不等式：**数据库大小 > 内存大小**（否则用内存数据结构就够了）。一旦成立，任何操作都必须假设「需要的页当前不在内存里」，于是产生三个必然的设计后果：

1. **必须有缓冲池**：把磁盘页缓存到内存，否则每次访问都要一次磁盘 I/O（第 4 讲）。
2. **必须有页的概念**：I/O 的最小单位是块，不能按字节读写，所以数据必须按固定大小分块管理。
3. **必须最大化顺序访问**：随机 I/O 80–100 µs vs 顺序 I/O 10–100 µs，差近一个数量级，因此要按 extent 批量分配、按顺序扫描。

### 5.2 页大小怎么选：一个权衡推导

- **读密集型**（数据仓库、分析）：一次查询要扫描大量元组，页越大，一次 I/O 带进来的有用元组越多，I/O 次数越少 → 倾向**大页（≥1 MB）**。
- **写密集型**（OLTP）：即使只改一行，也必须把**整页**写回磁盘（除非有更细粒度的机制）。页越大，写放大（write amplification）越严重 → 倾向**小页（4–16 KB）**。

所以页大小不是「越大越好」或「越小越好」，而是由读写比例决定的。常见默认值：Postgres 8 KB、MySQL InnoDB 16 KB、SQL Server 8 KB、Oracle 8 KB（可配）。

### 5.3 三种页概念与「原子写」的边界

硬件保证的原子写粒度 = 硬件页（通常 4 KB）。若数据库页 = 16 KB，一次页写入跨了 4 个硬件页，崩溃可能发生在第 2 个硬件页写完之后——磁盘上就出现了「半个新页 + 半个旧页」的撕裂页（torn page）。

由此推导出两个必须存在的机制：

1. **校验和（checksum）**：页头存校验和，读回时验证，发现撕裂就报错重试。
2. **日志 / 双写（WAL / doublewrite）**：恢复时用日志重放或从双写缓冲区修补。

这说明「页头为什么要有 checksum」不是随便加的字段，而是原子写边界的直接产物。

### 5.4 堆文件 + 页目录的定位推导

朴素方案：`offset = page# × pageSize`。这对**定长页、单文件、页不移动**成立。但现实中：

- 页可能被删除产生空洞 → 需要空闲页链表；
- 一个表可能跨多个文件 → 需要 file id；
- 页可能需要搬迁（整理碎片）→ 需要间接层。

于是引入**页目录**：一张「逻辑页号 → (文件, 偏移)」的映射表。目录本身也是页，也存在内存里（通常常驻）。代价是多一次查表，收益是页可以自由移动、文件可以分裂。这就是「DBMS 用间接层把 page ID 映射到物理位置」这句话的工程含义。

### 5.5 Slotted Page 的生长模型

```
+-------------------------------+
| Header: num_slots, last_offset|
+-------------------------------+
| slot[0] -> offset_0           |   ↓ slot array 从头向尾生长
| slot[1] -> offset_1           |
| ...                           |
|            (free space)       |
| ...                           |
| tuple_1 (变长)                |   ↑ tuple data 从尾向头生长
| tuple_0 (变长)                |
+-------------------------------+
```

推导它为什么能解决「稻草人方案」的两个问题：

- **删除元组**：稻草人方案（`num_tuples` + 尾部追加）删除中间元组后，要么留下无法复用的洞，要么必须移动后续所有元组。slotted page 只需把 `slot[i]` 标记为失效（例如偏移设为 -1），空间可以在**整理（compaction）**时统一回收。元组的物理位置由 slot 间接给出，所以**元组可以在页内移动而不改变外部引用**——外部只需要 `(page_id, slot#)`。
- **变长属性**：由于是「slot 指向偏移」而不是「定长数组下标」，变长元组天然可支持。

关键洞察：**间接层（slot）把「元组的逻辑身份」与「元组的物理位置」解耦**，这正是 record id 用 slot# 而不是字节偏移的原因。

### 5.6 字对齐的推导：为什么需要 padding

CPU 访问一个 8 字节的 `double` 时，若地址不是 8 的倍数，在 x86 上可能跨缓存行导致两次访问（性能损失），在某些架构（ARM 严格对齐模式）上直接触发异常。DBMS 要保证跨平台正确 + 高性能，就必须让每个属性的起始地址是其大小的整数倍。

例：`CREATE TABLE foo (id INT, cdate TIMESTAMP, color CHAR(2), zipcode INT)`。按声明顺序紧凑排列：4 + 8 + 2 + 4 = 18 字节，但 `cdate` 起始偏移 4（不是 8 的倍数）→ 不合法。两种解法：

- **Padding**：在 `id` 后补 4 字节，`color` 后补 2 字节，总计 24 字节。
- **Reordering**：改成 `id(4) + zipcode(4) + cdate(8) + color(2) + pad(6)` = 24 字节；或者更紧凑的排布仍有 6 字节填充。

结论：**重排通常能减少填充，但无法完全消除**（因为总大小还要满足结构体对齐要求）。

### 5.7 变精度 vs 定点：一个必须记住的反例

```c
float x = 0.1, y = 0.2;
printf("%.20f\n", x + y);  // 0.30000001192092895508
printf("%.20f\n", 0.3);    // 0.29999999999999998890
```

原因：0.1 与 0.2 在二进制下是无限循环小数，float 只能截断存储，相加后误差累积。对**金额**这类绝对不能出错的字段，必须用 `NUMERIC`/`DECIMAL`（定点），代价是运算更慢（没有原生指令支持）。

### 5.8 大值存储的三级方案

1. **溢出页（overflow page）**：元组里存 `(size, page_id, offset)`，真实数据放别的页。最通用，Postgres/MySQL/SQL Server 都这么做，但每次访问都要多一次 I/O。
2. **German Strings**：针对 VARCHAR 的优化。≤16 字节则**完全内联**；>16 字节则内联存「4 字节总长 + 4 字节前缀 + 8 字节位置指针」。前缀的作用是让 `WHERE s LIKE 'AndyP%'` 这类谓词**不必读溢出页就能判断**，直接省掉一次 I/O。
3. **外部文件（external value storage）**：Oracle 的 `BFILE`、SQL Server 的 `FILESTREAM`。DBMS 无法操作文件内容，因此**没有持久性保证、没有事务保证**——这是用它必须接受的代价。

## 6. 代码示例

### 6.1 讲义原文示例

**变精度浮点的舍入误差**（`03-storage1.pdf` 第 108–111 页）：

```c
#include <stdio.h>
int main(int argc, char* argv[]) {
    float x = 0.1;
    float y = 0.2;
    printf("x+y = %.20f\n", x+y);
    printf("0.3 = %.20f\n", 0.3);
}
```

输出（第 111 页）：

```
x+y = 0.30000001192092895508
0.3 = 0.29999999999999998890
```

**Postgres 的 NUMERIC 实现**（第 113–114 页）：

```c
typedef unsigned char NumericDigit;
typedef struct {
    int ndigits;   // 数字位数
    int weight;    // 首位数字的权重
    int scale;     // 小数点位置
    int sign;      // 正/负/NaN
    NumericDigit *digits;  // 数字存储
} numeric;
```

**字对齐示例表**（第 91–103 页）：

```sql
CREATE TABLE foo (
    id      INT PRIMARY KEY,
    cdate   TIMESTAMP,
    color   CHAR(2),
    zipcode INT
);
```

**元组头部的构成**（第 84–85 页）：`Header | Attribute Data`，header 内含可见性信息（并发控制用）与 NULL 位图；**不需要存模式元数据**，因为 schema 在 DBMS 的 catalog 里。

**属性按声明顺序存储**（第 85 页）：

```sql
CREATE TABLE foo (a INT PRIMARY KEY, b INT NOT NULL, c INT, d DOUBLE, e FLOAT);
```

讲义注明：按声明顺序存储是**软件工程上的选择（简单）**，物理上重排可能更高效。

**German Strings 布局**（第 126–135 页）：≤16 字节内联；>16 字节为 `4 字节 size | 4 字节 prefix | 8 字节 location`。

### 6.2 补充示例（非官方，仅用于说明概念）

**手工计算 slotted page 的容量**（伪代码，非官方）：

```
page_size        = 8192 B
header           = 32 B
slot_size        = 8 B           # offset(4) + length(4)
tuple_size       = 100 B         # 平均行长，含 tuple header
n 满足: 32 + 8n + 100n <= 8192
=> 108n <= 8160  => n = 75
```

即一页约放 **75 行**；1 亿行需要约 133 万个页 ≈ 10.2 GB（不含索引）。这类估算在项目里判断「页够不够」时非常实用。

**字对齐的手工排布**（非官方）：

```c
// 朴素顺序：4 + 8 + 2 + 4 = 18 B，cdate 偏移 4 → 不对齐
struct Bad { int32_t id; int64_t cdate; char color[2]; int32_t zipcode; };

// 重排 + 填充：4 + 4 + 8 + 2 + 6(pad) = 24 B，全部对齐
struct Good { int32_t id; int32_t zipcode; int64_t cdate; char color[2]; char pad[6]; };
```

这解释了为什么「元组的物理布局顺序」可以与「建表时的列顺序」不同——DBMS 内部按对齐需要重排，对外仍按列名访问。

## 7. 容易混淆的概念

| 概念对 | 区别 | 记忆要点 |
|---|---|---|
| 硬件页 vs OS 页 vs 数据库页 | 硬件页 = 原子写粒度（4 KB）；OS 页 = 虚拟内存映射粒度（4 KB / 2 MB / 1 GB）；数据库页 = DBMS 自定义（512 B–32 KB） | 三者可以互不相等 |
| 页目录（Page Directory） vs 页头（Page Header） | 页目录是**独立的页**，记录「有哪些数据页、在哪」；页头是**每页开头**的元数据 | 目录管页的集合，页头管页的内部 |
| Slot Array vs 元组数据 | slot array 从页首向后生长，存**偏移**；元组数据从页尾向前生长，存**内容** | 一个存指针，一个存实体 |
| Record ID vs 主键 | record id 是**物理位置**（可随重组变化）；主键是**逻辑唯一标识**（不变） | 应用依赖主键，永不依赖 record id |
| Padding vs Reordering | padding 补空字节；reordering 换属性顺序以减少填充 | 先重排，再补洞 |
| FLOAT/REAL vs NUMERIC/DECIMAL | IEEE-754 变精度、快、不精确；定点、慢、精确 | 金额用 DECIMAL |
| Heap File vs Tree File | 堆文件无序、插入快、查找要全扫；树文件按索引组织、查找快、维护贵 | 堆文件是默认，树文件是索引 |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Slides | `90-原始PDF/15-445/slides/03-storage1.pdf` | 141 | 10–19（磁盘架构、存储层次、访问延迟、顺序 vs 随机、设计目标）、20–33（面向磁盘 DBMS 全链路图）、36–44（文件存储、存储管理器、三种页、页大小权衡）、45–55（页存储架构、堆文件、页目录）、57–80（页头、三种页布局、slotted page、record id）、83–105（元组布局、字对齐 padding/reordering）、105–138（数据表示、浮点精度、NUMERIC、NULL、大值、German Strings、外部存储） |
| Notes | `90-原始PDF/15-445/notes/03-storage1.pdf` | 6 | 全文；第 1 页存储层次与易失/非易失定义，第 3 页页目录与 slotted pages 生长方向，第 5–6 页数据类型表示与 NULL 方案 |

原始 URL：

- Slides：`https://15445.courses.cs.cmu.edu/fall2026/slides/03-storage1.pdf`
- Notes：`https://15445.courses.cs.cmu.edu/fall2026/notes/03-storage1.pdf`

> 待核实：讲义第 43 页「Default DB Page Sizes」只列出了 16KB / 4KB / 8KB 三个数字，未在文本层标注对应系统名（原图为图形标注）；具体对应关系需人工核对原 PDF 图。

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内，本讲内容对应 2025 年第 3 讲）

- 标题：Database Storage I（2025 年第 3 讲）
- URL：`https://www.youtube.com/watch?v=PRLXdIMJhOg&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 年份：2025
- 时间戳：未核实，故不标注。

## 10. 本节复习

- 能默写存储层次，并给出 DRAM / SSD / HDD 的典型延迟数量级。
- 能解释「随机 I/O 80–100 µs vs 顺序 I/O 10–100 µs」如何推出 extent 与「最大化顺序访问」的设计目标。
- 能说清三种页的区别，以及「数据库页大于硬件页」会带来什么后果（撕裂页 → checksum + WAL）。
- 能画出 slotted page 三段结构，说明 slot array 与 tuple data 的生长方向，以及页满的判定条件。
- 能解释 record id 为什么用 slot# 而不是字节偏移（因为元组可在页内移动）。
- 能给出一张表的字段列表，手工算出 padding 前后的元组大小，并给出一个重排后更小的布局。
- 能说出 `0.1 + 0.2 != 0.3` 的原因，以及什么场景必须用 DECIMAL。
- 能列举 NULL 的三种表示与大值的三种存储方式，并说明 German Strings 的前缀为什么能省 I/O。

## 11. 自我检查

**Q1.** 为什么 DBMS 要「最大化顺序访问」？请用具体延迟数字说明，并指出 extent 在这个目标中的作用。

<details><summary>参考答案</summary>

非易失存储上，随机访问与顺序访问的代价差距显著：讲义给出的数字是随机 I/O 约 80–100 µs，顺序 I/O 每块约 10–100 µs；在 HDD 上这个差距还来自机械寻道（毫秒级）与旋转延迟。一次查询若要做 10 万次随机页读取，按 90 µs 计约 9 秒；若改成顺序扫描同样数据量，可能只需不到 1 秒。

因此 DBMS 的算法尽量「减少对随机页的写入」，把逻辑上相关的数据放在**物理连续**的块里。**Extent（区段）**就是一次分配的多个连续页：分配时按 extent 申请，写入时就能连续落盘，从而把多次随机 I/O 合并成一次顺序 I/O。

</details>

**Q2.** slotted page 如何同时解决「删除元组产生空洞」和「变长属性」两个问题？

<details><summary>参考答案</summary>

结构上，页分为三段：header（记录已用槽数与最后使用偏移）、slot array（从页首向后生长，每个槽存对应元组的起始偏移）、tuple data（从页尾向前生长）。当 slot array 与 tuple data 相遇时页满。

- **删除元组**：把该槽标记失效（如偏移置 -1），元组占用的空间在后续**整理（compaction）**时统一回收。因为外部引用的是 `(page_id, slot#)` 而不是字节偏移，整理时元组在页内移动不会破坏任何引用。而稻草人方案（只记 `num_tuples` 并尾部追加）删除中间元组后无法安全复用空洞，也无法在不移动后续元组的前提下插入变长元组。
- **变长属性**：槽存的是「偏移」而非「定长数组下标」，因此每个元组可以占任意字节数；插入时从空闲区尾部切出所需大小，把偏移写进槽即可。

本质是**间接层**：slot 把元组的逻辑身份与物理位置解耦。

</details>

**Q3.** 给定 `CREATE TABLE foo (id INT, cdate TIMESTAMP, color CHAR(2), zipcode INT)`（INT 4B、TIMESTAMP 8B、CHAR(2) 2B），按声明顺序紧凑排列有什么问题？给出 padding 与 reordering 两种修正后的大小。

<details><summary>参考答案</summary>

按声明顺序紧凑排列：`id`(4) + `cdate`(8) + `color`(2) + `zipcode`(4) = 18 字节。但 `cdate` 的起始偏移是 4，而 8 字节类型要求偏移是 8 的倍数 → **不对齐**，在严格对齐架构上会触发异常，在 x86 上也会跨缓存行降低性能。

- **Padding**：在 `id` 后补 4 字节使 `cdate` 从偏移 8 开始；`color`(2) 后补 2 字节使 `zipcode` 从偏移 20（4 的倍数）开始；总计 4+4+8+2+2+4 = 24 字节（可能再补到 8 的倍数，仍是 24）。
- **Reordering**：改为 `id`(4) + `zipcode`(4) + `cdate`(8) + `color`(2) + pad(6) = 24 字节，所有属性都对齐，且填充只出现在末尾。

两种方案总大小相同，但重排把填充集中到尾部，便于后续扩展字段。

</details>

**Q4.** 分别说明 NULL 的三种表示法，并指出行存与列存各自偏好哪一种、为什么。

<details><summary>参考答案</summary>

1. **Null Column Bitmap Header**：在页/元组头部集中放一个位图，第 i 位为 1 表示第 i 个属性为 NULL。**行存最常见**，因为行存一行内属性连续，一个位图就能覆盖整行，空间开销极小（每属性 1 bit）。
2. **Special Values**：为每个类型保留一个哨兵值（如 `INT32_MIN`）表示 NULL。**列存最常见**，因为列存按列连续存储同类型值，用哨兵值不需要额外的位图列，且便于向量化运算（可以整列比较）。
3. **Per-Attribute Null Flag**：每个属性带一个标志位/字节。讲义明确标注 "Don't Do This!"——因为破坏字对齐，必须填充到字长，反而浪费更多空间。

</details>

**Q5.** German Strings 相比普通溢出页方案，优化点在哪里？请举一个能体现优势的查询。

<details><summary>参考答案</summary>

普通溢出页方案：元组里只存 `(size, page_id, offset)`，任何需要该字符串的谓词都必须先读溢出页取回完整内容。

German Strings：≤16 字节的值**完全内联**（无需任何间接）；>16 字节的值内联存 `4 字节总长 + 4 字节前缀 + 8 字节位置指针`。优化点在于**前缀内联**——对于只关心开头几个字节的谓词，可以**不读溢出页就做出判断**。

体现优势的查询：`SELECT * FROM t WHERE name LIKE 'AndyP%'`。若表中有 100 万行、每行 name 平均 200 字节，普通方案要读 100 万个溢出页（约 100 万次额外 I/O，按 90 µs 计约 90 秒）；German Strings 只需比较内联的 4 字节前缀，绝大多数行直接被排除，**只有真正匹配的行才需要读溢出页**。

</details>

## 12. 进一步学习

- 上一讲：[[15-445-02-Modern-SQL]] —— SQL 的现代特性。
- 下一讲：[[15-445-04-Memory-Management]] —— 缓冲池：内存如何管理、页如何换入换出、替换策略与钉住页。
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]、[[40-CMU-15-445/04-学习进度|CMU 15-445 - 学习进度]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：教材 *Database System Concepts*（第 7 版）第 12 章「Physical Storage Systems」与第 13 章「Data Storage Structures」，其中对 slotted page、record organization 有更形式化的描述。
- 动手建议：用 `psql` 或 `sqlite3` 建一张含定长与变长字段的表，插入若干行后查看页大小设置（`SHOW block_size;` / `PRAGMA page_size;`），再用 `pg_relation_size()` 估算「每页多少行」，与 6.2 节的手工计算对照。
