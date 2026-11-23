# Agent 开发与服务器部署｜自学资料清单

> 目标：不是收集链接，而是用最少资料把当前学习助手推进到“有状态、可评估、可部署”的版本。
>
> 推荐顺序：概念 → 工具调用 → 单 Agent 状态机 → RAG 评估 → 部署与运维。

## 1. 先定方向

你做后端，不需要先学模型训练。当前要补的是：

- LLM 应用架构：Prompt、结构化输出、工具调用、超时和重试；
- RAG：切片、召回、重排、引用、评估；
- Agent：状态、计划、工具选择、观察、停止条件、失败恢复；
- 工程化：日志、追踪、评估集、成本、权限、安全；
- 部署：Linux、Nginx、systemd、Docker、PostgreSQL、CI/CD、备份。

一句话：

> Agent 开发的核心不是“多调用几次模型”，而是让模型在受控工具和持久化状态中完成多步任务。

## 2. 最少必读

### 概念

1. **Anthropic: Building effective agents**
   https://www.anthropic.com/research/building-effective-agents
   - 先分清 workflow 和 agent；
   - 重点看 prompt chaining、routing、parallelization、orchestrator-workers、evaluator-optimizer。

2. **OpenAI: A practical guide to building agents**
   https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
   - 看工具设计、guardrails、人工确认和评估。

3. **Chip Huyen: AI Engineering**
   - 如果只买一本，优先这本；
   - 重点读 RAG、evaluation、prompt engineering、serving 和 cost/latency。

4. **The LLM Engineer's Handbook**（Paul Iusztin / Maxime Labonne）
   - 更偏工程落地；
   - 适合看 RAG、微调、评估和部署组合。

### 工具调用与结构化输出

1. **OpenAI Cookbook**
   https://github.com/openai/openai-cookbook
   - 先看 function calling、structured outputs、RAG、evaluation 相关 notebook。

2. **OpenAI Agents SDK**
   https://github.com/openai/openai-agents-python
   https://openai.github.io/openai-agents-python/
   - 看 agent loop、tools、handoffs、guardrails、tracing；
   - 不要一开始学 handoffs 和多 agent，先看单 agent + tools。

3. **PydanticAI**
   https://github.com/pydantic/pydantic-ai
   - 和你现有的 Pydantic + FastAPI 技术栈最贴合；
   - 重点看 typed dependencies、structured output、tool calling 和 testing。

### 有状态的 Agent

1. **LangGraph**
   https://github.com/langchain-ai/langgraph
   - 看 state graph、checkpoint、human-in-the-loop、durable execution；
   - 先理解状态机，再决定是否引入框架。

2. **LangGraph 文档**
   https://langchain-ai.github.io/langgraph/
   - 重点不是 API 记忆，而是节点、边、状态和恢复。

### RAG 质量

1. **LlamaIndex**
   https://github.com/run-llama/llama_index
   - 看 ingestion、chunking、retrieval、reranking、query engines。

2. **Ragas**
   https://github.com/explodinggradients/ragas
   - 看 faithfulness、answer relevancy、context precision/recall；
   - 用来建立自己的 RAG 评估集。

### 可观测性与安全

1. **Langfuse**
   https://github.com/langfuse/langfuse
   - 记录每次 LLM 调用的输入、输出、耗时、成本和错误；
   - 面试时“可观测性”比“会调 API”更有区分度。

2. **Model Context Protocol**
   https://github.com/modelcontextprotocol/modelcontextprotocol
   - 先知道它是工具/资源协议，不要过早把项目改成 MCP 服务。

### 多 Agent，最后再看

- Microsoft AutoGen：https://github.com/microsoft/autogen
- CrewAI：https://github.com/crewAIInc/crewAI
- Google ADK：https://github.com/google/adk-python

这些适合在你已经能讲清单 Agent 状态机之后再看。否则容易变成“会写角色和任务，但讲不清状态、失败和评估”。

## 3. 服务器部署资料

### 文章和官方文档

1. **The Twelve-Factor App**
   https://12factor.net/
   - 配置、日志、进程、端口绑定、环境隔离；
   - 部署面试的基础语言。

2. **FastAPI Deployment**
   https://fastapi.tiangolo.com/deployment/
   - 看 Uvicorn/Gunicorn、HTTPS、容器和反向代理。

3. **Docker Compose**
   https://docs.docker.com/compose/
   - 服务、网络、卷、健康检查、依赖顺序。

4. **Nginx Beginner's Guide**
   https://nginx.org/en/docs/beginners_guide.html
   - 反向代理、静态文件、`proxy_pass`、日志。

5. **systemd Service**
   https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
   - `ExecStart`、`Restart`、`EnvironmentFile`、安全选项。

### GitHub 参考

1. **fastapi/full-stack-fastapi-template**
   https://github.com/fastapi/full-stack-fastapi-template
   - 官方模板；看配置、测试、Alembic、Docker Compose、PostgreSQL。

2. **docker/awesome-compose**
   https://github.com/docker/awesome-compose
   - 看 FastAPI + PostgreSQL、Nginx、Traefik 等 Compose 组合。

3. **zhanymkanov/fastapi-best-practices**
   https://github.com/zhanymkanov/fastapi-best-practices
   - 看项目结构、异步、依赖注入、Alembic、测试。

### 部署方向的书

- **The Linux Command Line**（William Shotts，免费在线）：shell、权限、进程、日志。
- **Docker Deep Dive**（Nigel Poulton）：镜像、容器、网络、卷、Compose。
- **Site Reliability Engineering**（Google，免费在线）：SLO、监控、告警、故障处理。
- **Designing Data-Intensive Applications**（Martin Kleppmann）：数据库、复制、分区、可靠性；长期读，不要一开始啃完。

## 4. 和当前项目结合的 14 天路线

### 第 1–2 天：概念

- 读 Anthropic 文章和 OpenAI Agents 指南；
- 写一页笔记：workflow、RAG、agent 的区别；
- 用当前项目举例：哪些是 workflow，哪些未来会成为 agent 状态。

### 第 3–4 天：单 Agent 基础

- 读 PydanticAI 和 OpenAI Agents SDK 的 tools 部分；
- 不引入框架，先在 FastAPI 中定义三个工具：
  - `retrieve_chunks(document_id, query)`
  - `generate_question(document_id, focus)`
  - `grade_answer(question_id, user_answer)`
- 所有工具只接受 JSON 参数，服务端校验资源归属。

### 第 5–7 天：有状态学习会话

- 建 `study_sessions` 和 `session_events`；
- 状态机：`created → diagnosing → questioning → grading → deciding → completed`；
- 最多 5 轮；
- 每轮保存题目、答案、分数、薄弱点和下一步动作；
- 刷新页面或重启服务后能继续。

### 第 8–9 天：评估

- 准备 20 条黄金样本：资料片段、问题、参考答案、rubric、人工评分；
- 统计结构化输出通过率、引用命中率、批改一致性、平均延迟；
- 失败样本单独记录，不要只看成功截图。

### 第 10–12 天：部署升级

- 用 Docker Compose 跑 FastAPI + PostgreSQL；
- 保留 Nginx 或改用 Caddy/Traefik 做反向代理；
- 前端、后端、数据库分别配置健康检查；
- 用环境变量管理密钥，不把 `.env` 打进镜像；
- 写清楚迁移、备份、回滚和日志查看步骤。

### 第 13–14 天：CI/CD 与面试表达

- GitHub Actions：lint + pytest + 镜像构建；
- 部署前自动测试，部署后访问 `/health`；
- 准备 3 分钟讲解：业务 → 架构 → 难点 → 边界 → 下一步；
- 明确说“已实现”和“计划中”，不要用多 Agent 包装单 Agent。

## 5. 学习时的取舍

### 现在不要做

- 不要先学微调；
- 不要一开始上多 Agent；
- 不要为了简历堆 Kafka、K8s、向量数据库；
- 不要把 LangChain/LangGraph 的 API 当知识点；
- 不要在没有评估集的情况下宣称“批改准确”。

### 现在最值得做

- 状态持久化；
- 工具参数校验；
- 失败重试和超时；
- 引用来源；
- 人工确认；
- 评估集；
- 部署、日志、备份；
- 能诚实讲清边界。

## 6. 面试时的一句话总结

> 我先把 AI 能力做成受控 workflow，再用数据库持久化会话状态，逐步引入工具调用和有限轮次 Agent Loop。每一步都有结构化输出、权限校验、失败处理和评估指标，而不是把业务全部交给模型自由发挥。
