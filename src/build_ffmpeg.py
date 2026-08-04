from typing import Dict, List
import os
import subprocess


def _check_nvenc_available() -> bool:
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True, text=True, check=True
        )
        return "h264_nvenc" in result.stdout
    except Exception:
        return False


def build_render_commands(timeline: Dict,
                          output_path: str,
                          work_dir: str = "/kaggle/working",
                          video_codec: str = "libx264",
                          video_crf: int = 18,
                          audio_codec: str = "aac",
                          audio_bitrate: str = "192k",
                          use_gpu: bool = False,
                          gpu_codec: str = "h264_nvenc",
                          gpu_cq: int = 19,
                          gpu_preset: str = "slow",
                          gpu_hwaccel: str = "cuda",
                          gpu_maxrate: str = "80M",
                          gpu_bufsize: str = "160M") -> List[str]:
    """
    Generate FFmpeg commands to render the timeline.

    Strategy:
    1. Render each video segment to an intermediate file (uniform codec)
    2. Concat all segments into video-only file
    3. Mix audio tracks and merge with video

    Returns:
        List of shell commands to execute in order
    """
    commands = []
    segment_files = []

    use_gpu = use_gpu and _check_nvenc_available()

    if use_gpu:
        encode_cmd = (
            f"-c:v {gpu_codec} -cq {gpu_cq} -preset {gpu_preset} "
            f"-maxrate {gpu_maxrate} -bufsize {gpu_bufsize}"
        )
        hwaccel_args = f"-hwaccel {gpu_hwaccel}"
        print(f"Using GPU encoding: {gpu_codec} (CQ={gpu_cq}, preset={gpu_preset}, maxrate={gpu_maxrate})")
    else:
        encode_cmd = f"-c:v {video_codec} -crf {video_crf} -preset fast"
        hwaccel_args = ""
        print(f"Using CPU encoding: {video_codec} (CRF={video_crf})")

    # Step 1: Render each video segment
    for i, clip in enumerate(timeline['video_clips']):
        segment_path = os.path.join(work_dir, f"segment_{i:04d}.mp4")
        segment_files.append(segment_path)

        cmd = (
            f"ffmpeg -y {hwaccel_args} "
            f"-ss {clip['source_in']:.6f} "
            f"-to {clip['source_out']:.6f} "
            f"-i \"{clip['source_path']}\" "
            f"{encode_cmd} "
            f"-an "
            f"\"{segment_path}\""
        )
        commands.append(cmd)

    # Step 2: Concat video segments
    concat_list_path = os.path.join(work_dir, "concat_list.txt")
    video_only_path = os.path.join(work_dir, "video_only.mp4")

    concat_list_cmd = f"cat > {concat_list_path} << 'EOF'\n"
    for seg in segment_files:
        concat_list_cmd += f"file '{seg}'\n"
    concat_list_cmd += "EOF"
    commands.append(concat_list_cmd)

    cmd = (
        f"ffmpeg -y "
        f"-f concat -safe 0 "
        f"-i {concat_list_path} "
        f"-c copy "
        f"\"{video_only_path}\""
    )
    commands.append(cmd)

    commands.append(f"rm -f {' '.join(segment_files)} {concat_list_path}")

    # Step 3: Mix audio and merge with video
    if timeline['audio_tracks']:
        audio_inputs = []
        audio_filter_parts = []
        input_idx = 1

        for track_name, clips in timeline['audio_tracks'].items():
            for clip in clips:
                audio_inputs.append(
                    f"-ss {clip['source_in']:.6f} "
                    f"-to {clip['source_out']:.6f} "
                    f"-i \"{clip['source_path']}\""
                )
                audio_filter_parts.append(f"[{input_idx}:a]")
                input_idx += 1

        num_audio_inputs = len(audio_inputs)
        audio_filter = (
            f"{' '.join(audio_filter_parts)}"
            f"amix=inputs={num_audio_inputs}:duration=longest[aout]"
        )

        cmd = (
            f"ffmpeg -y "
            f"-i \"{video_only_path}\" "
            f"{' '.join(audio_inputs)} "
            f"-filter_complex \"{audio_filter}\" "
            f"-map 0:v -map \"[aout]\" "
            f"-c:v copy "
            f"-c:a {audio_codec} -b:a {audio_bitrate} "
            f"\"{output_path}\""
        )
        commands.append(cmd)
    else:
        cmd = f"ffmpeg -y -i \"{video_only_path}\" -c copy \"{output_path}\""
        commands.append(cmd)

    return commands
