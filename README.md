# 学习助手 · 全栈

> 一个多用户的学习计划 / 资料 / 检索 / 出题 / 答题应用。FastAPI + SQLAlchemy 2.0 + Alembic + SQLite FTS5，可接入 DeepSeek 或 OpenAI 兼容模型。

`Python 3.13` · `FastAPI` · `SQLAlchemy 2.0` · `Alembic` · `JWT` · `FTS5` · `PydanticAI` · `56 tests passed`

---

## 这是什么

把「今天学什么 → 看资料 → 检索 → 出题 → 答题 → 回看记录」做成一套可用的应用：

- 每个用户有自己的资料、题目、答题记录和计划，互相看不到
- 资料自动切片并用 SQLite FTS5 检索，模型可以根据引用片段生成结构化题目草稿
- 基于 PydanticAI 的受限 StudyAgent 会自主调用检索工具，服务端再校验来源、步数和工具调用上限
- 整数题服务端精确判分；文本题按 rubric 调用模型批改，返回分数、命中点和遗漏点
- 有测试、有迁移、有性能实测，不是只能跑一遍的 demo

## 功能

| 模块 | 能力 |
|---|---|
| 用户 | 注册、登录（bcrypt + JWT）、获取当前用户 |
| 资料 | 新建、列表、详情；文件或网址至少填一个（数据库 CHECK 约束） |
| 题目 | 按资料建题、列题、改题；支持整数题和文本题，标准答案只保存在服务端 |
| 答题 | 整数题精确判分；文本题 AI 批改；按题回看分数、反馈和历史 |
| 计划 | 按天建计划、列表、详情 |
| 检索 | 资料自动切片；SQLite FTS5 检索，短查询自动回退到词项匹配 |
| 智能出题 | 检索相关片段，调用 DeepSeek / OpenAI 兼容模型返回题目、答案、rubric 和引用来源；草稿可一键入库 |
| StudyAgent | 使用 PydanticAI 将 `search_documents` 注册为工具；通过 `RunContext` 注入用户和文档归属，结构化输出后校验引用来源，并限制请求步数、工具次数和超时 |
| 自动批改 | 按参考答案和 rubric 评分，返回 0-100 分、命中要点、遗漏要点和改进建议，并持久化到作答记录 |
| 隔离 | 所有业务查询都带 `user_id`，跨用户访问统一返回 404 |

## 技术栈

- **Web**：FastAPI 0.141、Uvicorn
- **ORM**：SQLAlchemy 2.0（`Mapped` / `mapped_column`）
- **迁移**：Alembic
- **数据库**：SQLite（开发）→ PostgreSQL（生产，改 `DATABASE_URL` 即可）
- **认证**：JWT（PyJWT，HS256）+ bcrypt
- **测试**：pytest + FastAPI TestClient，内存 SQLite
- **检索**：SQLite FTS5（trigram）+ 词项回退
- **Agent**：PydanticAI 2.75，类型化依赖、函数工具、结构化输出和 `output_validator`
- **模型**：DeepSeek / OpenAI 兼容 Chat Completions，服务端环境变量配置

## 架构

```
app/
├── main.py          # 入口：挂路由、Swagger、/health
├── db.py            # engine / Base / Session，SQLite 外键 PRAGMA
├── models.py        # 7 张表的 ORM 模型
├── schemas.py       # Pydantic 请求/响应模型
├── security.py      # JWT 签发与校验、get_current_user
├── chunking.py      # 资料切片
├── retrieval.py     # FTS5 索引、检索与回退
├── llm.py           # DeepSeek / OpenAI 兼容出题客户端
├── study_agent.py   # PydanticAI Agent、检索工具、依赖注入和来源校验
└── routers/         # users / documents / questions / answers / plan_days / rag / study_agent
```

请求链路：

```
HTTP → APIRouter → Depends(get_current_user) → SQLAlchemy Session → SQLite / PostgreSQL
                                                     └── StudyAgent → search_documents（仅当前用户、当前文档）
```

## 数据模型（7 张表）

```
users ──< plan_days ──< newplan
  └──< documents ──< document_chunks
          └──< question ──< answer
```

- 所有外键带 `ondelete="CASCADE"`，删除用户时关联数据在**一个事务**里归零
- SQLite 默认不检查外键，`db.py` 在每个连接上执行 `PRAGMA foreign_keys=ON`
- `documents` 上有 CHECK 约束：文件和网址至少填一个
- `document_chunks` 保存资料切片，由 FTS5 触发器同步全文索引

## 快速开始

```powershell
# 1. 安装依赖
python -m pip install -r requirements.txt bcrypt pyjwt

# 2. 执行数据库迁移
python -m alembic upgrade head

# 3. 运行完整闭环演示
python tools/demo_flow.py

# 4. 启动
python -m uvicorn app.main:app --reload --port 8000

# 5. 打开浏览器 UI
# http://127.0.0.1:8000/ui/

# 6. 打开 Swagger
# http://127.0.0.1:8000/docs
```

Windows 也可以直接跑 `.\run_api.ps1`；脚本优先使用项目 `.venv`，可用 `LEARNING_ASSISTANT_PYTHON` 指定其他解释器。

浏览器 UI 使用原生 HTML/CSS/JavaScript，与 API 同源部署，覆盖登录注册、学习计划、资料收录、建题、答题和作答历史。根路径 `/` 会自动跳转到 `/ui/`。
在资料详情中点击「AI 出题」，系统会先检索切片，再生成带标准答案、评分要点和引用来源的题目草稿。

一键演示会在内存 SQLite 中依次完成注册、登录、建计划、加资料、出题、答题和回看，不会污染 `app.db`。

简历和面试讲解材料见 [`RESUME_PROJECT.md`](RESUME_PROJECT.md)。
Agent 开发与服务器部署的面试知识点见 [`docs/INTERVIEW_AGENT_DEPLOY.md`](docs/INTERVIEW_AGENT_DEPLOY.md)。
GitHub 后端项目阅读路线见 [`docs/GITHUB_BACKEND_READING.md`](docs/GITHUB_BACKEND_READING.md)。
Agent 与服务器部署自学资料见 [`docs/AGENT_DEPLOY_RESOURCES.md`](docs/AGENT_DEPLOY_RESOURCES.md)。
简历项目八股与口述稿见 [`docs/RESUME_INTERVIEW_QA.md`](docs/RESUME_INTERVIEW_QA.md)。

环境变量：

| 变量 | 默认 | 说明 |
|---|---|---|
| `DATABASE_URL` | `sqlite:///app.db` | 切 PostgreSQL 改这里 |
| `SECRET_KEY` | `dev-only-change-me` | **生产必须改** |
| `SQL_ECHO` | 空 | 设为 `1` 打印 SQL |
| `DEEPSEEK_API_KEY` | 空 | 配置后启用 DeepSeek 出题与批改 |
| `LLM_API_KEY` | 空 | 其他 OpenAI 兼容服务的密钥 |
| `LLM_BASE_URL` | 按提供商 | 例如 `https://api.openai.com/v1` |
| `LLM_MODEL` | `deepseek-chat` / `gpt-4o-mini` | 模型名称 |
| `LLM_TRUST_ENV` | `false` | 设为 `true` 时读取系统代理环境变量 |

## 智能出题配置

DeepSeek 示例：

```powershell
$env:DEEPSEEK_API_KEY = "your-key"
python -m uvicorn app.main:app --reload --port 8000
```

其他 OpenAI 兼容服务使用 `LLM_API_KEY`、`LLM_BASE_URL` 和 `LLM_MODEL`。密钥只放服务端环境变量，不会返回给浏览器。

接口调用顺序：

```text
POST /documents
  → 自动切片并写入 FTS5
GET  /documents/{id}/search?q=回表
  → 返回相关片段
POST /documents/{id}/study-agent
  → Agent 自主调用 search_documents，返回带来源校验和运行指标的草稿
POST /documents/{id}/generate-question
  → 返回题目、答案、rubric、难度和引用来源
POST /documents/{id}/questions/from-draft
  → 校验引用片段后，把草稿保存成正式文本题
POST /questions/{id}/answers/grade
  → 按 rubric 批改文本答案并写入作答记录
```

模型生成结果先作为草稿展示，用户确认后再写入 `question` 表。参考答案和 rubric 不会通过题目列表接口返回；批改结果的命中点、遗漏点和反馈会随作答记录保存。

## API 概览（19 个路径 / 23 个操作）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/users` | 注册（邮箱重复返回 409） |
| POST | `/login` | 登录，返回 JWT |
| GET | `/me` | 当前用户 |
| GET | `/users/{user_id}` | 用户详情（仅可查询自己） |
| GET | `/users/by-email/{email}` | 按邮箱查用户（仅可查询自己） |
| GET | `/documents` | 资料列表 |
| POST | `/documents` | 新建资料 |
| GET | `/documents/{document_id}` | 资料详情 |
| POST | `/documents/{document_id}/reindex` | 重建资料切片与全文索引 |
| GET | `/documents/{document_id}/search` | 在本人资料中检索相关片段 |
| POST | `/documents/{document_id}/generate-question` | 检索并生成结构化题目草稿 |
| POST | `/documents/{document_id}/study-agent` | PydanticAI Agent 检索并生成受来源约束的题目草稿 |
| POST | `/documents/{document_id}/questions` | 给资料建题 |
| POST | `/documents/{document_id}/questions/from-draft` | 保存 AI 草稿为正式文本题 |
| GET | `/documents/{document_id}/questions` | 资料的题目列表 |
| PATCH | `/questions/{question_id}` | 改题（只改传入字段） |
| POST | `/questions/{question_id}/answers` | 提交整数题答案 |
| POST | `/questions/{question_id}/answers/grade` | AI 批改文本题答案 |
| GET | `/questions/{question_id}/answers` | 答案列表 |
| GET | `/plan_days` | 计划列表 |
| POST | `/plan_days` | 新建计划 |
| GET | `/plan_days/{plan_id}` | 计划详情 |
| GET | `/health` | 健康检查 |

## 测试

```powershell
pytest -q
# 56 passed
```

覆盖的关键边界：

- 未登录访问业务接口 → 401
- 未登录查询用户、查询其他用户 → 401 / 404
- 访问别人的资源 → 404（不是 403，避免泄露资源是否存在）
- 重复邮箱注册 → 409
- 只改题干 / 只改答案 / 空对象 / 空题干
- 跨用户改题、跨用户答题
- 删除用户后关联表级联清空
- 资料切片长度、中文检索、跨用户检索隔离
- 模型返回值的结构化校验和来源约束（测试使用 Fake LLM）
- StudyAgent 的工具调用轨迹、非法来源重试、跨用户隔离、运行上限和异常映射
- 文本题答案不外泄、草稿引用片段归属校验、批改明细持久化和跨用户批改隔离

## 性能实测

`tools/bench_fk_index.py`，5 万行数据：

| 操作 | 优化前 | 优化后 | 提升 |
|---|---|---|---|
| 关联查询 | 12.86 ms | 0.138 ms | 约 93× |
| 级联删除 | 546 ms | 3.6 ms | 约 150× |

原因：SQLite 不会自动给外键列建索引；补索引后关联查询才走索引，级联删除也不必全表扫描。

## 设计取舍（面试可讲）

1. **跨用户为什么返回 404 而不是 403**：403 等于告诉对方“这个资源存在，只是你没权限”，404 不泄露存在性。
2. **邮箱唯一为什么靠数据库约束**：应用层“先查再插”有竞态，两个请求同时通过检查会插出两条；直接 `commit` 捕获 `IntegrityError` 转 409 才是原子的。
3. **级联删除为什么必须在一个事务里**：任一关联表失败都要整体回滚，否则会留下孤儿数据。
4. **JWT 无状态怎么登出**：服务端不存 session，登出由客户端丢弃 token；需要强制失效时再加黑名单或短过期 + refresh token。

## 目录结构

```
项目-学习助手/
├── app/                 # 应用代码
├── tests/               # pytest（56 个用例）
├── migrations/          # Alembic 迁移
├── docs/                # 表设计、评审记录、schema.sql
├── tools/               # bench_fk_index.py 等
├── requirements.txt
└── run_api.ps1
```

## 已知限制 / Roadmap

- [ ] 统一异常响应格式与分页
- [x] 用户查询接口的权限收敛（仅允许本人访问）
- [x] 检索层：资料切片 + SQLite FTS5
- [x] 结构化题目生成（带答案、rubric 和来源）
- [x] PydanticAI 单轮受限 StudyAgent（工具调用 + 结构化输出 + 来源校验）
- [x] 基于 rubric 的文本题 AI 批改与评分明细持久化
- [ ] 多轮学习会话状态和 LangGraph 状态机
- [ ] 向量检索与混合召回
- [ ] 生产部署：PostgreSQL + Docker Compose

## 截图清单（发帖 / 简历用）

1. `http://127.0.0.1:8000/ui/` 的工作台与资料答题页
2. `http://127.0.0.1:8000/docs` 的 Swagger 首页
3. `pytest -q` 的 `56 passed` 输出
4. `python tools/bench_fk_index.py` 的优化前后对比
5. `docs/schema.sql` 的表关系图（dbdiagram.io 导入即可）

## License

MIT
