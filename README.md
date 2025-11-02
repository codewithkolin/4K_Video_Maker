# 4K Video Creator for YouTube

A professional GUI application for creating high-quality 4K (3840x2160) videos from a single image and multiple audio files, optimized for YouTube upload. Video length is dynamically determined by the total duration of all selected audio files.

## Features

- **4K Resolution**: Creates videos at 3840x2160 pixels (true 4K)
- **High Quality**: Uses industry-standard FFmpeg with YouTube-optimized settings
- **Flexible Audio Selection**: Choose files manually or use random selection from a directory
- **Multiple Audio Formats**: Supports WAV, MP3, M4A, FLAC, AAC, and OGG
- **Random Audio Selection**: Automatically selects files to meet your target duration with no duplicates
- **Smooth Audio Transitions**: Automatic fade-in/fade-out between music files
- **User-Friendly GUI**: Simple interface for selecting files and creating videos
- **YouTube Ready**: Output format optimized for YouTube uploads

## Requirements

### System Requirements

- **Python 3.8+**
- **FFmpeg** (must be installed separately)

### Python Dependencies

All Python dependencies are listed in `requirements.txt`:
- Pillow >= 10.0.0
- pydub >= 0.25.1
- ffmpeg-python >= 0.2.0
- audioop-lts >= 0.2.0 (required for Python 3.13+ compatibility)

## Installation

### 1. Install FFmpeg

FFmpeg is required for video encoding. Install it based on your operating system:

#### macOS
```bash
brew install ffmpeg
```

#### Windows
1. Download FFmpeg from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
2. Extract and add to your system PATH
3. Or use a package manager like Chocolatey:
   ```bash
   choco install ffmpeg
   ```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

### 2. Create Virtual Environment (Recommended)

It's recommended to use a virtual environment to keep dependencies isolated:

```bash
python3 -m venv venv
```

### 3. Activate Virtual Environment

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

### 4. Install Python Dependencies

Once the virtual environment is activated, install dependencies:

```bash
pip install -r requirements.txt
```

Or install individually:
```bash
pip install Pillow pydub ffmpeg-python
```

## Usage

### Running the Application

**First, activate the virtual environment (if using one):**

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

**Then run the application:**
```bash
python main.py
```

### Step-by-Step Guide

1. **Select Image**: Click "Select Image" and choose a high-quality image file
   - Supported formats: JPG, PNG, BMP, TIFF
   - The image will be automatically resized to 4K resolution

2. **Select Audio Files**: Choose one of the following methods:
   
   **Method A: Manual Selection**
   - Click "Select WAV Files" and choose one or more WAV audio files
   - Only WAV files are supported for manual selection
   - You can select any number of audio files (1 or more)
   - Files will be concatenated in the order selected
   
   **Method B: Random Selection**
   - Click "Select Directory" to choose a folder containing audio files
   - Enter your desired target duration in minutes (default: 60)
   - Click "Generate Random Selection" to randomly select files to meet your target
   - Supports multiple audio formats: WAV, MP3, M4A, FLAC, AAC, OGG
   - Searches directory and all subdirectories automatically
   - No duplicate files will be selected
   - Result will be close to your target duration with 30% tolerance
   
   **Audio Processing**:
   - Video length automatically matches the total duration of all audio files
   - Fade transitions (2 seconds) are added between files

3. **Select Output Location**: Click "Select Location" and choose where to save the video
   - Recommended: Save as `.mp4` format
   - The output will be a 4K MP4 file ready for YouTube

4. **Create Video**: Click "Create 4K Video" button
   - Progress will be shown in the status area
   - This may take several minutes depending on video length

## Video Quality Settings

The application uses the following settings for maximum quality:

- **Resolution**: 3840x2160 (4K UHD)
- **Video Codec**: H.264 (libx264)
- **Video Quality**: CRF 18 (near-lossless)
- **Preset**: Slow (best quality encoding)
- **Pixel Format**: yuv420p (YouTube compatible)
- **Frame Rate**: 30 fps
- **Audio Codec**: AAC
- **Audio Bitrate**: 384 kbps

These settings ensure the highest possible quality suitable for YouTube's 4K format.

## How It Works

1. **Image Processing**: The selected image is resized to 4K resolution using high-quality LANCZOS resampling algorithm, maintaining aspect ratio with black padding if needed.

2. **Audio Processing**: All selected audio files are loaded and processed:
   - Supports multiple formats (WAV, MP3, M4A, FLAC, AAC, OGG)
   - Fade-in (2 seconds) applied to each file
   - Fade-out (2 seconds) applied to each file
   - Files are concatenated sequentially
   - Total duration determines video length

3. **Video Creation**: FFmpeg creates a video:
   - Static 4K image displayed for the full audio duration
   - Audio track synchronized with video
   - Output in MP4 format with YouTube-optimized settings

## Troubleshooting

### FFmpeg Not Found Error

If you see "FFmpeg Not Found":
- Make sure FFmpeg is installed (see Installation section)
- Verify FFmpeg is in your system PATH
- Test by running `ffmpeg -version` in terminal/command prompt

### Audio Processing Errors

- Ensure all files are valid audio files (WAV, MP3, M4A, FLAC, AAC, or OGG)
- Check that at least one audio file is selected
- Verify files are not corrupted
- For random selection, ensure your directory contains enough audio files to meet the target duration

### Image Processing Issues

- Use high-quality source images for best results
- Supported formats: JPG, JPEG, PNG, BMP, TIFF

### Video Creation Takes Too Long

- Large audio files will result in longer processing times
- This is normal - FFmpeg is doing high-quality encoding
- Be patient, especially for videos over 1 hour long

## File Structure

```
Video_Edit/
├── main.py              # Main GUI application
├── video_processor.py   # Video creation logic with FFmpeg
├── audio_processor.py   # Audio concatenation with fades
├── image_processor.py   # Image resizing to 4K
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## License

This project is provided as-is for creating high-quality 4K videos.

## Notes

- Temporary files are automatically cleaned up after video creation
- The image will be displayed for the entire duration of the concatenated audio
- Audio files can be in various formats (WAV, MP3, M4A, FLAC, AAC, OGG)
- Random selection automatically avoids duplicate files and searches all subdirectories
- For best YouTube results, use high-bitrate source audio files
- Random selection uses a 30% tolerance for target duration to ensure flexibility

# 4K_Video_Maker
