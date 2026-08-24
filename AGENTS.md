# AGENTS.md

## Cursor Cloud specific instructions

This repo is a single Python product: a Tkinter desktop GUI ("4K Video Creator for YouTube",
entry point `main.py`) that renders a static image + concatenated audio into a 4K H.264 MP4 via
FFmpeg, with an optional music-player overlay rendered by Playwright (Chromium). See `README.md`
for the user-facing feature list and `README_EXTRACT.md` in `Final/` for the overlay-extraction variant.

### Environment / running
- Use the project virtualenv at `venv/` (created by the update script). Run Python as
  `./venv/bin/python`, e.g. `./venv/bin/python main.py`.
- System dependencies FFmpeg (`ffmpeg`/`ffprobe`), the Tk toolkit (`python3-tk`), and the
  Playwright Chromium OS libraries are provided by the base image snapshot; the update script only
  refreshes Python packages and the Playwright browser. `main.py` exits immediately if `ffmpeg`
  is not on PATH.
- `main.py` is a GUI app and needs a display. There is no headless/CLI entry point. To run it in
  the cloud VM, start a virtual display first, e.g. `Xvfb :99 -screen 0 1280x1400x24 &` then
  `DISPLAY=:99 ./venv/bin/python main.py`. `scrot` can capture the window.

### Dependency notes (non-obvious)
- `requirements.txt` pins `audioop-lts`, which only publishes wheels for Python 3.13+. This VM's
  Python is 3.12, where `audioop` is still a built-in stdlib module, so `audioop-lts` is neither
  available nor needed. A plain `pip install -r requirements.txt` therefore FAILS on Python 3.12;
  install the other packages directly (Pillow, pydub, ffmpeg-python, playwright). The update
  script handles this automatically.
- Playwright needs its browser binary: `./venv/bin/python -m playwright install chromium`.
  `video_processor.py` imports the Playwright overlay renderer and silently falls back to a
  PIL-based renderer (`player_overlay.py`) if Playwright is unavailable.

### Lint / test / build
- There is no configured linter, no automated test suite, and no build step in this repo.
- To smoke-test the core pipeline headlessly, drive `resize_image_to_4k`, `process_audio_files`
  /`export_audio_to_wav`, `generate_overlay_frames`/`create_overlay_video`, and `create_4k_video`
  (all importable modules) with a generated image + a short FFmpeg-generated WAV, then verify the
  output MP4 with `ffprobe`. Keep test audio short — encoding is `libx264 -preset slow -crf 18` at
  3840x2160, which is CPU-heavy for long clips.
