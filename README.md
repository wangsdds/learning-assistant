# 学习助手 · 后端

> 一个多用户的学习计划 / 资料 / 出题 / 答题后端。FastAPI + SQLAlchemy 2.0 + Alembic，开发期 SQLite，可切换 PostgreSQL。

`Python 3.13` · `FastAPI` · `SQLAlchemy 2.0` · `Alembic` · `JWT` · `30 tests passed`

---

## 这是什么

把「今天学什么 → 看资料 → 出题 → 答题 → 回看记录」做成一套可用的后端：

- 每个用户有自己的资料、题目、答题记录和计划，互相看不到
- 题目从资料里生成，答题时服务端记录耗时和评分
- 有测试、有迁移、有性能实测，不是只能跑一遍的 demo

## 功能

| 模块 | 能力 |
|---|---|
| 用户 | 注册、登录（bcrypt + JWT）、获取当前用户 |
| 资料 | 新建、列表、详情；文件或网址至少填一个（数据库 CHECK 约束） |
| 题目 | 按资料建题、列题、改题（只改传了的字段） |
| 答题 | 提交答案（服务端生成耗时与评分）、按题回看 |
| 计划 | 按天建计划、列表、详情 |
| 隔离 | 所有业务查询都带 `user_id`，跨用户访问统一返回 404 |

## 技术栈

- **Web**：FastAPI 0.141、Uvicorn
- **ORM**：SQLAlchemy 2.0（`Mapped` / `mapped_column`）
- **迁移**：Alembic
- **数据库**：SQLite（开发）→ PostgreSQL（生产，改 `DATABASE_URL` 即可）
- **认证**：JWT（PyJWT，HS256）+ bcrypt
- **测试**：pytest + FastAPI TestClient，内存 SQLite

## 架构

```
app/
├── main.py          # 入口：挂路由、Swagger、/health
├── db.py            # engine / Base / Session，SQLite 外键 PRAGMA
├── models.py        # 6 张表的 ORM 模型
├── schemas.py       # Pydantic 请求/响应模型
├── security.py      # JWT 签发与校验、get_current_user
└── routers/         # users / documents / questions / answers / plan_days
```

请求链路：

```
HTTP → APIRouter → Depends(get_current_user) → SQLAlchemy Session → SQLite / PostgreSQL
```

## 数据模型（6 张表）

```
users ──< plan_days ──< newplan
  └──< documents ──< question ──< answer
```

- 所有外键带 `ondelete="CASCADE"`，删除用户时六张表在**一个事务**里归零
- SQLite 默认不检查外键，`db.py` 在每个连接上执行 `PRAGMA foreign_keys=ON`
- `documents` 上有 CHECK 约束：文件和网址至少填一个

## 快速开始

```powershell
# 1. 安装依赖
python -m pip install -r requirements.txt bcrypt pyjwt

# 2. 运行完整闭环演示
python tools/demo_flow.py

# 3. 启动
python -m uvicorn app.main:app --reload --port 8000

# 4. 打开 Swagger
# http://127.0.0.1:8000/docs
```

本机也可以直接跑 `.\run_api.ps1`（脚本里固定了 Python 与 site-packages 路径）。

一键演示会在内存 SQLite 中依次完成注册、登录、建计划、加资料、出题、答题和回看，不会污染 `app.db`。

简历和面试讲解材料见 [`RESUME_PROJECT.md`](RESUME_PROJECT.md)。

环境变量：

| 变量 | 默认 | 说明 |
|---|---|---|
| `DATABASE_URL` | `sqlite:///app.db` | 切 PostgreSQL 改这里 |
| `SECRET_KEY` | `dev-only-change-me` | **生产必须改** |
| `SQL_ECHO` | 空 | 设为 `1` 打印 SQL |

## API 概览（13 个路径 / 17 个操作）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/users` | 注册（邮箱重复返回 409） |
| POST | `/login` | 登录，返回 JWT |
| GET | `/me` | 当前用户 |
| GET | `/users/{user_id}` | 用户详情 |
| GET | `/users/by-email/{email}` | 按邮箱查用户 |
| GET | `/documents` | 资料列表 |
| POST | `/documents` | 新建资料 |
| GET | `/documents/{document_id}` | 资料详情 |
| POST | `/documents/{document_id}/questions` | 给资料建题 |
| GET | `/documents/{document_id}/questions` | 资料的题目列表 |
| PATCH | `/questions/{question_id}` | 改题（只改传入字段） |
| POST | `/questions/{question_id}/answers` | 提交答案 |
| GET | `/questions/{question_id}/answers` | 答案列表 |
| GET | `/plan_days` | 计划列表 |
| POST | `/plan_days` | 新建计划 |
| GET | `/plan_days/{plan_id}` | 计划详情 |
| GET | `/health` | 健康检查 |

## 测试

```powershell
pytest -q
# 30 passed in 12.67s
```

覆盖的关键边界：

- 未登录访问业务接口 → 401
- 访问别人的资源 → 404（不是 403，避免泄露资源是否存在）
- 重复邮箱注册 → 409
- 只改题干 / 只改答案 / 空对象 / 空题干
- 跨用户改题、跨用户答题
- 删除用户后六张表级联清空

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
3. **级联删除为什么必须在一个事务里**：六张表任一失败都要整体回滚，否则会留下孤儿数据。
4. **JWT 无状态怎么登出**：服务端不存 session，登出由客户端丢弃 token；需要强制失效时再加黑名单或短过期 + refresh token。

## 目录结构

```
项目-学习助手/
├── app/                 # 应用代码
├── tests/               # pytest（30 个用例）
├── migrations/          # Alembic 迁移
├── docs/                # 表设计、评审记录、schema.sql
├── tools/               # bench_fk_index.py 等
├── requirements.txt
└── run_api.ps1
```

## 已知限制 / Roadmap

- [ ] 统一异常响应格式与分页
- [ ] 用户查询接口的权限收敛（仅允许本人访问）
- [ ] 检索层：资料切分 + 向量检索
- [ ] agent loop + tool calling
- [ ] 生产部署：PostgreSQL + Docker Compose

## 截图清单（发帖 / 简历用）

1. `http://127.0.0.1:8000/docs` 的 Swagger 首页
2. `pytest -q` 的 `30 passed` 输出
3. `python tools/bench_fk_index.py` 的优化前后对比
4. `docs/schema.sql` 的六表关系图（dbdiagram.io 导入即可）
5. 一次完整请求：注册 → 登录 → 建资料 → 出题 → 答题 → 回看
