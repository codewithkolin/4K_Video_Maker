#!/usr/bin/env python3
"""
GUI Version of Overlay Extraction Script
Extracts music overlay videos from audio files with customizable dimensions.
Auto-calculates vertical dimension based on horizontal input (maintains 600:174 ratio).
Text scales proportionally with resolution changes.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import sys
import math
import subprocess
import tempfile
import shutil
import re
from pydub import AudioSegment
from audio_processor import find_all_audio_files

# Try to import overlay modules
try:
    from player_overlay_playwright import create_player_overlay_frame, extract_song_title, close_browser
    use_playwright = True
except ImportError:
    try:
        from player_overlay import create_player_overlay_frame, extract_track_name
        use_playwright = False
    except ImportError:
        messagebox.showerror(
            "Import Error",
            "Could not import overlay modules.\n\n"
            "Please ensure player_overlay.py or player_overlay_playwright.py is in the same directory."
        )
        sys.exit(1)


# Recommended aspect ratio
RECOMMENDED_RATIO = 600 / 174  # Approximately 3.448


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


def generate_single_track_overlay_frames(audio_file_info, fps=30, overlay_width=600, overlay_height=174, progress_callback=None):
    """
    Generate overlay frames for a single audio track at specified resolution.
    Text scales proportionally with resolution changes.
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
    
    # Generate frames at FPS rate (no fade in/out effects)
    for frame_num in range(num_frames):
        # Call progress callback periodically during frame generation
        if progress_callback and frame_num % 30 == 0:  # Update every 30 frames (~1 second at 30fps)
            try:
                current_time = frame_num * frame_duration
                progress_callback(current_time, track_duration, f"Generating frames: {frame_num + 1}/{num_frames}")
            except:
                pass
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


def export_overlay_video(audio_file_info, output_path, fps=30, overlay_width=600, overlay_height=174, progress_callback=None):
    """
    Export a single overlay video with alpha channel.
    """
    track_duration = audio_file_info['duration']
    
    # Generate overlay frames at specified resolution
    # Extract progress callback for frame generation (if provided, it will be called during encoding too)
    frame_gen_callback = None
    if progress_callback:
        # Wrap the callback to provide frame generation updates
        def frame_gen_wrapper(current_time, total_duration, message):
            if progress_callback:
                try:
                    # Adjust message to indicate frame generation
                    if message and "Generating" in message:
                        progress_callback(current_time, total_duration, message)
                except:
                    pass
        frame_gen_callback = frame_gen_wrapper
    
    overlay_frames = generate_single_track_overlay_frames(
        audio_file_info, fps, overlay_width, overlay_height, progress_callback=frame_gen_callback
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


class OverlayExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Overlay Extraction Tool")
        self.root.geometry("700x750")
        self.root.resizable(True, True)
        
        # Variables
        self.audio_files = []
        self.working_directory = None  # Single directory for both input and output
        self.horizontal_var = tk.StringVar(value="600")
        self.vertical_var = tk.StringVar(value="174")
        self.auto_calculate = tk.BooleanVar(value=True)
        
        # Check FFmpeg availability
        if not check_ffmpeg_available():
            messagebox.showerror(
                "FFmpeg Not Found",
                "FFmpeg is not installed or not in your system PATH.\n\n"
                "Please install FFmpeg:\n"
                "  macOS: brew install ffmpeg\n"
                "  Windows: Download from https://ffmpeg.org/download.html\n"
                "  Linux: sudo apt-get install ffmpeg\n\n"
                "The application will close."
            )
            root.quit()
            return
        
        self.create_widgets()
        
        # Bind horizontal entry to auto-calculate vertical
        self.horizontal_entry.bind('<KeyRelease>', self.on_horizontal_change)
    
    def create_widgets(self):
        # Title
        title_label = tk.Label(
            self.root,
            text="Overlay Extraction Tool",
            font=("Arial", 18, "bold")
        )
        title_label.pack(pady=15)
        
        subtitle_label = tk.Label(
            self.root,
            text="Extract music overlay videos with alpha channel",
            font=("Arial", 10),
            fg="gray"
        )
        subtitle_label.pack(pady=(0, 20))
        
        # Directory selection (both input and output)
        dir_frame = tk.Frame(self.root)
        dir_frame.pack(pady=10, padx=20, fill="x")
        
        tk.Label(dir_frame, text="Working Directory:", font=("Arial", 11, "bold")).pack(anchor="w")
        
        dir_info_label = tk.Label(
            dir_frame,
            text="Select a directory containing audio files. Overlays will be saved in the same directory.",
            font=("Arial", 9),
            fg="gray",
            anchor="w",
            wraplength=600
        )
        dir_info_label.pack(anchor="w", pady=(5, 5))
        
        dir_btn_frame = tk.Frame(dir_frame)
        dir_btn_frame.pack(fill="x", pady=5)
        
        self.dir_label = tk.Label(
            dir_btn_frame,
            text="No directory selected",
            fg="gray",
            anchor="w",
            wraplength=400
        )
        self.dir_label.pack(side="left", fill="x", expand=True)
        
        tk.Button(
            dir_btn_frame,
            text="Select Directory",
            command=self.select_directory,
            width=18
        ).pack(side="right", padx=(10, 0))
        
        # Audio files found
        audio_info_frame = tk.Frame(self.root)
        audio_info_frame.pack(pady=5, padx=20, fill="x")
        
        self.audio_label = tk.Label(
            audio_info_frame,
            text="No audio files found",
            fg="gray",
            anchor="w",
            wraplength=600,
            font=("Arial", 10)
        )
        self.audio_label.pack(anchor="w")
        
        # Dimensions section
        dims_frame = tk.Frame(self.root)
        dims_frame.pack(pady=15, padx=20, fill="x")
        
        tk.Label(dims_frame, text="Overlay Dimensions:", font=("Arial", 11, "bold")).pack(anchor="w")
        
        # Auto-calculate checkbox
        auto_frame = tk.Frame(dims_frame)
        auto_frame.pack(fill="x", pady=(5, 10))
        
        tk.Checkbutton(
            auto_frame,
            text="Auto-calculate vertical based on aspect ratio (600:174)",
            variable=self.auto_calculate,
            command=self.toggle_auto_calculate,
            font=("Arial", 10)
        ).pack(anchor="w")
        
        # Horizontal dimension
        horizontal_frame = tk.Frame(dims_frame)
        horizontal_frame.pack(fill="x", pady=5)
        
        tk.Label(horizontal_frame, text="Horizontal (width):", font=("Arial", 10), width=18, anchor="w").pack(side="left")
        self.horizontal_entry = tk.Entry(
            horizontal_frame,
            textvariable=self.horizontal_var,
            font=("Arial", 11),
            width=15
        )
        self.horizontal_entry.pack(side="left", padx=(10, 0))
        tk.Label(horizontal_frame, text="pixels", font=("Arial", 10), fg="gray").pack(side="left", padx=(5, 0))
        
        # Vertical dimension
        vertical_frame = tk.Frame(dims_frame)
        vertical_frame.pack(fill="x", pady=5)
        
        tk.Label(vertical_frame, text="Vertical (height):", font=("Arial", 10), width=18, anchor="w").pack(side="left")
        self.vertical_entry = tk.Entry(
            vertical_frame,
            textvariable=self.vertical_var,
            font=("Arial", 11),
            width=15,
            state="readonly" if self.auto_calculate.get() else "normal"
        )
        self.vertical_entry.pack(side="left", padx=(10, 0))
        tk.Label(vertical_frame, text="pixels", font=("Arial", 10), fg="gray").pack(side="left", padx=(5, 0))
        
        # Aspect ratio info
        self.ratio_label = tk.Label(
            dims_frame,
            text="Aspect ratio: 3.448 (recommended: 3.448)",
            font=("Arial", 9),
            fg="green"
        )
        self.ratio_label.pack(anchor="w", pady=(5, 0))
        
        
        # Progress section
        progress_frame = tk.Frame(self.root)
        progress_frame.pack(pady=20, padx=20, fill="x")
        
        self.progress_var = tk.StringVar(value="Ready to extract overlays")
        self.progress_label = tk.Label(
            progress_frame,
            textvariable=self.progress_var,
            font=("Arial", 10)
        )
        self.progress_label.pack()
        
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            length=400,
            maximum=100
        )
        self.progress_bar.pack(pady=10)
        
        self.progress_percent_var = tk.StringVar(value="0%")
        self.progress_percent_label = tk.Label(
            progress_frame,
            textvariable=self.progress_percent_var,
            font=("Arial", 14, "bold"),
            fg="blue"
        )
        self.progress_percent_label.pack()
        
        # Status text
        status_frame = tk.Frame(self.root)
        status_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        tk.Label(status_frame, text="Status Log:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        self.status_text = tk.Text(
            status_frame,
            height=6,
            width=70,
            wrap=tk.WORD,
            state="disabled",
            font=("Courier", 9)
        )
        self.status_text.pack(fill="both", expand=True)
        
        # Button frame - placed after status text, always visible
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=20, padx=20, fill="x")
        
        # Extract button
        self.extract_btn = tk.Button(
            button_frame,
            text="Extract Overlays",
            command=self.extract_overlays,
            font=("Arial", 12, "bold"),
            bg="#4CAF50",
            fg="white",
            width=20,
            height=2,
            state="disabled"
        )
        self.extract_btn.pack(side="left", padx=10)
        
        # Reset button
        self.reset_btn = tk.Button(
            button_frame,
            text="Reset",
            command=self.reset_all,
            font=("Arial", 12, "bold"),
            bg="#f44336",
            fg="white",
            width=20,
            height=2
        )
        self.reset_btn.pack(side="left", padx=10)
        
        # Update initial state
        self.update_extract_button_state()
        self.on_horizontal_change()
    
    def on_horizontal_change(self, event=None):
        """Auto-calculate vertical dimension when horizontal changes."""
        if self.auto_calculate.get():
            try:
                horizontal = int(self.horizontal_var.get())
                if horizontal > 0:
                    vertical = round(horizontal / RECOMMENDED_RATIO)
                    # Ensure even number for video encoding compatibility
                    if vertical % 2 != 0:
                        vertical += 1
                    self.vertical_var.set(str(vertical))
                    self.update_aspect_ratio_info()
            except ValueError:
                pass
    
    def toggle_auto_calculate(self):
        """Toggle auto-calculation mode."""
        if self.auto_calculate.get():
            self.vertical_entry.config(state="readonly")
            self.on_horizontal_change()
        else:
            self.vertical_entry.config(state="normal")
            self.vertical_entry.bind('<KeyRelease>', self.update_aspect_ratio_info)
    
    def update_aspect_ratio_info(self, event=None):
        """Update aspect ratio information label."""
        try:
            horizontal = int(self.horizontal_var.get())
            vertical = int(self.vertical_var.get())
            if horizontal > 0 and vertical > 0:
                ratio = horizontal / vertical
                diff = abs(ratio - RECOMMENDED_RATIO)
                if diff < 0.01:
                    self.ratio_label.config(
                        text=f"Aspect ratio: {ratio:.3f} (recommended: {RECOMMENDED_RATIO:.3f}) ✓",
                        fg="green"
                    )
                elif diff < 0.1:
                    self.ratio_label.config(
                        text=f"Aspect ratio: {ratio:.3f} (recommended: {RECOMMENDED_RATIO:.3f}) - Close",
                        fg="orange"
                    )
                else:
                    self.ratio_label.config(
                        text=f"Aspect ratio: {ratio:.3f} (recommended: {RECOMMENDED_RATIO:.3f}) ⚠ Warning",
                        fg="red"
                    )
        except ValueError:
            self.ratio_label.config(text="Invalid dimensions", fg="red")
    
    def select_directory(self):
        """Select directory containing audio files."""
        directory = filedialog.askdirectory(title="Select Directory with Audio Files")
        
        if directory:
            self.working_directory = directory
            self.dir_label.config(text=directory, fg="black")
            
            # Find all audio files in the directory
            self.log_status("Scanning directory for audio files...")
            self.root.update()
            
            try:
                audio_files = find_all_audio_files(directory)
                
                if len(audio_files) > 0:
                    self.audio_files = audio_files
                    file_count = len(self.audio_files)
                    file_text = f"Found {file_count} audio file{'s' if file_count != 1 else ''}"
                    
                    # Show first few filenames
                    if file_count <= 5:
                        file_text += f":\n  {', '.join([os.path.basename(f) for f in self.audio_files])}"
                    else:
                        file_text += f":\n  {', '.join([os.path.basename(f) for f in self.audio_files[:5]])} ... and {file_count - 5} more"
                    
                    self.audio_label.config(text=file_text, fg="green")
                    self.log_status(f"Found {file_count} audio file(s) in directory")
                else:
                    self.audio_files = []
                    self.audio_label.config(text="No audio files found in this directory", fg="red")
                    self.log_status("No audio files found in directory")
                    messagebox.showwarning(
                        "No Audio Files",
                        "No audio files found in the selected directory.\n\n"
                        "Supported formats: WAV, MP3, M4A, FLAC, AAC, OGG"
                    )
                
                self.update_extract_button_state()
            except Exception as e:
                self.audio_files = []
                self.audio_label.config(text=f"Error scanning directory: {str(e)}", fg="red")
                messagebox.showerror("Error", f"Error scanning directory:\n\n{str(e)}")
    
    def update_extract_button_state(self):
        """Update extract button state based on inputs."""
        if len(self.audio_files) > 0 and self.working_directory:
            try:
                horizontal = int(self.horizontal_var.get())
                vertical = int(self.vertical_var.get())
                if horizontal > 0 and vertical > 0:
                    self.extract_btn.config(state="normal")
                    return
            except ValueError:
                pass
        self.extract_btn.config(state="disabled")
    
    def reset_all(self):
        """Reset all inputs."""
        self.audio_files = []
        self.working_directory = None
        self.horizontal_var.set("600")
        self.vertical_var.set("174")
        self.auto_calculate.set(True)
        self.vertical_entry.config(state="readonly")
        
        self.dir_label.config(text="No directory selected", fg="gray")
        self.audio_label.config(text="No audio files found", fg="gray")
        self.progress_var.set("Ready to extract overlays")
        self.progress_bar['value'] = 0
        self.progress_percent_var.set("0%")
        
        self.status_text.config(state="normal")
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state="disabled")
        
        self.extract_btn.config(state="disabled")
        self.on_horizontal_change()
    
    def log_status(self, message):
        """Thread-safe logging to status text."""
        def update():
            self.status_text.config(state="normal")
            self.status_text.insert(tk.END, message + "\n")
            self.status_text.see(tk.END)
            self.status_text.config(state="disabled")
        self.root.after(0, update)
    
    def update_progress(self, value, message="", percent=None):
        """Thread-safe progress bar update."""
        def update():
            self.progress_bar['value'] = value
            if message:
                self.progress_var.set(message)
            percent_value = percent if percent is not None else int(value)
            self.progress_percent_var.set(f"{percent_value}%")
        self.root.after(0, update)
    
    def extract_overlays(self):
        """Start overlay extraction process."""
        if len(self.audio_files) == 0:
            messagebox.showwarning("No Audio Files", "Please select a directory containing audio files.")
            return
        
        if not self.working_directory:
            messagebox.showwarning("No Directory", "Please select a working directory.")
            return
        
        try:
            overlay_width = int(self.horizontal_var.get())
            overlay_height = int(self.vertical_var.get())
            
            if overlay_width <= 0 or overlay_height <= 0:
                raise ValueError("Dimensions must be positive")
        except ValueError:
            messagebox.showerror("Invalid Dimensions", "Please enter valid dimensions.")
            return
        
        # Verify directory exists
        if not os.path.exists(self.working_directory):
            messagebox.showerror("Directory Not Found", "The selected directory no longer exists.")
            return
        
        # Disable button during processing
        self.extract_btn.config(state="disabled")
        self.progress_bar['value'] = 0
        self.progress_var.set("Starting extraction...")
        self.progress_percent_var.set("0%")
        self.status_text.config(state="normal")
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state="disabled")
        self.log_status(f"Starting extraction for {len(self.audio_files)} file(s)...")
        self.log_status(f"Output directory: {self.working_directory}")
        self.log_status(f"Resolution: {overlay_width}x{overlay_height}")
        self.log_status("=" * 60)
        
        # Run in separate thread
        thread = threading.Thread(
            target=self.process_extraction,
            args=(overlay_width, overlay_height)
        )
        thread.daemon = True
        thread.start()
    
    def process_extraction(self, overlay_width, overlay_height):
        """Process overlay extraction in background thread."""
        try:
            self.log_status("Starting overlay extraction process...")
            self.update_progress(0, "Initializing...")
            
            # Get audio files info
            self.log_status(f"Reading {len(self.audio_files)} audio file(s)...")
            audio_files_info = get_audio_files_info(self.audio_files)
            total_files = len(audio_files_info)
            
            self.log_status(f"Extracting {total_files} overlay video(s) at {overlay_width}x{overlay_height}...")
            
            # Close any existing browser before processing
            if use_playwright:
                try:
                    close_browser()
                except:
                    pass
            
            # Process each audio file
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
                
                # Create output filename using same base name as audio file
                audio_basename = os.path.basename(track_path)
                audio_name_without_ext = os.path.splitext(audio_basename)[0]
                
                # Clean the name for filename
                safe_name = "".join(c for c in audio_name_without_ext if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_name = safe_name.replace(' ', '_')
                
                if not safe_name:
                    safe_name = f"track_{i+1}"
                
                # Create output filename in same directory with _overlay suffix
                output_filename = f"{safe_name}_overlay.mov"
                output_path = os.path.join(self.working_directory, output_filename)
                
                # Handle duplicates
                counter = 1
                while os.path.exists(output_path):
                    output_path = os.path.join(self.working_directory, f"{safe_name}_overlay_{counter}.mov")
                    counter += 1
                    output_filename = os.path.basename(output_path)
                
                output_filename = os.path.basename(output_path)
                
                # Update progress - update UI immediately
                file_progress = (i / total_files) * 100
                self.update_progress(
                    file_progress,
                    f"Processing {i+1}/{total_files}: {os.path.basename(track_path)}...",
                    int(file_progress)
                )
                self.log_status(f"\n[{i+1}/{total_files}] Processing: {os.path.basename(track_path)}")
                self.log_status(f"  Track: {track_name}")
                self.log_status(f"  Duration: {track_duration:.2f} seconds")
                self.log_status(f"  Output: {output_filename}")
                self.root.update()  # Force UI update
                
                # Initialize browser if needed
                if use_playwright:
                    try:
                        from player_overlay_playwright import get_browser
                        get_browser()
                    except:
                        pass
                
                # Define progress callback for this overlay
                def overlay_progress_callback(current_time, total_duration, message=None):
                    """Update progress for current overlay export."""
                    if total_duration > 0:
                        overlay_progress = (current_time / total_duration) * 100
                        file_size_percentage = 100 / total_files
                        overall_progress = file_progress + (overlay_progress * file_size_percentage / 100)
                        
                        status_msg = message or f"Encoding {i+1}/{total_files}: {current_time:.1f}s / {total_duration:.1f}s"
                        self.update_progress(
                            overall_progress,
                            status_msg,
                            int(overall_progress)
                        )
                        
                        # Log detailed progress every 5 seconds
                        if int(current_time) % 5 == 0 and int(current_time) > 0:
                            self.log_status(f"    Progress: {current_time:.1f}s / {total_duration:.1f}s ({overlay_progress:.1f}%)")
                            self.root.update()  # Force UI update
                
                # Export overlay video
                try:
                    # Generate frames with progress callback
                    self.log_status(f"  Generating overlay frames...")
                    self.root.update()
                    
                    # Export overlay video (includes frame generation and encoding)
                    export_overlay_video(
                        audio_info,
                        output_path,
                        fps=30,
                        overlay_width=overlay_width,
                        overlay_height=overlay_height,
                        progress_callback=overlay_progress_callback
                    )
                    
                    self.log_status(f"  ✓ Successfully exported: {output_filename}")
                    self.root.update()  # Force UI update after each file
                except Exception as e:
                    self.log_status(f"  ✗ Error exporting: {str(e)}")
                    self.root.update()  # Force UI update even on error
                    continue  # Continue with next file
            
            # Close browser after processing
            if use_playwright:
                try:
                    close_browser()
                except:
                    pass
            
            # Count successful exports
            successful_files = sum(1 for f in os.listdir(self.working_directory) if f.endswith('_overlay.mov') and os.path.isfile(os.path.join(self.working_directory, f)))
            
            # Final progress
            self.update_progress(100, "All overlays extracted successfully!")
            self.log_status(f"\n{'=' * 60}")
            self.log_status(f"✓ SUCCESS! Extracted {successful_files} overlay video(s)")
            self.log_status(f"Location: {self.working_directory}")
            self.log_status(f"Format: MOV with ProRes 4444 (alpha channel)")
            self.log_status(f"Resolution: {overlay_width}x{overlay_height}")
            self.root.update()  # Final UI update
            
            def on_success():
                self.progress_var.set("Extraction complete!")
                self.progress_percent_var.set("100%")
                messagebox.showinfo(
                    "Success",
                    f"Successfully extracted {successful_files} overlay video(s)!\n\n"
                    f"Location:\n{self.working_directory}\n\n"
                    f"Resolution: {overlay_width}x{overlay_height}\n"
                    f"Format: MOV with ProRes 4444 (alpha channel)"
                )
                self.extract_btn.config(state="normal")
            self.root.after(0, on_success)
            
        except Exception as e:
            error_message = str(e)
            
            # Close browser on error
            if use_playwright:
                try:
                    close_browser()
                except:
                    pass
            
            def on_error():
                self.progress_var.set("Error occurred")
                self.progress_percent_var.set("Error")
                self.log_status(f"\n✗ ERROR: {error_message}")
                messagebox.showerror(
                    "Error",
                    f"An error occurred while extracting overlays:\n\n{error_message}"
                )
                self.extract_btn.config(state="normal")
            self.root.after(0, on_error)


def main():
    """Main function for GUI application."""
    root = tk.Tk()
    app = OverlayExtractorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

