#!/usr/bin/env python3
"""
TipOff 서버 실행 스크립트
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app.server.bridge import ServerBridge, ServerBridgeConfig

def main():
    print("=== TipOff 서버 시작 ===")
    
    # 서버 설정
    config = ServerBridgeConfig(
        db_path="tipoff.db",
        http_port=8080,
        udp_listen_port=5002,
        host="0.0.0.0"
    )
    
    server = ServerBridge(config)
    
    try:
        server.start()
        print("\n서버가 실행 중입니다.")
        print("- DB 파일:", config.db_path)
        print("- HTTP API:", f"http://{config.host}:{config.http_port}")
        print("- UDP 수집:", f"{config.host}:{config.udp_listen_port}")
        print("\nCtrl+C로 서버를 종료할 수 있습니다.")
        
        # 무한 대기
        while True:
            import time
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n서버를 종료합니다...")
        server.stop()
        print("서버 종료 완료")

if __name__ == "__main__":
    main()