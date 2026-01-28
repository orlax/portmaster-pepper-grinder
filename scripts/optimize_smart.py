#!/usr/bin/env python3
"""
Smart asset optimization - only optimize when it actually reduces size
"""

import struct
import zlib
from pathlib import Path
from PIL import Image
import sys

def encode_chowdren_image_inline(img, original_header_bytes):
    """Encode image with header updates"""
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    width, height = img.size
    pixel_data = img.tobytes()
    pixel_size = len(pixel_data)
    
    if pixel_size > 65535:
        raise ValueError(f"Image too large: {pixel_size} bytes")
    
    # Try different compression levels and pick best
    best_compressed = None
    best_size = float('inf')
    
    for level in [6, 9]:  # Try medium and max compression
        compressed = zlib.compress(pixel_data, level)
        if len(compressed) < best_size:
            best_size = len(compressed)
            best_compressed = compressed
    
    # Build header
    header = bytearray(original_header_bytes[:50])
    
    # Update ALL dimension fields
    struct.pack_into('<H', header, 0, width)
    struct.pack_into('<H', header, 2, height)
    struct.pack_into('<H', header, 4, width)
    struct.pack_into('<H', header, 6, height)
    struct.pack_into('<H', header, 12, width)
    struct.pack_into('<H', header, 14, height)
    struct.pack_into('<H', header, 46, pixel_size)
    
    # CRITICAL FIX: Zero out mystery bytes 20-45 when dimensions change
    orig_w = struct.unpack('<H', original_header_bytes[0:2])[0]
    orig_h = struct.unpack('<H', original_header_bytes[2:4])[0]
    
    if orig_w != width or orig_h != height:
        # Dimensions changed - zero out mystery region
        header[20:46] = b'\x00' * 26
    else:
        # Same dimensions - keep hotspot scaling
        if orig_w > 0 and orig_h > 0:
            orig_hotspot_x = struct.unpack('<f', original_header_bytes[16:20])[0]
            orig_hotspot_y = struct.unpack('<f', original_header_bytes[20:24])[0]
            new_hotspot_x = (orig_hotspot_x / orig_w) * width
            new_hotspot_y = (orig_hotspot_y / orig_h) * height
            struct.pack_into('<f', header, 16, new_hotspot_x)
            struct.pack_into('<f', header, 20, new_hotspot_y)
    
    return bytes(header) + best_compressed

def decode_chowdren_image_inline(data):
    """Decode a .bin to PIL Image"""
    width = struct.unpack('<H', data[0:2])[0]
    height = struct.unpack('<H', data[2:4])[0]
    
    # Find zlib
    zlib_start = None
    for i in range(min(100, len(data) - 1)):
        if data[i:i+2] == b'\x78\x9c':
            zlib_start = i
            break
    
    if zlib_start is None:
        raise ValueError("No zlib data found")
    
    pixel_data = zlib.decompress(data[zlib_start:])
    img = Image.frombytes('RGBA', (width, height), pixel_data)
    return img

def optimize_single_image_smart(bin_path, output_bin_path, scale_factor=0.5, min_dimension=16):
    """
    Smart optimization: focus on reducing RAM usage (pixel count), not file size
    
    Args:
        scale_factor: How much to scale down (0.5 = 50%)
        min_dimension: Don't resize if either dimension is <= this (default: 16)
    
    Returns: (saved, original_pixels, new_pixels, reason)
    """
    try:
        # Read original
        with open(bin_path, 'rb') as f:
            original_data = f.read()
        
        original_size = len(original_data)
        
        if original_size < 50:
            return (False, original_size, 0, "too_small", None)
        
        # Decode
        img = decode_chowdren_image_inline(original_data)
        orig_w, orig_h = img.size
        
        # Skip if already too small
        if orig_w <= min_dimension or orig_h <= min_dimension:
            return (False, orig_w * orig_h, 0, "too_small", None)
        
        # Calculate new size
        new_w = max(1, int(orig_w * scale_factor))
        new_h = max(1, int(orig_h * scale_factor))
        
        # Enforce minimum after scaling
        if new_w < min_dimension:
            new_w = min_dimension
        if new_h < min_dimension:
            new_h = min_dimension
        
        # If scaling doesn't change anything, skip
        if new_w == orig_w and new_h == orig_h:
            return (False, orig_w * orig_h, 0, "no_change", None)
        
        # Check if safe
        new_pixel_size = new_w * new_h * 4
        if new_pixel_size > 65535:
            return (False, orig_w * orig_h, 0, "would_be_too_large", None)
        
        # Resize
        img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Re-encode
        encoded_data = encode_chowdren_image_inline(img_resized, original_data)
        
        # Always save! We care about RAM (pixels), not file size
        output_bin_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_bin_path, 'wb') as f:
            f.write(encoded_data)
        
        # Calculate pixel reduction
        orig_pixels = orig_w * orig_h
        new_pixels = new_w * new_h
        pixel_reduction = (1 - new_pixels / orig_pixels) * 100
        
        return (True, orig_pixels, new_pixels, "saved", pixel_reduction)
        
    except Exception as e:
        return (False, 0, 0, "error", str(e))

def optimize_batch_smart(input_dir, output_dir, scale_factor=0.5, min_dimension=16, start=0, end=None):
    """Smart batch optimization - focus on RAM reduction"""
    
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    bin_files = sorted(input_path.glob('image_*.bin'))
    
    if end:
        bin_files = [f for f in bin_files if start <= int(f.stem.split('_')[1]) <= end]
    else:
        bin_files = bin_files[start:]
    
    print(f"\n{'='*80}")
    print(f"SMART ASSET OPTIMIZATION - RAM FOCUSED")
    print(f"{'='*80}")
    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Scale:  {scale_factor*100:.0f}%")
    print(f"Min dimension: {min_dimension}x{min_dimension} (skip smaller)")
    print(f"Files:  {len(bin_files)}")
    print(f"{'='*80}\n")
    
    stats = {
        'saved': 0,
        'skipped_too_small': 0,
        'skipped_no_change': 0,
        'skipped_error': 0,
        'original_pixels': 0,
        'new_pixels': 0,
    }
    
    examples_shown = 0
    
    for i, bin_file in enumerate(bin_files):
        index = int(bin_file.stem.split('_')[1])
        output_file = output_path / f"image_{index:05d}.bin"
        
        saved, orig_pixels, new_pixels, reason, extra = optimize_single_image_smart(
            bin_file, output_file, scale_factor, min_dimension
        )
        
        if saved:
            stats['saved'] += 1
            stats['original_pixels'] += orig_pixels
            stats['new_pixels'] += new_pixels
            
            if examples_shown < 20 or stats['saved'] % 500 == 0:
                print(f"✓ Image {index:05d}: {orig_pixels:6,} → {new_pixels:6,} pixels (-{extra:.0f}%) RAM savings")
                examples_shown += 1
        else:
            if reason == "too_small":
                stats['skipped_too_small'] += 1
            elif reason == "no_change":
                stats['skipped_no_change'] += 1
            else:
                stats['skipped_error'] += 1
                if examples_shown < 20:
                    print(f"✗ Image {index:05d}: {reason}")
                    examples_shown += 1
        
        if (i + 1) % 1000 == 0:
            if stats['original_pixels'] > 0:
                reduction = (1 - stats['new_pixels']/stats['original_pixels'])*100
                print(f"\nProcessed {i+1}/{len(bin_files)} images...")
                print(f"  Optimized: {stats['saved']}, RAM reduction: {reduction:.1f}%\n")
            else:
                print(f"\nProcessed {i+1}/{len(bin_files)} images...\n")
    
    print(f"\n{'='*80}")
    print(f"SMART OPTIMIZATION COMPLETE")
    print(f"{'='*80}")
    print(f"Images optimized:         {stats['saved']:,}")
    print(f"Images skipped (too small): {stats['skipped_too_small']:,}")
    print(f"Images skipped (no change): {stats['skipped_no_change']:,}")
    print(f"Images skipped (errors):    {stats['skipped_error']:,}")
    print()
    
    if stats['original_pixels'] > 0:
        print(f"RAM REDUCTION (what matters!):")
        print(f"  Original pixels: {stats['original_pixels']:,}")
        print(f"  New pixels:      {stats['new_pixels']:,}")
        reduction = (1 - stats['new_pixels'] / stats['original_pixels']) * 100
        print(f"  Pixel reduction: {reduction:.1f}%")
        print(f"  Estimated RAM saved: ~{(stats['original_pixels'] - stats['new_pixels']) * 4 / 1024 / 1024:.2f} MB")
    
    print(f"{'='*80}\n")
    
    print("NOTE: File size may be larger, but RAM usage will be lower!")
    print("Smaller textures = less RAM when decompressed, even if compressed file is bigger.")
    
    return stats

def main():
    if len(sys.argv) < 3:
        print("Usage: python optimize_smart.py <input_dir> <output_dir> [scale] [min_dimension] [start] [end]")
        print()
        print("Arguments:")
        print("  scale:         Resize factor (default: 0.5 = 50%)")
        print("  min_dimension: Don't resize if width or height <= this (default: 16)")
        print()
        print("Examples:")
        print("  # Resize to 50%, skip images 16x16 or smaller")
        print("  python optimize_smart.py extracted_assets/images/ repacked_assets/images/ 0.5 16")
        print()
        print("  # Resize to 75%, skip images 32x32 or smaller")
        print("  python optimize_smart.py extracted_assets/images/ repacked_assets/images/ 0.75 32")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    scale = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
    min_dim = int(sys.argv[4]) if len(sys.argv) > 4 else 16
    start = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    end = int(sys.argv[6]) if len(sys.argv) > 6 else None
    
    optimize_batch_smart(input_dir, output_dir, scale, min_dim, start, end)

if __name__ == '__main__':
    main()