"""
4K Video Creator GUI Application
Creates high-quality 4K videos from an image and multiple WAV music files.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
from image_processor import resize_image_to_4k
from audio_processor import (
    process_audio_files, export_audio_to_wav, get_audio_duration, get_audio_files_info,
    select_random_audio_files, find_all_audio_files
)
from video_processor import create_4k_video, check_ffmpeg_available, estimate_video_file_size, format_file_size
from PIL import Image, ImageTk


class VideoCreatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("4K Video Creator for YouTube")
        self.root.geometry("900x1000")
        self.root.resizable(True, True)
        
        # Variables
        self.image_path = None
        self.audio_files = []
        self.output_path = None
        self.temp_files = []  # Track temp files for cleanup
        self.audio_directory = None
        self.target_duration_minutes = tk.StringVar(value="60")
        
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
    
    def create_widgets(self):
        # Title
        title_label = tk.Label(
            self.root,
            text="4K Video Creator",
            font=("Arial", 20, "bold")
        )
        title_label.pack(pady=10)
        
        # Quality info
        quality_label = tk.Label(
            self.root,
            text="Output: 4K (3840x2160) - YouTube Ready",
            font=("Arial", 10),
            fg="green"
        )
        quality_label.pack(pady=5)
        
        # Image selection
        image_frame = tk.Frame(self.root)
        image_frame.pack(pady=10, padx=20, fill="x")
        
        tk.Label(image_frame, text="High Quality Image:", font=("Arial", 11)).pack(anchor="w")
        
        image_btn_frame = tk.Frame(image_frame)
        image_btn_frame.pack(fill="x", pady=5)
        
        self.image_label = tk.Label(
            image_btn_frame,
            text="No image selected",
            fg="gray",
            anchor="w"
        )
        self.image_label.pack(side="left", fill="x", expand=True)
        
        tk.Button(
            image_btn_frame,
            text="Select Image",
            command=self.select_image,
            width=15
        ).pack(side="right")
        
        # Audio files selection
        audio_frame = tk.Frame(self.root)
        audio_frame.pack(pady=10, padx=20, fill="x")
        
        tk.Label(audio_frame, text="WAV Music Files:", font=("Arial", 11)).pack(anchor="w")
        
        audio_btn_frame = tk.Frame(audio_frame)
        audio_btn_frame.pack(fill="x", pady=5)
        
        self.audio_label = tk.Label(
            audio_btn_frame,
            text="0 files selected",
            fg="gray",
            anchor="w"
        )
        self.audio_label.pack(side="left", fill="x", expand=True)
        
        tk.Button(
            audio_btn_frame,
            text="Select WAV Files",
            command=self.select_audio_files,
            width=15
        ).pack(side="right")
        
        # Random audio selection from directory
        random_audio_frame = tk.Frame(self.root)
        random_audio_frame.pack(pady=10, padx=20, fill="x")
        
        tk.Label(random_audio_frame, text="Random Audio Selection:", font=("Arial", 11)).pack(anchor="w")
        
        random_btn_frame = tk.Frame(random_audio_frame)
        random_btn_frame.pack(fill="x", pady=5)
        
        self.random_audio_label = tk.Label(
            random_btn_frame,
            text="No directory selected",
            fg="gray",
            anchor="w"
        )
        self.random_audio_label.pack(side="left", fill="x", expand=True)
        
        tk.Button(
            random_btn_frame,
            text="Select Directory",
            command=self.select_audio_directory,
            width=15
        ).pack(side="right")
        
        # Target duration input
        duration_frame = tk.Frame(self.root)
        duration_frame.pack(pady=10, padx=20, fill="x")
        
        tk.Label(duration_frame, text="Target Duration (minutes):", font=("Arial", 11)).pack(anchor="w")
        
        duration_input_frame = tk.Frame(duration_frame)
        duration_input_frame.pack(fill="x", pady=5)
        
        self.duration_entry = tk.Entry(
            duration_input_frame,
            textvariable=self.target_duration_minutes,
            font=("Arial", 11),
            width=15
        )
        self.duration_entry.pack(side="left", padx=(0, 10))
        
        tk.Button(
            duration_input_frame,
            text="Generate Random Selection",
            command=self.generate_random_selection,
            width=20
        ).pack(side="left", padx=5)
        
        # Output path selection
        output_frame = tk.Frame(self.root)
        output_frame.pack(pady=10, padx=20, fill="x")
        
        tk.Label(output_frame, text="Output Video Location:", font=("Arial", 11)).pack(anchor="w")
        
        output_btn_frame = tk.Frame(output_frame)
        output_btn_frame.pack(fill="x", pady=5)
        
        self.output_label = tk.Label(
            output_btn_frame,
            text="No output path selected",
            fg="gray",
            anchor="w"
        )
        self.output_label.pack(side="left", fill="x", expand=True)
        
        tk.Button(
            output_btn_frame,
            text="Select Location",
            command=self.select_output_path,
            width=15
        ).pack(side="right")
        
        # Progress bar
        progress_frame = tk.Frame(self.root)
        progress_frame.pack(pady=20, padx=20, fill="x")
        
        self.progress_var = tk.StringVar(value="Ready to create video")
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
            font=("Arial", 16, "bold"),
            fg="white",
            bg="black"
        )
        self.progress_percent_label.pack()
        
        # Estimated file size display
        size_info_frame = tk.Frame(self.root)
        size_info_frame.pack(pady=10, padx=20, fill="x")
        
        tk.Label(
            size_info_frame,
            text="Estimated Video File Size:",
            font=("Arial", 10)
        ).pack(side="left")
        
        self.estimated_size_var = tk.StringVar(value="N/A (select audio files)")
        self.estimated_size_label = tk.Label(
            size_info_frame,
            textvariable=self.estimated_size_var,
            font=("Arial", 10, "bold"),
            fg="green"
        )
        self.estimated_size_label.pack(side="left", padx=10)
        
        # Music Player Preview
        preview_frame = tk.Frame(self.root)
        preview_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        tk.Label(
            preview_frame,
            text="Music Player Preview:",
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(0, 5))
        
        # Preview canvas with scrollable area
        preview_canvas_frame = tk.Frame(preview_frame, bg="lightgrey", relief="sunken", bd=2)
        preview_canvas_frame.pack(fill="both", expand=True)
        
        self.preview_canvas = tk.Canvas(
            preview_canvas_frame,
            bg="black",
            width=400,
            height=225,
            highlightthickness=0
        )
        self.preview_canvas.pack(padx=5, pady=5, fill="both", expand=True)
        
        self.preview_image = None
        self.preview_photo = None
        
        # Preview status label
        self.preview_status_var = tk.StringVar(value="No preview available")
        self.preview_status_label = tk.Label(
            preview_frame,
            textvariable=self.preview_status_var,
            font=("Arial", 9),
            fg="gray"
        )
        self.preview_status_label.pack()
        
        # Button frame for Create and Reset buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=20)
        
        # Create button
        self.create_btn = tk.Button(
            button_frame,
            text="Create 4K Video",
            command=self.create_video,
            font=("Arial", 12, "bold"),
            bg="#4CAF50",
            fg="white",
            width=20,
            height=2,
            state="disabled"
        )
        self.create_btn.pack(side="left", padx=10)
        
        # Reset button
        self.reset_btn = tk.Button(
            button_frame,
            text="Reset All",
            command=self.reset_all,
            font=("Arial", 12, "bold"),
            bg="#f44336",
            fg="white",
            width=20,
            height=2
        )
        self.reset_btn.pack(side="left", padx=10)
        
        # Status text
        self.status_text = tk.Text(
            self.root,
            height=8,
            width=80,
            wrap=tk.WORD,
            state="disabled"
        )
        self.status_text.pack(pady=10, padx=20, fill="both", expand=True)
    
    def select_image(self):
        file_path = filedialog.askopenfilename(
            title="Select High Quality Image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.image_path = file_path
            filename = os.path.basename(file_path)
            self.image_label.config(text=filename, fg="black")
            self.check_ready()
    
    def select_audio_files(self):
        file_paths = filedialog.askopenfilenames(
            title="Select WAV Music Files",
            filetypes=[
                ("WAV files", "*.wav"),
                ("All files", "*.*")
            ]
        )
        
        if file_paths:
            wav_files = [f for f in file_paths if f.lower().endswith('.wav')]
            
            if len(wav_files) == 0:
                messagebox.showwarning(
                    "No WAV Files Selected",
                    "Please select at least one WAV audio file."
                )
                return
            
            self.audio_files = wav_files
            file_count = len(wav_files)
            file_text = f"{file_count} WAV file{'s' if file_count != 1 else ''} selected"
            self.audio_label.config(
                text=file_text,
                fg="black"
            )
            self.update_estimated_size()
            self.update_preview()
            self.check_ready()
    
    def select_output_path(self):
        file_path = filedialog.asksaveasfilename(
            title="Save Video As",
            defaultextension=".mp4",
            filetypes=[
                ("MP4 files", "*.mp4"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.output_path = file_path
            filename = os.path.basename(file_path)
            self.output_label.config(text=filename, fg="black")
            self.check_ready()
    
    def reset_all(self):
        """Reset all input selections and clear the form."""
        # Reset variables
        self.image_path = None
        self.audio_files = []
        self.output_path = None
        self.audio_directory = None
        self.target_duration_minutes.set("60")
        self.temp_files = []
        
        # Reset labels
        self.image_label.config(text="No image selected", fg="gray")
        self.audio_label.config(text="0 files selected", fg="gray")
        self.random_audio_label.config(text="No directory selected", fg="gray")
        self.output_label.config(text="No output path selected", fg="gray")
        
        # Reset progress
        self.progress_var.set("Ready to create video")
        self.progress_bar['value'] = 0
        self.progress_percent_var.set("0%")
        self.estimated_size_var.set("N/A (select audio files)")
        
        # Clear status text
        self.status_text.config(state="normal")
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state="disabled")
        
        # Clear preview
        self.preview_canvas.delete("all")
        self.preview_status_var.set("No preview available")
        
        # Disable create button
        self.create_btn.config(state="disabled")
        
        # Show confirmation message
        messagebox.showinfo("Reset Complete", "All selections have been cleared.")
    
    def select_audio_directory(self):
        """Select a directory to search for audio files."""
        directory = filedialog.askdirectory(title="Select Audio Directory")
        
        if directory:
            self.audio_directory = directory
            folder_name = os.path.basename(directory)
            self.random_audio_label.config(text=folder_name, fg="black")
    
    def generate_random_selection(self):
        """Generate random audio file selection based on target duration."""
        if not self.audio_directory:
            messagebox.showwarning(
                "No Directory Selected",
                "Please select an audio directory first."
            )
            return
        
        try:
            # Get target duration from entry
            target_duration = float(self.target_duration_minutes.get())
            
            if target_duration <= 0:
                messagebox.showerror(
                    "Invalid Duration",
                    "Target duration must be greater than 0."
                )
                return
            
            # Show progress dialog
            progress_dialog = tk.Toplevel(self.root)
            progress_dialog.title("Scanning Audio Files")
            progress_dialog.geometry("400x150")
            progress_dialog.transient(self.root)
            progress_dialog.grab_set()
            
            tk.Label(
                progress_dialog,
                text=f"Scanning audio files in:\n{self.audio_directory}",
                wraplength=350
            ).pack(pady=10)
            
            progress_bar = ttk.Progressbar(progress_dialog, mode='indeterminate')
            progress_bar.pack(pady=10, padx=20, fill="x")
            progress_bar.start()
            
            status_label = tk.Label(
                progress_dialog,
                text="Please wait...",
                fg="blue"
            )
            status_label.pack(pady=5)
            
            progress_dialog.update()
            
            # Run selection in a thread to avoid freezing
            def run_selection():
                try:
                    selected_files = select_random_audio_files(
                        self.audio_directory,
                        target_duration
                    )
                    
                    # Calculate actual duration
                    actual_duration = get_audio_duration(selected_files)
                    
                    # Close progress dialog
                    progress_dialog.destroy()
                    
                    # Update UI
                    self.audio_files = selected_files
                    file_count = len(selected_files)
                    minutes = int(actual_duration // 60)
                    seconds = int(actual_duration % 60)
                    
                    self.audio_label.config(
                        text=f"{file_count} file{'s' if file_count != 1 else ''} selected ({minutes}m {seconds}s)",
                        fg="black"
                    )
                    
                    self.update_estimated_size()
                    self.update_preview()
                    self.check_ready()
                    
                    messagebox.showinfo(
                        "Random Selection Complete",
                        f"Selected {file_count} files\n"
                        f"Total duration: {minutes}m {seconds}s"
                    )
                    
                except Exception as e:
                    progress_dialog.destroy()
                    messagebox.showerror(
                        "Selection Error",
                        f"Error selecting random files:\n\n{str(e)}"
                    )
            
            thread = threading.Thread(target=run_selection)
            thread.daemon = True
            thread.start()
            
        except ValueError:
            messagebox.showerror(
                "Invalid Duration",
                "Please enter a valid number for target duration."
            )
    
    def check_ready(self):
        if self.image_path and len(self.audio_files) > 0 and self.output_path:
            self.create_btn.config(state="normal")
        else:
            self.create_btn.config(state="disabled")
    
    def update_estimated_size(self):
        """Calculate and update estimated video file size."""
        if len(self.audio_files) == 0:
            self.estimated_size_var.set("N/A (select audio files)")
            return
        
        try:
            # Calculate total audio duration
            total_duration = get_audio_duration(self.audio_files)
            
            # Estimate file size (60 Mbps video + 384 kbps audio)
            estimated_size_mb = estimate_video_file_size(
                total_duration,
                video_bitrate_mbps=60,
                audio_bitrate_kbps=384
            )
            
            # Format and display
            formatted_size = format_file_size(estimated_size_mb)
            
            # Also show duration
            minutes = int(total_duration // 60)
            seconds = int(total_duration % 60)
            duration_text = f"{minutes}m {seconds}s"
            
            self.estimated_size_var.set(f"~{formatted_size} ({duration_text})")
            
        except Exception as e:
            self.estimated_size_var.set(f"Error calculating: {str(e)}")
    
    def update_preview(self):
        """Update the music player preview display."""
        if len(self.audio_files) == 0:
            self.preview_status_var.set("Select audio files to see preview")
            self.preview_canvas.delete("all")
            return
        
        try:
            self.preview_status_var.set("Generating preview...")
            self.root.update()
            
            # Get first audio file info for preview
            audio_files_info = get_audio_files_info(self.audio_files)
            first_file = audio_files_info[0]
            
            # Extract song title and create frame (try Playwright first, fallback to PIL)
            try:
                from player_overlay_playwright import extract_song_title, create_player_overlay_frame
            except ImportError:
                try:
                    from player_overlay import extract_song_title, create_player_overlay_frame
                except ImportError:
                    self.preview_status_var.set("Preview not available (missing overlay modules)")
                    self.preview_canvas.delete("all")
                    return
            
            song_title = extract_song_title(first_file['path'])
            track_duration = first_file['duration']
            
            # Create preview frame (show at 25% progress as example)
            preview_time = track_duration * 0.25
            preview_frame = create_player_overlay_frame(
                song_title,
                preview_time,
                track_duration
            )
            
            # Resize preview for display (fit to canvas while maintaining aspect ratio)
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            
            if canvas_width <= 1 or canvas_height <= 1:
                # Canvas not yet rendered, use default size
                canvas_width = 400
                canvas_height = 225
            
            # Calculate scaling to fit canvas
            frame_ratio = preview_frame.width / preview_frame.height
            canvas_ratio = canvas_width / canvas_height
            
            if frame_ratio > canvas_ratio:
                # Frame is wider - fit to width
                display_width = int(canvas_width * 0.9)
                display_height = int(display_width / frame_ratio)
            else:
                # Frame is taller - fit to height
                display_height = int(canvas_height * 0.9)
                display_width = int(display_height * frame_ratio)
            
            # Resize frame for preview
            display_frame = preview_frame.resize((display_width, display_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage for tkinter
            self.preview_photo = ImageTk.PhotoImage(display_frame)
            
            # Clear canvas and display preview
            self.preview_canvas.delete("all")
            
            # Center the image
            x = (canvas_width - display_width) // 2
            y = (canvas_height - display_height) // 2
            
            self.preview_canvas.create_image(x, y, anchor="nw", image=self.preview_photo)
            
            # Update status
            minutes_preview = int(preview_time // 60)
            seconds_preview = int(preview_time % 60)
            minutes_total = int(track_duration // 60)
            seconds_total = int(track_duration % 60)
            time_text = f"{minutes_preview}:{seconds_preview:02d} / {minutes_total}:{seconds_total:02d}"
            self.preview_status_var.set(f"Preview: {song_title} - {time_text} (Showing first track at 25%)")
            
        except Exception as e:
            error_msg = str(e)
            self.preview_status_var.set(f"Preview error: {error_msg}")
            self.preview_canvas.delete("all")
    
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
    
    def create_video(self):
        # Disable button during processing
        self.create_btn.config(state="disabled")
        self.progress_bar['value'] = 0
        self.progress_var.set("Starting...")
        self.progress_percent_var.set("0%")
        self.status_text.config(state="normal")
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state="disabled")
        self.temp_files = []  # Reset temp files list
        
        # Run in separate thread to avoid freezing GUI
        thread = threading.Thread(target=self.process_video)
        thread.daemon = True
        thread.start()
    
    def process_video(self):
        try:
            self.log_status("Starting video creation process...")
            self.update_progress(0, "Initializing...")
            
            # Step 1: Resize image to 4K (0-25%)
            self.log_status("Step 1/4: Resizing image to 4K resolution (3840x2160)...")
            self.update_progress(5, "Resizing image to 4K...")
            output_dir = os.path.dirname(self.output_path)
            if not output_dir:
                output_dir = os.getcwd()
            temp_image_path = os.path.join(output_dir, "temp_4k_image.jpg")
            resize_image_to_4k(self.image_path, temp_image_path)
            self.temp_files.append(temp_image_path)
            self.update_progress(25, "Image resized to 4K")
            self.log_status(f"✓ Image resized to 4K")
            
            # Step 2: Process and concatenate audio files (25-50%)
            self.log_status("Step 2/4: Processing audio files with fade transitions...")
            self.update_progress(30, "Processing audio files...")
            audio_segment = process_audio_files(self.audio_files, fade_duration=2000)
            self.update_progress(45, f"Processed {len(self.audio_files)} audio files")
            self.log_status(f"✓ Processed {len(self.audio_files)} audio files with fades")
            
            # Step 3: Export concatenated audio (50-75%)
            self.log_status("Step 3/4: Exporting concatenated audio...")
            self.update_progress(50, "Exporting audio...")
            temp_audio_path = os.path.join(output_dir, "temp_audio.wav")
            export_audio_to_wav(audio_segment, temp_audio_path)
            self.temp_files.append(temp_audio_path)
            self.update_progress(75, "Audio exported")
            self.log_status(f"✓ Audio exported")
            
            # Step 4: Create 4K video with overlay (75-100%)
            self.log_status("Step 4/4: Creating 4K video with music player overlay...")
            self.update_progress(75, "Generating overlay frames...")
            
            # Get audio files info for overlay
            audio_files_info = get_audio_files_info(self.audio_files)
            
            # Close any existing Playwright browser from main thread before worker thread
            try:
                from player_overlay_playwright import close_browser
                close_browser()
            except:
                pass
            
            # Generate overlay frames (this may take time)
            # Initialize Playwright in worker thread to avoid threading issues
            try:
                from player_overlay_playwright import generate_overlay_frames, close_browser
                self.log_status("Using Playwright for high-quality rendering...")
                total_duration = get_audio_duration(self.audio_files)
                overlay_frames = generate_overlay_frames(audio_files_info, total_duration, fps=30)
                # Close browser after frame generation in worker thread
                close_browser()
            except ImportError:
                from player_overlay import generate_overlay_frames
                self.log_status("Using PIL for rendering (Playwright not available)...")
                total_duration = get_audio_duration(self.audio_files)
                overlay_frames = generate_overlay_frames(audio_files_info, total_duration, fps=30)
            
            self.log_status(f"✓ Generated {len(overlay_frames)} overlay frames")
            self.update_progress(80, "Saving overlay frames...")
            
            # Save overlay frames as PNG images (in worker thread)
            from video_processor import create_overlay_video
            overlay_temp_dir, _ = create_overlay_video(overlay_frames, total_duration, fps=30)
            
            # Cleanup browser after overlay frames saved (in worker thread)
            try:
                close_browser()
            except:
                pass
            
            self.log_status(f"✓ Overlay frames saved")
            self.update_progress(85, "Creating 4K video with FFmpeg...")
            
            # Create final video with overlay
            create_4k_video(
                temp_image_path, 
                temp_audio_path, 
                self.output_path,
                progress_callback=self.update_ffmpeg_progress,
                overlay_video_path=None,  # Not used anymore
                overlay_temp_dir=overlay_temp_dir
            )
            
            # Cleanup overlay temp directory
            if overlay_temp_dir and os.path.exists(overlay_temp_dir):
                try:
                    import shutil
                    shutil.rmtree(overlay_temp_dir)
                except Exception as e:
                    self.log_status(f"Warning: Could not delete overlay temp dir: {e}")
            self.update_progress(100, "Video created successfully!")
            self.log_status(f"✓ Video created successfully!")
            
            # Cleanup temp files
            self.log_status("Cleaning up temporary files...")
            for temp_file in self.temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception as e:
                    self.log_status(f"Warning: Could not delete temp file: {e}")
            
            def on_success():
                self.progress_var.set("Video created successfully!")
                self.progress_percent_var.set("100%")
                self.log_status(f"\n✓ SUCCESS! Video saved to: {self.output_path}")
                messagebox.showinfo(
                    "Success",
                    f"4K video created successfully!\n\nSaved to:\n{self.output_path}"
                )
                self.create_btn.config(state="normal")
            self.root.after(0, on_success)
            
        except Exception as e:
            error_message = str(e)  # Capture the error message in the outer scope
            def on_error():
                self.progress_var.set("Error occurred")
                self.progress_percent_var.set("Error")
                self.log_status(f"\n✗ ERROR: {error_message}")
                messagebox.showerror(
                    "Error",
                    f"An error occurred while creating the video:\n\n{error_message}"
                )
                # Cleanup temp files on error
                for temp_file in self.temp_files:
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    except:
                        pass
                self.create_btn.config(state="normal")
            self.root.after(0, on_error)
    
    def update_ffmpeg_progress(self, current_time, total_duration):
        """Update progress based on FFmpeg encoding progress."""
        if total_duration > 0:
            # Video encoding is from 75% to 100% (or 80% after overlay generation)
            # So we map 0-100% of encoding to 80-100% of total progress
            encoding_progress = (current_time / total_duration) * 100
            total_progress = 80 + (encoding_progress * 0.20)  # 80% + (encoding * 20%)
            
            self.update_progress(
                total_progress, 
                f"Encoding video... {current_time:.1f}s / {total_duration:.1f}s",
                int(total_progress)
            )


def main():
    root = tk.Tk()
    app = VideoCreatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

