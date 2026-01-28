#!/usr/bin/env python3
"""
Extract assets from Pepper Grinder's Assets.dat file
Supports the new format with offset+size pairs
"""

import struct
import sys
import json
from pathlib import Path

# Pepper Grinder format information
PEPPER_GRINDER_FORMAT = {
    "metadata_offset": 0,
    "image_count": 10260,
    "sound_count": 267,
    "font_count": 19,
    "shader_count": 3,
    "file_count": 0,
    "table_offsets": {
        "images": 0,
        "sounds": 82048,  # 0x14080
        "fonts": 84184,   # 0x14080 + 0x858
        "shaders": 84336  # 0x14080 + 0x858 + 0x98
    }
}

def read_asset_table(f, table_offset, count):
    """
    Read an asset table with offset+size pairs
    Returns list of (offset, size) tuples
    """
    f.seek(table_offset)
    entries = []
    
    for i in range(count):
        data = f.read(8)  # 8 bytes: 4 for offset, 4 for size
        if len(data) < 8:
            break
        offset, size = struct.unpack('<II', data)
        entries.append((offset, size))
    
    return entries

def extract_asset(f, offset, size, output_path):
    """Extract a single asset to a file"""
    f.seek(offset)
    data = f.read(size)
    
    # Create parent directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'wb') as out:
        out.write(data)

def detect_image_format(data):
    """Detect image format from file signature"""
    if data[:4] == b'\x89PNG':
        return 'png'
    elif data[:2] == b'\xff\xd8':
        return 'jpg'
    elif data[:2] == b'BM':
        return 'bmp'
    elif data[:4] == b'DDS ':
        return 'dds'
    else:
        return 'bin'

def extract_images(assets_file, output_dir, limit=10):
    """Extract first N images"""
    print(f"\n{'='*80}")
    print(f"EXTRACTING IMAGES (first {limit})")
    print(f"{'='*80}\n")
    
    with open(assets_file, 'rb') as f:
        # Read image table
        images = read_asset_table(
            f, 
            PEPPER_GRINDER_FORMAT['table_offsets']['images'],
            PEPPER_GRINDER_FORMAT['image_count']
        )
        
        print(f"Found {len(images)} images in table")
        print(f"Extracting first {limit}...\n")
        
        for i, (offset, size) in enumerate(images[:limit]):
            # Read first few bytes to detect format
            f.seek(offset)
            header = f.read(min(16, size))
            fmt = detect_image_format(header)
            
            output_path = Path(output_dir) / 'images' / f'image_{i:05d}.{fmt}'
            extract_asset(f, offset, size, output_path)
            
            print(f"Image {i:5d}: offset=0x{offset:08x}, size={size:8,} bytes -> {output_path}")

def extract_sounds(assets_file, output_dir, limit=10):
    """Extract first N sounds"""
    print(f"\n{'='*80}")
    print(f"EXTRACTING SOUNDS (first {limit})")
    print(f"{'='*80}\n")
    
    with open(assets_file, 'rb') as f:
        # Read sound table
        sounds = read_asset_table(
            f,
            PEPPER_GRINDER_FORMAT['table_offsets']['sounds'],
            PEPPER_GRINDER_FORMAT['sound_count']
        )
        
        print(f"Found {len(sounds)} sounds in table")
        print(f"Extracting first {limit}...\n")
        
        for i, (offset, size) in enumerate(sounds[:limit]):
            # Check format
            f.seek(offset)
            header = f.read(4)
            
            if header == b'OggS':
                ext = 'ogg'
                fmt_info = "OggS (Ogg Vorbis)"
            elif header == b'RIFF':
                ext = 'wav'
                fmt_info = "RIFF (WAV audio)"
            else:
                ext = 'bin'
                fmt_info = f"Unknown (header: {header.hex()})"
            
            output_path = Path(output_dir) / 'sounds' / f'sound_{i:03d}.{ext}'
            extract_asset(f, offset, size, output_path)
            
            print(f"Sound {i:3d}: offset=0x{offset:08x}, size={size:8,} bytes, format={fmt_info} -> {output_path}")

def extract_fonts(assets_file, output_dir):
    """Extract all fonts"""
    print(f"\n{'='*80}")
    print(f"EXTRACTING FONTS")
    print(f"{'='*80}\n")
    
    with open(assets_file, 'rb') as f:
        # Read font table
        fonts = read_asset_table(
            f,
            PEPPER_GRINDER_FORMAT['table_offsets']['fonts'],
            PEPPER_GRINDER_FORMAT['font_count']
        )
        
        print(f"Found {len(fonts)} fonts in table\n")
        
        for i, (offset, size) in enumerate(fonts):
            # Check format
            f.seek(offset)
            header = f.read(min(16, size))
            
            # TTF/OTF detection
            if header[:4] in [b'\x00\x01\x00\x00', b'OTTO', b'true']:
                ext = 'ttf'
                fmt_info = "TrueType/OpenType"
            else:
                ext = 'bin'
                fmt_info = f"Unknown (header: {header[:4].hex()})"
            
            output_path = Path(output_dir) / 'fonts' / f'font_{i:02d}.{ext}'
            extract_asset(f, offset, size, output_path)
            
            print(f"Font {i:2d}: offset=0x{offset:08x}, size={size:6,} bytes, format={fmt_info} -> {output_path}")

def extract_shaders(assets_file, output_dir):
    """Extract all shaders"""
    print(f"\n{'='*80}")
    print(f"EXTRACTING SHADERS")
    print(f"{'='*80}\n")
    
    with open(assets_file, 'rb') as f:
        # Read shader table
        shaders = read_asset_table(
            f,
            PEPPER_GRINDER_FORMAT['table_offsets']['shaders'],
            PEPPER_GRINDER_FORMAT['shader_count']
        )
        
        print(f"Found {len(shaders)} shaders in table\n")
        
        for i, (offset, size) in enumerate(shaders):
            output_path = Path(output_dir) / 'shaders' / f'shader_{i:02d}.glsl'
            extract_asset(f, offset, size, output_path)
            
            # Try to read as text
            with open(output_path, 'rb') as shader_file:
                try:
                    content = shader_file.read(100).decode('utf-8', errors='ignore')
                    preview = content[:50].replace('\n', ' ')
                    print(f"Shader {i}: offset=0x{offset:08x}, size={size:6,} bytes")
                    print(f"  Preview: {preview}...")
                except:
                    print(f"Shader {i}: offset=0x{offset:08x}, size={size:6,} bytes (binary)")

def analyze_asset_distribution(assets_file):
    """Analyze and display statistics about the assets"""
    print(f"\n{'='*80}")
    print(f"ASSET DISTRIBUTION ANALYSIS")
    print(f"{'='*80}\n")
    
    with open(assets_file, 'rb') as f:
        # Analyze images
        images = read_asset_table(
            f,
            PEPPER_GRINDER_FORMAT['table_offsets']['images'],
            PEPPER_GRINDER_FORMAT['image_count']
        )
        
        if images:
            sizes = [size for _, size in images]
            print(f"Images ({len(images)} total):")
            print(f"  Smallest: {min(sizes):,} bytes")
            print(f"  Largest:  {max(sizes):,} bytes")
            print(f"  Average:  {sum(sizes)//len(sizes):,} bytes")
            print(f"  Total:    {sum(sizes):,} bytes ({sum(sizes)/1024/1024:.2f} MB)")
            print()
        
        # Analyze sounds
        sounds = read_asset_table(
            f,
            PEPPER_GRINDER_FORMAT['table_offsets']['sounds'],
            PEPPER_GRINDER_FORMAT['sound_count']
        )
        
        if sounds:
            sizes = [size for _, size in sounds]
            print(f"Sounds ({len(sounds)} total):")
            print(f"  Smallest: {min(sizes):,} bytes")
            print(f"  Largest:  {max(sizes):,} bytes")
            print(f"  Average:  {sum(sizes)//len(sizes):,} bytes")
            print(f"  Total:    {sum(sizes):,} bytes ({sum(sizes)/1024/1024:.2f} MB)")
            print()
        
        # Analyze fonts
        fonts = read_asset_table(
            f,
            PEPPER_GRINDER_FORMAT['table_offsets']['fonts'],
            PEPPER_GRINDER_FORMAT['font_count']
        )
        
        if fonts:
            sizes = [size for _, size in fonts]
            print(f"Fonts ({len(fonts)} total):")
            print(f"  Smallest: {min(sizes):,} bytes")
            print(f"  Largest:  {max(sizes):,} bytes")
            print(f"  Average:  {sum(sizes)//len(sizes):,} bytes")
            print(f"  Total:    {sum(sizes):,} bytes ({sum(sizes)/1024/1024:.2f} MB)")

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_pepper_grinder.py <path_to_Assets.dat> [output_dir]")
        print("\nThis will extract assets from Pepper Grinder's Assets.dat file")
        print("Output directory defaults to './extracted_assets'")
        sys.exit(1)
    
    assets_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else './extracted_assets'
    
    if not Path(assets_file).exists():
        print(f"Error: File not found: {assets_file}")
        sys.exit(1)
    
    print(f"\nPepper Grinder Asset Extractor")
    print(f"{'='*80}")
    print(f"Input file:  {assets_file}")
    print(f"Output dir:  {output_dir}")
    print(f"{'='*80}")
    
    # First, analyze the distribution
    analyze_asset_distribution(assets_file)
    
    # Extract samples
    extract_images(assets_file, output_dir, limit=PEPPER_GRINDER_FORMAT['image_count'])
    extract_sounds(assets_file, output_dir, limit=PEPPER_GRINDER_FORMAT['sound_count'])
    extract_fonts(assets_file, output_dir)
    extract_shaders(assets_file, output_dir)
    
    print(f"\n{'='*80}")
    print(f"EXTRACTION COMPLETE!")
    print(f"{'='*80}")
    print(f"\nAssets extracted to: {output_dir}")
    print(f"\nTo extract ALL assets (10,260 images, etc.), modify the limit parameter")
    print(f"in the script or use the functions programmatically.\n")

if __name__ == '__main__':
    main()