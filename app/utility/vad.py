"""
Voice Activity Detection (VAD) Utility
Prevents Whisper hallucination by detecting actual speech presence
"""

import numpy as np
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class VoiceActivityDetector:
    """
    Voice Activity Detector

    Detects actual human voice to prevent Whisper hallucination

    Example:
        >>> vad = VoiceActivityDetector()
        >>> result = vad.detect_speech("audio.mp3")
        >>> if result["has_speech"]:
        ...     # Proceed with Whisper transcription
        ... else:
        ...     # No speech, use visual features only
    """

    def __init__(
        self,
        threshold_db: float = -40.0,
        min_speech_ratio: float = 0.1,
        min_duration: float = 1.0
    ):
        """
        Args:
            threshold_db: RMS energy threshold in dB (default: -40dB)
            min_speech_ratio: Minimum speech ratio to consider (default: 10%)
            min_duration: Minimum speech duration in seconds (default: 1s)
        """
        self.threshold_db = threshold_db
        self.min_speech_ratio = min_speech_ratio
        self.min_duration = min_duration

    def detect_speech(self, audio_path: str) -> Dict[str, any]:
        """
        Detect if there is actual speech in audio file

        Args:
            audio_path: Path to audio file

        Returns:
            {
                "has_speech": bool,           # Speech detected
                "speech_ratio": float,        # Ratio of speech frames (0-1)
                "energy_db": float,           # Average energy in dB
                "duration": float,            # Speech duration in seconds
                "confidence": float           # Confidence score (0-1)
            }
        """
        try:
            import librosa

            # Load audio (resample to 16kHz)
            y, sr = librosa.load(audio_path, sr=16000)
            total_duration = len(y) / sr

            # Calculate RMS energy
            # 25ms window, 10ms hop (following paper)
            frame_length = int(0.025 * sr)
            hop_length = int(0.010 * sr)

            rms = librosa.feature.rms(
                y=y,
                frame_length=frame_length,
                hop_length=hop_length
            )[0]

            # Convert to dB
            rms_db = librosa.amplitude_to_db(rms, ref=np.max(rms))

            # Detect speech frames
            speech_frames = rms_db > self.threshold_db
            speech_count = np.sum(speech_frames)
            total_frames = len(rms_db)

            # Calculate ratio
            speech_ratio = speech_count / total_frames if total_frames > 0 else 0.0

            # Calculate speech duration
            speech_duration = (speech_count * hop_length) / sr

            # Calculate average energy
            avg_energy = np.mean(rms_db)

            # Calculate confidence (multiple factors)
            confidence = self._calculate_confidence(
                speech_ratio=speech_ratio,
                avg_energy=avg_energy,
                speech_duration=speech_duration,
                total_duration=total_duration
            )

            # Final decision
            has_speech = (
                speech_ratio >= self.min_speech_ratio and
                avg_energy > self.threshold_db and
                speech_duration >= self.min_duration
            )

            logger.info(
                f"VAD Results - Speech: {has_speech}, "
                f"Ratio: {speech_ratio:.2%}, "
                f"Energy: {avg_energy:.2f}dB, "
                f"Duration: {speech_duration:.2f}s, "
                f"Confidence: {confidence:.2%}"
            )

            return {
                "has_speech": has_speech,
                "speech_ratio": speech_ratio,
                "energy_db": avg_energy,
                "duration": speech_duration,
                "confidence": confidence
            }

        except ImportError:
            logger.error("librosa not installed. Install with: pip install librosa")
            # Return safe default values
            return {
                "has_speech": True,
                "speech_ratio": 0.0,
                "energy_db": -60.0,
                "duration": 0.0,
                "confidence": 0.0
            }
        except Exception as e:
            logger.error(f"VAD error: {str(e)}", exc_info=True)
            # On error, safely return True (preserve existing behavior)
            return {
                "has_speech": True,
                "speech_ratio": 0.0,
                "energy_db": -60.0,
                "duration": 0.0,
                "confidence": 0.0
            }

    def _calculate_confidence(
        self,
        speech_ratio: float,
        avg_energy: float,
        speech_duration: float,
        total_duration: float
    ) -> float:
        """
        Calculate speech detection confidence

        Combines multiple indicators to produce 0-1 confidence score
        """
        # Ratio score (0-1)
        ratio_score = min(speech_ratio / 0.5, 1.0)  # Full score at 50%+

        # Energy score (0-1)
        # Normalize -60dB to 0dB range to 0-1
        energy_score = np.clip((avg_energy + 60) / 60, 0, 1)

        # Duration score (0-1)
        duration_score = min(speech_duration / 5.0, 1.0)  # Full score at 5s+

        # Weighted average
        confidence = (
            0.4 * ratio_score +
            0.3 * energy_score +
            0.3 * duration_score
        )

        return confidence

    def is_hallucination(
        self,
        transcription: list,
        vad_result: Dict
    ) -> bool:
        """
        Determine if Whisper transcription result is hallucination

        Args:
            transcription: Whisper transcription result list
                [{"text": "...", "start": 0.0, "end": 1.0}, ...]
            vad_result: VAD result dictionary

        Returns:
            True if hallucination detected, False otherwise
        """
        if not transcription:
            return False

        # Extract full text
        total_text = " ".join([seg.get("text", "") for seg in transcription])
        text_length = len(total_text.strip())

        # 1. Low speech ratio but long text = hallucination
        if vad_result["speech_ratio"] < 0.2 and text_length > 100:
            logger.warning(
                f"Hallucination detected: Low speech ratio "
                f"({vad_result['speech_ratio']:.2%}) but long text ({text_length} chars)"
            )
            return True

        # 2. Low energy but text present = hallucination
        if vad_result["energy_db"] < -50 and text_length > 50:
            logger.warning(
                f"Hallucination detected: Low energy "
                f"({vad_result['energy_db']:.2f}dB) but text present"
            )
            return True

        # 3. Detect repeated phrases (e.g., "Tokyo Station Tokyo Station Tokyo Station")
        words = total_text.split()
        if len(words) > 3:
            unique_words = len(set(words))
            repetition_ratio = unique_words / len(words)
            if repetition_ratio < 0.3:  # Less than 30% unique words
                logger.warning(
                    f"Hallucination detected: High repetition "
                    f"(uniqueness: {repetition_ratio:.2%})"
                )
                return True

        # 4. Low confidence = suspicious
        if vad_result["confidence"] < 0.2 and text_length > 0:
            logger.warning(
                f"Hallucination suspected: Low confidence "
                f"({vad_result['confidence']:.2%})"
            )
            return True

        return False


# Convenience functions
def detect_speech(audio_path: str, **kwargs) -> Dict:
    """
    Convenient speech detection function

    Args:
        audio_path: Path to audio file
        **kwargs: VoiceActivityDetector initialization parameters

    Returns:
        VAD result dictionary
    """
    vad = VoiceActivityDetector(**kwargs)
    return vad.detect_speech(audio_path)


def check_hallucination(
    transcription: list,
    audio_path: str,
    **kwargs
) -> bool:
    """
    Convenience function to check for Whisper hallucination

    Args:
        transcription: Whisper transcription result
        audio_path: Original audio file path
        **kwargs: VoiceActivityDetector initialization parameters

    Returns:
        True if hallucination detected
    """
    vad = VoiceActivityDetector(**kwargs)
    vad_result = vad.detect_speech(audio_path)
    return vad.is_hallucination(transcription, vad_result)
