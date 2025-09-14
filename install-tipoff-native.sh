#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_PY_MODULE="app.main"
APP_DATA_DIR="$HOME/.tipoff"
VENV_DIR="$HOME/.local/share/tipoff/venv"
BIN_DIR="$HOME/bin"
RUNNER="$BIN_DIR/run-tipoff-native.sh"
DESKTOP="$HOME/Desktop/TIP-OFF.desktop"

# 1) 필수 패키지 설치 (Ubuntu)
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y \
    python3 python3-venv python3-pip python3-tk \
    fonts-noto-cjk fonts-nanum \
    ibus x11-xserver-utils locales
  # ko_KR.UTF-8 로케일 생성/적용
  if ! locale -a | grep -qi 'ko_KR\.utf8'; then
    sudo sed -i 's/^# *\(ko_KR\.UTF-8 UTF-8\)/\1/' /etc/locale.gen
    sudo locale-gen
    sudo update-locale LANG=ko_KR.UTF-8 LC_ALL=ko_KR.UTF-8
  fi
else
  echo "※ 이 스크립트는 Ubuntu/apt 환경을 가정합니다. 다른 배포판은 의존성 수동 설치가 필요합니다." >&2
fi

# 2) 가상환경 준비
mkdir -p "$(dirname "$VENV_DIR")"
[ -d "$VENV_DIR" ] || python3 -m venv "$VENV_DIR"
# shellcheck disable=SC1091
. "$VENV_DIR/bin/activate"
pip install --upgrade pip
[ -f "$REPO_DIR/requirements.txt" ] && pip install -r "$REPO_DIR/requirements.txt"

# 3) 사용자 데이터 디렉토리
mkdir -p "$APP_DATA_DIR"

# 4) 실행기 생성 (레포로 cd + PYTHONPATH 설정 포함, 한글 표시/입력 지원)
mkdir -p "$BIN_DIR"
cat > "$RUNNER" <<'RS'
#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$HOME/tip_off"
cd "$REPO_DIR"
export PYTHONPATH="$REPO_DIR:${PYTHONPATH:-}"

# X 접근 완화(조용히 실패 무시)
command -v xhost >/dev/null 2>&1 && xhost +local: >/dev/null 2>&1 || true

# 한글 표시/입력 환경
export LANG="${LANG:-ko_KR.UTF-8}"
export LC_ALL="${LC_ALL:-ko_KR.UTF-8}"
export XMODIFIERS='@im=ibus'
export GTK_IM_MODULE=ibus
export QT_IM_MODULE=ibus

# venv 활성화
VENV_DIR="$HOME/.local/share/tipoff/venv"
# shellcheck disable=SC1091
. "$VENV_DIR/bin/activate"

# (옵션) 실행 전 자동 업데이트 하고 싶으면 아래 주석 해제
# git -C "$HOME/tip_off" pull --ff-only >/dev/null 2>&1 || true

# 앱 실행 (Tk GUI)
exec python -m app.main
RS
chmod +x "$RUNNER"

# 5) 바탕화면 아이콘 생성
mkdir -p "$(dirname "$DESKTOP")"
cat > "$DESKTOP" <<DESK
[Desktop Entry]
Type=Application
Name=TIP-OFF (Native)
Comment=Run TIP-OFF (no Docker)
Exec=$RUNNER
Icon=utilities-terminal
Terminal=true
Categories=Utility;
StartupNotify=false
DESK
chmod +x "$DESKTOP"
gio set "$DESKTOP" metadata::trusted true 2>/dev/null || true

echo "✅ TIP-OFF 네이티브 설치 완료!"
echo " - 실행기: $RUNNER"
echo " - 아이콘 : $DESKTOP"
echo "바탕화면 아이콘을 더블클릭해 실행하세요."
