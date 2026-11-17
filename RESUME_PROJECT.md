# 学习助手后端｜简历与面试材料

## 一句话项目介绍

基于 FastAPI + SQLAlchemy 构建的多用户学习助手后端，支持学习计划、资料管理、题目生成、答题评分和答题记录回看，使用 JWT 做认证并按用户隔离数据。

## 技术栈

Python 3.13、FastAPI、SQLAlchemy 2.0、Alembic、SQLite / PostgreSQL、JWT、bcrypt、pytest、Swagger/OpenAPI、HTML/CSS/JavaScript

## 简历项目栏（可直接使用）

- 设计并实现多用户学习助手后端，覆盖注册登录、学习计划、资料、题目、答题记录等核心模块，提供 17 个 REST API。
- 基于 JWT + bcrypt 实现认证与密码安全存储，所有业务查询按当前用户过滤；跨用户访问统一返回 404，避免泄露资源存在性。
- 使用 SQLAlchemy 2.0 ORM 与 Alembic 管理 6 张表及外键级联，补充外键索引；在 5 万行测试数据上将关联查询从约 12.86ms 降至 0.138ms。
- 使用 `APIRouter` 按领域拆分用户、资料、题目、答题和计划模块，并通过 pytest + 内存 SQLite 构建 32 个测试，覆盖认证、隔离、边界校验和完整业务闭环。
- 提供原生 JavaScript 浏览器 UI，覆盖登录注册、学习计划、资料、建题、答题和历史回看；通过 Nginx + systemd 部署到云服务器。

## 面试讲解提纲

### 1. 用户隔离

- `user_id` 从 JWT 的当前用户中获取，不接受客户端传入。
- 查询资料、题目、答案、计划时都带当前用户条件。
- 访问别人的资源返回 404，而不是 403，避免暴露资源是否存在。

### 2. 数据一致性

- 6 张表通过外键和 `ON DELETE CASCADE` 建立关联。
- SQLite 默认不启用外键检查，因此在每个连接上执行 `PRAGMA foreign_keys=ON`。
- 邮箱唯一性依赖数据库约束，捕获 `IntegrityError` 后回滚并返回 409，避免“先查再插”的竞态。

### 3. 测试与重构

- 每个测试使用独立的内存 SQLite，通过 `dependency_overrides` 替换真实数据库。
- 端到端测试覆盖：注册 → 登录 → 计划 → 资料 → 出题 → 答题 → 回看。
- 先用测试锁定行为，再把单体 `main.py` 拆成多个 router；当前全套仍为 32 passed。

### 4. 当前边界

当前版本是可演示的全栈 MVP，已部署到云服务器；检索层、RAG、agent loop、流式返回，以及 PostgreSQL/Docker 的生产级部署尚未实现。面试时应明确区分“已完成”和“下一步计划”，不要把这些说成已完成。

## 演示顺序

```powershell
# 1. 运行闭环演示
python tools/demo_flow.py

# 2. 运行测试
pytest -q

# 3. 启动服务并打开浏览器 UI
.\run_api.ps1
# http://127.0.0.1:8000/ui/
# API 文档：http://127.0.0.1:8000/docs
```

## 简历投递时的项目一句话

> 独立开发多用户学习助手全栈 MVP，使用 FastAPI + SQLAlchemy + JWT 实现计划、资料、出题与答题闭环，配套浏览器 UI、分层路由、数据库迁移和 32 个自动化测试。
