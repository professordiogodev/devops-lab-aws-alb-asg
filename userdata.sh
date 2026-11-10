#!/bin/bash
# First boot of every server in the group: install and start Clippy on port 80. Provided: not the point of the lab.
# /healthz reports APP_VERSION, and we set it to the instance id so you can SEE which server answers.
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -y && apt-get install -y python3-venv git
id clippy >/dev/null 2>&1 || useradd --system --home /opt/clippy --shell /usr/sbin/nologin clippy
git clone --branch v0.2.0 --depth 1 https://github.com/professordiogodev/clippy /opt/clippy
python3 -m venv /opt/clippy/.venv && /opt/clippy/.venv/bin/pip install -q -r /opt/clippy/requirements.txt
chown -R clippy:clippy /opt/clippy
TOKEN=$(curl -s -X PUT http://169.254.169.254/latest/api/token -H 'X-aws-ec2-metadata-token-ttl-seconds: 60')
ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
cat > /etc/systemd/system/clippy.service <<UNIT
[Unit]
Description=Clippy
After=network-online.target
[Service]
User=clippy
WorkingDirectory=/opt/clippy
Environment=APP_VERSION=$ID
ExecStart=/opt/clippy/.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 80
AmbientCapabilities=CAP_NET_BIND_SERVICE
Restart=on-failure
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload && systemctl enable --now clippy
