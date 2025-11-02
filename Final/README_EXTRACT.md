# Overlay Extraction Script

Standalone script to extract music overlay videos from audio files.

## Two Versions Available

### 1. GUI Version (Recommended)
**File**: `extract_overlay_gui.py`

- **User-friendly interface** with buttons and input fields
- **Auto-calculates vertical dimension** when horizontal is entered (maintains 600:174 ratio)
- Real-time aspect ratio validation
- Progress bars and status updates
- Easy file and directory selection

### 2. Command Line Version
**File**: `extract_overlay.py`

- Text-based interface
- Manual entry of both dimensions
- Suitable for automation/scripting

## Features

- **Customizable Dimensions**: Enter custom horizontal and vertical dimensions
- **Auto-calculation**: Vertical dimension automatically calculated from horizontal (GUI version)
- **Aspect Ratio**: Maintains 600:174 ratio recommendation (with warning if different)
- **Proportional Text Scaling**: Text size scales automatically with resolution changes
- **Alpha Channel Support**: Exports MOV files with ProRes 4444 codec (alpha channel)
- **Batch Processing**: Process multiple audio files at once
- **No Fade Effects**: Clean overlay without fade in/out effects

## Requirements

- Python 3.8+
- FFmpeg (must be installed separately)
- Dependencies listed in `requirements.txt`

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers (optional, for better rendering):
```bash
playwright install
```

3. Ensure FFmpeg is installed:
```bash
# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html

# Linux
sudo apt-get install ffmpeg
```

## Usage

### GUI Version (Recommended)

Run the GUI application:

```bash
python extract_overlay_gui.py
```

**Step-by-Step:**

1. **Select Audio Files**: Click "Select Audio Files" button and choose one or more audio files
2. **Enter Horizontal Dimension**: Enter width in pixels (e.g., 600, 1200, 2400)
   - **Auto-calculation enabled by default**: Vertical dimension is automatically calculated to maintain 600:174 ratio
   - You can disable auto-calculation to manually enter both dimensions
3. **Select Output Directory**: Click "Select Directory" button
4. **Extract**: Click "Extract Overlays" button

The GUI shows:
- Real-time aspect ratio validation (green = good, orange = close, red = warning)
- Progress bars for each overlay
- Status messages in the log area

### Command Line Version

Run the command-line script:

```bash
python extract_overlay.py
```

**Step-by-Step:**

1. **Enter Audio Files**: 
   - Enter one or more audio file paths (comma-separated)
   - Example: `song1.mp3, song2.wav, song3.m4a`

2. **Enter Dimensions**:
   - **Horizontal (width)**: Enter width in pixels (e.g., 600, 1200, 2400)
   - **Vertical (height)**: Enter height in pixels (e.g., 174, 348, 696)
   - Text will scale proportionally with resolution
   - Recommended aspect ratio: 600:174

3. **Output Directory**:
   - Enter output directory path (or press Enter for current directory)

### Examples

**Standard Size (600x174)**:
```
Horizontal: 600
Vertical: 174
```

**Double Size (1200x348)**:
```
Horizontal: 1200
Vertical: 348
```

**4K Size (3720x1080)**:
```
Horizontal: 3720
Vertical: 1080
```

## Output

- **Format**: MOV with ProRes 4444 codec
- **Alpha Channel**: Full transparency support
- **Resolution**: As specified by user
- **Frame Rate**: 30 fps
- **Naming**: `{track_name}_overlay.mov`

## Text Scaling

Text sizes scale proportionally with resolution:
- **Track Name**: 12% of height
- **Time Display**: 8% of height
- **Icons**: 10% of height

All elements maintain proper proportions when dimensions change.

## Notes

- Aspect ratio should ideally be 600:174 (approximately 3.45:1)
- Script warns if aspect ratio differs significantly
- Duplicate filenames are automatically handled (numbered)
- Temporary files are cleaned up automatically
- Supports multiple audio formats: WAV, MP3, M4A, FLAC, AAC, OGG

