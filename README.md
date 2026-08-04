# Video Render Pipeline

Production-grade pipeline for rendering video sequences from editor XML exports (FCP 7 XML / FCPXML) using FFmpeg.

## GPU Acceleration (Kaggle T4)

This pipeline supports NVIDIA NVENC GPU encoding on Kaggle T4 GPUs for faster rendering without quality loss.

Enable GPU encoding by setting `USE_GPU = True` in `notebooks/kaggle_render.ipynb`. GPU settings:

- Codec: `h264_nvenc`
- Quality: `cq 19` (visually lossless)
- Preset: `slow`
- HW accel: `cuda`
- Maxrate: `80M` (caps bitrate to avoid filling disk)
- Bufsize: `160M`

If NVENC is unavailable, the pipeline automatically falls back to CPU `libx264` encoding.

### Disk Space Management

On Kaggle, `/kaggle/working` has limited space. The pipeline automatically:
- Caps NVENC bitrate to 80 Mbps via `-maxrate 80M -bufsize 160M`
- Deletes intermediate segment files after concatenation

## Project Structure

```
render_project/
├── xml/
│   └── sequence.xml           # Exported from your editor
├── media/
│   ├── video/
│   │   ├── clip_a.mp4
│   │   └── clip_b.mp4
│   └── audio/
│       └── music.mp3
├── src/
│   ├── __init__.py
│   ├── parse_xml.py           # Parse XML → structured timeline
│   ├── resolve_media.py       # Map XML references → actual files
│   ├── build_ffmpeg.py        # Generate FFmpeg commands
│   ├── render.py              # Execute with checkpointing
│   └── qc.py                  # Validate output
├── configs/
│   └── render.yaml            # Codec, bitrate, audio settings
├── notebooks/
│   └── kaggle_render.ipynb    # Main execution notebook
├── requirements.txt
└── README.md
```

## Quick Start

```bash
pip install -r requirements.txt
```

Then open `notebooks/kaggle_render.ipynb` and run all cells.

## Modules

- `parse_xml.py` - Parse FCP 7 XML into structured timeline using a custom parser
- `resolve_media.py` - Resolve media file paths and validate existence
- `build_ffmpeg.py` - Generate ordered FFmpeg commands for segment rendering, concatenation, and audio mixing
- `render.py` - Execute commands with checkpoint/resume and error logging
- `qc.py` - Validate output duration, streams, and file integrity
- `youtube_upload.py` - Upload final render to YouTube via YouTube Data API v3

## Upload to YouTube

The notebook includes an optional cell to upload the rendered video directly to YouTube from Kaggle.

### Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **YouTube Data API v3**
4. Create OAuth 2.0 credentials (Desktop app type)
5. In `notebooks/kaggle_render.ipynb`, find the cell titled **"Write YouTube OAuth client secret from embedded string"** and replace the placeholder values (`YOUR_CLIENT_ID`, `YOUR_PROJECT_ID`, `YOUR_CLIENT_SECRET`) with your actual OAuth client JSON values
6. In the notebook upload cell, set:
   - `VIDEO_TITLE`
   - `VIDEO_DESCRIPTION`
   - `VIDEO_TAGS`
   - `PRIVACY_STATUS` (`public`, `unlisted`, or `private`)

The upload cell will print a URL. Open it in your browser, authenticate, and paste the authorization code into the notebook when prompted. The first run saves a `token.json` for subsequent runs.

**Note:** `notebooks/kaggle_render.ipynb` is gitignored and kept local-only because it contains personal OAuth credentials.
