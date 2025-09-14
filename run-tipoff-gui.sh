#!/usr/bin/env bash
set -euo pipefail

IMAGE="${IMAGE:-tipoff:latest}"
mkdir -p "$HOME/.tipoff"

# 호스트 X 서버에 "로컬 클라이언트" 접속 허용 (한 번만 필요, 실패해도 무시)
xhost +local: >/dev/null 2>&1 || true

exec docker run --rm -it \
  --name tipoff \
  --network=host \
  -e TZ="${TZ:-Asia/Seoul}" \
  -e DISPLAY="${DISPLAY}" \
  -e HEADLESS=false \
  -v "$HOME/.tipoff:/home/appuser/.tipoff" \
  -v /tmp/.X11-unix:/tmp/.X11-unix:ro \
  "$IMAGE" \
  "$@"
