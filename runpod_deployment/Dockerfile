FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 핸들러 복사
COPY handler.py .

# RunPod 엔트리 포인트
CMD ["python", "-u", "handler.py"]
