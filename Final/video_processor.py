"""
Video processor module for creating 4K videos using FFmpeg with YouTube-optimized settings.
"""

import subprocess
import os
import re
import tempfile
import shutil
import math
try:
    from player_overlay_playwright import generate_overlay_frames, PLAYER_WIDTH, PLAYER_HEIGHT, PADDING_X, PADDING_Y, close_browser
except ImportError:
    # Fallback to PIL-based renderer if Playwright not available
    from player_overlay import generate_overlay_frames, PLAYER_WIDTH, PLAYER_HEIGHT, PADDING_X, PADDING_Y
    close_browser = None


def estimate_video_file_size(duration_seconds, video_bitrate_mbps=60, audio_bitrate_kbps=384):
    """
    Estimate the file size of the output video.
    
    Args:
        duration_seconds: Total duration of the video in seconds
        video_bitrate_mbps: Video bitrate in Mbps (default: 60 for 4K H.264 at CRF 18)
        audio_bitrate_kbps: Audio bitrate in kbps (default: 384)
    
    Returns:
        Estimated file size in MB (float)
    """
    # Convert bitrates to bits per second
    video_bitrate_bps = video_bitrate_mbps * 1_000_000  # Mbps to bps
    audio_bitrate_bps = audio_bitrate_kbps * 1_000  # kbps to bps
    
    # Total bitrate in bits per second
    total_bitrate_bps = video_bitrate_bps + audio_bitrate_bps
    
    # File size in bits
    file_size_bits = total_bitrate_bps * duration_seconds
    
    # Convert to bytes
    file_size_bytes = file_size_bits / 8
    
    # Convert to MB
    file_size_mb = file_size_bytes / (1024 * 1024)
    
    return file_size_mb


def format_file_size(mb_size):
    """
    Format file size in a human-readable format.
    
    Args:
        mb_size: File size in MB
    
    Returns:
        Formatted string (e.g., "123.4 MB" or "1.2 GB")
    """
    if mb_size < 1024:
        return f"{mb_size:.1f} MB"
    else:
        gb_size = mb_size / 1024
        return f"{gb_size:.2f} GB"


def create_overlay_video(overlay_frames, total_duration, fps=30, temp_dir=None):
    """
    Save overlay frames as PNG images for direct use in FFmpeg (bypassing video encoding).
    
    Args:
        overlay_frames: List of (frame_number, PIL Image) tuples
        total_duration: Total video duration in seconds
        fps: Frame rate
        temp_dir: Temporary directory for frames
    
    Returns:
        Tuple of (temp_dir, temp_dir) for compatibility with existing code
    """
    if temp_dir is None:
        temp_dir = tempfile.mkdtemp()
    
    # Save frames as PNG images with sequential naming starting from 0
    num_frames = len(overlay_frames)
    
    for i, (frame_num, frame_img) in enumerate(overlay_frames):
        # FFmpeg expects sequential numbering starting from 0 for pattern matching
        frame_path = os.path.join(temp_dir, f"frame_{i:06d}.png")
        frame_img.save(frame_path, 'PNG')
    
    # Return temp_dir as both values for compatibility
    return temp_dir, temp_dir


def create_4k_video(image_path, audio_path, output_path, fps=30, progress_callback=None, audio_files_info=None, overlay_video_path=None, overlay_temp_dir=None, audio_file_paths=None):
    """
    Create a 4K video (3840x2160) with static image and audio track.
    Optionally includes music player overlay.
    
    Args:
        image_path: Path to the 4K image file
        audio_path: Path to the concatenated audio file (WAV)
        output_path: Path for the output video file
        fps: Frame rate (default: 30 fps)
        progress_callback: Optional callback function(current_time, total_duration) for progress updates
        audio_files_info: Optional list of audio file info dicts with 'path' and 'duration' for overlay
        overlay_video_path: Path to overlay PNG frames directory (now used as temp dir)
        overlay_temp_dir: Temporary directory containing PNG frames
    
    Returns:
        Path to the created video file
    """
    # YouTube 4K recommended settings
    # Resolution: 3840x2160
    # Video codec: H.264 (libx264)
    # Video bitrate: 50-68 Mbps (using 60 Mbps for high quality)
    # Pixel format: yuv420p (YouTube compatible)
    # Audio codec: AAC
    # Audio bitrate: 384 kbps
    # CRF: 18 (high quality, near-lossless)
    
    # Get total duration for progress tracking
    total_duration = get_audio_duration(audio_path)
    
    # Use provided overlay temp dir if available, otherwise generate if audio_files_info provided
    if overlay_temp_dir is None and audio_files_info:
        # Fallback: generate overlay if not provided (but this should be avoided in threaded context)
        overlay_frames = generate_overlay_frames(audio_files_info, total_duration, fps)
        overlay_temp_dir, _ = create_overlay_video(overlay_frames, total_duration, fps)
    
    # Build FFmpeg command
    ffmpeg_inputs = [
        '-loop', '1',  # Loop the image
        '-i', image_path,  # Input image
        '-i', audio_path,  # Input audio
    ]
    
    overlay_y = 2160 - PLAYER_HEIGHT - PADDING_Y
    
    # Build filter complex for overlay
    base_filter = 'scale=3840:2160:force_original_aspect_ratio=decrease,pad=3840:2160:(ow-iw)/2:(oh-ih)/2'
    
    if overlay_temp_dir:
        # Use PNG sequence directly for overlay (better alpha transparency)
        frame_pattern = os.path.join(overlay_temp_dir, "frame_%06d.png")
        
        ffmpeg_inputs.extend([
            '-framerate', str(fps),
            '-i', frame_pattern  # PNG sequence input
        ])
        
        # Composite overlay at bottom left with proper alpha blending
        video_filter = f'{base_filter}[base];[base][2:v]overlay={PADDING_X}:{overlay_y}[v]'
        
        ffmpeg_cmd = [
            'ffmpeg',
        ] + ffmpeg_inputs + [
            '-filter_complex', video_filter,
            '-map', '[v]',
            '-map', '1:a',  # Map audio
            '-c:v', 'libx264',  # Video codec
            '-preset', 'slow',  # Encoding preset (slower = better quality)
            '-crf', '18',  # Constant Rate Factor (lower = higher quality, 18 is near-lossless)
            '-pix_fmt', 'yuv420p',  # Pixel format (YouTube compatible)
            '-c:a', 'aac',  # Audio codec
            '-b:a', '384k',  # Audio bitrate
            '-shortest',  # Finish when shortest input ends
            '-y',  # Overwrite output file if exists
            output_path
        ]
    else:
        # No overlay - simpler command
        ffmpeg_cmd = [
            'ffmpeg',
        ] + ffmpeg_inputs + [
            '-r', str(fps),  # Frame rate
            '-vf', base_filter,
            '-c:v', 'libx264',  # Video codec
            '-preset', 'slow',  # Encoding preset (slower = better quality)
            '-crf', '18',  # Constant Rate Factor (lower = higher quality, 18 is near-lossless)
            '-pix_fmt', 'yuv420p',  # Pixel format (YouTube compatible)
            '-c:a', 'aac',  # Audio codec
            '-b:a', '384k',  # Audio bitrate
            '-shortest',  # Finish when shortest input ends
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
        
        # Parse progress from stderr (FFmpeg writes progress info to stderr)
        current_time = 0.0
        progress_pattern = re.compile(r'time=(\d+):(\d+):(\d+\.\d+)')
        
        while True:
            output_line = process.stderr.readline()
            if not output_line and process.poll() is not None:
                break
            
            # Extract time from FFmpeg output line
            # Format: "frame=  123 fps= 25 q=28.0 size=    1024kB time=00:00:05.12 bitrate=1638.4kbits/s"
            match = progress_pattern.search(output_line)
            if match:
                hours = int(match.group(1))
                minutes = int(match.group(2))
                seconds = float(match.group(3))
                current_time = hours * 3600 + minutes * 60 + seconds
                
                # Call progress callback if provided
                if progress_callback:
                    try:
                        progress_callback(current_time, total_duration)
                    except Exception:
                        pass  # Ignore callback errors
        
        # Wait for process to complete
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr if stderr else stdout
            raise RuntimeError(f"FFmpeg error: {error_msg}")
        
        # Note: overlay temp directory cleanup is handled by caller (main.py)
        # to avoid issues with thread-local browser cleanup
        
        if os.path.exists(output_path):
            return output_path
        else:
            raise FileNotFoundError(f"Video file was not created: {output_path}")
            
    except FileNotFoundError:
        raise FileNotFoundError(
            "FFmpeg not found. Please install FFmpeg and ensure it's in your system PATH."
        )
    except Exception as e:
        raise RuntimeError(f"FFmpeg error: {str(e)}")


def get_audio_duration(audio_path):
    """
    Get duration of audio file using FFprobe.
    
    Args:
        audio_path: Path to audio file
    
    Returns:
        Duration in seconds (float)
    """
    try:
        ffprobe_cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_path
        ]
        
        result = subprocess.run(
            ffprobe_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        
        duration = float(result.stdout.strip())
        return duration
        
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        # Fallback: use pydub if available
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_wav(audio_path)
            return len(audio) / 1000.0
        except Exception:
            raise RuntimeError("Could not determine audio duration. FFprobe or pydub required.")


def generate_single_track_overlay_frames(audio_file_info, fps=30, overlay_width=600, overlay_height=174):
    """
    Generate overlay frames for a single audio track at specified resolution.
    
    Args:
        audio_file_info: Dict with 'path' and 'duration' keys
        fps: Frames per second (default: 30)
        overlay_width: Width of overlay in pixels (default: 600)
        overlay_height: Height of overlay in pixels (default: 174)
    
    Returns:
        List of (frame_number, PIL Image) tuples - one frame per video frame
    """
    try:
        from player_overlay_playwright import create_player_overlay_frame, extract_song_title
        use_playwright = True
    except ImportError:
        from player_overlay import create_player_overlay_frame, extract_track_name
        use_playwright = False
    
    frames = []
    frame_duration = 1.0 / fps
    track_path = audio_file_info['path']
    track_duration = audio_file_info['duration']
    
    if use_playwright:
        song_title = extract_song_title(track_path)
    else:
        song_title = extract_track_name(track_path)
    
    # Calculate total number of frames needed for this track
    num_frames = math.ceil(track_duration * fps)
    
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
            # PIL version (no fade effects)
            frame = create_player_overlay_frame(
                song_title, current_time, track_duration,
                width=overlay_width, height=overlay_height
            )
        
        # Ensure frame is exactly the right size (frames should already be correct size from create_player_overlay_frame)
        # But we'll verify and resize if needed
        if frame.size != (overlay_width, overlay_height):
            from PIL import Image
            frame = frame.resize((overlay_width, overlay_height), Image.Resampling.LANCZOS)
        
        frames.append((frame_num, frame))
    
    return frames


def export_overlay_video(audio_file_info, output_path, fps=30, progress_callback=None, overlay_width=600, overlay_height=174):
    """
    Export a single overlay video with alpha channel at 600x174 resolution.
    
    Args:
        audio_file_info: Dict with 'path' and 'duration' keys
        output_path: Path for the output MOV file
        fps: Frame rate (default: 30 fps)
        progress_callback: Optional callback function(current_time, total_duration) for progress updates
        overlay_width: Width of overlay in pixels (default: 600)
        overlay_height: Height of overlay in pixels (default: 174)
    
    Returns:
        Path to the created video file
    """
    # Get track duration
    track_duration = audio_file_info['duration']
    
    # Generate overlay frames at specified resolution
    overlay_frames = generate_single_track_overlay_frames(
        audio_file_info, fps, overlay_width, overlay_height
    )
    
    # Save frames to temporary directory
    temp_dir = tempfile.mkdtemp()
    
    # Save frames as PNG images with sequential naming starting from 0
    for i, (frame_num, frame_img) in enumerate(overlay_frames):
        # Ensure frame is RGBA for alpha channel
        if frame_img.mode != 'RGBA':
            frame_img = frame_img.convert('RGBA')
        
        frame_path = os.path.join(temp_dir, f"frame_{i:06d}.png")
        frame_img.save(frame_path, 'PNG')
    
    # Build FFmpeg command for ProRes 4444 with alpha channel
    frame_pattern = os.path.join(temp_dir, "frame_%06d.png")
    
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
        
        # Parse progress from stderr (FFmpeg writes progress info to stderr)
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
                
                # Call progress callback if provided
                if progress_callback:
                    try:
                        progress_callback(current_time, track_duration)
                    except Exception:
                        pass  # Ignore callback errors
        
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
    """
    Check if FFmpeg is installed and available in system PATH.
    
    Returns:
        True if FFmpeg is available, False otherwise
    """
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
