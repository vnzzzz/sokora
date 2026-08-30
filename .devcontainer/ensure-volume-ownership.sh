#!/usr/bin/env bash
set -Eeuo pipefail

uid=$(id -u)
gid=$(id -g)

ensure_owned_by_remote_user() {
  local path=$1
  local owner

  sudo mkdir -p "$path"
  owner=$(stat -c '%u:%g' "$path")
  if [[ "$owner" != "$uid:$gid" ]]; then
    sudo chown -R "$uid:$gid" "$path"
  fi
}

ensure_owned_by_remote_user /app/data
ensure_owned_by_remote_user /home/vscode/.cache/pypoetry
