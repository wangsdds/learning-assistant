#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/opt/learning-assistant
DATA_DIR=/var/lib/learning-assistant

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip nginx

mkdir -p "$APP_DIR" "$DATA_DIR"
chown -R www-data:www-data "$DATA_DIR"

if [ ! -x "$APP_DIR/.venv/bin/python" ]; then
    python3 -m venv "$APP_DIR/.venv"
fi

"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

if [ ! -f "$APP_DIR/.env" ]; then
    secret=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')
    cat > "$APP_DIR/.env" <<EOF
SECRET_KEY=$secret
DATABASE_URL=sqlite:////var/lib/learning-assistant/app.db
PYTHONUNBUFFERED=1
EOF
    chown root:www-data "$APP_DIR/.env"
    chmod 640 "$APP_DIR/.env"
fi

set -a
. "$APP_DIR/.env"
set +a

runuser -u www-data -- env SECRET_KEY="$SECRET_KEY" DATABASE_URL="$DATABASE_URL" \
    sh -c "cd '$APP_DIR' && .venv/bin/alembic upgrade head"

install -m 644 "$APP_DIR/deploy/learning-assistant.service" \
    /etc/systemd/system/learning-assistant.service
systemctl daemon-reload
systemctl enable --now learning-assistant.service

install -m 644 "$APP_DIR/deploy/nginx.conf" \
    /etc/nginx/sites-available/learning-assistant
ln -sfn /etc/nginx/sites-available/learning-assistant \
    /etc/nginx/sites-enabled/learning-assistant
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable --now nginx
systemctl reload nginx

echo "Deployment complete"
echo "Service: $(systemctl is-active learning-assistant)"
echo "Nginx:   $(systemctl is-active nginx)"
echo "Health:  http://127.0.0.1:8000/health"
