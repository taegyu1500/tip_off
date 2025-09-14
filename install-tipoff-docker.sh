#!/usr/bin/env bash
set -euo pipefail
IMAGE="${1:-tipoff:latest}"
DESK="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
APPS="$HOME/.local/share/applications"
APPDIR="$HOME/tipoff"
mkdir -p "$DESK" "$APPS" "$APPDIR" "$HOME/.tipoff"
cat > "$APPDIR/run-tipoff-gui.sh" <<'RUN'
#!/usr/bin/env bash
set -euo pipefail
IMG="${IMAGE:-tipoff:latest}"
mkdir -p "$HOME/.tipoff"
xhost +local: >/dev/null 2>&1 || true
exec docker run --rm -it \
  --name tipoff \
  --network=host \
  -e TZ="${TZ:-Asia/Seoul}" \
  -e DISPLAY="${DISPLAY}" \
  -e HEADLESS=false \
  -v "$HOME/.tipoff:/home/appuser/.tipoff" \
  -v /tmp/.X11-unix:/tmp/.X11-unix:ro \
  "$IMG" \
  "$@"
RUN
chmod +x "$APPDIR/run-tipoff-gui.sh"

cat > "$DESK/TIP-OFF (Docker).desktop" <<DESK
[Desktop Entry]
Type=Application
Name=TIP-OFF (Docker)
Comment=LAN chat (containerized)
Exec=/usr/bin/env bash -lc 'IMAGE="$IMAGE" "$HOME/tipoff/run-tipoff-gui.sh"'
Icon=utilities-terminal
Terminal=false
Categories=Network;Chat;
DESK
cp "$DESK/TIP-OFF (Docker).desktop" "$APPS/TIP-OFF (Docker).desktop"
chmod +x "$DESK/TIP-OFF (Docker).desktop" "$APPS/TIP-OFF (Docker).desktop"
if command -v gio >/dev/null 2>&1; then
  gio set "$DESK/TIP-OFF (Docker).desktop" metadata::trusted true || true
fi
if ! command -v docker >/dev/null 2>&1; then
  echo "⚠️  Docker가 설치되어 있지 않습니다. 설치 후 다시 실행하세요." >&2
  exit 1
fi
docker pull "$IMAGE" || true
echo "✅ 설치 완료 — 바탕화면 아이콘 더블클릭으로 실행하세요."
