"""
High-Quality Music Player Overlay Renderer using Playwright
Generates professional-quality overlay frames with HTML/CSS rendering.
"""

from playwright.sync_api import sync_playwright, Browser, Page
import os
import tempfile
import time
import threading
import math


# Player dimensions (38:11 ratio as requested)
# Width: 600 pixels (as specified)
# For 38:11 ratio: height = width × 11/38 = 600 × 11/38 ≈ 173.68
# Adjusted to even number for H.264 compatibility: 600 × 174
# Actual ratio: 600/174 = 3.4483 (very close to 38/11 = 3.4545)
PLAYER_WIDTH = 600
PLAYER_HEIGHT = 174

# Padding from bottom left
# X: right offset, Y: up from bottom offset
PADDING_X = 100
PADDING_Y = 150

# Fade duration for player appearance/disappearance (in seconds)
FADE_IN_DURATION = 3.0  # 1 second fade in when track starts
FADE_OUT_DURATION = 3.0  # 1 second fade out when track ends

# Browser instance cache (thread-local to avoid cross-thread issues)
_browser: Browser = None
_playwright = None
_browser_thread_id = None
import threading


def get_browser():
    """Get or create a cached Playwright browser instance for the current thread."""
    global _browser, _playwright, _browser_thread_id
    
    current_thread_id = threading.current_thread().ident
    
    # If browser was created in a different thread, close it first
    if _browser is not None and _browser_thread_id != current_thread_id:
        try:
            if _cached_page:
                _cached_page.close()
                _cached_page = None
            _browser.close()
            _playwright.stop()
        except:
            pass
        _browser = None
        _playwright = None
    
    # Create new browser instance for this thread
    if _browser is None:
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(headless=True)
        _browser_thread_id = current_thread_id
    
    return _browser


def close_browser():
    """Close the browser instance and cached page."""
    global _browser, _playwright, _cached_page, _browser_thread_id
    
    if _cached_page:
        try:
            _cached_page.close()
        except:
            pass
        _cached_page = None
    
    if _browser:
        try:
            _browser.close()
        except:
            pass
        _browser = None
    
    if _playwright:
        try:
            _playwright.stop()
        except:
            pass
        _playwright = None
    
    _browser_thread_id = None


def extract_song_title(filename):
    """
    Extract song title from filename.
    
    Args:
        filename: Full path or just filename
    
    Returns:
        Song title without extension
    """
    base_name = os.path.basename(filename)
    song_title = os.path.splitext(base_name)[0]
    
    # Replace underscores with spaces
    song_title = song_title.replace('_', ' ')
    
    # Remove common patterns like "Artist - Song" and keep just the song
    if ' - ' in song_title:
        song_title = song_title.split(' - ')[-1]
    
    return song_title


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


# Cached page for better performance
_cached_page = None
_html_template = None
_css_content = None


def _init_playwright_template():
    """Initialize and cache HTML template and CSS."""
    global _html_template, _css_content
    
    if _html_template is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        html_path = os.path.join(script_dir, "player_overlay.html")
        css_path = os.path.join(script_dir, "player_overlay.css")
        
        # Read HTML template
        with open(html_path, 'r', encoding='utf-8') as f:
            _html_template = f.read()
        
        # Read CSS
        with open(css_path, 'r', encoding='utf-8') as f:
            _css_content = f.read()
        
        # Inject CSS into HTML
        _html_template = _html_template.replace(
            '<link rel="stylesheet" href="player_overlay.css">',
            f'<style>{_css_content}</style>'
        )


def create_player_overlay_frame(song_title, current_time, total_time, width=PLAYER_WIDTH, height=PLAYER_HEIGHT, opacity=1.0, slide_offset=0.0):
    """
    Create a single overlay frame using Playwright HTML/CSS rendering.
    Optimized with cached page for better performance.
    
    Args:
        song_title: Name of the current song
        current_time: Current playback time in seconds
        total_time: Total track duration in seconds
        width: Width of overlay frame
        height: Height of overlay frame
        opacity: Opacity value from 0.0 to 1.0 for fade effects
        slide_offset: Vertical offset from bottom (0.0 = normal position, 1.0 = fully off screen below)
    
    Returns:
        PIL Image with transparent background
    """
    from PIL import Image
    import io
    
    global _cached_page
    
    browser = get_browser()
    _init_playwright_template()
    
    # Create or reuse cached page
    if _cached_page is None:
        _cached_page = browser.new_page()
        _cached_page.set_viewport_size({"width": width, "height": height})
        # Set background to transparent for screenshot
        _cached_page.set_content(_html_template)
        # Force transparent background
        _cached_page.evaluate("""
            document.body.style.backgroundColor = 'transparent';
            document.documentElement.style.backgroundColor = 'transparent';
        """)
        # Wait for initial render
        _cached_page.wait_for_timeout(50)
    
    # Calculate progress (0.0 to 1.0)
    if total_time > 0:
        progress = min(current_time / total_time, 1.0)
    else:
        progress = 0.0
    
    progress_percent = progress * 100
    
    # Calculate slide transform (0.0 = normal, 1.0 = fully below screen)
    translate_y = slide_offset * height  # Slide down/up effect
    
    # Update content using JavaScript (much faster than reloading page)
    js_code = f"""
    document.getElementById('song-title').textContent = {repr(song_title)};
    document.getElementById('artist-name').textContent = 'Neural Rhythms';
    document.getElementById('current-time').textContent = {repr(format_time(current_time))};
    document.getElementById('total-time').textContent = {repr(format_time(total_time))};
    document.getElementById('progress-filled').style.width = '{progress_percent}%';
    document.getElementById('progress-scrubber').style.left = '{progress_percent}%';
    document.querySelector('.player-container').style.transform = 'translateY({translate_y}px)';
    document.querySelector('.player-container').style.opacity = '{opacity}';
    """
    
    # Apply JavaScript updates
    _cached_page.evaluate(js_code)
    
    # Small delay for rendering update
    _cached_page.wait_for_timeout(10)
    
    # Capture screenshot with transparent background
    screenshot_bytes = _cached_page.screenshot(
        type='png',
        full_page=False,
        clip={'x': 0, 'y': 0, 'width': width, 'height': height},
        omit_background=True  # Ensure transparency
    )
    
    # Convert screenshot to PIL Image
    img = Image.open(io.BytesIO(screenshot_bytes))
    
    # Convert RGBA if needed
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Note: Opacity and slide transform are already applied via CSS/JavaScript above
    # No need to apply opacity again here as Playwright's screenshot captures the CSS transform
    
    return img


def generate_overlay_frames(audio_files, total_duration, fps=30):
    """
    Generate overlay frames for entire video duration at specified FPS.
    
    Args:
        audio_files: List of dicts with 'path' and 'duration' keys
        total_duration: Total video duration in seconds
        fps: Frames per second (default: 30)
    
    Returns:
        List of (frame_number, PIL Image) tuples - one frame per video frame
    """
    frames = []
    frame_duration = 1.0 / fps  # Duration of each frame in seconds
    
    for i, audio_info in enumerate(audio_files):
        track_path = audio_info['path']
        track_duration = audio_info['duration']
        song_title = extract_song_title(track_path)
        
        # Calculate total number of frames needed for this track
        # Use ceil to ensure we have enough frames to cover the full duration
        num_frames = math.ceil(track_duration * fps)
        
        # Calculate fade frames
        fade_in_frames = math.ceil(FADE_IN_DURATION * fps)
        fade_out_frames = math.ceil(FADE_OUT_DURATION * fps)
        
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
            
            # Calculate opacity and slide offset for fade in/out
            opacity = 1.0
            slide_offset = 0.0  # 0.0 = visible, 1.0 = below screen
            
            # Fade in at the start (slide up from bottom)
            if frame_num < fade_in_frames and fade_in_frames > 0:
                fade_progress = frame_num / fade_in_frames  # 0.0 to 1.0
                opacity = fade_progress  # Fade from transparent to opaque
                slide_offset = 1.0 - fade_progress  # Slide from bottom (1.0) to position (0.0)
            
            # Fade out at the end (slide down to bottom)
            elif frame_num >= num_frames - fade_out_frames and fade_out_frames > 0:
                frames_until_end = num_frames - frame_num
                fade_progress = frames_until_end / fade_out_frames  # 1.0 to 0.0
                opacity = fade_progress  # Fade from opaque to transparent
                slide_offset = 1.0 - fade_progress  # Slide from position (0.0) to bottom (1.0)
            
            frame = create_player_overlay_frame(song_title, current_time, track_duration, opacity=opacity, slide_offset=slide_offset)
            frames.append((frame_num, frame))
    
    return frames

