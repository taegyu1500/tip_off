from .io import config_paths, ensure_dir, read_yaml, backup, restore_backup, dump_effective_log, FileLock
from .merge import merge_layers, env_layer
from .schema import AppConfig
from .cli import cli_layer
from app.ui.onboarding_tk import run_onboarding_tk

def load_effective_config() -> AppConfig:
    path, bak, lock = config_paths()
    ensure_dir(path.parent)

    file_cfg = {}
    if not path.exists():
        # 첫 실행: 온보딩으로 파일 생성
        model = run_onboarding_tk()
        if model is None:
            raise SystemExit("온보딩이 취소되었습니다.")
        # 온보딩 결과를 '파일 레이어'로 사용(여기서 바로 병합)
        file_cfg = model.model_dump()
    else:
        # 기존 파일 로드(손상 시 복구 시도)
        with FileLock(lock):
            try:
                file_cfg = read_yaml(path)
            except Exception:
                if restore_backup(path, bak):
                    file_cfg = read_yaml(path)
                else:
                    file_cfg = {}

    # 최종 병합: 파일 < ENV < CLI
    merged = merge_layers(file_cfg, env_layer(), cli_layer())
    model = AppConfig(**merged)

    # 백업 최신화 (파일이 있을 때만)
    if path.exists():
        backup(path, bak)

    # 시작 로그(민감정보 제외는 dump_effective_log가 처리)
    dump_effective_log(model.model_dump())
    return model
