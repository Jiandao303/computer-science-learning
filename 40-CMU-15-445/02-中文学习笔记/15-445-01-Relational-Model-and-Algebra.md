---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: L01
topic: Relational Model & Algebra
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 数据库
  - 关系模型
  - 关系代数
  - SQL
---

# 15-445 L01：关系模型与关系代数（Relational Model & Algebra）

> 本讲是整门课的地基。它回答两个问题：数据库为什么不能用「一堆 CSV 文件 + 手写循环」来做？以及关系模型用什么数学语言描述「我要什么数据」，从而把「怎么取」交给 DBMS。

## 1. 本节学习目标

学完本讲，你应该能够：

1. 用自己的话说明用平坦文件（flat file）管理数据的三个致命缺陷，并指出 DBMS 分别用什么机制解决。
2. 区分数据模型（data model）、模式（schema）与数据独立性（data independence）三个概念，并画出物理模式 → 逻辑模式 → 外部模式的三层结构。
3. 写出关系（relation）、元组（tuple）、主键（primary key）、外键（foreign key）的形式化定义，并说明为什么多对多关系需要连接表（junction table）。
4. 把 σ、π、∪、∩、−、×、⋈ 七个关系代数算子分别翻译成等价的 SQL 语句，反之亦然。
5. 解释「声明式（declarative）」查询语言为什么能让 DBMS 做查询优化，并举例说明同一个逻辑结果的不同执行顺序在代价上可能差几个数量级。
6. 说出至少三种关系模型之外的数据模型及其适用场景（文档、向量、键值等）。

## 2. 前置知识

- **集合论基础**：集合的无序性、笛卡尔积、子集。关系模型完全建立在集合之上，理解「关系是无序集合」是理解「为什么关系代数没有 ORDER BY」的前提。
- **SQL 基本语法**：`SELECT ... FROM ... WHERE`、`CREATE TABLE`、`JOIN`。本讲不是 SQL 入门课，讲义假定你已能用 SQL 做简单查询。
- **C++ 基础（课程层面）**：15-445 的所有项目（project）都用 CMU 数据库组的教学数据库 **BusTub** 实现，讲义第 6 页明确说课程不会教你写/调试 C++，项目按 **C++17** 编写并遵循 **Google C++ Style**、用 clang-format 格式化。因此本讲之外请同步准备 C++ 智能指针、RAII、move 语义等（详见 [[40-CMU-15-445/04-学习进度|CMU 15-445 - 学习进度]] 的 C++ 准备清单）。
- **先修课程**：15-213/513（Introduction to Computer Systems），因为后续存储、并发部分需要理解缓存层次、磁盘 I/O、线程与锁。

## 3. 核心概念

### 3.1 Database（数据库）

有组织地存放在一起、相互关联、用于建模现实世界某一方面的数据集合。注意定义里的三个词：**organized**（不是随便堆文件）、**inter-related**（实体之间有联系）、**models some aspect of the real world**（只建模关心的那部分）。讲义第 18 页给出的就是这个定义。

### 3.2 DBMS（数据库管理系统）

管理数据库的软件系统。DBMS 的核心价值不是「存数据」，而是当数据量超过内存、多个用户并发访问、随时可能崩溃时，仍然保证数据**完整、正确、持久**。讲义第 26 页强调本课程研究的是 DBMS 的设计与实现，而不是「怎么用数据库写应用」（后者是 95-703 的内容）。

### 3.3 Flat File Strawman（平坦文件稻草人）

用「每个实体一个 CSV 文件 + 应用层手写解析循环」来管理数据的做法。讲义第 22 页给的例子是两个文件 `Artist(name, year, country)` 与 `Album(name, artist, year)`，查询 GZA 的出道年份要写：

```python
for line in file.readlines():
    record = parse(line)
    if record[0] == "GZA":
        print(int(record[1]))
```

这个「稻草人」存在的意义是被推翻：它暴露了数据库系统必须解决的所有问题。

### 3.4 Data Model（数据模型）

描述数据库中所存数据的概念集合，是一套「高层抽象」。讲义第 28–34 页列出的模型包括：关系模型（Relational，绝大多数 DBMS 使用，也是本课程主线）、键值模型（Key/Value，简单应用与缓存）、图模型（Graph）、文档模型（Document/JSON/XML）、宽列模型（Wide-Column，以上后四者常被统称为 NoSQL）、数组/向量/矩阵模型（Array/Vector/Matrix，机器学习场景）、以及已基本淘汰的层次模型（Hierarchical）、网状模型（Network）、语义模型（Semantic）、实体-关系模型（ER）。

### 3.5 Schema（模式）

用某个数据模型描述的具体数据布局。**数据模型是「语言」，模式是「用这门语言写出的一句话」**：同一个关系模型可以对应无数种模式（`Artist(name, year)` 是一种，`Album(name, artist)` 是另一种）。

### 3.6 Data Independence（数据独立性）

在某一层修改模式不影响上一层的能力。讲义第 47–55 页的三层结构是：

- **物理模式（Physical Schema）**：数据实际怎么存 —— 页（pages）、文件（files）、区段（extents）。
- **逻辑模式（Logical Schema）**：数据库里有哪些表、列、约束 —— schema、constraints、SQL。
- **外部模式（External Schema）**：应用看到的样子 —— 视图（views）。

物理层改动不影响逻辑层，叫**物理数据独立性**；逻辑层改动不影响外部层，叫**逻辑数据独立性**。这是关系模型能统治数据库半个世纪的根本原因：应用只依赖逻辑模式，存储引擎可以随便换。

### 3.7 Relation / Tuple（关系 / 元组）

- **Relation（关系）**：属性之间关系的**无序集合**。注意「无序」——表没有「第一行」，也没有「最后一行」。
- **Tuple（元组）**：一组属性值的集合，每个值属于某个**域（domain）**。
- 值通常是**原子的（atomic）/ 标量的（scalar）**：不允许一个单元格里再放一张表（这是「第一范式」的来源）。
- **NULL** 表示属性不存在或未知；若某个域允许 NULL，则 NULL 属于该域。

有 n 个属性的关系称为 **n 元关系（n-ary relation）**，直观上就是一张 n 列的表。

### 3.8 Primary Key（主键）与 Foreign Key（外键）

**主键**唯一标识元组。讲义第 58–60 页提示：即使业务上已有唯一标识，DBMS 内部通常还会加一个自动生成的内部主键（internal key），实现方式如 `IDENTITY`、`SEQUENCE`、`AUTO_INCREMENT`。

**外键**引用另一张表的主键，用来表达实体之间的关联。讲义第 61–66 页展示了外键如何从「一对多」演化为「多对多」：一张专辑有多个艺人、一个艺人有多个专辑时，靠连接表（junction table）`ArtistAlbum(artist_id, album_id)` 来表达。

### 3.9 Relational Algebra（关系代数）

一组以关系为输入、以关系为输出的算子。因为是「关系进、关系出」，算子可以任意嵌套、组合成表达式树——这正是查询计划（query plan）的数学基础。讲义第 74 页给出的核心算子：σ（选择 Select）、π（投影 Projection）、∪（并 Union）、∩（交 Intersection）、−（差 Difference）、×（笛卡尔积 Product）、⋈（连接 Join）。

### 3.10 Declarative Query Language（声明式查询语言）

你只描述「要什么」，不描述「怎么取」。对比：

- **过程式（Procedural）**：关系代数，你写出算子顺序。
- **非过程式/声明式（Non-Procedural / Declarative）**：关系演算（relational calculus），典型代表是 SQL。

声明式的收益在讲义第 102 页被点破：`σ_{b_id=102}(R ⋈ S)` 与 `R ⋈ (σ_{b_id=102}(S))` 结果完全相同，但当 S 有十亿条元组、只有一条满足条件时，后者的代价比前者小几个数量级。**由 DBMS 而不是用户来选择执行顺序**，这就是查询优化器存在的理由。

## 4. 通俗理解

把 DBMS 想成一家**大型图书馆**，把平坦文件想成**自己家书架上贴的便签**。

便签式管理：每本书贴一张纸条写「书名、作者、年份」，想找「1990 年出版的、作者是 GZA 的书」就从头翻到尾。书有 20 本时毫无问题；有 200 万本时，一次查询要翻 200 万张纸条，而且你搬一次家（换存储设备）所有便签都要重贴（缺乏物理数据独立性），两个人同时改同一张便签会互相覆盖（并发问题），便签被水泡了数据就没了（持久性）。

图书馆式管理：读者只说「我要 1990 年 GZA 的书」（声明式），管理员知道书按作者分架、架内有索引卡（物理模式），于是直奔 GZA 那一格。读者完全不需要知道书放在几号书架——这就是数据独立性。

具体数字对比：200 万条记录的 CSV，一次全表扫描在普通 SSD 上约需 0.2–2 秒；而 B+ 树索引查找通常只需 3–4 次页读取，约 0.1 毫秒——差了四个数量级。这个差距就是「为什么要学一学期数据库」的答案。

## 5. 原理与推导

### 5.1 从平坦文件到 DBMS：三个缺陷的推导

讲义第 23–25 页列出平坦文件的三大问题，每一个都直接对应 DBMS 的一个子系统：

| 缺陷 | 具体表现 | DBMS 的解法 | 本课程对应讲次 |
|---|---|---|---|
| 数据完整性（Data Integrity） | 同一条数据在多个文件重复存储，改一处忘另一处就不一致；无法表达「年份必须 > 1900」这类约束 | 约束（constraints）、外键、事务 | 本讲 + 事务部分 |
| 实现（Implementation） | 要支持「按年份查」就得自己写循环、自己写索引、自己处理并发读写 | 索引、查询优化器、并发控制 | 索引与查询执行部分 |
| 持久性（Durability） | 程序崩在写一半，文件里留下半条记录 | 预写日志（WAL）、恢复 | 恢复部分 |

推导的逻辑是：**只要数据量或并发度超过某个阈值，应用层手写的「文件 + 循环」必然在一致性、性能、可靠性三方面同时崩掉**，于是需要一个专门的系统把这些横切关注点（cross-cutting concerns）收拢起来。DBMS 就是那个系统。

### 5.2 关系代数算子与 SQL 的对应

这是本讲最需要「背下来 + 会翻译」的部分。设两张表 R(a_id, b_id) 与 S(a_id, b_id)。

**选择 σ（Select）**：按谓词过滤**行**。

- 代数：`σ_{a_id='a2' ∧ b_id>102}(R)`
- SQL：`SELECT * FROM R WHERE a_id = 'a2' AND b_id > 102;`

**投影 π（Projection）**：挑出**列**，并且**去重**（因为输出是集合）。

- 代数：`π_{b_id-100, a_id}(σ_{a_id='a2'}(R))`
- SQL：`SELECT b_id - 100, a_id FROM R WHERE a_id = 'a2';`

注意两点差异：第一，π 的列表里可以写表达式（`b_id-100`），说明投影不只是「选列」；第二，SQL 的 `SELECT` 默认**不去重**（bag 语义），要 `SELECT DISTINCT` 才等价于 π。这是本讲第一个必须记住的「代数 ≠ SQL」的地方。

**并 ∪（Union）**：两表属性名与类型必须一致，结果去重。

- 代数：`R ∪ S`
- SQL：`(SELECT * FROM R) UNION (SELECT * FROM S);`

**交 ∩（Intersection）**：`(SELECT * FROM R) INTERSECT (SELECT * FROM S);`

**差 −（Difference）**：`(SELECT * FROM R) EXCEPT (SELECT * FROM S);` 注意差**不满足交换律**，`R − S ≠ S − R`。

**笛卡尔积 ×（Product）**：`SELECT * FROM R, S;` 或 `SELECT * FROM R CROSS JOIN S;` 结果是 |R|×|S| 行，通常紧接着做选择，否则毫无意义。

**连接 ⋈（Join）**：笛卡尔积 + 选择。三种 SQL 写法在讲义第 95–100 页都出现了：

```sql
-- 自然连接：自动按同名同类型属性等值连接
SELECT * FROM R NATURAL JOIN S;

-- USING：显式指定连接列
SELECT * FROM R JOIN S USING (a_id, b_id);

-- ON：最通用的形式
SELECT * FROM R JOIN S ON R.a_id = S.a_id AND R.b_id = S.b_id;
```

**补充算子**（讲义第 101 页）：重命名 ρ（Rename）、赋值 R ← S（Assignment）、去重 δ（Duplicate Elimination）、聚合 γ（Aggregation）、排序 τ（Sorting）、除法 R ÷ S（Division）。这些在后续讲聚合与连接时会反复出现。

### 5.3 为什么「无序集合」很重要

关系是集合，因此：

1. 关系代数里**没有**「第 n 行」的概念，也就没有 `LIMIT` 的代数对应物。SQL 的 `ORDER BY` 与 `LIMIT` 是关系代数之外附加的操作。
2. 输出是集合意味着**自动去重**，这解释了为什么 π 去重而 SQL 的 SELECT 不去重——SQL 实现为了性能选择了 bag（多重集）语义。
3. 因为无序，DBMS 可以自由改变算子顺序、自由并行——**无序性是优化空间的来源**。

### 5.4 声明式的价值：从「怎么做」到「要什么」

讲义第 103–105 页把开头那段 Python 循环改写为一条 SQL：

```sql
SELECT year FROM artists WHERE name = 'GZA';
```

改写后发生了三件事：

1. **应用不再关心存储布局**：数据从 CSV 换成页式存储、加了索引，这条 SQL 不用改。
2. **DBMS 可以选择访问路径**：有 `name` 上的索引就走索引，没有就全表扫描，甚至可以并行扫描。
3. **优化空间被打开**：如 5.2 末所述，`σ(R⋈S)` 与 `R⋈σ(S)` 逻辑等价但代价悬殊，声明式语言允许优化器在等价变换中挑最便宜的。

这就是本讲的主线逻辑：**关系模型用集合抽象切断了应用与存储的耦合 → 声明式语言把「怎么执行」的决定权交给系统 → 系统才有空间做索引、优化、并发、恢复**。

### 5.5 关系模型之外：为什么还要别的模型

讲义第 106–131 页用两个例子说明关系模型不是万能：

- **文档模型（Document Model）**：把一张专辑及其曲目存成一个 JSON 文档 `{"name": "GZA", "year": 1990, "albums": [{"name": "Liquid Swords", "year": 1995}, ...]}`。好处是避免了**对象-关系阻抗不匹配（object-relational impedance mismatch）**——应用里的对象树可以直接序列化，不用拆成多张表再 JOIN 回来。
- **向量模型（Vector Model）**：把每条记录表示成嵌入向量 `Id1 → [0.32, 0.78, 0.30, ...]`，建立向量索引（vector index），查询返回按相似度排序的 id 列表。讲义举的混合查询是「找出歌词关于逃避警察、且 2005 年之后发行的专辑」——语义部分走向量索引，结构化条件 `year > 2005` 走标量过滤（scalar filter），两者结合。工程实现可参考 pgvector。

结论不是「关系模型要死了」，而是：**关系模型在结构化、强一致、复杂查询上仍是最优解；新模型在特定访问模式（嵌套文档、相似度检索）上有优势，现代系统往往在同一引擎里同时支持多种模型**。

## 6. 代码示例

### 6.1 讲义原文示例

**平坦文件的 GZA 查询**（`01-relationalmodel.pdf` 第 22 页，notes 第 2 页同）：

```python
for line in file.readlines():
    record = parse(line)
    if record[0] == "GZA":
        print(int(record[1]))
```

**早期 DBMS 的过程式导航查询**（`01-relationalmodel.pdf` 第 38–39 页，CODASYL 风格）：

```
PROCEDURE GET_ARTISTS_FOR_ALBUM:
    FIND ALBUM USING ALBUM.NAME = "Mooshoo Tribute"
    FIND FIRST APPEARS WITHIN APPEARS_ALBUM OF ALBUM_RECORD
    FIND OWNER WITHIN ARTIST_APPEARS
    ...
    FIND NEXT APPEARS WITHIN APPEARS_ALBUM OF ALBUM_RECORD
```

对比同页给出的声明式 SQL：

```sql
SELECT ARTIST.NAME
FROM ARTIST, APPEARS, ALBUM
WHERE ARTIST.ID = APPEARS.ARTIST_ID
  AND APPEARS.ALBUM_ID = ALBUM.ID
  AND ALBUM.NAME = "Mooshoo Tribute";
```

前者要程序员手动沿指针在记录间跳转，后者只描述结果集合。这段对比出现在 1974 年 SIGFIDET 研讨会照片（Bachman、Codd、Gray、Stonebraker，第 41–44 页）之后，是数据库史上「导航式 → 声明式」转折的原始素材。

**带约束的建表语句**（`01-relationalmodel.pdf` 第 67 页）：

```sql
CREATE TABLE Artist (
    name    VARCHAR NOT NULL,
    year    INT,
    country CHAR(60),
    CHECK (year > 1900)
);
```

以及全局断言（第 68–69 页）：

```sql
CREATE ASSERTION myAssert CHECK ( <SQL> );
```

讲义注明：SQL:92 定义的全局断言在实际系统中**极少被支持**，因为每次写入都要检查全表条件，代价太高。

**关系代数与 SQL 对照**（`01-relationalmodel.pdf` 第 75–100 页，notes 第 5–6 页）：

```sql
-- σ：选择
SELECT * FROM R WHERE a_id = 'a2' AND b_id > 102;

-- π：投影（含表达式）
SELECT b_id - 100, a_id FROM R WHERE a_id = 'a2';

-- ∪ / ∩ / −
(SELECT * FROM R) UNION     (SELECT * FROM S);
(SELECT * FROM R) INTERSECT (SELECT * FROM S);
(SELECT * FROM R) EXCEPT    (SELECT * FROM S);

-- ×：笛卡尔积
SELECT * FROM R, S;

-- ⋈：连接
SELECT * FROM R NATURAL JOIN S;
```

### 6.2 补充示例（非官方，仅用于说明概念）

下面用通用 SQL 演示「同一逻辑结果、不同写法、不同代价」，帮助你建立优化器的直觉：

```sql
-- 写法 A：先连接再过滤（逻辑等价于 σ(R ⋈ S)）
SELECT *
FROM orders o JOIN customers c ON o.cust_id = c.id
WHERE c.country = 'CN';

-- 写法 B：先过滤再连接（逻辑等价于 R ⋈ σ(S)）
SELECT *
FROM orders o
JOIN (SELECT * FROM customers WHERE country = 'CN') c
  ON o.cust_id = c.id;
```

如果 `customers` 有 1 亿行而 `country = 'CN'` 只有 10 万行，写法 B 在朴素执行下要少做三个数量级的比较。但**在真正的 DBMS 里你不必手动改写**——优化器会把谓词下推（predicate pushdown）。手动改写的意义在于理解优化器在做什么。

再补一个 π 去重语义的例子：

```sql
-- 关系代数 π_country(Artist) 会自动去重
SELECT DISTINCT country FROM Artist;   -- 与 π 等价
SELECT country FROM Artist;            -- bag 语义，有重复
```

## 7. 容易混淆的概念

| 概念对 | 区别 | 记忆要点 |
|---|---|---|
| 数据模型（Data Model） vs 模式（Schema） | 数据模型是描述数据的**概念集合/语言**；模式是用该语言写出的**具体布局** | 模型是语法，模式是程序 |
| 关系（Relation） vs 表（Table） | 关系是**无序集合**、自动去重；SQL 表是**多重集（bag）**、允许重复行、可能有隐含顺序 | 代数去重，SQL 不去重 |
| 关系代数（Relational Algebra） vs 关系演算（Relational Calculus） | 代数是**过程式**（给算子顺序）；演算是**声明式**（只给谓词） | 代数=怎么做，演算=要什么 |
| 主键（Primary Key） vs 内部主键（Internal Key） | 主键是逻辑层唯一标识；内部主键是 DBMS 自动加的物理标识（IDENTITY/SEQUENCE） | 业务用主键，引擎用内部键 |
| 逻辑数据独立性 vs 物理数据独立性 | 前者：改逻辑模式不影响外部模式（视图）；后者：改物理模式不影响逻辑模式 | 越往上越稳定 |
| DBMS vs 数据库（Database） | DBMS 是**软件**，数据库是**数据集合** | 一个是程序，一个是内容 |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Slides | `90-原始PDF/15-445/slides/01-relationalmodel.pdf` | 133 | 18（数据库定义）、22–25（平坦文件三缺陷）、26–27（DBMS/模型与模式）、45–55（关系模型与数据独立性）、56–69（关系/元组/键/约束）、74–101（关系代数算子）、102–105（声明式的价值）、106–131（文档与向量模型） |
| Notes | `90-原始PDF/15-445/notes/01-relationalmodel.pdf` | 6 | 全文；第 5–6 页为关系代数各算子的语法/示例/SQL 对照 |

原始 URL：

- Slides：`https://15445.courses.cs.cmu.edu/fall2026/slides/01-relationalmodel.pdf`
- Notes：`https://15445.courses.cs.cmu.edu/fall2026/notes/01-relationalmodel.pdf`

> 待核实：slides 首页标注学期为 Fall 2026，但页眉运行标题（running head）写的是 "CMU DATABASE SYSTEMS (SPRING 2026)"，二者不一致；以官网课表为准，此处保留原样记录。首页署名讲师为 Jignesh Patel，讲师名单以官网为准。

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内，本讲内容对应 2025 年第 1 讲）

- 标题：Relational Model & Algebra（2025 年第 1 讲）
- URL：`https://www.youtube.com/watch?v=7NPIENPr-zk&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 年份：2025
- 时间戳：未核实，故不标注。

说明：根据课程 FAQ Q11，"the Fall 2026 lectures will be recorded but will only be available to CMU students. Non-CMU students should watch the Fall 2025 lectures on YouTube." 因此本笔记的视频链接一律指向 Fall 2025 公开播放列表，与 F26 的 slides/notes 分开标注。

## 10. 本节复习

- 能不看笔记说出平坦文件的三大缺陷，以及每个缺陷由 DBMS 的哪个子系统解决。
- 能画出物理模式 → 逻辑模式 → 外部模式三层图，并标出两种数据独立性分别在哪两条箭头之间。
- 能默写关系、元组、域、主键、外键的定义，并解释为什么多对多需要连接表。
- 能把 σ、π、∪、∩、−、×、⋈ 七个算子与对应 SQL 互相翻译，且记得 π 去重而 SELECT 不去重。
- 能解释「关系是无序集合」如何带来优化空间（可自由重排、可并行）。
- 能用 `σ(R⋈S)` vs `R⋈σ(S)` 的例子说明声明式语言为什么能优化。
- 能说出文档模型与向量模型各自解决关系模型的什么痛点。
- 记住项目用 BusTub、C++17、Google C++ Style，且课程不教 C++ 基础。

## 11. 自我检查

**Q1.** 用平坦文件（每个实体一个 CSV）管理数据会遇到哪三类问题？请各举一个具体场景。

<details><summary>参考答案</summary>

1. **数据完整性（Data Integrity）**：同一条数据在多个文件中重复。例如艺人 GZA 的国籍同时出现在 `Artist.csv` 和多张专辑的 `Album.csv` 行里，改了一处忘了另一处，两份数据就矛盾了；而且 CSV 无法声明「year > 1900」这类约束，脏数据可以直接写进去。
2. **实现（Implementation）**：任何新查询都要写新的循环。想「按年份查」就得全文件扫描；想支持并发读写、想加索引，都得自己在应用层实现一遍，而这些恰恰是数据库最难的工程问题。
3. **持久性（Durability）**：程序在写第 500 行时崩溃，文件里留下半条记录，下次启动解析直接报错，且没有任何机制能回滚到一致状态。

</details>

**Q2.** 关系代数中 `π` 与 SQL 的 `SELECT` 语义有何不同？给出一个能体现差异的例子。

<details><summary>参考答案</summary>

`π` 的输出是**集合**，自动去除重复元组；SQL 的 `SELECT` 默认是**多重集（bag）**语义，保留重复行，必须显式写 `DISTINCT` 才等价于 `π`。

例子：`Artist` 表中有 100 位艺人来自中国、20 位来自美国。`π_country(Artist)` 返回 `{中国, 美国}` 两行；`SELECT country FROM Artist` 返回 120 行；`SELECT DISTINCT country FROM Artist` 才返回 2 行。

此外 `π` 的属性列表允许写表达式（如 `π_{b_id-100, a_id}`），说明投影不仅是「选列」，还可以在投影时做计算。

</details>

**Q3.** 给定 `R(a_id, b_id)` 与 `S(a_id, b_id)`，写出 `σ_{b_id=102}(R ⋈ S)` 的等价 SQL，并说明为什么 DBMS 可能选择先过滤 S 再连接。

<details><summary>参考答案</summary>

```sql
SELECT *
FROM R JOIN S ON R.a_id = S.a_id AND R.b_id = S.b_id
WHERE S.b_id = 102;
```

等价的、更高效的写法是 `R ⋈ (σ_{b_id=102}(S))`。原因：连接代价大致与两表行数的乘积（嵌套循环）或行数之和（哈希/排序归并）相关。若 S 有 10 亿行而只有 1 行满足 `b_id=102`，先过滤把 S 压到 1 行，再做连接的总代价比先做十亿级连接再过滤低几个数量级。两者逻辑等价，因此优化器可以在等价变换中自由选择——这正是声明式语言相对过程式语言的核心优势。

</details>

**Q4.** 什么是物理数据独立性与逻辑数据独立性？各举一个「改了下层不影响上层」的例子。

<details><summary>参考答案</summary>

- **物理数据独立性**：修改物理模式（数据如何存储）不影响逻辑模式。例：把某张表从堆文件（heap file）改成按主键聚簇的 B+ 树存储，甚至换成列存，所有已有的 SQL 查询和应用代码都不用改。
- **逻辑数据独立性**：修改逻辑模式（表结构、约束）不影响外部模式（应用看到的视图）。例：把 `Artist` 表垂直拆分成 `ArtistBasic` 与 `ArtistDetail` 两张表，但保留一个名为 `Artist` 的视图做 JOIN，应用仍然 `SELECT ... FROM Artist`，感知不到底层拆分。

</details>

**Q5.** 关系模型已经很成功，为什么还会出现文档模型和向量模型？各举一个它们更合适的场景。

<details><summary>参考答案</summary>

因为关系模型要求值原子化、结构扁平化，在两类场景下会带来额外成本：

- **文档模型**：数据天然是嵌套的对象树（如一张专辑带曲目列表）。用关系模型要拆成多张表再 JOIN 回来，产生「对象-关系阻抗不匹配」。文档模型允许把整棵树存成一个 JSON 文档，读写都只需一次操作，适合内容管理、目录类应用。
- **向量模型**：查询是「找最相似的 k 条」，而不是「找满足等值/范围条件的行」。把记录表示成嵌入向量并建向量索引（如 pgvector），可以直接返回按相似度排序的 id 列表；讲义中的混合查询还把语义相似度与结构化条件 `year > 2005` 结合起来。

现代系统常见做法是在同一引擎内同时支持多种模型，而不是二选一。

</details>

## 12. 进一步学习

- 下一讲：[[15-445-02-Modern-SQL]] —— 从关系代数走向真实 SQL 的复杂特性（窗口函数、CTE、递归查询等）。
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]、[[40-CMU-15-445/04-学习进度|CMU 15-445 - 学习进度]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：教材 *Database System Concepts*（第 7 版）第 2 章「Introduction to the Relational Model」与第 6 章「Formal Relational Query Languages」，可把本讲的关系代数算子与教材的形式化定义逐条对齐。
- 动手建议：在本地装一个 PostgreSQL，用 `EXPLAIN` 观察同一查询的两种写法（5.2 节的 A/B 写法）是否被优化器改写成同一个计划，验证「声明式让系统决定执行顺序」这一结论。
