#!/usr/bin/env bash
set -euo pipefail

# setup_deploy.sh
# Deploy license server to /root/tools/license_server, create venv, install deps,
# generate ADMIN_TOKEN, install systemd service and optionally configure nginx+certbot.

TARGET_DIR=/root/tools/license_server
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

usage(){
  cat <<EOF
Usage: $0 [--yes] [--token TOKEN] [--with-nginx --domain example.com --email admin@example.com]
  --yes         : run non-interactive (assume yes)
  --token TOKEN : use provided ADMIN_TOKEN
  --with-nginx  : install nginx and attempt Let's Encrypt (requires --domain and --email)
  --domain NAME : domain name for certbot
  --email ADDR  : email for certbot
EOF
  exit 1
}

CONFIRM=yes
ADMIN_TOKEN=""
WITH_NGINX=0
DOMAIN=""
EMAIL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes) CONFIRM=yes; shift;;
    --token) ADMIN_TOKEN="$2"; shift 2;;
    --with-nginx) WITH_NGINX=1; shift;;
    --domain) DOMAIN="$2"; shift 2;;
    --email) EMAIL="$2"; shift 2;;
    -h|--help) usage;;
    *) echo "Unknown arg: $1"; usage;;
  esac
done

if [[ $EUID -ne 0 ]]; then
  echo "This script must be run as root. Use sudo." >&2
  exit 1
fi

if [[ $WITH_NGINX -eq 1 && -z "$DOMAIN" ]]; then
  echo "--with-nginx requires --domain" >&2; exit 1
fi

echo "Deploying license server to $TARGET_DIR"
if [[ ! "$CONFIRM" == "yes" ]]; then
  read -p "Proceed? [y/N] " ok
  [[ "$ok" == "y" || "$ok" == "Y" ]] || exit 1
fi

# copy files
rm -rf "$TARGET_DIR.tmp"
mkdir -p "$TARGET_DIR.tmp"
rsync -a --delete "$SRC_DIR/" "$TARGET_DIR.tmp/"
mkdir -p "$(dirname "$TARGET_DIR")"
rm -rf "$TARGET_DIR.bak" || true
if [[ -d "$TARGET_DIR" ]]; then mv "$TARGET_DIR" "$TARGET_DIR.bak"; fi
mv "$TARGET_DIR.tmp" "$TARGET_DIR"
chown -R root:root "$TARGET_DIR"

cd "$TARGET_DIR"

# create venv
if [[ ! -d "$TARGET_DIR/venv" ]]; then
  python3 -m venv "$TARGET_DIR/venv"
fi
source "$TARGET_DIR/venv/bin/activate"
pip install --upgrade pip
if [[ -f requirements.txt ]]; then
  pip install -r requirements.txt
fi

# generate ADMIN_TOKEN if not provided
if [[ -z "$ADMIN_TOKEN" ]]; then
  ADMIN_TOKEN=$(openssl rand -hex 24)
fi

echo "Using ADMIN_TOKEN: $ADMIN_TOKEN"

# update service file token and paths
SERVICE_FILE="$TARGET_DIR/license_server.service"
if [[ -f "$SERVICE_FILE" ]]; then
  sed -i "s|Environment=PATH=.*|Environment=PATH=${TARGET_DIR}/venv/bin|" "$SERVICE_FILE"
  sed -i "s|WorkingDirectory=.*|WorkingDirectory=${TARGET_DIR}|" "$SERVICE_FILE"
  sed -i "s|ExecStart=.*|ExecStart=${TARGET_DIR}/venv/bin/gunicorn -w 3 -b 0.0.0.0:5000 server:app|" "$SERVICE_FILE"
  sed -i "s|Environment=ADMIN_TOKEN=.*|Environment=ADMIN_TOKEN=${ADMIN_TOKEN}|" "$SERVICE_FILE" || true
else
  echo "Warning: $SERVICE_FILE missing"
fi

# install systemd unit
cp "$SERVICE_FILE" /etc/systemd/system/license_server.service
systemctl daemon-reload
systemctl enable --now license_server.service
sleep 1
systemctl status --no-pager license_server.service || true

# open firewall if ufw exists
if command -v ufw >/dev/null 2>&1; then
  if ufw status | grep -q inactive; then
    echo "ufw inactive — skipping port open"
  else
    ufw allow 5000/tcp || true
  fi
fi

echo "License server deployed and started. Admin token: $ADMIN_TOKEN"

if [[ $WITH_NGINX -eq 1 ]]; then
  echo "Installing nginx and certbot for domain $DOMAIN"
  apt-get update
  apt-get install -y nginx certbot python3-certbot-nginx

  # write nginx conf
  NCONF="/etc/nginx/sites-available/license_server"
  cat > "$NCONF" <<EOF
server {
    listen 80;
    server_name ${DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
  ln -sf "$NCONF" /etc/nginx/sites-enabled/license_server
  nginx -t && systemctl reload nginx

  if [[ -n "$EMAIL" ]]; then
    certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" || true
  else
    echo "No email provided; skipping certbot. Run: certbot --nginx -d $DOMAIN -m you@example.com"
  fi
fi

echo "Setup complete. Use the ADMIN_TOKEN above for admin API calls."
exit 0
