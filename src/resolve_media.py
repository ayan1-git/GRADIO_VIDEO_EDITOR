import os
from typing import Dict


def resolve_media_paths(timeline: Dict, media_root: str) -> Dict:
    """
    Resolve relative/absolute paths in XML to actual file locations.

    Args:
        timeline: Output from parse_sequence()
        media_root: Root directory where media is stored (e.g., '/kaggle/input/dataset/media/')

    Returns:
        Timeline with resolved absolute paths

    Raises:
        FileNotFoundError: If any referenced media file is missing
    """
    missing_files = []

    # Resolve video clips
    for clip in timeline['video_clips']:
        filename = os.path.basename(clip['source_path'])
        resolved_path = os.path.join(media_root, 'video', filename)

        if not os.path.exists(resolved_path):
            missing_files.append(resolved_path)
        else:
            clip['source_path'] = resolved_path

    # Resolve audio tracks
    for track_name, clips in timeline['audio_tracks'].items():
        for clip in clips:
            filename = os.path.basename(clip['source_path'])
            resolved_path = os.path.join(media_root, 'audio', filename)

            if not os.path.exists(resolved_path):
                missing_files.append(resolved_path)
            else:
                clip['source_path'] = resolved_path

    if missing_files:
        raise FileNotFoundError(
            "Missing media files:\n" + "\n".join(missing_files)
        )

    return timeline
