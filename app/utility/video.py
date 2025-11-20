"""
Video processing utilities using FFmpeg
"""
import subprocess
import os
from pathlib import Path


def check_ffmpeg_installed() -> bool:
    """
    Check if FFmpeg is installed and available in PATH

    Returns:
        bool: True if FFmpeg is installed, False otherwise
    """
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def generate_thumbnail(
        video_path: str,
        output_path: str,
        timestamp: str = "00:00:01",
        width: int = 640,
        height: int = -1,
        quality: int = 2
) -> bool:
    """
    Generate a thumbnail image from a video file using FFmpeg

    Args:
        video_path: Path to the input video file
        output_path: Path to save the thumbnail image
        timestamp: Time position to extract frame (format: HH:MM:SS or seconds)
        width: Width of the thumbnail (default: 640px)
        height: Height of the thumbnail (-1 for auto, maintains aspect ratio)
        quality: JPEG quality (1-31, lower is better, default: 2)

    Returns:
        bool: True if thumbnail was generated successfully, False otherwise
    """
    if not check_ffmpeg_installed():
        print("Error: FFmpeg is not installed")
        return False

    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        return False

    try:
        # FFmpeg command to extract thumbnail
        command = [
            "ffmpeg",
            "-i", video_path,  # Input file
            "-ss", timestamp,  # Seek to timestamp
            "-vframes", "1",  # Extract 1 frame
            "-vf", f"scale={width}:{height}",  # Resize
            "-q:v", str(quality),  # Quality
            "-y",  # Overwrite output file
            output_path
        ]

        # Run FFmpeg
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        # Check if thumbnail was created
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True
        else:
            print("Error: Thumbnail file was not created")
            return False

    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e.stderr.decode()}")
        return False
    except Exception as e:
        print(f"Error generating thumbnail: {str(e)}")
        return False


def generate_multiple_thumbnails(
        video_path: str,
        output_dir: str,
        count: int = 3,
        width: int = 640,
        height: int = -1,
        quality: int = 2
) -> list[str]:
    """
    Generate multiple thumbnails from a video at different timestamps

    Args:
        video_path: Path to the input video file
        output_dir: Directory to save thumbnails
        count: Number of thumbnails to generate
        width: Width of thumbnails
        height: Height of thumbnails (-1 for auto)
        quality: JPEG quality (1-31, lower is better)

    Returns:
        list[str]: List of paths to generated thumbnails
    """
    if not check_ffmpeg_installed():
        print("Error: FFmpeg is not installed")
        return []

    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        return []

    # Get video duration
    duration = get_video_duration(video_path)
    if duration <= 0:
        print("Error: Could not get video duration")
        return []

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Generate thumbnails at evenly distributed timestamps
    thumbnails = []
    video_name = Path(video_path).stem

    for i in range(count):
        # Calculate timestamp
        timestamp = (duration / (count + 1)) * (i + 1)

        # Output path
        output_path = os.path.join(output_dir, f"{video_name}_thumb_{i + 1}.jpg")

        # Generate thumbnail
        if generate_thumbnail(
                video_path=video_path,
                output_path=output_path,
                timestamp=str(int(timestamp)),
                width=width,
                height=height,
                quality=quality
        ):
            thumbnails.append(output_path)

    return thumbnails


def get_video_duration(video_path: str) -> float:
    """
    Get the duration of a video file in seconds

    Args:
        video_path: Path to the video file

    Returns:
        float: Duration in seconds, or 0 if error
    """
    if not check_ffmpeg_installed():
        return 0

    if not os.path.exists(video_path):
        return 0

    try:
        command = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        duration = float(result.stdout.decode().strip())
        return duration

    except Exception as e:
        print(f"Error getting video duration: {str(e)}")
        return 0


def get_video_info(video_path: str) -> dict:
    """
    Get detailed information about a video file

    Args:
        video_path: Path to the video file

    Returns:
        dict: Video information including duration, resolution, codec, etc.
    """
    if not check_ffmpeg_installed():
        return {}

    if not os.path.exists(video_path):
        return {}

    try:
        command = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        import json
        data = json.loads(result.stdout.decode())

        # Extract video stream info
        video_stream = next(
            (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
            None
        )

        if not video_stream:
            return {}

        return {
            "duration": float(data.get("format", {}).get("duration", 0)),
            "size": int(data.get("format", {}).get("size", 0)),
            "bit_rate": int(data.get("format", {}).get("bit_rate", 0)),
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "codec": video_stream.get("codec_name"),
            "fps": eval(video_stream.get("r_frame_rate", "0/1")),
            "format": data.get("format", {}).get("format_name")
        }

    except Exception as e:
        print(f"Error getting video info: {str(e)}")
        return {}