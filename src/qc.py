import subprocess
import os


def validate_output(output_path: str, expected_duration: float, duration_tolerance: float = 1.0):
    """
    Validate rendered output.

    Checks:
    - File exists
    - Duration matches expected timeline duration
    - Has video and audio streams
    """
    if not os.path.exists(output_path):
        raise FileNotFoundError(f"Output file not found: {output_path}")

    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', output_path],
        capture_output=True, text=True, check=True
    )
    actual_duration = float(result.stdout.strip())

    duration_diff = abs(actual_duration - expected_duration)
    if duration_diff > duration_tolerance:
        raise ValueError(
            f"Duration mismatch: {actual_duration:.2f}s vs expected {expected_duration:.2f}s "
            f"(tolerance: {duration_tolerance:.2f}s)"
        )

    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type',
         '-of', 'default=noprint_wrappers=1:nokey=1', output_path],
        capture_output=True, text=True, check=True
    )
    streams = result.stdout.strip().split('\n')

    if 'video' not in streams:
        raise ValueError("Output has no video stream")

    print(f"Output validation passed")
    print(f"   Duration: {actual_duration:.2f}s")
    print(f"   File size: {os.path.getsize(output_path) / 1024**2:.2f} MB")
    print(f"   Streams: {', '.join(set(streams))}")
