"""
Audio processor module for processing audio files with fade transitions.
Supports multiple audio formats including WAV, MP3, M4A, FLAC, AAC, and OGG.
"""

from pydub import AudioSegment
from pydub.utils import make_chunks
import os
import random
import glob


def process_audio_files(wav_files, fade_duration=2000):
    """
    Load audio files, add fade-in and fade-out transitions, and concatenate them.
    
    Args:
        wav_files: List of paths to audio files (at least 1 file required)
        fade_duration: Duration of fade in/out in milliseconds (default: 2000ms = 2 seconds)
    
    Returns:
        Concatenated AudioSegment with all fades applied
    """
    if len(wav_files) == 0:
        raise ValueError("At least one audio file is required")
    
    processed_segments = []
    
    for i, audio_file in enumerate(wav_files):
        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"Audio file not found: {audio_file}")
        
        # Load audio file (supports WAV, MP3, M4A, FLAC, etc.)
        audio = AudioSegment.from_file(audio_file)
        
        # Apply fade-in (except for first file to avoid abrupt start)
        if i == 0:
            # Short fade-in for first file
            audio = audio.fade_in(min(fade_duration, len(audio)))
        else:
            # Full fade-in for subsequent files
            audio = audio.fade_in(min(fade_duration, len(audio)))
        
        # Apply fade-out (except for last file to avoid abrupt end)
        if i == len(wav_files) - 1:
            # Short fade-out for last file
            audio = audio.fade_out(min(fade_duration, len(audio)))
        else:
            # Full fade-out for all files except last
            audio = audio.fade_out(min(fade_duration, len(audio)))
        
        processed_segments.append(audio)
    
    # Concatenate all segments
    final_audio = sum(processed_segments)
    
    return final_audio


def export_audio_to_wav(audio_segment, output_path):
    """
    Export AudioSegment to high-quality WAV file.
    
    Args:
        audio_segment: AudioSegment object to export
        output_path: Path where the WAV file will be saved
    """
    audio_segment.export(output_path, format="wav", parameters=["-acodec", "pcm_s24le"])
    
    return output_path


def get_audio_duration(wav_files):
    """
    Calculate total duration of all audio files combined.
    
    Args:
        wav_files: List of paths to audio files
    
    Returns:
        Total duration in seconds
    """
    total_duration = 0
    for audio_file in wav_files:
        audio = AudioSegment.from_file(audio_file)
        total_duration += len(audio) / 1000.0  # Convert milliseconds to seconds
    
    return total_duration


def get_audio_files_info(wav_files):
    """
    Get information about each audio file including duration.
    
    Args:
        wav_files: List of paths to audio files
    
    Returns:
        List of dictionaries with 'path' and 'duration' keys
    """
    files_info = []
    for audio_file in wav_files:
        audio = AudioSegment.from_file(audio_file)
        duration = len(audio) / 1000.0  # Convert milliseconds to seconds
        files_info.append({
            'path': audio_file,
            'duration': duration
        })
    return files_info


def find_all_audio_files(directory, extensions=None):
    """
    Find all audio files in a directory and its subdirectories.
    
    Args:
        directory: Root directory to search
        extensions: List of file extensions to search for (default: wav, mp3, m4a, flac)
    
    Returns:
        List of file paths
    """
    if extensions is None:
        extensions = ['wav', 'mp3', 'm4a', 'flac', 'aac', 'ogg']
    
    audio_files = []
    
    # Walk through directory and subdirectories
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_ext = file.lower().split('.')[-1]
            if file_ext in extensions:
                full_path = os.path.join(root, file)
                audio_files.append(full_path)
    
    return audio_files


def select_random_audio_files(directory, target_duration_minutes, extensions=None, max_attempts=1000):
    """
    Select random audio files from a directory and subdirectories to reach target duration.
    
    Args:
        directory: Root directory to search for audio files
        target_duration_minutes: Target duration in minutes
        extensions: List of file extensions to search for
        max_attempts: Maximum attempts to find a combination (to prevent infinite loops)
    
    Returns:
        List of selected audio file paths (no duplicates)
    
    Raises:
        ValueError: If target duration cannot be reached with available files
    """
    # Find all audio files
    all_audio_files = find_all_audio_files(directory, extensions)
    
    if len(all_audio_files) == 0:
        raise ValueError(f"No audio files found in directory: {directory}")
    
    # Get info for all files
    all_files_info = []
    for audio_file in all_audio_files:
        try:
            audio = AudioSegment.from_file(audio_file)
            duration = len(audio) / 1000.0  # Convert to seconds
            all_files_info.append({
                'path': audio_file,
                'duration': duration
            })
        except Exception as e:
            print(f"Warning: Could not read {audio_file}: {e}")
            continue
    
    if len(all_files_info) == 0:
        raise ValueError("No valid audio files found")
    
    # Convert target duration to seconds
    target_duration_seconds = target_duration_minutes * 60
    # Use fixed 20-minute window for flexibility (e.g., 60 minutes -> 50-70 minutes range)
    tolerance_seconds = 10 * 60  # 10 minutes on either side = 20-minute window
    min_duration = max(0, target_duration_seconds - tolerance_seconds)  # Ensure non-negative
    max_duration = target_duration_seconds + tolerance_seconds
    
    # Try random combinations
    for attempt in range(max_attempts):
        selected_files = []
        total_duration = 0
        
        # Shuffle the list for randomness
        files_copy = all_files_info.copy()
        random.shuffle(files_copy)
        
        # Add files until we reach or exceed target
        for file_info in files_copy:
            if total_duration + file_info['duration'] <= max_duration:
                selected_files.append(file_info['path'])
                total_duration += file_info['duration']
                
                # Check if we've reached the minimum duration
                if total_duration >= min_duration:
                    return selected_files
        
        # If this attempt didn't work, try again
    
    # If we couldn't find a combination within tolerance
    # Return closest combination we found
    best_combination = []
    best_duration = 0
    
    files_copy = all_files_info.copy()
    random.shuffle(files_copy)
    
    for file_info in files_copy:
        if best_duration + file_info['duration'] <= max_duration:
            best_combination.append(file_info['path'])
            best_duration += file_info['duration']
    
    if len(best_combination) == 0:
        raise ValueError(f"Could not find any combination of files to reach target duration")
    
    # Return the best we could do (closest to target)
    return best_combination

