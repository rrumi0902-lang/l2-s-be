# EchoFusion RunPod Deployment

개선된 EchoFusion 파이프라인을 RunPod에 배포하기 위한 파일들입니다.

## 주요 개선 사항

### 1. VAD (Voice Activity Detection) 통합
- 실제 사람 목소리가 있는지 먼저 판단
- Whisper 환각 현상 방지
- 음성이 없는 영상(풍경, 음악 비디오 등)에서도 안정적 동작

### 2. Fallback 로직
- TXT 브랜치 실패 시 HD 브랜치만으로 처리
- 서버 다운 없이 안정적으로 결과 반환
- 처리 방법을 Webhook에 포함하여 프론트엔드에 알림

### 3. 안전한 예외 처리
- 빈 타임스탬프 방지
- LLM 실패 시에도 시각적 특징으로 대체
- 모든 에러를 Webhook으로 전달

### 4. 멀티모달 융합 강화
- HD (모션, 음량, CLIP) + TXT (LLM) 점수 결합
- 논문의 원리를 충실히 구현

## 파일 구조

```
runpod_deployment/
├── handler.py              # 메인 RunPod 핸들러
├── requirements.txt        # Python 의존성
└── README.md              # 이 파일
```

## 환경 변수 설정

RunPod 환경 변수에 다음을 추가하세요:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

## 배포 방법

### 1. RunPod 템플릿 생성

```bash
# Docker 이미지 빌드
docker build -t echofusion:latest .

# Docker Hub에 푸시
docker tag echofusion:latest yourdockerhub/echofusion:latest
docker push yourdockerhub/echofusion:latest
```

### 2. RunPod에서 설정

1. **Serverless Endpoints** → **New Endpoint**
2. Container Image: `yourdockerhub/echofusion:latest`
3. GPU Type: NVIDIA A40 이상 권장
4. Environment Variables에 `GEMINI_API_KEY` 추가

### 3. 테스트

```python
import requests

response = requests.post(
    "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run",
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {RUNPOD_API_KEY}"
    },
    json={
        "input": {
            "webhook_url": "https://your-backend.vercel.app/runpod/webhook/123",
            "task": "process_video",
            "video_url": "https://example.com/video.mp4",
            "options": {
                "method": "echofusion",
                "subtitles": True,
                "vertical": False,
                "target_duration": 60
            }
        }
    }
)

print(response.json())
```

## Webhook 응답 형식

### 성공 (멀티모달)
```json
{
  "status": "completed",
  "result_url": "https://storage.../result.mp4",
  "processing_method": "multimodal",
  "message": "Successfully generated highlights using multimodal fusion",
  "metadata": {
    "scene_count": 45,
    "selected_count": 8,
    "vad_speech_ratio": 0.65,
    "vad_energy_db": -25.3
  }
}
```

### 부분 성공 (시각적 특징만)
```json
{
  "status": "completed",
  "result_url": "https://storage.../result.mp4",
  "processing_method": "visual_only",
  "message": "Generated highlights using visual features only",
  "metadata": {
    "scene_count": 30,
    "selected_count": 6,
    "vad_speech_ratio": 0.05,
    "vad_energy_db": -55.2
  }
}
```

### 실패
```json
{
  "status": "failed",
  "error": "Error message here",
  "processing_method": "error"
}
```

## 로컬 테스트

```bash
# 의존성 설치
pip install -r requirements.txt

# FFmpeg 설치 (필수)
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# 환경 변수 설정
export GEMINI_API_KEY=your_key_here

# 테스트 실행
python handler.py
```

## 문제 해결

### VAD가 작동하지 않음
- `librosa` 설치 확인: `pip install librosa soundfile`
- FFmpeg 설치 확인: `ffmpeg -version`

### Whisper 환각 감지
- 로그에서 `"Hallucination detected"` 메시지 확인
- VAD 임계값 조정: `VoiceActivityDetector(threshold_db=-45.0)`

### LLM 타임아웃
- Gemini API 키 확인
- 네트워크 연결 확인
- Fallback이 자동으로 작동하여 HD만으로 처리됨

## 성능 최적화

### GPU 활용
- CUDA 사용 가능 시 자동으로 GPU 사용
- Whisper: `device="cuda"`, `compute_type="float16"`
- CLIP: 자동으로 GPU 감지

### 메모리 최적화
- 키프레임 추출 시 1 FPS로 제한
- 영상을 장면 단위로 분할 처리
- 사용 후 OpenCV VideoCapture 릴리즈

## 참고 자료

- [EchoFusion 논문](../shortcake/EchoFusion%20-%20멀티모달%20영상%20특징%20기반%20하이라이트%20추출%20및%20요약%20자동화%20(최종).pdf)
- [RunPod 문서](https://docs.runpod.io/)
- [Whisper 문서](https://github.com/openai/whisper)
- [CLIP 문서](https://github.com/openai/CLIP)
