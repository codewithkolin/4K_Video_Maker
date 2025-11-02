"""
Image processor module for resizing images to 4K resolution (3840x2160)
with high-quality resampling using LANCZOS algorithm.
"""

from PIL import Image
import os


def resize_image_to_4k(image_path, output_path=None):
    """
    Resize an image to 4K resolution (3840x2160) using high-quality resampling.
    
    Args:
        image_path: Path to the input image file
        output_path: Path to save the resized image (optional, creates temp if None)
    
    Returns:
        Path to the resized image file
    """
    # Load the image
    img = Image.open(image_path)
    
    # Target 4K resolution
    target_width = 3840
    target_height = 2160
    target_size = (target_width, target_height)
    
    # Calculate aspect ratios
    img_aspect = img.width / img.height
    target_aspect = target_width / target_height
    
    # Resize strategy: maintain aspect ratio and fit within 4K bounds
    # Using LANCZOS resampling for highest quality
    if img_aspect > target_aspect:
        # Image is wider - fit to width
        new_height = int(target_width / img_aspect)
        resized = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
    else:
        # Image is taller - fit to height
        new_width = int(target_height * img_aspect)
        resized = img.resize((new_width, target_height), Image.Resampling.LANCZOS)
    
    # Create a 4K canvas with black background
    canvas = Image.new('RGB', target_size, (0, 0, 0))
    
    # Calculate position to center the image
    x_offset = (target_width - resized.width) // 2
    y_offset = (target_height - resized.height) // 2
    
    # Paste the resized image onto the canvas
    canvas.paste(resized, (x_offset, y_offset))
    
    # Save the result
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        output_path = f"{base_name}_4k.jpg"
    
    # Save as high-quality JPEG for FFmpeg
    canvas.save(output_path, 'JPEG', quality=100, optimize=False)
    
    return output_path

