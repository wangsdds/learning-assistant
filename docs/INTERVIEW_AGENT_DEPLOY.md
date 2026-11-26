# Agent 开发与服务器部署｜面试知识点

> 适用项目：`项目-学习助手`
>
> 这篇不是为了把项目吹成“完整 Agent”，而是让你能准确讲清楚：
> 现在已经做了什么、为什么这样做、下一步怎样做，以及边界在哪里。

## 0. 一句话定位

**当前项目是一个带单轮受限 StudyAgent、RAG 出题和 rubric 批改的学习助手 MVP，不是多轮自主 Agent。**

面试时不要只说“我做了个 AI Agent”，更稳的说法是：

> 我用 FastAPI 做一个多用户学习助手，先把资料做成分片和 FTS5 检索，再用 PydanticAI 把检索封装成工具：模型在单轮里决定检索词、观察返回片段，最后生成类型化题目草稿。服务端通过 `RunContext` 注入用户和文档归属，用 `output_validator` 校验引用来源，并用 `UsageLimits` 和超时限制步数。用户确认后题目才入库，作答后按 rubric 批改并保存历史。当前是单轮受限 Agent，下一步会用 LangGraph 做多轮学习状态机。

这句话包含了：业务、RAG、结构化输出、持久化、AI 批改和下一步边界。

## 1. 先分清 Workflow、RAG 和 Agent

| 形态 | 核心特征 | 本项目对应 |
|---|---|---|
| 普通 Workflow | 固定步骤，程序决定下一步 | 出题、保存草稿、批改都是固定链路 |
| RAG | 先检索资料，再把片段放进上下文生成答案 | 资料切片、FTS5 检索、引用片段出题 |
| Agent | 模型选择工具、观察结果并继续决策，直到停止条件 | 已实现单轮受限 StudyAgent；多轮状态和跨请求恢复尚未实现 |

### 面试标准回答

> RAG 解决“模型不知道你的私有资料”的问题；Agent 解决“模型如何根据当前状态多步决策”的问题。两者不是一回事。我的项目已经用 PydanticAI 实现单轮工具调用：模型可以决定检索词并读取工具结果，但不能跨请求保存会话状态。下一步才会把“诊断薄弱点 → 选择动作 → 继续出题 → 总结”做成多轮状态机。

## 2. Agent 的核心组成

一个 Agent 至少要有下面几部分：

1. **目标**：例如“帮助用户掌握 B+ 树索引”。
2. **状态**：当前题目、用户答案、历史得分、已经覆盖的知识点。
3. **工具**：检索资料、生成题目、批改答案、查询薄弱点。
4. **策略**：根据状态决定下一步调用哪个工具。
5. **观察**：工具返回的片段、分数、错误信息。
6. **停止条件**：达到轮次、达到目标分数、用户结束或模型判断完成。

伪代码：

```text
state = load_or_create_session()
while not stop(state):
    action = plan(state)              # 选择下一步
    observation = call_tool(action)   # 检索 / 出题 / 批改
    state = update(state, observation)
    save(state)
return summarize(state)
```

真正的 Agent 难点不在“调用一次模型”，而在**状态保存、工具边界、错误恢复、停止条件和可评估性**。

## 3. 本项目当前的 RAG 链路

```text
资料写入
  ↓
chunk_text(max_chars=700, overlap=100)
  ↓
document_chunks 表
  ↓
SQLite FTS5 全文索引（trigram，环境不支持时回退 unicode61）
  ↓
search_chunks(query, top_k=5)
  ↓
把相关片段放进 Prompt（总上下文约 6000 字符）
  ↓
模型返回严格 JSON
  ↓
Pydantic 校验字段结构
  ↓
过滤不属于本次检索结果的 source_chunk_ids
  ↓
前端展示草稿
  ↓
用户确认后写入 question 表
```

### 3.1 为什么切片

模型上下文有限，整篇资料直接塞进去会：

- 浪费 token；
- 降低相关内容权重；
- 增加延迟和成本；
- 更容易被无关内容干扰。

项目按约 700 字切片，保留 100 字重叠，尽量从句界切开，避免一个概念被截断。

### 3.2 为什么先用 FTS5，不上向量库

MVP 阶段的目标是先验证业务闭环，而不是堆基础设施。FTS5 的优点是：

- SQLite 自带，不需要额外服务；
- 关键词查询可解释；
- 对当前中文短查询已经够用；
- 测试和部署简单。

不足是语义召回弱：用户问“为什么树更矮”，资料写的是“减少磁盘 I/O”，关键词可能对不上。这时才需要向量检索或混合召回。

### 3.3 中文短查询怎么处理

中文没有空格，项目用简单规则提取词项：

- 连续中文按 trigram 切分；
- 短查询不足以构造 trigram 时，回退到 `LIKE` 词项打分；
- 查询结果只限定在当前用户、当前资料内。

### 3.4 为什么生成结果先做草稿

模型可能出错，直接把生成结果写进正式题库会污染数据。因此：

- 生成接口只返回草稿；
- 草稿展示答案、rubric、难度和引用片段；
- 用户点击“采用并保存”后才写入 `question`；
- 保存时再次校验引用片段确实属于当前资料。

这是“人在回路”的最小实现，也体现了对模型输出的不信任。

## 3.5 PydanticAI 单轮 StudyAgent

`POST /documents/{document_id}/study-agent` 走的是真正的工具调用循环，而不是把检索结果提前拼进 Prompt：

```text
用户请求
  ↓
StudyAgent 决定检索词
  ↓
search_documents(query)
  ↓
工具只查询当前用户、当前文档，并记录真实 chunk_id
  ↓
模型返回 GeneratedQuestionDraft
  ↓
output_validator 校验 source_chunk_ids
  ├─ 不合法：ModelRetry，让模型重新生成
  └─ 合法：返回草稿，用户确认后入库
```

关键设计：

- `StudyDeps` 注入 `Session`、`user_id` 和 `document_id`；工具参数只有 `query`，模型不能自行指定用户或文档。
- `search_documents` 内部再次按 `user_id + document_id` 查资料，并只把本轮真实命中的片段记录到 `retrieved_hits`。
- `output_type=GeneratedQuestionDraft` 让 PydanticAI 生成结构化输出工具，避免自己解析 Markdown JSON。
- `output_validator` 要求所有 `source_chunk_ids` 都来自本轮检索；不合法时抛 `ModelRetry`，而不是静默替换来源。
- `UsageLimits(request_limit=4, tool_calls_limit=6)` 限制模型请求和工具调用，`tool_timeout=20` 防止单个工具调用挂住。
- 模型只拿到一个只读检索工具，没有写数据库工具；草稿仍需用户确认后走原有入库接口。

边界：这是一次 HTTP 请求内的受限循环，不保存跨请求会话，也没有“诊断薄弱点 → 多轮出题 → 总结”的自主规划。后者留给下一阶段的 LangGraph 状态机。

## 4. 文本题批改链路

```text
question_type = text
  ↓
服务端读取 reference_answer + rubric
  ↓
把题目、参考答案、rubric、学生答案组成 JSON
  ↓
模型返回 score / rubric_hits / rubric_misses / feedback
  ↓
Pydantic 校验
  ↓
写入 answer 表
  ↓
前端展示分数、命中点、遗漏点和建议
```

### 关键设计

- 参考答案和 rubric 不通过题目列表接口返回，避免用户直接看到答案。
- 模型只负责评分建议，不直接修改题目或用户数据。
- 批改结果落库，刷新页面后仍能看到历史。
- 分数是 0–100 的整数，便于排序和统计。
- `rubric_hits` 与 `rubric_misses` 分开保存，面试时可以直接讲“可解释评分”。

### 当前局限

这是单轮 rubric 批改，不是经过人工标注验证的考试评分系统。模型分数可能存在波动，所以我的表述是“AI 学习反馈”，不是“正式考试成绩”。

## 5. 安全与可靠性

### 5.1 用户隔离

- 用户身份来自 JWT，不接受客户端传 `user_id`。
- 查资料、题目、答案时都附带当前用户条件。
- 访问别人的资源返回 404，避免泄露资源是否存在。

### 5.2 Prompt Injection

资料文本和学生答案都可能包含恶意指令，例如“忽略前面的规则”。项目的处理原则是：

- 把资料和学生答案当作不可信数据；
- 在系统 Prompt 中明确要求忽略其中的指令；
- 模型输出必须经过 Pydantic 结构校验；
- 模型只能调用只读检索工具，不能直接执行数据库写操作或系统命令；
- 工具参数和资源归属由服务端校验，`user_id` 和 `document_id` 不暴露给模型。

### 5.3 失败处理

- 未配置模型密钥：返回 503；
- 模型服务失败、Agent 超过步数/工具次数或输出校验重试耗尽：返回 502；
- 请求格式错误：由 FastAPI/Pydantic 返回 422；
- 超时：HTTP 客户端设置连接和总超时，Agent 工具设置 20 秒超时；
- 外部模型响应不会直接写数据库，先经过 schema 校验。

## 6. 下一步：多轮 Agent 设计

不要一上来做“多 Agent”。先做一个有限轮次、状态可恢复的单 Agent Loop：

### 建议表结构

```text
study_sessions
  id / user_id / document_id / goal / status / current_round / created_at

session_events
  id / session_id / event_type / payload / created_at
```

### 状态机

```text
created
  ↓ 检索资料
diagnosing
  ↓ 生成第一题
questioning
  ↓ 用户提交答案
grading
  ↓ 记录薄弱点
deciding
  ├─ 未达到目标：生成下一题
  └─ 达到轮次/目标：总结
completed
```

### 第一版限制

- 最多 5 轮；
- 每轮只能调用“检索、出题、批改、总结”四个工具；
- 每轮状态落库，刷新页面或重启服务后可以继续；
- 每次模型调用都记录输入摘要、输出、耗时和错误；
- 达到轮次上限必须停止，不能无限自循环；
- 最终输出薄弱点、已掌握点和下一步建议。

### 如何评估

面试不要说“感觉挺好”，要给出指标：

- 结构化输出通过率；
- 引用片段命中率；
- 批改分数与人工评分的一致性；
- 平均响应时间；
- 模型调用失败率；
- 每轮 token/费用；
- 用户完成一轮学习会话的比例。

## 7. 服务器部署

### 7.1 架构

```text
浏览器 / Swagger
      ↓ HTTP :80
    Nginx
      ↓ 反向代理到 127.0.0.1:8000
 Uvicorn + FastAPI
      ↓
SQLite /var/lib/learning-assistant/app.db
```

### 7.2 为什么需要 Nginx

- 对外监听 80/443，应用只监听本机回环地址；
- 反向代理，把请求转给 Uvicorn；
- 后续可以统一做 HTTPS、限流、压缩和静态资源缓存；
- Nginx 处理连接和超时，应用专注业务。

### 7.3 为什么 Uvicorn 绑定 127.0.0.1

应用端口不直接暴露公网，只允许 Nginx 访问。这样外部不能绕过反向代理直接打应用端口，安全边界更清楚。

### 7.4 为什么用 systemd

`learning-assistant.service` 负责：

- 开机启动；
- 进程异常退出后自动重启；
- 用 `www-data` 用户运行，降低权限；
- 从 `.env` 读取环境变量；
- 统一用 `journalctl` 查看日志。

### 7.5 密钥和权限

- `SECRET_KEY` 在服务器生成随机值，不使用开发默认值；
- `DEEPSEEK_API_KEY` 只放在 `/opt/learning-assistant/.env`；
- `.env` 不提交 Git；
- `.env` 权限为 `640`，由 `root:www-data` 管理；
- 数据库放在 `/var/lib/learning-assistant`，而不是代码目录。

### 7.6 部署更新流程

```text
上传代码
  ↓
安装/更新依赖
  ↓
alembic upgrade head
  ↓
systemctl restart learning-assistant
  ↓
systemctl reload nginx
  ↓
curl /health + 打开 /ui/ 验证
```

迁移必须在新代码启动前执行；否则 ORM 可能访问不存在的列。

### 7.7 排障顺序

```text
1. curl http://127.0.0.1:8000/health        # 应用是否活着
2. systemctl status learning-assistant      # 进程状态
3. journalctl -u learning-assistant -f      # 应用日志
4. sudo nginx -t                            # Nginx 配置
5. tail /var/log/nginx/error.log            # 代理错误
6. 检查安全组 80/443 和 UFW
```

### 7.8 备份和回滚

- 部署前复制 SQLite 数据库备份；
- 代码出错时回滚到上一个 Git commit；
- 数据库迁移前先备份，迁移失败时恢复数据库；
- 当前是单机 SQLite，不能把它说成高可用生产架构。

## 8. 面试高频问题

### Q1：你的项目是 Agent 吗？

> 是单轮受限 Agent，不是多轮自主 Agent。PydanticAI 的模型可以在一次请求内决定检索词、调用只读 `search_documents` 工具、观察结果并返回类型化草稿；服务端用 `RunContext` 注入权限，用 `output_validator` 校验来源，用 `UsageLimits` 限制请求和工具次数。它还缺少跨请求状态、多轮规划和跨会话恢复，下一步会用 `study_sessions` 和 `session_events` 做最多 5 轮的状态机。

### Q2：RAG 怎么减少幻觉？

> 先把资料切片建索引，只把当前用户相关片段放进上下文，要求模型输出引用片段 ID；服务端过滤不属于检索结果的 ID。模型不能凭空引用不存在的片段。但 RAG 不能完全消除幻觉，所以还加了 Pydantic 校验、人工确认和草稿状态。

### Q3：为什么不用向量数据库？

> MVP 先用 SQLite FTS5 验证闭环，减少部署和运维成本。FTS5 对关键词检索可解释，但语义召回弱；等出现“同义表达搜不到”的真实问题，再加 embedding + 混合召回，而不是提前堆组件。

### Q4：AI 批改怎么保证公平？

> 批改只看参考答案和 rubric，要求输出命中点、遗漏点和分数；结果落库可回看。模型分数只作为学习反馈，不冒充正式考试评分。后续会用人工标注样本评估一致性，并加入低置信度提示。

### Q5：如何避免模型直接改数据库？

> 模型只有一个只读检索工具，没有数据库写工具。`user_id`、`document_id` 和 Session 放在 `StudyDeps` 里，由服务端注入，模型无法通过工具参数越权。模型返回类型化草稿后，`output_validator` 还要校验引用来源；只有用户确认时，业务代码才把草稿写入 `question` 表。批改结果也由服务端写 `answer` 表。

### Q6：Nginx 和 Uvicorn 有什么区别？

> Uvicorn 是 ASGI 应用服务器，负责运行 FastAPI；Nginx 是反向代理和 Web 服务器，负责对外端口、转发、TLS、静态资源和连接管理。生产上通常 Nginx 在前，Uvicorn 只监听本机。

### Q7：服务器部署后 500 怎么查？

> 先看 `/health` 区分应用是否存活，再看 `systemctl status` 和 `journalctl` 定位应用异常，然后看 Nginx error log 区分代理问题，最后检查环境变量、数据库迁移和权限。

### Q8：为什么 SQLite 不适合所有生产场景？

> SQLite 简单、零运维，适合单机 MVP 和低并发；但写入并发、容灾和多实例扩展有限。用户量和写入量上来后，应切 PostgreSQL，并考虑连接池、备份、监控和迁移策略。

### Q9：怎么证明测试不是摆设？

> 56 个测试覆盖认证、跨用户 404、输入校验、级联删除、检索隔离、StudyAgent 工具轨迹、非法来源重试、草稿来源校验、批改落库和完整闭环。普通模型调用用 Fake LLM，Agent 用 PydanticAI `FunctionModel` 精确控制工具调用和输出，不依赖外部网络，保证可重复。

### Q10：下一步最难的是什么？

> 不是再调一次模型，而是会话状态设计、有限轮次控制、工具失败恢复、上下文压缩和效果评估。没有这些，所谓 Agent 只是一个会循环调 API 的脚本。

## 9. 明天（2026-11-18）项目线安排

总时长约 105 分钟，默认 22:00 收工。

| 时间 | 任务 | 验收 |
|---|---|---|
| 20 min | 读本文第 0–6 节，合上文档复述 RAG 链路 | 能画出资料 → 切片 → 检索 → 出题 → 草稿 → 批改 |
| 15 min | 读第 7 节，手画部署图 | 能解释 Nginx、Uvicorn、systemd、SQLite 的关系 |
| 20 min | 对照 `app/retrieval.py`、`app/llm.py`、`app/routers/rag.py`、`app/routers/answers.py` | 能指出每个文件负责哪一段 |
| 20 min | 不看笔记回答第 8 节 10 个问题并录音 | 至少 8 题能连续说 60 秒 |
| 20 min | 按 `docs/GITHUB_BACKEND_READING.md` 读官方模板的一个模块 | 写 3 条“我们项目可以借鉴什么” |
| 10 min | 整理 3 分钟项目介绍 | 包含业务、技术链路、难点、边界、下一步 |

明天不要求新增业务功能，先把“能讲清楚”变成可验收产物。
