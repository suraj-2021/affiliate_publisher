from PIL import Image, ImageOps
import os
import hashlib
from django.core.files.base import ContentFile
from io import BytesIO

class ImageProcessor:
    """Utility class for image processing"""
    
    @staticmethod
    def optimize_image(image_file, max_width=1920, quality=85):
        """Optimize image for web"""
        img = Image.open(image_file)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                rgb_img.paste(img, mask=img.split()[3])
            else:
                rgb_img.paste(img)
            img = rgb_img
        
        # Auto-orient based on EXIF
        img = ImageOps.exif_transpose(img)
        
        # Resize if needed
        if img.width > max_width:
            ratio = max_width / img.width
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Save optimized
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        
        return ContentFile(output.read())
    
    @staticmethod
    def generate_image_hash(image_file):
        """Generate hash for duplicate detection"""
        hasher = hashlib.md5()
        for chunk in image_file.chunks():
            hasher.update(chunk)
        return hasher.hexdigest()
    
    @staticmethod
    def create_thumbnails(image_file, sizes=None):
        """Create multiple thumbnail sizes"""
        if sizes is None:
            sizes = {
                'small': (300, 300),
                'medium': (768, 768),
                'large': (1920, 1920)
            }
        
        thumbnails = {}
        img = Image.open(image_file)
        
        for size_name, dimensions in sizes.items():
            thumb = img.copy()
            thumb.thumbnail(dimensions, Image.Resampling.LANCZOS)
            
            output = BytesIO()
            thumb.save(output, format='JPEG', quality=85)
            output.seek(0)
            
            thumbnails[size_name] = ContentFile(output.read())
        
        return thumbnails