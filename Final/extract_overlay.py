#!/usr/bin/env python3
"""
Standalone Overlay Extraction Script
Extracts music overlay videos from audio files with customizable dimensions.
Maintains aspect ratio 600:174 but allows manual entry of horizontal and vertical dimensions.
Text scales proportionally with resolution changes.
"""

import os
import sys
import math
import subprocess
import tempfile
import shutil
import re
from pydub import AudioSegment

# Try to import overlay modules
try:
    from player_overlay_playwright import create_player_overlay_frame, extract_song_title, close_browser
    use_playwright = True
except ImportError:
    try:
        from player_overlay import create_player_overlay_frame, extract_track_name
        use_playwright = False
    except ImportError:
        print("Error: Could not import overlay modules.")
        print("Please ensure player_overlay.py or player_overlay_playwright.py is in the same directory.")
        sys.exit(1)


def get_audio_duration(audio_path):
    """Get duration of audio file."""
    try:
        audio = AudioSegment.from_file(audio_path)
        return len(audio) / 1000.0  # Convert milliseconds to seconds
    except Exception as e:
        raise RuntimeError(f"Could not read audio file: {e}")


def get_audio_files_info(audio_files):
    """Get information about each audio file including duration."""
    files_info = []
    for audio_file in audio_files:
        duration = get_audio_duration(audio_file)
        files_info.append({
            'path': audio_file,
            'duration': duration
        })
    return files_info


def generate_single_track_overlay_frames(audio_file_info, fps=30, overlay_width=600, overlay_height=174):
    """
    Generate overlay frames for a single audio track at specified resolution.
    Text scales proportionally with resolution changes.
    
    Args:
        audio_file_info: Dict with 'path' and 'duration' keys
        fps: Frames per second (default: 30)
        overlay_width: Width of overlay in pixels
        overlay_height: Height of overlay in pixels
    
    Returns:
        List of (frame_number, PIL Image) tuples - one frame per video frame
    """
    frames = []
    frame_duration = 1.0 / fps
    track_path = audio_file_info['path']
    track_duration = audio_file_info['duration']
    
    # Extract track name
    if use_playwright:
        song_title = extract_song_title(track_path)
    else:
        song_title = extract_track_name(track_path)
    
    # Calculate total number of frames needed for this track
    num_frames = math.ceil(track_duration * fps)
    
    print(f"Generating {num_frames} frames for '{song_title}'...")
    
    # Generate frames at FPS rate (no fade in/out effects)
    for frame_num in range(num_frames):
        # Calculate current time within this track
        current_time = frame_num * frame_duration
        
        # For the last frame, ensure it shows the exact track duration
        if frame_num == num_frames - 1:
            current_time = track_duration
        else:
            current_time = min(current_time, track_duration)
        
        # Generate frame at specified resolution (no fade effects)
        if use_playwright:
            # No fade in/out - always fully visible and centered
            frame = create_player_overlay_frame(
                song_title, current_time, track_duration,
                width=overlay_width, height=overlay_height,
                opacity=1.0, slide_offset=0.0
            )
        else:
            # PIL version (text scales proportionally via height-based font sizes)
            frame = create_player_overlay_frame(
                song_title, current_time, track_duration,
                width=overlay_width, height=overlay_height
            )
        
        # Ensure frame is exactly the right size
        if frame.size != (overlay_width, overlay_height):
            from PIL import Image
            frame = frame.resize((overlay_width, overlay_height), Image.Resampling.LANCZOS)
        
        frames.append((frame_num, frame))
    
    return frames


def export_overlay_video(audio_file_info, output_path, fps=30, overlay_width=600, overlay_height=174):
    """
    Export a single overlay video with alpha channel.
    
    Args:
        audio_file_info: Dict with 'path' and 'duration' keys
        output_path: Path for the output MOV file
        fps: Frame rate (default: 30 fps)
        overlay_width: Width of overlay in pixels
        overlay_height: Height of overlay in pixels
    
    Returns:
        Path to the created video file
    """
    track_duration = audio_file_info['duration']
    
    print(f"Generating overlay frames at {overlay_width}x{overlay_height}...")
    # Generate overlay frames at specified resolution
    overlay_frames = generate_single_track_overlay_frames(
        audio_file_info, fps, overlay_width, overlay_height
    )
    
    # Save frames to temporary directory
    temp_dir = tempfile.mkdtemp()
    print(f"Saving {len(overlay_frames)} frames to temporary directory...")
    
    # Save frames as PNG images with sequential naming starting from 0
    for i, (frame_num, frame_img) in enumerate(overlay_frames):
        # Ensure frame is RGBA for alpha channel
        if frame_img.mode != 'RGBA':
            frame_img = frame_img.convert('RGBA')
        
        frame_path = os.path.join(temp_dir, f"frame_{i:06d}.png")
        frame_img.save(frame_path, 'PNG')
        
        # Progress indicator
        if (i + 1) % 30 == 0:
            print(f"  Saved {i + 1}/{len(overlay_frames)} frames...")
    
    # Build FFmpeg command for ProRes 4444 with alpha channel
    frame_pattern = os.path.join(temp_dir, "frame_%06d.png")
    
    print("Encoding video with ProRes 4444 (this may take a while)...")
    # ProRes 4444 supports alpha channel and is ideal for Premiere Pro
    ffmpeg_cmd = [
        'ffmpeg',
        '-framerate', str(fps),
        '-i', frame_pattern,  # PNG sequence input
        '-c:v', 'prores_ks',  # ProRes codec
        '-profile:v', '4444',  # ProRes 4444 profile (supports alpha)
        '-pix_fmt', 'yuva444p10le',  # 10-bit YUV with alpha channel
        '-r', str(fps),  # Output frame rate
        '-y',  # Overwrite output file if exists
        output_path
    ]
    
    try:
        # Start FFmpeg process
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Parse progress from stderr
        current_time = 0.0
        progress_pattern = re.compile(r'time=(\d+):(\d+):(\d+\.\d+)')
        
        while True:
            output_line = process.stderr.readline()
            if not output_line and process.poll() is not None:
                break
            
            # Extract time from FFmpeg output line
            match = progress_pattern.search(output_line)
            if match:
                hours = int(match.group(1))
                minutes = int(match.group(2))
                seconds = float(match.group(3))
                current_time = hours * 3600 + minutes * 60 + seconds
                
                if track_duration > 0:
                    progress = (current_time / track_duration) * 100
                    print(f"\r  Encoding progress: {progress:.1f}% ({current_time:.1f}s / {track_duration:.1f}s)", end='', flush=True)
        
        print()  # New line after progress
        
        # Wait for process to complete
        stdout, stderr = process.communicate()
        
        # Cleanup temp directory
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass  # Ignore cleanup errors
        
        if process.returncode != 0:
            error_msg = stderr if stderr else stdout
            raise RuntimeError(f"FFmpeg error: {error_msg}")
        
        if os.path.exists(output_path):
            return output_path
        else:
            raise FileNotFoundError(f"Video file was not created: {output_path}")
            
    except FileNotFoundError:
        # Cleanup temp directory on error
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
        raise FileNotFoundError(
            "FFmpeg not found. Please install FFmpeg and ensure it's in your system PATH."
        )
    except Exception as e:
        # Cleanup temp directory on error
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
        raise RuntimeError(f"FFmpeg error: {str(e)}")


def check_ffmpeg_available():
    """Check if FFmpeg is installed and available in system PATH."""
    try:
        subprocess.run(
            ['ffmpeg', '-version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def main():
    """Main function for standalone overlay extraction."""
    print("=" * 60)
    print("Overlay Extraction Script")
    print("=" * 60)
    print()
    
    # Check FFmpeg availability
    if not check_ffmpeg_available():
        print("ERROR: FFmpeg is not installed or not in your system PATH.")
        print("Please install FFmpeg:")
        print("  macOS: brew install ffmpeg")
        print("  Windows: Download from https://ffmpeg.org/download.html")
        print("  Linux: sudo apt-get install ffmpeg")
        sys.exit(1)
    
    # Get audio file(s)
    print("Enter audio file path(s) separated by commas:")
    audio_input = input("> ").strip()
    audio_files = [f.strip().strip('"\'') for f in audio_input.split(',')]
    audio_files = [f for f in audio_files if f]  # Remove empty strings
    
    if not audio_files:
        print("ERROR: No audio files specified.")
        sys.exit(1)
    
    # Verify files exist
    for audio_file in audio_files:
        if not os.path.exists(audio_file):
            print(f"ERROR: Audio file not found: {audio_file}")
            sys.exit(1)
    
    # Get dimensions
    print()
    print("Enter overlay dimensions:")
    print("  Recommended aspect ratio: 600:174")
    print("  (Text scales proportionally with resolution)")
    
    try:
        print()
        overlay_width = int(input("  Horizontal (width) in pixels: ").strip())
        overlay_height = int(input("  Vertical (height) in pixels: ").strip())
        
        if overlay_width <= 0 or overlay_height <= 0:
            raise ValueError("Dimensions must be positive integers")
    except ValueError as e:
        print(f"ERROR: Invalid dimensions: {e}")
        sys.exit(1)
    
    # Calculate aspect ratio
    current_ratio = overlay_width / overlay_height
    recommended_ratio = 600 / 174
    
    print()
    print(f"Dimensions: {overlay_width}x{overlay_height}")
    print(f"Aspect ratio: {current_ratio:.3f} (recommended: {recommended_ratio:.3f})")
    if abs(current_ratio - recommended_ratio) > 0.1:
        print("  WARNING: Aspect ratio differs significantly from recommended 600:174")
    
    # Get output directory
    print()
    output_dir = input("Enter output directory (press Enter for current directory): ").strip()
    if not output_dir:
        output_dir = os.getcwd()
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"Created output directory: {output_dir}")
    
    # Get audio files info
    print()
    print("Reading audio files...")
    audio_files_info = get_audio_files_info(audio_files)
    total_files = len(audio_files_info)
    
    # Close any existing browser before processing
    if use_playwright:
        try:
            close_browser()
        except:
            pass
    
    # Process each audio file
    print()
    print(f"Processing {total_files} audio file(s)...")
    print("=" * 60)
    
    for i, audio_info in enumerate(audio_files_info):
        track_path = audio_info['path']
        track_duration = audio_info['duration']
        
        # Extract track name for filename
        if use_playwright:
            track_name = extract_song_title(track_path)
        else:
            track_name = extract_track_name(track_path)
        
        # Clean track name for filename
        safe_track_name = "".join(c for c in track_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_track_name = safe_track_name.replace(' ', '_')
        
        if not safe_track_name:
            safe_track_name = f"track_{i+1}"
        
        # Create output filename
        output_filename = f"{safe_track_name}_overlay.mov"
        output_path = os.path.join(output_dir, output_filename)
        
        # Handle duplicates
        counter = 1
        while os.path.exists(output_path):
            output_path = os.path.join(output_dir, f"{safe_track_name}_overlay_{counter}.mov")
            counter += 1
        
        output_filename = os.path.basename(output_path)
        
        print()
        print(f"[{i+1}/{total_files}] Processing: {track_name}")
        print(f"  Duration: {track_duration:.2f} seconds")
        print(f"  Output: {output_filename}")
        print()
        
        try:
            # Export overlay video
            export_overlay_video(
                audio_info,
                output_path,
                fps=30,
                overlay_width=overlay_width,
                overlay_height=overlay_height
            )
            
            print(f"  ✓ Successfully exported: {output_filename}")
            
        except Exception as e:
            print(f"  ✗ Error exporting {track_name}: {e}")
            continue
    
    # Close browser after processing
    if use_playwright:
        try:
            close_browser()
        except:
            pass
    
    print()
    print("=" * 60)
    print("Overlay extraction complete!")
    print(f"Output directory: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user.")
        if use_playwright:
            try:
                close_browser()
            except:
                pass
        sys.exit(1)

