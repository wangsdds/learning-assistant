# GitHub 后端项目阅读清单

> 仓库已经浅克隆到：
> `reference/github-backend-projects/`
>
> `reference/` 在 `.gitignore` 中，属于本地参考材料，不会误提交到项目仓库。
>
> 阅读目标不是照抄代码，而是带着问题看：**它解决了我们项目哪个不足？**

## 1. `full-stack-fastapi-template`（官方全栈模板）

本地路径：

```text
reference/github-backend-projects/full-stack-fastapi-template
```

为什么读：

- FastAPI 官方维护的全栈模板；
- 有 PostgreSQL、Docker Compose、Alembic、JWT、测试、CI；
- 适合学习“项目怎么组织”，不是只看接口怎么写。

建议阅读顺序：

1. `backend/app/main.py`：应用如何组装。
2. `backend/app/core/config.py`：Pydantic Settings 如何管理环境变量。
3. `backend/app/core/db.py`：engine、Session、数据库初始化。
4. `backend/app/models.py`：SQLModel 的模型、输入、输出拆分。
5. `backend/app/api/deps.py`：依赖注入和认证依赖。
6. `backend/app/api/routes/`：按资源拆路由。
7. `backend/app/crud.py`：业务 CRUD 和路由分离。
8. `backend/tests/`：认证、用户、Item 的测试写法。
9. `compose.yml`、`backend/Dockerfile`、`deployment.md`：部署方式。

读的时候回答：

- 它的配置和密钥从哪里进入应用？
- 路由、CRUD、模型三层如何分工？
- 测试如何隔离数据库和用户？
- 它的部署比我们当前的 Nginx + systemd 多了什么？

不要直接照搬：

- 它使用 SQLModel 和 PostgreSQL，我们当前是 SQLAlchemy + SQLite；
- 它前端使用 React，我们刻意保持原生 HTML/CSS/JS；
- 它是模板，包含很多我们 MVP 不需要的邮件、后台和 Docker 配置。

## 2. `fastapi-realworld-example-app`（RealWorld 后端实现）

本地路径：

```text
reference/github-backend-projects/fastapi-realworld-example-app
```

为什么读：

- 完整的文章、用户、评论、标签业务；
- 路由、依赖、Repository、Service 分层明显；
- 有 JWT、异步 PostgreSQL、SQL 查询和较完整测试。

建议阅读顺序：

1. `app/main.py`：应用入口。
2. `app/api/routes/api.py`：总路由如何聚合。
3. `app/api/dependencies/`：认证、数据库、资源依赖。
4. `app/db/repositories/`：Repository 封装查询。
5. `app/services/`：业务逻辑和 JWT。
6. `app/models/schemas/`：请求/响应模型。
7. `tests/conftest.py` 和 `tests/test_api/`：异步测试与 fixture。

读的时候回答：

- Repository 层解决了什么问题？
- 它如何避免路由函数里堆 SQL？
- 依赖注入如何复用“当前用户”和数据库连接？
- 我们的 `questions.py`、`answers.py` 哪些地方可以拆出 service/repository？

注意：

- 这个仓库版本较旧，依赖不是最新；
- 不要把它当成可以直接运行的生产模板；
- 主要学分层和测试组织，不要陷入它的历史依赖。

## 3. `fastapi-best-practices`（工程实践清单）

本地路径：

```text
reference/github-backend-projects/fastapi-best-practices
```

中文入口：

```text
README_ZH.md
```

为什么读：

- 不是业务项目，而是高密度工程经验；
- 适合快速发现自己项目里的工程缺口；
- 每个主题都可以转成面试回答。

明天只读四节：

1. `项目结构`：为什么按领域拆分，而不是所有路由堆在一个文件。
2. `异步路由`：I/O 密集任务和 CPU 密集任务的区别。
3. `依赖项`：依赖注入、链式依赖、依赖缓存。
4. `Migrations. Alembic` + `Set DB naming conventions`：迁移和数据库命名规范。

读的时候回答：

- 我们哪些路由是同步的？为什么不影响当前 MVP？
- 哪些依赖可以在我们项目里复用？
- Alembic 迁移为什么不能靠 `create_all` 代替？
- 数据库约束命名为什么会影响线上迁移和排障？

## 4. 三个仓库的对比结论

| 维度 | 学习助手 | 官方模板 | RealWorld |
|---|---|---|---|
| 业务 | 学习计划 + RAG 出题 + 批改 | 用户 + Item + 邮件 | 文章社区 |
| 数据库 | SQLite FTS5 | PostgreSQL + SQLModel | PostgreSQL + 异步驱动 |
| 分层 | router 为主，少量 helper | router + crud + core | router + service + repository |
| 部署 | Nginx + systemd | Docker Compose + Traefik | Docker + ASGI |
| 测试 | 50 个，Fake LLM | 全栈模板测试 | 较完整 API 测试 |
| 适合学 | RAG 业务闭环 | 工程组织与部署 | 分层与异步实践 |

## 5. 阅读产出要求

每读一个仓库，只写三条：

1. 一个值得借鉴的设计；
2. 一个我们项目暂时不需要的设计；
3. 一个可以改进我们项目的具体动作。

不要写大段摘要。面试需要的是判断力，不是复述目录。
