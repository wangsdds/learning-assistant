# 批改：`docs/schema.sql` 第一版（2026-10-15 22:10）

> 工具已升级：`tools\run_schema.py` 现在**一次列出全部问题**（以前只报第一个），
> 而且能查出「# 不是 SQL 注释」「漏分号」这两类。跑它就能看到下面第一组的全部 18 条。

## 先记住一件事：你终于把 6 张表**画全了**

`users` / `plan_days` / `newplan`（条目）/ `documents` / `question` / `answer`

而且三处关键的都对了：
- 一对多拆对了（计划 + 条目两张表）
- 条目表的外键指向计划的**主键**（`plan_days(plan_id)`）✅
- 资料表跟用户的关联回来了 ✅
- 每个关系都用外键写出来了 —— **这一步是你今天最大的进步**：从散文到结构，含糊的地方被逼出来了

## 第一组：脚本会报的 18 个（机械错误）

| 类别 | 数量 | 说明 |
|---|---|---|
| `###` 开头的行 | 6 | 不是 SQL 注释。SQL 的注释是 `--`。整行前面加 `--`，或者直接删掉 |
| 语句结尾漏 `;` | 6 | 每条语句结尾都要有分号，否则整段文件执行不了 |
| `REFRENCES` 拼错 | 5 | 正确写法 `REFERENCES`。实测报 `near "REFRENCES": syntax error` |
| 列定义后面多余的逗号 | 6 | 最后一个列定义后面紧跟 `)`，那个逗号要删。实测报 `near ")": syntax error` |
| 外键指向的表名写错 | 1 | 你写 `REFRENCES docments(id)`，但表建出来叫 `documents`。实测建表能过（SQLite 建表时不管目标存不存在），**插入时才炸**：`no such table: main.docments` |

**这 18 条跑一次 `run_schema.py` 就能全看到**，别自己肉眼找。

## 第二组：脚本查不出来的（语义，这几条只能靠你想）

### 1. 题目表里没有题干，却有一个 `answer_time`

```sql
CREATE TABLE question(
    doc_id      INTEGER not null,
    id          INTEGER PRIMARY KEY,
    answer_time not null,        -- 这个不属于这里
    Foreign key(doc_id) REFRENCES docments(id),
)
```

题目表存在的理由就是存**题干**。现在它只有「属于哪份资料」和一个不该在这的答题时间。

`answer_time` 绑的是**一次作答** —— 同一道题答 3 次，题目行只有一行，时间只会剩最后一次。

### 2. 标准答案还在答题表里（第四轮了）

```sql
system_answer INTEGER not null,   -- 标准答案
```

它跟「题目」是一对一：一道题一个标准答案，答 10 次不该存 10 遍。
另外：标准答案一般是**文字**，写 `INTEGER` 的话「因为扇出大」这答案存不进去。

### 3. 「文件」和「网址」两列都 `NOT NULL` → 只登记网址就存不进去

实测：

```
只给网址（文件那列写 NULL）
-> IntegrityError: NOT NULL constraint failed: documents.docments
```

现实里一份资料要么是文件、要么是网址。两列都强制非空，就只能往空的那列塞个假值（空字符串）—— 这就是「假数据从哪来的」的起点。

想清楚：**这两列是「二选一」还是一份资料可以两者都有？** 二选一的话，靠 `NOT NULL` 是表达不出来的。

### 4. 所有外键都没写 `ON DELETE CASCADE`

现在删一个用户：他的计划、条目、资料、题目、答题记录**全部变成孤儿**（实测过：`materials=1 questions=1 answers=1` 还在）。

这是你硬约束里那条「删掉一个用户时，他的数据应该跟着消失」。

### 5. 唯一约束还没落到位

- `documents`：同一个用户不该有两份同名资料 → `(user_id, namedoc)`
- `plan_days`：某一天一条计划 → `(user_id, add_date)`

## 顺带一条小知识

**不写类型不会报错**。实测 `password NOT NULL` 能建出来，`NOT NULL` 也照样生效 —— 但这一列的类型是空的（没有类型亲和性）。
所以 `password` / `add_date` / `answer_time` / `user_answer` / `scores` 这五列虽然不报错，还是补上类型（基本都是 `TEXT`）。

**不报错 ≠ 对。** 这是本课最该带走的一句话。
## 更正（2026-10-18 21:05）· 「漏分号 6 条」是我脚本的误报
`split_statements()` 在切语句时把**下一张表前面的注释行**也算进了上一条语句的文本，
于是「文本是否以分号结尾」永远为 False —— 6 条语句全被判成漏分号。用户的 6 个分号其实都在。
同一天还修了第二处：`check_semicolons()` 拿到的是已经剥掉分号的文本（`text[:-1]`），
所以它连「有分号的语句」也照样报。两处都已改：
- `split_statements()` 现在返回 `(起始行号, 语句文本, 是否以分号结尾)`，末尾空行/`--` 注释行不计入；
- `check_semicolons()` 改用第三个字段判断。
教训：**批改工具自己也要被校验** —— 误报比漏报更伤，因为用户会去改本来对的东西。

## 21:05 实测：6 条语句全部失败，真实原因（按行号）
1. `users` 18 行：`password NOT NULL,` 是最后一列却带逗号 ⇒ `)` 前多逗号；且 `password` **没写类型**。
2. `plan_days` 22 行：`on delete cascade` 写在**列定义**里（CASCADE 是外键的动作，不是列属性）；
   26 行 `REFRENCES` 拼错 + 该行末尾多逗号。
3. `newplan` 30 行：同样的 CASCADE 位置错；33 行 `REFRENCES` + 尾随逗号。
4. `documents` 41 行：同样的 CASCADE 位置错；42 行 `REFRENCES` + 尾随逗号。
5. `question` 48 行 `answer_time` 缺类型；50 行 `REFRENCES` + 外键目标表名拼成 `docments`（应为 `documents`）；
   50 行末尾尾随逗号。
6. `answer` 54 行：同样的 CASCADE 位置错；59 行 `scores` 缺类型；60 行 `REFRENCES`。
⇒ 这一轮暴露的是**同一类错误的 4 次复制**（CASCADE 当列属性）+ 拼写 + 分隔符语义（逗号是分隔符不是结束符）。
⇒ 脚本每条语句只报第一个错，所以改完第一个错会冒新的 —— 这是正常的迭代方式，别当成"越改越错"。
## 21:08 第二轮：改对 5 类，剩 2 类机械问题（各 6 次）
改对的：① CASCADE 挪进 FOREIGN KEY 子句（4 处 + question 也加了）② `REFERENCES` 拼写全对 ③ 外键目标表名 `docments`→`documents`
④ 缺类型补齐（`password text` / `answer_time text` / `scores text`）⑤ **标准答案已挪进 `question.system_answer`，答题表只剩用户答案+耗时+成绩**。
剩下的机械问题：
- 6 条语句结尾都**没有分号**（19、27、34、43、51、61 行）—— 上一轮我误报"漏分号"之后他把分号删了，现在是真的没有了。
- 6 处**最后一个约束后面多了逗号**（18、26、33、42、50、60 行）→ `)` 前不能有逗号。
其他：`calender` 拼成 `calendar` 才对（不报错，但以后写 SQLAlchemy/Pydantic 会难受）。
语义上还欠 3 条决策（题干、`documents` 双 NOT NULL、唯一约束组合），文件顶部仍没有 `-- 决策` 段。