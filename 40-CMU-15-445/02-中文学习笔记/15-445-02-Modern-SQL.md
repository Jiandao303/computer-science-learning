---
course: CMU 15-445
course_name: Database Systems
semester: Fall 2026
lecture_id: L02
topic: Modern SQL
language: zh-CN
source_language: en
status: draft
tags:
  - 15-445
  - 数据库
  - SQL
  - 聚合
  - 窗口函数
---

# 15-445 L02：现代 SQL（Modern SQL）

> 上一讲把关系代数当作「查询的数学」，这一讲把镜头拉回工程师日常真正写的东西：SQL。重点不是基础语法，而是那些**能让一条 SQL 顶掉几十行应用代码**的现代特性——分组集、FILTER、LATERAL、CTE、窗口函数。

## 1. 本节学习目标

学完本讲，你应该能够：

1. 说清 SQL 的四类子语言（DML/DDL/DCL + 视图/约束/事务），并解释 SQL 为什么基于**袋（bag）**而非**集合（set）**。
2. 正确使用聚合函数与 `GROUP BY`，解释为什么「SELECT 列表里出现未聚合列」在语义上是未定义的，以及 `ANY_VALUE` 解决了什么。
3. 区分 `WHERE`、`FILTER`、`HAVING` 三者的过滤时机，并能用 `GROUPING SETS` 替代多条 `UNION ALL`。
4. 写出嵌套查询的四种形式（SELECT 目标、FROM 子句、WHERE 子句、相关子查询），并说明 `ALL / ANY / IN / EXISTS` 的语义差异。
5. 解释 `LATERAL` 为什么等价于「对每一行执行一次子查询的 for 循环」，以及它与普通 JOIN 的区别。
6. 用 `WITH` 与 `WITH RECURSIVE` 写 CTE，理解「递归 CTE 让 SQL 图灵完备」这句话的含义。
7. 用 `OVER (PARTITION BY ... ORDER BY ...)` 写窗口函数，说明它与 `GROUP BY` 聚合的本质差别（不折叠行），并记住 `ROW_NUMBER` 在排序前计算、`RANK` 在排序后计算。

## 2. 前置知识

- **关系代数与 SQL 的对应**：σ/π/∪/⋈ 与 `WHERE`/`SELECT`/`UNION`/`JOIN` 的映射，见 [[15-445-01-Relational-Model-and-Algebra]]。
- **SQL 基础**：`CREATE TABLE`、`PRIMARY KEY`、`FOREIGN KEY`/`REFERENCES`、`NOT NULL`、`UNIQUE`。
- **NULL 三值逻辑**：`NULL = NULL` 结果是 `UNKNOWN` 而不是 `TRUE`，这会影响 `NOT IN` 与 `NOT EXISTS` 的行为差异（见第 7 节）。
- **C++ 提醒**：本课程项目用 **C++17** 编写、遵循 **Google C++ Style** 并用 clang-format 格式化；讲义明确说不教 C++，请自行补齐（智能指针、RAII、move 语义、模板）。

## 3. 核心概念

### 3.1 SQL（结构化查询语言）

一种**声明式（declarative）**的关系数据库查询语言。与命令式语言相反，使用者只声明「要做什么」（例如「把这两张表连接起来」），而不规定「怎么做」。SQL 1970 年代诞生于 IBM System R 项目，原名 SEQUEL（Structured English Query Language），1980 年代改名为 SQL。

### 3.2 SQL 标准演进（SQL Standard）

讲义列出的关键版本：SQL:1999（正则、触发器、面向对象）、SQL:2003（XML、窗口函数、序列、自增 ID）、SQL:2008（截断、更复杂的排序）、SQL:2011（时态数据库、流水线 DML）、SQL:2016（JSON、多态表）、SQL:2023（属性图查询、多维数组）。**一个系统要声称「支持 SQL」，最低限度要实现 SQL-92 的语法**；各厂商在此之上各有私有扩展。

### 3.3 DML / DDL / DCL（三类子语言）

- **DML（Data Manipulation Language，数据操纵语言）**：`SELECT`、`INSERT`、`UPDATE`、`DELETE`。
- **DDL（Data Definition Language，数据定义语言）**：表、索引、视图等对象的模式定义。
- **DCL（Data Control Language，数据控制语言）**：安全与访问控制（`GRANT`/`REVOKE`）。
- 此外 SQL 还包含视图定义、完整性与参照约束、事务控制。

### 3.4 Bag vs Set（袋 vs 集合）

关系代数基于**集合**（无序、无重复）；SQL 基于**袋（bag，无序、允许重复）**，目的是**避免默认去重的开销**。需要去重时显式写 `DISTINCT`。这是上一讲「π 去重、SELECT 不去重」的正式表述，也是理解 SQL 与关系代数所有细微差异的总纲。

### 3.5 Aggregate Function（聚合函数）

输入一袋元组、输出一个标量值的函数：`AVG`、`MIN`、`MAX`、`SUM`、`COUNT`。聚合函数**几乎只能出现在 SELECT 输出列表**中。部分聚合（`COUNT`、`SUM`、`AVG`）支持 `DISTINCT`，如 `COUNT(DISTINCT login)`。一条 SELECT 可以包含多个聚合。

### 3.6 GROUP BY（分组）

把元组投影到若干子集，再对每个子集计算聚合。规则：**SELECT 输出子句中未聚合的列必须出现在 GROUP BY 中**，这样每个分组才有规范值（canonical value）。

### 3.7 GROUPING SETS（分组集）

在一次查询中指定多种分组方式，替代多条 `UNION ALL` 查询。收益是 **DBMS 只需扫描一遍数据**而不是多遍。

### 3.8 FILTER（聚合前过滤）

在**聚合计算之前**过滤进入聚合函数的行。用于「在同一份原始数据上按不同条件算多个聚合」，典型用途是**行转列（pivot）**。

### 3.9 HAVING（聚合后过滤）

在**聚合计算之后**过滤分组（而不是过滤行）。`WHERE` 过滤行，`HAVING` 过滤组——这就是「HAVING 是 GROUP BY 的 WHERE」这句话的准确含义。

### 3.10 Nested Query（嵌套查询）

在查询内部再调用查询，用于在单条语句内表达更复杂的逻辑。**外层作用域对内层可见，内层作用域对外层不可见**。内层查询几乎可以出现在任何位置：SELECT 输出目标、FROM 子句、WHERE 子句。讲义特别提醒：**嵌套查询往往难以优化**。

### 3.11 LATERAL Join（横向连接）

允许嵌套查询引用**在它之前出现的**其他嵌套查询（或外层表）的属性。可以理解为「对表中的每一行，执行一次子查询的 for 循环」。普通 JOIN 的右表不能引用左表的列，`LATERAL` 打破了这个限制。

### 3.12 Common Table Expression（CTE，公共表表达式）

用 `WITH` 子句把内层查询的输出绑定到一个临时表名上，作用域限于该条查询。是嵌套查询、视图、显式临时表之外的第四种写法。加上 `RECURSIVE` 关键字后 CTE 可以引用自身，从而在 SQL 里实现递归——**这让 SQL 在图灵完备意义下与通用编程语言等价**（虽然写起来啰嗦）。

### 3.13 Window Function（窗口函数）

在一组「与当前元组相关」的元组上做滑动计算，但**不把元组折叠成单个输出元组**——这是它与聚合的本质区别。语法 `SELECT FUNC(...) OVER (...)`。支持运行总和（running total）、排名（rank）、移动平均（moving average）。

## 4. 通俗理解

把 `GROUP BY` 想成**按班级收卷子**：把所有卷子按班级分成几摞，每摞算一个平均分，最后每个班只交**一个数字**——卷子被「折叠」了。

把窗口函数想成**成绩单上多印一列**：每张卷子都还在（行数不变），只是在旁边多印一个「你在班里的排名」。你既能看到自己的分数，也能看到自己在班里的位置。

具体数字对比：`enrolled` 表有 5 条记录，涉及 3 门课。

- 用 `GROUP BY cid` 求平均 GPA：输出 **3 行**（每门课一行），5 条原始记录消失。
- 用 `RANK() OVER (PARTITION BY cid ORDER BY grade)`：输出 **5 行**（每条记录一行），每行多一个 `rank` 列。

行数从 5 变 3 还是保持 5，就是「聚合」与「窗口」的分水岭。

再举个 GROUPING SETS 的收益：要同时得到「按课程+成绩计数」「按课程计数」「总计数」三张结果，用三条 `GROUP BY` + `UNION ALL` 要扫描 `enrolled` 三遍；用 `GROUPING SETS` 只扫描**一遍**。表有 1 亿行时，这就是 3 次全表扫描 vs 1 次全表扫描的差别。

## 5. 原理与推导

### 5.1 为什么 SQL 选择 bag 语义

推导链条：关系代数要求输出是集合 → 集合意味着每次操作后都要去重 → 去重需要排序或哈希，代价 O(n log n) 或 O(n) 额外空间 → 而大多数查询（尤其是中间结果）根本不需要去重 → 于是 SQL 默认采用 bag 语义，把去重变成**可选的 `DISTINCT`**。

这个决定的连锁后果：`SELECT` 不去重、`UNION` 去重而 `UNION ALL` 不去重、`IN` 与 `EXISTS` 在重复行下语义仍需仔细辨析。

### 5.2 聚合的三层过滤时机

这是本讲最容易出错的地方，用一张时序图理解：

```
FROM/JOIN 产生原始行
   ↓
WHERE        过滤「行」（分组之前）
   ↓
GROUP BY     把行分成组
   ↓
FILTER       过滤「进入聚合函数的行」（仍在组内，聚合之前）
   ↓
聚合计算     每组得到一个标量
   ↓
HAVING       过滤「组」（聚合之后）
   ↓
SELECT       投影 + 计算输出列
   ↓
ORDER BY     排序（唯一能依赖顺序的地方）
   ↓
LIMIT/FETCH  截断
```

由此可以推导出几条实用规则：

1. `WHERE` 里不能写聚合函数（此时还没有组）。
2. `HAVING` 里可以写聚合函数，也可以引用 SELECT 里的别名（多数系统支持，但**不是 SQL 标准**；标准要求重复写出 `AVG(s.gpa)`）。
3. `FILTER` 与 `WHERE` 的区别：`WHERE` 过滤后整行消失，所有聚合都看不到它；`FILTER` 只让某**一个**聚合看不到它，其他聚合照常统计。所以 `FILTER` 天生适合「一行里算多个条件下的聚合」。

### 5.3 未聚合列的未定义性

```sql
SELECT AVG(s.gpa), e.cid
FROM enrolled AS e JOIN student AS s ON e.sid = s.sid;
```

这里没有 `GROUP BY`，整张表是一个组，`AVG(s.gpa)` 有唯一值；但 `e.cid` 在一个组里有多个不同的值，**输出哪一个在语义上是未定义的**。多数真实系统会直接报错，SQLite 这类宽松系统会随便挑一个，SQL:2023 则引入 `ANY_VALUE()` 把「随便挑一个」变成显式声明。

正确写法是加 `GROUP BY e.cid`，让每个组内 `cid` 唯一。

### 5.4 GROUPING SETS 为什么只扫一遍

普通做法：

```sql
SELECT c.name, e.grade, COUNT(*) FROM ... GROUP BY c.name, e.grade
UNION ALL
SELECT c.name, NULL, COUNT(*) FROM ... GROUP BY c.name
UNION ALL
SELECT NULL, NULL, COUNT(*) FROM ...;
```

三次 `GROUP BY` 意味着三次扫描 + 三次聚合 + 两次 UNION 去重（如果用了 `UNION` 而非 `UNION ALL`）。

`GROUPING SETS ((c.name, e.grade), (c.name), ())` 的推导：DBMS 可以只做一次扫描，把每行**同时**喂给三个分组哈希表（或按最细粒度分组后再上卷），最后一次输出所有层级的结果。这就是「一次扫描、多级聚合」的思路，也是数据仓库里 CUBE/ROLLUP 的实现基础。

### 5.5 嵌套查询的四种形态与相关子查询的代价

**形态 1：SELECT 输出目标中的标量子查询**

```sql
SELECT sid, (SELECT name FROM student AS s WHERE s.sid = e.sid) AS name
FROM enrolled AS e;
```

**形态 2：FROM 子句中的派生表**

```sql
SELECT name FROM student AS s, (SELECT sid FROM enrolled) AS e
WHERE s.sid = e.sid;
```

**形态 3：WHERE 子句中的 `IN`**

```sql
SELECT name FROM student WHERE sid IN (SELECT sid FROM enrolled WHERE cid = '15-445');
```

**形态 4：相关子查询（correlated subquery）**

```sql
SELECT * FROM course
WHERE NOT EXISTS (
    SELECT * FROM enrolled WHERE course.cid = enrolled.cid
);
```

关键差别在于**是否引用外层列**。形态 1–3 的子查询可以只算一次（非相关），形态 4 引用了 `course.cid`，**逻辑上对每一行都要执行一次**。朴素实现是 O(外层行数 × 内层代价)，优化器通常会把 `NOT EXISTS` 改写成反连接（anti-join），从而避免嵌套执行——这也解释了讲义为什么说「嵌套查询往往难以优化」：能否改写成功取决于优化器的能力。

四种结果表达式：

| 表达式 | 语义 |
|---|---|
| `ALL` | 对子查询的**所有**行，表达式都必须为真 |
| `ANY` | 对子查询的**至少一行**，表达式为真 |
| `IN` | 等价于 `= ANY()` |
| `EXISTS` | 子查询至少返回一行（不比较具体属性值） |

`NOT IN` 与 `NOT EXISTS` 的经典陷阱：如果子查询结果里含 `NULL`，`x NOT IN (..., NULL)` 的结果是 `UNKNOWN` 而非 `TRUE`，整行被过滤掉；而 `NOT EXISTS` 不受 `NULL` 影响。**子查询可能返回 NULL 时，优先用 `NOT EXISTS`。**

### 5.6 LATERAL：把 JOIN 变成 for 循环

讲义给的玩具例子：

```sql
SELECT * FROM
  (SELECT 1 AS x) AS t1,
  LATERAL (SELECT t1.x + 1 AS y) AS t2;
```

等价的伪代码是：

```python
for x in [1]:
    for y in [x + 1]:
        print(x, y)
```

真正的用例（每门课算选课人数与平均 GPA）：

```sql
SELECT * FROM course AS c,
  LATERAL (SELECT COUNT(*) AS cnt FROM enrolled WHERE enrolled.cid = c.cid) AS t1,
  LATERAL (SELECT AVG(gpa) AS avg FROM student AS s
           JOIN enrolled AS e ON s.sid = e.sid
           WHERE e.cid = c.cid) AS t2
ORDER BY cnt ASC;
```

没有 `LATERAL` 的话，`t1` 和 `t2` 无法引用 `c.cid`。所以 `LATERAL` 的本质是：**允许 FROM 子句里的子查询成为「参数化」的，参数来自左侧的行**。代价上，它天然接近嵌套循环连接（nested loop join），外层行数多时要小心。

### 5.7 CTE 与递归

普通 CTE：

```sql
WITH cteName (col1, col2) AS (SELECT 1, 2)
SELECT col1 + col2 FROM cteName;
```

多个 CTE 可以并列声明：`WITH cte1 (col1) AS (SELECT 1), cte2 (col2) AS (SELECT 2) SELECT * FROM cte1, cte2;`

递归 CTE（打印 1 到 10）：

```sql
WITH RECURSIVE cteSource (counter) AS (
    (SELECT 1)
    UNION
    (SELECT counter + 1 FROM cteSource WHERE counter < 10)
)
SELECT * FROM cteSource;
```

推导它的执行方式：先算**基础项**（`SELECT 1`），得到工作表中的 1；然后反复执行**递归项**（`counter + 1`），每轮把新行加入结果集并作为下一轮的输入，直到递归项不再产生新行。`WHERE counter < 10` 就是终止条件——**没有终止条件的递归 CTE 会无限循环**。

因为有了递归，SQL 可以表达任意可计算函数（图灵完备），理论上不需要宿主语言。实践中仍然用宿主语言，因为 SQL 表达复杂控制流非常笨重。

### 5.8 窗口函数的执行模型

讲义第 102–115 页给出的概念执行顺序（注意：不是所有窗口函数都严格如此）：

1. （可选）**分区**：`PARTITION BY` 把表切成若干分区。
2. （可选）**排序**：每个分区内按 `ORDER BY` 排序。
3. **确定帧（frame）**：对每一行，确定一个跨多行的窗口（默认是从分区开头到当前行，即 `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`）。
4. **逐行输出**：对每个窗口算出一个值，附加到当前行上。

关键细节（讲义 notes 用 IMPORTANT 标出）：**`ROW_NUMBER()` 在窗口排序之前计算，`RANK()` 在窗口排序之后计算**。所以

```sql
SELECT cid, sid, ROW_NUMBER() OVER (PARTITION BY cid) FROM enrolled ORDER BY cid;
```

里的 `ROW_NUMBER` 只是「分区内的序号」，与 `grade` 无关；要按成绩排名必须写成 `RANK() OVER (PARTITION BY cid ORDER BY grade ASC)`。

「每门课第二名」的经典写法：

```sql
SELECT * FROM (
    SELECT *, RANK() OVER (PARTITION BY cid ORDER BY grade ASC) AS rank
    FROM enrolled
) AS ranking
WHERE ranking.rank = 2;
```

注意这里必须套一层子查询，因为**窗口函数在 WHERE 之后才计算**，不能直接写在 `WHERE rank = 2` 里（`WHERE` 阶段 `rank` 还不存在）。

### 5.9 ORDER BY / LIMIT 与「无序」的关系

关系模型不保证顺序，所以：

- `ORDER BY` 是**唯一**能让输出有序的手段。
- 不带 `ORDER BY` 的 `LIMIT` 是**不确定**的：同一查询多次执行可能返回不同的元组。讲义 notes 明确警告这一点。
- `LIMIT n OFFSET m` 与标准写法 `OFFSET m ROWS FETCH FIRST n ROWS ONLY` 等价；`FETCH FIRST n ROWS WITH TIES` 会把与第 n 行排序键相同的行也一并返回。

## 6. 代码示例

### 6.1 讲义原文示例

**示例数据库模式**（`02-modernsql.pdf` 第 10 页，notes 第 2 页）：

```sql
CREATE TABLE student (
    sid    INT PRIMARY KEY,
    name   VARCHAR(16),
    login  VARCHAR(32) UNIQUE,
    age    SMALLINT,
    gpa    FLOAT
);
CREATE TABLE course (
    cid    VARCHAR(32) PRIMARY KEY,
    name   VARCHAR(32) NOT NULL
);
CREATE TABLE enrolled (
    sid    INT REFERENCES student (sid),
    cid    VARCHAR(32) REFERENCES course (cid),
    grade  CHAR(1)
);
```

**聚合的三种等价写法**（`02-modernsql.pdf` 第 12–15 页）：

```sql
SELECT COUNT(login) AS cnt FROM student WHERE login LIKE '%@cs';
SELECT COUNT(*)     AS cnt FROM student WHERE login LIKE '%@cs';
SELECT COUNT(1)     AS cnt FROM student WHERE login LIKE '%@cs';
```

**未聚合列 + ANY_VALUE**（第 16–19 页）：

```sql
SELECT AVG(s.gpa), ANY_VALUE(e.cid)
FROM enrolled AS e JOIN student AS s ON e.sid = s.sid;
```

**GROUP BY**（第 20–23 页）：

```sql
SELECT AVG(s.gpa), e.cid
FROM enrolled AS e JOIN student AS s ON e.sid = s.sid
GROUP BY e.cid;
```

**GROUPING SETS**（第 25–30 页）：

```sql
SELECT c.name AS c_name, e.grade, COUNT(*) AS num_students
FROM enrolled AS e JOIN course AS c ON e.cid = c.cid
GROUP BY GROUPING SETS (
    (c.name, e.grade),  -- 按课程和成绩
    (c.name),           -- 只按课程
    ()                  -- 总计
);
```

**FILTER**（第 34–35 页）：

```sql
SELECT AVG(s.gpa) FILTER (WHERE e.cid = '15-445') AS avg_gpa,
       ANY_VALUE(e.cid)
FROM enrolled AS e JOIN student AS s ON e.sid = s.sid;
```

**HAVING 的三种写法**（第 36–42 页）：第一种把 `avg_gpa` 写进 `WHERE` 是**错的**（聚合尚未计算）；第二种用 `HAVING avg_gpa > 3.9` 可被多数系统接受但不是标准；第三种 `HAVING AVG(s.gpa) > 3.9` 才是标准写法。

```sql
SELECT AVG(s.gpa) AS avg_gpa, e.cid
FROM enrolled AS e JOIN student AS s ON e.sid = s.sid
GROUP BY e.cid
HAVING AVG(s.gpa) > 3.9;
```

**字符串操作**（第 43–46 页）：

```sql
SELECT * FROM enrolled AS e WHERE e.cid LIKE '15-%';
SELECT * FROM student AS s WHERE s.login LIKE '%@c_';
SELECT * FROM student AS s WHERE login SIMILAR TO '[\w]{3}@cs';
SELECT SUBSTRING(name, 1, 5) AS abbrv_name FROM student WHERE sid = 53688;
SELECT name FROM student WHERE login = LOWER(name) || '@cs';   -- SQL-92 拼接
```

**输出控制**（第 53–56 页）：

```sql
SELECT sid, name FROM student WHERE login LIKE '%@cs'
FETCH FIRST 10 ROWS ONLY;

SELECT sid, name FROM student WHERE login LIKE '%@cs'
ORDER BY gpa
OFFSET 5 ROWS FETCH FIRST 5 ROWS WITH TIES;
```

**输出重定向**（第 57–58 页）：

```sql
SELECT DISTINCT cid INTO CourseIds FROM enrolled;            -- SQL-92 新建表
CREATE TABLE CourseIds (SELECT DISTINCT cid FROM enrolled);  -- MySQL
SELECT DISTINCT cid INTO TEMPORARY CourseIds FROM enrolled;  -- Postgres 临时表
```

**嵌套查询：三门写法求「最高学号且在选课」**（第 68–72 页）：

```sql
SELECT sid, name FROM student WHERE sid = ANY(SELECT MAX(sid) FROM enrolled);

SELECT sid, name FROM student WHERE sid IN (
    SELECT sid FROM enrolled ORDER BY sid DESC FETCH FIRST 1 ROW ONLY
);

SELECT student.sid, name
FROM student JOIN (SELECT MAX(sid) AS sid FROM enrolled) AS max_e
  ON student.sid = max_e.sid;
```

**嵌套查询：没有学生选的课**（第 73–75 页）：

```sql
SELECT * FROM course
WHERE NOT EXISTS (
    SELECT * FROM enrolled WHERE course.cid = enrolled.cid
);
```

**LATERAL JOIN**（第 77–84 页）：

```sql
SELECT * FROM course AS c,
  LATERAL (SELECT COUNT(*) AS cnt FROM enrolled
           WHERE enrolled.cid = c.cid) AS t1,
  LATERAL (SELECT AVG(gpa) AS avg FROM student AS s
           JOIN enrolled AS e ON s.sid = e.sid
           WHERE e.cid = c.cid) AS t2
ORDER BY cnt ASC;
```

**CTE 与递归 CTE**（第 85–88 页，notes 第 8 页）：

```sql
WITH cteName (col1, col2) AS (SELECT 1, 2)
SELECT col1 + col2 FROM cteName;

WITH RECURSIVE cteSource (counter) AS (
    (SELECT 1)
    UNION
    (SELECT counter + 1 FROM cteSource WHERE counter < 10)
)
SELECT * FROM cteSource;
```

**窗口函数**（第 89–101 页）：

```sql
SELECT *, ROW_NUMBER() OVER () AS row_num FROM enrolled;

SELECT cid, sid, ROW_NUMBER() OVER (PARTITION BY cid)
FROM enrolled ORDER BY cid;

SELECT * FROM (
    SELECT *, RANK() OVER (PARTITION BY cid ORDER BY grade ASC) AS rank
    FROM enrolled
) AS ranking
WHERE ranking.rank = 2;
```

### 6.2 补充示例（非官方，仅用于说明概念）

**用 GROUPING SETS 做小计与总计**（通用 SQL）：

```sql
SELECT COALESCE(cid, 'ALL') AS course, COUNT(*) AS n
FROM enrolled
GROUP BY GROUPING SETS ((cid), ());
```

`COALESCE` 把分组集产生的 `NULL` 占位符换成可读的 `'ALL'`，这是报表里的常见套路。

**用窗口函数算移动平均**（通用 SQL）：

```sql
SELECT cid, sid,
       AVG(gpa) OVER (PARTITION BY cid ORDER BY sid
                      ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS moving_avg
FROM student JOIN enrolled USING (sid);
```

`ROWS BETWEEN ... AND ...` 显式指定帧，是默认帧（到当前行为止）之外的另一种选择，适合做滑动窗口统计。

**递归 CTE 展开组织架构**（通用 SQL）：

```sql
WITH RECURSIVE org (id, mgr_id, depth) AS (
    SELECT id, mgr_id, 0 FROM employee WHERE mgr_id IS NULL
    UNION ALL
    SELECT e.id, e.mgr_id, o.depth + 1
    FROM employee e JOIN org o ON e.mgr_id = o.id
)
SELECT * FROM org ORDER BY depth;
```

这是递归 CTE 最实用的场景：层级数据（组织架构、BOM 物料清单、评论树）用一条 SQL 展开。

## 7. 容易混淆的概念

| 概念对 | 区别 | 记忆要点 |
|---|---|---|
| `WHERE` vs `HAVING` | `WHERE` 在分组**前**过滤行；`HAVING` 在聚合**后**过滤组 | WHERE 看行，HAVING 看组 |
| `FILTER` vs `WHERE` | `WHERE` 让整行对所有聚合消失；`FILTER` 只让某**一个**聚合忽略这些行 | FILTER 是「聚合函数的局部 WHERE」 |
| `GROUP BY` vs 窗口函数 | `GROUP BY` 把每组折叠成一行；窗口函数保留每一行 | 行数变少 vs 行数不变 |
| `ROW_NUMBER()` vs `RANK()` | `ROW_NUMBER` 在窗口排序前编号（分区内连续 1,2,3）；`RANK` 在排序后计算名次，并列时跳号（1,1,3） | 序号 vs 名次 |
| `UNION` vs `UNION ALL` | `UNION` 去重（要排序/哈希）；`UNION ALL` 保留重复、更快 | 除非确需去重，用 ALL |
| `IN` vs `EXISTS` | `IN` 比较值集合，子查询含 NULL 时 `NOT IN` 会失效；`EXISTS` 只判断有无行，不受 NULL 影响 | 有 NULL 风险时用 EXISTS |
| CTE vs 视图（View） | CTE 作用域限于**一条查询**；视图是持久化的命名查询 | CTE 是一次性的，视图是长期的 |

## 8. 对应原版讲义

| 材料 | 相对路径 | 总页数 | 重点页码 |
|---|---|---|---|
| Slides | `90-原始PDF/15-445/slides/02-modernsql.pdf` | 117 | 4–7（SQL 历史与标准）、8（DML/DDL/DCL 与 bag 语义）、10（示例数据库）、11–42（聚合/GROUP BY/GROUPING SETS/FILTER/HAVING）、43–52（字符串与日期时间）、53–58（输出控制与重定向）、59–75（嵌套查询）、77–84（LATERAL）、85–88（CTE）、89–115（窗口函数） |
| Notes | `90-原始PDF/15-445/notes/02-modernsql.pdf` | 9 | 全文；第 2 页示例库 DDL，第 4 页 FILTER/HAVING，第 7 页 LATERAL 与 CTE，第 8–9 页窗口函数与图 2 概念执行图 |

原始 URL：

- Slides：`https://15445.courses.cs.cmu.edu/fall2026/slides/02-modernsql.pdf`
- Notes：`https://15445.courses.cs.cmu.edu/fall2026/notes/02-modernsql.pdf`

> 待核实：讲义第 78 页正文说「按选课人数**降序**排序」，而第 79–84 页的 SQL 写的是 `ORDER BY cnt ASC`（升序）；notes 第 7 页同样写「descending order」但示例代码为 `ASC`。以代码为准，文字描述疑为笔误。

## 9. 对应视频

**Fall 2025 公开视频**（2026 版录像仅限 CMU 校内，本讲内容对应 2025 年第 2 讲）

- 标题：Modern SQL（2025 年第 2 讲）
- URL：`https://www.youtube.com/watch?v=O5gU9NQjCAs&list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`
- 年份：2025
- 时间戳：未核实，故不标注。

说明：FAQ Q11 明确 F26 录像只对 CMU 学生开放，非 CMU 学习者应观看 Fall 2025 的公开视频；两版讲义内容可能略有差异，以 F26 的 slides/notes 为准。

## 10. 本节复习

- 能说出 SQL 的四类子语言，并解释 bag 语义的由来与代价。
- 能画出「FROM → WHERE → GROUP BY → FILTER → 聚合 → HAVING → SELECT → ORDER BY → LIMIT」的执行时序，并指出每层能写什么、不能写什么。
- 能解释为什么 `SELECT AVG(gpa), cid` 不加 `GROUP BY` 是错的，`ANY_VALUE` 又做了什么。
- 能说出 `GROUPING SETS` 相对 `UNION ALL` 的性能优势（一次扫描 vs 多次扫描）。
- 能写出「每门课第二名」的窗口函数查询，并解释为什么要套一层子查询。
- 能默写 `ROW_NUMBER` 与 `RANK` 的计算时机差异，并给出一个二者结果不同的例子。
- 能写出递归 CTE 求 1 到 10，并指出哪一句是终止条件。
- 能解释 `LATERAL` 为什么是「参数化的子查询」，以及它与嵌套循环连接的相似性。

## 11. 自我检查

**Q1.** 一条 SQL 的执行顺序中，`WHERE`、`FILTER`、`HAVING` 分别作用在什么阶段？请各举一个只有它能做、别人做不了的例子。

<details><summary>参考答案</summary>

- **`WHERE`**：在 `FROM/JOIN` 之后、`GROUP BY` 之前，过滤**行**。只有它能做的：用非聚合谓词提前剪掉大量行以减少后续工作量，如 `WHERE login LIKE '%@cs'`。写在 `HAVING` 里语义上也可（如果没有分组），但会丧失「提前减少行数」的优化机会。
- **`FILTER`**：在分组内、聚合计算之前，过滤**进入某个聚合函数的行**。只有它能做的：在同一份数据上一次算出多个不同条件下的聚合，如 `AVG(gpa) FILTER (WHERE cid='15-445')` 与 `AVG(gpa) FILTER (WHERE cid='15-721')` 并列，实现行转列。
- **`HAVING`**：在聚合计算之后，过滤**组**。只有它能做的：用聚合结果做筛选，如 `HAVING AVG(s.gpa) > 3.9`——此时 `WHERE` 里根本没有聚合值可用。

</details>

**Q2.** 下面这条查询有什么问题？给出两种修正方式。

```sql
SELECT AVG(s.gpa), e.cid
FROM enrolled AS e JOIN student AS s ON e.sid = s.sid;
```

<details><summary>参考答案</summary>

问题：没有 `GROUP BY`，整张表被视为一个组，`AVG(s.gpa)` 有唯一值，但 `e.cid` 在一个组里有多个不同值，**输出哪个 `cid` 在语义上未定义**。多数系统直接报错，SQLite 会随便挑一个。

修正 1（推荐）：加分组，让每组内 `cid` 唯一。

```sql
SELECT AVG(s.gpa), e.cid
FROM enrolled AS e JOIN student AS s ON e.sid = s.sid
GROUP BY e.cid;
```

修正 2：若确实只想要一个整体平均值、`cid` 只是随便带出来，用 SQL:2023 的 `ANY_VALUE` 显式表达这个意图。

```sql
SELECT AVG(s.gpa), ANY_VALUE(e.cid)
FROM enrolled AS e JOIN student AS s ON e.sid = s.sid;
```

</details>

**Q3.** 用窗口函数找出每门课成绩第二高的学生，并解释为什么不能直接写 `WHERE rank = 2`。

<details><summary>参考答案</summary>

```sql
SELECT * FROM (
    SELECT *, RANK() OVER (PARTITION BY cid ORDER BY grade ASC) AS rank
    FROM enrolled
) AS ranking
WHERE ranking.rank = 2;
```

不能直接写 `WHERE rank = 2` 的原因：SQL 的逻辑执行顺序中 `WHERE` 在窗口函数计算**之前**，此时 `rank` 这个列还不存在。必须先用子查询（或 CTE）把窗口函数的结果物化成一张表，再在外层过滤。

注意 `grade` 是 `A/B/C` 字符，字母序 `A < B < C`，所以「第二高」要 `ORDER BY grade ASC`；若成绩是数值则应 `DESC`。

</details>

**Q4.** `NOT IN` 与 `NOT EXISTS` 在什么情况下结果不同？给出一个具体例子。

<details><summary>参考答案</summary>

当子查询的结果集中**含 `NULL`** 时结果不同。SQL 三值逻辑下，`x NOT IN (1, 2, NULL)` 等价于 `x <> 1 AND x <> 2 AND x <> NULL`，最后一项是 `UNKNOWN`，整个表达式既不是 `TRUE` 也不是 `FALSE`，`WHERE` 只保留 `TRUE` 的行，因此**整张表一行都返回不了**。

例子：`enrolled.cid` 允许为 `NULL`（学生选了课但课程号缺失）。

```sql
-- 若 enrolled.cid 中有 NULL，此查询返回空集
SELECT * FROM course WHERE cid NOT IN (SELECT cid FROM enrolled);

-- 正确写法，不受 NULL 影响
SELECT * FROM course c
WHERE NOT EXISTS (SELECT 1 FROM enrolled e WHERE e.cid = c.cid);
```

结论：子查询列可能为 `NULL` 时，用 `NOT EXISTS`。

</details>

**Q5.** `GROUPING SETS ((c.name, e.grade), (c.name), ())` 相比三条 `GROUP BY` + `UNION ALL`，性能优势从何而来？如果表只有 100 行，这个优势还重要吗？

<details><summary>参考答案</summary>

优势来自**扫描次数**：三条独立查询各需扫描一遍 `enrolled JOIN course`，共三遍；`GROUPING SETS` 只需扫描一遍，把每行同时喂给多个分组结构（或按最细粒度分组后逐级上卷），最后一次性输出所有层级。数据量大时，扫描 I/O 与连接代价是主要成本，一遍 vs 三遍是接近 3 倍的差距；此外 `UNION ALL` 虽不去重，但仍需多次物化中间结果。

如果表只有 100 行，三遍扫描的绝对代价都在微秒级，性能优势可以忽略；此时用 `GROUPING SETS` 的主要理由是**可读性与可维护性**（一条语句 vs 三条语句拼接），而不是性能。

</details>

## 12. 进一步学习

- 上一讲：[[15-445-01-Relational-Model-and-Algebra]] —— 关系代数与 SQL 的对应关系。
- 下一讲：[[15-445-03-Database-Storage-I]] —— 从「怎么写查询」转入「DBMS 内部怎么存数据」，磁盘、页、文件组织。
- 课程导航：[[40-CMU-15-445/00-课程总览|CMU 15-445 - 课程总览]]、[[40-CMU-15-445/01-课程目录|CMU 15-445 - 课程目录]]、[[40-CMU-15-445/04-学习进度|CMU 15-445 - 学习进度]]
- 术语对照：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸阅读：教材 *Database System Concepts*（第 7 版）第 3 章「Introduction to SQL」与第 5 章「Advanced SQL」，可对照本讲的窗口函数、递归 CTE、OLAP 分组特性。
- 动手建议：在 PostgreSQL 里对同一份数据分别用 `GROUP BY` + `UNION ALL` 与 `GROUPING SETS` 写报表，用 `EXPLAIN (ANALYZE, BUFFERS)` 比较扫描次数与执行时间；再对比 `NOT IN` 与 `NOT EXISTS` 在含 NULL 列上的结果差异。
