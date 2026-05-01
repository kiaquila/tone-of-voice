#!/usr/bin/env bash

set -euo pipefail

TARGET_DIR="${TARGET_DIR:?TARGET_DIR is required}"
RELEASE_SHA="${RELEASE_SHA:?RELEASE_SHA is required}"
RELEASE_SOURCE_DIR="${RELEASE_SOURCE_DIR:-$(pwd)}"
SERVICE_NAME="${SERVICE_NAME:-tone-of-voice-telegram-bot}"
SERVICE_USER="${SERVICE_USER:-ubuntu}"
SERVICE_GROUP="${SERVICE_GROUP:-${SERVICE_USER}}"
BOT_ENV_FILE="${BOT_ENV_FILE:-}"
BOT_ALLOWED_CHAT_IDS="${BOT_ALLOWED_CHAT_IDS:-}"
BOT_SESSION_DIR="${BOT_SESSION_DIR:-${TARGET_DIR}/sessions}"
BOT_OUTPUT_DIR="${BOT_OUTPUT_DIR:-${TARGET_DIR}/data/bot}"
DEPLOY_METADATA_DIR="${TARGET_DIR}/.deploy"
LOCK_FILE="/tmp/tone-of-voice-deploy.lock"

run_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  else
    sudo "$@"
  fi
}

ensure_target_dir() {
  if [ ! -d "${TARGET_DIR}" ]; then
    if ! mkdir -p "${TARGET_DIR}" 2>/dev/null; then
      run_root mkdir -p "${TARGET_DIR}"
      run_root chown "${SERVICE_USER}:${SERVICE_GROUP}" "${TARGET_DIR}"
    fi
  fi

  if [ ! -w "${TARGET_DIR}" ]; then
    run_root chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${TARGET_DIR}"
  fi
}

stop_existing_bot() {
  run_root systemctl stop "${SERVICE_NAME}" 2>/dev/null || true

  mapfile -t pids < <(
    pgrep -af "run_telegram_bot.py" \
      | awk '/tone-of-voice/ {print $1}' \
      | sort -u
  )

  if [ "${#pids[@]}" -eq 0 ]; then
    return
  fi

  for pid in "${pids[@]}"; do
    if [ "$pid" != "$$" ]; then
      run_root kill "$pid" 2>/dev/null || true
    fi
  done

  sleep 2

  for pid in "${pids[@]}"; do
    if [ "$pid" != "$$" ] && kill -0 "$pid" 2>/dev/null; then
      run_root kill -9 "$pid" 2>/dev/null || true
    fi
  done
}

write_systemd_unit() {
  local unit_path="/etc/systemd/system/${SERVICE_NAME}.service"
  local env_file="${BOT_ENV_FILE}"
  local allowed_env_line=""
  local tmp_unit
  tmp_unit="$(mktemp)"

  if [ -z "${env_file}" ]; then
    env_file="${TARGET_DIR}/.env"
  fi

  if [ -n "${BOT_ALLOWED_CHAT_IDS}" ]; then
    allowed_env_line="Environment=TONE_OF_VOICE_BOT_ALLOWED_CHAT_IDS=${BOT_ALLOWED_CHAT_IDS}"
  fi

  cat > "${tmp_unit}" <<EOF
[Unit]
Description=tone-of-voice Telegram drafting bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${TARGET_DIR}
EnvironmentFile=${env_file}
${allowed_env_line}
ExecStart=${TARGET_DIR}/.venv/bin/python scripts/run_telegram_bot.py --env-file ${env_file} --session-dir ${BOT_SESSION_DIR} --output-dir ${BOT_OUTPUT_DIR}
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

  run_root install -m 0644 "${tmp_unit}" "${unit_path}"
  rm -f "${tmp_unit}"
}

exec 9>"${LOCK_FILE}"
flock 9

ensure_target_dir
stop_existing_bot

rsync -a --delete \
  --exclude ".env" \
  --exclude ".venv/" \
  --exclude "data/" \
  --exclude "logs/" \
  --exclude "*.session" \
  --exclude "*.session-journal" \
  --exclude ".deploy/" \
  --exclude ".git/" \
  "${RELEASE_SOURCE_DIR}/" "${TARGET_DIR}/"

mkdir -p "${TARGET_DIR}/logs" "${BOT_SESSION_DIR}" "${BOT_OUTPUT_DIR}" "${DEPLOY_METADATA_DIR}"

if [ ! -x "${TARGET_DIR}/.venv/bin/python" ]; then
  python3 -m venv "${TARGET_DIR}/.venv"
fi

"${TARGET_DIR}/.venv/bin/python" -m pip install --upgrade pip
"${TARGET_DIR}/.venv/bin/python" -m pip install -e "${TARGET_DIR}"
"${TARGET_DIR}/.venv/bin/python" -m py_compile \
  "${TARGET_DIR}"/scripts/*.py \
  "${TARGET_DIR}"/src/tone_of_voice/*.py

write_systemd_unit
run_root systemctl daemon-reload
run_root systemctl enable "${SERVICE_NAME}"
run_root systemctl restart "${SERVICE_NAME}"

DEPLOY_METADATA_DIR="${DEPLOY_METADATA_DIR}" \
RELEASE_SHA="${RELEASE_SHA}" \
SERVICE_NAME="${SERVICE_NAME}" \
TARGET_DIR="${TARGET_DIR}" \
BOT_ENV_FILE="${BOT_ENV_FILE}" \
BOT_SESSION_DIR="${BOT_SESSION_DIR}" \
BOT_OUTPUT_DIR="${BOT_OUTPUT_DIR}" \
python3 - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

metadata_path = Path(os.environ["DEPLOY_METADATA_DIR"]) / "current_release.json"
metadata = {
    "release_sha": os.environ["RELEASE_SHA"],
    "deployed_at_utc": datetime.now(timezone.utc).isoformat(),
    "target_dir": os.environ["TARGET_DIR"],
    "service_name": os.environ["SERVICE_NAME"],
    "bot_env_file": os.environ["BOT_ENV_FILE"],
    "bot_session_dir": os.environ["BOT_SESSION_DIR"],
    "bot_output_dir": os.environ["BOT_OUTPUT_DIR"],
}
metadata_path.write_text(json.dumps(metadata, ensure_ascii=True, indent=2) + "\n")
PY

run_root systemctl --no-pager --full status "${SERVICE_NAME}"

echo "Deployed ${RELEASE_SHA} to ${TARGET_DIR} and restarted ${SERVICE_NAME}"
