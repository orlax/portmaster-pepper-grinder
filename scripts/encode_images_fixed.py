#!/usr/bin/env python3
"""
Improved Chowdren image encoder with proper size handling
Fixes uint16 overflow and ensures all header fields are updated
"""

import struct
import zlib
import sys
from pathlib import Path
from PIL import Image

def analyze_original_header(header_bytes):
    """Analyze and print all fields in original header"""
    if len(header_bytes) < 50:
        return None
    
    info = {
        'width': struct.unpack('<H', header_bytes[0:2])[0],
        'height': struct.unpack('<H', header_bytes[2:4])[0],
        'width_copy1': struct.unpack('<H', header_bytes[4:6])[0],
        'height_copy1': struct.unpack('<H', header_bytes[6:8])[0],
        'width_copy2': struct.unpack('<H', header_bytes[12:14])[0],
        'height_copy2': struct.unpack('<H', header_bytes[14:16])[0],
        'hotspot_x': struct.unpack('<f', header_bytes[16:20])[0],
        'hotspot_y': struct.unpack('<f', header_bytes[20:24])[0],
        'flags': struct.unpack('<H', header_bytes[24:26])[0],
        'decompressed_size': struct.unpack('<H', header_bytes[46:48])[0] if len(header_bytes) >= 48 else 0,
    }
    return info

def encode_chowdren_image(img, original_header=None, force_dimensions=None):
    """
    Encode a PIL Image to Chowdren format with proper size handling
    
    Args:
        img: PIL Image object
        original_header: Optional original .bin header (first 50 bytes) to preserve metadata
        force_dimensions: Optional (width, height) to force specific dimensions
    
    Returns:
        bytes: Encoded image data
        
    Raises:
        ValueError: If image is too large for format
    """
    
    # Convert to RGBA if needed
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    width, height = img.size
    
    # Check if dimensions are being forced (for optimization)
    if force_dimensions:
        orig_width, orig_height = width, height
        width, height = force_dimensions
        print(f"  Resizing: {orig_width}x{orig_height} → {width}x{height}")
        img = img.resize((width, height), Image.Resampling.LANCZOS)
    
    # Get pixel data
    pixel_data = img.tobytes()
    pixel_size = len(pixel_data)
    
    # CRITICAL: Check size limits
    # The format uses uint16 for decompressed size (max 65,535 bytes)
    # RGBA: 65535 / 4 = 16,383 pixels max → ~127x127 image
    MAX_PIXEL_DATA_SIZE = 65535
    
    if pixel_size > MAX_PIXEL_DATA_SIZE:
        max_dimension = int((MAX_PIXEL_DATA_SIZE / 4) ** 0.5)
        raise ValueError(
            f"Image too large! Decompressed size {pixel_size:,} bytes exceeds "
            f"format limit of {MAX_PIXEL_DATA_SIZE:,} bytes.\n"
            f"Maximum safe dimensions: ~{max_dimension}x{max_dimension} pixels.\n"
            f"Current dimensions: {width}x{height} pixels.\n"
            f"Consider resizing the image first."
        )
    
    # Compress with zlib
    compressed_data = zlib.compress(pixel_data, 9)  # Max compression
    
    print(f"  Dimensions: {width}x{height}")
    print(f"  Pixel data: {pixel_size:,} bytes")
    print(f"  Compressed: {len(compressed_data):,} bytes ({len(compressed_data)/pixel_size*100:.1f}%)")
    
    # Build header
    if original_header and len(original_header) >= 50:
        # Use original header but update ALL dimension and size fields
        header = bytearray(original_header[:50])
        
        # Update width in ALL locations (bytes 0-1, 4-5, 12-13)
        struct.pack_into('<H', header, 0, width)
        struct.pack_into('<H', header, 4, width)
        struct.pack_into('<H', header, 12, width)
        
        # Update height in ALL locations (bytes 2-3, 6-7, 14-15)
        struct.pack_into('<H', header, 2, height)
        struct.pack_into('<H', header, 6, height)
        struct.pack_into('<H', header, 14, height)
        
        # Update hotspot (should scale with dimensions if image was resized)
        if force_dimensions:
            # Preserve hotspot ratio from original
            old_info = analyze_original_header(original_header)
            if old_info and old_info['width'] > 0 and old_info['height'] > 0:
                hotspot_x_ratio = old_info['hotspot_x'] / old_info['width']
                hotspot_y_ratio = old_info['hotspot_y'] / old_info['height']
                new_hotspot_x = width * hotspot_x_ratio
                new_hotspot_y = height * hotspot_y_ratio
                struct.pack_into('<f', header, 16, new_hotspot_x)
                struct.pack_into('<f', header, 20, new_hotspot_y)
                print(f"  Hotspot: ({new_hotspot_x:.1f}, {new_hotspot_y:.1f})")
        
        # Update decompressed size (bytes 46-47)
        struct.pack_into('<H', header, 46, pixel_size)
        
        # CRITICAL FIX: Zero out mystery bytes 20-45 when dimensions change
        # These bytes contain texture coordinates, bounding boxes, or other metadata
        # from the original image that breaks rendering when dimensions change
        old_info = analyze_original_header(original_header)
        if old_info and (old_info['width'] != width or old_info['height'] != height):
            # Dimensions changed - zero out the mystery region
            header[20:46] = b'\x00' * 26
            print(f"  Zeroed bytes 20-45 (dimensions changed: {old_info['width']}×{old_info['height']} → {width}×{height})")
        
    else:
        # Create default header
        header = bytearray(50)
        
        # Width in all locations
        struct.pack_into('<H', header, 0, width)
        struct.pack_into('<H', header, 4, width)
        struct.pack_into('<H', header, 12, width)
        
        # Height in all locations
        struct.pack_into('<H', header, 2, height)
        struct.pack_into('<H', header, 6, height)
        struct.pack_into('<H', header, 14, height)
        
        # Hotspot (center of image)
        struct.pack_into('<f', header, 16, float(width) / 2.0)
        struct.pack_into('<f', header, 20, float(height) / 2.0)
        
        # Flags (default to 2)
        struct.pack_into('<H', header, 24, 2)
        
        # Decompressed size
        struct.pack_into('<H', header, 46, pixel_size)
    
    # Combine header + compressed data
    return bytes(header) + compressed_data

def encode_image_file(png_path, output_path, original_bin_path=None, target_dimensions=None):
    """
    Encode a PNG file to Chowdren .bin format
    
    Args:
        png_path: Path to input PNG file
        output_path: Path to output .bin file
        original_bin_path: Optional path to original .bin to preserve metadata
        target_dimensions: Optional (width, height) to resize to
    """
    
    print(f"\nEncoding: {png_path}")
    print("="*60)
    
    # Load PNG
    img = Image.open(png_path)
    print(f"Original: {img.size[0]}x{img.size[1]}, mode: {img.mode}")
    
    # Load original header if provided
    original_header = None
    if original_bin_path and Path(original_bin_path).exists():
        with open(original_bin_path, 'rb') as f:
            original_header = f.read(50)
        
        # Analyze original
        orig_info = analyze_original_header(original_header)
        if orig_info:
            print(f"Original .bin: {orig_info['width']}x{orig_info['height']}, "
                  f"decompressed={orig_info['decompressed_size']} bytes")
    
    try:
        # Encode
        encoded_data = encode_chowdren_image(img, original_header, target_dimensions)
        
        # Save
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(encoded_data)
        
        print(f"Total size: {len(encoded_data):,} bytes")
        print(f"Saved to: {output_path}")
        print("✓ Success!\n")
        return True
        
    except ValueError as e:
        print(f"✗ Error: {e}\n")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}\n")
        return False

def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python encode_images_fixed.py <input.png> <output.bin> [original.bin] [width] [height]")
        print()
        print("Arguments:")
        print("  input.png:     Input PNG file")
        print("  output.bin:    Output .bin file")
        print("  original.bin:  Optional original .bin for metadata preservation")
        print("  width height:  Optional target dimensions for optimization")
        print()
        print("Examples:")
        print("  # Preserve original dimensions")
        print("  python encode_images_fixed.py modified.png output.bin original.bin")
        print()
        print("  # Resize to 32x32")
        print("  python encode_images_fixed.py modified.png output.bin original.bin 32 32")
        sys.exit(1)
    
    png_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    original_bin = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    
    target_dims = None
    if len(sys.argv) >= 6:
        try:
            width = int(sys.argv[4])
            height = int(sys.argv[5])
            target_dims = (width, height)
        except ValueError:
            print("Error: Width and height must be integers")
            sys.exit(1)
    
    if not png_path.exists():
        print(f"Error: Input file not found: {png_path}")
        sys.exit(1)
    
    success = encode_image_file(png_path, output_path, original_bin, target_dims)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()