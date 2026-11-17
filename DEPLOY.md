# 部署说明（Ubuntu 22.04）

目标服务器：`your-server-ip-or-domain`

## 架构

```text
浏览器 / Swagger
        ↓ :80
      Nginx
        ↓ 127.0.0.1:8000
   Uvicorn + FastAPI
        ↓
  SQLite (/var/lib/learning-assistant/app.db)
```

## 首次部署

把项目上传到服务器后，在项目目录执行：

```bash
sudo bash deploy/bootstrap.sh
```

脚本会完成：

- 安装 Python、venv、Nginx
- 创建虚拟环境并安装依赖
- 生成 `.env` 和随机 `SECRET_KEY`
- 在 `/var/lib/learning-assistant/app.db` 执行 Alembic 迁移
- 安装并启动 systemd 服务
- 安装 Nginx 反向代理并启用 80 端口

## 验证

```bash
systemctl status learning-assistant --no-pager
curl http://127.0.0.1:8000/health
curl -I http://127.0.0.1/
sudo nginx -t
```

公网访问：

```text
http://your-server-ip-or-domain/docs
```

## 更新

上传新代码后：

```bash
cd /opt/learning-assistant
sudo -u www-data env $(cat .env | xargs) .venv/bin/alembic upgrade head
sudo systemctl restart learning-assistant
sudo systemctl reload nginx
```

## 日志

```bash
journalctl -u learning-assistant -f
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## 注意

- 不要把 `.env` 提交到 Git
- `SECRET_KEY` 必须使用随机值，不能沿用开发默认值
- 当前使用 SQLite，适合 MVP 演示；后续可切 PostgreSQL
- 阿里云安全组需放行 `80/443`，SSH `22` 建议只对自己 IP 开放
