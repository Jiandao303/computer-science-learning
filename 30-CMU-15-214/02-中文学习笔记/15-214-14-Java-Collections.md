---
course: CMU 15-214
course_name: Principles of Software Construction - Objects, Design, and Concurrency
semester: Fall 2013
lecture_id: L14
topic: Java Collections Framework
language: zh-CN
source_language: en
status: draft
tags:
  - CMU
  - 15-214
  - Java
  - 集合框架
  - Iterator
  - Comparable
  - Comparator
  - 泛型
  - 设计模式
  - 复杂度
---

# 第 14 讲 Java 集合框架

> 说明：本课程公开页面为 **2013 年秋季学期（Fall 2013）** 版本，本笔记按该版本整理。本讲对应 `14_Collections.pdf`（37 页），页脚署名 Garrod，封面版权为 "© 2012-13 C Garrod, J Aldrich, and W Scherlis"，页脚标注 Fall 2013。本讲紧接 Midterm（10 月 15 日）之前，第 2 页是考前通知。

## 1. 本节学习目标

- 能画出 Java 集合框架的接口层次：`Iterable` → `Collection` → `List` / `Set` / `Queue`，以及独立的 `Map`。
- 能说明 `Collection`、`List`、`Set`、`Queue`、`Map` 各自的语义保证，并解释为什么 `Map` **不**继承 `Collection`。
- 能识别集合框架中使用的六种设计模式：Iterator、Marker Interface、Factory Method、Adapter、Strategy、Decorator、Template Method。
- 能说明 `Iterator.remove()` 与 `Collection.remove()` 的区别，并解释 `ConcurrentModificationException` 的成因。
- 能写出 `Comparable` 与 `Comparator` 两种排序方式，并说明 `compareTo` 的三条契约（全序、反对称、与 `equals` 一致）。
- 能解释为什么 `compareTo` 不该写 `return a - b`（溢出）。
- 能用 `Collections` 工具类的 `unmodifiableXxx` / `synchronizedXxx` 说明 Decorator 的用法。
- 能读懂 `Collections.binarySearch` 的复杂泛型签名，并说明每一层通配符的含义。
- 能说明 `AbstractList` 的「伪抽象方法」如何体现 Template Method，以及为什么这让框架可扩展。

## 2. 前置知识

- [[15-214-04-Inheritance-Typechecking-Dispatch]]：`equals` / `hashCode` 契约——`Set` 与 `Map` 的正确性完全依赖它。
- [[15-214-06-Mutability-and-Java-Potpourri]]：泛型基础、集合骨架（`Collection`→`List`→`AbstractList`）、可变性。
- [[15-214-07-Design-Patterns]]：Composite、Observer、Template Method、Strategy、Factory Method、Decorator、Adapter。
- [[15-214-09-Design-Patterns-Continued]]：Decorator 与 Java I/O——本讲的 `unmodifiableList` 是同一手法的应用。
- [[15-214-13-GUIs-Continued]]：上一讲（第 3–4 页复习了 GUI、MVC、Observer、Swing 线程架构）。

## 3. 核心概念

- **集合框架（Collections Framework）**：一组表示与操作集合的统一架构，含接口、实现、算法三部分。
- **`Iterable<E>` / `Iterator<E>`**：遍历协议。`iterator()` 是 Factory Method，`Iterator` 是 Iterator 模式。
- **`Collection<E>`**：所有集合的根接口（`Map` 除外）。
- **`List<E>`**：**有序**、**可重复**、**可按索引访问**。
- **`Set<E>`**：**元素唯一**（依 `equals`/`hashCode` 判定）。
- **`Queue<E>`**：**先进先出**语义，提供两套方法（抛异常 vs 返回特殊值）。
- **`Map<K,V>`**：**键唯一**的键值映射；**不继承 `Collection`**。
- **`SortedSet<E>` / `SortedMap<K,V>`**：保证迭代顺序按自然序或 `Comparator`。
- **`Comparable<T>`**：自然序（natural ordering），`compareTo` 返回负数/零/正数。
- **`Comparator<T>`**：外部比较策略（Strategy 模式），`compare(o1, o2)`。
- **`Collections`（工具类）**：静态算法（`sort`、`binarySearch`、`frequency`…）+ 装饰器工厂（`unmodifiableXxx`、`synchronizedXxx`）。
- **Marker Interface（标记接口）**：无方法的接口，用于声明一个编译期无法检查的行为约束。
- **fail-fast（快速失败）**：迭代期间检测到结构性修改就抛 `ConcurrentModificationException`。
- **伪抽象方法（pseudo-abstract）**：`AbstractList` 中「有实现但依赖抽象方法」的方法，属 Template Method。

## 4. 通俗理解

**集合框架为什么值得单独讲一讲？** 因为它是一个**教科书级的框架设计案例**。它同时具备：

- 一个**小而稳定的接口核心**（`Collection` 只有十来个方法）；
- 大量**可替换的实现**（`ArrayList`、`LinkedList`、`HashSet`、`TreeSet`…）；
- 一批**复用的算法**（`Collections.sort` 能排任何 `List`）；
- 而且它把前面十一讲讲过的**六种设计模式**全部用上了。

第 6 页把这个意图写得很直白：

> **Key concepts for today**
> - A tour of the Java Collections Framework
>   - Some of the features
>   - Some of the common usage patterns
>   - **Some of the design patterns in use**
> - **Iterator, Marker Interface, Factory Method, Adapter, Strategy, Decorator, Template Method**

所以这一讲表面上是「API 导览」，实质上是**「用真实代码复习设计模式」**。

**框架的设计哲学**（第 7 页）只有两句话，但很有分量：

> - **Powerful and general**
> - **Small in size and conceptual weight**
>   - **Only include fundamental operations**
>   - "Fun and easy to learn and use"

「Only include fundamental operations」是关键取舍。集合框架**故意不**提供 `sort`、`shuffle`、`frequency` 这些方法——它们被放进 `Collections` 工具类。为什么？因为如果每个集合接口都带一堆算法方法，接口会膨胀，实现者要写几十个方法，而其中大部分可以**用少数基础操作组合出来**。这个决定让接口保持「小而稳定」，代价是客户端要多记一个工具类。

这正是第 11 讲 **Small Interfaces** 原则的实践：**接口交换的信息越少，实现者负担越轻、演化越容易**。

## 5. 原理与推导

### 5.1 接口层次

先看整体结构（依据第 8–12、30 页整理）：

```
                     Iterable<E>
                         │
                    Collection<E>
                    ╱    │    ╲
              List<E>  Set<E>  Queue<E>
                 │       │        │
        ┌────────┼───────┼────────┴────────┐
   ArrayList  HashSet  SortedSet<E>     Deque<E>
   LinkedList          │                 │
   Vector           TreeSet          ArrayDeque
                                     LinkedList
                     Map<K,V>  ← 不继承 Collection！
                        │
                   SortedMap<K,V>
                        │
                     TreeMap
```

**`Map` 为什么不继承 `Collection`？**（第 12 页首句：「Does not extend `java.util.Collection<E>`」）

因为 `Collection<E>` 的语义是「**一堆 E**」，它的方法签名都是围绕单个元素类型 `E` 设计的：`add(E e)`、`contains(E e)`、`remove(E e)`。而 `Map<K,V>` 是「**K 到 V 的映射**」，它的基本操作是 `put(K, V)`、`get(K)`——**两个**类型参数，且 `get` 的参数是 `K` 而返回 `V`。

如果硬让 `Map` 继承 `Collection`，那么 `E` 该是什么？`Map.Entry<K,V>`？那样 `add(E)` 就变成了 `add(Entry)`，`contains(E)` 变成「是否包含某个 entry」——语义上很别扭，而且**丢失了按 key 查找**这个最核心的能力。所以 JDK 选择了**不继承**，只通过 `keySet()`、`values()`、`entrySet()` 三个方法**视图**暴露集合视角。

这是一个重要的设计教训：**「都是容器」不构成继承关系**。继承要求**行为契约的兼容**（里氏替换），而不是「概念上属于同一家族」。第 3 讲讲过的「Is every Foo really a Bar?」在这里有一个反例。

### 5.2 `Collection<E>`：最小接口

第 8 页列出完整方法：

```java
boolean     add(E e);
boolean     addAll(Collection<E> c);
boolean     remove(E e);
boolean     removeAll(Collection<E> c);
boolean     retainAll(Collection<E> c);
boolean     contains(E e);
boolean     containsAll(Collection<E> c);
void        clear();
int         size();
boolean     isEmpty();
Iterator<E> iterator();
Object[]    toArray();
E[]         toArray(E[] a);
…
```

三个观察：

**（1）几乎所有方法都返回 `boolean`。** `add`、`remove`、`addAll`、`removeAll`、`retainAll` 都返回「集合是否因此改变」。这对 `Set` 尤其重要：`set.add(x)` 返回 `false` 意味着「x 已存在，没加进去」。这个设计让调用者能区分「操作成功」与「操作无效果」，而不需要先 `contains` 再 `add`（那是两次查找）。

**（2）`addAll` / `removeAll` / `retainAll` 是「批量版」基础操作。** 它们不引入新语义，只是把循环下推到实现里（实现可以用更高效的方式，比如 `removeAll` 在 `HashSet` 上是 O(n) 而不是 O(n·m)）。这体现了「Only include fundamental operations」——批量操作之所以被包含，是因为它们**无法由基础操作高效组合**。

**（3）`iterator()` 是 Factory Method。** 第 20 页专门用一页讲这个：

> **Aside: The Factory Method pattern**
> （在 `Collection` 接口的 `iterator()` 旁标注）
> **Defines an interface for creating an Iterator, but allows Collection implementation to decide which Iterator to create.**

这是 Factory Method 的**最纯粹形态**：接口声明「我需要一个 `Iterator<E>`」，但**具体是哪个类**由实现决定——`ArrayList` 返回自己的 `Itr` 内部类，`LinkedList` 返回 `ListItr`，`HashSet` 返回 `HashIterator`。客户端只看到 `Iterator<E>` 接口。

值得注意的是这里**没有**独立的 `Creator` 类（不像第 7 讲的 `Factory Method` 那样有一个 `AbstractFactory` 层次）——`Collection` 自己就是 creator。这就是 GoF 所说的「Factory Method 的另一种形态：Creator 是一个接口，具体创建由实现类完成」。

### 5.3 `List<E>`：顺序

第 9 页：

> - **Defines order of a collection**
> - Extends `java.util.Collection<E>`:
> ```java
> boolean add(int index, E e);
> E       get(int index);
> E       set(int index, E e);
> int     indexOf(E e);
> int     lastIndexOf(E e);
> List<E> sublist(int fromIndex, int toIndex);
> ```

关键点：`List` 的**唯一新增语义是「顺序」**（更准确地说：**位置索引**）。所有方法都是围绕「第 i 个元素」展开的。

注意 `add(int, E)` 与 `Collection.add(E)` 的**重载**关系：前者在指定位置插入，后者追加到末尾。这是第 4 讲讲过的**重载（overloading）**——编译期按参数类型选择。

`subList(from, to)` 有一个常被忽略的陷阱：它返回的是**视图（view）**而非拷贝。对 `subList` 的修改会写回原 `List`，反之亦然。这个设计是为了性能（避免复制），但它是一个**别名（alias）**——正是第 6 讲与第 11 讲「Explicit Interfaces」警告的那种隐式耦合。

### 5.4 `Set<E>`：唯一性，以及 Marker Interface

第 10 页：

> - **Enforces uniqueness of each element in collection**
> - Extends `java.util.Collection<E>`:
> - **Aside: The Marker Interface pattern**
>   - **Problem**: You want to define a **behavioral constraint not enforced at compile time**.
>   - **Solution**: **Define an interface with no methods.**

注意 `Set` 在接口层面**没有新增任何方法**——它就是 `Collection` 的「空子接口」。这是一个极简但深刻的设计：

**为什么需要 `Set` 这个空接口？** 因为它携带的是**契约（语义保证）**而非**语法（方法签名）**：

| 接口 | 语法上新增 | 语义上新增 |
|---|---|---|
| `Collection` | 基础操作 | 「一堆元素」 |
| `List` | `get(i)`、`set(i,e)`、`indexOf`… | 有位置索引 |
| `Set` | **无** | **元素唯一** |

`Set` 的「唯一性」**无法在编译期检查**——编译器不可能知道你的 `equals` 写得对不对，也不可能知道运行时会不会加进重复元素。所以它只能作为**文档化的承诺**：所有 `Set` 的实现都必须保证唯一性，所有接受 `Set` 参数的方法都可以**假定**唯一性。

这就是 **Marker Interface** 模式：**用类型系统承载一个无法用类型系统检查的约束**。课件把它归为「Problem / Solution」的成对形式，正是在用模式语言描述一个设计决策。

其他经典 Marker Interface 包括 `java.io.Serializable`（可序列化）、`java.lang.Cloneable`（可用 `Object.clone()`）、`java.util.RandomAccess`（支持快速随机访问）。注意最后一个：`RandomAccess` 也是空的，它让 `Collections.shuffle` 等算法能**在运行时**用 `instanceof` 判断该用哪种遍历策略——这是「标记接口作为运行时优化的开关」的用法。

> 待核实：第 10 页在「Extends `java.util.Collection<E>`:」之后**没有列出任何方法**，直接进入 Marker Interface 的旁注。这与实际 JDK 一致（`Set` 在 Java 8 之前确实没有新增方法；Java 8 起通过 `default` 方法新增了 `spliterator()`、`stream()` 等，但那些来自 `Collection`）。讲义此处留白应是刻意的——它正是要说明「`Set` 没有新方法」。

### 5.5 `Queue<E>`：两套方法

第 11 页：

```java
boolean add(E e);      // These three methods
E       remove();      // might throw exceptions
E       element();

boolean offer(E e);
E       poll();        // These two methods
E       peek();        // might return null
```

这是本讲最实用的一个设计细节：`Queue` 提供**两套等价操作**，区别只在**失败时的行为**。

| 操作 | 抛异常版 | 返回特殊值版 | 失败时 |
|---|---|---|---|
| 入队 | `add(e)` | `offer(e)` | `add` 抛 `IllegalStateException`；`offer` 返回 `false` |
| 出队 | `remove()` | `poll()` | `remove` 抛 `NoSuchElementException`；`poll` 返回 `null` |
| 查看队首 | `element()` | `peek()` | `element` 抛 `NoSuchElementException`；`peek` 返回 `null` |

**为什么要两套？** 因为「队列满」和「队列空」在不同场景下是不同的东西：

- 在**有界队列**（如 `ArrayBlockingQueue`）里，「满」是**正常状态**（生产者应等待），不是异常 → 用 `offer` 返回 `false`；
- 在**无界队列**里，「满」只可能是内存耗尽，属**程序错误** → 用 `add` 抛异常更容易暴露 bug；
- 在**轮询式**消费循环里，「空」是**常态** → 用 `poll` 返回 `null` 更自然；
- 在**「必须有元素」**的协议里，「空」是**违约** → 用 `remove` 抛异常。

这个设计把「异常 vs 返回值」的选择权**交给调用者**，而不是替它决定。这与第 5 讲「受检异常迫使调用者处理」是同一个思路：**库作者应当暴露语义，让调用者选择处理策略**。

注意 `remove()` 与 `Collection.remove(Object)` 的**重载陷阱**：`Queue.remove()` 无参（出队），`Collection.remove(Object)` 有参（删指定元素）。`LinkedList` 同时实现了 `List` 和 `Deque`，所以 `list.remove(3)` 在 `List<Integer>` 上是「删索引 3」，在 `Queue` 语境下可能被理解为「删元素 3」——这是 Java 集合 API 中著名的**重载歧义**。用 `list.remove(Integer.valueOf(3))` 可以强制选择「删元素」。

### 5.6 `Map<K,V>`：键值映射

第 12 页：

```java
V       put(K key, V value);
V       get(Object key);
V       remove(Object key);
boolean containsKey(Object key);
boolean containsValue(Object value);
void    putAll(Map<K,V> m);
int     size();
boolean isEmpty();
void    clear();
Set<K>              keySet();
Collection<V>       values();
Set<Map.Entry<K,V>> entrySet();
```

三个值得注意的地方：

**（1）`put` 返回旧值。** `V put(K, V)` 返回「该 key 之前映射的值」，若之前没有则返回 `null`。这个设计让你**一次操作**完成「替换 + 得知旧值」，避免先 `get` 再 `put`（两次查找）。但也带来一个歧义：返回 `null` 可能是「之前没有」也可能是「之前映射到 `null`」——用 `containsKey` 可以区分。

**（2）`get` 与 `remove` 的参数类型是 `Object` 而不是 `K`。** 这是历史遗留（为了兼容泛型之前的 API），但它实际上放宽了约束——你可以传任何对象，只要它的 `equals`/`hashCode` 与某个 key 匹配。这在某些场景下有用（比如用「等价的但不同类型的」对象查询），但更多时候是**类型安全的漏洞**（传错类型编译器不报错）。

**（3）三个视图方法返回的都是「活的视图」，不是拷贝。**

| 方法 | 返回 | 语义 |
|---|---|---|
| `keySet()` | `Set<K>` | 键的集合视图 |
| `values()` | `Collection<V>` | 值的集合视图（**可重复**，所以是 `Collection` 不是 `Set`） |
| `entrySet()` | `Set<Map.Entry<K,V>>` | 键值对的集合视图（**迭代 `Map` 的标准方式**） |

「视图」意味着：删掉 `keySet()` 里的元素会**同时**从 `Map` 里删掉；反过来 `Map` 变了，视图也变。这个设计的价值在于**让 `Map` 能复用所有针对 `Collection` 写的算法**——比如 `Collections.frequency(map.values(), x)`、`map.keySet().retainAll(other)`。

`values()` 返回 `Collection<V>` 而非 `Set<V>` 是一个精确的类型选择：多个 key 可以映射到相同的 value，所以值的集合**可能重复**，不满足 `Set` 的唯一性契约。这正是 5.4 节说的「`Set` 是语义标记」的反向应用——**不该标 `Set` 的地方就不能标**。

### 5.7 数组与集合的互转：Adapter 模式

第 13–14 页：

> **One problem: Java arrays are not Collections**
>
> To convert a Collection to an array — use `toArray`:
> ```java
> List<String> arguments = new LinkedList<String>();
> …               // puts something into the list
> String[] arr = (String[]) arguments.toArray();
> String[] brr = arguments.toArray(new String[0]);
> ```
>
> To view an array as a Collection — use `java.util.Arrays.asList`:
> ```java
> String[] arr = {"foo", "bar", "baz", "qux"};
> List<String> arguments = Arrays.asList(arr);
> ```
>
> **Aside: The Adapter pattern**
> - **Problem**: Existing library or class **does not match the interface you want**
> - **Solution**: **Expose the functionality of the object in a different form**

**两种 `toArray` 的差别**（讲义并列展示但未解释）：

| 写法 | 返回类型 | 说明 |
|---|---|---|
| `(String[]) arguments.toArray()` | `Object[]`，强转 | **不安全**：`toArray()` 返回的是 `Object[]`，强转成 `String[]` 在运行时可能抛 `ClassCastException`（取决于实现）。已不推荐 |
| `arguments.toArray(new String[0])` | `String[]` | **推荐**：传入目标类型数组，由 JVM 按运行时类型创建正确数组 |

第二种写法为什么传一个**零长度**数组？因为它只用来**传递类型信息**；实现会（在需要时）创建新的正确类型数组。早期 JDK 里传预分配大小的数组可以避免再分配，但现代 JVM 上 `new String[0]` 已被优化得同样快（甚至更快，因为不需要清零），所以**零长度数组是当前的标准写法**。

> 待核实：讲义第 13–14 页并列了两种 `toArray` 写法，但**未说明哪种更好、为什么**。上面的取舍说明（`ClassCastException` 风险、零长度数组的优化）属笔记补充，非讲义原文。讲义只把它们作为「两种可选写法」列出。

**`Arrays.asList` 的三个陷阱**（讲义未展开，属笔记补充）：

1. **返回的是固定大小的视图，不是 `ArrayList`。** `Arrays.asList(arr).add(x)` 会抛 `UnsupportedOperationException`——因为它背后就是原数组，长度不可变。
2. **`set(i, e)` 可以，而且会写回原数组。** 这是别名——修改列表元素等于修改 `arr[i]`。
3. **对基本类型数组会「失效」**：`Arrays.asList(new int[]{1,2,3})` 返回的是 `List<int[]>`（**一个元素**，那个数组本身），不是 `List<Integer>`。因为泛型不能是基本类型。

第 14 页把它标为 **Adapter 模式**：`Arrays.asList` 把一个「数组」**适配**成「`List` 接口」，让所有针对 `List` 写的代码（包括 `Collections.sort`）能用在数组上。适配的方式是**包装**（持有原数组引用并转发调用），不是拷贝——所以才有上面三个陷阱。

这与第 9 讲 Java I/O 的 `InputStreamReader`（把字节流适配成字符流）是同一手法：**Adapter 改变接口，不改变语义**。

### 5.8 遍历集合的三种方式

第 16 页：

> **Traversing a Collection**
> - Old-school Java for loop for **ordered types**
> ```java
> List<String> arguments = …;
> for (int i = 0; i < arguments.size(); ++i) {
>   System.out.println(arguments.get(i));
> }
> ```
> - Modern standard Java for-each loop
> ```java
> List<String> arguments = …;
> for (String s : arguments) {
>   System.out.println(s);
> }
> ```
> - Use an Iterator

三种方式的适用性：

| 方式 | 适用 | 不适用 | 复杂度隐患 |
|---|---|---|---|
| 索引 `for` | 实现了 `RandomAccess` 的 `List`（`ArrayList`） | `Set`、`Queue`（无索引） | 在 `LinkedList` 上是 **O(n²)**——`get(i)` 每次都要从头走 |
| for-each | 一切 `Iterable` | 需要在遍历中**删除**元素 | 无 |
| `Iterator` | 需要在遍历中**删除**元素 | 简单遍历时啰嗦 | 无 |

**`LinkedList` 上的索引循环是经典的性能陷阱**：`for (int i = 0; i < list.size(); i++) list.get(i);` 在 `LinkedList` 上是 O(n²)，因为 `get(i)` 要从头（或从尾）走到第 i 个节点。而 for-each 用迭代器，是 O(n)。

这个例子很好地说明了第 11 讲的「接口掩盖了实现差异」的另一面：**`List` 接口让 `ArrayList` 与 `LinkedList` 可以互换，但性能特征不能互换**。所以 JDK 引入了 `RandomAccess` 标记接口，让算法能检测并选择正确的遍历策略——这是 Marker Interface 的实用价值。

### 5.9 Iterator 模式

第 17–18 页：

> **The Iterator pattern**
> ```java
> public interface java.util.Iterator<E> {
>   boolean hasNext();
>   E next();
>   void remove();  // removes previous returned item
> }                 // from the underlying collection
> ```

**Iterator 模式的核心价值**：把「遍历」从「集合的表示」中**分离**出来。

- 客户端不需要知道集合是数组、链表还是哈希表；
- 集合可以提供**多个**独立的迭代器（各自有独立位置）；
- 新增一种集合类型时，只要提供 `Iterator`，所有客户端代码不用改。

这就是第 11 讲 **Indirection** 原则：引入一个中间对象（迭代器）来解耦「使用」与「表示」。

第 18 页给出 `Iterator.remove()` 的正确用法：

```java
List<String> arguments = …;
for (Iterator<String> it = arguments.iterator();
     it.hasNext();  ) {
  String s = it.next();
  if (s.equals("Charlie"))
    it.remove();
}
// The next line will always print false!
System.out.println(arguments.contains("Charlie"));
```

关键点：`it.remove()` 删除的是「**上一次 `next()` 返回的那个元素**」。这个设计有点反直觉——`remove()` 不带参数，它依赖迭代器的**内部游标状态**。所以：

- 必须先调 `next()` 才能调 `remove()`，否则抛 `IllegalStateException`；
- 连续两次 `remove()` 也抛 `IllegalStateException`（因为中间没有 `next()`）。

这个「有状态的 `remove`」是 Iterator 模式的一个**已知缺点**：它让接口不那么函数式，也让实现必须维护额外状态。但它换来了一个重要的能力——**在遍历中安全删除**，而这是最常见的集合操作之一。

### 5.10 `ConcurrentModificationException`：fail-fast

第 19 页，本讲最重要的警告：

> **Using a `java.util.Iterator<E>`: A warning**
> - **The default Collections implementations are mutable**
> - **The `java.util.Iterator` assumes the Collection does not change while the Iterator is being used**
>   - **You will get a `ConcurrentModificationException`!**
> ```java
> List<String> arguments = …;
> for (Iterator<String> it = arguments.iterator();
>      it.hasNext();  ) {
>   String s = it.next();
>   if (s.equals("Charlie"))
>     arguments.remove("Charlie");   // runtime error!
> }
> ```

这段代码的 bug 很微妙：它**用了**迭代器，却**绕过**迭代器修改集合。

**为什么会抛异常？** 主流实现（`ArrayList`、`HashMap` 等）维护一个 **`modCount`（修改计数）** 字段。每次结构性修改（增/删元素，不包括 `set`）都会 `modCount++`。迭代器在创建时**快照**这个值，每次 `next()` 时检查「`modCount` 是否还是快照值」，不等就抛 `ConcurrentModificationException`。

所以这个异常的**准确含义**不是「多线程并发修改」，而是「**迭代期间集合被结构性修改了**」——**单线程也会抛**。这是一个常见的误解：很多人以为只有多线程才需要担心它。

**三种正确写法**：

```java
// ① 用 Iterator.remove()（推荐，向后兼容）
for (Iterator<String> it = list.iterator(); it.hasNext(); ) {
    if (it.next().equals("Charlie")) it.remove();
}

// ② 用 removeIf（Java 8+，最简洁）
list.removeIf(s -> s.equals("Charlie"));

// ③ 先收集再批量删（适合复杂条件或需要跨集合操作）
List<String> toRemove = new ArrayList<>();
for (String s : list) if (s.equals("Charlie")) toRemove.add(s);
list.removeAll(toRemove);
```

**为什么 JDK 选择「快速失败」而不是「允许修改」？** 因为允许修改会让迭代器的行为**不可预测**：删掉当前元素后，下一个元素是哪个？在 `ArrayList` 里是「原来的下一个」，在 `LinkedList` 里可能不同，在 `HashMap` 里可能触发 rehash 导致完全错乱。与其定义一套复杂且难以实现的规则，不如**直接禁止并快速报错**——这就是 fail-fast 的哲学：**宁可立刻崩溃，也不要悄悄产生错误结果**。

这与第 5 讲「运行时异常表示程序错误」一致：`ConcurrentModificationException` 是 `RuntimeException`，表示「你的代码逻辑错了」，而不是「环境出了意外」。

**注意 fail-fast 不是保证**：Javadoc 明确说它只是「尽力检测」（best-effort），不保证一定抛出。所以**不能**依赖它来做正确性保证——它只是帮你尽早发现 bug 的调试工具。

### 5.11 排序：`Collections.sort` 与 `SortedSet`

第 21 页给出两种排序方式：

```java
// ① 排序一个 List
public static void main(String[] args) {
  List<String> lst = Arrays.asList(args);
  Collections.sort(lst);
  for (String s : lst) {
    System.out.println(s);
  }
}

// ② "Abuse the SortedSet"
public static void main(String[] args) {
  SortedSet<String> set =
        new TreeSet<String>(Arrays.asList(args));
  for (String s : set) {
    System.out.println(s);
  }
}
```

课件用「**Abuse**」这个词（滥用）评价第二种写法，这个措辞值得注意。`TreeSet` 的**语义是「唯一 + 有序」**，用它来排序会**静默去重**——如果 `args` 里有重复参数，输出会少几行。所以除非你**同时**需要去重，否则应该用 `Collections.sort`。

这个例子很好地说明了第 5.4 节的观点：**集合接口的语义保证是契约，误用会带来静默的行为改变**。

> 补充（讲义未提）：`Collections.sort` 是**稳定排序**（stable）——相等元素保持原有相对顺序。这对多键排序很重要：先按次要键排、再按主要键排，就能得到「主要键优先、次要键次之」的结果。而 `TreeSet` 的排序**不是**这个意义上的稳定（它靠比较器决定顺序，相等元素根本无法共存）。

### 5.12 `Comparable<T>`：自然序及其契约

第 22 页：

```java
public interface Comparable<T> {
  int compareTo(T o);
}
```

> **General contracts**:
> - `a.compareTo(b)` should return:
>   - **< 0** if a is less than b
>   - **0** if a and b are equal
>   - **> 0** if a is greater than b
> - Should define a **total order**
>   - If `a.compareTo(b) < 0` and `b.compareTo(c) < 0`, then `a.compareTo(c)` should be `< 0`（**传递性**）
>   - If `a.compareTo(b) < 0`, then `b.compareTo(a)` should be `> 0`（**反对称性**）
> - **Should usually be consistent with `.equals`**
>   - **`a.compareTo(b) == 0` iff `a.equals(b)`**

这里有一个非常重要的对照：`Comparable` 的契约与第 4 讲的 `equals` 契约**高度相似**（都是等价关系：自反、对称/反对称、传递），但多了一条「**与 `equals` 一致**」。

**为什么「一致」只是「usually」而不是强制？** 因为 JDK 自己就有反例：`BigDecimal`。`new BigDecimal("1.0").equals(new BigDecimal("1.00"))` 返回 `false`（因为精度不同），但 `compareTo` 返回 `0`（数值相等）。这是**故意的**设计：`BigDecimal` 在 `HashSet` 里应当区分 `1.0` 与 `1.00`（它们是不同的值），但在 `TreeSet` 里会被视为相同。

**不一致的后果**：`TreeSet` 用 `compareTo` 判重，`HashSet` 用 `equals`/`hashCode` 判重。所以同一个对象放进 `TreeSet` 和 `HashSet`，**大小可能不同**。更危险的是：`TreeMap` 用 `compareTo` 找 key，如果你用 `equals` 认为相等的两个对象 `compareTo` 不为 0，`map.get(k)` 会找不到。这类 bug 极难排查。

**结论**：自定义 `Comparable` 时，**务必**让 `compareTo == 0` 与 `equals == true` 等价。若做不到（比如需要按多个字段排序但 `equals` 只比 ID），就用 `Comparator` 而不是 `Comparable`。

### 5.13 为什么不该写 `return a - b`

第 23 页给出 `Integer` 的 `compareTo` 实现：

```java
public class Integer implements Comparable<Integer> {
  private int val;
  public Integer(int val) { this.val = val; }
  …
  public int compareTo(Integer o) {
    if (val < o.val) return -1;
    if (val == o.val) return 0;
    return 1;
  }
}
```

> **Aside: Why did I not just return `val – o.val`?**

这是本讲一个精巧的伏笔。答案是 **`int` 溢出**。

`compareTo` 的返回值只需**符号**有意义（负/零/正），具体数值无关。但如果写 `return val - o.val;`，当两个数相差超过 `Integer.MAX_VALUE` 时，减法会**溢出**，符号可能反转。

具体例子：

```java
int a = 2_000_000_000;
int b = -2_000_000_000;
a - b == -294967296   // 溢出！负数！
// 但 a > b，正确的 compareTo 应返回正数
```

后果：`Collections.sort` 或 `TreeSet` 会得到**错误的顺序**，而且是**静默的**——不抛异常，只是结果乱。这类 bug 极难发现，因为只在极端数值下出现。

**正确写法**（任选）：

```java
// ① 显式比较（讲义的做法，最清晰）
if (val < o.val) return -1;
if (val == o.val) return 0;
return 1;

// ② Java 7+ 标准库
return Integer.compare(val, o.val);

// ③ 对 long 用 Long.compare，对 double 用 Double.compare
```

第 28 页的 `EmpSalComp` 里写着 `return o1.salary – o2.salary; // Why is this OK?` ——课件在这里又埋了一个问题。答案是：**在这个具体例子里它是错的**（同样有溢出风险），但因为薪水是非负的 `int` 且实际值远小于 `Integer.MAX_VALUE`，所以「实际上不会出问题」。课件的提问方式是在提醒学生：**「碰巧能跑」不等于「正确」**。

> 待核实：第 28 页的注释 "Why is this OK?" 在讲义中**未给出答案**（下一页直接转入 `Comparator` 的使用）。上述「溢出风险 + 实际值域小所以碰巧安全」的解释属笔记推断。严格来说 `o1.salary - o2.salary` 在 `salary` 可能为负或极大时确实会溢出，所以更准确的答案是「**它并不真的 OK，只是因为值域假设而侥幸**」。这与第 23 页刻意用三个 `if` 而非减法的做法形成对照。

### 5.14 `Comparator<T>`：外部比较策略

第 26–27 页：

> ```java
> public class Employee implements Comparable<Employee> {
>   protected Name name;
>   protected int  salary;
>   …
> }
> ```
> - **What if we want to sort Employees by name, usually, but sometimes sort by salary?**
> - **Answer: There's a Strategy pattern interface for that**
> ```java
> public interface Comparator<T> {
>   public int     compare(T o1, T o2);
>   public boolean equals(Object obj);
> }
> ```

课件明确说 `Comparator` 是 **Strategy 模式**的接口。对照第 7 讲第 27 页的 `sort(int[], Comparator)`——那是同一个模式在数组排序上的应用。

**`Comparable` vs `Comparator`** 的本质差别：

| 维度 | `Comparable<T>` | `Comparator<T>` |
|---|---|---|
| 位置 | 实现**在元素类内部** | 实现**在独立的类** |
| 数量 | 一个类只能有**一种**自然序 | 可以有**任意多种**策略 |
| 修改原类 | 需要 | **不需要** |
| 排序调用 | `Collections.sort(list)` | `Collections.sort(list, cmp)` |
| 适用 | 「这个类天然有一种顺序」 | 「需要多种排序方式」/「无法修改元素类」 |
| 模式 | —（内建能力） | **Strategy** |

`Comparator` 的 `equals` 方法在接口里声明，但**通常不需要实现**——因为任何类都继承 `Object.equals`，接口里的声明只是**强调契约**（两个 comparator 相等意味着它们产生相同顺序）。JDK 文档明确说「不需要覆写 `Object.equals`」，这个声明是历史遗留。

第 28 页的完整例子：

```java
public class Employee implements Comparable<Employee> {
  protected Name name;
  protected int  salary;
  public int compareTo(Employee o) {
    return name.compareTo(o.name);
  }
}

public class EmpSalComp implements Comparator<Employee> {
  public int compare (Employee o1, Employee o2) {
    return o1.salary – o2.salary;  // Why is this OK?
  }
  public boolean equals(Object obj) {
    return obj instanceof EmpSalComp;
  }
}
```

`Employee` 的 `compareTo` 委托给 `name.compareTo`——这就是第 24–25 页 `Name` 例子的用法：**复合对象的比较逐字段委托**。

第 24–25 页的 `Name` 例子值得一读：

```java
// 第一版：没有实现 Comparable
public class Name {
  private String first;
  private String last;
  public Name(String first, String last) {  // should
    this.first = first;  this.last = last;  // check
  }                                         // for null
  …
}

// 第二版：Hint: Strings implement Comparable<String>
public class Name implements Comparable<Name> {
  private String first;
  private String last;
  public Name(String first, String last) { … }
  …
  public int compareTo(Name o) {
    int lastComparison = last.compareTo(o.last);
    if (lastComparison != 0) return lastComparison;
    return first.compareTo(o.first);
  }
}
```

三个要点：

1. **「Hint: Strings implement `Comparable<String>`」** —— 这是关键提示。不要手写字符串比较，直接委托给 `String.compareTo`（它按 Unicode 码点比较）。
2. **逐字段委托的模式**：先比 `last`，若不相等就返回；相等再比 `first`。这是**多键排序**的标准写法。
3. **注意顺序**：先 `last` 后 `first`，即「按姓排序，姓相同再按名」——西方式的姓名排序。如果要按中文习惯（先名后姓）就要反过来。
4. **注释「should check for null」** —— 构造函数没有做 `null` 检查。若 `first` 或 `last` 为 `null`，`compareTo` 里的 `last.compareTo(o.last)` 会抛 `NullPointerException`。这是第 5 讲「前置条件」的实例：构造函数应当拒绝 `null`（或用 `Objects.requireNonNull`）。

### 5.15 用 `Comparator` 排序

第 29 页：

> **Using a Comparator**
> - **Order-dependent classes and methods take a Comparator as an argument**
> ```java
> public class Main {
>   public static void main(String[] args) {
>     SortedSet<Employee> empByName =   // sorted by name
>           new TreeSet<Employee>();
>
>     SortedSet<Employee> empBySal =  // sorted by salary
>           new TreeSet<Employee>(new EmpSalComp());
>   }
> }
> ```

这是 **Strategy 模式**的教科书用法：

- `TreeSet` 是 **Context**；
- `Comparator` 是 **Strategy 接口**；
- `EmpSalComp` 是 **ConcreteStrategy**；
- 通过构造函数**注入**策略（依赖注入）。

注意第一个 `TreeSet<Employee>()` **不传 comparator** ——它使用 `Employee` 的**自然序**（`compareTo`，按 name）。第二个传入 `EmpSalComp`，改用按 salary 排序。同一个类，两种顺序，**不需要修改 `Employee`**。

这也解释了为什么 `SortedSet` 接口要有 `comparator()` 方法（第 30 页）：

> - **The `comparator` method returns `null` if the natural ordering is being used**

返回 `null` 是一个**哨兵值**，表示「用自然序」。这个设计有点不优雅（更好的做法是返回 `Optional` 或一个表示自然序的常量对象），但它是 Java 早期 API 的常见风格。使用时的判据：`if (set.comparator() == null) { /* 自然序 */ }`。

第 30 页还列出 `SortedSet` 的其他方法：

```java
Comparator<E> comparator();
E             first();
E             last();
SortedSet<E>  subSet(E fromElement, E toElement);
SortedSet<E>  headSet(E toElement);
SortedSet<E>  tailSet(E fromElement);
```

`subSet` / `headSet` / `tailSet` 返回的都是**视图**（同 5.6 节 `Map` 的视图，同 5.3 节 `subList` 的视图）——这是一个贯穿整个集合框架的一致设计：**范围操作返回视图而非拷贝**。

### 5.16 `Collections` 工具类

第 31–32 页：

> **The `java.util.Collections` class**
> - **Standard implementations of common algorithms**
>   - `binarySearch`, `copy`, `fill`, `frequency`, `indexOfSubList`, `min`, `max`, `nCopies`, `replaceAll`, `reverse`, `rotate`, `shuffle`, `sort`, `swap`, …

两个例子：

```java
// 排序
List<String> lst = Arrays.asList(args);
Collections.sort(lst);
for (String s : lst) System.out.println(s);

// 计数
List<String> lst = Arrays.asList(args);
int x = Collections.frequency(lst, "Charlie");
System.out.println("There are " + x + " students named Charlie");
```

**注意 `Collections`（带 s）与 `Collection`（不带 s）的区别**——这是一个经典的混淆点：

| 名字 | 是什么 | 用途 |
|---|---|---|
| `Collection` | **接口** | 「一堆元素」的抽象 |
| `Collections` | **工具类**（`final`，私有构造，全静态方法） | 算法 + 装饰器工厂 |

命名上只差一个 `s`，但一个是类型、一个是工具类。JDK 里还有 `Arrays`（对应数组）、`Objects`（对应 `Object`）——同一命名惯例。

**为什么算法放在工具类而不是接口里？** 回到第 7 页的哲学「Only include fundamental operations」：如果把 `sort`、`shuffle`、`frequency` 都放进 `Collection` 接口，那么每个实现类（包括你自己写的）都要实现这十几个方法——即使它们都可以用 `iterator()` + `size()` 组合出来。放进工具类后，**实现者只需实现少数基础方法，就自动获得所有算法**。

这是第 11 讲 **Modular Composability** 与 **Small Interfaces** 的联合体现。

### 5.17 Decorator：`unmodifiableXxx` 与 `synchronizedXxx`

第 33 页：

> **The `java.util.Collections` class**
> - **Many uses of the Decorator pattern**:
> ```java
> static List<T>  unmodifiableList(List<T>  lst);
> static Set<T>   unmodifiableSet( Set<T>   set);
> static Map<K,V> unmodifiableMap( Map<K,V> map);
> static List<T>  synchronizedList(List<T>  lst);
> static Set<T>   synchronizedSet( Set<T>   set);
> static Map<K,V> synchronizedMap( Map<K,V> map);
> ```

这是 **Decorator 模式**的完美实例（对照第 9 讲 `FilterOutputStream`）：

```java
List<String> base = new ArrayList<>();
List<String> safe = Collections.unmodifiableList(base);

safe.add("x");        // 抛 UnsupportedOperationException
safe.get(0);          // 可以读
base.add("y");        // 可以（通过原始引用）
safe.get(0);          // 能看到 "y" —— 它只是包装，不是拷贝
```

**Decorator 的三个特征**（第 9 讲第 25 页）：

1. **同一接口**：`unmodifiableList` 返回的也是 `List`，可以传给任何接受 `List` 的方法；
2. **包装而非继承**：内部持有一个 `List` 引用，转发调用；
3. **可以叠加**：`Collections.unmodifiableList(Collections.synchronizedList(list))` —— 先加锁再禁改。

**`unmodifiableList` 的一个重要局限**：它只阻止**通过这个引用**修改。如果原 `base` 还被别处持有，仍能改，而且改动对 `safe` 可见。所以它不是「不可变对象」，只是「**不可变视图**」。真正的不可变集合需要拷贝（Java 9 的 `List.copyOf`）。

这个区别在第 6 讲「不可变性」的语境下很重要：**不可变视图 ≠ 不可变对象**。前者是接口约束，后者是表示约束。

**`synchronizedXxx` 的局限**：它给每个方法加锁，但**复合操作仍然不安全**：

```java
// 线程不安全！即使 list 是 synchronizedList
if (!list.isEmpty()) {
    list.get(0);      // 两步之间可能有别的线程清空列表
}
```

正确做法是**在客户端加锁**（`synchronized (list) { ... }`），或使用并发集合（`CopyOnWriteArrayList`、`ConcurrentHashMap`）。这是「装饰器只能保护单个调用，不能保护调用序列」的经典问题。

### 5.18 一个真实的复杂泛型签名

第 34 页用一整页解读 `binarySearch` 的签名：

```java
static int binarySearch(
     List<? extends Comparable<? super T>> list,
     T                                     key);
```

> - **An object of some type T to search for**
> - **A List of objects of some type that has a `compareTo` method that can take an object of type T as an argument**

逐层拆解：

| 部分 | 含义 |
|---|---|
| `T key` | 要查找的键，类型为 `T` |
| `List<...>` | 一个列表 |
| `? extends Comparable<...>` | 列表元素类型必须是 `Comparable` 的**某个子类型**（协变：可以是 `Comparable` 的实现类） |
| `? super T` | 那个 `Comparable` 的**类型参数**必须是 `T` 或其**父类型**（逆变：`compareTo` 要能接受 `T`） |

**为什么需要 `? super T`？** 因为 `compareTo` 的参数是**消费者**（consumes），按 PECS 原则（Producer Extends, Consumer Super）应该用 `super`。举例：

- `List<Employee>` 的元素是 `Employee`，它 `implements Comparable<Employee>`；
- 想用 `Employee` 的父类 `Person` 作为 key 查找（`Person` 也可以比较 `Employee`，因为 `Employee` 是 `Person`）——`Comparable<? super T>` 允许这种用法。

**这个签名告诉我们什么？** 它说明**泛型的变型（variance）不是学术装饰，而是 API 可用性的关键**。如果写成 `List<Comparable<T>>`（不变），那么 `List<Employee>`（其中 `Employee implements Comparable<Employee>`）**不能**传给这个参数——因为 `Comparable<Employee>` 与 `Comparable<T>` 在 `T=Employee` 时确实相同，但一旦涉及子类型就失效。

课件的两行说明写得极其精确：

> A List of objects of some type that has a `compareTo` method **that can take an object of type T as an argument**

这句话就是 `? super T` 的自然语言翻译。它示范了一种重要的能力：**读懂复杂泛型签名的方法是把每一层翻译成一句自然语言**。

### 5.19 集合框架本身是框架：`AbstractList` 与伪抽象方法

第 35–36 页是本讲的收尾，也是最有深度的一页。

**第 35 页：你可以写自己的集合**

> **Java Collections as a framework**
> - **You can write specialty collections**
>   - Custom representations and algorithms
>   - Custom behavioral guarantees
>     - e.g., **file-based storage**
> - **JDK built-in algorithms would then be calling your collections code**

最后一句是**框架的标志**：**依赖反转**。你写的集合类不是「使用」JDK 的算法，而是被 JDK 的算法「使用」——`Collections.sort` 会调用你的 `get(i)` 和 `size()`。控制权在框架手里。

这正是第 12 讲「好莱坞法则」的又一次出现：「不要调用我们，我们会调用你」。

**第 36 页：`AbstractList` 的伪抽象方法**

```java
public abstract class AbstractList<T> {
  abstract T   get(int i);             // Template Method
  abstract int size();                 // Template Method
  boolean      set(int i, E e);        // set add remove are
  boolean      add(E e);               // pseudo-abstract
  boolean      remove(E e);            // Template Methods
  boolean      addAll(Collection<E> c);
  boolean      removeAll(Collection<E> c);
  boolean      retainAll(Collection<E> c);
  boolean      contains(E e);
  boolean      containsAll(Collection<E> c);
  void         clear();
  boolean      isEmpty();
  Iterator<E>  iterator();
  Object[]     toArray();
  E[]          toArray(E[] a);
  …
}
```

课件用三种标注区分了三类方法：

| 标注 | 方法 | 含义 |
|---|---|---|
| **`abstract`（真抽象）** | `get(int)`、`size()` | 子类**必须**实现，它们依赖具体表示 |
| **Template Method** | `iterator()`、`toArray()` 等 | 父类用 `get`/`size` 实现了通用逻辑，子类**可以**覆写以优化 |
| **pseudo-abstract（伪抽象）** | `set`、`add`、`remove` | 父类**有实现**，但默认抛 `UnsupportedOperationException`；子类按需覆写 |

**为什么叫「伪抽象」？** 因为它们在语法上**不是** `abstract`（有方法体），但在语义上**表现得像抽象**——不覆写就无法使用。这是**在 Java 没有 `default` 方法（Java 8 之前）时的权宜之计**：

- 如果声明为 `abstract`，那么所有子类**必须**实现，包括只读列表（它们不想支持 `add`）；
- 如果声明为普通方法，那么子类**可能忘记**覆写，导致调用时抛异常却不知道原因；
- 折中方案：**提供默认实现但抛 `UnsupportedOperationException`**，让「不支持」成为一个**显式的、运行时可检测的**状态。

这就是为什么 `Collections.unmodifiableList` 能工作——它返回一个 `AbstractList` 的子类，`get`/`size` 转发给底层，`add`/`remove` **不覆写**，于是继承到「抛 `UnsupportedOperationException`」的默认实现。

**这套设计的教学价值**：它展示了**抽象类作为「部分实现的接口」**的威力。子类只需实现 **2 个方法**（`get`、`size`），就获得了 `AbstractList` 提供的**十几个**方法。这是第 11 讲 **Modular Composability**（可复用）与 **Modular Decomposability**（可分工）的双赢。

而 `Collection` 接口 + `AbstractList` 骨架类 + 具体实现（`ArrayList`、`LinkedList`）的三层结构，是 JDK 集合框架的**通用骨架**：

```
接口（Collection/List）       ← 契约
   ↑
骨架实现（AbstractCollection/AbstractList）  ← 复用
   ↑
具体实现（ArrayList/LinkedList）  ← 表示
```

这个三层模式后来被总结为「**接口 + 骨架实现 + 具体类**」，是 Java 库设计的标准做法（`AbstractSet`、`AbstractMap`、`AbstractQueue` 都是同构的）。

第 37 页只有一句：

> **Next time…**
> - **Midterm exam on Tuesday**

第 2 页也重申了考试安排：

> **Administrivia**
> - **Midterm exam in class next Tuesday, 15 Oct**
> - **Midterm review session Sunday 1 – 3 p.m., Hamburg Hall 1000**
>   - Review sheet will be released before the review session
>   - Will also release a sample midterm exam soon

## 6. 代码示例

### 6.1 官方课程代码

出自 `14_Collections.pdf` 第 8 页（`Collection` 接口）：

```java
boolean     add(E e);
boolean     addAll(Collection<E> c);
boolean     remove(E e);
boolean     removeAll(Collection<E> c);
boolean     retainAll(Collection<E> c);
boolean     contains(E e);
boolean     containsAll(Collection<E> c);
void        clear();
int         size();
boolean     isEmpty();
Iterator<E> iterator();
Object[]    toArray();
E[]         toArray(E[] a);
…
```

出自第 9 页（`List` 接口新增方法）：

```java
boolean add(int index, E e);
E       get(int index);
E       set(int index, E e);
int     indexOf(E e);
int     lastIndexOf(E e);
List<E> sublist(int fromIndex, int toIndex);
```

出自第 11 页（`Queue` 的两套方法）：

```java
boolean add(E e);    // These three methods
E       remove();    // might throw exceptions
E       element();

boolean offer(E e);
E       poll();      // These two methods
E       peek();      // might return null
```

出自第 12 页（`Map` 接口）：

```java
V       put(K key, V value);
V       get(Object key);
V       remove(Object key);
boolean containsKey(Object key);
boolean containsValue(Object value);
void    putAll(Map<K,V> m);
int     size();
boolean isEmpty();
void    clear();
Set<K>              keySet();
Collection<V>       values();
Set<Map.Entry<K,V>> entrySet();
```

出自第 13–14 页（数组与集合互转）：

```java
List<String> arguments = new LinkedList<String>();
…               // puts something into the list
String[] arr = (String[]) arguments.toArray();
String[] brr = arguments.toArray(new String[0]);

String[] arr = {"foo", "bar", "baz", "qux"};
List<String> arguments = Arrays.asList(arr);
```

出自第 16 页（三种遍历）：

```java
// Old-school
List<String> arguments = …;
for (int i = 0; i < arguments.size(); ++i) {
  System.out.println(arguments.get(i));
}

// for-each
List<String> arguments = …;
for (String s : arguments) {
  System.out.println(s);
}
```

出自第 17–18 页（`Iterator` 接口与删除）：

```java
public interface java.util.Iterator<E> {
  boolean hasNext();
  E next();
  void remove();  // removes previous returned item
}                 // from the underlying collection

List<String> arguments = …;
for (Iterator<String> it = arguments.iterator();
     it.hasNext();  ) {
  String s = it.next();
  System.out.println(s);
}
```

```java
List<String> arguments = …;
for (Iterator<String> it = arguments.iterator();
     it.hasNext();  ) {
  String s = it.next();
  if (s.equals("Charlie"))
    it.remove();
}
// The next line will always print false!
System.out.println(arguments.contains("Charlie"));
```

出自第 19 页（`ConcurrentModificationException` 反例）：

```java
List<String> arguments = …;
for (Iterator<String> it = arguments.iterator();
     it.hasNext();  ) {
  String s = it.next();
  if (s.equals("Charlie"))
    arguments.remove("Charlie"); // runtime error!
}
```

出自第 21 页（两种排序）：

```java
public static void main(String[] args) {
  List<String> lst = Arrays.asList(args);
  Collections.sort(lst);
  for (String s : lst) {
    System.out.println(s);
  }
}

public static void main(String[] args) {
  SortedSet<String> set =
        new TreeSet<String>(Arrays.asList(args));
  for (String s : set) {
    System.out.println(s);
  }
}
```

出自第 22 页（`Comparable` 接口与契约）：

```java
public interface Comparable<T> {
  int compareTo(T o);
}
```

出自第 23 页（`Integer.compareTo`）：

```java
public class Integer implements Comparable<Integer> {
  private int val;
  public Integer(int val) { this.val = val; }
  …
  public int compareTo(Integer o) {
    if (val < o.val) return -1;
    if (val == o.val) return 0;
    return 1;
  }
}
```

出自第 25 页（`Name` 实现 `Comparable`）：

```java
public class Name implements Comparable<Name> {
  private String first;
  private String last;
  public Name(String first, String last) {  // should
    this.first = first;  this.last = last;  // check
  }                                         // for null
  …
  public int compareTo(Name o) {
    int lastComparison = last.compareTo(o.last);
    if (lastComparison != 0) return lastComparison;
    return first.compareTo(o.first);
  }
}
```

出自第 27 页（`Comparator` 接口）：

```java
public interface Comparator<T> {
  public int     compare(T o1, T o2);
  public boolean equals(Object obj);
}
```

出自第 28 页（`Employee` 与 `EmpSalComp`）：

```java
public class Employee implements Comparable<Employee> {
  protected Name name;
  protected int  salary;
  public int compareTo(Employee o) {
    return name.compareTo(o.name);
  }
}

public class EmpSalComp implements Comparator<Employee> {
  public int compare (Employee o1, Employee o2) {
    return o1.salary – o2.salary;  // Why is this OK?
  }
  public boolean equals(Object obj) {
    return obj instanceof EmpSalComp;
  }
}
```

出自第 29 页（用 `Comparator` 构造 `TreeSet`）：

```java
public class Main {
  public static void main(String[] args) {
    SortedSet<Employee> empByName =   // sorted by name
          new TreeSet<Employee>();

    SortedSet<Employee> empBySal =  // sorted by salary
          new TreeSet<Employee>(new EmpSalComp());
  }
}
```

出自第 30 页（`SortedSet` 接口）：

```java
Comparator<E> comparator();
E             first();
E             last();
SortedSet<E>  subSet(E fromElement, E toElement);
SortedSet<E>  headSet(E toElement);
SortedSet<E>  tailSet(E fromElement);
```

出自第 31–32 页（`Collections` 工具类）：

```java
public class Main() {
  public static void main(String[] args) {
    List<String> lst = Arrays.asList(args);
    Collections.sort(lst);
    for (String s : lst) {
      System.out.println(s);
    }
  }
}

public class Main() {
  public static void main(String[] args) {
    List<String> lst = Arrays.asList(args);
    int x = Collections.frequency(lst, "Charlie");
    System.out.println("There are " + x +
                       " students named Charlie");
  }
}
```

出自第 33 页（Decorator 工厂）：

```java
static List<T>  unmodifiableList(List<T>  lst);
static Set<T>   unmodifiableSet( Set<T>   set);
static Map<K,V> unmodifiableMap( Map<K,V> map);
static List<T>  synchronizedList(List<T>  lst);
static Set<T>   synchronizedSet( Set<T>   set);
static Map<K,V> synchronizedMap( Map<K,V> map);
```

出自第 34 页（`binarySearch` 的真实签名）：

```java
static int binarySearch(
     List<? extends Comparable<? super T>> list,
     T                                     key);
```

出自第 36 页（`AbstractList` 的方法分类）：

```java
abstract T   get(int i);             // Template Method
abstract int size();                 // Template Method
boolean      set(int i, E e);        // set add remove are
boolean      add(E e);               // pseudo-abstract
boolean      remove(E e);            // Template Methods
boolean      addAll(Collection<E> c);
boolean      removeAll(Collection<E> c);
boolean      retainAll(Collection<E> c);
boolean      contains(E e);
boolean      containsAll(Collection<E> c);
void         clear();
boolean      isEmpty();
Iterator<E>  iterator();
Object[]     toArray();
E[]          toArray(E[] a);
…
```

### 6.2 Agent 自行编写的教学示例

> 非官方，仅用于说明概念。

**示例 A：用 `AbstractList` 写一个只读的「平方数列表」**

```java
import java.util.*;

// 只实现 get 与 size，就自动获得 iterator/contains/indexOf/toString…
public final class Squares extends AbstractList<Integer> {
    private final int n;
    public Squares(int n) { this.n = n; }

    @Override public Integer get(int i) {
        if (i < 0 || i >= n) throw new IndexOutOfBoundsException("i=" + i);
        return i * i;
    }
    @Override public int size() { return n; }
    // add/remove/set 不覆写 → 继承 AbstractList 的「抛 UnsupportedOperationException」
}

// 使用
List<Integer> sq = new Squares(5);       // [0, 1, 4, 9, 16]
System.out.println(sq);                  // 自动有 toString
System.out.println(sq.contains(9));      // true（AbstractList 用 get 逐个比）
Collections.reverse(sq);                 // 抛 UnsupportedOperationException（set 未实现）
```

这个例子演示了 5.19 节的「伪抽象方法」：`Squares` 只写了 **2 个方法**，就获得了 `AbstractList` 的十几个方法。而 `add`/`set`/`remove` 的「默认抛异常」正好符合一个**只读**列表的语义——不需要额外代码。

对照：如果不继承 `AbstractList` 而直接 `implements List`，就要实现 **25 个以上**方法。

**示例 B：`Iterator.remove()` vs `Collection.remove()`**

```java
List<String> names = new ArrayList<>(List.of("Alice", "Charlie", "Bob", "Charlie"));

// ✗ 错误：绕过迭代器修改 → ConcurrentModificationException
try {
    for (String s : names) {
        if (s.equals("Charlie")) names.remove(s);
    }
} catch (ConcurrentModificationException ex) {
    System.out.println("fail-fast 触发了：" + ex.getClass().getSimpleName());
}

// ✓ 正确 ①：用 Iterator.remove()
names = new ArrayList<>(List.of("Alice", "Charlie", "Bob", "Charlie"));
for (Iterator<String> it = names.iterator(); it.hasNext(); ) {
    if (it.next().equals("Charlie")) it.remove();
}
System.out.println(names);   // [Alice, Bob]

// ✓ 正确 ②：removeIf（Java 8+）
names = new ArrayList<>(List.of("Alice", "Charlie", "Bob", "Charlie"));
names.removeIf(s -> s.equals("Charlie"));
System.out.println(names);   // [Alice, Bob]

// ✓ 正确 ③：先收集再批量删（条件复杂时）
names = new ArrayList<>(List.of("Alice", "Charlie", "Bob", "Charlie"));
List<String> toRemove = new ArrayList<>();
for (String s : names) if (s.equals("Charlie")) toRemove.add(s);
names.removeAll(toRemove);
```

注意第一种错误写法在**单线程**下也会抛异常——`ConcurrentModificationException` 与多线程无关，它检测的是「迭代期间的结构性修改」。

**示例 C：`Comparable` 与 `Comparator` 并用**

```java
import java.util.*;

public final class Student implements Comparable<Student> {
    private final String name;
    private final int    score;

    public Student(String name, int score) {
        this.name  = Objects.requireNonNull(name, "name");   // 前置条件
        this.score = score;
    }

    public String name()  { return name; }
    public int    score() { return score; }

    // 自然序：按分数从高到低；分数相同按名字
    @Override public int compareTo(Student o) {
        int c = Integer.compare(o.score, this.score);   // 注意 o 在前 = 降序
        if (c != 0) return c;
        return this.name.compareTo(o.name);
    }

    @Override public boolean equals(Object obj) {
        if (this == obj) return true;
        if (!(obj instanceof Student)) return false;
        Student s = (Student) obj;
        return score == s.score && name.equals(s.name);
    }
    @Override public int hashCode() { return Objects.hash(name, score); }
    @Override public String toString() { return name + ":" + score; }
}

// 外部策略：按名字长度
final class ByNameLength implements Comparator<Student> {
    @Override public int compare(Student a, Student b) {
        return Integer.compare(a.name().length(), b.name().length());
    }
}

// 使用
List<Student> list = new ArrayList<>(List.of(
    new Student("Alice", 90), new Student("Bo", 90), new Student("Cindy", 85)));

Collections.sort(list);                                  // 自然序：90, 90, 85
System.out.println(list);                                // [Alice:90, Bo:90, Cindy:85]

Collections.sort(list, new ByNameLength());              // 外部策略：按名字长度
System.out.println(list);                                // [Bo:90, Alice:90, Cindy:85]

SortedSet<Student> byScore = new TreeSet<>(list);        // 用自然序
SortedSet<Student> byLen   = new TreeSet<>(new ByNameLength());  // 用策略
```

三个要点：

1. **`compareTo` 与 `equals` 保持一致**：`compareTo == 0` 当且仅当 `equals == true`（这里两个字段都比了，所以一致）。如果只比 `score`，就会破坏一致性——同分不同名的两个学生会在 `TreeSet` 里被误判为重复。
2. **`Integer.compare` 而非减法**：避免溢出。
3. **`Comparator` 不需要修改 `Student`**：`ByNameLength` 是独立类，`Student` 完全不知道它的存在——这是 Strategy 模式的价值。

**示例 D：不可变视图的陷阱**

```java
List<String> base = new ArrayList<>();
base.add("a");

List<String> view = Collections.unmodifiableList(base);
view.add("b");              // ✗ UnsupportedOperationException
System.out.println(view);   // [a]

base.add("c");              // ✓ 通过原引用可以改
System.out.println(view);   // [a, c] —— 视图「看到了」变化！

// 真正的不可变：拷贝
List<String> snapshot = List.copyOf(base);   // Java 10+
base.add("d");
System.out.println(snapshot);   // [a, c] —— 不受影响
```

`unmodifiableList` 是**视图**（Decorator，包装同一个底层对象），`List.copyOf` 是**快照**（拷贝）。第 6 讲说的「不可变对象」只有后者才满足。若要把一个可变列表「安全地交给别人」，必须拷贝；若只是想「防止自己被误改」，视图就够了。

**示例 E：`Arrays.asList` 的三个陷阱**

```java
// 陷阱 1：固定大小，不能增删
List<String> fixed = Arrays.asList("a", "b");
fixed.set(0, "z");     // ✓ 可以（写回原数组）
fixed.add("c");        // ✗ UnsupportedOperationException

// 陷阱 2：它是原数组的别名
String[] arr = {"a", "b"};
List<String> alias = Arrays.asList(arr);
alias.set(0, "z");
System.out.println(arr[0]);   // "z" —— 原数组被改了！

// 陷阱 3：基本类型数组会「退化」成一个元素
int[] nums = {1, 2, 3};
List<int[]> weird = Arrays.asList(nums);   // List<int[]>，size() == 1！
System.out.println(weird.size());          // 1，不是 3
```

陷阱 3 的成因：泛型参数不能是基本类型，所以 `Arrays.asList(int[])` 把**整个数组**当作一个 `Object` 元素。要用 `List<Integer>` 必须手动装箱（或用 `IntStream.of(nums).boxed().collect(...)`）。

**示例 F：`Queue` 的两套方法对照**

```java
Queue<String> q = new ArrayDeque<>();

// 空队列时：
// q.remove();   → 抛 NoSuchElementException
// q.poll();     → 返回 null
// q.element();  → 抛 NoSuchElementException
// q.peek();     → 返回 null

// 有界队列满时（以 ArrayBlockingQueue 为例）：
// q.add("x");   → 抛 IllegalStateException
// q.offer("x"); → 返回 false

// 典型用法：轮询消费（空是常态 → 用 poll）
String item;
while ((item = q.poll()) != null) {
    process(item);
}
```

判据：**「失败」是异常情况还是正常情况？** 异常情况用抛异常版（早暴露 bug），正常情况用返回特殊值版（自然的控制流）。

## 7. 容易混淆的概念

| 概念 A | 概念 B | 区别 |
|---|---|---|
| **`Collection`（接口）** | **`Collections`（工具类）** | 前者是「一堆元素」的抽象类型；后者是 `final` 工具类，全静态方法（算法 + 装饰器工厂）。名字只差一个 `s` |
| **`List`** | **`Set`** | 前者有序、可重复、有索引；后者元素唯一（依 `equals`/`hashCode`）。`Set` 在接口层面**不新增任何方法** |
| **`Set`** | **`SortedSet`** | 前者只保证唯一；后者还保证**迭代顺序**（自然序或 `Comparator`）。`TreeSet` 实现 `SortedSet` |
| **`Map`** | **`Collection`** | `Map` **不继承** `Collection`——因为它有两个类型参数、核心操作是按 key 查找，与「一堆 E」的语义不兼容 |
| **`map.keySet()`** | **`map.values()`** | 前者返回 `Set<K>`（键唯一）；后者返回 `Collection<V>`（值**可能重复**，所以不是 `Set`） |
| **`Collection.add(e)`** | **`List.add(i, e)`** | 前者追加到末尾（`boolean` 返回值）；后者插入到索引 i（`void`）。**重载**，编译期按参数类型选择 |
| **`Queue.remove()`** | **`Collection.remove(Object)`** | 前者无参、出队、抛异常；后者有参、删指定元素。`LinkedList` 同时是两者，`remove(3)` 有歧义 |
| **`Queue.add/remove/element`** | **`Queue.offer/poll/peek`** | 前者失败时**抛异常**；后者失败时返回 `false`/`null`。语义相同，失败策略不同 |
| **`Iterator.remove()`** | **`Collection.remove(o)`** | 前者删「上次 `next()` 返回的元素」（有状态、安全）；后者删指定元素（遍历中调用 → `ConcurrentModificationException`） |
| **`ConcurrentModificationException`** | **多线程问题** | 前者是 **fail-fast** 检测：迭代期间集合被结构性修改，**单线程也会抛**。与并发无关 |
| **fail-fast** | **fail-safe** | 前者立刻抛异常（`ArrayList`、`HashMap`）；后者在副本上迭代（`CopyOnWriteArrayList`、`ConcurrentHashMap`），不抛但可能看到旧数据 |
| **`Comparable<T>`** | **`Comparator<T>`** | 前者在**元素类内部**（`compareTo(T)`），一种自然序；后者是**独立策略类**（`compare(T,T)`），可任意多种。后者是 Strategy 模式 |
| **`compareTo` 返回 0** | **`equals` 返回 true** | 应当等价（「consistent with equals」），但**不强制**。`BigDecimal` 是反例：`1.0` 与 `1.00` 的 `equals` 为 false，`compareTo` 为 0 |
| **`return a - b`** | **`Integer.compare(a, b)`** | 前者在差值超过 `int` 范围时**溢出**，符号反转 → 排序结果错误且**静默**。后者安全 |
| **`Arrays.asList(arr)`** | **`new ArrayList<>(...)`** | 前者是**固定大小的视图**（Adapter，别名原数组，`add` 抛异常）；后者是独立的可变列表 |
| **`toArray()`** | **`toArray(new T[0])`** | 前者返回 `Object[]`，强转有 `ClassCastException` 风险；后者由 JVM 按运行时类型创建正确数组。推荐后者 |
| **`subList` / `subSet` / `keySet`** | **拷贝** | 全是**视图**：修改会写回原集合，原集合变化也能被看到。这是贯穿集合框架的一致设计 |
| **`unmodifiableList`** | **不可变对象** | 前者是**不可变视图**（Decorator，底层仍可变）；后者要求拷贝（`List.copyOf`）。前者防不住「通过原引用修改」 |
| **`synchronizedList`** | **线程安全** | 前者只给**单个方法**加锁；复合操作（`if (!isEmpty()) get(0)`）仍不安全，需客户端加锁或用并发集合 |
| **`AbstractList` 的 `abstract` 方法** | **伪抽象方法** | 前者子类**必须**实现（`get`、`size`）；后者父类**有实现**但默认抛 `UnsupportedOperationException`，子类按需覆写（`add`、`set`、`remove`） |
| **`AbstractList`（骨架类）** | **`List`（接口）** | 前者提供部分实现（Template Method），子类只需 2 个方法；后者是纯契约，直接实现要写 25+ 个方法 |
| **Marker Interface** | **普通接口** | 前者**无方法**，只承载语义约束（`Set`、`Serializable`、`RandomAccess`）；后者约定行为 |
| **Iterator 模式** | **for-each** | 后者是前者的**语法糖**（编译成 `iterator()` + `hasNext()`/`next()`）。需要 `remove()` 时必须显式用 `Iterator` |
| **索引 `for` 遍历 `LinkedList`** | **for-each 遍历 `LinkedList`** | 前者 O(n²)（`get(i)` 每次从头走）；后者 O(n)。`RandomAccess` 标记接口正是为区分这两者 |

## 8. 对应原版讲义

- PDF 相对路径：`90-原始PDF/15-214/slides/14_Collections.pdf`
- 总页数：37 页
- 重点页码：
  - 第 1 页：封面（Fall 2013，"© 2012-13 C Garrod, J Aldrich, and W Scherlis"，含 toad 图片）
  - 第 2 页：考前通知——Midterm 10 月 15 日（下周二）课上；复习课周日 13:00–15:00 Hamburg Hall 1000；复习提纲与样题将发布
  - 第 3–4 页：上周要点回顾（GUI、MVC、Observer、Swing 架构与线程）
  - 第 5 页：已见模式清单（Composite、Observer、Template Method、Decorator、Strategy、MVC）
  - 第 6 页：本讲要点与将出现的模式（Iterator、Marker Interface、Factory Method、Adapter、Strategy、Decorator、Template Method）
  - 第 7 页：集合框架的哲学（强大而通用 / 小而轻；只含基础操作）
  - 第 8 页：`java.util.Collection<E>` 接口全方法
  - 第 9 页：`java.util.List<E>` 接口（顺序 + 索引）
  - 第 10 页：`java.util.Set<E>` 接口（唯一性）+ Marker Interface 旁注
  - 第 11 页：`java.util.Queue<E>` 接口（两套方法：抛异常 vs 返回特殊值）
  - 第 12 页：`java.util.Map<K,V>` 接口（不继承 `Collection`）
  - 第 13–14 页：数组与集合互转（`toArray` / `Arrays.asList`）+ Adapter 旁注
  - 第 15 页：「What do you want to do with your Collection today?」（过渡页）
  - 第 16 页：三种遍历方式（索引 for / for-each / Iterator）
  - 第 17 页：Iterator 模式（接口定义 + 用法）
  - 第 18 页：用 `Iterator.remove()` 删除元素
  - 第 19 页：**警告**——迭代期间用 `Collection.remove()` 会抛 `ConcurrentModificationException`
  - 第 20 页：Factory Method 旁注（`iterator()` 由实现决定创建哪个迭代器）
  - 第 21 页：两种排序方式（`Collections.sort` / 「滥用」`SortedSet`）
  - 第 22 页：`Comparable<T>` 接口与三条契约（三分返回、全序、与 `equals` 一致）
  - 第 23 页：`Integer.compareTo` 示例 + 「为什么不直接 `return val - o.val`」
  - 第 24–25 页：`Name` 实现 `Comparable`（提示「`String` 实现了 `Comparable<String>`」）
  - 第 26–27 页：多排序需求 → `Comparator<T>` 接口（Strategy 模式）
  - 第 28 页：`Employee` 的 `compareTo` 与 `EmpSalComp`（含 "Why is this OK?" 提问）
  - 第 29 页：用 `Comparator` 构造 `TreeSet`（自然序 vs 策略）
  - 第 30 页：`SortedSet<E>` 接口（`comparator()` 返回 `null` 表示自然序）
  - 第 31–32 页：`Collections` 工具类（算法清单、`sort` 与 `frequency` 示例）
  - 第 33 页：`Collections` 的 Decorator 用法（`unmodifiableXxx`、`synchronizedXxx`）
  - 第 34 页：`binarySearch` 的真实泛型签名逐层解读（`? extends Comparable<? super T>`）
  - 第 35 页：集合框架作为框架——可写自定义集合，JDK 算法会调用你的代码
  - 第 36 页：`AbstractList` 的方法三分类（`abstract` / Template Method / 伪抽象）
  - 第 37 页：下次为周二期中考试
- 原始网页链接：`https://www.cs.cmu.edu/~aldrich/214/slides/14_Collections.pdf`

> 待核实：本讲义的文件名以 `14_` 开头，而同一课程另有 `14-frameworks.pdf`（第 16 讲，Frameworks）——两个文件都以「14」为前缀，可能是课件编号与实际讲次的错位（`14_Collections.pdf` 按课表对应 10 月 10 日，`14-frameworks.pdf` 对应 10 月 22 日）。笔记按课表顺序编号（本讲为第 14 讲，Frameworks 为第 16 讲）。第 10 页 `Set` 接口处「Extends `java.util.Collection<E>`:」之后**未列任何方法**（与 Java 8 之前的实际 API 一致，应为刻意留白）。第 23 页的「Why did I not just return `val – o.val`?」与第 28 页的「Why is this OK?」两个提问，讲义**均未给出答案**；笔记中的溢出解释属补充推导。第 31–32 页代码写作 `public class Main()`（类名后带括号），是排版错误，应为 `public class Main`。

## 9. 对应视频

未找到官方公开录像。2013 年秋季的 15-214 课堂没有公开发布录像，故不提供链接与时间戳。

## 10. 本节复习

- 集合框架的哲学：**强大而通用** + **小而轻**（只含基础操作，其余放 `Collections` 工具类）。
- 接口层次：`Iterable` → `Collection` → `List`/`Set`/`Queue`；`Map` **独立**（不继承 `Collection`，因为有两个类型参数、核心是按 key 查找）。
- `List` = 顺序 + 索引；`Set` = 唯一性（接口**不新增方法**，是 Marker Interface）；`Queue` = 两套方法（抛异常 vs 返回特殊值）。
- `Map` 的三个视图：`keySet()`（`Set<K>`）、`values()`（`Collection<V>`，可重复）、`entrySet()`（`Set<Entry>`）。都是**活的视图**，不是拷贝。
- 数组 ↔ 集合：`toArray(new T[0])`（推荐，类型安全）与 `Arrays.asList`（Adapter，固定大小 + 别名）。
- 三种遍历：索引 for（只适合 `RandomAccess`）、for-each（通用）、Iterator（需删除时）。`LinkedList` 上用索引 for 是 O(n²)。
- `Iterator` 模式 = Indirection：把遍历与表示解耦。`iterator()` 是 **Factory Method**。
- `Iterator.remove()` 删「上次 `next()` 的元素」；用 `Collection.remove()` 会抛 `ConcurrentModificationException`（fail-fast，**单线程也抛**）。
- `Comparable` 三条契约：三分返回、全序（传递 + 反对称）、与 `equals` 一致（`compareTo == 0` iff `equals`）。
- **不要写 `return a - b`**：会溢出，符号反转，排序错误且静默。用 `Integer.compare`。
- `Comparator` = **Strategy 模式**：外部策略、可多种、不需修改元素类。`TreeSet(comparator)` 注入策略。
- `SortedSet.comparator()` 返回 `null` 表示使用自然序。
- `Collections` 工具类：算法（`sort`、`binarySearch`、`frequency`…）+ **Decorator** 工厂（`unmodifiableXxx`、`synchronizedXxx`）。
- `unmodifiableList` 是**不可变视图**而非不可变对象；`synchronizedList` 只保护单方法，复合操作仍需客户端加锁。
- `binarySearch` 的 `List<? extends Comparable<? super T>>`：`extends` 是生产者（元素类型协变），`super` 是消费者（`compareTo` 参数逆变）——PECS 原则。
- 集合框架本身是**框架**：你写集合，JDK 算法调用你（依赖反转 / 好莱坞法则）。
- `AbstractList` 三分类：`get`/`size` 真抽象（必须实现）；`iterator`/`toArray` 是 Template Method（可覆写优化）；`add`/`set`/`remove` 是**伪抽象**（默认抛 `UnsupportedOperationException`）。只写 2 个方法就得到十几个。

## 11. 自我检查

1. 为什么 `Map<K,V>` 不继承 `Collection<E>`？请从「方法签名」和「语义契约」两个角度说明，并解释 `values()` 为什么返回 `Collection<V>` 而不是 `Set<V>`。

2. 下面这段代码会抛什么异常？为什么？请给出两种正确写法，并说明 JDK 为什么选择「快速失败」而不是「允许在遍历中修改」。
   ```java
   List<String> names = new ArrayList<>(List.of("Alice", "Bob", "Charlie"));
   for (String s : names) {
       if (s.startsWith("C")) names.remove(s);
   }
   ```

3. 下面的 `compareTo` 有什么 bug？在什么输入下会出错？请修正。
   ```java
   public int compareTo(Money o) {
       return this.cents - o.cents;   // cents 是 int
   }
   ```

4. `Comparable` 的契约要求「`compareTo` 应与 `equals` 一致」，但 JDK 的 `BigDecimal` 违反了这个要求。请说明这会导致什么具体问题，以及为什么 `BigDecimal` 仍然这样设计。

5. 下面的类只写了两个方法，却拥有 `List` 的全部行为。请解释这是怎么做到的，并说明为什么 `add` 会抛 `UnsupportedOperationException`。
   ```java
   public final class Range extends AbstractList<Integer> {
       private final int lo, hi;
       public Range(int lo, int hi) { this.lo = lo; this.hi = hi; }
       @Override public Integer get(int i) { return lo + i; }
       @Override public int size() { return hi - lo; }
   }
   ```

<details>
<summary>参考答案</summary>

1. **从方法签名看**：`Collection<E>` 的所有方法都围绕**单个**类型参数 `E`——`add(E e)`、`contains(E e)`、`remove(E e)`。而 `Map<K,V>` 有**两个**类型参数，核心操作是 `put(K, V)` 与 `get(Object)`：参数类型是 `K`，返回类型是 `V`。如果硬让 `Map` 继承 `Collection`，`E` 只能取 `Map.Entry<K,V>`，于是 `add(Entry)`、`contains(Entry)` 都变成「按 entry 操作」，而**丢失了按 key 查找**这个最核心的能力（`get(key)` 无法从 `Collection` 的签名推出）。
   **从语义契约看**：继承要求**行为兼容**（里氏替换）——任何接受 `Collection` 的地方都应能接受 `Map`。但 `Collection` 的契约是「一堆元素，可以 `add`/`remove`/遍历」，而 `Map` 的契约是「key 到 value 的映射，key 唯一」。用 `Map` 替换 `Collection` 会破坏调用者的预期（比如 `add` 该加什么？`iterator()` 该遍历 key 还是 entry？）。所以「都是容器」**不构成**继承关系——这是第 3 讲「Is every Foo really a Bar?」的一个反例。
   **`values()` 返回 `Collection<V>` 而非 `Set<V>`**：因为多个 key 可以映射到**相同**的 value（例如 `{a→1, b→1}`），所以值的集合**可能重复**，不满足 `Set` 的唯一性契约。而 `keySet()` 返回 `Set<K>` 是正确的，因为 key 本身唯一。这是「Marker Interface 承载语义契约」的反向应用：**不该标 `Set` 的地方不能标**，否则调用者会错误地依赖唯一性。

2. **抛 `ConcurrentModificationException`。** 原因：for-each 循环被编译成 `Iterator` 循环，而循环体内用 `names.remove(s)` **绕过迭代器**直接修改了集合。`ArrayList` 的迭代器维护一个 `modCount` 快照，每次 `next()` 时检查集合的 `modCount` 是否变了；`remove` 会 `modCount++`，于是下一次 `next()` 检测到不一致，抛异常。注意：这是**单线程**代码，与并发无关——异常名的「Concurrent」是历史遗留的误导。
   **两种正确写法**：
   ```java
   // ① 用 Iterator.remove()
   for (Iterator<String> it = names.iterator(); it.hasNext(); ) {
       if (it.next().startsWith("C")) it.remove();
   }

   // ② removeIf（Java 8+）
   names.removeIf(s -> s.startsWith("C"));
   ```
   （第三种：先收集到临时列表再 `removeAll`。）
   **为什么选快速失败**：如果允许遍历中修改，迭代器的行为会**不可预测**——删掉当前元素后「下一个」是哪个？在 `ArrayList` 里是原来的下一个，在 `LinkedList` 里可能不同，在 `HashMap` 里可能因 rehash 而完全错乱。要定义一套对所有实现都一致的规则，代价极高且难以实现。所以 JDK 选择**直接禁止并立刻报错**：宁可崩溃，也不要静默产生错误结果。这与第 5 讲「运行时异常表示程序错误」一致——`ConcurrentModificationException` 是 `RuntimeException`，它在说「你的代码逻辑错了」。**注意**：Javadoc 明确说 fail-fast 只是 best-effort，不保证一定检测到，所以不能依赖它做正确性保证。

3. **bug：`int` 减法溢出。** `compareTo` 只需返回值的**符号**有意义，但 `this.cents - o.cents` 在差值超出 `int` 范围时会溢出，导致符号反转。
   **出错输入**：`this.cents = 2_000_000_000`、`o.cents = -2_000_000_000`。此时 `this > o`，正确应返回正数；但 `2_000_000_000 - (-2_000_000_000) = 4_000_000_000` 超出 `Integer.MAX_VALUE`（约 21.47 亿），溢出为 `-294967296`——**负数**。于是排序算法认为 `this < o`，顺序颠倒。这个 bug **静默**：不抛异常，只在极端数值下产生错误顺序，极难排查。
   **修正**：
   ```java
   public int compareTo(Money o) {
       return Integer.compare(this.cents, o.cents);   // 安全
   }
   ```
   或显式三分：
   ```java
   if (this.cents < o.cents) return -1;
   if (this.cents == o.cents) return 0;
   return 1;
   ```
   这正是讲义第 23 页 `Integer.compareTo` 用三个 `if` 而**不用**减法的原因。

4. **具体问题**：`TreeSet`/`TreeMap` 用 `compareTo`（或 `Comparator`）判等与定位，而 `HashSet`/`HashMap` 用 `equals`/`hashCode`。二者不一致时：
   - 同一个对象集合放进 `TreeSet` 与 `HashSet`，**大小可能不同**：`new BigDecimal("1.0")` 与 `new BigDecimal("1.00")` 在 `TreeSet` 里视为同一个（`compareTo == 0`），在 `HashSet` 里视为两个（`equals == false`）。
   - 更危险的是 `TreeMap.get(k)`：它用 `compareTo` 找 key。如果两个对象 `equals` 为 true 但 `compareTo != 0`，那么 `map.put(k1, v)` 之后 `map.get(k2)`（其中 `k2.equals(k1)`）会**返回 null**——看起来像「数据丢了」。
   - 反过来，如果 `compareTo == 0` 但 `equals == false`，`TreeMap` 会把两个「不同」的 key 当成同一个，后者覆盖前者。
   **为什么 `BigDecimal` 仍这样设计**：因为「数值相等」与「表示相等」是两个不同的概念。`1.0` 与 `1.00` 有**不同的精度（scale）**，这在金融计算里是有意义的区别（`1.0` 精确到十分位，`1.00` 精确到百分位，`divide` 时的舍入行为不同）。所以 `equals` 比较「值 + 精度」，而 `compareTo` 只比较「数值」。Javadoc 明确警告了这个不一致，建议「用 `TreeMap` 时注意，或用 `Comparator` 显式定义顺序」。
   **实践建议**：自定义 `Comparable` 时，**务必**让 `compareTo == 0` 与 `equals == true` 等价。若业务上需要「按某字段排序但按全部字段判等」，就用 `Comparator` 而不是 `Comparable`——`Comparator` 没有「与 `equals` 一致」的要求。

5. **这是 `AbstractList` 骨架类的 Template Method 设计。** `Range` 只实现了两个**真抽象**方法：
   - `get(int i)`：返回第 i 个元素（`lo + i`）；
   - `size()`：返回元素个数（`hi - lo`）。
   `AbstractList` 用这两个方法**实现了其余全部方法**：
   - `iterator()` → 内部用 `get(0)`、`get(1)`… 逐个产出（Template Method，子类可覆写优化）；
   - `contains(o)` → 用 `iterator()` 逐个比 `equals`；
   - `indexOf(o)` → 同上，返回下标；
   - `toArray()` → 用 `size()` 建数组，用 `get(i)` 填充；
   - `toString()` → 用 `iterator()` 拼接；
   - `equals`/`hashCode` → 按 `List` 契约用 `iterator()` 实现；
   - `subList` → 返回一个视图。
   所以 `Range(0, 5)` 立刻拥有 `[0,1,2,3,4]` 的全部 `List` 行为，包括 `System.out.println` 能打印、`Collections.reverse` 能调用（但会失败，见下）。
   **为什么 `add` 抛 `UnsupportedOperationException`**：`AbstractList` 对 `add`/`set`/`remove` 提供的是**伪抽象方法**——它们**有方法体**，但方法体就是 `throw new UnsupportedOperationException()`。`Range` 没有覆写它们，所以继承到这个默认实现。
   这样设计的理由（5.19 节）：如果声明为 `abstract`，那么**所有**子类都必须实现，包括只读列表（它们根本不支持 `add`）；如果声明为普通空方法，子类忘记覆写时会**静默无效**。折中方案是「默认抛异常」——让「不支持」成为一个**显式的、运行时可检测的**状态。所以 `Range` 天然是一个**只读列表**，`Collections.reverse(range)` 会在第一次 `set` 时抛 `UnsupportedOperationException`。
   这也解释了 `Collections.unmodifiableList` 的实现方式：它返回一个 `AbstractList` 子类，`get`/`size` 转发给底层，`add`/`set`/`remove` **不覆写**——于是自动获得「抛异常」的只读行为。**同一个机制，两种用途。**

</details>

## 12. 进一步学习

- 上一讲：[[15-214-13-GUIs-Continued]]
- 下一讲：[[15-214-15-Formal-Analysis]]（注：按 2013 年课表，10 月 15 日为 Midterm，10 月 17 日为 Formal Analysis）
- 课程总览：[[30-CMU-15-214/00-课程总览|CMU 15-214 - 课程总览]]
- 课程目录：[[30-CMU-15-214/01-课程目录|CMU 15-214 - 课程目录]]
- 术语：[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]
- 延伸：Joshua Bloch, *Effective Java*（第 2 版）第 2 章「Methods Common to All Objects」——`equals`/`hashCode`/`compareTo` 契约的权威讨论，与本讲第 22 页和 [[15-214-04-Inheritance-Typechecking-Dispatch]] 直接相关；同书第 4 章「Generics」讲 PECS 原则（`? extends` / `? super`），可对照本讲第 34 页的 `binarySearch` 签名；JDK 源码中 `java.util.AbstractList`、`java.util.ArrayList.Itr`、`java.util.Collections.UnmodifiableList` 三处是理解「骨架类 + 伪抽象 + Decorator」的最佳读物；`java.util` 包的 Javadoc 开头的「Collections Framework Overview」有完整的接口层次图与实现类对照表（含复杂度）。
