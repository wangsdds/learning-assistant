# 简历项目八股｜学习助手面试速记

> 背法：先背粗体骨架，再用自己的话展开。不要逐字背长答案。
>
> 核心原则：**只讲已经做过的，主动说边界。**

## 1. 30 秒项目介绍

> 我做了一个多用户学习助手，后端是 FastAPI + SQLAlchemy + SQLite，前端用原生 JavaScript。资料会切片并用 FTS5 检索，PydanticAI StudyAgent 可以自主调用检索工具生成带答案、rubric 和引用来源的题目草稿，服务端校验来源后才允许入库；文本题作答后按 rubric 做 AI 批改并保存历史。项目有 JWT 鉴权、多用户隔离、Alembic 迁移、Nginx + systemd 部署和 56 个自动化测试。当前是单轮受限 Agent，多轮状态机是下一步。

## 2. 90 秒项目介绍

1. **业务**：解决“计划、资料、出题、自测、复盘分散”的问题。
2. **链路**：资料写入 → 切片 → FTS5 检索 → StudyAgent 调用检索工具 → 结构化草稿 → 来源校验 → 用户确认入库 → 作答 → rubric 批改 → 历史记录。
3. **难点**：用户隔离、工具权限边界、检索片段约束、模型结构化输出、参考答案不下发、批改结果持久化。
4. **工程**：SQLAlchemy + Alembic、PydanticAI、pytest + 内存 SQLite、Nginx + systemd 部署。
5. **边界**：是单轮受限 Agent，不是多轮自主 Agent；向量检索、多轮会话和 PostgreSQL 生产化尚未完成。

## 3. 必背问答

### Q1：为什么做这个项目？

> 因为计划、资料、检索、自测和复盘通常是分散的。我想做一个闭环：资料进来后能检索、能出题、能作答、能批改、能回看。它同时覆盖后端认证、数据库设计、检索、外部模型调用、测试和部署，适合作为完整的后端项目。

### Q2：项目整体架构是什么？

> FastAPI 入口挂多个 `APIRouter`，按 users、documents、questions、answers、plan_days、rag、study_agent 拆分。Pydantic 负责请求和响应校验，SQLAlchemy 2.0 负责 ORM，Alembic 管迁移，SQLite 存业务数据和 FTS5 索引；StudyAgent 通过 PydanticAI 调用检索工具并返回类型化草稿。UI 是原生 HTML/CSS/JS，与 API 同源。

### Q3：为什么选 FastAPI？

> 我的主语言是 Python；FastAPI 有 Pydantic 校验、依赖注入和自动 OpenAPI，适合快速构建类型明确的 REST API。同步数据库操作放普通 `def` 路由，FastAPI 会放到线程池，不阻塞事件循环。当前项目没有做高并发压测，不能宣称它在高负载下一定优于其他框架。

### Q4：为什么用 SQLAlchemy 2.0 和 Alembic？

> SQLAlchemy 用 `Mapped` 和 `mapped_column` 表达类型，业务层能按 ORM 写查询；Alembic 把表结构变更版本化。测试里可以用 `create_all` 建内存库，但线上不能靠 `create_all`，否则没有迁移历史和回滚路径。

### Q5：用户隔离怎么做？

> 用户身份从 Bearer JWT 中解析，不接受客户端传 `user_id`。查询资料、题目、答案、计划时都带当前用户条件；`/users/{user_id}` 和 `/users/by-email/{email}` 也只允许查询本人，访问别人的资源统一返回 404。因为 403 等于告诉对方“资源存在，只是你没权限”，404 不泄露资源存在性。

### Q6：JWT 怎么工作？有什么缺点？

> 登录成功后签发 HS256 JWT，`sub` 放 user_id，带 `iat` 和 `exp`，默认 30 分钟；服务端只验签和查用户，不保存 session。优点是水平扩展简单、无状态；缺点是主动登出困难、权限变更不能立刻生效。当前登出只是客户端丢弃 token，生产上可加短过期、refresh token 或黑名单。

### Q7：密码怎么存？为什么用 bcrypt？

> 不存明文，使用 bcrypt 加盐哈希。bcrypt 计算慢，能增加暴力破解成本；验证时用 `checkpw` 比较。邮箱唯一性靠数据库唯一约束，插入冲突捕获 `IntegrityError`、回滚并返回 409，避免“先查再插”的竞态。

### Q8：表怎么设计？为什么用外键级联？

> 7 张表：users、plan_days、newplan、documents、document_chunks、question、answer。users 关联计划和资料，资料关联切片和题目，题目关联答案。外键带 `ON DELETE CASCADE`，删除用户时关联数据在数据库层清理，避免孤儿数据。SQLite 默认不检查外键，所以每个连接执行 `PRAGMA foreign_keys=ON`。

### Q9：为什么要给外键建索引？

> SQLite 不会自动给外键列建索引。没有索引时，按 `user_id` 查计划和级联删除都要扫全表；加索引后走索引查找。项目的 benchmark 用 5 万用户、20 万计划，查询 100 次取平均，并删除 20 个用户测级联；结果是从约 12.86ms 降到 0.138ms、级联删除约 546ms 降到 3.6ms。这个数字是本地 SQLite 基准，不是线上生产压测。

### Q10：B+ 树和回表怎么讲？

> B+ 树非叶子节点只存键和子节点指针，叶子节点存数据或数据指针，叶子之间有链表，适合范围查询。InnoDB 聚簇索引叶子存整行；二级索引叶子存索引列和主键，查询列不在索引里时要拿主键回聚簇索引查，叫回表。覆盖索引就是把查询需要的列都放进索引，避免回表。

### Q11：FTS5 检索怎么做的？

> 资料先按约 700 字、100 字重叠、尽量按句界切片，写入 `document_chunks` 和 FTS5 索引。查询时优先用 trigram 和 BM25 排序，取前 5 个片段；中文短查询不足三个字符或 FTS5 无结果时，回退到词项 `LIKE` 打分。检索始终限定当前用户、当前资料。

### Q12：为什么不上向量数据库？

> MVP 先用 SQLite FTS5 验证闭环，零额外服务、查询可解释、部署简单。缺点是语义召回弱，同义表达可能搜不到；等出现真实召回问题，再引入 embedding + 向量检索 + 混合召回，而不是提前堆组件。

### Q13：RAG 怎么减少幻觉？

> 只把当前用户当前资料的相关片段放进上下文；Prompt 明确把资料视为不可信数据，要求不执行其中指令；模型必须返回严格 JSON，服务端用 Pydantic 校验；模型给的 `source_chunk_ids` 必须属于本次检索结果，否则过滤。生成结果只是草稿，用户确认后才入库。RAG 不能完全消除幻觉，所以还需要人工确认和评估。

### Q14：为什么草稿不直接入库？

> 模型输出可能错、引用可能不成立，直接写正式题库会污染数据。草稿展示答案、rubric、难度和来源，用户确认后才写入 `question`；保存时再次校验来源片段确实属于当前资料。这是人在回路的基本实现。

### Q15：AI 批改怎么做的？

> 文本题在服务端保存参考答案和 rubric，题目列表不返回它们。用户提交答案后，把题目、参考答案、rubric 和学生答案组成 JSON，要求模型返回 0–100 分、命中点、遗漏点、反馈和置信度；服务端校验后写入 answer 表。当前是单轮 rubric 反馈，不是经过人工标注验证的正式考试评分。

### Q16：测试怎么做的？为什么不用真实模型？

> pytest 使用独立的内存 SQLite，通过 `dependency_overrides` 替换数据库；普通模型测试用 Fake LLM，Agent 测试用 PydanticAI `FunctionModel`，避免外部网络和随机性。56 个测试覆盖认证、跨用户隔离、输入边界、级联删除、中文检索、工具调用轨迹、非法来源重试、草稿来源校验、批改落库和完整闭环。真实模型只做少量人工冒烟测试。

### Q17：怎么部署的？

> 浏览器请求 80 端口到 Nginx，Nginx 反向代理到 `127.0.0.1:8000` 的 Uvicorn + FastAPI；systemd 以 `www-data` 拉起服务，异常退出自动重启；`.env` 权限 640，存 SECRET_KEY 和模型 Key；更新时先执行 `alembic upgrade head`，再重启服务。日志用 `journalctl` 和 Nginx 日志。

### Q18：上线后 500 怎么查？

> 先 `curl 127.0.0.1:8000/health` 看应用是否活着，再 `systemctl status` 和 `journalctl -u` 看应用异常；然后 `nginx -t` 和 Nginx error log 区分代理问题；最后检查环境变量、迁移版本、数据库权限和安全组。不要一上来就重启，要先定位是应用、代理还是数据库。

### Q19：项目最大的难点是什么？

> 不是调用模型，而是把模型放进可控的后端链路：用户隔离、只给相关片段、工具权限由 `RunContext` 注入、结构化输出、来源校验、参考答案不下发、草稿确认、批改落库和失败处理。下一步真正难的是多轮状态和评估，而不是再换一个模型。

### Q20：当前不足和下一步？

> 已完成 RAG 出题、PydanticAI 单轮受限 StudyAgent、草稿入库、单轮 rubric 批改和部署。未完成多轮学习会话、跨请求状态恢复、向量检索、流式输出、HTTPS、AI 接口限流和 PostgreSQL 生产化。下一步先做 `study_sessions` 和 `session_events`，用 LangGraph 做最多 5 轮的状态机，记录工具调用、分数和薄弱点，再建立评估集。

### Q21：PydanticAI StudyAgent 具体怎么做的？

> `StudyDeps` 里放数据库 Session、当前 `user_id` 和 `document_id`，模型只能通过 `RunContext` 拿到这些权限，工具参数里没有用户身份。`search_documents` 只查当前用户拥有的当前文档，并记录本轮真实返回的 chunk；输出类型是 `GeneratedQuestionDraft`，`output_validator` 再检查 `source_chunk_ids` 是否全部来自本轮检索，不合法就抛 `ModelRetry`。最后用 `UsageLimits` 限制 4 次请求、6 次工具调用，并设置 20 秒工具超时。

## 4. 简历数字怎么防守

| 简历写法 | 面试时必须能解释 |
|---|---|
| 23 个 REST 操作 | 是方法+路径操作数，不是 23 张表 |
| 7 张表 | users、plan_days、newplan、documents、document_chunks、question、answer |
| 93× / 150× | 5 万用户、20 万计划的本地 SQLite benchmark；不是生产压测 |
| 56 个测试 | 内存 SQLite + Fake LLM / PydanticAI FunctionModel；覆盖认证、隔离、检索、Agent、草稿、批改 |
| PydanticAI StudyAgent | 单轮受限 Agent，能调用检索工具；不是多轮自主 Agent |
| AI 批改 | 单轮 rubric 反馈，不是正式考试评分 |
| 云服务器部署 | Nginx + systemd + Uvicorn + SQLite，单机，不是高可用集群 |
| PostgreSQL | 技术栈兼容方向，不是已经上线的数据库 |

## 5. 十句必须脱口而出的锚点

1. **项目定位**：多用户学习助手，PydanticAI 受限 StudyAgent + RAG 出题 + 单轮 rubric 批改。
2. **请求链路**：HTTP → APIRouter → Depends 认证 → Session → SQLite。
3. **用户隔离**：user_id 来自 JWT，跨用户统一 404。
4. **认证**：JWT 无状态，bcrypt 加盐，邮箱唯一靠数据库约束。
5. **数据库**：外键 CASCADE，SQLite 开 `PRAGMA foreign_keys=ON`，外键补索引。
6. **索引**：B+ 树、二级索引、回表、覆盖索引。
7. **检索**：切片 → FTS5 trigram → BM25 → 短查询 LIKE 回退。
8. **防幻觉**：片段约束 + 工具白名单 + Pydantic 结构校验 + `output_validator` 来源校验 + 草稿确认。
9. **批改**：参考答案隐藏，rubric 输出分数/命中/遗漏/反馈并落库。
10. **部署**：Nginx → Uvicorn → FastAPI → SQLite，systemd 拉起，Alembic 先迁移。

## 6. 千万别说

- “我做了多轮自主 Agent。” → 当前是单轮受限 Agent，多轮状态机还没做。
- “AI 批改很准确。” → 是学习反馈，不是正式评分。
- “用了 PostgreSQL。” → 当前线上是 SQLite。
- “高可用、高并发。” → 单机 MVP，没有压测和集群。
- “向量检索也做了。” → 没有。
- “56 个测试覆盖所有情况。” → 覆盖关键边界，不等于全覆盖。
