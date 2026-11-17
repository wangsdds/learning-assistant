# -*- coding: utf-8 -*-
"""FastAPI 入口：路由 + HTTP 层。"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.routers import answers, documents, plan_days, questions, users

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="学习助手",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)
app.include_router(documents.router)
app.include_router(questions.router)
app.include_router(answers.router)
app.include_router(plan_days.router)
app.include_router(users.router)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/ui", StaticFiles(directory=BASE_DIR / "static" / "ui", html=True), name="ui")


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse(url="/ui/")


@app.get("/docs", include_in_schema=False)
def swagger_ui():
    return HTMLResponse(
        """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="/static/swagger/swagger-ui.css">
    <link rel="shortcut icon" href="/static/swagger/favicon-32x32.png">
    <title>学习助手 - API 文档</title>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="/static/swagger/swagger-ui-bundle.js"></script>
    <script src="/static/swagger/swagger-ui-standalone-preset.js"></script>
    <script>
        window.ui = SwaggerUIBundle({
            url: "/openapi.json",
            dom_id: "#swagger-ui",
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIStandalonePreset
            ],
            layout: "BaseLayout",
            deepLinking: true,
            persistAuthorization: true,
            tryItOutEnabled: true,
            filter: true
        });
    </script>
</body>
</html>
        """
    )


@app.get("/health")
def health():
    return {"status": "ok"}
