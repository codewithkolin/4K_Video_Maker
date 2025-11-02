"""
Simplified Music Player Overlay Renderer
Creates overlay frames with horizontal progress bar design for 4K video.
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math


# Color constants
TEAL = "#00ffcc"
WHITE = "#ffffff"
GRAY = "#808080"

# Player dimensions (38:11 ratio as requested)
# Width: 600 pixels (as specified)
# For 38:11 ratio: height = width × 11/38 = 600 × 11/38 ≈ 173.68
# Must be divisible by 2 for H.264 encoding (yuv420p)
# Adjusted to even number: 600 × 174
# Actual ratio: 600/174 = 3.4483 (very close to 38/11 = 3.4545)
PLAYER_WIDTH = 600
PLAYER_HEIGHT = 174

# Padding from bottom left
# X: right offset, Y: up from bottom offset
PADDING_X = 100
PADDING_Y = 150


def extract_track_name(filename):
    """
    Extract track name from filename.
    
    Args:
        filename: Full path or just filename
    
    Returns:
        Track name without extension
    """
    base_name = os.path.basename(filename)
    track_name = os.path.splitext(base_name)[0]
    
    # Replace underscores with spaces
    track_name = track_name.replace('_', ' ')
    
    return track_name


def format_time(seconds):
    """
    Format time in MM:SS format.
    
    Args:
        seconds: Time in seconds (float or int)
    
    Returns:
        Formatted time string (e.g., "3:45")
    """
    total_seconds = int(seconds)
    minutes = total_seconds // 60
    secs = total_seconds % 60
    return f"{minutes}:{secs:02d}"


def draw_icon_heart(draw, x, y, size, color=WHITE):
    """Draw a simple heart icon."""
    # Simplified heart shape
    half_size = size / 2
    
    # Left curve
    draw.ellipse([x, y, x + half_size, y + half_size], fill=color)
    # Right curve
    draw.ellipse([x + half_size, y, x + size, y + half_size], fill=color)
    # Bottom triangle
    points = [
        (x, y + half_size * 0.5),
        (x + half_size, y + size),
        (x + size, y + half_size * 0.5)
    ]
    draw.polygon(points, fill=color)


def draw_icon_pause(draw, x, y, size, color=WHITE):
    """Draw pause icon (two vertical bars)."""
    bar_width = size * 0.3
    bar_height = size * 0.8
    gap = size * 0.2
    
    # Left bar
    draw.rectangle(
        [x, y + size * 0.1, x + bar_width, y + size * 0.9],
        fill=color
    )
    
    # Right bar
    draw.rectangle(
        [x + bar_width + gap, y + size * 0.1, x + bar_width * 2 + gap, y + size * 0.9],
        fill=color
    )


def draw_horizontal_progress_bar(draw, x, y, width, height, progress, color_filled=TEAL, color_unfilled=GRAY):
    """
    Draw horizontal progress bar with moving circle indicator.
    
    Args:
        draw: PIL ImageDraw object
        x, y: Top-left position of the bar
        width: Total width of the progress bar
        height: Height of the bar
        progress: Progress value 0.0 to 1.0
        color_filled: Color for filled portion
        color_unfilled: Color for unfilled portion
    
    Returns:
        Position of the moving circle (center_x, center_y)
    """
    bar_height = int(height * 0.3)  # Thinner bar
    bar_y = y + (height - bar_height) // 2
    
    # Draw unfilled bar (background)
    draw.rectangle(
        [x, bar_y, x + width, bar_y + bar_height],
        fill=color_unfilled,
        outline=WHITE,
        width=2
    )
    
    # Draw filled portion
    if progress > 0:
        filled_width = int(width * progress)
        draw.rectangle(
            [x, bar_y, x + filled_width, bar_y + bar_height],
            fill=color_filled
        )
    
    # Draw moving circle indicator
    circle_radius = bar_height * 1.5
    circle_x = x + int(width * progress)
    circle_y = bar_y + bar_height // 2
    
    # Draw circle
    draw.ellipse(
        [circle_x - circle_radius, circle_y - circle_radius,
         circle_x + circle_radius, circle_y + circle_radius],
        fill=color_filled,
        outline=WHITE,
        width=3
    )
    
    return circle_x, circle_y


def create_player_overlay_frame(track_name, current_time, total_time, width=PLAYER_WIDTH, height=PLAYER_HEIGHT):
    """
    Create a single overlay frame with simplified music player UI.
    
    Args:
        track_name: Name of the current track
        current_time: Current playback time in seconds
        total_time: Total track duration in seconds
        width: Width of overlay frame
        height: Height of overlay frame
    
    Returns:
        PIL Image with transparent background
    """
    # Create image with fully transparent background
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # No background rectangle - fully transparent
    
    # Calculate progress (0.0 to 1.0)
    if total_time > 0:
        progress = min(current_time / total_time, 1.0)
    else:
        progress = 0.0
    
    # Layout positioning
    content_x = width * 0.08
    content_width = width * 0.84
    
    # 1. Track name (top)
    track_y = height * 0.15
    try:
        font_size = int(height * 0.12)
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except:
        font = None
    
    if font:
        draw.text((content_x, track_y), track_name, fill=WHITE, font=font)
    else:
        draw.text((content_x, track_y), track_name, fill=WHITE)
    
    # 2. Progress bar (middle)
    progress_y = height * 0.45
    progress_height = height * 0.15
    
    circle_x, circle_y = draw_horizontal_progress_bar(
        draw,
        content_x,
        progress_y,
        content_width,
        progress_height,
        progress,
        TEAL,
        GRAY
    )
    
    # 3. Time displays
    try:
        time_font_size = int(height * 0.08)
        time_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", time_font_size)
    except:
        time_font = None
    
    # Current time (below moving circle)
    current_time_str = format_time(current_time)
    if time_font:
        time_bbox = draw.textbbox((0, 0), current_time_str, font=time_font)
        time_width = time_bbox[2] - time_bbox[0]
    else:
        time_bbox = draw.textbbox((0, 0), current_time_str)
        time_width = time_bbox[2] - time_bbox[0]
    
    current_time_x = circle_x - time_width / 2
    current_time_y = progress_y + progress_height + height * 0.05
    
    if time_font:
        draw.text((current_time_x, current_time_y), current_time_str, fill=WHITE, font=time_font)
    else:
        draw.text((current_time_x, current_time_y), current_time_str, fill=WHITE)
    
    # Total time (right end of progress bar)
    total_time_str = format_time(total_time)
    if time_font:
        total_bbox = draw.textbbox((0, 0), total_time_str, font=time_font)
        total_width = total_bbox[2] - total_bbox[0]
    else:
        total_bbox = draw.textbbox((0, 0), total_time_str)
        total_width = total_bbox[2] - total_bbox[0]
    
    total_time_x = content_x + content_width - total_width
    total_time_y = progress_y + progress_height + height * 0.05
    
    if time_font:
        draw.text((total_time_x, total_time_y), total_time_str, fill=WHITE, font=time_font)
    else:
        draw.text((total_time_x, total_time_y), total_time_str, fill=WHITE)
    
    # 4. Icons (bottom)
    icon_size = height * 0.1
    icon_y = height * 0.75
    
    # Heart icon (left side)
    heart_x = content_x
    draw_icon_heart(draw, heart_x, icon_y, icon_size, WHITE)
    
    # Pause icon (right side)
    pause_x = content_x + content_width - icon_size
    draw_icon_pause(draw, pause_x, icon_y, icon_size, WHITE)
    
    return img


def generate_overlay_frames(audio_files, total_duration, fps=30):
    """
    Generate overlay frames for entire video duration at specified FPS.
    
    Args:
        audio_files: List of dicts with 'path' and 'duration' keys
        total_duration: Total video duration in seconds
        fps: Frames per second (default: 30)
    
    Returns:
        List of (timestamp, PIL Image) tuples - one frame per video frame
    """
    frames = []
    frame_duration = 1.0 / fps  # Duration of each frame in seconds
    
    for i, audio_info in enumerate(audio_files):
        track_path = audio_info['path']
        track_duration = audio_info['duration']
        track_name = extract_track_name(track_path)
        
        # Calculate total number of frames needed for this track
        # Use ceil to ensure we have enough frames to cover the full duration
        num_frames = math.ceil(track_duration * fps)
        
        # Generate frames at FPS rate
        for frame_num in range(num_frames):
            # Calculate current time within this track
            # Use frame_num * frame_duration for precise timing
            current_time = frame_num * frame_duration
            
            # For the last frame, ensure it shows the exact track duration
            # For other frames, clamp to track_duration to ensure we never exceed it
            if frame_num == num_frames - 1:
                current_time = track_duration
            else:
                current_time = min(current_time, track_duration)
            
            frame = create_player_overlay_frame(track_name, current_time, track_duration)
            frames.append((frame_num, frame))
    
    return frames
