"""
EchoFusion: Improved Video Highlight Extraction Handler for RunPod
개선 사항:
1. VAD (Voice Activity Detection) 통합 - Whisper 환각 방지
2. TXT 브랜치 실패 시 HD 브랜치만으로 Fallback
3. 빈 타임스탬프에 대한 안전한 예외 처리
4. 멀티모달 융합 강화

RunPod에 배포할 파일입니다.
"""

import os
import sys
import logging
import json
import subprocess
from typing import List, Dict, Tuple, Optional
import numpy as np
import torch
import requests
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================
# VAD (Voice Activity Detection)
# ============================================

class VoiceActivityDetector:
    """음성 활동 감지기 - Whisper 환각 방지"""

    def __init__(self, threshold_db: float = -40.0, min_speech_ratio: float = 0.1):
        self.threshold_db = threshold_db
        self.min_speech_ratio = min_speech_ratio

    def detect_speech(self, audio_path: str) -> Dict:
        """실제 사람 목소리가 있는지 감지"""
        try:
            import librosa

            y, sr = librosa.load(audio_path, sr=16000)

            rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
            rms_db = librosa.amplitude_to_db(rms, ref=np.max(rms))

            speech_frames = np.sum(rms_db > self.threshold_db)
            speech_ratio = speech_frames / len(rms_db)
            avg_energy = np.mean(rms_db)

            has_speech = speech_ratio >= self.min_speech_ratio and avg_energy > self.threshold_db

            logger.info(f"VAD - Speech: {has_speech}, Ratio: {speech_ratio:.2%}, Energy: {avg_energy:.2f}dB")

            return {
                "has_speech": has_speech,
                "speech_ratio": speech_ratio,
                "energy_db": avg_energy
            }
        except Exception as e:
            logger.error(f"VAD error: {str(e)}")
            return {"has_speech": True, "speech_ratio": 0.0, "energy_db": -60.0}

    def is_hallucination(self, transcription: List[Dict], vad_result: Dict) -> bool:
        """Whisper 환각 감지"""
        if not transcription:
            return False

        total_text = " ".join([seg.get("text", "") for seg in transcription])
        text_length = len(total_text.strip())

        # 음성 비율이 낮은데 텍스트가 많으면 환각
        if vad_result["speech_ratio"] < 0.2 and text_length > 100:
            logger.warning(f"Hallucination: low speech ({vad_result['speech_ratio']:.2%}) but long text")
            return True

        # 반복 문구 감지
        words = total_text.split()
        if len(words) > 0:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.3:
                logger.warning(f"Hallucination: high repetition ({unique_ratio:.2%})")
                return True

        return False


# ============================================
# Visual Highlight Detector (HD Branch)
# ============================================

class VisualHighlightDetector:
    """시각적 특징만으로 하이라이트 탐지"""

    def __init__(self, clip_model_name: str = "openai/clip-vit-base-patch32"):
        from transformers import CLIPProcessor, CLIPModel

        self.clip_model = CLIPModel.from_pretrained(clip_model_name)
        self.clip_processor = CLIPProcessor.from_pretrained(clip_model_name)

        self.highlight_prompts = [
            "exciting moment",
            "visually stunning scene",
            "action peak",
            "beautiful landscape",
            "dramatic moment",
            "key visual content"
        ]

    def calculate_hd_score(
        self,
        scene: Dict,
        keyframes: List[np.ndarray],
        audio_segment: np.ndarray,
        sr: int = 22050
    ) -> float:
        """HD 점수 계산 (모션 + 음량 + CLIP)"""
        try:
            motion_score = self._calculate_motion(keyframes)
            loud_score = self._calculate_loudness(audio_segment, sr)
            clip_score = self._calculate_clip_score(keyframes)

            # 가중 평균 (논문 권장)
            hd_score = 0.3 * motion_score + 0.3 * loud_score + 0.4 * clip_score

            logger.debug(f"HD - Motion: {motion_score:.3f}, Loud: {loud_score:.3f}, CLIP: {clip_score:.3f}")

            return hd_score
        except Exception as e:
            logger.error(f"HD calculation error: {str(e)}")
            return 0.0

    def _calculate_motion(self, keyframes: List[np.ndarray]) -> float:
        """모션 특징 계산"""
        if len(keyframes) < 2:
            return 0.0

        import cv2
        motion_values = []
        for i in range(len(keyframes) - 1):
            diff = cv2.absdiff(keyframes[i], keyframes[i + 1])
            motion = np.mean(diff) / 255.0
            motion_values.append(motion)

        return np.mean(motion_values) if motion_values else 0.0

    def _calculate_loudness(self, audio: np.ndarray, sr: int) -> float:
        """음량 특징 계산"""
        if audio is None or len(audio) == 0:
            return 0.0

        import librosa
        rms = librosa.feature.rms(
            y=audio,
            frame_length=int(0.025 * sr),
            hop_length=int(0.010 * sr)
        )[0]

        avg_rms = np.mean(rms)
        loud_db = librosa.amplitude_to_db([avg_rms])[0]
        loud_normalized = np.clip((loud_db + 60) / 60, 0, 1)

        return loud_normalized

    def _calculate_clip_score(self, keyframes: List[np.ndarray]) -> float:
        """CLIP 유사도 계산"""
        if not keyframes:
            return 0.0

        try:
            from PIL import Image
            import cv2

            pil_frames = [
                Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
                for f in keyframes[:5]
            ]

            inputs = self.clip_processor(
                text=self.highlight_prompts,
                images=pil_frames,
                return_tensors="pt",
                padding=True
            )

            with torch.no_grad():
                outputs = self.clip_model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)

            return probs.max().item()
        except Exception as e:
            logger.error(f"CLIP score error: {str(e)}")
            return 0.0


# ============================================
# Main EchoFusion Handler
# ============================================

class ImprovedEchoFusion:
    """개선된 EchoFusion 파이프라인"""

    # 언어별 환청 방지 프롬프트
    LANGUAGE_PROMPTS = {
        "ko": "이 영상은 한국어입니다. 한국어로 정확하게 받아적어 주세요.",
        "en": "This video is in English. Please transcribe accurately in English.",
        "ja": "この動画は日本語です。日本語で正確に書き起こしてください。",
        "zh": "这个视频是中文的。请用中文准确转录。",
        "es": "Este video está en español. Por favor, transcribe con precisión en español.",
        "auto": None,  # 자동 감지 시 프롬프트 없음
    }

    def __init__(self):
        self.vad = VoiceActivityDetector()
        self.visual_detector = VisualHighlightDetector()

        # Whisper 모델 로드
        from faster_whisper import WhisperModel
        self.whisper_model = WhisperModel(
            "large-v3",
            device="cuda" if torch.cuda.is_available() else "cpu",
            compute_type="float16" if torch.cuda.is_available() else "int8"
        )

        # Gemini API 설정
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.llm = genai.GenerativeModel('gemini-pro')
        else:
            self.llm = None
            logger.warning("Gemini API key not found, TXT branch disabled")

    def process_video(
        self,
        video_url: str,
        webhook_url: str,
        target_duration: int = 60,
        options: Dict = None
    ) -> Dict:
        """
        영상 처리 메인 함수

        Args:
            video_url: 처리할 영상 URL
            webhook_url: 결과를 보낼 Webhook URL
            target_duration: 목표 요약 길이 (초)
            options: 추가 옵션

        Returns:
            처리 결과
        """
        try:
            logger.info(f"Processing video: {video_url}")

            # 유저 선택 언어 추출 (기본값: auto)
            language = (options or {}).get("language", "auto")
            logger.info(f"User selected language: {language}")

            # 1. 영상 다운로드
            video_path = self._download_video(video_url)

            # 2. 장면 검출
            scenes = self._detect_scenes(video_path)
            logger.info(f"Detected {len(scenes)} scenes")

            # 3. 오디오 추출
            audio_path = self._extract_audio(video_path)

            # 4. VAD 실행
            vad_result = self.vad.detect_speech(audio_path)
            has_speech = vad_result["has_speech"]

            # 5. HD 점수 계산 (항상 실행)
            hd_scores = self._calculate_all_hd_scores(video_path, scenes, audio_path)

            # 6. TXT 점수 계산 (음성이 있을 때만)
            txt_scores = None
            txt_success = False
            processing_method = "unknown"
            transcription = []  # 자막 저장용

            if has_speech and self.llm:
                try:
                    # 유저 선택 언어로 Whisper 강제 적용
                    transcription = self._transcribe_audio(audio_path, language=language)

                    if self.vad.is_hallucination(transcription, vad_result):
                        logger.warning("Whisper hallucination detected, skipping TXT")
                        transcription = []  # 환각이면 자막 비우기
                    else:
                        txt_scores = self._calculate_txt_scores(transcription, scenes, target_duration)
                        txt_success = len(txt_scores) > 0
                except Exception as e:
                    logger.error(f"TXT branch failed: {str(e)}")

            # 7. 최종 점수 계산 및 메시지 결정 (자막 우선 원칙)
            has_subtitles = len(transcription) > 0

            if txt_success and txt_scores:
                final_scores = self._fuse_scores(hd_scores, txt_scores)
                processing_method = "multimodal"
            else:
                logger.warning("Falling back to visual-only detection")
                final_scores = hd_scores
                processing_method = "visual_only"

            # 메시지 결정: 자막이 1개라도 있으면 "no speech detected" 삭제
            if has_subtitles:
                lang_display = language if language != "auto" else "detected"
                message = f"[OK] Completed with subtitles. ({lang_display})"
            else:
                message = "[OK] Completed (Visual features only - no speech detected)"

            # 8. 상위 장면 선택
            timestamps = self._select_top_scenes(scenes, final_scores, target_duration)

            if len(timestamps) == 0:
                raise RuntimeError("No highlights found")

            # 9. 요약 영상 생성
            output_path = self._create_summary_video(
                video_path,
                timestamps,
                options or {}
            )

            # 10. 결과 업로드
            result_url = self._upload_result(output_path)

            # 11. Webhook 전송 (language 포함)
            webhook_payload = {
                "status": "completed",
                "result_url": result_url,
                "processing_method": processing_method,
                "message": message,
                "language": language,  # DB 업데이트용
                "has_subtitles": has_subtitles,
                "metadata": {
                    "scene_count": len(scenes),
                    "selected_count": len(timestamps),
                    "subtitle_count": len(transcription),
                    "vad_speech_ratio": vad_result["speech_ratio"],
                    "vad_energy_db": vad_result["energy_db"]
                }
            }
            self._send_webhook(webhook_url, webhook_payload)

            return {
                "status": "success",
                "result_url": result_url,
                "processing_method": processing_method,
                "language": language
            }

        except Exception as e:
            logger.error(f"Processing failed: {str(e)}", exc_info=True)

            # 실패 시 Webhook 전송
            error_payload = {
                "status": "failed",
                "error": str(e),
                "processing_method": "error"
            }

            try:
                self._send_webhook(webhook_url, error_payload)
            except:
                pass

            return {
                "status": "failed",
                "error": str(e)
            }

    def _download_video(self, url: str) -> str:
        """영상 다운로드"""
        output_path = "/tmp/input_video.mp4"
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"Video downloaded: {output_path}")
        return output_path

    def _extract_audio(self, video_path: str) -> str:
        """오디오 추출"""
        audio_path = "/tmp/audio.wav"
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            audio_path, "-y"
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return audio_path

    def _detect_scenes(self, video_path: str) -> List[Dict]:
        """장면 검출 (PySceneDetect 사용)"""
        from scenedetect import detect, ContentDetector

        scene_list = detect(video_path, ContentDetector())

        scenes = []
        for i, scene in enumerate(scene_list):
            scenes.append({
                "id": i,
                "start": scene[0].get_seconds(),
                "end": scene[1].get_seconds()
            })

        return scenes

    def _transcribe_audio(self, audio_path: str, language: str = "auto") -> List[Dict]:
        """
        Whisper 음성 인식 - 유저 선택 언어 강제 적용

        Args:
            audio_path: 오디오 파일 경로
            language: 유저가 선택한 언어 ("ko", "en", "ja", "zh", "es", "auto")
        """
        # 언어 설정: "auto"면 None (자동 감지), 아니면 강제 적용
        whisper_language = None if language == "auto" else language

        # 환청 방지 프롬프트
        initial_prompt = self.LANGUAGE_PROMPTS.get(language)

        logger.info(f"Whisper transcribe - language: {whisper_language}, prompt: {initial_prompt is not None}")

        # Whisper 호출 (언어 강제 적용)
        transcribe_kwargs = {
            "beam_size": 5,
        }

        if whisper_language:
            transcribe_kwargs["language"] = whisper_language

        if initial_prompt:
            transcribe_kwargs["initial_prompt"] = initial_prompt

        segments, info = self.whisper_model.transcribe(audio_path, **transcribe_kwargs)

        logger.info(f"Whisper detected language: {info.language} (prob: {info.language_probability:.2f})")

        transcription = []
        for segment in segments:
            transcription.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text
            })

        return transcription

    def _calculate_all_hd_scores(
        self,
        video_path: str,
        scenes: List[Dict],
        audio_path: str
    ) -> List[float]:
        """모든 장면의 HD 점수 계산"""
        import cv2
        import librosa

        # 영상과 오디오 로드
        cap = cv2.VideoCapture(video_path)
        y, sr = librosa.load(audio_path, sr=22050)

        hd_scores = []
        for scene in scenes:
            # 키프레임 추출
            keyframes = self._extract_keyframes(cap, scene["start"], scene["end"])

            # 오디오 세그먼트 추출
            start_sample = int(scene["start"] * sr)
            end_sample = int(scene["end"] * sr)
            audio_segment = y[start_sample:end_sample]

            # HD 점수 계산
            score = self.visual_detector.calculate_hd_score(
                scene, keyframes, audio_segment, sr
            )
            hd_scores.append(score)

        cap.release()
        return hd_scores

    def _extract_keyframes(self, cap: 'cv2.VideoCapture', start: float, end: float) -> List[np.ndarray]:
        """키프레임 추출 (1 FPS)"""
        import cv2
        fps = cap.get(cv2.CAP_PROP_FPS)
        start_frame = int(start * fps)
        end_frame = int(end * fps)

        keyframes = []
        for frame_idx in range(start_frame, end_frame, int(fps)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if ret:
                keyframes.append(frame)

        return keyframes

    def _calculate_txt_scores(
        self,
        transcription: List[Dict],
        scenes: List[Dict],
        target_duration: int
    ) -> List[float]:
        """TXT 점수 계산 (LLM 기반)"""
        if not self.llm:
            return []

        try:
            # LLM에 전달할 프롬프트 생성
            prompt = self._create_llm_prompt(transcription, target_duration)

            # LLM 호출
            response = self.llm.generate_content(prompt)

            # 응답 파싱 (타임스탬프 추출)
            highlight_ranges = self._parse_llm_response(response.text)

            if not highlight_ranges:
                logger.warning("LLM returned empty highlights")
                return []

            # 장면별 TXT 점수 계산 (tIoU)
            txt_scores = []
            for scene in scenes:
                max_iou = 0.0
                for h_range in highlight_ranges:
                    iou = self._calculate_temporal_iou(
                        (scene["start"], scene["end"]),
                        h_range
                    )
                    max_iou = max(max_iou, iou)
                txt_scores.append(max_iou)

            return txt_scores

        except Exception as e:
            logger.error(f"TXT scoring failed: {str(e)}")
            return []

    def _create_llm_prompt(self, transcription: List[Dict], budget: int) -> str:
        """LLM 프롬프트 생성"""
        transcript_text = "\n".join([
            f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}"
            for seg in transcription
        ])

        prompt = f"""다음은 영상의 전사 내용입니다:

{transcript_text}

총 {budget}초 분량의 하이라이트를 추출하려고 합니다.
가장 중요하고 흥미로운 구간의 시간 범위를 JSON 형식으로 알려주세요.

응답 형식:
{{
  "highlights": [
    {{"start": 10.5, "end": 25.3}},
    {{"start": 45.0, "end": 60.2}}
  ]
}}
"""
        return prompt

    def _parse_llm_response(self, response_text: str) -> List[Tuple[float, float]]:
        """LLM 응답 파싱"""
        try:
            # JSON 추출
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                return []

            data = json.loads(json_match.group())
            highlights = data.get("highlights", [])

            return [(h["start"], h["end"]) for h in highlights]
        except Exception as e:
            logger.error(f"LLM response parsing failed: {str(e)}")
            return []

    def _calculate_temporal_iou(
        self,
        range1: Tuple[float, float],
        range2: Tuple[float, float]
    ) -> float:
        """시간적 IoU 계산"""
        intersection = max(0, min(range1[1], range2[1]) - max(range1[0], range2[0]))
        union = max(range1[1], range2[1]) - min(range1[0], range2[0])
        return intersection / union if union > 0 else 0.0

    def _fuse_scores(
        self,
        hd_scores: List[float],
        txt_scores: List[float],
        w_hd: float = 0.5,
        w_txt: float = 0.5
    ) -> List[float]:
        """HD와 TXT 점수 융합"""
        return [w_hd * hd + w_txt * txt for hd, txt in zip(hd_scores, txt_scores)]

    def _select_top_scenes(
        self,
        scenes: List[Dict],
        scores: List[float],
        target_duration: int
    ) -> List[Tuple[float, float]]:
        """상위 점수 장면 선택"""
        scene_score_pairs = list(zip(scenes, scores))
        scene_score_pairs.sort(key=lambda x: x[1], reverse=True)

        selected = []
        total_duration = 0.0

        for scene, score in scene_score_pairs:
            duration = scene["end"] - scene["start"]
            if total_duration + duration <= target_duration:
                selected.append(scene)
                total_duration += duration

            if total_duration >= target_duration * 0.9:
                break

        selected.sort(key=lambda x: x["start"])
        return [(s["start"], s["end"]) for s in selected]

    def _create_summary_video(
        self,
        video_path: str,
        timestamps: List[Tuple[float, float]],
        options: Dict
    ) -> str:
        """요약 영상 생성"""
        output_path = "/tmp/summary.mp4"

        # FFmpeg 필터 생성
        filter_parts = []
        for i, (start, end) in enumerate(timestamps):
            filter_parts.append(f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}];")
            filter_parts.append(f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}];")

        # 연결
        v_concat = "".join([f"[v{i}]" for i in range(len(timestamps))])
        a_concat = "".join([f"[a{i}]" for i in range(len(timestamps))])
        filter_complex = "".join(filter_parts) + f"{v_concat}concat=n={len(timestamps)}:v=1:a=0[outv];{a_concat}concat=n={len(timestamps)}:v=0:a=1[outa]"

        cmd = [
            "ffmpeg", "-i", video_path,
            "-filter_complex", filter_complex,
            "-map", "[outv]", "-map", "[outa]",
            output_path, "-y"
        ]

        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"Summary video created: {output_path}")

        return output_path

    def _upload_result(self, file_path: str) -> str:
        """결과 파일 업로드 (Supabase 등)"""
        # TODO: 실제 업로드 로직 구현
        # 여기서는 임시로 로컬 경로 반환
        return f"https://storage.example.com/result_{Path(file_path).name}"

    def _send_webhook(self, webhook_url: str, payload: Dict):
        """Webhook 전송"""
        response = requests.post(webhook_url, json=payload, timeout=30)
        response.raise_for_status()
        logger.info(f"Webhook sent successfully to {webhook_url}")


# ============================================
# RunPod Handler Entry Point
# ============================================

def handler(event):
    """
    RunPod 핸들러 엔트리 포인트

    event = {
        "input": {
            "webhook_url": "https://...",
            "task": "process_video",
            "video_url": "https://...",
            "options": {...}
        }
    }
    """
    try:
        input_data = event.get("input", {})

        webhook_url = input_data.get("webhook_url")
        task = input_data.get("task")
        video_url = input_data.get("video_url")
        options = input_data.get("options", {})

        if task == "process_video":
            processor = ImprovedEchoFusion()
            result = processor.process_video(
                video_url=video_url,
                webhook_url=webhook_url,
                target_duration=options.get("target_duration", 60),
                options=options
            )
            return result
        else:
            return {"status": "error", "message": f"Unknown task: {task}"}

    except Exception as e:
        logger.error(f"Handler error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    # 로컬 테스트
    test_event = {
        "input": {
            "webhook_url": "http://localhost:8080/runpod/webhook/1",
            "task": "process_video",
            "video_url": "https://example.com/video.mp4",
            "options": {
                "target_duration": 60
            }
        }
    }

    result = handler(test_event)
    print(json.dumps(result, indent=2))
