#!/usr/bin/env python3
"""
Safe asset optimization for Pepper Grinder
Handles size limits and validates all changes
"""

import struct
from pathlib import Path
from PIL import Image
import subprocess
import sys

# Format limits
MAX_PIXEL_DATA_SIZE = 65535  # uint16 limit
MAX_SAFE_DIMENSION = int((MAX_PIXEL_DATA_SIZE / 4) ** 0.5)  # ~127 pixels

def analyze_image(bin_path):
    """Get info about a .bin image without fully decoding"""
    with open(bin_path, 'rb') as f:
        header = f.read(50)
    
    width = struct.unpack('<H', header[0:2])[0]
    height = struct.unpack('<H', header[2:4])[0]
    decompressed_size = struct.unpack('<H', header[46:48])[0]
    
    return {
        'width': width,
        'height': height,
        'decompressed_size': decompressed_size,
        'file_size': bin_path.stat().st_size
    }

def calculate_safe_dimensions(original_width, original_height, scale_factor=0.5):
    """
    Calculate safe dimensions for resizing
    
    Args:
        original_width, original_height: Original dimensions
        scale_factor: How much to scale (0.5 = 50%)
    
    Returns:
        (new_width, new_height, is_safe)
    """
    new_width = max(1, int(original_width * scale_factor))
    new_height = max(1, int(original_height * scale_factor))
    
    # Check if result would be safe
    pixel_count = new_width * new_height
    pixel_data_size = pixel_count * 4  # RGBA
    is_safe = pixel_data_size <= MAX_PIXEL_DATA_SIZE
    
    # If not safe, scale down further
    if not is_safe:
        max_pixels = MAX_PIXEL_DATA_SIZE // 4
        aspect_ratio = original_width / original_height
        new_height = int((max_pixels / aspect_ratio) ** 0.5)
        new_width = int(new_height * aspect_ratio)
        pixel_data_size = new_width * new_height * 4
        is_safe = pixel_data_size <= MAX_PIXEL_DATA_SIZE
    
    return new_width, new_height, is_safe, pixel_data_size

def optimize_asset_batch(
    extracted_dir,
    decoded_dir,
    optimized_dir,
    repacked_dir,
    scale_factor=0.5,
    start_index=0,
    end_index=None,
    dry_run=False
):
    """
    Optimize a batch of assets safely
    
    Args:
        extracted_dir: Directory with original .bin files
        decoded_dir: Directory for decoded PNGs (temp)
        optimized_dir: Directory for optimized PNGs (temp)
        repacked_dir: Directory for re-encoded .bin files
        scale_factor: How much to scale down (0.5 = 50% size)
        start_index: First image to optimize
        end_index: Last image to optimize (None = all)
        dry_run: If True, only analyze, don't modify
    """
    
    extracted_path = Path(extracted_dir)
    decoded_path = Path(decoded_dir)
    optimized_path = Path(optimized_dir)
    repacked_path = Path(repacked_dir)
    
    # Create directories
    if not dry_run:
        decoded_path.mkdir(parents=True, exist_ok=True)
        optimized_path.mkdir(parents=True, exist_ok=True)
        repacked_path.mkdir(parents=True, exist_ok=True)
    
    # Find all .bin files
    bin_files = sorted(extracted_path.glob('image_*.bin'))
    
    if end_index:
        bin_files = [f for f in bin_files if start_index <= int(f.stem.split('_')[1]) <= end_index]
    else:
        bin_files = bin_files[start_index:]
    
    print(f"\n{'='*80}")
    print(f"ASSET OPTIMIZATION ANALYSIS")
    print(f"{'='*80}")
    print(f"Scale factor: {scale_factor*100:.0f}%")
    print(f"Processing: {len(bin_files)} images")
    print(f"Mode: {'DRY RUN (analysis only)' if dry_run else 'LIVE (will modify)'}")
    print(f"{'='*80}\n")
    
    stats = {
        'total': 0,
        'safe': 0,
        'unsafe': 0,
        'skipped': 0,
        'original_size': 0,
        'new_size': 0,
        'original_pixels': 0,
        'new_pixels': 0
    }
    
    unsafe_files = []
    
    for bin_file in bin_files:
        stats['total'] += 1
        index = int(bin_file.stem.split('_')[1])
        
        try:
            # Analyze original
            info = analyze_image(bin_file)
            
            # Calculate new dimensions
            new_w, new_h, is_safe, new_pixel_size = calculate_safe_dimensions(
                info['width'], info['height'], scale_factor
            )
            
            stats['original_size'] += info['file_size']
            stats['original_pixels'] += info['width'] * info['height']
            
            if not is_safe:
                stats['unsafe'] += 1
                unsafe_files.append((index, info['width'], info['height'], new_w, new_h))
                print(f"⚠ Image {index:05d}: {info['width']:3d}x{info['height']:3d} → {new_w:3d}x{new_h:3d} "
                      f"UNSAFE (would be {new_pixel_size:,} bytes)")
                continue
            
            stats['safe'] += 1
            stats['new_pixels'] += new_w * new_h
            
            reduction = (1 - (new_w * new_h) / (info['width'] * info['height'])) * 100
            
            if stats['safe'] <= 20 or stats['safe'] % 100 == 0:
                print(f"✓ Image {index:05d}: {info['width']:3d}x{info['height']:3d} → {new_w:3d}x{new_h:3d} "
                      f"(-{reduction:.0f}% pixels)")
            
            if not dry_run:
                # Decode
                png_file = decoded_path / f"image_{index:05d}.png"
                subprocess.run([
                    'python3', 'decode_images.py',
                    str(bin_file), str(png_file)
                ], capture_output=True)
                
                # Resize
                img = Image.open(png_file)
                img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                optimized_file = optimized_path / f"image_{index:05d}.png"
                img_resized.save(optimized_file)
                
                # Re-encode with new dimensions
                repacked_file = repacked_path / f"image_{index:05d}.bin"
                subprocess.run([
                    'python3', 'encode_images_fixed.py',
                    str(optimized_file),
                    str(repacked_file),
                    str(bin_file),
                    str(new_w), str(new_h)
                ], capture_output=True)
                
                # Track new size
                if repacked_file.exists():
                    stats['new_size'] += repacked_file.stat().st_size
                
        except Exception as e:
            stats['skipped'] += 1
            print(f"✗ Image {index:05d}: Error - {e}")
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"OPTIMIZATION SUMMARY")
    print(f"{'='*80}")
    print(f"Total images:     {stats['total']}")
    print(f"Safe to optimize: {stats['safe']} ({stats['safe']/stats['total']*100:.1f}%)")
    print(f"Unsafe (skipped): {stats['unsafe']} ({stats['unsafe']/stats['total']*100:.1f}%)")
    print(f"Errors (skipped): {stats['skipped']}")
    print()
    print(f"Original pixels:  {stats['original_pixels']:,}")
    print(f"New pixels:       {stats['new_pixels']:,}")
    print(f"Pixel reduction:  {(1-stats['new_pixels']/stats['original_pixels'])*100:.1f}%")
    print()
    
    if not dry_run and stats['new_size'] > 0:
        print(f"Original size:    {stats['original_size']:,} bytes ({stats['original_size']/1024/1024:.2f} MB)")
        print(f"New size:         {stats['new_size']:,} bytes ({stats['new_size']/1024/1024:.2f} MB)")
        print(f"Size reduction:   {(1-stats['new_size']/stats['original_size'])*100:.1f}%")
    
    if unsafe_files:
        print(f"\n{'='*80}")
        print(f"UNSAFE FILES (would exceed format limits):")
        print(f"{'='*80}")
        for idx, ow, oh, nw, nh in unsafe_files[:10]:
            print(f"  Image {idx:05d}: {ow}x{oh} → {nw}x{nh}")
        if len(unsafe_files) > 10:
            print(f"  ... and {len(unsafe_files)-10} more")
    
    print(f"{'='*80}\n")
    
    if dry_run:
        print("This was a DRY RUN. No files were modified.")
        print("Run without --dry-run to actually optimize.")
    
    return stats

def main():
    if len(sys.argv) < 5:
        print("Usage: python optimize_assets.py <extracted_dir> <decoded_dir> <optimized_dir> <repacked_dir> [options]")
        print()
        print("Options:")
        print("  --scale FACTOR     Scale factor (default: 0.5 = 50%)")
        print("  --start INDEX      Start at image index (default: 0)")
        print("  --end INDEX        End at image index (default: all)")
        print("  --dry-run          Analyze only, don't modify")
        print()
        print("Example:")
        print("  python optimize_assets.py extracted_assets/images/ decoded/ optimized/ repacked/images/ --scale 0.5 --dry-run")
        sys.exit(1)
    
    extracted = sys.argv[1]
    decoded = sys.argv[2]
    optimized = sys.argv[3]
    repacked = sys.argv[4]
    
    scale = 0.5
    start = 0
    end = None
    dry_run = False
    
    i = 5
    while i < len(sys.argv):
        if sys.argv[i] == '--scale' and i + 1 < len(sys.argv):
            scale = float(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--start' and i + 1 < len(sys.argv):
            start = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--end' and i + 1 < len(sys.argv):
            end = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--dry-run':
            dry_run = True
            i += 1
        else:
            i += 1
    
    optimize_asset_batch(extracted, decoded, optimized, repacked, scale, start, end, dry_run)

if __name__ == '__main__':
    main()