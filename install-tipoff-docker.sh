#!/usr/bin/env bash
set -euo pipefail

IMAGE="${1:-docker.io/gksruf123/tipoff:latest}"
USER_BIN="$HOME/bin"
LAUNCHER="$USER_BIN/run-tipoff.sh"
DESKTOP="$HOME/Desktop/TIP-OFF.desktop"

mkdir -p "$USER_BIN"

# 실행 스크립트 생성 (한글 입력/표시 대응 포함)
cat > "$LAUNCHER" <<'INNER'
#!/usr/bin/env bash
set -euo pipefail
xhost +local: >/dev/null 2>&1 || true

UID_CUR=$(id -u)

EXTRA_ENV=()
EXTRA_MOUNTS=()

if [ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
  EXTRA_ENV+=(-e DBUS_SESSION_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS")
  EXTRA_MOUNTS+=(-v "/run/user/${UID_CUR}:/run/user/${UID_CUR}")
fi

exec docker run --rm -it \
  --net=host \
  -e DISPLAY="${DISPLAY:-:0}" \
  -e LANG="ko_KR.UTF-8" \
  -e LC_ALL="ko_KR.UTF-8" \
  -e XMODIFIERS='@im=ibus' \
  -e GTK_IM_MODULE=ibus \
  -e QT_IM_MODULE=ibus \
  "${EXTRA_ENV[@]}" \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v "$HOME/.tipoff:/home/appuser/.tipoff" \
  "${EXTRA_MOUNTS[@]}" \
  --name tipoff \
  __IMAGE_PLACEHOLDER__
INNER

# 이미지 이름 주입
sed -i "s|__IMAGE_PLACEHOLDER__|$IMAGE|g" "$LAUNCHER"
chmod +x "$LAUNCHER"

# .desktop 아이콘 생성
mkdir -p "$HOME/Desktop"
cat > "$DESKTOP" <<DESK
[Desktop Entry]
Type=Application
Name=TIP-OFF (Docker)
Comment=Run TIP-OFF
Exec=$LAUNCHER
Icon=utilities-terminal
Terminal=true
Categories=Utility;
StartupNotify=false
DESK

chmod +x "$DESKTOP"
gio set "$DESKTOP" metadata::trusted true 2>/dev/null || true

echo "✅ TIP-OFF 설치 완료!"
echo " - 런처: $LAUNCHER"
echo " - 아이콘: $DESKTOP"
echo "이제 바탕화면 아이콘을 더블클릭하면 TIP-OFF가 실행됩니다."
