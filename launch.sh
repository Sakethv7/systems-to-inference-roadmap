#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"
if ! docker info >/dev/null 2>&1; then
  printf 'Docker Desktop is not running yet. Open Docker Desktop, wait until it says running, then run this script again.\n' >&2
  exit 1
fi
docker compose up -d --build
docker compose ps
printf '\nOpen http://127.0.0.1:${LEARNING_PORT:-8768}/\n'
