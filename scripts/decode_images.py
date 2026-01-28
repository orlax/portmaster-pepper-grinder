#!/usr/bin/env python3
"""
Decode Chowdren image format from Pepper Grinder
Images are zlib-compressed with a custom header
"""

import struct
import zlib
import sys
from pathlib import Path
from PIL import Image

def decode_chowdren_image(data):
    """
    Decode a Chowdren image file
    
    Format:
    - Bytes 0-1: Width (uint16)
    - Bytes 2-3: Height (uint16)
    - Bytes 4-49: Metadata (texture coords, hotspot, flags, etc.)
    - Bytes 50+: zlib compressed RGBA pixel data
    """
    
    # Parse header
    width = struct.unpack('<H', data[0:2])[0]
    height = struct.unpack('<H', data[2:4])[0]
    
    print(f"Dimensions: {width}x{height}")
    
    # Find zlib header (78 9c)
    zlib_start = None
    for i in range(len(data) - 1):
        if data[i:i+2] == b'\x78\x9c':
            zlib_start = i
            break
    
    if zlib_start is None:
        raise ValueError("Could not find zlib compressed data")
    
    print(f"zlib data starts at byte: {zlib_start} (0x{zlib_start:x})")
    
    # Decompress pixel data
    compressed_data = data[zlib_start:]
    try:
        pixel_data = zlib.decompress(compressed_data)
        print(f"Decompressed size: {len(pixel_data)} bytes")
    except Exception as e:
        raise ValueError(f"Failed to decompress: {e}")
    
    # Determine pixel format
    # Expected size for RGBA: width * height * 4
    expected_rgba = width * height * 4
    expected_rgb = width * height * 3
    expected_bgra = width * height * 4
    
    print(f"Expected sizes: RGBA={expected_rgba}, RGB={expected_rgb}")
    print(f"Actual size: {len(pixel_data)}")
    
    # Try to create image
    if len(pixel_data) == expected_rgba:
        # RGBA format
        img = Image.frombytes('RGBA', (width, height), pixel_data)
        print("Format: RGBA")
    elif len(pixel_data) == expected_rgb:
        # RGB format
        img = Image.frombytes('RGB', (width, height), pixel_data)
        print("Format: RGB")
    else:
        # Try BGRA or other formats
        print(f"Warning: Unexpected pixel data size. Trying RGBA anyway...")
        # Pad or truncate to RGBA size
        if len(pixel_data) < expected_rgba:
            pixel_data += b'\xff' * (expected_rgba - len(pixel_data))
        else:
            pixel_data = pixel_data[:expected_rgba]
        img = Image.frombytes('RGBA', (width, height), pixel_data)
    
    return img

def decode_image_file(input_path, output_path=None):
    """Decode a Chowdren .bin image file to PNG"""
    
    print(f"\nDecoding: {input_path}")
    print("="*60)
    
    with open(input_path, 'rb') as f:
        data = f.read()
    
    try:
        img = decode_chowdren_image(data)
        
        if output_path is None:
            output_path = str(input_path).replace('.bin', '.png')
        
        img.save(output_path)
        print(f"Saved to: {output_path}")
        print("✓ Success!\n")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}\n")
        return False

def batch_decode_images(input_dir, output_dir=None):
    """Decode all .bin images in a directory"""
    
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"Error: Directory not found: {input_dir}")
        return
    
    bin_files = list(input_path.glob('*.bin'))
    
    if not bin_files:
        print(f"No .bin files found in: {input_dir}")
        return
    
    print(f"\nFound {len(bin_files)} image files")
    print("="*60)
    
    success_count = 0
    
    for bin_file in bin_files:
        if output_dir:
            output_path = Path(output_dir) / bin_file.name.replace('.bin', '.png')
            output_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            output_path = bin_file.with_suffix('.png')
        
        if decode_image_file(bin_file, output_path):
            success_count += 1
    
    print("="*60)
    print(f"Successfully decoded: {success_count}/{len(bin_files)} images")

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Decode single image:")
        print("    python decode_images.py <image.bin> [output.png]")
        print()
        print("  Decode directory of images:")
        print("    python decode_images.py <directory> [output_directory]")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if input_path.is_dir():
        batch_decode_images(input_path, output_path)
    elif input_path.is_file():
        decode_image_file(input_path, output_path)
    else:
        print(f"Error: Path not found: {input_path}")
        sys.exit(1)

if __name__ == '__main__':
    main()