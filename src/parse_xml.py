import xml.etree.ElementTree as ET
from typing import Dict, List


def _get_text(parent, tag, default=None):
    el = parent.find(tag)
    return el.text if el is not None else default


def _get_rate(parent, default=30.0):
    rate_el = parent.find('rate')
    if rate_el is None:
        return default
    tb = rate_el.find('timebase')
    if tb is None or tb.text is None:
        return default
    try:
        return float(tb.text)
    except ValueError:
        return default


def _extract_clips(track):
    clips = []
    for clip in track.findall('clipitem'):
        file_el = clip.find('file')
        if file_el is None:
            continue

        pathurl = file_el.find('pathurl')
        source_path = pathurl.text if pathurl is not None else ""

        source_in = float(_get_text(clip, 'in', 0) or 0)
        source_out = float(_get_text(clip, 'out', 0) or 0)
        record_in = float(_get_text(clip, 'start', 0) or 0)
        record_out = float(_get_text(clip, 'end', 0) or 0)

        clip_timebase = _get_rate(clip, 30.0)

        if source_out <= source_in:
            source_out = source_in + 1

        clips.append({
            'source_path': source_path,
            'source_in': source_in / clip_timebase,
            'source_out': source_out / clip_timebase,
            'record_in': record_in / clip_timebase,
            'duration': (source_out - source_in) / clip_timebase,
        })
    return clips


def parse_sequence(xml_path: str) -> Dict:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    seq_el = root.find('sequence')
    if seq_el is None:
        seq_el = root

    seq_timebase = _get_rate(seq_el, 30.0)
    seq_duration = float(_get_text(seq_el, 'duration', 0) or 0)

    video_clips = []
    audio_tracks = {}

    media = seq_el.find('media')
    if media is None:
        raise ValueError("No <media> element found in XML")

    video_section = media.find('video')
    if video_section is not None:
        for track in video_section.findall('track'):
            video_clips.extend(_extract_clips(track))

    audio_section = media.find('audio')
    if audio_section is not None:
        track_idx = 0
        for track in audio_section.findall('track'):
            track_name = f"audio_{track_idx}"
            audio_tracks[track_name] = _extract_clips(track)
            track_idx += 1

    video_clips.sort(key=lambda c: c['record_in'])
    for clips in audio_tracks.values():
        clips.sort(key=lambda c: c['record_in'])

    max_record_out = seq_duration / seq_timebase
    for clip in video_clips:
        max_record_out = max(max_record_out, clip['record_in'] + clip['duration'])
    for clips in audio_tracks.values():
        for clip in clips:
            max_record_out = max(max_record_out, clip['record_in'] + clip['duration'])

    return {
        'video_clips': video_clips,
        'audio_tracks': audio_tracks,
        'duration': max_record_out,
    }
