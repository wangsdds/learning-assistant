# 0007 · 行为验收（第一轮）

2026-10-18 21:15。`docs/schema.sql` 已能跑通（6 条语句 / 6 张表 / 0 语法问题），
`tools/run_schema.py` 全部通过。这一轮换一个问法：**不看语法，直接插数据看它能不能用。**

工具：`tools/check_behavior.py`（读你的 schema.sql，建内存库，跑 8 个真实场景）。

## 结果：PASS 3 / FAIL 3 / 待决定 2

| 结果 | 场景 | 说明 |
|---|---|---|
| PASS | 重复邮箱 | UNIQUE constraint failed: users.email —— 拦住了 |
| PASS | 两人同名昵称 | 允许。昵称本来就不该唯一 |
| PASS | 删用户级联 | 删掉用户后 users / plan_days / newplan / documents / question / answer **六张表全部清零** |
| FAIL | 资料只填一半 | docments 与 websites 都 NOT NULL ⇒ 只登记网址、只登记文件，**都存不进去** |
| FAIL | 题目表没有题干位 | 只有 doc_id / answer_time / system_answer —— **没地方放题目本身** |
| FAIL | 答题记录没有 owner 列 | answer 只有 que_id，谁答的靠 question→documents→users 三跳；**用户 B 答 A 的题，记录会算到 A 名下** |
| 待决定 | 同一天两条计划 | 现在允许；一天只该有一条就得加 UNIQUE(user_id, add_date) |
| 待决定 | 同一题答两次 | 现在允许，但 answer 没有作答时间列 ⇒ 分不清哪次是最新 |

## 这三点为什么脚本查不出来
`run_schema.py` 只回答「语法对不对、结构长什么样」。
「这道题问的是什么」「一份资料是不是必须两种形式都有」这类问题，语法层面完全合法，
**只有把数据真插进去才会露馅**。→ 以后每改完一版 schema，两个脚本都要跑。

## 下一轮要落地的决策（按影响排序）
1. **题干**：question 表加一列存题目文本。
2. **answer_time 的位置**：题目没有「答题时间」，答题才有 —— 它属于 answer。
3. **资料半填**：两列改成可空，再加一条「至少填一个」的约束（SQLite 里叫 CHECK）。
   注意：NOT NULL 只能管一列，管不了「两列里至少一列」。
4. **answer 的 owner**：要不要加 user_id？资料私有 ⇒ 可以不加，但要接受「谁答的」要三跳查询；
   多人共用同一份资料 ⇒ 必须加。
5. **两个唯一性**：`(user_id, add_date)`、`(user_id, documents_name)` 要不要唯一。
   写成 `UNIQUE(a, b)` 是**组合唯一**，不是两列各自唯一。
## 21:53 · 两个待决定的结论（用户回答：都能）
1. **同一用户同一天可以有两条计划** ⇒ 不加 `UNIQUE(user_id, add_date)`。理由：计划可能上午/下午各一份，日期粒度不够。
2. **同一道题可以答多次** ⇒ 不加组合唯一；`answer` 已经有 `answer_time`，多次作答分得清。
⇒ 这一版 schema 就定稿：`run_schema.py` 全部通过（6 语句 / 6 表）、`check_behavior.py` PASS 6 / FAIL 0 / 待决定 2（两条都已决定，实际为全清）。
⇒ 没有动用户的 `schema.sql`（他可能正开着编辑器，避免覆盖未保存内容）；决策记在这里。