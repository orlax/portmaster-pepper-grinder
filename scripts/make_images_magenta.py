#!/usr/bin/env python3
"""
Make Pepper Grinder player sprites magenta for testing
Modifies images 1800-2049 (250 player animation frames)
"""

from PIL import Image
from pathlib import Path
import sys

START_INDEX = 10003
END_INDEX = 10027



def make_magenta(image_path, output_path, intensity=0.8):
    """
    Make an image magenta while preserving alpha channel
    
    Args:
        image_path: Input PNG file
        output_path: Output PNG file
        intensity: How much magenta to apply (0.0-1.0)
                   1.0 = fully magenta, 0.5 = half magenta/half original
    """
    img = Image.open(image_path)
    
    # Ensure RGBA mode
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Get pixel data
    pixels = img.load()
    
    # Make it magenta
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = pixels[x, y]
            
            # Only modify non-transparent pixels
            if a > 0:
                # Blend with magenta (255, 0, 255)
                new_r = int(r * (1 - intensity) + 255 * intensity)
                new_g = int(g * (1 - intensity) + 0 * intensity)
                new_b = int(b * (1 - intensity) + 255 * intensity)
                
                pixels[x, y] = (new_r, new_g, new_b, a)
    
    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)

def batch_make_magenta(input_dir, output_dir, start_index, end_index, intensity=0.8):
    """
    Make a range of player sprites magenta
    
    Args:
        input_dir: Directory with decoded PNG images
        output_dir: Directory for magenta output images
        start_index: First image index (e.g., 1800)
        end_index: Last image index (e.g., 2049)
        intensity: Magenta intensity (0.0-1.0)
    """
    
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    if not input_path.exists():
        print(f"Error: Input directory not found: {input_dir}")
        return
    
    print(f"Making player sprites magenta...")
    print(f"Range: image_{start_index:05d} to image_{end_index:05d}")
    print(f"Intensity: {intensity * 100:.0f}%")
    print(f"{'='*60}\n")
    
    success_count = 0
    missing_count = 0
    
    for i in range(start_index, end_index + 1):
        image_name = f"image_{i:05d}.png"
        input_file = input_path / image_name
        output_file = output_path / image_name
        
        if not input_file.exists():
            if missing_count < 10:  # Only show first 10 missing files
                print(f"⚠ Missing: {image_name}")
            missing_count += 1
            continue
        
        try:
            make_magenta(input_file, output_file, intensity)
            success_count += 1
            
            # Show progress every 50 images
            if success_count % 50 == 0:
                print(f"✓ Processed {success_count} images...")
                
        except Exception as e:
            print(f"✗ Error processing {image_name}: {e}")
    
    print(f"\n{'='*60}")
    print(f"Complete!")
    print(f"  Successfully processed: {success_count} images")
    if missing_count > 0:
        print(f"  Missing files: {missing_count}")
    print(f"  Output directory: {output_dir}")
    print(f"{'='*60}\n")

def main():
    if len(sys.argv) < 3:
        print("Usage: python make_player_magenta.py <input_dir> <output_dir> [intensity]")
        print()
        print("Makes player sprites (images 1800-2049) magenta for testing")
        print()
        print("Arguments:")
        print("  input_dir:  Directory with decoded PNG images")
        print("  output_dir: Directory for magenta output images")
        print("  intensity:  Optional, 0.0-1.0 (default: 0.8)")
        print()
        print("Example:")
        print("  python make_player_magenta.py decoded_images/ magenta_player/")
        print("  python make_player_magenta.py decoded_images/ magenta_player/ 0.6")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    intensity = float(sys.argv[3]) if len(sys.argv) > 3 else 0.8
    
    batch_make_magenta(input_dir, output_dir, START_INDEX, END_INDEX, intensity)
    
    print("\nNext steps:")
    print("1. Encode the magenta images back to .bin:")
    print(f"   python3 encode_images.py {output_dir} repacked_assets/images/ extracted_assets/images/")
    print()
    print("2. Repack Assets.dat:")
    print("   python3 repack_assets.py assets_linux/Assets.dat repacked_assets/ Assets_modded.dat")
    print()
    print("3. Test in game:")
    print("   cp assets_linux/Assets.dat assets_linux/Assets.dat.backup")
    print("   cp Assets_modded.dat assets_linux/Assets.dat")
    print()

if __name__ == '__main__':
    main()