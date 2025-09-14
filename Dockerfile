FROM python:3.11-slim

# 런타임 패키지: Tk, Xvfb(헤드리스 GUI), tzdata(시간대)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-tk xvfb tzdata \
 && rm -rf /var/lib/apt/lists/*

# 앱 사용자
RUN useradd -m -u 1000 appuser
ENV HOME=/home/appuser
WORKDIR /app

# 소스 복사
COPY app/ /app/app/

# 파이썬 의존성
RUN python -m pip install -U pip wheel && \
    python -m pip install -r /app/app/requirements.txt

# 설정 디렉토리 (호스트의 ~/.tipoff를 여기에 마운트합니다)
RUN mkdir -p /home/appuser/.tipoff && chown -R appuser:appuser /home/appuser
VOLUME ["/home/appuser/.tipoff"]

# UDP 포트(문서화용)
EXPOSE 5000/udp 5001/udp 5002/udp

# 엔트리포인트: 기본은 헤드리스(Xvfb)로 실행
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
USER appuser
ENTRYPOINT ["/entrypoint.sh"]
# CLI 플래그 전달 가능: docker run ... -- --broadcast-ip 192.168.1.255
CMD []
