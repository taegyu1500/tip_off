#!/usr/bin/env bash
set -euo pipefail

IMAGE="${1:-docker.io/gksruf123/tipoff:latest}"
USER_BIN="$HOME/bin"
LAUNCHER="$USER_BIN/run-tipoff.sh"
DESKTOP="$HOME/Desktop/TIP-OFF.desktop"

mkdir -p "$USER_BIN"

# 실행 스크립트 생성 (X11 바인딩 + 설정 볼륨)
cat > "$LAUNCHER" <<'INNER'
#!/usr/bin/env bash
set -euo pipefail
# X 접근 느슨히 허용(조용히 실패 무시)
xhost +local: >/dev/null 2>&1 || true

# 이미지 이름은 런처가 만들어질 때 주입됨
IMAGE_PLACEHOLDER="__TO_BE_REPLACED__"

exec docker run --rm -it \
  --net=host \
  -e DISPLAY="${DISPLAY:-:0}" \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v "$HOME/.tipoff:/home/appuser/.tipoff" \
  --name tipoff \
  "$IMAGE_PLACEHOLDER"
INNER

# 이미지 이름 주입
sed -i "s|__TO_BE_REPLACED__|$IMAGE|g" "$LAUNCHER"
chmod +x "$LAUNCHER"

# .desktop 아이콘 생성 (터미널 열어서 로그 보이게)
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

# GNOME/우분투에서 신뢰 설정(있으면 적용, 없어도 무시)
gio set "$DESKTOP" metadata::trusted true 2>/dev/null || true

echo "✅ 설치 완료"
echo " - 런처: $LAUNCHER"
echo " - 아이콘: $DESKTOP"
echo "이제 바탕화면 아이콘을 더블클릭해 실행하세요."
