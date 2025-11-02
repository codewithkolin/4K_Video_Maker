# Video Edit - Final Package

Complete package for creating 4K videos with music overlays.

## Contents

### Main Application
- **main.py**: Full GUI application for creating 4K videos with overlays
- **extract_overlay.py**: Standalone script for extracting overlay videos only

### Core Modules
- **audio_processor.py**: Audio file processing and concatenation
- **image_processor.py**: Image resizing to 4K
- **video_processor.py**: Video creation with FFmpeg
- **player_overlay.py**: PIL-based overlay rendering
- **player_overlay_playwright.py**: High-quality Playwright-based overlay rendering

### Assets
- **player_overlay.html**: HTML template for overlay
- **player_overlay.css**: CSS styling for overlay
- **requirements.txt**: Python dependencies

## Features

### Main Application (main.py)
- Create 4K videos from images and audio files
- Music player overlay with progress bars
- Batch audio processing
- Random audio selection

### Overlay Extraction Script (extract_overlay.py)
- **Standalone**: Works independently
- **Custom Dimensions**: Manual entry of horizontal and vertical pixels
- **Aspect Ratio**: Maintains 600:174 recommendation
- **Proportional Text Scaling**: Text scales automatically with resolution
- **Alpha Channel**: ProRes 4444 format for Premiere Pro
- **No Fade Effects**: Clean overlay without transitions
- **Batch Processing**: Process multiple audio files

## Installation

1. **Install Python Dependencies**:
```bash
pip install -r requirements.txt
```

2. **Install Playwright Browsers** (optional, for better rendering):
```bash
playwright install
```

3. **Install FFmpeg**:
```bash
# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html

# Linux
sudo apt-get install ffmpeg
```

## Usage

### Main Application
```bash
python main.py
```

See main README for detailed usage instructions.

### Overlay Extraction Script
```bash
python extract_overlay.py
```

1. Enter audio file(s) (comma-separated)
2. Enter horizontal dimension (width in pixels)
3. Enter vertical dimension (height in pixels)
4. Enter output directory

**Example dimensions:**
- Standard: 600x174
- Double: 1200x348
- 4K: 3720x1080

Text scales proportionally with resolution changes!

## Text Scaling

Text sizes scale automatically based on overlay height:
- **Track Name**: 12% of height
- **Time Display**: 8% of height
- **Icons**: 10% of height

All elements maintain proper proportions when you change dimensions.

## Output Format

### Overlay Videos
- **Format**: MOV
- **Codec**: ProRes 4444 (supports alpha channel)
- **Frame Rate**: 30 fps
- **Alpha Channel**: Full transparency support

### Full Videos
- **Format**: MP4
- **Resolution**: 4K (3840x2160)
- **Codec**: H.264 (YouTube optimized)

## Dependencies

- Python 3.8+
- Pillow >= 10.0.0
- pydub >= 0.25.1
- ffmpeg-python >= 0.2.0
- audioop-lts >= 0.2.0 (for Python 3.13+)
- playwright >= 1.40.0 (optional, for better rendering)

## Notes

- Aspect ratio recommendation: 600:174 (approximately 3.45:1)
- Overlay extraction script warns if aspect ratio differs significantly
- Both PIL and Playwright renderers support proportional text scaling
- Duplicate filenames are automatically handled
- Temporary files are cleaned up automatically
